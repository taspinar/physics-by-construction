"""The experiment of the lesson "Navier-Stokes fundamentals: pressure,
projection, and a solver checked".

The incompressible Navier-Stokes equations of ``pbc.fluids.navier_stokes``
on a periodic staggered grid: the projection of a field onto its
divergence-free part; the Taylor-Green vortex against its exact decay; a
manufactured solution, whose force makes every term of the equations act,
under grid refinement for the velocity and the pressure; and the energy
budget, without viscosity and with it. Lengths and times are in the units of
the box, [0, 2 pi) on each side, and of the flow's amplitude. Run it as a
program to write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.fluids.experiments.navier_stokes_fundamentals out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.fluids.navier_stokes import (
    Grid,
    divergence,
    gradient,
    kinetic_energy,
    manufactured,
    manufactured_forcing,
    march,
    pressure,
    project,
    taylor_green,
    tendency,
    viscous_dissipation,
)
from pbc.verification.estimates import fitted_order

# region: projection
PROJECTION_CELLS = 32
POTENTIAL = 0.6  # amplitude of the gradient part, phi = 0.6 cos(x + 2y)
ROUND_OFF = 1e-12  # 1/s and m/s: a bound for zero at double precision
# endregion: projection

# region: convergence
NU = 0.05  # m^2/s, the kinematic viscosity
FINAL = 1.0  # s
cells = [16, 32, 64, 128]
COURANT = 0.5
# endregion: convergence

# region: energy
ENERGY_CELLS = 64
ENERGY_TIME = 2.0  # s
energy_steps = [0.08, 0.04, 0.02]  # s, fixed steps without viscosity
BUDGET_NU = 0.02  # m^2/s
BUDGET_STEP = 0.01  # s
# endregion: energy


def projection_example(grid: Grid) -> dict:
    """A divergence-free field (the Taylor-Green vortex) plus the gradient of
    phi = POTENTIAL cos(x + 2y), and its projection."""
    kept_u, kept_v = taylor_green(grid, 0.0, 0.0)
    x, y = grid.points("p")
    phi_x, phi_y = gradient(POTENTIAL * np.cos(x + 2 * y), grid)
    u, v = kept_u + phi_x, kept_v + phi_y
    pu, pv, _ = project(u, v, grid)
    return {
        "u": u,
        "v": v,
        "projected": (pu, pv),
        "before": float(np.max(np.abs(divergence(u, v, grid)))),
        "after": float(np.max(np.abs(divergence(pu, pv, grid)))),
        "recovered": float(
            max(np.max(np.abs(pu - kept_u)), np.max(np.abs(pv - kept_v)))
        ),
        "energy": kinetic_energy(u, v, grid),
        "energy-kept": kinetic_energy(pu, pv, grid),
        "energy-removed": kinetic_energy(u - pu, v - pv, grid),
    }


def projection_run(experiment: Experiment) -> dict:
    """Record the table of the projection example."""
    grid = Grid(PROJECTION_CELLS, PROJECTION_CELLS)
    found = projection_example(grid)
    assert found["after"] < ROUND_OFF and found["recovered"] < ROUND_OFF
    split = found["energy-kept"] + found["energy-removed"] - found["energy"]
    assert abs(split) < ROUND_OFF * found["energy"], "the parts are not orthogonal"
    bound = f"below {ROUND_OFF:.0e}"
    experiment.table(
        "projection-run",
        [
            ("largest divergence", "1/s", f"{found['before']:.4f}", bound),
            ("largest difference from the vortex", "m/s", "", bound),
            (
                "kinetic energy",
                "m⁴/s²",
                f"{found['energy']:.4f}",
                f"{found['energy-kept']:.4f}",
            ),
        ],
        [
            ("quantity", "", ""),
            ("unit", "", ""),
            ("before the projection", "", ""),
            ("after it", "", ""),
        ],
        "A Taylor-Green vortex plus a gradient on a grid of 32 by 32 cells, "
        "before and after the projection: the largest divergence of a cell, "
        "the largest difference of the projected field from the vortex, and "
        "the kinetic energy, to four decimals.",
    )
    return found


def draw_projection(found: dict, grid: Grid) -> Figure:
    """The field before and after the projection: arrows of the velocity at
    the cell centres over the divergence in false colour, on one scale."""
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.6), sharey=True)
    xc, yc = grid.points("p")
    limit = found["before"]
    every = 2
    for ax, (u, v), title in (
        (axes[0], (found["u"], found["v"]), "before the projection"),
        (axes[1], found["projected"], "after the projection"),
    ):
        image = ax.imshow(
            divergence(u, v, grid),
            origin="lower",
            extent=(0, grid.lx, 0, grid.ly),
            cmap="PuOr",
            vmin=-limit,
            vmax=limit,
        )
        uc = 0.5 * (u + np.roll(u, -1, axis=1))
        vc = 0.5 * (v + np.roll(v, -1, axis=0))
        ax.quiver(
            xc[::every, ::every],
            yc[::every, ::every],
            uc[::every, ::every],
            vc[::every, ::every],
            color=FIGURE_COLOURS[2],
            scale=30,
            width=0.004,
        )
        ax.set_title(title, fontsize="medium")
        ax.set_xlabel("x (m)")
        ax.set_aspect("equal")
    axes[0].set_ylabel("y (m)")
    fig.colorbar(
        image, ax=axes, label="divergence (1/s) (false colour, zero at the centre)"
    )
    return fig


def solve_taylor_green(n: int) -> float:
    """The largest velocity error of the Taylor-Green vortex at FINAL."""
    grid = Grid(n, n)
    u, v = taylor_green(grid, NU, 0.0)
    u, v, _ = march(u, v, grid, NU, FINAL, courant=COURANT)
    exact_u, exact_v = taylor_green(grid, NU, FINAL)
    return float(max(np.max(np.abs(u - exact_u)), np.max(np.abs(v - exact_v))))


def solve_manufactured(n: int) -> tuple[float, float]:
    """The largest velocity error and the largest pressure error (both
    pressures with mean zero) of the manufactured solution at FINAL."""
    grid = Grid(n, n)
    force = manufactured_forcing(grid, NU)
    u, v, _ = manufactured(grid, 0.0)
    u, v, _ = march(u, v, grid, NU, FINAL, force, COURANT)
    exact_u, exact_v, exact_p = manufactured(grid, FINAL)
    p = pressure(u, v, grid, NU, force(FINAL))
    velocity = max(np.max(np.abs(u - exact_u)), np.max(np.abs(v - exact_v)))
    return float(velocity), float(np.max(np.abs(p - (exact_p - exact_p.mean()))))


def convergence_run(experiment: Experiment) -> dict:
    """Both problems on every grid; record the table and return the errors
    and the fitted orders."""
    widths = 2 * np.pi / np.array(cells)
    vortex = [solve_taylor_green(n) for n in cells]
    made = [solve_manufactured(n) for n in cells]
    velocity = [m[0] for m in made]
    pressures = [m[1] for m in made]
    orders = {
        "order-vortex": fitted_order(widths, vortex),
        "order-velocity": fitted_order(widths, velocity),
        "order-pressure": fitted_order(widths, pressures),
    }
    assert all(1.9 < order < 2.1 for order in orders.values()), orders
    experiment.table(
        "convergence-run",
        [
            (n, h, e, mv, mp)
            for n, h, e, mv, mp in zip(
                cells, widths, vortex, velocity, pressures, strict=False
            )
        ],
        [
            ("cells per side", "", "d"),
            ("cell width", "m", ".4f"),
            ("Taylor-Green velocity error", "m/s", ".3e"),
            ("manufactured velocity error", "m/s", ".3e"),
            ("manufactured pressure error", "m²/s²", ".3e"),
        ],
        "The largest error at one second against the exact solution, for "
        "each grid: the velocity of the Taylor-Green vortex, and the velocity "
        "and the pressure of the manufactured solution, to four significant "
        "digits.",
    )
    return {
        "widths": widths,
        "vortex": vortex,
        "velocity": velocity,
        "pressure": pressures,
        **orders,
    }


def draw_convergence(found: dict) -> Figure:
    """The errors against the cell width, log-log, with a reference line of
    slope two."""
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    h = found["widths"]
    series = (
        ("vortex", "Taylor-Green velocity", "o", "-"),
        ("velocity", "manufactured velocity", "s", "--"),
        ("pressure", "manufactured pressure", "^", ":"),
    )
    for (key, label, marker, style), colour in zip(
        series, FIGURE_COLOURS, strict=False
    ):
        ax.loglog(
            h, found[key], marker=marker, linestyle=style, color=colour, label=label
        )
    reference = found["pressure"][0] * 2.0 * (h / h[0]) ** 2
    ax.loglog(
        h,
        reference,
        color=FIGURE_COLOURS[2],
        linestyle="-.",
        linewidth=0.9,
        label="slope 2 (reference)",
    )
    ax.set_xlabel("cell width (m)")
    ax.set_ylabel("largest error at one second")
    ax.legend(frameon=False, fontsize="small")
    fig.tight_layout()
    return fig


def energy_field(grid: Grid) -> tuple[np.ndarray, np.ndarray]:
    """The flow of the energy examples: the manufactured velocity at the time
    one, plus a shear sin(2y) along x, which together are not steady."""
    u, v, _ = manufactured(grid, 1.0)
    _, y = grid.points("u")
    u, v, _ = project(u + 0.5 * np.sin(2 * y), v, grid)
    return u, v


def inviscid_run(experiment: Experiment) -> float:
    """Without viscosity, the relative change of the kinetic energy after
    ENERGY_TIME for each fixed step; record the table and return its order."""
    grid = Grid(ENERGY_CELLS, ENERGY_CELLS)
    u0, v0 = energy_field(grid)
    start = kinetic_energy(u0, v0, grid)
    changes = []
    for dt in energy_steps:
        u, v, _ = march(u0, v0, grid, 0.0, ENERGY_TIME, courant=10.0, largest_step=dt)
        changes.append(abs(kinetic_energy(u, v, grid) - start) / start)
    order = fitted_order(energy_steps, changes)
    assert order > 2.5, "the energy change does not fall with the step"
    experiment.table(
        "inviscid-run",
        list(zip(energy_steps, changes, strict=False)),
        [("time step", "s", ".2f"), ("relative change of the energy", "", ".3e")],
        "Without viscosity: the relative change of the kinetic energy over "
        "two seconds on a grid of 64 by 64 cells, for each fixed time step, "
        "to four significant digits.",
    )
    return order


def budget_history(grid: Grid) -> dict:
    """With viscosity BUDGET_NU: the energy and the dissipation rate at every
    step of BUDGET_STEP over ENERGY_TIME."""
    u, v = energy_field(grid)
    times = [0.0]
    energies = [kinetic_energy(u, v, grid)]
    rates = [viscous_dissipation(u, v, grid, BUDGET_NU)]

    def observe(t, u, v):
        times.append(t)
        energies.append(kinetic_energy(u, v, grid))
        rates.append(viscous_dissipation(u, v, grid, BUDGET_NU))

    march(
        u,
        v,
        grid,
        BUDGET_NU,
        ENERGY_TIME,
        courant=10.0,
        observe=observe,
        largest_step=BUDGET_STEP,
    )
    times, energies, rates = map(np.array, (times, energies, rates))
    # The trapezoidal rule: the dissipated energy up to each step.
    dissipated = np.concatenate(
        [[0.0], np.cumsum(0.5 * (rates[1:] + rates[:-1]) * np.diff(times))]
    )
    return {"t": times, "energy": energies, "dissipated": dissipated}


def budget_run(experiment: Experiment) -> dict:
    """Record the energy lost and the energy dissipated, and return the
    history."""
    found = budget_history(Grid(ENERGY_CELLS, ENERGY_CELLS))
    lost = found["energy"][0] - found["energy"][-1]
    dissipated = found["dissipated"][-1]
    mismatch = abs(lost - dissipated) / lost
    assert mismatch < 1e-4, "the energy budget does not close"
    experiment.number("budget-lost", lost, ".4f")
    experiment.number("budget-dissipated", dissipated, ".4f")
    experiment.number("budget-mismatch", mismatch, ".0e")
    experiment.number("budget-fraction", 100 * lost / found["energy"][0], ".0f")
    return found


def draw_energy_budget(found: dict) -> Figure:
    """Top: the kinetic energy against time, and the energy at the start
    minus the dissipated energy. Bottom: their difference relative to the
    energy at the start."""
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(6.4, 4.8), sharex=True, height_ratios=(2, 1)
    )
    t = found["t"]
    balance = found["energy"][0] - found["dissipated"]
    top.plot(
        t,
        found["energy"],
        color=FIGURE_COLOURS[0],
        linewidth=2.2,
        label="kinetic energy",
    )
    top.plot(
        t,
        balance,
        color=FIGURE_COLOURS[1],
        linestyle="--",
        label="start minus the dissipated energy",
    )
    top.set_ylabel("energy (m⁴/s²)")
    top.legend(frameon=False)
    bottom.plot(
        t,
        (found["energy"] - balance) / found["energy"][0],
        color=FIGURE_COLOURS[2],
        marker=".",
        markersize=2,
        linestyle="none",
    )
    bottom.axhline(0.0, color=FIGURE_COLOURS[2], linewidth=0.6)
    bottom.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
    bottom.set_ylabel("difference\n(relative)")
    bottom.set_xlabel("time (s)")
    fig.tight_layout()
    return fig


# region: reynolds
flows = [
    # (flow, speed in m/s, length in m, kinematic viscosity in m^2/s)
    ("honey poured from a spoon", 0.01, 0.005, 1e-2),
    ("blood in the aorta", 0.3, 0.025, 3.3e-6),
    ("a swimmer", 1.5, 2.0, 1.0e-6),
    ("air past a car on a motorway", 30.0, 4.0, 1.5e-5),
]
# endregion: reynolds


def reynolds_run(experiment: Experiment) -> None:
    """Exercise 1: the Reynolds number U L / nu of everyday flows."""
    experiment.table(
        "reynolds-run",
        [(name, u, length, nu, u * length / nu) for name, u, length, nu in flows],
        [
            ("flow", "", ""),
            ("speed", "m/s", ".2f"),
            ("length", "m", ".3f"),
            ("kinematic viscosity", "m²/s", ".1e"),
            ("Reynolds number", "", ".1e"),
        ],
        "The Reynolds number of four flows from their speed, size, and "
        "viscosity, to two significant digits.",
    )


def unprojected_run(experiment: Experiment) -> None:
    """Exercise 2: one step of the manufactured problem on 32 cells without
    the projection and with it, for three steps: the largest divergence."""
    grid = Grid(32, 32)
    force = manufactured_forcing(grid, NU)
    u, v, _ = manufactured(grid, 0.0)
    rows = []
    for dt in (0.04, 0.02, 0.01):
        du, dv = tendency(u, v, grid, NU, force(0.0))
        raw = float(np.max(np.abs(divergence(u + dt * du, v + dt * dv, grid))))
        pu, pv, _ = project(u + dt * du, v + dt * dv, grid)
        assert np.max(np.abs(divergence(pu, pv, grid))) < ROUND_OFF
        rows.append((dt, raw, f"below {ROUND_OFF:.0e}"))
    experiment.table(
        "unprojected-run",
        rows,
        [
            ("time step", "s", ".2f"),
            ("largest divergence without projection", "1/s", ".3e"),
            ("with projection", "1/s", ""),
        ],
        "One explicit step of the manufactured problem on 32 by 32 cells: the "
        "largest divergence of a cell without the projection, to four "
        "significant digits, and with it.",
    )


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()

    grid = Grid(PROJECTION_CELLS, PROJECTION_CELLS)
    found = projection_run(experiment)
    experiment.number("removed-energy", found["energy-removed"], ".4f")
    experiment.number("round-off", ROUND_OFF, ".0e")
    experiment.figure("fig-projection", partial(draw_projection, found, grid))

    converged = convergence_run(experiment)
    for name in ("order-vortex", "order-velocity", "order-pressure"):
        experiment.number(name, converged[name], ".2f")
    experiment.figure("fig-ns-convergence", partial(draw_convergence, converged))

    experiment.number("inviscid-order", inviscid_run(experiment), ".2f")
    history = budget_run(experiment)
    experiment.figure("fig-energy-budget", partial(draw_energy_budget, history))

    reynolds_run(experiment)
    unprojected_run(experiment)
    return experiment


if __name__ == "__main__":
    main(run)
