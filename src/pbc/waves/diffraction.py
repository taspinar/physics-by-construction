"""Diffraction by slits, gratings, and a circular aperture.

An aperture in the plane z = 0 is sampled at the midpoints of small equal
pieces, and each piece sends out a wavelet. Two sums of the wavelets are
here: the field on an arc at a finite distance, with the exact distance from
every piece (Huygens and Fresnel), and the field in a direction far away,
where only the path difference x sin(theta) matters (Fraunhofer, or the focal
plane of a lens). Neither uses a formula of the pattern. The closed forms of
the zeros and the maxima are in this module to be compared with.

The slits are long in the third direction, so the problem is
two-dimensional and a wavelet is a cylindrical wave exp(i k r) / sqrt(r).
The circular aperture is computed from its radial integral with the Bessel
function J0. Lengths are in m, angles in rad.
"""

from collections.abc import Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.special import j0, jn_zeros

Array = NDArray[np.float64]

AIRY_FIRST_ZERO = float(jn_zeros(1, 1)[0] / np.pi)  # 1.2197 lambda / D


def aperture(
    openings: Sequence[tuple[float, float]], pieces: int
) -> tuple[Array, Array]:
    """The midpoints and the widths of ``pieces`` equal pieces of each open
    interval (start, end) in m."""
    if pieces < 1:
        raise ValueError("need at least one piece per opening")
    points, widths = [], []
    for start, end in openings:
        if end <= start:
            raise ValueError("an opening ends after it starts")
        h = (end - start) / pieces
        points.append(start + h * (np.arange(pieces) + 0.5))
        widths.append(np.full(pieces, h))
    return np.concatenate(points), np.concatenate(widths)


def slits(count: int, width: float, period: float, pieces: int) -> tuple[Array, Array]:
    """``count`` slits of ``width`` m, ``period`` m apart, centred on x = 0."""
    if width > period and count > 1:
        raise ValueError("the slits overlap")
    centres = (np.arange(count) - (count - 1) / 2) * period
    return aperture([(c - width / 2, c + width / 2) for c in centres], pieces)


def far_field(
    sin_theta: ArrayLike, points: ArrayLike, widths: ArrayLike, wavelength: float
) -> NDArray[np.complex128]:
    """The field far away in the direction ``sin_theta``: the sum of the
    wavelets of the pieces with the phase -k x sin(theta) of their path
    difference, weighted by their widths."""
    s = np.atleast_1d(np.asarray(sin_theta, dtype=float))
    k = 2.0 * np.pi / wavelength
    x = np.asarray(points, dtype=float)
    w = np.asarray(widths, dtype=float)
    out = np.empty(s.shape, dtype=complex)
    for start in range(0, s.size, 512):  # in blocks, to bound the memory
        block = s[start : start + 512]
        out[start : start + 512] = np.exp(-1j * k * np.outer(block, x)) @ w
    return out


def field_at(
    px: ArrayLike,
    pz: ArrayLike,
    points: ArrayLike,
    widths: ArrayLike,
    wavelength: float,
) -> NDArray[np.complex128]:
    """The field at the points (``px``, ``pz``) m in front of the aperture:
    the sum of cylindrical wavelets exp(i k r) / sqrt(r) of the pieces, with
    r the exact distance from each piece to the point."""
    px = np.atleast_1d(np.asarray(px, dtype=float))
    pz = np.broadcast_to(np.asarray(pz, dtype=float), px.shape)
    k = 2.0 * np.pi / wavelength
    x = np.asarray(points, dtype=float)
    w = np.asarray(widths, dtype=float)
    out = np.empty(px.shape, dtype=complex)
    for start in range(0, px.size, 256):  # in blocks, to bound the memory
        block = slice(start, start + 256)
        r = np.hypot(px[block, None] - x[None, :], pz[block, None])
        out[block] = (np.exp(1j * k * r) / np.sqrt(r)) @ w
    return out


def huygens_field(
    angle: ArrayLike,
    points: ArrayLike,
    widths: ArrayLike,
    wavelength: float,
    distance: float,
) -> NDArray[np.complex128]:
    """The field on an arc of radius ``distance`` m about the centre of the
    aperture, at the ``angle`` from the axis (``field_at``), times
    sqrt(``distance``) and with the constant phase k ``distance`` removed."""
    angle = np.atleast_1d(np.asarray(angle, dtype=float))
    k = 2.0 * np.pi / wavelength
    u = field_at(
        distance * np.sin(angle), distance * np.cos(angle), points, widths, wavelength
    )
    return u * np.sqrt(distance) * np.exp(-1j * k * distance)


def fresnel_number(width: float, wavelength: float, distance: float) -> float:
    """a^2 / (lambda L): small in the far field, where the Fraunhofer
    pattern holds."""
    return width**2 / (wavelength * distance)


def single_slit_zero(m: int, width: float, wavelength: float) -> float:
    """sin(theta) of zero ``m`` (not 0) of one slit: m lambda / a."""
    if m == 0:
        raise ValueError("the centre of a single slit is its maximum, not a zero")
    return m * wavelength / width


def double_slit_zero(m: int, separation: float, wavelength: float) -> float:
    """sin(theta) of the zero between fringes of two slits:
    (m + 1/2) lambda / d."""
    return (m + 0.5) * wavelength / separation


def grating_maximum(m: int, period: float, wavelength: float) -> float:
    """sin(theta) of the principal maximum of order ``m``: m lambda / d."""
    return m * wavelength / period


def resolving_power(order: int, count: int) -> float:
    """lambda / delta lambda = m N, the smallest relative difference of two
    wavelengths that a grating of ``count`` slits separates in ``order``."""
    return float(order * count)


def circular_field(
    sin_theta: ArrayLike, diameter: float, wavelength: float, pieces: int = 4000
) -> Array:
    """The far field of a circular aperture of ``diameter`` m, normalised to
    one on the axis: the radial integral of J0(k r sin(theta)) r dr over the
    aperture, by the midpoint rule with ``pieces`` rings. The field is real;
    its square is the Airy pattern."""
    s = np.atleast_1d(np.asarray(sin_theta, dtype=float))
    k = 2.0 * np.pi / wavelength
    h = diameter / 2 / pieces
    r = h * (np.arange(pieces) + 0.5)
    field = j0(k * np.outer(s, r)) @ (r * h)
    return field / (diameter**2 / 8)


def two_points(
    sin_theta: ArrayLike, separation: float, diameter: float, wavelength: float
) -> Array:
    """The image of two equally bright points that do not interfere, at
    plus and minus half the angular ``separation`` (in sin(theta)): the sum of
    their two Airy intensities."""
    s = np.asarray(sin_theta, dtype=float)
    left = circular_field(s - separation / 2, diameter, wavelength) ** 2
    right = circular_field(s + separation / 2, diameter, wavelength) ** 2
    return left + right
