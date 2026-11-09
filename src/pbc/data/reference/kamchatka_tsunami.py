"""The inputs of the 2025 Kamchatka tsunami capstone (FL10): DART bottom-pressure
records, the USGS finite-fault model, and the ETOPO 2022 bathymetry.

Status of the figure: *processed*. A DART station measures the pressure at
the sea floor; NDBC converts it to a height of the water column (metres,
670 mm per psia), and NCEI fits and removes the tide. The sea-surface
residual is therefore processed measurement. Two further steps are this
project's and are disclosed:

1. **The double conversion.** NCEI's event files give heights that are
   NDBC's heights multiplied a second time by 0.670: their mean is 0.670
   times the station depth, and NCEI height / NDBC height is 0.670 at every
   matched timestamp. The residuals here are NCEI's residual divided by
   ``NDBC_FACTOR`` = 0.670. The factor is checked on the files by
   ``conversion_ratios``, not assumed.
2. **The arrival estimates.** The long-wave speed sqrt(g h) integrated along
   the great circle over the ETOPO depths, from the epicentre and from the
   nearest point of the USGS model's uplift, is a modelled reference: a
   check that each record's window contains the arrival, drawn apart from
   the measurement. It is not the propagation model of the capstone and not
   a comparison of a model with the records.

The USGS finite fault (product ``us6000qw60_1``, version 5) was inverted
from teleseismic body and surface waves, GNSS, and InSAR; its data table
lists no DART record, so the DART records are independent of it. Its
surface deformation is a 40 x 40 grid of the vertical (and horizontal)
displacement of the surface of an elastic half-space, a modelled reference.

The bathymetry is ETOPO 2022 at 60 arc-seconds, every fourth cell (4
arc-minutes, about 7.4 km by 4.6 km at 52N), decimated, not averaged, and
rounded to the metre (``tools/datasets/etopo_ascii_to_npy.py``).
"""

import gzip
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

from pbc.data.plotting import COLOURS, add_credit, label_status, signed_image

NCEI_FILES = {
    "21416": "dart21416_20250727to20250803_meter.txt",
    "21415": "dart21415_20250727to20250803_meter.txt",
}
NDBC_FILES = {"21416": "21416t2025.txt.gz", "21415": "21415t2025.txt.gz"}
STATIONS_FILE = "DART_deployment_coord.txt"
FSP_FILE = "complete_inversion.fsp"
DISP_FILE = "surface_deformation.disp"
ETOPO_FILE = "etopo2022_60s_bed_35N60N_140E180E_stride4.npy"

# USGS ComCat, event us6000qw60 (https://earthquake.usgs.gov/earthquakes/eventpage/us6000qw60),
# read 2026-11-09: origin time 1753831492483 ms after the Unix epoch, epicentre.
ORIGIN = np.datetime64("2025-07-29T23:24:52.483", "ms")
EPICENTRE = (52.4948, 160.2395)  # degrees N, degrees E
# NDBC's pressure-to-height factor, 670 mm of sea water per psia, applied a
# second time to the heights of NCEI's event files.
NDBC_FACTOR = 0.670
NDBC_MISSING = 9999.0
G = 9.81  # m/s^2
EARTH_RADIUS = 6371.0e3  # m, mean radius
# ETOPO crop: every fourth 60" cell from 35N and 140E, 375 x 600.
ETOPO_LAT0, ETOPO_LON0, ETOPO_STRIDE = 35.0, 140.0, 4
ETOPO_SHAPE = (375, 600)
# A path through a cell shallower than this is blocked (land or a coast).
MIN_DEPTH = 1.0  # m
# Windows in minutes after the origin.
SEISMIC = (1.0, 26.0)  # shaking of the pressure sensor at 21416
SEARCH = (26.0, 240.0)  # where the tsunami peak is searched
BEFORE = (-24 * 60.0, 0.0)  # the day before the origin, for the noise floor
UPLIFT_LEVELS = (0.5, 1.0, 2.0)  # m, sources for the nearest-uplift arrival

ATTRIBUTION = (
    "DART: NOAA National Data Buoy Center (stations 21416, 21415), event files of "
    "NOAA NCEI (doi 10.7289/V5F18WNS), heights divided by 0.670 (double conversion "
    "in the event files). Finite fault: USGS NEIC, us6000qw60, product us6000qw60_1 "
    "v5. Bathymetry: NOAA NCEI ETOPO 2022 60 arc-second (doi 10.25921/fd45-gt74, "
    "CC0), every fourth cell. US-government works, public domain."
)


