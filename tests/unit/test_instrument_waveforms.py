"""The square wave of the instrument contract (F145, Issue #614; the safety
boundary I34): the envelope and the instrument refuse a waveform that is not
permitted, or that the adapter does not declare, before any adapter call;
a sine reaches the adapters as before; the square wave steps between 0 V
and the amplitude on every adapter that declares it; and the current a
step drives through the declared series circuit stays within the bound the
envelope computes, amplitude over series resistance."""

import math

import numpy as np
import pytest

from pbc.electromagnetism.circuits import SeriesRLC
from pbc.instruments import (
    SINE,
    SQUARE,
    Envelope,
    Instrument,
    Limit,
    OutOfEnvelope,
    Refused,
)
from pbc.instruments.channels import ChannelChain, ImperfectChannels
from pbc.instruments.conformance import (
    FAILED,
    NOT_APPLICABLE,
    PASSED,
    CallLog,
    SquareSetting,
    check_waveforms,
)
from pbc.instruments.recorded import (
    Declaration,
    RecordedBench,
    RecordedCapture,
    RecordedSample,
    load_sample,
    record_sample,
    save_sample,
)
from pbc.instruments.simulated import SimulatedRLCBench, square_wave

SETTING = SquareSetting(
    amplitude_v=1.0, frequency_hz=200.0, sample_rate_hz=200_000.0, samples=1_500
)


def envelope(waveforms=(SINE, SQUARE), current=None, resistance=None):
    return Envelope(
        amplitude=Limit("excitation amplitude", "V", 0.01, 2.0),
        frequency=Limit("excitation frequency", "Hz", 100.0, 50_000.0),
        sample_rate=Limit("sample rate", "samples/s", 1_000.0, 5_000_000.0),
        samples=Limit("samples", "samples", 16, 16_384, integer=True),
        timeout_s=10.0,
        waveforms=waveforms,
        current=current,
        series_resistance_ohm=resistance,
    )


class SineOnly:
    """An adapter written before F145: no ``waveforms``, and a
    ``set_output`` that takes the amplitude and the frequency alone."""

    mode = "simulated"

    def __init__(self):
        self.bench = SimulatedRLCBench()

    def identity(self):
        return self.bench.identity()

    def set_output(self, amplitude_v, frequency_hz):
        self.bench.set_output(amplitude_v, frequency_hz)

    def output_off(self):
        self.bench.output_off()

    def capture(self, sample_rate_hz, samples):
        return self.bench.capture(sample_rate_hz, samples)


def declaration():
    return Declaration(
        dataset="test",
        origin="simulated",
        description="square-wave captures of the simulated bench",
        units={"source": "V", "response": "V"},
        provenance="SimulatedRLCBench, seed 0",
    )


# -- the envelope and the instrument --------------------------------------------


def test_an_envelope_permits_only_the_sine_unless_it_names_the_square_wave():
    log = CallLog(SimulatedRLCBench())
    instrument = Instrument(log, envelope(waveforms=(SINE,)))
    with pytest.raises(OutOfEnvelope, match="square"):
        instrument.excite(1.0, 1_000.0, SQUARE)
    assert log.device_calls() == []
    assert "waveforms" not in envelope(waveforms=(SINE,)).describe()
    assert envelope().describe()["waveforms"] == ["sine", "square"]


def test_an_unknown_waveform_is_refused_by_the_envelope_and_never_declared():
    with pytest.raises(ValueError, match="waveforms"):
        envelope(waveforms=("triangle",))
    log = CallLog(SimulatedRLCBench())
    with pytest.raises(OutOfEnvelope):
        Instrument(log, envelope()).excite(1.0, 1_000.0, "triangle")
    assert log.device_calls() == []


def test_an_adapter_that_declares_no_square_wave_is_never_asked_for_one():
    log = CallLog(SineOnly())
    instrument = Instrument(log, envelope())
    with pytest.raises(Refused, match="does not output"):
        instrument.excite(1.0, 1_000.0, SQUARE)
    assert log.device_calls() == []
    # The sine reaches it as before F145.
    instrument.excite(1.0, 1_000.0)
    assert log.device_calls() == [("set_output", 1.0, 1_000.0)]


