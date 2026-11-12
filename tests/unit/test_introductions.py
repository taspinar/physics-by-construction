"""The introductions of courses and method paths (F156): the data file and
its rules, the references, the generated page, the links from the atlas panel
and the lesson header, and the one-to-one rule of page sources and data
files."""

import copy
import html
import importlib.util
import json
import re
import shutil

import pytest
import yaml
from support.paths import SITE_SOURCE

from pbc.authoring.atlas import Atlas, AtlasSection
from pbc.authoring.glossary import Glossary
from pbc.authoring.introductions import (
    SECTIONS,
    Introduction,
    IntroductionContent,
    introduction_problems,
    page_source_problems,
    sequence_ids,
)
from pbc.authoring.path import LearningPath, LessonHeader
from pbc.authoring.website import introduced, introduction_page

ATLAS = Atlas.read(SITE_SOURCE)
CURRICULUM = ATLAS.path.curriculum
GLOSSARY = Glossary.read(SITE_SOURCE)
TERMS = tuple(entry.term for entry in GLOSSARY.entries)
PILOT = ("mechanics", "law-discovery")
AVAILABLE = frozenset(PILOT)


def _data(sequence_id: str = "mechanics") -> dict:
    file = SITE_SOURCE / "introductions" / f"{sequence_id}.yaml"
    return yaml.safe_load(file.read_text(encoding="utf-8"))


def _problems(data: object, sequence_id: str = "mechanics") -> list[str]:
    return introduction_problems(data, sequence_id, CURRICULUM, TERMS)


def _content(sequence_id: str, available=AVAILABLE) -> IntroductionContent:
    introduction = Introduction.parse(
        _data(sequence_id), sequence_id, CURRICULUM, TERMS
    )
    return IntroductionContent(ATLAS, GLOSSARY, introduction, frozenset(available))


# --- The data file and its rules ---------------------------------------------


@pytest.mark.parametrize("sequence_id", PILOT)
def test_the_two_pilot_files_hold_every_section_of_the_decision_and_no_problem(
    sequence_id,
):
    data = _data(sequence_id)

    assert _problems(data, sequence_id) == []
    assert set(data) == {"sequence", *(key for key, _, _ in SECTIONS)}
    assert [key for key, _, _ in SECTIONS] == [
        "why",
        "questions",
        "learn",
        "order",
        "method",
        "capstone",
        "next",
    ]


def test_a_slot_that_is_not_in_the_curriculum_file_is_an_error():
    data = _data()
    data["why"] = ["See {slot:M99} for the start."]

    assert any("M99" in message for message in _problems(data))


def test_a_sequence_that_is_neither_a_course_nor_a_path_is_an_error():
    data = _data()
    data["next"] = ["Go on with {sequence:alchemy}."]

    assert any("alchemy" in message for message in _problems(data))


def test_a_term_that_is_not_in_the_glossary_is_an_error():
    data = _data()
    data["learn"] = ["You need {term:Astrology}."]

    assert any("Astrology" in message for message in _problems(data))


def test_a_reference_of_an_unknown_kind_is_an_error():
    data = _data()
    data["why"] = ["Read {lesson:kinematics} first."]

    assert any("lesson" in message for message in _problems(data))


@pytest.mark.parametrize(
    "text",
    [
        "See {slot:M1 for the start.",
        "See {slot:} for the start.",
        "See {slot:M1}} for the start.",
        "See {term: for the start.",
        "See {} for the start.",
        "See slot:M1} for the start.",
        "See {Slot:M1} for the start.",
    ],
)
def test_a_malformed_or_empty_reference_is_an_error(text):
    data = _data()
    data["why"] = [text]

    assert _problems(data) != []


@pytest.mark.parametrize("field", ["lessons", "title", "count", "prerequisites"])
def test_a_field_outside_the_schema_is_an_error(field):
    data = _data()
    data[field] = ["kinematics"] if field == "lessons" else "x"

    assert any(field in message for message in _problems(data))


