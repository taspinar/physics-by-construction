"""DWD Potsdam soil temperature: the thermal diffusivity of the soil from the
annual and the daily temperature wave.

Status of the figure: *processed*. The thermometer readings (PT100 sensors at
5, 10, 20, 50, and 100 cm, after DWD's automatic quality control) are a
measurement; the sample selects rows of DWD's file without changing a value,
and this module fits the harmonics of the annual and of the daily cycle at
each depth and draws the heat-equation model apart from them, with residuals.

The model is the heat equation of T6 (``pbc.thermodynamics.conduction``),
dT/dt = kappa d2T/dz2, in a homogeneous half-space whose surface temperature
varies as a cosine of angular frequency omega. Its periodic solution is a wave
that decays and lags with depth z by the same length d = sqrt(2 kappa / omega),
the damping depth:

    T(z, t) = T_mean + A0 exp(-z / d) cos(omega t - z / d - phi0).

The amplitude falls by a factor e and the phase lags by one radian over d,
so kappa = omega d^2 / 2 follows twice: from the slope of ln A against z,
and from the slope of the phase lag against z. A soil that is not homogeneous
(water content, texture, compaction varying with depth) gives two different
values, and different values at different depths.

The uncertainty is the scatter of the estimate between years (the annual
wave) and between summers (the daily wave), as a standard error of the mean.
The files state no sensor accuracy and no tolerance of the depths; the
readings are given to 0.1 K. The dossier says what follows from that.
"""

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from pbc.data.plotting import COLOURS, add_credit, label_status

ANNUAL_FILE = "eb_stunde_03987_2015_2024_6h.txt"
DIURNAL_FILE = "eb_stunde_03987_jja_2020_2024_1h.txt"
FIELDS = (
    "STATIONS_ID",
    "MESS_DATUM",
    "QN_2",
    "V_TE002",
    "V_TE005",
    "V_TE010",
    "V_TE020",
    "V_TE050",
    "V_TE100",
    "eor",
)
STATION = 3987
MISSING = -999.0
# The depths of the five columns that are measured (V_TE002 is -999 throughout).
COLUMNS = ("V_TE005", "V_TE010", "V_TE020", "V_TE050", "V_TE100")
DEPTHS = np.array([0.05, 0.10, 0.20, 0.50, 1.00])  # m
UNITS = {"MESS_DATUM": "YYYYMMDDHH", "QN_2": "none", "V_TE*": "degC"}
YEAR = 365.2425 * 86400.0  # s, the mean Gregorian year
DAY = 86400.0  # s
OMEGA_YEAR = 2 * np.pi / YEAR  # rad/s
OMEGA_DAY = 2 * np.pi / DAY  # rad/s
ANNUAL_YEARS = tuple(range(2015, 2025))
SUMMERS = tuple(range(2020, 2025))
# The daily wave at 100 cm is about 0.01 K, below the 0.1 K of the readings.
DIURNAL_DEPTHS = 4  # the first four depths, 5 to 50 cm
WEEK = ("2024-07-01", "2024-07-08")  # the hourly week shown in the figure


@dataclass(frozen=True)
class Readings:
    time: np.ndarray  # datetime64[h], MESS_DATUM
    quality: np.ndarray  # QN_2, the quality level of the row
    temperature: np.ndarray  # (rows, 5) degC at DEPTHS, nan where -999
    header: str  # the first line of the file


def read_readings(path: Path) -> Readings:
    """Read a file of lines of DWD's product file (``;``-separated, CRLF)."""
    raw = Path(path).read_bytes().decode("ascii")
    lines = raw.split("\r\n")
    if lines[-1] != "":
        raise ValueError(f"{path}: the last line does not end with CRLF")
    header, rows = lines[0], [line.split(";") for line in lines[1:-1]]
    if tuple(header.split(";")) != FIELDS:
        raise ValueError(f"{path}: columns {header}, expected {FIELDS}")
    if any(len(r) != len(FIELDS) or r[-1] != "eor" for r in rows):
        raise ValueError(f"{path}: a row without {len(FIELDS)} fields ending in eor")
    if any(int(r[0]) != STATION for r in rows):
        raise ValueError(f"{path}: a row of another station than {STATION}")
    stamps = [r[1].strip() for r in rows]
    time = np.array(
        [f"{s[:4]}-{s[4:6]}-{s[6:8]}T{s[8:10]}" for s in stamps], dtype="datetime64[h]"
    )
    values = np.array([[float(x) for x in r[3:9]] for r in rows])
    if not np.all(values[:, 0] == MISSING):
        raise ValueError(f"{path}: V_TE002 (2 cm) has values, expected none")
    temperature = values[:, 1:]
    temperature[temperature == MISSING] = np.nan
    quality = np.array([int(r[2]) for r in rows])
    return Readings(time, quality, temperature, header)


