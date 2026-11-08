"""Lesson EV1: a physics reasoning benchmark built from the site's own
lessons, scored by the build over seeds.

Each seed gives twelve items of four kinds: problems stated in words, visual
affordances (what the setup of a picture allows), tool affordances (what a
physical instrument can measure of it), and counterfactual predictions (what
a picture would show if one thing changed). Every item comes from a lesson:
the drag-free range, the large-amplitude pendulum, the oscillator, and the
elastic collision of the mechanics course; the two pictures are verified
figures of the lessons on the harmonic oscillator and on projectile motion
with drag, drawn again by their own ``draw_`` functions. The seed draws the
numbers of each item and the order of a choice's options.

Every answer is computed by the build from the code of the lesson it comes
from (``Item.solve``) and, where a second route exists, checked against it
(``Item.verify``: a simulation against a closed form, a quadrature against
an elliptic integral). The model answers through the one software tool
``answer`` of ``pbc.agents.vision``, which records and acknowledges; the
physical tools are in the items. ``outcome`` keeps a failure of the software
interface (a refused call, an item left without an accepted answer) apart
from a failure of reasoning (an accepted answer that is wrong).

Run it live on your machine (needs ``OPENAI_API_KEY`` and the optional
dependency)::

    uv run --extra openai python -m pbc.agents.reasoning_benchmark

Record the replay fixtures of the lesson from a live run (maintainer)::

    uv run --extra openai python -m pbc.agents.reasoning_benchmark --record
"""

import argparse
import datetime
import math
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import numpy as np
from scipy.constants import g
from scipy.integrate import quad
from scipy.stats import t as student

from pbc.agents.loop import Step, Transcript, run
from pbc.agents.messages import Picture
from pbc.agents.replay import Recording, load_recording, replay, save_recording
from pbc.agents.secrets import Secret, redact
from pbc.agents.tools import Allowlist
from pbc.agents.vision import READING_TOLERANCE, answer_sheet, answers
from pbc.experiment import encode
from pbc.mechanics.dynamics import State, newton, simulate
from pbc.mechanics.experiments import harmonic_oscillator as spring_lesson
from pbc.mechanics.experiments import projectile_with_drag as throw
from pbc.mechanics.integrators import INTEGRATORS
from pbc.mechanics.oscillator import angular_frequency, harmonic_motion, spring
from pbc.mechanics.particles import (
    hard_sphere_collision,
    interacting,
    soft_sphere,
    stack,
    unstack,
)
from pbc.mechanics.pendulum import pendulum_period
from pbc.mechanics.projectile import drag_free_range, projectile_range

verlet = INTEGRATORS[2]

# The four kinds of item, in the order of the page.
KINDS = ("problem", "visual affordance", "tool affordance", "counterfactual")

# A computed answer is correct within this fraction of the truth; a reading
# off a picture within the reading tolerance of AI6. A whole number must be
# exact.
COMPUTED_TOLERANCE = 0.01
WHOLE = 0.0

# The keys of the pictures' items do not change when the picture is read
# within this fraction of its value.
READING_MARGIN = 0.05

# The seeds of the benchmark, fixed before any run.
SEEDS = (1, 2, 3, 4, 5)

MAX_STEPS = 8  # model messages per run: twelve answers, at most four a message
TOLERANCE = 1e-9  # the acknowledgements are exact
PROMPT_VERSION = 1

DIRECTORY = "site/lessons/agents-llm/21-physics-reasoning-benchmarks"
RECORD_COMMAND = (
    "uv run --extra openai python -m pbc.agents.reasoning_benchmark --record"
    " (with OPENAI_API_KEY set)"
)

# The precision a simulation must reach to confirm a closed form.
CHECK_TOLERANCE = 2e-3


