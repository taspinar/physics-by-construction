"""The experiment of the lesson "The double pendulum and chaos".

The double pendulum (``pbc.mechanics.chaos``): its normal modes, its energy
drift, the separation of two nearby starts, and the largest Lyapunov
exponent of a regular and a chaotic start. Run it as a program to write the
figure and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.double_pendulum_chaos out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from scipy.constants import g

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.figure_language import LINE, MUTED, direct_label, figsize, figure_style, finish
from pbc.mechanics.chaos import (
    double_pendulum,
    double_pendulum_energy,
    lyapunov_exponent,
)
from pbc.mechanics.dynamics import State, simulate
from pbc.mechanics.integrators import rk4_step

# region: setup
mass, length = 1.0, 1.0  # kg, m
pendulum = double_pendulum(mass, mass, length, length)
dt = 0.01  # s
# endregion: setup
# region: offset
offset = 1e-8  # rad
# endregion: offset


def released(first, second):
    """At rest, with the two rods at the given angles (rad)."""
    return State(t=0.0, x=[first, second], v=[0.0, 0.0])


def run_for(start, duration):
    return simulate(start, pendulum, dt, round(duration / dt), step=rk4_step)


def periods(trajectory):
    """The times between the passages of the first angle through zero in the
    same direction, interpolated within the step (s)."""
    s, t = trajectory.x[:, 0], trajectory.t
    before = np.where((s[:-1] > 0) & (s[1:] <= 0))[0]
    crossings = t[before] + s[before] / (s[before] - s[before + 1]) * (
        t[before + 1] - t[before]
    )
    return np.diff(crossings)


def modes_and_energy(experiment: Experiment) -> None:
    """The periods of the two normal modes of small oscillations, closed form
    and simulated; record the table."""
    rows = []
    for label, ratio, factor in (
        ("slow mode", np.sqrt(2.0), 2.0 - np.sqrt(2.0)),
        ("fast mode", -np.sqrt(2.0), 2.0 + np.sqrt(2.0)),
    ):
        small = 1e-3  # rad
        trajectory = run_for(released(small, small * ratio), 12.0)
        analytic = 2.0 * np.pi / np.sqrt(g / length * factor)
        rows.append((label, analytic, np.mean(periods(trajectory))))

    experiment.table(
        "modes-and-energy",
        rows,
        columns=[
            ("mode", "", ""),
            ("period from the equations", "s", ".4f"),
            ("simulated period", "s", ".4f"),
        ],
        caption="Period of the two normal modes of the small oscillations: the "
        "closed form and the simulation, to four decimals.",
    )


def drift(trajectory):
    energy = double_pendulum_energy(
        trajectory.x, trajectory.v, mass, mass, length, length
    )
    return np.max(np.abs(energy - energy[0])) / abs(energy[0])


# region: starts
regular_start, chaotic_start = released(0.2, 0.2), released(2.0, 2.0)
# endregion: starts


def energy_drift(experiment: Experiment):
    """Fifty seconds of a regular and a chaotic start; record the table of
    their energy drift and return the runs."""
    regular_run, chaotic_run = (
        run_for(regular_start, 50.0),
        run_for(chaotic_start, 50.0),
    )

    experiment.table(
        "energy-drift",
        [
            ("regular", 0.2, drift(regular_run)),
            ("chaotic", 2.0, drift(chaotic_run)),
        ],
        columns=[
            ("start", "", ""),
            ("both angles", "rad", ".1f"),
            ("energy drift over 50 s", "", ".1e"),
        ],
        caption="Relative energy drift of the double pendulum released at rest "
        "with both rods at the same angle, over fifty seconds, classical "
        "Runge-Kutta method.",
    )
    return regular_run, chaotic_run


def separation(first, second):
    return np.linalg.norm(np.hstack([first.x - second.x, first.v - second.v]), axis=1)


def shifted(start):
    return State(t=0.0, x=start.x + np.array([offset, 0.0]), v=start.v)


def separations(regular_run, chaotic_run):
    """The distance of each run from a start shifted by ``offset``, and the
    estimate of the largest Lyapunov exponent of each start."""
    regular_gap = separation(regular_run, run_for(shifted(regular_start), 50.0))
    chaotic_gap = separation(chaotic_run, run_for(shifted(chaotic_start), 50.0))

    estimates = {
        name: lyapunov_exponent(start, pendulum, dt, round(100.0 / dt))
        for name, start in (("regular", regular_start), ("chaotic", chaotic_start))
    }
    return regular_gap, chaotic_gap, estimates


def draw_separation(regular_run, chaotic_run, regular_gap, chaotic_gap, rate) -> Figure:
    """The distance between two nearby starts against time."""
    regular, chaotic = FIGURE_COLOURS[0], FIGURE_COLOURS[1]
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line"))
        ax.semilogy(
            regular_run.t,
            regular_gap,
            color=regular,
            linestyle="-",
            label="regular start",
        )
        ax.semilogy(
            chaotic_run.t,
            chaotic_gap,
            color=chaotic,
            linestyle="--",
            label="chaotic start",
        )
        t_line = np.linspace(0.0, 14.0, 50)
        ax.semilogy(
            t_line,
            offset * np.exp(rate * t_line),
            color=MUTED,
            linestyle=":",
            linewidth=LINE["guide"],
            label="slope of the exponent",
        )
        ax.set_xlabel("time (s)")
        ax.set_ylabel("distance between\nthe two starts")
        # The series named beside the curves: a legend inside the axes
        # covered the regular start's curve.
        direct_label(
            ax, 35.0, 3e-6, "regular start", regular, offset=(0.0, 0.0), ha="center"
        )
        direct_label(
            ax, 32.0, 3e-1, "chaotic start", chaotic, offset=(0.0, 0.0), ha="center"
        )
        direct_label(
            ax,
            10.5,
            1e-1,
            "slope of the\nexponent",
            MUTED,
            offset=(-6.0, 0.0),
            ha="right",
        )
    return finish(fig, grid=True)


def lyapunov_table(experiment: Experiment, estimates) -> list:
    """The estimate of the exponent of both starts after three lengths of
    the run; record the table and return its rows."""
    rows = []
    for name, estimate in estimates.items():
        row = [name]
        for horizon in (25.0, 50.0, 100.0):
            row.append(estimate.running[np.searchsorted(estimate.t, horizon) - 1])
        rows.append(row)

    experiment.table(
        "lyapunov-table",
        rows,
        columns=[
            ("start", "", ""),
            ("after 25 s", "1/s", ".3f"),
            ("after 50 s", "1/s", ".3f"),
            ("after 100 s", "1/s", ".3f"),
        ],
        caption="The estimate of the largest Lyapunov exponent of the two starts of "
        "the figure, after three lengths of the run, to three decimals.",
    )
    return rows


def known_exponent(experiment: Experiment) -> None:
    """The estimator on the hyperbolic point, whose exponent is known;
    record the table."""
    known = 1.3  # 1/s
    check = lyapunov_exponent(
        State(t=0.0, x=[0.0], v=[0.0]),
        lambda t, x, v: known**2 * x,
        dt=0.01,
        n_steps=3000,
        separation=1e-6,
    )
    experiment.table(
        "known-exponent",
        [(known, check.exponent, abs(check.exponent / known - 1.0))],
        columns=[
            ("exponent", "1/s", ".3f"),
            ("estimate", "1/s", ".4f"),
            ("relative difference", "", ".1e"),
        ],
        caption="The estimator on the hyperbolic point, whose exponent is known, "
        "to the precision shown.",
    )


def step_halved(experiment: Experiment, chaotic_run, estimates):
    """The chaotic start at half the step: when the two runs part, and the
    estimate of the exponent; record the table."""
    fine = 0.005  # s
    coarse_run = chaotic_run
    fine_run = simulate(
        chaotic_start, pendulum, fine, round(50.0 / fine), step=rk4_step
    )
    gap = np.linalg.norm(
        np.hstack([coarse_run.x - fine_run.x[::2], coarse_run.v - fine_run.v[::2]]),
        axis=1,
    )
    diverged = coarse_run.t[np.argmax(gap > 1e-3)]
    fine_estimate = lyapunov_exponent(
        chaotic_start, pendulum, fine, round(100.0 / fine), rescale_every=20
    )

    experiment.table(
        "step-halved",
        [
            ("step of the first run", dt, estimates["chaotic"].exponent),
            ("half the step", fine, fine_estimate.exponent),
        ],
        columns=[
            ("run", "", ""),
            ("step", "s", ".3f"),
            ("estimate after 100 s", "1/s", ".3f"),
        ],
        caption="The estimate of the exponent of the chaotic start at two steps, to "
        "three decimals.",
    )
    return diverged, fine_estimate


def prediction_horizon(experiment: Experiment, chaotic_run, rate):
    """Exercise 1: the time to lose a distance of a hundredth from a start
    known to a millionth, from the exponent and measured; record the
    table."""
    d0, tolerance = 1e-6, 1e-2
    horizon = np.log(tolerance / d0) / rate
    other = run_for(
        State(0.0, chaotic_start.x + np.array([d0, 0.0]), chaotic_start.v), 50.0
    )
    gap_curve = separation(chaotic_run, other)
    measured = chaotic_run.t[np.argmax(gap_curve > tolerance)]

    experiment.table(
        "prediction-horizon",
        [(horizon, measured)],
        columns=[("from the exponent", "s", ".1f"), ("measured", "s", ".1f")],
        caption="The time to lose a phase-space distance of a hundredth from a "
        "start known to a millionth of a radian, to one decimal.",
    )
    return horizon, measured


def energy_scan(experiment: Experiment) -> list:
    """Exercise 2: the estimate of the exponent for five starts of increasing
    energy; record the table and return its rows."""
    rows = []
    for angle in (0.5, 1.0, 1.5, 2.0, 2.5):
        estimate = lyapunov_exponent(
            released(angle, angle), pendulum, dt, round(50.0 / dt)
        )
        middle = estimate.running[np.searchsorted(estimate.t, 25.0) - 1]
        rows.append((angle, middle, estimate.exponent))

    experiment.table(
        "energy-scan",
        rows,
        columns=[
            ("both angles", "rad", ".1f"),
            ("estimate after 25 s", "1/s", ".3f"),
            ("estimate after 50 s", "1/s", ".3f"),
        ],
        caption="The estimate of the exponent for five starts of increasing "
        "energy, to three decimals.",
    )
    return rows


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    modes_and_energy(experiment)
    regular_run, chaotic_run = energy_drift(experiment)
    experiment.number("drift-ratio", drift(chaotic_run) / drift(regular_run), ".0e")

    regular_gap, chaotic_gap, estimates = separations(regular_run, chaotic_run)
    # region: rate
    rate = estimates["chaotic"].exponent
    # endregion: rate
    experiment.figure(
        "fig-separation",
        partial(
            draw_separation, regular_run, chaotic_run, regular_gap, chaotic_gap, rate
        ),
    )
    experiment.number("regular-gap", regular_gap.max(), ".0e")
    experiment.number("chaotic-gap", chaotic_gap.max(), ".1f")
    experiment.number("offset", offset, ".0e")

    rows = lyapunov_table(experiment, estimates)
    experiment.number("regular-25", rows[0][1], ".3f")
    experiment.number("regular-100", rows[0][3], ".3f")
    experiment.number("chaotic-25", rows[1][1], ".2f")
    experiment.number("chaotic-100", rows[1][3], ".2f")
    experiment.number("e-folding", 1.0 / rate, ".2f")
    known_exponent(experiment)

    diverged, fine_estimate = step_halved(experiment, chaotic_run, estimates)
    experiment.number("diverged", diverged, ".0f")
    experiment.number(
        "fine-agreement",
        abs(fine_estimate.exponent / estimates["chaotic"].exponent - 1.0),
        ".0%",
    )

    horizon, measured = prediction_horizon(experiment, chaotic_run, rate)
    experiment.number("measured-over-horizon", measured / horizon, ".2f")
    experiment.number("hundred-times", np.log(100.0) / rate, ".1f")

    rows = energy_scan(experiment)
    experiment.number("settling-0", 1.0 - rows[0][2] / rows[0][1], ".0%")
    experiment.number("settling-1", 1.0 - rows[1][2] / rows[1][1], ".0%")
    experiment.number("jump", rows[2][1] / rows[1][1], ".0f")
    experiment.number("steady", abs(1.0 - rows[2][2] / rows[2][1]), ".0%")
    experiment.number("steady-angle", rows[2][0], ".1f")
    return experiment


if __name__ == "__main__":
    main(run)
