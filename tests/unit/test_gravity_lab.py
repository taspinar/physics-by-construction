"""pbc.discovery.gravity and gravity_lab: the transfer judge scores orbits
against Kepler's law, the laboratory hides its law, the run's record matches
its fixture, and the replay is scored again offline from the tool calls."""

import json
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from pbc.agents import ModelMessage, ToolCall
from pbc.agents.loop import Step, Transcript
from pbc.agents.replay import load_recording
from pbc.discovery import environment_allowlist, prompts, score_transcript
from pbc.discovery import gravity_lab as lab
from pbc.discovery.gravity import GravityEnvironment, radial_period

LESSON = Path(__file__).parents[2] / "site/lessons/agents-llm/14-discovering-gravity"
# Recognisable if they ever appear in an output.
HIDDEN = {
    "G": 0.0412345,
    "source_power": 1.04321,
    "test_power": 0.97654,
    "exponent": 2.07654,
}


def test_the_radial_period_of_an_inverse_square_orbit_is_keplers():
    gm, r, v = 25.0, 8.0, 2.0
    a = 1 / (2 / r - v**2 / gm)  # vis-viva
    kepler = 2 * math.pi * math.sqrt(a**3 / gm)
    assert radial_period(lambda x: -gm / x**2, r, v) == pytest.approx(kepler, rel=1e-8)
    # Started slower than the circular speed, the start is an apoapsis; the
    # period is the same.
    a = 1 / (2 / r - 1.5**2 / gm)
    kepler = 2 * math.pi * math.sqrt(a**3 / gm)
    assert radial_period(lambda x: -gm / x**2, r, 1.5) == pytest.approx(
        kepler, rel=1e-8
    )
    # A body that escapes has no period.
    assert math.isnan(radial_period(lambda x: -gm / x**2, r, 3.0))
    assert math.isnan(radial_period(lambda x: gm / x**2, r, 1.0))


def test_the_transfer_scores_the_truth_zero_and_amplifies_an_error_of_the_mass_power():
    world = GravityEnvironment(**HIDDEN)
    assert world.held_out_error(HIDDEN) == 0.0
    shifted = HIDDEN | {"source_power": HIDDEN["source_power"] + 0.01}
    # At the source masses of the laboratory the force barely changes; at
    # those of the orbits it changes by far more.
    lab_change = 10**0.01 - 1
    assert world.held_out_error(shifted) > 2 * lab_change
    assert world.held_out_error(HIDDEN | {"G": 0.0}) == math.inf


def test_no_public_attribute_tool_or_prompt_reaches_the_hidden_law():
    world = GravityEnvironment(**HIDDEN, budget=lab.BUDGET)
    seen = []
    for name in dir(world):
        if name.startswith("_") or name == "measure":
            continue
        value = getattr(world, name)
        if callable(value):
            try:
                value = value()
            except TypeError, ValueError:
                continue
        seen.append(repr(value))
    text = " ".join(seen)
    allowlist = environment_allowlist(world)
    text += json.dumps([s.__dict__ for s in allowlist.specs()], default=str)
    text += "".join(prompts(world, lab.CONDITION))
    for hidden in HIDDEN.values():
        assert f"{hidden:g}" not in text
    for sneaky in ("_law", "_truth", "held_out_error", "score_predictor", "_held_out"):
        assert not allowlist.dispatch(ToolCall("x", sneaky, {})).ok
    # The text the agent sees is the same whatever the hidden law.
    assert prompts(world, lab.CONDITION) == lab.task()


def test_the_record_of_the_run_matches_its_fixture():
    recording = load_recording(LESSON / lab.FIXTURE)
    info = lab.RUN.info
    assert (recording.model, recording.recorded) == (info.model, info.recorded)
    assert (recording.system, recording.task) == lab.task()
    assert not recording.placeholder
    calls = sum(len(step.message.tool_calls) for step in recording.steps)
    assert (info.cost.model_calls, info.cost.tool_calls) == (
        len(recording.steps),
        calls,
    )


def test_the_run_replays_offline_and_is_scored_again_from_the_calls_alone():
    _, transcript, score = lab.replay_run(LESSON)
    assert transcript.finished and score.refused == 0
    assert score.probes <= lab.BUDGET
    assert score.outcome == "recovered"
    silent = replace(
        transcript,
        steps=tuple(
            Step(ModelMessage("", step.message.tool_calls), step.results)
            for step in transcript.steps
        ),
    )
    assert score_transcript(lab.PROTOCOL, silent, lab.SEED) == score


def test_an_unfinished_run_or_a_wrong_law_is_not_recovered():
    wrong = ToolCall(
        "s",
        "submit",
        {"G": 0.05, "source_power": 1.1, "test_power": 1.0, "exponent": 2.0},
    )
    steps = (Step(ModelMessage("", (wrong,)), ()),)
    score = score_transcript(lab.PROTOCOL, Transcript("m", "s", "t", steps, True), 0)
    assert score.outcome == "not recovered"
    right = ToolCall("s", "submit", dict(lab.WORLD))
    steps = (Step(ModelMessage("", (right,)), ()),)
    unfinished = Transcript("m", "s", "t", steps, False)
    assert not score_transcript(lab.PROTOCOL, unfinished, 0).recovered


def test_the_least_squares_baselines_pass_the_transfer_and_the_scan_separates_laws():
    results = {b.name: b for b in lab.baselines()}
    assert lab.recovered(results["grid + least squares"])
    assert lab.recovered(results["grid + sparse identification"])
    data = lab.probes(lab.replay_run(LESSON)[1])
    shifts = (-3.0, 0.0, 3.0)

    def spread(parameter):
        scan = lab.sensitivity(data, parameter, shifts)
        assert [s.chi2_increase for s in scan] == pytest.approx([9, 0, 9], abs=0.1)
        errors = [s.transfer_error for s in scan]
        assert np.isfinite(errors).all()
        return max(errors) - min(errors)

    # Laws the laboratory rejects equally (three standard errors each) part
    # on the orbits by far more when the power of the source mass is wrong
    # than when the coefficient is: the orbits' source masses are a thousand
    # times the laboratory's.
    assert spread("source_power") > 5 * spread("G")
