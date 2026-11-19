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


A = "A: inverse square, gauge reads high"
B = "B: true gauge, shallower law"


def test_two_explanations_fit_the_same_readings_and_differ_beyond_them(results):
    _, found = results
    numbers = found["numbers"]
    rows = _rows(found, "explanations")
    chi2 = {name: float(row[1]) for name, row in rows.items()}

    # Both consistent with the readings ...
    assert rows[A][3] == rows[B][3] == "yes"
    # ... their chi-squares less than one apart, B the lower, though A is true.
    assert abs(chi2[A] - chi2[B]) < 1.0
    assert float(numbers["delta-chi2"]) == pytest.approx(
        abs(chi2[A] - chi2[B]), abs=0.01
    )
    assert chi2[B] < chi2[A]
    # Their laws part where nothing was probed: A within a percent, B far off.
    assert float(numbers["a-far-error"]) == pytest.approx(
        abs(float(rows[A][4])), abs=0.1
    )
    assert float(numbers["a-far-error"]) < 1.0
    assert float(numbers["b-far-error"]) > 15.0


def test_the_precise_exponent_of_b_is_far_from_the_truth(results):
    _, found = results
    numbers = found["numbers"]
    exponent = float(numbers["b-exponent"])
    error = float(numbers["b-exponent-error"])

    assert exponent < 2.0 and (2.0 - exponent) / error > 5
    assert int(numbers["b-exponent-off"]) == round((2.0 - exponent) / error)


def test_the_offset_is_correlated_and_its_interval_holds_both_explanations(results):
    _, found = results
    numbers = found["numbers"]

    assert float(numbers["correlation"]) > 0.9
    low, high = float(numbers["offset-low"]), float(numbers["offset-high"])
    a_offset = float(_rows(found, "explanations")[A][0].split("offset ")[1].split()[0])
    # Zero, B's offset, and A's fitted offset are both inside the interval.
    assert low < 0.0 < a_offset < high


def test_readings_at_zero_mass_reject_b_and_keep_a(results):
    _, found = results
    numbers = found["numbers"]
    rows = _rows(found, "separated")
    before = _rows(found, "explanations")

    assert rows[A][3] == "yes" and rows[B][3] == "no"
    assert float(numbers["null-chi2-rise"]) == pytest.approx(
        float(rows[B][1]) - float(before[B][1]), abs=1
    )
    assert numbers["null-readings"] == "2"
    assert f"offset {numbers['null-offset']}" in rows[A][0]
    # The measured offset holds the truth of the synthetic gauge within
    # two standard errors.
    offset, error = float(numbers["null-offset"]), float(numbers["null-offset-error"])
    assert abs(offset - float(numbers["truth-offset"])) < 2 * error


def test_more_of_the_same_readings_separate_them_only_slowly(results):
    _, found = results
    numbers = found["numbers"]
    rows = found["tables"]["more-of-the-same"]["rows"]

    # The predicted separating noise is below the lesson's noise.
    assert float(numbers["separating-noise"]) < float(numbers["sigma"])
    assert float(numbers["misfit"]) < float(numbers["margin"])
    first = next(int(r[0]) for r in rows if r[3] == "yes")
    assert (
        int(numbers["enough-readings"]) == first > 100 * int(numbers["null-readings"])
    )
    assert all(r[3] == "no" for r in rows if int(r[0]) < first)
