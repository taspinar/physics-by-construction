"""Piecewise-linear finite elements for -div(k grad u) = f on a triangular mesh.

The weak form asks for u such that, for every test function v that vanishes
where u is fixed,

    integral of k grad u . grad v  +  sum over convective edges of h u v
        = integral of f v  +  sum over convective edges of h g v,

which says that the heat each test function collects from the sources and
the fluid equals the heat it conducts away. With u and v linear on every
triangle and continuous across them, u is the vector of its node values and
the weak form becomes the sparse linear system K u = F: K holds the
conduction between neighbouring nodes and the convective edges, F the sources
and the fluid. A fixed value is imposed explicitly by removing its node from
the unknowns.

The residual K u - F of the full system, which vanishes at the free nodes,
is at a fixed node the heat that flows into the domain there: the boundary
flux consistent with the discrete balance.

The mass matrix M, the integral of c phi_i phi_j, adds what the steady
problem lacks: heat stored, c du/dt, for a transient (``pbc.fem.transient``),
and heat exchanged at every point with a fluid, c (u - g), for a thin plate
cooled over its face.
"""

from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray
from scipy import sparse
from scipy.sparse.linalg import spsolve

from pbc.fem.mesh import Indices, Mesh, areas

Array = NDArray[np.float64]
Field = Callable[[Array, Array], Array]

# A quadrature rule of degree four on a triangle (Strang and Fix): barycentric
# points and weights that sum to one.
_A, _B = 0.445948490915965, 0.091576213509771
QUADRATURE_POINTS = np.array(
    [
        [_A, _A, 1 - 2 * _A],
        [_A, 1 - 2 * _A, _A],
        [1 - 2 * _A, _A, _A],
        [_B, _B, 1 - 2 * _B],
        [_B, 1 - 2 * _B, _B],
        [1 - 2 * _B, _B, _B],
    ]
)
QUADRATURE_WEIGHTS = np.array([0.223381589678011] * 3 + [0.109951743655322] * 3)
# Two-point Gauss rule on an edge, as fractions along it, weights summing to one.
_EDGE_POINTS = 0.5 + np.array([-0.5, 0.5]) / np.sqrt(3.0)


def gradients(mesh: Mesh) -> Array:
    """The constant gradients of the three hat functions on every triangle
    (m x 3 x 2, 1/m): the hat of node i is one there and zero at the others,
    and its gradient is the side opposite i turned outward, divided by 2 A."""
    p = mesh.nodes[mesh.triangles]
    area = areas(mesh)
    grad = np.empty((len(area), 3, 2))
    for i in range(3):
        j, k = (i + 1) % 3, (i + 2) % 3
        grad[:, i, 0] = p[:, j, 1] - p[:, k, 1]
        grad[:, i, 1] = p[:, k, 0] - p[:, j, 0]
    return grad / (2.0 * area)[:, None, None]


def _scatter(mesh: Mesh, local: Array) -> sparse.csr_matrix:
    """Add the 3 x 3 matrices of the triangles into one sparse matrix."""
    rows = np.repeat(mesh.triangles, 3, axis=1).ravel()
    cols = np.tile(mesh.triangles, (1, 3)).ravel()
    n = len(mesh.nodes)
    return sparse.coo_matrix((local.ravel(), (rows, cols)), shape=(n, n)).tocsr()


def per_triangle(mesh: Mesh, coefficient: float | Array) -> Array:
    """A coefficient as one value per triangle: a constant is repeated, an
    array of one value per triangle is taken as it is."""
    values = np.asarray(coefficient, dtype=float)
    if values.ndim == 0:
        return np.full(len(mesh.triangles), float(values))
    if values.shape != (len(mesh.triangles),):
        raise ValueError("a coefficient is a constant or one value per triangle")
    return values


def stiffness(mesh: Mesh, conductivity: float | Array = 1.0) -> sparse.csr_matrix:
    """K_ij = integral of k grad phi_i . grad phi_j, triangle by triangle:
    k A times the dot products of the constant gradients (W/K). The
    conductivity is a constant or one value per triangle, so that a part of
    the domain can be another material."""
    grad = gradients(mesh)
    weight = per_triangle(mesh, conductivity) * np.abs(areas(mesh))
    local = weight[:, None, None] * np.einsum("tia,tja->tij", grad, grad)
    return _scatter(mesh, local)


def mass(mesh: Mesh, coefficient: float | Array = 1.0) -> sparse.csr_matrix:
    """M_ij = integral of c phi_i phi_j, with c a constant or one value per
    triangle: c A / 12 times [[2, 1, 1], [1, 2, 1], [1, 1, 2]] on every
    triangle, exact for linear hats. With c the heat capacity per unit
    volume it stores heat; with c a coefficient of exchange it couples every
    point of the domain to a fluid, as h couples a convective edge. Its
    entries sum to the integral of c."""
    weight = per_triangle(mesh, coefficient) * np.abs(areas(mesh)) / 12.0
    local = weight[:, None, None] * (np.ones((3, 3)) + np.eye(3))
    return _scatter(mesh, local)


def quadrature(mesh: Mesh) -> tuple[Array, Array]:
    """The points (m x 6 x 2) and weights (m x 6, m^2) of the degree-four rule
    on every triangle."""
    p = mesh.nodes[mesh.triangles]
    points = np.einsum("qi,tia->tqa", QUADRATURE_POINTS, p)
    weights = np.abs(areas(mesh))[:, None] * QUADRATURE_WEIGHTS[None, :]
    return points, weights


