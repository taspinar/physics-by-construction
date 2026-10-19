"""The experiment of "Equations from noisy trajectories" (agents-llm 10, the
second lesson of D8)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.mechanics.experiments.equations_from_noisy_trajectories"
PAGE = "agents-llm/10-equations-from-noisy-trajectories"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("equations_from_noisy_trajectories")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_noise_moves_the_best_step_of_a_second_difference_up(results):
    _, found = results

    rows = found["tables"]["best-steps"]["rows"]
    steps = [float(row[1]) for row in rows]
    errors = [float(row[2]) for row in rows]
    assert steps == sorted(steps) and steps[0] < steps[-1]
    assert errors == sorted(errors)


def test_the_filter_tolerates_more_noise_and_both_fail_at_the_largest(results):
    _, found = results
    numbers = found["numbers"]

    assert float(numbers["filter-last"]) >= 10 * float(numbers["central-last"])
    last = found["tables"]["sweep"]["rows"][-1]
    assert last[1] == "0" and last[2] == "0"
    first = found["tables"]["sweep"]["rows"][0]
    assert first[1] == first[2] == "10"
    # The median coefficient error: central differences are the more accurate
    # at the smallest noise, cross the tolerance first, and the filter's error
    # sits at its window bias, under the tolerance, until the largest noise.
    errors = [(float(r[3]), float(r[4])) for r in found["tables"]["sweep"]["rows"]]
    assert errors[0][0] < errors[0][1] < 0.05 < errors[3][0]
    assert all(f < 0.05 for _, f in errors[:-1]) and errors[-1][1] > 0.05
    # At the first failing noise the acceleration's noise swamps its signal.
    assert float(numbers["central-drowned"]) > 5 * float(numbers["rms-acceleration"])
    assert "x^3" in numbers["loudest"]


def test_a_wide_window_fails_on_clean_data_by_its_bias(results):
    _, found = results
    numbers = found["numbers"]

    assert float(numbers["bias-window"]) < 5 < float(numbers["bias-wide"])
    by_window = {
        int(row[0]): [int(c) for c in row[2:]]
        for row in found["tables"]["windows"]["rows"]
    }
    assert by_window[41][0] == 10 and by_window[81][0] == 0
    # A narrow window fails at a smaller noise than the window of the lesson.
    assert sum(by_window[11]) < sum(by_window[41])


def test_faster_sampling_hurts_differences_and_not_the_filter(results):
    _, found = results

    first = [int(c) for c in found["tables"]["finer-sampling"]["rows"][0][1:]]
    assert first[0] > first[1]
    for row in found["tables"]["finer-sampling"]["rows"]:
        assert int(row[4]) >= int(row[3])
