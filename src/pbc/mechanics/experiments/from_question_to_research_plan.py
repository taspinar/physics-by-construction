"""The experiment of the lesson "From a question or publication to a research
plan".

Two research plans about the tennis ball, declared before execution in the
seven parts of ``pbc.research.plan``: a replication of the published claim
of the lesson "From research question to experiment specification" (SA1)
and the original question the lesson "Generating and selecting research
ideas" selected. Each is checked, frozen by its digest, and executed by the
scripted route of SA1 with a positive control, a grid baseline, and a
withheld test opened once. Plans with a part missing are refused, and a plan
changed after its result is reported as a deviation. Run it as a program to
write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.from_question_to_research_plan out
"""

import copy
import itertools
from functools import partial

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from pbc.agents.specification import execute as route
from pbc.agents.specification import parse
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
from pbc.mechanics.experiments.experiment_specification import (
    SPECIFICATION,
    laboratory,
)
from pbc.mechanics.experiments.generating_and_selecting_research_ideas import (
    SLOW_THROW,
)
from pbc.research.plan import (
    CRITERIA,
    PUBLISHED_VERDICT,
    PlanRecord,
    PlanRejected,
    check,
    execute,
    freeze,
)

# region: replication
REPLICATION = {
    "kind": "replication",
    "source": {
        "reference": "SA1, From research question to experiment specification",
        "statement": (
            "The launch angle of the longest simulated throw lies between the"
            " two ends of the bracket, and the whole bracket lies below the"
            " predicted bound."
        ),
        "verdict": "supported",
    },
    "specification": SPECIFICATION,
    "baselines": {
        "control": {"action": "range_in_vacuum", "answer": 45.0},
        "grid": {"runs": 20},
    },
    "withheld": [
        {
            "name": "finer scan",
            "numerical": 0.001,
            "span": 2.0,
            "fraction": 8,
            "runs": 33,
        }
    ],
    "success": list(CRITERIA),
    "stopping": {"max_runs": 120, "stop_if_control_fails": True},
}
# endregion: replication

# region: original
ORIGINAL = copy.deepcopy(REPLICATION)
ORIGINAL["kind"] = "original"
ORIGINAL["source"] = {
    "reference": "RR1, the archive, entry 3 (slow-throw)",
    "statement": "Is the best angle at 10 m/s within two degrees of 45?",
}
ORIGINAL["specification"] = SLOW_THROW
ORIGINAL["success"].remove(PUBLISHED_VERDICT)
# endregion: original


def without(part: str, plan: dict) -> dict:
    """``plan`` with the part ``part`` removed."""
    changed = copy.deepcopy(plan)
    del changed[part]
    return changed


def seen_by_the_search(plan: dict) -> dict:
    """``plan`` with its withheld test at half the time step of the
    specification, a time step the route uses for its stability check."""
    changed = copy.deepcopy(plan)
    changed["withheld"][0]["numerical"] = 0.002
    return changed


def refusal(data: dict) -> list[tuple[str, str]]:
    """The problems ``check`` finds in ``data``, or an empty list."""
    try:
        check(data, laboratory())
    except PlanRejected as rejected:
        return [(p.part, p.message) for p in rejected.problems]
    return []


def run_plan(data: dict) -> PlanRecord:
    """Check ``data``, freeze it, and execute it."""
    lab = laboratory()
    frozen = freeze(data)
    return execute(check(data, lab), lab, frozen)


def moved_prediction() -> PlanRecord:
    """The original plan with its predicted bound moved after its result,
    half a degree closer to the route's bracket, and executed against the
    digest frozen before the first run: a deviation."""
    frozen = freeze(ORIGINAL)
    changed = copy.deepcopy(ORIGINAL)
    changed["specification"]["hypothesis"]["prediction"]["value"] = 43.5
    lab = laboratory()
    return execute(check(changed, lab), lab, frozen)


def medium_throw() -> dict:
    """The plan of the exercise: the original plan at 15 m/s."""
    changed = copy.deepcopy(ORIGINAL)
    changed["source"] = {
        "reference": "RR1, the archive, entry 5 (middle-throw)",
        "statement": "Is the best angle at 15 m/s within two degrees of 45?",
    }
    changed["specification"]["variables"]["speed"]["value"] = 15.0
    return changed


def wrong_control() -> dict:
    """The plan of the exercise: the original plan with a control whose
    stated answer is wrong."""
    changed = copy.deepcopy(ORIGINAL)
    changed["baselines"]["control"]["answer"] = 42.0
    return changed


