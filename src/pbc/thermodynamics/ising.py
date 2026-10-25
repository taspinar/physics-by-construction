"""The Ising model on a square lattice with periodic boundaries.

A spin s = +1 or -1 sits on every site of an L x L lattice, and the energy is
E = -J sum s_i s_j over the pairs of nearest neighbours, with no external
field. Energies and temperatures are in units of J and J / k_B, so that
beta = 1 / T. Every pair is counted once: the lattice has 2 L^2 bonds.

A batch of lattices has the shape ``(B, L, L)`` with spins of type int8; every
lattice of the batch has its own temperature. The Metropolis sweep updates the
two sublattices of a checkerboard in turn, so that no two neighbours change in
the same half-sweep and the whole sublattice is one array operation.
"""

from math import log, sqrt

import numpy as np
from numpy.typing import NDArray

Array = NDArray[np.float64]
Spins = NDArray[np.int8]


def critical_temperature() -> float:
    """Onsager's critical temperature 2 / ln(1 + sqrt 2) of the infinite
    square lattice (units of J / k_B)."""
    return 2.0 / log(1.0 + sqrt(2.0))


def onsager_magnetisation(temperature: Array) -> Array:
    """The spontaneous magnetisation per spin of the infinite lattice,
    (1 - sinh(2 / T)^-4)^(1/8) below the critical temperature and zero above
    it (Onsager, published by Yang)."""
    t = np.atleast_1d(np.asarray(temperature, dtype=np.float64))
    inner = 1.0 - np.sinh(2.0 / t) ** -4.0
    return np.where(t < critical_temperature(), np.clip(inner, 0.0, None) ** 0.125, 0.0)


def neighbour_sum(spins: Spins) -> Spins:
    """The sum of the four neighbours of every site, with periodic boundaries
    (between -4 and 4, so int8 holds it)."""
    return (
        np.roll(spins, 1, axis=-1)
        + np.roll(spins, -1, axis=-1)
        + np.roll(spins, 1, axis=-2)
        + np.roll(spins, -1, axis=-2)
    )


def energy(spins: Spins) -> Array:
    """The energy -sum s_i s_j of each lattice of a batch, each bond once (units
    of J)."""
    s = spins.astype(np.int64)
    bonds = s * np.roll(s, -1, axis=-1) + s * np.roll(s, -1, axis=-2)
    return -bonds.sum(axis=(-2, -1)).astype(np.float64)


def magnetisation(spins: Spins) -> Array:
    """The magnetisation per spin, the mean of the spins, of each lattice."""
    return spins.mean(axis=(-2, -1), dtype=np.float64)


def checkerboard(size: int) -> tuple[NDArray[np.bool_], NDArray[np.bool_]]:
    """The two sublattices of an L x L checkerboard. For an even L no site has
    a neighbour of its own sublattice, also across the periodic boundary."""
    if size < 2 or size % 2:
        raise ValueError("the lattice size must be even and at least 2")
    i, j = np.indices((size, size))
    black = (i + j) % 2 == 0
    return black, ~black


def metropolis_sweep(spins: Spins, beta: Array, rng: np.random.Generator) -> None:
    """One Metropolis sweep of every lattice of the batch, in place.

    Each half-sweep proposes to flip every spin of one sublattice. A flip
    changes the energy by dE = 2 s h, with h the sum of the neighbours, and is
    accepted with probability min(1, exp(-beta dE)). dE takes the values -8,
    -4, 0, 4, 8, so only exp(-4 beta) and exp(-8 beta) are needed. ``beta``
    has one value per lattice. One uniform number is drawn per site and
    sweep; each half uses those of its own sites.
    """
    b = np.asarray(beta, dtype=np.float64).reshape(-1, 1, 1)
    p4 = np.exp(-4.0 * b).astype(np.float32)
    p8 = np.exp(-8.0 * b).astype(np.float32)
    draw = rng.random(spins.shape, dtype=np.float32)
    for sublattice in checkerboard(spins.shape[-1]):
        local = spins * neighbour_sum(spins)  # dE / 2: -4, -2, 0, 2, 4
        # p8 < p4: a draw below p8 accepts every flip, one below p4 those of dE = 4
        accept = (local <= 0) | (draw < p8) | ((local == 2) & (draw < p4))
        np.negative(spins, out=spins, where=accept & sublattice)


def simulate(
    size: int,
    temperatures: Array,
    replicas: int,
    sweeps: int,
    burn_in: int,
    rng: np.random.Generator,
) -> tuple[Array, Array]:
    """Metropolis runs of ``replicas`` independent lattices at each of the
    ``temperatures``, every lattice started with all spins up.

    Returns the magnetisation per spin and the energy per spin after each of
    the ``sweeps`` sweeps that follow ``burn_in`` sweeps, each of shape
    ``(sweeps, len(temperatures), replicas)``.
    """
    if replicas < 1 or sweeps < 1 or burn_in < 0:
        raise ValueError("replicas and sweeps must be at least 1, burn_in at least 0")
    t = np.asarray(temperatures, dtype=np.float64)
    beta = np.repeat(1.0 / t, replicas)
    spins = np.ones((beta.size, size, size), dtype=np.int8)
    for _ in range(burn_in):
        metropolis_sweep(spins, beta, rng)
    m = np.empty((sweeps, beta.size))
    e = np.empty((sweeps, beta.size))
    for k in range(sweeps):
        metropolis_sweep(spins, beta, rng)
        m[k] = magnetisation(spins)
        e[k] = energy(spins) / size**2
    shape = (sweeps, t.size, replicas)
    return m.reshape(shape), e.reshape(shape)


