"""Bragg diffraction by a cubic lattice: the model of the X-ray diffraction lab.

The crystal lattices lesson modelled a crystal as atoms on a lattice that
repeats with a spacing ``a``. A cubic lattice repeats with the same ``a``
along three perpendicular axes, and its atoms lie on families of parallel
planes, each family named by its Miller indices (h k l). X-rays of
wavelength ``lambda`` scattered by one family add in phase only when the
path difference between neighbouring planes is a whole wavelength, Bragg's
law

    lambda = 2 d sin(theta),

with ``d = a / sqrt(h^2 + k^2 + l^2)`` the spacing of the planes and
``2 theta`` the angle between the incident and the scattered beam. A
measured peak position therefore gives ``d``, and with the indices of its
reflection the lattice parameter ``a``.

A diffractometer of the Bragg-Brentano kind measures ``2 theta`` with
errors that depend on the angle. The best known is the displacement of the
specimen's surface from the axis of the goniometer: a displacement ``s``
on a circle of radius ``R`` shifts every peak by ``-2 s cos(theta) / R``
in ``2 theta`` (the sign of ``s`` is the one that makes this formula hold),
and, to first order, the lattice parameter of every reflection by the
fraction ``s cos^2(theta) / (R sin(theta))``. The error vanishes at
``theta = 90 deg``, which is why the lattice parameters of the single
reflections are extrapolated there, against the Nelson-Riley function.

Angles are in degrees where they are ``two_theta``, and in radians where they
are ``theta``; lengths in any one unit (the lab uses angstrom and mm).
"""

import numpy as np


def index_sum(hkl: tuple[int, int, int]) -> int:
    """h^2 + k^2 + l^2 of the reflection (h k l)."""
    return sum(i * i for i in hkl)


def plane_spacing(a: float, hkl: tuple[int, int, int]) -> float:
    """Spacing d of the planes (h k l) of a cubic lattice of parameter a."""
    return a / float(np.sqrt(index_sum(hkl)))


def bragg_two_theta(d, wavelength: float):
    """The angle 2 theta [degrees] at which planes of spacing d reflect
    the wavelength: lambda = 2 d sin(theta)."""
    return 2 * np.degrees(np.arcsin(wavelength / (2 * np.asarray(d, float))))


def bragg_spacing(two_theta, wavelength: float):
    """The spacing d of the planes that reflect the wavelength at 2 theta
    [degrees]: Bragg's law solved for d."""
    return wavelength / (2 * np.sin(np.radians(np.asarray(two_theta, float)) / 2))


def lattice_parameter(two_theta, hkl: tuple[int, int, int], wavelength: float):
    """The cubic lattice parameter a from the peak of (h k l) at 2 theta
    [degrees]: a = d sqrt(h^2 + k^2 + l^2)."""
    return bragg_spacing(two_theta, wavelength) * float(np.sqrt(index_sum(hkl)))


def displacement_shift(two_theta, displacement: float, radius: float):
    """The shift [degrees] of a peak at 2 theta [degrees] when the specimen's
    surface lies ``displacement`` from the goniometer's axis, on a circle of
    ``radius`` in the same unit: -2 s cos(theta) / R."""
    theta = np.radians(np.asarray(two_theta, float)) / 2
    return np.degrees(-2 * displacement * np.cos(theta) / radius)


def displacement_function(theta):
    """cos^2(theta) / sin(theta): to first order, the fractional error of
    a that a specimen displacement s gives is (s / R) times this."""
    theta = np.asarray(theta, float)
    return np.cos(theta) ** 2 / np.sin(theta)


def nelson_riley(theta):
    """The Nelson-Riley function cos^2(theta)/sin(theta) + cos^2(theta)/theta
    of theta [radians]; zero at theta = 90 degrees."""
    theta = np.asarray(theta, float)
    return np.cos(theta) ** 2 / np.sin(theta) + np.cos(theta) ** 2 / theta
