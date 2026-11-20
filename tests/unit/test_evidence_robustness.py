"""The repeated trials of lesson AE5 (``pbc.evidence.robustness``): the
variants perturb only what they say, the failing instrument fails on its
schedule and costs no probe, every trial's record matches its fixture and
its cost is the one recorded, and the interval of a rate is exact."""

import json
from pathlib import Path

import pytest
from scipy import stats

from pbc.agents import ModelMessage, ToolCall, run
from pbc.discovery import force_lab
from pbc.discovery.protocol import prompt_sha
from pbc.evidence import robustness, summary
from pbc.evidence.robustness import (
    BASE,
    BASELINE_SEEDS,
    FAIL_EVERY,
    FAILURE,
    NOISE_FACTOR,
    TRIALS,
    VARIANTS,
    baseline,
    calls_for,
    failed_calls,
    failing_instrument,
    replay_trial,
    success_interval,
    task,
)

ROOT = Path(__file__).parents[2]
DIRECTORY = ROOT / robustness.DIRECTORY


class Scripted:
    model = "scripted"
    secrets = ()

    def __init__(self, *messages):
        self.messages = list(messages)

    def complete(self, system, conversation, tools):
        return self.messages.pop(0)


def measure(amplitude, time):
    return ToolCall("c", "measure", {"amplitude": amplitude, "time": time})


def test_every_variant_keeps_the_prompt_the_world_and_the_budget_of_d2():
    assert task() == force_lab.task_of("prior-knowledge", "partial")
    for variant in VARIANTS.values():
        p = variant.protocol
        assert dict(p.world) == dict(BASE.world)
        assert (p.budget, p.tolerance, p.max_steps) == (
            BASE.budget,
            BASE.tolerance,
            BASE.max_steps,
        )
        assert p.held_out_settings() == BASE.held_out_settings()
    versions = [v.protocol.version for v in VARIANTS.values()]
    assert len(set(versions)) == len(versions)


def test_the_noisier_readings_are_the_published_noise_scaled():
    published = BASE.make(3)
    noisier = VARIANTS["noisier"].protocol.make(3)
    setting = {"amplitude": 1.5, "time": 2.2}
    truth = published._law(setting)
    plain = published.measure(**setting)["displacement"] - truth
    scaled = noisier.measure(**setting)["displacement"] - truth
    assert scaled == pytest.approx(NOISE_FACTOR * plain)
    assert noisier.held_out_error({"omega": 1.73}) == published.held_out_error(
        {"omega": 1.73}
    )


def test_the_failing_instrument_fails_every_third_accepted_call_and_spends_no_probe():
    world = VARIANTS["failing"].protocol.make(1)
    tools = failing_instrument(world)
    calls = [measure(1.0, 0.1 * i) for i in range(1, 8)]
    results = [tools.dispatch(c) for c in calls]
    failed = [i for i, r in enumerate(results, start=1) if not r.ok]
    assert failed == [FAIL_EVERY, 2 * FAIL_EVERY]
    assert all(r.content == {"error": FAILURE} for r in results if not r.ok)
    assert world.used == 7 - len(failed)
    # A call refused by validation is not counted toward the schedule.
    fresh = failing_instrument(VARIANTS["failing"].protocol.make(1))
    out_of_bounds = fresh.dispatch(measure(9.0, 0.1))
    assert not out_of_bounds.ok and out_of_bounds.content != {"error": FAILURE}
    assert [fresh.dispatch(measure(1.0, t)).ok for t in (0.1, 0.2, 0.3)] == [
        True,
        True,
        False,
    ]


def test_a_failed_call_is_counted_apart_from_a_refusal():
    variant = VARIANTS["failing"]
    world = variant.protocol.make(1)
    system, text = task()
    transcript = run(
        Scripted(
            ModelMessage("", tuple(measure(1.0, 0.1 * i) for i in range(1, 6))),
            ModelMessage("done"),
        ),
        variant.tools(world),
        system,
        text,
        3,
    )
    assert failed_calls(transcript) == 1
    refused = [r for r in transcript.steps[0].results if not r.ok]
    assert len(refused) == 2  # the instrument's failure and the fifth call


