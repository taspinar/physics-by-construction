"""The experiment of the lesson "Hamiltonian mechanics".

The Hamiltonian by the Legendre transform, the volume of phase space that a
step keeps or changes, and the modified energy that the symplectic methods
conserve (``pbc.mechanics.hamiltonian``). Run it as a program to write the
figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.hamiltonian_mechanics out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from scipy.constants import g

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.figure_language import direct_label, figsize, figure_style, finish
from pbc.mechanics.dynamics import State, euler_step, newton, simulate
from pbc.mechanics.energy import mechanical_energy
from pbc.mechanics.hamiltonian import (
    legendre_hamiltonian,
    loop_area,
    step_jacobian,
    symplectic_euler_modified_energy,
    verlet_oscillator_modified_energy,
)
from pbc.mechanics.integrators import rk4_step, symplectic_euler_step, verlet_step
from pbc.mechanics.lagrangian import coupled_springs_lagrangian, pendulum_lagrangian
from pbc.mechanics.oscillator import spring
from pbc.mechanics.pendulum import (
    pendulum_force,
    pendulum_potential,
    small_angle_period,
)

METHODS = (
    ("explicit Euler", euler_step),
    ("symplectic Euler", symplectic_euler_step),
    ("velocity Verlet", verlet_step),
    ("classical Runge-Kutta", rk4_step),
)
# region: pendulum
pendulum = newton(1.0, pendulum_force(1.0, 1.0))
t0 = small_angle_period(1.0)
# endregion: pendulum
# region: oscillator
mass, k = 0.5, 2.0
period = 2.0 * np.pi / np.sqrt(k / mass)
oscillator = newton(mass, spring(k))
dt = period / 16
ROUND_OFF = 1e-12
# endregion: oscillator


def legendre() -> float:
    """The Hamiltonian of the pendulum and of the coupled springs, written in
    the momenta and from the Legendre transform; the bound the two agree
    within, in J."""
    rows = []
    pendulum_h = legendre_hamiltonian(pendulum_lagrangian(1.0, 1.0))
    for angle, momentum in ((0.5, 1.0), (1.5, -0.8), (2.5, 2.0)):
        from_program = pendulum_h(np.array([angle]), np.array([momentum]))
        closed = 0.5 * momentum**2 - g * np.cos(angle)
        rows.append(("pendulum", angle, momentum, closed, from_program))

    springs_h = legendre_hamiltonian(coupled_springs_lagrangian(0.5, 4.0, 1.5))
    q, p = np.array([0.3, -0.2]), np.array([0.4, 0.1])
    closed = p @ p / (2 * 0.5) + 0.5 * 4.0 * q @ q + 0.5 * 1.5 * (q[0] - q[1]) ** 2
    rows.append(("two springs", q[0], p[0], closed, springs_h(q, p)))

    bound = 1e-12  # J, far above round-off for numbers of this size
    assert max(abs(r[3] - r[4]) for r in rows) < bound
    return bound


FLOOR = 1e-8  # the Jacobian is found to about one part in ten billion


def shown(value):
    """A deviation at the level of the numerical derivative is shown as a
    bound."""
    return f"{value:.1e}" if abs(value) > FLOOR else "below 1e-8"


def determinants(experiment: Experiment):
    """The determinant of the Jacobian of one step, minus one, for four
    methods at two steps, and the formula for explicit Euler; record the
    table."""
    point = State(0.0, [1.1], [0.4])
    curvature = g * np.cos(1.1)  # U'' for the unit pendulum
    steps = (0.1, 0.5)  # s
    deviations = {}
    for name, step in METHODS:
        deviations[name] = [
            np.linalg.det(step_jacobian(step, point, pendulum, dt)) - 1.0
            for dt in steps
        ]
    euler_formula = [curvature * dt**2 for dt in steps]

    experiment.table(
        "determinants",
        [(name, *(shown(d) for d in values)) for name, values in deviations.items()],
        columns=[
            ("method", "", ""),
            ("determinant minus one, step 0.1 s", "", ""),
            ("determinant minus one, step 0.5 s", "", ""),
        ],
        caption="The determinant of the Jacobian of one step, minus one, for four "
        "methods on the pendulum at an angle of one and a tenth radians and a "
        "velocity of four tenths, at two step lengths; a deviation at the level "
        "of the numerical derivative is shown as a bound.",
    )
    return deviations, euler_formula


def blob(experiment: Experiment):
    """A circle of starting states after two small-angle periods with each
    method, and the area it encloses; record the table and return the
    starting circle, its images, and the rows."""
    angles = np.linspace(0.0, 2.0 * np.pi, 120, endpoint=False)
    x_start, v_start = 1.2 + 0.1 * np.cos(angles), 0.1 * np.sin(angles)
    area_start = loop_area(x_start, v_start)

    images, rows = {}, []
    for name, step in METHODS:
        ends = [
            simulate(State(0.0, [a], [b]), pendulum, t0 / 50, 100, step=step)
            for a, b in zip(x_start, v_start, strict=True)
        ]
        x_end = np.array([e.x[-1, 0] for e in ends])
        v_end = np.array([e.v[-1, 0] for e in ends])
        images[name] = (x_end, v_end)
        rows.append((name, loop_area(x_end, v_end) / area_start))

    experiment.table(
        "blob",
        rows,
        columns=[
            ("method", "", ""),
            ("area after two periods / starting area", "", ".5f"),
        ],
        caption="The area enclosed by the images of a circle of starting states "
        "of the pendulum after two small-angle periods, relative to the starting "
        "area, to five decimals.",
    )
    return x_start, v_start, images, rows


def closed_loop(x, v):
    return np.append(x, x[0]), np.append(v, v[0])


def draw_phase_blob(x_start, v_start, images) -> Figure:
    """The starting circle and its images after two periods, each named
    beside its curve."""
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line"))
        curves = (
            ("start", (x_start, v_start), FIGURE_COLOURS[0], "-"),
            ("symplectic Euler", images["symplectic Euler"], FIGURE_COLOURS[1], "--"),
            ("explicit Euler", images["explicit Euler"], FIGURE_COLOURS[2], ":"),
        )
        for name, (x, v), colour, style in curves:
            ax.plot(*closed_loop(x, v), color=colour, linestyle=style, label=name)
            if name == "start":
                # Above the small circle, where there is room.
                top = int(np.argmax(v))
                direct_label(
                    ax,
                    x[top],
                    v[top],
                    name,
                    colour,
                    offset=(0.0, 4.0),
                    ha="center",
                    va="bottom",
                )
            else:
                right = int(np.argmax(x))
                direct_label(ax, x[right], v[right], name, colour, offset=(6.0, 0.0))
        ax.set_xlabel("angle (rad)")
        ax.set_ylabel("angular velocity (rad/s)")
    return finish(fig)


def potential(x):
    return 0.5 * k * float(x @ x)


def gradient(x):
    return k * x


def spread(values):
    return np.max(np.abs(values / values[0] - 1.0))


def conserved(value):
    """A spread at the level of round-off is shown as a bound, not as a
    number."""
    return f"{value:.1e}" if value > ROUND_OFF else "below 1e-12"


def modified_oscillator(experiment: Experiment):
    """Twenty periods of the oscillator with the two symplectic methods: the
    spread of the energy and of the modified energy; record the table and
    return the symplectic Euler run and the rows."""
    se_run = simulate(
        State(0.0, [1.0], [0.0]), oscillator, dt, 320, step=symplectic_euler_step
    )
    vv_run = simulate(State(0.0, [1.0], [0.0]), oscillator, dt, 320, step=verlet_step)

    rows = [
        (
            "symplectic Euler",
            spread(mechanical_energy(se_run, mass, potential)),
            spread(
                symplectic_euler_modified_energy(se_run, mass, potential, gradient, dt)
            ),
        ),
        (
            "velocity Verlet",
            spread(mechanical_energy(vv_run, mass, potential)),
            spread(verlet_oscillator_modified_energy(vv_run, mass, k, dt)),
        ),
    ]
    assert all(row[2] < ROUND_OFF for row in rows)

    experiment.table(
        "modified-oscillator",
        [
            (name, energy_spread, conserved(modified_spread))
            for name, energy_spread, modified_spread in rows
        ],
        columns=[
            ("method", "", ""),
            ("spread of the energy", "", ".1e"),
            ("spread of the modified energy", "", ""),
        ],
        caption="The largest relative deviation from the starting value of the "
        "energy and of the modified energy over twenty periods of the oscillator, "
        "two symplectic methods.",
    )
    return se_run, rows


# region: pendulum-energy
potential_p = pendulum_potential(1.0, 1.0)
# endregion: pendulum-energy


def gradient_p(x):
    return g * np.sin(x)


def modified_pendulum(experiment: Experiment):
    """The band of the energy and of the modified energy of symplectic Euler
    on the pendulum at three steps; record the table and return the runs
    and the rows."""
    rows, runs = [], {}
    for per_period in (50, 100, 200):
        step = t0 / per_period
        trajectory = simulate(
            State(0.0, [1.0], [0.0]),
            pendulum,
            step,
            20 * per_period,
            step=symplectic_euler_step,
        )
        energy = mechanical_energy(trajectory, 1.0, potential_p)
        modified = symplectic_euler_modified_energy(
            trajectory, 1.0, potential_p, gradient_p, step
        )
        runs[per_period] = (trajectory, energy, modified)
        rows.append(
            [per_period, np.ptp(energy) / energy[0], np.ptp(modified) / energy[0]]
        )
    for i in (1, 2):
        rows[i] += [rows[i - 1][1] / rows[i][1], rows[i - 1][2] / rows[i][2]]
    rows[0] += [None, None]

    experiment.table(
        "modified-pendulum",
        rows,
        columns=[
            ("steps per period", "", "d"),
            ("band of the energy", "", ".1e"),
            ("band of the modified energy", "", ".1e"),
            ("energy: ratio for a halved step", "", ".2f"),
            ("modified energy: ratio for a halved step", "", ".2f"),
        ],
        caption="The width of the band of the energy and of the modified energy of "
        "symplectic Euler on the pendulum over twenty periods, relative to the "
        "starting energy, with the ratio of the widths for a halved step.",
    )
    return runs, rows


def draw_modified_energy_pendulum(runs) -> Figure:
    """The energy and the modified energy over six periods."""
    trajectory, energy, modified = runs[100]
    early = trajectory.t <= 6.0 * t0
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.plot(
        trajectory.t[early],
        (energy - energy[0])[early],
        color=FIGURE_COLOURS[0],
        linestyle="-",
        label="energy",
    )
    ax.plot(
        trajectory.t[early],
        (modified - modified[0])[early],
        color=FIGURE_COLOURS[1],
        linestyle="--",
        label="modified energy",
    )
    ax.set_xlabel("time (s)")
    ax.set_ylabel("deviation from the start (J)")
    ax.legend(loc="upper right")
    return fig


def long_run(experiment: Experiment) -> float:
    """Exercise 1: three hundred periods of the pendulum with velocity Verlet
    and Runge-Kutta 4; record the table and return the period, in
    small-angle periods, at which the drift of Runge-Kutta passes the band of
    Verlet."""
    steps = 20
    long_runs = {
        name: simulate(
            State(0.0, [1.2], [0.0]), pendulum, t0 / steps, 300 * steps, step=step
        )
        for name, step in (
            ("velocity Verlet", verlet_step),
            ("classical Runge-Kutta", rk4_step),
        )
    }
    drifts = {}
    for name, trajectory in long_runs.items():
        e = mechanical_energy(trajectory, 1.0, potential_p)
        drifts[name] = np.maximum.accumulate(np.abs(e - e[0]) / abs(e[0]))
    band = drifts["velocity Verlet"][-1]
    crossing = (
        long_runs["velocity Verlet"].t[
            np.argmax(drifts["classical Runge-Kutta"] > band)
        ]
        / t0
    )

    experiment.table(
        "long-run",
        [
            (
                "velocity Verlet",
                drifts["velocity Verlet"][len(drifts["velocity Verlet"]) // 30],
                band,
            ),
            (
                "classical Runge-Kutta",
                drifts["classical Runge-Kutta"][
                    len(drifts["classical Runge-Kutta"]) // 30
                ],
                drifts["classical Runge-Kutta"][-1],
            ),
        ],
        columns=[
            ("method", "", ""),
            ("drift after ten periods", "", ".1e"),
            ("drift after three hundred periods", "", ".1e"),
        ],
        caption="The largest relative deviation of the energy from its start for "
        "velocity Verlet and the classical Runge-Kutta method, after ten and after "
        "three hundred periods of the pendulum at twenty steps per period.",
    )
    return crossing


def sign_of_the_correction(experiment: Experiment, se_run) -> float:
    """Exercise 2: the spread of the energy with the correction subtracted
    and added; record the table and return the spread with the wrong sign
    over that of the energy."""
    wrong = mechanical_energy(se_run, mass, potential) + 0.5 * dt * np.array(
        [gradient(x) @ v for x, v in zip(se_run.x, se_run.v, strict=True)]
    )
    right = symplectic_euler_modified_energy(se_run, mass, potential, gradient, dt)
    plain = mechanical_energy(se_run, mass, potential)

    experiment.table(
        "sign-of-the-correction",
        [
            ("energy", spread(plain)),
            ("minus the correction", spread(right)),
            ("plus the correction", spread(wrong)),
        ],
        columns=[("quantity", "", ""), ("spread", "", ".1e")],
        caption="The spread of the energy and of the energy with the correction of "
        "the explanation subtracted and added, symplectic Euler on the "
        "oscillator.",
    )
    return spread(wrong) / spread(plain)


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.number("bound", legendre(), ".0e")

    deviations, euler_formula = determinants(experiment)
    experiment.number("euler-short", deviations["explicit Euler"][0], ".2e")
    experiment.number("euler-long", deviations["explicit Euler"][1], ".2e")
    experiment.number("formula-short", euler_formula[0], ".2e")
    experiment.number("formula-long", euler_formula[1], ".2e")
    experiment.number("rk4-long", abs(deviations["classical Runge-Kutta"][1]), ".0e")

    x_start, v_start, images, rows = blob(experiment)
    experiment.number("euler-area", rows[0][1], ".2f")
    experiment.number("symplectic-area", rows[1][1], ".4f")
    experiment.number("verlet-area", rows[2][1], ".4f")
    experiment.number("rk4-area", abs(rows[3][1] - 1.0), ".0e")
    experiment.figure(
        "fig-phase-blob", partial(draw_phase_blob, x_start, v_start, images)
    )

    se_run, rows = modified_oscillator(experiment)
    experiment.number("round-off", ROUND_OFF, ".0e")
    experiment.number("symplectic-energy-spread", rows[0][1], ".2f")
    experiment.number("verlet-energy-spread", rows[1][1], ".3f")

    runs, rows = modified_pendulum(experiment)
    experiment.number("energy-ratio", rows[2][3], ".2f")
    experiment.number("modified-ratio", rows[2][4], ".2f")
    experiment.figure(
        "fig-modified-energy-pendulum", partial(draw_modified_energy_pendulum, runs)
    )

    experiment.number("crossing", long_run(experiment), ".0f")
    experiment.number(
        "wrong-over-plain", sign_of_the_correction(experiment, se_run), ".1f"
    )
    return experiment


if __name__ == "__main__":
    main(run)
