"""COBE FIRAS, the CMB monopole spectrum: the measured spectrum, a blackbody,
and the residuals of Fixsen et al. (1996), Table 4.

Status of the figure: *processed*. The file of NASA's LAMBDA archive holds,
per frequency, the monopole spectrum "computed as the sum of a 2.725 K BB
spectrum and the residual" of Table 4 (its header's words), the residual
itself, its one-standard-deviation uncertainty, and the modelled Galactic
spectrum at the poles. The residuals are those the paper left after its own
fit of a temperature shift and a Galactic term to the calibrated spectrum
(the caption of its Fig. 5: I0 - B(T0) - dT dB/dT - G0 g); the reference
temperature of column 2 (2.725 K) is the later calibration of Fixsen and
Mather (2002), not the paper's 2.728 K. So the file is derived data twice
over, and this module says so on the figure's record.

What this module computes, apart from the record: the Planck intensity

    B_nu(T) = (2 h nu^3 / c^2) / (exp(x) - 1),   x = h nu / (k T),   nu = c nu~,

with nu~ the wavenumber of the file (cm^-1), in MJy/sr (1 Jy = 1e-26
W m^-2 Hz^-1); its derivative in T; and the weighted least-squares fit of
the residual to dT dB/dT + G g(nu), with the file's uncertainties as the
weights. The fit is linear and diagonal: the paper weighted with the full
covariance between frequencies, which the file does not carry (the
reproduction track of ``pbc.products.research_workspace.firas`` treats that
as a typed discrepancy, not this module).

The reference temperature is read from the card (``reference_temperature``),
which quotes the header; ``read_spectrum`` refuses a file whose header names
another one.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from pbc.data.figure_provenance import RESIDUAL, FigureProvenance, card_of, role
from pbc.data.plotting import COLOURS

DATASET = "cobe-firas-monopole"
FILE = "firas_monopole_spec_v1.txt"
FIELDS = ("wavenumber", "monopole", "residual", "sigma", "galaxy")
UNITS = {
    "wavenumber": "cm^-1",
    "monopole": "MJy/sr",
    "residual": "kJy/sr",
    "sigma": "kJy/sr",
    "galaxy": "kJy/sr",
}
ROWS = 43

# SI 2019, exact (CODATA 2018).
H = 6.62607015e-34  # J s
K_B = 1.380649e-23  # J/K
C = 299792458.0  # m/s
# CODATA 1986, with which the file's column 2 is rebuilt to under 1 kJy/sr
# (``rebuild_monopole``); the analysis uses the exact constants above.
H_1986 = 6.6260755e-34  # J s
K_B_1986 = 1.380658e-23  # J/K
MJY = 1e-20  # W m^-2 Hz^-1 sr^-1 per MJy/sr
KJY_PER_MJY = 1000.0
_HEADER_T = re.compile(r"sum\s*of a ([0-9.]+) K BB spectrum")


@dataclass(frozen=True)
class Spectrum:
    wavenumber: np.ndarray  # nu~ [cm^-1]
    monopole: np.ndarray  # column 2 [MJy/sr]
    residual: np.ndarray  # column 3, Table 4 [kJy/sr]
    sigma: np.ndarray  # column 4, 1-sigma, Table 4 [kJy/sr]
    galaxy: np.ndarray  # column 5, Galactic spectrum at the poles, Table 4 [kJy/sr]
    header: tuple[str, ...]  # the comment lines
    t_ref: float  # the reference temperature column 2 is built on [K]


def reference_temperature(card: dict | None = None) -> float:
    """The reference temperature ``T_ref`` (K) the card records."""
    card = card or card_of(DATASET)
    return float(card["reference_temperature"]["value"])


def header_temperature(header: tuple[str, ...]) -> float:
    """The temperature the header names for column 2's blackbody (K)."""
    match = _HEADER_T.search(" ".join(line.lstrip("# ").strip() for line in header))
    if match is None:
        raise ValueError("the header names no reference blackbody")
    return float(match.group(1))


