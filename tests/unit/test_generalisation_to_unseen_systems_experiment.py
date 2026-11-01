"""The experiment of "Generalisation to unseen physical systems" (agents-llm 20)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.mechanics.experiments.generalisation_to_unseen_systems"
PAGE = "agents-llm/20-generalisation-to-unseen-systems"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("generalisation_to_unseen_systems")
    return directory, run_entry_point(MODULE, directory)


def _rows(found: dict, name: str) -> dict[str, list[str]]:
    return {row[0]: row[1:] for row in found["tables"][name]["rows"]}


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_trace_never_probed_a_held_out_world(results):
    _, found = results
    assert found["numbers"]["probes-inside"] == "yes"
    assert found["numbers"]["probes-on-held-out"] == "0"
    for world, row in _rows(found, "d12-never-probed").items():
        assert row[-1] == "0" and float(row[-2]) > 0
        assert row[1] == ("no" if world == "interpolation" else "yes")


def test_every_claim_fails_the_closer_world_and_the_agent_passes_the_others(results):
    _, found = results
    assert found["numbers"]["outcome"] == "recovered"
    for row in _rows(found, "d12-suite").values():
        assert float(row[-1]) > 0.05
    assert all(float(e) <= 0.05 for e in _rows(found, "d12-suite")["agent"][:-1])


def test_the_orbits_amplify_the_agents_error_of_the_strength(results):
    _, found = results
    rows = _rows(found, "d12-sensitivity")
    assert len(rows) == 3
    assert all(float(claimed) > 1 for claimed, _ in rows.values())
    assert min(float(square) for _, square in rows.values()) < 1
