"""The experiment of the lesson "Many-body gravitation".

Bodies under their mutual gravity (``pbc.mechanics.nbody``): the two-body
case against the exact Kepler motion, the drift of the energy and the
angular momentum of a Sun, Jupiter, and Saturn system for each integrator of
the course over a thousand years, the figure-eight orbit of three equal
masses, and Jupiter's pull on Saturn. Run it as a program to write the
figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.many_body_gravitation out
"""

import itertools
from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.mechanics.dynamics import State, simulate
from pbc.mechanics.integrators import INTEGRATORS, rk4_step, verlet_step
from pbc.mechanics.nbody import (
    angular_momentum,
    barycentric,
    gravity,
    total_energy,
)
from pbc.mechanics.orbit import kepler_motion, orbital_elements
from pbc.mechanics.particles import unstack
from pbc.verification.estimates import convergence_table, invariant_band

# region: setup
G = 4 * np.pi**2  # AU³ / (M_sun yr²): one solar mass gives GM = 4 pi²
sun, jupiter, saturn = 1.0, 9.547e-4, 2.858e-4  # masses, M_sun
jupiter_radius, saturn_radius = 5.20, 9.58  # starting distances from the Sun, AU
FLOOR = 1e-12  # below this, a relative drift is shown as a bound
# endregion: setup

# region: long-run
dt, years = 0.05, 1200.0  # yr
# endregion: long-run

# region: figure-eight
# The figure-eight orbit of three equal masses with G = 1 (Chenciner and
# Montgomery, 2000), from the initial conditions published by Simó, to
# eight digits: two bodies opposite each other, the third at the centre.
x1 = np.array([0.97000436, -0.24308753])
v3 = np.array([-0.93240737, -0.86473146])
# endregion: figure-eight


def shown(drift):
    """A drift at the level of round-off is shown as a bound, not as a number."""
    return f"{drift:.1e}" if drift > FLOOR else "below 1e-12"


def bound(value, limit):
    """A value at the level of round-off is shown as below ``limit``."""
    return f"{value:.1e}" if value > limit else f"below {limit:.0e}"


def circular_speed(radius, mass):
    """The speed in AU/yr of a body of ``mass`` (M_sun) on a circular orbit of
    ``radius`` (AU) about the Sun, when the two are alone."""
    return np.sqrt(G * (sun + mass) / radius)


def solar_system(with_jupiter=True):
    """The Sun, Jupiter, and Saturn at the start, on circular speeds about
    the Sun, Jupiter a quarter turn behind Saturn, in the centre-of-mass
    frame; without Jupiter, the Sun and Saturn alone."""
    bodies = [
        (sun, [0.0, 0.0], [0.0, 0.0]),
        (
            jupiter,
            [jupiter_radius, 0.0],
            [0.0, circular_speed(jupiter_radius, jupiter)],
        ),
        (saturn, [0.0, saturn_radius], [-circular_speed(saturn_radius, saturn), 0.0]),
    ]
    if not with_jupiter:
        bodies.pop(1)
    masses = [m for m, _, _ in bodies]
    return masses, barycentric(
        masses, [x for _, x, _ in bodies], [v for _, _, v in bodies]
    )


def two_body_check(experiment: Experiment):
    """A star and a planet of a thousandth of its mass on an ellipse of
    eccentricity one half, five orbits with velocity Verlet at three steps,
    against the exact Kepler motion of the relative position; record the
    table and return the rows."""
    masses = [1.0, 1.0e-3]
    gm = G * sum(masses)
    a, e = 1.0, 0.5
    perihelion = a * (1 - e)
    speed = np.sqrt(gm * (1 + e) / perihelion)
    start = barycentric(
        masses, [[0.0, 0.0], [perihelion, 0.0]], [[0.0, 0.0], [0.0, speed]]
    )
    relative = State(t=0.0, x=[perihelion, 0.0], v=[0.0, speed])
    period = orbital_elements(relative, gm).period

    steps, errors = [], []
    for per_orbit in (400, 800, 1600):
        run = simulate(
            start,
            gravity(G, masses),
            period / per_orbit,
            5 * per_orbit,
            step=verlet_step,
        )
        bodies = unstack(run.x, 2)
        exact = kepler_motion(relative, gm, run.t)
        errors.append(np.max(np.hypot(*(bodies[:, 1] - bodies[:, 0] - exact.x).T)))
        steps.append(period / per_orbit)

    rows = convergence_table(steps, errors)
    experiment.table(
        "two-body-check",
        [(round(period / h), h, error, order) for h, error, order in rows],
        columns=[
            ("steps per orbit", "", "d"),
            ("time step", "yr", ".6f"),
            ("largest error of the relative position", "AU", ".2e"),
            ("observed order", "", ".2f"),
        ],
        caption="The relative position of two bodies simulated as a many-body "
        "system with velocity Verlet over five orbits, against the exact Kepler "
        "motion, for three time steps.",
    )
    return rows


