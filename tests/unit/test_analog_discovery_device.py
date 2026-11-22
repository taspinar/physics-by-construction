"""The live adapter on the real Analog Discovery 3 (F140's physical pilot).

These tests drive a device, so they run only when asked to: with
``PBC_LIVE_DEVICE=1``, the WaveForms SDK library present, an Analog Discovery
connected and not opened by WaveForms, and the pilot's circuit wired (R
100 ohm, L 1 mH, C 10 nF in series from W1 to ground; scope 1+ at W1, 2+ at
the L-C node, both negatives at ground). Otherwise each skips with the
reason, so that no verification and no CI job drives a device. They use at
most 1 V, within the live envelope.

Whether the generator is off is observed with the scope: channel 1 reads W1,
and the amplitude at the excitation's frequency is compared with what was
set. The observation is an acquisition only; it never switches an output on.

    PBC_LIVE_DEVICE=1 uv run --locked pytest -s \
        tests/unit/test_analog_discovery_device.py
"""

import json
import os
import subprocess
import sys
import threading
import time

import numpy as np
import pytest

from pbc.instruments import Instrument, OutOfEnvelope, Stopped
from pbc.instruments import analog_discovery as ad
from pbc.instruments.conformance import (
    FAILED,
    OFF_FRACTION,
    CallLog,
    Setting,
    amplitude_at,
    check_driver,
)
from pbc.products.physics_lab.protocol import live_envelope, transfer


def _skip_reason() -> str | None:
    """Why the device tests do not run, or None. The SDK is probed in a
    separate process, so that this process never loads it (see ENDING)."""
    if os.environ.get("PBC_LIVE_DEVICE") != "1":
        return "drives a device: set PBC_LIVE_DEVICE=1 with the pilot's circuit wired"
    probe = (
        "import ctypes\n"
        "from pbc.instruments import analog_discovery as ad\n"
        "try:\n    sdk = ad.load_library()\n"
        "except ad.DeviceUnavailable as reason:\n    print(reason); raise SystemExit\n"
        "n = ctypes.c_int(0)\nsdk.FDwfEnum(ctypes.c_int(0), ctypes.byref(n))\n"
        "print('' if n.value else 'no Analog Discovery is connected')\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, timeout=60
    ).stdout.strip()
    return out or None


REASON = _skip_reason()
pytestmark = pytest.mark.skipif(REASON is not None, reason=REASON or "")

AMPLITUDE = 1.0
FREQUENCY = 10_000.0
RATE = 64 * FREQUENCY
SAMPLES = 513
EVIDENCE: dict[str, object] = {}


def report(name: str, value: object) -> None:
    EVIDENCE[name] = value
    print(f"\n[device] {name}: {json.dumps(value)}")


def on_w1(driver: ad.AnalogDiscovery3, frequency: float = FREQUENCY) -> float:
    """The amplitude at ``frequency`` on channel 1 (W1), observed only."""
    capture = driver.capture(64 * frequency, SAMPLES)
    return amplitude_at(capture.channels["source"], capture.t, frequency)


def source_amplitude(capture, frequency: float = FREQUENCY) -> float:
    return amplitude_at(capture.channels["source"], capture.t, frequency)


def make() -> ad.AnalogDiscovery3:
    return ad.AnalogDiscovery3()


def test_the_adapter_passes_the_contract_tests_on_the_device():
    drivers = []

    def fresh():
        for d in drivers:
            d.close()
        drivers.clear()
        drivers.append(make())
        return drivers[0]

    try:
        findings = check_driver(fresh, Setting(AMPLITUDE, FREQUENCY, RATE, SAMPLES))
    finally:
        for d in drivers:
            d.close()
    report("contract", {f.check: f"{f.status}: {f.detail}" for f in findings})
    assert [f for f in findings if f.status == FAILED] == []


def test_the_envelope_refuses_on_the_device_before_anything_reaches_it():
    with make() as driver:
        log = CallLog(driver)
        refused = {}
        for name, envelope, amplitude, frequency in (
            ("amplitude 2.5 V", live_envelope(99.0), 2.5, FREQUENCY),
            ("frequency 250 kHz", live_envelope(99.0), AMPLITUDE, 250_000.0),
            ("2 V into a declared 50 ohm", live_envelope(50.0), 2.0, FREQUENCY),
        ):
            instrument = Instrument(log, envelope)
            with pytest.raises(OutOfEnvelope) as error:
                instrument.excite(amplitude, frequency)
            refused[name] = str(error.value)
        assert log.device_calls() == []
        left = on_w1(driver)
        refused["W1 amplitude after the refusals (V)"] = round(left, 5)
        report("envelope refusal", refused)
        assert left < OFF_FRACTION * AMPLITUDE


