"""The experiment report of lesson SA8 (``pbc.evidence.report``): every
statement resolves to a claim of the ledger or is marked proposed, a report
that breaks a rule is refused with every problem, and a statement's evidence
status follows the ledger, so a changed artifact or a contradicting
evaluation shows on the report."""

from pathlib import Path

import pytest

from pbc.evidence import (
    COMPLETED,
    FAILED,
    NOT_EVALUATED,
    Artifact,
    Attempt,
    Claim,
    Evaluation,
    Ledger,
    RunRecord,
)
from pbc.evidence.report import (
    COMPUTED,
    MARKED,
    OBSERVED,
    PROPOSED,
    ReportRejected,
    Statement,
    problems,
    trace,
    validate,
)

RECORD = RunRecord(
    task="t",
    hypothesis="h",
    assumptions=("first", "second"),
    protocol_version="p-1",
    split={"given": "all"},
    seeds=(),
    budgets={"steps": 4},
    code="c" * 64,
    configuration="f" * 64,
    environment={"python": "3"},
)


def _ledger(root: Path, correct: bool = True) -> Ledger:
    """A recording (a raw artifact) evaluated once, and a computed
    baseline without an artifact, each with a claim."""
    recording = root / "recording.json"
    recording.write_text('{"value": 1.0}\n')
    artifact = Artifact.of("recording", recording, root)
    ledger = Ledger(RECORD)
    ledger.add_attempt(Attempt("run", "model", 1, COMPLETED, artifacts=(artifact,)))
    ledger.add_attempt(Attempt("fit", "baseline", 1, COMPLETED))
    for attempt, depends_on in (("run", (artifact,)), ("fit", ())):
        ledger.add_evaluation(
            Evaluation(attempt, "e", correct, {}, {}, depends_on, "c", "f")
        )
    ledger.add_claim(Claim("recorded", "the recording holds it", "s", {"run": True}))
    ledger.add_claim(Claim("fitted", "the fit is right", "s", {"fit": True}))
    return ledger


def _computed(**changes) -> Statement:
    fields = {
        "id": "c",
        "text": "The fit is right.",
        "kind": COMPUTED,
        "record": "fitted",
        "plots": ("fig-fit",),
        "assumptions": (1,),
        "uncertainty": "within the tolerance",
    }
    return Statement(**{**fields, **changes})


def _observed(**changes) -> Statement:
    return _computed(
        **{
            "id": "o",
            "text": "The recording holds a value.",
            "kind": OBSERVED,
            "record": "recorded",
            "uncertainty": "exact as recorded",
            **changes,
        }
    )


PROPOSAL = Statement("p", "A harder task could tell them apart.", PROPOSED)


def test_a_traced_report_resolves_every_statement(tmp_path):
    ledger = _ledger(tmp_path)

    traced = trace((_observed(), _computed(), PROPOSAL), ledger, tmp_path)

    assert [t.status for t in traced] == [COMPLETED, COMPLETED, MARKED]
    assert traced[0].runs == ("run",) and traced[0].artifacts == ("recording.json",)
    assert traced[1].runs == ("fit",) and traced[1].artifacts == ()
    assert traced[2].runs == () and traced[2].artifacts == ()


@pytest.mark.parametrize(
    ("statement", "message"),
    [
        (_computed(record=None), "names its record, or is proposed"),
        (_computed(record="nowhere"), "the ledger has no claim 'nowhere'"),
        (_computed(plots=()), "no figure or table shows it"),
        (_computed(assumptions=()), "it names no assumption"),
        (_computed(assumptions=(3,)), "the run record has no assumption 3"),
        (_computed(assumptions=(0,)), "the run record has no assumption 0"),
        (_observed(uncertainty=" "), "it states no uncertainty"),
        (_observed(record="fitted"), "rests on a recorded artifact"),
        (
            Statement("p", "A proposal.", PROPOSED, record="fitted"),
            "a proposed statement names no record",
        ),
        (_computed(kind="inferred"), "is not one of observed, computed, proposed"),
        (_computed(text=""), "the statement has no text"),
    ],
)
def test_a_deliberately_wrong_statement_is_refused(tmp_path, statement, message):
    ledger = _ledger(tmp_path)

    with pytest.raises(ReportRejected) as refused:
        trace((statement,), ledger, tmp_path)

    assert any(message in p.message for p in refused.value.problems)
    assert all(p.statement == statement.id for p in refused.value.problems)


def test_every_problem_is_reported_at_once(tmp_path):
    ledger = _ledger(tmp_path)
    bad = _computed(record="nowhere", plots=(), uncertainty="")

    found = problems((bad, _observed(id="c")), ledger)

    messages = [p.message for p in found]
    assert len(found) == 5
    assert messages.count("the id is used by another statement") == 2
    assert "no figure or table shows it" in messages
    assert "it states no uncertainty" in messages


def test_a_valid_report_passes_validation(tmp_path):
    validate((_observed(), _computed(), PROPOSAL), _ledger(tmp_path))


def test_a_changed_recording_withdraws_the_status_of_what_rests_on_it(tmp_path):
    ledger = _ledger(tmp_path)
    (tmp_path / "recording.json").write_text('{"value": 2.0}\n')

    traced = trace((_observed(), _computed(), PROPOSAL), ledger, tmp_path)

    assert [t.status for t in traced] == [NOT_EVALUATED, COMPLETED, MARKED]


def test_an_evaluation_that_contradicts_the_claim_fails_the_statement(tmp_path):
    ledger = _ledger(tmp_path, correct=False)

    traced = trace((_observed(), _computed()), ledger, tmp_path)

    assert [t.status for t in traced] == [FAILED, FAILED]


def test_the_status_is_never_written_in_the_report():
    # A statement has no field for its status: only the ledger gives one.
    assert "status" not in Statement.__dataclass_fields__
