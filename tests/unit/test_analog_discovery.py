"""The live adapter of the Analog Discovery 3 (F140), on a stand-in for the
WaveForms SDK library, so that its calls, its refusals, and the contract
tests run without the library or a device; and the envelope's current bound.
The same checks on the real device are in ``test_analog_discovery_device.py``,
which runs only when asked to.

The stand-in answers like the SDK of WaveForms 3.25.1 as the pilot found it
(2026-11-22): the scope's rate is 100 MHz over a whole number, and the
generator keeps the frequency set. Its response channel is a fixed transfer
function, so that what the protocol reads from a capture can be compared with
a known answer.
"""

import ctypes
import math
import threading
import time

import numpy as np
import pytest

from pbc.instruments import (
    Envelope,
    Instrument,
    Limit,
    OutOfEnvelope,
    Refused,
    Stopped,
)
from pbc.instruments import analog_discovery as ad
from pbc.instruments.conformance import FAILED, NOT_APPLICABLE, Setting, check_driver
from pbc.products.physics_lab import workflow
from pbc.products.physics_lab.protocol import (
    Config,
    fitted_phasor,
    live_envelope,
    transfer,
    whole_periods,
)

CLOCK_HZ = 100e6
GAIN, PHASE_DEG = 0.5, -60.0  # the stand-in's response over its source


def _value(x):
    return x.value if hasattr(x, "value") else x


def _store(reference, value):
    reference._obj.value = value


