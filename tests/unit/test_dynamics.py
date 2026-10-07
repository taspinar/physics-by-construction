import numpy as np
import pytest

from pbc.mechanics import kinematics
from pbc.mechanics.dynamics import (
    Acceleration,
    State,
    euler_step,
    newton,
    simulate,
    weight,
)

G = 9.81


def free_fall(t: float, x: np.ndarray, v: np.ndarray) -> np.ndarray:
    return np.array([0.0, -G])


def test_state_holds_position_and_velocity_as_vectors():
    plane = State(t=0.0, x=[1.0, 2.0], v=[3.0, 4.0])
    line = State(t=0.0, x=1.0, v=3.0)

    assert plane.x.shape == (2,) and plane.v.tolist() == [3.0, 4.0]
    assert line.x.shape == (1,) and line.v.tolist() == [3.0]


def test_state_rejects_position_and_velocity_of_different_lengths():
    with pytest.raises(ValueError, match="same length"):
        State(t=0.0, x=[1.0, 2.0], v=[3.0])


def test_one_step_uses_the_rates_at_the_start_of_the_step():
    def acceleration(t: float, x: np.ndarray, v: np.ndarray) -> np.ndarray:
        return 10.0 * t * x  # depends on time and position

    state = euler_step(State(t=1.0, x=[2.0, 0.5], v=[3.0, -1.0]), acceleration, 0.5)

    assert state.t == 1.5
    # x moves with the old velocity, v changes with a(1, x, v) = (20, 5).
    np.testing.assert_allclose(state.x, [3.5, 0.0])
    np.testing.assert_allclose(state.v, [13.0, 1.5])


def test_newton_divides_the_sum_of_the_forces_by_the_mass():
    def spring(t: float, x: np.ndarray, v: np.ndarray) -> np.ndarray:
        return -4.0 * x

    acceleration = newton(2.0, weight(2.0, [0.0, -G]), spring)

    a = acceleration(0.0, np.array([1.0, 0.5]), np.array([0.0, 0.0]))
    np.testing.assert_allclose(a, [-2.0, -G - 1.0])


def test_newton_without_forces_gives_no_acceleration():
    a = newton(1.0)(0.0, np.array([1.0, 2.0]), np.array([3.0, 4.0]))

    assert a.tolist() == [0.0, 0.0]


@pytest.mark.parametrize("mass", [0.0, -1.0])
def test_newton_rejects_a_mass_that_is_not_positive(mass: float):
    with pytest.raises(ValueError, match="mass"):
        newton(mass)


def test_trajectory_holds_the_initial_state_and_one_state_per_step():
    initial = State(t=0.0, x=[0.0, 1.5], v=[4.0, 12.0])

    trajectory = simulate(initial, free_fall, dt=0.1, n_steps=20)

    assert trajectory.t.shape == (21,)
    assert trajectory.x.shape == trajectory.v.shape == (21, 2)
    np.testing.assert_allclose(trajectory.t, 0.1 * np.arange(21), rtol=0, atol=1e-12)
    np.testing.assert_allclose(trajectory.x[0], initial.x)
    np.testing.assert_allclose(trajectory.v[0], initial.v)
    # Nothing accelerates horizontally.
    np.testing.assert_allclose(trajectory.v[:, 0], 4.0)


def test_simulation_stops_after_the_first_state_that_meets_the_condition():
    initial = State(t=0.0, x=[0.0, 0.0], v=[1.0, 5.0])

    trajectory = simulate(
        initial, free_fall, dt=0.1, n_steps=1000, until=lambda state: state.x[1] < 0
    )

    assert trajectory.x[-1, 1] < 0 <= trajectory.x[-2, 1]
    assert len(trajectory.t) < 1001


def test_simulation_runs_every_step_when_the_condition_is_never_met():
    trajectory = simulate(
        State(t=0.0, x=[0.0], v=[1.0]),
        lambda t, x, v: np.zeros(1),
        dt=0.1,
        n_steps=5,
        until=lambda state: False,
    )

    assert len(trajectory.t) == 6


def test_another_stepper_with_the_same_signature_replaces_explicit_euler():
    """The stepping interface later lessons use for other integrators."""

    def midpoint_step(state: State, acceleration: Acceleration, dt: float) -> State:
        half = euler_step(state, acceleration, dt / 2)
        a = acceleration(half.t, half.x, half.v)
        return State(t=state.t + dt, x=state.x + half.v * dt, v=state.v + a * dt)

    initial = State(t=0.0, x=[0.0, 0.0], v=[3.0, 20.0])
    euler = simulate(initial, free_fall, dt=0.1, n_steps=20)
    midpoint = simulate(initial, free_fall, dt=0.1, n_steps=20, step=midpoint_step)

    exact_height = 20.0 * 2.0 - 0.5 * G * 2.0**2
    # Explicit Euler lags the height by g t dt / 2; the midpoint rule is
    # exact for a constant acceleration.
    assert euler.x[-1, 1] - exact_height == pytest.approx(G * 2.0 * 0.1 / 2)
    assert midpoint.x[-1, 1] == pytest.approx(exact_height, abs=1e-12)


def test_on_a_line_with_a_time_dependent_acceleration_it_is_the_first_lesson():
    """The general stepper reproduces the kinematics simulation of lesson M1
    when the acceleration depends on time alone."""
    one_dimensional = simulate(
        State(t=0.0, x=[1.5], v=[12.0]),
        lambda t, x, v: np.array([3.0 * np.cos(2.0 * t)]),
        dt=0.05,
        n_steps=40,
    )
    reference = kinematics.simulate(
        kinematics.State(t=0.0, x=1.5, v=12.0),
        lambda t: 3.0 * np.cos(2.0 * t),
        dt=0.05,
        n_steps=40,
    )

    np.testing.assert_allclose(one_dimensional.x[:, 0], reference.x, rtol=0, atol=1e-12)
    np.testing.assert_allclose(one_dimensional.v[:, 0], reference.v, rtol=0, atol=1e-12)


@pytest.mark.parametrize("dt", [0.0, -0.1])
def test_rejects_a_time_step_that_is_not_positive(dt: float):
    with pytest.raises(ValueError, match="dt"):
        simulate(State(t=0.0, x=[0.0], v=[0.0]), free_fall, dt=dt, n_steps=1)


def test_rejects_a_negative_number_of_steps():
    with pytest.raises(ValueError, match="n_steps"):
        simulate(State(t=0.0, x=[0.0], v=[0.0]), free_fall, dt=0.1, n_steps=-1)
