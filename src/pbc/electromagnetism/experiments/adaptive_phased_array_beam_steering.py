"""The experiment of the lesson "Applied capstone: adaptive phased-array beam
steering".

A hypothetical linear array of sixteen elements at 10 GHz
(``pbc.electromagnetism.arrays``, on the array factor of
``pbc.electromagnetism.antennas``): the model checked against the closed-form
array factor, the steering angle, the nulls, and its symmetries; the
grating-lobe onset against lambda / (1 + sin psi0); the Dolph-Chebyshev
taper against its design level; a null toward an interferer and its cost
against the closed form; the degradation by quantised phase shifters and by
random channel errors, measured by Monte Carlo against the exact expected
pattern; the squint of phase steering across the band; the element pattern;
then a receiver passing on a road with the interferer fixed, the weights
recomputed at every step, and the number of phase-shifter bits chosen from
the measured null depth. Run it as a program to write the figures and
numbers of the page:

    uv run --locked --no-dev python -m \\
        pbc.electromagnetism.experiments.adaptive_phased_array_beam_steering out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from scipy.optimize import brentq, minimize_scalar

from pbc.authoring import FIGURE_COLOURS
from pbc.electromagnetism.arrays import (
    chebyshev_taper,
    dipole_element,
    expected_power,
    factor,
    grating_onset,
    line_positions,
    mean_phase_factor,
    null_direction,
    null_weights,
    peak_direction,
    quantise,
    realised_gain,
    steering_vector,
    steering_weights,
    uniform_factor,
)
from pbc.electromagnetism.fdtd import SPEED_OF_LIGHT
from pbc.experiment import Experiment, main

# region: requirements
FREQUENCY = 10e9  # Hz, the carrier
BAND = (9.5e9, 10.5e9)  # Hz, the band the array must work over
COUNT = 16  # elements
SPACING = 15e-3  # m, half a wavelength at the carrier
SCAN = np.radians(50.0)  # the receiver may be up to this far from broadside
SIDELOBES = 30.0  # dB below the main lobe, the taper's design level
NULL_DEPTH = 30.0  # dB below the main lobe toward the interferer
FEASIBLE_LOSS = 3.0  # dB of gain a null may cost the receiver
# endregion: requirements
# region: errors
BITS = [2, 3, 4, 5, 6, 7]  # phase-shifter bits compared
PHASE_ERROR = np.radians(2.0)  # rms phase error of a channel
AMPLITUDE_ERROR = 0.02  # rms relative amplitude error of a channel
DRAWS = 20000  # realised arrays per Monte Carlo estimate
CONFIDENCE = 0.95  # the share of realised arrays that must meet the null
LOBE_BITS, LOBE_DRAWS = 3, 40  # the quantisation-lobe comparison
SEED = 301
# endregion: errors
# region: pass
ROAD = 200.0  # m, the road's distance from the array
SPEED = 25.0  # m/s, the receiver's speed along it
INTERFERER = np.radians(20.0)  # the fixed interferer
STEPS = 121  # weight updates over the pass
# endregion: pass

WAVELENGTH = SPEED_OF_LIGHT / FREQUENCY
POSITIONS = line_positions(COUNT, SPACING)
CHECK_STEER = np.radians(30.0)  # the beam of the model checks
NULL_STEER = np.radians(-10.0)  # the receiver of the null and error studies
ANGLES = np.radians(np.linspace(-90.0, 90.0, 3601))


def below(value: float, bound: float) -> str:
    """A quantity at the level of round-off is not shown as a number: only
    that it is smaller than ``bound``."""
    if abs(value) >= bound:
        raise ValueError(f"{value!r} is not below {bound!r}")
    return f"below {bound:.0e}"


def db(power_ratio) -> np.ndarray:
    """A power ratio in decibels."""
    return 10.0 * np.log10(power_ratio)


def pattern_db(weights, wavelength: float = WAVELENGTH) -> np.ndarray:
    """The power pattern on ANGLES in dB below its largest value."""
    power = np.abs(factor(ANGLES, POSITIONS, weights, wavelength)) ** 2
    return db(np.maximum(power / power.max(), 1e-12))


def design_weights(steer: float, null: float | None = None) -> np.ndarray:
    """The ideal weights of the design: the Chebyshev taper, steered to
    ``steer``, with a null toward ``null`` if one is given."""
    weights = steering_weights(
        steer, POSITIONS, WAVELENGTH, chebyshev_taper(COUNT, SIDELOBES)
    )
    if null is None:
        return weights
    return null_weights(weights, null, POSITIONS, WAVELENGTH)


def main_lobe(weights, steer: float, samples: int = 20001):
    """The first minima on each side of the main lobe of the beam steered
    near ``steer``, as values of u = sin(psi), on a fine grid of u."""
    u = np.linspace(-1.0, 1.0, samples)
    size = np.abs(factor(np.arcsin(u), POSITIONS, weights, WAVELENGTH))
    top = int(np.argmin(np.abs(u - np.sin(steer))))
    while 0 < top < samples - 1 and size[top + 1] > size[top]:
        top += 1
    while 0 < top < samples - 1 and size[top - 1] > size[top]:
        top -= 1
    left = top
    while left > 0 and size[left - 1] < size[left]:
        left -= 1
    right = top
    while right < samples - 1 and size[right + 1] < size[right]:
        right += 1
    return u, size, left, right


def largest_sidelobe(weights, steer: float) -> float:
    """The largest lobe outside the main lobe, dB below the peak: the local
    maxima of a fine grid in u, each refined by a bounded search."""
    u, size, left, right = main_lobe(weights, steer)
    peak = abs(
        factor(
            peak_direction(POSITIONS, weights, WAVELENGTH, steer, 0.05),
            POSITIONS,
            weights,
            WAVELENGTH,
        )
    )
    step = u[1] - u[0]
    best = 0.0
    for i in range(1, u.size - 1):
        if left <= i <= right or not (
            size[i] >= size[i - 1] and size[i] >= size[i + 1]
        ):
            continue
        found = minimize_scalar(
            lambda v: -abs(factor(np.arcsin(v), POSITIONS, weights, WAVELENGTH)),
            bounds=(max(u[i] - step, -1.0), min(u[i] + step, 1.0)),
            method="bounded",
            options={"xatol": 1e-14},
        )
        best = max(best, -found.fun)
    return float(db((best / peak) ** 2))


def half_power_width(weights, steer: float) -> float:
    """The width (rad) of the main lobe between its half-power directions."""
    u, _, left, right = main_lobe(weights, steer)
    top = peak_direction(POSITIONS, weights, WAVELENGTH, steer, 0.05)
    level = abs(factor(top, POSITIONS, weights, WAVELENGTH)) / np.sqrt(2.0)

    def gap(a: float) -> float:
        return abs(factor(a, POSITIONS, weights, WAVELENGTH)) - level

    low = brentq(gap, np.arcsin(u[left]), top, xtol=1e-14)
    high = brentq(gap, top, np.arcsin(u[right]), xtol=1e-14)
    return high - low


def model_checks(experiment: Experiment):
    """The model against its closed forms: the direct sum against the
    closed-form array factor; the peak at the commanded angle; the first
    nulls; the mirror and translation symmetries. Record the tables and
    numbers and return the curves of the figure."""
    weights = steering_weights(CHECK_STEER, POSITIONS, WAVELENGTH)
    direct = factor(ANGLES, POSITIONS, weights, WAVELENGTH)
    closed = uniform_factor(ANGLES, COUNT, SPACING, WAVELENGTH, CHECK_STEER)
    experiment.number(
        "closed-form-gap", below(np.max(np.abs(direct - closed)) / COUNT, 1e-12)
    )
    rows, gaps = [], []
    for degrees in (0.0, 15.0, 30.0, 45.0, 50.0):
        steer = np.radians(degrees)
        found = peak_direction(
            POSITIONS,
            steering_weights(steer, POSITIONS, WAVELENGTH),
            WAVELENGTH,
            steer,
            0.05,
        )
        gaps.append(abs(found - steer))
        rows.append((degrees, np.degrees(found)))
    experiment.table(
        "steering",
        rows,
        [("commanded", "deg", ".1f"), ("peak found", "deg", ".9f")],
        "The direction of the largest field of the equal-amplitude array "
        "steered to each angle, found by a search on the computed pattern, "
        "to nine decimals of a degree.",
    )
    experiment.number("steering-gap", below(np.degrees(max(gaps)), 1e-9))
    rows, gaps, nulls = [], [], []
    shift = WAVELENGTH / (COUNT * SPACING)
    for m in (-3, -2, -1, 1, 2, 3):
        predicted = np.arcsin(np.sin(CHECK_STEER) + m * shift)
        bracket = np.arcsin(
            np.clip(np.sin(CHECK_STEER) + (m + np.array([-0.4, 0.4])) * shift, -1, 1)
        )
        found = null_direction(POSITIONS, weights, WAVELENGTH, *bracket)
        gaps.append(abs(found - predicted))
        nulls.append(found)
        rows.append((m, np.degrees(predicted), np.degrees(found)))
    experiment.table(
        "nulls",
        rows,
        [
            ("m", "", "d"),
            ("closed form", "deg", ".6f"),
            ("found", "deg", ".6f"),
        ],
        "The nulls nearest the main lobe of the equal-amplitude array steered "
        "to 30 degrees: the closed form sin(psi) = sin(psi0) + m lambda / (N d) "
        "against the sign changes of the computed array factor, to six "
        "decimals of a degree.",
    )
    experiment.number("null-gap", below(np.degrees(max(gaps)), 1e-9))
    mirrored = factor(
        -ANGLES,
        POSITIONS,
        steering_weights(-CHECK_STEER, POSITIONS, WAVELENGTH),
        WAVELENGTH,
    )
    experiment.number(
        "mirror-gap",
        below(np.max(np.abs(np.abs(direct) - np.abs(mirrored))) / COUNT, 1e-12),
    )
    # Steering only translates the pattern in u = sin(psi).
    u = np.linspace(-1.0, 1.0 - np.sin(CHECK_STEER), 801)
    broadside = factor(
        np.arcsin(u),
        POSITIONS,
        steering_weights(0.0, POSITIONS, WAVELENGTH),
        WAVELENGTH,
    )
    steered = factor(np.arcsin(u + np.sin(CHECK_STEER)), POSITIONS, weights, WAVELENGTH)
    experiment.number(
        "translation-gap", below(np.max(np.abs(broadside - steered)) / COUNT, 1e-12)
    )
    return direct, closed, nulls


def onset_shift(level: float) -> float:
    """The relative amount by which a threshold ``level`` below the full
    height detects a grating lobe early: near its peak a lobe of N equal
    elements falls as 1 - (N^2 - 1) x^2 / 24 in x = k d (u - u_lobe), and at
    the onset spacing x = 2 pi times the relative shortfall of the spacing."""
    return float(np.sqrt(24.0 * (1.0 - level) / (COUNT**2 - 1)) / (2 * np.pi))


def grating_lobes(experiment: Experiment):
    """The onset of grating lobes: the spacing at which a second lobe of
    full height enters the visible directions, found by bisection, against
    lambda / (1 + sin psi0); the spacing the band and the scan allow. Record
    and return the curves of the figure."""
    level = 1.0 - 1e-6
    rows, residuals, measured = [], [], []
    for degrees in (0.0, 15.0, 30.0, 45.0, 60.0):
        steer = np.radians(degrees)
        found = grating_onset(COUNT, WAVELENGTH, steer, level)
        closed = WAVELENGTH / (1.0 + np.sin(steer))
        gap = found / closed - 1.0
        residuals.append(abs(gap + onset_shift(level)))
        measured.append((degrees, found / WAVELENGTH))
        rows.append((degrees, closed / WAVELENGTH, found / WAVELENGTH, gap))
    experiment.table(
        "grating-onset",
        rows,
        [
            ("steered to", "deg", ".0f"),
            ("closed form", "wavelengths", ".6f"),
            ("bisection", "wavelengths", ".6f"),
            ("relative gap", "", ".2e"),
        ],
        "The smallest element spacing at which a second lobe reaches the "
        "height of the main lobe, to one part in a million, for sixteen "
        "elements: the closed form lambda / (1 + sin psi0) against the "
        "bisection on the computed pattern.",
    )
    experiment.number("onset-shift", onset_shift(level), ".2e")
    experiment.number("onset-residual", below(max(residuals), 1e-8))
    top = SPEED_OF_LIGHT / BAND[1]
    experiment.number("largest-spacing", 1e3 * top / (1.0 + np.sin(SCAN)), ".2f")
    experiment.number("spacing", 1e3 * SPACING, ".0f")
    experiment.number("onset-scan", np.degrees(np.arcsin(top / SPACING - 1.0)), ".1f")
    curves = {}
    for ratio in (0.5, 1.0):
        positions = line_positions(COUNT, ratio * WAVELENGTH)
        weights = steering_weights(CHECK_STEER, positions, WAVELENGTH)
        power = np.abs(factor(ANGLES, positions, weights, WAVELENGTH)) ** 2
        curves[ratio] = db(np.maximum(power / power.max(), 1e-12))
    return curves, measured


def taper_and_null(experiment: Experiment):
    """The amplitude taper and the null: the largest sidelobe and the
    half-power width of equal amplitudes and of the Chebyshev taper; the
    depth of the null toward the interferer and its cost, against 1 - r^2
    for equal amplitudes. Record and return the curves of the figure."""
    uniform = steering_weights(NULL_STEER, POSITIONS, WAVELENGTH)
    tapered = design_weights(NULL_STEER)
    rows = []
    for name, weights in (("equal amplitudes", uniform), ("Chebyshev taper", tapered)):
        rows.append(
            (
                name,
                largest_sidelobe(weights, NULL_STEER),
                np.degrees(half_power_width(weights, NULL_STEER)),
                -db(realised_gain(weights, NULL_STEER, POSITIONS, WAVELENGTH)),
            )
        )
    experiment.table(
        "taper",
        rows,
        [
            ("amplitudes", "", ""),
            ("largest sidelobe", "dB", ".6f"),
            ("half-power width", "deg", ".2f"),
            ("loss against equal amplitudes", "dB", ".2f"),
        ],
        "The sixteen-element array steered to -10 degrees: its largest "
        "sidelobe below the main lobe, its half-power beam width, and the "
        "power it sends toward the receiver for the same total power into "
        "the elements, with equal amplitudes and with the Dolph-Chebyshev "
        "taper designed for 30 dB.",
    )
    experiment.number("taper-gap", below(abs(rows[1][1] + SIDELOBES), 1e-6))
    experiment.number("uniform-sidelobe", rows[0][1], ".2f")
    experiment.number("taper-loss", rows[1][3], ".2f")
    # The null toward the interferer.
    nulled = null_weights(uniform, INTERFERER, POSITIONS, WAVELENGTH)
    depth = abs(factor(INTERFERER, POSITIONS, nulled, WAVELENGTH)) / abs(
        factor(NULL_STEER, POSITIONS, nulled, WAVELENGTH)
    )
    experiment.number("ideal-null", below(depth, 1e-12))
    rows, gaps = [], []
    for separation in (2.0, 4.0, 6.0, 8.0, 10.0, 15.0, 30.0):
        receiver = INTERFERER - np.radians(separation)
        steered = steering_weights(receiver, POSITIONS, WAVELENGTH)
        cost = realised_gain(
            null_weights(steered, INTERFERER, POSITIONS, WAVELENGTH),
            receiver,
            POSITIONS,
            WAVELENGTH,
        )
        r = uniform_factor(INTERFERER, COUNT, SPACING, WAVELENGTH, receiver) / COUNT
        closed = 1.0 - r**2
        gaps.append(abs(cost / closed - 1.0))
        tapered_cost = realised_gain(
            design_weights(receiver, INTERFERER), receiver, POSITIONS, WAVELENGTH
        ) / realised_gain(design_weights(receiver), receiver, POSITIONS, WAVELENGTH)
        rows.append((separation, -db(closed), -db(cost), -db(tapered_cost)))
    experiment.table(
        "null-cost",
        rows,
        [
            ("receiver from interferer", "deg", ".0f"),
            ("cost, closed form", "dB", ".3f"),
            ("cost, equal amplitudes", "dB", ".3f"),
            ("cost, Chebyshev taper", "dB", ".3f"),
        ],
        "The gain toward the receiver that a null toward the interferer at "
        "20 degrees costs, for the same total power into the elements, as "
        "the receiver approaches the interferer: equal amplitudes against "
        "the closed form 1 - r^2, with r the array factor toward the "
        "interferer of the beam steered to the receiver over N, and the "
        "tapered design.",
    )
    experiment.number("null-cost-gap", below(max(gaps), 1e-12))
    return {
        "Chebyshev taper": pattern_db(tapered),
        "taper and null": pattern_db(design_weights(NULL_STEER, INTERFERER)),
    }


def null_statistics(realised: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The power toward the receiver and toward the interferer of each row
    of ``realised`` weights (draws, N) of the study's beam."""
    toward = steering_vector(NULL_STEER, POSITIONS, WAVELENGTH)
    away = steering_vector(INTERFERER, POSITIONS, WAVELENGTH)
    return np.abs(realised @ toward) ** 2, np.abs(realised @ away) ** 2


