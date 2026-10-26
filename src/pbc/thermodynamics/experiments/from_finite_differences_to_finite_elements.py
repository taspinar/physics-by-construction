"""The experiment of the lesson "From finite differences to finite elements".

Piecewise-linear finite elements (``pbc.fem``) for steady heat conduction: a
manufactured solution with fixed and convective sides, refined to measure the
orders of the L2 and H1 errors; on a structured mesh the comparison with the
five-point finite differences of ``pbc.thermodynamics.conduction``; an
insulated pipe on an annulus meshed in the lesson, its mesh quality, its heat
loss against the exact one, and its heat balance closed with the consistent
boundary flux. Run it as a program to write the figures and numbers of the
page:

    uv run --locked --no-dev python -m \\
        pbc.thermodynamics.experiments.from_finite_differences_to_finite_elements out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.tri import Triangulation

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.fem.assembly import (
    convection,
    edge_outflow,
    errors,
    load,
    residual,
    solve,
    stiffness,
)
from pbc.fem.mesh import Mesh, angles, annulus, areas, radius_ratio, rectangle, size
from pbc.thermodynamics.conduction import steady_plate
from pbc.verification.estimates import fitted_order

# region: manufactured
WAVE, GROWTH, PHASE = 2.0, 1.0, 0.5  # u = sin(WAVE x + PHASE) exp(GROWTH y)
H_TOP = 2.0  # the heat transfer coefficient of the convective top side
REFINEMENTS = [4, 8, 16, 32, 64]  # cells per side of the unit square
# endregion: manufactured
# region: plate
PLATE_REFINEMENTS = [8, 16, 32]  # cells per side
# endregion: plate
# region: pipe
R_PIPE, R_OUTER = 0.02, 0.05  # m, the pipe wall and the outside of the insulation
K_INSULATION = 0.05  # W/(m K), mineral wool
H_AIR = 10.0  # W/(m^2 K), still air outside
T_PIPE, T_AIR = 90.0, 20.0  # degrees C
LAYERS = [2, 4, 8, 16, 32]  # rings of triangles across the insulation
WIRE_LAYERS = 48  # graded rings across the insulation of the wire (exercise)
# endregion: pipe


def below(value: float, bound: float) -> str:
    """A gap at the level of round-off is not shown as a number: only that it
    is smaller than ``bound``."""
    if abs(value) >= bound:
        raise ValueError(f"{value!r} is not below {bound!r}")
    return f"below {bound:.0e}"


def manufactured(x, y):
    """The chosen solution u(x, y) of the manufactured problem."""
    return np.sin(WAVE * x + PHASE) * np.exp(GROWTH * y)


def manufactured_gradient(x, y):
    """Its gradient, the two components in the last axis."""
    return np.stack(
        [
            WAVE * np.cos(WAVE * x + PHASE) * np.exp(GROWTH * y),
            GROWTH * manufactured(x, y),
        ],
        axis=-1,
    )


def manufactured_source(x, y):
    """f = -laplacian(u) = (WAVE^2 - GROWTH^2) u, with k = 1."""
    return (WAVE**2 - GROWTH**2) * manufactured(x, y)


def manufactured_fluid(x, y):
    """The fluid temperature g that makes the top side's condition
    -du/dy = H_TOP (u - g) hold for u: g = u + (du/dy) / H_TOP."""
    return manufactured(x, y) * (1.0 + GROWTH / H_TOP)


def solve_manufactured(cells: int) -> tuple[Mesh, np.ndarray]:
    """The manufactured problem on the unit square: fixed values of u on the
    bottom, left, and right sides, convection on the top."""
    mesh = rectangle(1.0, 1.0, cells, cells)
    top_matrix, top_vector = convection(
        mesh, mesh.boundary["top"], H_TOP, manufactured_fluid
    )
    matrix = stiffness(mesh) + top_matrix
    vector = load(mesh, manufactured_source) + top_vector
    fixed = mesh.boundary_nodes("bottom", "left", "right")
    u = solve(matrix, vector, fixed, manufactured(*mesh.nodes[fixed].T))
    return mesh, u


def manufactured_convergence(experiment: Experiment):
    """The L2 and H1 errors against the manufactured solution as the mesh is
    refined; record the table and the fitted orders, and return h and the
    errors."""
    rows, sizes, l2, h1 = [], [], [], []
    for cells in REFINEMENTS:
        mesh, u = solve_manufactured(cells)
        e_l2, e_h1 = errors(mesh, u, manufactured, manufactured_gradient)
        sizes.append(size(mesh))
        l2.append(e_l2)
        h1.append(e_h1)
        rows.append((cells, len(mesh.nodes), size(mesh), e_l2, e_h1))
    experiment.table(
        "manufactured",
        rows,
        [
            ("cells per side", "", "d"),
            ("nodes", "", "d"),
            ("h", "", ".4f"),
            ("L2 error", "", ".2e"),
            ("H1 error", "", ".2e"),
        ],
        "The error of the finite-element solution against the manufactured "
        "solution on the unit square (dimensionless), in the L2 norm and in the "
        "H1 seminorm (the L2 norm of the gradient error), as the mesh is "
        "refined; h is the longest side of any triangle.",
    )
    experiment.number("l2-order", fitted_order(sizes, l2), ".2f")
    experiment.number("h1-order", fitted_order(sizes, h1), ".2f")
    return sizes, l2, h1


def stencil_gap(cells: int) -> float:
    """The largest difference between a row of the finite-element stiffness
    matrix (k = 1) at an interior node of the structured mesh and the
    five-point stencil: 4 on the node, -1 on its four neighbours."""
    mesh = rectangle(1.0, 1.0, cells, cells)
    matrix = stiffness(mesh).toarray()
    width = cells + 1
    gap = 0.0
    for row in range(1, cells):
        for column in range(1, cells):
            node = row * width + column
            stencil = np.zeros(len(mesh.nodes))
            stencil[node] = 4.0
            stencil[[node - 1, node + 1, node - width, node + width]] = -1.0
            gap = max(gap, float(np.max(np.abs(matrix[node] - stencil))))
    return gap


def sine_plate(x, y):
    """The exact temperature of the plate example, sin(pi x) sin(pi y)."""
    return np.sin(np.pi * x) * np.sin(np.pi * y)


def sine_source(x, y):
    """The heat source that makes it the solution, 2 pi^2 sin sin (k = 1)."""
    return 2.0 * np.pi**2 * sine_plate(x, y)


def fd_against_fem(experiment: Experiment) -> None:
    """The unit plate with the sine source and zero edges, by the five-point
    finite differences and by the finite elements on the same nodes; record
    the table and the stencil gap."""
    rows = []
    for cells in PLATE_REFINEMENTS:
        mesh = rectangle(1.0, 1.0, cells, cells)
        x, y = mesh.nodes.T
        exact = sine_plate(x, y)
        fixed = mesh.boundary_nodes("bottom", "right", "top", "left")
        fem = solve(
            stiffness(mesh), load(mesh, sine_source), fixed, np.zeros(len(fixed))
        )
        grid = (cells + 1, cells + 1)
        fd = steady_plate(
            np.zeros(grid), sine_source(x, y).reshape(grid), 1.0 / cells, 1.0
        ).ravel()
        rows.append(
            (
                cells,
                np.max(np.abs(fd - exact)),
                np.max(np.abs(fem - exact)),
                np.max(np.abs(fd - fem)),
            )
        )
    experiment.table(
        "fd-against-fem",
        rows,
        [
            ("cells per side", "", "d"),
            ("finite differences, largest error", "", ".2e"),
            ("finite elements, largest error", "", ".2e"),
            ("largest difference between them", "", ".2e"),
        ],
        "The unit plate with a sine-shaped heat source and edges at zero "
        "(dimensionless), by the five-point finite differences of the previous "
        "lesson and by linear finite elements on the same nodes, against the "
        "exact solution sin(pi x) sin(pi y).",
    )
    experiment.number("stencil-gap", below(stencil_gap(PLATE_REFINEMENTS[0]), 1e-12))


def polygon_annulus_area(mesh: Mesh) -> float:
    """The area between the outer and the inner polygon of the boundary, by
    the shoelace formula over the boundary edges."""
    total = 0.0
    for name in ("outer", "inner"):
        a, b = (
            mesh.nodes[mesh.boundary[name][:, 0]],
            mesh.nodes[mesh.boundary[name][:, 1]],
        )
        total += 0.5 * np.sum(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0])
    return total


def inspect_meshes(experiment: Experiment) -> None:
    """The annulus meshes of the pipe: their size and quality; record the
    table and the smallest angle of any of them."""
    rows, smallest = [], 180.0
    for layers in LAYERS:
        mesh = annulus(R_PIPE, R_OUTER, layers)
        angle = angles(mesh).min()
        ratio = radius_ratio(mesh)
        area_gap = abs(np.sum(areas(mesh)) - polygon_annulus_area(mesh))
        smallest = min(smallest, angle)
        rows.append(
            (
                layers,
                len(mesh.nodes),
                len(mesh.triangles),
                1e3 * size(mesh),
                angle,
                ratio.min(),
                ratio.mean(),
                below(area_gap / polygon_annulus_area(mesh), 1e-12),
            )
        )
    experiment.table(
        "mesh-quality",
        rows,
        [
            ("layers", "", "d"),
            ("nodes", "", "d"),
            ("triangles", "", "d"),
            ("h", "mm", ".2f"),
            ("smallest angle", "degrees", ".1f"),
            ("smallest radius ratio", "", ".3f"),
            ("mean radius ratio", "", ".3f"),
            ("triangles against the polygon, relative area gap", "", ""),
        ],
        "The annulus meshes of the insulation, from two to thirty-two layers of "
        "triangles: their size, the smallest angle of any triangle, the radius "
        "ratio 2 r_in / r_out (one for an equilateral triangle), and the area of "
        "the triangles against the area between the two boundary polygons.",
    )
    experiment.number("smallest-angle", smallest, ".1f")


def exact_heat_loss(inner: float, outer: float, k: float, h: float, dt: float):
    """The heat lost per metre of pipe through a cylinder of insulation (W/m):
    the temperature difference over the conduction resistance
    ln(r_o / r_i) / (2 pi k) and the convection resistance 1 / (2 pi r_o h)."""
    return 2.0 * np.pi * dt / (np.log(outer / inner) / k + 1.0 / (h * outer))


def exact_pipe_temperature(r):
    """The exact temperature in the insulation: it falls with ln(r)."""
    q = exact_heat_loss(R_PIPE, R_OUTER, K_INSULATION, H_AIR, T_PIPE - T_AIR)
    return T_PIPE - q * np.log(r / R_PIPE) / (2.0 * np.pi * K_INSULATION)


def solve_pipe(
    layers: int,
    inner=R_PIPE,
    outer=R_OUTER,
    k=K_INSULATION,
    t_pipe=T_PIPE,
    graded=False,
):
    """The insulation of the pipe: the inner wall fixed at the pipe
    temperature, convection to the air on the outside, on an annulus of
    ``layers`` rings, evenly spaced or ``graded``. Returns the mesh, the
    temperature, the system, and the fixed nodes."""
    mesh = annulus(inner, outer, layers, graded)
    air_matrix, air_vector = convection(
        mesh, mesh.boundary["outer"], H_AIR, lambda x, y: np.full_like(x, T_AIR)
    )
    matrix = stiffness(mesh, k) + air_matrix
    vector = air_vector
    fixed = mesh.boundary_nodes("inner")
    u = solve(matrix, vector, fixed, np.full(len(fixed), t_pipe))
    return mesh, u, matrix, vector, fixed


def heat_flows(layers: int) -> tuple[Mesh, float, float, float]:
    """The heat into the insulation at the pipe wall from the residual at the
    fixed nodes, the heat out into the air along the convective edges, and
    the heat in from the gradient on the wall's triangles (W/m)."""
    mesh, u, matrix, vector, fixed = solve_pipe(layers)
    heat_in = float(residual(matrix, vector, u)[fixed].sum())
    outer = mesh.boundary["outer"]
    length = np.linalg.norm(mesh.nodes[outer[:, 1]] - mesh.nodes[outer[:, 0]], axis=1)
    mean = 0.5 * (u[outer[:, 0]] + u[outer[:, 1]])
    heat_out = float(np.sum(H_AIR * length * (mean - T_AIR)))
    from_gradient = -float(
        edge_outflow(mesh, mesh.boundary["inner"], u, K_INSULATION).sum()
    )
    return mesh, heat_in, heat_out, from_gradient


