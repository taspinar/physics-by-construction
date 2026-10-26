"""The experiment of the lesson "Waveguides and antenna basics".

The modes of a WR-90 rectangular waveguide (``pbc.electromagnetism.waveguides``):
the cut-off frequencies of its cross-section from a sparse finite-difference
eigenproblem against the closed form, as the grid is refined; the guide
simulated in time with the FDTD solver of ``pbc.electromagnetism.fdtd``,
driven above and below the cut-off of its first mode, with the measured
wavenumber and decay against the guide's dispersion relation. Then the
radiation of a wire (``pbc.electromagnetism.antennas``): the patterns of a
short and a half-wave dipole built by superposing short current elements,
against the closed forms, with directivity and radiation resistance, and two
elements as the element pattern times an array factor. Run it as a program
to write the figures and numbers of the page:

    uv run --locked --no-dev python -m \\
        pbc.electromagnetism.experiments.waveguides_and_antenna_basics out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.electromagnetism.antennas import (
    IMPEDANCE_OF_FREE_SPACE,
    array_factor,
    directivity,
    far_field,
    half_wave_dipole_pattern,
    half_wave_radiation_resistance,
    radiation_resistance,
    short_dipole_pattern,
    wire_current,
    wire_elements,
)
from pbc.electromagnetism.fdtd import SPEED_OF_LIGHT, Plane
from pbc.electromagnetism.fields import EPSILON_0
from pbc.electromagnetism.waveguides import (
    attenuation,
    cross_section_cutoffs,
    cutoff_frequency,
    group_velocity,
    guide_wavenumber,
    modes,
    phase_velocity,
)
from pbc.experiment import Experiment, main
from pbc.verification.estimates import fitted_order

# region: guide
A, B = 22.86e-3, 10.16e-3  # m, the inside of a WR-90 guide
REFINEMENTS = [2, 4, 8, 16]  # the grid has 9 r by 4 r cells, square
TE_COUNT, TM_COUNT = 5, 3  # modes compared, lowest first
# endregion: guide
# region: fdtd
ACROSS = 20  # cells across the width a
LENGTH = 700  # cells along the guide
ABSORBER = 150  # cells of graded conductivity at the far end
SOURCE_COLUMN = 10
COURANT = 0.66  # about; the step is a whole fraction of the period
RAMP, SETTLE, RECORD = 12, 2500, 4  # periods, steps, periods
ABOVE = [8e9, 9e9, 10e9, 11e9, 12e9]  # Hz, above the TE10 cut-off
BELOW = [3e9, 4e9, 5e9]  # Hz, below it
SHOWN = (10e9, 5e9)  # the frequencies of the field figure
SHOWN_CELLS = 220  # the length of guide it shows
# endregion: fdtd
# region: antenna
WAVELENGTH = 1.0  # m; everything scales with it
SEGMENTS = 400  # current elements per wire
SHORT = 0.1  # length of the short dipole, wavelengths
SPACING = 0.5  # of the two elements, wavelengths
# endregion: antenna


def below(value: float, bound: float) -> str:
    """A quantity at the level of round-off is not shown as a number: only
    that it is smaller than ``bound``."""
    if abs(value) >= bound:
        raise ValueError(f"{value!r} is not below {bound!r}")
    return f"below {bound:.0e}"


def cutoffs(experiment: Experiment) -> tuple[list, list]:
    """The lowest TE and TM cut-off frequencies from the eigenproblem on
    refined grids, against the closed form; record the tables and the order,
    and return the spacings and the largest relative errors."""
    exact = {
        kind: modes(A, B, count, kind)
        for kind, count in (("TE", TE_COUNT), ("TM", TM_COUNT))
    }
    spacings, errors, finest = [], [], {}
    for r in REFINEMENTS:
        worst = 0.0
        for kind, listed in exact.items():
            found = cross_section_cutoffs(A, B, 9 * r, 4 * r, kind, len(listed))
            reference = np.array([mode[2] for mode in listed])
            worst = max(worst, np.max(np.abs(found / reference - 1.0)))
            finest[kind] = found
        spacings.append(A / (9 * r))
        errors.append(worst)
    rows = [
        (f"{kind}{m}{n}", 1e-9 * f_c, 1e-9 * finest[kind][index])
        for kind, listed in exact.items()
        for index, (m, n, f_c) in enumerate(listed)
    ]
    rows.sort(key=lambda row: row[1])
    experiment.table(
        "cutoffs",
        rows,
        [
            ("mode", "", ""),
            ("closed form", "GHz", ".4f"),
            ("eigenproblem, finest grid", "GHz", ".4f"),
        ],
        "The lowest cut-off frequencies of the WR-90 guide, 22.86 mm by "
        "10.16 mm: the closed form against the eigenvalues of the five-point "
        "Laplacian on 144 by 64 cells.",
    )
    experiment.table(
        "cutoff-convergence",
        [
            (9 * r, 4 * r, 1e3 * h, e)
            for r, h, e in zip(REFINEMENTS, spacings, errors, strict=True)
        ],
        [
            ("cells across a", "", "d"),
            ("cells across b", "", "d"),
            ("dx", "mm", ".3f"),
            ("largest relative error", "", ".2e"),
        ],
        "The largest relative error of the eight cut-off frequencies as the "
        "grid of the cross-section is refined.",
    )
    experiment.number("cutoff-order", fitted_order(spacings, errors), ".2f")
    experiment.number("cutoff-error", errors[-1], ".0e")
    experiment.number("te10", 1e-9 * cutoff_frequency(1, 0, A, B), ".3f")
    return spacings, errors


def guide_run(f: float):
    """The guide of width A, ACROSS cells wide, driven at ``f`` by a soft
    source with the TE10 profile, run to a steady state: return the
    positions (m), the complex amplitude of E_z on the centre line, a
    snapshot of E_z, and the time step."""
    dx = A / ACROSS
    period = 1.0 / f
    per_period = int(np.ceil(SPEED_OF_LIGHT * period / (dx * COURANT)))
    courant = SPEED_OF_LIGHT * period / (dx * per_period)
    i = np.arange(LENGTH + 1)
    ramp = np.clip((i - (LENGTH - ABSORBER)) / ABSORBER, 0.0, 1.0) ** 3
    sigma_max = 2.4 * EPSILON_0 * SPEED_OF_LIGHT / dx  # S/m
    plane = Plane(
        LENGTH,
        ACROSS,
        dx,
        courant,
        conductivity=np.outer(sigma_max * ramp, np.ones(ACROSS + 1)),
    )
    profile = np.sin(np.pi * np.arange(ACROSS + 1) / ACROSS)
    source = np.zeros((LENGTH + 1, ACROSS + 1))
    total = RAMP * per_period + SETTLE + RECORD * per_period
    recorded = np.zeros(LENGTH + 1, dtype=complex)
    for n in range(total):
        t = (n + 1) * plane.dt
        envelope = np.sin(0.5 * np.pi * min(1.0, t / (RAMP * period))) ** 2
        source[SOURCE_COLUMN] = 0.05 * envelope * np.sin(2 * np.pi * f * t) * profile
        plane.step(source)
        if n >= total - RECORD * per_period:
            recorded += plane.ez[:, ACROSS // 2] * np.exp(-2j * np.pi * f * t)
    recorded *= 2.0 / (RECORD * per_period)
    return dx * i, recorded, plane.ez.copy(), plane.dt


def grid_wavenumber(f: float, dt: float) -> tuple[float, float]:
    """The wavenumber beta (above the cut-off) or the attenuation alpha
    (below it) of the TE10 field on the FDTD grid, from its dispersion
    relation (2 / (c dt))^2 sin^2(omega dt / 2) = (2 / dx)^2 (sin^2(beta dx / 2)
    + sin^2(pi / (2 N))), with N cells across; returns (beta, alpha), one of
    them nan."""
    dx = A / ACROSS
    left = (2.0 / (SPEED_OF_LIGHT * dt)) ** 2 * np.sin(np.pi * f * dt) ** 2
    rest = left - (2.0 / dx) ** 2 * np.sin(np.pi / (2 * ACROSS)) ** 2
    if rest >= 0:
        return 2.0 / dx * np.arcsin(np.sqrt(rest) * dx / 2.0), np.nan
    return np.nan, 2.0 / dx * np.arcsinh(np.sqrt(-rest) * dx / 2.0)


def transmission(experiment: Experiment):
    """The guide driven above and below the cut-off: the measured wavenumber
    and attenuation against the continuum and the grid; record the table
    and return the measurements and the snapshots of SHOWN."""
    f_c = cutoff_frequency(1, 0, A, B)
    rows, measured, snapshots = [], {}, {}
    for f in ABOVE + BELOW:
        x, phasor, snapshot, dt = guide_run(f)
        beta_grid, alpha_grid = grid_wavenumber(f, dt)
        if f > f_c:
            window = slice(60, 400)
            phase = np.unwrap(np.angle(phasor[window]))
            value = -np.polyfit(x[window], phase, 1)[0]
            continuum, grid = float(guide_wavenumber(f, f_c)), beta_grid
            inferred = np.sqrt(f**2 - (SPEED_OF_LIGHT * value / (2 * np.pi)) ** 2)
        else:
            window = slice(15, 60)
            value = -np.polyfit(x[window], np.log(np.abs(phasor[window])), 1)[0]
            continuum, grid = float(attenuation(f, f_c)), alpha_grid
            inferred = np.sqrt(f**2 + (SPEED_OF_LIGHT * value / (2 * np.pi)) ** 2)
        measured[f] = value
        if f in SHOWN:
            snapshots[f] = (x, snapshot)
        rows.append(
            (
                1e-9 * f,
                "beta" if f > f_c else "alpha",
                value,
                continuum,
                abs(value / grid - 1.0),
                1e-9 * inferred,
            )
        )
    experiment.table(
        "transmission",
        rows,
        [
            ("f", "GHz", ".1f"),
            ("quantity", "", ""),
            ("measured", "1/m", ".3f"),
            ("continuum", "1/m", ".3f"),
            ("measured against grid, relative", "", ".0e"),
            ("cut-off inferred", "GHz", ".4f"),
        ],
        "The FDTD guide, twenty cells across, driven at each frequency: the "
        "wavenumber beta (rad/m) fitted to the phase on the centre line above "
        "the cut-off, the attenuation alpha (Np/m) fitted to the logarithm of "
        "the amplitude below it, against the continuum and the grid's "
        "dispersion relation, and the cut-off frequency that the measured "
        "value implies with the continuum relation.",
    )
    experiment.number("transmission-to-grid", max(row[4] for row in rows), ".0e")
    experiment.number(
        "inferred-cutoff-gap",
        max(abs(row[5] / (1e-9 * f_c) - 1.0) for row in rows),
        ".0e",
    )
    above = [row for row in rows if row[1] == "beta"]
    experiment.number(
        "beta-to-continuum", max(abs(row[2] / row[3] - 1.0) for row in above), ".0e"
    )
    f = SHOWN[0]
    experiment.table(
        "velocities",
        [
            (
                1e-9 * f,
                1e3 * 2 * np.pi / guide_wavenumber(f, f_c),
                1e3 * SPEED_OF_LIGHT / f,
                phase_velocity(f, f_c) / SPEED_OF_LIGHT,
                group_velocity(f, f_c) / SPEED_OF_LIGHT,
            )
        ],
        [
            ("f", "GHz", ".1f"),
            ("guide wavelength", "mm", ".2f"),
            ("free-space wavelength", "mm", ".2f"),
            ("phase velocity / c", "", ".4f"),
            ("group velocity / c", "", ".4f"),
        ],
        "The TE10 mode of the WR-90 guide at 10 GHz: its wavelength along the "
        "guide, longer than in free space, and its phase and group velocities.",
    )
    return measured, snapshots


def patterns(experiment: Experiment):
    """The E-plane patterns of a half-wave and a short wire by superposition,
    against the closed forms; directivity and radiation resistance; record
    the table and return the patterns for the figure."""
    theta = np.linspace(0.0, np.pi, 721)
    rows, curves = [], {}
    for name, length, closed in (
        ("half-wave dipole", 0.5 * WAVELENGTH, half_wave_dipole_pattern),
        ("short dipole", SHORT * WAVELENGTH, short_dipole_pattern),
    ):
        z, dz = wire_elements(length, SEGMENTS)
        positions = np.column_stack([np.zeros_like(z), np.zeros_like(z), z])
        currents = wire_current(z, length, WAVELENGTH) * dz
        field = far_field(theta, 0.0, positions, currents, WAVELENGTH)
        pattern = np.abs(field) / np.abs(field).max()
        reference = closed(theta)
        curves[name] = (theta, pattern, reference)
        rows.append(
            (
                name,
                length / WAVELENGTH,
                np.max(np.abs(pattern - reference)),
                directivity(pattern**2, theta),
                directivity(reference**2, theta),
                radiation_resistance(field, theta, 1.0),
            )
        )
    experiment.table(
        "patterns",
        rows,
        [
            ("antenna", "", ""),
            ("length", "wavelengths", ".2f"),
            ("largest gap to the closed-form pattern", "", ".1e"),
            ("directivity, superposition", "", ".4f"),
            ("directivity, closed form", "", ".4f"),
            ("radiation resistance", "ohm", ".2f"),
        ],
        "Wires with the standing-wave current, each built of four hundred "
        "short elements: the field pattern in a plane through the wire against "
        "the closed form of the dipole, the directivity of each, and the "
        "radiation resistance seen at the feed.",
    )
    experiment.number("half-wave-gap", rows[0][2], ".0e")
    experiment.number("short-gap", rows[1][2], ".1e")
    experiment.number("half-wave-resistance", rows[0][5], ".2f")
    experiment.number("closed-resistance", half_wave_radiation_resistance(), ".2f")
    experiment.number("short-resistance", rows[1][5], ".3f")
    # The short dipole with a triangular current: (pi / 6) eta (L / lambda)^2.
    experiment.number(
        "short-estimate", np.pi / 6 * IMPEDANCE_OF_FREE_SPACE * SHORT**2, ".3f"
    )
    return curves


def two_elements(experiment: Experiment):
    """Two half-wave dipoles side by side, SPACING apart, in phase and in
    antiphase: the pattern in the plane across them (theta = pi/2), by direct
    superposition of all the elements of both wires and as the element
    pattern times the array factor; record the gap and return the curves."""
    phi = np.linspace(0.0, 2 * np.pi, 721)
    theta = np.full_like(phi, 0.5 * np.pi)
    length = 0.5 * WAVELENGTH
    z, dz = wire_elements(length, SEGMENTS)
    currents = wire_current(z, length, WAVELENGTH) * dz
    single = np.column_stack([np.zeros_like(z), np.zeros_like(z), z])
    element = far_field(theta, phi, single, currents, WAVELENGTH)
    centres = np.array([[-0.5, 0.0, 0.0], [0.5, 0.0, 0.0]]) * SPACING * WAVELENGTH
    curves, gaps = {}, []
    for name, weights in (("in phase", [1.0, 1.0]), ("in antiphase", [1.0, -1.0])):
        positions = np.concatenate([single + centre for centre in centres])
        both = np.concatenate([w * currents for w in weights])
        direct = far_field(theta, phi, positions, both, WAVELENGTH)
        product = element * array_factor(theta, phi, centres, weights, WAVELENGTH)
        gaps.append(np.max(np.abs(direct - product)) / np.max(np.abs(direct)))
        curves[name] = (phi, np.abs(direct) / np.max(np.abs(direct)))
    experiment.number("multiplication-gap", below(max(gaps), 1e-12))
    return curves


def draw_cutoff_convergence(spacings, errors) -> Figure:
    """Log-log largest relative error of the cut-off frequencies against the
    grid spacing, with a reference slope two."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    h = 1e3 * np.array(spacings)
    ax.loglog(h, errors, color=FIGURE_COLOURS[0], marker="o", label="eigenproblem")
    ax.loglog(
        h,
        0.5 * errors[0] * (h / h[0]) ** 2,
        color=FIGURE_COLOURS[2],
        linestyle=":",
        label="reference, slope two",
    )
    ax.set_xticks(h, labels=[f"{value:.3g}" for value in h])
    ax.minorticks_off()
    ax.set_xlabel("dx (mm)")
    ax.set_ylabel("largest relative error of f_c")
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    return fig


