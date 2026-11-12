"""The experiment of the lesson "Exoplanet light curves lab".

The transit model of the exoplanet transit lesson (``pbc.astrophysics.transit``)
against the TESS light curve of WASP-18 in sector 29 (the committed sample of
the card ``tess-exoplanet-light-curves``): the limb-darkened ring model
checked against the lesson's closed forms and grid, the cadences the quality
flags and the missing values remove, one transit divided by its baseline,
the analysis of the dossier (``pbc.data.reference.tess_wasp18``: the dips,
the normalisation, the shape fit, the mid-times, the ephemeris), a uniform
star fitted to the same cadences, the depth, durations, impact parameter,
and radius ratio with standard errors propagated through the covariance of
the fit, the mid-times against their errors, the sensitivity to the
normalisation, and the stellar density against the catalogue values of the
file. Run it as a program to write the figures and the numbers of the page:

    uv run --locked --no-dev python -m \\
        pbc.astrophysics.experiments.exoplanet_light_curves out
"""

from collections.abc import Callable
from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.astrophysics.transit import (
    central_depth,
    durations,
    grid_flux,
    quadratic_limb,
    total_flux,
    uniform_flux,
)
from pbc.data import SAMPLES_DIR
from pbc.data.adapters import light_curve_series
from pbc.data.fit import FitResult, fit_curve
from pbc.data.plotting import COLOURS, add_credit, label_status
from pbc.data.reference import tess_wasp18 as reference
from pbc.data.reference.tess_wasp18 import Analysis, LightCurve
from pbc.experiment import Experiment, main

DATASET = "tess-exoplanet-light-curves"
# region: tic
# Catalogue values of the star in the header of the FITS file (TIC 100100827,
# keywords LOGG and RADIUS), given there without an uncertainty.
TIC_LOGG = 4.25879  # log10 of the surface gravity in cgs units
TIC_RADIUS = 1.34658  # solar radii
R_SUN = 6.957e8  # m, the nominal solar radius (IAU 2015)
R_JUPITER = 7.1492e7  # m, Jupiter's nominal equatorial radius (IAU 2015)
# endregion: tic
BIN = 0.1  # h, the width of the bins of the folded figure (6 minutes)
PHASE_BIN = 0.02  # the width in orbital phase of the bins of the phase curve
CREDIT = (
    "Data: TESS mission, SPOC 2-minute light curve of TIC 100100827 (WASP-18), "
    "sector 29, file tess2020238165205-s0029-0000000100100827-0193-s_lc.fits, "
    "obtained from the MAST data archive at STScI; funding for TESS by the NASA "
    "Explorer Program; public domain (MAST data use policy). Columns converted to "
    "CSV unchanged. Cleaning, normalisation, folding, fits and residuals: this "
    "lesson's code, not part of the record."
)
GEOMETRY = (
    # name, unit, scale from the value of ``derived`` to the unit shown
    ("radius ratio p = Rp/R*", "1", 1.0),
    ("impact parameter b", "stellar radii", 1.0),
    ("orbital radius a/R*", "stellar radii", 1.0),
    ("depth at mid-transit", "ppm", 1e6),
    ("total duration T14", "h", 1.0),
    ("full duration T23", "h", 1.0),
    ("ingress (T14 - T23)/2", "min", 1.0),
    ("inclination arccos(b/a)", "deg", 1.0),
    ("mean stellar density", "kg/m3", 1.0),
)


# The model before the data.


