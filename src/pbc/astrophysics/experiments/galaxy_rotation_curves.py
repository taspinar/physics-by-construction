"""The experiment of the lesson "Galaxy rotation curves lab".

The Newtonian circular-speed model of a disk galaxy
(``pbc.astrophysics.rotation_curves``), checked by summing the pull of thin
shells, against measured rotation curves (the committed sample of the card
``sparc-rotation-curves``): five SPARC galaxies with the team's speeds of
their gas and stars. The experiment fits the mass models of the reference
module with and without a dark halo, tests whether the residuals are
independent, varies the inclination, the distance, and the error floor that
the files do not carry, compares a cusp with a core, and shows the
degeneracy of the stellar mass-to-light ratio. Run it as a program to write
the figures and the numbers of the page:

    uv run --locked --no-dev python -m \\
        pbc.astrophysics.experiments.galaxy_rotation_curves out
"""

from dataclasses import replace
from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.astrophysics.rotation_curves import (
    G_KPC,
    circular_speed_squared,
    enclosed_mass,
    iso_density,
    nfw_density,
    shell_sum_speed_squared,
)
from pbc.data import SAMPLES_DIR
from pbc.data.adapters import rotation_curve_series
from pbc.data.plotting import COLOURS, add_credit, label_status
from pbc.data.reference.sparc_rotmod import (
    GALAXIES,
    HALOS,
    PROFILE_VALUES,
    Galaxy,
    MassModel,
    fit_mass_model,
    iso_squared,
    load,
    maximum_disk,
    nfw_squared,
    stellar_profile,
)
from pbc.experiment import Experiment, main

DATASET = "sparc-rotation-curves"
# region: choices
FLOORS = (0.05, 0.10)  # error floors, a fraction of Vobs in quadrature
SPEED_SCALES = (0.9, 1.1)  # a common scale of Vobs and errV: the inclination
DISTANCE_SCALES = (0.8, 1.25)  # the distance: radii x k, baryon speeds x sqrt(k)
BAR_RADIUS = 1.0  # kpc; NGC 2903 refitted without the points inside it
# endregion: choices
# The model check: two halos with given parameters (radius in kpc, density
# in M_sun/pc^3), at given radii, the shells summed out to OUTER.
CHECK_HALOS = (
    ("NFW", nfw_density, nfw_squared, 10.0, 0.01),
    ("pseudo-isothermal", iso_density, iso_squared, 2.0, 0.05),
)
CHECK_RADII = (0.5, 2.0, 10.0, 40.0)
OUTER = 100.0  # kpc
CHECK_BOUND = 1e-9
CREDIT = (
    "Data: SPARC, https://astroweb.case.edu/SPARC/; Lelli, McGaugh, Schombert 2016, "
    "AJ 152, 157. Rotmod files unmodified, with the authors' permission. Vgas, "
    "Vdisk, Vbul: the SPARC team's models; fits: this lesson's code."
)
STYLES = {
    "none": {"color": "0.35", "ls": "-.", "marker": "D"},
    "nfw": {"color": COLOURS[0], "ls": "--", "marker": "s"},
    "iso": {"color": COLOURS[1], "ls": "-", "marker": "^"},
}
MARK = {"none": "\u25c6", "nfw": "\u25a0", "iso": "\u25b2"}  # residual markers
FIT_LABEL = {
    "none": "fit: baryons only",
    "nfw": "fit: NFW, cusp",
    "iso": "fit: isothermal, core",
}
SHORT = {"none": "baryons only", "nfw": "NFW halo", "iso": "isothermal halo"}


def load_sample() -> dict[str, Galaxy]:
    """The committed sample: five Rotmod files, unmodified."""
    return load(SAMPLES_DIR / DATASET)


def at_least(value: float, decimals: int) -> str:
    """``value`` rounded down, for a statement "at least ..."."""
    scale = 10**decimals
    return f"{np.floor(value * scale) / scale:.{decimals}f}"


def pretty(name: str) -> str:
    """NGC3198 as NGC 3198."""
    return name.replace("NGC", "NGC ").replace("DDO", "DDO ")


# The systematics the files do not carry.


