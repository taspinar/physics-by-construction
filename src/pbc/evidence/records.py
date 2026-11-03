"""The records of the evidence contract and the ledger that holds them
(ADR 022 decision 6; ``docs/discovery-protocol.md``, "The evidence contract").

The evaluator owns the ledger. It records the task (``RunRecord``), each
attempt of a candidate with its status and the artifacts it produced
(``Attempt``, ``Artifact``), what the evaluator recomputed from those
artifacts (``Evaluation``), and, apart from it, what the candidate said about
itself (``CandidateReport``, labelled unverified). A claim links to the runs
that support it and to its sources; its evidence status is derived from the
evaluations, never written by hand (``claim_status``).

A selected candidate is frozen by the digest of its artifacts and a version
(``FrozenCandidate``); its final evaluation is bound to both and runs once per
development and evaluation cycle (``FinalEvaluation``). A change after it is a
new cycle (``Ledger.new_cycle``), never a second final evaluation of the same
candidate. ``check`` digests every artifact an evaluation depended on again,
so that a changed artifact invalidates that evaluation visibly.

A digest establishes identity, not scientific truth: it says that an artifact
is the one evaluated, not that what it records is correct.
"""

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

FORMAT = 1
UNVERIFIED = "unverified"

COMPLETED = "completed"
FAILED = "failed"
INCONCLUSIVE = "inconclusive"
INVALID = "invalid"
MISSING = "missing"
# The status of an attempt: it ran and was evaluated (completed); it ran and
# produced no result to evaluate (failed); it was evaluated but the protocol
# cannot decide its outcome (inconclusive); its artifact is not what it
# claims to be, or does not replay (invalid); its artifact is absent
# (missing).
ATTEMPT_STATUSES = (COMPLETED, FAILED, INCONCLUSIVE, INVALID, MISSING)

NOT_EVALUATED = "not evaluated"
INDEPENDENTLY_CHECKED = "independently checked"
# The evidence status of a claim (requirements, "Data and persistence").
EVIDENCE_STATUSES = (
    COMPLETED,
    FAILED,
    INCONCLUSIVE,
    NOT_EVALUATED,
    INDEPENDENTLY_CHECKED,
)

RAW = "raw"
DERIVED = "derived"


class ContractError(ValueError):
    """An operation the evidence contract forbids."""


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str | None:
    """The SHA-256 of the file at ``path``, ``None`` when there is none."""
    return digest_bytes(path.read_bytes()) if path.is_file() else None


def digest_value(value: Any) -> str:
    """The SHA-256 of ``value`` as canonical JSON (sorted keys, no spaces)."""
    text = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return digest_bytes(text.encode())


def digest_files(paths: Iterable[Path], root: Path) -> str:
    """One digest over the files ``paths``, by their path relative to
    ``root`` and their content: the identity of a set of source files."""
    entries = sorted(
        (p.relative_to(root).as_posix(), digest_file(p) or "") for p in paths
    )
    return digest_value(entries)


@dataclass(frozen=True)
class RunRecord:
    """The task the evidence is about, as the evaluator states it.

    ``split`` describes the data split in words (what is probed, what is held
    out), never the held-out values; ``code`` and ``configuration`` are the
    digests of the evaluator's code and of the protocol; ``environment``
    names the interpreter and libraries the evaluation ran with."""

    task: str
    hypothesis: str
    assumptions: tuple[str, ...]
    protocol_version: str
    split: Mapping[str, str]
    seeds: tuple[int, ...]
    budgets: Mapping[str, int]
    code: str
    configuration: str
    environment: Mapping[str, str]


@dataclass(frozen=True)
class Artifact:
    """A raw or derived artifact of an attempt: its path relative to the
    ledger's root and its digest when recorded (``None``: absent then)."""

    name: str
    path: str
    sha256: str | None
    kind: str = RAW

    @classmethod
    def of(cls, name: str, path: Path, root: Path, kind: str = RAW) -> Artifact:
        return cls(name, path.relative_to(root).as_posix(), digest_file(path), kind)


@dataclass(frozen=True)
class Attempt:
    """One attempt of a candidate in a development and evaluation cycle."""

    id: str
    candidate: str
    cycle: int
    status: str
    diagnostics: tuple[str, ...] = ()
    artifacts: tuple[Artifact, ...] = ()
    prior: tuple[str, ...] = ()  # the attempts this one follows

    def __post_init__(self):
        if self.status not in ATTEMPT_STATUSES:
            raise ContractError(f"unknown attempt status {self.status!r}")


