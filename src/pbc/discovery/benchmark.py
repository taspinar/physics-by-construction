"""Lessons EV2 and EV3: an interactive discovery benchmark and the agent against
methods without one (F81; ``docs/discovery-protocol.md``).

The benchmark is a grid: three environments, each under one protocol, and the
three conditions of prior knowledge, one frozen run per cell. Four cells are
the runs of the lessons D1 and D2 (``pbc.discovery.force_lab``), read from
their own pages; the other five, and the runs of a plain model that has the
task but no ``measure`` tool, are recorded here with the same protocols. The
protocols, the runs, and their ``TraceInfo`` are fixed in this module; the
hidden worlds are the judge's configuration and reach no prompt, tool, or
page.

``comparable`` says why two scored entries may not be compared: it reads the
protocols, so a page states a comparison that is not meaningful from the
same objects that produced the scores.
"""

import argparse
import datetime
import sys
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from pbc.agents.loop import Transcript, run
from pbc.agents.replay import Recording, save_recording
from pbc.agents.tools import Allowlist
from pbc.discovery import force_lab
from pbc.discovery.baselines import (
    BaselineResult,
    Dataset,
    least_squares,
    random_probe,
    run_baselines,
)
from pbc.discovery.environment import Environment
from pbc.discovery.force_lab import (
    MAX_STEPS,
    SEED,
    TOLERANCE,
    Run,
    replay_entry,
)
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
from pbc.discovery.tools import MEASURE, SUBMIT, environment_allowlist

BUDGET = force_lab.BUDGET
# The condition of a plain model: the partial task, no probe.
PLAIN = "plain"

PROTOCOLS: dict[str, Protocol] = {
    "black-box": force_lab.PROTOCOLS["black-box"],
    "prior-knowledge": force_lab.PROTOCOLS["prior-knowledge"],
    "projectile": Protocol(
        version="f81-projectile-1",
        environment="projectile",
        world={"gravity": 6.0},
        budget=BUDGET,
        seeds=(SEED,),
        tolerance=TOLERANCE,
        max_steps=MAX_STEPS,
    ),
}
# The protocol of each environment of the grid, in the order of the pages.
ENVIRONMENTS = {
    "projectile": "projectile",
    "oscillator": "prior-knowledge",
    "central-force": "black-box",
}

# Who produced the recordings of F81, and when (the plan of Issue #295).
MODEL = "claude-sonnet-5-5 in a Claude Code session"
RECORDED = "2026-10-26"


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


def _run(
    protocol: str, condition: str, fixture: str, sha: str, cost: CostRecord
) -> Run:
    return Run(protocol, condition, fixture, _info(protocol, condition, sha, cost))


RUNS: dict[str, Run] = {
    "projectile-full": _run(
        "projectile",
        "full",
        "replay-projectilefull.json",
        "d74a3949a9154fd4bed45652a182253c1d15aac9eb7dfe3b8f5d0a4cfe781ab2",
        _cost(3, 9),
    ),
    "projectile-partial": _run(
        "projectile",
        "partial",
        "replay-projectilepartial.json",
        "5a6f05b66bb033432c25c4495ac13f2441ad1188ab1ecc1c0daeaa2ed134b151",
        _cost(3, 6),
    ),
    "projectile-none": _run(
        "projectile",
        "none",
        "replay-projectilenone.json",
        "f50e2eba953a735645bc9cd8aef9dc93cea4992d5d1265cb6e07777805aa7160",
        _cost(5, 4),
    ),
    "central-full": _run(
        "black-box",
        "full",
        "replay-centralfull.json",
        "e22c0650d0dec3c6f8c158da7962346d893f4df19f4ea82ef0facfcef97c56c0",
        _cost(3, 5),
    ),
    "central-none": _run(
        "black-box",
        "none",
        "replay-centralnone.json",
        "81719a6367550621d8800441da0491b122ed83ca909e9aee29cce35ad6cf93c7",
        _cost(3, 5),
    ),
    "plain-projectile": _run(
        "projectile",
        PLAIN,
        "replay-plainprojectile.json",
        "5db57f7b8dbaa6aa81c4960ae5bc1b7ad7383427a8445b1eb972f4353f03c816",
        _cost(2, 1),
    ),
    "plain-oscillator": _run(
        "prior-knowledge",
        PLAIN,
        "replay-plainoscillator.json",
        "266b5c9b02d18ffd627ccb7233c4fcd3f702398ff81433ca6b9c1d9b8dbf2715",
        _cost(2, 1),
    ),
    "plain-central-force": _run(
        "black-box",
        PLAIN,
        "replay-plaincentral.json",
        "57c9682c17d766dc40db9dc42235e2b1ec6d5ba592be7571a868cb1e64ac2e8e",
        _cost(2, 1),
    ),
}