def scaled_speed(galaxy: Galaxy, k: float) -> Galaxy:
    """Vobs and errV times ``k``: a different inclination, since the
    deprojected speed is the measured one over sin i."""
    return replace(galaxy, v_obs=galaxy.v_obs * k, v_err=galaxy.v_err * k)


def at_distance(galaxy: Galaxy, k: float) -> Galaxy:
    """The galaxy ``k`` times farther: radii times k, and the light and the
    gas mass times k^2, so the speeds of the baryons times sqrt(k)."""
    q = np.sqrt(k)
    return replace(
        galaxy,
        distance=galaxy.distance * k,
        radius=galaxy.radius * k,
        v_gas=galaxy.v_gas * q,
        v_disk=galaxy.v_disk * q,
        v_bulge=galaxy.v_bulge * q,
    )


def outside(galaxy: Galaxy, radius: float) -> Galaxy:
    """The rows of the file beyond ``radius``."""
    keep = galaxy.radius > radius
    columns = ("radius", "v_obs", "v_err", "v_gas", "v_disk", "v_bulge")
    rows = {c: getattr(galaxy, c)[keep] for c in (*columns, "sb_disk", "sb_bulge")}
    return replace(galaxy, **rows)


def fit_all(galaxy: Galaxy, floor: float = 0.0) -> dict[str, MassModel]:
    """The three mass models of one galaxy."""
    return {halo: fit_mass_model(galaxy, halo, floor=floor) for halo in HALOS}


def normalised_residuals(galaxy: Galaxy, model: MassModel) -> np.ndarray:
    return (galaxy.v_obs - model.total(galaxy)) / galaxy.sigma(model.floor)


def neighbour_correlation(galaxy: Galaxy, model: MassModel) -> float:
    """The correlation of each normalised residual with the next point's."""
    r = normalised_residuals(galaxy, model)
    return float(np.corrcoef(r[:-1], r[1:])[0, 1])


# The model before the data.


def model_check(experiment: Experiment) -> dict:
    """The circular speed of two halos three ways: the closed form the fits
    use, G M(<r)/r with M integrated from the density, and the pull of
    every thin shell summed numerically, with the part of the outer shells."""
    rows, worst, worst_outer = [], 0.0, 0.0

    def below(value: float) -> str:
        return "below 1e-9" if abs(value) < CHECK_BOUND else f"{value:.1e}"

    for name, density, closed, radius, rho in CHECK_HALOS:
        profile = (
            partial(density, r_s=radius, rho_s=rho)
            if density is nfw_density
            else partial(density, r_c=radius, rho_0=rho)
        )
        for r in CHECK_RADII:
            exact = float(closed(np.array(r), radius, rho))
            from_mass = circular_speed_squared(enclosed_mass(profile, r), r)
            summed, outer = shell_sum_speed_squared(profile, r, OUTER)
            d_mass = from_mass / exact - 1
            d_sum = summed / exact - 1
            share = outer / exact
            worst = max(worst, abs(d_mass), abs(d_sum))
            worst_outer = max(worst_outer, abs(share))
            rows.append(
                (name, r, np.sqrt(exact), below(d_mass), below(d_sum), below(share))
            )
    experiment.table(
        "model-check",
        rows,
        columns=[
            ("halo", "", "s"),
            ("radius", "kpc", "g"),
            ("closed form", "km/s", ".2f"),
            ("G M(<r)/r, relative difference", "", "s"),
            ("shell sum, relative difference", "", "s"),
            ("outer shells' share", "", "s"),
        ],
        caption="The circular speed of an NFW halo (scale radius 10 kpc, density "
        "0.01 M_sun/pc^3) and a pseudo-isothermal halo (core 2 kpc, 0.05 "
        "M_sun/pc^3): the closed form of the fits, G M(<r)/r with the mass "
        "integrated from the density, and the pull of every thin shell out to "
        "100 kpc summed numerically; the last column is the part of v^2 from the "
        "shells outside r.",
    )
    return {"worst": worst, "worst-outer": worst_outer}


# The record.


