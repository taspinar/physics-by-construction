"""The experiment of the lesson "Exoplanet transit simulation".

A planet crossing its star (``pbc.astrophysics.transit``): the orbit
integrated in three dimensions with its contacts located as events, the
light curve by counting grid cells over the planet's disk, the depth
against the ratio of the areas and the flux against the closed-form
overlap, the durations against the analytic geometry for several impact
parameters up to a grazing transit, and a limb-darkened star against the
closed-form depth of a central transit. Run it as a program to write the
figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.astrophysics.experiments.exoplanet_transit out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from scipy import constants

from pbc.astrophysics.transit import (
    central_depth,
    durations,
    grid_flux,
    quadratic_limb,
    total_flux,
    transit_orbit,
    uniform_flux,
)
from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main

# region: setup
GM_SUN = 1.32712440018e20  # m³/s², the Sun's mass parameter
R_SUN = 6.957e8  # m, the Sun's nominal radius
HOUR = 3600.0  # s
period = 3 * constants.day  # s
p = 0.1  # the planet's radius over the star's
cells = 400  # grid cells across the planet's diameter
# endregion: setup

# region: impacts
impacts = [0.0, 0.3, 0.6, 0.85, 0.95]  # b, in stellar radii
# endregion: impacts

# region: limb
u1, u2 = 0.4, 0.26  # quadratic limb darkening, given coefficients
# endregion: limb


def semi_major_axis(orbit_period: float = period, gm: float = GM_SUN) -> float:
    """Kepler's third law, a³ = GM P² / (4 pi²), in metres."""
    return (gm * orbit_period**2 / (4 * np.pi**2)) ** (1 / 3)


def simulate(b: float, samples: int = 401):
    """One transit at the impact parameter ``b``: the orbit integrated over
    a little more than the analytic total duration, the separations, the
    contacts, and the analytic durations, in hours from the start."""
    a = semi_major_axis()
    inclination = np.arccos(b * R_SUN / a)
    t14, t23 = durations(period, a / R_SUN, inclination, p)
    before = 1.2 * np.pi * t14 / period  # radians ahead of mid-transit
    t = np.linspace(0, 2 * before * period / (2 * np.pi), samples)
    t, d, contacts = transit_orbit(GM_SUN, a, inclination, p, t, before, R_SUN)
    middle = t[-1] / 2
    return {
        "hours": (t - middle) / HOUR,
        "d": d,
        "outer": (contacts["outer"] - middle) / HOUR,
        "inner": (contacts["inner"] - middle) / HOUR,
        "t14": t14 / HOUR,
        "t23": t23 / HOUR,
    }


def one_transit(experiment: Experiment):
    """The transit at the second impact parameter: the grid flux against the
    closed-form overlap, the depth against p², and the contacts against the
    analytic durations; record the table and return the run and the fluxes."""
    run_ = simulate(impacts[1])
    grid = grid_flux(run_["d"], p, cells=cells)
    closed = uniform_flux(run_["d"], p)
    gap = np.max(np.abs(grid - closed)) / p**2
    depth = 1 - grid.min()
    assert gap < 1e-3
    assert abs(depth / p**2 - 1) < 1e-3
    t14 = run_["outer"][1] - run_["outer"][0]
    t23 = run_["inner"][1] - run_["inner"][0]
    timing = max(abs(t14 / run_["t14"] - 1), abs(t23 / run_["t23"] - 1))
    assert timing < 1e-9
    experiment.table(
        "one-transit",
        [
            ("transit depth", depth, p**2, f"{depth / p**2 - 1:.1e}"),
            ("total duration T14 (hours)", t14, run_["t14"], f"below {1e-9:.0e}"),
            ("full duration T23 (hours)", t23, run_["t23"], f"below {1e-9:.0e}"),
        ],
        [
            ("quantity", "", ""),
            ("simulated", "", ".6f"),
            ("analytic", "", ".6f"),
            ("simulated / analytic - 1", "", ""),
        ],
        "A planet of a tenth of the star's radius on a three-day circular "
        "orbit about a star of the Sun's mass and radius, impact parameter "
        "0.3: the depth of the grid light curve against p^2, and the contacts "
        "of the integrated orbit against the analytic durations.",
    )
    return run_, grid, closed, gap


