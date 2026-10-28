"""Three bodies, modified central forces, and the deflection of light
(lessons AST1, AST2, AST3): each result is compared with a closed-form
solution, a limiting case, or an independent computation, with a stated
tolerance."""

import numpy as np
import pytest
from scipy.integrate import solve_ivp

from pbc.astrophysics.central_force import (
    angular_momentum,
    energy,
    first_order_precession,
    near_circular_precession,
    orbit,
    periapsis_start,
    power_law,
    power_law_potential,
    power_law_precession,
    precession_per_orbit,
    yukawa,
    yukawa_potential,
    yukawa_term,
)
from pbc.astrophysics.lensing import (
    closest_approach,
    deflection,
    disk_magnification,
    einstein_radius,
    image_positions,
    lens_map,
    light_curve,
    magnification,
    newtonian_deflection,
    ray_shoot,
    weak_field_deflection,
)
from pbc.astrophysics.three_body import (
    adaptive,
    escaper,
    lagrange_growth_rate,
    lagrange_libration,
    lagrange_triangle,
    pythagorean_start,
    rigid_rotation,
    routh_beta,
    shape_departure,
)
from pbc.mechanics.dynamics import simulate
from pbc.mechanics.integrators import rk4_step
from pbc.mechanics.nbody import angular_momentum as total_angular_momentum
from pbc.mechanics.nbody import gravity, total_energy
from pbc.mechanics.particles import unstack

# --- AST1: three bodies --------------------------------------------------------


def test_the_triangle_starts_equilateral_at_rest_in_its_centre_of_mass():
    masses = [1.0, 2.0, 3.0]
    start, omega = lagrange_triangle(1.0, masses, 2.0)
    x, v = unstack(start.x, 3), unstack(start.v, 3)

    sides = [np.linalg.norm(x[i] - x[(i + 1) % 3]) for i in range(3)]
    assert sides == pytest.approx([2.0, 2.0, 2.0], rel=1e-14)
    assert np.allclose(np.array(masses) @ x, 0, atol=1e-14)
    assert np.allclose(np.array(masses) @ v, 0, atol=1e-14)
    assert omega == pytest.approx(np.sqrt(6.0 / 8.0))


def test_the_triangle_turns_rigidly_under_the_nbody_force():
    # The independent check of the closed form: the F69 acceleration with
    # a fine Runge-Kutta step follows the rigid rotation for a full turn.
    masses = [1.0, 2.0, 3.0]
    start, omega = lagrange_triangle(1.0, masses, 1.0)
    period = 2 * np.pi / omega
    run = simulate(start, gravity(1.0, masses), period / 1000, 1000, step=rk4_step)

    assert np.max(np.abs(run.x - rigid_rotation(start, omega, run.t))) < 1e-9


def test_each_body_of_the_triangle_feels_the_centripetal_acceleration():
    masses = [3.0, 1.0, 0.5]
    start, omega = lagrange_triangle(2.0, masses, 1.5)
    acceleration = gravity(2.0, masses)(0.0, start.x, start.v)

    assert acceleration == pytest.approx(-(omega**2) * start.x, rel=1e-12)


def test_routh_beta_and_the_growth_rate_of_known_cases():
    assert routh_beta([1, 1, 1]) == pytest.approx(1 / 3)
    # Equal masses: lambda^2 = omega^2 (-1 +- 2 sqrt(2) i) / 2, whose root
    # has the real part omega / sqrt(2).
    assert lagrange_growth_rate([1, 1, 1], 1.0) == pytest.approx(1 / np.sqrt(2))
    assert lagrange_growth_rate([1, 1e-3, 1e-9], 1.0) == 0.0
    roots = np.roots([1, 0, 1, 0, 27 / 4 * routh_beta([1, 2, 3])])
    assert lagrange_growth_rate([1, 2, 3], 1.0) == pytest.approx(max(roots.real))


def test_the_libration_frequencies_solve_routh_s_equation():
    masses = [1.0, 9.547e-4, 1e-9]
    slow, fast = lagrange_libration(masses, 1.0)
    beta = routh_beta(masses)

    for frequency in (slow, fast):
        lam2 = -(frequency**2)
        assert lam2**2 + lam2 + 27 / 4 * beta == pytest.approx(0, abs=1e-14)
    assert slow == pytest.approx(np.sqrt(27 * beta / 4), rel=1e-2)
    with pytest.raises(ValueError):
        lagrange_libration([1, 1, 1], 1.0)