@dataclass(frozen=True)
class Item:
    """One item of a seed's benchmark.

    ``solve`` computes the answer with the code of the lesson ``source``;
    ``verify``, when there is one, computes it again by another route. A
    choice item is answered by the option's number, counted from 1; a numeric
    one by a number in ``unit`` within ``low`` and ``high``, correct within
    ``tolerance`` of the truth (relative), or exactly when it is ``WHOLE``.
    The attributes ``number``, ``options``, and ``numeric`` are those the
    answer sheet of ``pbc.agents.vision`` reads.
    """

    number: int
    kind: str
    source: str
    text: str
    solve: Callable[[], float]
    picture: str = ""
    options: tuple[str, ...] = ()
    unit: str = ""
    low: float = 0.0
    high: float = 0.0
    tolerance: float = COMPUTED_TOLERANCE
    verify: Callable[[], float] | None = None

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"unknown kind {self.kind!r}")
        if not self.options and not self.low < self.high:
            raise ValueError(f"item {self.number} has no options and no range")

    @property
    def numeric(self) -> bool:
        return not self.options

    def prompt(self) -> str:
        """The item as the task states it."""
        if self.options:
            listed = "; ".join(f"{k} {o}" for k, o in enumerate(self.options, 1))
            asked = f"Answer with the option's number: {listed}."
        elif self.tolerance == WHOLE:
            asked = (
                f"Answer with a whole number between {self.low:g} and {self.high:g}."
            )
        else:
            asked = f"Answer in {self.unit}, between {self.low:g} and {self.high:g}."
        where = f"(picture {self.picture}) " if self.picture else ""
        return f"{self.number}. {where}{self.text} {asked}"


# region: pictures
@cache
def oscillation():
    """The explicit Euler run that picture A plots, as its lesson makes it."""
    return simulate(
        spring_lesson.released,
        spring_lesson.oscillator,
        spring_lesson.dt,
        spring_lesson.n_periods * spring_lesson.steps_per_period,
    )


@cache
def range_curves():
    """The ranges with and without drag that picture B plots, as its lesson
    computes them."""
    with_drag = np.array(
        [
            projectile_range(throw.speed, a, throw.mass, throw.c, throw.scan_dt)
            for a in throw.angles
        ]
    )
    without = np.array(
        [
            projectile_range(throw.speed, a, throw.mass, 0.0, throw.scan_dt)
            for a in throw.angles
        ]
    )
    return with_drag, without


def draw_oscillation():
    """Picture A, drawn by the lesson on the harmonic oscillator."""
    return spring_lesson.draw_oscillator_position(oscillation())


def draw_ranges():
    """Picture B, drawn by the lesson on projectile motion with drag."""
    return throw.draw_range_against_angle(*range_curves())


CAPTIONS = {
    "A": "the position against time of a mass on a spring, released from rest,"
    " exact and simulated with explicit Euler (from a lesson on the harmonic"
    " oscillator)",
    "B": "the range of a ball thrown from flat ground against its launch angle,"
    " at one launch speed, with quadratic air drag and without it (from a lesson"
    " on projectile motion with drag)",
}
SOURCES = {
    "A": ("harmonic-oscillator", "fig-oscillator-position", draw_oscillation),
    "B": ("projectile-with-drag", "fig-range-against-angle", draw_ranges),
}


def pictures() -> tuple[Picture, ...]:
    """The two pictures, drawn again by their lessons' code."""
    return tuple(Picture(label, encode(SOURCES[label][2])) for label in SOURCES)


# endregion: pictures


# region: physics
def oscillator_period(mass: float = spring_lesson.mass) -> float:
    """The period of the spring of picture A with ``mass`` on it, in s."""
    return 2.0 * math.pi / angular_frequency(mass, spring_lesson.k)


def measured_period(amplitude: float) -> float:
    """The period of the exact motion of picture A released at ``amplitude``
    (m): the time of the first return to the largest excursion, in s."""
    period = oscillator_period()
    times = np.linspace(0.0, 1.5 * period, 300_001)
    x = harmonic_motion(
        State(t=0.0, x=amplitude, v=0.0), spring_lesson.mass, spring_lesson.k, times
    ).x[:, 0]
    later = times > 0.5 * period
    return float(times[later][np.argmax(x[later])])