def pipe_refinement(experiment: Experiment):
    """The heat loss of the pipe on each mesh against the exact one, and the
    balance between the heat in and the heat out; record the table and the
    numbers, and return h and the two relative errors."""
    exact = exact_heat_loss(R_PIPE, R_OUTER, K_INSULATION, H_AIR, T_PIPE - T_AIR)
    rows, sizes, consistent, gradient, gaps = [], [], [], [], []
    for layers in LAYERS:
        mesh, heat_in, heat_out, from_gradient = heat_flows(layers)
        sizes.append(size(mesh))
        consistent.append(abs(heat_in - exact) / exact)
        gradient.append(abs(from_gradient - exact) / exact)
        gaps.append(abs(heat_in - heat_out) / heat_in)
        rows.append(
            (
                layers,
                1e3 * size(mesh),
                heat_in,
                heat_out,
                below(gaps[-1], 1e-10),
                consistent[-1],
                from_gradient,
                gradient[-1],
            )
        )
    experiment.table(
        "pipe",
        rows,
        [
            ("layers", "", "d"),
            ("h", "mm", ".2f"),
            ("heat in at the pipe, residual", "W/m", ".4f"),
            ("heat out into the air", "W/m", ".4f"),
            ("relative balance gap", "", ""),
            ("residual flux, relative error", "", ".1e"),
            ("heat in at the pipe, gradient", "W/m", ".3f"),
            ("gradient flux, relative error", "", ".1e"),
        ],
        "The heat lost per metre of insulated pipe on each mesh: in at the pipe "
        "wall from the residual of the fixed nodes, out into the air along the "
        "convective edges, and in at the wall from the gradient of the "
        "triangles there, each against the exact heat loss.",
    )
    experiment.number("exact-heat-loss", exact, ".4f")
    experiment.number("balance-gap", below(max(gaps), 1e-10))
    experiment.number("pipe-order", fitted_order(sizes, consistent), ".2f")
    experiment.number("gradient-order", fitted_order(sizes, gradient), ".2f")
    experiment.number("pipe-error", consistent[-1], ".1e")
    return sizes, consistent, gradient


