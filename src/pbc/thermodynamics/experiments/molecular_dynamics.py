"""The experiment of the lesson "Molecular dynamics".

Lennard-Jones particles in a periodic square box, integrated with velocity
Verlet (``pbc.thermodynamics.molecular``): the conservation of the energy and
how its error scales with the time step, the relaxation of a mixture of light
and heavy particles started at different temperatures to one temperature
(equipartition), and the pressure from the virial. Run it as a program to
write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.thermodynamics.experiments.molecular_dynamics out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.ticker import NullFormatter, NullLocator

from pbc.abm.gas import mean_and_error
from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.thermodynamics.molecular import (
    initial_velocities,
    shifted_force,
    square_lattice,
    velocity_verlet,
    virial_pressure,
)
from pbc.verification.estimates import fitted_order

# region: system
PER_SIDE = 6
N = PER_SIDE**2
DENSITY = 0.4  # particles per sigma^2
BOX = float(np.sqrt(N / DENSITY))
LIGHT_MASS, HEAVY_MASS = 1.0, 4.0
# endregion: system
# region: energy
time_steps = [0.01, 0.005, 0.0025]  # coarsest first
ENERGY_DURATION = 20.0
# endregion: energy
# region: mixture
LIGHT_START, HEAVY_START = 2.0, 0.1  # temperatures at the start
DT = 0.005
DURATION = 20.0
SETTLED = 5.0  # averages are taken after this time
SEEDS = range(12)
EVERY = 10
# endregion: mixture

# The three time steps of a figure: line style, colour, and marker.
STEP_STYLES = [
    ("-", FIGURE_COLOURS[1], "o"),
    ("--", FIGURE_COLOURS[0], "s"),
    (":", FIGURE_COLOURS[4], "^"),
]


def masses() -> np.ndarray:
    """Light and heavy particles in a checkerboard on the starting lattice."""
    i = np.arange(N)
    return np.where((i + i // PER_SIDE) % 2 == 0, LIGHT_MASS, HEAVY_MASS)


def groups() -> tuple[np.ndarray, np.ndarray]:
    """The indices of the light and of the heavy particles."""
    m = masses()
    return np.flatnonzero(m == LIGHT_MASS), np.flatnonzero(m == HEAVY_MASS)


def potential_table(experiment: Experiment) -> None:
    """The shifted-force potential at a few distances; record the table."""
    distances = [0.95, 2.0 ** (1.0 / 6.0), 1.5, 2.0, 2.5]
    experiment.table(
        "potential",
        [(r, float(shifted_force(np.array([r]))[0])) for r in distances],
        [("distance", "sigma", ".4f"), ("shifted-force potential", "epsilon", ".4f")],
        "The shifted-force Lennard-Jones potential at five distances: repulsive "
        "inside sigma, deepest near the minimum of the full potential at 2^(1/6) "
        "sigma, and zero at the cut-off.",
    )


def settled_state():
    """The state after a short run from the lattice at temperature one, the
    start of the runs of the energy check."""
    m = masses()
    v = initial_velocities(m, np.full(N, 1.0), np.random.default_rng(10))
    run = velocity_verlet(square_lattice(PER_SIDE, BOX), v, m, BOX, DT, 1000, 1000)
    return run.positions, run.velocities


def energy_runs():
    """One run of ``ENERGY_DURATION`` from the settled state for each time
    step; the trajectories, coarsest step first."""
    x, v = settled_state()
    return [
        velocity_verlet(x, v, masses(), BOX, dt, round(ENERGY_DURATION / dt))
        for dt in time_steps
    ]


def energy_check(experiment: Experiment, runs) -> tuple[list, float]:
    """The fluctuation and the drift of the total energy per particle for each
    time step; record the table and return the fluctuations and the largest
    ratio of drift to fluctuation."""
    rows, fluctuations, ratios = [], [], []
    for dt, run in zip(time_steps, runs, strict=True):
        e = run.energy / N
        fluctuation = float(np.sqrt(np.mean((e - e.mean()) ** 2)))
        slope = np.polyfit(run.times, e, 1)[0]
        drift = abs(slope) * ENERGY_DURATION
        fluctuations.append(fluctuation)
        ratios.append(drift / fluctuation)
        rows.append((dt, fluctuation, drift, drift / fluctuation))
    experiment.table(
        "energy-check",
        rows,
        [
            ("time step", "", ".4f"),
            ("fluctuation of the energy per particle", "epsilon", ".2e"),
            ("drift over the run", "epsilon", ".1e"),
            ("drift / fluctuation", "", ".2f"),
        ],
        "The root-mean-square fluctuation of the total energy per particle about "
        "its mean, and its drift (the slope of a straight line fitted to it, "
        "times the duration of the run), for three time steps from the same "
        "start, in reduced units.",
    )
    return fluctuations, max(ratios)


def draw_energy_drift(runs, fluctuations) -> Figure:
    """Left: the change of the total energy per particle against the time,
    for the three time steps. Right: its fluctuation against the time step,
    log-log, with a reference line of slope two."""
    fig, (left, right) = plt.subplots(
        1, 2, figsize=(7.2, 3.4), gridspec_kw={"width_ratios": [1.8, 1.0]}
    )
    for (line, colour, marker), dt, run in zip(
        STEP_STYLES, time_steps, runs, strict=True
    ):
        left.plot(
            run.times,
            (run.energy - run.energy[0]) / N,
            color=colour,
            linestyle=line,
            linewidth=0.8,
            label=f"step {dt:g}",
        )
        right.loglog(
            dt,
            fluctuations[time_steps.index(dt)],
            color=colour,
            marker=marker,
            linestyle="none",
        )
    left.set_xlabel(r"time ($\sigma\sqrt{m/\epsilon}$)")
    left.set_ylabel(r"$(E(t) - E(0))/N$ ($\epsilon$)")
    left.legend(frameon=False, loc="lower left", ncols=3, fontsize="small")
    steps = np.array([time_steps[-1], time_steps[0]])
    reference = fluctuations[-1] * (steps / time_steps[-1]) ** 2
    right.loglog(
        steps,
        reference,
        color=FIGURE_COLOURS[2],
        linestyle=":",
        label="slope 2 (reference)",
    )
    right.set_xticks(time_steps, labels=[f"{dt:g}" for dt in time_steps])
    right.xaxis.set_minor_locator(NullLocator())
    right.yaxis.set_minor_formatter(NullFormatter())
    right.set_xlabel("time step (reduced units)")
    right.set_ylabel(r"fluctuation of $E/N$ ($\epsilon$)")
    right.legend(frameon=False, loc="upper left", fontsize="small")
    fig.tight_layout()
    return fig


def mixture_runs():
    """The runs of the mixture, light particles started hot and heavy ones
    nearly at rest, one per seed."""
    m = masses()
    start = np.where(m == LIGHT_MASS, LIGHT_START, HEAVY_START)
    lattice = square_lattice(PER_SIDE, BOX)
    steps = round(DURATION / DT)
    return [
        velocity_verlet(
            lattice,
            initial_velocities(m, start, np.random.default_rng(seed)),
            m,
            BOX,
            DT,
            steps,
            EVERY,
            groups(),
        )
        for seed in SEEDS
    ]


def equipartition_check(experiment: Experiment, runs) -> tuple[float, float]:
    """The time-averaged temperatures of the light and the heavy particles,
    per component, after ``SETTLED``, over the runs; record the table and
    return the differences light - heavy and x - y in standard errors."""
    settled = [run.temperatures[run.times >= SETTLED].mean(axis=0) for run in runs]
    t = np.array(settled)  # runs, groups (light, heavy), components (x, y)
    rows = []
    for name, values in (
        ("light, x", t[:, 0, 0]),
        ("light, y", t[:, 0, 1]),
        ("heavy, x", t[:, 1, 0]),
        ("heavy, y", t[:, 1, 1]),
    ):
        rows.append((name, *mean_and_error(values)))
    species_mean, species_error = mean_and_error(
        t[:, 0].mean(axis=1) - t[:, 1].mean(axis=1)
    )
    axes_mean, axes_error = mean_and_error(
        t[:, :, 0].mean(axis=1) - t[:, :, 1].mean(axis=1)
    )
    rows.append(("light - heavy", species_mean, species_error))
    rows.append(("x - y", axes_mean, axes_error))
    experiment.table(
        "equipartition",
        rows,
        [
            ("particles, component", "", ""),
            ("mean temperature", "epsilon/k_B", ".3f"),
            ("standard error", "epsilon/k_B", ".3f"),
        ],
        "The kinetic temperature of each species in each direction, averaged "
        "over time after the mixture has settled and then over twelve "
        "independent runs, and the differences between the species and between "
        "the directions.",
    )
    return abs(species_mean) / species_error, abs(axes_mean) / axes_error


def draw_equipartition(runs) -> Figure:
    """The temperatures of the light and the heavy particles against the
    time, averaged over the runs."""
    times = runs[0].times
    t = np.mean([run.temperatures.mean(axis=2) for run in runs], axis=0)
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.plot(
        times,
        t[:, 0],
        color=FIGURE_COLOURS[1],
        label=f"light particles (mass {LIGHT_MASS:g})",
    )
    ax.plot(
        times,
        t[:, 1],
        color=FIGURE_COLOURS[0],
        linestyle="--",
        label=f"heavy particles (mass {HEAVY_MASS:g})",
    )
    ax.axvline(SETTLED, color=FIGURE_COLOURS[2], linestyle=":", linewidth=1.0)
    ax.annotate(
        "averages from here",
        (SETTLED, 0.05),
        xycoords=("data", "axes fraction"),
        xytext=(4, 0),
        textcoords="offset points",
        color=FIGURE_COLOURS[2],
    )
    ax.set_xlabel(r"time ($\sigma\sqrt{m/\epsilon}$)")
    ax.set_ylabel(r"kinetic temperature ($\epsilon/k_B$)")
    ax.legend(frameon=False, loc="upper right")
    return fig


def pressure_table(experiment: Experiment, runs) -> None:
    """The temperature, the potential energy per particle, and the pressure
    from the virial of the settled mixture, against the ideal gas at the same
    density and temperature; record the table."""
    temps, potentials, pressures, ideal = [], [], [], []
    for run in runs:
        late = run.times >= SETTLED
        t = float(run.temperatures[late].mean())
        temps.append(t)
        potentials.append(float(run.potential[late].mean()) / N)
        pressures.append(virial_pressure(N, t, float(run.virial[late].mean()), BOX))
        ideal.append(DENSITY * t)
    experiment.table(
        "observables",
        [
            (name, *mean_and_error(np.array(values)))
            for name, values in (
                ("temperature", temps),
                ("potential energy per particle", potentials),
                ("pressure from the virial", pressures),
                ("pressure of an ideal gas, rho k_B T", ideal),
            )
        ],
        [
            ("quantity", "", ""),
            ("mean", "reduced units", ".3f"),
            ("standard error", "reduced units", ".3f"),
        ],
        "Thermodynamic observables of the settled mixture, averaged over time and "
        "then over the twelve runs, in reduced units (temperature in epsilon/k_B, "
        "energy in epsilon, pressure in epsilon/sigma^2).",
    )


def larger_steps(experiment: Experiment) -> None:
    """Exercise 1: the largest change of the energy per particle for larger
    time steps; record the table."""
    x, v = settled_state()
    rows = []
    for dt in (0.01, 0.02, 0.03, 0.04):
        run = velocity_verlet(x, v, masses(), BOX, dt, round(10.0 / dt))
        e = run.energy / N
        change = float(np.abs(e - e[0]).max())
        rows.append((dt, f"{change:.3f}" if change < 1.0 else "above 1: the run fails"))
    experiment.table(
        "larger-steps",
        rows,
        [
            ("time step", "", ".2f"),
            ("largest change of the energy per particle", "epsilon", ""),
        ],
        "The largest change of the total energy per particle during a run of ten "
        "time units from the same start, for four time steps.",
    )


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    potential_table(experiment)
    runs = energy_runs()
    fluctuations, drift_ratio = energy_check(experiment, runs)
    experiment.number("energy-order", fitted_order(time_steps, fluctuations), ".2f")
    experiment.number("drift-ratio", drift_ratio, ".2f")
    experiment.figure(
        "fig-energy-drift", partial(draw_energy_drift, runs, fluctuations)
    )
    mixture = mixture_runs()
    experiment.figure("fig-equipartition", partial(draw_equipartition, mixture))
    species, axes = equipartition_check(experiment, mixture)
    experiment.number("species-distance", species, ".1f")
    experiment.number("axes-distance", axes, ".1f")
    pressure_table(experiment, mixture)
    larger_steps(experiment)
    return experiment


if __name__ == "__main__":
    main(run)
