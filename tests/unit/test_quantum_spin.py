"""Spin one half, pairs of spins, and the open qubit (lessons Q4, Q5, Q6):
each result is compared with a closed form, an exact enumeration, or an
independent computation, with a stated tolerance."""

import numpy as np
import pytest
from scipy.integrate import solve_ivp
from scipy.linalg import expm

from pbc.quantum.bell import (
    CHSH_ANGLES,
    LOCAL_BOUND,
    SINGLET,
    TSIRELSON_BOUND,
    chsh,
    chsh_error,
    correlation,
    correlation_error,
    density,
    deterministic_strategies,
    family,
    joint_probabilities,
    local_correlation,
    local_counts,
    local_outcomes,
    marginal,
    quantum_correlation,
    sample_counts,
    setting_pairs,
    werner,
)
from pbc.quantum.open_systems import (
    choi,
    coherence_time,
    euler_step,
    evolve,
    exact_qubit,
    expectation,
    exponential_step,
    generator,
    lindblad,
    partial_trace,
    plus_x,
    purity,
    qubit,
    qubit_terms,
    ramsey,
    random_phase_coherence,
    rk4_step,
    smallest_eigenvalue,
    trace,
)
from pbc.quantum.spin import (
    ELECTRON_MOMENT,
    IDENTITY,
    SIGMA_X,
    SIGMA_Y,
    SIGMA_Z,
    SILVER_MASS,
    bloch_vector,
    born_angle,
    deflection,
    direction,
    filters,
    measure,
    probability,
    projector,
    sample_outcomes,
    spin_operator,
    spin_state,
    standard_error,
)

RNG_SEED = 311


def random_density(rng, n=2):
    """A random density matrix of size n: A A^+ / tr(A A^+)."""
    a = rng.normal(size=(n, n)) + 1j * rng.normal(size=(n, n))
    rho = a @ a.conj().T
    return rho / np.trace(rho)


# --- Q4: spin and measurement -------------------------------------------------


def test_the_pauli_matrices_obey_their_algebra():
    for s in (SIGMA_X, SIGMA_Y, SIGMA_Z):
        assert s @ s == pytest.approx(IDENTITY)
    commutator = SIGMA_X @ SIGMA_Y - SIGMA_Y @ SIGMA_X
    assert commutator == pytest.approx(2j * SIGMA_Z)


def test_the_projectors_split_the_identity_along_any_direction():
    rng = np.random.default_rng(RNG_SEED)
    for theta, phi in rng.uniform(0, np.pi, (5, 2)):
        n = direction(theta, 2 * phi)
        plus, minus = projector(n, 1), projector(n, -1)
        assert plus + minus == pytest.approx(IDENTITY)
        assert plus @ plus == pytest.approx(plus)
        assert plus @ minus == pytest.approx(np.zeros((2, 2)), abs=1e-15)
        assert np.linalg.eigvalsh(spin_operator(n)) == pytest.approx([-1, 1])
    with pytest.raises(ValueError):
        projector(direction(0.0), 0)


def test_the_state_points_along_its_direction():
    for theta, phi in [(0.0, 0.0), (0.7, 1.9), (np.pi / 2, -0.4), (np.pi, 0.0)]:
        state = spin_state(theta, phi)
        assert np.linalg.norm(state) == pytest.approx(1.0)
        assert bloch_vector(state) == pytest.approx(direction(theta, phi), abs=1e-15)


def test_the_born_rule_depends_only_on_the_angle_between_the_directions():
    rng = np.random.default_rng(RNG_SEED)
    for (t1, p1), (t2, p2) in rng.uniform(0, np.pi, (8, 2, 2)):
        state, n = spin_state(t1, 2 * p1), direction(t2, 2 * p2)
        angle = np.arccos(np.clip(direction(t1, 2 * p1) @ n, -1, 1))
        assert probability(state, n) == pytest.approx(born_angle(angle))
        assert probability(state, n) + probability(state, n, -1) == pytest.approx(1)


