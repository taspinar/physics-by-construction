"""The experiment of the lesson "Applied capstone: reconstructing the 2025
Kamchatka tsunami".

A teaching-scale model of the tsunami of 29 July 2025: the two-dimensional
shallow-water equations of ``pbc.fluids.tsunami`` (the HLL flux and the
hydrostatic reconstruction of the lessons "Finite-volume methods and
conservation laws" and "Shallow-water equations", on a latitude-longitude
grid) over the ETOPO 2022 bathymetry, cropped and block-averaged, with the
USGS finite-fault model's vertical surface deformation as the initial lift of
the sea floor and the sea surface (card ``kamchatka-2025-tsunami-inputs``,
committed sample). The experiment verifies the model (still water, linear
waves against exact solutions, the volume budget, positivity, the CFL limit,
the boundaries, grid refinement), and then compares the computed surface at
the DART stations 21416 and 21415 with their records (NCEI's residual divided
by 0.670) by a metric fixed beforehand. Run it as a program to write the
figures and the numbers of the page:

    uv run --locked --no-dev python -m \\
        pbc.fluids.experiments.reconstructing_the_2025_kamchatka_tsunami out

A heavier rerun on the whole domain at 4 arc-minutes, which the page and the
checks do not run (about a minute), is ``fine_check()``.
"""

from dataclasses import dataclass
from functools import cache

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import BoundaryNorm
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from scipy.interpolate import RegularGridInterpolator
from scipy.spatial import cKDTree

from pbc.data import SAMPLES_DIR
from pbc.data.adapters import dart_residual_series
from pbc.data.plotting import (
    COLOURS,
    add_credit,
    label_status,
    plot_series,
    residual,
    sequential_image,
)
from pbc.data.reference import kamchatka_tsunami
from pbc.data.reference.kamchatka_tsunami import Inputs, NceiRecord
from pbc.data.series import Series
from pbc.experiment import Experiment, main
from pbc.fluids import tsunami
from pbc.fluids.shallow_water import GRAVITY
from pbc.fluids.tsunami import Gauge, Grid, Run
from pbc.fluids.tsunami_benchmarks import (
    RADIAL,
    draw_plane_wave_convergence,
    plane_wave_errors,
    radial_exact,
    radial_run,
)

DATASET = "kamchatka-2025-tsunami-inputs"
# region: choices
SOUTH, WEST = 44.0, 153.0  # degrees N, E: the corner of the domain
ROWS, COLUMNS = 192, 344  # cells of the 4' crop: 12.8 by 22.9 degrees
LARGE = (38.0, 146.0, 320, 508)  # the larger domain of the boundary check
NEAR = (46.5, 155.0, 120, 164)  # the domain of the 4' run, around DART 21416
FINE, BASE, COARSE, COARSEST = 1, 2, 4, 8  # blocks of 4' cells: 4' to 32'
LIMITER = "monotonized central"  # chosen on the plane-wave benchmark
COURANT = 0.8  # dt (a_x / dx + a_y / dy) of the CFL condition
DURATION = 7200.0  # s, two hours after the origin
NEAR_DURATION = 2700.0  # s, the 4' run: past the crest at DART 21416
THRESHOLD = 0.01  # m, the surface height that counts as arrival on the map
TAPER = 3  # steps of the USGS grid over which its edge is tapered to zero
STATIONS = ("21416", "21415")
WINDOWS = {"21416": (26.0, 70.0), "21415": (50.0, 118.0)}  # min, compared
SHOWN = {"21416": (20.0, 100.0), "21415": (40.0, 120.0)}  # min, drawn
SAMPLING = 0.5  # min: half the one-minute spacing of the records
# endregion: choices
GRID_NAMES = {FINE: "4'", BASE: "8'", COARSE: "16'", COARSEST: "32'"}
CREDIT = (
    "Data: NOAA NDBC and NCEI, DART 21416 and 21415 (doi 10.7289/V5F18WNS), "
    "residual divided by 0.670; USGS NEIC, us6000qw60_1 v5; NOAA NCEI ETOPO "
    "2022 (CC0), every fourth cell. US-government works, not endorsed by NOAA "
    "or the USGS. Model: this lesson's code."
)
STYLES = ("-", "--", ":", "-.")
MARKERS = ("o", "s", "^", "D")


@cache
def inputs() -> Inputs:
    """The committed sample of the card."""
    return kamchatka_tsunami.load(SAMPLES_DIR / DATASET)


def records() -> dict[str, NceiRecord]:
    return inputs().ncei


# The domain, the source, and the runs.


@dataclass(frozen=True)
class Domain:
    """A grid of the domain with the uplift and the onset time of each cell
    (m, s) and the two stations as gauges."""

    grid: Grid
    uplift: np.ndarray
    onset: np.ndarray
    gauges: tuple[Gauge, ...]
    factor: int


def centres(values: np.ndarray, factor: int) -> np.ndarray:
    """The centres of blocks of ``factor`` neighbouring cells."""
    n = len(values) // factor * factor
    return values[:n].reshape(-1, factor).mean(axis=1)


