"""The experiment of the lesson "Diffraction and imaging".

The far field of a single slit, a double slit, and a grating as a sum of
wavelets, its zeros and maxima against the closed forms, the fringe spacing
on a screen against lambda L / d, the Airy pattern of a round aperture and
the Rayleigh criterion, the resolving power of a grating on a doublet, and
the distance at which the Fraunhofer pattern holds (``pbc.waves.diffraction``).
Run it as a program to write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.waves.experiments.diffraction_and_imaging out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.verification.estimates import fitted_order
from pbc.waves.diffraction import (
    AIRY_FIRST_ZERO,
    circular_field,
    double_slit_zero,
    far_field,
    fresnel_number,
    grating_maximum,
    huygens_field,
    resolving_power,
    single_slit_zero,
    slits,
    two_points,
)
from pbc.waves.refraction import bisect_root, golden_minimum

# region: slits
WAVELENGTH = 633e-9  # m, a helium-neon laser
WIDTH = 50e-6  # m, the width of a slit
SEPARATION = 250e-6  # m, between the centres of the two slits
GRATING = dict(count=10, width=10e-6, period=40e-6)  # m
SCREEN = 1.0  # m, the distance of a flat screen
PIECES = 400  # pieces per slit
ZERO_TOLERANCE = 1e-9  # relative, a chosen tolerance on a zero of the slits
# endregion: slits
# region: imaging
DIAMETER = 0.10  # m, the aperture of a small telescope
GREEN = 550e-9  # m
separations = [0.8, 1.0, AIRY_FIRST_ZERO, 1.5]  # in units of lambda / D
# endregion: imaging
# region: doublet
SODIUM = (588.995e-9, 589.592e-9)  # m, the two yellow lines of sodium
DOUBLET_PERIOD = 2e-6  # m, a grating of 500 lines per mm
counts = [500, 987, 2000]  # slits lit by the beam
# endregion: doublet


def intensity_at(points, widths, wavelength):
    """The far-field intensity as a function of one sin(theta)."""
    return lambda s: float(abs(far_field(s, points, widths, wavelength)[0]) ** 2)


def located(f, guess: float, half_width: float) -> float:
    """The smallest value of ``f`` within ``half_width`` of ``guess``."""
    return golden_minimum(f, guess - half_width, guess + half_width)


def slits_run(experiment: Experiment):
    """The zeros of a single and a double slit and the maxima of a grating,
    found by searching the computed intensity near the closed form; record
    the table and return the largest relative difference."""
    rows, worst = [], 0.0
    one = intensity_at(*slits(1, WIDTH, WIDTH, PIECES), WAVELENGTH)
    for m in (1, 2, 3):
        closed = single_slit_zero(m, WIDTH, WAVELENGTH)
        found = located(one, closed, 0.3 * WAVELENGTH / WIDTH)
        worst = max(worst, abs(found / closed - 1))
        rows.append(("single slit, zero", m, found * 1e3, closed * 1e3))
    two = intensity_at(*slits(2, WIDTH, SEPARATION, PIECES), WAVELENGTH)
    for m in (0, 1, 2):
        closed = double_slit_zero(m, SEPARATION, WAVELENGTH)
        found = located(two, closed, 0.2 * WAVELENGTH / SEPARATION)
        worst = max(worst, abs(found / closed - 1))
        rows.append(("double slit, zero", m, found * 1e3, closed * 1e3))
    grating = slits(GRATING["count"], GRATING["width"], GRATING["period"], 40)
    many = intensity_at(*grating, WAVELENGTH)
    peak_width = WAVELENGTH / (GRATING["count"] * GRATING["period"])
    shift = 0.0
    for m in (1, 2, 3):
        closed = grating_maximum(m, GRATING["period"], WAVELENGTH)
        found = located(lambda s: -many(s), closed, 0.3 * peak_width)
        rows.append(("grating, maximum", m, found * 1e3, closed * 1e3))
        # the falling envelope of one slit pulls a maximum towards the
        # centre by a small fraction of its width, lambda / (N d)
        shift = max(shift, abs(found - closed) / peak_width)
    assert shift < 0.05, "a maximum of the grating is off its order"
    assert worst < ZERO_TOLERANCE, "a zero is not where the closed form puts it"
    experiment.table(
        "slits-run",
        rows,
        [
            ("aperture", "", ""),
            ("order m", "", "d"),
            ("sin(theta) found, times 1000", "", ".6f"),
            ("closed form, times 1000", "", ".6f"),
        ],
        "The zeros of one and of two slits and the principal maxima of a grating, "
        "found by searching the intensity computed as a sum of wavelets, against "
        "m lambda / a, (m + 1/2) lambda / d, and m lambda / d, as sin(theta) "
        "times a thousand, to six decimals.",
    )
    missing = many(grating_maximum(4, GRATING["period"], WAVELENGTH)) / many(0.0)
    return worst, missing, shift


def spacing_run(experiment: Experiment):
    """The zeros of the double slit on a flat screen, their mean spacing,
    and lambda L / d; record the table and return the two."""
    two = intensity_at(*slits(2, WIDTH, SEPARATION, PIECES), WAVELENGTH)
    orders = np.arange(-5, 5)
    positions = []
    for m in orders:
        closed = double_slit_zero(int(m), SEPARATION, WAVELENGTH)
        s = located(two, closed, 0.2 * WAVELENGTH / SEPARATION)
        positions.append(SCREEN * np.tan(np.arcsin(s)))
    positions = np.array(positions)
    spacing = float(np.mean(np.diff(positions)))
    paraxial = WAVELENGTH * SCREEN / SEPARATION
    assert abs(spacing / paraxial - 1) < 1e-3
    experiment.table(
        "spacing-run",
        [(int(m), y * 1e3) for m, y in zip(orders, positions, strict=True)],
        [("zero m", "", "d"), ("position on the screen", "mm", ".4f")],
        "The zeros of the double slit on a flat screen at the stated distance, "
        "from the computed intensity, to a ten-thousandth of a millimetre.",
    )
    return spacing, paraxial


def draw_slits() -> Figure:
    """The far-field intensity of one slit, two slits, and a grating, with
    the closed-form zeros and maxima."""
    s = np.linspace(-0.07, 0.07, 4001)
    setups = [
        ("one slit", slits(1, WIDTH, WIDTH, PIECES)),
        ("two slits", slits(2, WIDTH, SEPARATION, PIECES)),
        (
            "grating of ten slits",
            slits(GRATING["count"], GRATING["width"], GRATING["period"], 40),
        ),
    ]
    fig, axes = plt.subplots(3, 1, figsize=(6.4, 5.6), sharex=True)
    for ax, (name, (points, widths)), colour in zip(
        axes,
        setups,
        (FIGURE_COLOURS[0], FIGURE_COLOURS[1], FIGURE_COLOURS[4]),
        strict=True,
    ):
        i = np.abs(far_field(s, points, widths, WAVELENGTH)) ** 2
        ax.plot(s, i / i.max(), color=colour, linewidth=0.9)
        ax.set_ylabel("intensity\n(of the peak,\ndimensionless)")
        ax.set_title(name, fontsize="small", loc="left")
    for m in (1, 2, 3, 4, 5):
        for sign in (-1, 1):
            axes[0].axvline(
                sign * single_slit_zero(m, WIDTH, WAVELENGTH),
                color=FIGURE_COLOURS[2],
                linestyle=":",
                linewidth=0.8,
            )
    for m in range(5):  # the zeros inside the central lobe of one slit
        for sign in (-1, 1):
            axes[1].axvline(
                sign * double_slit_zero(m, SEPARATION, WAVELENGTH),
                color=FIGURE_COLOURS[2],
                linestyle=":",
                linewidth=0.5,
            )
    axes[1].set_xlim(-0.07, 0.07)
    for m in range(-4, 5):
        axes[2].axvline(
            grating_maximum(m, GRATING["period"], WAVELENGTH),
            color=FIGURE_COLOURS[2],
            linestyle=":",
            linewidth=0.8,
        )
    axes[2].set_xlabel("sin(theta), the direction on the screen")
    fig.tight_layout()
    return fig


def airy_run(experiment: Experiment):
    """The first zero of the Airy pattern by bisection against its closed
    form, and the dip between two points at four separations; record the
    table and return the values for the page."""
    unit = GREEN / DIAMETER
    zero = bisect_root(
        lambda s: float(circular_field(s, DIAMETER, GREEN)[0]), 1.0 * unit, 1.4 * unit
    )
    assert abs(zero / unit - AIRY_FIRST_ZERO) < 1e-6
    rows, dips = [], {}
    for sep in separations:
        s = np.linspace(-1.0, 1.0, 801) * sep * unit
        image = two_points(s, sep * unit, DIAMETER, GREEN)
        dip = float(image[400] / image.max())
        dips[sep] = dip
        rows.append((sep, dip, "yes" if dip < 1 else "no"))
    experiment.table(
        "airy-run",
        rows,
        [
            ("separation", "lambda / D", ".3f"),
            ("centre over the brightest point of the image", "", ".3f"),
            ("a dip between the two", "", ""),
        ],
        "The image of two equally bright points that do not interfere, seen "
        "through a round aperture, at four angular separations: the intensity "
        "midway between them over the largest intensity of the image.",
    )
    return zero / unit, dips


def draw_airy_rayleigh() -> Figure:
    """The Airy pattern, and the image of two points at three separations."""
    unit = GREEN / DIAMETER
    s = np.linspace(-3.0, 3.0, 1201)
    fig, (left, right) = plt.subplots(1, 2, figsize=(7.2, 3.2))
    left.plot(
        s, circular_field(s * unit, DIAMETER, GREEN) ** 2, color=FIGURE_COLOURS[0]
    )
    left.axvline(AIRY_FIRST_ZERO, color=FIGURE_COLOURS[2], linestyle=":")
    left.axvline(-AIRY_FIRST_ZERO, color=FIGURE_COLOURS[2], linestyle=":")
    left.set_xlabel("sin(theta) in units of lambda / D")
    left.set_ylabel("intensity\n(of the centre, dimensionless)")
    left.set_title("one point: the Airy pattern", fontsize="small")
    styles = [
        ("-", FIGURE_COLOURS[0]),
        ("--", FIGURE_COLOURS[1]),
        ("-.", FIGURE_COLOURS[4]),
    ]
    for sep, (line, colour) in zip(separations[1:], styles, strict=True):
        image = two_points(s * unit, sep * unit, DIAMETER, GREEN)
        right.plot(
            s,
            image / image.max(),
            color=colour,
            linestyle=line,
            label=f"{sep:.2f} lambda / D",
        )
    right.set_xlim(-2.5, 2.5)
    right.set_xlabel("sin(theta) in units of lambda / D")
    right.set_ylabel("intensity\n(of the brightest, dimensionless)")
    right.set_title("two points", fontsize="small")
    right.legend(fontsize=7, loc="lower center")
    fig.tight_layout()
    return fig


def doublet_image(count: int):
    """The first-order image of the sodium doublet through a grating of
    ``count`` slits: the directions and the summed intensity."""
    centre = grating_maximum(1, DOUBLET_PERIOD, float(np.mean(SODIUM)))
    s = centre + np.linspace(-1.2e-3, 1.2e-3, 1201)
    points, widths = slits(count, DOUBLET_PERIOD / 2, DOUBLET_PERIOD, 4)
    total = sum(np.abs(far_field(s, points, widths, lam)) ** 2 for lam in SODIUM)
    return s, total / total.max()


def dip_between(s, image) -> float:
    """The smallest intensity between the two expected lines, over the
    smaller of the two peaks: one when there is no dip."""
    lines = [grating_maximum(1, DOUBLET_PERIOD, lam) for lam in SODIUM]
    inside = (s >= lines[0]) & (s <= lines[1])
    peaks = [image[np.argmin(np.abs(s - line))] for line in lines]
    return float(np.min(image[inside]) / min(peaks))


def doublet_run(experiment: Experiment):
    """The doublet through gratings of three sizes; record the table and
    return the needed number of slits and the dips."""
    needed = float(np.mean(SODIUM) / (SODIUM[1] - SODIUM[0]))
    rows, dips = [], {}
    for count in counts:
        s, image = doublet_image(count)
        dip = dip_between(s, image)
        dips[count] = dip
        rows.append(
            (count, resolving_power(1, count), dip, "yes" if dip < 0.99 else "no")
        )
    assert dips[counts[0]] > 0.99 and dips[counts[-1]] < 0.5
    experiment.table(
        "doublet-run",
        rows,
        [
            ("slits lit", "", "d"),
            ("resolving power m N", "", ".0f"),
            ("lowest between the lines over the smaller line", "", ".3f"),
            ("a dip between the two", "", ""),
        ],
        "The sodium doublet in the first order of a grating of 500 lines per mm, "
        "for three numbers of lit slits: the resolving power and the lowest "
        "intensity between the two lines over the smaller peak, to three "
        "decimals.",
    )
    return needed, dips


def draw_doublet() -> Figure:
    """The first-order image of the sodium doublet for three gratings."""
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    styles = [
        (":", FIGURE_COLOURS[2]),
        ("--", FIGURE_COLOURS[1]),
        ("-", FIGURE_COLOURS[0]),
    ]
    for count, (line, colour) in zip(counts, styles, strict=True):
        s, image = doublet_image(count)
        ax.plot(s * 1e3, image, color=colour, linestyle=line, label=f"{count} slits")
    for lam in SODIUM:
        ax.axvline(
            grating_maximum(1, DOUBLET_PERIOD, lam) * 1e3,
            color=FIGURE_COLOURS[3],
            linewidth=0.6,
        )
    ax.set_xlabel("sin(theta), times 1000")
    ax.set_ylabel("intensity\n(of the brightest, dimensionless)")
    ax.legend(fontsize=7, loc="upper left")
    return fig


def fraunhofer_run(experiment: Experiment):
    """One slit at seven distances: the largest difference between the
    pattern at that distance and the far-field pattern, against the Fresnel
    number; record the table and return the numbers and the slope."""
    width = 100e-6
    points, widths = slits(1, width, width, 1000)
    s = np.linspace(-3.0, 3.0, 301) * WAVELENGTH / width
    far = np.abs(far_field(s, points, widths, WAVELENGTH)) ** 2
    far /= far[150]
    numbers = np.array([0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0])
    rows, departures = [], []
    for nf in numbers:
        distance = width**2 / (WAVELENGTH * nf)
        near = (
            np.abs(huygens_field(np.arcsin(s), points, widths, WAVELENGTH, distance))
            ** 2
        )
        near /= near[150]
        departures.append(float(np.max(np.abs(near - far))))
        rows.append(
            (
                fresnel_number(width, WAVELENGTH, distance),
                distance * 100,
                departures[-1],
            )
        )
    departures = np.array(departures)
    slope = fitted_order(numbers[3::-1], departures[3::-1])  # largest first
    assert 1.9 < slope < 2.1, (
        "the departure does not fall as the square of the Fresnel number"
    )
    experiment.table(
        "fraunhofer-run",
        rows,
        [
            ("Fresnel number a^2 / (lambda L)", "", ".2f"),
            ("distance L", "cm", ".2f"),
            ("largest departure from the far-field pattern", "", ".1e"),
        ],
        "A slit of a tenth of a millimetre: the largest difference between the "
        "intensity on an arc at the distance L and the far-field intensity, both "
        "normalised on the axis, over three zeros on each side.",
    )
    return numbers, departures, slope


def draw_fraunhofer_limit(numbers, departures) -> Figure:
    """The departure from the far-field pattern against the Fresnel number,
    log-log, with a slope-two reference."""
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ax.loglog(
        numbers, departures, "o-", color=FIGURE_COLOURS[0], label="sum of wavelets at L"
    )
    ax.loglog(
        numbers,
        3 * departures[0] * (numbers / numbers[0]) ** 2,
        color=FIGURE_COLOURS[2],
        linestyle=":",
        label="slope 2 (reference, drawn above)",
    )
    ax.set_xlabel("Fresnel number a^2 / (lambda L), dimensionless")
    ax.set_ylabel("largest departure of the intensity\n(of the centre, dimensionless)")
    ax.legend(fontsize=8, loc="upper left")
    return fig


def telescope():
    """Exercise 1: the smallest angle a telescope of 10 cm separates in green
    light, in seconds of arc, and the distance of two car lights 1.5 m apart
    at which they merge."""
    angle = AIRY_FIRST_ZERO * GREEN / DIAMETER
    return np.degrees(angle) * 3600, 1.5 / angle / 1000


def eye():
    """Exercise 2: the same for a pupil of 3 mm."""
    angle = AIRY_FIRST_ZERO * GREEN / 3e-3
    return np.degrees(angle) * 60, 1.5 / angle / 1000


def hair():
    """Exercise 3: the width of a hair whose dark fringes on a screen 2 m
    away are 2.5 cm apart in red light."""
    return WAVELENGTH * 2.0 / 0.025 * 1e6


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    worst, missing, shift = slits_run(experiment)
    experiment.number("grating-shift", shift * 100, ".1f")
    experiment.figure("fig-slits", draw_slits)
    experiment.number("zero-tolerance", ZERO_TOLERANCE, ".0e")
    experiment.number(
        "zero-gap", "below 1e-11" if worst < 1e-11 else f"{worst:.0e}", ""
    )
    experiment.number(
        "missing-order", "below 1e-6" if missing < 1e-6 else f"{missing:.1e}", ""
    )

    spacing, paraxial = spacing_run(experiment)
    experiment.number("spacing", spacing * 1e3, ".4f")
    experiment.number("paraxial", paraxial * 1e3, ".4f")
    experiment.number("spacing-gap", abs(spacing / paraxial - 1) * 100, ".3f")

    zero, dips = airy_run(experiment)
    experiment.figure("fig-airy-rayleigh", draw_airy_rayleigh)
    experiment.number("airy-zero", zero, ".6f")
    experiment.number("airy-closed", AIRY_FIRST_ZERO, ".6f")
    experiment.number("rayleigh-dip", dips[AIRY_FIRST_ZERO], ".3f")

    needed, doublet_dips = doublet_run(experiment)
    experiment.figure("fig-doublet", draw_doublet)
    experiment.number("needed", needed, ".0f")
    experiment.number("dip-limit", doublet_dips[counts[1]], ".2f")

    numbers, departures, slope = fraunhofer_run(experiment)
    experiment.figure(
        "fig-fraunhofer-limit", partial(draw_fraunhofer_limit, numbers, departures)
    )
    experiment.number("fresnel-slope", slope, ".2f")
    experiment.number("departure-small", departures[3], ".0e")
    experiment.number("departure-one", departures[-1] * 100, ".1f")

    arcsec, km = telescope()
    experiment.number("telescope-arcsec", arcsec, ".2f")
    experiment.number("telescope-km", km, ".0f")
    arcmin, eye_km = eye()
    experiment.number("eye-arcmin", arcmin, ".2f")
    experiment.number("eye-km", eye_km, ".1f")
    experiment.number("hair-um", hair(), ".0f")
    return experiment


if __name__ == "__main__":
    main(run)
