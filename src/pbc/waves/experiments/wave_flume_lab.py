"""The experiment of the lesson "Wave flume lab".

A regular wave measured at twenty gauges along a flume with a submerged bar
(dataset ``aalborg-submerged-bar``, wave condition 1), against the linear
dispersion relation of water waves (``pbc.waves.water``) and against the
long-wave limit, the wave equation of the lesson "The wave equation", which
has no dispersion; the three CFD solvers of the archive are shown beside
them as what they are, modelled references. Run it as a program to write
the figures and numbers of the page:

    uv run --locked --no-dev python -m pbc.waves.experiments.wave_flume_lab out

The measurement is the *processed-measured* artifact of the card (five
repetitions aligned on gauge 1, their mean, its expanded uncertainty); the
solvers are the *modelled-reference* one; the predictions of this module are
computed here and are *simulated*. Nothing merges them.
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.data import SAMPLES_DIR
from pbc.data.adapters import measured_elevation, modelled_elevation
from pbc.data.comparison import named_comparison
from pbc.data.fit import fit_curve
from pbc.data.flume import (
    BED,
    GAUGE_X,
    STILL_WATER_DEPTH,
    WAVE_HEIGHT,
    WAVE_PERIOD,
    depth_at,
    harmonics,
)
from pbc.data.plotting import COLOURS, add_credit, label_status, measured_vs_model
from pbc.data.reference.aalborg_flume import LAB_END, load_lab
from pbc.data.series import Series
from pbc.experiment import Experiment, main
from pbc.waves.water import (
    G,
    accumulated_phase,
    group_speed,
    group_travel_time,
    phase_speed,
    propagate,
    shallow_wavenumber,
    wavenumber,
)

DATA_DIR = SAMPLES_DIR / "aalborg-submerged-bar"
GAUGES = tuple(GAUGE_X)
REPETITIONS = tuple(f"rep {k}" for k in range(1, 6))
CREDIT = (
    "Data: Andersen, Eldrup, Ferri, Verao Fernandez, Aalborg University, Zenodo "
    "10.5281/zenodo.15049542, CC BY 4.0. Subset of the published files; the "
    "harmonic fits, the windows, and the linear predictions are ours."
)
SOLVER_LABEL = "modelled-reference"  # the artifact type of the card

# region: wave
FREQUENCY = 1 / WAVE_PERIOD  # Hz, the wavemakers' period
OMEGA = 2 * np.pi * FREQUENCY  # rad/s
HARMONIC_COUNT = 3  # harmonics fitted at each gauge
# endregion: wave
# region: windows
DELAY = WAVE_PERIOD  # s after the arrival of the front
LENGTH = 3 * WAVE_PERIOD  # s, three whole periods
# endregion: windows
# region: clusters
# Gauges closer together than half a wavelength, so that the phase between
# neighbours needs no choice of the whole number of cycles.
CLUSTERS = {
    "before the bar": (1, 2, 3, 4, 5),
    "on the crest": (8, 9),
    "behind the bar": (13, 14, 15, 16, 17, 18, 19),
}
# endregion: clusters
# region: propagation
FROM_GAUGE, TO_GAUGE = 1, 5  # both on the flat bed before the bar
STEADY = (6.0, 12.0)  # s; four whole periods, steady at both gauges
# endregion: propagation


def wrap(phase):
    """A phase difference brought into (-pi, pi]."""
    return np.pi - np.mod(np.pi - np.asarray(phase, dtype=float), 2 * np.pi)


def load():
    """The committed sample: the experiment at every gauge, the three
    solvers with all their gauges."""
    return load_lab(DATA_DIR)


def arrival_time(time, mean) -> float:
    """The first time (s) at which the root-mean-square elevation over the
    last period reaches half of its largest value in the record."""
    keep = time <= LAB_END
    t, y = time[keep], mean[keep]
    n = round(WAVE_PERIOD / np.median(np.diff(t)))
    total = np.concatenate([[0.0], np.cumsum(y**2)])
    rms = np.sqrt((total[n:] - total[:-n]) / n)
    return float(t[n - 1 :][np.argmax(rms >= 0.5 * rms.max())])


def gauge_phases(experiment):
    """At every gauge: the arrival, the window, and the harmonics of the
    mean; the phase of the fundamental relative to gauge 1 for the mean and
    for each repetition, and the standard error of the mean phase from the
    spread of the repetitions."""
    rows = {}
    reference = None
    for gauge in GAUGES:
        record = experiment[gauge]
        t = record.time
        mean = record.column(gauge, "mean")
        start = arrival_time(t, mean) + DELAY
        window = (start, start + LENGTH)
        amplitudes = harmonics(t, mean, FREQUENCY, HARMONIC_COUNT, window)
        repetitions = np.array(
            [
                harmonics(t, record.column(gauge, r), FREQUENCY, 1, window)[0]
                for r in REPETITIONS
            ]
        )
        lag = -np.angle(amplitudes[0])
        lags = -np.angle(repetitions)
        if reference is None:
            reference = (lag, lags)
        relative = wrap(lag - reference[0])
        each = wrap(lags - reference[1])
        spread = wrap(each - relative)
        rows[gauge] = {
            "x": GAUGE_X[gauge],
            "depth": float(depth_at(GAUGE_X[gauge])),
            "arrival": start - DELAY,
            "window": window,
            "amplitudes": np.abs(amplitudes),
            "phase": float(relative),
            "sigma": float(np.std(spread, ddof=1) / np.sqrt(len(REPETITIONS))),
        }
    return rows


def predicted_phases(bed: str = "i-VoF", g: float = G):
    """The phase relative to gauge 1 at every gauge, from the dispersion
    relation and from the long-wave limit, accumulated along ``bed``."""
    x = np.array([GAUGE_X[k] for k in GAUGES])
    depth = partial(depth_at, bed=bed)
    start = GAUGE_X[GAUGES[0]]
    linear = accumulated_phase(x, depth, OMEGA, start=start, g=g)
    long_wave = accumulated_phase(x, depth, OMEGA, start=start, dispersive=False, g=g)
    return linear, long_wave


def solver_phases(models, rows):
    """The phase of each solver's fundamental relative to its own gauge 1, in
    the measurement's window of each gauge; NaN where the run does not cover
    the window."""
    out = {}
    for name, model in models.items():
        lags = {}
        for k, gauge in enumerate(GAUGES):
            window = rows[gauge]["window"]
            column = model.values[:, k]
            inside = (model.time >= window[0]) & (model.time <= window[1])
            covered = model.time[np.isfinite(column)]
            if covered.max() < window[1] or not inside.any():
                lags[gauge] = np.nan
                continue
            a = harmonics(model.time, column, FREQUENCY, 1, window)[0]
            lags[gauge] = -np.angle(a)
        first = lags[GAUGES[0]]
        out[name] = {g: float(wrap(v - first)) for g, v in lags.items()}
    return out


def phase_run(experiment: Experiment, rows, models):
    """The measured phases against both predictions and the solvers; record
    the table of every gauge."""
    linear, long_wave = predicted_phases()
    solvers = solver_phases(models, rows)
    table = []
    for k, gauge in enumerate(GAUGES):
        r = rows[gauge]
        table.append(
            (
                gauge,
                r["x"],
                r["depth"] * 100,
                r["arrival"],
                1000 * r["amplitudes"][0],
                1000 * r["amplitudes"][1],
                r["phase"],
                1000 * r["sigma"],
                float(wrap(r["phase"] - linear[k])),
                float(wrap(r["phase"] - long_wave[k])),
            )
        )
    experiment.table(
        "phase-table",
        table,
        [
            ("gauge", "", ""),
            ("position", "m", ".3f"),
            ("depth", "cm", ".1f"),
            ("arrival", "s", ".2f"),
            ("first harmonic", "mm", ".1f"),
            ("second harmonic", "mm", ".1f"),
            ("phase from gauge 1, wrapped", "rad", ".3f"),
            ("its standard error", "mrad", ".1f"),
            ("minus linear theory, wrapped", "rad", ".3f"),
            ("minus long-wave limit, wrapped", "rad", ".3f"),
        ],
        "The measured fundamental at every gauge in a window of three periods "
        "starting one period after the front: amplitudes of the first two "
        "harmonics, the phase relative to gauge 1 (wrapped into one cycle), its "
        "standard error from the five repetitions, and the difference to each "
        "prediction accumulated along the bed, wrapped.",
    )
    residual_linear = np.array([row[8] for row in table])
    residual_long = np.array([row[9] for row in table])
    solver_rows = []
    for name, phases in solvers.items():
        measured = np.array([rows[g]["phase"] for g in GAUGES])
        shown = np.array([phases[g] for g in GAUGES])
        ok = np.isfinite(shown)
        difference = wrap(shown[ok] - measured[ok])
        last = max(g for g, v in phases.items() if np.isfinite(v))
        solver_rows.append(
            (
                f"{name}, {SOLVER_LABEL}",
                int(ok.sum()),
                last,
                float(np.sqrt(np.mean(difference**2))),
                float(np.max(np.abs(difference))),
            )
        )
    experiment.table(
        "solver-table",
        solver_rows,
        [
            ("solver", "", ""),
            ("gauges covered", "", ""),
            ("last gauge", "", ""),
            ("RMS difference to the measurement", "rad", ".3f"),
            ("largest difference", "rad", ".3f"),
        ],
        "The phase of each solver's fundamental, relative to its own gauge 1, "
        "against the measured phase, in the measurement's window of every gauge "
        "that the run covers. The runs end at different times, so they cover "
        "different gauges.",
    )
    return linear, long_wave, residual_linear, residual_long, solvers, solver_rows


def _line(x, c, k):
    return c + k * x


def cluster_fit(rows, gauges):
    """The local wavenumber of a cluster: a straight line through the phases
    of its gauges, unwrapped along the cluster. Two uncertainties: with the
    standard errors of the repetitions (absolute), and from the scatter
    about the line (as if the uncertainties were unknown)."""
    x = np.array([rows[g]["x"] for g in gauges])
    phase = np.unwrap([rows[g]["phase"] for g in gauges])
    sigma = np.array([rows[g]["sigma"] for g in gauges])
    if len(gauges) == 2:
        k = (phase[1] - phase[0]) / (x[1] - x[0])
        stat = float(np.hypot(*sigma) / (x[1] - x[0]))
        return {"k": float(k), "stat": stat, "scatter": None, "reduced_chi2": None}
    guess = [phase[0], (phase[-1] - phase[0]) / (x[-1] - x[0])]
    weighted = fit_curve(_line, x, phase, guess, sigma=sigma, names=("c", "k"))
    scatter = fit_curve(_line, x, phase, guess, names=("c", "k"))
    return {
        "k": weighted.value("k"),
        "stat": float(weighted.stderr[1]),
        "scatter": float(scatter.stderr[1]),
        "reduced_chi2": weighted.reduced_chi2,
        "k_scatter": scatter.value("k"),
    }


def cluster_run(experiment: Experiment, rows):
    """The local wavenumber of each cluster against both predictions at its
    depth; record the table."""
    table = []
    fits = {}
    for name, gauges in CLUSTERS.items():
        fit = cluster_fit(rows, gauges)
        depth = float(depth_at(GAUGE_X[gauges[0]]))
        linear = float(wavenumber(OMEGA, depth))
        long_wave = float(shallow_wavenumber(OMEGA, depth))
        sigma = (
            fit["stat"] if fit["scatter"] is None else max(fit["stat"], fit["scatter"])
        )
        fit.update(depth=depth, linear=linear, long_wave=long_wave, sigma=sigma)
        fits[name] = fit
        table.append(
            (
                name,
                f"{gauges[0]} to {gauges[-1]}",
                depth * 100,
                fit["k"],
                fit["stat"],
                np.nan if fit["scatter"] is None else fit["scatter"],
                linear,
                long_wave,
                (fit["k"] - linear) / sigma,
                (fit["k"] - long_wave) / sigma,
            )
        )
    experiment.table(
        "cluster-table",
        table,
        [
            ("cluster", "", ""),
            ("gauges", "", ""),
            ("depth", "cm", ".1f"),
            ("measured k", "rad/m", ".3f"),
            ("error, repetitions", "rad/m", ".3f"),
            ("error, scatter", "rad/m", ".3f"),
            ("linear theory", "rad/m", ".3f"),
            ("long-wave limit", "rad/m", ".3f"),
            ("(measured - linear) / error", "", ".1f"),
            ("(measured - long wave) / error", "", ".1f"),
        ],
        "The local wavenumber of each cluster of gauges, the slope of the phase "
        "against position, with the error from the repetitions and the error from "
        "the scatter about the line (none for two gauges), against the two "
        "predictions at the cluster's depth. The error in the last two columns is "
        "the larger of the two.",
    )
    return fits


def model_spread():
    """How much the predicted wavenumber of the flat bed moves with the
    inputs: the gravity of the other solver and a depth 3 mm off, the
    difference of the two solvers' bars."""
    base = float(wavenumber(OMEGA, STILL_WATER_DEPTH))
    gravity = float(wavenumber(OMEGA, STILL_WATER_DEPTH, g=9.82)) - base
    depth = float(wavenumber(OMEGA, STILL_WATER_DEPTH - 0.003)) - base
    linear_ivof, _ = predicted_phases("i-VoF")
    linear_dsph, _ = predicted_phases("D-SPH")
    bars = float(np.max(np.abs(linear_ivof - linear_dsph)))
    return gravity, depth, bars


