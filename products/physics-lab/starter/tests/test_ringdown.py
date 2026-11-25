"""The provided tests of the ring-down fit (SPECIFICATION.md). They are not
yours to change. Each compares the fit with the closed-form step response of
a circuit that the fit never sees."""

import math

import numpy as np
import pytest
from my_lab.ringdown import RingdownFit, fit_ringdown

from pbc.electromagnetism.circuits import SeriesRLC, step_response
from pbc.instruments.simulated import BENCH_CIRCUIT

STEP_V = 1.0
SAMPLES = 2_000
DURATION_S = 2e-3


def truth(circuit: SeriesRLC) -> tuple[float, float]:
    """The circuit's f0, Hz, and Q."""
    return circuit.natural_frequency / (2 * math.pi), circuit.quality_factor


def record(
    circuit: SeriesRLC = BENCH_CIRCUIT,
    *,
    step_v: float = STEP_V,
    noise_v: float = 0.0,
    seed: int = 0,
    start_s: float = 0.0,
    offset_v: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """A sampled ring-down of ``circuit`` with Gaussian noise."""
    t = start_s + np.linspace(0.0, DURATION_S, SAMPLES, endpoint=False)
    v = step_response(circuit, step_v, t) + offset_v
    if noise_v:
        v = v + np.random.default_rng(seed).normal(0.0, noise_v, SAMPLES)
    return t, v


def test_without_noise_the_fit_recovers_f0_and_q():
    f0, q = truth(BENCH_CIRCUIT)
    fit = fit_ringdown(*record())
    assert isinstance(fit, RingdownFit)
    assert fit.f0_hz == pytest.approx(f0, rel=1e-3)
    assert fit.q == pytest.approx(q, rel=5e-3)
    alpha = BENCH_CIRCUIT.damping_rate
    assert fit.decay_rate == pytest.approx(alpha, rel=5e-3)
    damped = math.sqrt(BENCH_CIRCUIT.natural_frequency**2 - alpha**2) / (2 * math.pi)
    assert fit.damped_frequency_hz == pytest.approx(damped, rel=1e-3)


def test_another_circuit_gives_another_answer():
    other = SeriesRLC(resistance=50.0, inductance=4.7e-3, capacitance=220e-9)
    f0, q = truth(other)
    fit = fit_ringdown(*record(other))
    assert fit.f0_hz == pytest.approx(f0, rel=1e-3)
    assert fit.q == pytest.approx(q, rel=5e-3)


def test_the_step_size_the_offset_and_the_start_time_are_not_assumed():
    f0, q = truth(BENCH_CIRCUIT)
    fit = fit_ringdown(*record(step_v=0.4, offset_v=0.15, start_s=3.3e-5))
    assert fit.f0_hz == pytest.approx(f0, rel=1e-3)
    assert fit.q == pytest.approx(q, rel=5e-3)


def test_with_noise_the_values_lie_within_a_few_standard_errors():
    f0, q = truth(BENCH_CIRCUIT)
    fit = fit_ringdown(*record(noise_v=0.01, seed=7))
    for se in (fit.decay_rate_se, fit.damped_frequency_se, fit.f0_se, fit.q_se):
        assert math.isfinite(se) and se > 0
    assert abs(fit.f0_hz - f0) < 4 * fit.f0_se
    assert abs(fit.q - q) < 4 * fit.q_se
    assert fit.f0_se < 0.01 * f0
    assert fit.q_se < 0.05 * q


def test_the_standard_errors_are_calibrated():
    """Over 40 noisy records the errors in units of the stated standard
    error behave like a standard normal variable: about 95 % under 2, and a
    root mean square near 1. A standard error that is a guess fails here."""
    f0, q = truth(BENCH_CIRCUIT)
    z_f0, z_q = [], []
    for seed in range(40):
        fit = fit_ringdown(*record(noise_v=0.01, seed=seed))
        z_f0.append((fit.f0_hz - f0) / fit.f0_se)
        z_q.append((fit.q - q) / fit.q_se)
    for z in (np.array(z_f0), np.array(z_q)):
        assert np.mean(np.abs(z) < 2) >= 0.85
        assert 0.6 < math.sqrt(np.mean(z**2)) < 1.5


def test_less_noise_gives_smaller_standard_errors():
    noisy = fit_ringdown(*record(noise_v=0.02, seed=3))
    quiet = fit_ringdown(*record(noise_v=0.002, seed=3))
    assert quiet.f0_se < 0.25 * noisy.f0_se
    assert quiet.q_se < 0.25 * noisy.q_se


def test_an_overdamped_record_is_refused():
    overdamped = SeriesRLC(resistance=2_000.0, inductance=10e-3, capacitance=100e-9)
    assert overdamped.regime == "overdamped"
    with pytest.raises(ValueError):
        fit_ringdown(*record(overdamped, noise_v=0.001, seed=1))


def test_a_flat_record_is_refused():
    t = np.linspace(0.0, DURATION_S, SAMPLES, endpoint=False)
    v = 0.5 + np.random.default_rng(2).normal(0.0, 0.01, SAMPLES)
    with pytest.raises(ValueError):
        fit_ringdown(t, v)


@pytest.mark.parametrize(
    "change",
    ["lengths", "few", "nan", "order"],
)
def test_invalid_records_are_refused(change):
    t, v = record()
    if change == "lengths":
        v = v[:-1]
    elif change == "few":
        t, v = t[:15], v[:15]
    elif change == "nan":
        v = v.copy()
        v[10] = math.nan
    else:
        t = t[::-1]
    with pytest.raises(ValueError):
        fit_ringdown(t, v)
