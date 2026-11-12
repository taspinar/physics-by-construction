"""The experiment of the lesson "Soil temperature measurements lab".

The heat equation of the lesson "Heat conduction and diffusion" in a
homogeneous half-space with a periodic surface temperature (the damped wave
of ``pbc.thermodynamics.periodic_conduction``) against measured soil
temperatures (the committed sample of the card
``dwd-potsdam-soil-temperature``): DWD's readings at 5, 10, 20, 50, and
100 cm at Potsdam, four a day over 2015-2024 and every hour of the summers
2020-2024. The experiment checks the damped wave against T6's explicit
scheme, fits the annual and the daily harmonic at each depth, infers the
thermal diffusivity from the decay and from the lag, checks the assumptions
of its uncertainty, and tests the homogeneous model by pairs of depths. Run
it as a program to write the figures and the numbers of the page:

    uv run --locked --no-dev python -m \\
        pbc.thermodynamics.experiments.soil_temperature_measurements out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.data import SAMPLES_DIR
from pbc.data.adapters import soil_temperature_series
from pbc.data.fit import FitResult, fit_curve
from pbc.data.plotting import COLOURS, add_credit, label_status
from pbc.data.reference.dwd_soil import (
    DAY,
    DEPTHS,
    OMEGA_DAY,
    OMEGA_YEAR,
    YEAR,
    Readings,
    Wave,
    annual_wave,
    daily_amplitudes,
    diurnal_wave,
    harmonic,
    load,
    seconds,
)
from pbc.experiment import Experiment, main
from pbc.thermodynamics.periodic_conduction import (
    damping_depth,
    diffusivity_from_slope,
    periodic_ftcs,
)

DATASET = "dwd-potsdam-soil-temperature"
# region: choices
CHECK_ALPHA = 1.1e-6  # m^2/s, the diffusivity of the scheme check
CHECK_DEPTHS = (0.05, 0.10, 0.20, 0.50)  # m, the depths of the daily wave
CHECK_GRID = {"dz": 0.01, "r": 0.25, "bottom": 1.2, "periods": 8}
SHOWN_YEAR = 2020  # the year whose readings fig-harmonic-fits shows
SHOWN_SUMMER = 2024  # the summer from which it shows a typical day
WEEK_START = "2024-07-01"  # the hourly week of fig-soil-record
RESIDUAL_LAGS = (4, 40)  # readings: one day and ten days at four a day
# endregion: choices
CREDIT = (
    "Data: Deutscher Wetterdienst (DWD), Climate Data Center, hourly soil "
    "temperature of station 03987 Potsdam, archive "
    "stundenwerte_EB_03987_19510101_20251231_hist.zip, CC BY 4.0. Rows selected "
    "unchanged. Fitted harmonics, model lines and residuals: this lesson's code, "
    "not part of the record."
)
STYLES = ("-", "--", "-.", ":", (0, (5, 1, 1, 1, 1, 1)))
MARKERS = ("o", "s", "^", "D", "v")


def load_readings() -> tuple[Readings, Readings]:
    """The committed sample: the readings at 00, 06, 12, 18 h of 2015-2024,
    and every hourly reading of June to August 2020-2024."""
    return load(SAMPLES_DIR / DATASET)


# The record without a model.


def record_landmarks(annual: Readings, hourly: Readings) -> dict:
    """What the sample shows without a model: its rows, the missing values,
    and the extremes at the shallowest and the deepest sensor."""
    shallow = annual.temperature[:, 0]
    deep = annual.temperature[:, -1]
    days = sum(len(daily_amplitudes(hourly, year)) for year in range(2020, 2025))
    return {
        "annual-rows": int(annual.time.size),
        "hourly-rows": int(hourly.time.size),
        "missing-annual": int(np.isnan(annual.temperature).sum()),
        "missing-hourly": int(np.isnan(hourly.temperature).sum()),
        "shallow-min": float(np.nanmin(shallow)),
        "shallow-max": float(np.nanmax(shallow)),
        "deep-min": float(np.nanmin(deep)),
        "deep-max": float(np.nanmax(deep)),
        "complete-days": days,
        "summer-days": 5 * 92,
    }


def record_table(experiment: Experiment, annual: Readings) -> None:
    """Mean, lowest and highest reading at each depth over 2015-2024."""
    rows = [
        (
            f"{100 * z:.0f} cm",
            int(np.isfinite(annual.temperature[:, k]).sum()),
            float(np.nanmean(annual.temperature[:, k])),
            float(np.nanmin(annual.temperature[:, k])),
            float(np.nanmax(annual.temperature[:, k])),
        )
        for k, z in enumerate(DEPTHS)
    ]
    experiment.table(
        "record",
        rows,
        columns=[
            ("depth", "", "s"),
            ("readings", "", "d"),
            ("mean", "degC", ".1f"),
            ("lowest", "degC", ".1f"),
            ("highest", "degC", ".1f"),
        ],
        caption="The readings at 00, 06, 12 and 18 h of 2015-2024 at each depth, "
        "read from the sample without a model.",
    )


# The model checked against T6's scheme.


def scheme_check(experiment: Experiment) -> dict:
    """T6's explicit scheme driven by a daily cosine at the surface against
    the damped wave: amplitude and lag at the depths of the daily wave."""
    depths = np.array(CHECK_DEPTHS)
    amplitude, lag = periodic_ftcs(CHECK_ALPHA, OMEGA_DAY, depths, **CHECK_GRID)
    d = damping_depth(CHECK_ALPHA, OMEGA_DAY)
    exact_a, exact_lag = np.exp(-depths / d), depths / d
    experiment.table(
        "scheme-check",
        [
            (f"{100 * z:.0f} cm", ea, a, el, lg)
            for z, ea, a, el, lg in zip(
                depths, exact_a, amplitude, exact_lag, lag, strict=True
            )
        ],
        columns=[
            ("depth", "", "s"),
            ("exp(-z/d)", "", ".4f"),
            ("scheme amplitude", "", ".4f"),
            ("z/d", "rad", ".4f"),
            ("scheme lag", "rad", ".4f"),
        ],
        caption="The explicit scheme of the heat-conduction lesson with the surface "
        "held at a daily cosine of unit amplitude, after eight days, against the "
        "damped wave of the same diffusivity.",
    )
    return {
        "damping-depth": d,
        "amplitude-error": float(np.max(np.abs(amplitude / exact_a - 1))),
        "lag-error": float(np.max(np.abs(lag - exact_lag))),
    }


# The harmonics of the record.


def year_fit(annual: Readings, year: int, column: int) -> tuple:
    """The annual harmonic fitted to one year's readings at one depth with
    ``fit_curve``: (days into the year, readings, the fit). Its standard
    errors assume independent readings."""
    start = np.datetime64(f"{year}-01-01T00", "h")
    inside = (annual.time >= start) & (
        annual.time < np.datetime64(f"{year + 1}-01-01T00", "h")
    )
    t = seconds(annual.time[inside], start)
    y = annual.temperature[inside, column]
    ok = np.isfinite(y)
    result = fit_curve(
        lambda x, m, a, b: m + a * np.cos(OMEGA_YEAR * x) + b * np.sin(OMEGA_YEAR * x),
        t[ok],
        y[ok],
        [10.0, -10.0, 0.0],
        names=("mean", "a", "b"),
    )
    return t[ok] / DAY, y[ok], result


def amplitude_error(result: FitResult) -> float:
    """The standard error of sqrt(a^2 + b^2) from the covariance of a, b."""
    a, b = result.value("a"), result.value("b")
    gradient = np.array([0.0, a, b]) / np.hypot(a, b)
    return float(np.sqrt(gradient @ result.covariance @ gradient))


def typical_day(hourly: Readings, summer: int) -> np.datetime64:
    """The complete day of June to August of ``summer`` whose daily amplitude
    at 5 cm is closest to the median of that summer's days."""
    day = np.datetime64(f"{summer}-06-01", "D")
    days, amplitudes = [], []
    while day < np.datetime64(f"{summer}-09-01", "D"):
        start = day.astype("datetime64[h]")
        inside = (hourly.time >= start) & (
            hourly.time < start + np.timedelta64(24, "h")
        )
        if inside.sum() == 24 and np.all(np.isfinite(hourly.temperature[inside, :4])):
            days.append(day)
            amplitudes.append(np.ptp(hourly.temperature[inside, 0]))
        day += np.timedelta64(1, "D")
    amplitudes = np.array(amplitudes)
    return days[int(np.argmin(np.abs(amplitudes - np.median(amplitudes))))]


