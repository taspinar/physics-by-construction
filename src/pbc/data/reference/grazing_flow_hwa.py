"""Grazing-flow benchmark (TU Delft, Zenodo 15044105): hot-wire profiles of
a turbulent boundary layer over a solid wall and over two porous inserts.

Status of the figure: *processed* (profiles that the creators averaged from
hot-wire time series and normalised; here put in inner scaling).

The record gives, per wall (D00 solid, D35 and D45 porous) and nominal speed
(15, 20, 25 m/s), five profiles across the insert (x/L = -1/3 ... 1/3,
L = 0.1 m) and one upstream profile (x/L = -6.6), each in U/Ue against
y/delta with the turbulence intensity and a length scale, and a parameter
file per case with Ue, delta, delta*, theta, H, and the air's temperature
and pressure. Three things the files do not say plainly:

- the parameter column headed ``x/L [-]`` holds x in metres (it is x/L
  times L = 0.1 m; ``parameter_x_is_metres`` checks it against the
  profiles);
- no friction velocity is given. Here it is taken from the Coles-Fernholz
  skin friction at the recorded Re_theta (``pbc.data.reference.
  tudelft_boundary_layer.coles_fernholz_utau``), with nu of dry air from the
  recorded T and p;
- for the solid wall, the readme says the y of the profiles "were further
  refined by fitting the plus-unit representation of the boundary layer on
  canonical profiles". The log-law agreement of the solid-wall profiles is
  therefore partly imposed by the providers' processing and is no
  independent measurement of kappa.

``Unc. U/Ue`` is a 95 % half-width of the mean (statistical only); the two
``Unc. TI`` columns are the lower and upper bounds of a 95 % interval of TI,
not half-widths.
"""

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from pbc.data.plotting import COLOURS, add_credit, label_status
from pbc.data.reference.tudelft_boundary_layer import (
    B_REF,
    KAPPA_REF,
    LOG_LOWER,
    LOG_UPPER,
    blasius,
    coles_fernholz_utau,
)

PROFILE_HEADER = (
    "x/L [-]",
    "y/delta [-]",
    "U/Ue [-]",
    "Unc. U/Ue [-]",
    "TI [%]",
    "Unc. TI Upper [%]",
    "Unc. TI Lower [%]",
    "Lambda/delta [-]",
)
PARAMETER_HEADER = (
    "x/L [-]",
    "Ue [m/s]",
    "delta [m]",
    "delta_star [m]",
    "theta [m]",
    "H [-]",
    "T_atm [K]",
    "p_atm [Pa]",
    "Liner [mm]",
    "Velocity [m/s]",
)
WALLS = ("D00", "D35", "D45")  # solid, porous 3.5 mm cells, porous 4.5 mm cells
SPEEDS = ("V15", "V20", "V25")
STATIONS = (-1 / 3, -1 / 6, 0.0, 1 / 6, 1 / 3)  # x/L across the insert
L = 0.1  # m, streamwise length of the insert
R_AIR = 287.05  # J/(kg K), dry air


@dataclass(frozen=True)
class Station:
    """One profile and its parameters."""

    case: str  # e.g. D00V15, UPV15
    x_over_L: float
    y_over_delta: np.ndarray
    U_over_Ue: np.ndarray
    U_uncertainty: np.ndarray  # 95 % half-width of U/Ue
    TI: np.ndarray  # %
    TI_upper: np.ndarray  # % (upper bound of the 95 % interval)
    TI_lower: np.ndarray  # %
    length_scale: np.ndarray  # Lambda/delta; NaN where the record gives none
    Ue: float  # m/s
    delta: float  # m
    delta_star: float  # m
    theta: float  # m
    H: float
    T: float  # K
    p: float  # Pa

    @property
    def nu(self) -> float:
        return air_viscosity(self.T) / (self.p / (R_AIR * self.T))

    @property
    def re_theta(self) -> float:
        return self.Ue * self.theta / self.nu

    @property
    def utau(self) -> float:
        return coles_fernholz_utau(self.Ue, self.re_theta)

    @property
    def re_tau(self) -> float:
        return self.delta * self.utau / self.nu

    @property
    def yplus(self) -> np.ndarray:
        return self.y_over_delta * self.delta * self.utau / self.nu

    @property
    def Uplus(self) -> np.ndarray:
        return self.U_over_Ue * self.Ue / self.utau


