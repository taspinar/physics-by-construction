"""The experiment of the lesson "The Schrödinger equation".

A free Gaussian wave packet evolved by Crank-Nicolson
(``pbc.quantum.schrodinger``) against its exact evolution: the norm, the
centre and the width, the convergence of the whole wave function, the
frequency of each mode of the grid against the free-particle dispersion, and
explicit Euler as the scheme that does not keep the norm. Run it as a
program to write the figures and numbers of the page:

    uv run --locked --no-dev python -m pbc.quantum.experiments.schrodinger_equation out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.ticker import NullFormatter

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.quantum.schrodinger import (
    Line,
    box_mode,
    box_wavenumber,
    crank_nicolson,
    crank_nicolson_frequency,
    euler_norm,
    explicit_euler,
    free_energy,
    free_packet,
    free_spread,
    gaussian_packet,
    grid_energy,
    line,
    mean_momentum,
    mean_position,
    measured_frequency,
    norm,
    spread,
)
from pbc.verification.estimates import convergence_table, fitted_order

# region: setup
# Units: hbar = m = 1, so a wavenumber k has the energy k^2 / 2.
CENTRE = -10.0  # x0, the starting centre of the packet
WIDTH = 1.0  # sigma, the starting spread of the position
WAVENUMBER = 2.0  # k0, the mean wavenumber
LEFT, RIGHT = -30.0, 40.0  # the walls
# endregion: setup

# region: packet
cells = 1400  # h = 0.05
dt = 0.01
end_time = 6.0
snapshots = 4  # records after the start, equally spaced
# endregion: packet

# region: convergence
cell_counts = [350, 700, 1400, 2800, 5600]  # h from 0.2 to 0.0125
step_ratio = 0.2  # dt = 0.2 h
# endregion: convergence

# region: dispersion
modes = [22, 45, 111, 223, 446, 891]  # k = j pi / 70, from about 1 to 40
# endregion: dispersion

# region: euler
euler_cells = 700  # h = 0.1
euler_dt = 0.002
euler_steps = [0, 100, 200, 300]
# endregion: euler

PACKET = {"centre": CENTRE, "width": WIDTH, "wavenumber": WAVENUMBER}
NORM_BOUND = 1e-12


def below(value: float, bound: float) -> str:
    """A change set by round-off is not shown as a number: only that it is
    smaller than ``bound``."""
    if abs(value) >= bound:
        raise ValueError(f"{value!r} is not below {bound!r}")
    return f"below {bound:.0e}"


def free_line(n_cells: int) -> Line:
    return line(LEFT, RIGHT, n_cells)


def evolve(grid: Line, step: float, until: float, records: int = 1):
    """The packet evolved by Crank-Nicolson with no potential."""
    n_steps = round(until / step)
    return crank_nicolson(
        gaussian_packet(grid.x, **PACKET),
        np.zeros_like(grid.x),
        h=grid.h,
        dt=step,
        n_steps=n_steps,
        every=n_steps // records,
    )


def packet_run(experiment: Experiment):
    """The packet at five times against the exact free packet: the norm, the
    centre, the width, and the largest error; record the table."""
    grid = free_line(cells)
    run = evolve(grid, dt, end_time, snapshots)
    exact = [free_packet(grid.x, t, **PACKET) for t in run.t]
    drift = float(np.max(np.abs(norm(run.psi, grid.h) - norm(run.psi[0], grid.h))))
    rows = []
    for t, psi, e in zip(run.t, run.psi, exact, strict=True):
        rows.append(
            (
                t,
                mean_position(grid.x, psi, grid.h),
                CENTRE + WAVENUMBER * t,
                spread(grid.x, psi, grid.h),
                float(free_spread(t, width=WIDTH)),
                float(np.max(np.abs(psi - e))),
            )
        )
    assert drift < NORM_BOUND, "Crank-Nicolson lost the norm"
    assert all(abs(r[1] - r[2]) < 0.05 and abs(r[3] - r[4]) < 0.05 for r in rows)

    experiment.table(
        "packet",
        rows,
        [
            ("time", "", ".1f"),
            ("centre", "", ".4f"),
            ("exact centre", "", ".4f"),
            ("width", "", ".4f"),
            ("exact width", "", ".4f"),
            ("largest error of psi", "", ".4f"),
        ],
        "The centre and the width of the computed packet against the exact free "
        "packet, and the largest difference of the wave functions, in the units of "
        "the lesson.",
    )
    return grid, run, exact, drift, rows


def draw_packet(grid: Line, run, exact) -> Figure:
    """The probability density at five times, computed and exact."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    for j, (t, psi, e) in enumerate(zip(run.t, run.psi, exact, strict=True)):
        ax.plot(
            grid.x,
            np.abs(psi) ** 2,
            color=FIGURE_COLOURS[0],
            label="Crank-Nicolson" if j == 0 else None,
        )
        ax.plot(
            grid.x,
            np.abs(e) ** 2,
            color=FIGURE_COLOURS[1],
            linestyle="--",
            linewidth=1,
            label="exact" if j == 0 else None,
        )
        peak = np.argmax(np.abs(psi))
        ax.annotate(
            f"t = {t:g}",
            (grid.x[peak], np.abs(psi[peak]) ** 2),
            textcoords="offset points",
            xytext=(0, 4),
            ha="center",
            color=FIGURE_COLOURS[2],
        )
    ax.set_xlim(-20, 25)
    ax.set_ylim(0, 0.46)
    ax.set_xlabel("position x (units with hbar = m = 1)")
    ax.set_ylabel(r"probability density $|\psi|^2$")
    ax.legend(loc="upper right")
    return fig


