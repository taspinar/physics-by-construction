"""Vorticity from a measured velocity grid, and the tests of a vortex street
(lesson FL7, the cylinder-wake PIV lab).

A PIV record gives the velocity (u, v) on a uniform grid of spacing h, with
points where there is no data (a mask). The vorticity w = dv/dx - du/dy is
not measured: it is a derivative of the measured field, computed here by one
of two finite-difference stencils.

- The central difference (f[i+1] - f[i-1]) / 2h, the stencil of FL3's
  solver and of the dataset's reference module: error h^2/6 f''' and, for
  independent errors of standard deviation s in each vector, a vorticity
  noise of s / h.
- The five-point least-squares stencil
  (2 f[i+2] + f[i+1] - f[i-1] - 2 f[i-2]) / 10h, the slope of the straight
  line fitted to five points: error 17/30 h^2 f''' (3.4 times larger) and a
  noise of sqrt(1/5) s / h, 0.447 times that of the central difference.

Neither stencil is used where it touches a masked point. ``lamb_oseen`` is
an analytic vortex on which both are checked, and ``band_pass`` and
``reflect`` serve the tests of the measured street.
"""

import numpy as np
from numpy.typing import NDArray
from scipy import ndimage, signal

__all__ = [
    "NOISE_GAIN",
    "REACH",
    "STENCILS",
    "TRUNCATION",
    "band_pass",
    "central_derivative",
    "lamb_oseen",
    "least_squares_derivative",
    "reflect",
    "vorticity",
]

Array = NDArray[np.float64]

STENCILS = ("central", "least squares")
# How many points each stencil reaches on either side of the centre.
REACH = {"central": 1, "least squares": 2}
# The leading truncation error of the derivative, as a multiple of h^2 f'''.
TRUNCATION = {"central": 1.0 / 6.0, "least squares": 17.0 / 30.0}
# The noise of the vorticity, in units of s / h, for independent errors of
# standard deviation s in u and v: each derivative contributes the root sum
# of the squares of its weights over its denominator.
NOISE_GAIN = {"central": 1.0, "least squares": float(np.sqrt(1.0 / 5.0))}


def _shifted(f: Array, axis: int, start: int, stop: int) -> Array:
    """The slice ``start:stop`` (``stop`` may be 0 for the end) along ``axis``."""
    index = [slice(None)] * f.ndim
    index[axis] = slice(start, None if stop == 0 else stop)
    return f[tuple(index)]


# region: stencils
def central_derivative(f: Array, h: float, axis: int) -> Array:
    """df/dx along ``axis`` by (f[i+1] - f[i-1]) / 2h; NaN at the two ends."""
    out = np.full(f.shape, np.nan)
    inner = [slice(None)] * f.ndim
    inner[axis] = slice(1, -1)
    out[tuple(inner)] = (_shifted(f, axis, 2, 0) - _shifted(f, axis, 0, -2)) / (2 * h)
    return out


def least_squares_derivative(f: Array, h: float, axis: int) -> Array:
    """df/dx along ``axis`` by (2 f[i+2] + f[i+1] - f[i-1] - 2 f[i-2]) / 10h,
    the slope of the least-squares line through five points; NaN at the two
    points at each end."""
    out = np.full(f.shape, np.nan)
    inner = [slice(None)] * f.ndim
    inner[axis] = slice(2, -2)
    out[tuple(inner)] = (
        2 * _shifted(f, axis, 4, 0)
        + _shifted(f, axis, 3, -1)
        - _shifted(f, axis, 1, -3)
        - 2 * _shifted(f, axis, 0, -4)
    ) / (10 * h)
    return out


# endregion: stencils


def vorticity(
    u: Array, v: Array, h: float, stencil: str = "central", mask: Array | None = None
) -> Array:
    """dv/dx - du/dy [1/s] of fields indexed [..., y, x] on a uniform grid of
    spacing ``h``; NaN at the edges the stencil cannot reach and wherever it
    touches a point of ``mask`` (True: no data)."""
    derivative = {
        "central": central_derivative,
        "least squares": least_squares_derivative,
    }[stencil]
    omega = derivative(v, h, -1) - derivative(u, h, -2)
    if mask is not None:
        width = 2 * REACH[stencil] + 1
        structure = np.ones((1,) * (mask.ndim - 2) + (width, width), bool)
        omega = np.where(ndimage.binary_dilation(mask, structure), np.nan, omega)
    return omega


def lamb_oseen(
    x: Array, y: Array, circulation: float = 1.0, core: float = 1.0
) -> tuple[Array, Array, Array]:
    """u, v and the vorticity of a Lamb-Oseen vortex centred at the origin:
    the azimuthal speed G / (2 pi r) (1 - exp(-r^2 / c^2)) and the vorticity
    G / (pi c^2) exp(-r^2 / c^2), for the circulation G and the core c."""
    r2 = x**2 + y**2
    safe = np.where(r2 > 0, r2, 1.0)
    swirl = np.where(
        r2 > 0, circulation / (2 * np.pi * safe) * (1 - np.exp(-r2 / core**2)), 0.0
    )
    omega = circulation / (np.pi * core**2) * np.exp(-r2 / core**2)
    return -swirl * y, swirl * x, omega


def band_pass(series: Array, low: float, high: float, rate: float) -> Array:
    """The series filtered forwards and backwards (no phase shift) by a
    second-order Butterworth band-pass from ``low`` to ``high`` [Hz] at the
    sampling ``rate`` [Hz]."""
    sos = signal.butter(2, (low, high), btype="band", fs=rate, output="sos")
    return signal.sosfiltfilt(sos, np.asarray(series, dtype=float))


# region: reflect
def reflect(field: Array, axis_row: int, rows: int) -> tuple[Array, Array]:
    """The ``rows`` rows on either side of ``axis_row`` of a field [..., y, x],
    and the same band reflected about that row (the first axis of the band
    reversed): a vortex street maps onto itself after half a period under
    this reflection with the sign of the vorticity flipped."""
    band = field[..., axis_row - rows : axis_row + rows + 1, :]
    return band, band[..., ::-1, :]


# endregion: reflect
