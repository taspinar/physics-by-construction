"""Lesson AI6, the part without measured data: the questions, the prompts,
the three simulated pictures, their part of the key, and the replay.

The four pictures of the lesson are verified figures of the site. Three are
drawn here by their lessons' code: a sketch of the forces on a falling
particle and the velocity of that particle (Newton's laws), and the field of
two charges (electric fields). The fourth, the calibrated strain of GW150914
with its noise spectrum, is a measurement; it and its part of the key are in
``pbc.agents.multimodal_lab``, which also holds the live run. Keeping them
apart keeps every figure that uses no data free of it.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.constants import g

from pbc.agents.loop import Transcript
from pbc.agents.replay import Recording, load_recording, replay
from pbc.agents.vision import Question, Source, answer_sheet
from pbc.electromagnetism.experiments import electric_fields_and_potential as fields
from pbc.electromagnetism.fields import coulomb_field
from pbc.mechanics.drag import fall_with_linear_drag, linear_drag
from pbc.mechanics.dynamics import simulate
from pbc.mechanics.experiments import newtons_laws as falling

MAX_STEPS = 6  # model messages per run
TOLERANCE = 1e-9  # the acknowledgements are exact
PROMPT_VERSION = 1

DIRECTORY = "site/lessons/agents-llm/16-multimodal-physics-reasoning"
RECORD_COMMAND = (
    "uv run --extra openai python -m pbc.agents.multimodal_lab --record"
    " (with OPENAI_API_KEY set)"
)


def euler():
    """The explicit Euler fall that picture B plots."""
    return simulate(falling.rest, falling.falling, falling.dt, falling.n_steps)


def _draw_fall():
    return falling.draw_fall_with_linear_drag(euler())


SIMULATED = (
    Source(
        "A",
        "newtons-laws",
        "fig-forces-on-a-falling-particle",
        "a sketch of the forces on a particle falling from rest with linear drag,"
        " at three moments",
        falling.draw_forces_on_a_falling_particle,
    ),
    Source(
        "B",
        "newtons-laws",
        "fig-fall-with-linear-drag",
        "the velocity of that particle against time, simulated and exact",
        _draw_fall,
    ),
    Source(
        "C",
        "electric-fields-and-potential",
        "fig-dipole-field",
        "field lines and equipotentials of two point charges, in a plane through both",
        fields.draw_dipole_field,
    ),
)

FORCES = ("drag is smaller than the weight", "they are equal", "drag is larger")
NET = ("upward", "downward", "zero")
FACTORS = ("halved", "unchanged", "doubled", "four times larger")
DIRECTIONS = ("up, along +z", "down, along -z", "sideways, along x", "zero")
DETECTORS = ("H1", "L1")

QUESTIONS = (
    Question(
        1,
        "A",
        "property",
        "At the moment labelled terminal speed, how does the drag on the particle"
        " compare with its weight?",
        FORCES,
    ),
    Question(
        2,
        "A",
        "property",
        "At the moment labelled speeding up, which way is the net force on the"
        " particle?",
        NET,
    ),
    Question(
        3,
        "A",
        "counterfactual",
        "If the particle's mass were doubled and the drag constant kept, its"
        " terminal speed would be:",
        FACTORS,
    ),
    Question(
        4,
        "B",
        "property",
        "Read the terminal speed of the particle.",
        unit="m/s",
        low=0.0,
        high=50.0,
    ),
    Question(
        5,
        "B",
        "property",
        "Read the time at which the exact velocity is half the terminal speed.",
        unit="s",
        low=0.0,
        high=10.0,
    ),
    Question(
        6,
        "B",
        "counterfactual",
        "If the drag constant were doubled and the mass kept, what would the"
        " terminal speed be?",
        unit="m/s",
        low=0.0,
        high=50.0,
    ),
    Question(
        7,
        "C",
        "spatial",
        "Which way does the electric field point at the midpoint between the two"
        " charges?",
        DIRECTIONS,
    ),
    Question(
        8,
        "C",
        "spatial",
        "Which way does the electric field point at x = 0, z = 2 cm, above the"
        " upper charge?",
        DIRECTIONS,
    ),
    Question(
        9,
        "C",
        "counterfactual",
        "If the lower charge were replaced by one equal to the upper charge,"
        " which way would the field point at the midpoint?",
        DIRECTIONS,
    ),
    Question(
        10,
        "D",
        "spatial",
        "In the noise spectrum, which detector has the lower amplitude spectral"
        " density between 12 and 25 Hz?",
        DETECTORS,
    ),
    Question(
        11,
        "D",
        "property",
        "In the noise spectrum, read the frequency of the tallest narrow line"
        " between 400 and 700 Hz.",
        unit="Hz",
        low=10.0,
        high=2000.0,
    ),
)

SHARED = (
    "You answer questions about physics pictures. Use the tool answer once per"
    " question; an answer cannot be changed and you are not told whether it is"
    " right. When you cannot tell, give your best estimate and say so in your"
    " message. When every question is answered, end with a short message that"
    " says which answers you read from a picture and which you inferred."
)
SYSTEM_WITH_PICTURES = (
    SHARED + " The four pictures, A to D, are attached to the task, in order."
)
SYSTEM_WITHOUT_PICTURES = (
    SHARED + " The pictures are not available to you: only their descriptions in"
    " the task. Answer from what you know."
)

# Picture D, the measurement, as the task describes it.
MEASURED_CAPTION = (
    "four seconds of the calibrated strain of the two LIGO detectors around"
    " GW150914, and their noise spectra"
)

TASK = (
    "Four pictures are described below; each is a figure of a physics course.\n"
    + "\n".join(f"Picture {s.label}: {s.caption}." for s in SIMULATED)
    + f"\nPicture D: {MEASURED_CAPTION}."
    + "\n\nAnswer every question with the tool answer.\n"
    + "\n".join(q.prompt() for q in QUESTIONS)
)


@dataclass(frozen=True)
class Condition:
    """One run of the lesson: with the pictures or without them."""

    id: str
    title: str
    system: str
    with_pictures: bool

    @property
    def fixture(self) -> str:
        return f"replay-{self.id}.json"


CONDITIONS = (
    Condition("pictures", "with the pictures", SYSTEM_WITH_PICTURES, True),
    Condition("text", "without the pictures", SYSTEM_WITHOUT_PICTURES, False),
)


def _direction(field: np.ndarray) -> int:
    """The option of ``DIRECTIONS`` for a field vector: zero when it is
    below a millionth of the field of one charge at the separation."""
    scale = np.linalg.norm(
        coulomb_field([[0.0, 0.0, fields.D]], [fields.Q], [[0.0] * 3])
    )
    if np.linalg.norm(field) < 1e-6 * scale:
        return 4
    x, _, z = field
    if abs(x) > abs(z):
        return 3
    return 1 if z > 0 else 2


def _terminal(mass: float, b: float) -> float:
    """The velocity of the exact fall after forty time constants."""
    late = 40.0 * mass / b
    return float(fall_with_linear_drag(falling.rest, mass, b, [g], late).v[0, 0])


def simulated_key() -> dict[int, float]:
    """The answers about the three simulated pictures (questions 1 to 9),
    computed from the physics code of the lessons they come from. Options
    are numbered from 1."""
    mass, b = falling.mass, falling.b
    v_t = _terminal(mass, b)
    drag = linear_drag(b)

    def drag_at(v):
        # positive: upward, against the motion (down is positive)
        return -float(drag(0.0, np.zeros(1), np.array([v]))[0])

    ratio = drag_at(v_t) / (mass * g)
    force_option = 2 if abs(ratio - 1.0) < 1e-6 else (1 if ratio < 1 else 3)
    net = mass * g - drag_at(v_t / 2)  # positive: downward
    net_option = 2 if net > 0 else (1 if net < 0 else 3)
    factor = _terminal(2 * mass, b) / v_t
    factor_option = 1 + int(np.argmin(np.abs(np.array([0.5, 1.0, 2.0, 4.0]) - factor)))

    times = np.linspace(0.0, 10.0, 100001)
    exact = fall_with_linear_drag(falling.rest, mass, b, [g], times).v[:, 0]
    half = float(times[np.argmax(exact >= v_t / 2)])

    def field_at(point, charges):
        return coulomb_field([point], charges, fields.pair)[0]

    origin = [0.0, 0.0, 0.0]
    above = [0.0, 0.0, 0.02]
    same = np.array([fields.Q, fields.Q])

    return {
        1: force_option,
        2: net_option,
        3: factor_option,
        4: v_t,
        5: half,
        6: _terminal(mass, 2 * b),
        7: _direction(field_at(origin, fields.signs)),
        8: _direction(field_at(above, fields.signs)),
        9: _direction(field_at(origin, same)),
    }


# The key as computed when the runs were recorded (judge configuration,
# never in a tool or a prompt). A test compares it with the key: when a
# source figure's physics changes, the recordings answer another picture and
# must be made again.
RECORDED_KEY = {
    1: 2,
    2: 2,
    3: 3,
    4: 19.6133,
    5: 1.3863,
    6: 9.80665,
    7: 2,
    8: 1,
    9: 4,
    10: 1,
    11: 516.0,
}


def replay_condition(condition: Condition, recording: Recording) -> Transcript:
    """Replay ``recording`` with a fresh answer sheet."""
    return replay(
        recording,
        answer_sheet(QUESTIONS),
        system=condition.system,
        task=TASK,
        tolerance=TOLERANCE,
        max_steps=MAX_STEPS,
        rerecord=RECORD_COMMAND,
    )


def replay_fixtures(
    directory: Path = Path(),
) -> dict[str, tuple[Recording, Transcript]]:
    """Replay the fixture of every condition found in ``directory``, by id."""
    replays = {}
    for condition in CONDITIONS:
        recording = load_recording(directory / condition.fixture)
        replays[condition.id] = (recording, replay_condition(condition, recording))
    return replays
