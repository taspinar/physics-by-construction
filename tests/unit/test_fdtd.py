"""Yee's FDTD scheme (lesson EM4, pbc.electromagnetism.fdtd): the step against
exact solutions of the grid, the dispersion relation and the stability limit
against the eigenvalues of the step built as a matrix, and the Fresnel
coefficients against the conservation of energy."""

import numpy as np
import pytest

from pbc.electromagnetism.fdtd import (
    MU_0,
    SPEED_OF_LIGHT,
    Line,
    Plane,
    divergence_h,
    fresnel_reflection,
    fresnel_transmission,
    group_velocity,
    highest_mode_growth,
    stability_limit,
)
from pbc.electromagnetism.fields import EPSILON_0

IMPEDANCE = np.sqrt(MU_0 / EPSILON_0)


def pulse(line: Line, centre: float, width: float) -> None:
    """A Gaussian pulse travelling to the right in vacuum (H half a step
    earlier than E)."""
    shape = lambda x: np.exp(-(((x - centre) / width) ** 2))  # noqa: E731
    line.e[:] = shape(line.x)
    line.e[[0, -1]] = 0.0
    half = line.x[:-1] + 0.5 * line.dx
    line.h[:] = -shape(half + 0.5 * SPEED_OF_LIGHT * line.dt) / IMPEDANCE


def test_the_speed_of_light_is_one_over_the_root_of_mu0_eps0():
    assert pytest.approx(299792458.0, rel=1e-9) == SPEED_OF_LIGHT


def test_at_the_courant_number_one_a_pulse_moves_one_cell_per_step_unchanged():
    line = Line(400, 1e-3, 1.0)
    pulse(line, 0.1, 0.01)
    start = line.e.copy()
    line.run(150)
    np.testing.assert_allclose(line.e[150:], start[:-150], atol=1e-12)


def test_the_energy_of_a_pulse_is_kept():
    line = Line(600, 1e-3, 0.5)
    pulse(line, 0.2, 0.02)
    before = line.energy().sum()
    line.run(300)
    assert line.energy().sum() == pytest.approx(before, rel=1e-6)


def test_a_conducting_end_reflects_the_pulse_with_the_sign_turned():
    line = Line(300, 1e-3, 1.0)
    pulse(line, 0.15, 0.01)
    line.run(300)  # to the end at 0.3 m and back to 0.15 m
    assert line.e.min() == pytest.approx(-1.0, abs=1e-12)
    assert np.argmin(line.e) == 150


def grid_frequency(k, dx, courant):
    """omega(k) of the 1D grid from sin(omega dt / 2) = S sin(k dx / 2)."""
    dt = courant * dx / SPEED_OF_LIGHT
    return 2.0 / dt * np.arcsin(courant * np.sin(0.5 * k * dx))


@pytest.mark.parametrize("courant", [0.3, 0.5, 0.9])
def test_the_group_velocity_is_the_derivative_of_the_grid_frequency(courant):
    dx, k = 1e-3, np.array([100.0, 500.0, 1500.0])
    h = 1e-3
    derivative = (
        grid_frequency(k + h, dx, courant) - grid_frequency(k - h, dx, courant)
    ) / (2 * h)
    np.testing.assert_allclose(group_velocity(k, dx, courant), derivative, rtol=1e-8)


def test_long_waves_travel_at_c_over_n_and_short_ones_slower():
    assert group_velocity(1e-3, 1e-3, 0.5, 2.0) == pytest.approx(
        SPEED_OF_LIGHT / 2.0, rel=1e-12
    )
    assert group_velocity(1000.0, 1e-3, 0.5) < SPEED_OF_LIGHT


def test_at_the_courant_number_one_the_1d_grid_has_no_dispersion():
    k = np.array([100.0, 1000.0, 2000.0])
    np.testing.assert_allclose(group_velocity(k, 1e-3, 1.0), SPEED_OF_LIGHT, rtol=1e-12)


