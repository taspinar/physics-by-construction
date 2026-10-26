"""Refraction, polarisation, diffraction, and inverse optics (lessons W3 to
W6): each result is compared with a closed form or a limiting case, with a
stated tolerance."""

import numpy as np
import pytest

from pbc.waves.diffraction import (
    AIRY_FIRST_ZERO,
    aperture,
    circular_field,
    double_slit_zero,
    far_field,
    field_at,
    grating_maximum,
    huygens_field,
    single_slit_zero,
    slits,
    two_points,
)
from pbc.waves.inverse import detector, double_slit_model, fit, scaled_jacobian, start
from pbc.waves.polarisation import (
    chain_transmission,
    circular,
    degree_of_polarisation,
    intensity,
    linear,
    malus,
    polariser,
    retarder,
    stokes_closed,
    stokes_measured,
    unpolarised,
)
from pbc.waves.refraction import (
    bisect_root,
    brewster_angle,
    critical_angle,
    fresnel_closed,
    fresnel_solved,
    golden_minimum,
    interface_exact,
    least_time_path,
    node_speeds,
    reflectance,
    snell_angle,
    solve_varying,
    transmittance,
)
from pbc.waves.wave import grid, solve, standing_mode

# Refraction


def test_snell_angle_and_its_limits():
    assert snell_angle(0.0, 1.0, 1.5) == 0.0
    assert snell_angle(np.pi / 6, 1.0, 1.0) == pytest.approx(np.pi / 6)
    assert np.sin(snell_angle(0.7, 1.0, 1.5)) * 1.5 == pytest.approx(np.sin(0.7))
    assert critical_angle(1.5, 1.0) == pytest.approx(np.arcsin(1 / 1.5))
    with pytest.raises(ValueError):
        snell_angle(1.0, 1.5, 1.0)
    with pytest.raises(ValueError):
        critical_angle(1.0, 1.5)


def test_golden_minimum_finds_the_vertex_of_a_parabola():
    assert golden_minimum(lambda x: (x - 0.3) ** 2 + 1, -2.0, 5.0) == pytest.approx(
        0.3, abs=1e-7
    )


def test_the_least_time_path_obeys_snells_law():
    for n1, n2, distance in [(1.0, 1.333, 0.7), (1.5, 1.0, 0.4), (1.0, 1.0, 2.0)]:
        x, incidence, refracted = least_time_path(
            height=1.0, depth=0.5, distance=distance, n1=n1, n2=n2
        )
        assert 0 < x < distance
        assert n1 * np.sin(incidence) == pytest.approx(n2 * np.sin(refracted), abs=1e-7)


def test_the_least_time_path_in_one_medium_is_straight():
    x, _, _ = least_time_path(height=1.0, depth=1.0, distance=2.0, n1=1.2, n2=1.2)
    assert x == pytest.approx(1.0, abs=1e-7)


def test_solved_fresnel_amplitudes_match_the_closed_forms_and_conserve_power():
    theta = np.radians(np.linspace(0, 89, 90))
    for n1, n2 in [(1.0, 1.5), (1.5, 1.0), (1.333, 1.0)]:
        solved, closed = fresnel_solved(theta, n1, n2), fresnel_closed(theta, n1, n2)
        for key in solved:
            np.testing.assert_allclose(solved[key], closed[key], atol=1e-12)
        for r, t in (("rs", "ts"), ("rp", "tp")):
            total = reflectance(solved[r]) + transmittance(solved[t], theta, n1, n2)
            np.testing.assert_allclose(total, 1.0, atol=1e-12)


def test_normal_incidence_and_total_reflection():
    normal = fresnel_solved(0.0, 1.0, 1.5)
    assert normal["rs"][0].real == pytest.approx(-0.2)
    assert normal["rp"][0].real == pytest.approx(0.2)  # the opposite sign convention
    beyond = np.radians([45.0, 60.0, 85.0])
    total = fresnel_solved(beyond, 1.5, 1.0)
    np.testing.assert_allclose(reflectance(total["rs"]), 1.0, atol=1e-12)
    np.testing.assert_allclose(reflectance(total["rp"]), 1.0, atol=1e-12)
    np.testing.assert_allclose(
        transmittance(total["ts"], beyond, 1.5, 1.0), 0.0, atol=1e-12
    )


def test_r_p_vanishes_at_the_brewster_angle():
    found = bisect_root(lambda a: fresnel_solved(a, 1.0, 1.5)["rp"][0].real, 0.1, 1.5)
    assert found == pytest.approx(brewster_angle(1.0, 1.5), abs=1e-10)
    with pytest.raises(ValueError):
        bisect_root(lambda a: a + 1.0, 0.0, 1.0)


