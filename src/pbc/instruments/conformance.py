"""The contract tests that every adapter passes, whatever its execution mode
(F142, the lesson "Connecting simulators and instruments"; ADR 022 decision
5, invariant I34).

A program that measures through an ``Instrument`` does not know which adapter
is below it. It relies on the same things from each: the adapter says what it
is and how it is calibrated, its output can be switched off at any time and
then is off, an acquisition has the length, the times, and the units it was
asked for, and the excitation that was set is the one on the source channel.
The ``Instrument`` adds the envelope and the stop, which hold whatever the
adapter is. ``check_driver`` runs every check on fresh adapters from a factory
and returns one ``Finding`` for each; the simulated, the recorded, and the
channel adapters pass them, and so must the optional live adapter (F140)
before anyone relies on it. Passing them is not a demonstration on a device.

The checks are written for the two-channel bench of the frequency-response
protocol: a ``source`` and a ``response`` channel in volts.

The waveform checks (F145, ``check_waveforms``) are apart from ``CHECKS``:
an adapter that declares the square wave outputs it between 0 V and the
amplitude on the source channel, and a waveform the envelope does not
permit, or the adapter does not declare, is refused before the adapter is
called.
"""

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np

from pbc.instruments.contract import (
    LIVE,
    MODES,
    SINE,
    SQUARE,
    Capture,
    Driver,
    Envelope,
    Instrument,
    Limit,
    OutOfEnvelope,
    Refused,
    Stopped,
    driver_waveforms,
)

PASSED = "passed"
FAILED = "failed"
NOT_APPLICABLE = "not applicable"
CHANNELS = ("source", "response")
# The excitation on the source channel is the one set within this fraction.
EXCITATION_TOLERANCE = 0.1
# A device with a divided sample clock realises a rate near the one asked
# (F140: the AD3's scope runs at 100 MHz over an integer); it reports the
# realised rate, within this fraction of the request, and its sample times
# follow it.
REALISED_RATE_TOLERANCE = 0.01
# After the output is off, what remains on the source channel at the old
# frequency is below this fraction of the old amplitude.
OFF_FRACTION = 0.05


@dataclass(frozen=True)
class Setting:
    """One operation of the bench: the excitation (V, Hz) and the
    acquisition (samples/s, samples)."""

    amplitude_v: float
    frequency_hz: float
    sample_rate_hz: float
    samples: int


@dataclass(frozen=True)
class Finding:
    """The outcome of one check on one adapter, with what it saw."""

    check: str
    status: str
    detail: str


class CallLog:
    """A driver that passes every call on to another and records it, so
    that what reached the adapter can be shown. ``output_off`` is recorded
    too; ``device_calls`` leaves it out, since it is always permitted."""

    def __init__(self, driver: Driver):
        self.driver = driver
        self.mode = driver.mode
        self.waveforms = driver_waveforms(driver)
        self.calls: list[tuple[Any, ...]] = []

    def identity(self) -> Mapping[str, str]:
        return self.driver.identity()

    def set_output(
        self, amplitude_v: float, frequency_hz: float, waveform: str = SINE
    ) -> None:
        if waveform == SINE:
            self.calls.append(("set_output", amplitude_v, frequency_hz))
            self.driver.set_output(amplitude_v, frequency_hz)
        else:
            self.calls.append(("set_output", amplitude_v, frequency_hz, waveform))
            self.driver.set_output(amplitude_v, frequency_hz, waveform=waveform)  # type: ignore[call-arg]

    def output_off(self) -> None:
        self.calls.append(("output_off",))
        self.driver.output_off()

    def capture(self, sample_rate_hz: float, samples: int) -> Capture:
        self.calls.append(("capture", sample_rate_hz, samples))
        return self.driver.capture(sample_rate_hz, samples)

    def device_calls(self) -> list[tuple[Any, ...]]:
        return [call for call in self.calls if call[0] != "output_off"]


def amplitude_at(signal: np.ndarray, t: np.ndarray, frequency_hz: float) -> float:
    """The amplitude of the component of ``signal`` at ``frequency_hz``, by a
    least-squares fit of a cosine, a sine, and a constant; samples that are
    not a number (lost) are left out."""
    keep = np.isfinite(signal)
    omega = 2.0 * math.pi * frequency_hz
    design = np.column_stack(
        [np.cos(omega * t[keep]), np.sin(omega * t[keep]), np.ones(keep.sum())]
    )
    (a, b, _), *_ = np.linalg.lstsq(design, signal[keep], rcond=None)
    return float(math.hypot(a, b))