def test_a_missing_section_is_an_error():
    data = _data()
    del data["method"]

    assert any("lacks method" in message for message in _problems(data))


def test_a_file_that_names_another_sequence_is_an_error():
    data = _data()
    data["sequence"] = "law-discovery"

    assert any("own sequence" in message for message in _problems(data))


@pytest.mark.parametrize(
    "text",
    [
        "The course has 17 lessons.",
        "It holds seventeen published lessons.",
        "Three planned slots remain.",
        "It holds twenty-one lessons.",
        "There are ninety-four slots.",
        "A forty four lesson course.",
        "A twenty-one-lesson course.",
        "It has 1,200 slots.",
        "Fifteen core-lessons form the path.",
        "Twenty-one Published Lessons.",
        "It has zero lessons yet.",
        "Ninety-nine slots.",
        "It has 0 slots.",
    ],
)
def test_a_count_of_lessons_in_the_prose_is_an_error(text):
    data = _data()
    data["why"] = [text]

    assert any("count" in message for message in _problems(data))


@pytest.mark.parametrize(
    "text",
    [
        "# A heading",
        "- a list item",
        "1. a numbered item",
        "Two paragraphs.\n\nThe second.",
        "A [link](https://example.org) written by hand.",
        "<b>raw html</b>",
        "![an image](a.png)",
        "a | table",
    ],
)
def test_prose_is_inline_markdown_only(text):
    data = _data()
    data["why"] = [text]

    assert _problems(data), text


def test_a_lesson_list_cannot_be_written_as_the_value_of_a_section():
    data = _data()
    data["order"] = {"M1": "Kinematics"}

    assert any("order" in message for message in _problems(data))


def test_a_lesson_list_written_as_prose_is_an_error():
    first, second = CURRICULUM.slots[0], CURRICULUM.slots[1]
    for text in (
        f"The path runs {first.label}, {second.label}.",
        f"First {first.title}, then {second.title}.",
    ):
        data = _data()
        data["order"] = [text]

        assert any("outside a reference" in m for m in _problems(data)), text


def test_a_lesson_named_by_reference_is_not_a_hand_written_list():
    data = _data()
    data["order"] = [
        f"First {{slot:{CURRICULUM.slots[0].label}}}, then"
        f" {{slot:{CURRICULUM.slots[1].label}}}."
    ]

    assert not any("outside a reference" in m for m in _problems(data))


def test_parse_raises_with_every_problem_listed():
    data = _data()
    data["lessons"] = []
    data["why"] = ["{slot:M99}"]

    with pytest.raises(ValueError) as caught:
        Introduction.parse(data, "mechanics", CURRICULUM, TERMS)

    message = str(caught.value)
    assert "lessons" in message and "M99" in message


def test_a_sequence_identifier_used_twice_is_an_error():
    clash = CURRICULUM.__class__(
        paths=(CURRICULUM.paths[0].__class__("mechanics", "A path"),),
        slots=CURRICULUM.slots,
    )

    with pytest.raises(ValueError, match="mechanics"):
        sequence_ids(clash)


def test_the_real_curriculum_has_unique_sequence_identifiers():
    assert len(set(sequence_ids(CURRICULUM))) == 12


# --- Page sources and data files are one to one ------------------------------


def test_the_real_page_sources_and_data_files_are_one_to_one():
    assert page_source_problems(SITE_SOURCE) == []
    assert introduced(SITE_SOURCE) == AVAILABLE
    for sequence_id in AVAILABLE:
        assert (SITE_SOURCE / introduction_page(sequence_id)).is_file()


def _site(tmp_path):
    site = tmp_path / "site"
    (site / "introductions").mkdir(parents=True)
    shutil.copy(SITE_SOURCE / "curriculum.yaml", site / "curriculum.yaml")
    return site


