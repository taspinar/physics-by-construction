"""The two-dimensional shallow-water model of the capstone FL10
(``pbc.fluids.tsunami``): it is FL5's scheme along each axis, keeps water at
rest at rest on a plane and on a rotating sphere, conserves the volume,
keeps the depth positive, treats x and y alike, and moves long waves at
sqrt(g h)."""

import numpy as np
import pytest

from pbc.fluids import finite_volume, shallow_water
from pbc.fluids import tsunami as ts

G = shallow_water.GRAVITY


def bump(n: int, length: float = 1000.0) -> tuple[np.ndarray, float]:
    x = (np.arange(n) + 0.5) * length / n
    return 0.2 * np.exp(-(((x - 0.5 * length) / (0.1 * length)) ** 2)), length / n


def one_row_state(n: int) -> tuple[np.ndarray, np.ndarray, float]:
    bed, dx = bump(n)
    x = (np.arange(n) + 0.5) * dx
    h = np.where(x < 400.0, 1.0, 0.6) - bed
    return bed, np.stack([h, np.zeros(n)], axis=-1), dx


def test_one_row_at_first_order_is_the_scheme_of_fl5():
    """Along one row, with no flow across it, the face fluxes and the bed
    source of the two-dimensional model are those of FL5's hydrostatic
    reconstruction, so one step of each gives the same cells."""
    bed, q1, dx = one_row_state(80)
    q1[:, 1] = 0.3 * q1[:, 0] * np.sin(np.arange(80) / 7.0)
    fluxes, source = shallow_water.well_balanced(bed, dx, finite_volume.transmissive)
    expected = -(np.diff(fluxes(q1), axis=0)) / dx + source(q1)
    grid = ts.plane_grid(bed[None, :], dx, dy=50.0)
    q2 = np.zeros((1, 80, 3))
    q2[0, :, :2] = q1
    rate, _, _ = ts.fluxes_and_source(grid, q2, open_ends=True, second_order=False)
    assert np.max(np.abs(rate[0, :, :2] - expected)) < 1e-12
    assert np.max(np.abs(rate[0, :, 2])) == 0.0


def test_a_run_along_one_row_is_fl5s_run():
    """A dam break over a bump, run by FL5's ``evolve`` and by the model on
    one row with a very long cell across it (so the CFL step is FL5's to a
    relative 1e-12): the same depths after the same steps."""
    bed, q1, dx = one_row_state(60)
    fluxes, source = shallow_water.well_balanced(bed, dx, finite_volume.transmissive)
    fl5 = finite_volume.evolve(
        q1, dx, 20.0, fluxes, shallow_water.max_speed, 0.45, source=source
    )
    grid = ts.plane_grid(bed[None, :], dx, dy=1e15)
    q2 = np.zeros((1, 60, 3))
    q2[0, :, :2] = q1
    run = ts.simulate(grid, q2, 20.0, 0.45, second_order=False)
    assert run.steps == len(fl5.t) - 1
    assert np.max(np.abs(run.q[0, :, 0] - fl5.q[:, 0])) < 1e-9
    assert np.max(np.abs(run.q[0, :, 1] - fl5.q[:, 1])) < 1e-9


@pytest.mark.parametrize("second_order", [False, True])
def test_x_and_y_are_treated_alike(second_order):
    """The same state transposed gives the transposed rate, with the two
    momenta swapped."""
    rng = np.random.default_rng(3)
    bed = -100.0 + 20.0 * rng.random((9, 9))
    q = np.zeros((9, 9, 3))
    q[..., 0] = -bed + 0.5 * rng.random((9, 9))
    q[..., 1:] = rng.normal(size=(9, 9, 2))
    grid = ts.plane_grid(bed, 7.0, 7.0)
    rate, _, _ = ts.fluxes_and_source(grid, q, second_order=second_order)
    flipped = np.transpose(q, (1, 0, 2))[..., [0, 2, 1]]
    rate_t, _, _ = ts.fluxes_and_source(
        ts.plane_grid(bed.T, 7.0, 7.0), flipped, second_order=second_order
    )
    assert np.allclose(
        np.transpose(rate_t, (1, 0, 2))[..., [0, 2, 1]], rate, atol=1e-12
    )


def rough_sphere(rotating: bool) -> ts.Grid:
    """A sphere grid of 20 x 30 cells from 40N to 60N with a rough bed, an
    island, and a coast."""
    rng = np.random.default_rng(7)
    lat = 40.25 + 0.5 * np.arange(40)[::2]
    lon = 150.25 + 0.5 * np.arange(30)
    bed = -4000.0 + 3000.0 * rng.random((20, 30))
    bed[8:11, 10:13] = 50.0  # an island
    bed[:, :3] = 200.0  # a coast
    return ts.sphere_grid(bed, lat, lon, rotating=rotating)


