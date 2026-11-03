"""The pilot of the evidence contract on the EV3 task (F137): the evaluator
replays the committed fixtures and scores them itself, so that a fabricated
score fails, a changed fixture invalidates what depended on it, every outcome
stays in the summary, and the final evaluation is bound to the frozen
candidate. The fixtures are copied before a test changes them."""

import json
import re
import shutil
import socket
from pathlib import Path

import pytest

from pbc.discovery import benchmark
from pbc.evidence import (
    ATTEMPT_STATUSES,
    COMPLETED,
    FAILED,
    INCONCLUSIVE,
    INVALID,
    MISSING,
    NOT_EVALUATED,
    UNVERIFIED,
    Claim,
    ContractError,
    Ledger,
    check,
    claim_status,
    load,
    pilot,
    save,
    summary,
)
from pbc.evidence.pilot import (
    CANDIDATES,
    EVALUATOR,
    FINAL_EVALUATOR,
    ISOLATION,
    evaluate_attempt,
    final_evaluation,
    fixture,
    freeze,
    run_pilot,
    run_record,
)

AGENT, PLAIN = "projectile-full", "plain-projectile"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("the pilot opened a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def root(tmp_path) -> Path:
    """A copy of the candidates' fixtures at their paths under the root."""
    for candidate in CANDIDATES:
        target = fixture(candidate, tmp_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fixture(candidate), target)
    return tmp_path


def _edit(path: Path, change) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _ledger() -> Ledger:
    return Ledger(run_record())


def test_the_pilot_reproduces_the_outcomes_of_ev3():
    ledger = run_pilot()
    s = summary(ledger, pilot.ROOT)
    assert [(r.attempt, r.status, r.correct) for r in s.rows] == [
        ("agent-1", COMPLETED, True),
        ("plain-1", COMPLETED, False),
        ("baseline-1", COMPLETED, True),
    ]
    assert [status for _, status in s.claims] == [COMPLETED, COMPLETED]
    assert s.invalidations == ()
    # The evaluator's score is the judge's score of the replayed run.
    _, _, score = benchmark.replay_cell(CANDIDATES[AGENT], fixture(AGENT).parent)
    agent = next(e for e in ledger.evaluations if e.attempt == "agent-1")
    assert agent.metrics["held_out_error"] == score.held_out_error
    assert agent.resources["probes"] == score.probes


def test_the_record_names_the_task_and_its_identities_and_hides_the_world():
    record = run_record()
    protocol = benchmark.PROTOCOLS["projectile"]
    assert record.protocol_version == protocol.version == "f81-projectile-1"
    assert record.seeds == protocol.seeds
    assert record.budgets == {"probes": protocol.budget, "steps": protocol.max_steps}
    assert len(record.code) == len(record.configuration) == 64
    assert set(record.environment) == {"python", "numpy", "system"}
    # The hidden gravity is in no field, only inside the configuration digest.
    texts = [
        record.task,
        record.hypothesis,
        *record.assumptions,
        *record.split.values(),
    ]
    numbers = {float(n) for t in texts for n in re.findall(r"\d+(?:\.\d+)?", t)}
    assert protocol.world["gravity"] not in numbers
    assert not any(c.isdigit() for v in record.split.values() for c in v)


# Acceptance criterion 1: a reported score the candidate did not achieve.


def test_a_candidate_reporting_a_high_score_it_did_not_achieve_fails():
    ledger = _ledger()
    evaluate_attempt(
        ledger,
        "plain-1",
        PLAIN,
        reported={"held_out_error": 0.001, "recovered": True},
        claims_correct=True,
    )
    ledger.add_claim(
        Claim("c", "The plain model recovers g.", "pilot", {"plain-1": True})
    )
    evaluation = ledger.evaluations[-1]
    assert evaluation.evaluator == EVALUATOR
    assert evaluation.correct is False
    assert evaluation.metrics["held_out_error"] > evaluation.metrics["tolerance"]
    report = ledger.reports[-1]
    assert report.label == UNVERIFIED
    assert report.details["held_out_error"] == 0.001  # kept, never evaluated
    s = summary(ledger, pilot.ROOT)
    assert s.rows[0].report == "disagrees"
    assert s.correct == 0
    assert claim_status(ledger, ledger.claims[0]) == FAILED
    assert "candidate's report disagrees (unverified)" in s.text()


def test_a_fixture_with_fabricated_readings_is_invalid_and_its_claim_fails(root):
    def better_readings(data):
        for result in data["steps"][0]["results"]:
            if "range" in result["content"]:
                result["content"]["range"] *= 1.2

    _edit(fixture(AGENT, root), better_readings)
    ledger = _ledger()
    attempt = evaluate_attempt(ledger, "agent-1", AGENT, root, claims_correct=True)
    assert attempt.status == INVALID
    assert attempt.diagnostics[0].startswith("ReplayMismatch")
    assert ledger.evaluations[-1].correct is None
    ledger.add_claim(Claim("c", "The agent recovers g.", "pilot", {"agent-1": True}))
    assert claim_status(ledger, ledger.claims[0]) == FAILED
    # The evaluator decided nothing: the report is unchecked, not refuted.
    s = summary(ledger, root)
    assert s.rows[0].report == "undecided"
    assert "candidate's report undecided (unverified)" in s.text()


def test_resources_are_counted_by_the_evaluator_not_taken_from_the_report():
    ledger = _ledger()
    evaluate_attempt(
        ledger, "agent-1", AGENT, reported={"tool_calls": 1, "cost_usd": 0.0}
    )
    _, transcript, score = benchmark.replay_cell(
        CANDIDATES[AGENT], fixture(AGENT).parent
    )
    resources = ledger.evaluations[-1].resources
    assert resources == {
        "probes": score.probes,
        "refused": score.refused,
        "model_messages": len(transcript.steps),
        "tool_calls": sum(len(s.message.tool_calls) for s in transcript.steps),
    }
    assert resources["tool_calls"] != 1
    # The run's own cost record is the candidate's report, not the evaluation.
    assert ledger.reports[-1].details["cost"]["tool_calls"] == 9


def test_a_candidate_that_submits_the_hidden_value_passes_the_isolation_is_stated(
    root,
):
    """The limit the contract states: the evaluator recomputes what the calls
    give; it cannot tell a claim learned from the readings from one copied
    from the repository, where the hidden world is."""
    hidden = benchmark.PROTOCOLS["projectile"].world["gravity"]

    def copied(data):
        data["steps"][0]["tool_calls"][0]["arguments"]["g"] = hidden

    _edit(fixture(PLAIN, root), copied)
    ledger = _ledger()
    evaluate_attempt(ledger, "plain-1", PLAIN, root)
    assert ledger.evaluations[-1].correct is True
    assert any("not private" in line for line in ISOLATION)


# Acceptance criterion 2: a changed artifact invalidates what depended on it.


def test_changing_a_fixture_after_evaluation_invalidates_it_visibly(root):
    ledger = run_pilot(root)
    assert check(ledger, root) == ()
    _edit(fixture(AGENT, root), lambda d: d["steps"][-1].update(text="edited"))
    stale = check(ledger, root)
    assert {(i.attempt, i.final) for i in stale} == {
        ("agent-1", False),
        ("final evaluation of projectile-full, version 1", True),
    }
    s = summary(ledger, root)
    rows = {r.attempt: r for r in s.rows}
    assert rows["agent-1"].invalidated and rows["agent-1"].correct is None
    assert not rows["plain-1"].invalidated
    assert dict((c.id, st) for c, st in s.claims) == {
        "agent-recovers": NOT_EVALUATED,
        "plain-fails-baseline-recovers": COMPLETED,
    }
    assert [stale for _, stale in s.finals] == [True]
    text = s.text()
    assert "evaluation invalidated" in text
    assert f"{fixture(AGENT, root).relative_to(root).as_posix()} was" in text


def test_a_removed_fixture_invalidates_and_a_new_attempt_is_missing(root):
    ledger = _ledger()
    evaluate_attempt(ledger, "plain-1", PLAIN, root)
    fixture(PLAIN, root).unlink()
    (invalidation,) = check(ledger, root)
    assert invalidation.current is None and "absent" in str(invalidation)
    attempt = evaluate_attempt(ledger, "plain-2", PLAIN, root, prior=("plain-1",))
    assert attempt.status == MISSING and attempt.prior == ("plain-1",)


# Acceptance criterion 3: every outcome stays visible.


def test_every_outcome_stays_in_the_record_and_the_summary(root, tmp_path):
    def no_claim(data):
        data["steps"] = data["steps"][1:]

    def never_finishes(data):
        step = data["steps"][0]
        hidden = benchmark.PROTOCOLS["projectile"].world["gravity"]
        step["tool_calls"][0]["arguments"]["g"] = hidden
        steps = benchmark.PROTOCOLS["projectile"].max_steps
        data["steps"] = [json.loads(json.dumps(step)) for _ in range(steps)]

    # One fixture per candidate: each change below also invalidates the
    # earlier evaluations of that fixture, which the summary shows.
    ledger = _ledger()
    _edit(fixture(PLAIN, root), no_claim)
    evaluate_attempt(ledger, "failed", PLAIN, root)
    shutil.copyfile(fixture(PLAIN), fixture(PLAIN, root))
    _edit(fixture(PLAIN, root), never_finishes)
    evaluate_attempt(ledger, "inconclusive", PLAIN, root)
    _edit(fixture(AGENT, root), lambda d: d["steps"][0]["results"].pop())
    evaluate_attempt(ledger, "invalid", AGENT, root)
    fixture(PLAIN, root).unlink()
    evaluate_attempt(ledger, "missing", PLAIN, root)
    shutil.copyfile(fixture(AGENT), fixture(AGENT, root))
    evaluate_attempt(ledger, "completed", AGENT, root)

    s = summary(ledger, root)
    assert [r.status for r in s.rows] == [
        FAILED,
        INCONCLUSIVE,
        INVALID,
        MISSING,
        COMPLETED,
    ]
    assert dict(s.counts) == {status: 1 for status in ATTEMPT_STATUSES}
    assert (s.correct, s.total) == (1, 5)  # the denominator keeps every attempt
    assert [r.invalidated for r in s.rows] == [True, True, True, False, False]
    assert s.rows[0].diagnostics == ("no claim submitted",)
    assert s.rows[1].diagnostics[0].startswith("the run reached the step limit")
    assert s.rows[3].diagnostics[0].startswith("no replay fixture")
    text = s.text()
    assert "correct 1 of 5" in text
    for status in ATTEMPT_STATUSES:
        assert f": {status}," in text
    # Persisted and read back, nothing is dropped.
    path = tmp_path / "ledger.json"
    save(ledger, path)
    again = load(path)
    assert again == ledger


def test_a_final_evaluation_that_does_not_replay_stays_visible(
    root, tmp_path, monkeypatch
):
    def broken(*args, **kwargs):
        raise ValueError("the replay broke after a code change")

    ledger = _ledger()
    freeze(ledger, AGENT, "1", root)
    monkeypatch.setattr(pilot, "replay_cell", broken)
    final = final_evaluation(ledger, AGENT, root)
    assert final.status == INVALID
    assert final.diagnostics == ("ValueError: the replay broke after a code change",)
    assert final.evaluation.correct is None
    assert ledger.finals == [final]
    text = summary(ledger, root).text()
    assert (
        f"by {FINAL_EVALUATOR}: invalid, undecided"
        " (ValueError: the replay broke after a code change)"
    ) in text
    path = tmp_path / "ledger.json"
    save(ledger, path)
    assert load(path) == ledger


# Acceptance criterion 4: the final evaluation and the next cycle.


def test_the_final_evaluation_is_bound_to_the_frozen_digest_and_version(root):
    ledger = run_pilot(root)
    (final,) = ledger.finals
    frozen = ledger.frozen_of(AGENT, 1)
    assert (final.digest, final.version, final.cycle) == (frozen.digest, "1", 1)
    assert final.evaluation.evaluator == FINAL_EVALUATOR
    assert final.evaluation.correct is True
    assert (final.status, final.diagnostics) == (COMPLETED, ())
    assert f"by {FINAL_EVALUATOR}: completed, correct" in summary(ledger, root).text()
    assert final.isolation == ISOLATION
    with pytest.raises(ContractError, match="already had its final evaluation"):
        final_evaluation(ledger, AGENT, root)
    with pytest.raises(ContractError, match="final evaluation in cycle 1"):
        evaluate_attempt(ledger, "agent-2", AGENT, root, prior=("agent-1",))


def test_a_change_after_the_final_evaluation_is_a_new_cycle(root):
    ledger = run_pilot(root)
    first = ledger.finals[0]
    _edit(fixture(AGENT, root), lambda d: d["steps"][-1].update(text="tuned"))
    with pytest.raises(ContractError, match="already frozen"):
        freeze(ledger, AGENT, "2", root)

    ledger.new_cycle("the fixture changed after the final evaluation of version 1")
    assert ledger.cycle == 2
    with pytest.raises(ContractError, match="already used"):
        freeze(ledger, AGENT, "1", root)
    evaluate_attempt(ledger, "agent-2", AGENT, root, prior=("agent-1",))
    frozen = freeze(ledger, AGENT, "2", root)
    assert frozen.digest != first.digest
    second = final_evaluation(ledger, AGENT, root)
    assert (second.version, second.cycle, second.digest) == ("2", 2, frozen.digest)
    # The first final evaluation stays in the record, marked invalidated.
    s = summary(ledger, root)
    assert [(f.version, f.cycle, stale) for f, stale in s.finals] == [
        ("1", 1, True),
        ("2", 2, False),
    ]


def test_a_candidate_changed_between_freeze_and_final_evaluation_is_refused(root):
    ledger = _ledger()
    evaluate_attempt(ledger, "agent-1", AGENT, root)
    freeze(ledger, AGENT, "1", root)
    _edit(fixture(AGENT, root), lambda d: d["steps"][-1].update(text="tuned"))
    with pytest.raises(ContractError, match="changed after it was frozen"):
        final_evaluation(ledger, AGENT, root)
    assert ledger.finals == []
