"""The glossary and the "Before you begin" block of a lesson.

``site/glossary.yaml`` defines the assumed vocabulary. A lesson lists what it
assumes in ``prerequisites.outside`` as ``"Term: what exactly"``, and the text
before the colon is the ``term`` of a glossary entry. The glossary page lists
every entry with the lessons that assume it, and the header of a lesson links
each of its outside prerequisites to its entry. Both are generated from the
lesson front matter, so they cannot drift from the lessons. The lesson source
checks validate with the same code.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import yaml

from pbc.authoring.website import page_href, project_root

GLOSSARY_FILE = "glossary.yaml"
GLOSSARY_PAGE = "glossary.qmd"
SENTENCES_RANGE = (1, 3)

_SENTENCE_END = re.compile(r"[.!?](?=\s|$)")


@dataclass(frozen=True)
class Entry:
    term: str
    definition: str
    see: str  # id of the lesson that explains the term; "" when none does

    @property
    def anchor(self) -> str:
        return re.sub(r"[^a-z0-9]+", "-", self.term.lower()).strip("-")


def split_outside(text: str) -> tuple[str, str]:
    """Split an outside prerequisite into its term and the detail after the
    colon ("" when there is none)."""
    term, _, detail = text.partition(":")
    return term.strip(), detail.strip()


def sentences(text: str) -> int:
    return len(_SENTENCE_END.findall(text))


def problems(entries: Iterable[Entry]) -> list[str]:
    """What is wrong with the glossary entries themselves."""
    found: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        if not entry.term or ":" in entry.term:
            found.append(f"entry {entry.term!r}: a term is not empty and has no colon")
        if entry.anchor in seen:
            found.append(f"term {entry.term!r} appears twice")
        seen.add(entry.anchor)
        low, high = SENTENCES_RANGE
        if not low <= sentences(entry.definition) <= high:
            found.append(
                f"entry {entry.term!r}: the definition has"
                f" {sentences(entry.definition)} sentences; an entry has"
                f" {low} to {high}"
            )
    return found


@dataclass(frozen=True)
class Glossary:
    entries: tuple[Entry, ...]

    @classmethod
    def read(cls, site: Path) -> Glossary:
        """Read ``glossary.yaml`` of the website project ``site``."""
        try:
            raw = yaml.safe_load((site / GLOSSARY_FILE).read_text(encoding="utf-8"))
            entries = tuple(
                Entry(
                    term=str(item["term"]),
                    definition=" ".join(str(item["definition"]).split()),
                    see=str(item.get("see") or ""),
                )
                for item in raw["entries"]
            )
        except (OSError, yaml.YAMLError, KeyError, TypeError) as error:
            raise ValueError(
                f"{GLOSSARY_FILE} does not follow its format: {error}"
            ) from None
        return cls(tuple(sorted(entries, key=lambda entry: entry.term.lower())))

    def entry(self, outside: str) -> Entry | None:
        """The entry that the outside prerequisite ``outside`` names."""
        term = split_outside(outside)[0]
        return next((entry for entry in self.entries if entry.term == term), None)

    def unresolved(self, outside: Iterable[str]) -> list[str]:
        return [text for text in outside if self.entry(text) is None]


def before_you_begin(from_page: str, glossary: Glossary, outside: Iterable[str]) -> str:
    """The "Before you begin" list of the lesson page ``from_page``: each
    outside prerequisite with its detail, the term linked to its entry."""
    items = []
    for text in outside:
        entry = glossary.entry(text)
        term, detail = split_outside(text)
        if entry is None:
            items.append(f"- {text}")
            continue
        link = f"[{term}]({page_href(from_page, GLOSSARY_PAGE, entry.anchor)})"
        items.append(f"- {link}: {detail}" if detail else f"- {link}")
    return "\n".join(items)


@dataclass(frozen=True)
class GlossaryPage:
    """The content of the glossary page: one section per entry, with its
    definition, the lesson that explains it when there is one, and the
    lessons that assume it. Print it from a cell with ``output: asis``."""

    glossary: Glossary
    path: object  # pbc.authoring.path.LearningPath
    page: str

    def __str__(self) -> str:
        lines: list[str] = []
        for entry in self.glossary.entries:
            lines += [f"## {entry.term} {{#{entry.anchor}}}", "", entry.definition, ""]
            if entry.see:
                target = self.path.lesson(entry.see)
                lines += [
                    f"Explained in [{target.title}]"
                    f"({page_href(self.page, target.page)}).",
                    "",
                ]
            users = [
                lesson
                for lesson in self.path.lessons
                if any(split_outside(text)[0] == entry.term for text in lesson.outside)
            ]
            links = ", ".join(
                f"[{lesson.title}]({page_href(self.page, lesson.page)})"
                for lesson in users
            )
            lines += [f"Assumed in: {links}.", ""] if users else []
        return "\n".join(lines)


def glossary_page() -> GlossaryPage:
    """Return the content of the glossary page being built."""
    from pbc.authoring.path import LearningPath

    site = project_root(Path.cwd().resolve())
    return GlossaryPage(Glossary.read(site), LearningPath.read(site), GLOSSARY_PAGE)
