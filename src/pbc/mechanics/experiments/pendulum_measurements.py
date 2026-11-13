"""The experiment of the lesson "Pendulum measurements lab".

The pendulum of the harmonic-oscillator, energy-conservation and resonance
lessons against a measured one: the rotary-encoder records of the card
``xu-damped-pendulum`` (five lengths, three trials each in air, and three
trials of the shortest length with a paper baffle). The experiment first
checks its analysis on a simulated record with the cadence and the encoder
step of the measurement, then measures the period cycle by cycle and
corrects it to small amplitude with the exact period, tests 2 pi sqrt(L/g)
across the lengths with the spread of the trials as the uncertainty, and
fits linear and linear-plus-quadratic damping to the decay of the amplitude,
testing each on trials it was not fitted to. Run it as a program to write
the figures and the numbers of the page:

    uv run --locked --no-dev python -m \\
        pbc.mechanics.experiments.pendulum_measurements out
"""

from dataclasses import dataclass
from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.data import SAMPLES_DIR
from pbc.data.adapters import pendulum_angle_series
from pbc.data.fit import FitResult, fit_curve
from pbc.data.inverse import residual_autocorrelation
from pbc.data.plotting import COLOURS, add_credit, label_status
from pbc.data.reference.xu_pendulum import (
    CLEAN_WINDOW,
    ENCODER_STEP,
    G_LOCAL,
    Cycles,
    Run,
    Sample,
    clean_window,
    cycles,
    load,
    read_cleaned,
    release,
)
from pbc.experiment import Experiment, main
from pbc.mechanics.damped_pendulum import (
    amplitude_envelope,
    damped_pendulum,
    effective_length,
    quadratic_envelope_constant,
    small_amplitude_period,
)
from pbc.mechanics.dynamics import State, simulate
from pbc.mechanics.integrators import rk4_step
from pbc.mechanics.pendulum import pendulum_period

DATASET = "xu-damped-pendulum"
# region: choices
G = G_LOCAL  # m/s^2, the record's README: "about 9.799"
LENGTHS = ("len1", "len2", "len3", "len4", "len5")
AIR = "cond1"  # damping setting 1: air only
BAFFLE = "cond3"  # damping setting 3: the large paper baffle
TRIALS = (1, 2, 3)
SHORTEST = "len1"  # the pendulum the lab follows through its damping
FIT_TRIAL = 1  # the damping laws are fitted to this trial ...
HOLDOUT = (2, 3)  # ... and tested on these
# The simulated record of the check: a pendulum like the shortest one,
# released at 54 degrees, with damping of the size the data show.
SIMULATED_T0 = 0.9952  # s
SIMULATED_GAMMA = 0.004  # 1/s
SIMULATED_KAPPA = 0.007  # 1/(rad s)
SIMULATED_RELEASE = 0.95  # rad
SIMULATED_STEP = 0.005  # s, the RK4 time step, half the record's 0.01 s
# endregion: choices
SECONDS = CLEAN_WINDOW[1] - CLEAN_WINDOW[0]  # s of every analysed run
RECORD_SHOWN = 20.0  # s of the raw record drawn in fig-record
CREDIT = (
    "Data: E. Xu, T. Tran, H. Zhao, Y. Wang, M. Huai, H. Shao, Damped Pendulum "
    "Dataset, github.com/EnzeXu/Damped_Pendulum_Dataset, commit cbf8267, "
    "Apache-2.0, unmodified. Fits and models: this lesson's code."
)


def run_name(length: str, setting: str, trial: int) -> str:
    """The record's name of a run, such as ``len1_cond1_2``."""
    return length + "_" + setting + "_" + str(trial)


@dataclass(frozen=True)
class Trace:
    """The recorded angle of one run over the creators' window of 60 s."""

    name: str
    length: float  # m, as stated by the record
    time: np.ndarray  # s, from the start of the window
    angle: np.ndarray  # rad, as recorded


def load_sample() -> Sample:
    """The committed raw files of the first trials and the stated lengths."""
    return load(SAMPLES_DIR / DATASET)


def load_traces(sample: Sample) -> dict[str, Trace]:
    """Every run the lab uses, each over the window 5 s <= t < 65 s of its
    recording: the first trials from their raw files (the rows that the
    creators' cleaning keeps), the others from the creators' cleaned files,
    which are those rows unchanged."""
    traces = {}
    for name, run in sample.runs.items():
        window = clean_window(run)
        traces[name] = Trace(
            name, run.length, run.time[window] - CLEAN_WINDOW[0], run.angle[window]
        )
    cleaned_dir = SAMPLES_DIR / DATASET / "cleaned_data"
    for length in LENGTHS:
        for setting in (AIR, BAFFLE):
            for trial in TRIALS:
                name = run_name(length, setting, trial)
                if name in traces or (setting == BAFFLE and length != SHORTEST):
                    continue
                cleaned = read_cleaned(cleaned_dir / (name + ".csv"))
                traces[name] = Trace(
                    name, sample.lengths[length], cleaned.time, cleaned.angle
                )
    return traces


def cycles_of(trace: Trace) -> Cycles:
    """The free cycles of a trace, by the cycle analysis of the card's
    reference module: upward crossings of the centre of the swing,
    interpolated between samples, the first cycle after the largest swing
    left out. That analysis reads only the time and the angle of a run."""
    empty = np.full(trace.time.shape, np.nan)
    run = Run(trace.name, trace.length, trace.time, trace.angle, *[empty] * 5)
    return cycles(run)


