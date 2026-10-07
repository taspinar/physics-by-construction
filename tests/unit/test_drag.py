import numpy as np
import pytest

from pbc.mechanics.drag import (
    drag_constant,
    fall_with_linear_drag,
    linear_drag,
    quadratic_drag,
)
from pbc.mechanics.dynamics import State, newton, simulate, weight

G = 9.81
# The falling particle of lesson M2: time constant tau = m / b = 2 s.
MASS = 0.5
B = 0.25
TAU = MASS / B


def test_linear_drag_is_proportional_to_the_velocity_and_against_it():
    force = linear_drag(0.25)(0.0, np.array([0.0, 0.0]), np.array([4.0, -2.0]))

    np.testing.assert_allclose(force, [-1.0, 0.5])


def test_quadratic_drag_grows_with_the_square_of_the_speed_and_points_against_it():
    force = quadratic_drag(0.5)(0.0, np.array([0.0, 0.0]), np.array([3.0, -4.0]))

    # |v| = 5, so |F| = 0.5 * 25 = 12.5 along -v / |v| = (-0.6, 0.8).
    np.testing.assert_allclose(force, [-7.5, 10.0])


def test_quadratic_drag_with_a_zero_constant_is_no_force():
    force = quadratic_drag(0.0)(0.0, np.array([0.0]), np.array([30.0]))

    assert force.tolist() == [0.0]


@pytest.mark.parametrize("model", [linear_drag, quadratic_drag])
def test_a_negative_drag_constant_is_rejected(model):
    with pytest.raises(ValueError, match="negative"):
        model(-0.1)


def test_drag_constant_is_half_the_density_times_the_coefficient_times_the_area():
    assert drag_constant(1.2, 0.5, 0.01) == pytest.approx(0.003)


def test_exact_fall_passes_through_the_initial_state_and_tends_to_terminal_velocity():
    initial = State(t=1.0, x=[2.0, 100.0], v=[5.0, 3.0])

    exact = fall_with_linear_drag(initial, MASS, B, [0.0, -G], [1.0, 1.0 + 50 * TAU])

    np.testing.assert_allclose(exact.x[0], initial.x)
    np.testing.assert_allclose(exact.v[0], initial.v)
    # Terminal velocity g tau: no horizontal motion left, falling at g tau.
    np.testing.assert_allclose(exact.v[1], [0.0, -G * TAU], rtol=0, atol=1e-12)


def test_exact_fall_satisfies_the_equation_of_motion():
    """dx/dt = v and m dv/dt = m g - b v, checked with central differences."""
    initial = State(t=0.0, x=[0.0, 0.0], v=[6.0, 10.0])
    g = np.array([0.0, -G])
    h = 1e-5
    for t in (0.3, 1.0, 4.0):
        before, at, after = (
            fall_with_linear_drag(initial, MASS, B, g, time)
            for time in (t - h, t, t + h)
        )
        dx_dt = (after.x[0] - before.x[0]) / (2 * h)
        dv_dt = (after.v[0] - before.v[0]) / (2 * h)
        np.testing.assert_allclose(dx_dt, at.v[0], rtol=0, atol=1e-7)
        np.testing.assert_allclose(dv_dt, g - at.v[0] / TAU, rtol=0, atol=1e-7)


@pytest.mark.parametrize("b", [0.0, -1.0])
def test_exact_fall_needs_drag(b: float):
    with pytest.raises(ValueError, match="drag constant"):
        fall_with_linear_drag(State(0.0, [0.0], [0.0]), MASS, b, [-G], [1.0])


def test_euler_matches_the_exact_fall_within_an_explicit_tolerance():
    """Validation of the M2 simulation against the analytic solution.

    From rest, over five time constants, with dt = tau / 2000. Explicit
    Euler's error is first order in dt; the tolerances are about 1.4 times
    the error observed when the test was written, so a method that does
    worse is reported.
    """
    initial = State(t=0.0, x=[0.0], v=[0.0])
    acceleration = newton(MASS, weight(MASS, [-G]), linear_drag(B))
    dt = TAU / 2000

    simulated = simulate(initial, acceleration, dt, n_steps=10_000)
    exact = fall_with_linear_drag(initial, MASS, B, [-G], simulated.t)

    assert np.max(np.abs(simulated.v - exact.v)) < 2.5e-3  # m/s, of 19.6 m/s
    assert np.max(np.abs(simulated.x - exact.x)) < 5.0e-3  # m, of 160 m
    # It does reach terminal velocity.
    assert simulated.v[-1, 0] == pytest.approx(-G * TAU, rel=1e-2)


def test_euler_relaxes_to_terminal_velocity_by_the_factor_one_minus_dt_over_tau():
    """What the lesson derives: the computed velocity is exactly
    v_T + (v_0 - v_T) (1 - dt / tau)^n, so the method is unstable for
    dt > 2 tau."""
    initial = State(t=0.0, x=[0.0], v=[4.0])
    acceleration = newton(MASS, weight(MASS, [-G]), linear_drag(B))
    terminal = -G * TAU

    for dt in (0.1, 1.5 * TAU, 2.5 * TAU):
        simulated = simulate(initial, acceleration, dt, n_steps=20)
        n = np.arange(21)
        predicted = terminal + (4.0 - terminal) * (1 - dt / TAU) ** n
        np.testing.assert_allclose(simulated.v[:, 0], predicted, rtol=1e-12, atol=0)
    # dt = 2.5 tau: the factor is -1.5, and the computed velocity grows.
    assert abs(simulated.v[-1, 0] - terminal) > 1e3 * abs(4.0 - terminal)


def test_euler_error_halves_when_the_time_step_halves_under_linear_drag():
    initial = State(t=0.0, x=[0.0, 0.0], v=[6.0, 10.0])
    acceleration = newton(MASS, weight(MASS, [0.0, -G]), linear_drag(B))
    duration = 2 * TAU

    def error(n_steps: int) -> float:
        simulated = simulate(initial, acceleration, duration / n_steps, n_steps)
        exact = fall_with_linear_drag(initial, MASS, B, [0.0, -G], simulated.t[-1])
        return float(np.max(np.abs(simulated.x[-1] - exact.x[0])))

    errors = np.array([error(n) for n in (200, 400, 800, 1600)])
    orders = np.log2(errors[:-1] / errors[1:])

    np.testing.assert_allclose(orders, 1.0, rtol=0, atol=0.02)


def test_a_long_fall_under_quadratic_drag_reaches_the_terminal_speed():
    """The limiting case that validates the quadratic drag model: the speed
    tends to sqrt(m g / c)."""
    mass, c = 0.058, 1.06e-3  # a tennis ball, as in lesson M3
    terminal_speed = np.sqrt(mass * G / c)
    time_scale = terminal_speed / G
    acceleration = newton(mass, weight(mass, [-G]), quadratic_drag(c))

    fall = simulate(
        State(0.0, [0.0], [0.0]), acceleration, 1e-3, int(12 * time_scale / 1e-3)
    )

    speeds = -fall.v[:, 0]
    assert np.all(np.diff(speeds) > 0)  # it only speeds up
    assert speeds[-1] < terminal_speed
    assert speeds[-1] == pytest.approx(terminal_speed, rel=1e-4)