def draw_guide_field(snapshots) -> Figure:
    """E_z in the first SHOWN_CELLS cells of the guide above and below the
    cut-off, false colour centred on zero."""
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 3.6), sharex=True)
    shown = SHOWN_CELLS
    for ax, f in zip(axes, SHOWN, strict=True):
        x, field = snapshots[f]
        part = field[:shown].T
        scale = float(np.max(np.abs(part)))
        image = ax.imshow(
            part / scale,
            origin="lower",
            extent=(0.0, 100 * x[shown], 0.0, 100 * A),
            cmap="PuOr",
            vmin=-1.0,
            vmax=1.0,
            aspect="auto",
        )
        side = "above" if f > cutoff_frequency(1, 0, A, B) else "below"
        ax.set_title(f"{f / 1e9:g} GHz, {side} the cut-off", fontsize="medium")
        ax.set_ylabel("across (cm)")
    axes[-1].set_xlabel("distance along the guide from its closed end (cm)")
    bar = fig.colorbar(image, ax=axes)
    bar.set_label("$E_z$ / its largest value\n(false colour, zero at the centre)")
    return fig


def draw_dispersion(measured: dict) -> Figure:
    """beta above and alpha below the cut-off against frequency: the
    continuum curves and the FDTD measurements."""
    f_c = cutoff_frequency(1, 0, A, B)
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    above = np.linspace(f_c, 1.05 * ABOVE[-1], 300)
    below_ = np.linspace(0.9 * BELOW[0], f_c, 300)
    ax.plot(
        1e-9 * above,
        guide_wavenumber(above, f_c),
        color=FIGURE_COLOURS[0],
        label=r"$\beta$, continuum",
    )
    ax.plot(
        1e-9 * below_,
        attenuation(below_, f_c),
        color=FIGURE_COLOURS[1],
        linestyle="--",
        label=r"$\alpha$, continuum",
    )
    ax.plot(
        [1e-9 * f for f in ABOVE],
        [measured[f] for f in ABOVE],
        color=FIGURE_COLOURS[0],
        marker="o",
        linestyle="none",
        label=r"$\beta$, FDTD",
    )
    ax.plot(
        [1e-9 * f for f in BELOW],
        [measured[f] for f in BELOW],
        color=FIGURE_COLOURS[1],
        marker="s",
        linestyle="none",
        label=r"$\alpha$, FDTD",
    )
    ax.axvline(
        1e-9 * f_c, color=FIGURE_COLOURS[2], linestyle=":", label="cut-off, TE10"
    )
    ax.set_xlabel("frequency (GHz)")
    ax.set_ylabel(r"$\beta$ (rad/m) or $\alpha$ (Np/m)")
    ax.legend(frameon=False, loc="upper left", fontsize="small")
    fig.tight_layout()
    return fig


