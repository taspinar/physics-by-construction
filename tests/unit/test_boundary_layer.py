"""The flat-plate boundary layer: the Blasius solution, the laminar layer at a
station, the integral thicknesses, the law of the wall, and the
Coles-Fernholz friction (the model of "Turbulent boundary layer measurements
lab", fluids 8)."""

import numpy as np
import pytest

from pbc.data.reference import tudelft_boundary_layer as reference
from pbc.fluids import boundary_layer as model


@pytest.fixture(scope="module")
def solution():
    return model.blasius()


def test_the_blasius_solution_has_the_classical_constants(solution):
    # f''(0) = 0.332057, eta_99 = 4.910, delta* = 1.7208, theta = 0.6641 in
    # units of sqrt(nu x / U), H = 2.591 (Schlichting's tables).
    assert solution.wall_curvature == pytest.approx(0.332057, abs=1e-6)
    assert solution.eta99 == pytest.approx(4.910, abs=1e-3)
    assert solution.displacement == pytest.approx(1.7208, abs=1e-4)
    assert solution.momentum == pytest.approx(0.6641, abs=1e-4)
    assert solution.shape_factor == pytest.approx(2.591, abs=1e-3)
    # The scaling reaches the free stream without a search.
    assert solution.u[0] == 0.0
    assert solution.u[-1] == pytest.approx(1.0, abs=1e-7)


def test_the_blasius_profile_solves_its_equation(solution):
    # f from u = f' by the trapezoid rule, f'' and f''' by differences of u:
    # f''' + f f'' / 2 vanishes in the interior to the error of the
    # differences, and f'' at the wall is the curvature the solver found.
    eta, u = solution.eta, solution.u
    h = eta[1] - eta[0]
    f = np.concatenate(([0.0], np.cumsum(0.5 * h * (u[1:] + u[:-1]))))
    f2 = np.gradient(u, h)
    f3 = np.gradient(f2, h)
    inner = slice(10, -10)
    assert np.max(np.abs(f3[inner] + 0.5 * f[inner] * f2[inner])) < 1e-4
    assert f2[1] == pytest.approx(solution.wall_curvature, rel=1e-3)


def test_the_two_blasius_solvers_agree(solution):
    # The lesson's RK4 with Toepfer's scaling against the reference module's
    # solve_ivp with a root search: two implementations of one equation.
    theirs = reference.blasius()
    assert solution.wall_curvature == pytest.approx(theirs.wall_curvature, rel=1e-7)
    assert solution.eta99 == pytest.approx(theirs.eta99, rel=1e-6)
    assert solution.shape_factor == pytest.approx(theirs.H, rel=1e-5)


def test_the_laminar_layer_grows_with_the_root_of_the_distance(solution):
    nu, speed = 1.5e-5, 10.0
    near = model.laminar_layer(solution, speed, nu, 1.0)
    far = model.laminar_layer(solution, speed, nu, 4.0)
    assert far["delta99"] == pytest.approx(2 * near["delta99"])
    assert far["momentum"] == pytest.approx(2 * near["momentum"])
    assert far["skin_friction"] == pytest.approx(near["skin_friction"] / 2)
    # C_f = 0.66411 / sqrt(Re_x); delta_99 = 4.91 sqrt(nu x / U).
    assert near["Re_x"] == pytest.approx(speed / nu)
    assert near["skin_friction"] == pytest.approx(
        0.66411 / np.sqrt(speed / nu), rel=1e-5
    )
    assert near["delta99"] == pytest.approx(4.91 * np.sqrt(nu / speed), rel=1e-3)
    assert near["displacement"] / near["momentum"] == pytest.approx(
        solution.shape_factor
    )


def test_the_integral_thicknesses_of_a_linear_profile():
    # u = y / delta up to delta: delta* = delta / 2, theta = delta / 6, H = 3.
    delta = 0.02
    y = np.linspace(0.0, delta, 20001)
    ds, th, h = model.integral_thicknesses(y, y / delta, delta)
    assert ds == pytest.approx(delta / 2, rel=1e-9)
    assert th == pytest.approx(delta / 6, rel=1e-7)
    assert h == pytest.approx(3.0, rel=1e-7)
    # Beyond delta nothing is added.
    y2 = np.concatenate((y, [0.03]))
    assert model.integral_thicknesses(y2, np.append(y / delta, 1.0), delta) == (
        ds,
        th,
        h,
    )


def test_the_thickness_99_is_interpolated_and_refuses_a_profile_without_it():
    y = np.linspace(0.0, 1.0, 11)
    assert model.thickness_99(y, y) == pytest.approx(0.99)
    with pytest.raises(ValueError):
        model.thickness_99(y, np.full_like(y, 1.0))


def test_the_law_of_the_wall():
    yplus = np.array([1.0, 10.0, 100.0, 1000.0])
    np.testing.assert_array_equal(model.sublayer(yplus), yplus)
    law = model.log_law(yplus, 0.41, 5.0)
    np.testing.assert_allclose(np.diff(law), np.log(10.0) / 0.41)
    assert model.log_law(1.0, 0.41, 5.0) == 5.0
    # The sublayer and the log law meet near y+ = 11 for these constants.
    grid = np.linspace(5.0, 20.0, 1501)
    crossing = grid[
        np.argmin(np.abs(model.sublayer(grid) - model.log_law(grid, 0.41, 5.0)))
    ]
    assert 10.5 < crossing < 11.5


def test_the_coles_fernholz_friction_is_the_reference_modules():
    for speed, re_theta in ((4.574, 3079.0), (18.28, 12020.0), (15.0, 3421.0)):
        assert model.coles_fernholz_friction(speed, re_theta) == pytest.approx(
            reference.coles_fernholz_utau(speed, re_theta), rel=1e-12
        )
    # C_f falls slowly with Re_theta: about 3.3e-3 at 3000, 2.5e-3 at 12000.
    cf = [2 * (model.coles_fernholz_friction(1.0, r)) ** 2 for r in (3000.0, 12000.0)]
    assert cf[0] == pytest.approx(3.3e-3, abs=1e-4)
    assert cf[1] == pytest.approx(2.5e-3, abs=1e-4)