def test_a_stop_on_the_device_switches_w1_off_and_a_restart_works():
    with make() as driver:
        instrument = Instrument(driver, live_envelope(99.0))
        instrument.excite(AMPLITUDE, FREQUENCY)
        before = source_amplitude(instrument.acquire(RATE, SAMPLES))
        stopper = threading.Timer(0.0, instrument.request_stop, ("stop pressed",))
        stopper.start()
        stopper.join()
        with pytest.raises(Stopped):
            instrument.excite(AMPLITUDE, FREQUENCY)
        with pytest.raises(Stopped):
            instrument.acquire(RATE, SAMPLES)
        after = on_w1(driver)
    with make() as driver:
        restarted = Instrument(driver, live_envelope(99.0))
        restarted.excite(AMPLITUDE, FREQUENCY)
        again = source_amplitude(restarted.acquire(RATE, SAMPLES))
        restarted.output_off()
    report(
        "stop and restart",
        {
            "W1 before the stop (V)": round(before, 4),
            "W1 after the stop (V)": round(after, 5),
            "W1 after a restart (V)": round(again, 4),
        },
    )
    assert abs(before / AMPLITUDE - 1.0) < 0.1
    assert after < OFF_FRACTION * AMPLITUDE
    assert abs(again / AMPLITUDE - 1.0) < 0.1


NEXT_PROGRAM = """
import ctypes, json, time
from pbc.instruments import analog_discovery as ad
from pbc.instruments.conformance import amplitude_at
sdk = ad.load_library()
started = time.monotonic()
while time.monotonic() - started < 15.0:
    count, opened = ctypes.c_int(0), ctypes.c_int(1)
    sdk.FDwfEnum(ctypes.c_int(0), ctypes.byref(count))
    if count.value:
        sdk.FDwfEnumDeviceIsOpened(ctypes.c_int(0), ctypes.byref(opened))
        if not opened.value:
            break
    time.sleep(0.1)
released = time.monotonic() - started
with ad.AnalogDiscovery3() as d:
    c = d.capture(640000.0, 513)
    seen = amplitude_at(c.channels["source"], c.t, 10000.0)
print(json.dumps({"released after (s)": round(released, 2),
                  "W1 at the next open (V)": round(seen, 5)}))
"""


def next_program() -> dict:
    """What a fresh program finds: how long until the SDK reports the
    device free, and the amplitude on W1 when it opens it. A fresh process,
    because a process that has the SDK loaded can keep a stale view of
    which program holds the device (pilot, 2026-11-22)."""
    out = subprocess.run(
        [sys.executable, "-c", NEXT_PROGRAM],
        check=True, timeout=60, capture_output=True, text=True,
    ).stdout  # fmt: skip
    return json.loads(out.strip().splitlines()[-1])


CONTINUE_AND_CLOSE = """
import ctypes as C
from pbc.instruments import analog_discovery as ad
d = ad.load_library()
d.FDwfParamSet(C.c_int(4), C.c_int(0))  # continue on close
h = C.c_int()
d.FDwfDeviceOpen(C.c_int(0), C.byref(h))
d.FDwfDeviceAutoConfigureSet(h, C.c_int(0))
d.FDwfDeviceParamSet(h, C.c_int(4), C.c_int(0))
d.FDwfAnalogOutNodeEnableSet(h, 0, 0, C.c_int(1))
d.FDwfAnalogOutNodeFunctionSet(h, 0, 0, C.c_ubyte(1))
d.FDwfAnalogOutNodeFrequencySet(h, 0, 0, C.c_double(10000.0))
d.FDwfAnalogOutNodeAmplitudeSet(h, 0, 0, C.c_double(1.0))
d.FDwfAnalogOutConfigure(h, 0, C.c_int(1))
d.FDwfDeviceClose(h)
"""


def test_the_next_program_finds_w1_off_even_after_a_close_with_continue():
    """The control of the next two tests. A program leaves W1 running on
    purpose (DwfParamOnClose continue, through the SDK directly); the next
    program that opens the device finds W1 off (pilot, 2026-11-22). So
    opening the device stops or resets the generator, and what W1 did
    between one program and the next cannot be seen with the AD3 alone: it
    needs an independent observation (decision record, the open cases)."""
    subprocess.run([sys.executable, "-c", CONTINUE_AND_CLOSE], check=True, timeout=30)
    found = next_program()
    report("control: close with continue", found)
    assert found["W1 at the next open (V)"] < OFF_FRACTION * AMPLITUDE


