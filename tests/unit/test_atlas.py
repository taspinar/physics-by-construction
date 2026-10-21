"""The map manifest of the course atlas, what the build derives from it, and
the atlas section of the path page (ADR 018 decision 3, F125)."""

import itertools
import re
from dataclasses import replace
from html import unescape
from pathlib import Path

import pytest
import yaml
from support.paths import SITE_SOURCE

from pbc.authoring import COURSES, LearningPath
from pbc.authoring.atlas import (
    AREA_HEADER,
    ATLAS_FILE,
    CAPSTONE,
    CONNECTION_TYPES,
    ILLUSTRATIONS,
    PLANNED,
    Atlas,
    AtlasManifest,
    AtlasMap,
    AtlasSection,
    atlas_problems,
)
from pbc.authoring.path import Curriculum

FILE = SITE_SOURCE / ATLAS_FILE
PATH = LearningPath.read(SITE_SOURCE)
CURRICULUM = PATH.curriculum
ATLAS = Atlas.read(SITE_SOURCE)


def data() -> dict:
    return yaml.safe_load(FILE.read_text(encoding="utf-8"))


def broken(change) -> list[str]:
    content = data()
    change(content)
    return atlas_problems(content, CURRICULUM)


def concept(content: dict, concept_id: str) -> dict:
    return next(item for item in content["concepts"] if item["id"] == concept_id)


# --- The rules of the manifest --------------------------------------------------


def test_the_manifest_as_committed_breaks_no_rule():
    assert atlas_problems(data(), CURRICULUM) == []


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        (
            lambda d: d.update(courses=[]),
            "the file holds the lists 'concepts' and 'connections', and nothing else",
        ),
        (
            lambda d: d["concepts"][0].update(colour="blue"),
            "concept 'motion-as-a-program': 'colour' is not a field of a concept",
        ),
        (
            lambda d: d["connections"][0].update(weight=2),
            "'weight' is not a field of a connection",
        ),
        (
            lambda d: d["concepts"][0].update(area="chemistry"),
            "concept 'motion-as-a-program': 'area' 'chemistry' is not a course"
            " or a path of the curriculum file",
        ),
        (
            lambda d: d["concepts"][0].update(slots=["M1", "ZZ9"]),
            "concept 'motion-as-a-program': 'ZZ9' is not a slot of the curriculum",
        ),
        (
            lambda d: d["concepts"][0].update(slots=[]),
            "concept 'motion-as-a-program' must name at least one slot in 'slots'",
        ),
        (
            lambda d: d["concepts"][0].pop("slots"),
            "concept 'motion-as-a-program' must name at least one slot in 'slots'",
        ),
        (
            lambda d: d["connections"][0].update(
                concepts=["oscillation-and-resonance", "no-such-concept"]
            ),
            "'no-such-concept' is not a concept",
        ),
        (
            lambda d: d["concepts"][0].update(slots=["M1", "W1"]),
            "concept 'motion-as-a-program': slot W1 belongs to 'waves', not to"
            " the area 'mechanics'",
        ),
        (
            lambda d: d["concepts"][0].update(slots=["M1", "L1"]),
            "concept 'motion-as-a-program': slot L1 belongs to 'lean', not to"
            " the area 'mechanics'",
        ),
        (
            lambda d: d["concepts"][1].update(id="motion-as-a-program"),
            "concept 'motion-as-a-program': the id is used twice",
        ),
        (
            lambda d: d["concepts"][0].update(id="Motion"),
            "concept 'Motion': 'id' must be a lower-case identifier",
        ),
        (
            lambda d: d["concepts"][0].update(position=[3, 1]),
            "concept 'motion-as-a-program': 'position' must be [column, row]",
        ),
        (
            lambda d: d["concepts"][1].update(position=[1, 1]),
            "concept 'numerical-integration': another concept of 'mechanics' has"
            " the position [1, 1]",
        ),
        (
            lambda d: d["concepts"][0].update(explanation=" "),
            "concept 'motion-as-a-program': 'explanation' must be a text",
        ),
        (
            lambda d: d["connections"][0].update(rationale=""),
            "'rationale' must be a text",
        ),
        (
            lambda d: d["connections"][0].update(type="looks-alike"),
            "'type' must be one of same-mathematics, limit, same-method, application",
        ),
        (
            lambda d: d["connections"][0].update(
                concepts=["oscillation-and-resonance", "oscillation-and-resonance"]
            ),
            "joins a concept to itself",
        ),
        (
            lambda d: d["connections"].append(
                {
                    "concepts": ["circuits-and-resonance", "oscillation-and-resonance"],
                    "type": "same-method",
                    "rationale": "Again.",
                }
            ),
            "the two concepts are connected twice",
        ),
    ],
)
def test_a_manifest_that_breaks_a_rule_is_rejected(change, expected):
    assert any(expected in message for message in broken(change)), broken(change)


