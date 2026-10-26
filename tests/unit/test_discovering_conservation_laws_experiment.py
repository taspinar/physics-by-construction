"""The experiment of "Discovering conservation laws and invariants"
(agents-llm 11)."""

import itertools
from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.mechanics.experiments.discovering_conservation_laws"
PAGE = "agents-llm/11-discovering-conservation-laws"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("discovering_conservation_laws")
    return directory, run_entry_point(MODULE, directory)


def _rows(found: dict, name: str) -> list[list[str]]:
    return found["tables"][name]["rows"]


def _verdicts(found: dict, name: str) -> list[str]:
    return [row[-1] for row in _rows(found, name)]


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_test_system_shows_the_artefacts_and_the_true_invariants(results):
    _, found = results
    assert _verdicts(found, "test-system") == [
        "integration artefact",
        "integration artefact",
        "invariant",
        "invariant",
    ]


def test_the_axis_starts_give_only_rejected_candidates(results):
    _, found = results
    verdicts = set(_verdicts(found, "coincidences"))
    assert verdicts == {"coincidence", "integration artefact"}


def test_the_agent_and_the_baseline_recover_both_invariants_of_the_box(results):
    _, found = results
    numbers = found["numbers"]
    assert (numbers["found"], numbers["known"], numbers["outcome"]) == (
        "2",
        "2",
        "recovered",
    )
    assert _verdicts(found, "agent-verdicts") == ["invariant", "invariant"]
    assert _verdicts(found, "box-baseline") == ["invariant", "invariant"]
    # The agent's energy converges at the order of velocity Verlet.
    assert 3.5 < float(numbers["energy-factor"]) < 4.5


def test_the_symmetry_test_tells_the_two_systems_apart(results):
    _, found = results
    rows = {row[0]: row[1] for row in _rows(found, "symmetry")}
    assert rows["the box of the agent"] == "below 1e-12"
    assert float(rows["the test oscillator"]) > 0.1


def test_the_top_has_four_invariants_and_one_identity(results):
    _, found = results
    rows = _rows(found, "top")
    assert sorted(_verdicts(found, "top")) == ["identity"] + ["invariant"] * 4
    assert {row[0] for row in rows} >= {"Lz", "L·e3", "(L·e3)²", "e3x² + e3y² + e3z²"}


def test_burgers_keeps_the_total_and_loses_the_square_only_after_the_shock(results):
    _, found = results
    rows = _rows(found, "burgers")
    assert all(row[1] == row[3] == "below 1e-12" for row in rows)
    before = [float(row[2]) for row in rows]
    after = [float(row[4]) for row in rows]
    # Before the shock the loss halves with the cells; after it, it does not.
    for coarse, fine in itertools.pairwise(before):
        assert fine == pytest.approx(coarse / 2, rel=0.15)
    assert after[-1] > 0.8 * after[0] > 0.04
