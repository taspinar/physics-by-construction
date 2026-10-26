"""The series RLC circuit (lesson EM5, pbc.electromagnetism.circuits): the
closed forms against the differential equation and its limits, the
simulation against the closed forms, and the reading of a steady phasor."""

import numpy as np
import pytest

from pbc.electromagnetism.circuits import (
    SeriesRLC,
    simulate,
    steady_phasor,
    step_response,
)

L, C = 10e-3, 100e-9


def test_the_circuit_quantities_are_the_textbook_ones():
    rlc = SeriesRLC(30.0, L, C)
    assert rlc.natural_frequency == pytest.approx(1 / np.sqrt(L * C))
    assert rlc.damping_rate == pytest.approx(30.0 / (2 * L))
    assert rlc.quality_factor == pytest.approx(rlc.natural_frequency * L / 30.0)
    assert rlc.critical_resistance == pytest.approx(2 * np.sqrt(L / C))


def test_the_regime_follows_the_resistance():
    critical = SeriesRLC(1.0, L, C).critical_resistance
    assert SeriesRLC(0.5 * critical, L, C).regime == "underdamped"
    assert SeriesRLC(critical, L, C).regime == "critical"
    assert SeriesRLC(2.0 * critical, L, C).regime == "overdamped"


def test_the_impedance_is_real_and_least_at_resonance():
    rlc = SeriesRLC(30.0, L, C)
    w0 = rlc.natural_frequency
    assert rlc.impedance(w0) == pytest.approx(30.0, abs=1e-9)
    assert rlc.impedance(0.5 * w0).imag < 0 < rlc.impedance(2 * w0).imag


@pytest.mark.parametrize("factor", [0.3, 1.0, 3.0])
def test_each_step_response_solves_the_circuit_equation(factor):
    """L C v'' + R C v' + v = V with v(0) = v'(0) = 0, checked by finite
    differences of the closed form."""
    rlc = SeriesRLC(factor * SeriesRLC(1.0, L, C).critical_resistance, L, C)
    h = 1e-8
    t = np.linspace(1e-5, 5e-4, 50)
    v = lambda s: step_response(rlc, 5.0, s)  # noqa: E731
    first = (v(t + h) - v(t - h)) / (2 * h)
    second = (v(t + h) - 2 * v(t) + v(t - h)) / h**2
    residual = L * C * second + rlc.resistance * C * first + v(t) - 5.0
    assert np.max(np.abs(residual)) < 1e-4 * 5.0
    assert v(np.array([0.0]))[0] == pytest.approx(0.0, abs=1e-12)
    # No current at the start: v rises as (V / LC) t^2 / 2, without a linear term.
    assert v(np.array([h]))[0] == pytest.approx(5.0 / (L * C) * h**2 / 2, rel=1e-3)
    assert v(np.array([1.0]))[0] == pytest.approx(5.0)


@pytest.mark.parametrize("factor", [0.2, 1.0, 4.0])
def test_the_simulation_follows_the_step_response(factor):
    rlc = SeriesRLC(factor * SeriesRLC(1.0, L, C).critical_resistance, L, C)
    t = np.linspace(0.0, 1e-3, 201)
    charge, current = simulate(rlc, lambda _t: 5.0, t)
    np.testing.assert_allclose(charge / C, step_response(rlc, 5.0, t), atol=1e-8)
    assert current[0] == 0.0


def test_a_lossless_circuit_keeps_its_energy():
    rlc = SeriesRLC(0.0, L, C)
    t = np.linspace(0.0, 2e-3, 101)
    charge, current = simulate(rlc, lambda _t: 0.0, t, charge=1e-6)
    energy = 0.5 * L * current**2 + 0.5 * charge**2 / C
    np.testing.assert_allclose(energy, energy[0], rtol=1e-9)


def test_the_steady_phasor_of_a_cosine_is_its_amplitude_and_phase():
    omega = 2 * np.pi * 50.0
    t = np.linspace(0.0, 3 / 50.0, 3 * 40 + 1)
    phasor = steady_phasor(2.0 * np.cos(omega * t + 0.7), t, omega)
    assert phasor == pytest.approx(2.0 * np.exp(0.7j), abs=1e-12)
    with pytest.raises(ValueError):
        steady_phasor(np.cos(omega * t[:50]), t[:50], omega)


def test_the_capacitor_voltage_lags_the_current_by_a_quarter_period():
    rlc = SeriesRLC(30.0, L, C)
    w = 0.8 * rlc.natural_frequency
    ratio = rlc.capacitor_phasor(5.0, w) / rlc.current_phasor(5.0, w)
    assert np.angle(ratio) == pytest.approx(-np.pi / 2)
    assert abs(ratio) == pytest.approx(1 / (w * C))


def test_impossible_circuits_are_refused():
    with pytest.raises(ValueError):
        SeriesRLC(-1.0, L, C)
    with pytest.raises(ValueError):
        SeriesRLC(1.0, 0.0, C)
