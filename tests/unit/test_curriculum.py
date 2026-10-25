"""The reference curriculum file, the slot of a lesson, the prerequisite rule
over the graph, and the planned slots on the learning path page (ADR 013)."""

import re
from collections import Counter
from pathlib import Path

import pytest
import yaml
from support.paths import REPO_ROOT, SITE_SOURCE

from pbc.authoring import COURSES, LearningPath, PathOverview
from pbc.authoring.path import (
    CURRICULUM_FILE,
    PATH_PAGE,
    Curriculum,
    Lesson,
    LessonHeader,
    curriculum_problems,
    problems,
    read_lessons,
)

FILE = SITE_SOURCE / CURRICULUM_FILE


def data() -> dict:
    return yaml.safe_load(FILE.read_text(encoding="utf-8"))


# --- The file -----------------------------------------------------------------


def test_the_file_holds_the_reference_curriculum_counted():
    # A change of these numbers is a reviewed change of the curriculum, and
    # docs/roadmap.md, "Slot mapping", is updated with it.
    curriculum = Curriculum.read(SITE_SOURCE)
    in_course = Counter(slot.course for slot in curriculum.slots if slot.course)
    assert [in_course[course.id] for course in COURSES] == [17, 12, 9, 9, 10, 8, 10, 6]
    assert sum(in_course.values()) == 81
    in_path = Counter(slot.path for slot in curriculum.slots if slot.path)
    assert [in_path[path.id] for path in curriculum.paths] == [9, 13, 5, 6]
    assert sum(in_path.values()) == 33
    assert [slot.label for slot in curriculum.slots if slot.strand] == ["L1"]
    assert len(curriculum.slots) == 115
    assert sum(slot.kind == "measured-data lab" for slot in curriculum.slots) == 16
    assert sum(slot.kind == "applied capstone" for slot in curriculum.slots) == 3


def test_every_slot_of_the_file_is_in_the_slot_mapping_of_the_roadmap():
    roadmap = (REPO_ROOT / "docs" / "roadmap.md").read_text(encoding="utf-8")
    start = roadmap.index("## Slot mapping")
    mapping = roadmap[
        start : roadmap.index("### Enhancements of existing slots", start)
    ]
    in_roadmap = set(
        re.findall(r"^\| (?:[a-z ]+ \| )?([A-Z]+[0-9]+) \|", mapping, re.M)
    )
    assert in_roadmap == {slot.label for slot in Curriculum.read(SITE_SOURCE).slots}


def test_the_labs_and_capstones_are_where_the_roadmap_puts_them():
    kinds = {slot.label: slot.kind for slot in Curriculum.read(SITE_SOURCE).slots}
    assert {label for label, kind in kinds.items() if kind == "applied capstone"} == {
        "T11",
        "EM9",
        "FL10",
    }
    assert {label for label, kind in kinds.items() if kind == "measured-data lab"} == {
        "M15", "M16", "T7", "T8", "W7", "W8", "EM7", "EM8",
        "FL7", "FL8", "Q7", "Q8", "AST8", "AST9", "MAT5", "MAT6",
    }  # fmt: skip


def test_the_teaching_order_of_the_file_is_not_the_label_order():
    curriculum = Curriculum.read(SITE_SOURCE)
    first = lambda *labels: [curriculum.index(label) for label in labels]  # noqa: E731
    for labels in (
        ("T0", "T1"),
        ("T6", "T10", "T11"),
        ("AST10", "AST4"),
        ("FL1", "FL4", "FL9", "FL5", "FL10"),
    ):
        indexes = first(*labels)
        assert indexes == sorted(indexes)
    assert (
        curriculum.index("AST10") < curriculum.index("AST4") < curriculum.index("AST5")
    )
    assert curriculum.index("T9") < curriculum.index("T10")


def broken(change) -> list[str]:
    content = data()
    change(content)
    return curriculum_problems(content)