def draw_annulus_mesh() -> Figure:
    """The coarsest useful annulus mesh, and the distribution of the smallest
    angle of its triangles for three refinements."""
    fig, (left, right) = plt.subplots(
        1, 2, figsize=(7.2, 3.4), gridspec_kw={"width_ratios": [1, 1.2]}
    )
    mesh = annulus(R_PIPE, R_OUTER, LAYERS[1])
    left.triplot(
        Triangulation(*(1e2 * mesh.nodes.T), mesh.triangles),
        color=FIGURE_COLOURS[0],
        linewidth=0.6,
    )
    for name, line in (("inner", "-"), ("outer", "--")):
        edges = mesh.boundary[name]
        for a, b in edges:
            left.plot(
                *(1e2 * mesh.nodes[[a, b]].T),
                color=FIGURE_COLOURS[1],
                linestyle=line,
                linewidth=1.6,
            )
    left.set_aspect("equal")
    left.set_xlabel("x (cm)")
    left.set_ylabel("y (cm)")
    bins = np.arange(40, 62, 2)
    for layers, line, colour in (
        (LAYERS[1], "-", FIGURE_COLOURS[0]),
        (LAYERS[2], "--", FIGURE_COLOURS[1]),
        (LAYERS[4], ":", FIGURE_COLOURS[4]),
    ):
        smallest = angles(annulus(R_PIPE, R_OUTER, layers)).min(axis=1)
        right.hist(
            smallest,
            bins=bins,
            density=True,
            histtype="step",
            color=colour,
            linestyle=line,
            linewidth=1.6,
            label=f"{layers} layers",
        )
    right.axvline(60.0, color=FIGURE_COLOURS[2], linewidth=0.8)
    right.annotate(
        "equilateral",
        (60.0, 0.5),
        xycoords=("data", "axes fraction"),
        xytext=(-4, 0),
        textcoords="offset points",
        ha="right",
        rotation=90,
        color=FIGURE_COLOURS[2],
        fontsize="small",
    )
    right.set_xlabel("smallest angle of a triangle (degrees)")
    right.set_ylabel("fraction per degree")
    right.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    return fig