def load(data_dir: Path) -> tuple[Readings, Readings]:
    """The 6-hourly rows of 2015-2024 and the hourly rows of June-August 2020-2024."""
    data_dir = Path(data_dir)
    return read_readings(data_dir / ANNUAL_FILE), read_readings(data_dir / DIURNAL_FILE)


def seconds(time: np.ndarray, start: np.datetime64) -> np.ndarray:
    return (time - start).astype("timedelta64[s]").astype(float)


# The model.


def damped_wave(z, t, mean, amplitude, phase, omega, kappa):
    """T(z, t) = mean + amplitude exp(-z/d) cos(omega t - z/d - phase),
    d = sqrt(2 kappa / omega): the periodic solution of the heat equation in a
    homogeneous half-space whose surface (z = 0) follows
    mean + amplitude cos(omega t - phase)."""
    d = np.sqrt(2.0 * kappa / omega)
    z = np.asarray(z, dtype=float)
    return mean + amplitude * np.exp(-z / d) * np.cos(omega * t - z / d - phase)


def diffusivity(slope: float, omega: float) -> float:
    """kappa = omega d^2 / 2 from the slope 1/d (1/m) of -ln A or of the lag."""
    return omega / (2.0 * slope**2)


# The harmonics.


def harmonic(t: np.ndarray, y: np.ndarray, omega: float, *, trend: bool = False):
    """Least-squares fit y = m [+ s t] + a cos(omega t) + b sin(omega t);
    returns the complex amplitude a - i b, so that the cosine part is
    |c| cos(omega t + arg c): the amplitude is |c|, the phase lag -arg c."""
    ok = np.isfinite(y)
    t, y = t[ok], y[ok]
    columns = [np.ones_like(t), np.cos(omega * t), np.sin(omega * t)]
    if trend:
        columns.append(t - t.mean())
    coefficients, *_ = np.linalg.lstsq(np.column_stack(columns), y, rcond=None)
    return coefficients[1] - 1j * coefficients[2]


@dataclass(frozen=True)
class Wave:
    """The wave at each depth in each period (year or summer)."""

    omega: float
    depths: np.ndarray  # m
    periods: tuple[int, ...]
    amplitude: np.ndarray  # (periods, depths) K
    lag: np.ndarray  # (periods, depths) rad, relative to the shallowest depth
    counts: np.ndarray  # rows (annual) or complete days (diurnal) per period


def _lags(c: np.ndarray) -> np.ndarray:
    """Phase lag -arg c, unwrapped along depth, relative to the first depth."""
    lag = np.unwrap(-np.angle(c), axis=-1)
    return lag - lag[..., :1]


def annual_wave(readings: Readings, years=ANNUAL_YEARS) -> Wave:
    """The annual harmonic at the five depths, fitted to each calendar year's
    6-hourly readings (four a day, equally spaced, so the daily cycle averages
    out of the fit)."""
    c, counts = [], []
    for year in years:
        start = np.datetime64(f"{year}-01-01T00", "h")
        inside = (readings.time >= start) & (
            readings.time < np.datetime64(f"{year + 1}-01-01T00", "h")
        )
        t = seconds(readings.time[inside], start)
        c.append(
            [
                harmonic(t, readings.temperature[inside, k], OMEGA_YEAR)
                for k in range(DEPTHS.size)
            ]
        )
        counts.append(int(inside.sum()))
    c = np.array(c)
    return Wave(OMEGA_YEAR, DEPTHS, tuple(years), np.abs(c), _lags(c), np.array(counts))