def arrival_run(rows):
    """The arrival of the front at every gauge against three travel times
    along the bed: at the group speed, at the phase speed, and at the
    long-wave speed, each with the offset that fits best (the start of the
    wavemaker is not in the files)."""
    x = np.array([GAUGE_X[g] for g in GAUGES])
    arrival = np.array([rows[g]["arrival"] for g in GAUGES])
    travel = {
        "group speed": group_travel_time(x, depth_at, OMEGA, start=0.0),
        "phase speed": _travel(x, lambda h: 1 / phase_speed(OMEGA, h)),
        "long-wave speed": _travel(x, lambda h: 1 / np.sqrt(G * h)),
    }
    fits = {}
    for name, tau in travel.items():
        offset = float(np.mean(arrival - tau))
        residual = arrival - tau - offset
        fits[name] = {
            "tau": tau,
            "offset": offset,
            "rms": float(np.sqrt(np.mean(residual**2))),
            "largest": float(np.max(np.abs(residual))),
        }
    return x, arrival, fits


def _travel(x, slowness):
    """The integral of ``slowness`` of the local depth from 0 to each x."""
    s = np.linspace(0.0, x.max(), 20001)
    values = slowness(depth_at(s))
    total = np.concatenate(
        [[0.0], np.cumsum(0.5 * (values[1:] + values[:-1]) * np.diff(s))]
    )
    return np.interp(x, s, total)


