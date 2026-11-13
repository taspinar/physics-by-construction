"""The experiment of the lesson "Turbulent boundary layer measurements lab".

The laminar boundary layer of the Navier-Stokes equations of the lessons
"Navier-Stokes fundamentals" and "Vortex formation and flow around
obstacles" (the Blasius layer of ``pbc.fluids.boundary_layer``) against two
measured turbulent boundary layers: the TU Delft PIV and PTV profiles at
four speeds (card ``tudelft-turbulent-boundary-layer``) and the hot-wire
profiles over the solid wall of the grazing-flow benchmark (card
``grazing-flow-hwa-benchmark``), both as committed samples. The experiment
checks its Blasius solution against the reference module's, compares the
measured layers with the laminar prediction, puts them in wall units, fits
the log law with its window as the dominant uncertainty, checks the
assumption of independent residuals, and compares the two records on the
law and on the turbulence intensity. Run it as a program to write the
figures and the numbers of the page:

    uv run --locked --no-dev python -m \\
        pbc.fluids.experiments.turbulent_boundary_layer_measurements out
"""

from dataclasses import replace
from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.ticker import NullFormatter

from pbc.data import SAMPLES_DIR
from pbc.data.adapters import boundary_layer_profile_series, hot_wire_profile_series
from pbc.data.fit import FitResult, fit_curve
from pbc.data.plotting import COLOURS, add_credit, label_status
from pbc.data.reference import grazing_flow_hwa, tudelft_boundary_layer
from pbc.data.reference.grazing_flow_hwa import Station
from pbc.data.reference.tudelft_boundary_layer import Profile
from pbc.experiment import Experiment, main
from pbc.fluids.boundary_layer import (
    Blasius,
    blasius,
    coles_fernholz_friction,
    integral_thicknesses,
    laminar_layer,
    log_law,
    sublayer,
    thickness_99,
)

TUDELFT = "tudelft-turbulent-boundary-layer"
GRAZING = "grazing-flow-hwa-benchmark"
# region: choices
STATION_X = 6.8  # m, the TU Delft station's distance (the record's description)
LOG_LOWER = 50.0  # y+, the nominal log window starts here ...
LOG_UPPER = 0.15  # ... and ends at y = 0.15 delta
LOG_WINDOWS = tudelft_boundary_layer.LOG_WINDOWS  # 15 windows for the sensitivity
SOLID = ("D00V15", "D00V20", "D00V25")  # the solid-wall hot-wire cases
CENTRE = 2  # the station x/L = 0 of the five across the insert
OUTER = (0.1, 0.3, 0.5)  # y/delta where the intensities are compared
KAPPA_REF, B_REF = 0.41, 5.0  # the reference law drawn, not fitted
# endregion: choices
CREDIT = (
    "Data: M. Knoop, A. Hassanein, W. Baars, TU Delft turbulent boundary layer, "
    "4TU.ResearchData, doi 10.4121/d0af5e8b-6bde-4c02-a165-c752b5ab435a.v1; "
    "O. Moriaux, R. Zamponi, grazing-flow benchmark, Zenodo, doi "
    "10.5281/zenodo.15044105; both CC BY 4.0, files unchanged. Scaling, fits, "
    "hot-wire u_tau and models: this lesson's code."
)
STYLES = ("-", "--", "-.", ":")
MARKERS = ("o", "s", "^", "D")
LAMINAR = "0.2"  # the grey of the models
HOT_WIRE = COLOURS[4]  # every hot-wire profile; the speeds by their markers


def load_records() -> tuple[dict[str, tuple[Profile, Profile]], dict[str, Station]]:
    """The committed samples: (PIV, PTV) of each TU Delft case, and the
    solid-wall hot-wire profile at x = 0 of each speed."""
    tudelft = tudelft_boundary_layer.load(SAMPLES_DIR / TUDELFT)
    stations = solid_stations()
    return tudelft, {case: stations[case][CENTRE] for case in SOLID}


def solid_stations() -> dict[str, list[Station]]:
    """The five stations across the insert of every solid-wall case."""
    directory = SAMPLES_DIR / GRAZING
    return {case: grazing_flow_hwa.load_case(directory, case) for case in SOLID}


def tudelft_delta99(piv: Profile) -> float:
    """delta_99 of a TU Delft PIV profile (m), where U / U_inf reaches 0.99."""
    return thickness_99(piv.y, piv.U / piv.Uinf)


def hot_wire_delta99(s: Station) -> float:
    """delta_99 of a hot-wire profile (m), where U / Ue reaches 0.99."""
    return thickness_99(s.y_over_delta, s.U_over_Ue) * s.delta


def speed_name(case: str) -> str:
    """'D00V15' -> '15 m/s'."""
    return case[-2:] + " m/s"


# The records without a model.