def daily_means(readings: Readings) -> tuple[np.ndarray, np.ndarray]:
    """The mean of each day that has all four 6-hourly readings at every depth:
    (days as datetime64[D], (days, 5) degC)."""
    day = readings.time.astype("datetime64[D]")
    days, index, counts = np.unique(day, return_inverse=True, return_counts=True)
    sums = np.zeros((days.size, DEPTHS.size))
    np.add.at(sums, index, readings.temperature)
    means = sums / counts[:, None]
    keep = (counts == 4) & np.all(np.isfinite(means), axis=1)
    return days[keep], means[keep]


def daily_amplitudes(readings: Readings, year: int) -> np.ndarray:
    """The complex daily harmonic of each complete day (24 readings, none
    missing at the depths used) of June to August of ``year``, fitted with a
    mean and a linear trend over the day; shape (days, DIURNAL_DEPTHS)."""
    out = []
    day = np.datetime64(f"{year}-06-01", "D")
    while day < np.datetime64(f"{year}-09-01", "D"):
        start = day.astype("datetime64[h]")
        inside = (readings.time >= start) & (
            readings.time < start + np.timedelta64(24, "h")
        )
        values = readings.temperature[inside, :DIURNAL_DEPTHS]
        if inside.sum() == 24 and np.all(np.isfinite(values)):
            t = seconds(readings.time[inside], start)
            out.append(
                [harmonic(t, values[:, k], OMEGA_DAY, trend=True) for k in range(4)]
            )
        day += np.timedelta64(1, "D")
    return np.array(out)


def diurnal_wave(readings: Readings, summers=SUMMERS) -> Wave:
    """The daily harmonic at 5 to 50 cm, per summer: the mean of the complex
    amplitudes of its complete days."""
    c, counts = [], []
    for year in summers:
        days = daily_amplitudes(readings, year)
        c.append(days.mean(axis=0))
        counts.append(len(days))
    c = np.array(c)
    return Wave(
        OMEGA_DAY,
        DEPTHS[:DIURNAL_DEPTHS],
        tuple(summers),
        np.abs(c),
        _lags(c),
        np.array(counts),
    )


# The diffusivity.


@dataclass(frozen=True)
class DepthFit:
    """Straight lines through -ln A and the lag against depth."""

    slope_amplitude: float  # 1/m, of -ln A
    intercept_amplitude: float  # ln of the amplitude at z = 0
    slope_lag: float  # rad/m
    intercept_lag: float  # rad

    def kappa(self, omega: float) -> tuple[float, float]:
        """(from the amplitude, from the phase) in m^2/s."""
        return diffusivity(self.slope_amplitude, omega), diffusivity(
            self.slope_lag, omega
        )


def fit_depths(depths, amplitude, lag) -> DepthFit:
    sa, ia = np.polyfit(depths, -np.log(amplitude), 1)
    sl, il = np.polyfit(depths, lag, 1)
    return DepthFit(float(sa), float(-ia), float(sl), float(il))


@dataclass(frozen=True)
class Estimate:
    wave: Wave
    fit: DepthFit  # through the mean over the periods
    kappa: tuple[float, float]  # of ``fit``: (amplitude, phase), m^2/s
    per_period: np.ndarray  # (periods, 2): the same from each period alone
    standard_error: tuple[float, float]  # of the mean of ``per_period``

    @property
    def damping_depth(self) -> tuple[float, float]:
        return 1.0 / self.fit.slope_amplitude, 1.0 / self.fit.slope_lag


def estimate(wave: Wave) -> Estimate:
    """kappa from the mean wave over the periods, with the standard error of
    the mean of the estimates of the single periods."""
    fit = fit_depths(wave.depths, wave.amplitude.mean(0), wave.lag.mean(0))
    per = np.array(
        [
            fit_depths(wave.depths, a, lag).kappa(wave.omega)
            for a, lag in zip(wave.amplitude, wave.lag, strict=True)
        ]
    )
    sem = per.std(axis=0, ddof=1) / np.sqrt(len(per))
    return Estimate(
        wave, fit, fit.kappa(wave.omega), per, (float(sem[0]), float(sem[1]))
    )


