"""The instrument contract (F138, invariant I34): the adapter layer refuses an
out-of-envelope operation, a timeout, and an operation after a stop before
anything reaches the device, whatever the caller, shown with a fake live
driver that records every call; and every run record names its execution
mode, a recorded run never a new experiment."""

import threading
import time

import numpy as np
import pytest

from pbc.agents.messages import ToolCall
from pbc.agents.tools import Allowlist, Parameter, Tool
from pbc.instruments import (
    LIVE,
    RECORDED,
    SIMULATED,
    Capture,
    Envelope,
    Instrument,
    InstrumentRun,
    InstrumentTimeout,
    Interlock,
    InterlockOpen,
    Limit,
    OutOfEnvelope,
    Stopped,
)
from pbc.instruments.recorded import (
    Declaration,
    NotRecorded,
    RecordedBench,
    load_sample,
    record_sample,
    save_sample,
)
from pbc.instruments.simulated import BENCH_CIRCUIT, SimulatedRLCBench


class FakeLiveDriver:
    """A live driver for tests only: it records every call it receives and
    can be made to block in ``capture`` or in ``set_output``. A blocked
    ``set_output`` is recorded when it returns, the moment a slow device
    would switch its output on."""

    mode = LIVE

    def __init__(
        self,
        block: threading.Event | None = None,
        block_output: threading.Event | None = None,
    ):
        self.calls: list[tuple] = []
        self.block = block
        self.block_output = block_output
        self.entered = threading.Event()
        self.output_entered = threading.Event()

    def identity(self):
        return {"device": "fake live driver (tests only)", "calibration": "none"}

    def set_output(self, amplitude_v, frequency_hz):
        self.output_entered.set()
        if self.block_output is not None:
            self.block_output.wait(5.0)
        self.calls.append(("set_output", amplitude_v, frequency_hz))

    def output_off(self):
        self.calls.append(("output_off",))

    def capture(self, sample_rate_hz, samples):
        self.calls.append(("capture", sample_rate_hz, samples))
        self.entered.set()
        if self.block is not None:
            self.block.wait(5.0)
        t = np.arange(samples) / sample_rate_hz
        return Capture(sample_rate_hz, t, {"source": t, "response": t}, {})

    def device_calls(self):
        """The calls that act on the device, not the safe output_off."""
        return [c for c in self.calls if c[0] != "output_off"]


def wait_until(condition, timeout_s=5.0):
    """Wait for a condition another thread makes true, at most timeout_s."""
    deadline = time.monotonic() + timeout_s
    while not condition():
        assert time.monotonic() < deadline, "the condition did not come true"
        time.sleep(0.005)


def envelope(timeout_s=1.0, interlocks=()):
    return Envelope(
        amplitude=Limit("excitation amplitude", "V", 0.01, 2.0),
        frequency=Limit("excitation frequency", "Hz", 100.0, 50_000.0),
        sample_rate=Limit("sample rate", "samples/s", 1_000.0, 5e6),
        samples=Limit("samples per acquisition", "samples", 16, 16_384, integer=True),
        timeout_s=timeout_s,
        interlocks=interlocks,
    )


@pytest.mark.parametrize(
    ("amplitude", "frequency"),
    [
        (2.5, 1_000.0),  # above the amplitude limit
        (230.0, 50.0),  # mains-like: both out
        (-1.0, 1_000.0),
        (1.0, 99.0),
        (1.0, 1e9),
        (float("nan"), 1_000.0),
        (float("inf"), 1_000.0),
        (True, 1_000.0),
        ("1", 1_000.0),
    ],
)
def test_an_out_of_envelope_excitation_never_reaches_the_driver(amplitude, frequency):
    driver = FakeLiveDriver()
    instrument = Instrument(driver, envelope())
    with pytest.raises(OutOfEnvelope):
        instrument.excite(amplitude, frequency)
    assert driver.calls == []
    assert instrument.counts == {"accepted": 0, "refused": 1}


