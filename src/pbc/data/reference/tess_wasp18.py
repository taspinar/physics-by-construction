"""TESS WASP-18, sector 29: the measured light curve and a fitted transit model.

Status of the figure: *processed*. The SPOC pipeline's PDCSAP flux is a
calibrated observation, corrected by the pipeline for instrumental
systematics; this module keeps the cadences of quality 0, divides each
transit by a parabola fitted to the flux just outside it (the star's
ellipsoidal variation curves the baseline), and folds the transits on the
ephemeris that it measures from the data. The fitted model is
drawn apart from the measurement, as a model, with its residuals.

The model is the AST7 transit (``pbc.astrophysics.transit``): a dark disk of
radius p in stellar radii crossing a star darkened towards the limb by the
quadratic law, on a circular orbit of radius a and impact parameter b. Its
flux is the brightness of the star summed over thin rings, each ring's share
of the planet's disk from the closed-form overlap of two disks
(``overlap_area``), and averaged over the 2-minute exposure.

The uncertainties come from the pipeline's PDCSAP_FLUX_ERR, propagated through
the normalisation; the reduced chi-square of the fit and the scatter of the
per-transit mid-times about the linear ephemeris test whether these errors
describe the scatter. The pipeline's systematics and crowding corrections
(CROWDSAP) are taken as released, and the star's own variability is followed
only by the parabola of each window; the dossier says what follows from that.
"""

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from pbc.astrophysics.transit import durations, overlap_area
from pbc.data.fit import FitResult, fit_curve
from pbc.data.plotting import COLOURS, add_credit, label_status

FILE = "wasp18_s0029_lc.csv"
FIELDS = ("time", "pdcsap_flux", "pdcsap_flux_err", "quality")
UNITS = {
    "time": "BJD - 2457000, days",
    "pdcsap_flux": "e-/s",
    "pdcsap_flux_err": "e-/s",
    "quality": "none",
}
CADENCE = 120.0  # s, TIMEDEL of the file (2-minute cadence)
EXPOSURE = 120.0 / 86400  # d, one cadence, over which the model is averaged
SUBSAMPLES = 5  # points per exposure in that average (1.6 ppm from the limit)
RINGS = 200  # rings of the star in the limb-darkened flux (1.8 ppm from the limit)
DEPTH_CUT = 0.005  # a cadence this far below its neighbourhood is in a transit
HALF_WINDOW = 0.16  # d, flux used around each mid-transit (T14 is about 0.09 d)
HALF_MASK = 0.065  # d, excluded from the baseline around each mid-transit
DEGREE = 2  # of the baseline polynomial: the star's ellipsoidal variation curves it
# The choices compared by ``sensitivity``: (half window [d], degree).
VARIANTS = ((0.12, 2), (0.20, 2), (0.16, 1))
SHAPE = ("p", "a", "b", "u1", "u2")
G = 6.67430e-11  # m3 kg-1 s-2 (CODATA 2018)


@dataclass(frozen=True)
class LightCurve:
    time: np.ndarray  # BJD - 2457000 [d]
    flux: np.ndarray  # PDCSAP [e-/s]
    flux_err: np.ndarray  # PDCSAP_FLUX_ERR [e-/s]
    quality: np.ndarray  # SPOC quality flags, 0 for a good cadence
    header: tuple[str, ...]  # the comment lines of the CSV


def read_light_curve(path: Path) -> LightCurve:
    """Read the four-column CSV written by ``tools/datasets/tess_lc_to_csv.py``."""
    lines = Path(path).read_text(encoding="ascii").splitlines()
    header = tuple(line for line in lines if line.startswith("#"))
    names = next(line for line in lines if not line.startswith("#")).split(",")
    if tuple(names) != FIELDS:
        raise ValueError(f"{path}: columns {names}, expected {FIELDS}")
    # skiprows counts the comment lines too: skip them and the column names
    table = np.loadtxt(path, delimiter=",", skiprows=len(header) + 1, ndmin=2)
    if table.shape[1] != len(FIELDS):
        raise ValueError(f"{path}: rows of {table.shape[1]} values")
    quality = table[:, 3]
    if not np.all(quality == np.round(quality)):
        raise ValueError(f"{path}: a quality flag that is not an integer")
    return LightCurve(
        table[:, 0], table[:, 1], table[:, 2], quality.astype(int), header
    )