@pytest.mark.parametrize(
    "field",
    [
        "title",
        "description",
        "outcomes",
        "prerequisites",
        "state",
        "count",
        "lesson",
        "lessons",
        "illustration",
    ],
)
def test_a_field_that_another_source_holds_is_rejected(field):
    problems = broken(lambda d: d["concepts"][0].update({field: "x"}))
    assert problems == [
        f"concept 'motion-as-a-program': {field!r} is held by the curriculum"
        " file or the front matter, or derived by the build, not written in the"
        " map manifest"
    ]


@pytest.mark.parametrize("kind", ["prerequisite", "requires", "capstone"])
def test_a_prerequisite_or_a_capstone_link_cannot_be_written(kind):
    problems = broken(lambda d: d["connections"][0].update(type=kind))
    assert len(problems) == 1
    assert "is not curated: prerequisites come from the front matter" in problems[0]


def test_a_prerequisite_field_cannot_be_written_on_a_connection():
    problems = broken(lambda d: d["connections"][0].update(requires=["x"]))
    assert "'requires' is held by the curriculum file" in problems[0]


def test_a_capstone_without_its_concept_is_rejected():
    problems = broken(
        lambda d: d["concepts"].remove(concept(d, "tsunami-reconstruction"))
    )
    assert problems == [
        "capstone slot FL10 must be represented by exactly one concept (a"
        " concept whose only slot it is); found 0"
    ]


def test_a_capstone_with_two_concepts_is_rejected():
    def change(d: dict) -> None:
        d["concepts"].append(
            {**concept(d, "tsunami-reconstruction"), "id": "tsunami-again",
             "position": [2, 4]}
        )  # fmt: skip

    assert any("capstone slot FL10" in m and "found 2" in m for m in broken(change))


def test_a_concept_of_two_capstones_alone_is_rejected():
    problems = broken(
        lambda d: concept(d, "tsunami-reconstruction").update(slots=["FL10", "T11"])
    )
    assert any("names only capstone slots" in message for message in problems)


def test_reading_a_broken_manifest_fails_with_every_problem(tmp_path: Path):
    content = data()
    content["concepts"][0]["title"] = "Motion"
    content["connections"][0]["type"] = "prerequisite"
    (tmp_path / ATLAS_FILE).write_text(yaml.safe_dump(content), encoding="utf-8")
    with pytest.raises(ValueError) as error:
        AtlasManifest.read(tmp_path, CURRICULUM)
    assert "'title' is held" in str(error.value)
    assert "is not curated" in str(error.value)


def test_a_site_without_the_manifest_fails_once_it_has_a_capstone(tmp_path: Path):
    assert AtlasManifest.read(tmp_path, Curriculum()) == AtlasManifest()
    with pytest.raises(ValueError, match="capstone slot T11"):
        AtlasManifest.read(tmp_path, CURRICULUM)


# --- The curation -----------------------------------------------------------------


def test_every_course_and_path_slot_is_on_the_map_once():
    # The capstone slots are named again by the concepts they integrate;
    # every other slot of a course or a path belongs to exactly one concept,
    # so that every planned slot is labelled on the map.
    named: dict[str, list[str]] = {}
    for item in ATLAS.concepts:
        for label in item.slots:
            named.setdefault(label, []).append(item.id)
    for slot in CURRICULUM.slots:
        if slot.strand:
            assert slot.label not in named
        elif slot.kind == CAPSTONE:
            assert ATLAS.manifest.capstone(slot.label).id in named[slot.label]
        else:
            assert len(named[slot.label]) == 1, slot.label


def test_every_course_and_path_has_concepts():
    for area in ATLAS.areas:
        assert ATLAS.in_area(area), area