def day_fit(hourly: Readings, day: np.datetime64, column: int) -> tuple:
    """The daily harmonic with a mean and a linear trend over the day, fitted
    to one day's 24 hourly readings at one depth: (hours, readings, fit)."""
    start = day.astype("datetime64[h]")
    inside = (hourly.time >= start) & (hourly.time < start + np.timedelta64(24, "h"))
    t = seconds(hourly.time[inside], start)
    y = hourly.temperature[inside, column]
    centre = float(t.mean())
    result = fit_curve(
        lambda x, m, s, a, b: (
            m + s * (x - centre) + a * np.cos(OMEGA_DAY * x) + b * np.sin(OMEGA_DAY * x)
        ),
        t,
        y,
        [20.0, 0.0, -1.0, 0.0],
        names=("mean", "trend", "a", "b"),
    )
    return t / 3600.0, y, result, centre


def deep_daily_amplitude(hourly: Readings) -> float:
    """The daily harmonic at 100 cm: the mean complex amplitude of every
    complete summer day, fitted as at the shallower depths."""
    amplitudes = []
    day = np.datetime64(f"{hourly.time[0].astype('datetime64[Y]')}-06-01", "D")
    while day <= hourly.time[-1].astype("datetime64[D]"):
        start = day.astype("datetime64[h]")
        inside = (hourly.time >= start) & (
            hourly.time < start + np.timedelta64(24, "h")
        )
        values = hourly.temperature[inside, -1]
        if inside.sum() == 24 and np.all(np.isfinite(values)):
            t = seconds(hourly.time[inside], start)
            amplitudes.append(harmonic(t, values, OMEGA_DAY, trend=True))
        day += np.timedelta64(1, "D")
    return float(abs(np.mean(amplitudes)))


