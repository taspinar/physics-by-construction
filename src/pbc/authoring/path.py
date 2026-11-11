"""The learning path: every lesson of the site in order.

The path is derived from the front matter of the lessons when a page is
built; there is no second, hand-maintained list (docs/architecture.md,
"Lesson model"). This module defines the strands, the courses, the methods,
and the one difficulty scale of the site, reads the lessons, puts them in
order, validates the result, and renders the learning path page and the
header of a lesson. The lesson source checks validate with the same code.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from html import escape
from pathlib import Path

import yaml

from pbc.authoring.context import marker
from pbc.authoring.glossary import Glossary, before_you_begin, definitions
from pbc.authoring.progress import (
    EXPLANATION_ANCHOR,
    PROGRESS_SENTENCE,
    STORAGE_KEY,
    progress_markup,
    raw_html,
    recommendations_markup,
)
from pbc.authoring.website import (
    PAGE_FILE,
    introduced,
    introduction_page,
    page_href,
    project_root,
)

_href = page_href

# Where the lessons and the learning path page sit in the website project.
LESSONS_DIRECTORY = "lessons"
PATH_PAGE = "path/index.qmd"
PATH_SCRIPT = "learner/path.js"
# The heading of a lesson page that says how to reproduce it.
REPRODUCE_ANCHOR = "reproduce-this"


@dataclass(frozen=True)
class Course:
    id: str
    title: str
    description: str


# The eight courses of the reference curriculum (ADR 013 decision 1), in the
# order of the learning path. An identifier never changes and is never
# reused. A lesson belongs to one primary course; a course appears on the
# learning path page once it has a lesson, and until then it is only named.
COURSES = (
    Course(
        "mechanics",
        "Classical mechanics",
        "Mechanics with numerical simulation: a model and its assumptions, a"
        " short program that steps it forward in time, and a comparison with"
        " what theory predicts. The core lessons are the mechanics lessons;"
        " the extensions repeat the course's results with an agent, with"
        " many agents, and with a proof.",
    ),
    Course(
        "thermodynamics",
        "Thermodynamics and statistical physics",
        "Heat, entropy, and equilibrium built from the motion of many"
        " particles: random walks, kinetic theory, the Ising model, and"
        " molecular dynamics.",
    ),
    Course(
        "waves",
        "Waves and optics",
        "Waves and what they do: interference, refraction, polarisation,"
        " diffraction, and the inverse problem of imaging.",
    ),
    Course(
        "electromagnetism",
        "Electromagnetism",
        "Electric and magnetic fields from Coulomb's law to Maxwell's"
        " equations, solved on a grid and checked against measurements.",
    ),
    Course(
        "fluids",
        "Fluid dynamics",
        "Flow from advection and diffusion to the Navier-Stokes equations,"
        " shocks, and shallow water, with finite-volume methods.",
    ),
    Course(
        "quantum",
        "Quantum physics",
        "The Schrodinger equation, tunnelling, spin, entanglement, and"
        " decoherence, computed and then measured.",
    ),
    Course(
        "astrophysics",
        "Astrophysics, cosmology, and relativity",
        "Gravity beyond two bodies, special and general relativity, cosmic"
        " expansion, gravitational waves, and observations of the sky.",
    ),
    Course(
        "materials",
        "Condensed matter and materials physics",
        "Crystals, phonons, bands, elasticity, and defects, and how their"
        " properties show in measurements.",
    ),
)


@dataclass(frozen=True)
class Strand:
    id: str
    title: str
    description: str


# The strands in learning path order (docs/architecture.md, "Lesson model";
# ADR 013 decision 2): every course is a strand with its identifier, then the
# three method strands. A course's directory exists once it has a lesson.
STRANDS = (
    *(Strand(course.id, course.title, course.description) for course in COURSES),
    Strand(
        "agents-llm",
        "Physics and AI: LLM agents",
        "Experiments driven by LLM agents: an agent proposes hypotheses and"
        " tests them by running the simulation code of earlier lessons, on"
        " your own machine with your own API key.",
    ),
    Strand(
        "agents-abm",
        "Agent-based modelling",
        "Agent-based modelling without LLMs: many simple agents with local"
        " rules, and the collective behaviour that emerges from them.",
    ),
    Strand(
        "lean",
        "Formal proofs",
        "Formal proofs: results about the models stated as theorems in Lean 4"
        " with Mathlib and checked by machine.",
    ),
)


@dataclass(frozen=True)
class Difficulty:
    level: int
    title: str
    description: str


# The one difficulty scale of the site. Lesson front matter states the level;
# the learning path page explains the scale from this definition.
DIFFICULTIES = (
    Difficulty(
        1,
        "Introductory",
        "Builds one idea from the outside prerequisites alone and shows every step.",
    ),
    Difficulty(
        2,
        "Intermediate",
        "Builds on earlier lessons and combines their ideas. The exercises"
        " need more than the worked examples show.",
    ),
    Difficulty(
        3,
        "Advanced",
        "Longer derivations, experiments, or proofs, with exercises that"
        " leave the route to you.",
    ),
)


@dataclass(frozen=True)
class Method:
    id: str
    title: str
    description: str


# The ways of working that cut across courses (ADR 008). A lesson lists the
# methods it uses; the path page shows one path per method.
METHODS = (
    Method(
        "simulation",
        "Simulation",
        "Lessons that build a model as a program and check it against theory.",
    ),
    Method(
        "llm-agents",
        "LLM agents",
        "Lessons in which a language model proposes and runs experiments with"
        " the simulation code, on your own machine with your own API key.",
    ),
    Method(
        "abm",
        "Agent-based modelling",
        "Lessons with many simple agents, local rules, and the collective"
        " behaviour that emerges from them.",
    ),
    Method(
        "lean",
        "Formal proofs",
        "Lessons that state results as theorems in Lean 4 with Mathlib and"
        " check them by machine.",
    ),
    Method(
        "measured-data",
        "Measured data",
        "Lessons that compare a model with measurements.",
    ),
    Method(
        "coding-agents",
        "Coding agents",
        "Exercises in which a coding agent works on the learner's machine.",
    ),
)

# Outcomes a lesson states: what the reader can do afterwards.
OUTCOMES_RANGE = (2, 5)

_STRAND_INDEX = {strand.id: index for index, strand in enumerate(STRANDS)}
_COURSE = {course.id: course for course in COURSES}
_METHOD = {method.id: method for method in METHODS}
_DIFFICULTY = {difficulty.level: difficulty for difficulty in DIFFICULTIES}


@dataclass(frozen=True)
class Lesson:
    """What the learning path knows about one lesson: its front matter."""

    page: str  # relative to the website project, "lessons/<strand>/<dir>/index.qmd"
    id: str
    title: str
    description: str  # "" when the lesson has none
    strand: str
    order: int
    difficulty: int
    prerequisites: tuple[str, ...]  # lesson ids
    outside: tuple[str, ...]  # what no lesson on the site teaches
    course: str
    methods: tuple[str, ...]
    outcomes: tuple[str, ...]
    related: tuple[str, ...]  # lesson ids the lesson links as extensions
    slot: str = ""  # the label of the curriculum slot the lesson fills, or ""
    preview: str = ""  # the label of the figure cell that is the preview, or ""


# --- The reference curriculum -------------------------------------------------

# Where the curriculum file sits in the website project (ADR 013 decision 3).
CURRICULUM_FILE = "curriculum.yaml"

KINDS = ("lesson", "measured-data lab", "applied capstone", "product capstone")
# The capstone of a course and the capstone of a method path, which teaches a
# local software product (ADR 022 decision 3); the atlas, Home, and the path
# view treat the two alike wherever they mark or choose a capstone.
APPLIED_CAPSTONE = "applied capstone"
PRODUCT_CAPSTONE = "product capstone"
CAPSTONES = (APPLIED_CAPSTONE, PRODUCT_CAPSTONE)

# The one slot that has neither a course nor a method path as its home is the
# Lean slot of the baseline; its home is the strand.
HOME_STRANDS = ("lean",)

_LABEL = re.compile(r"[A-Z]+[0-9]+")
_PATH_ID = re.compile(r"[a-z][a-z0-9]*(-[a-z0-9]+)*")
_SLOT_KEYS = {
    "label",
    "title",
    "kind",
    "course",
    "path",
    "position",
    "strand",
    "extension",
}
# What a lesson's front matter holds; the curriculum file must not.
_FRONT_MATTER_FIELDS = {
    "id",
    "description",
    "outcomes",
    "prerequisites",
    "difficulty",
    "methods",
    "related",
    "order",
    "format",
    "lean-modules",
    "lessons",
    "outside",
    "preview",
    "experiment",
}


@dataclass(frozen=True)
class MethodPath:
    """One of the four method paths of the reference curriculum: a secondary
    view over lessons that fill its slots, never a course or a strand."""

    id: str
    title: str


@dataclass(frozen=True)
class Slot:
    """One planned lesson of the reference curriculum: what the file declares.

    The home is one of ``course``, ``path`` (with its ``position``), or
    ``strand``; the other two are empty. An extension slot (ADR 022
    decision 2) is optional depth of its method path: listed after the
    path's core slots and never counted with them.
    """

    label: str
    title: str
    kind: str
    course: str = ""
    path: str = ""
    position: int = 0
    strand: str = ""
    extension: bool = False

    @property
    def is_capstone(self) -> bool:
        return self.kind in CAPSTONES


@dataclass(frozen=True)
class Curriculum:
    """The reference curriculum as declared data: the method paths and every
    slot, in teaching order. It holds what is planned; what is published
    comes from the front matter of the lessons."""

    paths: tuple[MethodPath, ...] = ()
    slots: tuple[Slot, ...] = ()

    @classmethod
    def read(cls, site: Path) -> Curriculum:
        """Read ``curriculum.yaml`` of the website project ``site``; a site
        without the file has an empty curriculum. Raises ``ValueError`` when
        the file is outside the schema; the message lists every problem."""
        file = site / CURRICULUM_FILE
        if not file.is_file():
            return cls()
        try:
            data = yaml.safe_load(file.read_text(encoding="utf-8"))
        except yaml.YAMLError as error:
            raise ValueError(f"{CURRICULUM_FILE} is not valid YAML: {error}") from None
        return cls.parse(data)

    @classmethod
    def parse(cls, data: object) -> Curriculum:
        found = curriculum_problems(data)
        if found:
            raise ValueError(
                f"{CURRICULUM_FILE} is outside its schema:\n"
                + "\n".join(f"  {message}" for message in found)
            )
        assert isinstance(data, dict)
        return cls(
            tuple(MethodPath(item["id"], item["title"]) for item in data["paths"]),
            tuple(
                Slot(
                    label=item["label"],
                    title=item["title"],
                    kind=item["kind"],
                    course=item.get("course", ""),
                    path=item.get("path", ""),
                    position=item.get("position", 0),
                    strand=item.get("strand", ""),
                    extension=item.get("extension", False),
                )
                for item in data["slots"]
            ),
        )

    def slot(self, label: str) -> Slot | None:
        return next((slot for slot in self.slots if slot.label == label), None)

    def index(self, label: str) -> int | None:
        """Where the file lists the slot: the teaching order."""
        return next(
            (index for index, slot in enumerate(self.slots) if slot.label == label),
            None,
        )

    def path(self, path_id: str) -> MethodPath:
        return next(path for path in self.paths if path.id == path_id)

    def in_course(self, course: Course) -> tuple[Slot, ...]:
        return tuple(slot for slot in self.slots if slot.course == course.id)

    def in_path(self, path: MethodPath) -> tuple[Slot, ...]:
        """Every slot of the path: its core slots, then its extensions."""
        return tuple(slot for slot in self.slots if slot.path == path.id)

    def core_in_path(self, path: MethodPath) -> tuple[Slot, ...]:
        """The core slots of the path: the ones the reference curriculum
        counts (ADR 022 decision 2)."""
        return tuple(slot for slot in self.in_path(path) if not slot.extension)

    def extensions_in_path(self, path: MethodPath) -> tuple[Slot, ...]:
        return tuple(slot for slot in self.in_path(path) if slot.extension)

    @property
    def core(self) -> tuple[Slot, ...]:
        """The slots of the reference curriculum's counts: every slot but the
        extensions."""
        return tuple(slot for slot in self.slots if not slot.extension)


def _is_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


# The display titles of requirements decision 42; the keys are stable.
METHOD_PATHS = (
    ("reasoning", "Reliable scientific agents and experiment automation"),
    ("law-discovery", "Physical model discovery through active experiments"),
    ("benchmarking", "Scientific agent evaluation and improvement"),
    ("autonomous-research", "Reproducible research with agents"),
)


def curriculum_problems(data: object) -> list[str]:
    """Return every way the contents of the curriculum file are outside its
    schema: an unknown course or path, a duplicate label, a slot without a
    home or with two, and any field that belongs to a lesson's front matter."""
    if not isinstance(data, dict) or set(data) != {"courses", "paths", "slots"}:
        return [
            "the file holds the lists 'courses', 'paths', and 'slots', and nothing else"
        ]
    found: list[str] = []

    courses = data["courses"]
    expected = [{"id": course.id, "title": course.title} for course in COURSES]
    if courses != expected:
        found.append(
            "'courses' must list the eight courses of the site, with their"
            " identifiers and titles, in the order of COURSES"
        )

    path_ids: list[str] = []
    paths = data["paths"]
    if not isinstance(paths, list):
        found.append("'paths' must be a list")
        paths = []
    for item in paths:
        if (
            isinstance(item, dict)
            and set(item) == {"id", "title"}
            and isinstance(item["id"], str)
            and _PATH_ID.fullmatch(item["id"])
            and _is_text(item["title"])
        ):
            if item["id"] in path_ids:
                found.append(f"path {item['id']!r} is listed twice")
            path_ids.append(item["id"])
        else:
            found.append(f"path entry {item!r} must hold an 'id' and a 'title'")

    expected_paths = [{"id": id, "title": title} for id, title in METHOD_PATHS]
    if paths != expected_paths:
        found.append(
            "'paths' must list the four method paths, with their identifiers"
            " and titles, in the order of METHOD_PATHS"
        )

    slots = data["slots"]
    if not isinstance(slots, list):
        return [*found, "'slots' must be a list"]
    labels: set[str] = set()
    positions: dict[str, int] = {}
    extended: set[str] = set()  # the paths whose extension slots have begun
    for item in slots:
        if not isinstance(item, dict):
            found.append(f"slot entry {item!r} must be a mapping")
            continue
        name = repr(item.get("label"))
        for key in item:
            if key in _FRONT_MATTER_FIELDS:
                found.append(
                    f"slot {name}: {key!r} belongs to the front matter of a"
                    " lesson, not to the curriculum file"
                )
            elif key not in _SLOT_KEYS:
                found.append(f"slot {name}: {key!r} is not a field of a slot")
        label = item.get("label")
        if not (isinstance(label, str) and _LABEL.fullmatch(label)):
            found.append(f"slot {name}: 'label' must be a label such as M1 or AI0")
        elif label in labels:
            found.append(f"slot {name}: the label is used twice")
        else:
            labels.add(label)
        if not _is_text(item.get("title")):
            found.append(f"slot {name}: 'title' must be a text")
        if item.get("kind") not in KINDS:
            found.append(f"slot {name}: 'kind' must be one of {', '.join(KINDS)}")
        homes = [key for key in ("course", "path", "strand") if key in item]
        if not homes:
            found.append(f"slot {name} has no home: name a course, a path, or a strand")
        elif len(homes) > 1:
            found.append(f"slot {name} has more than one home: {' and '.join(homes)}")
        elif homes == ["course"]:
            if item["course"] not in _COURSE:
                found.append(
                    f"slot {name}: {item['course']!r} is not a course of the site"
                )
        elif homes == ["path"]:
            path_id = item["path"]
            if path_id not in path_ids:
                found.append(
                    f"slot {name}: {path_id!r} is not a path of the curriculum"
                )
            else:
                positions[path_id] = positions.get(path_id, 0) + 1
                if item.get("position") != positions[path_id]:
                    found.append(
                        f"slot {name}: 'position' must be {positions[path_id]},"
                        f" the number of the slot in the path"
                    )
        elif item["strand"] not in HOME_STRANDS:
            found.append(
                f"slot {name}: {item['strand']!r} is not a strand that homes a slot"
            )
        if homes != ["path"] and "position" in item:
            found.append(f"slot {name}: only a slot of a path has a 'position'")
        kind = item.get("kind")
        if kind == APPLIED_CAPSTONE and homes != ["course"]:
            found.append(f"slot {name}: an applied capstone is homed in a course")
        if kind == PRODUCT_CAPSTONE and homes != ["path"]:
            found.append(f"slot {name}: a product capstone is homed in a method path")
        if "extension" in item:
            if item["extension"] is not True:
                found.append(
                    f"slot {name}: 'extension' is true or absent, nothing else"
                )
            elif homes != ["path"]:
                found.append(
                    f"slot {name}: only a slot of a method path is an extension"
                )
            elif kind in CAPSTONES:
                found.append(f"slot {name}: a capstone is never an extension")
            else:
                extended.add(item["path"])
        elif homes == ["path"] and item["path"] in extended:
            found.append(
                f"slot {name}: a core slot of {item['path']!r} comes after its"
                " extension slots; the extensions are listed after the core"
            )
    return found


