"""The live client for an open-weights model on the learner's own machine.

A local server that speaks the OpenAI-compatible chat completions API
(Ollama, LM Studio, a llama.cpp server) answers it; the request and the
response have the shape of ``pbc.agents.clients.openai``, whose functions
build and read them, and the ``openai`` SDK sends them (``uv sync --extra
openai``). No new dependency, and no key: the server asks for none, and the
SDK is given a placeholder so that it never looks for a provider key.

The address is ``PBC_LOCAL_BASE_URL``, else ``DEFAULT_BASE_URL`` (the address
Ollama serves the API on). It must name a loopback address, ``localhost`` or
an address of 127.0.0.0/8 or ``[::1]``, and the client sends its request
without any proxy the environment configures, so no prompt leaves the machine
by this client. The model is ``PBC_LOCAL_MODEL`` (or the argument of
``make_client``), the name the server knows it by; the project chooses none.

The tokens are counted where the server reports them (``last_usage``); a
local model costs nothing per token, so the client's ``prices_eur_per_mtok``
are zero and a recording with it (``record-campaign``) needs no prices.
"""

import ipaddress
import re
from collections.abc import Sequence
from typing import Any

from pbc.agents.clients import openai as chat
from pbc.agents.messages import ModelMessage, ToolSpec, Turn
from pbc.agents.secrets import Secret, read_setting

BASE_URL_VARIABLE = "PBC_LOCAL_BASE_URL"
MODEL_VARIABLE = "PBC_LOCAL_MODEL"
DEFAULT_BASE_URL = "http://localhost:11434/v1"
PRICES_EUR_PER_MTOK = (0.0, 0.0)
# A local model on a learner's machine answers more slowly than a hosted one.
TIMEOUT_SECONDS = 600.0
# What the SDK sends as its key: the server ignores it.
PLACEHOLDER_KEY = "local-no-key"
LOOPBACK_NAMES = {"localhost"}
# A base address: a scheme, a host (a name, an IPv4 address, or an IPv6
# address in brackets), an optional port, and an optional path; no user
# part, query, or fragment.
_ADDRESS = re.compile(
    r"(?P<scheme>https?)://(?P<host>\[[0-9A-Fa-f:.]+\]|[A-Za-z0-9.-]+)"
    r"(?::(?P<port>[0-9]{1,5}))?(?P<path>/[A-Za-z0-9._~/-]*)?"
)


class ProviderError(RuntimeError):
    """The local client is not configured, or the request failed."""


def loopback_base_url(address: str) -> str:
    """``address`` if it is an HTTP base address on a loopback host;
    otherwise raise ``ProviderError``."""
    match = _ADDRESS.fullmatch(address)
    if match is None:
        raise ProviderError(
            f"{address!r} is not a base address such as {DEFAULT_BASE_URL}"
        )
    host = match["host"].lower()
    if host not in LOOPBACK_NAMES:
        try:
            loopback = ipaddress.ip_address(host.strip("[]")).is_loopback
        except ValueError:
            loopback = False
        if not loopback:
            raise ProviderError(
                f"{host} is not a loopback address; the local client sends"
                " prompts only to a server on this machine (localhost,"
                " 127.0.0.1, or [::1])"
            )
    return address


class LocalClient:
    """A ``ModelClient`` that calls a model server on the loopback address."""

    def __init__(self, model: str, base_url: str, sdk: Any):
        self.model = model
        self.base_url = loopback_base_url(base_url)
        self.secrets: tuple[Secret, ...] = ()
        self.prices_eur_per_mtok = PRICES_EUR_PER_MTOK
        self.last_usage: dict[str, int] | None = None
        try:
            self._client = sdk.OpenAI(
                api_key=PLACEHOLDER_KEY,
                base_url=self.base_url,
                timeout=TIMEOUT_SECONDS,
                max_retries=1,
                http_client=sdk.DefaultHttpxClient(trust_env=False),
            )
        except Exception as error:
            raise _failure("the local client could not be set up", error) from None

    def __repr__(self) -> str:
        return f"LocalClient(model={self.model!r}, base_url={self.base_url!r})"

    def complete(
        self, system: str, conversation: Sequence[Turn], tools: Sequence[ToolSpec]
    ) -> ModelMessage:
        request = chat.build_request(self.model, system, conversation, tools)
        self.last_usage = None
        try:
            response = self._client.chat.completions.create(**request)
            data = response.model_dump()
            self.last_usage = chat.parse_usage(data)
            return chat.parse_response(data)
        except Exception as error:
            raise _failure("the local model request failed", error) from None


def _failure(what: str, error: Exception) -> ProviderError:
    """A ``ProviderError`` for ``error``; raise it with ``from None`` so that
    the SDK's own message chain is dropped."""
    return ProviderError(f"{what}: {type(error).__name__}: {error}")


def make_client(model: str | None = None, base_url: str | None = None) -> LocalClient:
    """The client for ``model`` (else ``PBC_LOCAL_MODEL``) on the server at
    ``base_url`` (else ``PBC_LOCAL_BASE_URL``, else ``DEFAULT_BASE_URL``)."""
    address = loopback_base_url(
        base_url or read_setting(BASE_URL_VARIABLE) or DEFAULT_BASE_URL
    )
    chosen = model or read_setting(MODEL_VARIABLE)
    if not chosen:
        raise ProviderError(
            f"no local model is configured: export {MODEL_VARIABLE} with the"
            " name your server knows the model by (for Ollama, a name that"
            " `ollama list` shows)"
        )
    try:
        import openai
    except ImportError:
        raise ProviderError(
            "the openai package is not installed; run: uv sync --extra openai"
        ) from None
    return LocalClient(chosen, address, openai)