def test_the_capstones_have_their_concepts_and_members():
    for label in ("T11", "EM9", "FL10"):
        capstone = ATLAS.manifest.capstone(label)
        assert ATLAS.capstone_of(capstone).label == label
        assert [m for m in ATLAS.memberships() if m.capstone == capstone.id]
    assert "hypothetical" in ATLAS.manifest.capstone("T11").explanation
    assert "not a model of any real chip" in ATLAS.manifest.capstone("T11").explanation


def test_every_course_has_an_illustration_of_its_own():
    assert set(ILLUSTRATIONS) == {course.id for course in COURSES}
    drawings = [draw() for draw in ILLUSTRATIONS.values()]
    assert len(set(drawings)) == len(drawings)
    for drawing in drawings:
        assert "<text" not in drawing and not re.search(r"<image|href", drawing)


# --- What the build derives -----------------------------------------------------


def test_a_concepts_lessons_come_only_from_its_slots():
    for item in ATLAS.concepts:
        own = {slot.label for slot in ATLAS.own_slots(item)}
        assert all(lesson.slot in own for lesson in ATLAS.lessons_of(item))
        filled = {lesson.slot for lesson in ATLAS.lessons_of(item)}
        assert {slot.label for slot in ATLAS.planned_of(item)} == own - filled


def test_the_published_counts_equal_the_lessons():
    filled = {lesson.slot for lesson in PATH.lessons if lesson.slot}
    total = sum(len(ATLAS.lessons_of(item)) for item in ATLAS.concepts)
    assert total == len(filled - {"L1"})
    for area in ATLAS.areas:
        published, slots = ATLAS.area_counts(area)
        home = [s for s in CURRICULUM.slots if (s.course or s.path) == area]
        assert slots == len(home)
        assert published == sum(1 for s in home if s.label in filled)


def test_the_prerequisite_edges_equal_the_front_matter():
    concept_of = {
        lesson.id: item.id
        for item in ATLAS.concepts
        for lesson in ATLAS.lessons_of(item)
    }
    expected: dict[tuple[str, str], set[tuple[str, str]]] = {}
    for lesson in PATH.lessons:
        for required in lesson.prerequisites:
            if lesson.id in concept_of and required in concept_of:
                source, target = concept_of[required], concept_of[lesson.id]
                if source != target:
                    expected.setdefault((source, target), set()).add(
                        (required, lesson.id)
                    )
    found = {
        (edge.source, edge.target): set(edge.pairs)
        for edge in ATLAS.prerequisite_edges()
    }
    assert found == expected
    # A planned slot has no lesson, so no edge touches only planned concepts.
    planned = {item.id for item in ATLAS.concepts if ATLAS.state(item) == PLANNED}
    assert not any(
        edge.source in planned or edge.target in planned
        for edge in ATLAS.prerequisite_edges()
    )


def _with_published_capstone() -> Atlas:
    lesson = replace(PATH.lessons[0], id="tsunami", slot="FL10", page="lessons/x.qmd")
    path = replace(PATH, lessons=(*PATH.lessons, lesson))
    return Atlas(path, ATLAS.manifest)


def test_a_capstone_is_linked_only_when_it_is_published():
    planned = str(AtlasSection(ATLAS))
    for label in ("T11", "EM9", "FL10"):
        item = re.search(
            rf'<li class="atlas-capstone-item" data-slot="{label}">(.*?)</li>', planned
        ).group(1)
        assert "Planned, not published." in item
        assert "lessons/" not in item
    published = str(AtlasSection(_with_published_capstone()))
    item = re.search(
        r'<li class="atlas-capstone-item" data-slot="FL10">(.*?)</li>', published
    ).group(1)
    assert 'href="../lessons/x.html"' in item
    assert "Published." in item


def test_the_capstones_planned_description_is_only_the_manifests_explanation():
    page = str(AtlasSection(ATLAS))
    descriptions = re.findall(r'<p class="capstone-description">(.*?)</p>', page)
    expected = [
        ATLAS.manifest.capstone(label).explanation for label in ("T11", "EM9", "FL10")
    ]
    # Once in the list of capstone projects and once in each panel.
    assert sorted(unescape(text) for text in descriptions) == sorted(expected * 2)


# --- The drawing and the page -----------------------------------------------------


@pytest.fixture(scope="module")
def page() -> str:
    return str(AtlasSection(ATLAS))


def svg(page: str) -> str:
    return re.search(r"<svg [^>]*class=\"atlas-svg\".*?</svg>", page, re.S).group(0)


