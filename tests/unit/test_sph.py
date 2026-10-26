"""Smoothed particle hydrodynamics: the kernel, the particle sums, the
forces and their conservation, the step, and the exact drop
(pbc.fluids.sph)."""

import numpy as np
import pytest

from pbc.fluids import sph
from pbc.fluids.sph import Particles


def test_the_kernel_integrates_to_one_and_vanishes_beyond_two_h():
    h = 0.7
    r = np.linspace(0.0, 2.0 * h, 200001)
    integrand = 2 * np.pi * r * sph.kernel(r, h)
    assert np.trapezoid(integrand, r) == pytest.approx(1.0, abs=1e-8)
    assert sph.kernel(np.array([2.0 * h, 3.0 * h]), h).tolist() == [0.0, 0.0]


def test_the_kernel_derivative_is_the_derivative_of_the_kernel():
    h, d = 0.5, 1e-6
    r = np.array([0.1, 0.3, 0.6, 0.9])
    numerical = (sph.kernel(r + d, h) - sph.kernel(r - d, h)) / (2 * d)
    np.testing.assert_allclose(sph.kernel_derivative(r, h), numerical, rtol=1e-6)


def test_pairs_are_the_pairs_within_reach():
    x = np.array([[0.0, 0.0], [0.5, 0.0], [1.5, 0.0]])
    i, j = sph.pairs(x, 0.5)  # reach 1.0
    assert sorted(zip(i.tolist(), j.tolist(), strict=False)) == [(0, 1), (1, 2)]


def test_the_density_sum_of_a_lattice_is_near_the_rest_density():
    spacing = 0.05
    x = sph.lattice_disc(1.0, spacing)
    rho = sph.density_sum(x, spacing**2, 2.0 * spacing)
    inside = np.sum(x**2, axis=1) < 0.5
    np.testing.assert_allclose(rho[inside], 1.0, rtol=1e-3)
    # At the surface the kernel is cut off and the density is too low.
    assert rho[~inside].min() < 0.8


def test_the_difference_gradient_of_a_constant_is_zero_on_disordered_particles():
    rng = np.random.default_rng(2)
    x = rng.uniform(0, 1, size=(300, 2))
    volume = np.full(300, 1 / 300)
    f = np.full(300, 3.0)
    assert np.max(np.abs(sph.gradient_difference(x, f, volume, 0.1))) < 1e-12
    assert np.max(np.abs(sph.gradient_sum(x, f, volume, 0.1))) > 1.0


def spinning_drop() -> Particles:
    x = sph.lattice_disc(1.0, 0.1)
    rng = np.random.default_rng(8)
    v = rng.normal(scale=0.3, size=x.shape)
    rho = 1.0 + rng.uniform(-0.01, 0.01, size=len(x))
    return Particles(x, v, rho, 0.01)


def test_the_pair_forces_conserve_momentum_and_angular_momentum():
    state = spinning_drop()
    dv, _drho, dq = sph.accelerations(state, 0.13, 1.0, 10.0, viscosity=0.5)
    assert np.max(np.abs(np.sum(dv, axis=0))) < 1e-10
    torque = np.sum(state.x[:, 0] * dv[:, 1] - state.x[:, 1] * dv[:, 0])
    assert abs(torque) < 1e-10
    assert np.all(dq >= -1e-15)


def test_the_equations_conserve_energy_including_the_heat():
    state = spinning_drop()
    dv, drho, dq = sph.accelerations(state, 0.13, 1.0, 10.0, viscosity=0.5)
    # dE/dt = sum m (v . dv + P / rho^2 drho + dq)
    p = sph.pressure(state.rho, 1.0, 10.0)
    rate = state.mass * np.sum(
        np.sum(state.v * dv, axis=1) + p / state.rho**2 * drho + dq
    )
    scale = state.mass * np.sum(np.abs(np.sum(state.v * dv, axis=1)))
    assert abs(rate) < 1e-12 * scale


def test_the_internal_energy_stores_the_work_of_the_pressure():
    rho, d = np.array([0.95, 1.0, 1.07]), 1e-6
    de = (
        sph.internal_energy(rho + d, 1.0, 3.0) - sph.internal_energy(rho - d, 1.0, 3.0)
    ) / (2 * d)
    np.testing.assert_allclose(
        de, sph.pressure(rho, 1.0, 3.0) / rho**2, rtol=1e-6, atol=1e-9
    )
    assert sph.internal_energy(np.array([1.0]), 1.0, 3.0)[0] == 0.0


def test_a_step_keeps_the_momentum_and_its_energy_error_falls_with_the_step():
    errors = []
    for dt in (0.004, 0.002):
        state = spinning_drop()
        e0, p0 = sph.energy(state, 1.0, 10.0), sph.momentum(state)
        for _ in range(round(0.08 / dt)):
            state = sph.step(state, dt, 0.13, 1.0, 10.0)
        assert np.max(np.abs(sph.momentum(state) - p0)) < 1e-12
        errors.append(abs(sph.energy(state, 1.0, 10.0) / e0 - 1))
    assert errors[0] / errors[1] > 3.5


def test_the_exact_drop_keeps_its_area_and_starts_as_a_circle():
    t = np.array([0.0, 0.3, 0.6])
    a, b, rate = sph.elliptical_drop(t, 1.0, 1.0)
    assert a[0] == b[0] == 1.0 and rate[0] == 1.0
    np.testing.assert_allclose(a * b, 1.0, rtol=1e-12)
    assert np.all(np.diff(a) > 0) and np.all(np.diff(rate) < 0)
    # da/dt = A a, checked by a centred difference of the solution.
    d = 1e-4
    (a1, a2), _, _ = sph.elliptical_drop(np.array([0.3 - d, 0.3 + d]), 1.0, 1.0)
    assert (a2 - a1) / (2 * d) == pytest.approx(rate[1] * a[1], rel=1e-6)


def test_the_drop_pressure_at_the_start():
    # A circle of radius R: P0 = rho A^2 R^2 / 2.
    assert sph.drop_pressure(1.0, 1.0, 2.0, 3.0) == pytest.approx(3.0 * 4.0 / 2)


def test_the_moments_of_a_uniform_ellipse():
    x = sph.lattice_disc(1.0, 0.01) * np.array([2.0, 0.5])
    a, b = sph.ellipse_moments(x)
    assert a == pytest.approx(2.0, rel=1e-3) and b == pytest.approx(0.5, rel=1e-3)
