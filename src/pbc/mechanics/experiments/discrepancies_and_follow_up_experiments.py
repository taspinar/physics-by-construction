"""The experiment of the lesson "Discrepancies, ablations, and follow-up
experiments".

The claim of the lesson "From a question or publication to a research plan"
(RR2), that the best launch angle of the slow throw lies above 43 degrees,
is reviewed. Four findings: every run used explicit Euler; the drag
coefficient was fixed although a tennis ball's is not known that well; the
claim names a real ball; no real ball was thrown. Each finding that asks for
evidence is answered by declared tests, run by the scripted route of SA1 on
a laboratory with two more actions (the throw stepped by the fourth-order
method, and the throw with the drag coefficient as an argument); an ablation
through the same route shows what the result depends on; the claim is
revised, and every line of follow-up is continued or stopped with its
reason. Everything enters the log of ``pbc.research.followup``. Run it as a
program to write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.discrepancies_and_follow_up_experiments out
"""

import copy
from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.agents import projectile_lab
from pbc.agents.specification import (
    REFUTED,
    SUPPORTED,
    UNDECIDED,
    Action,
    Laboratory,
    Record,
    parse,
)
from pbc.agents.specification import execute as route
from pbc.agents.tools import Parameter, Tool
from pbc.authoring import FIGURE_COLOURS, diagrams
from pbc.experiment import Experiment, main
from pbc.figure_language import (
    LINE,
    MARKER,
    MUTED,
    direct_label,
    figsize,
    figure_style,
    finish,
)
from pbc.mechanics.drag import drag_constant
from pbc.mechanics.experiments import experiment_specification as sa1
from pbc.mechanics.experiments.from_question_to_research_plan import (
    ORIGINAL,
    run_plan,
)
from pbc.mechanics.experiments.generating_and_selecting_research_ideas import (
    SLOW_THROW,
)
from pbc.mechanics.integrators import rk4_step
from pbc.mechanics.projectile import STANDARD_GRAVITY, projectile_range
from pbc.research.followup import (
    CONTINUE,
    EVIDENCE,
    STOP,
    WORDING,
    Explanation,
    Finding,
    FollowUp,
    FollowUpRefused,
    Log,
    record_digest,
    status,
    verify_log,
)

AREA = np.pi * (projectile_lab.DIAMETER / 2) ** 2  # m², the ball's cross-section
AIR = 1.2  # kg/m³, the density of air of M3
COEFFICIENT = 0.5  # M3's drag coefficient of the tennis ball
REVIEWER = "the author of this page, as a reviewer"
UNITS = {"speed": "m/s", "angle": "deg", "dt": "s"}


def _fourth_order(speed: float, angle: float, dt: float) -> dict[str, float]:
    return {
        "range_m": projectile_range(
            speed, angle, projectile_lab.MASS, projectile_lab.DRAG, dt, step=rk4_step
        )
    }


def _with_coefficient(speed: float, angle: float, dt: float, cd: float) -> dict:
    drag = drag_constant(AIR, cd, AREA)
    return {"range_m": projectile_range(speed, angle, projectile_lab.MASS, drag, dt)}


def laboratory() -> Laboratory:
    """SA1's laboratory and two more actions, each changing one thing of the
    throw with drag: the integrator, or the drag coefficient."""
    # region: actions
    base = sa1.laboratory()
    parameters = base.action("range_with_drag").tool.parameters
    fourth_order = Tool(
        name="range_fourth_order",
        description="The throw with drag, stepped by the fourth-order method.",
        parameters=parameters,
        function=_fourth_order,
    )
    coefficient = Tool(
        name="range_with_coefficient",
        description="The throw with drag, with the drag coefficient as given.",
        parameters=(*parameters, Parameter("cd", "drag coefficient", 0.0, 1.0)),
        function=_with_coefficient,
    )
    # endregion: actions
    return Laboratory(
        (
            *base.actions,
            Action(fourth_order, units=UNITS, returns={"range_m": "m"}),
            Action(
                coefficient,
                units={**UNITS, "cd": "dimensionless"},
                returns={"range_m": "m"},
            ),
        )
    )


