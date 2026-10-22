"""The generated parts of the home page: the examples, Part A and Part B, the
capstone projects, the invitation, and the provenance of the opening figure.

What the home page says is published comes from the lesson front matter, read
with the same code as the learning path, so a number or a title on the home
page cannot differ from the lessons. What is planned comes from the
curriculum file (``site/curriculum.yaml``, ADR 013): the eight courses of
Part A and the four method paths of Part B with their published and planned
counts. A capstone project is described by the explanation of its concept in
the map manifest (``site/atlas.yaml``, ADR 018 decision 3), the one place that
text lives. A planned item is labelled planned and is never a link.

The composition is the owner's (Issue #238, 2026-10-21): three courses are
featured with the course illustrations of the atlas, the other five follow in
a compact row; Part B is a second layer under the editorial heading
"Physics + AI"; one capstone is featured on the dark navy ground with an
editorial heading and the conceptual artwork of ``pbc.authoring.home_artwork``,
the other two follow smaller. The editorial headings are kept apart from the
manifest's explanations.
"""

import posixpath
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from pbc.authoring import home_artwork
from pbc.authoring.atlas import CAPSTONE, ILLUSTRATION, ILLUSTRATIONS, AtlasManifest
from pbc.authoring.path import (
    COURSES,
    Course,
    LearningPath,
    Lesson,
    MethodPath,
    Slot,
    _href,
    _link,
)
from pbc.authoring.repository import BuildCommit, build_commit, repository_url
from pbc.authoring.website import PAGE_FILE, project_root

HOME_PAGE = PAGE_FILE
PATH_PAGE = "path/index.qmd"

# The one published lesson that each activity points to, by lesson id.
CONSTRUCT_EXAMPLE = "numerical-integrators"
INVESTIGATE_EXAMPLE = "agent-experiment"
VERIFY_EXAMPLE = "proving-what-the-simulation-showed"

# The module that draws the opening figure, and its file in the repository.
OPENING_MODULE = "pbc.mechanics.experiments.home_opening"
OPENING_SOURCE = "src/pbc/mechanics/experiments/home_opening.py"
OPENING_LESSON = "double-pendulum-chaos"

# The courses featured with their illustrations, and the capstone featured on
# the dark ground with its editorial heading (the owner's decisions 2 and 3).
FEATURED_COURSES = ("mechanics", "thermodynamics", "waves")
FEATURED_CAPSTONE = "FL10"
FEATURED_HEADING = "Model a wave. Understand a coastline."
ARTWORK_LABEL = (
    "Conceptual artwork for a planned capstone, drawn by code: it shows no"
    " data and no simulation."
)

_WORDS = (
    "no",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
)


def _word(number: int) -> str:
    """A small number in words, as running text writes it."""
    return _WORDS[number] if number < len(_WORDS) else str(number)


def _scientific(text: str) -> str:
    """A number written as ``8e-08`` in the Markdown of 8 times ten to the
    power minus 8, with a superscript exponent."""
    mantissa, _, exponent = text.partition("e")
    if not exponent:
        return text
    power = (
        f"10^\u2212{int(exponent[1:])}^"
        if exponent[0] == "-"
        else f"10^{int(exponent)}^"
    )
    return f"{mantissa}\u00a0\u00d7\u00a0{power}"


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"


def _illustration(course_id: str) -> str:
    """The course's illustration of the atlas, as inline SVG; decorative,
    since the course's name stands beside it."""
    return (
        '`<svg class="atlas-illustration home-illustration"'
        f' viewBox="0 0 {ILLUSTRATION} {ILLUSTRATION}" aria-hidden="true"'
        f' focusable="false">{ILLUSTRATIONS[course_id]()}</svg>`{{=html}}'
    )


def _planned(item: str, planned: int) -> str:
    """A list item of a course or path without a published lesson."""
    return (
        f"- {item} [planned]{{.home-planned}}"
        f" [no lesson published, {planned} planned]{{.home-count}}"
    )


