"""The agent reviewer of the workspace (ADR 004 harness), its placeholder
policy, its recording, and its replay.

The agent's whole reach is one allowlisted tool, ``run_check``: the name of
one of the scripted reviewer's checks (``review.NAMES``), recomputed from
the project's records; it returns whether the check passed and its number,
nothing else. The agent's answer names the checks it proposes as findings
on a last line ``FINDINGS: <name>, ...``; each enters the follow-up log as
``proposed`` and is accepted only when its recomputed check confirms it
(``log.Log.accept``), never on the agent's word. An agent's agreement is
never "independently checked".

Without a model account the role is replayed from its fixture in
``products/research-workspace/fixtures/`` (ADR 022 decision 8): every
recorded call is executed again against the project and compared. The
committed fixture was written by ``ScriptedReviewer``, a deterministic
policy and not a model, and is labelled a placeholder; the owner or the
supervisor records real ones (``record``), each in a pull request of its
own.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pbc.agents.loop import MAX_CALLS_PER_MESSAGE, Transcript, run
from pbc.agents.messages import ModelMessage, ToolCall, ToolResult, ToolSpec, Turn
from pbc.agents.replay import load_recording, replay, save_recording
from pbc.agents.secrets import Secret
from pbc.agents.tools import Allowlist, Choice, Tool
from pbc.data import REPO_ROOT
from pbc.products.research_workspace import log as worklog
from pbc.products.research_workspace import review

SYSTEM = (
    "You review the report of a reproduction of a published spectrum fit. You"
    " can recompute the reviewer's checks through one tool, run_check, which"
    " returns passed (1 passed, 0 failed, -1 undecided) and the check's number."
    " You cannot change the records. Propose as findings only checks that"
    " failed when you ran them, on a last line 'FINDINGS: <names>' or"
    " 'FINDINGS: none'."
)
TOLERANCE = 1e-9
MAX_STEPS = 4
FINDINGS = "FINDINGS:"
FIXTURE = REPO_ROOT / "products/research-workspace/fixtures/reproduction-reviewer.json"
RERECORD = (
    "uv run --locked python -m pbc.products.research_workspace record --project"
    " <project> --scripted --out products/research-workspace/fixtures/"
    "reproduction-reviewer.json"
)


def task(budget: int) -> str:
    return (
        "Review the reproduction report of the COBE FIRAS spectrum fit. Run the"
        f" checks you need, at most {budget}, and propose the failing ones as"
        " findings. The checks: " + ", ".join(review.NAMES) + "."
    )


def tools(context: review.Context, budget: int) -> Allowlist:
    def run_check(name: str) -> dict[str, float]:
        result = review.run_check(name, context)
        code = {True: 1.0, False: 0.0, None: -1.0}[result.passed]
        return {"passed": code, "value": float(result.value)}

    tool = Tool(
        name="run_check",
        description="Recompute one check of the scripted reviewer from the records.",
        parameters=(Choice("name", "the check to recompute", review.NAMES),),
        function=run_check,
    )
    return Allowlist((tool,), budget=budget)


@dataclass
class ScriptedReviewer:
    """A deterministic policy in the shape of a model client: every check, as
    many per message as the harness allows, then the failing ones as
    findings. Not a model; no key."""

    model: str = "placeholder: scripted policy, not a model"
    secrets: tuple[Secret, ...] = ()

    def complete(
        self, system: str, conversation: Sequence[Turn], tools: Sequence[ToolSpec]
    ) -> ModelMessage:
        asked = [t for t in conversation if isinstance(t, ModelMessage)]
        step = len(asked)
        batch = review.NAMES[
            step * MAX_CALLS_PER_MESSAGE : (step + 1) * MAX_CALLS_PER_MESSAGE
        ]
        if batch:
            calls = tuple(
                ToolCall(f"call-{step}-{n}", "run_check", {"name": name})
                for n, name in enumerate(batch)
            )
            return ModelMessage("", calls)
        results = [t for t in conversation if isinstance(t, ToolResult)]
        calls = {c.id: c for m in asked for c in m.tool_calls}
        failing = [
            calls[r.call_id].arguments["name"]
            for r in results
            if r.ok and r.content["passed"] == 0.0
        ]
        listed = ", ".join(failing) or "none"
        return ModelMessage(
            f"I ran {len(results)} checks; {len(failing)} failed.\n{FINDINGS} {listed}",
            (),
        )


def proposed(transcript: Transcript) -> list[str]:
    """The checks the agent's last message proposes as findings."""
    text = transcript.steps[-1].message.text if transcript.steps else ""
    lines = [line for line in text.splitlines() if line.startswith(FINDINGS)]
    if not lines:
        return []
    names = [n.strip() for n in lines[-1][len(FINDINGS) :].split(",")]
    return [n for n in names if n and n != "none"]


def record(
    context: review.Context, client, path: Path, recorded: str, *, placeholder: bool
) -> Transcript:
    budget = len(review.NAMES)
    transcript = run(client, tools(context, budget), SYSTEM, task(budget), MAX_STEPS)
    save_recording(path, transcript, recorded, *client.secrets, placeholder=placeholder)
    return transcript


def replay_review(context: review.Context, path: Path = FIXTURE) -> Transcript:
    """Replay the fixture against ``context``; every tool call recomputed."""
    budget = len(review.NAMES)
    return replay(
        load_recording(path),
        tools(context, budget),
        system=SYSTEM,
        task=task(budget),
        tolerance=TOLERANCE,
        max_steps=MAX_STEPS,
        rerecord=RERECORD,
    )


def enter(
    transcript: Transcript, context: review.Context, log: worklog.Log, by: str
) -> list[str]:
    """Enter the agent's proposed findings in the log, and accept each only
    through its recomputed check. Returns the accepted keys."""
    accepted = []
    held = log.findings()
    for name in proposed(transcript):
        if name not in review.NAMES:
            continue  # a name outside the list is never looked up
        definition = next(c for c in review.CHECKS if c.name == name)
        key = f"agent-{name}"
        if key not in held:
            log.find(
                key,
                definition.claim,
                transcript.model,
                definition.finding,
                definition.kind,
                name,
            )
        result = review.run_check(name, context)
        try:
            log.accept(key, result.passed, by)
            accepted.append(key)
        except worklog.LogRefused:
            pass  # kept as proposed: its check does not confirm it
    return accepted
