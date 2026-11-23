"""Review findings, discriminating tests, and the log of a follow-up
(``pbc.research.followup``, RR6, Issue #594). A revision of the claim never
resolves a finding that asks for new evidence (acceptance criterion 2)."""

import dataclasses

import pytest

from pbc.agents.specification import (
    REFUTED,
    SUPPORTED,
    UNDECIDED,
    Record,
    Run,
)
from pbc.evidence.records import digest_value
from pbc.research.followup import (
    EVIDENCE,
    INCONCLUSIVE,
    OPEN,
    RESOLVED,
    REWORDED,
    STOP,
    WORDING,
    Explanation,
    Finding,
    FollowUp,
    FollowUpRefused,
    Log,
    decided,
    discriminates,
    record_digest,
    status,
    verify_log,
)

HOLDS = Explanation("holds", "the claim holds", (SUPPORTED,))
FAILS = Explanation("fails", "the claim fails", (REFUTED,))
METHOD = Finding("method", "claim", "a reviewer", "another method?", EVIDENCE)
WORDS = Finding("words", "claim", "a reviewer", "say simulated", WORDING)


SPEC = {"actions": ["x"]}


def record(verdict: str, value: float = 1.0) -> Record:
    # A record of the route on SPEC: the execution sets the identity of the
    # specification it ran (Issue #606).
    run = Run(1, "scan", {"angle": 44.0}, value)
    return Record(
        (run,),
        "criteria met",
        (43.5, 44.0, 44.5),
        {},
        verdict,
        specification=digest_value(SPEC),
    )


def follow_up(key: str = "other-method", explanations=(HOLDS, FAILS)) -> FollowUp:
    return FollowUp(key, "method", "another method", SPEC, explanations)


def started(*findings: Finding, old: Record | None = None) -> Log:
    log = Log()
    log.claim("claim", "the claim", [record_digest(old or record(SUPPORTED, 0.0))])
    for finding in findings or (METHOD, WORDS):
        log.find(finding)
    return log


def test_a_test_discriminates_only_when_no_outcome_is_predicted_by_both():
    assert discriminates(follow_up()) == []
    both = Explanation("fails", "fails somewhere else", (SUPPORTED, REFUTED))
    assert discriminates(follow_up(explanations=(HOLDS, both))) == [
        "both explanations predict the verdict supported"
    ]
    silent = Explanation("silent", "predicts nothing", ())
    assert discriminates(follow_up(explanations=(HOLDS, silent))) == [
        "silent predicts no outcome"
    ]


def test_an_outcome_neither_explanation_predicted_decides_nothing():
    assert decided(follow_up(), SUPPORTED) == "holds"
    assert decided(follow_up(), REFUTED) == "fails"
    assert decided(follow_up(), UNDECIDED) is None


def test_the_log_refuses_a_test_that_does_not_discriminate_or_answers_wording():
    log = started()
    with pytest.raises(FollowUpRefused, match="does not discriminate"):
        log.declare(follow_up(explanations=(HOLDS, HOLDS)))
    words = dataclasses.replace(follow_up(), finding="words")
    with pytest.raises(FollowUpRefused, match="asks for other words"):
        log.declare(words)
    with pytest.raises(FollowUpRefused, match="no finding"):
        log.declare(dataclasses.replace(follow_up(), finding="unknown"))


def test_evidence_needs_a_declared_test_and_a_new_record():
    old = record(SUPPORTED, 0.0)
    log = started(old=old)
    with pytest.raises(FollowUpRefused, match="not declared"):
        log.record("other-method", record(SUPPORTED), SPEC)
    log.declare(follow_up())
    with pytest.raises(FollowUpRefused, match="not new evidence"):
        log.record("other-method", old, SPEC)
    log.record("other-method", record(SUPPORTED), SPEC)
    with pytest.raises(FollowUpRefused, match="already has its evidence"):
        log.record("other-method", record(SUPPORTED, 2.0), SPEC)


def test_a_finding_is_resolved_by_decisive_evidence_inconclusive_without_it():
    log = started()
    assert status(log, "method") == OPEN
    log.declare(follow_up("first"))
    log.record("first", record(UNDECIDED), SPEC)
    assert status(log, "method") == INCONCLUSIVE
    log.declare(follow_up("second"))
    log.record("second", record(REFUTED, 2.0), SPEC)
    assert status(log, "method") == RESOLVED  # decided, against the claim


def test_revising_the_prose_never_resolves_a_request_for_evidence():
    # Criterion 2: a revision that says it answers the finding, cites
    # nothing new, or cites a test without evidence leaves it open.
    log = started()
    log.revise("the claim, with a narrower scope", ["method", "words"], [])
    assert status(log, "method") == OPEN
    log.declare(follow_up())
    with pytest.raises(FollowUpRefused, match="no evidence of the test other-method"):
        log.revise("the claim, citing the declared test", ["method"], ["other-method"])
    log.record("other-method", record(UNDECIDED), SPEC)
    log.revise("the claim, citing the test", ["method"], ["other-method"])
    assert status(log, "method") == INCONCLUSIVE
    # A revision is what resolves a finding about the wording, and only that.
    assert status(log, "words") == REWORDED
    assert status(started(), "words") == OPEN