def test_the_file_as_committed_has_no_problem():
    assert curriculum_problems(data()) == []


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        (
            lambda d: d["slots"][0].update(course="chemistry"),
            "slot 'M1': 'chemistry' is not a course of the site",
        ),
        (
            lambda d: d["slots"].append(
                {
                    "label": "ZZ1",
                    "title": "x",
                    "kind": "lesson",
                    "path": "nowhere",
                    "position": 1,
                }
            ),
            "slot 'ZZ1': 'nowhere' is not a path of the curriculum",
        ),
        (
            lambda d: d["slots"][1].update(label="M1"),
            "slot 'M1': the label is used twice",
        ),
        (
            lambda d: d["slots"][0].pop("course"),
            "slot 'M1' has no home: name a course, a path, or a strand",
        ),
        (
            lambda d: d["slots"][0].update(path="reasoning"),
            "slot 'M1' has more than one home: course and path",
        ),
        (
            lambda d: d["slots"][0].update(difficulty=2),
            "slot 'M1': 'difficulty' belongs to the front matter of a lesson,"
            " not to the curriculum file",
        ),
        (
            lambda d: d["slots"][0].update(prerequisites=[]),
            "slot 'M1': 'prerequisites' belongs to the front matter of a"
            " lesson, not to the curriculum file",
        ),
        (
            lambda d: d["slots"][0].update(kind="seminar"),
            "slot 'M1': 'kind' must be one of lesson, measured-data lab,"
            " applied capstone",
        ),
        (
            lambda d: d["paths"].pop(),
            "'paths' must list the four method paths, with their identifiers"
            " and titles, in the order of METHOD_PATHS",
        ),
        (
            lambda d: d["paths"][0].update(id="renamed"),
            "'paths' must list the four method paths, with their identifiers"
            " and titles, in the order of METHOD_PATHS",
        ),
        (
            lambda d: d["paths"].append({"id": "extra", "title": "Extra"}),
            "'paths' must list the four method paths, with their identifiers"
            " and titles, in the order of METHOD_PATHS",
        ),
        (
            lambda d: d["courses"].pop(),
            "'courses' must list the eight courses of the site, with their"
            " identifiers and titles, in the order of COURSES",
        ),
    ],
)
def test_a_file_outside_the_schema_is_rejected(change, expected):
    assert expected in broken(change)


def test_reading_a_file_outside_the_schema_fails_with_every_problem(tmp_path: Path):
    content = data()
    content["slots"][0]["course"] = "chemistry"
    content["slots"][1]["label"] = "M1"
    (tmp_path / CURRICULUM_FILE).write_text(yaml.safe_dump(content), encoding="utf-8")

    with pytest.raises(ValueError) as error:
        Curriculum.read(tmp_path)

    assert "'chemistry' is not a course" in str(error.value)
    assert "the label is used twice" in str(error.value)


def test_a_site_without_the_file_has_no_curriculum(tmp_path: Path):
    assert Curriculum.read(tmp_path) == Curriculum()


# --- The slot of a lesson -----------------------------------------------------


def lesson(
    id: str,
    strand: str = "mechanics",
    order: int = 1,
    course: str = "mechanics",
    prerequisites: tuple[str, ...] = (),
    slot: str = "",
    methods: tuple[str, ...] = ("simulation",),
) -> Lesson:
    return Lesson(
        page=f"lessons/{strand}/{order:02d}-{id}/index.qmd",
        id=id,
        title=id.upper(),
        description="",
        strand=strand,
        order=order,
        difficulty=1,
        prerequisites=prerequisites,
        outside=(),
        course=course,
        methods=methods,
        outcomes=("One thing", "Another thing"),
        related=(),
        slot=slot,
    )


CURRICULUM = Curriculum.read(SITE_SOURCE)


def messages(lessons: list[Lesson]) -> list[str]:
    return [f"{p.page}: {p.message}" for p in problems(lessons, CURRICULUM)]


def test_a_lesson_may_fill_a_slot_of_its_course():
    assert messages([lesson("kinematics", slot="M1")]) == []


def test_a_slot_that_is_not_in_the_curriculum_is_reported():
    item = lesson("kinematics", slot="M99")
    assert messages([item]) == [
        f"{item.page}: 'lesson.slot' 'M99' is not a slot of the curriculum"
    ]


def test_a_slot_claimed_by_two_lessons_is_reported_on_the_later_one():
    first = lesson("kinematics", slot="M1")
    second = lesson("newton", order=2, slot="M1")
    assert messages([first, second]) == [
        f"{second.page}: slot 'M1' is already filled by {first.page}"
    ]