def draw_fem_convergence(manufactured_errors, pipe_errors) -> Figure:
    """Log-log errors against h: the manufactured solution in L2 and H1, and
    the pipe's heat loss from the residual and from the gradient, with
    reference slopes."""
    fig, (left, right) = plt.subplots(1, 2, figsize=(7.2, 3.6))
    h, l2, h1 = (np.array(v) for v in manufactured_errors)
    left.loglog(h, l2, color=FIGURE_COLOURS[0], marker="o", label="L2 error")
    left.loglog(
        h, h1, color=FIGURE_COLOURS[1], marker="s", linestyle="--", label="H1 error"
    )
    hp, consistent, gradient = (np.array(v) for v in pipe_errors)
    hp = 1e3 * hp
    right.loglog(
        hp, consistent, color=FIGURE_COLOURS[0], marker="o", label="residual flux"
    )
    right.loglog(
        hp,
        gradient,
        color=FIGURE_COLOURS[1],
        marker="s",
        linestyle="--",
        label="gradient flux",
    )
    for ax, x, top, bottom in ((left, h, h1, l2), (right, hp, gradient, consistent)):
        ax.loglog(
            x,
            0.5 * bottom[0] * (x / x[0]) ** 2,
            color=FIGURE_COLOURS[2],
            linestyle=":",
            label="reference, slope two",
        )
        ax.loglog(
            x,
            0.5 * top[0] * (x / x[0]),
            color=FIGURE_COLOURS[2],
            linestyle="-.",
            label="reference, slope one",
        )
        ax.set_xticks(x, labels=[f"{value:.2g}" for value in x])
        ax.minorticks_off()
        low, high = ax.get_ylim()
        ax.set_ylim(low, high * 100)
        ax.legend(frameon=False, loc="upper left", fontsize="small")
    left.set_xlabel("h (dimensionless)")
    left.set_ylabel("error (dimensionless)")
    right.set_xlabel("h (mm)")
    right.set_ylabel("relative error of the heat loss")
    fig.tight_layout()
    return fig