def draw_patterns(curves: dict, arrays: dict) -> Figure:
    """Polar patterns: the two wires by superposition against the closed
    forms, and the two-element arrays across the wires."""
    fig, (left, right) = plt.subplots(
        1, 2, figsize=(7.2, 3.8), subplot_kw={"projection": "polar"}
    )
    for (name, (theta, pattern, reference)), colour, line, marker in zip(
        curves.items(),
        (FIGURE_COLOURS[0], FIGURE_COLOURS[1]),
        ("-", "--"),
        ("o", "s"),
        strict=True,
    ):
        for side in (1, -1):  # the pattern is the same on both sides of the wire
            left.plot(
                side * theta,
                reference,
                color=colour,
                linestyle=line,
                label=f"{name}, closed form" if side == 1 else None,
            )
            left.plot(
                side * theta[::30],
                pattern[::30],
                color=colour,
                marker=marker,
                linestyle="none",
                markersize=3,
                label=f"{name}, superposition" if side == 1 else None,
            )
    left.set_theta_zero_location("N")
    left.set_theta_direction(-1)
    left.set_title(
        "one wire, plane through it\n(angle from the wire)", fontsize="small"
    )
    left.set_yticklabels([])
    left.legend(
        frameon=False,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.08),
        fontsize="x-small",
    )
    for (name, (phi, pattern)), colour, line in zip(
        arrays.items(), (FIGURE_COLOURS[4], FIGURE_COLOURS[3]), ("-", "-."), strict=True
    ):
        right.plot(phi, pattern, color=colour, linestyle=line, label=name)
    right.set_title(
        "two wires, plane across them\n(angle from the line joining them)",
        fontsize="small",
    )
    right.set_yticklabels([])
    right.legend(
        frameon=False,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.08),
        fontsize="x-small",
    )
    fig.tight_layout()
    return fig


