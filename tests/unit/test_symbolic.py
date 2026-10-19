"""pbc.discovery.symbolic: the power-law search finds a law of its grammar,
reports the forms the data cannot tell apart, and fails on a law outside the
grammar instead of returning a claim."""

import itertools
import math

import numpy as np
import pytest

from pbc.discovery.symbolic import HALF_STEPS, PowerLaw, noise_floor, power_law_search


def data(n=30, seed=0):
    rng = np.random.default_rng(seed)
    return {"a": rng.uniform(0.5, 5.0, n), "b": rng.uniform(1.0, 20.0, n)}


def test_a_law_of_the_grammar_is_found_with_its_constant():
    variables = data()
    y = 3.0 * variables["a"] ** 1.5 / variables["b"]

    search = power_law_search(variables, y, sigma=1e-6)

    assert search.chosen.exponents == (1.5, -1.0)
    assert search.chosen.constant == pytest.approx(3.0, rel=1e-9)
    assert search.chosen.chi2 < 1e-12
    assert search.consistent() == (search.chosen,)
    assert len(search.forms) == len(HALF_STEPS) ** 2


def test_the_simplest_consistent_form_is_chosen_over_a_better_fitting_one():
    variables = data()
    # A weak dependence on b, hidden by noise of 10 percent.
    y = 2.0 * variables["a"] * variables["b"] ** 0.01
    rng = np.random.default_rng(1)
    y = y * np.exp(0.1 * rng.standard_normal(y.size))

    search = power_law_search(variables, y, sigma=0.1)

    assert search.chosen.exponents == (1.0, 0.0)
    assert search.chosen.complexity == 3


def test_a_variable_the_data_do_not_vary_ties_every_exponent_it_could_have():
    variables = data()
    variables["b"] = np.full(30, 4.0)
    y = 2.0 * variables["a"] ** 0.5 * variables["b"] ** -0.5

    search = power_law_search(variables, y, sigma=1e-3)

    assert {f.exponents[0] for f in search.rivals} == {0.5}
    assert sorted(f.exponents[1] for f in search.rivals) == sorted(HALF_STEPS)
    # The simplest of them leaves b out, with the constant absorbing it.
    assert search.chosen.exponents == (0.5, 0.0)
    assert search.chosen.constant == pytest.approx(1.0)


def test_a_law_outside_the_grammar_gives_no_claim_but_a_reason():
    variables = data()
    y = np.exp(variables["a"])

    search = power_law_search(variables, y, sigma=1e-3)

    assert search.chosen is None
    assert search.rivals == ()
    assert search.reason.startswith("no form of the grammar is consistent")


def test_the_noise_floor_is_where_the_misfit_fills_the_margin_of_the_limit():
    variables = data()
    y = 2.0 * variables["a"] ** 0.5 * variables["b"] ** -0.5
    search = power_law_search(variables, y * (1 + 1e-9), sigma=1e-3)
    wrong = next(f for f in search.forms if f.exponents == (0.5, 0.0))

    floor = noise_floor(search, wrong)

    misfit_at_floor = wrong.chi2 * (search.sigma / floor) ** 2
    assert misfit_at_floor == pytest.approx(3 * math.sqrt(2 * search.dof))
    # Far above the floor the form passes, far below it is rejected.
    rng = np.random.default_rng(3)
    for noise, passes in ((3 * floor, True), (floor / 3, False)):
        noisy = y * np.exp(noise * rng.standard_normal(y.size))
        found = power_law_search(variables, noisy, sigma=noise)
        refit = next(f for f in found.forms if f.exponents == (0.5, 0.0))
        assert (refit.chi2 <= found.limit) is passes


def test_the_pareto_front_trades_complexity_for_fit():
    variables = data()
    y = 2.0 * variables["a"] ** 0.5 * variables["b"] ** -0.5

    front = power_law_search(variables, y, sigma=1e-3).pareto()

    assert [f.complexity for f in front] == sorted({f.complexity for f in front})
    assert all(b.chi2 < a.chi2 for a, b in itertools.pairwise(front))
    assert front[-1].exponents == (0.5, -0.5)


def test_complexity_counts_variables_and_half_steps():
    def form(*p):
        return PowerLaw(("L", "g"), p, 1.0, 0.0)

    assert form(0.0, 0.0).complexity == 0
    assert form(0.5, 0.0).complexity == 2
    assert form(1.0, 0.0).complexity == 3
    assert form(0.5, -0.5).complexity == 4


def test_a_form_reads_and_predicts_as_written():
    form = PowerLaw(("L", "g"), (0.5, -0.5), 2 * math.pi, 0.0)

    assert form.shape == "L^(1/2) g^(-1/2)"
    assert form.formula() == "6.283 L^(1/2) g^(-1/2)"
    assert PowerLaw(("L",), (1.0,), 2.0, 0.0).formula() == "2 L"
    assert PowerLaw(("L",), (0.0,), 2.0, 0.0).formula() == "2"
    assert form.predict({"L": 1.0, "g": 9.80665}) == pytest.approx(2.006, abs=1e-3)


def test_a_search_needs_a_positive_noise_and_two_measurements():
    with pytest.raises(ValueError, match="sigma"):
        power_law_search({"a": [1.0, 2.0]}, [1.0, 2.0], sigma=0.0)
    with pytest.raises(ValueError, match="two"):
        power_law_search({"a": [1.0]}, [1.0], sigma=0.1)