class FakeSDK:
    """A stand-in for the SDK library: the functions the adapter calls, with
    a log of every call by name, and switches for the failures."""

    def __init__(self, devices=1, opened=False, fail=(), polls=2, block_polls=None):
        self.devices = devices
        self.opened = opened
        self.fail = set(fail)
        self.polls = polls
        self.block_polls = block_polls  # an Event the status waits on
        self.calls: list[tuple] = []
        self.params: dict[int, int] = {}
        self.device_params: dict[int, int] = {}
        self.out = {"enabled": 0, "frequency": 0.0, "amplitude": 0.0, "running": 0}
        self.ranges: dict[int, float] = {}
        self.rate = 0.0
        self.buffer = 0
        self.remaining = 0
        self.handle = 0
        self.polling = threading.Event()

    def _log(self, name, *arguments):
        self.calls.append((name, *(_value(a) for a in arguments)))
        return 0 if name in self.fail else 1

    def names(self):
        return [c[0] for c in self.calls]

    def FDwfGetVersion(self, buffer):
        buffer.value = b"3.25.1"
        return 1

    def FDwfGetLastErrorMsg(self, buffer):
        buffer.value = b"stand-in error"
        return 1

    def FDwfParamSet(self, param, value):
        self.params[_value(param)] = _value(value)
        return self._log("FDwfParamSet", param, value)

    def FDwfEnum(self, kind, count):
        _store(count, self.devices)
        return self._log("FDwfEnum", kind)

    def FDwfEnumDeviceName(self, index, buffer):
        buffer.value = b"Analog Discovery 3"
        return 1

    def FDwfEnumSN(self, index, buffer):
        buffer.value = b"SN:TEST"
        return 1

    def FDwfEnumDeviceIsOpened(self, index, flag):
        _store(flag, int(self.opened))
        return 1

    def FDwfDeviceOpen(self, index, handle):
        ok = self._log("FDwfDeviceOpen", index)
        if ok:
            self.handle = 7
            _store(handle, 7)
        return ok

    def FDwfDeviceClose(self, handle):
        self.out["running"] = 0  # DwfParamOnClose stop
        self.handle = 0
        return self._log("FDwfDeviceClose", handle)

    def FDwfDeviceAutoConfigureSet(self, handle, value):
        return self._log("FDwfDeviceAutoConfigureSet", handle, value)

    def FDwfDeviceParamSet(self, handle, param, value):
        self.device_params[_value(param)] = _value(value)
        return self._log("FDwfDeviceParamSet", handle, param, value)

    def FDwfAnalogInChannelEnableSet(self, handle, channel, value):
        return self._log("FDwfAnalogInChannelEnableSet", handle, channel, value)

    def FDwfAnalogInChannelRangeSet(self, handle, channel, span):
        self.ranges[_value(channel)] = _value(span)
        return self._log("FDwfAnalogInChannelRangeSet", handle, channel, span)

    def FDwfAnalogInChannelOffsetSet(self, handle, channel, offset):
        return self._log("FDwfAnalogInChannelOffsetSet", handle, channel, offset)

    def FDwfAnalogInConfigure(self, handle, reconfigure, start):
        if _value(start):
            self.remaining = self.polls
        return self._log("FDwfAnalogInConfigure", handle, reconfigure, start)

    def FDwfAnalogInFrequencySet(self, handle, rate):
        # the divider is rounded to the nearest whole number, halves up (the
        # pilot: 62.5 gave 63, 31.25 gave 31)
        self.rate = CLOCK_HZ / math.floor(CLOCK_HZ / _value(rate) + 0.5)
        return self._log("FDwfAnalogInFrequencySet", handle, rate)

    def FDwfAnalogInFrequencyGet(self, handle, rate):
        _store(rate, self.rate)
        return self._log("FDwfAnalogInFrequencyGet", handle)

    def FDwfAnalogInBufferSizeSet(self, handle, samples):
        self.buffer = _value(samples)
        return self._log("FDwfAnalogInBufferSizeSet", handle, samples)

    def FDwfAnalogInStatus(self, handle, read, state):
        self.polling.set()
        if self.block_polls is not None:
            self.block_polls.wait(5.0)
        self.remaining -= 1
        _store(state, ad.STATE_DONE if self.remaining <= 0 else 1)
        return self._log("FDwfAnalogInStatus", handle)

    def FDwfAnalogInStatusData(self, handle, channel, buffer, samples):
        n = _value(samples)
        t = np.arange(n) / self.rate
        amplitude = self.out["amplitude"] if self.out["running"] else 0.0
        omega = 2.0 * math.pi * self.out["frequency"]
        if _value(channel) == ad.SOURCE_CHANNEL:
            values = amplitude * np.cos(omega * t) + 0.003  # an input offset
        else:
            phase = math.radians(PHASE_DEG)
            values = GAIN * amplitude * np.cos(omega * t + phase) - 0.01
        for i, v in enumerate(values):
            buffer[i] = v
        return self._log("FDwfAnalogInStatusData", handle, channel)

    def FDwfAnalogOutNodeEnableSet(self, handle, channel, node, value):
        self.out["enabled"] = _value(value)
        return self._log("FDwfAnalogOutNodeEnableSet", handle, channel, node, value)

    def FDwfAnalogOutNodeFunctionSet(self, handle, channel, node, function):
        return self._log(
            "FDwfAnalogOutNodeFunctionSet", handle, channel, node, function
        )

    def FDwfAnalogOutNodeFrequencySet(self, handle, channel, node, frequency):
        self.out["frequency"] = _value(frequency)
        return self._log(
            "FDwfAnalogOutNodeFrequencySet", handle, channel, node, frequency
        )

    def FDwfAnalogOutNodeFrequencyGet(self, handle, channel, node, frequency):
        _store(frequency, self.out["frequency"])
        return self._log("FDwfAnalogOutNodeFrequencyGet", handle, channel, node)

    def FDwfAnalogOutNodeAmplitudeSet(self, handle, channel, node, amplitude):
        self.out["amplitude"] = _value(amplitude)
        return self._log(
            "FDwfAnalogOutNodeAmplitudeSet", handle, channel, node, amplitude
        )

    def FDwfAnalogOutNodeOffsetSet(self, handle, channel, node, offset):
        return self._log("FDwfAnalogOutNodeOffsetSet", handle, channel, node, offset)

    def FDwfAnalogOutConfigure(self, handle, channel, start):
        self.out["running"] = int(bool(_value(start)) and self.out["enabled"])
        return self._log("FDwfAnalogOutConfigure", handle, channel, start)

    def FDwfAnalogIOStatus(self, handle):
        return self._log("FDwfAnalogIOStatus", handle)

    def FDwfAnalogIOChannelNodeStatus(self, handle, channel, node, value):
        _store(value, 10.0 * _value(channel) + _value(node))
        return self._log("FDwfAnalogIOChannelNodeStatus", handle, channel, node)


def make(sdk=None, **options):
    options.setdefault("warmup_s", 0.0)
    options.setdefault("settle_s", 0.0)
    return ad.AnalogDiscovery3(sdk or FakeSDK(), library="stand-in", **options)


