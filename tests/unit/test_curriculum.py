"""The reference curriculum file, the slot of a lesson, the prerequisite rule
over the graph, and the planned slots on the learning path page (ADR 013).

The progress of the curriculum is never written into a test: it is computed
from site/curriculum.yaml and the front matter of the lessons, and compared
with the generated view (#277)."""

import re
import shutil
from collections import Counter
from dataclasses import dataclass
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
    # The course and the slot of every lesson, as its front matter declares
    # them, read without pbc.authoring.path.
    sources = Progress.read(SITE_SOURCE)
    lessons = read_lessons(SITE_SOURCE)
    assert {item.id: (item.course, item.slot) for item in lessons} == sources.lessons
    assert sources.problems() == []
    slots = {item.id: item.slot for item in lessons}
    # The header of every lesson that fills a slot names it.
    path = LearningPath.read(SITE_SOURCE)
    for label, lesson_id in sources.filled().items():
        header = LessonHeader(path, path.lesson(lesson_id)).markdown()
        assert f"Slot\n:   {label}, " in header
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
    # The expectation computed from the sources: the unfilled slots of each
    # course with a lesson, then of every path, in the order of the YAML.
    sources = Progress.read(SITE_SOURCE)
    assert planned == sources.page_planned()
    # A slot is filled or planned, never both, and every slot of a course with
    # a lesson and of every path is on the page once, as one or the other.
    assert not set(sources.filled()) & set(planned)
    assert not path.filled() & set(planned)
    homes = [("course", course) for course in sources.shown_courses()]
    homes += [("path", method_path) for method_path in sources.paths]
    for key, home in homes:
        labels = [slot["label"] for slot in sources.slots if slot.get(key) == home]
        shown = [
            label
            for label in labels
            if (label in sources.filled()) != (label in planned)
        ]
        assert shown == labels


def test_a_course_without_a_lesson_is_named_in_one_sentence_and_shows_no_slot(
    page: str,
):
    path = LearningPath.read(SITE_SOURCE)
    sources = Progress.read(SITE_SOURCE)
    titles = {course.id: course.title for course in COURSES}
    without = sources.planned_courses()
    assert [course.id for course in path.planned_courses] == without
    count = (
        "1 further course has"
        if len(without) == 1
        else f"{len(without)} further courses have"
    )
    sentences = [line for line in page.splitlines() if line.startswith(count)]
    assert len(sentences) == (1 if without else 0)
    for course_id in without:
        assert titles[course_id] in sentences[0]
        assert f"{{#course-{course_id}}}" not in page
    for course_id in sources.shown_courses():
        assert f"{{#course-{course_id}}}" in page
        assert not sentences or titles[course_id] not in sentences[0]


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


# --- The expected progress, computed from the sources (#277) -----------------
#
# The progress of the curriculum (which slots the lessons fill, which are
# planned, and in which order the page shows them) is computed here from
# site/curriculum.yaml and the front matter of the lessons, without
# pbc.authoring.path, and compared with the generated view: LearningPath and
# the learning path page. A new lesson therefore needs no edit of a test, and
# a mismatch between the sources and the view still fails.

LESSON_FRONT_MATTER = re.compile(r"\A---\n(.*?\n)(?:---|\.\.\.)[ \t]*\n", re.S)