@dataclass(frozen=True)
class Period:
    name: str
    length: float  # m, stated
    t0: float  # s, mean small-amplitude period of the cycles
    scatter: float  # s, standard deviation of one cycle's T0
    stderr: float  # s, standard error of the mean over the cycles
    cycles: int
    first_amplitude: float  # rad
    last_amplitude: float  # rad


def period_of(trace: Trace) -> Period:
    """The small-amplitude period of a run: the mean over its cycles of
    each cycle's period corrected for its amplitude."""
    c = cycles_of(trace)
    t0 = small_amplitude_period(c.period, c.amplitude)
    return Period(
        trace.name,
        trace.length,
        float(t0.mean()),
        float(t0.std(ddof=1)),
        float(t0.std(ddof=1) / np.sqrt(t0.size)),
        int(t0.size),
        float(c.amplitude[0]),
        float(c.amplitude[-1]),
    )


def amplitude_slope(trace: Trace) -> tuple[float, float]:
    """Slope [s/rad] of a straight line through the period of each cycle
    against its amplitude, before and after the correction to small
    amplitude: what the correction removes, and what it leaves."""
    c = cycles_of(trace)
    before = np.polyfit(c.amplitude, c.period, 1)[0]
    after = np.polyfit(c.amplitude, small_amplitude_period(c.period, c.amplitude), 1)[0]
    return float(before), float(after)


# The simulated check.


def simulated_record() -> tuple[np.ndarray, np.ndarray]:
    """A record made by the model with known T0, gamma and kappa: the
    angle integrated with RK4, sampled every 0.01 s, and rounded to whole
    encoder steps and to 3 decimals as the PASCO file writes it."""
    beta = SIMULATED_KAPPA / quadratic_envelope_constant(1.0, SIMULATED_T0)
    trajectory = simulate(
        State(0.0, [SIMULATED_RELEASE], [0.0]),
        damped_pendulum(SIMULATED_T0, SIMULATED_GAMMA, beta),
        SIMULATED_STEP,
        round(SECONDS / SIMULATED_STEP),
        step=rk4_step,
    )
    every = round(0.01 / SIMULATED_STEP)
    time = trajectory.t[::every]
    exact = trajectory.x[::every, 0]
    recorded = np.round(np.round(exact / ENCODER_STEP) * ENCODER_STEP, 3)
    return time, recorded


def fit_linear(t: np.ndarray, amplitude: np.ndarray) -> FitResult:
    """The exponential decay of linear damping, A1 e^(-gamma t)."""
    return fit_curve(
        lambda s, a1, gamma: amplitude_envelope(s, a1, gamma),
        t,
        amplitude,
        [amplitude[0], 0.01],
        names=("A1", "gamma"),
    )


def fit_both(t: np.ndarray, amplitude: np.ndarray) -> FitResult:
    """The averaged decay of linear plus quadratic damping,
    A' = -gamma A - kappa A^2."""
    return fit_curve(
        amplitude_envelope,
        t,
        amplitude,
        [amplitude[0], 0.01, 0.01],
        names=("A1", "gamma", "kappa"),
    )


def decay_of(trace: Trace) -> tuple[np.ndarray, np.ndarray]:
    """Time [s] from the first used cycle, and the amplitude [rad] of each
    cycle: the measured decay the damping laws are fitted to."""
    c = cycles_of(trace)
    return c.start - c.start[0], c.amplitude


def rms(values: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.asarray(values) ** 2)))


def simulation_check(experiment: Experiment) -> dict:
    """The analysis of the lab on a simulated record whose T0, gamma and
    kappa are known; record the table and return what it recovered."""
    time, angle = simulated_record()
    trace = Trace("simulated", 0.0, time, angle)
    period = period_of(trace)
    t, amplitude = decay_of(trace)
    linear, both = fit_linear(t, amplitude), fit_both(t, amplitude)
    _, slope = amplitude_slope(trace)
    found = {
        "t0": period.t0,
        "t0-error": period.t0 - SIMULATED_T0,
        "scatter": period.scatter,
        "slope": slope,
        "gamma": both.value("gamma"),
        "gamma-err": float(both.stderr[1]),
        "kappa": both.value("kappa"),
        "kappa-err": float(both.stderr[2]),
        "rms-both": rms(both.residuals),
        "rms-linear": rms(linear.residuals),
        "cycles": period.cycles,
        "first-amplitude": period.first_amplitude,
    }
    experiment.table(
        "simulation-check",
        [
            ("small-amplitude period T0", "s", SIMULATED_T0, found["t0"]),
            ("gamma, linear damping", "1/s", SIMULATED_GAMMA, found["gamma"]),
            ("kappa, quadratic damping", "1/(rad s)", SIMULATED_KAPPA, found["kappa"]),
        ],
        columns=[
            ("quantity", "", "s"),
            ("unit", "", "s"),
            ("set in the simulation", "", ".5f"),
            ("recovered by the analysis", "", ".5f"),
        ],
        caption="The lab's analysis on a record simulated by the model, sampled every "
        "0.01 s and rounded to the encoder step: the cycle periods corrected for "
        "amplitude, and the linear-plus-quadratic envelope fitted to the cycle "
        "amplitudes.",
    )
    return found


# The record.