def test_the_map_shows_every_course_path_and_concept(page: str):
    drawing = svg(page)
    words = " ".join(unescape(re.sub(r"<[^>]+>", " ", drawing)).split())
    for area in ATLAS.areas:
        assert f'data-area="{area}"' in drawing
        assert ATLAS.area_title(area) in words
    for item in ATLAS.concepts:
        assert f'href="#concept-{item.id}"' in drawing
        assert f'id="concept-{item.id}"' in page
    assert 'class="atlas-rail"' in drawing
    assert drawing.count('class="atlas-illustration"') == len(COURSES)
    assert 'data-concept="phased-array-beam-steering"' in drawing


def test_the_views_link_every_published_lesson_by_its_methods(page: str):
    drawing = svg(page)
    for method, lessons in ATLAS.views():
        view = re.search(
            rf'<g class="atlas-view" data-method="{method}">(.*?)</g>', drawing, re.S
        ).group(1)
        assert re.findall(r'data-lesson="([^"]+)"', view) == [
            item.id for item in lessons
        ]
    linked = set(re.findall(r'class="atlas-lesson" data-lesson="([^"]+)"', drawing))
    assert linked == {lesson.id for lesson in PATH.lessons}
    assert ATLAS.views()[0][0] == "lean"
    without_slot = {lesson.id for lesson in PATH.lessons if not lesson.slot}
    assert without_slot and without_slot <= linked


def test_the_three_edge_types_have_their_own_marks(page: str):
    drawing = svg(page)
    edges = re.findall(r'<path class="atlas-edge atlas-edge-(\w+)"[^>]*>', drawing)
    assert edges.count("prerequisite") == len(ATLAS.prerequisite_edges())
    assert edges.count("conceptual") == len(ATLAS.manifest.connections)
    assert edges.count("capstone") == len(ATLAS.memberships())
    markers = {
        kind: set(re.findall(rf'atlas-edge-{kind}"[^>]*end="url\(#([^)]+)\)"', drawing))
        for kind in ("prerequisite", "conceptual", "capstone")
    }
    assert all(len(found) == 1 for found in markers.values())
    assert len(set().union(*markers.values())) == 3


def test_a_planned_concept_or_slot_is_labelled_and_never_a_lesson_link(page: str):
    drawing = svg(page)
    for item in ATLAS.concepts:
        node = re.search(
            rf'<a href="([^"]+)" class="([^"]+)" data-concept="{item.id}"'
            r"[^>]*>(.*?)</a>",
            drawing,
            re.S,
        )
        assert node.group(1) == f"#concept-{item.id}"
        if ATLAS.state(item) == PLANNED:
            assert "atlas-planned" in node.group(2)
            assert "planned" in node.group(3)
    panels = re.findall(r'<li data-slot-state="planned">(.*?)</li>', page)
    planned = sum(len(ATLAS.planned_of(item)) for item in ATLAS.concepts)
    assert len(panels) == planned
    for item in panels:
        assert "<a " not in item and "(planned, not published)" in item


def test_every_published_lesson_of_a_slot_is_linked_from_its_concepts_panel(page: str):
    for item in ATLAS.concepts:
        panel = re.search(
            rf'<details class="concept-panel" id="concept-{item.id}".*?</details>',
            page,
            re.S,
        ).group(0)
        for lesson in ATLAS.lessons_of(item):
            built = Path(lesson.page).with_suffix(".html").as_posix()
            assert f'href="../{built}"' in panel


def test_every_conceptual_connection_shows_its_type_and_rationale(page: str):
    for connection in ATLAS.manifest.connections:
        for end in connection.concepts:
            panel = re.search(rf'id="concept-{end}".*?</details>', page, re.S).group(0)
            assert connection.rationale in unescape(panel)