def run_route(specification: dict) -> Record:
    """The scripted route of SA1 on ``specification``, in this laboratory."""
    lab = laboratory()
    return route(parse(copy.deepcopy(specification), lab), lab)


def with_action(action: str, specification: dict = SLOW_THROW) -> dict:
    """``specification`` measured by ``action`` instead."""
    changed = copy.deepcopy(specification)
    changed["actions"] = [action]
    return changed


def with_coefficient(cd: float, resolution: float | None = None) -> dict:
    """The slow throw with the drag coefficient ``cd``, and the resolution
    (deg) of the answer if it is given."""
    changed = with_action("range_with_coefficient")
    changed["variables"]["cd"] = {"role": "fixed", "unit": "dimensionless", "value": cd}
    if resolution is not None:
        changed["success"]["resolution"]["value"] = resolution
    return changed


def with_time_step(dt: float) -> dict:
    """The slow throw with the time step ``dt`` (s) as its numerical setting."""
    changed = copy.deepcopy(SLOW_THROW)
    changed["variables"]["dt"]["value"] = dt
    return changed


CLAIM = (
    "At the slow throw the best angle lies above the predicted bound, and"
    " every success criterion of the plan, declared before the first run, is"
    " met."
)

# region: findings
FINDINGS = (
    Finding(
        "integrator",
        "slow-throw",
        REVIEWER,
        "Every run of the claim, the withheld test included, steps the flight"
        " with explicit Euler; the withheld test changed the time step, not"
        " the method. Is the bracket a property of the model or of the method?",
        EVIDENCE,
    ),
    Finding(
        "coefficient",
        "slow-throw",
        REVIEWER,
        "The drag coefficient is fixed at 0.5, but a tennis ball's is not known"
        " that well. Does the claim hold for coefficients from 0.4 to 1.0?",
        EVIDENCE,
    ),
    Finding(
        "wording",
        "slow-throw",
        REVIEWER,
        "The plan and its question speak of the tennis ball; the claim is"
        " about a simulated one and should say so.",
        WORDING,
    ),
    Finding(
        "real-ball",
        "slow-throw",
        REVIEWER,
        "No real ball was thrown. Does a measured throw at 10 m/s land"
        " furthest above 43 degrees?",
        EVIDENCE,
    ),
)
# endregion: findings

HOLDS = "the claim holds there"
FAILS = "the claim fails there"

# region: gap
TOP_OF_RANGE = FollowUp(
    "top-of-range",
    "coefficient",
    "the drag coefficient at the top of the reviewer's range, 1.0",
    with_coefficient(1.0),
    (
        Explanation(
            HOLDS,
            "Even the largest coefficient leaves the best angle above 43 degrees.",
            (SUPPORTED,),
        ),
        Explanation(
            FAILS,
            "At the largest coefficient the best angle lies below 43 degrees.",
            (REFUTED,),
        ),
    ),
)
# endregion: gap


def coefficient_test(key: str, change: str, specification: dict) -> FollowUp:
    """A test of the coefficient finding with the explanations of
    ``TOP_OF_RANGE``, at another coefficient or resolution."""
    return FollowUp(
        key, "coefficient", change, specification, TOP_OF_RANGE.explanations
    )


FOURTH_ORDER = FollowUp(
    "fourth-order",
    "integrator",
    "the fourth-order method instead of explicit Euler",
    with_action("range_fourth_order"),
    (
        Explanation(
            "the claim belongs to the model",
            "Another method at the same time step gives the same verdict.",
            (SUPPORTED,),
        ),
        Explanation(
            "the claim belongs to explicit Euler",
            "Another method puts the best angle at or below 43 degrees.",
            (REFUTED, UNDECIDED),
        ),
    ),
)
TOP_AT_HALF_DEGREE = coefficient_test(
    "top-at-half-degree",
    "the coefficient 1.0, the answer to half a degree",
    with_coefficient(1.0, resolution=0.5),
)
BELOW_THE_TOP = coefficient_test(
    "below-the-top", "the drag coefficient 0.8", with_coefficient(0.8)
)