def draw_transit(run_, grid, closed) -> Figure:
    """The simulated light curve, the closed-form curve, and the four
    contacts of the integrated orbit."""
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    step = 8
    ax.plot(
        run_["hours"][::step],
        grid[::step],
        "o",
        color=FIGURE_COLOURS[0],
        markerfacecolor="none",
        label="simulated (grid over the planet)",
    )
    ax.plot(
        run_["hours"],
        closed,
        color=FIGURE_COLOURS[1],
        linestyle="--",
        linewidth=1.2,
        label="closed-form overlap",
    )
    for k, time in enumerate(np.concatenate([run_["outer"], run_["inner"]])):
        ax.axvline(
            time,
            color=FIGURE_COLOURS[2],
            linestyle=":",
            linewidth=1,
            label="contacts of the integrated orbit" if k == 0 else None,
        )
    ax.set_xlabel("time from mid-transit (hours)")
    ax.set_ylabel("flux / flux out of transit")
    ax.legend(fontsize="small", loc="upper center")
    fig.tight_layout()
    return fig


def impact_scan(experiment: Experiment):
    """For each impact parameter, the contacts against the analytic
    durations and the depth against p²; record the table and return the
    light curves and the largest gap of the durations."""
    rows, curves, gap = [], [], 0.0
    for b in impacts:
        run_ = simulate(b)
        flux = grid_flux(run_["d"], p, cells=cells)
        t14 = run_["outer"][1] - run_["outer"][0]
        gap = max(gap, abs(t14 / run_["t14"] - 1))
        if len(run_["inner"]) == 2:
            t23 = run_["inner"][1] - run_["inner"][0]
            gap = max(gap, abs(t23 / run_["t23"] - 1))
        else:
            assert np.isnan(run_["t23"])
            t23 = np.nan
        rows.append((b, t14, run_["t14"], t23, run_["t23"], (1 - flux.min()) / p**2))
        curves.append((b, run_["hours"], flux))
    assert gap < 1e-9

    def cell(value):
        return "none" if np.isnan(value) else f"{value:.4f}"

    experiment.table(
        "impacts",
        [
            (b, f"{s14:.4f}", f"{a14:.4f}", cell(s23), cell(a23), depth)
            for b, s14, a14, s23, a23, depth in rows
        ],
        [
            ("impact parameter b", "stellar radii", ".2f"),
            ("T14, simulated", "hours", ""),
            ("T14, analytic", "hours", ""),
            ("T23, simulated", "hours", ""),
            ("T23, analytic", "hours", ""),
            ("depth / p^2", "", ".4f"),
        ],
        "The total and full durations from the contacts of the integrated "
        "orbit against the analytic geometry, and the depth of the grid light "
        "curve over p^2, for a planet of radius 0.1 on the three-day orbit; "
        "above b = 1 - p the transit is grazing and has no full phase.",
    )
    return rows, curves, gap


def draw_impacts(curves) -> Figure:
    """The light curves of the impact parameters."""
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    styles = ("-", "--", "-.", ":", (0, (1, 3)))
    for k, ((b, hours, flux), line) in enumerate(zip(curves, styles, strict=True)):
        ax.plot(
            hours,
            flux,
            color=FIGURE_COLOURS[k % len(FIGURE_COLOURS)],
            linestyle=line,
            linewidth=1.5,
            label=f"b = {b:.2f}",
        )
    ax.set_xlabel("time from mid-transit (hours)")
    ax.set_ylabel("flux / flux out of transit")
    ax.legend(fontsize="small", loc="lower center", bbox_to_anchor=(0.5, 1.0), ncols=5)
    fig.tight_layout()
    return fig


def limb_darkening(experiment: Experiment):
    """A central transit on a uniform and on a limb-darkened star: the grid
    depth against the closed form for a centred planet, at three grid sizes;
    record the table and return the two light curves and the gap."""
    darker = quadratic_limb(u1, u2)
    full = total_flux(u1, u2)
    rows = []
    for n in (100, 200, cells):
        depth = 1 - grid_flux([0.0], p, darker, n, full)[0]
        rows.append(
            (n, depth, central_depth(p, u1, u2), depth / central_depth(p, u1, u2) - 1)
        )
    gap = abs(rows[-1][-1])
    assert gap < 1e-3
    run_ = simulate(0.0)
    uniform_curve = grid_flux(run_["d"], p, cells=cells)
    darker_curve = grid_flux(run_["d"], p, darker, cells, full)
    experiment.table(
        "limb",
        rows,
        [
            ("grid cells across the planet", "", "d"),
            ("depth, grid", "", ".6f"),
            ("depth, closed form", "", ".6f"),
            ("grid / closed form - 1", "", ".1e"),
        ],
        "The depth of a central transit of a planet of radius 0.1 on a star "
        "with the quadratic limb-darkening law (u1 = 0.4, u2 = 0.26): the grid "
        "at three sizes against the closed form for a centred planet.",
    )
    return run_["hours"], uniform_curve, darker_curve, rows


