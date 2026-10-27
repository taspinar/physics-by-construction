"""Two spins one half: the correlations of the singlet, the CHSH
combination of four correlations, and a local hidden-variable model to
compare them with.

The pair lives in the four-dimensional space of A and B, basis order
(up up, up down, down up, down down) along z. Each side measures in the x-z
plane, at the angle alpha from z for A and beta for B; the outcomes are +1
and -1. The joint probability of (a, b) is tr(rho P_A(a) x P_B(b)), with the
projectors of ``pbc.quantum.spin``. For the singlet
(|up down> - |down up>) / sqrt(2) the correlation, the mean of the product
a b, is E(alpha, beta) = -cos(alpha - beta).

CHSH combines four settings, a and a' for A and b and b' for B:

    S = E(a, b) - E(a, b') + E(a', b) + E(a', b').

A local hidden-variable model gives each pair a value lambda that fixes both
outcomes, A's from alpha and lambda only, B's from beta and lambda only; for
each lambda S is then -2 or +2, so its average obeys |S| <= 2. Quantum
mechanics allows |S| up to 2 sqrt(2) (Tsirelson's bound), which the singlet
reaches at a = 0, a' = pi / 2, b = pi / 4, b' = 3 pi / 4.
"""

from itertools import product

import numpy as np
from numpy.typing import ArrayLike, NDArray

from pbc.quantum.spin import direction, projector

Array = NDArray[np.float64]
Counts = NDArray[np.int64]

OUTCOMES = (1, -1)
LOCAL_BOUND = 2.0
TSIRELSON_BOUND = 2 * np.sqrt(2)
CHSH_ANGLES = (0.0, np.pi / 2, np.pi / 4, 3 * np.pi / 4)  # a, a', b, b'
SIGNS = (1, -1, 1, 1)  # of E(a, b), E(a, b'), E(a', b), E(a', b') in S

SINGLET = np.array([0, 1, -1, 0], dtype=complex) / np.sqrt(2)


def density(state: ArrayLike) -> NDArray[np.complex128]:
    """|psi><psi| of a state vector."""
    psi = np.asarray(state, dtype=complex)
    return np.outer(psi, psi.conj())


def werner(visibility: float) -> NDArray[np.complex128]:
    """The singlet mixed with white noise, V |singlet><singlet| + (1 - V) / 4."""
    return visibility * density(SINGLET) + (1 - visibility) * np.eye(4) / 4


def plane(angle: float) -> Array:
    """The direction in the x-z plane at ``angle`` from z."""
    return direction(angle, 0.0)


def joint_probabilities(rho: ArrayLike, alpha: float, beta: float) -> Array:
    """p[i, j] = tr(rho P_A(a_i) x P_B(b_j)) for the outcomes (+1, -1) of A
    along ``alpha`` and of B along ``beta``."""
    rho = np.asarray(rho, dtype=complex)
    p = np.empty((2, 2))
    for i, a in enumerate(OUTCOMES):
        for j, b in enumerate(OUTCOMES):
            joint = np.kron(projector(plane(alpha), a), projector(plane(beta), b))
            p[i, j] = np.real(np.trace(rho @ joint))
    return p


def correlation(table: ArrayLike) -> float:
    """The mean of a b from a table of probabilities or of counts,
    (p++ + p-- - p+- - p-+) / total."""
    t = np.asarray(table, dtype=float)
    return float((t[0, 0] + t[1, 1] - t[0, 1] - t[1, 0]) / t.sum())


def correlation_error(table: ArrayLike) -> float:
    """The standard error of the correlation estimated from counts,
    sqrt((1 - E^2) / N): a b is +1 or -1, so its variance is 1 - E^2."""
    counts = np.asarray(table, dtype=float)
    return float(np.sqrt((1 - correlation(counts) ** 2) / counts.sum()))


def sample_counts(p: ArrayLike, count: int, rng: np.random.Generator) -> Counts:
    """The counts of the four outcomes of ``count`` pairs drawn independently
    with the probabilities ``p``."""
    p = np.asarray(p, dtype=float)
    return rng.multinomial(count, p.ravel() / p.sum()).reshape(2, 2)


def quantum_correlation(alpha: ArrayLike, beta: ArrayLike) -> Array:
    """E(alpha, beta) = -cos(alpha - beta) of the singlet."""
    return -np.cos(np.asarray(alpha, dtype=float) - np.asarray(beta, dtype=float))


def local_outcomes(
    alpha: float, beta: float, hidden: ArrayLike
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """The outcomes of the local model for the hidden angles ``hidden``:
    A = sign cos(alpha - lambda) and B = -sign cos(beta - lambda), each set
    by its own setting and lambda."""
    lam = np.asarray(hidden, dtype=float)
    a = np.where(np.cos(alpha - lam) >= 0, 1, -1)
    b = np.where(np.cos(beta - lam) >= 0, -1, 1)
    return a, b


def local_counts(
    alpha: float, beta: float, count: int, rng: np.random.Generator
) -> Counts:
    """The counts of ``count`` pairs of the local model, each with a hidden
    angle drawn uniformly from [0, 2 pi)."""
    a, b = local_outcomes(alpha, beta, rng.uniform(0, 2 * np.pi, count))
    return np.array([[np.sum((a == i) & (b == j)) for j in OUTCOMES] for i in OUTCOMES])


def local_correlation(alpha: ArrayLike, beta: ArrayLike) -> Array:
    """E(alpha, beta) = -1 + 2 delta / pi of the local model, delta the angle
    between the settings folded into [0, pi]."""
    delta = np.abs(np.asarray(alpha, dtype=float) - np.asarray(beta, dtype=float))
    delta = np.mod(delta, 2 * np.pi)
    delta = np.minimum(delta, 2 * np.pi - delta)
    return -1 + 2 * delta / np.pi


def setting_pairs(angles: ArrayLike = CHSH_ANGLES) -> list[tuple[float, float]]:
    """The four pairs (a, b), (a, b'), (a', b), (a', b') of the settings
    (a, a', b, b'), in the order of the CHSH sum."""
    a, a2, b, b2 = angles
    return [(a, b), (a, b2), (a2, b), (a2, b2)]


def chsh(correlations: ArrayLike) -> float:
    """S = E(a, b) - E(a, b') + E(a', b) + E(a', b')."""
    return float(np.dot(SIGNS, np.asarray(correlations, dtype=float)))


def chsh_error(errors: ArrayLike) -> float:
    """The standard error of S from four independent estimates: the root of
    the sum of their squares."""
    return float(np.sqrt(np.sum(np.asarray(errors, dtype=float) ** 2)))


def family(theta: float) -> tuple[float, float, float, float]:
    """The settings (a, a', b, b') = (0, 2 theta, theta, 3 theta): each
    setting theta from the next, so three of the pairs are theta apart and
    one 3 theta."""
    return (0.0, 2 * theta, theta, 3 * theta)


def deterministic_strategies() -> list[tuple[tuple[int, int, int, int], float]]:
    """Every assignment of fixed outcomes (A(a), A(a'), B(b), B(b')), and its
    S = A B - A B' + A' B + A' B'. A local hidden-variable model is a
    probability mixture of these sixteen."""
    return [
        ((x, x2, y, y2), float(x * y - x * y2 + x2 * y + x2 * y2))
        for x, x2, y, y2 in product(OUTCOMES, repeat=4)
    ]


def marginal(table: ArrayLike) -> float:
    """The fraction of A's outcomes that are +1, from a table of counts."""
    t = np.asarray(table, dtype=float)
    return float((t[0, 0] + t[0, 1]) / t.sum())
