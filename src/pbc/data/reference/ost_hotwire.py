"""Ost, de Paula and Möller hot-wire cylinder wakes: the Strouhal number.

Status of the figure: *processed*. The record (Mendeley Data, doi
10.17632/xy8ggx9hn6.1, "Turbulent flow past cylinders") holds ten plain-text
files, one per run: time [s] and velocity [m/s] of a single hot wire (DANTEC
StreamLine, 1000 Hz, low-pass filter at 300 Hz, 2^17 samples) in the wake of
a cylinder of diameter 25.1, 32 or 50 mm spanning an aerodynamic channel
0.147 m high and 0.193 m wide, at a reference velocity from a Pitot tube.
The cylinder diameter, the reference velocity, the Reynolds number, and the
probe position of each run are in the record's file descriptions only; they
are copied to ``runs.csv``.

``tools/datasets/ost_hotwire_extract.py`` reads the ten files once, outside
the build, and writes the first 2^14 samples (16.384 s) of each as one CSV,
velocities rounded to 1 mm/s. This module finds the shedding frequency of
each run as the peak of the velocity spectrum, forms St = f D / U with the
record's D and reference velocity U, and compares the runs with each other,
with the blockage D / W of the channel, and with the PIV wake of
``piv-cylinder-wake`` at Re = 413.
"""

import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

from pbc.data import SAMPLES_DIR
from pbc.data.plotting import COLOURS, add_credit, label_status
from pbc.data.reference import cylinder_wake

SERIES = "ost_hotwire_16s.csv"
RUNS = "runs.csv"
RUN_FIELDS = (
    "run",
    "file",
    "sha256",
    "diameter_mm",
    "velocity_m_s",
    "reynolds_record",
    "aspect_ratio",
    "x_over_d",
    "w_over_d",
)
FS = 1000.0  # Hz (record)
SAMPLES = 2**14  # the first 16.384 s of each run
RECORD_SAMPLES = 2**17
CHANNEL_WIDTH = 0.193  # m (record: cross section 0.147 m high, 0.193 m wide)
NPERSEG = 4096  # Welch windows of 4.096 s
BLOCKS = 4  # non-overlapping blocks of 4.096 s for the spread of the peak
F_MIN = 5.0  # Hz: the peak is searched above the slow fluctuations


@dataclass(frozen=True)
class Run:
    name: str
    file: str
    sha256: str
    diameter: float  # m
    velocity: float  # m/s, the reference velocity (Pitot)
    reynolds_record: float
    aspect_ratio: float
    x_over_d: float
    w_over_d: float


@dataclass(frozen=True)
class HotWire:
    runs: tuple[Run, ...]
    u: np.ndarray  # (SAMPLES, runs) m/s
    header: tuple[str, ...]


def read_runs(path: Path) -> tuple[Run, ...]:
    with open(path, encoding="ascii", newline="") as handle:
        rows = list(csv.reader(handle))
    if tuple(rows[0]) != RUN_FIELDS:
        raise ValueError(f"{path}: columns {rows[0]}, expected {RUN_FIELDS}")
    return tuple(
        Run(
            name=r[0],
            file=r[1],
            sha256=r[2],
            diameter=float(r[3]) / 1e3,
            velocity=float(r[4]),
            reynolds_record=float(r[5]),
            aspect_ratio=float(r[6]),
            x_over_d=float(r[7]),
            w_over_d=float(r[8]),
        )
        for r in rows[1:]
    )


def read_series(path: Path, names: tuple[str, ...]) -> tuple[np.ndarray, tuple]:
    lines = Path(path).read_text(encoding="ascii").splitlines()
    header = tuple(line for line in lines if line.startswith("#"))
    columns = lines[len(header)].split(",")
    if tuple(columns) != names:
        raise ValueError(f"{path}: columns {columns}, expected {names}")
    table = np.loadtxt(path, delimiter=",", skiprows=len(header) + 1, ndmin=2)
    if table.shape != (SAMPLES, len(names)) or not np.all(np.isfinite(table)):
        raise ValueError(f"{path}: {table.shape} values, expected {SAMPLES} rows")
    return table, header


def load(data_dir: Path) -> HotWire:
    data_dir = Path(data_dir)
    runs = read_runs(data_dir / RUNS)
    u, header = read_series(data_dir / SERIES, tuple(r.name for r in runs))
    return HotWire(runs, u, header)


# The analysis.


def spectrum(series: np.ndarray, nperseg: int = NPERSEG):
    series = np.asarray(series, dtype=float)
    return signal.welch(series - series.mean(), fs=FS, nperseg=nperseg)


def peak(freq: np.ndarray, power: np.ndarray, f_min: float = F_MIN) -> float:
    return cylinder_wake.peak(freq, power, f_min)


def block_peaks(series: np.ndarray, blocks: int = BLOCKS) -> np.ndarray:
    return np.array(
        [
            peak(*spectrum(part, nperseg=1024))
            for part in np.array_split(np.asarray(series, float), blocks)
        ]
    )


@dataclass(frozen=True)
class Analysis:
    frequency: np.ndarray  # Hz, the Welch peak of each run
    frequency_err: np.ndarray  # Hz, sd of the four block peaks / 2
    strouhal: np.ndarray  # f D / U
    strouhal_err: np.ndarray
    reynolds: np.ndarray  # U D / nu with the median nu the record implies
    nu: float  # m^2/s, the median of U D / Re of the record
    nu_ratio: np.ndarray  # U D / Re / nu of each run (1 if consistent)
    blockage: np.ndarray  # D / W
    mean_velocity: np.ndarray  # m/s, at the probe


