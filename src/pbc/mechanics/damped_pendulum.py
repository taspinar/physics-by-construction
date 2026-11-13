"""The damped pendulum: the model that the pendulum lab tests against a
measured record.

It joins three lessons. At small angles the pendulum is the harmonic
oscillator (``pbc.mechanics.oscillator``) with the period 2 pi sqrt(L/g); at
any amplitude its period is the exact one of ``pbc.mechanics.pendulum``,
4 sqrt(L/g) K(sin^2(A/2)); and a drag that is linear in the angular
velocity makes its amplitude decay exponentially at the rate gamma of the
damped oscillator (``pbc.mechanics.resonance``). The lab adds the drag that
is quadratic in the speed, which a body moving fast through air feels.

In the angle theta about the pivot the equation of motion is

    theta'' = -w0^2 sin(theta) - 2 gamma theta' - beta |theta'| theta',

with w0 = 2 pi / T0 the small-amplitude angular frequency, gamma in 1/s
and beta in 1/rad. It holds for any rigid pendulum, not only a point mass:
for a body of moment of inertia I about the axis, mass m and centre of mass
at the distance d from it, w0^2 = m g d / I, the same as for a point mass on
a massless rod of the *effective length* L_eff = I / (m d).

When the damping is weak (little change of the amplitude A within one
cycle), averaging the drag over one cycle gives

    A' = -gamma A - kappa A^2,    kappa = 4 beta w0 / (3 pi),

whose solution is ``amplitude_envelope``. The averaging takes theta =
A cos(w0 t) within a cycle, so at large amplitude kappa is a parameter of
the envelope rather than an exact function of beta; the lab fits gamma and
kappa to the envelope and never needs beta.

Quantities in SI units: time in s, angles in rad, lengths in m, ``g`` in
m/s^2.
"""

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.special import ellipk

from pbc.mechanics.dynamics import Acceleration, Vector


def small_amplitude_period(period: ArrayLike, amplitude: ArrayLike) -> NDArray:
    """The small-amplitude period T0 [s] of a pendulum that swings with the
    ``period`` [s] at the ``amplitude`` [rad]: the exact period
    4 sqrt(L/g) K(m), m = sin^2(A/2), divided by its value at zero
    amplitude, inverted: T0 = T pi / (2 K(m))."""
    m = np.sin(np.asarray(amplitude, dtype=float) / 2) ** 2
    return np.asarray(period, dtype=float) * np.pi / (2 * ellipk(m))


def damped_pendulum(t0: float, gamma: float, beta: float) -> Acceleration:
    """The angular acceleration a(t, theta, omega) [rad/s^2] of a pendulum
    of small-amplitude period ``t0`` [s] with linear damping ``gamma``
    [1/s] and quadratic damping ``beta`` [1/rad], for the steppers of
    ``pbc.mechanics.integrators`` (the position is the angle, the velocity
    the angular velocity)."""
    if t0 <= 0:
        raise ValueError(f"the period must be positive, got {t0}")
    if gamma < 0 or beta < 0:
        raise ValueError("the damping constants must not be negative")
    w0_squared = (2 * np.pi / t0) ** 2

    def acceleration(t: float, x: Vector, v: Vector) -> Vector:
        return -w0_squared * np.sin(x) - 2 * gamma * v - beta * np.abs(v) * v

    return acceleration


def amplitude_envelope(
    t: ArrayLike, a1: float, gamma: float, kappa: float = 0.0
) -> NDArray:
    """The amplitude [rad] at the times ``t`` [s] of the averaged decay
    A' = -gamma A - kappa A^2 from A(0) = ``a1``:

        A(t) = a1 e^(-gamma t) / (1 + (kappa a1 / gamma) (1 - e^(-gamma t))),

    the exponential decay of linear damping when ``kappa`` = 0, and
    a1 / (1 + kappa a1 t) when ``gamma`` = 0."""
    t = np.asarray(t, dtype=float)
    decay = np.exp(-gamma * t)
    # (1 - e^(-gamma t)) / gamma, which tends to t as gamma goes to 0.
    growth = -np.expm1(-gamma * t) / gamma if gamma != 0 else t
    return a1 * decay / (1 + kappa * a1 * growth)


def quadratic_envelope_constant(beta: float, t0: float) -> float:
    """kappa [1/(rad s)] of the averaged envelope for the quadratic damping
    ``beta`` [1/rad] of a pendulum of small-amplitude period ``t0`` [s]:
    4 beta w0 / (3 pi), from the average of |sin|^3 over a cycle."""
    return 4 * beta * (2 * np.pi / t0) / (3 * np.pi)


def effective_length(t0: ArrayLike, g: float) -> NDArray:
    """The length [m] of the simple pendulum with the small-amplitude period
    ``t0`` [s]: g T0^2 / (4 pi^2), which is I / (m d) of a rigid one."""
    return g * np.asarray(t0, dtype=float) ** 2 / (4 * np.pi**2)
