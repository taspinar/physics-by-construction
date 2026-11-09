"""trackpy-examples ``bulk_water``: tracked 1 µm spheres and their diffusion.

Status of the figure: *processed*. The frames are measurements (video of
1 µm latex spheres in water, 24 frames per second, 2.85 pixels per µm, as the
provider's README states). Everything else is the project's own processing,
disclosed as such: the particles are located and linked by
``pbc.data.tracking`` (NumPy and SciPy, not trackpy) once, outside the build,
by ``tools/datasets/bulk_water_tracks.py`` on the 40 frames 000-039; the
committed CSV holds every located feature with its track number. This module
reads that CSV, keeps the tracks of at least ``MIN_LENGTH`` frames, subtracts
the drift of the whole sample, and fits the ensemble mean squared
displacement (MSD) of lags 1 to 10 frames with a straight line,

    MSD(tau) = 4 D tau + c,

whose slope gives the diffusion coefficient D in two dimensions and whose
intercept c takes the localisation noise (positive) and the motion blur
(negative) that the record does not quantify. The uncertainty of D is the
standard deviation of a bootstrap over tracks (the MSD points share their
tracks and are correlated, so the least-squares error of the fit would be too
small). The Stokes-Einstein value kT / (6 pi eta r) for a sphere of diameter
1 µm in water is the model it is compared with, at 20 and 25 °C, because the
record gives no temperature; ``sensitivity`` repeats the analysis with other
choices of the processing.

The green channel of frames 000-002 is committed as a NumPy array (the
repository commits no image file outside site/assets/, invariant I6); it lets
the build repeat the detection and the linking on real frames and compare
them with the CSV (tests/unit/test_data_bulk_water.py). ``read_frame`` reads
a downloaded PNG, for the one-time tracking.
"""

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np

from pbc.data import tracking
from pbc.data.plotting import COLOURS, add_credit, label_status

TRACKS = "bulk_water_tracks.csv"
# The green channel of frames 000-002 (the PNGs are not committed: I6).
FRAMES = "bulk_water_green_000-002.npy"
COMMITTED_FRAMES = 3
README = "README"
FIELDS = ("frame", "particle", "x", "y", "mass")
UNITS = {
    "frame": "frame number (24 per second)",
    "particle": "track number",
    "x": "px",
    "y": "px",
    "mass": "grey levels (band-passed, summed over the disk)",
}
SHAPE = (424, 640)  # rows, columns of every frame
FRAME_COUNT = 40  # frames 000-039 were tracked
FPS = 24.0  # frames per second (provider's README)
MICRONS_PER_PIXEL = 1 / 2.85  # "1 micron = 2.85 pixels" (provider's README)
# The tracking, chosen once from frame 000 and kept for all frames.
# px: the disk of the maxima and the centroid (diameter 11, as trackpy's notebook)
RADIUS = 5
SMOOTHING = 1.0  # px: the Gaussian of the band-pass
MINMASS = 90.0  # the minimum of the mass histogram between the noise and the particles
SEARCH_RANGE = 3.0  # px: about 6 times the rms step per axis (0.52 px)
MIN_LENGTH = 15  # frames: the shortest track used for the MSD
LAGS = np.arange(1, 11)  # frames
BOOTSTRAP = 1000
SEED = 20261108
# Stokes-Einstein.
BOLTZMANN = 1.380649e-23  # J/K (exact, SI 2019)
RADIUS_SPHERE = 0.5e-6  # m: half the nominal 1 µm (no tolerance given)
# Viscosity of water at 0.1 MPa [Pa s], IAPWS R12-08 (2008): 1001.6 and 890.0 µPa s.
VISCOSITY = {20.0: 1.0016e-3, 25.0: 0.8900e-3}
# The choices compared by ``sensitivity``.
VARIANTS = {
    "link range 2 px": {"search_range": 2.0},
    "link range 4 px": {"search_range": 4.0},
    "mass >= 120": {"minmass": 120.0},
    "tracks >= 10 frames": {"min_length": 10},
    "tracks >= 25 frames": {"min_length": 25},
    "lags 1-5": {"lags": np.arange(1, 6)},
    "lags 2-10": {"lags": np.arange(2, 11)},
    "no drift subtracted": {"subtract_drift": False},
}


