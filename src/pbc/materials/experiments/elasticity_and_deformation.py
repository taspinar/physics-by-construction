"""The experiment of the lesson "Elasticity and deformation".

A bar loaded by its own weight and an end force, by linear elements,
against the closed form of the loaded bar; a plate in plane stress with
linear vector elements (``pbc.materials.elasticity`` on a ``pbc.fem``
mesh) under uniform tension, first free to contract sideways, against the
closed form, then clamped to a wall, where the support disturbs the
uniform state near it and nowhere else. Run it as a program to write the
figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.materials.experiments.elasticity_and_deformation out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.tri import Triangulation

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.fem.assembly import solve
from pbc.fem.mesh import rectangle
from pbc.materials.elasticity import (
    bar_displacement,
    bar_load,
    bar_stiffness,
    bar_stress,
    clamped_supports,
    roller_supports,
    solve_bar,
    solve_plate,
    traction_load,
    uniform_tension,
)

# region: bar
# A steel rod hanging in a shaft, carrying a load at its lower end.
E = 200e9  # Young's modulus of steel (Pa)
AREA = 1e-4  # cross-section (m^2), 1 cm^2
LENGTH = 100.0  # (m)
WEIGHT = 7850 * 9.81 * AREA  # its own weight per metre, rho g A (N/m)
FORCE = 1000.0  # the load at the end (N)
elements = [1, 2, 4, 8, 16]
# endregion: bar

# region: plate
NU = 0.3  # Poisson's ratio of steel
WIDTH, HEIGHT = 0.2, 0.05  # the plate (m), four times as wide as high
THICKNESS = 0.01  # (m)
SIGMA = 100e6  # the tension pulling on the right edge (Pa)
meshes = [8, 16, 32]  # cells along the width; a quarter as many along the height
clamped_meshes = [32, 64, 128]
distances = [0.125, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0]  # from the clamp, in heights
# endregion: plate


def bound(value, limit):
    """A value at the level of round-off is shown as below ``limit``."""
    return f"{value:.1e}" if value > limit else f"below {limit:.0e}"


def bars(experiment: Experiment):
    """The bar on growing numbers of elements against the closed form:
    the nodal displacements, the element stress at the midpoints and at
    the ends, and the reaction; record the table and return the largest
    errors."""
    scale = bar_stress(0.0, LENGTH, AREA, WEIGHT, FORCE)  # the largest stress
    rows, nodal, middle, reactions = [], [], [], []
    for n in elements:
        bar = solve_bar(LENGTH, n, E, AREA, WEIGHT, FORCE)
        exact = bar_displacement(bar.x, LENGTH, E, AREA, WEIGHT, FORCE)
        mid = (bar.x[:-1] + bar.x[1:]) / 2
        ends = np.column_stack([bar.x[:-1], bar.x[1:]])
        node_error = np.max(np.abs(bar.u - exact)) / exact[-1]
        mid_error = np.max(
            np.abs(bar.stress - bar_stress(mid, LENGTH, AREA, WEIGHT, FORCE))
        )
        end_error = np.max(
            np.abs(bar.stress[:, None] - bar_stress(ends, LENGTH, AREA, WEIGHT, FORCE))
        )
        balance = abs(bar.reaction + FORCE + WEIGHT * LENGTH) / (
            FORCE + WEIGHT * LENGTH
        )
        nodal.append(node_error)
        middle.append(mid_error / scale)
        reactions.append(balance)
        h = LENGTH / n
        rows.append(
            (
                n,
                bound(node_error, 1e-12),
                bound(mid_error / scale, 1e-12),
                end_error / 1e6,
                WEIGHT * h / (2 * AREA) / 1e6,
            )
        )
    experiment.table(
        "bar",
        rows,
        [
            ("elements", "", "d"),
            ("largest nodal error / u(L)", "", ""),
            ("stress error at the midpoints / sigma(0)", "", ""),
            ("stress error at the element ends", "MPa", ".4f"),
            ("q h / (2A)", "MPa", ".4f"),
        ],
        "A steel rod of 100 m and 1 cm^2 hanging from its top, loaded by its "
        "own weight and by 1 kN at its lower end, on equal linear elements: "
        "the nodal displacements and the stress of each element against the "
        "closed form of the loaded bar.",
    )
    return max(nodal), max(middle), max(reactions)


def draw_bar() -> Figure:
    """The displacement and the stress of the rod on four elements against
    the closed form."""
    bar = solve_bar(LENGTH, 4, E, AREA, WEIGHT, FORCE)
    x = np.linspace(0, LENGTH, 200)
    fig, (left, right) = plt.subplots(1, 2, figsize=(7.2, 3.2))
    left.plot(
        x,
        1e3 * bar_displacement(x, LENGTH, E, AREA, WEIGHT, FORCE),
        color=FIGURE_COLOURS[0],
        linestyle="-",
        label="closed form",
    )
    left.plot(
        bar.x,
        1e3 * bar.u,
        "o--",
        color=FIGURE_COLOURS[1],
        markerfacecolor="none",
        label="four linear elements",
    )
    left.set_ylabel("displacement u (mm)")
    right.plot(
        x,
        bar_stress(x, LENGTH, AREA, WEIGHT, FORCE) / 1e6,
        color=FIGURE_COLOURS[0],
        linestyle="-",
        label="closed form",
    )
    right.stairs(
        bar.stress / 1e6,
        bar.x,
        baseline=None,
        color=FIGURE_COLOURS[1],
        linestyle="--",
        label="element stress",
    )
    right.plot(
        (bar.x[:-1] + bar.x[1:]) / 2,
        bar.stress / 1e6,
        "s",
        color=FIGURE_COLOURS[1],
        markerfacecolor="none",
        label="at the midpoints",
    )
    right.set_ylabel("stress sigma (MPa)")
    for ax in (left, right):
        ax.set_xlabel("distance x from the support (m)")
        ax.set_xlim(0, LENGTH)
        ax.legend(fontsize="small", loc="best")
    fig.tight_layout()
    return fig


def plate(cells: int, supports):
    """The plate on a mesh of ``cells`` x ``cells / 4`` squares, each split
    into two triangles, pulled by SIGMA on its right edge and held on its
    left edge by ``supports``."""
    mesh = rectangle(WIDTH, HEIGHT, cells, cells // 4)
    load = traction_load(mesh, "right", (SIGMA, 0.0), THICKNESS)
    return mesh, solve_plate(mesh, E, NU, THICKNESS, load, supports(mesh))


def patch(experiment: Experiment):
    """The plate with the roller support against uniform tension; record
    the table and return the largest errors."""
    rows, errors = [], []
    scale = SIGMA * WIDTH / E
    for cells in meshes:
        mesh, result = plate(cells, roller_supports)
        exact = uniform_tension(mesh.nodes, E, NU, SIGMA)
        u_error = np.max(np.abs(result.u - exact)) / scale
        s_error = np.max(np.abs(result.stress - [SIGMA, 0.0, 0.0])) / SIGMA
        strain_x = result.stress[:, 0] - NU * result.stress[:, 1]
        strain_y = result.stress[:, 1] - NU * result.stress[:, 0]
        ratio = float(np.mean(-strain_y / strain_x))
        errors += [u_error, s_error]
        rows.append(
            (
                cells,
                len(mesh.triangles),
                bound(u_error, 1e-12),
                bound(s_error, 1e-12),
                ratio,
            )
        )
    experiment.table(
        "patch",
        rows,
        [
            ("cells along the width", "", "d"),
            ("triangles", "", "d"),
            ("largest displacement error / (sigma W / E)", "", ""),
            ("largest stress error / sigma", "", ""),
            ("-epsilon_yy / epsilon_xx", "", ".6f"),
        ],
        "A steel plate of 20 cm by 5 cm by 1 cm in plane stress, pulled by "
        "100 MPa on its right edge, its left edge on rollers: the linear "
        "elements against the closed form of uniform tension, and the ratio "
        "of the sideways to the lengthwise strain.",
    )
    return max(errors)


def contraction(mesh, result, distance):
    """The change of the plate's height at ``distance`` heights from the
    clamp, divided by the free change -nu sigma H / E."""
    x = distance * HEIGHT
    column = np.flatnonzero(np.isclose(mesh.nodes[:, 0], x))
    y = mesh.nodes[column, 1]
    top, bottom = column[np.argmax(y)], column[np.argmin(y)]
    change = result.u[top, 1] - result.u[bottom, 1]
    return change / (-NU * SIGMA * HEIGHT / E)


def clamped(experiment: Experiment):
    """The clamped plate on three meshes: the balance of the reactions,
    the end displacement, the largest stress, and the recovery of the free
    contraction with the distance from the clamp; record the tables and
    return the profiles and the largest stresses."""
    rows, profiles, peaks, balances = [], [], [], []
    applied = SIGMA * HEIGHT * THICKNESS
    for cells in clamped_meshes:
        mesh, result = plate(cells, clamped_supports)
        balance = abs(result.reactions[0::2].sum() + applied) / applied
        right = mesh.boundary_nodes("right")
        end = np.mean(result.u[right, 0]) / (SIGMA * WIDTH / E)
        peak = float(np.max(result.stress[:, 0]) / SIGMA)
        balances.append(balance)
        peaks.append(peak)
        profiles.append([contraction(mesh, result, d) for d in distances])
        rows.append((cells, len(mesh.triangles), bound(balance, 1e-10), end, peak))
    experiment.table(
        "clamped",
        rows,
        [
            ("cells along the width", "", "d"),
            ("triangles", "", "d"),
            ("reactions + load, relative", "", ""),
            ("mean end displacement / (sigma W / E)", "", ".5f"),
            ("largest sigma_xx / sigma", "", ".3f"),
        ],
        "The same plate with its left edge clamped (both displacements zero), "
        "on three meshes: the balance of the forces, the mean displacement "
        "of the loaded edge, and the largest stress, found at the corners of "
        "the clamped edge.",
    )
    experiment.table(
        "recovery",
        [(d, *(p[i] for p in profiles)) for i, d in enumerate(distances)],
        [("distance from the clamp", "H", "g")]
        + [(f"{cells} cells", "", ".4f") for cells in clamped_meshes],
        "The change of the plate's height at a distance from the clamp, "
        "divided by its free value -nu sigma H / E, on three meshes: zero at "
        "the clamp, one far from it.",
    )
    return profiles, peaks, max(balances)


def draw_plate(profiles) -> Figure:
    """The clamped plate deformed, with sigma_xx in false colour, and the
    recovery of the free contraction with the distance from the clamp."""
    mesh, result = plate(64, clamped_supports)
    scale = 0.2 * HEIGHT / np.max(np.abs(result.u))  # exaggerate the shape
    moved = mesh.nodes + scale * result.u
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(6.6, 5.4), gridspec_kw={"height_ratios": [1.1, 1]}
    )
    image = top.tripcolor(
        Triangulation(100 * moved[:, 0], 100 * moved[:, 1], mesh.triangles),
        result.stress[:, 0] / SIGMA,
        cmap="viridis",
        shading="flat",
        vmin=0.9,
        vmax=1.1,
    )
    top.plot(
        100 * np.array([0, WIDTH, WIDTH, 0, 0]),
        100 * np.array([0, 0, HEIGHT, HEIGHT, 0]),
        color=FIGURE_COLOURS[2],
        linestyle=":",
        linewidth=1,
        label="undeformed outline",
    )
    top.axvline(0, color=FIGURE_COLOURS[1], linewidth=3, label="clamped edge")
    top.set_aspect("equal")
    top.set_xlabel("x (cm); displacements exaggerated")
    top.set_ylabel("y (cm)")
    top.legend(fontsize="small", loc="upper right", bbox_to_anchor=(1.0, 1.45), ncol=2)
    bar = fig.colorbar(
        image, ax=top, orientation="vertical", fraction=0.04, extend="both"
    )
    bar.set_label("sigma_xx / sigma (false colour)")
    markers = ("o", "s", "^")
    styles = ("-", "--", ":")
    for cells, profile, marker, style in zip(
        clamped_meshes, profiles, markers, styles, strict=True
    ):
        bottom.plot(
            distances,
            profile,
            marker=marker,
            linestyle=style,
            color=FIGURE_COLOURS[0],
            markerfacecolor="none",
            label=f"clamped, {cells} cells along the width",
        )
    bottom.axhline(
        1.0,
        color=FIGURE_COLOURS[2],
        linestyle="-.",
        label="free contraction (rollers, closed form)",
    )
    bottom.set_xlabel("distance from the clamp (units of the height H)")
    bottom.set_ylabel("change of height / (-nu sigma H / E)")
    bottom.set_ylim(0, 1.1)
    bottom.legend(fontsize="small", loc="lower right")
    fig.tight_layout()
    return fig


def two_materials():
    """Exercise 1: a bar of 1 m of steel and 1 m of aluminium (E = 70 GPa)
    in series, 1 cm^2, pulled by 10 kN, on ten elements; the end
    displacement against F (L1 / (E1 A) + L2 / (E2 A)), and the stress of
    each element."""
    x = np.linspace(0.0, 2.0, 11)
    modulus = np.where((x[:-1] + x[1:]) / 2 < 1.0, E, 70e9)
    k = bar_stiffness(x, modulus, AREA)
    f = bar_load(x, 0.0, 1e4)
    u = solve(k, f, np.array([0]), np.array([0.0]))
    closed = 1e4 * (1.0 / (E * AREA) + 1.0 / (70e9 * AREA))
    stress = modulus * np.diff(u) / np.diff(x)
    return u[-1], closed, stress


def no_contraction():
    """Exercise 2: the clamped and the roller plate with nu = 0, on 32
    cells: the largest difference of their displacements, relative to
    sigma W / E."""
    mesh = rectangle(WIDTH, HEIGHT, 32, 8)
    load = traction_load(mesh, "right", (SIGMA, 0.0), THICKNESS)
    held = solve_plate(mesh, E, 0.0, THICKNESS, load, clamped_supports(mesh))
    free = solve_plate(mesh, E, 0.0, THICKNESS, load, roller_supports(mesh))
    return float(np.max(np.abs(held.u - free.u)) / (SIGMA * WIDTH / E))


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()

    nodal, middle, balance = bars(experiment)
    assert nodal < 1e-12 and middle < 1e-12 and balance < 1e-12
    experiment.figure("fig-bar", draw_bar)
    experiment.number(
        "tip-mm", 1e3 * bar_displacement(LENGTH, LENGTH, E, AREA, WEIGHT, FORCE), ".3f"
    )
    experiment.number(
        "top-stress", bar_stress(0.0, LENGTH, AREA, WEIGHT, FORCE) / 1e6, ".2f"
    )
    experiment.number("weight-kn", WEIGHT * LENGTH / 1e3, ".2f")

    assert patch(experiment) < 1e-12

    profiles, peaks, balance = clamped(experiment)
    assert balance < 1e-10
    assert peaks == sorted(peaks) and peaks[-1] > peaks[0] + 0.1
    finest = profiles[-1]
    assert finest[0] < 0.9 and abs(finest[-1] - 1) < 1e-4
    experiment.figure("fig-plate", partial(draw_plate, profiles))
    experiment.number(
        "recovery-two",
        max(abs(p[distances.index(2.0)] - 1) for p in profiles),
        ".1e",
    )
    experiment.number(
        "mesh-spread-one",
        max(p[distances.index(1.0)] for p in profiles)
        - min(p[distances.index(1.0)] for p in profiles),
        ".1e",
    )

    end, closed, stress = two_materials()
    experiment.number("series-end-mm", 1e3 * end, ".4f")
    experiment.number("series-closed-mm", 1e3 * closed, ".4f")
    experiment.number("series-gap", bound(abs(end / closed - 1), 1e-12), "")
    experiment.number(
        "series-stress-spread",
        bound(float(np.ptp(stress) / np.mean(stress)), 1e-12),
        "",
    )
    experiment.number("no-contraction", bound(no_contraction(), 1e-12), "")
    return experiment


if __name__ == "__main__":
    main(run)
