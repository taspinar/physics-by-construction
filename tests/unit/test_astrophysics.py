"""Three bodies, modified central forces, the deflection of light, the
gravitational wave of a binary, the transit of a planet, special relativity,
relativistic orbits, and cosmic expansion (lessons AST1, AST2, AST3, AST6,
AST7, AST10, AST4, AST5): each result is compared with a closed-form
solution, a limiting case, or an independent computation, with a stated
tolerance."""

import numpy as np
import pytest
from scipy.integrate import quad, solve_ivp

from pbc.astrophysics import cosmology, relativistic_orbits
from pbc.astrophysics import special_relativity as sr
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
from pbc.astrophysics.gravitational_waves import (
    cycles_in_band,
    inspiral,
    isco_frequency,
    isco_separation,
    mass_for_chirp_mass,
    polarisations,
    positions,
    quadrupole,
    second_derivative,
    strain_amplitude,
    wave_phase,
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
from pbc.astrophysics.transit import (
    central_depth,
    durations,
    grid_flux,
    overlap_area,
    quadratic_limb,
    total_flux,
    transit_orbit,
    uniform_flux,
)
from pbc.mechanics.chirp import (
    GM_SUN,
    chirp_frequency,
    chirp_mass,
    chirp_phase,
    frequency_from_separation,
    shrink_rate,
    time_to_coalescence,
)
from pbc.mechanics.dynamics import simulate
from pbc.mechanics.integrators import rk4_step
from pbc.mechanics.nbody import angular_momentum as total_angular_momentum
from pbc.mechanics.nbody import gravity, total_energy
from pbc.mechanics.particles import unstack
from pbc.verification.estimates import fitted_order

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


# --- AST6: the gravitational wave of a binary -------------------------------------


def test_the_innermost_orbit_and_its_frequency_agree_with_kepler():
    for total in (2.8, 60.0):
        assert isco_frequency(total) == pytest.approx(
            float(frequency_from_separation(isco_separation(total), total)), rel=1e-12
        )


def test_the_inspiral_ends_at_the_closed_form_time_and_cycles():
    m1, m2, f0 = 10.0, 1.4, 30.0
    mc = chirp_mass(m1, m2)
    f_end = isco_frequency(m1 + m2)
    end, a, phi = inspiral(m1, m2, f0)
    assert a[0] == pytest.approx(isco_separation(m1 + m2), rel=1e-9)
    assert end[0] == pytest.approx(
        time_to_coalescence(f0, mc) - time_to_coalescence(f_end, mc), rel=1e-9
    )
    assert phi[0] / np.pi == pytest.approx(cycles_in_band(f0, f_end, mc), rel=1e-9)
    with pytest.raises(ValueError):
        inspiral(m1, m2, 2 * f_end)


def test_the_quadrupole_is_symmetric_trace_free_and_centred():
    x1, x2 = positions([1.0, 2.0], [0.3, 1.1], 3.0, 1.0)
    assert 3.0 * x1 + 1.0 * x2 == pytest.approx(np.zeros((2, 3)), abs=1e-15)
    q = quadrupole(x1, x2, 3.0, 1.0)
    assert np.einsum("nii->n", q) == pytest.approx(
        [0.0, 0.0], abs=1e-12 * np.abs(q).max()
    )
    assert q == pytest.approx(np.swapaxes(q, 1, 2))


def test_the_second_difference_is_exact_for_a_quintic():
    t = np.linspace(0.0, 1.0, 41)
    y = 2 - t + 3 * t**2 - t**3 + 0.5 * t**4 - 2 * t**5
    exact = 6 - 6 * t + 6 * t**2 - 40 * t**3
    assert second_derivative(y, t[1] - t[0]) == pytest.approx(exact[2:-2], rel=1e-9)


def test_a_rigid_orbit_radiates_the_closed_form_amplitude():
    # An orbit that does not shrink: the quadrupole formula gives exactly the
    # closed-form amplitude at twice the orbital frequency.
    m1, m2, f = 20.0, 10.0, 40.0
    a = float(frequency_from_separation(1.0, m1 + m2) / f) ** (2 / 3)  # f ∝ a^(-3/2)
    rate = 2**16
    t = np.arange(0.0, 0.1, 1 / rate)
    phi = np.pi * f * t
    x1, x2 = positions(np.full_like(t, a), phi, m1, m2)
    q_ddot = second_derivative(quadrupole(x1, x2, m1, m2), 1 / rate)
    distance = 1e25
    h0 = float(strain_amplitude(f, chirp_mass(m1, m2), distance))
    for inclination in (0.0, 0.7, np.pi / 2):
        plus, cross = polarisations(q_ddot, distance, inclination)
        c = np.cos(inclination)
        assert np.max(np.abs(plus)) == pytest.approx(h0 * (1 + c**2) / 2, rel=1e-6)
        assert np.max(np.abs(cross)) == pytest.approx(
            h0 * abs(c), rel=1e-6, abs=1e-12 * h0
        )


def test_the_wave_phase_of_a_rigid_orbit_is_twice_the_orbital_phase():
    # The convention of wave_phase, from the quadrupole formula: seen face
    # on, h+ = -A cos 2 phi and hx = -A sin 2 phi, so the phase is +2 phi,
    # not -2 phi, and it grows with time.
    m1, m2, f = 20.0, 10.0, 40.0
    a = float(frequency_from_separation(1.0, m1 + m2) / f) ** (2 / 3)
    rate = 2**16
    t = np.arange(0.0, 0.1, 1 / rate)
    phi = np.pi * f * t
    x1, x2 = positions(np.full_like(t, a), phi, m1, m2)
    q_ddot = second_derivative(quadrupole(x1, x2, m1, m2), 1 / rate)
    plus, cross = polarisations(q_ddot, 1e25, 0.0)
    h0 = float(strain_amplitude(f, chirp_mass(m1, m2), 1e25))
    assert plus == pytest.approx(-h0 * np.cos(2 * phi[2:-2]), abs=1e-6 * h0)
    assert cross == pytest.approx(-h0 * np.sin(2 * phi[2:-2]), abs=1e-6 * h0)
    assert wave_phase(plus, cross) == pytest.approx(2 * phi[2:-2], abs=1e-6)


def test_twice_the_orbital_phase_is_the_closed_form_phase():
    # chirp_phase grows at 2 pi f, and the integrated orbit turns as it says.
    m1, m2, f0 = 30.0, 30.0, 20.0
    mc = chirp_mass(m1, m2)
    t_c = time_to_coalescence(f0, mc)
    end, _, _ = inspiral(m1, m2, f0)
    t = np.linspace(0.0, end[0], 2001)
    t, _, phi = inspiral(m1, m2, f0, t)
    reference = chirp_phase(t, mc, t_c)
    assert np.gradient(reference, t)[1:-1] == pytest.approx(
        2 * np.pi * chirp_frequency(t, mc, t_c)[1:-1], rel=1e-3
    )
    assert 2 * phi == pytest.approx(reference - reference[0], abs=1e-8)


def test_the_wave_of_a_shrinking_orbit_leads_by_five_quarters_of_the_slowness():
    # The derivatives of a and omega in Q'' turn the wave ahead of 2 phi by
    # +(5/4) eps, eps = |da/dt| / (a omega): a sign error in the phase
    # convention would give -(5/4) eps.
    m1, m2, f0 = 30.0, 30.0, 60.0
    rate = 2**15
    end, _, _ = inspiral(m1, m2, f0)
    t = np.arange(0.0, end[0], 1 / rate)
    t, a, phi = inspiral(m1, m2, f0, t)
    x1, x2 = positions(a, phi, m1, m2)
    q_ddot = second_derivative(quadrupole(x1, x2, m1, m2), 1 / rate)
    plus, cross = polarisations(q_ddot, 1e25, 0.0)
    a, phi = a[2:-2], phi[2:-2]
    eps = -shrink_rate(a, m1, m2) / (a * np.sqrt((m1 + m2) * GM_SUN / a**3))
    lead = wave_phase(plus, cross) - 2 * phi
    assert np.all(lead > 0)
    assert lead / eps == pytest.approx(np.full_like(eps, 5 / 4), rel=5e-3)


def test_the_second_mass_gives_the_chirp_mass():
    m2 = mass_for_chirp_mass(50.0, 20.0)
    assert chirp_mass(50.0, m2) == pytest.approx(20.0, rel=1e-12)
    assert mass_for_chirp_mass(30.0, chirp_mass(30.0, 30.0)) == pytest.approx(30.0)


# --- AST7: the transit of a planet ------------------------------------------------


def test_the_overlap_has_its_limits_and_is_continuous():
    p = 0.1
    assert overlap_area([0.0, 0.5, 0.9], p) == pytest.approx([np.pi * p**2] * 3)
    assert overlap_area([1.1, 2.0], p) == pytest.approx([0.0, 0.0])
    near = overlap_area([0.9 + 1e-9, 1.1 - 1e-9], p)
    assert near == pytest.approx([np.pi * p**2, 0.0], abs=1e-7)
    # A planet as large as the star, centre on the limb: two equal lenses
    # of the classic closed form (2 pi / 3 - sqrt(3) / 2).
    assert overlap_area(1.0, 1.0)[0] == pytest.approx(2 * np.pi / 3 - np.sqrt(3) / 2)


def test_the_grid_counts_the_overlap():
    d = np.linspace(0.85, 1.15, 13)
    assert grid_flux(d, 0.1, cells=600) == pytest.approx(uniform_flux(d, 0.1), abs=2e-6)


def test_a_central_planet_on_a_limb_darkened_star():
    assert central_depth(0.1) == pytest.approx(0.01, rel=1e-12)
    # The whole star covered: the depth is one, whatever the law.
    assert central_depth(1.0, 0.4, 0.26) == pytest.approx(1.0, rel=1e-12)
    darker = quadratic_limb(0.4, 0.26)
    depth = 1 - grid_flux([0.0], 0.2, darker, 600, total_flux(0.4, 0.26))[0]
    assert depth == pytest.approx(central_depth(0.2, 0.4, 0.26), rel=5e-4)
    # A small planet in front of the centre hides I(0) / mean(I) times p².
    assert central_depth(1e-3, 0.4, 0.26) == pytest.approx(
        1e-6 * np.pi / total_flux(0.4, 0.26), rel=1e-5
    )


def test_the_durations_have_their_limits():
    period, a, p = 10.0, 20.0, 0.1
    t14, t23 = durations(period, a, np.pi / 2, p)
    assert t14 == pytest.approx(period / np.pi * np.arcsin(1.1 / a))
    assert t23 == pytest.approx(period / np.pi * np.arcsin(0.9 / a))
    grazing = durations(period, a, np.arccos(0.95 / a), p)
    assert np.isfinite(grazing[0]) and np.isnan(grazing[1])
    assert all(np.isnan(durations(period, a, np.arccos(1.2 / a), p)))


def test_the_integrated_orbit_crosses_at_the_analytic_contacts():
    gm, a, p, b = 1.0, 10.0, 0.1, 0.5
    period = 2 * np.pi * np.sqrt(a**3 / gm)
    inclination = np.arccos(b / a)
    t14, t23 = durations(period, a, inclination, p)
    before = 0.1
    t = np.linspace(0.0, 2 * before * period / (2 * np.pi), 201)
    _, d, contacts = transit_orbit(gm, a, inclination, p, t, before)
    assert np.min(d) == pytest.approx(b, rel=1e-4)
    assert np.diff(contacts["outer"])[0] == pytest.approx(t14, rel=1e-9)
    assert np.diff(contacts["inner"])[0] == pytest.approx(t23, rel=1e-9)
    # Mid-transit in the middle of the run.
    assert np.mean(contacts["outer"]) == pytest.approx(t[-1] / 2, rel=1e-9)


def test_the_transit_functions_reject_inputs_outside_their_domain():
    for p in (0.0, 1.5):
        with pytest.raises(ValueError):
            central_depth(p)
    with pytest.raises(ValueError):
        overlap_area(0.5, 0.0)
    with pytest.raises(ValueError):
        grid_flux([0.0], -0.1)
    with pytest.raises(ValueError):
        grid_flux([0.0], 0.1, cells=0)
    with pytest.raises(ValueError):
        grid_flux([0.0], 0.1, cells=10.5)
    with pytest.raises(ValueError):
        grid_flux([0.0], 0.1, full=0.0)
    with pytest.raises(ValueError):
        durations(0.0, 20.0, np.pi / 2, 0.1)
    with pytest.raises(ValueError):
        durations(10.0, 1.05, np.pi / 2, 0.1)  # the planet grazes the surface
    for inclination in (0.0, np.pi, np.nan):
        with pytest.raises(ValueError):
            durations(10.0, 20.0, inclination, 0.1)
    gm, a, p = 1.0, 10.0, 0.1
    inclination = np.pi / 2
    for t in ([0.0], [0.0, 0.0, 1.0], [1.0, 0.5], [0.0, np.inf], [[0.0, 1.0]]):
        with pytest.raises(ValueError):
            transit_orbit(gm, a, inclination, p, t, 0.1)
    with pytest.raises(ValueError):
        transit_orbit(-1.0, a, inclination, p, [0.0, 1.0], 0.1)
    with pytest.raises(ValueError):
        transit_orbit(gm, a, inclination, p, [0.0, 1.0], 0.1, radius=0.0)


def test_the_durations_reject_a_planet_larger_than_the_star():
    assert np.isfinite(durations(10.0, 20.0, np.pi / 2, 1.0)[0])  # p = 1 is kept
    with pytest.raises(ValueError, match="no larger than the star"):
        durations(10.0, 20.0, np.pi / 2, 1.5)


def test_the_integrated_orbit_rejects_inputs_that_describe_no_transit():
    gm, p, before = 1.0, 0.1, 0.1
    t = [0.0, 1.0]
    with pytest.raises(ValueError, match="no larger than the star"):
        transit_orbit(gm, 10.0, np.pi / 2, 1.5, t, before)
    # The orbit must clear the star and the planet, in the star's radius.
    for a, radius in ((1.05, 1.0), (0.5, 1.0), (3.0, 2.8)):
        with pytest.raises(ValueError, match="outside the star"):
            transit_orbit(gm, a, np.pi / 2, p, t, before, radius)
    # The planet must cross the disk: |b| < 1 + p, on either side.
    a = 10.0
    for b in (1.1, 1.5, -1.2, a):
        with pytest.raises(ValueError, match="impact parameter"):
            transit_orbit(gm, a, np.arccos(b / a), p, t, before)
    with pytest.raises(ValueError, match="impact parameter"):
        transit_orbit(gm, a, np.nan, p, t, before)
    # An on-disk impact parameter with the planet behind the star at
    # mid-transit (sin i <= 0) is no transit either.
    for inclination in (-np.pi / 2, 3 * np.pi / 2, -np.pi / 2 + 0.05, -1.6):
        with pytest.raises(ValueError, match="inclination"):
            transit_orbit(gm, a, inclination, p, t, before)
    # A grazing transit, 1 - p < b < 1 + p, is kept, with no inner contacts.
    period = 2 * np.pi * np.sqrt(a**3 / gm)
    times = np.linspace(0.0, 2 * before * period / (2 * np.pi), 201)
    _, _, contacts = transit_orbit(gm, a, np.arccos(1.05 / a), p, times, before)
    assert contacts["outer"].size == 2 and contacts["inner"].size == 0


# --- AST10: special relativity -------------------------------------------------


def test_a_boost_along_x_is_the_textbook_transformation():
    beta, gamma = 0.6, 1.25
    t, x, y, z = 2.0, 1.0, 3.0, -1.0
    moved = sr.boost([beta, 0.0, 0.0]) @ [t, x, y, z]
    assert moved == pytest.approx(
        [gamma * (t - beta * x), gamma * (x - beta * t), y, z]
    )
    assert sr.boost([0.0, 0.0, 0.0]) == pytest.approx(np.eye(4))


def test_a_boost_in_any_direction_keeps_the_metric_and_the_interval():
    rng = np.random.default_rng(3)
    events = rng.normal(size=(20, 4))
    for _ in range(10):
        v = rng.normal(size=3)
        v *= rng.uniform(0.0, 0.999) / np.linalg.norm(v)
        matrix = sr.boost(v)
        assert matrix.T @ sr.METRIC @ matrix == pytest.approx(sr.METRIC, abs=1e-9)
        assert sr.interval(events @ matrix.T) == pytest.approx(
            sr.interval(events), abs=1e-9
        )
        # The boost and the boost with the opposite velocity undo each other.
        assert sr.boost(-v) @ matrix == pytest.approx(np.eye(4), abs=1e-9)
        # The frame's own origin is at rest in it.
        assert (matrix @ np.concatenate([[1.0], v]))[1:] == pytest.approx(
            np.zeros(3), abs=1e-12
        )
    with pytest.raises(ValueError):
        sr.boost([1.0, 0.0, 0.0])


def test_collinear_boosts_add_rapidities_and_velocities():
    u, v = 0.5, 0.7
    product = sr.boost([u, 0, 0]) @ sr.boost([v, 0, 0])
    combined = float(sr.add_velocities(u, v))
    assert combined == pytest.approx(np.tanh(sr.rapidity(u) + sr.rapidity(v)))
    assert product == pytest.approx(sr.boost([combined, 0, 0]))
    assert float(sr.add_velocities(0.9, 1.0)) == pytest.approx(1.0)  # light stays light


def test_proper_time_and_the_moving_rod_against_their_formulas():
    beta = 0.8
    assert sr.proper_time([[0, 0, 0, 0], [5, 4, 0, 0]]) == pytest.approx(3.0)
    # A curved worldline in many straight pieces: x = sin t, proper time
    # integral of sqrt(1 - cos² t) dt = integral of |sin t| over (0, pi) = 2.
    t = np.linspace(0.0, np.pi, 20001)
    worldline = np.stack([t, 0.5 * np.sin(t), 0 * t, 0 * t], axis=1)
    exact, _ = quad(lambda s: np.sqrt(1 - 0.25 * np.cos(s) ** 2), 0, np.pi)
    assert sr.proper_time(worldline) == pytest.approx(exact, rel=1e-8)
    assert sr.moving_rod_length(2.0, beta) == pytest.approx(2.0 * 0.6)
    assert sr.moving_rod_length(2.0, -beta) == pytest.approx(2.0 * 0.6)
    with pytest.raises(ValueError):
        sr.proper_time([[0, 0, 0, 0], [1, 2, 0, 0]])  # spacelike


def test_four_momentum_mass_and_velocity():
    p = sr.four_momentum(2.0, [0.6, 0.0, 0.0])
    assert p == pytest.approx([2.5, 1.5, 0.0, 0.0])
    assert float(sr.invariant_mass(p)) == pytest.approx(2.0)
    assert sr.velocity(p) == pytest.approx([0.6, 0.0, 0.0])


def test_an_elastic_collision_conserves_four_momentum_and_matches_newton_slowly():
    before = np.array(
        [sr.four_momentum(1.0, [0.3, 0.1, 0]), sr.four_momentum(2.5, [-0.2, 0, 0])]
    )
    after = sr.elastic_collision(before, deflection=1.0)
    assert after.sum(axis=0) == pytest.approx(before.sum(axis=0), abs=1e-12)
    assert sr.invariant_mass(after) == pytest.approx([1.0, 2.5], abs=1e-12)
    # At low speed a head-on rebound gives Newton's elastic result.
    m1, m2, u1, u2 = 1.0, 3.0, 1e-4, -2e-4
    slow = np.array(
        [sr.four_momentum(m1, [u1, 0, 0]), sr.four_momentum(m2, [u2, 0, 0])]
    )
    v1 = sr.velocity(sr.elastic_collision(slow))[0, 0]
    newton = ((m1 - m2) * u1 + 2 * m2 * u2) / (m1 + m2)
    assert v1 == pytest.approx(newton, rel=1e-7)


def test_the_kinetic_energy_keeps_its_digits_and_tends_to_newtons():
    beta = np.array([1e-8, 1e-3, 0.5])
    gamma = 1 / np.sqrt(1 - beta**2)
    assert sr.kinetic_energy(2.0, beta)[2] == pytest.approx(2.0 * (gamma[2] - 1))
    ratio = sr.kinetic_energy(2.0, beta) / sr.newtonian_kinetic_energy(2.0, beta)
    assert ratio[:2] == pytest.approx(1 + 0.75 * beta[:2] ** 2, rel=1e-12)
    assert sr.galilean([0.5, 0, 0]) @ [2.0, 1.0, 0, 0] == pytest.approx(
        [2.0, 0.0, 0, 0]
    )


# --- AST4: relativistic orbits -------------------------------------------------


def test_the_exact_turn_tends_to_the_first_order_and_its_known_second_term():
    for e in (0.1, 0.5, 0.9):
        m = 1e-4
        exact = relativistic_orbits.exact_precession(m, 1.0, e)
        first = float(relativistic_orbits.first_order_precession(m, 1.0))
        gap = (exact - first) / m**2
        assert gap == pytest.approx(
            relativistic_orbits.second_order_coefficient(e), rel=2e-3
        )


def test_the_exact_turn_against_a_direct_quadrature_of_the_cubic():
    m, p, e = 0.02, 1.0, 0.4
    u1, u2 = (1 - e) / p, (1 + e) / p
    u3 = 1 / (2 * m) - u1 - u2
    h2 = relativistic_orbits.angular_momentum(m, p, e) ** 2
    # u = u1 + (u2 - u1) sin² w removes both end singularities of
    # du / sqrt(2 m (u - u1)(u2 - u)(u3 - u)), leaving 2 dw / sqrt(2 m (u3 - u)),
    # smooth and periodic, so the trapezoidal rule converges fast.
    w = np.linspace(0, np.pi / 2, 2001)
    u = u1 + (u2 - u1) * np.sin(w) ** 2
    angle = 2 * np.trapezoid(2 / np.sqrt(2 * m * (u3 - u)), w)
    assert angle - 2 * np.pi == pytest.approx(
        relativistic_orbits.exact_precession(m, p, e), rel=1e-10
    )
    # The cubic with this h is the first integral of the orbit equation,
    # 2 m u³ - u² + 2 m u / h² + const, with its turning points at u1 and u2.
    cubic = 2 * m * (u - u1) * (u2 - u) * (u3 - u)
    polynomial = 2 * m * u**3 - u**2 + 2 * m * u / h2
    assert np.ptp(cubic - polynomial) < 1e-12


def test_the_integrated_geodesic_turns_by_the_exact_amount_and_closes_without_mass():
    path = relativistic_orbits.geodesic(0.01, 1.0, 0.3, 5.5)
    assert len(path.periapsis_phi) == 5
    assert relativistic_orbits.turn_per_orbit(path.periapsis_phi) == pytest.approx(
        relativistic_orbits.exact_precession(0.01, 1.0, 0.3), abs=1e-10
    )
    assert path.u.max() == pytest.approx(1.3, rel=1e-10)
    tiny = relativistic_orbits.geodesic(1e-9, 1.0, 0.3, 3.5)
    assert abs(relativistic_orbits.turn_per_orbit(tiny.periapsis_phi)) < 1e-7


def test_the_post_newtonian_orbit_turns_at_first_order():
    for m in (1e-3, 1e-4):
        turn = relativistic_orbits.turn_per_orbit(
            relativistic_orbits.post_newtonian_orbit(m, 1.0, 0.3, 5.5)
        )
        first = float(relativistic_orbits.first_order_precession(m, 1.0))
        assert turn == pytest.approx(first, rel=200 * m)


def test_circular_orbits_and_the_innermost_stable_one():
    unstable, stable = relativistic_orbits.circular_orbit_radii(4.0, 1.0)
    assert (unstable, stable) == pytest.approx((4.0, 12.0))
    r = np.array([stable * (1 - 1e-4), stable, stable * (1 + 1e-4)])
    v = relativistic_orbits.effective_potential(r, 4.0, 1.0)
    assert v[1] < v[0] and v[1] < v[2]
    assert relativistic_orbits.circular_orbit_radii(
        np.sqrt(12) * (1 + 1e-12), 1.0
    ) == pytest.approx((6.0, 6.0), abs=1e-4)
    assert relativistic_orbits.circular_orbit_radii(3.0, 1.0) is None
    with pytest.raises(ValueError):
        relativistic_orbits.exact_precession(0.2, 1.0, 0.5)  # falls in


# --- AST5: cosmic expansion ----------------------------------------------------


def test_the_hubble_rate_is_one_today_and_the_curvature_closes_the_budget():
    for model in (
        cosmology.Model(1.0),
        cosmology.Model(0.3, 1e-4, 0.7),
        cosmology.Model(0.2),
    ):
        assert float(cosmology.hubble_rate(model, 1.0)) == pytest.approx(1.0)
        assert (
            model.matter + model.radiation + model.lam + model.curvature
            == pytest.approx(1)
        )
    radiation = cosmology.Model(0.0, radiation=1.0)
    assert cosmology.age(radiation) == pytest.approx(0.5, rel=1e-10)  # a = sqrt(2 t)


def test_the_ages_against_their_closed_forms():
    assert cosmology.age(cosmology.Model(1.0)) == pytest.approx(2 / 3, rel=1e-12)
    assert cosmology.age(cosmology.Model(0.0)) == pytest.approx(1.0, rel=1e-12)
    for m in (0.1, 0.3, 0.8):
        assert cosmology.age(cosmology.Model(m, lam=1 - m)) == pytest.approx(
            cosmology.flat_lambda_age(m), rel=1e-10
        )
    # An open universe of matter only:
    # H0 t0 = 1/(1 - m) - m/(2 (1 - m)^1.5) acosh(2/m - 1).
    m = 0.3
    open_age = 1 / (1 - m) - m / (2 * (1 - m) ** 1.5) * np.arccosh(2 / m - 1)
    assert cosmology.age(cosmology.Model(m)) == pytest.approx(open_age, rel=1e-10)


def test_the_integrated_scale_factor_against_the_analytic_histories():
    eds = cosmology.expansion(cosmology.Model(1.0), 1.0, 1.0)
    assert eds.a == pytest.approx((1.5 * (eds.tau + 2 / 3)) ** (2 / 3), rel=1e-9)
    assert eds.a[0] == pytest.approx(1e-3)  # stopped where a reaches its floor
    sitter = cosmology.expansion(cosmology.Model(0.0, lam=1.0), 1.0, 1.0)
    assert sitter.a == pytest.approx(np.exp(sitter.tau), rel=1e-10)
    toy = cosmology.expansion(cosmology.Model(0.3, lam=0.7), 0.5, 0.5)
    assert toy.a == pytest.approx(
        cosmology.flat_lambda_scale_factor(
            0.3, toy.tau + cosmology.flat_lambda_age(0.3)
        ),
        rel=1e-9,
    )


def test_the_distances_against_the_analytic_cases_and_each_other():
    z = 1.7
    eds, milne, sitter = (
        cosmology.Model(1.0),
        cosmology.Model(0.0),
        cosmology.Model(0.0, lam=1.0),
    )
    assert cosmology.comoving_distance(eds, z) == pytest.approx(
        float(cosmology.einstein_de_sitter_comoving(z)), rel=1e-12
    )
    assert cosmology.luminosity_distance(milne, z) == pytest.approx(
        float(cosmology.milne_luminosity(z)), rel=1e-12
    )
    assert cosmology.comoving_distance(sitter, z) == pytest.approx(z, rel=1e-12)
    for model in (eds, milne, cosmology.Model(0.3, lam=0.7), cosmology.Model(2.0)):
        d_l = cosmology.luminosity_distance(model, z)
        d_a = cosmology.angular_diameter_distance(model, z)
        assert d_l / d_a == pytest.approx((1 + z) ** 2)  # Etherington's relation
        assert cosmology.ray_distance(model, z) == pytest.approx(
            cosmology.comoving_distance(model, z), rel=1e-10
        )
    # A closed model bends the transverse distance below the comoving one.
    closed = cosmology.Model(2.0)
    d_c = cosmology.comoving_distance(closed, z)
    assert cosmology.transverse_distance(closed, d_c) == pytest.approx(
        np.sin(d_c) / 1.0
    )


def test_the_low_redshift_form_is_second_order():
    model = cosmology.Model(0.3, lam=0.7)
    z = np.array([0.02, 0.01, 0.005])
    exact = np.array([cosmology.luminosity_distance(model, x) for x in z])
    gap = np.abs(exact - cosmology.low_redshift_luminosity(model, z))
    assert fitted_order(z, gap) == pytest.approx(3.0, abs=0.05)
    assert model.deceleration == pytest.approx(-0.55)
