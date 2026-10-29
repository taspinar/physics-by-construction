"""The energy bands of an electron in a one-dimensional crystal, in the
tight-binding model.

The electron sits on the sites of a chain and hops to a neighbouring site
with the amplitude -t. A cell of length a holds one site of energy eps0
(the one-band chain) or two sites a half cell apart, of energies +Delta and
-Delta (the two-site chain). The Hamiltonian of a ring of N cells is built
hop by hop in real space; its eigenvalues are the energies of the ring.

Bloch's argument gives them in closed form at the allowed wavenumbers
k = 2 pi n / (N a):

    one band:   E(k) = eps0 - 2 t cos(k a),
    two sites:  E(k) = -+ sqrt(Delta^2 + 4 t^2 cos^2(k a / 2)).

Units: hbar = a = 1 and t = 1 in the lesson, so energies are in units of t
and times in units of hbar / t; the functions take t and a as arguments.
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

Array = NDArray[np.float64]


def ring_hamiltonian(cells: int, onsite: ArrayLike, hopping: float) -> Array:
    """The Hamiltonian of a ring of ``cells`` cells whose sites have the
    energies ``onsite`` (one or two per cell), added hop by hop: -t between
    each pair of neighbouring sites."""
    if cells < 2:
        raise ValueError("a ring needs at least two cells")
    energies = np.tile(np.asarray(onsite, dtype=float), cells)
    sites = energies.size
    h = np.diag(energies)
    for i in range(sites):
        j = (i + 1) % sites
        h[i, j] -= hopping
        h[j, i] -= hopping
    return h


def ring_energies(cells: int, onsite: ArrayLike, hopping: float) -> Array:
    """The energies of the ring, ascending."""
    return np.linalg.eigvalsh(ring_hamiltonian(cells, onsite, hopping))


def allowed_wavenumbers(cells: int, a: float = 1.0) -> Array:
    """The wavenumbers a ring of ``cells`` cells allows, 2 pi n / (N a), in
    the zone (-pi / a, pi / a]."""
    n = np.arange(cells)
    n = np.where(n > cells // 2, n - cells, n)
    return 2 * np.pi * n / (cells * a)


def one_band(k: ArrayLike, eps0: float, hopping: float, a: float = 1.0):
    """The closed form E(k) = eps0 - 2 t cos(k a)."""
    return eps0 - 2 * hopping * np.cos(np.asarray(k) * a)


def two_site_bands(k: ArrayLike, delta: float, hopping: float, a: float = 1.0):
    """The closed form of the two bands, (lower, upper):
    -+ sqrt(Delta^2 + 4 t^2 cos^2(k a / 2))."""
    root = np.sqrt(delta**2 + 4 * hopping**2 * np.cos(np.asarray(k) * a / 2) ** 2)
    return -root, root


def closed_form_energies(cells: int, onsite: ArrayLike, hopping: float) -> Array:
    """The closed-form energies at every allowed wavenumber, ascending. Two
    sites per cell must have the energies +Delta and -Delta."""
    k = allowed_wavenumbers(cells)
    onsite = np.atleast_1d(np.asarray(onsite, dtype=float))
    if onsite.size == 1:
        values = one_band(k, onsite[0], hopping)
    elif onsite.size == 2 and onsite[0] == -onsite[1]:
        values = np.concatenate(two_site_bands(k, onsite[0], hopping))
    else:
        raise ValueError("one site, or two of energies +Delta and -Delta")
    return np.sort(values)


def counting(energy: ArrayLike, eps0: float, hopping: float) -> Array:
    """The closed-form fraction of the one-band chain's states below
    ``energy``, arccos((eps0 - E) / (2 t)) / pi, 0 below the band and 1
    above it."""
    x = np.clip((eps0 - np.asarray(energy, dtype=float)) / (2 * hopping), -1, 1)
    return np.arccos(x) / np.pi


def effective_mass(hopping: float, a: float = 1.0, hbar: float = 1.0) -> float:
    """The mass of the band bottom, E ~ E(0) + hbar^2 k^2 / (2 m*):
    m* = hbar^2 / (2 t a^2)."""
    return hbar**2 / (2 * hopping * a**2)


def filled(energies: ArrayLike, electrons: int) -> tuple[float, float]:
    """The highest occupied and the lowest empty level when ``electrons``
    electrons fill the levels from the bottom, two per level (spin)."""
    e = np.sort(np.asarray(energies, dtype=float))
    if electrons % 2 or not 0 < electrons < 2 * e.size:
        raise ValueError("an even number of electrons that leaves an empty level")
    occupied = electrons // 2
    return float(e[occupied - 1]), float(e[occupied])


def chain_hamiltonian(sites: int, hopping: float, force: float, a: float = 1.0):
    """The Hamiltonian of an open chain of ``sites`` one-band sites
    (eps0 = 0) with a uniform force F along the chain: the potential energy
    -F x_n at x_n = n a."""
    x = a * np.arange(sites)
    h = np.diag(-force * x)
    h -= hopping * (np.eye(sites, k=1) + np.eye(sites, k=-1))
    return h


def gaussian_packet(sites: int, centre: float, width: float, k0: float = 0.0):
    """A normalised Gaussian packet, |psi_n|^2 of standard deviation
    ``width`` sites about ``centre``, with the carrier wavenumber ``k0``."""
    n = np.arange(sites)
    psi = np.exp(-((n - centre) ** 2) / (4 * width**2) + 1j * k0 * n)
    return psi / np.linalg.norm(psi)


def translation(psi: ArrayLike) -> complex:
    """The expectation <psi| T |psi> of the one-site translation
    T |n> = |n + 1>: sum over n of conj(psi_(n+1)) psi_n."""
    psi = np.asarray(psi)
    return complex(np.vdot(psi[1:], psi[:-1]))


@dataclass(frozen=True)
class Evolution:
    """A state propagated exactly: the times, the states at those times
    (one row each), and the centre <x> (units of a)."""

    t: Array
    psi: NDArray[np.complex128]
    centre: Array


def propagate(h: Array, psi0: ArrayLike, times: ArrayLike, a: float = 1.0):
    """psi(t) = exp(-i H t / hbar) psi0 with hbar = 1, by the
    eigendecomposition of the Hermitian H, at each of ``times``."""
    energies, vectors = np.linalg.eigh(h)
    coefficients = vectors.conj().T @ np.asarray(psi0)
    times = np.asarray(times, dtype=float)
    phases = np.exp(-1j * np.outer(times, energies))
    psi = (phases * coefficients) @ vectors.T
    x = a * np.arange(h.shape[0])
    return Evolution(times, psi, np.sum(np.abs(psi) ** 2 * x, axis=1))


def bloch_centre(t: ArrayLike, x0: float, shift: complex, hopping, force, a=1.0):
    """The closed-form centre of a packet on the infinite chain under the
    force F: x0 + (2 t / F) (Re<T> - Re(<T> exp(-i omega_B t))), with
    omega_B = F a / hbar and <T> the initial ``shift`` (``translation``).

    It follows from two exact statements: T(t) = exp(-i omega_B t) T(0) in
    the Heisenberg picture, because [-F x, T] = -F a T and the hopping
    commutes with T; and <H> = -t (<T> + <T>*) - F <x> is conserved."""
    t = np.asarray(t, dtype=float)
    omega = force * a
    return x0 + 2 * hopping / force * (
        shift.real - (shift * np.exp(-1j * omega * t)).real
    )
