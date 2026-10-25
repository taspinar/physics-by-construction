import numpy as np
import pytest

from pbc.mechanics.bifurcation import (
    critical_rotation,
    final_amplitude,
    hoop,
    hoop_equilibrium,
    hoop_linear_rate,
    limit_cycle_amplitude,
    self_excited,
)
from pbc.mechanics.dynamics import State, simulate
from pbc.mechanics.integrators import rk4_step

# The hoop of lesson M14.
G, RADIUS, GAMMA = 9.81, 0.25, 2.0
OMEGA_C = critical_rotation(G, RADIUS)


def test_the_critical_rate_is_the_root_of_g_over_r():
    assert pytest.approx(np.sqrt(9.81 / 0.25)) == OMEGA_C


def test_the_tilted_equilibria_are_where_the_acceleration_vanishes():
    omegas = np.array([1.2, 1.5, 3.0]) * OMEGA_C
    theta = hoop_equilibrium(G, RADIUS, omegas)
    assert np.all(theta > 0)
    acceleration = hoop(G, RADIUS, omegas, GAMMA)
    for sign in (1.0, -1.0):
        at_rest = acceleration(0.0, sign * theta, np.zeros(3))
        assert at_rest == pytest.approx(np.zeros(3), abs=1e-12)
    # Below the threshold the only stable equilibrium is the bottom.
    assert hoop_equilibrium(G, RADIUS, [0.5 * OMEGA_C, OMEGA_C]) == pytest.approx(
        [0, 0]
    )


@pytest.mark.parametrize("ratio", [0.6, 0.97, 0.99, 1.2, 2.0])
def test_the_linear_rate_is_the_slow_eigenvalue_of_the_jacobian(ratio):
    # The Jacobian of (theta, theta') at the stable equilibrium by central
    # differences of the acceleration, independent of the closed form.
    omega = ratio * OMEGA_C
    acceleration = hoop(G, RADIUS, omega, GAMMA)
    theta = float(hoop_equilibrium(G, RADIUS, omega))
    h = 1e-6
    stiffness = -(
        acceleration(0.0, np.array([theta + h]), np.zeros(1))[0]
        - acceleration(0.0, np.array([theta - h]), np.zeros(1))[0]
    ) / (2 * h)
    eigenvalues = np.linalg.eigvals(np.array([[0.0, 1.0], [-stiffness, -2 * GAMMA]]))
    slowest = -np.max(eigenvalues.real)
    assert float(hoop_linear_rate(G, RADIUS, omega, GAMMA)) == pytest.approx(
        slowest, rel=1e-6
    )


def test_the_bead_settles_on_the_branch_of_its_side():
    omegas = np.array([0.8, 1.3, 1.3]) * OMEGA_C
    start = State(t=0.0, x=[0.3, 0.3, -0.3], v=[0.0, 0.0, 0.0])
    run = simulate(start, hoop(G, RADIUS, omegas, GAMMA), 0.005, 8000, step=rk4_step)
    expected = hoop_equilibrium(G, RADIUS, omegas) * np.array([1.0, 1.0, -1.0])
    assert run.x[-1] == pytest.approx(expected, abs=1e-9)


def test_at_the_threshold_the_angle_decays_as_the_cubic_term_predicts():
    # Once the fast motion has died, 1 / theta² grows at Omega_c² / (2 gamma).
    start = State(t=0.0, x=[0.3], v=[0.0])
    run = simulate(start, hoop(G, RADIUS, OMEGA_C, GAMMA), 0.005, 24000, step=rk4_step)
    late = run.t >= 60.0
    slope = np.polyfit(run.t[late], run.x[late, 0] ** -2.0, 1)[0]
    assert slope == pytest.approx(OMEGA_C**2 / (2 * GAMMA), rel=1e-2)


def test_the_limit_cycle_has_the_averaged_amplitude_and_balances_its_power():
    mus = np.array([-0.1, 0.05, 0.1])
    start = State(t=0.0, x=[1.0, 1.0, 1.0], v=[0.0, 0.0, 0.0])
    run = simulate(start, self_excited(mus), 0.02, 15000, step=rk4_step)
    amplitude = final_amplitude(run, 4 * np.pi)
    assert amplitude[0] < 1e-6
    assert amplitude[1:] == pytest.approx(limit_cycle_amplitude(mus[1:]), rel=1e-3)
    # On the cycle the power (mu - x²) v² fed in and taken out averages to
    # zero over whole periods.
    late = run.t >= run.t[-1] - 4 * np.pi
    x, v = run.x[late, 2], run.v[late, 2]
    power = (mus[2] - x**2) * v**2
    assert abs(np.mean(power)) < 1e-3 * np.mean(np.abs(power))


def test_the_averaged_amplitude_is_zero_below_the_threshold():
    assert limit_cycle_amplitude([-0.5, 0.0, 0.25]) == pytest.approx([0.0, 0.0, 1.0])


def test_bad_parameters_are_rejected():
    with pytest.raises(ValueError):
        hoop(G, -1.0, 1.0, GAMMA)
    with pytest.raises(ValueError):
        hoop(G, RADIUS, 1.0, -0.1)
