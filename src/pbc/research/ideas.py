"""Candidate research questions, assessed before any run, and their archive.

An ``Idea`` is a question with its proposer, a draft specification in the
seven parts of ``pbc.agents.specification`` (or none, when the question
cannot be written in the laboratory's terms), and the proposer's own
ratings of it. ``assess`` computes, without running anything, what can be
known about it beforehand:

- **feasible**: the draft passes ``parse`` against the laboratory, so every
  action exists and every setting is within its bounds;
- **falsifiable**: the predicted bound lies inside the varied range by at
  least the resolution from each end, so that a result of the route can
  fall on either side of it;
- **within budget**: the number of runs the route makes for the draft,
  counted from its procedure (``runs_needed``), is no more than the draft's
  budget;
- **contribution**: what the archive of answered questions already holds
  for the same action and settings: a replication of an answered question,
  an extension of one (the same action, another setting), or a question
  answered by a formula.

Interest is not computed: it is a judgement, recorded with its author and
reason. ``select`` applies a rule declared before the assessment and reads
no self-rating; the ratings are kept beside the assessment and shown, and
nothing else. ``Archive`` keeps every idea and every decision, chained by
digest, so that an entry edited, or removed before the last, is found when
the digests after it were not recomputed. The chain has no head recorded
outside its entries: a removed last entry, or a chain recomputed after an
edit, is not found.
"""

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pbc.agents.specification import (
    SCAN_POINTS,
    Laboratory,
    Specification,
    SpecificationRejected,
    parse,
)
from pbc.evidence.records import digest_value

# The proposer's ratings of an idea, each from 1 to 5.
RATINGS = ("feasibility", "interest", "novelty")
# A person's judgement of interest, in order.
INTEREST = ("low", "medium", "high")

REPLICATION = "replication"
EXTENSION = "extension"
BY_FORMULA = "answered by a formula"
# Better contributions first.
CONTRIBUTIONS = (EXTENSION, REPLICATION, BY_FORMULA)

SELECTED = "selected"
DEFERRED = "deferred"
REJECTED = "rejected"


@dataclass(frozen=True)
class Idea:
    """A candidate question: its ``key``, the question in words, who
    proposed it, the draft specification (``None`` when the question cannot
    be written in the laboratory's terms), and the proposer's own ratings,
    by ``RATINGS``."""

    key: str
    question: str
    proposer: str
    draft: Mapping[str, Any] | None
    self_ratings: Mapping[str, int]


@dataclass(frozen=True)
class Answered:
    """A question the archive already answers: the action, the settings of
    its fixed variables, and where the answer is published."""

    action: str
    settings: Mapping[str, float]
    source: str
    by_formula: bool = False


@dataclass(frozen=True)
class Judgement:
    """A person's judgement of an idea's interest, one of ``INTEREST``, with
    its author and reason. It is an opinion, recorded as one."""

    interest: str
    author: str
    reason: str


@dataclass(frozen=True)
class Assessment:
    """What the build computed for an idea before any run. A check that
    could not be made because an earlier one failed is ``None``."""

    feasible: bool
    problems: tuple[str, ...]
    falsifiable: bool | None
    runs: int | None
    budget: int | None
    contribution: str | None
    source: str = ""

    @property
    def within_budget(self) -> bool | None:
        if self.runs is None or self.budget is None:
            return None
        return self.runs <= self.budget

    @property
    def passed(self) -> bool:
        """Whether every check passed."""
        return bool(self.feasible and self.falsifiable and self.within_budget)


def falsifiable(specification: Specification) -> bool:
    """Whether a result of the route can contradict the prediction: the
    predicted bound lies inside the varied range by at least the resolution
    from each end. A bound at or beyond an end is met by every bracket the
    route can report, whatever the ball does."""
    varied = specification.varied
    bound = specification.prediction.value
    margin = specification.resolution
    return varied.low + margin <= bound <= varied.high - margin


def runs_needed(specification: Specification) -> int:
    """The number of runs the scripted route makes for ``specification``
    when the best setting lies inside the range: the scan, two runs for each
    halving of the bracket until it is no wider than the resolution, and
    three runs at the halved numerical variable when the answer must be
    stable. Counted from the procedure of ``execute``; nothing is run."""
    varied = specification.varied
    step = (varied.high - varied.low) / (SCAN_POINTS - 1)
    runs = SCAN_POINTS
    while 2.0 * step > specification.resolution:
        step /= 2.0
        runs += 2
    if specification.stable:
        runs += 3
    return runs


def contribution(
    specification: Specification, answered: tuple[Answered, ...]
) -> tuple[str, str]:
    """What the answered questions already hold for the specification's
    action and fixed settings, and the source: a question answered by a
    formula, a replication of an answered question, or an extension of
    one."""
    settings = {v.name: v.value for v in specification.variables if v.role == "fixed"}
    for known in answered:
        if specification.measure == known.action and known.by_formula:
            return BY_FORMULA, known.source
    for known in answered:
        if specification.measure == known.action and dict(known.settings) == settings:
            return REPLICATION, known.source
    sources = [k.source for k in answered if k.action == specification.measure]
    return EXTENSION, ", ".join(sources)


