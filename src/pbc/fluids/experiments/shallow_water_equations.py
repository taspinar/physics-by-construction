"""The experiment of the lesson "Shallow-water equations: still water and
the dam break".

The shallow-water equations of ``pbc.fluids.shallow_water`` on the shared
finite-volume interface, with the HLL Riemann solver: a lake at rest over a
bump, kept still by hydrostatic reconstruction and set moving by a pointwise
bed source; the dam break over a wet bed against its exact solution; the
dam break over a dry bed, where the depth must stay positive; the speed of
long waves; and the budgets of a closed tank. Run it as a program to write
the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.fluids.experiments.shallow_water_equations out
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.fluids.finite_volume import (
    conservative_update,
    evolve,
    interface_fluxes,
    transmissive,
)
from pbc.fluids.shallow_water import (
    GRAVITY,
    dam_break,
    hll_flux,
    max_speed,
    pointwise_source,
    reflective,
    velocity,
    well_balanced,
)
from pbc.verification.estimates import fitted_order

COURANT = 0.9

# region: lake
LAKE_LENGTH = 10.0  # m, from -5 to 5, walls at both ends
SURFACE = 1.0  # m above the datum
BUMP = 0.5  # m, the height of the bed's bump, 0.5 exp(-x^2)
LAKE_TIME = 5.0  # s
lake_cells = [50, 100, 200, 400]
STILL_BOUND = 1e-12  # m/s and m
# endregion: lake

# region: dam
LENGTH = 20.0  # m, from -10 to 10, open ends
UPSTREAM = 2.0  # m, still water left of the dam at x = 0
DOWNSTREAM = 0.5  # m, still water right of it
DAM_TIME = 1.0  # s
dam_cells = [100, 200, 400, 800, 1600]
# endregion: dam

# region: dry
DRY_UPSTREAM = 1.0  # m, nothing right of the dam
dry_cells = [200, 400, 800, 1600]
WET = 1e-3  # m: the front is the last cell deeper than this
# endregion: dry

TANK_BOUND = 1e-13  # relative to the size of the totals at the start


def centres(n: int, length: float) -> np.ndarray:
    """The centres of ``n`` equal cells on [-length / 2, length / 2]."""
    return -length / 2 + (np.arange(n) + 0.5) * length / n


def lake(n: int) -> tuple[np.ndarray, np.ndarray, float]:
    """The bed, the still water over it, and the cell width of the lake."""
    x = centres(n, LAKE_LENGTH)
    bed = BUMP * np.exp(-(x**2))
    water = np.stack([SURFACE - bed, np.zeros(n)], axis=-1)
    return bed, water, LAKE_LENGTH / n


def lake_run(experiment: Experiment) -> tuple[float, float]:
    """The lake at rest run with the two treatments of the bed, for each
    grid; record the table and return the order of the spurious speed of the
    pointwise source and that speed on the coarsest grid."""
    rows, spurious = [], []
    for n in lake_cells:
        bed, water, dx = lake(n)
        fluxes, source = well_balanced(bed, dx, reflective)
        kept = evolve(water, dx, LAKE_TIME, fluxes, max_speed, COURANT, source).q
        fluxes, source = pointwise_source(bed, dx, reflective)
        moved = evolve(water, dx, LAKE_TIME, fluxes, max_speed, COURANT, source).q
        speed = float(np.max(np.abs(velocity(kept))))
        level = float(np.max(np.abs(kept[:, 0] + bed - SURFACE)))
        assert speed < STILL_BOUND and level < STILL_BOUND, "the lake moved"
        spurious.append(float(np.max(np.abs(velocity(moved)))))
        rows.append(
            (n, f"below {STILL_BOUND:.0e}", spurious[-1],
             float(np.max(np.abs(moved[:, 0] + bed - SURFACE))))
        )  # fmt: skip
    order = fitted_order(LAKE_LENGTH / np.array(lake_cells), spurious)
    assert order > 0.9, "the spurious current does not fall with the cell width"
    experiment.table(
        "lake-run",
        rows,
        [
            ("cells", "", "d"),
            ("largest speed, reconstruction", "m/s", ""),
            ("largest speed, pointwise source", "m/s", ".2e"),
            ("largest surface change, pointwise source", "m", ".2e"),
        ],
        "Still water with a flat surface over a bump of the bed, after five "
        "seconds, for each grid: the largest speed with hydrostatic "
        "reconstruction (where the surface also stays within the same bound), "
        "and the largest speed and change of the surface with the pointwise "
        "bed source.",
    )
    return order, spurious[0]


def dam_profile(n: int):
    """The wet dam break run on ``n`` cells: the centres and the state."""
    x = centres(n, LENGTH)
    water = np.stack([np.where(x < 0, UPSTREAM, DOWNSTREAM), np.zeros(n)], axis=-1)
    run = evolve(
        water,
        LENGTH / n,
        DAM_TIME,
        lambda q: interface_fluxes(q, hll_flux, transmissive),
        max_speed,
        COURANT,
    )
    return x, run.q


def front_position(h: np.ndarray, x: np.ndarray, level: float) -> float:
    """The last place where the depth crosses ``level``, interpolated."""
    i = int(np.nonzero((h[:-1] - level) * (h[1:] - level) <= 0)[0][-1])
    return float(x[i] + (level - h[i]) / (h[i + 1] - h[i]) * (x[i + 1] - x[i]))


def dam_run(experiment: Experiment) -> float:
    """The wet dam break against the exact solution, for each grid: the
    integral of the absolute depth error and the position of the front;
    record the table and return the order of the depth error."""
    exact = dam_break(UPSTREAM, DOWNSTREAM)
    front = exact.front_speed * DAM_TIME
    level = 0.5 * (exact.middle + DOWNSTREAM)
    rows, errors = [], []
    for n in dam_cells:
        x, q = dam_profile(n)
        dx = LENGTH / n
        errors.append(float(np.sum(np.abs(q[:, 0] - exact.depth(x, DAM_TIME))) * dx))
        found = front_position(q[:, 0], x, level)
        assert abs(found - front) < dx, "the front is more than a cell off"
        rows.append((n, dx, errors[-1], found, abs(found - front) / dx))
    order = fitted_order(LENGTH / np.array(dam_cells), errors)
    assert order > 0.7, "the dam break does not converge"
    experiment.table(
        "dam-run",
        rows,
        [
            ("cells", "", "d"),
            ("cell width", "m", ".4f"),
            ("depth error", "m²", ".3e"),
            ("front", "m", ".4f"),
            ("front error", "cells", ".2f"),
        ],
        "The dam break over a wet bed after one second, for each grid: the "
        "integral over the domain of the absolute difference between the "
        "computed and the exact depth, the computed position of the front, "
        "and its distance from the exact front in cell widths.",
    )
    return order


def draw_dam_break() -> Figure:
    """The depth and the velocity of the wet dam break after one second on
    two hundred cells, against the exact solution."""
    n = 200
    x, q = dam_profile(n)
    exact = dam_break(UPSTREAM, DOWNSTREAM)
    fine = np.linspace(-LENGTH / 2, LENGTH / 2, 4001)
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(6.4, 5.2), sharex=True)
    top.plot(
        fine,
        exact.depth(fine, DAM_TIME),
        color=FIGURE_COLOURS[2],
        linewidth=1.2,
        label="exact",
    )
    top.plot(
        x,
        q[:, 0],
        color=FIGURE_COLOURS[0],
        linestyle="none",
        marker="o",
        markersize=2.5,
        label="HLL, 200 cells",
    )
    top.set_ylabel("depth (m)")
    top.legend(loc="upper right", frameon=False)
    bottom.plot(
        fine,
        exact.velocity(fine, DAM_TIME),
        color=FIGURE_COLOURS[2],
        linewidth=1.2,
        label="exact",
    )
    bottom.plot(
        x,
        velocity(q),
        color=FIGURE_COLOURS[1],
        linestyle="none",
        marker="s",
        markersize=2.5,
        label="HLL, 200 cells",
    )
    bottom.set_ylabel("velocity (m/s)")
    bottom.set_xlabel("position (m)")
    bottom.legend(loc="upper left", frameon=False)
    return fig


def dry_run(experiment: Experiment) -> float:
    """The dam break over a dry bed, step by step, for each grid: the
    smallest depth of any cell at any step, the depth error, and the wet
    front against the exact front 2 sqrt(g h) t; record the table and return
    the smallest depth of all runs."""
    exact = dam_break(DRY_UPSTREAM, 0.0)
    rows = []
    lowest = np.inf
    for n in dry_cells:
        dx = LENGTH / n
        x = centres(n, LENGTH)
        q = np.stack([np.where(x < 0, DRY_UPSTREAM, 0.0), np.zeros(n)], axis=-1)
        t, smallest = 0.0, 0.0
        while t < DAM_TIME:
            dt = min(COURANT * dx / max_speed(q), DAM_TIME - t)
            q = conservative_update(
                q, interface_fluxes(q, hll_flux, transmissive), dt, dx
            )
            smallest = min(smallest, float(np.min(q[:, 0])))
            t = DAM_TIME if t + dt >= DAM_TIME else t + dt
        lowest = min(lowest, smallest)
        error = float(np.sum(np.abs(q[:, 0] - exact.depth(x, DAM_TIME))) * dx)
        rows.append((n, smallest, error, float(x[q[:, 0] > WET].max())))
    assert lowest >= 0.0, "a depth became negative"
    experiment.table(
        "dry-run",
        rows,
        [
            ("cells", "", "d"),
            ("smallest depth at any step", "m", ".1f"),
            ("depth error", "m²", ".3e"),
            ("last cell deeper than a millimetre", "m", ".3f"),
        ],
        "The dam break over a dry bed after one second, for each grid: the "
        "smallest depth of any cell at any step, the integral over the domain "
        "of the absolute depth error, and the centre of the last cell whose "
        "depth exceeds one millimetre.",
    )
    return lowest


def wave_speed() -> tuple[float, float]:
    """Exercise 1: a small hump on still water one metre deep splits into two
    waves; the speed of the right-going one from its crest at two times, and
    sqrt(g h)."""
    n, depth = 2000, 1.0
    dx = LENGTH / n
    x = centres(n, LENGTH)
    q = np.stack([depth + 0.001 * np.exp(-((x / 0.5) ** 2)), np.zeros(n)], axis=-1)

    def fluxes(state):
        return interface_fluxes(state, hll_flux, transmissive)

    first = evolve(q, dx, 0.5, fluxes, max_speed, COURANT).q
    second = evolve(first, dx, 1.0, fluxes, max_speed, COURANT).q
    right = x > 0
    crests = [x[right][np.argmax(s[right, 0])] for s in (first, second)]
    return float((crests[1] - crests[0]) / 1.0), float(np.sqrt(GRAVITY * depth))


def tank_run(experiment: Experiment) -> None:
    """Exercise 2: the wet dam break between two walls for ten seconds;
    record the change of the mass and of the momentum and the largest
    residual of their budgets."""
    n = 400
    dx = LENGTH / n
    x = centres(n, LENGTH)
    water = np.stack([np.where(x < 0, UPSTREAM, DOWNSTREAM), np.zeros(n)], axis=-1)
    run = evolve(
        water,
        dx,
        10.0,
        lambda q: interface_fluxes(q, hll_flux, reflective),
        max_speed,
        COURANT,
    )
    residual = np.max(np.abs(run.budget_residual), axis=0)
    scale = np.abs(run.totals[0]) + 1.0
    assert np.all(residual / scale < TANK_BOUND), "a budget of the tank did not close"
    # Rounded to the table's four decimals with the sign of zero removed.
    change = np.round(run.totals[-1] - run.totals[0], 4) + 0.0
    bound = f"below {TANK_BOUND:.0e}"
    experiment.table(
        "tank-run",
        [
            ("water volume per width", "m²", change[0], bound),
            ("momentum per density and width", "m³/s", change[1], bound),
        ],
        [
            ("quantity", "", ""),
            ("unit", "", ""),
            ("change after ten seconds", "", ".4f"),
            ("largest budget residual", "", ""),
        ],
        "The dam break in a tank with walls at both ends, for ten seconds on "
        "four hundred cells: the change of each total, and the largest "
        "difference over all steps between that change and what crossed the "
        "walls, relative to the total at the start plus one.",
    )


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()

    order, worst = lake_run(experiment)
    experiment.number("lake-order", order, ".2f")
    experiment.number("lake-worst", worst, ".3f")
    experiment.number("still-bound", STILL_BOUND, ".0e")

    exact = dam_break(UPSTREAM, DOWNSTREAM)
    experiment.number("middle-depth", exact.middle, ".4f")
    experiment.number("middle-velocity", exact.middle_velocity, ".4f")
    experiment.number("front-speed", exact.front_speed, ".4f")
    experiment.number("dam-order", dam_run(experiment), ".2f")
    experiment.figure("fig-dam-break", draw_dam_break)

    dry_run(experiment)
    experiment.number(
        "dry-front", dam_break(DRY_UPSTREAM, 0.0).front_speed * DAM_TIME, ".3f"
    )

    measured, expected = wave_speed()
    experiment.number("wave-measured", measured, ".3f")
    experiment.number("wave-expected", expected, ".3f")

    tank_run(experiment)
    return experiment


if __name__ == "__main__":
    main(run)
