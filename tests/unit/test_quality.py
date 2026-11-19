"""The measures of lesson AE1 (F149): each is computed from the readings and
the claim alone, is undefined where it has nothing to read, and tells apart
the cases a single score merges."""

import math

import numpy as np
import pytest

from pbc.discovery.baselines import Dataset, grid_probe, random_probe
from pbc.discovery.benchmark import PROTOCOLS, SEED
from pbc.discovery.environment import ProjectileEnvironment
from pbc.discovery.quality import (
    chance_distribution,
    information,
    probes_to_evidence,
    reasoning,
    supports,
)

PROTOCOL = PROTOCOLS["projectile"]


def _readings(settings) -> Dataset:
    world = PROTOCOL.make(SEED)
    values = [world.measure(**s)["range"] for s in settings]
    return Dataset(tuple(settings), np.array(values), world.observation.sigma)


SETTINGS = [{"speed": v, "angle": a} for v in (20.0, 30.0, 40.0) for a in (30.0, 45.0)]


def test_a_claim_that_contradicts_the_readings_fails_reasoning():
    world = PROTOCOL.make(SEED)
    data = _readings(SETTINGS)
    best = supports(PROTOCOL, data, SEED)
    assert best
    assert reasoning(world, {"g": 2.0}, data) is False


def test_reasoning_is_undefined_without_readings_or_without_a_claim():
    world = PROTOCOL.make(SEED)
    empty = Dataset((), np.array([]), world.observation.sigma)
    assert reasoning(world, {"g": 9.8}, empty) is None
    assert reasoning(world, None, _readings(SETTINGS)) is None


def test_readings_that_tell_nothing_do_not_support_a_recovery():
    # Every probe at the slowest launch: the ranges are short and the
    # noise hides gravity's effect less well than a spread of speeds would.
    flat = [{"speed": 5.0, "angle": 10.0 + k} for k in range(2)]
    assert probes_to_evidence(PROTOCOL, _readings(flat), SEED) is None


def test_probes_to_evidence_is_at_most_the_readings():
    data = _readings(SETTINGS)
    n = probes_to_evidence(PROTOCOL, data, SEED)
    assert n is not None and 2 <= n <= len(SETTINGS)


def test_a_grid_has_the_information_of_a_grid():
    world = ProjectileEnvironment(budget=9)
    grid = grid_probe(world)
    assert information(world, {"g": 6.0}, grid) == pytest.approx(1.0)


def test_fast_launches_at_forty_five_degrees_carry_more_information_than_a_grid():
    # The range depends on gravity as speed^2 sin(2 angle) / g^2: largest at
    # the fastest launch and at forty-five degrees.
    world = ProjectileEnvironment(budget=4)
    chosen = Dataset(
        tuple({"speed": 40.0, "angle": 45.0} for _ in range(4)),
        np.zeros(4),
        0.5,
    )
    assert information(world, {"g": 6.0}, chosen) > 1.0
    scattered = random_probe(ProjectileEnvironment(budget=4), 0)
    assert math.isfinite(information(world, {"g": 6.0}, scattered))


def test_the_chance_distribution_is_a_distribution_with_the_right_mean():
    p = [0.5, 0.25, 0.1]
    pmf = chance_distribution(p)
    assert pmf.sum() == pytest.approx(1.0)
    assert np.dot(np.arange(len(pmf)), pmf) == pytest.approx(sum(p))
