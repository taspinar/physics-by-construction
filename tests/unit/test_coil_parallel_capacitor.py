"""The coil in parallel with a capacitor (lab EM8,
pbc.electromagnetism.circuits): the impedance against the sum of the
admittances, the closed forms of the phase zero and the dynamic resistance
against a root search, and the search for the maximum of |Z|."""

import numpy as np
import pytest
from scipy.optimize import brentq

from pbc.electromagnetism.circuits import (
    CoilParallelCapacitor,
    SeriesRLC,
    impedance_peak,
)

R, L, C = 9.7, 5e-3, 2.2e-6


def test_the_impedance_is_the_inverse_of_the_summed_admittances():
    tank = CoilParallelCapacitor(R, L, C)
    omega = np.geomspace(1e2, 1e6, 50)
    admittance = 1 / (R + 1j * omega * L) + 1j * omega * C
    np.testing.assert_allclose(tank.impedance(omega), 1 / admittance, rtol=1e-13)


def test_the_limits_are_the_coil_at_low_and_the_capacitor_at_high_frequency():
    tank = CoilParallelCapacitor(R, L, C)
    assert tank.impedance(1e-3) == pytest.approx(R, rel=1e-6)
    omega = 1e8
    assert tank.impedance(omega) == pytest.approx(1 / (1j * omega * C), rel=1e-3)


def test_the_natural_frequency_and_q_are_those_of_the_series_circuit():
    tank, series = CoilParallelCapacitor(R, L, C), SeriesRLC(R, L, C)
    assert tank.natural_frequency == pytest.approx(series.natural_frequency)
    assert tank.quality_factor == pytest.approx(series.quality_factor)


@pytest.mark.parametrize("r", [1.0, 9.7, 30.0])
def test_the_phase_zero_and_the_dynamic_resistance_match_a_root_search(r):
    tank = CoilParallelCapacitor(r, L, C)
    omega0 = tank.natural_frequency
    root = brentq(lambda w: tank.impedance(w).imag, 0.3 * omega0, omega0, xtol=1e-12)
    assert tank.phase_zero_frequency == pytest.approx(root, rel=1e-10)
    z = tank.impedance(tank.phase_zero_frequency)
    assert z.real == pytest.approx(tank.dynamic_resistance, rel=1e-10)
    assert abs(z.imag) < 1e-8 * z.real


@pytest.mark.parametrize("r", [1.0, 9.7, 15.0])
def test_the_peak_of_z_lies_between_the_phase_zero_and_the_natural_frequency(r):
    tank = CoilParallelCapacitor(r, L, C)
    peak = impedance_peak(tank)
    assert tank.phase_zero_frequency < peak < tank.natural_frequency
    # A maximum: the neighbours on a fine grid are lower.
    step = 1e-4 * peak
    here = abs(tank.impedance(peak))
    assert abs(tank.impedance(peak - step)) < here
    assert abs(tank.impedance(peak + step)) < here


def test_a_common_scale_of_the_impedance_is_a_scale_of_r_and_l_over_c():
    # Why a calibration error common to every frequency is invisible to the
    # fit of the lab: Z(kR, kL, C/k) = k Z(R, L, C), with the same resonance
    # and quality factor.
    k = 1.07
    tank, scaled = (
        CoilParallelCapacitor(R, L, C),
        CoilParallelCapacitor(k * R, k * L, C / k),
    )
    omega = np.geomspace(1e2, 1e6, 50)
    np.testing.assert_allclose(
        scaled.impedance(omega), k * tank.impedance(omega), rtol=1e-13
    )
    assert scaled.natural_frequency == pytest.approx(tank.natural_frequency)
    assert scaled.quality_factor == pytest.approx(tank.quality_factor)


def test_a_circuit_without_a_phase_zero_says_so():
    tank = CoilParallelCapacitor(2 * np.sqrt(L / C), L, C)  # Q = 1/2
    with pytest.raises(ValueError):
        _ = tank.phase_zero_frequency


def test_impossible_circuits_are_refused():
    with pytest.raises(ValueError):
        CoilParallelCapacitor(-1.0, L, C)
    with pytest.raises(ValueError):
        CoilParallelCapacitor(1.0, L, 0.0)
