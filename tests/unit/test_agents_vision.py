"""The answer tools of AI6 and AI7: what they accept, what they never
reveal, and how the build scores and tests the answers."""

import math

import pytest

from pbc.agents import ModelMessage, ToolCall, run
from pbc.agents import explanation_lab as ex
from pbc.agents import multimodal_lab as lab
from pbc.agents import multimodal_questions as mm
from pbc.agents.vision import (
    READING_TOLERANCE,
    Question,
    answer_sheet,
    chance,
    correct,
    score,
)


class Scripted:
    model = "scripted"
    secrets = ()

    def __init__(self, *messages):
        self.messages = list(messages)

    def complete(self, system, conversation, tools):
        return self.messages.pop(0)


def _calls(name, *arguments):
    return tuple(ToolCall(f"c{k}", name, a) for k, a in enumerate(arguments))


def test_the_answer_tool_acknowledges_and_reveals_nothing():
    sheet = answer_sheet(mm.QUESTIONS)
    result = sheet.dispatch(ToolCall("1", "answer", {"question": 4, "value": 19.0}))
    assert result.ok
    assert dict(result.content) == {"question": 4, "recorded": 1}


def test_a_question_is_answered_once_and_a_choice_only_by_its_options():
    sheet = answer_sheet(mm.QUESTIONS)
    assert sheet.dispatch(ToolCall("1", "answer", {"question": 1, "value": 2})).ok
    again = sheet.dispatch(ToolCall("2", "answer", {"question": 1, "value": 3}))
    assert not again.ok and "already answered" in again.content["error"]
    for value in (0, 4, 2.5):
        refused = sheet.dispatch(
            ToolCall("3", "answer", {"question": 2, "value": value})
        )
        assert not refused.ok


def test_the_budget_is_one_call_per_question():
    assert answer_sheet(mm.QUESTIONS).budget == len(mm.QUESTIONS)
    assert ex.explain_sheet().budget == len(ex.QUESTIONS)


def test_questions_are_numbered_without_gaps():
    with pytest.raises(ValueError):
        answer_sheet(mm.QUESTIONS[1:])


def test_scores_come_from_the_accepted_calls_not_the_text():
    key = dict(mm.RECORDED_KEY)
    transcript = run(
        Scripted(
            ModelMessage(
                "Every answer is right.",
                _calls(
                    "answer",
                    {"question": 1, "value": 2},
                    {"question": 4, "value": 30.0},
                    {"question": 4, "value": 19.6},  # refused: already answered
                ),
            ),
            ModelMessage("Done."),
        ),
        answer_sheet(mm.QUESTIONS),
        "s",
        "t",
        4,
    )
    scored = {s.question.number: s for s in score(mm.QUESTIONS, key, transcript)}
    assert scored[1].correct
    assert scored[4].answer == 30.0 and not scored[4].correct
    assert scored[2].answer is None and not scored[2].correct


def test_a_reading_is_correct_within_the_tolerance():
    q = Question(1, "B", "property", "read", unit="m/s", low=0.0, high=50.0)
    assert correct(q, 20.0 * (1 + 0.99 * READING_TOLERANCE), 20.0)
    assert not correct(q, 20.0 * (1 + 1.01 * READING_TOLERANCE), 20.0)


def test_chance_is_exact_for_options_and_for_a_range():
    choice = mm.QUESTIONS[0]
    assert chance(choice, 2) == pytest.approx(1 / 3)
    reading = Question(1, "B", "property", "read", unit="m/s", low=0.0, high=50.0)
    assert chance(reading, 20.0) == pytest.approx(2 * READING_TOLERANCE * 20.0 / 50.0)


def test_the_key_is_the_one_the_runs_were_recorded_against():
    for number, value in lab.key().items():
        assert math.isclose(value, mm.RECORDED_KEY[number], rel_tol=1e-4), number


