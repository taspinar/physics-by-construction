"""The experiment of the lesson "Defining scientific quality".

Every frozen run of the interactive discovery benchmark (the nine runs of its
grid, the three runs of the plain model, and the run on the drawn world) and
two deterministic baselines on each system, each measured on its own by the
metrics of ``pbc.discovery.quality``: correctness, reasoning, evidence,
completion, cost, measurement efficiency, the software interface, and
physical-tool use, never added into one number. Then the diagram task's two
recorded runs, scored by the kind of understanding each question asks for.
Run it as a program to write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.defining_scientific_quality out

The page records nothing new: every run it measures is a fixture of the
pages of D1, D2, AE2, and AE3, replayed here, and the live commands are on
those pages.
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.agents.vision import score as score_answers
from pbc.authoring import FIGURE_COLOURS
from pbc.authoring.repository import REPOSITORY_ROOT
from pbc.discovery import tasks
from pbc.discovery.baselines import grid_probe, least_squares, random_probe
from pbc.discovery.benchmark import (
    ENVIRONMENTS,
    GRID,
    PLAIN_RUNS,
    PROTOCOLS,
    SEED,
    TOLERANCE,
    Cell,
    entry,
    replay_cell,
)
from pbc.discovery.protocol import CONDITIONS
from pbc.discovery.quality import (
    Profile,
    baseline_profile,
    by_category,
    readings_of,
    run_profile,
)
from pbc.experiment import Experiment, main
from pbc.figure_language import figsize, figure_style, finish

# The live run of a recording this lesson measures: the drawn world of the
# benchmark lesson, with a model and its key and the extra openai. The other
# live commands are on the pages that hold their fixtures.
LIVE = "pbc.discovery.tasks world"

# The pages that hold the frozen runs, each used by name.
D1 = REPOSITORY_ROOT / "site/lessons/agents-llm/05-discovering-a-force-law"
D2 = REPOSITORY_ROOT / "site/lessons/agents-llm/06-prior-knowledge-in-discovery"
AE2 = REPOSITORY_ROOT / "site/lessons/agents-llm/12-interactive-discovery-benchmarks"
AE3 = REPOSITORY_ROOT / "site/lessons/agents-llm/13-agent-versus-non-agent-baselines"


def home(cell: Cell):
    """The page that holds the fixture of ``cell``."""
    if cell.home == "D1":
        return D1
    if cell.home == "D2":
        return D2
    if cell.home == "EV2":
        return AE2
    return AE3


def _yes(value: bool | None) -> str:
    return "-" if value is None else ("yes" if value else "no")


def profiles() -> dict[str, Profile]:
    """Every contestant's profile, by a short name."""
    found: dict[str, Profile] = {}
    for name, protocol in ENVIRONMENTS.items():
        p = PROTOCOLS[protocol]
        for condition in CONDITIONS:
            cell = GRID[name, condition]
            # region: one-row
            _, transcript, score = replay_cell(cell, home(cell))
            calls = entry(cell.run).info.cost.model_calls
            found[f"{name}, {condition}"] = run_profile(
                f"agent, {condition}", name, p, transcript, score, SEED, calls, p.budget
            )
            # endregion: one-row
        cell = PLAIN_RUNS[name]
        _, transcript, score = replay_cell(cell, home(cell))
        calls = entry(cell.run).info.cost.model_calls
        found[f"{name}, plain"] = run_profile(
            "plain model", name, p, transcript, score, SEED, calls, 0
        )
        world = p.make(SEED)
        for label, data in (
            ("grid + least squares", grid_probe(world)),
            ("random + least squares", random_probe(world, SEED)),
        ):
            fit = least_squares(p.make(SEED), data, label)
            found[f"{name}, {label}"] = baseline_profile(name, p, fit, data, SEED)
    _, transcript, score = tasks.replay_world(AE2)
    found["drawn world, none"] = run_profile(
        "agent, none",
        "drawn world",
        tasks.PROTOCOL,
        transcript,
        score,
        SEED,
        tasks.WORLD_RUN.info.cost.model_calls,
        tasks.PROTOCOL.budget,
    )
    return found


def profile_table(experiment: Experiment, found: dict[str, Profile]) -> None:
    """Record the table of every profile."""
    experiment.table(
        "ae1-profiles",
        [
            (
                q.environment,
                q.who,
                _yes(q.correct),
                _yes(q.reasoning),
                _yes(q.evidence),
                _yes(q.completed),
                "-" if q.model_calls is None else str(q.model_calls),
                q.tool_calls,
                f"{q.probes} of {q.allowed}",
                "-" if q.to_evidence is None else str(q.to_evidence),
                q.refused,
                "-" if q.information is None else f"{q.information:.2f}",
            )
            for q in found.values()
        ],
        [
            ("system", "", ""),
            ("contestant", "", ""),
            ("correct", "", ""),
            ("reasoning", "", ""),
            ("evidence", "", ""),
            ("completed", "", ""),
            ("model messages", "", ""),
            ("tool calls", "", "d"),
            ("probes", "", ""),
            ("probes to evidence", "", ""),
            ("refused calls", "", "d"),
            ("information against a grid", "", ""),
        ],
        "Every contestant measured on its own: no column is added to another."
        " A dash marks a measure that is undefined for the contestant.",
    )


