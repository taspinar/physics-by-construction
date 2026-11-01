"""pbc.discovery.generalisation_lab: the short-range term is below the noise
within the bounds and decides the closer world, the judge scores each
held-out world, no tool reaches them, the trace of the run never probed one,
and the run is scored again offline from the tool calls."""

import json
import math
from dataclasses import replace
from pathlib import Path

from pbc.agents import ModelMessage, ToolCall
from pbc.agents.loop import Step
from pbc.agents.replay import load_recording
from pbc.discovery import environment_allowlist, score_transcript
from pbc.discovery import generalisation_lab as lab
from pbc.discovery.generalisation_lab import ShortRangeForceEnvironment

LESSON = (
    Path(__file__).parents[2]
    / "site/lessons/agents-llm/20-generalisation-to-unseen-systems"
)
# Recognisable if they ever appear in an output.
HIDDEN = {
    "strength": 16.12345,
    "exponent": 2.212345,
    "short": 1876.5,
    "length": 0.0712345,
}
FAMILY = {k: HIDDEN[k] for k in ("strength", "exponent")}


def test_the_short_range_term_hides_within_the_bounds_and_decides_the_closer_world():
    world = ShortRangeForceEnvironment(**HIDDEN)
    sigma = world.observation.sigma
    nearest = {"distance": world.controls[0].low, "mass": world.controls[1].high}
    assert abs(world._law(nearest) - world.predict(FAMILY, nearest)) < sigma / 2
    errors = world.generalisation_of(FAMILY)
    assert list(errors) == list(lab.WORLDS)
    assert all(errors[w] < 1e-4 for w in lab.SCORED)
    assert errors["closer"] > lab.TOLERANCE
    # The score is the worst scored world; a wrong exponent fails the
    # farther world and the orbits most.
    assert world.held_out_error(FAMILY) == max(errors[w] for w in lab.SCORED)
    wrong = world.generalisation_of(FAMILY | {"exponent": FAMILY["exponent"] + 0.05})
    assert wrong["farther"] > wrong["interpolation"]
    assert world.held_out_error(FAMILY | {"strength": 0.0}) == math.inf


def test_the_orbits_amplify_an_error_of_the_strength_only_where_the_starts_allow():
    # An inverse square from the same starts reproduces D4's formula
    # 3/2 x/(2-x) + 1/2, x = v0^2 r0/(GM): the factor depends on the orbit,
    # and the farthest start of the suite gives less than one.
    square = {"strength": 17.3, "exponent": 2.0}
    found = lab.period_sensitivity(square)
    for orbit, value in zip(ShortRangeForceEnvironment._orbits, found, strict=True):
        x = orbit["speed"] ** 2 * orbit["apsis"] / square["strength"]
        assert math.isclose(value, 1.5 * x / (2 - x) + 0.5, rel_tol=1e-3)
    assert found[0] > 1 > found[-1]
    # The law of the suite falls off faster, and amplifies it at every orbit.
    assert all(
        v > 1 for v in lab.period_sensitivity({"strength": 17.3, "exponent": 2.17})
    )


def test_no_public_attribute_tool_or_prompt_reaches_a_held_out_world():
    world = ShortRangeForceEnvironment(**HIDDEN, budget=lab.BUDGET)
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
    # The drawn interpolation settings are recognisable to four digits.
    for setting in world._interpolation:
        for value in setting.values():
            assert f"{value:.4f}" not in text
    for sneaky in ("_law", "generalisation", "_orbits", "_held_out", "_closer"):
        assert not allowlist.dispatch(ToolCall("x", sneaky, {})).ok


def test_the_run_never_probed_a_held_out_world():
    recording = load_recording(LESSON / lab.FIXTURE)
    world = lab.environment()
    held_out = [dict(s) for s in world._held_out]
    for step in recording.steps:
        for call in step.message.tool_calls:
            if call.name != "measure":
                continue
            for c in world.controls:
                assert c.low <= float(call.arguments[c.name]) <= c.high
            assert {k: float(v) for k, v in call.arguments.items()} not in held_out
    data = lab.probes(lab.replay_run(LESSON)[1])
    reached = {r.world: r for r in lab.reach(data)}
    assert all(r.probed == 0 and r.nearest > 0 for r in reached.values())
    for name in ("farther", "heavier", "closer"):
        assert reached[name].outside_bounds


def test_the_least_squares_baselines_generalise_and_none_reaches_the_closer_world():
    for result in lab.baselines():
        errors = lab.generalisation_of(result)
        assert errors["closer"] > lab.TOLERANCE
        if result.name.endswith("least squares"):
            assert lab.recovered(result)


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
