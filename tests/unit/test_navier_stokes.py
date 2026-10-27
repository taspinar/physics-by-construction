"""The incompressible solver on the periodic staggered grid: its discrete
operators, the projection, the step, and the exact references
(pbc.fluids.navier_stokes)."""

import numpy as np
import pytest

from pbc.fluids import navier_stokes as ns
from pbc.fluids.navier_stokes import Grid

GRID = Grid(24, 16, 2 * np.pi, 2 * np.pi)


def smooth_field(grid: Grid) -> tuple[np.ndarray, np.ndarray]:
    xu, yu = grid.points("u")
    xv, yv = grid.points("v")
    return np.sin(xu) * np.cos(2 * yu) + 0.3, np.cos(3 * xv) * np.sin(yv) - 0.2


def test_the_points_of_the_staggered_grid():
    x, y = GRID.points("u")
    assert x[0, 1] == pytest.approx(GRID.dx) and y[0, 0] == pytest.approx(GRID.dy / 2)
    x, y = GRID.points("v")
    assert x[0, 0] == pytest.approx(GRID.dx / 2) and y[1, 0] == pytest.approx(GRID.dy)
    x, y = GRID.points("p")
    assert (x[0, 0], y[0, 0]) == pytest.approx((GRID.dx / 2, GRID.dy / 2))


def test_the_divergence_of_the_gradient_is_the_five_point_laplacian():
    rng = np.random.default_rng(3)
    p = rng.normal(size=(GRID.ny, GRID.nx))
    np.testing.assert_allclose(
        ns.divergence(*ns.gradient(p, GRID), GRID), ns.laplacian(p, GRID), atol=1e-11
    )


def test_the_divergence_is_the_net_outflow_of_a_cell():
    u = np.zeros((GRID.ny, GRID.nx))
    v = np.zeros((GRID.ny, GRID.nx))
    u[3, 5] = 1.0  # flows into cell (3, 5) through its left face
    div = ns.divergence(u, v, GRID)
    assert div[3, 5] == pytest.approx(-1 / GRID.dx)
    assert div[3, 4] == pytest.approx(1 / GRID.dx)
    assert np.count_nonzero(div) == 2


def test_the_poisson_solve_inverts_the_laplacian():
    rng = np.random.default_rng(4)
    rhs = rng.normal(size=(GRID.ny, GRID.nx))
    rhs -= rhs.mean()
    phi = ns.solve_poisson(rhs, GRID)
    np.testing.assert_allclose(ns.laplacian(phi, GRID), rhs, atol=1e-10)
    assert abs(phi.mean()) < 1e-12


def test_the_projection_is_divergence_free_idempotent_and_orthogonal():
    rng = np.random.default_rng(5)
    u, v = rng.normal(size=(2, GRID.ny, GRID.nx))
    pu, pv, _ = ns.project(u, v, GRID)
    assert np.max(np.abs(ns.divergence(pu, pv, GRID))) < 1e-10
    qu, qv, _ = ns.project(pu, pv, GRID)
    np.testing.assert_allclose(qu, pu, atol=1e-12)
    np.testing.assert_allclose(qv, pv, atol=1e-12)
    removed = np.sum((u - pu) * pu) + np.sum((v - pv) * pv)
    assert abs(removed) < 1e-9


def test_the_sampled_taylor_green_vortex_has_no_discrete_divergence():
    grid = Grid(20, 20)
    u, v = ns.taylor_green(grid, 0.1, 0.3)
    assert np.max(np.abs(ns.divergence(u, v, grid))) < 1e-13


def test_advection_of_a_uniform_flow_is_zero_and_conserves_momentum():
    u = np.full((GRID.ny, GRID.nx), 0.7)
    v = np.full((GRID.ny, GRID.nx), -0.4)
    adv_u, adv_v = ns.advection(u, v, GRID)
    assert np.max(np.abs(adv_u)) < 1e-14 and np.max(np.abs(adv_v)) < 1e-14
    u, v = smooth_field(GRID)
    adv_u, adv_v = ns.advection(u, v, GRID)
    # A divergence of fluxes on a periodic grid sums to zero.
    assert abs(np.sum(adv_u)) < 1e-11 and abs(np.sum(adv_v)) < 1e-11


def test_advection_does_no_work_on_a_divergence_free_field():
    u, v, _ = ns.project(*smooth_field(GRID), GRID)
    adv_u, adv_v = ns.advection(u, v, GRID)
    assert abs(np.sum(u * adv_u) + np.sum(v * adv_v)) < 1e-11


def test_the_viscous_term_dissipates_at_the_discrete_rate():
    u, v = smooth_field(GRID)
    nu = 0.3
    rate = nu * (np.sum(u * ns.laplacian(u, GRID)) + np.sum(v * ns.laplacian(v, GRID)))
    assert rate * GRID.dx * GRID.dy == pytest.approx(
        -ns.viscous_dissipation(u, v, GRID, nu), rel=1e-12
    )