def test_node_speeds_put_the_mean_slowness_on_the_interface():
    x = np.linspace(0.0, 1.0, 11)
    speeds = node_speeds(x, interface=0.5, c1=1.0, c2=0.5)
    assert list(speeds[:5]) == [1.0] * 5 and list(speeds[6:]) == [0.5] * 5
    assert speeds[5] ** -2 == pytest.approx((1.0 + 4.0) / 2)


def test_solve_varying_with_one_speed_is_the_scheme_of_lesson_w1():
    x = grid(1.0, 100)
    u0 = standing_mode(x, 0.0, length=1.0, n=2, c=1.0)
    ours = solve_varying(
        u0, np.zeros_like(x), speeds=np.ones_like(x), dx=0.01, dt=0.005, n_steps=150
    )
    theirs = solve(
        u0, np.zeros_like(x), c=1.0, dx=0.01, dt=0.005, n_steps=150, every=150
    )
    np.testing.assert_allclose(ours, theirs.u[-1], atol=1e-12)


def test_a_pulse_across_an_interface_converges_at_second_order():
    def profile(z):
        return np.exp(-(((z - 0.25) / 0.03) ** 2))

    def slope(z):
        return -2 * (z - 0.25) / 0.03**2 * profile(z)

    errors = []
    for cells in (200, 400, 800):
        x = np.linspace(0, 1, cells + 1)
        dx = 1 / cells
        speeds = node_speeds(x, interface=0.5, c1=1.0, c2=1 / 1.5)
        steps = round(0.45 / (0.5 * dx))
        u = solve_varying(
            profile(x), -slope(x), speeds=speeds, dx=dx, dt=0.5 * dx, n_steps=steps
        )
        exact = interface_exact(
            x, steps * 0.5 * dx, profile, interface=0.5, c1=1.0, c2=1 / 1.5
        )
        errors.append(np.sqrt(np.mean((u - exact) ** 2)))
    assert np.log2(errors[0] / errors[1]) == pytest.approx(2.0, abs=0.1)
    assert np.log2(errors[1] / errors[2]) == pytest.approx(2.0, abs=0.1)


def test_solve_varying_refuses_a_courant_number_above_one():
    x = np.linspace(0, 1, 11)
    with pytest.raises(ValueError):
        solve_varying(x, x, speeds=np.ones_like(x), dx=0.1, dt=0.2, n_steps=2)


# Polarisation


def test_intensity_of_the_sampled_field_is_the_squared_length():
    for jones in (
        linear(0.3),
        circular(1),
        np.array([0.6, 0.8j]),
        np.array([2.0, 0.0]),
    ):
        assert intensity(jones) == pytest.approx(np.sum(np.abs(jones) ** 2), abs=1e-14)


def test_malus_law_for_ideal_and_leaky_polarisers():
    for angle in np.radians([0, 20, 45, 77, 90, 135]):
        assert intensity(polariser(angle) @ linear(0.0)) == pytest.approx(
            malus(angle), abs=1e-14
        )
        assert intensity(polariser(angle, 1e-3) @ linear(0.0)) == pytest.approx(
            malus(angle, 1e-3), abs=1e-14
        )
    with pytest.raises(ValueError):
        polariser(0.0, 1.5)


def test_a_chain_of_polarisers_against_the_closed_form():
    for n in (1, 2, 7, 30):
        beam = linear(0.0)
        for k in range(1, n + 1):
            beam = polariser(k * np.pi / (2 * n)) @ beam
        assert intensity(beam) == pytest.approx(chain_transmission(n), abs=1e-13)
    assert chain_transmission(1000) == pytest.approx(1 - np.pi**2 / 4000, rel=1e-5)


def test_a_quarter_wave_plate_makes_circular_light():
    out = retarder(0.0, np.pi / 2) @ linear(np.pi / 4)
    s = stokes_closed(out)
    assert s[3] == pytest.approx(1.0) and abs(s[1]) < 1e-15 and abs(s[2]) < 1e-15
    with pytest.raises(ValueError):
        circular(0)


def test_measured_stokes_parameters_match_the_closed_forms():
    states = [
        linear(0.0),
        linear(1.1),
        circular(1),
        circular(-1),
        np.array([0.6, 0.8 * np.exp(0.4j)]),
    ]
    for state in states:
        np.testing.assert_allclose(
            stokes_measured(state), stokes_closed(state), atol=1e-13
        )
        assert degree_of_polarisation(stokes_measured(state)) == pytest.approx(1.0)


def test_unpolarised_light_passes_one_polariser_by_half():
    states = unpolarised(20_000, np.random.default_rng(1))
    values = intensity(states @ polariser(0.4).T)
    error = np.std(values) / np.sqrt(values.size)
    assert abs(np.mean(values) - 0.5) < 4 * error
    assert degree_of_polarisation(stokes_measured(states)) < 5 / np.sqrt(
        states.shape[0]
    )


# Diffraction