def channel_errors(
    rng: np.random.Generator, draws: int, phase: float, amplitude: float
):
    """Independent multiplicative channel errors (draws, N): a relative
    amplitude error and a phase error, both normal with the standard
    deviations ``amplitude`` and ``phase`` (rad)."""
    return (1.0 + amplitude * rng.standard_normal((draws, COUNT))) * np.exp(
        1j * phase * rng.standard_normal((draws, COUNT))
    )


def degradation(experiment: Experiment):
    """Quantisation and channel errors on the design beam (taper, receiver
    at -10 degrees, null at 20 degrees), by Monte Carlo with a fixed seed:
    the mean gain loss and the mean null depth against the exact expected
    pattern; rounding without insertion phases; the number of bits the
    requirement needs with the channel errors. Record and return the
    curve of the figure and the chosen number of bits."""
    rng = np.random.default_rng(SEED)
    ideal = design_weights(NULL_STEER, INTERFERER)
    main_power = abs(factor(NULL_STEER, POSITIONS, ideal, WAVELENGTH)) ** 2
    rows, measured_curve = [], []
    for bits in BITS:
        offsets = rng.uniform(0.0, 2 * np.pi, (DRAWS, COUNT))
        toward, away = null_statistics(quantise(ideal, bits, offsets))
        m = mean_phase_factor("uniform", 2 * np.pi / 2**bits)
        expected_main = float(expected_power(np.sqrt(main_power), ideal, m))
        expected_null = float(expected_power(0.0, ideal, m))
        rows.append(
            (
                bits,
                -db(m**2),
                -db(toward.mean() / main_power),
                db(expected_null / expected_main),
                db(away.mean() / toward.mean()),
            )
        )
        measured_curve.append(
            (bits, db(away.mean() / toward.mean()), db(expected_null / expected_main))
        )
    experiment.table(
        "quantisation",
        rows,
        [
            ("bits", "", "d"),
            ("gain loss, expected", "dB", ".3f"),
            ("gain loss, mean", "dB", ".3f"),
            ("null depth, expected", "dB", ".2f"),
            ("null depth, mean", "dB", ".2f"),
        ],
        f"The design beam with quantised phase shifters and random insertion "
        f"phases, {DRAWS} realised arrays per row: the mean loss of power "
        f"toward the receiver and the mean power toward the interferer "
        f"relative to it, against the exact expectation.",
    )
    experiment.number(
        "quantisation-gap",
        max(abs(row[2] - row[1]) for row in rows),
        ".3f",
    )
    experiment.number(
        "quantisation-null-gap", max(abs(row[4] - row[3]) for row in rows), ".2f"
    )
    experiment.number("draws", DRAWS, "d")
    # Rounding without insertion phases: the errors repeat along the array.
    lobe_steer = np.radians(10.0)
    tapered = design_weights(lobe_steer)
    rounded = quantise(tapered, LOBE_BITS)
    realisations = [
        quantise(tapered, LOBE_BITS, rng.uniform(0.0, 2 * np.pi, COUNT))
        for _ in range(LOBE_DRAWS)
    ]
    experiment.number("lobe-bits", LOBE_BITS, "d")
    experiment.number("lobe-draws", LOBE_DRAWS, "d")
    experiment.number("rounding-lobe", largest_sidelobe(rounded, lobe_steer), ".1f")
    experiment.number(
        "offset-lobe",
        np.mean([largest_sidelobe(w, lobe_steer) for w in realisations]),
        ".1f",
    )
    # Channel errors alone.
    rows = []
    for degrees in (1.0, 2.0, 5.0, 10.0):
        errors = channel_errors(rng, DRAWS, np.radians(degrees), AMPLITUDE_ERROR)
        toward, away = null_statistics(errors * ideal)
        m = mean_phase_factor("normal", np.radians(degrees))
        square = 1.0 + AMPLITUDE_ERROR**2
        expected_main = float(expected_power(np.sqrt(main_power), ideal, m, square))
        expected_null = float(expected_power(0.0, ideal, m, square))
        rows.append(
            (
                degrees,
                -db(expected_main / main_power),
                -db(toward.mean() / main_power),
                db(expected_null / expected_main),
                db(away.mean() / toward.mean()),
            )
        )
    experiment.table(
        "channel-errors",
        rows,
        [
            ("rms phase error", "deg", ".0f"),
            ("gain change, expected", "dB", ".4f"),
            ("gain change, mean", "dB", ".4f"),
            ("null depth, expected", "dB", ".2f"),
            ("null depth, mean", "dB", ".2f"),
        ],
        f"The design beam with random channel errors, a relative amplitude "
        f"error of rms 0.02 and the phase error of each row, {DRAWS} realised "
        f"arrays per row, against the exact expectation; a negative change "
        f"is a loss.",
    )
    experiment.number(
        "channel-null-gap", max(abs(row[4] - row[3]) for row in rows), ".2f"
    )
    # The decision: bits with the channel-error budget.
    rows, chosen = [], None
    for bits in BITS:
        offsets = rng.uniform(0.0, 2 * np.pi, (DRAWS, COUNT))
        errors = channel_errors(rng, DRAWS, PHASE_ERROR, AMPLITUDE_ERROR)
        toward, away = null_statistics(errors * quantise(ideal, bits, offsets))
        depth = db(away / toward)
        worst = float(np.percentile(depth, 100 * CONFIDENCE))
        rows.append(
            (bits, float(np.median(depth)), worst, float(np.mean(depth > -NULL_DEPTH)))
        )
        if chosen is None and worst <= -NULL_DEPTH:
            chosen = bits
    experiment.table(
        "decision",
        rows,
        [
            ("bits", "", "d"),
            ("null depth, median", "dB", ".1f"),
            ("null depth, 95th percentile", "dB", ".1f"),
            ("share of arrays short of 30 dB", "", ".3f"),
        ],
        f"The null depth of realised arrays of the design, {DRAWS} per row, "
        f"with quantised phase shifters, random insertion phases, and channel "
        f"errors of rms 2 degrees and 0.02 in amplitude: the median and the "
        f"level that nineteen arrays in twenty reach or beat.",
    )
    if chosen is None:
        raise ValueError("no number of bits meets the null requirement")
    experiment.number("chosen-bits", chosen, "d")
    return measured_curve, chosen