def read_spectrum(path: Path, *, t_ref: float | None = None) -> Spectrum:
    """Read the LAMBDA file (``FILE`` in ``path``, or ``path`` itself).

    ``t_ref`` defaults to the card's reference temperature; a header that
    names another one is refused, so the analysis never runs on a file whose
    reference it does not know.
    """
    path = Path(path)
    if path.is_dir():
        path = path / FILE
    lines = path.read_text(encoding="ascii").splitlines()
    header = tuple(line for line in lines if line.startswith("#"))
    table = np.loadtxt(path, comments="#", ndmin=2)
    if table.shape != (ROWS, len(FIELDS)):
        raise ValueError(
            f"{path}: table {table.shape}, expected ({ROWS}, {len(FIELDS)})"
        )
    wavenumber, monopole, residual, sigma, galaxy = table.T
    if np.any(np.diff(wavenumber) <= 0):
        raise ValueError(f"{path}: wavenumbers not increasing")
    if np.any(sigma <= 0):
        raise ValueError(f"{path}: an uncertainty is not positive")
    stated = header_temperature(header)
    expected = reference_temperature() if t_ref is None else t_ref
    if stated != expected:
        raise ValueError(
            f"{path}: the header's reference blackbody is {stated} K, the card's"
            f" {expected} K"
        )
    return Spectrum(wavenumber, monopole, residual, sigma, galaxy, header, stated)


def planck(wavenumber: np.ndarray, temperature: float, *, h=H, k=K_B) -> np.ndarray:
    """``B_nu(T)`` (MJy/sr) at wavenumbers ``wavenumber`` (cm^-1)."""
    nu = C * 100.0 * np.asarray(wavenumber, dtype=float)
    x = h * nu / (k * temperature)
    return 2 * h * nu**3 / C**2 / np.expm1(x) / MJY


def dplanck_dt(wavenumber: np.ndarray, temperature: float) -> np.ndarray:
    """``dB_nu/dT`` (MJy/sr per K): ``B_nu x e^x / ((e^x - 1) T)``."""
    nu = C * 100.0 * np.asarray(wavenumber, dtype=float)
    x = H * nu / (K_B * temperature)
    return planck(wavenumber, temperature) * x * np.exp(x) / np.expm1(x) / temperature


def rebuild_monopole(spectrum: Spectrum) -> np.ndarray:
    """Column 2 rebuilt as the header says: ``B_nu(T_ref)`` with the CODATA
    1986 constants plus the residual (MJy/sr)."""
    blackbody = planck(spectrum.wavenumber, spectrum.t_ref, h=H_1986, k=K_B_1986)
    return blackbody + spectrum.residual / KJY_PER_MJY


def peak_brightness(temperature: float) -> float:
    """The maximum of ``B_nu(T)`` over frequency (MJy/sr), at x = 2.8214."""
    x_peak = 2.821439372122079  # the root of 3 (1 - e^-x) = x
    wavenumber = x_peak * K_B * temperature / (H * C * 100.0)
    return float(planck(np.array([wavenumber]), temperature)[0])


@dataclass(frozen=True)
class BlackbodyFit:
    delta_t: float  # [K]
    sigma_t: float  # statistical [K]
    galaxy_scale: float  # G, dimensionless multiple of column 5
    sigma_galaxy: float
    model: np.ndarray  # dT dB/dT + G g [kJy/sr]
    chi2: float
    dof: int
    weighted_rms: float  # [kJy/sr]


def weighted_rms(difference: np.ndarray, sigma: np.ndarray) -> float:
    """``sqrt(sum (d/sigma)^2 / sum 1/sigma^2)``: the paper's weighted rms
    (section 6.1, as read on the register entry ``fixsen-1996-firas-spectrum``)."""
    return float(np.sqrt(np.sum((difference / sigma) ** 2) / np.sum(sigma**-2.0)))


def fit_blackbody(spectrum: Spectrum) -> BlackbodyFit:
    """The residual fitted by ``dT dB/dT + G g``, weighted by ``1/sigma^2``."""
    design = np.column_stack(
        [
            dplanck_dt(spectrum.wavenumber, spectrum.t_ref) * KJY_PER_MJY,
            spectrum.galaxy,
        ]
    )
    weights = 1.0 / spectrum.sigma
    a = design * weights[:, None]
    coef, *_ = np.linalg.lstsq(a, spectrum.residual * weights, rcond=None)
    covariance = np.linalg.inv(a.T @ a)
    model = design @ coef
    difference = spectrum.residual - model
    chi2 = float(np.sum((difference / spectrum.sigma) ** 2))
    return BlackbodyFit(
        delta_t=float(coef[0]),
        sigma_t=float(np.sqrt(covariance[0, 0])),
        galaxy_scale=float(coef[1]),
        sigma_galaxy=float(np.sqrt(covariance[1, 1])),
        model=model,
        chi2=chi2,
        dof=len(spectrum.residual) - 2,
        weighted_rms=weighted_rms(difference, spectrum.sigma),
    )