def test_the_square_wave_is_held_to_the_same_ranges_and_current_bound():
    bounded = envelope(
        current=Limit("source current bound", "A", 0.0, 0.030), resistance=50.0
    )
    log = CallLog(SimulatedRLCBench())
    instrument = Instrument(log, bounded)
    for amplitude, frequency in ((2.5, 1_000.0), (1.0, 60_000.0), (2.0, 1_000.0)):
        with pytest.raises(OutOfEnvelope):
            instrument.excite(amplitude, frequency, SQUARE)
    assert log.device_calls() == []
    instrument.excite(1.0, 1_000.0, SQUARE)
    assert log.device_calls() == [("set_output", 1.0, 1_000.0, SQUARE)]
    assert instrument.snapshot()["output"] == {
        "amplitude_v": 1.0,
        "frequency_hz": 1_000.0,
        "waveform": SQUARE,
    }
    instrument.request_stop()
    assert instrument.snapshot()["output"] is None


# -- the current bound of a step -------------------------------------------------


@pytest.mark.parametrize("resistance", [20.0, 100.0, 300.0, 1_000.0])
def test_a_step_drives_at_most_the_amplitude_over_the_series_resistance(resistance):
    """The bound the envelope computes for the square wave, amplitude over
    series resistance, holds for the step response of a series RLC circuit
    from Q about 16 to overdamped: the integrated current never exceeds it."""
    circuit = SeriesRLC(resistance=resistance, inductance=10e-3, capacitance=100e-9)
    bench = SimulatedRLCBench(circuit=circuit, noise_v=0.0)
    bench.set_output(1.0, 100.0, waveform=SQUARE)
    times = np.linspace(0.0, 0.02, 20_001)
    _, current = bench._square_response(times)
    peak = float(np.max(np.abs(current)))
    assert peak <= 1.0 / resistance
    # The closed form of the underdamped peak, (A / (Q R)) e^(-alpha t*).
    if circuit.quality_factor > 0.5:
        alpha = circuit.damping_rate
        omega_d = math.sqrt(circuit.natural_frequency**2 - alpha**2)
        t_star = math.atan2(omega_d, alpha) / omega_d
        closed = math.exp(-alpha * t_star) / (circuit.quality_factor * resistance)
        assert peak == pytest.approx(closed, rel=1e-3)


# -- the adapters -----------------------------------------------------------------


def test_the_simulated_square_wave_steps_between_zero_and_the_amplitude():
    bench = SimulatedRLCBench(noise_v=0.0)
    bench.set_output(1.5, 200.0, waveform=SQUARE)
    capture = bench.capture(200_000.0, 1_500)
    source = capture.channels["source"]
    assert set(np.unique(source)) == {0.0, 1.5}
    assert np.array_equal(source, square_wave(1.5, 200.0, 0.0024 + capture.t))
    # The capacitor rings about the level and settles to it: after a rising
    # edge it overshoots 1.5 V (Q about 3), and it never goes below -1.5 V.
    response = capture.channels["response"]
    assert 1.5 < response.max() < 3.0
    assert response.min() > -1.5


def test_a_sine_on_the_simulated_bench_is_unchanged_by_the_square_wave():
    a, b = SimulatedRLCBench(seed=3), SimulatedRLCBench(seed=3)
    a.set_output(1.0, 5_000.0)
    b.set_output(1.0, 5_000.0, waveform=SINE)
    first, second = a.capture(320_000.0, 513), b.capture(320_000.0, 513)
    for name in ("source", "response"):
        assert np.array_equal(first.channels[name], second.channels[name])