def band(experiment: Experiment):
    """Phase steering across the band: the peak of a beam set for 50
    degrees at the carrier against arcsin((f0 / f) sin psi0), the gain lost
    toward 50 degrees, and the depth of the design's null at each frequency;
    record the table and numbers. The ideal null must meet the requirement
    at every frequency of the band."""
    weights = steering_weights(SCAN, POSITIONS, WAVELENGTH)
    nulled = design_weights(NULL_STEER, INTERFERER)
    rows, gaps = [], []
    for f in (BAND[0], 9.75e9, FREQUENCY, 10.25e9, BAND[1]):
        wavelength = SPEED_OF_LIGHT / f
        predicted = np.arcsin(FREQUENCY / f * np.sin(SCAN))
        found = peak_direction(POSITIONS, weights, wavelength, predicted, 0.05)
        gaps.append(abs(found - predicted))
        peak = abs(factor(found, POSITIONS, weights, wavelength)) ** 2
        toward = abs(factor(SCAN, POSITIONS, weights, wavelength)) ** 2
        depth = (
            abs(factor(INTERFERER, POSITIONS, nulled, wavelength)) ** 2
            / abs(factor(NULL_STEER, POSITIONS, nulled, wavelength)) ** 2
        )
        rows.append(
            (
                1e-9 * f,
                np.degrees(predicted),
                np.degrees(found),
                db(toward / peak),
                db(depth) if f != FREQUENCY else None,
            )
        )
    experiment.table(
        "band",
        rows,
        [
            ("f", "GHz", ".2f"),
            ("peak, closed form", "deg", ".4f"),
            ("peak found", "deg", ".4f"),
            ("field toward 50 degrees", "dB", ".2f"),
            ("null depth of the design", "dB", ".1f"),
        ],
        "A beam whose phases are set for 50 degrees at 10 GHz, used across "
        "the band: its peak against arcsin((f0 / f) sin psi0) and the level "
        "it keeps toward 50 degrees; and the depth of the design's null "
        "toward the interferer, exact at the carrier (left empty), at the "
        "other frequencies.",
    )
    experiment.number("squint-gap", below(np.degrees(max(gaps)), 1e-9))
    experiment.number("squint", np.degrees(SCAN) - rows[-1][2], ".1f")
    experiment.number("edge-loss", -min(row[3] for row in rows), ".2f")
    edge = max(row[4] for row in rows if row[4] is not None)
    if edge > -NULL_DEPTH:
        raise ValueError(f"the band-edge null, {edge!r} dB, misses the requirement")
    experiment.number("edge-null", edge, ".1f")
    experiment.number("edge-null-margin", -NULL_DEPTH - edge, ".1f")


