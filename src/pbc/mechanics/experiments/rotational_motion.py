"""The experiment of the lesson "Rotational motion, torque, and angular momentum".

The inertia tensor of a disc and the parallel-axis theorem, and a toy
gyroscope as a heavy symmetric top (``pbc.mechanics.rigid_body``): torque
against the rate of the angular momentum, the conserved energy and
components of the angular momentum, the precession rate against the
fast-top limit, steady precession, and the same run in other units. Run it
as a program to write the figures and numbers of the page:

    uv run --locked --no-dev python -m pbc.mechanics.experiments.rotational_motion out
"""

from functools import cache, partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.mechanics.rigid_body import (
    Top,
    axial_momentum,
    fast_top_rate,
    inertia_tensor,
    mean_precession_rate,
    parallel_axis,
    simulate_top,
    steady_precession_rates,
    tilted_start,
    top_energy,
)
from pbc.verification.estimates import fitted_order, invariant_drift

# region: setup
mass, disc_radius, arm = (
    0.5,
    0.04,
    0.05,
)  # kg, m, m: the disc and its distance from the pivot
g = 9.81  # m/s²
tilt = 0.5  # angle of the axis from the vertical, rad
duration = 3.0  # s
# endregion: setup

# region: top
i3 = 0.5 * mass * disc_radius**2  # about the axis of the disc, kg m²
i1 = 0.25 * mass * disc_radius**2 + mass * arm**2  # about the pivot, across the axis
top = Top(mass=mass, length=arm, i1=i1, i3=i3, g=g)
# endregion: top

# region: spins
spins = [100.0, 200.0, 400.0, 800.0]  # omega_3, rad/s
# endregion: spins


def bound(value, limit):
    """A difference at the level of round-off is shown as below ``limit``."""
    return f"{value:.1e}" if value > limit else f"below {limit:.0e}"


def disc_points(rings):
    """A flat disc of ``mass`` and ``disc_radius`` in the x-y plane as point
    masses at the midpoints of ``rings`` rings of equal width, each cut into
    four times as many equal sectors, each mass in proportion to its area."""
    edges = np.linspace(0.0, disc_radius, rings + 1)
    middles = 0.5 * (edges[1:] + edges[:-1])
    sectors = 4 * rings
    angles = (np.arange(sectors) + 0.5) * 2 * np.pi / sectors
    rho, phi = np.meshgrid(middles, angles, indexing="ij")
    area = np.repeat(np.pi * (edges[1:] ** 2 - edges[:-1] ** 2) / sectors, sectors)
    positions = np.stack(
        [
            rho.ravel() * np.cos(phi.ravel()),
            rho.ravel() * np.sin(phi.ravel()),
            np.zeros(rho.size),
        ],
        axis=1,
    )
    return mass * area / area.sum(), positions


def inertia_of_a_disc(experiment: Experiment):
    """The inertia tensor of the disc of point masses about its centre for
    finer and finer divisions, against the closed forms, and the tensor
    about the pivot directly and by the parallel-axis theorem; record the
    table and return the rows and the difference of the two tensors."""
    rows, steps, errors = [], [], []
    for rings in (4, 8, 16, 32):
        masses, positions = disc_points(rings)
        tensor = inertia_tensor(masses, positions)
        error = abs(tensor[2, 2] / i3 - 1.0)
        rows.append((rings, tensor[2, 2], tensor[0, 0], error))
        steps.append(disc_radius / rings)
        errors.append(error)
    experiment.table(
        "inertia-of-a-disc",
        rows,
        columns=[
            ("rings", "", "d"),
            ("moment about the axis", "kg m²", ".4e"),
            ("moment across the axis", "kg m²", ".4e"),
            ("relative error against m r² / 2", "", ".1e"),
        ],
        caption="The principal moments of the disc built from point masses about its "
        "centre, for four divisions, with the relative error of the moment about the "
        "axis against the closed form.",
    )
    masses, positions = disc_points(32)
    centre = inertia_tensor(masses, positions)
    pivot = inertia_tensor(masses, positions + np.array([0.0, 0.0, arm]))
    shifted = parallel_axis(centre, mass, [0.0, 0.0, arm])
    return fitted_order(steps, errors), float(np.max(np.abs(pivot - shifted)) / i1)


@cache
def gyroscope(spin, precession=0.0, model=top, step=5e-4):
    """The top released with its axis at ``tilt`` and the ``spin``, with the
    given starting ``precession`` rate, over ``duration``; each run is
    computed once and shared by the examples that use it."""
    q, momentum = tilted_start(model, tilt, spin, precession)
    return simulate_top(model, q, momentum, step, round(duration / step))


