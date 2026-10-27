"""Smoothed particle hydrodynamics in two dimensions (lesson FL6).

A fluid is a set of particles of fixed mass m that move with the flow. A
field is read from the particles with a kernel W of width h: the density at
a particle is the sum of m W over its neighbours, and a derivative is a sum
of m times the gradient of W. Nothing is on a grid, so a free surface needs
no treatment: where there are no particles, there is no fluid.

The particles here are a weakly compressible liquid, the pressure
P = c0^2 (rho - rho0) with a speed of sound c0 well above the speeds of the
flow, so that the density changes by about the square of their ratio. The
density of each particle follows the continuity equation,

    d rho_i / dt = sum_j m (v_i - v_j) . grad_i W_ij,

and its acceleration the symmetric pressure force,

    d v_i / dt = -sum_j m (P_i / rho_i^2 + P_j / rho_j^2 + Pi_ij) grad_i W_ij,

where Pi_ij is Monaghan's artificial viscosity, zero unless asked for, which
acts only between particles that approach each other and turns the kinetic
energy it removes into heat.

Every pair pushes its two particles with equal and opposite forces along the
line between them, so the equations conserve the momentum and the angular
momentum; and the work of the pressure on the motion is the rate of change
of the internal energy e(rho) = c0^2 (ln(rho / rho0) + rho0 / rho - 1), so
the equations also conserve the total energy. A time step keeps the
momentum to round-off and changes the other two by an amount that falls
with the step. Positions in m, velocities in m/s, densities in kg/m^2 (per
unit depth).
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.spatial import cKDTree

__all__ = [
    "Particles",
    "accelerations",
    "angular_momentum",
    "density_sum",
    "drop_pressure",
    "ellipse_moments",
    "elliptical_drop",
    "energy",
    "gradient_difference",
    "gradient_sum",
    "internal_energy",
    "kernel",
    "kernel_derivative",
    "lattice_disc",
    "momentum",
    "pairs",
    "pressure",
    "step",
]

Array = NDArray[np.float64]


@dataclass(frozen=True)
class Particles:
    """The state of the particles: positions and velocities of shape (n, 2),
    densities of shape (n,), the one mass of every particle (kg per m of
    depth), and the heat per unit mass that the artificial viscosity has
    deposited in each (J/kg; ``None`` before the first step)."""

    x: Array
    v: Array
    rho: Array
    mass: float
    heat: Array | None = None


# region: kernel
def kernel(r: Array, h: float) -> Array:
    """The cubic spline kernel of Monaghan in two dimensions (1/m^2): a bell
    of width h that is zero beyond 2h and integrates to one over the plane."""
    q = np.asarray(r, dtype=float) / h
    sigma = 10.0 / (7.0 * np.pi * h**2)
    inner = 1.0 - 1.5 * q**2 + 0.75 * q**3
    outer = 0.25 * (2.0 - q) ** 3
    return sigma * np.where(q < 1.0, inner, np.where(q < 2.0, outer, 0.0))


def kernel_derivative(r: Array, h: float) -> Array:
    """The derivative dW/dr of the cubic spline kernel (1/m^3)."""
    q = np.asarray(r, dtype=float) / h
    sigma = 10.0 / (7.0 * np.pi * h**2)
    inner = -3.0 * q + 2.25 * q**2
    outer = -0.75 * (2.0 - q) ** 2
    return sigma / h * np.where(q < 1.0, inner, np.where(q < 2.0, outer, 0.0))


# endregion: kernel


def pairs(x: Array, h: float) -> tuple[NDArray[np.intp], NDArray[np.intp]]:
    """The indices (i, j), i < j, of every pair of particles closer than the
    kernel's reach 2h, found with a k-d tree."""
    found = cKDTree(x).query_pairs(2.0 * h, output_type="ndarray")
    return found[:, 0], found[:, 1]


def _pair_geometry(x: Array, i, j, h: float) -> tuple[Array, Array]:
    """The separation x_i - x_j of each pair and grad_i W_ij."""
    d = x[i] - x[j]
    r = np.sqrt(np.sum(d**2, axis=1))
    with np.errstate(invalid="ignore", divide="ignore"):
        scale = np.where(r > 0, kernel_derivative(r, h) / r, 0.0)
    return d, d * scale[:, None]