@dataclass(frozen=True)
class Evaluation:
    """What the evaluator recomputed for an attempt from its artifacts.

    ``correct`` is ``None`` when the evaluation cannot decide (an invalid,
    missing, or inconclusive attempt). ``resources`` are counted by the
    evaluator from the artifacts, never copied from the candidate's log.
    ``depends_on`` are the artifacts with the digests they had when
    evaluated."""

    attempt: str
    evaluator: str  # the evaluator's identity and version
    correct: bool | None
    metrics: Mapping[str, float]
    resources: Mapping[str, int]
    depends_on: tuple[Artifact, ...]
    code: str
    configuration: str


@dataclass(frozen=True)
class CandidateReport:
    """What a candidate says about its attempt: its own score, diagnostics,
    log, or cost. Stored apart from the evaluations and never one of them."""

    attempt: str
    claims_correct: bool | None
    details: Mapping[str, Any]
    label: str = UNVERIFIED


@dataclass(frozen=True)
class Claim:
    """A scientific claim, the runs that support it with the correctness each
    is claimed to have, its sources, and its scope."""

    id: str
    text: str
    scope: str
    runs: Mapping[str, bool]
    sources: tuple[str, ...] = ()


@dataclass(frozen=True)
class FrozenCandidate:
    """The selected candidate of a cycle, identified by the digest of its
    artifacts and a version."""

    candidate: str
    version: str
    cycle: int
    digest: str
    artifacts: tuple[Artifact, ...]


@dataclass(frozen=True)
class FinalEvaluation:
    """The final evaluation of a frozen candidate, bound to its digest and
    version, by a versioned evaluator, with the isolation it actually had.

    ``status`` and ``diagnostics`` are those of the evaluation, as for an
    attempt: a final evaluation that is invalid, failed, or inconclusive
    stays in the record with its reason."""

    candidate: str
    version: str
    cycle: int
    digest: str
    evaluation: Evaluation
    isolation: tuple[str, ...]
    status: str = COMPLETED
    diagnostics: tuple[str, ...] = ()

    def __post_init__(self):
        if self.status not in ATTEMPT_STATUSES:
            raise ContractError(f"unknown final evaluation status {self.status!r}")


@dataclass(frozen=True)
class Cycle:
    number: int
    reason: str


@dataclass(frozen=True)
class Invalidation:
    """An artifact that changed after an evaluation depended on it."""

    attempt: str
    evaluator: str
    path: str
    recorded: str | None
    current: str | None
    final: bool = False  # True: the artifact of a final evaluation

    def __str__(self) -> str:
        was = self.recorded[:12] if self.recorded else "absent"
        now = self.current[:12] if self.current else "absent"
        what = "final evaluation" if self.final else "evaluation"
        return (
            f"{what} of {self.attempt} by {self.evaluator} invalidated:"
            f" {self.path} was {was} and is {now}"
        )


def candidate_digest(artifacts: Iterable[Artifact]) -> str:
    """The digest of a candidate: of its artifacts' paths and digests."""
    return digest_value(sorted((a.path, a.sha256) for a in artifacts))