@cache
def best_throw(mass: float = throw.mass) -> tuple[float, float]:
    """The launch angle (degrees) and range (m) of the longest throw with
    drag at the speed of picture B, for a ball of ``mass`` and its size."""
    angle, furthest = throw.best_angle(throw.c, mass)
    return float(angle), float(furthest)


def side(angle: float, reference: float) -> int:
    """0, 1, or 2: ``angle`` below, within half a degree of, or above
    ``reference``."""
    if abs(angle - reference) <= 0.5:
        return 1
    return 0 if angle < reference else 2


def simulated_range(speed: float, angle: float) -> float:
    """The drag-free range simulated with a fine step, in m."""
    return projectile_range(speed, angle, throw.mass, 0.0, 1e-4)


def pendulum_quadrature(length: float, amplitude: float) -> float:
    """The period of a pendulum (s) by numerical quadrature of the energy
    integral, without the elliptic function."""
    k = math.sin(0.5 * amplitude)
    integral, _ = quad(
        lambda phi: 1.0 / math.sqrt(1.0 - (k * math.sin(phi)) ** 2), 0.0, math.pi / 2
    )
    return 4.0 * math.sqrt(length / g) * integral


def equilibrium_speed(mass: float, k: float, amplitude: float) -> float:
    """The speed of the oscillator at equilibrium from its exact motion, in
    m/s."""
    quarter = 0.5 * math.pi / angular_frequency(mass, k)
    motion = harmonic_motion(State(t=0.0, x=amplitude, v=0.0), mass, k, [quarter])
    return abs(float(motion.v[0, 0]))


def simulated_equilibrium_speed(mass: float, k: float, amplitude: float) -> float:
    """The same speed simulated with velocity Verlet until the mass first
    crosses equilibrium, interpolated within the last step, in m/s."""
    dt = 1e-4 * 2.0 * math.pi / angular_frequency(mass, k)
    run_ = simulate(
        State(t=0.0, x=amplitude, v=0.0),
        newton(mass, spring(k)),
        dt,
        10**6,
        step=verlet.step,
        until=lambda state: state.x[0] <= 0.0,
    )
    x0, x1 = run_.x[-2, 0], run_.x[-1, 0]
    v0, v1 = run_.v[-2, 0], run_.v[-1, 0]
    return abs(float(v0 + (v1 - v0) * x0 / (x0 - x1)))


def collision_velocity(m1: float, m2: float, v1: float) -> float:
    """The velocity (m/s) of the second body after an elastic head-on
    collision, the first moving at ``v1`` towards it at rest."""
    return float(hard_sphere_collision(m1, [v1], m2, [0.0], [-1.0])[1][0])


def soft_collision_velocity(m1: float, m2: float, v1: float) -> float:
    """The same velocity from a simulation of two stiff soft spheres with
    velocity Verlet, read after they part."""
    diameter, stiffness = 0.2, 1e5
    start = State(t=0.0, x=stack([[0.0], [0.5]]), v=stack([[v1], [0.0]]))
    contact = math.pi * math.sqrt(m1 * m2 / (m1 + m2) / stiffness)
    duration = 0.6 / v1 + 4.0 * contact
    dt = contact / 200
    trajectory = simulate(
        start,
        interacting([m1, m2], soft_sphere(stiffness, diameter)),
        dt,
        round(duration / dt),
        step=verlet.step,
    )
    return float(unstack(trajectory.v, 2)[-1, 1, 0])


# endregion: physics


def _round(value: float, digits: int) -> float:
    return float(round(value, digits))


def _shuffled(rng, options: Sequence[str]) -> tuple[str, ...]:
    """``options`` in an order drawn by ``rng``."""
    return tuple(options[int(i)] for i in rng.permutation(len(options)))


STOPWATCHES = (0.1, 0.15, 0.2, 0.25, 0.3)  # s, the error of one timing
PRECISIONS = (0.5, 1.0, 2.0)  # per cent


def periods_to_time(error: float, precision: float, period: float) -> int:
    """The fewest whole periods a timing of ``error`` (s) must span for the
    period to be known within ``precision`` per cent."""
    return math.ceil(error / (precision / 100.0 * period) - 1e-12)


