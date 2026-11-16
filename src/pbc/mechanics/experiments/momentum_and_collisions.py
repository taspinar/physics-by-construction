"""The experiment of the lesson "Momentum and collisions".

Two masses on a spring, and soft spheres colliding head on, glancing, in a
row, and in the frame of the centre of mass (``pbc.mechanics.particles``),
against the hard-sphere formulas. Run it as a program to write the figures
and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.momentum_and_collisions out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS, diagrams
from pbc.experiment import Experiment, main
from pbc.figure_language import LINE, direct_label, figsize, figure_style, finish
from pbc.mechanics.dynamics import State, simulate
from pbc.mechanics.integrators import INTEGRATORS
from pbc.mechanics.oscillator import harmonic_motion
from pbc.mechanics.particles import (
    centre_of_mass,
    first_contact,
    hard_sphere_collision,
    interacting,
    kinetic_energy,
    pair_potential_energy,
    reduced_mass,
    soft_sphere,
    soft_sphere_potential,
    spring_pair,
    stack,
    total_momentum,
    unstack,
)

euler, symplectic_euler, verlet, rk4 = INTEGRATORS

# region: setup
masses = [1.0, 3.0]  # kg
k = 12.0  # N/m
rest_length = 1.0  # m
stretch0 = 0.2  # m, how far the spring starts stretched
dt = 0.01  # s
duration = 4.0  # s
tolerance = 1e-12  # the bound the conservation checks are compared with
mu = reduced_mass(*masses)
omega = np.sqrt(k / mu)
pair = interacting(masses, spring_pair(k, rest_length))
start = State(
    t=0.0,
    x=stack([[0.0, 0.0], [rest_length + stretch0, 0.0]]),
    v=stack([[1.0, 0.5], [0.6, 0.5]]),  # relative velocity along the spring
)
# endregion: setup

# region: head-on
m1, m2 = 1.0, 2.0  # kg
v1, v2 = 1.0, -0.5  # m/s, head on along a line
diameter = 0.2  # m, the sum of the radii
stiffness = 1000.0  # N/m
fine = 40  # steps per contact for the main run
contact_time = np.pi * np.sqrt(reduced_mass(m1, m2) / stiffness)
expected = hard_sphere_collision(m1, [v1], m2, [v2], [-1.0])  # heavier one ahead
collision = interacting([m1, m2], soft_sphere(stiffness, diameter))
contact = soft_sphere_potential(stiffness, diameter)
approaching = State(t=0.0, x=stack([[0.0], [1.0]]), v=stack([[v1], [v2]]))
# endregion: head-on

# region: glancing
offset = 0.1  # m, the distance by which the path misses the centre
# endregion: glancing
# region: exercises
# The contact of the exercises: the stiffer one of the figure.
exercise_stiffness = 10_000.0  # N/m
# endregion: exercises


def draw_collision_geometry() -> Figure:
    """The geometry of a glancing collision and the centre of mass of a pair,
    as a sketch."""
    fig, (geometry, centre) = plt.subplots(
        2, 1, figsize=(6.4, 4.8), gridspec_kw={"height_ratios": [1.5, 1]}
    )
    radius, b = 0.5, 0.5
    contact = (-np.sqrt(1.0 - b**2), b)
    diagrams.frame(geometry, (-3.2, 3.2), (-1.5, 1.3))
    diagrams.circle(geometry, (0.0, 0.0), radius, colour=1)
    diagrams.circle(geometry, contact, radius, colour=0)
    diagrams.line(geometry, [(-2.9, 0.0), (-0.5, 0.0)], colour="#57606a", linestyle=":")
    diagrams.arrow(geometry, (-3.0, b), (contact[0] - radius - 0.1, b), colour=0)
    diagrams.text(geometry, (-3.0, b + 0.25), "incoming velocity", ha="left", colour=0)
    diagrams.line(geometry, [(-2.5, 0.0), (-2.5, b)], colour="#57606a", width=1.0)
    diagrams.text(geometry, (-2.4, b / 2), "$b$", ha="left", colour="#57606a")
    diagrams.line(geometry, [contact, (0.0, 0.0)], colour="#1f2328", linestyle="--")
    diagrams.text(geometry, (-0.12, 0.34), "$D$", ha="center")
    diagrams.arrow(geometry, (0.45, -0.26), (1.5, -0.87), colour=1)
    diagrams.text(
        geometry,
        (0.7, -1.2),
        "the target leaves along the line of centres",
        ha="left",
        colour=1,
    )
    diagrams.frame(centre, (-0.4, 5.4), (-1.0, 1.9))
    diagrams.line(centre, [(0.3, 0.0), (3.7, 0.0)], colour="#57606a")
    diagrams.circle(centre, (0.3, 0.0), 0.32, colour=0, filled=True)
    diagrams.circle(centre, (3.7, 0.0), 0.16, colour=1, filled=True)
    diagrams.text(centre, (0.3, -0.65), "$m_1$", colour=0)
    diagrams.text(centre, (3.7, -0.65), "$m_2$", colour=1)
    com = 0.3 + 3.4 * 0.2
    diagrams.line(centre, [(com, -0.22), (com, 0.22)], colour="#1f2328", width=2.4)
    diagrams.text(centre, (com, -0.65), "$\\mathbf{X}$", colour="#1f2328")
    diagrams.arrow(centre, (com - 0.5, 1.0), (com + 1.7, 1.0), colour="#1f2328")
    diagrams.text(
        centre, (com + 0.6, 1.5), "$\\mathbf{P}/M$, constant", colour="#1f2328"
    )
    fig.tight_layout()
    return fig


def pair_conservation(experiment: Experiment) -> None:
    """The total momentum of the pair on a spring and the two conservation
    checks, for each method; record the table."""
    rows = []
    for integrator in INTEGRATORS:
        trajectory = simulate(
            start, pair, dt, round(duration / dt), step=integrator.step
        )
        positions, velocities = unstack(trajectory.x, 2), unstack(trajectory.v, 2)
        momentum = total_momentum(masses, velocities)
        centre = centre_of_mass(masses, positions)
        on_the_line = centre[0] + trajectory.t[:, np.newaxis] * momentum[0] / sum(
            masses
        )
        kept = np.max(np.abs(momentum - momentum[0])) < tolerance * np.linalg.norm(
            momentum[0]
        )
        straight = np.max(np.abs(centre - on_the_line)) < tolerance
        rows.append(
            (
                integrator.name,
                momentum[0, 0],
                momentum[0, 1],
                "yes" if kept else "no",
                "yes" if straight else "no",
            )
        )

    experiment.table(
        "pair-conservation",
        rows,
        columns=[
            ("method", "", ""),
            ("total momentum, x", "kg m/s", ".1f"),
            ("total momentum, y", "kg m/s", ".1f"),
            ("constant within the bound", "", ""),
            ("centre of mass on its line within the bound", "", ""),
        ],
        caption="The total momentum of the pair and the two conservation checks, "
        "for each method, over the whole run.",
    )


def relative_motion():
    """The pair with Runge-Kutta 4, and the largest difference between the
    stretch of the spring and the oscillator of the reduced mass, in m."""
    trajectory = simulate(start, pair, dt, round(duration / dt), step=rk4.step)
    positions = unstack(trajectory.x, 2)
    stretch = np.linalg.norm(positions[:, 1] - positions[:, 0], axis=1) - rest_length
    relative_velocity = (unstack(start.v, 2)[1] - unstack(start.v, 2)[0])[0]
    relative = harmonic_motion(
        State(t=0.0, x=[stretch0], v=[relative_velocity]), mu, k, trajectory.t
    )
    oscillator_error = np.max(np.abs(stretch - relative.x[:, 0]))
    return positions, oscillator_error


def draw_pair_on_a_spring(positions) -> Figure:
    """The paths of the two masses and of their centre of mass."""
    centre = centre_of_mass(masses, positions)
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    for i, (label, style) in enumerate(
        ((f"{masses[0]:g} kg", "-"), (f"{masses[1]:g} kg", "--"))
    ):
        ax.plot(
            positions[:, i, 0],
            positions[:, i, 1],
            color="#93003a",
            linestyle=style,
            label=label,
        )
        ax.plot(
            positions[::50, i, 0],
            positions[::50, i, 1],
            color="#93003a",
            marker="o",
            markersize=3,
            linestyle="none",
        )
    ax.plot(
        centre[:, 0],
        centre[:, 1],
        color="#00429d",
        linestyle=":",
        label="centre of mass",
    )
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_aspect("equal")
    ax.legend(loc="upper left")
    return fig


def collide(steps_per_contact, duration=1.2):
    """The collision, resolved with that many steps per contact time."""
    step = contact_time / steps_per_contact
    return simulate(
        approaching, collision, step, round(duration / step), step=verlet.step
    )


def head_on(experiment: Experiment):
    """The head-on collision at forty steps per contact against the elastic
    formula; record the table and return the run, its positions and
    velocities, and when the spheres first and last overlap, in s."""
    trajectory = collide(fine)
    positions, velocities = unstack(trajectory.x, 2), unstack(trajectory.v, 2)
    overlapping = positions[:, 1, 0] - positions[:, 0, 0] < diameter
    first, last = trajectory.t[overlapping][0], trajectory.t[overlapping][-1]

    experiment.table(
        "head-on",
        [
            ("hard spheres", expected[0][0], expected[1][0]),
            ("soft spheres", velocities[-1, 0, 0], velocities[-1, 1, 0]),
        ],
        columns=[
            ("model", "", ""),
            ("outgoing velocity, first sphere", "m/s", "+.4f"),
            ("outgoing velocity, second sphere", "m/s", "+.4f"),
        ],
        caption="Outgoing velocities of the head-on collision, to four decimals: "
        "the elastic formula and the simulation.",
    )
    return trajectory, positions, velocities, first, last


def draw_head_on_collision(trajectory, positions, velocities) -> Figure:
    """The positions and the energies of the head-on collision."""
    energies = kinetic_energy([m1, m2], velocities)
    stored = pair_potential_energy(positions, contact)

    with figure_style():
        fig, (top, bottom) = plt.subplots(2, 1, figsize=figsize("stacked"), sharex=True)
        top.plot(
            trajectory.t,
            positions[:, 0, 0],
            color=FIGURE_COLOURS[1],
            label=f"{m1:g} kg sphere",
        )
        top.plot(
            trajectory.t,
            positions[:, 1, 0],
            color=FIGURE_COLOURS[0],
            linestyle="--",
            label=f"{m2:g} kg sphere",
        )
        top.set_ylabel("position (m)")
        # The spheres named beside the ends of their paths (S5): one legend
        # under the plot would give "1 kg sphere" and "kinetic" the same key.
        for k, colour in ((0, FIGURE_COLOURS[1]), (1, FIGURE_COLOURS[0])):
            direct_label(
                top,
                trajectory.t[-1],
                positions[-1, k, 0],
                f"{(m1, m2)[k]:g} kg\nsphere",
                colour,
            )
        bottom.plot(trajectory.t, energies, color=FIGURE_COLOURS[1], label="kinetic")
        bottom.plot(
            trajectory.t,
            stored,
            color=FIGURE_COLOURS[0],
            linestyle="--",
            label="contact",
        )
        bottom.plot(
            trajectory.t,
            energies + stored,
            color=FIGURE_COLOURS[2],
            linestyle=":",
            label="total",
        )
        bottom.set_xlabel("time (s)")
        bottom.set_ylabel("energy (J)")
        bottom.legend(loc="center left")
    return finish(fig)


def steps_per_contact(experiment: Experiment):
    """The head-on collision at eight step sizes; record the table and return
    the errors by steps per contact and how close the drift comes to the
    band from twenty steps on."""
    rows = []
    for steps_per_contact in (1, 2, 5, 10, 20, 40, 80, 160):
        trajectory = collide(steps_per_contact)
        positions, velocities = unstack(trajectory.x, 2), unstack(trajectory.v, 2)
        total = kinetic_energy([m1, m2], velocities) + pair_potential_energy(
            positions, contact
        )
        momentum = total_momentum([m1, m2], velocities)
        error = max(
            abs(velocities[-1, 0, 0] - expected[0][0]),
            abs(velocities[-1, 1, 0] - expected[1][0]),
        )
        drift = np.max(np.abs(total / total[0] - 1))
        band = (np.pi / steps_per_contact) ** 2 / 4
        kept = (
            np.max(np.abs(momentum - momentum[0])) < tolerance * abs(momentum[0, 0])
            if momentum[0, 0]
            else True
        )
        rows.append(
            (
                steps_per_contact,
                velocities[-1, 0, 0],
                velocities[-1, 1, 0],
                error,
                drift,
                band,
                "yes" if kept else "no",
            )
        )
    errors = {row[0]: row[3] for row in rows}
    close = [abs(row[4] / row[5] - 1) for row in rows if row[0] >= 20]

    experiment.table(
        "steps-per-contact",
        rows,
        columns=[
            ("steps per contact", "", "d"),
            ("outgoing velocity, first sphere", "m/s", ".5f"),
            ("outgoing velocity, second sphere", "m/s", ".5f"),
            ("error against hard spheres", "m/s", ".1e"),
            ("total energy drift", "", ".1e"),
            ("band", "", ".1e"),
            ("momentum constant within the bound", "", ""),
        ],
        caption="The head-on collision at eight step sizes: outgoing velocities, "
        "the larger error against the hard-sphere velocities, the largest "
        "relative drift of the total energy, and the band from the oscillator.",
    )
    return errors, close


def angle_between(u, w):
    return np.degrees(np.arccos(u @ w / (np.linalg.norm(u) * np.linalg.norm(w))))


def glancing_sweep():
    """The glancing collision of equal spheres for five contact stiffnesses,
    against the hard spheres: the time and normal of the hard contact, the
    hard spheres' velocities and deflection, the rows of the table, and the
    paths."""
    moment, normal = first_contact([-1.0, offset], [1.0, 0.0], diameter)
    hard = hard_sphere_collision(1.0, [1.0, 0.0], 1.0, [0.0, 0.0], normal)
    hard_angle = np.degrees(np.arctan2(hard[0][1], hard[0][0]))

    rows = []
    paths = {}
    for stiffness in (10.0, 100.0, 1000.0, 10_000.0, 100_000.0):
        tau = np.pi * np.sqrt(reduced_mass(1.0, 1.0) / stiffness)
        step = tau / fine
        glancing = State(
            t=0.0,
            x=stack([[-1.0, offset], [0.0, 0.0]]),
            v=stack([[1.0, 0.0], [0.0, 0.0]]),
        )
        n_steps = round(2.0 / step)
        trajectory = simulate(
            glancing,
            interacting([1.0, 1.0], soft_sphere(stiffness, diameter)),
            step,
            n_steps,
            step=verlet.step,
        )
        paths[stiffness] = unstack(trajectory.x, 2)
        final = unstack(trajectory.v, 2)[-1]
        deflection = np.degrees(np.arctan2(final[0, 1], final[0, 0]))
        rows.append(
            (
                stiffness,
                tau,
                n_steps,
                deflection,
                deflection - hard_angle,
                angle_between(final[0], final[1]),
            )
        )
    return moment, hard, hard_angle, rows, paths


def stiffness_sweep(experiment: Experiment, rows) -> None:
    """Record the table of the glancing collision for five stiffnesses."""
    experiment.table(
        "stiffness-sweep",
        rows,
        columns=[
            ("stiffness", "N/m", ".0f"),
            ("contact time", "s", ".4f"),
            ("steps", "", "d"),
            ("deflection", "°", ".2f"),
            ("difference from hard spheres", "°", "+.2f"),
            ("angle between the leaving spheres", "°", ".2f"),
        ],
        caption="The glancing collision for five contact stiffnesses, each at the "
        "same number of steps per contact: deflection of the moving sphere, its "
        "difference from the hard-sphere value, and the angle between the two "
        "leaving spheres, to two decimals.",
    )


def draw_glancing_collision(moment, hard, paths) -> Figure:
    """The paths of the glancing collision for two stiffnesses and of the
    hard spheres."""
    after = np.linspace(0.0, 1.0, 2)[:, np.newaxis]
    touch = np.array([-1.0 + moment, offset])
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("square", legend=3))
        for sphere, start_point in ((hard[0], touch), (hard[1], np.zeros(2))):
            line = start_point + after * sphere
            ax.plot(
                line[:, 0],
                line[:, 1],
                color=FIGURE_COLOURS[2],
                linestyle=":",
                label="hard spheres" if sphere is hard[0] else None,
            )
        for stiffness, style in ((100.0, "--"), (10_000.0, "-")):
            for i in range(2):
                ax.plot(
                    paths[stiffness][:, i, 0],
                    paths[stiffness][:, i, 1],
                    color=FIGURE_COLOURS[1] if i == 0 else FIGURE_COLOURS[0],
                    linestyle=style,
                    label=f"{stiffness:.0f} N/m" if i == 0 else None,
                )
        for centre_point in (touch, np.zeros(2)):
            ax.add_patch(
                plt.Circle(
                    centre_point,
                    diameter / 2,
                    fill=False,
                    color=FIGURE_COLOURS[2],
                    linewidth=LINE["axis"],
                )
            )
        ax.set_xlim(-1.1, 1.0)
        ax.set_ylim(-0.6, 0.9)
        ax.set_aspect("equal")
        ax.set_xlabel("x (m)")
        ax.set_ylabel("y (m)")
        # Under the plot: inside, the legend would lie over the paths.
        fig.legend(loc="outside lower center", ncols=1)
    return finish(fig)


def energy_transfer(experiment: Experiment) -> None:
    """Exercise 1: the fraction of the kinetic energy a target at rest
    carries away, for five mass ratios; record the
    table."""
    rows = []
    for ratio in (0.1, 0.5, 1.0, 2.0, 10.0):
        target_mass = ratio * 1.0
        tau = np.pi * np.sqrt(reduced_mass(1.0, target_mass) / exercise_stiffness)
        step = tau / fine
        resting = State(t=0.0, x=stack([[0.0], [0.5]]), v=stack([[1.0], [0.0]]))
        trajectory = simulate(
            resting,
            interacting([1.0, target_mass], soft_sphere(exercise_stiffness, diameter)),
            step,
            round(1.0 / step),
            step=verlet.step,
        )
        final = unstack(trajectory.v, 2)[-1]
        transferred = target_mass * final[1, 0] ** 2 / 1.0
        rows.append((ratio, transferred, 4 * target_mass / (1 + target_mass) ** 2))

    experiment.table(
        "energy-transfer",
        rows,
        columns=[
            ("mass ratio, target over moving sphere", "", ".1f"),
            ("transferred, soft spheres", "", ".4f"),
            ("4 m1 m2 / (m1 + m2)^2", "", ".4f"),
        ],
        caption="The fraction of the kinetic energy that the target carries away: "
        "soft spheres and the formula, to four decimals.",
    )


def pass_through(experiment: Experiment) -> None:
    """Exercise 2: equal spheres below and above the speed at which they
    pass through each other; record the table."""
    bound = diameter * np.sqrt(exercise_stiffness / reduced_mass(1.0, 1.0))
    rows = []
    for fraction in (0.5, 0.9, 1.1, 1.5):
        speed = fraction * bound
        tau = np.pi * np.sqrt(reduced_mass(1.0, 1.0) / exercise_stiffness)
        step = tau / fine
        rushing = State(t=0.0, x=stack([[0.0], [0.5]]), v=stack([[speed], [0.0]]))
        trajectory = simulate(
            rushing,
            interacting([1.0, 1.0], soft_sphere(exercise_stiffness, diameter)),
            step,
            round(0.5 / step),
            step=verlet.step,
        )
        positions = unstack(trajectory.x, 2)[-1]
        final = unstack(trajectory.v, 2)[-1]
        rows.append(
            (
                fraction,
                final[0, 0] / speed,
                final[1, 0] / speed,
                "swapped" if positions[0, 0] > positions[1, 0] else "kept",
            )
        )

    experiment.table(
        "pass-through",
        rows,
        columns=[
            ("speed over the bound", "", ".1f"),
            ("final velocity, first sphere, over the initial speed", "", "+.3f"),
            ("final velocity, second sphere, over the initial speed", "", "+.3f"),
            ("order of the spheres at the end", "", ""),
        ],
        caption="Equal spheres at speeds below and above the pass-through bound, "
        f"which here is {bound:.2f} m/s: the velocities at the end in units of the "
        "initial speed.",
    )


row_diameter = 0.1  # m


def cradle_final(row_stiffness, gap):
    """The final velocities of a row of three spheres, the first one moving."""
    tau = np.pi * np.sqrt(reduced_mass(1.0, 1.0) / row_stiffness)
    step = tau / fine
    row = State(
        t=0.0,
        x=stack([[-0.3], [0.0], [row_diameter + gap]]),
        v=stack([[1.0], [0.0], [0.0]]),
    )
    cradle = interacting([1.0, 1.0, 1.0], soft_sphere(row_stiffness, row_diameter))
    return unstack(
        simulate(row, cradle, step, round(0.8 / step), step=verlet.step).v, 3
    )[-1, :, 0]


def cradle(experiment: Experiment) -> float:
    """Exercise 3: the row of three spheres for touching spheres at three
    stiffnesses and for a gap; record the table and return the largest
    spread of the touching rows around their mean, in m/s."""
    rows = [(1e4, gap, *cradle_final(1e4, gap)) for gap in (0.0, 0.02)]
    rows += [(row_k, 0.0, *cradle_final(row_k, 0.0)) for row_k in (1e3, 1e5)]
    touching = [row[2:] for row in rows if row[1] == 0.0]
    spread = np.max(np.abs(touching - np.mean(touching, axis=0)))

    experiment.table(
        "cradle",
        rows,
        columns=[
            ("stiffness", "N/m", ".0f"),
            ("gap", "m", ".2f"),
            ("final velocity, first sphere", "m/s", "+.4f"),
            ("final velocity, second sphere", "m/s", "+.4f"),
            ("final velocity, third sphere", "m/s", "+.4f"),
        ],
        caption="The row of three spheres: final velocities for touching spheres "
        "at three stiffnesses and for a gap at one, to four decimals.",
    )
    return spread


def centre_of_mass_frame(experiment: Experiment):
    """Exercise 4: the speeds of unequal spheres in a glancing collision, in
    the laboratory and in the frame of the centre of mass; record the table
    and return the velocity of the centre of mass, in m/s."""
    pair_masses = [1.0, 2.0]
    tau = np.pi * np.sqrt(reduced_mass(*pair_masses) / 10_000.0)
    step = tau / fine
    glancing = State(
        t=0.0, x=stack([[-1.0, offset], [0.0, 0.0]]), v=stack([[1.0, 0.0], [0.0, 0.0]])
    )
    velocities = unstack(
        simulate(
            glancing,
            interacting(pair_masses, soft_sphere(10_000.0, diameter)),
            step,
            round(2.0 / step),
            step=verlet.step,
        ).v,
        2,
    )
    drift = total_momentum(pair_masses, velocities[0]) / sum(pair_masses)

    rows = []
    for i, mass in enumerate(pair_masses):
        before, after = velocities[0, i], velocities[-1, i]
        rows.append(
            (
                mass,
                np.linalg.norm(before),
                np.linalg.norm(after),
                np.linalg.norm(before - drift),
                np.linalg.norm(after - drift),
            )
        )

    experiment.table(
        "centre-of-mass-frame",
        rows,
        columns=[
            ("mass", "kg", ".0f"),
            ("lab speed before", "m/s", ".4f"),
            ("lab speed after", "m/s", ".4f"),
            ("speed before, centre-of-mass frame", "m/s", ".4f"),
            ("speed after, centre-of-mass frame", "m/s", ".4f"),
        ],
        caption="Speeds of the two spheres in the laboratory frame and in the "
        "frame of the centre of mass, before and after the glancing collision, "
        "to four decimals.",
    )
    return drift


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.figure("fig-collision-geometry", draw_collision_geometry)

    for name, value, spec in (
        ("mass-1", masses[0], "g"),
        ("mass-2", masses[1], "g"),
        ("k", k, "g"),
        ("rest-length", rest_length, "g"),
        ("stretch0", stretch0, "g"),
        ("mu", mu, "g"),
        ("omega", omega, ".1f"),
        ("period", 2 * np.pi / omega, ".4f"),
        ("duration", duration, "g"),
        ("dt", dt, "g"),
        ("tolerance", tolerance, ".0e"),
    ):
        experiment.number(name, value, spec)
    pair_conservation(experiment)
    positions, oscillator_error = relative_motion()
    experiment.number("oscillator-error", oscillator_error, ".1e")
    experiment.figure("fig-pair-on-a-spring", partial(draw_pair_on_a_spring, positions))
    experiment.number("mass-ratio", masses[1] / masses[0], "g")

    trajectory, positions, velocities, first, last = head_on(experiment)
    for name, value, spec in (
        ("m1", m1, "g"),
        ("m2", m2, "g"),
        ("v1", v1, "g"),
        ("v2", -v2, "g"),
        ("diameter", diameter, "g"),
        ("stiffness", stiffness, "g"),
        ("contact-time", contact_time, ".4f"),
        ("first", first, ".3f"),
        ("last", last, ".3f"),
    ):
        experiment.number(name, value, spec)
    experiment.figure(
        "fig-head-on-collision",
        partial(draw_head_on_collision, trajectory, positions, velocities),
    )

    errors, close = steps_per_contact(experiment)
    for steps, spec in ((2, ".0f"), (5, ".1f"), (10, ".2f"), (1, ".0f")):
        experiment.number(
            f"error-{steps}-per-cent", 100 * errors[steps] / abs(expected[0][0]), spec
        )
    experiment.number("closest-to-band", 100 * max(close), ".1f")

    # region: sweep
    moment, hard, hard_angle, rows, paths = glancing_sweep()
    alpha = np.degrees(np.arcsin(offset / diameter))
    differences = np.abs([row[4] for row in rows])
    ratios = differences[:-1] / differences[1:]
    right_angle = max(abs(row[5] - 90.0) for row in rows)
    # endregion: sweep
    experiment.number("alpha", alpha, ".2f")
    experiment.number("moment", moment, ".4f")
    experiment.number("hard-angle", hard_angle, ".2f")
    experiment.number("hard-between", angle_between(*hard), ".2f")
    stiffness_sweep(experiment, rows)
    experiment.figure(
        "fig-glancing-collision", partial(draw_glancing_collision, moment, hard, paths)
    )
    experiment.number("right-angle", right_angle, ".2f")
    experiment.number("smallest-ratio", min(ratios[1:]), ".1f")
    experiment.number("largest-ratio", max(ratios[1:]), ".1f")
    experiment.number("root-ten", np.sqrt(10), ".2f")

    energy_transfer(experiment)
    pass_through(experiment)
    experiment.number("cradle-spread", cradle(experiment), ".0e")
    drift = centre_of_mass_frame(experiment)
    experiment.number("drift-x", drift[0], ".4f")
    experiment.number("drift-y", drift[1], ".4f")
    return experiment


if __name__ == "__main__":
    main(run)
