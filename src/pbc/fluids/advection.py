"""Advection and diffusion of a quantity u carried by a flow of constant
speed a > 0 (lesson FL1),

    u_t + a u_x = nu u_xx,

on a grid of spacing dx with steps dt. Two numbers govern a scheme: the
Courant number C = a dt / dx, the fraction of a cell the flow crosses in one
step, and the diffusion number r = nu dt / dx^2.

Each scheme updates a cell from itself and its two neighbours; a boundary
(``pbc.fluids.finite_volume``) supplies the neighbours beyond the ends. The
upwind scheme takes the difference on the side the flow comes from and is
stable for C + 2 r <= 1; the central scheme is stable only for C^2 <= 2 r <= 1,
so without diffusion it is unstable for every C > 0; the Lax-Wendroff scheme
is second order and stable for C^2 + 2 r <= 1. The upwind scheme
behaves as if the equation had the extra diffusion a dx (1 - C) / 2: the
leading term of its modified equation.
"""

from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray

from pbc.fluids.finite_volume import Boundary, periodic, with_ghosts

__all__ = [
    "SCHEMES",
    "amplification",
    "fixed",
    "inflow_outflow",
    "mode_amplitude",
    "modified_diffusion",
    "step",
]

Array = NDArray


def _upwind(left: Array, u: Array, right: Array, courant: float) -> Array:
    return u - courant * (u - left)


def _central(left: Array, u: Array, right: Array, courant: float) -> Array:
    return u - 0.5 * courant * (right - left)


def _lax_wendroff(left: Array, u: Array, right: Array, courant: float) -> Array:
    return (
        u - 0.5 * courant * (right - left) + 0.5 * courant**2 * (right - 2.0 * u + left)
    )


SCHEMES: dict[str, Callable[[Array, Array, Array, float], Array]] = {
    "upwind": _upwind,
    "central": _central,
    "Lax-Wendroff": _lax_wendroff,
}


def step(
    u: Array,
    courant: float,
    scheme: str,
    boundary: Boundary = periodic,
    diffusion: float = 0.0,
) -> Array:
    """One step of ``scheme`` (a key of ``SCHEMES``) at the Courant number
    ``courant``, plus the explicit central diffusion r (u_left - 2 u +
    u_right) for the diffusion number ``diffusion``."""
    padded = with_ghosts(u, boundary)
    left, right = padded[:-2], padded[2:]
    advected = SCHEMES[scheme](left, u, right, courant)
    return advected + diffusion * (left - 2.0 * u + right)


def inflow_outflow(value: float) -> Boundary:
    """The flow enters at the left end with the given ``value`` and leaves
    at the right end, whose ghost copies the last cell."""

    def boundary(u: Array) -> tuple[Array, Array]:
        return np.asarray(value, dtype=u.dtype), u[-1]

    return boundary


def fixed(left: float, right: float) -> Boundary:
    """Fixed values beyond both ends: right for an inflow, wrong for an
    outflow, where it imposes a value the flow does not carry."""

    def boundary(u: Array) -> tuple[Array, Array]:
        return np.asarray(left, dtype=u.dtype), np.asarray(right, dtype=u.dtype)

    return boundary


def amplification(
    scheme: str, courant: float, n: int, diffusion: float = 0.0
) -> NDArray[np.complex128]:
    """The factor by which one step multiplies each Fourier mode of a periodic
    grid of ``n`` cells, measured by applying the step to the mode
    exp(i j theta) itself, theta = 2 pi k / n for k = 0 .. n - 1. A scheme is
    stable when no factor exceeds one in modulus."""
    j = np.arange(n)
    factors = np.empty(n, dtype=complex)
    for k in range(n):
        mode = np.exp(2j * np.pi * k * j / n)
        factors[k] = step(mode, courant, scheme, periodic, diffusion)[0] / mode[0]
    return factors


def mode_amplitude(u: Array, k: int) -> float:
    """The amplitude of the Fourier mode of wavenumber index ``k`` (whole
    waves over the domain) in the periodic profile ``u``."""
    n = len(u)
    j = np.arange(n)
    return float(2.0 / n * np.abs(np.sum(u * np.exp(-2j * np.pi * k * j / n))))


def modified_diffusion(speed: float, dx: float, courant: float) -> float:
    """The numerical diffusion a dx (1 - C) / 2 of the upwind scheme (m^2/s
    for a in m/s and dx in m): the coefficient of u_xx in its modified
    equation, which the scheme adds to the physical diffusion."""
    return speed * dx * (1.0 - courant) / 2.0