def wave_table(experiment: Experiment, annual: Wave, diurnal: Wave) -> None:
    """Amplitude and lag of both harmonics at each depth: the mean over the
    years or summers, with the standard error of that mean."""
    rows = []
    for k, z in enumerate(DEPTHS):
        a_mean = annual.amplitude[:, k].mean()
        a_err = annual.amplitude[:, k].std(ddof=1) / np.sqrt(len(annual.periods))
        a_lag = annual.lag[:, k].mean() / OMEGA_YEAR / DAY
        if k < diurnal.depths.size:
            d_mean = diurnal.amplitude[:, k].mean()
            d_err = diurnal.amplitude[:, k].std(ddof=1) / np.sqrt(len(diurnal.periods))
            d_lag = diurnal.lag[:, k].mean() / OMEGA_DAY / 3600.0
            daily = (f"{d_mean:.2f} ± {d_err:.2f}", f"{d_lag:.1f}")
        else:
            daily = ("below the 0.1 K of the readings", "")
        rows.append((f"{100 * z:.0f} cm", f"{a_mean:.2f} ± {a_err:.2f}", a_lag, *daily))
    experiment.table(
        "wave",
        rows,
        columns=[
            ("depth", "", "s"),
            ("annual amplitude", "K", "s"),
            ("annual lag behind 5 cm", "d", ".1f"),
            ("daily amplitude", "K", "s"),
            ("daily lag behind 5 cm", "h", "s"),
        ],
        caption="The annual harmonic (mean of the ten years 2015-2024) and the daily "
        "harmonic (mean of the five summers 2020-2024) at each depth, with the "
        "standard error of the mean over the years or summers.",
    )


# The diffusivity.


def depth_line(depths: np.ndarray, values: np.ndarray) -> FitResult:
    """A straight line y = slope z + intercept through -ln A or the lag
    against depth. With no uncertainty given, its standard errors come from
    the scatter about the line, as if the departures were random."""
    return fit_curve(
        lambda z, slope, intercept: slope * z + intercept,
        depths,
        values,
        [1.0, 0.0],
        names=("slope", "intercept"),
    )


def diffusivity(wave: Wave) -> dict:
    """alpha from the decay and from the lag of the mean wave, the same from
    each year or summer alone, and their scatter."""
    n = len(wave.periods)
    amplitude, lag = wave.amplitude.mean(0), wave.lag.mean(0)
    lines = {"amplitude": depth_line(wave.depths, -np.log(amplitude))}
    lines["phase"] = depth_line(wave.depths, lag)
    out = {"lines": lines, "periods": n}
    for name, line in lines.items():
        slope, err = line.value("slope"), float(line.stderr[0])
        single = np.array(
            [
                diffusivity_from_slope(
                    depth_line(
                        wave.depths,
                        -np.log(a) if name == "amplitude" else lg,
                    ).value("slope"),
                    wave.omega,
                )
                for a, lg in zip(wave.amplitude, wave.lag, strict=True)
            ]
        )
        centred = single - single.mean()
        out[name] = {
            "alpha": diffusivity_from_slope(slope, wave.omega),
            "damping-depth": 1.0 / slope,
            "single": single,
            "sem": float(single.std(ddof=1) / np.sqrt(n)),
            # alpha ~ 1/slope^2: a relative error e of the slope is 2e of alpha.
            "line-error": 2.0 * err / slope * diffusivity_from_slope(slope, wave.omega),
            "rho1": float(np.sum(centred[1:] * centred[:-1]) / np.sum(centred**2)),
        }
    out["surface-amplitude"] = float(np.exp(-lines["amplitude"].value("intercept")))
    return out