@pytest.mark.parametrize(
    ("rate", "samples"),
    [
        (1e7, 100),
        (1e4, 10),
        (1e4, 1e5),
        (1e4, float("nan")),
        (1e4, float("inf")),
        (1e4, float("-inf")),
    ],
)
def test_an_out_of_envelope_acquisition_never_reaches_the_driver(rate, samples):
    driver = FakeLiveDriver()
    instrument = Instrument(driver, envelope())
    with pytest.raises(OutOfEnvelope):
        instrument.acquire(rate, samples)
    assert driver.calls == []


def test_a_fractional_number_of_samples_is_refused():
    driver = FakeLiveDriver()
    with pytest.raises(OutOfEnvelope, match="whole number"):
        Instrument(driver, envelope()).acquire(1e4, 100.5)
    assert driver.calls == []


def test_an_open_interlock_keeps_the_output_off():
    confirmed = {"value": False}
    interlock = Interlock("circuit-confirmed", "confirm it", lambda: confirmed["value"])
    driver = FakeLiveDriver()
    instrument = Instrument(driver, envelope(interlocks=(interlock,)))
    with pytest.raises(InterlockOpen, match="circuit-confirmed"):
        instrument.excite(1.0, 1_000.0)
    assert driver.calls == []
    confirmed["value"] = True
    instrument.excite(1.0, 1_000.0)
    assert driver.calls == [("set_output", 1.0, 1_000.0)]


def test_a_timeout_switches_the_output_off_and_halts_the_instrument():
    release = threading.Event()
    driver = FakeLiveDriver(block=release)
    instrument = Instrument(driver, envelope(timeout_s=0.05))
    instrument.excite(1.0, 1_000.0)
    with pytest.raises(InstrumentTimeout):
        instrument.acquire(64_000.0, 513)
    release.set()
    assert driver.calls[-1] == ("output_off",)
    before = driver.device_calls()
    for operation in (
        lambda: instrument.excite(1.0, 1_000.0),
        lambda: instrument.acquire(64_000.0, 513),
    ):
        with pytest.raises(Stopped, match="timeout"):
            operation()
    assert driver.device_calls() == before  # nothing reached the device after
    assert driver.calls[-1] == ("output_off",)
    assert instrument.snapshot()["halted"].startswith("timeout")


def test_a_stop_request_from_another_thread_is_honoured_at_once():
    release = threading.Event()
    driver = FakeLiveDriver(block=release)
    instrument = Instrument(driver, envelope(timeout_s=5.0))
    instrument.excite(1.0, 1_000.0)
    errors = []

    def acquire():
        try:
            instrument.acquire(64_000.0, 513)
        except Stopped as error:
            errors.append(error)

    worker = threading.Thread(target=acquire)
    worker.start()
    assert driver.entered.wait(5.0)
    instrument.request_stop("the learner pressed stop")
    # The output went off while the acquisition was still running.
    assert driver.calls[-1] == ("output_off",)
    assert worker.is_alive()
    release.set()
    worker.join(5.0)
    assert len(errors) == 1, "the data of a stopped acquisition are not handed out"
    device_calls = driver.device_calls()
    with pytest.raises(Stopped, match="the learner pressed stop"):
        instrument.excite(1.0, 1_000.0)
    assert driver.device_calls() == device_calls
    assert instrument.stopped


def test_the_adapter_refuses_whatever_the_caller():
    """A careless tool whose bounds are wider than the envelope, called as an
    agent would call it: the harness accepts the call, the instrument refuses
    it, and the driver never sees it."""
    driver = FakeLiveDriver()
    instrument = Instrument(driver, envelope())

    def excite(amplitude_v, frequency_hz):
        instrument.excite(amplitude_v, frequency_hz)
        return {"ok": 1.0}

    careless = Tool(
        "excite",
        "set the output",
        (
            Parameter("amplitude_v", "V", 0, 1000),
            Parameter("frequency_hz", "Hz", 0, 1e9),
        ),
        excite,
    )
    result = Allowlist((careless,)).dispatch(
        ToolCall("1", "excite", {"amplitude_v": 230.0, "frequency_hz": 50.0})
    )
    assert not result.ok
    assert "outside the permitted range" in result.content["error"]
    assert driver.calls == []


