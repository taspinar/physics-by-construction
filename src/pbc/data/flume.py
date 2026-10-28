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


# The geometry of the flume, from the solver input files of the archive
# (Readme.pdf and the data files do not give it). Positions are along the
# flume in m, from the wavemaker's mean position; the bed is the depth below
# still water.
#
# Gauge k is the (k - 1)-th set of i-VoF/inputFiles/iVoF_WC1_inputFiles/
# waveGaugesNProbes/WGset1_sets; the gauges of the D-SPH definition XML
# (DSPH_WC1_inputFiles/dp_0p0012_coefh_1p8_visco_0p01_Def.xml) are at the
# same twenty positions in the same order.
GAUGE_X = {
    1: 0.83, 2: 1.502, 3: 2.053, 4: 2.36, 5: 2.608, 6: 3.012, 7: 4.113,
    8: 4.521, 9: 5.118, 10: 5.52, 11: 5.864, 12: 6.273, 13: 9.516, 14: 9.588,
    15: 9.703, 16: 9.985, 17: 10.274, 18: 10.836, 19: 11.503, 20: 14.776,
}  # fmt: skip
STILL_WATER_DEPTH = 0.3  # m; both solvers' input files
# The bar as (position, depth) corners: i-VoF's system/blockMeshDict and the
# bathymetry polygon of the D-SPH definition XML. They differ by 20 mm in the
# position of the crest and by 3 mm in its depth.
BED = {
    "i-VoF": ((2.813, 0.3), (4.323, 0.147), (5.327, 0.147), (6.112, 0.3)),
    "D-SPH": ((2.813, 0.3), (4.343, 0.150), (5.347, 0.150), (6.112, 0.3)),
}
WAVE_PERIOD = 1.5  # s, wave condition 1: the period of both solvers' wavemakers
WAVE_HEIGHT = (0.024, 0.025)  # m, wave condition 1: D-SPH, i-VoF


def depth_at(x: np.ndarray, bed: str = "i-VoF") -> np.ndarray:
    """Still-water depth (m) at ``x`` (m) over the bar ``bed``: piecewise
    linear between its corners, the still-water depth elsewhere.

    The beach at the end of the flume, beyond the last gauge, is not part of
    it.
    """
    corners = BED[bed]
    xs = [c[0] for c in corners]
    hs = [c[1] for c in corners]
    return np.interp(np.asarray(x, dtype=float), xs, hs)


def harmonics(
    time: np.ndarray, values: np.ndarray, frequency: float, count: int,
    window: tuple[float, float],
) -> np.ndarray:  # fmt: skip
    """The complex amplitudes a_n, n = 1 .. ``count``, of the harmonics of
    ``frequency`` (Hz) in ``window`` (s), by least squares.

    The record is fitted with c + sum_n Re(a_n exp(i 2 pi n f t)), with t the
    time of the file, so the phase of every gauge refers to the same clock.
    A wave travelling towards larger x, Re(a exp(i (omega t - k x))), has
    arg(a_1) = -k x plus a constant. NaN samples are skipped.
    """
    inside = (time >= window[0]) & (time <= window[1]) & np.isfinite(values)
    t, y = time[inside], values[inside]
    columns = [np.ones_like(t)]
    for n in range(1, count + 1):
        w = 2 * np.pi * n * frequency * t
        columns += [np.cos(w), np.sin(w)]
    coefficients, *_ = np.linalg.lstsq(np.stack(columns, 1), y, rcond=None)
    return coefficients[1::2] - 1j * coefficients[2::2]
