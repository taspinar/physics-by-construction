"""The damped wave of the heat equation with a periodic surface temperature
(the model of "Soil temperature measurements lab", thermodynamics 10)."""

import numpy as np
import pytest

from pbc.data.reference import dwd_soil
from pbc.thermodynamics import periodic_conduction as model

OMEGA = 2 * np.pi / 86400.0


def test_the_damping_depth_scales_with_the_root_of_the_period():
    alpha = 1.1e-6
    d_day = model.damping_depth(alpha, OMEGA)
    assert d_day == pytest.approx(np.sqrt(2 * alpha * 86400 / (2 * np.pi)))
    assert model.damping_depth(alpha, OMEGA / 4) == pytest.approx(2 * d_day)
    assert model.diffusivity_from_slope(1 / d_day, OMEGA) == pytest.approx(alpha)


def test_the_damped_wave_solves_the_heat_equation():
    # Central differences of the formula: dT/dt = alpha d2T/dz2 at interior
    # points, and the surface follows the cosine it is driven by.
    alpha, mean, amplitude, phase = 1.1e-6, 15.0, 6.0, 0.3
    z = np.linspace(0.02, 0.5, 25)
    t, dt, dz = 3.7e4, 1.0, 1e-4

    def temperature(zz, tt):
        return model.periodic_temperature(zz, tt, mean, amplitude, phase, OMEGA, alpha)

    dtdt = (temperature(z, t + dt) - temperature(z, t - dt)) / (2 * dt)
    d2z = (temperature(z + dz, t) - 2 * temperature(z, t) + temperature(z - dz, t)) / (
        dz**2
    )
    np.testing.assert_allclose(dtdt, alpha * d2z, atol=1e-8, rtol=1e-4)
    times = np.linspace(0, 86400, 7)
    np.testing.assert_allclose(
        temperature(0.0, times), mean + amplitude * np.cos(OMEGA * times - phase)
    )


def test_the_formula_is_the_reference_modules():
    z, t = np.array([0.05, 0.3, 1.0]), np.linspace(0, 1e7, 9)[:, None]
    np.testing.assert_allclose(
        model.periodic_temperature(z, t, 9.0, 12.0, 0.4, dwd_soil.OMEGA_YEAR, 1.07e-6),
        dwd_soil.damped_wave(z, t, 9.0, 12.0, 0.4, dwd_soil.OMEGA_YEAR, 1.07e-6),
        rtol=1e-14,
    )


def test_the_harmonic_fit_returns_amplitude_and_lag():
    t = np.linspace(0, 86400, 24, endpoint=False)
    c = model.harmonic_of(t, 3.0 + 2.5 * np.cos(OMEGA * t - 0.7), OMEGA)
    assert abs(c) == pytest.approx(2.5)
    assert -np.angle(c) == pytest.approx(0.7)


def test_the_explicit_scheme_settles_into_the_damped_wave():
    alpha = 1.1e-6
    depths = np.array([0.05, 0.10, 0.20, 0.50])
    amplitude, lag = model.periodic_ftcs(
        alpha, OMEGA, depths, dz=0.01, r=0.25, bottom=1.2, periods=8
    )
    d = model.damping_depth(alpha, OMEGA)
    np.testing.assert_allclose(amplitude, np.exp(-depths / d), rtol=1e-3)
    np.testing.assert_allclose(lag, depths / d, atol=1e-3)
    # Too few periods: the start of the forcing has not died out at depth.
    early, _ = model.periodic_ftcs(
        alpha, OMEGA, depths, dz=0.01, r=0.25, bottom=1.2, periods=1
    )
    assert abs(early[-1] / np.exp(-depths[-1] / d) - 1) > 1e-2
