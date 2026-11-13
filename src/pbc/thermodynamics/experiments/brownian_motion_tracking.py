"""The experiment of the lesson "Brownian motion tracking lab".

The random walk of the lesson "Random walks and diffusion", seen through a
camera (``pbc.thermodynamics.brownian``), against the tracked spheres of the
card ``trackpy-bulk-water``: a published video of 1 µm latex spheres in
water, 24 frames per second, 2.85 pixels per µm, whose frames 000-039 this
project located and linked (the committed tracks CSV, the project's own
processing). The experiment checks the camera model on simulated walks,
reads the frames and the tracks, infers the diffusion coefficient D from the
drift-corrected mean squared displacement (MSD) with a bootstrap over tracks,
compares it with Stokes-Einstein, sets the sensitivity to the processing
beside it, checks the assumptions of its error, and tests the camera model
against the short lags. Run it as a program to write the figures and the
numbers of the page:

    uv run --locked --no-dev python -m \\
        pbc.thermodynamics.experiments.brownian_motion_tracking out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from scipy.stats import chi2 as chi2_distribution

from pbc.data import SAMPLES_DIR, tracking
from pbc.data.adapters import track_series
from pbc.data.plotting import COLOURS, add_credit, label_status
from pbc.data.reference.trackpy_bulk_water import (
    FPS,
    FRAMES,
    LAGS,
    MICRONS_PER_PIXEL,
    MIN_LENGTH,
    RADIUS_SPHERE,
    SEARCH_RANGE,
    VISCOSITY,
    Analysis,
    Tracks,
    analyse,
    load,
    read_frames,
    sensitivity,
)
from pbc.experiment import Experiment, main
from pbc.thermodynamics.brownian import (
    camera_msd,
    camera_step_correlation,
    camera_walks,
    stokes_einstein,
)
from pbc.thermodynamics.diffusion import diffusion_coefficient

DATASET = "trackpy-bulk-water"
# region: choices
CHECK_D = 0.40  # µm^2/s, the diffusion coefficient of the simulated walkers
CHECK_NOISE = 0.03  # µm, the localisation error of the simulated camera
CHECK_WALKERS = 4000  # walkers per simulated case, each 40 frames long
CHECK_SEED = 20261113
REGION_BOOTSTRAP = 400  # resamples for the D of a part of the field
REGION_SEED = 20261114
CORNER = 120  # px: the top-left corner of frame 000 that the page shows
# endregion: choices
CREDIT = (
    "Frames: trackpy-examples, sample_data/bulk_water (commit 09fb307), "
    "Copyright (c) 2013-2014 trackpy-examples contributors, CC BY 3.0 "
    "https://creativecommons.org/licenses/by/3.0/."
)
PROCESSING = (
    " Tracking, drift subtraction, MSD and fits: this project's processing "
    "(NumPy, SciPy), not the provider's."
)
FRAME_TIME = 1.0 / FPS  # s
WIDTH, HEIGHT = 640, 424  # px


def load_tracks() -> Tracks:
    """The committed tracks: every located feature of frames 000-039."""
    return load(SAMPLES_DIR / DATASET)


def load_frame() -> np.ndarray:
    """The green channel of frame 000, grey levels as recorded."""
    return read_frames(SAMPLES_DIR / DATASET / FRAMES)[0]


# The camera model against simulated walks.


def camera_check(experiment: Experiment) -> dict:
    """Simulated walkers of known D, recorded by an ideal camera, by one that
    blurs over a whole frame, and by one that also adds a localisation error;
    each analysed as the lab analyses the data."""
    tau = LAGS * FRAME_TIME
    cases = (
        ("instant, no error", 0.0, 0.0),
        ("whole-frame exposure", FRAME_TIME, 0.0),
        ("whole-frame exposure and error", FRAME_TIME, CHECK_NOISE),
    )
    rng = np.random.default_rng(CHECK_SEED)
    rows, worst = [], {"z": 0.0, "d": 0.0, "rho": 0.0}
    for name, exposure, noise in cases:
        walks = camera_walks(
            CHECK_WALKERS, 40, FRAME_TIME, exposure, CHECK_D, noise, rng
        )
        per_walker = np.stack(
            [((walks[k:] - walks[:-k]) ** 2).sum(axis=2).mean(axis=0) for k in LAGS],
            axis=1,
        )
        msd = per_walker.mean(axis=0)
        error = per_walker.std(axis=0, ddof=1) / np.sqrt(CHECK_WALKERS)
        model = camera_msd(tau, CHECK_D, exposure, noise)
        slope, intercept = np.polyfit(tau, msd, 1)
        steps = np.diff(walks, axis=0)
        rho = float(np.corrcoef(steps[:-1].ravel(), steps[1:].ravel())[0, 1])
        rho_model = camera_step_correlation(FRAME_TIME, CHECK_D, exposure, noise)
        rows.append(
            (
                name,
                slope / 4,
                diffusion_coefficient(tau, msd),
                intercept,
                camera_msd(0.0, CHECK_D, 0.0, noise) - 4 * CHECK_D * exposure / 3,
                rho,
                rho_model,
            )
        )
        worst["z"] = max(worst["z"], float(np.max(np.abs(msd - model) / error)))
        worst["d"] = max(worst["d"], abs(slope / 4 / CHECK_D - 1))
        worst["rho"] = max(worst["rho"], abs(rho - rho_model))
    experiment.table(
        "camera-check",
        rows,
        columns=[
            ("camera", "", "s"),
            ("D, line with intercept", "µm^2/s", ".3f"),
            ("D, line through the origin", "µm^2/s", ".3f"),
            ("intercept, fitted", "µm^2", "+.4f"),
            ("intercept, formula", "µm^2", "+.4f"),
            ("step correlation, simulated", "", "+.3f"),
            ("step correlation, formula", "", "+.3f"),
        ],
        caption="Walkers of the random-walks lesson with D = 0.40 µm^2/s, 20 steps "
        "per frame, 4,000 walkers of 40 frames per camera, analysed at lags of 1 to "
        "10 frames: the line with an intercept recovers D, the line through the "
        "origin does not once the camera blurs.",
    )
    origin = [row[2] for row in rows]
    return {**worst, "origin-blurred": origin[1]}


# The record without a model.


def record_landmarks(tracks: Tracks) -> dict:
    """What the frames and the tracks hold before any analysis."""
    per_frame = np.bincount(tracks.frame)
    length = np.bincount(tracks.particle)
    long = length >= MIN_LENGTH
    return {
        "frames": int(per_frame.size),
        "rows": int(tracks.frame.size),
        "features-low": int(per_frame.min()),
        "features-high": int(per_frame.max()),
        "features-mean": float(per_frame.mean()),
        "tracks": int(length.size),
        "long-tracks": int(long.sum()),
        "long-features": int(length[long].sum()),
        "full-tracks": int((length == per_frame.size).sum()),
    }


def record_table(experiment: Experiment, found: dict) -> None:
    experiment.table(
        "record",
        [
            ("frames tracked (000 to 039)", found["frames"]),
            ("located features, all frames", found["rows"]),
            ("features per frame, fewest", found["features-low"]),
            ("features per frame, most", found["features-high"]),
            ("tracks", found["tracks"]),
            (f"tracks of at least {MIN_LENGTH} frames", found["long-tracks"]),
            ("tracks over all 40 frames", found["full-tracks"]),
        ],
        columns=[("quantity", "", "s"), ("count", "", ",d")],
        caption="The committed tracks CSV, this project's processing of the "
        "video, counted without a model.",
    )


# The analysis.


def corrected_positions(tracks: Tracks) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(frame, track, position in µm) of the tracks of at least MIN_LENGTH
    frames with the drift of the whole sample subtracted, the selection of
    the reference module's ``analyse``."""
    motion = tracking.drift(
        tracks.frame, tracks.particle, tracks.xy * MICRONS_PER_PIXEL
    )
    length = np.bincount(tracks.particle)
    keep = length[tracks.particle] >= MIN_LENGTH
    frame = tracks.frame[keep]
    xy = tracks.xy[keep] * MICRONS_PER_PIXEL - motion[frame]
    return frame, tracks.particle[keep], xy


