"""The linear phased array of the electromagnetism capstone, against closed
forms and limiting cases."""

import numpy as np
import pytest

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

WAVELENGTH = 0.03
COUNT = 16
SPACING = 0.5 * WAVELENGTH
POSITIONS = line_positions(COUNT, SPACING)
ANGLES = np.radians(np.linspace(-90.0, 90.0, 1801))


def test_the_elements_are_centred_and_evenly_spaced():
    x = POSITIONS[:, 0]
    assert x.sum() == pytest.approx(0.0, abs=1e-15)
    assert np.diff(x) == pytest.approx(np.full(COUNT - 1, SPACING))
    assert not POSITIONS[:, 1:].any()
    with pytest.raises(ValueError):
        line_positions(1, SPACING)


def test_the_direct_sum_is_the_closed_form_array_factor():
    for steer in np.radians([0.0, 25.0, -60.0]):
        weights = steering_weights(steer, POSITIONS, WAVELENGTH)
        direct = factor(ANGLES, POSITIONS, weights, WAVELENGTH)
        closed = uniform_factor(ANGLES, COUNT, SPACING, WAVELENGTH, steer)
        assert np.max(np.abs(direct - closed)) < 1e-12 * COUNT


def test_the_closed_form_takes_its_limit_on_the_main_and_grating_lobes():
    # Two wavelengths apart, broadside: lobes of full height wherever
    # d sin(psi) is a whole number of wavelengths.
    angles = np.arcsin([0.0, 0.5, -0.5, 1.0])
    for count in (4, 5):
        values = uniform_factor(angles, count, 2 * WAVELENGTH, WAVELENGTH, 0.0)
        direct = factor(
            angles,
            line_positions(count, 2 * WAVELENGTH),
            np.ones(count),
            WAVELENGTH,
        )
        assert values == pytest.approx(direct.real, abs=1e-9)
        assert np.abs(values) == pytest.approx(np.full(4, count))


def test_the_beam_points_where_it_is_steered():
    for steer in np.radians([0.0, 20.0, -45.0, 55.0]):
        weights = steering_weights(steer, POSITIONS, WAVELENGTH)
        found = peak_direction(POSITIONS, weights, WAVELENGTH, steer + 0.01, 0.05)
        assert found == pytest.approx(steer, abs=1e-12)
        assert abs(factor(found, POSITIONS, weights, WAVELENGTH)) == pytest.approx(
            COUNT
        )


def test_the_first_nulls_are_where_the_closed_form_puts_them():
    steer = np.radians(30.0)
    weights = steering_weights(steer, POSITIONS, WAVELENGTH)
    shift = WAVELENGTH / (COUNT * SPACING)
    for m in (-1, 1):
        predicted = np.arcsin(np.sin(steer) + m * shift)
        low, high = np.arcsin(np.sin(steer) + (m + np.array([-0.4, 0.4])) * shift)
        found = null_direction(POSITIONS, weights, WAVELENGTH, low, high)
        assert found == pytest.approx(predicted, abs=1e-12)


def test_steering_mirrors_and_translates_the_pattern():
    steer = np.radians(35.0)
    plus = factor(
        ANGLES, POSITIONS, steering_weights(steer, POSITIONS, WAVELENGTH), WAVELENGTH
    )
    minus = factor(
        -ANGLES, POSITIONS, steering_weights(-steer, POSITIONS, WAVELENGTH), WAVELENGTH
    )
    assert np.abs(plus) == pytest.approx(np.abs(minus), abs=1e-11)
    u = np.linspace(-1.0, 1.0 - np.sin(steer), 101)
    broadside = factor(np.arcsin(u), POSITIONS, np.ones(COUNT), WAVELENGTH)
    steered = factor(
        np.arcsin(u + np.sin(steer)),
        POSITIONS,
        steering_weights(steer, POSITIONS, WAVELENGTH),
        WAVELENGTH,
    )
    assert steered == pytest.approx(broadside, abs=1e-11)


def test_the_null_is_exact_and_costs_one_minus_r_squared():
    receiver, interferer = np.radians(-5.0), np.radians(3.0)
    weights = null_weights(
        steering_weights(receiver, POSITIONS, WAVELENGTH),
        interferer,
        POSITIONS,
        WAVELENGTH,
    )
    assert abs(factor(interferer, POSITIONS, weights, WAVELENGTH)) < 1e-12 * COUNT
    r = uniform_factor(interferer, COUNT, SPACING, WAVELENGTH, receiver) / COUNT
    assert realised_gain(weights, receiver, POSITIONS, WAVELENGTH) == pytest.approx(
        1.0 - r**2, rel=1e-12
    )
    # Two nulls at once.
    both = null_weights(weights, [interferer, np.radians(40.0)], POSITIONS, WAVELENGTH)
    for angle in (interferer, np.radians(40.0)):
        assert abs(factor(angle, POSITIONS, both, WAVELENGTH)) < 1e-12 * COUNT


