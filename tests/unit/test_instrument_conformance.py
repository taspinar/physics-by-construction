"""The contract tests of the instrument adapters (F142, acceptance criterion 2
of Issue #570): the simulated, the recorded, the channel, and the
resistor-probe adapters pass the same checks, and so does a stand-in for the
optional live adapter, which exists only in tests until F140; every check
fails on an adapter that breaks what it checks."""

import numpy as np
import pytest

from pbc.instruments import LIVE, MODES, Capture
from pbc.instruments.channels import ChannelChain, Dropouts, ImperfectChannels
from pbc.instruments.conformance import (
    CHECKS,
    FAILED,
    NOT_APPLICABLE,
    PASSED,
    CallLog,
    Setting,
    amplitude_at,
    check_driver,
)
from pbc.instruments.recorded import Declaration, RecordedBench, record_sample
from pbc.instruments.simulated import ResistorProbeBench, SimulatedRLCBench

SETTING = Setting(1.0, 4_000.0, 256_000.0, 513)


class LiveStandIn:
    """What a live adapter does, for tests only: it has the live mode and
    answers like a device would, from the simulated bench behind it."""

    mode = LIVE

    def __init__(self):
        self._bench = SimulatedRLCBench(seed=11)

    def identity(self):
        return {"device": "live stand-in (tests only)", "calibration": "factory"}

    def set_output(self, amplitude_v, frequency_hz):
        self._bench.set_output(amplitude_v, frequency_hz)

    def output_off(self):
        self._bench.output_off()

    def capture(self, sample_rate_hz, samples):
        return self._bench.capture(sample_rate_hz, samples)


def recorded():
    declaration = Declaration(
        "conformance-sample",
        "simulated",
        "a test",
        {"source": "V", "response": "V"},
        "",
    )
    sample = record_sample(
        SimulatedRLCBench(seed=5),
        [(SETTING.amplitude_v, SETTING.frequency_hz, SETTING.sample_rate_hz, 513)],
        declaration,
    )
    return RecordedBench(sample)


ADAPTERS = {
    "simulated": lambda: SimulatedRLCBench(seed=1),
    "resistor-probe": lambda: ResistorProbeBench(seed=1),
    "recorded": recorded,
    "channels": lambda: ImperfectChannels(
        SimulatedRLCBench(seed=1),
        {"response": ChannelChain(0.97, 0.01, 4.0, 12)},
        Dropouts(2, 8, seed=3),
    ),
    "live-stand-in": LiveStandIn,
}


@pytest.mark.parametrize("name", ADAPTERS)
def test_every_adapter_passes_the_same_contract_tests(name):
    findings = check_driver(ADAPTERS[name], SETTING)
    assert [f.check for f in findings] == [check for check, _ in CHECKS]
    for finding in findings:
        expected = (
            NOT_APPLICABLE if (name, finding.check) == ("live-stand-in", "repeatable")
            else PASSED
        )  # fmt: skip
        assert finding.status == expected, finding


def test_the_checks_cover_the_modes():
    assert {ADAPTERS[n]().mode for n in ADAPTERS} == set(MODES)


# -- every check can fail ------------------------------------------------------------


class Broken(SimulatedRLCBench):
    """The simulated bench with one fault, chosen by name."""

    def __init__(self, fault):
        super().__init__(seed=1)
        self.fault = fault

    @property
    def mode(self):
        return "remote" if self.fault == "mode" else super().mode

    def identity(self):
        if self.fault == "identity":
            return {"device": "a bench"}
        return super().identity()

    def output_off(self):
        if self.fault == "off-raises":
            raise RuntimeError("no output to switch off")
        if self.fault != "forgets-off":
            super().output_off()

    def set_output(self, amplitude_v, frequency_hz):
        if self.fault == "volts-as-millivolts":
            amplitude_v = amplitude_v * 1e-3
        super().set_output(amplitude_v, frequency_hz)

    def capture(self, sample_rate_hz, samples):
        if self.fault == "unseeded":
            self.seed = int(np.random.SeedSequence().entropy % 1000)
        capture = super().capture(sample_rate_hz, samples)
        if self.fault == "short":
            return Capture(
                capture.sample_rate_hz,
                capture.t[:-1],
                {k: v[:-1] for k, v in capture.channels.items()},
                capture.units,
            )
        if self.fault == "units":
            return Capture(
                capture.sample_rate_hz,
                capture.t,
                capture.channels,
                {**capture.units, "response": "mV"},
            )
        return capture


