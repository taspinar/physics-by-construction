"""Linear water waves (lesson W8): the dispersion relation, its limits, the
group speed, the phase along a bed, and linear propagation, each against a
closed form or an independent computation, with a stated tolerance."""

import numpy as np
import pytest

from pbc.waves.water import (
    G,
    accumulated_phase,
    group_speed,
    group_travel_time,
    phase_speed,
    propagate,
    shallow_wavenumber,
    wavenumber,
)

OMEGA = 2 * np.pi / 1.5


@pytest.mark.parametrize("depth", [1e-4, 0.01, 0.147, 0.3, 3.0, 300.0])
def test_the_wavenumber_solves_the_dispersion_relation_to_round_off(depth):
    k = wavenumber(OMEGA, depth)
    assert G * k * np.tanh(k * depth) == pytest.approx(OMEGA**2, rel=1e-13)


def test_the_wavenumber_takes_its_long_and_short_wave_limits():
    # kh = 0.003: tanh(kh) = kh (1 - (kh)^2 / 3), so k is the long-wave one to
    # about (kh)^2 / 6 relative.
    shallow = 1e-5
    assert wavenumber(OMEGA, shallow) == pytest.approx(
        shallow_wavenumber(OMEGA, shallow), rel=1e-5
    )
    # kh = 50: tanh(kh) = 1 to round-off.
    deep = 50 * G / OMEGA**2
    assert wavenumber(OMEGA, deep) == pytest.approx(OMEGA**2 / G, rel=1e-14)


def test_the_wavenumber_works_on_arrays_and_refuses_a_dry_bed():
    depths = np.array([0.1, 0.2, 0.3])
    k = wavenumber(OMEGA, depths)
    assert k.shape == (3,)
    assert np.all(np.diff(k) < 0)  # deeper water, longer wave
    with pytest.raises(ValueError):
        wavenumber(OMEGA, 0.0)


@pytest.mark.parametrize("depth", [0.05, 0.3, 2.0])
def test_the_group_speed_is_the_derivative_of_the_dispersion_relation(depth):
    # Central difference of omega(k) = sqrt(g k tanh(k h)), independent of the
    # closed form; step 1e-5 relative, so the difference is good to ~1e-9.
    k = float(wavenumber(OMEGA, depth))
    step = 1e-5 * k

    def omega(kk):
        return np.sqrt(G * kk * np.tanh(kk * depth))

    numerical = (omega(k + step) - omega(k - step)) / (2 * step)
    assert group_speed(OMEGA, depth) == pytest.approx(numerical, rel=1e-8)


def test_group_and_phase_speed_order_and_their_shallow_limit():
    assert group_speed(OMEGA, 0.3) < phase_speed(OMEGA, 0.3) < np.sqrt(G * 0.3)
    tiny = 1e-6
    assert group_speed(OMEGA, tiny) == pytest.approx(np.sqrt(G * tiny), rel=1e-5)


def test_the_phase_along_a_flat_bed_is_k_times_the_distance():
    x = np.array([1.0, 2.5, 7.0])

    def flat(s):
        return np.full_like(s, 0.3)

    phase = accumulated_phase(x, flat, OMEGA, start=1.0)
    k = float(wavenumber(OMEGA, 0.3))
    np.testing.assert_allclose(phase, k * (x - 1.0), rtol=1e-12, atol=1e-12)
    long_wave = accumulated_phase(x, flat, OMEGA, start=1.0, dispersive=False)
    np.testing.assert_allclose(long_wave, OMEGA / np.sqrt(G * 0.3) * (x - 1.0))
    time = group_travel_time(x, flat, OMEGA, start=1.0)
    np.testing.assert_allclose(time, (x - 1.0) / group_speed(OMEGA, 0.3))


def test_the_phase_over_a_linear_slope_matches_the_integral_by_quadrature():
    from scipy.integrate import quad

    def slope(s):
        return 0.3 - 0.02 * np.asarray(s)

    phase = accumulated_phase(np.array([5.0]), slope, OMEGA, start=0.0)[0]
    exact, _ = quad(lambda s: float(wavenumber(OMEGA, slope(s))), 0.0, 5.0)
    assert phase == pytest.approx(exact, rel=1e-8)


def test_propagation_moves_a_monochromatic_wave_by_k_times_the_distance():
    # Six whole periods sampled at 150 Hz: the discrete transform holds the
    # wave exactly, so the carried record is the closed form to round-off.
    t = np.arange(1350) / 150.0
    eta = 0.01 * np.cos(OMEGA * t) + 0.002
    distance = 1.778
    k = float(wavenumber(OMEGA, 0.3))
    carried = propagate(t, eta, distance, 0.3)
    np.testing.assert_allclose(
        carried, 0.01 * np.cos(OMEGA * t - k * distance) + 0.002, atol=1e-14
    )
    delayed = propagate(t, eta, distance, 0.3, dispersive=False)
    expected = 0.01 * np.cos(OMEGA * (t - distance / np.sqrt(G * 0.3))) + 0.002
    np.testing.assert_allclose(delayed, expected, atol=1e-14)