@pytest.mark.parametrize("rotating", [False, True])
def test_water_at_rest_stays_at_rest_on_a_sphere(rotating):
    """Over a rough bed with dry land, on cells whose north and south faces
    differ in length, the surface stays flat and the water still: the source
    cancels the pressure on the unequal faces to round-off."""
    grid = rough_sphere(rotating)
    q = np.zeros((*grid.shape, 3))
    q[..., 0] = np.maximum(0.0, -grid.bed)
    run = ts.simulate(grid, q, 3600.0, 0.45)
    wet = run.q[..., 0] > ts.WET
    eta = run.q[..., 0] + grid.bed
    assert np.max(np.abs(eta[wet])) < 1e-9
    assert np.max(np.abs(run.q[..., 1:])) < 1e-9
    assert np.all(run.q[~wet, 0] == 0.0)


def test_without_the_metric_source_the_sphere_does_not_balance():
    """The pressure on the north and south faces alone pushes water at rest:
    dropping the term g / 4 (h_n^2 + h_s^2) (L_n - L_s) from the source would
    leave a rate of the size of the term itself. The flat bed shows it."""
    lat = 40.25 + np.arange(10)
    grid = ts.sphere_grid(np.full((10, 6), -4000.0), lat, 150.25 + np.arange(6))
    q = np.zeros((10, 6, 3))
    q[..., 0] = 4000.0
    rate, _, _ = ts.fluxes_and_source(grid, q)
    assert np.max(np.abs(rate)) < 1e-12
    metric = 0.5 * G * 4000.0**2 * np.diff(grid.north) / grid.area
    assert np.min(np.abs(metric)) > 1e-3


@pytest.mark.parametrize("second_order", [False, True])
def test_a_closed_basin_keeps_its_volume(second_order):
    """Walls all round: a hump of water sloshes over a rough bed with an
    island; the volume stays the same to round-off, and nothing leaves."""
    grid = rough_sphere(rotating=True)
    q = np.zeros((*grid.shape, 3))
    q[..., 0] = np.maximum(0.0, -grid.bed)
    q[5:9, 15:19, 0] += 2.0
    run = ts.simulate(grid, q, 1800.0, 0.45, open_ends=False, second_order=second_order)
    assert np.max(np.abs(run.outflow)) == 0.0
    assert np.max(np.abs(run.volume - run.volume[0])) / run.volume[0] < 1e-13
    assert run.min_depth >= 0.0


def test_the_open_budget_closes_and_the_depth_stays_positive():
    """Open boundaries and a wave that runs onto a dry slope: the volume
    changes only by what leaves, and no depth becomes negative."""
    x = np.arange(60)
    bed = np.tile(-50.0 + 1.2 * x, (12, 1))  # dry beyond x = 41
    grid = ts.plane_grid(bed, 100.0, 100.0)
    q = np.zeros((12, 60, 3))
    q[..., 0] = np.maximum(0.0, -bed)
    q[:, 5:12, 0] += 3.0
    run = ts.simulate(grid, q, 400.0, 0.45)
    assert run.min_depth >= 0.0
    assert np.max(np.abs(run.budget_residual)) / run.volume[0] < 1e-12
    assert np.any(run.q[:, 42:, 0] > ts.WET)  # the wave ran onto the dry bed


@pytest.mark.parametrize("second_order", [False, True])
def test_a_radiating_boundary_keeps_water_at_rest_at_rest(second_order):
    """At rest at the sea level over a rough bed with an island, the
    radiating ghost cells are the copied ones to round-off, so nothing
    moves."""
    grid = rough_sphere(rotating=True)
    q = np.zeros((*grid.shape, 3))
    q[..., 0] = np.maximum(0.0, -grid.bed)
    rate, mx, my = ts.fluxes_and_source(
        grid, q, second_order=second_order, sea_level=0.0
    )
    copied, _, _ = ts.fluxes_and_source(grid, q, second_order=second_order)
    assert np.max(np.abs(rate[..., 0])) < 1e-12
    assert np.max(np.abs(mx)) < 1e-9 and np.max(np.abs(my)) < 1e-9  # m^2/s
    assert np.allclose(rate, copied, rtol=0.0, atol=1e-9)