@dataclass
class Ledger:
    """The evaluator's record of one task over its cycles."""

    record: RunRecord
    cycles: list[Cycle] = field(default_factory=lambda: [Cycle(1, "first cycle")])
    attempts: list[Attempt] = field(default_factory=list)
    evaluations: list[Evaluation] = field(default_factory=list)
    reports: list[CandidateReport] = field(default_factory=list)
    claims: list[Claim] = field(default_factory=list)
    frozen: list[FrozenCandidate] = field(default_factory=list)
    finals: list[FinalEvaluation] = field(default_factory=list)

    @property
    def cycle(self) -> int:
        return self.cycles[-1].number

    def attempt(self, id_: str) -> Attempt | None:
        return next((a for a in self.attempts if a.id == id_), None)

    def final_of(self, candidate: str, cycle: int) -> FinalEvaluation | None:
        return next(
            (f for f in self.finals if (f.candidate, f.cycle) == (candidate, cycle)),
            None,
        )

    def frozen_of(self, candidate: str, cycle: int) -> FrozenCandidate | None:
        return next(
            (f for f in self.frozen if (f.candidate, f.cycle) == (candidate, cycle)),
            None,
        )

    def add_attempt(self, attempt: Attempt) -> None:
        if attempt.cycle != self.cycle:
            raise ContractError(
                f"attempt {attempt.id} names cycle {attempt.cycle}; the current"
                f" cycle is {self.cycle}"
            )
        if self.attempt(attempt.id) is not None:
            raise ContractError(f"attempt {attempt.id} is already recorded")
        if self.final_of(attempt.candidate, self.cycle) is not None:
            raise ContractError(
                f"{attempt.candidate} had its final evaluation in cycle"
                f" {self.cycle}; a further attempt starts a new cycle"
            )
        unknown = [p for p in attempt.prior if self.attempt(p) is None]
        if unknown:
            raise ContractError(f"attempt {attempt.id} follows unknown {unknown}")
        self.attempts.append(attempt)

    def add_evaluation(self, evaluation: Evaluation) -> None:
        if self.attempt(evaluation.attempt) is None:
            raise ContractError(f"no attempt {evaluation.attempt} to evaluate")
        self.evaluations.append(evaluation)

    def add_report(self, report: CandidateReport) -> None:
        if self.attempt(report.attempt) is None:
            raise ContractError(f"no attempt {report.attempt} to report on")
        if report.label != UNVERIFIED:
            raise ContractError("a candidate's report is labelled unverified")
        self.reports.append(report)

    def add_claim(self, claim: Claim) -> None:
        self.claims.append(claim)

    def freeze(
        self, candidate: str, version: str, artifacts: tuple[Artifact, ...]
    ) -> FrozenCandidate:
        """Freeze ``candidate`` for its final evaluation in this cycle."""
        if not artifacts or any(a.sha256 is None for a in artifacts):
            raise ContractError(f"{candidate} has no complete artifacts to freeze")
        if self.frozen_of(candidate, self.cycle) is not None:
            raise ContractError(f"{candidate} is already frozen in cycle {self.cycle}")
        if any(f.candidate == candidate and f.version == version for f in self.frozen):
            raise ContractError(f"version {version} of {candidate} is already used")
        frozen = FrozenCandidate(
            candidate, version, self.cycle, candidate_digest(artifacts), artifacts
        )
        self.frozen.append(frozen)
        return frozen

    def add_final(self, final: FinalEvaluation, root: Path) -> None:
        """Record the final evaluation of a frozen candidate, once per cycle,
        only while its artifacts are still those it was frozen with."""
        frozen = self.frozen_of(final.candidate, final.cycle)
        if final.cycle != self.cycle or frozen is None:
            raise ContractError(
                f"{final.candidate} is not frozen in the current cycle {self.cycle}"
            )
        if (final.version, final.digest) != (frozen.version, frozen.digest):
            raise ContractError(
                f"the final evaluation names version {final.version} with digest"
                f" {final.digest[:12]}; {final.candidate} was frozen as version"
                f" {frozen.version} with digest {frozen.digest[:12]}"
            )
        if self.final_of(final.candidate, self.cycle) is not None:
            raise ContractError(
                f"{final.candidate} already had its final evaluation in cycle"
                f" {self.cycle}; its feedback may not tune it: start a new cycle"
            )
        current = [
            Artifact(a.name, a.path, digest_file(root / a.path), a.kind)
            for a in frozen.artifacts
        ]
        if candidate_digest(current) != frozen.digest:
            raise ContractError(
                f"{final.candidate} changed after it was frozen as version"
                f" {frozen.version}; record a new cycle and freeze it again"
            )
        self.finals.append(final)

    def new_cycle(self, reason: str) -> Cycle:
        """Start a new development and evaluation cycle, saying why."""
        if not reason.strip():
            raise ContractError("a new cycle states its reason")
        cycle = Cycle(self.cycle + 1, reason)
        self.cycles.append(cycle)
        return cycle


