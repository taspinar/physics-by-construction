"""The heat conduction model: lumped cooling, the explicit scheme, its
boundaries, stability, and the exact references (pbc.thermodynamics.conduction)."""

import numpy as np
import pytest

from pbc.thermodynamics import conduction
from pbc.thermodynamics.conduction import Convective, Fixed, Material

STEEL = Material(k=45.0, rho=7850.0, c=490.0)


def test_the_diffusivity_is_k_over_rho_c():
    assert STEEL.diffusivity == pytest.approx(45.0 / (7850.0 * 490.0))


def test_lumped_cooling_is_the_exponential_with_tau_rho_c_l_over_h():
    tau = conduction.lumped_time_constant(STEEL, 0.01, 50.0)
    assert tau == pytest.approx(7850.0 * 490.0 * 0.01 / 50.0)
    t = np.array([0.0, tau, 2 * tau])
    np.testing.assert_allclose(
        conduction.lumped_temperature(t, 100.0, 20.0, tau),
        20.0 + 80.0 * np.exp([0.0, -1.0, -2.0]),
    )


def test_a_uniform_state_at_the_fluid_temperature_does_not_change():
    end = Convective(h=500.0, ambient=20.0)
    state = np.full(11, 20.0)
    new = conduction.ftcs_step(state, 0.3, 0.001, 45.0, end, end)
    np.testing.assert_array_equal(new, state)


def test_a_linear_profile_between_fixed_ends_is_steady():
    state = np.linspace(100.0, 20.0, 21)
    new = conduction.ftcs_step(state, 0.4, 0.001, 45.0, Fixed(100.0), Fixed(20.0))
    np.testing.assert_allclose(new, state, rtol=0, atol=1e-12)


def test_the_ghost_node_end_keeps_a_steady_profile_with_the_matching_flux():
    """A linear profile whose slope is the convective flux at both ends is a
    steady solution of the continuous problem, and the ghost node keeps it
    exactly."""
    k, h, fluid = 45.0, 300.0, 20.0
    x = np.linspace(0.0, 0.04, 41)
    # T(x) = a + b x with k b = h (T(0) - fluid) at x = 0 and
    # -k b = h (T(L) - fluid') at x = L; choose the fluid at the far end.
    a, b = 120.0, h * (120.0 - fluid) / k
    far = a + b * x[-1] + k * b / h
    state = a + b * x
    new = conduction.ftcs_step(
        state, 0.3, x[1], k, Convective(h, fluid), Convective(h, far)
    )
    np.testing.assert_allclose(new, state, rtol=0, atol=1e-9)


def test_the_grid_energy_changes_by_exactly_the_heat_out_of_the_ends():
    dx, dt = 0.002, 0.05
    r = STEEL.diffusivity * dt / dx**2
    ends = (Convective(800.0, 20.0), Convective(100.0, 50.0))
    states = conduction.march(
        np.linspace(200.0, 150.0, 21),
        500,
        lambda t: conduction.ftcs_step(t, r, dx, STEEL.k, *ends),
    )
    lost = conduction.grid_energy(states[0], dx, STEEL) - conduction.grid_energy(
        states[-1], dx, STEEL
    )
    assert lost == pytest.approx(
        conduction.convective_loss(states[:-1], dt, ends), rel=1e-12
    )


def test_the_positive_step_limit_shrinks_with_the_cell_biot_number():
    assert conduction.positive_step_limit(0.001, 45.0, (Fixed(0.0),)) == 0.5
    assert conduction.positive_step_limit(
        0.001, 45.0, (Convective(45000.0, 0.0),)
    ) == pytest.approx(0.25)


@pytest.mark.parametrize("dimension", [1, 2])
def test_the_measured_stability_limit_is_the_limit_of_the_grid(dimension):
    n = 12
    rng = np.random.default_rng(0)
    state = np.zeros((n + 2,) * dimension)
    state[(slice(1, -1),) * dimension] = rng.standard_normal((n,) * dimension)

    def step(r):
        if dimension == 1:
            return lambda t: conduction.ftcs_step(
                t, r, 1.0, 1.0, Fixed(0.0), Fixed(0.0)
            )
        return lambda t: conduction.ftcs_step_2d(t, r)

    def growth(r):
        return conduction.growth_per_step(step(r), state, 400)

    found = conduction.stability_limit(growth, 0.1, 0.7 / dimension, 1e-6)
    exact = conduction.discrete_stability_limit(n, dimension)
    assert found == pytest.approx(exact, abs=2e-6)
    assert exact > 1 / (2 * dimension)


def test_the_stability_limit_refuses_a_bracket_that_does_not_cross_one():
    with pytest.raises(ValueError):
        conduction.stability_limit(lambda r: 0.5, 0.1, 0.2, 1e-3)


def test_the_slab_eigenvalues_solve_lambda_tan_lambda_equals_bi():
    lam = conduction.slab_eigenvalues(2.0, 6)
    np.testing.assert_allclose(lam * np.tan(lam), 2.0, rtol=1e-10)
    assert np.all(np.diff(lam) > 0)


def test_the_slab_series_starts_uniform_and_meets_the_lumped_model_at_small_biot():
    x = np.linspace(-0.9, 0.9, 7)
    np.testing.assert_allclose(
        conduction.slab_temperature(x, 1e-3, 1.0, 2000), 1.0, atol=2e-3
    )
    # Bi -> 0: the mean decays as exp(-Bi Fo), the lumped exponential.
    bi, fo = 1e-3, np.array([10.0, 100.0, 500.0])
    np.testing.assert_allclose(
        conduction.slab_mean_temperature(fo, bi), np.exp(-bi * fo), rtol=1e-3
    )


def test_the_steady_plate_reproduces_a_harmonic_function():
    """T = x^2 - y^2 + 3 x y is harmonic and the five-point stencil is exact
    for it, so the sparse solve returns it at every node."""
    n, side = 16, 1.0
    s = np.linspace(0.0, side, n + 1)
    y, x = np.meshgrid(s, s, indexing="ij")
    exact = x**2 - y**2 + 3 * x * y
    boundary = exact.copy()
    boundary[1:-1, 1:-1] = 0.0
    found = conduction.steady_plate(boundary, np.zeros_like(exact), side / n, 1.0)
    np.testing.assert_allclose(found, exact, atol=1e-12)


def test_the_steady_plate_balances_a_uniform_source():
    """-k laplacian T = q with T = q x (1 - x) / (2 k) on the side walls: the
    stencil is exact for this quadratic."""
    n, k, q = 10, 2.0, 50.0
    s = np.linspace(0.0, 1.0, n + 1)
    _, x = np.meshgrid(s, s, indexing="ij")
    exact = q * x * (1 - x) / (2 * k)
    boundary = exact.copy()
    boundary[1:-1, 1:-1] = 0.0
    found = conduction.steady_plate(boundary, np.full_like(exact, q), 1.0 / n, k)
    np.testing.assert_allclose(found, exact, atol=1e-12)
