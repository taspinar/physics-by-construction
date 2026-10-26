"""The experiment of the lesson "Maxwell's equations and FDTD".

Yee's finite-difference time-domain scheme of ``pbc.electromagnetism.fdtd``:
the speed of a pulse in vacuum and in a dielectric against c / n and against
the scheme's own dispersion relation, as the grid is refined; the reflection
and transmission of a pulse at a dielectric interface and at a conductor
against the Fresnel coefficients, with the energy balance; the stability
limit in one and two dimensions, shown by runs just below and just above it;
and a pulse in a plane meeting a dielectric block, with the divergence of H
kept at round-off. Run it as a program to write the figures and numbers of
the page:

    uv run --locked --no-dev python -m \\
        pbc.electromagnetism.experiments.maxwells_equations_and_fdtd out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.electromagnetism.fdtd import (
    MU_0,
    SPEED_OF_LIGHT,
    Line,
    Plane,
    divergence_h,
    fresnel_reflection,
    fresnel_transmission,
    group_velocity,
    highest_mode_growth,
    stability_limit,
)
from pbc.electromagnetism.fields import EPSILON_0
from pbc.experiment import Experiment, main
from pbc.verification.estimates import fitted_order

# region: pulse
WAVELENGTH = 0.03  # m, of the carrier in the medium (10 GHz in vacuum)
CELLS_PER_WAVELENGTH = [10, 20, 40, 80]  # coarsest first
COURANT = 0.5  # c dt / dx
ENVELOPE = 3.0  # wavelengths, the 1/e half-width of the envelope
TRAVEL = 20.0  # wavelengths the pulse travels between the two centroids
INDICES = [1.0, 2.0]  # vacuum, and a dielectric of relative permittivity 4
# endregion: pulse
# region: interface
DX = 1e-3  # m
PULSE_CELLS = [10, 20, 40]  # the 1/e half-width of the pulse, in cells
N_RIGHT = 2.0  # refractive index beyond the interface
# endregion: interface
# region: stability
STABILITY_CELLS = 40  # per direction, between conducting walls
MARGIN = 0.01  # the runs are at (1 -/+ MARGIN) times the limit of the grid
STABILITY_STEPS = 400
SEED = 11  # of the random starting field
# endregion: stability
# region: plane
PLANE_CELLS = (380, 280)  # nx, ny
PLANE_DX = 1e-3  # m
SOURCE = (140, 140)  # the node at the centre of the starting pulse
BLOCK = (200, 360, 60, 220)  # i from, i to, j from, j to: the dielectric
BLOCK_PERMITTIVITY = 4.0
SNAPSHOTS = [70, 175]  # steps
# endregion: plane


def below(value: float, bound: float) -> str:
    """A quantity at the level of round-off is not shown as a number: only
    that it is smaller than ``bound``."""
    if abs(value) >= bound:
        raise ValueError(f"{value!r} is not below {bound!r}")
    return f"below {bound:.0e}"


def impedance(n: float) -> float:
    """The wave impedance of a medium of refractive index ``n``, ohm."""
    return float(np.sqrt(MU_0 / (EPSILON_0 * n**2)))


def launch(line: Line, shape, n: float = 1.0) -> None:
    """Start ``line`` with the pulse E_z = shape(x) travelling to the right
    in a medium of index ``n``: H_y = -E_z / Z, taken half a step earlier,
    since a step advances H first."""
    x = line.x
    line.e[:] = shape(x)
    line.e[[0, -1]] = 0.0
    half = x[:-1] + 0.5 * line.dx
    line.h[:] = -shape(half + 0.5 * (SPEED_OF_LIGHT / n) * line.dt) / impedance(n)


def centroid(line: Line) -> float:
    """The centre of the electromagnetic energy on the line, m."""
    energy = line.energy()
    return float(energy @ line.x / energy.sum())


def pulse_speed(n: float, cells_per_wavelength: int) -> tuple[float, float, float]:
    """A pulse with a carrier of ``cells_per_wavelength`` cells per
    wavelength in a medium of index ``n``: return dx, the measured speed of
    its energy centroid, and the group velocity of the grid, m/s."""
    dx = WAVELENGTH / cells_per_wavelength
    k0 = 2.0 * np.pi / WAVELENGTH
    width, start = ENVELOPE * WAVELENGTH, 8.0 * WAVELENGTH
    line = Line(
        round((2 * start + TRAVEL * WAVELENGTH) / dx),
        dx,
        COURANT,
        permittivity=n**2,
    )
    launch(
        line,
        lambda x: np.exp(-(((x - start) / width) ** 2)) * np.cos(k0 * (x - start)),
        n,
    )
    before = centroid(line)
    steps = round(TRAVEL * WAVELENGTH / (SPEED_OF_LIGHT / n * line.dt))
    line.run(steps)
    speed = (centroid(line) - before) / (steps * line.dt)
    return dx, speed, float(group_velocity(k0, dx, COURANT, n))


def wave_speed(experiment: Experiment) -> dict:
    """The measured speed of the pulse against c / n and the grid's group
    velocity, for each medium and grid; record the table and the fitted
    orders, and return the spacings and gaps by index."""
    rows, gaps = [], {}
    for n in INDICES:
        spacings, to_c = [], []
        for cells in CELLS_PER_WAVELENGTH:
            dx, speed, grid = pulse_speed(n, cells)
            exact = SPEED_OF_LIGHT / n
            spacings.append(dx)
            to_c.append(abs(speed / exact - 1.0))
            rows.append(
                (n, cells, speed / exact, grid / exact, abs(speed / grid - 1.0))
            )
        gaps[n] = (spacings, to_c)
        experiment.number(f"speed-order-{n:.0f}", fitted_order(spacings, to_c), ".2f")
    experiment.table(
        "wave-speed",
        rows,
        [
            ("refractive index", "", ".1f"),
            ("cells per wavelength", "", "d"),
            ("measured speed / (c/n)", "", ".5f"),
            ("group velocity of the grid / (c/n)", "", ".5f"),
            ("measured against grid, relative", "", ".1e"),
        ],
        "The speed of the energy centroid of a pulse with a carrier, measured "
        "over twenty wavelengths at the Courant number one half, against the "
        "speed of light in the medium and against the group velocity that the "
        "dispersion relation of the grid gives at the carrier.",
    )
    finest = [row for row in rows if row[1] == CELLS_PER_WAVELENGTH[-1]]
    experiment.number("speed-gap-fine", max(1.0 - row[2] for row in finest), ".1e")
    experiment.number("speed-to-grid", max(row[4] for row in rows), ".0e")
    return gaps


def interface_run(pulse_cells: int):
    """A Gaussian pulse of half-width ``pulse_cells`` cells from vacuum onto
    the dielectric of index N_RIGHT that fills the right half of the line.
    Return the line, its field at three times (start, at the interface,
    after), the interface node, and the starting energy."""
    cells = 40 * pulse_cells
    middle = cells // 2
    eps = np.ones(cells + 1)
    eps[middle + 1 :] = N_RIGHT**2
    eps[middle] = 0.5 * (1.0 + N_RIGHT**2)  # the interface node: the mean
    line = Line(cells, DX, COURANT, permittivity=eps)
    start, width = 0.5 * middle * DX, pulse_cells * DX
    launch(line, lambda x: np.exp(-(((x - start) / width) ** 2)))
    energy = line.energy().sum()
    snapshots = [line.e.copy()]
    arrive = round((middle * DX - start) / (SPEED_OF_LIGHT * line.dt))
    line.run(arrive)
    snapshots.append(line.e.copy())
    line.run(arrive)
    snapshots.append(line.e.copy())
    return line, snapshots, middle, energy


def largest(values) -> float:
    """The value of largest size, with its sign."""
    return float(values[np.argmax(np.abs(values))])


def reflection(experiment: Experiment):
    """The reflected and transmitted amplitudes and energies at the
    dielectric interface for three pulse widths, and the reflection at a
    conductor; record the tables and return the snapshots of the finest
    dielectric run."""
    r_exact, t_exact = (
        fresnel_reflection(1.0, N_RIGHT),
        fresnel_transmission(1.0, N_RIGHT),
    )
    rows, widths, gaps = [], [], []
    for cells in PULSE_CELLS:
        line, snapshots, middle, start = interface_run(cells)
        r = largest(line.e[:middle])
        t = largest(line.e[middle + 1 :])
        energy = line.energy()
        back = energy[:middle].sum() / start
        on = energy[middle:].sum() / start
        rows.append((cells, r, t, back, on, abs(back + on - 1.0)))
        widths.append(1.0 / cells)  # dx relative to the pulse width
        gaps.append(max(abs(r - r_exact), abs(t - t_exact)))
        if cells == PULSE_CELLS[-1]:
            shown = (line.x, snapshots, middle)
    rows.append((None, r_exact, t_exact, r_exact**2, N_RIGHT * t_exact**2, None))
    experiment.table(
        "interface",
        rows,
        [
            ("pulse half-width", "cells", "d"),
            ("reflected E / incident E", "", ".5f"),
            ("transmitted E / incident E", "", ".5f"),
            ("energy reflected", "", ".5f"),
            ("energy transmitted", "", ".5f"),
            ("energy balance, gap", "", ".0e"),
        ],
        "A pulse from vacuum onto a dielectric of refractive index two: the "
        "largest reflected and transmitted fields relative to the incident "
        "peak, and the fractions of the starting energy on each side, at the "
        "Courant number one half; the last row is the Fresnel prediction.",
    )
    experiment.number("interface-gap", gaps[-1], ".0e")
    experiment.number("interface-order", fitted_order(widths, gaps), ".2f")
    experiment.number("energy-balance", max(row[5] for row in rows[:-1]), ".0e")
    # A conductor in place of the dielectric: the line ends at the middle.
    middle = 20 * PULSE_CELLS[-1]
    line = Line(middle, DX, COURANT)
    start, width = 0.5 * middle * DX, PULSE_CELLS[-1] * DX
    launch(line, lambda x: np.exp(-(((x - start) / width) ** 2)))
    line.run(2 * round((middle * DX - start) / (SPEED_OF_LIGHT * line.dt)))
    experiment.number("conductor-reflection", largest(line.e), ".5f")
    return shown


def stability_run(dimensions: int, courant: float) -> np.ndarray:
    """The largest |E_z| after each step of a random field on a grid of
    STABILITY_CELLS cells per direction, at ``courant``."""
    rng = np.random.default_rng(SEED)
    n = STABILITY_CELLS
    if dimensions == 1:
        grid = Line(n, DX, courant)
        grid.e[1:-1] = rng.standard_normal(n - 1)
        field = lambda: grid.e  # noqa: E731
    else:
        grid = Plane(n, n, DX, courant)
        grid.ez[1:-1, 1:-1] = rng.standard_normal((n - 1, n - 1))
        field = lambda: grid.ez  # noqa: E731
    peaks = []
    for _ in range(STABILITY_STEPS):
        grid.step()
        peaks.append(np.max(np.abs(field())))
    return np.array(peaks)


def stability(experiment: Experiment) -> dict:
    """Runs just below and just above the stability limit of the grid, in
    one and two dimensions: the growth per step measured from the last half
    of each run, against the amplification of the highest mode; record the
    table and return the runs."""
    rows, runs = [], {}
    for dimensions in (1, 2):
        limit = stability_limit(STABILITY_CELLS, dimensions)
        for factor in (1.0 - MARGIN, 1.0 + MARGIN):
            courant = factor * limit
            peaks = stability_run(dimensions, courant)
            late = np.arange(STABILITY_STEPS // 2, STABILITY_STEPS)
            slope = np.polyfit(late, np.log(peaks[late]), 1)[0]
            runs[(dimensions, factor)] = peaks
            rows.append(
                (
                    dimensions,
                    limit,
                    courant,
                    peaks.max() / peaks[0],
                    np.exp(slope),
                    highest_mode_growth(courant, STABILITY_CELLS, dimensions),
                )
            )
    experiment.table(
        "stability",
        rows,
        [
            ("dimensions", "", "d"),
            ("limit of the grid", "", ".5f"),
            ("Courant number", "", ".5f"),
            ("largest |E| / first |E|", "", ".3g"),
            ("measured growth per step", "", ".4f"),
            ("growth of the highest mode", "", ".4f"),
        ],
        "A random field on a grid of forty cells per direction, run for four "
        "hundred steps one per cent below and one per cent above the stability "
        "limit of the grid: the growth of its largest value, and the growth "
        "per step fitted over the last two hundred steps, against the "
        "amplification of the highest mode of the grid.",
    )
    for dimensions in (1, 2):
        experiment.number(
            f"limit-{dimensions}d", stability_limit(STABILITY_CELLS, dimensions), ".4f"
        )
    stable = [row for row in rows if row[2] < row[1]]
    unstable = [row for row in rows if row[2] > row[1]]
    experiment.number("stable-growth", max(row[3] for row in stable), ".2f")
    experiment.number(
        "growth-gap", max(abs(row[4] / row[5] - 1.0) for row in unstable), ".0e"
    )
    return runs


def plane() -> tuple[Plane, list]:
    """A pulse of E_z at a point of the plane, spreading towards a dielectric
    block: the grid and two snapshots."""
    nx, ny = PLANE_CELLS
    eps = np.ones((nx + 1, ny + 1))
    i0, i1, j0, j1 = BLOCK
    eps[i0:i1, j0:j1] = BLOCK_PERMITTIVITY
    grid = Plane(nx, ny, PLANE_DX, 0.99 * stability_limit(max(nx, ny), 2), eps)
    i, j = np.meshgrid(np.arange(nx + 1), np.arange(ny + 1), indexing="ij")
    grid.ez[:] = np.exp(-(((i - SOURCE[0]) ** 2 + (j - SOURCE[1]) ** 2) / 4.0**2))
    grid.ez[[0, -1], :] = 0.0
    grid.ez[:, [0, -1]] = 0.0
    snapshots, done = [], 0
    for steps in SNAPSHOTS:
        grid.run(steps - done)
        done = steps
        snapshots.append(grid.ez.copy())
    return grid, snapshots


def draw_interface(shown) -> Figure:
    """E_z along the line at the start, at the interface, and after."""
    x, snapshots, middle = shown
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    centimetres = 100 * x
    ax.axvspan(
        centimetres[middle], centimetres[-1], color=FIGURE_COLOURS[2], alpha=0.12
    )
    for e, line, colour, label in zip(
        snapshots,
        ("-", "--", "-."),
        (FIGURE_COLOURS[0], FIGURE_COLOURS[2], FIGURE_COLOURS[1]),
        ("start", "at the interface", "after"),
        strict=True,
    ):
        ax.plot(centimetres, e, color=colour, linestyle=line, label=label)
    ax.text(
        centimetres[middle] + 1.0, 0.85, "dielectric, n = 2", color=FIGURE_COLOURS[2]
    )
    ax.set_xlabel("x (cm)")
    ax.set_ylabel(r"$E_z$ / incident peak (dimensionless)")
    ax.legend(frameon=False, loc="lower left")
    fig.tight_layout()
    return fig


def draw_dispersion(gaps: dict) -> Figure:
    """Log-log gap of the measured speed to c / n against dx, both media,
    with a reference slope two."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    for (n, (spacings, to_c)), marker, line, colour in zip(
        gaps.items(),
        ("o", "s"),
        ("-", "--"),
        (FIGURE_COLOURS[0], FIGURE_COLOURS[1]),
        strict=True,
    ):
        h = 1e3 * np.array(spacings)
        ax.loglog(
            h,
            to_c,
            color=colour,
            marker=marker,
            linestyle=line,
            label="vacuum" if n == 1 else f"dielectric, n = {n:g}",
        )
    h = 1e3 * np.array(gaps[INDICES[0]][0])
    ax.loglog(
        h,
        0.5 * gaps[INDICES[0]][1][0] * (h / h[0]) ** 2,
        color=FIGURE_COLOURS[2],
        linestyle=":",
        label="reference, slope two",
    )
    ax.set_xticks(h, labels=[f"{value:.3g}" for value in h])
    ax.minorticks_off()
    ax.set_xlabel("dx (mm)")
    ax.set_ylabel("1 - measured speed / (c/n)")
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    return fig


