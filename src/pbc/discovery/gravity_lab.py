"""Lesson D4: discovering gravity from experiments (F99;
``docs/discovery-protocol.md``, "Transfer").

The protocol of the lesson, fixed before the run was recorded, the frozen
run, and its score recomputed from the tool calls. An agent probes the
attraction between two masses in a laboratory whose law is hidden
(``pbc.discovery.gravity``) and states the law as the parameters of the
public family. The build scores the claim on a world the agent never
probed: the periods of orbits about bodies a thousand times heavier, at
distances tens of times larger.

The run is a replay fixture next to the page (ADR 002); its version record,
the ``TraceInfo``, is kept here and checked against the fixture by
``replay_run``. The hidden law is the judge's configuration: no prompt,
tool, or page shows it.
"""

import argparse
import datetime
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from pbc.agents.loop import Step, Transcript, run
from pbc.agents.replay import Recording, save_recording
from pbc.data.fit import FitResult, fit_curve
from pbc.discovery.baselines import (
    BaselineResult,
    Dataset,
    grid_probe,
    least_squares,
    random_probe,
    sparse_identification,
)
from pbc.discovery.force_lab import Run, replay_entry
from pbc.discovery.gravity import GravityEnvironment, gravity_library
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
TOLERANCE = 0.05  # transfer error that counts as recovering the law
SEED = 0
CONDITION = "partial"  # told the names of the parameters, not the law
# The judge's configuration: the hidden law. Never on a page.
WORLD = {"G": 0.0437, "source_power": 1.0, "test_power": 1.0, "exponent": 2.0}


@dataclass(frozen=True)
class GravityProtocol(Protocol):
    """The protocol of the lesson: its environment is the gravity
    laboratory, which the protocols of D1 to D3 do not list."""

    def make(self, seed: int) -> GravityEnvironment:
        return GravityEnvironment(budget=self.budget, seed=seed, **self.world)

    def held_out_settings(self) -> tuple[dict[str, float], ...]:
        """The orbits of the transfer a claim is scored on."""
        return tuple(dict(s) for s in GravityEnvironment._held_out)


PROTOCOL = GravityProtocol(
    version="f99-gravity-1",
    environment=GravityEnvironment.name,
    world=WORLD,
    budget=BUDGET,
    seeds=(SEED,),
    tolerance=TOLERANCE,
    max_steps=MAX_STEPS,
)

# Who produced the recording, and when (the plan of Issue #336, "Recording").
MODEL = "claude-opus-5-5 in a Claude Code session"
RECORDED = "2026-10-29"
FIXTURE = "replay.json"


def environment() -> GravityEnvironment:
    """A fresh laboratory of the protocol, with its seed."""
    return PROTOCOL.make(SEED)


def task() -> tuple[str, str]:
    """The system prompt and the task (``pbc.discovery.prompts``)."""
    return prompts(environment(), CONDITION)


RUN = Run(
    "gravity",
    CONDITION,
    FIXTURE,
    TraceInfo(
        protocol=PROTOCOL.version,
        environment=PROTOCOL.environment,
        condition=CONDITION,
        seed=SEED,
        prompt_version=PROMPT_VERSION,
        prompt_sha256=prompt_sha(*task()),
        model=MODEL,
        recorded=RECORDED,
        # The sub-agent's session reported no token counts and no price.
        cost=CostRecord(5, 13, None, None, None),
    ),
)


def record_command() -> str:
    return f"uv run --extra openai python -m {__name__} --record"


def replay_run(directory: Path = Path()) -> tuple[Recording, Transcript, Score]:
    """Replay the fixture in ``directory`` against the current code and score
    it again (``pbc.discovery.force_lab.replay_entry``)."""
    return replay_entry(
        RUN,
        PROTOCOL,
        directory,
        *task(),
        environment_allowlist,
        record_command(),
    )


def probes(transcript: Transcript) -> Dataset:
    """The probes a run made: the accepted ``measure`` calls of a replayed
    transcript, with the readings the replay recomputed."""
    world = environment()
    settings, values = [], []
    for step in transcript.steps:
        for call, result in zip(step.message.tool_calls, step.results, strict=True):
            if call.name == MEASURE and result.ok:
                settings.append({k: float(v) for k, v in call.arguments.items()})
                values.append(result.content[world.observation.name])
    return Dataset(tuple(settings), np.array(values), world.observation.sigma)


