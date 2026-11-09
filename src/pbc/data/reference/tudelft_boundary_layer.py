"""TU Delft turbulent boundary layer: mean velocity and Reynolds stresses
by PIV and PTV at four free-stream speeds, against the laminar (Blasius)
boundary layer and the law of the wall.

Status of the figure: *processed* (profiles that the creators averaged from
PIV and PTV fields; here scaled and fitted).

The record (4TU.ResearchData, doi 10.4121/d0af5e8b-6bde-4c02-a165-c752b5ab435a.v1)
gives for each case U05, U10, U15, U20 one MAT v5 file per technique with
the profiles and the integral parameters, including the friction velocity
``Utau``. The readme says the variables sit in a struct ``EXPparam``; they
are top-level variables. It says PTV ``y`` is in metres; it is in
millimetres (the near-wall PTV points give U+ = y+ only in millimetres, and
they then overlap the PIV profile). It names the PIV stresses ``uu`` three
times; the file holds ``uu``, ``uv``, and ``vv``.

The checks this module makes, none of which the record states:

- the friction velocity of the file against the Coles-Fernholz skin
  friction at the file's Re_theta (an empirical correlation, independent of
  the profile's log region);
- the log law U+ = ln(y+)/kappa + B fitted over a stated window, with the
  spread over other common windows as the sensitivity of kappa and B;
- the shape factor H recomputed from the profile (PTV below the first PIV
  point), against the file's H and the laminar 2.591 of Blasius;
- PTV against PIV where both measure;
- the peak of the Reynolds shear stress -u'v'+ against 1, the wall value of
  the total stress in inner units.

The record gives no uncertainty for any profile value and does not say how
``Utau`` was determined, so the log-law constants are those of the file's
``Utau``; the Coles-Fernholz comparison is what checks it.
"""

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.integrate import solve_ivp
from scipy.io import loadmat
from scipy.optimize import brentq

from pbc.data.plotting import COLOURS, add_credit, label_status

CASES = ("U05", "U10", "U15", "U20")
PIV_FIELDS = (
    "H",
    "Ubar",
    "Uinf",
    "Utau",
    "delta",
    "deltastar",
    "mu",
    "rho",
    "theta",
    "uu",
    "uv",
    "vv",
    "y",
)
PTV_FIELDS = ("Ubar", "Uinf", "Utau", "mu", "rho", "y")
PTV_Y_UNIT = 1e-3  # m per unit of the PTV file's y: millimetres
LOG_LOWER = 50.0  # y+: the nominal log window starts here ...
LOG_UPPER = 0.15  # ... and ends at y = 0.15 delta
# The sensitivity of kappa and B: lower bounds in y+ (None: 3 sqrt(Re_tau))
# and upper bounds in y/delta that are common in the literature.
LOG_WINDOWS = tuple(
    (lo, hi) for lo in (30.0, 50.0, 80.0, 100.0, None) for hi in (0.1, 0.15, 0.2)
)
KAPPA_REF, B_REF = 0.41, 5.0  # the reference law of the wall drawn on the figure
SUBLAYER = 5.0  # y+ below which U+ = y+


@dataclass(frozen=True)
class Profile:
    """One technique at one case, in SI units (PTV y converted from mm)."""

    case: str
    technique: str
    y: np.ndarray  # m
    U: np.ndarray  # m/s
    Uinf: float  # m/s
    Utau: float  # m/s
    mu: float  # kg/(m s)
    rho: float  # kg/m^3
    uu: np.ndarray | None = None  # m^2/s^2
    uv: np.ndarray | None = None
    vv: np.ndarray | None = None
    delta: float | None = None  # m
    deltastar: float | None = None
    theta: float | None = None
    H: float | None = None

    @property
    def nu(self) -> float:
        return self.mu / self.rho

    @property
    def yplus(self) -> np.ndarray:
        return self.y * self.Utau / self.nu

    @property
    def Uplus(self) -> np.ndarray:
        return self.U / self.Utau


