"""The instrument contract: the one object a caller gets, and the safety
envelope it enforces before anything reaches a device (ADR 022 decision 5,
invariant I34).

A device is reached through a ``Driver``, the adapter of one execution mode
(simulated, recorded, live). No caller holds a driver: a caller, the scripted
baseline, the agent's tools, or the local interface, holds an ``Instrument``,
which

- validates every operation against the ``Envelope`` (the permitted range of
  each quantity, with its unit) and its interlocks before the driver is
  called, so that an out-of-envelope operation never reaches the device;
- runs each driver call under the envelope's timeout: a call that does not
  return in time is refused, the output is switched off, and the instrument
  is faulted until it is made again;
- honours a stop request from any thread: the output is switched off at once
  and every later operation is refused. The halt is checked again after the
  operation lock is taken and right before each driver call, and after a
  driver call returns: a stop or timeout that landed meanwhile switches the
  output off again, so that ``output_off`` is the driver's last call, also
  when a timed-out call returns late;
- gives a snapshot of its state, and the run record that names the
  execution mode (``InstrumentRun``).

The limits are enforced here, in code, never in a prompt or a tool
description, so that they hold whatever the caller is.
"""

import math
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray

SIMULATED = "simulated"
RECORDED = "recorded"
LIVE = "live"
# The three execution modes (requirements, "Data and persistence").
MODES = (SIMULATED, RECORDED, LIVE)

_LABELS = {
    SIMULATED: "simulated experiment on a deterministic model, not a measurement",
    RECORDED: "recorded data replayed from a declared sample, not a new experiment",
    LIVE: "live measurement on the learner's own instrument",
}


class Refused(RuntimeError):
    """An operation the instrument did not perform, with the reason."""


class OutOfEnvelope(Refused):
    """A value outside the permitted range of its quantity."""


class InterlockOpen(Refused):
    """An interlock that does not permit the operation."""


class InstrumentTimeout(Refused):
    """A driver call that did not return within the envelope's timeout."""


class Stopped(Refused):
    """An operation after a stop request or a fault."""


@dataclass(frozen=True)
class Limit:
    """The permitted range of one quantity, inclusive, in its unit."""

    quantity: str
    unit: str
    low: float
    high: float
    integer: bool = False

    def __post_init__(self):
        if not self.low <= self.high:
            raise ValueError(f"{self.quantity}: low {self.low} above high {self.high}")

    def check(self, value: Any) -> float:
        """``value`` when it is a finite number within the range; otherwise
        raise ``OutOfEnvelope``."""
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise OutOfEnvelope(f"{self.quantity} must be a number")
        # Finiteness first: int() of NaN or infinity raises, and every
        # refusal must come as OutOfEnvelope.
        if not math.isfinite(value) or not self.low <= value <= self.high:
            raise OutOfEnvelope(
                f"{self.quantity} {value:g} {self.unit} is outside the permitted"
                f" range {self.low:g} to {self.high:g} {self.unit}"
            )
        if self.integer and value != int(value):
            raise OutOfEnvelope(f"{self.quantity} must be a whole number")
        return value


@dataclass(frozen=True)
class Interlock:
    """A condition that must hold before the output is switched on, for
    example that the learner confirmed the prepared circuit. ``closed``
    answers whether it permits the operation now."""

    name: str
    description: str
    closed: Callable[[], bool]


@dataclass(frozen=True)
class Envelope:
    """The safety envelope of an instrument: the permitted ranges, the
    interlocks, and the timeout of one driver call."""

    amplitude: Limit  # of the excitation, V
    frequency: Limit  # of the excitation, Hz
    sample_rate: Limit  # of the acquisition, Hz
    samples: Limit  # per acquisition
    timeout_s: float
    interlocks: tuple[Interlock, ...] = ()

    def __post_init__(self):
        if not self.timeout_s > 0:
            raise ValueError("the timeout must be positive")

    def describe(self) -> dict[str, Any]:
        limits = (self.amplitude, self.frequency, self.sample_rate, self.samples)
        return {
            "limits": [
                {"quantity": x.quantity, "unit": x.unit, "low": x.low, "high": x.high}
                for x in limits
            ],
            "timeout_s": self.timeout_s,
            "interlocks": [i.name for i in self.interlocks],
        }


@dataclass(frozen=True)
class Capture:
    """One acquisition: the sample times from its start (s) and one array
    per channel, each with its unit."""

    sample_rate_hz: float
    t: NDArray[np.float64]
    channels: Mapping[str, NDArray[np.float64]]
    units: Mapping[str, str]


class Driver(Protocol):
    """What an adapter of one execution mode implements. Only an
    ``Instrument`` calls it. ``output_off`` must be safe to call at any
    time, also while another call is running: it is the stop behaviour."""

    mode: str

    def identity(self) -> Mapping[str, str]:
        """The device or model and its calibration."""
        ...

    def set_output(self, amplitude_v: float, frequency_hz: float) -> None: ...

    def output_off(self) -> None: ...

    def capture(self, sample_rate_hz: float, samples: int) -> Capture: ...


