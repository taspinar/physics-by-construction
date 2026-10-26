"""The incompressible Navier-Stokes equations in two dimensions (lesson FL2),

    u_t + (u . grad) u = -grad p + nu lap u + f,    div u = 0,

for the velocity u = (u, v) (m/s), the kinematic pressure p (pressure over
density, m^2/s^2), the kinematic viscosity nu (m^2/s), and a body force per
unit mass f (m/s^2), on a periodic rectangle of nx by ny cells.

The grid is staggered, the marker-and-cell (MAC) arrangement: p sits at the
centre of a cell, u on the middle of its left face, v on the middle of its
bottom face. Arrays are indexed ``[j, i]``, row j along y and column i along
x, so ``p[j, i]`` is at ((i + 1/2) dx, (j + 1/2) dy), ``u[j, i]`` at
(i dx, (j + 1/2) dy), and ``v[j, i]`` at ((i + 1/2) dx, j dy). Every
difference is central and of second order, and the discrete divergence of
the discrete gradient is the five-point Laplacian, which the fast Fourier
transform inverts exactly on a periodic grid.

A step is the projection method: the explicit tendency of advection,
diffusion, and force moves the velocity off the divergence-free fields, and
the projection removes the gradient part, u = u* - grad phi with
lap phi = div u*. The time integrator is the three-stage strong-stability-
preserving Runge-Kutta method, with a projection after every stage.
"""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

__all__ = [
    "Forcing",
    "Grid",
    "advection",
    "divergence",
    "gradient",
    "kinetic_energy",
    "laplacian",
    "manufactured",
    "manufactured_forcing",
    "march",
    "pressure",
    "project",
    "solve_poisson",
    "stable_step",
    "step",
    "taylor_green",
    "tendency",
    "viscous_dissipation",
    "vorticity",
]

Array = NDArray[np.float64]
Forcing = Callable[[float], tuple[Array, Array]]
"""A body force per unit mass at the time t, as (f_x at the u points,
f_y at the v points)."""


@dataclass(frozen=True)
class Grid:
    """A periodic rectangle of ``nx`` by ``ny`` cells, ``lx`` by ``ly`` (m)."""

    nx: int
    ny: int
    lx: float = 2.0 * np.pi
    ly: float = 2.0 * np.pi

    @property
    def dx(self) -> float:
        return self.lx / self.nx

    @property
    def dy(self) -> float:
        return self.ly / self.ny

    def points(self, where: str) -> tuple[Array, Array]:
        """The coordinates (x, y), each of shape (ny, nx), of the ``"u"``,
        ``"v"``, ``"p"`` (cell centre), or ``"corner"`` points."""
        shift_x = {"u": 0.0, "v": 0.5, "p": 0.5, "corner": 0.0}[where]
        shift_y = {"u": 0.5, "v": 0.0, "p": 0.5, "corner": 0.0}[where]
        x = (np.arange(self.nx) + shift_x) * self.dx
        y = (np.arange(self.ny) + shift_y) * self.dy
        return np.meshgrid(x, y)


def _left(a: Array) -> Array:
    """The value one cell to the left (i - 1), periodic."""
    return np.roll(a, 1, axis=1)


def _right(a: Array) -> Array:
    return np.roll(a, -1, axis=1)


def _below(a: Array) -> Array:
    return np.roll(a, 1, axis=0)


def _above(a: Array) -> Array:
    return np.roll(a, -1, axis=0)


def divergence(u: Array, v: Array, grid: Grid) -> Array:
    """The divergence u_x + v_y (1/s) at the cell centres: the net outflow
    through the four faces of each cell per unit area."""
    return (_right(u) - u) / grid.dx + (_above(v) - v) / grid.dy


def gradient(p: Array, grid: Grid) -> tuple[Array, Array]:
    """The gradient of a cell-centred ``p``: p_x at the u points and p_y at
    the v points."""
    return (p - _left(p)) / grid.dx, (p - _below(p)) / grid.dy


def laplacian(a: Array, grid: Grid) -> Array:
    """The five-point Laplacian of a field on any of the staggered points."""
    return (_left(a) - 2.0 * a + _right(a)) / grid.dx**2 + (
        _below(a) - 2.0 * a + _above(a)
    ) / grid.dy**2


def advection(u: Array, v: Array, grid: Grid) -> tuple[Array, Array]:
    """The advection (u . grad) u in the divergence form div(u u), at the u
    and the v points.

    The products are formed where their difference is needed: u u and v v at
    the cell centres from the average of the two faces, u v at the corners
    from the average of the two faces on each side. For a velocity whose
    discrete divergence is zero this form moves momentum and kinetic energy
    between cells without creating or destroying either.
    """
    # region: products
    uu = (0.5 * (u + _right(u))) ** 2  # at the centres
    vv = (0.5 * (v + _above(v))) ** 2
    uv = (0.5 * (u + _below(u))) * (0.5 * (v + _left(v)))  # at the corners
    # endregion: products
    adv_u = (uu - _left(uu)) / grid.dx + (_above(uv) - uv) / grid.dy
    adv_v = (_right(uv) - uv) / grid.dx + (vv - _below(vv)) / grid.dy
    return adv_u, adv_v


