"""Two-ports and the lumped attenuator (lab EM7, pbc.electromagnetism.two_port):
the matched pad against its design, the line as a pure delay, the energy
balance and passivity, and the Smith-chart mappings."""

import numpy as np
import pytest

from pbc.electromagnetism.two_port import (
    REFERENCE_IMPEDANCE,
    TeeAttenuator,
    absorbed_fraction,
    amplitude_db,
    largest_singular_value,
    matched_tee,
    normalised_impedance,
    power_db,
    power_fraction,
    reflection,
    symmetric_s,
)

FREQUENCY = np.linspace(1e9, 200e9, 50)


@pytest.mark.parametrize("loss", [3.0, 6.0, 10.0, 20.0])
def test_the_matched_tee_reflects_nothing_and_passes_its_loss(loss):
    series, shunt = matched_tee(loss)
    s = TeeAttenuator(series, shunt).s(FREQUENCY)
    np.testing.assert_allclose(np.abs(s[:, 0, 0]), 0.0, atol=1e-14)
    np.testing.assert_allclose(amplitude_db(s[:, 1, 0]), -loss, atol=1e-12)


def test_the_matched_tee_is_the_textbook_three_db_pad():
    # The 3 dB T pad in 50 ohm: 8.55 ohm arms and a 141.9 ohm shunt.
    series, shunt = matched_tee(3.0)
    assert series == pytest.approx(8.55, abs=0.005)
    assert shunt == pytest.approx(141.9, abs=0.05)
    with pytest.raises(ValueError):
        matched_tee(0.0)


def test_the_input_impedance_of_a_terminated_tee_is_its_reflection():
    # Port 2 terminated in Z0: Z_in = R + R_shunt || (R + Z0).
    r, shunt = 14.0, 146.0
    s = TeeAttenuator(r, shunt).s([1e9])
    z_in = r + 1 / (1 / shunt + 1 / (r + REFERENCE_IMPEDANCE))
    assert s[0, 0, 0] == pytest.approx(reflection(z_in / REFERENCE_IMPEDANCE))


def test_a_matched_line_only_delays_the_wave():
    delay = 1e-12
    plain = TeeAttenuator(14.0, 146.0, 2e-11).s(FREQUENCY)
    delayed = TeeAttenuator(14.0, 146.0, 2e-11, delay).s(FREQUENCY)
    np.testing.assert_allclose(np.abs(delayed), np.abs(plain), rtol=1e-13)
    turn = np.angle(delayed[:, 1, 0] / plain[:, 1, 0])
    np.testing.assert_allclose(
        turn, np.angle(np.exp(-2j * np.pi * FREQUENCY * delay)), atol=1e-12
    )


def test_the_tee_is_reciprocal_and_symmetric():
    s = TeeAttenuator(10.0, 80.0, 3e-11, 2e-12).s(FREQUENCY)
    np.testing.assert_array_equal(s[:, 0, 1], s[:, 1, 0])
    np.testing.assert_array_equal(s[:, 0, 0], s[:, 1, 1])


def test_a_lossless_two_port_absorbs_nothing():
    # A series reactance alone: Z11 = Z21 + jX with the shunt arm open is not
    # finite, so use the S of a pure series inductor directly.
    x = 1j * 2 * np.pi * FREQUENCY * 1e-10
    s11 = x / (x + 2 * REFERENCE_IMPEDANCE)
    s21 = 2 * REFERENCE_IMPEDANCE / (x + 2 * REFERENCE_IMPEDANCE)
    s = np.stack([[s11, s21], [s21, s11]]).transpose(2, 0, 1)
    np.testing.assert_allclose(absorbed_fraction(s), 0.0, atol=1e-14)
    np.testing.assert_allclose(largest_singular_value(s), 1.0, atol=1e-14)


def test_a_resistive_pad_absorbs_a_positive_fraction():
    s = TeeAttenuator(*matched_tee(3.0)).s(FREQUENCY)
    absorbed = absorbed_fraction(s)
    assert absorbed.shape == (FREQUENCY.size, 2)
    np.testing.assert_allclose(absorbed, 1 - 10 ** (-3.0 / 10), atol=1e-12)
    assert np.all(largest_singular_value(s) < 1)


def test_symmetric_s_of_a_through_and_of_a_load():
    # A through connection: Z11 = Z21 -> infinity; a large shunt gives S21 -> 1.
    s11, s21 = symmetric_s(1e9, 1e9)
    assert abs(s11) < 1e-7 and s21 == pytest.approx(1.0, abs=1e-7)
    # A shunt of Z0 / 2 straight across the line: S11 = -1/2, S21 = 1/2.
    s11, s21 = symmetric_s(REFERENCE_IMPEDANCE / 2, REFERENCE_IMPEDANCE / 2)
    assert s11 == pytest.approx(-0.5) and s21 == pytest.approx(0.5)


def test_normalised_impedance_and_reflection_invert():
    z = np.array([0.2 + 0.5j, 1.0, 3.0 - 2.0j, 0.0])
    np.testing.assert_allclose(normalised_impedance(reflection(z)), z, atol=1e-14)
    assert reflection(1.0) == 0  # matched
    assert reflection(0.0) == -1  # short


def test_power_and_amplitude_decibels_are_the_same_number():
    s = np.array([0.5, 0.641, 0.1 + 0.2j])
    np.testing.assert_allclose(amplitude_db(s), power_db(power_fraction(s)))
    assert power_fraction(1 / np.sqrt(2)) == pytest.approx(0.5)
    assert power_db(0.5) == pytest.approx(-3.0103, abs=1e-4)
