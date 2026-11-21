"""The experiment of "An agent runs an experiment" (agents-llm 01)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.mechanics.experiments.agent_experiment"
PAGE = "agents-llm/01-an-agent-runs-an-experiment"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("agent_experiment")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_only_the_well_formed_call_runs(results):
    _, found = results
    outcomes = [row[3] for row in found["tables"]["misbehaving-calls"]["rows"]]

    assert outcomes[0] == "ran"
    assert all(outcome != "ran" for outcome in outcomes[1:])


def test_the_replay_runs_without_a_model_and_catches_a_changed_ball(results):
    _, found = results

    assert "This build did not call a model." in found["displays"]["run"]
    assert found["outputs"]["rough-ball"].strip()


def test_the_scan_confirms_the_agent_s_bracket(results):
    _, found = results
    numbers = found["numbers"]

    assert float(numbers["bracket-low"]) <= float(numbers["best-angle"])
    assert float(numbers["best-angle"]) <= float(numbers["bracket-high"])


def test_both_routes_meet_every_step_and_reach_the_same_answer(results):
    """The claims 'protocol-check' and 'two-routes' of the bounded part."""
    _, found = results
    checks = found["tables"]["protocol-check"]["rows"]
    assert [row[0] for row in checks] == [
        "time step",
        "search",
        "recovery",
        "budget",
        "stop",
    ]
    assert all(row[1] == "met" and row[3] == "met" for row in checks)
    routes = {row[0]: row[1:] for row in found["tables"]["two-routes"]["rows"]}
    assert routes["answer, degrees"][0] == routes["answer, degrees"][1]
    assert routes["time step chosen, s"][0] == routes["time step chosen, s"][1]
    assert int(routes["runs spent"][1]) == int(routes["runs spent"][0]) - 1
    distance = routes["distance from the best angle of a fine scan, degrees"]
    assert all(float(d) <= 1.0 for d in distance)


def test_the_agent_did_not_need_the_failed_run_and_the_script_repeated_it(results):
    _, found = results
    recovery = next(
        row for row in found["tables"]["protocol-check"]["rows"]
        if row[0] == "recovery"
    )  # fmt: skip
    assert "repeated 0 time(s)" in recovery[2]
    assert "repeated 1 time(s)" in recovery[4]


def test_the_small_budget_gives_no_answer(results):
    _, found = results
    assert found["numbers"]["small-budget-stopped"].endswith("no answer")
