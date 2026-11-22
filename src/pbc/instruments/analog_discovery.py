"""The live adapter: a Digilent Analog Discovery 3 through the vendor's
WaveForms SDK (execution mode *live*; F140's physical pilot,
``docs/products.md``).

The bench is the one of the simulated adapter, built by the learner on a
breadboard: the generator W1 drives a series RLC circuit, scope channel 1
reads the source at W1 (channel ``source``) and channel 2 the capacitor
voltage (channel ``response``), both against ground. The adapter is reached
only through ``pbc.instruments.Instrument``, which checks the envelope
before any call arrives here.

The SDK is a C library that the learner installs with WaveForms; it is not a
Python package and is never in the lock. It is loaded with ``ctypes`` from
``PBC_DWF_LIBRARY`` when that is set, otherwise from the vendor's place on
the platform (on macOS ``/Library/Frameworks/dwf.framework/dwf``: the copy
inside ``WaveForms.app`` loads but finds no device). WaveForms itself must
be closed while the adapter holds the device.

What the adapter does for safety, beyond the envelope:

- before the device is opened it sets ``DwfParamOnClose`` to 1, *stop*, so
  that the outputs stop when the program closes the device or ends, instead
  of the vendor's samples' *continue*; ``output_off`` stops the generator
  and is safe at any time and from any thread (each SDK call is serialised,
  never an operation as a whole, so a stop does not wait behind an
  acquisition, and it waits at most ``OFF_LOCK_WAIT_S`` behind a call that
  hangs before it stops the generator anyway);
- an acquisition polls the device under its own deadline, shorter than the
  envelope's timeout, and a failed SDK call is refused with the SDK's
  message (``DeviceError``);
- the input ranges are fixed: channel 1 on the 5 V range (plus or minus
  2.5 V, above the envelope's 2 V), channel 2 on the 50 V range (plus or
  minus 25 V, above the capacitor's Q times the source);
- every opening switches W1 off before anything else, and ``close`` treats
  a device that is lost (a pulled cable) as closed;
- a watchdog process watches the program that holds the device. The pilot
  found that ``DwfParamOnClose`` acts only on a proper close: after
  ``kill -9`` of the program, W1 kept its last output (0.9 V on the owner's
  meter at 2 V, 1 kHz) until the device was opened again (2026-11-22). The
  watchdog never loads the SDK while the program lives; when the program
  ends without closing the device (killed, crashed, ended by a signal), it
  opens the device by its serial, switches W1 off, and closes it
  (``watch``, ``switch_off``; ``python -m pbc.instruments.analog_discovery
  --watchdog SERIAL``). What it cannot cover: a watchdog killed together
  with the program, or a device that does not come back within
  ``WATCHDOG_DEADLINE_S``; the bound is then the last permitted setting,
  inside the envelope, until the device is opened again or unplugged.

The scope's sample clock is 100 MHz divided by a whole number, so a requested
rate is realised to within a fraction of a percent; the capture reports the
realised rate and its sample times, and the protocol reads phasors that do
not span whole periods by a least-squares fit
(``pbc.products.physics_lab.protocol.transfer``).
"""

import atexit
import ctypes
import os
import signal
import subprocess
import sys
import threading
import time
import weakref
from collections.abc import Callable, Iterable, Mapping
from typing import IO, Any

import numpy as np

from pbc.instruments.contract import LIVE, Capture, Refused

ENVIRONMENT = "PBC_DWF_LIBRARY"
LIBRARIES = {
    "darwin": "/Library/Frameworks/dwf.framework/dwf",
    "linux": "libdwf.so",
    "win32": "dwf",
}
INSTALL = {
    "darwin": "install WaveForms, then copy dwf.framework from the WaveForms"
    " installer to /Library/Frameworks (the copy inside WaveForms.app finds no"
    " device), or set PBC_DWF_LIBRARY to the library",
    "linux": "install WaveForms and the Adept runtime, or set PBC_DWF_LIBRARY",
    "win32": "install WaveForms, or set PBC_DWF_LIBRARY to dwf.dll",
}