def convergence(experiment: Experiment):
    """The largest error of the wave function at the end time as h and dt are
    halved together; record the table."""
    spacings, errors = [], []
    for n_cells in cell_counts:
        grid = free_line(n_cells)
        run = evolve(grid, step_ratio * grid.h, end_time)
        exact = free_packet(grid.x, run.t[-1], **PACKET)
        spacings.append(grid.h)
        errors.append(float(np.max(np.abs(run.psi[-1] - exact))))
    order = fitted_order(spacings, errors)
    assert abs(order - 2.0) < 0.05

    experiment.table(
        "convergence",
        [(h, step_ratio * h, e, p) for h, e, p in convergence_table(spacings, errors)],
        [
            ("spacing h", "", ".4f"),
            ("time step", "", ".4f"),
            ("largest error of psi", "", ".2e"),
            ("observed order", "", ".2f"),
        ],
        "The largest difference between the computed and the exact wave function "
        "at the end time, with h and the time step halved together.",
    )
    return spacings, errors, order


def draw_convergence(spacings, errors) -> Figure:
    """The error against the spacing on log-log axes, with a line of slope
    two drawn below the points for comparison."""
    h = np.array(spacings)
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.loglog(
        h,
        errors,
        "o",
        color=FIGURE_COLOURS[0],
        markerfacecolor="none",
        label="Crank-Nicolson",
    )
    ax.loglog(
        h,
        0.5 * errors[-1] * (h / h[-1]) ** 2,
        color=FIGURE_COLOURS[2],
        linestyle=":",
        label="slope two",
    )
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xticks(h, [f"{v:g}" for v in h])
    ax.set_xlabel("spacing h, with time step 0.2 h (units with hbar = m = 1)")
    ax.set_ylabel(r"largest error of $\psi$")
    ax.legend()
    return fig


def dispersion_run(experiment: Experiment):
    """One Crank-Nicolson step of each sine mode of the grid: its measured
    frequency against the scheme's closed form and the free dispersion;
    record the table."""
    grid = free_line(cells)
    rows = []
    for j in modes:
        mode = box_mode(grid, j)
        k = box_wavenumber(grid, j)
        run = crank_nicolson(mode, np.zeros_like(grid.x), h=grid.h, dt=dt, n_steps=1)
        rows.append(
            (
                k,
                k * grid.h,
                float(free_energy(k)),
                float(grid_energy(k, grid.h)),
                float(crank_nicolson_frequency(grid_energy(k, grid.h), dt)),
                measured_frequency(run, mode),
            )
        )
    assert all(abs(r[5] / r[4] - 1) < 1e-9 for r in rows)

    experiment.table(
        "dispersion",
        rows,
        [
            ("wavenumber k", "", ".3f"),
            ("k h", "", ".3f"),
            ("free-particle energy", "", ".4f"),
            ("grid energy", "", ".4f"),
            ("scheme frequency, predicted", "", ".4f"),
            ("scheme frequency, measured", "", ".4f"),
        ],
        "The angular frequency of each sine mode of the grid: the free-particle "
        "dispersion, the energy of the mode on the grid, and the frequency of "
        "Crank-Nicolson predicted and measured over one time step of the example.",
    )
    return grid, rows


