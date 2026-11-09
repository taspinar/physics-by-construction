"""Xu et al. damped pendulum: the period against amplitude and against length.

Status of the figure: *processed*. The angle is the record's raw measurement
(the counts of a rotary encoder, converted to radians by the PASCO software);
the cycle periods, the amplitudes, the large-amplitude correction, the
envelope, and the fits are computed here and drawn apart from it.

The record's README gives the five lengths of the pendulum without saying
from where to where they are measured, and the local g (about 9.799 m/s^2).
The period does not need L: ``effective_length`` is the length of the simple
pendulum with the measured small-amplitude period, ``g T0^2 / (4 pi^2)``, and
``length_fit`` fits ``T0^2 = a L + b`` against the stated lengths. Neither
tells which physical cause (the bob's size, the rod, the sensor's inertia)
makes the effective length differ from the stated one.

The correction for amplitude, ``T0 = T pi / (2 K(sin^2(A/2)))`` with ``K`` the
complete elliptic integral of the first kind (parameter m = k^2), is exact for
any rigid pendulum without damping (the equation of motion has the same form
as for a point mass); the damping of these runs (Q of a few hundred) shifts
the period by less than 1e-5 of itself.
"""

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.special import ellipk

from pbc.data.fit import FitResult, fit_curve
from pbc.data.plotting import COLOURS, add_credit, label_status

RAW_FIELDS = (
    "Time (s) Run #1",
    "Angle (rad) Run #1",
    "Angular Velocity (rad/s) Run #1",
    "Angular Acceleration (rad/s²) Run #1",
    "Position (m) Run #1",
    "Velocity (m/s) Run #1",
    "Acceleration (m/s²) Run #1",
)
CLEANED_FIELDS = ("time", "angle", "angular_velocity", "is_peak")
LENGTHS_FILE = "pendulum_length.json"
LICENSE = "LICENSE"
RUNS = tuple(f"len{k}_cond1_1" for k in range(1, 6))  # air only, first trial
CLEANED = "len1_cond1_1"
STEP = 0.01  # s, the sampling interval of every file
ENCODER_STEP = 2 * np.pi / 2000  # rad, the step of the recorded angle
# The cleaning of the record's process.py: the rows 5 s <= t < 65 s, the time
# shifted to start at 0, values written with 2 and 3 decimals.
CLEAN_WINDOW = (5.0, 65.0)
# The README: "the gravitational acceleration is about 9.799 m/s^2".
G_LOCAL = 9.799
# Cycles with a smaller amplitude are not used (none in the air-only runs).
MIN_AMPLITUDE = np.radians(3.0)


@dataclass(frozen=True)
class Run:
    name: str
    length: float  # m, as stated by the record
    time: np.ndarray  # s
    angle: np.ndarray  # rad
    angular_velocity: np.ndarray  # rad/s, NaN where the file is empty
    angular_acceleration: np.ndarray  # rad/s^2
    position: np.ndarray  # m, the software's linear conversion (not used)
    velocity: np.ndarray  # m/s
    acceleration: np.ndarray  # m/s^2


@dataclass(frozen=True)
class Cleaned:
    time: np.ndarray  # s, from 0
    angle: np.ndarray  # rad
    angular_velocity: np.ndarray  # rad/s
    is_peak: np.ndarray  # bool, the extremes of |angle| chosen by process.py


@dataclass(frozen=True)
class Sample:
    runs: dict[str, Run]
    cleaned: Cleaned
    lengths: dict[str, float]  # m, by the key len1 .. len5


@dataclass(frozen=True)
class Cycles:
    start: np.ndarray  # s, upward crossing of the centre that opens the cycle
    period: np.ndarray  # s, to the next upward crossing
    amplitude: np.ndarray  # rad, half the range of the angle in the cycle
    centre: float  # rad, the median angle after the release
    # s, one standard deviation of the period from the encoder step alone: the
    # quantisation (step / sqrt(12)) of the angle divided by the angular speed
    # at each of the two crossings, added in quadrature. A lower bound of the
    # period's uncertainty, at most comparable to the scatter of the cycles.
    period_error: np.ndarray

    @property
    def small_amplitude_period(self) -> np.ndarray:
        return corrected_period(self.period, self.amplitude)


