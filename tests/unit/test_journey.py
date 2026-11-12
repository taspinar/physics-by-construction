"""The learning journey (F157, requirements decision 43): the one source of
the Part A and Part B text, its rules, and About, which carries the text
from the file; since Issue #483 the Course Atlas opens with the owner's own
paragraphs and shows no part of the journey."""

import re

import pytest
import yaml
from support.paths import SITE_SOURCE

from pbc.authoring.atlas import Atlas, AtlasSection
from pbc.authoring.glossary import Glossary
from pbc.authoring.journey import (
    EVIDENCE,
    JOURNEY_FILE,
    SECTIONS,
    SHARED,
    Journey,
    JourneyContent,
    journey_problems,
)
from pbc.authoring.website import introduced

ATLAS = Atlas.read(SITE_SOURCE)
CURRICULUM = ATLAS.path.curriculum
GLOSSARY = Glossary.read(SITE_SOURCE)
TERMS = tuple(entry.term for entry in GLOSSARY.entries)
AVAILABLE = introduced(SITE_SOURCE)
ABOUT = SITE_SOURCE / "about.qmd"


def _data() -> dict:
    return yaml.safe_load((SITE_SOURCE / JOURNEY_FILE).read_text(encoding="utf-8"))


def _problems(data: object) -> list[str]:
    return journey_problems(data, CURRICULUM, TERMS)


def _journey() -> Journey:
    return Journey.parse(_data(), CURRICULUM, TERMS)


def _content(page: str) -> JourneyContent:
    return JourneyContent(ATLAS, GLOSSARY, _journey(), AVAILABLE, page)


def _words(markdown: str) -> str:
    """The text as a reader sees it: link targets, attributes, and markup
    removed, white space collapsed."""
    text = re.sub(r"\]\([^)]*\)", "]", markdown)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\{[#.][^}]*\}", " ", text)
    return " ".join(text.replace("[", "").replace("]", "").split())


# --- The file and its rules ----------------------------------------------------


def test_the_committed_file_holds_every_part_and_breaks_no_rule():
    data = _data()

    assert _problems(data) == []
    assert set(data) == {key for key, _ in SECTIONS} | {"evidence"}
    assert set(data["evidence"]) == {key for key, _ in EVIDENCE}


def test_the_file_covers_the_five_points_of_the_decision():
    """How Part A leads to Part B, the background, that a route needs only
    its stated prerequisites, how a capstone fits, and the three kinds of
    evidence, each a part of the file."""
    keys = {key for key, _ in SECTIONS}

    assert {"part-a", "part-b", "relation"} <= keys
    assert {"background", "routes", "capstones"} <= keys
    assert [key for key, _ in EVIDENCE] == ["numerical", "empirical", "formal-proof"]
    assert set(SHARED) == {"part-a", "part-b", "relation"}


@pytest.mark.parametrize("data", [None, [], "text", 3])
def test_a_file_that_is_not_a_mapping_is_an_error(data):
    assert _problems(data)


@pytest.mark.parametrize("field", ["lessons", "count", "state", "title", "order"])
def test_a_field_outside_the_schema_is_an_error(field):
    data = _data()
    data[field] = ["Something."]

    assert any("outside the schema" in message for message in _problems(data))


@pytest.mark.parametrize("field", ["part-a", "relation", "routes", "evidence"])
def test_a_missing_field_is_an_error(field):
    data = _data()
    del data[field]

    assert any("lacks" in m and field in m for m in _problems(data))


@pytest.mark.parametrize("value", ["A text.", [], {"M1": "Kinematics"}, [3], [""]])
def test_a_section_is_a_non_empty_list_of_texts(value):
    data = _data()
    data["background"] = value

    assert any("background" in message for message in _problems(data))


@pytest.mark.parametrize(
    "change",
    [
        lambda e: e.pop("empirical"),
        lambda e: e.update(observational=["A text."]),
        lambda e: e.update(numerical=[]),
        lambda e: e.update(numerical="A text."),
    ],
)
def test_the_evidence_is_exactly_the_three_kinds_each_with_texts(change):
    data = _data()
    change(data["evidence"])

    assert any("evidence" in message for message in _problems(data))


def test_the_evidence_as_a_list_is_an_error():
    data = _data()
    data["evidence"] = ["Numerical evidence is ...", "Empirical evidence is ..."]

    assert any("evidence" in message for message in _problems(data))


@pytest.mark.parametrize(
    "text",
    [
        "# A heading",
        "- a list item",
        "Two paragraphs.\n\nThe second.",
        "A [link](https://example.org) written by hand.",
        "<b>raw html</b>",
        "![an image](a.png)",
        "a | table",
    ],
)
def test_prose_is_inline_markdown_only(text):
    data = _data()
    data["routes"] = [text]

    assert _problems(data), text


@pytest.mark.parametrize(
    "text",
    [
        "The site has 94 lessons.",
        "Thirty-two planned slots remain.",
        "It has eight courses.",
        "There are 4 method paths.",
        "Twelve sequences make the atlas.",
        "Four paths follow.",
        "Two capstones close it.",
    ],
)
def test_a_count_in_the_prose_is_an_error(text):
    data = _data()
    data["part-a"] = [text]

    assert any("count" in message for message in _problems(data)), text


def test_a_lesson_named_outside_a_reference_is_an_error():
    first, second = CURRICULUM.slots[0], CURRICULUM.slots[1]
    data = _data()
    data["capstones"] = [f"Begin with {first.label}, then {second.label}."]

    assert any("outside a reference" in m for m in _problems(data))


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("See {slot:M99}.", "M99"),
        ("See {sequence:optics}.", "optics"),
        ("See {term:Alchemy}.", "Alchemy"),
        ("See {page:verify}.", "not a reference"),
        ("See {slot:M1.", "brace"),
    ],
)
def test_a_reference_that_does_not_resolve_is_an_error(text, expected):
    data = _data()
    data["relation"] = [text]

    assert any(expected in message for message in _problems(data)), text


