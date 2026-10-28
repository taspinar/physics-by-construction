"""Orbits under central forces other than the inverse square.

A body moves in the plane about a fixed centre under a radial acceleration
f(r) (negative for attraction) per unit mass. Any central force keeps the
angular momentum per unit mass h = x v_y - y v_x, and a force with a
potential V(r), f = -dV/dr, keeps the energy v²/2 + V(r). Only the inverse
square and the linear spring close every bound orbit (Bertrand, 1873); any
other law turns the orbit's periapsis a little at every pass.

For a small radial perturbation R(r) of Newton's -GM/r², the turn of the
periapsis per orbit follows, to first order in R, from Gauss's equation for
the argument of periapsis, integrated along the unperturbed ellipse of
semi-major axis a and eccentricity e:

    delta omega = -(1 / (e GM)) * integral over nu from 0 to 2 pi of
                  R(r(nu)) r(nu)² cos(nu) dnu,
    r(nu) = a (1 - e²) / (1 + e cos nu).

For the power law f = -GM a^delta / r^(2 + delta), which equals Newton's at
r = a, the integral has the closed form

    delta omega = 2 pi delta (1 - sqrt(1 - e²)) / e²,

which is pi delta for a nearly circular orbit. For a nearly circular orbit
the apsidal angle is also known for any delta < 1, pi / sqrt(1 - delta), so
the turn per orbit is 2 pi (1 / sqrt(1 - delta) - 1).

The orbits are integrated by the adaptive Dormand-Prince method of order
eight (``scipy.integrate.solve_ivp``, DOP853), and each periapsis is the
event at which the radial velocity x . v crosses zero upwards, located to
the tolerance of the integrator.
"""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.integrate import solve_ivp

# A radial acceleration per unit mass, f(r), for an array of radii.
type Radial = Callable[[NDArray[np.float64]], NDArray[np.float64]]


def _check(gm: float, a: float, e: float) -> None:
    if gm <= 0 or a <= 0:
        raise ValueError("GM and a must be positive")
    if not 0 < e < 1:
        raise ValueError(f"the eccentricity must be between 0 and 1, got {e}")


def newton(gm: float) -> Radial:
    """Newton's inverse square, -GM / r²."""
    return lambda r: -gm / r**2


def power_law(gm: float, a: float, delta: float) -> Radial:
    """The attraction -GM a^delta / r^(2 + delta): an inverse square for
    delta = 0, and equal to it at r = a for every delta."""
    return lambda r: -gm * a**delta / r ** (2 + delta)


def yukawa(gm: float, alpha: float, scale: float) -> Radial:
    """Newton's attraction with a Yukawa term of strength ``alpha`` and range
    ``scale``, from the potential -(GM / r)(1 + alpha exp(-r / scale)):
    -(GM / r²)(1 + alpha (1 + r / scale) exp(-r / scale))."""
    if scale <= 0:
        raise ValueError("the range must be positive")
    return lambda r: -gm / r**2 * (1 + alpha * (1 + r / scale) * np.exp(-r / scale))


def yukawa_term(gm: float, scale: float) -> Radial:
    """The Yukawa part of ``yukawa`` per unit strength, the radial
    perturbation -(GM / r²)(1 + r / scale) exp(-r / scale) of Newton's
    force."""
    if scale <= 0:
        raise ValueError("the range must be positive")
    return lambda r: -gm / r**2 * (1 + r / scale) * np.exp(-r / scale)


def power_law_potential(gm: float, a: float, delta: float) -> Radial:
    """The potential of ``power_law``, -GM a^delta / ((1 + delta) r^(1 + delta)),
    per unit mass."""
    return lambda r: -gm * a**delta / ((1 + delta) * r ** (1 + delta))


def yukawa_potential(gm: float, alpha: float, scale: float) -> Radial:
    """The potential of ``yukawa``, -(GM / r)(1 + alpha exp(-r / scale)), per
    unit mass."""
    return lambda r: -gm / r * (1 + alpha * np.exp(-r / scale))


def periapsis_start(gm: float, a: float, e: float) -> tuple[NDArray, NDArray]:
    """The position and velocity at periapsis, on the x axis, of the Kepler
    ellipse of semi-major axis ``a`` and eccentricity ``e`` about GM."""
    _check(gm, a, e)
    r = a * (1 - e)
    return np.array([r, 0.0]), np.array([0.0, np.sqrt(gm * (1 + e) / r)])


