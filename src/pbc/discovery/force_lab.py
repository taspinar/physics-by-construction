"""Lessons D1 to D3: black-box force laws (F66; ``docs/discovery-protocol.md``).

Three protocols of the Discovery evaluation protocol, fixed before any run was
recorded, and the frozen runs of the lessons:

- ``black-box`` (D1): the central force, an unknown law; the agent is told the
  names of the parameters to report (``partial``).
- ``prior-knowledge`` (D2): the oscillator, whose spring force is seen only
  through the motion, under the three conditions of prior knowledge. One
  protocol object serves all three, so the model, the tools, the budget, the
  step limit, the seed, and the held-out settings are the same; only the task
  text differs.
- ``modified`` (D3): the central force with a modified law, and the familiar
  inverse-square law fitted to the same probes as a baseline of its own.

Each run is a replay fixture next to its page (ADR 002). Its version record,
the ``TraceInfo`` of the protocol, is kept here, because a lesson directory
holds nothing but the page and its fixtures; ``replay_run`` checks the two
against each other. The hidden worlds are the judge's configuration: no
prompt, tool, or page shows them.
"""

import argparse
import datetime
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from pbc.agents.loop import Step, Transcript, run
from pbc.agents.replay import Recording, load_recording, replay, save_recording
from pbc.agents.tools import Allowlist
from pbc.data.fit import FitResult, fit_curve
from pbc.discovery.baselines import (
    BaselineResult,
    Dataset,
    consistent,
    grid_probe,
    run_baselines,
)
from pbc.discovery.environment import CentralForceEnvironment, Environment
from pbc.discovery.protocol import (
    PROMPT_VERSION,
    CostRecord,
    Protocol,
    Score,
    TraceInfo,
    prompt_sha,
    prompts,
    score_transcript,
)
from pbc.discovery.tools import MEASURE, environment_allowlist

BUDGET = 20
MAX_STEPS = 12
TOLERANCE = 0.05  # held-out error that counts as recovering the law
SEED = 0
# The exponent of the familiar law, Newton's inverse square.
FAMILIAR_EXPONENT = 2.0

PROTOCOLS: dict[str, Protocol] = {
    "black-box": Protocol(
        version="f66-black-box-1",
        environment="central-force",
        world={"strength": 20.0, "exponent": 2.0},
        budget=BUDGET,
        seeds=(SEED,),
        tolerance=TOLERANCE,
        max_steps=MAX_STEPS,
    ),
    "prior-knowledge": Protocol(
        version="f66-prior-knowledge-1",
        environment="oscillator",
        world={"stiffness": 3.0},
        budget=BUDGET,
        seeds=(SEED,),
        tolerance=TOLERANCE,
        max_steps=MAX_STEPS,
    ),
    "modified": Protocol(
        version="f66-modified-1",
        environment="central-force",
        world={"strength": 12.0, "exponent": 2.5},
        budget=BUDGET,
        seeds=(SEED,),
        tolerance=TOLERANCE,
        max_steps=MAX_STEPS,
    ),
}

# Who produced the recordings, and when (the plan of Issue #189, "Recording").
MODEL = "claude-sonnet-5-5 in a Claude Code session"
RECORDED = "2026-10-16"


@dataclass(frozen=True)
class Run:
    """One frozen run of a lesson: its protocol, its condition, the fixture
    next to the page, and the record that versions it."""

    protocol: str  # a key of PROTOCOLS
    condition: str
    fixture: str
    info: TraceInfo


def _info(protocol: str, condition: str, sha: str, cost: CostRecord) -> TraceInfo:
    return TraceInfo(
        protocol=PROTOCOLS[protocol].version,
        environment=PROTOCOLS[protocol].environment,
        condition=condition,
        seed=SEED,
        prompt_version=PROMPT_VERSION,
        prompt_sha256=sha,
        model=MODEL,
        recorded=RECORDED,
        cost=cost,
    )


# The sub-agent's session reported no token counts and no price.
def _cost(model_calls: int, tool_calls: int) -> CostRecord:
    return CostRecord(model_calls, tool_calls, None, None, None)