def check_against_ast7(experiment: Experiment) -> dict:
    """The ring model of the fit against the exoplanet transit lesson: the
    closed-form flux of a uniform star, the closed-form depth of a central
    transit of a limb-darkened star, and the grid count over the planet's
    disk; record the table and return the largest gap of each."""
    p, u1, u2 = 0.1, 0.3, 0.2  # a planet and a limb of about WASP-18's size
    d = np.linspace(0.0, 1.2, 25)
    uniform_gap = np.abs(reference.limb_flux(d, p, 0.0, 0.0) - uniform_flux(d, p))
    centre = 1.0 - reference.limb_flux(np.array([0.0]), p, u1, u2)[0]
    depth_gap = abs(centre / central_depth(p, u1, u2) - 1)
    grid = grid_flux(d, p, quadratic_limb(u1, u2), cells=400, full=total_flux(u1, u2))
    grid_gap = np.abs(reference.limb_flux(d, p, u1, u2) - grid)
    gaps = {
        "uniform": float(uniform_gap.max()),
        "depth": float(depth_gap),
        "grid": float(grid_gap.max()),
    }
    experiment.table(
        "model-check",
        [
            (
                "uniform star, 25 separations from 0 to 1.2",
                "closed-form overlap of two disks",
                "below 1e-12" if gaps["uniform"] < 1e-12 else f"{gaps['uniform']:.0e}",
                "flux [1]",
            ),
            (
                "limb-darkened star, central transit",
                "closed-form depth",
                f"{gaps['depth']:.0e}",
                "relative",
            ),
            (
                "limb-darkened star, 25 separations",
                "grid of 400 x 400 cells over the planet",
                f"{gaps['grid']:.0e}",
                "flux [1]",
            ),
        ],
        columns=[
            ("case", "", "s"),
            ("against the transit lesson's", "", "s"),
            ("largest difference", "", "s"),
            ("measured as", "", "s"),
        ],
        caption="The model of the fit, the star summed over 200 rings, against "
        "the closed forms and the grid of the exoplanet transit lesson, for "
        "p = 0.1 and u1 = 0.3, u2 = 0.2.",
    )
    return gaps


# The data.


def load_light_curve() -> LightCurve:
    """The committed sample, every cadence of the file."""
    return reference.load(SAMPLES_DIR / DATASET)


def cleaning(experiment: Experiment, lc: LightCurve) -> dict:
    """What the missing values and the quality flags remove; record the
    table and return the counts."""
    no_time = ~np.isfinite(lc.time)
    no_flux = ~np.isfinite(lc.flux)
    flagged = lc.quality != 0
    good = reference.good(lc)
    counts = {
        "total": int(lc.time.size),
        "no-time": int(no_time.sum()),
        "no-flux": int(no_flux.sum()),
        "flagged": int(flagged.sum()),
        "flagged-with-flux": int((flagged & ~no_flux).sum()),
        "unflagged-without-flux": int((~flagged & no_flux).sum()),
        "good": int(good.sum()),
        "first": float(lc.time[good].min()),
        "last": float(lc.time[good].max()),
        "median-flux": float(np.median(lc.flux[good])),
        "median-error": float(np.median(lc.flux_err[good] / lc.flux[good])),
    }
    experiment.table(
        "cleaning",
        [
            ("cadences in the file", counts["total"]),
            ("without a time stamp", counts["no-time"]),
            ("without a PDCSAP flux and error", counts["no-flux"]),
            ("with a nonzero quality flag", counts["flagged"]),
            ("of these, with a PDCSAP flux", counts["flagged-with-flux"]),
            ("without a flux but not flagged", counts["unflagged-without-flux"]),
            ("kept: quality 0 and every value finite", counts["good"]),
        ],
        columns=[("cadences", "", "s"), ("number", "", "d")],
        caption="The 2-minute cadences of the file and what the cleaning "
        "removes: a cadence is kept when its quality flag is 0 and its time, "
        "flux, and error are numbers.",
    )
    return counts


def one_transit(lc: LightCurve, analysis: Analysis, epoch: int) -> dict:
    """One transit's window as the normalisation sees it: the good cadences
    within +-HALF_WINDOW of the mid-time, which of them form the baseline,
    the parabola fitted to the baseline (the normalisation of the analysis),
    and a straight line fitted to the same cadences."""
    ok = reference.good(lc)
    t, f, e = lc.time[ok], lc.flux[ok], lc.flux_err[ok]
    eph = analysis.ephemeris
    offset = t - (eph.t0 + epoch * eph.period)
    window = np.abs(offset) < reference.HALF_WINDOW
    offset, f, e, t = offset[window], f[window], e[window], t[window]
    base = np.abs(offset) > reference.HALF_MASK
    parabola = np.polyfit(offset[base], f[base], reference.DEGREE)
    line = np.polyfit(offset[base], f[base], 1)
    return {
        "time": t,
        "offset": offset,
        "flux": f,
        "error": e,
        "base": base,
        "parabola": parabola,
        "line": line,
        "normalised": f / np.polyval(parabola, offset),
    }


