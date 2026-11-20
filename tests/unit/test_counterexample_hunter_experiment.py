"""The experiment of "A counterexample hunter" (agents-llm 02)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.mechanics.experiments.counterexample_hunter"
PAGE = "agents-llm/02-a-counterexample-hunter"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("counterexample_hunter")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_only_the_valid_experiment_runs(results):
    _, found = results
    lines = found["outputs"]["bounds"].splitlines()

    assert lines[0].startswith("a valid experiment: 0.")
    assert len(lines) == 7


def test_the_judge_decides_from_the_results_not_the_words(results):
    _, found = results
    said = found["outputs"]["what-the-agent-says"].splitlines()

    assert said[0].endswith("counterexample")
    assert not said[1].endswith(": counterexample")
    assert "counterexample" not in found["outputs"]["forged-results"].split(":")[1]


# --- Physical constraints (SA7). ---


def test_the_exact_motion_has_no_counterexample(results):
    _, found = results
    rows = {row[0]: row[1:] for row in found["tables"]["constraint-outcomes"]["rows"]}

    assert rows["exact motion"] == ["none found"] * 4


def test_each_check_finds_a_counterexample_to_a_wrong_candidate(results):
    _, found = results
    table = found["tables"]["constraint-outcomes"]
    rows = [row[1:] for row in table["rows"] if row[0] != "exact motion"]

    assert len(rows) == 4
    for column in range(4):
        assert "counterexample" in [row[column] for row in rows]


def test_the_witnesses_are_the_counterexamples_of_the_outcomes(results):
    _, found = results
    outcomes = found["tables"]["constraint-outcomes"]
    checks = outcomes["columns"][1:]
    expected = {
        (row[0], check)
        for row in outcomes["rows"]
        for check, outcome in zip(checks, row[1:], strict=True)
        if outcome == "counterexample"
    }
    witnesses = found["tables"]["constraint-witnesses"]["rows"]

    assert {(row[0], row[1]) for row in witnesses} == expected


def test_the_missing_root_at_a_unit_ratio_is_found_by_dimensions_alone(results):
    _, found = results
    assert found["numbers"]["unit-ratio-checks"] == "dimensions"


def test_the_exercise_candidate_fails_dimensions_and_limits(results):
    _, found = results
    rows = found["tables"]["constraint-exercise"]["rows"]

    assert [row[1] for row in rows] == ["dimensions", "limits"]