def test_a_decision_states_its_reason():
    log = started()
    with pytest.raises(FollowUpRefused, match="reason"):
        log.decide("method", STOP, " ", "")
    with pytest.raises(FollowUpRefused, match="unknown"):
        log.decide("method", "pause", "why", "")
    with pytest.raises(FollowUpRefused, match="no finding"):
        log.revise("text", ["unknown"], [])


def test_an_edited_or_removed_entry_breaks_the_chain():
    log = started()
    log.declare(follow_up())
    log.record("other-method", record(UNDECIDED), SPEC)
    assert verify_log(log.entries) == []
    entries = list(log.entries)
    evidence = entries[-1]
    entries[-1] = dataclasses.replace(
        evidence, content={**evidence.content, "decided": "holds"}
    )
    assert verify_log(entries) == ["entry 5: its digest does not match its content"]
    removed = log.entries[:2] + log.entries[3:]
    assert "entry 4 stands at position 3" in verify_log(removed)
    assert any("chain" in p for p in verify_log(removed))


def test_the_claim_comes_first_and_a_finding_once():
    log = started()
    with pytest.raises(FollowUpRefused, match="first entry"):
        log.claim("claim", "again", [])
    with pytest.raises(FollowUpRefused, match="already"):
        log.find(METHOD)
    with pytest.raises(FollowUpRefused, match="kind"):
        log.find(dataclasses.replace(METHOD, key="new", kind="taste"))


def test_a_finding_or_a_revision_before_the_claim_is_refused():
    with pytest.raises(FollowUpRefused, match="no claim yet"):
        Log().find(METHOD)
    with pytest.raises(FollowUpRefused, match="no claim yet"):
        Log().revise("text", [], [])
    with pytest.raises(FollowUpRefused, match="is about other"):
        started().find(dataclasses.replace(METHOD, key="new", claim="other"))


def test_a_decision_about_an_unknown_finding_is_refused():
    with pytest.raises(FollowUpRefused, match="no finding unknown"):
        started().decide("unknown", STOP, "why", "")


def test_a_revision_rests_only_on_tests_with_recorded_evidence():
    log = started()
    with pytest.raises(FollowUpRefused, match="no evidence of the test nowhere"):
        log.revise("the claim", ["method"], ["nowhere"])
    log.declare(follow_up())
    with pytest.raises(FollowUpRefused, match="no evidence of the test other-method"):
        log.revise("the claim", ["method"], ["other-method"])
    log.record("other-method", record(SUPPORTED), SPEC)
    log.revise("the claim", ["method"], ["other-method"])
    assert [e.kind for e in log.entries][-1] == "claim revised"


def test_a_second_declaration_under_a_declared_key_is_refused():
    # The owner's review of PR #599 (1): a second declaration overwrote the
    # test, and with it the predictions its recorded evidence is read by.
    log = started()
    log.declare(follow_up())
    swapped = follow_up(explanations=(FAILS, HOLDS))
    with pytest.raises(FollowUpRefused, match="other-method is already declared"):
        log.declare(swapped)
    assert log.tests["other-method"] == follow_up()
    assert [e.kind for e in log.entries].count("test declared") == 1


def test_a_record_of_another_specification_is_not_the_evidence_of_a_test():
    # The owner's review of PR #599 (2): the record must come from the
    # specification the test was declared with.
    log = started()
    log.declare(follow_up())
    with pytest.raises(FollowUpRefused, match="another specification"):
        log.record("other-method", record(REFUTED), {"actions": ["y"]})
    assert status(log, "method") == OPEN
    entry = log.record("other-method", record(REFUTED), dict(SPEC))
    assert entry.content["specification"] == log.entries[-2].content["specification"]


def test_a_record_of_experiment_a_is_refused_as_the_evidence_of_test_b():
    # Issue #606: the identity of the specification comes from the run.
    # Experiment A (the top of the range) is executed by the route and
    # registered under test B (a smaller coefficient): refused, also when
    # the caller passes test B's specification beside it.
    from pbc.mechanics.experiments import (
        discrepancies_and_follow_up_experiments as rr6,
    )

    a, b = rr6.TOP_OF_RANGE, rr6.BELOW_THE_TOP
    log = Log()
    log.claim("slow-throw", rr6.CLAIM, [])
    for finding in rr6.FINDINGS:
        log.find(finding)
    log.declare(b)
    ran_a = rr6.run_route(a.specification)
    assert ran_a.specification == digest_value(a.specification)
    for supplied in (None, b.specification):
        with pytest.raises(FollowUpRefused, match="another specification"):
            log.record(b.key, ran_a, supplied)
    assert log.evidence_of(b.finding) == []
    entry = log.record(b.key, rr6.run_route(b.specification))
    assert entry.content["specification"] == digest_value(b.specification)


def test_a_record_that_names_no_specification_is_refused():
    log = started()
    log.declare(follow_up())
    anonymous = dataclasses.replace(record(SUPPORTED), specification="")
    with pytest.raises(FollowUpRefused, match="names no specification"):
        log.record("other-method", anonymous, SPEC)
    assert status(log, "method") == OPEN


def test_the_record_digest_covers_the_specification_it_ran():
    # A record cannot be relabelled with another specification without
    # changing its digest.
    ran = record(SUPPORTED)
    relabelled = dataclasses.replace(ran, specification=digest_value({"other": 1}))
    assert record_digest(relabelled) != record_digest(ran)
