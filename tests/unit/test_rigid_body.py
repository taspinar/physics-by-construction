import numpy as np
import pytest

from pbc.mechanics.rigid_body import (
    Top,
    axial_momentum,
    fast_top_rate,
    inertia_tensor,
    mean_precession_rate,
    parallel_axis,
    rotation_matrix,
    simulate_top,
    steady_precession_rates,
    tilted_start,
    top_energy,
)
from pbc.verification.estimates import invariant_drift

# The gyroscope of lesson M17: a disc of half a kilogram and radius 4 cm,
# 5 cm from the pivot.
MASS, RADIUS, ARM = 0.5, 0.04, 0.05
TOP = Top(
    mass=MASS,
    length=ARM,
    i1=0.25 * MASS * RADIUS**2 + MASS * ARM**2,
    i3=0.5 * MASS * RADIUS**2,
)


def test_the_inertia_tensor_of_a_dumbbell_has_its_closed_form():
    # Two masses on the x axis: no moment about x, m d² about y and z.
    tensor = inertia_tensor([1.0, 1.0], [[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0]])
    assert tensor == pytest.approx(np.diag([0.0, 2.0, 2.0]))


def test_the_principal_moments_of_a_ring_are_m_r_squared_and_half_of_it():
    angles = np.linspace(0.0, 2 * np.pi, 360, endpoint=False)
    points = np.stack([np.cos(angles), np.sin(angles), np.zeros_like(angles)], axis=1)
    tensor = inertia_tensor(np.full(360, 1.0 / 360), points)
    assert np.linalg.eigvalsh(tensor) == pytest.approx([0.5, 0.5, 1.0])


def test_the_parallel_axis_theorem_agrees_with_the_moved_points():
    rng = np.random.default_rng(7)
    masses = rng.uniform(0.1, 1.0, 20)
    points = rng.normal(size=(20, 3))
    points -= masses @ points / masses.sum()
    offset = np.array([0.3, -0.2, 0.5])
    direct = inertia_tensor(masses, points + offset)
    assert parallel_axis(
        inertia_tensor(masses, points), masses.sum(), offset
    ) == pytest.approx(direct)


def test_the_quaternion_of_the_start_tilts_the_axis_in_the_x_z_plane():
    q, _ = tilted_start(TOP, 0.5, 100.0)
    rotation = rotation_matrix(q)
    assert rotation @ rotation.T == pytest.approx(np.eye(3), abs=1e-15)
    assert rotation[:, 2] == pytest.approx([np.sin(0.5), 0.0, np.cos(0.5)])


def test_the_angular_momentum_changes_at_the_rate_of_the_torque():
    q, momentum = tilted_start(TOP, 0.5, 200.0)
    motion = simulate_top(TOP, q, momentum, 1e-4, 20)
    rate = (motion.momentum[2] - motion.momentum[0]) / (2e-4)
    torque = TOP.torque(motion.q[1])
    assert np.linalg.norm(rate - torque) < 1e-6 * np.linalg.norm(torque)


def test_the_run_keeps_the_energy_and_the_conserved_components():
    q, momentum = tilted_start(TOP, 0.5, 200.0)
    motion = simulate_top(TOP, q, momentum, 5e-4, 2000)
    assert invariant_drift(top_energy(TOP, motion)) < 1e-6
    assert invariant_drift(motion.momentum[:, 2]) < 1e-14
    assert invariant_drift(axial_momentum(motion)) < 1e-6


def test_a_hanging_top_without_spin_is_a_pendulum():
    # No spin, the axis hanging a little off the downward vertical: it swings
    # with the period of a physical pendulum, 2 pi sqrt(I1 / (m g l)), and
    # after half a period hangs as far off on the other side.
    q, momentum = tilted_start(TOP, np.pi - 0.01, 0.0)
    period = 2 * np.pi * np.sqrt(TOP.i1 / (TOP.mass * TOP.g * TOP.length))
    motion = simulate_top(TOP, q, momentum, period / 2000, 1000)
    expected = [-np.sin(0.01), 0.0, -np.cos(0.01)]
    assert motion.axes()[-1] == pytest.approx(expected, abs=1e-6)


def test_a_start_on_steady_precession_precesses_at_the_slow_rate():
    slow, fast = steady_precession_rates(TOP, 0.5, 200.0)
    assert slow < fast
    q, momentum = tilted_start(TOP, 0.5, 200.0, slow)
    motion = simulate_top(TOP, q, momentum, 5e-4, 2000)
    assert mean_precession_rate(motion) == pytest.approx(slow, rel=1e-6)
    tilts = np.arccos(motion.axes()[:, 2])
    assert np.ptp(tilts) < 1e-6


def test_the_slow_rate_tends_to_the_fast_top_limit():
    ratios = [
        steady_precession_rates(TOP, 0.5, spin)[0] / fast_top_rate(TOP, spin)
        for spin in (2000.0, 20000.0)
    ]
    # The correction falls as the inverse square of the spin.
    differences = np.array(ratios) - 1.0
    assert np.all(differences > 0)
    assert differences[1] / differences[0] == pytest.approx(0.01, rel=0.01)


def test_steady_precession_needs_enough_spin():
    with pytest.raises(ValueError, match="too small"):
        steady_precession_rates(TOP, 0.5, 10.0)
    with pytest.raises(ValueError, match="positive"):
        Top(mass=1.0, length=0.0, i1=1.0, i3=1.0)
