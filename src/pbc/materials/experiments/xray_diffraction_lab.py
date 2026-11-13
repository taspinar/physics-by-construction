"""The experiment of the lesson "X-ray diffraction lab".

The lattice model of the lesson "Crystal lattices and phonons" (atoms on a
lattice that repeats with one spacing a), extended to the cubic lattice
of lanthanum hexaboride, against the X-ray powder patterns that certified
NIST's line-position standard SRM 660c (the committed samples of the card
``nist-srm660c-lab6``, 20 specimens). Bragg's law turns the position of each
of the 24 measured reflections into a spacing and a lattice parameter; the
Nelson-Riley extrapolation removes the errors that vanish at theta = 90 deg;
and the same analysis of NIST's own model pattern measures the bias of the
method. Run it as a program to write the figures and the numbers of the
page:

    uv run --locked --no-dev python -m \\
        pbc.materials.experiments.xray_diffraction_lab out
"""

from dataclasses import dataclass
from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from scipy import stats

from pbc.data import SAMPLES_DIR
from pbc.data.adapters import diffraction_pattern_series
from pbc.data.fit import fit_curve
from pbc.data.inverse import residual_autocorrelation
from pbc.data.plotting import COLOURS, add_credit, label_status
from pbc.data.reference.srm660c import (
    CERTIFIED_A,
    CERTIFIED_T,
    CERTIFIED_U,
    HKL,
    SPECIMENS,
    TABLE1_TWO_THETA,
    WAVELENGTH,
    Analysis,
    Pattern,
    Peak,
    analyse,
    analyse_measured,
    analyse_model,
    doublet,
    kalpha2,
    load,
    read_specimens,
    windows,
)
from pbc.data.uncertainty import standard_from_expanded
from pbc.experiment import Experiment, main
from pbc.materials.diffraction import (
    bragg_two_theta,
    displacement_function,
    displacement_shift,
    index_sum,
    lattice_parameter,
    nelson_riley,
    plane_spacing,
)

DATASET = "nist-srm660c-lab6"
SPECIMEN_FILE = "specimens.csv"
# region: choices
RADIUS = 217.5  # mm, the goniometer radius of NIST's diffractometer
LOWEST = 60.0  # degrees 2theta: reflections above it enter the extrapolation
SHOWN = "100a"  # the specimen whose pattern, peaks and lines are drawn
SHOWN_PEAKS = ((1, 1, 0), (5, 1, 0))  # a low-angle and a high-angle reflection
PEAK_MARGIN = 0.4  # degrees shown on either side of a drawn doublet
SYNTHETIC_DISPLACEMENT = -0.1  # mm, the displacement of the synthetic check
SEED = 443  # the noise of the synthetic patterns
# The extrapolations of the sensitivity table: function, lowest 2theta,
# weighted by the peak positions' standard errors or not. The first is the
# lab's own.
EXTRAPOLATIONS = (
    ("Nelson-Riley", 60.0, False),
    ("Nelson-Riley", 40.0, False),
    ("Nelson-Riley", 80.0, False),
    ("Nelson-Riley", 100.0, False),
    ("Nelson-Riley", 60.0, True),
    ("displacement", 60.0, False),
)
# endregion: choices
CREDIT = (
    "Data: NIST; Black, Cline, Mendenhall, 'Diffraction Data for SRM 660c', "
    "doi 10.18434/mds2-2315 (17 U.S.C. 105); CIFs converted to CSV 2026-11-09, "
    "values unchanged. Fits, lines: this lesson's code."
)
FUNCTIONS = {"Nelson-Riley": nelson_riley, "displacement": displacement_function}


def ppm(value: float, reference: float) -> float:
    """``value`` relative to ``reference``, in parts per million."""
    return (value / reference - 1) * 1e6


def load_patterns() -> dict[str, Pattern]:
    """The 20 committed patterns, measured and NIST's model on one grid."""
    return load(SAMPLES_DIR / DATASET)


def load_specimens() -> dict[str, dict[str, float]]:
    """Per specimen the CIF's temperature, displacement, and NIST's a."""
    return read_specimens(SAMPLES_DIR / DATASET / SPECIMEN_FILE)


def peak_lattice_parameter(peak: Peak) -> float:
    """a [angstrom] from one fitted K-alpha-1 position by Bragg's law."""
    return float(lattice_parameter(peak.two_theta, peak.hkl, WAVELENGTH))


def bragg_positions(a: float) -> np.ndarray:
    """The K-alpha-1 angles 2theta [degrees] of the 24 reflections that
    Bragg's law predicts for a cubic lattice of parameter ``a``."""
    return np.array([bragg_two_theta(plane_spacing(a, hkl), WAVELENGTH) for hkl in HKL])


@dataclass(frozen=True)
class Line:
    """The line a = a0 + slope f(theta) of an extrapolation, in angstrom."""

    a0: float  # a at theta = 90 deg
    slope: float
    a0_error: float  # standard error of a0
    residuals: np.ndarray  # a per reflection minus the line, in angle order
    warnings: tuple[str, ...]

    def at(self, x):
        return self.a0 + self.slope * np.asarray(x, float)


def _straight(x, intercept, slope):
    return intercept + slope * x


