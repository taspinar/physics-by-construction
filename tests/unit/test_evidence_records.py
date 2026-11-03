"""The records of the evidence contract (F137): the evidence status of a
claim follows from the evaluations, the ledger refuses what the contract
forbids, and a digest names an artifact by its content."""

import pytest

from pbc.evidence import (
    COMPLETED,
    EVIDENCE_STATUSES,
    FAILED,
    INCONCLUSIVE,
    INDEPENDENTLY_CHECKED,
    INVALID,
    MISSING,
    NOT_EVALUATED,
    Artifact,
    Attempt,
    CandidateReport,
    Claim,
    ContractError,
    Evaluation,
    FinalEvaluation,
    Ledger,
    RunRecord,
    candidate_digest,
    check,
    claim_status,
    digest_file,
    digest_value,
)

RECORD = RunRecord(
    task="t",
    hypothesis="h",
    assumptions=("a",),
    protocol_version="p-1",
    split={"probed": "inside", "held out": "outside"},
    seeds=(0,),
    budgets={"probes": 3},
    code="c" * 64,
    configuration="f" * 64,
    environment={"python": "3"},
)


def _evaluation(attempt: str, correct, evaluator="e1", depends_on=()) -> Evaluation:
    return Evaluation(attempt, evaluator, correct, {}, {}, depends_on, "c", "f")


def _ledger(*statuses: str) -> Ledger:
    ledger = Ledger(RECORD)
    for number, status in enumerate(statuses, start=1):
        ledger.add_attempt(Attempt(f"a{number}", "x", 1, status))
    return ledger


def test_the_evidence_statuses_are_those_of_the_requirements():
    assert EVIDENCE_STATUSES == (
        "completed",
        "failed",
        "inconclusive",
        "not evaluated",
        "independently checked",
    )


@pytest.mark.parametrize(
    ("status", "evaluations", "expected"),
    [
        (COMPLETED, [True], COMPLETED),
        (COMPLETED, [False], FAILED),
        (COMPLETED, [], NOT_EVALUATED),
        (COMPLETED, [True, False], INCONCLUSIVE),
        (INCONCLUSIVE, [None], INCONCLUSIVE),
        (INVALID, [None], FAILED),
        (MISSING, [], NOT_EVALUATED),
    ],
)
def test_the_status_of_a_claim_follows_from_its_evaluations(
    status, evaluations, expected
):
    ledger = _ledger(status)
    for number, correct in enumerate(evaluations):
        ledger.add_evaluation(_evaluation("a1", correct, f"e{number}"))
    assert claim_status(ledger, Claim("c", "", "", {"a1": True})) == expected


def test_agreeing_evaluators_of_different_identities_check_a_claim_independently():
    ledger = _ledger(COMPLETED)
    ledger.add_evaluation(_evaluation("a1", True, "e1"))
    claim = Claim("c", "", "", {"a1": True})
    assert claim_status(ledger, claim) == COMPLETED
    ledger.add_evaluation(_evaluation("a1", True, "e1"))  # the same evaluator again
    assert claim_status(ledger, claim) == COMPLETED
    ledger.add_evaluation(_evaluation("a1", True, "e2"))
    assert claim_status(ledger, claim) == INDEPENDENTLY_CHECKED


def test_one_failing_run_fails_a_claim_and_one_without_a_run_is_not_evaluated():
    ledger = _ledger(COMPLETED, COMPLETED, MISSING)
    ledger.add_evaluation(_evaluation("a1", True))
    ledger.add_evaluation(_evaluation("a2", True))
    assert claim_status(ledger, Claim("c", "", "", {"a1": True, "a2": False})) == FAILED
    assert claim_status(ledger, Claim("c", "", "", {"a1": True, "a3": True})) == (
        NOT_EVALUATED
    )
    assert claim_status(ledger, Claim("c", "", "", {"a9": True})) == NOT_EVALUATED
    assert claim_status(ledger, Claim("c", "", "", {})) == NOT_EVALUATED


def test_a_changed_artifact_turns_a_completed_claim_into_not_evaluated(tmp_path):
    path = tmp_path / "out.json"
    path.write_text("1")
    artifact = Artifact.of("out", path, tmp_path)
    ledger = _ledger(COMPLETED)
    ledger.add_evaluation(_evaluation("a1", True, depends_on=(artifact,)))
    claim = Claim("c", "", "", {"a1": True})
    assert claim_status(ledger, claim, check(ledger, tmp_path)) == COMPLETED
    path.write_text("2")
    stale = check(ledger, tmp_path)
    assert [(i.path, i.recorded, i.current) for i in stale] == [
        ("out.json", artifact.sha256, digest_file(path))
    ]
    assert claim_status(ledger, claim, stale) == NOT_EVALUATED


def test_the_ledger_refuses_what_the_contract_forbids(tmp_path):
    ledger = _ledger(COMPLETED)
    with pytest.raises(ContractError, match="unknown attempt status"):
        Attempt("b", "x", 1, "succeeded")
    with pytest.raises(ContractError, match="current cycle is 1"):
        ledger.add_attempt(Attempt("b", "x", 2, COMPLETED))
    with pytest.raises(ContractError, match="already recorded"):
        ledger.add_attempt(Attempt("a1", "x", 1, COMPLETED))
    with pytest.raises(ContractError, match="unknown"):
        ledger.add_attempt(Attempt("b", "x", 1, COMPLETED, prior=("zz",)))
    with pytest.raises(ContractError, match="no attempt"):
        ledger.add_evaluation(_evaluation("zz", True))
    with pytest.raises(ContractError, match="unverified"):
        ledger.add_report(CandidateReport("a1", True, {}, label="verified"))
    with pytest.raises(ContractError, match="no complete artifacts"):
        ledger.freeze("x", "1", (Artifact("f", "absent.json", None),))
    with pytest.raises(ContractError, match="states its reason"):
        ledger.new_cycle(" ")

    path = tmp_path / "c.json"
    path.write_text("{}")
    artifact = Artifact.of("c", path, tmp_path)
    frozen = ledger.freeze("x", "1", (artifact,))
    assert frozen.digest == candidate_digest((artifact,))
    evaluation = _evaluation("final", True, "final-1", (artifact,))
    wrong = FinalEvaluation("x", "2", 1, frozen.digest, evaluation, ())
    with pytest.raises(ContractError, match="was frozen as version 1"):
        ledger.add_final(wrong, tmp_path)
    with pytest.raises(ContractError, match="not frozen"):
        ledger.add_final(FinalEvaluation("y", "1", 1, "d", evaluation, ()), tmp_path)
    final = FinalEvaluation("x", "1", 1, frozen.digest, evaluation, ("open task",))
    ledger.add_final(final, tmp_path)
    assert ledger.final_of("x", 1) == final


def test_a_digest_names_content_not_correctness(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.write_text("g = 9.81")
    b.write_text("g = 9.81")
    assert digest_file(a) == digest_file(b)  # the same content, whatever it claims
    assert digest_file(tmp_path / "none") is None
    assert digest_value({"x": 1, "y": 2}) == digest_value({"y": 2, "x": 1})
