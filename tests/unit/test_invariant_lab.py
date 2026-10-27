"""pbc.discovery.invariant_lab: the record of the run matches its fixture,
the replay is scored again offline from the tool calls alone, and the
prompts and tools carry nothing of the hidden force."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from pbc.agents import ModelMessage, ToolCall
from pbc.agents.loop import Step, Transcript
from pbc.agents.replay import load_recording
from pbc.discovery import invariant_lab as lab
from pbc.discovery.invariants import (
    INVARIANT,
    NOT_CONSERVED,
    PLANAR_LIBRARY,
    CentralBox,
    box_allowlist,
)
from pbc.discovery.protocol import prompt_sha

LESSON = (
    Path(__file__).parents[2]
    / "site/lessons/agents-llm/11-discovering-conservation-laws"
)


def test_the_record_of_the_run_matches_its_fixture():
    recording = load_recording(LESSON / lab.FIXTURE)
    assert (recording.model, recording.recorded) == (lab.INFO.model, lab.INFO.recorded)
    assert prompt_sha(recording.system, recording.task) == lab.INFO.prompt_sha256
    assert (recording.system, recording.task) == lab.prompts()
    assert not recording.placeholder
    calls = sum(len(step.message.tool_calls) for step in recording.steps)
    assert (lab.INFO.cost.model_calls, lab.INFO.cost.tool_calls) == (
        len(recording.steps),
        calls,
    )


def test_the_run_replays_offline_and_is_scored_again():
    _, transcript, score = lab.replay_run(LESSON)
    assert transcript.finished
    assert score.trajectories <= lab.BUDGET and score.refused == 0
    assert [v.verdict for v in score.verdicts] == [INVARIANT, INVARIANT]
    assert (score.found, score.known, score.outcome) == (2, 2, "recovered")


def test_the_score_depends_on_the_calls_and_not_on_the_words():
    _, transcript, score = lab.replay_run(LESSON)
    silent = replace(
        transcript,
        steps=tuple(
            Step(ModelMessage("", step.message.tool_calls), step.results)
            for step in transcript.steps
        ),
    )
    assert lab.score_run(silent) == score


def _submit(**coefficients):
    zeros = dict.fromkeys(PLANAR_LIBRARY, 0.0)
    return ToolCall("s", "submit", zeros | coefficients)


def test_a_run_that_submits_a_wrong_candidate_or_nothing_is_not_recovered():
    start = ToolCall("t", "trajectory", {"x": 1.0, "y": 0.2, "vx": 0.0, "vy": 0.7})
    one_axis = _submit(x2=1.0, vx2=0.5, x4=0.375)
    angular = _submit(xvy=1.0, yvx=-1.0)
    steps = (Step(ModelMessage("", (start, one_axis, angular)), ()),)
    score = lab.score_run(Transcript("m", "s", "t", steps, True))
    assert [v.verdict for v in score.verdicts] == [NOT_CONSERVED, INVARIANT]
    assert (score.found, score.outcome) == (1, "not recovered")
    nothing = lab.score_run(Transcript("m", "s", "t", (), True))
    assert nothing.outcome == "no claim"
    # An unfinished run is never reported as a recovery.
    energy = _submit(x2=1.0, y2=1.0, vx2=0.5, vy2=0.5, x4=0.375, y4=0.375, x2y2=0.75)
    steps = (Step(ModelMessage("", (start, energy, angular)), ()),)
    assert not lab.score_run(Transcript("m", "s", "t", steps, False)).recovered


def test_the_prompts_and_tools_carry_nothing_of_the_hidden_force():
    # The text the agent sees is the same whatever the hidden force: nothing
    # of it depends on the world.
    def seen(world):
        allowlist, _ = box_allowlist(world, lab.MAX_CANDIDATES)
        return json.dumps([s.__dict__ for s in allowlist.specs()], default=str)

    assert seen(lab.box()) == seen(CentralBox(k=3.1, b=0.7))
    assert "WORLD" not in "".join(lab.prompts())
    allowlist, _ = box_allowlist(lab.box(), lab.MAX_CANDIDATES)
    with pytest.raises(KeyError):
        allowlist.tool("held_out")
