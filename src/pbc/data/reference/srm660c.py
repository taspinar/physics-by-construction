"""NIST SRM 660c (LaB6): Bragg peaks of the certification data, the lattice
parameter by a Nelson-Riley extrapolation, and the same analysis of NIST's
own model pattern.

Status of the figure: *processed* (NIST's corrected 2theta and its count rates,
rebinned by NIST; here fitted).

The release holds, per specimen (two from each of ten bottles), the measured
powder pattern of 24 scan windows, each around one reflection hkl of the
cubic Pm-3m lattice, and NIST's fundamental-parameters model of it on the
same 2theta grid. Bragg's law with the Cu K-alpha-1 wavelength of the certificate
gives the spacing d = lambda / (2 sin theta) of each reflection and the lattice
parameter a = d sqrt(h^2 + k^2 + l^2).

The analysis here is the simple one a laboratory course can repeat: per
window a K-alpha-1/K-alpha-2 doublet of pseudo-Voigt profiles on a straight background,
the K-alpha-2/K-alpha-1 wavelength and intensity ratios taken from the doublets that are
resolved (2theta above ``RESOLVED``), and an ordinary least-squares line of a
against the Nelson-Riley function cos^2theta/sin theta + cos^2theta/theta over the
reflections above ``NR_MIN``, extrapolated to theta = 90 deg. A symmetric profile
does not describe the asymmetric instrument profile, so this a is biased.
The bias is measured, not assumed: the same analysis applied to NIST's model
pattern, whose lattice parameter the CIF states, gives the bias of the
method; the measurement minus the model by the same method is the
comparison that the bias does not affect.
"""

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import least_squares

from pbc.data.plotting import COLOURS, add_credit, label_status

# Certificate of SRM 660c (NIST, 29 October 2015): Table 1 and the certified
# value with its expanded uncertainty (k = 2), at 22.5 degC.
WAVELENGTH = 1.5405929  # angstrom, Cu K-alpha-1
CERTIFIED_A = 4.156826  # angstrom
CERTIFIED_U = 0.000080  # angstrom, k = 2
CERTIFIED_T = 22.5  # degC
HKL = (
    (1, 0, 0), (1, 1, 0), (1, 1, 1), (2, 0, 0), (2, 1, 0), (2, 1, 1),
    (2, 2, 0), (3, 0, 0), (3, 1, 0), (3, 1, 1), (2, 2, 2), (3, 2, 0),
    (3, 2, 1), (4, 0, 0), (4, 1, 0), (3, 3, 0), (3, 3, 1), (4, 2, 0),
    (4, 2, 1), (3, 3, 2), (4, 2, 2), (5, 0, 0), (5, 1, 0), (5, 1, 1),
)  # fmt: skip
TABLE1_TWO_THETA = (
    21.358,
    30.385,
    37.442,
    43.507,
    48.958,
    53.990,
    63.220,
    67.549,
    71.747,
    75.846,
    79.872,
    83.847,
    87.794,
    95.673,
    99.645,
    103.663,
    107.752,
    111.936,
    116.248,
    120.726,
    130.413,
    135.805,
    141.780,
    148.685,
)  # fmt: skip  (degrees, information values)

SPECIMENS = tuple(f"{b}{s}" for b in range(100, 1001, 100) for s in "ab")
HEADER = ("two_theta", "intensity", "weight", "calc_intensity")
GAP = 0.1  # degrees: a larger step in 2theta separates two scan windows
RESOLVED = 94.0  # degrees: doublets above this give the K-alpha-2 ratios
NR_MIN = 60.0  # degrees: reflections above this enter the extrapolation
SHOWN = "100a"  # the specimen of the pattern and peak panels
SHOWN_PEAK = (5, 1, 0)
NR_FRAME = (415.45, 415.70)  # pm: the a range of the Nelson-Riley panel
NR_XMAX = 3.6  # the Nelson-Riley function at the right edge of that panel


@dataclass(frozen=True)
class Pattern:
    two_theta: np.ndarray  # degrees
    intensity: np.ndarray  # counts over counting time
    weight: np.ndarray  # 1 / sigma^2 of intensity
    calc: np.ndarray  # NIST's model, units of intensity

    @property
    def sigma(self) -> np.ndarray:
        return 1 / np.sqrt(self.weight)


