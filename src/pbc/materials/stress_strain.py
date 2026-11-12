"""The uniaxial stress-strain relations a tension test is read with.

The lesson "Elasticity and deformation" models a solid as linear elastic,
sigma = E epsilon. Along one axis that is a straight line through the
origin; a measured test adds an intercept for the zero of the instruments.
The functions here are that line, the offset construction that measures how
far a curve has left it, the line a purely elastic unloading would follow,
the work per volume of a closed path in the stress-strain plane, and the
true stress and strain of a uniform bar. Stresses are in MPa, moduli in
GPa, strains are dimensionless (mm/mm).
"""

import numpy as np
from numpy.typing import ArrayLike, NDArray

Array = NDArray[np.float64]


def hooke_stress(strain: ArrayLike, modulus: float, intercept: float = 0.0) -> Array:
    """Hooke's law along one axis, S = E e + S0, in MPa for E in GPa."""
    return modulus * 1e3 * np.asarray(strain, dtype=float) + intercept


def offset_crossing(
    strain: ArrayLike,
    stress: ArrayLike,
    modulus: float,
    offset: float,
    intercept: float = 0.0,
) -> float:
    """The stress [MPa] where a loading curve first falls below the elastic
    line shifted by ``offset`` in strain, interpolated linearly between the
    two samples on either side. Only samples with a strain above the offset
    count, so the start of the curve, below the shifted line's foot, is
    never taken for a crossing."""
    e = np.asarray(strain, dtype=float)
    s = np.asarray(stress, dtype=float)
    gap = s - hooke_stress(e - offset, modulus, intercept)
    below = np.flatnonzero((gap < 0) & (e > offset))
    if below.size == 0 or below[0] == 0:
        raise ValueError("the curve does not cross the shifted line")
    k = int(below[0])
    w = gap[k - 1] / (gap[k - 1] - gap[k])
    return float(s[k - 1] + w * (s[k] - s[k - 1]))


def elastic_unloading(
    strain: ArrayLike, start_strain: float, start_stress: float, modulus: float
) -> Array:
    """The stress [MPa] of a purely elastic unloading from the point
    (``start_strain``, ``start_stress``): the line of slope E through it,
    which is what the linear elastic model predicts whatever the material
    did before."""
    e = np.asarray(strain, dtype=float)
    return start_stress + modulus * 1e3 * (e - start_strain)


def closed_loop_work(strain: ArrayLike, stress: ArrayLike) -> tuple[float, float]:
    """The closed integral of S de [MJ/m^3 for MPa] over the path through
    the points in order, closed by a straight segment from the last point
    back to the first; returns (the integral, the closing segment's part).

    Trapezoids over the points plus the closing segment: for a polygon
    that is the exact integral, equal to the shoelace area when the path
    runs clockwise in the (e, S) plane and does not cross itself, and minus
    that area when it runs anticlockwise. The work per volume done on a
    material over a cycle is positive."""
    e = np.asarray(strain, dtype=float)
    s = np.asarray(stress, dtype=float)
    open_part = float(np.sum(0.5 * (s[1:] + s[:-1]) * np.diff(e)))
    closing = float(0.5 * (s[0] + s[-1]) * (e[0] - e[-1]))
    return open_part + closing, closing


def true_stress_strain(strain: ArrayLike, stress: ArrayLike) -> tuple[Array, Array]:
    """The true strain ln(1 + e) and the true stress S (1 + e) of a bar that
    deforms uniformly at constant volume; neither holds once it necks."""
    e = np.asarray(strain, dtype=float)
    s = np.asarray(stress, dtype=float)
    return np.log1p(e), s * (1 + e)
