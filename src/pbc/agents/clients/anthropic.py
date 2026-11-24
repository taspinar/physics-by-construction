"""The live client for Claude (the Messages API of Anthropic).

It runs only on a learner's machine, or the recorder's (#615). The key is read
from the environment variable ``ANTHROPIC_API_KEY`` and used for nothing but
the provider request; it is handed to the SDK explicitly, so the SDK's own
search for credentials (a stored login, another variable) is not used.
Errors from the SDK, when it is set up and when it is asked, are re-raised
without the SDK's own message chain, with the key removed, because an SDK may
echo the request or its configuration in an error.

The model is a configuration value: the argument of ``make_client``, else the
variable ``PBC_ANTHROPIC_MODEL``, else ``MODEL``, the current Opus model of
the provider's model table (checked on 2026-11-24). A recording names the
model that produced it, so changing the default changes no recording.

The harness keeps the text and the tool calls of an assistant turn, not the
model's thinking blocks; the provider accepts a conversation sent back
without any of them (the model then continues without its earlier
reasoning), so a conversation is sent back as the harness holds it. No
server-side fallback to another model is requested: a declined request ends
the campaign, and a recording names the one model that produced it.

The SDK is an optional dependency (``uv sync --extra anthropic``). Building
the request and reading the response are plain functions, tested without it.
"""

import base64
import json
from collections.abc import Mapping, Sequence
from typing import Any

from pbc.agents.messages import (
    ModelMessage,
    ToolCall,
    ToolResult,
    ToolSpec,
    Turn,
    UserTurn,
)
from pbc.agents.secrets import MissingKey, Secret, read_setting, redact

KEY_VARIABLE = "ANTHROPIC_API_KEY"
MODEL_VARIABLE = "PBC_ANTHROPIC_MODEL"
MODEL = "claude-opus-5-5"
GROUP = "anthropic"
# A turn of a campaign asks for one or a few tool calls; the limit keeps a
# request well inside the SDK's limit for a request that is not streamed.
MAX_TOKENS = 16000
TIMEOUT_SECONDS = 300.0


class ProviderError(RuntimeError):
    """The provider request failed. The message never contains the key."""


def build_request(
    model: str, system: str, conversation: Sequence[Turn], tools: Sequence[ToolSpec]
) -> dict[str, Any]:
    """The arguments of one Messages request.

    The tool results that follow one assistant turn go back in one user
    message, as the provider asks. An assistant turn with neither text nor a
    tool call has no content to send and is left out.
    """
    messages: list[dict[str, Any]] = []
    for turn in conversation:
        if isinstance(turn, UserTurn):
            content: list[dict[str, Any]] = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": base64.b64encode(picture.png).decode("ascii"),
                    },
                }
                for picture in turn.pictures
            ]
            content.append({"type": "text", "text": turn.text})
            messages.append({"role": "user", "content": content})
        elif isinstance(turn, ModelMessage):
            content = [{"type": "text", "text": turn.text}] if turn.text else []
            content += [
                {
                    "type": "tool_use",
                    "id": call.id,
                    "name": call.name,
                    "input": call.arguments if isinstance(call.arguments, dict) else {},
                }
                for call in turn.tool_calls
            ]
            if content:
                messages.append({"role": "assistant", "content": content})
        elif isinstance(turn, ToolResult):
            block = {
                "type": "tool_result",
                "tool_use_id": turn.call_id,
                "content": json.dumps(dict(turn.content)),
                "is_error": not turn.ok,
            }
            last = messages[-1] if messages else None
            if (
                last is not None
                and last["role"] == "user"
                and last["content"]
                and all(part["type"] == "tool_result" for part in last["content"])
            ):
                last["content"].append(block)
            else:
                messages.append({"role": "user", "content": [block]})
    return {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "system": system,
        "messages": messages,
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": dict(tool.parameters),
            }
            for tool in tools
        ],
    }


def parse_response(response: Mapping[str, Any]) -> ModelMessage:
    """The assistant message of a Messages response: its text blocks, joined,
    and its tool calls. Thinking blocks are not kept. A declined request
    (``stop_reason`` ``refusal``) becomes a message without tool calls that
    says so, and the campaign ends there."""
    blocks = response.get("content") or []
    text = "\n\n".join(
        block["text"]
        for block in blocks
        if block.get("type") == "text" and block.get("text")
    )
    if response.get("stop_reason") == "refusal":
        details = response.get("stop_details") or {}
        category = details.get("category") or "no category given"
        note = f"The provider declined to answer ({category})."
        return ModelMessage(text=f"{text}\n\n{note}" if text else note)
    calls = tuple(
        ToolCall(id=block["id"], name=block["name"], arguments=block.get("input"))
        for block in blocks
        if block.get("type") == "tool_use"
    )
    return ModelMessage(text=text, tool_calls=calls)


def parse_usage(response: Mapping[str, Any]) -> dict[str, int] | None:
    """The tokens of one response, as ``input_tokens`` and ``output_tokens``,
    or None when the provider reported none (F145: the spend count of a
    recorded campaign). Tokens written to or read from the prompt cache count
    as input, at the full input price: the count never undercounts. Thinking
    is billed as output and is part of ``output_tokens``."""
    usage = response.get("usage") or {}
    if not usage:
        return None
    return {
        "input_tokens": int(usage.get("input_tokens") or 0)
        + int(usage.get("cache_creation_input_tokens") or 0)
        + int(usage.get("cache_read_input_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or 0),
    }


class AnthropicClient:
    """A ``ModelClient`` that calls Claude with the learner's key."""

    def __init__(self, secret: Secret, sdk: Any, model: str = MODEL):
        self.model = model
        self.secrets = (secret,)
        self.last_usage: dict[str, int] | None = None
        self._secret = secret
        try:
            self._client = sdk.Anthropic(
                api_key=secret.reveal(), timeout=TIMEOUT_SECONDS, max_retries=1
            )
        except Exception as error:
            raise self._failure(
                "the provider client could not be set up", error
            ) from None

    def __repr__(self) -> str:
        return f"AnthropicClient(model={self.model!r}, key={self._secret!r})"

    def _failure(self, what: str, error: Exception) -> ProviderError:
        """A ``ProviderError`` for ``error``, with the key removed. Raise it
        with ``from None`` so that the SDK's own message chain is dropped."""
        text = redact(f"{type(error).__name__}: {error}", self._secret)
        return ProviderError(f"{what}: {text}")

    def complete(
        self, system: str, conversation: Sequence[Turn], tools: Sequence[ToolSpec]
    ) -> ModelMessage:
        request = build_request(self.model, system, conversation, tools)
        self.last_usage = None
        try:
            response = self._client.messages.create(**request)
            data = response.model_dump()
            self.last_usage = parse_usage(data)
            return parse_response(data)
        except Exception as error:
            raise self._failure("the provider request failed", error) from None


def make_client(model: str | None = None) -> AnthropicClient:
    """The client for the key in ``ANTHROPIC_API_KEY``, for ``model``, else
    the model in ``PBC_ANTHROPIC_MODEL``, else ``MODEL``."""
    setup = f"run: uv sync --extra {GROUP}, and export {KEY_VARIABLE}"
    try:
        secret = Secret.from_environment(KEY_VARIABLE)
    except MissingKey as error:
        raise MissingKey(f"{error} The Claude client needs: {setup}.") from None
    try:
        import anthropic
    except ImportError:
        raise ProviderError(
            f"the anthropic package is not installed; {setup}"
        ) from None
    chosen = model or read_setting(MODEL_VARIABLE) or MODEL
    return AnthropicClient(secret, anthropic, chosen)
