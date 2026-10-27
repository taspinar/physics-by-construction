"""The experiment of the lesson "An interactive discovery benchmark".

Three environments, each under one protocol, and the three conditions of
prior knowledge: nine frozen runs (``pbc.discovery.benchmark``), five of them
recorded for this lesson and four read from the pages of D1 and D2. The
check that only the task differs within an environment, the replay and the
score of every run, the fit to each run's own readings, the baselines with
the same budget, and the comparability check on the comparisons a reader
might make. Run it as a program to write the figure and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.interactive_discovery_benchmarks out

The live runs, which ask a model and need its key, are a separate command
behind the optional dependency ``openai``: ``LIVE``, run with
``uv run --locked --no-dev --extra openai python -m pbc.discovery.benchmark
projectile-full projectile-partial projectile-none central-full
central-none``.
"""

from functools import partial
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from scipy.stats import fisher_exact

from pbc.agents.display import AllowlistDisplay, RunDisplay
from pbc.agents.loop import MAX_CALLS_PER_MESSAGE
from pbc.authoring import FIGURE_COLOURS
from pbc.authoring.repository import REPOSITORY_ROOT
from pbc.discovery import environment_allowlist, force_lab
from pbc.discovery.benchmark import (
    BUDGET,
    ENVIRONMENTS,
    GRID,
    MAX_STEPS,
    PROTOCOLS,
    TOLERANCE,
    Cell,
    agent_entry,
    baseline_entry,
    baselines,
    entry,
    environment,
    fit_readings,
    replay_cell,
    task_of,
    tools_of,
    verdict,
)
from pbc.discovery.protocol import CONDITIONS
from pbc.experiment import Experiment, main

# The live runs of the lesson: a model, its key, and the extra openai.
LIVE = (
    "pbc.discovery.benchmark projectile-full projectile-partial projectile-none"
    " central-full central-none"
)

# The pages that hold the frozen runs of the grid.
D1 = REPOSITORY_ROOT / "site/lessons/agents-llm/05-discovering-a-force-law"
D2 = REPOSITORY_ROOT / "site/lessons/agents-llm/06-prior-knowledge-in-discovery"
D3 = REPOSITORY_ROOT / "site/lessons/agents-llm/07-a-modified-force-law"
LESSON = REPOSITORY_ROOT / "site/lessons/agents-llm/12-interactive-discovery-benchmarks"
PAGES = {
    "D1": "the force-law lesson",
    "D2": "the prior-knowledge lesson",
    "EV2": "this page",
}
# The runs recorded for this lesson, shown on it.
SHOWN = (
    ("projectile", "full"),
    ("projectile", "partial"),
    ("projectile", "none"),
    ("central-force", "full"),
    ("central-force", "none"),
)


def home(cell: Cell) -> Path:
    """The page that holds the fixture of ``cell``."""
    if cell.home == "D1":
        return D1
    if cell.home == "D2":
        return D2
    return LESSON


# The floor of the error axis: a claim that equals the world scores 0.
FLOOR = 1e-6


def fairness(experiment: Experiment) -> None:
    """Within each environment, what the three runs share, from the protocol
    and the record of each run; record the table."""
    rows = []
    for name in ENVIRONMENTS:
        runs = [GRID[name, c].run for c in CONDITIONS]
        prompts = [task_of(r) for r in runs]
        same = (
            len({entry(r).protocol for r in runs}) == 1,
            len({entry(r).info.model for r in runs}) == 1,
            len({system for system, _ in prompts}) == 1,
            len(
                {str(tools_of(r)(environment(entry(r).protocol)).specs()) for r in runs}
            )
            == 1,
            len({entry(r).info.seed for r in runs}) == 1,
            len({task for _, task in prompts}) == 1,
        )
        rows.append((name, *("same" if s else "differs" for s in same)))
    experiment.table(
        "ev2-fairness",
        rows,
        [
            ("environment", "", ""),
            ("protocol", "", ""),
            ("model", "", ""),
            ("system prompt", "", ""),
            ("tools and bounds", "", ""),
            ("seed", "", ""),
            ("task text", "", ""),
        ],
        "Within each environment, what the three runs share, checked by the"
        " build from the protocol and the record of each run.",
    )


