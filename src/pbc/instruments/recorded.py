"""The recorded adapter: a declared sample replayed capture by capture
(execution mode *recorded*).

A ``RecordedSample`` holds acquisitions made earlier, each with the setting
it was made at, and its ``Declaration``: the dataset it comes from, whether
it was measured or simulated, its units, and its provenance (ADR 007: a
measured sample enters the repository only as a dataset sample with its
card). The adapter answers an acquisition only with the recorded one of the
same setting; a setting the sample does not hold is refused, never computed,
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

from pbc.instruments.contract import RECORDED, Capture, Driver, Refused

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
    amplitude_v: float
    frequency_hz: float
    sample_rate_hz: float
    channels: Mapping[str, tuple[float, ...]]


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
        )
        for c in data["captures"]
    )
    return RecordedSample(declaration, captures)


def record_sample(
    driver: Driver,
    settings: Sequence[tuple[float, float, float, int]],
    declaration: Declaration,
) -> RecordedSample:
    """Acquire one capture for each (amplitude, frequency, sample rate,
    samples) on ``driver``, for a synthetic sample of a simulated driver."""
    captures = []
    for amplitude, frequency, rate, samples in settings:
        driver.set_output(amplitude, frequency)
        capture = driver.capture(rate, samples)
        captures.append(
            RecordedCapture(
                amplitude,
                frequency,
                rate,
                {k: tuple(float(x) for x in v) for k, v in capture.channels.items()},
            )
        )
    driver.output_off()
    return RecordedSample(declaration, tuple(captures))


def _same(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=0.0)


class RecordedBench:
    """A driver that replays a recorded sample."""

    mode = RECORDED

    def __init__(self, sample: RecordedSample):
        self.sample = sample
        self._setting: tuple[float, float] | None = None

    def identity(self) -> Mapping[str, Any]:
        d = self.sample.declaration
        return {
            "device": f"recorded sample {d.dataset}",
            "dataset": d.dataset,
            "origin": d.origin,
            "provenance": d.provenance,
            "calibration": "as declared by the sample",
        }

    def set_output(self, amplitude_v: float, frequency_hz: float) -> None:
        self._setting = (float(amplitude_v), float(frequency_hz))

    def output_off(self) -> None:
        self._setting = None

    def capture(self, sample_rate_hz: float, samples: int) -> Capture:
        if self._setting is None:
            raise NotRecorded(
                "the recorded sample holds no capture with the output off"
            )
        amplitude, frequency = self._setting
        for c in self.sample.captures:
            if (
                _same(c.amplitude_v, amplitude)
                and _same(c.frequency_hz, frequency)
                and _same(c.sample_rate_hz, sample_rate_hz)
                and all(len(v) == samples for v in c.channels.values())
            ):
                return Capture(
                    sample_rate_hz=c.sample_rate_hz,
                    t=np.arange(samples) / c.sample_rate_hz,
                    channels={k: np.array(v) for k, v in c.channels.items()},
                    units={"t": "s", **self.sample.declaration.units},
                )
        raise NotRecorded(
            f"the recorded sample holds no capture at {amplitude:g} V,"
            f" {frequency:g} Hz, {sample_rate_hz:g} samples/s, {samples} samples;"
            " a recorded run cannot make a new measurement"
        )
