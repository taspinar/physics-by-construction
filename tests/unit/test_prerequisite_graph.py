"""The prerequisite graph shows exactly the relations of the front matter,
lays them out without overlap, and renders the same bytes every time."""

import re
import xml.etree.ElementTree as ET

import pytest
from support.paths import SITE_SOURCE

from pbc.authoring import COURSES, LearningPath
from pbc.authoring.graph import (
    NODE_HEIGHT,
    NODE_WIDTH,
    RELATED,
    REQUIRES,
    Edge,
    PrerequisiteGraph,
)
from pbc.authoring.path import PATH_PAGE, Lesson, PathOverview


def lesson(
    id: str,
    order: int,
    prerequisites: tuple[str, ...] = (),
    related: tuple[str, ...] = (),
    title: str | None = None,
) -> Lesson:
    return Lesson(
        page=f"lessons/mechanics/{order:02d}-{id}/index.qmd",
        id=id,
        title=title or id.capitalize(),
        description="",
        strand="mechanics",
        order=order,
        difficulty=1,
        prerequisites=prerequisites,
        outside=(),
        course="mechanics",
        methods=("simulation",),
        outcomes=("One", "Two"),
        related=related,
    )


def href(item: Lesson) -> str:
    return "../" + item.page.replace("index.qmd", "index.html")


def draw(graph: PrerequisiteGraph) -> str:
    return graph.svg(href, "A graph.")


def relations(lessons) -> set[Edge]:
    """The relations of the front matter, read without the graph module."""
    found = set()
    for item in lessons:
        found |= {Edge(p, item.id, REQUIRES) for p in item.prerequisites}
        found |= {Edge(item.id, r, RELATED) for r in item.related}
    return found


def synthetic(count: int = 30) -> list[Lesson]:
    """A path of ``count`` lessons that branch and join: each lesson requires
    the one before and, now and then, one further back; some are related."""
    lessons = []
    for number in range(1, count + 1):
        prerequisites = (f"l{number - 1}",) if number > 1 else ()
        if number % 3 == 0 and number > 3:
            prerequisites += (f"l{number - 3}",)
        if number % 5 == 0:
            prerequisites = (f"l{number // 5}",)
        related = (f"l{number + 4}",) if number % 4 == 0 and number + 4 <= count else ()
        lessons.append(lesson(f"l{number}", number, prerequisites, related))
    return lessons


def test_the_edges_of_the_graph_are_the_relations_of_the_site():
    path = LearningPath.read(SITE_SOURCE)
    graph = PrerequisiteGraph.layout(path.lessons, path.courses)

    assert set(graph.edges) == relations(path.lessons)
    assert len(graph.edges) == len(set(graph.edges))
    assert {edge.kind for edge in graph.edges} == {REQUIRES, RELATED}
    assert [node.lesson for node in graph.nodes] == list(path.lessons)


def test_the_drawing_and_the_text_list_state_the_same_edges():
    lessons = synthetic()
    graph = PrerequisiteGraph.layout(lessons, COURSES)
    root = ET.fromstring(draw(graph))

    drawn = {
        Edge(p.get("data-from"), p.get("data-to"), p.get("data-kind"))
        for p in root.iter("{http://www.w3.org/2000/svg}path")
        if p.get("data-kind")
    }
    assert drawn == relations(lessons)
    assert len(graph.sentences()) == len(graph.edges)
    assert "L2 requires L1" in graph.sentences()
    assert any(
        "has the related lesson" in sentence and "not required" in sentence
        for sentence in graph.sentences()
    )


def test_every_node_links_to_its_lesson_and_the_svg_is_labelled_not_an_image():
    lessons = synthetic()
    graph = PrerequisiteGraph.layout(lessons, COURSES)
    text = draw(graph)
    root = ET.fromstring(text)
    svg = "{http://www.w3.org/2000/svg}"

    assert 'role="img"' not in text
    labels = root.get("aria-labelledby").split()
    ids = {
        element.get("id"): element.tag for element in root.iter() if element.get("id")
    }
    assert [ids[label] for label in labels] == [svg + "title", svg + "desc"]
    links = [(a.get("href"), a.get("data-lesson")) for a in root.iter(svg + "a")]
    assert links == [(href(item), item.id) for item in lessons]
    # Grouping is used for the course bands only.
    assert [g.get("role") for g in root.iter(svg + "g") if g.get("role")] == ["group"]


def test_a_column_is_one_step_right_of_the_furthest_prerequisite():
    lessons = synthetic()
    graph = PrerequisiteGraph.layout(lessons, COURSES)
    column = {node.lesson.id: node.layer for node in graph.nodes}

    for item in lessons:
        expected = 1 + max((column[p] for p in item.prerequisites), default=-1)
        assert column[item.id] == expected


def test_thirty_lessons_do_not_overlap_and_stay_inside_the_drawing():
    graph = PrerequisiteGraph.layout(synthetic(30), COURSES)

    boxes = [(n.x, n.y, n.x + NODE_WIDTH, n.y + NODE_HEIGHT) for n in graph.nodes]
    assert len(boxes) == 30
    for index, (left, top, right, bottom) in enumerate(boxes):
        assert left >= 0 and right <= graph.width
        assert top >= 0 and bottom <= graph.height
        for other in boxes[index + 1 :]:
            apart = right <= other[0] or other[2] <= left
            apart = apart or bottom <= other[1] or other[3] <= top
            assert apart
    # Bands hold their nodes.
    band = graph.bands[0]
    assert all(
        band.y <= node.y and node.y + NODE_HEIGHT <= band.y + band.height
        for node in graph.nodes
    )


def test_the_svg_is_byte_stable():
    lessons = synthetic()
    first = draw(PrerequisiteGraph.layout(lessons, COURSES))
    second = draw(PrerequisiteGraph.layout(list(lessons), tuple(COURSES)))

    assert first == second
    # No address, time, or counter ends up in the drawing.
    assert not re.search(r"\b0x[0-9a-f]+\b|\d{4}-\d\d-\d\d", first)


def test_the_overview_embeds_the_graph_once_with_its_legend_and_text_list():
    path = LearningPath.read(SITE_SOURCE)
    text = str(PathOverview(path, PATH_PAGE))

    assert text == str(PathOverview(path, PATH_PAGE))
    assert text.count("<svg xmlns") == 1
    assert "## Prerequisite graph {#graph}" in text
    assert "Requires</strong>" in text and "Related</strong>" in text
    assert text.count('<ol class="visually-hidden"') == 1


def test_a_long_title_is_cut_but_keeps_its_full_name_for_assistive_technology():
    title = "A very long title that goes on and on beyond what a box can hold"
    graph = PrerequisiteGraph.layout([lesson("a", 1, title=title)], COURSES)
    text = draw(graph)

    assert f'aria-label="{title}"' in text
    assert "…" in text


def test_lessons_without_edges_still_form_a_graph():
    graph = PrerequisiteGraph.layout([lesson("a", 1), lesson("b", 2)], COURSES)

    assert graph.edges == ()
    assert len({node.layer for node in graph.nodes}) == 1
    ET.fromstring(draw(graph))


@pytest.mark.parametrize("count", [1, 12, 30])
def test_the_layout_does_not_depend_on_the_input_object(count: int):
    lessons = synthetic(count)
    assert draw(PrerequisiteGraph.layout(lessons, COURSES)) == draw(
        PrerequisiteGraph.layout(tuple(lessons), COURSES)
    )
