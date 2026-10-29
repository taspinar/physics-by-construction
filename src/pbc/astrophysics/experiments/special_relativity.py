"""The experiment of the lesson "Special relativity and spacetime".

Events and four-momenta under Lorentz boosts
(``pbc.astrophysics.special_relativity``): the interval and the metric kept
by every boost, events carried along the hyperbolas of constant interval,
time dilation and length contraction read off transformed events, a
collision whose four-momentum is conserved in every frame while its
Newtonian momentum is not, and the approach to Newton's mechanics at low
speed. Run it as a program to write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.astrophysics.experiments.special_relativity out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.astrophysics.special_relativity import (
    METRIC,
    add_velocities,
    boost,
    elastic_collision,
    four_momentum,
    galilean,
    interval,
    invariant_mass,
    kinetic_energy,
    lorentz_factor,
    moving_rod_length,
    newtonian_kinetic_energy,
    proper_time,
    rapidity,
    velocity,
)
from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.verification.estimates import fitted_order

# region: setup
# Units: c = 1, so a velocity is a fraction of the speed of light.
# Events (t, x, y, z): two timelike, two spacelike, one on the light cone.
events = np.array(
    [
        [1.0, 0.0, 0.0, 0.0],
        [2.0, 0.5, -0.3, 0.2],
        [0.0, 1.0, 0.0, 0.0],
        [0.4, -1.5, 0.7, 0.0],
        [1.0, 0.6, 0.8, 0.0],
    ]
)
# Boost velocities, along x and along an oblique direction.
velocities = [
    [0.3, 0.0, 0.0],
    [0.9, 0.0, 0.0],
    [-0.99, 0.0, 0.0],
    [0.4, 0.4, 0.4],
    [0.0, -0.7, 0.6],
]
# endregion: setup

# region: dilation
speeds = [0.1, 0.5, 0.9, 0.99, 0.999]
# endregion: dilation

# region: collision
masses = (1.0, 3.0)
lab_velocities = (0.8, -0.4)  # along x, before the collision
frames = [-0.6, -0.3, 0.0, 0.3, 0.6, 0.9]  # velocities of the observers along x
# endregion: collision

# region: limit
betas = [1e-3, 3e-3, 1e-2, 3e-2, 0.1, 0.3]
# endregion: limit


def bound(value, limit):
    """A value at the level of round-off is shown as below ``limit``."""
    return f"{value:.1e}" if value > limit else f"below {limit:.0e}"


def invariants(experiment: Experiment):
    """Every event of ``events`` boosted with every velocity of
    ``velocities``: the largest change of the interval and of the metric,
    and the gap between two collinear boosts and the boost of their summed
    rapidity; record the table and return the largest of all."""
    rows, largest = [], 0.0
    s2 = interval(events)
    for v in velocities:
        matrix = boost(v)
        moved = events @ matrix.T
        change = np.max(np.abs(interval(moved) - s2))
        metric = np.max(np.abs(matrix.T @ METRIC @ matrix - METRIC))
        speed = float(np.linalg.norm(v))
        direction = np.asarray(v) / speed
        half = boost(direction * np.tanh(rapidity(speed) / 2))
        composed = np.max(np.abs(half @ half - matrix))
        largest = max(largest, change, metric, composed)
        rows.append(
            (
                "(" + ", ".join(f"{c:g}" for c in v) + ")",
                speed,
                float(lorentz_factor(speed)),
                bound(change, 1e-12),
                bound(metric, 1e-12),
                bound(composed, 1e-12),
            )
        )
    experiment.table(
        "invariants",
        rows,
        [
            ("boost velocity", "c", ""),
            ("speed", "c", ".4g"),
            ("gamma", "", ".4f"),
            ("largest change of the interval", "", ""),
            ("largest change of the metric", "", ""),
            ("two half-rapidity boosts against one", "", ""),
        ],
        "Five events boosted into five frames (c = 1): the largest change of "
        "their squared intervals, the largest entry of the boost's change of "
        "the metric, and the largest gap between two boosts of half the "
        "rapidity and the one boost, to the level of round-off.",
    )
    return largest


def draw_spacetime() -> Figure:
    """A spacetime diagram: the light cone, the hyperbolas of squared
    interval -1 and +1, the events (1, 0) and (0, 1) carried by boosts along
    x, and the axes of the frame that moves with the largest of them."""
    shown = [-0.6, -0.3, 0.0, 0.3, 0.6]
    fig, ax = plt.subplots(figsize=(6.0, 5.0))
    w = np.linspace(-1.2, 1.2, 200)
    ax.plot(
        np.sinh(w),
        np.cosh(w),
        color=FIGURE_COLOURS[0],
        linestyle="--",
        linewidth=1,
        label="squared interval -1 (timelike)",
    )
    ax.plot(
        np.cosh(w),
        np.sinh(w),
        color=FIGURE_COLOURS[1],
        linestyle="-.",
        linewidth=1,
        label="squared interval +1 (spacelike)",
    )
    edge = np.array([-1.9, 1.9])
    ax.plot(edge, edge, color="#57606a", linestyle=":", linewidth=1, label="light cone")
    ax.plot(edge, -edge, color="#57606a", linestyle=":", linewidth=1)
    for event, colour, marker, name in (
        (
            [1.0, 0.0, 0.0, 0.0],
            FIGURE_COLOURS[0],
            "o",
            "boosted images of (t, x) = (1, 0)",
        ),
        (
            [0.0, 1.0, 0.0, 0.0],
            FIGURE_COLOURS[1],
            "s",
            "boosted images of (t, x) = (0, 1)",
        ),
    ):
        moved = np.array([boost([b, 0.0, 0.0]) @ event for b in shown])
        ax.plot(
            moved[:, 1],
            moved[:, 0],
            marker,
            color=colour,
            markerfacecolor="none",
            label=name,
        )
    beta = shown[-1]
    ax.plot(
        edge * beta,
        edge,
        color=FIGURE_COLOURS[2],
        linewidth=1.2,
        label=f"axes of the frame moving with {beta} c",
    )
    ax.plot(edge, edge * beta, color=FIGURE_COLOURS[2], linewidth=1.2)
    ax.set_xlim(-1.9, 1.9)
    ax.set_ylim(-1.9, 1.9)
    ax.set_aspect("equal")
    ax.set_xlabel("x (light-seconds)")
    ax.set_ylabel("t (s)")
    ax.legend(
        loc="lower center", bbox_to_anchor=(0.5, 1.0), ncols=2, fontsize="x-small"
    )
    return fig


def dilation(experiment: Experiment):
    """For each speed of ``speeds``: the lab time of one tick of a moving
    clock, from the boosted event of the tick; the clock's own time along
    that worldline; the measured length of a moving rod of unit length;
    record the table and return the largest gap from 1/gamma and gamma."""
    rows, largest = [], 0.0
    for beta in speeds:
        gamma = float(lorentz_factor(beta))
        tick = np.linalg.inv(boost([beta, 0.0, 0.0])) @ np.array([1.0, 0.0, 0.0, 0.0])
        own = proper_time(np.array([[0.0, 0.0, 0.0, 0.0], tick]))
        length = moving_rod_length(1.0, beta)
        largest = max(
            largest, abs(tick[0] / gamma - 1), abs(own - 1), abs(length * gamma - 1)
        )
        rows.append((beta, gamma, tick[0], tick[1], own, length))
    experiment.table(
        "dilation",
        rows,
        [
            ("speed", "c", "g"),
            ("gamma", "", ".4f"),
            ("lab time of one tick", "s", ".4f"),
            ("lab distance of one tick", "light-s", ".4f"),
            ("clock's own time", "s", ".6f"),
            ("length of a unit rod", "light-s", ".6f"),
        ],
        "A clock that ticks once per second and a rod one light-second long, "
        "at rest in a frame moving with the given speed: where and when the "
        "lab sees the tick, the time along the clock's worldline, and the "
        "rod's length from its two ends at one lab time, to four or six "
        "decimals.",
    )
    return largest


def collision(experiment: Experiment):
    """The elastic head-on collision of ``masses`` with ``lab_velocities``,
    seen by observers moving with each velocity of ``frames``: the change of
    the total four-momentum and of the total Newtonian momentum; record the
    table and return the Newtonian changes and the largest relativistic one."""
    before = np.array(
        [
            four_momentum(m, [u, 0.0, 0.0])
            for m, u in zip(masses, lab_velocities, strict=True)
        ]
    )
    after = elastic_collision(before)
    rows, newtonian, largest = [], [], 0.0
    for w in frames:
        matrix = boost([w, 0.0, 0.0])
        b, a = before @ matrix.T, after @ matrix.T
        change = np.max(np.abs(a.sum(axis=0) - b.sum(axis=0)))
        m = np.array(masses)
        n_before = np.sum(m * velocity(b)[:, 0])
        n_after = np.sum(m * velocity(a)[:, 0])
        newtonian.append(n_after - n_before)
        largest = max(largest, change)
        rows.append(
            (
                w,
                float(invariant_mass(b.sum(axis=0))),
                b.sum(axis=0)[1],
                bound(change, 1e-12),
                n_before,
                n_after,
            )
        )
    experiment.table(
        "collision",
        rows,
        [
            ("observer's velocity", "c", "g"),
            ("invariant mass", "m", ".6f"),
            ("total momentum", "m c", ".4f"),
            ("change of the four-momentum", "m c", ""),
            ("Newtonian momentum before", "m c", ".4f"),
            ("Newtonian momentum after", "m c", ".4f"),
        ],
        "An elastic head-on collision of masses m and 3 m at 0.8 c and -0.4 c in "
        "the lab, seen by observers moving along x: the invariant mass and the "
        "relativistic momentum of the pair, the largest change of its total "
        "four-momentum, and the Newtonian momentum sum of m v before and after.",
    )
    return np.array(newtonian), largest, before, after


def draw_collision(newtonian_at) -> Figure:
    """The change of the total Newtonian momentum of the collision against
    the observer's velocity, beside the change of the relativistic momentum."""
    w = np.linspace(-0.95, 0.95, 191)
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    ax.axhline(
        0.0,
        color=FIGURE_COLOURS[0],
        linestyle="--",
        linewidth=1.5,
        label="relativistic momentum m gamma v (conserved)",
    )
    ax.plot(
        w,
        newtonian_at(w),
        color=FIGURE_COLOURS[1],
        linestyle="-",
        label="Newtonian momentum m v",
    )
    ax.plot(
        frames,
        newtonian_at(np.array(frames)),
        "o",
        color=FIGURE_COLOURS[1],
        markerfacecolor="none",
        label="observers of the table",
    )
    ax.set_xlabel("observer's velocity along x (c)")
    ax.set_ylabel("change of total momentum (m c)")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncols=2, fontsize="small")
    return fig