def _number(text: str) -> float:
    return float(text) if text != "" else np.nan


def read_raw(path: Path, length: float) -> Run:
    """Read a PASCO export of the record's ``raw_data/`` (UTF-8 with a BOM)."""
    path = Path(path)
    with open(path, encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    if tuple(rows[0]) != RAW_FIELDS:
        raise ValueError(f"{path}: not a raw export of the record: {rows[0]}")
    if any(len(row) != len(RAW_FIELDS) for row in rows[1:]):
        raise ValueError(f"{path}: a row without {len(RAW_FIELDS)} fields")
    values = np.array([[_number(v) for v in row] for row in rows[1:]], dtype=float)
    return Run(path.stem, length, *values.T)


def read_cleaned(path: Path) -> Cleaned:
    path = Path(path)
    with open(path, encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    if tuple(rows[0]) != CLEANED_FIELDS:
        raise ValueError(f"{path}: not a cleaned file of the record: {rows[0]}")
    values = np.array([[float(v) for v in row] for row in rows[1:]], dtype=float)
    return Cleaned(values[:, 0], values[:, 1], values[:, 2], values[:, 3] == 1)


def read_lengths(path: Path) -> dict[str, float]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {key: float(value) for key, value in data["dictData"].items()}


def load(data_dir: Path) -> Sample:
    data_dir = Path(data_dir)
    lengths = read_lengths(data_dir / LENGTHS_FILE)
    runs = {
        name: read_raw(
            data_dir / "raw_data" / f"{name}.csv", lengths[name.split("_")[0]]
        )
        for name in RUNS
    }
    cleaned = read_cleaned(data_dir / "cleaned_data" / f"{CLEANED}.csv")
    return Sample(runs, cleaned, lengths)


def clean_window(run: Run) -> np.ndarray:
    """The rows of a raw run that the record's cleaning keeps."""
    start, end = CLEAN_WINDOW
    # The times are written with 3 decimals; compare in whole sampling steps.
    steps = np.round(run.time / STEP)
    return (steps >= round(start / STEP)) & (steps < round(end / STEP))


def software_velocity(angle: np.ndarray) -> np.ndarray:
    """The angular velocity as the PASCO software computes it from the angle:
    ``(theta[i+2] + theta[i+1] - theta[i-1] - theta[i-2]) / (6 dt)`` of the
    encoder counts (the angle before its rounding to 3 decimals), rounded to 3
    decimals; NaN where the stencil leaves the record."""
    exact = np.round(np.asarray(angle) / ENCODER_STEP) * ENCODER_STEP
    out = np.full(exact.shape, np.nan)
    out[2:-2] = (exact[4:] + exact[3:-1] - exact[1:-3] - exact[:-4]) / (6 * STEP)
    return np.round(out, 3)


def release(run: Run) -> int:
    """Index of the release: the largest |angle| of the record (the pendulum is
    lifted by hand from rest, held, and let go)."""
    return int(np.argmax(np.abs(run.angle)))


def cycles(run: Run) -> Cycles:
    """Periods and amplitudes of the free cycles after the release.

    A cycle runs from one upward crossing of the centre (the median angle after
    the release; the encoder's zero is where the pendulum hung when the
    recording started) to the next, each crossing interpolated linearly between
    two samples. The first cycle after the release is not used: the hand may
    still touch the pendulum during it."""
    after = release(run)
    t, theta = run.time[after:], run.angle[after:]
    centre = float(np.median(theta))
    x = theta - centre
    up = np.flatnonzero((x[:-1] < 0) & (x[1:] >= 0))
    crossings = t[up] + (-x[up]) / (x[up + 1] - x[up]) * (t[up + 1] - t[up])
    speed = (x[up + 1] - x[up]) / (t[up + 1] - t[up])  # rad/s at each crossing
    timing = ENCODER_STEP / np.sqrt(12) / speed  # s, one crossing
    errors = np.hypot(timing[:-1], timing[1:])
    starts, periods, amplitudes = [], [], []
    for a, b, i, j in zip(crossings[:-1], crossings[1:], up[:-1], up[1:], strict=True):
        segment = theta[i + 1 : j + 1]
        amplitude = (segment.max() - segment.min()) / 2
        if amplitude < MIN_AMPLITUDE:
            break
        starts.append(a)
        periods.append(b - a)
        amplitudes.append(amplitude)
    used = len(periods)
    return Cycles(
        np.array(starts[1:]),
        np.array(periods[1:]),
        np.array(amplitudes[1:]),
        centre,
        errors[1:used],
    )


def corrected_period(period: np.ndarray, amplitude: np.ndarray) -> np.ndarray:
    """Small-amplitude period of a rigid pendulum from its period at amplitude
    ``amplitude`` [rad]: T0 = T pi / (2 K(m)), m = sin^2(amplitude / 2)."""
    m = np.sin(np.asarray(amplitude) / 2) ** 2
    return np.asarray(period) * np.pi / (2 * ellipk(m))


@dataclass(frozen=True)
class Period:
    name: str
    length: float  # m, stated
    t0: float  # s, mean small-amplitude period of the cycles
    stderr: float  # s, standard error of the mean over the cycles
    scatter: float  # s, standard deviation of one cycle's T0
    cycles: int
    first_amplitude: float  # rad
    last_amplitude: float  # rad


def period(run: Run) -> Period:
    c = cycles(run)
    t0 = c.small_amplitude_period
    return Period(
        run.name,
        run.length,
        float(t0.mean()),
        float(t0.std(ddof=1) / np.sqrt(t0.size)),
        float(t0.std(ddof=1)),
        int(t0.size),
        float(c.amplitude[0]),
        float(c.amplitude[-1]),
    )


def amplitude_slopes(run: Run) -> tuple[float, float]:
    """Slope [s/rad] of the period of each cycle against its amplitude, before
    and after the correction: how much of the amplitude dependence the
    correction removes, and what is left."""
    c = cycles(run)
    raw = np.polyfit(c.amplitude, c.period, 1)[0]
    corrected = np.polyfit(c.amplitude, c.small_amplitude_period, 1)[0]
    return float(raw), float(corrected)


def simple_period(length: float, g: float = G_LOCAL) -> float:
    """2 pi sqrt(L/g) [s] of a point mass at ``length`` [m]."""
    return float(2 * np.pi * np.sqrt(length / g))


def effective_length(t0: float, g: float = G_LOCAL) -> float:
    """Length [m] of the simple pendulum with the small-amplitude period ``t0``."""
    return float(g * t0**2 / (4 * np.pi**2))


def length_fit(periods: list[Period]) -> FitResult:
    """Straight line T0^2 = a L + b [s^2] against the stated lengths [m], with
    standard errors from the scatter about the line (the cycles' standard
    errors, 0.1 to 0.3 ms, are far below that scatter)."""
    lengths = np.array([p.length for p in periods])
    squares = np.array([p.t0 for p in periods]) ** 2
    return fit_curve(
        lambda x, a, b: a * x + b,
        lengths,
        squares,
        [4 * np.pi**2 / G_LOCAL, 0.0],
        names=("a", "b"),
    )


def fitted_g(result: FitResult) -> float:
    """g [m/s^2] that the slope of ``length_fit`` would mean: 4 pi^2 / a."""
    return float(4 * np.pi**2 / result.value("a"))


def fitted_offset(result: FitResult) -> float:
    """Length [m] that the line adds to every stated length: b / a."""
    return float(result.value("b") / result.value("a"))


def envelope_fit(run: Run) -> tuple[FitResult, float]:
    """Exponential envelope A(t) = A1 exp(-(t - t1) / tau) of the cycle
    amplitudes (viscous damping), and the quality factor pi tau / T0."""
    c = cycles(run)
    t1 = c.start[0]
    result = fit_curve(
        lambda t, a1, tau: a1 * np.exp(-(t - t1) / tau),
        c.start,
        c.amplitude,
        [c.amplitude[0], 100.0],
        names=("A1", "tau"),
    )
    q = np.pi * result.value("tau") / float(c.small_amplitude_period.mean())
    return result, float(q)


def envelope_rms(run: Run) -> dict[str, float]:
    """RMS residual [rad] of three damping laws fitted to the cycle amplitudes:
    exponential (viscous), linear (dry friction), and 1/(1 + k A1 t)
    (drag quadratic in the speed). A sensitivity check of the damping model,
    not a measurement of the law."""
    c = cycles(run)
    t = c.start - c.start[0]
    a = c.amplitude
    laws = {
        "exponential": (lambda t, a1, tau: a1 * np.exp(-t / tau), [a[0], 100.0]),
        "linear": (lambda t, a1, rate: a1 - rate * t, [a[0], 0.002]),
        "quadratic": (lambda t, a1, k: a1 / (1 + k * a1 * t), [a[0], 0.01]),
    }
    out = {}
    for name, (model, p0) in laws.items():
        result = fit_curve(model, t, a, p0)
        out[name] = float(np.sqrt(np.mean(result.residuals**2)))
    return out


def analyse(sample: Sample) -> dict:
    periods = [period(sample.runs[name]) for name in RUNS]
    fit = length_fit(periods)
    return {
        "periods": periods,
        "length_fit": fit,
        "g": fitted_g(fit),
        "offset": fitted_offset(fit),
        "effective_lengths": [effective_length(p.t0) for p in periods],
    }


def make_figure(data_dir: Path) -> plt.Figure:
    sample = load(data_dir)
    result = analyse(sample)
    periods = result["periods"]
    first = sample.runs[RUNS[0]]
    c = cycles(first)
    envelope, q = envelope_fit(first)
    p1 = periods[0]

    fig, axes = plt.subplots(2, 2, figsize=(11, 8.5), constrained_layout=True)
    (ax_angle, ax_period), (ax_length, ax_res) = axes
    measured = {"color": COLOURS[0], "marker": "o", "ms": 4, "ls": "none"}
    model = {"color": COLOURS[1], "ls": "--", "lw": 1.4}
    reference = {"color": "0.35", "ls": ":", "lw": 1.2}

    start, end = CLEAN_WINDOW
    ax_angle.axvspan(
        start, end, color="0.92", label="window of the record's cleaned file"
    )
    ax_angle.plot(
        first.time,
        first.angle,
        color=COLOURS[0],
        lw=0.6,
        label=f"measured angle, L = {first.length:.3f} m (encoder step 0.18 deg)",
    )
    t = np.linspace(c.start[0], c.start[-1] + c.period[-1], 300)
    a1, tau = envelope.value("A1"), envelope.value("tau")
    curve = a1 * np.exp(-(t - c.start[0]) / tau)
    ax_angle.plot(
        t,
        c.centre + curve,
        label=f"fitted exponential envelope, tau = {tau:.0f} s (Q = {q:.0f})",
        **model,
    )
    ax_angle.plot(t, c.centre - curve, **model)
    ax_angle.axvline(first.time[release(first)], label="release", **reference)
    ax_angle.set_xlabel("time [s]")
    ax_angle.set_ylabel("angle [rad]")
    ax_angle.set_title(
        f"Measured angle, air only: the amplitude falls\nfrom "
        f"{np.degrees(c.amplitude[0]):.0f} deg to {np.degrees(c.amplitude[-1]):.0f} deg"
        " over the used cycles",
        fontsize=10,
    )
    ax_angle.legend(fontsize=7.5, loc="lower right")

    degrees = np.degrees(c.amplitude)
    t0 = c.small_amplitude_period
    ax_period.axhspan(
        p1.t0 - p1.scatter,
        p1.t0 + p1.scatter,
        color=COLOURS[0],
        alpha=0.15,
        lw=0,
        label=f"T0 of the run +/- 1 sd of one cycle ({1000 * p1.scatter:.1f} ms)",
    )
    ax_period.errorbar(
        degrees,
        c.period,
        yerr=c.period_error,
        label="period of each cycle",
        **{**measured, "marker": "x", "color": COLOURS[2]},
    )
    ax_period.errorbar(
        degrees,
        t0,
        yerr=c.period_error * t0 / c.period,
        label="corrected to small amplitude, T pi / (2 K)",
        **measured,
    )
    ax_period.text(
        0.02,
        0.07,
        "The record gives no uncertainty per cycle. Bars (smaller than the\n"
        "markers): 1 sd from the encoder step alone, "
        f"{1000 * c.period_error.min():.2f} to {1000 * c.period_error.max():.2f} ms,"
        "\na lower bound. Band: the scatter of this run's cycles. The spread of\n"
        "the trials (dossier) exceeds the standard error of the run's T0.",
        transform=ax_period.transAxes,
        fontsize=7,
        va="bottom",
    )
    ax_period.axhline(
        simple_period(first.length),
        label=f"2 pi sqrt(L/g), stated L, g = {G_LOCAL} m/s^2",
        **reference,
    )
    ax_period.set_xlabel("amplitude of the cycle [deg]")
    ax_period.set_ylabel("period [s]")
    raw_slope, corrected_slope = amplitude_slopes(first)
    simple = simple_period(first.length)
    ax_period.set_title(
        f"Processed: T0 = {p1.t0:.4f} s, {100 * (p1.t0 / simple - 1):.1f} % above "
        f"2 pi sqrt(L/g);\nthe correction removes "
        f"{100 * (1 - corrected_slope / raw_slope):.0f} % of the slope with amplitude",
        fontsize=10,
    )
    ax_period.legend(fontsize=7.5, loc="upper left")

    lengths = np.array([p.length for p in periods])
    squares = np.array([p.t0 for p in periods]) ** 2
    span = np.linspace(0, lengths.max() * 1.05, 50)
    fit = result["length_fit"]
    ax_length.plot(
        lengths, squares, label="T0^2 of each length (first run, air)", **measured
    )
    ax_length.plot(
        span,
        fit.value("a") * span + fit.value("b"),
        label=(
            f"fitted line: slope gives g = {result['g']:.2f} m/s^2, "
            f"offset {1000 * result['offset']:.0f} mm"
        ),
        **model,
    )
    ax_length.plot(
        span,
        4 * np.pi**2 * span / G_LOCAL,
        label=f"4 pi^2 L / g, g = {G_LOCAL} m/s^2 (simple pendulum)",
        **reference,
    )
    ax_length.set_xlim(0, span[-1])
    ax_length.set_ylim(0, None)
    ax_length.set_xlabel("stated length L [m]")
    ax_length.set_ylabel("T0^2 [s^2]")
    ax_length.set_title(
        "Processed: the small-amplitude period against\nthe stated length", fontsize=10
    )
    ax_length.legend(fontsize=7.5, loc="upper left")

    excess = 1000 * (np.array(result["effective_lengths"]) - lengths)
    ax_res.plot(
        lengths, excess, label="L_eff - L, L_eff = g T0^2 / (4 pi^2)", **measured
    )
    line = effective_length(1.0) * (fit.value("a") * span + fit.value("b")) - span
    ax_res.plot(span, 1000 * line, label="the same for the fitted line", **model)
    ax_res.set_xlim(0, span[-1])
    ax_res.axhline(0, label="simple pendulum of the stated length", **reference)
    ax_res.set_xlabel("stated length L [m]")
    ax_res.set_ylabel("residual of the simple pendulum, L_eff - L [mm]")
    ax_res.set_title(
        "Residuals: the effective length exceeds the stated one\n"
        f"by {excess.min():.0f} to {excess.max():.0f} mm",
        fontsize=10,
    )
    ax_res.legend(fontsize=7.5, loc="upper right")

    add_credit(
        fig,
        "Data: E. Xu, T. Tran, H. Zhao, Y. Wang, M. Huai, H. Shao, Damped Pendulum "
        "Dataset, github.com/EnzeXu/Damped_Pendulum_Dataset at commit cbf8267, "
        "Apache-2.0; files raw_data/len1..5_cond1_1.csv, unmodified. Cycles, "
        "corrections, envelope, and fits: this figure's code "
        "(pbc.data.reference.xu_pendulum), not part of the record.",
    )
    label_status(fig, "processed")
    return fig