def element_pattern(experiment: Experiment):
    """Dipoles along the array's axis: the peak of element pattern times
    array factor against the commanded angle, and the loss of the element
    pattern there; record the table and numbers."""
    rows = []
    for degrees in (0.0, 20.0, 40.0, 50.0, 60.0):
        steer = np.radians(degrees)
        weights = steering_weights(steer, POSITIONS, WAVELENGTH)
        found = peak_direction(
            POSITIONS, weights, WAVELENGTH, steer, 0.15, element=dipole_element
        )
        rows.append((degrees, np.degrees(found), db(float(dipole_element(steer)) ** 2)))
    experiment.table(
        "element",
        rows,
        [
            ("commanded", "deg", ".0f"),
            ("peak with dipole elements", "deg", ".2f"),
            ("element pattern there", "dB", ".2f"),
        ],
        "Half-wave dipoles along the array's axis: the direction of the "
        "largest field of element pattern times array factor, and the "
        "element pattern's level at the commanded angle relative to "
        "broadside.",
    )
    experiment.number("element-pull", rows[3][0] - rows[3][1], ".2f")
    experiment.number("element-loss", -rows[3][2], ".1f")


def tracking(experiment: Experiment, bits: int):
    """The receiver passing along a road ROAD from the array at SPEED, the
    interferer fixed: at each step the design's weights for the receiver's
    direction, a null toward the interferer where it costs at most
    FEASIBLE_LOSS, realised by one array with ``bits``-bit shifters, fixed
    insertion phases, and fixed channel errors. Record and return the
    history and the frames of the figures."""
    rng = np.random.default_rng(SEED + 1)
    offsets = rng.uniform(0.0, 2 * np.pi, COUNT)
    errors = channel_errors(rng, 1, PHASE_ERROR, AMPLITUDE_ERROR)[0]
    half = ROAD * np.tan(SCAN) / SPEED
    times = np.linspace(-half, half, STEPS)
    history = []
    for t in times:
        receiver = float(np.arctan(SPEED * t / ROAD))
        plain = design_weights(receiver)
        nulled = design_weights(receiver, INTERFERER)
        cost = -db(
            realised_gain(nulled, receiver, POSITIONS, WAVELENGTH)
            / realised_gain(plain, receiver, POSITIONS, WAVELENGTH)
        )
        placed = cost <= FEASIBLE_LOSS
        realised = errors * quantise(nulled if placed else plain, bits, offsets)
        gain = db(realised_gain(realised, receiver, POSITIONS, WAVELENGTH))
        level = db(
            abs(factor(INTERFERER, POSITIONS, realised, WAVELENGTH)) ** 2
            / abs(factor(receiver, POSITIONS, realised, WAVELENGTH)) ** 2
        )
        history.append((t, receiver, placed, gain, level, realised))
    placed = [row for row in history if row[2]]
    skipped = [row for row in history if not row[2]]
    experiment.table(
        "tracking",
        [
            (t, np.degrees(receiver), "yes" if on else "no", gain, level)
            for t, receiver, on, gain, level, _ in history[::12]
        ],
        [
            ("time", "s", ".1f"),
            ("receiver", "deg", ".1f"),
            ("null placed", "", ""),
            ("gain toward receiver", "dB", ".2f"),
            ("interferer below receiver", "dB", ".1f"),
        ],
        f"Every twelfth of the {STEPS} weight updates of the pass: the "
        f"receiver's direction, whether the null was placed, the power toward "
        f"the receiver relative to an ideal equal-amplitude beam steered to "
        f"it, and the interferer's level relative to the receiver's, for one "
        f"realised array with {bits}-bit phase shifters.",
    )
    experiment.number("steps", STEPS, "d")
    experiment.number("pass-time", 2 * half, ".1f")
    experiment.number("worst-null", max(row[4] for row in placed), ".1f")
    experiment.number("worst-gain", -min(row[3] for row in placed), ".2f")
    experiment.number("window-low", np.degrees(min(row[1] for row in skipped)), ".1f")
    experiment.number("window-high", np.degrees(max(row[1] for row in skipped)), ".1f")
    experiment.number(
        "met-share",
        np.mean([row[4] <= -NULL_DEPTH for row in history]),
        ".2f",
    )
    frames = [history[i] for i in (0, 36, 60, 72, 78, 120)]
    return history, frames


