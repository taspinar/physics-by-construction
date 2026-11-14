"""The experiment of the lesson "Projectile motion with drag".

A tennis ball thrown with and without quadratic drag
(``pbc.mechanics.projectile``), the convergence of its range, the best
launch angle, and the comparison with a steel ball. Run it as a program to
write the figures and numbers of the page:

    uv run --locked --no-dev \
        python -m pbc.mechanics.experiments.projectile_with_drag out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from scipy.constants import g  # standard gravity, m/s^2
from scipy.optimize import minimize_scalar

from pbc.authoring import FIGURE_COLOURS
from pbc.authoring.design import PAGE
from pbc.authoring.diagrams import arrow, canvas, text
from pbc.experiment import Experiment, main
from pbc.mechanics.drag import drag_constant, quadratic_drag
from pbc.mechanics.dynamics import State, newton, simulate, weight
from pbc.mechanics.projectile import (
    drag_free_range,
    fly,
    landing,
    launch,
    projectile_range,
)

# region: setup
mass = 0.058  # kg
diameter = 0.067  # m
air_density = 1.2  # kg/m^3
air_viscosity = 1.8e-5  # Pa s
drag_coefficient = 0.5
c = drag_constant(air_density, drag_coefficient, np.pi * (diameter / 2) ** 2)
terminal_speed = np.sqrt(mass * g / c)

speed = 25.0  # launch speed, m/s
angle = 45.0  # launch angle, degrees
dt = 0.001  # time step, s
reynolds = air_density * speed * diameter / air_viscosity
stable_step = mass / (c * speed)  # largest stable step at the launch speed, s
# endregion: setup

# region: scan
scan_dt = 0.002  # s
angles = np.arange(10.0, 80.5, 2.5)
# endregion: scan


def draw_drag_against_speed() -> Figure:
    """The linear and the quadratic drag law against speed, as a sketch."""
    fig, ax = canvas(6.4, 3.6, (0, 10), (0, 6))
    ax.set_aspect("auto")
    origin, width, height = 0.6, 8.6, 4.6
    arrow(ax, (origin, origin), (9.8, origin), colour=PAGE["muted"])
    arrow(ax, (origin, origin), (origin, 5.7), colour=PAGE["muted"])
    text(ax, (9.8, origin - 0.18), r"speed $|v|$", colour=PAGE["muted"], ha="right")
    text(ax, (origin + 0.1, 5.7), "drag force", colour=PAGE["muted"], ha="left")
    share = np.linspace(0.0, 1.0, 100)
    ax.plot(
        origin + width * share,
        origin + height * share / 2,
        color=FIGURE_COLOURS[0],
        linewidth=1.6,
    )
    ax.plot(
        origin + width * share,
        origin + height * share**2,
        color=FIGURE_COLOURS[1],
        linewidth=1.6,
        linestyle="--",
    )
    # The line height * share / 2 and the curve height * share**2 are equal at
    # share = 1/2, where both are height / 4: the marker is on both.
    ax.plot(
        [origin + width / 2], [origin + height / 4], marker="o", color=FIGURE_COLOURS[2]
    )
    # Each label sits beside its own curve: the linear one below the line
    # near its end, the quadratic one left of the steep part of the curve,
    # and the crossing's just below and right of the marker.
    text(ax, (7.2, 1.95), r"linear: $b\,|v|$", colour=0, ha="left")
    text(ax, (7.7, 4.2), r"quadratic: $c\,|v|^{2}$", colour=1, ha="right")
    text(ax, (5.15, 1.45), "the curves cross", colour=2, ha="left")
    return fig


def throws(experiment: Experiment):
    """The same throw with and without quadratic drag; record their range,
    time of flight, and highest point."""
    down = [0.0, -g]
    ball_in_air = newton(mass, weight(mass, down), quadratic_drag(c))
    ball_in_vacuum = newton(mass, weight(mass, down))
    with_drag = fly(launch(speed, angle), ball_in_air, dt)
    without_drag = fly(launch(speed, angle), ball_in_vacuum, dt)

    experiment.table(
        "throws",
        [
            (name, landing(flight).x, landing(flight).t, flight.x[:, 1].max())
            for name, flight in (
                ("with drag", with_drag),
                ("without drag", without_drag),
            )
        ],
        columns=[
            ("throw", "", ""),
            ("range", "m", ".2f"),
            ("time of flight", "s", ".2f"),
            ("highest point", "m", ".2f"),
        ],
        caption="Range, time of flight, and highest point of the same throw "
        "with and without quadratic drag.",
    )
    return with_drag, without_drag


def draw_throw_with_and_without_drag(with_drag, without_drag) -> Figure:
    """The paths of the throw with and without drag."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.plot(
        without_drag.x[:, 0],
        without_drag.x[:, 1],
        color="#555555",
        linestyle=":",
        label="without drag",
    )
    ax.plot(with_drag.x[:, 0], with_drag.x[:, 1], color="#93003a", label="with drag")
    ax.set_ylim(bottom=0.0)
    ax.set_xlabel("horizontal distance (m)")
    ax.set_ylabel("height (m)")
    ax.legend()
    return fig