def propagation_run(experiment_data, models):
    """Gauge 1 carried to gauge 5 over the flat bed by linear theory, with
    and without dispersion, against the measurement at gauge 5; the solvers
    at gauge 5 beside them. Returns the measured series, the predictions as
    series, and the comparator's data."""
    distance = GAUGE_X[TO_GAUGE] - GAUGE_X[FROM_GAUGE]
    # Half a sample short of the end, so that the window holds whole periods.
    stop = STEADY[1] - 0.5 / 150
    source = measured_elevation(experiment_data[FROM_GAUGE], FROM_GAUGE)
    source = source.select(STEADY[0], stop)
    measured = measured_elevation(experiment_data[TO_GAUGE], TO_GAUGE)
    measured = measured.select(STEADY[0], stop)
    if not np.allclose(source.x, measured.x):
        raise ValueError("the two gauges' windows differ")
    t1, y1, t5 = source.x, source.y, measured.x
    predictions = {}
    for label, dispersive in (
        ("linear dispersion, from gauge 1", True),
        ("wave equation, no dispersion, from gauge 1", False),
    ):
        y = propagate(t1, y1, distance, STILL_WATER_DEPTH, dispersive=dispersive)
        predictions[label] = Series(
            x=t5, y=y, artifact="synthetic-test",
            x_name="time", x_unit="s", y_name="surface elevation", y_unit="m",
        )  # fmt: skip
    solvers = {}
    for name, model in models.items():
        if np.nanmax(model.time[np.isfinite(model.values[:, 0])]) < STEADY[1]:
            continue  # the run ends inside the window
        column = GAUGES.index(TO_GAUGE)
        single = type(model)(
            time=model.time, gauges=(TO_GAUGE,), labels=("surface elevation",),
            values=model.values[:, column : column + 1],
        )  # fmt: skip
        solvers[f"{name}, {SOLVER_LABEL}"] = modelled_elevation(single).select(*STEADY)
    return measured, predictions, solvers