def extrapolate(
    peaks: tuple[Peak, ...],
    function: str = "Nelson-Riley",
    lowest: float = LOWEST,
    weighted: bool = False,
) -> Line:
    """A straight line of a per reflection against ``function`` of theta,
    over the reflections above ``lowest``, fitted with ``fit_curve``; its
    intercept is a at theta = 90 deg. Unweighted, the standard errors come
    from the scatter about the line; weighted, from the peak positions'
    standard errors. The fit runs in ppm of the certified a, so that the
    intercept and the slope are numbers of similar size."""
    used = [p for p in peaks if p.two_theta > lowest]
    x = FUNCTIONS[function]([p.theta for p in used])
    a = np.array([peak_lattice_parameter(p) for p in used])
    sigma = np.array([p.a_error for p in used]) / CERTIFIED_A * 1e6
    fit = fit_curve(
        _straight,
        x,
        ppm(a, CERTIFIED_A),
        [0.0, 0.0],
        sigma=sigma if weighted else None,
        names=("a0", "slope"),
    )
    scale = CERTIFIED_A / 1e6
    return Line(
        CERTIFIED_A + fit.value("a0") * scale,
        fit.value("slope") * scale,
        float(fit.stderr[0]) * scale,
        fit.residuals * scale,
        fit.warnings,
    )


def analyse_all(patterns: dict[str, Pattern]) -> tuple[dict, dict]:
    """The dossier's peak fits of every measured pattern, and of NIST's
    model pattern with the measured weights."""
    measured = {s: analyse_measured(p) for s, p in patterns.items()}
    model = {s: analyse_model(p) for s, p in patterns.items()}
    return measured, model


def intercepts(analyses: dict[str, Analysis], **choice) -> np.ndarray:
    """The extrapolated a [angstrom] of each specimen."""
    return np.array([extrapolate(analyses[s].peaks, **choice).a0 for s in SPECIMENS])


def summary(values: np.ndarray) -> tuple[float, float, float]:
    """Mean, standard deviation, and standard error of the mean."""
    sd = float(np.std(values, ddof=1))
    return float(np.mean(values)), sd, sd / np.sqrt(values.size)


def reflection_table(experiment: Experiment, analysis: Analysis) -> None:
    """The 24 reflections of the shown specimen: indices, the certificate's
    position, the fitted K-alpha-1 position, the spacing, and a."""
    rows = []
    for peak, table in zip(analysis.peaks, TABLE1_TWO_THETA, strict=True):
        rows.append(
            (
                "".join(map(str, peak.hkl)),
                index_sum(peak.hkl),
                table,
                peak.two_theta,
                1e4 * peak.error,
                peak.d,
                peak_lattice_parameter(peak),
                peak.reduced_chi2,
            )
        )
    experiment.table(
        "reflections",
        rows,
        columns=[
            ("hkl", "", "s"),
            ("h²+k²+l²", "", "d"),
            ("2θ, certificate", "degrees", ".3f"),
            ("2θ, fitted Kα₁", "degrees", ".4f"),  # noqa: RUF001
            ("its standard error", "10⁻⁴ degrees", ".1f"),
            ("spacing d", "Å", ".6f"),
            ("a = d √(h²+k²+l²)", "Å", ".6f"),
            ("reduced χ² of the fit", "", ".1f"),
        ],
        caption=f"The 24 reflections of specimen {SHOWN}: the certificate's position "
        "(Table 1, an information value), the fitted Kα₁ position with its standard "  # noqa: RUF001
        "error scaled by the fit's residuals, the spacing by Bragg's law, and the "
        "lattice parameter of each reflection alone.",
    )


def indexing(measured: dict[str, Analysis]) -> dict:
    """How far the fitted positions of all 20 specimens lie from the
    certificate's Table 1, and how far each from the angles Bragg's law
    gives for one a fitted to the 24 positions of that specimen."""
    offsets = np.array(
        [
            [
                p.two_theta - t
                for p, t in zip(measured[s].peaks, TABLE1_TWO_THETA, strict=True)
            ]
            for s in SPECIMENS
        ]
    )
    return {
        "max-offset": float(np.abs(offsets).max()),
        "low-offset": float(offsets[:, 0].mean()),
        "high-offset": float(offsets[:, -1].mean()),
    }


def single_reflections(measured: dict[str, Analysis]) -> dict:
    """The a of single reflections of the shown specimen: lowest and
    highest angle, and their difference."""
    peaks = measured[SHOWN].peaks
    first, last = peak_lattice_parameter(peaks[0]), peak_lattice_parameter(peaks[-1])
    return {"first": first, "last": last, "drift": last - first}


