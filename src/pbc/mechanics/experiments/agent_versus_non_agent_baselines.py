"""The experiment of the lesson "The agent against methods without one".

On the three protocols of the interactive discovery benchmark
(``pbc.discovery.benchmark``): the agent (the run of the partial condition on
each environment), a plain model given the same task and no ``measure`` tool,
random selection of settings with least squares, a grid with least squares,
and a grid with sparse identification (the symbolic fit), all on the same
hidden world, held-out settings, and tolerance. Every row carries the verdict
of ``comparable`` against the agent. Run it as a program to write the figure
and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.agent_versus_non_agent_baselines out

The live runs of the plain model, which ask a model and need its key, are a
separate command behind the optional dependency ``openai``: ``LIVE``, run
with ``uv run --locked --no-dev --extra openai python -m
pbc.discovery.benchmark plain-projectile plain-oscillator
plain-central-force``.
"""

from dataclasses import replace
from functools import partial
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.agents.display import AllowlistDisplay, RunDisplay
from pbc.authoring import FIGURE_COLOURS
from pbc.authoring.repository import REPOSITORY_ROOT
from pbc.discovery.benchmark import (
    BUDGET,
    ENVIRONMENTS,
    GRID,
    PLAIN_RUNS,
    PROTOCOLS,
    TOLERANCE,
    Cell,
    Entry,
    agent_entry,
    baseline_entry,
    baselines,
    environment,
    plain_allowlist,
    random_fit,
    replay_cell,
    task_of,
    verdict,
)
from pbc.experiment import Experiment, main

# The live runs of the lesson: a model, its key, and the extra openai.
LIVE = "pbc.discovery.benchmark plain-projectile plain-oscillator plain-central-force"

# The pages that hold the frozen runs.
D1 = REPOSITORY_ROOT / "site/lessons/agents-llm/05-discovering-a-force-law"
D2 = REPOSITORY_ROOT / "site/lessons/agents-llm/06-prior-knowledge-in-discovery"
EV2 = REPOSITORY_ROOT / "site/lessons/agents-llm/12-interactive-discovery-benchmarks"
LESSON = REPOSITORY_ROOT / "site/lessons/agents-llm/13-agent-versus-non-agent-baselines"


def home(cell: Cell) -> Path:
    """The page that holds the fixture of ``cell``."""
    if cell.home == "D1":
        return D1
    if cell.home == "D2":
        return D2
    if cell.home == "EV2":
        return EV2
    return LESSON


# The condition of the agent: the task the plain model is given too.
CONDITION = "partial"
METHODS = (
    "agent",
    "plain model",
    "random + least squares",
    "grid + least squares",
    "grid + sparse identification",
    "random + least squares, the agent's probes",
)
# The floor of the error axis: a claim that equals the world scores 0.
FLOOR = 1e-6
# Where a method without a claim is drawn, above every error.
NO_CLAIM = 5.0
# Exercise: the seeds of the random selection.
SEEDS = tuple(range(20))


def plain_task(experiment: Experiment) -> None:
    """What the plain model and the agent are given; record the table."""
    rows = []
    for name in ENVIRONMENTS:
        agent_system, agent_task = task_of(GRID[name, CONDITION].run)
        plain_system, plain_task_ = task_of(PLAIN_RUNS[name].run)
        rows.append(
            (
                name,
                "same" if agent_task == plain_task_ else "differs",
                "same" if agent_system == plain_system else "differs",
            )
        )
    experiment.table(
        "ev3-inputs",
        rows,
        [
            ("environment", "", ""),
            ("task text", "", ""),
            ("system prompt", "", ""),
        ],
        "What the plain model shares with the agent, checked by the build.",
    )


def entries(experiment: Experiment) -> dict[str, dict[str, Entry]]:
    """Every method on every environment, scored by the judge of its
    protocol; record the table and return the entries."""
    found: dict[str, dict[str, Entry]] = {}
    for name, protocol in ENVIRONMENTS.items():
        p = PROTOCOLS[protocol]
        # region: replay
        _, _, agent = replay_cell(GRID[name, CONDITION], home(GRID[name, CONDITION]))
        _, _, plain = replay_cell(PLAIN_RUNS[name], home(PLAIN_RUNS[name]))
        # endregion: replay
        rows = {
            "agent": agent_entry("agent", p, agent),
            "plain model": agent_entry("plain model", p, plain, plain=True),
        }
        for result in baselines(protocol):
            rows[result.name] = baseline_entry(p, result)
        matched = random_fit(protocol, agent.probes, 0)
        rows[METHODS[-1]] = baseline_entry(replace(p, budget=agent.probes), matched)
        found[name] = rows
    experiment.table(
        "ev3-entries",
        [
            (
                name,
                method,
                e.allowed,
                e.probes,
                e.held_out_error,
                "yes" if e.recovered else "no",
                "-" if method == "agent" else verdict(rows["agent"], e),
            )
            for name, rows in found.items()
            for method, e in rows.items()
        ],
        [
            ("environment", "", ""),
            ("method", "", ""),
            ("probes allowed", "", "d"),
            ("probes spent", "", "d"),
            ("held-out error", "relative", ".2g"),
            ("recovered", "", ""),
            ("against the agent", "", ""),
        ],
        "Every method on the three environments, scored by the same judge;"
        " the last column is the build's check against the agent.",
    )
    return found