def draw_limb(hours, uniform_curve, darker_curve) -> Figure:
    """A central transit on a uniform and on a limb-darkened star."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.plot(
        hours,
        uniform_curve,
        color=FIGURE_COLOURS[0],
        linestyle="-",
        linewidth=1.5,
        label="uniform star",
    )
    ax.plot(
        hours,
        darker_curve,
        color=FIGURE_COLOURS[1],
        linestyle="--",
        linewidth=1.5,
        label="limb-darkened star",
    )
    ax.axhline(
        1 - p**2, color=FIGURE_COLOURS[2], linestyle=":", linewidth=1, label="1 - p^2"
    )
    ax.set_xlabel("time from mid-transit (hours)")
    ax.set_ylabel("flux / flux out of transit")
    ax.legend(fontsize="small", loc="upper center")
    fig.tight_layout()
    return fig


def earth_transit():
    """Exercise 1: the depth in parts per million and the central duration in
    hours of the Earth crossing the Sun, and the chance that a randomly
    oriented orbit shows a transit, R / a, in per cent."""
    r_earth = 6.371e6  # m
    a = semi_major_axis(constants.year)
    t14, _ = durations(constants.year, a / R_SUN, np.pi / 2, r_earth / R_SUN)
    return 1e6 * (r_earth / R_SUN) ** 2, t14 / HOUR, 100 * R_SUN / a


def duration_with_period():
    """Exercise 2: the central total duration in hours for several periods
    about the Sun, and its ratio to the period to the power one third."""
    rows = []
    for days in (1.0, 3.0, 10.0, 30.0, 365.25):
        orbit_period = days * constants.day
        a = semi_major_axis(orbit_period)
        t14, _ = durations(orbit_period, a / R_SUN, np.pi / 2, p)
        rows.append((days, a / R_SUN, t14 / HOUR, t14 / HOUR / days ** (1 / 3)))
    return rows


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()

    experiment.number("a-over-r", semi_major_axis() / R_SUN, ".2f")
    run_, grid, closed, gap = one_transit(experiment)
    experiment.figure("fig-transit", partial(draw_transit, run_, grid, closed))
    experiment.number("flux-gap", gap, ".0e")
    experiment.number("t14", run_["t14"], ".2f")

    rows, curves, duration_gap = impact_scan(experiment)
    experiment.figure("fig-impacts", partial(draw_impacts, curves))
    experiment.number(
        "duration-gap", f"below {1e-9:.0e}" if duration_gap < 1e-9 else duration_gap
    )
    experiment.number("grazing-depth", rows[-1][-1], ".2f")

    hours, uniform_curve, darker_curve, limb_rows = limb_darkening(experiment)
    experiment.figure(
        "fig-limb", partial(draw_limb, hours, uniform_curve, darker_curve)
    )
    experiment.number("limb-gap", abs(limb_rows[-1][-1]), ".0e")
    experiment.number("limb-excess", 100 * (limb_rows[-1][2] / p**2 - 1), ".0f")

    depth, hours_earth, chance = earth_transit()
    experiment.number("earth-depth", depth, ".0f")
    experiment.number("earth-hours", hours_earth, ".1f")
    experiment.number("earth-chance", chance, ".2f")
    period_rows = duration_with_period()
    experiment.table(
        "durations-with-period",
        period_rows,
        [
            ("period", "days", ".2f"),
            ("a / R", "", ".1f"),
            ("central T14", "hours", ".2f"),
            ("T14 / P^(1/3)", "hours / days^(1/3)", ".3f"),
        ],
        "The central total duration of a planet of radius 0.1 about a star of "
        "the Sun's mass and radius, for several orbital periods.",
    )
    return experiment


if __name__ == "__main__":
    main(run)
