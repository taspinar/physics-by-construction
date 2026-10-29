"""The vibrations of a one-dimensional crystal: a chain of masses joined by
springs, closed into a ring.

A cell of length a holds one mass (the monatomic chain) or two masses m1 and
m2 a half cell apart (the diatomic chain); every spring between neighbours
has the constant K. The equations of motion are M u'' = -C u, with the
force-constant matrix C built spring by spring, and the normal-mode
frequencies are the square roots of the eigenvalues of M^(-1/2) C M^(-1/2).

Bloch's argument gives the same frequencies in closed form. A ring of N
cells allows the wavenumbers k = 2 pi n / (N a), n = 0, ..., N - 1, and
for each of them

    monatomic:  omega = 2 sqrt(K / m) |sin(k a / 2)|,
    diatomic:   omega^2 = K S -+ K sqrt(S^2 - 4 sin^2(k a / 2) / (m1 m2)),
                S = 1 / m1 + 1 / m2,

the minus sign for the acoustic branch, the plus sign for the optical one.
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

Array = NDArray[np.float64]


def ring_masses(cells: int, masses: ArrayLike) -> Array:
    """The masses of a ring of ``cells`` cells, the masses of one cell
    repeated, in the order of the atoms along the ring."""
    if cells < 2:
        raise ValueError("a ring needs at least two cells")
    return np.tile(np.asarray(masses, dtype=float), cells)


def force_constants(atoms: int, spring: float) -> Array:
    """The force-constant matrix C of a ring of ``atoms`` atoms with the
    spring constant ``spring`` between neighbours, added spring by spring:
    the spring between atoms i and j stores K (u_j - u_i)^2 / 2."""
    c = np.zeros((atoms, atoms))
    for i in range(atoms):
        j = (i + 1) % atoms
        c[i, i] += spring
        c[j, j] += spring
        c[i, j] -= spring
        c[j, i] -= spring
    return c


def ring_frequencies(cells: int, masses: ArrayLike, spring: float) -> Array:
    """The normal-mode frequencies of the ring, ascending: the square roots
    of the eigenvalues of M^(-1/2) C M^(-1/2)."""
    m = ring_masses(cells, masses)
    weight = 1 / np.sqrt(m)
    dynamical = weight[:, None] * force_constants(m.size, spring) * weight[None, :]
    squares = np.linalg.eigvalsh(dynamical)
    # The uniform translation has omega^2 = 0, computed at the level of
    # round-off and possibly a tiny negative number.
    return np.sqrt(np.clip(squares, 0.0, None))


def ring_modes(cells: int, masses: ArrayLike, spring: float, a: float = 1.0):
    """The frequencies of the ring and the wavenumber |k| of each mode, in
    [0, pi / a]: the wavenumber at which the cell-to-cell Fourier transform
    of the mode's displacements has its largest power. For display; the
    check of the frequencies needs no wavenumber."""
    m = ring_masses(cells, masses)
    weight = 1 / np.sqrt(m)
    dynamical = weight[:, None] * force_constants(m.size, spring) * weight[None, :]
    squares, vectors = np.linalg.eigh(dynamical)
    per_cell = len(np.atleast_1d(masses))
    displacements = (weight[:, None] * vectors).reshape(cells, per_cell, -1)
    power = np.sum(np.abs(np.fft.fft(displacements, axis=0)) ** 2, axis=1)
    k = 2 * np.pi * np.fft.fftfreq(cells) / a
    return np.sqrt(np.clip(squares, 0.0, None)), np.abs(k[np.argmax(power, axis=0)])


def allowed_wavenumbers(cells: int, a: float = 1.0) -> Array:
    """The wavenumbers a ring of ``cells`` cells allows, 2 pi n / (N a)."""
    return 2 * np.pi * np.arange(cells) / (cells * a)


def monatomic_dispersion(k: ArrayLike, mass: float, spring: float, a: float = 1.0):
    """The closed form omega(k) = 2 sqrt(K / m) |sin(k a / 2)|."""
    return 2 * np.sqrt(spring / mass) * np.abs(np.sin(np.asarray(k) * a / 2))


def diatomic_dispersion(k: ArrayLike, m1: float, m2: float, spring: float, a=1.0):
    """The closed form of the two branches, (acoustic, optical)."""
    s = 1 / m1 + 1 / m2
    root = np.sqrt(s**2 - 4 * np.sin(np.asarray(k) * a / 2) ** 2 / (m1 * m2))
    # S^2 - 4 / (m1 m2) = (1/m1 - 1/m2)^2 >= 0; round-off may dip below the
    # acoustic zero at k = 0.
    acoustic = np.sqrt(np.clip(spring * (s - root), 0.0, None))
    return acoustic, np.sqrt(spring * (s + root))


def closed_form_frequencies(cells: int, masses: ArrayLike, spring: float) -> Array:
    """The closed-form frequencies at every allowed wavenumber of the ring,
    ascending: one branch for one mass per cell, two for two."""
    k = allowed_wavenumbers(cells)
    masses = np.atleast_1d(np.asarray(masses, dtype=float))
    if masses.size == 1:
        values = monatomic_dispersion(k, masses[0], spring)
    elif masses.size == 2:
        values = np.concatenate(diatomic_dispersion(k, *masses, spring))
    else:
        raise ValueError("one or two masses per cell")
    return np.sort(values)


def sound_speed(masses: ArrayLike, spring: float, a: float = 1.0) -> float:
    """The slope of the acoustic branch at k = 0: a sqrt(K / m) for one mass,
    a sqrt(K / (2 (m1 + m2))) for two."""
    masses = np.atleast_1d(np.asarray(masses, dtype=float))
    if masses.size == 1:
        return float(a * np.sqrt(spring / masses[0]))
    return float(a * np.sqrt(spring / (2 * masses.sum())))


def zone_boundary(m1: float, m2: float, spring: float) -> tuple[float, float, float]:
    """The diatomic chain's acoustic top sqrt(2K / m_max) and optical bottom
    sqrt(2K / m_min), both at k = pi / a, and the optical top
    sqrt(2K (1/m1 + 1/m2)) at k = 0."""
    return (
        float(np.sqrt(2 * spring / max(m1, m2))),
        float(np.sqrt(2 * spring / min(m1, m2))),
        float(np.sqrt(2 * spring * (1 / m1 + 1 / m2))),
    )


def group_velocity(k: ArrayLike, mass: float, spring: float, a: float = 1.0):
    """The monatomic chain's group velocity d omega / dk
    = a sqrt(K / m) cos(k a / 2), for 0 <= k <= pi / a."""
    return a * np.sqrt(spring / mass) * np.cos(np.asarray(k) * a / 2)


def phase_velocity(k: ArrayLike, mass: float, spring: float, a: float = 1.0):
    """The monatomic chain's phase velocity omega / k."""
    k = np.asarray(k)
    return monatomic_dispersion(k, mass, spring, a) / k


