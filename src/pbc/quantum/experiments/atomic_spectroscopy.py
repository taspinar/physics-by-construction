"""The experiment of the lesson "Atomic spectroscopy lab".

The level model of hydrogen with the reduced mass (``pbc.quantum.hydrogen``),
checked on the grid of the quantum course, against a measured spectrum (the
committed sample of the card ``sdss-balmer-spectrum``): the SDSS co-added
spectrum of a starburst galaxy, with four Balmer lines of hydrogen and nine
forbidden lines of other elements. The experiment fits the lines, reads their
widths, calibrates the redshift on the forbidden lines, infers the Rydberg
constant of hydrogen from the Balmer lines, compares it with the laboratory
value, and checks the assumptions of its uncertainty. Run it as a program to
write the figures and the numbers of the page:

    uv run --locked --no-dev python -m \\
        pbc.quantum.experiments.atomic_spectroscopy out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.data import SAMPLES_DIR
from pbc.data.adapters import sdss_flux_series
from pbc.data.plotting import COLOURS, add_credit, label_status
from pbc.data.reference.sdss_balmer import (
    BALMER,
    C_KMS,
    DLOGLAM,
    FORBIDDEN,
    ME_OVER_MP,
    R_H,
    R_INF,
    Analysis,
    Spectrum,
    analyse,
    bohr_lab_rydberg,
    good,
    load,
    pipeline_value,
    rydberg,
    sensitivity,
)
from pbc.experiment import Experiment, main
from pbc.quantum.hydrogen import (
    level,
    radial_levels,
    reduced_mass_ratio,
    richardson,
)

DATASET = "sdss-balmer-spectrum"
# region: choices
GRID = {"r_max": 250.0, "n_cells": 10000}  # a_0; h = 0.025 a_0, then h / 2
LEVELS = 6  # n = 1 to 6: the upper levels of the four Balmer lines and below
GAS_TEMPERATURE = 1.0e4  # K, assumed for the thermal width, not measured
# endregion: choices
BOLTZMANN = 1.380649e-23  # J/K
HYDROGEN_MASS = 1.6735575e-27  # kg, the hydrogen atom
CREDIT = (
    "Data: Sloan Digital Sky Survey, spectrum spec-1949-53433-0480.fits (plate "
    "1949, MJD 53433, fibre 480), Data Release 17, public domain under the "
    "current SDSS data policy; the SDSS acknowledgement is on the page. Line "
    "fits, calibration and Rydberg formula: this lesson's code, not part of the "
    "record."
)
MARKERS = ("o", "s", "^", "D")
# The labels of fig-calibration: one per ion, placed above its lines.
CALIBRATION_LABELS = (
    ("[Ne III]", ("[Ne III] 3870",), 6),
    ("[O III]", ("[O III] 4960", "[O III] 5008"), 6),
    ("[O I]", ("[O I] 6302",), 18),
    ("[N II]", ("[N II] 6550", "[N II] 6585"), 22),
    ("[S II]", ("[S II] 6718", "[S II] 6733"), 6),
    ("[Ar III]", ("[Ar III] 7138",), 6),
)


def load_spectrum() -> Spectrum:
    """The committed sample: every pixel of the co-added spectrum."""
    return load(SAMPLES_DIR / DATASET)


def velocity_width(sigma: float, centre: float) -> float:
    """A Gaussian width in wavelength as a velocity [km/s]."""
    return sigma / centre * C_KMS


def instrument_width(spectrum: Spectrum, centre: float) -> float:
    """The line-spread sigma of the spectrograph at ``centre`` [km/s]: the
    pipeline's ``wdisp`` in pixels times the velocity width of a pixel."""
    k = int(np.argmin(np.abs(spectrum.wavelength - centre)))
    return float(spectrum.wdisp[k] * DLOGLAM * np.log(10.0) * C_KMS)


def thermal_width(temperature: float, mass: float) -> float:
    """sqrt(k T / m), the thermal velocity sigma along the line of sight [km/s]."""
    return float(np.sqrt(BOLTZMANN * temperature / mass) / 1e3)


