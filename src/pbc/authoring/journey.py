"""The learning journey (F157, requirements decision 43,
``docs/architecture.md`` "The textbook layer").

One source, ``site/journey.yaml`` beside the atlas manifest, holds the text
of the learning journey from computational physics to AI-supported
scientific investigation: Part A, Part B, and how the first leads to the
second (the three texts About shares with the atlas), the expected
background, that a route needs only its stated prerequisites, how a capstone
fits, and the three kinds of evidence (numerical, empirical, formal proof).
The Course Atlas opens with all of it, before its cards; About carries the
Part A and Part B text from the same file.

The file holds prose (inline Markdown, one string per paragraph) and
references, nothing else: no lesson list, title, count, or publication
state, which come from the curriculum file and the front matter. A reference
is ``{sequence:<id>}``, ``{slot:<label>}``, or ``{term:<glossary term>}`` and
is resolved as on an introduction (``pbc.authoring.introductions``); one that
does not resolve fails the build. Beyond the rules of an introduction's
text, the prose states no count of courses, method paths, sequences, or
capstones, and uses no form of "discover" outside a reference, so that it
cannot present an AI result as a discovery; the review decides the rest.
"""

from __future__ import annotations

import re
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path

import yaml

from pbc.authoring.atlas import _PART_NAMES, Atlas
from pbc.authoring.glossary import Glossary
from pbc.authoring.introductions import (
    _NUMBER_WORDS,
    _REFERENCE,
    References,
    _reference_problems,
    _text_problems,
    sequence_ids,
)
from pbc.authoring.path import COURSES, PATH_PAGE, Curriculum
from pbc.authoring.website import introduced, page_href, project_root

# Where the file sits in the website project, beside the atlas manifest.
JOURNEY_FILE = "journey.yaml"
VERIFY_PAGE = "verify.qmd"
ABOUT_PAGE = "about.qmd"

# The sections of prose, in the order of the atlas: the key of the file and
# the heading. The first three are the Part A and Part B text that About
# shares with the atlas.
SECTIONS = (
    ("part-a", f"Part A: {_PART_NAMES['A']}"),
    ("part-b", f"Part B: {_PART_NAMES['B']}"),
    ("relation", "From Part A to Part B"),
    ("background", "What you need to begin"),
    ("routes", "Choosing a route"),
    ("capstones", "Where a capstone fits"),
)
SHARED = ("part-a", "part-b", "relation")
# The three kinds of evidence, each with its own texts: the key under
# ``evidence`` and the term the pages show.
EVIDENCE = (
    ("numerical", "Numerical evidence"),
    ("empirical", "Empirical evidence"),
    ("formal-proof", "Formal proof"),
)
EVIDENCE_HEADING = "Three kinds of evidence"
FIELDS = {key for key, _ in SECTIONS} | {"evidence"}

# A count of the sequences of the atlas: the atlas derives it. "One" is no
# count ("each lesson belongs to one course").
_SEQUENCE_COUNT = re.compile(
    rf"\b(\d[\d,.]*|(?!one\b){_NUMBER_WORDS})[\s-]+"
    r"((physics|method|core|published|planned)[\s-]+)*"
    r"(courses?|paths?|sequences?|capstones?)\b",
    re.IGNORECASE,
)
_DISCOVERY = re.compile(r"\bdiscover\w*", re.IGNORECASE)
# A sentence of a text: up to its full stop, question or exclamation mark.
_SENTENCE = re.compile(r"[^.!?]+[.!?]*")
_NEGATION = re.compile(r"\b(not|no)\b", re.IGNORECASE)


def _unframed_discovery(text: str) -> bool:
    """Whether ``text`` uses a form of "discover" in a sentence that neither
    asks a question nor negates the word ("not" or "no" before it)."""
    for sentence in _SENTENCE.findall(text):
        for word in _DISCOVERY.finditer(sentence):
            asked = sentence.rstrip().endswith("?")
            if not asked and not _NEGATION.search(sentence[: word.start()]):
                return True
    return False


