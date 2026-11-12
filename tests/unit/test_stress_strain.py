"""The uniaxial stress-strain relations of the stress-strain lab (MAT6,
``pbc.materials.stress_strain``): each against a case whose answer is known
in closed form."""

import numpy as np
import pytest

from pbc.materials.stress_strain import (
    closed_loop_work,
    elastic_unloading,
    hooke_stress,
    offset_crossing,
    true_stress_strain,
)


def test_hookes_law_is_the_line_of_the_modulus_in_mpa_for_gpa():
    strain = np.array([0.0, 0.001, 0.002])
    # 200 GPa times a strain of 0.001 is 200 MPa.
    np.testing.assert_allclose(hooke_stress(strain, 200.0), [0.0, 200.0, 400.0])
    np.testing.assert_allclose(hooke_stress(strain, 200.0, 5.0), [5.0, 205.0, 405.0])


def _bilinear(modulus: float, yield_stress: float, hardening: float):
    """An elastic line to the yield stress, then a line of slope
    ``hardening`` (GPa), sampled finely."""
    strain = np.linspace(0, 0.02, 4001)
    elastic = hooke_stress(strain, modulus)
    knee = yield_stress / (modulus * 1e3)
    plastic = yield_stress + hardening * 1e3 * (strain - knee)
    return strain, np.where(strain < knee, elastic, plastic)


def test_the_offset_crossing_of_a_bilinear_curve_is_its_closed_form():
    modulus, yield_stress, hardening = 200.0, 500.0, 2.0
    strain, stress = _bilinear(modulus, yield_stress, hardening)
    offset = 0.002
    # Plastic branch S = Y + H (e - Y/E) meets S = E (e - offset) where
    # e = (Y - H Y/E + E offset) / (E - H).
    e_cross = (yield_stress * (1 - hardening / modulus) + modulus * 1e3 * offset) / (
        (modulus - hardening) * 1e3
    )
    expected = modulus * 1e3 * (e_cross - offset)
    found = offset_crossing(strain, stress, modulus, offset)
    assert found == pytest.approx(expected, rel=1e-9)
    assert found > yield_stress


def test_the_offset_crossing_ignores_the_foot_of_the_shifted_line():
    # A curve that is elastic everywhere never crosses a shifted line to
    # its right; the first samples, below the line's foot, do not count.
    strain = np.linspace(0, 0.01, 101)
    with pytest.raises(ValueError):
        offset_crossing(strain, hooke_stress(strain, 200.0), 200.0, 0.002)


def test_an_elastic_unloading_recovers_stress_over_modulus():
    start_strain, start_stress, modulus = 0.05, 980.0, 196.0
    at_zero = start_strain - start_stress / (modulus * 1e3)
    line = elastic_unloading(
        np.array([start_strain, at_zero]), start_strain, start_stress, modulus
    )
    np.testing.assert_allclose(line, [start_stress, 0.0], atol=1e-9)


def _ellipse(n: int, clockwise: bool):
    phi = np.linspace(0, 2 * np.pi, n, endpoint=False)
    if clockwise:
        phi = -phi
    return 0.03 * np.cos(phi), 800.0 * np.sin(phi)


def test_the_closed_integral_of_a_clockwise_ellipse_converges_to_its_area():
    exact = np.pi * 0.03 * 800.0
    errors = []
    for n in (100, 200, 400):
        work, _ = closed_loop_work(*_ellipse(n, clockwise=True))
        assert 0 < work < exact
        errors.append(exact - work)
    # Second order: halving the step divides the error by four.
    assert errors[0] / errors[1] == pytest.approx(4.0, rel=0.01)
    assert errors[1] / errors[2] == pytest.approx(4.0, rel=0.01)


def test_the_closed_integral_changes_sign_with_the_direction():
    clockwise, _ = closed_loop_work(*_ellipse(200, clockwise=True))
    anticlockwise, _ = closed_loop_work(*_ellipse(200, clockwise=False))
    assert anticlockwise == pytest.approx(-clockwise, rel=1e-12)


def test_the_closed_integral_of_a_polygon_is_its_shoelace_area():
    # A unit-square-like loop run clockwise from its top-right corner,
    # open at the end: the closing segment completes it.
    e = np.array([0.01, 0.01, 0.0, 0.0])
    s = np.array([100.0, 0.0, 0.0, 100.0])
    work, closing = closed_loop_work(e, s)
    assert work == pytest.approx(1.0)  # 0.01 times 100 MPa
    # The closing segment runs from (0, 100) to (0.01, 100).
    assert closing == pytest.approx(1.0)


def test_true_stress_and_strain_are_those_of_a_uniform_bar():
    true_e, true_s = true_stress_strain(np.array([0.0, 0.1]), np.array([500.0, 900.0]))
    np.testing.assert_allclose(true_e, [0.0, np.log(1.1)])
    np.testing.assert_allclose(true_s, [500.0, 990.0])