def bootstrap_diffusion(
    frame: np.ndarray, particle: np.ndarray, xy: np.ndarray, seed: int, n: int
) -> tuple[float, float]:
    """D [µm^2/s] from the line through the MSD at LAGS, and the standard
    deviation of a bootstrap over the tracks."""
    sums, counts, numbers = tracking.msd_sums(frame, particle, xy, LAGS)
    tau = LAGS * FRAME_TIME
    slope = np.polyfit(tau, sums.sum(0) / counts.sum(0), 1)[0]
    rng = np.random.default_rng(seed)
    slopes = []
    for _ in range(n):
        pick = rng.integers(0, len(numbers), len(numbers))
        slopes.append(np.polyfit(tau, sums[pick].sum(0) / counts[pick].sum(0), 1)[0])
    return slope / 4, float(np.std(slopes, ddof=1) / 4)


def local_diffusion(tracks: Tracks) -> tuple[np.ndarray, np.ndarray]:
    """D [µm^2/s] from the increase of the MSD over each frame, lags 2 to 10
    (one value if the MSD were straight), and the standard deviation of a
    bootstrap over tracks."""
    sums, counts, numbers = tracking.msd_sums(*corrected_positions(tracks), LAGS)
    local = np.diff(sums.sum(0) / counts.sum(0)) / (4 * FRAME_TIME)
    rng = np.random.default_rng(REGION_SEED)
    resampled = []
    for _ in range(REGION_BOOTSTRAP):
        pick = rng.integers(0, len(numbers), len(numbers))
        msd = sums[pick].sum(0) / counts[pick].sum(0)
        resampled.append(np.diff(msd) / (4 * FRAME_TIME))
    return local, np.std(resampled, axis=0, ddof=1)