def record_table(experiment: Experiment, sample: dict[str, Galaxy]) -> dict:
    """What the files hold, without a model."""
    rows = []
    for name in GALAXIES:
        g = sample[name]
        series = rotation_curve_series(g)
        rows.append(
            (
                pretty(name),
                g.distance,
                int(series.x.size),
                float(series.x[0]),
                float(series.x[-1]),
                float(series.y.max()),
                float(series.sigma.min()),
                float(np.median(series.sigma)),
                float(series.sigma.max()),
                "yes" if g.v_bulge.max() > 0 else "no",
            )
        )
    experiment.table(
        "record",
        rows,
        columns=[
            ("galaxy", "", "s"),
            ("distance", "Mpc", "g"),
            ("points", "", "d"),
            ("first radius", "kpc", ".2f"),
            ("last radius", "kpc", ".2f"),
            ("highest Vobs", "km/s", ".0f"),
            ("smallest errV", "km/s", ".2f"),
            ("median errV", "km/s", ".2f"),
            ("largest errV", "km/s", ".2f"),
            ("bulge", "", "s"),
        ],
        caption="The five Rotmod files of the sample: the adopted distance, the "
        "points of the rotation curve, their radii, the highest speed, and errV.",
    )
    every = np.concatenate([sample[n].v_err for n in GALAXIES])
    radii = np.concatenate([sample[n].radius for n in GALAXIES])
    return {
        "points": sum(int(sample[n].radius.size) for n in GALAXIES),
        "errv-low": float(every.min()),
        "errv-high": float(every.max()),
        "radius-low": float(radii.min()),
        "radius-high": float(radii.max()),
    }


# The fits.


def stellar_text(model: MassModel) -> tuple[str, str]:
    """Y and its standard error as the page shows them."""
    i = model.fit.names.index("Y")
    if model.stellar < 0.005:
        return "0.00", "at the bound"
    error = float(model.fit.stderr[i])
    return f"{model.stellar:.2f}", "not identified" if not np.isfinite(error) else (
        f"{error:.2f}"
    )


def fit_table(experiment: Experiment, sample: dict, fits: dict) -> None:
    """Every galaxy with the three mass models: Y, the halo, the reduced
    chi-square with errV, and the correlation of neighbouring residuals."""
    rows = []
    for name in GALAXIES:
        g = sample[name]
        for halo in HALOS:
            m = fits[name][halo]
            y, y_err = stellar_text(m)
            radius = "" if halo == "none" else f"{m.halo_radius:.2f}"
            density = "" if halo == "none" else f"{m.halo_density:.4f}"
            rows.append(
                (
                    pretty(name),
                    SHORT[halo],
                    y,
                    y_err,
                    radius,
                    density,
                    m.reduced_chi2,
                    neighbour_correlation(g, m),
                )
            )
    experiment.table(
        "fits",
        rows,
        columns=[
            ("galaxy", "", "s"),
            ("model", "", "s"),
            ("Y", "M_sun/L_sun", "s"),
            ("standard error", "M_sun/L_sun", "s"),
            ("halo radius", "kpc", "s"),
            ("halo density", "M_sun/pc^3", "s"),
            ("reduced chi-square", "", ".2f"),
            ("neighbour correlation", "", "+.2f"),
        ],
        caption="The mass models fitted to Vobs with errV: the stellar "
        "mass-to-light ratio Y at 3.6 micron with the fit's standard error, the "
        "halo's radius (NFW scale radius, isothermal core) and central density "
        "scale, the reduced chi-square, and the correlation of each normalised "
        "residual with the next point's.",
    )


def variants(sample: dict) -> dict[str, tuple[dict[str, Galaxy], float]]:
    """The record as given and with each systematic it does not carry."""
    out = {"errV as given": (sample, 0.0)}
    for floor in FLOORS:
        out[f"errV + {100 * floor:.0f} % floor"] = (sample, floor)
    for k in SPEED_SCALES:
        out[f"Vobs x {k:g} (inclination)"] = (
            {n: scaled_speed(g, k) for n, g in sample.items()},
            0.0,
        )
    for k in DISTANCE_SCALES:
        out[f"distance x {k:g}"] = (
            {n: at_distance(g, k) for n, g in sample.items()},
            0.0,
        )
    return out


