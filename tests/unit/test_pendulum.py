import numpy as np
import pytest
from scipy.constants import g

from pbc.mechanics.dynamics import State, Trajectory, euler_step, newton, simulate
from pbc.mechanics.energy import energy_drift, mechanical_energy
from pbc.mechanics.integrators import rk4_step, verlet_step
from pbc.mechanics.oscillator import harmonic_motion, spring
from pbc.mechanics.pendulum import (
    pendulum_force,
    pendulum_period,
    pendulum_potential,
    small_angle_period,
)

# The pendulum of lesson M6: one kilogram on a one-metre rod.
MASS = 1.0
LENGTH = 1.0
PENDULUM = newton(MASS, pendulum_force(MASS, LENGTH))
POTENTIAL = pendulum_potential(MASS, LENGTH)
T0 = small_angle_period(LENGTH)


def released_at(degrees: float) -> State:
    return State(t=0.0, x=[LENGTH * np.radians(degrees)], v=[0.0])


def upward_crossings(trajectory: Trajectory) -> np.ndarray:
    """The times at which the bob passes the bottom moving in the positive
    direction, interpolated linearly within the step."""
    s, t = trajectory.x[:, 0], trajectory.t
    before = np.where((s[:-1] < 0) & (s[1:] >= 0))[0]
    fraction = -s[before] / (s[before + 1] - s[before])
    return t[before] + fraction * (t[before + 1] - t[before])


def test_the_force_along_the_arc_is_the_tangential_weight():
    force = pendulum_force(MASS, LENGTH)
    quarter = np.array([LENGTH * np.pi / 2])  # the rod horizontal

    np.testing.assert_allclose(force(0.0, quarter, np.zeros(1)), [-MASS * g])
    np.testing.assert_allclose(force(0.0, -quarter, np.zeros(1)), [MASS * g])
    assert force(0.0, np.zeros(1), np.zeros(1)) == pytest.approx(0.0)


def test_for_small_angles_the_pendulum_is_the_harmonic_oscillator_of_m4():
    """The small-angle limit: the force is Hooke's law with k = m g / L to
    third order in the angle, and the motion at one degree follows the
    exact harmonic motion."""
    k = MASS * g / LENGTH
    s = np.array([0.01 * LENGTH])
    difference = pendulum_force(MASS, LENGTH)(0.0, s, np.zeros(1)) - spring(k)(
        0.0, s, np.zeros(1)
    )
    assert abs(difference[0]) < k * 0.01**3 * LENGTH

    initial = released_at(1.0)
    simulated = simulate(initial, PENDULUM, T0 / 400, 800, step=rk4_step)
    exact = harmonic_motion(initial, MASS, k, simulated.t)
    # What remains is the physics: the period is longer than the oscillator's
    # by theta² / 16, a phase lag of a few millionths of the amplitude.
    np.testing.assert_allclose(simulated.x, exact.x, rtol=0, atol=5e-6 * LENGTH)


def test_the_potential_is_the_height_times_the_weight():
    assert POTENTIAL(np.zeros(1)) == 0.0
    assert POTENTIAL(np.array([LENGTH * np.pi / 2])) == pytest.approx(MASS * g * LENGTH)
    assert POTENTIAL(np.array([LENGTH * np.pi])) == pytest.approx(2 * MASS * g * LENGTH)


def test_the_exact_period_starts_at_the_small_angle_one_and_grows_with_the_amplitude():
    assert pendulum_period(LENGTH, 0.0) == pytest.approx(T0)
    assert pytest.approx(2 * np.pi * np.sqrt(LENGTH / g)) == T0
    # The first correction: T = T0 (1 + theta² / 16 + ...).
    small = np.radians(5.0)
    assert pendulum_period(LENGTH, small) / T0 - 1 == pytest.approx(
        small**2 / 16, rel=1e-2
    )
    # The classical value at a right angle.
    assert pendulum_period(LENGTH, np.pi / 2) / T0 == pytest.approx(1.18034, abs=1e-5)
    periods = [pendulum_period(LENGTH, np.radians(d)) for d in (30, 90, 150, 179)]
    assert periods == sorted(periods) and periods[-1] > 3 * T0


def test_the_simulated_period_at_large_amplitude_matches_the_elliptic_integral():
    """The force model and the period formula agree: Runge-Kutta 4 at a fine
    step reproduces the exact period at 90 degrees within a stated bound."""
    exact = pendulum_period(LENGTH, np.pi / 2)
    simulated = simulate(
        released_at(90.0),
        PENDULUM,
        T0 / 400,
        round(4 * exact / T0 * 400),
        step=rk4_step,
    )

    measured = np.diff(upward_crossings(simulated))
    assert len(measured) == 3
    np.testing.assert_allclose(measured, exact, rtol=1e-6)


def test_velocity_verlet_keeps_the_energy_in_a_band_and_explicit_euler_does_not():
    """The diagnostic of lesson M6 on a force with no closed-form motion:
    over 40 periods at 100 steps per small-angle period the drift of the
    symplectic method is bounded and does not grow with the run, while
    explicit Euler's exceeds the initial energy."""
    exact = pendulum_period(LENGTH, np.pi / 2)
    n_steps = round(40 * exact / T0 * 100)
    verlet = simulate(released_at(90.0), PENDULUM, T0 / 100, n_steps, step=verlet_step)
    euler = simulate(released_at(90.0), PENDULUM, T0 / 100, n_steps, step=euler_step)

    energies = mechanical_energy(verlet, MASS, POTENTIAL)
    assert energy_drift(energies) < 1e-3
    assert energy_drift(energies) <= 1.01 * energy_drift(energies[: n_steps // 2])
    assert energy_drift(mechanical_energy(euler, MASS, POTENTIAL)) > 1.0


def test_explicit_euler_sends_a_pendulum_over_the_top_that_the_physics_keeps_swinging():
    """Released near the top, the pendulum has less than 2 m g L and swings
    back and forth forever; explicit Euler feeds it energy until it rotates."""
    initial = released_at(170.0)
    assert POTENTIAL(initial.x) < 2 * MASS * g * LENGTH
    n_steps = round(3 * pendulum_period(LENGTH, np.radians(170.0)) / T0 * 200)

    verlet = simulate(initial, PENDULUM, T0 / 200, n_steps, step=verlet_step)
    euler = simulate(initial, PENDULUM, T0 / 200, n_steps, step=euler_step)

    assert np.max(np.abs(verlet.x)) <= initial.x[0] * (1 + 1e-9)
    assert np.max(np.abs(euler.x)) > LENGTH * np.pi
    assert np.max(mechanical_energy(euler, MASS, POTENTIAL)) > 2 * MASS * g * LENGTH


@pytest.mark.parametrize(
    ("mass", "length", "gravity", "message"),
    [(0.0, 1.0, g, "mass"), (1.0, -1.0, g, "length"), (1.0, 1.0, 0.0, "g")],
)
def test_arguments_that_are_not_positive_are_rejected(mass, length, gravity, message):
    with pytest.raises(ValueError, match=message):
        pendulum_force(mass, length, gravity)
    with pytest.raises(ValueError, match=message):
        pendulum_potential(mass, length, gravity)


def test_the_period_is_defined_for_amplitudes_below_the_top_only():
    with pytest.raises(ValueError, match="amplitude"):
        pendulum_period(LENGTH, np.pi)
    with pytest.raises(ValueError, match="amplitude"):
        pendulum_period(LENGTH, -0.1)
