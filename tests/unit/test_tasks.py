"""The tasks of lesson AE2 beyond a number (F149): the key of the diagram
task is computed from the physics that draws its pictures, the drawn
world's truth and evaluation cases stay out of the agent's reach (I27), and
every recorded run replays offline and is scored again."""

import json
import math
from pathlib import Path

import pytest

from pbc.agents import ToolCall
from pbc.agents.vision import score
from pbc.discovery import tasks
from pbc.discovery.environment import CentralForceEnvironment
from pbc.discovery.protocol import prompt_sha
from pbc.discovery.tools import environment_allowlist
from pbc.mechanics.projectile import drag_free_range

LESSON = Path(__file__).parents[2] / tasks.DIRECTORY


def test_the_key_is_the_key_the_runs_were_recorded_against():
    key = tasks.diagram_key()
    assert set(key) == set(tasks.RECORDED_KEY)
    for number, value in tasks.RECORDED_KEY.items():
        assert key[number] == pytest.approx(value, abs=1e-4)


def test_the_drawn_flight_lands_where_the_closed_form_says():
    for angle in tasks.ANGLES:
        path = tasks.flight(angle)
        assert path[-1, 0] == pytest.approx(
            drag_free_range(tasks.LAUNCH_SPEED, angle), rel=1e-9
        )
        assert path[-1, 1] == pytest.approx(0.0, abs=1e-9)


def test_exactly_one_drawn_trajectory_passes_over_the_wall_with_a_margin():
    heights = [tasks.height_at(a, tasks.WALL_DISTANCE) for a in tasks.ANGLES]
    over = [h > tasks.WALL_HEIGHT for h in heights]
    assert over == [False, True, False]
    assert heights[1] - tasks.WALL_HEIGHT > 2.0  # m: readable off the picture


def test_every_question_has_a_category():
    assert set(tasks.CATEGORY) == {q.number for q in tasks.QUESTIONS}
    assert set(tasks.CATEGORY.values()) == set(tasks.CATEGORIES)


def test_the_task_text_gives_no_answer_the_pictures_carry():
    # The launch speed, the wall, and the period are only on the pictures.
    for hidden in ("20 m/s", "30 m", "1.5 s", "5 m high"):
        assert hidden not in tasks.ITEM_TASK


def test_the_drawn_world_is_out_of_the_agents_reach():
    assert tasks.withheld_unreachable() == {
        "tools": True,
        "prompt and tools": True,
        "evaluation cases refused": True,
        "public attributes": True,
    }


def test_no_drawn_value_or_evaluation_case_is_in_the_fixture():
    text = (LESSON / tasks.WORLD_RUN.fixture).read_text(encoding="utf-8")
    drawn = [*tasks.PROTOCOL.world.values()] + [
        v for case in tasks.PROTOCOL.held_out_settings() for v in case.values()
    ]
    for value in drawn:
        for digits in (4, 6, 12):
            assert f"{value:.{digits}g}" not in text


def test_measure_refuses_every_evaluation_case():
    allowlist = environment_allowlist(tasks.PROTOCOL.make(tasks.SEED))
    for case in tasks.PROTOCOL.held_out_settings():
        result = allowlist.dispatch(ToolCall("x", "measure", case))
        assert not result.ok


def test_the_drawn_values_are_not_round_and_come_from_the_stated_ranges():
    for seed in (tasks.WORLD_SEED, *tasks.OTHER_WORLDS):
        world, cases = tasks.drawn_world(seed)
        low, high = tasks.STRENGTHS
        assert low <= world["strength"] <= high
        assert tasks.EXPONENTS[0] <= world["exponent"] <= tasks.EXPONENTS[1]
        assert world["exponent"] != round(world["exponent"], 1)
        for case in cases:
            assert case["distance"] > CentralForceEnvironment.controls[0].high


def test_the_check_notices_a_drawn_value_in_the_prompt(monkeypatch):
    shown = f"{tasks.PROTOCOL.world['exponent']:.3g}"
    monkeypatch.setattr(
        tasks, "prompts", lambda world, condition: ("system", f"the power is {shown}")
    )
    assert not tasks.withheld_unreachable()["prompt and tools"]


@pytest.mark.parametrize("item", tasks.ITEM_RUNS, ids=lambda i: i.id)
def test_each_item_run_replays_and_answers_every_question(item):
    _, transcript = tasks.replay_items(item, LESSON)
    scored = score(tasks.QUESTIONS, tasks.diagram_key(), transcript)
    assert all(s.answer is not None for s in scored)
    assert transcript.finished


def test_the_world_run_matches_its_record_and_replays():
    _, transcript, result = tasks.replay_world(LESSON)
    system, task = tasks.world_prompts()
    assert prompt_sha(system, task) == tasks.WORLD_RUN.info.prompt_sha256
    cost = tasks.WORLD_RUN.info.cost
    assert cost.model_calls == len(transcript.steps)
    assert cost.tool_calls == sum(len(s.message.tool_calls) for s in transcript.steps)
    assert cost.input_tokens is None and cost.cost_usd is None
    assert result.claim is not None
    assert math.isfinite(result.held_out_error)


def test_the_item_runs_record_their_model_calls():
    for item in tasks.ITEM_RUNS:
        data = json.loads((LESSON / item.fixture).read_text(encoding="utf-8"))
        assert len(data["steps"]) == item.model_calls
        assert data["model"] == tasks.MODEL
        assert data["recorded"] == tasks.RECORDED