def msd_table(
    experiment: Experiment, result: Analysis, local: np.ndarray, error: np.ndarray
) -> None:
    """The MSD at each lag with its bootstrap error, the residual of the line,
    and D from the increase over each frame."""
    fitted = 4 * result.diffusion * result.tau + result.intercept
    rows = [
        (
            1e3 * t,
            m,
            e,
            m - f,
            "" if k == 0 else f"{local[k - 1]:.3f} ± {error[k - 1]:.3f}",
        )
        for k, (t, m, e, f) in enumerate(
            zip(result.tau, result.msd, result.msd_err, fitted, strict=True)
        )
    ]
    experiment.table(
        "msd",
        rows,
        columns=[
            ("lag", "ms", ".1f"),
            ("MSD", "µm^2", ".4f"),
            ("bootstrap error", "µm^2", ".4f"),
            ("residual, measured minus line", "µm^2", "+.4f"),
            ("D from the increase since the lag before", "µm^2/s", "s"),
        ],
        caption=f"The drift-corrected MSD of the {result.tracks} tracks of at least "
        f"{MIN_LENGTH} frames, with one standard deviation of a bootstrap over "
        "tracks, the residual of the straight line, and D from each increase with "
        "its bootstrap error.",
    )


def stokes_table(experiment: Experiment, result: Analysis) -> dict:
    """Stokes-Einstein for the nominal sphere at 20 and 25 °C, and the radius
    that would make it agree with the measured D."""
    rows, found = [], {}
    for celsius, eta in VISCOSITY.items():
        model = 1e12 * stokes_einstein(celsius + 273.15, eta, RADIUS_SPHERE)
        radius = 1e6 * RADIUS_SPHERE * model / result.diffusion
        rows.append(
            (
                f"{celsius:.0f}",
                1e3 * eta,
                model,
                100 * (result.diffusion / model - 1),
                radius,
            )
        )
        found[celsius] = {"model": model, "radius": radius, "viscosity": eta}
    experiment.table(
        "stokes",
        rows,
        columns=[
            ("assumed temperature", "degC", "s"),
            ("viscosity of water", "mPa s", ".4f"),
            ("Stokes-Einstein D, r = 0.5 µm", "µm^2/s", ".3f"),
            ("measured D against it", "%", "+.0f"),
            ("radius that would give the measured D", "µm", ".3f"),
        ],
        caption="kT/(6 pi eta r) for the nominal 1 µm sphere in water at two "
        "temperatures the record does not state; the viscosities are IAPWS R12-08 "
        "at 0.1 MPa.",
    )
    return found


