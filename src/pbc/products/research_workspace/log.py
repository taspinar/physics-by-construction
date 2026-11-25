"""The follow-up log of the workspace: findings, the evidence that answers
them, revisions of the wording, and the human's decisions, in one chain.

The rules of ``pbc.research.followup`` applied to evidence that is a record
of an analysis (a check's result with the digest of what it read), not a
scripted route's ``Record``: a finding is of the kind ``EVIDENCE`` or
``WORDING``; a revision of the prose never resolves a finding that asks for
evidence; a finding an agent proposes is accepted only through a recomputed
check. Entries are only added, each chained to the one before.
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from pbc.evidence.records import digest_value
from pbc.research.followup import (
    EVIDENCE,
    INCONCLUSIVE,
    KINDS,
    OPEN,
    RESOLVED,
    REWORDED,
    WORDING,
)

FINDING = "finding"
EVIDENCE_ENTRY = "evidence"
REVISION = "revision"
DECISION = "decision"
ENTRY_KINDS = (FINDING, EVIDENCE_ENTRY, REVISION, DECISION)
ACCEPTED = "accepted"
DECLINED = "declined"
PROPOSED = "proposed"
SCRIPTED = "scripted reviewer"


class LogRefused(ValueError):
    """An entry the log does not accept, with the reason."""


@dataclass(frozen=True)
class Entry:
    number: int
    kind: str
    content: Mapping[str, Any]
    previous: str
    digest: str


def _digest(number: int, kind: str, content: Any, previous: str) -> str:
    return digest_value([number, kind, content, previous])


class Log:
    def __init__(self, entries: Sequence[Entry] = ()) -> None:
        self.entries: list[Entry] = list(entries)

    def _add(self, kind: str, content: Mapping[str, Any]) -> Entry:
        content = json.loads(json.dumps(dict(content)))
        number = len(self.entries) + 1
        previous = self.entries[-1].digest if self.entries else ""
        entry = Entry(
            number, kind, content, previous, _digest(number, kind, content, previous)
        )
        self.entries.append(entry)
        return entry

    def of(self, kind: str) -> list[Entry]:
        return [e for e in self.entries if e.kind == kind]

    def findings(self) -> dict[str, Entry]:
        return {e.content["key"]: e for e in self.of(FINDING)}

    def find(
        self, key: str, claim: str, reviewer: str, text: str, kind: str, check: str
    ) -> Entry:
        """Record a finding. A finding by anyone but the scripted reviewer is
        ``proposed`` until a recomputed check accepts it (``accept``)."""
        if kind not in KINDS:
            raise LogRefused(f"unknown kind {kind!r}")
        if key in self.findings():
            raise LogRefused(f"there is already a finding {key!r}")
        state = ACCEPTED if reviewer == SCRIPTED else PROPOSED
        return self._add(
            FINDING,
            {
                "key": key,
                "claim": claim,
                "reviewer": reviewer,
                "text": text,
                "kind": kind,
                "check": check,
                "state": state,
            },
        )

    def evidence(
        self, finding: str, check: str, passed: bool | None, digest: str
    ) -> Entry:
        """Record the result of a recomputed check for ``finding``: decided
        when it passed or failed, inconclusive when it could not decide."""
        if finding not in self.findings():
            raise LogRefused(f"there is no finding {finding!r}")
        return self._add(
            EVIDENCE_ENTRY,
            {"finding": finding, "check": check, "passed": passed, "digest": digest},
        )

    def revise(self, answers: Sequence[str], text: str) -> Entry:
        unknown = [a for a in answers if a not in self.findings()]
        if unknown:
            raise LogRefused(f"no findings {unknown}")
        return self._add(REVISION, {"answers": list(answers), "text": text})

    def decide(
        self, subject: str, decision: str, reason: str, revisit: str, by: str
    ) -> Entry:
        """A human's decision about a branch, a question, or a finding, with
        its reason and what would warrant revisiting it."""
        if not reason.strip():
            raise LogRefused("a decision needs its reason")
        return self._add(
            DECISION,
            {
                "subject": subject,
                "decision": decision,
                "reason": reason,
                "revisit": revisit,
                "by": by,
            },
        )

    def accepted(self, finding: str) -> bool:
        """The log already holds the acceptance of ``finding``."""
        return any(
            e.content["subject"] == finding and e.content["decision"] == ACCEPTED
            for e in self.of(DECISION)
        )

    def accept(self, finding: str, check_passed: bool | None, by: str) -> Entry:
        """Accept a proposed finding, only through its recomputed check: the
        check must have failed (the finding is real) on record. A finding
        is accepted once; a second acceptance is refused, so that the
        decisions record each of the human's decisions once."""
        entry = self.findings().get(finding)
        if entry is None:
            raise LogRefused(f"there is no finding {finding!r}")
        if self.accepted(finding):
            raise LogRefused(f"{finding} is already accepted")
        if check_passed is not False:
            raise LogRefused(
                f"{finding} is accepted only when its recomputed check"
                f" {entry.content['check']!r} confirms it; it did not"
            )
        return self.decide(
            finding, ACCEPTED, "its recomputed check confirms it", "", by
        )


def state(log: Log, finding: str) -> str:
    """The finding's state: what the evidence decided, never what a revision
    says (the rule of ``pbc.research.followup.status``)."""
    entry = log.findings()[finding]
    if entry.content["kind"] == WORDING:
        revised = any(finding in e.content["answers"] for e in log.of(REVISION))
        return REWORDED if revised else OPEN
    evidence = [e for e in log.of(EVIDENCE_ENTRY) if e.content["finding"] == finding]
    if any(e.content["passed"] is True for e in evidence):
        return RESOLVED
    return INCONCLUSIVE if evidence else OPEN


def verify(entries: Sequence[Entry]) -> list[str]:
    """The problems of the chain: an entry out of order, a broken link, or a
    digest that does not match its content."""
    found = []
    previous = ""
    for position, entry in enumerate(entries, start=1):
        if entry.number != position:
            found.append(f"log entry {entry.number} stands at position {position}")
        if entry.previous != previous:
            found.append(f"log entry {entry.number}: the chain is broken")
        if (
            _digest(entry.number, entry.kind, entry.content, entry.previous)
            != entry.digest
        ):
            found.append(f"log entry {entry.number}: its digest does not match")
        previous = entry.digest
    return found


def save(log: Log, path: Path) -> None:
    data = [asdict(e) for e in log.entries]
    Path(path).write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")


def load(path: Path) -> Log:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Log([Entry(**e) for e in data])


__all__ = [
    "EVIDENCE",
    "INCONCLUSIVE",
    "OPEN",
    "RESOLVED",
    "REWORDED",
    "WORDING",
    "Log",
    "state",
    "verify",
]