def method_check(experiment: Experiment, pattern: Pattern, fitted: Analysis) -> dict:
    """The analysis on synthetic patterns whose a is known: the method's own
    symmetric doublet with the fitted widths and heights of the shown
    specimen, at the Bragg positions of the certified a, shifted by a
    specimen displacement or not, with noise of the measured counting
    errors (fixed seed). Records the table; returns the errors in ppm."""
    rng = np.random.default_rng(SEED)
    noise = rng.normal(size=pattern.two_theta.size) * pattern.sigma
    rows, found = [], {}
    for displacement in (0.0, SYNTHETIC_DISPLACEMENT):
        intensity = np.empty_like(pattern.two_theta)
        for ix, peak in zip(windows(pattern.two_theta), fitted.peaks, strict=True):
            b0, b1, height, _, fwhm, eta = peak.params
            centre = bragg_two_theta(plane_spacing(CERTIFIED_A, peak.hkl), WAVELENGTH)
            centre = float(centre + displacement_shift(centre, displacement, RADIUS))
            intensity[ix] = doublet(
                (b0, b1, height, centre, fwhm, eta),
                pattern.two_theta[ix],
                fitted.ratio,
                fitted.share,
            )
        result = analyse(pattern.two_theta, intensity + noise, pattern.sigma)
        for function in FUNCTIONS:
            line = extrapolate(result.peaks, function)
            error = ppm(line.a0, CERTIFIED_A)
            found[(displacement, function)] = error
            rows.append(
                (
                    f"{displacement:.1f}",
                    function,
                    error,
                    line.slope,
                    CERTIFIED_A * displacement / RADIUS
                    if function == "displacement"
                    else None,
                )
            )
    experiment.table(
        "method-check",
        rows,
        columns=[
            ("displacement s", "mm", "s"),
            ("extrapolated against", "", "s"),
            ("a0 minus the true a", "ppm", "+.1f"),
            ("slope of the line", "Å", "+.5f"),
            ("first-order slope a s/R", "Å", "+.5f"),
        ],
        caption="The analysis of the lab on synthetic patterns on the grid of "
        f"specimen {SHOWN}, built with the certified a, symmetric doublets, and "
        "Gaussian noise of the measured counting errors (seed "
        f"{SEED}): the extrapolated a against the true one, without and with a "
        f"specimen displacement on a circle of radius {RADIUS} mm.",
    )
    return found


def _ppm_of_a(value: float) -> float:
    """A length [angstrom] in parts per million of the certified a."""
    return value / CERTIFIED_A * 1e6


def error_check(experiment: Experiment, measured: dict, model: dict) -> dict:
    """Whether the scatter about one specimen's line is counting noise, as
    the ordinary standard error of its intercept assumes. For the
    measurement, for NIST's model (which has no counting noise), and for
    measured minus model: the autocorrelation of neighbouring residuals in
    the order of the angle (mean over the specimens, and the number of
    specimens above the band 2/sqrt(n) of independent residuals), the
    standard error of one intercept, and the spread over the specimens."""
    lines = {
        name: [extrapolate(analyses[s].peaks) for s in SPECIMENS]
        for name, analyses in (("measured", measured), ("model", model))
    }
    pairs = list(zip(lines["measured"], lines["model"], strict=True))
    n = lines["measured"][0].residuals.size
    band = 2 / np.sqrt(n)
    series = (
        ("measured", "measured", lines["measured"]),
        ("model", "NIST's model, same method", lines["model"]),
        (
            "difference",
            "measured minus model",
            [
                Line(m.a0 - c.a0, 0.0, np.nan, m.residuals - c.residuals, ())
                for m, c in pairs
            ],
        ),
    )
    out, rows = {"band": band, "n": n}, []
    for name, label, fits in series:
        a0 = np.array([f.a0 for f in fits])
        rho = np.array([residual_autocorrelation(f.residuals)[0] for f in fits])
        sd = float(np.std(a0, ddof=1))
        out[name] = {
            "rho1": float(rho.mean()),
            "above": int(np.sum(rho > band)),
            "stderr": _ppm_of_a(float(np.mean([f.a0_error for f in fits]))),
            "sd": _ppm_of_a(sd),
            "mean": _ppm_of_a(float(a0.mean())),
            "sem": _ppm_of_a(sd / np.sqrt(a0.size)),
        }
        rows.append(
            (
                label,
                out[name]["rho1"],
                out[name]["above"],
                None if name == "difference" else out[name]["stderr"],
                out[name]["sd"],
            )
        )
    experiment.table(
        "error-check",
        rows,
        columns=[
            ("series", "", "s"),
            ("autocorrelation of neighbouring residuals, mean of 20", "", "+.2f"),
            (f"specimens above {band:.2f}", "", "d"),
            ("standard error of one intercept, mean of 20", "ppm", ".1f"),
            ("standard deviation of the intercept over 20 specimens", "ppm", ".1f"),
        ],
        caption="The residuals of each specimen's line in the order of the angle, for "
        "the measurement, for NIST's noise-free model analysed the same way, and for "
        f"their difference. For {n} independent residuals the autocorrelation of "
        f"neighbours scatters about zero by about 1/sqrt({n}) = {1 / np.sqrt(n):.2f}; "
        f"{band:.2f} is two of those.",
    )
    return out


