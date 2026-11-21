"""Lesson RR5 (F153): the roles of an investigation, a human step, and
checks instead of votes.

An investigation of a piece of code has roles: one **extracts** the claim
from what was handed over, one **implements** the pieces, one **reviews**
them (the three reviewers of ``pbc.agents.review_lab``, replayed), and a
**human** decides what happens next. Each role has an interface
(``INTERFACES``): the fields of the board it may read and the one it may
write. ``Board`` refuses a read or a write outside it, and a second write of
a field: a correction is a steering entry, never an overwrite.

The extraction states, for each property of the claim, the words of the
handover it rests on; a quote the handover does not contain is refused. The
human steers by a small set of actions (``ACTIONS``): accept a piece, send
it back, narrow its claim, or require a check. No action sets the result of
a check, and an acceptance is refused while a recomputed check that applies
to the piece's claim failed (``steer``).

A disagreement is decided by the recomputed checks, not by counting
reviewers: ``votes`` counts the decisions of the recorded panel sessions of
lesson AE6 (``review_lab.PANEL_SESSIONS``), and ``checked`` decides the same
cases from the checks those sessions ran, by the contract's rule
(``pbc.evidence.reviewers.contract_rule``), for the panel of four and each
panel of three.

``pbc.agents.review_lab`` is used as it is; nothing here changes it, and
nothing here calls a model.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Any

from pbc.agents.review_lab import (
    CANDIDATES,
    CASES,
    CLAIM,
    PANEL_SESSIONS,
    REVIEWERS,
    Verdict,
    decisions,
    replay_panel,
    verdicts,
)
from pbc.evidence.reviewers import applies, contract_rule
from pbc.verification.checks import CHECKS, Claim

# What was handed over with the two pieces, in words.
HANDOVER = (
    "Both pieces are a first-order method for Newton's second law, and the"
    " energy of a harmonic oscillator they step stays in a band that does not"
    " grow."
)


class OutOfBounds(ValueError):
    """A read, a write, or a steering action that an interface forbids."""


@dataclass(frozen=True)
class Interface:
    """A role: the fields of the board it may read and those it may write."""

    role: str
    reads: tuple[str, ...]
    writes: tuple[str, ...]


# region: interfaces
INTERFACES = (
    Interface("extraction", reads=("handover",), writes=("claim",)),
    Interface("implementation", reads=("claim",), writes=("pieces",)),
    Interface("review", reads=("claim", "pieces"), writes=("verdicts",)),
    Interface(
        "human",
        reads=("handover", "claim", "pieces", "verdicts", "steering"),
        writes=("steering",),
    ),
)
# endregion: interfaces


def interface(role: str) -> Interface:
    for candidate in INTERFACES:
        if candidate.role == role:
            return candidate
    raise OutOfBounds(f"there is no role {role!r}")


@dataclass
class Board:
    """The fields of one investigation and who wrote each, in order."""

    fields: dict[str, Any] = field(default_factory=lambda: {"handover": HANDOVER})
    log: list[tuple[str, str]] = field(default_factory=list)

    def read(self, role: str, name: str) -> Any:
        if name not in interface(role).reads:
            raise OutOfBounds(f"the {role} role may not read {name}")
        if name not in self.fields:
            raise OutOfBounds(f"{name} has not been written yet")
        return self.fields[name]

    def write(self, role: str, name: str, value: Any) -> None:
        if name not in interface(role).writes:
            raise OutOfBounds(f"the {role} role may not write {name}")
        if name == "steering":
            self.fields.setdefault(name, []).append(value)
        elif name in self.fields:
            raise OutOfBounds(
                f"{name} is already written; a correction is a steering entry"
            )
        else:
            self.fields[name] = value
        self.log.append((role, name))


@dataclass(frozen=True)
class Extraction:
    """The claim as the extraction role states it, with the words of the
    handover that each property rests on."""

    order: int
    bounded_energy: bool
    quotes: Mapping[str, str]

    @property
    def claim(self) -> Claim:
        return Claim(order=self.order, bounded_energy=self.bounded_energy)


# The extraction of this lesson, written by the author.
EXTRACTION = Extraction(
    order=1,
    bounded_energy=True,
    quotes={
        "order": "a first-order method",
        "bounded_energy": "stays in a band that does not grow",
    },
)


def extraction_problems(extraction: Extraction, handover: str) -> list[str]:
    """Every property of the extracted claim without words of the handover
    to rest on; empty when each one has them."""
    claimed = ["order"] + (["bounded_energy"] if extraction.bounded_energy else [])
    found = []
    for name in claimed:
        quote = extraction.quotes.get(name)
        if not quote:
            found.append(f"{name} has no words of the handover")
        elif quote not in handover:
            found.append(f"{name} rests on {quote!r}, which the handover does not say")
    return found


def extract(board: Board, extraction: Extraction) -> None:
    """The extraction role writes the claim, if every property is quoted
    from the handover and the claim is the one the reviewers reviewed."""
    handover = board.read("extraction", "handover")
    found = extraction_problems(extraction, handover)
    if extraction.claim != CLAIM:
        found.append(
            f"the claim {extraction.claim} is not the claim {CLAIM} the"
            " recorded reviewers were given"
        )
    if found:
        raise OutOfBounds("; ".join(found))
    board.write("extraction", "claim", extraction.claim)


def implement(board: Board) -> None:
    """The implementation role reads the claim and writes the pieces."""
    board.read("implementation", "claim")
    board.write("implementation", "pieces", tuple(CANDIDATES))


def review(board: Board, transcripts: Mapping[str, Any]) -> None:
    """The review role writes the verdicts the build recomputed from the
    replayed runs of the three reviewers; their words are not read."""
    board.read("review", "pieces")
    found = [v for r in REVIEWERS for v in verdicts(r, transcripts[r.id])]
    board.write("review", "verdicts", tuple(found))


ACCEPT, SEND_BACK, NARROW, REQUIRE = "accept", "send back", "narrow", "require"
ACTIONS = (ACCEPT, SEND_BACK, NARROW, REQUIRE)


@dataclass(frozen=True)
class Steering:
    """One decision of the human on one piece, with its reason; ``drop``
    names the property a narrowing removes, ``check`` the check a
    requirement adds."""

    action: str
    piece: int
    reason: str
    drop: str | None = None
    check: str | None = None


def words(claim: Claim) -> str:
    """The claim in words: its order, with a bounded energy or without."""
    order = {1: "first", 2: "second", 4: "fourth"}.get(claim.order, f"{claim.order}th")
    energy = "and a bounded energy" if claim.bounded_energy else "only"
    return f"{order} order {energy}"


def steering(board: Board) -> list[Steering]:
    """The human's steering entries, read through the human's interface;
    empty before the first."""
    if "steering" not in board.fields:
        return []
    return board.read("human", "steering")


@dataclass(frozen=True)
class _Claimed:
    """A piece's claim in the shape the contract's rule ``applies`` reads."""

    claim: Claim


def claim_of(board: Board, piece: int) -> Claim:
    """The claim of ``piece`` after the narrowings the human recorded."""
    claim = board.read("human", "claim")
    for entry in steering(board):
        if entry.action == NARROW and entry.piece == piece:
            claim = Claim(order=claim.order, bounded_energy=False)
    return claim


def failed_checks(board: Board, piece: int) -> list[str]:
    """The recomputed checks of ``piece`` that failed and apply to its claim."""
    claimed = _Claimed(claim_of(board, piece))
    return sorted(
        {
            v.check
            for v in board.read("human", "verdicts")
            if v.candidate == piece and not v.passed and applies(v.check, claimed)
        }
    )


def _not_run(board: Board, piece: int) -> list[str]:
    ran = {v.check for v in board.read("human", "verdicts") if v.candidate == piece}
    required = {
        e.check for e in steering(board) if e.action == REQUIRE and e.piece == piece
    }
    return sorted(required - ran)


def steer(board: Board, entry: Steering) -> None:
    """Record a decision of the human, or refuse it. An acceptance is refused
    while a check that applies to the piece's claim failed, or a required
    check was not run: the human changes the question, not the answer."""
    if entry.action not in ACTIONS:
        raise OutOfBounds(
            f"{entry.action!r} is not a steering action; no action sets the"
            " result of a check"
        )
    if not entry.reason.strip():
        raise OutOfBounds("a steering entry states its reason")
    if entry.piece not in board.read("human", "pieces"):
        raise OutOfBounds(f"there is no piece {entry.piece}")
    if entry.action == NARROW and entry.drop != "bounded_energy":
        raise OutOfBounds("a claim is narrowed by dropping its bounded energy")
    if entry.action == REQUIRE and entry.check not in CHECKS:
        raise OutOfBounds(f"there is no check {entry.check!r}")
    if entry.action == ACCEPT:
        failed = failed_checks(board, entry.piece)
        missing = _not_run(board, entry.piece)
        if failed or missing:
            raise OutOfBounds(
                f"piece {entry.piece} cannot be accepted for the claim"
                f" {words(claim_of(board, entry.piece))!r}: failed {failed or 'none'},"
                f" required and not run {missing or 'none'}; narrow the claim"
                " or send the piece back"
            )
    board.write("human", "steering", entry)


def decision(board: Board, piece: int) -> str:
    """Where ``piece`` stands after the human's last acceptance or sending
    back, with the claim it is accepted for."""
    last = None
    for entry in steering(board):
        if entry.piece == piece and entry.action in (ACCEPT, SEND_BACK):
            last = entry
    if last is None:
        return "open"
    if last.action == SEND_BACK:
        return f"sent back to implementation: {last.reason}"
    return f"accepted for the claim {words(claim_of(board, piece))!r}: {last.reason}"


# --- Not a vote: the recorded panel of lesson AE6, replayed. ---


def panel(directory: Path) -> tuple[dict[str, dict[int, bool]], list[Verdict]]:
    """The decisions of every recorded panel session, by its name, and the
    recomputed verdicts of the checks each ran, with the session's name as
    the reviewer."""
    decided = {}
    found = []
    for session in PANEL_SESSIONS:
        _, transcript = replay_panel(session, directory)
        decided[session.name] = decisions(transcript)
        found += [
            Verdict(
                session.name, v.candidate, v.check, v.measured, v.tolerance, v.passed
            )
            for v in verdicts(session.reviewer, transcript)
        ]
    return decided, found


def panels() -> list[tuple[str, ...]]:
    """The panel of all four sessions, then each panel of three."""
    names = [s.name for s in PANEL_SESSIONS]
    return [tuple(names), *combinations(names, len(names) - 1)]


def votes(
    decided: Mapping[str, Mapping[int, bool]], case: int, sessions: Iterable[str]
) -> tuple[int, int, str]:
    """The sessions' decisions on ``case`` counted as votes: accept, reject,
    and the majority (``tie`` when there is none)."""
    cast = [decided[s][case] for s in sessions if case in decided[s]]
    accept, reject = sum(cast), len(cast) - sum(cast)
    if accept == reject:
        return accept, reject, "tie"
    return accept, reject, "accept" if accept > reject else "reject"


def checked(found: Iterable[Verdict], case: int, sessions: Iterable[str]) -> str:
    """The decision on ``case`` from the recomputed checks the ``sessions``
    ran: a failed check that applies to the case's claim rejects it."""
    kept = [v for v in found if v.reviewer in set(sessions)]
    decided = contract_rule(kept, CASES)[case]
    if decided is None:
        return "undecided"
    return "accept" if decided else "reject"


def failing(found: Iterable[Verdict], case: int) -> list[str]:
    """The checks that failed on ``case`` and apply to its claim."""
    return sorted(
        {
            v.check
            for v in found
            if v.candidate == case and not v.passed and applies(v.check, CASES[case])
        }
    )
