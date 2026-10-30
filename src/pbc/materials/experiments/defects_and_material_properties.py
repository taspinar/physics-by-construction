"""The experiment of the lesson "Defects and material properties".

The number of vacancies a crystal holds in equilibrium, from the exact
minimum of its free energy against the closed form; a vacancy hopping on a
square lattice at the Arrhenius rate, its diffusion coefficient measured
and checked against the random walk of T1 (``pbc.thermodynamics.diffusion``)
and its migration energy recovered from an Arrhenius fit; and the atoms the
vacancy moves, whose correlated jumps give the tracer correlation factor
1 / (pi - 1). Run it as a program to write the figures and numbers of the
page:

    uv run --locked --no-dev \\
        python -m pbc.materials.experiments.defects_and_material_properties out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.materials.defects import (
    BOLTZMANN,
    SQUARE_LATTICE_CORRELATION,
    correlation_factor,
    exact_vacancies,
    free_energy,
    hop_rate,
    lattice_walks,
    vacancy_exchanges,
    vacancy_fraction,
)
from pbc.thermodynamics.diffusion import (
    diffusion_coefficient,
    mean_squared_displacement,
    predicted_diffusion_coefficient,
    random_walks,
)

# region: setup
# Illustrative values of the size of those of a metal, not fitted to one.
FORMATION = 1.0  # the energy to make a vacancy (eV)
MIGRATION = 0.7  # the barrier of a vacancy's hop (eV)
ATTEMPT = 1e13  # the attempt frequency nu (1/s)
SPACING = 0.25e-9  # the lattice spacing a (m)
SITES = 10**12  # the sites of a small crystal
temperatures = [600.0, 800.0, 1000.0, 1200.0]  # (K)
# endregion: setup

# region: walk
WALKERS = 8000
GROUPS = 20  # the walkers split into groups for the standard error
HOPS = 200  # the mean number of hops a walker makes in a run
RECORDS = 50  # the recorded times of a run
# endregion: walk

# region: exchange
SIDE = 64  # the periodic lattice of the vacancy and the atoms
START, END = 2000, 8000  # f from the growth between these numbers of jumps
RUNS = 2000  # independent runs
sides = [4, 8, 16, 32]  # smaller lattices, for the exercise
# endregion: exchange


def kt(temperature):
    """k T (eV) at the temperature (K)."""
    return BOLTZMANN * np.asarray(temperature, dtype=float)


def vacancies(experiment: Experiment):
    """The exact minimum of the free energy against the closed form at
    each temperature; record the table and return the largest difference
    in vacancies."""
    rows, gaps = [], []
    for temperature in temperatures:
        fraction = float(vacancy_fraction(FORMATION, kt(temperature)))
        closed = fraction * SITES
        exact = exact_vacancies(SITES, FORMATION, float(kt(temperature)))
        gaps.append(abs(exact - closed))
        rows.append((temperature, fraction, closed, exact, exact - closed))
    experiment.table(
        "vacancies",
        rows,
        [
            ("temperature", "K", ".0f"),
            ("vacancy fraction, closed form", "", ".3e"),
            ("vacancies, closed form", "", ".2f"),
            ("vacancies, exact minimum", "", "d"),
            ("difference", "vacancies", ".3f"),
        ],
        "The number of vacancies on 10^12 sites (formation energy 1.0 eV) "
        "that minimises the exact free energy n E_f - k T ln C(N, n), found "
        "by bisection on its steps, against the closed form "
        "N e^(-E_f/kT) / (1 + e^(-E_f/kT)) of Stirling's approximation.",
    )
    return max(gaps)


def draw_free_energy() -> Figure:
    """G(n), its energy and its entropy term on 10^8 sites at 1000 K, with
    the exact minimum and the closed form."""
    sites, temperature = 10**8, 1000.0
    t = float(kt(temperature))
    closed = float(vacancy_fraction(FORMATION, t)) * sites
    n = np.arange(0, int(3 * closed))
    g = free_energy(sites, n, FORMATION, t)
    energy = n * FORMATION
    exact = exact_vacancies(sites, FORMATION, t)
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(6.4, 5.2), sharex=True)
    top.plot(n, energy, color=FIGURE_COLOURS[1], linestyle="--", label="energy n E_f")
    top.plot(
        n, g - energy, color=FIGURE_COLOURS[2], linestyle=":", label="entropy term -T S"
    )
    top.plot(n, g, color=FIGURE_COLOURS[0], linestyle="-", label="free energy G")
    top.set_ylabel("change of energy (eV)")
    top.legend(fontsize="small", loc="upper left")
    bottom.plot(n, g, color=FIGURE_COLOURS[0], linestyle="-", label="free energy G")
    bottom.plot(
        exact,
        g[exact],
        "o",
        color=FIGURE_COLOURS[0],
        markerfacecolor="none",
        markersize=9,
        label="exact minimum",
    )
    bottom.axvline(
        closed, color=FIGURE_COLOURS[3], linestyle="-.", label="closed form N c_v"
    )
    bottom.set_xlabel("number of vacancies n")
    bottom.set_ylabel("G, enlarged (eV)")
    bottom.legend(fontsize="small", loc="upper center")
    for ax in (top, bottom):
        ax.axhline(0, color=FIGURE_COLOURS[2], linewidth=0.6)
    fig.tight_layout()
    return fig


def walk_coefficient(paths, times):
    """D (m^2/s) fitted by T1's estimator to every group of walkers: the
    mean over the groups and its standard error."""
    estimates = [
        diffusion_coefficient(times, mean_squared_displacement(group), 2)
        for group in np.array_split(paths, GROUPS, axis=1)
    ]
    return float(np.mean(estimates)), float(np.std(estimates, ddof=1) / np.sqrt(GROUPS))


def lattice_run(temperature, rng):
    """The vacancy's walk at the temperature: the recorded times (s), the
    paths, and the mean time tau = 1 / (4 Gamma) between hops (s)."""
    rate = float(hop_rate(ATTEMPT, MIGRATION, kt(temperature)))
    tau = 1 / (4 * rate)
    times = np.linspace(HOPS * tau / RECORDS, HOPS * tau, RECORDS)
    paths = lattice_walks(WALKERS, times, rate, SPACING, rng)
    return np.concatenate([[0.0], times]), paths, tau


def against_t1(experiment: Experiment):
    """At 1000 K: the vacancy's diffusion coefficient on the lattice, the
    coefficient of T1's walk with the same step and the same mean time
    between steps, and T1's prediction; record the table and return the
    runs for the figure."""
    rng = np.random.default_rng(20261030)
    times, lattice, tau = lattice_run(1000.0, rng)
    t1_times = tau * np.arange(HOPS + 1)
    t1 = random_walks(WALKERS, HOPS, SPACING, rng, dimension=2)
    predicted = predicted_diffusion_coefficient(SPACING, tau, 2)
    rows = []
    for name, paths, t in (
        ("vacancy on the square lattice, exponential waiting times", lattice, times),
        ("T1's walk, random directions, fixed time tau", t1, t1_times),
    ):
        d, error = walk_coefficient(paths, t)
        rows.append((name, d, error, (d - predicted) / error))
    rows.append(("T1's prediction a^2 / (2 d tau)", predicted, None, None))
    experiment.table(
        "walk",
        [
            (
                name,
                d * 1e4,
                "" if e is None else f"{e * 1e4:.2e}",
                "" if z is None else f"{z:+.1f}",
            )
            for name, d, e, z in rows
        ],
        [
            ("walk", "", ""),
            ("D", "cm^2/s", ".4e"),
            ("standard error", "cm^2/s", ""),
            ("difference from the prediction", "standard errors", ""),
        ],
        "The diffusion coefficient of 8000 walkers with steps of 0.25 nm at "
        "1000 K (migration barrier 0.7 eV, attempt frequency 10^13 /s), each "
        "fitted by T1's estimator <r^2> = 4 D t over about 200 steps, against "
        "T1's prediction; the standard error from 20 groups of walkers.",
    )
    return (times, lattice), (t1_times, t1), predicted, rows


def draw_msd(lattice, t1, predicted) -> Figure:
    """The mean squared displacement of both walks against T1's line
    4 D t."""
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    t_l, p_l = lattice
    t_w, p_w = t1
    ax.plot(
        1e9 * t_w,
        1e18 * 4 * predicted * t_w,
        color=FIGURE_COLOURS[2],
        linestyle="--",
        label="T1's prediction 4 D t, D = a^2 / (4 tau)",
    )
    ax.plot(
        1e9 * t_l,
        1e18 * mean_squared_displacement(p_l),
        "o",
        color=FIGURE_COLOURS[0],
        markerfacecolor="none",
        label="vacancy on the lattice",
    )
    ax.plot(
        1e9 * t_w[::4],
        1e18 * mean_squared_displacement(p_w)[::4],
        "s",
        color=FIGURE_COLOURS[1],
        markerfacecolor="none",
        label="T1's walk",
    )
    ax.set_xlabel("time t (ns)")
    ax.set_ylabel("mean squared displacement (nm^2)")
    ax.legend(fontsize="small", loc="upper left")
    fig.tight_layout()
    return fig


def arrhenius(experiment: Experiment):
    """The vacancy's diffusion coefficient at four temperatures and the
    migration energy from the slope of ln D against 1 / kT; record the
    table and return the coefficients, the fitted energy and its error."""
    rng = np.random.default_rng(600)
    rows, ds, errors = [], [], []
    for temperature in temperatures:
        times, paths, tau = lattice_run(temperature, rng)
        d, error = walk_coefficient(paths, times)
        predicted = predicted_diffusion_coefficient(SPACING, tau, 2)
        ds.append(d)
        errors.append(error)
        rows.append(
            (
                temperature,
                1 / (4 * tau),
                d * 1e4,
                predicted * 1e4,
                (d - predicted) / error,
            )
        )
    x = 1 / kt(temperatures)
    y = np.log(ds)
    weights = np.array(ds) / np.array(errors)  # 1 / the error of ln D
    (slope, _), covariance = np.polyfit(x, y, 1, w=weights, cov="unscaled")
    energy, energy_error = -slope, float(np.sqrt(covariance[0, 0]))
    experiment.table(
        "arrhenius",
        rows,
        [
            ("temperature", "K", ".0f"),
            ("hop rate Gamma", "1/s", ".3e"),
            ("D measured", "cm^2/s", ".4e"),
            ("D = Gamma a^2", "cm^2/s", ".4e"),
            ("difference", "standard errors", "+.1f"),
        ],
        "The vacancy's diffusion coefficient on the square lattice at four "
        "temperatures, each from 8000 walkers over about 200 hops, against "
        "T1's prediction a^2 / (2 d tau) = Gamma a^2.",
    )
    return np.array(ds), np.array(errors), energy, energy_error


def correlations(experiment: Experiment):
    """The tracer correlation factor on the lattice of SIDE x SIDE sites,
    from the growth of the atoms' squared displacements and from their
    value at the end divided by the jumps, and on smaller lattices; record
    the tables and return f and its error."""
    rng = np.random.default_rng(1949)
    atoms, _ = vacancy_exchanges(SIDE, [START, END], RUNS, rng)
    naive = atoms / np.array([[START], [END]])
    rng = np.random.default_rng(1949)
    f, error, vacancy, vacancy_error = correlation_factor(SIDE, START, END, RUNS, rng)
    experiment.table(
        "correlation",
        [
            (
                f"atoms: growth of the sum of r^2 from {START} to {END} jumps,"
                " per jump",
                f,
                error,
                SQUARE_LATTICE_CORRELATION,
            ),
            *(
                (
                    f"atoms: sum of r^2 after {jumps} jumps, per jump",
                    float(values.mean()),
                    float(values.std(ddof=1) / np.sqrt(RUNS)),
                    SQUARE_LATTICE_CORRELATION,
                )
                for jumps, values in zip((START, END), naive, strict=True)
            ),
            (f"vacancy: r^2 after {END} jumps, per jump", vacancy, vacancy_error, 1.0),
        ],
        [
            ("quantity", "", ""),
            ("measured", "a^2", ".4f"),
            ("standard error", "a^2", ".4f"),
            ("expected", "a^2", ".4f"),
        ],
        "One vacancy making 8000 jumps on a periodic square lattice of 64 x 64 "
        "sites, in 2000 runs: the squared displacements of all atoms, summed, "
        "per jump of the vacancy, against the correlation factor 1 / (pi - 1) "
        "of the square lattice, and the vacancy's own squared displacement per "
        "jump against one, its uncorrelated value.",
    )
    rows = []
    for side in sides:
        value, err, _, _ = correlation_factor(side, START, END, 1000, rng)
        rows.append((side, value, err, (value - SQUARE_LATTICE_CORRELATION) / err))
    rows.append((SIDE, f, error, (f - SQUARE_LATTICE_CORRELATION) / error))
    experiment.table(
        "finite-size",
        rows,
        [
            ("lattice side", "sites", "d"),
            ("f", "", ".4f"),
            ("standard error", "", ".4f"),
            ("difference from 1 / (pi - 1)", "standard errors", "+.1f"),
        ],
        "The correlation factor from the growth between 2000 and 8000 jumps on "
        "periodic lattices of growing side, 1000 runs each (2000 on the "
        "largest).",
    )
    return f, error, naive, rows


def draw_arrhenius(ds, errors, f) -> Figure:
    """The Arrhenius plot of the vacancy's diffusion coefficient and of the
    atoms' self-diffusion coefficient f c_v D_v."""
    t = np.linspace(550, 1250, 100)
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    vacancy_line = SPACING**2 * hop_rate(ATTEMPT, MIGRATION, kt(t))
    atoms_line = f * vacancy_fraction(FORMATION, kt(t)) * vacancy_line
    x_line, x = 1000 / t, 1000 / np.array(temperatures)
    ax.semilogy(
        x_line,
        1e4 * vacancy_line,
        color=FIGURE_COLOURS[0],
        linestyle="-",
        label="vacancy, Gamma a^2 (slope -E_m / k)",
    )
    ax.errorbar(
        x,
        1e4 * ds,
        yerr=1e4 * errors,
        fmt="o",
        color=FIGURE_COLOURS[0],
        markerfacecolor="none",
        label="vacancy, measured on the lattice (one standard error)",
    )
    ax.semilogy(
        x_line,
        1e4 * atoms_line,
        color=FIGURE_COLOURS[1],
        linestyle="--",
        label="atoms, f c_v Gamma a^2 (slope -(E_f + E_m) / k)",
    )
    ax.plot(
        x,
        1e4 * f * vacancy_fraction(FORMATION, kt(temperatures)) * ds,
        "s",
        color=FIGURE_COLOURS[1],
        markerfacecolor="none",
        label="atoms, measured f and D_v times c_v",
    )
    ax.set_xlabel("1000 / T (1/K)")
    ax.set_ylabel("diffusion coefficient D (cm^2/s, log scale)")
    ax.legend(fontsize="small", loc="lower left")
    fig.tight_layout()
    return fig


