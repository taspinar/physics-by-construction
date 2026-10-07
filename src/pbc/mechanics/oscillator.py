"""The harmonic oscillator: a particle pulled back to the origin by a force
proportional to its displacement, F = -k x.

It is the test system of the course. Its exact motion is known for all time,
its energy is conserved, and both can be compared with a simulation at every
step. The functions here give the force model, the exact motion, the energy
of a trajectory, and the one number this lesson derives about explicit
Euler: the factor by which it multiplies the energy at every step.

Quantities are in SI units as in ``pbc.mechanics.dynamics``; the spring
constant ``k`` is in N/m.
"""

import numpy as np
from numpy.typing import ArrayLike, NDArray

from pbc.mechanics.dynamics import Force, State, Trajectory, Vector


def spring(k: float) -> Force:
    """Hooke's law: the force -k x towards the origin, with the spring
    constant ``k`` in N/m.

    The same function serves on a line and in a plane; in a plane it is an
    isotropic spring, equally stiff in every direction.
    """
    if k <= 0:
        raise ValueError(f"the spring constant must be positive, got {k}")

    def force(t: float, x: Vector, v: Vector) -> Vector:
        return -k * x

    return force


def angular_frequency(mass: float, k: float) -> float:
    """The angular frequency omega = sqrt(k / m) in rad/s of a particle of
    ``mass`` (kg) on a spring with the constant ``k`` (N/m). The period is
    2 pi / omega."""
    if mass <= 0:
        raise ValueError(f"mass must be positive, got {mass}")
    if k <= 0:
        raise ValueError(f"the spring constant must be positive, got {k}")
    return float(np.sqrt(k / mass))


def harmonic_motion(initial: State, mass: float, k: float, t: ArrayLike) -> Trajectory:
    """The exact motion of a particle of ``mass`` (kg) on a spring with the
    constant ``k`` (N/m), evaluated at the times ``t``.

    With omega = sqrt(k / m) and the elapsed time s = t - t_0,

        x(t) = x_0 cos(omega s) + (v_0 / omega) sin(omega s),
        v(t) = -x_0 omega sin(omega s) + v_0 cos(omega s).

    The formula holds componentwise, so it serves on a line and in a plane.
    ``t`` is a scalar or an array; the arrays of the result have one row per
    time.
    """
    omega = angular_frequency(mass, k)
    times = np.array(t, dtype=np.float64, ndmin=1)
    phase = omega * (times - initial.t)[:, np.newaxis]
    cos, sin = np.cos(phase), np.sin(phase)
    return Trajectory(
        t=times,
        x=initial.x * cos + initial.v / omega * sin,
        v=-initial.x * omega * sin + initial.v * cos,
    )


def energy(trajectory: Trajectory, mass: float, k: float) -> NDArray[np.float64]:
    """The total mechanical energy in J at every instant of ``trajectory``:
    the kinetic energy m |v|² / 2 plus the potential energy k |x|² / 2 of
    the spring."""
    kinetic = 0.5 * mass * np.sum(trajectory.v**2, axis=1)
    potential = 0.5 * k * np.sum(trajectory.x**2, axis=1)
    return kinetic + potential


def euler_energy_growth(mass: float, k: float, dt: float) -> float:
    """The factor 1 + omega² dt² = 1 + k dt² / m by which one explicit Euler
    step of length ``dt`` (s) multiplies the energy of the harmonic
    oscillator, whatever the state.

    The lesson derives it from the update rule; the formal proofs strand
    proves it. It is never less than 1: explicit Euler feeds energy into the
    oscillator at every step, by the same factor each time.
    """
    if dt <= 0:
        raise ValueError(f"dt must be positive, got {dt}")
    return 1.0 + angular_frequency(mass, k) ** 2 * dt**2