def drag_free_convergence(experiment: Experiment):
    """The range of the drag-free throw for each time step against the exact
    range; record the table."""
    exact = drag_free_range(speed, angle)
    v_x = launch(speed, angle).v[0]
    steps = [0.1 / 2**k for k in range(8)]

    free_ranges = [projectile_range(speed, angle, mass, 0.0, step) for step in steps]

    experiment.table(
        "drag-free-convergence",
        [
            (step, computed, computed - exact, v_x * step)
            for step, computed in zip(steps, free_ranges, strict=True)
        ],
        columns=[
            ("time step", "s", ".6f"),
            ("range", "m", ".4f"),
            ("error", "m", ".4f"),
            ("v_x times time step", "m", ".4f"),
        ],
        caption="Range of the drag-free throw for each time step, its error "
        "against the exact range, and the error the first lesson predicts.",
    )
    return exact, v_x, steps, free_ranges


def richardson(experiment: Experiment, steps):
    """The range with drag for each time step, the observed order, and the
    Richardson estimate of the limit; record the table."""
    ranges = np.array([projectile_range(speed, angle, mass, c, step) for step in steps])
    differences = np.diff(ranges)
    orders = np.log2(differences[:-1] / differences[1:])
    limits = 2 * ranges[1:] - ranges[:-1]

    best_estimate = limits[-1]
    error_estimate = abs(differences[-1])

    experiment.table(
        "richardson",
        [
            (
                step,
                ranges[i],
                differences[i - 1] if i else None,
                orders[i - 2] if i >= 2 else None,
                limits[i - 1] if i else None,
            )
            for i, step in enumerate(steps)
        ],
        columns=[
            ("time step", "s", ".6f"),
            ("range", "m", ".4f"),
            ("difference", "m", ".4f"),
            ("observed order", "", ".3f"),
            ("estimated limit", "m", ".4f"),
        ],
        caption="Range with drag for each time step, the difference to the "
        "previous result, the observed order, and the Richardson estimate of "
        "the limit.",
    )
    return ranges, differences, orders, best_estimate, error_estimate


