"""The measurement-quality analysis of pbc.electromagnetism.measurement (F142),
each against a case whose answer is known."""

import math

import numpy as np
import pytest

from pbc.electromagnetism.measurement import (
    alias,
    calibrate,
    correct,
    dominant_frequency,
    fit_sine,
    quality,
    valid_samples,
)

RATE, FREQUENCY = 64_000.0, 1_000.0
T = np.arange(513) / RATE


def sine(amplitude=1.3, phase=0.4, offset=0.2):
    return amplitude * np.cos(2 * math.pi * FREQUENCY * T + phase) + offset


def test_the_fit_of_an_exact_sinusoid_is_exact():
    fit = fit_sine(T, sine(), FREQUENCY)
    assert (fit.amplitude, fit.phase, fit.offset) == pytest.approx((1.3, 0.4, 0.2))
    assert fit.residual_rms < 1e-12 and fit.used == len(T)


def test_the_fit_reports_the_standard_error_of_white_noise():
    """sigma sqrt(2 / N) for the amplitude, over many seeded records."""
    sigma, found, reported = 0.05, [], []
    for seed in range(200):
        noisy = sine() + np.random.default_rng(seed).normal(0, sigma, len(T))
        fit = fit_sine(T, noisy, FREQUENCY)
        found.append(fit.amplitude)
        reported.append(fit.amplitude_error)
    expected = sigma * math.sqrt(2 / len(T))
    assert np.std(found, ddof=1) == pytest.approx(expected, rel=0.15)
    assert np.mean(reported) == pytest.approx(expected, rel=0.02)
    assert np.mean(found) == pytest.approx(1.3, abs=3 * expected / math.sqrt(200))


def test_lost_and_masked_samples_are_left_out():
    v = sine()
    v[100:180] = np.nan
    mask = np.ones(len(T), dtype=bool)
    mask[300:320] = False
    v[300:320] = 99.0  # nonsense, masked
    fit = fit_sine(T, v, FREQUENCY, valid=mask)
    assert fit.amplitude == pytest.approx(1.3) and fit.used == len(T) - 100
    with pytest.raises(ValueError, match="more than three"):
        fit_sine(T[:3], v[:3], FREQUENCY)


def test_the_valid_samples_lie_inside_the_rails_by_half_a_step():
    v = np.array([0.0, 0.99, 1.0, -1.0, np.nan, 0.97])
    np.testing.assert_array_equal(
        valid_samples(v, 1.0, step_v=0.04), [True, False, False, False, False, True]
    )


def test_the_quality_report_flags_each_defect():
    v = np.clip(sine(amplitude=2.0, offset=0.0), -1.5, 1.5)
    v[:50] = np.nan
    report = quality(v, RATE, FREQUENCY, 1.5, calibrated=False)
    assert report.flags == ("clipped", "samples missing", "not calibrated")
    assert report.missing_fraction == pytest.approx(50 / len(T))
    assert not report.usable
    clean = quality(sine(), RATE, FREQUENCY, 5.0, calibrated=True)
    assert clean.flags == () and clean.usable
    slow = quality(sine(), 1.5 * FREQUENCY, FREQUENCY, 5.0, calibrated=True)
    assert "below the Nyquist rate" in slow.flags and not slow.usable


def test_the_calibration_recovers_a_gain_and_an_offset_and_undoes_them():
    reference = sine(offset=0.0)
    recorded = 0.9 * reference - 0.03
    gain, offset = calibrate(reference, recorded)
    assert (gain, offset) == pytest.approx((0.9, -0.03))
    np.testing.assert_allclose(correct(recorded, gain, offset), reference, atol=1e-12)


@pytest.mark.parametrize(
    ("frequency", "rate", "expected"),
    [(5_000.0, 320_000.0, 5_000.0), (5_000.0, 6_000.0, 1_000.0),
     (5_000.0, 4_000.0, 1_000.0), (3.98, 5.0, 1.02), (5_000.0, 5_000.0, 0.0)],
)  # fmt: skip
def test_the_alias_is_the_distance_to_the_nearest_multiple_of_the_rate(
    frequency, rate, expected
):
    assert alias(frequency, rate) == pytest.approx(expected)


def test_the_dominant_frequency_of_a_sampled_sinusoid_is_its_alias():
    for rate in (64_000.0, 1_500.0):
        t = np.arange(4001) / rate
        v = np.cos(2 * math.pi * FREQUENCY * t + 0.3)
        assert dominant_frequency(v, rate) == pytest.approx(
            alias(FREQUENCY, rate), abs=rate / len(t)
        )
