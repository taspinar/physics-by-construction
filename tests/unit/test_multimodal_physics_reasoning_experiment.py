"""The experiment of "Reading physics from pictures" (agents-llm 14, AI6)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.mechanics.experiments.multimodal_physics_reasoning"
PAGE = "agents-llm/16-multimodal-physics-reasoning"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("multimodal_physics_reasoning")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_four_pictures_are_drawn_again(results):
    directory, _ = results
    for label in "abcd":
        assert (directory / f"fig-picture-{label}.png").stat().st_size > 0


def test_the_runs_are_scored_as_recorded(results):
    _, found = results
    assert found["numbers"]["correct-pictures"] == "11"
    assert found["numbers"]["correct-text"] == "11"
    rows = found["tables"]["ai6-answers"]["rows"]
    assert len(rows) == 11
    assert all(row[4] == "yes" and row[6] == "yes" for row in rows)


def test_chance_is_far_below_both_runs(results):
    _, found = results
    tally = {row[0]: row[-1] for row in found["tables"]["ai6-tally"]["rows"]}
    assert float(tally["uniform guessing (expected)"]) < 3


def test_the_pictures_bring_every_reading_closer():
    from pbc.agents.multimodal_lab import key
    from pbc.mechanics.experiments import multimodal_physics_reasoning as experiment

    distances = experiment.readings(
        experiment.replay_fixtures(experiment.LESSON), key()
    )
    assert set(distances["pictures"]) == {4, 5, 6, 11}
    for number, seen in distances["pictures"].items():
        assert seen < distances["text"][number]


def test_the_runs_part_only_at_a_stricter_tolerance(results):
    _, found = results
    rows = found["tables"]["ai6-stricter"]["rows"]
    assert rows[0][1] == rows[0][2] == rows[0][3]
    assert int(rows[-1][1]) > int(rows[-1][2])
