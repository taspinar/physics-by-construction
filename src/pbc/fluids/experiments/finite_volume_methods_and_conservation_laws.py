"""The experiment of the lesson "Finite-volume methods and conservation laws".

The shared finite-volume interface of ``pbc.fluids.finite_volume`` with two
Riemann solvers, the Godunov flux of the Burgers equation and the HLL flux of
the shallow-water equations: the budgets of mass and momentum closed to
round-off, the CFL limit of the Godunov scheme, and a shock computed by the
conservative scheme and by a non-conservative one. Run it as a program to
write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.fluids.experiments.finite_volume_methods_and_conservation_laws out
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.fluids import burgers, shallow_water
from pbc.fluids.finite_volume import (
    evolve,
    interface_fluxes,
    periodic,
    rusanov,
    transmissive,
)
from pbc.verification.estimates import fitted_order

# region: budgets
LENGTH = 1.0  # m
BUDGET_CELLS = 200
BUDGET_BOUND = 1e-13  # relative to the size of the totals at the start
# endregion: budgets

# region: courant
courants = [0.5, 0.9, 1.0, 1.3, 1.6, 2.0]
COURANT_TIME = 1.0  # s
# endregion: courant

# region: jump
LEFT, RIGHT = 2.0, 0.5  # m/s
START = 0.2  # m
END_TIME = 0.4  # s
cells = [100, 200, 400, 800, 1600]
COURANT = 0.9
# endregion: jump


def centres(n: int) -> np.ndarray:
    return (np.arange(n) + 0.5) * LENGTH / n


def godunov(boundary):
    """The face fluxes of the Burgers equation with the Godunov flux."""
    return lambda u: interface_fluxes(u, burgers.godunov_flux, boundary)


def hll(boundary):
    """The face fluxes of the shallow-water equations with the HLL flux."""
    return lambda q: interface_fluxes(q, shallow_water.hll_flux, boundary)


def budget_cases():
    """The runs whose budgets the first example checks: the system, the
    boundary, the names of the conserved quantities, and the run."""
    n = BUDGET_CELLS
    dx = LENGTH / n
    x = centres(n)
    wave = 1.0 + 0.5 * np.sin(2.0 * np.pi * x)
    jump = np.where(x < 0.3, LEFT, RIGHT)
    hump = np.stack(
        [1.0 + 0.2 * np.exp(-(((x - 0.5) / 0.1) ** 2)), 0.3 * np.ones(n)], axis=-1
    )
    still = np.stack([np.where(x < 0.5, 1.0, 0.5), np.zeros(n)], axis=-1)
    burgers_speed, water_speed = burgers.max_speed, shallow_water.max_speed
    return [
        ("Burgers", "periodic", ["u"],
         evolve(wave, dx, 1.0, godunov(periodic), burgers_speed, COURANT)),
        ("Burgers", "open", ["u"],
         evolve(jump, dx, 0.3, godunov(transmissive), burgers_speed, COURANT)),
        ("shallow water", "periodic", ["h", "hu"],
         evolve(hump, dx, 2.0, hll(periodic), water_speed, COURANT)),
        ("shallow water", "walls", ["h", "hu"],
         evolve(still, dx, 2.0, hll(shallow_water.reflective), water_speed, COURANT)),
    ]  # fmt: skip


def budget_run(experiment: Experiment) -> float:
    """The change of each total and the largest residual of its budget, for
    each case; record the table and return the largest relative residual."""
    rows = []
    worst = 0.0
    for system, boundary, names, run in budget_cases():
        totals = run.totals.reshape(len(run.t), -1)
        scale = np.abs(totals[0]) + 1.0
        residual = np.max(np.abs(run.budget_residual.reshape(len(run.t), -1)), axis=0)
        for i, name in enumerate(names):
            relative = float(residual[i] / scale[i])
            worst = max(worst, relative)
            # Rounded to the table's four decimals with the sign of zero removed,
            # so that a change of -1e-17 shows as "0.0000", never "-0.0000".
            change = round(float(totals[-1, i] - totals[0, i]), 4) + 0.0
            rows.append((system, boundary, name, change, f"below {BUDGET_BOUND:.0e}"))
    assert worst < BUDGET_BOUND, "a budget did not close"
    experiment.table(
        "budget-run",
        rows,
        [
            ("system", "", ""),
            ("ends", "", ""),
            ("quantity", "", ""),
            ("change of the total", "", ".4f"),
            ("largest budget residual", "", ""),
        ],
        "For each run: the change of the total of each conserved quantity over "
        "the run, in the units of the quantity times metres, and the largest "
        "difference, over all steps, between that change and what entered "
        "through the ends, relative to the total at the start plus one.",
    )
    return worst


def total_variation(u: np.ndarray) -> float:
    """The sum of the jumps between neighbouring cells, around the periodic
    domain."""
    return float(np.sum(np.abs(np.diff(np.concatenate([u, u[:1]])))))


def courant_run(experiment: Experiment) -> list[tuple[float, float, float]]:
    """The wave of the budget example run at each Courant number; record the
    total variation and the largest value at the end over those at the start,
    and return the rows."""
    n = BUDGET_CELLS
    dx = LENGTH / n
    wave = 1.0 + 0.5 * np.sin(2.0 * np.pi * centres(n))
    rows = []
    for courant in courants:
        with np.errstate(over="ignore", invalid="ignore"):
            run = evolve(
                wave, dx, COURANT_TIME, godunov(periodic), burgers.max_speed, courant
            )
        relative = float(np.max(np.abs(run.budget_residual)) / (abs(run.totals[0]) + 1))
        assert relative < BUDGET_BOUND, "the budget broke with the step"
        rows.append(
            (courant, total_variation(run.q) / total_variation(wave),
             float(np.max(run.q) / np.max(wave)))
        )  # fmt: skip
    for courant, variation, largest in rows:
        if courant <= 1.0:
            assert variation <= 1.0 and largest <= 1.0, "the scheme grew within C <= 1"
    assert rows[-1][1] > 10.0, "the largest step did not blow up"
    experiment.table(
        "courant-run",
        rows,
        [
            ("Courant number", "", ".1f"),
            ("total variation, end over start", "", ".3f"),
            ("largest value, end over start", "", ".3f"),
        ],
        "The smooth wave of the budget example, run for one second with the "
        "Godunov flux at each Courant number: its total variation and its "
        "largest value at the end, each over its value at the start.",
    )
    return rows


def shock_position(u: np.ndarray, x: np.ndarray) -> float:
    """Where the profile crosses the mean of the two states, interpolated."""
    middle = 0.5 * (LEFT + RIGHT)
    i = int(np.nonzero((u[:-1] - middle) * (u[1:] - middle) <= 0)[0][0])
    return float(x[i] + (middle - u[i]) / (u[i + 1] - u[i]) * (x[i + 1] - x[i]))


def nonconservative(n: int) -> tuple[np.ndarray, float]:
    """The jump run with the non-conservative upwind step on ``n`` cells: the
    profile at the end, and the mass it created per unit time, the change of
    the total minus what the fluxes at the two ends brought in."""
    dx = LENGTH / n
    u = np.where(centres(n) < START, LEFT, RIGHT)
    mass = float(np.sum(u) * dx)
    entered = 0.0
    t = 0.0
    while t < END_TIME:
        dt = min(COURANT * dx / burgers.max_speed(u), END_TIME - t)
        entered += dt * float(burgers.flux(u[0]) - burgers.flux(u[-1]))
        u = burgers.nonconservative_step(u, dt, dx, transmissive)
        t = END_TIME if t + dt >= END_TIME else t + dt
    return u, (float(np.sum(u) * dx) - mass - entered) / END_TIME


def conservative(n: int, riemann=burgers.godunov_flux) -> np.ndarray:
    """The jump run with the conservative scheme on ``n`` cells, with the
    Riemann solver ``riemann``."""
    dx = LENGTH / n
    u = np.where(centres(n) < START, LEFT, RIGHT)
    return evolve(
        u,
        dx,
        END_TIME,
        lambda v: interface_fluxes(v, riemann, transmissive),
        burgers.max_speed,
        COURANT,
    ).q


def comparison_run(experiment: Experiment) -> tuple[float, float, float, float]:
    """The error and the shock speed of the two schemes on each grid; record
    the table, return the fitted orders of the two errors, the speed the
    non-conservative scheme converges to, and the mass it creates per unit
    time on the finest grid."""
    exact_speed = burgers.shock_speed(LEFT, RIGHT)
    rows, right_errors, wrong_errors = [], [], []
    for n in cells:
        x = centres(n)
        dx = LENGTH / n
        exact = burgers.riemann_solution(LEFT, RIGHT, (x - START) / END_TIME)
        good = conservative(n)
        bad, created = nonconservative(n)
        right_errors.append(float(np.sum(np.abs(good - exact)) * dx))
        wrong_errors.append(float(np.sum(np.abs(bad - exact)) * dx))
        rows.append(
            (n, right_errors[-1], wrong_errors[-1],
             (shock_position(good, x) - START) / END_TIME,
             (shock_position(bad, x) - START) / END_TIME)
        )  # fmt: skip
    widths = LENGTH / np.array(cells)
    right_order = fitted_order(widths, right_errors)
    wrong_order = fitted_order(widths, wrong_errors)
    wrong_speed = rows[-1][4]
    assert abs(rows[-1][3] - exact_speed) < 1e-3, "the conservative shock is slow"
    assert abs(wrong_speed - exact_speed) > 0.1, "the non-conservative shock is right"
    assert right_order > 0.9 and wrong_order < 0.1
    experiment.table(
        "comparison-run",
        rows,
        [
            ("cells", "", "d"),
            ("error, conservative", "m²/s", ".2e"),
            ("error, non-conservative", "m²/s", ".2e"),
            ("shock speed, conservative", "m/s", ".4f"),
            ("shock speed, non-conservative", "m/s", ".4f"),
        ],
        "The jump from two to one half metres per second after four tenths of "
        "a second, computed by the conservative Godunov scheme and by the "
        "non-conservative upwind scheme on each grid: the integral of the "
        "absolute error over the domain, and the speed of the shock from its "
        "position.",
    )
    return right_order, wrong_order, wrong_speed, created


def draw_conservative_and_not() -> Figure:
    """The jump after the run on two hundred cells: the exact solution, the
    conservative scheme, and the non-conservative scheme."""
    n = 200
    x = centres(n)
    exact = burgers.riemann_solution(LEFT, RIGHT, (x - START) / END_TIME)
    good = conservative(n)
    bad, _ = nonconservative(n)
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.plot(x, exact, color=FIGURE_COLOURS[2], linewidth=1.2, label="exact")
    ax.plot(
        x,
        good,
        color=FIGURE_COLOURS[0],
        linestyle="--",
        marker="o",
        markersize=3,
        markevery=3,
        label="conservative (Godunov)",
    )
    ax.plot(
        x,
        bad,
        color=FIGURE_COLOURS[1],
        linestyle=":",
        marker="s",
        markersize=3,
        markevery=3,
        label="non-conservative (upwind)",
    )
    ax.set_xlabel("position (m)")
    ax.set_ylabel("u (m/s)")
    ax.legend(loc="center left", frameon=False)
    return fig


def rusanov_run(experiment: Experiment) -> None:
    """Exercise 1: the jump on four hundred cells and the smooth wave of the
    budget example before it breaks, with the Godunov and the Rusanov flux;
    record the speed of the shock and the error of each run."""
    n = 400
    dx = LENGTH / n
    x = centres(n)
    exact = burgers.riemann_solution(LEFT, RIGHT, (x - START) / END_TIME)
    wave = 1.0 + 0.5 * np.sin(2.0 * np.pi * x)
    smooth = burgers.characteristic_solution(
        lambda y: 1.0 + 0.5 * np.sin(2.0 * np.pi * y), x, 0.2, LENGTH
    )
    rows = []
    for name, riemann in (
        ("Godunov", burgers.godunov_flux),
        ("Rusanov", rusanov(burgers.flux, np.abs)),
    ):
        u = conservative(n, riemann)
        v = evolve(
            wave,
            dx,
            0.2,
            lambda w, riemann=riemann: interface_fluxes(w, riemann, periodic),
            burgers.max_speed,
            COURANT,
        ).q
        rows.append(
            (name, (shock_position(u, x) - START) / END_TIME,
             float(np.sum(np.abs(u - exact)) * dx),
             float(np.sum(np.abs(v - smooth)) * dx))
        )  # fmt: skip
    experiment.table(
        "rusanov-run",
        rows,
        [
            ("flux", "", ""),
            ("shock speed", "m/s", ".4f"),
            ("error at the shock", "m²/s", ".2e"),
            ("error of the smooth wave", "m²/s", ".2e"),
        ],
        "Two Riemann solvers on four hundred cells: the speed of the shock of "
        "the comparison and the integral of its absolute error, and the "
        "integral of the absolute error of the smooth wave of the budget "
        "example before it breaks.",
    )


def upwind_flux_speed() -> float:
    """Exercise 2: the shock speed of the upwind scheme written as a
    difference of fluxes, on the finest grid; every state of the jump is
    positive, so the upwind face takes the flux of its left cell."""
    n = cells[-1]
    u = conservative(n, lambda left, right: burgers.flux(left))
    return (shock_position(u, centres(n)) - START) / END_TIME


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()

    budget_run(experiment)
    experiment.number("budget-bound", BUDGET_BOUND, ".0e")

    courant_run(experiment)

    right_order, wrong_order, wrong_speed, created = comparison_run(experiment)
    experiment.number("right-order", right_order, ".2f")
    experiment.number("wrong-order", wrong_order, ".2f")
    experiment.number("exact-speed", burgers.shock_speed(LEFT, RIGHT), ".4f")
    experiment.number("wrong-speed", wrong_speed, ".3f")
    experiment.number("created", created, ".3f")
    experiment.number(
        "deficit",
        (wrong_speed - burgers.shock_speed(LEFT, RIGHT)) * (LEFT - RIGHT),
        ".3f",
    )
    experiment.figure("fig-conservative-and-not", draw_conservative_and_not)

    rusanov_run(experiment)
    experiment.number("upwind-flux-speed", upwind_flux_speed(), ".4f")
    return experiment


if __name__ == "__main__":
    main(run)