def pairwise(wave: Wave) -> list[tuple[float, float, float, float]]:
    """kappa between adjacent depths, from the mean wave: a test of a
    homogeneous soil; rows (upper depth, lower depth, from amplitude, from
    phase)."""
    a, lag, z = wave.amplitude.mean(0), wave.lag.mean(0), wave.depths
    out = []
    for k in range(z.size - 1):
        dz = z[k + 1] - z[k]
        sa = np.log(a[k] / a[k + 1]) / dz
        sl = (lag[k + 1] - lag[k]) / dz
        out.append(
            (
                float(z[k]),
                float(z[k + 1]),
                diffusivity(sa, wave.omega),
                diffusivity(sl, wave.omega),
            )
        )
    return out


def depth_residuals(result: Estimate) -> tuple[np.ndarray, np.ndarray]:
    """The mean ln A and lag at each depth minus the straight lines."""
    wave, fit = result.wave, result.fit
    z = wave.depths
    ln_a = np.log(wave.amplitude.mean(0))
    lag = wave.lag.mean(0)
    return (
        ln_a - (fit.intercept_amplitude - fit.slope_amplitude * z),
        lag - (fit.intercept_lag + fit.slope_lag * z),
    )


def analyse(data_dir: Path) -> tuple[Estimate, Estimate]:
    annual, hourly = load(data_dir)
    return estimate(annual_wave(annual)), estimate(diurnal_wave(hourly))


# The figure.


def _depth_panels(ax_a, ax_l, ax_ra, ax_rl, result: Estimate, colour, marker, name):
    wave, fit = result.wave, result.fit
    z = wave.depths
    n = len(wave.periods)
    a_mean, a_sem = wave.amplitude.mean(0), wave.amplitude.std(0, ddof=1) / np.sqrt(n)
    l_mean, l_sem = wave.lag.mean(0), wave.lag.std(0, ddof=1) / np.sqrt(n)
    dense = np.linspace(0.0, z[-1] + 0.05, 100)
    k_a, k_l = result.kappa
    se_a, se_l = result.standard_error
    span = f"{wave.periods[0]}-{wave.periods[-1]}"
    ax_a.errorbar(
        z,
        a_mean,
        yerr=a_sem,
        ls="none",
        marker=marker,
        ms=5,
        color=colour,
        label=f"{name} wave, measured ({span}, mean of {n})",
    )
    ax_a.plot(
        dense,
        np.exp(fit.intercept_amplitude - fit.slope_amplitude * dense),
        color=colour,
        ls="--",
        lw=1.2,
        label=f"model, κ = {k_a * 1e6:.2f} ± {se_a * 1e6:.2f} $\\times$ 10⁻⁶ m²/s",
    )
    ax_l.errorbar(
        z,
        l_mean,
        yerr=l_sem,
        ls="none",
        marker=marker,
        ms=5,
        color=colour,
        label=f"{name} wave, measured ({span}, mean of {n})",
    )
    ax_l.plot(
        dense,
        fit.intercept_lag + fit.slope_lag * dense,
        color=colour,
        ls="--",
        lw=1.2,
        label=f"model, κ = {k_l * 1e6:.2f} ± {se_l * 1e6:.2f} $\\times$ 10⁻⁶ m²/s",
    )
    ra, rl = depth_residuals(result)
    ax_ra.errorbar(
        z,
        ra,
        yerr=a_sem / a_mean,
        ls="-",
        lw=0.6,
        marker=marker,
        ms=4,
        color=colour,
        label=f"{name} wave",
    )
    ax_rl.errorbar(
        z,
        rl,
        yerr=l_sem,
        ls="-",
        lw=0.6,
        marker=marker,
        ms=4,
        color=colour,
        label=f"{name} wave",
    )