def record_table(experiment: Experiment, tudelft: dict, hot_wire: dict) -> dict:
    """What each profile is: speed, thickness, Reynolds numbers, H of the
    record, u_tau and where it comes from."""
    rows, found = [], {"re-tau": [], "re-theta": []}
    for case, (piv, ptv) in tudelft.items():
        re_theta = tudelft_boundary_layer.re_theta(piv)
        re_tau = tudelft_boundary_layer.re_tau(piv)
        friction = coles_fernholz_friction(piv.Uinf, re_theta)
        found["re-tau"].append(re_tau)
        found["re-theta"].append(re_theta)
        rows.append(
            (
                f"TU Delft {case}",
                f"PIV {piv.y.size}, PTV {ptv.y.size}",
                piv.Uinf,
                1e3 * piv.delta,
                1e3 * tudelft_delta99(piv),
                re_theta,
                re_tau,
                piv.H,
                piv.Utau,
                f"file; Coles-Fernholz {100 * (piv.Utau / friction - 1):+.2f} %",
            )
        )
    for case, s in hot_wire.items():
        rows.append(
            (
                f"hot wire, solid, {speed_name(case)}",
                f"{s.y_over_delta.size}",
                s.Ue,
                1e3 * s.delta,
                1e3 * hot_wire_delta99(s),
                s.re_theta,
                s.re_tau,
                s.H,
                s.utau,
                "Coles-Fernholz (none in the record)",
            )
        )
    experiment.table(
        "records",
        rows,
        columns=[
            ("profile", "", "s"),
            ("points", "", "s"),
            ("U_inf", "m/s", ".2f"),
            ("delta, record", "mm", ".1f"),
            ("delta_99, from the profile", "mm", ".1f"),
            ("Re_theta", "", ".0f"),
            ("Re_tau", "", ".0f"),
            ("H, record", "", ".3f"),
            ("u_tau", "m/s", ".3f"),
            ("u_tau from", "", "s"),
        ],
        caption="The profiles of the lab: the four TU Delft speeds (PIV and PTV) and "
        "the solid-wall hot-wire profiles at the middle station (x = 0) of the "
        "grazing-flow benchmark. delta, theta and H are the records'; delta_99 is "
        "where U / U_inf reaches 0.99 in the profile; Re_tau uses the record's "
        "delta and the u_tau of the last column.",
    )
    return found


# The laminar model checked.


def blasius_check(experiment: Experiment) -> tuple[Blasius, dict]:
    """This lesson's Blasius solution (RK4 and Toepfer's scaling) against the
    reference module's (SciPy's adaptive solver and a root search)."""
    ours = blasius()
    theirs = tudelft_boundary_layer.blasius()
    pairs = [
        ("wall curvature f''(0)", ours.wall_curvature, theirs.wall_curvature),
        ("eta at u/U = 0.99", ours.eta99, theirs.eta99),
        ("delta* / sqrt(nu x / U)", ours.displacement, theirs.displacement),
        ("theta / sqrt(nu x / U)", ours.momentum, theirs.momentum),
        ("H = delta* / theta", ours.shape_factor, theirs.H),
    ]
    experiment.table(
        "blasius",
        [(name, a, b, abs(a / b - 1)) for name, a, b in pairs],
        columns=[
            ("quantity", "", "s"),
            ("this lesson (RK4, scaling)", "", ".6f"),
            ("reference module (solve_ivp, root search)", "", ".6f"),
            ("relative difference", "", ".1e"),
        ],
        caption="The Blasius layer by two independent solvers of the same equation.",
    )
    return ours, {"worst": max(abs(a / b - 1) for _, a, b in pairs)}


def laminar_comparison(experiment: Experiment, tudelft: dict, lam: Blasius) -> dict:
    """The laminar layer of the same plate, speed and air at x = STATION_X,
    against the measured turbulent layer: thickness, momentum thickness,
    skin friction."""
    rows, ratios = [], {"delta": [], "theta": [], "cf": [], "re-x": []}
    for case, (piv, _) in tudelft.items():
        laminar = laminar_layer(lam, piv.Uinf, piv.nu, STATION_X)
        cf = 2.0 * (piv.Utau / piv.Uinf) ** 2
        ratios["delta"].append(tudelft_delta99(piv) / laminar["delta99"])
        ratios["theta"].append(piv.theta / laminar["momentum"])
        ratios["cf"].append(cf / laminar["skin_friction"])
        ratios["re-x"].append(laminar["Re_x"])
        rows.append(
            (
                case,
                f"{laminar['Re_x']:.1e}",
                1e3 * laminar["delta99"],
                1e3 * tudelft_delta99(piv),
                1e3 * laminar["momentum"],
                1e3 * piv.theta,
                1e3 * laminar["skin_friction"],
                1e3 * cf,
            )
        )
    experiment.table(
        "laminar",
        rows,
        columns=[
            ("case", "", "s"),
            ("Re_x", "", "s"),
            ("laminar delta_99", "mm", ".1f"),
            ("measured delta_99", "mm", ".1f"),
            ("laminar theta", "mm", ".2f"),
            ("measured theta", "mm", ".2f"),
            ("laminar C_f", "1e-3", ".2f"),
            ("measured C_f", "1e-3", ".2f"),
        ],
        caption="The Blasius layer of a plate 6.8 m long at each speed, against the "
        "TU Delft layer: the measured C_f is 2 (u_tau / U_inf)^2 with the file's "
        "u_tau, theta is the file's, delta_99 is read from the PIV profile.",
    )
    return ratios