def robust_stopwatches() -> list[tuple[float, float]]:
    """The pairs of stopwatch error and precision whose answer is the same
    for a period read within the reading margin."""
    period = oscillator_period()
    pairs = []
    for error in STOPWATCHES:
        for precision in PRECISIONS:
            answers_ = {
                periods_to_time(error, precision, period * f)
                for f in (1 - READING_MARGIN, 1.0, 1 + READING_MARGIN)
            }
            if len(answers_) == 1:
                pairs.append((error, precision))
    return pairs


SIDES = (
    "lower than 45 degrees",
    "within half a degree of 45",
    "higher than 45 degrees",
)
CHANGE = ("lower", "the same, within half a degree", "higher")


@cache
def items(seed: int) -> tuple[Item, ...]:
    """The twelve items of ``seed``, in the order of the task."""
    rng = np.random.default_rng(seed)

    # problems in words
    v, angle = _round(rng.uniform(12.0, 30.0), 1), int(rng.integers(20, 71))
    length, swing = _round(rng.uniform(0.3, 2.0), 2), int(rng.integers(40, 121))
    m, k, x0 = (
        _round(rng.uniform(0.2, 2.0), 2),
        _round(rng.uniform(5.0, 50.0), 1),
        _round(rng.uniform(0.05, 0.3), 2),
    )
    m1, m2, v1 = (
        _round(rng.uniform(0.5, 3.0), 2),
        _round(rng.uniform(0.5, 3.0), 2),
        _round(rng.uniform(1.0, 4.0), 2),
    )
    # visual affordances
    reach = _round(best_throw()[1] * float(rng.choice([0.75, 0.85, 1.15, 1.3])), 0)
    sides = _shuffled(rng, SIDES)
    # tool affordances
    pairs = robust_stopwatches()
    error, precision = pairs[int(rng.integers(len(pairs)))]
    planet = _round(rng.uniform(1.6, 25.0), 2)
    # counterfactuals
    heavier = float(rng.choice([0.25, 0.5, 2.0, 3.0, 4.0]))
    wider = float(rng.choice([0.5, 2.0, 3.0]))
    faster = float(rng.choice([0.6, 0.8, 1.2, 1.5]))
    ball = float(rng.choice([0.25, 0.5, 2.0, 4.0]))
    changes = _shuffled(rng, CHANGE)

    swing_rad = math.radians(swing)
    return (
        Item(
            1,
            "problem",
            "projectile-with-drag",
            f"A ball is launched from flat ground at {v:g} m/s, {angle} degrees"
            f" above the horizontal, without air resistance (g = {g:g} m/s²)."
            " How far from the launch point does it land?",
            lambda: drag_free_range(v, angle),
            unit="m",
            low=0.0,
            high=200.0,
            verify=lambda: simulated_range(v, angle),
        ),
        Item(
            2,
            "problem",
            "lagrangian-mechanics",
            f"A simple pendulum of length {length:g} m is released from rest at"
            f" {swing} degrees from the vertical (g = {g:g} m/s²). What is its"
            " period?",
            lambda: pendulum_period(length, swing_rad),
            unit="s",
            low=0.0,
            high=10.0,
            verify=lambda: pendulum_quadrature(length, swing_rad),
        ),
        Item(
            3,
            "problem",
            "harmonic-oscillator",
            f"A mass of {m:g} kg on a spring of constant {k:g} N/m slides without"
            f" friction. It is pulled {x0:g} m from equilibrium and released from"
            " rest. How fast does it move as it passes equilibrium?",
            lambda: equilibrium_speed(m, k, x0),
            unit="m/s",
            low=0.0,
            high=10.0,
            verify=lambda: simulated_equilibrium_speed(m, k, x0),
        ),
        Item(
            4,
            "problem",
            "momentum-and-collisions",
            f"A body of {m1:g} kg moving at {v1:g} m/s hits a body of {m2:g} kg at"
            " rest, head on and elastically. What is the velocity of the second"
            " body afterwards, positive in the first body's original direction?",
            lambda: collision_velocity(m1, m2, v1),
            unit="m/s",
            low=-10.0,
            high=10.0,
            verify=lambda: soft_collision_velocity(m1, m2, v1),
        ),
        Item(
            5,
            "visual affordance",
            "projectile-with-drag",
            "Thrown at the launch speed of the picture, with drag, can the ball be"
            f" made to land at least {reach:g} m away by choosing its launch angle?",
            lambda: 1 if best_throw()[1] >= reach else 2,
            picture="B",
            options=("yes", "no"),
        ),
        Item(
            6,
            "visual affordance",
            "projectile-with-drag",
            "With drag, the launch angle of the longest throw is:",
            lambda: sides.index(SIDES[side(best_throw()[0], 45.0)]) + 1,
            picture="B",
            options=sides,
        ),
        Item(
            7,
            "tool affordance",
            "harmonic-oscillator",
            "You time the oscillation of the exact motion with a hand stopwatch;"
            f" one timing, start and stop together, is uncertain by {error:g} s."
            " What is the fewest whole periods one timing must span for the"
            f" period to be known within {precision:g} per cent?",
            lambda: periods_to_time(error, precision, oscillator_period()),
            picture="A",
            low=1.0,
            high=1000.0,
            tolerance=WHOLE,
        ),
        Item(
            8,
            "tool affordance",
            "harmonic-oscillator",
            f"The mass is {spring_lesson.mass:g} kg. Hung from the same spring at"
            f" rest, on a planet where g = {planet:g} m/s², how far beyond its"
            " natural length is the spring stretched, as a ruler would read it?",
            lambda: spring_lesson.mass * planet / spring_lesson.k,
            picture="A",
            unit="m",
            low=0.0,
            high=20.0,
            tolerance=READING_TOLERANCE,
        ),
        Item(
            9,
            "counterfactual",
            "harmonic-oscillator",
            f"If the mass were {heavier:g} times as large, with the same spring,"
            " what would the period of the exact motion be?",
            lambda: oscillator_period(heavier * spring_lesson.mass),
            picture="A",
            unit="s",
            low=0.0,
            high=20.0,
            tolerance=READING_TOLERANCE,
        ),
        Item(
            10,
            "counterfactual",
            "harmonic-oscillator",
            f"If the mass were released from {wider:g} times as far from"
            " equilibrium, with the same mass and spring, what would the period of"
            " the exact motion be?",
            oscillator_period,
            picture="A",
            unit="s",
            low=0.0,
            high=20.0,
            tolerance=READING_TOLERANCE,
            verify=lambda: measured_period(wider * spring_lesson.released.x[0]),
        ),
        Item(
            11,
            "counterfactual",
            "projectile-with-drag",
            f"If the launch speed were {faster:g} times as large, without drag,"
            " how far would a throw at 45 degrees land?",
            lambda: drag_free_range(faster * throw.speed, 45.0),
            picture="B",
            unit="m",
            low=0.0,
            high=300.0,
            tolerance=READING_TOLERANCE,
            verify=lambda: simulated_range(faster * throw.speed, 45.0),
        ),
        Item(
            12,
            "counterfactual",
            "projectile-with-drag",
            f"If the ball were {ball:g} times as heavy, with the same size and the"
            " same launch speed, the launch angle of its longest throw with drag,"
            " compared with the picture's, would be:",
            lambda: (
                changes.index(
                    CHANGE[side(best_throw(ball * throw.mass)[0], best_throw()[0])]
                )
                + 1
            ),
            picture="B",
            options=changes,
        ),
    )


