"""SPARC rotation curves: the measured curve against mass models with a halo.

Status of the figure: *processed*. ``Vobs`` and ``errV`` of a SPARC ``Rotmod``
file are a rotation curve the SPARC team derived from HI and H-alpha velocity
fields (tilted rings, folded to one side, corrected for inclination); the
``Vgas``, ``Vdisk`` and ``Vbul`` columns are the team's models of the
baryons, the circular speeds of the measured gas and of the 3.6 micron light
at a mass-to-light ratio of 1. The fits below, the halos, and the maximum
disk are computed here and drawn apart from the measurement.

The mass model adds the squares of circular speeds, as the potentials of the
components add (Lelli, McGaugh and Schombert 2016, the SPARC paper):

    V^2(r) = Vgas |Vgas| + Y (Vdisk^2 + Vbul^2) + Vhalo^2(r)

with one stellar mass-to-light ratio ``Y`` for the disk and the bulge (both
at 3.6 micron; a separate bulge ratio is a further parameter that only one
galaxy of the sample could constrain). ``Vgas |Vgas|`` keeps the sign of the
file: a negative ``Vgas`` is a net outward pull of the gas (a central hole).
Two halos: the NFW profile, rho = rho_s / ((r/r_s) (1 + r/r_s)^2), cuspy at
the centre, and the pseudo-isothermal sphere, rho = rho_0 / (1 + (r/r_c)^2),
with a core. Without a halo, ``Y`` alone is fitted.

The fit is a model comparison under stated assumptions (the distance, the
inclination folded into ``Vobs``, one ``Y``, circular orbits, spherical
halos), not a measurement of dark matter: ``errV`` excludes the uncertainty of
the distance and the inclination, so the reduced chi-square of a well-sampled
galaxy is large for any smooth model, and ``Y`` and the halo trade against
each other (``stellar_profile``).
"""

import re
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from pbc.data.fit import FitResult, fit_curve
from pbc.data.plotting import COLOURS, add_credit, label_status

GALAXIES = ("NGC3198", "NGC2403", "NGC2841", "DDO154", "NGC2903")
COLUMNS = ("Rad", "Vobs", "errV", "Vgas", "Vdisk", "Vbul", "SBdisk", "SBbul")
UNITS = ("kpc", "km/s", "km/s", "km/s", "km/s", "km/s", "L/pc^2", "L/pc^2")
_DISTANCE = re.compile(r"^# Distance = (\d+(?:\.\d+)?) Mpc$")

# G in kpc (km/s)^2 per solar mass, from the IAU 2015 nominal solar mass
# parameter GM_sun = 1.3271244e20 m^3/s^2 and the IAU 2012 astronomical unit
# (1 pc = 648000/pi au, au = 149597870700 m).
PARSEC = 648000 / np.pi * 149_597_870_700.0  # m
G_KPC = 1.3271244e20 / (1e3 * PARSEC) / 1e6  # kpc (km/s)^2 / M_sun
PC3_PER_KPC3 = 1e9

HALOS = ("none", "nfw", "iso")
HALO_NAMES = {
    "none": "baryons only",
    "nfw": "NFW halo (cusp)",
    "iso": "pseudo-isothermal halo (core)",
}
# Bounds of the fitted parameters: Y, log10 of the halo's radius in kpc, and
# log10 of its density in M_sun/pc^3.
STELLAR_BOUNDS = (0.0, 5.0)
STELLAR_BOUNDS_NO_HALO = (0.0, 50.0)
LOG_RADIUS_BOUNDS = (-1.5, 3.0)
LOG_DENSITY_BOUNDS = (-6.0, 2.0)
# An illustrative error floor, not from the record: 5 % of Vobs added in
# quadrature to errV, the order of the effect of a few degrees of
# inclination on a moderately inclined disk (dV/V = cot(i) di).
FLOOR = 0.05
# The degeneracy panel: the galaxy and the values of Y held fixed.
DEGENERACY_GALAXY = "NGC2403"
PROFILE_VALUES = np.linspace(0.0, 1.2, 31)