def shape_factors(tudelft: dict, stations: dict) -> dict:
    """H of every profile: the TU Delft records', recomputed from the profile
    with PTV next to the wall, and the hot-wire records' at every solid
    station."""
    recomputed = []
    for piv, ptv in tudelft.values():
        y, u = tudelft_boundary_layer.spliced(piv, ptv)
        recomputed.append(integral_thicknesses(y, u, piv.delta)[2])
    return {
        "tudelft": np.array([piv.H for piv, _ in tudelft.values()]),
        "recomputed": np.array(recomputed),
        "hot-wire": np.array([s.H for case in SOLID for s in stations[case]]),
        "hot-wire-re-theta": np.array(
            [s.re_theta for case in SOLID for s in stations[case]]
        ),
    }


# Wall units and the log law.


def window(yplus: np.ndarray, y_over_delta: np.ndarray, lower, upper: float):
    """The points of a log window: lower < y+ (None: 3 sqrt(Re_tau)) and
    y < upper delta."""
    return (yplus > lower) & (y_over_delta < upper)


def log_fit(yplus: np.ndarray, uplus: np.ndarray) -> FitResult:
    """U+ = ln(y+) / kappa + B fitted by ``fit_curve`` to the points given.
    With no uncertainty given, its standard errors come from the scatter
    about the line, as if the residuals were independent."""
    return fit_curve(
        lambda x, kappa, b: log_law(x, kappa, b),
        yplus,
        uplus,
        [0.4, 5.0],
        names=("kappa", "B"),
    )


def neighbour_correlation(residuals: np.ndarray) -> float:
    """The correlation of each residual with the next one along the profile."""
    c = residuals - residuals.mean()
    return float(np.sum(c[1:] * c[:-1]) / np.sum(c**2))


def tudelft_log_law(piv: Profile) -> dict:
    """The nominal fit, its least-squares errors and residual correlation,
    and the range of kappa and B over the windows of the literature."""
    y_over_delta = piv.y / piv.delta
    inside = window(piv.yplus, y_over_delta, LOG_LOWER, LOG_UPPER)
    nominal = log_fit(piv.yplus[inside], piv.Uplus[inside])
    kappas, bs = [], []
    for lower, upper in LOG_WINDOWS:
        lo = (
            3.0 * np.sqrt(tudelft_boundary_layer.re_tau(piv))
            if lower is None
            else lower
        )
        sel = window(piv.yplus, y_over_delta, lo, upper)
        fit = log_fit(piv.yplus[sel], piv.Uplus[sel])
        kappas.append(fit.value("kappa"))
        bs.append(fit.value("B"))
    rho = neighbour_correlation(nominal.residuals)
    n = int(inside.sum())
    return {
        "fit": nominal,
        "points": n,
        "kappa": nominal.value("kappa"),
        "B": nominal.value("B"),
        "kappa-error": float(nominal.stderr[0]),
        "rho": rho,
        # Independent points that n points with neighbour correlation rho
        # are worth, for the error of a mean (an AR(1) series).
        "effective": n * (1.0 - rho) / (1.0 + rho),
        "kappa-range": (min(kappas), max(kappas)),
        "B-range": (min(bs), max(bs)),
    }


def friction_sensitivity(piv: Profile, change: float = 0.01) -> tuple[float, float]:
    """How far kappa and B of the nominal fit move when u_tau is ``change``
    (relative) larger: the profile rescaled and fitted again."""
    before = tudelft_log_law(piv)
    after = tudelft_log_law(replace(piv, Utau=piv.Utau * (1.0 + change)))
    return after["kappa"] - before["kappa"], after["B"] - before["B"]


