"""Drag: the force of a fluid on a body that moves through it, in the two
models the mechanics course uses.

- Linear drag, F = -b v, holds for small bodies at low speed, when the flow
  around the body is smooth (Reynolds number below about 1): a fog droplet
  in air, a bead sinking in oil. Falling under it has a closed-form
  solution, given here as the reference for the simulation.
- Quadratic drag, F = -c |v| v, holds for everyday bodies at everyday
  speeds, when the body leaves a turbulent wake (Reynolds number from about
  1000 to 100 000): a thrown ball, a cyclist, a raindrop. Motion under it has
  no closed form.

Both forces point against the velocity. ``b`` is in kg/s and ``c`` in kg/m;
the other quantities are in SI units as in ``pbc.mechanics.dynamics``.
"""

import numpy as np
from numpy.typing import ArrayLike

from pbc.mechanics.dynamics import Force, State, Trajectory, Vector


def linear_drag(b: float) -> Force:
    """The linear drag force -b v, with the drag constant ``b`` in kg/s.

    For a sphere of radius r in a fluid of viscosity eta, Stokes' law gives
    b = 6 pi eta r.
    """
    if b < 0:
        raise ValueError(f"the drag constant must not be negative, got {b}")

    def drag(t: float, x: Vector, v: Vector) -> Vector:
        return -b * v

    return drag


def quadratic_drag(c: float) -> Force:
    """The quadratic drag force -c |v| v, with the drag constant ``c`` in kg/m.

    ``c`` is 0 for no drag. For a body of cross-section area A in a fluid of
    density rho, c = rho C_d A / 2 with the dimensionless drag coefficient
    C_d of its shape; see ``drag_constant``.
    """
    if c < 0:
        raise ValueError(f"the drag constant must not be negative, got {c}")

    def drag(t: float, x: Vector, v: Vector) -> Vector:
        return -c * np.sqrt(v @ v) * v

    return drag


def drag_constant(density: float, drag_coefficient: float, area: float) -> float:
    """The constant c = rho C_d A / 2 of quadratic drag, in kg/m.

    ``density`` is that of the fluid in kg/m³, ``drag_coefficient`` the
    dimensionless C_d of the body's shape, and ``area`` its cross-section
    facing the flow in m².
    """
    return 0.5 * density * drag_coefficient * area


def fall_with_linear_drag(
    initial: State, mass: float, b: float, g: ArrayLike, t: ArrayLike
) -> Trajectory:
    """The exact motion of a particle of ``mass`` (kg) under its weight and
    linear drag with the constant ``b`` (kg/s), evaluated at the times ``t``.

    ``g`` is the gravitational acceleration as a vector in m/s², like the
    position. With the time constant tau = m / b and the terminal velocity
    v_T = g tau, the velocity relaxes towards v_T and the position follows:

        v(t) = v_T + (v_0 - v_T) exp(-(t - t_0) / tau),
        x(t) = x_0 + v_T (t - t_0) + (v_0 - v_T) tau (1 - exp(-(t - t_0) / tau)).

    ``t`` is a scalar or an array; the arrays of the result have one row per
    time. ``b`` must be positive: without drag the motion is the one of
    ``pbc.mechanics.kinematics.constant_acceleration``.
    """
    if mass <= 0:
        raise ValueError(f"mass must be positive, got {mass}")
    if b <= 0:
        raise ValueError(f"the drag constant must be positive, got {b}")
    tau = mass / b
    terminal = np.array(g, dtype=np.float64, ndmin=1) * tau
    times = np.array(t, dtype=np.float64, ndmin=1)
    elapsed = (times - initial.t)[:, np.newaxis]
    decay = np.exp(-elapsed / tau)
    excess = initial.v - terminal
    return Trajectory(
        t=times,
        x=initial.x + terminal * elapsed + excess * tau * (1.0 - decay),
        v=terminal + excess * decay,
    )
