"""The experiment of "Defining scientific quality" (agents-llm 21, AE1)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.mechanics.experiments.defining_scientific_quality"
PAGE = "agents-llm/21-defining-scientific-quality"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("defining_scientific_quality")
    return directory, run_entry_point(MODULE, directory)


def _profiles(found: dict) -> dict[tuple[str, str], list[str]]:
    return {(r[0], r[1]): r[2:] for r in found["tables"]["ae1-profiles"]["rows"]}


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_spring_failures_had_the_evidence_and_concluded_consistently(results):
    _, found = results
    profiles = _profiles(found)
    for condition in ("partial", "none"):
        correct, reasoning, evidence, completed, *_ = profiles[
            "oscillator", f"agent, {condition}"
        ]
        assert (correct, reasoning, evidence, completed) == ("no", "yes", "yes", "yes")


def test_the_plain_model_completes_and_has_nothing_to_weigh(results):
    _, found = results
    for (_, who), row in _profiles(found).items():
        if who == "plain model":
            assert row[:4] == ["no", "-", "-", "yes"]
            assert row[-1] == "-"


def test_refused_calls_and_informative_settings_are_measured_apart(results):
    _, found = results
    hidden = dict(found["tables"]["ae1-disagreements"]["rows"])
    assert hidden["refused calls, yet settings more informative than a grid"] == "3"
    # The claim names the three runs, and the spring's partial run, refused
    # as often as its full run, far below the grid.
    profiles = _profiles(found)
    named = [
        ("projectile", "agent, full"),
        ("projectile", "agent, partial"),
        ("oscillator", "agent, full"),
    ]
    for run in named:
        assert int(profiles[run][-2]) > 0, run
        assert float(profiles[run][-1]) > 1, run
    partial = profiles["oscillator", "agent, partial"]
    assert partial[-2] == profiles["oscillator", "agent, full"][-2]
    assert float(partial[-1]) < 0.5
    assert (
        hidden["the readings support a recovery, yet the claim is not correct"] == "2"
    )


def test_the_items_are_scored_by_kind(results):
    _, found = results
    rows = {r[0]: r[1:] for r in found["tables"]["ae1-items"]["rows"]}
    assert rows["reading"][1:3] == ["2", "0"]
    # With the pictures, every question of every kind is answered correctly.
    for kind, row in rows.items():
        assert row[1] == row[0], kind
    for kind in ("concept", "counterfactual"):
        assert rows[kind][1] == rows[kind][2] == rows[kind][0]
