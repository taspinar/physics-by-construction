"""The experiment of the lesson "Ising model and phase transitions".

The two-dimensional Ising model of ``pbc.thermodynamics.ising``, sampled by
Metropolis sweeps: the sampler against the exact enumeration of a small
lattice, the magnetisation against Onsager's exact curve and its finite-size
rounding, and the critical temperature estimated from the crossings of Binder
cumulants and compared with the exact value. Run it as a program to write the
figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.thermodynamics.experiments.ising_model_and_phase_transitions out
"""

from functools import partial
from itertools import pairwise

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from scipy.optimize import brentq

from pbc.abm.gas import mean_and_error
from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.thermodynamics.ising import (
    critical_temperature,
    crossing,
    exact_averages,
    exact_heat_capacity,
    jackknife,
    onsager_magnetisation,
    simulate,
    susceptibility,
)

# region: exact
SMALL = 4
check_temperatures = [1.5, 2.5, 3.5]
SMALL_REPLICAS = 16
SMALL_SWEEPS = 4000
# endregion: exact
# region: curve
sizes = [8, 16, 32]
temperatures = [1.6, 1.8, 2.0, 2.1, 2.2, 2.25, 2.3, 2.35, 2.4, 2.5, 2.6, 2.8, 3.0]
CURVE_REPLICAS = 6
CURVE_SWEEPS = 1000
BURN_IN = 300
ONSAGER_BELOW = 2.1  # compared with Onsager at and below this temperature
# endregion: curve
# region: binder
binder_sizes = [4, 8, 16]
binder_temperatures = [2.22, 2.24, 2.26, 2.28, 2.30, 2.32]
BINDER_REPLICAS = 12
binder_sweeps = {4: 6000, 8: 6000, 16: 5000}
BINDER_BURN_IN = 1000
# endregion: binder

# The three lattice sizes of a figure: marker, line style, and colour; grey is
# kept for the exact references.
SIZE_STYLES = [
    ("o", "--", FIGURE_COLOURS[0]),
    ("s", "-.", FIGURE_COLOURS[1]),
    ("^", ":", FIGURE_COLOURS[4]),
]


def exact_check(experiment: Experiment) -> float:
    """Metropolis runs of the 4 x 4 lattice against its exact enumeration at
    three temperatures; record the table and return the largest difference in
    standard errors."""
    exact_m, exact_e = exact_averages(SMALL, check_temperatures)
    m, e = simulate(
        SMALL,
        check_temperatures,
        SMALL_REPLICAS,
        SMALL_SWEEPS,
        BURN_IN,
        np.random.default_rng(1),
    )
    rows, distances = [], []
    for k, t in enumerate(check_temperatures):
        m_mean, m_error = mean_and_error(np.abs(m[:, k]).mean(axis=0))
        e_mean, e_error = mean_and_error(e[:, k].mean(axis=0))
        dm = abs(m_mean - exact_m[k]) / m_error
        de = abs(e_mean - exact_e[k]) / e_error
        distances += [dm, de]
        rows.append((t, exact_m[k], m_mean, dm, exact_e[k], e_mean, de))
    experiment.table(
        "exact-check",
        rows,
        [
            ("temperature", "J/k_B", ".1f"),
            ("exact <|m|>", "", ".4f"),
            ("sampled <|m|>", "", ".4f"),
            ("difference", "standard errors", ".1f"),
            ("exact energy per spin", "J", ".4f"),
            ("sampled energy per spin", "J", ".4f"),
            ("difference", "standard errors", ".1f"),
        ],
        "The mean absolute magnetisation and the mean energy per spin of the "
        "4 x 4 lattice, exact by summing over every configuration and "
        "sampled by sixteen independent Metropolis runs, with the difference in "
        "standard errors of the sampled mean.",
    )
    return max(distances)


def curve_runs():
    """Metropolis runs of three lattice sizes at every temperature of the
    curve: the magnetisation per spin of each sweep, by size."""
    return {
        size: simulate(
            size,
            temperatures,
            CURVE_REPLICAS,
            CURVE_SWEEPS,
            BURN_IN,
            np.random.default_rng(100 + size),
        )[0]
        for size in sizes
    }