def sensitivity_table(experiment: Experiment, result: Analysis, tracks: Tracks) -> dict:
    """D for each other choice of the processing, beside the lab's own."""
    found = sensitivity(tracks)
    experiment.table(
        "sensitivity",
        [("the lab's choices", result.diffusion)]
        + [(name, value) for name, value in found.items()],
        columns=[("processing", "", "s"), ("D", "µm^2/s", ".3f")],
        caption="The analysis repeated with one choice changed at a time: link "
        "range 3 px, mass at least 90, tracks of at least 15 frames, lags 1 to 10, "
        "drift subtracted are the lab's.",
    )
    return found


# Are the errors honest?


def region_diffusion(tracks: Tracks) -> dict:
    """D with its bootstrap error in the four quarters and the four halves of
    the field, each track placed by its mean position."""
    frame, particle, xy = corrected_positions(tracks)
    keep = np.bincount(tracks.particle)[tracks.particle] >= MIN_LENGTH
    pixels = tracks.xy[keep]
    count = np.bincount(particle)
    mean = (
        np.column_stack([np.bincount(particle, weights=pixels[:, k]) for k in (0, 1)])
        / np.maximum(count, 1)[:, None]
    )
    right = mean[particle, 0] >= WIDTH / 2
    lower = mean[particle, 1] >= HEIGHT / 2
    parts = {
        "top left": ~right & ~lower,
        "top right": right & ~lower,
        "bottom left": ~right & lower,
        "bottom right": right & lower,
        "top half": ~lower,
        "bottom half": lower,
        "left half": ~right,
        "right half": right,
    }
    return {
        name: bootstrap_diffusion(
            frame[s], particle[s], xy[s], REGION_SEED + k, REGION_BOOTSTRAP
        )
        for k, (name, s) in enumerate(parts.items())
    }


def continuations(tracks: Tracks) -> int:
    """Tracks of at least MIN_LENGTH frames that begin one or two frames after
    another such track ended, close enough to be the same particle (within the
    link range times the square root of the frames between)."""
    frame, particle, _ = corrected_positions(tracks)
    keep = np.bincount(tracks.particle)[tracks.particle] >= MIN_LENGTH
    xy = tracks.xy[keep]
    numbers = np.unique(particle)
    first = {p: frame[particle == p].min() for p in numbers}
    last = {p: frame[particle == p].max() for p in numbers}
    where = {
        (p, f): xy[(particle == p) & (frame == f)][0]
        for p in numbers
        for f in (first[p], last[p])
    }
    found = 0
    for p in numbers:
        for q in numbers:
            gap = first[q] - last[p]
            if q != p and gap in (2, 3):
                step = np.hypot(*(where[(q, first[q])] - where[(p, last[p])]))
                found += int(step <= SEARCH_RANGE * np.sqrt(gap))
    return found


