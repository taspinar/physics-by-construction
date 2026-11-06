"""The evidence map: every typed claim of the site with its evidence.

A claim is written in a lesson as ``[text]{.claim type=".." scope=".."
evidence=".."}``. ``evidence`` names what supports it, as one or more words
separated by white space or commas, each of them one of:

- the label of an executed cell of the same lesson (``#| label: ..``);
- the key of an entry of the reference register (``site/references.yaml``);
- the key of a dataset card (``data/registry/<key>.yaml``);
- the name of a Lean theorem of ``lean/PhysicsByConstruction``;
- the name of a recorded agent run of the lesson, ``replay`` for
  ``replay.json`` and ``replay-<agent>`` for ``replay-<agent>.json``.

The evidence page lists every claim with its links, generated from the
lesson sources, so it cannot drift from them. The lesson source checks and
the page build validate with the same code: a claim without evidence, or
with a word that names nothing of the above, is a problem.
"""

import html
import importlib.util
import json
import os
import platform
import re
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from functools import cache
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from pbc.authoring.design import CLAIM_TYPES
from pbc.authoring.repository import REPOSITORY_ROOT, build_commit, repository_url
from pbc.authoring.website import page_href, project_root

EVIDENCE_PAGE = "evidence.qmd"
SITE_DIRECTORY = "site"  # the website project, relative to the root
LESSONS_DIRECTORY = "lessons"
REGISTER_FILE = "references.yaml"
CARDS_DIRECTORY = "data/registry"
LEAN_DIRECTORY = "lean/PhysicsByConstruction"
CLAIM_ID = "claim-{number}"
# What a computed value of the statement is shown as: the page cannot run
# the lesson's code, and the number is in the lesson.
COMPUTED = "…"

_FRONT_MATTER = re.compile(r"\A---\n(.*?\n)(?:---|\.\.\.)[ \t]*\n", re.DOTALL)
# How Quarto recognises the first line of a cell, for any engine.
_ANY_CELL_START = re.compile(r"^(\s*)(```+)\s*\{([A-Za-z][=A-Za-z]*)( *[ ,].*)?\}\s*$")
_CELL_START = re.compile(r"^\s*```+\s*\{python( *[ ,].*)?\}\s*$")
_OPTION_LINE = re.compile(r"\s*#\s*\| ?")
_THEOREM = re.compile(
    r"^\s*(?:(?:private|protected|nonrec)\s+)*(?:theorem|lemma)\s+([^\s:({\[]+)",
    re.MULTILINE,
)
_REPLAY = re.compile(r"replay(-[a-z]+)?")
_SEPARATORS = re.compile(r"[\s,]+")
_MARKDOWN_SPECIAL = re.compile(r"([\\`*_\[\]<>|$~^#&])")
_SEPARATOR_BLOCK = "-" * 72


def markdown_text(text: str) -> str:
    """The text with every character that Markdown would read as markup
    escaped: a claim's scope reads the same on every page that shows it."""
    return _MARKDOWN_SPECIAL.sub(r"\\\1", text)


@dataclass(frozen=True)
class Claim:
    """A claim as written in a lesson."""

    page: str  # the lesson page, relative to the website project
    number: int  # position among the claims of the page, from 1
    type: str
    scope: str
    statement: str  # Markdown; computed values are shown as COMPUTED
    evidence: tuple[str, ...]

    @property
    def anchor(self) -> str:
        return CLAIM_ID.format(number=self.number)

    @property
    def row(self) -> str:
        """The identifier of the claim's row on the evidence page: the strand,
        the lesson's directory, and the claim's anchor."""
        lesson = PurePosixPath(self.page).parent
        return f"{lesson.parent.name}-{lesson.name}-{self.anchor}"


@dataclass(frozen=True)
class Source:
    """Evidence found: what kind it is, its name, and where it is."""

    kind: str  # "cell", "reference", "card", "theorem", or "replay"
    name: str
    href: str


@dataclass(frozen=True)
class Problem:
    page: str
    message: str


# --- Reading the claims of a lesson -------------------------------------------


def _body(text: str) -> str:
    match = _FRONT_MATTER.match(text)
    return text[match.end() :] if match else text


def _plain_fences(text: str) -> str:
    """The body with each cell fence rewritten to a plain code fence, which
    Pandoc reads as a code block and not as inline code."""
    return "\n".join(
        f"{cell.group(1)}{cell.group(2)}"
        if (cell := _ANY_CELL_START.match(line))
        else line
        for line in _body(text).splitlines()
    )


