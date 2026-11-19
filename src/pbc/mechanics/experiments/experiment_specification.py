"""The experiment of the lesson "From research question to experiment
specification".

A specification of the projectile experiment (at which angle does a tennis
ball with drag land furthest away?), written before the first run, checked
against the laboratory, and executed by the scripted route of
``pbc.agents.specification``: a fixed procedure with no model in it. The
same specification is run on the throw without drag, where it must refute
its hypothesis, and three specifications of the exercises are parsed or
run. Run it as a program to write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.experiment_specification out
"""

import copy
from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.agents import projectile_lab
from pbc.agents.specification import (
    PARTS,
    Action,
    Laboratory,
    Record,
    Specification,
    SpecificationRejected,
    execute,
    parse,
)
from pbc.agents.tools import Tool
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
from pbc.mechanics.projectile import projectile_range

# region: specification
SPECIFICATION = {
    "question": (
        "At what launch angle does a tennis ball thrown at 25 m/s from the"
        " ground, with air drag, land furthest away?"
    ),
    "hypothesis": {
        "statement": (
            "Drag takes speed from the ball along its whole path, and most on"
            " a long, flat flight, so the best angle is lower than the 45"
            " degrees of a throw without drag, by more than the resolution."
        ),
        "prediction": {
            "quantity": "angle",
            "relation": "below",
            "value": 44.0,
            "unit": "deg",
        },
    },
    "variables": {
        "angle": {"role": "varied", "unit": "deg", "low": 20.0, "high": 60.0},
        "speed": {"role": "fixed", "unit": "m/s", "value": 25.0},
        "dt": {"role": "numerical", "unit": "s", "value": 0.004},
    },
    "observable": {"name": "range_m", "unit": "m", "goal": "largest"},
    "actions": ["range_with_drag"],
    "success": {"resolution": {"value": 1.0, "unit": "deg"}, "stable": True},
    "stopping": {"max_runs": 40},
}
# endregion: specification


def _range_in_vacuum(speed: float, angle: float, dt: float) -> dict[str, float]:
    return {"range_m": projectile_range(speed, angle, projectile_lab.MASS, 0.0, dt)}


def laboratory() -> Laboratory:
    """The actions an experiment on the ball may be specified with: the
    simulated throw with drag, the tool the agent of the later lesson is
    given, and the same simulation without drag; each with the unit of every
    argument and of its result."""
    with_drag = projectile_lab.tools().tool("range_with_drag")
    in_vacuum = Tool(
        name="range_in_vacuum",
        description="Simulate the same throw without air drag.",
        parameters=with_drag.parameters,
        function=_range_in_vacuum,
    )
    units = {"speed": "m/s", "angle": "deg", "dt": "s"}
    return Laboratory(
        tuple(
            Action(tool, units=units, returns={"range_m": "m"})
            for tool in (with_drag, in_vacuum)
        )
    )


def without_drag() -> dict:
    """The specification of the lesson with one change: the permitted action
    is the throw without drag. The hypothesis is the same."""
    changed = copy.deepcopy(SPECIFICATION)
    changed["actions"] = ["range_in_vacuum"]
    return changed


# region: at-forty
AT_FORTY = copy.deepcopy(SPECIFICATION)
AT_FORTY["question"] = (
    "Is the best launch angle of the same ball lower at 40 m/s than at 25 m/s?"
)
AT_FORTY["hypothesis"] = {
    "statement": (
        "Drag grows with the square of the speed, so at 40 m/s it matters"
        " more and the best angle lies below the bracket found at 25 m/s."
    ),
    "prediction": {
        "quantity": "angle",
        "relation": "below",
        "value": 40.0,
        "unit": "deg",
    },
}
AT_FORTY["variables"]["speed"]["value"] = 40.0
# endregion: at-forty


def defective() -> dict:
    """The specification of the second exercise: the lesson's with three
    defects."""
    changed = copy.deepcopy(SPECIFICATION)
    del changed["stopping"]
    del changed["variables"]["angle"]["unit"]
    changed["variables"]["dt"] = {"role": "numerical", "unit": "ms", "value": 4.0}
    return changed


def small_budget() -> dict:
    """The specification of the third exercise: a budget of twelve runs."""
    changed = copy.deepcopy(SPECIFICATION)
    changed["stopping"]["max_runs"] = 12
    return changed


def refusal(data: dict) -> list[tuple[str, str]]:
    """The problems ``parse`` finds in ``data``: the part and the message of
    each, or an empty list when the specification is accepted."""
    try:
        parse(data, laboratory())
    except SpecificationRejected as rejected:
        return [(problem.part, problem.message) for problem in rejected.problems]
    return []