def read_pattern(path: Path) -> Pattern:
    """Read a specimen CSV written by ``tools/datasets/srm660c_cif_to_csv.py``."""
    lines = [
        line
        for line in Path(path).read_text(encoding="ascii").splitlines()
        if not line.startswith("#")
    ]
    if tuple(lines[0].split(",")) != HEADER:
        raise ValueError(f"{path}: header {lines[0]!r}, expected {HEADER}")
    values = np.array([[float(v) for v in line.split(",")] for line in lines[1:]])
    return Pattern(*values.T)


def read_specimens(path: Path) -> dict[str, dict[str, float]]:
    """``specimens.csv``: per specimen the CIF's temperature [degC], vertical
    displacement [mm], NIST's refined a [angstrom], and number of points."""
    lines = [
        line
        for line in Path(path).read_text(encoding="ascii").splitlines()
        if not line.startswith("#")
    ]
    header = lines[0].split(",")
    out = {}
    for line in lines[1:]:
        cells = line.split(",")
        out[cells[0]] = {
            h: float(v) for h, v in zip(header[1:], cells[1:], strict=True)
        }
    return out


def load(data_dir: Path) -> dict[str, Pattern]:
    return {s: read_pattern(Path(data_dir) / f"660c_{s}.csv") for s in SPECIMENS}


def windows(two_theta: np.ndarray) -> list[np.ndarray]:
    """Index arrays of the scan windows: runs of 2theta without a gap."""
    cuts = np.flatnonzero(np.diff(two_theta) > GAP) + 1
    return np.split(np.arange(two_theta.size), cuts)


def pseudo_voigt(x, centre, fwhm, eta):
    """Unit-height pseudo-Voigt: eta Lorentzian + (1 - eta) Gaussian."""
    u = (x - centre) / fwhm
    return eta / (1 + 4 * u**2) + (1 - eta) * np.exp(-4 * np.log(2) * u**2)


def kalpha2(two_theta1, ratio):
    """2theta of K-alpha-2 for K-alpha-1 at ``two_theta1``, lambda2/lambda1 = ratio."""
    s = np.clip(ratio * np.sin(np.radians(two_theta1) / 2), -1, 1)
    return 2 * np.degrees(np.arcsin(s))


def doublet(p, x, ratio, share):
    b0, b1, height, centre, fwhm, eta = p
    profile = pseudo_voigt(x, centre, fwhm, eta)
    profile = profile + share * pseudo_voigt(x, kalpha2(centre, ratio), fwhm, eta)
    return b0 + b1 * (x - centre) + height * profile


def _start(x, y):
    i = int(np.argmax(y))
    return x[i], y[i], float(np.median(np.r_[y[:15], y[-15:]]))


def free_doublet(x, y, sigma):
    """Kalpha1 and Kalpha2 with free positions and heights; returns the
    wavelength ratio sin(theta2)/sin(theta1) and the height ratio."""
    x1, top, base = _start(x, y)
    x2 = kalpha2(x1, 1.0025)

    def model(p):
        b0, b1, h1, c1, h2, c2, fwhm, eta = p
        return (
            b0
            + b1 * (x - c1)
            + h1 * pseudo_voigt(x, c1, fwhm, eta)
            + h2 * pseudo_voigt(x, c2, fwhm, eta)
        )

    fit = least_squares(
        lambda p: (model(p) - y) / sigma,
        [base, 0, top, x1, top / 2, x2, 0.05, 0.5],
        bounds=(
            [-np.inf, -np.inf, 0, x1 - 0.2, 0, x1, 0.005, 0],
            [np.inf, np.inf, np.inf, x1 + 0.2, np.inf, x1 + 2, 1, 1],
        ),
    )
    _, _, h1, c1, h2, c2, _, _ = fit.x
    ratio = np.sin(np.radians(c2) / 2) / np.sin(np.radians(c1) / 2)
    return float(ratio), float(h2 / h1)


@dataclass(frozen=True)
class Peak:
    hkl: tuple[int, int, int]
    two_theta: float  # K-alpha-1 position, degrees
    error: float  # its standard error, degrees (scaled by the residual)
    fwhm: float  # degrees
    eta: float  # Lorentzian fraction
    reduced_chi2: float
    params: tuple[float, ...]

    @property
    def theta(self) -> float:
        return float(np.radians(self.two_theta) / 2)

    @property
    def d(self) -> float:
        """Spacing [angstrom] by Bragg's law with the K-alpha-1 wavelength."""
        return WAVELENGTH / (2 * np.sin(self.theta))

    @property
    def a(self) -> float:
        """Lattice parameter [angstrom] from this reflection alone."""
        return self.d * float(np.sqrt(sum(h * h for h in self.hkl)))

    @property
    def a_error(self) -> float:
        return self.a * float(np.radians(self.error) / 2) / float(np.tan(self.theta))