# The SDK's constants (dwf.h of WaveForms 3.25.1).
PARAM_ON_CLOSE = 4  # DwfParamOnClose: 0 continue, 1 stop, 2 shutdown
ON_CLOSE_STOP = 1
NODE_CARRIER = 0
FUNC_SINE = 1
STATE_DONE = 2
GENERATOR = 0  # W1
SOURCE_CHANNEL = 0  # scope channel 1
RESPONSE_CHANNEL = 1  # scope channel 2
# The input range, peak to peak (V): 5 V is plus or minus 2.5 V, 50 V is
# plus or minus 25 V.
SOURCE_RANGE_V = 5.0
RESPONSE_RANGE_V = 50.0
WARMUP_S = 2.0  # the vendor's samples wait this long for the input offsets
SETTLE_S = 0.01  # after a change of the excitation, before a record starts
POLL_DEADLINE_S = 5.0  # below the bench envelope's 10 s timeout
POLL_INTERVAL_S = 0.001
# output_off waits at most this long for a running SDK call, then stops the
# generator without waiting.
OFF_LOCK_WAIT_S = 0.5
# The watchdog: the line the program sends when it closed the device itself,
# how long the watchdog waits for a dead program's device to come free (the
# pilot: 2 s after kill -9), and how often it looks.
CLOSED = "closed"
WATCHDOG_DEADLINE_S = 60.0
WATCHDOG_POLL_S = 0.5
DISMISS_WAIT_S = 2.0

UNITS = {"t": "s", "source": "V", "response": "V"}
MODULE = "pbc.instruments.analog_discovery"  # the watchdog runs it with -m


class DeviceUnavailable(Refused):
    """The SDK library or the device is not there; the message says what to
    do."""


class DeviceError(Refused):
    """An SDK call that failed, with the SDK's message."""


def library_path(platform: str = sys.platform) -> str:
    """Where the SDK library is loaded from: ``PBC_DWF_LIBRARY`` or the
    vendor's place on ``platform``."""
    return os.environ.get(ENVIRONMENT) or LIBRARIES.get(platform, "libdwf.so")


def load_library(path: str | None = None) -> Any:
    """The SDK library, or ``DeviceUnavailable`` with the installation step."""
    path = path or library_path()
    try:
        return ctypes.cdll.LoadLibrary(path)
    except OSError as error:
        step = INSTALL.get(sys.platform, "install WaveForms")
        raise DeviceUnavailable(
            f"the WaveForms SDK library is not at {path} ({error}); {step}"
        ) from None


def _text(buffer: ctypes.Array) -> str:
    return buffer.value.decode(errors="replace").strip()


def _close_at_exit(reference: weakref.ref) -> None:
    driver = reference()
    if driver is not None:
        driver.close()


def _stop_generator(sdk: Any, handle: ctypes.c_int) -> bool:
    """Stop W1 and disable its carrier; True when the SDK confirms the stop."""
    channel = ctypes.c_int(GENERATOR)
    stopped = sdk.FDwfAnalogOutConfigure(handle, channel, ctypes.c_int(0))
    sdk.FDwfAnalogOutNodeEnableSet(
        handle, channel, ctypes.c_int(NODE_CARRIER), ctypes.c_int(0)
    )
    sdk.FDwfAnalogOutConfigure(handle, channel, ctypes.c_int(0))
    return bool(stopped)


# -- the watchdog ----------------------------------------------------------------


class Watchdog:
    """The watchdog process of one opened device: it switches W1 off when
    this program ends without ``dismiss``. It is started in its own session,
    so that a Ctrl-C or a hang-up of the terminal does not end it with the
    program, and it reads the program's end from its standard input: the
    pipe closes when the program's process ends, however it ends."""

    def __init__(self, serial: str, library: str, stderr: IO | int | None = None):
        self.process = subprocess.Popen(
            [sys.executable, "-m", MODULE, "--watchdog", serial,
             "--library", library],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=stderr,
            text=True, start_new_session=True,
        )  # fmt: skip

    def dismiss(self) -> None:
        """The program closed the device itself: the watchdog ends."""
        stdin = self.process.stdin
        try:
            if stdin is not None:
                stdin.write(CLOSED + "\n")
                stdin.close()
        except BrokenPipeError, OSError, ValueError:
            pass  # a watchdog that has ended has nothing to do
        try:
            self.process.wait(DISMISS_WAIT_S)
        except subprocess.TimeoutExpired:
            self.process.kill()