def comparison_data(measured, predictions, solvers):
    """The comparator's data: every model on the measurement's samples."""
    models = {name: s.y for name, s in predictions.items()}
    for name, s in solvers.items():
        models[name] = s.interpolate_to(measured.x).y
    return named_comparison(
        measured.x, measured.y,
        {k: v for k, v in models.items() if np.isfinite(v).all()},
        window=STEADY, quantity="surface elevation at gauge 5", unit="mm",
        measured_label="measured mean, gauge 5",
        title="surface elevation at gauge 5 (mm), measured and model",
        notes=["models: linear predictions from gauge 1 (simulated) and the "
               "solvers of the archive (modelled-reference, interpolated)"],
        scale=1000.0,
    )  # fmt: skip


def draw_records(experiment_data, rows) -> Figure:
    """The measured mean at three gauges along the flume, with the band of one
    standard uncertainty, the arrival, and the analysis window."""
    shown = (1, 9, 13)
    fig, axes = plt.subplots(
        len(shown), 1, figsize=(5.4, 3.9), sharex=True, constrained_layout=True
    )
    for row, (ax, gauge) in enumerate(zip(axes, shown, strict=True)):
        series = measured_elevation(experiment_data[gauge], gauge)
        keep = series.x <= LAB_END
        mm = 1000

        def label(text, first=row == 0):  # the legend of the first panel
            return text if first else "_nolegend_"

        ax.fill_between(
            series.x[keep], mm * (series.y - series.sigma)[keep],
            mm * (series.y + series.sigma)[keep], color=COLOURS[0], alpha=0.3, lw=0,
            label=label("1 standard uncertainty of the mean"),
        )  # fmt: skip
        ax.plot(
            series.x[keep], mm * series.y[keep], color=COLOURS[0], lw=0.9,
            label=label("measured mean [processed]"),
        )  # fmt: skip
        ax.axvspan(
            *rows[gauge]["window"], color="0.5", alpha=0.18, lw=0,
            label=label("window"),
        )  # fmt: skip
        ax.axvline(
            rows[gauge]["arrival"], color=COLOURS[1], ls=":", lw=1.4,
            label=label("arrival"),
        )  # fmt: skip
        ax.set_ylabel("η [mm]")
        ax.set_title(f"gauge {gauge}, x = {GAUGE_X[gauge]:.2f} m", fontsize=9)
    axes[0].legend(fontsize=7, ncols=2, loc="lower center", bbox_to_anchor=(0.5, 1.35))
    axes[-1].set_xlabel("time [s]")
    label_status(fig, "processed")
    add_credit(fig, CREDIT)
    return fig