def phase_curve(lc: LightCurve, analysis: Analysis) -> dict:
    """The good cadences outside the transits folded on the orbital phase:
    each complete orbit (phase -0.25 to 0.75, at least 90 % of its cadences
    good) divided by its own median, then the mean and its standard error in
    bins of PHASE_BIN; phase 0 is mid-transit. Returns the bin centres, the
    means and standard errors in ppm, the number of orbits used, and the
    half width in phase of the part excluded around the transit."""
    ok = reference.good(lc)
    t, f = lc.time[ok], lc.flux[ok]
    eph = analysis.ephemeris
    cycles = (t - eph.t0) / eph.period + 0.25
    orbit, phase = np.floor(cycles), cycles % 1 - 0.25
    per_orbit = eph.period * 86400 / reference.CADENCE
    relative = np.full(f.shape, np.nan)
    used = 0
    for n in np.unique(orbit):
        mine = orbit == n
        if mine.sum() >= 0.9 * per_orbit:
            relative[mine] = f[mine] / np.median(f[mine])
            used += 1
    mask = reference.HALF_MASK / eph.period
    keep = np.isfinite(relative) & (np.abs(phase) > mask)
    edges = np.arange(-0.25, 0.75 + 1e-9, PHASE_BIN)
    centres, means, sems = _binned(phase[keep], (relative[keep] - 1) * 1e6, edges)
    return {
        "phase": centres,
        "ppm": means,
        "sem": sems,
        "orbits": used,
        "mask": mask,
    }


def phase_contrast(curve: dict) -> dict:
    """Mean of the bins near the quarter phases (within 0.1 of -0.25, 0.25,
    and 0.75) against the bins next to the transit (outside the mask, within
    0.16 of phase 0) and around phase 0.5 (within 0.06), in ppm with
    standard errors."""
    x, y, s = curve["phase"], curve["ppm"], curve["sem"]

    def mean(where: np.ndarray) -> tuple[float, float]:
        return float(y[where].mean()), float(
            np.sqrt(np.sum(s[where] ** 2)) / where.sum()
        )

    quarter = (
        (np.abs(x - 0.25) < 0.1) | (np.abs(x + 0.25) < 0.1) | (np.abs(x - 0.75) < 0.1)
    )
    return {
        "quarter": mean(quarter),
        "transit": mean(np.abs(x) < 0.16),
        "half": mean(np.abs(x - 0.5) < 0.06),
    }


# The fits.


def fit_uniform_star(analysis: Analysis) -> FitResult:
    """The transit lesson's uniform star (u1 = u2 = 0) fitted to the same
    normalised cadences, on the same ephemeris and with the same errors:
    p, a, and b only."""
    folded = analysis.folded
    t0, period = analysis.ephemeris.t0, analysis.ephemeris.period

    def model(time, p, a, b):
        return reference.model_flux(time, t0, period, p, a, b, 0.0, 0.0)

    return fit_curve(
        model,
        folded.time,
        folded.flux,
        [0.1, 3.5, 0.3],
        sigma=folded.error,
        names=("p", "a", "b"),
        bounds=([0.01, 1.5, 0.0], [0.5, 10.0, 1.0]),
    )


def derived(params: np.ndarray, period: float) -> np.ndarray:
    """p, b, a, depth at mid-transit [1], T14 and T23 [h], ingress [min],
    inclination [deg], and mean stellar density [kg/m3] from the shape
    parameters p, a, b, u1, u2 and the period [d]."""
    p, a, b, u1, u2 = params
    inclination = np.arccos(b / a)
    t14, t23 = durations(period, a, inclination, p)
    depth = 1.0 - reference.limb_flux(np.array([b]), p, u1, u2)[0]
    density = 3 * np.pi * a**3 / (reference.G * (period * 86400) ** 2)
    return np.array(
        [
            p,
            b,
            a,
            depth,
            t14 * 24,
            t23 * 24,
            (t14 - t23) / 2 * 24 * 60,
            np.degrees(inclination),
            density,
        ]
    )