def vacancy_temperature(fraction: float) -> float:
    """Exercise 1: the temperature (K) at which the closed-form vacancy
    fraction reaches ``fraction``: E_f / (k ln((1 - c) / c))."""
    return FORMATION / (BOLTZMANN * np.log((1 - fraction) / fraction))


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()

    assert vacancies(experiment) < 1
    experiment.figure("fig-free-energy", draw_free_energy)
    experiment.number(
        "fraction-1000", float(vacancy_fraction(FORMATION, kt(1000.0))), ".1e"
    )

    lattice, t1, predicted, rows = against_t1(experiment)
    assert all(abs(z) < 3 for _, _, _, z in rows[:2])
    experiment.figure("fig-msd", partial(draw_msd, lattice, t1, predicted))

    ds, errors, energy, energy_error = arrhenius(experiment)
    assert abs(energy - MIGRATION) < 3 * energy_error
    experiment.number("migration-fit", energy, ".4f")
    experiment.number("migration-error", energy_error, ".4f")

    f, error, naive, sizes = correlations(experiment)
    assert abs(f - SQUARE_LATTICE_CORRELATION) < 3 * error
    offsets = naive.mean(axis=1) - SQUARE_LATTICE_CORRELATION
    assert offsets[0] > max(offsets[1], 3 * error)
    assert sizes[0][1] - SQUARE_LATTICE_CORRELATION > 0.05
    experiment.figure("fig-arrhenius", partial(draw_arrhenius, ds, errors, f))
    experiment.number("f-gap", (f - SQUARE_LATTICE_CORRELATION) / error, "+.1f")
    d_v = SPACING**2 * float(hop_rate(ATTEMPT, MIGRATION, kt(1000.0)))
    c_v = float(vacancy_fraction(FORMATION, kt(1000.0)))
    experiment.number("dv-1000", d_v * 1e4, ".2e")
    experiment.number("datoms-1000", f * c_v * d_v * 1e4, ".2e")
    experiment.number("slowdown-1000", 1 / (f * c_v), ".1e")

    experiment.number("t-1e-4", vacancy_temperature(1e-4), ".0f")
    experiment.number("t-1e-6", vacancy_temperature(1e-6), ".0f")
    return experiment


if __name__ == "__main__":
    main(run)