def bottle_check(experiment: Experiment, series: dict[str, np.ndarray]) -> dict:
    """Whether the two specimens of one bottle are independent, as the
    standard error of the mean of 20 assumes. The specimens come in pairs,
    a and b, from 10 bottles (``SPECIMENS`` in bottle order). For each
    series of 20 values [ppm]: the correlation of the a and b specimens over
    the bottles, the one-way analysis of variance of the 10 bottles (the F
    ratio of the scatter between the bottle means to that within them, on 9
    and 10 degrees of freedom, and its p-value), the standard error of the
    mean of 20 independent specimens, and that of the mean of the 10 bottle
    means, which assumes nothing about the two specimens of a bottle."""
    out, rows = {}, []
    for name, (label, values) in series.items():
        pairs = np.asarray(values, float).reshape(-1, 2)
        bottles = pairs.mean(axis=1)
        within = float(np.var(pairs, axis=1, ddof=1).mean())
        between = pairs.shape[1] * float(np.var(bottles, ddof=1))
        ratio = between / within
        dof = (bottles.size - 1, bottles.size * (pairs.shape[1] - 1))
        out[name] = {
            "correlation": float(np.corrcoef(pairs[:, 0], pairs[:, 1])[0, 1]),
            "f": ratio,
            "p": float(stats.f.sf(ratio, *dof)),
            "sem": float(np.std(pairs, ddof=1)) / np.sqrt(pairs.size),
            "sem-bottles": float(np.std(bottles, ddof=1)) / np.sqrt(bottles.size),
        }
        found = out[name]
        rows.append(
            (
                label,
                found["correlation"],
                found["f"],
                found["p"],
                found["sem"],
                found["sem-bottles"],
            )
        )
    experiment.table(
        "bottle-check",
        rows,
        columns=[
            ("series", "", "s"),
            ("correlation of the a and b specimens over 10 bottles", "", "+.2f"),
            ("F, between bottles over within (9 and 10 dof)", "", ".2f"),
            ("p-value of F", "", ".2f"),
            ("standard error of the mean, 20 specimens", "ppm", ".2f"),
            ("standard error of the mean, 10 bottle means", "ppm", ".2f"),
        ],
        caption="The two specimens of each of the 10 bottles: whether they scatter "
        "together. F near 1 and a correlation near zero are what independent "
        "specimens give; the standard error of the 10 bottle means holds whether "
        "they are independent or not.",
    )
    return out


def displacement_slopes(measured: dict, specimens: dict) -> dict:
    """The slope of each specimen's line against the displacement function
    cos^2(theta)/sin(theta), against the displacement NIST refined for it:
    the line through them, its correlation, and the first-order slope a/R
    per mm that the geometry of the displacement predicts."""
    disp = np.array([specimens[s]["vertical_displacement_mm"] for s in SPECIMENS])
    slopes = np.array(
        [extrapolate(measured[s].peaks, "displacement").slope for s in SPECIMENS]
    )
    a0_nr = intercepts(measured)
    coefficient, offset = np.polyfit(disp, slopes, 1)
    return {
        "displacement": disp,
        "slopes": slopes,
        "coefficient": float(coefficient),
        "offset": float(offset),
        "correlation": float(np.corrcoef(disp, slopes)[0, 1]),
        "predicted": CERTIFIED_A / RADIUS,
        "nr-correlation": float(np.corrcoef(disp, a0_nr)[0, 1]),
    }


def sensitivity(
    experiment: Experiment, measured: dict, model: dict, nist: float
) -> dict:
    """The mean a over the 20 specimens for each extrapolation of
    ``EXTRAPOLATIONS``, for the measurement and NIST's model; the bias of
    the method, measured minus model, and measured minus certified."""
    rows, gaps, biases, differences = [], [], [], []
    for function, lowest, weighted in EXTRAPOLATIONS:
        choice = {"function": function, "lowest": lowest, "weighted": weighted}
        a_meas = intercepts(measured, **choice)
        a_model = intercepts(model, **choice)
        used = sum(t > lowest for t in TABLE1_TWO_THETA)
        mean, sd, _ = summary(a_meas)
        bias = ppm(float(a_model.mean()), nist)
        gaps.append(ppm(mean, CERTIFIED_A))
        biases.append(bias)
        differences.append(ppm(mean, float(a_model.mean())))
        rows.append(
            (
                function,
                f"{lowest:.0f}",
                "yes" if weighted else "no",
                used,
                mean,
                sd / CERTIFIED_A * 1e6,
                bias,
                differences[-1],
                gaps[-1],
            )
        )
    experiment.table(
        "extrapolations",
        rows,
        columns=[
            ("extrapolated against", "", "s"),
            ("lowest 2θ", "degrees", "s"),
            ("weighted", "", "s"),
            ("reflections", "", "d"),
            ("measured a, mean of 20", "Å", ".6f"),
            ("its standard deviation", "ppm", ".1f"),
            ("model by the same method minus NIST's a", "ppm", "+.1f"),
            ("measured minus model", "ppm", "+.1f"),
            ("measured minus certified", "ppm", "+.1f"),
        ],
        caption="The extrapolated a over the 20 specimens for six choices of the "
        "extrapolation; the first row is the lab's. NIST's model analysed the same way "
        "gives the bias of each choice against the a NIST refined for the model. A "
        "sensitivity of the result to the analysis, not an interval for a.",
    )
    return {
        "gap-low": min(gaps),
        "gap-high": max(gaps),
        "bias-low": min(biases),
        "bias-high": max(biases),
        "difference-max": max(abs(d) for d in differences),
    }