def read_mat(path: Path, fields: tuple[str, ...]) -> dict[str, np.ndarray]:
    """The variables of a MAT v5 file as flat float arrays; exactly ``fields``,
    each a top-level double (no struct)."""
    raw = {k: v for k, v in loadmat(Path(path)).items() if not k.startswith("__")}
    if sorted(raw) != sorted(fields) or any(
        v.dtype != np.float64 for v in raw.values()
    ):
        raise ValueError(f"{path}: variables {sorted(raw)}, expected doubles {fields}")
    return {k: np.asarray(v, dtype=float).ravel() for k, v in raw.items()}


def read_piv(path: Path, case: str) -> Profile:
    m = read_mat(path, PIV_FIELDS)
    s = {k: float(m[k][0]) for k in PIV_FIELDS if m[k].size == 1}
    return Profile(
        case,
        "PIV",
        m["y"],
        m["Ubar"],
        s["Uinf"],
        s["Utau"],
        s["mu"],
        s["rho"],
        m["uu"],
        m["uv"],
        m["vv"],
        s["delta"],
        s["deltastar"],
        s["theta"],
        s["H"],
    )


def read_ptv(path: Path, case: str) -> Profile:
    m = read_mat(path, PTV_FIELDS)
    s = {k: float(m[k][0]) for k in PTV_FIELDS if m[k].size == 1}
    return Profile(
        case,
        "PTV",
        m["y"] * PTV_Y_UNIT,
        m["Ubar"],
        s["Uinf"],
        s["Utau"],
        s["mu"],
        s["rho"],
    )


def load(data_dir: Path) -> dict[str, tuple[Profile, Profile]]:
    """(PIV, PTV) for every case."""
    data_dir = Path(data_dir)
    return {
        c: (
            read_piv(data_dir / "PIV" / c / "EXPparam.mat", c),
            read_ptv(data_dir / "PTV" / c / "EXPparam.mat", c),
        )
        for c in CASES
    }


def re_tau(piv: Profile) -> float:
    return piv.delta * piv.Utau / piv.nu


def re_theta(piv: Profile) -> float:
    return piv.Uinf * piv.theta / piv.nu


def coles_fernholz_utau(Uinf: float, Re_theta: float) -> float:
    """u_tau from Cf = 2 [ln(Re_theta)/0.384 + 4.127]^-2 (Nagib et al. 2007)."""
    cf = 2.0 * (np.log(Re_theta) / 0.384 + 4.127) ** -2
    return float(Uinf * np.sqrt(cf / 2.0))


def log_fit(piv: Profile, lower: float | None = LOG_LOWER, upper: float = LOG_UPPER):
    """kappa, B, and the number of points of U+ = ln(y+)/kappa + B over the
    window lower < y+ and y < upper delta (lower None: 3 sqrt(Re_tau))."""
    lo = 3.0 * np.sqrt(re_tau(piv)) if lower is None else lower
    sel = (piv.yplus > lo) & (piv.y < upper * piv.delta)
    slope, intercept = np.polyfit(np.log(piv.yplus[sel]), piv.Uplus[sel], 1)
    return float(1.0 / slope), float(intercept), int(sel.sum())


def log_fit_range(piv: Profile) -> tuple[tuple[float, float], tuple[float, float]]:
    """(min, max) of kappa and of B over ``LOG_WINDOWS``."""
    fits = [log_fit(piv, lo, hi) for lo, hi in LOG_WINDOWS]
    kappa = [f[0] for f in fits]
    b = [f[1] for f in fits]
    return (min(kappa), max(kappa)), (min(b), max(b))


def spliced(piv: Profile, ptv: Profile) -> tuple[np.ndarray, np.ndarray]:
    """y and U/U_inf from the wall: zero at the wall, PTV below the first PIV
    point (each technique scaled by its own U_inf), then PIV."""
    below = ptv.y < piv.y.min()
    y = np.concatenate(([0.0], ptv.y[below], piv.y))
    u = np.concatenate(([0.0], ptv.U[below] / ptv.Uinf, piv.U / piv.Uinf))
    return y, u


