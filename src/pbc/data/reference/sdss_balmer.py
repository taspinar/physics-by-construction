"""SDSS spectrum of a starburst galaxy: the Balmer series and the Rydberg constant.

Status of the figure: *processed*. The SDSS pipeline's co-added spectrum is a
calibrated observation (flux- and wavelength-calibrated, vacuum wavelengths,
corrected to the heliocentric frame); this module fits a Gaussian to each
emission line on a straight continuum, calibrates the redshift on the
forbidden lines, and gives each hydrogen line's Rydberg constant from the
Balmer formula. The fitted lines and models are drawn apart from the
measurement, as models, with their residuals.

The physics: a hydrogen atom that falls from level n to level 2 emits at the
vacuum wavelength 1 / lambda = R (1/4 - 1/n^2) (Bohr, with R = R_H the
Rydberg constant of hydrogen). The galaxy recedes, so every line is observed
at (1 + z) times its rest wavelength. From the hydrogen lines alone, R and
(1 + z) appear only as the ratio (1 + z) / R: the redshift must come from
other lines. Here it comes from the forbidden lines of oxygen, nitrogen,
sulphur, neon, and argon, whose rest wavelengths are laboratory values (the
vacuum wavelengths of the SDSS line list in the FITS file's ``SPZLINE``
table), so the hydrogen rest wavelengths are never used. The forbidden lines
give z as a straight line in wavelength, a calibration of the spectrum's
wavelength scale and of the gas's velocity together; one z for all is the
comparison.

The uncertainties come from the pipeline's inverse variance per pixel
(``ivar``), scaled where a fit's reduced chi-square is above 1; the scatter of
the forbidden lines about the calibration and of the hydrogen lines' R about
their mean test them. The pipeline's wavelength calibration is taken as
released, and the hydrogen and the forbidden lines are assumed to share the
gas's velocity; the dossier says what follows from both.
"""

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.special import erf

from pbc.data.fit import FitResult, fit_curve
from pbc.data.plotting import COLOURS, add_credit, label_status

FILE = "spec-1949-53433-0480.csv"
FIELDS = ("loglam", "flux", "ivar", "and_mask", "wdisp")
UNITS = {
    "loglam": "log10(wavelength / Angstrom), vacuum, heliocentric",
    "flux": "1E-17 erg/cm^2/s/Ang",
    "ivar": "(1E-17 erg/cm^2/s/Ang)^-2",
    "and_mask": "none, SPPIXMASK bits",
    "wdisp": "pixels of 1e-4 in loglam",
}
DLOGLAM = 1e-4  # pixel width in log10(wavelength), WFITTYPE LOG-LINEAR, COEFF1
C_KMS = 299792.458  # speed of light [km/s]
# Rest vacuum wavelengths [Angstrom] of the forbidden lines, the LINEWAVE
# values of the FITS file's SPZLINE table (the SDSS line list).
FORBIDDEN = {
    "[Ne III] 3870": 3869.857,
    "[O III] 4960": 4960.295,
    "[O III] 5008": 5008.240,
    "[O I] 6302": 6302.046,
    "[N II] 6550": 6549.859,
    "[N II] 6585": 6585.268,
    "[S II] 6718": 6718.294,
    "[S II] 6733": 6732.678,
    "[Ar III] 7138": 7137.757,
}
# The hydrogen lines used, by upper level n (lower level 2). H epsilon (n = 7)
# falls on [Ne III] 3969 and n = 8 on He I 3889, so the series stops at n = 6.
BALMER = {3: "H alpha", 4: "H beta", 5: "H gamma", 6: "H delta"}
# Balmer's constant of 1885 (B = 3645.6 Angstrom, air), which places the
# windows: lambda_n = B n^2 / (n^2 - 4), times (1 + z). It is only a starting
# point; the fit does not depend on it to better than 1e-4 Angstrom.
BALMER_B = 3645.6
# Lines fitted together because their wings overlap: H alpha and [N II], the
# [S II] doublet. Every other line is fitted alone.
GROUPS = (
    ("[N II] 6550", "H alpha", "[N II] 6585"),
    ("[S II] 6718", "[S II] 6733"),
)
HALF_WINDOW = 12.0  # Angstrom, observed, beyond the outermost line of a group
SEARCH = 4.0  # Angstrom, around a line's guess, for its brightest pixel
# The choices compared by ``sensitivity``: name -> (half window [Angstrom],
# Balmer lines used, a slope in the redshift calibration, a forbidden line
# left out of it). "no H delta" drops the line with the most stellar
# absorption under it; "no [Ne III]" the bluest calibration line, which sets
# most of the slope; "one z" is the calibration without its slope.
VARIANTS = {
    "window 9 A": (9.0, (3, 4, 5, 6), True, None),
    "window 16 A": (16.0, (3, 4, 5, 6), True, None),
    "no H delta": (12.0, (3, 4, 5), True, None),
    "no [Ne III]": (12.0, (3, 4, 5, 6), True, "[Ne III] 3870"),
    "one z": (12.0, (3, 4, 5, 6), False, None),
}
# CODATA 2018: the Rydberg constant and the electron-proton mass ratio, for
# the comparison only. R_H = R_inf / (1 + m_e / m_p).
R_INF = 10973731.568160  # 1/m
ME_OVER_MP = 1 / 1836.15267343
R_H = R_INF / (1 + ME_OVER_MP)
# Laboratory vacuum wavelengths [Angstrom] of the Balmer lines (the SPZLINE
# LINEWAVE values): the centroids of the fine-structure components, used
# only to say how far the Bohr formula is from real hydrogen.
BALMER_LAB = {3: 6564.614, 4: 4862.683, 5: 4341.684, 6: 4102.892}