@dataclass(frozen=True)
class Galaxy:
    name: str
    distance: float  # Mpc, the file's first line
    radius: np.ndarray  # kpc
    v_obs: np.ndarray  # km/s
    v_err: np.ndarray  # km/s
    v_gas: np.ndarray  # km/s, signed
    v_disk: np.ndarray  # km/s at Y = 1
    v_bulge: np.ndarray  # km/s at Y = 1
    sb_disk: np.ndarray  # L_sun/pc^2 at 3.6 micron
    sb_bulge: np.ndarray  # L_sun/pc^2 at 3.6 micron

    def gas_squared(self) -> np.ndarray:
        return self.v_gas * np.abs(self.v_gas)

    def stars_squared(self, stellar: float) -> np.ndarray:
        return stellar * (self.v_disk**2 + self.v_bulge**2)

    def baryons_squared(self, stellar: float) -> np.ndarray:
        return self.gas_squared() + self.stars_squared(stellar)

    def sigma(self, floor: float = 0.0) -> np.ndarray:
        """``errV``, with ``floor`` times ``Vobs`` added in quadrature."""
        return np.hypot(self.v_err, floor * self.v_obs)


def read_rotmod(path: Path) -> Galaxy:
    """Read a SPARC ``<name>_rotmod.dat`` file and check its three header lines."""
    path = Path(path)
    lines = path.read_text(encoding="ascii").splitlines()
    match = _DISTANCE.match(lines[0])
    if match is None:
        raise ValueError(f"{path}: no distance line: {lines[0]!r}")
    if tuple(lines[1].lstrip("# ").split()) != COLUMNS:
        raise ValueError(f"{path}: unexpected columns: {lines[1]!r}")
    if tuple(lines[2].lstrip("# ").split()) != UNITS:
        raise ValueError(f"{path}: unexpected units: {lines[2]!r}")
    table = np.loadtxt(path, comments="#", ndmin=2)
    if table.shape[1] != len(COLUMNS):
        raise ValueError(f"{path}: {table.shape[1]} columns, not {len(COLUMNS)}")
    return Galaxy(path.name.removesuffix("_rotmod.dat"), float(match[1]), *table.T)


def load(data_dir: Path) -> dict[str, Galaxy]:
    data_dir = Path(data_dir)
    return {name: read_rotmod(data_dir / f"{name}_rotmod.dat") for name in GALAXIES}


def nfw_squared(r: np.ndarray, r_s: float, rho_s: float) -> np.ndarray:
    """Circular speed squared [(km/s)^2] of an NFW halo.

    ``r`` and ``r_s`` in kpc, ``rho_s`` in M_sun/pc^3.
    """
    x = np.asarray(r) / r_s
    mass = 4 * np.pi * rho_s * PC3_PER_KPC3 * r_s**3 * (np.log1p(x) - x / (1 + x))
    return G_KPC * mass / np.asarray(r)


def iso_squared(r: np.ndarray, r_c: float, rho_0: float) -> np.ndarray:
    """Circular speed squared [(km/s)^2] of a pseudo-isothermal sphere.

    ``r`` and ``r_c`` in kpc, ``rho_0`` in M_sun/pc^3.
    """
    r = np.asarray(r)
    return (
        4
        * np.pi
        * G_KPC
        * rho_0
        * PC3_PER_KPC3
        * r_c**2
        * (1 - (r_c / r) * np.arctan(r / r_c))
    )


HALO_SQUARED = {"nfw": nfw_squared, "iso": iso_squared}


def maximum_disk(galaxy: Galaxy) -> float:
    """The largest Y for which the baryons exceed no point's ``Vobs + errV``."""
    room = (galaxy.v_obs + galaxy.v_err) ** 2 - galaxy.gas_squared()
    stars = galaxy.v_disk**2 + galaxy.v_bulge**2
    return float(np.min(room[stars > 0] / stars[stars > 0]))


