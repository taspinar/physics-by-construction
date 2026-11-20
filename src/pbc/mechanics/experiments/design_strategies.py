"""The part of the experiment of lesson A4 (MD8) that compares four ways of
choosing the readings under one budget (F147; ``pbc.agents.strategy_lab``).

Every strategy at every seed is an attempt in the evaluator's ledger
(``pbc.evidence``); the page's table and figure are read from the ledger's
summary, never from what a strategy or a session reported. The experiment of
the lesson (``pbc.mechanics.experiments.experimental_design_agent``) calls
``extend``.
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.agents.design_lab import BUDGET, MAX_STEPS, THRESHOLD
from pbc.agents.strategy_lab import (
    HYBRID_OPENING,
    MAXIMUM_SPEED,
    MORE_SEEDS,
    RECORDED,
    SEEDS,
    STRATEGIES,
    ledger,
)
from pbc.authoring import FIGURE_COLOURS
from pbc.authoring.repository import REPOSITORY_ROOT
from pbc.evidence.records import COMPLETED, summary
from pbc.evidence.robustness import success_interval
from pbc.experiment import Experiment
from pbc.figure_language import figsize, figure_style, finish

# The recorded sessions, next to the page that shows them.
LESSON = REPOSITORY_ROOT / "site/lessons/agents-llm/04-an-experimental-design-agent"


def rows_by_strategy(found, seeds) -> dict[str, list]:
    """The summary rows of each strategy at ``seeds``, in the order of the
    seeds; an attempt that is not in the ledger is missing from its list."""
    wanted = {f"{name}-{seed}" for name in STRATEGIES for seed in seeds}
    rows = {name: [] for name in STRATEGIES}
    for row in found.rows:
        if row.attempt in wanted:
            rows[row.candidate].append(row)
    return rows


# region: uncertainty
def over_seeds(rows) -> tuple:
    """A strategy over its seeds: the attempts, the correct ones with their
    exact interval at a level of ninety-five percent, the mean chi-square
    difference with its standard error, and the median relative uncertainty
    of the quadratic constant. An attempt that is not completed counts as
    not correct and has no difference."""
    n = len(rows)
    correct = sum(r.correct is True for r in rows)
    low, high = success_interval(correct, n)
    differences = np.array(
        [r.metrics["chi-square difference"] for r in rows if r.status == COMPLETED]
    )
    error = differences.std(ddof=1) / np.sqrt(len(differences))
    uncertainty = np.median([r.metrics["relative uncertainty of k"] for r in rows])
    return n, correct, low, high, differences.mean(), error, uncertainty


# endregion: uncertainty


def strategy_table(experiment: Experiment, found) -> list[tuple]:
    """The four strategies at the shared seeds, and the two without a model
    at all the seeds."""
    shared = rows_by_strategy(found, SEEDS)
    every = rows_by_strategy(found, MORE_SEEDS)
    lines = []
    for name in STRATEGIES:
        lines.append((name, *over_seeds(shared[name])))
    for name in ("scripted", "adaptive"):
        lines.append((name, *over_seeds(every[name])))
    experiment.table(
        "strategies",
        lines,
        columns=[
            ("strategy", "", "s"),
            ("seeds", "", "d"),
            ("correct", "", "d"),
            ("interval, low", "", ".2f"),
            ("interval, high", "", ".2f"),
            ("mean chi-square difference", "", ".1f"),
            ("its standard error", "", ".1f"),
            ("median relative uncertainty of k", "", ".3f"),
        ],
        caption="Each strategy over the seeds of the instrument, as the evaluator"
        " recomputed it: the attempts, those correct (a discrimination in favour"
        " of quadratic drag), the exact (Clopper-Pearson) interval of the rate of"
        " success at a level of ninety-five percent, the"
        " mean chi-square of linear drag minus that of quadratic drag with its"
        " standard error over the seeds, and the median relative standard"
        " uncertainty of the quadratic constant. The first four rows share five"
        " seeds; the last two repeat the strategies without a model on forty.",
    )
    return lines


def overlap(lines) -> str:
    """Whether the intervals of the rates of success of ``lines`` share a
    point: then the seeds cannot rank the strategies by success."""
    shared = max(line[3] for line in lines) <= min(line[4] for line in lines)
    return "overlap" if shared else "do not overlap"


def draw_strategies(differences: dict[str, list[float]], threshold: float) -> Figure:
    """The chi-square difference of each attempt, one column of points per
    strategy, and the threshold."""
    markers = ("o", "s", "^", "D")
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line"))
        for i, values in enumerate(differences.values()):
            ax.plot(
                np.full(len(values), i),
                values,
                linestyle="none",
                marker=markers[i],
                color=FIGURE_COLOURS[i],
                markerfacecolor="none",
            )
        ax.axhline(threshold, color="black", linestyle="--", linewidth=1)
        ax.annotate(
            "threshold",
            (len(differences) - 0.5, threshold),
            textcoords="offset points",
            xytext=(0, 4),
            ha="right",
        )
        ax.set_xticks(range(len(differences)), list(differences))
        ax.set_xlim(-0.5, len(differences) - 0.5)
        ax.set_ylim(bottom=0)
        ax.set_ylabel("chi-square of linear drag minus\nthat of quadratic drag")
        ax.set_xlabel("strategy (five seeds each)")
    return finish(fig)


def extend(experiment: Experiment):
    """The comparison of the four strategies, for the lesson's page;
    returns the drawing of its figure, which the lesson's experiment
    records."""
    experiment.number("strategy-speed", MAXIMUM_SPEED, "g")
    experiment.number("strategy-seeds", len(SEEDS))
    experiment.number("more-seeds", len(MORE_SEEDS))
    experiment.number("hybrid-opening", HYBRID_OPENING)
    experiment.number("strategy-readings", BUDGET)
    experiment.number("strategy-messages", MAX_STEPS)
    experiment.number("strategy-recorded", RECORDED)
    record = ledger(LESSON, MORE_SEEDS)
    found = summary(record, LESSON)
    experiment.number("attempts", found.total)
    experiment.number("invalidated", len(found.invalidations))
    experiment.number(
        "not-completed", sum(n for s, n in found.counts.items() if s != COMPLETED)
    )
    lines = strategy_table(experiment, found)
    four, two = lines[: len(STRATEGIES)], lines[len(STRATEGIES) :]
    for line in four:
        experiment.number(f"correct-{line[0].lower()}", line[2])
    for line in two:
        experiment.number(f"correct-{line[0]}-more", line[2])
    experiment.number("overlap-shared", overlap(four))
    experiment.number("overlap-more", overlap(two))
    by_mean = sorted(four, key=lambda line: -line[5])
    experiment.number("difference-order", ", ".join(line[0] for line in by_mean))
    means = {line[0]: line[5] for line in four}
    experiment.number(
        "margin-ratio",
        min(means["adaptive"], means["hybrid"]) / means["scripted"],
        ".1f",
    )
    shared = rows_by_strategy(found, SEEDS)
    readings = {e.attempt: e.resources["readings"] for e in record.evaluations}
    experiment.number(
        "llm-readings-least",
        min(readings[r.attempt] for r in shared["LLM"] if r.attempt in readings),
    )
    differences = {
        name: [
            r.metrics["chi-square difference"] for r in rows if r.status == COMPLETED
        ]
        for name, rows in shared.items()
    }
    return partial(draw_strategies, differences, THRESHOLD)
