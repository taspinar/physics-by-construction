"""Vortices and the flow around a cylinder on the periodic solver
(pbc.fluids.vortices)."""

import numpy as np
import pytest

from pbc.fluids import vortices as vx
from pbc.fluids.navier_stokes import Grid, divergence, march, project


def test_roshko_fit_at_its_ends_and_outside():
    assert vx.roshko_strouhal(100.0) == pytest.approx(0.212 * (1 - 0.212))
    assert vx.roshko_strouhal(149.0) < 0.212
    with pytest.raises(ValueError):
        vx.roshko_strouhal(30.0)
    with pytest.raises(ValueError):
        vx.roshko_strouhal(300.0)


def test_the_double_shear_layer_is_divergence_free_with_two_opposite_layers():
    grid = Grid(64, 64, 1.0, 1.0)
    u, v = vx.double_shear_layer(grid)
    assert np.max(np.abs(divergence(u, v, grid))) < 1e-12
    _, y = grid.points("u")
    column = u[:, 0]
    assert column[np.argmin(np.abs(y[:, 0] - 0.5))] == pytest.approx(1.0, abs=1e-3)
    assert column[0] == pytest.approx(-1.0, abs=1e-3)


def test_the_circulation_of_a_periodic_box_is_zero():
    rng = np.random.default_rng(7)
    grid = Grid(20, 12, 2.0, 1.0)
    u, v = rng.normal(size=(2, 12, 20))
    assert abs(vx.circulation(u, v, grid)) < 1e-12


def test_the_circulation_stays_zero_while_the_layers_roll_up():
    grid = Grid(32, 32, 1.0, 1.0)
    u, v = vx.double_shear_layer(grid)
    u, v, _ = march(u, v, grid, 1e-3, 0.3)
    assert abs(vx.circulation(u, v, grid)) < 1e-12


def test_the_solid_fraction_is_one_inside_zero_outside_with_a_one_cell_ramp():
    grid = Grid(40, 40, 4.0, 4.0)
    solid_u, solid_v = vx.solid_fraction(grid, vx.Cylinder((2.0, 2.0), 1.0))
    for where, solid in (("u", solid_u), ("v", solid_v)):
        x, y = grid.points(where)
        r = np.hypot(x - 2.0, y - 2.0)
        assert np.all(solid[r < 0.5 - grid.dx / 2] == 1.0)
        assert np.all(solid[r > 0.5 + grid.dx / 2] == 0.0)
    # The covered area is the disc's, to the order of the ramp.
    assert np.sum(solid_u) * grid.dx * grid.dy == pytest.approx(np.pi / 4, rel=0.03)


def test_the_fringe_weight_rises_from_zero_to_one():
    grid = Grid(40, 4, 10.0, 1.0)
    weight_u, _ = vx.fringe_weight(grid, 6.0, 2.0)
    x, _ = grid.points("u")
    assert np.all(weight_u[x <= 6.0] == 0.0) and np.all(weight_u[x >= 8.0] == 1.0)
    row = weight_u[0]
    assert np.all(np.diff(row) >= 0)


def test_the_constraint_stops_the_body_and_restores_the_stream_in_the_fringe():
    grid = Grid(80, 40, 8.0, 4.0)
    constrain = vx.wake_constraint(grid, vx.Cylinder((2.0, 2.0)), 1.0, (5.0, 2.0), 1e6)
    u, v = np.full((40, 80), 0.3), np.full((40, 80), 0.2)
    u, v = constrain(u, v, 1.0)
    x, y = grid.points("u")
    assert np.all(u[np.hypot(x - 2, y - 2) < 0.4] == 0.0)
    np.testing.assert_allclose(u[x >= 7.0], 1.0)
    xv, _ = grid.points("v")
    np.testing.assert_allclose(v[xv >= 7.0], 0.0, atol=1e-12)


def test_shedding_frequency_of_a_sampled_sine():
    t = np.linspace(0.0, 10.0, 2001)
    signal = 0.4 + np.sin(2 * np.pi * 0.37 * t + 0.3)
    frequency, crossings = vx.shedding_frequency(t, signal)
    assert frequency == pytest.approx(0.37, rel=1e-4)
    assert len(crossings) == 3  # at phases 2 pi, 4 pi, 6 pi
    with pytest.raises(ValueError):
        vx.shedding_frequency(t, t)


def test_a_short_wake_run_keeps_the_body_still_and_the_flow_divergence_free():
    wake = vx.cylinder_wake(
        100.0, cells_per_diameter=4, width=6.0, length=12.0, upstream=3.0, duration=2.0
    )
    grid = wake.grid
    assert len(wake.t) == len(wake.probe) and wake.t[-1] == 2.0
    u, _v, _ = project(wake.u, wake.v, grid)
    np.testing.assert_allclose(u, wake.u, atol=1e-12)
    x, y = grid.points("u")
    inside = np.hypot(x - 3.0, y - 3.0) < 0.25
    # Direct forcing holds the no-slip condition to about a cell width.
    assert np.max(np.abs(wake.u[inside])) < 0.3
    upstream = (x > 0.5) & (x < 1.0)
    assert np.mean(wake.u[upstream]) == pytest.approx(1.0, abs=0.1)
