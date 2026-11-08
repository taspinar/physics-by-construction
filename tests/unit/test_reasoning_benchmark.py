"""The physics reasoning benchmark of EV1: items drawn from the seed, every
answer computed by its lesson's code and checked by a second route, the one
software tool, and the score that keeps interface and reasoning apart."""

import math

import pytest

from pbc.agents import ModelMessage, ToolCall, run
from pbc.agents import reasoning_benchmark as benchmark
from pbc.agents.reasoning_benchmark import (
    KINDS,
    RECORDED_KEY,
    SEEDS,
    WHOLE,
    chance,
    checks,
    items,
    key,
    outcome,
    periods_to_time,
    sheet,
    spread,
    task,
)


class _Scripted:
    model = "scripted"
    secrets = ()

    def __init__(self, *messages):
        self._messages = list(messages)

    def complete(self, system, conversation, tools):
        return self._messages.pop(0)


def _call(number, item, value):
    return ToolCall(f"c{number}", "answer", {"question": item, "value": value})


@pytest.mark.parametrize("seed", SEEDS)
def test_every_seed_has_twelve_items_of_the_four_kinds(seed):
    found = items(seed)
    assert [item.number for item in found] == list(range(1, 13))
    assert {item.kind for item in found} == set(KINDS)
    assert all(item.picture for item in found if item.kind != "problem")
    assert not any(item.picture for item in found if item.kind == "problem")


def test_the_seed_changes_the_numbers_of_the_items():
    assert len({task(seed) for seed in SEEDS}) == len(SEEDS)
    assert task(1) == task(1)


@pytest.mark.parametrize("seed", SEEDS)
def test_every_second_route_agrees_with_the_lesson_code(seed):
    found = checks(seed)
    assert set(found) >= {1, 2, 3, 4, 10, 11}
    for solved, verified in found.values():
        assert verified == pytest.approx(solved, rel=benchmark.CHECK_TOLERANCE)


@pytest.mark.parametrize("seed", SEEDS)
def test_the_key_is_the_one_the_runs_were_recorded_against(seed):
    recorded = RECORDED_KEY[seed]
    for number, truth in key(seed).items():
        assert truth == pytest.approx(recorded[number], rel=1e-5)


@pytest.mark.parametrize("seed", SEEDS)
def test_a_choice_key_names_an_option_and_a_number_lies_in_its_range(seed):
    truths = key(seed)
    for item in items(seed):
        truth = truths[item.number]
        if item.options:
            assert truth in range(1, len(item.options) + 1)
        else:
            assert item.low <= truth <= item.high


def test_the_stopwatch_answer_does_not_hang_on_the_reading():
    period = benchmark.oscillator_period()
    for error, precision in benchmark.robust_stopwatches():
        expected = periods_to_time(error, precision, period)
        for factor in (0.95, 1.05):
            assert periods_to_time(error, precision, factor * period) == expected
    # the precision is met with that many periods and not with one fewer
    assert periods_to_time(0.2, 1.0, math.pi) == 7


def test_the_period_does_not_depend_on_the_amplitude():
    period = benchmark.oscillator_period()
    for amplitude in (0.5, 1.0, 3.0):
        assert benchmark.measured_period(amplitude) == pytest.approx(period, rel=1e-4)


def test_a_heavier_ball_throws_best_closer_to_45_degrees():
    light = benchmark.best_throw(0.5 * benchmark.throw.mass)[0]
    angle = benchmark.best_throw()[0]
    heavy = benchmark.best_throw(2.0 * benchmark.throw.mass)[0]
    assert light < angle < heavy < 45.0


def test_the_tool_says_nothing_about_the_truth():
    allowlist = sheet(1)
    (spec,) = allowlist.specs()
    assert spec.name == "answer"
    transcript = run(
        _Scripted(ModelMessage("", (_call(1, 1, 41.0),)), ModelMessage("done")),
        allowlist,
        benchmark.SYSTEM,
        task(1),
        benchmark.MAX_STEPS,
    )
    (result,) = transcript.steps[0].results
    assert result.ok
    assert dict(result.content) == {"question": 1, "recorded": 1}


def test_the_score_keeps_interface_failures_apart_from_reasoning_failures():
    seed = 1
    truths = key(seed)
    found = items(seed)
    right = truths[1]
    transcript = run(
        _Scripted(
            ModelMessage(
                "",
                (
                    _call(1, 1, right),
                    _call(2, 2, 2.0 * truths[2]),  # wrong: a reasoning failure
                    _call(3, 5, 7),  # option 7 does not exist: refused
                    ToolCall("c4", "answer", {"question": 6}),  # no value: refused
                ),
            ),
            ModelMessage("done"),
        ),
        sheet(seed),
        benchmark.SYSTEM,
        task(seed),
        benchmark.MAX_STEPS,
    )
    scored = {o.item.number: o for o in outcome(found, truths, transcript)}
    assert scored[1].verdict == "correct"
    assert scored[2].verdict == "wrong"
    assert scored[5].verdict == "unanswered" and scored[5].refused == 1
    assert scored[6].verdict == "unanswered" and scored[6].refused == 1
    assert scored[7].verdict == "unanswered" and scored[7].refused == 0


def test_a_whole_number_must_be_exact_and_a_reading_within_its_tolerance():
    by_number = {item.number: item for item in items(1)}
    stopwatch, ruler = by_number[7], by_number[8]
    assert stopwatch.tolerance == WHOLE
    assert benchmark.correct(stopwatch, 7, 7.0)
    assert not benchmark.correct(stopwatch, 8, 7.0)
    assert benchmark.correct(ruler, 1.08, 1.0)
    assert not benchmark.correct(ruler, 1.12, 1.0)


def test_chance_is_one_over_the_options_or_the_share_of_the_range():
    by_number = {item.number: item for item in items(1)}
    assert chance(by_number[5], 1.0) == 0.5
    assert chance(by_number[7], 7.0) == pytest.approx(1 / 1000)
    # a reading of 10 m in 0 to 20 m within a tenth: 2 m of 20 m
    assert chance(by_number[8], 10.0) == pytest.approx(0.1)


def test_the_spread_over_seeds_is_a_student_t_interval():
    found = spread([0.5, 0.75, 1.0])
    assert found.mean == pytest.approx(0.75)
    assert found.deviation == pytest.approx(0.25)
    half = 4.302652729911275 * 0.25 / math.sqrt(3)
    assert (found.low, found.high) == pytest.approx((0.75 - half, 0.75 + half))
    assert math.isnan(spread([1.0]).deviation)