# The record without a model.


def record_landmarks(spectrum: Spectrum) -> dict:
    """What the sample shows without a model: its pixels, the masked ones,
    the wavelength range, the signal-to-noise, and the pipeline's values."""
    series = sdss_flux_series(spectrum)
    ok = good(spectrum)
    return {
        "series": series,
        "pixels": int(series.x.size),
        "good": int(ok.sum()),
        "masked": int((spectrum.and_mask != 0).sum()),
        "lowest": float(series.x.min()),
        "highest": float(series.x.max()),
        "snr": float(np.median(series.y / series.sigma)),
        "pipeline-z": float(pipeline_value(spectrum, "Z")),
        "pixel-kms": float(DLOGLAM * np.log(10.0) * C_KMS),
    }


# The model on the grid.


def level_check(experiment: Experiment) -> dict:
    """The radial equation of hydrogen with the reduced mass on the grid of
    the quantum course, on two steps, against E_n = -(mu/m_e) / 2 n^2."""
    mu = reduced_mass_ratio(ME_OVER_MP)
    n = np.arange(1, LEVELS + 1)
    exact = level(n, mu)
    coarse = radial_levels(0, LEVELS, GRID["r_max"], GRID["n_cells"], mu)
    fine = radial_levels(0, LEVELS, GRID["r_max"], 2 * GRID["n_cells"], mu)
    extrapolated = richardson(coarse, fine)
    p_coarse = radial_levels(1, LEVELS - 1, GRID["r_max"], GRID["n_cells"], mu)
    p_fine = radial_levels(1, LEVELS - 1, GRID["r_max"], 2 * GRID["n_cells"], mu)
    p_extrapolated = richardson(p_coarse, p_fine)
    error_coarse = coarse / exact - 1
    error_fine = fine / exact - 1
    rows = []
    for k in range(LEVELS):
        p_error = "" if k == 0 else f"{p_coarse[k - 1] / exact[k] - 1:.2e}"
        rows.append((str(n[k]), exact[k], error_coarse[k], error_fine[k], p_error))
    experiment.table(
        "level-check",
        rows,
        columns=[
            ("n", "", "s"),
            ("E_n = -(mu/m_e)/2n^2", "Hartree", ".8f"),
            ("grid error, l = 0, h", "relative", ".2e"),
            ("grid error, l = 0, h/2", "relative", ".2e"),
            ("grid error, l = 1, h", "relative", "s"),
        ],
        caption="The radial equation of hydrogen with the reduced mass on the grid "
        "of the quantum course (step h = 0.025 Bohr radii and half of it, a wall "
        "at 250 Bohr radii), against the level formula.",
    )
    # The Balmer terms (E_n - E_2) / (-E_1) = 1/4 - 1/n^2 from the levels.
    balmer = (extrapolated[2:] - extrapolated[1]) / (-extrapolated[0])
    terms = 0.25 - 1.0 / n[2:] ** 2
    return {
        "ratio": float(np.min(error_coarse / error_fine)),
        "ratio-high": float(np.max(error_coarse / error_fine)),
        "worst-coarse": float(np.max(np.abs(error_coarse))),
        "worst-extrapolated": float(
            max(
                np.max(np.abs(extrapolated / exact - 1)),
                np.max(np.abs(p_extrapolated / exact[1:] - 1)),
            )
        ),
        "worst-term": float(np.max(np.abs(balmer / terms - 1))),
        "degeneracy": float(np.max(np.abs(p_extrapolated / extrapolated[1:] - 1))),
    }


# The lines.