RUNS: dict[str, Run] = {
    "black-box": Run(
        "black-box",
        "partial",
        "replay.json",
        _info(
            "black-box",
            "partial",
            "59c910ca675c5da449f8f830c55dddacf80971f7f421b7e63a8759253bf15fe3",
            _cost(3, 5),
        ),
    ),
    "prior-full": Run(
        "prior-knowledge",
        "full",
        "replay-full.json",
        _info(
            "prior-knowledge",
            "full",
            "5182074ee4c4083326d0937d28799801e390bd8f86e9900a7810a83034192577",
            _cost(4, 11),
        ),
    ),
    "prior-partial": Run(
        "prior-knowledge",
        "partial",
        "replay-partial.json",
        _info(
            "prior-knowledge",
            "partial",
            "7da8bc8bcea991f03d640ad635f120c43aed34a557c333b0c4aeb4ad63568a9f",
            _cost(4, 11),
        ),
    ),
    "prior-none": Run(
        "prior-knowledge",
        "none",
        "replay-none.json",
        _info(
            "prior-knowledge",
            "none",
            "3c66a44f248fe0dbf17078cfcf9115d100b4d910fa3d399be59f8324d2d5668b",
            _cost(4, 11),
        ),
    ),
    "modified": Run(
        "modified",
        "partial",
        "replay.json",
        _info(
            "modified",
            "partial",
            "59c910ca675c5da449f8f830c55dddacf80971f7f421b7e63a8759253bf15fe3",
            _cost(3, 6),
        ),
    ),
}


def environment(protocol: str) -> Environment:
    """A fresh environment of ``protocol``, with its seed."""
    return PROTOCOLS[protocol].make(SEED)


def task_of(protocol: str, condition: str) -> tuple[str, str]:
    """The system prompt and the task of a run (``pbc.discovery.prompts``)."""
    return prompts(environment(protocol), condition)


def record_command(name: str) -> str:
    return f"uv run --extra openai python -m pbc.discovery.force_lab {name} --record"


def replay_run(
    name: str, directory: Path = Path()
) -> tuple[Recording, Transcript, Score]:
    """Replay the fixture of run ``name`` from ``directory`` against the
    current code and score it again (``replay_entry``)."""
    entry = RUNS[name]
    protocol = PROTOCOLS[entry.protocol]
    system, task = task_of(entry.protocol, entry.condition)
    return replay_entry(
        entry,
        protocol,
        directory,
        system,
        task,
        environment_allowlist,
        record_command(name),
    )


def replay_entry(
    entry: Run,
    protocol: Protocol,
    directory: Path,
    system: str,
    task: str,
    tools: Callable[[Environment], Allowlist],
    rerecord: str,
) -> tuple[Recording, Transcript, Score]:
    """Replay the fixture of ``entry`` from ``directory`` with the ``tools``
    over a fresh environment of ``protocol``, and score it again with the
    same tools.

    Raises ``ValueError`` when the fixture and the record of the run disagree
    on the model, the date, or the prompt, and ``ReplayMismatch`` when a
    recomputed tool result differs from the recorded one."""
    recording = load_recording(directory / entry.fixture)
    if (recording.model, recording.recorded) != (entry.info.model, entry.info.recorded):
        raise ValueError(f"{entry.fixture} is not the run recorded for {rerecord}")
    if prompt_sha(recording.system, recording.task) != entry.info.prompt_sha256:
        raise ValueError(f"{entry.fixture} was recorded with another prompt")
    transcript = replay(
        recording,
        tools(protocol.make(SEED)),
        system=system,
        task=task,
        tolerance=protocol.replay_tolerance,
        max_steps=protocol.max_steps,
        rerecord=rerecord,
    )
    return recording, transcript, score_transcript(protocol, transcript, SEED, tools)


def probes(protocol: str, transcript: Transcript) -> Dataset:
    """The probes a run made: the accepted ``measure`` calls of a replayed
    transcript, with the readings the replay recomputed."""
    world = environment(protocol)
    settings, values = [], []
    for step in transcript.steps:
        for call, result in zip(step.message.tool_calls, step.results, strict=True):
            if call.name == MEASURE and result.ok:
                settings.append({k: float(v) for k, v in call.arguments.items()})
                values.append(result.content[world.observation.name])
    return Dataset(tuple(settings), np.array(values), world.observation.sigma)