def log_law_table(experiment: Experiment, tudelft: dict) -> dict:
    found = {case: tudelft_log_law(piv) for case, (piv, _) in tudelft.items()}
    experiment.table(
        "log-law",
        [
            (
                case,
                f["points"],
                f["kappa"],
                f["B"],
                f"{f['kappa-range'][0]:.3f} to {f['kappa-range'][1]:.3f}",
                f"{f['B-range'][0]:.2f} to {f['B-range'][1]:.2f}",
                f["kappa-error"],
                f["rho"],
                f["effective"],
            )
            for case, f in found.items()
        ],
        columns=[
            ("case", "", "s"),
            ("points", "", "d"),
            ("kappa", "", ".3f"),
            ("B", "", ".2f"),
            ("kappa, 15 windows", "", "s"),
            ("B, 15 windows", "", "s"),
            ("standard error of kappa, residuals independent", "", ".4f"),
            ("correlation of neighbouring residuals", "", ".2f"),
            ("independent points they are worth", "", ".1f"),
        ],
        caption="The log law fitted to the TU Delft PIV profiles with the file's "
        "u_tau over 50 < y+ and y < 0.15 delta, the range over 15 windows in use in "
        "the literature, and the assumption of independent residuals checked.",
    )
    return found


def hot_wire_log_law(experiment: Experiment, stations: dict) -> dict:
    """The log law of every solid-wall hot-wire profile, u_tau from
    Coles-Fernholz, over the nominal window: by speed, the range over the
    five stations."""
    rows, kappas, bs, points = [], [], [], []
    for case in SOLID:
        fits = []
        for s in stations[case]:
            sel = window(s.yplus, s.y_over_delta, LOG_LOWER, LOG_UPPER)
            fits.append((log_fit(s.yplus[sel], s.Uplus[sel]), int(sel.sum())))
        k = [f.value("kappa") for f, _ in fits]
        b = [f.value("B") for f, _ in fits]
        n = [m for _, m in fits]
        kappas += k
        bs += b
        points += n
        rows.append(
            (
                speed_name(case),
                f"{min(n)} to {max(n)}",
                f"{min(k):.3f} to {max(k):.3f}",
                f"{min(b):.2f} to {max(b):.2f}",
                f"{min(s.H for s in stations[case]):.3f} to "
                f"{max(s.H for s in stations[case]):.3f}",
            )
        )
    experiment.table(
        "hot-wire-log-law",
        rows,
        columns=[
            ("speed", "", "s"),
            ("points in the window", "", "s"),
            ("kappa", "", "s"),
            ("B", "", "s"),
            ("H, record", "", "s"),
        ],
        caption="The log law of the solid-wall hot-wire profiles at the five stations "
        "across the insert, over the same window, with u_tau from the Coles-Fernholz "
        "correlation; the providers fitted the wall position of these profiles to "
        "canonical profiles.",
    )
    return {
        "kappa": (min(kappas), max(kappas)),
        "B": (min(bs), max(bs)),
        "points": (min(points), max(points)),
    }


# The turbulence intensity.


def tudelft_intensity(piv: Profile) -> np.ndarray:
    """u'_rms / U_inf in % of the PIV profile."""
    return 100.0 * np.sqrt(piv.uu) / piv.Uinf


def intensity_table(experiment: Experiment, tudelft: dict, hot_wire: dict) -> dict:
    """The streamwise turbulence intensity u'_rms / U_inf at three heights in
    the outer layer, and the largest u'+ of each profile with its y+."""
    rows, outer = [], {"tudelft": [], "hot-wire": []}
    for case, (piv, _) in tudelft.items():
        ti = np.interp(OUTER, piv.y / tudelft_delta99(piv), tudelft_intensity(piv))
        uplus = np.sqrt(piv.uu) / piv.Utau
        k = int(np.argmax(uplus))
        outer["tudelft"].append(ti)
        rows.append((f"TU Delft {case}, PIV", *ti, uplus[k], piv.yplus[k]))
    for case, s in hot_wire.items():
        ti = np.interp(OUTER, s.y_over_delta * s.delta / hot_wire_delta99(s), s.TI)
        uplus = s.TI / 100.0 * s.Ue / s.utau
        k = int(np.argmax(uplus))
        outer["hot-wire"].append(ti)
        rows.append((f"hot wire, solid, {speed_name(case)}", *ti, uplus[k], s.yplus[k]))
    experiment.table(
        "intensity",
        rows,
        columns=[
            ("profile", "", "s"),
            ("TI at y/delta_99 0.1", "%", ".2f"),
            ("TI at y/delta_99 0.3", "%", ".2f"),
            ("TI at y/delta_99 0.5", "%", ".2f"),
            ("largest u'+", "", ".2f"),
            ("at y+", "", ".0f"),
        ],
        caption="The streamwise turbulence intensity u'_rms / U_inf, interpolated at "
        "three heights in units of delta_99, and the largest u'_rms / u_tau of each "
        "profile with its wall distance (hot wire: u_tau from Coles-Fernholz).",
    )
    return {k: np.array(v) for k, v in outer.items()}


# The figures.


def _straight(ax, x_ends, value, **kwargs) -> None:
    """A model line drawn from its two ends (on a log axis, a straight line
    in ln x): a long run of collinear points rasterises differently from one
    call to the next, and the page's figure has to be the same bytes."""
    ends = np.array(x_ends, dtype=float)
    ax.plot(ends, value(ends), **kwargs)