def conservation(experiment: Experiment):
    """The checks of one run at the second spin: torque against the rate of
    change of the angular momentum, and the drift of the energy and of the
    two conserved components of the angular momentum; record the table and
    return the run."""
    motion = gyroscope(spins[1])
    rate = (motion.momentum[2:] - motion.momentum[:-2]) / (
        motion.t[2:] - motion.t[:-2]
    )[:, None]
    torque = np.array([top.torque(q) for q in motion.q[1:-1]])
    torque_gap = np.max(np.linalg.norm(rate - torque, axis=1)) / np.max(
        np.linalg.norm(torque, axis=1)
    )
    energy = top_energy(top, motion)
    vertical = motion.momentum[:, 2]
    axial = axial_momentum(motion)
    experiment.table(
        "conservation",
        [
            ("dL/dt by central differences against the torque", f"{torque_gap:.1e}"),
            ("energy", f"{invariant_drift(energy):.1e}"),
            ("vertical component of L", bound(invariant_drift(vertical), 1e-12)),
            ("component of L along the axis", f"{invariant_drift(axial):.1e}"),
        ],
        columns=[
            ("quantity", "", ""),
            ("largest relative difference or drift", "", ""),
        ],
        caption="The checks of one run of the gyroscope: the rate of change of the "
        "angular momentum against the torque of gravity, relative to the largest "
        "torque, and the largest relative drift of the energy and of the two "
        "components of the angular momentum that the exact motion keeps.",
    )
    return motion


def draw_axis_path(motion) -> Figure:
    """The tip of the axis seen from above: precession with nodding."""
    axes = motion.axes()
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    ax.plot(
        100 * arm * axes[:, 0],
        100 * arm * axes[:, 1],
        color=FIGURE_COLOURS[0],
        linestyle="-",
        linewidth=1.0,
        label="tip of the axis",
    )
    ax.plot(
        100 * arm * axes[0, 0],
        100 * arm * axes[0, 1],
        color=FIGURE_COLOURS[1],
        marker="o",
        linestyle="",
        label="release",
    )
    ax.plot(
        0.0,
        0.0,
        color="#57606a",
        marker="+",
        markersize=10,
        linestyle="",
        label="pivot",
    )
    ax.set_aspect("equal")
    ax.set_xlabel("x of the centre of mass (cm)")
    ax.set_ylabel("y of the centre of mass (cm)")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncols=3, fontsize="small")
    return fig


def precession(experiment: Experiment):
    """The mean precession rate of the gyroscope released without
    precession, for each spin, against the fast-top limit m g l / (I₃ omega₃)
    and the slow steady rate; record the table and return the spins, the
    relative differences from the limit, and their fitted power."""
    rows, differences = [], []
    for spin in spins:
        measured = mean_precession_rate(gyroscope(spin))
        limit = fast_top_rate(top, spin)
        slow, _ = steady_precession_rates(top, tilt, spin)
        difference = abs(measured / limit - 1.0)
        rows.append((spin, measured, slow, limit, difference))
        differences.append(difference)
    experiment.table(
        "precession",
        rows,
        columns=[
            ("spin", "rad/s", ".0f"),
            ("measured mean precession rate", "rad/s", ".4f"),
            ("slow steady rate", "rad/s", ".4f"),
            ("fast-top limit m g l / (I3 spin)", "rad/s", ".4f"),
            ("relative difference from the limit", "", ".1e"),
        ],
        caption="The mean rate at which the axis of the gyroscope turns about the "
        "vertical, released without precession, for four spins: measured from the "
        "simulation, the slow rate of steady precession at the same tilt, and the "
        "fast-top limit, to four decimals.",
    )
    # The difference as a power of 1 / spin, which falls as the spin grows.
    power = fitted_order(1.0 / np.array(spins), differences)
    return np.array(spins), np.array(differences), power


