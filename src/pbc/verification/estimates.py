"""Estimates a verifier computes from the output of a simulation.

All of them take plain arrays, so they serve any method and any model: a
list of step sizes with the error measured at each, or the values of a
quantity that the exact motion keeps constant.
"""

import numpy as np
from numpy.typing import ArrayLike, NDArray


def _convergence_data(
    steps: ArrayLike, errors: ArrayLike
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    h = np.asarray(steps, dtype=np.float64)
    e = np.asarray(errors, dtype=np.float64)
    if h.ndim != 1 or h.shape != e.shape or len(h) < 2:
        raise ValueError(
            "steps and errors must be vectors of the same length, at least 2"
        )
    if np.any(h <= 0):
        raise ValueError("the steps must be positive")
    if np.any(np.diff(h) >= 0):
        raise ValueError("the steps must decrease, coarsest first")
    return h, e


def observed_orders(steps: ArrayLike, errors: ArrayLike) -> NDArray[np.float64]:
    """The order of convergence seen between each pair of successive steps.

    ``steps`` are decreasing step sizes and ``errors`` the error of the run
    at each. With the error proportional to ``h ** p``, the pair gives
    ``p = log(e_i / e_(i+1)) / log(h_i / h_(i+1))``; for halved steps that is
    the base-2 logarithm of the ratio of the errors. An error that is zero
    or not finite gives ``nan``: nothing was measured.
    """
    h, e = _convergence_data(steps, errors)
    with np.errstate(divide="ignore", invalid="ignore"):
        orders = np.log(e[:-1] / e[1:]) / np.log(h[:-1] / h[1:])
    orders[
        ~np.isfinite(e[:-1]) | ~np.isfinite(e[1:]) | (e[:-1] <= 0) | (e[1:] <= 0)
    ] = np.nan
    return orders


def fitted_order(steps: ArrayLike, errors: ArrayLike) -> float:
    """The slope of the straight line through the points (log h, log error),
    fitted by least squares: one number for the order of a method.

    ``nan`` when any error is zero or not finite.
    """
    h, e = _convergence_data(steps, errors)
    if not np.all(np.isfinite(e)) or np.any(e <= 0):
        return float("nan")
    return float(np.polyfit(np.log(h), np.log(e), 1)[0])


def convergence_table(
    steps: ArrayLike, errors: ArrayLike
) -> list[tuple[float, float, float | None]]:
    """The rows (step, error, observed order) of a convergence table. The
    first row has no order, as there is no coarser step to compare with."""
    h, e = _convergence_data(steps, errors)
    orders = observed_orders(h, e)
    return [
        (float(h[i]), float(e[i]), None if i == 0 else float(orders[i - 1]))
        for i in range(len(h))
    ]


def invariant_drift(values: ArrayLike) -> float:
    """The largest relative deviation of ``values`` from the first value.

    For a quantity the exact motion keeps constant, such as an energy or an
    angular momentum, this is how far the simulation has moved it.
    """
    v = np.asarray(values, dtype=np.float64)
    if v.ndim != 1 or len(v) < 2 or v[0] == 0:
        raise ValueError(
            "values must be a vector of at least 2 numbers, the first not zero"
        )
    return float(np.max(np.abs(v / v[0] - 1.0)))


def invariant_band(
    values: ArrayLike, first: slice, later: slice
) -> tuple[float, float]:
    """The drift of ``values`` within the slice ``first`` and within the
    slice ``later``, each relative to the first value of ``values``.

    A bounded quantity has about the same drift in both; a quantity that
    leaks has a larger one later. Comparing the two tells a band from a
    trend, which one number cannot.
    """
    v = np.asarray(values, dtype=np.float64)
    if v.ndim != 1 or len(v) < 2 or v[0] == 0:
        raise ValueError(
            "values must be a vector of at least 2 numbers, the first not zero"
        )
    relative = v / v[0] - 1.0
    return (
        float(np.max(np.abs(relative[first]))),
        float(np.max(np.abs(relative[later]))),
    )