def draw_convergence_of_the_range(steps, ranges, best_estimate, v_x) -> Figure:
    """The error of the range with drag against the time step, log-log."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.loglog(
        steps,
        np.abs(ranges - best_estimate),
        color="#93003a",
        marker="o",
        label="computed range, against the extrapolated limit",
    )
    ax.loglog(
        steps,
        np.array(steps) * v_x,
        color="#555555",
        linestyle=":",
        label="slope 1",
    )
    ax.set_xlabel("time step (s)")
    ax.set_ylabel("size of the error (m)")
    ax.legend()
    return fig


def best_angle(drag, ball_mass=mass):
    """The launch angle of the longest throw, to a tenth of a degree."""
    result = minimize_scalar(
        lambda a: -projectile_range(speed, a, ball_mass, drag, scan_dt),
        bounds=(20.0, 60.0),
        method="bounded",
        options={"xatol": 0.05},
    )
    return result.x, -result.fun


def longest_throws(experiment: Experiment):
    """The range for each launch angle and the longest throw with and
    without drag; record the table of the longest throws."""
    ranges_with_drag = np.array(
        [projectile_range(speed, a, mass, c, scan_dt) for a in angles]
    )
    ranges_without = np.array(
        [projectile_range(speed, a, mass, 0.0, scan_dt) for a in angles]
    )

    best_with, furthest_with = best_angle(c)
    best_without, furthest_without = best_angle(0.0)

    experiment.table(
        "longest-throws",
        [
            ("with drag", furthest_with, best_with),
            ("without drag", furthest_without, best_without),
        ],
        columns=[
            ("throw", "", ""),
            ("longest range", "m", ".2f"),
            ("best angle", "degrees", ".1f"),
        ],
        caption="Longest range and the launch angle that gives it, found by a "
        "one-dimensional minimiser.",
    )
    return ranges_with_drag, ranges_without, best_with, furthest_with, best_without


def draw_range_against_angle(ranges_with_drag, ranges_without) -> Figure:
    """The range against the launch angle, with and without drag."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.plot(
        angles,
        ranges_without,
        color="#555555",
        linestyle=":",
        marker="s",
        markersize=3,
        label="without drag",
    )
    ax.plot(
        angles,
        ranges_with_drag,
        color="#93003a",
        marker="o",
        markersize=3,
        label="with drag",
    )
    ax.axvline(
        45.0,
        color="#00429d",
        linestyle="--",
        linewidth=0.8,
        label="45 degrees",
    )
    ax.set_xlabel("launch angle (degrees)")
    ax.set_ylabel("range (m)")
    ax.legend()
    return fig


def terminal_fall():
    """Exercise 1: the ball dropped from rest, with quadratic drag; the
    speeds and the time it reaches 95 per cent of the terminal speed."""
    dropped = State(t=0.0, x=0.0, v=0.0)
    falling = newton(mass, weight(mass, [g]), quadratic_drag(c))
    fall = simulate(dropped, falling, 0.001, 15_000)
    speeds = fall.v[:, 0]
    reached = fall.t[np.argmax(speeds >= 0.95 * terminal_speed)]
    return fall, speeds, reached


def refine(experiment: Experiment, steps, differences, ranges):
    """Exercise 2: the time steps that bring the range within a centimetre,
    and further halvings until the estimated error is below a millimetre;
    record the table of the halvings."""
    within_a_centimetre = [
        step
        for step, error in zip(steps[1:], np.abs(differences), strict=True)
        if error < 0.01
    ]

    tolerance = 0.001  # m
    step = steps[-1]
    previous = ranges[-1]
    refinement = []
    while True:
        step /= 2
        current = projectile_range(speed, angle, mass, c, step)
        estimate = abs(current - previous)
        refinement.append((step, current, estimate))
        if estimate < tolerance:
            break
        previous = current

    experiment.table(
        "refinement",
        refinement,
        columns=[
            ("time step", "s", ".6f"),
            ("range", "m", ".4f"),
            ("estimated error", "m", ".5f"),
        ],
        caption="Further halvings of the time step until the estimated error "
        "is below the tolerance.",
    )
    return within_a_centimetre, step