def taper(x: np.ndarray, axis: np.ndarray) -> np.ndarray:
    """1 inside the USGS grid, falling to 0 at its edge as a half cosine
    over ``TAPER`` of its steps."""
    width = TAPER * abs(axis[1] - axis[0])
    inside = np.minimum(x - axis.min(), axis.max() - x) / width
    return 0.5 - 0.5 * np.cos(np.pi * np.clip(inside, 0.0, 1.0))


def uplift_at(lat: np.ndarray, lon: np.ndarray, tapered: bool = True) -> np.ndarray:
    """The USGS vertical displacement (m) interpolated bilinearly to the
    points, zero outside its grid, tapered at its edge if ``tapered``."""
    d = inputs().deformation
    lat_axis, lon_axis = d.lat[:, 0], d.lon[0, :]
    lift = RegularGridInterpolator(
        (lat_axis, lon_axis), d.up, bounds_error=False, fill_value=0.0
    )(np.stack([lat, lon], axis=-1))
    if tapered:
        lift = lift * taper(lat, lat_axis) * taper(lon, lon_axis)
    return lift


def unit_vectors(lat, lon) -> np.ndarray:
    la, lo = np.radians(lat), np.radians(lon)
    return np.stack(
        [np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], axis=-1
    )


def onset_at(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """The time (s after the origin) at which the sea floor at each point
    rises: the rupture time plus half the rise time of the nearest subfault
    of the USGS model."""
    s = inputs().fault.subfaults
    tree = cKDTree(unit_vectors(s[:, 0], s[:, 1]))
    _, nearest = tree.query(unit_vectors(lat, lon).reshape(-1, 3))
    return (s[nearest, 7] + 0.5 * s[nearest, 8]).reshape(lat.shape)


@cache
def domain(
    factor: int, large: bool = False, rotating: bool = True, near: bool = False
) -> Domain:
    """The domain on blocks of ``factor`` x ``factor`` cells of the 4' crop:
    the mean bed, the mean uplift, the onset at each block's centre. The
    larger domain, or the smaller one around DART 21416 (``near``), instead
    of the base domain."""
    south, west, rows, columns = (
        LARGE if large else NEAR if near else (SOUTH, WEST, ROWS, COLUMNS)
    )
    b = inputs().bathymetry
    stride = kamchatka_tsunami.ETOPO_STRIDE
    i0 = round((south - kamchatka_tsunami.ETOPO_LAT0) * 60 / stride)
    j0 = round((west - kamchatka_tsunami.ETOPO_LON0) * 60 / stride)
    z = b.z[i0 : i0 + rows, j0 : j0 + columns].astype(float)
    lat, lon = b.lat[i0 : i0 + rows], b.lon[j0 : j0 + columns]
    fine_lat, fine_lon = np.meshgrid(lat, lon, indexing="ij")
    lift = tsunami.coarsen(uplift_at(fine_lat, fine_lon), factor)
    lat_c, lon_c = centres(lat, factor), centres(lon, factor)
    grid = tsunami.sphere_grid(tsunami.coarsen(z, factor), lat_c, lon_c, rotating)
    block_lat, block_lon = np.meshgrid(lat_c, lon_c, indexing="ij")
    gauges = tuple(
        Gauge(
            name,
            (inputs().stations[name].lat - lat_c[0]) / (lat_c[1] - lat_c[0]),
            (inputs().stations[name].lon - lon_c[0]) / (lon_c[1] - lon_c[0]),
        )
        for name in (STATIONS[:1] if near else STATIONS)
    )
    return Domain(grid, lift, onset_at(block_lat, block_lon), gauges, factor)


def at_rest(grid: Grid) -> np.ndarray:
    q = np.zeros((*grid.shape, 3))
    q[..., 0] = np.maximum(0.0, -grid.bed)
    return q


@cache
def kamchatka_run(
    factor: int,
    kinematic: bool = True,
    large: bool = False,
    rotating: bool = True,
    near: bool = False,
) -> Run:
    """The tsunami on the domain of ``factor`` for two hours (45 minutes on
    the domain ``near`` DART 21416): the sea floor and the surface rise at
    each cell's onset (``kinematic``) or all at once."""
    d = domain(factor, large, rotating, near)
    duration = NEAR_DURATION if near else DURATION
    options = {"threshold": THRESHOLD, "limiter": LIMITER}
    if kinematic:
        return tsunami.simulate(
            d.grid,
            at_rest(d.grid),
            duration,
            COURANT,
            d.gauges,
            uplift=d.uplift,
            onset=d.onset,
            **options,
        )
    grid, q = tsunami.initial_state(d.grid, d.uplift)
    return tsunami.simulate(grid, q, duration, COURANT, d.gauges, **options)


VARIANTS = {
    "base": {},
    "instantaneous": {"kinematic": False},
    "no rotation": {"rotating": False},
    "larger domain": {"large": True},
}


# The metric, the same for a model and a record.


def crest(minutes: np.ndarray, y: np.ndarray, window) -> tuple[float, float]:
    """The largest value (m) in ``window`` (min) and its time."""
    inside = (minutes > window[0]) & (minutes < window[1])
    k = int(np.argmax(np.where(inside, y, -np.inf)))
    return float(y[k]), float(minutes[k])


def half_crest_time(minutes: np.ndarray, y: np.ndarray, window) -> float:
    """The arrival: the time (min) the series last rises through half its
    crest (in ``window``) before the crest, interpolated linearly between
    samples. Being the last crossing, it is the definition of
    ``kamchatka_tsunami.half_peak_time`` without its lower bound, so a model
    may arrive before the window opens; the records give the same times."""
    height, at = crest(minutes, y, window)
    up = (y[1:] >= height / 2) & (y[:-1] < height / 2) & (minutes[1:] <= at)
    k = int(np.nonzero(up)[0][-1]) + 1
    return float(
        minutes[k - 1]
        + (height / 2 - y[k - 1]) * (minutes[k] - minutes[k - 1]) / (y[k] - y[k - 1])
    )


def model_series(run: Run, station: str) -> Series:
    """The computed surface at a station as a modelled series."""
    return Series(
        x=run.t / 60.0,
        y=run.records[station],
        artifact="modelled-reference",
        x_name="time after the origin",
        x_unit="min",
        y_name="sea level minus tide",
        y_unit="m",
    )


def measured(station: str) -> Series:
    """The record of a station, the drawn part of it."""
    return dart_residual_series(records()[station]).select(*SHOWN[station])


def metric(series_x, series_y, station) -> tuple[float, float, float]:
    """Arrival (min), crest (m), crest time (min) in the station's window."""
    window = WINDOWS[station]
    height, at = crest(series_x, series_y, window)
    return half_crest_time(series_x, series_y, window), height, at


def run_metric(run: Run, station: str) -> tuple[float, float, float]:
    return metric(run.t / 60.0, run.records[station], station)


def record_metric(station: str) -> tuple[float, float, float]:
    s = dart_residual_series(records()[station])
    return metric(s.x, s.y, station)


def below(bound: float) -> str:
    return f"below {bound:.0e}"


# Benchmarks.


def still_water(experiment: Experiment) -> None:
    """Water at rest over the 16' bathymetry on the rotating sphere, open
    boundaries, one hour."""
    d = domain(COARSE)
    run = tsunami.simulate(d.grid, at_rest(d.grid), 3600.0, COURANT, limiter=LIMITER)
    wet = run.q[..., 0] > tsunami.WET
    surface = float(np.max(np.abs(run.q[..., 0] + d.grid.bed)[wet]))
    speed = float(
        np.max(
            np.hypot(
                *(run.q[..., k] / np.where(wet, run.q[..., 0], 1.0) for k in (1, 2))
            )
        )
    )
    bound = 1e-9
    if not (surface < bound and speed < bound):
        raise AssertionError(f"the water at rest moved: {surface}, {speed}")
    experiment.number("still-steps", run.steps)
    experiment.number("still-bound", f"{bound:.0e}")
    experiment.table(
        "still-water",
        [
            (
                f"{d.grid.shape[0]} x {d.grid.shape[1]}",
                run.steps,
                below(bound),
                below(bound),
            )
        ],
        [
            ("cells", "", ""),
            ("steps", "", "d"),
            ("largest |surface|", "m", ""),
            ("largest speed", "m/s", ""),
        ],
        "Water at rest over the bathymetry of the 16' grid, on the rotating "
        "sphere, after one hour: it stays at rest.",
    )


PLANE_CELLS = (50, 100, 200, 400)


SCHEMES = {
    "first order (FL5)": None,
    "minmod": "minmod",
    "monotonized central": "monotonized central",
}


def linear_wave(experiment: Experiment, errors: dict[str, list[float]]) -> None:
    rows = []
    for k, n in enumerate(PLANE_CELLS):
        row: list = [800.0 / n]
        for e in errors.values():
            row += [e[k], None if k == 0 else np.log2(e[k - 1] / e[k])]
        rows.append(row)
    columns = [("cell", "km", ".0f")]
    for name in SCHEMES:
        columns += [
            (f"rms error, {name}", "of the amplitude", ".2e"),
            ("order", "", ".2f"),
        ]
    experiment.table(
        "linear-wave",
        rows,
        columns,
        "A plane hump on a flat bed 4000 m deep, against d'Alembert's solution "
        "after 1000 s: the first-order scheme of FL5 converges at first order, "
        "the two reconstructions faster, the monotonized central slopes with "
        "the smallest error.",
    )
    for key, name in (
        ("first", "first order (FL5)"),
        ("minmod", "minmod"),
        ("mc", "monotonized central"),
    ):
        e = errors[name]
        experiment.number(f"order-{key}", np.log2(e[-2] / e[-1]), ".2f")
    experiment.number(
        "error-ratio", errors["minmod"][-1] / errors["monotonized central"][-1], ".1f"
    )


def radial_speed(experiment: Experiment) -> dict:
    run, r = radial_run(5e3, COURANT, LIMITER)
    n = r.shape[0]
    eta = run.q[..., 0] - RADIAL["depth"]
    lines = {
        "along an axis": (r[0], eta[0]),
        "along the diagonal": (np.diag(r), np.diag(eta)),
    }
    c = np.sqrt(GRAVITY * RADIAL["depth"])
    rows, found = [], {}
    for name, (radius, value) in lines.items():
        exact = radial_exact(radius, RADIAL["t"])
        error = float(np.sqrt(np.mean((value - exact) ** 2)) / RADIAL["amplitude"])
        k = int(np.argmax(value))
        k_exact = int(np.argmax(exact))
        rows.append(
            (name, radius[k] / 1e3, radius[k_exact] / 1e3, c * RADIAL["t"] / 1e3, error)
        )
        found[name] = (radius, value, exact)
    experiment.table(
        "radial",
        rows,
        [
            ("line", "", ""),
            ("computed crest", "km", ".0f"),
            ("exact crest", "km", ".0f"),
            ("sqrt(gh) t", "km", ".0f"),
            ("rms error", "of the amplitude", ".2e"),
        ],
        f"A Gaussian hump on a flat bed, {n} x {n} cells of 5 km in a quarter "
        "domain, after 1200 s, against the exact linear solution: the crest is "
        "where the exact solution puts it along the axis and the diagonal alike.",
    )
    errors = [row[-1] for row in rows]
    experiment.number("radial-error", max(errors), ".1e")
    experiment.number("radial-lead", rows[0][2] - rows[0][3], ".0f")
    if float(np.max(np.abs(run.volume - run.volume[0])) / run.volume[0]) >= 1e-13:
        raise AssertionError("the closed quarter domain lost volume")
    return found


CFL_NUMBERS = (0.4, 0.8, 1.0, 1.1, 1.2)


def cfl_study(experiment: Experiment) -> None:
    rows = []
    for courant in CFL_NUMBERS:
        run, _ = radial_run(10e3, courant, LIMITER, max_steps=2000)
        top = float(np.nanmax(np.abs(run.q[..., 0] - RADIAL["depth"])))
        stable = bool(np.isfinite(top) and top <= RADIAL["amplitude"])
        growth = f"{top / RADIAL['amplitude']:.3g}" if np.isfinite(top) else "overflow"
        rows.append((courant, run.steps, growth, "yes" if stable else "no"))
    experiment.table(
        "cfl",
        rows,
        [
            ("Courant number", "", ".2f"),
            ("steps", "", "d"),
            ("largest |surface| at the end", "of the initial crest", ""),
            ("stable", "", ""),
        ],
        "The hump of the radial benchmark on 10 km cells for 1200 s at growing "
        "steps: the scheme is stable at the operating Courant number and "
        "beyond, and blows up above its limit.",
    )
    stable = [row[0] for row in rows if row[3] == "yes"]
    unstable = [row[0] for row in rows if row[3] == "no"]
    experiment.number("cfl-stable", max(stable), ".2f")
    experiment.number("cfl-unstable", min(unstable), ".2f")
    experiment.number("courant", COURANT, ".2f")


# The runs of the page: (factor, options) -> label.
RUNS = {
    (COARSEST, ()): "32', base",
    (COARSE, ()): "16', base",
    (BASE, ()): "8', base",
    (BASE, (("near", True),)): "8', near DART 21416, 45 min",
    (FINE, (("near", True),)): "4', near DART 21416, 45 min",
    **{
        (COARSE, tuple(options.items())): f"16', {name}"
        for name, options in VARIANTS.items()
        if options
    },
}


def budgets(experiment: Experiment) -> None:
    rows = []
    for (factor, options), name in RUNS.items():
        o = dict(options)
        d = domain(
            factor, o.get("large", False), o.get("rotating", True), o.get("near", False)
        )
        rows.append(_budget_row(name, kamchatka_run(factor, **o), d))
    worst = max(row[2] for row in rows)
    bound = 1e-12
    if worst >= bound:
        raise AssertionError(f"the volume budget does not close: {worst}")
    experiment.table(
        "budget",
        [
            (name, steps, below(bound), left, depth, wetted)
            for name, steps, _, left, depth, wetted in rows
        ],
        [
            ("run", "", ""),
            ("steps", "", "d"),
            ("budget residual", "of the volume", ""),
            ("left through the boundary", "km³", ".1f"),
            ("smallest depth", "m", ".1f"),
            ("land cells wet at the end", "", "d"),
        ],
        "Every run of the tsunami on the page: the volume changes only by what "
        "leaves through the open boundary, and no depth becomes negative.",
    )
    experiment.number("budget-bound", f"{bound:.0e}")
    experiment.number("run-count", len(rows))
    experiment.number("smallest-depth", min(row[4] for row in rows), ".1f")


def _budget_row(name: str, run: Run, d: Domain):
    gap = float(np.max(np.abs(run.budget_residual)) / run.volume[0])
    wetted = int(np.sum((d.grid.bed >= 0) & (run.q[..., 0] > tsunami.WET)))
    return name, run.steps, gap, run.outflow[-1] / 1e9, run.min_depth, wetted


# The Kamchatka model: grid, boundaries, source.


def inputs_table(experiment: Experiment) -> None:
    d = domain(BASE)
    near = domain(FINE, near=True)
    fault = inputs().fault
    up = inputs().deformation.up
    edge = np.concatenate([up[0], up[-1], up[:, 0], up[:, -1]])
    south, west, rows_n, columns_n = NEAR
    width_52 = np.interp(52.0, d.grid.lat, d.grid.width) / 1e3
    rows = [
        ("domain", f"{span(SOUTH, WEST, ROWS, COLUMNS)}"),
        ("bathymetry", "ETOPO 2022, every fourth 60″ cell (4'), 2 x 2 means (8')"),
        ("cells of the base grid", f"{d.grid.shape[0]} x {d.grid.shape[1]} (8')"),
        (
            "cell size at 52 °N",
            f"{d.grid.height / 1e3:.1f} km north-south, {width_52:.1f} km east-west",
        ),
        (
            "finest run",
            f"4', {near.grid.shape[0]} x {near.grid.shape[1]} cells, "
            f"{span(south, west, rows_n, columns_n)}, {NEAR_DURATION / 60:.0f} min",
        ),
        (
            "source",
            f"USGS finite fault, Mw {fault.mw:.2f}, vertical surface deformation "
            f"{up.min():.1f} to {up.max():.1f} m",
        ),
        (
            "edge of the deformation grid",
            f"up to {np.abs(edge).max():.2f} m; tapered to zero over {TAPER} of its "
            "steps",
        ),
        (
            "onset of the uplift",
            "rupture time plus half the rise time of the nearest subfault, 0 to "
            f"{d.onset.max():.0f} s",
        ),
        ("boundaries", "open (each ghost cell copies its neighbour); land is dry"),
        (
            "scheme",
            f"HLL, hydrostatic reconstruction, {LIMITER} slopes, Heun's method, "
            f"Courant number {COURANT}",
        ),
        ("time", f"{DURATION / 3600:.0f} h after the origin"),
    ]
    experiment.table(
        "inputs",
        rows,
        [("input", "", ""), ("value", "", "")],
        "The model of the tsunami: domain, grids, source, boundaries, and scheme.",
    )
    experiment.number("mw", fault.mw, ".2f")
    experiment.number("uplift-max", up.max(), ".1f")
    experiment.number("subsidence-max", -up.min(), ".1f")
    experiment.number("edge-lift", np.abs(edge).max(), ".2f")
    experiment.number("onset-max", d.onset.max() / 60.0, ".1f")
    for name in STATIONS:
        site = inputs().stations[name]
        experiment.number(f"depth-{name}", site.depth, ".0f")
        experiment.number(f"model-depth-{name}", gauge_depth(d, name), ".0f")


def span(south: float, west: float, rows: int, columns: int) -> str:
    """The extent of a crop of ``rows`` x ``columns`` 4' cells."""
    north, east = south + rows / 15, west + columns / 15
    return f"{south:.1f} to {north:.1f} °N, {west:.1f} to {east:.1f} °E"


def gauge_depth(d: Domain, name: str) -> float:
    """The model's depth at a station, interpolated as its surface is."""
    gauge = next(g for g in d.gauges if g.name == name)
    (i0, j0, i1, j1), w = gauge.weights(d.grid)
    corners = [
        d.grid.bed[i0, j0],
        d.grid.bed[i0, j1],
        d.grid.bed[i1, j0],
        d.grid.bed[i1, j1],
    ]
    return -float(np.array(corners) @ w)


def grid_runs(station: str) -> list[tuple[int, Run]]:
    """The runs of the grid study at a station, coarsest first: the base
    domain at 32', 16', 8', and at 21416 also the 4' run near it."""
    runs = [(f, kamchatka_run(f)) for f in (COARSEST, COARSE, BASE)]
    if station == STATIONS[0]:
        runs.append((FINE, kamchatka_run(FINE, near=True)))
    return runs


def grid_study(experiment: Experiment) -> dict:
    found, rows = {}, []
    for station in STATIONS:
        values = [run_metric(run, station) for _, run in grid_runs(station)]
        found[station] = values
        for k, (f, _) in enumerate(grid_runs(station)):
            arrival, height, at = values[k]
            change = None if k == 0 else arrival - values[k - 1][0]
            grow = None if k == 0 else 100 * (height / values[k - 1][1] - 1)
            rows.append(
                (f"DART {station}", GRID_NAMES[f], arrival, change, height, grow, at)
            )
    experiment.table(
        "grid-study",
        rows,
        [
            ("station", "", ""),
            ("grid", "", ""),
            ("arrival", "min", ".2f"),
            ("change", "min", "+.2f"),
            ("crest", "m", ".3f"),
            ("change", "%", "+.0f"),
            ("crest at", "min", ".1f"),
        ],
        "The arrival (half-crest crossing) and the crest at the two stations on "
        "grids of 32' to 4', each cell four times the area of the next (the 4' "
        "run on the smaller domain near DART 21416): the arrival changes less "
        "with each refinement, the crest does not.",
    )
    for station in STATIONS:
        h = [v[1] for v in found[station]]
        experiment.number(f"grid-crest-{station}", 100 * (h[-1] / h[-2] - 1), ".0f")
    a = [v[0] for v in found[STATIONS[0]]]
    experiment.number("grid-arrival-21416", a[-1] - a[-2], ".1f")
    experiment.number("fine-crest", found[STATIONS[0]][-1][1], ".2f")
    return found


def sensitivity(experiment: Experiment) -> dict:
    rows, found = [], {}
    pairs = [
        (station, name, kamchatka_run(COARSE), kamchatka_run(COARSE, **options))
        for station in STATIONS
        for name, options in VARIANTS.items()
        if options
    ]
    pairs.append(
        (
            STATIONS[0],
            "smaller domain (8')",
            kamchatka_run(BASE),
            kamchatka_run(BASE, near=True),
        )
    )
    for station, name, base_run, other_run in pairs:
        window = WINDOWS[station]
        end = min(window[1], other_run.t[-1] / 60.0)
        base = metric_until(base_run, station, end)
        other = metric_until(other_run, station, end)
        m = base_run.t / 60.0
        inside = (m >= window[0]) & (m <= end)
        other_y = np.interp(m, other_run.t / 60.0, other_run.records[station])
        gap = float(np.max(np.abs(other_y - base_run.records[station])[inside]))
        change = (other[0] - base[0], other[1] / base[1] - 1, gap)
        rows.append((f"DART {station}", name, change[0], 100 * change[1], gap))
        found[(station, name)] = change
    experiment.table(
        "sensitivity",
        rows,
        [
            ("station", "", ""),
            ("change from the base run", "", ""),
            ("arrival", "min", "+.2f"),
            ("crest", "%", "+.1f"),
            ("largest surface difference in the window", "m", ".3f"),
        ],
        "Against the base run on the same grid (16', and 8' for the smaller "
        "domain, compared up to its end): the uplift all at once instead of in "
        "the order of the rupture, the Earth's rotation left out, a domain twice "
        "as large in each direction, and the smaller domain of the 4' run.",
    )
    for station in STATIONS:
        experiment.number(
            f"kinematic-shift-{station}", -found[(station, "instantaneous")][0], ".1f"
        )
        experiment.number(
            f"boundary-gap-{station}", found[(station, "larger domain")][2] * 1e3, ".0f"
        )
    experiment.number(
        "near-gap", found[(STATIONS[0], "smaller domain (8')")][2] * 1e3, ".0f"
    )
    return found


def metric_until(run: Run, station: str, end: float) -> tuple[float, float, float]:
    window = (WINDOWS[station][0], end)
    m = run.t / 60.0
    height, at = crest(m, run.records[station], window)
    return half_crest_time(m, run.records[station], window), height, at


# The comparison with the records.


def comparison(experiment: Experiment, grid: dict, sens: dict) -> dict:
    rows, budget, found = [], [], {}
    for station in STATIONS:
        record = records()[station]
        obs = record_metric(station)
        runs = grid_runs(station)
        series = measured(station)
        window = WINDOWS[station]
        inside = (series.x >= window[0]) & (series.x <= window[1])
        floor = kamchatka_tsunami.noise_floor(record)
        rows.append(
            (f"DART {station}", "record", obs[0], obs[1], obs[2], None, None, floor)
        )
        for f, run in runs[1:]:
            mod = grid[station][[g for g, _ in runs].index(f)]
            if run.t[-1] / 60.0 >= window[1]:
                model = model_series(run, station)
                r = residual(series, model)
                shifted = Series(**{**model.__dict__, "x": model.x - (mod[0] - obs[0])})
                rms = float(np.sqrt(np.mean(r[inside] ** 2)))
                rms_shift = float(
                    np.sqrt(np.mean(residual(series, shifted)[inside] ** 2))
                )
            else:
                rms = rms_shift = None
            name = f"model, {GRID_NAMES[f]}" + (" (to 45 min)" if f == FINE else "")
            rows.append(
                (f"DART {station}", name, mod[0], mod[1], mod[2], rms, rms_shift, None)
            )
            if f == BASE:
                found[station] = {
                    "obs": obs,
                    "mod": mod,
                    "rms": rms,
                    "rms-shift": rms_shift,
                    "floor": floor,
                }
        finest, second = grid[station][-1], grid[station][-2]
        parts = {
            "last refinement of the grid": (
                abs(finest[0] - second[0]),
                abs(finest[1] / second[1] - 1),
            ),
            "source timing (all at once)": tuple(
                abs(v) for v in sens[(station, "instantaneous")][:2]
            ),
            "larger domain": tuple(
                abs(v) for v in sens[(station, "larger domain")][:2]
            ),
            "no rotation": tuple(abs(v) for v in sens[(station, "no rotation")][:2]),
        }
        spread_a = float(np.sqrt(sum(a * a for a, _ in parts.values()) + SAMPLING**2))
        spread_h = float(np.sqrt(sum(h * h for _, h in parts.values())))
        for name, (a, h) in parts.items():
            budget.append((f"DART {station}", name, a, 100 * h))
        budget.append((f"DART {station}", "sampling of the record", SAMPLING, None))
        budget.append(
            (f"DART {station}", "combined, as independent", spread_a, 100 * spread_h)
        )
        best = finest
        found[station].update(
            {"spread-a": spread_a, "spread-h": spread_h, "best": best}
        )
        mod = found[station]["mod"]
        experiment.number(f"obs-arrival-{station}", obs[0], ".1f")
        experiment.number(f"obs-crest-{station}", obs[1], ".2f")
        experiment.number(f"obs-crest-at-{station}", obs[2], ".1f")
        experiment.number(f"early-{station}", obs[0] - mod[0], ".1f")
        experiment.number(f"ratio-{station}", 100 * mod[1] / obs[1], ".0f")
        if station == STATIONS[0]:
            experiment.number("best-early-21416", obs[0] - best[0], ".1f")
            experiment.number("best-ratio-21416", 100 * best[1] / obs[1], ".0f")
        experiment.number(f"rms-{station}", found[station]["rms"], ".3f")
        experiment.number(f"rms-shift-{station}", found[station]["rms-shift"], ".3f")
        experiment.number(f"floor-{station}", floor, ".3f")
        experiment.number(f"spread-a-{station}", spread_a, ".1f")
        experiment.number(f"window-{station}", f"+{window[0]:.0f} to +{window[1]:.0f}")
    experiment.table(
        "comparison",
        rows,
        [
            ("station", "", ""),
            ("series", "", ""),
            ("arrival", "min", ".1f"),
            ("crest", "m", ".3f"),
            ("crest at", "min", ".1f"),
            ("rms residual in the window", "m", ".3f"),
            ("rms after the time shift", "m", ".3f"),
            ("rms the day before", "m", ".3f"),
        ],
        "The metric fixed before the comparison, at each station in its window: "
        "the arrival as the half-crest crossing, the crest, and the residual "
        "model minus record, also after shifting the model by the difference "
        "of the arrivals.",
    )
    experiment.table(
        "uncertainty",
        budget,
        [
            ("station", "", ""),
            ("source of spread", "", ""),
            ("arrival", "min", ".2f"),
            ("crest", "%", ".1f"),
        ],
        "What moves the model's arrival and crest at its finest grid: the "
        "change of the last refinement, the variants of the source, the domain "
        "and the rotation, and the sampling of the records, combined as if "
        "independent.",
    )
    return found


# Exercises.

PERIODS = (4.0, 10.0, 20.0)  # min


def dispersion(experiment: Experiment, comp: dict) -> None:
    """How much later would linear dispersion bring a wave of a given
    period, at the station's depth, over its travel time?"""
    rows = []
    for station in STATIONS:
        depth = inputs().stations[station].depth
        travel = comp[station]["obs"][0]
        c0 = np.sqrt(GRAVITY * depth)
        for minutes in PERIODS:
            omega = 2 * np.pi / (60.0 * minutes)
            k = omega / c0
            for _ in range(200):  # omega^2 = g k tanh(k h), by fixed point
                k = omega**2 / (GRAVITY * np.tanh(k * depth))
            c = omega / k
            group = 0.5 * c * (1 + 2 * k * depth / np.sinh(2 * k * depth))
            rows.append(
                (
                    f"DART {station}",
                    minutes,
                    2 * np.pi / k / 1e3,
                    c / c0,
                    group / c0,
                    travel * (c0 / group - 1),
                )
            )
    experiment.table(
        "dispersion",
        rows,
        [
            ("station", "", ""),
            ("period", "min", ".0f"),
            ("wavelength", "km", ".0f"),
            ("phase speed", "of sqrt(gh)", ".3f"),
            ("group speed", "of sqrt(gh)", ".3f"),
            ("delay over the travel time", "min", ".1f"),
        ],
        "Linear dispersion at the depth of each station over its observed "
        "arrival time: little for the long periods of the records, much for "
        "the short waves of a narrow source.",
    )
    long = [row[-1] for row in rows if row[1] == PERIODS[-1]]
    short = [row[-1] for row in rows if row[1] == PERIODS[0]]
    experiment.number("dispersion-long", max(long), ".1f")
    experiment.number("dispersion-short", min(short), ".0f")


def rotation(experiment: Experiment, sens: dict) -> None:
    f = 2 * tsunami.OMEGA * np.sin(np.radians(50.0))
    experiment.number("inertial-period", 2 * np.pi / f / 3600.0, ".1f")
    experiment.number(
        "rotation-shift",
        max(abs(sens[(s, "no rotation")][0]) * 60.0 for s in STATIONS),
        ".0f",
    )


# Figures.


def draw_map() -> Figure:
    d = domain(BASE)
    run = kamchatka_run(BASE)
    land = d.grid.bed - d.uplift >= 0
    extent = (d.grid.lon[0], d.grid.lon[-1], d.grid.lat[0], d.grid.lat[-1])
    fig, ax = plt.subplots(figsize=(5.0, 4.2), layout="constrained")
    peak = np.where(land, np.nan, np.clip(run.peak, 0.0, 1.0))
    sequential_image(
        ax,
        peak,
        label="largest height",
        unit="m",
        extent=extent,
        aspect=1.0 / np.cos(np.radians(50.5)),
        interpolation="nearest",
        norm=BoundaryNorm(np.linspace(0.0, 1.0, 9), 256),
    )
    minutes = np.where(np.isfinite(run.arrival) & ~land, run.arrival / 60.0, np.nan)
    lon, lat = d.grid.lon, d.grid.lat
    arrival = ax.contour(
        lon,
        lat,
        minutes,
        levels=np.arange(15.0, 120.0, 15.0),
        colors="w",
        linewidths=0.6,
    )
    ax.clabel(arrival, fmt="%d min", fontsize=6)
    ax.contour(lon, lat, d.uplift, levels=[1.0, 3.0, 5.0], colors="k", linewidths=0.7)
    ax.contour(
        lon,
        lat,
        d.uplift,
        levels=[-2.0, -1.0],
        colors="k",
        linewidths=0.7,
        linestyles="--",
    )
    epicentre = kamchatka_tsunami.EPICENTRE
    ax.plot(epicentre[1], epicentre[0], "*", ms=9, mfc="w", mec="k")
    for name in STATIONS:
        site = inputs().stations[name]
        ax.plot(site.lon, site.lat, "^", ms=6, mfc="w", mec="k")
        ax.annotate(
            name,
            (site.lon, site.lat),
            (4, -9),
            textcoords="offset points",
            fontsize=7,
            color="w",
        )
    handles = [
        Line2D([], [], color="w", lw=0.6, label="arrival, every 15 min"),
        Line2D([], [], color="k", lw=0.7, label="USGS uplift 1, 3, 5 m"),
        Line2D([], [], color="k", lw=0.7, ls="--", label="subsidence 1, 2 m"),
        Line2D([], [], ls="", marker="*", mfc="w", mec="k", ms=8, label="epicentre"),
        Line2D([], [], ls="", marker="^", mfc="w", mec="k", label="DART station"),
    ]
    # Anchored below the axis label "longitude", which it must not cover; the
    # constrained layout keeps room for it above the credit.
    ax.legend(
        handles=handles,
        fontsize=6.5,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.24),
        ncols=3,
        facecolor="0.85",
    )
    ax.set_xlabel("longitude [degrees E]")
    ax.set_ylabel("latitude [degrees N]")
    ax.set_title("Model, 8' grid: height and arrival")
    label_status(fig, "simulated")
    add_credit(fig, CREDIT)
    return fig


