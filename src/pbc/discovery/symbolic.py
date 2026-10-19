"""Symbolic regression over a grammar of power laws, without a model or an
agent (F67, lesson D7).

The grammar is every product ``c * x1**p1 * x2**p2 * ...`` of the variables
with each exponent on a fixed grid, by default the half-integers from -2 to
2. The search is exhaustive: every form of the grammar is fitted, so the
result does not depend on a random start, and two runs on the same data
give the same answer.

A form is fitted in logarithms: with ``ln y = ln c + sum p_i ln x_i`` and a
noise of relative size ``sigma`` on ``y``, the constant is the mean of the
residual and the chi-square is the sum of the squared deviations divided by
``sigma**2``. A form is **consistent** when its chi-square is what the noise
alone gives (``pbc.discovery.baselines.consistent``). The search chooses the
simplest consistent form; it reports every form as good as the best, which
the data cannot tell apart, and it reports a failure, never a claim, when no
form of the grammar is consistent.
"""

import itertools
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from functools import cached_property

import numpy as np
from numpy.typing import ArrayLike, NDArray

from pbc.discovery.baselines import FIT_SIGMAS

Array = NDArray[np.float64]
# The exponents of the default grammar: -2, -3/2, ..., 3/2, 2.
HALF_STEPS = tuple(k / 2 for k in range(-4, 5))
# Two forms whose chi-square differs by less than this are as good as each
# other: one unit is the change of one standard deviation in one point.
TIE = 1.0


@dataclass(frozen=True)
class PowerLaw:
    """One form of the grammar, fitted: ``constant`` times the product of the
    variables ``names`` to the powers ``exponents``."""

    names: tuple[str, ...]
    exponents: tuple[float, ...]
    constant: float
    chi2: float

    @property
    def complexity(self) -> int:
        """The number of variables the form uses plus the number of half
        steps in its exponents: 1 for sqrt(L), 4 for sqrt(L / g)."""
        return sum((p != 0) + round(abs(2 * p)) for p in self.exponents)

    def predict(self, variables: Mapping[str, ArrayLike]) -> Array:
        """The value of the form at ``variables``, one array per name."""
        value = np.full(np.shape(variables[self.names[0]]), self.constant)
        for name, p in zip(self.names, self.exponents, strict=True):
            if p:
                value = value * np.asarray(variables[name], dtype=float) ** p
        return value

    @property
    def shape(self) -> str:
        """The form without its constant, such as ``L^(1/2) g^(-1/2)``; ``1``
        for a constant."""
        factors = [
            name if p == 1 else f"{name}^({Fraction(p).limit_denominator(4)})"
            for name, p in zip(self.names, self.exponents, strict=True)
            if p
        ]
        return " ".join(factors) or "1"

    def formula(self, digits: int = 4) -> str:
        """The form as text, such as ``6.283 L^(1/2) g^(-1/2)``."""
        constant = f"{self.constant:.{digits}g}"
        return constant if self.shape == "1" else f"{constant} {self.shape}"


