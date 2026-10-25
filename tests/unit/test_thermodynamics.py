from itertools import pairwise
from math import comb, log

import numpy as np
import pytest

from pbc.abm.gas import mean_and_error
from pbc.thermodynamics import cycles, diffusion, entropy, ising, kinetic, molecular

# --- diffusion -----------------------------------------------------------------


def test_random_walks_are_a_function_of_the_seed():
    first = diffusion.random_walks(20, 30, 0.1, np.random.default_rng(3))
    again = diffusion.random_walks(20, 30, 0.1, np.random.default_rng(3))
    other = diffusion.random_walks(20, 30, 0.1, np.random.default_rng(4))
    np.testing.assert_array_equal(first, again)
    assert not np.array_equal(first, other)
    assert first.shape == (31, 20, 2)
    np.testing.assert_array_equal(first[0], 0.0)


def test_every_step_has_the_stated_length():
    paths = diffusion.random_walks(50, 40, 0.25, np.random.default_rng(0))
    lengths = np.hypot(*np.diff(paths, axis=0).transpose(2, 0, 1))
    np.testing.assert_allclose(lengths, 0.25)
    line = diffusion.random_walks(50, 40, 0.25, np.random.default_rng(0), dimension=1)
    np.testing.assert_allclose(np.abs(np.diff(line, axis=0)), 0.25)


@pytest.mark.parametrize("dimension", [1, 2])
def test_the_measured_diffusion_coefficient_matches_the_random_walk_prediction(
    dimension,
):
    step, tau, n_steps = 0.1, 0.5, 200
    times = tau * np.arange(n_steps + 1)
    estimates = []
    for seed in range(6):
        paths = diffusion.random_walks(
            500, n_steps, step, np.random.default_rng(seed), dimension
        )
        msd = diffusion.mean_squared_displacement(paths)
        estimates.append(diffusion.diffusion_coefficient(times, msd, dimension))
    mean, error = mean_and_error(np.array(estimates))
    predicted = diffusion.predicted_diffusion_coefficient(step, tau, dimension)
    assert abs(mean - predicted) <= 4.0 * error
    # The tolerance is not so wide that a wrong prediction passes.
    assert abs(mean - 2.0 * predicted) > 4.0 * error


def test_the_mean_squared_displacement_of_one_known_path():
    paths = np.array([[[0.0, 0.0]], [[3.0, 4.0]]])
    np.testing.assert_allclose(diffusion.mean_squared_displacement(paths), [0.0, 25.0])
    # <r²> = 4 D t in the plane: D = 25 / (4 * 5) at t = 5 s.
    assert diffusion.diffusion_coefficient(
        np.array([0.0, 5.0]), np.array([0.0, 25.0])
    ) == (pytest.approx(25.0 / 20.0))


def test_the_fraction_within_a_radius_follows_the_gaussian_prediction():
    step, tau, n_steps = 0.1, 0.5, 100
    d = diffusion.predicted_diffusion_coefficient(step, tau)
    t = tau * n_steps
    radius = np.sqrt(4.0 * d * t * log(2.0))  # the median distance
    assert diffusion.predicted_fraction_within(radius, d, t) == pytest.approx(0.5)
    fractions = [
        diffusion.fraction_within(
            diffusion.random_walks(2000, n_steps, step, np.random.default_rng(s))[-1],
            radius,
        )
        for s in range(6)
    ]
    mean, error = mean_and_error(np.array(fractions))
    assert abs(mean - 0.5) <= 4.0 * error


def test_random_walks_refuse_bad_arguments():
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError):
        diffusion.random_walks(0, 10, 1.0, rng)
    with pytest.raises(ValueError):
        diffusion.random_walks(10, 10, 1.0, rng, dimension=3)


# --- kinetic -------------------------------------------------------------------


def test_the_quantile_inverts_the_distribution_function():
    p = np.linspace(0.05, 0.95, 10)
    v = kinetic.speed_quantile(p, 0.7, 2.0)
    np.testing.assert_allclose(kinetic.speed_cdf(v, 0.7, 2.0), p)


def test_the_distribution_has_the_stated_moments():
    rng = np.random.default_rng(0)
    kt, mass = 0.8, 1.5
    velocities = rng.normal(0.0, np.sqrt(kt / mass), size=(400_000, 2))
    speeds = np.hypot(*velocities.T)
    assert speeds.mean() == pytest.approx(kinetic.mean_speed(kt, mass), rel=5e-3)
    counts, edges = np.histogram(speeds, bins=200)
    peak = 0.5 * (edges[np.argmax(counts)] + edges[np.argmax(counts) + 1])
    assert peak == pytest.approx(kinetic.most_probable_speed(kt, mass), abs=0.05)