def errors_table(experiment: Experiment, result: Analysis, regions: dict) -> dict:
    """The bootstrap error beside the least-squares error that assumes
    independent MSD points, and the scatter of D across the field."""
    design = np.column_stack([result.tau, np.ones_like(result.tau)])
    coef, *_ = np.linalg.lstsq(design, result.msd, rcond=None)
    residual = result.msd - design @ coef
    variance = residual @ residual / (len(residual) - 2)
    ols = float(np.sqrt(variance * np.linalg.inv(design.T @ design)[0, 0]) / 4)
    quarters = np.array(
        [
            regions[n][0]
            for n in ("top left", "top right", "bottom left", "bottom right")
        ]
    )
    quarter_errors = np.array(
        [
            regions[n][1]
            for n in ("top left", "top right", "bottom left", "bottom right")
        ]
    )
    chi2 = float(np.sum((quarters - quarters.mean()) ** 2 / quarter_errors**2))
    halves = {}
    for a, b in (("top half", "bottom half"), ("left half", "right half")):
        (da, ea), (db, eb) = regions[a], regions[b]
        halves[a] = (da - db, (da - db) / np.hypot(ea, eb))
    rows = [
        ("bootstrap over tracks (the lab's)", result.diffusion_err),
        ("least squares, MSD points independent", ols),
        ("scatter of the four quarters, sd", float(quarters.std(ddof=1))),
        ("bootstrap error of one quarter, mean", float(quarter_errors.mean())),
    ]
    experiment.table(
        "errors",
        rows,
        columns=[("error of D", "", "s"), ("value", "µm^2/s", ".4f")],
        caption="The error of D under three assumptions: tracks independent "
        "(bootstrap), MSD points independent (least squares), and D the same "
        "everywhere in the field (the quarters).",
    )
    experiment.table(
        "regions",
        [(name, d, e) for name, (d, e) in regions.items()],
        columns=[
            ("part of the field", "", "s"),
            ("D", "µm^2/s", ".3f"),
            ("bootstrap error", "µm^2/s", ".3f"),
        ],
        caption="D of the tracks whose mean position lies in each quarter and "
        "half of the field, with a bootstrap over those tracks.",
    )
    return {"ols": ols, "chi2": chi2, "halves": halves, "quarters": quarters}


# The figures.


def draw_frame(green: np.ndarray) -> Figure:
    """A corner of frame 000 as recorded: the green channel's grey levels."""
    fig, ax = plt.subplots(figsize=(4.0, 3.6), constrained_layout=True)
    image = ax.imshow(
        green[:CORNER, :CORNER],
        cmap="gray",
        extent=(-0.5, CORNER - 0.5, CORNER - 0.5, -0.5),
        interpolation="nearest",
    )
    ax.set_xlabel("x [px]")
    ax.set_ylabel("y [px]")
    ax.set_title("Frame 000, top-left corner", fontsize=10)
    bar = fig.colorbar(image, ax=ax, shrink=0.85)
    bar.set_label("green channel [grey level] (false colour)", fontsize=7)
    add_credit(fig, CREDIT + " Shown as recorded.")
    label_status(fig, "measured")
    return fig


def draw_tracks(tracks: Tracks, motion: np.ndarray) -> Figure:
    """Left: the same corner with the features of frame 000 and the tracks of
    40 frames, drift included; right: the drift of the whole sample."""
    fig, (ax, drift_ax) = plt.subplots(
        1,
        2,
        figsize=(6.8, 3.8),
        constrained_layout=True,
        gridspec_kw={"width_ratios": [1.0, 1.2]},
    )
    length = np.bincount(tracks.particle)
    status, first = "processed", True
    for number in np.unique(tracks.particle[length[tracks.particle] >= MIN_LENGTH]):
        x, y = track_series(tracks, number, 0), track_series(tracks, number, 1)
        if x.y.max() < CORNER and y.y.max() < CORNER:
            status = x.status
            ax.plot(
                x.y,
                y.y,
                color=COLOURS[0],
                lw=1.0,
                label=f"tracks over 40 frames [{status}]" if first else None,
            )
            first = False
    start = tracks.frame == 0
    inside = start & np.all(tracks.xy < CORNER, axis=1)
    ax.plot(
        *tracks.xy[inside].T,
        "o",
        mfc="none",
        mec=COLOURS[1],
        ms=7,
        mew=0.8,
        label=f"features of frame 000 [{status}]",
    )
    ax.set_xlim(-0.5, CORNER - 0.5)
    # Room below the corner for the legend: nothing is drawn there.
    ax.set_ylim(CORNER + 40, -0.5)
    ax.axhline(CORNER - 0.5, color="0.6", lw=0.6)
    ax.set_yticks(np.arange(0, CORNER + 1, 40))
    ax.set_aspect("equal")
    ax.set_xlabel("x [px]")
    ax.set_ylabel("y [px]")
    ax.set_title("Located and linked, same corner", fontsize=10)
    ax.legend(fontsize=6.5, loc="lower right")
    time = np.arange(motion.shape[0]) * FRAME_TIME
    for k, (name, style) in enumerate((("x", "-"), ("y", "--"))):
        drift_ax.plot(
            time,
            motion[:, k],
            ls=style,
            color=COLOURS[k + 2],
            label=f"drift in {name}, all linked features [{status}]",
        )
    drift_ax.set_xlabel("time from frame 000 [s]")
    drift_ax.set_ylabel("sample displacement [µm]")
    drift_ax.set_title("Drift, subtracted before the MSD", fontsize=10)
    drift_ax.legend(fontsize=6.5, loc="upper left")
    add_credit(fig, CREDIT + PROCESSING)
    label_status(fig, status)
    return fig