def tally(experiment: Experiment, found) -> None:
    """Recoveries of each method over the three environments; record the
    table."""
    experiment.table(
        "ev3-tally",
        [
            (
                method,
                sum(rows[method].recovered for rows in found.values()),
                len(found),
                "yes"
                if all(
                    not verdict(rows["agent"], rows[method]).startswith("not")
                    for rows in found.values()
                )
                else "no",
            )
            for method in METHODS
        ],
        [
            ("method", "", ""),
            ("recovered", "", "d"),
            ("environments", "", "d"),
            ("comparable with the agent", "", ""),
        ],
        "Recoveries per method, and whether the build counts the comparison"
        " with the agent as meaningful.",
    )


def draw_methods(found) -> Figure:
    """The held-out error of every method on each environment, with the
    tolerance; methods told apart by marker and position."""
    names = list(found)
    markers = ("o", "x", "s", "D", "^", "v")
    colours = (0, 1, 4, 3, 5, 2)
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    width = 0.13
    for k, method in enumerate(METHODS):
        x = np.arange(len(names)) + (k - (len(METHODS) - 1) / 2) * width
        y = [found[n][method].held_out_error for n in names]
        y = [NO_CLAIM if not np.isfinite(v) else max(v, FLOOR) for v in y]
        ax.scatter(
            x,
            y,
            marker=markers[k],
            s=40,
            color=FIGURE_COLOURS[colours[k]],
            label=method,
            zorder=3,
        )
    ax.axhline(TOLERANCE, color=FIGURE_COLOURS[2], linestyle="--", label="tolerance")
    ax.axhline(FLOOR, color=FIGURE_COLOURS[2], linestyle=":", linewidth=0.8)
    ax.text(
        0.99,
        FLOOR * 1.4,
        "error 0: the claim equals the hidden value",
        transform=ax.get_yaxis_transform(),
        ha="right",
        va="bottom",
        fontsize=7,
        color=FIGURE_COLOURS[2],
    )
    for i, n in enumerate(names):
        for k, method in enumerate(METHODS):
            if not np.isfinite(found[n][method].held_out_error):
                x = i + (k - (len(METHODS) - 1) / 2) * width
                ax.annotate(
                    "no claim",
                    (x, NO_CLAIM),
                    xytext=(0, -12),
                    textcoords="offset points",
                    ha="center",
                    fontsize=7,
                )
    ax.set_yscale("log")
    ax.set_ylim(FLOOR / 2, 10.0)
    ax.set_xticks(np.arange(len(names)), names)
    ax.set_xlabel("environment")
    ax.set_ylabel("held-out error (relative, log scale)")
    ax.legend(fontsize=7, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.2))
    return fig


def seeds(experiment: Experiment, found) -> None:
    """Exercise: random selection with the agent's number of probes, over
    twenty seeds; record the table."""
    rows = []
    for name, protocol in ENVIRONMENTS.items():
        probes = found[name]["agent"].probes
        p = PROTOCOLS[protocol]
        results = [random_fit(protocol, probes, seed) for seed in SEEDS]
        recovered = sum(
            baseline_entry(replace(p, budget=probes), r).recovered for r in results
        )
        rows.append((name, probes, recovered, len(SEEDS)))
    experiment.table(
        "ev3-seeds",
        rows,
        [
            ("environment", "", ""),
            ("probes", "", "d"),
            ("seeds that recover", "", "d"),
            ("seeds", "", "d"),
        ],
        "Random selection with the agent's number of probes, over twenty seeds.",
    )


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.number("tolerance", TOLERANCE, "g")
    experiment.number("budget", BUDGET)
    plain_task(experiment)
    experiment.display(
        "plain-allowlist", AllowlistDisplay(plain_allowlist(environment("projectile")))
    )
    for name in ENVIRONMENTS:
        recording, transcript, _ = replay_cell(PLAIN_RUNS[name], home(PLAIN_RUNS[name]))
        experiment.display(f"run-plain-{name}", RunDisplay(recording, transcript))
    found = entries(experiment)
    tally(experiment, found)
    experiment.figure("fig-agent-versus-baselines", partial(draw_methods, found))
    seeds(experiment, found)
    return experiment


if __name__ == "__main__":
    main(run)