def key(seed: int) -> dict[int, float]:
    """The answer to every item of ``seed``, computed by the code of its
    lesson. Options are numbered from 1."""
    return {item.number: float(item.solve()) for item in items(seed)}


def checks(seed: int) -> dict[int, tuple[float, float]]:
    """For every item of ``seed`` with a second route, the answer of its
    lesson's code and that of the second route."""
    return {
        item.number: (float(item.solve()), float(item.verify()))
        for item in items(seed)
        if item.verify is not None
    }


# The key of every seed as computed when the runs were recorded (judge
# configuration, never in a tool or a prompt). A test compares it with the
# key: when the physics of a source lesson changes, the recordings answer
# other items and must be made again.
RECORDED_KEY: dict[int, dict[int, float]] = {
    1: {
        1: 41.1918,
        2: 1.99371,
        3: 0.504638,
        4: 3.33032,
        5: 1.0,
        6: 1.0,
        7: 7.0,
        8: 3.5475,
        9: 6.28319,
        10: 3.14159,
        11: 40.7886,
        12: 1.0,
    },
    2: {
        1: 21.7854,
        2: 2.81921,
        3: 2.13896,
        4: 2.19304,
        5: 1.0,
        6: 1.0,
        7: 3.0,
        8: 1.2775,
        9: 5.4414,
        10: 3.14159,
        11: 91.7745,
        12: 1.0,
    },
    3: {
        1: 15.7604,
        2: 2.76759,
        3: 0.434069,
        4: 4.18462,
        5: 1.0,
        6: 3.0,
        7: 2.0,
        8: 3.4225,
        9: 4.44288,
        10: 3.14159,
        11: 91.7745,
        12: 3.0,
    },
    4: {
        1: 67.5783,
        2: 3.20621,
        3: 1.34492,
        4: 5.24709,
        5: 1.0,
        6: 1.0,
        7: 7.0,
        8: 2.9175,
        9: 4.44288,
        10: 3.14159,
        11: 143.398,
        12: 1.0,
    },
    5: {
        1: 47.9162,
        2: 2.75101,
        3: 0.484259,
        4: 1.64131,
        5: 1.0,
        6: 1.0,
        7: 3.0,
        8: 1.7725,
        9: 2.22144,
        10: 3.14159,
        11: 40.7886,
        12: 2.0,
    },
}


