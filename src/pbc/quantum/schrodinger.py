"""The time-dependent Schrödinger equation in one dimension, on a grid.

    i hbar dpsi/dt = H psi,    H = -(hbar^2 / 2m) d^2/dx^2 + V(x).

The Hamiltonian is the matrix of the three-point second difference, the
centred difference of the wave equation (W1), on the interior nodes of a
line with a wall at each end (psi = 0 there), with the potential on the
diagonal. It is real, symmetric, and tridiagonal, and is kept as its
diagonal and its off-diagonal.

Two steps in time:

- Crank-Nicolson, (1 + i dt H / 2 hbar) psi[n+1] = (1 - i dt H / 2 hbar) psi[n].
  Each eigenmode of energy E is multiplied by
  (1 - i dt E / 2 hbar) / (1 + i dt E / 2 hbar), of modulus one: the step is
  unitary and keeps the norm, and it is second order in dt.
- Explicit Euler, psi[n+1] = (1 - i dt H / hbar) psi[n]. Each eigenmode is
  multiplied by 1 - i dt E / hbar, of modulus above one: the norm grows.

The coefficient ``kinetic`` is hbar^2 / 2m. The default units are
hbar = m = 1 (``kinetic`` = 1/2, ``hbar`` = 1); the tunnelling lesson
passes the values of an electron in eV, nm, and fs.
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.linalg import eigh_tridiagonal
from scipy.sparse import diags
from scipy.sparse.linalg import splu

Array = NDArray[np.float64]
ComplexArray = NDArray[np.complex128]


@dataclass(frozen=True)
class Line:
    """The interior nodes ``x`` of a line between two walls, ``h`` apart."""

    x: Array
    h: float


@dataclass(frozen=True)
class Evolution:
    """The wave function at the recorded times: ``psi[j]`` at the time
    ``t[j]``, one column per node."""

    t: Array
    psi: ComplexArray


def line(x_min: float, x_max: float, n_cells: int) -> Line:
    """The ``n_cells - 1`` interior nodes of ``[x_min, x_max]``; the walls at
    the two ends are not unknowns, psi is zero there."""
    if x_max <= x_min or n_cells < 3:
        raise ValueError("the line needs x_max > x_min and at least 3 cells")
    h = (x_max - x_min) / n_cells
    return Line(x_min + h * np.arange(1, n_cells), h)


def hamiltonian(
    potential: ArrayLike, h: float, kinetic: float = 0.5
) -> tuple[Array, Array]:
    """The diagonal and the off-diagonal of H = -kinetic d^2/dx^2 + V with the
    three-point second difference and a wall beyond each end node."""
    v = np.asarray(potential, dtype=float)
    if v.ndim != 1 or v.size < 2 or h <= 0 or kinetic <= 0:
        raise ValueError("the potential is a vector of nodes; h and kinetic > 0")
    return 2.0 * kinetic / h**2 + v, np.full(v.size - 1, -kinetic / h**2)


def apply(diagonal: Array, off: Array, psi: ArrayLike) -> ComplexArray:
    """H psi for the tridiagonal H of ``hamiltonian``."""
    psi = np.asarray(psi)
    result = diagonal * psi
    result[:-1] += off * psi[1:]
    result[1:] += off * psi[:-1]
    return result


def _record(steps: int, every: int) -> set[int]:
    if steps < 1 or every < 1:
        raise ValueError("n_steps and every must be at least 1")
    return {*range(every, steps + 1, every), steps}


def crank_nicolson(
    psi0: ArrayLike,
    potential: ArrayLike,
    *,
    h: float,
    dt: float,
    n_steps: int,
    every: int = 1,
    kinetic: float = 0.5,
    hbar: float = 1.0,
) -> Evolution:
    """Advance ``psi0`` by ``n_steps`` Crank-Nicolson steps of ``dt``.

    The matrix 1 + i dt H / 2 hbar is factorised once; every step is one
    product with H and one solve. The wave function is recorded at the start,
    after every ``every`` steps, and after the last one.
    """
    psi = np.array(psi0, dtype=complex)
    diagonal, off = hamiltonian(potential, h, kinetic)
    if psi.shape != diagonal.shape:
        raise ValueError("psi0 and the potential must have the same length")
    a = 0.5j * dt / hbar
    implicit = splu(
        diags([a * off, 1.0 + a * diagonal, a * off], [-1, 0, 1], format="csc")
    )
    recorded = _record(n_steps, every)
    times, records = [0.0], [psi.copy()]
    for step in range(1, n_steps + 1):
        psi = implicit.solve(psi - a * apply(diagonal, off, psi))
        if step in recorded:
            times.append(step * dt)
            records.append(psi.copy())
    return Evolution(np.array(times), np.array(records))


def explicit_euler(
    psi0: ArrayLike,
    potential: ArrayLike,
    *,
    h: float,
    dt: float,
    n_steps: int,
    every: int = 1,
    kinetic: float = 0.5,
    hbar: float = 1.0,
) -> Evolution:
    """Advance ``psi0`` by ``n_steps`` explicit Euler steps of ``dt``: the
    counter-example, which does not keep the norm."""
    psi = np.array(psi0, dtype=complex)
    diagonal, off = hamiltonian(potential, h, kinetic)
    if psi.shape != diagonal.shape:
        raise ValueError("psi0 and the potential must have the same length")
    recorded = _record(n_steps, every)
    times, records = [0.0], [psi.copy()]
    for step in range(1, n_steps + 1):
        psi = psi - 1j * dt / hbar * apply(diagonal, off, psi)
        if step in recorded:
            times.append(step * dt)
            records.append(psi.copy())
    return Evolution(np.array(times), np.array(records))


def euler_norm(
    psi0: ArrayLike,
    potential: ArrayLike,
    *,
    h: float,
    dt: float,
    steps: ArrayLike,
    kinetic: float = 0.5,
    hbar: float = 1.0,
) -> Array:
    """The norm that explicit Euler gives after each number of ``steps``,
    predicted from the spectrum of H: with psi0 = sum c_k phi_k,

        norm = h sum |c_k|^2 (1 + (dt E_k / hbar)^2)^n.
    """
    diagonal, off = hamiltonian(potential, h, kinetic)
    energies, vectors = eigh_tridiagonal(diagonal, off)
    weights = np.abs(vectors.T @ np.asarray(psi0, dtype=complex)) ** 2
    growth = 1.0 + (dt * energies / hbar) ** 2
    n = np.asarray(steps, dtype=float)
    return h * np.array([np.sum(weights * growth**k) for k in n.ravel()]).reshape(
        n.shape
    )


def norm(psi: ArrayLike, h: float) -> Array:
    """The total probability h sum |psi|^2, along the last axis."""
    return h * np.sum(np.abs(np.asarray(psi)) ** 2, axis=-1)


def mean_position(x: ArrayLike, psi: ArrayLike, h: float) -> Array:
    """<x> = h sum x |psi|^2 / norm, along the last axis."""
    density = np.abs(np.asarray(psi)) ** 2
    return h * np.sum(np.asarray(x) * density, axis=-1) / norm(psi, h)


def spread(x: ArrayLike, psi: ArrayLike, h: float) -> Array:
    """The standard deviation of the position, along the last axis."""
    x = np.asarray(x)
    density = np.abs(np.asarray(psi)) ** 2
    mean = mean_position(x, psi, h)
    second = h * np.sum(x**2 * density, axis=-1) / norm(psi, h)
    return np.sqrt(second - mean**2)


def mean_momentum(psi: ArrayLike, h: float, hbar: float = 1.0) -> Array:
    """<p> = hbar Im(h sum conj(psi) dpsi/dx) / norm, with the centred
    difference for the derivative, along the last axis."""
    psi = np.asarray(psi)
    slope = np.zeros_like(psi)
    slope[..., 1:-1] = (psi[..., 2:] - psi[..., :-2]) / (2 * h)
    return hbar * np.imag(h * np.sum(np.conj(psi) * slope, axis=-1)) / norm(psi, h)


def gaussian_packet(
    x: ArrayLike, *, centre: float, width: float, wavenumber: float
) -> ComplexArray:
    """The Gaussian packet (2 pi sigma^2)^(-1/4) exp(-(x - x0)^2 / 4 sigma^2
    + i k0 (x - x0)), normalised on the whole line; ``width`` is sigma, the
    standard deviation of the position."""
    if width <= 0:
        raise ValueError("the width must be positive")
    x = np.asarray(x, dtype=float)
    return (2 * np.pi * width**2) ** -0.25 * np.exp(
        -((x - centre) ** 2) / (4 * width**2) + 1j * wavenumber * (x - centre)
    )


def free_packet(
    x: ArrayLike,
    t: float,
    *,
    centre: float,
    width: float,
    wavenumber: float,
    kinetic: float = 0.5,
    hbar: float = 1.0,
) -> ComplexArray:
    """The exact free evolution of ``gaussian_packet`` on the whole line.

    With tau = hbar t / m = 2 kinetic t / hbar and s = sigma^2 + i tau / 2,

        psi = (2 pi)^(-1/4) sigma^(1/2) s^(-1/2)
              exp(-(x - x0 - k0 tau)^2 / 4 s + i k0 (x - x0) - i k0^2 tau / 2).
    """
    x = np.asarray(x, dtype=float)
    tau = 2 * kinetic * t / hbar
    s = width**2 + 0.5j * tau
    return (
        (2 * np.pi) ** -0.25
        * np.sqrt(width)
        / np.sqrt(s)
        * np.exp(
            -((x - centre - wavenumber * tau) ** 2) / (4 * s)
            + 1j * wavenumber * (x - centre)
            - 0.5j * wavenumber**2 * tau
        )
    )


def free_spread(
    t: ArrayLike, *, width: float, kinetic: float = 0.5, hbar: float = 1.0
) -> Array:
    """The width of the free packet, sigma sqrt(1 + (hbar t / 2 m sigma^2)^2)."""
    tau = 2 * kinetic * np.asarray(t, dtype=float) / hbar
    return width * np.sqrt(1 + (tau / (2 * width**2)) ** 2)


def free_energy(k: ArrayLike, kinetic: float = 0.5) -> Array:
    """The energy of a plane wave, hbar^2 k^2 / 2m: the free-particle
    dispersion hbar omega = hbar^2 k^2 / 2m."""
    return kinetic * np.asarray(k, dtype=float) ** 2


def grid_energy(k: ArrayLike, h: float, kinetic: float = 0.5) -> Array:
    """The energy of a mode of wavenumber ``k`` under the three-point second
    difference, 2 kinetic (1 - cos k h) / h^2; it tends to ``free_energy``
    as k h goes to zero."""
    return 2 * kinetic * (1 - np.cos(np.asarray(k, dtype=float) * h)) / h**2


def crank_nicolson_frequency(energy: ArrayLike, dt: float, hbar: float = 1.0) -> Array:
    """The angular frequency with which Crank-Nicolson turns the phase of a
    mode of ``energy``: 2 arctan(E dt / 2 hbar) / dt, which tends to E / hbar
    as dt goes to zero."""
    return 2 * np.arctan(np.asarray(energy, dtype=float) * dt / (2 * hbar)) / dt


def box_mode(grid: Line, j: int) -> Array:
    """The ``j``-th sine mode of the line between its walls, sin(j pi s / L)
    with s the distance from the left wall: an exact eigenvector of the
    three-point second difference, of wavenumber j pi / L."""
    length = grid.h * (grid.x.size + 1)
    left = grid.x[0] - grid.h
    return np.sin(j * np.pi * (grid.x - left) / length)


def box_wavenumber(grid: Line, j: int) -> float:
    return j * np.pi / (grid.h * (grid.x.size + 1))


def measured_frequency(evolution: Evolution, mode: ArrayLike) -> float:
    """The angular frequency of the phase of the projection of the evolved
    wave function on ``mode``, from its first two records."""
    mode = np.asarray(mode)
    first, second = (np.vdot(mode, psi) for psi in evolution.psi[:2])
    return float(-np.angle(second / first) / (evolution.t[1] - evolution.t[0]))
