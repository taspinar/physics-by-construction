"""Three bodies, modified central forces, the deflection of light, the
gravitational wave of a binary, and the transit of a planet (lessons AST1,
AST2, AST3, AST6, AST7): each result is compared with a closed-form
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