def refusals(experiment: Experiment) -> None:
    """Three ways to leave something out, and what ``parse`` answers; record
    the table."""
    no_stop = copy.deepcopy(SPECIFICATION)
    del no_stop["stopping"]
    no_unit = copy.deepcopy(SPECIFICATION)
    del no_unit["variables"]["angle"]["unit"]
    radians = copy.deepcopy(SPECIFICATION)
    radians["variables"]["angle"].update(unit="rad", low=0.35, high=1.05)
    radians["hypothesis"]["prediction"].update(unit="rad", value=0.77)
    radians["success"]["resolution"].update(unit="rad", value=0.02)
    rows = [
        (what, part, message)
        for what, data in (
            ("no stopping condition", no_stop),
            ("the angle without a unit", no_unit),
            ("the angle in radians", radians),
        )
        for part, message in refusal(data)
    ]
    experiment.table(
        "refusals",
        rows,
        [
            ("what was left out or changed", "", ""),
            ("part", "", ""),
            ("problem", "", ""),
        ],
        "Three specifications that are refused before anything runs, with the"
        " part and the problem the check names.",
    )


def same_number_two_units(experiment: Experiment) -> None:
    """The throw at the number 0.7 read as degrees and read as radians;
    record both ranges."""
    ball = (projectile_lab.MASS, projectile_lab.DRAG, 0.002)
    experiment.number("range-as-degrees", projectile_range(25.0, 0.7, *ball), ".2f")
    experiment.number(
        "range-as-radians", projectile_range(25.0, np.degrees(0.7), *ball), ".2f"
    )


def run_table(experiment: Experiment, name: str, record: Record, caption: str) -> None:
    """Record the runs of ``record`` as the table ``name``."""
    experiment.table(
        name,
        [
            (
                run.number,
                run.stage,
                run.arguments["angle"],
                run.arguments["dt"],
                run.value,
            )
            for run in record.runs
        ],
        [
            ("run", "", "d"),
            ("stage", "", ""),
            ("angle", "deg", ".4f"),
            ("time step", "s", ".3f"),
            ("range", "m", ".3f"),
        ],
        caption,
    )


def outcome(experiment: Experiment, prefix: str, record: Record) -> None:
    """Record what the route reported: the runs it used, why it stopped, the
    bracket, the criteria, and the verdict."""
    experiment.number(f"{prefix}-runs", len(record.runs), "d")
    experiment.number(f"{prefix}-stop", record.stop)
    experiment.number(f"{prefix}-verdict", record.verdict)
    experiment.number(
        f"{prefix}-criteria",
        ", ".join(
            f"{name} {'met' if met else 'not met'}"
            for name, met in record.criteria.items()
        ),
    )
    if record.bracket is not None:
        low, _, high = record.bracket
        experiment.number(f"{prefix}-low", low, ".2f")
        experiment.number(f"{prefix}-high", high, ".2f")


def independent_scan(specification: Specification) -> float:
    """The best angle of a scan the route did not make: every eighth of a
    degree of the specified range, at a quarter of the specified time step,
    straight from the simulation."""
    angles = np.arange(specification.varied.low, specification.varied.high, 0.125)
    dt = specification.numerical.value / 4.0
    ranges = [
        projectile_range(25.0, angle, projectile_lab.MASS, projectile_lab.DRAG, dt)
        for angle in angles
    ]
    return float(angles[int(np.argmax(ranges))])


