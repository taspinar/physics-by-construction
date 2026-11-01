"""Lesson D11: hidden forces and unobserved variables (F98;
``docs/discovery-protocol.md``, "Latent effects").

The environment is a fall: a body of a set mass is released from rest, and
the distance it has fallen at a set time is read with noise. Besides gravity
the body feels two effects nobody sees: a constant force against the fall
(a buoyancy or a hidden pull) and linear drag. With ``a = g - F/m`` and
``k = b/m`` the distance is

    distance = (a/k) (time - (1 - exp(-k time))/k),

which is ``a time^2/2`` when there is no drag. A claim is ``g``, the hidden
force ``F``, and the drag coefficient ``b``; it is scored at masses and
times outside the bounds.

At one mass the hidden force only lowers the acceleration, so a record taken
at one mass cannot tell it from a weaker gravity, and at short times drag
cannot be told from either. The lesson measures that ambiguity on an
observational record and chooses the experiment that resolves it: the
setting where the laws the record cannot tell apart disagree most.

The protocol, fixed before the run was recorded, the frozen run, and its
score recomputed from the tool calls. The hidden world is the judge's
configuration: no prompt, tool, or page shows it.
"""

import argparse
import datetime
import itertools
import math
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from pbc.agents.loop import Step, Transcript, run
from pbc.agents.replay import Recording, save_recording
from pbc.data.fit import FitResult, fit_curve
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

BUDGET = 16
MAX_STEPS = 12
TOLERANCE = 0.05  # held-out error that counts as recovering the law
SEED = 0
CONDITION = "full"  # told the form of the law, not which effects are present
# The judge's configuration: the hidden world. Never on a page.
WORLD = {"g": 6.83, "hidden_force": 0.947, "drag": 0.0832}
# Below this k t the series of the fall is used instead of its closed form.
SERIES_BELOW = 1e-4


def fall(g: float, force: float, drag: float, mass: float, time: float) -> float:
    """The distance fallen from rest after ``time`` (s) by a body of ``mass``
    (kg) under gravity ``g`` (m/s²), a constant ``force`` (N) against the
    fall, and linear drag of coefficient ``drag`` (kg/s)."""
    a = g - force / mass
    k = drag / mass
    kt = k * time
    if abs(kt) < SERIES_BELOW:
        return a * time**2 / 2 * (1 - kt / 3 + kt**2 / 12)
    return a / k * (time + math.expm1(-kt) / k)


class HiddenForceEnvironment(Environment):
    """The distance a body has fallen, under gravity, a hidden constant force
    against the fall, and hidden linear drag."""

    name = "hidden-force"
    controls = (
        Control("mass", "kg", 0.2, 2.0, "mass of the body"),
        Control("time", "s", 0.2, 2.0, "time since the release from rest"),
    )
    observation = Observation("distance", "m", 0.01, "distance fallen")
    claim = (
        Control("g", "m/s^2", 0.1, 30.0, "gravity of the world"),
        Control("hidden_force", "N", -5.0, 5.0, "constant force against the fall"),
        Control("drag", "kg/s", 0.0, 2.0, "coefficient b of the drag force b v"),
    )
    family = (
        "distance = (a/k) (time - (1 - exp(-k time))/k), with a = g -"
        " hidden_force/mass and k = drag/mass (distance = a time^2/2 when drag"
        " is zero)"
    )
    starts = ((9.8, 0.0, 0.0), (5.0, 1.0, 0.1), (7.0, 0.5, 0.5))
    # Lighter and heavier bodies than the bounds, falling for longer.
    _held_out = (
        {"mass": 0.16, "time": 3.0},
        {"mass": 5.0, "time": 4.0},
        {"mass": 20.0, "time": 5.0},
    )

    def __init__(
        self,
        *,
        g: float = 9.81,
        hidden_force: float = 0.0,
        drag: float = 0.0,
        budget: int = 30,
        seed: int = 0,
    ):
        super().__init__(budget=budget, seed=seed)
        self._truth = {"g": g, "hidden_force": hidden_force, "drag": drag}

    def __repr__(self) -> str:
        return f"HiddenForceEnvironment(budget={self.budget}, seed={self.seed})"

    def _law(self, settings):
        return self.predict(self._truth, settings)

    def predict(self, claim, settings):
        return fall(
            claim["g"],
            claim["hidden_force"],
            claim["drag"],
            settings["mass"],
            settings["time"],
        )


