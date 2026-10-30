"""Linear elasticity: a bar loaded along its axis, and a plate in plane
stress, both by piecewise-linear finite elements.

A bar of Young's modulus E (Pa) and cross-section A (m^2) along [0, L],
fixed at x = 0, carries a load q (N/m) spread along it, its own weight
rho g A when it hangs, and a force F (N) at its free end. Its displacement
u(x) (m) obeys -E A u'' = q with u(0) = 0 and E A u'(L) = F, whose solution
for a constant q is

    u(x) = (F x + q (L x - x^2 / 2)) / (E A),
    sigma(x) = E u'(x) = (F + q (L - x)) / A.

Linear elements of length h make the bar a chain of springs of stiffness
E A / h, each node carrying the load of half of each element beside it.

A thin plate in the plane, loaded in its plane, has the stresses
sigma = (sigma_xx, sigma_yy, tau_xy) (Pa) and the strains
epsilon = (du_x/dx, du_y/dy, du_x/dy + du_y/dx), related by Hooke's law in
plane stress, sigma = D epsilon with

    D = E / (1 - nu^2) [[1, nu, 0], [nu, 1, 0], [0, 0, (1 - nu) / 2]].

The displacement is linear on every triangle of a ``pbc.fem`` mesh, with
two unknowns per node (u_x, u_y, interleaved), so the strain and the
stress are constant on each triangle. The element stiffness is
t A B^T D B, with B built from the gradients of the hat functions
(``pbc.fem.assembly.gradients``), and the load of a traction on an edge is
assembled by ``pbc.fem.assembly.edge_load``. A uniform tension
sigma_0 along x, with the plate free to contract sideways, is

    u_x = sigma_0 x / E,  u_y = -nu sigma_0 y / E,

and a linear displacement is reproduced exactly by linear elements.
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy import sparse

from pbc.fem.assembly import edge_load, gradients, residual, solve
from pbc.fem.mesh import Mesh, areas

Array = NDArray[np.float64]


# --- the bar -----------------------------------------------------------------


def bar_stiffness(x: Array, modulus, area: float) -> sparse.csr_matrix:
    """The stiffness matrix (N/m) of a bar with the nodes ``x`` (m),
    element by element: the element between x_i and x_(i+1) is a spring
    of stiffness E A / h that adds k to the two diagonal entries of its
    nodes and -k to the two between them. The modulus is a constant or one
    value per element, so that a part of the bar can be another material."""
    h = np.diff(x)
    if np.any(h <= 0):
        raise ValueError("the nodes must increase along the bar")
    k = modulus * area / h
    n = len(x)
    i = np.arange(n - 1)
    rows = np.concatenate([i, i + 1, i, i + 1])
    cols = np.concatenate([i, i + 1, i + 1, i])
    values = np.concatenate([k, k, -k, -k])
    return sparse.coo_matrix((values, (rows, cols)), shape=(n, n)).tocsr()


def bar_load(x: Array, q: float, end_force: float) -> Array:
    """The nodal loads (N) of a constant load q (N/m) along the bar and a
    force at its last node: each element hands q h / 2 to each of its two
    nodes, which is the integral of q times each hat function."""
    h = np.diff(x)
    f = np.zeros(len(x))
    f[:-1] += q * h / 2
    f[1:] += q * h / 2
    f[-1] += end_force
    return f


@dataclass(frozen=True)
class Bar:
    """A solved bar: the nodes (m), the nodal displacements (m), the stress
    of every element (Pa), and the force at the support (N)."""

    x: Array
    u: Array
    stress: Array
    reaction: float


def solve_bar(
    length: float,
    elements: int,
    modulus: float,
    area: float,
    q: float,
    end_force: float,
) -> Bar:
    """The bar fixed at x = 0 and loaded by q along it and F at x = L, on
    ``elements`` equal elements: the stiffness and the loads assembled,
    u(0) = 0 imposed, the system solved, and the stress E (u_(i+1) - u_i) / h
    of every element."""
    x = np.linspace(0.0, length, elements + 1)
    k = bar_stiffness(x, modulus, area)
    f = bar_load(x, q, end_force)
    u = solve(k, f, np.array([0]), np.array([0.0]))
    stress = modulus * np.diff(u) / np.diff(x)
    return Bar(x, u, stress, float(residual(k, f, u)[0]))


def bar_displacement(x, length, modulus, area, q, end_force):
    """The closed-form displacement (m) of the loaded bar,
    (F x + q (L x - x^2 / 2)) / (E A)."""
    x = np.asarray(x, dtype=float)
    return (end_force * x + q * (length * x - x**2 / 2)) / (modulus * area)


def bar_stress(x, length, area, q, end_force):
    """The closed-form stress (Pa) of the loaded bar, (F + q (L - x)) / A:
    the force carried through the section at x, divided by its area."""
    x = np.asarray(x, dtype=float)
    return (end_force + q * (length - x)) / area


# --- the plate in plane stress -----------------------------------------------


def plane_stress(modulus: float, poisson: float) -> Array:
    """The matrix D (Pa) of Hooke's law in plane stress, sigma = D epsilon,
    with the engineering shear strain gamma_xy = 2 epsilon_xy."""
    return (
        modulus
        / (1 - poisson**2)
        * np.array(
            [[1.0, poisson, 0.0], [poisson, 1.0, 0.0], [0.0, 0.0, (1 - poisson) / 2]]
        )
    )


def strain_matrices(mesh: Mesh) -> Array:
    """The matrix B (m x 3 x 6, 1/m) of every triangle, epsilon = B u_e, with
    u_e = (u_x0, u_y0, u_x1, u_y1, u_x2, u_y2) at its three nodes."""
    grad = gradients(mesh)
    b = np.zeros((len(mesh.triangles), 3, 6))
    b[:, 0, 0::2] = grad[:, :, 0]
    b[:, 1, 1::2] = grad[:, :, 1]
    b[:, 2, 0::2] = grad[:, :, 1]
    b[:, 2, 1::2] = grad[:, :, 0]
    return b


def element_dofs(mesh: Mesh) -> NDArray[np.int64]:
    """The six unknowns of every triangle, (2 i, 2 i + 1) for each node i."""
    t = mesh.triangles
    return np.stack([2 * t, 2 * t + 1], axis=-1).reshape(len(t), 6)


def plate_stiffness(
    mesh: Mesh, modulus: float, poisson: float, thickness: float
) -> sparse.csr_matrix:
    """K = sum over triangles of t A B^T D B (N/m), two unknowns per node."""
    b = strain_matrices(mesh)
    d = plane_stress(modulus, poisson)
    weight = thickness * np.abs(areas(mesh))
    local = weight[:, None, None] * np.einsum("tki,kl,tlj->tij", b, d, b)
    dofs = element_dofs(mesh)
    rows = np.repeat(dofs, 6, axis=1).ravel()
    cols = np.tile(dofs, (1, 6)).ravel()
    n = 2 * len(mesh.nodes)
    return sparse.coo_matrix((local.ravel(), (rows, cols)), shape=(n, n)).tocsr()


def traction_load(
    mesh: Mesh, group: str, traction: tuple[float, float], thickness: float
) -> Array:
    """The nodal forces (N) of a uniform traction (t_x, t_y) (Pa) on a named
    boundary group: the integral of the traction times each hat function
    along the edges (``edge_load``), times the thickness."""
    f = np.zeros(2 * len(mesh.nodes))
    edges = mesh.boundary[group]
    for component, value in enumerate(traction):
        f[component::2] = thickness * edge_load(
            mesh, edges, lambda x, y, v=value: np.full_like(x, v)
        )
    return f


@dataclass(frozen=True)
class Plate:
    """A solved plate: the displacements (n x 2, m), the stress of every
    triangle (m x 3: sigma_xx, sigma_yy, tau_xy, Pa), and the reactions at
    the supported unknowns (N per unknown, zero elsewhere)."""

    u: Array
    stress: Array
    reactions: Array


def solve_plate(
    mesh: Mesh,
    modulus: float,
    poisson: float,
    thickness: float,
    load: Array,
    fixed: NDArray[np.int64],
) -> Plate:
    """The plate with the unknowns ``fixed`` held at zero: K u = F solved at
    the others (``pbc.fem.assembly.solve``), the stress D B u_e of every
    triangle, and the reactions K u - F, which vanish at the free unknowns."""
    k = plate_stiffness(mesh, modulus, poisson, thickness)
    u = solve(k, load, fixed, np.zeros(len(fixed)))
    strain = np.einsum("tkj,tj->tk", strain_matrices(mesh), u[element_dofs(mesh)])
    stress = strain @ plane_stress(modulus, poisson).T
    return Plate(u.reshape(-1, 2), stress, residual(k, load, u))


def roller_supports(mesh: Mesh) -> NDArray[np.int64]:
    """The left edge free to slide along itself: u_x = 0 on every node of
    the left group, and u_y = 0 at its lowest node only, which removes the
    rigid motions and nothing more."""
    left = mesh.boundary_nodes("left")
    lowest = left[np.argmin(mesh.nodes[left, 1])]
    return np.sort(np.concatenate([2 * left, [2 * lowest + 1]]))


def clamped_supports(mesh: Mesh) -> NDArray[np.int64]:
    """The left edge glued to a rigid wall: u_x = u_y = 0 on every node of
    the left group."""
    left = mesh.boundary_nodes("left")
    return np.sort(np.concatenate([2 * left, 2 * left + 1]))


def uniform_tension(nodes: Array, modulus: float, poisson: float, stress: float):
    """The closed-form displacement (n x 2, m) of a plate in uniform tension
    sigma_0 along x, free to contract sideways, fixed at x = 0 and at the
    origin: u_x = sigma_0 x / E, u_y = -nu sigma_0 y / E."""
    x, y = nodes[:, 0], nodes[:, 1]
    return np.column_stack([stress * x / modulus, -poisson * stress * y / modulus])
