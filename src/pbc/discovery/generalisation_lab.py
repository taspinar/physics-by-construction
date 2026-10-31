"""Lesson D12: generalisation to unseen physical systems (F98;
``docs/discovery-protocol.md``, "Generalisation").

The environment is the central force of D1 with one more hidden term: a
short-range attraction ``c mass exp(-distance/length)`` that lies below the
noise everywhere the agent may probe. A claim is the strength and the
exponent of the family ``strength mass distance^-exponent``.

A claim is challenged on a suite of **held-out worlds**, none of which is in
a tool, a prompt, or a page:

- **interpolation**: settings within the bounds that the agent did not probe;
- **farther**: distances beyond the bounds;
- **heavier**: test masses far beyond the bounds, the condition changed;
- **orbits**: another system, the law used as the force of a dynamical model
  (the radial periods of bound orbits about the centre, as in D4);
- **closer**: distances below the bounds, where the short-range term matters.

The claim is recovered when the largest error of the first four worlds is
within the tolerance. The fifth is reported apart: the probes cannot reach
it, so it fails every claim of the family, the agent's and the baselines'
alike, and shows where generalisation stops being warranted.

The protocol, fixed before the run was recorded, the frozen run, its score
recomputed from the tool calls, and the evidence, from the trace, that no
held-out world was probed.
"""

import argparse
import datetime
import math
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from pbc.agents.loop import Step, Transcript, run
from pbc.agents.replay import Recording, save_recording
from pbc.discovery.baselines import (
    BaselineResult,
    Dataset,
    grid_probe,
    least_squares,
    random_probe,
    sparse_identification,
)
from pbc.discovery.environment import Control, Environment, Observation
from pbc.discovery.force_lab import Run, replay_entry
from pbc.discovery.gravity import radial_period
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
TOLERANCE = 0.05  # the largest error of the scored worlds that recovers the law
SEED = 0
CONDITION = "partial"  # told the names of the parameters, not the law
# The judge's configuration: the hidden law. Never on a page.
WORLD = {"strength": 17.3, "exponent": 2.17, "short": 2000.0, "length": 0.07}
# The held-out worlds, in the order of the page; the last is reported apart.
WORLDS = ("interpolation", "farther", "heavier", "orbits", "closer")
SCORED = WORLDS[:-1]
INTERPOLATION_SEED = 345  # draws the unprobed settings within the bounds