def propagate_correlated(
    func: Callable[[np.ndarray], np.ndarray],
    values: np.ndarray,
    covariance: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Value of ``func(values)`` and its standard errors from the covariance
    of the inputs, sqrt(diag(J C J^T)) with J the Jacobian by central
    differences; and, for comparison, the standard errors if the inputs
    were independent (the diagonal of C alone)."""
    values = np.asarray(values, dtype=float)
    centre = np.asarray(func(values), dtype=float)
    columns = []
    for k in range(values.size):
        step = 1e-6 * max(abs(values[k]), 1e-3)
        up, down = values.copy(), values.copy()
        up[k] += step
        down[k] -= step
        columns.append((np.asarray(func(up)) - np.asarray(func(down))) / (2 * step))
    jacobian = np.array(columns).T
    full = np.sqrt(np.diag(jacobian @ covariance @ jacobian.T))
    independent = np.sqrt(np.diag(jacobian @ np.diag(np.diag(covariance)) @ jacobian.T))
    return centre, full, independent


def geometry_table(experiment: Experiment, analysis: Analysis) -> dict:
    """The geometry with its standard errors from the pipeline's errors and
    the same scaled by the square root of the reduced chi-square; record the
    table and return value, error, and independent error by row name."""
    shape = analysis.shape
    period = analysis.ephemeris.period
    values, errors, independent = propagate_correlated(
        lambda x: derived(x, period), shape.params, shape.covariance
    )
    inflate = np.sqrt(shape.reduced_chi2)
    rows, found = [], {}
    for (name, unit, scale), v, s, i in zip(
        GEOMETRY, values, errors, independent, strict=True
    ):
        found[name] = (v * scale, s * scale, i * scale)
        rows.append((name, unit, v * scale, s * scale, s * scale * inflate))
    experiment.table(
        "geometry",
        rows,
        columns=[
            ("quantity", "", "s"),
            ("unit", "", "s"),
            ("fitted or derived", "", ".5g"),
            ("standard error", "", ".2g"),
            ("scaled by sqrt(reduced chi-square)", "", ".2g"),
        ],
        caption="The geometry of WASP-18 b from the fit of the limb-darkened "
        "model to 21 transits. Standard errors from the pipeline's errors, "
        "propagated through the covariance of the five fitted parameters; the "
        "last column allows for the excess scatter of the residuals.",
    )
    return found


def sensitivity_table(experiment: Experiment, lc: LightCurve, analysis: Analysis):
    """The normalisation and the shape fit repeated with other windows and
    baselines on the ephemeris of the analysis; record the table and return
    the rows (half window, degree, p, a, b, depth [ppm], T14 [h])."""
    t0, period = analysis.ephemeris.t0, analysis.ephemeris.period
    rows = []
    choices = [(reference.HALF_WINDOW, reference.DEGREE), *reference.VARIANTS]
    for half_window, degree in choices:
        if (half_window, degree) == choices[0]:
            shape = analysis.shape
        else:
            folded = reference.normalise(lc, t0, period, half_window, degree)
            shape = reference.fit_shape(folded, t0, period)
        g = derived(shape.params, period)
        baseline = "parabola" if degree == 2 else "straight line"
        rows.append(
            (
                f"{baseline}, +-{half_window:.2f} d",
                shape.value("p"),
                shape.value("a"),
                shape.value("b"),
                g[3] * 1e6,
                g[4],
            )
        )
    experiment.table(
        "sensitivity",
        rows,
        columns=[
            ("normalisation", "", "s"),
            ("p", "", ".5f"),
            ("a/R*", "", ".3f"),
            ("b", "", ".3f"),
            ("depth", "ppm", ".0f"),
            ("T14", "h", ".4f"),
        ],
        caption="The shape fit after other normalisations: the first row is "
        "the analysis of the page, the others change the window around each "
        "mid-time or the baseline. A sensitivity of the result to a choice of "
        "the analysis, not an uncertainty interval.",
    )
    return rows


def tic_density() -> float:
    """The mean density [kg/m3] that the catalogue values of the header
    imply, 3 g / (4 pi G R), with g in m/s2 and R in m."""
    g = 10**TIC_LOGG / 100
    return float(3 * g / (4 * np.pi * reference.G * TIC_RADIUS * R_SUN))


# The figures.


def _binned(x: np.ndarray, y: np.ndarray, edges: np.ndarray):
    """Mean and standard error of the mean of ``y`` in the bins of ``x``
    with more than five points."""
    index = np.digitize(x, edges)
    centres, means, sems = [], [], []
    for k in range(1, edges.size):
        inside = index == k
        if inside.sum() > 5:
            centres.append(x[inside].mean())
            means.append(y[inside].mean())
            sems.append(y[inside].std(ddof=1) / np.sqrt(inside.sum()))
    return np.array(centres), np.array(means), np.array(sems)


def draw_light_curve(lc: LightCurve, analysis: Analysis) -> Figure:
    """The PDCSAP flux of the file as released, over the sector and over
    two days, with the pipeline's errors."""
    series = light_curve_series(lc)
    flagged = (lc.quality != 0) & np.isfinite(lc.flux)
    # Every cadence is drawn as a small square without an edge: thousands of
    # round, outlined dots cost the page tens of kilobytes more as PNG.
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(6.4, 4.8), constrained_layout=True)
    top.plot(
        series.x[~flagged],
        series.y[~flagged],
        ls="none",
        marker="s",
        ms=1.0,
        mew=0,
        color=COLOURS[0],
        label=f"PDCSAP flux, quality 0 [{series.status}]",
    )
    top.plot(
        series.x[flagged],
        series.y[flagged],
        ls="none",
        marker="x",
        ms=6,
        color=COLOURS[1],
        label=f"PDCSAP flux with a quality flag [{series.status}]",
    )
    top.set_xlabel(f"time [{series.x_unit}]")
    top.set_ylabel(f"PDCSAP flux [{series.y_unit}]")
    top.set_ylim(47300, 48450)
    top.set_title("The light curve of the file, sector 29: gaps where no value is")
    top.legend(fontsize=7.5, loc="upper center", ncols=2)
    eph = analysis.ephemeris
    start = eph.t0 + analysis.folded.epochs[0] * eph.period - 0.5
    near = (series.x > start) & (series.x < start + 2.0)
    bottom.errorbar(
        series.x[near],
        series.y[near],
        yerr=series.sigma[near],
        ls="none",
        marker=".",
        ms=2.5,
        elinewidth=0.5,
        color=COLOURS[0],
        label=f"PDCSAP flux with the pipeline's one-sigma error [{series.status}]",
    )
    bottom.set_xlabel(f"time [{series.x_unit}]")
    bottom.set_ylabel(f"PDCSAP flux [{series.y_unit}]")
    bottom.set_ylim(47100, 48100)
    bottom.set_title("Two days of it: two transits")
    bottom.legend(fontsize=7.5, loc="lower center")
    add_credit(fig, CREDIT)
    label_status(fig, series.status)
    return fig


