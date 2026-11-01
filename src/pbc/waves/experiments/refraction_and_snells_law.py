"""The experiment of the lesson "Refraction and Snell's law".

The path of least time across a flat interface against Snell's law, the
Fresnel amplitudes from the boundary conditions against their closed forms,
and a pulse on a grid across a step of the refractive index against the
exact reflected and transmitted pulses (``pbc.waves.refraction``). Run it
as a program to write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.waves.experiments.refraction_and_snells_law out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.verification.estimates import fitted_order
from pbc.waves.refraction import (
    bisect_root,
    brewster_angle,
    critical_angle,
    fresnel_closed,
    fresnel_solved,
    interface_exact,
    least_time_path,
    node_speeds,
    reflectance,
    snell_angle,
    solve_varying,
    transmittance,
)

# region: media
AIR, WATER, GLASS = 1.0, 1.333, 1.5  # refractive indices
pairs = {
    "air to water": (AIR, WATER),
    "air to glass": (AIR, GLASS),
    "glass to air": (GLASS, AIR),
}
HEIGHT = DEPTH = 1.0  # m, source above and target below the interface
distances = [0.2, 0.5, 1.0, 1.5, 2.5, 5.0]  # m, of the target along the interface
ANGLE_TOLERANCE = 1e-6  # rad, a chosen tolerance on the refracted angle
# endregion: media
# region: pulse
INTERFACE = 0.5  # m, on a line from 0 to 1 m
START, WIDTH = 0.25, 0.03  # m, the centre and the width of the pulse
DURATION = 0.45  # in units of 1 / c0 (m): the pulse has crossed
cells = [200, 400, 800, 1600]
COURANT = 0.5  # in the faster medium
# endregion: pulse


def least_time_run(experiment: Experiment):
    """The path of least time for targets at six distances along the
    interface and three pairs of media, against Snell's law; record the
    table and return the angles by pair and the largest difference."""
    rows, found, worst = [], {}, 0.0
    for name, (n1, n2) in pairs.items():
        angles = []
        for distance in distances:
            _, incidence, refracted = least_time_path(
                height=HEIGHT, depth=DEPTH, distance=distance, n1=n1, n2=n2
            )
            snell = float(snell_angle(incidence, n1, n2))
            worst = max(worst, abs(refracted - snell))
            angles.append((incidence, refracted))
            rows.append(
                (
                    name,
                    distance,
                    np.degrees(incidence),
                    np.degrees(refracted),
                    np.degrees(snell),
                )
            )
        found[name] = np.array(angles)
    assert worst < ANGLE_TOLERANCE, "a path of least time breaks Snell's law"
    experiment.table(
        "least-time",
        rows,
        [
            ("media", "", ""),
            ("target along the interface", "m", ".1f"),
            ("incidence of the least-time path", "deg", ".4f"),
            ("refraction of the least-time path", "deg", ".4f"),
            ("Snell's law", "deg", ".4f"),
        ],
        "The angles of the path of least time from a source a metre above the "
        "interface to a target a metre below it, found by searching the travel "
        "time, and the angle of refraction that Snell's law gives for the same "
        "incidence, to four decimals of a degree.",
    )
    return found, worst


def draw_refraction(found) -> Figure:
    """The refracted angle against the angle of incidence: Snell's law as
    lines, the paths of least time as markers."""
    fig, ax = plt.subplots(figsize=(7.6, 3.8))
    styles = {
        "air to water": (FIGURE_COLOURS[0], "-", "o"),
        "air to glass": (FIGURE_COLOURS[1], "--", "s"),
        "glass to air": (FIGURE_COLOURS[4], "-.", "^"),
    }
    for name, (n1, n2) in pairs.items():
        colour, line, marker = styles[name]
        top = critical_angle(n1, n2) if n1 > n2 else np.pi / 2
        theta = np.linspace(0.0, top, 400)
        ax.plot(
            np.degrees(theta),
            np.degrees(snell_angle(theta, n1, n2)),
            color=colour,
            linestyle=line,
            label=f"{name}: Snell's law",
        )
        ax.plot(
            np.degrees(found[name][:, 0]),
            np.degrees(found[name][:, 1]),
            marker,
            color=colour,
            label=f"{name}: least time",
        )
    critical = np.degrees(critical_angle(GLASS, AIR))
    ax.axvline(critical, color=FIGURE_COLOURS[2], linestyle=":", linewidth=0.8)
    ax.annotate(
        "critical angle, glass to air",
        (critical, 4.0),
        xytext=(4, 0),
        textcoords="offset points",
        fontsize="small",
        color=FIGURE_COLOURS[2],
    )
    ax.plot(
        [0, 90],
        [0, 90],
        color=FIGURE_COLOURS[2],
        linewidth=0.6,
        linestyle=":",
        label="angle unchanged",
    )
    ax.set_xlim(0, 90)
    ax.set_ylim(0, 90)
    ax.set_xlabel("angle of incidence (degrees)")
    ax.set_ylabel("angle of refraction (degrees)")
    ax.legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.02, 1.0))
    fig.tight_layout()
    return fig


def fresnel_run(experiment: Experiment):
    """The Fresnel amplitudes solved from the boundary conditions against
    the closed forms, the balance R + T, the Brewster angle by bisection,
    and the total reflection beyond the critical angle; record the table and
    return the values for the page."""
    theta = np.radians(np.linspace(0.0, 89.5, 180))
    rows, summary = [], {}
    for name, (n1, n2) in (
        ("air to glass", (AIR, GLASS)),
        ("glass to air", (GLASS, AIR)),
    ):
        solved = fresnel_solved(theta, n1, n2)
        closed = fresnel_closed(theta, n1, n2)
        gap = max(float(np.max(np.abs(solved[k] - closed[k]))) for k in solved)
        balance = max(
            float(
                np.max(
                    np.abs(
                        reflectance(solved[r])
                        + transmittance(solved[t], theta, n1, n2)
                        - 1
                    )
                )
            )
            for r, t in (("rs", "ts"), ("rp", "tp"))
        )
        found = bisect_root(
            lambda a, n1=n1, n2=n2: float(np.real(fresnel_solved(a, n1, n2)["rp"][0])),
            0.01,
            critical_angle(n1, n2) - 1e-6 if n1 > n2 else 1.5,
        )
        closed_brewster = brewster_angle(n1, n2)
        rows.append(
            (name, gap, balance, np.degrees(found), np.degrees(closed_brewster))
        )
        summary[name] = (gap, balance, found, closed_brewster)
    assert all(
        gap < 1e-12 and balance < 1e-12 for gap, balance, _, _ in summary.values()
    )
    assert all(abs(f - c) < 1e-9 for _, _, f, c in summary.values())
    beyond = np.radians(np.linspace(45.0, 89.0, 45))
    total = fresnel_solved(beyond, GLASS, AIR)
    total_gap = float(
        np.max(
            np.abs(
                np.concatenate([reflectance(total["rs"]), reflectance(total["rp"])]) - 1
            )
        )
    )
    assert total_gap < 1e-12, "light beyond the critical angle is not all reflected"
    experiment.table(
        "fresnel",
        [(n, below(g), below(b), f, c) for n, g, b, f, c in rows],
        [
            ("media", "", ""),
            ("largest difference, solved and closed amplitudes", "", ""),
            ("largest departure of R + T from one", "", ""),
            ("Brewster angle, zero of r_p", "deg", ".6f"),
            ("arctan(n2 / n1)", "deg", ".6f"),
        ],
        "The reflection and transmission amplitudes found by solving the boundary "
        "conditions at each of the sampled angles of incidence, against the closed "
        "Fresnel forms; the energy balance R + T; and the angle at which r_p "
        "vanishes, found by bisection, against the closed form.",
    )
    return summary, total_gap


def below(value: float, bound: float = 1e-12) -> str:
    """A value, or the bound when it is smaller: a difference at the level
    of round-off is not shown as a number."""
    return f"below {bound:.0e}" if abs(value) < bound else f"{value:.1e}"


def draw_fresnel() -> Figure:
    """R_s and R_p against the angle of incidence, from air into glass and
    from glass into air, with the Brewster and the critical angles."""
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4), sharey=True)
    for ax, (name, (n1, n2)) in zip(
        axes,
        (("air to glass", (AIR, GLASS)), ("glass to air", (GLASS, AIR))),
        strict=True,
    ):
        theta = np.radians(np.linspace(0.0, 89.9, 600))
        solved = fresnel_solved(theta, n1, n2)
        ax.plot(
            np.degrees(theta),
            reflectance(solved["rs"]),
            color=FIGURE_COLOURS[0],
            label="R_s",
        )
        ax.plot(
            np.degrees(theta),
            reflectance(solved["rp"]),
            color=FIGURE_COLOURS[1],
            linestyle="--",
            label="R_p",
        )
        ax.axvline(
            np.degrees(brewster_angle(n1, n2)),
            color=FIGURE_COLOURS[2],
            linestyle=":",
            label="Brewster angle",
        )
        if n1 > n2:
            ax.axvline(
                np.degrees(critical_angle(n1, n2)),
                color=FIGURE_COLOURS[3],
                linestyle="-.",
                label="critical angle",
            )
        ax.set_title(name, fontsize="medium")
        ax.set_xlabel("angle of incidence (degrees)")
        ax.set_xlim(0, 90)
    axes[0].set_ylabel("reflected fraction of the power\n(dimensionless)")
    axes[0].legend(fontsize=7, loc="upper left")
    axes[1].legend(fontsize=7, loc="center right")
    return fig


def gaussian(z):
    return np.exp(-(((z - START) / WIDTH) ** 2))


def gaussian_slope(z):
    return -2.0 * (z - START) / WIDTH**2 * gaussian(z)


def pulse(n_cells: int, n1: float = AIR, n2: float = GLASS):
    """A pulse from air into glass on a grid of ``n_cells`` cells: the grid,
    the computed field at the end, and the exact one."""
    x = np.linspace(0.0, 1.0, n_cells + 1)
    dx = 1.0 / n_cells
    c1, c2 = 1.0 / n1, 1.0 / n2
    dt = COURANT * dx / max(c1, c2)
    steps = round(DURATION / dt)
    speeds = node_speeds(x, interface=INTERFACE, c1=c1, c2=c2)
    u = solve_varying(
        gaussian(x), -c1 * gaussian_slope(x), speeds=speeds, dx=dx, dt=dt, n_steps=steps
    )
    exact = interface_exact(x, steps * dt, gaussian, interface=INTERFACE, c1=c1, c2=c2)
    return x, u, exact


def pulse_run(experiment: Experiment):
    """The pulse from air into glass on four grids: the error against the
    exact field, its order, and the reflected and transmitted parts of the
    finest grid against the Fresnel amplitudes at normal incidence; record
    the table and return the values for the page."""
    rows, errors = [], []
    for n in cells:
        x, u, exact = pulse(n)
        error = float(np.sqrt(np.mean((u - exact) ** 2)))
        errors.append(error)
        rows.append((n, 1.0 / n, error))
    order = fitted_order([1.0 / n for n in cells], errors)
    assert 1.8 < order < 2.2, "the scheme is not of second order across the interface"
    dx = x[1] - x[0]
    left, right = x < INTERFACE, x > INTERFACE
    area = np.sum(gaussian(x)) * dx
    reflected = np.sum(u[left]) * dx / area
    # the transmitted pulse is narrower by c2 / c1 = n1 / n2
    transmitted = np.sum(u[right]) * dx / area * GLASS / AIR
    r, t = (
        fresnel_closed(0.0, AIR, GLASS)["rs"][0].real,
        fresnel_closed(0.0, AIR, GLASS)["ts"][0].real,
    )
    assert abs(reflected - r) < 1e-3 and abs(transmitted - t) < 1e-3
    experiment.table(
        "pulse-run",
        rows,
        [
            ("cells", "", "d"),
            ("cell size", "m", ".5f"),
            ("root-mean-square error of the field", "", ".2e"),
        ],
        "The difference between the field computed on the grid and the exact "
        "incident, reflected, and transmitted pulses after the pulse has crossed "
        "the interface from air into glass, on four grids.",
    )
    return order, reflected, transmitted, r, t


def draw_interface_pulse() -> Figure:
    """The pulse at the start and after it has crossed the interface, on
    the grid and exact."""
    x, u, exact = pulse(400)
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ax.axvspan(INTERFACE, 1.0, color=FIGURE_COLOURS[2], alpha=0.12, linewidth=0)
    ax.plot(x, gaussian(x), color=FIGURE_COLOURS[2], linestyle=":", label="start")
    ax.plot(x, exact, color=FIGURE_COLOURS[0], label="exact, after crossing")
    ax.plot(
        x[::4],
        u[::4],
        "o",
        markersize=3,
        color=FIGURE_COLOURS[1],
        label="grid, after crossing",
    )
    ax.annotate("air", (0.05, 0.85), xycoords="axes fraction")
    ax.annotate("glass", (0.85, 0.85), xycoords="axes fraction")
    ax.set_xlabel("position (m)")
    ax.set_ylabel("electric field (units of the incident peak)")
    ax.legend(fontsize=7, loc="center left")
    return fig


def glass_slab():
    """Exercise 1: the sideways shift of a ray that crosses a glass slab
    one centimetre thick at 45 degrees."""
    thickness = 0.01
    incidence = np.radians(45.0)
    inside = float(snell_angle(incidence, AIR, GLASS))
    shift = thickness * np.sin(incidence - inside) / np.cos(inside)
    leaving = float(snell_angle(inside, GLASS, AIR))
    return np.degrees(inside), shift, np.degrees(leaving)


def snells_window():
    """Exercise 2: the cone through which a fish sees the sky."""
    return np.degrees(critical_angle(WATER, AIR))


def lake_glare():
    """Exercise 3: the angle at which light reflected from water has no p
    part, and the reflected fraction of s there."""
    angle = brewster_angle(AIR, WATER)
    solved = fresnel_solved(angle, AIR, WATER)
    return (
        np.degrees(angle),
        float(reflectance(solved["rs"])[0]),
        float(reflectance(solved["rp"])[0]),
    )


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    found, worst = least_time_run(experiment)
    experiment.figure("fig-refraction", partial(draw_refraction, found))
    experiment.number("angle-gap", below(worst, 1e-7), "")
    experiment.number("angle-tolerance", ANGLE_TOLERANCE, ".0e")
    experiment.number("critical-glass", np.degrees(critical_angle(GLASS, AIR)), ".1f")

    summary, total_gap = fresnel_run(experiment)
    experiment.figure("fig-fresnel", draw_fresnel)
    experiment.number("brewster-glass", np.degrees(summary["air to glass"][3]), ".2f")
    experiment.number("brewster-inside", np.degrees(summary["glass to air"][3]), ".2f")
    normal = fresnel_closed(0.0, AIR, GLASS)
    experiment.number("normal-reflectance", reflectance(normal["rs"])[0] * 100, ".1f")
    experiment.number("total-gap", below(total_gap), "")

    order, reflected, transmitted, r, t = pulse_run(experiment)
    experiment.figure("fig-interface-pulse", draw_interface_pulse)
    experiment.number("pulse-order", order, ".2f")
    experiment.number("reflected", reflected, ".4f")
    experiment.number("transmitted", transmitted, ".4f")
    experiment.number("r-normal", r, ".4f")
    experiment.number("t-normal", t, ".4f")
    experiment.number("flux-balance", r**2 + GLASS / AIR * t**2, ".4f")

    inside, shift, leaving = glass_slab()
    experiment.number("slab-inside", inside, ".1f")
    experiment.number("slab-shift-mm", shift * 1000, ".2f")
    experiment.number("slab-leaving", leaving, ".1f")
    experiment.number("window", snells_window(), ".1f")
    experiment.number("window-full", 2 * snells_window(), ".0f")
    angle, rs2, rp2 = lake_glare()
    experiment.number("lake-brewster", angle, ".1f")
    experiment.number("lake-rs", rs2 * 100, ".1f")
    experiment.number("lake-rp", below(rp2), "")
    return experiment


if __name__ == "__main__":
    main(run)