def fit_peak(x, y, sigma, hkl, ratio, share) -> Peak:
    x1, top, base = _start(x, y)
    p0 = [base, 0, top, x1, 0.05, 0.5]
    fit = least_squares(
        lambda p: (doublet(p, x, ratio, share) - y) / sigma,
        p0,
        bounds=(
            [-np.inf, -np.inf, 0, x1 - 0.3, 0.005, 0],
            [np.inf, np.inf, np.inf, x1 + 0.3, 1, 1],
        ),
    )
    dof = len(y) - len(p0)
    chi2 = float(np.sum(fit.fun**2) / dof)
    cov = np.linalg.pinv(fit.jac.T @ fit.jac) * chi2
    return Peak(
        hkl,
        float(fit.x[3]),
        float(np.sqrt(cov[3, 3])),
        float(fit.x[4]),
        float(fit.x[5]),
        chi2,
        tuple(map(float, fit.x)),
    )


def nelson_riley(theta):
    theta = np.asarray(theta, float)
    return np.cos(theta) ** 2 / np.sin(theta) + np.cos(theta) ** 2 / theta


@dataclass(frozen=True)
class Analysis:
    ratio: float  # lambda(K-alpha-2) / lambda(K-alpha-1)
    share: float  # height of K-alpha-2 / K-alpha-1
    peaks: tuple[Peak, ...]
    a0: float  # Nelson-Riley extrapolation to theta = 90 deg, angstrom
    slope: float  # angstrom per unit of the Nelson-Riley function


def analyse(two_theta, intensity, sigma) -> Analysis:
    """The peak fits and the extrapolation of one pattern (measured or model,
    with the same weights)."""
    parts = windows(two_theta)
    if len(parts) != len(HKL):
        raise ValueError(f"{len(parts)} scan windows, expected {len(HKL)}")
    ratios = [
        free_doublet(two_theta[ix], intensity[ix], sigma[ix])
        for ix in parts
        if two_theta[ix[0]] > RESOLVED
    ]
    ratio = float(np.median([r for r, _ in ratios]))
    share = float(np.median([s for _, s in ratios]))
    peaks = tuple(
        fit_peak(two_theta[ix], intensity[ix], sigma[ix], hkl, ratio, share)
        for ix, hkl in zip(parts, HKL, strict=True)
    )
    a0, slope = extrapolate(peaks)
    return Analysis(ratio, share, peaks, a0, slope)


def extrapolate(peaks) -> tuple[float, float]:
    """Ordinary least squares of a against the Nelson-Riley function over
    the reflections above ``NR_MIN``; returns (a at theta = 90 deg, slope)."""
    used = [p for p in peaks if p.two_theta > NR_MIN]
    x = nelson_riley([p.theta for p in used])
    slope, a0 = np.polyfit(x, [p.a for p in used], 1)
    return float(a0), float(slope)


def analyse_measured(pattern: Pattern) -> Analysis:
    return analyse(pattern.two_theta, pattern.intensity, pattern.sigma)


def analyse_model(pattern: Pattern) -> Analysis:
    """The same analysis of NIST's model pattern, with the measured weights."""
    return analyse(pattern.two_theta, pattern.calc, pattern.sigma)


def summary(values) -> tuple[float, float, float]:
    """Mean, standard deviation, and standard error of the mean."""
    values = np.asarray(values, float)
    sd = float(np.std(values, ddof=1))
    return float(np.mean(values)), sd, sd / np.sqrt(values.size)