def draw_precession(spins_, differences) -> Figure:
    """The relative difference of the measured rate from the fast-top limit
    over the spin, log-log, with the reference slope minus two."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.plot(
        spins_,
        differences,
        color=FIGURE_COLOURS[0],
        marker="o",
        linestyle="-",
        label="measured",
    )
    reference = differences[0] * (spins_ / spins_[0]) ** -2.0
    ax.plot(
        spins_,
        reference,
        color="#57606a",
        linestyle=":",
        label="reference slope minus two",
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks(spins_, labels=[f"{spin:.0f}" for spin in spins_])
    ax.minorticks_off()
    ax.set_xlabel("spin (rad/s)")
    ax.set_ylabel("relative difference from the limit")
    ax.legend(loc="upper right", fontsize="small")
    return fig


def steady(experiment: Experiment):
    """The gyroscope released on its slow steady precession at the second
    spin: the measured rate against the slow root, and how far the tilt
    moves; record the table and return the relative difference."""
    spin = spins[1]
    slow, fast = steady_precession_rates(top, tilt, spin)
    motion = gyroscope(spin, precession=slow)
    measured = mean_precession_rate(motion)
    angles = np.arccos(np.clip(motion.axes()[:, 2], -1.0, 1.0))
    experiment.table(
        "steady",
        [(spin, slow, measured, np.ptp(angles), fast)],
        columns=[
            ("spin", "rad/s", ".0f"),
            ("slow steady rate", "rad/s", ".6f"),
            ("measured rate", "rad/s", ".6f"),
            ("largest change of the tilt", "rad", ".0e"),
            ("fast steady rate", "rad/s", ".1f"),
        ],
        caption="The gyroscope released on its slow steady precession: the rate of "
        "the closed form and the measured rate, the range of the tilt during the "
        "run, and the other, fast, steady rate at the same tilt.",
    )
    return abs(measured / slow - 1.0)


def other_units(experiment: Experiment):
    """The unit check: the same gyroscope in grams, centimetres, and
    seconds, at the third spin; record the table and return the relative
    difference of the two measured rates."""
    spin = spins[2]
    grams, centimetres = 1e3, 1e2
    cgs = Top(
        mass=mass * grams,
        length=arm * centimetres,
        i1=i1 * grams * centimetres**2,
        i3=i3 * grams * centimetres**2,
        g=g * centimetres,
    )
    si_rate = mean_precession_rate(gyroscope(spin))
    cgs_rate = mean_precession_rate(gyroscope(spin, model=cgs))
    difference = abs(cgs_rate / si_rate - 1.0)
    experiment.table(
        "other-units",
        [
            ("kg, m, s", si_rate, fast_top_rate(top, spin)),
            ("g, cm, s", cgs_rate, fast_top_rate(cgs, spin)),
        ],
        columns=[
            ("units of the run", "", ""),
            ("measured mean precession rate", "rad/s", ".5f"),
            ("fast-top limit", "rad/s", ".5f"),
        ],
        caption="The same gyroscope simulated in two systems of units: the precession "
        "rates in radians per second, to five decimals.",
    )
    return difference


def longer_arm(experiment: Experiment):
    """Exercise 1: the precession rate with the disc twice as far from the
    pivot; record the table and return the ratio of the rates."""
    spin = spins[2]
    far = Top(
        mass=mass,
        length=2 * arm,
        i1=0.25 * mass * disc_radius**2 + mass * (2 * arm) ** 2,
        i3=i3,
        g=g,
    )
    rates = [
        mean_precession_rate(gyroscope(spin)),
        mean_precession_rate(gyroscope(spin, model=far)),
    ]
    experiment.table(
        "longer-arm",
        [
            (arm, rates[0], fast_top_rate(top, spin)),
            (2 * arm, rates[1], fast_top_rate(far, spin)),
        ],
        columns=[
            ("distance of the disc from the pivot", "m", ".2f"),
            ("measured mean precession rate", "rad/s", ".4f"),
            ("fast-top limit", "rad/s", ".4f"),
        ],
        caption="The precession rate of the gyroscope with the disc at two distances "
        "from the pivot, at one spin, to four decimals.",
    )
    return rates[1] / rates[0]


def tilted_spin(experiment: Experiment):
    """Exercise 2: the angle between the angular velocity and the angular
    momentum of the disc spun about an axis through its centre tilted from
    its symmetry axis; record the table and return the rows."""
    centre = np.diag([0.25, 0.25, 0.5]) * mass * disc_radius**2
    rows = []
    for degrees in (0, 15, 30, 45, 60, 90):
        alpha = np.radians(degrees)
        omega = np.array([np.sin(alpha), 0.0, np.cos(alpha)])
        momentum = centre @ omega
        cosine = momentum @ omega / np.linalg.norm(momentum)
        found = np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))
        expected = (
            degrees - np.degrees(np.arctan(0.5 * np.tan(alpha)))
            if degrees < 90
            else 0.0
        )
        rows.append((degrees, found, expected))
    experiment.table(
        "tilted-spin",
        rows,
        columns=[
            ("angle of the spin axis from the symmetry axis", "degree", "d"),
            ("angle between L and omega, from the tensor", "degree", ".2f"),
            ("the same, from tan(beta) = tan(alpha) / 2", "degree", ".2f"),
        ],
        caption="The angle between the angular momentum and the angular velocity of "
        "a disc spun about a tilted axis through its centre, to two decimals.",
    )
    return rows


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    order, parallel_gap = inertia_of_a_disc(experiment)
    experiment.number("disc-order", order, ".2f")
    experiment.number("parallel-gap", bound(parallel_gap, 1e-12))

    motion = conservation(experiment)
    experiment.figure("fig-axis-path", partial(draw_axis_path, motion))

    spins_, differences, power = precession(experiment)
    experiment.figure(
        "fig-precession-rate", partial(draw_precession, spins_, differences)
    )
    experiment.number("precession-power", power, ".2f")
    experiment.number("largest-spin-difference", differences[-1], ".0e")

    experiment.number("steady-difference", bound(steady(experiment), 1e-6))
    experiment.number("units-difference", bound(other_units(experiment), 1e-9))
    experiment.number("arm-ratio", longer_arm(experiment), ".3f")
    tilted_spin(experiment)
    return experiment


if __name__ == "__main__":
    main(run)
