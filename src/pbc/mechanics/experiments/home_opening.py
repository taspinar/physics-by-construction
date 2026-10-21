"""The opening figure of the home page: a double pendulum, simulated, with
the change of its energy as a second figure.

The figure is drawn from the implementation of the lesson "The double
pendulum and chaos" (``pbc.mechanics.chaos``), which its lesson validates:
the equations reduce to the single pendulum, the small oscillations have the
periods of the two normal modes, the Lagrangian lesson derives the same
equations, and the classical Runge-Kutta method keeps the energy. The start
is the lesson's chaotic one, both rods released at rest at 2 rad. A chaotic
motion is followed only as long as the step does not matter, so the figure
uses a finer step than the lesson and records how far a run at half the step
departs from it. Run it as a program to write the figure and its numbers:

    uv run --locked --no-dev python -m pbc.mechanics.experiments.home_opening out
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring.design import FIGURE_COLOURS, PAGE
from pbc.experiment import Experiment, main
from pbc.mechanics.chaos import double_pendulum, double_pendulum_energy
from pbc.mechanics.dynamics import State, Trajectory, simulate
from pbc.mechanics.integrators import rk4_step

LABEL = "fig-opening"
ENERGY_LABEL = "fig-opening-energy"
MASS, LENGTH = 1.0, 1.0  # kg, m
ANGLE = 2.0  # rad, both rods at the start
DURATION = 10.0  # s
STEP = 0.002  # s
START = State(t=0.0, x=[ANGLE, ANGLE], v=[0.0, 0.0])
PENDULUM = double_pendulum(MASS, MASS, LENGTH, LENGTH)


def run_at(step: float) -> Trajectory:
    """The start followed for ``DURATION`` with the classical Runge-Kutta
    method at ``step`` (s)."""
    return simulate(START, PENDULUM, step, round(DURATION / step), step=rk4_step)


def bobs(trajectory: Trajectory) -> tuple[np.ndarray, np.ndarray]:
    """The positions (m) of the first and the second bob, arrays of shape
    (n, 2), with the pivot at the origin and y upwards."""
    first = LENGTH * np.column_stack(
        [np.sin(trajectory.x[:, 0]), -np.cos(trajectory.x[:, 0])]
    )
    second = first + LENGTH * np.column_stack(
        [np.sin(trajectory.x[:, 1]), -np.cos(trajectory.x[:, 1])]
    )
    return first, second


def energy_change(trajectory: Trajectory) -> np.ndarray:
    """The change of the energy from its start, relative to the start."""
    energy = double_pendulum_energy(
        trajectory.x, trajectory.v, MASS, MASS, LENGTH, LENGTH
    )
    return (energy - energy[0]) / abs(energy[0])


def half_step_gap(trajectory: Trajectory) -> float:
    """The largest distance (m) between the second bob of ``trajectory`` and
    that of a run at half the step, at the times both have."""
    _, coarse = bobs(trajectory)
    _, fine = bobs(run_at(STEP / 2))
    return float(np.max(np.linalg.norm(coarse - fine[::2], axis=1)))


def _pose(ax, trajectory: Trajectory, index: int, filled: bool) -> None:
    """The rods and the bobs at the step ``index``: solid with filled bobs,
    or dashed with open ones."""
    first, second = bobs(trajectory)
    xs = [0.0, first[index, 0], second[index, 0]]
    ys = [0.0, first[index, 1], second[index, 1]]
    ink = PAGE["text"] if filled else PAGE["muted"]
    ax.plot(xs, ys, color=ink, linewidth=1.8, linestyle="-" if filled else "--")
    ax.plot(
        xs[1:],
        ys[1:],
        linestyle="none",
        marker="o",
        markersize=8,
        markeredgecolor=ink,
        markerfacecolor=ink if filled else PAGE["plate"],
    )


def draw_opening(trajectory: Trajectory) -> Figure:
    """The paths of both bobs, the first on its circle about the pivot and
    the second, with the pendulum at the start and at the end. The two paths
    differ in colour, in width, and by the label at the start of each."""
    fig, motion = plt.subplots(figsize=(5.6, 5.6))
    first, second = bobs(trajectory)
    motion.plot(first[:, 0], first[:, 1], color=FIGURE_COLOURS[1], linewidth=2.6)
    motion.plot(second[:, 0], second[:, 1], color=FIGURE_COLOURS[0], linewidth=0.9)
    _pose(motion, trajectory, 0, True)
    _pose(motion, trajectory, -1, False)
    motion.plot([0.0], [0.0], marker="+", color=PAGE["text"], markersize=10)
    # Each label beside its bob at the start, clear of the rods.
    for bob, name, colour, offset, align in (
        (first, "first bob", FIGURE_COLOURS[1], (-12, -4), "right"),
        (second, "second bob", FIGURE_COLOURS[0], (10, 6), "left"),
    ):
        motion.annotate(
            name,
            bob[0],
            xytext=offset,
            textcoords="offset points",
            color=colour,
            fontsize=10,
            ha=align,
        )
    reach = 2 * LENGTH * 1.05
    motion.set_xlim(-reach, reach)
    motion.set_ylim(-reach, reach)
    motion.set_aspect("equal")
    motion.set_xlabel("horizontal position (m)")
    motion.set_ylabel("height above the pivot (m)")
    motion.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


def draw_energy(trajectory: Trajectory, change: np.ndarray) -> Figure:
    """The relative change of the energy against time."""
    fig, energy = plt.subplots(figsize=(6.4, 2.8))
    energy.plot(
        trajectory.t,
        change,
        color=FIGURE_COLOURS[1],
        linewidth=1.0,
        linestyle="-",
    )
    energy.axhline(0.0, color=PAGE["muted"], linewidth=0.8, linestyle=":")
    energy.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
    energy.set_xlim(0.0, DURATION)
    energy.set_xlabel("time (s)")
    energy.set_ylabel("relative energy change\n(dimensionless)")
    energy.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


def run() -> Experiment:
    """The figures of the home page and the numbers stated beside them."""
    experiment = Experiment()
    trajectory = run_at(STEP)
    change = energy_change(trajectory)
    experiment.figure(LABEL, lambda: draw_opening(trajectory))
    experiment.figure(ENERGY_LABEL, lambda: draw_energy(trajectory, change))
    experiment.number("angle", ANGLE, ".0f")
    experiment.number("duration", DURATION, ".0f")
    experiment.number("step", STEP, ".3f")
    experiment.number("energy-change", float(np.max(np.abs(change))), ".0e")
    experiment.number("half-step-gap", half_step_gap(trajectory), ".0e")
    return experiment


if __name__ == "__main__":
    main(run)