def test_the_vorticity_of_the_taylor_green_vortex():
    grid = Grid(64, 64)
    u, v = ns.taylor_green(grid, 0.0, 0.0)
    x, y = grid.points("corner")
    # v_x - u_y = 2 sin x sin y, to second order in the cell width.
    np.testing.assert_allclose(
        ns.vorticity(u, v, grid), 2 * np.sin(x) * np.sin(y), atol=2e-3
    )


def test_the_manufactured_force_is_the_residual_of_the_equations():
    """The force, worked out by hand, against the residual of the exact
    solution evaluated by central finite differences of its formulas."""
    nu, t, d = 0.07, 0.4, 1e-4
    rng = np.random.default_rng(6)
    x, y = rng.uniform(0, 2 * np.pi, size=(2, 50))

    def fields(x, y, t):
        a, b = np.cos(t), np.sin(t)
        u = a * np.sin(x) * np.cos(y) + b * np.cos(y)
        v = -a * np.cos(x) * np.sin(y)
        p = 0.25 * a**2 * (np.cos(2 * x) + np.cos(2 * y))
        return u, v, p

    def derivative(index, wrt):
        shift = {"x": (d, 0, 0), "y": (0, d, 0), "t": (0, 0, d)}[wrt]
        up = fields(x + shift[0], y + shift[1], t + shift[2])[index]
        down = fields(x - shift[0], y - shift[1], t - shift[2])[index]
        return (up - down) / (2 * d)

    def second(index):
        centre = fields(x, y, t)[index]
        total = 0.0
        for dx_, dy_ in ((d, 0), (0, d)):
            total = (
                total
                + (
                    fields(x + dx_, y + dy_, t)[index]
                    - 2 * centre
                    + fields(x - dx_, y - dy_, t)[index]
                )
                / d**2
            )
        return total

    u, v, _ = fields(x, y, t)
    rx = (
        derivative(0, "t")
        + u * derivative(0, "x")
        + v * derivative(0, "y")
        + derivative(2, "x")
        - nu * second(0)
    )
    ry = (
        derivative(1, "t")
        + u * derivative(1, "x")
        + v * derivative(1, "y")
        + derivative(2, "y")
        - nu * second(1)
    )

    # A grid whose u and v points are the random points: one cell per point.
    class Points:
        def points(self, where):
            return x, y

    fx, fy = ns.manufactured_forcing(Points(), nu)(t)
    np.testing.assert_allclose(fx, rx, atol=1e-5)
    np.testing.assert_allclose(fy, ry, atol=1e-5)


def test_the_manufactured_velocity_has_no_divergence():
    grid = Grid(16, 16)
    u, v, _ = ns.manufactured(grid, 0.8)
    assert np.max(np.abs(ns.divergence(u, v, grid))) < 1e-13


def test_the_taylor_green_vortex_decays_at_the_exact_rate():
    grid = Grid(32, 32)
    nu = 0.1
    u, v = ns.taylor_green(grid, nu, 0.0)
    u, v, steps = ns.march(u, v, grid, nu, 0.5)
    assert steps > 1
    exact_u, _ = ns.taylor_green(grid, nu, 0.5)
    assert np.max(np.abs(u - exact_u)) < 1e-3


def test_the_pressure_of_the_manufactured_solution_converges():
    nu = 0.05
    errors = []
    for n in (16, 32):
        grid = Grid(n, n)
        u, v, p = ns.manufactured(grid, 0.3)
        computed = ns.pressure(u, v, grid, nu, ns.manufactured_forcing(grid, nu)(0.3))
        errors.append(np.max(np.abs(computed - (p - p.mean()))))
    assert errors[0] / errors[1] == pytest.approx(4.0, rel=0.1)


def test_march_ends_on_the_duration_and_observes_every_step():
    grid = Grid(16, 16)
    u, v = ns.taylor_green(grid, 0.1, 0.0)
    times = []
    _, _, steps = ns.march(
        u, v, grid, 0.1, 0.37, observe=lambda t, u, v: times.append(t)
    )
    assert len(times) == steps and times[-1] == 0.37
    assert times == sorted(times)


def test_the_stable_step_respects_both_limits():
    grid = Grid(10, 10)
    u = np.full((10, 10), 2.0)
    v = np.zeros((10, 10))
    assert ns.stable_step(u, v, grid, 0.0, 0.5) == pytest.approx(0.5 * grid.dx / 2.0)
    viscous = 0.25 / (1.0 * 2 / grid.dx**2)
    assert ns.stable_step(u, v, grid, 1.0, 0.5) == pytest.approx(viscous)