def draw_detrending(curve: dict, window: dict, epoch: int) -> Figure:
    """The flux outside the transits folded on the orbital phase, one
    transit in e-/s with the parabola fitted to its baseline, and that
    transit divided by the parabola."""
    hours = window["offset"] * 24
    dense = np.linspace(-reference.HALF_WINDOW, reference.HALF_WINDOW, 300)
    base = window["base"]
    fig = plt.figure(figsize=(6.4, 7.0), constrained_layout=True)
    grid = fig.add_gridspec(3, 1, height_ratios=(1.0, 1.0, 1.0))
    phase = fig.add_subplot(grid[0])
    top = fig.add_subplot(grid[1])
    bottom = fig.add_subplot(grid[2], sharex=top)
    phase.errorbar(
        curve["phase"],
        curve["ppm"],
        yerr=curve["sem"],
        ls="none",
        marker="o",
        ms=3,
        color=COLOURS[0],
        label="measured outside the transits, bins of 0.02 in phase, "
        "standard error of the mean [processed]",
    )
    phase.axvspan(
        -curve["mask"],
        curve["mask"],
        color="0.85",
        zorder=0,
        label="the transit, left out",
    )
    phase.axhline(0.0, color="0.5", lw=0.8)
    phase.set_ylim(-700, 800)
    phase.set_xlabel("orbital phase from mid-transit [1]")
    phase.set_ylabel("relative flux [ppm]")
    phase.set_title(
        f"{curve['orbits']} orbits folded, flux over the median: "
        "the baseline is not flat"
    )
    phase.legend(fontsize=7, loc="upper center")
    for ax in (top, bottom):
        ax.axvspan(
            -reference.HALF_MASK * 24,
            reference.HALF_MASK * 24,
            color="0.92",
            zorder=0,
            label="excluded from the baseline fit" if ax is top else None,
        )
    top.plot(
        hours[base],
        window["flux"][base],
        ls="none",
        marker="o",
        ms=2.5,
        color=COLOURS[0],
        label="measured, quality 0, used for the baseline [calibrated]",
    )
    top.plot(
        hours[~base],
        window["flux"][~base],
        ls="none",
        marker="o",
        ms=2.5,
        mfc="none",
        color=COLOURS[0],
        label="measured, quality 0, in the transit [calibrated]",
    )
    top.plot(
        dense * 24,
        np.polyval(window["parabola"], dense),
        "--",
        color=COLOURS[1],
        lw=1.4,
        label="baseline model: parabola, fitted [simulated]",
    )
    top.set_ylim(46500, 48100)
    top.set_ylabel("PDCSAP flux [e-/s]")
    top.set_title(f"Transit number {epoch}: the flux and its baseline")
    top.legend(fontsize=7, loc="lower center")
    top.tick_params(labelbottom=False)
    bottom.plot(
        hours,
        window["normalised"],
        ls="none",
        marker=".",
        ms=3,
        color="0.35",
        label="measured flux divided by the parabola [processed]",
    )
    bottom.axhline(1.0, color="0.5", lw=0.8)
    bottom.set_ylim(0.980, 1.003)
    bottom.set_ylabel("normalised flux [1]")
    bottom.set_xlabel("time from mid-transit [h]")
    bottom.set_title("The same transit, normalised")
    bottom.legend(fontsize=7, loc="lower center")
    add_credit(fig, CREDIT)
    label_status(fig, "processed")
    return fig