def shape_factor(
    y: np.ndarray, u: np.ndarray, delta: float
) -> tuple[float, float, float]:
    """delta*, theta, and H by the trapezoid rule from the wall to delta."""
    inside = y <= delta
    ds = float(np.trapezoid((1.0 - u)[inside], y[inside]))
    th = float(np.trapezoid((u * (1.0 - u))[inside], y[inside]))
    return ds, th, ds / th


def ptv_over_piv(piv: Profile, ptv: Profile) -> tuple[float, float]:
    """Mean and max of (U/U_inf by PTV) / (U/U_inf by PIV) where both measure."""
    over = ptv.y >= piv.y.min()
    ratio = (ptv.U[over] / ptv.Uinf) / (np.interp(ptv.y[over], piv.y, piv.U) / piv.Uinf)
    return float(ratio.mean()), float(ratio.max())


def sublayer_deviation(ptv: Profile) -> float:
    """Mean of U+/y+ - 1 over the PTV points with y+ < ``SUBLAYER``."""
    sel = ptv.yplus < SUBLAYER
    return float(np.mean(ptv.Uplus[sel] / ptv.yplus[sel]) - 1.0)


def shear_stress_peak(piv: Profile) -> float:
    """The maximum of -u'v' / u_tau^2."""
    return float(np.max(-piv.uv / piv.Utau**2))


@dataclass(frozen=True)
class Blasius:
    eta: np.ndarray  # y sqrt(U / (nu x))
    u: np.ndarray  # U / U_inf
    wall_curvature: float  # f''(0)
    eta99: float
    displacement: float  # delta* in units of sqrt(nu x / U)
    momentum: float  # theta in the same units
    H: float


def blasius(eta_max: float = 10.0) -> Blasius:
    """The laminar boundary layer, f''' + f f'' / 2 = 0, f(0) = f'(0) = 0,
    f'(inf) = 1, by shooting on f''(0)."""

    def run(curvature: float):
        return solve_ivp(
            lambda _, f: (f[1], f[2], -0.5 * f[0] * f[2]),
            (0.0, eta_max),
            (0.0, 0.0, curvature),
            rtol=1e-11,
            atol=1e-12,
            dense_output=True,
        )

    curvature = brentq(lambda a: run(a).y[1, -1] - 1.0, 0.2, 0.5, xtol=1e-13)
    sol = run(curvature)
    eta = np.linspace(0.0, eta_max, 20001)
    u = sol.sol(eta)[1]
    eta99 = float(brentq(lambda e: sol.sol(e)[1] - 0.99, 3.0, 7.0, xtol=1e-12))
    ds = float(np.trapezoid(1.0 - u, eta))
    th = float(np.trapezoid(u * (1.0 - u), eta))
    return Blasius(eta, u, float(curvature), eta99, ds, th, ds / th)