def watch(lines: Iterable[str], switch: Callable[[], None]) -> str:
    """Wait for the program: ``dismissed`` when it reports that it closed
    the device, otherwise, when its lines end (the program's process ended),
    ``switch`` W1 off and ``switched off``."""
    for line in lines:
        if line.strip() == CLOSED:
            return "dismissed"
    switch()
    return "switched off"


def switch_off(
    sdk: Any,
    serial: str,
    *,
    deadline_s: float = WATCHDOG_DEADLINE_S,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> None:
    """Open the device with ``serial`` once the ended program has released
    it, stop W1, and close it (with ``DwfParamOnClose`` stop). A device that
    is not there, or not free, within ``deadline_s`` is refused with
    ``DeviceUnavailable``: the watchdog says so, and only opening the
    device again or unplugging it then stops W1."""
    sdk.FDwfParamSet(ctypes.c_int(PARAM_ON_CLOSE), ON_CLOSE_STOP)
    end = clock() + deadline_s
    seen = "not found"
    while True:
        count = ctypes.c_int(0)
        sdk.FDwfEnum(ctypes.c_int(0), ctypes.byref(count))
        for index in range(count.value):
            number = ctypes.create_string_buffer(32)
            sdk.FDwfEnumSN(ctypes.c_int(index), number)
            if _text(number) != serial:
                continue
            opened = ctypes.c_int(0)
            sdk.FDwfEnumDeviceIsOpened(ctypes.c_int(index), ctypes.byref(opened))
            seen = "still opened"
            if opened.value:
                break
            handle = ctypes.c_int(0)
            if sdk.FDwfDeviceOpen(ctypes.c_int(index), ctypes.byref(handle)) and (
                handle.value
            ):
                sdk.FDwfDeviceAutoConfigureSet(handle, ctypes.c_int(0))
                sdk.FDwfDeviceParamSet(
                    handle, ctypes.c_int(PARAM_ON_CLOSE), ON_CLOSE_STOP
                )
                stopped = _stop_generator(sdk, handle)
                sdk.FDwfDeviceClose(handle)
                if stopped:
                    return
            break
        if clock() > end:
            raise DeviceUnavailable(
                f"the device {serial} was {seen} for {deadline_s:g} s: W1 may"
                " still run; open the lab again or unplug the USB cable"
            )
        sleep(WATCHDOG_POLL_S)


def watchdog_main(arguments: list[str], stdin: IO[str] = sys.stdin) -> int:
    """The watchdog process: ``--watchdog SERIAL [--library PATH]``."""
    serial = arguments[arguments.index("--watchdog") + 1]
    library = (
        arguments[arguments.index("--library") + 1]
        if "--library" in arguments
        else library_path()
    )
    for name in ("SIGINT", "SIGHUP", "SIGTERM"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), signal.SIG_IGN)

    def switch() -> None:
        print(
            f"watchdog: the program ended without closing {serial};"
            " switching W1 off",
            file=sys.stderr, flush=True,
        )  # fmt: skip
        switch_off(load_library(library), serial)
        print(f"watchdog: W1 of {serial} is off", file=sys.stderr, flush=True)

    try:
        watch(stdin, switch)
    except DeviceUnavailable as reason:
        print(f"watchdog: {reason}", file=sys.stderr, flush=True)
        return 1
    return 0