def test_equal_amplitudes_steered_have_unit_gain():
    steer = np.radians(12.0)
    weights = steering_weights(steer, POSITIONS, WAVELENGTH)
    assert realised_gain(weights, steer, POSITIONS, WAVELENGTH) == pytest.approx(1.0)
    assert steering_vector(steer, POSITIONS, WAVELENGTH) @ weights == pytest.approx(
        COUNT
    )


def test_the_grating_onset_is_lambda_over_one_plus_sin():
    level = 1.0 - 1e-6
    shift = np.sqrt(24 * (1 - level) / (COUNT**2 - 1)) / (2 * np.pi)
    for steer in np.radians([0.0, 30.0, 50.0]):
        found = grating_onset(COUNT, WAVELENGTH, steer, level)
        closed = WAVELENGTH / (1 + np.sin(steer))
        assert found / closed - 1.0 == pytest.approx(-shift, abs=1e-8)


def test_the_chebyshev_taper_has_equal_sidelobes_at_its_level():
    taper = chebyshev_taper(COUNT, 30.0)
    assert taper.max() == pytest.approx(1.0)
    assert taper == pytest.approx(taper[::-1])
    u = np.linspace(-1.0, 1.0, 40001)
    power = np.abs(factor(np.arcsin(u), POSITIONS, taper, WAVELENGTH)) ** 2
    power /= power.max()
    peaks = (power[1:-1] > power[:-2]) & (power[1:-1] > power[2:])
    sidelobes = np.sort(10 * np.log10(power[1:-1][peaks]))[:-1]
    assert sidelobes == pytest.approx(np.full(sidelobes.size, -30.0), abs=1e-3)


def test_quantisation_rounds_the_phase_and_keeps_the_amplitude():
    weights = 0.7 * np.exp(1j * np.array([0.1, 1.0, -2.0, 3.1]))
    for bits in (1, 2, 3, 6):
        step = 2 * np.pi / 2**bits
        q = quantise(weights, bits)
        assert np.abs(q) == pytest.approx(np.abs(weights))
        error = np.angle(q * np.conj(weights))
        assert np.all(np.abs(error) <= 0.5 * step + 1e-12)
        ratio = np.angle(q) / step
        assert ratio == pytest.approx(np.round(ratio), abs=1e-9)
    offsets = np.array([0.3, -1.2, 2.2, 0.0])
    q = quantise(weights, 3, offsets)
    shifter = (np.angle(q) - offsets) / (2 * np.pi / 8)
    residue = np.angle(np.exp(2j * np.pi * (shifter - np.round(shifter))))
    assert residue == pytest.approx(np.zeros(4), abs=1e-9)


def test_the_mean_phase_factors_are_the_closed_forms():
    rng = np.random.default_rng(1)
    size = 2 * np.pi / 8
    uniform = rng.uniform(-size / 2, size / 2, 400000)
    assert mean_phase_factor("uniform", size) == pytest.approx(
        np.mean(np.exp(1j * uniform)).real, abs=2e-4
    )
    assert mean_phase_factor("uniform", size) == pytest.approx(
        np.sin(size / 2) / (size / 2)
    )
    assert mean_phase_factor("normal", 0.2) == pytest.approx(np.exp(-0.02))
    with pytest.raises(ValueError):
        mean_phase_factor("other", 1.0)


def test_the_expected_power_matches_a_monte_carlo_estimate():
    rng = np.random.default_rng(2)
    steer = np.radians(10.0)
    weights = steering_weights(
        steer, POSITIONS, WAVELENGTH, chebyshev_taper(COUNT, 25.0)
    )
    angles = np.radians([10.0, -30.0, 60.0])
    vectors = np.stack([steering_vector(a, POSITIONS, WAVELENGTH) for a in angles])
    sigma, amplitude = 0.1, 0.05
    draws = 200000
    errors = (1 + amplitude * rng.standard_normal((draws, COUNT))) * np.exp(
        1j * sigma * rng.standard_normal((draws, COUNT))
    )
    measured = np.mean(np.abs((errors * weights) @ vectors.T) ** 2, axis=0)
    expected = expected_power(
        factor(angles, POSITIONS, weights, WAVELENGTH),
        weights,
        mean_phase_factor("normal", sigma),
        1 + amplitude**2,
    )
    assert measured == pytest.approx(expected, rel=2e-2)


def test_the_dipole_element_is_the_half_wave_pattern_along_the_axis():
    assert dipole_element(0.0) == pytest.approx(1.0)
    assert dipole_element(0.5 * np.pi) == pytest.approx(0.0, abs=1e-12)
    psi = np.radians(40.0)
    assert dipole_element(psi) == pytest.approx(
        np.cos(0.5 * np.pi * np.sin(psi)) / np.cos(psi)
    )
