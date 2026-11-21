"""The local literature of RR3 (``pbc.research.corpus``,
``pbc.research.literature``; acceptance criterion 2 of Issue #585): every
passage verified against its lesson, the labels computed from the readings
checked against the annotated labels, the retrieval baseline, and the log
of proposals for human review."""

import inspect
import re
from pathlib import Path

import pytest
import yaml

from pbc.authoring.evidence import read_claims
from pbc.research import corpus, literature
from pbc.research.corpus import (
    ANNOTATIONS,
    ANY,
    CONTRADICTS,
    INSUFFICIENT,
    LABELS,
    PASSAGES,
    STATEMENTS,
    SUPPORTS,
    Reading,
    Statement,
)

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"


def plain(text: str) -> str:
    return " ".join(text.split())


@pytest.mark.parametrize("passage", PASSAGES, ids=lambda p: p.key)
def test_every_passage_stands_on_its_page(passage):
    source = (SITE / passage.page).read_text(encoding="utf-8")
    assert f"id: {passage.lesson}\n" in source
    if passage.claim is None:
        assert plain(passage.text) in plain(source)
    else:
        claims = read_claims(passage.page, source)
        assert plain(claims[passage.claim - 1].statement) == plain(passage.text)


def test_every_passage_has_a_licence_the_dataset_policy_accepts():
    # The site's own text: CC BY 4.0, LICENSE-CONTENT (ADR 007 accepts CC BY).
    assert "Attribution 4.0 International" in (ROOT / "LICENSE-CONTENT").read_text()
    assert {p.licence for p in PASSAGES} == {"CC BY 4.0"}
    assert len({p.key for p in PASSAGES}) == len(PASSAGES)


def test_the_register_source_and_the_proposal_are_quoted_from_the_register():
    entries = {
        e["key"]: e
        for e in yaml.safe_load((SITE / "references.yaml").read_text())["references"]
    }
    for source in corpus.REGISTER:
        assert plain(source.statement) in plain(entries[source.key]["statement"])
    alternatives = plain(entries["drag-coefficient-regimes"]["alternatives"])
    for proposal in corpus.PROPOSALS:
        assert plain(proposal.source) in alternatives
        assert "was not opened" in alternatives


def test_every_pair_of_a_claim_and_a_passage_is_annotated():
    assert set(ANNOTATIONS) == {s.key for s in STATEMENTS}
    for given in ANNOTATIONS.values():
        assert set(given) == {p.key for p in PASSAGES}
        assert set(given.values()) <= set(LABELS)


@pytest.mark.parametrize("statement", STATEMENTS, ids=lambda s: s.key)
def test_the_computed_labels_are_the_annotated_labels(statement):
    for passage in PASSAGES:
        computed, reason = literature.label(statement, passage.reading)
        assert computed == ANNOTATIONS[statement.key][passage.key], (
            passage.key,
            reason,
        )


def test_all_three_labels_occur():
    given = {label for labels in ANNOTATIONS.values() for label in labels.values()}
    assert given == {SUPPORTS, CONTRADICTS, INSUFFICIENT}


# A reading of the best angle under quadratic drag, and under no drag.
def R(drag: str, ball: str, speed, **bounds) -> Reading:
    return Reading("best angle", drag, ball, speed, **bounds)


Q, NONE = "quadratic", "none"
CLAIM = Statement("c", "", "best angle", "quadratic", "tennis", 25.0, "below", 44.0)
GENERAL = Statement("g", "", "best angle", "quadratic", ANY, ANY, "above", 45.0)


@pytest.mark.parametrize(
    ("statement", "reading", "expected"),
    [
        # the assumptions first, however close the bound
        (CLAIM, R(NONE, ANY, ANY, below=40.0), INSUFFICIENT),
        (
            CLAIM,
            Reading("range", "quadratic", "tennis", 25.0, below=40.0),
            INSUFFICIENT,
        ),
        (CLAIM, R(Q, "baseball", 25.0, below=40.0), INSUFFICIENT),
        (CLAIM, R(Q, "tennis", 10.0, below=40.0), INSUFFICIENT),
        (CLAIM, R(Q, "tennis", None, below=40.0), INSUFFICIENT),
        # then the bound
        (CLAIM, R(Q, "tennis", 25.0, below=44.0), SUPPORTS),
        (CLAIM, R(Q, ANY, ANY, below=43.0), SUPPORTS),
        (CLAIM, R(Q, "tennis", 25.0, below=45.0), INSUFFICIENT),
        (CLAIM, R(Q, "tennis", 25.0, above=44.0), CONTRADICTS),
        (CLAIM, R(Q, "tennis", 25.0), INSUFFICIENT),
        # one case contradicts a general claim and does not establish one
        (GENERAL, R(Q, "tennis", 25.0, below=44.0), CONTRADICTS),
        (GENERAL, R(Q, "baseball", None, below=45.0), CONTRADICTS),
        (GENERAL, R(Q, "tennis", 25.0, above=45.0), INSUFFICIENT),
        (GENERAL, R(Q, ANY, ANY, above=45.0), SUPPORTS),
    ],
)
def test_the_label_rule(statement, reading, expected):
    assert literature.label(statement, reading)[0] == expected


def test_the_retrieval_is_lexical_and_deterministic():
    assert literature.words("$45^\\circ$, forty-five") == [
        "45",
        "circ",
        "forty",
        "five",
    ]
    ranked = literature.retrieve("forty-five degrees without air", PASSAGES)
    assert ranked == literature.retrieve("forty-five degrees without air", PASSAGES)
    assert len(ranked) == len(PASSAGES)
    assert [s for _, s in ranked] == sorted((s for _, s in ranked), reverse=True)
    assert ranked[0][0] == "sa5-without-air"
    assert literature.retrieve("zebra", PASSAGES)[0][1] == 0.0


def test_recall_counts_the_decisive_passages_found():
    replication, slow, no_change = STATEMENTS
    ranked = literature.retrieve(replication.text, PASSAGES)
    assert literature.recall(replication, ranked, 3) == 1.0
    assert literature.recall(slow, literature.retrieve(slow.text, PASSAGES), 3) is None
    ranked = literature.retrieve(no_change.text, PASSAGES)
    assert literature.recall(no_change, ranked, len(PASSAGES)) == 1.0
    assert literature.recall(no_change, ranked, 3) < 0.5


def test_the_log_holds_every_proposal_and_labels_only_what_was_annotated():
    log = literature.review_log(STATEMENTS, PASSAGES, 3)
    assert len(log) == 3 * len(STATEMENTS) + len(corpus.PROPOSALS)
    for entry in log[:-1]:
        assert entry.status == "verified passage"
        assert entry.label == ANNOTATIONS[entry.claim][entry.source]
    assert log[-1].status == "awaiting human review" and log[-1].label == ""


def test_an_empty_search_never_says_new():
    _, slow, _ = STATEMENTS
    said = literature.novelty(slow, PASSAGES)
    assert said == f"not found in this corpus of {len(PASSAGES)} passages"
    assert not re.search(r"\bnovel\b|\bnew\b", said)


def test_nothing_is_read_from_the_web():
    for module in (corpus, literature):
        text = inspect.getsource(module)
        assert not re.search(r"\b(urllib|requests|http\.client|socket|httpx)\b", text)