def test_the_empirical_distribution_function():
    assert list(
        kinetic.fractions_below(
            np.array([1.0, 2.0, 3.0, 4.0]), np.array([0.5, 2.5, 9.0])
        )
    ) == [
        0.0,
        0.5,
        1.0,
    ]


def test_the_simulated_gas_follows_the_analytic_distribution_at_its_temperature():
    from pbc.abm.gas import measure, temperature

    probabilities = np.array([0.1, 0.25, 0.5, 0.75, 0.9])
    deviations = []
    for seed in range(6):
        m = measure(seed)
        v = kinetic.speed_quantile(probabilities, temperature(m.speeds, 1.0), 1.0)
        deviations.append(kinetic.fractions_below(m.speeds, v) - probabilities)
    mean = np.mean(deviations, axis=0)
    error = np.std(deviations, axis=0, ddof=1) / np.sqrt(6)
    assert np.all(np.abs(mean) <= 4.0 * error)


# --- entropy -------------------------------------------------------------------


def test_log_multiplicity_equals_the_log_of_the_binomial_coefficient():
    n = np.arange(0, 11)
    np.testing.assert_allclose(
        entropy.log_multiplicity(10, n), [log(comb(10, int(k))) for k in n]
    )
    assert entropy.log_multiplicity(10, np.array(3)).shape == (1,)