@dataclass(frozen=True)
class Packet:
    """A wave packet on the monatomic ring: the times, the displacements at
    those times, and the energy-weighted centre (in units of a)."""

    t: Array
    u: Array
    centre: Array


def packet_start(atoms: int, centre: float, width: float, k0: float, mass, spring):
    """A Gaussian packet of carrier wavenumber ``k0`` (units of 1/a) that
    travels towards larger n: the displacements and velocities of the
    complex field g_n exp(i k0 n), each Fourier component given the velocity
    of a wave moving forward at the ring's own frequency, the square root of
    the eigenvalue of the circulant C / m."""
    n = np.arange(atoms)
    field = np.exp(-((n - centre) ** 2) / (2 * width**2) + 1j * k0 * n)
    row = force_constants(atoms, spring)[0] / mass
    omega = np.sqrt(np.clip(np.fft.fft(row).real, 0.0, None))
    u = field.real
    v = np.fft.ifft(-1j * omega * np.fft.fft(field)).real
    return u, v


def energy_density(u: Array, v: Array, mass: float, spring: float) -> Array:
    """The energy of each atom of the ring: its kinetic energy, and half of
    each of its two springs."""
    stretch = 0.5 * spring * (np.roll(u, -1) - u) ** 2
    return 0.5 * mass * v**2 + 0.5 * (stretch + np.roll(stretch, 1))


def verlet_packet(u, v, mass, spring, dt, steps, every) -> Packet:
    """Velocity-Verlet integration of the monatomic ring from (u, v),
    recording every ``every`` steps the displacements and the energy-weighted
    centre of the packet. The packet must stay away from the seam of the
    ring, which the centre does not unwrap."""
    u, v = np.array(u, dtype=float), np.array(v, dtype=float)
    n = np.arange(u.size)

    def acceleration(u):
        return spring * (np.roll(u, -1) - 2 * u + np.roll(u, 1)) / mass

    times, shapes, centres = [], [], []
    a = acceleration(u)
    for step in range(steps + 1):
        if step % every == 0:
            e = energy_density(u, v, mass, spring)
            times.append(step * dt)
            shapes.append(u.copy())
            centres.append(np.sum(n * e) / np.sum(e))
        if step == steps:
            break
        v += 0.5 * dt * a
        u += dt * v
        a = acceleration(u)
        v += 0.5 * dt * a
    return Packet(np.array(times), np.array(shapes), np.array(centres))
