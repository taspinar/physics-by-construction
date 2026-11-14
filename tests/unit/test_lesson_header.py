"""The compact lesson header and the previous and next lesson at the end of a
lesson (F174): what a reader sees first, what the closed disclosure holds,
and that no fact of the header is lost."""

import re

import pytest
from support.paths import SITE_SOURCE

from pbc.authoring.context import InvalidContext, marker, regenerate_page
from pbc.authoring.glossary import Glossary
from pbc.authoring.path import (
    HEADER_DETAILS_CLASS,
    PAGER_CLASS,
    PAGER_LABEL,
    LearningPath,
    LessonHeader,
    lesson_pager,
)
from pbc.authoring.repository import BuildCommit

PATH = LearningPath.read(SITE_SOURCE)
GLOSSARY = Glossary.read(SITE_SOURCE)
_TERM = re.compile(r"^([A-Z][^\n:]*)\n:   ", re.MULTILINE)
SHOWN = ["Course", "Methods", "Difficulty", "What you'll learn", "Previous", "Next"]
# Every term the header had before F174, in its order.
ALL = [
    "Course",
    "Slot",
    "Introduction",
    "Methods",
    "Difficulty",
    "What you'll learn",
    "Prerequisites",
    "Before you begin",
    "Related",
    "Connections",
    "Previous",
    "Next",
]


def _parts(text: str) -> tuple[str, str]:
    shown, _, more = text.partition(f'<details class="{HEADER_DETAILS_CLASS}">')
    return shown, more


def test_every_header_shows_the_orientation_and_closes_the_rest():
    for lesson in PATH.lessons:
        text = LessonHeader(PATH, lesson, GLOSSARY).markdown()
        shown, more = _parts(text)

        assert more, lesson.id
        assert "<details open" not in text
        assert _TERM.findall(shown) == SHOWN, lesson.id
        inside = _TERM.findall(more)
        assert inside[:1] == (["Slot"] if lesson.slot else ["Prerequisites"])
        assert {"Prerequisites", "Before you begin", "Related"} <= set(inside)
        assert set(inside).isdisjoint(SHOWN)
        # Nothing is lost: every term the header had (this one has no
        # introductions and no connections), each once, in its old order.
        expected = {*SHOWN, "Prerequisites", "Before you begin", "Related"}
        if lesson.slot:
            expected.add("Slot")
        terms = _TERM.findall(shown) + inside
        assert sorted(terms) == sorted(expected), lesson.id
        assert inside == sorted(inside, key=ALL.index)
        for outcome in lesson.outcomes:
            assert f"    - {outcome}" in shown
        for related in lesson.related:
            assert PATH.lesson(related).title in more
        for prerequisite in lesson.prerequisites:
            assert PATH.lesson(prerequisite).title in more


def test_the_pager_repeats_the_previous_and_next_lesson_of_the_header():
    lessons = PATH.lessons
    for lesson in (lessons[0], lessons[len(lessons) // 2], lessons[-1]):
        header = LessonHeader(PATH, lesson).markdown()
        pager = lesson_pager(PATH, lesson)

        assert pager.startswith(
            f'<nav class="{PAGER_CLASS}" aria-label="{PAGER_LABEL}">'
        )
        assert pager.rstrip().endswith("</nav>")
        assert _TERM.findall(pager) == ["Previous", "Next"]
        rows = pager.split("\n\n", 1)[1].rsplit("\n\n", 1)[0]
        assert rows in header
    first = lesson_pager(PATH, lessons[0])
    assert "none; this is the first lesson of the" in first
    previous = PATH.previous(lessons[1])
    assert f"[{previous.title}](" in lesson_pager(PATH, lessons[1])


def test_the_page_ends_with_the_pager_after_everything_the_render_wrote():
    lesson = PATH.lesson("kinematics")
    payload = {
        "page": f"site/{lesson.page}",
        "code": ["src/pbc/mechanics/kinematics.py"],
        "tests": [],
        "experiment": "pbc.mechanics.experiments.kinematics",
        "kind": "run",
        "lean_modules": [],
        "live": "",
    }
    markers = "".join(
        _html_marker(marker(kind, lesson.page, payload if kind == "reproduce" else {}))
        for kind in ("header", "reproduce")
    )
    # A data lab has a paragraph after the last section's cell.
    text = f"<main>{markers}<p>The data card above.</p></main><script></script>"

    built = regenerate_page(
        text,
        lesson.page,
        SITE_SOURCE,
        BuildCommit("0" * 40, False),
        "https://github.com/example/physics-by-construction",
        convert=lambda chunks: chunks,
    )

    before, _, end = built.partition(f'<nav class="{PAGER_CLASS}"')
    assert end.count(f'<nav class="{PAGER_CLASS}"') == 0
    assert "suggest-improvement" in before and "The data card above." in before
    assert end.rstrip().endswith("</main><script></script>")
    assert "</nav>\n\n</main>" in end
    assert before.count("</main>") == 0


def test_a_lesson_page_without_main_cannot_take_the_pager():
    lesson = PATH.lesson("kinematics")
    payload = {
        "page": f"site/{lesson.page}",
        "code": [],
        "tests": [],
        "experiment": "pbc.mechanics.experiments.kinematics",
        "kind": "run",
        "lean_modules": [],
        "live": "",
    }
    text = "".join(
        _html_marker(marker(kind, lesson.page, payload if kind == "reproduce" else {}))
        for kind in ("header", "reproduce")
    )

    with pytest.raises(InvalidContext, match="previous and next lesson"):
        regenerate_page(
            text,
            lesson.page,
            SITE_SOURCE,
            BuildCommit("0" * 40, False),
            "https://github.com/example/physics-by-construction",
            convert=lambda chunks: chunks,
        )


def _html_marker(text: str) -> str:
    """The marker as pandoc writes it into the built page."""
    attributes = re.search(r"\{\.pbc-context ([^}]*)\}", text).group(1)
    data = re.sub(r"pbc-", "data-pbc-", attributes)
    return f'<div class="pbc-context" {data}>\n</div>'