@dataclass(frozen=True)
class Problem:
    """One way the lessons fail to form a learning path."""

    page: str
    message: str


def _key(lesson: Lesson) -> tuple[int, int, str]:
    # Strands in their order, then the order within the strand. A strand the
    # site does not have sorts last; the lesson source checks report it.
    return (_STRAND_INDEX.get(lesson.strand, len(STRANDS)), lesson.order, lesson.page)


def problems(
    lessons: Sequence[Lesson], curriculum: Curriculum | None = None
) -> list[Problem]:
    """Return every violation of the rules that make the lessons a path:
    ids are unique, orders within a strand run from 1 without gaps or
    duplicates, prerequisites exist, a prerequisite in the same strand comes
    earlier in it (one in another strand may come later in the linear order,
    ADR 013 decision 8), the prerequisites form no cycle, and the course,
    slot, methods, outcomes, and related lessons follow the rules of the
    front matter. ``curriculum`` is the reference curriculum the slots name;
    without one, no slot exists."""
    curriculum = curriculum or Curriculum()
    ordered = sorted(lessons, key=_key)
    found: list[Problem] = []

    first_with_id: dict[str, Lesson] = {}
    for lesson in ordered:
        if lesson.id in first_with_id:
            found.append(
                Problem(
                    lesson.page,
                    f"lesson id '{lesson.id}' is already used by"
                    f" {first_with_id[lesson.id].page}",
                )
            )
        else:
            first_with_id[lesson.id] = lesson

    for strand in STRANDS:
        expected = 1
        first_with_order: dict[int, Lesson] = {}
        for lesson in (lesson for lesson in ordered if lesson.strand == strand.id):
            if lesson.order in first_with_order:
                found.append(
                    Problem(
                        lesson.page,
                        f"'lesson.order' {lesson.order} is already used by"
                        f" {first_with_order[lesson.order].page}",
                    )
                )
                continue
            first_with_order[lesson.order] = lesson
            if lesson.order != expected:
                found.append(
                    Problem(
                        lesson.page,
                        f"'lesson.order' is {lesson.order}, but strand"
                        f" '{strand.id}' has no lesson with order {expected}",
                    )
                )
            expected = lesson.order + 1

    # The first lesson with an id is the one a prerequisite refers to.
    position: dict[str, int] = {}
    for index, lesson in enumerate(ordered):
        position.setdefault(lesson.id, index)
    for index, lesson in enumerate(ordered):
        for prerequisite in lesson.prerequisites:
            if prerequisite not in position:
                found.append(
                    Problem(
                        lesson.page,
                        f"prerequisite '{prerequisite}' is not the id of any lesson",
                    )
                )
            elif (
                first_with_id[prerequisite].strand == lesson.strand
                and position[prerequisite] >= index
            ):
                found.append(
                    Problem(
                        lesson.page,
                        f"prerequisite '{prerequisite}' does not come earlier in"
                        f" its strand '{lesson.strand}'",
                    )
                )

    for lesson in ordered:
        found += [
            Problem(lesson.page, message) for message in _facets(lesson, position)
        ]
    found += _slot_problems(ordered, curriculum)

    graph = {
        lesson.id: tuple(p for p in lesson.prerequisites if p in position)
        for lesson in first_with_id.values()
    }
    for cycle in _cycles(graph, list(first_with_id)):
        found.append(
            Problem(
                first_with_id[cycle[0]].page,
                "prerequisites form a cycle: " + " -> ".join(cycle),
            )
        )
    return found