def _eigenvalues(grid: Grid) -> Array:
    kx = 2.0 * np.pi * np.fft.rfftfreq(grid.nx)
    ky = 2.0 * np.pi * np.fft.fftfreq(grid.ny)
    return (2.0 * np.cos(ky)[:, None] - 2.0) / grid.dy**2 + (
        2.0 * np.cos(kx)[None, :] - 2.0
    ) / grid.dx**2


def solve_poisson(rhs: Array, grid: Grid) -> Array:
    """The cell-centred phi with the five-point Laplacian of phi equal to
    ``rhs`` and mean zero. The periodic problem has a solution only for a
    ``rhs`` of mean zero; its mean is ignored. Exact up to round-off: each
    Fourier mode is an eigenvector of the discrete Laplacian, with the
    eigenvalue (2 cos(k dx) - 2) / dx^2 + (2 cos(l dy) - 2) / dy^2."""
    transformed = np.fft.rfft2(rhs)
    eigenvalues = _eigenvalues(grid)
    eigenvalues[0, 0] = 1.0
    transformed = transformed / eigenvalues
    transformed[0, 0] = 0.0
    return np.fft.irfft2(transformed, s=rhs.shape)


def project(u: Array, v: Array, grid: Grid) -> tuple[Array, Array, Array]:
    """The divergence-free part of (u, v) and the potential phi of the part
    removed: u - grad phi with lap phi = div u. The removed part is a
    gradient and the kept part has no divergence, so the two are orthogonal
    and the projection never adds kinetic energy."""
    phi = solve_poisson(divergence(u, v, grid), grid)
    phi_x, phi_y = gradient(phi, grid)
    return u - phi_x, v - phi_y, phi


def tendency(
    u: Array, v: Array, grid: Grid, nu: float, force: tuple[Array, Array] | None
) -> tuple[Array, Array]:
    """The rate of change of the velocity without the pressure:
    -(u . grad) u + nu lap u + f, at the u and the v points."""
    adv_u, adv_v = advection(u, v, grid)
    du = -adv_u + nu * laplacian(u, grid)
    dv = -adv_v + nu * laplacian(v, grid)
    if force is not None:
        du, dv = du + force[0], dv + force[1]
    return du, dv


def pressure(
    u: Array,
    v: Array,
    grid: Grid,
    nu: float,
    force: tuple[Array, Array] | None = None,
) -> Array:
    """The kinematic pressure (m^2/s^2, mean zero) that keeps a divergence-free
    velocity divergence-free: the solution of lap p = div(-(u . grad) u +
    nu lap u + f). Incompressible flow has no equation of state; the pressure
    is whatever this constraint requires."""
    du, dv = tendency(u, v, grid, nu, force)
    return solve_poisson(divergence(du, dv, grid), grid)


def step(
    u: Array,
    v: Array,
    t: float,
    dt: float,
    grid: Grid,
    nu: float,
    forcing: Forcing | None = None,
    constrain: Callable[[Array, Array, float], tuple[Array, Array]] | None = None,
) -> tuple[Array, Array]:
    """One step of ``dt`` (s) from the time ``t``: three Runge-Kutta stages,
    each an explicit update followed by the projection.

    ``forcing`` gives the body force at a time. ``constrain(u, v, dt)``, if
    given, acts on each stage's velocity before its projection, for a body
    in the flow or a region that relaxes it (lesson FL3).
    """

    def stage(base_u, base_v, from_u, from_v, time, weight):
        force = None if forcing is None else forcing(time)
        du, dv = tendency(from_u, from_v, grid, nu, force)
        new_u = (1 - weight) * base_u + weight * (from_u + dt * du)
        new_v = (1 - weight) * base_v + weight * (from_v + dt * dv)
        if constrain is not None:
            new_u, new_v = constrain(new_u, new_v, weight * dt)
        new_u, new_v, _ = project(new_u, new_v, grid)
        return new_u, new_v

    u1, v1 = stage(u, v, u, v, t, 1.0)
    u2, v2 = stage(u, v, u1, v1, t + dt, 0.25)
    return stage(u, v, u2, v2, t + 0.5 * dt, 2.0 / 3.0)


def march(
    u: Array,
    v: Array,
    grid: Grid,
    nu: float,
    duration: float,
    forcing: Forcing | None = None,
    courant: float = 0.5,
    constrain: Callable[[Array, Array, float], tuple[Array, Array]] | None = None,
    observe: Callable[[float, Array, Array], None] | None = None,
    largest_step: float = np.inf,
) -> tuple[Array, Array, int]:
    """Steps from the time zero to ``duration`` (s), each within
    ``stable_step`` and ``largest_step``, the last one shortened to end on
    ``duration``; ``observe(t, u, v)`` is called after every step. Returns
    the velocity and the number of steps."""
    t, steps = 0.0, 0
    while t < duration:
        dt = min(stable_step(u, v, grid, nu, courant), largest_step, duration - t)
        u, v = step(u, v, t, dt, grid, nu, forcing, constrain)
        t = duration if t + dt >= duration else t + dt
        steps += 1
        if observe is not None:
            observe(t, u, v)
    return u, v, steps


