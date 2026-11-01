"""pbc.discovery.noise_lab: the faulty gauge hides its law, offset, and
faults, a repeated probe repeats its fault, only the calibrated robust fit
survives the gauge, the baselines degrade with the noise, and the run is
scored again offline from the tool calls."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from pbc.agents import ModelMessage, ToolCall
from pbc.agents.loop import Step, Transcript
from pbc.agents.replay import load_recording
from pbc.discovery import environment_allowlist, score_transcript
from pbc.discovery import noise_lab as lab
from pbc.discovery.baselines import grid_probe, random_probe
from pbc.discovery.noise_lab import FaultyGaugeEnvironment

LESSON = Path(__file__).parents[2] / "site/lessons/agents-llm/18-discovery-under-noise"
# Recognisable if they ever appear in an output.
HIDDEN = {"strength": 13.4567, "exponent": 2.43219, "offset": 0.0771234, "faulty": 0.21}


def test_the_null_reading_is_the_offset_and_a_fault_repeats():
    world = FaultyGaugeEnvironment(**HIDDEN, sigma=1e-9, budget=500)
    readings = [world.measure(distance=d, mass=0.0)["force"] for d in (1, 2, 3, 4)]
    clean = [r for r in readings if abs(r - HIDDEN["offset"]) < 1e-6]
    assert clean, "every null reading was faulty"
    # Faults are large, and a repeated probe repeats its reading exactly.
    faults = []
    for i in range(200):
        settings = {"distance": 1 + i * 0.015, "mass": 2.0}
        first = world.measure(**settings)["force"]
        assert world.measure(**settings)["force"] == first
        deviation = first - world.predict(HIDDEN, settings) - HIDDEN["offset"]
        if abs(deviation) > 1e-6:
            faults.append(abs(deviation))
    assert 0.1 < len(faults) / 200 < 0.35
    assert min(faults) >= lab.FAULT_SIZE and max(faults) <= 2 * lab.FAULT_SIZE
    # The score is on the noise-free law, without the offset.
    assert world.held_out_error(HIDDEN) == 0.0


def test_no_public_attribute_tool_or_prompt_reaches_the_hidden_gauge():
    world = FaultyGaugeEnvironment(**HIDDEN, budget=lab.BUDGET)
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
    for sneaky in ("_law", "_offset", "_fault", "held_out_error", "_held_out"):
        assert not allowlist.dispatch(ToolCall("x", sneaky, {})).ok


def test_each_failure_of_the_gauge_needs_its_remedy():
    table = lab.failure_analysis()
    assert all(
        lab.recovered(r) for r in table["noise only"].values() if "sparse" not in r.name
    )
    assert not table["noise and offset"]["least squares"].success
    assert lab.recovered(table["noise and offset"]["least squares with an offset"])
    assert not table["noise and faulty readings"][
        "least squares with an offset"
    ].success
    for gauge in table:
        assert lab.recovered(table[gauge]["calibrated robust fit"])


def test_the_calibrated_fit_drops_exactly_the_faulty_readings():
    world = lab.environment()
    data = grid_probe(world)
    found = lab.calibrated_fit(world, data)
    faulty = {
        i
        for i, s in enumerate(data.settings)
        if world._fault(world._validated(s)) != 0.0
    }
    assert set(found.dropped) == faulty and faulty
    assert found.offset == pytest.approx(lab.WORLD["offset"], abs=4 * lab.SIGMA)


def test_the_calibrated_fit_degrades_with_the_noise():
    found = {
        d.sigma: d
        for d in lab.degradation((0.01, 0.3), (0, 1, 2))
        if d.method == "grid + calibrated robust fit"
    }
    assert found[0.3].median > 5 * found[0.01].median
    assert found[0.01].recovered == 3


def test_the_degradation_measures_every_baseline_at_every_noise_and_seed():
    sigmas, seeds = (0.01, 0.3), (0, 1, 2)
    found = lab.degradation(sigmas, seeds)
    names = [b.name for b in lab.baselines()]
    assert [d.method for d in found] == [n for n in names for _ in sigmas]
    assert all(len(d.errors) == len(seeds) for d in found)
    # The random settings are drawn anew with each seed.
    (row,) = [
        d
        for d in found
        if d.method == "random + calibrated robust fit" and d.sigma == 0.3
    ]
    for seed, error in zip(seeds, row.errors, strict=True):
        world = lab.environment(sigma=0.3, seed=seed)
        data = random_probe(world, seed)
        assert lab.calibrated_fit(world, data).result.held_out_error == error
    assert len(set(row.errors)) == len(seeds)


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


def test_an_unfinished_run_is_not_recovered():
    right = ToolCall("s", "submit", {"strength": 14.7, "exponent": 2.37})
    steps = (Step(ModelMessage("", (right,)), ()),)
    assert score_transcript(
        lab.PROTOCOL, Transcript("m", "s", "t", steps, True), 0
    ).recovered
    unfinished = Transcript("m", "s", "t", steps, False)
    assert not score_transcript(lab.PROTOCOL, unfinished, 0).recovered
