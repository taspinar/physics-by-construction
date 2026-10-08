import numpy as np
import pytest

import pbc.abm.gas as gas_module
from pbc.abm.gas import (
    N_DISCS,
    RADIUS,
    SIDE,
    SPEED,
    Gas,
    ideal_gas_pressure,
    initial_gas,
    mean_and_error,
    measure,
    rayleigh_pdf,
    run,
    speed_ratio,
    step,
    temperature,
    virial_correction,
    wall_pressure,
)


def two_discs(x1, v1, x2, v2, radius=0.05, side=1.0) -> Gas:
    return Gas(
        np.array([x1, x2], dtype=float),
        np.array([v1, v2], dtype=float),
        radius=radius,
        mass=2.0,
        side=side,
    )


def test_initial_gas_is_a_function_of_the_seed():
    first = initial_gas(30, 0.02, 1.0, 1.0, np.random.default_rng(7))
    again = initial_gas(30, 0.02, 1.0, 1.0, np.random.default_rng(7))
    other = initial_gas(30, 0.02, 1.0, 1.0, np.random.default_rng(8))

    np.testing.assert_array_equal(first.positions, again.positions)
    np.testing.assert_array_equal(first.velocities, again.velocities)
    assert not np.array_equal(first.positions, other.positions)


def test_initial_gas_has_no_overlap_no_momentum_and_the_stated_energy():
    gas = initial_gas(60, 0.02, 1.0, 1.5, np.random.default_rng(1))

    assert np.all(gas.positions >= gas.radius)
    assert np.all(gas.positions <= gas.side - gas.radius)
    gaps = np.hypot(*(gas.positions[:, None] - gas.positions[None]).transpose(2, 0, 1))
    assert np.all(gaps[np.triu_indices(60, k=1)] >= 2.0 * gas.radius)
    np.testing.assert_allclose(gas.velocities.sum(axis=0), 0.0, atol=1e-12)
    np.testing.assert_allclose(np.mean(np.sum(gas.velocities**2, axis=1)), 1.5**2)


def test_initial_gas_refuses_a_box_that_cannot_hold_the_discs():
    with pytest.raises(ValueError, match="more than half"):
        initial_gas(100, 0.1, 1.0, 1.0, np.random.default_rng(0))


def test_initial_gas_refuses_fewer_than_two_discs():
    # One disc cannot have zero momentum and the stated energy at once.
    with pytest.raises(ValueError, match="at least 2"):
        initial_gas(1, 0.007, 1.0, 1.0, np.random.default_rng(0))
    with pytest.raises(ValueError, match="at least 2"):
        initial_gas(0, 0.007, 1.0, 1.0, np.random.default_rng(0))


def test_initial_gas_restarts_when_the_first_disc_leaves_no_room():
    # Two discs of radius 0.28 pass the area check, but their centres are
    # confined to a square of side 0.44 whose diagonal, 0.62, barely exceeds
    # the separation 0.56 they need. With seed 0 the first centre lands near
    # the middle, where no second disc fits, so the placement has to start
    # over rather than reject candidates forever.
    gas = initial_gas(2, 0.28, 1.0, 1.0, np.random.default_rng(0))

    assert np.hypot(*(gas.positions[0] - gas.positions[1])) >= 2 * gas.radius
    assert np.all(gas.positions >= gas.radius)
    assert np.all(gas.positions <= gas.side - gas.radius)
    assert np.all(np.isfinite(gas.velocities))


def test_initial_gas_gives_up_after_the_bounded_search(monkeypatch):
    # The same stalled start, with the search cut to one batch of one start:
    # the placement must end in a clear error rather than run on.
    monkeypatch.setattr(gas_module, "PLACEMENT_BATCHES", 1)
    monkeypatch.setattr(gas_module, "PLACEMENT_RESTARTS", 1)
    with pytest.raises(ValueError, match="could not place 2 discs"):
        initial_gas(2, 0.28, 1.0, 1.0, np.random.default_rng(0))


def test_a_disc_reflects_from_a_wall_and_the_wall_gets_the_impulse():
    # One disc of mass 2 reaches the right wall with normal speed 3.
    gas = two_discs([0.93, 0.5], [3.0, 0.5], [0.3, 0.5], [0.0, 0.0])

    after, impulse = step(gas, 0.1)

    assert after.velocities[0, 0] == -3.0
    assert after.velocities[0, 1] == 0.5
    assert impulse == pytest.approx(2.0 * 2.0 * 3.0)
    assert np.all(after.positions <= gas.side - gas.radius)


def test_equal_discs_that_meet_head_on_exchange_velocities():
    gas = two_discs([0.46, 0.5], [1.0, 0.0], [0.55, 0.5], [-1.0, 0.0])

    after, impulse = step(gas, 0.001)

    np.testing.assert_allclose(after.velocities, [[-1.0, 0.0], [1.0, 0.0]])
    assert impulse == 0.0


def test_overlapping_discs_that_move_apart_do_not_collide():
    gas = two_discs([0.45, 0.5], [-1.0, 0.0], [0.53, 0.5], [1.0, 0.0])

    after, _ = step(gas, 0.001)

    np.testing.assert_array_equal(after.velocities, gas.velocities)


def test_a_run_conserves_energy_and_keeps_the_discs_in_the_box():
    gas = initial_gas(60, 0.02, 1.0, 1.0, np.random.default_rng(3))
    energy = 0.5 * gas.mass * np.sum(gas.velocities**2)

    recorded = run(gas, 1.0, 0.002, every=50)

    final = recorded.final
    np.testing.assert_allclose(
        0.5 * final.mass * np.sum(final.velocities**2), energy, rtol=1e-12
    )
    assert np.all(final.positions >= final.radius)
    assert np.all(final.positions <= final.side - final.radius)
    assert recorded.times.shape == (10,)
    assert recorded.wall_impulse.sum() > 0.0


