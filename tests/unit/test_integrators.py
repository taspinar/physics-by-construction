import numpy as np
import pytest

from pbc.mechanics.drag import fall_with_linear_drag, linear_drag
from pbc.mechanics.dynamics import State, euler_step, newton, simulate, weight
from pbc.mechanics.integrators import (
    INTEGRATORS,
    Integrator,
    rk4_step,
    symplectic_euler_step,
    verlet_step,
)
from pbc.mechanics.oscillator import energy, harmonic_motion, spring

# The oscillator of lessons M4 and M5: omega = 2 rad/s, period pi s.
MASS = 0.5
K = 2.0
OMEGA = 2.0
PERIOD = np.pi
OSCILLATOR = newton(MASS, spring(K))
RELEASED = State(t=0.0, x=[1.0], v=[0.0])


def _state_error(simulated, exact) -> float:
    """The largest distance in the scaled phase plane (omega x, v) between
    the simulated states and the exact ones. The error at one instant would
    mislead: a position error misses a phase error at a turning point, and
    the first-order part of symplectic Euler's error is periodic and
    vanishes at whole periods."""
    dx = OMEGA * (simulated.x - exact.x)
    dv = simulated.v - exact.v
    return float(np.max(np.sqrt(np.sum(dx**2 + dv**2, axis=1))))


def _observed_orders(step, steps_per_period: list[int], periods: float):
    errors = []
    for n in steps_per_period:
        n_steps = round(periods * n)
        simulated = simulate(RELEASED, OSCILLATOR, PERIOD / n, n_steps, step=step)
        exact = harmonic_motion(RELEASED, MASS, K, simulated.t)
        errors.append(_state_error(simulated, exact))
    errors = np.array(errors)
    return np.log2(errors[:-1] / errors[1:])


def test_the_four_integrators_are_listed_in_the_order_of_the_course():
    assert [integrator.name for integrator in INTEGRATORS] == [
        "explicit Euler",
        "symplectic Euler",
        "velocity Verlet",
        "Runge-Kutta 4",
    ]
    assert INTEGRATORS[0].step is euler_step
    assert all(isinstance(integrator, Integrator) for integrator in INTEGRATORS)


@pytest.mark.parametrize("integrator", INTEGRATORS[1:], ids=lambda i: i.name)
def test_the_higher_order_integrators_show_their_order_on_the_oscillator(
    integrator: Integrator,
):
    """Acceptance criterion 2: the empirical order of accuracy. Over two
    periods, halving the step divides the error by 2 ** order."""
    orders = _observed_orders(integrator.step, [50, 100, 200, 400, 800], periods=2)

    np.testing.assert_allclose(orders, integrator.order, rtol=0, atol=0.1)


def test_explicit_euler_shows_first_order_once_the_step_is_small_enough():
    """Explicit Euler's error on an oscillator grows exponentially in
    omega² dt T, so its first-order regime needs omega² dt T well below 1.
    Over one period that takes thousands of steps."""
    orders = _observed_orders(euler_step, [1000, 2000, 4000, 8000], periods=1)

    np.testing.assert_allclose(orders, 1.0, rtol=0, atol=0.05)


@pytest.mark.parametrize("integrator", INTEGRATORS, ids=lambda i: i.name)
def test_each_integrator_evaluates_the_acceleration_as_often_as_it_says(
    integrator: Integrator,
):
    calls = []

    def counted(t, x, v):
        calls.append(t)
        return OSCILLATOR(t, x, v)

    simulate(RELEASED, counted, 0.1, n_steps=7, step=integrator.step)

    assert len(calls) == 7 * integrator.evaluations