def generator_calls(sdk):
    """The generator calls after the opening (which switches W1 off before
    the inputs are configured)."""
    names = sdk.names()
    opened = (
        names.index("FDwfAnalogInConfigure") if "FDwfAnalogInConfigure" in names else 0
    )
    return [c for c in sdk.calls[opened:] if c[0].startswith("FDwfAnalogOut")]


# -- opening -------------------------------------------------------------------


def test_the_outputs_stop_on_close_before_the_device_is_opened():
    """DwfParamOnClose is 1 (stop) for the library before the device opens,
    and for the device after, instead of the vendor's samples' continue."""
    sdk = FakeSDK()
    make(sdk)
    names = sdk.names()
    assert names.index("FDwfParamSet") < names.index("FDwfDeviceOpen")
    assert sdk.params[ad.PARAM_ON_CLOSE] == ad.ON_CLOSE_STOP == 1
    assert sdk.device_params[ad.PARAM_ON_CLOSE] == 1


def test_the_input_ranges_hold_the_source_and_the_resonant_capacitor():
    """Channel 1 on plus or minus 2.5 V (above the envelope's 2 V), channel 2
    on plus or minus 25 V (above Q times 2 V of the bench circuit)."""
    sdk = FakeSDK()
    make(sdk)
    assert sdk.ranges == {ad.SOURCE_CHANNEL: 5.0, ad.RESPONSE_CHANNEL: 50.0}
    assert live_envelope(99.0).amplitude.high < 5.0 / 2
    assert 3.2 * live_envelope(99.0).amplitude.high < 50.0 / 2


def test_the_identity_comes_from_the_device_and_names_the_calibration():
    identity = make().identity()
    assert identity["device"] == "Digilent Analog Discovery 3"
    assert identity["serial"] == "SN:TEST"
    assert identity["sdk"] == "WaveForms SDK 3.25.1"
    assert "factory calibration" in identity["calibration"]
    assert identity["on_close"] == "stop"


@pytest.mark.parametrize(
    ("sdk", "message"),
    [
        (FakeSDK(devices=0), "finds 0 device"),
        (FakeSDK(opened=True), "close WaveForms"),
        (FakeSDK(fail={"FDwfDeviceOpen"}), "did not open"),
    ],
    ids=["no-device", "opened-elsewhere", "open-fails"],
)
def test_a_missing_or_busy_device_is_refused_with_what_to_do(sdk, message):
    with pytest.raises(ad.DeviceUnavailable, match=message):
        make(sdk)
    assert "FDwfAnalogOutConfigure" not in sdk.names()


def test_a_missing_library_is_refused_with_the_installation_step(monkeypatch):
    monkeypatch.setenv(ad.ENVIRONMENT, "/nonexistent/dwf")
    assert ad.library_path() == "/nonexistent/dwf"
    with pytest.raises(ad.DeviceUnavailable, match="WaveForms SDK library"):
        ad.load_library()
    monkeypatch.delenv(ad.ENVIRONMENT)
    assert ad.library_path("darwin") == "/Library/Frameworks/dwf.framework/dwf"


# -- the driver protocol -------------------------------------------------------


def test_the_adapter_passes_the_contract_tests_on_the_stand_in():
    setting = Setting(1.0, 47_000.0, 64 * 47_000.0, 513)
    findings = check_driver(make, setting)
    assert [f for f in findings if f.status == FAILED] == []
    repeatable = next(f for f in findings if f.check == "repeatable")
    assert repeatable.status == NOT_APPLICABLE
    shape = next(f for f in findings if f.check == "capture-shape")
    assert "realised" in shape.detail


def test_a_rate_beyond_the_tolerance_fails_the_contract_test():
    """The tolerance of a realised rate is a bound, not a pass: a driver
    that reports a rate 2 % from the request fails capture-shape."""

    class Drifting(ad.AnalogDiscovery3):
        def capture(self, sample_rate_hz, samples):
            return super().capture(sample_rate_hz * 1.02, samples)

    def make_drifting():
        return Drifting(FakeSDK(), library="stand-in", warmup_s=0.0, settle_s=0.0)

    setting = Setting(1.0, 10_000.0, 1_000_000.0, 513)
    findings = {f.check: f for f in check_driver(make_drifting, setting)}
    assert findings["capture-shape"].status == FAILED


