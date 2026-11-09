"""The introduction of a course or a method path (F156, requirements decision
43, ``docs/architecture.md`` "The textbook layer").

The editorial text of an introduction lives in one data file per sequence,
``site/introductions/<sequence-id>.yaml``, beside the atlas manifest. It holds
prose (inline Markdown, one string per paragraph or item) in the seven
sections of decision 43 and references, and nothing else: no lesson list,
title, count, prerequisite, outcome, capstone identity, or publication state.
Those come from the curriculum file and the front matter when the page is
built, so no second lesson catalogue exists. Any other field is an error.

A reference is written in braces inside a text and resolved here:

- ``{sequence:mechanics}``: the title of a course or a method path, linked to
  its introduction when it has one, else to its panel in the atlas;
- ``{slot:M8}``: the title of the lesson that fills the slot, linked to the
  lesson; a slot that no published lesson fills is shown as its working
  title with "(planned)", never as a link;
- ``{term:Calculus}``: a term of the glossary, linked to its entry.

A reference that does not resolve is an error and fails the build. The page
``courses/<sequence-id>/index.qmd`` is a thin source that calls
``introduction_content()``; a test keeps the page sources and the data files
one to one.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path

import yaml

from pbc.authoring.atlas import Atlas, AtlasSection, AtlasSequence, Row
from pbc.authoring.glossary import GLOSSARY_PAGE, Glossary, split_outside
from pbc.authoring.path import (
    COURSES,
    PATH_PAGE,
    Curriculum,
    Lesson,
    _href,
)
from pbc.authoring.website import (
    INTRODUCTION_SUFFIX,
    INTRODUCTIONS_DIRECTORY,
    introduced,
    introduction_page,
    page_href,
    project_root,
)

# The sections of decision 43, in the order of the page: the key of the data
# file, the heading, whether the text is a list of items or of paragraphs.
SECTIONS = (
    ("why", "Why it matters", "paragraphs"),
    ("questions", "Central questions", "items"),
    ("learn", "What you will learn", "items"),
    ("order", "Why the lessons come in this order", "paragraphs"),
    ("method", "The method and why", "paragraphs"),
    ("capstone", "The capstone", "paragraphs"),
    ("next", "What comes next", "paragraphs"),
)
FIELDS = {"sequence"} | {key for key, _, _ in SECTIONS}

# The kinds of reference.
SEQUENCE, SLOT, TERM = "sequence", "slot", "term"
_REFERENCE = re.compile(r"\{([a-z]+):([^{}]*)\}")

# What an inline text must not hold: blocks, tables, raw HTML, images, links
# written by hand (a link is a reference, which resolves), attributes, and a
# bare address.
_BLOCK = re.compile(r"^\s*(#|>|[-*+]\s|\d+[.)]\s|```|~~~|\||:::)")
_NOT_INLINE = re.compile(r"<[A-Za-z/!]|!\[|\]\(|\{[#.=]|https?://|\||```")
_UNITS = "one|two|three|four|five|six|seven|eight|nine"
_TEENS = (
    "ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen"
)
_TENS = "twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety"
# A number word: a unit, a teen, a ten with an optional unit joined by a
# hyphen or a space ("twenty-one", "ninety four"), or a hundred.
_NUMBER_WORDS = (
    rf"(?:(?:{_TENS})(?:[\s-]+(?:{_UNITS}))?|{_TEENS}|{_UNITS}|zero|hundred)"
)
# A count of lessons or slots: the page derives it, the file never states it.
# The number and the noun are joined by a space or a hyphen ("17 lessons",
# "twenty-one-lesson course").
_COUNT = re.compile(
    rf"\b(\d[\d,.]*|{_NUMBER_WORDS})[\s-]+"
    r"((core|published|planned|optional)[\s-]+)*(lessons?|slots?)\b",
    re.IGNORECASE,
)


def sequence_ids(curriculum: Curriculum) -> tuple[str, ...]:
    """The identifiers of the courses and method paths. Raises
    ``ValueError`` when two sequences share one: the address of an
    introduction is the identifier alone."""
    found = [course.id for course in COURSES] + [p.id for p in curriculum.paths]
    twice = sorted({item for item in found if found.count(item) > 1})
    if twice:
        raise ValueError(
            f"the sequence identifiers {', '.join(twice)} are used by both a"
            " course and a method path or twice; an introduction is addressed"
            " by the identifier alone"
        )
    return tuple(found)


# --- The data file -----------------------------------------------------------


def _unreferenced_lessons(text: str, curriculum: Curriculum) -> list[str]:
    """What the text names of the lessons outside a reference, a lesson list
    written by hand that would be a second, stale catalogue: any slot label,
    and a run of two or more slot titles (one title alone may be the plain
    name of a concept). A lesson is named by ``{slot:<label>}``."""
    bare = _REFERENCE.sub(" ", text)
    labels, titles = [], []
    for slot in curriculum.slots:
        edge = r"(?<![A-Za-z0-9]){}(?![A-Za-z0-9])"
        if re.search(edge.format(re.escape(slot.label)), bare):
            labels.append(slot.label)
        if re.search(edge.format(re.escape(slot.title)), bare, re.IGNORECASE):
            titles.append(slot.title)
    return labels + (titles if len(titles) > 1 else [])


def _text_problems(
    where: str, value: object, curriculum: Curriculum | None = None
) -> list[str]:
    """What is wrong with one text of a section: not text, empty, more than
    one paragraph, not inline Markdown, a count of lessons, or a lesson
    named outside a reference."""
    if not isinstance(value, str) or not value.strip():
        return [f"{where} is not text"]
    found = []
    if "\n\n" in value.strip():
        found.append(f"{where} holds more than one paragraph; one text each")
    text = " ".join(value.split())
    if _BLOCK.search(text) or _NOT_INLINE.search(text):
        found.append(
            f"{where} holds more than inline Markdown (a heading, list, table,"
            " HTML, image, link, or attribute); write a link as a reference"
        )
    if _COUNT.search(text):
        found.append(
            f"{where} states a count of lessons or slots; the page derives"
            " every count from the curriculum file and the front matter"
        )
    if curriculum is not None and (named := _unreferenced_lessons(text, curriculum)):
        found.append(
            f"{where} names lessons outside a reference ({', '.join(named)});"
            " write each as {slot:<label>}, never a hand-written lesson list"
        )
    return found


def _reference_problems(
    where: str,
    text: str,
    curriculum: Curriculum,
    sequences: Collection[str],
    terms: Collection[str],
) -> list[str]:
    found = []
    for kind, name in _REFERENCE.findall(text):
        name = name.strip()
        if kind == SEQUENCE and name not in sequences:
            found.append(f"{where}: the sequence {name!r} is not a course or path")
        elif kind == SLOT and curriculum.slot(name) is None:
            found.append(f"{where}: the slot {name!r} is not in the curriculum file")
        elif kind == TERM and name not in terms:
            found.append(f"{where}: the term {name!r} is not in the glossary")
        elif kind not in (SEQUENCE, SLOT, TERM):
            found.append(
                f"{where}: {{{kind}:...}} is not a reference; use sequence, slot,"
                " or term"
            )
    if re.search(r"[{}]", _REFERENCE.sub(" ", text)):
        found.append(
            f"{where}: a brace that is not part of a complete reference"
            " {sequence|slot|term:name}"
        )
    return found


def introduction_problems(
    data: object,
    sequence_id: str,
    curriculum: Curriculum,
    terms: Collection[str] = (),
) -> list[str]:
    """Every rule of an introduction file that ``data`` breaks: it is a
    mapping of ``sequence`` (the identifier of the file's own sequence) and
    the seven sections, no field more, none less; the paragraphs of a
    section and the items of a list are non-empty inline Markdown without a
    count of lessons or slots; every reference resolves."""
    where = f"{INTRODUCTIONS_DIRECTORY}/{sequence_id}{INTRODUCTION_SUFFIX}"
    if not isinstance(data, dict):
        return [f"{where} is not a mapping of the sections"]
    found = []
    if unknown := set(data) - FIELDS:
        found.append(
            f"{where} has fields outside the schema: "
            + ", ".join(sorted(map(str, unknown)))
            + " (an introduction holds prose and references only)"
        )
    if missing := FIELDS - set(data):
        found.append(f"{where} lacks {', '.join(sorted(missing))}")
    try:
        sequences = sequence_ids(curriculum)
    except ValueError as error:
        return [*found, str(error)]
    if sequence_id not in sequences:
        found.append(f"{where}: {sequence_id!r} is neither a course nor a method path")
    if "sequence" in data and data["sequence"] != sequence_id:
        found.append(
            f"{where}: 'sequence' is {data['sequence']!r}; it names the file's"
            f" own sequence, {sequence_id!r}"
        )
    for key, _, _ in SECTIONS:
        items = data.get(key)
        if key not in data:
            continue
        if not isinstance(items, list) or not items:
            found.append(f"{where}: {key} is not a non-empty list of texts")
            continue
        for number, item in enumerate(items, start=1):
            place = f"{where}: {key} {number}"
            problems = _text_problems(place, item, curriculum)
            found += problems
            if isinstance(item, str):
                found += _reference_problems(place, item, curriculum, sequences, terms)
    return found


@dataclass(frozen=True)
class Introduction:
    """The validated editorial text of the introduction of one sequence."""

    sequence: str
    sections: dict[str, tuple[str, ...]]

    @classmethod
    def parse(
        cls,
        data: object,
        sequence_id: str,
        curriculum: Curriculum,
        terms: Collection[str] = (),
    ) -> Introduction:
        found = introduction_problems(data, sequence_id, curriculum, terms)
        if found:
            raise ValueError(
                f"the introduction of {sequence_id} breaks its rules:\n"
                + "\n".join(f"  {message}" for message in found)
            )
        assert isinstance(data, dict)
        return cls(
            sequence_id,
            {
                key: tuple(" ".join(t.split()) for t in data[key])
                for key, _, _ in SECTIONS
            },
        )

    @classmethod
    def read(
        cls, site: Path, sequence_id: str, curriculum: Curriculum, glossary: Glossary
    ) -> Introduction:
        """Read ``introductions/<sequence_id>.yaml`` of the website project
        ``site``. Raises ``ValueError`` when it breaks a rule; a missing file
        breaks them."""
        file = site / INTRODUCTIONS_DIRECTORY / f"{sequence_id}{INTRODUCTION_SUFFIX}"
        data: object = None
        if file.is_file():
            try:
                data = yaml.safe_load(file.read_text(encoding="utf-8"))
            except yaml.YAMLError as error:
                raise ValueError(f"{file.name} is not valid YAML: {error}") from None
        terms = tuple(entry.term for entry in glossary.entries)
        return cls.parse(data, sequence_id, curriculum, terms)


_TITLE = re.compile(r"^title:\s*(.+?)\s*$", re.MULTILINE)


def _title_problems(site: Path, sequence_id: str, title: str) -> list[str]:
    """The page source carries the sequence's title as its ``title``, since
    the page's title is a field of the source; it must equal the title of
    the curriculum file."""
    source = (site / introduction_page(sequence_id)).read_text(encoding="utf-8")
    front = source.split("---", 2)[1] if source.startswith("---") else ""
    match = _TITLE.search(front)
    shown = yaml.safe_load(match.group(1)) if match else None
    if shown != title:
        return [
            f"{introduction_page(sequence_id)} has the title {shown!r}; the"
            f" title of the sequence is {title!r}"
        ]
    return []


def page_source_problems(site: Path) -> list[str]:
    """The page sources and the data files are one to one: every data file
    has its page source ``courses/<id>/index.qmd``, every such page source
    has its data file, a data file names a course or a method path, and the
    title of a page source is the title of its sequence."""
    files = introduced(site)
    pages = {
        page.parent.name
        for page in (site / "courses").glob("*/index.qmd")
        if page.is_file()
    }
    found = [
        f"{INTRODUCTIONS_DIRECTORY}/{item}{INTRODUCTION_SUFFIX} has no page"
        f" source {introduction_page(item)}"
        for item in sorted(files - pages)
    ]
    found += [
        f"{introduction_page(item)} has no data file"
        f" {INTRODUCTIONS_DIRECTORY}/{item}{INTRODUCTION_SUFFIX}"
        for item in sorted(pages - files)
    ]
    curriculum = Curriculum.read(site)
    titles = {course.id: course.title for course in COURSES} | {
        method_path.id: method_path.title for method_path in curriculum.paths
    }
    for item in sorted(files & pages & titles.keys()):
        found += _title_problems(site, item, titles[item])
    known = set(sequence_ids(curriculum))
    found += [
        f"{INTRODUCTIONS_DIRECTORY}/{item}{INTRODUCTION_SUFFIX}: {item!r} is"
        " neither a course nor a method path"
        for item in sorted(files - known)
    ]
    return found


# --- The references ----------------------------------------------------------


@dataclass(frozen=True)
class References:
    """The resolution of the references of a prose source on the page
    ``page``: a slot is the title of its lesson, linked, or its working title
    with "(planned)" and no link; a sequence is its title, linked to its
    introduction when it has one, else to its panel in the atlas; a term is
    linked to its glossary entry. The introductions and the learning journey
    (F157) share it."""

    atlas: Atlas
    glossary: Glossary
    available: frozenset[str]  # the sequences that have an introduction
    page: str

    def _slot(self, label: str) -> str:
        slot = self.atlas.path.curriculum.slot(label)
        assert slot is not None
        lesson = next(
            (item for item in self.atlas.path.lessons if item.slot == label), None
        )
        if lesson is None:
            # A planned slot is text: never a link, never counted.
            return f"{slot.title} (planned)"
        return f"[{lesson.title}]({_href(self.page, lesson.page)})"

    def _sequence_link(self, sequence_id: str) -> str:
        sequence = next(
            item for item in self.atlas.sequences() if item.id == sequence_id
        )
        if sequence_id in self.available:
            target = page_href(self.page, introduction_page(sequence_id))
        else:
            target = page_href(self.page, PATH_PAGE, sequence.anchor)
        return f"[{sequence.title}]({target})"

    def _term(self, term: str) -> str:
        entry = next(entry for entry in self.glossary.entries if entry.term == term)
        return f"[{term}]({page_href(self.page, GLOSSARY_PAGE, entry.anchor)})"

    def inline(self, text: str) -> str:
        """The text with its references replaced by links or text."""

        def replace(match: re.Match[str]) -> str:
            kind, name = match.group(1), match.group(2).strip()
            if kind == SEQUENCE:
                return self._sequence_link(name)
            if kind == SLOT:
                return self._slot(name)
            return self._term(name)

        return _REFERENCE.sub(replace, text)


# --- The page ----------------------------------------------------------------


@dataclass(frozen=True)
class IntroductionContent:
    """The introduction page of one sequence: the editorial sections from
    the data file and everything else from the curriculum file, the front
    matter, the atlas manifest, and the glossary. It holds no script and no
    state."""

    atlas: Atlas
    glossary: Glossary
    introduction: Introduction
    available: frozenset[str]  # the sequences that have an introduction

    @property
    def sequence(self) -> AtlasSequence:
        return next(
            sequence
            for sequence in self.atlas.sequences()
            if sequence.id == self.introduction.sequence
        )

    @property
    def page(self) -> str:
        return introduction_page(self.sequence.id)

    @property
    def references(self) -> References:
        return References(self.atlas, self.glossary, self.available, self.page)

    def _term(self, term: str) -> str:
        return self.references._term(term)

    def inline(self, text: str) -> str:
        """The text with its references replaced by links or text."""
        return self.references.inline(text)

    # --- Derived parts ---------------------------------------------------------

    def lessons(self) -> tuple[Lesson, ...]:
        return tuple(row.lesson for row in self.sequence.rows if row.lesson is not None)

    def prerequisite_lessons(self) -> tuple[Lesson, ...]:
        """The lessons of other sequences that a lesson of this one names as
        a prerequisite, in the order of the learning path."""
        own = {lesson.id for lesson in self.lessons()}
        needed = {
            item
            for lesson in self.lessons()
            for item in lesson.prerequisites
            if item not in own
        }
        return tuple(
            lesson for lesson in self.atlas.path.lessons if lesson.id in needed
        )

    def prerequisite_terms(self) -> tuple[str, ...]:
        """The terms of the background that no lesson teaches, which the
        lessons of this sequence assume, in the glossary's order."""
        named = {
            split_outside(text)[0]
            for lesson in self.lessons()
            for text in lesson.outside
        }
        known = [entry.term for entry in self.glossary.entries if entry.term in named]
        return (*known, *sorted(named - set(known)))

    def _home_of(self, lesson: Lesson) -> str:
        """The sequence of a prerequisite lesson, as its name: its slot's
        path or its course."""
        slot = self.atlas.path.slot_of(lesson)
        if slot is not None and slot.path:
            return self.atlas.path.curriculum.path(slot.path).title
        if lesson.strand == "lean":
            return "the Lean proofs"
        return next(
            (course.title for course in COURSES if course.id == lesson.course),
            lesson.course,
        )

    def prerequisites(self) -> str:
        lessons = self.prerequisite_lessons()
        terms = self.prerequisite_terms()
        parts = []
        if lessons:
            items = "\n".join(
                f"- [{lesson.title}]({_href(self.page, lesson.page)}),"
                f" in {self._home_of(lesson)}"
                for lesson in lessons
            )
            parts.append(
                "Lessons of other sequences that a lesson here builds on:\n\n" + items
            )
        else:
            parts.append(
                "No lesson of another course or method path is required first."
            )
        if terms:
            glossary = {entry.term for entry in self.glossary.entries}
            items = "\n".join(
                f"- {self._term(term) if term in glossary else term}" for term in terms
            )
            parts.append(
                "Background from outside the site, which the glossary defines:\n\n"
                + items
            )
        return "\n\n".join(parts)

    def _row(self, row: Row) -> str:
        label = f'<span class="intro-label">{html.escape(row.label)}</span>'
        marks = ""
        if row.kind == "measured-data lab":
            marks += '<span class="intro-mark">Lab</span>'
        if row.is_capstone:
            marks += '<span class="intro-mark">Capstone</span>'
        if row.lesson is None:
            # Planned: its label and working title, no link, not counted.
            title = f'<span class="intro-planned">{html.escape(row.title)}</span>'
            marks += '<span class="intro-mark">planned</span>'
            state = "planned"
            description = (
                f'<span class="intro-description">{html.escape(row.description)}</span>'
                if row.description
                else ""
            )
        else:
            href = html.escape(_href(self.page, row.lesson.page))
            title = f'<a href="{href}">{html.escape(row.title)}</a>'
            state = "published"
            description = ""
        return (
            f'<li class="intro-row" data-state="{state}">{label}'
            f'<span class="intro-title">{title}{description}</span>'
            f'<span class="intro-marks">{marks}</span></li>'
        )

    def lesson_list(self) -> str:
        """The lessons as the atlas shows them: the core rows in teaching
        order with the published and planned counts, and a method path's
        optional extensions after them."""
        sequence = self.sequence
        counts = f"{sequence.published} published"
        if sequence.planned:
            counts += f" and {sequence.planned} planned"
        core = len(sequence.core)
        lines = [
            f"{sequence.published} of {core} lessons are published"
            + (f" ({sequence.planned} planned)" if sequence.planned else "")
            + ". A planned lesson is named here and is not a link.",
            "",
            "```{=html}",
            '<ol class="intro-rows">'
            + "".join(self._row(row) for row in sequence.core)
            + "</ol>",
        ]
        if sequence.extensions:
            extra = f"{sequence.extension_published} published"
            if sequence.extension_planned:
                extra += f", {sequence.extension_planned} planned"
            lines += [
                "```",
                "",
                f"Optional extensions, beside the {core} lessons of the path"
                f" and not counted with them ({extra}):",
                "",
                "```{=html}",
                '<ol class="intro-rows intro-rows-extension">'
                + "".join(self._row(row) for row in sequence.extensions)
                + "</ol>",
            ]
        lines.append("```")
        return "\n".join(lines)

    def _kicker(self) -> str:
        sequence = self.sequence
        kind = "Course" if sequence.part == "A" else "Method path"
        return f"Part {sequence.part}, {kind} {sequence.number}"

    def _head(self) -> str:
        sequence = self.sequence
        section = AtlasSection(self.atlas, self.page)
        image = section._image(sequence, "panel", eager=True)
        home = html.escape(page_href(self.page, "index.qmd"))
        atlas = html.escape(page_href(self.page, PATH_PAGE, sequence.anchor))
        title = html.escape(sequence.title)
        crumbs = (
            '<nav class="pbc-breadcrumb" aria-label="Breadcrumb"><ol>'
            f'<li><a href="{home}">Home</a></li>'
            f'<li><a href="{atlas}">Course Atlas</a></li>'
            f'<li><span aria-current="page">{title}</span></li>'
            "</ol></nav>"
        )
        return "\n".join(
            [
                "```{=html}",
                crumbs,
                '<div class="intro-head">',
                f'<figure class="intro-figure">{image}</figure>',
                "<div>",
                f'<p class="intro-kicker">{html.escape(self._kicker())}</p>',
                f'<p class="intro-description">{html.escape(sequence.description)}</p>',
                "</div></div>",
                "```",
            ]
        )

    def markdown(self) -> str:
        """The whole page below its title (the ``title`` of the page source,
        which ``page_source_problems`` keeps equal to the sequence's title):
        the breadcrumb, the sequence's illustration and one-line description,
        the seven sections, the prerequisites, and the lessons."""
        parts = [self._head()]
        for key, heading, kind in SECTIONS:
            parts.append(f"## {heading} {{#{key}}}")
            texts = [self.inline(text) for text in self.introduction.sections[key]]
            if kind == "items":
                parts.append("\n".join(f"- {text}" for text in texts))
            else:
                parts.append("\n\n".join(texts))
        parts += [
            "## Prerequisites {#prerequisites}",
            self.prerequisites(),
            "## The lessons {#lessons}",
            self.lesson_list(),
        ]
        return "\n\n".join(parts) + "\n"


def introduction_content() -> IntroductionContent:
    """Return the introduction page being built: the sequence is the name of
    the directory of the page, ``courses/<sequence-id>/``."""
    directory = Path.cwd().resolve()
    site = project_root(directory)
    sequence_id = directory.name
    atlas = Atlas.read(site)
    glossary = Glossary.read(site)
    introduction = Introduction.read(site, sequence_id, atlas.path.curriculum, glossary)
    return IntroductionContent(atlas, glossary, introduction, introduced(site))


def main(argv: list[str] | None = None) -> int:
    """``python -m pbc.authoring.introductions --site <dir>``: the build's
    check that page sources and data files are one to one."""
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--site", type=Path, required=True)
    found = page_source_problems(parser.parse_args(argv).site)
    for problem in found:
        print(f"introductions: {problem}", file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