def draw_specification_parts() -> Figure:
    """The seven parts of a specification in three groups, and what reads
    each group, as a sketch."""
    fig, ax = diagrams.canvas(6.4, 3.9, (0.0, 12.8), (0.0, 7.8))
    groups = (
        ("what is asked", ("question", "hypothesis"), 2.2),
        ("what may be done", ("variables", "observable", "actions"), 6.4),
        ("when it is over", ("success", "stopping"), 10.6),
    )
    assert tuple(part for _, parts, _ in groups for part in parts) == PARTS
    for title, parts, x in groups:
        diagrams.text(ax, (x, 7.4), title, colour="#57606a")
        diagrams.state_box(
            ax, (x, 5.9), "\n".join(parts), width=3.4, height=2.2, colour=0
        )
    diagrams.state_box(ax, (6.4, 2.6), "route", width=2.6, height=0.9, colour=1)
    diagrams.state_box(ax, (2.2, 2.6), "laboratory", width=2.6, height=0.9, colour=2)
    diagrams.state_box(ax, (10.6, 0.7), "verdict", width=2.6, height=0.9, colour=1)
    # The route does only what the middle group permits, in the laboratory.
    diagrams.arrow(ax, (6.4, 4.75), (6.4, 3.1), colour=1)
    diagrams.text(ax, (6.2, 3.95), "settings,\nin range", ha="right")
    diagrams.arrow(ax, (5.05, 2.6), (3.55, 2.6), colour=1)
    diagrams.text(ax, (4.3, 3.0), "runs")
    # The last group tells the route when to stop.
    diagrams.arrow(ax, (10.0, 4.75), (7.4, 3.1), colour=1, linestyle="--")
    diagrams.text(ax, (9.2, 3.75), "when to stop", ha="left")
    # The verdict reads the record of the route and the first group.
    diagrams.arrow(ax, (6.4, 2.1), (9.25, 0.85), colour=1)
    diagrams.text(ax, (8.1, 1.75), "record", ha="left")
    diagrams.line(ax, [(0.65, 4.75), (0.65, 0.55)], colour=0, linestyle=":")
    diagrams.arrow(ax, (0.65, 0.55), (9.25, 0.55), colour=0, linestyle=":")
    diagrams.text(ax, (4.3, 0.2), "prediction")
    return fig


def draw_specified_search(with_drag: Record, in_vacuum: Record) -> Figure:
    """The runs of the route with drag and without: the range against the
    angle, the bracket each ends in, and the bound the hypothesis predicts."""
    bound = SPECIFICATION["hypothesis"]["prediction"]["value"]
    series = (
        ("with drag", with_drag, FIGURE_COLOURS[0], "o"),
        ("without drag", in_vacuum, FIGURE_COLOURS[1], "s"),
    )
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line"))
        for name, record, colour, marker in series:
            first = [run for run in record.runs if run.stage != "check"]
            first.sort(key=lambda run: run.arguments["angle"])
            angles = [run.arguments["angle"] for run in first]
            ranges = [run.value for run in first]
            ax.plot(
                angles,
                ranges,
                color=colour,
                marker=marker,
                markersize=MARKER,
                linewidth=LINE["guide"],
                linestyle="-" if marker == "o" else "--",
            )
            low, _, high = record.bracket
            ax.axvspan(low, high, color=colour, alpha=0.25, linewidth=0)
            direct_label(
                ax,
                angles[-1],
                ranges[-1],
                name,
                colour,
                offset=(0.0, -12.0),
                ha="right",
                va="top",
            )
        # Room under the lower curve for its name.
        ax.set_ylim(bottom=22.0)
        ax.axvline(bound, color=MUTED, linestyle=":", linewidth=LINE["guide"])
        low, high = ax.get_ylim()
        direct_label(ax, bound, 0.5 * (low + high), "predicted\nbound", MUTED)
        ax.set_xlabel("launch angle (deg)")
        ax.set_ylabel("range (m)")
    return finish(fig)


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    lab = laboratory()
    experiment.figure("fig-specification-parts", draw_specification_parts)
    same_number_two_units(experiment)
    refusals(experiment)

    # region: execute
    specification = parse(SPECIFICATION, lab)
    with_drag = execute(specification, lab)
    # endregion: execute
    run_table(
        experiment,
        "runs",
        with_drag,
        "Every run of the scripted route on the throw with drag, in the order"
        " it was made; ranges to the millimetre.",
    )
    outcome(experiment, "drag", with_drag)
    for stage in ("scan", "refine", "check"):
        count = sum(run.stage == stage for run in with_drag.runs)
        experiment.number(f"drag-{stage}", count, "d")
    experiment.number("budget", specification.max_runs, "d")
    experiment.number("bound", specification.prediction.value, "g")
    experiment.number("scan-best", independent_scan(specification), ".3f")

    in_vacuum = execute(parse(without_drag(), lab), lab)
    outcome(experiment, "vacuum", in_vacuum)
    experiment.figure(
        "fig-specified-search", partial(draw_specified_search, with_drag, in_vacuum)
    )

    at_forty = execute(parse(AT_FORTY, lab), lab)
    outcome(experiment, "forty", at_forty)
    experiment.table(
        "defects",
        refusal(defective()),
        [("part", "", ""), ("problem", "", "")],
        "The problems the check finds in the specification of the exercise.",
    )
    short = execute(parse(small_budget(), lab), lab)
    outcome(experiment, "short", short)
    return experiment


if __name__ == "__main__":
    main(run)