def draw_steered_pattern(direct, closed, nulls) -> Figure:
    """The power pattern of the equal-amplitude array steered to 30
    degrees: the direct sum, the closed form, the commanded angle and the
    closed-form nulls."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    degrees = np.degrees(ANGLES)
    power = db(np.maximum(np.abs(direct) ** 2 / COUNT**2, 1e-12))
    ax.plot(degrees, power, color=FIGURE_COLOURS[0], label="direct sum")
    every = slice(0, None, 40)
    ax.plot(
        degrees[every],
        db(np.maximum(closed[every] ** 2 / COUNT**2, 1e-12)),
        color=FIGURE_COLOURS[1],
        marker="o",
        markersize=3,
        linestyle="none",
        label="closed form",
    )
    ax.axvline(
        np.degrees(CHECK_STEER),
        color=FIGURE_COLOURS[2],
        linestyle="--",
        label="commanded angle",
    )
    for i, null in enumerate(nulls):
        ax.axvline(
            np.degrees(null),
            color=FIGURE_COLOURS[3],
            linestyle=":",
            label="nulls, closed form" if i == 0 else None,
        )
    ax.set_ylim(-60, 3)
    ax.set_xlim(-90, 90)
    ax.set_xlabel("direction from broadside (deg)")
    ax.set_ylabel("power below the peak (dB)")
    ax.legend(frameon=False, loc="upper left", fontsize="small")
    fig.tight_layout()
    return fig


def draw_grating_lobes(curves, measured) -> Figure:
    """Left: patterns steered to 30 degrees at two spacings. Right: the
    measured onset spacing against lambda / (1 + sin psi0)."""
    fig, (left, right) = plt.subplots(1, 2, figsize=(7.2, 3.6))
    degrees = np.degrees(ANGLES)
    for (ratio, power), colour, line in zip(
        curves.items(), FIGURE_COLOURS[:2], ("-", "--"), strict=True
    ):
        left.plot(
            degrees,
            power,
            color=colour,
            linestyle=line,
            label=f"d = {ratio:g} wavelength",
        )
    left.set_ylim(-40, 3)
    left.set_xlim(-90, 90)
    left.set_xlabel("direction from broadside (deg)")
    left.set_ylabel("power below the peak (dB)")
    left.legend(
        frameon=False,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.2),
        fontsize="x-small",
    )
    steer = np.radians(np.linspace(0.0, 70.0, 200))
    right.plot(
        np.degrees(steer),
        1.0 / (1.0 + np.sin(steer)),
        color=FIGURE_COLOURS[0],
        label="closed form",
    )
    right.plot(
        [row[0] for row in measured],
        [row[1] for row in measured],
        color=FIGURE_COLOURS[1],
        marker="s",
        linestyle="none",
        label="bisection",
    )
    right.set_xlabel("steered to (deg)")
    right.set_ylabel("onset spacing (wavelengths)")
    right.legend(frameon=False, loc="upper right", fontsize="x-small")
    fig.tight_layout()
    return fig


def draw_taper_and_null(curves) -> Figure:
    """The design beam: the Chebyshev taper, and the taper with the null
    toward the interferer."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    degrees = np.degrees(ANGLES)
    for (name, power), colour, line in zip(
        curves.items(), FIGURE_COLOURS[:2], ("-", "--"), strict=True
    ):
        ax.plot(degrees, power, color=colour, linestyle=line, label=name)
    ax.axhline(
        -SIDELOBES,
        color=FIGURE_COLOURS[3],
        linewidth=0.8,
        linestyle="-.",
        label="taper design level",
    )
    ax.axvline(
        np.degrees(INTERFERER),
        color=FIGURE_COLOURS[4],
        linewidth=0.8,
        label="interferer",
    )
    ax.set_ylim(-60, 3)
    ax.set_xlim(-90, 90)
    ax.set_xlabel("direction from broadside (deg)")
    ax.set_ylabel("power below the peak (dB)")
    ax.legend(frameon=False, loc="upper left", fontsize="x-small")
    fig.tight_layout()
    return fig