@dataclass(frozen=True)
class NceiRecord:
    """An NCEI event file: height, NCEI's tide fit, and their difference."""

    time: np.ndarray  # datetime64[ms], UTC
    height: np.ndarray  # m, as in the file (0.670 times NDBC's height)
    tide: np.ndarray  # m, NCEI's tide fit, same scale
    residual: np.ndarray  # m, height - tide, same scale
    flag: np.ndarray  # the eleventh column, 0.000 throughout

    def minutes(self) -> np.ndarray:
        return minutes_after_origin(self.time)

    def corrected(self) -> np.ndarray:
        """The residual on NDBC's scale, in metres of sea level."""
        return self.residual / NDBC_FACTOR


@dataclass(frozen=True)
class NdbcRecord:
    """An NDBC annual DART file: height of the water column, by record type."""

    time: np.ndarray  # datetime64[ms], UTC
    kind: np.ndarray  # 1: 15-minute, 2: 1-minute, 3: 15-second
    height: np.ndarray  # m, NaN where the file has 9999.000


@dataclass(frozen=True)
class Station:
    lat: float
    lon: float
    depth: float  # m
    deployment: str


@dataclass(frozen=True)
class Fault:
    header: dict
    subfaults: np.ndarray  # LAT LON X Y Z SLIP RAKE TRUP RISE SF_MOMENT
    segment: np.ndarray  # 1, 2, 3 for each subfault

    @property
    def moment(self) -> float:
        """The summed subfault moments, N m."""
        return float(self.subfaults[:, 9].sum())

    @property
    def mw(self) -> float:
        return moment_magnitude(self.moment)


@dataclass(frozen=True)
class Deformation:
    lon: np.ndarray  # degrees E, 40 x 40
    lat: np.ndarray  # degrees N
    east: np.ndarray  # m
    north: np.ndarray  # m
    up: np.ndarray  # m


@dataclass(frozen=True)
class Bathymetry:
    lat: np.ndarray  # cell centres, degrees N, 375
    lon: np.ndarray  # degrees E, 600
    z: np.ndarray  # m, positive up (EGM2008), 375 x 600, row 0 southernmost

    def depth_at(self, lat, lon) -> np.ndarray:
        """Depth below sea level (m, positive in the sea) of the nearest cell."""
        i = np.rint((60.0 * (np.asarray(lat) - ETOPO_LAT0) - 0.5) / ETOPO_STRIDE)
        j = np.rint((60.0 * (np.asarray(lon) - ETOPO_LON0) - 0.5) / ETOPO_STRIDE)
        inside = (i >= 0) & (i < self.z.shape[0]) & (j >= 0) & (j < self.z.shape[1])
        i = np.clip(i, 0, self.z.shape[0] - 1).astype(int)
        j = np.clip(j, 0, self.z.shape[1] - 1).astype(int)
        return np.where(inside, -self.z[i, j].astype(float), np.nan)


def minutes_after_origin(time: np.ndarray) -> np.ndarray:
    return (time - ORIGIN) / np.timedelta64(60_000, "ms")


def _stamp(y, mo, d, h, mi, s) -> np.datetime64:
    return np.datetime64(
        f"{int(y):04d}-{int(mo):02d}-{int(d):02d}T{int(h):02d}:{int(mi):02d}:{int(s):02d}",
        "ms",
    )


def read_ncei(path: Path) -> NceiRecord:
    """Read an NCEI event file: 11 columns, day of year (decimal), year, month,
    day, hour, minute, second, height, tide, residual, flag."""
    rows = np.loadtxt(path, ndmin=2)
    if rows.shape[1] != 11:
        raise ValueError(f"{path}: {rows.shape[1]} columns, expected 11")
    time = np.array([_stamp(*r[1:7]) for r in rows])
    start = np.datetime64(f"{int(rows[0, 1]):04d}-01-01T00:00:00", "ms")
    doy = 1 + (time - start) / np.timedelta64(86_400_000, "ms")
    if np.abs(doy - rows[:, 0]).max() > 1e-5:
        raise ValueError(f"{path}: the day of year disagrees with the date")
    return NceiRecord(time, rows[:, 7], rows[:, 8], rows[:, 9], rows[:, 10])


