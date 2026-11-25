"""Estimates with standard errors, the comparison of repetitions, and the
consistency check of two protocols (F145).

An ``Estimate`` is a value with its standard error. Repetitions of one
measurement are combined by their weighted mean; their spread is compared
with their standard errors by the Birge ratio sqrt(chi^2 / (n - 1)), and a
ratio above one widens the combined error by it, so that a spread the
errors do not explain is never hidden. Two estimates of one quantity agree
when they differ by at most ``COVERAGE`` times their combined standard
error: the independent check of the live and recorded routes, where the
nominal closed form of the circuit is not a reference (F140).
"""

import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass

# The coverage factor of an interval and of the consistency check: about
# 95 % for normal errors.
COVERAGE = 2.0


@dataclass(frozen=True)
class Estimate:
    """A ``value`` with its standard error ``se`` (both in the quantity's
    unit)."""

    value: float
    se: float

    def interval(self, k: float = COVERAGE) -> tuple[float, float]:
        """The interval value plus or minus ``k`` standard errors."""
        return (self.value - k * self.se, self.value + k * self.se)

    @property
    def relative_width(self) -> float:
        """The width of the interval over the value (dimensionless)."""
        return 2.0 * COVERAGE * self.se / abs(self.value) if self.value else math.inf

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class Combined:
    """Repetitions combined: the weighted ``estimate``, the number ``n``,
    and the ``birge`` ratio of their spread to their errors (one when they
    agree as their errors say; NaN for a single one)."""

    estimate: Estimate
    n: int
    birge: float

    @property
    def consistent(self) -> bool:
        """Whether the spread is explained by the errors: a Birge ratio
        below 1 + 2 sqrt(1 / (2 (n - 1))), its two-sigma range for normal
        errors."""
        if self.n < 2:
            return True
        return self.birge <= 1.0 + 2.0 * math.sqrt(1.0 / (2.0 * (self.n - 1)))


def combine(estimates: Sequence[Estimate]) -> Combined:
    """The weighted mean of ``estimates`` with weights 1 / se^2, its standard
    error widened by the Birge ratio when that is above one."""
    if not estimates:
        raise ValueError("nothing to combine")
    if any(not e.se > 0 or not math.isfinite(e.value) for e in estimates):
        raise ValueError("every estimate needs a finite value and a positive error")
    # region: combine
    weights = [1.0 / e.se**2 for e in estimates]
    total = sum(weights)
    mean = sum(w * e.value for w, e in zip(weights, estimates, strict=True)) / total
    se = 1.0 / math.sqrt(total)
    n = len(estimates)
    if n < 2:
        return Combined(Estimate(mean, se), n, math.nan)
    chi2 = sum(
        w * (e.value - mean) ** 2 for w, e in zip(weights, estimates, strict=True)
    )
    birge = math.sqrt(chi2 / (n - 1))
    # endregion: combine
    return Combined(Estimate(mean, se * max(1.0, birge)), n, birge)


@dataclass(frozen=True)
class Agreement:
    """The consistency check of two estimates of one quantity."""

    quantity: str
    first: str
    second: str
    a: Estimate
    b: Estimate
    difference: float
    combined_se: float
    agree: bool

    @property
    def sigmas(self) -> float:
        return abs(self.difference) / self.combined_se

    def to_dict(self) -> dict[str, object]:
        return {
            "quantity": self.quantity,
            "first": self.first,
            "second": self.second,
            "a": self.a.to_dict(),
            "b": self.b.to_dict(),
            "difference": self.difference,
            "combined_se": self.combined_se,
            "sigmas": self.sigmas,
            "coverage": COVERAGE,
            "agree": self.agree,
        }


def agreement(
    quantity: str, first: str, a: Estimate, second: str, b: Estimate
) -> Agreement:
    """Whether the estimate ``a`` of the protocol ``first`` and the
    estimate ``b`` of the protocol ``second`` agree:
    |a - b| <= COVERAGE sqrt(se_a^2 + se_b^2)."""
    # region: agreement
    difference = a.value - b.value
    combined = math.hypot(a.se, b.se)
    agree = abs(difference) <= COVERAGE * combined
    # endregion: agreement
    return Agreement(quantity, first, second, a, b, difference, combined, agree)
