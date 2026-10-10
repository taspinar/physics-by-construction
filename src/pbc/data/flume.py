"""Reader for the surface-elevation CSV files of the Aalborg submerged-bar flume."""

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class Elevation:
    """Surface elevation series: ``values[:, k]`` belongs to column ``labels[k]``.

    ``gauges[k]`` is the wave-gauge number of that column; the experiment has
    seven columns per gauge (five repetitions, the sample mean, the expanded
    uncertainty), a numerical file one column per gauge.
    """

    time: np.ndarray  # s
    gauges: tuple[int, ...]
    labels: tuple[str, ...]
    values: np.ndarray  # m

    def column(self, gauge: int, label: str) -> np.ndarray:
        for k, (g, name) in enumerate(zip(self.gauges, self.labels, strict=True)):
            if g == gauge and name == label:
                return self.values[:, k]
        raise KeyError(f"gauge {gauge}, column {label!r}")


def read_elevation(path: Path) -> Elevation:
    """Read a file with a gauge-number row, a header row, and numeric rows."""
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    gauge_row, header = rows[0][1:], rows[1]
    if not header[0].startswith("time [s]"):
        raise ValueError(f"{path}: first column is {header[0]!r}, not 'time [s]'")
    data = np.array([[float(x) for x in row] for row in rows[2:]])
    if data.shape[1] != len(header):
        raise ValueError(f"{path}: row width differs from header")
    labels = [h.rsplit(" [", 1)[0] for h in header[1:]]
    return Elevation(
        time=data[:, 0],
        gauges=tuple(int(g) for g in gauge_row),
        labels=tuple(labels),
        values=data[:, 1:],
    )