def line_table(experiment: Experiment, spectrum: Spectrum, analysis: Analysis) -> dict:
    """Every fitted line: its centre with the scaled error, its width, the
    instrument's width there, the width of the gas, the fit's chi-square."""
    rows, intrinsic = [], {}
    order = list(BALMER.values()) + list(FORBIDDEN)
    for name in order:
        line = analysis.lines[name]
        observed = velocity_width(line.sigma, line.centre)
        instrument = instrument_width(spectrum, line.centre)
        gas = float(np.sqrt(observed**2 - instrument**2))
        intrinsic[name] = gas
        rows.append(
            (
                name,
                line.centre,
                line.error,
                observed,
                instrument,
                gas,
                line.reduced_chi2,
            )
        )
    experiment.table(
        "lines",
        rows,
        columns=[
            ("line", "", "s"),
            ("observed centre", "Angstrom", ".3f"),
            ("scaled error", "Angstrom", ".3f"),
            ("width sigma", "km/s", ".0f"),
            ("instrument sigma", "km/s", ".0f"),
            ("gas sigma", "km/s", ".0f"),
            ("reduced chi-square", "", ".1f"),
        ],
        caption="The four Balmer lines and the nine forbidden lines, each fitted as "
        "a Gaussian on a straight continuum (H alpha with the two [N II] lines, the "
        "[S II] doublet together); the error is scaled by the square root of the "
        "reduced chi-square where that is above one; the gas sigma removes the "
        "instrument's sigma in quadrature.",
    )
    return intrinsic


def calibration_table(experiment: Experiment, analysis: Analysis) -> None:
    """The forbidden lines' redshifts and their offsets from the calibration."""
    cal = analysis.rydberg.calibration
    rows = []
    for name, rest in FORBIDDEN.items():
        error = analysis.lines[name].error / cal.wavelength[name] * C_KMS
        rows.append(
            (name, rest, cal.wavelength[name], cal.z[name], cal.velocity(name), error)
        )
    experiment.table(
        "calibration",
        rows,
        columns=[
            ("line", "", "s"),
            ("rest wavelength", "Angstrom", ".3f"),
            ("observed", "Angstrom", ".3f"),
            ("z", "", ".7f"),
            ("offset from z(lambda)", "km/s", "+.1f"),
            ("error", "km/s", ".1f"),
        ],
        caption="The forbidden lines, their laboratory vacuum wavelengths (the SDSS "
        "line list), their redshifts, and their velocities about the fitted "
        "calibration z(lambda), with the scaled error of each line.",
    )


def rydberg_table(experiment: Experiment, analysis: Analysis) -> None:
    """Each Balmer line: its observed and calibrated rest wavelength, its R,
    and its offset from the Rydberg formula with R_H."""
    ryd = analysis.rydberg
    rows = []
    for n, name in BALMER.items():
        observed = analysis.lines[name].centre
        rest = observed / (1 + float(ryd.calibration.at(observed)))
        per = ryd.per_line[n]
        rows.append(
            (
                name,
                str(n),
                observed,
                rest,
                per,
                ryd.per_line_err[n],
                (R_H / per - 1) * C_KMS,
            )
        )
    experiment.table(
        "rydberg",
        rows,
        columns=[
            ("line", "", "s"),
            ("n", "", "s"),
            ("observed", "Angstrom", ".3f"),
            ("rest, calibrated", "Angstrom", ".3f"),
            ("R from the line", "1/m", ",.0f"),
            ("error", "1/m", ",.0f"),
            ("offset from R_H", "km/s", "+.1f"),
        ],
        caption="Each Balmer line's rest wavelength from the calibration z(lambda), "
        "its Rydberg constant from 1/lambda = R (1/4 - 1/n^2), and how far it lies "
        "from the line the formula gives with the laboratory R_H.",
    )


# Are the errors honest?


def neighbour_correlation(normalised: np.ndarray) -> float:
    """The correlation of each residual with the next pixel's."""
    return float(np.corrcoef(normalised[:-1], normalised[1:])[0, 1])