def test_the_capture_reports_the_realised_rate_and_the_protocol_reads_it():
    """At 64 samples per period of 25 kHz the scope realises 100 MHz / 63, not
    1.6 MS/s: the record does not span whole periods, and the fitted phasors
    recover the stand-in's gain and phase, with its input offsets."""
    driver = make()
    driver.set_output(1.0, 25_000.0)
    capture = driver.capture(64 * 25_000.0, 513)
    assert capture.sample_rate_hz == pytest.approx(CLOCK_HZ / 63)
    assert np.allclose(capture.t, np.arange(513) / capture.sample_rate_hz)
    assert not whole_periods(capture.t, 25_000.0)
    gain, phase = transfer(capture, driver.frequency_set_hz)
    assert gain == pytest.approx(GAIN, rel=1e-9)
    assert phase == pytest.approx(PHASE_DEG, abs=1e-7)


def test_on_whole_periods_the_fit_and_the_steady_phasor_agree():
    """The fit is the fallback, and on whole periods it gives the projection
    of steady_phasor, so the simulated and recorded routes read the same."""
    from pbc.electromagnetism.circuits import steady_phasor

    t = np.arange(513) / (64 * 1000.0)
    omega = 2.0 * math.pi * 1000.0
    signal = 0.7 * np.cos(omega * t - 1.1)
    assert whole_periods(t, 1000.0)
    assert fitted_phasor(signal, t, omega) == pytest.approx(
        steady_phasor(signal, t, omega), abs=1e-12
    )


def test_output_off_is_safe_at_any_time_and_stops_the_generator():
    sdk = FakeSDK()
    driver = make(sdk)
    driver.output_off()
    driver.set_output(1.0, 10_000.0)
    assert sdk.out["running"] == 1
    driver.output_off()
    driver.output_off()
    assert sdk.out["running"] == 0
    driver.close()
    before = len(sdk.calls)
    driver.output_off()
    driver.close()
    assert len(sdk.calls) == before  # nothing reaches a closed device
    with pytest.raises(ad.DeviceError, match="closed"):
        driver.set_output(1.0, 10_000.0)


def test_a_failed_sdk_call_is_refused_with_its_message():
    sdk = FakeSDK(fail={"FDwfAnalogOutNodeFrequencySet"})
    driver = make(sdk)
    with pytest.raises(ad.DeviceError, match="stand-in error"):
        driver.set_output(1.0, 10_000.0)
    assert sdk.out["running"] == 0


def test_an_acquisition_that_never_finishes_is_refused_at_its_deadline():
    sdk = FakeSDK(polls=10**9)
    ticks = iter(range(10**6))
    driver = make(sdk, poll_deadline_s=5.0, clock=lambda: float(next(ticks)))
    driver.set_output(1.0, 10_000.0)
    with pytest.raises(ad.DeviceError, match="did not finish within 5 s"):
        driver.capture(640_000.0, 513)
    assert driver.poll_deadline_s < live_envelope(99.0).timeout_s


def test_the_operating_conditions_come_from_the_device_monitor():
    conditions = make().conditions()
    assert set(conditions) == {
        "pcb_temperature_c",
        "die_temperature_c",
        "usb_voltage_v",
        "usb_current_a",
        "aux_voltage_v",
        "aux_current_a",
    }
    assert conditions["aux_voltage_v"] == 24.0  # channel 2, node 4


# -- through the instrument ----------------------------------------------------


@pytest.mark.parametrize(
    ("amplitude", "frequency"),
    [(2.5, 47_000.0), (1.0, 250_000.0), (1.0, 500.0), (math.nan, 47_000.0)],
    ids=["amplitude", "frequency-high", "frequency-low", "not-a-number"],
)
def test_an_excitation_outside_the_live_envelope_never_reaches_the_device(
    amplitude, frequency
):
    sdk = FakeSDK()
    instrument = Instrument(make(sdk), live_envelope(99.0))
    with pytest.raises(OutOfEnvelope):
        instrument.excite(amplitude, frequency)
    assert generator_calls(sdk) == []