def load(data_dir: Path) -> LightCurve:
    return read_light_curve(Path(data_dir) / FILE)


def good(lc: LightCurve) -> np.ndarray:
    """Cadences with no quality flag and a finite time, flux, and error."""
    return (
        (lc.quality == 0)
        & np.isfinite(lc.time)
        & np.isfinite(lc.flux)
        & np.isfinite(lc.flux_err)
    )


# The model.


def limb_flux(d: np.ndarray, p: float, u1: float, u2: float) -> np.ndarray:
    """Flux relative to the unocculted star with the planet at the projected
    separation ``d`` (stellar radii), for the quadratic law
    I(r) = 1 - u1 (1 - mu) - u2 (1 - mu)^2, mu = sqrt(1 - r^2).

    The star is cut into ``RINGS`` rings of equal width; the planet hides of
    the ring between r1 and r2 the area A(r2) - A(r1), where A(r) is the
    overlap of the disk of radius r with the planet's (``overlap_area``
    scaled to r), and the ring shines with I at its middle radius. A uniform
    star (u1 = u2 = 0) gives the closed form of AST7 exactly."""
    d = np.atleast_1d(np.asarray(d, dtype=float))
    edges = np.linspace(0.0, 1.0, RINGS + 1)
    middle = 0.5 * (edges[1:] + edges[:-1])
    mu = np.sqrt(1.0 - middle**2)
    intensity = 1.0 - u1 * (1.0 - mu) - u2 * (1.0 - mu) ** 2
    near = d < 1.0 + p
    hidden = np.zeros(d.shape)
    if near.any():
        dn = np.maximum(d[near], 1e-9)
        previous = np.zeros(dn.shape)
        for r, shine in zip(edges[1:], intensity, strict=True):
            covered = r**2 * overlap_area(dn / r, p / r)
            hidden[near] += shine * (covered - previous)
            previous = covered
    total = np.pi * (1.0 - u1 / 3.0 - u2 / 6.0)
    return 1.0 - hidden / total


def separation(time: np.ndarray, t0: float, period: float, a: float, b: float):
    """Projected separation [stellar radii] on a circular orbit, with the
    planet in front of the star near t0 (and behind it, d = inf, else)."""
    phase = 2 * np.pi * (np.asarray(time, dtype=float) - t0) / period
    cos_i = b / a
    d = a * np.sqrt(np.sin(phase) ** 2 + (cos_i * np.cos(phase)) ** 2)
    return np.where(np.cos(phase) > 0, d, np.inf)


def model_flux(time: np.ndarray, t0, period, p, a, b, u1, u2) -> np.ndarray:
    """The transit model averaged over the 2-minute exposure."""
    time = np.asarray(time, dtype=float)
    offsets = (np.arange(SUBSAMPLES) + 0.5) / SUBSAMPLES - 0.5
    fine = time[:, None] + EXPOSURE * offsets[None, :]
    d = separation(fine.ravel(), t0, period, a, b)
    return limb_flux(d, p, u1, u2).reshape(fine.shape).mean(axis=1)


# The steps from the light curve to the fit.


def transit_events(lc: LightCurve) -> np.ndarray:
    """Mid-times [BJD - 2457000] of the dips found in the good cadences: runs
    of cadences more than DEPTH_CUT below the running median of 0.5 d, each
    centred on the mean time of its run. No ephemeris is assumed."""
    ok = good(lc)
    t, f = lc.time[ok], lc.flux[ok]
    reference = np.array(
        [np.median(f[np.abs(t - ti) < 0.25]) for ti in t]
    )  # running median over 0.5 d
    low = f < (1 - DEPTH_CUT) * reference
    events, run = [], []
    for k in np.flatnonzero(low):
        if run and t[k] - t[run[-1]] > 0.02:
            events.append(run)
            run = []
        run.append(k)
    if run:
        events.append(run)
    return np.array([t[r].mean() for r in events if len(r) >= 10])


