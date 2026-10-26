"""Maxwell's equations in time on a grid: the finite-difference time-domain
(FDTD) scheme of Yee.

In one dimension a wave travelling along x with the electric field along z
and the magnetic field along y obeys two of Maxwell's curl equations,

    eps dE_z/dt = dH_y/dx,        mu_0 dH_y/dt = dE_z/dx.

Yee's scheme stores E_z at the nodes x_i = i dx and H_y halfway between
them, and advances the two fields in turn, half a step apart in time; every
derivative is a centred difference. In two dimensions (the TM_z
polarisation) E_z lives at the nodes (i dx, j dx) and H_x, H_y on the edges
between them:

    mu_0 dH_x/dt = -dE_z/dy,  mu_0 dH_y/dt = dE_z/dx,
    eps dE_z/dt = dH_y/dx - dH_x/dy - sigma E_z.

The ends of the line and the walls of the plane are perfect conductors:
E_z = 0 there. A conductivity sigma, set per node, absorbs a wave.

The scheme is stable when the Courant number S = c dt / dx stays below a
limit of the grid, near 1 in one dimension and 1 / sqrt(2) in two, and its
waves travel at the speed its own dispersion relation gives, slightly below
c. Both are in this module, to compare the scheme with.

Quantities are in SI units: lengths in m, times in s, E in V/m, H in A/m,
the conductivity in S/m; the relative permittivity is a pure number.
"""

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import ArrayLike, NDArray

from pbc.electromagnetism.fields import EPSILON_0

Array = NDArray[np.float64]

__all__ = [
    "MU_0",
    "SPEED_OF_LIGHT",
    "Line",
    "Plane",
    "divergence_h",
    "fresnel_reflection",
    "fresnel_transmission",
    "group_velocity",
    "highest_mode_growth",
    "stability_limit",
]

MU_0 = 1.25663706212e-6  # vacuum permeability, N/A^2 (CODATA 2018)
SPEED_OF_LIGHT = 1.0 / np.sqrt(MU_0 * EPSILON_0)  # m/s


@dataclass
class Line:
    """A one-dimensional Yee grid of ``cells`` cells of ``dx`` m between two
    perfectly conducting ends, run at the Courant number ``courant``.

    ``e[i]`` is E_z at x = i dx (``cells + 1`` nodes, the two ends held at
    zero) and ``h[i]`` is H_y at x = (i + 1/2) dx, half a step earlier in time
    (a step advances H first).
    ``permittivity`` is the relative permittivity at each node, or one number
    for all of them.
    """

    cells: int
    dx: float
    courant: float
    permittivity: ArrayLike = 1.0
    e: Array = field(init=False)
    h: Array = field(init=False)

    def __post_init__(self) -> None:
        if self.cells < 2 or self.dx <= 0 or self.courant <= 0:
            raise ValueError("need at least 2 cells, a positive dx and Courant number")
        eps = np.broadcast_to(np.asarray(self.permittivity, dtype=float), self.nodes)
        if np.any(eps < 1.0):
            raise ValueError("a relative permittivity is at least 1")
        self.dt = self.courant * self.dx / SPEED_OF_LIGHT
        self._eps = EPSILON_0 * eps
        self._ce = self.dt / (self._eps * self.dx)
        self._ch = self.dt / (MU_0 * self.dx)
        self.e = np.zeros(self.cells + 1)
        self.h = np.zeros(self.cells)

    @property
    def nodes(self) -> int:
        return self.cells + 1

    @property
    def x(self) -> Array:
        """The positions of the E nodes, m."""
        return self.dx * np.arange(self.nodes)

    def step(self) -> None:
        """Advance H by one step from the curl of E, then E from the curl of H."""
        self.h += self._ch * (self.e[1:] - self.e[:-1])
        self.e[1:-1] += self._ce[1:-1] * (self.h[1:] - self.h[:-1])

    def run(self, steps: int) -> None:
        for _ in range(steps):
            self.step()

    def energy(self) -> Array:
        """The electromagnetic energy per unit area in each cell, J/m^2: the
        electric energy of the node and the magnetic energy of the edge to its
        right (the last node gets no edge)."""
        electric = 0.5 * self._eps * self.e**2 * self.dx
        magnetic = np.zeros(self.nodes)
        magnetic[:-1] = 0.5 * MU_0 * self.h**2 * self.dx
        return electric + magnetic