@dataclass(frozen=True)
class HomeContent:
    path: LearningPath
    manifest: AtlasManifest
    commit: BuildCommit | None = None
    repository: str = ""
    page: str = HOME_PAGE

    def example(self, lesson_id: str) -> str:
        """A link to the published lesson ``lesson_id``."""
        return _link(self.page, self.path.lesson(lesson_id))

    def _atlas(self, fragment: str) -> str:
        return _href(self.page, PATH_PAGE, fragment)

    def _counts(self, published: int, planned: int) -> str:
        text = f"{_count(published, 'lesson')} published"
        if planned:
            text += f", {planned} planned"
        return f"[{text}]{{.home-count}}"

    def _course(self, course: Course) -> str:
        lessons = self.path.in_course(course)
        planned = len(self.path.planned_in_course(course))
        if not lessons:
            return _planned(f"{_illustration(course.id)} {course.title}", planned)
        link = f"[{course.title}]({self._atlas(f'course-{course.id}')})"
        return (
            f"- {_illustration(course.id)} {link} {self._counts(len(lessons), planned)}"
        )

    def _featured_course(self, course: Course) -> list[str]:
        """A featured course: its illustration, its name, its counts, and
        its first published lesson."""
        lessons = self.path.in_course(course)
        planned = len(self.path.planned_in_course(course))
        if lessons:
            name = f"[{course.title}]({self._atlas(f'course-{course.id}')})"
            counts = self._counts(len(lessons), planned)
            first = f"Starts with {self.example(lessons[0].id)}."
        else:
            name = f"{course.title} [planned]{{.home-planned}}"
            counts = f"[no lesson published, {planned} planned]{{.home-count}}"
            first = ""
        return [
            f"::: {{.home-course data-course={course.id}}}",
            _illustration(course.id),
            "",
            f"### {name} {{#home-course-{course.id} .unnumbered .unlisted}}",
            "",
            counts,
            "",
            first,
            ":::",
            "",
        ]

    def _method_path(self, method_path: MethodPath) -> str:
        lessons = self.path.in_path(method_path)
        planned = len(self.path.planned_in_path(method_path))
        if not lessons:
            return _planned(method_path.title, planned)
        link = f"[{method_path.title}]({self._atlas(f'path-{method_path.id}')})"
        return f"- {link} {self._counts(len(lessons), planned)}"

    def featured_courses(self) -> tuple[Course, ...]:
        return tuple(course for course in COURSES if course.id in FEATURED_COURSES)

    def part_a(self) -> str:
        """The eight courses with their counts: the featured three with their
        illustrations, then the other five in a compact row. A course with a
        published lesson links to its place in the atlas."""
        path = self.path
        capstones = len(self.capstone_slots())
        ending = (
            f"; {_word(capstones)} of them end in an applied capstone project"
            if capstones
            else ""
        )
        featured = self.featured_courses()
        lines = [
            f"Part A is {_word(len(COURSES))} physics courses. A course is a"
            " sequence of lessons in the teaching order of the reference"
            f" curriculum{ending}. The site publishes"
            f" {_count(len(path.lessons), 'lesson')}.",
            "",
            "::: {.home-featured}",
        ]
        for course in featured:
            lines += self._featured_course(course)
        lines += [
            ":::",
            "",
            "::: {.home-structure .home-compact}",
            *(self._course(course) for course in COURSES if course not in featured),
            ":::",
        ]
        return "\n".join(lines)

    def part_b(self) -> str:
        """The method paths with their counts, linked into the atlas the same
        way: a second layer over the courses."""
        return "\n".join(
            [
                f"Part B is {_word(len(self.path.paths))} method paths. A path is a"
                " second way through the lessons: the lessons of one method, in"
                " the order of the path, each published in its course.",
                "",
                "::: {.home-structure .home-paths}",
                *(self._method_path(item) for item in self.path.paths),
                ":::",
            ]
        )

    def capstone_slots(self) -> tuple[Slot, ...]:
        return tuple(
            slot for slot in self.path.curriculum.slots if slot.kind == CAPSTONE
        )

    def _capstone_lesson(self, slot: Slot) -> Lesson | None:
        return next(
            (lesson for lesson in self.path.lessons if lesson.slot == slot.label),
            None,
        )

    def _capstone_name(self, slot: Slot) -> str:
        """The capstone's course and state, linked to its lesson once it is
        published."""
        course = next(course for course in COURSES if course.id == slot.course)
        lesson = self._capstone_lesson(slot)
        if lesson is None:
            return f"{course.title}, capstone project [planned]{{.home-planned}}"
        return (
            f"[{course.title}, capstone project]({_href(self.page, lesson.page)})"
            " [published]{.home-published}"
        )

    def _artwork(self) -> list[str]:
        """The featured capstone's conceptual artwork and its label."""
        source = posixpath.relpath(
            f"{home_artwork.ASSETS}/{home_artwork.WAVEFRONT}",
            PurePosixPath(self.page).parent.as_posix(),
        )
        return [
            "::: {.home-artwork}",
            f'`<img src="{source}" alt="{home_artwork.ALT}"'
            f' width="{home_artwork.WIDTH}" height="{home_artwork.HEIGHT}">`{{=html}}',
            "",
            f"[{ARTWORK_LABEL}]{{.home-artwork-label}}",
            ":::",
        ]

    def capstones(self) -> str:
        """Each capstone project of the curriculum file: its course, its
        state, and the explanation of its concept in the map manifest, which
        names the project; nothing else describes it. The featured one comes
        first, on the dark ground, under its editorial heading and beside the
        conceptual artwork; the others follow smaller. A published capstone
        links to its lesson."""
        slots = self.capstone_slots()
        if not slots:
            return ""
        featured = [slot for slot in slots if slot.label == FEATURED_CAPSTONE]
        items = []
        for slot in featured:
            explanation = self.manifest.capstone(slot.label).explanation
            items += [
                f"::: {{.home-capstone .home-capstone-feature data-slot={slot.label}}}",
                "::: {.home-capstone-text}",
                f"### {FEATURED_HEADING} {{#capstone-{slot.label.lower()}"
                " .unnumbered .unlisted}",
                "",
                f"[{self._capstone_name(slot)}]{{.home-capstone-name}}",
                "",
                f"[{explanation}]{{.capstone-description}}",
                ":::",
                "",
                *self._artwork(),
                ":::",
                "",
            ]
        items.append("::: {.home-capstones}")
        for slot in slots:
            if slot in featured:
                continue
            explanation = self.manifest.capstone(slot.label).explanation
            items += [
                f"::: {{.home-capstone data-slot={slot.label}}}",
                f"[{self._capstone_name(slot)}]{{.home-capstone-name}}",
                "",
                f"[{explanation}]{{.capstone-description}}",
                ":::",
                "",
            ]
        items.append(":::")
        published = sum(self._capstone_lesson(slot) is not None for slot in slots)
        if published == 0:
            state = (
                "None is published yet: each is planned, and described as the"
                " curriculum plans it."
            )
        else:
            state = (
                f"{_word(published).capitalize()} of them"
                f" {'is' if published == 1 else 'are'} published."
            )
        intro = (
            f"{_word(len(slots)).capitalize()}"
            f" course{'s end' if len(slots) != 1 else ' ends'} in a project that"
            " brings their methods together on one applied problem. " + state
        )
        return "\n".join([intro, "", *items])

    def first_lesson(self) -> Lesson:
        """The first lesson of the first course in teaching order."""
        return self.path.in_course(self.path.courses[0])[0]

    def actions(self) -> str:
        """The two ways in, under the opening: the atlas and the first
        lesson."""
        first = self.first_lesson()
        return "\n".join(
            [
                "::: {.home-actions}",
                f"[Open the course atlas]({self._atlas('atlas')})"
                "{.home-action-primary}"
                f" [Start with {first.title}]({_href(self.page, first.page)})"
                "{.home-action}",
                ":::",
            ]
        )

    def begin(self) -> str:
        """The invitation: the atlas, and the first lesson."""
        return (
            f"Begin with the [course atlas]({self._atlas('atlas')}): the"
            " courses and the method paths on one map, with a link to every"
            " published lesson. Or start reading at the first lesson,"
            f" {self.example(self.first_lesson().id)}."
        )

    def opening_note(self, result: Mapping[str, str]) -> str:
        """What the opening figure computed, from the numbers of its run
        (``home_opening.run()``), and where it comes from."""
        return "\n\n".join(
            [
                self.provenance(),
                f"Both rods start at {result['angle']} rad. The motion is"
                " computed with the classical Runge-Kutta method at a step of"
                f" {result['step']} s for {result['duration']} s: the energy"
                f" changes by at most {_scientific(result['energy-change'])} of"
                " its start, and a run at half the step keeps the second bob"
                f" within {_scientific(result['half-step-gap'])} m of this path."
                " The model and its checks are in the lesson"
                f" {self.example(OPENING_LESSON)}.",
            ]
        )

    def provenance(self) -> str:
        """Where the opening figure comes from: the module and the commit."""
        commit = self.commit
        if commit is None or commit.sha is None or not self.repository:
            source = f"`{OPENING_SOURCE}`"
            built = (
                "This page was not built from a Git checkout, so no commit is named."
            )
        else:
            source = (
                f"[`{OPENING_SOURCE}`]({self.repository}/blob/{commit.sha}"
                f"/{OPENING_SOURCE})"
            )
            built = (
                f"Built from commit [`{commit.sha[:12]}`]"
                f"({self.repository}/commit/{commit.sha})"
            )
            built += (
                ", with uncommitted changes in the checkout." if commit.dirty else "."
            )
        return (
            f"Drawn when this page was built, by `draw_opening` in {source},"
            " from the double pendulum of `pbc.mechanics.chaos`. " + built
        )


def home_content() -> HomeContent:
    """Return the generated parts of the home page being built."""
    site = project_root(Path.cwd().resolve())
    path = LearningPath.read(site)
    return HomeContent(
        path,
        AtlasManifest.read(site, path.curriculum),
        commit=build_commit(),
        repository=repository_url(),
    )
