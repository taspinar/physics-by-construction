"""The glossary in context: definitions on demand in "Before you begin" (F135)."""

import html
from pathlib import Path

from pbc.authoring.glossary import DEFINITIONS_LABEL, Entry, Glossary, definitions
from pbc.authoring.path import LearningPath, LessonHeader

SITE = Path(__file__).parents[2] / "site"
GLOSSARY = Glossary(
    (
        Entry("Calculus", "Rates of change.", ""),
        Entry("Vectors", "Arrows with a < b & c.", ""),
    )
)


def test_each_named_entry_gets_one_closed_disclosure_with_its_definition():
    shown = definitions(
        GLOSSARY, ["Vectors: the dot product", "Calculus", "Vectors: the cross product"]
    )

    assert shown.startswith('<div class="glossary-definitions">')
    assert DEFINITIONS_LABEL in shown
    # In the order of the list, once per entry, closed, without a script.
    assert shown.count("<details") == 2
    assert shown.index("<summary>Vectors</summary>") < shown.index(
        "<summary>Calculus</summary>"
    )
    assert "<details open" not in shown and "<script" not in shown
    assert "<p>Rates of change.</p>" in shown
    # The definition is text, escaped; the term above already links to it.
    assert "<p>Arrows with a &lt; b &amp; c.</p>" in shown
    assert "<a " not in shown


def test_a_prerequisite_without_an_entry_gets_no_disclosure():
    assert definitions(GLOSSARY, ["Topology: open sets"]) == ""
    assert definitions(GLOSSARY, []) == ""
    shown = definitions(GLOSSARY, ["Topology: open sets", "Calculus: limits"])
    assert shown.count("<details") == 1 and "Topology" not in shown


def test_the_header_shows_the_definitions_after_the_unchanged_list():
    path = LearningPath.read(SITE)
    glossary = Glossary.read(SITE)
    lesson = next(item for item in path.lessons if item.outside)

    shown = LessonHeader(path, lesson, glossary).markdown()
    begin = shown.split("Before you begin\n:   \n", 1)[1].split("\nRelated\n")[0]
    listing, _, disclosures = begin.partition("\n\n")

    assert listing.count("    - ") == len(lesson.outside)
    assert disclosures.strip() == definitions(glossary, lesson.outside)
    for text in lesson.outside:
        entry = glossary.entry(text)
        assert entry is not None
        assert f"<p>{html.escape(entry.definition)}</p>" in disclosures