class ShortRangeForceEnvironment(Environment):
    """The force on a test mass at a distance from a fixed centre: the
    central force of D1 and a hidden short-range term."""

    name = "short-range-force"
    controls = (
        Control("distance", "m", 1.0, 4.0, "distance from the centre"),
        Control("mass", "kg", 0.5, 5.0, "mass of the test body"),
    )
    observation = Observation("force", "N", 0.02, "attraction toward the centre")
    claim = (
        Control("strength", "N m^p/kg", 0.1, 100.0, "coefficient of the law"),
        Control("exponent", "1", 0.0, 6.0, "power p of the distance"),
    )
    family = "force = strength mass distance^-exponent"
    starts = ((10.0, 2.0), (30.0, 1.0), (5.0, 3.0))
    # The worlds of the suite that are settings of the controls.
    _farther = (
        {"distance": 6.0, "mass": 1.0},
        {"distance": 9.0, "mass": 2.0},
        {"distance": 12.0, "mass": 4.0},
    )
    _heavier = (
        {"distance": 1.5, "mass": 20.0},
        {"distance": 2.5, "mass": 50.0},
        {"distance": 3.5, "mass": 100.0},
    )
    _closer = (
        {"distance": 0.2, "mass": 1.0},
        {"distance": 0.3, "mass": 2.0},
    )
    # Orbits of a 1 kg body started at an apsis (m) with a speed (m/s)
    # perpendicular to the radius; their periapses stay beyond the bounds'
    # nearest distance.
    _orbits = (
        {"apsis": 3.0, "speed": 1.9},
        {"apsis": 6.0, "speed": 1.2},
        {"apsis": 10.0, "speed": 0.85},
    )
    _ORBIT_MASS = 1.0  # kg

    def __init__(
        self,
        *,
        strength: float = 20.0,
        exponent: float = 2.0,
        short: float = 0.0,
        length: float = 0.1,
        budget: int = 30,
        seed: int = 0,
    ):
        super().__init__(budget=budget, seed=seed)
        self._strength = strength
        self._exponent = exponent
        self._short = short
        self._length = length
        rng = np.random.default_rng(INTERPOLATION_SEED)
        self._interpolation = tuple(
            {c.name: float(rng.uniform(c.low, c.high)) for c in self.controls}
            for _ in range(5)
        )
        self._held_out = (
            self._interpolation + self._farther + self._heavier + self._closer
        )
        self._periods: tuple[float, ...] | None = None

    def __repr__(self) -> str:
        return f"ShortRangeForceEnvironment(budget={self.budget}, seed={self.seed})"

    def _law(self, settings):
        m, r = settings["mass"], settings["distance"]
        return self._strength * m * r**-self._exponent + self._short * m * math.exp(
            -r / self._length
        )

    def predict(self, claim, settings):
        return float(
            claim["strength"]
            * settings["mass"]
            * settings["distance"] ** -claim["exponent"]
        )

    # region: judge
    def generalisation(
        self, predictor: Callable[[Mapping[str, float]], float]
    ) -> dict[str, float]:
        """The error of the force ``predictor`` in each held-out world of
        ``WORLDS``: the root-mean-square relative error of the force at the
        settings of a world, or of the radial periods of the orbits; ``inf``
        where a prediction is not a number or an orbit has no period.

        This is the judge's call. It gives one number per world about a
        prediction and is in no allowlist."""
        errors = {
            "interpolation": self._force_error(predictor, self._interpolation),
            "farther": self._force_error(predictor, self._farther),
            "heavier": self._force_error(predictor, self._heavier),
            "orbits": self._orbit_error(predictor),
            "closer": self._force_error(predictor, self._closer),
        }
        return {w: errors[w] for w in WORLDS}

    def score_predictor(
        self, predictor: Callable[[Mapping[str, float]], float]
    ) -> float:
        """The largest error of ``predictor`` over the scored worlds."""
        errors = self.generalisation(predictor)
        return max(errors[w] for w in SCORED)

    def generalisation_of(self, claim: Mapping[str, float]) -> dict[str, float]:
        """``generalisation`` of a claim of the family."""
        return self.generalisation(lambda s: self.predict(claim, s))

    # endregion: judge

    def _force_error(self, predictor, settings) -> float:
        try:
            predicted = np.array([predictor(s) for s in settings], dtype=float)
        except ArithmeticError, ValueError, TypeError, KeyError:
            return math.inf
        if not np.all(np.isfinite(predicted)):
            return math.inf
        truth = np.array([self._law(s) for s in settings])
        return float(np.sqrt(np.mean(((predicted - truth) / truth) ** 2)))

    def _orbit_error(self, predictor) -> float:
        if self._periods is None:
            self._periods = tuple(self._period(self._law, o) for o in self._orbits)
        predicted = np.array([self._period(predictor, o) for o in self._orbits])
        if not np.all(np.isfinite(predicted)):
            return math.inf
        truth = np.array(self._periods)
        return float(np.sqrt(np.mean(((predicted - truth) / truth) ** 2)))

    def _period(self, predictor, orbit: Mapping[str, float]) -> float:
        mass = self._ORBIT_MASS

        def acceleration(r: float) -> float:
            return -float(predictor({"distance": float(r), "mass": mass})) / mass

        try:
            return radial_period(acceleration, orbit["apsis"], orbit["speed"])
        except ArithmeticError, ValueError, TypeError, KeyError:
            return math.nan


@dataclass(frozen=True)
class GeneralisationProtocol(Protocol):
    """The protocol of the lesson: its environment is the force with a
    short-range term, which the protocols of D1 to D3 do not list."""

    def make(self, seed: int) -> ShortRangeForceEnvironment:
        return ShortRangeForceEnvironment(budget=self.budget, seed=seed, **self.world)

    def held_out_settings(self) -> tuple[dict[str, float], ...]:
        """The held-out worlds that are settings of the controls."""
        return tuple(dict(s) for s in self.make(SEED)._held_out)


PROTOCOL = GeneralisationProtocol(
    version="f98-generalisation-1",
    environment=ShortRangeForceEnvironment.name,
    world=WORLD,
    budget=BUDGET,
    seeds=(SEED,),
    tolerance=TOLERANCE,
    max_steps=MAX_STEPS,
)

# Who produced the recording, and when (the plan of Issue #345, "Recording").
MODEL = "claude-opus-5-5 in a Claude Code session"
RECORDED = "2026-10-30"
FIXTURE = "replay.json"