def independence_table(experiment: Experiment, analysis: Analysis) -> dict:
    """For each fit window: the pixels, the reduced chi-square, and the
    correlation of neighbouring normalised residuals against the band
    2 / sqrt(N) that independent residuals would fill."""
    rows, found = [], {}
    for fit in analysis.fits:
        normalised = fit.result.residuals / fit.error
        rho = neighbour_correlation(normalised)
        band = 2 / np.sqrt(normalised.size)
        name = " + ".join(fit.names)
        found[name] = (fit.result.reduced_chi2, rho, band)
        rows.append(
            (
                name,
                int(normalised.size),
                fit.result.reduced_chi2,
                rho,
                band,
                "yes" if abs(rho) < band else "no",
            )
        )
    experiment.table(
        "independence",
        rows,
        columns=[
            ("fit", "", "s"),
            ("pixels", "", "d"),
            ("reduced chi-square", "", ".1f"),
            ("neighbour correlation", "", "+.2f"),
            ("band", "", ".2f"),
            ("inside", "", "s"),
        ],
        caption="The residuals of each line fit over the pixel error: the "
        "correlation of every residual with its neighbour's, and the band of "
        "plus or minus 2 / sqrt(N) that independent residuals would fill.",
    )
    return found


def sensitivity_table(experiment: Experiment, spectrum: Spectrum) -> dict:
    """R with the other choices of the reference module."""
    variants = sensitivity(spectrum)
    rows = [
        (name, v.r, v.r_err, v.chi2, v.calibration.chi2, v.calibration.dof)
        for name, v in variants.items()
    ]
    experiment.table(
        "sensitivity",
        rows,
        columns=[
            ("choice", "", "s"),
            ("R", "1/m", ",.0f"),
            ("error", "1/m", ",.0f"),
            ("chi-square of the lines", "", ".2f"),
            ("chi-square of the calibration", "", ".1f"),
            ("its degrees of freedom", "", "d"),
        ],
        caption="The Rydberg constant when one choice changes: the fit window, "
        "the lines used, the calibration. A sensitivity range of the choices, not "
        "an uncertainty interval.",
    )
    return variants


# The figures.


def draw_spectrum(spectrum: Spectrum, analysis: Analysis) -> Figure:
    """The whole spectrum as released, the masked pixels marked, the fitted
    lines named."""
    series = sdss_flux_series(spectrum)
    masked = spectrum.and_mask != 0
    fig, ax = plt.subplots(figsize=(6.8, 3.5), constrained_layout=True)
    ax.plot(
        series.x,
        series.y,
        color=COLOURS[0],
        lw=0.5,
        label="measured flux density, every pixel [calibrated]",
    )
    ax.plot(
        series.x[masked],
        series.y[masked],
        ls="none",
        marker="x",
        ms=3,
        color="0.35",
        label="pixels the pipeline masks (bright sky)",
    )
    for k, name in enumerate(BALMER.values()):
        centre = analysis.lines[name].centre
        ax.annotate(
            name,
            (centre, 0.96 - 0.07 * (k % 2)),
            xycoords=("data", "axes fraction"),
            ha="center",
            va="top",
            fontsize=7,
            color=COLOURS[1],
        )
    for name in ("[Ne III] 3870", "[O III] 5008", "[S II] 6718"):
        centre = analysis.lines[name].centre
        ax.annotate(
            name,
            (centre, 0.80),
            xycoords=("data", "axes fraction"),
            ha="center",
            va="top",
            fontsize=6.5,
            color="0.25",
        )
    ax.set_yscale("log")
    ax.set_ylim(8, 30000)
    ax.set_xlabel("observed vacuum wavelength, heliocentric [Angstrom]")
    ax.set_ylabel("flux density [1e-17 erg/s/cm2/A]", fontsize=8)
    ax.set_title(
        "SDSS spectrum 1949-53433-0480 of a starburst galaxy (log scale)",
        fontsize=10,
    )
    ax.legend(fontsize=7, loc="lower center", ncols=2)
    add_credit(fig, CREDIT)
    label_status(fig, "calibrated")
    return fig


