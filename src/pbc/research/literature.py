"""Claims against a local literature: labels, a retrieval baseline, the log
of proposals, and what an empty search may say.

``label`` compares a claim with the reading of a passage and returns
supports, contradicts, or insufficient, with the reason. The assumptions
come first: a passage about another quantity, under another drag, or about
another ball or speed says nothing about the claim, however close its
words. Then the bound: a passage supports a claim when its bound implies
the claim's and it holds for every case the claim covers; it contradicts
the claim when its bound excludes the claim's and it holds for a case the
claim covers (one counterexample is enough against a general claim, one
case is not enough for it); otherwise it is insufficient.

``retrieve`` is the baseline: TF-IDF weights over the words of the
passages, lower case, split at every character that is not a letter or a
digit, no stemming and no list of stop words, ranked by the cosine of the
angle between the claim's weights and each passage's. It is lexical: it
finds shared words, and it does not know that "45" and "forty-five" are one
number.

``review_log`` records every item the retrieval proposed for a claim with
two separate statuses: that of its quotation, which a test checks against
its page (a check of the text only), and that of its label, which is one
annotator's reading and was not checked independently, never a label the
program chose; and every source that was proposed and not read, as awaiting
human review. ``novelty`` says what a search found, and never that a claim
is new.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass

from pbc.research.corpus import (
    ANNOTATIONS,
    ANY,
    AWAITING_REVIEW,
    CONTRADICTS,
    INSUFFICIENT,
    PROPOSALS,
    SUPPORTS,
    Passage,
    Reading,
    Statement,
)

_WORD = re.compile(r"[a-z0-9]+")


def _overlaps(claimed: float | str, read: float | str | None) -> bool | None:
    """Whether a condition of the passage and one of the claim can be the
    same case: ``True`` or ``False``, or ``None`` when the passage concerns
    one value it does not state and the claim names a value."""
    if claimed == ANY or read == ANY:
        return True
    if read is None:
        return None
    return claimed == read


def _covers(claimed: float | str, read: float | str | None) -> bool:
    """Whether the passage holds for every case of the claim's condition."""
    return read == ANY or (read is not None and read == claimed)


def label(statement: Statement, reading: Reading) -> tuple[str, str]:
    """The label of ``statement`` against a passage of ``reading``, and the
    reason: the assumptions first, then the bound."""
    if reading.quantity != statement.quantity:
        return INSUFFICIENT, f"the passage is about the {reading.quantity}"
    if reading.drag != statement.drag:
        return INSUFFICIENT, f"the passage assumes drag: {reading.drag}"
    for name in ("ball", "speed"):
        overlap = _overlaps(getattr(statement, name), getattr(reading, name))
        if overlap is None:
            return INSUFFICIENT, f"the passage does not state the {name}"
        if not overlap:
            return INSUFFICIENT, f"the passage is about another {name}"
    if statement.relation == "below":
        implies = reading.below is not None and reading.below <= statement.value
        excludes = reading.above is not None and reading.above >= statement.value
    else:
        implies = reading.above is not None and reading.above >= statement.value
        excludes = reading.below is not None and reading.below <= statement.value
    if excludes:
        return CONTRADICTS, "its bound excludes the claim's in a case it covers"
    if implies:
        if _covers(statement.ball, reading.ball) and _covers(
            statement.speed, reading.speed
        ):
            return SUPPORTS, "its bound implies the claim's in every case it covers"
        return INSUFFICIENT, "one case does not establish a general claim"
    return INSUFFICIENT, "its bound does not decide the claim's"


def words(text: str) -> list[str]:
    """The words of ``text`` as the retrieval sees them."""
    return _WORD.findall(text.lower())


def retrieve(query: str, passages: tuple[Passage, ...]) -> list[tuple[str, float]]:
    """Every passage's key with its TF-IDF cosine score against ``query``,
    highest first (ties by key)."""
    documents = {p.key: Counter(words(p.text)) for p in passages}
    frequency = Counter(word for counts in documents.values() for word in counts)
    weight = {w: math.log(len(documents) / df) for w, df in frequency.items()}

    def vector(counts: Counter) -> dict[str, float]:
        return {w: n * weight.get(w, 0.0) for w, n in counts.items()}

    def norm(v: dict[str, float]) -> float:
        return math.sqrt(sum(x * x for x in v.values()))

    asked = vector(Counter(words(query)))
    scores = []
    for key, counts in documents.items():
        found = vector(counts)
        dot = sum(x * found.get(w, 0.0) for w, x in asked.items())
        size = norm(asked) * norm(found)
        scores.append((key, dot / size if size else 0.0))
    return sorted(scores, key=lambda item: (-item[1], item[0]))


def decisive(statement: Statement) -> set[str]:
    """The passages the annotator labelled supporting or contradicting."""
    return {
        key
        for key, given in ANNOTATIONS[statement.key].items()
        if given in (SUPPORTS, CONTRADICTS)
    }


def recall(
    statement: Statement, ranked: list[tuple[str, float]], k: int
) -> float | None:
    """The share of the claim's decisive passages among the first ``k``
    retrieved; ``None`` when the annotations hold no decisive passage, so
    that there is nothing to find."""
    wanted = decisive(statement)
    if not wanted:
        return None
    found = {key for key, _ in ranked[:k]}
    return len(wanted & found) / len(wanted)


# The status of a quotation the corpus holds: a test compares it with the
# current source of its page. It checks the text, not what anyone read in it.
QUOTATION_CHECKED = "quotation checked against its page"
# A source the corpus does not hold, so there is no quotation to check.
NOT_HELD = "not held"
# The status of a label from ``ANNOTATIONS``: one annotator's reading.
ONE_ANNOTATOR = "annotated by one annotator, not independently checked"


@dataclass(frozen=True)
class LogEntry:
    """One item of the review log: the claim, the proposed source, who
    proposed it, the status of its quotation, the status of its label, and
    the label the annotation gives it, if any."""

    claim: str
    source: str
    proposed_by: str
    quotation: str
    label_status: str
    label: str = ""


def review_log(
    statements: tuple[Statement, ...], passages: tuple[Passage, ...], k: int
) -> list[LogEntry]:
    """What the retrieval proposed for each claim (its first ``k`` passages)
    and the proposals nobody has read. A passage is logged with its checked
    quotation and, apart from it, the label of the annotations and where
    that label comes from; nothing is accepted or labelled by the
    program."""
    entries = []
    for statement in statements:
        for key, _ in retrieve(statement.text, passages)[:k]:
            given = ANNOTATIONS[statement.key].get(key)
            entries.append(
                LogEntry(
                    claim=statement.key,
                    source=key,
                    proposed_by="retrieval baseline",
                    quotation=QUOTATION_CHECKED,
                    label_status=ONE_ANNOTATOR if given else AWAITING_REVIEW,
                    label=given or "",
                )
            )
    for proposal in PROPOSALS:
        entries.append(
            LogEntry(
                claim="all",
                source=proposal.source,
                proposed_by=proposal.proposed_by,
                quotation=NOT_HELD,
                label_status=proposal.status,
            )
        )
    return entries


def novelty(statement: Statement, passages: tuple[Passage, ...]) -> str:
    """What the corpus says about whether the claim has been answered: the
    passages that decide it, or that none of the searched passages does.
    Never that the claim is new."""
    found = [
        p.key
        for p in passages
        if label(statement, p.reading)[0] in (SUPPORTS, CONTRADICTS)
    ]
    if found:
        return f"answered in the corpus: {', '.join(found)}"
    return f"not found in this corpus of {len(passages)} passages"