def draw_dispersion(grid: Line, rows) -> Figure:
    """omega against k: free, grid, and scheme, with the measured modes."""
    k = np.linspace(0, np.pi / grid.h, 400)
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.plot(
        k,
        free_energy(k),
        color=FIGURE_COLOURS[2],
        linestyle=":",
        label=r"free, $k^2/2$",
    )
    ax.plot(
        k,
        grid_energy(k, grid.h),
        color=FIGURE_COLOURS[0],
        linestyle="--",
        label="grid energy",
    )
    ax.plot(
        k,
        crank_nicolson_frequency(grid_energy(k, grid.h), dt),
        color=FIGURE_COLOURS[1],
        label="Crank-Nicolson",
    )
    ax.plot(
        [r[0] for r in rows],
        [r[5] for r in rows],
        "o",
        color=FIGURE_COLOURS[1],
        markerfacecolor="none",
        label="measured modes",
    )
    ax.set_ylim(0, 1.2 * grid_energy(np.pi / grid.h, grid.h))
    ax.set_xlabel("wavenumber k (units with hbar = m = 1)")
    ax.set_ylabel(r"angular frequency $\omega$")
    ax.legend()
    return fig


def euler_run(experiment: Experiment):
    """Explicit Euler on the packet: the norm it reaches after each number of
    steps, against the norm its spectrum predicts; record the table."""
    grid = free_line(euler_cells)
    start = gaussian_packet(grid.x, **PACKET)
    potential = np.zeros_like(grid.x)
    run = explicit_euler(
        start, potential, h=grid.h, dt=euler_dt, n_steps=euler_steps[-1], every=100
    )
    measured = norm(run.psi, grid.h)
    predicted = euler_norm(start, potential, h=grid.h, dt=euler_dt, steps=euler_steps)
    assert np.all(np.abs(measured / predicted - 1) < 1e-10)
    assert np.all(np.diff(measured) > 0)
    top = np.sqrt(1 + (euler_dt * 2 / grid.h**2) ** 2)

    experiment.table(
        "euler",
        list(zip(euler_steps, measured, predicted, strict=True)),
        [
            ("steps", "", "d"),
            ("norm, measured", "", ".6f"),
            ("norm, predicted from the spectrum", "", ".6f"),
        ],
        "The norm of the packet under explicit Euler, measured and predicted from "
        "the energies of the grid, on the coarse grid and short step of the example.",
    )
    return measured, top


def doubling():
    """Exercise 1: the time at which the width has doubled, 2 sqrt(3) sigma^2
    in these units, and the computed width there in units of the start."""
    time = 2 * np.sqrt(3) * WIDTH**2
    grid = free_line(cells)
    run = evolve(grid, dt, time)
    return time, spread(grid.x, run.psi[-1], grid.h) / WIDTH


def momentum():
    """Exercise 2: the mean momentum at the start and at the end time."""
    grid = free_line(cells)
    run = evolve(grid, dt, end_time)
    return mean_momentum(run.psi[0], grid.h), mean_momentum(run.psi[-1], grid.h)


def long_step():
    """Exercise 3: a step fifty times longer: the norm, and the error."""
    grid = free_line(cells)
    run = evolve(grid, 50 * dt, end_time)
    drift = float(np.max(np.abs(norm(run.psi, grid.h) - norm(run.psi[0], grid.h))))
    error = float(np.max(np.abs(run.psi[-1] - free_packet(grid.x, end_time, **PACKET))))
    return drift, error


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    grid, packet, exact, drift, rows = packet_run(experiment)
    experiment.figure("fig-packet", partial(draw_packet, grid, packet, exact))
    experiment.number("norm-drift", below(drift, NORM_BOUND))
    experiment.number("end-time", end_time, "g")
    experiment.number("end-error", rows[-1][5], ".4f")
    experiment.number("end-width", rows[-1][3], ".3f")

    spacings, errors, order = convergence(experiment)
    experiment.figure("fig-convergence", partial(draw_convergence, spacings, errors))
    experiment.number("order", order, ".2f")

    dispersion_grid, dispersion = dispersion_run(experiment)
    experiment.figure(
        "fig-dispersion", partial(draw_dispersion, dispersion_grid, dispersion)
    )
    gap = max(abs(r[5] / r[4] - 1) for r in dispersion)
    experiment.number("dispersion-gap", below(gap, 1e-9))
    packet_k = WAVENUMBER * dispersion_grid.h
    experiment.number("packet-kh", packet_k, ".2f")
    experiment.number("packet-grid-error", packet_k**2 / 12 * 100, ".2f")

    measured, top = euler_run(experiment)
    experiment.number("euler-gain", (measured[-1] - 1) * 100, ".2f")
    experiment.number("euler-top", top, ".3f")

    time, ratio = doubling()
    experiment.number("doubling-time", time, ".3f")
    experiment.number("doubling-ratio", ratio, ".4f")
    start_p, end_p = momentum()
    experiment.number("momentum-start", start_p, ".4f")
    experiment.number("momentum-end", end_p, ".4f")
    long_drift, long_error = long_step()
    experiment.number("long-drift", below(long_drift, NORM_BOUND))
    experiment.number("long-error", long_error, ".2f")
    return experiment


if __name__ == "__main__":
    main(run)
