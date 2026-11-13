"""The damped-pendulum model of the pendulum lab: the correction to small
amplitude inverts the exact period, the averaged envelope solves its
equation and follows a simulation of the full equation of motion, and the
effective length inverts the small-angle period."""

import numpy as np
import pytest

from pbc.mechanics.damped_pendulum import (
    amplitude_envelope,
    damped_pendulum,
    effective_length,
    quadratic_envelope_constant,
    small_amplitude_period,
)
from pbc.mechanics.dynamics import State, simulate
from pbc.mechanics.integrators import rk4_step
from pbc.mechanics.pendulum import pendulum_period, small_angle_period

G = 9.799


@pytest.mark.parametrize("amplitude", [0.0, 0.1, 0.5, 1.0, 2.0, 3.0])
def test_the_correction_inverts_the_exact_period(amplitude):
    period = pendulum_period(0.25, amplitude, G)
    assert small_amplitude_period(period, amplitude) == pytest.approx(
        small_angle_period(0.25, G), rel=1e-12
    )


def test_the_correction_follows_its_series_at_small_amplitude():
    # T / T0 = 1 + A^2/16 + 11 A^4/3072 + ...
    a = np.array([0.05, 0.1, 0.2])
    ratio = 1 / small_amplitude_period(1.0, a)
    np.testing.assert_allclose(ratio, 1 + a**2 / 16 + 11 * a**4 / 3072, rtol=2e-7)


def test_the_envelope_solves_its_equation():
    t = np.linspace(0, 60, 6001)
    a1, gamma, kappa = 0.9, 0.004, 0.007
    a = amplitude_envelope(t, a1, gamma, kappa)
    assert a[0] == pytest.approx(a1)
    rate = np.gradient(a, t)
    np.testing.assert_allclose(rate[1:-1], (-gamma * a - kappa * a**2)[1:-1], rtol=1e-5)


def test_the_envelope_has_the_limits_of_its_two_laws():
    t = np.linspace(0, 100, 11)
    np.testing.assert_allclose(
        amplitude_envelope(t, 0.5, 0.02), 0.5 * np.exp(-0.02 * t), rtol=1e-14
    )
    np.testing.assert_allclose(
        amplitude_envelope(t, 0.5, 0.0, 0.01), 0.5 / (1 + 0.01 * 0.5 * t), rtol=1e-14
    )
    # Continuous as gamma goes to zero.
    np.testing.assert_allclose(
        amplitude_envelope(t, 0.5, 1e-12, 0.01),
        amplitude_envelope(t, 0.5, 0.0, 0.01),
        rtol=1e-9,
    )


def _peaks(t0: float, gamma: float, beta: float, release: float, seconds: float):
    """Times and sizes of the turning points of a simulated swing."""
    dt = t0 / 400
    trajectory = simulate(
        State(0.0, [release], [0.0]),
        damped_pendulum(t0, gamma, beta),
        dt,
        int(seconds / dt),
        step=rk4_step,
    )
    theta = trajectory.x[:, 0]
    k = np.flatnonzero(
        (np.abs(theta[1:-1]) >= np.abs(theta[:-2]))
        & (np.abs(theta[1:-1]) >= np.abs(theta[2:]))
    )
    return trajectory.t[k + 1], np.abs(theta[k + 1]), trajectory


def test_without_damping_the_swing_keeps_its_energy_and_its_exact_period():
    t0, release = 1.0, 1.0
    times, sizes, trajectory = _peaks(t0, 0.0, 0.0, release, 10.0)
    # The turning points are read on the time grid, which misses the true
    # extreme by up to (pi/400)^2/2 of it; the energy below is the strict test.
    np.testing.assert_allclose(sizes, release, rtol=4e-5)
    period = 2 * np.mean(np.diff(times))
    expected = pendulum_period(effective_length(t0, G), release, G)
    assert period == pytest.approx(expected, rel=2e-3)  # turning points to dt
    w0 = 2 * np.pi / t0
    energy = 0.5 * trajectory.v[:, 0] ** 2 + w0**2 * (1 - np.cos(trajectory.x[:, 0]))
    assert np.ptp(energy) < 1e-7 * energy[0]


def test_linear_damping_decays_exponentially_at_gamma():
    times, sizes, _ = _peaks(1.0, 0.05, 0.0, 0.05, 30.0)
    np.testing.assert_allclose(sizes, 0.05 * np.exp(-0.05 * times), rtol=2e-3)


def test_the_averaged_envelope_follows_the_quadratic_damping_of_a_small_swing():
    # At a small amplitude the averaging over a cosine holds, and the
    # turning points follow the envelope with kappa = 4 beta w0 / (3 pi).
    t0, gamma, beta, release = 1.0, 0.01, 0.2, 0.15
    kappa = quadratic_envelope_constant(beta, t0)
    times, sizes, _ = _peaks(t0, gamma, beta, release, 40.0)
    envelope = amplitude_envelope(times, release, gamma, kappa)
    assert sizes[-1] < 0.6 * release  # the quadratic part matters here
    np.testing.assert_allclose(sizes, envelope, rtol=0.01)


def test_the_effective_length_inverts_the_small_angle_period():
    for length in (0.236, 0.607):
        assert effective_length(small_angle_period(length, G), G) == pytest.approx(
            length, rel=1e-14
        )


def test_the_model_refuses_impossible_constants():
    with pytest.raises(ValueError):
        damped_pendulum(0.0, 0.0, 0.0)
    with pytest.raises(ValueError):
        damped_pendulum(1.0, -0.1, 0.0)
    with pytest.raises(ValueError):
        damped_pendulum(1.0, 0.0, -0.1)