def check(ledger: Ledger, root: Path) -> tuple[Invalidation, ...]:
    """Digest again every artifact an evaluation or a final evaluation
    depended on, and return those that changed."""
    found = []
    entries = [(e, False) for e in ledger.evaluations]
    entries += [(f.evaluation, True) for f in ledger.finals]
    for evaluation, final in entries:
        for artifact in evaluation.depends_on:
            now = digest_file(root / artifact.path)
            if now != artifact.sha256:
                found.append(
                    Invalidation(
                        evaluation.attempt,
                        evaluation.evaluator,
                        artifact.path,
                        artifact.sha256,
                        now,
                        final,
                    )
                )
    return tuple(found)


def _current(
    ledger: Ledger, attempt: str, stale: tuple[Invalidation, ...]
) -> list[Evaluation]:
    bad = {(i.attempt, i.evaluator) for i in stale if not i.final}
    return [
        e
        for e in ledger.evaluations
        if e.attempt == attempt and (e.attempt, e.evaluator) not in bad
    ]


_PRECEDENCE = (FAILED, NOT_EVALUATED, INCONCLUSIVE, COMPLETED, INDEPENDENTLY_CHECKED)


def _run_status(
    ledger: Ledger, attempt_id: str, asserted: bool, stale: tuple[Invalidation, ...]
) -> str:
    attempt = ledger.attempt(attempt_id)
    if attempt is None or attempt.status == MISSING:
        return NOT_EVALUATED
    if attempt.status == INVALID:
        return FAILED  # the evidence offered failed the evaluator's check
    evaluations = _current(ledger, attempt_id, stale)
    if not evaluations:
        return NOT_EVALUATED
    verdicts = {e.correct for e in evaluations}
    if attempt.status == INCONCLUSIVE or None in verdicts or len(verdicts) > 1:
        return INCONCLUSIVE
    if verdicts != {asserted}:
        return FAILED
    evaluators = {e.evaluator for e in evaluations}
    return INDEPENDENTLY_CHECKED if len(evaluators) > 1 else COMPLETED


def claim_status(
    ledger: Ledger, claim: Claim, stale: tuple[Invalidation, ...] = ()
) -> str:
    """The evidence status of ``claim``, from the evaluations of its runs
    that ``stale`` (the result of ``check``) has not invalidated.

    A run counts as failed when its evaluation contradicts the correctness
    the claim asserts for it, or its artifact was invalid; as not evaluated
    when it is missing, unevaluated, or its evaluation was invalidated; as
    inconclusive when the evaluation cannot decide or evaluators disagree;
    as independently checked when evaluators of different identities agree.
    The claim takes the first of failed, not evaluated, inconclusive,
    completed, independently checked that any of its runs has; a claim
    without a run is not evaluated."""
    if not claim.runs:
        return NOT_EVALUATED
    statuses = {_run_status(ledger, a, v, stale) for a, v in claim.runs.items()}
    return next(s for s in _PRECEDENCE if s in statuses)


@dataclass(frozen=True)
class AttemptRow:
    attempt: str
    candidate: str
    cycle: int
    status: str
    correct: bool | None
    metrics: Mapping[str, float]
    # "none"; "agrees" or "disagrees" with the evaluation's verdict;
    # "undecided" when the evaluation has no verdict to compare it with.
    report: str
    invalidated: bool
    diagnostics: tuple[str, ...]


@dataclass(frozen=True)
class Summary:
    """Every attempt, every claim, and every final evaluation of a ledger.

    ``counts`` holds every attempt status, zero included; ``correct`` and
    ``total`` give the share of correct attempts over every attempt, so that
    an invalid, missing, failed, or inconclusive attempt lowers it instead of
    leaving it."""

    rows: tuple[AttemptRow, ...]
    counts: Mapping[str, int]
    correct: int
    total: int
    claims: tuple[tuple[Claim, str], ...]
    finals: tuple[tuple[FinalEvaluation, bool], ...]  # with "invalidated"
    invalidations: tuple[Invalidation, ...]

    def text(self) -> str:
        verdict = {True: "correct", False: "not correct", None: "undecided"}
        lines = [f"Attempts: {self.total}, correct {self.correct} of {self.total}"]
        lines += [f"  {s}: {self.counts[s]}" for s in ATTEMPT_STATUSES]
        for r in self.rows:
            flag = ", evaluation invalidated" if r.invalidated else ""
            note = f" ({'; '.join(r.diagnostics)})" if r.diagnostics else ""
            lines.append(
                f"{r.attempt} [{r.candidate}, cycle {r.cycle}]: {r.status},"
                f" {verdict[r.correct]}, candidate's report {r.report}"
                f" ({UNVERIFIED}){flag}{note}"
            )
        for claim, status in self.claims:
            lines.append(f"claim {claim.id}: {status} ({claim.scope})")
        for final, stale in self.finals:
            flag = ", invalidated" if stale else ""
            note = f" ({'; '.join(final.diagnostics)})" if final.diagnostics else ""
            lines.append(
                f"final evaluation of {final.candidate} version {final.version},"
                f" cycle {final.cycle}, digest {final.digest[:12]},"
                f" by {final.evaluation.evaluator}: {final.status},"
                f" {verdict[final.evaluation.correct]}{flag}{note}"
            )
        lines += [str(i) for i in self.invalidations]
        return "\n".join(lines)