def _straight(ax, x_end: float, value, **kwargs) -> None:
    """A straight line from x = 0 to ``x_end``, drawn from its two ends: Agg
    rasterises a long run of collinear segments differently from one call to
    the next, and the page's figure has to be the same bytes."""
    ends = np.array([0.0, x_end])
    ax.plot(ends, value(ends), **kwargs)


def draw_msd(result: Analysis, local: tuple, models: dict, origin: float) -> Figure:
    """The MSD with its bootstrap error, the fitted line, T1's line through
    the origin, and Stokes-Einstein; the residuals below; D from each
    increase on the right."""
    fig = plt.figure(figsize=(6.8, 4.6), constrained_layout=True)
    grid = fig.add_gridspec(2, 2, height_ratios=(1.5, 1.0), width_ratios=(1.4, 1.0))
    top = fig.add_subplot(grid[0, 0])
    bottom = fig.add_subplot(grid[1, 0], sharex=top)
    right = fig.add_subplot(grid[:, 1])
    tau_ms = 1e3 * result.tau
    end = 1e3 * (result.tau[-1] + FRAME_TIME / 2)
    top.errorbar(
        tau_ms,
        result.msd,
        yerr=result.msd_err,
        ls="none",
        marker="o",
        ms=4,
        capsize=2,
        color=COLOURS[0],
        label=f"MSD, {result.tracks} tracks [processed], 1 sd bootstrap",
    )
    d, c = result.diffusion, result.intercept
    _straight(
        top,
        end,
        lambda t: 4e-3 * d * t + c,
        ls="--",
        color=COLOURS[1],
        label=f"line 4Dτ + c: D = {d:.3f} µm²/s",
    )
    _straight(
        top,
        end,
        lambda t: 4e-3 * origin * t,
        ls="-.",
        color=COLOURS[3],
        label=f"line through 0 (random-walks lesson): D = {origin:.3f} µm²/s",
    )
    for (celsius, found), style in zip(models.items(), (":", (0, (1, 3))), strict=True):
        _straight(
            top,
            end,
            lambda t, m=found["model"]: 4e-3 * m * t + c,
            ls=style,
            color=COLOURS[2],
            label=f"Stokes-Einstein {celsius:.0f} °C, same c [simulated]",
        )
    top.set_ylabel("MSD [µm²]")
    top.set_title("Drift-corrected MSD", fontsize=10)
    top.set_ylim(-0.08, 1.3)  # room for the legend above the data
    top.legend(fontsize=6, loc="upper left")
    bottom.axhline(0, color="0.4", lw=0.8)
    bottom.errorbar(
        tau_ms,
        result.msd - (4 * d * result.tau + c),
        yerr=result.msd_err,
        ls="none",
        marker="o",
        ms=4,
        capsize=2,
        color=COLOURS[0],
    )
    bottom.set_xlim(0, end)
    bottom.set_xlabel("lag time τ [ms]")
    bottom.set_ylabel("residual [µm²]")
    bottom.set_title("Residual: measured minus line", fontsize=10)
    right.errorbar(
        tau_ms[1:],
        local[0],
        yerr=local[1],
        ls="none",
        marker="s",
        ms=4,
        capsize=2,
        color=COLOURS[0],
        label="from each increase [processed], 1 sd bootstrap",
    )
    right.axhline(d, ls="--", color=COLOURS[1], label="line 4Dτ + c")
    for (celsius, found), style in zip(models.items(), (":", (0, (1, 3))), strict=True):
        right.axhline(
            found["model"],
            ls=style,
            color=COLOURS[2],
            label=f"Stokes-Einstein {celsius:.0f} °C [simulated]",
        )
    right.set_ylim(0.3, 0.52)
    right.set_xlabel("lag time τ [ms]")
    right.set_ylabel("D [µm²/s]")
    right.set_title("D from each increase", fontsize=10)
    right.legend(fontsize=6, loc="lower right")
    add_credit(fig, CREDIT + PROCESSING)
    label_status(fig, "processed")
    return fig