def read_ndbc(path: Path) -> NdbcRecord:
    """Read an NDBC annual DART file (gzip): two header lines, then
    ``YY MM DD hh mm ss T HEIGHT``; 9999.000 is a missing height."""
    with gzip.open(path, "rt", encoding="ascii") as handle:
        lines = handle.read().splitlines()
    if lines[0].split() != ["#YY", "MM", "DD", "hh", "mm", "ss", "T", "HEIGHT"]:
        raise ValueError(f"{path}: unexpected header {lines[0]!r}")
    rows = [line.split() for line in lines[2:] if line.strip()]
    time = np.array([_stamp(*r[:6]) for r in rows])
    kind = np.array([int(r[6]) for r in rows])
    height = np.array([float(r[7]) for r in rows])
    height[height == NDBC_MISSING] = np.nan
    return NdbcRecord(time, kind, height)


def read_stations(path: Path) -> dict[str, Station]:
    """NCEI's list of DART deployments: ``<id>_<deployment> - <place>`` then
    latitude, longitude, and in parentheses the depth in metres."""
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        name, _, rest = line.partition(" - ")
        numbers = rest.split("\t")[-1].split()
        lat, lon = float(numbers[0]), float(numbers[1])
        depth = float(line.rsplit(",", 1)[1].strip().rstrip(")").split()[0])
        station, deployment = name.strip().split("_", 1)
        out[station] = Station(lat, lon, depth, deployment)
    return out


def _header_value(line: str, key: str) -> float:
    return float(line.split(f"{key} =", 1)[1].split()[0])


def read_fsp(path: Path) -> Fault:
    """The SRCMOD-style finite-source file of the USGS: a commented header,
    then one row per subfault after each ``SEGMENT #`` block."""
    header: dict = {}
    rows, segment, current = [], [], 0
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.startswith("% Loc"):
            header["lat"] = _header_value(line, "LAT")
            header["lon"] = _header_value(line, "LON")
            header["depth_km"] = _header_value(line, "DEP")
        elif line.startswith("% Size"):
            header["mw"] = _header_value(line, "Mw")
            header["mo"] = _header_value(line, "Mo")
        elif line.startswith("% Mech"):
            for key in ("STRK", "DIP", "RAKE"):
                header[key.lower()] = _header_value(line, key)
        elif line.startswith("% EventTAG:"):
            header["time"] = np.datetime64(line.split(":", 1)[1].strip(), "ms")
        elif line.startswith("% SEGMENT #"):
            current = int(line.split("#")[1].split(":")[0])
        elif line.strip() and not line.startswith("%"):
            rows.append([float(v) for v in line.split()])
            segment.append(current)
    subfaults = np.array(rows)
    if subfaults.shape[1] != 10:
        raise ValueError(f"{path}: {subfaults.shape[1]} columns, expected 10")
    return Fault(header, subfaults, np.array(segment))


def read_disp(path: Path) -> Deformation:
    """The USGS surface deformation: one header line, then longitude,
    latitude, elevation (0), east, north, and vertical displacement (m) on a
    40 x 40 grid, longitude varying fastest."""
    rows = np.loadtxt(path, skiprows=1)
    n = round(np.sqrt(len(rows)))
    if n * n != len(rows) or rows.shape[1] != 6:
        raise ValueError(f"{path}: not a square grid of 6 columns")
    grid = rows.reshape(n, n, 6)
    return Deformation(*(grid[:, :, k] for k in (0, 1, 3, 4, 5)))


def read_etopo(path: Path) -> Bathymetry:
    z = np.load(path, allow_pickle=False)
    if z.shape != ETOPO_SHAPE or z.dtype != np.int16:
        raise ValueError(f"{path}: {z.shape} {z.dtype}, expected {ETOPO_SHAPE} int16")
    lat = ETOPO_LAT0 + (ETOPO_STRIDE * np.arange(z.shape[0]) + 0.5) / 60.0
    lon = ETOPO_LON0 + (ETOPO_STRIDE * np.arange(z.shape[1]) + 0.5) / 60.0
    return Bathymetry(lat, lon, z)


@dataclass(frozen=True)
class Inputs:
    ncei: dict[str, NceiRecord]
    ndbc: dict[str, NdbcRecord]
    stations: dict[str, Station]
    fault: Fault
    deformation: Deformation
    bathymetry: Bathymetry


