import numpy as np
import pytest

from pbc.mechanics.dynamics import State, Trajectory, newton, simulate
from pbc.mechanics.energy import (
    energy_drift,
    kinetic_energy,
    mechanical_energy,
    potential_energy,
)
from pbc.mechanics.oscillator import (
    energy,
    euler_energy_growth,
    harmonic_motion,
    spring,
)

# The oscillator of lesson M4: omega = 2 rad/s.
MASS = 0.5
K = 2.0


def spring_potential(x):
    return 0.5 * K * float(x @ x)


def test_kinetic_plus_potential_is_the_energy_of_the_oscillator_lesson():
    """The general energy with the spring potential agrees with the
    special-purpose energy of lesson M4 on the same trajectory."""
    initial = State(t=0.0, x=[1.0, 0.0], v=[0.0, 3.0])
    exact = harmonic_motion(initial, MASS, K, np.linspace(0.0, 5.0, 40))

    np.testing.assert_allclose(
        mechanical_energy(exact, MASS, spring_potential), energy(exact, MASS, K)
    )
    np.testing.assert_allclose(kinetic_energy(exact, MASS)[0], 0.5 * MASS * 9.0)
    np.testing.assert_allclose(potential_energy(exact, spring_potential)[0], 0.5 * K)


def test_the_exact_motion_has_no_drift_and_explicit_euler_has_the_derived_one():
    initial = State(t=0.0, x=[1.0], v=[0.0])
    dt, n_steps = 0.05, 100
    exact = harmonic_motion(initial, MASS, K, dt * np.arange(n_steps + 1))
    simulated = simulate(initial, newton(MASS, spring(K)), dt, n_steps)

    assert energy_drift(mechanical_energy(exact, MASS, spring_potential)) < 1e-14
    drift = energy_drift(mechanical_energy(simulated, MASS, spring_potential))
    assert drift == pytest.approx(euler_energy_growth(MASS, K, dt) ** n_steps - 1)


def test_drift_is_measured_against_the_size_of_a_negative_initial_energy():
    # A bound orbit has a negative energy; a change of 0.5 on -2 is a quarter.
    assert energy_drift(np.array([-2.0, -1.5, -2.0])) == pytest.approx(0.25)
    with pytest.raises(ValueError, match="zero"):
        energy_drift(np.array([0.0, 1.0]))


def test_kinetic_energy_rejects_a_mass_that_is_not_positive():
    trajectory = Trajectory(t=np.zeros(1), x=np.zeros((1, 1)), v=np.ones((1, 1)))
    with pytest.raises(ValueError, match="mass"):
        kinetic_energy(trajectory, 0.0)