def draw_outer_profiles(
    tudelft: dict, hot_wire: dict, lam: Blasius, factors: dict
) -> Figure:
    """Left: U/U_inf against y/delta, measured and laminar; right: H against
    Re_theta for both records and the laminar value."""
    fig, (prof, shape) = plt.subplots(
        1,
        2,
        figsize=(6.0, 3.1),
        constrained_layout=True,
        gridspec_kw={"width_ratios": [1.3, 1.0]},
    )
    for k, (case, (piv, ptv)) in enumerate(tudelft.items()):
        y, u = tudelft_boundary_layer.spliced(piv, ptv)
        status = boundary_layer_profile_series(piv).status
        prof.plot(
            y / tudelft_delta99(piv),
            u,
            ls=STYLES[k],
            lw=1.0,
            color=COLOURS[k],
            label=f"TU Delft {case}, PTV + PIV [{status}]",
        )
    for k, (case, s) in enumerate(hot_wire.items()):
        series = hot_wire_profile_series(s)
        prof.plot(
            series.x * s.delta / hot_wire_delta99(s),
            series.y,
            ls="none",
            marker=MARKERS[k + 1],
            ms=3.0,
            mew=0,
            color=HOT_WIRE,
            label=f"hot wire, {speed_name(case)} [{series.status}]",
        )
    prof.plot(
        lam.eta[::20] / lam.eta99,
        lam.u[::20],
        ls=(0, (5, 2, 1, 2)),
        lw=1.6,
        color=LAMINAR,
        label="Blasius laminar layer [simulated]",
    )
    prof.set_xlim(0, 1.3)
    prof.set_ylim(0, 1.08)
    prof.set_xlabel("y / delta_99 [1]")
    prof.set_ylabel("U / U_inf [1]")
    prof.set_title("Mean velocity, outer scaling", fontsize=10)
    prof.legend(fontsize=5.5, loc="lower right", labelspacing=0.2, borderpad=0.3)

    re_theta = [tudelft_boundary_layer.re_theta(piv) for piv, _ in tudelft.values()]
    shape.plot(
        re_theta,
        factors["tudelft"],
        ls="none",
        marker="o",
        ms=5,
        color=COLOURS[0],
        label="TU Delft, H of the record [processed]",
    )
    shape.plot(
        re_theta,
        factors["recomputed"],
        ls="none",
        marker="o",
        ms=7,
        mfc="none",
        color=COLOURS[0],
        label="TU Delft, H recomputed from the profile",
    )
    shape.plot(
        factors["hot-wire-re-theta"],
        factors["hot-wire"],
        ls="none",
        marker="s",
        ms=4,
        mew=0,
        color=HOT_WIRE,
        label="hot wire, solid, 15 stations [processed]",
    )
    _straight(
        shape,
        (2.0e3, 1.5e4),
        lambda x: np.full_like(x, lam.shape_factor),
        ls=(0, (5, 2, 1, 2)),
        lw=1.4,
        color=LAMINAR,
        label="Blasius laminar layer [simulated]",
    )
    shape.set_xscale("log")
    shape.set_xticks([3000, 5000, 10000], labels=["3000", "5000", "10000"])
    shape.xaxis.set_minor_formatter(NullFormatter())
    shape.set_ylim(1.0, 2.8)
    shape.set_xlabel("Re_theta = U_inf theta / nu [1]")
    shape.set_ylabel("H = delta* / theta [1]")
    shape.set_title("Shape factor, turbulent and laminar", fontsize=10)
    shape.legend(fontsize=5.5, loc="center right")
    add_credit(fig, CREDIT)
    label_status(fig, "processed")
    return fig


