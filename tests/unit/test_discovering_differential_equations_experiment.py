"""The experiment of "Discovering differential equations from trajectories"
(agents-llm 09, D8)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.mechanics.experiments.discovering_differential_equations"
PAGE = "agents-llm/09-discovering-differential-equations"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("discovering_differential_equations")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_equation_is_recovered_from_clean_positions(results):
    _, found = results
    numbers = found["numbers"]

    assert numbers["recovered"] == "recovered"
    assert float(numbers["largest-error"]) < float(numbers["tolerance"])
    kept = {
        row[0]: float(row[2])
        for row in found["tables"]["coefficients"]["rows"]
        if row[2]
    }
    assert kept == pytest.approx({"x": -4.0, "v": -0.3}, rel=1e-3)


def test_the_found_equation_holds_from_a_held_out_start(results):
    _, found = results
    numbers = found["numbers"]

    assert float(numbers["held-out-error"]) < 1e-3 * float(
        numbers["held-out-amplitude"]
    )


def test_one_orbit_cannot_tell_the_equation_from_a_rival(results):
    _, found = results
    numbers = found["numbers"]

    (true, on_true, off_true), (_, on_rival, off_rival) = found["tables"][
        "rival-equations"
    ]["rows"]
    assert true == "a = -4 x"
    # Both fit the orbit within the error of the differences; only another
    # orbit separates them.
    assert max(float(on_true), float(on_rival)) < 1e-3
    assert float(off_true) < 1e-3 < 1.0 < float(off_rival)
    assert numbers["near-zero"] == "3"
    assert float(numbers["smallest-several"]) > 0.01


def test_a_pendulum_gives_the_law_of_its_training_range(results):
    _, found = results

    (_, linear, drift_small), (_, cubic, drift_large) = found["tables"]["pendulum"][
        "rows"
    ]
    assert "x^3" not in linear and "x^3" in cubic and "+" in cubic
    assert float(drift_large) < float(drift_small)


def test_a_state_without_the_second_mass_is_detected_and_its_cure_named(results):
    _, found = results
    numbers = found["numbers"]
    (
        (one, one_found, one_res, one_pairs, one_largest, one_err),
        (
            two,
            two_found,
            two_res,
            two_pairs,
            two_largest,
            two_err,
        ),
    ) = found["tables"]["state-selection"]["rows"]
    limit = float(numbers["smoothness-limit"])

    assert (one, two) == ("x1, v1", "x1, v1, x2, v2")
    assert float(one_err) > 100 * float(two_err)
    # The search on the one-mass state returns a short equation regardless.
    assert one_found == numbers["one-mass-found"]
    assert 1 <= int(numbers["one-mass-terms"]) <= 4
    assert float(one_res) > 10 and float(two_res) < 1e-4
    # The state test fails on one mass and passes on both.
    assert numbers["one-mass-test"] == "fails" and float(one_largest) > limit
    assert numbers["two-mass-test"] == "passes" and float(two_largest) <= limit
    # Both verdicts rest on pairs from separate visits, not on neighbours
    # in time, which agree whatever the state.
    assert int(one_pairs) > 0 and int(two_pairs) > 0
    assert numbers["two-mass-pairs"] == two_pairs
    assert float(numbers["one-mass-largest"]) == pytest.approx(
        float(one_largest), rel=0.05
    )
    assert numbers["two-mass-recovered"] == "keeps exactly the true terms"
    assert two_found == numbers["two-mass-found"] == "a = -5.5 x1 + 1.5 x2"
    # The witness pair: the same state of the first mass, the second mass
    # on opposite sides, the accelerations of opposite signs.
    assert float(numbers["witness-x2-first"]) * float(numbers["witness-x2-second"]) < 0
    assert float(numbers["witness-a-first"]) * float(numbers["witness-a-second"]) < 0


def test_only_the_complete_state_predicts_a_held_out_start(results):
    _, found = results
    numbers = found["numbers"]

    assert float(numbers["one-mass-held-out"]) > 1.0
    assert float(numbers["two-mass-held-out"]) < 1e-2
    assert float(numbers["two-mass-held-out"]) * 100 < float(
        numbers["one-mass-held-out"]
    )
