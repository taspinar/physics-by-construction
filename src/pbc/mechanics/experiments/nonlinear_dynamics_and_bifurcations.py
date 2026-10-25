"""The experiment of the lesson "Nonlinear dynamics and bifurcations".

A bead on a rotating hoop and a self-excited oscillator
(``pbc.mechanics.bifurcation``): the bifurcation diagram of the bead against
the known threshold and branch, the decay near the threshold against the
linearised rate and the algebraic decay at it, the limit cycle and its
amplitude, and the oscillations about an equilibrium. Run it as a program to
write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.nonlinear_dynamics_and_bifurcations out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.mechanics.bifurcation import (
    critical_rotation,
    final_amplitude,
    hoop,
    hoop_equilibrium,
    hoop_linear_rate,
    limit_cycle_amplitude,
    self_excited,
)
from pbc.mechanics.dynamics import State, simulate
from pbc.mechanics.integrators import rk4_step

# region: setup
g, radius = 9.81, 0.25  # m/s², m
gamma = 2.0  # damping rate of the bead, 1/s
tilt = 0.3  # starting angle of the bead from the bottom, rad
omega_c = critical_rotation(g, radius)  # rad/s
# endregion: setup

# region: diagram
ratios = np.round(
    np.concatenate(
        [
            np.linspace(0.5, 0.95, 10),
            np.linspace(0.96, 0.99, 4),
            np.linspace(1.01, 1.04, 4),
            np.linspace(1.05, 2.0, 20),
        ]
    ),
    2,
)  # rotation rates in units of the critical rate
settle_time, dt = 80.0, 0.005  # s
# endregion: diagram

# region: cycle
mus = np.array([-0.2, -0.1, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5])
cycle_time, cycle_dt = 400.0, 0.02  # in units of the inverse natural frequency
# endregion: cycle


def bound(value, limit=1e-6):
    """A difference at the level of round-off is shown as below ``limit``."""
    return f"{value:.0e}" if value > limit else f"below {limit:.0e}"


def released(angles):
    """Copies of the bead released at rest at the given ``angles``."""
    angles = np.asarray(angles, dtype=np.float64)
    return State(t=0.0, x=angles, v=np.zeros_like(angles))


def bifurcation_diagram(experiment: Experiment):
    """The angle the bead settles at, released on either side, at every
    rotation rate of the diagram, against the stable equilibrium; record the
    table of every fourth rate and return the rates, the settled angles of
    both starts, and the bracket of the threshold."""
    omegas = ratios * omega_c
    both = np.concatenate([omegas, omegas])
    starts = np.concatenate([np.full(len(omegas), tilt), np.full(len(omegas), -tilt)])
    run = simulate(
        released(starts),
        hoop(g, radius, both, gamma),
        dt,
        round(settle_time / dt),
        step=rk4_step,
    )
    # An angle below the precision of the table is shown as zero, not as a
    # signed zero whose sign no physics decides.
    settled = np.where(np.abs(run.x[-1]) < 5e-5, 0.0, run.x[-1])
    plus, minus = settled[: len(omegas)], settled[len(omegas) :]
    equilibrium = hoop_equilibrium(g, radius, omegas)

    # The bottom holds the bead where it settles there from both sides, to
    # the precision of the table; the threshold lies between the last such
    # rate and the first at which the bead leaves it.
    held = (plus == 0.0) & (minus == 0.0)
    below, above = omegas[held].max(), omegas[~held].min()

    pick = [*range(0, len(omegas), 4), int(np.argmax(~held))]
    experiment.table(
        "bifurcation-diagram",
        [
            (ratios[i], omegas[i], equilibrium[i], plus[i], minus[i])
            for i in sorted(set(pick))
        ],
        columns=[
            ("rotation rate over the critical rate", "", ".2f"),
            ("rotation rate", "rad/s", ".3f"),
            ("stable angle, closed form", "rad", ".4f"),
            ("settled angle, released at plus", "rad", ".4f"),
            ("settled angle, released at minus", "rad", ".4f"),
        ],
        caption="The angle at which the damped bead comes to rest on the rotating "
        "hoop, released on either side of the bottom, at a selection of rotation "
        "rates including the first above the threshold, against the stable "
        "equilibrium of the closed form, to four decimals.",
    )
    # The gap from the closed form, of the angles as computed, not as shown.
    gap = np.max(np.abs(np.abs(run.x[-1]) - np.concatenate([equilibrium, equilibrium])))
    return omegas, plus, minus, below, above, gap


def draw_bifurcation(omegas, plus, minus) -> Figure:
    """The bifurcation diagram: the settled angles over the rotation rate,
    with the branches of the closed form."""
    dense = np.linspace(0.5 * omega_c, 2.0 * omega_c, 600)
    branch = hoop_equilibrium(g, radius, dense)
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    stable_bottom = dense <= omega_c
    ax.plot(
        dense[stable_bottom],
        0 * dense[stable_bottom],
        color=FIGURE_COLOURS[0],
        linestyle="-",
        label="stable, closed form",
    )
    ax.plot(
        dense[~stable_bottom],
        0 * dense[~stable_bottom],
        color=FIGURE_COLOURS[0],
        linestyle="--",
        label="unstable, closed form",
    )
    ax.plot(
        dense[~stable_bottom],
        branch[~stable_bottom],
        color=FIGURE_COLOURS[0],
        linestyle="-",
    )
    ax.plot(
        dense[~stable_bottom],
        -branch[~stable_bottom],
        color=FIGURE_COLOURS[0],
        linestyle="-",
    )
    ax.plot(
        omegas,
        plus,
        color=FIGURE_COLOURS[1],
        marker="o",
        markersize=4,
        linestyle="",
        label=r"settled, released at $+\theta_0$",
    )
    ax.plot(
        omegas,
        minus,
        color=FIGURE_COLOURS[2],
        marker="s",
        markersize=4,
        markerfacecolor="white",
        linestyle="",
        label=r"settled, released at $-\theta_0$",
    )
    ax.axvline(omega_c, color="#57606a", linestyle=":", label="critical rate")
    ax.set_xlabel("rotation rate of the hoop (rad/s)")
    ax.set_ylabel("angle of the bead (rad)")
    ax.legend(loc="upper left", fontsize="small")
    return fig


def near_threshold(experiment: Experiment):
    """The decay of the bead released near the bottom, below the threshold
    and at it: the measured exponential rate against the linearised one,
    and at the threshold the algebraic decay; record the table and return
    the run, its rates, and the slope of the inverse square angle."""
    near = np.array([0.95, 0.97, 0.98, 0.99, 0.995, 1.0])
    omegas = near * omega_c
    run = simulate(
        released(np.full(len(near), tilt)),
        hoop(g, radius, omegas, gamma),
        dt,
        round(120.0 / dt),
        step=rk4_step,
    )
    late = run.t >= 60.0
    measured = np.array(
        [
            -np.polyfit(run.t[late], np.log(np.abs(run.x[late, i])), 1)[0]
            for i in range(len(near) - 1)
        ]
    )
    linear = hoop_linear_rate(g, radius, omegas[:-1], gamma)
    # At the threshold the cubic term predicts
    # 1 / theta² = 1 / theta_0² + (Omega_c² / 2 gamma) t
    # once the fast motion has died: a straight line in time.
    slope = np.polyfit(run.t[late], run.x[late, -1] ** -2.0, 1)[0]

    experiment.table(
        "near-threshold",
        [
            (near[i], measured[i], linear[i], bound(abs(measured[i] / linear[i] - 1.0)))
            for i in range(len(near) - 1)
        ],
        columns=[
            ("rotation rate over the critical rate", "", ".3f"),
            ("measured decay rate", "1/s", ".4f"),
            ("linearised decay rate", "1/s", ".4f"),
            ("relative difference", "", ""),
        ],
        caption="The rate at which the angle of the bead decays below the threshold, "
        "fitted to the logarithm of the angle over the second minute, against the "
        "slow rate of the linearised equation, to four decimals.",
    )
    return run, near, slope


def draw_critical_slowing(run, near) -> Figure:
    """The angle over time near and at the threshold, log-log, with the
    reference slope of the algebraic decay."""
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    t = run.t[1:]
    styles = [
        ("--", FIGURE_COLOURS[1]),
        ("-.", FIGURE_COLOURS[2]),
        ((0, (3, 1, 1, 1, 1, 1)), FIGURE_COLOURS[3]),
    ]
    for (line, colour), r in zip(styles, (0.95, 0.98, 0.995), strict=True):
        i = int(np.argmin(np.abs(near - r)))
        ax.plot(
            t,
            np.abs(run.x[1:, i]),
            color=colour,
            linestyle=line,
            label=f"{r:.3g} of the critical rate",
        )
    ax.plot(
        t,
        np.abs(run.x[1:, -1]),
        color=FIGURE_COLOURS[0],
        linestyle="-",
        linewidth=2.0,
        label="at the critical rate",
    )
    reference = np.sqrt(2.0 * gamma) / omega_c / np.sqrt(t)
    ax.plot(
        t,
        reference,
        color="#57606a",
        linestyle=":",
        linewidth=2.0,
        label="reference slope minus one half",
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_ylim(1e-6, 1.0)
    ax.set_xlabel("time (s)")
    ax.set_ylabel("angle of the bead (rad)")
    ax.legend(loc="lower left", fontsize="small")
    return fig


def limit_cycle(experiment: Experiment):
    """The amplitude the self-excited oscillator settles at for each mu,
    from a start at one, against 2 sqrt(mu); record the table and return the
    amplitudes and the fitted threshold and slope of the squared amplitude."""
    run = simulate(
        released(np.ones(len(mus))),
        self_excited(mus),
        cycle_dt,
        round(cycle_time / cycle_dt),
        step=rk4_step,
    )
    amplitude = final_amplitude(run, 4 * np.pi)
    predicted = limit_cycle_amplitude(mus)
    rows = []
    for mu, found, expected in zip(mus, amplitude, predicted, strict=True):
        if mu < 0:
            rows.append(
                (f"{mu:.2f}", "below 1e-6" if found < 1e-6 else f"{found:.1e}", "0", "")
            )
        else:
            rows.append(
                (
                    f"{mu:.2f}",
                    f"{found:.4f}",
                    f"{expected:.4f}",
                    f"{abs(found / expected - 1):.0e}",
                )
            )
    small = (mus > 0) & (mus <= 0.2)
    slope, intercept = np.polyfit(mus[small], amplitude[small] ** 2, 1)

    experiment.table(
        "limit-cycle",
        rows,
        columns=[
            ("mu", "", ""),
            ("settled amplitude", "", ""),
            ("2 sqrt(mu)", "", ""),
            ("relative difference", "", ""),
        ],
        caption="The amplitude of the self-excited oscillator after four hundred "
        "time units from a start at one, read over the last two periods, against "
        "the amplitude of the averaged equation, in the dimensionless units of the "
        "oscillator.",
    )
    return amplitude, -intercept / slope, slope


def draw_limit_cycle() -> Figure:
    """Two motions of the self-excited oscillator at mu = 0.2, from inside
    and from outside the cycle, in the phase plane."""
    mu = 0.2
    run = simulate(
        State(t=0.0, x=[0.05, 2.5], v=[0.0, 0.0]),
        self_excited([mu, mu]),
        cycle_dt,
        round(60.0 / cycle_dt),
        step=rk4_step,
    )
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    ax.plot(
        run.x[:, 0],
        run.v[:, 0],
        color=FIGURE_COLOURS[0],
        linestyle="-",
        linewidth=0.8,
        label="start inside",
    )
    ax.plot(
        run.x[:, 1],
        run.v[:, 1],
        color=FIGURE_COLOURS[1],
        linestyle="--",
        linewidth=0.8,
        label="start outside",
    )
    angle = np.linspace(0, 2 * np.pi, 300)
    a = float(limit_cycle_amplitude(mu))
    ax.plot(
        a * np.cos(angle),
        a * np.sin(angle),
        color="#57606a",
        linestyle=":",
        linewidth=2.0,
        label=r"circle of radius $2\sqrt{\mu}$",
    )
    ax.set_aspect("equal")
    ax.set_xlabel("x (dimensionless)")
    ax.set_ylabel("velocity (dimensionless)")
    ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize="small")
    return fig


def crossing_period(t, signal):
    """The mean time between upward zero crossings of ``signal``, by linear
    interpolation between the samples around each crossing."""
    up = np.nonzero((signal[:-1] < 0) & (signal[1:] >= 0))[0]
    times = t[up] - signal[up] * (t[up + 1] - t[up]) / (signal[up + 1] - signal[up])
    return float(np.mean(np.diff(times)))


def tilted_oscillation(experiment: Experiment):
    """Exercise 1: the frequency of small oscillations about the tilted
    equilibrium, with weak damping, against the linearised frequency;
    record the table and return the rows."""
    weak = 0.1  # 1/s
    near = np.array([1.2, 1.5, 2.0])
    omegas = near * omega_c
    equilibrium = hoop_equilibrium(g, radius, omegas)
    run = simulate(
        released(equilibrium + 0.01),
        hoop(g, radius, omegas, weak),
        0.002,
        10000,
        step=rk4_step,
    )
    stiffness = omegas**2 * np.sin(equilibrium) ** 2
    rows = []
    for i in range(len(near)):
        measured = 2 * np.pi / crossing_period(run.t, run.x[:, i] - equilibrium[i])
        rows.append(
            (near[i], equilibrium[i], measured, np.sqrt(stiffness[i] - weak**2))
        )
    experiment.table(
        "tilted-oscillation",
        rows,
        columns=[
            ("rotation rate over the critical rate", "", ".1f"),
            ("stable angle", "rad", ".4f"),
            ("measured angular frequency", "rad/s", ".4f"),
            ("linearised angular frequency", "rad/s", ".4f"),
        ],
        caption="The angular frequency of small oscillations of the weakly damped "
        "bead about its tilted equilibrium, measured from the zero crossings and "
        "from the linearised equation, to four decimals.",
    )
    return rows


def undamped_period(experiment: Experiment):
    """Exercise 2: the period of the undamped bead about the bottom below
    the threshold, at two amplitudes, against the linearised period;
    record the table and return the rows."""
    near = np.array([0.6, 0.9, 0.99])
    amplitudes = (0.01, 0.2)
    omegas = np.concatenate([near * omega_c, near * omega_c])
    starts = np.concatenate([np.full(len(near), a) for a in amplitudes])
    run = simulate(
        released(starts), hoop(g, radius, omegas, 0.0), 0.002, 15000, step=rk4_step
    )
    linear = 2 * np.pi / np.sqrt(g / radius - (near * omega_c) ** 2)
    rows = []
    for i, r in enumerate(near):
        small = crossing_period(run.t, run.x[:, i])
        large = crossing_period(run.t, run.x[:, i + len(near)])
        rows.append((r, linear[i], small, large))
    experiment.table(
        "undamped-period",
        rows,
        columns=[
            ("rotation rate over the critical rate", "", ".2f"),
            ("linearised period", "s", ".3f"),
            ("period at amplitude 0.01 rad", "s", ".3f"),
            ("period at amplitude 0.2 rad", "s", ".3f"),
        ],
        caption="The period of the undamped bead oscillating about the bottom below "
        "the threshold, from the linearised equation and measured at two "
        "amplitudes, to three decimals.",
    )
    return rows


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    omegas, plus, minus, below, above, gap = bifurcation_diagram(experiment)
    experiment.figure(
        "fig-hoop-bifurcation", partial(draw_bifurcation, omegas, plus, minus)
    )
    experiment.number("omega-c", omega_c, ".3f")
    experiment.number("below", below, ".3f")
    experiment.number("above", above, ".3f")
    experiment.number("branch-gap", bound(gap))

    decay, near, slope = near_threshold(experiment)
    experiment.figure(
        "fig-critical-slowing", partial(draw_critical_slowing, decay, near)
    )
    experiment.number("inverse-square-slope", slope, ".3f")
    experiment.number("cubic-slope", omega_c**2 / (2 * gamma), ".3f")
    experiment.number(
        "slope-difference", abs(slope / (omega_c**2 / (2 * gamma)) - 1), ".0e"
    )

    _, threshold, cycle_slope = limit_cycle(experiment)
    experiment.figure("fig-limit-cycle", draw_limit_cycle)
    experiment.number("hopf-threshold", threshold, ".0e")
    experiment.number("hopf-slope", cycle_slope, ".3f")

    rows = tilted_oscillation(experiment)
    experiment.number(
        "tilted-difference", max(abs(m / p - 1) for _, _, m, p in rows), ".0e"
    )
    rows = undamped_period(experiment)
    experiment.number("near-small", rows[-1][2] / rows[-1][1], ".3f")
    experiment.number("near-large", rows[-1][3] / rows[-1][1], ".3f")
    return experiment


if __name__ == "__main__":
    main(run)
