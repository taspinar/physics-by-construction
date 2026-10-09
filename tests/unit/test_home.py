"""The planned items of the home page match the roadmap, and the examples
the page links exist as lessons."""

import re

from support.paths import REPO_ROOT, SITE_SOURCE

from pbc.authoring import PLANNED, HomeContent, LearningPath
from pbc.authoring.home import CONSTRUCT_EXAMPLE, INVESTIGATE_EXAMPLE, VERIFY_EXAMPLE

ROADMAP = (REPO_ROOT / "docs" / "roadmap.md").read_text()


def roadmap_row(roadmap_id: str) -> str:
    match = re.search(rf"^\| {roadmap_id} \|.*$", ROADMAP, re.M)
    assert match, f"{roadmap_id} is not in the roadmap table"
    return match.group(0)


def test_every_planned_item_is_a_roadmap_feature_that_is_not_delivered():
    assert PLANNED
    for item in PLANNED:
        assert "delivered" not in roadmap_row(item.roadmap_id), item.roadmap_id


def test_every_planned_item_is_labelled_and_none_is_linked():
    text = HomeContent(LearningPath.read(SITE_SOURCE)).planned()
    for item in PLANNED:
        assert f"- Planned, {item.roadmap_id}: " in text
    assert "](" not in text and "http" not in text


def test_the_examples_are_published_lessons_of_the_three_activities():
    path = LearningPath.read(SITE_SOURCE)
    content = HomeContent(path)
    for lesson_id in (CONSTRUCT_EXAMPLE, INVESTIGATE_EXAMPLE, VERIFY_EXAMPLE):
        assert path.lesson(lesson_id).title in content.example(lesson_id)
    assert "simulation" in path.lesson(CONSTRUCT_EXAMPLE).methods
    assert "llm-agents" in path.lesson(INVESTIGATE_EXAMPLE).methods
    assert "lean" in path.lesson(VERIFY_EXAMPLE).methods
