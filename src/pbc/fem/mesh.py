"""Triangular meshes: generation, boundary edges, and quality.

A mesh is an array of node coordinates (m) and an array of triangles, three
node indices each, counter-clockwise. Its boundary is a set of named groups
of edges, two node indices each, so that a boundary condition can be put on
a part of the boundary by name.

Two generators cover the lessons: a rectangle of split squares, every
diagonal in the same direction, and an annulus of rings of nodes joined by a
Delaunay triangulation (``scipy.spatial.Delaunay``) with the triangles of
the hole removed. The quality of a triangle is measured by its smallest
angle and its radius ratio 2 r_in / r_out, which is one for an equilateral
triangle and falls to zero as the triangle flattens.
"""

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray
from scipy.spatial import Delaunay

Array = NDArray[np.float64]
Indices = NDArray[np.int64]


@dataclass(frozen=True)
class Mesh:
    """Nodes (n x 2, m), triangles (m x 3, counter-clockwise), and the named
    groups of boundary edges (e x 2 each)."""

    nodes: Array
    triangles: Indices
    boundary: dict[str, Indices] = field(default_factory=dict)

    def boundary_nodes(self, *names: str) -> Indices:
        """The nodes on the named boundary groups, each once, sorted."""
        return np.unique(np.concatenate([self.boundary[name] for name in names]))


def areas(mesh: Mesh) -> Array:
    """The signed area of every triangle (m^2): positive when its nodes run
    counter-clockwise."""
    p = mesh.nodes[mesh.triangles]
    d1, d2 = p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]
    return 0.5 * (d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0])


def edge_lengths(mesh: Mesh) -> Array:
    """The lengths of the three sides of every triangle (m x 3, m); side i is
    opposite node i."""
    p = mesh.nodes[mesh.triangles]
    return np.stack(
        [
            np.linalg.norm(p[:, (i + 2) % 3] - p[:, (i + 1) % 3], axis=1)
            for i in range(3)
        ],
        axis=1,
    )


def size(mesh: Mesh) -> float:
    """h, the longest side of any triangle (m)."""
    return float(edge_lengths(mesh).max())


def angles(mesh: Mesh) -> Array:
    """The three angles of every triangle (m x 3, degrees), angle i at node i,
    by the law of cosines."""
    s = edge_lengths(mesh)
    out = np.empty_like(s)
    for i in range(3):
        a, b, c = s[:, i], s[:, (i + 1) % 3], s[:, (i + 2) % 3]
        out[:, i] = np.degrees(
            np.arccos(np.clip((b**2 + c**2 - a**2) / (2 * b * c), -1, 1))
        )
    return out


def radius_ratio(mesh: Mesh) -> Array:
    """2 r_in / r_out of every triangle: one for an equilateral triangle, zero
    for a flat one. r_in = A / s with s the half perimeter, r_out = abc / (4 A)."""
    s = edge_lengths(mesh)
    area = np.abs(areas(mesh))
    r_in = area / (0.5 * s.sum(axis=1))
    r_out = s.prod(axis=1) / (4.0 * area)
    return 2.0 * r_in / r_out


def boundary_edges(triangles: Indices) -> Indices:
    """The edges that belong to one triangle only, in the direction they run
    around their triangle (so the domain lies on their left)."""
    edges = np.concatenate(
        [triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]]
    )
    key = np.sort(edges, axis=1)
    _, inverse, counts = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    return edges[counts[inverse.ravel()] == 1]


def rectangle(width: float, height: float, nx: int, ny: int) -> Mesh:
    """A rectangle [0, width] x [0, height] of nx x ny cells, each split into
    two triangles along the diagonal from its lower-left to its upper-right
    corner. Boundary groups: bottom, right, top, left."""
    x = np.linspace(0.0, width, nx + 1)
    y = np.linspace(0.0, height, ny + 1)
    xx, yy = np.meshgrid(x, y)
    nodes = np.column_stack([xx.ravel(), yy.ravel()])
    index = np.arange((nx + 1) * (ny + 1)).reshape(ny + 1, nx + 1)
    a, b = index[:-1, :-1].ravel(), index[:-1, 1:].ravel()
    c, d = index[1:, 1:].ravel(), index[1:, :-1].ravel()
    triangles = np.concatenate([np.column_stack([a, b, c]), np.column_stack([a, c, d])])
    boundary = {
        "bottom": np.column_stack([index[0, :-1], index[0, 1:]]),
        "right": np.column_stack([index[:-1, -1], index[1:, -1]]),
        "top": np.column_stack([index[-1, 1:], index[-1, :-1]]),
        "left": np.column_stack([index[1:, 0], index[:-1, 0]]),
    }
    return Mesh(nodes, triangles, boundary)


def annulus(inner: float, outer: float, layers: int, graded: bool = False) -> Mesh:
    """An annulus between the radii ``inner`` and ``outer`` (m): ``layers + 1``
    rings of nodes, each with as many nodes as make its spacing along the ring
    equal to the spacing between rings, and every other ring turned by half a
    spacing; the nodes are triangulated by Delaunay and the triangles whose
    centroid lies in the hole are removed. The rings are evenly spaced in
    radius, or, ``graded``, in the logarithm of the radius, so that the
    triangles grow in proportion to their distance from the centre: fine at a
    thin inner ring, where a temperature that falls as ln(r) changes fastest.
    Boundary groups: inner, outer."""
    if graded:
        radii = np.geomspace(inner, outer, layers + 1)
        spacings = radii * np.log(outer / inner) / layers
    else:
        radii = np.linspace(inner, outer, layers + 1)
        spacings = np.full(layers + 1, (outer - inner) / layers)
    rings = []
    for j, (radius, spacing) in enumerate(zip(radii, spacings, strict=True)):
        count = max(6, round(2.0 * np.pi * radius / spacing))
        phase = 0.5 * (j % 2) * 2.0 * np.pi / count
        theta = phase + 2.0 * np.pi * np.arange(count) / count
        rings.append(radius * np.column_stack([np.cos(theta), np.sin(theta)]))
    nodes = np.concatenate(rings)
    triangles = Delaunay(nodes).simplices.astype(np.int64)
    centroids = nodes[triangles].mean(axis=1)
    triangles = triangles[np.hypot(*centroids.T) > inner]
    mesh = Mesh(nodes, triangles)
    flipped = areas(mesh) < 0
    triangles[flipped] = triangles[flipped][:, [0, 2, 1]]
    edges = boundary_edges(triangles)
    middle = np.hypot(*nodes[edges].mean(axis=1).T)
    radius = 0.5 * (inner + outer)
    boundary = {"inner": edges[middle < radius], "outer": edges[middle > radius]}
    return Mesh(nodes, triangles, boundary)