@pytest.mark.parametrize(
    "text",
    [
        "An agent discovers the law.",
        "The model made a discovery.",
        "What the agent discovered is checked.",
        "Discovering a law is the aim.",
    ],
)
def test_a_discovery_in_the_prose_is_an_error(text):
    data = _data()
    data["part-b"] = [text]

    assert any("discover" in message for message in _problems(data)), text


def test_the_law_discovery_path_named_by_reference_is_no_discovery():
    data = _data()
    data["part-b"] = ["The path {sequence:law-discovery} asks how a law is found."]

    assert not any("discover" in message for message in _problems(data))


def test_evidence_texts_follow_the_same_rules():
    data = _data()
    data["evidence"]["formal-proof"] = ["It has 12 lessons, see {slot:M99}."]

    found = _problems(data)
    assert any("count" in m for m in found) and any("M99" in m for m in found)


def test_parse_raises_with_every_problem_listed():
    data = _data()
    data["lessons"] = []
    data["routes"] = ["{slot:M99}"]

    with pytest.raises(ValueError) as caught:
        Journey.parse(data, CURRICULUM, TERMS)

    assert "lessons" in str(caught.value) and "M99" in str(caught.value)


def test_a_missing_file_is_an_error(tmp_path):
    with pytest.raises(ValueError):
        Journey.read(tmp_path, CURRICULUM, GLOSSARY)


def test_a_file_that_is_not_yaml_is_an_error(tmp_path):
    (tmp_path / JOURNEY_FILE).write_text("part-a: [unclosed\n", encoding="utf-8")

    with pytest.raises(ValueError, match="not valid YAML"):
        Journey.read(tmp_path, CURRICULUM, GLOSSARY)


def test_the_committed_file_is_read_from_the_site():
    assert Journey.read(SITE_SOURCE, CURRICULUM, GLOSSARY) == _journey()


# --- The Course Atlas (Issue #483) -------------------------------------------------


def test_the_atlas_holds_no_journey_and_about_does():
    """The atlas opens with the owner's two paragraphs (pbc.authoring.atlas);
    the journey's text is on About only, its shared sections, and the
    generator offers no atlas form of it."""
    atlas = _words(str(AtlasSection(ATLAS, "path/index.qmd", AVAILABLE)))
    about = _words(_content("about.qmd").about_markdown())

    for key, _ in SECTIONS:
        for text in _journey().sections[key]:
            shown = _words(_content("path/index.qmd").inline(text))
            assert shown not in atlas, key
            assert (shown in about) == (key in SHARED), key
    assert "journey" not in atlas.lower()
    assert not hasattr(JourneyContent, "atlas_markdown")


def test_a_reference_to_a_planned_slot_is_text_and_a_published_one_a_link():
    content = _content("about.qmd")
    planned = next(
        slot
        for slot in CURRICULUM.slots
        if not any(lesson.slot == slot.label for lesson in ATLAS.path.lessons)
    )
    published = next(lesson for lesson in ATLAS.path.lessons if lesson.slot)

    assert content.inline(f"{{slot:{planned.label}}}") == f"{planned.title} (planned)"
    assert content.inline(f"{{slot:{published.slot}}}").startswith(
        f"[{published.title}]("
    )


# --- About ----------------------------------------------------------------------------


def test_about_carries_the_part_a_and_part_b_text_of_the_source():
    about = _words(_content("about.qmd").about_markdown())

    for key in SHARED:
        for text in _journey().sections[key]:
            assert _words(_content("about.qmd").inline(text)) in about, key


def test_about_lists_the_courses_and_paths_from_the_curriculum():
    about = _content("about.qmd").about_markdown()

    for sequence in ATLAS.sequences():
        if sequence.part:
            assert f"- {sequence.title}" in about, sequence.title


def test_about_takes_the_journey_from_the_source_and_not_by_hand():
    source = ABOUT.read_text(encoding="utf-8")

    assert "about_journey()" in source
    for text in _journey().sections["part-a"]:
        assert text[:60] not in source


def test_about_keeps_every_anchor_it_had():
    source = ABOUT.read_text(encoding="utf-8")
    anchors = set(re.findall(r"\{#([a-z-]+)\}", source))

    assert {
        "creator-and-jidai",
        "why-it-exists",
        "why-open-source",
        "who-it-is-for",
        "what-this-site-is",
        "how-the-site-is-built",
    } <= anchors
    assert {"mission", "philosophy"} <= anchors


def test_about_keeps_the_attribution_cell():
    source = ABOUT.read_text(encoding="utf-8")
    start, end = source.index("{#creator-and-jidai}"), source.index("{#why-it-exists}")
    creator = source[start:end]

    assert "from pbc.authoring.identity import description" in creator
    assert "print(description())" in creator


def test_about_refers_to_how_we_verify_the_science_instead_of_repeating_it():
    source = ABOUT.read_text(encoding="utf-8")
    section = source[source.index("{#how-the-site-is-built}") :]
    section = section[: section.index("\n## ")]

    assert "[How we verify the science](verify.qmd)" in section
    for repeated in (
        "Code shown in a lesson is code the build ran",
        "Proofs are compiled by Lean",
        "a claim without evidence stops",
    ):
        assert repeated not in source


def test_about_states_the_mission_and_the_philosophy():
    source = ABOUT.read_text(encoding="utf-8")

    assert re.search(r"^#+ .*\{#mission\}$", source, re.MULTILINE)
    assert re.search(r"^#+ .*\{#philosophy\}$", source, re.MULTILINE)
