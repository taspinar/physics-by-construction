import numpy as np
import pytest

from pbc.mechanics.dynamics import State, simulate
from pbc.mechanics.integrators import symplectic_euler_step, verlet_step
from pbc.mechanics.nbody import (
    angular_momentum,
    barycentric,
    gravity,
    potential_energy,
    total_energy,
)
from pbc.mechanics.orbit import gravitational_attraction, kepler_motion
from pbc.mechanics.particles import interacting, stack, unstack
from pbc.verification.estimates import fitted_order

G = 4 * np.pi**2  # AU³ / (M_sun yr²)


def test_the_acceleration_is_the_sum_of_the_pair_forces():
    # Against the loop over pairs of pbc.mechanics.particles, one pair law
    # per pair of masses, for four bodies in general position.
    masses = [1.0, 0.3, 2.0, 0.05]
    x = stack([[0.1, -0.2], [1.3, 0.4], [-0.7, 1.1], [0.5, -1.6]])
    found = gravity(1.7, masses)(0.0, x, np.zeros_like(x))
    positions = unstack(x, 4)
    expected = np.zeros_like(positions)
    for i in range(4):
        for j in range(4):
            if i != j:
                pair = gravitational_attraction(1.7, masses[i], masses[j])
                expected[i] += pair(positions[i] - positions[j]) / masses[i]
    assert found == pytest.approx(expected.reshape(-1), rel=1e-13)


def test_two_bodies_agree_with_the_pairwise_interface_for_equal_masses():
    masses = [1.0, 1.0]
    x = stack([[0.0, 0.0], [2.0, 0.0]])
    pairwise = interacting(masses, gravitational_attraction(G, 1.0, 1.0))
    assert gravity(G, masses)(0.0, x, x) == pytest.approx(pairwise(0.0, x, x))


def test_the_potential_energy_is_minus_g_m_m_over_r_summed_over_pairs():
    positions = [[0.0, 0.0], [3.0, 4.0], [0.0, 4.0]]
    masses = [2.0, 1.0, 1.0]
    expected = -(2.0 * 1.0 / 5.0 + 2.0 * 1.0 / 4.0 + 1.0 * 1.0 / 3.0)
    assert potential_energy(1.0, masses, positions) == pytest.approx(expected)


def test_the_barycentric_frame_has_its_centre_of_mass_at_rest_at_the_origin():
    masses = [1.0, 0.5]
    state = barycentric(masses, [[1.0, 2.0], [4.0, -1.0]], [[0.3, 0.0], [0.0, 2.0]])
    x, v = unstack(state.x, 2), unstack(state.v, 2)
    assert masses @ x == pytest.approx([0.0, 0.0], abs=1e-15)
    assert masses @ v == pytest.approx([0.0, 0.0], abs=1e-15)


def test_two_bodies_follow_the_exact_kepler_motion_with_order_two():
    masses = [1.0, 1.0e-3]
    gm = G * sum(masses)
    perihelion, e = 0.5, 0.5
    speed = np.sqrt(gm * (1 + e) / perihelion)
    start = barycentric(
        masses, [[0.0, 0.0], [perihelion, 0.0]], [[0.0, 0.0], [0.0, speed]]
    )
    relative = State(t=0.0, x=[perihelion, 0.0], v=[0.0, speed])
    period = 2 * np.pi * np.sqrt(1.0 / gm)
    steps, errors = [], []
    for per_orbit in (800, 1600):
        run = simulate(
            start,
            gravity(G, masses),
            period / per_orbit,
            2 * per_orbit,
            step=verlet_step,
        )
        bodies = unstack(run.x, 2)
        exact = kepler_motion(relative, gm, run.t)
        errors.append(np.max(np.abs(bodies[:, 1] - bodies[:, 0] - exact.x)))
        steps.append(period / per_orbit)
    assert errors[-1] < 3e-3
    assert fitted_order(steps, errors) == pytest.approx(2.0, abs=0.05)


def test_symplectic_steps_keep_the_angular_momentum_and_bound_the_energy():
    masses = [1.0, 1e-3, 3e-4]
    start = barycentric(
        masses,
        [[0.0, 0.0], [5.0, 0.0], [0.0, 9.0]],
        [[0.0, 0.0], [0.0, np.sqrt(G / 5.0)], [-np.sqrt(G / 9.0), 0.0]],
    )
    for step in (symplectic_euler_step, verlet_step):
        run = simulate(start, gravity(G, masses), 0.05, 2000, step=step)
        momentum = angular_momentum(masses, run)
        assert np.max(np.abs(momentum / momentum[0] - 1.0)) < 1e-12
        energy = total_energy(G, masses, run)
        early = np.max(np.abs(energy[:200] / energy[0] - 1.0))
        late = np.max(np.abs(energy[-200:] / energy[0] - 1.0))
        assert late < 2.0 * early


def test_fewer_than_two_bodies_or_a_body_without_mass_are_rejected():
    with pytest.raises(ValueError, match="at least two"):
        gravity(1.0, [1.0])
    with pytest.raises(ValueError, match="positive"):
        gravity(1.0, [1.0, 0.0])
    with pytest.raises(ValueError, match="G must be positive"):
        gravity(0.0, [1.0, 1.0])