def _identity(make: Callable[[], Driver], setting: Setting) -> Finding:
    identity = make().identity()
    missing = [k for k in ("device", "calibration") if not str(identity.get(k, ""))]
    if missing:
        return Finding("identity", FAILED, f"the identity does not name {missing}")
    return Finding("identity", PASSED, f"device: {identity['device']}")


def _mode(make: Callable[[], Driver], setting: Setting) -> Finding:
    mode = make().mode
    if mode not in MODES:
        return Finding("mode", FAILED, f"{mode!r} is not one of {MODES}")
    return Finding("mode", PASSED, f"mode {mode}")


def _off_at_any_time(make: Callable[[], Driver], setting: Setting) -> Finding:
    driver = make()
    try:
        driver.output_off()
        driver.output_off()
    except Exception as error:  # the check reports any failure
        return Finding("output-off-at-any-time", FAILED, f"raised {error!r}")
    return Finding("output-off-at-any-time", PASSED, "before any output, and twice")


def _acquire(make: Callable[[], Driver], setting: Setting) -> tuple[Driver, Capture]:
    driver = make()
    driver.set_output(setting.amplitude_v, setting.frequency_hz)
    return driver, driver.capture(setting.sample_rate_hz, setting.samples)


def _capture_shape(make: Callable[[], Driver], setting: Setting) -> Finding:
    _, capture = _acquire(make, setting)
    n, asked = setting.samples, setting.sample_rate_hz
    rate = capture.sample_rate_hz
    problems = []
    if not abs(rate / asked - 1.0) <= REALISED_RATE_TOLERANCE:
        problems.append(
            f"sample rate {rate:g}, asked {asked:g}: more than"
            f" {REALISED_RATE_TOLERANCE:.0%} apart"
        )
    if len(capture.t) != n or not np.allclose(capture.t, np.arange(n) / rate):
        problems.append("the sample times are not n / rate from zero")
    if set(capture.channels) != set(CHANNELS):
        problems.append(f"channels {sorted(capture.channels)}, not {list(CHANNELS)}")
    for name, values in capture.channels.items():
        values = np.asarray(values, dtype=float)
        if len(values) != n:
            problems.append(f"{name} has {len(values)} samples, not {n}")
        elif np.isinf(values).any():
            problems.append(f"{name} holds an infinite value")
    if problems:
        return Finding("capture-shape", FAILED, "; ".join(problems))
    realised = "" if rate == asked else f" (realised; {asked:g} asked)"
    return Finding(
        "capture-shape", PASSED, f"{n} samples at {rate:g} samples/s{realised}"
    )


def _units(make: Callable[[], Driver], setting: Setting) -> Finding:
    _, capture = _acquire(make, setting)
    expected = {"t": "s", **{name: "V" for name in CHANNELS}}
    units = dict(capture.units)
    wrong = {k: units.get(k) for k, v in expected.items() if units.get(k) != v}
    if wrong:
        return Finding("units", FAILED, f"units {wrong}, expected {expected}")
    return Finding("units", PASSED, "t in s, source and response in V")


def _excitation(make: Callable[[], Driver], setting: Setting) -> Finding:
    _, capture = _acquire(make, setting)
    found = amplitude_at(
        np.asarray(capture.channels["source"], dtype=float),
        np.asarray(capture.t, dtype=float),
        setting.frequency_hz,
    )
    ratio = found / setting.amplitude_v
    detail = (
        f"{found:.3f} V at {setting.frequency_hz:g} Hz on the source channel,"
        f" {setting.amplitude_v:g} V set"
    )
    if abs(ratio - 1.0) > EXCITATION_TOLERANCE:
        return Finding("excitation-on-source", FAILED, detail)
    return Finding("excitation-on-source", PASSED, detail)


def _off_means_off(make: Callable[[], Driver], setting: Setting) -> Finding:
    driver, _ = _acquire(make, setting)
    driver.output_off()
    try:
        capture = driver.capture(setting.sample_rate_hz, setting.samples)
    except Refused as error:
        return Finding("output-off-stops-excitation", PASSED, f"refused: {error}")
    left = amplitude_at(
        np.asarray(capture.channels["source"], dtype=float),
        np.asarray(capture.t, dtype=float),
        setting.frequency_hz,
    )
    detail = f"{left:.3f} V left at {setting.frequency_hz:g} Hz after output_off"
    if left > OFF_FRACTION * setting.amplitude_v:
        return Finding("output-off-stops-excitation", FAILED, detail)
    return Finding("output-off-stops-excitation", PASSED, detail)


