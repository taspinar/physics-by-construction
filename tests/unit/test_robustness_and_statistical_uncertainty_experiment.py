"""The experiment of "Robustness and statistical uncertainty" (agents-llm 23,
AE5): the trials, rates, and claims as the page states them."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.mechanics.experiments.robustness_and_statistical_uncertainty"
PAGE = "agents-llm/23-robustness-and-statistical-uncertainty"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("robustness")
    return directory, run_entry_point(MODULE, directory)


def _interval(text: str) -> tuple[float, float]:
    low, high = text.split(" to ")
    return float(low), float(high)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_counts_by_variant(results):
    _, found = results
    recovered = {}
    for variant, *_, ok, _p, _f, _r, _m, _c in found["tables"]["ae5-trials"]["rows"]:
        recovered.setdefault(variant, []).append(ok == "yes")
    assert {v: (sum(r), len(r)) for v, r in recovered.items()} == {
        "repeated": (4, 4),
        "noisier": (1, 3),
        "failing": (2, 3),
    }


def test_every_failure_claimed_the_one_rounded_value_outside_the_tolerance(results):
    _, found = results
    trials = found["tables"]["ae5-trials"]["rows"]
    failing = {row[2] for row in trials if row[4] == "no"}
    assert failing == {found["numbers"]["claims-failing"]}
    claims = {row[0]: row[3] for row in found["tables"]["ae5-claims"]["rows"]}
    assert [value for value, ok in claims.items() if ok == "no"] == list(failing)


def test_the_failing_instrument_failed_calls_in_every_trial(results):
    _, found = results
    for row in found["tables"]["ae5-trials"]["rows"]:
        failed = int(row[6])
        assert (failed > 0) == (row[0] == "failing")


def test_every_agent_interval_overlaps_the_baselines(results):
    _, found = results
    rows = found["tables"]["ae5-rates"]["rows"]
    for variant in ("repeated", "noisier", "failing"):
        mine = [_interval(r[3]) for r in rows if r[0] == variant]
        agent, *baselines = mine
        for low, high in baselines:
            assert agent[0] <= high and low <= agent[1]
    assert found["numbers"]["repeated-low"] == "0.40"
