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


def test_the_known_law_fails_and_so_does_a_missing_constant_force(results):
    _, found = results
    numbers = found["numbers"]
    (stokes, *s), (force, *f) = found["tables"]["known-law"]["rows"]

    assert stokes == "Stokes' law" and s[3] == "no"
    assert force == "a missing constant force" and f[3] == "no"
    # The residuals are systematic: light spheres fast, heavy ones slow.
    assert float(numbers["residual-light"]) > 2
    assert float(numbers["residual-heavy"]) < 0
    assert float(numbers["reynolds-least"]) < float(numbers["reynolds-most"]) < 1


def test_two_extensions_fit_the_record_and_the_chosen_sphere_rejects_one(results):
    _, found = results
    numbers = found["numbers"]
    record = {row[0]: row for row in found["tables"]["extensions-record"]["rows"]}
    after = {row[0]: row for row in found["tables"]["extensions-after"]["rows"]}

    for name in ("quadratic drag", "power-law drag"):
        assert record[name][4] == "yes" and record[name][5] == "yes"
    # The heaviest sphere the lab owns, where the fits part by many sigmas.
    assert float(numbers["chosen-weight"]) == pytest.approx(11.0, abs=0.05)
    assert float(numbers["chosen-apart"]) > 10
    assert numbers["faster-extension"] == "power-law drag"
    assert after["power-law drag"][4] == "no"
    assert after["quadratic drag"][4] == "yes"
    assert numbers["survivors"] == (
        "quadratic drag and quadratic drag and a constant force"
    )


def test_the_remaining_ambiguity_is_a_bounded_force_and_the_world_is_oseens(results):
    _, found = results
    numbers = found["numbers"]

    low, high = float(numbers["force-low"]), float(numbers["force-high"])
    assert low < 0 < high
    assert numbers["force-excludes-zero"] == "includes"
    assert float(numbers["force-share"]) == pytest.approx(
        100 * max(abs(low), abs(high)) * 1e-6 / 1e-4, abs=0.1
    )
    assert float(numbers["quadratic-ratio"]) == pytest.approx(1.0, abs=0.1)
