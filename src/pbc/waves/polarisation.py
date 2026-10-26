"""Polarisation of light: Jones vectors and matrices, the intensity of the
real field, Stokes parameters, and unpolarised light as an ensemble.

A monochromatic plane wave along z has the transverse field
E(t) = Re(J exp(-i omega t)), with the complex Jones vector J = (Ex, Ey).
An optical element acts on J by a 2 x 2 complex matrix. The intensity is
measured here as the time average of |E(t)|^2 over one period of the real
field, sampled at equal steps, and normalised so that |J| = 1 gives one;
Malus's law and the Stokes parameters are results of that measurement, and
their closed forms are in this module to be compared with.

Angles are in radians, from the x axis towards the y axis.
"""

import numpy as np
from numpy.typing import ArrayLike, NDArray

Array = NDArray[np.float64]
Jones = NDArray[np.complex128]

SAMPLES = 16  # samples of the field per period; any number above two is exact


def linear(angle: float) -> Jones:
    """Light polarised along the direction ``angle``."""
    return np.array([np.cos(angle), np.sin(angle)], dtype=complex)


def circular(sense: int = 1) -> Jones:
    """Circularly polarised light whose field turns from x towards y
    (``sense`` = 1) or from y towards x (``sense`` = -1)."""
    if sense not in (1, -1):
        raise ValueError("the sense is 1 or -1")
    return np.array([1.0, sense * 1j], dtype=complex) / np.sqrt(2.0)


def rotation(angle: float) -> NDArray[np.float64]:
    """The matrix that turns a vector by ``angle``."""
    c, s = np.cos(angle), np.sin(angle)
    return np.array([[c, -s], [s, c]])


def polariser(angle: float, leak: float = 0.0) -> Jones:
    """A linear polariser that passes the field along ``angle`` and, of the
    field across it, the amplitude sqrt(``leak``): ``leak`` is the fraction
    of the power polarised across the axis that it lets through, the
    inverse of its extinction ratio. ``leak`` = 0 is an ideal polariser."""
    if not 0.0 <= leak <= 1.0:
        raise ValueError("the leak is a fraction of the power, from 0 to 1")
    return (
        rotation(angle)
        @ np.diag([1.0, np.sqrt(leak)]).astype(complex)
        @ rotation(-angle)
    )


def retarder(angle: float, retardance: float) -> Jones:
    """A wave plate with its fast axis along ``angle``: the field along the
    slow axis is delayed by the phase ``retardance`` (rad). A quarter-wave
    plate has pi / 2, a half-wave plate pi."""
    phase = np.diag([1.0, np.exp(1j * retardance)])
    return rotation(angle) @ phase @ rotation(-angle)


def field(jones: ArrayLike, samples: int = SAMPLES) -> Array:
    """The real field Re(J exp(-i omega t)) at ``samples`` equal steps of
    one period. For a Jones vector of shape (..., 2) the result has the
    shape (..., samples, 2)."""
    phase = np.exp(-2j * np.pi * np.arange(samples) / samples)
    jones = np.asarray(jones, dtype=complex)
    return np.real(jones[..., None, :] * phase[:, None])


def intensity(jones: ArrayLike, samples: int = SAMPLES) -> Array:
    """The time average of |E(t)|^2 over one period of the real field,
    times two, so that a Jones vector of unit length has intensity one;
    one value per Jones vector of shape (..., 2). The average of cos^2 over
    three or more equal steps of a period is exactly one half, so the
    sampling adds no error beyond round-off."""
    e = field(jones, samples)
    return 2.0 * np.mean(np.sum(e**2, axis=-1), axis=-1)


def analysers() -> dict[str, Jones]:
    """The six analysers of a Stokes measurement: polarisers along x, y,
    +45 and -45 degrees, and a quarter-wave plate with its fast axis along
    x followed by a polariser at -45 or +45 degrees, which passes the
    circular light that turns from x towards y, or from y towards x."""
    quarter = retarder(0.0, np.pi / 2)
    return {
        "x": polariser(0.0),
        "y": polariser(np.pi / 2),
        "+45": polariser(np.pi / 4),
        "-45": polariser(-np.pi / 4),
        "turning x to y": polariser(-np.pi / 4) @ quarter,
        "turning y to x": polariser(np.pi / 4) @ quarter,
    }


def stokes_measured(states: ArrayLike) -> Array:
    """The Stokes parameters (S0, S1, S2, S3) of a beam, from the mean
    intensities behind the six analysers. ``states`` is one Jones vector or
    an ensemble of them, shape (n, 2), whose intensities add: light whose
    states are not coherent with each other."""
    states = np.atleast_2d(np.asarray(states, dtype=complex))
    means = {
        name: float(np.mean(intensity(states @ m.T))) for name, m in analysers().items()
    }
    return np.array(
        [
            means["x"] + means["y"],
            means["x"] - means["y"],
            means["+45"] - means["-45"],
            means["turning x to y"] - means["turning y to x"],
        ]
    )


def stokes_closed(jones: ArrayLike) -> Array:
    """The Stokes parameters of one Jones vector from their closed forms:
    |Ex|^2 + |Ey|^2, |Ex|^2 - |Ey|^2, 2 Re(conj(Ex) Ey), 2 Im(conj(Ex) Ey)."""
    ex, ey = np.asarray(jones, dtype=complex)
    cross = np.conj(ex) * ey
    return np.array(
        [
            abs(ex) ** 2 + abs(ey) ** 2,
            abs(ex) ** 2 - abs(ey) ** 2,
            2 * cross.real,
            2 * cross.imag,
        ]
    )


def degree_of_polarisation(stokes: ArrayLike) -> float:
    """sqrt(S1^2 + S2^2 + S3^2) / S0: one for a pure state, zero for
    unpolarised light."""
    s = np.asarray(stokes, dtype=float)
    return float(np.sqrt(np.sum(s[1:] ** 2)) / s[0])


def unpolarised(n: int, rng: np.random.Generator) -> Jones:
    """``n`` Jones vectors of unit intensity with independent Gaussian
    complex components, normalised: states spread evenly over all
    polarisations, a model of unpolarised light as an incoherent ensemble."""
    z = rng.standard_normal((n, 2)) + 1j * rng.standard_normal((n, 2))
    return z / np.linalg.norm(z, axis=1, keepdims=True)


def malus(angle: ArrayLike, leak: float = 0.0) -> Array:
    """Malus's law for an analyser at ``angle`` to the polarisation of the
    light, cos^2(angle), with a leaky analyser cos^2 + leak sin^2."""
    angle = np.asarray(angle, dtype=float)
    return np.cos(angle) ** 2 + leak * np.sin(angle) ** 2


def chain_transmission(n: int) -> float:
    """The closed form cos^(2n)(pi / 2n) of the power that passes ``n``
    ideal polarisers, each turned by pi / 2n from the one before, behind
    light polarised along the first direction."""
    return float(np.cos(np.pi / (2 * n)) ** (2 * n))
