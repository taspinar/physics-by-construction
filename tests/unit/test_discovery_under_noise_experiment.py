"""The experiment of "Scientific discovery under measurement noise" (agents-llm 18)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

from pbc.discovery.noise_lab import BASELINES

MODULE = "pbc.mechanics.experiments.discovery_under_noise"
PAGE = "agents-llm/18-discovery-under-noise"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("discovery_under_noise")
    return directory, run_entry_point(MODULE, directory)


def _rows(found: dict, name: str) -> dict[str, list[str]]:
    return {row[0]: row[1:] for row in found["tables"][name]["rows"]}


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_only_the_calibrated_robust_fit_survives_the_faulty_gauge(results):
    _, found = results
    for name, row in _rows(found, "d10-baselines").items():
        assert (row[-1] == "yes") == ("calibrated robust fit" in name)
    assert found["numbers"]["outcome"] == "recovered"


def test_each_failure_needs_its_remedy(results):
    _, found = results
    failures = _rows(found, "d10-failures")
    assert all("recovered" in cell for cell in (r[-1] for r in failures.values()))
    assert "fails" in failures["noise and offset"][0]
    assert "recovered" in failures["noise and offset"][2]
    assert "fails" in failures["noise and faulty readings"][2]


def test_the_calibrated_fit_degrades_with_the_noise(results):
    _, found = results
    rows = [
        r
        for r in found["tables"]["d10-degradation"]["rows"]
        if r[0] == "grid + calibrated robust fit"
    ]
    medians = [float(r[2]) for r in rows]
    assert medians == sorted(medians)
    assert rows[0][-1] == "5 of 5" and rows[-1][-1] == "0 of 5"


def test_the_calibrated_fit_on_random_settings_degrades_like_on_the_grid(results):
    _, found = results
    table = found["tables"]["d10-degradation"]["rows"]
    random = [r for r in table if r[0] == "random + calibrated robust fit"]
    grid = [r for r in table if r[0] == "grid + calibrated robust fit"]
    assert [r[-1] for r in random[:4]] == ["5 of 5"] * 4
    assert random[-1][-1] == "0 of 5"
    assert all(
        1.5 < float(r[2]) / float(g[2]) < 3 for r, g in zip(random, grid, strict=True)
    )
    assert {r[0] for r in table} == {f"{design} + {name}" for design, name in BASELINES}