def robustness_table(experiment: Experiment, sample: dict) -> dict:
    """For each variant: how far the baryons alone stay from the best halo,
    the cusp and the core of DDO 154, and Y of NGC 2403 with each halo."""
    rows, found = [], {}
    for label, (galaxies, floor) in variants(sample).items():
        fits = {n: fit_all(g, floor) for n, g in galaxies.items()}
        none = [fits[n]["none"].reduced_chi2 for n in GALAXIES]
        best = [
            min(fits[n]["nfw"].reduced_chi2, fits[n]["iso"].reduced_chi2)
            for n in GALAXIES
        ]
        ratio = min(a / b for a, b in zip(none, best, strict=True))
        ddo = fits["DDO154"]
        n2403 = fits["NGC2403"]
        row = (
            label,
            min(none),
            max(best),
            ratio,
            ddo["nfw"].reduced_chi2,
            ddo["iso"].reduced_chi2,
            n2403["nfw"].stellar,
            n2403["iso"].stellar,
        )
        found[label] = row
        rows.append(row)
    experiment.table(
        "robustness",
        rows,
        columns=[
            ("variant", "", "s"),
            ("baryons only, lowest", "chi2/dof", ".1f"),
            ("best halo, highest", "chi2/dof", ".2f"),
            ("baryons over best halo, smallest", "", ".1f"),
            ("DDO 154, cusp", "chi2/dof", ".2f"),
            ("DDO 154, core", "chi2/dof", ".2f"),
            ("NGC 2403, Y with the cusp", "M_sun/L_sun", ".2f"),
            ("NGC 2403, Y with the core", "M_sun/L_sun", ".2f"),
        ],
        caption="The fits redone with each systematic that the files do not "
        "carry: an error floor added to errV, a common scale of the speeds (a "
        "different inclination), and a different distance. Over the five "
        "galaxies: the lowest reduced chi-square of the baryons alone, the "
        "highest of the better halo, and the smallest ratio of the two for one "
        "galaxy; then the two halos of DDO 154 and Y of NGC 2403. A range of "
        "the choices, not an uncertainty interval.",
    )
    return found


# The figures.


def _curve(ax, galaxy: Galaxy, label: bool) -> None:
    ax.errorbar(
        galaxy.radius,
        galaxy.v_obs,
        yerr=galaxy.v_err,
        color="black",
        marker="o",
        ms=2.2,
        ls="none",
        elinewidth=0.6,
        label="Vobs, measured [processed]" if label else None,
    )


def draw_curves(sample: dict[str, Galaxy]) -> Figure:
    """The five rotation curves with errV, and the team's speeds of the gas
    and of the stars at Y = 1."""
    fig, axes = plt.subplots(2, 3, figsize=(6.4, 3.5), constrained_layout=True)
    for k, name in enumerate(GALAXIES):
        ax = axes.flat[k]
        g = sample[name]
        measured = ax.errorbar(
            g.radius,
            g.v_obs,
            yerr=g.v_err,
            color="black",
            marker="o",
            ms=2.2,
            ls="none",
            elinewidth=0.6,
        )
        (gas,) = ax.plot(g.radius, g.v_gas, color=COLOURS[2], ls=":", lw=1.2)
        (stars,) = ax.plot(
            g.radius, np.sqrt(g.stars_squared(1.0)), color=COLOURS[3], ls="-.", lw=1.0
        )
        ax.axhline(0, color="0.6", lw=0.5)
        ax.set_xlim(0, g.radius.max() * 1.04)
        ax.set_title(f"{pretty(name)}, D = {g.distance:g} Mpc", fontsize=8)
        ax.set_xlabel("radius [kpc]", fontsize=7)
        ax.set_ylabel("circular speed [km/s]", fontsize=7)
        ax.tick_params(labelsize=6.5)
    # One legend for the five panels, in the empty sixth cell.
    key = axes.flat[-1]
    key.axis("off")
    key.legend(
        [measured, gas, stars],
        [
            "Vobs +/- errV, measured [processed]",
            "gas, Vgas (SPARC model)",
            "stars, Vdisk and Vbul at Y = 1\n(SPARC model)",
        ],
        fontsize=6.5,
        loc="center",
        title="every panel",
        title_fontsize=7,
    )
    add_credit(fig, CREDIT)
    label_status(fig, "processed")
    return fig