def make_figure(data_dir: Path) -> plt.Figure:
    annual_readings, hourly = load(data_dir)
    annual = estimate(annual_wave(annual_readings))
    diurnal = estimate(diurnal_wave(hourly))

    fig = plt.figure(figsize=(10, 10.5), constrained_layout=True)
    grid = fig.add_gridspec(3, 2, height_ratios=(1.0, 1.1, 0.6))
    ax_year = fig.add_subplot(grid[0, 0])
    ax_week = fig.add_subplot(grid[0, 1])
    ax_a = fig.add_subplot(grid[1, 0])
    ax_l = fig.add_subplot(grid[1, 1])
    ax_ra = fig.add_subplot(grid[2, 0], sharex=ax_a)
    ax_rl = fig.add_subplot(grid[2, 1], sharex=ax_l)
    styles = ("-", "-", "-", "--", ":")

    day, means = daily_means(annual_readings)
    years = day.astype("datetime64[s]").astype(float) / YEAR + 1970
    for k, z in enumerate(DEPTHS):
        ax_year.plot(
            years,
            means[:, k],
            lw=0.7,
            ls=styles[k],
            color=COLOURS[k],
            label=f"{z * 100:.0f} cm",
        )
    ax_year.set_xlabel("year [calendar year]")
    ax_year.set_ylabel("daily mean soil temperature [degC]")
    ax_year.set_title(
        "Processed: mean of the 00, 06, 12, 18 h readings of each day", fontsize=10
    )
    ax_year.legend(fontsize=7, ncols=5, loc="upper center")
    ax_year.set_ylim(-5, 34)

    start, end = (np.datetime64(s, "h") for s in WEEK)
    inside = (hourly.time >= start) & (hourly.time < end)
    days = seconds(hourly.time[inside], start) / DAY
    for k, z in enumerate(DEPTHS):
        ax_week.plot(
            days,
            hourly.temperature[inside, k],
            lw=1.0,
            ls=styles[k],
            color=COLOURS[k],
            label=f"{z * 100:.0f} cm",
        )
    ax_week.set_xlabel(f"days from {WEEK[0]} 00 h (MESS_DATUM) [d]")
    ax_week.set_ylabel("soil temperature [degC]")
    ax_week.set_title("Processed: hourly readings, one summer week", fontsize=10)
    ax_week.legend(fontsize=7, ncols=5, loc="upper center")
    ax_week.set_ylim(10, 42)

    _depth_panels(ax_a, ax_l, ax_ra, ax_rl, annual, COLOURS[0], "o", "annual")
    _depth_panels(ax_a, ax_l, ax_ra, ax_rl, diurnal, COLOURS[1], "s", "daily")
    ax_a.set_yscale("log")
    ax_a.set_ylabel("amplitude of the harmonic [K]")
    ax_a.set_title("Amplitude: exp(-z/d), d = sqrt(2κ/ω); log scale", fontsize=10)
    ax_a.set_ylim(0.2, 30)
    ax_a.legend(fontsize=7, loc="center right")
    ax_a.tick_params(labelbottom=False)
    ax_l.set_ylabel("phase lag behind 5 cm [rad]")
    ax_l.set_title("Phase lag: z/d, the same d for a uniform soil", fontsize=10)
    ax_l.set_ylim(-0.4, 3.0)
    ax_l.legend(fontsize=7, loc="center right")
    ax_l.tick_params(labelbottom=False)
    for ax in (ax_ra, ax_rl):
        ax.axhline(0, color="0.3", lw=0.8)
        ax.set_xlabel("depth z [m]")
        ax.set_ylim(-0.065, 0.065)
        ax.legend(fontsize=7, loc="upper right", ncols=2)
    ax_ra.set_ylabel("residual of ln A [1]")
    ax_ra.set_title(
        "Residuals of the straight line in ln A (one standard error)", fontsize=10
    )
    ax_rl.set_ylabel("residual of the lag [rad]")
    ax_rl.set_title("Residuals of the straight line in the lag", fontsize=10)

    add_credit(
        fig,
        "Data: Deutscher Wetterdienst (DWD), Climate Data Center, hourly soil "
        "temperature of station 03987 Potsdam, archive "
        "stundenwerte_EB_03987_19510101_20251231_hist.zip, CC BY 4.0. Rows "
        "selected unchanged (00, 06, 12, 18 h of 2015-2024; every hour of June to "
        "August 2020-2024). Harmonic fits, the heat-equation model, and residuals: "
        "this figure's code (pbc.data.reference.dwd_soil), not part of the record.",
    )
    label_status(fig, "processed")
    return fig
