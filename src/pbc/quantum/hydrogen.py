"""The levels of hydrogen and the lines of its Balmer series.

The model of the atomic spectroscopy lab, stated here and not derived by an
earlier lesson of the course (source: R. Fitzpatrick, *Quantum Mechanics*,
"Hydrogen Atom" and "Rydberg Formula"). An electron and a proton bound by the
Coulomb potential are one particle of the reduced mass

    mu = m_e m_p / (m_e + m_p)

in the potential -e^2 / (4 pi eps0 r). With psi = R(r) Y_lm and u = r R the
radial equation is, in atomic units (hbar = m_e = e^2 / 4 pi eps0 = 1,
lengths in Bohr radii a_0, energies in Hartree),

    -(1 / 2 mu) u'' + (l (l + 1) / (2 mu r^2) - 1 / r) u = E u,   u(0) = 0,

and its bound states have the energies

    E_n = -(mu / m_e) / (2 n^2),   n = l + 1, l + 2, ...

independent of l. A fall from level n to level 2 emits at the vacuum
wavenumber 1 / lambda = R_H (1/4 - 1/n^2), with R_H = R_inf mu / m_e =
R_inf / (1 + m_e / m_p): the Balmer series, with the Rydberg constant of
hydrogen. The model leaves out the electron's spin and relativity (the fine
structure, a few parts in 1e5 of the Balmer wavelengths) and the Lamb shift.

``radial_levels`` checks the energies with the grid of the quantum course:
the Hamiltonian of ``pbc.quantum.schrodinger`` (the three-point second
difference between two walls), diagonalised by ``pbc.quantum.eigenstates``,
on the radial equation, with a wall at r = 0 (u = 0) and one at ``r_max``.
"""

import numpy as np
from numpy.typing import ArrayLike, NDArray

from pbc.quantum.eigenstates import eigenstates
from pbc.quantum.schrodinger import line

Array = NDArray[np.float64]


def reduced_mass_ratio(me_over_mp: float) -> float:
    """mu / m_e = 1 / (1 + m_e / m_p)."""
    return 1.0 / (1.0 + me_over_mp)


def level(n: ArrayLike, mass_ratio: float = 1.0) -> Array:
    """E_n = -(mu / m_e) / (2 n^2) in Hartree; ``mass_ratio`` is mu / m_e
    (1 for an infinitely heavy nucleus)."""
    n = np.asarray(n, dtype=float)
    if np.any(n < 1):
        raise ValueError("n starts at 1")
    return -mass_ratio / (2.0 * n**2)


def rydberg_hydrogen(r_inf: float, me_over_mp: float) -> float:
    """R_H = R_inf mu / m_e: the Rydberg constant of a nucleus of finite mass."""
    return r_inf * reduced_mass_ratio(me_over_mp)


def balmer_wavenumber(n: ArrayLike, rydberg: float) -> Array:
    """1 / lambda = R (1/4 - 1/n^2) of the fall from level n to level 2, in the
    unit of ``rydberg``."""
    n = np.asarray(n, dtype=float)
    if np.any(n <= 2):
        raise ValueError("a Balmer line starts above level 2")
    return rydberg * (0.25 - 1.0 / n**2)


def radial_levels(
    ell: int, count: int, r_max: float, n_cells: int, mass_ratio: float = 1.0
) -> Array:
    """The ``count`` lowest energies [Hartree] of the radial equation for the
    angular momentum ``ell`` on ``n_cells`` cells of (0, r_max) [a_0]: the
    Coulomb and centrifugal potential on the interior nodes, the kinetic
    coefficient 1 / (2 mu), u = 0 at both ends."""
    if ell < 0 or count < 1:
        raise ValueError("ell >= 0 and count >= 1")
    grid = line(0.0, r_max, n_cells)
    r = grid.x
    potential = ell * (ell + 1) / (2.0 * mass_ratio * r**2) - 1.0 / r
    energies, _ = eigenstates(potential, grid.h, count, kinetic=0.5 / mass_ratio)
    return energies


def richardson(coarse: ArrayLike, fine: ArrayLike, order: int = 2) -> Array:
    """The extrapolation (2^p fine - coarse) / (2^p - 1) of two results of a
    method of order p on steps h and h / 2: it removes the h^p term."""
    factor = 2.0**order
    return (factor * np.asarray(fine, dtype=float) - np.asarray(coarse)) / (
        factor - 1.0
    )
