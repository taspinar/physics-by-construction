"""Lesson D10: scientific discovery under measurement noise (F98;
``docs/discovery-protocol.md``, "Noise, calibration, and faulty readings").

The environment is the central force of D1 read through a faulty gauge: its
noise has a stated standard deviation, but the gauge also reads with a
hidden zero offset, and a hidden fraction of its readings are faulty, off by
a large amount. The mass may be set to zero, where the true force vanishes:
the null reading is the calibration. A claim is the strength and the
exponent of the force; it is scored on the noise-free force, with no offset,
at distances beyond the bounds.

The protocol, fixed before the run was recorded, the frozen run, its score
recomputed from the tool calls, the baselines without a model with a
calibrated robust fit among them, and the measurements of the lesson: how
each baseline degrades as the noise grows, and which remedy each failure of
the gauge needs. The hidden gauge and law are the judge's configuration: no
prompt, tool, or page shows them.
"""

import argparse
import datetime
import hashlib
import math
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import optimize

from pbc.agents.loop import Step, Transcript, run
from pbc.agents.replay import Recording, save_recording
from pbc.data.fit import fit_curve
from pbc.discovery.baselines import (
    BaselineResult,
    Dataset,
    consistent,
    grid_probe,
    least_squares,
    random_probe,
    sparse_identification,
)
from pbc.discovery.environment import Control, Environment, Observation
from pbc.discovery.force_lab import Run, replay_entry
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

BUDGET = 24
MAX_STEPS = 12
TOLERANCE = 0.05  # held-out error that counts as recovering the law
SEED = 0
CONDITION = "partial"  # told the names of the parameters, not the law
SIGMA = 0.03  # N, the gauge's stated noise
# A faulty reading is off by this much at least, and at most twice it.
FAULT_SIZE = 1.0  # N
# The calibrated robust fit drops readings this many standard deviations off.
REJECT_SIGMAS = 4.0
# The judge's configuration: the hidden law and gauge. Never on a page.
WORLD = {
    "strength": 14.7,
    "exponent": 2.37,
    "offset": 0.0864,
    "faulty": 0.15,
    "sigma": SIGMA,
}


class FaultyGaugeEnvironment(Environment):
    """The central force read by a gauge with Gaussian noise of a stated
    standard deviation, a hidden zero offset, and a hidden fraction of faulty
    readings. The fault of a setting, like its noise, is a function of the
    seed and the controls: a repeated probe repeats it."""

    name = "faulty-gauge"
    controls = (
        Control("distance", "m", 1.0, 4.0, "distance from the centre"),
        Control("mass", "kg", 0.0, 5.0, "mass of the test body, zero for none"),
    )
    claim = (
        Control("strength", "N m^p/kg", 0.1, 100.0, "coefficient of the law"),
        Control("exponent", "1", 0.0, 6.0, "power p of the distance"),
    )
    family = "force = strength mass distance^-exponent"
    starts = ((10.0, 2.0), (30.0, 1.0), (5.0, 3.0))
    _held_out = (
        {"distance": 6.0, "mass": 1.0},
        {"distance": 9.0, "mass": 2.0},
        {"distance": 12.0, "mass": 4.0},
    )

    def __init__(
        self,
        *,
        strength: float = 20.0,
        exponent: float = 2.0,
        offset: float = 0.0,
        faulty: float = 0.0,
        sigma: float = SIGMA,
        budget: int = 30,
        seed: int = 0,
    ):
        super().__init__(budget=budget, seed=seed)
        if not 0.0 <= faulty < 1.0:
            raise ValueError(
                f"the fraction of faulty readings must be in [0, 1), got {faulty}"
            )
        self.observation = Observation(
            "force", "N", sigma, "reading of the gauge, toward the centre"
        )
        self._strength = strength
        self._exponent = exponent
        self._offset = offset
        self._faulty = faulty

    def __repr__(self) -> str:
        return f"FaultyGaugeEnvironment(budget={self.budget}, seed={self.seed})"

    # region: gauge
    def measure(self, **controls: float) -> dict[str, float]:
        """One probe: the force with the gauge's noise, offset, and fault."""
        reading = super().measure(**controls)
        settings = self._validated(controls)
        reading["force"] += self._offset + self._fault(settings)
        return reading

    # endregion: gauge

    def _law(self, settings):
        return (
            self._strength * settings["mass"] * settings["distance"] ** -self._exponent
        )

    def predict(self, claim, settings):
        return float(
            claim["strength"]
            * settings["mass"]
            * settings["distance"] ** -claim["exponent"]
        )

    def _fault(self, settings: Mapping[str, float]) -> float:
        key = f"{self.seed}|{self.name}|fault|" + "|".join(
            f"{k}={v:.12g}" for k, v in sorted(settings.items())
        )
        digest = hashlib.sha256(key.encode()).digest()
        chance, size, sign = np.random.default_rng(
            int.from_bytes(digest[:8], "big")
        ).random(3)
        if chance >= self._faulty:
            return 0.0
        return float((1.0 if sign < 0.5 else -1.0) * FAULT_SIZE * (1.0 + size))