def stable_step(
    u: Array, v: Array, grid: Grid, nu: float, courant: float = 0.5
) -> float:
    """A time step (s) within the two limits of the explicit scheme: the
    flow crosses at most ``courant`` of a cell per step, and the viscous
    number nu dt (1/dx^2 + 1/dy^2) stays below one quarter."""
    speed = max(
        float(np.max(np.abs(u))) / grid.dx + float(np.max(np.abs(v))) / grid.dy,
        1e-12,
    )
    limits = [courant / speed]
    if nu > 0:
        limits.append(0.25 / (nu * (1 / grid.dx**2 + 1 / grid.dy**2)))
    return min(limits)


def kinetic_energy(u: Array, v: Array, grid: Grid) -> float:
    """The kinetic energy per unit mass and depth, the sum over the faces of
    (u^2 + v^2) / 2 times the cell area (m^4/s^2)."""
    return float(0.5 * np.sum(u**2 + v**2) * grid.dx * grid.dy)


def vorticity(u: Array, v: Array, grid: Grid) -> Array:
    """The vorticity v_x - u_y (1/s) at the corners of the cells, where the
    differences of the faces around a corner meet: the circulation around
    the corner's dual cell divided by its area."""
    return (v - _left(v)) / grid.dx - (u - _below(u)) / grid.dy


def viscous_dissipation(u: Array, v: Array, grid: Grid, nu: float) -> float:
    """The rate nu times the sum of the squared differences of u and v, times
    the cell area (m^4/s^3): the kinetic energy that viscosity turns into heat
    per unit time, the exact rate of loss of the semi-discrete scheme."""
    total = 0.0
    for a in (u, v):
        total += np.sum(((_right(a) - a) / grid.dx) ** 2)
        total += np.sum(((_above(a) - a) / grid.dy) ** 2)
    return float(nu * total * grid.dx * grid.dy)


def taylor_green(
    grid: Grid, nu: float, t: float, amplitude: float = 1.0
) -> tuple[Array, Array]:
    """The Taylor-Green vortex on [0, 2 pi)^2 at the time t, an exact
    solution of the equations without force: u = a sin x cos y e^(-2 nu t),
    v = -a cos x sin y e^(-2 nu t), with the pressure that balances its
    advection."""
    decay = amplitude * np.exp(-2.0 * nu * t)
    x, y = grid.points("u")
    u = decay * np.sin(x) * np.cos(y)
    x, y = grid.points("v")
    v = -decay * np.cos(x) * np.sin(y)
    return u, v


# region: manufactured
def _a(t):
    return np.cos(t)


def _b(t):
    return np.sin(t)


def manufactured(grid: Grid, t: float) -> tuple[Array, Array, Array]:
    """The manufactured solution on [0, 2 pi)^2 at the time t, sampled at its
    own points: u = A sin x cos y + B cos y, v = -A cos x sin y, and
    p = A^2 (cos 2x + cos 2y) / 4, with A = cos t and B = sin t. Its
    divergence is zero, and its advection is not a gradient, so the pressure
    alone cannot absorb it."""
    a, b = _a(t), _b(t)
    x, y = grid.points("u")
    u = a * np.sin(x) * np.cos(y) + b * np.cos(y)
    x, y = grid.points("v")
    v = -a * np.cos(x) * np.sin(y)
    x, y = grid.points("p")
    p = 0.25 * a**2 * (np.cos(2 * x) + np.cos(2 * y))
    return u, v, p


def manufactured_forcing(grid: Grid, nu: float) -> Forcing:
    """The body force that makes ``manufactured`` an exact solution:
    f = u_t + (u . grad) u + grad p - nu lap u, worked out by hand,

        f_x = A' sin x cos y + B' cos y + A B cos x + nu (2 A sin x cos y + B cos y),
        f_y = -A' cos x sin y + A B sin x sin y cos y - 2 nu A cos x sin y,

    with A' = -sin t and B' = cos t."""
    xu, yu = grid.points("u")
    xv, yv = grid.points("v")

    def force(t: float) -> tuple[Array, Array]:
        a, b, da, db = _a(t), _b(t), -np.sin(t), np.cos(t)
        fx = (
            da * np.sin(xu) * np.cos(yu)
            + db * np.cos(yu)
            + a * b * np.cos(xu)
            + nu * (2 * a * np.sin(xu) * np.cos(yu) + b * np.cos(yu))
        )
        fy = (
            -da * np.cos(xv) * np.sin(yv)
            + a * b * np.sin(xv) * np.sin(yv) * np.cos(yv)
            - 2 * nu * a * np.cos(xv) * np.sin(yv)
        )
        return fx, fy

    return force


# endregion: manufactured
