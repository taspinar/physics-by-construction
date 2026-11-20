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


def test_the_thermal_law_transfers_to_three_levels_and_fails_two(results):
    _, found = results
    numbers = found["numbers"]
    rows = {row[0]: row for row in found["tables"]["thermal-transfer"]["rows"]}
    tolerance = float(numbers["thermal-tolerance"])

    assert [row[1] for row in rows.values()] == [
        "interpolation",
        "new excitation",
        "new parameters",
        "new regime",
        "another structure",
    ]
    assert {row[2] for row in rows.values()} == {"never"}
    assert numbers["thermal-probed-worlds"] == "none"
    assert numbers["thermal-in-bounds"] == "all"
    for name in ("interpolation", "oscillating air", "cold room"):
        assert float(rows[name][4]) < tolerance / 10 and rows[name][5] == "yes"
    for name in ("hot start", "sheathed sphere"):
        assert float(rows[name][4]) > tolerance and rows[name][5] == "no"
    assert numbers["thermal-failed"] == "hot start and sheathed sphere"
    # The figure's text: the sheathed sphere's bar is the longest.
    assert float(rows["sheathed sphere"][4]) == max(float(r[4]) for r in rows.values())
    assert numbers["thermal-passed"] == "interpolation, oscillating air, cold room"
    assert float(numbers["thermal-largest-passed"]) == pytest.approx(
        max(
            float(rows[n][4]) for n in ("interpolation", "oscillating air", "cold room")
        ),
        rel=0.5,
    )


def test_the_thermal_law_is_consistent_and_radiation_explains_the_hot_failure(
    results,
):
    _, found = results
    numbers = found["numbers"]
    dof = int(numbers["thermal-dof"])

    assert float(numbers["thermal-chi2"]) < dof + 3 * (2 * dof) ** 0.5
    assert int(numbers["thermal-probes"]) == int(numbers["thermal-budget"])
    assert float(numbers["radiation-share-probed"]) < 5
    assert float(numbers["radiation-share-hot"]) > 3 * float(
        numbers["radiation-share-probed"]
    )
    # The sheathed sphere's nearest probed start is its own start.
    assert found["tables"]["thermal-transfer"]["rows"][-1][3] == "0"