class AnalogDiscovery3:
    """A driver over an Analog Discovery 3. ``sdk`` is the loaded library
    (a stand-in in the tests); ``sleep`` and ``clock`` are injectable for
    the same reason. The device is opened here and closed by ``close``."""

    mode = LIVE

    def __init__(
        self,
        sdk: Any = None,
        *,
        device_index: int = 0,
        warmup_s: float = WARMUP_S,
        settle_s: float = SETTLE_S,
        poll_deadline_s: float = POLL_DEADLINE_S,
        library: str | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        watchdog: Callable[[str, str], Any] | bool | None = True,
    ):
        """``watchdog`` starts the watchdog of the opened device from its
        serial and the library (``Watchdog``); ``True`` means ``Watchdog``
        when the adapter loads the SDK itself and none on a stand-in."""
        self.library = library or library_path()
        if watchdog is True:
            watchdog = Watchdog if sdk is None else None
        self._sdk = sdk if sdk is not None else load_library(self.library)
        self._sleep = sleep
        self._clock = clock
        self.settle_s = settle_s
        self.poll_deadline_s = poll_deadline_s
        self._calls = threading.Lock()  # one SDK call at a time
        self._handle = ctypes.c_int(0)
        self._amplitude = 0.0
        self._frequency = 0.0
        self._changed = clock()
        self._watchdog: Any = None
        self.lost: str | None = None  # why a close found the device lost
        self._identity = self._open(device_index)
        if watchdog:
            try:
                self._watchdog = watchdog(self._identity["serial"], self.library)
            except OSError as error:
                self.close()
                raise DeviceError(f"the watchdog did not start: {error}") from None
        # A program that ends without close crashed at the interpreter's exit
        # with the device open (SIGSEGV, pilot 2026-11-22): it is closed at
        # exit, output off first.
        atexit.register(_close_at_exit, weakref.ref(self))
        self._configure_inputs()
        sleep(warmup_s)

    # -- opening and closing ---------------------------------------------------

    def _sdk_call(self, name: str, *arguments: Any) -> None:
        """One SDK call, serialised; a failure is refused with its message."""
        with self._calls:
            ok = getattr(self._sdk, name)(*arguments)
        if not ok:
            raise DeviceError(f"{name} failed: {self._last_error()}")

    def _last_error(self) -> str:
        message = ctypes.create_string_buffer(512)
        self._sdk.FDwfGetLastErrorMsg(message)
        return _text(message) or "no message from the SDK"

    def _open(self, index: int) -> dict[str, str]:
        sdk = self._sdk
        version = ctypes.create_string_buffer(32)
        sdk.FDwfGetVersion(version)
        # Stop the outputs when the device is closed or the program ends.
        self._sdk_call("FDwfParamSet", ctypes.c_int(PARAM_ON_CLOSE), ON_CLOSE_STOP)
        count = ctypes.c_int(0)
        self._sdk_call("FDwfEnum", ctypes.c_int(0), ctypes.byref(count))
        if not 0 <= index < count.value:
            raise DeviceUnavailable(
                f"no Analog Discovery at index {index}: the SDK finds"
                f" {count.value} device(s); connect it by USB and close WaveForms"
            )
        name = ctypes.create_string_buffer(32)
        serial = ctypes.create_string_buffer(32)
        sdk.FDwfEnumDeviceName(ctypes.c_int(index), name)
        sdk.FDwfEnumSN(ctypes.c_int(index), serial)
        opened = ctypes.c_int(0)
        sdk.FDwfEnumDeviceIsOpened(ctypes.c_int(index), ctypes.byref(opened))
        if opened.value:
            raise DeviceUnavailable(
                f"{_text(name)} is opened by another program; close WaveForms"
            )
        with self._calls:
            ok = sdk.FDwfDeviceOpen(ctypes.c_int(index), ctypes.byref(self._handle))
        if not ok or self._handle.value == 0:
            raise DeviceUnavailable(f"the device did not open: {self._last_error()}")
        h = self._handle
        self._sdk_call("FDwfDeviceAutoConfigureSet", h, ctypes.c_int(0))
        self._sdk_call(
            "FDwfDeviceParamSet", h, ctypes.c_int(PARAM_ON_CLOSE), ON_CLOSE_STOP
        )
        # W1 off first: a program that was killed leaves W1 running until the
        # device is opened again (pilot, 2026-11-22).
        with self._calls:
            stopped = _stop_generator(sdk, h)
        if not stopped:
            with self._calls:
                sdk.FDwfDeviceClose(h)
            self._handle = ctypes.c_int(0)
            raise DeviceError(
                "the generator did not confirm the stop at opening:"
                f" {self._last_error()}"
            )
        return {
            "device": f"Digilent {_text(name)}",
            "serial": _text(serial),
            "sdk": f"WaveForms SDK {_text(version)}",
            "library": self.library,
            "calibration": "the device's factory calibration, not adjusted;"
            f" channel 1 (source) on the {SOURCE_RANGE_V:g} V range, channel 2"
            f" (response) on the {RESPONSE_RANGE_V:g} V range, both against"
            " ground; the generator W1, sine, offset 0 V",
            "on_close": "stop",
        }

    def _configure_inputs(self) -> None:
        h = self._handle
        for channel, span in (
            (SOURCE_CHANNEL, SOURCE_RANGE_V),
            (RESPONSE_CHANNEL, RESPONSE_RANGE_V),
        ):
            self._sdk_call(
                "FDwfAnalogInChannelEnableSet",
                h,
                ctypes.c_int(channel),
                ctypes.c_int(1),
            )
            self._sdk_call(
                "FDwfAnalogInChannelRangeSet",
                h,
                ctypes.c_int(channel),
                ctypes.c_double(span),
            )
            self._sdk_call(
                "FDwfAnalogInChannelOffsetSet",
                h,
                ctypes.c_int(channel),
                ctypes.c_double(0.0),
            )
        self._sdk_call("FDwfAnalogInConfigure", h, ctypes.c_int(1), ctypes.c_int(0))

    def close(self) -> None:
        """Switch the output off and close the device. Safe to repeat. A
        device that no longer answers (a pulled cable: the pilot's stop
        failed with "did not confirm") counts as closed, its reason is kept
        in ``lost``, and the watchdog stays to stop W1 if the device comes
        back within its deadline."""
        if self._handle.value == 0:
            return
        try:
            self.output_off()
        except DeviceError as error:
            self.lost = str(error)
        finally:
            with self._calls:
                self._sdk.FDwfDeviceClose(self._handle)
            self._handle = ctypes.c_int(0)
            if self._watchdog is not None and self.lost is None:
                self._watchdog.dismiss()
            self._watchdog = None

    def __enter__(self) -> AnalogDiscovery3:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @property
    def is_open(self) -> bool:
        return self._handle.value != 0

    # -- the driver protocol ---------------------------------------------------

    def identity(self) -> Mapping[str, str]:
        identity = dict(self._identity)
        if self._frequency:
            identity["frequency_set_hz"] = f"{self._frequency:.12g}"
        return identity

    def set_output(self, amplitude_v: float, frequency_hz: float) -> None:
        if not self.is_open:
            raise DeviceError("the device is closed")
        h, ch, node = self._handle, ctypes.c_int(GENERATOR), ctypes.c_int(NODE_CARRIER)
        self._sdk_call("FDwfAnalogOutNodeEnableSet", h, ch, node, ctypes.c_int(1))
        self._sdk_call(
            "FDwfAnalogOutNodeFunctionSet", h, ch, node, ctypes.c_ubyte(FUNC_SINE)
        )
        self._sdk_call(
            "FDwfAnalogOutNodeFrequencySet", h, ch, node, ctypes.c_double(frequency_hz)
        )
        self._sdk_call(
            "FDwfAnalogOutNodeAmplitudeSet", h, ch, node, ctypes.c_double(amplitude_v)
        )
        self._sdk_call("FDwfAnalogOutNodeOffsetSet", h, ch, node, ctypes.c_double(0.0))
        self._sdk_call("FDwfAnalogOutConfigure", h, ch, ctypes.c_int(1))
        realised = ctypes.c_double(0.0)
        self._sdk_call(
            "FDwfAnalogOutNodeFrequencyGet", h, ch, node, ctypes.byref(realised)
        )
        self._amplitude = float(amplitude_v)
        self._frequency = realised.value or float(frequency_hz)
        self._changed = self._clock()

    def output_off(self) -> None:
        """Stop the generator W1. Safe before any output, after close, twice,
        and from another thread."""
        self._amplitude = 0.0
        self._changed = self._clock()
        if not self.is_open:
            return
        h = self._handle
        # Wait briefly for a running SDK call (milliseconds on the device);
        # one that hangs does not keep the output on: the stop goes anyway.
        locked = self._calls.acquire(timeout=OFF_LOCK_WAIT_S)
        try:
            stopped = _stop_generator(self._sdk, h)
        finally:
            if locked:
                self._calls.release()
        if not stopped:
            raise DeviceError(
                f"the generator did not confirm the stop: {self._last_error()}"
            )

    @property
    def frequency_set_hz(self) -> float:
        """The generator's frequency as the SDK reports it set."""
        return self._frequency

    def capture(self, sample_rate_hz: float, samples: int) -> Capture:
        if not self.is_open:
            raise DeviceError("the device is closed")
        h = self._handle
        self._sdk_call("FDwfAnalogInFrequencySet", h, ctypes.c_double(sample_rate_hz))
        self._sdk_call("FDwfAnalogInBufferSizeSet", h, ctypes.c_int(samples))
        self._sdk_call("FDwfAnalogInConfigure", h, ctypes.c_int(1), ctypes.c_int(0))
        realised = ctypes.c_double(0.0)
        self._sdk_call("FDwfAnalogInFrequencyGet", h, ctypes.byref(realised))
        rate = realised.value
        if not rate > 0:
            raise DeviceError("the device reported no sample rate")
        wait = self.settle_s - (self._clock() - self._changed)
        if wait > 0:
            self._sleep(wait)
        self._sdk_call("FDwfAnalogInConfigure", h, ctypes.c_int(0), ctypes.c_int(1))
        deadline = self._clock() + self.poll_deadline_s
        state = ctypes.c_ubyte(0)
        while True:
            self._sdk_call(
                "FDwfAnalogInStatus", h, ctypes.c_int(1), ctypes.byref(state)
            )
            if state.value == STATE_DONE:
                break
            if self._clock() > deadline:
                raise DeviceError(
                    f"the acquisition did not finish within {self.poll_deadline_s:g} s"
                )
            self._sleep(POLL_INTERVAL_S)
        channels = {}
        for name, channel in (
            ("source", SOURCE_CHANNEL),
            ("response", RESPONSE_CHANNEL),
        ):
            buffer = (ctypes.c_double * samples)()
            self._sdk_call(
                "FDwfAnalogInStatusData",
                h,
                ctypes.c_int(channel),
                buffer,
                ctypes.c_int(samples),
            )
            channels[name] = np.array(buffer, dtype=float)
        return Capture(
            sample_rate_hz=rate,
            t=np.arange(samples) / rate,
            channels=channels,
            units=UNITS,
        )

    # -- the operating conditions ----------------------------------------------

    def conditions(self) -> dict[str, float]:
        """The device's own monitor: temperatures (degrees C) and the USB and
        auxiliary supply (V, A), for the run record's operating conditions.
        A powered auxiliary supply means that a pulled USB cable does not
        remove the power (docs/products.md, the desk spike)."""
        h = self._handle
        self._sdk_call("FDwfAnalogIOStatus", h)
        names = {
            "pcb_temperature_c": (2, 0),
            "die_temperature_c": (2, 1),
            "usb_voltage_v": (2, 2),
            "usb_current_a": (2, 3),
            "aux_voltage_v": (2, 4),
            "aux_current_a": (2, 5),
        }
        values = {}
        for key, (channel, node) in names.items():
            value = ctypes.c_double(0.0)
            self._sdk_call(
                "FDwfAnalogIOChannelNodeStatus",
                h,
                ctypes.c_int(channel),
                ctypes.c_int(node),
                ctypes.byref(value),
            )
            values[key] = float(value.value)
        return values


if __name__ == "__main__":
    if "--watchdog" not in sys.argv:
        raise SystemExit(
            f"usage: python -m {MODULE} --watchdog SERIAL [--library PATH]"
        )
    raise SystemExit(watchdog_main(sys.argv[1:]))