def stage_table(experiment: Experiment, name: str, record: PlanRecord) -> None:
    """Record what each stage of ``record`` did, as the table ``name``."""
    rows = [
        (
            "positive control",
            len(record.control.record.runs),
            record.control.record.bracket[0],
            record.control.record.bracket[2],
            "finds 45" if record.control.passed else "misses 45",
        ),
        (
            "route",
            len(record.record.runs),
            record.record.bracket[0],
            record.record.bracket[2],
            record.record.verdict,
        ),
        ("grid baseline", len(record.grid.settings), record.grid.best, None, ""),
    ]
    for outcome in record.withheld:
        rows.append(
            (
                f"withheld: {outcome.test.name}",
                len(outcome.settings),
                outcome.best,
                None,
                "inside the bracket" if outcome.passed else "outside the bracket",
            )
        )
    experiment.table(
        name,
        rows,
        [
            ("stage", "", ""),
            ("runs", "", "d"),
            ("best or low", "deg", ".3f"),
            ("high", "deg", ".3f"),
            ("outcome", "", ""),
        ],
        "Each stage of the plan in the order it ran: the bracket of the"
        " control and of the route (low and high), the best angle of the grid"
        " and of the withheld test, and what each found; angles to a"
        " thousandth of a degree.",
    )


def outcome(
    experiment: Experiment,
    prefix: str,
    record: PlanRecord,
    names: tuple[str, ...] = ("status", "verdict", "runs", "criteria", "bracket"),
) -> None:
    """Record of ``names`` what the page shows: the status, the verdict,
    the runs of all stages, the criteria, and the route's bracket."""
    if "status" in names:
        experiment.number(f"{prefix}-status", record.status)
    if "verdict" in names:
        experiment.number(f"{prefix}-verdict", record.verdict)
    if "runs" in names:
        experiment.number(f"{prefix}-runs", record.runs, "d")
    if "criteria" in names:
        experiment.number(
            f"{prefix}-criteria",
            "; ".join(
                f"{criterion}: {'yes' if met else 'no'}"
                for criterion, met in record.criteria.items()
            ),
        )
    if "bracket" in names and record.record is not None:
        low, _, high = record.record.bracket
        experiment.number(f"{prefix}-low", low, ".3f")
        experiment.number(f"{prefix}-high", high, ".3f")


def draw_plan_stages() -> Figure:
    """The stages of a plan, from writing to verdict, as a sketch."""
    fig, ax = diagrams.canvas(6.4, 4.4, (0.0, 12.8), (0.0, 8.8))
    top = (
        (1.5, "plan\nwritten"),
        (4.4, "check"),
        (7.3, "frozen:\ndigest"),
        (10.6, "positive\ncontrol"),
    )
    for x, label in top:
        diagrams.state_box(ax, (x, 7.4), label, width=2.2, height=1.1)
    for (a, _), (b, _) in itertools.pairwise(top):
        diagrams.arrow(ax, (a + 1.1, 7.4), (b - 1.1, 7.4))
    diagrams.text(ax, (4.4, 5.9), "refused, with\nevery problem", colour=1)
    diagrams.arrow(ax, (4.4, 6.85), (4.4, 6.35), colour=1, linestyle="--")
    bottom = (
        (10.6, "route and\ngrid baseline"),
        (6.9, "withheld tests,\nopened once"),
        (3.2, "criteria\nand verdict"),
    )
    for x, label in bottom:
        diagrams.state_box(ax, (x, 3.9), label, width=2.9, height=1.1)
    diagrams.arrow(ax, (10.6, 6.85), (10.6, 4.45))
    diagrams.text(ax, (10.75, 5.65), "passed", ha="left")
    diagrams.arrow(ax, (9.15, 3.9), (8.35, 3.9))
    diagrams.arrow(ax, (5.45, 3.9), (4.65, 3.9))
    diagrams.text(ax, (12.25, 5.65), "failed:\nstop", colour=1)
    diagrams.arrow(ax, (11.4, 6.85), (12.05, 6.15), colour=1, linestyle="--")
    diagrams.state_box(
        ax,
        (3.2, 1.3),
        "deviation record",
        width=3.6,
        height=0.9,
        colour=MUTED,
    )
    diagrams.arrow(ax, (3.2, 3.35), (3.2, 1.75), colour=MUTED, linestyle=":")
    diagrams.text(
        ax,
        (3.4, 2.55),
        "the plan executed\ndiffers from its digest",
        ha="left",
        colour=MUTED,
    )
    return fig