def _journey_text_problems(
    where: str,
    value: object,
    curriculum: Curriculum,
    sequences: Collection[str],
    terms: Collection[str],
    framed_discovery: bool = False,
) -> list[str]:
    """Every text rule of the journey that ``value`` breaks. With
    ``framed_discovery`` (the Home copy, Issue #481), a form of "discover"
    may stand in a question or after a negation in its sentence; elsewhere
    it never may."""
    found = _text_problems(where, value, curriculum)
    if not isinstance(value, str):
        return found
    bare = _REFERENCE.sub(" ", " ".join(value.split()))
    if _SEQUENCE_COUNT.search(bare):
        found.append(
            f"{where} states a count of courses, paths, or capstones; the atlas"
            " derives every count from the curriculum file"
        )
    if _unframed_discovery(bare) if framed_discovery else _DISCOVERY.search(bare):
        found.append(
            f"{where} says 'discover' outside a reference; the journey never"
            " presents a result, least of all an AI result, as a discovery"
        )
    return found + _reference_problems(where, value, curriculum, sequences, terms)


def _texts_problems(
    where: str,
    items: object,
    curriculum: Curriculum,
    sequences: Collection[str],
    terms: Collection[str],
) -> list[str]:
    if not isinstance(items, list) or not items:
        return [f"{where} is not a non-empty list of texts"]
    found = []
    for number, item in enumerate(items, start=1):
        found += _journey_text_problems(
            f"{where} {number}", item, curriculum, sequences, terms
        )
    return found


def journey_problems(
    data: object, curriculum: Curriculum, terms: Collection[str] = ()
) -> list[str]:
    """Every rule of the journey file that ``data`` breaks: a mapping of the
    six sections of prose and ``evidence``, no field more, none less; each
    section a non-empty list of texts; ``evidence`` a mapping of exactly the
    three kinds, each a non-empty list of texts; every text inline Markdown,
    one paragraph, without a count of lessons, slots, courses, paths, or
    capstones, without a lesson named outside a reference, and without
    "discover"; every reference resolves."""
    where = JOURNEY_FILE
    if not isinstance(data, dict):
        return [f"{where} is not a mapping of the sections of the journey"]
    found = []
    if unknown := set(data) - FIELDS:
        found.append(
            f"{where} has fields outside the schema: "
            + ", ".join(sorted(map(str, unknown)))
            + " (the journey holds prose and references only)"
        )
    if missing := FIELDS - set(data):
        found.append(f"{where} lacks {', '.join(sorted(missing))}")
    try:
        sequences = sequence_ids(curriculum)
    except ValueError as error:
        return [*found, str(error)]
    for key, _ in SECTIONS:
        if key in data:
            found += _texts_problems(
                f"{where}: {key}", data[key], curriculum, sequences, terms
            )
    if "evidence" in data:
        evidence = data["evidence"]
        kinds = {key for key, _ in EVIDENCE}
        if not isinstance(evidence, dict):
            found.append(
                f"{where}: evidence is not a mapping of the three kinds"
                f" ({', '.join(key for key, _ in EVIDENCE)})"
            )
        else:
            if set(evidence) != kinds:
                found.append(
                    f"{where}: evidence holds {', '.join(sorted(map(str, evidence)))};"
                    f" it holds exactly {', '.join(key for key, _ in EVIDENCE)}"
                )
            for key, _ in EVIDENCE:
                if key in evidence:
                    found += _texts_problems(
                        f"{where}: evidence {key}",
                        evidence[key],
                        curriculum,
                        sequences,
                        terms,
                    )
    return found


def _texts(items: list[str]) -> tuple[str, ...]:
    return tuple(" ".join(text.split()) for text in items)


@dataclass(frozen=True)
class Journey:
    """The validated text of the learning journey."""

    sections: dict[str, tuple[str, ...]]
    evidence: dict[str, tuple[str, ...]]

    @classmethod
    def parse(
        cls, data: object, curriculum: Curriculum, terms: Collection[str] = ()
    ) -> Journey:
        found = journey_problems(data, curriculum, terms)
        if found:
            raise ValueError(
                "the learning journey breaks its rules:\n"
                + "\n".join(f"  {message}" for message in found)
            )
        assert isinstance(data, dict)
        return cls(
            {key: _texts(data[key]) for key, _ in SECTIONS},
            {key: _texts(data["evidence"][key]) for key, _ in EVIDENCE},
        )

    @classmethod
    def read(cls, site: Path, curriculum: Curriculum, glossary: Glossary) -> Journey:
        """Read ``journey.yaml`` of the website project ``site``. Raises
        ``ValueError`` when it breaks a rule; a missing file breaks them."""
        file = site / JOURNEY_FILE
        data: object = None
        if file.is_file():
            try:
                data = yaml.safe_load(file.read_text(encoding="utf-8"))
            except yaml.YAMLError as error:
                raise ValueError(f"{JOURNEY_FILE} is not valid YAML: {error}") from None
        terms = tuple(entry.term for entry in glossary.entries)
        return cls.parse(data, curriculum, terms)


