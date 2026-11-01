"""pbc.discovery.latent_lab: the fall agrees with its free-fall and
small-drag limits, hides its latent effects, a record at one mass cannot
tell the hypotheses apart, the disambiguating experiment can, and the run is
scored again offline from the tool calls."""

import json
import math
from dataclasses import replace
from pathlib import Path

import pytest

from pbc.agents import ModelMessage, ToolCall
from pbc.agents.loop import Step
from pbc.agents.replay import load_recording
from pbc.discovery import environment_allowlist, score_transcript
from pbc.discovery import latent_lab as lab
from pbc.discovery.latent_lab import HiddenForceEnvironment, fall

LESSON = Path(__file__).parents[2] / "site/lessons/agents-llm/19-hidden-variables"
# Recognisable if they ever appear in an output.
HIDDEN = {"g": 7.12345, "hidden_force": 0.812345, "drag": 0.0712345}


def test_the_fall_has_its_limits():
    # Free fall, and a hidden force that only lowers the acceleration.
    assert fall(9.0, 0.0, 0.0, 2.0, 1.5) == pytest.approx(9.0 * 1.5**2 / 2)
    assert fall(9.0, 4.0, 0.0, 2.0, 1.5) == pytest.approx(7.0 * 1.5**2 / 2)
    # Drag: the closed form meets the series at its seam, and a long fall
    # approaches the terminal speed a m / b.
    k_t = lab.SERIES_BELOW
    below = fall(9.0, 0.0, 2.0 * k_t * 0.999, 2.0, 1.0)
    above = fall(9.0, 0.0, 2.0 * k_t * 1.001, 2.0, 1.0)
    assert below == pytest.approx(above, rel=1e-6)
    speed = fall(9.0, 0.0, 1.0, 1.0, 40.0) - fall(9.0, 0.0, 1.0, 1.0, 39.0)
    assert speed == pytest.approx(9.0, rel=1e-9)


def test_no_public_attribute_tool_or_prompt_reaches_the_latent_effects():
    world = HiddenForceEnvironment(**HIDDEN, budget=lab.BUDGET)
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
    text += "".join(lab.task())
    for hidden in HIDDEN.values():
        assert f"{hidden:g}" not in text
    for sneaky in ("_law", "_truth", "held_out_error", "_held_out"):
        assert not allowlist.dispatch(ToolCall("x", sneaky, {})).ok


def test_a_record_at_one_mass_cannot_tell_the_hypotheses_apart():
    verdicts = {v.hypothesis: v for v in lab.judge_hypotheses(lab.record())}
    assert all(v.consistent for v in verdicts.values())
    # With a hidden force the record fixes only g - F/m: the fit stops at an
    # arbitrary point of that line, so no held-out error is given for it.
    unknown = {"a hidden force", "a hidden force and drag"}
    for name, verdict in verdicts.items():
        assert verdict.identifiable is (name not in unknown)
        assert (verdict.held_out_error is None) is (name in unknown)
    # The hypotheses the record does determine miss the held-out settings by
    # far: their errors are 4 and 5, against a tolerance of 0.05.
    errors = [v.held_out_error for v in verdicts.values() if v.identifiable]
    assert min(errors) > 10 * lab.TOLERANCE
    assert len(lab.rivals(lab.record())) == len(lab.FORCES) * len(lab.DRAGS)


def test_the_line_a_record_leaves_free_holds_laws_that_predict_differently():
    # Why no held-out error belongs to an undetermined hypothesis: two laws on
    # the line g - F/m = const fit the record equally well and predict the
    # held-out masses differently by a factor of fifty.
    data, world = lab.record(), lab.environment()
    found = []
    for force in (0.0, 1.0):
        held = {"hidden_force": force, "drag": 0.0}
        fit = lab.fit_hypothesis(data, held)
        found.append((fit.chi2, world.held_out_error(held | {"g": fit.value("g")})))
    (chi2_none, error_none), (chi2_one, error_one) = found
    assert chi2_one == pytest.approx(chi2_none, rel=1e-9)
    assert error_none > 10 * lab.TOLERANCE
    assert error_one < error_none / 10


def test_the_disambiguating_experiment_leaves_one_hypothesis():
    record = lab.record()
    chosen, spread = lab.disambiguating_experiment(lab.rivals(record))
    assert chosen == {"mass": min(lab.MASSES), "time": max(lab.TIMES)}
    # At the record's own mass the rivals agree far more closely.
    assert spread[(lab.RECORD_MASS, 0.5)] < spread[(chosen["mass"], 0.5)] / 10
    verdicts = {
        v.hypothesis: v
        for v in lab.judge_hypotheses(lab.with_readings_at(record, chosen["mass"]))
    }
    survivors = [v for v in verdicts.values() if v.consistent]
    assert [v.hypothesis for v in survivors] == ["a hidden force and drag"]
    assert survivors[0].identifiable
    assert survivors[0].held_out_error <= lab.TOLERANCE


def test_the_baselines_least_squares_recovers_and_free_fall_is_rejected():
    results = {b.name: b for b in lab.baselines()}
    assert lab.recovered(results["grid + least squares"])
    assert not results["grid + free fall"].success
    assert math.isfinite(results["grid + free fall"].held_out_error)


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
    assert transcript.finished and score.probes <= lab.BUDGET
    silent = replace(
        transcript,
        steps=tuple(
            Step(ModelMessage("", step.message.tool_calls), step.results)
            for step in transcript.steps
        ),
    )
    assert score_transcript(lab.PROTOCOL, silent, lab.SEED) == score