def analyse(data: HotWire) -> Analysis:
    d = np.array([r.diameter for r in data.runs])
    v = np.array([r.velocity for r in data.runs])
    implied = v * d / np.array([r.reynolds_record for r in data.runs])
    nu = float(np.median(implied))
    freq = np.array([peak(*spectrum(data.u[:, k])) for k in range(len(data.runs))])
    blocks = np.array([block_peaks(data.u[:, k]) for k in range(len(data.runs))])
    err = blocks.std(axis=1, ddof=1) / np.sqrt(BLOCKS)
    return Analysis(
        frequency=freq,
        frequency_err=err,
        strouhal=freq * d / v,
        strouhal_err=err * d / v,
        reynolds=v * d / nu,
        nu=nu,
        nu_ratio=implied / nu,
        blockage=d / CHANNEL_WIDTH,
        mean_velocity=data.u.mean(axis=0),
    )


# The figure.

MARKERS = {25.1: ("o", COLOURS[0]), 32.0: ("s", COLOURS[2]), 50.0: ("^", COLOURS[1])}


def make_figure(data_dir: Path, piv_dir: Path = SAMPLES_DIR / "piv-cylinder-wake"):
    data = load(data_dir)
    result = analyse(data)
    piv = cylinder_wake.analyse(cylinder_wake.load(piv_dir))
    fig = plt.figure(figsize=(13, 4.8), constrained_layout=True)
    grid = fig.add_gridspec(1, 3, width_ratios=(1.2, 1, 1))
    power, st_re, st_block = (fig.add_subplot(grid[0, k]) for k in range(3))

    # The spectra of the three runs at 10.5 m/s.
    for k, run in enumerate(data.runs):
        if run.velocity != 10.5:
            continue
        marker, colour = MARKERS[round(run.diameter * 1e3, 1)]
        f, p = spectrum(data.u[:, k])
        power.semilogy(
            f[1:],
            p[1:],
            color=colour,
            lw=0.9,
            label=(
                f"D = {run.diameter * 1e3:g} mm, U = 10.5 m/s: peak "
                f"{result.frequency[k]:.1f} Hz [processed]"
            ),
        )
    power.axvline(300, color="0.4", ls=":", label="low-pass filter, 300 Hz")
    power.set_xlim(0, 400)
    power.set_xlabel("frequency [Hz]")
    power.set_ylabel("power spectral density [(m/s)²/Hz]")
    power.set_title("Hot-wire spectra (Welch, 4.096 s windows)")
    power.legend(fontsize=7, loc="upper right")

    # St against Re, with the PIV wake and Roshko's correlation.
    for diameter, (marker, colour) in MARKERS.items():
        pick = np.array([round(r.diameter * 1e3, 1) == diameter for r in data.runs])
        st_re.errorbar(
            result.reynolds[pick],
            result.strouhal[pick],
            yerr=result.strouhal_err[pick],
            fmt=marker,
            color=colour,
            capsize=2,
            label=f"hot wire, D = {diameter:g} mm, D/W = {diameter / 193:.2f}",
        )
        st_block.errorbar(
            result.blockage[pick],
            result.strouhal[pick],
            yerr=result.strouhal_err[pick],
            fmt=marker,
            color=colour,
            capsize=2,
            label=f"D = {diameter:g} mm",
        )
    st_re.errorbar(
        [cylinder_wake.REYNOLDS],
        [piv.strouhal],
        yerr=[piv.strouhal_err],
        fmt="D",
        color=COLOURS[3],
        capsize=2,
        label="PIV wake, Re = 413 (piv-cylinder-wake)",
    )
    re_range = np.geomspace(200, 2000, 50)
    st_re.plot(
        re_range,
        cylinder_wake.roshko(re_range),
        "--",
        color="0.3",
        label="Roshko (1954), St = 0.212 - 2.7/Re [model]",
    )
    st_re.set_xscale("log")
    st_re.set_ylim(0.17, 0.26)
    st_re.set_xlabel("Reynolds number U D / ν [dimensionless]")  # noqa: RUF001
    st_re.set_ylabel("Strouhal number f D / U [dimensionless]")
    st_re.set_title("Strouhal number against Reynolds number")
    st_re.legend(fontsize=7, loc="lower right")

    st_block.set_ylim(0.17, 0.26)
    st_block.set_xlabel("blockage D / W [dimensionless]")
    st_block.set_ylabel("Strouhal number f D / U [dimensionless]")
    st_block.set_title("Strouhal number against the blockage")
    st_block.legend(fontsize=7, loc="upper left")

    label_status(fig, "processed")
    add_credit(
        fig,
        "Data: A. P. Ost, A. V. de Paula, S. V. Möller, 'Turbulent flow past "
        "cylinders', Mendeley Data, v1, 2019, doi 10.17632/xy8ggx9hn6.1, CC BY "
        "4.0 https://creativecommons.org/licenses/by/4.0/; the first 16.384 s of "
        "each run, rounded to 1 mm/s. PIV point: J. Shang, J. Tu, Zenodo, doi "
        "10.5281/zenodo.20765567, CC BY 4.0. Spectra and Strouhal numbers are "
        "this project's processing.",
    )
    return fig