def draw_steps(result: Analysis) -> Figure:
    """The one-frame steps after the drift against the Gaussian of their
    measured variance, on a log scale."""
    fig, ax = plt.subplots(figsize=(4.6, 3.2), constrained_layout=True)
    values = result.steps.ravel()
    sigma = float(np.sqrt(np.mean(values**2)))
    reach = 1.1 * SEARCH_RANGE * MICRONS_PER_PIXEL
    edges = np.linspace(-reach, reach, 67)
    ax.hist(
        values,
        bins=edges,
        density=True,
        color=COLOURS[0],
        alpha=0.6,
        label=f"x and y steps, {values.size:,} [processed]",
    )
    grid = np.linspace(-reach, reach, 201)
    ax.plot(
        grid,
        np.exp(-0.5 * (grid / sigma) ** 2) / (sigma * np.sqrt(2 * np.pi)),
        "--",
        color=COLOURS[1],
        label=f"Gaussian of the same rms, {sigma:.3f} µm",
    )
    ax.set_yscale("log")
    ax.set_ylim(1e-3, 10)
    ax.set_xlabel("displacement in one frame [µm]")
    ax.set_ylabel("probability density [1/µm]")
    ax.set_title("One-frame steps after the drift (log scale)", fontsize=10)
    ax.legend(fontsize=6.5, loc="upper left")
    add_credit(fig, CREDIT + PROCESSING)
    label_status(fig, "processed")
    return fig


# The exercises.


def spreading_exercise() -> None:
    """Exercise 1: how long a sphere takes to move its own diameter, and how
    far it gets in an hour, in the plane of the camera."""
    d = 0.403  # µm^2/s, the lab's
    print(f"time to move 1 µm (rms, in the plane): {1.0**2 / (4 * d):.2f} s")
    print(f"rms distance in one hour: {np.sqrt(4 * d * 3600):.0f} µm")