def test_a_recorded_sample_answers_only_the_waveform_it_holds(tmp_path):
    settings = [(SETTING.amplitude_v, SETTING.frequency_hz, SETTING.sample_rate_hz,
                 SETTING.samples)]  # fmt: skip
    sample = record_sample(SimulatedRLCBench(), settings, declaration(), SQUARE)
    path = tmp_path / "sample.json"
    save_sample(path, sample)
    loaded = load_sample(path)
    assert loaded.captures[0].waveform == SQUARE
    bench = RecordedBench(loaded)
    bench.set_output(SETTING.amplitude_v, SETTING.frequency_hz)
    with pytest.raises(Refused, match="sine"):
        bench.capture(SETTING.sample_rate_hz, SETTING.samples)
    bench.set_output(SETTING.amplitude_v, SETTING.frequency_hz, waveform=SQUARE)
    assert len(bench.capture(SETTING.sample_rate_hz, SETTING.samples).t) == 1_500


def test_a_sample_written_before_the_square_wave_reads_as_a_sine(tmp_path):
    sample = RecordedSample(
        declaration(), (RecordedCapture(1.0, 1_000.0, 64_000.0, {"source": (0.0,)}),)
    )
    path = tmp_path / "old.json"
    save_sample(path, sample)
    text = path.read_text().replace('"waveform": "sine",', "")
    text = text.replace(',\n   "waveform": "sine"', "")
    path.write_text(text)
    assert "waveform" not in path.read_text()
    assert load_sample(path).captures[0].waveform == SINE


# -- the waveform checks ------------------------------------------------------------


def _recorded_square():
    settings = [(SETTING.amplitude_v, SETTING.frequency_hz, SETTING.sample_rate_hz,
                 SETTING.samples)]  # fmt: skip
    sample = record_sample(SimulatedRLCBench(), settings, declaration(), SQUARE)
    return lambda: RecordedBench(sample)


@pytest.mark.parametrize(
    "make",
    [
        SimulatedRLCBench,
        _recorded_square(),
        lambda: ImperfectChannels(SimulatedRLCBench(), {"source": ChannelChain()}),
    ],
    ids=["simulated", "recorded", "channels"],
)
def test_every_adapter_that_declares_the_square_wave_passes_the_waveform_checks(
    make,
):
    findings = {f.check: f.status for f in check_waveforms(make, SETTING)}
    assert findings == {
        "square-on-source": PASSED,
        "waveform-before-adapter": PASSED,
        "undeclared-waveform": NOT_APPLICABLE,
    }


def test_a_sine_only_adapter_passes_by_refusal():
    findings = {f.check: f.status for f in check_waveforms(SineOnly, SETTING)}
    assert findings == {
        "square-on-source": NOT_APPLICABLE,
        "waveform-before-adapter": PASSED,
        "undeclared-waveform": PASSED,
    }


class InvertedSquare(SimulatedRLCBench):
    """An adapter that outputs the square wave between -A and 0 V."""

    def capture(self, sample_rate_hz, samples):
        capture = super().capture(sample_rate_hz, samples)
        capture.channels["source"] = capture.channels["source"] - self._amplitude
        return capture


class PassesTheSquareThrough(SineOnly):
    """An adapter that declares no square wave and would output one if asked."""

    waveforms = (SINE,)

    def set_output(self, amplitude_v, frequency_hz, waveform=SINE):
        self.bench.set_output(amplitude_v, frequency_hz, waveform=waveform)


def test_the_square_check_fails_an_adapter_whose_levels_are_wrong():
    findings = {f.check: f for f in check_waveforms(InvertedSquare, SETTING)}
    assert findings["square-on-source"].status == FAILED


def test_the_undeclared_check_holds_for_an_adapter_that_could_output_it():
    findings = {
        f.check: f.status for f in check_waveforms(PassesTheSquareThrough, SETTING)
    }
    assert findings["undeclared-waveform"] == PASSED


def test_a_sample_on_an_edge_is_integrated_like_any_other():
    """The square drive is integrated over every half period up to and
    including the one that starts at the last sample's time."""
    bench = SimulatedRLCBench(noise_v=0.0)
    bench.set_output(1.0, 100.0, waveform=SQUARE)
    charge, current = bench._square_response(np.array([0.001, 0.005, 0.01]))
    assert np.all(np.isfinite(charge)) and np.all(np.abs(current) <= 0.01)
