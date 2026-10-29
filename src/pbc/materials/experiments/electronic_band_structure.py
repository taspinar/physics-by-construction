"""The experiment of the lesson "Electronic band structure".

The tight-binding Hamiltonian of a ring (``pbc.materials.bands``) against
the closed-form bands of the one-band and the two-site chain: the energies
at every allowed wavenumber, the counting of the states, the effective mass
of the band bottom, the levels at the Fermi level of a half-filled band and
of a filled band, and a packet under a uniform force that oscillates instead
of accelerating. Run it as a program to write the figures and numbers of the
page:

    uv run --locked --no-dev \\
        python -m pbc.materials.experiments.electronic_band_structure out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.materials.bands import (
    bloch_centre,
    chain_hamiltonian,
    closed_form_energies,
    counting,
    effective_mass,
    filled,
    gaussian_packet,
    one_band,
    propagate,
    ring_energies,
    ring_hamiltonian,
    translation,
    two_site_bands,
)
from pbc.verification.estimates import fitted_order

# region: setup
# Units: hbar = a = 1 and the hopping t = 1, so energies are in units of t,
# wavenumbers in units of 1 / a, and times in units of hbar / t.
T = 1.0  # the hopping
EPS0 = 0.0  # the site energy of the one-band chain
DELTA = 0.5  # the two-site chain: site energies +Delta and -Delta
CELLS = 24  # the ring of the bands
# endregion: setup

# region: filling
# Rings with N = 2 mod 4 cells, so that N electrons fill whole levels.
fillings = [18, 34, 66, 130]
# endregion: filling

# region: bloch
SITES = 600  # the open chain
WIDTH = 10.0  # the packet's width (sites)
forces = [0.05, 0.1, 0.2]  # the force F (units of t / a)
NARROW = 1.5  # a narrow packet, at F = 0.1
# endregion: bloch


def bound(value, limit):
    """A value at the level of round-off is shown as below ``limit``."""
    return f"{value:.1e}" if value > limit else f"below {limit:.0e}"


def bands_check(experiment: Experiment):
    """The ring's energies of both chains against the closed-form bands at
    the allowed wavenumbers; record the table and return the differences."""
    rows, differences = [], []
    for name, onsite in (("one band", [EPS0]), ("two sites", [DELTA, -DELTA])):
        ring = ring_energies(CELLS, onsite, T)
        difference = float(
            np.max(np.abs(ring - closed_form_energies(CELLS, onsite, T)))
        )
        differences.append(difference)
        rows.append((name, CELLS, ring.size, bound(difference, 1e-12)))
    experiment.table(
        "bands",
        rows,
        [
            ("chain", "", ""),
            ("cells", "", "d"),
            ("states", "", "d"),
            ("largest difference of the energy", "t", ""),
        ],
        "The eigenvalues of the tight-binding Hamiltonian of a ring of 24 "
        "cells (t = 1, eps0 = 0 for the one-band chain, Delta = 0.5 for the "
        "two-site chain) against the closed-form bands at the ring's allowed "
        "wavenumbers, compared as sorted sets.",
    )
    return differences


def band_modes(onsite):
    """The ring's energies with the wavenumber |k| of each state, in
    [0, pi]: the wavenumber of the largest power of the cell-to-cell
    Fourier transform of the eigenvector. For the figure; a real
    eigenvector holds +k and -k equally."""
    energies, vectors = np.linalg.eigh(ring_hamiltonian(CELLS, onsite, T))
    per_cell = len(onsite)
    power = np.sum(
        np.abs(np.fft.fft(vectors.reshape(CELLS, per_cell, -1), axis=0)) ** 2, axis=1
    )
    k = 2 * np.pi * np.fft.fftfreq(CELLS)
    return energies, np.abs(k[np.argmax(power, axis=0)])


def draw_bands(data) -> Figure:
    """The two-site chain's ring energies on the closed-form bands, the
    one-band chain folded into the same zone, the gap, and the highest
    filled level of one electron per site."""
    energies, k = data
    q = np.linspace(-np.pi, np.pi, 300)
    lower, upper = two_site_bands(q, DELTA, T)
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    ax.axhspan(-DELTA, DELTA, color=FIGURE_COLOURS[2], alpha=0.15, label="gap, 2 Delta")
    folded_lower, folded_upper = two_site_bands(q, 0.0, T)
    ax.plot(q, folded_lower, color=FIGURE_COLOURS[2], linestyle=":", label="Delta = 0")
    ax.plot(q, folded_upper, color=FIGURE_COLOURS[2], linestyle=":")
    ax.plot(
        q,
        lower,
        color=FIGURE_COLOURS[0],
        linestyle="-",
        label="lower band, closed form",
    )
    ax.plot(
        q,
        upper,
        color=FIGURE_COLOURS[0],
        linestyle="--",
        label="upper band, closed form",
    )
    # Each level is drawn at +|k| and -|k|: the ring holds both states.
    k, energies = np.concatenate([k, -k]), np.concatenate([energies, energies])
    filled_mask = energies < 0
    ax.plot(
        k[filled_mask],
        energies[filled_mask],
        "o",
        color=FIGURE_COLOURS[1],
        label="ring, filled",
    )
    ax.plot(
        k[~filled_mask],
        energies[~filled_mask],
        "o",
        color=FIGURE_COLOURS[1],
        markerfacecolor="none",
        label="ring, empty",
    )
    ax.set_xlim(-np.pi, np.pi)
    ax.set_xticks([-np.pi, 0, np.pi], ["-pi/a", "0", "pi/a"])
    ax.set_xlabel("wavenumber k (units of 1/a, a the cell length)")
    ax.set_ylabel("energy E (units of t)")
    ax.legend(fontsize="small", loc="upper left", bbox_to_anchor=(1.0, 1.0))
    return fig


def one_band_checks(experiment: Experiment):
    """The counting of the states of rings of growing size against its
    closed form, and the effective mass from the two lowest levels; record
    the table and return the fitted order of the mass gap."""
    probe = np.linspace(-2.5 * T, 2.5 * T, 2001)
    rows, gaps = [], []
    for cells in (16, 32, 64, 128):
        energies = ring_energies(cells, [EPS0], T)
        below = np.searchsorted(energies, probe, side="left")
        deviation = float(np.max(np.abs(below - cells * counting(probe, EPS0, T))))
        assert deviation <= 1 + 1e-9
        k = 2 * np.pi / cells
        curvature = (energies[1] - energies[0]) / k**2
        mass = 1 / (2 * curvature)
        gap = mass / effective_mass(T) - 1
        gaps.append(gap)
        rows.append((cells, deviation, mass, effective_mass(T), gap))
    order = fitted_order([2 * np.pi / c for c in (16, 32, 64, 128)], gaps)
    assert abs(order - 2) < 0.05
    experiment.table(
        "one-band",
        rows,
        [
            ("cells", "", "d"),
            ("largest miscount", "states", ".3f"),
            ("mass from the two lowest levels", "hbar^2/(t a^2)", ".6f"),
            ("m* = hbar^2/(2 t a^2)", "hbar^2/(t a^2)", ".6f"),
            ("relative gap", "", ".2e"),
        ],
        "The one-band ring (t = 1, eps0 = 0): the largest difference between "
        "the number of levels below E and N arccos(-E / 2t) / pi over a grid "
        "of energies, and the mass hbar^2 k^2 / (2 (E_1 - E_0)) of the "
        "smallest nonzero wavenumber against the effective mass of the band "
        "bottom.",
    )
    return order


def draw_counting() -> Figure:
    """The count of the levels of a small ring below E, a staircase, on the
    closed form N arccos(-E / 2t) / pi."""
    cells = 16
    energies = ring_energies(cells, [EPS0], T)
    e = np.linspace(-2.6 * T, 2.6 * T, 600)
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.plot(
        e,
        cells * counting(e, EPS0, T),
        color=FIGURE_COLOURS[0],
        linestyle="--",
        label="closed form N arccos(-E/2t) / pi",
    )
    ax.step(
        e,
        np.searchsorted(energies, e, side="left"),
        where="post",
        color=FIGURE_COLOURS[1],
        linestyle="-",
        label="levels of the ring below E",
    )
    ax.set_xlabel("energy E (units of t)")
    ax.set_ylabel("number of levels below E (dimensionless)")
    ax.legend(fontsize="small", loc="upper left")
    return fig


def fill(experiment: Experiment):
    """One electron per site: the gap between the highest filled and the
    lowest empty level of the one-band ring (half filled) and of the
    two-site ring (lower band filled), for rings of growing size; record
    the table and return the fitted order of the one-band gap."""
    rows, gaps = [], []
    for cells in fillings:
        lo, hi = filled(ring_energies(cells, [EPS0], T), cells)
        metal = hi - lo
        m = (cells // 2 - 1) // 2  # the filled levels are n = -m, ..., m
        k_m, k_next = 2 * np.pi * m / cells, 2 * np.pi * (m + 1) / cells
        closed = float(one_band(k_next, EPS0, T) - one_band(k_m, EPS0, T))
        lo2, hi2 = filled(ring_energies(cells, [DELTA, -DELTA], T), 2 * cells)
        gaps.append(metal)
        rows.append((cells, metal, closed, cells * metal, hi2 - lo2))
    order = fitted_order([1 / c for c in fillings], gaps)
    assert abs(order - 1) < 0.05
    experiment.table(
        "filling",
        rows,
        [
            ("cells N", "", "d"),
            ("one band: gap at the Fermi level", "t", ".5f"),
            ("closed form", "t", ".5f"),
            ("N times the gap", "t", ".4f"),
            ("two sites: gap at the Fermi level", "t", ".5f"),
        ],
        "One electron per site, two electrons per level: the gap between the "
        "highest filled and the lowest empty level of the one-band ring "
        "(t = 1) against its closed form, and of the two-site ring "
        "(Delta = 0.5), for rings of growing size.",
    )
    return order


def bloch(experiment: Experiment):
    """Packets on the open chain under a uniform force, propagated exactly:
    the centre against its closed form, the largest displacement, and the
    return of the state after one Bloch period; record the table and
    return the run of the middle force."""
    rows, runs = [], {}
    cases = [(f, WIDTH) for f in forces] + [(0.1, NARROW)]
    for force, width in cases:
        psi0 = gaussian_packet(SITES, SITES / 2, width)
        h = chain_hamiltonian(SITES, T, force)
        period = 2 * np.pi / force
        times = np.linspace(0, 2 * period, 401)  # holds T_B / 2 and T_B
        run = propagate(h, psi0, times)
        shift = translation(psi0)
        closed = bloch_centre(times, run.centre[0], shift, T, force)
        error = float(np.max(np.abs(run.centre - closed)))
        back = 1 - abs(np.vdot(psi0, run.psi[200]))
        assert error < 1e-9 and back < 1e-9
        rows.append(
            (
                force,
                width,
                period,
                np.ptp(run.centre),
                4 * T * shift.real / force,
                4 * T / force,
                bound(error, 1e-9),
                bound(back, 1e-9),
            )
        )
        runs[(force, width)] = (run, shift)
    experiment.table(
        "bloch",
        rows,
        [
            ("force F", "t/a", "g"),
            ("width", "a", "g"),
            ("Bloch period 2 pi hbar/(F a)", "hbar/t", ".2f"),
            ("swing of the centre", "a", ".4f"),
            ("closed form 4 t Re<T>/F", "a", ".4f"),
            ("band width over F, 4t/F", "a", ".1f"),
            ("largest gap from the closed-form centre", "a", ""),
            ("1 - |<psi(0)|psi(T_B)>|", "", ""),
        ],
        "A Gaussian packet at rest (k0 = 0) on an open chain of 600 sites "
        "(t = 1) under a uniform force, propagated exactly for two Bloch "
        "periods: the swing of its centre, the largest gap from the closed "
        "form, and the overlap with the start after one period.",
    )
    return runs[(0.1, WIDTH)]


def draw_bloch(data) -> Figure:
    """The centre of the packet against time: exact propagation, the closed
    form, and the free particle of the effective mass."""
    run, shift = data
    force = 0.1
    t = np.linspace(0, run.t[-1], 400)
    x0 = run.centre[0]
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    ax.plot(
        t,
        bloch_centre(t, x0, shift, T, force) - x0,
        color=FIGURE_COLOURS[0],
        linestyle="--",
        label="closed form",
    )
    ax.plot(
        t,
        force * t**2 / (2 * effective_mass(T)),
        color=FIGURE_COLOURS[2],
        linestyle=":",
        label="free particle of mass m*",
    )
    ax.plot(
        run.t[::8],
        run.centre[::8] - x0,
        "o",
        color=FIGURE_COLOURS[1],
        markerfacecolor="none",
        label="exact propagation",
    )
    ax.set_ylim(-5, 4.6 * T / force)
    ax.set_xlabel("time t (units of hbar/t)")
    ax.set_ylabel("displacement of the centre (units of a)")
    ax.legend(fontsize="small", loc="upper right")
    return fig


def gap_closes():
    """Exercise 1: the gap at the Fermi level of the two-site ring of 24
    cells, filled with one electron per site, for shrinking Delta."""
    rows = []
    for delta in (0.5, 0.1, 0.01, 0.0):
        lo, hi = filled(ring_energies(CELLS, [delta, -delta], T), 2 * CELLS)
        rows.append((delta, hi - lo, 2 * delta))
    return rows


def band_widths():
    """Exercise 2: the width of each band of the two-site chain, from the
    ring of 24 cells, against sqrt(Delta^2 + 4 t^2) - Delta."""
    energies = ring_energies(CELLS, [DELTA, -DELTA], T)
    lower, upper = energies[:CELLS], energies[CELLS:]
    closed = np.sqrt(DELTA**2 + 4 * T**2) - DELTA
    return lower.max() - lower.min(), upper.max() - upper.min(), closed


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()

    differences = bands_check(experiment)
    assert max(differences) < 1e-12
    experiment.figure("fig-bands", partial(draw_bands, band_modes([DELTA, -DELTA])))

    order = one_band_checks(experiment)
    experiment.number("mass-order", order, ".2f")
    experiment.figure("fig-counting", draw_counting)

    fill_order = fill(experiment)
    experiment.number("fill-order", fill_order, ".2f")

    experiment.figure("fig-bloch", partial(draw_bloch, bloch(experiment)))

    experiment.table(
        "gap-closes",
        gap_closes(),
        [
            ("Delta", "t", "g"),
            ("gap at the Fermi level, ring", "t", ".6f"),
            ("2 Delta", "t", ".6f"),
        ],
        "The two-site ring of 24 cells with one electron per site: the gap "
        "between the highest filled and the lowest empty level against "
        "2 Delta, to six decimals.",
    )
    lower, upper, closed = band_widths()
    experiment.number("width-lower", lower, ".6f")
    experiment.number("width-upper", upper, ".6f")
    experiment.number("width-closed", closed, ".6f")
    return experiment


if __name__ == "__main__":
    main(run)
