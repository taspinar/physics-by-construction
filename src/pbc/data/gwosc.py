"""Reader for the plain-text strain product of GWOSC (gzip, one value per line)."""

import gzip
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

_HEADER = re.compile(
    r"# Gravitational wave strain for (?P<event>\S+) for (?P<detector>\w+)"
)
_RATE = re.compile(r"# This file has (?P<rate>\d+) samples per second")
_START = re.compile(r"# starting GPS (?P<gps>\d+) duration (?P<duration>\d+)")


@dataclass(frozen=True)
class Strain:
    """Dimensionless strain h(t) of one detector, sampled at a constant rate."""

    event: str
    detector: str
    sample_rate: float
    gps_start: float
    duration: float
    strain: np.ndarray

    @property
    def time(self) -> np.ndarray:
        """GPS time of every sample, in seconds."""
        return self.gps_start + np.arange(self.strain.size) / self.sample_rate


def read_strain(path: Path) -> Strain:
    """Read a GWOSC ``.txt.gz`` strain file; the header must state rate and span."""
    with gzip.open(path, "rt", encoding="ascii") as handle:
        lines = handle.read().splitlines()
    header = [line for line in lines if line.startswith("#")]
    text = "\n".join(header)
    found = (_HEADER.search(text), _RATE.search(text), _START.search(text))
    if not all(found):
        raise ValueError(f"{path}: header does not state event, rate, and span")
    meta, rate, start = found
    values = np.array([float(line) for line in lines if not line.startswith("#")])
    sample_rate = float(rate["rate"])
    duration = float(start["duration"])
    if values.size != round(sample_rate * duration):
        raise ValueError(
            f"{path}: {values.size} samples, header says {sample_rate * duration:g}"
        )
    return Strain(
        event=meta["event"],
        detector=meta["detector"],
        sample_rate=sample_rate,
        gps_start=float(start["gps"]),
        duration=duration,
        strain=values,
    )