def _repeatable(make: Callable[[], Driver], setting: Setting) -> Finding:
    if make().mode == LIVE:
        return Finding("repeatable", NOT_APPLICABLE, "a live device is not repeatable")
    first = _acquire(make, setting)[1].channels
    second = _acquire(make, setting)[1].channels
    same = all(
        np.array_equal(np.asarray(first[k]), np.asarray(second[k]), equal_nan=True)
        for k in CHANNELS
    )
    if not same:
        return Finding("repeatable", FAILED, "a fresh adapter gave other samples")
    return Finding("repeatable", PASSED, "a fresh adapter gave the same samples")


def _envelope(setting: Setting) -> Envelope:
    """An envelope around ``setting``: twice its amplitude, a decade of
    frequency either side, its sample rate, and its number of samples."""
    return Envelope(
        amplitude=Limit("excitation amplitude", "V", 0.0, 2.0 * setting.amplitude_v),
        frequency=Limit(
            "excitation frequency",
            "Hz",
            setting.frequency_hz / 10.0,
            setting.frequency_hz * 10.0,
        ),
        sample_rate=Limit(
            "sample rate", "samples/s", setting.sample_rate_hz, setting.sample_rate_hz
        ),
        samples=Limit("samples", "samples", 1, setting.samples, integer=True),
        timeout_s=10.0,
    )


def _envelope_before_driver(make: Callable[[], Driver], setting: Setting) -> Finding:
    log = CallLog(make())
    instrument = Instrument(log, _envelope(setting))
    try:
        instrument.excite(3.0 * setting.amplitude_v, setting.frequency_hz)
    except OutOfEnvelope:
        pass
    else:
        return Finding("envelope-before-adapter", FAILED, "the excitation was accepted")
    if log.device_calls():
        return Finding(
            "envelope-before-adapter", FAILED, f"the adapter saw {log.device_calls()}"
        )
    return Finding(
        "envelope-before-adapter", PASSED, "refused; the adapter received nothing"
    )


def _stop(make: Callable[[], Driver], setting: Setting) -> Finding:
    log = CallLog(make())
    instrument = Instrument(log, _envelope(setting))
    instrument.excite(setting.amplitude_v, setting.frequency_hz)
    instrument.request_stop("stop requested by the check")
    before = list(log.device_calls())
    try:
        instrument.excite(setting.amplitude_v, setting.frequency_hz)
    except Stopped:
        pass
    else:
        return Finding("stop", FAILED, "an operation after the stop was accepted")
    if log.device_calls() != before or log.calls[-1] != ("output_off",):
        return Finding("stop", FAILED, "the adapter was called after the stop")
    return Finding("stop", PASSED, "output off at once; later operations refused")


CHECKS: tuple[tuple[str, Callable[[Callable[[], Driver], Setting], Finding]], ...] = (
    ("mode", _mode),
    ("identity", _identity),
    ("output-off-at-any-time", _off_at_any_time),
    ("capture-shape", _capture_shape),
    ("units", _units),
    ("excitation-on-source", _excitation),
    ("output-off-stops-excitation", _off_means_off),
    ("repeatable", _repeatable),
    ("envelope-before-adapter", _envelope_before_driver),
    ("stop", _stop),
)


def check_driver(make: Callable[[], Driver], setting: Setting) -> list[Finding]:
    """Every contract check on fresh adapters from ``make``, at ``setting``
    (one the adapter can answer: a recorded one must hold it). A check
    that raises is a failed check, with the error as its detail."""
    findings = []
    for name, check in CHECKS:
        try:
            findings.append(check(make, setting))
        except Exception as error:  # the check reports any failure
            findings.append(Finding(name, FAILED, f"raised {error!r}"))
    return findings


# -- the waveform checks (F145) ------------------------------------------------

# The levels of the square wave on the source channel are within this
# fraction of the amplitude of 0 V and of the amplitude.
SQUARE_LEVEL_TOLERANCE = 0.05