def magnetisation_table(experiment: Experiment, runs) -> float:
    """<|m|> of the three sizes against Onsager's curve; record the table and
    return the largest difference of the largest lattice from Onsager, in
    standard errors, at the temperatures up to ``ONSAGER_BELOW``."""
    exact = onsager_magnetisation(np.array(temperatures))
    largest = sizes[-1]
    rows, distances = [], []
    for k, t in enumerate(temperatures):
        row = [t, float(exact[k])]
        for size in sizes:
            mean, error = mean_and_error(np.abs(runs[size][:, k]).mean(axis=0))
            row.append(mean)
            if size == largest:
                row.append(error)
                if t <= ONSAGER_BELOW:
                    distances.append(abs(mean - exact[k]) / error)
        rows.append(tuple(row))
    experiment.table(
        "magnetisation",
        rows,
        [
            ("temperature", "J/k_B", ".2f"),
            ("Onsager", "", ".4f"),
            *[(f"L = {size}", "", ".4f") for size in sizes],
            (f"standard error, L = {largest}", "", ".4f"),
        ],
        "The mean absolute magnetisation per spin of three lattice sizes, each "
        "from six independent Metropolis runs, against Onsager's spontaneous "
        "magnetisation of the infinite lattice.",
    )
    return max(distances)


def susceptibility_peaks(experiment: Experiment, runs) -> None:
    """The temperature of the largest susceptibility on the grid, by size;
    record the table."""
    t = np.array(temperatures)
    rows = []
    for size in sizes:
        chi = susceptibility(runs[size], t[:, None], size * size).mean(axis=1)
        k = int(np.argmax(chi))
        rows.append((size, float(t[k]), float(chi[k])))
    experiment.table(
        "susceptibility-peaks",
        rows,
        [
            ("lattice size L", "", "d"),
            ("temperature of the largest susceptibility", "J/k_B", ".2f"),
            ("largest susceptibility per spin", "1/J", ".1f"),
        ],
        "The temperature of the grid at which the susceptibility of each "
        "lattice size is largest, and its value, from the runs of the curve.",
    )


def draw_magnetisation(runs) -> Figure:
    """<|m|> against the temperature for three sizes, with Onsager's curve."""
    fine = np.linspace(temperatures[0], temperatures[-1], 400)
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    ax.plot(
        fine,
        onsager_magnetisation(fine),
        color=FIGURE_COLOURS[2],
        linewidth=1.4,
        label="Onsager, infinite lattice",
    )
    for (marker, line, colour), size in zip(SIZE_STYLES, sizes, strict=True):
        means = np.abs(runs[size]).mean(axis=0)
        ax.errorbar(
            temperatures,
            means.mean(axis=1),
            yerr=means.std(axis=1, ddof=1) / np.sqrt(CURVE_REPLICAS),
            color=colour,
            marker=marker,
            markersize=4,
            linestyle=line,
            linewidth=1.0,
            capsize=2,
            label=f"L = {size}",
        )
    ax.axvline(
        critical_temperature(), color=FIGURE_COLOURS[2], linestyle=":", linewidth=1.0
    )
    ax.annotate(
        "exact $T_c$",
        (critical_temperature(), 0.05),
        xytext=(6, 0),
        textcoords="offset points",
        color=FIGURE_COLOURS[2],
    )
    ax.set_xlabel(r"temperature $T$ ($J/k_B$)")
    ax.set_ylabel(r"mean absolute magnetisation $\langle|m|\rangle$")
    ax.legend(frameon=False, loc="upper right")
    return fig


def binder_runs():
    """The second and fourth moments of the magnetisation of each independent
    run, by size: arrays of shape (2, temperatures, replicas)."""
    moments = {}
    for size in binder_sizes:
        m, _ = simulate(
            size,
            binder_temperatures,
            BINDER_REPLICAS,
            binder_sweeps[size],
            BINDER_BURN_IN,
            np.random.default_rng(200 + size),
        )
        moments[size] = np.stack([(m**2).mean(axis=0), (m**4).mean(axis=0)])
    return moments


def cumulant(moments):
    """The Binder cumulant at each temperature from the moments of the runs
    pooled over the runs (the last axis)."""
    m2 = moments[0].mean(axis=-1)
    m4 = moments[1].mean(axis=-1)
    return 1.0 - m4 / (3.0 * m2**2)


def pair_crossing(pair) -> float:
    """The crossing temperature of the cumulants of two sizes; ``pair`` holds
    the moments of the smaller and of the larger size."""
    return crossing(binder_temperatures, cumulant(pair[0]), cumulant(pair[1]))


