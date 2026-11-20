"""The choice of state variables (MD4, F147): ``pbc.discovery.state_selection``."""

import numpy as np
import pytest

from pbc.discovery.equations import (
    central_differences,
    combine,
    polynomial_library,
    sparse_regression,
)
from pbc.discovery.state_selection import (
    APART,
    RADIUS,
    SMOOTHNESS,
    library,
    search,
    state_test,
)
from pbc.mechanics.experiments import discovering_differential_equations as d8


def damped_samples():
    return combine(
        [
            central_differences(d8.positions(d8.damped, *start), d8.DT)
            for start in d8.STARTS
        ]
    )


def damped_visits():
    """The orbit and the time (s) of each sample of ``damped_samples``."""
    count = len(damped_samples().a) // len(d8.STARTS)
    orbits = np.repeat(np.arange(len(d8.STARTS)), count)
    times = np.tile(d8.DT * np.arange(1, count + 1), len(d8.STARTS))
    return orbits, times


def test_the_library_of_position_and_velocity_is_that_of_the_published_search():
    assert set(library(("x", "v"), 3)) == set(polynomial_library(3))
    assert len(library(("a", "b", "c", "d"), 3)) == 35


def test_the_search_on_position_and_velocity_is_the_published_search():
    data = damped_samples()
    found = search(("x", "v"), np.column_stack([data.x, data.v]), data.a)
    published = sparse_regression(polynomial_library(3), data)

    assert found.coefficients.keys() == published.coefficients.keys()
    for term, c in published.coefficients.items():
        assert found.coefficients[term] == pytest.approx(c, rel=1e-9)
    assert found.residual == pytest.approx(published.residual, rel=1e-6)


def test_a_complete_state_passes_the_state_test():
    data = damped_samples()
    orbits, times = damped_visits()
    test = state_test(np.column_stack([data.x, data.v]), data.a, orbits, times)

    assert test.pairs > 0
    assert test.passes
    assert test.largest <= SMOOTHNESS * RADIUS
    # The witness pair is a pair of separate visits, not neighbours in time.
    i, j = test.witness
    assert orbits[i] != orbits[j] or abs(times[i] - times[j]) >= APART


def test_neighbours_in_time_are_not_compared():
    # One smooth orbit on which the position never returns: every pair
    # within the radius is a pair of neighbours in time, less than APART
    # apart, which agree for any smooth record. They test nothing, so the
    # test finds no pair; counted as separate orbits, they would all pass.
    t = np.arange(0.0, 3.0, 0.001)
    values, a = t.reshape(-1, 1), np.sin(t)
    test = state_test(values, a, np.zeros(len(t)), t)

    assert test.pairs == 0 and not test.passes
    counted = state_test(values, a, np.arange(len(t)), t)
    assert counted.pairs > 0 and counted.passes


def test_a_variable_the_dynamics_need_left_out_fails_the_state_test():
    # The damped oscillator's acceleration depends on the velocity; the
    # position alone is not its state.
    data = damped_samples()
    test = state_test(data.x.reshape(-1, 1), data.a, *damped_visits())

    assert not test.passes
    i, j = test.witness
    assert abs(data.x[i] - data.x[j]) < RADIUS * data.x.std()
    assert abs(data.a[i] - data.a[j]) > SMOOTHNESS * RADIUS * np.sqrt(
        (data.a**2).mean()
    )


def test_without_a_pair_the_state_test_does_not_pass():
    values = np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 0.0]])
    test = state_test(
        values,
        np.array([0.0, 1.0, 2.0]),
        np.arange(3),
        np.zeros(3),
        radius=1e-6,
    )

    assert test.pairs == 0 and not test.passes
