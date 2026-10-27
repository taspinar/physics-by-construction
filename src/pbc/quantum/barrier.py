"""Scattering of a particle by a potential barrier in one dimension.

A particle of energy E > 0 comes from the left. Outside the barrier, where
V = 0, the stationary wave function is a sum of plane waves of wavenumber
k = sqrt(E / kinetic), kinetic = hbar^2 / 2m:

    psi = A exp(i k x) + B exp(-i k x)   left of the barrier,
    psi = exp(i k x)                     right of it (only a transmitted wave).

The transmission and reflection coefficients are T = 1 / |A|^2 and
R = |B|^2 / |A|^2, and the conservation of the probability current gives
R + T = 1.

Two independent computations of T:

- ``transmission``: the closed form for a rectangular barrier of height V0
  and width a, from matching psi and psi' at its two edges;
- ``scattering``: the stationary equation psi'' = (V - E) psi / kinetic
  integrated across the barrier by the classical fourth-order Runge-Kutta
  method, from the transmitted wave on the right to the left edge, where
  psi and psi' give A and B. It needs no closed form and takes any potential
  that is smooth on the barrier and zero outside it.

The units are those of an electron in eV, nm, and fs (``KINETIC``,
``HBAR``), from the CODATA values of ``scipy.constants``.
"""

from collections.abc import Callable

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import constants

Array = NDArray[np.float64]

#: hbar^2 / 2 m_e in eV nm^2.
KINETIC = constants.hbar**2 / (2 * constants.m_e) / constants.e * 1e18
#: hbar in eV fs.
HBAR = constants.hbar / constants.e * 1e15


def wavenumber(energy: ArrayLike, kinetic: float = KINETIC) -> Array:
    """k = sqrt(E / kinetic), in 1/nm for an electron in eV."""
    return np.sqrt(np.asarray(energy, dtype=float) / kinetic)


def transmission(
    energy: ArrayLike, height: float, width: ArrayLike, kinetic: float = KINETIC
) -> Array:
    """The closed-form transmission coefficient of a rectangular barrier.

    Below the top, with kappa = sqrt((V0 - E) / kinetic),

        T = 1 / (1 + V0^2 sinh^2(kappa a) / (4 E (V0 - E))),

    above it the same with sin and q = sqrt((E - V0) / kinetic), and at the
    top T = 1 / (1 + V0 a^2 / (4 kinetic)), the limit of both.
    """
    e = np.asarray(energy, dtype=float)
    width = np.asarray(width, dtype=float)
    if np.any(e <= 0) or height <= 0 or np.any(width <= 0):
        raise ValueError("the energy, the height, and the width must be positive")
    gap = height - e
    with np.errstate(invalid="ignore", divide="ignore"):
        below = np.sinh(np.sqrt(np.abs(gap) / kinetic) * width) ** 2
        above = np.sin(np.sqrt(np.abs(gap) / kinetic) * width) ** 2
        factor = np.where(gap > 0, below, above) / (4 * e * np.abs(gap))
    top = width**2 / (4 * kinetic * height)
    factor = np.where(gap == 0, top, factor)
    return 1.0 / (1.0 + height**2 * factor)


def rectangle(height: float) -> Callable[[ArrayLike], Array]:
    """The potential of a rectangular barrier of ``height`` on its own
    width: constant, for ``scattering``."""

    def potential(x: ArrayLike) -> Array:
        return np.full_like(np.asarray(x, dtype=float), height)

    return potential


def on_grid(x: ArrayLike, h: float, height: float, width: float) -> Array:
    """The rectangular barrier on the nodes ``x``, ``h`` apart, as the mean of
    the potential over the cell of each node: ``height`` inside, half of it on
    a node at an edge. The sum h sum V is then exactly height times width, and
    the barrier the grid sees is as wide as the real one."""
    x = np.asarray(x, dtype=float)
    inside = np.minimum(x + h / 2, width) - np.maximum(x - h / 2, 0.0)
    return height * np.clip(inside, 0.0, h) / h


def scattering(
    energy: ArrayLike,
    potential: Callable[[ArrayLike], Array],
    width: float,
    n_steps: int,
    kinetic: float = KINETIC,
) -> tuple[Array, Array]:
    """T and R of the barrier ``potential`` on [0, ``width``], zero outside,
    by ``n_steps`` Runge-Kutta steps across it, for every energy at once.

    The state (psi, psi') starts as the transmitted wave exp(i k x) at the
    right edge and is integrated leftwards; at the left edge,
    A = (psi + psi' / i k) / 2 and B = (psi - psi' / i k) / 2.
    """
    e = np.atleast_1d(np.asarray(energy, dtype=float))
    if np.any(e <= 0) or width <= 0 or n_steps < 1:
        raise ValueError("positive energies and width, and at least one step")
    k = wavenumber(e, kinetic)
    step = -width / n_steps

    def slope(x: float, psi: NDArray, dpsi: NDArray) -> tuple[NDArray, NDArray]:
        return dpsi, (potential(np.array(x)) - e) / kinetic * psi

    psi = np.exp(1j * k * width)
    dpsi = 1j * k * psi
    x = width
    for _ in range(n_steps):
        k1 = slope(x, psi, dpsi)
        k2 = slope(x + step / 2, psi + step / 2 * k1[0], dpsi + step / 2 * k1[1])
        k3 = slope(x + step / 2, psi + step / 2 * k2[0], dpsi + step / 2 * k2[1])
        k4 = slope(x + step, psi + step * k3[0], dpsi + step * k3[1])
        psi = psi + step / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        dpsi = dpsi + step / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        x += step
    incoming = 0.5 * (psi + dpsi / (1j * k))
    reflected = 0.5 * (psi - dpsi / (1j * k))
    return 1.0 / np.abs(incoming) ** 2, np.abs(reflected / incoming) ** 2


def packet_transmission(
    centre_k: float,
    width: float,
    height: float,
    barrier: float,
    kinetic: float = KINETIC,
) -> float:
    """The probability that a Gaussian packet of position spread ``width``
    and mean wavenumber ``centre_k`` passes a rectangular barrier: T(E(k))
    averaged over the packet's distribution of k, a normal distribution of
    standard deviation 1 / (2 width). Wavenumbers that are not positive
    carry a weight below 1e-12 for the packets used here and are left out."""
    spread = 1 / (2 * width)
    k = np.linspace(
        max(centre_k - 10 * spread, 1e-6 * centre_k), centre_k + 10 * spread, 20001
    )
    weight = np.exp(-((k - centre_k) ** 2) / (2 * spread**2)) / (
        np.sqrt(2 * np.pi) * spread
    )
    return float(
        np.trapezoid(weight * transmission(kinetic * k**2, height, barrier, kinetic), k)
    )