def draw_balmer_fits(analysis: Analysis) -> Figure:
    """Each Balmer line's pixels with one sigma, the fitted Gaussian on a
    straight continuum, and the residuals over the pixel error."""
    fig = plt.figure(figsize=(6.8, 4.6), constrained_layout=True)
    grid = fig.add_gridspec(2, 4, height_ratios=(1.5, 1.0))
    by_name = {name: fit for fit in analysis.fits for name in fit.names}
    for k, name in enumerate(BALMER.values()):
        ax = fig.add_subplot(grid[0, k])
        res = fig.add_subplot(grid[1, k], sharex=ax)
        fit = by_name[name]
        line = analysis.lines[name]
        x = (fit.wavelength - line.centre) / line.centre * C_KMS
        ax.errorbar(
            x,
            fit.flux,
            yerr=fit.error,
            ls="none",
            marker="o",
            ms=2,
            elinewidth=0.6,
            color=COLOURS[0],
            label="measured pixels [processed]",
        )
        dense = np.linspace(np.log10(fit.lo), np.log10(fit.hi), 240)
        ax.plot(
            (10**dense - line.centre) / line.centre * C_KMS,
            fit.model(dense),
            color=COLOURS[1],
            ls="--",
            lw=1.0,
            label="fit: Gaussian on a line",
        )
        ax.set_ylim(top=1.4 * float(np.max(fit.flux)))
        ax.set_title(name, fontsize=9)
        ax.tick_params(labelsize=7, labelbottom=False)
        unit = "[1e-17 cgs/A]"
        ax.set_ylabel("flux density " + unit if k == 0 else unit, fontsize=7)
        res.plot(
            x,
            fit.result.residuals / fit.error,
            ls="none",
            marker=MARKERS[k],
            ms=2.5,
            color=COLOURS[2],
        )
        res.axhline(0, color="0.4", lw=0.8)
        res.set_title("residual", fontsize=8)
        res.set_xlabel("velocity [km/s]", fontsize=7)
        res.set_ylabel("residual [sigma]" if k == 0 else "[sigma]", fontsize=7)
        res.tick_params(labelsize=7)
        if k == 0:
            ax.legend(fontsize=5.5, loc="upper left")
    add_credit(fig, CREDIT)
    label_status(fig, "processed")
    return fig


def draw_calibration(analysis: Analysis) -> Figure:
    """The forbidden lines' velocities about z0, with the fitted z(lambda)
    and the single z."""
    ryd = analysis.rydberg
    cal = ryd.calibration
    flat = rydberg(analysis.lines, ryd.levels, slope=False).calibration
    names = list(FORBIDDEN)
    observed = np.array([cal.wavelength[n] for n in names])
    z = np.array([cal.z[n] for n in names])
    zerr = np.array([analysis.lines[n].error / FORBIDDEN[n] for n in names])
    z0 = float(cal.params[0])
    to_kms = C_KMS / (1 + z0)
    fig, (ax, res) = plt.subplots(
        2,
        1,
        figsize=(6.8, 4.6),
        sharex=True,
        constrained_layout=True,
        gridspec_kw={"height_ratios": (1.5, 1.0)},
    )
    ax.errorbar(
        observed,
        (z - z0) * to_kms,
        yerr=zerr * to_kms,
        ls="none",
        marker="o",
        ms=4,
        color=COLOURS[0],
        label="forbidden lines, fitted centres [processed], scaled 1 sigma",
    )
    velocity = (z - z0) * to_kms
    for text, members, dy in CALIBRATION_LABELS:
        k = [names.index(m) for m in members]
        ax.annotate(
            text,
            (float(np.mean(observed[k])), float(np.max(velocity[k]))),
            xytext=(0, dy),
            textcoords="offset points",
            ha="center",
            fontsize=6.5,
        )
    ends = np.array([3800.0, 7400.0])
    ax.plot(
        ends,
        (cal.at(ends) - z0) * to_kms,
        color=COLOURS[1],
        ls="--",
        label="calibration z(lambda), a straight line",
    )
    ax.plot(
        ends,
        np.full(2, (float(flat.params[0]) - z0) * to_kms),
        color="0.45",
        ls=":",
        label="one z for all lines",
    )
    ax.set_ylabel("velocity about z0 [km/s]", fontsize=8)
    ax.set_ylim(-22, 22)
    ax.set_title("The redshift of the forbidden lines", fontsize=10)
    ax.legend(fontsize=6.5, loc="lower right")
    res.errorbar(
        observed,
        [cal.velocity(n) for n in names],
        yerr=zerr * to_kms,
        ls="none",
        marker="s",
        ms=4,
        color=COLOURS[2],
    )
    res.axhline(0, color="0.4", lw=0.8)
    res.set_xlabel("observed wavelength [Angstrom]")
    res.set_ylabel("residual [km/s]", fontsize=8)
    fig.align_ylabels((ax, res))
    res.set_title("Offsets about the calibration", fontsize=9)
    add_credit(fig, CREDIT)
    label_status(fig, "processed")
    return fig