@pytest.mark.parametrize("name", list(TRIALS))
def test_each_trial_replays_and_its_record_matches_its_fixture(name):
    trial = TRIALS[name]
    recording, transcript, score = replay_trial(name, DIRECTORY)
    assert trial.info.protocol == VARIANTS[trial.variant].protocol.version
    assert trial.info.prompt_sha256 == prompt_sha(recording.system, recording.task)
    assert (recording.model, recording.recorded) == (
        trial.info.model,
        trial.info.recorded,
    )
    # The cost is the one the recording session reported: its messages and
    # calls, as the fixture holds them; tokens and price were not reported.
    data = json.loads((DIRECTORY / trial.fixture).read_text())
    assert trial.info.cost.model_calls == len(data["steps"])
    assert trial.info.cost.tool_calls == sum(
        len(s["tool_calls"]) for s in data["steps"]
    )
    assert trial.info.cost.input_tokens is None and trial.info.cost.cost_usd is None
    assert transcript.finished and score.claim is not None


def test_a_trial_replayed_with_another_variants_tools_does_not_replay():
    trial = TRIALS["failing-1"]
    recording = robustness.load_recording(DIRECTORY / trial.fixture)
    system, text = task()
    with pytest.raises(robustness.ReplayMismatch):
        robustness.replay_recording(
            recording,
            VARIANTS["repeated"].tools(VARIANTS["repeated"].protocol.make(1)),
            system=system,
            task=text,
            tolerance=1e-9,
            max_steps=BASE.max_steps,
            rerecord="",
        )


def test_the_ledger_holds_every_trial_and_its_outcome():
    ledger = robustness.ledger(DIRECTORY)
    s = summary(ledger, DIRECTORY)
    assert s.total == len(TRIALS) == 10
    assert s.correct == 7
    by_variant = {}
    for e in ledger.evaluations:
        by_variant.setdefault(TRIALS[e.attempt].variant, []).append(e.correct)
    assert {v: sum(c) for v, c in by_variant.items()} == {
        "repeated": 4,
        "noisier": 1,
        "failing": 2,
    }
    failing = [e for e in ledger.evaluations if TRIALS[e.attempt].variant == "failing"]
    assert all(e.resources["failed"] > 0 for e in failing)


@pytest.mark.parametrize("k, n", [(0, 1), (1, 3), (2, 3), (4, 4), (8, 20), (20, 20)])
def test_the_interval_is_exact(k, n):
    low, high = success_interval(k, n)
    if k > 0:
        assert stats.binom.sf(k - 1, n, low) == pytest.approx(0.025)
    else:
        assert low == 0.0
    if k < n:
        assert stats.binom.cdf(k, n, high) == pytest.approx(0.025)
    else:
        assert high == 1.0
    assert low <= k / n <= high


def test_all_successes_give_the_closed_form_lower_end():
    assert success_interval(4, 4)[0] == pytest.approx(0.025 ** (1 / 4))
    assert round(success_interval(4, 4)[0], 2) == 0.40


def test_an_impossible_count_is_refused():
    with pytest.raises(ValueError):
        success_interval(3, 2)


def test_a_retrying_method_needs_more_calls_on_the_failing_instrument():
    assert calls_for(2) == 2
    assert calls_for(3) == 4
    assert calls_for(BASE.budget) == 29


def test_every_refusal_of_the_trials_is_the_limit_of_calls_per_message():
    """The page says the refused calls are the harness's limit of four calls
    per message; the instrument's failures are counted apart."""
    for name in TRIALS:
        _, transcript, _ = replay_trial(name, DIRECTORY)
        errors = {
            r.content["error"]
            for step in transcript.steps
            for r in step.results
            if not r.ok
        }
        assert errors <= {"at most 4 tool calls per message", FAILURE}, name


def test_the_failing_baselines_are_the_published_ones_by_construction():
    # Review 01, MIN1: the baselines are not run through the failing
    # instrument; the page says their rows equal the published ones.
    for method in ("grid", "random"):
        for seed in BASELINE_SEEDS:
            assert baseline("failing", method, seed) == baseline(
                "repeated", method, seed
            )