@dataclass(frozen=True)
class Search:
    """The outcome of a search over the grammar: every form, fitted, as one
    row of arrays per form, best chi-square first.

    ``chosen`` is the simplest consistent form, or ``None`` with the
    ``reason``; ``rivals`` are the consistent forms whose chi-square is within
    ``TIE`` of the best one: forms the data cannot tell apart from it."""

    names: tuple[str, ...]
    exponents: Array  # one row per form, one column per variable
    constants: Array
    chi2: Array
    dof: int
    sigma: float

    def form(self, index: int) -> PowerLaw:
        """The form of row ``index``."""
        return PowerLaw(
            self.names,
            tuple(map(float, self.exponents[index])),
            float(self.constants[index]),
            float(self.chi2[index]),
        )

    @cached_property
    def forms(self) -> tuple[PowerLaw, ...]:
        return tuple(self.form(i) for i in range(len(self.chi2)))

    @property
    def limit(self) -> float:
        """The largest chi-square that counts as consistent: the rule of
        ``pbc.discovery.baselines.consistent``."""
        return self.dof + FIT_SIGMAS * math.sqrt(2 * self.dof)

    @property
    def complexity(self) -> NDArray[np.int64]:
        """The complexity of each form, as ``PowerLaw.complexity``."""
        steps = np.rint(np.abs(2 * self.exponents)).astype(int)
        return (self.exponents != 0).sum(axis=1) + steps.sum(axis=1)

    def _consistent(self) -> NDArray[np.intp]:
        return np.flatnonzero(self.chi2 <= self.limit)

    def consistent(self) -> tuple[PowerLaw, ...]:
        return tuple(self.form(i) for i in self._consistent())

    @property
    def chosen(self) -> PowerLaw | None:
        good = self._consistent()
        if not good.size:
            return None
        # The rows are in order of chi-square, so the first of the simplest
        # is the best fit among them.
        return self.form(good[np.argmin(self.complexity[good])])

    @property
    def rivals(self) -> tuple[PowerLaw, ...]:
        good = self._consistent()
        return tuple(self.form(i) for i in good if self.chi2[i] <= self.chi2[0] + TIE)

    @property
    def reason(self) -> str:
        if self.chosen is not None:
            return ""
        return (
            "no form of the grammar is consistent: the best has a chi-square of"
            f" {self.chi2[0]:.3g} for {self.dof} degrees of freedom"
        )

    def pareto(self) -> tuple[PowerLaw, ...]:
        """The best form of each complexity that beats every simpler one:
        the trade-off between simplicity and fit."""
        front: list[PowerLaw] = []
        for i in np.lexsort((self.chi2, self.complexity)):
            if not front or self.chi2[i] < front[-1].chi2:
                front.append(self.form(i))
        return tuple(front)


def power_law_search(
    variables: Mapping[str, ArrayLike],
    y: ArrayLike,
    sigma: float,
    exponents: Sequence[float] = HALF_STEPS,
) -> Search:
    """Fit every power law of ``variables`` to ``y``.

    ``variables`` maps a name to its positive values, one per measurement;
    ``y`` holds the positive measurements, with a relative noise of standard
    deviation ``sigma`` (the standard deviation of ``ln y``). Each variable
    takes each exponent of ``exponents``."""
    names = tuple(variables)
    logs = np.column_stack([np.log(np.asarray(variables[n], float)) for n in names])
    log_y = np.log(np.asarray(y, float))
    if sigma <= 0:
        raise ValueError(f"sigma must be positive, got {sigma}")
    if len(log_y) < 2:
        raise ValueError("a search needs at least two measurements")
    grid = np.array(list(itertools.product(exponents, repeat=len(names))), float)
    # In logarithms each form is a straight line: the constant is the mean of
    # what the exponents leave of ln y, and the rest is the misfit.
    residual = log_y[:, None] - logs @ grid.T
    log_c = residual.mean(axis=0)
    chi2 = ((residual - log_c) ** 2).sum(axis=0) / sigma**2
    unsorted = Search(names, grid, np.exp(log_c), chi2, len(log_y) - 1, sigma)
    order = np.lexsort((unsorted.complexity, chi2))
    return Search(
        names, grid[order], np.exp(log_c[order]), chi2[order], len(log_y) - 1, sigma
    )


def noise_floor(search: Search, form: PowerLaw) -> float:
    """The relative noise at which ``form``, fitted by ``search`` on data with
    no noise beyond ``search.sigma``, is expected to become consistent.

    The misfit of the form grows its chi-square by ``form.chi2`` at the noise
    ``search.sigma``, and by that times ``(search.sigma / s)**2`` at a noise
    ``s``; the noise itself adds one per degree of freedom on average. The
    form passes once the misfit is below the margin of the limit,
    ``FIT_SIGMAS * sqrt(2 * dof)``: below this noise the data reject the
    form, above it they cannot."""
    margin = FIT_SIGMAS * math.sqrt(2 * search.dof)
    return search.sigma * math.sqrt(form.chi2 / margin)