def long_run(integrator):
    """The Sun, Jupiter, and Saturn over ``years`` with one integrator."""
    masses, start = solar_system()
    return masses, simulate(
        start, gravity(G, masses), dt, round(years / dt), step=integrator.step
    )


def drift_per_integrator(experiment: Experiment):
    """The relative drift of the energy and of the angular momentum of the
    Sun, Jupiter, and Saturn for each integrator over ``years``; record the
    table and return, per integrator, the times and the relative energy
    error."""
    rows, curves = [], []
    for integrator in INTEGRATORS:
        masses, run = long_run(integrator)
        energy = total_energy(G, masses, run)
        momentum = angular_momentum(masses, run)
        tenth = len(run.t) // 10
        early, late = invariant_band(energy, slice(0, tenth), slice(-tenth, None))
        rows.append(
            (
                integrator.name,
                integrator.evaluations,
                early,
                late,
                shown(np.max(np.abs(momentum / momentum[0] - 1.0))),
            )
        )
        # The largest error within each window of a hundred steps: the
        # envelope of the oscillation, which shows a band as a band.
        error = np.abs(energy[1:] / energy[0] - 1.0).reshape(-1, 100).max(axis=1)
        curves.append((integrator.name, run.t[100::100], error))

    experiment.table(
        "drift-per-integrator",
        rows,
        columns=[
            ("integrator", "", ""),
            ("evaluations per step", "", "d"),
            ("energy drift, first tenth", "", ".1e"),
            ("energy drift, last tenth", "", ".1e"),
            ("angular momentum drift, whole run", "", ""),
        ],
        caption="The largest relative change of the total energy within the first "
        "and within the last tenth of a twelve-hundred-year run of the Sun, Jupiter, "
        "and Saturn, and of the total angular momentum over the whole run, for each "
        "integrator at the same time step.",
    )
    return curves


def draw_energy_drift(curves) -> Figure:
    """The relative energy error over time, one curve per integrator."""
    styles = [("-", None), ("--", None), ("-", "o"), (":", "s")]
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    for (name, t, error), (line, marker), colour in zip(
        curves, styles, FIGURE_COLOURS, strict=False
    ):
        ax.plot(
            t,
            error,
            color=colour,
            linestyle=line,
            marker=marker,
            markevery=24,
            markersize=4,
            label=name,
        )
    ax.set_yscale("log")
    ax.set_xlabel("time (yr)")
    ax.set_ylabel("relative energy error, largest per 5 yr")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncols=2, fontsize="small")
    return fig


def figure_eight_start(scale=1.0):
    """The figure-eight start, with the velocities multiplied by ``scale``."""
    return State(
        t=0.0,
        x=np.concatenate([x1, -x1, [0.0, 0.0]]),
        v=scale * np.concatenate([-v3 / 2, -v3 / 2, v3]),
    )