def ring_luminosity(radius: np.ndarray, surface: np.ndarray) -> float:
    """Light inside the last radius [L_sun]: 2 pi r SB summed by the trapezoid
    rule, the surface brightness held at its first value down to r = 0."""
    r = np.concatenate([[0.0], radius])
    sb = np.concatenate([[surface[0]], surface]) * 1e6  # L_sun/kpc^2
    return float(np.trapezoid(2 * np.pi * r * sb, r))


def normalisation_ratio(galaxy: Galaxy) -> float:
    """Mass implied by ``Vdisk`` at the last radius, ``Vdisk^2 r / G``, over the
    light of ``SBdisk`` inside it. Near 1 when ``Vdisk`` is computed for
    1 M_sun per L_sun; a thin disk's speed at a few scale lengths exceeds the
    Keplerian one of its mass by some per cent, so slightly above 1."""
    mass = galaxy.v_disk[-1] ** 2 * galaxy.radius[-1] / G_KPC
    return mass / ring_luminosity(galaxy.radius, galaxy.sb_disk)


@dataclass(frozen=True)
class MassModel:
    galaxy: str
    halo: str  # "none", "nfw", "iso"
    fit: FitResult
    fixed_stellar: float | None  # Y when it was held, else None
    floor: float

    @property
    def stellar(self) -> float:
        if self.fixed_stellar is not None:
            return self.fixed_stellar
        return self.fit.value("Y")

    @property
    def halo_radius(self) -> float:  # kpc
        return 10 ** self.fit.value("log_r")

    @property
    def halo_density(self) -> float:  # M_sun/pc^3
        return 10 ** self.fit.value("log_rho")

    @property
    def reduced_chi2(self) -> float:
        return self.fit.reduced_chi2

    def halo_squared(self, r: np.ndarray) -> np.ndarray:
        if self.halo == "none":
            return np.zeros_like(np.asarray(r, dtype=float))
        return HALO_SQUARED[self.halo](r, self.halo_radius, self.halo_density)

    def total(self, galaxy: Galaxy) -> np.ndarray:
        """The model's circular speed [km/s] at the radii of the file."""
        squared = galaxy.baryons_squared(self.stellar) + self.halo_squared(
            galaxy.radius
        )
        return np.sqrt(np.clip(squared, 0, None))


def _speed(galaxy: Galaxy, halo: str, stellar, log_r, log_rho) -> np.ndarray:
    """The model's speed, broadcast over arrays of parameters (radius last)."""
    r = galaxy.radius
    squared = galaxy.gas_squared() + np.multiply.outer(
        stellar, galaxy.v_disk**2 + galaxy.v_bulge**2
    )
    if halo != "none":
        rs = np.expand_dims(10.0 ** np.asarray(log_r), -1)
        rho = np.expand_dims(10.0 ** np.asarray(log_rho), -1)
        squared = squared + HALO_SQUARED[halo](r, rs, rho)
    return np.sqrt(np.clip(squared, 0, None))


def _start(galaxy: Galaxy, halo: str, stellar: float | None, sigma: np.ndarray):
    """The best point of a coarse grid, so that the local fit starts in the
    right valley (the chi-square has several in a 3-parameter fit)."""
    if stellar is None:
        top = STELLAR_BOUNDS[1] if halo != "none" else STELLAR_BOUNDS_NO_HALO[1]
        ys = np.linspace(0, top, 51)
    else:
        ys = np.array([stellar])
    if halo == "none":
        chi2 = (((galaxy.v_obs - _speed(galaxy, halo, ys, 0, 0)) / sigma) ** 2).sum(-1)
        return [ys[np.argmin(chi2)]]
    lr = np.linspace(*LOG_RADIUS_BOUNDS, 46)
    ld = np.linspace(*LOG_DENSITY_BOUNDS, 41)
    r2, d2 = np.meshgrid(lr, ld, indexing="ij")
    # One value of Y at a time keeps the memory to one 2-D grid of curves.
    chi2 = np.array(
        [
            (((galaxy.v_obs - _speed(galaxy, halo, y, r2, d2)) / sigma) ** 2).sum(-1)
            for y in ys
        ]
    )
    k = np.unravel_index(np.argmin(chi2), chi2.shape)
    point = [lr[k[1]], ld[k[2]]]
    return ([ys[k[0]]] if stellar is None else []) + point


