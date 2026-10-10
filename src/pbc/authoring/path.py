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

from pbc.authoring.glossary import Glossary, before_you_begin
from pbc.authoring.graph import (
    RELATED_MARKER,
    REQUIRES,
    REQUIRES_MARKER,
    PrerequisiteGraph,
)
from pbc.authoring.website import PAGE_FILE, page_href, project_root

_href = page_href

# Where the lessons and the learning path page sit in the website project.
LESSONS_DIRECTORY = "lessons"
PATH_PAGE = "path/index.qmd"


@dataclass(frozen=True)
class Strand:
    id: str
    title: str
    description: str


# The strands in learning path order (docs/architecture.md, "Lesson model").
STRANDS = (
    Strand(
        "mechanics",
        "Mechanics",
        "Mechanics with numerical simulation: a model and its assumptions, a"
        " short program that steps it forward in time, and a comparison with"
        " what theory predicts.",
    ),
    Strand(
        "agents-llm",
        "LLM agents",
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
class Course:
    id: str
    title: str
    description: str


# The courses of the site (ADR 008). A lesson belongs to one primary course;
# a course appears on the learning path page once it has a lesson.
COURSES = (
    Course(
        "mechanics",
        "Mechanics",
        "Mechanics with numerical simulation: a model and its assumptions, a"
        " short program that steps it forward in time, and a comparison with"
        " what theory predicts. The core lessons are the mechanics lessons;"
        " the extensions repeat the course's results with an agent, with"
        " many agents, and with a proof.",
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


@dataclass(frozen=True)
class Problem:
    """One way the lessons fail to form a learning path."""

    page: str
    message: str


def _key(lesson: Lesson) -> tuple[int, int, str]:
    # Strands in their order, then the order within the strand. A strand the
    # site does not have sorts last; the lesson source checks report it.
    return (_STRAND_INDEX.get(lesson.strand, len(STRANDS)), lesson.order, lesson.page)


def problems(lessons: Sequence[Lesson]) -> list[Problem]:
    """Return every violation of the rules that make the lessons a path:
    ids are unique, orders within a strand run from 1 without gaps or
    duplicates, prerequisites exist, come earlier in the path, and form no
    cycle, and the course, methods, outcomes, and related lessons follow
    the rules of the front matter."""
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
            elif position[prerequisite] >= index:
                found.append(
                    Problem(
                        lesson.page,
                        f"prerequisite '{prerequisite}' does not come earlier in"
                        " the learning path",
                    )
                )

    for lesson in ordered:
        found += [
            Problem(lesson.page, message) for message in _facets(lesson, position)
        ]

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
    """Return one cycle per set of lessons that depend on each other, each
    starting at its first member in ``order``."""
    cycles: list[list[str]] = []
    reported: set[str] = set()
    for start in order:
        if start in reported:
            continue
        stack = [(start, [start])]
        seen = {start}
        while stack:
            node, trail = stack.pop()
            for following in graph.get(node, ()):
                if following == start:
                    cycles.append([*trail, start])
                    reported.update(trail)
                    stack.clear()
                    break
                if following not in seen:
                    seen.add(following)
                    stack.append((following, [*trail, following]))
    return cycles


@dataclass(frozen=True)
class LearningPath:
    """The lessons of a site in path order, validated."""

    lessons: tuple[Lesson, ...]

    @classmethod
    def read(cls, site: Path) -> LearningPath:
        """Read the lessons of the website project ``site``.

        Raises ``ValueError`` when they do not form a path; the message lists
        every problem. The lesson source checks report the same problems.
        """
        lessons = read_lessons(site)
        found = problems(lessons)
        if found:
            raise ValueError(
                "the lessons do not form a learning path:\n"
                + "\n".join(f"  {problem.page}: {problem.message}" for problem in found)
            )
        return cls(tuple(sorted(lessons, key=_key)))

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
        return tuple(lesson for lesson in self.lessons if lesson.course == course.id)

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


@dataclass(frozen=True)
class LessonHeader:
    """The header of a lesson page: course and position, methods,
    difficulty, outcomes, prerequisites, related lessons, and the previous
    and next lesson.

    As the result of a code cell it renders as a list of those facts, with
    links.
    """

    path: LearningPath
    lesson: Lesson
    # With a glossary, the outside prerequisites are a "Before you begin"
    # list that links each to its entry; without, they end the Prerequisites.
    glossary: Glossary | None = None

    def _repr_markdown_(self) -> str:
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
        rows = [
            ("Course", f"{course_link}, {position}"),
            ("Methods", methods),
            ("Difficulty", level),
            ("What you'll learn", "\n" + outcomes),
            (
                "Prerequisites",
                _prerequisites(path, page, lesson, outside=self.glossary is None),
            ),
            *self._before_you_begin(),
            ("Related", related),
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
        return (
            "::: {.lesson-header}\n"
            + "\n".join(f"{term}\n:   {definition}\n" for term, definition in rows)
            + ":::\n"
        )

    def _before_you_begin(self) -> list[tuple[str, str]]:
        if self.glossary is None:
            return []
        if not self.lesson.outside:
            return [("Before you begin", "nothing beyond the prerequisites above.")]
        items = before_you_begin(self.lesson.page, self.glossary, self.lesson.outside)
        return [("Before you begin", "\n" + _indent(items, 4))]


@dataclass(frozen=True)
class PathOverview:
    """The content of the learning path page: the difficulty scale, what
    previous and next mean, every course that has a lesson with its core
    lessons and extensions, and one path per method, as Markdown with a
    section per course and per method.

    Print it from a cell with ``output: asis``, so that the sections are
    part of the page and its table of contents; as a cell result they would
    sit inside the output of the cell.
    """

    path: LearningPath
    page: str  # the page it is rendered on, relative to the website project

    def __str__(self) -> str:
        lines = [
            "## Difficulty {#difficulty}",
            "",
            f"Every lesson states one of {len(DIFFICULTIES)} levels.",
            "",
        ]
        for difficulty in DIFFICULTIES:
            lines += [
                f"{difficulty.level}, {difficulty.title.lower()}",
                f":   {difficulty.description}",
                "",
            ]
        lines += self._order()
        if not self.path.lessons:
            lines += ["No lesson has been published yet.", ""]
        if self.path.courses:
            lines += [
                "## Courses {#courses}",
                "",
                "A lesson belongs to one course. The core lessons of a course"
                " are the lessons of its own strand, in order; its extensions"
                " are lessons of other strands that repeat its results with"
                " another method.",
                "",
            ]
        for course in self.path.courses:
            lines += [
                f"### {course.title} {{#{_course_id(course)}}}",
                "",
                course.description,
                "",
            ]
            lessons = self.path.in_course(course)
            core = [lesson for lesson in lessons if lesson.strand == course.id]
            extensions = [lesson for lesson in lessons if lesson.strand != course.id]
            for title, group in (("Core lessons", core), ("Extensions", extensions)):
                if group:
                    anchor = f"{_course_id(course)}-{title.split()[0].lower()}"
                    lines += [
                        f"#### {title} {{#{anchor}}}",
                        "",
                    ]
                    lines += self._items(group, 5)
        if self.path.methods:
            lines += [
                "## Methods {#methods}",
                "",
                "A method is a way of working that cuts across courses. Each"
                " path lists the lessons that use the method, in the order of"
                " the learning path.",
                "",
            ]
        for method in self.path.methods:
            lines += [
                f"### {method.title} {{#{_method_id(method)}}}",
                "",
                method.description,
                "",
            ]
            lines += self._items(self.path.using(method), 4)
        lines += self._graph()
        return "\n".join(lines)

    def _graph(self) -> list[str]:
        if not self.path.lessons:
            return []
        graph = PrerequisiteGraph.layout(self.path.lessons, self.path.courses)
        requires = sum(1 for edge in graph.edges if edge.kind == REQUIRES)
        related = len(graph.edges) - requires
        summary = (
            f"{len(graph.nodes)} lessons in {len(graph.bands)} course"
            f"{'s' if len(graph.bands) != 1 else ''}, with {requires}"
            f" prerequisite and {related} related"
            f" link{'s' if related != 1 else ''}. Arrows point from a"
            " prerequisite to the lesson that requires it, and from a lesson"
            " to a related lesson it recommends. The edges are listed as"
            " sentences after the drawing."
        )
        drawing = graph.svg(lambda lesson: _href(self.page, lesson.page), summary)
        sentences = "\n".join(f"<li>{escape(text)}.</li>" for text in graph.sentences())
        return [
            "## Prerequisite graph {#graph}",
            "",
            "The graph shows the same prerequisites as the lists above, as a"
            " picture. Each box is a lesson and links to it. A lesson stands"
            " one column to the right of its furthest prerequisite, and the"
            " lessons of a course share a band. On a narrow screen the lists"
            " above are the way to read the path; the graph scrolls sideways"
            " inside its box.",
            "",
            "```{=html}",
            '<ul class="graph-legend">',
            '<li><svg aria-hidden="true" width="56" height="14" viewBox="0 0 56 14">'
            '<path class="edge-requires" d="M2,7 L52,7"'
            f' marker-end="url(#{REQUIRES_MARKER})"/></svg>'
            " <strong>Requires</strong>: a solid line with a filled arrowhead,"
            " from a prerequisite to the lesson that needs it.</li>",
            '<li><svg aria-hidden="true" width="56" height="14" viewBox="0 0 56 14">'
            '<path class="edge-related" d="M2,7 L52,7"'
            f' marker-end="url(#{RELATED_MARKER})"/></svg>'
            " <strong>Related</strong>: a dashed line with an open arrowhead,"
            " from a lesson to a lesson it recommends as an extension; not"
            " required.</li>",
            "</ul>",
            '<div class="prerequisite-graph" tabindex="0" role="region"'
            ' aria-label="Prerequisite graph, scrolls sideways">',
            drawing,
            "</div>",
            '<ol class="visually-hidden" aria-label="The edges of the'
            ' prerequisite graph">',
            sentences,
            "</ol>",
            "```",
            "",
        ]

    def _order(self) -> list[str]:
        strands = ", then ".join(strand.title for strand in self.path.strands)
        return [
            "## Order {#order}",
            "",
            "Three orders are in use, and they are not the same.",
            "",
            "Previous and next on a lesson page follow the one linear order of the"
            " site: the strands one after the other"
            + (f" ({strands})" if strands else "")
            + ", and within a strand the lessons by their number. Following"
            " next from the last lesson of one strand leads to the first lesson"
            " of the following strand, which may belong to another course.",
            "",
            "The course order is the order of the lessons of one course in this"
            " linear order, as listed below. Its extensions come after its core"
            " lessons because their strands come after.",
            "",
            "The prerequisites of a lesson are the lessons it builds on, and"
            " are the only statement of what you need first. A lesson may"
            " precede others in the linear order without being a prerequisite"
            " of them.",
            "",
        ]

    def _items(self, lessons: Sequence[Lesson], heading: int) -> list[str]:
        """The lessons as cards (``ul.path-cards`` of ``li.path-card``, the
        F44 component): a heading of the given depth, the description, and
        the facts of the lesson as plain terms and lists."""
        cards = [self._card(lesson, heading) for lesson in lessons]
        return ["```{=html}", '<ul class="path-cards">', *cards, "</ul>", "```", ""]

    def _card(self, lesson: Lesson, heading: int) -> str:
        page, path = self.page, self.path

        def link(to_page: str, text: str, fragment: str = "", title: str = "") -> str:
            tip = f' title="{escape(title)}"' if title else ""
            href = escape(_href(page, to_page, fragment))
            return f'<a href="{href}"{tip}>{escape(text)}</a>'

        def lesson_link(item: str) -> str:
            other = path.lesson(item)
            return link(other.page, other.title)

        course = _COURSE[lesson.course]
        difficulty = _DIFFICULTY[lesson.difficulty]
        methods = ", ".join(
            link(PATH_PAGE, _METHOD[m].title, _method_id(_METHOD[m]))
            for m in lesson.methods
        )
        # The title of the link is the definition of the level, shown on
        # hover; the legend states it in text.
        level = link(PATH_PAGE, _level(lesson), "difficulty", difficulty.description)
        outcomes = "".join(f"<li>{escape(outcome)}</li>" for outcome in lesson.outcomes)
        prerequisites = (
            ", ".join(lesson_link(item) for item in lesson.prerequisites)
            if lesson.prerequisites
            else "none on this site"
        )
        if lesson.outside:
            prerequisites += ". Also assumed: " + escape("; ".join(lesson.outside))
        related = (
            ", ".join(lesson_link(item) for item in lesson.related)
            if lesson.related
            else "none"
        )
        rows = [
            ("Course", link(PATH_PAGE, course.title, _course_id(course))),
            ("Methods", methods),
            ("Level", level),
            ("What you\u2019ll learn", f"<ul>{outcomes}</ul>"),
            ("Prerequisites", prerequisites + "."),
            ("Related", related),
        ]
        facts = "".join(f"<dt>{term}</dt><dd>{value}</dd>" for term, value in rows)
        description = (
            f"<p>{escape(lesson.description)}</p>" if lesson.description else ""
        )
        return (
            f'<li class="path-card"><h{heading} class="lesson-card-title">'
            f"{link(lesson.page, lesson.title)}</h{heading}>{description}"
            f"<dl>{facts}</dl></li>"
        )


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
    return PathOverview(LearningPath.read(site), page)
