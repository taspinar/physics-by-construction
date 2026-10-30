"""The experiment of "Discovering gravity from experiments" (agents-llm 14)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.mechanics.experiments.discovering_gravity"
PAGE = "agents-llm/14-discovering-gravity"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("discovering_gravity")
    return directory, run_entry_point(MODULE, directory)


def _rows(found: dict, name: str) -> dict[str, list[str]]:
    return {row[0]: row[1:] for row in found["tables"][name]["rows"]}


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_every_baseline_and_the_agent_pass_the_transfer(results):
    _, found = results
    for row in _rows(found, "d4-baselines").values():
        assert row[-2:] == ["yes", "yes"]
    assert found["numbers"]["outcome"] == "recovered"
    assert _rows(found, "d4-score")["outcome"] == ["recovered"]


def test_the_claim_lies_within_two_standard_errors_of_the_agents_readings(results):
    _, found = results
    for row in _rows(found, "d4-agent-readings").values():
        assert abs(float(row[-1])) < 2
    assert found["numbers"]["agent-fit-consistent"] == "yes"


def test_the_orbits_are_most_sensitive_to_the_power_of_the_source_mass(results):
    _, found = results
    spread = {p: float(row[-1]) for p, row in _rows(found, "d4-scan").items()}
    assert spread["source_power"] > 5 * spread["G"]
    assert all(float(row[2]) <= 0.05 for row in _rows(found, "d4-scan").values())
    far = found["tables"]["far-shifts"]["rows"]
    assert [row[-1] for row in far] == ["yes", "yes", "no", "no"]