def crossing_check(experiment: Experiment, moments) -> list:
    """The crossings of the cumulants of successive sizes with their jackknife
    standard errors against the exact Tc; record the table and return its
    rows."""
    tc = critical_temperature()
    rows = []
    for small, large in pairwise(binder_sizes):
        estimate, error = jackknife(
            pair_crossing, np.stack([moments[small], moments[large]])
        )
        rows.append(
            (f"{small} and {large}", estimate, error, 100.0 * (estimate - tc) / tc)
        )
    experiment.table(
        "crossings",
        rows,
        [
            ("lattice sizes", "", ""),
            ("crossing temperature", "J/k_B", ".4f"),
            ("standard error", "J/k_B", ".4f"),
            ("deviation from the exact Tc", "%", ".2f"),
        ],
        "The temperature at which the Binder cumulants of two lattice sizes "
        "cross, from straight lines fitted to the cumulants, with the jackknife "
        "standard error over twelve independent runs per size, against "
        "Onsager's critical temperature.",
    )
    return rows


def draw_binder_crossing(moments) -> Figure:
    """The Binder cumulant against the temperature for three sizes, with the
    exact Tc."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    for (marker, line, colour), size in zip(SIZE_STYLES, binder_sizes, strict=True):
        value, error = jackknife(cumulant, moments[size])
        ax.errorbar(
            binder_temperatures,
            value,
            yerr=error,
            color=colour,
            marker=marker,
            markersize=4,
            linestyle=line,
            linewidth=1.0,
            capsize=2,
            label=f"L = {size}",
        )
    ax.axvline(
        critical_temperature(), color=FIGURE_COLOURS[2], linestyle=":", linewidth=1.2
    )
    ax.annotate(
        "exact $T_c$",
        (critical_temperature(), 0.03),
        xycoords=("data", "axes fraction"),
        xytext=(6, 0),
        textcoords="offset points",
        color=FIGURE_COLOURS[2],
    )
    ax.set_xlabel(r"temperature $T$ ($J/k_B$)")
    ax.set_ylabel("Binder cumulant $U$ (dimensionless)")
    ax.legend(frameon=False, loc="upper right")
    return fig


def below(value: float, bound: float = 1e-12) -> str:
    """A difference at the level of round-off, shown against a bound."""
    return f"below {bound:.0e}" if value < bound else f"{value:.1e}"


def critical_point(experiment: Experiment) -> None:
    """Exercise 1: the temperature at which Onsager's magnetisation vanishes,
    sinh(2 / T) = 1, found numerically and against 2 / ln(1 + sqrt 2); record
    the table."""
    root = brentq(lambda t: np.sinh(2.0 / t) - 1.0, 1.0, 4.0, xtol=1e-14)
    experiment.table(
        "critical-point",
        [(root, critical_temperature(), below(abs(root - critical_temperature())))],
        [
            ("root of sinh(2/T) = 1", "J/k_B", ".6f"),
            ("2 / ln(1 + sqrt 2)", "J/k_B", ".6f"),
            ("difference", "J/k_B", ""),
        ],
        "The temperature at which Onsager's magnetisation vanishes, found by a "
        "root finder, and the closed form.",
    )


def small_lattice_peak(experiment: Experiment) -> None:
    """Exercise 2: the exact heat capacity of the 2 x 2 and 4 x 4 lattices, and
    the temperature of its peak; record the table."""
    fine = np.linspace(1.5, 4.0, 2501)
    rows = []
    for size in (2, 4):
        c = exact_heat_capacity(size, fine)
        k = int(np.argmax(c))
        rows.append((size, float(fine[k]), float(c[k])))
    experiment.table(
        "small-lattice-peak",
        rows,
        [
            ("lattice size L", "", "d"),
            ("temperature of the peak", "J/k_B", ".3f"),
            ("heat capacity per spin at the peak", "k_B", ".3f"),
        ],
        "The temperature at which the exact heat capacity per spin of two small "
        "lattices peaks, on a grid of step 0.001, and the peak value.",
    )


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.number("exact-largest", exact_check(experiment), ".1f")
    experiment.number("critical-temperature", critical_temperature(), ".4f")
    runs = curve_runs()
    experiment.number("onsager-largest", magnetisation_table(experiment, runs), ".1f")
    experiment.figure("fig-ising-magnetisation", partial(draw_magnetisation, runs))
    susceptibility_peaks(experiment, runs)
    moments = binder_runs()
    experiment.figure("fig-binder-crossing", partial(draw_binder_crossing, moments))
    rows = crossing_check(experiment, moments)
    experiment.number("crossing-first", abs(rows[0][3]), ".1f")
    experiment.number("crossing-last", abs(rows[-1][3]), ".1f")
    critical_point(experiment)
    small_lattice_peak(experiment)
    return experiment


if __name__ == "__main__":
    main(run)
