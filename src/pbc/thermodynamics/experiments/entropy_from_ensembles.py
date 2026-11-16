"""The experiment of the lesson "Entropy from ensembles".

The Ehrenfest model of particles hopping between two halves of a box
(``pbc.thermodynamics.entropy``): the counting of microstates, the Gibbs
entropy of an ensemble of boxes against the exact distribution, and the bias
of the estimate from a finite ensemble. Run it as a program to write the
figure and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.thermodynamics.experiments.entropy_from_ensembles out
"""

from functools import partial
from math import comb, log

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.abm.gas import mean_and_error
from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.figure_language import LINE, figsize, figure_style, finish
from pbc.thermodynamics.entropy import (
    distribution,
    ehrenfest_ensemble,
    equilibrium_entropy,
    exact_distribution,
    gibbs_entropy,
    log_multiplicity,
    mean_left,
    plug_in_bias,
    stirling_log_multiplicity_half,
)

# region: counting
N = 12
macrostates = np.array([12, 9, 6, 3, 0])
# endregion: counting
# region: ensemble
MEMBERS = 5000
STEPS = 120
SEEDS = range(6)
# endregion: ensemble
# region: late
LATE = 12 * N
# endregion: late


def counting(experiment: Experiment) -> None:
    """The number of microstates of five macrostates and their entropy;
    record the table."""
    experiment.table(
        "counting",
        [
            (int(n), comb(N, int(n)), log(comb(N, int(n))), s)
            for n, s in zip(macrostates, log_multiplicity(N, macrostates), strict=True)
        ],
        [
            ("particles on the left", "", "d"),
            ("microstates", "", "d"),
            ("ln of the count", "", ".4f"),
            ("entropy from the log-gamma function", "", ".4f"),
        ],
        "The number of microstates of five macrostates of twelve particles and the "
        "entropy S / k_B computed in two ways.",
    )