def draw_quantisation(measured) -> Figure:
    """The mean null depth against the bits of the phase shifters: the Monte
    Carlo mean against the exact expectation."""
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    bits = [row[0] for row in measured]
    ax.plot(
        bits, [row[2] for row in measured], color=FIGURE_COLOURS[0], label="expected"
    )
    ax.plot(
        bits,
        [row[1] for row in measured],
        color=FIGURE_COLOURS[1],
        marker="o",
        linestyle="none",
        label="Monte Carlo mean",
    )
    ax.set_xlabel("phase-shifter bits")
    ax.set_ylabel("mean null depth (dB)")
    ax.legend(frameon=False, loc="upper right", fontsize="small")
    fig.tight_layout()
    return fig


def draw_tracking_sequence(frames) -> Figure:
    """Six moments of the pass: the realised array's power pattern, the
    receiver and the interferer."""
    fig, axes = plt.subplots(2, 3, figsize=(7.2, 4.4), sharex=True, sharey=True)
    degrees = np.degrees(ANGLES)
    for ax, (t, receiver, placed, _, _, realised) in zip(
        axes.flat, frames, strict=True
    ):
        ax.plot(degrees, pattern_db(realised), color=FIGURE_COLOURS[0], linewidth=1.0)
        ax.axvline(
            np.degrees(receiver), color=FIGURE_COLOURS[1], linestyle="--", linewidth=1.0
        )
        ax.axvline(
            np.degrees(INTERFERER),
            color=FIGURE_COLOURS[3],
            linestyle=":",
            linewidth=1.2,
        )
        ax.set_title(
            f"t = {t:.1f} s, {'null placed' if placed else 'no null'}", fontsize="small"
        )
        ax.set_ylim(-60, 3)
        ax.set_xlim(-90, 90)
    for ax in axes[-1]:
        ax.set_xlabel("direction (deg)")
    for ax in axes[:, 0]:
        ax.set_ylabel("power (dB)")
    handles = [
        plt.Line2D([], [], color=FIGURE_COLOURS[0], label="realised pattern"),
        plt.Line2D([], [], color=FIGURE_COLOURS[1], linestyle="--", label="receiver"),
        plt.Line2D([], [], color=FIGURE_COLOURS[3], linestyle=":", label="interferer"),
    ]
    fig.legend(
        handles=handles, loc="lower center", ncol=3, frameon=False, fontsize="small"
    )
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    return fig


