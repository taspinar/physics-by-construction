"""The "published and planned" section and the examples of the home page.

What the home page says is published comes from the lesson front matter, read
with the same code as the learning path, so a number or a title on the home
page cannot differ from the lessons. What is planned is the short list below:
every item names its roadmap ID (``docs/roadmap.md``), is labelled planned,
and is never a link. ``tests/unit/test_home.py`` checks the list against the
roadmap.
"""

from dataclasses import dataclass
from pathlib import Path

from pbc.authoring.path import LearningPath, _href, _link
from pbc.authoring.website import PAGE_FILE, project_root

HOME_PAGE = PAGE_FILE

# The one published lesson that each activity points to, by lesson id.
CONSTRUCT_EXAMPLE = "numerical-integrators"
INVESTIGATE_EXAMPLE = "agent-experiment"
VERIFY_EXAMPLE = "proving-what-the-simulation-showed"


@dataclass(frozen=True)
class Planned:
    roadmap_id: str
    title: str
    kind: str


# Planned, not published. No date is promised. Keep to the items of the
# roadmap; remove an item when its feature is delivered.
PLANNED = (
    Planned(
        "F60",
        "Gravitational-wave strain lab: from Kepler's orbit to a chirp",
        "measured-data lab",
    ),
    Planned("F54", "Microwave S-parameter lab", "measured-data lab"),
    Planned("F53", "Flow measurement lab with PIV fields", "measured-data lab"),
    Planned("F52", "Optical diffraction lab", "measured-data lab"),
    Planned("F15", "A second course beyond mechanics", "further course"),
)


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"


@dataclass(frozen=True)
class HomeContent:
    path: LearningPath
    page: str = HOME_PAGE

    def example(self, lesson_id: str) -> str:
        """A link to the published lesson ``lesson_id``."""
        return _link(self.page, self.path.lesson(lesson_id))

    def published(self) -> str:
        path = self.path
        lines = [
            f"The site publishes {_count(len(path.lessons), 'lesson')} in"
            f" {_count(len(path.strands), 'strand')}. A lesson appears here"
            " only after it passes verification.",
            "",
        ]
        for course in path.courses:
            lessons = path.in_course(course)
            core = [lesson for lesson in lessons if lesson.strand == course.id]
            extensions = len(lessons) - len(core)
            lines.append(
                f"The {course.title} course is published with"
                f" {_count(len(core), 'core lesson')} and"
                f" {_count(extensions, 'extension')}"
                f" ([by course]({_href(self.page, 'path/index.qmd', 'courses')}))."
            )
            lines.append("")
        for strand in path.strands:
            lessons = path.in_strand(strand)
            lines.append(
                f"{strand.title}: "
                + "; ".join(_link(self.page, lesson) for lesson in lessons)
                + "."
            )
            lines.append("")
        lines.append(
            "See the [learning path](" + _href(self.page, "path/index.qmd") + ")"
            " for every lesson with its difficulty and prerequisites, and"
            " [by method](" + _href(self.page, "path/index.qmd", "methods") + ")"
            " for the paths of simulation, LLM agents, agent-based modelling,"
            " and formal proofs."
        )
        return "\n".join(lines)

    def planned(self) -> str:
        lines = [
            "Planned means not published. No date is promised. The IDs are"
            " those of the project roadmap in the repository.",
            "",
        ]
        for item in PLANNED:
            lines.append(f"- Planned, {item.roadmap_id}: {item.title} ({item.kind}).")
        return "\n".join(lines)


def home_content() -> HomeContent:
    """Return the generated parts of the home page being built."""
    site = project_root(Path.cwd().resolve())
    return HomeContent(LearningPath.read(site))