@dataclass
class Plane:
    """A two-dimensional TM_z Yee grid of ``nx`` by ``ny`` square cells of
    ``dx`` m, inside perfectly conducting walls, at the Courant number
    ``courant``.

    ``ez[i, j]`` is E_z at (i dx, j dx); ``hx[i, j]`` is H_x at
    (i dx, (j + 1/2) dx) and ``hy[i, j]`` is H_y at ((i + 1/2) dx, j dx).
    ``permittivity`` (relative) and ``conductivity`` (S/m) are given at the
    nodes, or as one number each.
    """

    nx: int
    ny: int
    dx: float
    courant: float
    permittivity: ArrayLike = 1.0
    conductivity: ArrayLike = 0.0
    ez: Array = field(init=False)
    hx: Array = field(init=False)
    hy: Array = field(init=False)

    def __post_init__(self) -> None:
        if min(self.nx, self.ny) < 2 or self.dx <= 0 or self.courant <= 0:
            raise ValueError("need 2 cells each way, a positive dx and Courant number")
        shape = (self.nx + 1, self.ny + 1)
        eps = EPSILON_0 * np.broadcast_to(np.asarray(self.permittivity, float), shape)
        sigma = np.broadcast_to(np.asarray(self.conductivity, float), shape)
        if np.any(eps < EPSILON_0) or np.any(sigma < 0):
            raise ValueError("need a relative permittivity >= 1 and sigma >= 0")
        self.dt = self.courant * self.dx / SPEED_OF_LIGHT
        loss = sigma * self.dt / (2.0 * eps)
        # The conduction current is averaged over the step (semi-implicit), so
        # a large sigma damps E instead of making it oscillate.
        self._decay = (1.0 - loss) / (1.0 + loss)
        self._ce = self.dt / (eps * self.dx) / (1.0 + loss)
        self._ch = self.dt / (MU_0 * self.dx)
        self.ez = np.zeros(shape)
        self.hx = np.zeros((self.nx + 1, self.ny))
        self.hy = np.zeros((self.nx, self.ny + 1))

    def step(self, source: Array | None = None) -> None:
        """Advance H, then E; ``source``, if given, is added to E_z at every
        interior node after the update (a soft source, in V/m per step)."""
        self.hx -= self._ch * np.diff(self.ez, axis=1)
        self.hy += self._ch * np.diff(self.ez, axis=0)
        curl = np.diff(self.hy, axis=0)[:, 1:-1] - np.diff(self.hx, axis=1)[1:-1, :]
        inner = (slice(1, -1), slice(1, -1))
        self.ez[inner] = self._decay[inner] * self.ez[inner] + self._ce[inner] * curl
        if source is not None:
            self.ez[inner] += source[inner]

    def run(self, steps: int) -> None:
        for _ in range(steps):
            self.step()


def divergence_h(plane: Plane) -> Array:
    """The discrete divergence of H at the cell centres, A/m^2."""
    return (np.diff(plane.hx, axis=0) + np.diff(plane.hy, axis=1)) / plane.dx


def group_velocity(
    k: ArrayLike, dx: float, courant: float, refractive_index: float = 1.0
) -> Array:
    """The group velocity, m/s, of a wave of wavenumber ``k`` (rad/m) on the
    one-dimensional Yee grid, from its dispersion relation

        sin(omega dt / 2) = S sin(k dx / 2),   S = (c / n) dt / dx,

    which gives d omega / dk = (c / n) cos(k dx / 2) / sqrt(1 - S^2 sin^2(k dx / 2)).
    ``courant`` is the Courant number of the vacuum, c dt / dx."""
    local = courant / refractive_index
    half = 0.5 * np.asarray(k, dtype=float) * dx
    speed = SPEED_OF_LIGHT / refractive_index
    return speed * np.cos(half) / np.sqrt(1.0 - (local * np.sin(half)) ** 2)


def stability_limit(cells: int, dimensions: int) -> float:
    """The largest stable Courant number of a grid of ``cells`` cells per
    direction between perfectly conducting walls, in ``dimensions`` (1 or 2).

    The highest mode of the grid alternates in sign from node to node; its
    second difference is -4 cos^2(pi / (2 cells)) / dx^2 per direction, and
    the leapfrog in time stays bounded while S^2 times the sum of these over
    the directions, times dx^2 / 4, is at most one."""
    if dimensions not in (1, 2):
        raise ValueError("one or two dimensions")
    return 1.0 / (np.sqrt(dimensions) * np.cos(np.pi / (2 * cells)))


def highest_mode_growth(courant: float, cells: int, dimensions: int) -> float:
    """The factor by which the highest mode grows per step beyond the
    stability limit: with a = S / S_max > 1 the leapfrog's multipliers solve
    g^2 - (2 - 4 a^2) g + 1 = 0, and the larger one in size is
    2 a^2 - 1 + 2 a sqrt(a^2 - 1). One below the limit."""
    a = courant / stability_limit(cells, dimensions)
    if a <= 1.0:
        return 1.0
    return float(2.0 * a**2 - 1.0 + 2.0 * a * np.sqrt(a**2 - 1.0))


def fresnel_reflection(n1: float, n2: float) -> float:
    """The ratio of the reflected to the incident electric field at normal
    incidence from a medium of index ``n1`` onto one of ``n2``."""
    return (n1 - n2) / (n1 + n2)


def fresnel_transmission(n1: float, n2: float) -> float:
    """The ratio of the transmitted to the incident electric field at normal
    incidence from ``n1`` onto ``n2``."""
    return 2.0 * n1 / (n1 + n2)