def draw_wall_units(tudelft: dict, hot_wire: dict, fits: dict) -> Figure:
    """U+ against y+ for both records with the sublayer and the reference
    log law; below, the residuals of each profile from its own fit inside
    the nominal window."""
    fig, (top, res) = plt.subplots(
        2,
        1,
        figsize=(6.0, 5.0),
        constrained_layout=True,
        sharex=True,
        gridspec_kw={"height_ratios": [1.6, 1.0]},
    )
    for k, (case, (piv, ptv)) in enumerate(tudelft.items()):
        status = boundary_layer_profile_series(piv).status
        top.plot(
            piv.yplus,
            piv.Uplus,
            ls=STYLES[k],
            lw=1.0,
            color=COLOURS[k],
            label=f"TU Delft {case}, PIV [{status}]",
            zorder=3,
        )
        top.plot(
            ptv.yplus,
            ptv.Uplus,
            ls="none",
            marker="o",
            ms=2.2,
            mfc="none",
            mew=0.6,
            color=COLOURS[k],
            label=f"TU Delft {case}, PTV [{status}]",
        )
        inside = window(piv.yplus, piv.y / piv.delta, LOG_LOWER, LOG_UPPER)
        res.plot(
            piv.yplus[inside],
            fits[case]["fit"].residuals,
            ls=STYLES[k],
            lw=1.0,
            color=COLOURS[k],
            label=f"TU Delft {case}",
        )
    for k, (case, s) in enumerate(hot_wire.items()):
        status = hot_wire_profile_series(s).status
        top.plot(
            s.yplus,
            s.Uplus,
            ls="none",
            marker=MARKERS[k + 1],
            ms=3.2,
            mew=0,
            color=HOT_WIRE,
            label=f"hot wire, {speed_name(case)} [{status}]",
        )
        sel = window(s.yplus, s.y_over_delta, LOG_LOWER, LOG_UPPER)
        res.plot(
            s.yplus[sel],
            log_fit(s.yplus[sel], s.Uplus[sel]).residuals,
            ls="none",
            marker=MARKERS[k + 1],
            ms=3.2,
            mew=0,
            color=HOT_WIRE,
            label=f"hot wire, {speed_name(case)}",
        )
    # U+ = y+ is curved on a log axis: drawn through points spaced in ln y+.
    grid = np.exp(np.linspace(np.log(0.5), np.log(15.0), 24))
    top.plot(
        grid,
        sublayer(grid),
        ls=":",
        lw=1.2,
        color=LAMINAR,
        label="viscous sublayer U+ = y+ [simulated]",
    )
    # The log law is straight on a log axis: drawn from its two ends.
    _straight(
        top,
        (20.0, 6000.0),
        lambda x: log_law(x, KAPPA_REF, B_REF),
        ls="--",
        lw=1.2,
        color=LAMINAR,
        label="log law, kappa 0.41, B 5.0, not fitted [simulated]",
    )
    top.set_xscale("log")
    top.set_xlim(0.5, 6000)
    top.set_ylim(0, 40)
    top.set_ylabel("U+ = U / u_tau [1]")
    top.set_title("Mean velocity in wall units", fontsize=10)
    top.legend(fontsize=5.5, loc="upper left", ncols=2)
    res.axhline(0, color="0.4", lw=0.8)
    res.set_ylim(-0.6, 0.6)
    res.set_xlabel("y+ = y u_tau / nu [1]")
    res.set_ylabel("residual of U+ [1]")
    res.set_title(
        "Residuals of each profile from its own log-law fit, 50 < y+, y < 0.15 delta",
        fontsize=9,
    )
    res.legend(fontsize=5.5, loc="lower left", ncols=4)
    add_credit(fig, CREDIT)
    label_status(fig, "processed")
    return fig


def draw_turbulence_intensity(tudelft: dict, hot_wire: dict) -> Figure:
    """Left: u'_rms / U_inf against y/delta, PIV and hot wire; right: the
    Reynolds shear stress of the PIV in wall units."""
    fig, (ti_ax, uv_ax) = plt.subplots(
        1, 2, figsize=(6.0, 3.1), constrained_layout=True
    )
    for k, (case, (piv, _)) in enumerate(tudelft.items()):
        y = piv.y / tudelft_delta99(piv)
        ti_ax.plot(
            y,
            tudelft_intensity(piv),
            ls=STYLES[k],
            lw=1.0,
            color=COLOURS[k],
            label=f"TU Delft {case}, PIV [processed]",
        )
        uv_ax.plot(
            y,
            -piv.uv / piv.Utau**2,
            ls=STYLES[k],
            lw=1.0,
            color=COLOURS[k],
            label=f"TU Delft {case}, PIV [processed]",
        )
    for k, (case, s) in enumerate(hot_wire.items()):
        ti_ax.plot(
            s.y_over_delta * s.delta / hot_wire_delta99(s),
            s.TI,
            ls="none",
            marker=MARKERS[k + 1],
            ms=3.2,
            mew=0,
            color=HOT_WIRE,
            label=f"hot wire, {speed_name(case)} [processed]",
        )
    ti_ax.set_xscale("log")
    ti_ax.set_xlim(2e-3, 2.0)
    ti_ax.set_ylim(0, 24)
    ti_ax.set_xlabel("y / delta_99 [1]")
    ti_ax.set_ylabel("u'_rms / U_inf [%]")
    ti_ax.set_title("Streamwise turbulence intensity", fontsize=10)
    ti_ax.legend(fontsize=5.5, loc="upper right")
    uv_ax.axhline(
        1.0, color=LAMINAR, ls="--", lw=1.0, label="total stress at the wall, 1"
    )
    uv_ax.set_xscale("log")
    uv_ax.set_xlim(2e-3, 2.0)
    uv_ax.set_ylim(-0.1, 1.4)
    uv_ax.set_xlabel("y / delta_99 [1]")
    uv_ax.set_ylabel("-u'v' / u_tau^2 [1]")
    uv_ax.set_title("Reynolds shear stress, PIV", fontsize=10)
    uv_ax.legend(fontsize=5.5, loc="lower center")
    add_credit(fig, CREDIT)
    label_status(fig, "processed")
    return fig


