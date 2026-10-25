"""Attractors and bifurcations of two nonlinear mechanical systems.

**A bead on a rotating hoop.** A bead slides without friction, but with a
drag proportional to its speed, on a vertical hoop of radius R that turns
about its vertical diameter at the angular velocity Omega. With theta the
angle of the bead from the bottom,

    theta'' = sin theta (Omega² cos theta - g / R) - 2 gamma theta',

the weight pulls the bead down and the centrifugal force of the rotating
frame pushes it out. The bottom, theta = 0, is an equilibrium at every
rotation rate. Linearised about it, theta'' = (Omega² - g/R) theta - 2 gamma
theta': stable below the critical rate Omega_c = sqrt(g / R), unstable above.
Above it two new stable equilibria appear, cos theta* = g / (R Omega²), one
on each side: a supercritical pitchfork bifurcation. At the threshold the
linear restoring force vanishes and the first term that acts is cubic,
theta'' ≈ -(Omega_c² / 2) theta³ - 2 gamma theta', so the bead returns
algebraically, not exponentially.

**A self-excited oscillator.** The oscillator

    x'' - (mu - x²) x' + x = 0

(time in units of the inverse natural angular frequency, x in units of
the amplitude at which the damping changes sign) has negative damping at
small amplitude when mu > 0 and positive damping at large amplitude. Below
mu = 0 every motion decays to rest; above it rest is unstable and every
motion approaches one closed orbit, the limit cycle, whose amplitude grows
from zero as 2 sqrt(mu) for small mu: a supercritical Hopf bifurcation.

Both accelerations take the parameter as an array with one entry per copy
of the system, so one simulation runs a whole bifurcation diagram: the
state vector holds one coordinate per parameter value.

Quantities of the hoop are in SI units: g in m/s², R in m, rates in
rad/s or 1/s, angles in rad.
"""

import numpy as np
from numpy.typing import ArrayLike, NDArray

from pbc.mechanics.dynamics import Acceleration, Trajectory, Vector


def _check_hoop(g: float, radius: float) -> None:
    if g <= 0 or radius <= 0:
        raise ValueError("g and the radius of the hoop must be positive")


def hoop(g: float, radius: float, rotation: ArrayLike, gamma: float) -> Acceleration:
    """The angular acceleration theta'' of a bead on a hoop of ``radius``
    (m) turning at ``rotation`` Omega (rad/s), under gravity ``g`` (m/s²),
    with the damping rate ``gamma`` (1/s).

    ``rotation`` is a number or an array with one rate per copy of the
    bead; the angle vector theta (rad) then has one entry per copy.
    """
    _check_hoop(g, radius)
    if gamma < 0:
        raise ValueError(f"the damping rate must not be negative, got {gamma}")
    omega_sq = np.asarray(rotation, dtype=np.float64) ** 2
    stiffness = g / radius

    def acceleration(t: float, x: Vector, v: Vector) -> Vector:
        return np.sin(x) * (omega_sq * np.cos(x) - stiffness) - 2.0 * gamma * v

    return acceleration


def critical_rotation(g: float, radius: float) -> float:
    """The rotation rate Omega_c = sqrt(g / R) in rad/s at which the bottom
    of the hoop stops being stable."""
    _check_hoop(g, radius)
    return float(np.sqrt(g / radius))


def hoop_equilibrium(g: float, radius: float, rotation: ArrayLike) -> NDArray:
    """The stable equilibrium angle theta* >= 0 in rad at each ``rotation``
    rate (rad/s): zero up to the critical rate, arccos(g / (R Omega²))
    above it (the bead may sit at minus this angle as well)."""
    _check_hoop(g, radius)
    omega = np.asarray(rotation, dtype=np.float64)
    ratio = np.minimum(1.0, g / (radius * np.maximum(omega**2, 1e-300)))
    return np.arccos(ratio)


def hoop_linear_rate(
    g: float, radius: float, rotation: ArrayLike, gamma: float
) -> NDArray:
    """The rate in 1/s at which the linearised motion about the stable
    equilibrium decays at each ``rotation`` rate (rad/s).

    The linearised equation is delta'' = -k delta - 2 gamma delta' with the
    stiffness k = Omega_c² - Omega² below the critical rate and
    k = Omega² sin² theta* above it. Overdamped (gamma² > k) the slow root
    gamma - sqrt(gamma² - k) sets the decay; underdamped the envelope
    decays at gamma. The rate vanishes at the threshold: there the linear
    model predicts no return at all.
    """
    omega = np.asarray(rotation, dtype=np.float64)
    theta = hoop_equilibrium(g, radius, omega)
    k = np.where(theta > 0.0, omega**2 * np.sin(theta) ** 2, g / radius - omega**2)
    return np.where(gamma**2 > k, gamma - np.sqrt(np.maximum(gamma**2 - k, 0.0)), gamma)


def self_excited(mu: ArrayLike) -> Acceleration:
    """The acceleration x'' = (mu - x²) x' - x of the self-excited
    oscillator, in its dimensionless units, for each value of ``mu`` (one
    entry of the state per value)."""
    mus = np.asarray(mu, dtype=np.float64)

    def acceleration(t: float, x: Vector, v: Vector) -> Vector:
        return (mus - x**2) * v - x

    return acceleration


def limit_cycle_amplitude(mu: ArrayLike) -> NDArray:
    """The amplitude 2 sqrt(mu) of the limit cycle for small mu > 0, and
    zero for mu <= 0, where the oscillator comes to rest.

    It follows from averaging over one period of the nearly harmonic
    motion x = A cos t: the energy the negative damping feeds in, mu A² / 2
    per unit time on average, balances what the cubic term takes out,
    A⁴ / 8, at A² = 4 mu.
    """
    mus = np.asarray(mu, dtype=np.float64)
    return 2.0 * np.sqrt(np.maximum(mus, 0.0))


def final_amplitude(trajectory: Trajectory, window: float) -> NDArray:
    """The largest |x| of each coordinate over the last ``window`` of time
    (s, or dimensionless time) of a ``trajectory``: the size of the
    attractor reached, an equilibrium (the angle itself) or a cycle (its
    amplitude)."""
    late = trajectory.t >= trajectory.t[-1] - window
    return np.max(np.abs(trajectory.x[late]), axis=0)