def test_the_snapshot_states_the_mode_the_device_and_the_envelope():
    driver = FakeLiveDriver()
    instrument = Instrument(driver, envelope())
    instrument.excite(0.5, 2_000.0)
    snapshot = instrument.snapshot()
    assert snapshot["mode"] == LIVE
    assert snapshot["device"]["device"].startswith("fake live driver")
    assert snapshot["output"] == {"amplitude_v": 0.5, "frequency_hz": 2_000.0}
    assert snapshot["envelope"]["limits"][0]["unit"] == "V"
    assert snapshot["halted"] is None


# -- execution modes in the run record -------------------------------------------


def _record(instrument):
    return instrument.run_record({"seed": 1}, {"t": "s"}, ("none",), "a", "b")


def test_every_run_record_names_its_mode():
    simulated = _record(Instrument(SimulatedRLCBench(), envelope()))
    live = _record(Instrument(FakeLiveDriver(), envelope()))
    assert (simulated.mode, simulated.new_experiment) == (SIMULATED, True)
    assert (live.mode, live.new_experiment) == (LIVE, True)
    assert "not a measurement" in simulated.label
    for record in (simulated, live):
        assert record.to_dict()["mode"] == record.mode
        assert record.to_dict()["label"] == record.label


def _sample(tmp_path):
    bench = SimulatedRLCBench(seed=3)
    declaration = Declaration(
        "test-sample", "simulated", "a test", {"source": "V", "response": "V"}, "test"
    )
    sample = record_sample(bench, [(1.0, 5_000.0, 320_000.0, 513)], declaration)
    path = tmp_path / "sample.json"
    save_sample(path, sample)
    return path


def test_a_recorded_run_is_never_labelled_a_new_experiment(tmp_path):
    instrument = Instrument(RecordedBench(load_sample(_sample(tmp_path))), envelope())
    record = _record(instrument)
    assert record.mode == RECORDED
    assert record.new_experiment is False
    assert "not a new experiment" in record.label
    assert record.device["origin"] == "simulated"
    with pytest.raises(ValueError, match="never a new experiment"):
        InstrumentRun(RECORDED, {}, {}, {}, (), "a", "b", new_experiment=True)
    with pytest.raises(ValueError, match="is a new experiment"):
        InstrumentRun(SIMULATED, {}, {}, {}, (), "a", "b", new_experiment=False)


def test_a_recorded_sample_answers_only_what_it_recorded(tmp_path):
    path = _sample(tmp_path)
    instrument = Instrument(RecordedBench(load_sample(path)), envelope())
    instrument.excite(1.0, 5_000.0)
    capture = instrument.acquire(320_000.0, 513)
    again = SimulatedRLCBench(seed=3)
    again.set_output(1.0, 5_000.0)
    expected = again.capture(320_000.0, 513)
    np.testing.assert_array_equal(
        capture.channels["response"], expected.channels["response"]
    )
    instrument.excite(1.0, 5_100.0)
    with pytest.raises(NotRecorded, match="cannot make a new measurement"):
        instrument.acquire(320_000.0, 513)


def test_a_declaration_names_its_origin():
    with pytest.raises(ValueError, match="origin"):
        Declaration("x", "made up", "", {}, "")


# -- the simulated adapter ----------------------------------------------------------