def replay_grid():
    """Replay and score every run of the grid."""
    # region: replay
    runs = {key: replay_cell(cell, home(cell)) for key, cell in GRID.items()}
    # endregion: replay
    return runs


def score_table(experiment: Experiment, runs) -> None:
    """The nine claims, scored again on each environment's held-out settings;
    record the table."""
    experiment.table(
        "ev2-scores",
        [
            (
                e,
                c,
                s.probes,
                s.refused,
                s.held_out_error,
                s.outcome,
                PAGES[GRID[e, c].home],
            )
            for (e, c), (_, _, s) in runs.items()
        ],
        [
            ("environment", "", ""),
            ("condition", "", ""),
            ("probes", "", "d"),
            ("refused", "", "d"),
            ("held-out error", "relative", ".2g"),
            ("outcome", "", ""),
            ("recorded for", "", ""),
        ],
        "The nine runs of the benchmark, scored again by the build.",
    )


def reading_fits(experiment: Experiment, runs):
    """The family fitted to each run's own readings; record the table and
    return the fits."""
    fits = {
        (e, c): fit_readings(ENVIRONMENTS[e], transcript)
        for (e, c), (_, transcript, _) in runs.items()
    }
    experiment.table(
        "ev2-readings",
        [
            (
                e,
                c,
                f.probes,
                f.held_out_error,
                "yes"
                if baseline_entry(PROTOCOLS[ENVIRONMENTS[e]], f).recovered
                else "no",
            )
            for (e, c), f in fits.items()
        ],
        [
            ("environment", "", ""),
            ("condition", "", ""),
            ("readings", "", "d"),
            ("held-out error of the fit", "relative", ".2g"),
            ("the readings support a recovery", "", ""),
        ],
        "Least squares on each run's own readings: what the probes supported.",
    )
    return fits


def tally(experiment: Experiment, runs, fits) -> dict[str, int]:
    """Recoveries per condition over the three environments; record the
    table and return the recoveries."""
    recovered = {
        c: sum(runs[e, c][2].recovered for e in ENVIRONMENTS) for c in CONDITIONS
    }
    supported = {
        c: sum(
            baseline_entry(PROTOCOLS[ENVIRONMENTS[e]], fits[e, c]).recovered
            for e in ENVIRONMENTS
        )
        for c in CONDITIONS
    }
    experiment.table(
        "ev2-tally",
        [(c, recovered[c], supported[c], len(ENVIRONMENTS)) for c in CONDITIONS],
        [
            ("condition", "", ""),
            ("claims that recover", "", "d"),
            ("readings that support it", "", "d"),
            ("runs", "", "d"),
        ],
        "Recoveries per condition, one run on each environment.",
    )
    return recovered


def beside_the_baselines(experiment: Experiment) -> None:
    """The baselines on each environment with the protocol's budget; record
    the table."""
    rows = []
    for name, protocol in ENVIRONMENTS.items():
        for result in baselines(protocol):
            e = baseline_entry(PROTOCOLS[protocol], result)
            rows.append(
                (
                    name,
                    result.name,
                    result.probes,
                    result.held_out_error,
                    "yes" if e.recovered else "no",
                    result.reason or "fit consistent with the noise",
                )
            )
    experiment.table(
        "ev2-baselines",
        rows,
        [
            ("environment", "", ""),
            ("method", "", ""),
            ("probes", "", "d"),
            ("held-out error", "relative", ".2g"),
            ("recovered", "", ""),
            ("note", "", ""),
        ],
        "The baselines without a model on each environment, with the same budget.",
    )


