"""The experiment of the lesson "Discovering differential equations".

A damped oscillator simulated from four initial conditions, of which only
the positions are kept; the velocity and the acceleration by central
differences; and the equation of motion found as a sparse sum of the terms
of a polynomial library (``pbc.discovery.equations``). The found equation
is integrated from a held-out start; one orbit of an undamped oscillator
shows a library the data cannot pin down, and a pendulum a law the library
cannot hold. Run it as a program to write the figures and numbers of the
page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.discovering_differential_equations out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.discovery.equations import (
    Equation,
    central_differences,
    combine,
    integrate,
    polynomial_library,
    singular_values,
    sparse_regression,
)
from pbc.experiment import Experiment, main
from pbc.mechanics.dynamics import State, simulate
from pbc.mechanics.integrators import rk4_step

# region: oscillator
OMEGA2 = 4.0  # k / m, 1/s²
DAMPING = 0.3  # b / m, 1/s
DT = 0.01  # s, the sampling interval
DURATION = 10.0  # s
STARTS = ((1.0, 0.0), (0.0, 2.0), (-0.5, 1.0), (2.0, -1.0))  # x0 (m), v0 (m/s)
# endregion: oscillator
# region: criterion
DEGREE = 3  # the library: every x^i v^j with i + j <= 3
TOLERANCE = 0.05  # relative, on each coefficient of the true equation
TRUE = {"x": -OMEGA2, "v": -DAMPING}
# endregion: criterion
# region: held-out
HELD_OUT = (3.0, -2.0)  # x0 (m), v0 (m/s): outside every training orbit
# endregion: held-out
# region: one-orbit
ORBIT = (1.0, 0.0)  # x0 (m), v0 (m/s) of the undamped orbit
OTHER_ORBIT = (2.0, 0.0)
LAMBDA = 1.0  # 1/s², the size of the added term
# endregion: one-orbit
PENDULUM = 4.0  # g / L, 1/s²


def damped(x: np.ndarray, v: np.ndarray) -> np.ndarray:
    """The true acceleration (m/s²) of the damped oscillator."""
    return -OMEGA2 * x - DAMPING * v


def undamped(x: np.ndarray, v: np.ndarray) -> np.ndarray:
    """The true acceleration (m/s²) of the oscillator without damping."""
    return -OMEGA2 * x


def positions(acceleration, x0: float, v0: float) -> np.ndarray:
    """The positions (m), every ``DT`` over ``DURATION``, of the motion from
    ``x0`` and ``v0``, simulated with the fourth-order Runge-Kutta method at
    the sampling interval; the velocities are not kept."""
    steps = round(DURATION / DT)
    motion = simulate(
        State(0.0, [x0], [v0]),
        lambda t, x, v: acceleration(x, v),
        DT,
        steps,
        step=rk4_step,
    )
    return motion.x[:, 0]


def recovered(equation: Equation) -> bool:
    """Did the regression keep exactly the terms of the true equation, each
    coefficient within the tolerance?"""
    found = equation.coefficients
    return set(found) == set(TRUE) and all(
        abs(found[t] / c - 1) < TOLERANCE for t, c in TRUE.items()
    )


def discover(experiment: Experiment) -> Equation:
    """Positions of four damped orbits, central differences, and the sparse
    regression; record the coefficients of every term."""
    terms = polynomial_library(DEGREE)
    data = combine([central_differences(positions(damped, *s), DT) for s in STARTS])
    equation = sparse_regression(terms, data)
    experiment.table(
        "coefficients",
        [(t, TRUE.get(t, 0.0), equation.coefficients.get(t)) for t in terms],
        columns=[
            ("term", "", "s"),
            ("true coefficient", "", ".4f"),
            ("found coefficient", "", ".4f"),
        ],
        caption="Each term of the library, its coefficient in the true equation,"
        " and its coefficient in the found one, to four decimals; an empty cell"
        " is a term the regression dropped. The unit of a coefficient is that of"
        " the acceleration divided by that of the term.",
    )
    return equation


def held_out(equation: Equation) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The true motion from the held-out start and the motion of the found
    equation from it, over the duration."""
    t = np.arange(round(DURATION / DT) + 1) * DT
    truth = integrate(damped, *HELD_OUT, t)
    found = integrate(equation.acceleration, *HELD_OUT, t)
    return t, truth, found


def draw_held_out(t: np.ndarray, truth: np.ndarray, found: np.ndarray) -> Figure:
    """The true and the found motion from the held-out start, and their
    difference."""
    fig, (top, bottom) = plt.subplots(
        2,
        1,
        figsize=(6.4, 4.4),
        sharex=True,
        constrained_layout=True,
        gridspec_kw={"height_ratios": [2, 1]},
    )
    top.plot(t, truth, color=FIGURE_COLOURS[0], linestyle="-", label="true equation")
    top.plot(t, found, color=FIGURE_COLOURS[1], linestyle="--", label="found equation")
    top.set_ylabel("position (m)")
    top.legend(loc="upper right", fontsize=8)
    bottom.plot(t, found - truth, color=FIGURE_COLOURS[1], linestyle="-")
    bottom.set_ylabel("difference (m)")
    bottom.set_xlabel("time (s)")
    bottom.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
    return fig