# The exercises.


def viscous_length_exercise() -> None:
    """Exercise 1: the viscous length at the highest TU Delft speed, and where
    the first PIV point and the log window lie in millimetres."""
    utau, nu = 0.6408, 1.50e-5  # m/s, m^2/s: the U20 file, rounded
    length = nu / utau
    print(f"viscous length nu/u_tau: {1e6 * length:.1f} micrometres")
    print(f"the log window begins at y = {1e3 * 50 * length:.2f} mm")
    print(f"the PIV spacing in wall units: {0.28e-3 / length:.0f}")


def laminar_plate_exercise() -> None:
    """Exercise 2: the length of plate a laminar layer would need to grow the
    momentum thickness the turbulent layer has at 6.8 m."""
    speed, nu, theta = 4.574, 1.50e-5, 10.04e-3  # U05: m/s, m^2/s, m
    x = speed / nu * (theta / 0.664) ** 2
    print(f"the measured momentum thickness: {1e3 * theta:.2f} mm")
    print(f"the laminar layer reaches it at x = {x:.0f} m")
    print(f"that is {x / 6.8:.0f} times the turbulent layer's distance")


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    tudelft, hot_wire = load_records()
    stations = solid_stations()

    found = record_table(experiment, tudelft, hot_wire)
    experiment.number("re-tau-low", min(found["re-tau"]), ".0f")
    experiment.number("re-tau-high", max(found["re-tau"]), ".0f")
    experiment.number("re-theta-low", min(found["re-theta"]), ".0f")
    experiment.number("re-theta-high", max(found["re-theta"]), ".0f")
    deviation = [
        piv.Utau
        / coles_fernholz_friction(piv.Uinf, tudelft_boundary_layer.re_theta(piv))
        - 1
        for piv, _ in tudelft.values()
    ]
    experiment.number("utau-deviation", 100 * max(abs(d) for d in deviation), ".1f")
    record_over_99 = [piv.delta / tudelft_delta99(piv) for piv, _ in tudelft.values()]
    experiment.number("delta-record-low", min(record_over_99), ".2f")
    experiment.number("delta-record-high", max(record_over_99), ".2f")
    hot = list(hot_wire.values())
    hot_over_99 = [abs(s.delta / hot_wire_delta99(s) - 1) for s in hot]
    experiment.number("hw-delta-gap", 100 * max(hot_over_99), ".1f")
    experiment.number("hw-re-tau-low", min(s.re_tau for s in hot), ".0f")
    experiment.number("hw-re-tau-high", max(s.re_tau for s in hot), ".0f")
    experiment.number("hw-points", hot[0].y_over_delta.size)
    experiment.number(
        "hw-u-uncertainty",
        max(float(np.max(s.U_uncertainty)) for c in SOLID for s in stations[c]),
        ".5f",
    )

    lam, check = blasius_check(experiment)
    experiment.number("blasius-worst", 1e6 * check["worst"], ".1f")
    experiment.number("blasius-curvature", lam.wall_curvature, ".4f")
    experiment.number("blasius-h", lam.shape_factor, ".3f")
    experiment.number("blasius-eta99", lam.eta99, ".2f")

    ratios = laminar_comparison(experiment, tudelft, lam)
    for name, spec in (("delta", ".0f"), ("theta", ".0f"), ("cf", ".0f")):
        experiment.number(f"{name}-ratio-low", min(ratios[name]), spec)
        experiment.number(f"{name}-ratio-high", max(ratios[name]), spec)
    experiment.number("re-x-low", min(ratios["re-x"]) / 1e6, ".1f")
    experiment.number("re-x-high", max(ratios["re-x"]) / 1e6, ".1f")

    factors = shape_factors(tudelft, stations)
    every = np.concatenate([factors["tudelft"], factors["hot-wire"]])
    experiment.number("h-low", every.min(), ".2f")
    experiment.number("h-high", every.max(), ".2f")
    experiment.number("h-tudelft-low", factors["tudelft"].min(), ".3f")
    experiment.number("h-tudelft-high", factors["tudelft"].max(), ".3f")
    experiment.number("h-hw-low", factors["hot-wire"].min(), ".3f")
    experiment.number("h-hw-high", factors["hot-wire"].max(), ".3f")
    gap = np.abs(factors["recomputed"] / factors["tudelft"] - 1)
    experiment.number("h-recomputed-gap", 100 * gap.max(), ".1f")

    fits = log_law_table(experiment, tudelft)
    kappas = [f["kappa"] for f in fits.values()]
    bs = [f["B"] for f in fits.values()]
    experiment.number("kappa-round", np.mean(kappas), ".1f")
    experiment.number("kappa-low", min(kappas), ".2f")
    experiment.number("kappa-high", max(kappas), ".2f")
    experiment.number("b-low", min(bs), ".1f")
    experiment.number("b-high", max(bs), ".1f")
    experiment.number(
        "kappa-window-low", min(f["kappa-range"][0] for f in fits.values()), ".2f"
    )
    experiment.number(
        "kappa-window-high", max(f["kappa-range"][1] for f in fits.values()), ".2f"
    )
    experiment.number(
        "b-window-low", min(f["B-range"][0] for f in fits.values()), ".1f"
    )
    experiment.number(
        "b-window-high", max(f["B-range"][1] for f in fits.values()), ".1f"
    )
    experiment.number(
        "kappa-error-high", max(f["kappa-error"] for f in fits.values()), ".4f"
    )
    experiment.number("rho-low", min(f["rho"] for f in fits.values()), ".2f")
    experiment.number(
        "effective-high", max(f["effective"] for f in fits.values()), ".0f"
    )
    experiment.number("points-low", min(f["points"] for f in fits.values()))
    experiment.number("points-high", max(f["points"] for f in fits.values()))
    inflated = [
        f["kappa-error"] * np.sqrt(f["points"] / f["effective"]) for f in fits.values()
    ]
    experiment.number("kappa-error-inflated", max(inflated), ".3f")
    window_half = max(
        (f["kappa-range"][1] - f["kappa-range"][0]) / 2 for f in fits.values()
    )
    experiment.number("kappa-window-half", window_half, ".2f")

    shifts = [friction_sensitivity(piv) for piv, _ in tudelft.values()]
    experiment.number("utau-kappa-shift", max(abs(k) for k, _ in shifts), ".3f")
    experiment.number("utau-b-shift", max(abs(b) for _, b in shifts), ".2f")

    hw = hot_wire_log_law(experiment, stations)
    experiment.number("hw-kappa-low", hw["kappa"][0], ".2f")
    experiment.number("hw-kappa-high", hw["kappa"][1], ".2f")
    experiment.number("hw-b-low", hw["B"][0], ".1f")
    experiment.number("hw-b-high", hw["B"][1], ".1f")
    experiment.number("hw-points-low", hw["points"][0])
    experiment.number("hw-points-high", hw["points"][1])

    outer = intensity_table(experiment, tudelft, hot_wire)
    gaps = outer["tudelft"].mean(0) - outer["hot-wire"].mean(0)
    experiment.number("ti-gap-low", gaps.min(), ".1f")
    experiment.number("ti-gap-high", gaps.max(), ".1f")
    experiment.number(
        "ti-gap-relative", 100 * np.max(gaps / outer["hot-wire"].mean(0)), ".0f"
    )
    experiment.number("ti-low", min(v.min() for v in outer.values()), ".1f")
    experiment.number("ti-high", max(v.max() for v in outer.values()), ".1f")
    piv_peaks = [
        float(np.max(np.sqrt(piv.uu) / piv.Utau)) for piv, _ in tudelft.values()
    ]
    hw_peaks = [float(np.max(s.TI / 100 * s.Ue / s.utau)) for s in hot]
    places = [float(s.yplus[np.argmax(s.TI)]) for s in hot]
    experiment.number("hw-peak-yplus", np.mean(places), ".0f")
    experiment.number("piv-peak-low", min(piv_peaks), ".1f")
    experiment.number("piv-peak-high", max(piv_peaks), ".1f")
    experiment.number("hw-peak-low", min(hw_peaks), ".1f")
    experiment.number("hw-peak-high", max(hw_peaks), ".1f")
    stress = [tudelft_boundary_layer.shear_stress_peak(p) for p, _ in tudelft.values()]
    experiment.number("stress-low", min(stress), ".2f")
    experiment.number("stress-high", max(stress), ".2f")
    ptv = [tudelft_boundary_layer.ptv_over_piv(p, t)[0] for p, t in tudelft.values()]
    experiment.number("ptv-piv-low", 100 * (min(ptv) - 1), ".1f")
    experiment.number("ptv-piv-high", 100 * (max(ptv) - 1), ".1f")

    experiment.figure(
        "fig-outer-profiles",
        partial(draw_outer_profiles, tudelft, hot_wire, lam, factors),
    )
    experiment.figure(
        "fig-wall-units", partial(draw_wall_units, tudelft, hot_wire, fits)
    )
    experiment.figure(
        "fig-turbulence-intensity",
        partial(draw_turbulence_intensity, tudelft, hot_wire),
    )

    with experiment.capture("viscous-length-exercise"):
        viscous_length_exercise()
    with experiment.capture("laminar-plate-exercise"):
        laminar_plate_exercise()
    return experiment


if __name__ == "__main__":
    main(run)
