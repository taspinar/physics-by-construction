"""The Bragg model of the X-ray diffraction lab (``pbc.materials.diffraction``)."""

import numpy as np
import pytest

from pbc.materials import diffraction

A = 4.156826  # angstrom
WAVELENGTH = 1.5405929  # angstrom


def test_the_spacing_of_cubic_planes():
    assert diffraction.index_sum((5, 1, 0)) == 26
    assert diffraction.plane_spacing(A, (1, 0, 0)) == pytest.approx(A)
    assert diffraction.plane_spacing(A, (1, 1, 0)) == pytest.approx(A / np.sqrt(2))
    assert diffraction.plane_spacing(A, (2, 2, 2)) == pytest.approx(A / np.sqrt(12))


def test_braggs_law_both_ways():
    d = diffraction.plane_spacing(A, (3, 1, 1))
    two_theta = diffraction.bragg_two_theta(d, WAVELENGTH)
    # lambda = 2 d sin(theta), directly.
    assert 2 * d * np.sin(np.radians(two_theta) / 2) == pytest.approx(WAVELENGTH)
    assert diffraction.bragg_spacing(two_theta, WAVELENGTH) == pytest.approx(d)
    assert diffraction.lattice_parameter(two_theta, (3, 1, 1), WAVELENGTH) == (
        pytest.approx(A, rel=1e-12)
    )


def test_braggs_law_places_the_certificates_reflections():
    # The certificate's Table 1 positions (information values) are those of
    # Bragg's law for the certified a and the K-alpha-1 wavelength, to the
    # 0.001 degrees they are given to.
    table = {(1, 0, 0): 21.358, (2, 1, 1): 53.990, (5, 1, 1): 148.685}
    for hkl, two_theta in table.items():
        d = diffraction.plane_spacing(A, hkl)
        assert diffraction.bragg_two_theta(d, WAVELENGTH) == pytest.approx(
            two_theta, abs=0.0015
        )


def test_the_displacement_error_of_a_is_the_first_order_formula():
    # A small displacement s on a circle R: shifting the peak by
    # -2 s cos(theta)/R makes a wrong by (s/R) cos^2(theta)/sin(theta), to
    # first order in s/R.
    s, radius = -0.01, 217.5
    for hkl in ((1, 0, 0), (3, 2, 1), (5, 1, 0)):
        true = diffraction.bragg_two_theta(
            diffraction.plane_spacing(A, hkl), WAVELENGTH
        )
        shifted = true + diffraction.displacement_shift(true, s, radius)
        error = diffraction.lattice_parameter(shifted, hkl, WAVELENGTH) / A - 1
        theta = np.radians(true) / 2
        expected = s / radius * diffraction.displacement_function(theta)
        assert error == pytest.approx(expected, rel=2e-3)
    # The shift is zero at 2 theta = 180 degrees and largest at small angles.
    assert diffraction.displacement_shift(180.0, s, radius) == pytest.approx(
        0, abs=1e-15
    )
    assert diffraction.displacement_shift(20.0, s, radius) == pytest.approx(
        np.degrees(-2 * s * np.cos(np.radians(10)) / radius)
    )


def test_the_nelson_riley_function_vanishes_at_ninety_degrees():
    assert diffraction.nelson_riley(np.pi / 2) == pytest.approx(0, abs=1e-15)
    assert diffraction.displacement_function(np.pi / 2) == pytest.approx(0, abs=1e-15)
    theta = np.radians([20.0, 40.0, 60.0, 80.0])
    values = diffraction.nelson_riley(theta)
    assert np.all(np.diff(values) < 0)
    assert np.all(values > diffraction.displacement_function(theta))
