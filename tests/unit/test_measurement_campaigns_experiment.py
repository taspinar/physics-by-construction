"""The experiment of "Running adaptive and resumable measurement campaigns"
(electromagnetism 12, slot SA6, Issue #580): every claim of the page is
asserted here as the page states it."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

from pbc.electromagnetism.campaign import RESUME_CHECKS

MODULE = "pbc.electromagnetism.experiments.measurement_campaigns"
PAGE = "electromagnetism/12-measurement-campaigns"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("measurement-campaigns")
    return directory, run_entry_point(MODULE, directory)


def rows(results, name):
    return results[1]["tables"][name]["rows"]


def value(results, name, quantity):
    return next(float(r[1]) for r in rows(results, name) if r[0] == quantity)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_campaign_agrees_with_the_closed_form_within_its_error(results):
    """Claim 'campaign-result': f0 within about one standard error of the
    repeats (here: within two), Q within a few parts in 1e5."""
    f0 = value(results, "campaign-result", "f0 of the campaign")
    error = value(results, "campaign-result", "its standard error, from the repeats")
    truth = value(results, "campaign-result", "f0 of the closed form")
    q_error = value(results, "campaign-result", "relative error of Q")
    assert results[1]["numbers"]["full-status"] == "complete"
    assert abs(f0 - truth) <= 1.0 * error
    assert abs(q_error) < 1e-4


def test_the_adaptive_campaign_beats_the_fixed_sweep_by_the_stated_factor(results):
    """Claim 'adaptive-vs-sweep': the same at the sweep, then more than a
    hundred times better at the compared count."""
    table = rows(results, "adaptive-vs-sweep")
    first = table[0]
    assert first[1] == first[2]
    at = next(r for r in table if r[0] == results[1]["numbers"]["compare-at"])
    assert float(at[2]) / float(at[1]) > 100


def test_every_invalid_resume_is_refused_by_its_own_check_and_reaches_nothing(
    results,
):
    """Claim 'refused-resumes'."""
    table = rows(results, "refused-resumes")
    assert [r[1] for r in table] == list(RESUME_CHECKS)
    assert all(r[3] == "0" for r in table)


def test_the_interrupted_segment_is_recorded_incomplete_with_the_output_off(results):
    numbers = results[1]["numbers"]
    assert numbers["first-status"] == "interrupted"
    assert numbers["first-output"] == "off"
    ledger = rows(results, "ledger")
    assert [(r[0], r[1], r[2]) for r in ledger] == [
        ("segment-1", "inconclusive", ""),
        ("segment-2", "completed", "segment-1"),
    ]
    assert "not kept" in ledger[0][3]


def test_the_resume_agrees_within_the_combined_error_at_the_same_frequencies(
    results,
):
    """Claim 'resumed-vs-uninterrupted'."""
    table = {r[0]: r[1:] for r in rows(results, "resumed-vs-uninterrupted")}
    numbers = results[1]["numbers"]
    assert table["taken from the checkpoint"][1] == numbers["first-measurements"]
    assert table["at the same frequencies as uninterrupted"] == [
        numbers["measurements"],
        numbers["measurements"],
    ]
    assert float(numbers["f0-difference"]) < float(numbers["f0-combined-error"])
    assert table["f0 (Hz)"][0] != table["f0 (Hz)"][1]  # new noise, not a replay


def test_the_suggestion_from_the_lost_measurement_is_refused(results):
    assert "m12, which the campaign did not make" in results[1]["outputs"]["lost-basis"]


def test_more_repeats_shrink_the_standard_error(results):
    three, ten = rows(results, "more-repeats")
    assert float(ten[2]) < float(three[2])