@dataclass(frozen=True)
class Cell:
    """Where the frozen run of one environment and condition is: its name in
    ``RUNS`` or ``force_lab.RUNS``, and the page that holds its fixture
    (``"D1"``, ``"D2"``, ``"EV2"``, ``"EV3"``)."""

    run: str
    home: str


GRID: dict[tuple[str, str], Cell] = {
    ("projectile", "full"): Cell("projectile-full", "EV2"),
    ("projectile", "partial"): Cell("projectile-partial", "EV2"),
    ("projectile", "none"): Cell("projectile-none", "EV2"),
    ("oscillator", "full"): Cell("prior-full", "D2"),
    ("oscillator", "partial"): Cell("prior-partial", "D2"),
    ("oscillator", "none"): Cell("prior-none", "D2"),
    ("central-force", "full"): Cell("central-full", "EV2"),
    ("central-force", "partial"): Cell("black-box", "D1"),
    ("central-force", "none"): Cell("central-none", "EV2"),
}
# The plain model on each environment.
PLAIN_RUNS = {e: Cell(f"plain-{e}", "EV3") for e in ENVIRONMENTS}


def entry(name: str) -> Run:
    """The run ``name`` of this module or of the lessons D1 to D3."""
    return RUNS[name] if name in RUNS else force_lab.RUNS[name]


def environment(protocol: str) -> Environment:
    """A fresh environment of ``protocol``, with its seed."""
    return PROTOCOLS[protocol].make(SEED)


def plain_allowlist(world: Environment) -> Allowlist:
    """The allowlist of a plain model: ``submit`` of ``world`` and nothing
    else, so it states a claim without a probe."""
    return Allowlist((environment_allowlist(world).tool(SUBMIT),))


def plain_prompts(world: Environment) -> tuple[str, str]:
    """The system prompt and the task of a plain model: the task of the
    partial condition, with a system prompt that says no probe is possible."""
    system = (
        "You are asked about a physical system that you cannot measure. Answer"
        " from what you know. Use only the tool you are given."
    )
    return system, prompts(world, "partial")[1]


def task_of(name: str) -> tuple[str, str]:
    """The system prompt and the task of run ``name``."""
    run_ = entry(name)
    world = environment(run_.protocol)
    if run_.condition == PLAIN:
        return plain_prompts(world)
    return prompts(world, run_.condition)


def tools_of(name: str) -> Callable[[Environment], Allowlist]:
    """The tools of run ``name``: they make its allowlist over an
    environment."""
    return plain_allowlist if entry(name).condition == PLAIN else environment_allowlist


def record_command(name: str) -> str:
    return f"uv run --extra openai python -m pbc.discovery.benchmark {name} --record"


def replay_cell(cell: Cell, directory: Path) -> tuple[Recording, Transcript, Score]:
    """Replay the run of ``cell`` from ``directory``, the page that holds its
    fixture, and score it again (``force_lab.replay_entry``)."""
    if cell.run in force_lab.RUNS:
        return force_lab.replay_run(cell.run, directory)
    run_ = RUNS[cell.run]
    system, task = task_of(cell.run)
    return replay_entry(
        run_,
        PROTOCOLS[run_.protocol],
        directory,
        system,
        task,
        tools_of(cell.run),
        record_command(cell.run),
    )


def readings(protocol: str, transcript: Transcript) -> Dataset:
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


def fit_readings(protocol: str, transcript: Transcript) -> BaselineResult:
    """The public family of ``protocol`` fitted to a run's own readings by
    least squares (``pbc.discovery.least_squares``): what the readings the
    agent saw support, apart from what it concluded."""
    world = environment(protocol)
    return least_squares(world, readings(protocol, transcript), "fit to the readings")