@dataclass(frozen=True)
class Orbit:
    """An orbit under a central force: the samples of the path, and the
    times and positions of its periapsis passages after the start."""

    t: NDArray[np.float64]  # sample times, shape (n,)
    x: NDArray[np.float64]  # positions, shape (n, 2)
    v: NDArray[np.float64]  # velocities, shape (n, 2)
    periapsis_t: NDArray[np.float64]
    periapsis_x: NDArray[np.float64]  # shape (passages, 2)


def orbit(
    force: Radial,
    position: ArrayLike,
    velocity: ArrayLike,
    duration: float,
    samples: int = 2001,
    tolerance: float = 1e-12,
) -> Orbit:
    """Integrate the motion under ``force`` from ``position`` and
    ``velocity`` for ``duration``, read at ``samples`` equally spaced
    times, and locate every periapsis passage after the start."""

    def rate(t, y):
        r = np.hypot(y[0], y[1])
        f = force(r)
        return [y[2], y[3], f * y[0] / r, f * y[1] / r]

    def radial_velocity(t, y):
        return y[0] * y[2] + y[1] * y[3]

    radial_velocity.direction = 1
    times = np.linspace(0.0, duration, samples)
    solution = solve_ivp(
        rate,
        (0.0, duration),
        np.concatenate([position, velocity]),
        method="DOP853",
        t_eval=times,
        events=radial_velocity,
        rtol=tolerance,
        atol=tolerance / 100,
    )
    if not solution.success:
        raise RuntimeError(solution.message)
    keep = solution.t_events[0] > duration * 1e-9  # not the start itself
    return Orbit(
        t=solution.t,
        x=solution.y[:2].T,
        v=solution.y[2:].T,
        periapsis_t=solution.t_events[0][keep],
        periapsis_x=solution.y_events[0][keep, :2],
    )


def precession_per_orbit(path: Orbit) -> float:
    """The mean turn of the periapsis per orbit, in radians, positive in the
    sense of the motion (anticlockwise): the angle of the last periapsis
    after the start, unwrapped from one passage to the next, over the number
    of orbits. The start must be a periapsis on the positive x axis, and the
    turn per orbit less than half a turn."""
    if len(path.periapsis_t) == 0:
        raise ValueError("the orbit has no periapsis passage after the start")
    angles = np.unwrap(
        np.concatenate(
            [[0.0], np.arctan2(path.periapsis_x[:, 1], path.periapsis_x[:, 0])]
        )
    )
    return float(angles[-1] / len(path.periapsis_t))


def energy(path: Orbit, potential: Callable[[NDArray], NDArray]) -> NDArray:
    """The energy per unit mass v²/2 + V(r) at every sample."""
    return 0.5 * np.sum(path.v**2, axis=1) + potential(np.hypot(*path.x.T))


def angular_momentum(path: Orbit) -> NDArray:
    """The angular momentum per unit mass x v_y - y v_x at every sample."""
    return path.x[:, 0] * path.v[:, 1] - path.x[:, 1] * path.v[:, 0]


def first_order_precession(
    perturbation: Radial, gm: float, a: float, e: float, nodes: int = 4096
) -> float:
    """The turn of the periapsis per orbit, to first order in the radial
    ``perturbation`` R(r) of Newton's force, from Gauss's equation
    integrated along the Kepler ellipse (a, e). The integrand is smooth and
    periodic, so the trapezoidal rule on ``nodes`` equal steps of the true
    anomaly converges faster than any power of the step."""
    _check(gm, a, e)
    nu = 2 * np.pi * np.arange(nodes) / nodes
    r = a * (1 - e**2) / (1 + e * np.cos(nu))
    integral = 2 * np.pi * np.mean(perturbation(r) * r**2 * np.cos(nu))
    return float(-integral / (e * gm))


def power_law_precession(delta: ArrayLike, e: float) -> NDArray:
    """The first-order turn per orbit of the power law, in closed form:
    2 pi delta (1 - sqrt(1 - e²)) / e²."""
    if not 0 < e < 1:
        raise ValueError(f"the eccentricity must be between 0 and 1, got {e}")
    return 2 * np.pi * np.asarray(delta) * (1 - np.sqrt(1 - e**2)) / e**2


def near_circular_precession(delta: ArrayLike) -> NDArray:
    """The turn per orbit of a nearly circular orbit under the power law,
    for any delta < 1: 2 pi (1 / sqrt(1 - delta) - 1)."""
    d = np.asarray(delta, dtype=np.float64)
    if np.any(d >= 1):
        raise ValueError("no circular orbit is stable for delta >= 1")
    return 2 * np.pi * (1 / np.sqrt(1 - d) - 1)