def draw_pipe_temperature() -> Figure:
    """The temperature in the insulation on a mesh, false colour, and the node
    values against the radius with the exact profile."""
    mesh, u, *_ = solve_pipe(LAYERS[2])
    fig, (left, right) = plt.subplots(
        1, 2, figsize=(7.2, 3.4), gridspec_kw={"width_ratios": [1.15, 1]}
    )
    image = left.tripcolor(
        Triangulation(*(1e2 * mesh.nodes.T), mesh.triangles),
        u,
        shading="gouraud",
        cmap="viridis",
    )
    left.triplot(
        Triangulation(*(1e2 * mesh.nodes.T), mesh.triangles),
        color="white",
        linewidth=0.3,
    )
    left.set_aspect("equal")
    left.set_xlabel("x (cm)")
    left.set_ylabel("y (cm)")
    fig.colorbar(image, ax=left, label="temperature (°C) (false colour)")
    r = np.hypot(*mesh.nodes.T)
    fine = np.linspace(R_PIPE, R_OUTER, 200)
    right.plot(
        1e2 * fine,
        exact_pipe_temperature(fine),
        color=FIGURE_COLOURS[2],
        linestyle="--",
        label="exact",
    )
    right.plot(
        1e2 * r,
        u,
        color=FIGURE_COLOURS[0],
        marker="o",
        markersize=3,
        linestyle="none",
        label="finite elements, nodes",
    )
    right.set_xlabel("radius (cm)")
    right.set_ylabel("temperature (°C)")
    right.legend(frameon=False)
    fig.tight_layout()
    return fig


