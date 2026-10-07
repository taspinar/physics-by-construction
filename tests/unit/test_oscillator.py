import numpy as np
import pytest

from pbc.mechanics.dynamics import State, newton, simulate
from pbc.mechanics.oscillator import (
    angular_frequency,
    energy,
    euler_energy_growth,
    harmonic_motion,
    spring,
)

# The oscillator of lesson M4: omega = 2 rad/s, period pi s.
MASS = 0.5
K = 2.0
OMEGA = 2.0


def test_spring_pulls_towards_the_origin_in_proportion_to_the_displacement():
    force = spring(K)(0.0, np.array([1.5, -0.5]), np.array([7.0, 7.0]))

    np.testing.assert_allclose(force, [-3.0, 1.0])


@pytest.mark.parametrize("k", [0.0, -2.0])
def test_a_spring_constant_that_is_not_positive_is_rejected(k: float):
    with pytest.raises(ValueError, match="spring constant"):
        spring(k)
    with pytest.raises(ValueError, match="spring constant"):
        angular_frequency(MASS, k)


def test_angular_frequency_is_the_root_of_k_over_m():
    assert angular_frequency(MASS, K) == pytest.approx(OMEGA)
    with pytest.raises(ValueError, match="mass"):
        angular_frequency(0.0, K)


def test_exact_motion_passes_through_the_initial_state_and_repeats_after_a_period():
    initial = State(t=1.0, x=[0.3, -1.0], v=[2.0, 0.5])
    period = 2 * np.pi / OMEGA

    exact = harmonic_motion(initial, MASS, K, [1.0, 1.0 + period, 1.0 + period / 2])

    np.testing.assert_allclose(exact.x[0], initial.x)
    np.testing.assert_allclose(exact.v[0], initial.v)
    np.testing.assert_allclose(exact.x[1], initial.x, rtol=0, atol=1e-12)
    np.testing.assert_allclose(exact.v[1], initial.v, rtol=0, atol=1e-12)
    # Half a period later the state is reversed.
    np.testing.assert_allclose(exact.x[2], -initial.x, rtol=0, atol=1e-12)
    np.testing.assert_allclose(exact.v[2], -initial.v, rtol=0, atol=1e-12)


def test_exact_motion_satisfies_the_equation_of_motion():
    """dx/dt = v and m dv/dt = -k x, checked with central differences."""
    initial = State(t=0.0, x=[1.0], v=[-0.4])
    h = 1e-5
    for t in (0.2, 1.1, 2.9):
        before, at, after = (
            harmonic_motion(initial, MASS, K, time) for time in (t - h, t, t + h)
        )
        dx_dt = (after.x[0] - before.x[0]) / (2 * h)
        dv_dt = (after.v[0] - before.v[0]) / (2 * h)
        np.testing.assert_allclose(dx_dt, at.v[0], rtol=0, atol=1e-7)
        np.testing.assert_allclose(dv_dt, -K / MASS * at.x[0], rtol=0, atol=1e-7)


def test_energy_is_kinetic_plus_potential_and_conserved_by_the_exact_motion():
    initial = State(t=0.0, x=[1.0, 0.0], v=[0.0, 3.0])

    exact = harmonic_motion(initial, MASS, K, np.linspace(0.0, 7.0, 50))
    energies = energy(exact, MASS, K)

    # At the start: m v² / 2 + k x² / 2 = 0.5 * 0.5 * 9 + 0.5 * 2 * 1.
    assert energies[0] == pytest.approx(3.25)
    np.testing.assert_allclose(energies, 3.25, rtol=1e-12)


@pytest.mark.parametrize("dt", [0.01, 0.1, 0.5, 2.0])
def test_explicit_euler_multiplies_the_energy_by_the_same_factor_every_step(dt):
    """The claim lesson M4 demonstrates and the formal proofs strand proves:
    E_{n+1} = (1 + omega² dt²) E_n, exactly, whatever the state and however
    large the step."""
    initial = State(t=0.0, x=[0.7, -0.2], v=[-1.5, 0.4])

    simulated = simulate(initial, newton(MASS, spring(K)), dt, n_steps=50)
    energies = energy(simulated, MASS, K)

    factor = euler_energy_growth(MASS, K, dt)
    assert factor == pytest.approx(1.0 + OMEGA**2 * dt**2)
    np.testing.assert_allclose(energies[1:] / energies[:-1], factor, rtol=1e-12)


def test_explicit_euler_rotates_the_state_by_arctan_and_scales_it_every_step():
    """The closed form of the method's iterates: in the scaled phase plane
    (omega x, v), one step is a rotation by arctan(omega dt) and a stretch
    by sqrt(1 + omega² dt²)."""
    dt = 0.3
    initial = State(t=0.0, x=[1.0], v=[0.0])

    simulated = simulate(initial, newton(MASS, spring(K)), dt, n_steps=40)

    n = np.arange(41)
    radius = np.sqrt(1 + OMEGA**2 * dt**2) ** n
    angle = n * np.arctan(OMEGA * dt)
    np.testing.assert_allclose(simulated.x[:, 0], radius * np.cos(angle))
    np.testing.assert_allclose(simulated.v[:, 0], -OMEGA * radius * np.sin(angle))


def test_euler_energy_growth_rejects_a_step_that_is_not_positive():
    with pytest.raises(ValueError, match="dt"):
        euler_energy_growth(MASS, K, 0.0)