def cavity(experiment: Experiment) -> None:
    """Exercise 1: a WR-90 section closed at both ends, 30 mm long, as a
    cavity: its lowest resonances f = sqrt(f_c^2 + (p c / (2 d))^2) for the
    TE10p modes; record the table."""
    d = 30e-3
    f_c = cutoff_frequency(1, 0, A, B)
    rows = [
        (f"TE10{p}", 1e-9 * np.sqrt(f_c**2 + (p * SPEED_OF_LIGHT / (2 * d)) ** 2))
        for p in (1, 2, 3)
    ]
    experiment.table(
        "cavity",
        rows,
        [("mode", "", ""), ("resonance", "GHz", ".3f")],
        "The lowest TE10p resonances of a WR-90 section 30 mm long closed by "
        "conducting plates at both ends.",
    )


def evanescent_length(experiment: Experiment) -> None:
    """Exercise 2: how far a 5 GHz field reaches into the WR-90 guide: the
    distance over which it falls by 20 dB and by 60 dB; record the table."""
    f_c = cutoff_frequency(1, 0, A, B)
    alpha = float(attenuation(5e9, f_c))
    rows = [(db, 1e3 * db / (20 * np.log10(np.e) * alpha)) for db in (20, 60)]
    experiment.table(
        "evanescent",
        rows,
        [("attenuation", "dB", "d"), ("distance", "mm", ".1f")],
        "The distance over which a 5 GHz field in the WR-90 guide, below the "
        "cut-off, falls by 20 and by 60 decibels.",
    )


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    spacings, errors = cutoffs(experiment)
    experiment.figure(
        "fig-cutoff-convergence", partial(draw_cutoff_convergence, spacings, errors)
    )
    measured, snapshots = transmission(experiment)
    experiment.figure("fig-guide-field", partial(draw_guide_field, snapshots))
    experiment.figure("fig-guide-dispersion", partial(draw_dispersion, measured))
    curves = patterns(experiment)
    arrays = two_elements(experiment)
    experiment.figure("fig-dipole-patterns", partial(draw_patterns, curves, arrays))
    cavity(experiment)
    evanescent_length(experiment)
    return experiment


if __name__ == "__main__":
    main(run)
