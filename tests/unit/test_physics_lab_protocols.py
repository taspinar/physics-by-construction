"""The three protocols of the Autonomous Physics Lab, their quality gate,
their intervals, and their independent checks (F145, Issue #614, criteria 2
and 3): the frequency response, the ring-down after a step, and the
amplitude-dependent response of the LED pair are distinct in physics, each
has an independent numerical check, and an invalid capture is detected and
never fitted."""

import dataclasses
import math

import numpy as np
import pytest

from pbc.electromagnetism.circuits import SeriesRLC
from pbc.electromagnetism.led_pair import LEDPair, harmonics
from pbc.instruments import SINE, SQUARE, Capture, Instrument
from pbc.instruments import analog_discovery as ad
from pbc.instruments.channels import ChannelChain, Dropouts, ImperfectChannels
from pbc.instruments.simulated import (
    BENCH_CIRCUIT,
    LED_BENCH_PAIR,
    SimulatedLEDBench,
    SimulatedRLCBench,
)
from pbc.products.physics_lab import nonlinear, resonance, transient
from pbc.products.physics_lab.estimates import (
    COVERAGE,
    Estimate,
    agreement,
    combine,
)
from pbc.products.physics_lab.protocol import bench_envelope, live_envelope
from pbc.products.physics_lab.quality import (
    LIVE_RAILS,
    Rails,
    gate,
)
from pbc.products.physics_lab.ringdown import fit_ringdown, model

# A circuit like F140's measured one (L 0.861 mH, C 14.55 nF, R with the
# coil's loss about 163 ohm), simulated: f0 near 45 kHz, Q near 1.5.
PILOT_LIKE = SeriesRLC(resistance=163.0, inductance=0.861e-3, capacitance=14.55e-9)
PILOT_TRANSIENT = transient.TransientSettings(1.0, 1_000.0, 10_000_000.0, 200_000.0)


def lab(envelope):
    return dataclasses.replace(envelope, waveforms=(SINE, SQUARE))


def rlc(circuit=BENCH_CIRCUIT, seed=0, envelope=None, wrap=None):
    driver = SimulatedRLCBench(circuit=circuit, seed=seed)
    if wrap is not None:
        driver = wrap(driver)
    return Instrument(driver, lab(envelope or bench_envelope()))


# -- the ring-down fit -----------------------------------------------------------------


def test_the_ringdown_fit_recovers_a_known_decay_with_honest_errors():
    rng = np.random.default_rng(1)
    t = np.arange(4_000) / 1e6
    alpha, omega_d = 4_000.0, 2 * math.pi * 6_000.0
    v = model(t, 1.0, -0.8, 0.3, alpha, omega_d) + rng.normal(0, 0.002, len(t))
    fit = fit_ringdown(t + 0.37, v)  # a shifted time origin changes no rate
    omega_0 = math.hypot(omega_d, alpha)
    assert fit.decay_rate == pytest.approx(alpha, abs=4 * fit.decay_rate_se)
    assert fit.f0_hz == pytest.approx(omega_0 / (2 * math.pi), abs=4 * fit.f0_se)
    assert fit.q == pytest.approx(omega_0 / (2 * alpha), abs=4 * fit.q_se)
    assert 0 < fit.q_se < 0.01 * fit.q


@pytest.mark.parametrize(
    ("t", "v", "message"),
    [
        (np.arange(10.0), np.zeros(10), "16 samples"),
        (np.arange(100.0) / 1e5, np.full(100, np.nan), "finite"),
        (np.arange(100.0)[::-1], np.zeros(100), "increase"),
        (
            np.arange(2_000) / 1e6,
            1
            - np.exp(-np.arange(2_000) / 200.0)
            + np.random.default_rng(0).normal(0, 0.002, 2_000),
            "oscillation|decay|fitted|determine",
        ),
    ],
    ids=["short", "not-finite", "decreasing", "overdamped"],
)
def test_a_record_that_is_not_a_ringdown_is_refused(t, v, message):
    with pytest.raises(ValueError, match=message):
        fit_ringdown(t, v)


# -- the transient protocol ------------------------------------------------------------


@pytest.mark.parametrize(
    ("circuit", "settings", "envelope"),
    [
        (BENCH_CIRCUIT, transient.TransientSettings(), bench_envelope()),
        (PILOT_LIKE, PILOT_TRANSIENT, live_envelope(99.0)),
    ],
    ids=["bench", "pilot-like"],
)
def test_the_ringdown_recovers_f0_and_q_of_the_closed_form(circuit, settings, envelope):
    transient.check_settings(settings, circuit)
    ringdowns = [
        transient.measure_ringdown(rlc(circuit, seed, envelope), settings)
        for seed in range(3)
    ]
    assert all(r.valid and r.verdict.valid for r in ringdowns)
    result = transient.combine_ringdowns(ringdowns)
    check = transient.check_against_closed_form(result, circuit)
    assert check is not None and check.correct, check
    assert result.f0_hz.consistent and result.q.consistent


def test_a_square_wave_too_fast_for_the_circuit_is_refused():
    with pytest.raises(ValueError, match="decay times"):
        transient.check_settings(
            transient.TransientSettings(square_hz=400.0), BENCH_CIRCUIT
        )