@dataclass(frozen=True)
class NoiseProtocol(Protocol):
    """The protocol of the lesson: its environment is the faulty gauge,
    which the protocols of D1 to D3 do not list."""

    def make(self, seed: int) -> FaultyGaugeEnvironment:
        return FaultyGaugeEnvironment(budget=self.budget, seed=seed, **self.world)

    def held_out_settings(self) -> tuple[dict[str, float], ...]:
        return tuple(dict(s) for s in FaultyGaugeEnvironment._held_out)


PROTOCOL = NoiseProtocol(
    version="f98-noise-1",
    environment=FaultyGaugeEnvironment.name,
    world=WORLD,
    budget=BUDGET,
    seeds=(SEED,),
    tolerance=TOLERANCE,
    max_steps=MAX_STEPS,
)

# What the agent is told of its gauge, beyond the task of D1.
GAUGE = (
    f"The gauge's noise has a standard deviation of {SIGMA:g} N; the gauge may"
    " also read with a constant offset, and some readings may be faulty."
)

# Who produced the recording, and when (the plan of Issue #345, "Recording").
MODEL = "claude-opus-5-5 in a Claude Code session"
RECORDED = "2026-10-30"
FIXTURE = "replay.json"


def environment(**changes: float) -> FaultyGaugeEnvironment:
    """A fresh gauge of the protocol, with its seed; ``changes`` replace
    entries of the hidden world (the noise, the offset, the faults) for the
    measurements of the lesson. ``seed`` among them sets the seed."""
    seed = int(changes.pop("seed", SEED))
    world = {**WORLD, **changes}
    return FaultyGaugeEnvironment(budget=BUDGET, seed=seed, **world)


def task() -> tuple[str, str]:
    """The system prompt and the task: those of ``pbc.discovery.prompts``,
    with what the agent is told of its gauge."""
    system, text = prompts(environment(), CONDITION)
    return system, f"{text} {GAUGE}"


