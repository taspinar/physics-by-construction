"""The halo of many disks (``pbc.waves.halo``): the wavelet integral of the
round aperture of "Diffraction and imaging" against the closed form, the
zeros of one disk, the weighting by area squared, the scaling with q d, and
the geometry of a flat screen."""

import numpy as np
import pytest
from scipy.special import j1, jn_zeros

from pbc.waves import halo


def _closed_form(u):
    u = np.asarray(u, dtype=float)
    safe = np.where(u > 0, np.pi * u, 1.0)
    return np.where(u > 0, 2 * j1(safe) / safe, 1.0)


def test_the_wavelet_integral_of_one_disk_is_the_closed_form():
    u = np.linspace(0.0, 10.0, 2001)
    assert np.max(np.abs(halo.disk_amplitude(u) - _closed_form(u))) < 1e-7
    assert halo.disk_amplitude(0.0)[0] == pytest.approx(1.0, abs=1e-12)


def test_the_amplitude_keeps_the_shape_of_its_argument():
    u = np.linspace(0.1, 3.0, 12).reshape(3, 4)
    assert halo.disk_amplitude(u).shape == (3, 4)
    # More values than one block of the integral.
    long = np.linspace(0.0, 8.0, 3 * halo.BLOCK + 7)
    assert np.max(np.abs(halo.disk_amplitude(long) - _closed_form(long))) < 1e-7


def test_the_halo_of_one_disk_has_the_airy_zeros():
    minima, maxima = halo.extrema([30.0])
    np.testing.assert_allclose(30.0 * minima, jn_zeros(1, 3) / np.pi, atol=2e-4)
    # The first bright ring lies between the first two zeros.
    assert minima[0] < maxima[0] < minima[1]


def test_the_halo_weights_each_disk_by_its_area_squared():
    q = np.linspace(0.0, 0.3, 61)
    small, large = 20.0, 40.0
    expected = (
        small**4 * _closed_form(q * small) ** 2
        + large**4 * _closed_form(q * large) ** 2
    ) / (small**4 + large**4)
    np.testing.assert_allclose(halo.halo(q, [small, large]), expected, atol=1e-5)
    assert halo.halo(0.0, [small, large])[0] == pytest.approx(1.0, abs=1e-12)


def test_the_halo_depends_on_q_times_d_only():
    d = np.array([25.0, 28.0, 31.0, 36.0])
    q = np.linspace(0.0, 0.2, 41)
    np.testing.assert_allclose(halo.halo(q, 2 * d), halo.halo(2 * q, d), atol=1e-5)


def test_a_spread_of_sizes_fills_the_dark_rings():
    # One disk goes dark at its zeros; a spread of diameters does not.
    d = np.linspace(26.0, 34.0, 9)
    minima, _ = halo.extrema(d)
    one = halo.halo(jn_zeros(1, 1) / np.pi / 30.0, [30.0])[0]
    assert one < 1e-6
    assert halo.halo(minima[0], d)[0] > 100 * one


def test_a_ring_on_a_flat_screen():
    q, wavelength, distance = 0.04, 0.6328, 500.0
    radius = halo.ring_radius(q, wavelength, distance)
    assert np.sin(np.arctan(radius / distance)) == pytest.approx(q * wavelength)
    assert halo.screen_distance(radius, q, wavelength) == pytest.approx(distance)
    # For small angles the radii scale with the wavelength; the tangent of a
    # flat screen makes the shorter wavelength's ring slightly smaller.
    ratio = halo.radius_ratio(q, 0.405, 0.6328)
    assert ratio == pytest.approx(0.405 / 0.6328, rel=1e-3)
    assert ratio < 0.405 / 0.6328
    assert halo.radius_ratio(1e-6, 0.405, 0.6328) == pytest.approx(
        0.405 / 0.6328, rel=1e-9
    )