def diffusivity_table(experiment: Experiment, annual: dict, daily: dict) -> None:
    rows = []
    for wave_name, found in (("annual", annual), ("daily", daily)):
        for method in ("amplitude", "phase"):
            f = found[method]
            rows.append(
                (
                    f"{wave_name}, from the {method}",
                    1e6 * f["alpha"],
                    1e6 * f["sem"],
                    f"{1e6 * f['single'].min():.2f} to {1e6 * f['single'].max():.2f}",
                    1e6 * f["line-error"],
                    f["damping-depth"],
                )
            )
    experiment.table(
        "diffusivity",
        rows,
        columns=[
            ("wave and method", "", "s"),
            ("alpha", "1e-6 m^2/s", ".3f"),
            ("standard error, between periods", "1e-6 m^2/s", ".3f"),
            ("single years or summers", "1e-6 m^2/s", "s"),
            ("standard error, scatter about the line", "1e-6 m^2/s", ".3f"),
            ("damping depth d", "m", ".3f"),
        ],
        caption="The thermal diffusivity from the straight lines through -ln A and "
        "the lag against depth: from the mean wave, with the standard error of the "
        "mean over the ten years or five summers, the range of the single ones, and "
        "the standard error of the line from the scatter of the depths about it.",
    )


def pairs(wave: Wave) -> list[tuple[str, float, float]]:
    """alpha between adjacent depths, from the decay and from the lag of the
    mean wave: one value for every pair if the soil is homogeneous."""
    a, lag, z = wave.amplitude.mean(0), wave.lag.mean(0), wave.depths
    out = []
    for k in range(z.size - 1):
        dz = z[k + 1] - z[k]
        out.append(
            (
                f"{100 * z[k]:.0f} to {100 * z[k + 1]:.0f} cm",
                diffusivity_from_slope(np.log(a[k] / a[k + 1]) / dz, wave.omega),
                diffusivity_from_slope((lag[k + 1] - lag[k]) / dz, wave.omega),
            )
        )
    return out


def pairs_table(experiment: Experiment, annual: Wave, diurnal: Wave) -> list:
    yearly, daily = pairs(annual), pairs(diurnal)
    rows = []
    for k, (name, ya, yp) in enumerate(yearly):
        d = ("", "")
        if k < len(daily):
            d = (f"{1e6 * daily[k][1]:.2f}", f"{1e6 * daily[k][2]:.2f}")
        rows.append((name, 1e6 * ya, 1e6 * yp, *d))
    experiment.table(
        "pairs",
        rows,
        columns=[
            ("pair of depths", "", "s"),
            ("annual, from the amplitude", "1e-6 m^2/s", ".2f"),
            ("annual, from the phase", "1e-6 m^2/s", ".2f"),
            ("daily, from the amplitude", "1e-6 m^2/s", "s"),
            ("daily, from the phase", "1e-6 m^2/s", "s"),
        ],
        caption="The diffusivity between adjacent depths, from the mean waves. A "
        "homogeneous half-space gives the same value in every cell.",
    )
    values = [v for _, a, p in yearly + daily for v in (a, p)]
    return values


# Are the errors honest?


def residual_correlation(residuals: np.ndarray, lag: int) -> float:
    """The autocorrelation of a series of residuals at ``lag`` readings."""
    c = residuals - residuals.mean()
    return float(np.sum(c[lag:] * c[:-lag]) / np.sum(c**2))