def assess(
    idea: Idea, laboratory: Laboratory, answered: tuple[Answered, ...]
) -> Assessment:
    """The checks of ``idea`` against ``laboratory`` and the archive of
    ``answered`` questions, in order; nothing is executed."""
    if idea.draft is None:
        return Assessment(
            feasible=False,
            problems=("the question cannot be written with the laboratory's actions",),
            falsifiable=None,
            runs=None,
            budget=None,
            contribution=None,
        )
    try:
        specification = parse(copy.deepcopy(dict(idea.draft)), laboratory)
    except SpecificationRejected as rejected:
        return Assessment(
            feasible=False,
            problems=tuple(f"{p.part}: {p.message}" for p in rejected.problems),
            falsifiable=None,
            runs=None,
            budget=None,
            contribution=None,
        )
    kind, source = contribution(specification, answered)
    return Assessment(
        feasible=True,
        problems=(),
        falsifiable=falsifiable(specification),
        runs=runs_needed(specification),
        budget=specification.max_runs,
        contribution=kind,
        source=source,
    )


def select(
    assessments: Mapping[str, Assessment], judgements: Mapping[str, Judgement]
) -> str | None:
    """The key of the idea the declared rule selects, or ``None`` when no
    idea passes every check: of the ideas that pass, the best contribution,
    then the fewest runs, then the higher interest a person judged, then
    the key. No self-rating is an argument."""
    passing = [key for key, a in assessments.items() if a.passed]
    if not passing:
        return None

    def rank(key: str) -> tuple:
        assessment = assessments[key]
        judged = judgements.get(key)
        interest = INTEREST.index(judged.interest) if judged else -1
        return (
            CONTRIBUTIONS.index(assessment.contribution),
            assessment.runs,
            -interest,
            key,
        )

    return min(passing, key=rank)


def idea_digest(idea: Idea) -> str:
    """The digest of everything an idea says, self-ratings included."""
    return digest_value(
        {
            "key": idea.key,
            "question": idea.question,
            "proposer": idea.proposer,
            "draft": idea.draft,
            "self_ratings": dict(idea.self_ratings),
        }
    )


@dataclass(frozen=True)
class Entry:
    """One entry of the archive: the idea and its digest, the decision, the
    reason, what would warrant revisiting it, the digest of the entry before
    it, and its own digest."""

    number: int
    idea: Idea
    idea_digest: str
    decision: str
    reason: str
    revisit: str
    previous: str
    digest: str


def _entry_digest(
    number: int, idea_sha: str, decision: str, reason: str, revisit: str, previous: str
) -> str:
    return digest_value([number, idea_sha, decision, reason, revisit, previous])


class Archive:
    """Every idea and every decision about it, in order. Entries are only
    added; a new decision about an idea is a new entry."""

    def __init__(self) -> None:
        self.entries: list[Entry] = []

    def add(self, idea: Idea, decision: str, reason: str, revisit: str) -> Entry:
        """Add the decision about ``idea`` with its reason and the condition
        for revisiting it, chained to the entry before."""
        if decision not in (SELECTED, DEFERRED, REJECTED):
            raise ValueError(f"unknown decision {decision!r}")
        if not reason.strip():
            raise ValueError("a decision needs its reason")
        number = len(self.entries) + 1
        previous = self.entries[-1].digest if self.entries else ""
        idea_sha = idea_digest(idea)
        digest = _entry_digest(number, idea_sha, decision, reason, revisit, previous)
        entry = Entry(
            number, idea, idea_sha, decision, reason, revisit, previous, digest
        )
        self.entries.append(entry)
        return entry


def verify_archive(entries: list[Entry]) -> list[str]:
    """The problems of an archive's entries: an entry out of order, an idea
    changed after its entry was written, a broken chain, or an entry whose
    own digest does not match. An empty list when none is found.

    The entries are the only record it reads, so a change that leaves every
    link intact is not found: the last entry removed, or an entry edited and
    every digest from it on recomputed."""
    found = []
    previous = ""
    for position, entry in enumerate(entries, start=1):
        if entry.number != position:
            found.append(f"entry {entry.number} stands at position {position}")
        if idea_digest(entry.idea) != entry.idea_digest:
            found.append(
                f"entry {entry.number}: the idea changed after it was archived"
            )
        if entry.previous != previous:
            found.append(
                f"entry {entry.number}: the chain to the entry before is broken"
            )
        recomputed = _entry_digest(
            entry.number,
            entry.idea_digest,
            entry.decision,
            entry.reason,
            entry.revisit,
            entry.previous,
        )
        if recomputed != entry.digest:
            found.append(f"entry {entry.number}: its digest does not match its content")
        previous = entry.digest
    return found