def load(mesh: Mesh, source: Field) -> Array:
    """F_i = integral of f phi_i, with the source f(x, y) (W/m^3) evaluated at
    the quadrature points of every triangle."""
    points, weights = quadrature(mesh)
    values = source(points[..., 0], points[..., 1]) * weights
    local = values @ QUADRATURE_POINTS  # the hats are the barycentric coordinates
    out = np.zeros(len(mesh.nodes))
    np.add.at(out, mesh.triangles, local)
    return out


def convection(
    mesh: Mesh, edges: Indices, h: float, ambient: Field
) -> tuple[sparse.csr_matrix, Array]:
    """The convective edges' share of K and F: h times the integral of
    phi_i phi_j along each edge (h L / 6 times [[2, 1], [1, 2]]), and h times
    the integral of g phi_i, with the fluid temperature g(x, y) at two Gauss
    points per edge."""
    n = len(mesh.nodes)
    a, b = mesh.nodes[edges[:, 0]], mesh.nodes[edges[:, 1]]
    length = np.linalg.norm(b - a, axis=1)
    local = (h * length / 6.0)[:, None, None] * np.array([[2.0, 1.0], [1.0, 2.0]])
    rows = np.repeat(edges, 2, axis=1).ravel()
    cols = np.tile(edges, (1, 2)).ravel()
    matrix = sparse.coo_matrix((local.ravel(), (rows, cols)), shape=(n, n)).tocsr()
    return matrix, edge_load(mesh, edges, lambda x, y: h * ambient(x, y))


def edge_load(mesh: Mesh, edges: Indices, flux: Field) -> Array:
    """The integral of g phi_i along the edges, with g(x, y) (W/m^2, or W/m
    per unit depth) at two Gauss points per edge: a heat flux into the domain
    through a part of its boundary."""
    a, b = mesh.nodes[edges[:, 0]], mesh.nodes[edges[:, 1]]
    length = np.linalg.norm(b - a, axis=1)
    vector = np.zeros(len(mesh.nodes))
    for s in _EDGE_POINTS:
        point = (1.0 - s) * a + s * b
        g = flux(point[:, 0], point[:, 1]) * 0.5 * length
        np.add.at(vector, edges[:, 0], g * (1.0 - s))
        np.add.at(vector, edges[:, 1], g * s)
    return vector


def solve(
    matrix: sparse.csr_matrix, vector: Array, fixed: Indices, values: Array
) -> Array:
    """u with u[fixed] = values and (K u - F) = 0 at every other node: the
    fixed nodes are removed from the unknowns and their known values moved to
    the right-hand side, K_ff u_f = F_f - K_fd u_d, solved directly."""
    n = len(vector)
    u = np.zeros(n)
    u[fixed] = values
    free = np.setdiff1d(np.arange(n), fixed)
    rhs = vector[free] - matrix[free][:, fixed] @ u[fixed]
    u[free] = spsolve(matrix[free][:, free].tocsc(), rhs)
    return u


def residual(matrix: sparse.csr_matrix, vector: Array, u: Array) -> Array:
    """K u - F: zero at the free nodes up to round-off, and at a fixed node
    the heat (W, or W/m per unit depth) that flows into the domain there."""
    return matrix @ u - vector


def edge_outflow(
    mesh: Mesh, edges: Indices, u: Array, conductivity: float = 1.0
) -> Array:
    """The heat that leaves through each boundary edge by the gradient of u on
    the triangle the edge belongs to, -k grad u . n times the edge length
    (W/m): the flux read from the gradient, which is constant per triangle
    and first-order accurate."""
    grad = gradients(mesh)
    owner = {}
    for t, tri in enumerate(mesh.triangles):
        for i in range(3):
            owner[(tri[i], tri[(i + 1) % 3])] = t
            owner[(tri[(i + 1) % 3], tri[i])] = t
    triangles = np.array([owner[(a, b)] for a, b in edges])
    grad_u = np.einsum("ti,tia->ta", u[mesh.triangles[triangles]], grad[triangles])
    tangent = mesh.nodes[edges[:, 1]] - mesh.nodes[edges[:, 0]]
    normal_length = np.column_stack([tangent[:, 1], -tangent[:, 0]])  # outward, |n| = L
    return -conductivity * np.einsum("ea,ea->e", grad_u, normal_length)


def errors(
    mesh: Mesh, u: Array, exact: Field, exact_gradient: Callable[[Array, Array], Array]
) -> tuple[float, float]:
    """The L2 norm of u_h - u and the H1 seminorm (the L2 norm of
    grad u_h - grad u) over the mesh, by the degree-four rule on every
    triangle; the exact gradient returns an array with the two components in
    its last axis."""
    points, weights = quadrature(mesh)
    x, y = points[..., 0], points[..., 1]
    u_h = QUADRATURE_POINTS @ u[mesh.triangles].T  # 6 x m
    l2 = np.sum(weights * (u_h.T - exact(x, y)) ** 2)
    grad_h = np.einsum("ti,tia->ta", u[mesh.triangles], gradients(mesh))
    diff = grad_h[:, None, :] - exact_gradient(x, y)
    h1 = np.sum(weights * np.sum(diff**2, axis=-1))
    return float(np.sqrt(l2)), float(np.sqrt(h1))