def test_the_title_of_a_page_source_is_the_title_of_its_sequence(tmp_path):
    site = _site(tmp_path)
    (site / "introductions" / "waves.yaml").write_text("sequence: waves\n")
    page = site / "courses" / "waves" / "index.qmd"
    page.parent.mkdir(parents=True)
    page.write_text('---\ntitle: "Wave things"\n---\n')

    found = page_source_problems(site)

    assert len(found) == 1 and "'Wave things'" in found[0]
    page.write_text('---\ntitle: "Waves and optics"\n---\n')
    assert page_source_problems(site) == []


def test_a_data_file_without_a_page_source_is_reported(tmp_path):
    site = _site(tmp_path)
    (site / "introductions" / "mechanics.yaml").write_text("sequence: mechanics\n")

    found = page_source_problems(site)

    assert len(found) == 1 and "no page source" in found[0]


def test_a_page_source_without_a_data_file_is_reported(tmp_path):
    site = _site(tmp_path)
    (site / "courses" / "waves").mkdir(parents=True)
    (site / "courses" / "waves" / "index.qmd").write_text("x\n")

    found = page_source_problems(site)

    assert len(found) == 1 and "no data file" in found[0]


def test_a_data_file_of_an_unknown_sequence_is_reported(tmp_path):
    site = _site(tmp_path)
    (site / "introductions" / "alchemy.yaml").write_text("sequence: alchemy\n")
    (site / "courses" / "alchemy").mkdir(parents=True)
    (site / "courses" / "alchemy" / "index.qmd").write_text("x\n")

    found = page_source_problems(site)

    assert len(found) == 1 and "neither a course nor a method path" in found[0]


# --- The generated page --------------------------------------------------------


@pytest.mark.parametrize("sequence_id", PILOT)
def test_the_page_has_every_section_in_order_with_its_title_first(sequence_id):
    page = _content(sequence_id).markdown()
    sequence = next(s for s in ATLAS.sequences() if s.id == sequence_id)

    assert not page.lstrip().startswith("# ")
    headings = re.findall(r"^## .*\{#([a-z]+)\}$", page, re.MULTILINE)
    assert headings == [
        "why",
        "questions",
        "learn",
        "order",
        "method",
        "capstone",
        "next",
        "prerequisites",
        "lessons",
    ]
    assert "alt=" in page and sequence.illustration in page


@pytest.mark.parametrize("sequence_id", PILOT)
def test_the_page_needs_no_script_and_holds_no_state(sequence_id):
    page = _content(sequence_id).markdown()

    for forbidden in ("<script", "data-enhancement", "localStorage", "data-lesson-id"):
        assert forbidden not in page


@pytest.mark.parametrize("sequence_id", PILOT)
def test_the_page_is_byte_stable(sequence_id):
    assert _content(sequence_id).markdown() == _content(sequence_id).markdown()


@pytest.mark.parametrize("sequence_id", PILOT)
def test_the_lesson_list_and_counts_are_those_of_the_atlas(sequence_id):
    content = _content(sequence_id)
    sequence = content.sequence
    page = content.markdown()

    assert f"{sequence.published} of {len(sequence.core)} lessons are published" in page
    for row in sequence.rows:
        if row.lesson is not None:
            assert f">{html.escape(row.title)}</a>" in page
    shown = re.findall(r'<li class="intro-row" data-state="(\w+)"', page)
    assert shown.count("published") == sequence.published + sequence.extension_published
    assert shown.count("planned") == sequence.planned + sequence.extension_planned


def test_a_planned_lesson_is_shown_with_label_and_title_but_not_linked_or_counted():
    content = _content("law-discovery")
    page = content.markdown()
    planned = [
        item
        for item in re.findall(
            r'<li class="intro-row" data-state="planned">.*?</li>', page
        )
    ]

    assert len(planned) == content.sequence.planned == 1
    assert "MD10" in planned[0] and "<a " not in planned[0]
    assert "Capstone: System Discovery Lab" in planned[0]
    # In the prose too: the planned capstone is text, never a link.
    assert "Capstone: System Discovery Lab (planned)" in page
    assert not re.search(r"\[Capstone: System Discovery Lab\]\(", page)


