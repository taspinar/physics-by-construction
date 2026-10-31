"""The experiment of "Hidden forces and unobserved variables" (agents-llm 19)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.mechanics.experiments.hidden_variables"
PAGE = "agents-llm/19-hidden-variables"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("hidden_variables")
    return directory, run_entry_point(MODULE, directory)


def _rows(found: dict, name: str) -> dict[str, list[str]]:
    return {row[0]: row[1:] for row in found["tables"][name]["rows"]}


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_record_is_ambiguous_and_the_experiment_resolves_it(results):
    _, found = results
    assert all(row[2] == "yes" for row in _rows(found, "d11-record").values())
    resolved = _rows(found, "d11-resolved")
    assert [h for h, row in resolved.items() if row[2] == "yes"] == [
        "a hidden force and drag"
    ]
    assert float(found["numbers"]["chosen-spread"]) > 10 * float(
        found["numbers"]["record-spread"]
    )


def test_the_agent_recovers_and_its_readings_need_both_effects(results):
    _, found = results
    assert found["numbers"]["outcome"] == "recovered"
    readings = _rows(found, "d11-agent-readings")
    assert [h for h, row in readings.items() if row[2] == "yes"] == [
        "a hidden force and drag"
    ]