# The ending of a program with W1 on, run from a process that never loads
# the SDK: a parent or grandparent that has the SDK loaded keeps a killed
# child's device opened until that process ends (pilot, 2026-11-22), and
# pytest's process loads it for the tests above. So these cases run from the
# shell, not under pytest:
#
#     PBC_LIVE_DEVICE=1 uv run --locked python \
#         tests/unit/test_analog_discovery_device.py
ENDING = """
import json, signal, subprocess, sys, time
ending, next_program = sys.argv[1], sys.argv[2]
tail = "time.sleep(60)" if ending == "killed" else "sys.exit(0)"
code = ("from pbc.instruments import analog_discovery as ad\\nimport sys, time\\n"
        "d = ad.AnalogDiscovery3()\\nd.set_output(1.0, 10000.0)\\n"
        "print('on', flush=True)\\n" + tail + "\\n")
child = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE,
                         text=True)
assert child.stdout.readline().strip() == "on"
if ending == "killed":
    time.sleep(0.5)
    child.send_signal(signal.SIGKILL)
child.wait(30)
found = subprocess.run([sys.executable, "-c", next_program], check=True,
                       capture_output=True, text=True, timeout=60).stdout
print(json.dumps({"exit code": child.returncode,
                  **json.loads(found.strip().splitlines()[-1])}))
"""


def test_the_round_trips_of_one_point():
    with make() as driver:
        instrument = Instrument(driver, live_envelope(99.0))
        times = {"excite": [], "acquire": []}
        for f in np.geomspace(5_000.0, 200_000.0, 10):
            t0 = time.perf_counter()
            instrument.excite(AMPLITUDE, float(f))
            t1 = time.perf_counter()
            capture = instrument.acquire(64 * float(f), SAMPLES)
            t2 = time.perf_counter()
            transfer(capture, driver.frequency_set_hz)
            times["excite"].append(t1 - t0)
            times["acquire"].append(t2 - t1)
        instrument.output_off()
    summary = {
        k: {"median_ms": round(1e3 * float(np.median(v)), 2),
            "max_ms": round(1e3 * float(np.max(v)), 2)}
        for k, v in times.items()
    }  # fmt: skip
    report("round trips", summary)
    assert summary["acquire"]["max_ms"] < 1e3 * live_envelope(99.0).timeout_s


def endings() -> None:
    """The two endings of a program with W1 on, reported as JSON lines."""
    for ending in ("killed", "exits-without-close"):
        out = subprocess.run(
            [sys.executable, "-c", ENDING, ending, NEXT_PROGRAM],
            check=True, timeout=120, capture_output=True, text=True,
        ).stdout  # fmt: skip
        print(json.dumps({ending: json.loads(out.strip().splitlines()[-1])}))


# The watchdog's case, which only an independent observation can show (the
# pilot found W1 running after kill -9, on the owner's meter, 2026-11-22):
# a program switches W1 on at 2 V, 1 kHz (within the envelope: 20 mA into
# 99 ohm) and is killed; the watchdog must switch W1 off within seconds.
# With a multimeter (V~) across W1 and ground, from the shell:
#
#     PBC_LIVE_DEVICE=1 uv run --locked python \
#         tests/unit/test_analog_discovery_device.py --meter
METER_CHILD = """
from pbc.instruments import Instrument
from pbc.instruments import analog_discovery as ad
from pbc.products.physics_lab.protocol import live_envelope
import time
instrument = Instrument(ad.AnalogDiscovery3(), live_envelope(99.0))
instrument.excite(2.0, 1000.0)
print("on", flush=True)
time.sleep(600)
"""


def meter() -> None:
    """Kill a program with W1 on and print the times for the meter's
    readings; the watchdog's own lines follow on the standard error."""
    import signal

    stamp = lambda: time.strftime("%H:%M:%S")  # noqa: E731
    child = subprocess.Popen(
        [sys.executable, "-c", METER_CHILD], stdout=subprocess.PIPE, text=True
    )
    assert child.stdout is not None and child.stdout.readline().strip() == "on"
    print(f"{stamp()} W1 on at 2 V, 1 kHz: read the meter (the pilot read 0.9 V~)")
    time.sleep(15)
    child.send_signal(signal.SIGKILL)
    child.wait(30)
    print(f"{stamp()} kill -9 of the program (exit {child.returncode})")
    for _ in range(10):
        time.sleep(3)
        print(f"{stamp()} read the meter: the watchdog should have W1 at 0 V~")


if __name__ == "__main__":
    if REASON is not None:
        raise SystemExit(REASON)
    if "--meter" in sys.argv:
        meter()
    else:
        endings()
