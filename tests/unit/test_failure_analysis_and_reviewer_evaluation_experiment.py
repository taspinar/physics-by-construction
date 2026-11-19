"""The experiment of "Failure analysis, reviewer evaluation, and regressions"
(agents-llm 24, AE6): the sessions, causes, rules, and regressions as the
page states them."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.mechanics.experiments.failure_analysis_and_reviewer_evaluation"
PAGE = "agents-llm/24-failure-analysis-and-reviewer-evaluation"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("reviewer_evaluation")
    return directory, run_entry_point(MODULE, directory)


def _cases(found) -> dict[str, list[str]]:
    return {row[1]: row[3:] for row in found["tables"]["ae6-cases"]["rows"]}


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_numerics_sessions_miss_only_the_energy_fault(results):
    _, found = results
    for name, outcomes in _cases(found).items():
        numerics = outcomes[2:]
        expected = "MISSED" if name == "explicit Euler as symplectic" else None
        assert all((o == "MISSED") == (expected == "MISSED") for o in numerics), name
        assert "FALSE ALARM" not in numerics


def test_the_physics_sessions_disagree_on_the_fourth_order_pieces_only(results):
    _, found = results
    cases = _cases(found)
    differ = {name for name, o in cases.items() if o[0] != o[1]}
    assert differ == {"rk4 with equal weights", "Runge-Kutta 4"}
    assert cases["Runge-Kutta 4"][0] == "FALSE ALARM"
    assert found["numbers"]["physics-agreement"] == "6"
    assert found["numbers"]["numerics-agreement"] == "8"


def test_no_session_accepted_a_piece_after_a_failing_check_that_applies(results):
    _, found = results
    causes = found["tables"]["ae6-causes"]["rows"]
    assert all("a failing check was run" not in row[3] for row in causes)
    alarms = [row for row in causes if row[2] == "false alarm"]
    assert [row[3] for row in alarms] == [
        "a check failed that the claim does not include"
    ]


def test_the_rules_and_ablations(results):
    _, found = results
    rules = {row[0]: (row[1], row[2]) for row in found["tables"]["ae6-rules"]["rows"]}
    assert rules["the contract's rule, both reviewers"] == ("0 of 5", "0 of 3")
    assert rules["AI4's rule, both reviewers"] == ("0 of 5", "1 of 3")
    assert rules["the contract's rule, physics only"][0] == "3 of 5"
    assert rules["the contract's rule, numerics only"][0] == "1 of 5"
    numbers = found["numbers"]
    assert numbers["overfit-ai4-wrong"] == "0"
    assert (numbers["overfit-missed"], numbers["overfit-false"]) == ("3", "1")


def test_both_regressions_are_detected(results):
    _, found = results
    assert found["numbers"]["code-regression"].startswith(
        "step 2, tool check_convergence_order"
    )
    (row,) = found["tables"]["ae6-regressions"]["rows"]
    assert row[1:] == ["Runge-Kutta 4", "correct acceptance", "false alarm", "yes"]
