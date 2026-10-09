"""The learning path: every lesson of the site in order.

The path is derived from the front matter of the lessons when a page is
built; there is no second, hand-maintained list (docs/architecture.md,
"Lesson model"). This module defines the strands and the one difficulty
scale of the site, reads the lessons, puts them in order, validates the
result, and renders the learning path page and the header of a lesson. The
lesson source checks validate with the same code.
"""

import posixpath
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import yaml

from pbc.authoring.website import PAGE_FILE, project_root

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

_STRAND_INDEX = {strand.id: index for index, strand in enumerate(STRANDS)}
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
    cycle."""
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


def _href(from_page: str, to_page: str, fragment: str = "") -> str:
    """A relative link from the built ``from_page`` to the built ``to_page``."""
    target = PurePosixPath(to_page).with_suffix(".html").as_posix()
    href = posixpath.relpath(target, PurePosixPath(from_page).parent.as_posix())
    return f"{href}#{fragment}" if fragment else href


def _link(from_page: str, lesson: Lesson) -> str:
    return f"[{lesson.title}]({_href(from_page, lesson.page)})"


def _level(lesson: Lesson) -> str:
    difficulty = _DIFFICULTY[lesson.difficulty]
    return f"{difficulty.title}, level {difficulty.level} of {len(DIFFICULTIES)}"


def _prerequisites(path: LearningPath, from_page: str, lesson: Lesson) -> str:
    links = [_link(from_page, path.lesson(item)) for item in lesson.prerequisites]
    text = ", ".join(links) if links else "none on this site"
    if lesson.outside:
        text += ". Also assumed: " + "; ".join(lesson.outside)
    return text + "."


@dataclass(frozen=True)
class LessonHeader:
    """The header of a lesson page: strand, position, difficulty,
    prerequisites, and the previous and next lesson.

    As the result of a code cell it renders as a list of those facts, with
    links.
    """

    path: LearningPath
    lesson: Lesson

    def _repr_markdown_(self) -> str:
        path, lesson, page = self.path, self.lesson, self.lesson.page
        strand = STRANDS[_STRAND_INDEX[lesson.strand]]
        in_strand = path.in_strand(strand)
        strand_link = f"[{strand.title}]({_href(page, PATH_PAGE, strand.id)})"
        position = f"lesson {in_strand.index(lesson) + 1} of {len(in_strand)}"
        level = f"[{_level(lesson)}]({_href(page, PATH_PAGE, 'difficulty')})"
        previous = path.previous(lesson)
        following = path.next(lesson)
        rows = [
            ("Strand", f"{strand_link}, {position}"),
            ("Difficulty", level),
            ("Prerequisites", _prerequisites(path, page, lesson)),
            (
                "Previous",
                _link(page, previous)
                if previous
                else "none; this is the first lesson of the"
                f" [learning path]({_href(page, PATH_PAGE)})",
            ),
            (
                "Next",
                _link(page, following)
                if following
                else "none yet; this is the last lesson of the"
                f" [learning path]({_href(page, PATH_PAGE)}) so far",
            ),
        ]
        return (
            "::: {.lesson-header}\n"
            + "\n".join(f"{term}\n:   {definition}\n" for term, definition in rows)
            + ":::\n"
        )


@dataclass(frozen=True)
class PathOverview:
    """The content of the learning path page: the difficulty scale and, for
    every strand that has a lesson, its lessons in order, as Markdown with
    a section per strand.

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
        if not self.path.lessons:
            lines += ["No lesson has been published yet.", ""]
        for strand in self.path.strands:
            lines += [f"## {strand.title} {{#{strand.id}}}", "", strand.description, ""]
            for number, lesson in enumerate(self.path.in_strand(strand), start=1):
                marker = f"{number}. "
                lines.append(marker + _link(self.page, lesson))
                paragraphs = [lesson.description] if lesson.description else []
                paragraphs.append(
                    f"{_level(lesson)}. Prerequisites:"
                    f" {_prerequisites(self.path, self.page, lesson)}"
                )
                for paragraph in paragraphs:
                    # A paragraph belongs to the item when every line of it
                    # is indented to where the item's text starts, so the
                    # indent follows the width of the marker ("10. " is
                    # wider than "1. ").
                    lines += ["", _indent(paragraph, len(marker))]
                lines.append("")
        return "\n".join(lines)


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
    return LessonHeader(path, path.at_page(page))


def learning_path() -> PathOverview:
    """Return the content of the learning path page being built."""
    site, page = _page_being_built()
    return PathOverview(LearningPath.read(site), page)