def fit_probes(protocol: str, data: Dataset) -> FitResult | None:
    """The public family of ``protocol`` fitted to ``data`` from each of its
    starts, the best fit kept, with its standard errors; ``None`` when no fit
    can be made."""
    world = environment(protocol)
    names = tuple(c.name for c in world.claim)
    bounds = ([c.low for c in world.claim], [c.high for c in world.claim])

    def curve(index: np.ndarray, *params: float) -> np.ndarray:
        claim = dict(zip(names, params, strict=True))
        return np.array([world.predict(claim, data.settings[int(i)]) for i in index])

    best = None
    for start in world.starts:
        try:
            fit = fit_curve(
                curve,
                np.arange(len(data.values), dtype=float),
                data.values,
                start,
                sigma=data.sigma,
                names=names,
                bounds=bounds,
            )
        except ValueError:
            continue
        if best is None or fit.chi2 < best.chi2:
            best = fit
    return best


def baselines(protocol: str) -> tuple[BaselineResult, ...]:
    """The baselines of ``pbc.discovery`` on the environment of ``protocol``,
    with its budget and seed."""
    return run_baselines(environment(protocol), SEED)


def familiar_law(
    protocol: str, data: Dataset | None = None, name: str = "grid + inverse-square law"
) -> BaselineResult:
    """The familiar law as a baseline on the environment of ``protocol``: the
    probes, the grid unless ``data`` is given, fitted by ``fit_familiar``."""
    return fit_familiar(environment(protocol), data, name)


def fit_familiar(
    world: Environment, data: Dataset | None = None, name: str = "inverse-square law"
) -> BaselineResult:
    """The probes of ``world``, its grid unless ``data`` is given, fitted with
    the exponent held at the inverse square and only the strength free
    (weighted least squares, which is linear in the strength).

    It succeeds only when that fit is consistent with the noise, as every
    baseline must; on a modified law it is not, and the result says so."""
    if not isinstance(world, CentralForceEnvironment):
        raise ValueError("the familiar law is a law of the central force")
    if data is None:
        data = grid_probe(world)
    x = np.array(
        [s["mass"] * s["distance"] ** -FAMILIAR_EXPONENT for s in data.settings]
    )
    strength = float(np.sum(x * data.values) / np.sum(x * x))
    chi2 = float(np.sum(((data.values - strength * x) / data.sigma) ** 2))
    dof = len(data.values) - 1
    claim = {"strength": strength, "exponent": FAMILIAR_EXPONENT}
    error = world.held_out_error(claim)
    reason = ""
    if not consistent(chi2, dof):
        reason = (
            f"chi-square {chi2:.3g} for {dof} degrees of freedom: the"
            " inverse-square law does not describe the measurements"
        )
    return BaselineResult(name, len(data.settings), not reason, claim, error, reason)


def recovered(result: BaselineResult) -> bool:
    """Whether a baseline recovered the law: a fit consistent with the noise
    whose claim predicts the held-out settings within the tolerance."""
    return result.success and result.held_out_error <= TOLERANCE


def _show(step: Step) -> None:
    if step.message.text:
        print(step.message.text)
    for call, result in zip(step.message.tool_calls, step.results, strict=False):
        print(f"  {call.name}({call.arguments}) -> {dict(result.content)}")


def main(argv: list[str] | None = None) -> int:
    """The live entry point: run each named run of the lessons with the
    provider's model, print it and its score, and optionally record it over
    its fixture in the current directory."""
    from pbc.agents.providers import PROVIDER, load_client

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("runs", nargs="+", choices=sorted(RUNS), metavar="run")
    parser.add_argument("--record", action="store_true")
    options = parser.parse_args(argv)
    try:
        client = load_client(PROVIDER)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    for name in options.runs:
        _live_run(client, name, options.record)
    return 0


def _live_run(client, name: str, record: bool) -> None:
    entry = RUNS[name]
    protocol = PROTOCOLS[entry.protocol]
    system, task = task_of(entry.protocol, entry.condition)
    print(f"Run: {name}\nTask: {task}\nModel: {client.model}\n")
    transcript = run(
        client,
        environment_allowlist(protocol.make(SEED)),
        system,
        task,
        protocol.max_steps,
        on_step=_show,
    )
    score = score_transcript(protocol, transcript, SEED)
    print(f"\nHeld-out error {score.held_out_error:.3g}: {score.outcome}\n")
    if record:
        today = datetime.date.today().isoformat()
        save_recording(Path(entry.fixture), transcript, today, *client.secrets)
        print(
            f"Recorded to {entry.fixture}. Review it, then set the model, the"
            f" date ({today}), and the cost of the run in RUNS[{name!r}]"
            f" of {__name__}; the prompt SHA-256 is {prompt_sha(system, task)}."
        )


if __name__ == "__main__":
    sys.exit(main())