@dataclass(frozen=True)
class Spectrum:
    loglam: np.ndarray  # log10(vacuum wavelength / Angstrom), heliocentric
    flux: np.ndarray  # [1e-17 erg/cm^2/s/Angstrom]
    ivar: np.ndarray  # inverse variance of the flux
    and_mask: np.ndarray  # SPPIXMASK bits set in every exposure
    wdisp: np.ndarray  # line-spread sigma [pixels]
    header: tuple[str, ...]  # the comment lines of the CSV

    @property
    def wavelength(self) -> np.ndarray:
        return 10.0**self.loglam


def read_spectrum(path: Path) -> Spectrum:
    """Read the five-column CSV written by ``tools/datasets/sdss_spec_to_csv.py``."""
    lines = Path(path).read_text(encoding="ascii").splitlines()
    header = tuple(line for line in lines if line.startswith("#"))
    names = next(line for line in lines if not line.startswith("#")).split(",")
    if tuple(names) != FIELDS:
        raise ValueError(f"{path}: columns {names}, expected {FIELDS}")
    table = np.loadtxt(path, delimiter=",", skiprows=len(header) + 1, ndmin=2)
    if table.shape[1] != len(FIELDS):
        raise ValueError(f"{path}: rows of {table.shape[1]} values")
    mask = table[:, 3]
    if not np.all(mask == np.round(mask)):
        raise ValueError(f"{path}: a mask value that is not an integer")
    return Spectrum(
        table[:, 0], table[:, 1], table[:, 2], mask.astype(int), table[:, 4], header
    )


def load(data_dir: Path) -> Spectrum:
    return read_spectrum(Path(data_dir) / FILE)


def good(spectrum: Spectrum) -> np.ndarray:
    """Pixels with a positive inverse variance and no bit of the AND mask."""
    return (spectrum.ivar > 0) & (spectrum.and_mask == 0)


def pipeline_value(spectrum: Spectrum, name: str) -> str:
    """A value of the pipeline's SPECOBJ row, as the CSV's comment gives it."""
    line = next(h for h in spectrum.header if h.startswith("# pipeline"))
    for item in line.split(":", 1)[1].split(";")[0].split(","):
        key, _, value = item.strip().partition(" ")
        if key == name:
            return value
    raise KeyError(name)


# The line model.


def pixel_gaussian(lo, hi, amplitude, centre, sigma):
    """Mean over the pixel [lo, hi] of amplitude * exp(-(x - centre)^2 / 2 sigma^2):
    the spectrum is a flux density averaged over each pixel."""
    s = np.sqrt(2.0) * sigma
    area = (
        0.5
        * amplitude
        * s
        * np.sqrt(np.pi)
        * (erf((hi - centre) / s) - erf((lo - centre) / s))
    )
    return area / (hi - lo)