def baselines(protocol: str, budget: int | None = None) -> tuple[BaselineResult, ...]:
    """The baselines of ``pbc.discovery`` on the environment of ``protocol``
    with its seed, and its budget unless ``budget`` is given."""
    p = PROTOCOLS[protocol]
    if budget is not None:
        p = replace(p, budget=budget)
    return run_baselines(p.make(SEED), SEED)


def random_fit(protocol: str, budget: int, seed: int) -> BaselineResult:
    """Random selection of ``budget`` settings with ``seed``, and least
    squares, on the hidden world of ``protocol``."""
    world = replace(PROTOCOLS[protocol], budget=budget).make(SEED)
    return least_squares(
        world, random_probe(world, seed), f"random + least squares, seed {seed}"
    )


@dataclass(frozen=True)
class Entry:
    """One scored contestant of a comparison: who, under which protocol, with
    how many probes allowed and spent, and the judge's score."""

    who: str
    protocol: Protocol
    allowed: int  # the probes the contestant could spend
    probes: int  # the probes it spent
    held_out_error: float
    recovered: bool


def agent_entry(
    who: str, protocol: Protocol, score: Score, plain: bool = False
) -> Entry:
    """A replayed run as an entry; a plain model is allowed no probe."""
    allowed = 0 if plain else protocol.budget
    return Entry(
        who, protocol, allowed, score.probes, score.held_out_error, score.recovered
    )


def baseline_entry(protocol: Protocol, result: BaselineResult) -> Entry:
    """A baseline as an entry: it spends the budget of ``protocol``, and it
    recovers the law only with a fit consistent with the noise whose claim is
    within the tolerance."""
    ok = result.success and result.held_out_error <= protocol.tolerance
    return Entry(
        result.name,
        protocol,
        protocol.budget,
        result.probes,
        result.held_out_error,
        ok,
    )


def comparable(a: Entry, b: Entry) -> tuple[str, ...]:
    """Why ``a`` and ``b`` may not be compared, empty when they may.

    Two entries compare when they were scored on the same environment, the
    same hidden world, the same held-out settings, and the same tolerance,
    with the same number of probes allowed. The reasons name what differs,
    never its value: the world and the held-out settings are the judge's."""
    p, q = a.protocol, b.protocol
    reasons = []
    if p.environment != q.environment:
        reasons.append(f"environments differ ({p.environment}, {q.environment})")
    else:
        if dict(p.world) != dict(q.world):
            reasons.append("the hidden worlds differ")
        if p.held_out_settings() != q.held_out_settings():
            reasons.append("the held-out settings differ")
        if p.seeds != q.seeds:
            reasons.append("the seeds differ")
    if p.tolerance != q.tolerance:
        reasons.append(f"tolerances differ ({p.tolerance:g}, {q.tolerance:g})")
    if a.allowed != b.allowed:
        reasons.append(f"budgets differ ({a.allowed}, {b.allowed} probes)")
    return tuple(reasons)


def verdict(a: Entry, b: Entry) -> str:
    """``comparable`` in words for a table."""
    reasons = comparable(a, b)
    return "comparable" if not reasons else "not meaningful: " + "; ".join(reasons)


def main(argv: list[str] | None = None) -> int:
    """The live entry point: run each named run of F81 with the provider's
    model, print it and its score, and optionally record it over its fixture
    in the current directory."""
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
    run_ = RUNS[name]
    protocol = PROTOCOLS[run_.protocol]
    system, task = task_of(name)
    print(f"Run: {name}\nTask: {task}\nModel: {client.model}\n")
    transcript = run(
        client,
        tools_of(name)(protocol.make(SEED)),
        system,
        task,
        protocol.max_steps,
        on_step=force_lab._show,
    )
    score = score_transcript(protocol, transcript, SEED, tools_of(name))
    print(f"\nHeld-out error {score.held_out_error:.3g}: {score.outcome}\n")
    if record:
        today = datetime.date.today().isoformat()
        save_recording(Path(run_.fixture), transcript, today, *client.secrets)
        print(
            f"Recorded to {run_.fixture}. Review it, then set the model, the"
            f" date ({today}), and the cost of the run in RUNS[{name!r}]"
            f" of {__name__}; the prompt SHA-256 is {prompt_sha(system, task)}."
        )


if __name__ == "__main__":
    sys.exit(main())