def test_stirling_approaches_the_exact_multiplicity():
    for n in (10, 100, 1000):
        exact = entropy.log_multiplicity(n, np.array([n // 2]))[0]
        assert abs(entropy.stirling_log_multiplicity_half(n) - exact) < 1.0 / n


def test_the_ensemble_starts_where_it_is_told_and_moves_one_particle_a_step():
    counts = entropy.ehrenfest_ensemble(20, 50, 100, np.random.default_rng(0))
    assert np.all(counts[0] == 20)
    assert set(np.abs(np.diff(counts, axis=0)).ravel()) == {0, 1}
    assert counts.min() >= 0 and counts.max() <= 20
    again = entropy.ehrenfest_ensemble(20, 50, 100, np.random.default_rng(0))
    np.testing.assert_array_equal(counts, again)


def test_the_ensemble_mean_follows_the_exact_formula():
    n, members, steps = 50, 4000, 120
    counts = entropy.ehrenfest_ensemble(n, members, steps, np.random.default_rng(1))
    exact = entropy.mean_left(n, n, np.arange(steps + 1))
    sem = counts.std(axis=1, ddof=1) / np.sqrt(members)
    # Each time is a separate comparison: allow five standard errors.
    assert np.all(np.abs(counts.mean(axis=1) - exact) <= 5.0 * sem + 1e-12)


def test_the_gibbs_entropy_of_equilibrium_is_n_ln_2():
    n = 12
    binomial = np.array([comb(n, k) for k in range(n + 1)]) / 2**n
    assert entropy.gibbs_entropy(binomial, n) == pytest.approx(
        entropy.equilibrium_entropy(n)
    )
    # The Shannon entropy of the macrostate alone is smaller.
    assert entropy.shannon_entropy(binomial) < entropy.equilibrium_entropy(n)


def test_the_gibbs_entropy_of_a_single_macrostate_is_its_boltzmann_entropy():
    n = 12
    p = np.zeros(n + 1)
    p[4] = 1.0
    assert entropy.gibbs_entropy(p, n) == pytest.approx(log(comb(n, 4)))
    p = np.zeros(n + 1)
    p[n] = 1.0
    assert entropy.gibbs_entropy(p, n) == pytest.approx(0.0)


def test_the_exact_gibbs_entropy_never_decreases_under_the_dynamics():
    n = 10
    rows = entropy.exact_distribution(n, n, 300)
    values = [entropy.gibbs_entropy(row, n) for row in rows]
    assert values[0] == pytest.approx(0.0)
    assert all(b >= a - 1e-12 for a, b in pairwise(values))
    assert values[-1] == pytest.approx(entropy.equilibrium_entropy(n), rel=1e-3)
    np.testing.assert_allclose(rows.sum(axis=1), 1.0)


def test_the_exact_distribution_has_the_exact_mean_and_the_binomial_limit():
    n = 10
    rows = entropy.exact_distribution(n, n, 400)
    means = rows @ np.arange(n + 1)
    np.testing.assert_allclose(means, entropy.mean_left(n, n, np.arange(401)))
    binomial = np.array([comb(n, k) for k in range(n + 1)]) / 2**n
    np.testing.assert_allclose(rows[-1], binomial, atol=1e-6)


def test_the_plug_in_estimate_of_the_equilibrium_entropy_is_low_by_the_stated_bias():
    n, members = 12, 20000
    raw, corrected = [], []
    for seed in range(6):
        counts = entropy.ehrenfest_ensemble(
            n, members, 12 * n, np.random.default_rng(seed)
        )
        p = entropy.distribution(counts[-1], n)
        raw.append(entropy.gibbs_entropy(p, n))
        corrected.append(raw[-1] + entropy.plug_in_bias(p, members))
    exact = entropy.equilibrium_entropy(n)
    mean, error = mean_and_error(np.array(corrected))
    assert abs(mean - exact) <= 4.0 * error
    raw_mean, raw_error = mean_and_error(np.array(raw))
    assert exact - raw_mean > 4.0 * raw_error


def test_plug_in_bias_counts_the_observed_macrostates():
    assert entropy.plug_in_bias(np.array([0.5, 0.5, 0.0]), 100) == pytest.approx(
        1 / 200
    )


def test_ehrenfest_refuses_bad_arguments():
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError):
        entropy.ehrenfest_ensemble(0, 10, 10, rng)
    with pytest.raises(ValueError):
        entropy.ehrenfest_ensemble(10, 10, 10, rng, n_start=11)


# --- ising ---------------------------------------------------------------------


def test_the_critical_temperature_is_where_sinh_2_over_t_is_one():
    tc = ising.critical_temperature()
    assert np.sinh(2.0 / tc) == pytest.approx(1.0, abs=1e-14)
    assert tc == pytest.approx(2.269185, abs=1e-6)


def test_onsagers_magnetisation_is_one_cold_zero_above_tc_and_falls_between():
    tc = ising.critical_temperature()
    t = np.linspace(0.5, tc - 1e-9, 200)
    m = ising.onsager_magnetisation(t)
    assert m[0] == pytest.approx(1.0, abs=1e-6)
    assert np.all(np.diff(m) < 0.0)
    assert m[-1] < 0.1
    np.testing.assert_array_equal(ising.onsager_magnetisation([tc, 3.0, 10.0]), 0.0)


def test_energy_and_magnetisation_of_ordered_lattices():
    up = np.ones((1, 6, 6), dtype=np.int8)
    np.testing.assert_array_equal(ising.energy(up), [-2.0 * 36])
    np.testing.assert_array_equal(ising.magnetisation(up), [1.0])
    i, j = np.indices((6, 6))
    staggered = np.where((i + j) % 2 == 0, 1, -1).astype(np.int8)[None]
    np.testing.assert_array_equal(ising.energy(staggered), [2.0 * 36])
    np.testing.assert_array_equal(ising.magnetisation(staggered), [0.0])


def test_the_exact_averages_of_the_two_by_two_lattice_are_its_closed_form():
    # The 2 x 2 periodic lattice counts each neighbour pair twice: two states
    # at E = -8, twelve at 0, two at +8.
    t = np.array([1.0, 2.5, 6.0])
    b = 1.0 / t
    z = 2.0 * np.exp(8.0 * b) + 12.0 + 2.0 * np.exp(-8.0 * b)
    energy = (-16.0 * np.exp(8.0 * b) + 16.0 * np.exp(-8.0 * b)) / z
    # |m| is 1 for the two ordered states and 1/2 for the eight with one spin
    # flipped; zero for the other six.
    abs_m = (2.0 * np.exp(8.0 * b) + 8.0 * 0.5) / z
    found_m, found_e = ising.exact_averages(2, t)
    np.testing.assert_allclose(found_e, energy / 4.0, rtol=1e-12)
    np.testing.assert_allclose(found_m, abs_m, rtol=1e-12)


def test_the_metropolis_sampler_finds_the_exact_averages_of_a_small_lattice():
    t = np.array([2.5])
    exact_m, exact_e = ising.exact_averages(4, t)
    m, e = ising.simulate(4, t, 16, 2000, 200, np.random.default_rng(5))
    mean, error = mean_and_error(np.abs(m[:, 0]).mean(axis=0))
    assert abs(mean - exact_m[0]) <= 4.0 * error
    mean, error = mean_and_error(e[:, 0].mean(axis=0))
    assert abs(mean - exact_e[0]) <= 4.0 * error
    # The tolerance is not so wide that the averages of another temperature pass.
    _, other_e = ising.exact_averages(4, [2.2])
    assert abs(mean - other_e[0]) > 4.0 * error


def test_the_heat_capacity_is_the_derivative_of_the_mean_energy():
    t, h = np.array([2.0, 2.4, 3.0]), 1e-5
    _, e_plus = ising.exact_averages(4, t + h)
    _, e_minus = ising.exact_averages(4, t - h)
    np.testing.assert_allclose(
        ising.exact_heat_capacity(4, t), (e_plus - e_minus) / (2 * h), rtol=1e-6
    )


def test_the_binder_cumulant_of_the_two_limits():
    assert ising.binder_cumulant(np.array([1.0, -1.0, 1.0, -1.0])) == pytest.approx(
        2.0 / 3.0
    )
    gaussian = np.random.default_rng(0).normal(size=400_000)
    assert ising.binder_cumulant(gaussian) == pytest.approx(0.0, abs=0.01)


def test_the_crossing_of_two_lines():
    t = np.linspace(2.0, 2.5, 6)
    assert ising.crossing(t, 1.0 - t, 2.0 * t - 5.0) == pytest.approx(2.0)
    with pytest.raises(ValueError):
        ising.crossing(t, t, t + 1.0)


def test_the_jackknife_error_of_a_mean_is_its_standard_error():
    x = np.random.default_rng(2).normal(size=12)
    value, error = ising.jackknife(np.mean, x)
    assert value == pytest.approx(x.mean())
    assert error == pytest.approx(x.std(ddof=1) / np.sqrt(x.size))


def test_the_checkerboard_needs_an_even_lattice():
    with pytest.raises(ValueError):
        ising.checkerboard(5)


# --- molecular dynamics --------------------------------------------------------


def test_the_shifted_force_potential_and_its_force_vanish_at_the_cut_off():
    rc, h = molecular.CUTOFF, 1e-6
    assert molecular.shifted_force(np.array([rc]))[0] == 0.0
    slope = (
        molecular.shifted_force(np.array([rc - h]))[0]
        - molecular.shifted_force(np.array([rc - 2 * h]))[0]
    ) / h
    assert abs(slope) < 1e-5
    # Inside, it differs from Lennard-Jones by a straight line.
    r = np.array([1.0, 1.5, 2.0])
    gap = molecular.lennard_jones(r) - molecular.shifted_force(r)
    assert np.diff(gap, 2)[0] == pytest.approx(0.0, abs=1e-12)


def test_the_forces_are_minus_the_gradient_of_the_potential_energy():
    box = 6.0
    x = molecular.square_lattice(4, box) + np.random.default_rng(1).normal(
        scale=0.15, size=(16, 2)
    )
    f, u, _ = molecular.forces(x, box)
    h = 1e-6
    for i, k in [(0, 0), (5, 1), (11, 0)]:
        plus, minus = x.copy(), x.copy()
        plus[i, k] += h
        minus[i, k] -= h
        gradient = (
            molecular.forces(plus, box)[1] - molecular.forces(minus, box)[1]
        ) / (2 * h)
        assert f[i, k] == pytest.approx(-gradient, rel=1e-5, abs=1e-6)
    np.testing.assert_allclose(f.sum(axis=0), 0.0, atol=1e-10)
    assert np.isfinite(u)


def test_the_energy_error_of_velocity_verlet_is_of_second_order():
    box, m = 7.0, np.ones(16)
    x0 = molecular.square_lattice(4, box)
    v0 = molecular.initial_velocities(m, np.full(16, 1.0), np.random.default_rng(3))
    spread = []
    for dt in (0.01, 0.005):
        run = molecular.velocity_verlet(x0, v0, m, box, dt, round(2.0 / dt))
        spread.append(np.std(run.energy))
    assert spread[0] / spread[1] == pytest.approx(4.0, rel=0.2)


def test_the_temperature_of_two_particles_with_no_total_momentum_is_shared():
    masses = np.array([1.0, 3.0])
    velocities = np.array([[3.0, -1.5], [-1.0, 0.5]])  # sum m v = 0
    light = molecular.temperature(velocities, masses, np.array([0]))
    heavy = molecular.temperature(velocities, masses, np.array([1]))
    np.testing.assert_allclose(light, heavy)
    # Without the share of the centre of mass the two would differ.
    assert masses[0] * velocities[0, 0] ** 2 != masses[1] * velocities[1, 0] ** 2


def test_initial_velocities_carry_no_momentum():
    m = np.array([1.0, 4.0] * 20)
    v = molecular.initial_velocities(m, np.full(40, 2.0), np.random.default_rng(0))
    np.testing.assert_allclose((m[:, None] * v).sum(axis=0), 0.0, atol=1e-12)


def test_the_virial_pressure_without_forces_is_the_ideal_gas():
    assert molecular.virial_pressure(50, 1.5, 0.0, 10.0) == pytest.approx(
        50 * 1.5 / 100.0
    )


def test_forces_refuse_a_box_smaller_than_twice_the_cut_off():
    with pytest.raises(ValueError):
        molecular.forces(np.zeros((2, 2)), 4.0)


# --- heat engines --------------------------------------------------------------


def test_an_isotherm_takes_in_n_r_t_ln_v2_over_v1_and_an_adiabat_none():
    gas = cycles.Gas()
    leg = cycles.isotherm("expansion", 400.0, 0.01, 0.03, 201)
    exact = cycles.R * 400.0 * log(3.0)
    assert cycles.heat(gas, leg) == pytest.approx(exact, rel=1e-12)
    assert cycles.work(gas, leg) == pytest.approx(exact, rel=1e-4)
    adiabat = cycles.adiabat(gas, "expansion", 0.01, 400.0, 0.03, 201)
    assert abs(cycles.heat(gas, adiabat)) < 1e-9
    assert cycles.work(gas, adiabat) == pytest.approx(
        -cycles.energy_change(gas, adiabat), rel=1e-4
    )


def test_the_first_law_residual_falls_at_second_order():
    gas = cycles.Gas()
    residuals = [
        abs(
            cycles.balance(
                gas, cycles.otto(gas, 600.0, 300.0, 0.1, 4.0, n), 600.0, 300.0
            ).first_law_residual
        )
        for n in (21, 41, 81)
    ]
    assert residuals[0] / residuals[1] == pytest.approx(4.0, rel=0.05)
    assert residuals[1] / residuals[2] == pytest.approx(4.0, rel=0.05)


def test_the_cycles_meet_their_closed_forms_and_the_carnot_bound():
    gas, hot, cold = cycles.Gas(), 600.0, 300.0
    bound = cycles.carnot_efficiency(hot, cold)
    c = cycles.balance(gas, cycles.carnot(gas, hot, cold, 0.01, 2.0, 2001), hot, cold)
    assert c.efficiency == pytest.approx(bound, abs=1e-6)
    assert abs(c.reservoir_entropy) < 1e-6
    o = cycles.balance(gas, cycles.otto(gas, hot, cold, 0.1, 4.0, 2001), hot, cold)
    assert o.efficiency == pytest.approx(cycles.otto_efficiency(gas, 4.0), abs=1e-6)
    b = cycles.balance(gas, cycles.brayton(gas, hot, cold, 25e3, 8.0, 2001), hot, cold)
    assert b.efficiency == pytest.approx(cycles.brayton_efficiency(gas, 8.0), abs=1e-6)
    s = cycles.balance(
        gas, cycles.stirling(gas, hot, cold, 0.1, 4.0, 2001, True), hot, cold
    )
    assert s.efficiency == pytest.approx(bound, abs=1e-6)
    for engine in (o, b):
        assert engine.efficiency < bound
        assert engine.reservoir_entropy > 0.0


def test_a_claimed_engine_beyond_carnot_lowers_the_entropy_of_the_reservoirs():
    assert cycles.reservoir_entropy(1000.0, 400.0, 600.0, 300.0) < 0.0
    assert cycles.reservoir_entropy(1000.0, 500.0, 600.0, 300.0) == pytest.approx(0.0)


def test_cycles_refuse_impossible_settings():
    gas = cycles.Gas()
    with pytest.raises(ValueError):
        cycles.otto(gas, 600.0, 300.0, 0.1, 6.0, 11)
    legs = cycles.carnot(gas, 600.0, 300.0, 0.01, 2.0, 11)
    with pytest.raises(ValueError):
        cycles.balance(gas, legs[:3], 600.0, 300.0)