def density_sum(x: Array, mass: float, h: float) -> Array:
    """The density by summation, rho_i = sum_j m W(|x_i - x_j|), the particle
    itself included."""
    i, j = pairs(x, h)
    d = x[i] - x[j]
    w = kernel(np.sqrt(np.sum(d**2, axis=1)), h)
    rho = np.full(len(x), mass * float(kernel(np.array(0.0), h)))
    np.add.at(rho, i, mass * w)
    np.add.at(rho, j, mass * w)
    return rho


def gradient_sum(x: Array, f: Array, volume: Array, h: float) -> Array:
    """The plain particle estimate of the gradient of f,
    sum_j V_j f_j grad_i W_ij, with V_j = m / rho_j the volume of a particle.
    It is the integral of f grad W with the integral replaced by a sum, and
    it is exact only where the particles sample that integral exactly."""
    i, j = pairs(x, h)
    _, grad = _pair_geometry(x, i, j, h)
    out = np.zeros_like(x)
    np.add.at(out, i, (volume[j] * f[j])[:, None] * grad)
    np.add.at(out, j, -(volume[i] * f[i])[:, None] * grad)
    return out


def gradient_difference(x: Array, f: Array, volume: Array, h: float) -> Array:
    """The difference estimate sum_j V_j (f_j - f_i) grad_i W_ij: the plain
    estimate minus f_i times the estimate of the gradient of one. It is
    exact for a constant f on any arrangement of particles."""
    i, j = pairs(x, h)
    _, grad = _pair_geometry(x, i, j, h)
    diff = (f[j] - f[i])[:, None] * grad
    out = np.zeros_like(x)
    np.add.at(out, i, volume[j][:, None] * diff)
    np.add.at(out, j, volume[i][:, None] * diff)
    return out


def pressure(rho: Array, rho0: float, c0: float) -> Array:
    """The weakly compressible equation of state P = c0^2 (rho - rho0)
    (Pa m: per unit depth)."""
    return c0**2 * (rho - rho0)


def internal_energy(rho: Array, rho0: float, c0: float) -> Array:
    """The internal energy per unit mass that the pressure stores, the
    integral of P / rho^2 from rho0 to rho (J/kg)."""
    return c0**2 * (np.log(rho / rho0) + rho0 / rho - 1.0)


def accelerations(
    state: Particles,
    h: float,
    rho0: float,
    c0: float,
    viscosity: float = 0.0,
) -> tuple[Array, Array, Array]:
    """The acceleration of every particle, the rate of change of its density,
    and the rate at which the artificial viscosity heats it (W/kg), from the
    pairs within reach."""
    # region: forces
    i, j = pairs(state.x, h)
    d, grad = _pair_geometry(state.x, i, j, h)
    p = pressure(state.rho, rho0, c0)
    dv_ij = state.v[i] - state.v[j]
    approach = np.sum(dv_ij * d, axis=1)
    mu = h * np.minimum(approach, 0.0) / (np.sum(d**2, axis=1) + 0.01 * h**2)
    damping = -viscosity * c0 * mu / (0.5 * (state.rho[i] + state.rho[j]))
    weight = state.mass * (
        p[i] / state.rho[i] ** 2 + p[j] / state.rho[j] ** 2 + damping
    )
    force = -weight[:, None] * grad  # on i from j; j gets the opposite
    dv = np.zeros_like(state.x)
    np.add.at(dv, i, force)
    np.add.at(dv, j, -force)
    flux = state.mass * np.sum(dv_ij * grad, axis=1)
    drho = np.zeros_like(state.rho)
    np.add.at(drho, i, flux)
    np.add.at(drho, j, flux)
    heating = 0.5 * state.mass * damping * np.sum(dv_ij * grad, axis=1)
    dq = np.zeros_like(state.rho)
    np.add.at(dq, i, heating)
    np.add.at(dq, j, heating)
    # endregion: forces
    return dv, drho, dq


def step(
    state: Particles,
    dt: float,
    h: float,
    rho0: float,
    c0: float,
    viscosity: float = 0.0,
) -> Particles:
    """One step of ``dt`` (s) of the midpoint method: the rates at the start
    carry every variable half a step, and the rates there carry the state
    the whole step. Second order in ``dt`` for the positions, velocities,
    densities, and heat together."""

    def advance(s: Particles, rates, by: float) -> Particles:
        dv, drho, dq = rates
        heat = np.zeros_like(state.rho) if state.heat is None else state.heat
        return Particles(
            x=state.x + by * s.v,
            v=state.v + by * dv,
            rho=state.rho + by * drho,
            mass=state.mass,
            heat=heat + by * dq,
        )

    middle = advance(state, accelerations(state, h, rho0, c0, viscosity), 0.5 * dt)
    return advance(middle, accelerations(middle, h, rho0, c0, viscosity), dt)