def draw_rydberg_law(analysis: Analysis) -> Figure:
    """The rest wavenumber of each Balmer line against 1/4 - 1/n^2 with the
    Rydberg formula, and each line's offset from the formula with R_H."""
    ryd = analysis.rydberg
    flat = rydberg(analysis.lines, ryd.levels, slope=False)
    levels = np.array(ryd.levels)
    terms = 0.25 - 1.0 / levels**2
    per = np.array([ryd.per_line[n] for n in levels])
    err = np.array([ryd.per_line_err[n] for n in levels])
    fig, (ax, res) = plt.subplots(
        1, 2, figsize=(6.8, 3.2), constrained_layout=True, width_ratios=(1.0, 1.3)
    )
    ax.plot(
        terms,
        per * terms / 1e6,
        ls="none",
        marker="o",
        ms=5,
        color=COLOURS[0],
        label="Balmer lines, calibrated [processed]",
    )
    ends = np.array([0.0, 0.25])
    ax.plot(
        ends,
        ends * ryd.r / 1e6,
        color=COLOURS[1],
        ls="--",
        lw=1.0,
        label="Rydberg formula, fitted R",
    )
    for n, x, y in zip(levels, terms, per * terms / 1e6, strict=True):
        ax.annotate(
            "n = " + str(n),
            (x, y),
            xytext=(-30, 3) if n == 5 else (4, -9),
            textcoords="offset points",
            fontsize=6.5,
        )
    ax.set_xlim(0, 0.28)
    ax.set_xlabel("1/4 - 1/n^2 [1]")
    ax.set_ylabel("rest wavenumber [1/um]", fontsize=8)
    ax.set_title("The Balmer series", fontsize=10)
    ax.legend(fontsize=6.5, loc="lower right")

    to_kms = C_KMS
    res.errorbar(
        levels,
        (R_H / per - 1) * to_kms,
        yerr=err / per * to_kms,
        ls="none",
        marker="o",
        ms=4,
        color=COLOURS[0],
        label="calibrated z(lambda)",
    )
    res.plot(
        levels + 0.12,
        [(R_H / flat.per_line[n] - 1) * to_kms for n in levels],
        ls="none",
        marker="s",
        ms=4,
        mfc="none",
        color="0.45",
        label="one z",
    )
    span = np.array([2.7, 6.3])
    res.plot(
        span,
        np.full(2, (R_H / ryd.r - 1) * to_kms),
        color=COLOURS[1],
        ls="--",
        label="fitted R",
    )
    res.plot(
        span,
        np.full(2, (R_H / bohr_lab_rydberg(ryd.levels) - 1) * to_kms),
        color=COLOURS[2],
        ls="-.",
        label="laboratory H",
    )
    res.axhline(0, color="0.3", lw=0.8, label="R_H (CODATA)")
    res.set_xticks(levels, [f"n = {n}" for n in levels])
    res.set_xlabel("upper level of the line [1]")
    res.set_ylabel("residual from R_H [km/s]", fontsize=8)
    res.set_title("Offsets from the formula with R_H", fontsize=10)
    res.set_ylim(-34, 6)
    res.legend(fontsize=6, loc="lower center", ncols=3)
    add_credit(fig, CREDIT)
    label_status(fig, "processed")
    return fig