def test_a_measurement_leaves_the_spin_along_its_outcome():
    rng = np.random.default_rng(RNG_SEED)
    n = direction(1.1, 0.3)
    outcomes = []
    for _ in range(4000):
        outcome, after = measure(spin_state(0.4), n, rng)
        outcomes.append(outcome)
        assert probability(after, n, outcome) == pytest.approx(1.0)
    p = probability(spin_state(0.4), n)
    fraction = np.mean(np.array(outcomes) == 1)
    assert abs(fraction - p) < 4 * standard_error(p, 4000)


def test_the_standard_error_is_the_spread_of_binomial_fractions():
    rng = np.random.default_rng(RNG_SEED)
    state, n = spin_state(0.0), direction(np.radians(70))
    fractions = [sample_outcomes(state, n, 400, rng) / 400 for _ in range(3000)]
    p = born_angle(np.radians(70))
    assert np.std(fractions) == pytest.approx(standard_error(p, 400), rel=0.05)


def test_a_blocked_beam_is_not_measured_again():
    rng = np.random.default_rng(RNG_SEED)
    z, x = direction(0.0), direction(np.pi / 2)
    for _ in range(200):
        outcomes = filters(spin_state(np.pi / 3), [z, z, x], rng)
        assert outcomes[:2] in ([-1], [1, 1])
        assert len(outcomes) == (1 if outcomes[0] == -1 else 3)


def test_the_deflection_is_the_integrated_trajectory():
    # An independent computation: the atom's height integrated by an
    # adaptive Runge-Kutta method, with the force on in the magnet only.
    gradient, length, drift, speed = 800.0, 0.04, 0.2, 600.0
    force = ELECTRON_MOMENT * gradient

    def motion(t, y):
        inside = t * speed < length
        return [y[1], force / SILVER_MASS if inside else 0.0]

    end = (length + drift) / speed
    solution = solve_ivp(
        motion,
        (0, end),
        [0.0, 0.0],
        rtol=1e-11,
        atol=1e-15,
        max_step=length / speed / 200,
    )
    found = deflection(ELECTRON_MOMENT, gradient, length, drift, speed)
    assert solution.y[0, -1] == pytest.approx(found, rel=1e-6)
    assert deflection(ELECTRON_MOMENT, gradient, length, drift, speed / 2) == (
        pytest.approx(4 * found)
    )


def test_the_moment_and_the_mass_are_codata_and_the_standard_weight():
    moment, mass = ELECTRON_MOMENT, SILVER_MASS
    assert moment == pytest.approx(9.2847647043e-24, rel=1e-9)
    assert mass == pytest.approx(107.8682 * 1.66053906660e-27, rel=1e-9)


# --- Q5: pairs of spins -------------------------------------------------------


def test_the_singlet_gives_the_textbook_joint_probabilities():
    rho = density(SINGLET)
    for alpha, beta in [(0.0, 0.0), (0.3, 1.4), (2.0, -0.5), (np.pi, 0.0)]:
        p = joint_probabilities(rho, alpha, beta)
        delta = alpha - beta
        expected = (
            np.array(
                [
                    [1 - np.cos(delta), 1 + np.cos(delta)],
                    [1 + np.cos(delta), 1 - np.cos(delta)],
                ]
            )
            / 4
        )
        assert p == pytest.approx(expected, abs=1e-15)
        assert correlation(p) == pytest.approx(quantum_correlation(alpha, beta))


def test_white_noise_scales_the_correlation_by_the_visibility():
    for v in (0.0, 0.4, 1.0):
        p = joint_probabilities(werner(v), 0.2, 1.3)
        assert correlation(p) == pytest.approx(-v * np.cos(1.1), abs=1e-15)
        assert marginal(p) == pytest.approx(0.5)


def test_the_local_model_has_its_straight_line_correlation():
    # The hidden angle on a fine even grid: the average is an integral.
    hidden = (np.arange(400_000) + 0.5) * 2 * np.pi / 400_000
    for alpha, beta in [(0.0, 0.0), (0.0, 0.7), (1.0, -1.2), (0.3, 0.3 + np.pi)]:
        a, b = local_outcomes(alpha, beta, hidden)
        assert np.mean(a * b) == pytest.approx(local_correlation(alpha, beta), abs=1e-4)
        assert np.mean(a) == pytest.approx(0.0, abs=1e-4)