def record_facts(sample: Sample, traces: dict[str, Trace]) -> dict:
    """What the first record of the shortest pendulum shows without a
    model: its rows, the release, and the cycles of the window."""
    raw = sample.runs[run_name(SHORTEST, AIR, 1)]
    k = release(raw)
    period = period_of(traces[raw.name])
    return {
        "rows": int(raw.time.size),
        "seconds": float(raw.time[-1]),
        "release-time": float(raw.time[k]),
        "release-angle": float(np.degrees(abs(raw.angle[k]))),
        "cycles": period.cycles,
        "first-amplitude": float(np.degrees(period.first_amplitude)),
        "last-amplitude": float(np.degrees(period.last_amplitude)),
    }


# Period against amplitude.


def amplitude_correction(experiment: Experiment, traces: dict[str, Trace]) -> dict:
    """The three air trials of the shortest pendulum: the slope of the
    period against the amplitude before and after the correction, and T0;
    record the table and return the ranges."""
    rows, before, after, t0s = [], [], [], []
    for trial in TRIALS:
        trace = traces[run_name(SHORTEST, AIR, trial)]
        p = period_of(trace)
        b, a = amplitude_slope(trace)
        before.append(b)
        after.append(a)
        t0s.append(p.t0)
        rows.append(
            (
                trace.name,
                p.cycles,
                f"{np.degrees(p.first_amplitude):.0f} to "
                f"{np.degrees(p.last_amplitude):.0f}",
                1000 * np.radians(1) * b,
                1000 * np.radians(1) * a,
                p.t0,
                1000 * p.scatter,
            )
        )
    experiment.table(
        "amplitude-correction",
        rows,
        columns=[
            ("run", "", "s"),
            ("cycles", "", "d"),
            ("amplitude", "deg", "s"),
            ("slope of T", "ms/deg", ".2f"),
            ("slope of T0", "ms/deg", ".2f"),
            ("T0", "s", ".5f"),
            ("scatter of one cycle's T0", "ms", ".2f"),
        ],
        caption="The period of each cycle against its amplitude, as straight-line "
        "slopes, before (T) and after (T0) the correction to small amplitude, for the "
        "three air trials of the shortest pendulum; T0 is the mean over the cycles.",
    )
    per_degree = 1000 * np.radians(1)
    return {
        "before-low": per_degree * min(before),
        "before-high": per_degree * max(before),
        "after-low": per_degree * min(after),
        "after-high": per_degree * max(after),
        "t0-spread": 1000 * (max(t0s) - min(t0s)),
        "removed": 100 * (1 - max(abs(a) for a in after) / min(before)),
    }


# Period against length.


@dataclass(frozen=True)
class LengthPoint:
    key: str
    length: float  # m, stated
    t0: np.ndarray  # s, one per air trial
    mean: float  # s
    sd: float  # s, standard deviation of the trials
    error: float  # s, standard error of the mean of the trials


def length_points(traces: dict[str, Trace]) -> list[LengthPoint]:
    points = []
    for key in LENGTHS:
        t0 = np.array([period_of(traces[run_name(key, AIR, t)]).t0 for t in TRIALS])
        sd = float(t0.std(ddof=1))
        points.append(
            LengthPoint(
                key,
                traces[run_name(key, AIR, 1)].length,
                t0,
                float(t0.mean()),
                sd,
                sd / np.sqrt(t0.size),
            )
        )
    return points


def trial_spread_test(traces: dict[str, Trace], points: list[LengthPoint]) -> dict:
    """Whether the trials of a length differ by more than the standard
    errors of their runs allow: the sum over the lengths of (n - 1) s^2 /
    se^2, with s the standard deviation of the n trials' T0 and se^2 the
    mean squared standard error of their runs. If each run's standard error
    were its whole uncertainty, the sum would follow a chi-square with
    (n - 1) degrees of freedom per length."""
    chi2, dof = 0.0, 0
    for p in points:
        errors = np.array(
            [period_of(traces[run_name(p.key, AIR, t)]).stderr for t in TRIALS]
        )
        chi2 += (p.t0.size - 1) * p.sd**2 / float(np.mean(errors**2))
        dof += p.t0.size - 1
    return {"chi2": chi2, "dof": dof}


def trials_table(experiment: Experiment, points: list[LengthPoint]) -> None:
    rows = []
    for p in points:
        excess = 1000 * (float(effective_length(p.mean, G)) - p.length)
        rows.append((p.length, *p.t0, p.mean, 1000 * p.sd, excess))
    experiment.table(
        "trials",
        rows,
        columns=[
            ("stated L", "m", ".3f"),
            ("T0, trial 1", "s", ".5f"),
            ("T0, trial 2", "s", ".5f"),
            ("T0, trial 3", "s", ".5f"),
            ("mean", "s", ".5f"),
            ("spread of the trials (1 sd)", "ms", ".2f"),
            ("L_eff - L", "mm", ".1f"),
        ],
        caption="The small-amplitude period of the three air trials of every length, "
        "their mean and standard deviation, and how much longer than stated a simple "
        "pendulum with the mean period would be (L_eff = g T0^2 / 4 pi^2, "
        "g = 9.799 m/s^2).",
    )


def _excess_mm(points: list[LengthPoint], model_squares: np.ndarray) -> np.ndarray:
    """Measured minus model T0^2, as a length [mm] of the simple pendulum."""
    squares = np.array([p.mean for p in points]) ** 2
    return 1000 * G * (squares - model_squares) / (4 * np.pi**2)