def test_the_shape_departure_ignores_rotation_and_scale():
    start, _ = lagrange_triangle(1.0, [1, 2, 3], 1.0)
    turned = rigid_rotation(start, 1.0, [0.7])[0]

    assert shape_departure(3 * turned)[0] < 1e-14
    stretched = unstack(start.x, 3).copy()
    stretched[0] *= 1.1
    assert shape_departure(stretched.reshape(-1))[0] > 1e-2


def test_the_adaptive_integration_keeps_the_conserved_quantities():
    masses, start = pythagorean_start()
    times = np.linspace(0, 10, 201)
    run = adaptive(1.0, masses, start, times, 1e-12)
    energy_ = total_energy(1.0, masses, run)

    assert np.max(np.abs(energy_ / energy_[0] - 1)) < 1e-9
    assert np.max(np.abs(total_angular_momentum(masses, run))) < 1e-10
    assert np.allclose(np.array(masses) @ unstack(run.x, 3), 0, atol=1e-10)


def test_the_pythagorean_start_has_the_classical_triangle_and_no_motion():
    masses, start = pythagorean_start()
    x = unstack(start.x, 3)

    for k, length in enumerate(masses):
        i, j = (b for b in range(3) if b != k)
        assert np.linalg.norm(x[i] - x[j]) == pytest.approx(length)
    assert np.all(start.v == 0)


def test_the_escaper_is_the_body_outside_the_tight_binary():
    masses = [1.0, 1.0, 1.0]
    positions = [[100.0, 0.0], [0.0, 0.5], [0.0, -0.5]]
    velocities = [[1.0, 0.0], [-0.5, 0.0], [0.5, 0.0]]

    k, outer, inner = escaper(1.0, masses, positions, velocities)
    assert k == 0
    assert inner == pytest.approx(0.5 * 0.5 * 1 - 1.0)
    assert outer == pytest.approx(0.5 * 2 / 3 * 1.0 - 2 / 100)


# --- AST2: modified central forces ----------------------------------------------


def test_the_inverse_square_closes_and_keeps_its_invariants():
    x, v = periapsis_start(1.0, 1.0, 0.6)
    path = orbit(power_law(1.0, 1.0, 0.0), x, v, 5.5 * 2 * np.pi)
    e = energy(path, power_law_potential(1.0, 1.0, 0.0))
    h = angular_momentum(path)

    assert len(path.periapsis_t) == 5
    assert np.diff(path.periapsis_t) == pytest.approx(2 * np.pi, rel=1e-10)
    assert abs(precession_per_orbit(path)) < 1e-9
    assert e[0] == pytest.approx(-0.5)
    assert np.max(np.abs(e / e[0] - 1)) < 1e-10
    assert np.max(np.abs(h / h[0] - 1)) < 1e-10


def test_the_yukawa_force_keeps_the_energy_of_its_potential():
    x, v = periapsis_start(1.0, 1.0, 0.5)
    path = orbit(yukawa(1.0, 0.05, 0.7), x, v, 3 * 2 * np.pi)
    e = energy(path, yukawa_potential(1.0, 0.05, 0.7))

    assert np.max(np.abs(e / e[0] - 1)) < 1e-10
    # The force is minus the derivative of the potential.
    r = np.linspace(0.3, 3, 7)
    step = 1e-6
    derivative = (
        yukawa_potential(1.0, 0.05, 0.7)(r + step)
        - yukawa_potential(1.0, 0.05, 0.7)(r - step)
    ) / (2 * step)
    assert yukawa(1.0, 0.05, 0.7)(r) == pytest.approx(-derivative, rel=1e-8)


def test_the_quadrature_gives_the_closed_form_for_the_linearised_power_law():
    # To first order in delta the power law adds GM delta ln(r/a) / r^2,
    # whose Gauss integral is the closed form.
    for e in (0.1, 0.5, 0.9):
        quadrature = first_order_precession(lambda r: np.log(r) / r**2, 1.0, 1.0, e)
        assert quadrature == pytest.approx(
            float(power_law_precession(1.0, e)), rel=1e-12
        )


