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
    test = state_test(np.column_stack([data.x, data.v]), data.a)

    assert test.pairs > 0
    assert test.passes
    assert test.largest <= SMOOTHNESS * RADIUS


def test_a_variable_the_dynamics_need_left_out_fails_the_state_test():
    # The damped oscillator's acceleration depends on the velocity; the
    # position alone is not its state.
    data = damped_samples()
    test = state_test(data.x.reshape(-1, 1), data.a)

    assert not test.passes
    i, j = test.witness
    assert abs(data.x[i] - data.x[j]) < RADIUS * data.x.std()
    assert abs(data.a[i] - data.a[j]) > SMOOTHNESS * RADIUS * np.sqrt(
        (data.a**2).mean()
    )


def test_without_a_pair_the_state_test_does_not_pass():
    values = np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 0.0]])
    test = state_test(values, np.array([0.0, 1.0, 2.0]), radius=1e-6)

    assert test.pairs == 0 and not test.passes