@dataclass(frozen=True)
class LatentProtocol(Protocol):
    """The protocol of the lesson: its environment is the fall, which the
    protocols of D1 to D3 do not list."""

    def make(self, seed: int) -> HiddenForceEnvironment:
        return HiddenForceEnvironment(budget=self.budget, seed=seed, **self.world)

    def held_out_settings(self) -> tuple[dict[str, float], ...]:
        return tuple(dict(s) for s in HiddenForceEnvironment._held_out)


PROTOCOL = LatentProtocol(
    version="f98-latent-1",
    environment=HiddenForceEnvironment.name,
    world=WORLD,
    budget=BUDGET,
    seeds=(SEED,),
    tolerance=TOLERANCE,
    max_steps=MAX_STEPS,
)

# What the agent is told of the latent effects, beyond the task of D2.
LATENT = (
    "The body may feel forces you cannot see; report an effect you find"
    " absent as zero. The noise has a standard deviation of 0.01 m."
)

# Who produced the recording, and when (the plan of Issue #345, "Recording").
MODEL = "claude-opus-5-5 in a Claude Code session"
RECORDED = "2026-10-30"
FIXTURE = "replay.json"


def environment() -> HiddenForceEnvironment:
    """A fresh fall of the protocol, with its seed."""
    return PROTOCOL.make(SEED)


def task() -> tuple[str, str]:
    """The system prompt and the task: those of ``pbc.discovery.prompts``,
    with what the agent is told of the latent effects."""
    system, text = prompts(environment(), CONDITION)
    return system, f"{text} {LATENT}"