def test_every_deterministic_strategy_has_s_of_two():
    strategies = deterministic_strategies()

    assert len(strategies) == 16
    assert {abs(s) for _, s in strategies} == {LOCAL_BOUND}


def test_the_singlet_reaches_tsirelsons_bound_at_the_chsh_settings():
    rho = density(SINGLET)
    tables = [joint_probabilities(rho, a, b) for a, b in setting_pairs(CHSH_ANGLES)]

    assert abs(chsh([correlation(t) for t in tables])) == pytest.approx(TSIRELSON_BOUND)


def test_the_family_follows_three_cos_minus_cos_three():
    for theta in (0.0, 0.3, np.pi / 4, 1.2):
        pairs = setting_pairs(family(theta))
        s = chsh(quantum_correlation(*np.transpose(pairs)))
        assert s == pytest.approx(-3 * np.cos(theta) + np.cos(3 * theta))


def test_no_product_state_breaks_the_local_bound():
    rng = np.random.default_rng(RNG_SEED)
    for _ in range(200):
        a = spin_state(*rng.uniform(0, 2 * np.pi, 2))
        b = spin_state(*rng.uniform(0, 2 * np.pi, 2))
        angles = rng.uniform(0, 2 * np.pi, 4)
        rho = density(np.kron(a, b))
        tables = [joint_probabilities(rho, x, y) for x, y in setting_pairs(angles)]
        assert abs(chsh([correlation(t) for t in tables])) <= LOCAL_BOUND + 1e-12


def test_the_error_of_s_is_the_spread_of_repeated_estimates():
    rng = np.random.default_rng(RNG_SEED)
    rho = density(SINGLET)
    pairs = setting_pairs(CHSH_ANGLES)
    values, errors = [], []
    for _ in range(600):
        tables = [
            sample_counts(joint_probabilities(rho, a, b), 500, rng) for a, b in pairs
        ]
        values.append(chsh([correlation(t) for t in tables]))
        errors.append(chsh_error([correlation_error(t) for t in tables]))
    assert np.std(values) == pytest.approx(np.mean(errors), rel=0.08)
    assert np.mean(values) == pytest.approx(-TSIRELSON_BOUND, abs=0.01)


def test_the_sampled_local_model_stays_near_its_bound():
    rng = np.random.default_rng(RNG_SEED)
    tables = [local_counts(a, b, 20_000, rng) for a, b in setting_pairs(CHSH_ANGLES)]
    s = chsh([correlation(t) for t in tables])
    error = chsh_error([correlation_error(t) for t in tables])

    assert abs(abs(s) - LOCAL_BOUND) < 4 * error


# --- Q6: the open qubit -------------------------------------------------------


def test_the_generator_is_the_lindblad_equation():
    rng = np.random.default_rng(RNG_SEED)
    h = rng.normal(size=(2, 2)) + 1j * rng.normal(size=(2, 2))
    h = h + h.conj().T
    jumps = [rng.normal(size=(2, 2)) + 1j * rng.normal(size=(2, 2)) for _ in range(2)]
    g = generator(h, jumps)
    for _ in range(3):
        rho = random_density(rng)
        assert (g @ rho.reshape(-1)).reshape(2, 2) == pytest.approx(
            lindblad(rho, h, jumps)
        )
        assert np.trace(lindblad(rho, h, jumps)) == pytest.approx(0, abs=1e-14)


def test_the_choi_matrix_tells_a_positive_map_from_a_completely_positive_one():
    identity = np.eye(4)
    transpose = np.zeros((4, 4))
    for i in range(2):
        for j in range(2):
            transpose[2 * i + j, 2 * j + i] = 1.0

    assert np.linalg.eigvalsh(choi(identity)) == pytest.approx([0, 0, 0, 2])
    # The transpose keeps every rho positive but is not completely positive.
    assert smallest_eigenvalue(choi(transpose)) == pytest.approx(-1.0)


