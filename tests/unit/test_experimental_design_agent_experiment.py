"""The experiment of "An experimental design agent" (agents-llm 04)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

from pbc.mechanics.experiments import design_strategies as strategies

MODULE = "pbc.mechanics.experiments.experimental_design_agent"
PAGE = "agents-llm/04-an-experimental-design-agent"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("experimental_design_agent")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_a_spread_of_start_speeds_is_the_best_design_by_far(results):
    _, found = results
    lines = found["outputs"]["three-designs"].splitlines()
    threshold = float(lines[-1].split(": ")[1])
    low, times, speeds = (float(line.rsplit("score ", 1)[1]) for line in lines[:-1])

    assert low < threshold
    assert speeds > 10 * max(low, times, threshold)


def test_a_fifth_reading_raises_the_score(results):
    _, found = results
    four, five = (
        float(line.split()[1])
        for line in found["outputs"]["a-fifth-reading"].splitlines()
    )

    assert five > four


def test_the_four_strategies_are_compared_by_the_evaluator_over_seeds(results):
    _, found = results
    numbers = found["numbers"]
    rows = found["tables"]["strategies"]["rows"]
    shared = {row[0]: row for row in rows[:4]}
    more = {row[0]: row for row in rows[4:]}

    assert [row[0] for row in rows] == [
        "scripted",
        "adaptive",
        "LLM",
        "hybrid",
        "scripted",
        "adaptive",
    ]
    assert {row[1] for row in shared.values()} == {numbers["strategy-seeds"]}
    assert {row[1] for row in more.values()} == {numbers["more-seeds"]}
    assert numbers["attempts"] == str(4 * 5 + 2 * 35)
    assert numbers["not-completed"] == "0"
    assert numbers["invalidated"] == "0"
    for name in ("scripted", "adaptive", "llm", "hybrid"):
        key = "LLM" if name == "llm" else name
        assert numbers[f"correct-{name}"] == shared[key][2]
    assert numbers["correct-scripted-more"] == more["scripted"][2]
    assert numbers["correct-adaptive-more"] == more["adaptive"][2]


def test_the_intervals_overlap_and_the_mean_margins_order_the_strategies(results):
    _, found = results
    numbers = found["numbers"]
    rows = found["tables"]["strategies"]["rows"]
    shared, more = rows[:4], rows[4:]

    for key, lines in (("overlap-shared", shared), ("overlap-more", more)):
        assert numbers[key] == "overlap"
        assert max(float(r[3]) for r in lines) <= min(float(r[4]) for r in lines)
    by_mean = sorted(shared, key=lambda r: -float(r[5]))
    assert numbers["difference-order"] == ", ".join(r[0] for r in by_mean)
    means = {r[0]: float(r[5]) for r in shared}
    ratio = min(means["adaptive"], means["hybrid"]) / means["scripted"]
    assert float(numbers["margin-ratio"]) == pytest.approx(ratio, abs=0.06)
    assert float(numbers["margin-ratio"]) >= 2
    # A strategy correct at every seed and one correct at four of five.
    assert {r[2] for r in shared} == {"4", "5"}
    assert int(numbers["llm-readings-least"]) <= 8


def test_the_figure_text_matches_the_differences_of_the_strategies():
    # The caption, the alt text, and "the model's sessions lie between":
    # on average the adaptive rule and the hybrid highest, the scripted grid
    # lowest with one point below the threshold, the LLM between; every
    # point of the other three above the threshold.
    record = strategies.ledger(strategies.LESSON, strategies.MORE_SEEDS)
    found = strategies.summary(record, strategies.LESSON)
    shared = strategies.rows_by_strategy(found, strategies.SEEDS)
    points = strategies.differences(shared)
    means = {name: sum(v) / len(v) for name, v in points.items()}
    below = {
        name: sum(x < strategies.THRESHOLD for x in v) for name, v in points.items()
    }

    assert below == {"scripted": 1, "adaptive": 0, "LLM": 0, "hybrid": 0}
    assert means["scripted"] < means["LLM"] < min(means["adaptive"], means["hybrid"])
