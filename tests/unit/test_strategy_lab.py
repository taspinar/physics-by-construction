"""Four strategies of choosing readings under one budget (MD8, F147):
``pbc.agents.strategy_lab``."""

import json
import shutil
from pathlib import Path

import pytest
from support.paths import REPO_ROOT

from pbc.agents import strategy_lab as lab
from pbc.agents.design import measurements
from pbc.agents.design_lab import BUDGET, MAX_STEPS, SYSTEM
from pbc.evidence.records import COMPLETED, INVALID, check, summary

LESSON = REPO_ROOT / lab.LESSON


def test_the_instrument_depends_on_the_seed_and_repeats_within_one():
    assert lab.reading(2.0, 3.0, 1, seed=1) == lab.reading(2.0, 3.0, 1, seed=1)
    assert lab.reading(2.0, 3.0, 1, seed=1) != lab.reading(2.0, 3.0, 1, seed=2)
    assert lab.reading(2.0, 3.0, 1, seed=1) != lab.reading(2.0, 3.0, 2, seed=1)


def test_the_rig_refuses_a_start_faster_than_its_launcher():
    allowlist = lab.tools(1)
    tool = allowlist.tool("measure_speed")
    with pytest.raises(Exception, match="initial_speed"):
        tool.validate({"initial_speed": 5.0, "time": 3.0, "repeat": 1})


@pytest.mark.parametrize("name", ["scripted", "adaptive"])
def test_a_strategy_without_a_model_takes_the_budget_through_the_harness(name):
    choose = {"scripted": lab.scripted, "adaptive": lab.adaptive}[name]
    transcript, assessment = lab.run_policy(name, choose, seed=3)

    assert len(assessment.measurements) == BUDGET
    assert len(transcript.steps) <= MAX_STEPS
    assert transcript.finished


def test_the_adaptive_rule_reads_where_the_fitted_models_part():
    _, assessment = lab.run_policy("adaptive", lab.adaptive, seed=1)
    points = [
        (m.arguments["initial_speed"], m.arguments["time"])
        for m in assessment.measurements
    ]

    assert points[: len(lab.OPENING)] == list(lab.OPENING)
    # After the opening it goes to the longest time, where the exponential
    # and the hyperbolic tails part.
    assert all(t >= 2.0 for _, t in points[len(lab.OPENING) :])
    assert max(t for _, t in points) == lab.CANDIDATE_TIMES[-1]


@pytest.mark.parametrize("seed", lab.SEEDS)
def test_each_fixture_is_the_session_recorded_for_its_seed(seed):
    data = json.loads((LESSON / lab.RECORDINGS[seed]).read_text(encoding="utf-8"))
    assert (data["model"], data["recorded"]) == (lab.MODEL, lab.RECORDED)
    assert data["system"] == SYSTEM and data["task"] == lab.TASK
    assert not data.get("placeholder", False)

    recording, transcript, assessment = lab.replay_session(seed, LESSON)
    assert len(transcript.steps) == len(recording.steps)
    assert 0 < len(assessment.measurements) <= BUDGET


@pytest.mark.parametrize("seed", lab.SEEDS)
def test_the_hybrid_opens_with_the_sessions_readings_at_the_same_seed(seed):
    _, session, _ = lab.replay_session(seed, LESSON)
    opening = lab.opening_of(session, seed)
    transcript, assessment = lab.run_policy("hybrid", lab.hybrid(opening), seed)

    assert len(opening) == lab.HYBRID_OPENING
    chosen = [dict(m.arguments) for m in assessment.measurements]
    assert chosen[: lab.HYBRID_OPENING] == opening
    assert len(chosen) == BUDGET
    assert measurements(lab.DESIGN, transcript, lab.tools(seed)) == (
        assessment.measurements
    )


def test_the_ledger_has_every_strategy_at_every_seed_and_keeps_reports_apart():
    record = lab.ledger(LESSON)
    found = summary(record, LESSON)

    assert found.total == len(lab.STRATEGIES) * len(lab.SEEDS)
    assert found.counts[COMPLETED] == found.total
    assert {e.attempt for e in record.evaluations} == {a.id for a in record.attempts}
    assert {r.attempt for r in record.reports} == {f"LLM-{s}" for s in lab.SEEDS}
    for evaluation in record.evaluations:
        assert evaluation.resources["readings"] <= BUDGET
        assert evaluation.resources["model messages"] <= MAX_STEPS


def test_an_edited_session_is_an_invalid_attempt_of_the_model_and_the_hybrid(
    tmp_path: Path,
):
    for name in lab.RECORDINGS.values():
        shutil.copy(LESSON / name, tmp_path / name)
    path = tmp_path / lab.RECORDINGS[1]
    data = json.loads(path.read_text(encoding="utf-8"))
    first = next(r for s in data["steps"] for r in s["results"] if r["ok"])
    first["content"]["speed"] += 1.0
    path.write_text(json.dumps(data), encoding="utf-8")

    record = lab.ledger(tmp_path, seeds=(1,))

    assert record.attempt("LLM-1").status == INVALID
    assert record.attempt("hybrid-1").status == INVALID
    assert record.attempt("scripted-1").status == COMPLETED
    assert "LLM-1" not in {e.attempt for e in record.evaluations}


def test_a_session_changed_after_its_evaluation_invalidates_it(tmp_path: Path):
    for name in lab.RECORDINGS.values():
        shutil.copy(LESSON / name, tmp_path / name)
    record = lab.ledger(tmp_path, seeds=(2,))
    assert check(record, tmp_path) == ()

    path = tmp_path / lab.RECORDINGS[2]
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    stale = {i.attempt for i in check(record, tmp_path)}
    assert stale == {"LLM-2", "hybrid-2"}
