"""The experiment of the lesson "Relativistic orbits".

Orbits of a test body about a spherical mass in general relativity
(``pbc.astrophysics.relativistic_orbits``): the precessing orbit of a
strong field beside Kepler's closed ellipse, the turn of the periapsis per
orbit against the first-order formula 6 pi m / p as the field weakens, from
the exact orbit integrated in angle, from its elliptic integral, and from
the post-Newtonian equations of motion integrated in time, and the
effective potential with the innermost stable circular orbit. Run it as a
program to write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.astrophysics.experiments.relativistic_orbits out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from scipy.constants import c as C
from scipy.optimize import brentq

from pbc.astrophysics import central_force
from pbc.astrophysics.relativistic_orbits import (
    circular_orbit_radii,
    effective_potential,
    exact_precession,
    first_order_precession,
    geodesic,
    post_newtonian_orbit,
    second_order_coefficient,
    turn_per_orbit,
)
from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.verification.estimates import fitted_order

# region: setup
# Units: G = c = 1 and the semi-latus rectum p = 1, so m is m/p.
P = 1.0
E = 0.5  # the eccentricity
ORBITS = 10.5  # the duration, in turns of the angle or Kepler periods
# endregion: setup

# region: strong
strong_m = 0.04  # periapsis at p / (1 + e), about 17 m
# endregion: strong

# region: scan
fields = [0.03, 0.01, 3e-3, 1e-3, 3e-4, 1e-4]  # m/p, strongest first
# endregion: scan

# region: circular
momenta = [3.4, 3.5, 4.0, 5.0, 8.0]  # h/m
# endregion: circular


def bound(value, limit):
    """A value at the level of round-off is shown as below ``limit``."""
    return f"{value:.1e}" if value > limit else f"below {limit:.0e}"


def strong_field(experiment: Experiment):
    """The orbit of ``strong_m`` integrated in angle: its turn per orbit
    against the elliptic integral and the first-order formula; record the
    numbers and return the orbit."""
    path = geodesic(strong_m, P, E, 6.5)
    turn = turn_per_orbit(path.periapsis_phi)
    exact = exact_precession(strong_m, P, E)
    assert abs(turn - exact) < 1e-9
    experiment.number("strong-turn", turn, ".4f")
    experiment.number("strong-exact", exact, ".4f")
    experiment.number("strong-first", float(first_order_precession(strong_m, P)), ".4f")
    experiment.number("strong-periapsis", P / (1 + E) / strong_m, ".1f")
    return path


def draw_orbit(path) -> Figure:
    """The precessing orbit of a strong field beside Kepler's ellipse with
    the same turning points, with the relativistic periapses marked."""
    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    r = 1 / path.u
    ax.plot(
        r * np.cos(path.phi),
        r * np.sin(path.phi),
        color=FIGURE_COLOURS[1],
        linewidth=0.8,
        label=f"Schwarzschild orbit, m/p = {strong_m}",
    )
    nu = np.linspace(0.0, 2 * np.pi, 400)
    kepler = P / (1 + E * np.cos(nu))
    ax.plot(
        kepler * np.cos(nu),
        kepler * np.sin(nu),
        color=FIGURE_COLOURS[0],
        linestyle="--",
        linewidth=1.5,
        label="Kepler ellipse",
    )
    rp = P / (1 + E)
    angles = np.concatenate([[0.0], path.periapsis_phi])
    ax.plot(
        rp * np.cos(angles),
        rp * np.sin(angles),
        "o",
        color=FIGURE_COLOURS[1],
        markerfacecolor="none",
        label="periapses",
    )
    ax.plot(0.0, 0.0, "+", color="#57606a", markersize=10, label="central mass")
    ax.set_aspect("equal")
    ax.set_xlabel("x (units of p)")
    ax.set_ylabel("y (units of p)")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncols=2, fontsize="small")
    return fig


def precession_scan(experiment: Experiment):
    """For each m/p of ``fields``: the turn per orbit of the orbit integrated
    in angle, of the elliptic integral, of the post-Newtonian equations
    integrated in time, and of the first-order formula; record the table and
    return the turns and the fitted orders of the gaps."""
    integrated, exact, pn = [], [], []
    for m in fields:
        integrated.append(turn_per_orbit(geodesic(m, P, E, ORBITS).periapsis_phi))
        exact.append(exact_precession(m, P, E))
        pn.append(turn_per_orbit(post_newtonian_orbit(m, P, E, ORBITS)))
    integrated, exact, pn = map(np.array, (integrated, exact, pn))
    first = first_order_precession(fields, P)
    x = np.array(fields)
    orders = (
        fitted_order(fields, np.abs(exact - first)),
        fitted_order(fields, np.abs(pn - first)),
    )
    assert np.max(np.abs(integrated - exact)) < 1e-10
    assert all(abs(order - 2) < 0.1 for order in orders)
    experiment.table(
        "precession",
        [
            (
                m,
                first[i],
                exact[i],
                bound(abs(integrated[i] - exact[i]), 1e-10),
                (exact[i] - first[i]) / x[i] ** 2,
                pn[i],
                (pn[i] - first[i]) / x[i] ** 2,
            )
            for i, m in enumerate(fields)
        ],
        [
            ("m/p", "", "g"),
            ("first order 6 pi m/p", "rad", ".4e"),
            ("exact, elliptic integral", "rad", ".4e"),
            ("integrated geodesic - exact", "rad", ""),
            ("(exact - first order) / (m/p)^2", "rad", ".2f"),
            ("post-Newtonian, integrated", "rad", ".4e"),
            ("(post-Newtonian - first order) / (m/p)^2", "rad", ".1f"),
        ],
        "The turn of the periapsis per orbit for e = 0.5 as the field weakens: "
        "the first-order formula, the exact value from the elliptic integral, "
        "the gap of the orbit integrated in angle from it, the post-Newtonian "
        "equations integrated in time over ten and a half periods, and each "
        "gap from the first order divided by (m/p)^2.",
    )
    return exact, pn, orders


def draw_precession(exact, pn) -> Figure:
    """Two panels against m/p, log-log: the turn per orbit (first order,
    exact, post-Newtonian), and the size of each gap from the first order
    with the second-order term of the exact turn."""
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(6.4, 6.0), sharex=True)
    x = np.geomspace(fields[-1], fields[0], 100)
    top.loglog(
        x,
        first_order_precession(x, P),
        color=FIGURE_COLOURS[0],
        linestyle="--",
        linewidth=1,
        label="first order, 6 pi m/p",
    )
    top.loglog(
        fields,
        exact,
        "o",
        color=FIGURE_COLOURS[1],
        markerfacecolor="none",
        label="exact (Schwarzschild)",
    )
    top.loglog(
        fields,
        pn,
        "^",
        color=FIGURE_COLOURS[2],
        markerfacecolor="none",
        label="post-Newtonian, integrated",
    )
    top.set_ylabel("turn per orbit (rad)")
    top.legend(fontsize="small")
    first = first_order_precession(fields, P)
    bottom.loglog(
        fields,
        np.abs(exact - first),
        "o",
        color=FIGURE_COLOURS[1],
        markerfacecolor="none",
        label="exact - first order",
    )
    bottom.loglog(
        fields,
        np.abs(pn - first),
        "^",
        color=FIGURE_COLOURS[2],
        markerfacecolor="none",
        label="|post-Newtonian - first order|",
    )
    bottom.loglog(
        x,
        second_order_coefficient(E) * x**2,
        color="#57606a",
        linestyle=":",
        label="(3 pi / 2)(18 + e^2)(m/p)^2",
    )
    bottom.set_xlabel("field strength m/p")
    bottom.set_ylabel("gap from first order (rad)")
    bottom.legend(fontsize="small")
    return fig


def gauss_check():
    """The first-order turn from Gauss's equation of the modified-gravity
    lesson, with the extra attraction -3 m h²/r⁴ that the relativistic Binet
    equation adds to Newton's, on the Kepler ellipse (h² = m p), against
    6 pi m / p; returns the relative gap for each m/p."""
    gaps = []
    for m in fields:
        a = P / (1 - E**2)
        turn = central_force.first_order_precession(
            lambda r, m=m: -3 * m * (m * P) / r**4, m, a, E
        )
        gaps.append(abs(turn / float(first_order_precession(m, P)) - 1))
    return max(gaps)


def stable_minimum(h, m=1.0):
    """The radius of the minimum of the effective potential found
    numerically: the root of its slope, by central differences, where the
    slope turns from negative to positive on a grid from 2m out; None when
    it never does (no stable circular orbit)."""

    def slope(r):
        return effective_potential(r * (1 + 1e-6), h, m) - effective_potential(
            r * (1 - 1e-6), h, m
        )

    r = np.geomspace(2.01 * m, 1e4 * m, 2001)
    up = np.nonzero((slope(r[:-1]) < 0) & (slope(r[1:]) >= 0))[0]
    if len(up) == 0:
        return None
    return brentq(slope, r[up[0]], r[up[0] + 1], xtol=1e-12)


def circular(experiment: Experiment):
    """For each h/m of ``momenta``: the stable circular orbit from the
    minimum of the effective potential found numerically, against the
    closed form; record the table."""
    rows = []
    for h in momenta:
        found = stable_minimum(h)
        radii = circular_orbit_radii(h, 1.0)
        assert (found is None) == (radii is None)
        if radii is None:
            rows.append((h, h**2, None, None, "none"))
        else:
            assert abs(found / radii[1] - 1) < 1e-5
            rows.append((h, h**2, found, radii[1], f"{radii[0]:.4f}"))
    experiment.table(
        "circular",
        rows,
        [
            ("h/m", "", "g"),
            ("(h/m)^2", "", ".2f"),
            ("stable radius, numerical minimum", "m", ".4f"),
            ("stable radius, closed form", "m", ".4f"),
            ("unstable radius", "m", ""),
        ],
        "The circular orbits of a test body for several angular momenta per "
        "unit rest mass h: the minimum of the effective potential found "
        "numerically and from the closed form, and the maximum, the unstable "
        "orbit, in units of m = GM/c^2, to four decimals.",
    )


def draw_potential() -> Figure:
    """The effective potential against r/m for several h/m, with the minima,
    the stable circular orbits, marked, and the innermost stable circular
    orbit."""
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    r = np.linspace(2.2, 40.0, 600)
    for h, colour, style in zip(
        (3.2, 2 * np.sqrt(3), 4.0, 4.4),
        FIGURE_COLOURS,
        ("-.", ":", "--", "-"),
        strict=False,
    ):
        ax.plot(
            r,
            effective_potential(r, h, 1.0),
            color=colour,
            linestyle=style,
            label=f"h/m = {h:.3g}",
        )
        radii = circular_orbit_radii(h, 1.0)
        if radii is not None:
            ax.plot(
                radii[1],
                effective_potential(radii[1], h, 1.0),
                "o",
                color=colour,
                markerfacecolor="none",
            )
    ax.axvline(
        6.0,
        color="#57606a",
        linestyle=(0, (1, 4)),
        linewidth=1,
        label="innermost stable orbit, r = 6m",
    )
    ax.set_ylim(0.85, 1.05)
    ax.set_xlabel("r (units of m = GM/c^2)")
    ax.set_ylabel("effective potential (squared energy per rest energy)")
    ax.legend(fontsize="small", loc="lower right")
    return fig


def mercury():
    """Exercise 1: the first-order turn of Mercury's periapsis per century,
    in arcseconds, from the Sun's mass parameter 1.32712440018e20 m³/s²,
    Mercury's semi-major axis 5.7909e10 m, eccentricity 0.2056, and period
    87.969 days (given values)."""
    gm, a, e, period = 1.32712440018e20, 5.7909e10, 0.2056, 87.969
    m = gm / C**2
    per_orbit = float(first_order_precession(m, a * (1 - e**2)))
    orbits = 36525 / period
    return per_orbit, np.degrees(per_orbit * orbits) * 3600, m / (a * (1 - e**2))


def near_circular(radii=(7.0, 10.0, 20.0, 100.0)):
    """Exercise 2: the exact turn per orbit of a nearly circular orbit
    (e = 0.001) at r = p in units of m, against 2 pi (1/sqrt(1 - 6m/r) - 1)
    and the first order 6 pi m/r."""
    return [
        (
            r,
            exact_precession(1 / r, 1.0, 1e-3),
            2 * np.pi * (1 / np.sqrt(1 - 6 / r) - 1),
            float(first_order_precession(1 / r, 1.0)),
        )
        for r in radii
    ]


def ten_percent():
    """Exercise 3: the m/p at which the first-order formula falls 10 per cent
    short of the exact turn, for e = 0.5."""
    return brentq(
        lambda m: float(first_order_precession(m, P)) / exact_precession(m, P, E) - 0.9,
        1e-4,
        0.1,
    )


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()

    path = strong_field(experiment)
    experiment.figure("fig-orbit", partial(draw_orbit, path))

    exact, pn, orders = precession_scan(experiment)
    experiment.figure("fig-precession", partial(draw_precession, exact, pn))
    experiment.number("exact-order", orders[0], ".2f")
    experiment.number("pn-order", orders[1], ".2f")
    experiment.number("second-order", second_order_coefficient(E), ".2f")
    gauss = gauss_check()
    assert gauss < 1e-10
    experiment.number("gauss-gap", bound(gauss, 1e-10))

    circular(experiment)
    experiment.figure("fig-potential", draw_potential)

    per_orbit, per_century, field = mercury()
    experiment.number("mercury-orbit", per_orbit, ".3e")
    experiment.number("mercury-century", per_century, ".2f")
    experiment.number("mercury-field", field, ".2e")
    experiment.table(
        "near-circular",
        near_circular(),
        [
            ("r", "m", "g"),
            ("exact turn, e = 0.001", "rad", ".5f"),
            ("2 pi (1/sqrt(1 - 6m/r) - 1)", "rad", ".5f"),
            ("first order 6 pi m/r", "rad", ".5f"),
        ],
        "The turn per orbit of nearly circular orbits at several radii in "
        "units of m: the exact value, the circular-orbit formula, and the first "
        "order, to five decimals.",
    )
    experiment.number("ten-percent", ten_percent(), ".4f")
    experiment.number("ten-percent-r", P / (1 + E) / ten_percent(), ".0f")
    return experiment


if __name__ == "__main__":
    main(run)
