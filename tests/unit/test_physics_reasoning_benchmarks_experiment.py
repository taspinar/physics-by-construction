"""The experiment of "Physics reasoning benchmarks" (agents-llm 21, EV1)."""

from collections import Counter
from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.mechanics.experiments.physics_reasoning_benchmarks"
PAGE = "agents-llm/21-physics-reasoning-benchmarks"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("physics_reasoning_benchmarks")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_both_pictures_are_drawn_again(results):
    directory, _ = results
    for label in "ab":
        assert (directory / f"fig-picture-{label}.png").stat().st_size > 0


def test_every_second_route_agrees_closely(results):
    _, found = results
    rows = found["tables"]["ev1-checks"]["rows"]
    assert len(rows) == 5
    assert all(float(row[2]) < 1e-3 for row in rows)


def test_the_failures_are_reasoning_and_one_run_holds_four(results):
    # The page: every failure is one of reasoning, four are in one run, and
    # no problem in words and no visual affordance failed.
    _, found = results
    numbers = found["numbers"]
    assert numbers["refused"] == "0"
    assert numbers["unanswered"] == "0"
    failures = found["tables"]["ev1-failures"]["rows"]
    assert len(failures) == int(numbers["wrong"]) == 5
    assert {row[5] for row in failures} == {"reasoning"}
    assert max(Counter(row[0] for row in failures).values()) == 4
    assert not {row[2] for row in failures} & {"problem", "visual affordance"}


def test_the_misread_period_is_twice_the_true_one():
    from pbc.agents import reasoning_benchmark as benchmark
    from pbc.mechanics.experiments import physics_reasoning_benchmarks as experiment

    scored = experiment.scored_runs(experiment.replay_fixtures(experiment.LESSON))
    by_number = {o.item.number: o for o in scored[3]}
    assert by_number[10].answer == pytest.approx(
        2 * benchmark.oscillator_period(), rel=1e-3
    )
    ruler = {o.item.number: o for o in scored[2]}[8]
    assert ruler.answer / ruler.truth == pytest.approx(4.0, rel=0.01)


def test_the_spread_is_over_seeds_and_guessing_is_far_below(results):
    _, found = results
    rows = {row[0]: row for row in found["tables"]["ev1-spread"]["rows"]}
    assert set(rows) == {
        "problem",
        "visual affordance",
        "tool affordance",
        "counterfactual",
        "all",
    }
    assert rows["problem"][1] == rows["visual affordance"][1] == "100"
    assert float(rows["all"][3]) < float(rows["all"][1]) <= float(rows["all"][4])
    assert float(rows["all"][5]) < float(rows["all"][3])