def summary(ledger: Ledger, root: Path) -> Summary:
    """The ledger in rows, with every artifact digested again."""
    stale = check(ledger, root)
    rows = []
    for a in ledger.attempts:
        evaluations = _current(ledger, a.id, stale)
        verdicts = {e.correct for e in evaluations}
        correct = verdicts.pop() if len(verdicts) == 1 else None
        metrics = evaluations[-1].metrics if evaluations else {}
        reports = [r for r in ledger.reports if r.attempt == a.id]
        if not reports or reports[-1].claims_correct is None:
            report = "none"
        elif correct is None:
            report = "undecided"
        else:
            agrees = reports[-1].claims_correct == correct
            report = "agrees" if agrees else "disagrees"
        invalidated = any(i.attempt == a.id for i in stale if not i.final)
        rows.append(
            AttemptRow(
                a.id,
                a.candidate,
                a.cycle,
                a.status,
                correct,
                metrics,
                report,
                invalidated,
                a.diagnostics,
            )
        )
    counts = {s: sum(r.status == s for r in rows) for s in ATTEMPT_STATUSES}
    finals = tuple(
        (
            f,
            any(
                i.final
                and (i.attempt, i.evaluator)
                == (f.evaluation.attempt, f.evaluation.evaluator)
                for i in stale
            ),
        )
        for f in ledger.finals
    )
    return Summary(
        tuple(rows),
        counts,
        sum(r.correct is True for r in rows),
        len(rows),
        tuple((c, claim_status(ledger, c, stale)) for c in ledger.claims),
        finals,
        stale,
    )


def _artifacts(items: list) -> tuple[Artifact, ...]:
    return tuple(Artifact(**a) for a in items)


def _evaluation(data: dict) -> Evaluation:
    return Evaluation(
        **{**data, "depends_on": _artifacts(data["depends_on"])},
    )


def save(ledger: Ledger, path: Path) -> None:
    """Write ``ledger`` to ``path`` as JSON."""
    data = {"format": FORMAT, **asdict(ledger)}
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load(path: Path) -> Ledger:
    """Read a ledger written by ``save``."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.pop("format", None) != FORMAT:
        raise ValueError(f"{path} is not an evidence ledger of format {FORMAT}")
    r = data["record"]
    record = RunRecord(
        **{
            **r,
            "assumptions": tuple(r["assumptions"]),
            "seeds": tuple(r["seeds"]),
        }
    )
    attempts = [
        Attempt(
            **{
                **a,
                "diagnostics": tuple(a["diagnostics"]),
                "artifacts": _artifacts(a["artifacts"]),
                "prior": tuple(a["prior"]),
            }
        )
        for a in data["attempts"]
    ]
    return Ledger(
        record=record,
        cycles=[Cycle(**c) for c in data["cycles"]],
        attempts=attempts,
        evaluations=[_evaluation(e) for e in data["evaluations"]],
        reports=[CandidateReport(**r) for r in data["reports"]],
        claims=[Claim(**{**c, "sources": tuple(c["sources"])}) for c in data["claims"]],
        frozen=[
            FrozenCandidate(**{**f, "artifacts": _artifacts(f["artifacts"])})
            for f in data["frozen"]
        ],
        finals=[
            FinalEvaluation(
                **{
                    **f,
                    "evaluation": _evaluation(f["evaluation"]),
                    "isolation": tuple(f["isolation"]),
                    "diagnostics": tuple(f.get("diagnostics", ())),
                }
            )
            for f in data["finals"]
        ],
    )