def fit_mass_model(
    galaxy: Galaxy, halo: str, *, stellar: float | None = None, floor: float = 0.0
) -> MassModel:
    """Fit Y (unless ``stellar`` fixes it) and the halo to ``Vobs``.

    The weights are ``errV``, or ``errV`` with ``floor`` times ``Vobs`` in
    quadrature. The fit is least squares in the speed with absolute sigma, so
    a reduced chi-square far above 1 says that the model or ``errV`` does not
    describe the scatter, and the standard errors are then too small.
    """
    if halo not in HALOS:
        raise ValueError(f"halo {halo!r} is not one of {HALOS}")
    sigma = galaxy.sigma(floor)
    names: list[str] = [] if stellar is not None else ["Y"]
    low: list[float] = []
    high: list[float] = []
    if stellar is None:
        bounds = STELLAR_BOUNDS if halo != "none" else STELLAR_BOUNDS_NO_HALO
        low.append(bounds[0])
        high.append(bounds[1])
    if halo != "none":
        names += ["log_r", "log_rho"]
        low += [LOG_RADIUS_BOUNDS[0], LOG_DENSITY_BOUNDS[0]]
        high += [LOG_RADIUS_BOUNDS[1], LOG_DENSITY_BOUNDS[1]]

    def model(r, *p):
        y = stellar if stellar is not None else p[0]
        halo_p = p[-2:] if halo != "none" else (0.0, 0.0)
        return _speed(galaxy, halo, y, *halo_p)

    p0 = _start(galaxy, halo, stellar, sigma)
    # Keep the start strictly inside the bounds.
    p0 = np.clip(p0, np.array(low) + 1e-9, np.array(high) - 1e-9)
    result = fit_curve(
        model,
        galaxy.radius,
        galaxy.v_obs,
        p0,
        sigma=sigma,
        names=names,
        bounds=(low, high),
    )
    return MassModel(galaxy.name, halo, result, stellar, floor)


def stellar_profile(
    galaxy: Galaxy, halo: str, values: np.ndarray, *, floor: float = 0.0
) -> np.ndarray:
    """Chi-square of the best halo at each fixed Y: the degeneracy of Y."""
    return np.array(
        [fit_mass_model(galaxy, halo, stellar=y, floor=floor).fit.chi2 for y in values]
    )


def analyse(sample: dict[str, Galaxy]) -> dict:
    """The three mass models of every galaxy, with errV and with the floor."""
    fits = {
        (name, halo, floor): fit_mass_model(galaxy, halo, floor=floor)
        for name, galaxy in sample.items()
        for halo in HALOS
        for floor in (0.0, FLOOR)
    }
    return {
        "fits": fits,
        "maximum_disk": {n: maximum_disk(g) for n, g in sample.items()},
        "normalisation": {n: normalisation_ratio(g) for n, g in sample.items()},
    }


