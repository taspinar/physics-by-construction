"""The experiment of "Full, partial, and no prior knowledge under one protocol"
(agents-llm 06)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.mechanics.experiments.prior_knowledge_in_discovery"
PAGE = "agents-llm/06-prior-knowledge-in-discovery"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("prior_knowledge_in_discovery")
    return directory, run_entry_point(MODULE, directory)


def _rows(found: dict, name: str) -> dict[str, list[str]]:
    return {row[0]: row[1:] for row in found["tables"][name]["rows"]}


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_only_the_task_text_differs_between_the_conditions(results):
    _, found = results
    shared = _rows(found, "d2-fairness")

    assert shared.pop("task text") == ["differs"]
    assert all(value == ["same"] for value in shared.values())


def test_the_conditions_are_scored_as_they_are_and_every_run_had_the_information(
    results,
):
    _, found = results
    tolerance = float(found["numbers"]["tolerance"])
    scores = _rows(found, "d2-scores")
    fits = _rows(found, "d2-probe-fits")

    assert {c: row[-1] for c, row in scores.items()} == {
        "full": "recovered",
        "partial": "not recovered",
        "none": "not recovered",
    }
    assert {row[0] for row in scores.values()} == {found["numbers"]["probes"]}
    assert all(float(row[4]) <= tolerance for row in fits.values())


def test_the_phase_shift_grows_with_the_time(results):
    _, found = results
    shift = _rows(found, "phase-shift")

    assert float(shift["9"][0]) > 2 * float(shift["3"][0])


def _tank_rows(found: dict, name: str) -> dict[tuple[str, str], list[str]]:
    return {(r[0], r[1]): r[2:] for r in found["tables"][name]["rows"]}


def test_on_the_grid_both_conditions_recover_and_on_one_sphere_only_the_prior(results):
    _, found = results
    numbers = found["numbers"]
    rows = _tank_rows(found, "tank-conditions")
    tolerance = float(numbers["tank-tolerance"])

    for condition in ("knowledge-informed", "restricted prior"):
        _forms, _consistent, chosen, error, recovered = rows[("grid", condition)]
        assert chosen == "v^(2) d^(2)" and recovered == "yes", condition
        assert float(error) <= tolerance
    *_, chosen, error, recovered = rows[("one sphere", "knowledge-informed")]
    assert chosen == "v^(2) d^(2)" and recovered == "yes" and float(error) <= tolerance
    _forms, consistent, chosen, error, recovered = rows[
        ("one sphere", "restricted prior")
    ]
    # One consistent form per exponent of the diameter in the grammar.
    assert consistent == numbers["one-sphere-rivals"] == "9"
    assert chosen == numbers["one-sphere-chosen"] == "v^(2)"
    assert recovered == "no" and float(error) > tolerance
    assert float(numbers["one-sphere-error"]) == pytest.approx(float(error), abs=0.01)


def test_the_boundary_table_names_the_box_controls_and_observation(results):
    _, found = results
    from pbc.discovery.towing_tank import tank

    rows = dict(found["tables"]["tank-boundary"]["rows"])
    box = tank()
    for control in box.controls:
        assert f"{control.name} ({control.unit})" in rows["set by the experimenter"]
    assert rows["read"].startswith(f"{box.observation.name} ({box.observation.unit})")


def test_own_random_probes_recover_the_law(results):
    _, found = results
    numbers = found["numbers"]
    (row,) = found["tables"]["tank-own-probes"]["rows"]

    assert (
        row[1] == "restricted prior"
        and row[4] == numbers["own-chosen"] == "v^(2) d^(2)"
    )
    assert row[-1] == "yes" and numbers["own-outcome"] == "recovered"


def test_in_the_unknown_world_only_the_restricted_prior_makes_a_right_claim(results):
    _, found = results
    numbers = found["numbers"]
    rows = _tank_rows(found, "tank-unknown")

    informed = rows[("grid", "knowledge-informed")]
    assert informed[1] == "0" and informed[2] == "none" and informed[3] == "no claim"
    assert numbers["unknown-reason"].startswith("neither candidate is consistent")
    restricted = rows[("grid", "restricted prior")]
    assert restricted[2] == numbers["unknown-chosen"] == "v^(3/2) d^(3/2)"
    assert restricted[-1] == "yes"