def test_the_first_order_precession_has_the_near_circular_limit():
    assert float(power_law_precession(0.01, 1e-4)) == pytest.approx(
        np.pi * 0.01, rel=1e-7
    )
    assert float(near_circular_precession(1e-6)) == pytest.approx(
        np.pi * 1e-6, rel=1e-5
    )


def test_a_small_power_law_turns_the_periapsis_as_predicted():
    x, v = periapsis_start(1.0, 1.0, 0.3)
    path = orbit(power_law(1.0, 1.0, 1e-3), x, v, 6.5 * 2 * np.pi)

    assert precession_per_orbit(path) == pytest.approx(
        float(power_law_precession(1e-3, 0.3)), rel=2e-3
    )


def test_the_yukawa_term_vanishes_far_beyond_its_range():
    r = np.array([50.0, 100.0])
    assert np.all(np.abs(yukawa_term(1.0, 1.0)(r) * r**2) < 1e-20)
    with pytest.raises(ValueError):
        yukawa_term(1.0, 0.0)


# --- AST3: deflection and the point lens ----------------------------------------


def test_the_closest_approach_solves_the_impact_relation():
    r0 = closest_approach(20.0)

    assert r0**3 / (r0 - 2) == pytest.approx(400.0, rel=1e-13)
    with pytest.raises(ValueError):
        closest_approach(5.0)


def test_the_quadrature_agrees_with_the_photon_orbit_integrated():
    # u'' + u = 3 m u^2 from u = 0 with u' = 1/b, until u returns to zero.
    def swept(b):
        def rate(phi, y):
            return [y[1], -y[0] + 3 * y[0] ** 2]

        def out(phi, y):
            return y[0]

        out.terminal, out.direction = True, -1
        solution = solve_ivp(
            rate,
            (1e-3, 4 * np.pi),
            [np.sin(1e-3) / b, np.cos(1e-3) / b],
            method="DOP853",
            rtol=1e-13,
            atol=1e-16,
            events=out,
        )
        return solution.t_events[0][0] - np.pi

    for b in (10.0, 100.0, 1000.0):
        assert deflection(b) == pytest.approx(swept(b), rel=1e-8)


def test_the_deflection_has_the_weak_field_limit_and_its_next_term():
    for b in (1e3, 1e4):
        remainder = (deflection(b) - float(weak_field_deflection(b))) * b**2
        assert remainder == pytest.approx(15 * np.pi / 4 + 128 / 3 / b, rel=1e-3)
    assert float(newtonian_deflection(1e6)) == pytest.approx(2e-6, rel=1e-10)


def test_the_images_solve_the_lens_equation_with_their_magnification():
    for u in (0.1, 0.5, 2.0):
        outer, inner = image_positions(u)
        for x in (outer, inner):
            assert lens_map([x, 0.0])[0] == pytest.approx(u, rel=1e-12)
        # 1 / |det| of the radial map y = x - 1/x, per image.
        per_image = [abs(1 / ((1 - x**-2) * (1 + x**-2))) for x in (outer, inner)]
        assert sum(per_image) == pytest.approx(float(magnification(u)), rel=1e-12)


def test_a_small_disk_is_magnified_as_a_point():
    assert disk_magnification(0.5, 1e-4) == pytest.approx(
        float(magnification(0.5)), rel=1e-7
    )


def test_ray_shooting_on_a_coarse_grid_finds_the_two_images():
    shot, hit = ray_shoot(0.5, 0.1, 2.2, 800)
    assert shot == pytest.approx(disk_magnification(0.5, 0.1), rel=1e-2)
    # The rays that land on the source lie around the two predicted images.
    centres = np.linspace(-2.2, 2.2, 801)
    centres = 0.5 * (centres[1:] + centres[:-1])
    xs = np.meshgrid(centres, centres)[0][hit]
    outer, inner = image_positions(0.5)
    assert np.mean(xs[xs > 0]) == pytest.approx(outer, abs=0.02)
    assert np.mean(xs[xs < 0]) == pytest.approx(inner, abs=0.02)


def test_the_einstein_radius_and_the_light_curve():
    assert einstein_radius(1.0, 1.0, 2.0, 1.0) == pytest.approx(np.sqrt(2.0))
    with pytest.raises(ValueError):
        einstein_radius(1.0, 2.0, 1.0, 1.0)
    curve = light_curve([0.0, 3.0], 0.0, 3.0, 0.5)
    assert curve == pytest.approx(magnification([0.5, np.sqrt(1.25)]))