def draw_transit_fit(analysis: Analysis, uniform: FitResult) -> Figure:
    """The folded transits, binned, against the limb-darkened fit and the
    uniform-star fit, with the binned residuals of both."""
    folded = analysis.folded
    eph = analysis.ephemeris
    params = analysis.params()
    hours = (folded.time - (eph.t0 + folded.epoch * eph.period)) * 24
    edges = np.arange(
        -reference.HALF_WINDOW * 24, reference.HALF_WINDOW * 24 + 1e-9, BIN
    )
    dense_h = np.linspace(edges[0], edges[-1], 800)
    dense_t = eph.t0 + dense_h / 24
    models = {
        "model: limb-darkened star, fitted [simulated]": (
            reference.model_flux(dense_t, *params),
            reference.model_flux(folded.time, *params),
            "--",
            COLOURS[1],
        ),
        "model: uniform star, fitted [simulated]": (
            reference.model_flux(dense_t, eph.t0, eph.period, *uniform.params, 0, 0),
            reference.model_flux(
                folded.time, eph.t0, eph.period, *uniform.params, 0, 0
            ),
            ":",
            COLOURS[2],
        ),
    }
    fig, (top, bottom) = plt.subplots(
        2,
        1,
        figsize=(6.4, 5.8),
        sharex=True,
        constrained_layout=True,
        gridspec_kw={"height_ratios": [2.0, 1.0]},
    )
    top.plot(
        hours,
        folded.flux,
        ls="none",
        marker="s",
        ms=1.0,
        mew=0,
        color="0.75",
        label="measured, normalised cadences [processed]",
    )
    x, mean, sem = _binned(hours, folded.flux, edges)
    top.errorbar(
        x,
        mean,
        yerr=sem,
        ls="none",
        marker="o",
        ms=3,
        color=COLOURS[0],
        label="measured, 6-minute bins, standard error of the mean [processed]",
    )
    for k, (name, (curve, at_data, style, colour)) in enumerate(models.items()):
        top.plot(dense_h, curve, ls=style, color=colour, lw=1.5, label=name)
        rx, rmean, rsem = _binned(hours, (folded.flux - at_data) * 1e6, edges)
        bottom.errorbar(
            rx,
            rmean,
            yerr=rsem,
            ls=style,
            lw=1.0,
            marker="os"[k],
            ms=3,
            color=colour,
            label=name.split(",")[0].removeprefix("model: ") + ": measured minus model",
        )
    top.set_ylim(0.9805, 1.002)
    top.set_ylabel("normalised flux [1]")
    top.set_title(f"{len(folded.epochs)} transits folded on the measured period")
    top.legend(fontsize=7, loc="lower center")
    bottom.axhline(0.0, color="0.4", lw=0.8)
    bottom.set_ylabel("residual [ppm]")
    bottom.set_xlabel("time from mid-transit [h]")
    bottom.set_ylim(-1400, 1000)
    bottom.set_title("Residuals of the two models, 6-minute bins")
    bottom.legend(fontsize=7, loc="lower center", ncols=2)
    add_credit(fig, CREDIT)
    label_status(fig, "processed")
    return fig