def length_models(experiment: Experiment, points: list[LengthPoint]) -> dict:
    """Three models of T0^2 against the stated length, judged with the
    standard error of the mean of the trials: the simple pendulum with the
    stated L and g, a straight line with a free slope and offset, and a
    physical pendulum L_eff = L + c / L with g known. Record the table and
    return their numbers."""
    lengths = np.array([p.length for p in points])
    squares = np.array([p.mean for p in points]) ** 2
    sigma = np.array([2 * p.mean * p.error for p in points])
    k = 4 * np.pi**2 / G
    simple = k * lengths
    simple_chi2 = float(np.sum(((squares - simple) / sigma) ** 2)) / lengths.size
    line = fit_curve(
        lambda x, a, b: a * x + b,
        lengths,
        squares,
        [k, 0.0],
        sigma=sigma,
        names=("a", "b"),
    )
    physical = fit_curve(
        lambda x, c: k * (x + c / x),
        lengths,
        squares,
        [0.002],
        sigma=sigma,
        names=("c",),
    )
    a, b = line.value("a"), line.value("b")
    c = physical.value("c")
    excess = {
        "simple": _excess_mm(points, simple),
        "line": _excess_mm(points, a * lengths + b),
        "physical": _excess_mm(points, k * (lengths + c / lengths)),
    }
    # The standard errors of a weighted fit assume that the model describes
    # the points within their uncertainties; with a reduced chi-square far
    # above 1 they are scaled by its square root, which takes the scatter
    # about the model as the uncertainty instead.
    g_line = 4 * np.pi**2 / a
    g_err = g_line * float(line.stderr[0]) * np.sqrt(line.reduced_chi2) / a
    c_err = float(physical.stderr[0]) * np.sqrt(physical.reduced_chi2)
    rows = [
        ("simple pendulum, 4 pi^2 L / g", "none", "-", simple_chi2, excess["simple"]),
        (
            "straight line, a L + b",
            "a, b",
            f"g = 4 pi^2 / a = {g_line:.2f} +- {g_err:.2f} m/s^2; "
            f"b / a = {1000 * b / a:.1f} mm",
            line.reduced_chi2,
            excess["line"],
        ),
        (
            "physical pendulum, 4 pi^2 (L + c / L) / g",
            "c",
            f"c = {1e4 * c:.1f} +- {1e4 * c_err:.1f} cm^2",
            physical.reduced_chi2,
            excess["physical"],
        ),
    ]
    experiment.table(
        "length-models",
        [
            (name, free, values, chi2, float(np.abs(res).max()))
            for name, free, values, chi2, res in rows
        ],
        columns=[
            ("model of T0^2", "", "s"),
            ("free parameters", "", "s"),
            ("fitted values", "", "s"),
            ("reduced chi-square", "", ".0f"),
            ("largest residual as a length", "mm", ".1f"),
        ],
        caption="Three models of the mean small-amplitude period squared against the "
        "stated length, judged with the standard error of the mean of the three "
        "trials; g = 9.799 m/s^2 where it is not fitted, and the errors of the fitted "
        "values are scaled by the square root of the reduced chi-square. A reduced "
        "chi-square near 1 "
        "would mean that the model describes the points within the spread of the "
        "trials. The largest residual is converted into the length of a simple "
        "pendulum.",
    )
    return {
        "simple-chi2": simple_chi2,
        "line": line,
        "g-line": g_line,
        "g-err": g_err,
        "offset": b / a,
        "physical": physical,
        "c": c,
        "c-err": c_err,
        "excess": excess,
        "sigma-mm": 1000 * G * sigma / (4 * np.pi**2),
    }


# Damping.


@dataclass(frozen=True)
class DampingFit:
    name: str
    trial: int
    t: np.ndarray  # s, from the first used cycle
    amplitude: np.ndarray  # rad
    linear: FitResult  # fitted to this trial
    both: FitResult  # fitted to this trial
    linear_rms: float  # rad, of the law of the fit trial (refitted A1 only)
    both_rms: float  # rad, likewise


def _with_rates(t, amplitude, gamma: float, kappa: float) -> FitResult:
    """The decay law with given rates, only the starting amplitude fitted."""
    return fit_curve(
        lambda s, a1: amplitude_envelope(s, a1, gamma, kappa),
        t,
        amplitude,
        [amplitude[0]],
        names=("A1",),
    )


def damping_fits(traces: dict[str, Trace], setting: str) -> list[DampingFit]:
    """Both damping laws fitted to each trial of the shortest pendulum in
    ``setting``, and each trial predicted with the rates fitted to trial
    ``FIT_TRIAL`` (only its starting amplitude fitted)."""
    decays = {
        trial: decay_of(traces[run_name(SHORTEST, setting, trial)]) for trial in TRIALS
    }
    t1, a1 = decays[FIT_TRIAL]
    reference_linear, reference_both = fit_linear(t1, a1), fit_both(t1, a1)
    out = []
    for trial in TRIALS:
        t, amplitude = decays[trial]
        lin = _with_rates(t, amplitude, reference_linear.value("gamma"), 0.0)
        both = _with_rates(
            t,
            amplitude,
            reference_both.value("gamma"),
            reference_both.value("kappa"),
        )
        out.append(
            DampingFit(
                run_name(SHORTEST, setting, trial),
                trial,
                t,
                amplitude,
                fit_linear(t, amplitude),
                fit_both(t, amplitude),
                rms(lin.residuals),
                rms(both.residuals),
            )
        )
    return out


