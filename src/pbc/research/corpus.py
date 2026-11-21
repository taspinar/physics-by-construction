"""A small local literature: verified passages, a person's reading of each,
and the claims they are compared with.

Every passage is a quotation from a published lesson of this site, the
project's own text under CC BY 4.0 (``LICENSE-CONTENT``), with its lesson
and where on the page it stands: a typed claim of the page (its number among
the page's claims) or a sentence of its prose. A test compares every
quotation with the current source of its lesson, so a passage that no longer
stands on its page fails the test: the passages are verified, not only
cited. Nothing is read from a page while the build runs.

A ``Reading`` is what the annotator, the author of the lesson that uses the
corpus, read in a passage, in the terms of the claims: the quantity, the
drag, the ball, the launch speed, and the bound the passage puts on the
best angle. Where the passage takes a condition from its page (the speed of
the page's ball, the bound of the page's specification), ``note`` says so.
``ANNOTATIONS`` holds the label the annotator gave each pair of a claim and
a passage directly, written apart from the readings; ``pbc.research.literature``
computes the labels from the readings, and a test compares the two.

The register entry the claims' drag assumption rests on is held the same way:
its key and the statement a person checked, quoted from
``site/references.yaml``. A source that came up in a search and was never
opened is held only as a proposal.
"""

from dataclasses import dataclass

LICENCE = "CC BY 4.0"
ATTRIBUTION = "Physics by Construction, the published lesson named with the passage"

ANY = "any"  # a condition the passage or the claim holds for every value of

QUADRATIC = "quadratic"
NO_DRAG = "none"
LINEAR = "linear"

BEST_ANGLE = "best angle"

SUPPORTS = "supports"
CONTRADICTS = "contradicts"
INSUFFICIENT = "insufficient"
LABELS = (SUPPORTS, CONTRADICTS, INSUFFICIENT)


@dataclass(frozen=True)
class Reading:
    """What a passage says, in the terms of the claims. ``speed`` (m/s) is
    a number, ``ANY``, or ``None`` when the passage concerns one speed it
    does not state; ``below`` and ``above`` (deg) are the bounds it puts on
    the quantity, ``None`` where it gives none."""

    quantity: str
    drag: str
    ball: str
    speed: float | str | None
    below: float | None = None
    above: float | None = None
    note: str = ""


@dataclass(frozen=True)
class Passage:
    """A quotation, where it stands, its licence, and its reading.
    ``claim`` is the number of the typed claim of the page it quotes, or
    ``None`` for a sentence of the prose."""

    key: str
    lesson: str
    page: str
    claim: int | None
    text: str
    reading: Reading
    licence: str = LICENCE


@dataclass(frozen=True)
class Statement:
    """A claim to compare with the literature: its words, and the same in
    the terms of a reading. ``speed`` (m/s) is a number or ``ANY``;
    ``value`` (deg) is the bound of ``relation``, below or above."""

    key: str
    text: str
    quantity: str
    drag: str
    ball: str
    speed: float | str
    relation: str
    value: float


@dataclass(frozen=True)
class RegisterSource:
    """An entry of the reference register: reviewed by a person for one
    statement, linked and not held. ``statement`` quotes the start of what
    the entry records as checked."""

    key: str
    assumption: str
    statement: str


@dataclass(frozen=True)
class Proposal:
    """A source someone proposed and nobody has read: who proposed it, where
    it is recorded, and its status."""

    source: str
    proposed_by: str
    recorded_in: str
    status: str = "awaiting human review"


M3 = "lessons/mechanics/03-projectile-motion-with-drag/index.qmd"
SA1 = "lessons/mechanics/21-experiment-specification/index.qmd"
SA5 = "lessons/agents-llm/01-an-agent-runs-an-experiment/index.qmd"
M10 = "lessons/mechanics/10-automated-analysis-pipelines/index.qmd"
M2 = "lessons/mechanics/02-newtons-laws/index.qmd"
M1 = "lessons/mechanics/01-kinematics-as-a-program/index.qmd"

# region: passage
SA1_BRACKET = Passage(
    key="sa1-bracket",
    lesson="experiment-specification",
    page=SA1,
    claim=1,
    text=(
        "The launch angle of the longest simulated throw lies between the"
        " two ends of the bracket, and the whole bracket lies below the"
        " predicted bound."
    ),
    reading=Reading(
        BEST_ANGLE,
        QUADRATIC,
        "tennis",
        25.0,
        below=44.0,
        note="the scope names 25 m/s; the bound is the 44 degrees of the"
        " page's specification",
    ),
)
# endregion: passage