def bottom_of_range() -> FollowUp:
    """The test of the coefficient at the bottom of the reviewer's range:
    with the drag weaker, both explanations predict that the claim holds."""
    holds, _ = TOP_OF_RANGE.explanations
    return FollowUp(
        "bottom-of-range",
        "coefficient",
        "the drag coefficient at the bottom of the reviewer's range, 0.4",
        with_coefficient(0.4),
        (
            holds,
            Explanation(
                FAILS,
                "The claim fails where the drag is strongest, so it holds at 0.4.",
                (SUPPORTED,),
            ),
        ),
    )


REVISED = (
    "At 10 m/s the best launch angle of the simulated tennis ball, with"
    " quadratic drag, lies above 43 degrees for every drag coefficient up to"
    " 0.8, and the fourth-order method gives the same bracket as explicit"
    " Euler; at the coefficient 1.0 the route cannot decide at a resolution of"
    " half a degree. No measured throw was compared."
)

# The conditions of the ablation: one change of the slow throw each.
ABLATION = (
    ("the claim as run", "none", SLOW_THROW),
    ("drag removed", "the throw without drag", with_action("range_in_vacuum")),
    (
        "fourth-order method",
        "the integrator",
        with_action("range_fourth_order"),
    ),
    ("time step halved", "the numerical setting", with_time_step(0.002)),
    ("coefficient 0.4", "the drag coefficient", with_coefficient(0.4)),
    ("coefficient 0.8", "the drag coefficient", with_coefficient(0.8)),
    ("coefficient 1.0", "the drag coefficient", with_coefficient(1.0)),
)


def drag_over_weight(cd: float, speed: float = 10.0) -> float:
    """The drag at launch over the weight, for the coefficient ``cd`` and the
    launch ``speed`` (m/s): the reason the hypothesis of the slow throw
    gives."""
    drag = drag_constant(AIR, cd, AREA)
    return drag * speed**2 / (projectile_lab.MASS * STANDARD_GRAVITY)


def follow_up() -> tuple[Log, dict[str, Record]]:
    """The log of the review of the slow-throw claim, from the claim to the
    decisions, and the record of every test."""
    original = run_plan(ORIGINAL)
    log = Log()
    log.claim("slow-throw", CLAIM, [record_digest(original.record)])
    for finding in FINDINGS:
        log.find(finding)
    records = {}

    def run_test(declared: FollowUp) -> None:
        log.declare(declared)
        records[declared.key] = run_route(declared.specification)
        log.record(declared.key, records[declared.key])

    run_test(FOURTH_ORDER)
    log.decide(
        "integrator",
        STOP,
        "The other method gives the same verdict; the gap is closed at the"
        " claim's resolution.",
        "a claim at a resolution finer than the bracket of either method",
    )
    run_test(TOP_OF_RANGE)
    log.decide(
        "coefficient",
        CONTINUE,
        "The bound lies inside the bracket: the test decided nothing. Two"
        " sharper tests are declared: the same coefficient at half a degree,"
        " and a smaller coefficient.",
        "",
    )
    run_test(TOP_AT_HALF_DEGREE)
    run_test(BELOW_THE_TOP)
    log.decide(
        "coefficient",
        STOP,
        "The claim holds up to 0.8; at 1.0 the bound stays inside a bracket of"
        " half a degree, and the claim is narrowed to where it was decided.",
        "a reason to believe the coefficient lies above 0.8, or a claim that needs it",
    )
    log.revise(REVISED, ["integrator", "coefficient", "wording"], list(records))
    log.decide(
        "real-ball",
        STOP,
        "No action of the laboratory throws a real ball: the evidence cannot be"
        " produced here, and the claim says that it is about a simulation.",
        "a dataset of measured throws, registered with its uncertainty",
    )
    return log, records


