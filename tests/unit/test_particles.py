import numpy as np
import pytest

from pbc.mechanics.dynamics import State, simulate
from pbc.mechanics.integrators import INTEGRATORS, Integrator, rk4_step, verlet_step
from pbc.mechanics.oscillator import harmonic_motion
from pbc.mechanics.particles import (
    centre_of_mass,
    first_contact,
    hard_sphere_collision,
    interacting,
    kinetic_energy,
    pair_potential_energy,
    reduced_mass,
    soft_sphere,
    soft_sphere_potential,
    spring_pair,
    stack,
    total_momentum,
    unstack,
)

# Three unequal particles in the plane, joined by springs of lesson M7.
MASSES = [1.0, 2.0, 3.0]
START = State(
    t=0.0,
    x=stack([[0.0, 0.0], [1.2, 0.1], [0.3, 1.5]]),
    v=stack([[1.0, 0.5], [-0.3, 0.2], [0.1, -0.4]]),
)
SPRINGS = interacting(MASSES, spring_pair(5.0, 1.0))


def test_stack_and_unstack_convert_between_rows_and_the_state_vector():
    rows = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]

    flat = stack(rows)
    assert flat.tolist() == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    np.testing.assert_array_equal(unstack(flat, 3), rows)
    # A trajectory's positions, one vector per step, become (steps, n, d).
    assert unstack(np.array([flat, flat]), 3).shape == (2, 3, 2)
    with pytest.raises(ValueError, match="does not hold"):
        unstack(flat, 4)


def test_the_pair_force_obeys_the_third_law_so_the_forces_sum_to_zero():
    accelerations = unstack(SPRINGS(0.0, START.x, START.v), 3)
    forces = accelerations * np.array(MASSES)[:, np.newaxis]

    np.testing.assert_allclose(forces.sum(axis=0), [0.0, 0.0], atol=1e-14)
    # Two particles: the forces are equal and opposite, along the line.
    pair = interacting([1.0, 3.0], spring_pair(2.0, 1.0))
    a = unstack(pair(0.0, stack([[0.0, 0.0], [3.0, 4.0]]), np.zeros(4)), 2)
    np.testing.assert_allclose(1.0 * a[0], -3.0 * a[1])
    np.testing.assert_allclose(a[0], 2.0 * (5.0 - 1.0) * np.array([0.6, 0.8]))


@pytest.mark.parametrize("integrator", INTEGRATORS, ids=lambda i: i.name)
def test_every_integrator_conserves_the_total_momentum_to_round_off(
    integrator: Integrator,
):
    """Acceptance criterion 2: with the third law built into the pairwise
    force, the total momentum is constant to round-off for every method of
    the course, and the centre of mass moves in a straight line at constant
    velocity."""
    trajectory = simulate(START, SPRINGS, 0.02, 500, step=integrator.step)
    velocities = unstack(trajectory.v, 3)
    positions = unstack(trajectory.x, 3)

    momentum = total_momentum(MASSES, velocities)
    np.testing.assert_allclose(momentum - momentum[0], 0.0, rtol=0, atol=1e-13)
    centre = centre_of_mass(MASSES, positions)
    velocity = momentum[0] / sum(MASSES)
    expected = centre[0] + trajectory.t[:, np.newaxis] * velocity
    np.testing.assert_allclose(centre, expected, rtol=0, atol=1e-12)


def test_two_masses_on_a_spring_oscillate_with_the_reduced_mass():
    """The relative motion of a pair under a spring is the harmonic
    oscillator of lesson M4 with the reduced mass, whatever the centre of
    mass does."""
    m1, m2, k, rest = 1.0, 3.0, 12.0, 1.0
    mu = reduced_mass(m1, m2)
    assert mu == pytest.approx(0.75)
    pair = interacting([m1, m2], spring_pair(k, rest))
    initial = State(t=0.0, x=stack([[0.0], [rest + 0.2]]), v=stack([[2.0], [2.0]]))
    trajectory = simulate(initial, pair, 0.002, 2000, step=rk4_step)

    positions = unstack(trajectory.x, 2)
    stretch = positions[:, 1, 0] - positions[:, 0, 0] - rest
    exact = harmonic_motion(State(0.0, x=[0.2], v=[0.0]), mu, k, trajectory.t)
    np.testing.assert_allclose(stretch, exact.x[:, 0], rtol=0, atol=1e-6)


