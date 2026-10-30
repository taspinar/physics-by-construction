"""Lesson D5: an unknown physical world of three bodies (F99;
``docs/discovery-protocol.md``, "Unknown worlds").

The protocol of the lesson, fixed before the run was recorded, the frozen
run, and its score recomputed from the tool calls. An agent places three
bodies at rest in a world whose pair forces are hidden
(``pbc.discovery.worlds``), reads their accelerations, and states the
couplings of the pairs and the exponent of the distance. The build starts
the bodies in motion from starts nobody probed and scores the positions the
claim predicts against the hidden world's.

The run is a replay fixture next to the page (ADR 002); its version record,
the ``TraceInfo``, is kept here and checked against the fixture. The hidden
couplings, the exponent, and the held-out starts are the judge's
configuration: no prompt, tool, or page shows them.
"""

import argparse
import datetime
import math
import sys
from pathlib import Path

import numpy as np

from pbc.agents.loop import MAX_CALLS_PER_MESSAGE, Step, Transcript, run
from pbc.agents.replay import Recording, load_recording, replay, save_recording
from pbc.agents.tools import Allowlist
from pbc.discovery.baselines import BaselineResult
from pbc.discovery.protocol import (
    PROMPT_VERSION,
    CostRecord,
    Score,
    TraceInfo,
    prompt_sha,
)
from pbc.discovery.worlds import (
    ACCELERATIONS,
    BOUND,
    CLOSEST,
    MASSES,
    NAMES,
    SIGMA,
    PairForceWorld,
    Probes,
    fit_family,
    newton,
    random_configurations,
    sparse_pairs,
    world_allowlist,
)

BUDGET = 12  # configurations
MAX_STEPS = 12
TOLERANCE = 0.02  # relative position error that counts as a correct prediction
SEED = 0
REPLAY_TOLERANCE = 1e-9
PROTOCOL = "f99-unknown-world-1"
CONDITION = "full"  # told the form of the pair force, not its couplings
# The judge's configuration: the hidden law. Never on a page.
WORLD = {"k12": 1.37, "k13": -0.82, "k23": 2.91, "exponent": 1.62}

# Who produced the recording, and when (the plan of Issue #336, "Recording").
MODEL = "claude-opus-5-5 in a Claude Code session"
RECORDED = "2026-10-29"
FIXTURE = "replay.json"


def world(budget: int = BUDGET) -> PairForceWorld:
    """A fresh world of the protocol."""
    return PairForceWorld(**WORLD, budget=budget, seed=SEED)


def allowlist() -> Allowlist:
    """The tools of a fresh world."""
    return world_allowlist(world())[0]


def prompts() -> tuple[str, str]:
    """The system prompt and the task. Nothing of the hidden law is in
    them."""
    masses = ", ".join(f"{m:g}" for m in MASSES)
    system = (
        "You study a physical system by measuring it. Use only the tools you are"
        f" given. You have {BUDGET} configurations."
    )
    task = (
        f"Three bodies of masses {masses} kg move in a plane. Each pair of bodies"
        " attracts or repels along the line between them with a force"
        " k r^-p, where r is their distance, k is a coupling of that pair"
        " (positive for attraction), and the exponent p is the same for every"
        " pair. Place the bodies at rest at positions with each coordinate from"
        f" {-BOUND:g} to {BOUND:g} m, no two closer than {CLOSEST:g} m, and read"
        " their accelerations, which have noise. Find k12, k13, k23, and p, and"
        " submit them. Your claim is scored by how well it predicts the motion"
        " of the bodies from starts you cannot probe."
    )
    return system, task


INFO = TraceInfo(
    protocol=PROTOCOL,
    environment=PairForceWorld.name,
    condition=CONDITION,
    seed=SEED,
    prompt_version=PROMPT_VERSION,
    prompt_sha256=prompt_sha(*prompts()),
    model=MODEL,
    recorded=RECORDED,
    # The sub-agent's session reported no token counts and no price.
    cost=CostRecord(3, 5, None, None, None),
)


def score_run(transcript: Transcript) -> Score:
    """Score ``transcript`` by running its tool calls again on a fresh world:
    the last accepted claim is judged on the held-out starts."""
    tools, claims = world_allowlist(world())
    used = refused = 0
    for step in transcript.steps:
        for number, call in enumerate(step.message.tool_calls):
            # The loop refuses the calls of a message beyond its limit unrun.
            if number >= MAX_CALLS_PER_MESSAGE:
                refused += 1
                continue
            result = tools.dispatch(call)
            if not result.ok:
                refused += 1
            elif call.name == ACCELERATIONS:
                used += 1
    claim = claims[-1] if claims else None
    error = math.inf if claim is None else world().held_out_error(claim)
    recovered = transcript.finished and error <= TOLERANCE
    return Score(SEED, used, refused, claim, error, recovered)


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
    transcript = replay(
        recording,
        allowlist(),
        system=system,
        task=task,
        tolerance=REPLAY_TOLERANCE,
        max_steps=MAX_STEPS,
        rerecord=record_command(),
    )
    return recording, transcript, score_run(transcript)


def agent_probes(transcript: Transcript) -> Probes:
    """The configurations the agent probed, with the accelerations the
    replay recomputed."""
    positions, found = [], []
    for step in transcript.steps:
        for call, result in zip(step.message.tool_calls, step.results, strict=True):
            if call.name == ACCELERATIONS and result.ok:
                positions.append([call.arguments[n] for n in NAMES])
                found.append(
                    [result.content[f"a{axis}{b}"] for b in (1, 2, 3) for axis in "xy"]
                )
    shape = (len(positions), 3, 2)
    return Probes(
        np.array(positions, dtype=float).reshape(shape),
        np.array(found, dtype=float).reshape(shape),
        SIGMA,
    )


def baselines() -> tuple[BaselineResult, ...]:
    """The baselines without a model with the protocol's budget, on random
    configurations: least squares of the family, sparse identification over
    whole powers, and Newton's gravity."""
    w = world()
    data = random_configurations(w, SEED)
    return (
        fit_family(w, data, "random + least squares"),
        sparse_pairs(w, data, name="random + sparse identification"),
        newton(w, data, "random + Newton's gravity"),
    )


def recovered(result: BaselineResult) -> bool:
    """Whether a baseline predicts the motion: a fit consistent with the
    noise whose prediction is within the tolerance."""
    return result.success and result.held_out_error <= TOLERANCE


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
    transcript = run(client, allowlist(), system, task, MAX_STEPS, on_step=_show)
    score = score_run(transcript)
    print(f"\nPrediction error {score.held_out_error:.3g}: {score.outcome}\n")
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