def draw_tracking_history(history) -> Figure:
    """Over the pass: the gain toward the receiver and the interferer's
    level below it, with the requirement and the steps without a null."""
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(6.4, 4.4), sharex=True)
    t = np.array([row[0] for row in history])
    skipped = np.array([not row[2] for row in history])
    for ax in (top, bottom):
        ax.fill_between(
            t,
            0,
            1,
            where=skipped,
            color=FIGURE_COLOURS[2],
            alpha=0.15,
            transform=ax.get_xaxis_transform(),
            label="no null (infeasible)",
        )
    top.plot(
        t,
        [row[3] for row in history],
        color=FIGURE_COLOURS[0],
        marker="o",
        markersize=2,
        label="gain toward receiver",
    )
    top.set_ylabel("gain (dB)")
    top.legend(frameon=False, loc="lower left", fontsize="x-small")
    bottom.plot(
        t,
        [row[4] for row in history],
        color=FIGURE_COLOURS[1],
        marker="s",
        markersize=2,
        label="interferer below receiver",
    )
    bottom.axhline(
        -NULL_DEPTH, color=FIGURE_COLOURS[3], linestyle="--", label="requirement"
    )
    bottom.set_ylabel("level (dB)")
    bottom.set_xlabel("time from the closest approach (s)")
    bottom.legend(frameon=False, loc="lower left", fontsize="x-small")
    fig.tight_layout()
    return fig


