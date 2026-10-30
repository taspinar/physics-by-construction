"""Questions about still pictures, answered through one tool and scored by
the build (lessons AI6 and AI7).

A picture is a verified figure of the site, drawn again by its own lesson's
``draw_`` function and given to the model as PNG bytes (``Picture``). A
question has a number, the picture it is about, a kind, and either a list of
options or a numeric range. The model answers through the tool ``answer``,
which records the answer and returns an acknowledgement: never a score, a
truth, or a hint. One answer per question.

The build reads the accepted answers out of the transcript (``answers``) and
scores them against a key it computes from the physics code (``score``). The
text of the model is not read.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import partial

from matplotlib.figure import Figure

from pbc.agents.loop import Transcript
from pbc.agents.messages import Picture
from pbc.agents.tools import Allowlist, Parameter, Tool
from pbc.experiment import encode

# The kinds of question of AI6: what an object is or can do, where things
# are relative to each other, and what would change in a world the picture
# does not show.
KINDS = ("property", "spatial", "counterfactual")

# A numeric answer is correct within this fraction of the true value: a
# reading off a plot, not a computation.
READING_TOLERANCE = 0.10

# The bound on any number a model may send, far beyond every range asked.
LARGEST = 1e4


@dataclass(frozen=True)
class Source:
    """A picture: a label the task names it by, the figure of the site it is
    (lesson and cell), and the function that draws it."""

    label: str
    lesson: str
    cell: str
    caption: str  # what the task says the picture shows; it gives no answer
    draw: Callable[[], Figure]

    def picture(self) -> Picture:
        return Picture(self.label, encode(self.draw))


@dataclass(frozen=True)
class Question:
    """One question about one picture.

    A choice question has ``options`` and is answered by the option's number,
    counted from 1. A numeric question has none and is answered by a number
    in ``unit``; ``low`` and ``high`` are the range the task states, which the
    chance baseline guesses in.
    """

    number: int
    picture: str
    kind: str
    text: str
    options: tuple[str, ...] = ()
    unit: str = ""
    low: float = 0.0
    high: float = 0.0

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"unknown kind {self.kind!r}")
        if not self.options and not self.low < self.high:
            raise ValueError(f"question {self.number} has no options and no range")

    @property
    def numeric(self) -> bool:
        return not self.options

    def prompt(self) -> str:
        """The question as the task states it."""
        if self.numeric:
            asked = f"Answer in {self.unit}, between {self.low:g} and {self.high:g}."
        else:
            listed = "; ".join(f"{k} {o}" for k, o in enumerate(self.options, 1))
            asked = f"Answer with the option's number: {listed}."
        return f"{self.number}. (picture {self.picture}) {self.text} {asked}"


def _record(questions: Mapping[int, Question], given: set[int], question, value):
    asked = questions[question]
    if question in given:
        raise ValueError(f"question {question} is already answered")
    if not asked.numeric and (
        value != int(value) or not 1 <= value <= len(asked.options)
    ):
        raise ValueError(
            f"question {question} takes an option number from 1 to {len(asked.options)}"
        )
    given.add(question)
    return {"question": question, "recorded": 1}


def answer_sheet(questions: Sequence[Question]) -> Allowlist:
    """A fresh allowlist with the one tool ``answer``, for one run: one call
    per question, a second answer to a question refused."""
    by_number = {q.number: q for q in questions}
    if sorted(by_number) != list(range(1, len(questions) + 1)):
        raise ValueError("questions are numbered from 1 without gaps")
    tool = Tool(
        name="answer",
        description=(
            "Give your answer to one question. It is recorded and cannot be"
            " changed; nothing is said about whether it is right."
        ),
        parameters=(
            Parameter(
                "question", "the number of the question", 1, len(questions), True
            ),
            Parameter(
                "value",
                "the option's number, or the number asked for in its unit",
                -LARGEST,
                LARGEST,
            ),
        ),
        function=partial(_record, by_number, set()),
    )
    return Allowlist((tool,), budget=len(questions))


def answers(transcript: Transcript, tool: str = "answer") -> dict[int, dict]:
    """The accepted calls of ``tool`` in a run, by question: the arguments
    as validated. A refused call gives nothing."""
    found = {}
    for step in transcript.steps:
        for call, result in zip(step.message.tool_calls, step.results, strict=True):
            if result.ok and call.name == tool:
                found[call.arguments["question"]] = dict(call.arguments)
    return found


@dataclass(frozen=True)
class Scored:
    """One question, the answer of a run (None when it gave none), the
    recomputed truth, and whether the answer is correct."""

    question: Question
    answer: float | None
    truth: float
    correct: bool


def correct(question: Question, value: float | None, truth: float) -> bool:
    """A choice is correct when it is the true option; a number when it is
    within ``READING_TOLERANCE`` of the truth."""
    if value is None:
        return False
    if question.numeric:
        return abs(value - truth) <= READING_TOLERANCE * abs(truth)
    return int(value) == int(truth)


def score(
    questions: Sequence[Question], key: Mapping[int, float], transcript: Transcript
) -> list[Scored]:
    """Every question with the run's answer and the key's truth."""
    given = answers(transcript)
    scored = []
    for q in questions:
        value = given.get(q.number, {}).get("value")
        scored.append(Scored(q, value, key[q.number], correct(q, value, key[q.number])))
    return scored


def chance(question: Question, truth: float) -> float:
    """The probability that a uniform guess is correct: one over the number
    of options, or the share of the stated range that lies within the
    tolerance of the truth."""
    if not question.numeric:
        return 1.0 / len(question.options)
    width = question.high - question.low
    low = max(question.low, truth - READING_TOLERANCE * abs(truth))
    high = min(question.high, truth + READING_TOLERANCE * abs(truth))
    return max(0.0, high - low) / width