@dataclass(frozen=True)
class Tracks:
    frame: np.ndarray  # int, 0-39
    particle: np.ndarray  # int, track number
    xy: np.ndarray  # (n, 2) px
    mass: np.ndarray  # grey levels
    header: tuple[str, ...]  # the comment lines of the CSV


# Reading the frames and tracking them.


def read_frame(path: Path) -> np.ndarray:
    """The green channel of one frame in grey levels 0-255 (as trackpy's
    walkthrough reads it); the PNG is RGBA, 8 bits per channel."""
    rgba = mpimg.imread(Path(path))
    if rgba.ndim != 3 or rgba.shape[:2] != SHAPE or rgba.shape[2] != 4:
        raise ValueError(f"{path}: shape {rgba.shape}, expected {SHAPE} x 4")
    return np.round(rgba[..., 1] * 255.0)


def read_frames(path: Path) -> np.ndarray:
    """The committed green channels, shape (3, 424, 640), grey levels as
    floats; the file holds uint8 and no Python object."""
    green = np.load(Path(path), allow_pickle=False)
    if green.dtype != np.uint8 or green.shape != (COMMITTED_FRAMES, *SHAPE):
        raise ValueError(f"{path}: {green.dtype} {green.shape}, expected uint8")
    return green.astype(float)


def detect(green: np.ndarray, minmass: float = MINMASS) -> np.ndarray:
    """Features (x, y, mass) of one frame: dark spheres on a bright field."""
    return tracking.locate(green, RADIUS, minmass, smoothing=SMOOTHING, invert=True)


def track(frames: list[np.ndarray]) -> np.ndarray:
    """Rows (frame, particle, x, y, mass) of the green channels ``frames``."""
    features = [detect(green) for green in frames]
    numbers = tracking.link(features, SEARCH_RANGE)
    return np.vstack(
        [
            np.column_stack([np.full(len(f), k), n, f])
            for k, (f, n) in enumerate(zip(features, numbers, strict=True))
        ]
    )


def format_rows(rows: np.ndarray) -> list[str]:
    """The CSV lines of ``rows``: positions to 0.001 px, mass to 0.1."""
    return [f"{int(f)},{int(p)},{x:.3f},{y:.3f},{m:.1f}" for f, p, x, y, m in rows]


def read_tracks(path: Path) -> Tracks:
    """Read the CSV written by ``tools/datasets/bulk_water_tracks.py``."""
    lines = Path(path).read_text(encoding="ascii").splitlines()
    header = tuple(line for line in lines if line.startswith("#"))
    names = next(line for line in lines if not line.startswith("#")).split(",")
    if tuple(names) != FIELDS:
        raise ValueError(f"{path}: columns {names}, expected {FIELDS}")
    table = np.loadtxt(path, delimiter=",", skiprows=len(header) + 1, ndmin=2)
    if table.shape[1] != len(FIELDS):
        raise ValueError(f"{path}: rows of {table.shape[1]} values")
    if not np.all(np.isfinite(table)):
        raise ValueError(f"{path}: a value that is not a finite number")
    for k in (0, 1):
        if not np.all(table[:, k] == np.round(table[:, k])):
            raise ValueError(f"{path}: a {FIELDS[k]} that is not an integer")
    return Tracks(
        table[:, 0].astype(int),
        table[:, 1].astype(int),
        table[:, 2:4],
        table[:, 4],
        header,
    )


def load(data_dir: Path) -> Tracks:
    return read_tracks(Path(data_dir) / TRACKS)