def stirling(experiment: Experiment) -> None:
    """The entropy of the largest macrostate, exact and by Stirling; record
    the table."""
    sizes = [10, 100, 1000]
    experiment.table(
        "stirling",
        [
            (
                n,
                float(log_multiplicity(n, np.array([n // 2]))[0]),
                stirling_log_multiplicity_half(n),
                equilibrium_entropy(n),
            )
            for n in sizes
        ],
        [
            ("particles", "", "d"),
            ("exact ln C(N, N/2)", "", ".4f"),
            ("Stirling approximation", "", ".4f"),
            ("N ln 2", "", ".4f"),
        ],
        "The entropy of the largest macrostate for three numbers of particles, "
        "exact and by the Stirling approximation, next to the leading term N ln 2.",
    )


def ensemble_runs(experiment: Experiment):
    """Six runs of an ensemble of boxes from all particles on the left: the
    entropy of the ensemble at every step against that of the exact
    distribution; record the table of four steps."""
    runs = [
        ehrenfest_ensemble(N, MEMBERS, STEPS, np.random.default_rng(seed))
        for seed in SEEDS
    ]
    estimates = np.array(
        [[gibbs_entropy(distribution(row, N), N) for row in counts] for counts in runs]
    )
    exact_rows = exact_distribution(N, N, STEPS)
    exact_entropy = np.array([gibbs_entropy(row, N) for row in exact_rows])
    mean_estimate = estimates.mean(axis=0)

    checkpoints = [0, 10, 30, 120]
    experiment.table(
        "ensemble-runs",
        [
            (t, mean_estimate[t], exact_entropy[t], equilibrium_entropy(N))
            for t in checkpoints
        ],
        [
            ("step", "", "d"),
            ("entropy of the ensemble", "", ".3f"),
            ("entropy of the exact distribution", "", ".3f"),
            ("N ln 2", "", ".3f"),
        ],
        "The entropy S / k_B of the ensemble averaged over six runs, that of the "
        "exact distribution of the model, and the equilibrium value, at four "
        "steps.",
    )
    return runs, mean_estimate, exact_entropy


def draw_entropy_growth(mean_estimate, exact_entropy) -> Figure:
    """The entropy of the ensemble and of the exact distribution against the
    step."""
    steps = np.arange(STEPS + 1)
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line"))
        ax.plot(
            steps, mean_estimate, color=FIGURE_COLOURS[0], label="ensemble of boxes"
        )
        ax.plot(
            steps,
            exact_entropy,
            color=FIGURE_COLOURS[2],
            linestyle=":",
            linewidth=2.5,
            label="exact distribution",
        )
        ax.axhline(
            equilibrium_entropy(N),
            color=FIGURE_COLOURS[1],
            linestyle="--",
            linewidth=LINE["guide"],
            label="N ln 2",
        )
        ax.set_xlabel("step")
        ax.set_ylabel(r"entropy $S/k_B$")
        ax.legend()
    return finish(fig)


def mean_check(experiment: Experiment, runs) -> float:
    """The mean number of particles on the left over six runs against the
    exact formula; record the table and return the largest distance in
    standard errors."""
    steps = np.arange(STEPS + 1)
    exact_mean = mean_left(N, N, steps)
    mean_runs = np.array([counts.mean(axis=1) for counts in runs])
    mean_value = mean_runs.mean(axis=0)
    mean_error = mean_runs.std(axis=0, ddof=1) / np.sqrt(len(runs))
    mean_checkpoints = [10, 30, 60, 120]
    experiment.table(
        "mean-check",
        [
            (
                t,
                mean_value[t],
                mean_error[t],
                exact_mean[t],
                abs(mean_value[t] - exact_mean[t]) / mean_error[t],
            )
            for t in mean_checkpoints
        ],
        [
            ("step", "", "d"),
            ("mean number on the left", "", ".3f"),
            ("standard error", "", ".3f"),
            ("exact mean", "", ".3f"),
            ("difference", "standard errors", ".1f"),
        ],
        "The mean number of particles on the left over six runs at four steps, "
        "against the exact formula.",
    )
    return max(
        abs(mean_value[t] - exact_mean[t]) / mean_error[t] for t in mean_checkpoints
    )


def equilibrium_check(experiment: Experiment) -> list:
    """The equilibrium entropy estimated from ensembles of three sizes,
    before and after the correction of the bias; record the table and return
    its rows."""
    rows = []
    for members in (200, 2000, 20000):
        raw, corrected = [], []
        for seed in SEEDS:
            counts = ehrenfest_ensemble(N, members, LATE, np.random.default_rng(seed))
            p = distribution(counts[-1], N)
            raw.append(gibbs_entropy(p, N))
            corrected.append(raw[-1] + plug_in_bias(p, members))
        raw_mean, raw_error = mean_and_error(np.array(raw))
        corrected_mean, corrected_error = mean_and_error(np.array(corrected))
        target = equilibrium_entropy(N)
        rows.append(
            (
                members,
                target - raw_mean,
                abs(raw_mean - target) / raw_error,
                abs(corrected_mean - target) / corrected_error,
            )
        )

    experiment.table(
        "equilibrium-check",
        rows,
        [
            ("boxes per run", "", "d"),
            ("shortfall of the plug-in estimate", "", ".5f"),
            ("plug-in estimate off by", "standard errors", ".1f"),
            ("corrected estimate off by", "standard errors", ".1f"),
        ],
        "The equilibrium entropy of the ensemble estimated from six runs of three "
        "sizes, as a shortfall from N ln 2 and in standard errors, before and "
        "after the first-order correction of the bias.",
    )
    return rows


def boxes_for_a_thousandth(experiment: Experiment) -> None:
    """Exercise 1: the number of boxes for a shortfall of a thousandth, and
    the shortfall measured with it; record the table."""
    needed = int(np.ceil(N / (2 * 1e-3)))
    shortfalls = []
    for seed in SEEDS:
        counts = ehrenfest_ensemble(N, needed, LATE, np.random.default_rng(seed))
        shortfalls.append(
            equilibrium_entropy(N) - gibbs_entropy(distribution(counts[-1], N), N)
        )
    experiment.table(
        "boxes-for-a-thousandth",
        [(needed, float(np.mean(shortfalls)))],
        [("boxes", "", "d"), ("mean shortfall", "", ".5f")],
        "The number of boxes the formula asks for and the shortfall of the plug-in "
        "estimate measured with it, over six runs.",
    )


def approach_to_the_middle(experiment: Experiment) -> None:
    """Exercise 2: the steps for the mean of forty particles to come within
    one of the middle, by the formula and in one ensemble; record the
    table."""
    n_big = 40
    t_formula = np.log(n_big / 2) / -np.log(1 - 1 / n_big)
    big = ehrenfest_ensemble(n_big, 4000, 200, np.random.default_rng(0))
    distance = np.abs(big.mean(axis=1) - n_big / 2)
    t_measured = int(np.argmax(distance < 1.0))
    experiment.table(
        "approach-to-the-middle",
        [(t_formula, t_measured)],
        [("steps by the formula", "", ".1f"), ("steps in the ensemble", "", "d")],
        "The number of steps for the mean to come within one particle of N / 2, by "
        "the formula and in one ensemble.",
    )


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    counting(experiment)
    stirling(experiment)
    runs, mean_estimate, exact_entropy = ensemble_runs(experiment)
    experiment.figure(
        "fig-entropy-growth", partial(draw_entropy_growth, mean_estimate, exact_entropy)
    )
    experiment.number("mean-distance", mean_check(experiment, runs), ".1f")
    rows = equilibrium_check(experiment)
    experiment.number("corrected-largest", max(row[3] for row in rows), ".1f")
    experiment.number("plug-in-off", rows[-1][2], ".0f")
    experiment.number("shortfall-small", rows[0][1], ".3f")
    experiment.number("shortfall-large", rows[-1][1], ".5f")
    boxes_for_a_thousandth(experiment)
    approach_to_the_middle(experiment)
    return experiment


if __name__ == "__main__":
    main(run)