# The directory of the pandoc that ships in the quarto-cli package, by machine.
_PANDOC_DIRECTORIES = {
    "arm64": "aarch64",
    "aarch64": "aarch64",
    "x86_64": "x86_64",
    "AMD64": "x86_64",
}


@cache
def _bundled_pandoc() -> str | None:
    """The pandoc that ships in the ``quarto-cli`` package, or None.

    ``quarto pandoc`` starts Quarto's JavaScript runtime (deno) before it
    starts this program: 0.3 s a call instead of 0.03 s, and deno now and
    then crashes with a segmentation fault. Reading the claims of every
    lesson starts a pandoc for each block, so the program is started directly.
    The package pins its version, as ``quarto`` does.
    """
    directory = _PANDOC_DIRECTORIES.get(platform.machine())
    spec = importlib.util.find_spec("quarto_cli")
    if directory is None or spec is None:
        return None
    for location in spec.submodule_search_locations or ():
        binary = Path(location) / "bin" / "tools" / directory / "pandoc"
        if binary.is_file() and os.access(binary, os.X_OK):
            return str(binary)
    return None


def _pandoc(arguments: list[str], text: str) -> str:
    bundled = _bundled_pandoc()
    command = [bundled] if bundled else ["quarto", "pandoc"]
    result = subprocess.run(
        [*command, *arguments],
        input=text,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pandoc could not read a lesson: {result.stderr}")
    return result.stdout


def _attributes(node: dict[str, Any]) -> dict[str, str]:
    return dict(node["c"][0][2])


def _classes(node: dict[str, Any]) -> list[str]:
    return node["c"][0][1]


def _nodes(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        if "t" in value:
            yield value
        for item in value.values():
            yield from _nodes(item)
    elif isinstance(value, list):
        for item in value:
            yield from _nodes(item)


def _without_computed_values(value: Any) -> Any:
    """Replace each inline expression, ``{python} ..``, by COMPUTED, and each
    span of material marked "not verified" by its text and that remark: the
    page that lists the claim is not a lesson and has no label for it."""
    if isinstance(value, dict):
        if value.get("t") == "Span" and "not-verified" in _classes(value):
            return {
                "t": "Span",
                "c": [
                    ["", [], []],
                    [
                        *_without_computed_values(value["c"][1]),
                        {"t": "Str", "c": " (not verified)"},
                    ],
                ],
            }
        if value.get("t") == "Code" and value["c"][1].lstrip().startswith("{python}"):
            return {"t": "Str", "c": COMPUTED}
        return {key: _without_computed_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_without_computed_values(item) for item in value]
    return value


def read_claims(page: str, text: str) -> list[Claim]:
    """The claims of the lesson ``page``, in the order of the document.

    A claim without a ``type`` is returned with an empty one; ``problems``
    reports it.
    """
    document = json.loads(
        _pandoc(["--from", "markdown", "--to", "json"], _plain_fences(text) + "\n")
    )
    found = [
        node
        for node in _nodes(document["blocks"])
        if node["t"] in ("Span", "Div") and "claim" in _classes(node)
    ]
    if not found:
        return []
    # One pandoc call writes every statement back as Markdown, so that math
    # and emphasis stay what the author wrote.
    blocks: list[dict[str, Any]] = []
    for node in found:
        content = _without_computed_values(node["c"][1])
        blocks += [{"t": "Plain", "c": content}] if node["t"] == "Span" else content
        blocks.append({"t": "HorizontalRule"})
    markdown = _pandoc(
        ["--from", "json", "--to", "markdown-smart", "--wrap=none"],
        json.dumps({**document, "blocks": blocks}),
    )
    statements = [
        " ".join(part.split()) for part in markdown.split(_SEPARATOR_BLOCK + "\n")
    ]
    return [
        Claim(
            page=page,
            number=number,
            type=_attributes(node).get("type", ""),
            scope=" ".join(_attributes(node).get("scope", "").split()),
            statement=statements[number - 1].replace("|", "\\|"),
            evidence=tuple(
                word
                for word in _SEPARATORS.split(_attributes(node).get("evidence", ""))
                if word
            ),
        )
        for number, node in enumerate(found, start=1)
    ]


# --- What a claim can name ----------------------------------------------------


def cell_labels(text: str) -> set[str]:
    """The labels of the executed Python cells of a lesson source."""
    labels: set[str] = set()
    lines = _body(text).splitlines()
    for number, line in enumerate(lines):
        if not _CELL_START.match(line):
            continue
        options = []
        for option in lines[number + 1 :]:
            match = _OPTION_LINE.match(option)
            if match is None:
                break
            options.append(option[match.end() :])
        try:
            loaded = yaml.safe_load("\n".join(options))
        except yaml.YAMLError:
            continue
        if (
            isinstance(loaded, dict)
            and loaded.get("eval", True) is True
            and isinstance(loaded.get("label"), str)
        ):
            labels.add(loaded["label"])
    return labels


def register_entries(site: Path) -> dict[str, str]:
    """The keys of the reference register, with the address of each."""
    try:
        data = yaml.safe_load((site / REGISTER_FILE).read_text(encoding="utf-8"))
        return {str(entry["key"]): str(entry["url"]) for entry in data["references"]}
    # Several exceptions without parentheses are valid from Python 3.14 on
    # (PEP 758), which is the oldest version the project supports
    # (pyproject.toml); the formatter writes this form and rejects the other.
    except OSError, yaml.YAMLError, KeyError, TypeError:
        return {}


def lean_theorems(root: Path) -> dict[str, tuple[str, int]]:
    """The theorems and lemmas of the Lean library: name to file and line."""
    found: dict[str, tuple[str, int]] = {}
    for file in sorted((root / LEAN_DIRECTORY).rglob("*.lean")):
        text = file.read_text(encoding="utf-8")
        for match in _THEOREM.finditer(text):
            line = text.count("\n", 0, match.start(1)) + 1
            found.setdefault(match.group(1), (file.relative_to(root).as_posix(), line))
    return found


class Evidence:
    """Resolves the words of an ``evidence`` attribute against the repository.

    ``root`` is the repository, which holds the Lean library and the dataset
    cards, and the website project is ``root/site`` unless ``site`` says
    otherwise (a build of a copy of the project, ADR 002, determinism).
    Every link is relative to the evidence page, or an absolute address.
    """

    def __init__(
        self,
        root: Path = REPOSITORY_ROOT,
        page: str = EVIDENCE_PAGE,
        site: Path | None = None,
    ):
        self.root = root
        self.site = site or root / "site"
        self.page = page
        self.register = register_entries(self.site)
        self.theorems = lean_theorems(root)
        self._labels: dict[str, set[str]] = {}
        self._commit: str | None = None

    def _labels_of(self, lesson: str) -> set[str]:
        if lesson not in self._labels:
            text = (self.site / lesson).read_text(encoding="utf-8")
            self._labels[lesson] = cell_labels(text)
        return self._labels[lesson]

    def _blob(self, path: str, line: int | None = None) -> str:
        if self._commit is None:
            self._commit = build_commit(self.root).sha or "main"
        commit = self._commit
        fragment = f"#L{line}" if line else ""
        return f"{repository_url()}/blob/{commit}/{path}{fragment}"

    def resolve(self, lesson: str, word: str) -> Source | None:
        """What ``word`` names in the lesson ``lesson``, or None."""
        if word in self._labels_of(lesson):
            return Source("cell", word, page_href(self.page, lesson, word))
        if word in self.register:
            return Source("reference", word, self.register[word])
        card = f"{CARDS_DIRECTORY}/{word}.yaml"
        if (self.root / card).is_file():
            return Source("card", word, self._blob(card))
        if word in self.theorems:
            path, line = self.theorems[word]
            return Source("theorem", word, self._blob(path, line))
        if _REPLAY.fullmatch(word):
            fixture = Path(lesson).parent / f"{word}.json"
            if (self.site / fixture).is_file():
                # The fixture's path in the repository, also when the site
                # built is a copy outside it (the determinism check).
                path = (Path(SITE_DIRECTORY) / fixture).as_posix()
                return Source("replay", word, self._blob(path))
        return None


# --- The check ----------------------------------------------------------------


def lesson_pages(site: Path) -> list[str]:
    """The lesson pages of the website project, relative to it."""
    return sorted(
        file.relative_to(site).as_posix()
        for file in (site / LESSONS_DIRECTORY).glob("*/*/index.qmd")
    )


def read_all(root: Path = REPOSITORY_ROOT, site: Path | None = None) -> list[Claim]:
    site = site or root / "site"
    return [
        claim
        for page in lesson_pages(site)
        for claim in read_claims(page, (site / page).read_text(encoding="utf-8"))
    ]


def problems(
    claims: list[Claim],
    root: Path = REPOSITORY_ROOT,
    page: str = EVIDENCE_PAGE,
    site: Path | None = None,
) -> list[Problem]:
    """Every claim has a type and evidence, and each word of the evidence
    names a cell, a register or card key, a Lean theorem, or a recorded run."""
    evidence = Evidence(root, page, site)
    found: list[Problem] = []
    for claim in claims:
        about = f"claim {claim.number} ({claim.statement[:50]!r})"
        if claim.type not in CLAIM_TYPES:
            found.append(Problem(claim.page, f"{about} has no valid type"))
        if not claim.evidence:
            found.append(
                Problem(
                    claim.page,
                    f"{about} has no 'evidence'; name the cell label, register or"
                    " card key, or Lean theorem that supports it",
                )
            )
        unknown = [w for w in claim.evidence if evidence.resolve(claim.page, w) is None]
        if unknown:
            found.append(
                Problem(
                    claim.page,
                    f"{about} names evidence {', '.join(map(repr, unknown))}, which"
                    " is no executed cell of the lesson, register or card key, Lean"
                    " theorem, or recorded run",
                )
            )
    return found


# --- The page -----------------------------------------------------------------

_KINDS = {
    "cell": "Cell",
    "reference": "Reference",
    "card": "Card",
    "theorem": "Theorem",
    "replay": "Replayed run",
}
_TYPE_NAMES = {kind: kind.replace("-", " ").capitalize() for kind in CLAIM_TYPES}


@dataclass(frozen=True)
class EvidencePage:
    """The content of the evidence page: one table of claims for each lesson
    that makes any, in the order of the learning path. Print it from a cell
    with ``output: asis``."""

    claims: tuple[Claim, ...]
    lessons: tuple[tuple[str, str], ...]  # page and title, in path order
    evidence: Evidence

    def __str__(self) -> str:
        lines: list[str] = []
        for page, title in self.lessons:
            mine = [claim for claim in self.claims if claim.page == page]
            if not mine:
                continue
            caption = f"Claims of {title}, with their evidence."
            # A table wider than the screen scrolls inside its own box, which
            # a keyboard reaches (the box of pbc.authoring.tables).
            lines += [
                f"## {title}",
                "",
                '::: {.table-scroll role="region" tabindex="0"'
                f' aria-label="{html.escape(caption, quote=True)}"}}',
                "",
            ]
            lines += [
                "| Claim | Type | Scope | Evidence |",
                "|:--|:--|:--|:--|",
            ]
            for claim in mine:
                link = page_href(self.evidence.page, page, claim.anchor)
                lines.append(
                    f"| []{{#{claim.row}}}[{claim.statement}]({link})"
                    f" | {_TYPE_NAMES[claim.type]}"
                    f" | {markdown_text(claim.scope) or 'not stated'}"
                    f" | {self._links(claim)} |"
                )
            lines += ["", f": {caption} {{.result-table}}", "", ":::", ""]
        return "\n".join(lines)

    def _links(self, claim: Claim) -> str:
        links = []
        for word in claim.evidence:
            source = self.evidence.resolve(claim.page, word)
            assert source is not None, word
            links.append(f"{_KINDS[source.kind]} [`{source.name}`]({source.href})")
        return "; ".join(links)


def evidence_page() -> EvidencePage:
    """Return the content of the evidence page being built. It raises when a
    claim lacks evidence or names evidence that does not exist, which fails
    the build."""
    from pbc.authoring.path import LearningPath

    site = project_root(Path.cwd().resolve())
    claims = read_all(REPOSITORY_ROOT, site)
    found = problems(claims, REPOSITORY_ROOT, site=site)
    if found:
        raise ValueError(
            "claims without valid evidence:\n"
            + "\n".join(f"  {p.page}: {p.message}" for p in found)
        )
    lessons = tuple(
        (lesson.page, lesson.title) for lesson in LearningPath.read(site).lessons
    )
    return EvidencePage(tuple(claims), lessons, Evidence(REPOSITORY_ROOT, site=site))
