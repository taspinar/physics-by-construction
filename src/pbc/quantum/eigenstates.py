"""The bound states of a particle in a potential: the lowest eigenpairs of
the finite-difference Hamiltonian, and the harmonic oscillator they are
checked against.

The Hamiltonian is that of ``pbc.quantum.schrodinger``: the three-point
second difference on the interior nodes between two walls, with the
potential on the diagonal. Its eigenvalues are the energies of the grid; a
wall far enough out that the wave function has decayed there does not change
them by more than round-off.

The oscillator V = m omega^2 x^2 / 2 is written with hbar = m = omega = 1:
the energies are E_n = n + 1/2, the eigenfunctions the Hermite functions. The
three-point difference adds -(h^2 / 12) d^4/dx^4 to the second derivative,
so to first order each level moves by -(h^2 / 24) <p^4>_n, and for the
oscillator <p^4>_n = (3/4)(2 n^2 + 2 n + 1):

    E_n(h) - E_n = -(h^2 / 32)(2 n^2 + 2 n + 1) + O(h^4).
"""

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.linalg import eigh_tridiagonal

from pbc.quantum.schrodinger import hamiltonian

Array = NDArray[np.float64]


def eigenstates(
    potential: ArrayLike, h: float, count: int, kinetic: float = 0.5
) -> tuple[Array, Array]:
    """The ``count`` lowest energies and eigenfunctions of the grid.

    Each eigenfunction (a column) has h sum psi^2 = 1 and the sign that makes
    its rightmost lobe positive, the sign of the Hermite functions.
    """
    diagonal, off = hamiltonian(potential, h, kinetic)
    if not 1 <= count <= diagonal.size:
        raise ValueError(f"count must be between 1 and {diagonal.size}")
    energies, vectors = eigh_tridiagonal(
        diagonal, off, select="i", select_range=(0, count - 1)
    )
    vectors = vectors / np.sqrt(h)
    for j in range(count):
        column = vectors[:, j]
        last = np.nonzero(np.abs(column) > 1e-3 * np.abs(column).max())[0][-1]
        if column[last] < 0:
            vectors[:, j] = -column
    return energies, vectors


def oscillator_potential(x: ArrayLike) -> Array:
    """V = x^2 / 2, with hbar = m = omega = 1."""
    return 0.5 * np.asarray(x, dtype=float) ** 2


def oscillator_energy(n: ArrayLike) -> Array:
    """E_n = n + 1/2, in units of hbar omega."""
    return np.asarray(n, dtype=float) + 0.5


def hermite_functions(count: int, x: ArrayLike) -> Array:
    """The first ``count`` eigenfunctions of the oscillator, one row each, by
    the stable recurrence

        psi_0 = pi^(-1/4) exp(-x^2 / 2),  psi_1 = sqrt(2) x psi_0,
        psi_(n+1) = sqrt(2 / (n + 1)) x psi_n - sqrt(n / (n + 1)) psi_(n-1).
    """
    x = np.asarray(x, dtype=float)
    rows = np.empty((count, x.size))
    rows[0] = np.pi**-0.25 * np.exp(-(x**2) / 2)
    if count > 1:
        rows[1] = np.sqrt(2) * x * rows[0]
    for n in range(1, count - 1):
        rows[n + 1] = (
            np.sqrt(2 / (n + 1)) * x * rows[n] - np.sqrt(n / (n + 1)) * rows[n - 1]
        )
    return rows


def oscillator_shift(n: ArrayLike, h: float) -> Array:
    """The predicted leading error of the grid's level n,
    -(h^2 / 32)(2 n^2 + 2 n + 1)."""
    n = np.asarray(n, dtype=float)
    return -(h**2) / 32 * (2 * n**2 + 2 * n + 1)


def quartic_moment(n: ArrayLike) -> Array:
    """<x^4>_n = (3/4)(2 n^2 + 2 n + 1) of the oscillator's level n: the
    first-order shift of the level per unit strength of a perturbation x^4."""
    n = np.asarray(n, dtype=float)
    return 0.75 * (2 * n**2 + 2 * n + 1)


def box_energy(n: ArrayLike, length: float, kinetic: float = 0.5) -> Array:
    """The level n = 1, 2, ... of an infinite square well of ``length``,
    kinetic (n pi / L)^2."""
    return kinetic * (np.pi * np.asarray(n, dtype=float) / length) ** 2
