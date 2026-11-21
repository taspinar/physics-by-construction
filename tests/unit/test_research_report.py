"""The check of a report's numbers and citations and the bundle of its
records (``pbc.research.report``, RR7, Issue #594; acceptance criterion 3)."""

from pathlib import Path

import pytest

from pbc.evidence.report import MARKED
from pbc.research.corpus import PASSAGES, STATEMENTS
from pbc.research.report import (
    CODE_CHANGED,
    CONFIGURATION_CHANGED,
    DIFFERS,
    PASSAGE,
    RECORD,
    REFUSED,
    REPRODUCED,
    Quantity,
    Recipe,
    Sentence,
    bundle,
    check_report,
    problems,
    reproduce,
    resolve_number,
)

RECORDS = {"plan": {"low": 43.75, "runs": 93, "verdict": "supported"}}


def check(*sentences: Sentence, records=RECORDS):
    return check_report(sentences, records, PASSAGES, STATEMENTS)


def test_a_number_resolves_at_the_decimals_it_is_written_with():
    low = Quantity("plan", "low")
    assert resolve_number("43.75", low, RECORDS) == (RECORD, "plan.low")
    assert resolve_number("43.8", low, RECORDS) == (RECORD, "plan.low")  # rounded
    assert resolve_number("44", low, RECORDS) == (RECORD, "plan.low")
    assert resolve_number("43.57", low, RECORDS) == (REFUSED, "the record gives 43.75")
    assert resolve_number("1", None, RECORDS) == (REFUSED, "a number with no record")
    assert resolve_number("1", Quantity("plan", "x"), RECORDS)[0] == REFUSED
    assert resolve_number("1", Quantity("other", "low"), RECORDS)[0] == REFUSED


def test_every_number_of_a_sentence_needs_its_record_in_order():
    sentence = Sentence(
        "s",
        "The bracket starts at 43.75 after 93 runs.",
        (Quantity("plan", "low"), Quantity("plan", "runs")),
    )
    assert [r.kind for r in check(sentence)] == [RECORD, RECORD]
    extra = Sentence("s", "After 93 runs and 7 ideas.", (Quantity("plan", "runs"),))
    assert [(r.token, r.kind) for r in check(extra)] == [
        ("93", RECORD),
        ("7", REFUSED),
    ]
    unused = Sentence("s", "No number here.", (Quantity("plan", "runs"),))
    assert [r.to for r in check(unused)] == ["plan.runs is named for no number"]


def test_a_citation_resolves_only_in_the_role_its_passage_plays():
    supports = Sentence(
        "s",
        "Supported [@sa1-bracket].",
        citations={"sa1-bracket": "supports"},
        claim="replication",
    )
    assert [(r.kind, r.to) for r in check(supports)] == [
        (PASSAGE, "sa1-bracket, supports")
    ]
    # The same passage, cited as support for another claim, is refused.
    wrong = Sentence(
        "s",
        "Supported [@m3-ratio].",
        citations={"m3-ratio": "supports"},
        claim="slow-throw",
    )
    [found] = check(wrong)
    assert found.kind == REFUSED and "insufficient" in found.to
    unknown = Sentence(
        "s", "See [@nowhere].", citations={"nowhere": "supports"}, claim="slow-throw"
    )
    assert check(unknown)[0].to == "the corpus holds no passage with this key"
    no_role = Sentence("s", "See [@m3-ratio].", claim="slow-throw")
    assert check(no_role)[0].to == "the citation names no role for a claim"


def test_the_digits_of_a_citation_key_are_not_numbers():
    sentence = Sentence(
        "s",
        "See [@sa5-moves-lower] and [@m3-flatter].",
        citations={"sa5-moves-lower": "contradicts", "m3-flatter": "contradicts"},
        claim="no-change",
    )
    assert [r.kind for r in check(sentence)] == [PASSAGE, PASSAGE]
    assert problems(check(sentence)) == []


def test_a_marked_sentence_is_listed_and_its_numbers_still_checked():
    marked = Sentence("s", "Probably lower still.", marked=True)
    assert [(r.kind, r.token) for r in check(marked)] == [(MARKED, "")]
    with_number = Sentence("s", "Probably below 43.", marked=True)
    assert [r.kind for r in check(with_number)] == [REFUSED]


def recipe(tmp_path: Path, value: dict, configuration="c") -> Recipe:
    (tmp_path / "code.py").write_text("x = 1\n")
    return Recipe(lambda: dict(value), configuration, (tmp_path / "code.py",))


def test_a_bundle_reproduces_and_finds_what_changed(tmp_path):
    recipes = {"r": recipe(tmp_path, {"a": 1})}
    entries = bundle(recipes)
    assert reproduce(entries, recipes) == {"r": REPRODUCED}
    edited = {tmp_path / "code.py": b"x = 2\n"}
    assert reproduce(entries, recipes, edited) == {"r": CODE_CHANGED}
    other = {"r": recipe(tmp_path, {"a": 1}, configuration="d")}
    assert reproduce(entries, other) == {"r": CONFIGURATION_CHANGED}
    drifted = {"r": recipe(tmp_path, {"a": 2})}
    assert reproduce(entries, drifted) == {"r": DIFFERS}


@pytest.mark.parametrize("text", ["the value 1.", "1, then", "(1)"])
def test_a_number_is_found_beside_punctuation(text):
    sentence = Sentence("s", text, (Quantity("plan", "x"),))
    assert [r.token for r in check(sentence)] == ["1"]