RUN = Run(
    "latent",
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


# Hypotheses about the latent effects: the parameters each holds at zero.
HYPOTHESES: dict[str, tuple[str, ...]] = {
    "free fall": ("hidden_force", "drag"),
    "a hidden force": ("drag",),
    "drag": ("hidden_force",),
    "a hidden force and drag": (),
}


def fit_hypothesis(data: Dataset, held: Mapping[str, float]) -> FitResult | None:
    """The family fitted to ``data`` by weighted least squares from each
    start, the parameters of ``held`` held at the values given; the best fit
    kept, ``None`` when none can be made."""
    world = environment()
    names = tuple(c.name for c in world.claim if c.name not in held)
    bounds = (
        [c.low for c in world.claim if c.name in names],
        [c.high for c in world.claim if c.name in names],
    )

    def curve(index: np.ndarray, *params: float) -> np.ndarray:
        claim = dict(held) | dict(zip(names, params, strict=True))
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
class Verdict:
    """A hypothesis fitted to a set of readings.

    ``held_out_error`` is ``None`` when the readings do not determine the
    parameters: they fix only a combination of them (at one mass, ``g -
    F/m``), every point of the line it leaves free fits equally well, and the
    fit stops at one of them by its start and the rounding of the machine.
    The laws on that line predict the held-out settings differently, so no
    single held-out error belongs to the hypothesis."""

    hypothesis: str
    chi2: float
    dof: int
    consistent: bool
    identifiable: bool
    claim: Mapping[str, float]
    held_out_error: float | None


def judge_hypotheses(data: Dataset) -> tuple[Verdict, ...]:
    """Each of ``HYPOTHESES`` fitted to ``data``, with the chi-square rule,
    whether the readings determine its parameters, and the judge's score of
    its best fit when they do."""
    world = environment()
    found = []
    for name, zero in HYPOTHESES.items():
        held = {p: 0.0 for p in zero}
        fit = fit_hypothesis(data, held)
        if fit is None:
            continue
        claim = held | dict(zip(fit.names, map(float, fit.params), strict=True))
        identifiable = all(fit.identifiable)
        found.append(
            Verdict(
                name,
                fit.chi2,
                fit.dof,
                consistent(fit.chi2, fit.dof),
                identifiable,
                claim,
                world.held_out_error(claim) if identifiable else None,
            )
        )
    return tuple(found)


# The observational record: one mass, short times, taken by someone else.
RECORD_MASS = 1.0  # kg
RECORD_TIMES = tuple(float(t) for t in np.linspace(0.2, 1.0, 9))  # s
# The laws the record is asked to tell apart: g fitted, the others held here.
FORCES = (0.0, 0.5, 1.0, 1.5, 2.0)  # N
DRAGS = (0.0, 0.05, 0.1, 0.2)  # kg/s
# Where a disambiguating experiment may be done.
MASSES = tuple(float(m) for m in np.linspace(0.2, 2.0, 10))  # kg
TIMES = (0.5, 1.0, 1.5, 2.0)  # s


def record() -> Dataset:
    """The observational record: readings at one mass and short times,
    taken from a fresh fall of the protocol."""
    world = environment()
    world.reset()
    settings = tuple({"mass": RECORD_MASS, "time": t} for t in RECORD_TIMES)
    values = np.array([world.measure(**s)["distance"] for s in settings])
    return Dataset(settings, values, world.observation.sigma)


def rivals(data: Dataset) -> tuple[dict[str, float], ...]:
    """The laws ``data`` cannot tell apart: for each hidden force of
    ``FORCES`` and drag of ``DRAGS``, gravity fitted to the readings; those
    whose chi-square passes the rule are kept."""
    found = []
    for force, drag in itertools.product(FORCES, DRAGS):
        held = {"hidden_force": force, "drag": drag}
        fit = fit_hypothesis(data, held)
        if fit is not None and consistent(fit.chi2, fit.dof):
            found.append(held | {"g": fit.value("g")})
    return tuple(found)


def disagreement(
    laws: tuple[dict[str, float], ...], settings: Mapping[str, float]
) -> float:
    """The spread of the distances that ``laws`` predict at ``settings``, in
    standard deviations of the noise: how well a reading there tells them
    apart."""
    world = environment()
    predicted = [world.predict(law, settings) for law in laws]
    return (max(predicted) - min(predicted)) / world.observation.sigma


def disambiguating_experiment(
    laws: tuple[dict[str, float], ...],
) -> tuple[dict[str, float], dict[tuple[float, float], float]]:
    """The setting of ``MASSES`` and ``TIMES`` where ``laws`` disagree most,
    and the disagreement at every setting."""
    spread = {
        (m, t): disagreement(laws, {"mass": m, "time": t})
        for m, t in itertools.product(MASSES, TIMES)
    }
    mass, time = max(spread, key=spread.__getitem__)
    return {"mass": mass, "time": time}, spread


def with_readings_at(data: Dataset, mass: float) -> Dataset:
    """``data`` with readings added at ``mass``, one at each of ``TIMES``,
    taken from a fresh fall of the protocol."""
    world = environment()
    world.reset()
    added = tuple({"mass": mass, "time": t} for t in TIMES)
    values = [world.measure(**s)["distance"] for s in added]
    return Dataset(
        data.settings + added, np.concatenate([data.values, values]), data.sigma
    )


def fall_library() -> dict:
    """The candidate terms of the sparse baseline: the free fall and the
    first corrections of a hidden force and of drag, as powers of the time
    over powers of the mass. Terms are public."""
    return {
        "time^2": lambda s: s["time"] ** 2,
        "time^2/mass": lambda s: s["time"] ** 2 / s["mass"],
        "time^3/mass": lambda s: s["time"] ** 3 / s["mass"],
        "time^3/mass^2": lambda s: s["time"] ** 3 / s["mass"] ** 2,
        "time^4/mass^2": lambda s: s["time"] ** 4 / s["mass"] ** 2,
    }


def familiar_law(data: Dataset, name: str) -> BaselineResult:
    """Free fall, gravity only, fitted to ``data``: the familiar law, which
    succeeds only when its fit is consistent with the noise."""
    world = environment()
    fit = fit_hypothesis(data, {"hidden_force": 0.0, "drag": 0.0})
    if fit is None:
        return BaselineResult(name, len(data.values), False, None, math.inf, "no fit")
    claim = {"g": fit.value("g"), "hidden_force": 0.0, "drag": 0.0}
    reason = ""
    if not consistent(fit.chi2, fit.dof):
        reason = (
            f"chi-square {fit.chi2:.3g} for {fit.dof} degrees of freedom: free"
            " fall does not describe the measurements"
        )
    return BaselineResult(
        name,
        len(data.values),
        not reason,
        claim,
        world.held_out_error(claim),
        reason,
    )


def baselines() -> tuple[BaselineResult, ...]:
    """The baselines without a model with the protocol's budget: least
    squares of the family on a grid and on random settings, sparse
    identification on the grid, and free fall on the grid."""
    world = environment()
    grid = grid_probe(world)
    scattered = random_probe(world, SEED)
    results = (
        least_squares(world, grid, "grid + least squares"),
        least_squares(world, scattered, "random + least squares"),
        sparse_identification(
            world, grid, fall_library(), name="grid + sparse identification"
        ),
        familiar_law(grid, "grid + free fall"),
    )
    world.reset()
    return results


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
