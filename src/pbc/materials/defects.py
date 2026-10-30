"""Point defects of a crystal: how many vacancies a crystal holds in
equilibrium, and how defects make atoms diffuse.

A vacancy is a lattice site without its atom. Making one costs the
formation energy E_f, and n vacancies on N sites can be placed in
C(N, n) = N! / (n! (N - n)!) ways, so the free energy of the crystal
changes by

    G(n) = n E_f - k T ln C(N, n).

Its minimum, with Stirling's approximation, is at n / (N - n) = e^(-E_f/kT):
the fraction of vacant sites is e^(-E_f/kT) / (1 + e^(-E_f/kT)).

A defect moves by hopping to a neighbouring site over an energy barrier
E_m, at the rate Gamma = nu e^(-E_m/kT) towards each of the z neighbours
(nu the attempt frequency). Its waiting time between hops is exponential
with the mean tau = 1 / (z Gamma), and its path is a random walk on the
lattice with steps of the spacing a, the walk of T1
(``pbc.thermodynamics.diffusion``) with D = a^2 / (2 d tau).

An atom of the crystal moves only when a vacancy passes it, and its jumps
are correlated: right after a jump the vacancy sits behind it, so its next
jump is likely to be back. Its diffusion coefficient is f c_v D_v, with
c_v the vacancy fraction, D_v the vacancy's own diffusion coefficient, and
f the tracer correlation factor, 1 / (pi - 1) on the square lattice.

Energies are in eV, temperatures in K; all randomness comes from a
``numpy.random.Generator`` created from a seed by the caller.
"""

import numpy as np
from numpy.typing import NDArray

Array = NDArray[np.float64]

BOLTZMANN = 8.617333262e-5  # eV/K, exact in the SI since 2019
STEPS = np.array([[1, 0], [-1, 0], [0, 1], [0, -1]])  # the square lattice, z = 4
SQUARE_LATTICE_CORRELATION = 1 / (np.pi - 1)  # the tracer correlation factor f


def free_energy(sites: int, counts: Array, formation: float, kt: float) -> Array:
    """G(n) - G(0) (eV) for the vacancy counts ``counts``: n E_f minus k T
    times the logarithm of C(N, n), the logarithm summed exactly as
    ln C(N, n) = sum over j < n of ln((N - j) / (j + 1)), with no Stirling
    approximation."""
    counts = np.asarray(counts, dtype=np.int64)
    top = int(counts.max())
    j = np.arange(top)
    log_choose = np.concatenate([[0.0], np.cumsum(np.log((sites - j) / (j + 1)))])
    return counts * formation - kt * log_choose[counts]


def free_energy_step(sites: int, count: int, formation: float, kt: float) -> float:
    """G(n + 1) - G(n) (eV), exactly: E_f - k T ln((N - n) / (n + 1)), the
    energy of one more vacancy against the ways of placing it."""
    return formation - kt * np.log((sites - count) / (count + 1))


def exact_vacancies(sites: int, formation: float, kt: float) -> int:
    """The vacancy count n that minimises the exact G(n). The step
    G(n + 1) - G(n) grows with n, so G falls while the step is negative and
    rises after; the minimum is the first n whose step is not negative,
    found by bisection over 0 to N - 1 without the closed form."""
    low, high = 0, sites - 1
    while low < high:
        middle = (low + high) // 2
        if free_energy_step(sites, middle, formation, kt) >= 0:
            high = middle
        else:
            low = middle + 1
    return low


def vacancy_fraction(formation: float, kt) -> Array:
    """The closed-form fraction of vacant sites in equilibrium,
    e^(-E_f/kT) / (1 + e^(-E_f/kT)), from the minimum of G with Stirling's
    approximation; e^(-E_f/kT) when it is small."""
    x = np.exp(-formation / np.asarray(kt, dtype=float))
    return x / (1 + x)


def hop_rate(attempt: float, barrier: float, kt) -> Array:
    """The Arrhenius rate (1/s) of a hop to one neighbour,
    Gamma = nu e^(-E_m/kT)."""
    return attempt * np.exp(-barrier / np.asarray(kt, dtype=float))