def newtonian_change(before, after, w):
    """The change of the total Newtonian momentum of the collision seen by
    observers moving with each velocity of the array ``w``."""
    m = np.array(masses)
    out = []
    for speed in np.atleast_1d(w):
        matrix = boost([speed, 0.0, 0.0])
        b, a = velocity(before @ matrix.T)[:, 0], velocity(after @ matrix.T)[:, 0]
        out.append(np.sum(m * a) - np.sum(m * b))
    return np.array(out)


def low_speed(experiment: Experiment):
    """For each beta of ``betas``: the relative gap of the kinetic energy
    from Newton's, of the sum of two velocities beta from velocity
    addition, and of the boosted event (1, 2 beta) from Galileo's
    transformation; record the table and return the gaps and their orders."""
    ke = kinetic_energy(1.0, betas) / newtonian_kinetic_energy(1.0, betas) - 1
    b = np.asarray(betas)
    addition = 2 * b / add_velocities(b, b) - 1
    frames_gap = []
    for beta in betas:
        event = np.array([1.0, 2 * beta, 0.0, 0.0])
        lorentz = boost([beta, 0.0, 0.0]) @ event
        galileo = galilean([beta, 0.0, 0.0]) @ event
        frames_gap.append(np.max(np.abs(lorentz[:2] / galileo[:2] - 1)))
    gaps = np.array([ke, addition, frames_gap])
    orders = [fitted_order(betas[::-1], g[::-1]) for g in gaps]
    for order in orders:
        assert abs(order - 2) < 0.05
    experiment.table(
        "limit",
        [(beta, *gaps[:, i]) for i, beta in enumerate(betas)],
        [
            ("beta", "c", "g"),
            ("kinetic energy / Newton's - 1", "", ".3e"),
            ("2 beta / velocity sum - 1", "", ".3e"),
            ("event (1, 2 beta): Lorentz / Galileo - 1", "", ".3e"),
        ],
        "The relative gap between the relativistic and the Newtonian result "
        "at speeds beta, for the kinetic energy, the sum of two velocities "
        "beta, and the coordinates of the event (t, x) = (1, 2 beta) seen from "
        "the frame moving with beta, to four significant digits.",
    )
    return gaps, orders


