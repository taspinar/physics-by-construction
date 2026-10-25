"""Heat conduction: lumped cooling and the heat equation by finite differences.

A solid of conductivity k (W/(m K)), density rho (kg/m^3), and specific heat
c (J/(kg K)) conducts heat by Fourier's law, q = -k grad T (W/m^2), and stores
it as rho c T, so its temperature T (K) obeys the heat equation

    dT/dt = alpha laplacian(T),   alpha = k / (rho c)   (m^2/s).

The explicit (forward-time, centred-space, FTCS) scheme advances the values
at the nodes of a grid of spacing dx by the step dt; its one number is
r = alpha dt / dx^2. A boundary either holds a fixed temperature or loses
heat to a fluid by convection, -k dT/dn = h (T - T_fluid), with the heat
transfer coefficient h (W/(m^2 K)); the convective boundary uses a ghost node
outside the grid, which keeps the scheme second order in dx and makes the
energy of the grid change by exactly the heat that leaves through the ends.

The lumped model replaces the solid by one temperature; the exact series of
a slab cooled on both faces, and the steady five-point plate solved as one
sparse linear system, are the references the lesson checks against.
"""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy import sparse
from scipy.optimize import brentq
from scipy.sparse.linalg import spsolve

Array = NDArray[np.float64]


@dataclass(frozen=True)
class Material:
    """A solid: conductivity ``k`` (W/(m K)), density ``rho`` (kg/m^3), and
    specific heat ``c`` (J/(kg K))."""

    k: float
    rho: float
    c: float

    @property
    def diffusivity(self) -> float:
        """alpha = k / (rho c) (m^2/s)."""
        return self.k / (self.rho * self.c)


@dataclass(frozen=True)
class Fixed:
    """A boundary held at ``temperature`` (K)."""

    temperature: float


@dataclass(frozen=True)
class Convective:
    """A boundary that loses heat to a fluid at ``ambient`` (K) with the heat
    transfer coefficient ``h`` (W/(m^2 K))."""

    h: float
    ambient: float


Boundary = Fixed | Convective


def biot_number(h: float, length: float, k: float) -> float:
    """Bi = h L / k: the resistance to conduction over L against the
    resistance to convection at the surface."""
    return h * length / k


def lumped_temperature(
    t: Array, initial: float, ambient: float, time_constant: float
) -> Array:
    """Newton cooling of one lumped temperature:
    T(t) = T_fluid + (T_0 - T_fluid) exp(-t / tau)."""
    return ambient + (initial - ambient) * np.exp(-np.asarray(t) / time_constant)


def lumped_time_constant(material: Material, half_thickness: float, h: float) -> float:
    """tau = rho c V / (h A) of a slab of thickness 2 L cooled on both faces:
    V / A = L per unit area of face (s)."""
    return material.rho * material.c * half_thickness / h


def _boundary_value(
    end: Boundary, inside: float, edge: float, r: float, dx: float, k: float
) -> float:
    """The new value of an end node from its value ``edge`` and its neighbour
    ``inside``: the fixed temperature, or the FTCS update with the ghost node
    T_ghost = T_inside - 2 dx (h / k) (T_edge - T_fluid)."""
    if isinstance(end, Fixed):
        return end.temperature
    ghost = inside - 2.0 * dx * end.h / k * (edge - end.ambient)
    return edge + r * (inside - 2.0 * edge + ghost)


def ftcs_step(
    temperature: Array,
    r: float,
    dx: float,
    k: float,
    left: Boundary,
    right: Boundary,
) -> Array:
    """One explicit step of the 1D heat equation on the nodes x_0 ... x_N,
    which include both ends: T_i + r (T_(i+1) - 2 T_i + T_(i-1))."""
    t = temperature
    new = np.empty_like(t)
    new[1:-1] = t[1:-1] + r * (t[2:] - 2.0 * t[1:-1] + t[:-2])
    new[0] = _boundary_value(left, t[1], t[0], r, dx, k)
    new[-1] = _boundary_value(right, t[-2], t[-1], r, dx, k)
    return new


def ftcs_step_2d(temperature: Array, r: float) -> Array:
    """One explicit step of the 2D heat equation on a square grid of spacing
    dx in both directions, with the boundary rows and columns held fixed:
    T + r (sum of the four neighbours - 4 T)."""
    t = temperature
    new = t.copy()
    new[1:-1, 1:-1] = t[1:-1, 1:-1] + r * (
        t[2:, 1:-1] + t[:-2, 1:-1] + t[1:-1, 2:] + t[1:-1, :-2] - 4.0 * t[1:-1, 1:-1]
    )
    return new


def positive_step_limit(dx: float, k: float, ends: tuple[Boundary, ...]) -> float:
    """The largest r for which every new value of the 1D scheme is a weighted
    mean of old values (all weights non-negative): 1/2 in the interior, and
    1 / (2 (1 + h dx / k)) at a convective end."""
    biot = max(
        (end.h * dx / k for end in ends if isinstance(end, Convective)), default=0.0
    )
    return 0.5 / (1.0 + biot)


def march(
    temperature: Array,
    steps: int,
    step: Callable[[Array], Array],
) -> Array:
    """``steps`` applications of ``step``, from ``temperature``; returns the
    states at every step, the initial one first."""
    states = [np.asarray(temperature, dtype=float)]
    for _ in range(steps):
        states.append(step(states[-1]))
    return np.array(states)


