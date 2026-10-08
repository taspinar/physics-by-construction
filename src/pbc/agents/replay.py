"""Record a run, and replay it without a model (ADR 004).

A ``Recording`` is the replay fixture of an agent lesson: the model's
messages of one live run and, for each tool call, the result of that run. It
holds no credential and no provider request data.

``replay`` feeds the recorded messages to the harness through a client that
needs no network and no key. Every tool call is executed again, against the
current code, and the new result is compared with the recorded one. Only the
recomputed results are ever shown (``pbc.agents.display``).
"""

import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pbc.agents.loop import Step, Transcript, run
from pbc.agents.messages import ModelMessage, ToolCall, ToolResult, ToolSpec, Turn
from pbc.agents.secrets import Secret, redact
from pbc.agents.tools import Allowlist

FORMAT = 1


class ReplayMismatch(AssertionError):
    """A replay that no longer matches its recording."""


@dataclass(frozen=True)
class Recording:
    """A committed recording of one live run."""

    model: str  # the model that produced the messages
    recorded: str  # the date of the run, YYYY-MM-DD
    system: str
    task: str
    steps: tuple[Step, ...]  # recorded messages and recorded tool results
    placeholder: bool = False  # True: written by hand, not a model run


class ReplayClient:
    """A model client that returns the recorded messages in order."""

    secrets: tuple[Secret, ...] = ()  # a replay holds no credential

    def __init__(self, recording: Recording):
        self.model = recording.model
        self._messages = [step.message for step in recording.steps]

    def complete(
        self, system: str, conversation: Sequence[Turn], tools: Sequence[ToolSpec]
    ) -> ModelMessage:
        if not self._messages:
            raise ReplayMismatch("the run asked for more messages than were recorded")
        return self._messages.pop(0)


def _encode(transcript: Transcript, recorded: str, placeholder: bool) -> dict:
    data: dict[str, Any] = {
        "format": FORMAT,
        "model": transcript.model,
        "recorded": recorded,
        "system": transcript.system,
        "task": transcript.task,
        "steps": [
            {
                "text": step.message.text,
                "tool_calls": [
                    {"id": c.id, "name": c.name, "arguments": c.arguments}
                    for c in step.message.tool_calls
                ],
                "results": [
                    {"call_id": r.call_id, "ok": r.ok, "content": dict(r.content)}
                    for r in step.results
                ],
            }
            for step in transcript.steps
        ],
    }
    if placeholder:
        data["placeholder"] = True
    return data


def save_recording(
    path: Path,
    transcript: Transcript,
    recorded: str,
    *secrets: Secret,
    placeholder: bool = False,
) -> None:
    """Write ``transcript`` to ``path`` as a replay fixture.

    Every occurrence of a secret in the text is replaced first, so that a key
    cannot reach the file even if a model repeated it.
    """
    text = json.dumps(_encode(transcript, recorded, placeholder), indent=2)
    path.write_text(redact(text, *secrets) + "\n", encoding="utf-8")


def _require(condition: bool, path: Path, what: str) -> None:
    if not condition:
        raise ValueError(f"{path} is not a replay fixture: {what}")


def load_recording(path: Path) -> Recording:
    """Read a replay fixture, rejecting anything that is not exactly one."""
    data = json.loads(path.read_text(encoding="utf-8"))
    allowed = {"format", "model", "recorded", "system", "task", "steps", "placeholder"}
    _require(isinstance(data, dict), path, "the top level is not an object")
    _require(data.get("format") == FORMAT, path, f"format is not {FORMAT}")
    _require(set(data) <= allowed, path, f"unknown keys {sorted(set(data) - allowed)}")
    for key in ("model", "recorded", "system", "task"):
        _require(isinstance(data.get(key), str), path, f"{key} is not a text")
    _require(isinstance(data.get("steps"), list), path, "steps is not a list")
    steps = []
    for item in data["steps"]:
        _require(
            isinstance(item, dict) and set(item) == {"text", "tool_calls", "results"},
            path,
            "a step needs exactly text, tool_calls, and results",
        )
        calls = tuple(
            ToolCall(id=c["id"], name=c["name"], arguments=c["arguments"])
            for c in item["tool_calls"]
        )
        results = tuple(
            ToolResult(
                call_id=r["call_id"], name=c.name, ok=r["ok"], content=r["content"]
            )
            for r, c in zip(item["results"], calls, strict=True)
        )
        steps.append(Step(ModelMessage(item["text"], calls), results))
    return Recording(
        model=data["model"],
        recorded=data["recorded"],
        system=data["system"],
        task=data["task"],
        steps=tuple(steps),
        placeholder=bool(data.get("placeholder", False)),
    )


def _close(recorded: Any, recomputed: Any, tolerance: float) -> bool:
    if isinstance(recorded, bool) or isinstance(recomputed, bool):
        return recorded == recomputed
    if isinstance(recorded, int | float) and isinstance(recomputed, int | float):
        return math.isclose(recorded, recomputed, rel_tol=tolerance, abs_tol=tolerance)
    return recorded == recomputed


def _differences(
    recorded: ToolResult, recomputed: ToolResult, tolerance: float
) -> str | None:
    if recorded.ok != recomputed.ok:
        was, now = ("accepted", "rejected") if recorded.ok else ("rejected", "accepted")
        return f"the call was {was} when recorded and is {now} now"
    if not recorded.ok:
        return None  # the wording of a refusal is not part of the contract
    if set(recorded.content) != set(recomputed.content):
        return (
            f"the result names {sorted(recorded.content)} when recorded and"
            f" {sorted(recomputed.content)} now"
        )
    for key, was in recorded.content.items():
        now = recomputed.content[key]
        if not _close(was, now, tolerance):
            return f"{key} was {was!r} when recorded and is {now!r} now"
    return None


def replay(
    recording: Recording,
    allowlist: Allowlist,
    *,
    system: str,
    task: str,
    tolerance: float,
    max_steps: int,
    rerecord: str,
) -> Transcript:
    """Run the recording again and check the recomputed tool results.

    Returns the transcript of the replay, whose tool results are the
    recomputed ones. Raises ``ReplayMismatch`` when the lesson's task or
    system prompt changed, or a recomputed result differs from the recorded
    one by more than ``tolerance`` (relative and absolute), and says how to
    re-record with ``rerecord``, the command to run.
    """
    how = f" If the change is intended, record the run again with: {rerecord}"
    if recording.task != task or recording.system != system:
        raise ReplayMismatch(
            "the task or system prompt of the lesson differs from the recording." + how
        )
    transcript = run(ReplayClient(recording), allowlist, system, task, max_steps)
    if len(transcript.steps) != len(recording.steps):
        raise ReplayMismatch(
            f"the replay has {len(transcript.steps)} steps, the recording"
            f" {len(recording.steps)}." + how
        )
    for number, (was, now) in enumerate(
        zip(recording.steps, transcript.steps, strict=True), start=1
    ):
        for old, new in zip(was.results, now.results, strict=True):
            difference = _differences(old, new, tolerance)
            if difference is not None:
                raise ReplayMismatch(
                    f"step {number}, tool {new.name}: {difference}"
                    f" (tolerance {tolerance:g})." + how
                )
    return transcript