def relink(tracks: Tracks, search_range: float, minmass: float = MINMASS) -> Tracks:
    """The same features (those of at least ``minmass``) linked anew."""
    keep = tracks.mass >= minmass
    frame, xy, mass = tracks.frame[keep], tracks.xy[keep], tracks.mass[keep]
    order = np.lexsort((np.arange(len(frame)), frame))
    frame, xy, mass = frame[order], xy[order], mass[order]
    per_frame = [xy[frame == k] for k in range(frame.max() + 1)]
    particle = np.concatenate(tracking.link(per_frame, search_range))
    return Tracks(frame, particle, xy, mass, tracks.header)


# The analysis.


@dataclass(frozen=True)
class Analysis:
    tau: np.ndarray  # s
    msd: np.ndarray  # µm^2
    msd_err: np.ndarray  # µm^2, bootstrap standard deviation
    diffusion: float  # µm^2/s
    diffusion_err: float  # µm^2/s, bootstrap
    intercept: float  # µm^2
    intercept_err: float  # µm^2, bootstrap
    tracks: int  # tracks used
    features: int  # features in them
    drift: np.ndarray  # (frames, 2) µm, the subtracted motion of the sample
    steps: np.ndarray  # (n, 2) µm, lag-1 displacements after the drift
    step_correlation: float  # of successive lag-1 steps of a track, per axis
    excess_kurtosis: float  # of the lag-1 steps, x and y pooled (0 for a Gaussian)
    track_spread: float  # relative sd of the step variance of tracks of >= 30 steps
    track_spread_expected: float  # the same for identical Gaussian walkers


def stokes_einstein(celsius: float) -> float:
    """kT / (6 pi eta r) [µm^2/s] for the nominal sphere in water."""
    kelvin = celsius + 273.15
    return BOLTZMANN * kelvin / (6 * np.pi * VISCOSITY[celsius] * RADIUS_SPHERE) * 1e12


def _line(tau: np.ndarray, msd: np.ndarray) -> tuple[float, float]:
    slope, intercept = np.polyfit(tau, msd, 1)
    return slope, intercept


def analyse(
    tracks: Tracks,
    *,
    search_range: float | None = None,
    minmass: float | None = None,
    min_length: int = MIN_LENGTH,
    lags: np.ndarray = LAGS,
    subtract_drift: bool = True,
    bootstrap: int = BOOTSTRAP,
) -> Analysis:
    if search_range is not None or minmass is not None:
        tracks = relink(
            tracks,
            SEARCH_RANGE if search_range is None else search_range,
            MINMASS if minmass is None else minmass,
        )
    length = np.bincount(tracks.particle)
    keep = length[tracks.particle] >= min_length
    frame, particle = tracks.frame[keep], tracks.particle[keep]
    xy = tracks.xy[keep] * MICRONS_PER_PIXEL
    motion = tracking.drift(frame, particle, xy)
    if subtract_drift:
        xy = xy - motion[frame]
    sums, counts, numbers = tracking.msd_sums(frame, particle, xy, lags)
    tau = lags / FPS
    msd = sums.sum(axis=0) / counts.sum(axis=0)
    slope, intercept = _line(tau, msd)
    rng = np.random.default_rng(SEED)
    resampled = np.empty((bootstrap, len(lags)))
    lines = np.empty((bootstrap, 2))
    for k in range(bootstrap):
        pick = rng.integers(0, len(numbers), len(numbers))
        resampled[k] = sums[pick].sum(axis=0) / counts[pick].sum(axis=0)
        lines[k] = _line(tau, resampled[k])
    order = np.lexsort((frame, particle))
    p, d = particle[order], xy[order]
    linked = p[1:] == p[:-1]
    steps = (d[1:] - d[:-1])[linked]
    successive = linked[1:] & linked[:-1]
    step = d[1:] - d[:-1]
    first, second = step[:-1][successive], step[1:][successive]
    correlation = float(np.corrcoef(first.ravel(), second.ravel())[0, 1])
    values = steps.ravel()
    kurtosis = float(np.mean(values**4) / np.mean(values**2) ** 2 - 3)
    _, owner = np.unique(p[1:][linked], return_inverse=True)
    count = np.bincount(owner)
    variance = np.bincount(owner, weights=(steps**2).sum(axis=1)) / (2 * count)
    long = count >= 30
    spread = float(variance[long].std() / variance[long].mean())
    # a variance from 2 n Gaussian values has the relative sd sqrt(1 / n)
    expected = float(np.mean(np.sqrt(1 / count[long])))
    return Analysis(
        tau=tau,
        msd=msd,
        msd_err=resampled.std(axis=0, ddof=1),
        diffusion=slope / 4,
        diffusion_err=float(lines[:, 0].std(ddof=1) / 4),
        intercept=intercept,
        intercept_err=float(lines[:, 1].std(ddof=1)),
        tracks=len(numbers),
        features=int(keep.sum()),
        drift=motion,
        steps=steps,
        step_correlation=correlation,
        excess_kurtosis=kurtosis,
        track_spread=spread,
        track_spread_expected=expected,
    )