def _slot_problems(ordered: Sequence[Lesson], curriculum: Curriculum) -> list[Problem]:
    """What is wrong with the slots the lessons claim: the label is not in
    the curriculum, two lessons claim one slot, or a slot homed in a course
    is claimed by a lesson of another course (a slot of a method path or of
    the Lean strand may be filled by a lesson of any course)."""
    found: list[Problem] = []
    claimed: dict[str, Lesson] = {}
    for lesson in ordered:
        if not lesson.slot:
            continue
        slot = curriculum.slot(lesson.slot)
        if slot is None:
            found.append(
                Problem(
                    lesson.page,
                    f"'lesson.slot' {lesson.slot!r} is not a slot of the curriculum",
                )
            )
            continue
        if lesson.slot in claimed:
            found.append(
                Problem(
                    lesson.page,
                    f"slot '{lesson.slot}' is already filled by"
                    f" {claimed[lesson.slot].page}",
                )
            )
        else:
            claimed[lesson.slot] = lesson
        if slot.course and slot.course != lesson.course:
            found.append(
                Problem(
                    lesson.page,
                    f"slot '{slot.label}' is a slot of the course '{slot.course}',"
                    f" but 'lesson.course' is {lesson.course!r}",
                )
            )
    return found


def _facets(lesson: Lesson, position: dict[str, int]) -> list[str]:
    """What is wrong with the course, methods, outcomes, and related lessons
    of ``lesson``; ``position`` has the id of every lesson."""
    found = []
    if lesson.course not in _COURSE:
        found.append(f"'lesson.course' {lesson.course!r} is not a course of the site")
    if not lesson.methods:
        found.append("'lesson.methods' names no method")
    found += [
        f"'lesson.methods' names {method!r}, which is not a method of the site"
        for method in lesson.methods
        if method not in _METHOD
    ]
    if len(set(lesson.methods)) != len(lesson.methods):
        found.append("'lesson.methods' names a method twice")
    low, high = OUTCOMES_RANGE
    if not low <= len(lesson.outcomes) <= high:
        found.append(
            f"'lesson.outcomes' has {len(lesson.outcomes)} outcomes; a lesson"
            f" states {low} to {high}"
        )
    for related in lesson.related:
        if related == lesson.id:
            found.append("the lesson lists itself as related")
        elif related not in position:
            found.append(f"related lesson '{related}' is not the id of any lesson")
        elif related in lesson.prerequisites:
            found.append(
                f"related lesson '{related}' is already a prerequisite; a"
                " prerequisite is linked as one, not as related"
            )
    if len(set(lesson.related)) != len(lesson.related):
        found.append("'lesson.related' names a lesson twice")
    return found