def baselines() -> tuple[BaselineResult, ...]:
    """The baselines without a model with the protocol's budget: least
    squares of the family on a grid and on random settings, and sparse
    identification on the grid with the terms of ``gravity_library``."""
    world = environment()
    grid = grid_probe(world)
    scattered = random_probe(world, SEED)
    results = (
        least_squares(world, grid, "grid + least squares"),
        least_squares(world, scattered, "random + least squares"),
        sparse_identification(
            world, grid, gravity_library(), name="grid + sparse identification"
        ),
    )
    world.reset()
    return results


def recovered(result: BaselineResult) -> bool:
    """Whether a baseline recovered the law: a fit consistent with the noise
    whose claim passes the transfer within the tolerance."""
    return result.success and result.held_out_error <= TOLERANCE


def fit_laboratory(
    data: Dataset, held: dict[str, float] | None = None
) -> FitResult | None:
    """The family fitted to the laboratory readings ``data`` by weighted
    least squares from each start, the best fit kept; with ``held``, those
    parameters are held at the values given and only the others are free.
    ``None`` when no fit can be made."""
    world = environment()
    held = held or {}
    names = tuple(c.name for c in world.claim if c.name not in held)
    bounds = (
        [c.low for c in world.claim if c.name in names],
        [c.high for c in world.claim if c.name in names],
    )

    def curve(index: np.ndarray, *params: float) -> np.ndarray:
        claim = held | dict(zip(names, params, strict=True))
        return np.array([world.predict(claim, data.settings[int(i)]) for i in index])

    best = None
    for start in world.starts:
        free = [v for c, v in zip(world.claim, start, strict=True) if c.name in names]
        try:
            fit = fit_curve(
                curve,
                np.arange(len(data.values), dtype=float),
                data.values,
                free,
                sigma=data.sigma,
                names=names,
                bounds=bounds,
            )
        except ValueError:
            continue
        if best is None or fit.chi2 < best.chi2:
            best = fit
    return best


@dataclass(frozen=True)
class Shifted:
    """One law of the sensitivity scan: a parameter held away from the
    laboratory fit, the others refitted to the same readings."""

    parameter: str
    shift: float  # in standard errors of the free fit
    chi2_increase: float  # over the free fit's chi-square
    transfer_error: float


def sensitivity(
    data: Dataset, parameter: str, shifts: tuple[float, ...]
) -> tuple[Shifted, ...]:
    """Hold ``parameter`` at the free fit's value plus each of ``shifts``
    standard errors, refit the other parameters to ``data``, and score each
    law on the transfer: how far the laboratory and the orbits tell the
    laws apart."""
    world = environment()
    free = fit_laboratory(data)
    if free is None:
        raise ValueError("the readings admit no fit of the family")
    i = free.names.index(parameter)
    found = []
    for shift in shifts:
        value = float(free.params[i] + shift * free.stderr[i])
        fit = fit_laboratory(data, {parameter: value})
        if fit is None:
            continue
        claim = {parameter: value} | dict(
            zip(fit.names, map(float, fit.params), strict=True)
        )
        found.append(
            Shifted(parameter, shift, fit.chi2 - free.chi2, world.held_out_error(claim))
        )
    return tuple(found)


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
    system, text = task()
    print(f"Task: {text}\nModel: {client.model}\n")
    transcript = run(
        client,
        environment_allowlist(environment()),
        system,
        text,
        MAX_STEPS,
        on_step=_show,
    )
    score = score_transcript(PROTOCOL, transcript, SEED)
    print(f"\nTransfer error {score.held_out_error:.3g}: {score.outcome}\n")
    if options.record:
        today = datetime.date.today().isoformat()
        save_recording(Path(FIXTURE), transcript, today, *client.secrets)
        print(
            f"Recorded to {FIXTURE}. Review it, then set MODEL, RECORDED"
            f" ({today}), and the cost of the run in RUN of {__name__}."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
