"""The recorded adapter: a declared sample replayed capture by capture
(execution mode *recorded*).

A ``RecordedSample`` holds acquisitions made earlier, each with the setting
it was made at, and its ``Declaration``: the dataset it comes from, whether
it was measured or simulated, its units, and its provenance (ADR 007: a
measured sample enters the repository only as a dataset sample with its
card). The adapter answers an acquisition only with the recorded one of the
same setting (amplitude, frequency, waveform, sample rate, length); a
setting the sample does not hold is refused, never computed,
because a recorded run cannot make a new measurement. Its run record says so
(``InstrumentRun.new_experiment`` is False).
"""

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from pbc.instruments.contract import (
    RECORDED,
    SINE,
    WAVEFORMS,
    Capture,
    Driver,
    Refused,
)

FORMAT = 1
MEASURED = "measured"
SIMULATED_ORIGIN = "simulated"
ORIGINS = (MEASURED, SIMULATED_ORIGIN)


class NotRecorded(Refused):
    """A setting the recorded sample does not hold."""


@dataclass(frozen=True)
class Declaration:
    """What a recorded sample is."""

    dataset: str
    origin: str  # measured or simulated
    description: str
    units: Mapping[str, str]
    provenance: str

    def __post_init__(self):
        if self.origin not in ORIGINS:
            raise ValueError(f"origin must be one of {ORIGINS}, got {self.origin!r}")


@dataclass(frozen=True)
class RecordedCapture:
    """One acquisition: the setting it was asked at (``sample_rate_hz`` the
    rate asked) and, for a device whose sample clock realises a rate near
    the one asked (F140's live adapter), the rate it was made at. The
    waveform of the excitation is a sine unless it says otherwise (F145),
    so that a sample written before F145 reads as it did."""

    amplitude_v: float
    frequency_hz: float
    sample_rate_hz: float
    channels: Mapping[str, tuple[float, ...]]
    realised_rate_hz: float | None = None
    waveform: str = SINE

    @property
    def rate_hz(self) -> float:
        """The rate the samples were made at."""
        return self.realised_rate_hz or self.sample_rate_hz


@dataclass(frozen=True)
class RecordedSample:
    declaration: Declaration
    captures: tuple[RecordedCapture, ...]


def save_sample(path: Path, sample: RecordedSample) -> None:
    data = {"format": FORMAT, **asdict(sample)}
    path.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")


def load_sample(path: Path) -> RecordedSample:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise ValueError(f"{path} is not a recorded sample of format {FORMAT}")
    declaration = Declaration(**data["declaration"])
    captures = tuple(
        RecordedCapture(
            amplitude_v=float(c["amplitude_v"]),
            frequency_hz=float(c["frequency_hz"]),
            sample_rate_hz=float(c["sample_rate_hz"]),
            channels={k: tuple(map(float, v)) for k, v in c["channels"].items()},
            realised_rate_hz=(
                None
                if c.get("realised_rate_hz") is None
                else float(c["realised_rate_hz"])
            ),
            waveform=str(c.get("waveform", SINE)),
        )
        for c in data["captures"]
    )
    return RecordedSample(declaration, captures)


def record_sample(
    driver: Driver,
    settings: Sequence[tuple[float, float, float, int]],
    declaration: Declaration,
    waveform: str = SINE,
) -> RecordedSample:
    """Acquire one capture for each (amplitude, frequency, sample rate,
    samples) on ``driver``, for a synthetic sample of a simulated driver,
    with the excitation ``waveform``."""
    captures = []
    for amplitude, frequency, rate, samples in settings:
        if waveform == SINE:
            driver.set_output(amplitude, frequency)
        else:
            driver.set_output(amplitude, frequency, waveform=waveform)  # type: ignore[call-arg]
        capture = driver.capture(rate, samples)
        captures.append(
            RecordedCapture(
                amplitude,
                frequency,
                rate,
                {k: tuple(float(x) for x in v) for k, v in capture.channels.items()},
                waveform=waveform,
            )
        )
    driver.output_off()
    return RecordedSample(declaration, tuple(captures))


def _same(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=0.0)


class RecordedBench:
    """A driver that replays a recorded sample. ``sequential`` replays a
    campaign that measured one setting more than once (F145: the
    repetitions of a ring-down): each capture answers once, in the order
    recorded, so that the n-th acquisition at a setting is the n-th one
    recorded there; a setting asked more often than recorded is refused."""

    mode = RECORDED
    # A recorded sample answers any waveform it holds a capture of.
    waveforms = WAVEFORMS

    def __init__(self, sample: RecordedSample, sequential: bool = False):
        self.sample = sample
        self.sequential = sequential
        self._used: set[int] = set()
        self._setting: tuple[float, float, str] | None = None

    def identity(self) -> Mapping[str, Any]:
        d = self.sample.declaration
        return {
            "device": f"recorded sample {d.dataset}",
            "dataset": d.dataset,
            "origin": d.origin,
            "provenance": d.provenance,
            "calibration": "as declared by the sample",
        }

    def set_output(
        self, amplitude_v: float, frequency_hz: float, waveform: str = SINE
    ) -> None:
        self._setting = (float(amplitude_v), float(frequency_hz), waveform)

    def output_off(self) -> None:
        self._setting = None

    def capture(self, sample_rate_hz: float, samples: int) -> Capture:
        if self._setting is None:
            raise NotRecorded(
                "the recorded sample holds no capture with the output off"
            )
        amplitude, frequency, waveform = self._setting
        for index, c in enumerate(self.sample.captures):
            if self.sequential and index in self._used:
                continue
            if (
                c.waveform == waveform
                and _same(c.amplitude_v, amplitude)
                and _same(c.frequency_hz, frequency)
                and _same(c.sample_rate_hz, sample_rate_hz)
                and all(len(v) == samples for v in c.channels.values())
            ):
                if self.sequential:
                    self._used.add(index)
                return Capture(
                    sample_rate_hz=c.rate_hz,
                    t=np.arange(samples) / c.rate_hz,
                    channels={k: np.array(v) for k, v in c.channels.items()},
                    units={"t": "s", **self.sample.declaration.units},
                )
        raise NotRecorded(
            f"the recorded sample holds no capture at {amplitude:g} V,"
            f" {frequency:g} Hz, {waveform}, {sample_rate_hz:g} samples/s,"
            f" {samples} samples;"
            " a recorded run cannot make a new measurement"
        )