def test_the_key_follows_the_physics():
    key = lab.key()
    assert key[4] == pytest.approx(mm.falling.mass * 9.80665 / mm.falling.b)
    assert key[5] == pytest.approx(math.log(2) * mm.falling.tau, rel=1e-3)
    assert key[6] == pytest.approx(key[4] / 2)
    assert (key[7], key[8], key[9]) == (2, 1, 4)


def test_the_explain_tool_refuses_an_interval_without_its_prediction():
    sheet = ex.explain_sheet()
    refused = sheet.dispatch(
        ToolCall(
            "1",
            "explain",
            {
                "question": 1,
                "value": 30.0,
                "low": 10.0,
                "high": 20.0,
                "unit": "m/s",
                "relation": "v = m g / b",
            },
        )
    )
    assert not refused.ok


def test_the_explain_tool_refuses_a_relation_another_question_offers():
    refused = ex.explain_sheet().dispatch(
        ToolCall(
            "1",
            "explain",
            {
                "question": 1,
                "value": 2.0,
                "low": 1.0,
                "high": 3.0,
                "unit": "s",
                "relation": "tau = m / b",
            },
        )
    )
    assert not refused.ok and "other relations" in refused.content["error"]


def test_the_scaling_test_separates_consistent_relations():
    q1, _, _, q4 = ex.QUESTIONS
    assert ex.dimensionally_consistent("v = m g / b", "m/s", q1)
    assert not ex.dimensionally_consistent("v = sqrt(m g / b)", "m/s", q1)
    # consistent and wrong: the scaling test is no test of the physics
    assert ex.dimensionally_consistent("v = g t", "m/s", q4)
    # the exponent of a dimensional quantity
    assert not ex.dimensionally_consistent("v = (m g / b) (1 - exp(-t))", "m/s", q4)
    # a right relation with the wrong unit
    assert not ex.dimensionally_consistent("v = m g / b", "s", q1)


def test_the_verified_results_come_from_the_exact_solution():
    truth = ex.verified()
    assert truth[1] == pytest.approx(ex.falling.mass * 9.80665 / ex.falling.b)
    assert truth[2] == pytest.approx(ex.falling.tau)
    assert truth[3] == pytest.approx(2 * truth[1])
    assert truth[4] == pytest.approx(truth[1] * (1 - math.exp(-4.0 / ex.falling.tau)))


def test_an_explanation_is_tested_apart_from_its_prediction():
    q4 = ex.QUESTIONS[3]
    truth = ex.verified()[4]
    # a right number explained by a wrong relation
    tested = ex.examine(
        q4,
        truth,
        {
            "value": truth,
            "low": truth - 1,
            "high": truth + 1,
            "unit": "m/s",
            "relation": "v = g t",
        },
    )
    assert tested.prediction and tested.covers and tested.unit_right
    assert tested.dimensions and not tested.physics and not tested.support
    # the right relation with a prediction it does not support
    tested = ex.examine(
        q4,
        truth,
        {
            "value": 30.0,
            "low": 29.0,
            "high": 31.0,
            "unit": "m/s",
            "relation": "v = (m g / b) (1 - exp(-b t / m))",
        },
    )
    assert tested.physics and not tested.support and not tested.prediction
    assert not tested.covers


def test_the_curve_fit_predicts_and_cannot_answer_the_counterfactual():
    fit, truth = ex.curve_fit_baseline(), ex.verified()
    for number in (1, 2, 4):
        assert (
            abs(fit[number] - truth[number]) <= ex.PREDICTION_TOLERANCE * truth[number]
        )
    assert abs(fit[3] - truth[3]) > ex.PREDICTION_TOLERANCE * truth[3]


def test_dimensional_analysis_identifies_the_forms_but_not_the_history():
    left = ex.dimensional_baseline()
    assert left[1] == ("v = m g / b",) and left[2] == ("tau = m / b",)
    assert len(left[4]) == 3