def make_figure(data_dir: Path) -> plt.Figure:
    patterns = load(data_dir)
    specimens = read_specimens(Path(data_dir) / "specimens.csv")
    measured = {s: analyse_measured(p) for s, p in patterns.items()}
    model = {s: analyse_model(p) for s, p in patterns.items()}
    nist = np.array([specimens[s]["cell_length_a_angstrom"] for s in SPECIMENS])
    a_meas = np.array([measured[s].a0 for s in SPECIMENS])
    a_model = np.array([model[s].a0 for s in SPECIMENS])
    pm = 100.0  # angstrom -> pm

    fig, axes = plt.subplot_mosaic(
        [["pattern", "peak"], ["pattern", "resid"], ["nr", "spec"]],
        figsize=(12, 10),
        height_ratios=[3, 1.3, 4.3],
        constrained_layout=True,
    )
    shown = patterns[SHOWN]

    ax = axes["pattern"]
    for k, ix in enumerate(windows(shown.two_theta)):
        ax.semilogy(
            shown.two_theta[ix],
            shown.intensity[ix],
            color=COLOURS[0],
            lw=0.7,
            label="measured, specimen " + SHOWN if k == 0 else None,
        )
    for peak in measured[SHOWN].peaks[::3]:
        top = shown.intensity[np.argmin(np.abs(shown.two_theta - peak.two_theta))]
        ax.annotate(
            "".join(map(str, peak.hkl)),
            (peak.two_theta, top * 1.15),
            ha="center",
            fontsize=7,
        )
    ax.set_xlabel("2$\\theta$ [degrees]")
    ax.set_ylabel("intensity [counts per counting time, log scale]")
    ax.set_title(
        f"Processed: the 24 scan windows of specimen {SHOWN} "
        "(every third hkl labelled)",
        fontsize=10,
    )
    ax.legend(fontsize=8, loc="upper right")

    peak = next(p for p in measured[SHOWN].peaks if p.hkl == SHOWN_PEAK)
    ix = next(
        i
        for i in windows(shown.two_theta)
        if abs(shown.two_theta[i].mean() - peak.two_theta) < 1.5
    )
    x = shown.two_theta[ix]
    fitted = doublet(peak.params, x, measured[SHOWN].ratio, measured[SHOWN].share)
    ax = axes["peak"]
    ax.errorbar(
        x,
        shown.intensity[ix],
        yerr=shown.sigma[ix],
        fmt=".",
        ms=3,
        color=COLOURS[0],
        elinewidth=0.6,
        label="measured (bars: 1$\\sigma$ counting error)",
    )
    ax.plot(
        x,
        fitted,
        color=COLOURS[1],
        ls="--",
        lw=1.2,
        label="K$\\alpha_1$ + K$\\alpha_2$ pseudo-Voigt fit",
    )
    ax.plot(
        x, shown.calc[ix], color=COLOURS[2], ls=":", lw=1.4, label="NIST's model (CIF)"
    )
    ax.axvline(peak.two_theta, color=COLOURS[1], ls="-.", lw=0.8)
    ax.set_ylabel("intensity [counts per time]")
    ax.set_title(
        f"Processed: reflection {''.join(map(str, SHOWN_PEAK))}, K$\\alpha_1$ at "
        f"{peak.two_theta:.4f}°; the doublet is resolved",
        fontsize=10,
    )
    ax.legend(fontsize=7.5, loc="upper right")
    resid = axes["resid"]
    resid.sharex(ax)
    ax.tick_params(labelbottom=False)
    resid.plot(
        x,
        (shown.intensity[ix] - fitted) / shown.sigma[ix],
        ".",
        ms=3,
        color=COLOURS[1],
        label="fit",
    )
    resid.plot(
        x,
        (shown.intensity[ix] - shown.calc[ix]) / shown.sigma[ix],
        ".",
        ms=3,
        color=COLOURS[2],
        label="NIST's model",
    )
    resid.axhline(0, color="0.4", lw=0.8)
    resid.set_xlabel("2$\\theta$ [degrees]")
    resid.set_ylabel("residual [$\\sigma$]")
    resid.set_title(
        "Measured minus fit, and minus NIST's model, in counting errors", fontsize=9
    )
    resid.legend(fontsize=7, loc="upper left", ncol=2)

    ax = axes["nr"]
    grid = np.linspace(0, NR_XMAX, 50)
    for k, s in enumerate(SPECIMENS):
        ax.plot(
            grid,
            (measured[s].a0 + measured[s].slope * grid) * pm,
            color="0.75",
            lw=0.6,
            label="measured: the line of each of the 20 specimens" if k == 0 else None,
        )
    for analysis, colour, marker, ls, name in (
        (measured[SHOWN], COLOURS[0], "o", "--", f"measured, {SHOWN}"),
        (model[SHOWN], COLOURS[2], "s", ":", f"NIST's model of {SHOWN}, same method"),
    ):
        x_nr = nelson_riley([p.theta for p in analysis.peaks])
        a = np.array([p.a for p in analysis.peaks]) * pm
        used = np.array([p.two_theta > NR_MIN for p in analysis.peaks])
        ax.errorbar(
            x_nr[used],
            a[used],
            yerr=np.array([p.a_error for p in analysis.peaks])[used] * pm,
            fmt=marker,
            mfc="none" if marker == "s" else colour,
            ms=5,
            color=colour,
            capsize=2,
            label=f"{name}: a per reflection, 2$\\theta$ > {NR_MIN:.0f}°",
        )
        ax.plot(x_nr[~used], a[~used], marker, mfc="none", color=colour, ms=4)
        ax.plot(
            grid,
            (analysis.a0 + analysis.slope * grid) * pm,
            color=colour,
            ls=ls,
            lw=1.2,
            label=f"{name}: Nelson-Riley line",
        )
    ax.axhline(
        nist.mean() * pm,
        color=COLOURS[3],
        ls="-",
        lw=1.0,
        label="NIST's refined a (CIF, mean, 20.85 °C)",
    )
    ax.axhline(
        CERTIFIED_A * pm, color="0.3", ls="-.", lw=1.0, label="certified a (22.5 °C)"
    )
    ax.set_xlim(0, NR_XMAX)
    ax.set_ylim(*NR_FRAME)
    ax.ticklabel_format(axis="y", useOffset=False)
    ax.set_xlabel(
        "Nelson-Riley function "
        "$\\cos^2\\theta/\\sin\\theta + \\cos^2\\theta/\\theta$ [dimensionless]"
    )
    ax.set_ylabel("lattice parameter a [pm]")
    ax.set_title(
        f"Processed: a per reflection, {SHOWN}; extrapolated to "
        f"$\\theta$ = 90° (hollow: 2$\\theta$ < {NR_MIN:.0f}°, not fitted)",
        fontsize=10,
    )
    ax.legend(fontsize=7, loc="lower left")

    ax = axes["spec"]
    index = np.arange(len(SPECIMENS))
    m_mean, m_sd, _ = summary(a_meas)
    c_mean, _, _ = summary(a_model)
    ax.plot(
        index,
        a_meas * pm,
        "o",
        color=COLOURS[0],
        label=f"measured: {m_mean:.6f} Å, SD {m_sd:.6f}",
    )
    ax.plot(
        index,
        a_model * pm,
        "s",
        mfc="none",
        color=COLOURS[2],
        label=f"NIST's model, same method: {c_mean:.6f} Å",
    )
    ax.plot(
        index,
        nist * pm,
        "x",
        color=COLOURS[3],
        label=f"NIST's refined a (CIF): {nist.mean():.6f} Å",
    )
    ax.axhspan(
        (CERTIFIED_A - CERTIFIED_U) * pm,
        (CERTIFIED_A + CERTIFIED_U) * pm,
        color="0.85",
        label="certified a ± U (k = 2), 22.5 °C",
    )
    ax.set_xticks(index, SPECIMENS, rotation=90, fontsize=7)
    ax.set_xlabel("specimen (bottle and specimen) [label]")
    ax.set_ylabel("lattice parameter a [pm]")
    ax.set_ylim(415.640, 415.700)
    ax.ticklabel_format(axis="y", useOffset=False)
    bias = (c_mean - nist.mean()) / nist.mean() * 1e6
    ax.set_title(
        f"Processed: a per specimen. The method's bias on NIST's model: "
        f"{bias:.0f} ppm;\nmeasured minus model by the same method: "
        f"{(m_mean - c_mean) / c_mean * 1e6:+.1f} ppm",
        fontsize=10,
    )
    ax.legend(fontsize=7, loc="center right")

    add_credit(
        fig,
        "Data: D. Black, J. Cline, M. Mendenhall (NIST), 'Diffraction Data for "
        "SRM 660c', doi 10.18434/mds2-2315, NIST open data licence; measured and "
        "calculated patterns converted from CIF to CSV, values unchanged. "
        "Wavelength and certified value: certificate of SRM 660c (2015). Peak "
        "fits and Nelson-Riley extrapolation: this figure's code "
        "(pbc.data.reference.srm660c), not NIST's analysis.",
    )
    label_status(fig, "processed")
    return fig