def test_the_simulated_bench_is_deterministic_by_its_seed():
    def run(seed):
        bench = SimulatedRLCBench(seed=seed)
        bench.set_output(1.0, 4_000.0)
        return bench.capture(256_000.0, 513).channels["response"]

    np.testing.assert_array_equal(run(7), run(7))
    assert not np.array_equal(run(7), run(8))


def test_the_simulated_steady_state_matches_the_closed_form():
    from pbc.electromagnetism.circuits import steady_phasor

    bench = SimulatedRLCBench(seed=0, noise_v=0.0)
    frequency = 4_000.0
    bench.set_output(1.0, frequency)
    capture = bench.capture(64 * frequency, 8 * 64 + 1)
    omega = 2 * np.pi * frequency
    ratio = steady_phasor(capture.channels["response"], capture.t, omega) / (
        steady_phasor(capture.channels["source"], capture.t, omega)
    )
    expected = BENCH_CIRCUIT.capacitor_phasor(1.0, omega)
    assert abs(ratio / expected - 1) < 1e-4


def _excite_in_thread(instrument, errors):
    def excite():
        try:
            instrument.excite(1.0, 1_000.0)
        except Stopped as error:
            errors.append(error)

    worker = threading.Thread(target=excite)
    worker.start()
    return worker


def test_a_stop_while_the_output_is_switched_on_leaves_it_off():
    """The stop lands while set_output is in the driver: the output the
    driver then switches on goes off again, and excite is refused."""
    release = threading.Event()
    driver = FakeLiveDriver(block_output=release)
    instrument = Instrument(driver, envelope(timeout_s=5.0))
    errors = []
    worker = _excite_in_thread(instrument, errors)
    assert driver.output_entered.wait(5.0)
    instrument.request_stop("the learner pressed stop")
    release.set()
    worker.join(5.0)
    assert len(errors) == 1, "an excitation overtaken by a stop is refused"
    assert ("set_output", 1.0, 1_000.0) in driver.calls
    assert driver.calls[-1] == ("output_off",)
    assert instrument.snapshot()["output"] is None


class _WatchedLock:
    """A lock that says when a second caller starts to wait on it."""

    def __init__(self):
        self._lock = threading.Lock()
        self.waiting = threading.Event()

    def acquire(self):
        if self._lock.locked():
            self.waiting.set()
        return self._lock.acquire()

    def release(self):
        self._lock.release()


def test_a_stop_while_a_caller_waits_on_the_lock_refuses_that_caller():
    release = threading.Event()
    driver = FakeLiveDriver(block=release)
    instrument = Instrument(driver, envelope(timeout_s=5.0))
    instrument._lock = _WatchedLock()
    acquire_errors, excite_errors = [], []

    def acquire():
        try:
            instrument.acquire(64_000.0, 513)
        except Stopped as error:
            acquire_errors.append(error)

    first = threading.Thread(target=acquire)
    first.start()
    assert driver.entered.wait(5.0)
    second = _excite_in_thread(instrument, excite_errors)
    assert instrument._lock.waiting.wait(5.0)
    instrument.request_stop("the learner pressed stop")
    release.set()
    first.join(5.0)
    second.join(5.0)
    assert len(acquire_errors) == 1 and len(excite_errors) == 1
    assert not any(c[0] == "set_output" for c in driver.calls)
    assert driver.calls[-1] == ("output_off",)


def test_a_timed_out_excitation_that_returns_late_leaves_the_output_off():
    release = threading.Event()
    driver = FakeLiveDriver(block_output=release)
    instrument = Instrument(driver, envelope(timeout_s=0.05))
    with pytest.raises(InstrumentTimeout):
        instrument.excite(1.0, 1_000.0)
    assert driver.calls == [("output_off",)]
    release.set()  # the device answers after its timeout and switches on
    wait_until(lambda: len(driver.calls) == 3)
    assert driver.calls == [
        ("output_off",),
        ("set_output", 1.0, 1_000.0),
        ("output_off",),
    ]
    assert instrument.snapshot()["output"] is None