def draw_arrival(x, arrival, fits) -> Figure:
    """The arrival of the front against position, with the three travel
    times, and the residuals."""
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(5.4, 4.2), sharex=True, constrained_layout=True,
        gridspec_kw={"height_ratios": [2, 1]},
    )  # fmt: skip
    top.plot(x, arrival, "o", color=COLOURS[0], label="measured arrival [processed]")
    styles = ("--", "-.", ":")
    s = np.linspace(0, x.max(), 400)
    for k, (name, fit) in enumerate(fits.items()):
        colour = COLOURS[k + 1]
        tau = np.interp(s, x, fit["tau"])  # for the line only, between gauges
        top.plot(
            s[s >= x[0]], (tau + fit["offset"])[s >= x[0]], styles[k], color=colour,
            label=f"travel at the {name}, linear theory [simulated]",
        )  # fmt: skip
        bottom.plot(
            x, arrival - fit["tau"] - fit["offset"], styles[k], marker="s",
            color=colour, ms=4, label=f"{name}: RMS {fit['rms']:.2f} s",
        )  # fmt: skip
    bottom.axhline(0, color="0.5", lw=0.8)
    top.set_ylabel("time [s]")
    top.set_ylim(top=19)  # room for the legend above the arrivals
    top.set_title("Arrival of the front (half its final RMS) and three travel times")
    top.legend(fontsize=7, loc="upper left")
    bottom.set_ylabel("residual [s]")
    bottom.set_xlabel("position along the flume [m]")
    bottom.set_title("Residual: measured minus travel time and its best offset")
    bottom.set_ylim(-1.6, 3.2)
    bottom.legend(fontsize=6.5, loc="upper left", ncols=2)
    label_status(fig, "processed")
    add_credit(fig, CREDIT)
    return fig


