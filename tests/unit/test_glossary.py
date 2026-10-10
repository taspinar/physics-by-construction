"""The glossary: reading, resolving outside prerequisites, and rendering."""

from pathlib import Path

import pytest

from pbc.authoring.glossary import (
    Entry,
    Glossary,
    before_you_begin,
    problems,
    sentences,
    split_outside,
)


def entry(term: str, definition: str = "A definition.", see: str = "") -> Entry:
    return Entry(term, definition, see)


GLOSSARY = Glossary((entry("Calculus"), entry("Complex numbers")))


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Calculus: derivatives: and more", ("Calculus", "derivatives: and more")),
        ("Calculus", ("Calculus", "")),
    ],
)
def test_an_outside_prerequisite_splits_at_the_first_colon(text, expected):
    assert split_outside(text) == expected


def test_an_outside_prerequisite_resolves_by_its_term_only():
    assert GLOSSARY.entry("Calculus: the chain rule") == entry("Calculus")
    assert GLOSSARY.unresolved(["Calculus: x", "Topology: y", "calculus"]) == [
        "Topology: y",
        "calculus",
    ]


def test_sentences_are_counted_at_their_ends_not_at_decimal_points():
    assert sentences("It is 3.5 m. Then it is 4 m! Really?") == 3


def test_entry_problems_name_the_entry():
    found = problems([entry("A"), entry("a"), entry("B", "No end")])

    assert found[0] == "term 'a' appears twice"
    assert "entry 'B': the definition has 0 sentences" in found[1]


def test_the_block_links_each_term_to_its_entry_from_the_page_depth():
    shown = before_you_begin(
        "lessons/mechanics/02-x/index.qmd",
        GLOSSARY,
        ["Calculus: the chain rule", "Topology: open sets"],
    )

    assert shown == (
        "- [Calculus](../../../glossary.html#calculus): the chain rule\n"
        "- Topology: open sets"
    )


def test_the_glossary_is_read_sorted_with_unwrapped_definitions(tmp_path: Path):
    (tmp_path / "glossary.yaml").write_text(
        "entries:\n  - term: B\n    definition: >-\n      One\n      line.\n"
        "  - term: A\n    definition: Two.\n    see: x\n"
    )

    read = Glossary.read(tmp_path)

    assert [e.term for e in read.entries] == ["A", "B"]
    assert read.entries[1].definition == "One line."
    assert read.entries[0].see == "x"


def test_a_malformed_glossary_is_rejected(tmp_path: Path):
    (tmp_path / "glossary.yaml").write_text("entries:\n  - term: A\n")

    with pytest.raises(ValueError, match="does not follow its format"):
        Glossary.read(tmp_path)
