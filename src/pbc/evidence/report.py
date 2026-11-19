"""An experiment report whose every statement is traced (lesson SA8;
``docs/discovery-protocol.md``, "The evidence contract").

A report is a list of statements about one task, and each says what kind
of statement it is:

- **observed**: what a recording or a measurement holds, read and not
  computed (a value a model wrote down, a reading of an instrument);
- **computed**: what the evaluator computed from the artifacts (a test that
  passed, a prediction within its tolerance);
- **proposed**: an interpretation or a next step that no record supports.

An observed or a computed statement names the claim of the ledger that
records it, the figures and tables of the page that show it, the
assumptions of the run record it rests on (by their number), and its
uncertainty in words. Its evidence status is derived from the ledger by
``claim_status``, never written in the report, so a changed artifact
changes it. A proposed statement names no record and is marked as
proposed. ``validate`` refuses a report that breaks these rules, with
every problem at once; ``trace`` resolves each statement.
"""

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from pbc.evidence.records import (
    RAW,
    Claim,
    ContractError,
    Ledger,
    check,
    claim_status,
)

OBSERVED = "observed"
COMPUTED = "computed"
PROPOSED = "proposed"
KINDS = (OBSERVED, COMPUTED, PROPOSED)
# The status a proposed statement carries in place of an evidence status.
MARKED = "proposed, not evaluated"


@dataclass(frozen=True)
class Statement:
    """One statement of a report.

    ``record`` is the id of a claim of the ledger; ``plots`` are the labels
    of the figures and tables of the page that show it; ``assumptions`` are
    the numbers, counted from 1, of the run record's assumptions it rests
    on; ``uncertainty`` says in words how far the statement may be off, or
    why it cannot be."""

    id: str
    text: str
    kind: str
    record: str | None = None
    plots: tuple[str, ...] = ()
    assumptions: tuple[int, ...] = ()
    uncertainty: str = ""


@dataclass(frozen=True)
class Problem:
    """A rule of the report that a statement breaks."""

    statement: str
    message: str

    def __str__(self) -> str:
        return f"{self.statement}: {self.message}"


class ReportRejected(ContractError):
    """A report with at least one problem; ``problems`` holds them all."""

    def __init__(self, problems: Sequence[Problem]):
        self.problems = tuple(problems)
        super().__init__("; ".join(str(p) for p in self.problems))


def _collector(found: list[Problem], statement: str):
    def problem(message: str) -> None:
        found.append(Problem(statement, message))

    return problem


def _claim(ledger: Ledger, id_: str) -> Claim | None:
    return next((c for c in ledger.claims if c.id == id_), None)


def problems(statements: Iterable[Statement], ledger: Ledger) -> tuple[Problem, ...]:
    """Every rule the statements break, in their order."""
    statements = tuple(statements)
    found = []
    repeated = Counter(s.id for s in statements)
    known = len(ledger.record.assumptions)
    for s in statements:
        problem = _collector(found, s.id)
        if repeated[s.id] > 1:
            problem("the id is used by another statement")
        if not s.text.strip():
            problem("the statement has no text")
        if s.kind not in KINDS:
            problem(f"the kind {s.kind!r} is not one of {', '.join(KINDS)}")
            continue
        if s.kind == PROPOSED:
            if s.record is not None:
                problem("a proposed statement names no record")
            continue
        if s.record is None:
            problem(f"a statement {s.kind} names its record, or is proposed")
            continue
        claim = _claim(ledger, s.record)
        if claim is None:
            problem(f"the ledger has no claim {s.record!r}")
        if not s.plots:
            problem("no figure or table shows it")
        if not s.assumptions:
            problem("it names no assumption")
        for number in s.assumptions:
            if not 1 <= number <= known:
                problem(f"the run record has no assumption {number}")
        if not s.uncertainty.strip():
            problem("it states no uncertainty")
        if s.kind == OBSERVED and claim is not None and not _recorded(ledger, claim):
            problem("an observed statement rests on a recorded artifact")
    return tuple(found)


def _recorded(ledger: Ledger, claim: Claim) -> bool:
    """Whether a run of ``claim`` has a raw artifact: a recording or a
    measurement, not only what the evaluator computed."""
    attempts = (ledger.attempt(run) for run in claim.runs)
    return any(
        artifact.kind == RAW
        for attempt in attempts
        if attempt is not None
        for artifact in attempt.artifacts
    )


def validate(statements: Iterable[Statement], ledger: Ledger) -> None:
    """Raise ``ReportRejected`` with every problem of the report."""
    found = problems(statements, ledger)
    if found:
        raise ReportRejected(found)


@dataclass(frozen=True)
class Traced:
    """A statement resolved: the evidence status of its record (or
    ``MARKED``), the runs that record links, and the artifacts of those
    runs (their paths, relative to the ledger's root)."""

    statement: Statement
    status: str
    runs: tuple[str, ...]
    artifacts: tuple[str, ...]


def trace(
    statements: Iterable[Statement], ledger: Ledger, root: Path
) -> tuple[Traced, ...]:
    """Validate the report, digest every artifact again under ``root``, and
    resolve each statement to the status of its record."""
    statements = tuple(statements)
    validate(statements, ledger)
    stale = check(ledger, root)
    traced = []
    for s in statements:
        if s.kind == PROPOSED:
            traced.append(Traced(s, MARKED, (), ()))
            continue
        claim = _claim(ledger, s.record)
        runs = tuple(claim.runs)
        artifacts = tuple(
            dict.fromkeys(
                a.path
                for run in runs
                if (attempt := ledger.attempt(run)) is not None
                for a in attempt.artifacts
            )
        )
        traced.append(Traced(s, claim_status(ledger, claim, stale), runs, artifacts))
    return tuple(traced)