@dataclass(frozen=True)
class Progress:
    """What the sources declare: the courses and paths of the YAML in their
    order, its slots in teaching order, and the course and slot of each
    lesson by id, in the order of the lesson files."""

    courses: tuple[str, ...]
    paths: tuple[str, ...]
    slots: tuple[dict, ...]
    lessons: dict[str, tuple[str, str]]  # id -> (course, slot or "")

    @classmethod
    def read(cls, site: Path) -> Progress:
        content = yaml.safe_load((site / "curriculum.yaml").read_text(encoding="utf-8"))
        lessons = {}
        for page in sorted((site / "lessons").glob("*/*/index.qmd")):
            match = LESSON_FRONT_MATTER.match(page.read_text(encoding="utf-8"))
            assert match, f"{page} has no front matter"
            meta = yaml.safe_load(match.group(1))["lesson"]
            lessons[str(meta["id"])] = (
                str(meta["course"]),
                str(meta.get("slot") or ""),
            )
        return cls(
            tuple(item["id"] for item in content["courses"]),
            tuple(item["id"] for item in content["paths"]),
            tuple(content["slots"]),
            lessons,
        )

    def problems(self) -> list[str]:
        """A slot a lesson names that is not in the YAML, that is the slot of
        another course, or that another lesson already fills."""
        found = []
        homes = {slot["label"]: slot.get("course", "") for slot in self.slots}
        filled: dict[str, str] = {}
        for lesson_id, (course, label) in self.lessons.items():
            if not label:
                continue
            if label not in homes:
                found.append(f"{lesson_id}: slot {label!r} is not in the curriculum")
            elif homes[label] and homes[label] != course:
                found.append(
                    f"{lesson_id}: slot {label!r} is a slot of {homes[label]!r},"
                    f" not of {course!r}"
                )
            if label in filled:
                found.append(
                    f"{lesson_id}: slot {label!r} is already filled by {filled[label]}"
                )
            filled.setdefault(label, lesson_id)
        return found

    def filled(self) -> dict[str, str]:
        """The label of each slot a lesson fills, and the lesson."""
        return {
            label: lesson_id for lesson_id, (_, label) in self.lessons.items() if label
        }

    def shown_courses(self) -> list[str]:
        """The courses with a lesson, in the order of the YAML."""
        return [
            course
            for course in self.courses
            if any(home == course for home, _ in self.lessons.values())
        ]

    def planned_courses(self) -> list[str]:
        return [course for course in self.courses if course not in self.shown_courses()]

    def rows(self, key: str, home: str) -> list[tuple[str, str]]:
        """The rows of the course or path ``home`` in the order of the YAML:
        ("lesson", id) for a slot of ``home`` that a lesson fills,
        ("planned", label) for one that none fills, and, under a course, also
        ("lesson", id) for a lesson of the course that fills a slot of a path
        or a strand."""
        filled = self.filled()
        rows = []
        for slot in self.slots:
            label = slot["label"]
            if slot.get(key) == home:
                rows.append(
                    ("lesson", filled[label]) if label in filled else ("planned", label)
                )
            elif (
                key == "course"
                and label in filled
                and not slot.get("course")
                and self.lessons[filled[label]][0] == home
            ):
                rows.append(("lesson", filled[label]))
        return rows

    def planned(self, key: str, home: str) -> list[str]:
        return [label for kind, label in self.rows(key, home) if kind == "planned"]

    def unslotted(self, course: str) -> set[str]:
        """The lessons of the course without a slot: shown after every slot."""
        return {
            lesson_id
            for lesson_id, (home, label) in self.lessons.items()
            if home == course and not label
        }

    def page_planned(self) -> list[str]:
        """The planned slots in the order of the page: those of each course
        with a lesson, then those of every path."""
        labels = [
            label for c in self.shown_courses() for label in self.planned("course", c)
        ]
        return labels + [label for p in self.paths for label in self.planned("path", p)]


def counts(lessons: int, planned: int) -> str:
    text = f"{lessons} published lesson{'s' if lessons != 1 else ''}"
    return text + (f", {planned} planned" if planned else "")


PLANNED_LABEL = re.compile(
    r'<li class="planned-slot"[^>]*><span class="slot-label">([A-Z]+[0-9]+)</span>'
)
PAGE_ROW = re.compile(
    r'<li class="(?:path-card|path-link)" data-lesson-id="([^"]+)"'
    r'|<li class="planned-slot"[^>]*><span class="slot-label">([A-Z]+[0-9]+)</span>'
)


def page_rows(section: str) -> list[tuple[str, str]]:
    return [
        ("lesson", lesson_id) if lesson_id else ("planned", label)
        for lesson_id, label in PAGE_ROW.findall(section)
    ]