def independence_table(experiment: Experiment, annual: Readings, wave: Wave) -> dict:
    """The least-squares error of one year's annual amplitude, which assumes
    independent readings, against the scatter of the amplitude between the
    years, and the autocorrelation of one year's residuals, at 5 and 100 cm;
    each the mean over the ten years."""
    rows, found = [], {}
    for column in (0, DEPTHS.size - 1):
        errors, correlations = [], []
        for year in wave.periods:
            *_, result = year_fit(annual, year, column)
            errors.append(amplitude_error(result))
            correlations.append(
                [residual_correlation(result.residuals, k) for k in RESIDUAL_LAGS]
            )
        scatter = float(wave.amplitude[:, column].std(ddof=1))
        error = float(np.mean(errors))
        rho = np.mean(correlations, axis=0)
        rows.append((f"{100 * DEPTHS[column]:.0f} cm", error, scatter, *rho))
        found[column] = {"error": error, "scatter": scatter, "rho": rho}
    experiment.table(
        "independence",
        rows,
        columns=[
            ("depth", "", "s"),
            ("error of one year's amplitude, readings independent", "K", ".2f"),
            ("scatter of the amplitude between years", "K", ".2f"),
            ("residuals' autocorrelation at one day", "", ".2f"),
            ("residuals' autocorrelation at ten days", "", ".2f"),
        ],
        caption="Within one year the residuals of the annual harmonic are the weather, "
        "and they persist for days: the error that assumes independent readings "
        "falls far short of how much the amplitude changes from year to year. Each "
        "value is the mean over the ten years.",
    )
    return found


# The figures.


def draw_soil_record(hourly: Readings) -> Figure:
    """One summer week of hourly readings at the five depths."""
    fig, bottom = plt.subplots(figsize=(6.0, 3.2), constrained_layout=True)
    start = np.datetime64(WEEK_START, "h")
    inside = (hourly.time >= start) & (
        hourly.time < start + np.timedelta64(7 * 24, "h")
    )
    days = seconds(hourly.time[inside], start) / DAY
    for k, z in enumerate(DEPTHS):
        series = soil_temperature_series(hourly, k)
        bottom.plot(
            days,
            series.y[inside],
            lw=1.0,
            ls=STYLES[k],
            color=COLOURS[k],
            label=f"{100 * z:.0f} cm, measured [{series.status}]",
        )
    bottom.set_xlabel(f"days from {WEEK_START} 00 h (MESS_DATUM) [d]")
    bottom.set_ylabel("soil temperature [degC]")
    bottom.set_title("Hourly readings, one summer week", fontsize=10)
    bottom.set_ylim(10, 44)
    bottom.legend(fontsize=6.5, ncols=3, loc="upper center")
    add_credit(fig, CREDIT)
    label_status(fig, series.status)
    return fig


def draw_harmonic_fits(
    annual: Readings, hourly: Readings, day: np.datetime64
) -> Figure:
    """Left: one year of readings at 5 and 100 cm with the fitted annual
    harmonic; right: one summer day at 5 to 50 cm with the fitted daily
    harmonic and trend; residuals below each."""
    status = soil_temperature_series(annual, 0).status
    fig, axes = plt.subplots(
        2,
        2,
        figsize=(6.8, 5.4),
        constrained_layout=True,
        gridspec_kw={"height_ratios": [1.4, 1.0]},
    )
    (year_ax, day_ax), (year_res, day_res) = axes
    for k in (0, DEPTHS.size - 1):
        t, y, result = year_fit(annual, SHOWN_YEAR, k)
        mean, a, b = result.params
        label = f"{100 * DEPTHS[k]:.0f} cm"
        year_ax.plot(
            t,
            y,
            # The 100 cm readings vary smoothly and are joined by a line.
            ls="none" if k == 0 else "-",
            lw=0.8,
            marker="." if k == 0 else "",
            ms=2.0,
            mew=0,  # an outline adds bytes to the page, not detail
            color=COLOURS[k],
            label=f"{label} [{status}]",
        )
        grid = np.linspace(0.0, 366.0, 367)
        year_ax.plot(
            grid,
            mean
            + a * np.cos(OMEGA_YEAR * grid * DAY)
            + b * np.sin(OMEGA_YEAR * grid * DAY),
            ls="--",
            lw=1.4,
            color="0.15" if k == 0 else "0.45",
            label=f"{label}, fitted harmonic",
        )
        year_res.plot(
            t,
            result.residuals,
            # The 100 cm readings vary smoothly and are joined by a line.
            ls="none" if k == 0 else "-",
            lw=0.8,
            marker="." if k == 0 else "",
            ms=1.7,
            mew=0,  # an outline adds bytes to the page, not detail
            color=COLOURS[k],
            label=label,
        )
    year_ax.set_xlabel(f"day of {SHOWN_YEAR} [d]")
    year_ax.set_ylabel("soil temperature [degC]")
    year_ax.set_title(f"One year ({SHOWN_YEAR}), four a day", fontsize=10)
    year_ax.legend(fontsize=6, loc="upper left", ncols=2)
    year_ax.set_ylim(-6, 50)
    year_res.axhline(0, color="0.4", lw=0.8)
    year_res.set_xlabel(f"day of {SHOWN_YEAR} [d]")
    year_res.set_ylabel("residual [K]")
    year_res.set_title("Residuals: weather lasting days", fontsize=10)
    year_res.legend(fontsize=6.5, loc="upper center", ncols=2)
    year_res.set_ylim(-16, 26)

    for k in range(4):
        hours, y, result, centre = day_fit(hourly, day, k)
        label = f"{100 * DEPTHS[k]:.0f} cm"
        day_ax.plot(
            hours,
            y,
            ls="none",
            marker=MARKERS[k],
            ms=3.0,
            color=COLOURS[k],
            label=f"{label} [{status}]",
        )
        grid = np.linspace(0.0, 23.0, 93) * 3600.0
        mean, trend, a, b = result.params
        day_ax.plot(
            grid / 3600.0,
            mean
            + trend * (grid - centre)
            + a * np.cos(OMEGA_DAY * grid)
            + b * np.sin(OMEGA_DAY * grid),
            ls=STYLES[k],
            lw=1.0,
            color=COLOURS[k],
            label="fitted harmonic and trend" if k == 0 else "_fitted",
        )
        day_res.plot(
            hours,
            result.residuals,
            ls="none",
            marker=MARKERS[k],
            ms=3.0,
            color=COLOURS[k],
            label=label,
        )
    when = str(day)
    day_ax.set_xlabel(f"hour of {when} (MESS_DATUM) [h]")
    day_ax.set_ylabel("soil temperature [degC]")
    day_ax.set_title(f"One summer day ({when}), hourly", fontsize=10)
    low, high = day_ax.get_ylim()
    day_ax.set_ylim(low, high + 0.6 * (high - low))
    day_ax.legend(fontsize=6, loc="upper left", ncols=2)
    day_res.axhline(0, color="0.4", lw=0.8)
    day_res.set_xlabel(f"hour of {when} (MESS_DATUM) [h]")
    day_res.set_ylabel("residual [K]")
    day_res.set_title("Residuals of the daily fit", fontsize=10)
    low, high = day_res.get_ylim()
    day_res.set_ylim(low, high + 0.4 * (high - low))
    day_res.legend(fontsize=6.5, loc="upper center", ncols=4)
    add_credit(fig, CREDIT)
    label_status(fig, status)
    return fig


