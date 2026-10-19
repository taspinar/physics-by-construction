"""The inviscid Burgers equation u_t + (u^2 / 2)_x = 0 (lessons FL4 and FL9):
the simplest conservation law whose waves steepen into shocks.

Each value of u travels at the speed u, so faster parts of a profile catch up
with slower parts ahead of them. Before they meet, the solution follows the
characteristics, u(x, t) = u0(x - u t); where they cross, a shock forms, and
it moves at the Rankine-Hugoniot speed (u_L + u_R) / 2 that conservation of
the integral of u fixes. Across the shock the energy u^2 / 2 is lost at the
rate (u_L - u_R)^3 / 12.

``godunov_flux`` is the Riemann solver of the shared finite-volume interface
(``pbc.fluids.finite_volume``). ``nonconservative_step`` discretises the
same equation in the form u_t + u u_x = 0, which agrees with it where u is
smooth and not at a shock.
"""

import numpy as np
from numpy.typing import ArrayLike
from scipy.optimize import brentq

from pbc.fluids.finite_volume import Array, Boundary, with_ghosts

__all__ = [
    "breaking_time",
    "characteristic_solution",
    "flux",
    "godunov_flux",
    "max_speed",
    "nonconservative_step",
    "riemann_solution",
    "shock_dissipation",
    "shock_speed",
]


def flux(u: Array) -> Array:
    """The flux u^2 / 2 of the Burgers equation."""
    return 0.5 * u * u


def max_speed(u: Array) -> float:
    """The largest signal speed |u| of a state, for the CFL condition."""
    return float(np.max(np.abs(u)))


def godunov_flux(left: Array, right: Array) -> Array:
    """The flux through a face of the exact solution of the Riemann problem
    with the states ``left`` and ``right``, at the face.

    For left > right the solution is a shock of speed (left + right) / 2, and
    the face sees the state on the side the shock moves away from. For
    left <= right it is a rarefaction fan, and the face sees left if the fan
    moves right, right if it moves left, and the sonic value u = 0 inside it.
    """
    shock = left > right
    speed = 0.5 * (left + right)
    shock_flux = np.where(speed > 0, flux(left), flux(right))
    fan_flux = np.where(left > 0, flux(left), np.where(right < 0, flux(right), 0.0))
    return np.where(shock, shock_flux, fan_flux)


def shock_speed(left: float, right: float) -> float:
    """The Rankine-Hugoniot speed of a shock between ``left`` and ``right``:
    the jump of the flux over the jump of u."""
    return (flux(np.float64(left)) - flux(np.float64(right))) / (left - right)


def shock_dissipation(left: float, right: float) -> float:
    """The rate (left - right)^3 / 12 at which a shock between ``left`` and
    ``right`` removes the energy u^2 / 2 from the flow, per unit time."""
    return (left - right) ** 3 / 12.0


def breaking_time(slope: ArrayLike) -> float:
    """The time at which the first characteristics cross, -1 over the most
    negative slope of the initial profile, sampled in ``slope``; infinite if
    the profile rises everywhere."""
    steepest = float(np.min(slope))
    return np.inf if steepest >= 0 else -1.0 / steepest


def characteristic_solution(u0, x: ArrayLike, t: float, period: float) -> Array:
    """The solution u(x, t) = u0(x - u t) of a smooth periodic profile ``u0``
    of the given ``period``, before its breaking time: for each point the
    foot of its characteristic, solved with a bracketing root finder."""
    points = np.asarray(x, dtype=float)
    low = float(np.min(u0(np.linspace(0.0, period, 2001))))
    high = float(np.max(u0(np.linspace(0.0, period, 2001))))
    values = np.empty_like(points)
    for i, xi in enumerate(points):
        # u = u0(xi - u t) has its root between the extreme values of u0.
        values[i] = brentq(
            lambda u, xi=xi: u - u0(xi - u * t),
            low - 1e-12,
            high + 1e-12,
            xtol=1e-14,
            rtol=1e-14,
        )
    return values


def riemann_solution(left: float, right: float, xi: ArrayLike) -> Array:
    """The exact solution of the Riemann problem with the states ``left`` and
    ``right``, as a function of xi = (x - x0) / t: a shock at the
    Rankine-Hugoniot speed if left > right, a rarefaction fan u = xi
    between them otherwise."""
    xi = np.asarray(xi, dtype=float)
    if left > right:
        return np.where(xi < shock_speed(left, right), left, right)
    return np.clip(xi, left, right)


def nonconservative_step(u: Array, dt: float, dx: float, boundary: Boundary) -> Array:
    """One upwind step of the form u_t + u u_x = 0: the difference of u is
    taken on the side the wave comes from, and multiplied by the local u.
    It is the same equation where u is smooth, but it is not a difference of
    fluxes, so nothing makes what leaves one cell enter the next."""
    padded = with_ghosts(u, boundary)
    backward = padded[1:-1] - padded[:-2]
    forward = padded[2:] - padded[1:-1]
    return u - dt / dx * u * np.where(u > 0, backward, forward)