def all_states(size: int) -> Spins:
    """Every one of the 2^(L^2) configurations of an L x L lattice, as a batch."""
    n = size * size
    if n > 20:
        raise ValueError("exact enumeration is limited to 20 spins")
    codes = np.arange(2**n, dtype=np.int64)[:, None] >> np.arange(n)
    return (1 - 2 * (codes & 1)).astype(np.int8).reshape(-1, size, size)


def exact_averages(size: int, temperatures: Array) -> tuple[Array, Array]:
    """The exact thermal averages of |m| and of the energy per spin of an
    L x L lattice at each temperature, by summing the Boltzmann weight
    exp(-E / T) over every configuration."""
    states = all_states(size)
    e = energy(states)
    m = np.abs(magnetisation(states))
    abs_m, e_per_spin = [], []
    for t in np.atleast_1d(np.asarray(temperatures, dtype=np.float64)):
        w = np.exp(-(e - e.min()) / t)
        z = w.sum()
        abs_m.append(float((w * m).sum() / z))
        e_per_spin.append(float((w * e).sum() / z / size**2))
    return np.array(abs_m), np.array(e_per_spin)


def exact_heat_capacity(size: int, temperatures: Array) -> Array:
    """The exact heat capacity per spin (<E^2> - <E>^2) / (N T^2) of an L x L
    lattice at each temperature, in units of k_B, from the number of
    configurations at each energy (the density of states)."""
    levels, counts = np.unique(energy(all_states(size)), return_counts=True)
    t = np.atleast_1d(np.asarray(temperatures, dtype=np.float64))[:, None]
    w = counts * np.exp(-(levels - levels.min()) / t)
    p = w / w.sum(axis=1, keepdims=True)
    mean = (p * levels).sum(axis=1, keepdims=True)
    return (p * (levels - mean) ** 2).sum(axis=1) / (size**2 * t[:, 0] ** 2)


def binder_cumulant(m: Array) -> Array:
    """U = 1 - <m^4> / (3 <m^2>^2) along the first axis (the samples). U tends
    to 2/3 in the ordered phase and to 0 in the disordered phase of a large
    lattice."""
    m2 = np.mean(m**2, axis=0)
    m4 = np.mean(m**4, axis=0)
    return 1.0 - m4 / (3.0 * m2**2)


def crossing(temperatures: Array, first: Array, second: Array) -> float:
    """The temperature at which two curves sampled at the same temperatures
    cross, from a straight line fitted to each by least squares: in a window
    narrow enough that both curves are close to straight, the intersection of
    the lines. Raises if the lines are parallel to round-off."""
    t = np.asarray(temperatures, dtype=np.float64)
    a1, b1 = np.polyfit(t, np.asarray(first, dtype=np.float64), 1)
    a2, b2 = np.polyfit(t, np.asarray(second, dtype=np.float64), 1)
    if abs(a1 - a2) <= 1e-9 * max(abs(a1), abs(a2)):
        raise ValueError("the fitted lines are parallel")
    return float((b2 - b1) / (a1 - a2))


def jackknife(estimate, samples: Array):
    """The estimate from all independent ``samples`` (along the last axis) and
    its jackknife standard error: ``estimate`` is applied to the samples with
    each one left out in turn. It suits an estimate, like a crossing or a
    cumulant, that is not a mean of the samples. An estimate that returns an
    array gets an array of errors."""
    x = np.asarray(samples, dtype=np.float64)
    n = x.shape[-1]
    if n < 2:
        raise ValueError("the jackknife needs at least two samples")
    full = estimate(x)
    left_out = np.array([estimate(np.delete(x, k, axis=-1)) for k in range(n)])
    spread = np.sum((left_out - left_out.mean(axis=0)) ** 2, axis=0)
    return full, np.sqrt((n - 1) / n * spread)


def heat_capacity(e: Array, temperature: Array, sites: int) -> Array:
    """The heat capacity per spin, N (<e^2> - <e>^2) / T^2 from the energy per
    spin ``e`` (samples along the first axis), in units of k_B."""
    t = np.asarray(temperature, dtype=np.float64)
    return sites * np.var(e, axis=0) / t**2


def susceptibility(m: Array, temperature: Array, sites: int) -> Array:
    """The susceptibility per spin, N (<m^2> - <|m|>^2) / T, from the
    magnetisation per spin ``m`` (samples along the first axis). The absolute
    value makes it finite on a finite lattice below Tc, where m itself
    changes sign now and then."""
    t = np.asarray(temperature, dtype=np.float64)
    return sites * (np.mean(m**2, axis=0) - np.mean(np.abs(m), axis=0) ** 2) / t