def draw_mid_times(analysis: Analysis) -> Figure:
    """Observed minus computed mid-time of every transit with its standard
    error from the pipeline's errors."""
    fig, ax = plt.subplots(figsize=(6.4, 3.8), constrained_layout=True)
    ax.errorbar(
        analysis.epochs,
        reference.o_minus_c(analysis),
        yerr=analysis.errors * 1440,
        ls="none",
        marker="o",
        ms=4,
        color=COLOURS[0],
        label="mid-time of each transit, one standard error [processed]",
    )
    ax.axhline(0.0, color=COLOURS[1], ls="--", lw=1.2, label="the fitted ephemeris")
    ax.set_xlabel("transit number from t0 [1]")
    ax.set_ylabel("observed minus computed [min]")
    ax.set_title("The mid-times against a constant period")
    ax.legend(fontsize=7.5, loc="upper left")
    add_credit(fig, CREDIT)
    label_status(fig, "processed")
    return fig


# The exercises.


def radius_exercise(p: float) -> None:
    """Exercise 1: the planet's radius from the radius ratio and the
    catalogue radius of the star."""
    radius = p * TIC_RADIUS * R_SUN
    print(f"planet radius: {radius / 1e3:,.0f} km")
    print(f"in Jupiter radii: {radius / R_JUPITER:.2f}")