def damping_table(experiment: Experiment, fits: dict[str, list[DampingFit]]) -> None:
    rows = []
    for setting, label in ((AIR, "air"), (BAFFLE, "large baffle")):
        for f in fits[setting]:
            role = "fitted" if f.trial == FIT_TRIAL else "held out"
            rows.append(
                (
                    label,
                    f.trial,
                    role,
                    np.degrees(f.amplitude[0]),
                    1000 * f.linear_rms,
                    1000 * f.both_rms,
                )
            )
    experiment.table(
        "damping-holdout",
        rows,
        columns=[
            ("setting", "", "s"),
            ("trial", "", "d"),
            ("role", "", "s"),
            ("first amplitude", "deg", ".0f"),
            ("rms residual, linear", "mrad", ".1f"),
            ("rms residual, linear plus quadratic", "mrad", ".1f"),
        ],
        caption="Each damping law with the rates fitted to trial 1 of the shortest "
        "pendulum, against the cycle amplitudes of every trial of the same setting; "
        "only the starting amplitude is fitted to trials 2 and 3, which the rates "
        "never saw.",
    )


def rates_table(experiment: Experiment, fits: dict[str, list[DampingFit]]) -> None:
    rows = []
    for setting, label in ((AIR, "air"), (BAFFLE, "large baffle")):
        for f in fits[setting]:
            rows.append(
                (
                    label,
                    f.trial,
                    1000 * f.linear.value("gamma"),
                    1000 * f.both.value("gamma"),
                    1000 * float(f.both.stderr[1]),
                    1000 * f.both.value("kappa"),
                    1000 * float(f.both.stderr[2]),
                )
            )
    experiment.table(
        "damping-rates",
        rows,
        columns=[
            ("setting", "", "s"),
            ("trial", "", "d"),
            ("gamma, linear law", "1/ks", ".2f"),
            ("gamma, both", "1/ks", ".2f"),
            ("its standard error", "1/ks", ".2f"),
            ("kappa, both", "1/(rad ks)", ".1f"),
            ("its standard error", "1/(rad ks)", ".1f"),
        ],
        caption="The rates of the two laws fitted to each trial on its own, in units "
        "of one per thousand seconds; the standard errors are those of the fit, from "
        "the scatter of its residuals.",
    )


def damping_summary(
    fits: dict[str, list[DampingFit]], traces: dict[str, Trace]
) -> dict:
    """The numbers the page states about the damping; the quality factor
    is Q = w0 / (2 gamma) = pi / (gamma T0) of the linear law of trial 1."""
    out = {}
    for setting in (AIR, BAFFLE):
        f = fits[setting]
        first = f[0]
        held = [x for x in f if x.trial in HOLDOUT]
        kappas = np.array([x.both.value("kappa") for x in f])
        gammas = np.array([x.both.value("gamma") for x in f])
        rho_linear, z_linear = residual_autocorrelation(first.linear.residuals)
        rho_both, z_both = residual_autocorrelation(first.both.residuals)
        out[setting] = {
            "fit-linear": first.linear_rms,
            "fit-both": first.both_rms,
            "held-linear-low": min(x.linear_rms for x in held),
            "held-linear-high": max(x.linear_rms for x in held),
            "held-both-low": min(x.both_rms for x in held),
            "held-both-high": max(x.both_rms for x in held),
            "kappa-mean": float(kappas.mean()),
            "kappa-sd": float(kappas.std(ddof=1)),
            "kappa-err-max": max(float(x.both.stderr[2]) for x in f),
            "gamma-mean": float(gammas.mean()),
            "gamma-sd": float(gammas.std(ddof=1)),
            "rho-linear": rho_linear,
            "rho-both": rho_both,
            "z-both": z_both,
            "z-linear": z_linear,
            "cycles": int(first.t.size),
            "quality": float(
                np.pi / (first.linear.value("gamma") * period_of(traces[first.name]).t0)
            ),
        }
    return out


# Figures.


def draw_record(sample: Sample) -> Figure:
    """The start of the raw record of the shortest pendulum's first air
    trial, sample by sample, with the release and the analysed window."""
    raw = sample.runs[run_name(SHORTEST, AIR, 1)]
    series = pendulum_angle_series(raw).select(0.0, RECORD_SHOWN)
    fig, ax = plt.subplots(figsize=(6.2, 3.3), constrained_layout=True)
    start, end = CLEAN_WINDOW
    ax.axvspan(start, end, color="0.92", label="start of the analysed window of 60 s")
    ax.plot(
        series.x,
        series.y,
        color=COLOURS[0],
        lw=0.8,
        label=f"recorded angle, every 0.01 s [{series.status}]",
    )
    ax.axvline(
        raw.time[release(raw)], color="0.3", ls=":", lw=1.2, label="release by hand"
    )
    ax.set_xlabel("time since the recording started [s]")
    ax.set_ylabel("angle [rad]")
    ax.set_xlim(0, RECORD_SHOWN)
    ax.set_ylim(-0.9, 1.45)
    ax.set_title(
        f"The record's first {RECORD_SHOWN:.0f} s, L = {raw.length:.3f} m: "
        "lifted by hand, released, swinging"
    )
    ax.legend(fontsize=7, loc="upper center", ncol=2)
    add_credit(fig, CREDIT)
    label_status(fig, series.status)
    return fig


