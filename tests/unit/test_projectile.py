import numpy as np
import pytest

from pbc.mechanics.drag import quadratic_drag
from pbc.mechanics.dynamics import State, Trajectory, euler_step, newton, weight
from pbc.mechanics.projectile import (
    STANDARD_GRAVITY,
    drag_free_range,
    fly,
    landing,
    launch,
    projectile_range,
)

# A tennis ball, as in lesson M3: mass in kg, drag constant in kg/m.
MASS = 0.058
DRAG = 1.06e-3
SPEED = 25.0  # m/s, close to its terminal speed of 23 m/s


def test_launch_resolves_the_speed_along_the_angle():
    state = launch(10.0, 30.0, height=1.5)

    assert state.t == 0.0
    np.testing.assert_allclose(state.x, [0.0, 1.5])
    np.testing.assert_allclose(state.v, [10.0 * np.cos(np.pi / 6), 5.0])


def test_launch_rejects_a_negative_speed():
    with pytest.raises(ValueError, match="speed"):
        launch(-1.0, 45.0)


def _acceleration(drag: float):
    return newton(MASS, weight(MASS, [0.0, -STANDARD_GRAVITY]), quadratic_drag(drag))


def test_flight_ends_with_the_first_state_below_the_ground():
    flight = fly(launch(SPEED, 45.0), _acceleration(DRAG), dt=0.01)

    heights = flight.x[:, 1]
    assert heights[-1] < 0 <= heights[-2]
    assert np.all(heights[:-1] >= 0)


def test_flight_that_does_not_land_in_time_is_reported():
    with pytest.raises(RuntimeError, match="not landed"):
        fly(launch(SPEED, 45.0), _acceleration(DRAG), dt=0.01, max_steps=10)


def test_landing_interpolates_the_crossing_within_the_last_step():
    trajectory = Trajectory(
        t=np.array([0.0, 1.0, 1.5]),
        x=np.array([[0.0, 2.0], [3.0, 1.0], [4.0, -3.0]]),
        v=np.zeros((3, 2)),
    )

    met = landing(trajectory)

    # The height goes from 1 to -3 in the last step: a quarter of the way.
    assert met.t == pytest.approx(1.125)
    assert met.x == pytest.approx(3.25)


def test_landing_needs_a_trajectory_that_has_just_crossed_the_ground():
    still_flying = Trajectory(
        t=np.array([0.0, 1.0]), x=np.array([[0.0, 1.0], [3.0, 2.0]]), v=np.zeros((2, 2))
    )

    with pytest.raises(ValueError, match="below the ground"):
        landing(still_flying)


def test_drag_free_range_is_the_closed_form():
    assert drag_free_range(10.0, 45.0, g=10.0) == pytest.approx(10.0)
    assert drag_free_range(10.0, 30.0, g=10.0) == pytest.approx(5 * np.sqrt(3))


def test_without_drag_the_simulated_range_tends_to_the_closed_form():
    """Validation by the drag-free limit, with an explicit tolerance.

    Lesson M1 showed that explicit Euler lands a drag-free projectile dt
    later than the exact motion, so the range is long by about v_x dt; the
    interpolation of the landing adds at most g dt² v_x / (8 v_y).
    """
    angle, dt = 40.0, 1e-4
    v_x, v_y = launch(SPEED, angle).v

    simulated = projectile_range(SPEED, angle, MASS, drag=0.0, dt=dt)

    exact = drag_free_range(SPEED, angle)
    assert simulated == pytest.approx(exact, abs=5e-3)  # m, of 63 m
    assert simulated - exact == pytest.approx(
        v_x * dt, abs=STANDARD_GRAVITY * dt**2 * v_x / (8 * v_y) + 1e-9
    )


def test_with_drag_the_range_converges_at_first_order_under_refinement():
    """Validation by convergence: there is no closed form, so the computed
    range must settle as the step shrinks, and for explicit Euler the
    differences between successive refinements must halve."""
    steps = [0.02 / 2**k for k in range(5)]
    ranges = np.array([projectile_range(SPEED, 45.0, MASS, DRAG, dt) for dt in steps])

    differences = np.abs(np.diff(ranges))
    orders = np.log2(differences[:-1] / differences[1:])
    np.testing.assert_allclose(orders, 1.0, rtol=0, atol=0.05)
    # Richardson extrapolation from any two successive steps agrees on the
    # limit to within a centimetre.
    limits = 2 * ranges[1:] - ranges[:-1]
    assert np.ptp(limits) < 1e-2
    assert differences[-1] < 2e-2


def test_drag_shortens_the_range_and_lowers_the_best_angle():
    """The two claims the lesson makes about the physics."""
    with_drag = {
        angle: projectile_range(SPEED, angle, MASS, DRAG, 1e-3) for angle in (40, 45)
    }
    without = {
        angle: projectile_range(SPEED, angle, MASS, 0.0, 1e-3) for angle in (40, 45)
    }

    assert with_drag[45] < 2 * without[45] / 3  # shorter by more than a third
    assert without[45] > without[40]
    assert with_drag[40] > with_drag[45]


def test_launching_from_a_height_lengthens_the_flight():
    from_ground = projectile_range(SPEED, 45.0, MASS, DRAG, 1e-3)
    from_height = projectile_range(SPEED, 45.0, MASS, DRAG, 1e-3, height=2.0)

    assert from_height > from_ground


def test_another_stepper_is_used_when_given():
    calls = []

    def counting_step(state: State, acceleration, dt: float) -> State:
        calls.append(state.t)
        return euler_step(state, acceleration, dt)

    projectile_range(SPEED, 45.0, MASS, DRAG, 0.05, step=counting_step)

    assert calls and calls[0] == 0.0