def draw_phase(rows, residual_linear, residual_long, solvers) -> Figure:
    """The measured phase minus each prediction at every gauge, wrapped, with
    the standard errors; the solvers' phase minus the measured one; the bed
    with the gauges below."""
    x = np.array([GAUGE_X[g] for g in GAUGES])
    sigma = np.array([rows[g]["sigma"] for g in GAUGES])
    fig, (top, middle, bed) = plt.subplots(
        3, 1, figsize=(6.4, 6), sharex=True, constrained_layout=True,
        gridspec_kw={"height_ratios": [2, 1.4, 1]},
    )  # fmt: skip
    top.errorbar(
        x, residual_linear, yerr=sigma, fmt="o", color=COLOURS[0], capsize=2,
        label="measured minus linear dispersion [processed]",
    )  # fmt: skip
    top.errorbar(
        x, residual_long, yerr=sigma, fmt="s", mfc="none", color=COLOURS[1], capsize=2,
        label="measured minus long-wave limit, no dispersion [processed]",
    )  # fmt: skip
    top.axhline(0, color="0.5", lw=0.8)
    top.set_ylim(-np.pi, np.pi)
    top.set_ylabel("phase difference [rad]")
    top.set_title(
        "Phase of the fundamental from gauge 1: measured minus prediction, wrapped"
    )
    top.legend(fontsize=8, loc="lower left")
    measured = np.array([rows[g]["phase"] for g in GAUGES])
    markers = ("^", "v", "D")
    for k, (name, phases) in enumerate(solvers.items()):
        shown = np.array([phases[g] for g in GAUGES])
        middle.plot(
            x, wrap(shown - measured), markers[k], ls="--", lw=0.8,
            color=COLOURS[k + 2],
            label=f"{name}, {SOLVER_LABEL} [simulated], minus measured",
        )  # fmt: skip
    middle.axhline(0, color="0.5", lw=0.8)
    middle.set_ylabel("phase difference [rad]")
    middle.set_title("Solvers: their phase from their gauge 1 minus the measured one")
    middle.set_ylim(-0.5, 0.1)
    middle.legend(fontsize=6.5, loc="lower left")
    s = np.linspace(0, 15.5, 600)
    for k, name in enumerate(BED):
        bed.plot(
            s, -100 * depth_at(s, name), ("-", "--")[k], color=("0.2", "0.55")[k],
            label=f"bed of the {name} input files",
        )  # fmt: skip
    bed.plot(x, np.zeros_like(x), "|", color=COLOURS[0], ms=10, label="gauges")
    bed.set_ylabel("height [cm]")
    bed.set_xlabel("position along the flume [m]")
    bed.set_title("The bed below still water", fontsize=9)
    bed.legend(fontsize=7, ncols=3, loc="lower right")
    label_status(fig, "processed")
    add_credit(fig, CREDIT)
    return fig


