"""Lesson D13: discovering conservation laws (F82; ``docs/discovery-protocol.md``,
"Invariants").

The protocol of the lesson, fixed before the run was recorded, the frozen
run, and its score recomputed from the tool calls. An agent starts a box (a
particle in a plane under a hidden force, ``pbc.discovery.invariants``)
from starts of its choice, tests candidate conserved quantities on its own
trajectories, and submits at most three. The build judges each on
trajectories nobody started, under three integration settings, and counts
the independent invariants among them against the number the box has.

The run is a replay fixture next to the page (ADR 002); its version record,
the ``TraceInfo``, is kept here and checked against the fixture. The hidden
force is the judge's configuration: no prompt, tool, or page shows it.
"""

import argparse
import datetime
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from pbc.agents.loop import MAX_CALLS_PER_MESSAGE, Step, Transcript, run
from pbc.agents.replay import Recording, load_recording, replay, save_recording
from pbc.discovery.invariants import (
    INVARIANT,
    PLANAR_LIBRARY,
    PLANAR_TERMS,
    REFERENCE,
    TRAJECTORY,
    CentralBox,
    Verdict,
    box_allowlist,
    independent,
)
from pbc.discovery.protocol import PROMPT_VERSION, CostRecord, TraceInfo, prompt_sha

BUDGET = 6  # trajectories
MAX_CANDIDATES = 3
MAX_STEPS = 12
TOLERANCE = 0.01  # conservation ratio that counts as conserved
SEED = 0  # the box has no noise; the seed versions the run as in F65
REPLAY_TOLERANCE = 1e-9
PROTOCOL = "f82-invariants-1"
CONDITION = "partial"  # told the terms to use, not the force
# The judge's configuration: the hidden force. Never on a page.
WORLD = {"k": 2.0, "b": 1.5}

# Who produced the recording, and when (the plan of Issue #294, "Recording").
MODEL = "claude-opus-5-5 in a Claude Code session"
RECORDED = "2026-10-26"
FIXTURE = "replay.json"


def box(budget: int = BUDGET) -> CentralBox:
    """A fresh box of the protocol."""
    return CentralBox(**WORLD, budget=budget)


def prompts() -> tuple[str, str]:
    """The system prompt and the task. Nothing of the force is in them."""
    b = CentralBox.bound
    terms = ", ".join(PLANAR_TERMS.values())
    system = (
        "You study a physical system by watching it. Use only the tools you are"
        f" given. You have {BUDGET} trajectories."
    )
    task = (
        "The system is a particle in a plane. Start it at a position x, y (m) and"
        f" a velocity vx, vy (m/s), each from {-b:g} to {b:g}, and read its state"
        " at fixed times. Find the quantities that stay constant along every"
        " trajectory, each written as a sum of the terms"
        f" {terms} with coefficients. You may test a candidate on your"
        f" trajectories with the variation tool. Submit at most {MAX_CANDIDATES}"
        " candidates. They are tested on trajectories you cannot start, which"
        " are also integrated in another way, and scored by how many independent"
        " conserved quantities they contain."
    )
    return system, task


INFO = TraceInfo(
    protocol=PROTOCOL,
    environment=CentralBox.name,
    condition=CONDITION,
    seed=SEED,
    prompt_version=PROMPT_VERSION,
    prompt_sha256=prompt_sha(*prompts()),
    model=MODEL,
    recorded=RECORDED,
    # The sub-agent's session reported no token counts and no price.
    cost=CostRecord(4, 8, None, None, None),
)


@dataclass(frozen=True)
class Score:
    """The score of a run, recomputed from its tool calls."""

    trajectories: int  # accepted trajectory calls, at most the budget
    refused: int  # calls the harness refused
    candidates: tuple[Mapping[str, float], ...]  # by term name, zeros left out
    verdicts: tuple[Verdict, ...]
    found: int  # independent invariants among the candidates
    known: int  # independent invariants of the box in the library
    finished: bool

    @property
    def recovered(self) -> bool:
        return self.finished and self.found == self.known

    @property
    def outcome(self) -> str:
        if not self.candidates:
            return "no claim"
        return "recovered" if self.recovered else "not recovered"


