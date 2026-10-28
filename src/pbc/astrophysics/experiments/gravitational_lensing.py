"""The experiment of the lesson "Gravitational lensing".

The deflection of light by a mass and the point lens
(``pbc.astrophysics.lensing``): the exact deflection of the photon orbit
against the weak-field formula and its next term, the images and the
magnification of a finite source by inverse ray shooting against the
average of the point-source formula, and three lenses of different mass
with one light curve. Run it as a program to write the figures and numbers
of the page:

    uv run --locked --no-dev \\
        python -m pbc.astrophysics.experiments.gravitational_lensing out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from scipy import constants

from pbc.astrophysics.lensing import (
    deflection,
    disk_magnification,
    einstein_radius,
    image_positions,
    light_curve,
    magnification,
    newtonian_deflection,
    ray_shoot,
    weak_field_deflection,
)
from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main

# region: setup
GM_SUN = 1.32712440018e20  # m³/s², the Sun's mass parameter
R_SUN = 6.957e8  # m, the Sun's nominal radius
C = constants.c  # m/s
KPC = 1e3 * constants.parsec  # m
ARCSEC = np.pi / (180 * 3600)  # rad
# endregion: setup

# region: deflection
impacts = [10, 30, 100, 300, 1e3, 1e4, 1e5]  # b / m, with m = GM/c²
# endregion: deflection

# region: images
radius = 0.1  # of the source, in Einstein radii
offsets = [0.2, 0.3, 0.5, 0.8, 1.2]
half, cells = 2.2, 2200  # the image plane [-half, half]², cells per side
# endregion: images

# region: degeneracy
source_distance = 8.0  # kpc
lenses = [(0.1, 7.0), (0.5, 4.0), (2.0, 1.0)]  # (mass in M_sun, D_l in kpc)
einstein_days = 30.0
u0 = 0.2
# endregion: degeneracy


def deflection_scan(experiment: Experiment):
    """The exact deflection for each b/m against the weak-field and the
    Newtonian ones, and the remainder (alpha - 4m/b)(b/m)² against
    15 pi / 4; record the table and return the exact deflections."""
    exact = np.array([deflection(b) for b in impacts])
    weak = weak_field_deflection(impacts)
    coefficient = (exact - weak) * np.array(impacts) ** 2
    assert abs(coefficient[-1] / (15 * np.pi / 4) - 1) < 1e-4
    assert np.all(np.diff(coefficient) < 0)

    experiment.table(
        "deflection",
        [
            (b, a, w, n, a / w - 1, k)
            for b, a, w, n, k in zip(
                impacts,
                exact,
                weak,
                newtonian_deflection(impacts),
                coefficient,
                strict=True,
            )
        ],
        [
            ("impact parameter b / m", "", "g"),
            ("exact deflection", "rad", ".6e"),
            ("weak field 4m / b", "rad", ".6e"),
            ("Newtonian 2 arctan(m / b)", "rad", ".6e"),
            ("exact / weak field - 1", "", ".2e"),
            ("(exact - weak field)(b / m)^2", "", ".4f"),
        ],
        "The deflection of a ray by a spherical mass of length m = GM/c^2, from "
        "the photon orbit by quadrature, against the weak-field formula and the "
        "Newtonian turn of a particle at the speed of light, and the remainder "
        "of the weak-field formula scaled by (b / m)^2.",
    )
    return exact, coefficient


def draw_deflection(exact, coefficient) -> Figure:
    """Left: the deflection against b/m, log-log, exact, weak field, and
    Newtonian. Right: the scaled remainder against b/m with its limit."""
    fig, (left, right) = plt.subplots(1, 2, figsize=(6.4, 3.4))
    b = np.geomspace(impacts[0], impacts[-1], 100)
    left.loglog(
        impacts,
        exact,
        "o",
        color=FIGURE_COLOURS[0],
        markerfacecolor="none",
        label="exact (quadrature)",
    )
    left.loglog(
        b,
        weak_field_deflection(b),
        color=FIGURE_COLOURS[1],
        linestyle="--",
        linewidth=1,
        label="weak field 4m / b",
    )
    left.loglog(
        b,
        newtonian_deflection(b),
        color=FIGURE_COLOURS[2],
        linestyle=":",
        label="Newtonian",
    )
    left.set_xlabel("impact parameter b / m")
    left.set_ylabel("deflection (rad)")
    left.legend(fontsize="small")
    right.semilogx(
        impacts,
        coefficient,
        "s",
        color=FIGURE_COLOURS[0],
        markerfacecolor="none",
        label="(exact - 4m/b)(b/m)^2",
    )
    right.axhline(
        15 * np.pi / 4,
        color=FIGURE_COLOURS[1],
        linestyle="--",
        linewidth=1,
        label="15 pi / 4",
    )
    right.set_xlabel("impact parameter b / m")
    right.set_ylabel("scaled remainder")
    right.legend(fontsize="small")
    fig.tight_layout()
    return fig


def images_run(experiment: Experiment):
    """For a source of ``radius`` at each offset, the magnification by ray
    shooting against the disk average and the point-source value; record the
    table and return the rows and the image of the second offset."""
    rows, shown = [], None
    for u in offsets:
        shot, hit = ray_shoot(u, radius, half, cells)
        averaged = disk_magnification(u, radius)
        rows.append((u, shot, averaged, float(magnification(u)), shot / averaged - 1))
        if u == offsets[1]:
            shown = hit
    assert all(abs(row[-1]) < 5e-3 for row in rows)

    experiment.table(
        "images",
        rows,
        [
            ("source offset u", "Einstein radii", ".1f"),
            ("magnification, ray shooting", "", ".4f"),
            ("magnification, disk average", "", ".4f"),
            ("magnification, point source", "", ".4f"),
            ("ray shooting / disk average - 1", "", ".1e"),
        ],
        "The magnification of a uniform source of radius 0.1 Einstein radii by "
        "a point lens: inverse ray shooting on a grid of 2200 by 2200 rays, the "
        "average of the point-source formula over the source's disk, and the "
        "point-source formula at the source's centre.",
    )
    return rows, shown


def draw_images(hit) -> Figure:
    """The cells of the image plane whose rays land on the source at the
    second offset, the Einstein ring, the unlensed source, the predicted
    image centres, and the lens."""
    u = offsets[1]
    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    ax.imshow(
        hit,
        origin="lower",
        extent=(-half, half, -half, half),
        cmap="Greys",
        vmin=0,
        vmax=1.4,
        interpolation="nearest",
    )
    angle = np.linspace(0, 2 * np.pi, 400)
    ax.plot(
        np.cos(angle),
        np.sin(angle),
        color=FIGURE_COLOURS[0],
        linestyle="--",
        linewidth=1,
        label="Einstein ring",
    )
    ax.plot(
        u + radius * np.cos(angle),
        radius * np.sin(angle),
        color=FIGURE_COLOURS[1],
        linestyle=":",
        linewidth=1.5,
        label="source without the lens",
    )
    outer, inner = image_positions(u)
    ax.plot(
        [outer, inner],
        [0, 0],
        "x",
        color=FIGURE_COLOURS[0],
        markersize=9,
        markeredgewidth=2,
        label="images of the source's centre (formula)",
    )
    ax.plot(0, 0, "+", color="#57606a", markersize=10, label="lens")
    ax.set_xlim(-1.8, 1.8)
    ax.set_ylim(-1.4, 1.4)
    ax.set_aspect("equal")
    ax.set_xlabel("x (Einstein radii)")
    ax.set_ylabel("y (Einstein radii)")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncols=2, fontsize="small")
    return fig


def degeneracy(experiment: Experiment):
    """Three lenses of different mass and distance, each with the transverse
    speed that gives the same Einstein time; record the table and return the
    light curves and the largest difference between them."""
    rows = []
    for mass, distance in lenses:
        theta = einstein_radius(mass * GM_SUN, distance * KPC, source_distance * KPC, C)
        ring = theta * distance * KPC  # m, in the lens plane
        speed = ring / (einstein_days * constants.day)
        rows.append(
            (
                mass,
                distance,
                theta / (1e-3 * ARCSEC),
                ring / constants.astronomical_unit,
                speed / 1e3,
                ring / speed / constants.day,
            )
        )
    t = np.linspace(-60, 60, 601)
    curves = [light_curve(t, 0.0, row[-1], u0) for row in rows]
    spread = max(np.max(np.abs(c - curves[0])) for c in curves[1:])
    assert spread < 1e-12

    experiment.table(
        "degeneracy",
        rows,
        [
            ("lens mass", "M_sun", ".1f"),
            ("lens distance", "kpc", ".1f"),
            ("Einstein radius", "mas", ".3f"),
            ("Einstein radius at the lens", "AU", ".2f"),
            ("transverse speed", "km/s", ".0f"),
            ("Einstein time", "days", ".1f"),
        ],
        "Three point lenses in front of a source at 8 kpc, each moving across "
        "the line of sight at the speed that gives an Einstein time of 30 days.",
    )
    return t, curves, spread


def draw_light_curves(t, curves) -> Figure:
    """The magnification against time of the three lenses."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    for k, (curve, (mass, distance), line, marker) in enumerate(
        zip(curves, lenses, ("-", "--", ":"), (None, "o", "s"), strict=True)
    ):
        ax.plot(
            t,
            curve,
            color=FIGURE_COLOURS[k],
            linestyle=line,
            marker=marker,
            markevery=(10 * k, 40),
            markerfacecolor="none",
            label=f"{mass:g} M_sun at {distance:g} kpc",
        )
    ax.set_xlabel("time from the closest approach (days)")
    ax.set_ylabel("magnification")
    ax.legend(fontsize="small")
    return fig