def draw_limit(gaps) -> Figure:
    """The three relative gaps against beta, log-log, with a reference line
    of slope two."""
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    for gap, colour, marker, name in zip(
        gaps,
        FIGURE_COLOURS,
        ("o", "s", "^"),
        ("kinetic energy", "velocity addition", "Lorentz against Galileo"),
        strict=False,
    ):
        ax.loglog(
            betas,
            gap,
            marker,
            color=colour,
            markerfacecolor="none",
            linestyle="-",
            linewidth=0.8,
            label=name,
        )
    b = np.geomspace(betas[0], betas[-1], 50)
    ax.loglog(
        b, 0.2 * b**2, color="#57606a", linestyle=":", label="reference: slope two"
    )
    ax.set_xlabel("speed beta (units of c)")
    ax.set_ylabel("relative gap from Newton's result")
    ax.legend(fontsize="small")
    return fig


def muon(experiment: Experiment):
    """Exercise 1: muons made 15 km up at 0.995 c with a mean lifetime of
    2.197 microseconds (given values): the mean distance before decay with
    and without time dilation, and the fraction that reaches the ground."""
    c = 299_792_458.0
    lifetime, beta, height = 2.197e-6, 0.995, 15e3
    gamma = float(lorentz_factor(beta))
    naive = beta * c * lifetime
    dilated = gamma * naive
    experiment.number("muon-gamma", gamma, ".2f")
    experiment.number("muon-naive", naive, ".0f")
    experiment.number("muon-dilated", dilated / 1e3, ".2f")
    experiment.number("muon-survive-naive", np.exp(-height / naive), ".1e")
    experiment.number("muon-survive", np.exp(-height / dilated), ".3f")


