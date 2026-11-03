"""Instructor packs: the part of a pack that is read from the repository.

A pack is a Markdown file in ``docs/instructor-packs/<lesson id>.md``. Its
generated block (learning objectives, prerequisites, difficulty, and the
citation) is written from the front matter of the lesson and from
``CITATION.cff``, so it cannot drift from them; the rest is written by hand.
``python -m pbc.authoring.educators`` writes the block into every pack
(``--check`` only compares), and a test reads the packs against the lessons.
The "For educators" page of the site lists the packs through :func:`packs_list`.
"""

import argparse
import re
import sys
from collections.abc import Sequence
from pathlib import Path

import yaml

from pbc.authoring.improvement import form_url
from pbc.authoring.path import DIFFICULTIES, LearningPath, Lesson
from pbc.authoring.repository import REPOSITORY_ROOT, repository_url

PACKS_DIRECTORY = "docs/instructor-packs"
CITATION_FILE = "CITATION.cff"

BLOCK_START = "<!-- pack:start (written by pbc.authoring.educators) -->"
BLOCK_END = "<!-- pack:end -->"
BLOCK = re.compile(re.escape(BLOCK_START) + r".*?" + re.escape(BLOCK_END), re.S)

# The Issue forms an educator can use; the outcome is recorded on the Issue.
FEEDBACK_FORMS = (
    (
        "scientific-correction",
        "Scientific correction",
        "a wrong statement, number, or derivation",
    ),
    ("bug", "Bug", "a listing or a reference solution that does not run"),
)


def citation_text(cff: Path | None = None) -> str:
    """Return the citation sentence, built from ``CITATION.cff`` alone."""
    path = cff or REPOSITORY_ROOT / CITATION_FILE
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    authors = ", ".join(
        f"{a['family-names']}, {a['given-names'][0]}." for a in data["authors"]
    )
    return f'{authors} "{data["title"]}". {data["url"]}'


def pack_path(lesson: Lesson, root: Path = REPOSITORY_ROOT) -> Path:
    return root / PACKS_DIRECTORY / f"{lesson.id}.md"


def generated_block(lesson: Lesson, path: LearningPath, cff: Path | None = None) -> str:
    """Return the block of the pack that is derived, markers included."""
    difficulty = next(d for d in DIFFICULTIES if d.level == lesson.difficulty)
    prerequisites = [
        f"- Lesson: {path.lesson(lesson_id).title}"
        for lesson_id in lesson.prerequisites
    ] + [f"- Outside the site: {text}" for text in lesson.outside]
    lines = [
        BLOCK_START,
        f"Lesson: **{lesson.title}** (`{lesson.id}`, {lesson.strand} lesson "
        f"{lesson.order}). Difficulty {lesson.difficulty}: {difficulty.title}.",
        "",
        "### Learning objectives",
        "",
        "After the lesson a student can:",
        "",
        *[f"- {outcome}" for outcome in lesson.outcomes],
        "",
        "### Prerequisites",
        "",
        *(prerequisites or ["- None."]),
        "",
        "### Citation",
        "",
        "Cite the project as:",
        "",
        f"> {citation_text(cff)}",
        BLOCK_END,
    ]
    return "\n".join(lines)


def sync_pack(text: str, lesson: Lesson, path: LearningPath) -> str:
    block = generated_block(lesson, path)
    return BLOCK.sub(lambda _: block, text, count=1)


def pack_lessons(path: LearningPath, root: Path = REPOSITORY_ROOT) -> list[Lesson]:
    """The lessons that have a pack, in learning path order."""
    return [lesson for lesson in path.lessons if pack_path(lesson, root).is_file()]


def packs_list(path: LearningPath) -> str:
    """Markdown list of the packs, for the "For educators" page."""
    base = repository_url()
    lines = [
        f"- [{lesson.title}]({base}/blob/main/{PACKS_DIRECTORY}/{lesson.id}.md)"
        for lesson in pack_lessons(path)
    ]
    return "\n".join(lines) or "No pack is published yet."


def forms_list(forms: Sequence[tuple[str, str, str]] = FEEDBACK_FORMS) -> str:
    """Markdown list of Issue forms: by default those an educator can use;
    the Contribute page passes the forms of "Suggest an improvement"
    (``pbc.authoring.improvement.FORMS``)."""
    base = repository_url()
    return "\n".join(
        f"- [{title}]({form_url(base, name)}): {what}" for name, title, what in forms
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="only compare")
    arguments = parser.parse_args(argv)
    path = LearningPath.read(REPOSITORY_ROOT / "site")
    stale = []
    for lesson in pack_lessons(path):
        file = pack_path(lesson)
        text = file.read_text(encoding="utf-8")
        updated = sync_pack(text, lesson, path)
        if updated != text:
            stale.append(file.name)
            if not arguments.check:
                file.write_text(updated, encoding="utf-8")
    if stale:
        print(("Out of date: " if arguments.check else "Updated: ") + ", ".join(stale))
    return 1 if stale and arguments.check else 0


if __name__ == "__main__":
    sys.exit(main())