def draw_stability(runs: dict) -> Figure:
    """The largest |E| against the step, just below and just above the
    limit, one panel per dimension."""
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4), sharey=True)
    steps = np.arange(1, STABILITY_STEPS + 1)
    for ax, dimensions in zip(axes, (1, 2), strict=True):
        for factor, line, colour, label in (
            (1.0 - MARGIN, "-", FIGURE_COLOURS[0], "just below the limit"),
            (1.0 + MARGIN, "--", FIGURE_COLOURS[1], "just above the limit"),
        ):
            peaks = runs[(dimensions, factor)]
            ax.semilogy(
                steps, peaks / peaks[0], color=colour, linestyle=line, label=label
            )
        ax.set_title(f"{dimensions}D", fontsize="medium")
        ax.set_xlabel("step")
    axes[0].set_ylabel("largest |E| / first (log scale)")
    axes[0].legend(frameon=False, loc="upper left")
    fig.tight_layout()
    return fig


def draw_plane(grid: Plane, snapshots: list) -> Figure:
    """E_z in the plane at two times, false colour centred on zero on one
    scale, with the dielectric block outlined."""
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4), sharey=True)
    side = 100 * grid.dx
    extent = (0.0, side * grid.nx, 0.0, side * grid.ny)
    i0, i1, j0, j1 = BLOCK
    scale = float(np.max(np.abs(snapshots[0])))
    for ax, field, steps in zip(axes, snapshots, SNAPSHOTS, strict=True):
        image = ax.imshow(
            field.T / scale,
            origin="lower",
            extent=extent,
            cmap="PuOr",
            vmin=-1.0,
            vmax=1.0,
        )
        ax.add_patch(
            plt.Rectangle(
                (side * i0, side * j0),
                side * (i1 - i0),
                side * (j1 - j0),
                fill=False,
                edgecolor="black",
                linestyle="--",
            )
        )
        ax.set_title(f"after {steps} steps", fontsize="medium")
        ax.set_xlabel("x (cm)")
    axes[0].set_ylabel("y (cm)")
    bar = fig.colorbar(image, ax=axes, shrink=0.8)
    bar.set_label(
        "$E_z$ / its largest value at the first time\n"
        "(false colour, zero at the centre)"
    )
    return fig