def test_aperture_pieces_cover_the_openings():
    points, widths = aperture([(0.0, 1.0), (2.0, 2.5)], 4)
    assert widths.sum() == pytest.approx(1.5)
    assert points[0] == pytest.approx(0.125) and points[-1] == pytest.approx(2.4375)
    with pytest.raises(ValueError):
        aperture([(1.0, 0.0)], 4)
    with pytest.raises(ValueError):
        slits(2, 2.0, 1.0, 4)


def test_far_field_of_one_slit_is_a_sinc():
    lam, a = 500e-9, 20e-6
    points, widths = slits(1, a, a, 2000)
    s = np.linspace(-0.08, 0.08, 101)
    field = far_field(s, points, widths, lam)
    np.testing.assert_allclose(
        np.abs(field) / a, np.abs(np.sinc(a * s / lam)), atol=1e-5
    )


def test_zeros_and_maxima_of_slits_and_gratings():
    lam = 600e-9
    one = slits(1, 30e-6, 30e-6, 300)
    assert abs(far_field(single_slit_zero(2, 30e-6, lam), *one, lam)[0]) < 1e-12
    two = slits(2, 30e-6, 120e-6, 300)
    assert abs(far_field(double_slit_zero(3, 120e-6, lam), *two, lam)[0]) < 1e-12
    many = slits(8, 5e-6, 20e-6, 20)
    peak = abs(far_field(grating_maximum(1, 20e-6, lam), *many, lam)[0])
    beside = abs(far_field(grating_maximum(1, 20e-6, lam) * 1.01, *many, lam)[0])
    assert peak > beside
    with pytest.raises(ValueError):
        single_slit_zero(0, 1e-6, lam)


def test_huygens_field_far_away_is_the_far_field():
    lam, a = 600e-9, 20e-6
    points, widths = slits(1, a, a, 400)
    s = np.linspace(-0.05, 0.05, 41)
    far = np.abs(far_field(s, points, widths, lam)) ** 2
    near = np.abs(huygens_field(np.arcsin(s), points, widths, lam, 100.0)) ** 2
    np.testing.assert_allclose(near / near[20], far / far[20], atol=1e-6)
    flat = np.abs(field_at([0.0], [100.0], points, widths, lam)) ** 2 * 100.0
    assert flat[0] == pytest.approx(near[20], rel=1e-9)


def test_airy_pattern_first_zero_and_rayleigh_dip():
    lam, d = 500e-9, 0.05
    unit = lam / d
    zero = bisect_root(lambda s: float(circular_field(s, d, lam)[0]), unit, 1.4 * unit)
    assert zero / unit == pytest.approx(AIRY_FIRST_ZERO, abs=1e-6)
    assert abs(AIRY_FIRST_ZERO - 1.21967) < 1e-5
    assert circular_field(0.0, d, lam)[0] == pytest.approx(1.0)
    image = two_points(np.array([0.0]), AIRY_FIRST_ZERO * unit, d, lam)
    peak = two_points(
        np.array([AIRY_FIRST_ZERO * unit / 2]), AIRY_FIRST_ZERO * unit, d, lam
    )
    assert image[0] / peak[0] == pytest.approx(0.735, abs=2e-3)


# Inverse optics


def test_double_slit_model_limits():
    s = np.linspace(-0.01, 0.01, 11)
    model = double_slit_model(s, 10.0, 2.0, 40e-6, 200e-6, 633e-9)
    assert model[5] == pytest.approx(12.0)
    zero = double_slit_zero(0, 200e-6, 633e-9)
    assert double_slit_model(zero, 10.0, 2.0, 40e-6, 200e-6, 633e-9) == pytest.approx(
        2.0
    )


def synthetic(rng, peak=2000.0):
    _, s = detector(1200, 50e-6, 2.0)
    expected = double_slit_model(s, peak, 20.0, 40e-6, 200e-6, 633e-9)
    return s, rng.poisson(expected).astype(float)


def test_the_start_finds_the_separation_from_the_fringes():
    s, counts = synthetic(np.random.default_rng(3))
    guess = start(s, counts, 633e-9)
    assert guess[3] == pytest.approx(200e-6, rel=0.1)


def test_the_fit_recovers_the_slits_within_their_errors():
    s, counts = synthetic(np.random.default_rng(4))
    result = fit(s, counts, 633e-9)
    assert abs(result.value("width") - 40e-6) < 4 * result.error("width")
    assert abs(result.value("separation") - 200e-6) < 4 * result.error("separation")
    assert result.chi2 / result.dof == pytest.approx(1.0, abs=0.15)


def test_the_wavelength_and_the_slits_are_not_identified_together():
    s, _ = synthetic(np.random.default_rng(5))
    jacobian = scaled_jacobian(s, 2000.0, 20.0, 40e-6, 200e-6, 633e-9)
    known = np.linalg.svd(jacobian[:, :4], compute_uv=False)
    free = np.linalg.svd(jacobian, compute_uv=False)
    assert known[-1] / known[0] > 1e-3
    assert free[-1] / free[0] < 1e-8