def load(data_dir: Path) -> Inputs:
    data_dir = Path(data_dir)
    return Inputs(
        {k: read_ncei(data_dir / f) for k, f in NCEI_FILES.items()},
        {k: read_ndbc(data_dir / f) for k, f in NDBC_FILES.items()},
        read_stations(data_dir / STATIONS_FILE),
        read_fsp(data_dir / FSP_FILE),
        read_disp(data_dir / DISP_FILE),
        read_etopo(data_dir / ETOPO_FILE),
    )


def moment_magnitude(moment: float) -> float:
    """Mw from the seismic moment in N m (Hanks and Kanamori)."""
    return 2.0 / 3.0 * (np.log10(moment) - 9.1)


def conversion_ratios(
    ncei: NceiRecord, ndbc: NdbcRecord
) -> tuple[np.ndarray, np.ndarray]:
    """NCEI height / NDBC height at every NCEI timestamp that NDBC also has,
    and the mask of those NCEI rows.

    Where NDBC has two records at one time (two record types), the ratio
    nearest 0.670 is kept.
    """
    by_time: dict = {}
    for t, h in zip(ndbc.time, ndbc.height, strict=True):
        if np.isfinite(h):
            by_time.setdefault(t, []).append(h)
    ratios, matched = [], np.zeros(len(ncei.time), dtype=bool)
    for k, (t, h) in enumerate(zip(ncei.time, ncei.height, strict=True)):
        if t in by_time:
            matched[k] = True
            ratios.append(
                min((h / x for x in by_time[t]), key=lambda r: abs(r - NDBC_FACTOR))
            )
    return matched, np.array(ratios)


def duplicate_times(record: NceiRecord) -> int:
    return len(record.time) - len(np.unique(record.time))


def peak(record: NceiRecord, window=SEARCH) -> tuple[float, float]:
    """The largest corrected residual (m) and its time (minutes) in ``window``."""
    m = record.minutes()
    inside = (m > window[0]) & (m < window[1])
    k = np.argmax(np.where(inside, record.corrected(), -np.inf))
    return float(record.corrected()[k]), float(m[k])


def trough(record: NceiRecord, window=SEARCH) -> tuple[float, float]:
    m = record.minutes()
    inside = (m > window[0]) & (m < window[1])
    k = np.argmin(np.where(inside, record.corrected(), np.inf))
    return float(record.corrected()[k]), float(m[k])


def half_peak_time(record: NceiRecord, window=SEARCH) -> float:
    """The time (minutes) the corrected residual last rises through half its
    peak before the peak, interpolated linearly between samples.

    The last crossing, not the first: a single 15-second sample can exceed
    half the peak before the wave (at 21415, 0.235 m at +50.1 min, beside a
    duplicate of 0.047 m at the same time)."""
    height, at = peak(record, window)
    m = record.minutes()
    order = np.argsort(m, kind="stable")
    m, y = m[order], record.corrected()[order]
    up = (y[1:] >= height / 2) & (y[:-1] < height / 2) & (m[1:] > window[0])
    up &= m[1:] <= at
    k = np.nonzero(up)[0][-1] + 1
    return float(
        m[k - 1] + (height / 2 - y[k - 1]) * (m[k] - m[k - 1]) / (y[k] - y[k - 1])
    )


def noise_floor(record: NceiRecord, window=BEFORE) -> float:
    """The rms of the corrected residual in the day before the origin, m."""
    m = record.minutes()
    y = record.corrected()[(m >= window[0]) & (m < window[1])]
    return float(np.sqrt(np.mean(y**2)))


def largest_excursion(record: NceiRecord, window=SEISMIC) -> float:
    m = record.minutes()
    return float(np.abs(record.corrected()[(m > window[0]) & (m < window[1])]).max())


def great_circle(lat0, lon0, lat1, lon1, step: float = 1000.0):
    """Points every ``step`` metres (or less) along the great circle, and the
    length of the arc in metres."""
    p0 = _unit(lat0, lon0)
    p1 = _unit(lat1, lon1)
    angle = float(np.arccos(np.clip(np.dot(p0, p1), -1.0, 1.0)))
    length = EARTH_RADIUS * angle
    n = max(int(np.ceil(length / step)), 1)
    f = np.linspace(0.0, 1.0, n + 1)
    if angle == 0.0:
        points = np.repeat(p0[None, :], n + 1, axis=0)
    else:
        points = (
            np.sin((1 - f) * angle)[:, None] * p0 + np.sin(f * angle)[:, None] * p1
        ) / np.sin(angle)
    lat = np.degrees(np.arcsin(np.clip(points[:, 2], -1, 1)))
    lon = np.degrees(np.arctan2(points[:, 1], points[:, 0])) % 360.0
    return lat, lon, length