# The exercises.


def proton_exercise() -> None:
    """Exercise 1: the electron-proton mass ratio that the measured R implies,
    if R_inf is known and the velocity offset is ignored."""
    measured, error = 10968065.0, 41.0
    ratio = R_INF / measured - 1
    print(f"m_e/m_p from R: {ratio:.4e} (CODATA {ME_OVER_MP:.4e})")
    print(f"m_p/m_e from R: {1 / ratio:.0f} (CODATA {1 / ME_OVER_MP:.0f})")
    print(f"its error from the 41 1/m alone: {R_INF / measured**2 * error / ratio:.1%}")


def deuterium_exercise() -> None:
    """Exercise 2: the shift of H alpha for deuterium against the line width."""
    me_over_md = ME_OVER_MP / 1.99900750  # m_d / m_p, given
    r_d = R_INF / (1 + me_over_md)
    lam_h = 1 / (R_H * (0.25 - 1 / 9)) * 1e10
    lam_d = 1 / (r_d * (0.25 - 1 / 9)) * 1e10
    shift = lam_h - lam_d
    print(f"H alpha of hydrogen, Bohr formula: {lam_h:.2f} A")
    print(f"H alpha of deuterium, Bohr formula: {lam_d:.2f} A")
    print(f"shift to the blue: {shift:.2f} A")
    print(f"as a velocity: {shift / lam_h * C_KMS:.0f} km/s")


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    spectrum = load_spectrum()

    found = record_landmarks(spectrum)
    experiment.number("pixels", found["pixels"], ",d")
    experiment.number("good", found["good"], ",d")
    experiment.number("masked", found["masked"])
    experiment.number("lowest", found["lowest"], ".0f")
    experiment.number("highest", found["highest"], ".0f")
    experiment.number("snr", found["snr"], ".0f")
    experiment.number("pixel-kms", found["pixel-kms"], ".1f")

    check = level_check(experiment)
    experiment.number("level-worst", check["worst-coarse"], ".1e")
    experiment.number("level-ratio-low", check["ratio"], ".2f")
    experiment.number("level-ratio-high", check["ratio-high"], ".2f")
    experiment.number("level-bound", "1e-7")
    experiment.number("mass-ratio", reduced_mass_ratio(ME_OVER_MP), ".6f")

    analysis = analyse(spectrum)
    ryd = analysis.rydberg
    cal = ryd.calibration
    intrinsic = line_table(experiment, spectrum, analysis)
    balmer_gas = [intrinsic[name] for name in BALMER.values()]
    forbidden_gas = [intrinsic[name] for name in FORBIDDEN]
    experiment.number("gas-low", min(balmer_gas + forbidden_gas), ".0f")
    experiment.number("gas-high", max(balmer_gas + forbidden_gas), ".0f")
    experiment.number("gas-balmer-low", min(balmer_gas), ".0f")
    experiment.number("gas-balmer-high", max(balmer_gas), ".0f")
    experiment.number("thermal-h", thermal_width(GAS_TEMPERATURE, HYDROGEN_MASS), ".0f")
    experiment.number(
        "thermal-o", thermal_width(GAS_TEMPERATURE, 16 * HYDROGEN_MASS), ".0f"
    )
    experiment.number("ha-error", analysis.lines["H alpha"].error, ".3f")
    experiment.number("ha-raw-error", analysis.lines["H alpha"].centre_err, ".3f")
    experiment.number("ha-chi2", analysis.lines["H alpha"].reduced_chi2, ".1f")

    calibration_table(experiment, analysis)
    z0, z0_err = float(cal.params[0]), float(np.sqrt(cal.covariance[0, 0]))
    experiment.number("z0", z0, ".7f")
    experiment.number("z0-err", z0_err, ".7f")
    experiment.number("cz", z0 * C_KMS, ",.0f")
    experiment.number("slope", cal.slope_kms, ".1f")
    slope_err = float(np.sqrt(cal.covariance[1, 1]) / (1 + z0) * C_KMS)
    experiment.number("slope-err", slope_err, ".1f")
    experiment.number("cal-chi2", cal.chi2, ".1f")
    experiment.number("cal-dof", cal.dof)
    experiment.number("cal-birge", np.sqrt(cal.chi2 / cal.dof), ".1f")
    experiment.number(
        "pipeline-offset", (found["pipeline-z"] - z0) / (1 + z0) * C_KMS, "+.1f"
    )

    rydberg_table(experiment, analysis)
    experiment.number("r", ryd.r, ",.0f")
    experiment.number("r-err", ryd.r_err, ",.0f")
    experiment.number("r-chi2", ryd.chi2, ".2f")
    experiment.number("r-dof", ryd.dof)
    experiment.number("r-h", R_H, ",.0f")
    experiment.number("r-inf", R_INF, ",.0f")
    experiment.number("rel-h", 1e5 * ryd.relative, ".2f")
    experiment.number("rel-h-sigma", (ryd.r - R_H) / ryd.r_err, ".1f")
    lab = bohr_lab_rydberg(ryd.levels)
    experiment.number("rel-fine", 1e5 * (lab / R_H - 1), ".2f")
    experiment.number("rel-lab", 1e5 * ryd.relative_lab, ".2f")
    experiment.number("rel-lab-kms", ryd.relative_lab * C_KMS, ".1f")
    experiment.number("rel-lab-sigma", (ryd.r - lab) / ryd.r_err, ".1f")
    experiment.number("rel-inf", 1e4 * (1 - ryd.r / R_INF), ".2f")
    experiment.number("rel-inf-sigma", (R_INF - ryd.r) / ryd.r_err, ".0f")
    experiment.number("recoil", 1e4 * ME_OVER_MP, ".2f")
    flat = rydberg(analysis.lines, ryd.levels, slope=False)
    experiment.number("flat-chi2", flat.chi2, ".1f")
    experiment.number("flat-r", flat.r, ",.0f")
    experiment.number("flat-r-err", flat.r_err, ",.0f")
    experiment.number("flat-cal-chi2", flat.calibration.chi2, ".0f")
    experiment.number("flat-cal-dof", flat.calibration.dof)

    independence = independence_table(experiment, analysis)
    inside = [k for k, (_, rho, band) in independence.items() if abs(rho) < band]
    near_one = [k for k, (chi2, _, _) in independence.items() if chi2 < 1.5]
    experiment.number("near-one-inside", sum(1 for k in near_one if k in inside))
    experiment.number("near-one", len(near_one))
    experiment.number("hd-rho", independence["H delta"][1], "+.2f")
    experiment.number("oi-rho", independence["[O I] 6302"][1], "+.2f")

    variants = sensitivity_table(experiment, spectrum)
    shifts = {name: abs(v.r - ryd.r) for name, v in variants.items() if name != "one z"}
    experiment.number(
        "window-shift",
        max(shifts["window 9 A"], shifts["window 16 A"], shifts["no H delta"]),
        ".0f",
    )
    experiment.number("neiii-shift", shifts["no [Ne III]"], ".0f")

    experiment.figure("fig-spectrum", partial(draw_spectrum, spectrum, analysis))
    experiment.figure("fig-balmer-fits", partial(draw_balmer_fits, analysis))
    experiment.figure("fig-calibration", partial(draw_calibration, analysis))
    experiment.figure("fig-rydberg-law", partial(draw_rydberg_law, analysis))

    with experiment.capture("proton-exercise"):
        proton_exercise()
    with experiment.capture("deuterium-exercise"):
        deuterium_exercise()
    return experiment


if __name__ == "__main__":
    main(run)