@dataclass(frozen=True)
class JourneyContent:
    """The journey on one page: the whole of it at the opening of the atlas,
    the Part A and Part B text on About. No script, no state."""

    atlas: Atlas
    glossary: Glossary
    journey: Journey
    available: frozenset[str]  # the sequences that have an introduction
    page: str

    def inline(self, text: str) -> str:
        """The text with its references replaced by links or text."""
        return References(self.atlas, self.glossary, self.available, self.page).inline(
            text
        )

    def _paragraphs(self, key: str) -> str:
        return "\n\n".join(self.inline(text) for text in self.journey.sections[key])

    def atlas_markdown(self) -> str:
        """The opening of the atlas: one native disclosure, outside the
        exclusive group of the cards, that holds the whole journey. It opens
        with a click, Enter, or Space and needs no script."""
        heading = dict(SECTIONS)
        verify = page_href(self.page, VERIFY_PAGE)
        lines = [
            "```{=html}",
            '<details class="atlas-journey" id="journey">'
            '<summary class="atlas-journey-summary">'
            '<span class="atlas-journey-title">The learning journey</span>'
            '<span class="visually-hidden">: </span>'
            '<span class="atlas-journey-hint">how Part A leads to Part B, and'
            " what counts as evidence</span></summary>",
            "```",
            "",
            "::: {.atlas-journey-body}",
            "",
        ]
        for key, _ in SECTIONS:
            # The two parts open with a rule in the ink of their part in the
            # atlas, which their headings also name in words.
            part = ""
            if key in ("part-a", "part-b"):
                part = f" .journey-part .journey-{key}"
            lines += [
                f"::: {{.journey-section{part}}}",
                "",
                f"## {heading[key]} {{#journey-{key}}}",
                "",
                self._paragraphs(key),
                "",
                ":::",
                "",
            ]
        lines += [
            "::: {.journey-section .journey-evidence}",
            "",
            f"## {EVIDENCE_HEADING} {{#journey-evidence}}",
            "",
        ]
        for key, term in EVIDENCE:
            texts = [self.inline(text) for text in self.journey.evidence[key]]
            lines += [term, ":   " + "\n\n    ".join(texts), ""]
        lines += [
            f"[How we verify the science]({verify}) shows each kind on a claim of"
            " a published lesson.",
            "",
            ":::",
            "",
            ":::",
            "",
            "```{=html}",
            "</details>",
            "```",
        ]
        return "\n".join(lines)

    def about_markdown(self) -> str:
        """The Part A and Part B text of About, with the courses and the
        method paths that the curriculum file names, and the relation."""
        heading = dict(SECTIONS)
        courses = "\n".join(f"- {course.title}" for course in COURSES)
        paths = "\n".join(
            f"- {method_path.title}" for method_path in self.atlas.path.curriculum.paths
        )
        atlas = page_href(self.page, PATH_PAGE)
        return (
            "\n\n".join(
                [
                    f"### {heading['part-a']} {{#part-a}}",
                    self._paragraphs("part-a"),
                    "The courses of Part A:",
                    courses,
                    f"### {heading['part-b']} {{#part-b}}",
                    self._paragraphs("part-b"),
                    "The method paths of Part B:",
                    paths,
                    f"### {heading['relation']} {{#part-a-to-part-b}}",
                    self._paragraphs("relation"),
                    f"The [Course Atlas]({atlas}) shows every course, path,"
                    " and lesson.",
                ]
            )
            + "\n"
        )


def _content(site: Path, atlas: Atlas, page: str) -> JourneyContent:
    glossary = Glossary.read(site)
    journey = Journey.read(site, atlas.path.curriculum, glossary)
    return JourneyContent(atlas, glossary, journey, introduced(site), page)


def atlas_journey(site: Path, atlas: Atlas, page: str = PATH_PAGE) -> JourneyContent:
    """The journey on the atlas page being built (``course_atlas``)."""
    return _content(site, atlas, page)


def about_journey() -> str:
    """The Part A and Part B text of About, printed from a cell of
    ``about.qmd`` with ``output: asis``."""
    site = project_root(Path.cwd().resolve())
    return _content(site, Atlas.read(site), ABOUT_PAGE).about_markdown()
