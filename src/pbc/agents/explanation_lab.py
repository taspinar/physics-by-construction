"""Lesson AI7: a prediction, and the explanation offered for it, tested
apart.

The model sees the velocity of a particle falling with linear drag (picture B
of AI6, the figure of Newton's laws) and the given values of the scene. For
each question it gives, through the tool ``explain``, a prediction with an
interval, its unit, and an explanation: one relation from a fixed list of
candidates. The build tests the prediction against the verified result (the
exact solution of ``pbc.mechanics.drag``) and the explanation by itself:

- **unit**: the unit named is the unit of the quantity asked;
- **dimensions**: the relation passes a scaling test, computed by changing
  the units of mass, length, and time and checking that the relation's value
  changes as the quantity must (``dimensionally_consistent``);
- **physics**: the relation, evaluated at the given values, gives the
  verified result;
- **support**: the relation, evaluated, lies within the model's own interval,
  so the explanation supports the prediction it came with;
- **uncertainty**: the interval covers the verified result.

Two baselines without a model: a curve fit to the plotted points (a
prediction with no explanation) and dimensional analysis (an explanation
with no data).

Run it live on your machine (needs ``OPENAI_API_KEY`` and the optional
dependency)::

    uv run --extra openai python -m pbc.agents.explanation_lab

Record the replay fixture of the lesson from a live run (maintainer)::

    uv run --extra openai python -m pbc.agents.explanation_lab --record
"""

import argparse
import datetime
import math
import sys
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from pathlib import Path

import numpy as np
from scipy.constants import g
from scipy.optimize import brentq, curve_fit

from pbc.agents.loop import Step, Transcript, run
from pbc.agents.multimodal_questions import SIMULATED, euler
from pbc.agents.replay import Recording, load_recording, replay, save_recording
from pbc.agents.secrets import Secret, redact
from pbc.agents.tools import Allowlist, Choice, Parameter, Tool
from pbc.agents.vision import LARGEST, answers
from pbc.mechanics.drag import fall_with_linear_drag
from pbc.mechanics.experiments import newtons_laws as falling

MAX_STEPS = 4  # model messages
TOLERANCE = 1e-9  # the acknowledgements are exact
PROMPT_VERSION = 1
# A prediction is correct within this fraction of the verified result.
PREDICTION_TOLERANCE = 0.05
# A relation agrees with the verified result within this fraction: the two
# are the same formula, evaluated twice.
AGREEMENT = 1e-6

DIRECTORY = "site/lessons/agents-llm/17-interpretable-physics-explanations"
FIXTURE = "replay.json"
RECORD_COMMAND = (
    "uv run --extra openai python -m pbc.agents.explanation_lab --record"
    " (with OPENAI_API_KEY set)"
)

PICTURE = SIMULATED[1]  # the velocity of the falling particle

# Dimensions as exponents of mass, length, and time.
DIMENSIONS = {
    "m/s": (0, 1, -1),
    "s": (0, 0, 1),
    "m": (0, 1, 0),
    "m/s^2": (0, 1, -2),
    "kg/s": (1, 0, -1),
    "N": (1, 1, -2),
}
UNITS = tuple(DIMENSIONS)


@dataclass(frozen=True)
class Relation:
    """A candidate explanation: a formula in the scene's symbols, m (kg),
    b (kg/s), g (m/s^2), and t (s)."""

    text: str
    value: Callable[[float, float, float, float], float]


RELATIONS = (
    Relation("v = m g / b", lambda m, b, g, t: m * g / b),
    Relation("v = sqrt(m g / b)", lambda m, b, g, t: math.sqrt(m * g / b)),
    Relation("v = b g / m", lambda m, b, g, t: b * g / m),
    Relation("v = m g b", lambda m, b, g, t: m * g * b),
    Relation("tau = m / b", lambda m, b, g, t: m / b),
    Relation("tau = b / m", lambda m, b, g, t: b / m),
    Relation("tau = m g / b", lambda m, b, g, t: m * g / b),
    Relation("tau = sqrt(m / b)", lambda m, b, g, t: math.sqrt(m / b)),
    Relation(
        "v = (m g / b) (1 - exp(-b t / m))",
        lambda m, b, g, t: m * g / b * (1 - math.exp(-b * t / m)),
    ),
    Relation("v = g t", lambda m, b, g, t: g * t),
    Relation(
        "v = (m g / b) exp(-b t / m)",
        lambda m, b, g, t: m * g / b * math.exp(-b * t / m),
    ),
    Relation(
        "v = (m g / b) (1 - exp(-t))",
        lambda m, b, g, t: m * g / b * (1 - math.exp(-t)),
    ),
)
_BY_TEXT = {r.text: r for r in RELATIONS}


