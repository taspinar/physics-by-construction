"""The experiment of the lesson "Crystal lattices and phonons".

The normal modes of a ring of masses and springs (``pbc.materials.phonons``)
against the closed-form dispersion of the monatomic and the diatomic chain:
the frequencies at every allowed wavenumber, the sound speed at long
wavelengths, the edges of the gap between the branches, and a wave packet
integrated in time that moves at the group velocity. Run it as a program to
write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.materials.experiments.crystal_lattices_and_phonons out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.materials.phonons import (
    closed_form_frequencies,
    diatomic_dispersion,
    group_velocity,
    monatomic_dispersion,
    packet_start,
    phase_velocity,
    ring_frequencies,
    ring_modes,
    sound_speed,
    verlet_packet,
    zone_boundary,
)
from pbc.verification.estimates import fitted_order

# region: setup
# Units: K = m1 = a = 1, so frequencies are in units of sqrt(K / m1) and
# wavenumbers in units of 1 / a.
K = 1.0
MONATOMIC = [1.0]  # one mass per cell
DIATOMIC = [1.0, 2.0]  # two masses per cell, m2 = 2 m1
CELLS = 24  # the ring of the dispersion
# endregion: setup

# region: sound
rings = [16, 32, 64, 128]
# endregion: sound

# region: packet
ATOMS = 1024  # the ring the packet travels on
START = 200.0  # the packet's starting centre (units of a)
k0 = np.pi / 2  # the carrier wavenumber (units of 1 / a)
widths = [10.0, 20.0, 40.0]  # the packet's widths (units of a)
DT = 0.01  # the time step (units of sqrt(m / K))
STEPS = 40000  # to t = 400
EVERY = 200  # record every 200 steps
# endregion: packet


def bound(value, limit):
    """A value at the level of round-off is shown as below ``limit``."""
    return f"{value:.1e}" if value > limit else f"below {limit:.0e}"


def dispersion(experiment: Experiment):
    """The squared frequencies of the ring of each chain against the
    closed form at the ring's allowed wavenumbers; record the table and
    return the largest differences."""
    rows, differences = [], []
    for name, masses in (("monatomic", MONATOMIC), ("diatomic", DIATOMIC)):
        ring = ring_frequencies(CELLS, masses, K)
        closed = closed_form_frequencies(CELLS, masses, K)
        difference = float(np.max(np.abs(ring**2 - closed**2)))
        differences.append(difference)
        rows.append((name, CELLS, ring.size, bound(difference, 1e-12)))
    experiment.table(
        "dispersion",
        rows,
        [
            ("chain", "", ""),
            ("cells", "", "d"),
            ("normal modes", "", "d"),
            ("largest difference of omega^2", "K/m1", ""),
        ],
        "The normal modes of a ring of 24 cells (K = m1 = a = 1, m2 = 2 m1 "
        "for the diatomic chain): the eigenvalues of the mass-weighted "
        "force-constant matrix against the closed-form omega^2 at the ring's "
        "allowed wavenumbers, compared as sorted sets.",
    )
    return differences


def branches(experiment: Experiment):
    """The edges of the diatomic chain's branches from the ring against
    their closed forms; record the table."""
    ring = ring_frequencies(CELLS, DIATOMIC, K)
    acoustic, optical = ring[:CELLS], ring[CELLS:]
    top, bottom, highest = zone_boundary(*DIATOMIC, K)
    measured = [
        acoustic.max(),
        optical.min(),
        optical.max(),
        optical.min() - acoustic.max(),
    ]
    closed = [top, bottom, highest, bottom - top]
    names = [
        "top of the acoustic branch, sqrt(2K/m2)",
        "bottom of the optical branch, sqrt(2K/m1)",
        "top of the optical branch, sqrt(2K(1/m1 + 1/m2))",
        "width of the gap",
    ]
    experiment.table(
        "branches",
        [
            (name, m, c, bound(abs(m - c), 1e-12))
            for name, m, c in zip(names, measured, closed, strict=True)
        ],
        [
            ("edge", "", ""),
            ("ring", "sqrt(K/m1)", ".6f"),
            ("closed form", "sqrt(K/m1)", ".6f"),
            ("difference", "sqrt(K/m1)", ""),
        ],
        "The edges of the branches of the diatomic chain (m2 = 2 m1) on the "
        "ring of 24 cells, whose allowed wavenumbers include 0 and pi / a, "
        "against their closed forms, to six decimals.",
    )
    return measured


def sound(experiment: Experiment):
    """omega / k of the lowest nonzero mode of rings of growing size against
    the sound speed of each chain; record the table and return the fitted
    orders of the gaps."""
    rows, gaps = [], {"monatomic": [], "diatomic": []}
    for cells in rings:
        k = 2 * np.pi / cells
        row = [cells, k]
        for name, masses in (("monatomic", MONATOMIC), ("diatomic", DIATOMIC)):
            slope = ring_frequencies(cells, masses, K)[1] / k
            gap = slope / sound_speed(masses, K) - 1
            gaps[name].append(abs(gap))
            row += [slope, gap]
        rows.append(tuple(row))
    k = [2 * np.pi / c for c in rings]
    orders = {name: fitted_order(k, g) for name, g in gaps.items()}
    assert all(abs(order - 2) < 0.05 for order in orders.values())
    experiment.table(
        "sound",
        rows,
        [
            ("cells", "", "d"),
            ("smallest k", "1/a", ".4f"),
            ("monatomic omega/k", "a sqrt(K/m1)", ".6f"),
            ("relative gap, monatomic", "", ".2e"),
            ("diatomic omega/k", "a sqrt(K/m1)", ".6f"),
            ("relative gap, diatomic", "", ".2e"),
        ],
        "The frequency divided by the wavenumber of the lowest nonzero mode of "
        "rings of growing size, against the sound speeds a sqrt(K/m) of the "
        "monatomic chain and a sqrt(K/(2(m1 + m2))) of the diatomic chain.",
    )
    return orders


def dispersion_data():
    """The modes of both rings with the wavenumber of each, for the figure."""
    return ring_modes(CELLS, MONATOMIC, K), ring_modes(CELLS, DIATOMIC, K)


def draw_dispersion(data) -> Figure:
    """The ring's frequencies on the closed-form dispersion: the monatomic
    chain with its sound line, the diatomic chain with its gap."""
    (w1, k1), (w2, k2) = data
    k = np.linspace(0, np.pi, 200)
    fig, (left, right) = plt.subplots(1, 2, figsize=(7.2, 3.4), sharey=True)
    left.plot(
        k,
        monatomic_dispersion(k, MONATOMIC[0], K),
        color=FIGURE_COLOURS[0],
        linestyle="-",
        label="closed form",
    )
    left.plot(
        k,
        sound_speed(MONATOMIC, K) * k,
        color=FIGURE_COLOURS[2],
        linestyle=":",
        label="sound line",
    )
    left.plot(
        k1, w1, "o", color=FIGURE_COLOURS[1], markerfacecolor="none", label="ring"
    )
    left.set_ylim(0, 2.1)
    left.set_title("monatomic chain", fontsize="medium")
    acoustic, optical = diatomic_dispersion(k, *DIATOMIC, K)
    right.plot(k, acoustic, color=FIGURE_COLOURS[0], linestyle="-", label="acoustic")
    right.plot(k, optical, color=FIGURE_COLOURS[0], linestyle="--", label="optical")
    top, bottom, _ = zone_boundary(*DIATOMIC, K)
    right.axhspan(top, bottom, color=FIGURE_COLOURS[2], alpha=0.15, label="gap")
    right.plot(
        k2, w2, "s", color=FIGURE_COLOURS[1], markerfacecolor="none", label="ring"
    )
    right.set_title("diatomic chain, m2 = 2 m1", fontsize="medium")
    for ax in (left, right):
        ax.set_xlim(0, np.pi)
        ax.set_xticks([0, np.pi / 2, np.pi], ["0", "pi/2a", "pi/a"])
        ax.set_xlabel("wavenumber k (units of 1/a)")
        ax.legend(fontsize="small", loc="lower right")
    left.set_ylabel("frequency omega (units of sqrt(K/m1))")
    return fig


def packets(experiment: Experiment):
    """Wave packets of three widths integrated by velocity Verlet: the
    speed of the centre against the group and the phase velocity; record
    the table and return the runs and the fitted order of the gap."""
    vg = float(group_velocity(k0, MONATOMIC[0], K))
    vp = float(phase_velocity(k0, MONATOMIC[0], K))
    runs, rows, gaps = [], [], []
    for width in widths:
        u, v = packet_start(ATOMS, START, width, k0, MONATOMIC[0], K)
        run = verlet_packet(u, v, MONATOMIC[0], K, DT, STEPS, EVERY)
        speed = float(np.polyfit(run.t, run.centre, 1)[0])
        gap = speed / vg - 1
        runs.append(run)
        gaps.append(abs(gap))
        rows.append((width, speed, vg, vp, gap))
    order = fitted_order(1 / np.array(widths), gaps)
    assert abs(order - 2) < 0.3
    assert max(gaps) < 0.01 and vp / vg - 1 > 0.2
    experiment.table(
        "packet",
        rows,
        [
            ("width", "a", "g"),
            ("speed of the centre", "a sqrt(K/m)", ".5f"),
            ("group velocity", "a sqrt(K/m)", ".5f"),
            ("phase velocity", "a sqrt(K/m)", ".5f"),
            ("relative gap from the group velocity", "", ".1e"),
        ],
        "The speed of the energy-weighted centre of a Gaussian packet of "
        "carrier wavenumber pi / (2a) on a monatomic ring of 1024 atoms, "
        "fitted over t = 0 to 400 (velocity Verlet, time step 0.01), against "
        "the closed-form group and phase velocities.",
    )
    return runs, order


def draw_packet(run) -> Figure:
    """The packet of the middle width at three times, and its centre against
    time with the lines of the group and the phase velocity."""
    vg = float(group_velocity(k0, MONATOMIC[0], K))
    vp = float(phase_velocity(k0, MONATOMIC[0], K))
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(6.4, 4.6))
    n = np.arange(ATOMS)
    styles = ("-", "--", ":")
    for index, style in zip((0, len(run.t) // 2, len(run.t) - 1), styles, strict=True):
        top.plot(
            n,
            run.u[index],
            color=FIGURE_COLOURS[0],
            linestyle=style,
            linewidth=0.8,
            label=f"t = {run.t[index]:.0f}",
        )
    top.set_xlim(100, 600)
    top.set_xlabel("atom n (position in units of a)")
    top.set_ylabel("displacement u (arbitrary units)")
    top.legend(fontsize="small", loc="upper right")
    bottom.plot(
        run.t,
        START + vp * run.t,
        color=FIGURE_COLOURS[2],
        linestyle=":",
        label="moving at the phase velocity",
    )
    bottom.plot(
        run.t,
        START + vg * run.t,
        color=FIGURE_COLOURS[0],
        linestyle="--",
        label="moving at the group velocity",
    )
    bottom.plot(
        run.t[::10],
        run.centre[::10],
        "o",
        color=FIGURE_COLOURS[1],
        markerfacecolor="none",
        label="centre of the packet",
    )
    bottom.set_xlabel("time t (units of sqrt(m/K))")
    bottom.set_ylabel("centre (units of a)")
    bottom.legend(fontsize="small", loc="upper left")
    fig.tight_layout()
    return fig


def equal_masses():
    """Exercise 1: the diatomic chain with m1 = m2: the width of the gap on
    the ring, and the largest difference of omega^2 between the diatomic
    closed form and the monatomic closed form of twice the atoms at half
    the spacing (in units of that spacing, the same allowed set)."""
    ring = ring_frequencies(CELLS, [1.0, 1.0], K)
    gap = ring[CELLS] - ring[CELLS - 1]
    diatomic = closed_form_frequencies(CELLS, [1.0, 1.0], K)
    single = closed_form_frequencies(2 * CELLS, [1.0], K)
    return gap, float(np.max(np.abs(diatomic**2 - single**2)))


def flat_optical_branch():
    """Exercise 2: the width of the optical branch, top minus bottom, on the
    ring and in closed form, for heavier and heavier m2."""
    rows = []
    for m2 in (2.0, 10.0, 100.0):
        ring = ring_frequencies(CELLS, [1.0, m2], K)
        _, bottom, highest = zone_boundary(1.0, m2, K)
        rows.append((m2, ring[-1] - ring[CELLS], highest - bottom))
    return rows


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()

    differences = dispersion(experiment)
    assert max(differences) < 1e-12
    edges = branches(experiment)
    experiment.figure("fig-dispersion", partial(draw_dispersion, dispersion_data()))
    experiment.number("gap-ratio", edges[1] / edges[0], ".4f")

    orders = sound(experiment)
    experiment.number("sound-order-mono", orders["monatomic"], ".2f")
    experiment.number("sound-order-di", orders["diatomic"], ".2f")

    runs, order = packets(experiment)
    experiment.figure("fig-packet", partial(draw_packet, runs[1]))
    experiment.number("packet-order", order, ".2f")
    vg = float(group_velocity(k0, MONATOMIC[0], K))
    vp = float(phase_velocity(k0, MONATOMIC[0], K))
    experiment.number("phase-excess", vp / vg - 1, ".2f")
    # Velocity Verlet's own dispersion, sin(w~ dt / 2) = w dt / 2, raises
    # the group velocity by the factor 1 / sqrt(1 - (w dt / 2)^2).
    half = float(monatomic_dispersion(k0, MONATOMIC[0], K)) * DT / 2
    experiment.number("verlet-excess", 1 / np.sqrt(1 - half**2) - 1, ".1e")

    gap, difference = equal_masses()
    experiment.number("equal-gap", bound(abs(gap), 1e-12), "")
    experiment.number("equal-difference", bound(difference, 1e-12), "")
    experiment.table(
        "flat-optical",
        flat_optical_branch(),
        [
            ("m2", "m1", "g"),
            ("width of the optical branch, ring", "sqrt(K/m1)", ".5f"),
            ("closed form", "sqrt(K/m1)", ".5f"),
        ],
        "The width of the optical branch, its top at k = 0 minus its bottom "
        "at k = pi / a, on the ring of 24 cells and in closed form, for three "
        "masses m2.",
    )
    return experiment


if __name__ == "__main__":
    main(run)