def critical_radius(experiment: Experiment) -> None:
    """Exercise 1: the heat lost by an insulated wire against the outer
    radius of its insulation, exact and by finite elements; record the
    table."""
    wire, k, warm = 0.001, 0.2, 40.0  # m, W/(m K), degrees C above the air
    rows = []
    for outer in (0.002, 0.005, 0.01, k / H_AIR, 0.04, 0.08):
        _, u, matrix, vector, fixed = solve_pipe(
            WIRE_LAYERS, inner=wire, outer=outer, k=k, t_pipe=T_AIR + warm, graded=True
        )
        fem = float(residual(matrix, vector, u)[fixed].sum())
        rows.append((1e3 * outer, exact_heat_loss(wire, outer, k, H_AIR, warm), fem))
    experiment.table(
        "critical-radius",
        rows,
        [
            ("outer radius", "mm", ".1f"),
            ("heat loss, exact", "W/m", ".3f"),
            ("heat loss, finite elements", "W/m", ".3f"),
        ],
        "The heat lost per metre by a wire of radius 1 mm, 40 degrees C above "
        "the air, through insulation of conductivity 0.2 W/(m K), against the "
        "outer radius of the insulation, on graded meshes; the fourth row is k / h.",
    )


def gradient_mesh(experiment: Experiment) -> None:
    """Exercise 2: the layers the gradient flux needs for an error of one per
    cent, extrapolated from the finest mesh with the measured order one;
    record the table."""
    _, heat_in, _, from_gradient = heat_flows(LAYERS[-1])
    exact = exact_heat_loss(R_PIPE, R_OUTER, K_INSULATION, H_AIR, T_PIPE - T_AIR)
    error = abs(from_gradient - exact) / exact
    needed = LAYERS[-1] * error / 0.01
    experiment.table(
        "gradient-mesh",
        [(LAYERS[-1], error, int(np.ceil(needed)), abs(heat_in - exact) / exact)],
        [
            ("layers now", "", "d"),
            ("gradient flux, relative error", "", ".3f"),
            ("layers for one per cent", "", "d"),
            ("residual flux on the present mesh, relative error", "", ".1e"),
        ],
        "The layers the gradient flux needs to be within one per cent of the "
        "exact heat loss, if its error stays proportional to h, against the "
        "error of the residual flux on the finest mesh of the lesson.",
    )


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    manufactured_errors = manufactured_convergence(experiment)
    fd_against_fem(experiment)
    inspect_meshes(experiment)
    experiment.figure("fig-annulus-mesh", draw_annulus_mesh)
    pipe_errors = pipe_refinement(experiment)
    experiment.figure(
        "fig-fem-convergence",
        partial(draw_fem_convergence, manufactured_errors, pipe_errors),
    )
    experiment.figure("fig-pipe-temperature", draw_pipe_temperature)
    critical_radius(experiment)
    gradient_mesh(experiment)
    return experiment


if __name__ == "__main__":
    main(run)