PASSAGES = (
    SA1_BRACKET,
    Passage(
        key="sa1-exercise",
        lesson="experiment-specification",
        page=SA1,
        claim=None,
        text="At 25 m/s the bracket of the best angle ended below 41 degrees.",
        reading=Reading(BEST_ANGLE, QUADRATIC, "tennis", 25.0, below=41.0),
    ),
    Passage(
        key="sa1-vacuum",
        lesson="experiment-specification",
        page=SA1,
        claim=None,
        text=(
            "The experiment worked, and the hypothesis is wrong for this ball:"
            " every criterion was met, and the whole bracket lies on the wrong"
            " side of the bound."
        ),
        reading=Reading(
            BEST_ANGLE,
            NO_DRAG,
            "tennis",
            25.0,
            above=44.0,
            note="the run of the page's specification without drag",
        ),
    ),
    Passage(
        key="m3-flatter",
        lesson="projectile-with-drag",
        page=M3,
        claim=1,
        text=(
            "With quadratic drag the longest throw is flatter than $45^\\circ$"
            " for this ball."
        ),
        reading=Reading(
            BEST_ANGLE,
            QUADRATIC,
            "tennis",
            25.0,
            below=45.0,
            note="the scope says the ball's launch speed, which the page"
            " gives as 25 m/s",
        ),
    ),
    Passage(
        key="m3-formula",
        lesson="projectile-with-drag",
        page=M3,
        claim=None,
        text="Without drag the answer is $45^\\circ$, from a formula.",
        reading=Reading(BEST_ANGLE, NO_DRAG, ANY, ANY, below=45.0, above=45.0),
    ),
    Passage(
        key="m3-ratio",
        lesson="projectile-with-drag",
        page=M3,
        claim=None,
        text=(
            "How far the best angle moves below $45^\\circ$ depends on the ratio"
            " of the launch speed to the terminal speed: a ball thrown much more"
            " slowly than its terminal speed hardly notices the air, and the"
            " third exercise puts numbers on that."
        ),
        reading=Reading(
            BEST_ANGLE,
            QUADRATIC,
            ANY,
            ANY,
            below=45.0,
            note="a direction for slow throws, with no bound",
        ),
    ),
    Passage(
        key="sa5-without-air",
        lesson="agent-experiment",
        page=SA5,
        claim=None,
        text=(
            "Without air the answer is forty-five degrees, as the projectile"
            " lesson shows."
        ),
        reading=Reading(BEST_ANGLE, NO_DRAG, ANY, ANY, below=45.0, above=45.0),
    ),
    Passage(
        key="sa5-moves-lower",
        lesson="agent-experiment",
        page=SA5,
        claim=None,
        text=(
            "With drag the ball loses speed along its whole path, the best angle"
            " moves lower, and no formula gives it."
        ),
        reading=Reading(
            BEST_ANGLE,
            QUADRATIC,
            "tennis",
            25.0,
            below=45.0,
            note="the page's ball is the tennis ball at 25 m/s",
        ),
    ),
    Passage(
        key="sa5-table",
        lesson="agent-experiment",
        page=SA5,
        claim=1,
        text=(
            "At the smallest time step the agent used, the two angles it tried"
            " with the longest ranges bracket the best angle of an independent"
            " scan of the simulation, and the best angle lands the ball further"
            " than forty-five degrees by the amount in the table."
        ),
        reading=Reading(
            BEST_ANGLE,
            QUADRATIC,
            "tennis",
            25.0,
            note="the bracket's ends are in the page's table, not in the passage",
        ),
    ),
    Passage(
        key="m10-baseball",
        lesson="automated-analysis-pipelines",
        page=M10,
        claim=1,
        text=(
            "Drag moves the angle of the longest throw below the drag-free value"
            " of forty-five degrees, to … degrees on the grid."
        ),
        reading=Reading(
            BEST_ANGLE,
            QUADRATIC,
            "baseball",
            None,
            below=45.0,
            note="the page's ball is a baseball; its speed is a computed value",
        ),
    ),
    Passage(
        key="m2-terminal",
        lesson="newtons-laws",
        page=M2,
        claim=1,
        text=(
            "Explicit Euler on linear drag converges to the terminal velocity"
            " only for $\\Delta t < 2\\tau$, and alternates around it for"
            " $\\Delta t > \\tau$."
        ),
        reading=Reading("terminal velocity", LINEAR, ANY, ANY),
    ),
    Passage(
        key="m1-rose-less",
        lesson="kinematics",
        page=M1,
        claim=None,
        text="The real ball slowed down during that time, so it rose less.",
        reading=Reading("height after one step", NO_DRAG, ANY, ANY),
    ),
)

