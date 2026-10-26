"""The far field of a thin wire antenna, built by superposition of short
current elements.

A short element of current I dz at height z on the z axis radiates, far
away in the direction theta from the axis, the field

    dE_theta = j eta k I dz sin(theta) e^(-j k r) e^(j k z cos(theta)) / (4 pi r),

where the factor e^(j k z cos(theta)) is the head start of the element's
wave over one at the origin. A wire is a line of such elements: its far
field is the sum of theirs, the element pattern sin(theta) times the
"array factor" of the current along the wire. The same superposition with
elements at other places gives the pattern of an array of antennas.

The current along a centre-fed wire of length L is assumed, not solved: the
standing wave I(z) = I_0 sin(k (L/2 - |z|)) / sin(k L / 2), which is I_0 at
the feed. The closed-form patterns of the short and the half-wave dipole
assume the same current; they are here to compare the superposition with.

Quantities are in SI units: lengths in m, angles in rad, currents in A,
resistances in ohm; patterns are normalised to one at their maximum.
"""

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.special import sici

from pbc.electromagnetism.fdtd import MU_0, SPEED_OF_LIGHT

Array = NDArray[np.float64]

__all__ = [
    "IMPEDANCE_OF_FREE_SPACE",
    "array_factor",
    "directivity",
    "far_field",
    "half_wave_dipole_pattern",
    "half_wave_radiation_resistance",
    "radiation_resistance",
    "short_dipole_pattern",
    "wire_current",
    "wire_elements",
]

IMPEDANCE_OF_FREE_SPACE = MU_0 * SPEED_OF_LIGHT  # ohm


def wire_elements(length: float, segments: int) -> tuple[Array, Array]:
    """The midpoints z (m) and the lengths dz (m) of ``segments`` equal
    elements of a wire from -length/2 to length/2 on the z axis."""
    if length <= 0 or segments < 2:
        raise ValueError("need a positive length and at least 2 segments")
    dz = length / segments
    z = -0.5 * length + dz * (np.arange(segments) + 0.5)
    return z, np.full(segments, dz)


def wire_current(z: ArrayLike, length: float, wavelength: float) -> Array:
    """The standing-wave current of a centre-fed wire, per ampere at the
    feed: sin(k (L/2 - |z|)) / sin(k L / 2)."""
    k = 2.0 * np.pi / wavelength
    feed = np.sin(0.5 * k * length)
    if abs(feed) < 1e-12:
        raise ValueError(
            "a wire of a whole number of wavelengths has no current at the feed"
        )
    return np.sin(k * (0.5 * length - np.abs(np.asarray(z, dtype=float)))) / feed


def far_field(
    theta: ArrayLike,
    phi: ArrayLike,
    positions: ArrayLike,
    currents: ArrayLike,
    wavelength: float,
) -> NDArray[np.complex128]:
    """r e^(j k r) E_theta, V, in the directions (theta, phi), of short
    z-directed elements at ``positions`` (n, 3), m, each carrying the
    current-length ``currents`` (n,), A m: the sum of the elements' fields."""
    theta = np.asarray(theta, dtype=float)
    k = 2.0 * np.pi / wavelength
    total = array_factor(theta, phi, positions, currents, wavelength)
    return 1j * IMPEDANCE_OF_FREE_SPACE * k * np.sin(theta) * total / (4.0 * np.pi)


def short_dipole_pattern(theta: ArrayLike) -> Array:
    """The field pattern |sin(theta)| of a short dipole."""
    return np.abs(np.sin(np.asarray(theta, dtype=float)))


def half_wave_dipole_pattern(theta: ArrayLike) -> Array:
    """The field pattern |cos((pi/2) cos(theta)) / sin(theta)| of a half-wave
    dipole (zero along the axis)."""
    theta = np.asarray(theta, dtype=float)
    s = np.sin(theta)
    with np.errstate(invalid="ignore", divide="ignore"):
        pattern = np.abs(np.cos(0.5 * np.pi * np.cos(theta)) / s)
    return np.where(np.abs(s) < 1e-12, 0.0, pattern)


def directivity(power: ArrayLike, theta: ArrayLike) -> float:
    """The directivity of a pattern that does not depend on phi: the largest
    radiated power per solid angle over its mean, 2 max(P) divided by the
    integral of P sin(theta) over theta from 0 to pi (trapezoidal rule on
    the samples ``theta``)."""
    power, theta = np.asarray(power, dtype=float), np.asarray(theta, dtype=float)
    return float(2.0 * power.max() / np.trapezoid(power * np.sin(theta), theta))


def radiation_resistance(
    field: ArrayLike, theta: ArrayLike, feed_current: float
) -> float:
    """The radiation resistance, ohm, of an antenna whose far field r E_theta
    (V) at the samples ``theta`` does not depend on phi: twice the radiated
    power, the integral of |r E|^2 / (2 eta) over the sphere, over the
    square of the feed current."""
    field, theta = np.asarray(field), np.asarray(theta, dtype=float)
    intensity = np.abs(field) ** 2 / (2.0 * IMPEDANCE_OF_FREE_SPACE)
    power = 2.0 * np.pi * np.trapezoid(intensity * np.sin(theta), theta)
    return float(2.0 * power / feed_current**2)


def half_wave_radiation_resistance() -> float:
    """eta Cin(2 pi) / (4 pi), ohm, about 73.1, where Cin(x) = gamma + ln x -
    Ci(x): the closed form of the radiation resistance of the half-wave
    dipole."""
    x = 2.0 * np.pi
    cin = np.euler_gamma + np.log(x) - sici(x)[1]
    return float(IMPEDANCE_OF_FREE_SPACE * cin / (4.0 * np.pi))


def array_factor(
    theta: ArrayLike,
    phi: ArrayLike,
    positions: ArrayLike,
    weights: ArrayLike,
    wavelength: float,
) -> NDArray[np.complex128]:
    """The array factor sum_n w_n e^(j k u . r_n) of identical elements at
    ``positions`` (n, 3), m, with the complex ``weights`` (n,), in the
    directions (theta, phi)."""
    k = 2.0 * np.pi / wavelength
    theta, phi = np.broadcast_arrays(
        np.asarray(theta, dtype=float), np.asarray(phi, dtype=float)
    )
    direction = np.stack(
        [np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)],
        axis=-1,
    )
    phases = np.exp(1j * k * direction @ np.asarray(positions, dtype=float).T)
    return phases @ np.asarray(weights, dtype=complex)