def budget(experiment: Experiment, found: dict) -> None:
    """The parts of the comparison with the certified value, in ppm of a."""
    u = float(standard_from_expanded(CERTIFIED_U, k=2)) / CERTIFIED_A * 1e6
    rows = [
        (
            "spread of measured minus model over 20 specimens (SD)",
            "statistical",
            found["count-sd"],
        ),
        ("repeatability over 20 specimens (SD)", "statistical", found["sd"]),
        ("standard error of the mean of 20 specimens", "statistical", found["sem"]),
        (
            "standard error of the mean of the 10 bottle means",
            "statistical",
            found["sem-bottles"],
        ),
        (
            "measured minus NIST's model, same method (mean of 20)",
            "measured",
            found["difference"],
        ),
        (
            "extrapolation choices: spread of the six means",
            "systematic (sensitivity)",
            found["gap-spread"],
        ),
        ("the method's bias, measured on NIST's model", "systematic", found["bias"]),
        (
            "NIST's refined a in the CIFs (20.85 °C) minus the certified "
            f"({CERTIFIED_T} °C)",
            "reference",
            found["nist-gap"],
        ),
        ("certificate: standard uncertainty U/2", "reference (Type B)", u),
        ("certificate: expanded uncertainty U (k = 2)", "reference (Type B)", 2 * u),
        ("measured minus certified", "the comparison", found["gap"]),
    ]
    experiment.table(
        "budget",
        rows,
        columns=[("part", "", "s"), ("kind", "", "s"), ("size", "ppm", "+.1f")],
        caption="The parts of the comparison of the measured a (mean of 20 specimens, "
        "Nelson-Riley above 60°) with the certified value, in parts per million of a. "
        "Measured minus model, the method's bias, and NIST's refined minus the "
        "certified a add up to the last row.",
    )


def _compact(fig: Figure) -> None:
    """Smaller tick and axis labels: text is most of a figure's bytes, and
    the page's payload budget leaves room for little of it."""
    for ax in fig.axes:
        ax.tick_params(labelsize=8)
        ax.xaxis.label.set_size(9)
        ax.yaxis.label.set_size(9)
        ax.title.set_size(min(ax.title.get_size(), 9.5))


def draw_pattern(patterns: dict, measured: dict) -> Figure:
    """The 24 windows of the shown specimen on a log scale, with the
    K-alpha-1 positions Bragg's law gives for the certified a."""
    shown = patterns[SHOWN]
    series = diffraction_pattern_series(shown)
    fig, ax = plt.subplots(figsize=(6.0, 3.1), constrained_layout=True)
    for k, ix in enumerate(windows(series.x)):
        ax.semilogy(
            series.x[ix],
            series.y[ix],
            color=COLOURS[0],
            lw=0.7,
            # A dense trace drawn at twice the screen's resolution: without
            # antialiasing it looks the same and costs a fifth fewer bytes.
            antialiased=False,
            label=f"measured, specimen {SHOWN} [{series.status}]" if k == 0 else None,
        )
    predicted = bragg_positions(CERTIFIED_A)
    top = float(series.y.max()) * 3
    ax.vlines(
        predicted,
        top,
        top * 2.2,
        color=COLOURS[1],
        lw=1.0,
        label="Bragg's law, K$\\alpha_1$, certified a [simulated]",
    )
    for peak, x in zip(measured[SHOWN].peaks[::3], predicted[::3], strict=True):
        ax.annotate(
            "".join(map(str, peak.hkl)), (x, top * 2.6), ha="center", fontsize=7
        )
    ax.set_ylim(float(series.y.min()) * 0.06, top * 6)
    ax.set_xlabel("2θ [degrees]")
    ax.set_ylabel("intensity [counts/counting time]")
    ax.set_title(f"LaB6, specimen {SHOWN}: 24 scan windows, every third hkl named")
    ax.legend(fontsize=7.5, loc="lower left")
    _compact(fig)
    add_credit(fig, CREDIT)
    label_status(fig, series.status)
    return fig


def draw_peaks(patterns: dict, measured: dict) -> Figure:
    """A low-angle and a high-angle reflection of the shown specimen with
    the fitted doublet and NIST's model; below, the residuals of both."""
    shown = patterns[SHOWN]
    series = diffraction_pattern_series(shown)
    analysis = measured[SHOWN]
    fig, axes = plt.subplots(
        2,
        2,
        figsize=(6.0, 3.6),
        constrained_layout=True,
        sharex="col",
        gridspec_kw={"height_ratios": [2.2, 1.0]},
    )
    for column, hkl in enumerate(SHOWN_PEAKS):
        k = HKL.index(hkl)
        peak = analysis.peaks[k]
        ix = windows(series.x)[k]
        # The peak and its K-alpha-2 with a margin: the flat ends of the
        # window add points and no information.
        ends = (peak.two_theta - PEAK_MARGIN, kalpha2(peak.two_theta, analysis.ratio))
        ix = ix[(series.x[ix] > ends[0]) & (series.x[ix] < ends[1] + PEAK_MARGIN)]
        x = series.x[ix]
        fitted = doublet(peak.params, x, analysis.ratio, analysis.share)
        top, bottom = axes[0, column], axes[1, column]
        # One legend, on the right panel, names the series of both.
        named = column == len(SHOWN_PEAKS) - 1
        top.errorbar(
            x,
            series.y[ix],
            yerr=series.sigma[ix],
            fmt="o",
            ms=1.8,
            color=COLOURS[0],
            elinewidth=0.5,
            label=f"measured [{series.status}], bars 1$\\sigma$ counting error"
            if named
            else None,
        )
        top.plot(
            x,
            fitted,
            "--",
            color=COLOURS[1],
            lw=1.2,
            label="K$\\alpha_1$ + K$\\alpha_2$ doublet fit [simulated]"
            if named
            else None,
        )
        top.plot(
            x,
            shown.calc[ix],
            ":",
            color=COLOURS[2],
            lw=1.4,
            label="NIST's model (CIF) [simulated]" if named else None,
        )
        top.set_ylabel("intensity [counts/time]")
        top.set_title(
            f"reflection {''.join(map(str, hkl))}, reduced χ² {peak.reduced_chi2:.1f}",
            fontsize=10,
        )
        if named:
            top.legend(fontsize=6, loc="upper right")
        bottom.plot(
            x,
            (series.y[ix] - fitted) / series.sigma[ix],
            "o",
            ms=1.8,
            color=COLOURS[1],
        )
        bottom.plot(
            x,
            (series.y[ix] - shown.calc[ix]) / series.sigma[ix],
            "x",
            ms=2.2,
            color=COLOURS[2],
        )
        bottom.axhline(0, color="0.5", lw=0.8)
        bottom.set_xlabel("2θ [degrees]")
        bottom.set_ylabel("residual [$\\sigma$]")
        bottom.set_title("minus the fit (dots), the model (crosses)", fontsize=8)
    _compact(fig)
    add_credit(fig, CREDIT)
    label_status(fig, series.status)
    return fig