def _models_panel(ax, res, galaxy: Galaxy, fits: dict, label: bool) -> None:
    _curve(ax, galaxy, label)
    r = galaxy.radius
    iso = fits["iso"]
    ax.plot(
        r,
        galaxy.v_gas,
        color=COLOURS[2],
        ls=":",
        lw=1.2,
        label="gas (SPARC model)" if label else None,
    )
    ax.plot(
        r,
        np.sqrt(galaxy.stars_squared(iso.stellar)),
        color=COLOURS[3],
        ls=":",
        lw=1.4,
        label="stars, core fit's Y" if label else None,
    )
    for halo in HALOS:
        m = fits[halo]
        style = STYLES[halo]
        ax.plot(
            r,
            m.total(galaxy),
            color=style["color"],
            ls=style["ls"],
            lw=1.3,
            label=f"{FIT_LABEL[halo]} ({MARK[halo]})" if label else None,
        )
        res.plot(
            r,
            galaxy.v_obs - m.total(galaxy),
            ls="none",
            ms=2.5,
            marker=style["marker"],
            color=style["color"],
        )
    res.errorbar(
        r, np.zeros_like(r), yerr=galaxy.v_err, color="black", ls="none", elinewidth=0.6
    )
    res.axhline(0, color="0.5", lw=0.6)
    top = max(
        float(galaxy.v_obs.max()),
        max(float(fits[h].total(galaxy).max()) for h in HALOS),
    )
    ax.set_ylim(0, 2.0 * top if label else 1.15 * top)
    ax.set_xlim(0, r.max() * 1.04)
    ax.set_ylabel("circular speed [km/s]", fontsize=7)
    res.set_ylabel("residual [km/s]", fontsize=7)
    res.set_xlabel("radius [kpc]", fontsize=7)
    for a in (ax, res):
        a.tick_params(labelsize=6.5)
    ax.tick_params(labelbottom=False)


def draw_mass_models(sample: dict[str, Galaxy], fits: dict) -> Figure:
    """NGC 3198 and DDO 154 with the three fitted mass models and their
    residuals."""
    fig = plt.figure(figsize=(6.4, 3.8), constrained_layout=True)
    grid = fig.add_gridspec(2, 2, height_ratios=(2.2, 1.0))
    titles = {
        "NGC3198": "NGC 3198: the stars and gas fall, the curve stays flat",
        "DDO154": "DDO 154: the gas dominates the baryons",
    }
    for col, name in enumerate(("NGC3198", "DDO154")):
        ax = fig.add_subplot(grid[0, col])
        res = fig.add_subplot(grid[1, col], sharex=ax)
        _models_panel(ax, res, sample[name], fits[name], col == 0)
        ax.set_title(titles[name], fontsize=8)
        res.set_title(
            "measured minus each fit (markers as in the key), bars +/- errV",
            fontsize=6.5,
        )
        if col == 0:
            ax.legend(fontsize=5.5, loc="upper center", ncols=2, columnspacing=0.8)
    add_credit(fig, CREDIT)
    label_status(fig, "processed")
    return fig