def test_kinetic_energy_sums_over_the_particles_with_their_own_masses():
    velocities = [[3.0, 4.0], [0.0, 1.0], [0.0, 0.0]]

    assert kinetic_energy(MASSES, velocities) == pytest.approx(0.5 * 25.0 + 0.5 * 2.0)
    assert kinetic_energy(MASSES, [velocities, velocities]).shape == (2,)


def test_soft_spheres_repel_only_while_they_overlap_and_the_potential_matches():
    k, diameter = 100.0, 0.2
    force = soft_sphere(k, diameter)
    potential = soft_sphere_potential(k, diameter)

    apart = np.array([0.3, 0.0])
    assert force(apart).tolist() == [0.0, 0.0] and potential(apart) == 0.0
    overlapping = np.array([0.12, 0.09])  # distance 0.15, overlap 0.05
    np.testing.assert_allclose(force(overlapping), k * 0.05 * overlapping / 0.15)
    assert potential(overlapping) == pytest.approx(0.5 * k * 0.05**2)
    # F = -dU/dr along the line of centres, by central differences.
    h = 1e-6
    along = overlapping / 0.15
    numerical = -(
        potential(overlapping + h * along) - potential(overlapping - h * along)
    ) / (2 * h)
    assert numerical == pytest.approx(force(overlapping) @ along, rel=1e-6)


def test_the_hard_sphere_collision_conserves_momentum_and_kinetic_energy():
    m1, m2 = 1.0, 2.0
    v1, v2 = np.array([1.0, 0.5]), np.array([-0.5, 0.0])
    normal = np.array([0.6, 0.8])

    w1, w2 = hard_sphere_collision(m1, v1, m2, v2, normal)

    np.testing.assert_allclose(m1 * w1 + m2 * w2, m1 * v1 + m2 * v2)
    assert m1 * w1 @ w1 + m2 * w2 @ w2 == pytest.approx(m1 * v1 @ v1 + m2 * v2 @ v2)
    # The relative velocity along the normal reverses; across it, nothing changes.
    assert (w1 - w2) @ normal == pytest.approx(-(v1 - v2) @ normal)
    across = np.array([-0.8, 0.6])
    assert (w1 - w2) @ across == pytest.approx((v1 - v2) @ across)


def test_equal_hard_spheres_exchange_velocities_head_on_and_part_at_a_right_angle():
    w1, w2 = hard_sphere_collision(1.0, [1.0], 1.0, [0.0], [-1.0])
    assert w1.tolist() == [0.0] and w2.tolist() == [1.0]

    normal = np.array([-np.sqrt(3) / 2, 0.5])  # an off-centre hit
    w1, w2 = hard_sphere_collision(1.0, [1.0, 0.0], 1.0, [0.0, 0.0], normal)
    assert w1 @ w2 == pytest.approx(0.0, abs=1e-15)


def test_first_contact_finds_the_moment_and_the_line_of_centres():
    # Approaching along x, offset by half a diameter: the centres touch at 60 degrees.
    t, normal = first_contact([-1.0, 0.1], [1.0, 0.0], 0.2)

    assert t == pytest.approx(1.0 - 0.2 * np.sqrt(3) / 2)
    np.testing.assert_allclose(normal, [-np.sqrt(3) / 2, 0.5])
    with pytest.raises(ValueError, match="overlap"):
        first_contact([0.1, 0.0], [1.0, 0.0], 0.2)
    with pytest.raises(ValueError, match="never"):
        first_contact([-1.0, 0.3], [1.0, 0.0], 0.2)  # passes by
    with pytest.raises(ValueError, match="never"):
        first_contact([-1.0, 0.0], [-1.0, 0.0], 0.2)  # moving apart