def make_figure(data_dir: Path) -> plt.Figure:
    data = load(data_dir)
    lam = blasius()
    fig, axes = plt.subplots(2, 2, figsize=(11, 8.5), constrained_layout=True)
    (ax_in, ax_out), (ax_uv, ax_h) = axes
    markers = ("o", "s", "^", "D")
    styles = ("-", "--", "-.", ":")

    for (case, (piv, ptv)), colour, ls, mk in zip(
        data.items(), COLOURS, styles, markers, strict=False
    ):
        k, b, _ = log_fit(piv)
        ax_in.plot(
            piv.yplus,
            piv.Uplus,
            color=colour,
            ls=ls,
            lw=1.2,
            label=f"{case} PIV, Re_tau {re_tau(piv):.0f} "
            f"(fit kappa {k:.3f}, B {b:.2f})",
        )
        ax_in.plot(
            ptv.yplus,
            ptv.Uplus,
            mk,
            color=colour,
            ms=2.5,
            mfc="none",
            label=f"{case} PTV",
        )
        y, u = spliced(piv, ptv)
        ax_out.plot(y / piv.delta, u, color=colour, ls=ls, lw=1.2, label=f"{case}")
        ax_uv.plot(
            piv.y / piv.delta,
            -piv.uv / piv.Utau**2,
            color=colour,
            ls=ls,
            lw=1.2,
            label=f"{case} PIV",
        )
        ax_h.plot(
            re_theta(piv),
            piv.H,
            mk,
            color=colour,
            ms=7,
            label=f"{case}: H {piv.H:.3f} (file)",
        )
        ax_h.plot(
            re_theta(piv),
            shape_factor(y, u, piv.delta)[2],
            mk,
            color=colour,
            ms=7,
            mfc="none",
            label=f"{case}: H recomputed from the profile",
        )

    grid = np.logspace(0, np.log10(5000), 200)
    ax_in.plot(
        grid[grid < 15],
        grid[grid < 15],
        color="0.3",
        ls=":",
        lw=1.0,
        label="viscous sublayer U+ = y+ (model)",
    )
    ax_in.plot(
        grid[grid > 20],
        np.log(grid[grid > 20]) / KAPPA_REF + B_REF,
        color="0.3",
        ls="--",
        lw=1.0,
        label=f"log law, kappa {KAPPA_REF}, B {B_REF} (reference, not fitted)",
    )
    ax_in.set_xscale("log")
    ax_in.set_xlabel("y+ = y u_tau / nu [-]")
    ax_in.set_ylabel("U+ = U / u_tau [-]")
    ax_in.set_title("Processed: inner scaling with the file's u_tau", fontsize=10)
    ax_in.set_ylim(0, 45)  # headroom: the legend sits above the profiles
    ax_in.legend(fontsize=6.5, loc="upper left")

    ax_out.plot(
        lam.eta / lam.eta99,
        lam.u,
        color="0.2",
        ls=(0, (5, 2, 1, 2)),
        lw=1.6,
        label=f"Blasius laminar layer, H {lam.H:.3f} (model)",
    )
    ax_out.set_xlim(0, 1.3)
    ax_out.set_xlabel("y / delta [-] (laminar: y / delta_99)")
    ax_out.set_ylabel("U / U_inf [-]")
    ax_out.set_title(
        "Processed: the turbulent profiles are far fuller than the laminar one",
        fontsize=10,
    )
    ax_out.legend(fontsize=8, loc="lower right")

    ax_uv.axhline(
        1.0, color="0.3", ls="--", lw=1.0, label="wall shear stress, -u'v'+ = 1"
    )
    ax_uv.set_xscale("log")
    ax_uv.set_xlabel("y / delta [-]")
    ax_uv.set_ylabel("-u'v' / u_tau^2 [-]")
    ax_uv.set_title("Processed: Reynolds shear stress, PIV", fontsize=10)
    ax_uv.legend(fontsize=8, loc="lower left")

    ax_h.axhline(
        lam.H, color="0.2", ls=(0, (5, 2, 1, 2)), lw=1.4, label="Blasius (model)"
    )
    ax_h.set_xscale("log")
    ax_h.set_ylim(1.0, 2.8)
    ax_h.set_xlabel("Re_theta = U_inf theta / nu [-]")
    ax_h.set_ylabel("shape factor H = delta* / theta [-]")
    ax_h.set_title("Processed: H, turbulent against laminar", fontsize=10)
    ax_h.legend(fontsize=6.5, loc="center right", ncol=1)

    add_credit(
        fig,
        "Data: M. Knoop, A. Hassanein, W. Baars, 'Dataset underlying the "
        "publication: Development and characterisation of a turbulent boundary "
        "layer facility at the Delft University of Technology', 4TU.ResearchData, "
        "doi 10.4121/d0af5e8b-6bde-4c02-a165-c752b5ab435a.v1, CC BY 4.0; PTV y "
        "converted from mm to m. Inner scaling, fits, recomputed H, and the "
        "Blasius and log-law references: this figure's code "
        "(pbc.data.reference.tudelft_boundary_layer), not part of the record.",
    )
    label_status(fig, "processed")
    return fig