def _unit(lat, lon) -> np.ndarray:
    la, lo = np.radians(lat), np.radians(lon)
    return np.array([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)])


def travel_time(bathymetry: Bathymetry, start, end) -> tuple[float, float]:
    """Minutes for a long wave, speed sqrt(g h), along the great circle from
    ``start`` to ``end`` (lat, lon), and the length in km; infinite if the
    path crosses a cell shallower than ``MIN_DEPTH`` or leaves the crop."""
    lat, lon, length = great_circle(*start, *end)
    h = bathymetry.depth_at(lat, lon)
    if not np.all(np.isfinite(h)) or np.any(h < MIN_DEPTH):
        return np.inf, length / 1e3
    slowness = 1.0 / np.sqrt(G * h)
    ds = length / (len(h) - 1)
    seconds = float(np.sum(0.5 * (slowness[1:] + slowness[:-1])) * ds)
    return seconds / 60.0, length / 1e3


def nearest_uplift_arrival(inputs: Inputs, station: str, level: float = 1.0):
    """The shortest sqrt(g h) travel time (minutes) to ``station`` from a
    point of the USGS grid whose vertical displacement is at least ``level``
    metres and which lies in the sea; with that point (lat, lon)."""
    target = inputs.stations[station]
    d = inputs.deformation
    best = (np.inf, None)
    for lat, lon in zip(d.lat[d.up >= level], d.lon[d.up >= level], strict=True):
        minutes, _ = travel_time(
            inputs.bathymetry, (lat, lon), (target.lat, target.lon)
        )
        if minutes < best[0]:
            best = (minutes, (float(lat), float(lon)))
    return best


@dataclass(frozen=True)
class StationResult:
    ratio_median: float
    ratio_max_deviation: float
    matched: int
    mean_over_depth: float
    duplicates: int
    peak: tuple[float, float]
    trough: tuple[float, float]
    half_peak: float
    noise: float
    seismic: float
    epicentre_arrival: float
    epicentre_distance: float
    uplift_arrival: dict  # level -> minutes


def analyse_station(inputs: Inputs, station: str) -> StationResult:
    ncei, ndbc = inputs.ncei[station], inputs.ndbc[station]
    site = inputs.stations[station]
    _, ratios = conversion_ratios(ncei, ndbc)
    arrival, distance = travel_time(inputs.bathymetry, EPICENTRE, (site.lat, site.lon))
    return StationResult(
        ratio_median=float(np.median(ratios)),
        ratio_max_deviation=float(np.abs(ratios - NDBC_FACTOR).max()),
        matched=len(ratios),
        mean_over_depth=float(ncei.height.mean() / site.depth),
        duplicates=duplicate_times(ncei),
        peak=peak(ncei),
        trough=trough(ncei),
        half_peak=half_peak_time(ncei),
        noise=noise_floor(ncei),
        seismic=largest_excursion(ncei),
        epicentre_arrival=arrival,
        epicentre_distance=distance,
        uplift_arrival={
            level: nearest_uplift_arrival(inputs, station, level)[0]
            for level in UPLIFT_LEVELS
        },
    )


def analyse(data_dir: Path) -> tuple[Inputs, dict[str, StationResult]]:
    inputs = load(data_dir)
    return inputs, {s: analyse_station(inputs, s) for s in NCEI_FILES}