def test_the_current_bound_refuses_what_the_circuit_resistance_cannot_carry():
    """A declared 50 ohm circuit: 1.5 V drives at most 30 mA and is accepted,
    2 V would drive 40 mA and never reaches the device."""
    sdk = FakeSDK()
    instrument = Instrument(make(sdk), live_envelope(50.0))
    with pytest.raises(OutOfEnvelope, match="current"):
        instrument.excite(2.0, 47_000.0)
    assert generator_calls(sdk) == []
    instrument.excite(1.5, 47_000.0)
    assert sdk.out == {**sdk.out, "running": 1, "amplitude": 1.5}


def test_the_bench_circuit_at_the_envelope_maximum_stays_within_the_bound():
    envelope = live_envelope(99.0)
    assert envelope.amplitude.high / 99.0 <= envelope.current.high
    assert envelope.describe()["series_resistance_ohm"] == 99.0
    assert envelope.describe()["limits"][-1]["unit"] == "A"


def test_a_current_bound_needs_a_positive_resistance():
    limits = {
        "amplitude": Limit("a", "V", 0, 1),
        "frequency": Limit("f", "Hz", 1, 2),
        "sample_rate": Limit("r", "samples/s", 1, 2),
        "samples": Limit("n", "samples", 1, 2),
        "timeout_s": 1.0,
        "current": Limit("i", "A", 0, 0.03),
    }
    for resistance in (None, 0.0, -1.0, math.inf):
        with pytest.raises(ValueError, match="series resistance"):
            Envelope(**limits, series_resistance_ohm=resistance)


def test_a_stop_during_an_acquisition_switches_the_generator_off_at_once():
    """The stop does not wait behind the acquisition: the SDK calls are
    serialised one by one, so the generator is stopped while the scope is
    still polled, and the acquisition's data are not handed out."""
    release = threading.Event()
    sdk = FakeSDK(block_polls=release)
    instrument = Instrument(make(sdk), live_envelope(99.0))
    instrument.excite(1.0, 47_000.0)
    outcome = {}

    def acquire():
        try:
            instrument.acquire(64 * 47_000.0, 513)
        except Refused as error:
            outcome["error"] = error

    worker = threading.Thread(target=acquire)
    worker.start()
    assert sdk.polling.wait(5.0)
    started = time.monotonic()
    instrument.request_stop("stop pressed")
    stopped_in = time.monotonic() - started
    assert sdk.out["running"] == 0
    release.set()
    worker.join(5.0)
    assert stopped_in < 1.0
    assert isinstance(outcome["error"], Stopped)
    with pytest.raises(Stopped):
        instrument.excite(1.0, 47_000.0)
    assert generator_calls(sdk)[-1][0] == "FDwfAnalogOutConfigure"
    assert generator_calls(sdk)[-1][-1] == 0


def test_a_live_run_records_the_device_the_circuit_and_the_conditions(tmp_path):
    sdk = FakeSDK()
    driver = make(sdk)
    config = Config(
        low_hz=5_000.0, high_hz=200_000.0, coarse_points=5, refine_points=0,
        circuit_confirmed=True,
    )  # fmt: skip
    result = workflow.run(config, tmp_path, mode="live", driver=driver)
    record = result.run.to_dict()
    assert record["mode"] == "live" and record["new_experiment"] is True
    assert record["device"]["serial"] == "SN:TEST"
    configuration = record["configuration"]
    assert configuration["circuit"]["inductance_h"] == 1e-3
    assert set(configuration["conditions_at_start"]) >= {"die_temperature_c"}
    assert list(record["processing"]) == list(workflow.LIVE_PROCESSING)
    assert sdk.out["running"] == 0  # the run ends with the output off
    # the stand-in's flat gain of 0.5 is no resonance: inconclusive, honestly
    assert result.status == "inconclusive"
    report = (tmp_path / "report.md").read_text()
    assert "lie on the dashed line" not in report


def test_a_live_run_with_the_circuit_unconfirmed_never_starts_the_generator(
    tmp_path,
):
    sdk = FakeSDK()
    result = workflow.run(Config(), tmp_path, mode="live", driver=make(sdk))
    assert result.status == "failed"
    assert "circuit-confirmed" in result.diagnostics[0]
    assert not any(c[0] == "FDwfAnalogOutConfigure" and c[-1] == 1 for c in sdk.calls)


