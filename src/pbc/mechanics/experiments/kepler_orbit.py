"""The experiment of the lesson "The Kepler orbit".

A planet on an ellipse of eccentricity one half about a fixed Sun
(``pbc.mechanics.orbit``) with four integrators: their errors and orders,
a thousand orbits, the precession of the perihelion, two bodies about their
centre of mass, Kepler's third law, escape, and the Sun and Jupiter. Run it
as a program to write the figures and numbers of the page:

    uv run --locked --no-dev python -m pbc.mechanics.experiments.kepler_orbit out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from scipy.constants import Julian_year, au

from pbc.authoring import FIGURE_COLOURS, diagrams
from pbc.experiment import Experiment, main
from pbc.figure_language import LINE, direct_label, figsize, figure_style, finish
from pbc.mechanics.dynamics import State, newton, simulate
from pbc.mechanics.energy import energy_drift, mechanical_energy
from pbc.mechanics.integrators import INTEGRATORS
from pbc.mechanics.orbit import (
    angular_momentum,
    central_gravity,
    eccentricity_vector,
    gravitational_attraction,
    gravitational_potential,
    kepler_motion,
    orbital_elements,
)
from pbc.mechanics.particles import (
    centre_of_mass,
    interacting,
    reduced_mass,
    stack,
    unstack,
)

euler, symplectic_euler, verlet, rk4 = INTEGRATORS

# region: setup
gm = 4 * np.pi**2  # G times one solar mass, in AU³/yr²
planet_mass = 3.0e-6  # solar masses: the Earth
gravity = newton(planet_mass, central_gravity(gm, planet_mass))
potential = gravitational_potential(gm, planet_mass)
FLOOR = 1e-12  # below this, a conserved quantity is shown as a bound
# endregion: setup


def at_perihelion(a, e):
    """At the closest point of the orbit with these elements, moving
    anticlockwise."""
    r = a * (1 - e)
    return State(t=0.0, x=[r, 0.0], v=[0.0, np.sqrt(gm * (1 + e) / r)])


# region: example
start = at_perihelion(1.0, 0.5)
ellipse = orbital_elements(start, gm)
metres_per_second = au / Julian_year  # one AU per year
perihelion_speed = np.linalg.norm(start.v) * metres_per_second / 1e3  # km/s
# endregion: example

# region: step-counts
step_counts = [200, 400, 800, 1600, 3200]
# endregion: step-counts
# region: thousand
n_orbits, steps_per_orbit = 1000, 100
# endregion: thousand


def draw_orbit_conserved_vectors() -> Figure:
    """The eccentricity and angular momentum vectors of the exact and of a
    turned orbit, as a sketch."""
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 3.2))
    eccentricity, semi_latus = 0.6, 1.0
    turn_simulated = np.radians(25.0)
    theta = np.linspace(0.0, 2.0 * np.pi, 300)
    radius = semi_latus / (1.0 + eccentricity * np.cos(theta))
    for ax, name, turn in zip(
        axes,
        ("Exact orbit", "Simulated orbit, turned"),
        (0.0, turn_simulated),
        strict=True,
    ):
        diagrams.frame(ax, (-2.9, 1.3), (-2.1, 1.9))
        ax.plot(
            radius * np.cos(theta),
            radius * np.sin(theta),
            color="#57606a",
            linestyle=":",
            linewidth=1.2,
        )
        ax.plot(
            radius * np.cos(theta + turn),
            radius * np.sin(theta + turn),
            color="#00429d",
            linewidth=1.6,
        )
        diagrams.circle(ax, (0.0, 0.0), 0.07, colour="#1f2328", filled=True)
        diagrams.arrow(
            ax, (0.0, 0.0), (1.0 * np.cos(turn), 1.0 * np.sin(turn)), colour=1
        )
        diagrams.text(
            ax,
            (1.1 * np.cos(turn) + 0.15, 1.1 * np.sin(turn) + 0.1),
            "$\\mathbf{e}$",
            colour=1,
        )
        diagrams.circle(ax, (-2.6, -1.8), 0.17, colour=2)
        diagrams.circle(ax, (-2.6, -1.8), 0.04, colour=2, filled=True)
        diagrams.text(ax, (-2.3, -1.8), "$\\mathbf{h}$", ha="left", colour=2)
        diagrams.text(ax, (-2.9, 1.6), name, ha="left")
    fig.tight_layout()
    return fig


def shown(spread):
    """A spread at the level of round-off is shown as a bound, not as a number."""
    return f"{spread:.1e}" if spread > FLOOR else "below 1e-12"


def run_orbits(integrator, steps_per_orbit, n_orbits, initial=start):
    return simulate(
        initial,
        gravity,
        ellipse.period / steps_per_orbit,
        round(n_orbits * steps_per_orbit),
        step=integrator.step,
    )


def position_error(trajectory, initial=start):
    """The largest distance from the exact position over the run, in AU."""
    exact = kepler_motion(initial, gm, trajectory.t)
    return np.max(np.hypot(*(trajectory.x - exact.x).T))


def four_methods_two_orbits(experiment: Experiment) -> None:
    """Two orbits at one hundred steps per orbit with each method; record the
    table."""
    rows = []
    for integrator in INTEGRATORS:
        trajectory = run_orbits(integrator, 100, 2)
        energies = mechanical_energy(trajectory, planet_mass, potential)
        momenta = angular_momentum(trajectory, planet_mass)
        rows.append(
            (
                integrator.name,
                position_error(trajectory),
                energy_drift(energies),
                shown(np.ptp(momenta) / momenta[0]),
            )
        )

    experiment.table(
        "four-methods-two-orbits",
        rows,
        columns=[
            ("method", "", ""),
            ("largest position error", "AU", ".1e"),
            ("energy drift", "", ".1e"),
            ("angular momentum spread", "", ""),
        ],
        caption="Two orbits at one hundred steps per orbit: position error, "
        "relative energy drift, and relative spread of the angular momentum; a "
        "spread at round-off level is shown as a bound.",
    )


def draw_orbit_four_methods() -> Figure:
    """Two orbits of each method against the exact ellipse."""
    with figure_style():
        exact_orbit = kepler_motion(start, gm, np.linspace(0.0, ellipse.period, 400))
        exact_colour, run_colour, star_colour = FIGURE_COLOURS[:3]

        fig, axes = plt.subplots(
            2, 2, figsize=figsize("square"), sharex=True, sharey=True
        )
        for ax, integrator in zip(axes.flat, INTEGRATORS, strict=True):
            trajectory = run_orbits(integrator, 100, 2)
            ax.plot(
                exact_orbit.x[:, 0],
                exact_orbit.x[:, 1],
                color=exact_colour,
                linestyle=":",
                linewidth=LINE["model"],
                label="exact",
            )
            ax.plot(
                trajectory.x[:, 0],
                trajectory.x[:, 1],
                color=run_colour,
                linewidth=LINE["guide"],
                label="two orbits",
            )
            ax.plot(0, 0, color=star_colour, marker="*", linestyle="none")
            ax.set_title(integrator.name)
            ax.set_xlim(-2.2, 1.2)
            ax.set_ylim(-1.6, 1.6)
            ax.set_aspect("equal")
        # Named once, in the first panel, where the curves lie apart.
        first = axes.flat[0]
        direct_label(
            first,
            -1.0,
            -0.87,
            "exact",
            exact_colour,
            offset=(0.0, -4.0),
            ha="center",
            va="top",
        )
        direct_label(
            first,
            -1.5,
            1.25,
            "two orbits",
            run_colour,
            offset=(0.0, 4.0),
            ha="center",
            va="bottom",
        )
        direct_label(
            first,
            0.0,
            0.0,
            "star",
            star_colour,
            offset=(-5.0, -3.0),
            ha="right",
            va="top",
        )
        for ax in axes[1]:
            ax.set_xlabel("x (AU)")
        for ax in axes[:, 0]:
            ax.set_ylabel("y (AU)")
    return finish(fig)


def observed_orders(experiment: Experiment) -> dict:
    """The largest position error over two orbits for each method and step
    count, with the observed order; record the table and return the
    errors."""
    errors = {
        integrator.name: np.array(
            [position_error(run_orbits(integrator, n, 2)) for n in step_counts]
        )
        for integrator in INTEGRATORS
    }

    columns = [("steps per orbit", "", "d")]
    for integrator in INTEGRATORS:
        columns += [
            (f"{integrator.name}: error", "AU", ".1e"),
            (f"{integrator.name}: order", "", ".2f"),
        ]
    rows = []
    for i, n in enumerate(step_counts):
        row = [n]
        for integrator in INTEGRATORS:
            error = errors[integrator.name]
            row += [error[i], np.log2(error[i - 1] / error[i]) if i else None]
        rows.append(row)

    experiment.table(
        "observed-orders",
        rows,
        columns=columns,
        caption="Largest position error over two orbits for each method, and the "
        "observed order from the previous row, to two decimals.",
    )
    return errors


def once_per_orbit(trajectory):
    """The state at the end of every orbit."""
    return [
        State(trajectory.t[i], trajectory.x[i], trajectory.v[i])
        for i in range(0, len(trajectory.t), steps_per_orbit)
    ]


def perihelion_direction(states):
    """The angle of the eccentricity vector, in degrees, unwrapped."""
    vectors = np.array([eccentricity_vector(state, gm) for state in states])
    return np.degrees(np.unwrap(np.arctan2(vectors[:, 1], vectors[:, 0])))


def thousand_orbits(experiment: Experiment):
    """A thousand orbits with velocity Verlet and Runge-Kutta 4; record the
    table and return the runs and their statistics."""
    long_runs = {
        integrator.name: run_orbits(integrator, steps_per_orbit, n_orbits)
        for integrator in (verlet, rk4)
    }

    long_stats = {}
    rows = []
    for integrator in (verlet, rk4):
        trajectory = long_runs[integrator.name]
        energies = mechanical_energy(trajectory, planet_mass, potential)
        momenta = angular_momentum(trajectory, planet_mass)
        axes_over_time = np.array(
            [
                orbital_elements(state, gm).semi_major_axis
                for state in once_per_orbit(trajectory)
            ]
        )
        turned = perihelion_direction(once_per_orbit(trajectory))
        long_stats[integrator.name] = {
            "axis_min": axes_over_time.min(),
            "axis_max": axes_over_time.max(),
            "turned": turned[-1] - turned[0],
        }
        rows.append(
            (
                integrator.name,
                energy_drift(energies[: 100 * steps_per_orbit + 1]),
                energy_drift(energies),
                shown(np.ptp(momenta) / momenta[0]),
                axes_over_time.min(),
                axes_over_time.max(),
                turned[-1] - turned[0],
                (turned[-1] - turned[0]) / n_orbits,
            )
        )

    experiment.table(
        "thousand-orbits",
        rows,
        columns=[
            ("method", "", ""),
            ("energy drift, first hundred orbits", "", ".1e"),
            ("energy drift, all orbits", "", ".1e"),
            ("angular momentum spread", "", ""),
            ("smallest semi-major axis", "AU", ".4f"),
            ("largest semi-major axis", "AU", ".4f"),
            ("perihelion turned in all", "degrees", "+.1f"),
            ("perihelion turned per orbit", "degrees", "+.3f"),
        ],
        caption="A thousand orbits at a hundred steps per orbit: energy drift over "
        "the first hundred and over all orbits, spread of the angular momentum, "
        "range of the semi-major axis at the end of each orbit, and the turn of "
        "the perihelion.",
    )
    return long_runs, long_stats


def draw_orbit_thousand(long_runs: dict) -> Figure:
    """The semi-major axis and the perihelion direction over a thousand
    orbits."""
    with figure_style():
        fig, (top, bottom) = plt.subplots(2, 1, figsize=figsize("stacked"), sharex=True)
        for integrator, style in ((verlet, "-"), (rk4, "--")):
            colour = FIGURE_COLOURS[1] if integrator is verlet else FIGURE_COLOURS[0]
            states = once_per_orbit(long_runs[integrator.name])
            orbit_number = np.arange(len(states))
            axis = [orbital_elements(state, gm).semi_major_axis for state in states]
            direction = perihelion_direction(states)
            top.plot(
                orbit_number, axis, color=colour, linestyle=style, label=integrator.name
            )
            bottom.plot(
                orbit_number,
                direction,
                color=colour,
                linestyle=style,
                label=integrator.name,
            )
        top.set_ylabel("semi-major axis (AU)")
        # Labels at the ends of the curves would sit on the spikes of the top
        # panel: one legend, where the curves leave room.
        top.legend(loc="lower left")
        bottom.set_xlabel("orbit")
        bottom.set_ylabel("perihelion direction (degrees)")
    return finish(fig, grid=True)


def precession_against_step(experiment: Experiment) -> None:
    """The precession of the perihelion per orbit for velocity Verlet at
    three steps; record the table."""
    rows, previous = [], None
    for n in (100, 200, 400):
        final = run_orbits(verlet, n, 50)
        turned = (
            perihelion_direction([State(final.t[-1], final.x[-1], final.v[-1])])[0] / 50
        )
        rows.append((n, turned, turned / previous if previous else None))
        previous = turned

    experiment.table(
        "precession-against-step",
        rows,
        columns=[
            ("steps per orbit", "", "d"),
            ("perihelion turned per orbit", "degrees", "+.4f"),
            ("ratio to the row above", "", ".3f"),
        ],
        caption="Precession of the perihelion per orbit for velocity Verlet over "
        "fifty orbits, for three steps, and its ratio to the coarser step.",
    )


def two_body_simulation(experiment: Experiment):
    """A heavy planet and its star as two bodies over five orbits, against
    the one-body run of their relative motion; record the table and return
    the positions and the speeds of the star, in m/s."""
    star_mass, heavy_planet = 1.0, 1.0e-3  # solar masses
    total_mass = star_mass + heavy_planet
    mu = reduced_mass(star_mass, heavy_planet)
    two_bodies = interacting(
        [star_mass, heavy_planet],
        gravitational_attraction(gm, star_mass, heavy_planet),
    )

    relative = State(
        t=0.0, x=[0.5, 0.0], v=[0.0, np.sqrt(gm * total_mass * 1.5 / 0.5)]
    )  # e = 0.5 again
    both = State(
        t=0.0,
        x=stack(
            [
                -heavy_planet / total_mass * relative.x,
                star_mass / total_mass * relative.x,
            ]
        ),
        v=stack(
            [
                -heavy_planet / total_mass * relative.v,
                star_mass / total_mass * relative.v,
            ]
        ),
    )
    pair_orbit = orbital_elements(relative, gm * total_mass)
    dt = pair_orbit.period / 200
    as_two = simulate(both, two_bodies, dt, 5 * 200, step=verlet.step)
    as_one = simulate(
        relative,
        newton(mu, central_gravity(gm * total_mass, mu)),
        dt,
        5 * 200,
        step=verlet.step,
    )

    positions, velocities = unstack(as_two.x, 2), unstack(as_two.v, 2)
    star_speed = np.linalg.norm(velocities[:, 0], axis=1) * metres_per_second
    centre_drift = np.max(np.abs(centre_of_mass([star_mass, heavy_planet], positions)))
    difference = np.max(np.abs((positions[:, 1] - positions[:, 0]) - as_one.x))
    bound = 1e-9  # AU, far above round-off and far below any other length

    experiment.table(
        "two-body-simulation",
        [
            ("period of the pair", "yr", f"{pair_orbit.period:.5f}"),
            (
                "drift of the centre of mass below the bound",
                "",
                "yes" if centre_drift < bound else "no",
            ),
            (
                "difference from the one-body run below the bound",
                "",
                "yes" if difference < bound else "no",
            ),
            ("slowest speed of the star", "m/s", f"{star_speed.min():.1f}"),
            ("fastest speed of the star", "m/s", f"{star_speed.max():.1f}"),
        ],
        columns=[("quantity", "", ""), ("unit", "", ""), ("value", "", "")],
        caption="The two bodies as two bodies over five orbits: the period, "
        "whether the centre of mass and the relative position agree with the "
        "one-body statements to a bound of 1e-9 AU, and the speed of the star.",
    )
    return positions, star_speed


def draw_two_bodies(positions) -> Figure:
    """The paths of the planet and of the star about the centre of mass."""
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(positions[:, 1, 0], positions[:, 1, 1], color="#93003a", label="planet")
    ax.plot(
        1000 * positions[:, 0, 0],
        1000 * positions[:, 0, 1],
        color="#00429d",
        linestyle="--",
        label="star, ×1000",  # noqa: RUF001, the multiplication sign
    )
    ax.plot(0, 0, color="#555555", marker="+", linestyle="none", label="centre of mass")
    ax.set_aspect("equal")
    ax.set_xlabel("x (AU)")
    ax.set_ylabel("y (AU)")
    ax.legend(loc="upper left")
    return fig


def third_law(experiment: Experiment) -> list:
    """Exercise 1: the period of circular orbits at four radii, measured from
    the crossings of the x axis; record the table and return its rows."""
    third_law_rows = []
    for a in (0.5, 1.0, 2.0, 4.0):
        circular = State(t=0.0, x=[a, 0.0], v=[0.0, np.sqrt(gm / a)])
        period = 2 * np.pi * np.sqrt(a**3 / gm)
        trajectory = simulate(
            circular, gravity, period / 200, 2 * 200 + 10, step=rk4.step
        )
        y = trajectory.x[:, 1]
        before = np.where((y[:-1] < 0) & (y[1:] >= 0))[0]
        crossing = trajectory.t[before] - y[before] / (y[before + 1] - y[before]) * (
            trajectory.t[before + 1] - trajectory.t[before]
        )
        third_law_rows.append((a, crossing[0], crossing[0] ** 2 / a**3))

    experiment.table(
        "third-law",
        third_law_rows,
        columns=[
            ("radius", "AU", ".1f"),
            ("measured period", "yr", ".4f"),
            ("T² / a³", "yr² / AU³", ".4f"),
        ],
        caption="Period of a circular orbit measured from the crossings of the x "
        "axis, and T² / a³, to four decimals.",
    )
    return third_law_rows


# region: escape
launch_distance = 0.5  # AU
escape_speed = np.sqrt(2 * gm / launch_distance)
# endregion: escape


def escape(experiment: Experiment) -> list:
    """Exercise 2: launches at 99 and 101 per cent of the escape speed;
    record the table and return its rows."""
    escape_rows = []
    for fraction in (0.99, 1.01):
        launched = State(
            t=0.0, x=[launch_distance, 0.0], v=[0.0, fraction * escape_speed]
        )
        trajectory = simulate(launched, gravity, 0.005, 6000, step=rk4.step)
        distance = np.hypot(*trajectory.x.T)
        try:
            elements = orbital_elements(launched, gm)
            axis, ecc, period_text = (
                elements.semi_major_axis,
                elements.eccentricity,
                f"{elements.period:.0f}",
            )
        except ValueError:
            axis, ecc, period_text = None, None, "not bound"
        escape_rows.append(
            (100 * fraction, distance[-1], distance.max(), axis, ecc, period_text)
        )

    experiment.table(
        "escape",
        escape_rows,
        columns=[
            ("launch speed", "per cent of escape", ".0f"),
            ("distance after thirty years", "AU", ".1f"),
            ("farthest distance", "AU", ".1f"),
            ("semi-major axis", "AU", ".1f"),
            ("eccentricity", "", ".3f"),
            ("period", "yr", ""),
        ],
        caption="Two launches from the perihelion of the example orbit, at 99 and "
        "at 101 per cent of the escape speed, and what orbital_elements reports.",
    )
    return escape_rows


def sun_and_jupiter(experiment: Experiment):
    """Exercise 3: the Sun and Jupiter as two bodies over one orbit; record
    the table and return the period, in yr, the speeds of the Sun, and the
    circular estimate, in m/s."""
    jupiter_mass, jupiter_a, jupiter_e = 0.000955, 5.20, 0.049
    total = 1.0 + jupiter_mass
    pair = interacting(
        [1.0, jupiter_mass], gravitational_attraction(gm, 1.0, jupiter_mass)
    )

    jupiter_r = jupiter_a * (1 - jupiter_e)
    jupiter_relative = State(
        t=0.0,
        x=[jupiter_r, 0.0],
        v=[0.0, np.sqrt(gm * total * (1 + jupiter_e) / jupiter_r)],
    )
    jupiter_both = State(
        t=0.0,
        x=stack(
            [
                -jupiter_mass / total * jupiter_relative.x,
                1.0 / total * jupiter_relative.x,
            ]
        ),
        v=stack(
            [
                -jupiter_mass / total * jupiter_relative.v,
                1.0 / total * jupiter_relative.v,
            ]
        ),
    )
    jupiter_period = orbital_elements(jupiter_relative, gm * total).period
    jupiter_run = simulate(
        jupiter_both, pair, jupiter_period / 400, 400, step=verlet.step
    )
    sun_speed = (
        np.linalg.norm(unstack(jupiter_run.v, 2)[:, 0], axis=1) * metres_per_second
    )
    circular_estimate = (
        jupiter_mass / total * np.sqrt(gm * total / jupiter_a) * metres_per_second
    )

    experiment.table(
        "sun-and-jupiter",
        [
            ("slowest speed of the Sun", sun_speed.min()),
            ("fastest speed of the Sun", sun_speed.max()),
            ("circular estimate", circular_estimate),
        ],
        columns=[("quantity", "", ""), ("speed", "m/s", ".1f")],
        caption="The speed of the Sun about the centre of mass of the Sun and "
        "Jupiter over one orbit, from the two-body simulation, and the circular "
        "estimate, to one decimal.",
    )
    return jupiter_period, sun_speed, circular_estimate


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.figure("fig-orbit-conserved-vectors", draw_orbit_conserved_vectors)

    four_methods_two_orbits(experiment)
    for name, value, spec in (
        ("semi-major-axis", ellipse.semi_major_axis, ".4f"),
        ("eccentricity", ellipse.eccentricity, ".4f"),
        ("period", ellipse.period, ".4f"),
        ("periapsis", ellipse.periapsis, ".2f"),
        ("perihelion-speed", perihelion_speed, ".1f"),
        ("apoapsis", ellipse.apoapsis, ".2f"),
    ):
        experiment.number(name, value, spec)
    experiment.figure("fig-orbit-four-methods", draw_orbit_four_methods)

    errors = observed_orders(experiment)
    experiment.number(
        "euler-error-in-axes",
        errors["explicit Euler"][-1] / ellipse.semi_major_axis,
        ".1f",
    )

    long_runs, long_stats = thousand_orbits(experiment)
    verlet_stats, rk4_stats = long_stats["velocity Verlet"], long_stats["Runge-Kutta 4"]
    experiment.number("verlet-axis-growth", 100 * (verlet_stats["axis_max"] - 1), ".1f")
    experiment.number("verlet-turns", abs(verlet_stats["turned"]) / 360, ".1f")
    experiment.number("rk4-axis-loss", 100 * (1 - rk4_stats["axis_min"]), ".1f")
    experiment.number("verlet-turned", abs(verlet_stats["turned"]), ".0f")
    experiment.figure("fig-orbit-thousand", partial(draw_orbit_thousand, long_runs))
    precession_against_step(experiment)

    positions, star_speed = two_body_simulation(experiment)
    experiment.number("star-slowest", star_speed.min(), ".0f")
    experiment.number("star-fastest", star_speed.max(), ".0f")
    experiment.figure("fig-two-bodies", partial(draw_two_bodies, positions))

    third_law_rows = third_law(experiment)
    experiment.number(
        "third-law-mean", np.mean([row[2] for row in third_law_rows]), ".4f"
    )
    escape_rows = escape(experiment)
    experiment.number("escape-speed", escape_speed, ".3f")
    experiment.number(
        "escape-speed-km-s", escape_speed * metres_per_second / 1e3, ".1f"
    )
    experiment.number("bound-period", f"{escape_rows[0][5]}")

    jupiter_period, sun_speed, circular_estimate = sun_and_jupiter(experiment)
    experiment.number("jupiter-period", jupiter_period, ".2f")
    experiment.number("sun-slowest", sun_speed.min(), ".1f")
    experiment.number("sun-fastest", sun_speed.max(), ".1f")
    experiment.number("circular-estimate", circular_estimate, ".1f")
    experiment.number("jupiter-period-years", jupiter_period, ".0f")
    return experiment


if __name__ == "__main__":
    main(run)
