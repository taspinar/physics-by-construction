"""pbc.discovery.worlds and world_lab: the pair forces reduce to Newton's
gravity of pbc.mechanics.nbody, the world hides its law and its held-out
starts, the run's record matches its fixture, and the replay is scored
again offline from the tool calls alone."""

import json
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from pbc.agents import ModelMessage, ToolCall
from pbc.agents.loop import Step, Transcript
from pbc.agents.replay import load_recording
from pbc.discovery import world_lab as lab
from pbc.discovery import worlds
from pbc.discovery.protocol import prompt_sha
from pbc.discovery.worlds import (
    MASSES,
    PairForceWorld,
    accelerations_of,
    family_force,
    world_allowlist,
)
from pbc.mechanics.nbody import gravity

LESSON = (
    Path(__file__).parents[2] / "site/lessons/agents-llm/15-unknown-physical-worlds"
)
# Recognisable if they ever appear in an output.
HIDDEN = {"k12": 1.23456, "k13": -0.654321, "k23": 2.34567, "exponent": 1.76543}


def test_the_pair_forces_of_gravity_are_those_of_the_n_body_model():
    G = 0.7
    claim = {
        name: G * MASSES[i] * MASSES[j]
        for name, (i, j) in zip(worlds.COUPLINGS, worlds.PAIRS, strict=True)
    } | {"exponent": 2.0}
    x = np.array([[0.3, -1.2], [2.0, 0.5], [-1.5, 1.0]])
    expected = gravity(G, MASSES)(0.0, x.reshape(-1), np.zeros(6)).reshape(3, 2)
    assert accelerations_of(family_force(claim), x) == pytest.approx(
        expected, rel=1e-12
    )
    # Equal and opposite pair forces: the total force is zero.
    a = accelerations_of(family_force(HIDDEN), x)
    assert np.array(MASSES) @ a == pytest.approx(np.zeros(2), abs=1e-12)


def test_the_judge_scores_the_truth_zero_and_a_wrong_law_above_the_tolerance():
    world = PairForceWorld(**HIDDEN)
    assert world.held_out_error(HIDDEN) == 0.0
    assert world.held_out_error(HIDDEN | {"k13": 0.654321}) > lab.TOLERANCE
    assert world.error_in_time(family_force(HIDDEN)).shape == (len(worlds.TIMES),)


def test_probes_are_bounded_deterministic_and_cost_nothing_when_refused():
    world = PairForceWorld(**HIDDEN, budget=2)
    x = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 2.0]])
    first = world.accelerations(x)
    assert np.array_equal(world.accelerations(x), first)
    with pytest.raises(RuntimeError, match="spent"):
        world.accelerations(x)
    world.reset()
    with pytest.raises(ValueError, match="closer"):
        world.accelerations(np.array([[0.0, 0.0], [0.2, 0.0], [0.0, 2.0]]))
    with pytest.raises(ValueError, match="between"):
        world.accelerations(np.array([[0.0, 0.0], [4.0, 0.0], [0.0, 2.0]]))
    assert world.remaining == 2
    noise = (first - accelerations_of(family_force(HIDDEN), x)) / worlds.SIGMA
    assert np.all(np.abs(noise) < 5)


def test_no_tool_prompt_or_public_attribute_reaches_the_hidden_law_or_starts():
    world = PairForceWorld(**HIDDEN, budget=lab.BUDGET)
    allowlist, _ = world_allowlist(world)
    assert [t.name for t in allowlist.tools] == ["accelerations", "submit"]
    for sneaky in ("_truth", "held_out_error", "score_forces", "_HELD_OUT"):
        result = allowlist.dispatch(ToolCall("x", sneaky, {}))
        assert not result.ok and "not an allowed tool" in result.content["error"]
    text = json.dumps([s.__dict__ for s in allowlist.specs()], default=str)
    text += "".join(lab.prompts()) + repr(world)
    text += " ".join(
        repr(getattr(world, a)) for a in dir(world) if not a.startswith("_")
    )
    for hidden in HIDDEN.values():
        assert f"{hidden:g}" not in text
    for x, _ in worlds._HELD_OUT:
        assert f"{x[0][0]:g}, {x[0][1]:g}" not in text
    # The tools say the same whatever the hidden law.
    other, _ = world_allowlist(lab.world())
    assert other.specs() == allowlist.specs()
    # The held-out starts are not a configuration the agent could probe.
    assert all(np.abs(np.array(x)).max() > worlds.BOUND for x, _ in worlds._HELD_OUT)


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


def test_the_run_replays_offline_and_is_scored_from_the_calls_alone():
    _, transcript, score = lab.replay_run(LESSON)
    assert transcript.finished and score.refused == 0
    assert score.probes <= lab.BUDGET and score.outcome == "recovered"
    silent = replace(
        transcript,
        steps=tuple(
            Step(ModelMessage("", step.message.tool_calls), step.results)
            for step in transcript.steps
        ),
    )
    assert lab.score_run(silent) == score
    assert len(lab.agent_probes(transcript)) == score.probes


def test_a_run_without_a_claim_or_unfinished_is_not_recovered():
    nothing = lab.score_run(Transcript("m", "s", "t", (), True))
    assert nothing.outcome == "no claim" and math.isinf(nothing.held_out_error)
    right = ToolCall("s", "submit", dict(lab.WORLD))
    steps = (Step(ModelMessage("", (right,)), ()),)
    assert not lab.score_run(Transcript("m", "s", "t", steps, False)).recovered


def test_least_squares_predicts_the_motion_and_newton_and_whole_powers_do_not():
    results = {b.name: b for b in lab.baselines()}
    assert lab.recovered(results["random + least squares"])
    for name in ("random + Newton's gravity", "random + sparse identification"):
        assert not results[name].success
        assert results[name].held_out_error > lab.TOLERANCE