def draw_period_amplitude(traces: dict[str, Trace]) -> Figure:
    """Period of every cycle of the three air trials of the shortest
    pendulum against its amplitude, before and after the correction, with
    the exact period of the energy-conservation lesson for their common T0
    and 2 pi sqrt(L/g) of the stated length; below, the residuals of the
    measured periods against the exact period."""
    runs = [traces[run_name(SHORTEST, AIR, t)] for t in TRIALS]
    all_t0 = np.concatenate(
        [small_amplitude_period(c.period, c.amplitude) for c in map(cycles_of, runs)]
    )
    common = float(all_t0.mean())
    length = runs[0].length
    fig, (top, bottom) = plt.subplots(
        2,
        1,
        figsize=(6.0, 5.0),
        sharex=True,
        constrained_layout=True,
        gridspec_kw={"height_ratios": [1.4, 1.0]},
    )
    markers = ("o", "s", "^")
    lowest, highest = np.inf, 0.0
    for k, trace in enumerate(runs):
        c = cycles_of(trace)
        degrees = np.degrees(c.amplitude)
        lowest, highest = min(lowest, degrees.min()), max(highest, degrees.max())
        top.plot(
            degrees,
            c.period,
            color=COLOURS[k],
            marker=markers[k],
            ms=3,
            ls="none",
            mfc="none",
            label=f"T of each cycle, trial {k + 1} [processed]",
        )
        top.plot(
            degrees,
            small_amplitude_period(c.period, c.amplitude),
            color=COLOURS[k],
            marker=markers[k],
            ms=3,
            ls="none",
            label=f"T0, corrected, trial {k + 1} [processed]",
        )
        model = np.array(
            [pendulum_period(effective_length(common, G), a, G) for a in c.amplitude]
        )
        bottom.plot(
            degrees,
            1000 * (c.period - model),
            color=COLOURS[k],
            marker=markers[k],
            ms=3,
            ls="none",
            label=f"residual, trial {k + 1}",
        )
    grid = np.radians(np.linspace(lowest - 1, highest + 1, 40))
    exact = [pendulum_period(effective_length(common, G), a, G) for a in grid]
    top.plot(
        np.degrees(grid),
        exact,
        "--",
        color="0.2",
        lw=1.3,
        label="exact period, mean T0 [simulated]",
    )
    small = 2 * np.pi * np.sqrt(length / G)
    top.plot(
        [np.degrees(grid[0]), np.degrees(grid[-1])],
        [small, small],
        ":",
        color="0.35",
        lw=1.3,
        label=f"2 pi sqrt(L/g), L = {length:.3f} m [simulated]",
    )
    top.set_ylim(0.968, 1.095)
    top.set_ylabel("period [s]")
    top.set_title("Period of each cycle against its amplitude, shortest pendulum, air")
    top.legend(fontsize=6.2, loc="upper left", ncol=2)
    bottom.axhline(0, color="0.2", ls="--", lw=1.0)
    bottom.set_xlabel("amplitude of the cycle [deg]")
    bottom.set_ylabel("residual, T minus exact [ms]")
    bottom.set_title("Residuals against the exact period")
    bottom.legend(fontsize=7, loc="upper left", ncol=3)
    add_credit(fig, CREDIT)
    label_status(fig, "processed")
    return fig


def draw_length(points: list[LengthPoint], models: dict) -> Figure:
    """Every air trial as the residual of the simple pendulum of its stated
    length, L_eff - L with L_eff = g T0^2 / (4 pi^2), the mean of the trials
    with its standard error, and the three models of T0^2 in the same
    terms: the simple pendulum is the zero line."""
    lengths = np.array([p.length for p in points])
    line, c = models["line"], models["c"]
    # Straight lines are drawn from their two ends, so that the figure is
    # the same bytes on every draw.
    ends = np.array([0.2, 0.65])
    smooth = np.linspace(0.2, 0.65, 46)
    fig, ax = plt.subplots(figsize=(6.2, 4.2), constrained_layout=True)
    for trial in range(len(TRIALS)):
        excess = 1000 * (
            effective_length(np.array([p.t0[trial] for p in points]), G) - lengths
        )
        ax.plot(
            lengths,
            excess,
            color=COLOURS[0],
            marker=("o", "s", "^")[trial],
            ms=3.5,
            ls="none",
            mfc="none" if trial else COLOURS[0],
            label=f"trial {trial + 1} [processed]",
        )
    means = 1000 * (effective_length(np.array([p.mean for p in points]), G) - lengths)
    ax.errorbar(
        lengths + 0.008,
        means,
        yerr=models["sigma-mm"],
        color="k",
        marker="D",
        ms=3.5,
        ls="none",
        capsize=2,
        label="mean of the trials, bar 1 standard error [processed]",
    )
    ax.plot(
        ends, [0, 0], ":", color="0.35", lw=1.3, label="simple pendulum, 2 pi sqrt(L/g)"
    )
    ax.plot(
        ends,
        1000 * (G * (line.value("a") * ends + line.value("b")) / (4 * np.pi**2) - ends),
        "--",
        color=COLOURS[1],
        lw=1.2,
        label="fitted straight line, a L + b [simulated]",
    )
    ax.plot(
        smooth,
        1000 * c / smooth,
        "-.",
        color=COLOURS[2],
        lw=1.2,
        label="fitted physical pendulum, L + c/L [simulated]",
    )
    ax.set_xlim(0.2, 0.65)
    ax.set_ylim(-1, 15)
    ax.set_xlabel("stated length L [m]")
    ax.set_ylabel("residual of the simple pendulum, L_eff - L [mm]")
    ax.set_title("How much longer than stated each pendulum swings")
    ax.legend(fontsize=6.6, loc="upper right", ncol=2)
    add_credit(fig, CREDIT)
    label_status(fig, "processed")
    return fig