def environment() -> ShortRangeForceEnvironment:
    """A fresh environment of the protocol, with its seed."""
    return PROTOCOL.make(SEED)


def task() -> tuple[str, str]:
    """The system prompt and the task (``pbc.discovery.prompts``)."""
    return prompts(environment(), CONDITION)


RUN = Run(
    "generalisation",
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
        cost=CostRecord(6, 17, None, None, None),
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


def force_library() -> dict:
    """The candidate terms of the sparse baseline: the mass over whole powers
    of the distance. Terms are public."""
    return {
        f"mass*distance^-{n}": (lambda s, n=n: s["mass"] * s["distance"] ** -n)
        for n in range(5)
    }


def baselines() -> tuple[BaselineResult, ...]:
    """The baselines without a model with the protocol's budget: least
    squares of the family on a grid and on random settings, and sparse
    identification on the grid."""
    world = environment()
    grid = grid_probe(world)
    scattered = random_probe(world, SEED)
    results = (
        least_squares(world, grid, "grid + least squares"),
        least_squares(world, scattered, "random + least squares"),
        sparse_identification(
            world, grid, force_library(), name="grid + sparse identification"
        ),
    )
    world.reset()
    return results


def generalisation_of(result: BaselineResult) -> dict[str, float]:
    """The error of a baseline's claim in each held-out world; a sum of
    terms is scored as a predictor."""
    world = environment()
    if result.claim is None:
        return dict.fromkeys(WORLDS, math.inf)
    if set(result.claim) == {"strength", "exponent"}:
        return world.generalisation_of(result.claim)
    terms = force_library()
    claim = result.claim
    return world.generalisation(
        lambda s: sum(c * terms[t](s) for t, c in claim.items())
    )


def recovered(result: BaselineResult) -> bool:
    """Whether a baseline recovered the law: a fit consistent with the noise
    whose claim is within the tolerance in every scored world."""
    return result.success and result.held_out_error <= TOLERANCE


def period_sensitivity(
    claim: Mapping[str, float], step: float = 1e-4
) -> tuple[float, ...]:
    """For each orbit of the suite, the magnitude of ``d ln T / d ln
    strength``: the relative change of the radial period per relative change
    of the strength of ``claim``, the start held fixed, by central
    differences. Above one, the orbit amplifies an error of the strength.

    For an inverse square it is ``3/2 x/(2-x) + 1/2`` with ``x = v₀²r₀/(GM)``
    (D4), above one only for ``x > 1/2``: it depends on the orbits chosen."""
    world = environment()

    def period(factor: float, orbit) -> float:
        scaled = {**claim, "strength": claim["strength"] * factor}
        return world._period(lambda s: world.predict(scaled, s), orbit)

    return tuple(
        abs(math.log(period(1 + step, o)) - math.log(period(1 - step, o))) / (2 * step)
        for o in world._orbits
    )


@dataclass(frozen=True)
class Reach:
    """How close the probes of a run came to a held-out world."""

    world: str
    settings: int  # how many settings of the controls the world has
    outside_bounds: bool  # every one of them lies outside the bounds
    nearest: float  # the smallest distance from a probe, in ranges of the controls
    probed: int  # held-out settings a probe of the run hit exactly


def reach(data: Dataset) -> tuple[Reach, ...]:
    """For each held-out world that is a set of settings of the controls,
    the nearest probe of ``data``, the distance measured in units of each
    control's range. The orbits are no setting of the controls: no tool
    starts one."""
    world = environment()
    worlds = {
        "interpolation": world._interpolation,
        "farther": world._farther,
        "heavier": world._heavier,
        "closer": world._closer,
    }
    span = {c.name: c.high - c.low for c in world.controls}
    found = []
    for name, settings in worlds.items():
        gaps = [
            math.sqrt(sum(((s[k] - p[k]) / span[k]) ** 2 for k in span))
            for s in settings
            for p in data.settings
        ]
        inside = [
            all(c.low <= s[c.name] <= c.high for c in world.controls) for s in settings
        ]
        found.append(
            Reach(
                name,
                len(settings),
                not any(inside),
                min(gaps) if gaps else math.inf,
                sum(gap == 0.0 for gap in gaps),
            )
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
    print(f"\nLargest held-out error {score.held_out_error:.3g}: {score.outcome}\n")
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