def _curve_panel(ax, ax_res, galaxy: Galaxy, fits: dict, styles: dict) -> None:
    r = galaxy.radius
    ax.errorbar(
        r,
        galaxy.v_obs,
        yerr=galaxy.v_err,
        color="black",
        marker="o",
        ms=3.5,
        ls="none",
        elinewidth=0.8,
        label="Vobs +/- errV (SPARC rotation curve)",
    )
    iso = fits["iso"]
    stellar = iso.stellar
    ax.plot(
        r,
        galaxy.v_gas,
        label="gas, Vgas (SPARC model; < 0: net outward pull)",
        color=COLOURS[2],
        ls=":",
        lw=1.5,
    )
    ax.plot(
        r,
        np.sqrt(galaxy.stars_squared(stellar)),
        label=f"stars, sqrt(Y) Vdisk (and Vbul), Y = {stellar:.2f} of the core fit",
        color=COLOURS[3],
        ls=":",
        lw=1.5,
    )
    ax.plot(
        r,
        np.sqrt(iso.halo_squared(r)),
        label="the core fit's halo alone",
        color=COLOURS[1],
        ls=(0, (5, 2, 1, 2)),
        lw=1.0,
    )
    for halo in HALOS:
        m = fits[halo]
        line = {k: v for k, v in styles[halo].items() if k != "marker"}
        ax.plot(
            r,
            m.total(galaxy),
            label=f"{HALO_NAMES[halo]}: chi2/dof = {m.reduced_chi2:.1f}",
            **line,
        )
        ax_res.plot(
            r,
            galaxy.v_obs - m.total(galaxy),
            marker=styles[halo]["marker"],
            ms=3.5,
            color=styles[halo]["color"],
            ls="none",
            label=HALO_NAMES[halo],
        )
    ax_res.errorbar(
        r,
        np.zeros_like(r),
        yerr=galaxy.v_err,
        color="black",
        ls="none",
        elinewidth=0.8,
        label="+/- errV about zero",
    )
    ax_res.axhline(0, color="0.5", lw=0.6)
    ax.set_ylim(0, None)
    ax.set_xlim(0, r.max() * 1.03)
    ax.set_ylabel("circular speed [km/s]")
    ax_res.set_ylabel("residual Vobs - model [km/s]")
    ax_res.set_xlabel(f"radius [kpc] (at D = {galaxy.distance:g} Mpc)")


