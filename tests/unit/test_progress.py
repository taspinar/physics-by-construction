"""What the pages hand to the learner-state script, and the path export."""

import json
import re

from pbc.authoring import LearningPath
from pbc.authoring.path import PATH_PAGE, Lesson
from pbc.authoring.progress import (
    DATA_ID,
    EXPLANATION_ANCHOR,
    SCRIPT,
    export_json,
    path_export,
    progress_markup,
)


def make(id: str, order: int, prerequisites: tuple[str, ...] = ()) -> Lesson:
    return Lesson(
        page=f"lessons/mechanics/{order:02d}-{id}/index.qmd",
        id=id,
        title=id.capitalize(),
        description="",
        strand="mechanics",
        order=order,
        difficulty=1,
        prerequisites=prerequisites,
        outside=(),
        course="mechanics",
        methods=("simulation",),
        outcomes=("Do one thing", "Do another"),
        related=(),
    )


KINEMATICS = make("kinematics", 1)
LESSONS = [KINEMATICS, make("newton", 2, ("kinematics",))]


def data_of(markup: str) -> dict:
    match = re.search(rf'id="{DATA_ID}">(.*?)</script>', markup)
    assert match
    return json.loads(match.group(1))


def test_a_lesson_page_gets_its_stable_id_and_a_relative_script_url():
    markup = progress_markup(KINEMATICS.page, KINEMATICS)

    assert data_of(markup)["lesson"] == KINEMATICS.id
    assert f'src="../../../{SCRIPT}"' in markup
    assert "http" not in markup


def test_the_path_page_has_no_lesson_and_reaches_its_own_explanation():
    markup = progress_markup(PATH_PAGE, None)

    assert data_of(markup) == {
        "lesson": None,
        "explanation": f"index.html#{EXPLANATION_ANCHOR}",
    }
    assert f'src="../{SCRIPT}"' in markup


def test_a_lesson_page_links_to_the_explanation_on_the_path_page():
    explanation = data_of(progress_markup(KINEMATICS.page, KINEMATICS))["explanation"]

    assert explanation == f"../../../path/index.html#{EXPLANATION_ANCHOR}"


def test_the_export_lists_the_lessons_in_path_order_with_pages_from_the_site_root():
    path = LearningPath(tuple(LESSONS))
    exported = path_export(path)

    assert [entry["id"] for entry in exported["lessons"]] == [
        lesson.id for lesson in LESSONS
    ]
    first = exported["lessons"][0]
    assert first["page"] == KINEMATICS.page.replace("index.qmd", "index.html")
    assert set(first) == {
        "id",
        "title",
        "page",
        "strand",
        "order",
        "course",
        "methods",
        "difficulty",
        "prerequisites",
        "related",
    }


def test_the_export_text_is_the_same_every_time_and_ends_with_a_newline():
    path = LearningPath(tuple(LESSONS))

    assert export_json(path) == export_json(path)
    assert export_json(path).endswith("}\n")
    assert json.loads(export_json(path)) == path_export(path)