def test_the_window_starts_after_a_rising_edge_and_ends_at_the_next_falling_one():
    source = np.array([0.0] * 10 + [1.0] * 50 + [0.0] * 50 + [1.0] * 40)
    assert transient.ringdown_window(source, 1.0, 1_000.0, 10.0) == (12, 60)
    assert transient.ringdown_window(np.ones(30), 1.0, 1_000.0, 10.0) is None


def test_a_clipped_ringdown_is_detected_recorded_and_never_fitted():
    """The capacitor overshoots the step (Q about 3): a response converter
    whose rails are at 1.5 V clips the peak, and the gate refuses it."""
    chains = {"response": ChannelChain(full_scale_v=1.5)}
    instrument = rlc(wrap=lambda d: ImperfectChannels(d, chains))
    ringdown = transient.analyse_ringdown(
        _acquire_square(instrument),
        transient.TransientSettings(),
        Rails(response_v=1.5),
    )
    assert not ringdown.verdict.valid and ringdown.fit is None
    assert "response clipped" in ringdown.note


def _acquire_square(instrument):
    s = transient.TransientSettings()
    instrument.excite(s.amplitude_v, s.square_hz, SQUARE)
    return instrument.acquire(s.sample_rate_hz, s.samples)


# -- the frequency response with intervals ---------------------------------------------


def _sweep(circuit, low, high, envelope, seed=5, wrap=None):
    instrument = rlc(circuit, seed, envelope, wrap)
    return [
        resonance.measure_point(instrument, float(f), 1.0)
        for f in np.geomspace(low, high, 13)
    ]


@pytest.mark.parametrize(
    ("circuit", "low", "high", "envelope"),
    [
        (BENCH_CIRCUIT, 1e3, 25e3, bench_envelope()),
        (PILOT_LIKE, 5e3, 2e5, live_envelope(99.0)),
    ],
    ids=["bench", "pilot-like"],
)
def test_the_resonance_fit_covers_the_closed_form(circuit, low, high, envelope):
    points = [m.point for m in _sweep(circuit, low, high, envelope)]
    fit = resonance.fit_resonance(points)
    f0 = circuit.natural_frequency / (2 * math.pi)
    assert abs(fit.f0_hz.value - f0) <= 3 * fit.f0_hz.se
    assert abs(fit.q.value - circuit.quality_factor) <= 3 * fit.q.se
    assert fit.k.value == pytest.approx(1.0, abs=3 * fit.k.se)
    assert resonance.fit_resonance(points[:3]) is None


def test_a_point_with_lost_samples_is_invalid_and_kept_out_of_the_fit():
    lossy = lambda d: ImperfectChannels(d, {}, Dropouts(bursts=3, length=20, seed=4))  # noqa: E731
    measured = _sweep(BENCH_CIRCUIT, 1e3, 25e3, bench_envelope(), wrap=lossy)
    assert all(not m.valid for m in measured)
    assert all("lost" in m.note for m in measured)


# -- the consistency of two protocols --------------------------------------------------


def test_the_two_protocols_agree_on_one_circuit_within_their_intervals():
    """The independent check of the live and recorded routes, shown on a
    simulated circuit: the frequency response and the ring-down give f0 and
    Q that agree within COVERAGE combined standard errors."""
    fit = resonance.fit_resonance(
        [m.point for m in _sweep(PILOT_LIKE, 5e3, 2e5, live_envelope(99.0))]
    )
    result = transient.combine_ringdowns(
        [
            transient.measure_ringdown(
                rlc(PILOT_LIKE, s, live_envelope(99.0)), PILOT_TRANSIENT
            )
            for s in range(3)
        ]
    )
    for name, a, b in (
        ("f0", fit.f0_hz, result.f0_hz.estimate),
        ("Q", fit.q, result.q.estimate),
    ):
        check = agreement(name, "frequency response", a, "transient", b)
        assert check.agree, check


def test_agreement_combines_the_errors_and_says_when_it_fails():
    a, b = Estimate(100.0, 3.0), Estimate(108.0, 4.0)
    assert agreement("x", "a", a, "b", b).combined_se == pytest.approx(5.0)
    assert agreement("x", "a", a, "b", b).agree is (COVERAGE * 5.0 >= 8.0)
    assert not agreement("x", "a", a, "b", Estimate(120.0, 4.0)).agree


def test_repetitions_whose_spread_the_errors_do_not_explain_widen_the_error():
    agreeing = combine([Estimate(10.0, 1.0), Estimate(10.5, 1.0), Estimate(9.8, 1.0)])
    assert agreeing.consistent and agreeing.estimate.se == pytest.approx(
        1 / math.sqrt(3)
    )
    spread = combine([Estimate(10.0, 0.1), Estimate(12.0, 0.1), Estimate(8.0, 0.1)])
    assert not spread.consistent
    assert spread.estimate.se == pytest.approx(spread.birge * 0.1 / math.sqrt(3))
    with pytest.raises(ValueError):
        combine([])


# -- the quality gate ------------------------------------------------------------------


