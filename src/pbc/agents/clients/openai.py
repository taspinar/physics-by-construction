"""The live client for the default provider, OpenAI (chat completions).

It runs only on a learner's machine. The key is read from the environment
variable ``OPENAI_API_KEY`` and used for nothing but the provider request.
Errors from the SDK, when it is set up and when it is asked, are re-raised
without the SDK's own message chain, with the key removed, because an SDK may
echo the request or its configuration in an error.

The SDK is an optional dependency (``uv sync --extra openai``). Building the
request and reading the response are plain functions, tested without it.
"""

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
from pbc.agents.secrets import Secret, redact

KEY_VARIABLE = "OPENAI_API_KEY"
# The model the lessons are recorded with. A recording names the model that
# produced it, so changing this does not change a recording.
MODEL = "gpt-5"
TIMEOUT_SECONDS = 60.0


class ProviderError(RuntimeError):
    """The provider request failed. The message never contains the key."""


def build_request(
    model: str, system: str, conversation: Sequence[Turn], tools: Sequence[ToolSpec]
) -> dict[str, Any]:
    """The arguments of one chat completion request."""
    messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for turn in conversation:
        if isinstance(turn, UserTurn):
            messages.append({"role": "user", "content": turn.text})
        elif isinstance(turn, ModelMessage):
            message: dict[str, Any] = {"role": "assistant", "content": turn.text}
            if turn.tool_calls:
                message["tool_calls"] = [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": json.dumps(call.arguments),
                        },
                    }
                    for call in turn.tool_calls
                ]
            messages.append(message)
        elif isinstance(turn, ToolResult):
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": turn.call_id,
                    "content": json.dumps(dict(turn.content)),
                }
            )
    return {
        "model": model,
        "messages": messages,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": dict(tool.parameters),
                },
            }
            for tool in tools
        ],
    }


def parse_response(response: Mapping[str, Any]) -> ModelMessage:
    """The assistant message of a chat completion response.

    Arguments the provider sent that are not valid JSON are kept as text; the
    allowlist rejects them.
    """
    message = response["choices"][0]["message"]
    calls = []
    for call in message.get("tool_calls") or []:
        raw = call["function"]["arguments"]
        try:
            arguments: Any = json.loads(raw)
        except TypeError, ValueError:
            arguments = raw
        calls.append(
            ToolCall(id=call["id"], name=call["function"]["name"], arguments=arguments)
        )
    return ModelMessage(text=message.get("content") or "", tool_calls=tuple(calls))


class OpenAIClient:
    """A ``ModelClient`` that calls the provider with the learner's key."""

    def __init__(self, secret: Secret, sdk: Any, model: str = MODEL):
        self.model = model
        self.secrets = (secret,)
        self._secret = secret
        try:
            self._client = sdk.OpenAI(
                api_key=secret.reveal(), timeout=TIMEOUT_SECONDS, max_retries=1
            )
        except Exception as error:
            raise self._failure(
                "the provider client could not be set up", error
            ) from None

    def __repr__(self) -> str:
        return f"OpenAIClient(model={self.model!r}, key={self._secret!r})"

    def _failure(self, what: str, error: Exception) -> ProviderError:
        """A ``ProviderError`` for ``error``, with the key removed. Raise it
        with ``from None`` so that the SDK's own message chain is dropped."""
        text = redact(f"{type(error).__name__}: {error}", self._secret)
        return ProviderError(f"{what}: {text}")

    def complete(
        self, system: str, conversation: Sequence[Turn], tools: Sequence[ToolSpec]
    ) -> ModelMessage:
        request = build_request(self.model, system, conversation, tools)
        try:
            response = self._client.chat.completions.create(**request)
            return parse_response(response.model_dump())
        except Exception as error:
            raise self._failure("the provider request failed", error) from None


def make_client() -> OpenAIClient:
    """The client for the key in ``OPENAI_API_KEY``."""
    secret = Secret.from_environment(KEY_VARIABLE)
    try:
        import openai
    except ImportError:
        raise ProviderError(
            "the openai package is not installed; run: uv sync --extra openai"
        ) from None
    return OpenAIClient(secret, openai)