def lattice_walks(
    n_walkers: int, times: Array, rate: float, spacing: float, rng: np.random.Generator
) -> Array:
    """The positions (shape (len(times) + 1, n_walkers, 2), units of
    ``spacing``) of walkers that start at the origin and hop to each of the
    four neighbours of the square lattice at the rate ``rate``, at the time
    0 and at each of ``times``. The hops form a Poisson process of the total
    rate 4 Gamma, so the number of hops between two recorded times is drawn
    from a Poisson distribution and the hops split among the four
    directions by a multinomial draw: the continuous-time walk, sampled
    exactly at the recorded times."""
    times = np.asarray(times, dtype=float)
    if np.any(np.diff(np.concatenate([[0.0], times])) <= 0):
        raise ValueError("the times must be positive and increasing")
    intervals = np.diff(np.concatenate([[0.0], times]))
    positions = np.zeros((len(times) + 1, n_walkers, 2))
    for i, interval in enumerate(intervals):
        hops = rng.poisson(4 * rate * interval, size=n_walkers)
        split = rng.multinomial(hops, [0.25] * 4)
        step = np.column_stack([split[:, 0] - split[:, 1], split[:, 2] - split[:, 3]])
        positions[i + 1] = positions[i] + spacing * step
    return positions


def vacancy_exchanges(
    side: int, checkpoints: list[int], runs: int, rng: np.random.Generator
) -> tuple[Array, Array]:
    """One vacancy on a periodic square lattice of side x side sites, all
    sites but one holding an atom, in ``runs`` independent copies. At each step the
    vacancy exchanges places with one of its four neighbours, chosen at
    random, and that atom moves one spacing the opposite way. Returns, after
    each number of jumps in ``checkpoints`` (one row each, one column per
    run), the sum over all atoms of their squared displacements and the
    squared displacement of the vacancy (units of the spacing squared)."""
    if side < 3:
        raise ValueError("the lattice needs at least three sites per side")
    sites = side * side
    occupant = np.tile(np.arange(sites, dtype=np.int32), (runs, 1))  # atom per site
    displacement = np.zeros((runs, sites, 2), dtype=np.int32)  # in spacings
    vacancy = np.zeros((runs, 2), dtype=np.int64)  # atom 0 is the vacancy
    travelled = np.zeros((runs, 2), dtype=np.int64)
    row = np.arange(runs)
    atoms, moved = [], []
    jumps = max(checkpoints)
    for count, direction in enumerate(rng.integers(0, 4, size=(jumps, runs)), 1):
        step = STEPS[direction]
        target = (vacancy + step) % side
        here = vacancy[:, 0] * side + vacancy[:, 1]
        there = target[:, 0] * side + target[:, 1]
        atom = occupant[row, there]
        displacement[row, atom] -= step.astype(np.int32)
        occupant[row, here] = atom
        occupant[row, there] = 0
        vacancy = target
        travelled += step
        if count in checkpoints:
            squares = displacement[:, 1:].astype(np.float64) ** 2
            atoms.append(np.sum(squares, axis=(1, 2)))
            moved.append(np.sum(travelled.astype(np.float64) ** 2, axis=1))
    return np.array(atoms), np.array(moved)


def correlation_factor(
    side: int, start: int, end: int, runs: int, rng: np.random.Generator
):
    """The tracer correlation factor f and its standard error, and the
    vacancy's own squared displacement per jump and its standard error.
    Each jump moves one atom by one spacing, so without correlation the sum
    of the atoms' squared displacements would grow by one spacing squared
    per jump; with it, the sum grows by f per jump, plus a constant from the
    start of the run, when no atom has a jump behind it. The growth between
    ``start`` and ``end`` jumps, divided by their difference, removes the
    constant. The vacancy's own walk is uncorrelated: one per jump."""
    atoms, moved = vacancy_exchanges(side, [start, end], runs, rng)
    growth = (atoms[1] - atoms[0]) / (end - start)
    per_jump = moved[1] / end
    return (
        float(growth.mean()),
        float(growth.std(ddof=1) / np.sqrt(runs)),
        float(per_jump.mean()),
        float(per_jump.std(ddof=1) / np.sqrt(runs)),
    )