def draw_degeneracy(
    galaxy: Galaxy,
    low: MassModel,
    high: MassModel,
    profiles: dict,
    best: dict,
    y_max: float,
) -> Figure:
    """NGC 2403 with a halo-dominated and a near-maximum disk, both with the
    core, and the reduced chi-square of the best halo at each fixed Y."""
    fig = plt.figure(figsize=(6.4, 3.5), constrained_layout=True)
    grid = fig.add_gridspec(2, 3, height_ratios=(2.0, 1.0))
    r = galaxy.radius
    for col, (model, title) in enumerate(
        ((low, "halo-dominated disk"), (high, "near-maximum disk"))
    ):
        ax = fig.add_subplot(grid[0, col])
        res = fig.add_subplot(grid[1, col], sharex=ax)
        _curve(ax, galaxy, col == 0)
        ax.plot(
            r,
            np.sqrt(galaxy.stars_squared(model.stellar)),
            color=COLOURS[3],
            ls=":",
            lw=1.4,
            label="stars" if col == 0 else None,
        )
        ax.plot(
            r,
            np.sqrt(model.halo_squared(r)),
            color=COLOURS[1],
            ls=(0, (5, 2, 1, 2)),
            lw=1.0,
            label="halo (core)" if col == 0 else None,
        )
        ax.plot(
            r,
            model.total(galaxy),
            color=COLOURS[0],
            ls="--",
            lw=1.3,
            label="fit, total" if col == 0 else None,
        )
        res.plot(
            r,
            galaxy.v_obs - model.total(galaxy),
            ls="none",
            marker="^",
            ms=2.2,
            color=COLOURS[0],
        )
        res.axhline(0, color="0.5", lw=0.6)
        ax.set_ylim(0, 1.8 * float(galaxy.v_obs.max()))
        ax.set_xlim(0, r.max() * 1.04)
        ax.set_title(f"{title}, Y = {model.stellar:.2f}", fontsize=8)
        ax.set_ylabel("circular speed [km/s]", fontsize=7)
        res.set_title(f"residual, chi2/dof {model.reduced_chi2:.1f}", fontsize=7.5)
        res.set_ylabel("residual [km/s]", fontsize=7)
        res.set_xlabel("radius [kpc]", fontsize=7)
        res.set_ylim(-12, 12)
        for a in (ax, res):
            a.tick_params(labelsize=6.5)
        ax.tick_params(labelbottom=False)
        if col == 0:
            ax.legend(fontsize=5.3, loc="upper left", ncols=2, columnspacing=0.8)
    ax = fig.add_subplot(grid[:, 2])
    for (halo, floor), chi2 in profiles.items():
        style = STYLES[halo]
        faint = floor > 0
        which = "errV" if not faint else f"{100 * floor:.0f} % floor"
        ax.plot(
            PROFILE_VALUES,
            chi2,
            color=style["color"],
            ls=style["ls"],
            lw=0.9 if faint else 1.4,
            alpha=0.6 if faint else 1.0,
            label=f"{SHORT[halo]}, {which}",
        )
        m = best[(halo, floor)]
        ax.plot(
            m.stellar,
            m.reduced_chi2,
            ls="none",
            marker=style["marker"],
            ms=4,
            color=style["color"],
            alpha=0.6 if faint else 1.0,
        )
    ax.axvline(y_max, color="0.3", ls=":", lw=1.0, label="maximum disk")
    ax.set_yscale("log")
    ax.set_ylim(0.2, 3000)
    ax.set_xlabel("Y held fixed [M_sun/L_sun]", fontsize=7)
    ax.set_ylabel("reduced chi-square of the best halo [1]", fontsize=7)
    ax.set_title("NGC 2403: chi2/dof against Y", fontsize=8)
    ax.tick_params(labelsize=6.5)
    ax.legend(fontsize=5.3, loc="upper left")
    add_credit(fig, CREDIT)
    label_status(fig, "processed")
    return fig


# The exercises.


def distance_exercise(galaxy: Galaxy) -> None:
    """Exercise 1: NGC 2841 at its adopted distance and a quarter farther."""
    fits = []
    for k, where in ((1.0, "as adopted"), (1.25, "a quarter farther")):
        moved = at_distance(galaxy, k)
        m = fit_mass_model(moved, "iso")
        fits.append(m.stellar)
        print(f"distance {where}: {moved.distance:.1f} Mpc")
        print(f"  core fit: Y = {m.stellar:.2f}")
        print(f"  its reduced chi-square: {m.reduced_chi2:.2f}")
        print(f"  maximum disk: Y = {maximum_disk(moved):.2f}")
    print(f"ratio of the two fitted Y: {fits[1] / fits[0]:.2f}")


