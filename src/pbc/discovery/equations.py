"""Equations of motion from trajectories, without a model or an agent
(F67, lessons D8).

Only the positions of a trajectory are observed, at equal time steps. The
velocity and the acceleration are estimated from them, either by central
differences or by a Savitzky-Golay filter (a polynomial fitted to a sliding
window, then differentiated). The acceleration is then written as a sparse
sum of the terms of a polynomial library in position and velocity, by
sequentially thresholded least squares: fit every term, drop the terms whose
contribution is small, fit the rest again.

Differentiation amplifies noise: a central second difference divides the
noise of the positions by the square of the time step. Smoothing reduces
that noise and adds a bias, which grows with the window. Neither is
guaranteed to recover the equation; the result says what it found, and the
lessons show where it fails.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.integrate import solve_ivp
from scipy.signal import savgol_filter

Array = NDArray[np.float64]
# A term is dropped when its contribution to the acceleration (coefficient
# times the root-mean-square of its column) is below this fraction of the
# root-mean-square acceleration.
THRESHOLD = 0.02


@dataclass(frozen=True)
class Derivatives:
    """Position, velocity, and acceleration at the same instants: what a
    differentiator returns from the positions it was given."""

    x: Array
    v: Array
    a: Array


def central_differences(x: Array, dt: float) -> Derivatives:
    """The velocity ``(x[i+1] - x[i-1]) / (2 dt)`` and the acceleration
    ``(x[i+1] - 2 x[i] + x[i-1]) / dt**2`` at every interior sample of the
    positions ``x`` (m), sampled every ``dt`` (s). Both are second order in
    ``dt``; a noise of standard deviation ``s`` in ``x`` becomes a noise of
    about ``s / dt`` in the velocity and ``2.4 s / dt**2`` in the acceleration.
    """
    x = np.asarray(x, dtype=float)
    return Derivatives(
        x=x[1:-1],
        v=(x[2:] - x[:-2]) / (2 * dt),
        a=(x[2:] - 2 * x[1:-1] + x[:-2]) / dt**2,
    )


def savitzky_golay(x: Array, dt: float, window: int, order: int = 3) -> Derivatives:
    """The position, velocity, and acceleration of a polynomial of degree
    ``order`` fitted by least squares to the ``window`` samples around each
    sample of ``x`` (m), sampled every ``dt`` (s). The samples closer than
    half a window to either end are dropped: there the window is one-sided.

    The fit averages the noise over the window and follows any part of the
    motion that is a polynomial of degree ``order`` over it; what is not, it
    smooths away, so the estimate has a bias that grows with the window."""
    x = np.asarray(x, dtype=float)
    if window % 2 == 0 or window <= order:
        raise ValueError(f"the window must be odd and larger than {order}")
    half = window // 2
    inner = slice(half, len(x) - half)

    def derivative(n: int) -> Array:
        return savgol_filter(x, window, order, deriv=n, delta=dt)[inner]

    return Derivatives(derivative(0), derivative(1), derivative(2))


def combine(parts: Sequence[Derivatives]) -> Derivatives:
    """The derivatives of several trajectories as one set of samples."""
    return Derivatives(
        np.concatenate([p.x for p in parts]),
        np.concatenate([p.v for p in parts]),
        np.concatenate([p.a for p in parts]),
    )


def polynomial_library(degree: int = 3) -> tuple[str, ...]:
    """The terms ``x^i v^j`` with ``i + j <= degree``, by degree:
    ``1, x, v, x^2, x v, v^2, ...``."""
    names = []
    for total in range(degree + 1):
        for j in range(total + 1):
            names.append(_term(total - j, j))
    return tuple(names)


def _term(i: int, j: int) -> str:
    def factor(name: str, power: int) -> str:
        return "" if power == 0 else name if power == 1 else f"{name}^{power}"

    return " ".join(p for p in (factor("x", i), factor("v", j)) if p) or "1"


def _powers(term: str) -> tuple[int, int]:
    i = j = 0
    for factor in term.split():
        base, _, power = factor.partition("^")
        if base == "x":
            i = int(power or 1)
        elif base == "v":
            j = int(power or 1)
    return i, j


def evaluate(terms: Sequence[str], x: Array, v: Array) -> Array:
    """The columns of the library: one column per term, one row per sample."""
    x = np.asarray(x, dtype=float)
    v = np.asarray(v, dtype=float)
    return np.column_stack([x**i * v**j for i, j in map(_powers, terms)])


def singular_values(terms: Sequence[str], data: Derivatives) -> Array:
    """The singular values of the library on ``data``, each column scaled to a
    root-mean-square of one, relative to the largest. A value near zero is a
    combination of terms that vanishes on the data: the data cannot tell an
    equation from the same equation plus that combination."""
    columns = evaluate(terms, data.x, data.v)
    columns = columns / np.sqrt((columns**2).mean(axis=0))
    values = np.linalg.svd(columns, compute_uv=False)
    return values / values[0]


@dataclass(frozen=True)
class Equation:
    """``a = sum of coefficient * term``: an equation of motion found in the
    data, with the root-mean-square of its residual (m/s²)."""

    coefficients: dict[str, float]
    residual: float

    def acceleration(self, x: Array, v: Array) -> Array:
        terms = list(self.coefficients)
        if not terms:
            return np.zeros_like(np.asarray(x, dtype=float))
        values = np.array([self.coefficients[t] for t in terms])
        return evaluate(terms, np.atleast_1d(x), np.atleast_1d(v)) @ values

    def formula(self, digits: int = 4) -> str:
        """The equation as text, such as ``a = -4 x - 0.3 v``."""
        parts = []
        for term, c in self.coefficients.items():
            factor = f"{abs(c):.{digits}g}" + ("" if term == "1" else f" {term}")
            sign = ("-" if c < 0 else "") if not parts else ("- " if c < 0 else "+ ")
            parts.append(sign + factor)
        return "a = " + (" ".join(parts) or "0")


def sparse_regression(
    terms: Sequence[str], data: Derivatives, threshold: float = THRESHOLD
) -> Equation:
    """Sequentially thresholded least squares: fit the acceleration with all
    ``terms``, drop each term whose contribution is below ``threshold`` times
    the root-mean-square acceleration, and fit the rest again, until no term
    is dropped."""
    columns = evaluate(terms, data.x, data.v)
    scale = np.sqrt((columns**2).mean(axis=0))
    scale[scale == 0] = 1.0
    scaled = columns / scale
    target = data.a
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
    return Equation(
        {t: float(c) for t, c in zip(terms, coefficients, strict=True) if c != 0.0},
        residual,
    )


def integrate(
    acceleration: Callable[[Array, Array], Array],
    x0: float,
    v0: float,
    t: Array,
) -> Array:
    """The positions at the times ``t`` (s) of the motion ``x'' =
    acceleration(x, v)`` from ``x0`` (m) and ``v0`` (m/s), integrated with
    SciPy's adaptive Runge-Kutta method to a relative tolerance of 1e-10."""

    def rate(_: float, state: Array) -> Array:
        x, v = state
        return np.array([v, float(np.squeeze(acceleration(x, v)))])

    solution = solve_ivp(
        rate, (t[0], t[-1]), [x0, v0], t_eval=t, rtol=1e-10, atol=1e-12
    )
    if not solution.success:
        raise RuntimeError(f"the integration failed: {solution.message}")
    return solution.y[0]