def make_figure(data_dir: Path) -> plt.Figure:
    sample = load(data_dir)
    result = analyse(sample)
    fits = result["fits"]
    styles = {
        "none": {"color": "0.4", "ls": "-.", "lw": 1.2, "marker": "D"},
        "nfw": {"color": COLOURS[0], "ls": "--", "lw": 1.5, "marker": "s"},
        "iso": {"color": COLOURS[1], "ls": "-", "lw": 1.5, "marker": "^"},
    }

    fig = plt.figure(figsize=(12, 12), constrained_layout=True)
    grid = fig.add_gridspec(3, 2, height_ratios=(3, 1.3, 2.6))
    for col, name in enumerate(("NGC3198", "DDO154")):
        ax = fig.add_subplot(grid[0, col])
        ax_res = fig.add_subplot(grid[1, col], sharex=ax)
        galaxy = sample[name]
        own = {h: fits[(name, h, 0.0)] for h in HALOS}
        _curve_panel(ax, ax_res, galaxy, own, styles)
        plt.setp(ax.get_xticklabels(), visible=False)
        if name == "NGC3198":
            ax.set_title(
                "NGC 3198, a spiral with a flat curve: no Y of the stars and gas\n"
                "alone fits; a halo with a core or a cusp fits, chi2/dof 1.2 to 1.4",
                fontsize=10,
            )
        else:
            ax.set_title(
                "DDO 154, a gas-rich dwarf: the halo dominates; the cusp (NFW)\n"
                "overshoots the inner points, the core does not",
                fontsize=10,
            )
        ax.legend(fontsize=7, loc="lower right")
        ax_res.set_title("Residuals, measured minus each model", fontsize=9)
        ax_res.legend(fontsize=6.5, loc="lower right", ncol=2)

    ax_deg = fig.add_subplot(grid[2, 0])
    name = DEGENERACY_GALAXY
    galaxy = sample[name]
    y_max = result["maximum_disk"][name]
    values = PROFILE_VALUES
    for halo in ("nfw", "iso"):
        for floor, alpha, lw in ((0.0, 1.0, 1.6), (FLOOR, 0.55, 1.0)):
            dof = galaxy.radius.size - 3
            chi2 = stellar_profile(galaxy, halo, values, floor=floor) / dof
            best = fits[(name, halo, floor)]
            which = "errV" if floor == 0 else f"errV + {100 * FLOOR:.0f} % floor"
            ax_deg.plot(
                values,
                chi2,
                color=styles[halo]["color"],
                ls=styles[halo]["ls"],
                lw=lw,
                alpha=alpha,
                label=f"{HALO_NAMES[halo]}, {which}: best Y = {best.stellar:.2f}",
            )
            ax_deg.plot(
                best.stellar,
                best.reduced_chi2,
                ls="none",
                ms=6,
                alpha=alpha,
                marker=styles[halo]["marker"],
                color=styles[halo]["color"],
            )
    ax_deg.axvline(
        y_max,
        color="0.3",
        ls=":",
        lw=1.2,
        label=f"maximum disk, Y = {y_max:.2f} (stars + gas reach Vobs + errV)",
    )
    ax_deg.axhline(1, color="0.5", lw=0.8)
    ax_deg.set_yscale("log")
    ax_deg.set_xlabel(
        "stellar mass-to-light ratio Y at 3.6 micron, held fixed [M_sun/L_sun]"
    )
    ax_deg.set_ylabel("reduced chi-square of the best halo at that Y [1]")
    ax_deg.set_title(
        "NGC 2403: the fitted Y depends on the halo assumed (cusp or core)\n"
        "and on the errors; markers: the best fit of each curve",
        fontsize=10,
    )
    ax_deg.legend(fontsize=6.5, loc="upper left")

    ax_all = fig.add_subplot(grid[2, 1])
    x = np.arange(len(GALAXIES))
    for k, halo in enumerate(HALOS):
        offset = (k - 1) * 0.22
        given = [fits[(n, halo, 0.0)].reduced_chi2 for n in GALAXIES]
        floored = [fits[(n, halo, FLOOR)].reduced_chi2 for n in GALAXIES]
        ax_all.plot(
            x + offset,
            given,
            ls="none",
            marker=styles[halo]["marker"],
            color=styles[halo]["color"],
            ms=7,
            label=f"{HALO_NAMES[halo]}, errV",
        )
        ax_all.plot(
            x + offset,
            floored,
            ls="none",
            marker=styles[halo]["marker"],
            mfc="none",
            color=styles[halo]["color"],
            ms=7,
            label=f"{HALO_NAMES[halo]}, errV + {100 * FLOOR:.0f} % floor",
        )
    ax_all.axhline(1, color="0.5", lw=0.8)
    ax_all.set_yscale("log")
    ax_all.set_ylim(0.05, 3e4)
    ax_all.set_xticks(
        x, [n.replace("NGC", "NGC ").replace("DDO", "DDO ") for n in GALAXIES]
    )
    ax_all.set_xlabel("galaxy of the sample [name]")
    ax_all.set_ylabel("reduced chi-square of the best fit [1]")
    ax_all.set_title(
        "All five: without a halo no fit; with one, chi2/dof depends on errV,\n"
        "which excludes distance and inclination (open markers: a 5 % floor)",
        fontsize=10,
    )
    ax_all.legend(fontsize=6.5, loc="upper right", ncol=2)

    add_credit(
        fig,
        "Data: SPARC (Spitzer Photometry and Accurate Rotation Curves), "
        "https://astroweb.case.edu/SPARC/; Lelli, F., McGaugh, S. S., Schombert, J. M. "
        "2016, AJ 152, 157. Files NGC3198, NGC2403, NGC2841, DDO154, and "
        "NGC2903_rotmod.dat "
        "of Rotmod_LTG.zip, unmodified, redistributed with the authors' permission. "
        "Vgas, Vdisk, Vbul are the SPARC team's models of the baryons. Fits, halos, "
        "and the maximum disk: this figure's code (pbc.data.reference.sparc_rotmod), "
        "not part of the record.",
    )
    label_status(fig, "processed")
    return fig