def test_a_slot_that_becomes_published_is_linked_and_counted():
    path = ATLAS.path
    lessons = path.lessons
    slot = CURRICULUM.slot("M15")
    clone = copy.copy(lessons[0])
    published = type(clone)(
        **{
            **clone.__dict__,
            "id": "pendulum-data",
            "slot": slot.label,
            "page": "lessons/mechanics/99-pendulum-data/index.qmd",
            "title": "A real pendulum",
            "course": "mechanics",
        }
    )
    altered = Atlas(LearningPath((*lessons, published), CURRICULUM), ATLAS.manifest)
    introduction = Introduction.parse(_data(), "mechanics", CURRICULUM, TERMS)
    content = IntroductionContent(altered, GLOSSARY, introduction, AVAILABLE)

    page = content.markdown()

    assert "18 of 18 lessons are published" in page
    assert 'data-state="planned"' not in page
    assert "99-pendulum-data/index.html" in page


def test_a_reference_to_a_planned_slot_in_prose_is_text():
    content = _content("mechanics")

    assert content.inline("{slot:FL10}") == (
        "Applied capstone: reconstructing the 2025 Kamchatka tsunami (planned)"
    )
    assert content.inline("{slot:M1}").startswith("[Kinematics as a program](")


def test_a_sequence_reference_links_to_its_introduction_when_it_has_one():
    content = _content("mechanics")

    assert content.inline("{sequence:law-discovery}").endswith(
        "(../law-discovery/index.html)"
    )
    assert content.inline("{sequence:waves}").endswith(
        "(../../path/index.html#course-waves)"
    )


def test_the_prerequisites_come_from_the_front_matter_of_the_lessons():
    content = _content("law-discovery")
    own = {lesson.id for lesson in content.lessons()}
    outside = {lesson.id for lesson in content.prerequisite_lessons()}

    assert outside and not outside & own
    assert "harmonic-oscillator" in outside
    for lesson in content.lessons():
        for item in lesson.prerequisites:
            assert item in own or item in outside
    assert "[Statistics](../../glossary.html#statistics)" in content.prerequisites()


# --- The links ------------------------------------------------------------------


def test_the_atlas_panel_of_a_sequence_with_an_introduction_links_to_it():
    html = str(AtlasSection(ATLAS, "path/index.qmd", AVAILABLE))

    for sequence_id in PILOT:
        assert f'href="../{introduction_page(sequence_id)[:-4]}.html"' in html
    assert html.count('class="atlas-introduction"') == len(PILOT)


def test_no_sequence_without_an_introduction_shows_a_link():
    html = str(AtlasSection(ATLAS, "path/index.qmd", frozenset({"mechanics"})))
    previous = str(AtlasSection(ATLAS))

    assert html.count('class="atlas-introduction"') == 1
    assert "courses/law-discovery" not in html
    assert "atlas-introduction" not in previous and "courses/" not in previous


def test_the_atlas_link_comes_before_the_lessons_after_the_description():
    """Issue #483: the open row offers the introduction before its lessons,
    never at the bottom; the tab order follows."""
    html = str(AtlasSection(ATLAS, "path/index.qmd", AVAILABLE))
    panel = html[html.index('id="course-mechanics"') : html.index('id="course-thermo')]

    assert (
        panel.index('class="atlas-description"')
        < panel.index("atlas-introduction")
        < panel.index('class="atlas-rows"')
    )
    assert "Read the course introduction</a></p></div><ol" in panel


def test_the_atlas_without_introductions_is_what_it_was():
    with_links = str(AtlasSection(ATLAS, "path/index.qmd", AVAILABLE))
    stripped = re.sub(r'<p class="atlas-introduction">.*?</p>', "", with_links)

    assert stripped == str(AtlasSection(ATLAS))


def test_the_header_of_a_mechanics_lesson_links_to_the_introduction():
    path = ATLAS.path
    header = LessonHeader(
        path, path.lesson("kinematics"), None, (), AVAILABLE
    ).markdown()

    assert (
        "Introduction\n:   [Classical mechanics]"
        "(../../../courses/mechanics/index.html)\n" in header
    )
    # The course link of the header is what it was.
    assert "[Classical mechanics](../../../path/index.html#course-mechanics)," in header


