import numpy as np
import pytest

from pbc.mechanics.kinematics import (
    State,
    constant_acceleration,
    euler_step,
    simulate,
)

G = 9.81


def falling(t: float) -> float:
    return -G


def test_one_step_uses_the_rates_at_the_start_of_the_step():
    state = euler_step(State(t=1.0, x=2.0, v=3.0), lambda t: 10.0 * t, dt=0.5)

    # x moves with the old velocity, v changes with the acceleration at t = 1.
    assert state == State(t=1.5, x=3.5, v=8.0)


def test_trajectory_holds_the_initial_state_and_one_state_per_step():
    initial = State(t=0.0, x=1.5, v=12.0)

    trajectory = simulate(initial, falling, dt=0.1, n_steps=20)

    assert trajectory.t.shape == trajectory.x.shape == trajectory.v.shape == (21,)
    assert (trajectory.t[0], trajectory.x[0], trajectory.v[0]) == (0.0, 1.5, 12.0)
    np.testing.assert_allclose(trajectory.t, 0.1 * np.arange(21), rtol=0, atol=1e-12)


def test_zero_steps_return_only_the_initial_state():
    trajectory = simulate(State(t=0.0, x=1.0, v=2.0), falling, dt=0.1, n_steps=0)

    assert trajectory.x.tolist() == [1.0]


def test_closed_form_passes_through_the_initial_state():
    initial = State(t=2.0, x=5.0, v=-1.0)

    exact = constant_acceleration(initial, a=3.0, t=[2.0, 4.0])

    # After 2 s: x = 5 - 1 * 2 + 3 * 2**2 / 2 = 9, v = -1 + 3 * 2 = 5.
    np.testing.assert_allclose(exact.x, [5.0, 9.0], rtol=0, atol=1e-12)
    np.testing.assert_allclose(exact.v, [-1.0, 5.0], rtol=0, atol=1e-12)


def test_euler_matches_the_closed_form_within_its_known_error():
    """Validation against the closed-form solution.

    Under a constant acceleration a, explicit Euler reproduces the velocity
    exactly and lags the position by a * (t - t0) * dt / 2. The simulation
    must agree with the closed form up to that lag, to round-off.
    """
    initial = State(t=0.0, x=1.5, v=12.0)
    dt = 0.01

    trajectory = simulate(initial, falling, dt=dt, n_steps=240)
    exact = constant_acceleration(initial, a=-G, t=trajectory.t)

    np.testing.assert_allclose(trajectory.v, exact.v, rtol=0, atol=1e-11)
    lag = -G * trajectory.t * dt / 2
    np.testing.assert_allclose(trajectory.x, exact.x - lag, rtol=0, atol=1e-11)
    # The lag itself is small: the simulation is within 0.12 m of the exact
    # position everywhere, and the bound is tight.
    assert np.max(np.abs(trajectory.x - exact.x)) == pytest.approx(
        G * 2.4 * dt / 2, abs=1e-11
    )


def test_error_halves_when_the_time_step_halves():
    """First-order convergence under an acceleration that varies in time."""
    initial = State(t=0.0, x=0.0, v=0.0)
    duration = 1.0

    def error(n_steps: int) -> float:
        trajectory = simulate(initial, np.cos, dt=duration / n_steps, n_steps=n_steps)
        # a = cos(t) from rest at the origin gives x = 1 - cos(t).
        return abs(trajectory.x[-1] - (1.0 - np.cos(duration)))

    errors = np.array([error(n) for n in (100, 200, 400, 800)])
    orders = np.log2(errors[:-1] / errors[1:])

    np.testing.assert_allclose(orders, 1.0, rtol=0, atol=0.01)
    # The errors are not small by accident of a loose tolerance: the leading
    # term of the error is (2 sin T - T) * dt / 2.
    predicted = (2 * np.sin(duration) - duration) * (duration / 800) / 2
    assert errors[-1] == pytest.approx(predicted, rel=0.01)


@pytest.mark.parametrize("dt", [0.0, -0.1])
def test_rejects_a_time_step_that_is_not_positive(dt: float):
    with pytest.raises(ValueError, match="dt"):
        simulate(State(t=0.0, x=0.0, v=0.0), falling, dt=dt, n_steps=1)


def test_rejects_a_negative_number_of_steps():
    with pytest.raises(ValueError, match="n_steps"):
        simulate(State(t=0.0, x=0.0, v=0.0), falling, dt=0.1, n_steps=-1)