@pytest.mark.parametrize(
    ("fault", "fails"),
    [
        ("mode", {"mode", "envelope-before-adapter", "stop"}),
        ("identity", {"identity"}),
        (
            "off-raises",
            {"output-off-at-any-time", "output-off-stops-excitation", "stop"},
        ),
        ("short", {"capture-shape"}),
        ("units", {"units"}),
        ("volts-as-millivolts", {"excitation-on-source"}),
        ("forgets-off", {"output-off-stops-excitation"}),
        ("unseeded", {"repeatable"}),
    ],
)
def test_each_check_fails_on_the_fault_it_is_for(fault, fails):
    findings = check_driver(lambda: Broken(fault), SETTING)
    assert {f.check for f in findings if f.status == FAILED} == fails


def test_a_forgetful_adapter_still_passes_the_stop_check():
    """The instrument switches the output off through the adapter and cannot
    see that the adapter ignored it: only the adapter's own check shows it."""
    findings = {
        f.check: f for f in check_driver(lambda: Broken("forgets-off"), SETTING)
    }
    assert findings["stop"].status == PASSED
    assert findings["output-off-stops-excitation"].status == FAILED


def test_the_call_log_passes_every_call_on_and_records_it():
    log = CallLog(SimulatedRLCBench(seed=2))
    log.output_off()
    log.set_output(1.0, 4_000.0)
    capture = log.capture(256_000.0, 513)
    assert log.calls == [
        ("output_off",),
        ("set_output", 1.0, 4_000.0),
        ("capture", 256_000.0, 513),
    ]
    assert log.device_calls() == log.calls[1:]
    direct = SimulatedRLCBench(seed=2)
    direct.set_output(1.0, 4_000.0)
    np.testing.assert_array_equal(
        capture.channels["response"],
        direct.capture(256_000.0, 513).channels["response"],
    )


def test_the_amplitude_at_a_frequency_leaves_lost_samples_out():
    t = np.arange(400) / 40_000.0
    signal = 0.7 * np.cos(2 * np.pi * 1_000.0 * t + 0.3) + 0.2
    signal[50:90] = np.nan
    assert amplitude_at(signal, t, 1_000.0) == pytest.approx(0.7, rel=1e-9)


def test_the_resistor_probe_reads_the_source_at_resonance():
    """At the natural frequency the impedance is R alone, so the voltage
    across the resistor equals the source voltage."""
    bench = ResistorProbeBench(seed=0, noise_v=0.0)
    f0 = bench.circuit.natural_frequency / (2 * np.pi)
    bench.set_output(1.0, f0)
    capture = bench.capture(64 * f0, 8 * 64 + 1)
    np.testing.assert_allclose(
        capture.channels["response"], capture.channels["source"], atol=1e-4
    )
    assert bench.identity()["probe"] == "response across the resistor"


def test_the_capacitor_bench_is_unchanged_by_the_probe_hook():
    """The default probe still reads the capacitor: the steady amplitude at
    the natural frequency is Q times the source."""
    bench = SimulatedRLCBench(seed=0, noise_v=0.0)
    f0 = bench.circuit.natural_frequency / (2 * np.pi)
    bench.set_output(1.0, f0)
    capture = bench.capture(64 * f0, 8 * 64 + 1)
    found = amplitude_at(capture.channels["response"], capture.t, f0)
    assert found == pytest.approx(bench.circuit.quality_factor, rel=1e-4)
    assert "probe" not in bench.identity()