def test_ctypes_arguments_reach_the_sdk_with_their_c_types():
    """The adapter passes ctypes values, as a C library needs: a double for a
    frequency, never a Python float that ctypes would pass as an int."""
    sdk = FakeSDK()
    calls = []
    original = sdk.FDwfAnalogOutNodeFrequencySet

    def spy(handle, channel, node, frequency):
        calls.append(frequency)
        return original(handle, channel, node, frequency)

    sdk.FDwfAnalogOutNodeFrequencySet = spy
    make(sdk).set_output(1.0, 47_000.5)
    assert isinstance(calls[0], ctypes.c_double)
    assert calls[0].value == 47_000.5


def test_a_program_that_ends_without_close_closes_the_device_at_exit():
    """The pilot found that the interpreter crashed at exit with the device
    open (SIGSEGV); the adapter registers a close at exit, output off first,
    which holds the driver only weakly."""
    import weakref

    sdk = FakeSDK()
    driver = make(sdk)
    driver.set_output(1.0, 10_000.0)
    ad._close_at_exit(weakref.ref(driver))
    assert sdk.out["running"] == 0 and sdk.handle == 0
    assert sdk.names()[-1] == "FDwfDeviceClose"
    ad._close_at_exit(weakref.ref(make()))  # and a closed one is no error


# -- the ending of a program: the pilot's crash finding ------------------------
#
# The pilot (2026-11-22, the owner's meter): after kill -9 of the program
# that held the device, W1 kept its last output until the device was opened
# again; DwfParamOnClose acts only on a proper close.


class FakeWatchdog:
    def __init__(self, serial, library):
        self.started = (serial, library)
        self.dismissed = False

    def dismiss(self):
        self.dismissed = True


def test_every_opening_switches_w1_off_before_the_inputs_are_configured():
    sdk = FakeSDK()
    sdk.out.update(enabled=1, running=1, amplitude=2.0)  # a killed program's W1
    make(sdk)
    assert sdk.out["running"] == 0 and sdk.out["enabled"] == 0
    names = sdk.names()
    stop = names.index("FDwfAnalogOutConfigure")
    assert names.index("FDwfDeviceOpen") < stop < names.index("FDwfAnalogInConfigure")


def test_an_opening_whose_stop_is_not_confirmed_is_refused_and_closed():
    sdk = FakeSDK(fail={"FDwfAnalogOutConfigure"})
    with pytest.raises(ad.DeviceError, match="stop at opening"):
        make(sdk)
    assert sdk.handle == 0


def test_a_lost_device_counts_as_closed_and_keeps_its_watchdog():
    """The pulled cable: the stop fails; close does not raise, the device
    counts as closed with the reason, and the watchdog is not dismissed, so
    it stops W1 if the device comes back within its deadline."""
    sdk = FakeSDK()
    watchdogs = []
    driver = make(
        sdk, watchdog=lambda *a: watchdogs.append(FakeWatchdog(*a)) or watchdogs[-1]
    )
    driver.set_output(1.0, 47_000.0)
    sdk.fail.add("FDwfAnalogOutConfigure")
    driver.close()
    assert not driver.is_open
    assert "did not confirm the stop" in driver.lost
    assert watchdogs[0].dismissed is False
    driver.close()  # and again, no error


def test_the_watchdog_starts_with_the_device_and_a_proper_close_dismisses_it():
    sdk = FakeSDK()
    watchdogs = []
    driver = make(
        sdk, watchdog=lambda *a: watchdogs.append(FakeWatchdog(*a)) or watchdogs[-1]
    )
    assert watchdogs[0].started == ("SN:TEST", "stand-in")
    driver.set_output(1.0, 47_000.0)
    driver.close()
    assert watchdogs[0].dismissed is True and driver.lost is None
    # a stand-in SDK starts no watchdog process unless asked to
    assert make()._watchdog is None


def test_a_watchdog_that_does_not_start_leaves_the_device_closed():
    sdk = FakeSDK()

    def failing(serial, library):
        raise OSError("no process")

    with pytest.raises(ad.DeviceError, match="watchdog did not start"):
        make(sdk, watchdog=failing)
    assert sdk.handle == 0


def test_watch_switches_off_only_when_the_program_ends_without_closing():
    switched = []
    assert ad.watch(iter(["\n", "closed\n"]), lambda: switched.append(1)) == "dismissed"
    assert switched == []
    assert ad.watch(iter([]), lambda: switched.append(1)) == "switched off"
    assert ad.watch(iter(["garbage\n"]), lambda: switched.append(1)) == "switched off"
    assert switched == [1, 1]