def draw_extrapolation(
    patterns: dict, measured: dict, model: dict, nist: float
) -> Figure:
    """a per reflection of the shown specimen against the Nelson-Riley
    function, measured and NIST's model by the same method, with their
    lines, NIST's refined and the certified a."""
    series = diffraction_pattern_series(patterns[SHOWN])
    fig, ax = plt.subplots(figsize=(6.0, 4.0), constrained_layout=True)
    ends = np.array([0.0, 2.9])
    for analysis, colour, marker, style, name in (
        (
            measured[SHOWN],
            COLOURS[0],
            "o",
            "--",
            f"measured, {SHOWN} [{series.status}]",
        ),
        (
            model[SHOWN],
            COLOURS[2],
            "s",
            ":",
            "NIST's model, same method [simulated]",
        ),
    ):
        x = nelson_riley([p.theta for p in analysis.peaks])
        a = np.array([peak_lattice_parameter(p) for p in analysis.peaks])
        err = np.array([p.a_error for p in analysis.peaks])
        used = np.array([p.two_theta > LOWEST for p in analysis.peaks])
        ax.errorbar(
            x[used],
            a[used],
            yerr=err[used],
            fmt=marker,
            ms=4,
            mfc=colour if marker == "o" else "none",
            color=colour,
            capsize=2,
            label=name,
        )
        line = extrapolate(analysis.peaks)
        ax.plot(
            ends,
            line.at(ends),
            style,
            color=colour,
            lw=1.2,
            label=f"line, {name.split(' [')[0]} [simulated]",
        )
    ax.axhline(
        nist, color=COLOURS[3], lw=1.0, label="NIST's refined a (mean, 20.85 °C)"
    )
    ax.axhline(
        CERTIFIED_A,
        color="0.3",
        lw=1.0,
        ls="-.",
        label=f"certified a ({CERTIFIED_T} °C)",
    )
    ax.set_xlim(*ends)
    ax.set_ylim(4.15520, 4.15690)
    ax.ticklabel_format(axis="y", useOffset=False)
    ax.set_xlabel("Nelson-Riley function of θ [dimensionless], 0 at θ = 90°")
    ax.set_ylabel("lattice parameter a [Å]")
    ax.set_title(
        f"a per reflection above 2θ = {LOWEST:.0f}°, extrapolated to θ = 90°",
        fontsize=10,
    )
    ax.legend(fontsize=6.5, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2)
    _compact(fig)
    add_credit(fig, CREDIT)
    label_status(fig, series.status)
    return fig


def draw_specimens(patterns: dict, measured_a, model_a, nist_a, slopes: dict) -> Figure:
    """Left: the extrapolated a of each specimen, measured and NIST's
    model, NIST's refined a, and the certified band. Right: the slope
    against the displacement function per specimen against its displacement."""
    series = diffraction_pattern_series(patterns[SHOWN])
    fig, (left, right) = plt.subplots(
        1,
        2,
        figsize=(6.0, 3.3),
        constrained_layout=True,
        gridspec_kw={"width_ratios": [1.5, 1.0]},
    )
    index = np.arange(len(SPECIMENS))
    left.axhspan(
        CERTIFIED_A - CERTIFIED_U,
        CERTIFIED_A + CERTIFIED_U,
        color="0.88",
        label=f"certified a ± U (k = 2), {CERTIFIED_T} °C",
    )
    left.plot(
        index,
        measured_a,
        "o",
        ms=4,
        color=COLOURS[0],
        label=f"measured [{series.status}]",
    )
    left.plot(
        index,
        model_a,
        "s",
        ms=4,
        mfc="none",
        color=COLOURS[2],
        label="NIST's model, same method [simulated]",
    )
    left.plot(
        index,
        nist_a,
        "x",
        ms=4,
        color=COLOURS[3],
        label="NIST's refined a (CIF), 20.85 °C",
    )
    left.set_xticks(index, SPECIMENS, rotation=90, fontsize=6.5)
    left.set_ylim(4.15640, 4.15695)
    left.ticklabel_format(axis="y", useOffset=False)
    left.set_xlabel("specimen (bottle, letter) [label]")
    left.set_ylabel("lattice parameter a [Å]")
    left.set_title("a per specimen", fontsize=10)
    # Between the specimens and the certified band, clear of both.
    left.legend(fontsize=6.5, loc="center right", bbox_to_anchor=(1.0, 0.42))

    disp = slopes["displacement"]
    right.plot(
        disp,
        slopes["slopes"],
        "o",
        ms=4,
        color=COLOURS[0],
        label=f"measured [{series.status}]",
    )
    ends = np.array([-0.15, -0.03])
    right.plot(
        ends,
        slopes["coefficient"] * ends + slopes["offset"],
        "--",
        color=COLOURS[1],
        lw=1.2,
        label="fitted line [simulated]",
    )
    right.plot(
        ends,
        slopes["predicted"] * ends,
        ":",
        color=COLOURS[2],
        lw=1.4,
        label="first order a s/R [simulated]",
    )
    right.set_xlabel("displacement s refined by NIST [mm]")
    right.set_ylabel("slope against cos²θ/sin θ [Å]")
    right.set_title("the slope follows the displacement", fontsize=10)
    right.legend(fontsize=6.5, loc="upper center", bbox_to_anchor=(0.5, -0.3))
    _compact(fig)
    add_credit(fig, CREDIT)
    label_status(fig, series.status)
    return fig