def draw_damping(fits: dict[str, list[DampingFit]]) -> Figure:
    """The cycle amplitudes of the shortest pendulum in air and with the
    large baffle, three trials each, with the linear-plus-quadratic law as
    fitted to trial 1 and as predicted for trials 2 and 3; below, the
    residuals of both laws, the linear one as dashed lines."""
    fig, axes = plt.subplots(
        2,
        2,
        figsize=(7.4, 5.0),
        sharex="col",
        constrained_layout=True,
        gridspec_kw={"height_ratios": [1.3, 1.0]},
    )
    markers = ("o", "s", "^")
    for column, (setting, label) in enumerate(((AIR, "air"), (BAFFLE, "large baffle"))):
        top, bottom = axes[0, column], axes[1, column]
        first = fits[setting][0]
        for k, f in enumerate(fits[setting]):
            role = "fitted" if f.trial == FIT_TRIAL else "held out"
            top.plot(
                f.t,
                np.degrees(f.amplitude),
                color=COLOURS[k],
                marker=markers[k],
                ms=2.2,
                ls="none",
                label=f"trial {f.trial} ({role}) [processed]",
            )
            gamma_l = first.linear.value("gamma")
            gamma_b, kappa_b = first.both.value("gamma"), first.both.value("kappa")
            lin = _with_rates(f.t, f.amplitude, gamma_l, 0.0)
            both = _with_rates(f.t, f.amplitude, gamma_b, kappa_b)
            top.plot(
                f.t,
                np.degrees(amplitude_envelope(f.t, both.value("A1"), gamma_b, kappa_b)),
                "-",
                color="0.15",
                lw=0.7,
                label="linear plus quadratic law [simulated]" if k == 0 else None,
            )
            bottom.plot(
                f.t,
                1000 * lin.residuals,
                color=COLOURS[k],
                ls="--",
                lw=0.9,
                label="linear law (colour: trial)" if k == 0 else None,
            )
            bottom.plot(
                f.t,
                1000 * both.residuals,
                color=COLOURS[k],
                marker=markers[k],
                ms=2.2,
                ls="none",
                label="linear plus quadratic" if k == 0 else None,
            )
        top.set_ylabel("amplitude [deg]")
        top.set_title(f"{label.capitalize()}: the law fitted to trial 1")
        if setting == AIR:
            top.set_ylim(20, 70)  # room above the swings for the legend
        top.legend(fontsize=6.6, loc="upper right")
        bottom.axhline(0, color="0.5", lw=0.8)
        bottom.set_xlabel("time from the first used cycle [s]")
        bottom.set_ylabel("residual [mrad]")
        bottom.set_title(f"Residuals, {label}")
        bottom.legend(fontsize=6.6, loc="upper right")
    add_credit(fig, CREDIT)
    label_status(fig, "processed")
    return fig


# Exercises.


def amplitude_exercise() -> None:
    """Exercise 1: how much longer the period is at 44 degrees than at small
    amplitude, exactly and from the first term of the series."""
    amplitude = np.radians(44.0)
    ratio = pendulum_period(1.0, amplitude, G) / pendulum_period(1.0, 0.0, G)
    print(f"exact ratio of the periods: {ratio:.4f}")
    print(f"with the first correction term only: {1 + amplitude**2 / 16:.4f}")
    print(f"the period is longer by {1000 * 0.995 * (ratio - 1):.0f} ms")


def bob_exercise(c: float) -> None:
    """Exercise 2: the radius of a solid sphere whose own moment of inertia
    alone would give the fitted c, L_eff = L + 2 r^2 / (5 L)."""
    radius = np.sqrt(5 * c / 2)
    print(f"the fitted c: {1e4 * c:.1f} cm^2")
    print(f"the radius of the sphere: {1000 * radius:.0f} mm")