def momentum(state: Particles) -> Array:
    """The total momentum, sum of m v (kg/s per m of depth)."""
    return state.mass * np.sum(state.v, axis=0)


def angular_momentum(state: Particles) -> float:
    """The total angular momentum about the origin, sum of m (x v_y - y v_x)."""
    x, v = state.x, state.v
    return float(state.mass * np.sum(x[:, 0] * v[:, 1] - x[:, 1] * v[:, 0]))


def energy(state: Particles, rho0: float, c0: float) -> float:
    """The kinetic plus the internal energy of the particles (J per m of
    depth), the quantity the equations conserve without gravity."""
    kinetic = 0.5 * np.sum(state.v**2)
    internal = np.sum(internal_energy(state.rho, rho0, c0))
    heat = 0.0 if state.heat is None else np.sum(state.heat)
    return float(state.mass * (kinetic + internal + heat))


def lattice_disc(radius: float, spacing: float) -> Array:
    """The points of a square lattice of the given spacing inside a circle of
    the given radius centred on the origin, offset by half a spacing."""
    n = int(np.ceil(radius / spacing)) + 1
    axis = (np.arange(-n, n) + 0.5) * spacing
    x, y = np.meshgrid(axis, axis)
    points = np.column_stack([x.ravel(), y.ravel()])
    return points[np.sum(points**2, axis=1) < radius**2]


def elliptical_drop(
    t: Array, stretch: float, radius: float = 1.0
) -> tuple[Array, Array, Array]:
    """The semi-axes a(t) along x and b(t) along y, and the rate A(t), of a
    drop of inviscid
    incompressible liquid that starts as a circle of the given radius with the
    velocity (A x, -A y), A(0) = ``stretch`` (1/s), with no pressure at its
    surface. The flow stays linear, (A x, -A y), the drop stays an ellipse
    of area pi radius^2, and

        dA/dt = A^2 (b^2 - a^2) / (a^2 + b^2),    da/dt = A a,    a b = radius^2,

    integrated here by the classical fourth-order Runge-Kutta method on a fine
    step and read at the increasing times ``t``. The pressure inside is
    P0 (1 - x^2 / a^2 - y^2 / b^2), with P0 = rho a^2 A^2 b^2 / (a^2 + b^2)
    (``drop_pressure``)."""
    t = np.asarray(t, dtype=float)

    def rate(state):
        a, big_a = state
        b = radius**2 / a
        return np.array([big_a * a, big_a**2 * (b**2 - a**2) / (a**2 + b**2)])

    out = np.empty((len(t), 2))
    state, now = np.array([radius, stretch]), 0.0
    for k, target in enumerate(t):
        n = max(int(np.ceil((target - now) / 1e-4)), 1)
        dt = (target - now) / n
        for _ in range(n):
            k1 = rate(state)
            k2 = rate(state + 0.5 * dt * k1)
            k3 = rate(state + 0.5 * dt * k2)
            k4 = rate(state + dt * k3)
            state = state + dt / 6.0 * (k1 + 2 * k2 + 2 * k3 + k4)
        now = target
        out[k] = state
    return out[:, 0], radius**2 / out[:, 0], out[:, 1]


def drop_pressure(a: float, b: float, rate: float, rho: float) -> float:
    """The pressure P0 at the centre of the elliptical drop (Pa m), from the
    momentum balance along x at its semi-axes a, b and rate A:
    (A' + A^2) a^2 = 2 P0 / rho, with A' = A^2 (b^2 - a^2) / (a^2 + b^2)."""
    return rho * a**2 * rate**2 * b**2 / (a**2 + b**2)


def ellipse_moments(x: Array) -> tuple[float, float]:
    """The semi-axes along x and y of the uniform ellipse with the same second
    moments as the particles about their centre: a = 2 sqrt(<x^2>)."""
    centred = x - np.mean(x, axis=0)
    return float(2.0 * np.sqrt(np.mean(centred[:, 0] ** 2))), float(
        2.0 * np.sqrt(np.mean(centred[:, 1] ** 2))
    )