def steel_and_tennis(experiment: Experiment, best_with):
    """Exercise 3: a steel ball of the same size against the tennis ball;
    record the table."""
    steel_mass = 1.23  # kg
    steel_terminal_speed = np.sqrt(steel_mass * g / c)
    steel_range = projectile_range(speed, 45.0, steel_mass, c, scan_dt)
    steel_best, _ = best_angle(c, steel_mass)
    tennis_range = projectile_range(speed, 45.0, mass, c, scan_dt)
    free_range = projectile_range(speed, 45.0, mass, 0.0, scan_dt)

    experiment.table(
        "steel-and-tennis",
        [
            (
                "steel",
                steel_terminal_speed,
                (speed / steel_terminal_speed) ** 2,
                steel_range,
                100 * (1 - steel_range / free_range),
                steel_best,
            ),
            (
                "tennis",
                terminal_speed,
                (speed / terminal_speed) ** 2,
                tennis_range,
                100 * (1 - tennis_range / free_range),
                best_with,
            ),
        ],
        columns=[
            ("ball", "", ""),
            ("terminal speed", "m/s", ".1f"),
            ("drag over weight at launch", "", ".3f"),
            ("range at 45 degrees", "m", ".2f"),
            ("range lost to drag", "per cent", ".1f"),
            ("best angle", "degrees", ".1f"),
        ],
        caption="The steel ball and the tennis ball, launched at the same speed.",
    )
    return steel_terminal_speed, steel_range, tennis_range, free_range


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.figure("fig-drag-against-speed", draw_drag_against_speed)

    experiment.number("c", c, ".2e")
    experiment.number("terminal-speed", terminal_speed, ".1f")
    experiment.number("drag-over-weight", (speed / terminal_speed) ** 2, ".2f")
    experiment.number("reynolds", reynolds, ".1e")
    experiment.number("stable-step", stable_step, ".1f")
    experiment.number("dt", dt)

    with_drag, without_drag = throws(experiment)
    experiment.number(
        "range-lost",
        100 * (1 - landing(with_drag).x / landing(without_drag).x),
        ".0f",
    )
    experiment.number("exact-range", drag_free_range(speed, angle), ".2f")
    experiment.number(
        "range-excess-cm",
        100 * (landing(without_drag).x - drag_free_range(speed, angle)),
        ".0f",
    )
    experiment.figure(
        "fig-throw-with-and-without-drag",
        partial(draw_throw_with_and_without_drag, with_drag, without_drag),
    )

    exact, v_x, steps, free_ranges = drag_free_convergence(experiment)
    experiment.number(
        "prediction-gap", abs(free_ranges[-1] - exact - v_x * steps[-1]), ".1e"
    )

    ranges, differences, orders, best_estimate, error_estimate = richardson(
        experiment, steps
    )
    experiment.number("last-order", orders[-1], ".3f")
    experiment.number("best-estimate", best_estimate, ".3f")
    experiment.number("error-estimate-mm", 1000 * error_estimate, ".0f")
    experiment.figure(
        "fig-convergence-of-the-range",
        partial(draw_convergence_of_the_range, steps, ranges, best_estimate, v_x),
    )

    ranges_with_drag, ranges_without, best_with, furthest_with, best_without = (
        longest_throws(experiment)
    )
    experiment.number("best-without", best_without, ".1f")
    experiment.number("best-with", best_with, ".1f")
    # The throw of the convergence table at the step of the scan: its error
    # against the extrapolated limit, and how much the best angle gains on it.
    at_45_degrees = projectile_range(speed, angle, mass, c, scan_dt)
    experiment.number("scan-error-cm", 100 * abs(at_45_degrees - best_estimate), ".0f")
    experiment.number("angle-gain", 100 * (furthest_with / at_45_degrees - 1), ".0f")
    experiment.figure(
        "fig-range-against-angle",
        partial(draw_range_against_angle, ranges_with_drag, ranges_without),
    )

    fall, speeds, reached = terminal_fall()
    experiment.number("terminal-speed-3", terminal_speed, ".3f")
    experiment.number("fall-time", fall.t[-1], ".0f")
    experiment.number("final-speed", speeds[-1], ".3f")
    experiment.number("reached", reached, ".2f")
    experiment.number(
        "reached-in-time-constants", reached / (terminal_speed / g), ".1f"
    )

    within_a_centimetre, step = refine(experiment, steps, differences, ranges)
    experiment.number("within-a-centimetre", len(within_a_centimetre))
    experiment.number("first-within", within_a_centimetre[0], ".6f")
    experiment.number("millimetre-step-ms", step * 1e3, ".2f")
    experiment.number("millimetre-steps", round(landing(with_drag).t / step))

    steel_terminal_speed, steel_range, tennis_range, free_range = steel_and_tennis(
        experiment, best_with
    )
    experiment.number(
        "steel-drag-per-cent", 100 * (speed / steel_terminal_speed) ** 2, ".0f"
    )
    experiment.number("steel-lost", 100 * (1 - steel_range / free_range), ".1f")
    experiment.number("tennis-lost", 100 * (1 - tennis_range / free_range), ".0f")
    return experiment


if __name__ == "__main__":
    main(run)