def test_a_slot_of_another_course_is_reported():
    item = lesson("kinematics", slot="T1")
    assert messages([item]) == [
        f"{item.page}: slot 'T1' is a slot of the course 'thermodynamics',"
        " but 'lesson.course' is 'mechanics'"
    ]


def test_a_slot_of_a_method_path_may_be_filled_by_a_lesson_of_any_course():
    mechanics = lesson(
        "agent", strand="agents-llm", slot="AI0", methods=("llm-agents",)
    )
    thermodynamics = lesson(
        "thermo-agent",
        strand="agents-llm",
        order=2,
        course="thermodynamics",
        slot="AI1",
        methods=("llm-agents",),
    )
    assert messages([mechanics, thermodynamics]) == []


def test_without_a_curriculum_no_slot_exists():
    item = lesson("kinematics", slot="M1")
    assert [p.message for p in problems([item])] == [
        "'lesson.slot' 'M1' is not a slot of the curriculum"
    ]


def test_the_published_lessons_that_fill_a_slot_carry_it():
    slots = {item.id: item.slot for item in read_lessons(SITE_SOURCE)}
    assert {key: value for key, value in slots.items() if value} == {
        "kinematics": "M1",
        "newtons-laws": "M2",
        "projectile-with-drag": "M3",
        "harmonic-oscillator": "M4",
        "numerical-integrators": "M5",
        "energy-conservation": "M6",
        "momentum-and-collisions": "M7",
        "kepler-orbit": "M8",
        "double-pendulum-chaos": "M9",
        "lagrangian-mechanics": "M10",
        "hamiltonian-mechanics": "M11",
        "resonance": "M12",
        "many-body-gravitation": "M13",
        "nonlinear-dynamics-and-bifurcations": "M14",
        "rotational-motion": "M17",
        "gravitational-wave-strain": "M16",
        "verifying-scientific-code": "AI2",
        "automated-analysis-pipelines": "R1",
        "inverse-physics": "D6",
        "agent-experiment": "AI0",
        "counterexample-hunter": "AI3",
        "scientific-review": "AI4",
        "experimental-design-agent": "D9",
        "black-box-force-law": "D1",
        "prior-knowledge-in-discovery": "D2",
        "modified-force-law": "D3",
        "symbolic-regression": "D7",
        "discovering-differential-equations": "D8",
        "proving-what-the-simulation-showed": "L1",
        "wave-equation": "W1",
        "interference-and-resonance": "W2",
        "sound-and-the-doppler-effect": "W9",
        "electric-fields-and-potential": "EM1",
        "charged-particles-in-fields": "EM2",
        "faradays-law-and-induction": "EM3",
        "advection-and-diffusion": "FL1",
        "shock-waves-and-burgers-equation": "FL4",
        "finite-volume-methods-and-conservation-laws": "FL9",
        "shallow-water-equations": "FL5",
        # The gas lesson gets its slot with its course (F70), with T1 to T3.
        "particles-in-a-box": "T0",
        "random-walks-and-diffusion": "T1",
        "kinetic-theory-of-gases": "T2",
        "entropy-from-ensembles": "T3",
    }
    # The Lean lessons beyond the baseline have no slot.
    for lesson_id in (
        "collision-momentum-proved",
        "symplectic-euler-conserved-energy",
        "lean-exercises-on-your-machine",
        "chirp-law-proved",
    ):
        assert slots[lesson_id] == ""
    # The gas lesson moved to its course by front matter, not by address (F70).
    gas = LearningPath.read(SITE_SOURCE).lesson("particles-in-a-box")
    assert (gas.course, gas.strand) == ("thermodynamics", "agents-abm")


# --- Prerequisites as a graph (ADR 013 decision 8) ----------------------------

M1 = lesson("kinematics", slot="M1")
GAS = lesson(
    "gas", strand="agents-abm", course="thermodynamics", slot="T0", methods=("abm",)
)
T2 = lesson(
    "kinetic-theory",
    strand="thermodynamics",
    course="thermodynamics",
    prerequisites=("gas",),
    slot="T2",
)


def test_a_prerequisite_in_a_later_strand_is_accepted():
    # T2 builds on the model of the gas lesson T0, which lives in agents-abm,
    # after every thermodynamics lesson in the linear order.
    assert messages([M1, GAS, T2]) == []
    # The course view lists T0 first although its strand comes after.
    path = LearningPath((T2, M1, GAS), CURRICULUM)
    assert [item.id for item in path.in_course(COURSES[1])] == ["gas", "kinetic-theory"]