def twins():
    """Exercise 2: the clock that travels out at 0.8 c for 5 years of the
    Earth's time and back at the same speed (given values), against the
    clock that stays: the proper times of the two worldlines, in years."""
    home = np.array([[0.0, 0.0, 0.0, 0.0], [10.0, 0.0, 0.0, 0.0]])
    away = np.array([[0.0, 0.0, 0.0, 0.0], [5.0, 4.0, 0.0, 0.0], [10.0, 0.0, 0.0, 0.0]])
    return proper_time(home), proper_time(away)


def sticking(beta):
    """Exercise 3: two unit masses meet head-on at +beta and -beta and stick:
    the mass of the lump less the masses of the parts, against Newton's
    kinetic energy of the two, m beta² (c = 1)."""
    total = four_momentum(1.0, [beta, 0.0, 0.0]) + four_momentum(1.0, [-beta, 0.0, 0.0])
    return float(invariant_mass(total)) - 2.0, beta**2


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()

    largest = invariants(experiment)
    assert largest < 1e-12
    experiment.figure("fig-spacetime", draw_spacetime)

    assert dilation(experiment) < 1e-12

    newtonian, largest, before, after = collision(experiment)
    assert largest < 1e-12 and np.min(np.abs(newtonian)) > 0.05
    experiment.figure(
        "fig-collision",
        partial(draw_collision, partial(newtonian_change, before, after)),
    )
    lab = velocity(after)[:, 0]
    experiment.number("after-light", lab[0], ".4f")
    experiment.number("after-heavy", lab[1], ".4f")
    experiment.number("newtonian-lab", newtonian[frames.index(0.0)], ".4f")

    gaps, orders = low_speed(experiment)
    experiment.figure("fig-limit", partial(draw_limit, gaps))
    experiment.number("limit-order", min(orders), ".3f")
    experiment.number("ke-coefficient", gaps[0][0] / betas[0] ** 2, ".4f")

    muon(experiment)
    home, away = twins()
    experiment.number("twin-home", home, ".1f")
    experiment.number("twin-away", away, ".1f")
    rows = []
    for beta in (0.01, 0.1, 0.5, 0.9):
        gain, newton = sticking(beta)
        rows.append((beta, gain, newton, gain / newton))
    experiment.table(
        "sticking",
        rows,
        [
            ("beta", "c", "g"),
            ("mass gained", "", ".6f"),
            ("Newton's kinetic energy", "", ".6f"),
            ("ratio", "", ".4f"),
        ],
        "Two unit masses meeting head-on at beta and -beta and sticking: the "
        "mass of the lump less two, against the Newtonian kinetic energy of the "
        "pair (c = 1), to six decimals.",
    )
    return experiment


if __name__ == "__main__":
    main(run)