def period_exercise(epochs: np.ndarray, sigma_minutes: float) -> None:
    """Exercise 2: the standard error of the period of a straight line
    through mid-times of equal error sigma at the given transit numbers."""
    spread = np.sum((epochs - epochs.mean()) ** 2)
    error = sigma_minutes * 60 / np.sqrt(spread)
    print(f"transits: {epochs.size}, numbers {epochs.min()} to {epochs.max()}")
    print(f"sum of squared distances from the mean number: {spread:.0f}")
    print(f"standard error of the period: {error:.2f} s")


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    gaps = check_against_ast7(experiment)
    experiment.number(
        "ast7-uniform-gap",
        "below 1e-12" if gaps["uniform"] < 1e-12 else f"{gaps['uniform']:.0e}",
    )
    experiment.number("ast7-depth-gap", gaps["depth"], ".0e")
    experiment.number("ast7-grid-gap", gaps["grid"], ".0e")

    lc = load_light_curve()
    counts = cleaning(experiment, lc)
    experiment.number("cadences", counts["total"], ",d")
    experiment.number("good", counts["good"], ",d")
    experiment.number("no-time", counts["no-time"], ",d")
    experiment.number("no-flux", counts["no-flux"], ",d")
    experiment.number("flagged", counts["flagged"], ",d")
    experiment.number("flagged-with-flux", counts["flagged-with-flux"], "d")
    experiment.number("good-percent", 100 * counts["good"] / counts["total"], ".0f")
    experiment.number("first-good", counts["first"], ".2f")
    experiment.number("last-good", counts["last"], ".2f")
    experiment.number("median-flux", counts["median-flux"], ",.0f")
    experiment.number("median-error", counts["median-error"] * 1e6, ".0f")

    analysis = reference.analyse(lc)
    folded, shape, eph = analysis.folded, analysis.shape, analysis.ephemeris
    experiment.number("dips", reference.transit_events(lc).size)
    experiment.number("transits", len(folded.epochs))
    experiment.number("fitted-cadences", folded.time.size, ",d")

    epoch = folded.epochs[0]
    window = one_transit(lc, analysis, epoch)
    experiment.number(
        "baseline-bow",
        (np.polyval(window["line"], 0.0) / np.polyval(window["parabola"], 0.0) - 1)
        * 1e6,
        ".0f",
    )
    curve = phase_curve(lc, analysis)
    contrast = phase_contrast(curve)
    experiment.number("phase-orbits", curve["orbits"])
    for key in ("quarter", "transit", "half"):
        experiment.number(f"phase-{key}", contrast[key][0], "+.0f")
        experiment.number(f"phase-{key}-err", contrast[key][1], ".0f")

    experiment.table(
        "fit",
        [
            (name, shape.params[k], shape.stderr[k])
            for k, name in enumerate(("p", "a/R*", "b", "u1", "u2"))
        ],
        columns=[
            ("parameter", "", "s"),
            ("fitted", "", ".5g"),
            ("standard error", "", ".2g"),
        ],
        caption="The five shape parameters of the limb-darkened model fitted to "
        "the normalised cadences, with standard errors from the pipeline's "
        "errors (an absolute covariance).",
    )
    experiment.number("reduced-chi2", shape.reduced_chi2, ".2f")
    experiment.number("dof", shape.dof, ",d")
    experiment.number("error-scale", np.sqrt(shape.reduced_chi2), ".2f")
    experiment.number(
        "fit-warnings", "; ".join(shape.warnings) if shape.warnings else "none"
    )
    experiment.number("corr-a-b", shape.correlation[1, 2], ".2f")
    experiment.number("corr-u1-u2", shape.correlation[3, 4], ".2f")
    experiment.number("corr-p-b", shape.correlation[0, 2], ".2f")
    residual = reference.residuals(analysis)
    experiment.number("residual-rms", residual.std() * 1e6, ".0f")
    experiment.number("pipeline-error", np.median(folded.error) * 1e6, ".0f")

    uniform = fit_uniform_star(analysis)
    experiment.number("uniform-chi2", uniform.chi2, ",.0f")
    experiment.number("ld-chi2", shape.chi2, ",.0f")
    experiment.number("uniform-reduced-chi2", uniform.reduced_chi2, ".2f")
    experiment.number("chi2-difference", uniform.chi2 - shape.chi2, ",.0f")
    experiment.number("uniform-p", uniform.value("p"), ".4f")
    experiment.number("uniform-b", uniform.value("b"), ".2f")

    found = geometry_table(experiment, analysis)

    def both(key: str, name: str, spec: str, err_spec: str) -> None:
        value, error, independent = found[name]
        experiment.number(key, value, spec)
        experiment.number(f"{key}-err", error, err_spec)
        if key in ("depth", "t14"):
            experiment.number(f"{key}-err-independent", independent, err_spec)

    both("p", "radius ratio p = Rp/R*", ".5f", ".5f")
    both("b", "impact parameter b", ".3f", ".3f")
    both("a", "orbital radius a/R*", ".3f", ".3f")
    both("depth", "depth at mid-transit", ",.0f", ".0f")
    both("t14", "total duration T14", ".4f", ".4f")
    both("t23", "full duration T23", ".3f", ".3f")
    both("ingress", "ingress (T14 - T23)/2", ".1f", ".1f")
    both("inclination", "inclination arccos(b/a)", ".1f", ".1f")
    both("density", "mean stellar density", ".0f", ".0f")
    experiment.number("p-squared", shape.value("p") ** 2 * 1e6, ",.0f")

    experiment.number("period", eph.period, ".7f")
    experiment.number("period-err", eph.period_err * 86400, ".2f")
    experiment.number("timing-chi2", eph.chi2, ".1f")
    experiment.number("timing-dof", eph.dof)
    experiment.number("timing-scale", np.sqrt(eph.chi2 / eph.dof), ".1f")
    experiment.number("timing-error", np.median(analysis.errors) * 1440, ".2f")
    experiment.number("largest-oc", np.abs(reference.o_minus_c(analysis)).max(), ".2f")
    experiment.number(
        "period-err-scaled", eph.period_err * 86400 * np.sqrt(eph.chi2 / eph.dof), ".2f"
    )

    rows = sensitivity_table(experiment, lc, analysis)
    window_p = [row[1] for row in rows if row[0].startswith("parabola")]
    experiment.number("window-p-range", max(window_p) - min(window_p), ".5f")
    experiment.number("line-deeper", rows[-1][4] - rows[0][4], ".0f")
    experiment.number("line-b", rows[-1][3], ".3f")

    rho_tic = tic_density()
    rho = found["mean stellar density"]
    experiment.number("tic-density", rho_tic, ".0f")
    experiment.number("density-difference", 100 * (1 - rho_tic / rho[0]), ".0f")
    experiment.number("density-sigmas", (rho[0] - rho_tic) / rho[1], ".0f")

    experiment.figure("fig-light-curve", partial(draw_light_curve, lc, analysis))
    experiment.figure("fig-detrending", partial(draw_detrending, curve, window, epoch))
    experiment.figure("fig-transit-fit", partial(draw_transit_fit, analysis, uniform))
    experiment.figure("fig-mid-times", partial(draw_mid_times, analysis))

    with experiment.capture("radius-exercise"):
        radius_exercise(shape.value("p"))
    with experiment.capture("period-exercise"):
        period_exercise(analysis.epochs, np.median(analysis.errors) * 1440)
    return experiment


if __name__ == "__main__":
    main(run)