def grid_energy(temperature: Array, dx: float, material: Material) -> float:
    """rho c times the integral of T over the 1D grid by the trapezoidal rule
    (J/m^2, per unit area of the faces): the energy the FTCS scheme with
    ghost-node boundaries conserves exactly."""
    weights = np.full(temperature.shape[-1], dx)
    weights[[0, -1]] = 0.5 * dx
    return float(material.rho * material.c * temperature @ weights)


def convective_loss(
    temperature: Array, dt: float, ends: tuple[Boundary, Boundary]
) -> float:
    """The heat (J/m^2) that leaves through the two ends during the explicit
    steps whose start states are ``temperature`` (one row per step):
    dt times the sum over steps of h (T_end - T_fluid)."""
    loss = 0.0
    for column, end in zip((0, -1), ends, strict=True):
        if isinstance(end, Convective):
            loss += dt * end.h * float(np.sum(temperature[:, column] - end.ambient))
    return loss


def growth_per_step(step: Callable[[Array], Array], state: Array, steps: int) -> float:
    """The factor by which a linear step multiplies the largest component of
    a state in the long run, measured by applying it ``steps`` times and
    normalising after each (power iteration): above one the scheme grows
    without bound, below one every state decays."""
    x = np.asarray(state, dtype=float)
    x = x / np.linalg.norm(x)
    growth = 0.0
    for _ in range(steps):
        x = step(x)
        growth = float(np.linalg.norm(x))
        x = x / growth
    return growth


def stability_limit(
    growth: Callable[[float], float], low: float, high: float, tolerance: float
) -> float:
    """The r at which the measured ``growth(r)`` crosses one, by bisection
    between a stable ``low`` and an unstable ``high``."""
    if not growth(low) < 1.0 < growth(high):
        raise ValueError("low must be stable and high unstable")
    while high - low > tolerance:
        middle = 0.5 * (low + high)
        if growth(middle) > 1.0:
            high = middle
        else:
            low = middle
    return 0.5 * (low + high)


def discrete_stability_limit(interior_points: int, dimension: int) -> float:
    """The exact limit of FTCS with fixed ends on ``interior_points`` unknowns
    per direction: the highest mode is multiplied by
    1 - 4 d r cos^2(pi / (2 (N + 1))) per step, which reaches -1 at
    r = 1 / (2 d cos^2(pi / (2 (N + 1)))); 1 / (2 d) as N grows."""
    return 1.0 / (2.0 * dimension * np.cos(np.pi / (2 * (interior_points + 1))) ** 2)


def slab_eigenvalues(biot: float, terms: int) -> Array:
    """The first ``terms`` roots of lambda tan lambda = Bi, one in each
    interval (n pi, n pi + pi / 2)."""

    def f(lam: float) -> float:
        return lam * np.sin(lam) - biot * np.cos(lam)

    return np.array(
        [brentq(f, n * np.pi, n * np.pi + 0.5 * np.pi) for n in range(terms)]
    )


def slab_temperature(x: Array, fourier: float, biot: float, terms: int = 200) -> Array:
    """The exact dimensionless temperature (T - T_fluid) / (T_0 - T_fluid) of a
    slab of half-thickness L, started uniform and cooled by convection on
    both faces, at x / L from its centre (-1 to 1) and the Fourier number
    Fo = alpha t / L^2: the sum of C_n exp(-lambda_n^2 Fo) cos(lambda_n x / L)
    with C_n = 4 sin(lambda_n) / (2 lambda_n + sin(2 lambda_n))."""
    lam = slab_eigenvalues(biot, terms)
    c = 4.0 * np.sin(lam) / (2.0 * lam + np.sin(2.0 * lam))
    x = np.asarray(x, dtype=float)
    return np.cos(np.multiply.outer(x, lam)) @ (c * np.exp(-(lam**2) * fourier))


def slab_mean_temperature(fourier: Array, biot: float, terms: int = 200) -> Array:
    """The exact mean of ``slab_temperature`` over the slab:
    the sum of C_n exp(-lambda_n^2 Fo) sin(lambda_n) / lambda_n."""
    lam = slab_eigenvalues(biot, terms)
    c = 4.0 * np.sin(lam) / (2.0 * lam + np.sin(2.0 * lam))
    fo = np.asarray(fourier, dtype=float)
    return np.exp(-np.multiply.outer(fo, lam**2)) @ (c * np.sin(lam) / lam)


def steady_plate(boundary: Array, source: Array, dx: float, k: float) -> Array:
    """The steady temperature of a square plate, k laplacian(T) + q = 0, by
    the five-point stencil: ``boundary`` gives the fixed values on its outer
    rows and columns, ``source`` the heat generated q (W/m^3) at every node.
    The interior unknowns form one sparse linear system,
    (4 T_ij - sum of the neighbours) / dx^2 = q_ij / k, solved directly."""
    grid = np.array(boundary, dtype=float)
    n = grid.shape[0] - 2
    one_d = sparse.diags([-1.0, 2.0, -1.0], [-1, 0, 1], shape=(n, n))
    eye = sparse.identity(n)
    matrix = (sparse.kron(eye, one_d) + sparse.kron(one_d, eye)).tocsc()
    rhs = np.asarray(source, dtype=float)[1:-1, 1:-1] * dx**2 / k
    rhs[0, :] += grid[0, 1:-1]
    rhs[-1, :] += grid[-1, 1:-1]
    rhs[:, 0] += grid[1:-1, 0]
    rhs[:, -1] += grid[1:-1, -1]
    grid[1:-1, 1:-1] = spsolve(matrix, rhs.ravel()).reshape(n, n)
    return grid
