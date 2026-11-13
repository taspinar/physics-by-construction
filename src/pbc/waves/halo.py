"""The diffraction halo of many small round particles.

By Babinet's principle an opaque disk diffracts, away from the direct beam,
like a round hole of the same diameter: the far field of the lesson
"Diffraction and imaging" (``pbc.waves.diffraction.circular_field``). Disks
at random places send fields with random relative phases, so on average
their intensities add, not their fields. The halo of a layer of particles is
then the Airy intensity of one disk averaged over their diameters d, each
weighted by the square of its area, d to the fourth power.

The amplitude of one disk depends on d, the angle, and the wavelength only
through u = d sin(theta) / lambda. The functions take q = sin(theta) /
lambda in 1/um and diameters in um, so that u = q d; a ring of the halo has
one q at every wavelength, and its sin(theta) is proportional to lambda.
"""

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.signal import find_peaks

from pbc.waves.diffraction import circular_field

Array = NDArray[np.float64]

PIECES = 4000  # rings of the radial integral of one disk
STEP = 0.002  # spacing of the table of the amplitude in u
BLOCK = 500  # values of u per block of the integral, to bound the memory


def disk_amplitude(u: ArrayLike, pieces: int = PIECES) -> Array:
    """The far-field amplitude of a disk at u = d sin(theta) / lambda,
    one on the axis: the radial integral of the wavelets of the round
    aperture of diameter and wavelength one (``circular_field``), in blocks."""
    u = np.atleast_1d(np.asarray(u, dtype=float))
    out = np.empty(u.shape)
    flat, result = u.ravel(), out.reshape(-1)
    for start in range(0, flat.size, BLOCK):
        block = flat[start : start + BLOCK]
        result[start : start + BLOCK] = circular_field(block, 1.0, 1.0, pieces)
    return out


def halo(q: ArrayLike, diameters: ArrayLike, step: float = STEP) -> Array:
    """The intensity of the halo of disks of ``diameters`` [um] at
    q = sin(theta) / lambda [1/um], one at q = 0: the mean of the squared
    amplitude over the disks, weighted by d^4. The amplitude is tabulated
    once in u with spacing ``step`` and interpolated."""
    q = np.atleast_1d(np.asarray(q, dtype=float))
    d = np.asarray(diameters, dtype=float)
    u = np.abs(np.outer(q, d))
    grid = np.arange(0.0, u.max() + 2 * step, step)
    amplitude = np.interp(u, grid, disk_amplitude(grid))
    weight = d**4
    return (amplitude**2 @ weight) / weight.sum()


def extrema(
    diameters: ArrayLike, count: int = 3, points: int = 30001
) -> tuple[Array, Array]:
    """q [1/um] of the first ``count`` minima and maxima of the halo: the
    extreme samples of a grid of ``points`` values of q up to six over the
    mean diameter, each refined by the vertex of the parabola through it and
    its two neighbours."""
    d = np.asarray(diameters, dtype=float)
    q = np.linspace(1e-5, 6.0 / d.mean(), points)
    intensity = halo(q, d)
    step = q[1] - q[0]

    def vertex(found: np.ndarray) -> Array:
        a, b, c = (intensity[found + k] for k in (-1, 0, 1))
        return q[found] + step * 0.5 * (a - c) / (a - 2 * b + c)

    minima, _ = find_peaks(-intensity)
    maxima, _ = find_peaks(intensity)
    return vertex(minima[:count]), vertex(maxima[:count])


def ring_radius(q: float, wavelength: float, distance: float) -> float:
    """The radius of the ring of ``q`` [1/um] at ``wavelength`` [um] on a
    flat screen ``distance`` away, in the unit of ``distance``:
    distance tan(theta) with sin(theta) = q lambda."""
    return float(distance * np.tan(np.arcsin(q * wavelength)))


def radius_ratio(q: float, short: float, long: float) -> float:
    """The radius of one ring at the wavelength ``short`` over its radius at
    ``long`` on the same flat screen; short / long for small angles."""
    return ring_radius(q, short, 1.0) / ring_radius(q, long, 1.0)


def screen_distance(radius: float, q: float, wavelength: float) -> float:
    """The distance to a flat screen at which the ring of ``q`` [1/um] at
    ``wavelength`` [um] has ``radius``, in the unit of ``radius``."""
    return radius / ring_radius(q, wavelength, 1.0)