def largest_spacing(experiment: Experiment) -> None:
    """Exercise 1: the largest spacing that keeps grating lobes out when an
    array steers to 60 degrees at 12 GHz; record it."""
    wavelength = SPEED_OF_LIGHT / 12e9
    experiment.number(
        "exercise-spacing", 1e3 * wavelength / (1.0 + np.sin(np.radians(60.0))), ".2f"
    )


def bits_for_null(experiment: Experiment) -> None:
    """Exercise 2: the fewest bits whose expected null depth reaches 40 dB
    for the equal-amplitude array steered to -10 degrees with its null at
    20 degrees, with no other error; record the table."""
    ideal = null_weights(
        steering_weights(NULL_STEER, POSITIONS, WAVELENGTH),
        INTERFERER,
        POSITIONS,
        WAVELENGTH,
    )
    main_field = abs(factor(NULL_STEER, POSITIONS, ideal, WAVELENGTH))
    rows = []
    for bits in range(3, 9):
        m = mean_phase_factor("uniform", 2 * np.pi / 2**bits)
        rows.append(
            (
                bits,
                db(
                    float(expected_power(0.0, ideal, m))
                    / float(expected_power(main_field, ideal, m))
                ),
            )
        )
    experiment.table(
        "exercise-bits",
        rows,
        [("bits", "", "d"), ("expected null depth", "dB", ".1f")],
        "The expected depth of the null of the equal-amplitude array, with "
        "random insertion phases and no other error, for each number of "
        "phase-shifter bits.",
    )


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    direct, closed, nulls = model_checks(experiment)
    experiment.figure(
        "fig-steered-pattern", partial(draw_steered_pattern, direct, closed, nulls)
    )
    curves, measured = grating_lobes(experiment)
    experiment.figure(
        "fig-grating-lobes", partial(draw_grating_lobes, curves, measured)
    )
    experiment.figure(
        "fig-taper-and-null", partial(draw_taper_and_null, taper_and_null(experiment))
    )
    measured_null, bits = degradation(experiment)
    experiment.figure("fig-quantisation", partial(draw_quantisation, measured_null))
    band(experiment)
    element_pattern(experiment)
    history, frames = tracking(experiment, bits)
    experiment.figure("fig-tracking-sequence", partial(draw_tracking_sequence, frames))
    experiment.figure("fig-tracking-history", partial(draw_tracking_history, history))
    largest_spacing(experiment)
    bits_for_null(experiment)
    return experiment


if __name__ == "__main__":
    main(run)
