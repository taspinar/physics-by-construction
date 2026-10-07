"""The pendulum: a particle on a rigid, massless rod of fixed length,
swinging in a vertical plane under its weight.

The particle moves on a circle, so one coordinate describes it: the arc
length s = L theta from the lowest point, in metres, with theta the angle
of the rod from the vertical. The rod's tension points along the rod, does
no work, and is not modelled; the force along the arc is the tangential
component of the weight, -m g sin(s / L). For small angles it is Hooke's
law with the spring constant m g / L, and the pendulum is the harmonic
oscillator of ``pbc.mechanics.oscillator``. At large amplitude the force is
weaker than the linear one, the period grows with the amplitude, and the
motion has no closed form in elementary functions; the period does, through
the complete elliptic integral.

Quantities are in SI units as in ``pbc.mechanics.dynamics``: the length in
metres, angles in radians, ``g`` in m/s² (the standard value by default).
"""

import numpy as np
from scipy.constants import g as STANDARD_GRAVITY  # 9.80665 m/s²
from scipy.special import ellipk

from pbc.mechanics.dynamics import Force, Vector
from pbc.mechanics.energy import Potential


def _check(mass: float | None, length: float, g: float) -> None:
    if mass is not None and mass <= 0:
        raise ValueError(f"mass must be positive, got {mass}")
    if length <= 0:
        raise ValueError(f"the length must be positive, got {length}")
    if g <= 0:
        raise ValueError(f"g must be positive, got {g}")


def pendulum_force(mass: float, length: float, g: float = STANDARD_GRAVITY) -> Force:
    """The force along the arc on a pendulum bob of ``mass`` (kg) on a rod
    of ``length`` (m): the tangential component -m g sin(s / L) of the
    weight, with the position s the arc length from the lowest point.

    For |s| much smaller than L it is -(m g / L) s, the spring of the
    harmonic oscillator lesson.
    """
    _check(mass, length, g)

    def force(t: float, x: Vector, v: Vector) -> Vector:
        return -mass * g * np.sin(x / length)

    return force


def pendulum_potential(
    mass: float, length: float, g: float = STANDARD_GRAVITY
) -> Potential:
    """The potential energy m g L (1 - cos(s / L)) in J of the bob at the arc
    length s: its weight times its height above the lowest point. It is 0 at
    the bottom and 2 m g L at the top, the energy that separates swinging
    from going over the top."""
    _check(mass, length, g)

    def potential(x: Vector) -> float:
        return float(mass * g * length * (1.0 - np.cos(x[0] / length)))

    return potential


def small_angle_period(length: float, g: float = STANDARD_GRAVITY) -> float:
    """The period 2 pi sqrt(L / g) in s of a pendulum of ``length`` (m) at
    small amplitude, where it is a harmonic oscillator."""
    _check(None, length, g)
    return float(2.0 * np.pi * np.sqrt(length / g))


def pendulum_period(
    length: float, amplitude: float, g: float = STANDARD_GRAVITY
) -> float:
    """The exact period in s of a pendulum of ``length`` (m) released from
    rest at the angle ``amplitude`` (rad), 0 <= amplitude < pi.

    With k = sin(amplitude / 2) the period is 4 sqrt(L / g) K(k²), where K
    is the complete elliptic integral of the first kind; it is the
    small-angle period at amplitude 0 and grows without bound as the
    amplitude approaches pi, the unstable rest position at the top.
    """
    _check(None, length, g)
    if not 0 <= amplitude < np.pi:
        raise ValueError(f"the amplitude must be in [0, pi), got {amplitude}")
    k = np.sin(0.5 * amplitude)
    return float(4.0 * np.sqrt(length / g) * ellipk(k**2))