def mismatches(sources: Progress, path: LearningPath, page: str) -> list[str]:
    """Every way the view differs from the progress the sources declare, and
    every problem of the sources themselves."""
    found = sources.problems()

    def compare(what: str, view: object, expected: object) -> None:
        if view != expected:
            found.append(f"{what}: the view shows {view}, the sources give {expected}")

    compare(
        "the course and the slot of each lesson",
        {item.id: (item.course, item.slot) for item in path.lessons},
        sources.lessons,
    )
    compare(
        "the courses with a lesson",
        [c.id for c in path.courses],
        sources.shown_courses(),
    )
    compare(
        "the courses without a lesson",
        [c.id for c in path.planned_courses],
        sources.planned_courses(),
    )
    courses = {course.id: course for course in COURSES}
    for course_id in sources.shown_courses():
        course = courses[course_id]
        rows = sources.rows("course", course_id)
        slotted = [value for kind, value in rows if kind == "lesson"]
        taught = [item.id for item in path.in_course(course)]
        compare(f"the slotted lessons of {course_id}", taught[: len(slotted)], slotted)
        compare(
            f"the lessons of {course_id} without a slot",
            set(taught[len(slotted) :]),
            sources.unslotted(course_id),
        )
        compare(
            f"the planned slots of {course_id}",
            [slot.label for slot in path.planned_in_course(course)],
            sources.planned("course", course_id),
        )
        if f"{{#course-{course_id}}}" not in page:
            found.append(f"the page has no section of the course {course_id}")
            continue
        section = page.split(f"{{#course-{course_id}}}")[1].split("\n#")[0]
        shown = page_rows(section)
        compare(f"the rows of {course_id} on the page", shown[: len(rows)], rows)
        compare(
            f"the rows of {course_id} without a slot on the page",
            set(value for _, value in shown[len(rows) :]),
            sources.unslotted(course_id),
        )
        compare(
            f"the count of {course_id} on the page",
            re.findall(r'<p class="course-count">([^<]*)\.</p>', section),
            [
                counts(
                    len(slotted) + len(sources.unslotted(course_id)),
                    len(rows) - len(slotted),
                )
            ],
        )
    for course_id in sources.planned_courses():
        if f"{{#course-{course_id}}}" in page:
            found.append(f"the page shows the course {course_id}, which has no lesson")
    for method_path in path.paths:
        rows = sources.rows("path", method_path.id)
        compare(
            f"the lessons of the path {method_path.id}",
            [item.id for item in path.in_path(method_path)],
            [value for kind, value in rows if kind == "lesson"],
        )
        compare(
            f"the planned slots of the path {method_path.id}",
            [slot.label for slot in path.planned_in_path(method_path)],
            sources.planned("path", method_path.id),
        )
        if f"{{#path-{method_path.id}}}" not in page:
            found.append(f"the page has no section of the path {method_path.id}")
            continue
        section = page.split(f"{{#path-{method_path.id}}}")[1].split("\n#")[0]
        compare(
            f"the rows of the path {method_path.id} on the page",
            page_rows(section),
            rows,
        )
        planned = sum(kind == "planned" for kind, _ in rows)
        compare(
            f"the count of the path {method_path.id} on the page",
            re.findall(r'<p class="path-count">([^<]*)</p>', section),
            [counts(len(rows) - planned, planned)],
        )
    compare(
        "the planned slots on the page",
        PLANNED_LABEL.findall(page),
        sources.page_planned(),
    )
    return found


def view_failures(site: Path) -> list[str]:
    """The mismatches between the sources of ``site`` and the view generated
    from them; a view that rejects the sources is one."""
    sources = Progress.read(site)
    try:
        path = LearningPath.read(site)
    except ValueError as error:
        return [*sources.problems(), f"the view rejects the sources: {error}"]
    return mismatches(sources, path, str(PathOverview(path, PATH_PAGE)))


def test_the_view_shows_the_progress_the_sources_declare():
    assert view_failures(SITE_SOURCE) == []


# --- The check still fails (#277) ---------------------------------------------


def site_copy(tmp_path: Path) -> Path:
    """A throwaway copy of the sources of the progress: the curriculum file
    and the lesson pages."""
    shutil.copy(FILE, tmp_path / CURRICULUM_FILE)
    for page in (SITE_SOURCE / "lessons").glob("*/*/index.qmd"):
        target = tmp_path / page.relative_to(SITE_SOURCE)
        target.parent.mkdir(parents=True)
        shutil.copy(page, target)
    return tmp_path


def front_matter(page: Path) -> tuple[dict, str]:
    text = page.read_text(encoding="utf-8")
    match = LESSON_FRONT_MATTER.match(text)
    assert match
    return yaml.safe_load(match.group(1)), text[match.end() :]