def linear_ephemeris(times: np.ndarray, first_guess: float | None = None):
    """Period and reference epoch from mid-times by a straight line in the
    transit number; ``first_guess`` is the spacing that numbers them (the
    median spacing of neighbours by default)."""
    times = np.sort(np.asarray(times, dtype=float))
    step = np.median(np.diff(times)) if first_guess is None else first_guess
    epoch = np.round((times - times[0]) / step)
    slope, intercept = np.polyfit(epoch, times, 1)
    middle = np.round(np.median(epoch))
    return intercept + slope * middle, slope


@dataclass(frozen=True)
class Folded:
    time: np.ndarray  # BJD - 2457000 [d]
    flux: np.ndarray  # normalised to the baseline of its transit
    error: np.ndarray  # PDCSAP_FLUX_ERR over the same baseline
    epoch: np.ndarray  # transit number relative to t0
    epochs: tuple[int, ...]  # the transits kept, complete and with a baseline


def normalise(
    lc: LightCurve,
    t0: float,
    period: float,
    half_window: float = HALF_WINDOW,
    degree: int = DEGREE,
) -> Folded:
    """Every transit whose window of +-``half_window`` is covered by good
    cadences on both sides, divided by a polynomial of ``degree`` in time
    fitted to the flux of that window outside +-HALF_MASK of its mid-time.

    The degree is 2 by default: WASP-18 b raises tides on its star, whose
    brightness then varies at half the orbital period, at its lowest near
    mid-transit, so the flux around a transit is curved and a straight line
    through both sides sits above it."""
    ok = good(lc)
    t, f, e = lc.time[ok], lc.flux[ok], lc.flux_err[ok]
    epoch = np.round((t - t0) / period).astype(int)
    offset = t - (t0 + epoch * period)
    keep_t, keep_f, keep_e, keep_n, kept = [], [], [], [], []
    for n in np.unique(epoch):
        window = (epoch == n) & (np.abs(offset) < half_window)
        before = window & (offset < -HALF_MASK)
        after = window & (offset > HALF_MASK)
        inside = window & (np.abs(offset) <= HALF_MASK)
        # complete: a baseline on both sides and no gap in the transit
        if before.sum() < 20 or after.sum() < 20:
            continue
        if inside.sum() < 0.95 * 2 * HALF_MASK * 86400 / CADENCE:
            continue
        base = before | after
        line = np.polyfit(offset[base], f[base], degree)
        level = np.polyval(line, offset[window])
        keep_t.append(t[window])
        keep_f.append(f[window] / level)
        keep_e.append(e[window] / level)
        keep_n.append(np.full(window.sum(), n))
        kept.append(int(n))
    return Folded(
        np.concatenate(keep_t),
        np.concatenate(keep_f),
        np.concatenate(keep_e),
        np.concatenate(keep_n),
        tuple(kept),
    )


def fit_shape(folded: Folded, t0: float, period: float) -> FitResult:
    """Fit p, a, b, u1, u2 to the normalised transits on a fixed ephemeris,
    weighted by the pipeline's errors (an absolute covariance; the reduced
    chi-square tests those errors).

    The ephemeris is fitted apart, from the mid-times (``fit_ephemeris``):
    in a joint fit the period is known about 10^5 times better, relatively,
    than u2, and the identifiability test of ``fit_curve``, which compares
    parameters scaled by their size, would report that contrast as a
    degeneracy. The covariance of the joint fit of all seven, computed for
    the dossier from the Jacobian at the final values, gives correlations of
    at most 0.001 in size between the ephemeris and the shape, so fixing one
    while fitting the other loses nothing."""

    def model(time, *shape):
        return model_flux(time, t0, period, *shape)

    return fit_curve(
        model,
        folded.time,
        folded.flux,
        [0.1, 3.5, 0.3, 0.3, 0.2],
        sigma=folded.error,
        names=SHAPE,
        bounds=([0.01, 1.5, 0.0, -1.0, -1.0], [0.5, 10.0, 1.0, 2.0, 2.0]),
    )