def air_viscosity(T: float) -> float:
    """Dynamic viscosity of air by Sutherland's law [kg/(m s)]."""
    return 1.716e-5 * (T / 273.15) ** 1.5 * (273.15 + 110.4) / (T + 110.4)


def _read_csv(path: Path, header: tuple[str, ...]) -> np.ndarray:
    text = Path(path).read_bytes().decode("ascii")
    lines = text.split("\r\n")
    if lines[-1] != "":
        raise ValueError(f"{path}: not CRLF-terminated")
    if tuple(lines[0].split(",")) != header:
        raise ValueError(f"{path}: header {lines[0]!r}, expected {header}")
    return np.array(
        [[float(v) if v else np.nan for v in line.split(",")] for line in lines[1:-1]]
    )


def read_profiles(path: Path) -> np.ndarray:
    return _read_csv(path, PROFILE_HEADER)


def read_parameters(path: Path) -> np.ndarray:
    return _read_csv(path, PARAMETER_HEADER)


def parameter_x_is_metres(profiles: np.ndarray, parameters: np.ndarray) -> bool:
    """The parameter file's ``x/L`` column, divided by L, gives the profiles'
    x/L (sorted): so the column is x in metres."""
    return bool(
        np.allclose(np.unique(profiles[:, 0]), np.sort(parameters[:, 0]) / L, atol=1e-4)
    )


def load_case(data_dir: Path, case: str) -> list[Station]:
    """The stations of one case, upstream to downstream."""
    data_dir = Path(data_dir)
    profiles = read_profiles(data_dir / "HWA_PROFILES_v2" / f"HW_{case}.csv")
    parameters = read_parameters(data_dir / "BL_PARAMETERS" / f"BL_{case}.csv")
    if not parameter_x_is_metres(profiles, parameters):
        raise ValueError(f"{case}: parameter x does not match the profiles' x/L")
    stations = []
    for row in parameters[np.argsort(parameters[:, 0])]:
        x = row[0] / L
        p = profiles[np.isclose(profiles[:, 0], x, atol=1e-4)]
        p = p[np.argsort(p[:, 1])]
        stations.append(
            Station(
                case,
                float(x),
                p[:, 1],
                p[:, 2],
                p[:, 3],
                p[:, 4],
                p[:, 5],
                p[:, 6],
                p[:, 7],
                *(float(v) for v in row[1:8]),
            )
        )
    return stations


def load(data_dir: Path) -> dict[str, list[Station]]:
    cases = [w + s for w in WALLS for s in SPEEDS] + ["UP" + s for s in SPEEDS]
    return {c: load_case(data_dir, c) for c in cases}


def log_fit(station: Station, lower: float = LOG_LOWER, upper: float = LOG_UPPER):
    """kappa, B, and the number of points over lower < y+ and y < upper delta."""
    sel = (station.yplus > lower) & (station.y_over_delta < upper)
    slope, intercept = np.polyfit(np.log(station.yplus[sel]), station.Uplus[sel], 1)
    return float(1.0 / slope), float(intercept), int(sel.sum())


def shape_factor(station: Station) -> float:
    """H from the profile, linear from the wall to the first point, to y = delta."""
    y = np.concatenate(([0.0], station.y_over_delta))
    u = np.concatenate(([0.0], station.U_over_Ue))
    inside = y <= 1.0
    ds = np.trapezoid((1.0 - u)[inside], y[inside])
    th = np.trapezoid((u * (1.0 - u))[inside], y[inside])
    return float(ds / th)