def test_a_radiating_boundary_holds_the_sea_level_outside():
    """A channel whose water stands 1 m above the sea level outside: copied
    ghost cells give no pressure from outside, so nothing restores the level,
    and it stays; radiating ghost cells bring it down to the sea level, the
    excess leaving through the two ends, after the waves from the ends have
    crossed the channel and left (about twice its length over sqrt(g h))."""
    n, depth = 100, 1000.0
    grid = ts.plane_grid(np.full((2, n), -depth), 1000.0, 1e9)
    q = np.zeros((2, n, 3))
    q[..., 0] = depth + 1.0
    t = 2.0 * n * 1000.0 / np.sqrt(G * depth)
    copied = ts.simulate(grid, q, t, 0.45)
    radiating = ts.simulate(grid, q, t, 0.45, sea_level=0.0)
    assert np.allclose(copied.q[..., 0], depth + 1.0, atol=1e-9)
    assert np.max(np.abs(radiating.q[..., 0] - depth)) < 1e-3
    excess = 1.0 * grid.area[0] * 2 * n  # m^3: 1 m over the two rows
    assert radiating.outflow[-1] == pytest.approx(excess, rel=1e-3)


def test_a_wave_leaves_through_a_radiating_boundary():
    """A small right-going wave on a flat bed (u = eta sqrt(g / h)) leaves
    through the east edge: what it leaves behind is below a hundredth of
    its height."""
    n, dx, depth, a = 300, 2000.0, 4000.0, 0.1
    x = (np.arange(n) + 0.5) * dx
    eta = a * np.exp(-(((x - 450e3) / 30e3) ** 2))
    grid = ts.plane_grid(np.full((2, n), -depth), dx, 1e9)
    q = np.zeros((2, n, 3))
    q[..., 0] = depth + eta
    q[..., 1] = q[..., 0] * eta * np.sqrt(G / depth)
    t = (n * dx - 450e3 + 150e3) / np.sqrt(G * depth)  # past the east edge
    run = ts.simulate(grid, q, t, 0.45, sea_level=0.0)
    assert np.max(np.abs(run.q[0, :, 0] - depth)) < 0.01 * a


def test_a_long_wave_travels_at_sqrt_gh():
    """A small hump on a flat bed 4000 m deep splits into two waves that each
    move at sqrt(g h): the crest of the right-going wave is where d'Alembert
    puts it, to within a cell."""
    n, dx, depth = 400, 2000.0, 4000.0
    x = (np.arange(n) + 0.5) * dx
    grid = ts.plane_grid(np.full((2, n), -depth), dx, 1e9)
    q = np.zeros((2, n, 3))
    q[..., 0] = depth + 0.1 * np.exp(-(((x - 200e3) / 20e3) ** 2))
    t = 600.0
    run = ts.simulate(grid, q, t, 0.45)
    crest = x[100 + np.argmax(run.q[0, 100:, 0])]
    assert abs(crest - (200e3 + np.sqrt(G * depth) * t)) < dx


def test_the_uplift_lifts_bed_and_surface_together():
    """An instantaneous source lifts the bed and the surface by the uplift
    and keeps the depth; a source in time does the same at its onset."""
    bed = np.full((6, 6), -1000.0)
    uplift = np.zeros((6, 6))
    uplift[2:4, 2:4] = 1.5
    grid, q = ts.initial_state(ts.plane_grid(bed, 1e3, 1e3), uplift)
    assert np.allclose(q[..., 0], 1000.0)
    assert np.allclose(ts.surface(grid, q), uplift)
    flat = ts.plane_grid(bed, 1e3, 1e3)
    q0 = np.zeros((6, 6, 3))
    q0[..., 0] = 1000.0
    onset = np.where(uplift > 0, 10.0, 0.0)
    run = ts.simulate(
        flat,
        q0,
        10.0,
        0.45,
        uplift=uplift,
        onset=onset,
        gauges=(ts.Gauge("c", 2.5, 2.5),),
    )
    assert run.records["c"][0] == 0.0
    assert run.volume[-1] == pytest.approx(run.volume[0], rel=1e-14)


def test_a_gauge_interpolates_bilinearly():
    gauge = ts.Gauge("g", 1.25, 2.5)
    cells, w = gauge.weights(ts.plane_grid(np.zeros((4, 5)), 1.0, 1.0))
    assert cells == (1, 2, 2, 3)
    assert np.allclose(w, [0.375, 0.375, 0.125, 0.125])


def test_coarsen_averages_blocks():
    field = np.arange(24.0).reshape(4, 6)
    assert np.allclose(ts.coarsen(field, 2), [[3.5, 5.5, 7.5], [15.5, 17.5, 19.5]])
    assert ts.coarsen(np.ones((5, 7)), 2).shape == (2, 3)
