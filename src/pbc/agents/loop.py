"""The run loop: ask the model, validate and run its tool calls, repeat."""

from collections.abc import Callable
from dataclasses import dataclass

from pbc.agents.messages import (
    ModelClient,
    ModelMessage,
    ToolCall,
    ToolResult,
    Turn,
    UserTurn,
)
from pbc.agents.secrets import Secret, redact_data
from pbc.agents.tools import Allowlist

# More calls in one message than this are refused, not run.
MAX_CALLS_PER_MESSAGE = 4


@dataclass(frozen=True)
class Step:
    """One model message and the results of its tool calls."""

    message: ModelMessage
    results: tuple[ToolResult, ...]


@dataclass(frozen=True)
class Transcript:
    """A run: who ran it, the task, and the steps.

    ``finished`` is True when the model ended the run with a message that
    requests no tool, False when the step limit stopped it.
    """

    model: str
    system: str
    task: str
    steps: tuple[Step, ...]
    finished: bool


def sanitize(message: ModelMessage, secrets: tuple[Secret, ...]) -> ModelMessage:
    """``message`` with every secret removed from its text and tool calls."""
    if not secrets:
        return message
    return ModelMessage(
        text=redact_data(message.text, *secrets),
        tool_calls=tuple(
            ToolCall(
                id=redact_data(call.id, *secrets),
                name=redact_data(call.name, *secrets),
                arguments=redact_data(call.arguments, *secrets),
            )
            for call in message.tool_calls
        ),
    )


def run(
    client: ModelClient,
    allowlist: Allowlist,
    system: str,
    task: str,
    max_steps: int,
    on_step: Callable[[Step], None] | None = None,
) -> Transcript:
    """Run the agent for at most ``max_steps`` model messages.

    Each message is first cleared of the client's secrets, so that a key the
    model repeats reaches no transcript, callback, or later request. Each tool
    call of each message is then validated against ``allowlist`` and run if
    it passes; the results go back to the model in the next request.
    """
    if max_steps < 1:
        raise ValueError(f"max_steps must be at least 1, got {max_steps}")
    conversation: list[Turn] = [UserTurn(task)]
    steps: list[Step] = []
    finished = False
    for _ in range(max_steps):
        message = sanitize(
            client.complete(system, conversation, allowlist.specs()), client.secrets
        )
        results = []
        for number, call in enumerate(message.tool_calls):
            if number >= MAX_CALLS_PER_MESSAGE:
                results.append(
                    ToolResult(
                        call_id=str(call.id),
                        name=str(call.name),
                        ok=False,
                        content={
                            "error": f"at most {MAX_CALLS_PER_MESSAGE} tool calls"
                            " per message"
                        },
                    )
                )
            else:
                results.append(allowlist.dispatch(call))
        step = Step(message, tuple(results))
        steps.append(step)
        if on_step is not None:
            on_step(step)
        conversation.append(message)
        conversation.extend(results)
        if not message.tool_calls:
            finished = True
            break
    return Transcript(
        model=client.model,
        system=system,
        task=task,
        steps=tuple(steps),
        finished=finished,
    )
