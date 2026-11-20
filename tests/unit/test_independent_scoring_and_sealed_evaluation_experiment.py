"""The experiment of "Independent scoring, sealed evaluation, and provenance"
(agents-llm 22, AE4): the cases of the pilot's tests and the sealed split, as
the page states them."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.mechanics.experiments.independent_scoring_and_sealed_evaluation"
PAGE = "agents-llm/22-independent-scoring-and-sealed-evaluation"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("independent_scoring")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_a_fabricated_report_disagrees_and_its_claim_fails(results):
    _, found = results
    rows = {r[0]: r for r in found["tables"]["ae4-scoring"]["rows"]}
    plain = rows["plain-projectile"]
    assert (plain[2], plain[3], plain[4]) == ("no", "0.001", "disagrees")
    assert float(plain[1]) > float(found["numbers"]["tolerance"])
    assert found["numbers"]["plain-claim-status"] == "failed"
    assert rows["projectile-full"][2] == rows["grid + least squares"][2] == "yes"


def test_the_contract_records_or_refuses_each_change(results):
    _, found = results
    rows = dict(found["tables"]["ae4-tampering"]["rows"])
    assert rows["readings edited before the evaluation"] == (
        "attempt invalid; claim failed"
    )
    assert rows["fixture edited after the evaluation"].endswith("claim not evaluated")
    assert rows["candidate changed between freeze and final evaluation"].startswith(
        "refused: projectile-full changed after it was frozen"
    )
    assert rows["a second final evaluation in the same cycle"].startswith(
        "refused: projectile-full already had its final evaluation"
    )
    assert rows["a change after the final evaluation, as a new cycle"] == (
        "version 1, cycle 1, invalidated; version 2, cycle 2, valid"
    )


def test_the_frozen_candidate_is_worse_on_the_sealed_split_yet_within_tolerance(
    results,
):
    _, found = results
    numbers = found["numbers"]
    assert numbers["selected"] == "told the form"
    development = float(numbers["selected-development"])
    error = float(numbers["selected-sealed"])
    assert development < error <= float(numbers["sealed-tolerance"])
    rows = found["tables"]["ae4-sealed"]["rows"]
    assert [r[4] for r in rows].count("not evaluated") == 2