def mid_times(
    folded: Folded, t0: float, period: float, shape: FitResult
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Mid-time of each kept transit, its shape fixed at ``shape``: transit
    numbers, times [BJD - 2457000], and their standard errors [d] from the
    pipeline's errors."""
    epochs, times, errors = [], [], []
    for n in folded.epochs:
        one = folded.epoch == n

        def model(time, tc):
            return model_flux(time, tc, period, *shape.params)

        single = fit_curve(
            model,
            folded.time[one],
            folded.flux[one],
            [t0 + n * period],
            sigma=folded.error[one],
            names=("tc",),
        )
        epochs.append(n)
        times.append(single.value("tc"))
        errors.append(single.stderr[0])
    return np.array(epochs), np.array(times), np.array(errors)


@dataclass(frozen=True)
class Ephemeris:
    t0: float  # mid-time of transit number 0 [BJD - 2457000]
    period: float  # [d]
    t0_err: float  # standard errors from the mid-times' errors [d]
    period_err: float
    chi2: float  # of the mid-times about the line
    dof: int


def fit_ephemeris(
    epochs: np.ndarray, times: np.ndarray, errors: np.ndarray
) -> Ephemeris:
    """Weighted straight line t = t0 + n P through the mid-times."""
    design = np.column_stack([np.ones(epochs.size), epochs.astype(float)])
    weights = 1.0 / errors**2
    normal = design.T @ (design * weights[:, None])
    covariance = np.linalg.inv(normal)
    t0, period = covariance @ (design.T @ (weights * times))
    chi2 = float(np.sum(weights * (times - t0 - period * epochs) ** 2))
    return Ephemeris(
        float(t0),
        float(period),
        float(np.sqrt(covariance[0, 0])),
        float(np.sqrt(covariance[1, 1])),
        chi2,
        int(epochs.size - 2),
    )


@dataclass(frozen=True)
class Analysis:
    folded: Folded
    shape: FitResult
    ephemeris: Ephemeris
    epochs: np.ndarray  # transit numbers of the mid-times
    times: np.ndarray  # mid-times [BJD - 2457000]
    errors: np.ndarray  # their standard errors [d]

    def params(self) -> tuple[float, ...]:
        """t0, P, p, a, b, u1, u2 as ``model_flux`` takes them."""
        return (self.ephemeris.t0, self.ephemeris.period, *self.shape.params)


def analyse(
    lc: LightCurve, half_window: float = HALF_WINDOW, degree: int = DEGREE
) -> Analysis:
    """The whole chain. The dips give a first ephemeris; the transits are
    normalised on it and their shape fitted; the mid-times of the single
    transits give the ephemeris; the normalisation and the two fits are then
    repeated once on that ephemeris."""
    t0, period = linear_ephemeris(transit_events(lc))
    for _ in range(2):
        folded = normalise(lc, t0, period, half_window, degree)
        shape = fit_shape(folded, t0, period)
        epochs, times, errors = mid_times(folded, t0, period, shape)
        ephemeris = fit_ephemeris(epochs, times, errors)
        t0, period = ephemeris.t0, ephemeris.period
    return Analysis(folded, shape, ephemeris, epochs, times, errors)


def sensitivity(lc: LightCurve) -> dict[tuple[float, int], Analysis]:
    """The analysis with the other choices of window and baseline in
    VARIANTS: a sensitivity analysis of the normalisation, not an
    uncertainty of the record."""
    return {(w, k): analyse(lc, w, k) for w, k in VARIANTS}


def geometry(analysis: Analysis) -> dict[str, float]:
    """Quantities derived from the fitted values: inclination [deg], depth at
    mid-transit [1], T14 and T23 [h], ingress [min], and the mean stellar
    density [kg/m3] from Kepler's third law, 3 pi a^3 / (G P^2) (the planet's
    mass neglected)."""
    period = analysis.ephemeris.period
    p, a, b, u1, u2 = analysis.shape.params
    inclination = np.arccos(b / a)
    t14, t23 = durations(period, a, inclination, p)
    depth = 1.0 - limb_flux(np.array([b]), p, u1, u2)[0]
    seconds = period * 86400
    return {
        "inclination": float(np.degrees(inclination)),
        "depth": float(depth),
        "t14": float(t14 * 24),
        "t23": float(t23 * 24),
        "ingress": float((t14 - t23) / 2 * 24 * 60),
        "density": float(3 * np.pi * a**3 / (G * seconds**2)),
    }


def o_minus_c(analysis: Analysis) -> np.ndarray:
    """Observed minus computed mid-time of each transit [min]."""
    eph = analysis.ephemeris
    return (analysis.times - eph.t0 - eph.period * analysis.epochs) * 1440


def residuals(analysis: Analysis) -> np.ndarray:
    """Measured minus fitted normalised flux at every kept cadence."""
    folded = analysis.folded
    return folded.flux - model_flux(folded.time, *analysis.params())


def make_figure(data_dir: Path) -> plt.Figure:
    lc = load(data_dir)
    analysis = analyse(lc)
    folded, result = analysis.folded, analysis.shape
    shape = geometry(analysis)
    t0, period = analysis.ephemeris.t0, analysis.ephemeris.period
    phase_h = (folded.time - (t0 + folded.epoch * period)) * 24
    ok = good(lc)

    fig = plt.figure(figsize=(10, 9), constrained_layout=True)
    grid = fig.add_gridspec(3, 2, height_ratios=(1.0, 1.6, 0.8))
    ax_all = fig.add_subplot(grid[0, :])
    ax_fold = fig.add_subplot(grid[1, 0])
    ax_res = fig.add_subplot(grid[2, 0], sharex=ax_fold)
    ax_oc = fig.add_subplot(grid[1:, 1])

    median = np.median(lc.flux[ok])
    ax_all.plot(
        lc.time[ok],
        lc.flux[ok] / median,
        ls="none",
        marker=".",
        ms=1.5,
        color=COLOURS[0],
        label="PDCSAP flux, quality 0, over its median",
    )
    marks = t0 + np.array(folded.epochs) * period
    ax_all.plot(
        marks,
        np.full(marks.size, 1.006),
        ls="none",
        marker="v",
        ms=4,
        color=COLOURS[1],
        label=f"{len(folded.epochs)} complete transits used",
    )
    ax_all.set_xlabel("time [BJD - 2457000, d]")
    ax_all.set_ylabel("relative flux [1]")
    ax_all.set_title(
        "Processed: TESS sector 29, 2-minute cadence; gaps: no time or no PDCSAP"
        " value, or a quality flag",
        fontsize=10,
    )
    ax_all.set_ylim(0.979, 1.008)
    ax_all.legend(fontsize=8, loc="lower center", ncols=2)

    order = np.argsort(phase_h)
    dense_h = np.linspace(-HALF_WINDOW * 24, HALF_WINDOW * 24, 800)
    curve = model_flux(t0 + dense_h / 24, *analysis.params())
    bins = np.arange(-HALF_WINDOW * 24, HALF_WINDOW * 24 + 1e-9, 0.1)
    index = np.digitize(phase_h, bins)
    centres, means, sems = [], [], []
    for k in range(1, bins.size):
        inside = index == k
        if inside.sum() > 5:
            centres.append(phase_h[inside].mean())
            means.append(folded.flux[inside].mean())
            sems.append(folded.flux[inside].std(ddof=1) / np.sqrt(inside.sum()))
    ax_fold.plot(
        phase_h[order],
        folded.flux[order],
        ls="none",
        marker=".",
        ms=1.5,
        color="0.65",
        label=(
            "measured, normalised cadences (pipeline error "
            f"{np.median(folded.error) * 1e6:.0f} ppm each, not drawn)"
        ),
    )
    ax_fold.errorbar(
        centres,
        means,
        yerr=sems,
        ls="none",
        marker="o",
        ms=3,
        color=COLOURS[0],
        label="measured, 6-minute bins (standard error of the mean)",
    )
    ax_fold.plot(
        dense_h,
        curve,
        color=COLOURS[1],
        ls="--",
        lw=1.4,
        label=(
            f"model fit: p = {result.value('p'):.4f}, a = {result.value('a'):.3f}, "
            f"b = {result.value('b'):.3f}"
        ),
    )
    ax_fold.axvspan(
        -HALF_MASK * 24,
        HALF_MASK * 24,
        color="0.92",
        zorder=0,
        label="excluded from the baseline parabola",
    )
    ax_fold.set_ylim(0.979, 1.003)
    ax_fold.set_ylabel("normalised flux [1]")
    ax_fold.set_title(
        f"Processed: folded on P = {period:.5f} d; depth {shape['depth'] * 1e6:.0f}"
        f" ppm, T14 = {shape['t14']:.3f} h",
        fontsize=10,
    )
    ax_fold.legend(fontsize=7, loc="lower center")
    ax_fold.tick_params(labelbottom=False)

    res = residuals(analysis) * 1e6
    ax_res.plot(phase_h, res, ls="none", marker=".", ms=1.5, color="0.65")
    rms = []
    for k in range(1, bins.size):
        inside = index == k
        rms.append(res[inside].mean() if inside.sum() > 5 else np.nan)
    ax_res.plot(
        0.5 * (bins[1:] + bins[:-1]),
        rms,
        color=COLOURS[2],
        marker="o",
        ms=3,
        label="6-minute bins",
    )
    ax_res.axhline(0, color="0.3", lw=0.8)
    ax_res.set_ylim(-3000, 3000)
    ax_res.set_xlabel("time from mid-transit [h]")
    ax_res.set_ylabel("residual [ppm]")
    ax_res.set_title(
        f"Residuals: reduced chi-square {result.reduced_chi2:.2f}", fontsize=10
    )
    ax_res.legend(fontsize=7, loc="lower left")

    epochs, errors = analysis.epochs, analysis.errors
    ax_oc.errorbar(
        epochs,
        o_minus_c(analysis),
        yerr=errors * 1440,
        ls="none",
        marker="o",
        ms=3.5,
        color=COLOURS[0],
        label="each transit, shape fixed (one standard error)",
    )
    ax_oc.axhline(0, color=COLOURS[1], ls="--", lw=1.2, label="the fitted ephemeris")
    ax_oc.set_xlabel("transit number from t0 [1]")
    ax_oc.set_ylabel("observed minus computed mid-time [min]")
    eph = analysis.ephemeris
    ax_oc.set_title(
        f"Mid-times: chi-square {eph.chi2:.1f} for {eph.dof} degrees of freedom",
        fontsize=10,
    )
    ax_oc.legend(fontsize=8, loc="upper left")

    add_credit(
        fig,
        "Data: TESS mission, SPOC 2-minute light curve of TIC 100100827 (WASP-18), "
        "sector 29, file tess2020238165205-s0029-0000000100100827-0193-s_lc.fits, "
        "obtained from MAST at STScI; public domain (MAST data use policy). "
        "Columns TIME, PDCSAP_FLUX, PDCSAP_FLUX_ERR, QUALITY converted to CSV "
        "unchanged. "
        "Normalisation, folding, fit and residuals: this figure's code "
        "(pbc.data.reference.tess_wasp18), not part of the record.",
    )
    label_status(fig, "processed")
    return fig