def make_figure(data_dir: Path) -> plt.Figure:
    data = load(data_dir)
    lam = blasius()
    fig, axes = plt.subplots(2, 2, figsize=(11, 8.5), constrained_layout=True)
    (ax_in, ax_out), (ax_ti, ax_h) = axes
    styles = {"V15": "-", "V20": "--", "V25": "-."}
    centre = STATIONS.index(0.0)

    for (speed, ls), colour in zip(styles.items(), COLOURS, strict=False):
        s = data["D00" + speed][centre]
        k, b, _ = log_fit(s)
        ax_in.plot(
            s.yplus,
            s.Uplus,
            "o",
            ls=ls,
            color=colour,
            ms=3,
            lw=1.0,
            label=f"solid, {speed[1:]} m/s, x = 0, Re_tau {s.re_tau:.0f} "
            f"(fit kappa {k:.3f}, B {b:.2f})",
        )
        ax_ti.fill_between(
            s.y_over_delta, s.TI_lower, s.TI_upper, color=colour, alpha=0.3, lw=0
        )  # the record's 95 % interval: narrower than the line
        ax_ti.plot(
            s.y_over_delta,
            s.TI,
            ls=ls,
            color=colour,
            lw=1.2,
            label=f"solid, {speed[1:]} m/s",
        )
    grid = np.logspace(0, np.log10(3000), 200)
    ax_in.plot(
        grid[grid < 15], grid[grid < 15], color="0.3", ls=":", label="U+ = y+ (model)"
    )
    ax_in.plot(
        grid[grid > 20],
        np.log(grid[grid > 20]) / KAPPA_REF + B_REF,
        color="0.3",
        ls="--",
        label=f"log law, kappa {KAPPA_REF}, B {B_REF} (reference, not fitted)",
    )
    ax_in.set_xscale("log")
    ax_in.set_xlabel("y+ [-] (u_tau from Coles-Fernholz, not in the record)")
    ax_in.set_ylabel("U+ [-]")
    ax_in.set_title(
        "Processed: solid wall; y fitted to canonical profiles by the providers",
        fontsize=10,
    )
    ax_in.legend(fontsize=6.5, loc="upper left")

    for wall, colour, mk in (("D00", COLOURS[0], "o"), ("D45", COLOURS[1], "s")):
        s = data[wall + "V25"][-1]
        ax_out.plot(
            s.y_over_delta,
            s.U_over_Ue,
            mk,
            ls="-",
            color=colour,
            ms=3,
            lw=1.0,
            label=f"{'solid' if wall == 'D00' else 'porous 4.5 mm'}, 25 m/s, "
            f"x/L = 1/3, H {s.H:.3f}",
        )
    up = data["UPV25"][0]
    ax_out.plot(
        up.y_over_delta,
        up.U_over_Ue,
        "^",
        ls=":",
        color=COLOURS[2],
        ms=3,
        label=f"upstream, x/L = -6.6, H {up.H:.3f}",
    )
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
    ax_out.set_ylabel("U / Ue [-]")
    ax_out.set_title(
        "Processed: turbulent profiles against the laminar one", fontsize=10
    )
    ax_out.legend(fontsize=7, loc="lower right")

    ax_ti.set_xscale("log")
    ax_ti.set_xlabel("y / delta [-]")
    ax_ti.set_ylabel("turbulence intensity u'_rms / Ue [%]")
    ax_ti.set_title(
        "Processed: TI at x = 0; the record's 95 % bounds are narrower than the lines",
        fontsize=10,
    )
    ax_ti.legend(fontsize=8, loc="upper right")

    for wall, colour, mk, name in (
        ("D00", COLOURS[0], "o", "solid"),
        ("D35", COLOURS[3], "D", "porous 3.5 mm"),
        ("D45", COLOURS[1], "s", "porous 4.5 mm"),
    ):
        for speed, ls in styles.items():
            stations = data[wall + speed]
            ax_h.plot(
                [s.x_over_L for s in stations],
                [s.H for s in stations],
                mk,
                ls=ls,
                color=colour,
                ms=5,
                mfc=colour if speed == "V25" else "none",
                label=f"{name}, {speed[1:]} m/s",
            )
    ax_h.set_xlabel("x / L across the insert [-] (L = 0.1 m)")
    ax_h.set_ylabel("shape factor H [-] (record)")
    ax_h.set_title(
        f"Processed: H over the insert (Blasius: {lam.H:.2f}, off scale)", fontsize=10
    )
    ax_h.legend(fontsize=6.5, loc="upper left", ncol=3)
    ax_h.set_ylim(1.30, 1.47)

    add_credit(
        fig,
        "Data: O. Moriaux, R. Zamponi, 'A benchmark dataset for the grazing flow "
        "over porous materials', Zenodo, v3, doi 10.5281/zenodo.15044105, "
        "CC BY 4.0; files unchanged. u_tau (Coles-Fernholz), nu (Sutherland, "
        "ideal gas), inner scaling, fits, and the Blasius and log-law "
        "references: this figure's code (pbc.data.reference.grazing_flow_hwa), "
        "not part of the record.",
    )
    label_status(fig, "processed")
    return fig