def test_the_exponential_step_is_completely_positive_and_keeps_the_trace():
    rng = np.random.default_rng(RNG_SEED)
    g = qubit(1.3, 0.2, 0.4)
    for dt in (0.01, 1.0, 50.0):
        step = exponential_step(g, dt)
        j = choi(step)
        assert smallest_eigenvalue(j) > -1e-12
        # Trace preservation: the trace over the output of the Choi matrix.
        assert np.einsum("kili->kl", j.reshape(2, 2, 2, 2)) == pytest.approx(
            np.eye(2), abs=1e-12
        )
        rho = random_density(rng)
        after = (step @ rho.reshape(-1)).reshape(2, 2)
        assert np.trace(after) == pytest.approx(1.0)
        assert smallest_eigenvalue(after) > -1e-12


def test_the_qubit_follows_its_closed_form():
    rng = np.random.default_rng(RNG_SEED)
    detuning, decay, dephasing = 0.8, 0.3, 0.15
    rho = random_density(rng)
    times = np.arange(41) * 0.25
    states = evolve(rho, exponential_step(qubit(detuning, decay, dephasing), 0.25), 40)
    exact = exact_qubit(rho, times, detuning, decay, dephasing)
    reference = np.array(
        [expm(t * qubit(detuning, decay, dephasing)) @ rho.reshape(-1) for t in times]
    )

    assert states == pytest.approx(exact, abs=1e-13)
    assert states.reshape(41, 4) == pytest.approx(reference, abs=1e-13)
    assert coherence_time(decay, dephasing) == pytest.approx(1 / 0.3)


def test_rk4_step_is_the_classical_method_on_the_equation():
    rng = np.random.default_rng(RNG_SEED)
    h, jumps = qubit_terms(1.0, 0.1, 0.2)
    rho, dt = random_density(rng), 0.3

    def f(r):
        return lindblad(r, h, jumps)

    k1 = f(rho)
    k2 = f(rho + dt / 2 * k1)
    k3 = f(rho + dt / 2 * k2)
    k4 = f(rho + dt * k3)
    expected = rho + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
    step = rk4_step(generator(h, jumps), dt)

    assert (step @ rho.reshape(-1)).reshape(2, 2) == pytest.approx(expected)
    assert euler_step(generator(h, jumps), dt) @ rho.reshape(-1) == pytest.approx(
        (rho + dt * k1).reshape(-1)
    )


def test_every_step_keeps_the_trace_but_euler_loses_positivity():
    g = qubit(1.0, 0.05, 0.1)
    for make in (euler_step, rk4_step, exponential_step):
        states = evolve(plus_x(), make(g, 0.5), 100)
        assert trace(states) == pytest.approx(np.ones(101), abs=1e-12)
    euler = evolve(plus_x(), euler_step(g, 0.5), 100)
    assert smallest_eigenvalue(euler).min() < -1


def test_the_ramsey_fringe_is_the_mean_of_sigma_x():
    t = np.linspace(0, 20, 9)
    states = exact_qubit(plus_x(), t, 1.0, 0.05, 0.1)

    assert (1 + expectation(states, SIGMA_X)) / 2 == pytest.approx(
        ramsey(t, 1.0, coherence_time(0.05, 0.1))
    )


def test_purity_and_the_partial_trace_of_a_product():
    rng = np.random.default_rng(RNG_SEED)
    a, b = random_density(rng), random_density(rng)
    pair = np.kron(a, b)

    assert partial_trace(pair, 0) == pytest.approx(a)
    assert partial_trace(pair, 1) == pytest.approx(b)
    assert purity(plus_x()) == pytest.approx(1.0)
    assert purity(np.eye(2) / 2) == pytest.approx(0.5)
    with pytest.raises(ValueError):
        partial_trace(pair, 2)


def test_random_phase_kicks_average_to_dephasing():
    rng = np.random.default_rng(RNG_SEED)
    times = np.linspace(0, 10, 21)[1:]
    mean, error = random_phase_coherence(times, 0.2, 4000, rng)

    assert np.all(np.abs(mean.real - np.exp(-0.2 * times)) < 4 * error)