def _straight(ax, z_end: float, value, **kwargs) -> None:
    """A straight model line from z = 0 to ``z_end``, drawn from its two ends:
    Agg rasterises a long run of collinear segments differently from one
    call to the next, and the page's figure has to be the same bytes."""
    ends = np.array([0.0, z_end])
    ax.plot(ends, value(ends), **kwargs)


def draw_depth_profiles(annual: Wave, diurnal: Wave, found: dict) -> Figure:
    """Amplitude (log scale) and lag against depth for both waves, measured
    with one standard error, with the model's straight lines; residuals."""
    fig, axes = plt.subplots(
        2,
        2,
        figsize=(6.8, 5.3),
        constrained_layout=True,
        sharex="col",
        gridspec_kw={"height_ratios": [1.4, 1.0]},
    )
    (amp_ax, lag_ax), (amp_res, lag_res) = axes
    for k, (name, wave) in enumerate((("annual", annual), ("daily", diurnal))):
        f = found[name]
        n = len(wave.periods)
        z = wave.depths
        a_mean = wave.amplitude.mean(0)
        a_err = wave.amplitude.std(0, ddof=1) / np.sqrt(n)
        l_mean = wave.lag.mean(0)
        l_err = wave.lag.std(0, ddof=1) / np.sqrt(n)
        colour, marker = COLOURS[k], MARKERS[k]
        span = f"{wave.periods[0]}-{wave.periods[-1]}"
        amp_line, lag_line = f["lines"]["amplitude"], f["lines"]["phase"]
        sa, ia = amp_line.value("slope"), amp_line.value("intercept")
        sl, il = lag_line.value("slope"), lag_line.value("intercept")
        amp_ax.errorbar(
            z,
            a_mean,
            yerr=a_err,
            ls="none",
            marker=marker,
            ms=5,
            color=colour,
            label=f"{name} wave, measured [processed], {span}",
        )
        _straight(
            amp_ax,
            z[-1] + 0.05,
            lambda x, s=sa, i=ia: np.exp(-(s * x + i)),
            ls="--",
            lw=1.2,
            color=colour,
            label=f"{name}: exp(-z/d), $\\alpha$ = "
            f"{1e6 * f['amplitude']['alpha']:.2f} $\\times$ 10⁻⁶ m²/s [simulated]",
        )
        lag_ax.errorbar(
            z,
            l_mean,
            yerr=l_err,
            ls="none",
            marker=marker,
            ms=5,
            color=colour,
            label=f"{name} wave, measured [processed], {span}",
        )
        _straight(
            lag_ax,
            z[-1] + 0.05,
            lambda x, s=sl, i=il: s * x + i,
            ls="--",
            lw=1.2,
            color=colour,
            label=f"{name}: lag z/d, $\\alpha$ = "
            f"{1e6 * f['phase']['alpha']:.2f} $\\times$ 10⁻⁶ m²/s [simulated]",
        )
        amp_res.errorbar(
            z,
            -amp_line.residuals,
            yerr=a_err / a_mean,
            ls="-",
            lw=0.6,
            marker=marker,
            ms=4,
            color=colour,
            label=f"{name} wave",
        )
        lag_res.errorbar(
            z,
            lag_line.residuals,
            yerr=l_err,
            ls="-",
            lw=0.6,
            marker=marker,
            ms=4,
            color=colour,
            label=f"{name} wave",
        )
    amp_ax.set_yscale("log")
    amp_ax.set_ylim(0.04, 30)
    amp_ax.set_ylabel("amplitude of the harmonic [K]")
    amp_ax.set_title("Amplitude against depth (log scale)", fontsize=10)
    amp_ax.legend(fontsize=6, loc="lower left")
    lag_ax.set_ylim(-0.4, 4.4)
    lag_ax.set_ylabel("phase lag behind 5 cm [rad]")
    lag_ax.set_title("Phase lag against depth", fontsize=10)
    lag_ax.legend(fontsize=6, loc="upper left")
    for ax in (amp_res, lag_res):
        ax.axhline(0, color="0.4", lw=0.8)
        ax.set_xlabel("depth z [m]")
        ax.set_ylim(-0.065, 0.065)
        ax.legend(fontsize=6.5, loc="upper right", ncols=2)
    amp_res.set_ylabel("residual of ln A [1]")
    amp_res.set_title("Residuals of the line in ln A", fontsize=10)
    lag_res.set_ylabel("residual of the lag [rad]")
    lag_res.set_title("Residuals of the line in the lag", fontsize=10)
    add_credit(fig, CREDIT)
    label_status(fig, "processed")
    return fig