@dataclass(frozen=True)
class Asked:
    """One question: the quantity, its unit, the scene it is asked for (mass
    and time; the drag constant and g are those of the picture), and the
    candidate relations offered."""

    number: int
    text: str
    unit: str
    mass: float
    time: float
    relations: tuple[str, ...]

    def prompt(self) -> str:
        offered = "; ".join(f'"{r}"' for r in self.relations)
        return f"{self.number}. {self.text} Candidate relations: {offered}."


SPEEDS = RELATIONS[0].text, RELATIONS[1].text, RELATIONS[2].text, RELATIONS[3].text
TIMES = tuple(r.text for r in RELATIONS[4:8])
HISTORIES = tuple(r.text for r in RELATIONS[8:])

QUESTIONS = (
    Asked(
        1,
        "Predict the terminal speed of the particle.",
        "m/s",
        falling.mass,
        0.0,
        SPEEDS,
    ),
    Asked(
        2,
        "Predict the time constant tau of the approach to the terminal speed:"
        " the time at which the velocity reaches 1 - 1/e of it.",
        "s",
        falling.mass,
        0.0,
        TIMES,
    ),
    Asked(
        3,
        "Predict the terminal speed if the mass were 1 kg, with the same drag"
        " constant.",
        "m/s",
        1.0,
        0.0,
        SPEEDS,
    ),
    Asked(
        4,
        "Predict the velocity of the particle 4 s after its release.",
        "m/s",
        falling.mass,
        4.0,
        HISTORIES,
    ),
)

SYSTEM = (
    "You predict physical quantities and explain your predictions. The picture"
    " attached to the task is a figure of a physics course. For each question,"
    " use the tool explain once: your prediction, an interval you are confident"
    " contains the true value, the unit, and the relation, from the candidates"
    " offered, that explains your prediction. An answer cannot be changed and"
    " you are not told whether it is right. When every question is answered,"
    " end with a short message that says, for each answer, whether it came from"
    " reading the picture or from the relation."
)

TASK = (
    f"The picture shows {PICTURE.caption}. The particle has mass m ="
    f" {falling.mass:g} kg, the drag constant is b = {falling.b:g} kg/s, and"
    f" g = {g:g} m/s^2; it starts from rest and down is positive.\n\n"
    "Answer every question with the tool explain.\n"
    + "\n".join(q.prompt() for q in QUESTIONS)
)


def _explain(given: set[int], question, value, low, high, unit, relation):
    asked = QUESTIONS[question - 1]
    if question in given:
        raise ValueError(f"question {question} is already answered")
    if not low <= value <= high:
        raise ValueError(
            "the interval must contain the prediction: low <= value <= high"
        )
    if relation not in asked.relations:
        raise ValueError(f"question {question} offers other relations")
    given.add(question)
    return {"question": question, "recorded": 1}


def explain_sheet() -> Allowlist:
    """A fresh allowlist with the one tool ``explain``, for one run."""
    number = partial(Parameter, low=-LARGEST, high=LARGEST)
    tool = Tool(
        name="explain",
        description=(
            "Give your prediction for one question, with an interval, its unit,"
            " and the relation that explains it. It is recorded and cannot be"
            " changed; nothing is said about whether it is right."
        ),
        parameters=(
            Parameter(
                "question", "the number of the question", 1, len(QUESTIONS), True
            ),
            number("value", "the prediction, in the unit you name"),
            number("low", "the lower end of your interval"),
            number("high", "the upper end of your interval"),
            Choice("unit", "the unit of the prediction", UNITS),
            Choice("relation", "the relation that explains it", tuple(_BY_TEXT)),
        ),
        function=partial(_explain, set()),
    )
    return Allowlist((tool,), budget=len(QUESTIONS))


def _velocity(mass: float, time: float) -> float:
    return float(
        fall_with_linear_drag(falling.rest, mass, falling.b, [g], time).v[0, 0]
    )


def verified() -> dict[int, float]:
    """The verified result of every question, from the exact solution of
    the fall (``pbc.mechanics.drag``), not from a candidate relation."""
    terminal = _velocity(falling.mass, 40.0 * falling.mass / falling.b)
    tau = brentq(
        lambda t: _velocity(falling.mass, t) - (1 - math.exp(-1)) * terminal,
        1e-6,
        20.0,
        xtol=1e-12,
    )
    return {
        1: terminal,
        2: tau,
        3: _velocity(1.0, 40.0 * 1.0 / falling.b),
        4: _velocity(falling.mass, 4.0),
    }


# Two changes of the units of mass, length, and time, by these factors.
SCALINGS = ((2.0, 3.0, 5.0), (7.0, 0.5, 0.3))