def test_switch_off_waits_for_the_ended_program_then_stops_w1():
    """The killed program's device is still opened for about 2 s (the
    pilot); switch_off waits, then opens it with on-close stop, stops W1, and
    closes it."""
    sdk = FakeSDK(opened=True)
    sdk.out.update(enabled=1, running=1, amplitude=2.0)
    ticks = iter(range(10**6))

    def sleep(_):
        if len([c for c in sdk.calls if c[0] == "FDwfEnum"]) >= 3:
            sdk.opened = False

    ad.switch_off(sdk, "SN:TEST", sleep=sleep, clock=lambda: float(next(ticks)))
    assert sdk.out["running"] == 0
    assert sdk.params[ad.PARAM_ON_CLOSE] == ad.ON_CLOSE_STOP
    assert sdk.device_params[ad.PARAM_ON_CLOSE] == ad.ON_CLOSE_STOP
    assert sdk.names()[-1] == "FDwfDeviceClose" and sdk.handle == 0


@pytest.mark.parametrize(
    ("sdk", "seen"),
    [(FakeSDK(devices=0), "not found"), (FakeSDK(opened=True), "still opened")],
    ids=["unplugged", "held"],
)
def test_switch_off_refuses_at_its_deadline_and_says_what_to_do(sdk, seen):
    ticks = iter(range(0, 10**6, 10))
    with pytest.raises(ad.DeviceUnavailable, match=f"{seen}.*unplug"):
        ad.switch_off(
            sdk, "SN:TEST", deadline_s=60.0, sleep=lambda _: None,
            clock=lambda: float(next(ticks)),
        )  # fmt: skip
    assert "FDwfDeviceOpen" not in sdk.names()


def test_switch_off_leaves_another_device_alone():
    sdk = FakeSDK()
    ticks = iter(range(0, 10**6, 10))
    with pytest.raises(ad.DeviceUnavailable, match="not found"):
        ad.switch_off(
            sdk, "SN:OTHER", deadline_s=30.0, sleep=lambda _: None,
            clock=lambda: float(next(ticks)),
        )  # fmt: skip
    assert "FDwfDeviceOpen" not in sdk.names()


KILLED_PROGRAM = """
import os, signal, sys
from pbc.instruments import analog_discovery as ad
log = open(sys.argv[1], "w")
dog = ad.Watchdog("SN:TEST", "/nonexistent/dwf", stderr=log)
print(dog.process.pid, flush=True)
os.kill(os.getpid(), signal.SIGKILL)
"""

DISMISSED_PROGRAM = """
import sys
from pbc.instruments import analog_discovery as ad
log = open(sys.argv[1], "w")
dog = ad.Watchdog("SN:TEST", "/nonexistent/dwf", stderr=log)
dog.dismiss()
print(dog.process.returncode, flush=True)
"""


def _ended(pid, within_s=30.0):
    import os

    end = time.monotonic() + within_s
    while time.monotonic() < end:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.05)
    return False


def test_the_watchdog_process_acts_when_its_program_is_killed(tmp_path):
    """A real watchdog process and a program killed with SIGKILL, without a
    device: the watchdog sees the end, tries to switch W1 off (here it finds
    no SDK library, so it says what to do), and ends. Its own session keeps
    it alive past the program."""
    import subprocess
    import sys

    log = tmp_path / "watchdog.log"
    out = subprocess.run(
        [sys.executable, "-c", KILLED_PROGRAM, str(log)],
        capture_output=True, text=True, timeout=60,
    )  # fmt: skip
    assert out.returncode == -9
    assert _ended(int(out.stdout.split()[0]))
    text = log.read_text()
    assert "ended without closing SN:TEST; switching W1 off" in text
    assert "WaveForms SDK library is not at /nonexistent/dwf" in text


def test_a_dismissed_watchdog_process_ends_without_acting(tmp_path):
    import subprocess
    import sys

    log = tmp_path / "watchdog.log"
    out = subprocess.run(
        [sys.executable, "-c", DISMISSED_PROGRAM, str(log)],
        capture_output=True, text=True, timeout=60, check=True,
    )  # fmt: skip
    assert out.stdout.strip() == "0"
    assert log.read_text() == ""