@dataclass(frozen=True)
class SquareSetting:
    """One square-wave operation of the bench: the amplitude (V), the
    frequency (Hz), and an acquisition (samples/s, samples) that spans at
    least one whole period."""

    amplitude_v: float
    frequency_hz: float
    sample_rate_hz: float
    samples: int


def _square_envelope(setting: SquareSetting, waveforms: tuple[str, ...]) -> Envelope:
    return Envelope(
        amplitude=Limit("excitation amplitude", "V", 0.0, 2.0 * setting.amplitude_v),
        frequency=Limit(
            "excitation frequency",
            "Hz",
            setting.frequency_hz / 10.0,
            setting.frequency_hz * 10.0,
        ),
        sample_rate=Limit(
            "sample rate", "samples/s", setting.sample_rate_hz, setting.sample_rate_hz
        ),
        samples=Limit("samples", "samples", 1, setting.samples, integer=True),
        timeout_s=10.0,
        waveforms=waveforms,
    )


def _square_on_source(make: Callable[[], Driver], setting: SquareSetting) -> Finding:
    name = "square-on-source"
    driver = make()
    if SQUARE not in driver_waveforms(driver):
        return Finding(name, NOT_APPLICABLE, "the adapter declares no square wave")
    driver.set_output(setting.amplitude_v, setting.frequency_hz, waveform=SQUARE)  # type: ignore[call-arg]
    capture = driver.capture(setting.sample_rate_hz, setting.samples)
    driver.output_off()
    source = np.asarray(capture.channels["source"], dtype=float)
    source = source[np.isfinite(source)]
    a = setting.amplitude_v
    low, high = float(np.percentile(source, 10)), float(np.percentile(source, 90))
    detail = (
        f"levels {low:.3f} V and {high:.3f} V on the source channel, 0 V and"
        f" {a:g} V set"
    )
    tolerance = SQUARE_LEVEL_TOLERANCE * a
    if abs(low) > tolerance or abs(high - a) > tolerance:
        return Finding(name, FAILED, detail)
    if source.min() < -tolerance or source.max() > a + tolerance:
        return Finding(name, FAILED, detail + "; a sample beyond 0 V to the amplitude")
    return Finding(name, PASSED, detail)


def _waveform_before_adapter(
    make: Callable[[], Driver], setting: SquareSetting
) -> Finding:
    name = "waveform-before-adapter"
    log = CallLog(make())
    instrument = Instrument(log, _square_envelope(setting, (SINE,)))
    try:
        instrument.excite(setting.amplitude_v, setting.frequency_hz, SQUARE)
    except OutOfEnvelope:
        pass
    else:
        return Finding(name, FAILED, "a square wave the envelope does not permit")
    if log.device_calls():
        return Finding(name, FAILED, f"the adapter saw {log.device_calls()}")
    return Finding(
        name, PASSED, "a waveform the envelope does not permit; nothing reached it"
    )


def _undeclared_waveform(make: Callable[[], Driver], setting: SquareSetting) -> Finding:
    name = "undeclared-waveform"
    driver = make()
    if SQUARE in driver_waveforms(driver):
        return Finding(name, NOT_APPLICABLE, "the adapter declares the square wave")
    log = CallLog(driver)
    instrument = Instrument(log, _square_envelope(setting, (SINE, SQUARE)))
    try:
        instrument.excite(setting.amplitude_v, setting.frequency_hz, SQUARE)
    except Refused:
        pass
    else:
        return Finding(name, FAILED, "an undeclared square wave was accepted")
    if log.device_calls():
        return Finding(name, FAILED, f"the adapter saw {log.device_calls()}")
    return Finding(name, PASSED, "refused before the adapter was called")


WAVEFORM_CHECKS: tuple[
    tuple[str, Callable[[Callable[[], Driver], SquareSetting], Finding]], ...
] = (
    ("square-on-source", _square_on_source),
    ("waveform-before-adapter", _waveform_before_adapter),
    ("undeclared-waveform", _undeclared_waveform),
)


def check_waveforms(
    make: Callable[[], Driver], setting: SquareSetting
) -> list[Finding]:
    """The waveform checks on fresh adapters from ``make`` at ``setting``
    (a recorded adapter must hold the square-wave capture). A check that
    raises is a failed check, with the error as its detail."""
    findings = []
    for name, check in WAVEFORM_CHECKS:
        try:
            findings.append(check(make, setting))
        except Exception as error:  # the check reports any failure
            findings.append(Finding(name, FAILED, f"raised {error!r}"))
    return findings