@dataclass(frozen=True)
class InstrumentRun:
    """The record of one run on an instrument: the execution mode, the
    device or model with its calibration, the configuration, the units, the
    processing, and the timestamps. A recorded run is never a new
    experiment."""

    mode: str
    device: Mapping[str, str]
    configuration: Mapping[str, Any]
    units: Mapping[str, str]
    processing: tuple[str, ...]
    started: str
    finished: str
    new_experiment: bool
    operations: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self):
        if self.mode not in MODES:
            raise ValueError(f"unknown execution mode {self.mode!r}")
        if self.mode == RECORDED and self.new_experiment:
            raise ValueError("a recorded run is never a new experiment")
        if self.mode != RECORDED and not self.new_experiment:
            raise ValueError(f"a {self.mode} run is a new experiment")

    @property
    def label(self) -> str:
        return _LABELS[self.mode]

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "label": self.label}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class Instrument:
    """The guarded instrument: the only way to a driver."""

    def __init__(self, driver: Driver, envelope: Envelope):
        if driver.mode not in MODES:
            raise ValueError(f"unknown execution mode {driver.mode!r}")
        self._driver = driver
        self.envelope = envelope
        self._lock = threading.Lock()  # one driver operation at a time
        self._stop = threading.Event()
        self._halt: str | None = None  # why operations are refused
        self._output: tuple[float, float] | None = None
        self.counts = {"accepted": 0, "refused": 0}

    @property
    def mode(self) -> str:
        return self._driver.mode

    # -- the operations --------------------------------------------------------

    def excite(self, amplitude_v: float, frequency_hz: float) -> None:
        """Switch the output on at ``amplitude_v`` and ``frequency_hz``."""
        with self._guard():
            amplitude = self.envelope.amplitude.check(amplitude_v)
            frequency = self.envelope.frequency.check(frequency_hz)
            for interlock in self.envelope.interlocks:
                if not interlock.closed():
                    raise InterlockOpen(
                        f"interlock {interlock.name} is open: {interlock.description}"
                    )
            self._call(self._driver.set_output, amplitude, frequency)
            self._output = (amplitude, frequency)
            if self._halted():
                # A stop or timeout while the output was being switched on:
                # it goes off again, and the operation is refused.
                self.output_off()
                raise Stopped(f"the instrument is halted ({self._halt_reason()})")

    def acquire(self, sample_rate_hz: float, samples: int) -> Capture:
        """One acquisition of ``samples`` samples at ``sample_rate_hz``."""
        with self._guard():
            rate = self.envelope.sample_rate.check(sample_rate_hz)
            count = int(self.envelope.samples.check(samples))
            capture = self._call(self._driver.capture, rate, count)
            if self._stop.is_set():
                # A stop during the acquisition: its data are not handed out.
                raise Stopped("stopped during the acquisition")
            return capture

    def output_off(self) -> None:
        """Switch the output off. Always permitted."""
        self._driver.output_off()
        self._output = None

    def request_stop(self, reason: str = "stop requested") -> None:
        """Stop: the output goes off now, from any thread, and every later
        operation is refused."""
        self._stop.set()
        if self._halt is None:
            self._halt = reason
        self.output_off()

    @property
    def stopped(self) -> bool:
        return self._halt is not None

    def snapshot(self) -> dict[str, Any]:
        """The state of the instrument; always permitted."""
        return {
            "mode": self.mode,
            "device": dict(self._driver.identity()),
            "output": None
            if self._output is None
            else {"amplitude_v": self._output[0], "frequency_hz": self._output[1]},
            "halted": self._halt,
            "operations": dict(self.counts),
            "envelope": self.envelope.describe(),
        }

    def run_record(
        self,
        configuration: Mapping[str, Any],
        units: Mapping[str, str],
        processing: tuple[str, ...],
        started: str,
        finished: str,
    ) -> InstrumentRun:
        return InstrumentRun(
            mode=self.mode,
            device=dict(self._driver.identity()),
            configuration=dict(configuration),
            units=dict(units),
            processing=processing,
            started=started,
            finished=finished,
            new_experiment=self.mode != RECORDED,
            operations=dict(self.counts),
        )

    # -- the guard -------------------------------------------------------------

    def _halted(self) -> bool:
        return self._stop.is_set() or self._halt is not None

    def _halt_reason(self) -> str:
        return self._halt or "stop requested"

    def _refuse_if_halted(self) -> None:
        if self._halted():
            raise Stopped(f"the instrument is halted ({self._halt_reason()})")

    def _guard(self) -> _Guard:
        return _Guard(self)

    def _call(self, function: Callable[..., Any], *arguments: Any) -> Any:
        """Run one driver call under the timeout. The halt is checked right
        before the call; a call that returns after a stop or a timeout,
        also one that returns late after its timeout, switches the output
        off again, so that output_off is the driver's last call."""
        self._refuse_if_halted()
        outcome: dict[str, Any] = {}

        def target():
            try:
                outcome["value"] = function(*arguments)
            except BaseException as error:  # handed to the caller below
                outcome["error"] = error
            finally:
                if self._halted():
                    self._driver.output_off()

        worker = threading.Thread(target=target, daemon=True)
        worker.start()
        worker.join(self.envelope.timeout_s)
        if worker.is_alive():
            self._halt = f"timeout after {self.envelope.timeout_s:g} s"
            self.output_off()
            raise InstrumentTimeout(
                f"the device did not answer within {self.envelope.timeout_s:g} s;"
                " the output is off and the instrument is halted"
            )
        if "error" in outcome:
            raise outcome["error"]
        return outcome.get("value")


class _Guard:
    """Refuses an operation once the instrument is halted, serialises the
    operations, and counts what was accepted and refused."""

    def __init__(self, instrument: Instrument):
        self.instrument = instrument

    def __enter__(self):
        instrument = self.instrument
        if not instrument._halted():
            instrument._lock.acquire()
            # Checked again with the lock held: a stop may have landed while
            # this operation waited behind another one.
            if not instrument._halted():
                return self
            instrument._lock.release()
        instrument.counts["refused"] += 1
        raise Stopped(f"the instrument is halted ({instrument._halt_reason()})")

    def __exit__(self, kind, error, trace):
        self.instrument._lock.release()
        self.instrument.counts["accepted" if error is None else "refused"] += 1
        return False