def disagreements(experiment: Experiment, found: dict[str, Profile]) -> None:
    """Count where two measures disagree; record the table and the numbers
    the page states."""
    runs = [q for q in found.values() if q.model_calls is not None]
    agents = [q for q in runs if q.allowed > 0]
    rows = [
        (
            "correct, yet the claim does not reproduce the run's own readings",
            sum(q.correct and q.reasoning is False for q in agents),
        ),
        (
            "the readings support a recovery, yet the claim is not correct",
            sum(q.evidence is True and not q.correct for q in agents),
        ),
        (
            "completed, yet not correct",
            sum(q.completed and not q.correct for q in runs),
        ),
        (
            "refused calls, yet settings more informative than a grid",
            sum(
                q.refused > 0 and q.information is not None and q.information > 1
                for q in agents
            ),
        ),
        (
            "probes spent beyond those that already supported a recovery",
            sum(q.to_evidence is not None and q.probes > q.to_evidence for q in agents),
        ),
    ]
    experiment.table(
        "ae1-disagreements",
        rows,
        [("what one score would hide", "", ""), ("runs", "", "d")],
        f"Runs of a model ({len(runs)}, of which {len(agents)} could probe) in"
        " which two measures disagree.",
    )
    spring = found["oscillator, partial"]
    experiment.number("spring-probes", spring.probes)
    experiment.number("spring-evidence", spring.to_evidence)


def items(experiment: Experiment) -> None:
    """The diagram task's two runs, scored by category; record the table."""
    key = tasks.diagram_key()
    scored = {
        item.id: score_answers(tasks.QUESTIONS, key, tasks.replay_items(item, AE2)[1])
        for item in tasks.ITEM_RUNS
    }
    pictures = by_category(scored["pictures"], tasks.CATEGORY, tasks.CATEGORIES)
    text = by_category(scored["text"], tasks.CATEGORY, tasks.CATEGORIES)
    experiment.table(
        "ae1-items",
        [
            (
                category,
                pictures[category][1],
                pictures[category][0],
                text[category][0],
                pictures[category][2],
            )
            for category in tasks.CATEGORIES
        ],
        [
            ("what the question asks", "", ""),
            ("questions", "", "d"),
            ("correct with the pictures", "", "d"),
            ("correct without them", "", "d"),
            ("a guess, on average", "", ".1f"),
        ],
        "The diagram task of the benchmark lesson, scored by the kind of"
        " understanding each question asks for.",
    )


def draw_probe_information(found: dict[str, Profile]) -> Figure:
    """Where the three spring runs and the grid probed, over the bound
    amplitude times time on how much a reading can say about the frequency
    (the bound does not depend on the hidden stiffness)."""
    p = PROTOCOLS[ENVIRONMENTS["oscillator"]]
    world = p.make(SEED)
    amplitude, time = world.controls
    t = np.linspace(time.low, time.high, 200)
    a = np.linspace(amplitude.low, amplitude.high, 200)
    tt, aa = np.meshgrid(t, a)
    markers = {"full": "o", "partial": "s", "none": "^"}
    colours = {"full": 0, "partial": 1, "none": 4}
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line", legend=4))
        lines = ax.contour(
            tt,
            aa,
            aa * tt,
            levels=(0.5, 1.5, 3.0, 4.5),
            colors=FIGURE_COLOURS[2],
            linewidths=0.8,
            linestyles=":",
        )
        ax.clabel(lines, fmt=lambda v: f"A t = {v:g}")
        probes = found["oscillator, partial"].probes  # every spring run spent as many
        grid = grid_probe(type(world)(budget=probes)).settings
        ax.scatter(
            [s["time"] for s in grid],
            [s["amplitude"] for s in grid],
            marker="+",
            s=36,
            color=FIGURE_COLOURS[2],
            label=f"grid of {probes} probes, the reference",
            zorder=3,
        )
        for condition in CONDITIONS:
            cell = GRID["oscillator", condition]
            _, transcript, _ = replay_cell(cell, home(cell))
            data = readings_of(p, transcript, SEED)
            q = found[f"oscillator, {condition}"]
            ax.scatter(
                [s["time"] for s in data.settings],
                [s["amplitude"] for s in data.settings],
                marker=markers[condition],
                s=34,
                facecolors="none",
                edgecolors=FIGURE_COLOURS[colours[condition]],
                zorder=4,
                label=f"agent, {condition} (information {q.information:.2f})",
            )
        ax.set_xlim(time.low - 0.1, time.high + 0.1)
        ax.set_ylim(0.0, amplitude.high + 0.15)
        ax.set_xlabel(f"time since the release ({time.unit})")
        ax.set_ylabel(f"amplitude ({amplitude.unit})")
        fig.legend(loc="outside lower center", ncols=1)
    return finish(fig)


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.number("tolerance", TOLERANCE, "g")
    found = profiles()
    profile_table(experiment, found)
    disagreements(experiment, found)
    experiment.figure("fig-probe-information", partial(draw_probe_information, found))
    experiment.figure("fig-task-launcher", tasks.draw_launcher)
    items(experiment)
    return experiment


if __name__ == "__main__":
    main(run)