def draw_waveform(measured, predictions) -> Figure:
    """Gauge 5, measured, against the two predictions from gauge 1, with the
    residuals. The solvers are in the comparator and its table."""
    fig, (top, bottom) = measured_vs_model(
        measured, predictions, window=STEADY, figsize=(5.8, 4.8)
    )
    top.set_title(
        f"Gauge {TO_GAUGE}: measured mean (solid), predictions from gauge "
        f"{FROM_GAUGE} (dashed)"
    )
    top.legend(fontsize=6.5, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    bottom.legend(fontsize=6.5, loc="upper center", bbox_to_anchor=(0.5, -0.48))
    add_credit(fig, CREDIT)
    return fig


def waveform_table(experiment: Experiment, comparison) -> None:
    """The metrics of every model of the comparator at gauge 5; the text
    alternative of the comparator."""
    experiment.table(
        "waveform-table",
        [
            (
                m["parameter"],
                m["metrics"]["rms_residual"],
                m["metrics"]["largest_residual"],
                m["metrics"]["correlation"],
            )
            for m in comparison["models"]
        ],
        [
            ("model", "", ""),
            ("RMS residual", "mm", ".2f"),
            ("largest residual", "mm", ".2f"),
            ("correlation", "", ".4f"),
        ],
        "Every model against the measured mean at gauge 5 in the window: our "
        "two predictions from gauge 1 (simulated) and the three solvers "
        "(modelled-reference, interpolated to the measurement's samples).",
    )


def dispersion_example():
    """The example of the theory section: the wave of the flume at the two
    depths, with its speeds and the depth parameter k h."""
    rows = []
    for depth in (STILL_WATER_DEPTH, BED["i-VoF"][1][1]):
        k = float(wavenumber(OMEGA, depth))
        rows.append(
            (
                depth * 100,
                k,
                k * depth,
                2 * np.pi / k,
                float(phase_speed(OMEGA, depth)),
                float(group_speed(OMEGA, depth)),
                float(np.sqrt(G * depth)),
            )
        )
    return rows


def longer_period():
    """Exercise 1: a wave of period 2 s in the flume's 0.3 m of water."""
    omega = 2 * np.pi / 2.0
    k = float(wavenumber(omega, 0.3))
    c = float(phase_speed(omega, 0.3))
    long_wave = float(np.sqrt(G * 0.3))
    print(f"k h = {k * 0.3:.2f}")
    print(f"wavelength: {2 * np.pi / k:.2f} m")
    print(f"phase speed: {c:.3f} m/s")
    print(f"group speed: {float(group_speed(omega, 0.3)):.3f} m/s")
    print(f"long-wave speed: {long_wave:.3f} m/s")
    print(f"long-wave speed above the phase speed: {100 * (long_wave / c - 1):.1f} %")


def cycles_in_the_gap():
    """Exercise 2: the whole cycles between gauges 12 and 13 by each model."""
    gap = (GAUGE_X[12], GAUGE_X[13])
    linear = accumulated_phase(np.array(gap), depth_at, OMEGA, start=gap[0])[1]
    long_wave = accumulated_phase(
        np.array(gap), depth_at, OMEGA, start=gap[0], dispersive=False
    )[1]
    print(f"linear dispersion: {linear / (2 * np.pi):.2f} cycles")
    print(f"long-wave limit:   {long_wave / (2 * np.pi):.2f} cycles")
    print(f"difference:        {(linear - long_wave) / (2 * np.pi):.2f} cycles")


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment_data, models = load()

    example = dispersion_example()
    experiment.table(
        "dispersion-example",
        example,
        [
            ("depth", "cm", ".1f"),
            ("k", "rad/m", ".3f"),
            ("k h", "", ".2f"),
            ("wavelength", "m", ".3f"),
            ("phase speed", "m/s", ".3f"),
            ("group speed", "m/s", ".3f"),
            ("long-wave speed", "m/s", ".3f"),
        ],
        "The wave of the flume, period 1.5 s, by the linear dispersion relation "
        "on the flat bed and on the crest of the bar, with the speed sqrt(g h) "
        "that the wave equation would give it.",
    )
    flat, crest = example
    experiment.number("period", WAVE_PERIOD, ".1f")
    experiment.number("height-low", WAVE_HEIGHT[0] * 1000, ".0f")
    experiment.number("height-high", WAVE_HEIGHT[1] * 1000, ".0f")
    experiment.number("depth", STILL_WATER_DEPTH * 100, ".0f")
    experiment.number("crest-depth", crest[0], ".1f")
    experiment.number("kh-flat", flat[2], ".2f")
    experiment.number("kh-crest", crest[2], ".2f")
    experiment.number("wavelength", flat[3], ".2f")
    experiment.number("c-flat", flat[4], ".2f")
    experiment.number("cg-flat", flat[5], ".2f")
    experiment.number("long-flat", flat[6], ".2f")
    experiment.number("long-excess", (flat[6] / flat[4] - 1) * 100, ".0f")

    rows = gauge_phases(experiment_data)
    experiment.figure("fig-records", partial(draw_records, experiment_data, rows))
    experiment.number("last-window-end", rows[GAUGES[-1]]["window"][1], ".1f")
    experiment.number("lab-end", LAB_END, ".0f")

    x, arrival, arrival_fits = arrival_run(rows)
    experiment.figure("fig-arrival", partial(draw_arrival, x, arrival, arrival_fits))
    for name, key in (
        ("group speed", "group"), ("phase speed", "phase"), ("long-wave speed", "long"),
    ):  # fmt: skip
        experiment.number(f"arrival-rms-{key}", arrival_fits[name]["rms"], ".2f")
    largest = arrival_fits["group speed"]["largest"]
    experiment.number("arrival-largest-group", largest, ".2f")

    phases = phase_run(experiment, rows, models)
    linear, _, residual_linear, residual_long, solvers, solver_rows = phases
    experiment.figure(
        "fig-phase",
        partial(draw_phase, rows, residual_linear, residual_long, solvers),
    )
    experiment.number("total-phase", linear[-1], ".1f")
    experiment.number("worst-linear", np.max(np.abs(residual_linear)), ".2f")
    experiment.number("rms-linear", np.sqrt(np.mean(residual_linear**2)), ".2f")
    experiment.number("worst-long", np.max(np.abs(residual_long)), ".2f")
    sigmas = np.array([rows[g]["sigma"] for g in GAUGES])
    experiment.number("sigma-low", 1000 * sigmas[1:].min(), ".1f")
    experiment.number("sigma-high", 1000 * sigmas.max(), ".1f")
    experiment.number("solvers-worst", max(r[4] for r in solver_rows), ".2f")

    fits = cluster_run(experiment, rows)
    before, crest_fit, behind = (fits[n] for n in CLUSTERS)
    experiment.number("k-before", before["k"], ".3f")
    experiment.number("k-before-sigma", before["sigma"], ".3f")
    experiment.number("k-behind", behind["k"], ".3f")
    experiment.number("k-behind-sigma", behind["sigma"], ".3f")
    experiment.number("k-crest", crest_fit["k"], ".3f")
    experiment.number("k-crest-sigma", crest_fit["sigma"], ".3f")
    experiment.number("k-linear", before["linear"], ".3f")
    experiment.number("k-long", before["long_wave"], ".3f")
    experiment.number("k-crest-linear", crest_fit["linear"], ".3f")
    experiment.number("k-crest-long", crest_fit["long_wave"], ".3f")
    experiment.number("chi2-before", before["reduced_chi2"], ".0f")
    experiment.number(
        "pull-long-before",
        abs(before["k"] - before["long_wave"]) / before["sigma"],
        ".0f",
    )
    experiment.number(
        "pull-long-behind",
        abs(behind["k"] - behind["long_wave"]) / behind["sigma"],
        ".0f",
    )
    gravity, depth_shift, bars = model_spread()
    experiment.number("spread-gravity", gravity * 1000, ".1f")
    experiment.number("spread-depth", depth_shift * 1000, ".1f")
    experiment.number("spread-bars", bars, ".3f")

    measured, predictions, solver_series = propagation_run(experiment_data, models)
    experiment.figure("fig-waveform", partial(draw_waveform, measured, predictions))
    comparison = experiment.widget(
        "gauge-five", comparison_data(measured, predictions, solver_series)
    )
    waveform_table(experiment, comparison)
    by_name = {m["parameter"]: m["metrics"] for m in comparison["models"]}
    experiment.number(
        "rms-dispersive",
        by_name["linear dispersion, from gauge 1"]["rms_residual"],
        ".2f",
    )
    experiment.number(
        "rms-long",
        by_name["wave equation, no dispersion, from gauge 1"]["rms_residual"],
        ".2f",
    )
    experiment.number("distance", GAUGE_X[TO_GAUGE] - GAUGE_X[FROM_GAUGE], ".2f")
    experiment.number(
        "delay-long-ms",
        1000
        * (GAUGE_X[TO_GAUGE] - GAUGE_X[FROM_GAUGE])
        / np.sqrt(G * STILL_WATER_DEPTH),
        ".0f",
    )

    with experiment.capture("longer-period"):
        longer_period()
    with experiment.capture("cycles-in-the-gap"):
        cycles_in_the_gap()
    second = np.array([rows[g]["amplitudes"][1] for g in GAUGES])
    experiment.number("second-before", 1000 * second[0], ".1f")
    experiment.number("second-most", 1000 * second.max(), ".1f")
    experiment.number("second-most-gauge", GAUGES[int(np.argmax(second))], "d")
    return experiment


if __name__ == "__main__":
    main(run)