def comparison_models(station: str) -> dict[str, Series]:
    """The modelled series drawn against a station's record: 8', and at
    21416 the 4' run, which ends at 45 minutes."""
    models = {}
    for f, run in grid_runs(station)[2:]:
        name = f"model, {GRID_NAMES[f]}" + (", to 45 min" if f == FINE else "")
        models[name] = model_series(run, station)
    return models


def draw_comparison() -> Figure:
    """Each record solid with the models dashed and apart, the residuals
    model minus record below on the same time axis, the compared window
    shaded: the panels of ``measured_vs_model``, for the two stations side
    by side."""
    fig, axes = plt.subplots(
        2,
        2,
        figsize=(7.0, 3.8),
        sharex="col",
        height_ratios=(3, 2),
        layout="constrained",
    )
    styles = {"16'": ":", "8'": "--", "4'": "-."}  # the grids, also by line
    for k, station in enumerate(STATIONS):
        top, bottom = axes[0, k], axes[1, k]
        record = measured(station)
        if record.status == "simulated":
            raise ValueError("the record is a simulation")
        plot_series(top, record, "record", colour=COLOURS[0], lw=1.4)
        bottom.axhline(0, color="0.5", lw=0.8)
        for (name, model), colour in zip(
            comparison_models(station).items(), COLOURS[1:], strict=False
        ):
            if model.status != "simulated":
                raise ValueError(f"model {name!r} is {model.status}, not simulated")
            style = styles[name.split(", ")[1]]
            keep = (model.x >= SHOWN[station][0]) & (model.x <= SHOWN[station][1])
            top.plot(
                model.x[keep],
                model.y[keep],
                color=colour,
                lw=1.1,
                ls=style,
                label=f"{name} [{model.status}]",
            )
            bottom.plot(
                record.x,
                residual(record, model),
                color=colour,
                lw=0.9,
                ls=style,
                label=name,
            )
        for ax in (top, bottom):
            ax.axvspan(*WINDOWS[station], color="0.5", alpha=0.12, lw=0)
            ax.set_xlim(*SHOWN[station])
        top.set_title(f"DART {station}: record and model")
        top.set_ylabel("sea level - tide [m]", fontsize=8)
        top.legend(fontsize=6, loc="upper right" if k == 0 else "lower left")
        bottom.set_title("Residual: model minus record")
        bottom.set_xlabel("time after the origin [min]")
        bottom.set_ylabel("residual [m]", fontsize=8)
        bottom.legend(fontsize=6, loc="lower right" if k == 0 else "upper left")
    label_status(fig, record.status)
    add_credit(fig, CREDIT)
    return fig


def fine_check() -> dict[str, tuple[float, float, float]]:
    """Not run by the page or the checks: the base run on the whole domain
    at 4' (about a minute), with the arrival, the crest and its time at each
    station."""
    run = kamchatka_run(FINE)
    return {station: run_metric(run, station) for station in STATIONS}


def run() -> Experiment:
    experiment = Experiment()
    still_water(experiment)
    plane_errors = plane_wave_errors(PLANE_CELLS, SCHEMES, COURANT)
    linear_wave(experiment, plane_errors)
    radial_speed(experiment)
    cfl_study(experiment)
    inputs_table(experiment)
    budgets(experiment)
    grid = grid_study(experiment)
    sens = sensitivity(experiment)
    comp = comparison(experiment, grid, sens)
    dispersion(experiment, comp)
    rotation(experiment, sens)
    experiment.figure(
        "fig-tsunami-benchmarks",
        lambda: draw_plane_wave_convergence(plane_errors, PLANE_CELLS),
    )
    experiment.figure("fig-tsunami-map", draw_map)
    experiment.figure("fig-tsunami-comparison", draw_comparison)
    return experiment


if __name__ == "__main__":
    main(run)