def test_symplectic_euler_conserves_a_modified_energy_exactly():
    """What keeps its energy bounded: it conserves
    m (v² + omega² x² - omega² dt x v) / 2 to round-off, at every step."""
    dt = 0.3
    simulated = simulate(RELEASED, OSCILLATOR, dt, 300, step=symplectic_euler_step)

    x, v = simulated.x[:, 0], simulated.v[:, 0]
    modified = 0.5 * MASS * (v**2 + OMEGA**2 * x**2 - OMEGA**2 * dt * x * v)
    np.testing.assert_allclose(modified, modified[0], rtol=1e-12)
    # The true energy is not conserved: it oscillates, by about omega dt.
    energies = energy(simulated, MASS, K)
    assert 0.1 < np.ptp(energies) / energies[0] < 1.0


def test_velocity_verlet_conserves_a_modified_energy_exactly():
    """It conserves m (v² + omega² (1 - omega² dt² / 4) x²) / 2 to round-off."""
    dt = 0.3
    simulated = simulate(RELEASED, OSCILLATOR, dt, 300, step=verlet_step)

    x, v = simulated.x[:, 0], simulated.v[:, 0]
    modified = 0.5 * MASS * (v**2 + OMEGA**2 * (1 - OMEGA**2 * dt**2 / 4) * x**2)
    np.testing.assert_allclose(modified, modified[0], rtol=1e-12)
    energies = energy(simulated, MASS, K)
    assert 0.01 < np.ptp(energies) / energies[0] < 0.2


def test_runge_kutta_4_multiplies_the_energy_by_the_same_factor_every_step():
    """With z = omega dt, each step multiplies the energy by
    1 - z⁶ / 72 + z⁸ / 576: a slow, steady loss."""
    dt = 0.5
    simulated = simulate(RELEASED, OSCILLATOR, dt, 100, step=rk4_step)

    energies = energy(simulated, MASS, K)
    z = OMEGA * dt
    factor = 1 - z**6 / 72 + z**8 / 576
    assert factor < 1
    np.testing.assert_allclose(energies[1:] / energies[:-1], factor, rtol=1e-12)


def _energy_after(step, omega_dt: float, n_steps: int = 200) -> float:
    simulated = simulate(RELEASED, OSCILLATOR, omega_dt / OMEGA, n_steps, step=step)
    energies = energy(simulated, MASS, K)
    return float(energies[-1] / energies[0])


def test_the_stability_limits_of_the_integrators():
    """Symplectic Euler and velocity Verlet are stable for omega dt < 2,
    Runge-Kutta 4 for omega dt < 2 sqrt(2); explicit Euler never is."""
    for step in (symplectic_euler_step, verlet_step):
        assert _energy_after(step, 1.9) < 100
        assert _energy_after(step, 2.1) > 1e20
    assert _energy_after(rk4_step, 2.7) < 1
    assert _energy_after(rk4_step, 2.9) > 1e20
    assert _energy_after(euler_step, 0.1) > 1 + 0.1**2 * 199


def test_verlet_and_runge_kutta_keep_their_order_with_a_velocity_dependent_force():
    """The fall with linear drag of lesson M2 has an exact solution; the
    predicted velocity in the Verlet step and the staged velocities of
    Runge-Kutta 4 keep both methods at their order on it."""
    mass, b = 0.5, 0.25
    initial = State(t=0.0, x=[0.0, 0.0], v=[6.0, 10.0])
    acceleration = newton(mass, weight(mass, [0.0, -9.81]), linear_drag(b))
    duration = 4.0

    for integrator in INTEGRATORS[2:]:
        errors = []
        for n_steps in (50, 100, 200, 400):
            simulated = simulate(
                initial, acceleration, duration / n_steps, n_steps, step=integrator.step
            )
            exact = fall_with_linear_drag(initial, mass, b, [0.0, -9.81], duration)
            errors.append(np.max(np.abs(simulated.x[-1] - exact.x[0])))
        errors = np.array(errors)
        orders = np.log2(errors[:-1] / errors[1:])
        np.testing.assert_allclose(orders, integrator.order, rtol=0, atol=0.1)