# The page.


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    sample = load_sample()
    traces = load_traces(sample)

    check = simulation_check(experiment)
    experiment.number("sim-t0-error", 1e6 * abs(check["t0-error"]), ".0f")
    experiment.number("sim-scatter", 1000 * check["scatter"], ".2f")
    experiment.number("sim-slope", 1000 * np.radians(1) * check["slope"], ".3f")
    experiment.number(
        "sim-gamma-off", 100 * abs(check["gamma"] / SIMULATED_GAMMA - 1), ".0f"
    )
    experiment.number(
        "sim-kappa-off", 100 * abs(check["kappa"] / SIMULATED_KAPPA - 1), ".0f"
    )
    experiment.number("sim-rms-both", 1000 * check["rms-both"], ".2f")
    experiment.number("sim-rms-linear", 1000 * check["rms-linear"], ".1f")
    experiment.number("sim-release", np.degrees(SIMULATED_RELEASE), ".0f")
    experiment.number("encoder-step-deg", np.degrees(ENCODER_STEP), ".2f")

    facts = record_facts(sample, traces)
    experiment.number("rows", facts["rows"])
    experiment.number("record-seconds", facts["seconds"], ".1f")
    experiment.number("release-time", facts["release-time"], ".2f")
    experiment.number("release-angle", facts["release-angle"], ".0f")
    experiment.number("window-cycles", facts["cycles"])
    experiment.number("first-amplitude", facts["first-amplitude"], ".0f")
    experiment.number("last-amplitude", facts["last-amplitude"], ".0f")
    experiment.number("runs", len(traces))

    corrected = amplitude_correction(experiment, traces)
    experiment.number("slope-before-low", corrected["before-low"], ".2f")
    experiment.number("slope-before-high", corrected["before-high"], ".2f")
    experiment.number("slope-after-low", corrected["after-low"], ".2f")
    experiment.number("slope-after-high", corrected["after-high"], ".2f")
    shortest = period_of(traces[run_name(SHORTEST, AIR, 1)])
    experiment.number("short-scatter", 1000 * shortest.scatter, ".1f")
    experiment.number("short-stderr", 1000 * shortest.stderr, ".2f")

    points = length_points(traces)
    trials_table(experiment, points)
    sds = [1000 * p.sd for p in points]
    experiment.number("trial-sd-low", min(sds), ".2f")
    experiment.number("trial-sd-high", max(sds), ".2f")
    stderrs = [
        1000 * period_of(traces[run_name(p.key, AIR, t)]).stderr
        for p in points
        for t in TRIALS
    ]
    experiment.number("run-stderr-low", min(stderrs), ".2f")
    experiment.number("run-stderr-high", max(stderrs), ".2f")
    spread = trial_spread_test(traces, points)
    experiment.number("trial-chi2", spread["chi2"], ".0f")
    experiment.number("trial-dof", spread["dof"])
    excess = [1000 * (float(effective_length(p.mean, G)) - p.length) for p in points]
    experiment.number("excess-low", min(excess), ".1f")
    experiment.number("excess-high", max(excess), ".1f")
    experiment.number(
        "short-above",
        100 * (points[0].mean / (2 * np.pi * np.sqrt(points[0].length / G)) - 1),
        ".1f",
    )

    models = length_models(experiment, points)
    experiment.number("simple-chi2", models["simple-chi2"], ".0f")
    experiment.number("line-chi2", models["line"].reduced_chi2, ".0f")
    experiment.number("physical-chi2", models["physical"].reduced_chi2, ".0f")
    experiment.number("g-line", models["g-line"], ".2f")
    experiment.number("g-err", models["g-err"], ".2f")
    experiment.number("line-offset", 1000 * models["offset"], ".1f")
    experiment.number("c-value", 1e4 * models["c"], ".1f")
    experiment.number("c-err", 1e4 * models["c-err"], ".1f")
    experiment.number(
        "line-residual-mm", float(np.abs(models["excess"]["line"]).max()), ".1f"
    )
    experiment.number(
        "physical-residual-mm", float(np.abs(models["excess"]["physical"]).max()), ".1f"
    )
    experiment.number("sigma-mm-high", float(models["sigma-mm"].max()), ".2f")

    fits = {setting: damping_fits(traces, setting) for setting in (AIR, BAFFLE)}
    damping_table(experiment, fits)
    rates_table(experiment, fits)
    summary = damping_summary(fits, traces)
    for setting, tag in ((AIR, "air"), (BAFFLE, "baffle")):
        s = summary[setting]
        experiment.number(tag + "-fit-linear", 1000 * s["fit-linear"], ".1f")
        experiment.number(tag + "-fit-both", 1000 * s["fit-both"], ".1f")
        experiment.number(tag + "-held-linear-low", 1000 * s["held-linear-low"], ".1f")
        experiment.number(
            tag + "-held-linear-high", 1000 * s["held-linear-high"], ".1f"
        )
        experiment.number(tag + "-held-both-low", 1000 * s["held-both-low"], ".1f")
        experiment.number(tag + "-held-both-high", 1000 * s["held-both-high"], ".1f")
        experiment.number(tag + "-kappa-mean", 1000 * s["kappa-mean"], ".0f")
        experiment.number(tag + "-kappa-sd", 1000 * s["kappa-sd"], ".0f")
        experiment.number(tag + "-kappa-err", 1000 * s["kappa-err-max"], ".1f")
        experiment.number(tag + "-rho-both", s["rho-both"], "+.2f")
    experiment.number("air-quality", summary[AIR]["quality"], ".0f")

    baffle_t0 = np.mean(
        [period_of(traces[run_name(SHORTEST, BAFFLE, t)]).t0 for t in TRIALS]
    )
    experiment.number("baffle-t0-longer", 1000 * (baffle_t0 - points[0].mean), ".1f")

    experiment.figure("fig-record", partial(draw_record, sample))
    experiment.figure("fig-period-amplitude", partial(draw_period_amplitude, traces))
    experiment.figure("fig-length", partial(draw_length, points, models))
    experiment.figure("fig-damping", partial(draw_damping, fits))

    with experiment.capture("amplitude-exercise"):
        amplitude_exercise()
    with experiment.capture("bob-exercise"):
        bob_exercise(models["c"])
    return experiment


if __name__ == "__main__":
    main(run)