RUN = Run(
    "noise",
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
        cost=CostRecord(8, 25, None, None, None),
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
    settings, values = [], []
    for step in transcript.steps:
        for call, result in zip(step.message.tool_calls, step.results, strict=True):
            if call.name == MEASURE and result.ok:
                settings.append({k: float(v) for k, v in call.arguments.items()})
                values.append(result.content["force"])
    return Dataset(tuple(settings), np.array(values), SIGMA)


def gauge_library() -> dict:
    """The candidate terms of the sparse baseline: the mass over whole powers
    of the distance, and a constant. Terms are public."""
    terms = {
        f"mass*distance^-{n}": (lambda s, n=n: s["mass"] * s["distance"] ** -n)
        for n in range(5)
    }
    terms["1"] = lambda s: 1.0
    return terms


@dataclass(frozen=True)
class Calibrated:
    """The calibrated robust fit: the claim, the offset, and the readings
    it dropped as faulty."""

    result: BaselineResult
    offset: float | None
    dropped: tuple[int, ...]  # indices into the data


def _with_offset(world: Environment, data: Dataset):
    def curve(index: np.ndarray, strength, exponent, offset) -> np.ndarray:
        claim = {"strength": strength, "exponent": exponent}
        return np.array(
            [world.predict(claim, data.settings[int(i)]) + offset for i in index]
        )

    return curve


def calibrated_fit(
    world: Environment,
    data: Dataset,
    name: str = "calibrated robust fit",
    reject: bool = True,
) -> Calibrated:
    """The family plus a constant offset of the gauge, fitted first with a
    soft-L1 loss, which a few faulty readings do not pull; then the readings
    more than ``REJECT_SIGMAS`` standard deviations from that fit are dropped
    (none with ``reject`` false) and the rest refitted by weighted least
    squares. It succeeds only when the refit is consistent with the noise
    and its parameters are determined."""
    n = len(data.values)
    if n <= 3:
        failed = BaselineResult(name, n, False, None, math.inf, "too few probes")
        return Calibrated(failed, None, ())
    curve = _with_offset(world, data)
    index = np.arange(n, dtype=float)
    bounds = (
        [c.low for c in world.claim] + [-10.0],
        [c.high for c in world.claim] + [10.0],
    )
    starts = [(*start, 0.0) for start in world.starts]
    keep = np.ones(n, dtype=bool)
    if reject:
        best = None
        for start in starts:
            found = optimize.least_squares(
                lambda p: (data.values - curve(index, *p)) / data.sigma,
                start,
                bounds=bounds,
                loss="soft_l1",
                x_scale="jac",
            )
            if best is None or found.cost < best.cost:
                best = found
        keep = np.abs(data.values - curve(index, *best.x)) <= REJECT_SIGMAS * data.sigma
    dropped = tuple(int(i) for i in np.flatnonzero(~keep))
    kept = Dataset(
        tuple(s for s, k in zip(data.settings, keep, strict=True) if k),
        data.values[keep],
        data.sigma,
    )
    if len(kept.values) <= 3:
        failed = BaselineResult(name, n, False, None, math.inf, "too few readings kept")
        return Calibrated(failed, None, dropped)
    curve = _with_offset(world, kept)
    fit = None
    for start in starts:
        try:
            trial = fit_curve(
                curve,
                np.arange(len(kept.values), dtype=float),
                kept.values,
                start,
                sigma=kept.sigma,
                names=("strength", "exponent", "offset"),
                bounds=bounds,
            )
        except ValueError:
            continue
        if fit is None or trial.chi2 < fit.chi2:
            fit = trial
    if fit is None:
        failed = BaselineResult(name, n, False, None, math.inf, "no fit could be made")
        return Calibrated(failed, None, dropped)
    claim = {"strength": fit.value("strength"), "exponent": fit.value("exponent")}
    error = world.held_out_error(claim)
    if not consistent(fit.chi2, fit.dof):
        reason = (
            f"chi-square {fit.chi2:.3g} for {fit.dof} degrees of freedom: the"
            " family with an offset does not describe the readings"
        )
    elif not all(fit.identifiable):
        reason = "the data do not determine the parameters separately"
    else:
        reason = ""
    result = BaselineResult(name, n, not reason, claim, error, reason)
    return Calibrated(result, fit.value("offset"), dropped)


# The methods of the measurements, each given a gauge and its grid.
METHODS = (
    "least squares",
    "sparse identification",
    "least squares with an offset",
    "calibrated robust fit",
)


def method(name: str, world: Environment, data: Dataset) -> BaselineResult:
    """One of ``METHODS`` on ``data`` of ``world``."""
    if name == "least squares":
        return least_squares(world, data, name)
    if name == "sparse identification":
        return sparse_identification(world, data, gauge_library(), name=name)
    if name == "least squares with an offset":
        return calibrated_fit(world, data, name, reject=False).result
    if name == "calibrated robust fit":
        return calibrated_fit(world, data, name).result
    raise ValueError(f"unknown method {name!r}")


def baselines() -> tuple[BaselineResult, ...]:
    """The baselines without a model with the protocol's budget: every method
    on the grid, and least squares and the calibrated robust fit on random
    settings."""
    world = environment()
    grid = grid_probe(world)
    scattered = random_probe(world, SEED)
    results = tuple(_renamed(method(m, world, grid), f"grid + {m}") for m in METHODS)
    results += (
        _renamed(method("least squares", world, scattered), "random + least squares"),
        _renamed(
            method("calibrated robust fit", world, scattered),
            "random + calibrated robust fit",
        ),
    )
    world.reset()
    return results


def _renamed(result: BaselineResult, name: str) -> BaselineResult:
    return BaselineResult(
        name,
        result.probes,
        result.success,
        result.claim,
        result.held_out_error,
        result.reason,
    )


def recovered(result: BaselineResult) -> bool:
    """Whether a baseline recovered the law: a fit consistent with the noise
    whose claim predicts the held-out settings within the tolerance."""
    return result.success and result.held_out_error <= TOLERANCE


@dataclass(frozen=True)
class Degradation:
    """One baseline at one noise level, over the seeds."""

    method: str  # the baseline: its design of probes and its method
    sigma: float
    errors: tuple[float, ...]  # held-out error, one per seed
    recovered: int  # seeds on which it recovered the law

    @property
    def median(self) -> float:
        return float(np.median(self.errors))


# The baselines of ``baselines``: a design of the probes and a method.
BASELINES = (
    *(("grid", m) for m in METHODS),
    ("random", "least squares"),
    ("random", "calibrated robust fit"),
)


def degradation(
    sigmas: tuple[float, ...], seeds: tuple[int, ...]
) -> tuple[Degradation, ...]:
    """Every baseline of ``BASELINES`` at each standard deviation of the
    noise in ``sigmas``, the offset and the faults held, once per seed; the
    random settings are drawn anew with each seed."""
    found = []
    for design, name in BASELINES:
        for sigma in sigmas:
            errors, hits = [], 0
            for seed in seeds:
                world = environment(sigma=sigma, seed=seed)
                if design == "grid":
                    data = grid_probe(world)
                else:
                    data = random_probe(world, seed)
                result = method(name, world, data)
                errors.append(result.held_out_error)
                hits += recovered(result)
            found.append(Degradation(f"{design} + {name}", sigma, tuple(errors), hits))
    return tuple(found)


# The failures of the gauge, one at a time: the hidden world's entries set.
GAUGES = {
    "noise only": {"offset": 0.0, "faulty": 0.0},
    "noise and offset": {"faulty": 0.0},
    "noise and faulty readings": {"offset": 0.0},
    "noise, offset, and faulty readings": {},
}


def failure_analysis() -> dict[str, dict[str, BaselineResult]]:
    """Every method on the grid of each gauge of ``GAUGES``, at the lesson's
    noise and seed: which remedy each failure needs."""
    table = {}
    for gauge, changes in GAUGES.items():
        world = environment(**changes)
        data = grid_probe(world)
        table[gauge] = {m: method(m, world, data) for m in METHODS}
    return table


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
    print(f"\nHeld-out error {score.held_out_error:.3g}: {score.outcome}\n")
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