# The exercises.


def cellar_exercise() -> None:
    """Exercise 1: how deep must a cellar be for the annual wave to fall to a
    tenth, and how late is its warmest day there?"""
    alpha = 1.1e-6
    d = damping_depth(alpha, OMEGA_YEAR)
    depth = d * np.log(10.0)
    print(f"damping depth of the year: {d:.2f} m")
    print(f"depth where the amplitude is a tenth: {depth:.1f} m")
    print(f"lag there: {depth / d:.2f} rad, {depth / d / OMEGA_YEAR / DAY:.0f} days")


def conductivity_exercise() -> None:
    """Exercise 2: the conductivity k = alpha rho c for an assumed volumetric
    heat capacity."""
    heat_capacity = 2.0e6  # J/(m^3 K), assumed
    for name, alpha in (("lowest", 1.01e-6), ("highest", 1.15e-6)):
        print(f"from the {name} estimate: k = {alpha * heat_capacity:.2f} W/(m K)")


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    annual_readings, hourly = load_readings()

    found = record_landmarks(annual_readings, hourly)
    record_table(experiment, annual_readings)
    experiment.number("annual-rows", found["annual-rows"], ",d")
    experiment.number("hourly-rows", found["hourly-rows"], ",d")
    experiment.number("missing-annual", found["missing-annual"])
    experiment.number("missing-hourly", found["missing-hourly"])
    experiment.number("shallow-min", found["shallow-min"], ".1f")
    experiment.number("shallow-max", found["shallow-max"], ".1f")
    experiment.number("deep-min", found["deep-min"], ".1f")
    experiment.number("deep-max", found["deep-max"], ".1f")
    experiment.number("complete-days", found["complete-days"])
    experiment.number("summer-days", found["summer-days"])

    check = scheme_check(experiment)
    experiment.number("check-depth", 100 * check["damping-depth"], ".1f")
    experiment.number("check-amplitude-error", 100 * check["amplitude-error"], ".2f")
    experiment.number("check-lag-error", check["lag-error"], ".4f")

    annual = annual_wave(annual_readings)
    diurnal = diurnal_wave(hourly)
    wave_table(experiment, annual, diurnal)
    a5, a100 = annual.amplitude.mean(0)[[0, -1]]
    experiment.number("annual-a5", a5, ".1f")
    experiment.number("annual-a100", a100, ".1f")
    experiment.number("annual-lag100", annual.lag.mean(0)[-1] / OMEGA_YEAR / DAY, ".0f")
    d5, d50 = diurnal.amplitude.mean(0)[[0, -1]]
    experiment.number("daily-a5", d5, ".1f")
    experiment.number("daily-a50", d50, ".2f")
    experiment.number("daily-a100", deep_daily_amplitude(hourly), ".3f")
    experiment.number("daily-lag50", diurnal.lag.mean(0)[-1] / OMEGA_DAY / 3600, ".1f")

    day = typical_day(hourly, SHOWN_SUMMER)

    yearly, daily = diffusivity(annual), diffusivity(diurnal)
    diffusivity_table(experiment, yearly, daily)
    for prefix, f in (("year", yearly), ("day", daily)):
        for method, short in (("amplitude", "amp"), ("phase", "phase")):
            experiment.number(f"{prefix}-{short}", 1e6 * f[method]["alpha"], ".3f")
            experiment.number(f"{prefix}-{short}-err", 1e6 * f[method]["sem"], ".3f")
            experiment.number(f"{prefix}-{short}-rho1", f[method]["rho1"], "+.2f")
        experiment.number(f"{prefix}-surface", f["surface-amplitude"], ".1f")
    experiment.number("year-depth", yearly["amplitude"]["damping-depth"], ".1f")
    experiment.number("day-depth", 100 * daily["amplitude"]["damping-depth"], ".1f")
    ratios = [
        yearly[m]["damping-depth"] / daily[m]["damping-depth"]
        for m in ("amplitude", "phase")
    ]
    experiment.number("depth-ratio-amp", ratios[0], ".1f")
    experiment.number("depth-ratio-phase", ratios[1], ".1f")
    experiment.number("depth-ratio-model", np.sqrt(YEAR / DAY), ".1f")
    experiment.number("band-years", 2 / np.sqrt(yearly["periods"]), ".2f")
    experiment.number("band-summers", 2 / np.sqrt(daily["periods"]), ".2f")

    def gap(f: dict) -> float:
        a, p = f["amplitude"], f["phase"]
        return (p["alpha"] - a["alpha"]) / np.hypot(a["sem"], p["sem"])

    experiment.number("year-gap", gap(yearly), ".1f")
    experiment.number("day-gap", gap(daily), ".1f")
    four = [f[m]["alpha"] for f in (yearly, daily) for m in ("amplitude", "phase")]
    centre = float(np.mean(four))
    experiment.number("four-low", 1e6 * min(four), ".2f")
    experiment.number("four-high", 1e6 * max(four), ".2f")
    experiment.number("four-mean", 1e6 * centre, ".2f")
    experiment.number(
        "four-half-range", 100 * (max(four) - min(four)) / 2 / centre, ".0f"
    )

    values = pairs_table(experiment, annual, diurnal)
    experiment.number("pairs-low", 1e6 * min(values), ".2f")
    shallow = pairs(annual)[0]
    experiment.number("pair-shallow-amp", 1e6 * shallow[1], ".2f")
    a = annual.amplitude.mean(0)
    experiment.number("pair-shallow-drop", 100 * (1 - a[1] / a[0]), ".0f")
    rest = sorted(values)
    rest.remove(shallow[1])
    experiment.number("pairs-rest-high", 1e6 * max(rest), ".2f")

    independence = independence_table(experiment, annual_readings, annual)
    shallow_found = independence[0]
    experiment.number("ols-error", shallow_found["error"], ".2f")
    experiment.number("year-scatter", shallow_found["scatter"], ".2f")
    experiment.number(
        "scatter-ratio", shallow_found["scatter"] / shallow_found["error"], ".0f"
    )
    experiment.number("rho-day", shallow_found["rho"][0], ".2f")
    experiment.number("rho-ten-days", shallow_found["rho"][1], ".2f")

    experiment.figure("fig-soil-record", partial(draw_soil_record, hourly))
    experiment.figure(
        "fig-harmonic-fits",
        partial(draw_harmonic_fits, annual_readings, hourly, day),
    )
    experiment.figure(
        "fig-depth-profiles",
        partial(
            draw_depth_profiles, annual, diurnal, {"annual": yearly, "daily": daily}
        ),
    )

    with experiment.capture("cellar-exercise"):
        cellar_exercise()
    with experiment.capture("conductivity-exercise"):
        conductivity_exercise()
    return experiment


if __name__ == "__main__":
    main(run)
