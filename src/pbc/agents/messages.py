"""The data that crosses the provider interface.

Everything here is plain data. A model client turns the conversation into a
provider request and the provider's response into a ``ModelMessage``; nothing
else of a provider reaches the harness.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from pbc.agents.secrets import Secret


@dataclass(frozen=True)
class ToolCall:
    """One tool call the model requested.

    ``arguments`` is whatever the model sent. It is untrusted: the allowlist
    validates it before anything runs.
    """

    id: str
    name: str
    arguments: Any


@dataclass(frozen=True)
class ModelMessage:
    """One assistant message: some text and zero or more tool calls."""

    text: str
    tool_calls: tuple[ToolCall, ...] = ()


@dataclass(frozen=True)
class ToolResult:
    """What came back for one tool call.

    ``ok`` is False when the call was rejected before it ran or the function
    refused its input; ``content`` then holds only an ``error`` text.
    """

    call_id: str
    name: str
    ok: bool
    content: Mapping[str, Any]


@dataclass(frozen=True)
class UserTurn:
    """The task, as the human gave it."""

    text: str


Turn = UserTurn | ModelMessage | ToolResult


@dataclass(frozen=True)
class ToolSpec:
    """A tool as the model sees it: a name, a description, and a JSON schema
    of the arguments."""

    name: str
    description: str
    parameters: Mapping[str, Any]


class ModelClient(Protocol):
    """The only provider-facing surface of the harness.

    A client names its model, holds its credentials, and returns the next
    assistant message for a conversation. The harness removes every secret in
    ``secrets`` from each message before anything else sees it. Switching
    provider means writing one class with this shape (``pbc.agents.clients``).
    """

    model: str
    secrets: tuple[Secret, ...]

    def complete(
        self, system: str, conversation: Sequence[Turn], tools: Sequence[ToolSpec]
    ) -> ModelMessage: ...