def _map_panel(ax, inputs: Inputs) -> None:
    b, d = inputs.bathymetry, inputs.deformation
    signed_image(
        ax,
        b.z.astype(float) / 1e3,
        label="elevation, ETOPO 2022",
        unit="km",
        extent=(b.lon[0], b.lon[-1], b.lat[0], b.lat[-1]),
        aspect=1.6,
    )
    ax.contour(d.lon, d.lat, d.up, levels=[1, 3, 5, 7], colors="k", linewidths=0.8)
    ax.contour(
        d.lon,
        d.lat,
        d.up,
        levels=[-4, -2, -1],
        colors="k",
        linewidths=0.8,
        linestyles="--",
    )
    ax.plot(EPICENTRE[1], EPICENTRE[0], "*", ms=12, mfc="w", mec="k")
    for name, colour in zip(NCEI_FILES, COLOURS, strict=False):
        site = inputs.stations[name]
        ax.plot(site.lon, site.lat, "^", ms=8, mfc=colour, mec="k")
        ax.annotate(
            f"DART {name}",
            (site.lon, site.lat),
            (4, 4),
            textcoords="offset points",
            fontsize=8,
        )
    handles = [
        Line2D([], [], color="k", lw=0.8, label="uplift 1, 3, 5, 7 m (USGS model)"),
        Line2D([], [], color="k", lw=0.8, ls="--", label="subsidence 1, 2, 4 m"),
        Line2D([], [], ls="", marker="*", mfc="w", mec="k", ms=10, label="epicentre"),
        Line2D([], [], ls="", marker="^", mfc="0.6", mec="k", label="DART station"),
    ]
    ax.legend(handles=handles, fontsize=7, loc="lower right")
    ax.set_xlim(150, 176)
    ax.set_ylim(44, 58)
    ax.set_xlabel("longitude [degrees E]")
    ax.set_ylabel("latitude [degrees N]")
    ax.set_title("Inputs: bathymetry, USGS vertical deformation, DARTs")


def _record_panel(ax, inputs: Inputs, station: str, result: StationResult, colour):
    record = inputs.ncei[station]
    m = record.minutes()
    order = np.argsort(m, kind="stable")
    shown = (m[order] > -30) & (m[order] < 180)
    ax.plot(
        m[order][shown],
        record.corrected()[order][shown],
        "-o",
        ms=2,
        lw=1,
        color=colour,
        label=f"DART {station}, NCEI residual / 0.670 [processed]",
    )
    if station == "21416":
        ax.axvspan(*SEISMIC, color="0.88", label="seafloor shaking, not sea level")
    ax.axvline(
        result.uplift_arrival[1.0],
        color="k",
        ls="--",
        lw=1,
        label="sqrt(gh) from nearest uplift >= 1 m [simulated]",
    )
    ax.axvline(
        result.epicentre_arrival,
        color="k",
        ls=":",
        lw=1,
        label="sqrt(gh) from the epicentre [simulated]",
    )
    ax.axhline(0, color="0.5", lw=0.5)
    ax.set_xlim(-30, 180)
    ax.set_xlabel("time after the origin [min]")
    ax.set_ylabel("sea level minus tide [m]")
    ax.set_title(
        f"DART {station}: peak {result.peak[0]:.2f} m at +{result.peak[1]:.1f} min"
    )
    bottom, top = ax.get_ylim()
    ax.set_ylim(bottom, max(top, 1.6 * result.peak[0]))  # room for the legend
    ax.legend(fontsize=7, loc="upper right" if station == "21416" else "upper left")


def _ratio_panel(ax, inputs: Inputs) -> None:
    for (name, colour), marker in zip(
        zip(NCEI_FILES, COLOURS, strict=False), ("o", "s"), strict=True
    ):
        ncei, ndbc = inputs.ncei[name], inputs.ndbc[name]
        matched, ratios = conversion_ratios(ncei, ndbc)
        m = minutes_after_origin(ncei.time[matched])
        ax.plot(
            m / 60.0,
            (ratios - NDBC_FACTOR) * 1e6,
            marker,
            ms=2,
            ls="",
            color=colour,
            label=f"DART {name}",
        )
    ax.axhline(0, color="0.5", lw=0.5)
    ax.set_xlabel("time after the origin [h]")
    ax.set_ylabel("NCEI / NDBC height - 0.670 [1e-6]")
    ax.set_title("Double conversion: NCEI heights are 0.670 x NDBC's")
    ax.legend(fontsize=7)


def make_figure(data_dir: Path) -> plt.Figure:
    inputs, results = analyse(data_dir)
    fig = plt.figure(figsize=(12, 9), layout="constrained")
    grid = fig.add_gridspec(2, 2)
    _map_panel(fig.add_subplot(grid[0, 0]), inputs)
    _ratio_panel(fig.add_subplot(grid[0, 1]), inputs)
    for k, (name, colour) in enumerate(zip(NCEI_FILES, COLOURS, strict=False)):
        _record_panel(fig.add_subplot(grid[1, k]), inputs, name, results[name], colour)
    label_status(fig, "processed")
    add_credit(fig, ATTRIBUTION)
    return fig
