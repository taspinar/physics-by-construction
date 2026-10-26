"""The experiment of the lesson "Heat conduction and diffusion".

Lumped (Newton) cooling against a steel slab cooled by convection on both
faces, computed with the explicit finite-difference scheme of
``pbc.thermodynamics.conduction`` and its exact series; the energy balance of
the scheme; its stability limit measured in one and two dimensions; its
convergence in the grid spacing and the time step; and a plate heated along
one edge, by the transient scheme and by the steady sparse solve. Run it as a
program to write the figures and numbers of the page:

    uv run --locked --no-dev python -m \\
        pbc.thermodynamics.experiments.heat_conduction_and_diffusion out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from scipy.optimize import brentq

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.thermodynamics.conduction import (
    Convective,
    Fixed,
    Material,
    convective_loss,
    discrete_stability_limit,
    ftcs_step,
    ftcs_step_2d,
    grid_energy,
    growth_per_step,
    lumped_temperature,
    lumped_time_constant,
    march,
    positive_step_limit,
    slab_mean_temperature,
    slab_temperature,
    stability_limit,
    steady_plate,
)
from pbc.verification.estimates import fitted_order

# region: slab
steel = Material(k=45.0, rho=7850.0, c=490.0)  # W/(m K), kg/m^3, J/(kg K)
HALF = 0.02  # m, half the thickness of the slab
START, FLUID = 200.0, 20.0  # degrees C, the slab at first and the fluid
BIOTS = [0.05, 0.5, 5.0]  # h L / k; h follows from it
CELLS = 20  # grid cells across the slab
# endregion: slab
# region: stability
INTERIOR = 20  # unknowns per direction, between fixed ends at zero
SEED = 7  # of the random starting state
POWER_STEPS = 600  # steps of the growth measurement
# endregion: stability
# region: convergence
GRID_CELLS = [10, 20, 40, 80, 160]  # across the slab, coarsest first
R_FIXED = 0.25  # alpha dt / dx^2, held while dx is refined
BIOT_CONVERGENCE, FOURIER_END = 1.0, 0.2
TIME_STEPS = [100, 200, 400, 800, 1600]  # on one grid, coarsest first
# endregion: convergence
# region: plate
SIDE = 0.1  # m, the side of the square plate
PLATE_CELLS = 40  # per side
HOT, COLD = 100.0, 20.0  # degrees C: the bottom edge, the other three
R_PLATE = 0.24  # alpha dt / dx^2, below the limit of 1/4
SNAPSHOT = 60.0  # s, the time of the transient panel
PLATE_END = 1500.0  # s, when the transient is compared with the steady plate
# endregion: plate


def below(value: float, bound: float) -> str:
    """A gap at the level of round-off or of the bisection's tolerance is not
    shown as a number: only that it is smaller than ``bound``."""
    if abs(value) >= bound:
        raise ValueError(f"{value!r} is not below {bound!r}")
    return f"below {bound:.0e}"


def convective_slab(biot: float, cells: int, fourier_end: float, r: float):
    """The slab started at START and cooled on both faces at the Biot number
    ``biot``, to the Fourier number ``fourier_end`` at about ``r``: returns the
    grid spacing, the step, the states, and the two ends."""
    alpha = steel.diffusivity
    dx = 2.0 * HALF / cells
    end = Convective(h=biot * steel.k / HALF, ambient=FLUID)
    t_end = fourier_end * HALF**2 / alpha
    steps = int(np.ceil(t_end / (r * dx**2 / alpha)))
    dt = t_end / steps
    r = alpha * dt / dx**2
    states = march(
        np.full(cells + 1, START),
        steps,
        lambda t: ftcs_step(t, r, dx, steel.k, end, end),
    )
    return dx, dt, states, (end, end)


def mean_of(states, dx: float):
    """The trapezoidal mean of each state over the slab."""
    weights = np.full(states.shape[-1], dx)
    weights[[0, -1]] = 0.5 * dx
    return states @ weights / (2.0 * HALF)


def lumped_against_slab(experiment: Experiment) -> dict:
    """The mean temperature of the slab by the scheme, its exact series, and
    the lumped model, for each Biot number, to three lumped time constants;
    record the table and return the curves by Biot number."""
    curves, rows = {}, []
    for biot in BIOTS:
        h = biot * steel.k / HALF
        tau = lumped_time_constant(steel, HALF, h)
        fourier_end = 3.0 / biot  # t / tau = Bi Fo
        dx = 2.0 * HALF / CELLS
        r = 0.9 * positive_step_limit(dx, steel.k, (Convective(h, FLUID),))
        dx, dt, states, _ = convective_slab(biot, CELLS, fourier_end, r)
        t = dt * np.arange(len(states))
        scheme = (mean_of(states, dx) - FLUID) / (START - FLUID)
        lumped = (lumped_temperature(t, START, FLUID, tau) - FLUID) / (START - FLUID)
        exact = slab_mean_temperature(steel.diffusivity * t[1:] / HALF**2, biot)
        curves[biot] = (t / tau, scheme, lumped)
        rows.append(
            (
                biot,
                h,
                tau,
                np.max(np.abs(scheme - lumped)),
                np.max(np.abs(scheme[1:] - exact)),
            )
        )
    experiment.table(
        "lumped-against-slab",
        rows,
        [
            ("Biot number", "", ".2f"),
            ("h", "W/(m^2 K)", ".1f"),
            ("lumped time constant", "s", ".1f"),
            ("largest gap, scheme to lumped", "", ".4f"),
            ("largest gap, scheme to exact series", "", ".4f"),
        ],
        "The mean dimensionless temperature (T - T_fluid) / (T_0 - T_fluid) of "
        "the steel slab by the explicit scheme, against the lumped model and "
        "against the exact series, as the largest gap over three lumped time "
        "constants.",
    )
    experiment.number("lumped-gap-small", rows[0][3], ".3f")
    experiment.number("lumped-gap-large", rows[-1][3], ".2f")
    experiment.number("series-gap", max(row[4] for row in rows), ".4f")
    return curves


def energy_balance(experiment: Experiment) -> float:
    """The energy the slab's grid loses against the heat that leaves through
    its faces, at the middle Biot number; return the relative gap."""
    dx, dt, states, ends = convective_slab(BIOTS[1], CELLS, 1.0, 0.4)
    lost = grid_energy(states[0], dx, steel) - grid_energy(states[-1], dx, steel)
    out = convective_loss(states[:-1], dt, ends)
    experiment.table(
        "energy-balance",
        [(lost, out)],
        [
            ("energy lost by the slab", "J/m^2", ".1f"),
            ("heat out through the faces", "J/m^2", ".1f"),
        ],
        "The energy the slab loses up to the Fourier number one, per square "
        "metre of face, against the convective heat summed over the steps.",
    )
    return abs(lost - out) / out


def random_state(dimension: int):
    """A random state with zeros on the fixed boundary."""
    rng = np.random.default_rng(SEED)
    shape = (INTERIOR + 2,) * dimension
    state = np.zeros(shape)
    inner = (slice(1, -1),) * dimension
    state[inner] = rng.standard_normal((INTERIOR,) * dimension)
    return state


def growth(dimension: int):
    """The measured growth per step of the scheme as a function of r."""
    state = random_state(dimension)
    zero = Fixed(0.0)
    if dimension == 1:
        return lambda r: growth_per_step(
            lambda t: ftcs_step(t, r, 1.0, 1.0, zero, zero), state, POWER_STEPS
        )
    return lambda r: growth_per_step(lambda t: ftcs_step_2d(t, r), state, POWER_STEPS)


def stability(experiment: Experiment) -> list:
    """The stability limit of the explicit scheme measured by bisection on
    its growth, in one and two dimensions; record the table and return the
    measured limits."""
    rows, limits = [], []
    for dimension in (1, 2):
        continuum = 1.0 / (2 * dimension)
        found = stability_limit(
            growth(dimension), 0.6 * continuum, 1.4 * continuum, 1e-6
        )
        exact = discrete_stability_limit(INTERIOR, dimension)
        limits.append(found)
        rows.append((dimension, found, exact, continuum, below(found - exact, 1e-6)))
    experiment.table(
        "stability",
        rows,
        [
            ("dimensions", "", "d"),
            ("measured limit of r", "", ".5f"),
            ("limit of the grid", "", ".5f"),
            ("limit of a fine grid, 1/(2d)", "", ".5f"),
            ("measured minus grid limit", "", ""),
        ],
        "The largest stable r = alpha dt / dx^2 of the explicit scheme, found by "
        "bisection on the measured growth per step of a random state, against "
        "the exact limit of a grid of twenty unknowns per direction and its "
        "fine-grid value.",
    )
    return limits


def grid_convergence(experiment: Experiment):
    """The error of the convective slab against its exact series as the grid
    is refined at fixed r; record the table and the fitted order, and return
    the spacings and errors."""
    spacings, errs = [], []
    for cells in GRID_CELLS:
        dx, _, states, _ = convective_slab(
            BIOT_CONVERGENCE, cells, FOURIER_END, R_FIXED
        )
        x = np.linspace(-1.0, 1.0, cells + 1)
        exact = FLUID + (START - FLUID) * slab_temperature(
            x, FOURIER_END, BIOT_CONVERGENCE
        )
        spacings.append(dx)
        errs.append(np.max(np.abs(states[-1] - exact)))
    experiment.table(
        "grid-convergence",
        [(c, 1e3 * dx, e) for c, dx, e in zip(GRID_CELLS, spacings, errs, strict=True)],
        [
            ("cells", "", "d"),
            ("dx", "mm", ".3f"),
            ("largest error", "degrees C", ".2e"),
        ],
        "The largest error of the slab temperature against the exact series at "
        "the Fourier number 0.2 and the Biot number one, as the grid is refined "
        "with r held near 0.25.",
    )
    experiment.number("grid-order", fitted_order(spacings, errs), ".2f")
    return spacings, errs


def time_convergence(experiment: Experiment):
    """The error of one sine mode against the exact solution of the grid's
    ordinary differential equations, as the time step is halved on a fixed
    grid; record the table and return the steps and errors."""
    alpha, length, cells = steel.diffusivity, 2.0 * HALF, CELLS
    dx = length / cells
    x = np.linspace(0.0, length, cells + 1)
    rate = 4.0 * alpha / dx**2 * np.sin(np.pi * dx / (2.0 * length)) ** 2
    t_end = 0.1 * length**2 / alpha
    zero = Fixed(0.0)
    steps_dt, errs, rows = [], [], []
    for steps in TIME_STEPS:
        dt = t_end / steps
        r = alpha * dt / dx**2
        final = march(
            np.sin(np.pi * x / length),
            steps,
            lambda t, r=r: ftcs_step(t, r, dx, 1.0, zero, zero),
        )[-1]
        error = np.max(
            np.abs(final - np.sin(np.pi * x / length) * np.exp(-rate * t_end))
        )
        steps_dt.append(dt)
        errs.append(error)
        rows.append((steps, dt, r, error))
    experiment.table(
        "time-convergence",
        rows,
        [
            ("steps", "", "d"),
            ("dt", "s", ".4f"),
            ("r", "", ".3f"),
            ("largest error", "", ".2e"),
        ],
        "The largest error of a sine mode of unit amplitude after the same time, "
        "against the exact solution of the grid's ordinary differential "
        "equations, so that only the error of the time step remains, as the "
        "step is halved on a grid of twenty cells.",
    )
    experiment.number("time-order", fitted_order(steps_dt, errs), ".2f")
    return steps_dt, errs


def plate():
    """The plate heated along its bottom edge: the boundary grid, the step,
    the transient state at SNAPSHOT and at PLATE_END, and the steady plate."""
    n = PLATE_CELLS
    dx = SIDE / n
    boundary = np.full((n + 1, n + 1), COLD)
    boundary[0, :] = HOT
    dt = R_PLATE * dx**2 / steel.diffusivity
    steady = steady_plate(boundary, np.zeros_like(boundary), dx, steel.k)
    start = boundary.copy()
    start[1:-1, 1:-1] = COLD
    snapshot_steps = round(SNAPSHOT / dt)
    states = march(start, round(PLATE_END / dt), lambda t: ftcs_step_2d(t, R_PLATE))
    return dt, states[snapshot_steps], states[-1], steady


def draw_lumped_against_slab(curves: dict) -> Figure:
    """The mean temperature of the slab against time in lumped time
    constants, scheme and lumped model, for the three Biot numbers."""
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    styles = ["-", "--", "-."]
    for (biot, (t, scheme, _)), line, colour in zip(
        curves.items(),
        styles,
        (FIGURE_COLOURS[0], FIGURE_COLOURS[1], FIGURE_COLOURS[4]),
        strict=True,
    ):
        ax.plot(t, scheme, color=colour, linestyle=line, label=f"slab, Bi = {biot:g}")
    t, _, lumped = curves[BIOTS[0]]
    ax.plot(
        t,
        lumped,
        color=FIGURE_COLOURS[2],
        linestyle=":",
        linewidth=2.2,
        label="lumped model",
    )
    ax.set_xlabel("time / lumped time constant")
    ax.set_ylabel("mean temperature, dimensionless")
    ax.set_xlim(0, 3)
    ax.set_ylim(0, 1)
    ax.legend(frameon=False)
    fig.tight_layout()
    return fig


def draw_stability() -> Figure:
    """The measured growth per step against r, in one and two dimensions,
    with the limits of the grid marked."""
    r = np.linspace(0.05, 0.65, 61)
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    for dimension, line, marker, colour in (
        (1, "-", "o", FIGURE_COLOURS[0]),
        (2, "--", "s", FIGURE_COLOURS[1]),
    ):
        g = growth(dimension)
        ax.plot(
            r,
            [g(value) for value in r],
            color=colour,
            linestyle=line,
            marker=marker,
            markersize=3,
            label=f"{dimension}D",
        )
        ax.axvline(
            discrete_stability_limit(INTERIOR, dimension),
            color=colour,
            linestyle=":",
            label=f"limit of the grid, {dimension}D",
        )
    ax.axhline(1.0, color=FIGURE_COLOURS[2], linewidth=0.8)
    ax.set_ylim(0.0, 4.5)
    ax.set_xlabel(r"$r = \alpha\,\Delta t / \Delta x^2$ (dimensionless)")
    ax.set_ylabel("growth per step (dimensionless)")
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    return fig


def draw_convergence(grid, time) -> Figure:
    """Log-log errors against dx and against dt, with reference slopes."""
    fig, (left, right) = plt.subplots(1, 2, figsize=(7.2, 3.4))
    for ax, (steps, errs), slope, label, unit in (
        (left, grid, 2, "dx (mm)", 1e3),
        (right, time, 1, "dt (s)", 1.0),
    ):
        h = np.array(steps) * unit
        e = np.array(errs)
        ax.loglog(h, e, color=FIGURE_COLOURS[0], marker="o", label="measured")
        ax.loglog(
            h,
            0.5 * e[0] * (h / h[0]) ** slope,
            color=FIGURE_COLOURS[2],
            linestyle=":",
            label=f"reference, slope {'two' if slope == 2 else 'one'}",
        )
        ax.set_xticks(h, labels=[f"{value:.3g}" for value in h])
        ax.minorticks_off()
        ax.set_xlabel(label)
        ax.legend(frameon=False, loc="upper left")
    left.set_ylabel("largest error (degrees C)")
    right.set_ylabel("largest error (dimensionless)")
    fig.tight_layout()
    return fig


def draw_plate(snapshot, steady) -> Figure:
    """The plate's temperature at SNAPSHOT and in the steady state, false
    colour on one scale."""
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4), sharey=True)
    extent = (0.0, 100 * SIDE, 0.0, 100 * SIDE)
    for ax, field, title in (
        (axes[0], snapshot, f"after {SNAPSHOT:.0f} s"),
        (axes[1], steady, "steady state"),
    ):
        image = ax.imshow(
            field, origin="lower", extent=extent, cmap="viridis", vmin=COLD, vmax=HOT
        )
        lines = ax.contour(
            field,
            levels=[30, 40, 60, 80],
            origin="lower",
            extent=extent,
            colors="white",
            linewidths=0.7,
        )
        ax.clabel(lines, fmt="%d °C", fontsize="x-small")
        ax.set_title(title, fontsize="medium")
        ax.set_xlabel("x (cm)")
    axes[0].set_ylabel("y (cm)")
    fig.colorbar(image, ax=axes, label="temperature (°C) (false colour)")
    return fig


def largest_step(experiment: Experiment) -> None:
    """Exercise 1: the largest time step of the slab's grid at the largest
    Biot number, from the positivity limit of r; record the table."""
    dx = 2.0 * HALF / CELLS
    h = BIOTS[-1] * steel.k / HALF
    r_max = positive_step_limit(dx, steel.k, (Convective(h, FLUID),))
    experiment.table(
        "largest-step",
        [(1e3 * dx, h * dx / steel.k, r_max, r_max * dx**2 / steel.diffusivity)],
        [
            ("dx", "mm", ".1f"),
            ("h dx / k", "", ".3f"),
            ("largest r", "", ".4f"),
            ("largest dt", "s", ".3f"),
        ],
        "The largest step that keeps every new value of the slab a weighted mean "
        "of old values, at the largest Biot number of the lesson.",
    )


def cooling_time(experiment: Experiment) -> None:
    """Exercise 2: the time a thin steel sheet takes to cool from START to
    50 degrees C, lumped and from the exact series; record the table."""
    half, h, target = 0.001, 25.0, 50.0  # m, W/(m^2 K), degrees C
    biot = h * half / steel.k
    tau = lumped_time_constant(steel, half, h)
    theta = (target - FLUID) / (START - FLUID)
    lumped = tau * np.log(1.0 / theta)
    fourier = brentq(lambda fo: slab_mean_temperature(fo, biot) - theta, 1e-3, 1e5)
    exact = fourier * half**2 / steel.diffusivity
    experiment.table(
        "cooling-time",
        [(biot, tau, lumped, exact)],
        [
            ("Biot number", "", ".2e"),
            ("lumped time constant", "s", ".1f"),
            ("lumped time to 50 degrees C", "s", ".1f"),
            ("exact time to a mean of 50 degrees C", "s", ".1f"),
        ],
        "A steel sheet two millimetres thick in still air, cooled from 200 to "
        "50 degrees C: the lumped estimate against the exact series.",
    )


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    curves = lumped_against_slab(experiment)
    experiment.figure(
        "fig-lumped-against-slab", partial(draw_lumped_against_slab, curves)
    )
    experiment.number("energy-gap", below(energy_balance(experiment), 1e-12))
    limits = stability(experiment)
    experiment.number("limit-1d", limits[0], ".4f")
    experiment.number("limit-2d", limits[1], ".4f")
    experiment.figure("fig-stability-limit", draw_stability)
    grid = grid_convergence(experiment)
    time = time_convergence(experiment)
    experiment.figure("fig-heat-convergence", partial(draw_convergence, grid, time))
    dt, snapshot, final, steady = plate()
    experiment.number("plate-step", dt, ".3f")
    experiment.number("plate-gap", below(float(np.max(np.abs(final - steady))), 1e-9))
    experiment.figure("fig-plate-temperature", partial(draw_plate, snapshot, steady))
    largest_step(experiment)
    cooling_time(experiment)
    return experiment


if __name__ == "__main__":
    main(run)