def test_a_mechanics_lesson_may_require_a_lean_lesson():
    proof = lesson("proof", strand="lean", methods=("lean",))
    needs = lesson("hamiltonian", order=2, prerequisites=("proof",), slot="M11")
    assert messages([M1, needs, proof]) == []


def test_a_prerequisite_later_in_the_same_strand_is_reported():
    early = lesson("kinematics", prerequisites=("newton",), slot="M1")
    later = lesson("newton", order=2, slot="M2")
    assert messages([early, later]) == [
        f"{early.page}: prerequisite 'newton' does not come earlier in its strand"
        " 'mechanics'"
    ]


def test_a_cycle_across_strands_is_reported():
    first = lesson("kinematics", prerequisites=("gas",), slot="M1")
    gas = Lesson(**{**GAS.__dict__, "prerequisites": ("kinematics",)})
    assert messages([first, gas]) == [
        f"{first.page}: prerequisites form a cycle: kinematics -> gas -> kinematics"
    ]


def test_the_published_lessons_pass_the_checks():
    lessons = read_lessons(SITE_SOURCE)
    assert problems(lessons, Curriculum.read(SITE_SOURCE)) == []


def test_the_course_view_orders_by_slot_then_linear_order():
    unslotted = lesson("extra", order=3)
    t1 = lesson("t1", order=2, slot="M2")
    t0 = lesson("t0", order=1, slot="M16")
    # M16 is listed after M2 in the file; the lesson without a slot is last.
    path = LearningPath((t0, t1, unslotted), CURRICULUM)
    assert [item.id for item in path.in_course(COURSES[0])] == ["t1", "t0", "extra"]


# --- The path page ------------------------------------------------------------


@pytest.fixture(scope="module")
def page() -> str:
    return str(PathOverview(LearningPath.read(SITE_SOURCE), PATH_PAGE))


def test_the_page_lists_every_published_lesson_under_its_course_and_path(page: str):
    path = LearningPath.read(SITE_SOURCE)
    for course in path.courses:
        section = page.split(f"{{#course-{course.id}}}")[1].split("\n## ")[0]
        for item in path.in_course(course):
            assert f'data-lesson-id="{item.id}"' in section
    for method_path in path.paths:
        section = page.split(f"{{#path-{method_path.id}}}")[1].split("\n## ")[0]
        section = section.split("\n### ")[0]
        ids = re.findall(r'data-lesson-id="([^"]+)"', section)
        assert ids == [item.id for item in path.in_path(method_path)]


def test_the_paths_come_after_the_courses_and_before_the_methods(page: str):
    order = [page.index(f"{{#{anchor}}}") for anchor in ("courses", "paths", "methods")]
    assert order == sorted(order)


def test_every_unfilled_slot_of_a_course_with_a_lesson_and_of_every_path_is_planned(
    page: str,
):
    path = LearningPath.read(SITE_SOURCE)
    planned = re.findall(
        r'<li class="planned-slot"[^>]*><span class="slot-label">([A-Z]+[0-9]+)</span>',
        page,
    )
    expected = [
        slot.label for course in path.courses for slot in path.planned_in_course(course)
    ]
    expected += [
        slot.label for method in path.paths for slot in path.planned_in_path(method)
    ]
    assert planned == expected
    assert "M15" in planned and "AI1" in planned and "EV1" in planned
    # The thermodynamics course shows its eight planned slots (F70), not T0 to T3.
    thermodynamics = [slot.label for slot in path.planned_in_course(COURSES[1])]
    assert thermodynamics == ["T4", "T5", "T6", "T9", "T10", "T11", "T7", "T8"]
    assert not {"T0", "T1", "T2", "T3"} & set(planned)
    assert not {item.slot for item in path.lessons} & set(planned)