def figure_eight(experiment: Experiment):
    """The period of the figure-eight, measured as the time at which the
    state comes back; the closure after one period and the permutation of
    the bodies after a third of it; record the table and return the run of
    one period."""
    start = figure_eight_start()
    masses = [1.0, 1.0, 1.0]
    acceleration = gravity(1.0, masses)

    # A first pass finds the step nearest to the return, a parabola through
    # the squared distance at the three steps around it refines the time.
    scan = simulate(start, acceleration, 0.002, 3500, step=rk4_step)
    distance = np.sum((scan.x - start.x) ** 2, axis=1) + np.sum(
        (scan.v - start.v) ** 2, axis=1
    )
    i = np.argmin(np.where(scan.t > 3.0, distance, np.inf))
    a, b, _ = np.polyfit(scan.t[i - 1 : i + 2], distance[i - 1 : i + 2], 2)
    period = -b / (2 * a)

    steps = 3000
    run = simulate(start, acceleration, period / steps, steps, step=rk4_step)
    closure = np.max(np.abs(run.x[-1] - start.x))
    bodies = unstack(run.x, 3)
    third = bodies[steps // 3]
    first = unstack(start.x, 3)
    permutations = {
        p: np.max(np.abs(third - first[list(p)]))
        for p in itertools.permutations(range(3))
    }
    best = min(permutations, key=permutations.get)
    energy = total_energy(1.0, masses, run)
    momentum = angular_momentum(masses, run)

    experiment.table(
        "figure-eight",
        [
            ("measured period", f"{period:.4f}"),
            ("largest coordinate difference after one period", f"{closure:.1e}"),
            (
                "largest difference after a third, bodies relabelled",
                f"{permutations[best]:.1e}",
            ),
            (
                "largest difference after a third, bodies not relabelled",
                f"{permutations[(0, 1, 2)]:.2f}",
            ),
            (
                "largest change of the energy",
                bound(np.max(np.abs(energy - energy[0])), 1e-10),
            ),
            ("largest total angular momentum", bound(np.max(np.abs(momentum)), 1e-10)),
        ],
        columns=[("quantity", "", ""), ("value", "", "")],
        caption="The figure-eight orbit of three equal masses with G = 1, simulated "
        "with the classical Runge-Kutta method in three thousand steps per period: "
        "its measured period, how closely it closes, and its conserved quantities, "
        "in the units of the problem.",
    )
    return run, period, best, closure, permutations[best]


def draw_figure_eight(run) -> Figure:
    """The path of one period of the figure-eight, which all three bodies
    trace, with the bodies at the start (filled) and a twelfth of a period
    later (open)."""
    bodies = unstack(run.x, 3)
    later = len(run.t) // 12
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    for k in range(3):
        ax.plot(
            bodies[:, k, 0],
            bodies[:, k, 1],
            color="#57606a",
            linestyle="-",
            linewidth=1.0,
            label="the path of every body" if k == 0 else None,
        )
    for k, marker in enumerate(("o", "s", "^")):
        ax.plot(
            bodies[0, k, 0],
            bodies[0, k, 1],
            color=FIGURE_COLOURS[k],
            marker=marker,
            markersize=9,
            linestyle="",
            label=f"body {k + 1}",
        )
        ax.plot(
            bodies[later, k, 0],
            bodies[later, k, 1],
            color=FIGURE_COLOURS[k],
            marker=marker,
            markersize=9,
            markerfacecolor="white",
            linestyle="",
        )
    ax.set_aspect("equal")
    ax.set_xlabel("x (units of the problem)")
    ax.set_ylabel("y (units of the problem)")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncols=4, fontsize="small")
    return fig


def draw_solar_system() -> Figure:
    """The paths of Jupiter and Saturn over one Saturn year, and the path of
    the Sun about the centre of mass, enlarged."""
    masses, start = solar_system()
    run = simulate(start, gravity(G, masses), dt, 600, step=verlet_step)
    bodies = unstack(run.x, 3)
    fig, (left, right) = plt.subplots(1, 2, figsize=(6.4, 3.4))
    for k, (name, line) in enumerate((("Jupiter", "--"), ("Saturn", ":")), start=1):
        left.plot(
            bodies[:, k, 0],
            bodies[:, k, 1],
            color=FIGURE_COLOURS[k],
            linestyle=line,
            label=name,
        )
    left.plot(0.0, 0.0, color=FIGURE_COLOURS[0], marker="o", linestyle="", label="Sun")
    left.set_aspect("equal")
    left.set_xlabel("x (AU)")
    left.set_ylabel("y (AU)")
    left.legend(
        loc="lower center", bbox_to_anchor=(0.5, 1.0), ncols=3, fontsize="small"
    )
    right.plot(
        1e3 * bodies[:, 0, 0],
        1e3 * bodies[:, 0, 1],
        color=FIGURE_COLOURS[0],
        linestyle="-",
    )
    right.plot(0.0, 0.0, color="#57606a", marker="+", markersize=10, linestyle="")
    right.set_aspect("equal")
    right.set_xlabel("x of the Sun (0.001 AU)")
    right.set_ylabel("y of the Sun (0.001 AU)")
    fig.tight_layout()
    return fig