def write_front_matter(page: Path, content: dict, body: str = "") -> None:
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(
        f"---\n{yaml.safe_dump(content, sort_keys=False)}---\n{body}", encoding="utf-8"
    )


def page_of(site: Path, lesson_id: str) -> Path:
    for page in (site / "lessons").glob("*/*/index.qmd"):
        if front_matter(page)[0]["lesson"]["id"] == lesson_id:
            return page
    raise LookupError(lesson_id)


def first_slot_of(course: str) -> str:
    return next(
        slot["label"] for slot in data()["slots"] if slot.get("course") == course
    )


@pytest.mark.parametrize(
    ("slot", "expected"),
    [
        ("M99", "kinematics: slot 'M99' is not in the curriculum"),
        (first_slot_of("quantum"), "is a slot of 'quantum', not of 'mechanics'"),
        ("M2", "slot 'M2' is already filled by"),
    ],
)
def test_a_lesson_whose_front_matter_names_the_wrong_slot_fails(
    tmp_path: Path, slot: str, expected: str
):
    site = site_copy(tmp_path)
    page = page_of(site, "kinematics")
    content, body = front_matter(page)
    content["lesson"]["slot"] = slot
    write_front_matter(page, content, body)

    failures = view_failures(site)

    assert any(expected in failure for failure in failures), failures


class FillsLess(LearningPath):
    """A defective view: it forgets that a lesson fills one slot, so the page
    shows that slot as planned."""

    def filled(self) -> frozenset[str]:
        filled = super().filled()
        return filled - {min(filled)}


class DropsPlanned(LearningPath):
    """A defective view: it drops the last planned slot of each course and
    path."""

    def planned_in_course(self, course):
        return super().planned_in_course(course)[:-1]

    def planned_in_path(self, path):
        return super().planned_in_path(path)[:-1]


@pytest.mark.parametrize("view", [FillsLess, DropsPlanned])
def test_a_view_that_misstates_the_planned_slots_fails(view: type[LearningPath]):
    path = LearningPath.read(SITE_SOURCE)
    defective = view(path.lessons, path.curriculum)

    failures = mismatches(
        Progress.read(SITE_SOURCE), defective, str(PathOverview(defective, PATH_PAGE))
    )

    assert any("planned" in failure for failure in failures), failures


def test_a_page_that_shows_a_filled_slot_as_planned_or_drops_one_fails(page: str):
    sources = Progress.read(SITE_SOURCE)
    path = LearningPath.read(SITE_SOURCE)
    label, lesson_id = next(iter(sources.filled().items()))
    planned = (
        f'<li class="planned-slot" data-state="planned"><span class="slot-label">'
        f"{label}</span> (planned, not published)</li>\n"
    )
    row = f'<li class="path-card" data-lesson-id="{lesson_id}"'
    shown_as_planned = page.replace(row, planned + row, 1)
    dropped = re.sub(r'<li class="planned-slot".*?</li>\n', "", page, count=1)

    for broken_page in (shown_as_planned, dropped):
        assert broken_page != page
        failures = mismatches(sources, path, broken_page)
        assert any("the planned slots on the page" in item for item in failures)


def test_a_new_lesson_that_fills_a_slot_needs_no_edit_of_a_test(tmp_path: Path):
    site = site_copy(tmp_path)
    before = Progress.read(site)
    course = next(c for c in before.shown_courses() if before.planned("course", c))
    label = before.planned("course", course)[0]
    pages = sorted((site / "lessons" / course).glob("*/index.qmd"))
    template, _ = front_matter(pages[-1])
    order = max(front_matter(page)[0]["lesson"]["order"] for page in pages) + 1
    template["title"] = "A throwaway lesson"
    template["lesson"].update(
        id="throwaway-lesson",
        order=order,
        slot=label,
        prerequisites={"lessons": [], "outside": []},
        related=[],
    )
    write_front_matter(
        site / "lessons" / course / f"{order:02d}-throwaway" / "index.qmd", template
    )

    after = Progress.read(site)

    assert after.filled()[label] == "throwaway-lesson"
    assert label not in after.page_planned()
    assert len(after.page_planned()) == len(before.page_planned()) - 1
    assert view_failures(site) == []