def dimensionally_consistent(relation: str, unit: str, asked: Asked) -> bool:
    """The scaling test: express the given values in larger units of mass,
    length, and time; a relation whose two sides have the same dimensions
    changes its value exactly as a quantity of ``unit`` does."""
    formula = _BY_TEXT[relation].value
    m, b, t = asked.mass, falling.b, asked.time
    base = formula(m, b, g, t)
    a, length, s = DIMENSIONS[unit]
    for mass_unit, length_unit, time_unit in SCALINGS:
        scaled = formula(
            m / mass_unit,
            b * time_unit / mass_unit,
            g * time_unit**2 / length_unit,
            t / time_unit,
        )
        expected = base / (mass_unit**a * length_unit**length * time_unit**s)
        if not math.isclose(scaled, expected, rel_tol=1e-9):
            return False
    return True


def evaluate(relation: str, asked: Asked) -> float:
    """The relation's value at the question's scene."""
    return _BY_TEXT[relation].value(asked.mass, falling.b, g, asked.time)


@dataclass(frozen=True)
class Tested:
    """One answer of a run, with the tests of its prediction and of its
    explanation. ``None`` where the answer has no such part."""

    asked: Asked
    truth: float
    value: float | None
    low: float | None
    high: float | None
    unit: str | None
    relation: str | None
    prediction: bool  # within PREDICTION_TOLERANCE of the verified result
    unit_right: bool | None
    dimensions: bool | None
    physics: bool | None  # the relation gives the verified result
    support: bool | None  # the relation, evaluated, lies in the interval
    covers: bool | None  # the interval contains the verified result

    @property
    def width(self) -> float | None:
        """The interval's width over the verified result."""
        if self.low is None or self.high is None:
            return None
        return (self.high - self.low) / abs(self.truth)


def examine(asked: Asked, truth: float, given: dict | None) -> Tested:
    """Every test of one answer (``given``: the arguments of an accepted
    ``explain`` call, or None when the run gave none)."""
    if given is None:
        return Tested(asked, truth, None, None, None, None, None, False, *[None] * 5)
    value, low, high = given["value"], given["low"], given["high"]
    relation, unit = given["relation"], given["unit"]
    found = evaluate(relation, asked)
    return Tested(
        asked,
        truth,
        value,
        low,
        high,
        unit,
        relation,
        prediction=abs(value - truth) <= PREDICTION_TOLERANCE * abs(truth),
        unit_right=unit == asked.unit,
        dimensions=dimensionally_consistent(relation, asked.unit, asked),
        physics=math.isclose(found, truth, rel_tol=AGREEMENT),
        support=low <= found <= high,
        covers=low <= truth <= high,
    )


def tested(transcript: Transcript) -> list[Tested]:
    """Every question with the run's answer and its tests."""
    truths = verified()
    given = answers(transcript, "explain")
    return [examine(q, truths[q.number], given.get(q.number)) for q in QUESTIONS]


def _approach(t, terminal, tau):
    return terminal * (1 - np.exp(-t / tau))


def curve_fit_baseline() -> dict[int, float]:
    """A prediction without an explanation: the approach v = A (1 - exp(-t/T))
    fitted to the explicit Euler points the picture plots. It has no mass in
    it, so its terminal speed for another mass is the same A."""
    points = euler()
    (terminal, tau), _ = curve_fit(_approach, points.t, points.v[:, 0], p0=(10.0, 1.0))
    return {
        1: float(terminal),
        2: float(tau),
        3: float(terminal),
        4: float(_approach(4.0, terminal, tau)),
    }


def dimensional_baseline() -> dict[int, tuple[str, ...]]:
    """An explanation without data: the candidate relations of each question
    that pass the scaling test. One left is an identified explanation; more
    are not."""
    return {
        q.number: tuple(
            r for r in q.relations if dimensionally_consistent(r, q.unit, q)
        )
        for q in QUESTIONS
    }


def replay_fixture(directory: Path = Path()) -> tuple[Recording, Transcript]:
    """Replay the lesson's fixture with a fresh sheet."""
    recording = load_recording(directory / FIXTURE)
    transcript = replay(
        recording,
        explain_sheet(),
        system=SYSTEM,
        task=TASK,
        tolerance=TOLERANCE,
        max_steps=MAX_STEPS,
        rerecord=RECORD_COMMAND,
    )
    return recording, transcript


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
    """The live entry point: one run with the picture, optionally recorded."""
    from pbc.agents.providers import PROVIDER, load_client

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--record", action="store_true", help=f"write the run to {DIRECTORY}/{FIXTURE}"
    )
    options = parser.parse_args(argv)
    try:
        client = load_client(PROVIDER)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    transcript = run(
        client,
        explain_sheet(),
        SYSTEM,
        TASK,
        MAX_STEPS,
        on_step=lambda step: _show(step, *client.secrets),
        pictures=(PICTURE.picture(),),
    )
    if options.record:
        path = Path(DIRECTORY) / FIXTURE
        save_recording(
            path, transcript, datetime.date.today().isoformat(), *client.secrets
        )
        print(f"\nRecorded to {path}. Review it before you commit it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