def prose_only() -> Log:
    """The log of the same review in which the coefficient finding is
    answered by a revision of the claim alone, with no test run."""
    log = Log()
    log.claim("slow-throw", CLAIM, [record_digest(run_plan(ORIGINAL).record)])
    for finding in FINDINGS:
        log.find(finding)
    log.revise(
        "At 10 m/s the best launch angle of the simulated tennis ball lies above"
        " 43 degrees for any plausible drag coefficient.",
        ["coefficient", "wording"],
        [],
    )
    return log


def old_record_as_evidence() -> str:
    """What the log answers when the claim's own route, run again, is offered
    as the evidence of a test of the integrator finding."""
    log = Log()
    original = run_plan(ORIGINAL)
    log.claim("slow-throw", CLAIM, [record_digest(original.record)])
    log.find(FINDINGS[0])
    again = FollowUp(
        "same-route-again",
        "integrator",
        "none: the claim's specification, run again",
        SLOW_THROW,
        FOURTH_ORDER.explanations,
    )
    log.declare(again)
    try:
        log.record(again.key, run_route(again.specification))
    except FollowUpRefused as refused:
        return str(refused)
    return ""


def refused_test() -> str:
    """What the log answers when the bottom of the range is declared."""
    log = Log()
    log.claim("slow-throw", CLAIM, [])
    log.find(FINDINGS[1])
    try:
        log.declare(bottom_of_range())
    except FollowUpRefused as refused:
        return str(refused)
    return ""


def tampered(log: Log) -> list[str]:
    """The log with the verdict of the first coefficient test changed after
    it was written, and what ``verify_log`` finds."""
    entries = list(log.entries)
    for position, entry in enumerate(entries):
        if entry.content.get("test") == TOP_OF_RANGE.key:
            content = {**entry.content, "verdict": SUPPORTED, "decided": HOLDS}
            entries[position] = type(entry)(
                entry.number, entry.kind, content, entry.previous, entry.digest
            )
    return verify_log(entries)


def summary(content: dict) -> str:
    """One line of what a log entry holds, for the table of the log."""
    if "test" in content:
        decided = content["decided"] or "neither explanation"
        return f"{content['test']}: {content['verdict']}, decides for {decided}"
    if "decision" in content:
        return f"{content['finding']}: {content['decision']}"
    if "answers" in content:
        return f"answers {', '.join(content['answers'])}"
    if "predictions" in content:
        return f"{content['key']}, for {content['finding']}"
    return content.get("key", "")


def draw_follow_up_chain() -> Figure:
    """A finding, its gap, the test, the record, the revised claim, and a
    revision of the prose that leaves the finding open, as a sketch."""
    fig, ax = diagrams.canvas(6.4, 4.4, (0.0, 12.8), (0.0, 8.8))
    top = (
        (1.5, "review\nfinding"),
        (4.4, "knowledge\ngap"),
        (7.5, "two explanations,\ntheir predictions"),
        (11.0, "discriminating\ntest"),
    )
    widths = (2.2, 2.2, 3.4, 2.8)
    for (x, label), width in zip(top, widths, strict=True):
        diagrams.state_box(ax, (x, 7.4), label, width=width, height=1.1)
    for left, right in ((2.6, 3.3), (5.5, 5.8), (9.2, 9.6)):
        diagrams.arrow(ax, (left, 7.4), (right, 7.4))
    diagrams.text(ax, (8.4, 5.9), "refused if both\npredict alike", colour=1)
    diagrams.arrow(ax, (8.4, 6.85), (8.4, 6.35), colour=1, linestyle="--")
    bottom = ((11.0, "new record\nin the log"), (6.4, "revised claim"))
    for x, label in bottom:
        diagrams.state_box(ax, (x, 3.9), label, width=2.8, height=1.1)
    diagrams.arrow(ax, (11.0, 6.85), (11.0, 4.45))
    diagrams.arrow(ax, (9.6, 3.9), (7.8, 3.9))
    diagrams.text(ax, (11.15, 5.65), "run once", ha="left")
    diagrams.state_box(
        ax,
        (2.2, 3.9),
        "prose revised,\nno new record",
        width=3.0,
        height=1.1,
        colour=MUTED,
    )
    diagrams.arrow(ax, (1.5, 4.45), (1.5, 6.85), colour=MUTED, linestyle=":")
    diagrams.text(ax, (1.7, 5.65), "finding\nstays open", ha="left", colour=MUTED)
    diagrams.state_box(ax, (6.4, 1.3), "continue or stop,\nwith the reason", width=3.6)
    diagrams.arrow(ax, (6.4, 3.35), (6.4, 1.85))
    return fig