def solar_limb():
    """Exercise 1: the deflection of starlight grazing the Sun, weak field
    and Newtonian, in arcseconds, and the size m/R of the correction."""
    m = GM_SUN / C**2
    return (
        float(weak_field_deflection(R_SUN, m)) / ARCSEC,
        float(newtonian_deflection(R_SUN, m)) / ARCSEC,
        m / R_SUN,
    )


def star_ring():
    """Exercise 2: the Einstein radius of one solar mass halfway to a source
    at 8 kpc, in milliarcseconds, and the separation of its two images for a
    source at u = 0.5."""
    theta = einstein_radius(GM_SUN, 4 * KPC, 8 * KPC, C)
    outer, inner = image_positions(0.5)
    return theta / (1e-3 * ARCSEC), (outer - inner) * theta / (1e-3 * ARCSEC)


def mass_from_ring():
    """Exercise 3: the lens mass, in solar masses, that gives an Einstein
    radius of 0.5 mas for a source at 8 kpc, for several lens distances."""
    theta = 0.5e-3 * ARCSEC
    rows = []
    for distance in (1.0, 2.0, 4.0, 6.0, 7.0):
        dl, ds = distance * KPC, 8.0 * KPC
        rows.append((distance, theta**2 * C**2 * dl * ds / (4 * (ds - dl)) / GM_SUN))
    return rows


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()

    exact, coefficient = deflection_scan(experiment)
    experiment.figure("fig-deflection", partial(draw_deflection, exact, coefficient))
    experiment.number("coefficient-far", coefficient[-1], ".4f")
    experiment.number("coefficient-limit", 15 * np.pi / 4, ".4f")
    near = exact[0] / weak_field_deflection(impacts[0]) - 1
    experiment.number("near-excess", 100 * near, ".0f")

    rows, hit = images_run(experiment)
    experiment.figure("fig-images", partial(draw_images, hit))
    experiment.number("ray-gap", max(abs(row[-1]) for row in rows), ".1e")
    experiment.number("finite-excess", 100 * (rows[0][2] / rows[0][3] - 1), ".2f")

    t, curves, spread = degeneracy(experiment)
    experiment.number(
        "curve-spread", f"below {1e-12:.0e}" if spread < 1e-12 else spread
    )
    experiment.figure("fig-light-curves", partial(draw_light_curves, t, curves))
    experiment.number("peak", float(magnification(u0)), ".3f")

    weak, newtonian, size = solar_limb()
    experiment.number("limb-weak", weak, ".3f")
    experiment.number("limb-newtonian", newtonian, ".3f")
    experiment.number("limb-size", size, ".1e")
    ring, separation = star_ring()
    experiment.number("star-ring", ring, ".2f")
    experiment.number("star-separation", separation, ".2f")
    masses = mass_from_ring()
    experiment.number("ring-mass-ratio", masses[-1][1] / masses[0][1], ".0f")
    experiment.table(
        "mass-from-ring",
        masses,
        [("lens distance", "kpc", ".1f"), ("lens mass", "M_sun", ".3f")],
        "The mass of a point lens with an Einstein radius of 0.5 mas, for a "
        "source at 8 kpc, at several lens distances.",
    )
    return experiment


if __name__ == "__main__":
    main(run)