def test_the_textual_equivalent_names_every_concept_edge_and_view_lesson():
    sentences = AtlasSection(ATLAS).sentences()
    text = "\n".join(sentences)
    for item in ATLAS.concepts:
        assert f"Concept {item.name}, in {ATLAS.area_title(item.area)}" in text
    prerequisites = [s for s in sentences if s.startswith("Prerequisite: ")]
    assert len(prerequisites) == len(ATLAS.prerequisite_edges())
    conceptual = [s for s in sentences if s.startswith("Conceptual connection, ")]
    assert len(conceptual) == len(ATLAS.manifest.connections)
    connections = ATLAS.manifest.connections
    for connection, sentence in zip(connections, conceptual, strict=True):
        assert connection.rationale in sentence
        a, b = (ATLAS.manifest.concept(end).name for end in connection.concepts)
        assert CONNECTION_TYPES[connection.type].format(a=a, b=b) in sentence
    memberships = [s for s in sentences if s.startswith("Capstone membership: ")]
    assert len(memberships) == len(ATLAS.memberships())
    views = [s for s in sentences if s.startswith("The view ")]
    for (_, lessons), sentence in zip(ATLAS.views(), views, strict=True):
        assert all(lesson.title in sentence for lesson in lessons)


def test_the_textual_equivalent_is_in_the_page_without_links(page: str):
    text = re.search(
        r'<section class="visually-hidden" aria-labelledby="atlas-text-title">(.*?)'
        "</section>",
        page,
        re.S,
    ).group(1)
    assert "<a " not in text
    assert text.count("<li>") == len(AtlasSection(ATLAS).sentences())


def test_the_switch_breadcrumb_and_index_anchors_are_links(page: str):
    assert '<a href="#atlas-map">Map</a>' in page
    assert '<a href="#choose">Course index</a>' in page
    assert '<a href="../index.html">Home</a>' in page
    assert 'id="atlas-map"' in page and 'tabindex="0"' in page
    # The F64 index's filters act on [data-state]; the atlas has none.
    assert "data-state=" not in page
    assert "slot-label" not in page and "path-card" not in page


def test_the_section_is_the_same_on_every_build():
    assert str(AtlasSection(Atlas.read(SITE_SOURCE))) == str(AtlasSection(ATLAS))


def test_the_map_keeps_its_nodes_inside_their_areas():
    layout = AtlasMap.layout(ATLAS)
    for item in ATLAS.concepts:
        node, area = layout.nodes[item.id], layout.areas[item.area]
        assert area.x <= node.x and node.x + node.width <= area.x + area.width
        assert area.y <= node.y and node.y + node.height <= area.y + area.height
    for _, band, chips in layout.views:
        for _, chip in chips:
            assert chip.x + chip.width <= band.x + band.width


def _inside(a, b, box, inset: float = 0.01) -> bool:
    """Whether the straight stretch from a to b enters the box."""
    (x0, x1), (y0, y1) = sorted((a[0], b[0])), sorted((a[1], b[1]))
    return (
        x1 > box.x + inset
        and x0 < box.x + box.width - inset
        and y1 > box.y + inset
        and y0 < box.y + box.height - inset
    )


def test_every_edge_runs_in_the_gutters_from_one_node_to_the_other():
    layout = AtlasMap.layout(ATLAS)
    edges = ATLAS.prerequisite_edges() + ATLAS.memberships()
    assert len(layout.routes) == len(edges) + len(ATLAS.manifest.connections)
    for route, points in layout.routes:
        for end, concept_id in ((points[0], route.source), (points[-1], route.target)):
            node = layout.nodes[concept_id]
            on_x = end[0] in (node.x, node.x + node.width)
            on_y = end[1] in (node.y, node.y + node.height)
            assert on_x or on_y
        for a, b in itertools.pairwise(points):
            assert a[0] == b[0] or a[1] == b[1]
            for concept_id, node in layout.nodes.items():
                assert not _inside(a, b, node), (route.source, route.target, concept_id)
            for area, box in layout.areas.items():
                header = replace(box, height=AREA_HEADER - 4)
                assert not _inside(a, b, header), (route.source, route.target, area)


def test_no_two_edges_lie_on_one_another():
    layout = AtlasMap.layout(ATLAS)
    stretches = [
        (number, a, b)
        for number, (_, points) in enumerate(layout.routes)
        for a, b in itertools.pairwise(points)
    ]
    for index, (number, a, b) in enumerate(stretches):
        for other, c, d in stretches[index + 1 :]:
            if other == number:
                continue
            for axis in (0, 1):
                if a[axis] == b[axis] == c[axis] == d[axis]:
                    along = 1 - axis
                    low = max(min(a[along], b[along]), min(c[along], d[along]))
                    high = min(max(a[along], b[along]), max(c[along], d[along]))
                    assert high - low <= 0.5, (a, b, c, d)