def draw_plan_results(replication: PlanRecord, original: PlanRecord) -> Figure:
    """The runs of each plan: the route's, its bracket, the grid baseline,
    the withheld test, and the predicted bound."""
    with figure_style():
        fig, axes = plt.subplots(2, 1, figsize=figsize("pair", legend=2), sharex=True)
        for ax, record, title in zip(
            axes,
            (replication, original),
            ("replication, 25 m/s", "original, 10 m/s"),
            strict=True,
        ):
            runs = sorted(
                (r for r in record.record.runs if r.stage != "check"),
                key=lambda r: r.arguments["angle"],
            )
            ax.plot(
                record.grid.settings,
                record.grid.values,
                linestyle="none",
                marker="s",
                markersize=MARKER,
                markerfacecolor="none",
                color=MUTED,
                label="grid baseline",
            )
            ax.plot(
                [r.arguments["angle"] for r in runs],
                [r.value for r in runs],
                linestyle="none",
                marker="o",
                markersize=MARKER,
                color=FIGURE_COLOURS[0],
                label="route",
            )
            for test in record.withheld:
                ax.plot(
                    test.settings,
                    test.values,
                    linestyle="none",
                    marker="^",
                    markersize=MARKER,
                    color=FIGURE_COLOURS[1],
                    label="withheld test",
                )
            low, _, high = record.record.bracket
            ax.axvspan(low, high, color=FIGURE_COLOURS[0], alpha=0.2, linewidth=0)
            bound = record_bound(record)
            ax.axvline(bound, color=MUTED, linestyle=":", linewidth=LINE["guide"])
            bottom, top = ax.get_ylim()
            direct_label(ax, bound, bottom + 0.15 * (top - bottom), "bound", MUTED)
            ax.set_ylabel("range (m)")
            ax.set_title(title, loc="left")
        axes[-1].set_xlabel("launch angle (deg)")
        axes[-1].legend(loc="upper center", bbox_to_anchor=(0.5, -0.3), ncol=3)
    return finish(fig)


def record_bound(record: PlanRecord) -> float:
    """The predicted bound of the plan a record executed."""
    return record.data["specification"]["hypothesis"]["prediction"]["value"]


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.figure("fig-plan-stages", draw_plan_stages)
    experiment.table(
        "refusals",
        [
            (what, part, message)
            for what, data in (
                ("no withheld test", without("withheld", ORIGINAL)),
                ("no stopping condition", without("stopping", ORIGINAL)),
                ("a test the search sees", seen_by_the_search(ORIGINAL)),
            )
            for part, message in refusal(data)
        ],
        [
            ("what was left out or changed", "", ""),
            ("part", "", ""),
            ("problem", "", ""),
        ],
        "Three plans that are refused before anything runs, with the part and"
        " the problem the check names.",
    )
    replication = run_plan(REPLICATION)
    stage_table(experiment, "replication-stages", replication)
    outcome(experiment, "replication", replication)
    # The published record: SA1's specification, run as SA1 runs it.
    lab = laboratory()
    published = route(parse(copy.deepcopy(SPECIFICATION), lab), lab)
    experiment.number(
        "reproduced",
        "identical" if published.runs == replication.record.runs else "different",
    )

    original = run_plan(ORIGINAL)
    stage_table(experiment, "original-stages", original)
    outcome(experiment, "original", original)
    experiment.number("original-bound", record_bound(original), "g")
    experiment.number(
        "grid-spacing", original.grid.settings[1] - original.grid.settings[0], ".2f"
    )
    experiment.number("original-grid-best", original.grid.best, ".2f")
    experiment.number("withheld-dt", ORIGINAL["withheld"][0]["numerical"], "g")
    experiment.number("route-dt", SLOW_THROW["variables"]["dt"]["value"], "g")
    experiment.figure(
        "fig-plan-results", partial(draw_plan_results, replication, original)
    )

    deviation = moved_prediction()
    outcome(experiment, "deviation", deviation, ("status", "verdict"))
    experiment.number("deviation-bound", record_bound(deviation), ".3f")
    experiment.table(
        "deviation",
        [
            (
                name,
                record_bound(r),
                r.verdict,
                "yes" if r.as_registered else "no",
                r.status,
            )
            for name, r in (("as frozen", original), ("bound moved", deviation))
        ],
        [
            ("plan", "", ""),
            ("bound", "deg", ".1f"),
            ("route's verdict", "", ""),
            ("as frozen", "", ""),
            ("status", "", ""),
        ],
        "The original plan as frozen and the same plan with its bound moved"
        " after the result, each executed against the digest frozen before"
        " the first run.",
    )

    outcome(
        experiment,
        "medium",
        run_plan(medium_throw()),
        ("status", "verdict", "criteria", "bracket"),
    )
    outcome(
        experiment, "control", run_plan(wrong_control()), ("status", "verdict", "runs")
    )
    return experiment


if __name__ == "__main__":
    main(run)