def comparisons(experiment: Experiment, runs) -> None:
    """Comparisons a reader might make, each judged by ``comparable``;
    record the table."""

    def agent(e: str, c: str):
        return agent_entry(f"{e}, {c}", PROTOCOLS[ENVIRONMENTS[e]], runs[e, c][2])

    modified = force_lab.replay_run("modified", D3)[2]
    d3 = agent_entry("modified law", force_lab.PROTOCOLS["modified"], modified)
    grid = baseline_entry(
        PROTOCOLS[ENVIRONMENTS["oscillator"]], baselines(ENVIRONMENTS["oscillator"])[0]
    )
    pairs = [
        (
            "full against none, on the oscillator",
            agent("oscillator", "full"),
            agent("oscillator", "none"),
        ),
        (
            "partial on the oscillator against grid + least squares on it",
            agent("oscillator", "partial"),
            grid,
        ),
        (
            "full on the projectile against full on the oscillator",
            agent("projectile", "full"),
            agent("oscillator", "full"),
        ),
        (
            "partial on the central force against the modified-law run",
            agent("central-force", "partial"),
            d3,
        ),
    ]
    experiment.table(
        "ev2-comparisons",
        [(what, verdict(a, b)) for what, a, b in pairs],
        [("comparison", "", ""), ("the check says", "", "")],
        "Comparisons a reader might make, judged by the build from the protocols.",
    )


def draw_benchmark_errors(runs, fits) -> Figure:
    """The held-out error of every claim and of the fit to the same run's
    readings, grouped by environment, with the tolerance."""
    names = list(ENVIRONMENTS)
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    markers = {"full": "o", "partial": "s", "none": "^"}
    colours = {
        "full": FIGURE_COLOURS[0],
        "partial": FIGURE_COLOURS[1],
        "none": FIGURE_COLOURS[4],
    }
    for k, c in enumerate(CONDITIONS):
        x = np.arange(len(names)) + (k - 1) * 0.22
        claims = [max(runs[e, c][2].held_out_error, FLOOR) for e in names]
        own = [max(fits[e, c].held_out_error, FLOOR) for e in names]
        ax.scatter(
            x,
            claims,
            marker=markers[c],
            s=46,
            color=colours[c],
            label=f"{c}: agent's claim",
            zorder=3,
        )
        ax.scatter(
            x,
            own,
            marker=markers[c],
            s=46,
            facecolors="none",
            edgecolors=colours[c],
            label=f"{c}: fit to its readings",
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
    ax.set_yscale("log")
    ax.set_xticks(np.arange(len(names)), names)
    ax.set_xlabel("environment")
    ax.set_ylabel("held-out error (relative, log scale)")
    ax.legend(fontsize=7, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.2))
    ax.set_ylim(FLOOR / 2, 1.0)
    return fig


def chance(experiment: Experiment, recovered: dict[str, int]) -> None:
    """Exercise: Fisher's exact test of the recoveries of each condition
    against those of the full condition; record the table."""
    n = len(ENVIRONMENTS)
    rows = []
    for c in ("partial", "none"):
        table = [
            [recovered["full"], n - recovered["full"]],
            [recovered[c], n - recovered[c]],
        ]
        rows.append((f"full against {c}", float(fisher_exact(table).pvalue)))
    experiment.table(
        "ev2-chance",
        rows,
        [("comparison", "", ""), ("p-value (two-sided)", "", ".2g")],
        "How likely recoveries at least this different are if the condition"
        " made no difference.",
    )


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.number("tolerance", TOLERANCE, "g")
    experiment.number("budget", BUDGET)
    experiment.number("max-steps", MAX_STEPS)
    experiment.number("max-calls", MAX_CALLS_PER_MESSAGE)
    experiment.number("runs", len(GRID))
    fairness(experiment)
    experiment.display(
        "allowlist", AllowlistDisplay(environment_allowlist(environment("projectile")))
    )
    runs = replay_grid()
    for e, c in SHOWN:
        experiment.display(f"run-{e}-{c}", RunDisplay(*runs[e, c][:2]))
    score_table(experiment, runs)
    experiment.number("recovered", sum(s.recovered for _, _, s in runs.values()))
    fits = reading_fits(experiment, runs)
    recovered = tally(experiment, runs, fits)
    beside_the_baselines(experiment)
    comparisons(experiment, runs)
    experiment.figure(
        "fig-benchmark-errors", partial(draw_benchmark_errors, runs, fits)
    )
    chance(experiment, recovered)
    return experiment


if __name__ == "__main__":
    main(run)