SYSTEM = (
    "You answer the items of a physics benchmark. Use the tool answer once per"
    " item, with the item's number as its argument question; an answer cannot"
    " be changed and you are not told whether it is right. At most four tool"
    " calls of one message are run. Some items are"
    " about the two pictures attached to the task, A and B; the others are"
    " stated in full in words. Work each answer out before you give it, and"
    " when you cannot tell, give your best estimate. When every item is"
    " answered, end with a short message that names the items you are least"
    " sure of."
)


def task(seed: int) -> str:
    """The task of ``seed``: the pictures described, every item stated."""
    return (
        "Two pictures are attached; each is a figure of a physics course.\n"
        + "\n".join(f"Picture {label}: {CAPTIONS[label]}." for label in CAPTIONS)
        + "\n\nAnswer every item with the tool answer.\n"
        + "\n".join(item.prompt() for item in items(seed))
    )


def fixture(seed: int) -> str:
    return f"replay-seed-{seed}.json"


def sheet(seed: int) -> Allowlist:
    """A fresh answer sheet for one run of ``seed``."""
    return answer_sheet(items(seed))


@dataclass(frozen=True)
class Outcome:
    """One item of one run: the accepted answer (None when there is none),
    the recomputed truth, the refused calls that named it, and the verdict:
    ``correct``, ``wrong`` (a reasoning failure), or ``unanswered`` (an
    interface failure)."""

    item: Item
    answer: float | None
    truth: float
    refused: int
    verdict: str


def correct(item: Item, value: float, truth: float) -> bool:
    """A choice or a whole number is correct when it is the truth; another
    number when it is within the item's tolerance of it."""
    if item.options or item.tolerance == WHOLE:
        return value == truth
    return abs(value - truth) <= item.tolerance * abs(truth)


def refusals(transcript: Transcript) -> list[dict]:
    """Every refused call of a run: the item it named (None when it named
    none the sheet has) and the reason."""
    found = []
    for step in transcript.steps:
        for call, result in zip(step.message.tool_calls, step.results, strict=True):
            if not result.ok:
                named = (
                    call.arguments.get("question")
                    if isinstance(call.arguments, dict)
                    else None
                )
                found.append({"item": named, "error": result.content.get("error", "")})
    return found


