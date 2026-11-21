"""Review findings, the experiments that answer them, and the claim they
revise (lesson RR6).

A ``Finding`` of a review says what is wrong with a claim and what kind of
answer it asks for: new evidence (``EVIDENCE``) or other words
(``WORDING``). A finding that asks for evidence opens a knowledge gap, and
the gap is answered by a declared ``FollowUp``: one change of the claim's
specification, run by the scripted route of ``pbc.agents.specification``,
with two competing explanations and the verdicts of the route each
predicts. A test is accepted only when it ``discriminates``: no verdict is
predicted by both explanations, so that its outcome can count for one
against the other.

Everything enters a ``Log`` in order: the claim with the digests of the
records it rests on, the findings, the tests as declared, the evidence (a
route's record by its digest), the revisions of the claim, and the
decisions about each line of follow-up. The log only grows, and each entry
names the digest of the entry before it (``verify_log``). Evidence names a
test declared before it, and a record that is new: not one the claim
already rested on, and not one recorded before the finding.

``status`` derives the state of a finding from the log. A finding that asks
for evidence is resolved only by evidence that decided one of its tests;
evidence that decided nothing leaves it inconclusive; without evidence it
is open. A revision of the claim never changes it: rewriting the prose is
not new evidence. Only a finding about the wording is resolved by a
revision that names it.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from pbc.agents.specification import Record
from pbc.evidence.records import digest_value

EVIDENCE = "evidence"  # the finding asks for new evidence
WORDING = "wording"  # the finding asks for other words
KINDS = (EVIDENCE, WORDING)

OPEN = "open"
INCONCLUSIVE = "inconclusive"
RESOLVED = "resolved by new evidence"
REWORDED = "resolved by a revision of the wording"

CONTINUE = "continue"
STOP = "stop"

CLAIM = "claim"
FINDING = "finding"
DECLARED = "test declared"
RECORDED = "evidence recorded"
REVISED = "claim revised"
DECIDED = "branch decided"


class FollowUpRefused(ValueError):
    """An entry the log does not accept, with the reason."""


@dataclass(frozen=True)
class Finding:
    """What a reviewer found wrong with the claim ``claim``, and the kind of
    answer it asks for."""

    key: str
    claim: str
    reviewer: str
    text: str
    kind: str


@dataclass(frozen=True)
class Explanation:
    """One answer to a gap, and the verdicts of the route it predicts for
    the test it is declared with."""

    name: str
    statement: str
    predicts: tuple[str, ...]


@dataclass(frozen=True)
class FollowUp:
    """A follow-up experiment, declared before it runs: the finding it
    answers, the one change of the claim's specification, the
    specification it runs, and the two explanations it decides between."""

    key: str
    finding: str
    change: str
    specification: Mapping[str, Any]
    explanations: tuple[Explanation, Explanation]


@dataclass(frozen=True)
class Entry:
    """One entry of the log: its number, its kind, what it records, the
    digest of the entry before it, and its own digest."""

    number: int
    kind: str
    content: Mapping[str, Any]
    previous: str
    digest: str


def record_digest(record: Record) -> str:
    """The digest of what a route did: every run, the bracket, the
    criteria, and the verdict."""
    return digest_value(
        {
            "runs": [
                [r.number, r.stage, dict(r.arguments), r.value] for r in record.runs
            ],
            "stop": record.stop,
            "bracket": list(record.bracket) if record.bracket else None,
            "criteria": dict(record.criteria),
            "verdict": record.verdict,
        }
    )


def discriminates(test: FollowUp) -> list[str]:
    """The reasons ``test`` cannot decide between its explanations: an
    explanation that predicts no verdict, or a verdict both predict. An
    empty list when its outcome counts for one against the other."""
    first, second = test.explanations
    found = [
        f"{e.name} predicts no outcome" for e in test.explanations if not e.predicts
    ]
    for verdict in sorted(set(first.predicts) & set(second.predicts)):
        found.append(f"both explanations predict {verdict!r}")
    return found


def decided(test: FollowUp, verdict: str) -> str | None:
    """The explanation whose prediction the route's ``verdict`` met, or
    ``None`` when it met neither: the test decided nothing."""
    for explanation in test.explanations:
        if verdict in explanation.predicts:
            return explanation.name
    return None


def _entry_digest(number: int, kind: str, content: Any, previous: str) -> str:
    return digest_value([number, kind, content, previous])


@dataclass
class Log:
    """The record of one claim's follow-up, in order. Entries are only
    added; a changed decision is a new entry."""

    entries: list[Entry] = field(default_factory=list)
    findings: dict[str, Finding] = field(default_factory=dict)
    tests: dict[str, FollowUp] = field(default_factory=dict)

    def _add(self, kind: str, content: Mapping[str, Any]) -> Entry:
        number = len(self.entries) + 1
        previous = self.entries[-1].digest if self.entries else ""
        content = dict(content)
        entry = Entry(
            number,
            kind,
            content,
            previous,
            _entry_digest(number, kind, content, previous),
        )
        self.entries.append(entry)
        return entry

    def _of(self, kind: str) -> list[Entry]:
        return [e for e in self.entries if e.kind == kind]

    def claim(self, key: str, text: str, records: Sequence[str]) -> Entry:
        """The claim under review and the digests of the records it rests on."""
        if self.entries:
            raise FollowUpRefused("the claim is the first entry of its log")
        return self._add(CLAIM, {"key": key, "text": text, "records": list(records)})

    def find(self, finding: Finding) -> Entry:
        if finding.kind not in KINDS:
            raise FollowUpRefused(
                f"{finding.key}: the kind {finding.kind!r} is unknown"
            )
        if finding.key in self.findings:
            raise FollowUpRefused(f"{finding.key} is already in the log")
        self.findings[finding.key] = finding
        return self._add(
            FINDING,
            {"key": finding.key, "kind": finding.kind, "text": finding.text},
        )

    def declare(self, test: FollowUp) -> Entry:
        """Declare ``test`` before it runs: it answers a finding that asks
        for evidence, and it discriminates."""
        finding = self.findings.get(test.finding)
        if finding is None:
            raise FollowUpRefused(f"{test.key}: the log has no finding {test.finding}")
        if finding.kind != EVIDENCE:
            raise FollowUpRefused(
                f"{test.key}: {test.finding} asks for other words, not for a test"
            )
        problems = discriminates(test)
        if problems:
            raise FollowUpRefused(
                f"{test.key} does not discriminate: {'; '.join(problems)}"
            )
        self.tests[test.key] = test
        return self._add(
            DECLARED,
            {
                "key": test.key,
                "finding": test.finding,
                "specification": digest_value(test.specification),
                "predictions": {e.name: list(e.predicts) for e in test.explanations},
            },
        )

    def record(self, test: str, record: Record) -> Entry:
        """The route's record of a declared test, by its digest. The record
        is new: neither one the claim rested on nor one already in the log."""
        if test not in self.tests:
            raise FollowUpRefused(f"{test} was not declared before its evidence")
        if any(e.content["test"] == test for e in self._of(RECORDED)):
            raise FollowUpRefused(
                f"{test} already has its evidence; declare a new test"
            )
        digest = record_digest(record)
        old = set(self.entries[0].content["records"])
        old |= {e.content["record"] for e in self._of(RECORDED)}
        if digest in old:
            raise FollowUpRefused(f"{test}: the record is not new evidence")
        return self._add(
            RECORDED,
            {
                "test": test,
                "record": digest,
                "verdict": record.verdict,
                "decided": decided(self.tests[test], record.verdict),
            },
        )

    def revise(
        self, text: str, answers: Sequence[str], evidence: Sequence[str]
    ) -> Entry:
        """A new text of the claim, the findings it answers, and the tests
        whose evidence it rests on."""
        unknown = [k for k in answers if k not in self.findings]
        if unknown:
            raise FollowUpRefused(f"the log has no finding {', '.join(unknown)}")
        return self._add(
            REVISED,
            {"text": text, "answers": list(answers), "evidence": list(evidence)},
        )

    def decide(self, finding: str, decision: str, reason: str, revisit: str) -> Entry:
        """Continue or stop the line of follow-up of ``finding``, with the
        reason and the condition that would warrant revisiting it."""
        if decision not in (CONTINUE, STOP):
            raise FollowUpRefused(f"the decision {decision!r} is unknown")
        if not reason.strip():
            raise FollowUpRefused("a decision needs its reason")
        return self._add(
            DECIDED,
            {
                "finding": finding,
                "decision": decision,
                "reason": reason,
                "revisit": revisit,
            },
        )

    def evidence_of(self, finding: str) -> list[Entry]:
        """The evidence recorded for the tests of ``finding``, in order."""
        return [
            e
            for e in self._of(RECORDED)
            if self.tests[e.content["test"]].finding == finding
        ]


def status(log: Log, finding: str) -> str:
    """The state of ``finding`` in ``log``: what the evidence decided, never
    what a revision says."""
    if log.findings[finding].kind == WORDING:
        revised = any(finding in e.content["answers"] for e in log._of(REVISED))
        return REWORDED if revised else OPEN
    evidence = log.evidence_of(finding)
    if any(e.content["decided"] is not None for e in evidence):
        return RESOLVED
    return INCONCLUSIVE if evidence else OPEN


def verify_log(entries: Sequence[Entry]) -> list[str]:
    """The problems of a log's entries: an entry out of order, a broken
    chain, or an entry whose digest does not match its content. An empty
    list when none is found."""
    found = []
    previous = ""
    for position, entry in enumerate(entries, start=1):
        if entry.number != position:
            found.append(f"entry {entry.number} stands at position {position}")
        if entry.previous != previous:
            found.append(
                f"entry {entry.number}: the chain to the entry before is broken"
            )
        if _entry_digest(entry.number, entry.kind, entry.content, entry.previous) != (
            entry.digest
        ):
            found.append(f"entry {entry.number}: its digest does not match its content")
        previous = entry.digest
    return found