# The provenance of the reference figure (Issue #531).
REFERENCE = FigureProvenance(
    status="processed",
    dataset=DATASET,
    combines=("simulated",),
    artifact="calibrated-observation",
    processing="The file firas_monopole_spec_v1.txt of LAMBDA, unmodified: the"
    " monopole (a 2.725 K blackbody plus the residual of Table 4 of Fixsen et al."
    " 1996), the residual, its 1-sigma uncertainty, and the Galactic spectrum at"
    " the poles. The blackbody at T_ref + dT and the weighted fit of dT and the"
    " Galactic scale: the reference figure's code (pbc.data.reference.cobe_firas),"
    " not part of the record.",
)


def make_figure(data_dir: Path) -> plt.Figure:
    spectrum = read_spectrum(data_dir)
    fit = fit_blackbody(spectrum)
    t_fit = spectrum.t_ref + fit.delta_t
    nu = spectrum.wavenumber
    fine = np.linspace(nu.min(), nu.max(), 400)

    fig, (ax, ax_res) = plt.subplots(
        2,
        1,
        figsize=(8, 8),
        sharex=True,
        height_ratios=(1.6, 1.4),
        constrained_layout=True,
    )
    points = ax.errorbar(
        nu,
        spectrum.monopole,
        yerr=spectrum.sigma / KJY_PER_MJY,
        color="black",
        marker="o",
        ms=3.5,
        ls="none",
        elinewidth=0.8,
        label="FIRAS monopole, column 2 (bars: 1 sigma, smaller than the dots)",
    )
    role(points, "processed")
    (curve,) = ax.plot(
        fine,
        planck(fine, t_fit),
        color=COLOURS[0],
        ls="--",
        lw=1.4,
        label=f"blackbody at T_ref + dT = {t_fit:.6f} K (fit)",
    )
    role(curve, "simulated")
    ax.set_ylabel("intensity I_nu [MJy/sr]")
    ax.set_title(
        "The CMB monopole of COBE FIRAS and a blackbody: the deviations are\n"
        "below the line width (Fixsen et al. 1996, Table 4, as LAMBDA distributes it)",
        fontsize=10,
    )
    ax.legend(fontsize=8, loc="upper right")

    bars = ax_res.errorbar(
        nu,
        spectrum.residual,
        yerr=spectrum.sigma,
        color="black",
        marker="o",
        ms=3.5,
        ls="none",
        elinewidth=0.8,
        label="residual of Table 4, column 3, +/- 1 sigma",
    )
    role(bars, "processed")
    (galaxy,) = ax_res.plot(
        nu,
        fit.galaxy_scale * spectrum.galaxy,
        color=COLOURS[1],
        ls=":",
        lw=1.4,
        marker="s",
        ms=2.5,
        label=f"fitted Galactic term G g, G = {fit.galaxy_scale:.3f}",
    )
    role(galaxy, "simulated")
    (left,) = ax_res.plot(
        nu,
        spectrum.residual - fit.model,
        color=COLOURS[2],
        marker="^",
        ms=3,
        ls="none",
        label=(
            f"residual minus the fit: chi2 = {fit.chi2:.1f} for {fit.dof} dof,"
            f" weighted rms {fit.weighted_rms:.1f} kJy/sr"
        ),
    )
    role(left, RESIDUAL)
    ax_res.axhline(0, color="0.5", lw=0.6)
    ax_res.set_ylabel("residual [kJy/sr]")
    ax_res.set_xlabel("wavenumber nu~ [cm^-1]")
    ax_res.set_title(
        "Residuals: the uncertainty grows at high frequency, where the Galaxy is"
        " brightest;\nthe fit of dT and G on the published residuals is close to"
        " zero by construction",
        fontsize=9,
    )
    ax_res.legend(fontsize=7, loc="lower left")
    return fig