def edges(loglam: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Wavelengths of the pixel edges, half a log-linear step either side."""
    return 10.0 ** (loglam - DLOGLAM / 2), 10.0 ** (loglam + DLOGLAM / 2)


@dataclass(frozen=True)
class Line:
    name: str
    centre: float  # observed vacuum wavelength [Angstrom]
    centre_err: float  # from ivar, not scaled
    sigma: float  # Gaussian width [Angstrom]
    flux: float  # [1e-17 erg/cm^2/s]
    reduced_chi2: float  # of the fit of its group
    dof: int

    @property
    def error(self) -> float:
        """The centre's standard error, scaled by sqrt(reduced chi-square)
        when the fit of its group is worse than its errors allow (a bright
        line is not exactly a Gaussian at this signal-to-noise)."""
        return self.centre_err * max(1.0, float(np.sqrt(self.reduced_chi2)))


@dataclass(frozen=True)
class GroupFit:
    names: tuple[str, ...]
    lo: float  # window [Angstrom]
    hi: float
    result: FitResult
    wavelength: np.ndarray  # the pixels fitted
    flux: np.ndarray
    error: np.ndarray

    def model(self, loglam: np.ndarray) -> np.ndarray:
        return group_model(loglam, (self.lo, self.hi), *self.result.params)

    def line(self, k: int) -> Line:
        r = self.result
        amplitude, position, sigma = r.params[2 + 3 * k : 5 + 3 * k]
        return Line(
            self.names[k],
            float(self.lo + position),
            float(r.stderr[3 + 3 * k]),
            float(sigma),
            float(amplitude * sigma * np.sqrt(2 * np.pi)),
            float(r.reduced_chi2),
            int(r.dof),
        )


def group_model(loglam, span, left, right, *lines):
    """The continuum is the straight line from ``left`` at the window's lower
    edge to ``right`` at its upper edge (``span`` = (lower, upper) [Angstrom]);
    two levels, not a level and a slope. Each line is (amplitude, position,
    sigma), its position the centre's distance from the lower edge. Both
    choices give the parameters the size of what they change, so the
    identifiability test of ``fit_curve``, which scales each parameter by its
    size, compares like with like (a centre near 5000 Angstrom would outweigh
    every other parameter by three orders of magnitude)."""
    lo, hi = edges(np.asarray(loglam, dtype=float))
    start, stop = span
    t = (0.5 * (lo + hi) - start) / (stop - start)
    out = left + (right - left) * t
    for k in range(0, len(lines), 3):
        amplitude, position, sigma = lines[k : k + 3]
        out = out + pixel_gaussian(lo, hi, amplitude, start + position, sigma)
    return out


def fit_group(
    spectrum: Spectrum,
    names: tuple[str, ...],
    guesses: tuple[float, ...],
    half_window: float = HALF_WINDOW,
) -> GroupFit:
    """Fit a straight continuum and one Gaussian per line to the good pixels
    from ``half_window`` below the first line's peak to ``half_window`` above
    the last one's, weighted by the pipeline's inverse variance. A line's peak
    is its brightest good pixel within ``SEARCH`` of its guess, so the window
    is set by the data, and a guess that is off by up to a pixel or two gives
    the same fit."""
    wave = spectrum.wavelength
    ok = good(spectrum)
    peaks = []
    for guess in guesses:
        near = ok & (np.abs(wave - guess) < SEARCH)
        peaks.append(float(wave[near][np.argmax(spectrum.flux[near])]))
    lo, hi = min(peaks) - half_window, max(peaks) + half_window
    inside = ok & (wave > lo) & (wave < hi)
    x, y = spectrum.loglam[inside], spectrum.flux[inside]
    err = 1.0 / np.sqrt(spectrum.ivar[inside])
    w = wave[inside]
    level = np.median(y)
    p0, lower, upper = [level, level], [-np.inf, -np.inf], [np.inf, np.inf]
    for peak in peaks:
        height = y[np.argmin(np.abs(w - peak))]
        p0 += [max(height - level, 1.0), peak - lo, 1.5]
        lower += [0.0, peak - lo - 3.0, 0.3]
        upper += [np.inf, peak - lo + 3.0, 6.0]
    names_fit = ["left", "right"]
    for name in names:
        names_fit += [f"{name}:amplitude", f"{name}:position", f"{name}:sigma"]

    def model(loglam, *params):
        return group_model(loglam, (lo, hi), *params)

    result = fit_curve(
        model, x, y, p0, sigma=err, names=names_fit, bounds=(lower, upper)
    )
    return GroupFit(tuple(names), lo, hi, result, w, y, err)


def rough_z(spectrum: Spectrum) -> float:
    """The redshift of the brightest line, [O III] 5008, from its peak pixel
    between 5009 and 5160 Angstrom (z up to 0.03): only a starting point."""
    wave = spectrum.wavelength
    near = good(spectrum) & (wave > 5009) & (wave < 5160)
    return float(
        wave[near][np.argmax(spectrum.flux[near])] / FORBIDDEN["[O III] 5008"] - 1
    )


def balmer_guess(n: int, z: float) -> float:
    """Observed position of H(n) from Balmer's formula, air to vacuum by the
    factor 1.00028 (good to 0.1 Angstrom here): a starting point only."""
    return (1 + z) * BALMER_B * n**2 / (n**2 - 4) * 1.00028


def fit_lines(
    spectrum: Spectrum,
    half_window: float = HALF_WINDOW,
    z_start: float | None = None,
) -> tuple[dict[str, Line], list[GroupFit]]:
    """Every forbidden and Balmer line, fitted in its group."""
    z = rough_z(spectrum) if z_start is None else z_start
    guess = {name: (1 + z) * rest for name, rest in FORBIDDEN.items()}
    guess.update({BALMER[n]: balmer_guess(n, z) for n in BALMER})
    grouped = {name for group in GROUPS for name in group}
    groups = list(GROUPS) + [(name,) for name in guess if name not in grouped]
    lines, fits = {}, []
    for names in groups:
        fit = fit_group(spectrum, names, tuple(guess[n] for n in names), half_window)
        fits.append(fit)
        for k in range(len(names)):
            lines[names[k]] = fit.line(k)
    return lines, fits


# From the lines to the calibration, z, and R.


PIVOT = 5500.0  # Angstrom, the zero point of the redshift's slope
SCALE = 1000.0  # Angstrom, the unit of that slope


@dataclass(frozen=True)
class Calibration:
    """The redshift as a straight line in observed wavelength,
    z(lambda) = z0 + z1 (lambda - PIVOT) / SCALE, fitted to the forbidden
    lines (``slope=False``: the constant z0 alone). The covariance is scaled
    by the reduced chi-square when it is above 1 (the Birge ratio)."""

    params: np.ndarray  # z0, z1 (or z0)
    covariance: np.ndarray
    chi2: float
    dof: int
    z: dict[str, float]  # each forbidden line's z
    wavelength: dict[str, float]  # its observed wavelength

    def at(self, wavelength) -> np.ndarray:
        wavelength = np.asarray(wavelength, dtype=float)
        if self.params.size == 1:
            return np.full(wavelength.shape, self.params[0])
        return self.params[0] + self.params[1] * (wavelength - PIVOT) / SCALE

    def velocity(self, name: str) -> float:
        """A forbidden line's offset from the calibration [km/s]."""
        z_fit = float(self.at(self.wavelength[name]))
        return (self.z[name] - z_fit) / (1 + z_fit) * C_KMS

    @property
    def slope_kms(self) -> float:
        """The velocity change per SCALE of wavelength [km/s]."""
        if self.params.size == 1:
            return 0.0
        return float(self.params[1] / (1 + self.params[0]) * C_KMS)


def calibrate(
    lines: dict[str, Line], slope: bool = True, without: str | None = None
) -> Calibration:
    """Weighted least squares of z = lambda_obs / lambda_rest - 1 of the
    forbidden lines (all but ``without``) against their observed wavelength,
    with each line's scaled error."""
    names = [n for n in FORBIDDEN if n != without]
    observed = np.array([lines[n].centre for n in names])
    rest = np.array([FORBIDDEN[n] for n in names])
    z = observed / rest - 1
    weights = 1 / (np.array([lines[n].error for n in names]) / rest) ** 2
    columns = [np.ones_like(z)]
    if slope:
        columns.append((observed - PIVOT) / SCALE)
    design = np.column_stack(columns)
    normal = design.T @ (design * weights[:, None])
    covariance = np.linalg.inv(normal)
    params = covariance @ (design.T @ (weights * z))
    chi2 = float(np.sum(weights * (z - design @ params) ** 2))
    dof = z.size - params.size
    covariance = covariance * max(1.0, chi2 / dof)
    return Calibration(
        params,
        covariance,
        chi2,
        dof,
        dict(zip(names, z.tolist(), strict=True)),
        dict(zip(names, observed.tolist(), strict=True)),
    )


def balmer_term(n) -> np.ndarray:
    return 0.25 - 1.0 / np.asarray(n, dtype=float) ** 2


@dataclass(frozen=True)
class Rydberg:
    levels: tuple[int, ...]
    calibration: Calibration
    r: float  # R_H [1/m], the weighted mean of the lines' values
    r_err: float  # from the lines' errors and the calibration's covariance
    per_line: dict[int, float]  # 1 / (lambda_rest,n (1/4 - 1/n^2)) [1/m]
    per_line_err: dict[int, float]  # from the line's error alone
    chi2: float  # of the per-line values about r: the test of the 1/n^2 law
    dof: int

    @property
    def relative(self) -> float:
        """(R - R_H) / R_H against CODATA 2018."""
        return self.r / R_H - 1

    @property
    def relative_lab(self) -> float:
        """(R - R_lab) / R_lab against the same method on laboratory hydrogen."""
        return self.r / bohr_lab_rydberg(self.levels) - 1

    def residual_kms(self, n: int) -> float:
        """The line's offset from the Balmer formula with R, as a velocity
        [km/s]: positive when the line is observed redder than the formula."""
        return (self.r / self.per_line[n] - 1) * C_KMS


def _per_line(lines, levels, calibration):
    term = balmer_term(levels)
    observed = np.array([lines[BALMER[n]].centre for n in levels])
    error = np.array([lines[BALMER[n]].error for n in levels])
    rest = observed / (1 + calibration.at(observed)) * 1e-10  # m
    value = 1 / (rest * term)
    return value, value * error / observed


def rydberg(
    lines: dict[str, Line],
    levels: tuple[int, ...] = tuple(BALMER),
    slope: bool = True,
    without: str | None = None,
) -> Rydberg:
    """Every hydrogen line's rest wavelength from the calibration, its R from
    the Balmer formula 1 / lambda = R (1/4 - 1/n^2), and their weighted mean.
    The error of the mean combines the lines' errors (scaled by the Birge
    ratio of the per-line values when it is above 1) with the calibration's
    covariance, propagated by its derivatives."""
    calibration = calibrate(lines, slope, without)
    value, error = _per_line(lines, levels, calibration)
    weights = 1 / error**2
    r = float(np.sum(weights * value) / np.sum(weights))
    chi2 = float(np.sum(weights * (value - r) ** 2))
    dof = len(levels) - 1
    var_lines = (1 / weights.sum()) * max(1.0, chi2 / dof if dof else 1.0)
    gradient = []
    for k in range(calibration.params.size):
        step = np.zeros(calibration.params.size)
        step[k] = 1e-7
        moved = Calibration(
            calibration.params + step,
            calibration.covariance,
            calibration.chi2,
            calibration.dof,
            calibration.z,
            calibration.wavelength,
        )
        shifted, _ = _per_line(lines, levels, moved)
        gradient.append((np.sum(weights * shifted) / np.sum(weights) - r) / 1e-7)
    gradient = np.array(gradient)
    var_calibration = float(gradient @ calibration.covariance @ gradient)
    return Rydberg(
        tuple(levels),
        calibration,
        r,
        float(np.sqrt(var_lines + var_calibration)),
        dict(zip(levels, value.tolist(), strict=True)),
        dict(zip(levels, error.tolist(), strict=True)),
        chi2,
        dof,
    )


def bohr_lab_rydberg(levels: tuple[int, ...] = tuple(BALMER)) -> float:
    """R from the laboratory wavelengths by the same formula, averaged over
    the lines: what the method gives for real hydrogen at rest, whose lines
    are fine-structure multiplets that the Bohr formula does not resolve."""
    term = balmer_term(levels)
    lam = np.array([BALMER_LAB[n] for n in levels]) * 1e-10
    return float(np.mean(1 / (lam * term)))


@dataclass(frozen=True)
class Analysis:
    lines: dict[str, Line]
    fits: list[GroupFit]
    rydberg: Rydberg


def analyse(
    spectrum: Spectrum,
    half_window: float = HALF_WINDOW,
    levels: tuple[int, ...] = tuple(BALMER),
    slope: bool = True,
    without: str | None = None,
) -> Analysis:
    lines, fits = fit_lines(spectrum, half_window)
    return Analysis(lines, fits, rydberg(lines, levels, slope, without))


def sensitivity(spectrum: Spectrum) -> dict[str, Rydberg]:
    """R with the other choices in VARIANTS: a sensitivity analysis of the
    window, the lines used, and the calibration, not an uncertainty of the
    record."""
    return {
        name: analyse(spectrum, window, levels, slope, without).rydberg
        for name, (window, levels, slope, without) in VARIANTS.items()
    }


def make_figure(data_dir: Path) -> plt.Figure:
    spectrum = load(data_dir)
    analysis = analyse(spectrum)
    ryd = analysis.rydberg
    cal = ryd.calibration
    flat = rydberg(analysis.lines, ryd.levels, slope=False)
    ok = good(spectrum)
    wave = spectrum.wavelength

    fig = plt.figure(figsize=(10, 11), constrained_layout=True)
    grid = fig.add_gridspec(4, 4, height_ratios=(1.1, 1.0, 0.45, 1.2))
    ax_all = fig.add_subplot(grid[0, :])
    ax_lines = [fig.add_subplot(grid[1, k]) for k in range(4)]
    ax_res = [fig.add_subplot(grid[2, k], sharex=ax_lines[k]) for k in range(4)]
    ax_cal = fig.add_subplot(grid[3, :2])
    ax_law = fig.add_subplot(grid[3, 2:])

    ax_all.plot(
        wave[ok],
        spectrum.flux[ok],
        color=COLOURS[0],
        lw=0.6,
        label="measured flux density (good pixels)",
    )
    for k, name in enumerate(BALMER.values()):
        centre = analysis.lines[name].centre
        ax_all.axvline(centre, color=COLOURS[1], lw=0.6, ls=":")
        ax_all.annotate(
            name,
            (centre, 0.97 - 0.06 * (k % 2)),
            xycoords=("data", "axes fraction"),
            xytext=(2, 0),
            textcoords="offset points",
            fontsize=7,
            va="top",
            color=COLOURS[1],
        )
    ax_all.set_yscale("log")
    ax_all.set_xlabel("observed vacuum wavelength, heliocentric [Angstrom]")
    ax_all.set_ylabel("flux density [1e-17 erg/cm2/s/A]")
    ax_all.set_title(
        "Calibrated: SDSS spectrum 1949-53433-0480 of a starburst galaxy;"
        " dotted, the four Balmer lines fitted",
        fontsize=10,
    )
    ax_all.legend(fontsize=8, loc="lower left")

    by_name = {name: fit for fit in analysis.fits for name in fit.names}
    for ax, ax_r, name in zip(ax_lines, ax_res, BALMER.values(), strict=True):
        fit = by_name[name]
        line = analysis.lines[name]
        ax.errorbar(
            fit.wavelength,
            fit.flux,
            yerr=fit.error,
            ls="none",
            marker="o",
            ms=2.5,
            color=COLOURS[0],
            label="measured pixels (1 sigma)",
        )
        dense = np.linspace(np.log10(fit.lo), np.log10(fit.hi), 600)
        ax.plot(
            10**dense,
            fit.model(dense),
            color=COLOURS[1],
            ls="--",
            lw=1.2,
            label="model fit: Gaussian on a line",
        )
        ax.set_title(
            f"Processed: {name}, {line.centre:.3f} A\n"
            f"reduced chi-square {line.reduced_chi2:.1f}",
            fontsize=8,
        )
        ax.set_ylabel("flux density [1e-17 cgs/A]", fontsize=7)
        ax.tick_params(labelsize=7, labelbottom=False)
        normalised = fit.result.residuals / fit.error
        ax_r.plot(
            fit.wavelength,
            normalised,
            ls="none",
            marker="o",
            ms=2.5,
            color=COLOURS[2],
        )
        ax_r.axhline(0, color="0.3", lw=0.8)
        ax_r.set_title("Residuals over the pixel error", fontsize=7)
        ax_r.set_xlabel("wavelength [A]", fontsize=8)
        ax_r.set_ylabel("residual [sigma]", fontsize=7)
        ax_r.tick_params(labelsize=7)
    ax_lines[0].legend(fontsize=6, loc="upper left")

    names = list(FORBIDDEN)
    observed = np.array([cal.wavelength[n] for n in names])
    z = np.array([cal.z[n] for n in names])
    zerr = np.array([analysis.lines[n].error / FORBIDDEN[n] for n in names])
    z_ref = float(cal.params[0])
    to_kms = C_KMS / (1 + z_ref)
    ax_cal.errorbar(
        observed,
        (z - z_ref) * to_kms,
        yerr=zerr * to_kms,
        ls="none",
        marker="o",
        ms=4,
        color=COLOURS[0],
        label="forbidden lines, measured (scaled 1 sigma)",
    )
    for name, x, y in zip(names, observed, (z - z_ref) * to_kms, strict=True):
        ax_cal.annotate(
            name, (x, y), xytext=(3, 3), textcoords="offset points", fontsize=6
        )
    span = np.linspace(3800, 7400, 50)
    ax_cal.plot(
        span,
        (cal.at(span) - z_ref) * to_kms,
        color=COLOURS[1],
        ls="--",
        label=f"model fit: z(lambda), slope {cal.slope_kms:.1f} km/s per 1000 A",
    )
    ax_cal.axhline(
        (flat.calibration.params[0] - z_ref) * to_kms,
        color="0.5",
        ls=":",
        label="model fit: one z for all",
    )
    ax_cal.set_xlabel("observed wavelength [A]")
    ax_cal.set_ylabel(f"velocity from z = {z_ref:.7f} [km/s]")
    ax_cal.set_title(
        f"Processed: redshift calibration; chi-square {cal.chi2:.0f}"
        f" for {cal.dof} degrees of freedom",
        fontsize=10,
    )
    ax_cal.legend(fontsize=7, loc="lower right")

    levels = list(ryd.levels)
    ax_law.errorbar(
        levels,
        [(ryd.per_line[n] / R_H - 1) * 1e6 for n in levels],
        yerr=[ryd.per_line_err[n] / R_H * 1e6 for n in levels],
        ls="none",
        marker="o",
        ms=4,
        color=COLOURS[0],
        label="each line, calibrated z(lambda) (scaled 1 sigma of the line)",
    )
    ax_law.plot(
        np.array(levels) + 0.12,
        [(flat.per_line[n] / R_H - 1) * 1e6 for n in levels],
        ls="none",
        marker="s",
        ms=4,
        mfc="none",
        color="0.45",
        label=f"each line, one z (chi-square {flat.chi2:.0f})",
    )
    ax_law.axhline(
        ryd.relative * 1e6,
        color=COLOURS[1],
        ls="--",
        label=(
            f"model fit: R = {ryd.r:.0f} +- {ryd.r_err:.0f} 1/m"
            f" (chi-square {ryd.chi2:.1f} for {ryd.dof})"
        ),
    )
    ax_law.axhline(
        (bohr_lab_rydberg() / R_H - 1) * 1e6,
        color=COLOURS[2],
        ls="-.",
        label="laboratory hydrogen, same formula",
    )
    ax_law.axhline(0, color="0.3", lw=0.8, label="R_H, CODATA 2018")
    ax_law.set_xticks(levels, [f"n = {n}" for n in levels])
    ax_law.set_xlabel("upper level n of the transition to level 2 [1]")
    ax_law.set_ylabel("(R - R_H) / R_H [1e-6]")
    ax_law.set_title(
        "Processed: R from 1/lambda = R (1/4 - 1/n^2) per line", fontsize=10
    )
    ax_law.set_ylim(-5, 95)
    ax_law.legend(fontsize=6.5, loc="upper left")

    add_credit(
        fig,
        "Data: Sloan Digital Sky Survey, spectrum spec-1949-53433-0480.fits"
        " (plate 1949, MJD 53433, fibre 480), Data Release 17, from the SDSS"
        " Science Archive Server; columns loglam, flux, ivar, and_mask, wdisp"
        " converted to CSV unchanged. Line fits, redshift calibration and"
        " Balmer formula: this figure's code (pbc.data.reference.sdss_balmer),"
        " not part of the record.",
    )
    label_status(fig, "processed")
    return fig