# The claims of RR2's two plans, and the guess the projectile lesson
# considered before its simulation answered it.
STATEMENTS = (
    Statement(
        key="replication",
        text=(
            "The best launch angle of the tennis ball thrown at 25 m/s with"
            " quadratic drag lies below 44 degrees."
        ),
        quantity=BEST_ANGLE,
        drag=QUADRATIC,
        ball="tennis",
        speed=25.0,
        relation="below",
        value=44.0,
    ),
    Statement(
        key="slow-throw",
        text=(
            "The best launch angle of the tennis ball thrown at 10 m/s with"
            " quadratic drag lies above 43 degrees."
        ),
        quantity=BEST_ANGLE,
        drag=QUADRATIC,
        ball="tennis",
        speed=10.0,
        relation="above",
        value=43.0,
    ),
    Statement(
        key="no-change",
        text=(
            "Quadratic drag scales every range down by the same factor, so the"
            " best launch angle stays at forty-five degrees for any ball."
        ),
        quantity=BEST_ANGLE,
        drag=QUADRATIC,
        ball=ANY,
        speed=ANY,
        relation="above",
        value=45.0,
    ),
)

# The label of every pair of a claim and a passage, as the annotator gave it,
# written out pair by pair and apart from the readings. There is no default:
# a passage added to the corpus has no label here until it is annotated, and
# a test fails until then.
ANNOTATIONS = {
    "replication": {
        "sa1-bracket": SUPPORTS,
        "sa1-exercise": SUPPORTS,
        "sa1-vacuum": INSUFFICIENT,
        "m3-flatter": INSUFFICIENT,
        "m3-formula": INSUFFICIENT,
        "m3-ratio": INSUFFICIENT,
        "sa5-without-air": INSUFFICIENT,
        "sa5-moves-lower": INSUFFICIENT,
        "sa5-table": INSUFFICIENT,
        "m10-baseball": INSUFFICIENT,
        "m2-terminal": INSUFFICIENT,
        "m1-rose-less": INSUFFICIENT,
    },
    "slow-throw": {
        "sa1-bracket": INSUFFICIENT,
        "sa1-exercise": INSUFFICIENT,
        "sa1-vacuum": INSUFFICIENT,
        "m3-flatter": INSUFFICIENT,
        "m3-formula": INSUFFICIENT,
        "m3-ratio": INSUFFICIENT,
        "sa5-without-air": INSUFFICIENT,
        "sa5-moves-lower": INSUFFICIENT,
        "sa5-table": INSUFFICIENT,
        "m10-baseball": INSUFFICIENT,
        "m2-terminal": INSUFFICIENT,
        "m1-rose-less": INSUFFICIENT,
    },
    "no-change": {
        "sa1-bracket": CONTRADICTS,
        "sa1-exercise": CONTRADICTS,
        "sa1-vacuum": INSUFFICIENT,
        "m3-flatter": CONTRADICTS,
        "m3-formula": INSUFFICIENT,
        "m3-ratio": CONTRADICTS,
        "sa5-without-air": INSUFFICIENT,
        "sa5-moves-lower": CONTRADICTS,
        "sa5-table": INSUFFICIENT,
        "m10-baseball": CONTRADICTS,
        "m2-terminal": INSUFFICIENT,
        "m1-rose-less": INSUFFICIENT,
    },
}
ANNOTATED_BY = "the author of this lesson, on 2026-11-20"

REGISTER = (
    RegisterSource(
        key="drag-coefficient-regimes",
        assumption="quadratic drag",
        statement=(
            "At large Reynolds number the drag coefficient is constant (the"
            " Newtonian regime), so the force is proportional to the speed"
            " squared."
        ),
    ),
)

PROPOSALS = (
    Proposal(
        source=(
            "An American Journal of Physics paper on a thrown ball with linear"
            " or quadratic drag"
        ),
        proposed_by="a search during the selection of drag-coefficient-regimes",
        recorded_in="site/references.yaml, drag-coefficient-regimes, alternatives",
    ),
)