def _cycles(graph: dict[str, tuple[str, ...]], order: list[str]) -> list[list[str]]:
    """Return one cycle per back edge of a depth-first search over the graph,
    each as the trail from the lesson reached again back to itself. A lesson is
    on the trail while it is being visited and done once all it needs is."""
    cycles: list[list[str]] = []
    done: set[str] = set()
    trail: list[str] = []

    def visit(node: str) -> None:
        trail.append(node)
        for following in graph.get(node, ()):
            if following in trail:
                cycles.append([*trail[trail.index(following) :], following])
            elif following not in done:
                visit(following)
        trail.pop()
        done.add(node)

    for start in order:
        if start not in done:
            visit(start)
    return cycles


@dataclass(frozen=True)
class LearningPath:
    """The lessons of a site in path order, validated."""

    lessons: tuple[Lesson, ...]
    curriculum: Curriculum = Curriculum()

    @classmethod
    def read(cls, site: Path) -> LearningPath:
        """Read the lessons of the website project ``site``.

        Raises ``ValueError`` when they do not form a path; the message lists
        every problem. The lesson source checks report the same problems.
        """
        lessons = read_lessons(site)
        curriculum = Curriculum.read(site)
        found = problems(lessons, curriculum)
        if found:
            raise ValueError(
                "the lessons do not form a learning path:\n"
                + "\n".join(f"  {problem.page}: {problem.message}" for problem in found)
            )
        return cls(tuple(sorted(lessons, key=_key)), curriculum)

    def lesson(self, lesson_id: str) -> Lesson:
        for lesson in self.lessons:
            if lesson.id == lesson_id:
                return lesson
        raise LookupError(f"no lesson has the id '{lesson_id}'")

    def at_page(self, page: str) -> Lesson:
        for lesson in self.lessons:
            if lesson.page == page:
                return lesson
        raise LookupError(f"{page} is not a lesson of the learning path")

    @property
    def strands(self) -> tuple[Strand, ...]:
        """The strands that have a lesson, in path order."""
        return tuple(strand for strand in STRANDS if self.in_strand(strand))

    def in_strand(self, strand: Strand) -> tuple[Lesson, ...]:
        return tuple(lesson for lesson in self.lessons if lesson.strand == strand.id)

    @property
    def courses(self) -> tuple[Course, ...]:
        """The courses that have a lesson, in the order of ``COURSES``."""
        return tuple(course for course in COURSES if self.in_course(course))

    def in_course(self, course: Course) -> tuple[Lesson, ...]:
        """The lessons of the course in teaching order: by the order in which
        the curriculum file lists their slots, then the lessons without a
        slot in linear order (ADR 013 decision 8)."""
        return self.taught(
            tuple(lesson for lesson in self.lessons if lesson.course == course.id)
        )

    def taught(self, lessons: Sequence[Lesson]) -> tuple[Lesson, ...]:
        """``lessons`` in teaching order; ``sorted`` is stable, so lessons
        without a slot keep the linear order."""

        def key(lesson: Lesson) -> tuple[int, int]:
            index = self.curriculum.index(lesson.slot) if lesson.slot else None
            return (0, index) if index is not None else (1, 0)

        return tuple(sorted(lessons, key=key))

    def filled(self) -> frozenset[str]:
        """The labels of the slots a published lesson fills."""
        return frozenset(lesson.slot for lesson in self.lessons if lesson.slot)

    def planned_in_course(self, course: Course) -> tuple[Slot, ...]:
        """The slots of the course that no published lesson fills."""
        filled = self.filled()
        return tuple(
            slot
            for slot in self.curriculum.in_course(course)
            if slot.label not in filled
        )

    @property
    def planned_courses(self) -> tuple[Course, ...]:
        """The courses that have no lesson yet: named, never shown as a
        course, and with no slot shown."""
        return tuple(course for course in COURSES if not self.in_course(course))

    @property
    def paths(self) -> tuple[MethodPath, ...]:
        """Every method path of the curriculum, with or without a lesson."""
        return self.curriculum.paths

    def in_path(self, path: MethodPath) -> tuple[Lesson, ...]:
        """The published lessons that fill a slot of the path, in the order
        of the slots."""
        homes = {slot.label for slot in self.curriculum.in_path(path)}
        return self.taught(
            tuple(lesson for lesson in self.lessons if lesson.slot in homes)
        )

    def planned_in_path(self, path: MethodPath) -> tuple[Slot, ...]:
        filled = self.filled()
        return tuple(
            slot for slot in self.curriculum.in_path(path) if slot.label not in filled
        )

    def slot_of(self, lesson: Lesson) -> Slot | None:
        return self.curriculum.slot(lesson.slot) if lesson.slot else None

    @property
    def methods(self) -> tuple[Method, ...]:
        """The methods that have a lesson, in the order of ``METHODS``."""
        return tuple(method for method in METHODS if self.using(method))

    def using(self, method: Method) -> tuple[Lesson, ...]:
        return tuple(lesson for lesson in self.lessons if method.id in lesson.methods)

    def previous(self, lesson: Lesson) -> Lesson | None:
        index = self.lessons.index(lesson)
        return self.lessons[index - 1] if index > 0 else None

    def next(self, lesson: Lesson) -> Lesson | None:
        index = self.lessons.index(lesson)
        return self.lessons[index + 1] if index + 1 < len(self.lessons) else None