def step_matrix(cells: int, courant: float) -> np.ndarray:
    """The matrix of one step of a Line, built by stepping each unit vector
    of the state (interior E, then H)."""
    size = (cells - 1) + cells
    columns = []
    for k in range(size):
        line = Line(cells, 1e-3, courant)
        state = np.zeros(size)
        state[k] = 1.0
        line.e[1:-1] = state[: cells - 1]
        line.h[:] = state[cells - 1 :]
        line.step()
        columns.append(np.concatenate([line.e[1:-1], line.h]))
    return np.array(columns).T


@pytest.mark.parametrize("cells", [4, 7, 12])
def test_the_stability_limit_is_where_the_step_gets_an_eigenvalue_above_one(cells):
    limit = stability_limit(cells, 1)
    below = np.max(np.abs(np.linalg.eigvals(step_matrix(cells, 0.999 * limit))))
    above = np.max(np.abs(np.linalg.eigvals(step_matrix(cells, 1.02 * limit))))
    assert below == pytest.approx(1.0, abs=1e-9)
    assert above == pytest.approx(highest_mode_growth(1.02 * limit, cells, 1), rel=1e-9)
    assert above > 1.0


def test_the_limits_approach_one_and_one_over_root_two_on_a_fine_grid():
    assert stability_limit(10_000, 1) == pytest.approx(1.0, abs=1e-7)
    assert stability_limit(10_000, 2) == pytest.approx(1 / np.sqrt(2), abs=1e-7)
    assert stability_limit(10, 2) > 1 / np.sqrt(2)
    assert highest_mode_growth(0.5, 10, 2) == 1.0
    with pytest.raises(ValueError):
        stability_limit(10, 3)


def test_a_plane_beyond_its_limit_grows_at_the_rate_of_its_highest_mode():
    cells = 12
    courant = 1.02 * stability_limit(cells, 2)
    plane = Plane(cells, cells, 1e-3, courant)
    plane.ez[1:-1, 1:-1] = np.random.default_rng(3).standard_normal((11, 11))
    peaks = []
    for _ in range(200):
        plane.step()
        peaks.append(np.abs(plane.ez).max())
    rate = np.exp(np.polyfit(np.arange(100, 200), np.log(peaks[100:]), 1)[0])
    assert rate == pytest.approx(highest_mode_growth(courant, cells, 2), rel=1e-6)


def test_the_plane_keeps_the_divergence_of_h_at_its_start():
    plane = Plane(40, 30, 1e-3, 0.7, permittivity=2.0)
    i, j = np.meshgrid(np.arange(41), np.arange(31), indexing="ij")
    plane.ez[:] = np.exp(-((i - 20) ** 2 + (j - 15) ** 2) / 9.0)
    plane.ez[[0, -1], :] = plane.ez[:, [0, -1]] = 0.0
    plane.run(100)
    scale = max(np.abs(plane.hx).max(), np.abs(plane.hy).max()) / plane.dx
    assert np.abs(divergence_h(plane)).max() < 1e-12 * scale


def test_a_conductor_damps_the_field_of_a_plane():
    lossless = Plane(30, 30, 1e-3, 0.7)
    lossy = Plane(30, 30, 1e-3, 0.7, conductivity=0.5)
    for plane in (lossless, lossy):
        plane.ez[15, 15] = 1.0
        plane.run(200)
    assert np.abs(lossy.ez).max() < 0.01 * np.abs(lossless.ez).max()


def test_a_soft_source_adds_to_the_field():
    plane = Plane(10, 10, 1e-3, 0.5)
    source = np.zeros((11, 11))
    source[5, 5] = 2.0
    plane.step(source)
    assert plane.ez[5, 5] == 2.0


@pytest.mark.parametrize(("n1", "n2"), [(1.0, 2.0), (1.5, 1.0), (1.0, 1.0)])
def test_the_fresnel_coefficients_conserve_energy(n1, n2):
    r, t = fresnel_reflection(n1, n2), fresnel_transmission(n1, n2)
    assert 1.0 + r == pytest.approx(t)
    assert r**2 + n2 / n1 * t**2 == pytest.approx(1.0)


def test_grids_refuse_impossible_settings():
    with pytest.raises(ValueError):
        Line(1, 1e-3, 0.5)
    with pytest.raises(ValueError):
        Line(10, 1e-3, 0.5, permittivity=0.5)
    with pytest.raises(ValueError):
        Plane(10, 10, 1e-3, 0.5, conductivity=-1.0)