def outcome(
    benchmark: Sequence[Item], truths: Mapping[int, float], transcript: Transcript
) -> list[Outcome]:
    """Every item of a run, scored from the accepted calls of its transcript;
    the text of the model is not read."""
    given = answers(transcript)
    refused = refusals(transcript)
    scored = []
    for item in benchmark:
        value = given.get(item.number, {}).get("value")
        truth = truths[item.number]
        if value is None:
            verdict = "unanswered"
        else:
            verdict = "correct" if correct(item, value, truth) else "wrong"
        scored.append(
            Outcome(
                item,
                value,
                truth,
                sum(r["item"] == item.number for r in refused),
                verdict,
            )
        )
    return scored


def chance(item: Item, truth: float) -> float:
    """The probability that a uniform guess in the stated options or range
    is correct."""
    if item.options:
        return 1.0 / len(item.options)
    if item.tolerance == WHOLE:
        return 1.0 / (item.high - item.low + 1)
    width = item.high - item.low
    low = max(item.low, truth - item.tolerance * abs(truth))
    high = min(item.high, truth + item.tolerance * abs(truth))
    return max(0.0, high - low) / width


@dataclass(frozen=True)
class Spread:
    """A score over seeds: its mean, its standard deviation, and the 95 per
    cent Student-t interval of the mean."""

    mean: float
    deviation: float
    low: float
    high: float


def spread(values: Sequence[float]) -> Spread:
    """The mean of ``values`` (one per seed) and its uncertainty over seeds."""
    data = np.asarray(values, dtype=float)
    mean = float(data.mean())
    if len(data) < 2:
        return Spread(mean, math.nan, math.nan, math.nan)
    deviation = float(data.std(ddof=1))
    half = float(student.ppf(0.975, len(data) - 1)) * deviation / math.sqrt(len(data))
    return Spread(mean, deviation, mean - half, mean + half)


def replay_seed(seed: int, recording: Recording) -> Transcript:
    """Replay the recording of ``seed`` with a fresh answer sheet."""
    return replay(
        recording,
        sheet(seed),
        system=SYSTEM,
        task=task(seed),
        tolerance=TOLERANCE,
        max_steps=MAX_STEPS,
        rerecord=RECORD_COMMAND,
    )


def replay_fixtures(
    directory: Path = Path(),
) -> dict[int, tuple[Recording, Transcript]]:
    """Replay the fixture of every seed found in ``directory``, by seed."""
    replays = {}
    for seed in SEEDS:
        recording = load_recording(directory / fixture(seed))
        replays[seed] = (recording, replay_seed(seed, recording))
    return replays


def _show(step: Step, *secrets: Secret) -> None:
    if step.message.text:
        print(redact(step.message.text, *secrets))
    for call, result in zip(step.message.tool_calls, step.results, strict=False):
        print(
            redact(
                f"  {call.name}({call.arguments}) -> {dict(result.content)}", *secrets
            )
        )


def main(argv: list[str] | None = None) -> int:
    """The live entry point: run every seed and optionally record it."""
    from pbc.agents.providers import PROVIDER, load_client

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--record",
        action="store_true",
        help=f"write each run to {DIRECTORY}/replay-seed-<seed>.json",
    )
    options = parser.parse_args(argv)
    try:
        client = load_client(PROVIDER)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    today = datetime.date.today().isoformat()
    drawn = pictures()
    for seed in SEEDS:
        print(f"\n== seed {seed} ({client.model}) ==\n")
        transcript = run(
            client,
            sheet(seed),
            SYSTEM,
            task(seed),
            MAX_STEPS,
            on_step=lambda step: _show(step, *client.secrets),
            pictures=drawn,
        )
        if options.record:
            path = Path(DIRECTORY) / fixture(seed)
            save_recording(path, transcript, today, *client.secrets)
            print(f"\nRecorded to {path}. Review it before you commit it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