def test_the_header_of_a_law_discovery_lesson_links_to_both_introductions():
    path = ATLAS.path
    lesson = path.lesson("symbolic-regression")
    header = LessonHeader(path, lesson, None, (), AVAILABLE).markdown()

    assert (
        "Introduction\n:   [Classical mechanics]"
        "(../../../courses/mechanics/index.html),"
        " [Physical model discovery through active experiments]"
        "(../../../courses/law-discovery/index.html)\n" in header
    )


def test_the_introduction_row_follows_the_course_and_slot_rows():
    path = ATLAS.path
    header = LessonHeader(
        path, path.lesson("symbolic-regression"), None, (), AVAILABLE
    ).markdown()
    terms = re.findall(r"^([A-Z][^\n:]*)\n:   ", header, re.MULTILINE)

    assert terms[:4] == ["Course", "Slot", "Introduction", "Methods"]


def test_a_lesson_of_a_sequence_without_an_introduction_has_no_link():
    path = ATLAS.path
    header = LessonHeader(
        path, path.lesson("particles-in-a-box"), None, (), AVAILABLE
    ).markdown()

    assert "Introduction" not in header


def test_the_header_without_introductions_is_what_it_was():
    path = ATLAS.path
    for lesson_id in ("kinematics", "symbolic-regression"):
        lesson = path.lesson(lesson_id)
        plain = LessonHeader(path, lesson).markdown()
        linked = LessonHeader(path, lesson, None, (), AVAILABLE).markdown()
        stripped = re.sub(r"Introduction\n:   [^\n]*\n\n", "", linked)

        assert stripped == plain


def test_every_lesson_address_is_unchanged_by_the_introductions():
    # The introductions add pages under courses/ and links; no lesson page
    # moves: the lessons are still where the curriculum and the path say.
    for lesson in ATLAS.path.lessons:
        assert lesson.page.startswith("lessons/")
        assert (SITE_SOURCE / lesson.page).is_file()
    assert not any(lesson.page.startswith("courses/") for lesson in ATLAS.path.lessons)


# --- The search index --------------------------------------------------------


def _search_index_module():
    spec = importlib.util.spec_from_file_location(
        "search_index", SITE_SOURCE / "search-index.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_introduction_pages_are_not_left_out_of_the_search_index():
    module = _search_index_module()

    for sequence_id in PILOT:
        assert f"courses/{sequence_id}/index.html" not in module.NOT_INDEXED


def test_the_post_render_step_keeps_the_entries_of_an_introduction(
    tmp_path, monkeypatch
):
    module = _search_index_module()
    page = tmp_path / "courses" / "mechanics" / "index.html"
    page.parent.mkdir(parents=True)
    page.write_text("<p>Why it matters</p>", encoding="utf-8")
    entries = [
        {
            "objectID": "a",
            "href": "courses/mechanics/index.html",
            "text": "Why it matters",
        },
        {"objectID": "b", "href": "path/index.html", "text": "navigation"},
    ]
    (tmp_path / "search.json").write_text(json.dumps(entries), encoding="utf-8")
    monkeypatch.setenv("QUARTO_PROJECT_OUTPUT_DIR", str(tmp_path))

    module.main()

    kept = json.loads((tmp_path / "search.json").read_text(encoding="utf-8"))
    assert [entry["href"] for entry in kept] == ["courses/mechanics/index.html"]


def test_the_build_check_fails_on_a_mismatch(tmp_path, capsys):
    from pbc.authoring.introductions import main

    assert main(["--site", str(SITE_SOURCE)]) == 0
    site = tmp_path / "site"
    shutil.copytree(SITE_SOURCE, site, ignore=shutil.ignore_patterns("_*"))
    (site / "courses/mechanics/index.qmd").unlink()
    assert main(["--site", str(site)]) == 1
    assert "has no page source" in capsys.readouterr().err
