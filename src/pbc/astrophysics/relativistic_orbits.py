"""Orbits of a test body about a spherical mass in general relativity.

Units G = c = 1: the mass has the length m = GM/c². In the Schwarzschild
geometry a bound orbit of a test body obeys, for u = 1/r as a function of
the angle phi (the relativistic Binet equation),

    u'' + u = m / h² + 3 m u²,

with h the angular momentum per unit rest mass. Without the last term it is
Kepler's ellipse u = (1 + e cos phi) / p. A first integral is the cubic

    (u')² = 2 m (u - u1)(u2 - u)(u3 - u),

whose roots u1 = (1 - e)/p and u2 = (1 + e)/p are the turning points (the
apoapsis and the periapsis) and u3 = 1/(2m) - u1 - u2. The angle from one
periapsis to the next is then a complete elliptic integral of the first
kind, which gives the exact turn per orbit

    delta phi = 4 K(k) / sqrt(2 m (u3 - u1)) - 2 pi,   k² = (u2 - u1)/(u3 - u1).

To first order in m/p it is the classic 6 pi m / p, and the next term is
(3 pi / 2)(18 + e²)(m/p)². The post-Newtonian equations of motion of a test
body in harmonic coordinates,

    a = -(m / r²) [(1 + v² - 4 m / r) n - 4 (n . v) v],

reproduce the first order and not the second. The effective potential
(1 - 2m/r)(1 + h²/r²) has a minimum, a stable circular orbit, only for
h² >= 12 m², at radii above the innermost stable circular orbit, r = 6 m.
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.integrate import solve_ivp
from scipy.special import ellipk


def _roots(m: float, p: float, e: float) -> tuple[float, float, float]:
    if m <= 0 or p <= 0:
        raise ValueError("m and p must be positive")
    if not 0 < e < 1:
        raise ValueError(f"the eccentricity must be between 0 and 1, got {e}")
    u1, u2 = (1 - e) / p, (1 + e) / p
    u3 = 1 / (2 * m) - u1 - u2
    if u3 <= u2:
        raise ValueError("no bound orbit has these turning points: it falls in")
    return u1, u2, u3


def angular_momentum(m: float, p: float, e: float) -> float:
    """The angular momentum per unit rest mass h of the Schwarzschild orbit
    whose turning points are r = p/(1 + e) and r = p/(1 - e):
    1/h² = u1 u2 + u3 (u1 + u2), from the coefficients of the cubic."""
    u1, u2, u3 = _roots(m, p, e)
    return float(1 / np.sqrt(u1 * u2 + u3 * (u1 + u2)))


def exact_precession(m: float, p: float, e: float) -> float:
    """The exact turn of the periapsis per orbit, in radians, of the
    Schwarzschild orbit with turning points p/(1 + e) and p/(1 - e), from
    the complete elliptic integral of its cubic."""
    u1, u2, u3 = _roots(m, p, e)
    k2 = (u2 - u1) / (u3 - u1)
    return float(4 * ellipk(k2) / np.sqrt(2 * m * (u3 - u1)) - 2 * np.pi)


def first_order_precession(m: ArrayLike, p: ArrayLike) -> NDArray[np.float64]:
    """The first-order (post-Newtonian) turn of the periapsis per orbit,
    6 pi m / p, with p = a (1 - e²) the semi-latus rectum: in SI units
    6 pi G M / (c² a (1 - e²))."""
    return 6 * np.pi * np.asarray(m, dtype=np.float64) / np.asarray(p)


def second_order_coefficient(e: float) -> float:
    """The coefficient of (m/p)² in the exact turn per orbit:
    (3 pi / 2)(18 + e²)."""
    return 1.5 * np.pi * (18 + e**2)


@dataclass(frozen=True)
class Geodesic:
    """A Schwarzschild orbit as u = 1/r against the angle, with the angles of
    its periapsis passages after the start."""

    phi: NDArray[np.float64]
    u: NDArray[np.float64]
    periapsis_phi: NDArray[np.float64]


def geodesic(
    m: float,
    p: float,
    e: float,
    orbits: float,
    samples: int = 4001,
    tolerance: float = 1e-12,
) -> Geodesic:
    """Integrate the relativistic Binet equation u'' + u = m/h² + 3 m u²
    (DOP853) from the periapsis u = (1 + e)/p for ``orbits`` turns of the
    angle, locating every periapsis as the angle at which u' crosses zero
    downwards."""
    h2 = angular_momentum(m, p, e) ** 2

    def rate(phi, y):
        return [y[1], m / h2 + 3 * m * y[0] ** 2 - y[0]]

    def slope(phi, y):
        return y[1]

    slope.direction = -1
    end = orbits * 2 * np.pi
    solution = solve_ivp(
        rate,
        (0.0, end),
        [(1 + e) / p, 0.0],
        method="DOP853",
        t_eval=np.linspace(0.0, end, samples),
        events=slope,
        rtol=tolerance,
        atol=tolerance * (1 + e) / p,
    )
    if not solution.success:
        raise RuntimeError(solution.message)
    passages = solution.t_events[0]
    return Geodesic(solution.t, solution.y[0], passages[passages > end * 1e-9])


def turn_per_orbit(periapsis_phi: ArrayLike) -> float:
    """The mean turn of the periapsis per orbit from the angles of the
    periapsis passages after a start at a periapsis at angle zero, with no
    turn of more than half a revolution per orbit."""
    phi = np.asarray(periapsis_phi, dtype=np.float64)
    if len(phi) == 0:
        raise ValueError("the orbit has no periapsis passage after the start")
    return float(phi[-1] / len(phi) - 2 * np.pi)


def post_newtonian_acceleration(m: float, x: NDArray, v: NDArray) -> NDArray:
    """The first post-Newtonian acceleration of a test body in harmonic
    coordinates, -(m/r²)[(1 + v² - 4m/r) n - 4 (n . v) v]."""
    r = np.linalg.norm(x)
    n = x / r
    return -(m / r**2) * ((1 + v @ v - 4 * m / r) * n - 4 * (n @ v) * v)


def post_newtonian_orbit(
    m: float, p: float, e: float, orbits: float, tolerance: float = 1e-12
) -> NDArray[np.float64]:
    """Integrate the post-Newtonian equations of motion in time (DOP853) from
    the periapsis r = p/(1 + e) of the Kepler ellipse (p, e), with Kepler's
    speed there, for about ``orbits`` Kepler periods; return the polar
    angles of the periapsis passages after the start, unwrapped."""
    if m <= 0 or p <= 0 or not 0 < e < 1:
        raise ValueError("m and p must be positive and e between 0 and 1")
    r0 = p / (1 + e)
    start = [r0, 0.0, 0.0, np.sqrt(m / p) * (1 + e)]

    def rate(t, y):
        return [y[2], y[3], *post_newtonian_acceleration(m, y[:2], y[2:])]

    def radial_velocity(t, y):
        return y[0] * y[2] + y[1] * y[3]

    radial_velocity.direction = 1
    period = 2 * np.pi * np.sqrt((p / (1 - e**2)) ** 3 / m)
    end = orbits * period
    solution = solve_ivp(
        rate,
        (0.0, end),
        start,
        method="DOP853",
        events=radial_velocity,
        rtol=tolerance,
        atol=tolerance * r0,
    )
    if not solution.success:
        raise RuntimeError(solution.message)
    keep = solution.t_events[0] > end * 1e-9
    at = solution.y_events[0][keep]
    angles = np.unwrap(np.concatenate([[0.0], np.arctan2(at[:, 1], at[:, 0])]))
    passages = np.arange(1, len(angles))
    return angles[1:] + 2 * np.pi * passages


def effective_potential(r: ArrayLike, h: float, m: float) -> NDArray[np.float64]:
    """The relativistic effective potential (1 - 2m/r)(1 + h²/r²), the
    square of the energy per unit rest mass at which a body of angular
    momentum h per unit rest mass turns at r."""
    r = np.asarray(r, dtype=np.float64)
    return (1 - 2 * m / r) * (1 + h**2 / r**2)


def circular_orbit_radii(h: float, m: float) -> tuple[float, float] | None:
    """The radii (unstable, stable) of the circular orbits of angular
    momentum h per unit rest mass, the turning points of the effective
    potential: r = (h²/(2m))(1 -+ sqrt(1 - 12 m²/h²)); None for
    h² < 12 m², when there is none."""
    discriminant = 1 - 12 * m**2 / h**2
    if discriminant < 0:
        return None
    root = np.sqrt(discriminant)
    return float(h**2 / (2 * m) * (1 - root)), float(h**2 / (2 * m) * (1 + root))