def mass_exercise(galaxy: Galaxy, model: MassModel) -> None:
    """Exercise 2: the mass that the last point needs against the mass the
    stars and gas of the core fit supply, both as v^2 r / G."""
    r = float(galaxy.radius[-1])
    needed = galaxy.v_obs[-1] ** 2 * r / G_KPC
    baryons = float(galaxy.baryons_squared(model.stellar)[-1]) * r / G_KPC
    print(f"last point: r = {r:.1f} kpc")
    print(f"its speed: Vobs = {galaxy.v_obs[-1]:.0f} km/s")
    print(f"mass inside it, Vobs^2 r / G: {needed:.2e} M_sun")
    print(f"stars and gas at Y = {model.stellar:.2f}: {baryons:.2e} M_sun")
    print(f"share of the baryons: {baryons / needed:.0%}")


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    sample = load_sample()

    model_check(experiment)
    experiment.number("check-bound", "1e-9")
    experiment.number("check-outer", OUTER, ".0f")

    found = record_table(experiment, sample)
    experiment.number("points", found["points"])
    experiment.number("errv-low", found["errv-low"], ".2f")
    experiment.number("errv-high", found["errv-high"], ".2f")
    experiment.number("radius-low", found["radius-low"], ".2f")
    experiment.number("radius-high", found["radius-high"], ".2f")

    fits = {name: fit_all(sample[name]) for name in GALAXIES}
    fit_table(experiment, sample, fits)
    none = {n: fits[n]["none"] for n in GALAXIES}
    experiment.number("none-low", min(m.reduced_chi2 for m in none.values()), ".0f")
    experiment.number("none-high", max(m.reduced_chi2 for m in none.values()), ".0f")
    short = {
        n: 1 - none[n].total(sample[n])[-1] / sample[n].v_obs[-1] for n in GALAXIES
    }
    experiment.number("short-low", 100 * min(short.values()), ".0f")
    experiment.number("short-high", 100 * max(short.values()), ".0f")
    n3198 = sample["NGC3198"]
    over = none["NGC3198"].total(n3198) - n3198.v_obs
    inner = (n3198.radius >= 4) & (n3198.radius <= 7)
    experiment.number("n3198-y", none["NGC3198"].stellar, ".2f")
    experiment.number("n3198-over-low", over[inner].min(), ".0f")
    experiment.number("n3198-over-high", over[inner].max(), ".0f")
    experiment.number(
        "n3198-over-sigma", at_least((over[inner] / n3198.v_err[inner]).min(), 0)
    )
    experiment.number("n3198-short", -over[-1], ".0f")
    experiment.number("ddo-none-y", none["DDO154"].stellar, ".0f")

    halo_fits = [fits[n][h] for n in GALAXIES for h in ("nfw", "iso")]
    good = [
        fits[n][h].reduced_chi2 for n in ("NGC3198", "NGC2841") for h in ("nfw", "iso")
    ]
    experiment.number("good-low", min(good), ".1f")
    experiment.number("good-high", max(good), ".1f")
    experiment.number("halo-high", max(m.reduced_chi2 for m in halo_fits), ".1f")
    corr = [
        float(fits[n][h].fit.correlation[0, 2])
        for n in GALAXIES
        if n != "DDO154"
        for h in ("nfw", "iso")
    ]
    experiment.number("y-rho-low", min(corr), "+.2f")
    experiment.number("y-rho-high", max(corr), "+.2f")

    rhos = [
        neighbour_correlation(sample[n], fits[n][h]) for n in GALAXIES for h in HALOS
    ]
    bands = [2 / np.sqrt(sample[n].radius.size) for n in GALAXIES]
    experiment.number("rho-low", min(rhos), ".2f")
    experiment.number("rho-high", max(rhos), ".2f")
    experiment.number("band-low", min(bands), ".2f")
    experiment.number("band-high", max(bands), ".2f")

    robust = robustness_table(experiment, sample)
    floor10 = robust["errV + 10 % floor"]
    experiment.number("robust-none", min(row[1] for row in robust.values()), ".1f")
    experiment.number(
        "robust-ratio", at_least(min(row[3] for row in robust.values()), 0)
    )
    systematic = [row for label, row in robust.items() if "floor" not in label]
    experiment.number(
        "robust-none-systematic", at_least(min(row[1] for row in systematic), 0)
    )
    experiment.number(
        "cusp-core-low", at_least(min(row[4] / row[5] for row in robust.values()), 1)
    )
    experiment.number("floor10-cusp", floor10[4], ".2f")
    experiment.number("floor10-core", floor10[5], ".2f")
    y_core = [row[7] for row in systematic]
    y_cusp = [row[6] for row in systematic]
    experiment.number("y-core-low", min(y_core), ".2f")
    experiment.number("y-core-high", max(y_core), ".2f")
    experiment.number("y-cusp-low", min(y_cusp), ".2f")
    experiment.number("y-cusp-high", max(y_cusp), ".2f")

    ddo = sample["DDO154"]
    cusp = fits["DDO154"]["nfw"]
    miss = cusp.total(ddo)[:2] - ddo.v_obs[:2]
    experiment.number("ddo-miss-1", miss[0], ".1f")
    experiment.number("ddo-miss-2", miss[1], ".1f")
    experiment.number("ddo-miss-1-sigma", miss[0] / ddo.v_err[0], ".1f")
    experiment.number("ddo-miss-2-sigma", miss[1] / ddo.v_err[1], ".1f")
    experiment.number("ddo-cusp", cusp.reduced_chi2, ".2f")
    experiment.number("ddo-core", fits["DDO154"]["iso"].reduced_chi2, ".2f")
    gas_share = ddo.gas_squared()[-1] / ddo.v_obs[-1] ** 2
    experiment.number("ddo-gas-share", 100 * gas_share, ".0f")

    bar = sample["NGC2903"]
    bar_fits = fits["NGC2903"]
    below = [bar_fits[h].total(bar)[:2] - bar.v_obs[:2] for h in ("nfw", "iso")]
    experiment.number("bar-low", min(float(b.min()) for b in below), ".0f")
    experiment.number("bar-high", max(float(b.max()) for b in below), ".0f")
    trimmed = outside(bar, BAR_RADIUS)
    trimmed_fits = fit_all(trimmed)
    experiment.number("bar-left-out", int(bar.radius.size - trimmed.radius.size))
    experiment.number("bar-cusp", trimmed_fits["nfw"].reduced_chi2, ".2f")
    experiment.number("bar-core", trimmed_fits["iso"].reduced_chi2, ".2f")
    experiment.number("bar-cusp-all", bar_fits["nfw"].reduced_chi2, ".2f")
    experiment.number("bar-core-all", bar_fits["iso"].reduced_chi2, ".2f")
    experiment.number("bar-max-disk", maximum_disk(bar), ".2f")
    experiment.number("bar-max-disk-trimmed", maximum_disk(trimmed), ".2f")

    n2403 = sample["NGC2403"]
    profiles = {
        (h, f): stellar_profile(n2403, h, PROFILE_VALUES, floor=f)
        / (n2403.radius.size - 3)
        for h in ("nfw", "iso")
        for f in (0.0, FLOORS[0])
    }
    best = {(h, f): fit_mass_model(n2403, h, floor=f) for h, f in profiles}
    core = profiles[("iso", 0.0)]
    minima = [
        k
        for k in range(1, core.size - 1)
        if core[k] < core[k - 1] and core[k] < core[k + 1]
    ]
    low_y = float(PROFILE_VALUES[minima[0]])
    low = fit_mass_model(n2403, "iso", stellar=low_y)
    high = fits["NGC2403"]["iso"]
    y_max = maximum_disk(n2403)
    experiment.number("n2403-y-cusp", fits["NGC2403"]["nfw"].stellar, ".2f")
    experiment.number("n2403-y-core", high.stellar, ".2f")
    experiment.number("n2403-y-low", low_y, ".2f")
    experiment.number("n2403-low-chi2", low.reduced_chi2, ".1f")
    experiment.number("n2403-high-chi2", high.reduced_chi2, ".1f")
    experiment.number("n2403-max-disk", y_max, ".2f")
    experiment.number("n2403-y-cusp-floor", best[("nfw", FLOORS[0])].stellar, ".2f")
    experiment.number("n2403-y-core-floor", best[("iso", FLOORS[0])].stellar, ".2f")
    experiment.number("n2841-y", fits["NGC2841"]["iso"].stellar, ".2f")
    experiment.number("n2841-max-disk", maximum_disk(sample["NGC2841"]), ".2f")

    experiment.figure("fig-curves", partial(draw_curves, sample))
    experiment.figure("fig-mass-models", partial(draw_mass_models, sample, fits))
    experiment.figure(
        "fig-degeneracy",
        partial(draw_degeneracy, n2403, low, high, profiles, best, y_max),
    )

    with experiment.capture("distance-exercise"):
        distance_exercise(sample["NGC2841"])
    with experiment.capture("mass-exercise"):
        mass_exercise(n3198, fits["NGC3198"]["iso"])
    return experiment


if __name__ == "__main__":
    main(run)