def test_a_course_without_a_lesson_is_named_in_one_sentence_and_shows_no_slot(
    page: str,
):
    path = LearningPath.read(SITE_SOURCE)
    # Mechanics has lessons, thermodynamics since F70, waves since F71,
    # electromagnetism since F72, and fluids since F73; the others have none
    # yet.
    without = [
        course
        for course in COURSES[2:]
        if course.id not in {"waves", "electromagnetism", "fluids"}
    ]
    assert [course.id for course in path.planned_courses] == [
        course.id for course in without
    ]
    sentences = [
        line
        for line in page.splitlines()
        if line.startswith(f"{len(without)} further courses")
    ]
    assert len(sentences) == 1
    for course in without:
        assert course.title in sentences[0]
        assert f"{{#course-{course.id}}}" not in page
    assert "Waves and optics" not in sentences[0]
    assert "Electromagnetism" not in sentences[0]
    assert "Fluid dynamics" not in sentences[0]
    assert f"{{#course-{COURSES[1].id}}}" in page


def test_a_planned_slot_has_no_link_and_no_card(page: str):
    blocks = re.findall(r'<li class="planned-slot".*?</li>', page, re.S)
    assert blocks
    for block in blocks:
        assert "<a " not in block and "path-card" not in block
        assert "planned, not published" in block


def test_a_lesson_is_a_row_once_and_a_link_everywhere_else(page: str):
    path = LearningPath.read(SITE_SOURCE)
    cards = re.findall(r'<li class="path-card" data-lesson-id="([^"]+)"', page)
    # The canonical content of a lesson is its row under its course, once.
    assert sorted(cards) == sorted(item.id for item in path.lessons)
    links = re.findall(r'<li class="path-link" data-lesson-id="([^"]+)"', page)
    # Under each method and each path a lesson is one link, never a row.
    expected = sum(len(path.using(method)) for method in path.methods) + sum(
        len(path.in_path(method_path)) for method_path in path.paths
    )
    assert len(links) == expected
    for section in re.findall(r'<ol class="path-links">.*?</ol>', page, re.S):
        assert "path-card" not in section and "<dl>" not in section


def test_the_header_shows_the_slot_and_the_position_in_the_path():
    path = LearningPath.read(SITE_SOURCE)
    course_lesson = LessonHeader(path, path.lesson("kinematics")).markdown()
    assert "Slot\n:   M1, Kinematics as a program" in course_lesson
    path_lesson = LessonHeader(path, path.lesson("agent-experiment")).markdown()
    assert (
        "Slot\n:   AI0, number 1 of the 9 slots of the path [Physics reasoning"
        " and scientific agents]" in path_lesson
    )
    gas = LessonHeader(path, path.lesson("particles-in-a-box")).markdown()
    assert "Slot\n:   T0, Gas from simple agents" in gas
    assert "Thermodynamics and statistical physics" in gas


def test_a_course_lists_lessons_and_planned_slots_in_the_order_of_the_file(page: str):
    path = LearningPath.read(SITE_SOURCE)
    for course in path.courses:
        section = page.split(f"{{#course-{course.id}}}")[1].split("\n#")[0]
        rows = re.findall(
            r'<li class="(?:path-card" data-lesson-id|planned-slot" data-state)'
            r'="([^"]+)"[^>]*>(?:<span class="slot-label">([A-Z]+[0-9]+))?',
            section,
        )
        shown = [label or path.lesson(name).slot for name, label in rows]
        indexes = [path.curriculum.index(label) for label in shown if label]
        assert indexes == sorted(indexes)
        # A lesson without a slot comes after every slot.
        assert shown == [label for label in shown if label] + [
            label for label in shown if not label
        ]
        # The lessons are in the teaching order, planned rows between them.
        assert [name for name, label in rows if not label] == [
            item.id for item in path.in_course(course)
        ]
        assert len(rows) == len(path.in_course(course)) + len(
            path.planned_in_course(course)
        )


def test_the_page_is_closed_by_default_and_loads_nothing_from_outside(page: str):
    assert "<details open" not in page and " open>" not in page
    sources = re.findall(r'(?:src|href)="(https?:[^"]+|//[^"]+)"', page)
    assert sources == []
    assert str(PathOverview(LearningPath.read(SITE_SOURCE), PATH_PAGE)) == page
    ids = re.findall(r' id="([^"]+)"', page)
    assert len(ids) == len(set(ids))


def test_the_page_script_stores_nothing():
    script = (SITE_SOURCE / "learner" / "path.js").read_text(encoding="utf-8")
    for forbidden in ("localStorage", "sessionStorage", "document.cookie", "fetch("):
        assert forbidden not in script