def score_run(transcript: Transcript) -> Score:
    """Score ``transcript`` by running its tool calls again on a fresh box:
    every submitted candidate is judged on the held-out trajectories, with
    the agent's own trajectories as its training set."""
    world = box()
    allowlist, submitted = box_allowlist(world, MAX_CANDIDATES)
    used = refused = 0
    for step in transcript.steps:
        for number, call in enumerate(step.message.tool_calls):
            # The loop refuses the calls of a message beyond its limit unrun.
            if number >= MAX_CALLS_PER_MESSAGE:
                refused += 1
                continue
            result = allowlist.dispatch(call)
            if not result.ok:
                refused += 1
            elif call.name == TRAJECTORY:
                used += 1
    verdicts = tuple(world.judge(c, TOLERANCE, world.probed) for c in submitted)
    kept = [
        c for c, v in zip(submitted, verdicts, strict=True) if v.verdict == INVARIANT
    ]
    found = independent(kept, PLANAR_LIBRARY, world.held_out(REFERENCE))
    candidates = tuple(
        {t: float(x) for t, x in zip(PLANAR_LIBRARY, c, strict=True) if x != 0.0}
        for c in submitted
    )
    return Score(
        used,
        refused,
        candidates,
        verdicts,
        found,
        world.known_invariants(TOLERANCE),
        transcript.finished,
    )


def record_command() -> str:
    return f"uv run --extra openai python -m {__name__} --record"


def replay_run(directory: Path = Path()) -> tuple[Recording, Transcript, Score]:
    """Replay the fixture in ``directory`` against the current code and score
    it again.

    Raises ``ValueError`` when the fixture and ``INFO`` disagree on the model,
    the date, or the prompt, and ``ReplayMismatch`` when a recomputed tool
    result differs from the recorded one."""
    recording = load_recording(directory / FIXTURE)
    system, task = prompts()
    if (recording.model, recording.recorded) != (INFO.model, INFO.recorded):
        raise ValueError(f"{FIXTURE} is not the run recorded for {PROTOCOL}")
    if prompt_sha(recording.system, recording.task) != INFO.prompt_sha256:
        raise ValueError(f"{FIXTURE} was recorded with another prompt")
    allowlist, _ = box_allowlist(box(), MAX_CANDIDATES)
    transcript = replay(
        recording,
        allowlist,
        system=system,
        task=task,
        tolerance=REPLAY_TOLERANCE,
        max_steps=MAX_STEPS,
        rerecord=record_command(),
    )
    return recording, transcript, score_run(transcript)


def agent_trajectories(transcript: Transcript) -> list[np.ndarray]:
    """The trajectories the agent started, as the replay recomputed them:
    the states at the box's times, one row per instant."""
    world = box()
    names = [f"{s}({t:g})" for t in world.times for s in ("x", "y", "vx", "vy")]
    found = []
    for step in transcript.steps:
        for call, result in zip(step.message.tool_calls, step.results, strict=True):
            if call.name == TRAJECTORY and result.ok:
                flat = np.array([result.content[name] for name in names])
                found.append(flat.reshape(len(world.times), 4))
    return found


def _show(step: Step) -> None:
    if step.message.text:
        print(step.message.text)
    for call, result in zip(step.message.tool_calls, step.results, strict=False):
        print(f"  {call.name}({call.arguments}) -> {dict(result.content)}")


def main(argv: list[str] | None = None) -> int:
    """The live entry point: run the lesson's agent with the provider's
    model, print it and its score, and optionally record it over the fixture
    in the current directory."""
    from pbc.agents.providers import PROVIDER, load_client

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--record", action="store_true")
    options = parser.parse_args(argv)
    try:
        client = load_client(PROVIDER)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    system, task = prompts()
    print(f"Task: {task}\nModel: {client.model}\n")
    allowlist, _ = box_allowlist(box(), MAX_CANDIDATES)
    transcript = run(client, allowlist, system, task, MAX_STEPS, on_step=_show)
    score = score_run(transcript)
    for candidate, verdict in zip(score.candidates, score.verdicts, strict=True):
        print(f"{candidate}: {verdict.verdict}")
    print(f"\n{score.found} of {score.known} invariants: {score.outcome}\n")
    if options.record:
        today = datetime.date.today().isoformat()
        save_recording(Path(FIXTURE), transcript, today, *client.secrets)
        print(
            f"Recorded to {FIXTURE}. Review it, then set MODEL, RECORDED"
            f" ({today}), and the cost of the run in INFO of {__name__}."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
