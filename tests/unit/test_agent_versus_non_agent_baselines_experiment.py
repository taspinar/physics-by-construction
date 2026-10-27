"""The experiment of "The agent against methods without one" (agents-llm 12,
EV3)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.mechanics.experiments.agent_versus_non_agent_baselines"
PAGE = "agents-llm/13-agent-versus-non-agent-baselines"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("agent_versus_non_agent_baselines")
    return directory, run_entry_point(MODULE, directory)


def _entries(found: dict) -> dict[tuple[str, str], list[str]]:
    rows = found["tables"]["ev3-entries"]["rows"]
    return {(row[0], row[1]): row[2:] for row in rows}


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_plain_model_has_the_agents_task_and_no_probe(results):
    _, found = results
    assert {row[1] for row in found["tables"]["ev3-inputs"]["rows"]} == {"same"}
    for (_, method), (allowed, spent, *_rest) in _entries(found).items():
        if method == "plain model":
            assert (allowed, spent) == ("0", "0")


def test_every_row_is_judged_against_the_agent_by_its_budget(results):
    _, found = results
    for (_, method), row in _entries(found).items():
        allowed, verdict = row[0], row[-1]
        if method == "agent":
            assert verdict == "-"
        elif allowed == found["numbers"]["budget"]:
            assert verdict == "comparable"
        else:
            assert verdict.startswith("not meaningful: budgets differ")


def test_the_tally_is_reported_as_it_is(results):
    _, found = results
    tally = {row[0]: row[1] for row in found["tables"]["ev3-tally"]["rows"]}
    assert tally["plain model"] == "0"
    assert tally["agent"] == "2"
    assert tally["grid + least squares"] == "3"
    assert tally["random + least squares"] == "3"
    assert tally["grid + sparse identification"] == "2"


def test_random_selection_with_few_probes_fails_on_some_seeds_of_the_spring(results):
    _, found = results
    seeds = {row[0]: row[2:] for row in found["tables"]["ev3-seeds"]["rows"]}
    recovered, total = map(int, seeds["oscillator"])
    assert 0 < recovered < total