def test_a_head_on_soft_sphere_collision_ends_as_the_hard_sphere_one():
    """Resolved with 40 steps per contact, the soft spheres leave with the
    hard-sphere velocities within a stated bound, with the total energy,
    kinetic plus contact, constant to a smaller one throughout."""
    m1, m2, k, diameter = 1.0, 2.0, 1000.0, 0.2
    contact_time = np.pi * np.sqrt(reduced_mass(m1, m2) / k)
    dt = contact_time / 40
    collision = interacting([m1, m2], soft_sphere(k, diameter))
    initial = State(t=0.0, x=stack([[0.0], [1.0]]), v=stack([[1.0], [-0.5]]))
    trajectory = simulate(initial, collision, dt, round(1.5 / dt), step=verlet_step)

    velocities = unstack(trajectory.v, 2)
    expected = hard_sphere_collision(m1, [1.0], m2, [-0.5], [-1.0])
    np.testing.assert_allclose(velocities[-1], expected, rtol=0, atol=1e-4)
    energies = kinetic_energy([m1, m2], velocities) + pair_potential_energy(
        unstack(trajectory.x, 2), soft_sphere_potential(k, diameter)
    )
    # The contact is a harmonic spring, so the band of lesson M5 applies:
    # omega² dt² / 4 = (pi / 40)² / 4, about 1.5e-3.
    assert np.max(np.abs(energies / energies[0] - 1)) < 3e-3
    # The contact lasted about as long as the formula says.
    overlapping = np.sum(
        unstack(trajectory.x, 2)[:, 1, 0] - unstack(trajectory.x, 2)[:, 0, 0] < diameter
    )
    assert overlapping * dt == pytest.approx(contact_time, rel=0.1)


def test_the_scattering_angle_tends_to_the_hard_sphere_angle_as_the_stiffness_grows():
    """Off centre, the line of centres turns during a soft contact, so the
    outcome differs from the hard-sphere one by an amount that shrinks
    with the contact time, about as 1 / sqrt(k)."""
    diameter, offset = 0.2, 0.1
    _, normal = first_contact([-1.0, offset], [1.0, 0.0], diameter)
    exact, _ = hard_sphere_collision(1.0, [1.0, 0.0], 1.0, [0.0, 0.0], normal)
    exact_angle = np.arctan2(exact[1], exact[0])

    differences = []
    for k in (1e3, 1e4):
        dt = np.pi * np.sqrt(0.5 / k) / 40
        collision = interacting([1.0, 1.0], soft_sphere(k, diameter))
        initial = State(
            0.0,
            x=stack([[-1.0, offset], [0.0, 0.0]]),
            v=stack([[1.0, 0.0], [0.0, 0.0]]),
        )
        final = unstack(
            simulate(initial, collision, dt, round(2.0 / dt), step=verlet_step).v, 2
        )[-1, 0]
        differences.append(abs(np.arctan2(final[1], final[0]) - exact_angle))

    assert differences[0] > differences[1] > 0
    assert differences[1] < differences[0] / 2
    assert differences[1] < np.radians(2.0)


def test_pair_potential_energy_sums_over_the_pairs():
    potential = soft_sphere_potential(100.0, 1.0)
    positions = [
        [0.0, 0.0],
        [0.5, 0.0],
        [0.0, 0.5],
        [5.0, 5.0],
    ]  # three overlapping pairs

    expected = 0.5 * 100.0 * (0.5**2 + 0.5**2 + (1 - np.sqrt(0.5)) ** 2)
    assert pair_potential_energy(positions, potential) == pytest.approx(expected)
    assert pair_potential_energy([positions, positions], potential).shape == (2,)


@pytest.mark.parametrize("masses", [[1.0, 0.0], [-1.0], [[1.0, 2.0]]])
def test_masses_must_be_a_list_of_positive_numbers(masses):
    with pytest.raises(ValueError, match="masses"):
        interacting(masses, spring_pair(1.0, 1.0))
    with pytest.raises(ValueError, match="masses"):
        total_momentum(masses, np.zeros((len(masses), 1)))


def test_pair_force_parameters_that_make_no_sense_are_rejected():
    with pytest.raises(ValueError, match="spring constant"):
        spring_pair(0.0, 1.0)
    with pytest.raises(ValueError, match="rest length"):
        spring_pair(1.0, -1.0)
    with pytest.raises(ValueError, match="stiffness"):
        soft_sphere(-1.0, 1.0)
    with pytest.raises(ValueError, match="diameter"):
        soft_sphere_potential(1.0, 0.0)
    with pytest.raises(ValueError, match="masses"):
        reduced_mass(1.0, 0.0)
