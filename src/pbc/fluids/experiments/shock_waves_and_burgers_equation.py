"""The experiment of the lesson "Shock waves and the Burgers equation".

The inviscid Burgers equation solved with the Godunov flux of
``pbc.fluids.burgers`` on the shared finite-volume interface: a smooth wave
that steepens, checked against the characteristic solution before it breaks;
shocks whose measured speed is checked against the Rankine-Hugoniot
condition; and the energy that the scheme removes, checked against the
dissipation of a shock and against zero for smooth flow. Run it as a program
to write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.fluids.experiments.shock_waves_and_burgers_equation out
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.fluids.burgers import (
    breaking_time,
    characteristic_solution,
    godunov_flux,
    max_speed,
    riemann_solution,
    shock_dissipation,
    shock_speed,
)
from pbc.fluids.finite_volume import evolve, interface_fluxes, periodic, transmissive
from pbc.verification.estimates import fitted_order

# region: wave
MEAN = 1.0  # m/s
AMPLITUDE = 0.5  # m/s
LENGTH = 1.0  # m, a periodic domain
cells = [50, 100, 200, 400, 800]
BEFORE = 0.2  # s, a time before the wave breaks
COURANT = 0.9
# endregion: wave

# region: shocks
pairs = [(2.0, 0.0), (1.0, -0.5), (3.0, 1.0), (1.0, -3.0)]  # u_L, u_R in m/s
SHOCK_CELLS = 400
DAM = 0.5  # m: where the jump starts
TRAVELS = (0.1, 0.3)  # m: the fastest wave travels this far by each of two times
# endregion: shocks

# region: energy
ENERGY_PAIR = (2.0, 0.0)  # m/s
ENERGY_START = 0.2  # m
ENERGY_WINDOW = (0.05, 0.25)  # s
energy_cells = [100, 200, 400, 800]
# endregion: energy

SPEED_TOLERANCE = 0.01  # relative, for the measured shock speed


def initial(x):
    """The smooth periodic wave at the start (m/s)."""
    return MEAN + AMPLITUDE * np.sin(2.0 * np.pi * x / LENGTH)


def centres(n: int, length: float = LENGTH) -> np.ndarray:
    return (np.arange(n) + 0.5) * length / n


def godunov(boundary):
    """The face fluxes of the Godunov scheme with ``boundary``."""
    return lambda u: interface_fluxes(u, godunov_flux, boundary)


def energy(u: np.ndarray, dx: float) -> float:
    """The energy, the integral of u^2 / 2 over the domain (m^3/s^2)."""
    return float(np.sum(0.5 * u * u) * dx)


def the_breaking_time() -> float:
    """The breaking time of the wave from its steepest slope."""
    x = np.linspace(0.0, LENGTH, 100_001)
    slope = AMPLITUDE * 2.0 * np.pi / LENGTH * np.cos(2.0 * np.pi * x / LENGTH)
    return breaking_time(slope)


def steepening_run(experiment: Experiment) -> tuple[float, list[float]]:
    """The run before breaking against the characteristic solution, and the
    energy it lost, for each grid; record the table and return the fitted
    order of the error and the rates of energy loss."""
    errors, rates = [], []
    for n in cells:
        dx = LENGTH / n
        x = centres(n)
        start = initial(x)
        end = evolve(start, dx, BEFORE, godunov(periodic), max_speed, COURANT).q
        exact = characteristic_solution(initial, x, BEFORE, LENGTH)
        errors.append(float(np.sum(np.abs(end - exact)) * dx))
        rates.append((energy(start, dx) - energy(end, dx)) / BEFORE)
    order = fitted_order(LENGTH / np.array(cells), errors)
    assert abs(order - 1.0) < 0.05, "the Godunov scheme is not of order one"
    experiment.table(
        "steepening-run",
        [(n, LENGTH / n, e) for n, e in zip(cells, errors, strict=True)],
        [("cells", "", "d"), ("cell width", "m", ".5f"), ("error", "m²/s", ".3e")],
        "The error of the Godunov scheme against the characteristic solution "
        "of the steepening wave before it breaks, the integral of the "
        "absolute difference over the domain, for each grid.",
    )
    return order, rates


def shock_position(u: np.ndarray, x: np.ndarray, left: float, right: float) -> float:
    """Where the profile crosses the mean of the two states, interpolated
    between the two cells on either side of the crossing."""
    middle = 0.5 * (left + right)
    i = int(np.nonzero((u[:-1] - middle) * (u[1:] - middle) <= 0)[0][0])
    return float(x[i] + (middle - u[i]) / (u[i + 1] - u[i]) * (x[i + 1] - x[i]))


def measured_speed(left: float, right: float, n: int = SHOCK_CELLS) -> float:
    """The speed of the shock between ``left`` and ``right``, from its
    positions at two times of the run."""
    dx = LENGTH / n
    x = centres(n)
    u = np.where(x < DAM, left, right)
    fastest = max(abs(left), abs(right))
    times = [d / fastest for d in TRAVELS]
    first = evolve(u, dx, times[0], godunov(transmissive), max_speed, COURANT).q
    second = evolve(
        first, dx, times[1] - times[0], godunov(transmissive), max_speed, COURANT
    ).q
    positions = [shock_position(v, x, left, right) for v in (first, second)]
    return (positions[1] - positions[0]) / (times[1] - times[0])


def shock_run(experiment: Experiment) -> list[float]:
    """The measured speed of each shock against the Rankine-Hugoniot speed;
    record the table and return the relative differences."""
    rows, gaps = [], []
    for left, right in pairs:
        found = measured_speed(left, right)
        expected = shock_speed(left, right)
        gaps.append(abs(found - expected) / max(abs(left), abs(right)))
        rows.append((left, right, found, expected))
    assert max(gaps) < SPEED_TOLERANCE, "a shock moved at another speed"
    experiment.table(
        "shock-run",
        rows,
        [
            ("left state", "m/s", ".1f"),
            ("right state", "m/s", ".1f"),
            ("measured speed", "m/s", ".4f"),
            ("Rankine-Hugoniot speed", "m/s", ".4f"),
        ],
        "The speed of each shock measured from its positions at two times of "
        "a run on four hundred cells, against the jump of the flux over the "
        "jump of u.",
    )
    return gaps


def shock_energy_rate(n: int) -> float:
    """The rate at which the run removes energy while the shock of
    ``ENERGY_PAIR`` moves, from the energy budget over ``ENERGY_WINDOW``:
    what entered through the ends (u^3 / 3 at each) minus the growth of the
    energy in the domain."""
    left, right = ENERGY_PAIR
    dx = LENGTH / n
    x = centres(n)
    u = np.where(x < ENERGY_START, left, right)
    start, end = ENERGY_WINDOW
    first = evolve(u, dx, start, godunov(transmissive), max_speed, COURANT).q
    second = evolve(first, dx, end - start, godunov(transmissive), max_speed, COURANT).q
    entered = (left**3 - right**3) / 3.0
    return entered - (energy(second, dx) - energy(first, dx)) / (end - start)


def dissipation_run(experiment: Experiment, smooth_rates: list[float]) -> list[float]:
    """The energy removed per unit time in smooth flow and at a shock, for
    each grid; record the table and return the shock rates."""
    shock_rates = [shock_energy_rate(n) for n in energy_cells]
    expected = shock_dissipation(*ENERGY_PAIR)
    smooth = dict(zip(cells, smooth_rates, strict=True))
    assert all(abs(r - expected) < 0.03 * expected for r in shock_rates), (
        "the shock does not dissipate (u_L - u_R)^3 / 12"
    )
    assert fitted_order(1.0 / np.array(cells), smooth_rates) > 0.9, (
        "the smooth flow does not stop losing energy as the grid is refined"
    )
    experiment.table(
        "dissipation-run",
        [(n, smooth[n], r) for n, r in zip(energy_cells, shock_rates, strict=True)],
        [
            ("cells", "", "d"),
            ("smooth wave", "m³/s³", ".5f"),
            ("shock", "m³/s³", ".4f"),
        ],
        "The energy removed per unit time by the Godunov scheme, for each "
        "grid: from the smooth wave before it breaks, and from the shock "
        "between two and zero metres per second, where the energy that "
        "entered through the ends is accounted for.",
    )
    return shock_rates


def draw_steepening() -> Figure:
    """The wave at four times, computed on four hundred cells: before the
    break with the characteristic solution beside it, at the break, and as a
    shock."""
    n = 400
    dx = LENGTH / n
    x = centres(n)
    t_break = the_breaking_time()
    times = [0.0, 0.15, t_break, 0.6]
    styles = [
        ("-", "o", FIGURE_COLOURS[0]),
        ("--", "s", FIGURE_COLOURS[1]),
        ("-.", "^", FIGURE_COLOURS[3]),
        (":", "D", FIGURE_COLOURS[2]),
    ]
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    u = initial(x)
    now = 0.0
    for t, (line, marker, colour) in zip(times, styles, strict=True):
        if t > now:
            u = evolve(u, dx, t - now, godunov(periodic), max_speed, COURANT).q
            now = t
        label = "t = 0 s" if t == 0 else f"t = {t:.2f} s"
        if t == t_break:
            label += ", breaking"
        ax.plot(
            x,
            u,
            color=colour,
            linestyle=line,
            marker=marker,
            markevery=25,
            markersize=4,
            label=label,
        )
    exact = characteristic_solution(initial, x[::8], 0.15, LENGTH)
    ax.plot(
        x[::8],
        exact,
        linestyle="none",
        marker="x",
        color=FIGURE_COLOURS[2],
        markersize=5,
        label="characteristics, t = 0.15 s",
    )
    ax.set_xlabel("position (m)")
    ax.set_ylabel("u (m/s)")
    fig.subplots_adjust(bottom=0.24)
    fig.legend(loc="lower center", ncol=3, frameon=False, fontsize=8)
    return fig


def rarefaction_run(experiment: Experiment) -> float:
    """Exercise 1: the rarefaction from u_L = 0 to u_R = 1 against the exact
    fan u = (x - x0) / t, for each grid; record the table, return the order."""
    start, t = 0.3, 0.4
    sizes = [100, 200, 400, 800]
    errors = []
    for n in sizes:
        dx = LENGTH / n
        x = centres(n)
        u = np.where(x < start, 0.0, 1.0)
        end = evolve(u, dx, t, godunov(transmissive), max_speed, COURANT).q
        exact = riemann_solution(0.0, 1.0, (x - start) / t)
        errors.append(float(np.sum(np.abs(end - exact)) * dx))
    experiment.table(
        "rarefaction-run",
        list(zip(sizes, errors, strict=True)),
        [("cells", "", "d"), ("error", "m²/s", ".3e")],
        "The error of the Godunov scheme against the exact rarefaction fan, "
        "the integral of the absolute difference over the domain, for each "
        "grid.",
    )
    return fitted_order(LENGTH / np.array(sizes), errors)


def standing_shock() -> tuple[float, float]:
    """Exercise 2: the shock between u_L = 1 and u_R = -1, its measured speed
    and its position after a while."""
    n = SHOCK_CELLS
    dx = LENGTH / n
    x = centres(n)
    u = np.where(x < DAM, 1.0, -1.0)
    end = evolve(u, dx, 0.3, godunov(transmissive), max_speed, COURANT).q
    return measured_speed(1.0, -1.0), shock_position(end, x, 1.0, -1.0)


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()

    experiment.number("breaking-time", the_breaking_time(), ".4f")
    order, smooth_rates = steepening_run(experiment)
    experiment.number("smooth-order", order, ".2f")
    experiment.figure("fig-burgers-steepening", draw_steepening)

    gaps = shock_run(experiment)
    experiment.number("speed-gap", max(gaps) * 100, ".2f")

    shock_rates = dissipation_run(experiment, smooth_rates)
    experiment.number("dissipation-exact", shock_dissipation(*ENERGY_PAIR), ".4f")
    experiment.number(
        "dissipation-gap",
        abs(shock_rates[-1] / shock_dissipation(*ENERGY_PAIR) - 1.0) * 100,
        ".1f",
    )

    experiment.number("fan-order", rarefaction_run(experiment), ".2f")
    speed, position = standing_shock()
    experiment.number("standing-speed", abs(speed), ".1e")
    experiment.number("standing-position", position, ".4f")
    return experiment


if __name__ == "__main__":
    main(run)