def light_crossing(experiment: Experiment) -> None:
    """Exercise 1: the steps a grid of the lesson needs for light to cross a
    room of 3 m at 10 GHz with twenty cells per wavelength, at the largest
    stable step of one, two, and three dimensions; record the table."""
    room, cells = 3.0, 20
    dx = WAVELENGTH / cells
    rows = []
    for dimensions in (1, 2, 3):
        courant = 1.0 / np.sqrt(dimensions)
        dt = courant * dx / SPEED_OF_LIGHT
        rows.append(
            (
                dimensions,
                courant,
                1e12 * dt,
                round(room / (SPEED_OF_LIGHT * dt)),
                (room / dx) ** dimensions,
            )
        )
    experiment.table(
        "light-crossing",
        rows,
        [
            ("dimensions", "", "d"),
            ("largest Courant number", "", ".4f"),
            ("dt", "ps", ".3f"),
            ("steps to cross 3 m", "", "d"),
            ("cells", "", ".2e"),
        ],
        "A room three metres across at 10 GHz with twenty cells per wavelength: "
        "the largest stable step of a fine grid in one, two, and three "
        "dimensions, the steps light needs to cross the room, and the cells.",
    )


def impedance_step(experiment: Experiment) -> None:
    """Exercise 2: the reflection from vacuum onto glass (n = 1.5) and from
    glass onto vacuum, and the energy fractions; record the table."""
    rows = []
    for n1, n2 in ((1.0, 1.5), (1.5, 1.0)):
        r = fresnel_reflection(n1, n2)
        t = fresnel_transmission(n1, n2)
        rows.append((n1, n2, r, t, r**2, n2 / n1 * t**2))
    experiment.table(
        "glass",
        rows,
        [
            ("n1", "", ".1f"),
            ("n2", "", ".1f"),
            ("reflected E / incident E", "", ".3f"),
            ("transmitted E / incident E", "", ".3f"),
            ("energy reflected", "", ".3f"),
            ("energy transmitted", "", ".3f"),
        ],
        "The Fresnel coefficients at normal incidence between vacuum and glass, "
        "both ways, with the fractions of the incident energy.",
    )


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    gaps = wave_speed(experiment)
    experiment.figure("fig-fdtd-dispersion", partial(draw_dispersion, gaps))
    shown = reflection(experiment)
    experiment.figure("fig-pulse-at-interface", partial(draw_interface, shown))
    runs = stability(experiment)
    experiment.figure("fig-fdtd-stability", partial(draw_stability, runs))
    grid, snapshots = plane()
    largest_h = max(np.max(np.abs(grid.hx)), np.max(np.abs(grid.hy)))
    experiment.number(
        "divergence-h",
        below(float(np.max(np.abs(divergence_h(grid)))) * grid.dx / largest_h, 1e-12),
    )
    experiment.figure("fig-fdtd-plane", partial(draw_plane, grid, snapshots))
    light_crossing(experiment)
    impedance_step(experiment)
    return experiment


if __name__ == "__main__":
    main(run)
