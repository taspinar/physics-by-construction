"""Two-ports described by scattering parameters, and a lumped attenuator.

A two-port between two lines of reference impedance Z0 is described by the
waves that travel on them: a_j enters port j, b_i leaves port i, and
b = S a. S11 is the reflection at port 1 and S21 the transmission from
port 1 to port 2, both complex amplitude ratios. The power a wave carries is
|a|^2 (in units of the line), so |S21|^2 is the fraction of the incident
power that leaves port 2, and the fraction of the power entering port j
that the two-port absorbs is 1 - sum_i |S_ij|^2. A passive two-port absorbs
a non-negative fraction for every combination of incident waves, which is
the statement that the largest singular value of S is at most 1.

A decibel is a power ratio: 10 log10 of the power fraction, which for an
amplitude ratio |S| is 20 log10 |S|; the two give the same number.

``TeeAttenuator`` is a symmetric T network of lumped elements (the element
impedances of the RLC lesson): a series arm R + j omega L on each side and
a shunt resistor in the middle, between two matched lines of total delay
tau. A matched line only delays the wave, by e^(-j omega tau) with
tau = length / speed: the TEM limit, zero cut-off, of the guided wave of
the waveguide lesson.

Quantities are in SI units: impedances in ohm, inductances in H, delays in
s, frequencies in Hz.
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

Complex = NDArray[np.complex128]
Array = NDArray[np.float64]

__all__ = [
    "REFERENCE_IMPEDANCE",
    "TeeAttenuator",
    "absorbed_fraction",
    "amplitude_db",
    "largest_singular_value",
    "matched_tee",
    "normalised_impedance",
    "power_db",
    "power_fraction",
    "reflection",
    "symmetric_s",
]

REFERENCE_IMPEDANCE = 50.0  # ohm, the reference of the files and of the model


def amplitude_db(s: ArrayLike) -> Array:
    """20 log10 |s|: an amplitude ratio in decibels."""
    return 20.0 * np.log10(np.abs(np.asarray(s)))


def power_db(fraction: ArrayLike) -> Array:
    """10 log10 of a power ratio in decibels."""
    return 10.0 * np.log10(np.asarray(fraction, dtype=float))


def power_fraction(s: ArrayLike) -> Array:
    """|s|^2: the fraction of the incident power that an amplitude ratio
    carries."""
    return np.abs(np.asarray(s)) ** 2


def absorbed_fraction(s: ArrayLike) -> Array:
    """1 - sum_i |S_ij|^2 for ``s`` of shape (n, 2, 2): the fraction of the
    power entering port j (column j) that the two-port absorbs while the
    other port is terminated in the reference impedance; shape (n, 2)."""
    return 1.0 - np.sum(np.abs(np.asarray(s)) ** 2, axis=-2)


def largest_singular_value(s: ArrayLike) -> Array:
    """The largest singular value of S at each frequency: a passive two-port
    has at most 1."""
    return np.linalg.svd(np.asarray(s), compute_uv=False)[..., 0]


def normalised_impedance(gamma: ArrayLike) -> Complex:
    """z = Z / Z0 = (1 + Gamma) / (1 - Gamma) of a reflection coefficient."""
    gamma = np.asarray(gamma, dtype=complex)
    return (1.0 + gamma) / (1.0 - gamma)


def reflection(z: ArrayLike) -> Complex:
    """Gamma = (z - 1) / (z + 1) of a normalised impedance z = Z / Z0."""
    z = np.asarray(z, dtype=complex)
    return (z - 1.0) / (z + 1.0)


def symmetric_s(
    z11: ArrayLike, z21: ArrayLike, z0: float = REFERENCE_IMPEDANCE
) -> tuple[Complex, Complex]:
    """S11 (= S22) and S21 (= S12) of a symmetric reciprocal two-port with
    the impedance parameters Z11 = Z22 and Z21 = Z12, at reference ``z0``."""
    z11 = np.asarray(z11, dtype=complex)
    z21 = np.asarray(z21, dtype=complex)
    determinant = (z11 + z0) ** 2 - z21**2
    s11 = ((z11 - z0) * (z11 + z0) - z21**2) / determinant
    s21 = 2.0 * z21 * z0 / determinant
    return s11, s21


def matched_tee(loss_db: float, z0: float = REFERENCE_IMPEDANCE) -> tuple[float, float]:
    """The series and shunt resistances, ohm, of the resistive T pad that is
    matched to ``z0`` (S11 = 0) and passes the amplitude 10^(-loss/20):
    with k = 10^(loss/20), R_series = z0 (k - 1)/(k + 1) and
    R_shunt = 2 z0 k / (k^2 - 1)."""
    if loss_db <= 0:
        raise ValueError("a pad has a positive loss")
    k = 10.0 ** (loss_db / 20.0)
    return z0 * (k - 1.0) / (k + 1.0), 2.0 * z0 * k / (k**2 - 1.0)


@dataclass(frozen=True)
class TeeAttenuator:
    """A symmetric T network, series arms R + j omega L and a shunt
    resistor, between matched lines of total delay tau."""

    series_resistance: float  # ohm, each arm
    shunt_resistance: float  # ohm
    series_inductance: float = 0.0  # H, each arm
    delay: float = 0.0  # s, the two lines together
    z0: float = REFERENCE_IMPEDANCE

    def __post_init__(self) -> None:
        if self.series_resistance < 0 or self.shunt_resistance <= 0:
            raise ValueError("resistances must be non-negative, the shunt positive")

    def s(self, frequency: ArrayLike) -> Complex:
        """S at each frequency, Hz: shape (n, 2, 2), the Touchstone layout of
        ``pbc.data.touchstone`` (``s[k, i, j]`` is S(i+1)(j+1))."""
        omega = 2.0 * np.pi * np.atleast_1d(np.asarray(frequency, dtype=float))
        arm = self.series_resistance + 1j * omega * self.series_inductance
        shunt = np.full(omega.shape, self.shunt_resistance, dtype=complex)
        s11, s21 = symmetric_s(arm + shunt, shunt, self.z0)
        line = np.exp(-1j * omega * self.delay)
        s11, s21 = s11 * line, s21 * line
        return np.stack([[s11, s21], [s21, s11]]).transpose(2, 0, 1)