def block_steps(green: np.ndarray, block: int = 8) -> np.ndarray:
    """Mean absolute difference [grey levels] of horizontally neighbouring
    pixels, by the column of the left one modulo ``block``: a step at the
    last position larger than the others is the edge of a compression block."""
    step = np.abs(np.diff(np.asarray(green, dtype=float), axis=1)).mean(axis=0)
    return np.array([step[k::block].mean() for k in range(block)])


def sensitivity(tracks: Tracks) -> dict[str, float]:
    """D [µm^2/s] for each choice of ``VARIANTS`` (no bootstrap)."""
    return {
        name: analyse(tracks, bootstrap=2, **options).diffusion
        for name, options in VARIANTS.items()
    }


# The figure.


def make_figure(data_dir: Path):
    data_dir = Path(data_dir)
    tracks = load(data_dir)
    result = analyse(tracks)
    green = read_frames(data_dir / FRAMES)[0]
    fig = plt.figure(figsize=(13, 6.4), constrained_layout=True)
    grid = fig.add_gridspec(2, 3, height_ratios=(2.2, 1), width_ratios=(1.25, 1, 1))
    image = fig.add_subplot(grid[:, 0])
    top = fig.add_subplot(grid[0, 1])
    bottom = fig.add_subplot(grid[1, 1], sharex=top)
    steps = fig.add_subplot(grid[:, 2])

    # A corner of frame 000 with the tracks, as measured (drift included).
    x0, x1, y0, y1 = 0, 200, 0, 200
    image.imshow(
        green[y0:y1, x0:x1],
        cmap="gray",
        extent=(x0 - 0.5, x1 - 0.5, y1 - 0.5, y0 - 0.5),
        interpolation="nearest",
    )
    length = np.bincount(tracks.particle)
    first = True
    for number in np.unique(tracks.particle[length[tracks.particle] >= MIN_LENGTH]):
        rows = tracks.particle == number
        order = np.argsort(tracks.frame[rows])
        x, y = tracks.xy[rows][order].T
        if x.min() >= x0 and x.max() < x1 and y.min() >= y0 and y.max() < y1:
            image.plot(
                x,
                y,
                color=COLOURS[4],
                lw=1.0,
                label="tracks over 40 frames [processed]" if first else None,
            )
            first = False
    start = tracks.frame == 0
    image.plot(
        *tracks.xy[start].T,
        "o",
        mfc="none",
        mec=COLOURS[5],
        ms=9,
        mew=0.8,
        label="features located in frame 000",
    )
    image.set_xlim(x0 - 0.5, x1 - 0.5)
    image.set_ylim(y1 - 0.5, y0 - 0.5)
    image.set_xlabel("x [px]")
    image.set_ylabel("y [px]")
    image.set_title("Frame 000, green channel, top-left corner")
    image.legend(fontsize=7, loc="lower right")

    # The MSD, the line fitted to it, and Stokes-Einstein.
    tau_ms = result.tau * 1e3
    top.errorbar(
        tau_ms,
        result.msd,
        yerr=result.msd_err,
        fmt="o",
        color=COLOURS[0],
        ms=4,
        capsize=2,
        label=f"MSD, {result.tracks} tracks [processed]: 1 sigma (bootstrap)",
    )
    fine = np.linspace(0, result.tau[-1], 50)
    top.plot(
        fine * 1e3,
        4 * result.diffusion * fine + result.intercept,
        "--",
        color=COLOURS[1],
        label=(
            f"fit 4Dτ + c: D = {result.diffusion:.3f} ± "
            f"{result.diffusion_err:.3f} µm²/s"
        ),
    )
    for celsius, style in ((20.0, ":"), (25.0, "-.")):
        top.plot(
            fine * 1e3,
            4 * stokes_einstein(celsius) * fine + result.intercept,
            style,
            color=COLOURS[2],
            label=(
                f"Stokes-Einstein {celsius:.0f} °C: "
                f"{stokes_einstein(celsius):.3f} µm²/s (same c)"
            ),
        )
    top.set_ylabel("MSD [µm²]")
    top.set_title("Drift-corrected MSD, lags 1-10 frames")
    top.legend(fontsize=7, loc="upper left")
    bottom.axhline(0, color="0.5", lw=0.8)
    residual = result.msd - (4 * result.diffusion * result.tau + result.intercept)
    bottom.errorbar(
        tau_ms,
        residual,
        yerr=result.msd_err,
        fmt="o",
        color=COLOURS[0],
        ms=4,
        capsize=2,
    )
    bottom.set_xlabel("lag time τ [ms]")
    bottom.set_ylabel("residual [µm²]")
    bottom.set_title("Residual: measurement minus fit")

    # The lag-1 steps against the Gaussian of the measured variance.
    values = result.steps.ravel()
    sigma = np.sqrt(np.mean(values**2))
    # Every step: a linked step is at most the link range in x and in y
    # (and the drift of a frame, about 0.02 µm, is added).
    reach = SEARCH_RANGE * MICRONS_PER_PIXEL
    edges = np.linspace(-1.1 * reach, 1.1 * reach, 89)
    steps.hist(
        values,
        bins=edges,
        density=True,
        color=COLOURS[0],
        alpha=0.6,
        label=(
            f"x and y steps [processed]\nn = {values.size}, "
            f"excess kurtosis {result.excess_kurtosis:.1f}"
        ),
    )
    grid_x = np.linspace(edges[0], edges[-1], 300)
    steps.plot(
        grid_x,
        np.exp(-0.5 * (grid_x / sigma) ** 2) / (sigma * np.sqrt(2 * np.pi)),
        "--",
        color=COLOURS[1],
        label=f"Gaussian, rms {sigma:.3f} µm",
    )
    steps.set_yscale("log")
    steps.set_ylim(1e-3, None)
    steps.set_xlabel("displacement in one frame [µm]")
    steps.set_ylabel("probability density [1/µm]")
    steps.set_title("Steps after the drift, log scale")
    steps.legend(fontsize=7, loc="upper left")

    label_status(fig, "processed")
    add_credit(
        fig,
        "Frames: trackpy-examples, sample_data/bulk_water (commit 09fb307), "
        "Copyright (c) 2013-2014 trackpy-examples contributors, CC BY 3.0 "
        "https://creativecommons.org/licenses/by/3.0/. Tracking, drift "
        "subtraction and fit are this project's processing (NumPy, SciPy), "
        "not the provider's.",
    )
    return fig