def test_the_live_rails_are_the_adapters_input_ranges():
    assert LIVE_RAILS.source_v == ad.SOURCE_RANGE_V / 2
    assert LIVE_RAILS.response_v == ad.RESPONSE_RANGE_V / 2


def test_a_source_probe_off_the_generator_is_detected():
    t = np.arange(513) / 64_000.0
    noise = np.random.default_rng(0).normal(0, 0.002, 513)
    capture = Capture(
        64_000.0, t, {"source": noise, "response": np.cos(2e3 * np.pi * t)}, {}
    )
    verdict = gate(capture, 1.0, 1_000.0)
    assert not verdict.valid
    assert "not on the generator" in verdict.reasons[0]


def test_a_rate_at_the_nyquist_limit_is_invalid():
    t = np.arange(64) / 2_000.0
    signal = np.cos(2 * np.pi * 1_000.0 * t + 0.3)
    capture = Capture(2_000.0, t, {"source": signal, "response": signal}, {})
    assert any("Nyquist" in r for r in gate(capture, 0.9, 1_000.0).reasons)


# -- the LED pair and the nonlinear protocol -------------------------------------------


def test_the_led_pair_shares_the_source_and_never_passes_more_than_v_over_r():
    pair = LEDPair(resistance=100.0, saturation_current=1e-17, ideality=2.0)
    vs = np.linspace(-2.0, 2.0, 401)
    v = pair.pair_voltage(vs)
    i = pair.current(v)
    assert np.allclose(v + pair.resistance * i, vs, atol=1e-12)
    assert np.all(np.abs(i) <= np.abs(vs) / pair.resistance + 1e-15)
    assert np.allclose(pair.pair_voltage(-vs), -v)
    assert pair.characteristic_voltage(pair.current(1.7)) == pytest.approx(1.7)
    # Odd symmetry: no second harmonic.
    found = harmonics(pair, 2.0, (1, 2, 3))
    assert found[2] < 1e-12 < found[3] < found[1]


def _amplitudes(seed=2, amplitudes=(0.2, 0.5, 1.0, 1.4, 1.6, 1.8, 2.0)):
    instrument = Instrument(SimulatedLEDBench(seed=seed), live_envelope(99.0))
    settings = nonlinear.NonlinearSettings()
    return [nonlinear.measure_amplitude(instrument, a, settings) for a in amplitudes]


def test_the_response_depends_on_the_amplitude():
    points = [m.point for m in _amplitudes()]
    low, high = points[0], points[-1]
    assert low.gain == pytest.approx(1.0, abs=3 * low.gain_se)
    assert low.h3 < 3 * low.h3_se + 1e-3
    assert high.gain < 0.95 and high.h3 > 0.03
    gains = [p.gain for p in points[2:]]
    assert gains == sorted(gains, reverse=True)


def test_the_characteristic_recovers_the_declared_leds():
    measured = _amplitudes()
    characteristic = nonlinear.fit_characteristic(measured, 100.0)
    check = nonlinear.check_against_model(characteristic, LED_BENCH_PAIR)
    assert check.correct, check


def test_the_held_out_prediction_agrees_with_every_other_amplitude():
    held = nonlinear.held_out_check(_amplitudes(), 100.0)
    assert held.fitted_on == 2.0
    assert len(held.agreements) == 6 and held.agree


class MixedPair(LEDPair):
    """Two LEDs of different colours in anti-parallel: the forward one of
    the pair conducts at a lower voltage than the reverse one."""

    def current(self, v):
        v = np.asarray(v, dtype=float)
        slope = self.slope_voltage
        return np.where(
            v >= 0, 1e-17 * np.expm1(v / slope), -1e-20 * np.expm1(-v / slope)
        )


def test_the_held_out_check_fails_a_pair_that_is_not_of_one_colour():
    """The check tests the model of the pair, a symmetric characteristic of
    the Shockley form: two colours break it, and the prediction from the
    largest amplitude misses the gains where one LED conducts and the other
    does not. (A wrong declared resistor does not: it rescales the fitted
    saturation current exactly, v_s = R i + v for any R and i = (v_s - v)/R,
    so the check cannot see it.)"""
    instrument = Instrument(
        SimulatedLEDBench(pair=MixedPair(), seed=2), live_envelope(99.0)
    )
    settings = nonlinear.NonlinearSettings()
    measured = [
        nonlinear.measure_amplitude(instrument, a, settings)
        for a in (0.2, 0.5, 1.0, 1.4, 1.6, 1.8, 2.0)
    ]
    held = nonlinear.held_out_check(measured, 100.0)
    assert not held.agree
    assert nonlinear.held_out_check(_amplitudes(), 150.0).agree


def test_a_clipped_amplitude_is_detected_and_not_used_for_the_characteristic():
    measured = _amplitudes(amplitudes=(1.0, 2.0))
    clipped = nonlinear.analyse_amplitude(
        measured[1].capture, 2.0, nonlinear.NonlinearSettings(), Rails(source_v=1.5)
    )
    assert not clipped.valid and "source clipped" in clipped.note
    assert nonlinear.fit_characteristic([clipped], 100.0) is None