def one_orbit(experiment: Experiment) -> tuple[np.ndarray, np.ndarray]:
    """The library on one orbit and on four orbits of the undamped
    oscillator, and an equation the one orbit cannot tell from the true one;
    record the residual of both on the orbit and on another one."""
    terms = polynomial_library(DEGREE)
    single = central_differences(positions(undamped, *ORBIT), DT)
    several = combine(
        [central_differences(positions(undamped, *s), DT) for s in STARTS]
    )
    # On the orbit the energy per mass, (OMEGA2 x^2 + v^2) / 2, keeps the
    # value it starts with; the added term is zero there and nowhere else.
    energy = OMEGA2 * ORBIT[0] ** 2 + ORBIT[1] ** 2
    true = Equation({"x": -OMEGA2}, 0.0)
    rival = Equation(
        {
            "x": -OMEGA2 - LAMBDA,
            "x^3": LAMBDA * OMEGA2 / energy,
            "x v^2": LAMBDA / energy,
        },
        0.0,
    )
    other = central_differences(positions(undamped, *OTHER_ORBIT), DT)

    def residual(equation: Equation, data) -> float:
        return float(
            np.sqrt(((data.a - equation.acceleration(data.x, data.v)) ** 2).mean())
        )

    experiment.table(
        "rival-equations",
        [
            (equation.formula(), residual(equation, single), residual(equation, other))
            for equation in (true, rival)
        ],
        columns=[
            ("equation", "", "s"),
            ("residual on the orbit", "m/s²", ".2g"),
            ("residual on another orbit", "m/s²", ".2g"),
        ],
        caption="Two equations on the orbit they were read from and on an orbit of"
        " twice the amplitude: the root-mean-square difference between the"
        " acceleration from central differences and the equation's, to two"
        " significant digits.",
    )
    return singular_values(terms, single), singular_values(terms, several)


def draw_singular_values(
    single: np.ndarray, several: np.ndarray, floor: float
) -> Figure:
    """The singular values of the library on one orbit and on four."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6), constrained_layout=True)
    index = np.arange(1, len(single) + 1)
    ax.semilogy(
        index,
        np.maximum(single, floor),
        color=FIGURE_COLOURS[1],
        marker="s",
        linestyle="--",
        label=f"one orbit (below {floor:g} drawn at {floor:g})",
    )
    ax.semilogy(
        index,
        several,
        color=FIGURE_COLOURS[0],
        marker="o",
        linestyle="-",
        label="four orbits",
    )
    ax.set_xlabel("singular value, largest first")
    ax.set_ylabel("relative to the largest (dimensionless)")
    ax.legend(loc="lower left", fontsize=8)
    return fig


def pendulum(experiment: Experiment) -> None:
    """Exercise: the regression on pendulum swings at small and at large
    amplitude; record the equations found and their error at a larger one."""
    terms = polynomial_library(DEGREE)

    def swing(x, v):
        return -PENDULUM * np.sin(x)

    t = np.arange(round(DURATION / DT) + 1) * DT
    rows = []
    for amplitude in (0.2, 1.5):
        starts = [(amplitude, 0.0), (0.5 * amplitude, 0.0)]
        data = combine([central_differences(positions(swing, *s), DT) for s in starts])
        equation = sparse_regression(terms, data)
        truth = integrate(swing, 2.0, 0.0, t)
        found = integrate(equation.acceleration, 2.0, 0.0, t)
        rows.append(
            (amplitude, equation.formula(), float(np.max(np.abs(found - truth))))
        )
    experiment.table(
        "pendulum",
        rows,
        columns=[
            ("largest amplitude", "rad", "g"),
            ("found equation", "", "s"),
            ("largest error from 2 rad", "rad", ".2f"),
        ],
        caption="The regression on two swings of a pendulum with g/L = 4 per"
        " square second, and the largest difference over ten seconds between its"
        " motion and the pendulum's from 2 rad, to two decimals.",
    )


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    equation = discover(experiment)
    experiment.number("found", equation.formula())
    experiment.number(
        "recovered", "recovered" if recovered(equation) else "not recovered"
    )
    experiment.number(
        "largest-error",
        100
        * max(abs(equation.coefficients.get(t, 0.0) / c - 1) for t, c in TRUE.items()),
        ".3f",
    )
    experiment.number("tolerance", 100 * TOLERANCE, "g")
    experiment.number("terms", len(polynomial_library(DEGREE)))
    experiment.number("samples", len(STARTS) * (round(DURATION / DT) - 1))

    t, truth, found = held_out(equation)
    experiment.number("held-out-error", float(np.max(np.abs(found - truth))), ".1e")
    experiment.number("held-out-amplitude", float(np.max(np.abs(truth))), ".1f")
    experiment.figure("fig-held-out", partial(draw_held_out, t, truth, found))

    single, several = one_orbit(experiment)
    floor = 1e-8
    experiment.number("bound", floor, ".0e")
    experiment.number("near-zero", int((single < floor).sum()))
    experiment.number("smallest-several", several[-1], ".2f")
    experiment.figure(
        "fig-singular-values", partial(draw_singular_values, single, several, floor)
    )
    pendulum(experiment)
    return experiment


if __name__ == "__main__":
    main(run)