def halved_step(experiment: Experiment):
    """Exercise 1: the energy band of velocity Verlet over a hundred years
    at the step of the lesson, half of it, and a quarter of it; record the
    table and return the ratios of successive bands."""
    masses, start = solar_system()
    steps, bands = (dt, dt / 2, dt / 4), []
    for step in steps:
        run = simulate(
            start, gravity(G, masses), step, round(100 / step), step=verlet_step
        )
        energy = total_energy(G, masses, run)
        bands.append(np.max(np.abs(energy / energy[0] - 1.0)))
    ratios = [None] + [bands[i - 1] / bands[i] for i in range(1, 3)]

    experiment.table(
        "halved-step",
        list(zip(steps, bands, ratios, strict=True)),
        columns=[
            ("time step", "yr", ".4f"),
            ("largest relative energy change", "", ".2e"),
            ("ratio to the previous step", "", ".2f"),
        ],
        caption="The band of the relative energy of the Sun, Jupiter, and Saturn "
        "under velocity Verlet over a hundred years, at three time steps.",
    )
    return ratios[1:]


def saturn_eccentricity(with_jupiter):
    """The eccentricity of Saturn's orbit about the Sun at every year of
    three hundred, from Saturn's position and velocity relative to the Sun."""
    masses, start = solar_system(with_jupiter)
    run = simulate(start, gravity(G, masses), dt, round(300 / dt), step=verlet_step)
    bodies, velocities = unstack(run.x, len(masses)), unstack(run.v, len(masses))
    gm = G * (sun + saturn)
    return np.array(
        [
            orbital_elements(
                State(
                    0.0,
                    bodies[i, -1] - bodies[i, 0],
                    velocities[i, -1] - velocities[i, 0],
                ),
                gm,
            ).eccentricity
            for i in range(0, len(run.t), round(1 / dt))
        ]
    )


def jupiter_on_saturn(experiment: Experiment):
    """Exercise 2: the range of Saturn's eccentricity with and without
    Jupiter; record the table and return the two ranges."""
    ranges = []
    for with_jupiter in (False, True):
        e = saturn_eccentricity(with_jupiter)
        ranges.append((np.min(e), np.max(e)))

    experiment.table(
        "jupiter-on-saturn",
        [
            ("Sun and Saturn", ranges[0][0], ranges[0][1]),
            ("Sun, Jupiter, and Saturn", ranges[1][0], ranges[1][1]),
        ],
        columns=[
            ("system", "", ""),
            ("smallest eccentricity", "", ".4f"),
            ("largest eccentricity", "", ".4f"),
        ],
        caption="The eccentricity of Saturn's orbit about the Sun, read once a year "
        "over three hundred years, with and without Jupiter, to four decimals.",
    )
    return ranges


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.figure("fig-solar-system", draw_solar_system)

    rows = two_body_check(experiment)
    experiment.number("two-body-order", rows[-1][2], ".2f")
    experiment.number("two-body-error", rows[-1][1], ".0e")

    curves = drift_per_integrator(experiment)
    experiment.figure("fig-energy-drift", partial(draw_energy_drift, curves))
    experiment.number(
        "orbits-of-jupiter",
        years / (2 * np.pi * np.sqrt(jupiter_radius**3 / (G * sun))),
        ".0f",
    )

    run_eight, period, best, closure, permuted = figure_eight(experiment)
    experiment.figure("fig-figure-eight", partial(draw_figure_eight, run_eight))
    experiment.number("period", period, ".4f")
    experiment.number("closure", closure, ".0e")
    experiment.number("permuted", permuted, ".0e")
    experiment.number("relabelling", " → ".join(str(k + 1) for k in best))

    ratios = halved_step(experiment)
    experiment.number("halved-ratio", ratios[0], ".2f")
    experiment.number("quartered-ratio", ratios[1], ".2f")
    ranges = jupiter_on_saturn(experiment)
    experiment.number("saturn-alone", ranges[0][1] - ranges[0][0], ".0e")
    experiment.number("saturn-with-jupiter", ranges[1][1] - ranges[1][0], ".3f")
    return experiment


if __name__ == "__main__":
    main(run)