def exposure_exercise() -> None:
    """Exercise 2: the exposure that blur alone would need for the measured
    intercept."""
    d, c = 0.403, -0.0355  # µm^2/s and µm^2, the lab's
    exposure = -3 * c / (4 * d)
    print(f"exposure for c by blur alone: {1e3 * exposure:.0f} ms")
    print(f"one frame lasts: {1e3 * FRAME_TIME:.1f} ms")


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    tracks = load_tracks()

    check = camera_check(experiment)
    experiment.number("check-z", check["z"], ".1f")
    experiment.number("check-d", 100 * check["d"], ".1f")
    experiment.number("check-rho", check["rho"], ".3f")
    experiment.number("check-origin", check["origin-blurred"], ".3f")
    experiment.number("check-true-d", CHECK_D, ".2f")

    found = record_landmarks(tracks)
    record_table(experiment, found)
    experiment.number("features-low", found["features-low"])
    experiment.number("features-high", found["features-high"])
    experiment.number("tracks", found["tracks"], ",d")
    experiment.number("long-tracks", found["long-tracks"])
    experiment.number("long-features", found["long-features"], ",d")

    result = analyse(tracks)
    total = result.drift[-1]
    duration = (result.drift.shape[0] - 1) * FRAME_TIME
    experiment.number("drift-x", total[0], ".2f")
    experiment.number("drift-y", total[1], ".2f")
    experiment.number("drift-speed", np.hypot(*total) / duration, ".2f")
    experiment.number("duration", duration, ".2f")

    local, local_err = local_diffusion(tracks)
    msd_table(experiment, result, local, local_err)
    origin = diffusion_coefficient(result.tau, result.msd)
    experiment.number("d", result.diffusion, ".3f")
    experiment.number("d-err", result.diffusion_err, ".3f")
    experiment.number("d-rel", 100 * result.diffusion_err / result.diffusion, ".1f")
    experiment.number("intercept", result.intercept, ".3f")
    experiment.number("intercept-err", result.intercept_err, ".3f")
    experiment.number("d-origin", origin, ".3f")
    experiment.number("local-first", local[0], ".3f")
    experiment.number("local-first-err", local_err[0], ".3f")
    experiment.number("local-late", local[4:].mean(), ".3f")

    models = stokes_table(experiment, result)
    experiment.number("se-20", models[20.0]["model"], ".3f")
    experiment.number("se-25", models[25.0]["model"], ".3f")
    experiment.number(
        "below-20", 100 * (1 - result.diffusion / models[20.0]["model"]), ".0f"
    )
    experiment.number(
        "below-25", 100 * (1 - result.diffusion / models[25.0]["model"]), ".0f"
    )
    experiment.number("radius-20", models[20.0]["radius"], ".2f")
    experiment.number("radius-25", models[25.0]["radius"], ".2f")
    experiment.number(
        "eta-per-kelvin",
        100 * np.log(VISCOSITY[20.0] / VISCOSITY[25.0]) / 5.0,
        ".1f",
    )

    variants = sensitivity_table(experiment, result, tracks)
    kept = {k: v for k, v in variants.items() if k != "no drift subtracted"}
    experiment.number("variants-low", min(kept.values()), ".3f")
    experiment.number("variants-high", max(kept.values()), ".3f")
    experiment.number("no-drift", variants["no drift subtracted"], ".3f")
    half_range = (max(kept.values()) - min(kept.values())) / 2
    experiment.number("range-ratio", half_range / result.diffusion_err, ".1f")
    experiment.number(
        "no-drift-rel",
        100 * (variants["no drift subtracted"] / result.diffusion - 1),
        ".0f",
    )

    regions = region_diffusion(tracks)
    honest = errors_table(experiment, result, regions)
    experiment.number("ols", honest["ols"], ".3f")
    experiment.number("boot-ratio", result.diffusion_err / honest["ols"], ".1f")
    experiment.number("chi2", honest["chi2"], ".1f")
    experiment.number("chi2-p", chi2_distribution.sf(honest["chi2"], 3), ".2f")
    experiment.number("quarters-low", honest["quarters"].min(), ".3f")
    experiment.number("quarters-high", honest["quarters"].max(), ".3f")
    gap, sigmas = honest["halves"]["top half"]
    experiment.number("top-bottom", gap, ".3f")
    experiment.number("top-bottom-sigmas", sigmas, ".1f")
    experiment.number("continuations", continuations(tracks))

    # The camera model against the short lags: with the measured intercept,
    # blur and noise fix the covariance of successive steps.
    variance = result.msd[0] / 2  # per coordinate
    predicted = -result.intercept / 4 / variance
    experiment.number("rho-measured", result.step_correlation, "+.2f")
    experiment.number("rho-predicted", predicted, "+.2f")
    experiment.number("blur-floor", -4 * result.diffusion * FRAME_TIME / 3, ".3f")
    experiment.number("kurtosis", result.excess_kurtosis, ".1f")
    experiment.number("spread", result.track_spread, ".2f")
    experiment.number("spread-expected", result.track_spread_expected, ".2f")

    experiment.figure("fig-frame", partial(draw_frame, load_frame()))
    experiment.figure("fig-tracks", partial(draw_tracks, tracks, result.drift))
    experiment.figure(
        "fig-msd", partial(draw_msd, result, (local, local_err), models, origin)
    )
    experiment.figure("fig-steps", partial(draw_steps, result))

    with experiment.capture("spreading-exercise"):
        spreading_exercise()
    with experiment.capture("exposure-exercise"):
        exposure_exercise()
    return experiment


if __name__ == "__main__":
    main(run)