def draw_ablation_brackets(rows: list[tuple[str, Record]], bound: float) -> Figure:
    """The route's bracket under each condition, with its best setting
    marked by the verdict, and the predicted bound."""
    styles = {
        SUPPORTED: ("o", FIGURE_COLOURS[0], "supported"),
        UNDECIDED: ("s", FIGURE_COLOURS[1], "undecided"),
        REFUTED: ("^", FIGURE_COLOURS[2], "refuted"),
    }
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("pair", legend=2))
        positions = range(len(rows))[::-1]
        first_low, _, first_high = rows[0][1].bracket
        ax.axvspan(first_low, first_high, color=MUTED, alpha=0.15, linewidth=0)
        shown = set()
        for y, (_, record) in zip(positions, rows, strict=True):
            low, best, high = record.bracket
            marker, colour, label = styles[record.verdict]
            ax.plot([low, high], [y, y], color=colour, linewidth=LINE["data"])
            ax.plot(
                best,
                y,
                linestyle="none",
                marker=marker,
                markersize=MARKER * 1.4,
                color=colour,
                label=None if label in shown else label,
            )
            shown.add(label)
        ax.axvline(bound, color=MUTED, linestyle=":", linewidth=LINE["guide"])
        direct_label(ax, bound, len(rows) - 0.4, "bound", MUTED)
        ax.set_yticks(list(positions), [name for name, _ in rows])
        ax.set_ylim(-0.7, len(rows) - 0.1)
        ax.set_xlabel("best launch angle (deg)")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3)
    return finish(fig)


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.figure("fig-follow-up-chain", draw_follow_up_chain)
    experiment.table(
        "findings",
        [(f.key, f.kind, f.text) for f in FINDINGS],
        [
            ("finding", "", ""),
            ("asks for", "", ""),
            ("what the reviewer wrote", "", ""),
        ],
        "The four findings of the review of the slow-throw claim, each with the"
        " kind of answer it asks for.",
    )
    log, records = follow_up()
    of_a_test = {record_digest(r): key for key, r in records.items()}
    ablation = [(name, run_route(spec)) for name, _, spec in ABLATION]
    experiment.table(
        "ablation",
        [
            (
                name,
                change,
                *record.bracket,
                record.verdict,
                of_a_test.get(record_digest(record), ""),
            )
            for (name, change, _), (_, record) in zip(ABLATION, ablation, strict=True)
        ],
        [
            ("condition", "", ""),
            ("what it changes", "", ""),
            ("low", "deg", ".3f"),
            ("best", "deg", ".3f"),
            ("high", "deg", ".3f"),
            ("verdict", "", ""),
            ("the record of the test", "", ""),
        ],
        "The route's bracket around the best angle (low, best, high) and its"
        " verdict on the bound of 43 degrees, for the slow throw as run and with"
        " one thing changed, and the test whose record a row is; angles to a"
        " thousandth of a degree.",
    )
    by_name = dict(ablation)
    claimed = by_name["the claim as run"]
    experiment.number("bound", SLOW_THROW["hypothesis"]["prediction"]["value"], "g")
    experiment.number(
        "same-bracket",
        "the same"
        if by_name["fourth-order method"].bracket == claimed.bracket
        else "another",
    )
    experiment.number(
        "drag-shift", claimed.bracket[1] - by_name["coefficient 1.0"].bracket[1], ".3f"
    )
    experiment.number("vacuum-best", by_name["drag removed"].bracket[1], ".3f")
    experiment.figure(
        "fig-ablation-brackets",
        partial(
            draw_ablation_brackets,
            ablation,
            SLOW_THROW["hypothesis"]["prediction"]["value"],
        ),
    )

    experiment.table(
        "tests",
        [
            (
                t.key,
                t.finding,
                t.change,
                *(", ".join(e.predicts) for e in t.explanations),
            )
            for t in (FOURTH_ORDER, TOP_OF_RANGE, TOP_AT_HALF_DEGREE, BELOW_THE_TOP)
        ],
        [
            ("test", "", ""),
            ("finding", "", ""),
            ("what it changes", "", ""),
            ("first explanation predicts", "", ""),
            ("second explanation predicts", "", ""),
        ],
        "The tests declared before they ran, the finding each answers, and the"
        " verdict of the route each of its two explanations predicts.",
    )
    experiment.number("refused-test", refused_test())

    experiment.table(
        "log",
        [(e.number, e.kind, summary(e.content)) for e in log.entries],
        [("entry", "", "d"), ("kind", "", ""), ("what it records", "", "")],
        "The log of the review in the order it was written: the claim, the"
        " findings, each test as declared and its evidence, the decisions, and"
        " the revision.",
    )
    experiment.number("log-problems", len(verify_log(log.entries)), "d")
    decisions = {}
    for entry in log.entries:
        if "decision" in entry.content:
            decisions[entry.content["finding"]] = entry.content
    experiment.table(
        "statuses",
        [
            (
                f.key,
                status(log, f.key),
                decisions.get(f.key, {}).get("decision", ""),
                decisions.get(f.key, {}).get("revisit", ""),
            )
            for f in FINDINGS
        ],
        [
            ("finding", "", ""),
            ("status", "", ""),
            ("last decision", "", ""),
            ("what would warrant revisiting it", "", ""),
        ],
        "Each finding's status, derived from the log, and the last decision"
        " about its line of follow-up.",
    )
    for key, record in records.items():
        experiment.number(f"{key}-verdict", record.verdict)
        experiment.number(f"{key}-low", record.bracket[0], ".3f")
        experiment.number(f"{key}-high", record.bracket[2], ".3f")
    experiment.number(
        "top-at-half-degree-runs", len(records["top-at-half-degree"].runs), "d"
    )
    for cd in (COEFFICIENT, 0.8, 1.0):
        experiment.number(f"ratio-{round(cd * 10)}", drag_over_weight(cd), ".2f")
    experiment.number("revised", REVISED)

    alone = prose_only()
    experiment.table(
        "prose-only",
        [(f.key, status(log, f.key), status(alone, f.key)) for f in FINDINGS],
        [
            ("finding", "", ""),
            ("after the tests", "", ""),
            ("after a revision of the prose alone", "", ""),
        ],
        "The status of each finding in the log of this page and in a log in"
        " which the claim was revised without any test.",
    )
    experiment.number("old-record", old_record_as_evidence())
    experiment.number("tampered", "; ".join(tampered(log)))

    exercise = run_route(with_coefficient(0.9))
    experiment.number("exercise-verdict", exercise.verdict)
    experiment.number("exercise-low", exercise.bracket[0], ".3f")
    experiment.number("exercise-high", exercise.bracket[2], ".3f")
    return experiment


if __name__ == "__main__":
    main(run)