def bragg_exercise() -> None:
    """Exercise 1: where the 100 and 510 reflections of a = 4.1568 angstrom
    lie for Cu K-alpha-1, and how far K-alpha-2 lies from each."""
    a, wavelength, ratio = 4.1568, 1.5406, 1.00248
    for hkl in ((1, 0, 0), (5, 1, 0)):
        d = plane_spacing(a, hkl)
        one = float(bragg_two_theta(d, wavelength))
        two = float(bragg_two_theta(d, wavelength * ratio))
        name = "(" + "".join(map(str, hkl)) + ")"
        print(f"{name} spacing d: {d:.4f} A")
        print(f"{name} K-alpha-1 peak at 2theta: {one:.3f} deg")
        print(f"{name} K-alpha-2 peak above it by: {two - one:.3f} deg")


def displacement_exercise() -> None:
    """Exercise 2: the shift of two peaks by a displacement of -0.1 mm on a
    circle of 217.5 mm, and the error of a it gives."""
    s, radius = -0.1, 217.5
    for name, two_theta in (("low-angle", 21.36), ("high-angle", 141.78)):
        shift = float(displacement_shift(two_theta, s, radius))
        theta = np.radians(two_theta) / 2
        error = 1e6 * s / radius * float(displacement_function(theta))
        print(f"{name} peak at 2theta: {two_theta} deg")
        print(f"{name} peak, its shift: {shift:+.4f} deg")
        print(f"{name} peak, error of a: {error:+.0f} ppm")


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    patterns = load_patterns()
    specimens = load_specimens()
    measured, model = analyse_all(patterns)
    nist_a = np.array([specimens[s]["cell_length_a_angstrom"] for s in SPECIMENS])
    nist = float(nist_a.mean())

    experiment.number("specimens", len(SPECIMENS))
    experiment.number("points", patterns[SHOWN].two_theta.size)
    experiment.number("temperature", specimens[SHOWN]["temperature_c"], ".2f")
    experiment.number("wavelength", WAVELENGTH, ".7f")
    experiment.number("certified", CERTIFIED_A, ".6f")
    experiment.number("certified-u", CERTIFIED_U, ".6f")
    experiment.number("certified-u-ppm", CERTIFIED_U / CERTIFIED_A * 1e6, ".0f")
    experiment.number("radius", RADIUS, ".1f")
    experiment.number("certified-temperature", CERTIFIED_T, ".1f")

    checks = method_check(experiment, patterns[SHOWN], measured[SHOWN])
    experiment.number("synthetic-plain", checks[(0.0, "Nelson-Riley")], "+.1f")
    experiment.number(
        "synthetic-nr", checks[(SYNTHETIC_DISPLACEMENT, "Nelson-Riley")], "+.1f"
    )
    experiment.number(
        "synthetic-disp", checks[(SYNTHETIC_DISPLACEMENT, "displacement")], "+.1f"
    )
    experiment.number("synthetic-s", SYNTHETIC_DISPLACEMENT, ".1f")

    reflection_table(experiment, measured[SHOWN])
    index = indexing(measured)
    experiment.number("max-offset", index["max-offset"], ".3f")
    experiment.number("low-offset", index["low-offset"], "+.3f")
    experiment.number("high-offset", index["high-offset"], "+.3f")
    chi2 = [p.reduced_chi2 for p in measured[SHOWN].peaks]
    high = [p.reduced_chi2 for p in measured[SHOWN].peaks if p.two_theta > LOWEST]
    experiment.number("chi2-lowest", chi2[0], ".0f")
    experiment.number("chi2-high-max", max(high), ".1f")
    experiment.number("ratio", measured[SHOWN].ratio, ".7f")
    experiment.number("share", measured[SHOWN].share, ".3f")

    single = single_reflections(measured)
    experiment.number("a-first", single["first"], ".6f")
    experiment.number("a-last", single["last"], ".6f")
    experiment.number("a-drift-ppm", ppm(single["last"], single["first"]), ".0f")

    shown_line = extrapolate(measured[SHOWN].peaks)
    experiment.number("shown-a0", shown_line.a0, ".6f")
    experiment.number("shown-a0-err", shown_line.a0_error, ".7f")
    experiment.number(
        "shown-warnings",
        "; ".join(shown_line.warnings) if shown_line.warnings else "none",
    )
    experiment.number("used", sum(p.two_theta > LOWEST for p in measured[SHOWN].peaks))
    experiment.number("lowest", LOWEST, ".0f")

    measured_a = intercepts(measured)
    model_a = intercepts(model)
    mean, sd, sem = summary(measured_a)
    model_mean = float(model_a.mean())
    experiment.number("a-mean", mean, ".6f")
    experiment.number("a-sd", sd, ".6f")
    experiment.number("a-sd-ppm", sd / CERTIFIED_A * 1e6, ".1f")
    experiment.number("a-sem-ppm", sem / CERTIFIED_A * 1e6, ".1f")
    experiment.number("a-min", measured_a.min(), ".6f")
    experiment.number("a-max", measured_a.max(), ".6f")
    experiment.number("model-mean", model_mean, ".6f")
    experiment.number("nist", nist, ".6f")

    errors = error_check(experiment, measured, model)
    experiment.number("rho-measured", errors["measured"]["rho1"], "+.2f")
    experiment.number("rho-model", errors["model"]["rho1"], "+.2f")
    experiment.number("rho-difference", errors["difference"]["rho1"], "+.2f")
    experiment.number("rho-band", errors["band"], ".2f")
    experiment.number("stderr-measured", errors["measured"]["stderr"], ".1f")
    experiment.number("stderr-model", errors["model"]["stderr"], ".1f")
    experiment.number("count-sd", errors["difference"]["sd"], ".1f")

    pairing = bottle_check(
        experiment,
        {
            "a": ("extrapolated a", ppm(measured_a, CERTIFIED_A)),
            "difference": ("measured minus model", ppm(measured_a, model_a)),
        },
    )
    for name in ("a", "difference"):
        found = pairing[name]
        experiment.number(f"bottle-correlation-{name}", found["correlation"], "+.2f")
        experiment.number(f"bottle-f-{name}", found["f"], ".2f")
        experiment.number(f"bottle-p-{name}", found["p"], ".2f")
        experiment.number(f"sem-bottles-{name}", found["sem-bottles"], ".2f")
    # The comparisons use the larger of the two standard errors of the mean,
    # so that they hold whether the specimens of a bottle are independent
    # or not.
    sem_used = max(sem / CERTIFIED_A * 1e6, pairing["a"]["sem-bottles"])
    difference_sem = max(
        errors["difference"]["sem"], pairing["difference"]["sem-bottles"]
    )
    experiment.number("sem-used", sem_used, ".1f")
    experiment.number("difference-sem", difference_sem, ".2f")
    experiment.number("above-measured", errors["measured"]["above"])
    experiment.number("above-model", errors["model"]["above"])

    slopes = displacement_slopes(measured, specimens)
    experiment.number("slope-correlation", slopes["correlation"], ".4f")
    experiment.number("slope-coefficient", slopes["coefficient"], ".4f")
    experiment.number("slope-predicted", slopes["predicted"], ".4f")
    experiment.number("slope-ratio", slopes["coefficient"] / slopes["predicted"], ".2f")
    experiment.number("nr-correlation", slopes["nr-correlation"], ".2f")

    bias = ppm(model_mean, nist)
    difference = ppm(mean, model_mean)
    gap = ppm(mean, CERTIFIED_A)
    nist_gap = ppm(nist, CERTIFIED_A)
    experiment.number("bias", bias, "+.1f")
    experiment.number("difference", difference, "+.1f")
    experiment.number("difference-sigmas", difference / difference_sem, ".0f")
    experiment.number("gap", gap, "+.1f")
    experiment.number("gap-u", abs(gap) / (CERTIFIED_U / CERTIFIED_A * 1e6), ".1f")
    experiment.number("gap-sem", abs(gap) / sem_used, ".0f")
    experiment.number("nist-gap", nist_gap, "+.1f")
    corrected = mean - (model_mean - nist)
    experiment.number("corrected", corrected, ".6f")
    experiment.number("corrected-gap", ppm(corrected, CERTIFIED_A), "+.1f")

    spread = sensitivity(experiment, measured, model, nist)
    experiment.number("gap-low", spread["gap-low"], "+.1f")
    experiment.number("gap-high", spread["gap-high"], "+.1f")
    experiment.number("bias-low", spread["bias-low"], "+.1f")
    experiment.number("bias-high", spread["bias-high"], "+.1f")
    experiment.number("difference-max", spread["difference-max"], ".1f")
    experiment.number("gap-spread", spread["gap-high"] - spread["gap-low"], ".1f")
    budget(
        experiment,
        {
            "count-sd": errors["difference"]["sd"],
            "sd": sd / CERTIFIED_A * 1e6,
            "sem": sem / CERTIFIED_A * 1e6,
            "sem-bottles": pairing["a"]["sem-bottles"],
            "difference": difference,
            "gap-spread": spread["gap-high"] - spread["gap-low"],
            "bias": bias,
            "nist-gap": nist_gap,
            "gap": gap,
        },
    )

    experiment.figure("fig-pattern", partial(draw_pattern, patterns, measured))
    experiment.figure("fig-peaks", partial(draw_peaks, patterns, measured))
    experiment.figure(
        "fig-extrapolation",
        partial(draw_extrapolation, patterns, measured, model, nist),
    )
    experiment.figure(
        "fig-specimens",
        partial(draw_specimens, patterns, measured_a, model_a, nist_a, slopes),
    )

    with experiment.capture("bragg-exercise"):
        bragg_exercise()
    with experiment.capture("displacement-exercise"):
        displacement_exercise()
    return experiment


if __name__ == "__main__":
    main(run)