def test_run_is_a_function_of_the_seed():
    def speeds(seed):
        gas = initial_gas(40, 0.02, 1.0, 1.0, np.random.default_rng(seed))
        return run(gas, 0.5, 0.002, every=50).speeds

    np.testing.assert_array_equal(speeds(5), speeds(5))


def test_run_refuses_bad_arguments():
    gas = initial_gas(5, 0.02, 1.0, 1.0, np.random.default_rng(0))
    with pytest.raises(ValueError):
        run(gas, 1.0, 0.0)
    with pytest.raises(ValueError):
        run(gas, 1.0, 0.01, every=0)


def test_measure_refuses_a_duration_shorter_than_one_snapshot_interval():
    # Snapshots come every `every * dt` seconds. A measurement shorter than
    # that selects no snapshot and would give NaN temperature and pressure.
    with pytest.raises(ValueError, match="at least one snapshot interval"):
        measure(0, n=2, duration=0.001)

    # One full interval is enough: the measurement is a finite number.
    one_interval = measure(0, n=2, duration=gas_module.EVERY * gas_module.DT)
    assert one_interval.speeds.shape == (1, 2)
    assert np.isfinite(one_interval.kt)
    assert np.isfinite(one_interval.pressure)


def test_temperature_and_pressure_formulas():
    speeds = np.array([3.0, 4.0])  # <v^2> = 12.5
    assert temperature(speeds, 2.0) == pytest.approx(12.5)
    assert ideal_gas_pressure(10, 2.0, 0.5) == pytest.approx(80.0)
    assert wall_pressure(8.0, 2.0, 0.5) == pytest.approx(2.0)
    assert virial_correction(0.05) == pytest.approx(1.1)


def test_rayleigh_pdf_is_the_two_dimensional_maxwell_distribution():
    # Normalised, with the mean speed sqrt(pi kT / (2 m)) and <v^4>/<v^2>^2 = 2.
    kt, mass = 0.7, 1.3
    v = np.linspace(0.0, 12.0, 200_001)
    pdf = rayleigh_pdf(v, kt, mass)
    dv = v[1] - v[0]

    assert np.sum(pdf) * dv == pytest.approx(1.0, abs=1e-6)
    assert np.sum(v * pdf) * dv == pytest.approx(np.sqrt(np.pi * kt / (2 * mass)))
    mean_v2, mean_v4 = np.sum(v**2 * pdf) * dv, np.sum(v**4 * pdf) * dv
    assert mean_v2 == pytest.approx(2.0 * kt / mass)
    assert mean_v4 / mean_v2**2 == pytest.approx(2.0, rel=1e-6)
    assert speed_ratio(np.full(10, 3.0)) == 1.0


def test_mean_and_error():
    mean, error = mean_and_error(np.array([1.0, 2.0, 3.0, 4.0]))
    assert mean == 2.5
    assert error == pytest.approx(np.std([1, 2, 3, 4], ddof=1) / 2.0)
    with pytest.raises(ValueError):
        mean_and_error(np.array([1.0]))


# Emergent behaviour of the relaxed gas against kinetic theory. Six
# independent seeded runs of the default gas; the tolerance is four standard
# errors of the mean over the runs, the heuristic the lesson states. The
# standard error is itself estimated from the six runs, so the discrepancy in
# standard errors follows Student's t with five degrees of freedom, and chance
# alone exceeds four in about one case in a hundred (not the Gaussian one in
# fifteen thousand). With the seeds fixed the outcome is the same on every
# run, so a failure is a strong reason to suspect the model, not a proof.
SEEDS = range(6)
SIGMAS = 4.0


@pytest.fixture(scope="module")
def measurements():
    return [measure(seed) for seed in SEEDS]


def test_collisions_turn_equal_speeds_into_the_maxwell_distribution(measurements):
    start = initial_gas(N_DISCS, RADIUS, SIDE, SPEED, np.random.default_rng(0))
    assert speed_ratio(np.hypot(*start.velocities.T)) < 1.2  # nearly one speed

    ratios = np.array([speed_ratio(m.speeds) for m in measurements])
    mean, error = mean_and_error(ratios)

    assert abs(mean - 2.0) <= SIGMAS * error
    assert error < 0.1  # the test can tell 2 from 1.2, the start, by a wide margin


# The prediction 1 + 2 phi stops at the second virial coefficient, and the
# fixed time step resolves collisions late, which lowers the measured
# pressure a little (1.056 at dt = 0.002 s, 1.0605 at 0.001 s and below, for
# a prediction of 1.063). Both are systematic and about 0.01 at most, so
# more runs or other seeds do not make them go away; the tolerance allows
# for them besides the statistical error of the runs.
PRESSURE_MODEL_ERROR = 0.01


def test_pressure_follows_the_gas_law_with_the_excluded_area(measurements):
    ratios = np.array([m.pressure / m.ideal_pressure for m in measurements])
    mean, error = mean_and_error(ratios)
    predicted = virial_correction(measurements[0].packing_fraction)

    assert abs(mean - predicted) <= SIGMAS * error + PRESSURE_MODEL_ERROR
    # The correction is real: ideal points would be outside the tolerance.
    assert abs(mean - 1.0) > SIGMAS * error + PRESSURE_MODEL_ERROR
