"""The choice of state variables in equation discovery (F147, lesson MD4).

``pbc.discovery.equations`` writes the acceleration as a sparse sum of terms
in the position and the velocity of one body. That is a choice of **state**:
the variables that, by assumption, determine what happens next. Here the
state is named, any number of variables, and two things are done with it:

- ``search`` writes the acceleration as a sparse sum of the products of the
  state's variables up to a degree, by the sequentially thresholded least
  squares of ``pbc.discovery.equations.sparse_regression`` (the same rule
  and the same threshold; on the state of position and velocity it gives the
  same equation, which a test checks);
- ``state_test`` asks whether the variables are a state at all: if they
  are, two moments at which they nearly agree have nearly the same
  acceleration. A pair of samples closer than ``RADIUS`` (in standard
  deviations of each variable) whose accelerations differ by much more is a
  witness that something the dynamics need is missing from the state.

The search alone cannot tell: given an incomplete state it still returns a
short equation, fitted as well as those variables allow.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import combinations_with_replacement

import numpy as np
from numpy.typing import NDArray
from scipy.spatial import cKDTree

from pbc.discovery.equations import THRESHOLD

Array = NDArray[np.float64]

# Two samples are "at nearly the same state" when they are closer than this,
# with each variable measured in its standard deviation over the samples.
RADIUS = 0.05
# A state passes the test when no pair closer than RADIUS differs in
# acceleration by more than this many radii, in units of the root-mean-square
# acceleration: a smooth law changes the acceleration across a small step of
# the state by about the step times its slope, of order one here.
SMOOTHNESS = 2.0


def library(names: Sequence[str], degree: int = 3) -> tuple[str, ...]:
    """The products of the variables ``names`` up to ``degree``, by degree,
    the constant first: for ``("x", "v")`` and degree two, ``1, x, v, x^2,
    x v, v^2``."""
    terms = ["1"]
    for total in range(1, degree + 1):
        for chosen in combinations_with_replacement(range(len(names)), total):
            powers = [chosen.count(i) for i in range(len(names))]
            terms.append(_term(names, powers))
    return tuple(terms)


def _term(names: Sequence[str], powers: Sequence[int]) -> str:
    return " ".join(
        name if p == 1 else f"{name}^{p}"
        for name, p in zip(names, powers, strict=True)
        if p
    )


def _powers(names: Sequence[str], term: str) -> list[int]:
    powers = [0] * len(names)
    for factor in term.split():
        if factor == "1":
            continue
        base, _, power = factor.partition("^")
        powers[list(names).index(base)] = int(power or 1)
    return powers


def evaluate(names: Sequence[str], terms: Sequence[str], values: Array) -> Array:
    """The columns of ``terms`` at the samples ``values`` (one row per
    sample, one column per variable of ``names``)."""
    values = np.atleast_2d(np.asarray(values, dtype=float))
    columns = []
    for term in terms:
        powers = _powers(names, term)
        columns.append(np.prod(values**powers, axis=1))
    return np.column_stack(columns)


@dataclass(frozen=True)
class Found:
    """``a = sum of coefficient * term`` in the variables ``names``, with the
    root-mean-square of its residual (m/s²)."""

    names: tuple[str, ...]
    coefficients: dict[str, float]
    residual: float

    def acceleration(self, values: Array) -> Array:
        terms = list(self.coefficients)
        if not terms:
            return np.zeros(np.atleast_2d(values).shape[0])
        weights = np.array([self.coefficients[t] for t in terms])
        return evaluate(self.names, terms, values) @ weights

    def formula(self, digits: int = 4) -> str:
        """The equation as text, such as ``a = -5.5 x1 + 1.5 x2``."""
        parts = []
        for term, c in self.coefficients.items():
            factor = f"{abs(c):.{digits}g}" + ("" if term == "1" else f" {term}")
            sign = ("-" if c < 0 else "") if not parts else ("- " if c < 0 else "+ ")
            parts.append(sign + factor)
        return "a = " + (" ".join(parts) or "0")


def search(
    names: Sequence[str],
    values: Array,
    target: Array,
    degree: int = 3,
    threshold: float = THRESHOLD,
) -> Found:
    """The acceleration ``target`` as a sparse sum of the library of the
    state ``names`` at the samples ``values``: fit every term, drop each
    whose contribution is below ``threshold`` times the root-mean-square
    acceleration, fit the rest again, until none is dropped."""
    terms = library(names, degree)
    columns = evaluate(names, terms, values)
    scale = np.sqrt((columns**2).mean(axis=0))
    scale[scale == 0] = 1.0
    scaled = columns / scale
    size = np.sqrt((target**2).mean())
    active = np.ones(len(terms), dtype=bool)
    fitted = np.zeros(len(terms))
    for _ in range(len(terms)):
        fitted[:] = 0.0
        fitted[active], *_ = np.linalg.lstsq(scaled[:, active], target, rcond=None)
        small = active & (np.abs(fitted) < threshold * size)
        if not small.any():
            break
        active &= ~small
    coefficients = fitted / scale
    residual = float(np.sqrt(((target - columns @ coefficients) ** 2).mean()))
    return Found(
        tuple(names),
        {t: float(c) for t, c in zip(terms, coefficients, strict=True) if c != 0.0},
        residual,
    )


@dataclass(frozen=True)
class StateTest:
    """The result of ``state_test``: how many pairs of samples lie within
    the radius, the largest difference of their accelerations relative to
    the root-mean-square acceleration, and the pair that has it."""

    pairs: int
    largest: float
    witness: tuple[int, int] | None

    @property
    def passes(self) -> bool:
        """No pair at nearly the same state differs by more than a smooth
        law allows. Without a pair the test has nothing to compare and does
        not pass."""
        return self.pairs > 0 and self.largest <= SMOOTHNESS * RADIUS


def state_test(values: Array, target: Array, radius: float = RADIUS) -> StateTest:
    """Do the variables of ``values`` (one row per sample) determine the
    acceleration ``target``? Every pair of samples closer than ``radius``,
    each variable measured in its standard deviation, is compared."""
    scaled = values / values.std(axis=0)
    pairs = cKDTree(scaled).query_pairs(radius, output_type="ndarray")
    if len(pairs) == 0:
        return StateTest(0, 0.0, None)
    size = np.sqrt((target**2).mean())
    apart = np.abs(target[pairs[:, 0]] - target[pairs[:, 1]]) / size
    worst = int(np.argmax(apart))
    first, second = (int(i) for i in pairs[worst])
    return StateTest(len(pairs), float(apart[worst]), (first, second))