# --- Reading ------------------------------------------------------------------

_FRONT_MATTER = re.compile(r"\A---\n(.*?\n)(?:---|\.\.\.)[ \t]*\n", re.DOTALL)


def read_lessons(site: Path) -> list[Lesson]:
    """Read the front matter of every lesson of the website project ``site``."""
    pages = sorted((site / LESSONS_DIRECTORY).glob(f"*/*/{PAGE_FILE}"))
    return [_read(site, page) for page in pages]


def _texts(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise TypeError("not a list")
    return tuple(str(item) for item in value)


def _read(site: Path, page: Path) -> Lesson:
    name = page.relative_to(site).as_posix()
    match = _FRONT_MATTER.match(page.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError(f"{name} has no YAML front matter")
    try:
        front_matter = yaml.safe_load(match.group(1))
        meta = front_matter["lesson"]
        prerequisites = meta["prerequisites"]
        lesson = Lesson(
            page=name,
            id=str(meta["id"]),
            title=str(front_matter["title"]),
            description=str(front_matter.get("description") or "").strip(),
            strand=str(meta["strand"]),
            order=int(meta["order"]),
            difficulty=int(meta["difficulty"]),
            prerequisites=tuple(str(item) for item in prerequisites["lessons"]),
            outside=tuple(str(item) for item in prerequisites["outside"]),
            course=str(meta["course"]),
            methods=_texts(meta["methods"]),
            outcomes=_texts(meta["outcomes"]),
            related=_texts(meta["related"]),
            slot=str(meta.get("slot") or ""),
            preview=str(meta.get("preview") or ""),
        )
    except yaml.YAMLError, KeyError, TypeError, ValueError:
        raise ValueError(
            f"the front matter of {name} does not follow the lesson format;"
            " the lesson source checks (tests/lessons) say what is wrong"
        ) from None
    if lesson.strand not in _STRAND_INDEX:
        raise ValueError(f"{name}: '{lesson.strand}' is not a strand of the site")
    if lesson.difficulty not in _DIFFICULTY:
        raise ValueError(
            f"{name}: difficulty {lesson.difficulty} is not on the scale of the site"
        )
    return lesson


# --- Rendering ----------------------------------------------------------------


def _link(from_page: str, lesson: Lesson) -> str:
    return f"[{lesson.title}]({_href(from_page, lesson.page)})"


def _level(lesson: Lesson) -> str:
    difficulty = _DIFFICULTY[lesson.difficulty]
    return f"{difficulty.title}, level {difficulty.level} of {len(DIFFICULTIES)}"


def _prerequisites(
    path: LearningPath, from_page: str, lesson: Lesson, outside: bool = True
) -> str:
    links = [_link(from_page, path.lesson(item)) for item in lesson.prerequisites]
    text = ", ".join(links) if links else "none on this site"
    if outside and lesson.outside:
        text += ". Also assumed: " + "; ".join(lesson.outside)
    return text + "."


def _course_id(course: Course) -> str:
    return f"course-{course.id}"


def _method_id(method: Method) -> str:
    return f"method-{method.id}"


def _path_id(path: MethodPath) -> str:
    return f"path-{path.id}"


def _slot_fact(path: LearningPath, from_page: str, lesson: Lesson) -> str | None:
    """The slot a lesson fills and, for a slot of a method path, the position
    in the path, as Markdown; ``None`` for a lesson without a slot."""
    slot = path.slot_of(lesson)
    if slot is None:
        return None
    if slot.path:
        method_path = path.curriculum.path(slot.path)
        link = (
            f"[{method_path.title}]"
            f"({_href(from_page, PATH_PAGE, _path_id(method_path))})"
        )
        if slot.extension:
            # Optional depth: no number among the core slots (ADR 022).
            return f"{slot.label}, an optional extension of the path {link}"
        length = len(path.curriculum.core_in_path(method_path))
        return (
            f"{slot.label}, number {slot.position} of the {length} slots of the"
            f" path {link}"
        )
    return f"{slot.label}, {slot.title}"


@dataclass(frozen=True)
class LessonHeader:
    """The header of a lesson page: course and position, methods,
    difficulty, outcomes, prerequisites, related lessons, and the previous
    and next lesson.

    As the result of a code cell it leaves a marker; the page the reader gets
    shows a list of those facts, with links, built after the render from the
    front matter of every lesson (``pbc.authoring.context``).
    """

    path: LearningPath
    lesson: Lesson
    # With a glossary, the outside prerequisites are a "Before you begin"
    # list that links each to its entry; without, they end the Prerequisites.
    glossary: Glossary | None = None
    # The conceptual connections and capstone memberships of the lesson's
    # concept, from the atlas manifest (pbc.authoring.atlas.connections), as
    # Markdown items; none for a lesson without them.
    connections: tuple[str, ...] = ()
    # The sequences that have an introduction (F156): the course and the path
    # of the lesson link to it.
    introductions: frozenset[str] = frozenset()

    @classmethod
    def from_payload(cls, site: Path, page: str, payload: dict) -> LessonHeader:
        """The header of the lesson ``page`` of the site project at ``site``."""
        # The atlas reads this module; imported here, there is no cycle.
        from pbc.authoring.atlas import Atlas, AtlasManifest, connections

        if payload:
            raise ValueError("a header marker holds no facts")
        path = LearningPath.read(site)
        lesson = path.at_page(page)
        atlas = Atlas(path, AtlasManifest.read(site, path.curriculum))
        return cls(
            path,
            lesson,
            Glossary.read(site),
            tuple(connections(atlas, lesson, page)),
            introduced(site),
        )

    def _repr_markdown_(self) -> str:
        return marker("header", self.lesson.page, {})

    def markdown(self) -> str:
        """The content of the header, from the lessons as they are now."""
        path, lesson, page = self.path, self.lesson, self.lesson.page
        course = _COURSE[lesson.course]
        in_course = path.in_course(course)
        course_link = f"[{course.title}]({_href(page, PATH_PAGE, _course_id(course))})"
        position = f"lesson {in_course.index(lesson) + 1} of {len(in_course)}"
        methods = ", ".join(
            f"[{_METHOD[method].title}]"
            f"({_href(page, PATH_PAGE, _method_id(_METHOD[method]))})"
            for method in lesson.methods
        )
        level = f"[{_level(lesson)}]({_href(page, PATH_PAGE, 'difficulty')})"
        outcomes = "\n".join(f"    - {outcome}" for outcome in lesson.outcomes)
        related = (
            ", ".join(_link(page, path.lesson(item)) for item in lesson.related)
            if lesson.related
            else "none"
        )
        previous = path.previous(lesson)
        following = path.next(lesson)
        slot = _slot_fact(path, page, lesson)
        rows = [
            ("Course", f"{course_link}, {position}"),
            *([("Slot", slot)] if slot else []),
            *self._introductions(),
            ("Methods", methods),
            ("Difficulty", level),
            ("What you'll learn", "\n" + outcomes),
            (
                "Prerequisites",
                _prerequisites(path, page, lesson, outside=self.glossary is None),
            ),
            *self._before_you_begin(),
            ("Related", related),
            *self._connections(),
            (
                "Previous",
                _link(page, previous)
                if previous
                else "none; this is the first lesson of the"
                f" [learning path]({_href(page, PATH_PAGE, 'order')})",
            ),
            (
                "Next",
                _link(page, following)
                if following
                else "none yet; this is the last lesson of the"
                f" [learning path]({_href(page, PATH_PAGE, 'order')}) so far",
            ),
        ]
        header = (
            "::: {.lesson-header}\n"
            + "\n".join(f"{term}\n:   {definition}\n" for term, definition in rows)
            + ":::\n"
        )
        # The script that keeps the learner's progress in the browser.
        return header + raw_html(progress_markup(page, lesson, path))

    def _introductions(self) -> list[tuple[str, str]]:
        """The introductions of the lesson's course and, when it fills a slot
        of a method path, of that path, as links by the sequence's name; none
        for a lesson whose sequences have no introduction (F156)."""
        page = self.lesson.page
        found = [(_COURSE[self.lesson.course].id, _COURSE[self.lesson.course].title)]
        slot = self.path.slot_of(self.lesson)
        if slot is not None and slot.path:
            method_path = self.path.curriculum.path(slot.path)
            found.append((method_path.id, method_path.title))
        links = [
            f"[{title}]({_href(page, introduction_page(sequence_id))})"
            for sequence_id, title in found
            if sequence_id in self.introductions
        ]
        return [("Introduction", ", ".join(links))] if links else []

    def _connections(self) -> list[tuple[str, str]]:
        if not self.connections:
            return []
        items = "\n".join(f"    - {item}" for item in self.connections)
        return [("Connections", "\n" + items)]

    def _before_you_begin(self) -> list[tuple[str, str]]:
        if self.glossary is None:
            return []
        if not self.lesson.outside:
            return [("Before you begin", "nothing beyond the prerequisites above.")]
        items = before_you_begin(self.lesson.page, self.glossary, self.lesson.outside)
        shown = "\n" + _indent(items, 4)
        # The definitions on demand, after the list (F135).
        extra = definitions(self.glossary, self.lesson.outside)
        if extra:
            shown += "\n\n" + _indent(extra, 4)
        return [("Before you begin", shown)]


@dataclass(frozen=True)
class PathOverview:
    """The content of the learning path page under the atlas's sequences
    (``pbc.authoring.atlas``): what the lesson pages link to on it (the
    difficulty scale, the methods, the three orders) and the learner's
    progress with its explanation, its control, and the recommendations.
    The lessons themselves are listed once, in the sequences (F133).

    Print it from a cell with ``output: asis``, so that the sections are
    part of the page and its table of contents; as a cell result they would
    sit inside the output of the cell.
    """

    path: LearningPath
    page: str  # the page it is rendered on, relative to the website project
    site: Path | None = None

    def __str__(self) -> str:
        lines: list[str] = []
        if not self.path.lessons:
            lines += ["No lesson has been published yet.", ""]
        lines += self._progress()
        lines += [
            "## How the lessons work {#about-the-lessons}",
            "",
            "Every lesson states its level and the methods it uses, and names"
            " the lessons it builds on.",
            "",
        ]
        lines += self._difficulty()
        lines += self._methods()
        lines += self._order()
        # The script that shows progress on the rows and clears it, with the
        # learning path the recommendations are computed from.
        lines += [raw_html(progress_markup(self.page, None, self.path))]
        return "\n".join(lines)

    def _methods(self) -> list[str]:
        """What each method means, one line per method; a lesson's header
        links its methods here. The lessons are in the sequences above, not
        listed again."""
        items = "".join(
            f'<li id="{_method_id(method)}"><span class="method-name">'
            f"{escape(method.title)}</span> {escape(method.description)}</li>"
            for method in METHODS
        )
        return [
            "### Methods {#methods}",
            "",
            "A method is a way of working that cuts across courses; a lesson's"
            " header names the methods it uses.",
            "",
            raw_html(f'<ul class="atlas-methods">{items}</ul>'),
        ]

    def _difficulty(self) -> list[str]:
        """The scale in one sentence, its descriptions in a closed native
        disclosure."""
        names = [difficulty.title for difficulty in DIFFICULTIES]
        levels = "".join(
            f"<dt>{escape(difficulty.title)}</dt>"
            f"<dd>{escape(difficulty.description)}</dd>"
            for difficulty in DIFFICULTIES
        )
        return [
            "### Difficulty {#difficulty}",
            "",
            f"Every lesson states one of {len(DIFFICULTIES)} levels,"
            f" {', '.join(names[:-1])}, or {names[-1]}, shown beside its title"
            " in the lists above.",
            "",
            raw_html(
                '<details class="atlas-note" id="difficulty-levels">'
                "<summary>What the levels mean</summary>"
                f'<dl class="atlas-levels">{levels}</dl></details>'
            ),
        ]

    def _progress(self) -> list[str]:
        """The section with the owner's sentence (the script replaces it by
        the count, the completed lessons, and the clear-data control), and
        the explanation of what the site stores in the browser, in a closed
        native disclosure."""
        return [
            f"## Your progress {{#{EXPLANATION_ANCHOR}}}",
            "",
            raw_html(
                '<div id="progress-controls" data-enhancement="">'
                f"<p>{escape(PROGRESS_SENTENCE)}</p></div>"
                '<details class="atlas-note" id="progress-details">'
                "<summary>What is stored, and how to clear it</summary>"
                "<p>With scripts, this site keeps in your browser and nowhere"
                " else, in local storage under the key"
                f" <code>{STORAGE_KEY}</code>, which lessons you marked"
                " completed, whether you finished a self-check and how often"
                " you checked an answer, and which suggestions you ignored. No"
                " account is needed; nothing is sent to a server, no cookie is"
                " set, and nothing is shared with other sites or other"
                " devices. The button that clears it is shown with scripts, and"
                " clearing the data of this site in your browser removes it"
                " too.</p>"
                "<p>Without scripts nothing is stored, and the self-checks work"
                " as exercises with a solution you can open.</p></details>"
            ),
            raw_html(recommendations_markup()),
        ]

    def _order(self) -> list[str]:
        return [
            "### Lesson order and prerequisites {#order}",
            "",
            "Each course and method path has a recommended teaching order, the"
            " order of its lessons above. Every lesson names in its header the"
            " lessons it builds on, and those are all you need first; the"
            " related lessons it lists offer further exploration.",
            "",
            "Previous and next at the foot of a lesson follow the site's one"
            " linear order, which is not the order of the prerequisites: a"
            " lesson may build on one that comes later, so the header is the"
            " guide to what to read first.",
            "",
        ]


def _indent(text: str, width: int) -> str:
    return "\n".join(" " * width + line for line in text.splitlines())


def _page_being_built() -> tuple[Path, str]:
    """Return the website project and the page of the cell that is running."""
    directory = Path.cwd().resolve()
    site = project_root(directory)
    return site, f"{directory.relative_to(site).as_posix()}/{PAGE_FILE}"


def lesson_header() -> LessonHeader:
    """Return the header of the lesson page being built.

    Call it from the first cell of a lesson's ``index.qmd``; the lesson is
    the one in the directory the cell runs in.
    """
    site, page = _page_being_built()
    path = LearningPath.read(site)
    return LessonHeader(path, path.at_page(page), Glossary.read(site))


def learning_path() -> PathOverview:
    """Return the content of the learning path page being built."""
    site, page = _page_being_built()
    return PathOverview(LearningPath.read(site), page, site)
