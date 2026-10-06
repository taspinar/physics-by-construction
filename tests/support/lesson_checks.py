"""Checks on the lesson sources (docs/authoring.md describes the format).

Each check takes the root of a repository and returns the violations it
found, so the same code runs on this repository (tests/lessons) and on small
repositories written to violate one rule (tests/integration).

A lesson is ``site/lessons/<strand>/<nn>-<slug>/index.qmd``. Its front matter
is read as YAML. Its body is read through the Pandoc that Quarto ships, so
headings, code blocks, and divs are found where Pandoc finds them and not by
a second Markdown parser.
"""

import functools
import json
import re
import secrets
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from support.site_checks import Violation

# --- The format ---------------------------------------------------------------

SITE = "site"
LESSONS = f"{SITE}/lessons"
PAGE = "index.qmd"
# The one committed recording a lesson directory may hold (ADR 002): the
# replay fixture of an agent lesson.
REPLAY_FIXTURE = "replay.json"

# Strands in learning path order (docs/architecture.md, "Lesson model").
STRANDS = ("mechanics", "agents-llm", "agents-abm", "lean")
DIFFICULTIES = (1, 2, 3)

# Level-2 sections every lesson has, by heading identifier.
REQUIRED_SECTIONS = (
    "assumptions",
    "explanation",
    "code",
    "worked-examples",
    "reproduce-this",
)
# A lesson also has at least one of these.
PRACTICE_SECTIONS = ("exercises", "interactive-visualization")

NOT_VERIFIED = "not-verified"

_ID = re.compile(r"[a-z][a-z0-9]*(-[a-z0-9]+)*")
_LESSON_DIRECTORY = re.compile(r"(\d{2})-[a-z0-9]+(-[a-z0-9]+)*")
_LEAN_MODULE = re.compile(r"PhysicsByConstruction(\.[A-Z][A-Za-z0-9_]*)+")

_FRONT_MATTER_KEYS = {"title", "description", "lesson"}
_LESSON_KEYS = {"id", "strand", "order", "difficulty", "prerequisites"}
_OPTIONAL_LESSON_KEYS = {"lean-modules"}
_PREREQUISITE_KEYS = {"lessons", "outside"}


def lesson_pages(repository: Path) -> list[Path]:
    """Return the page of every lesson directory, in path order."""
    return sorted((repository / LESSONS).rglob(PAGE))


def _name(repository: Path, path: Path) -> str:
    return path.relative_to(repository).as_posix()


# --- Reading a lesson ---------------------------------------------------------

# How Quarto recognises the first line of an executable cell
# (breakQuartoMd, startCodeCellRegEx). A language that starts with '=' is a
# raw block, not a cell.
_CELL_START = re.compile(r"^(\s*)(```+)\s*\{([A-Za-z][=A-Za-z]*)( *[ ,].*)?\}\s*$")
# How Quarto recognises an option line at the top of a {python} cell
# (nb_cell_yaml_lines in its notebook.py, which decides whether the cell
# runs): '#|', and also '# |' with any white space in between.
_OPTION_LINE = re.compile(r"#\s*\| ?")
_FRONT_MATTER = re.compile(r"\A---\n(.*?\n)(?:---|\.\.\.)[ \t]*\n", re.DOTALL)
# Shortcodes that bring in content from another file: text and code the
# checks would not see, or stored outputs of a notebook.
_INCLUDE = re.compile(r"\{\{<\s*(include|embed)\b")


@dataclass(frozen=True)
class Cell:
    """An executable cell, as Pandoc sees it after the fence is rewritten."""

    engine: str
    inline_options: bool
    code: str

    @property
    def options(self) -> dict[str, Any]:
        """The ``#|`` options at the top of the cell."""
        lines = []
        for line in self.code.splitlines():
            option = _OPTION_LINE.match(line)
            if option is None:
                break
            lines.append(line[option.end() :])
        try:
            options = yaml.safe_load("\n".join(lines))
        except yaml.YAMLError:
            return {}
        return options if isinstance(options, dict) else {}

    @property
    def executed(self) -> bool:
        return self.engine == "python" and self.options.get("eval", True) is True


@dataclass(frozen=True)
class Lesson:
    front_matter: Any  # parsed YAML; None when there is none
    front_matter_error: str
    blocks: list[dict[str, Any]]  # Pandoc blocks of the body
    includes: tuple[str, ...]  # include and embed shortcodes
    _marker: str

    def cell(self, node: dict[str, Any]) -> Cell | None:
        """Return the cell that code block ``node`` is, or None."""
        if node["t"] != "CodeBlock":
            return None
        (_, classes, attributes), code = node["c"]
        if self._marker not in classes:
            return None
        values = dict(attributes)
        return Cell(values["engine"], values["inline-options"] == "yes", code)


def _pandoc_blocks(markdown: str) -> list[dict[str, Any]]:
    result = subprocess.run(
        ["quarto", "pandoc", "--from", "markdown", "--to", "json"],
        input=markdown,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pandoc could not read a lesson: {result.stderr}")
    return json.loads(result.stdout)["blocks"]


@functools.cache
def _read(text: str) -> Lesson:
    front_matter, error = None, ""
    match = _FRONT_MATTER.match(text)
    body = text
    if match is None:
        error = "the page does not start with YAML front matter between '---' lines"
    else:
        body = text[match.end() :]
        try:
            front_matter = yaml.safe_load(match.group(1))
        except yaml.YAMLError as problem:
            error = f"front matter is not valid YAML: {problem}"

    # Pandoc does not know Quarto's cell fences. Rewrite each one, the way
    # Quarto finds them, into a fence Pandoc reads as a code block carrying
    # a class no author can have written.
    marker = f"cell-{secrets.token_hex(8)}"
    lines = []
    for line in body.splitlines():
        cell = _CELL_START.match(line)
        if cell is not None:
            indent, fence, engine, options = cell.groups()
            line = (
                f'{indent}{fence}{{.{marker} engine="{engine}"'
                f' inline-options="{"yes" if options else "no"}"}}'
            )
        lines.append(line)
    return Lesson(
        front_matter=front_matter,
        front_matter_error=error,
        blocks=_pandoc_blocks("\n".join(lines) + "\n"),
        includes=tuple(found.group(0) for found in _INCLUDE.finditer(body)),
        _marker=marker,
    )


def read_lesson(page: Path) -> Lesson:
    return _read(page.read_text(encoding="utf-8"))


Node = dict[str, Any]


def _walk(value: Any, ancestors: tuple[Node, ...] = ()) -> Iterator[tuple[Node, ...]]:
    """Yield every node below ``value`` as the path of nodes leading to it."""
    if isinstance(value, dict):
        if "t" in value:
            path = (*ancestors, value)
            yield path
            yield from _walk(value.get("c"), path)
        else:
            for item in value.values():
                yield from _walk(item, ancestors)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item, ancestors)


def _attributes(node: Node) -> tuple[str, list[str]]:
    """Return the identifier and classes of ``node``; empty when it has none."""
    if node["t"] in ("Div", "Span", "CodeBlock", "Code", "Figure"):
        identifier, classes, _ = node["c"][0]
        return identifier, classes
    if node["t"] == "Header":
        identifier, classes, _ = node["c"][1]
        return identifier, classes
    return "", []


def _has_class(node: Node, name: str) -> bool:
    return node["t"] in ("Div", "Span") and name in _attributes(node)[1]


def _marked_not_verified(path: tuple[Node, ...]) -> bool:
    return any(_has_class(node, NOT_VERIFIED) for node in path[:-1])


def _sections(lesson: Lesson) -> dict[str, list[Node]]:
    """Return the blocks of each level-2 section, by heading identifier."""
    sections: dict[str, list[Node]] = {}
    current: list[Node] | None = None
    for block in lesson.blocks:
        if block["t"] == "Header" and block["c"][0] <= 2:
            current = None
            if block["c"][0] == 2:
                current = sections.setdefault(_attributes(block)[0], [])
        elif current is not None:
            current.append(block)
    return sections


# --- Front matter -------------------------------------------------------------


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _text_list(value: Any) -> bool:
    return isinstance(value, list) and all(_is_text(item) for item in value)


def _metadata_problems(front_matter: Any, strand: str, directory: str) -> list[str]:
    if not isinstance(front_matter, dict):
        return ["front matter is not a mapping"]
    problems = [
        f"front matter key '{key}' is not part of the lesson format"
        for key in sorted(set(front_matter) - _FRONT_MATTER_KEYS, key=str)
    ]
    if not _is_text(front_matter.get("title")):
        problems.append("front matter has no 'title'")
    if "description" in front_matter and not _is_text(front_matter["description"]):
        problems.append("'description' is not a text")

    lesson = front_matter.get("lesson")
    if not isinstance(lesson, dict):
        return [*problems, "front matter has no 'lesson' mapping"]
    problems += [
        f"front matter has no 'lesson.{key}'"
        for key in sorted(_LESSON_KEYS - set(lesson))
    ]
    problems += [
        f"'lesson.{key}' is not part of the lesson format"
        for key in sorted(set(lesson) - _LESSON_KEYS - _OPTIONAL_LESSON_KEYS, key=str)
    ]

    if "id" in lesson and not (
        isinstance(lesson["id"], str) and _ID.fullmatch(lesson["id"])
    ):
        problems.append(
            "'lesson.id' must be lowercase words joined by '-', starting with a letter"
        )
    if "strand" in lesson:
        if lesson["strand"] not in STRANDS:
            problems.append(f"'lesson.strand' must be one of {', '.join(STRANDS)}")
        elif lesson["strand"] != strand:
            problems.append(
                f"'lesson.strand' is {lesson['strand']!r}, but the lesson is in"
                f" the directory of strand {strand!r}"
            )
    if "order" in lesson:
        prefix = _LESSON_DIRECTORY.fullmatch(directory)
        if not (_is_integer(lesson["order"]) and 1 <= lesson["order"] <= 99):
            problems.append("'lesson.order' must be a whole number from 1 to 99")
        elif prefix is not None and int(prefix.group(1)) != lesson["order"]:
            problems.append(
                f"'lesson.order' is {lesson['order']}, but the directory name"
                f" starts with {prefix.group(1)}"
            )
    if "difficulty" in lesson and not (
        _is_integer(lesson["difficulty"]) and lesson["difficulty"] in DIFFICULTIES
    ):
        problems.append(
            f"'lesson.difficulty' must be one of {', '.join(map(str, DIFFICULTIES))}"
        )
    if "prerequisites" in lesson:
        prerequisites = lesson["prerequisites"]
        if not (
            isinstance(prerequisites, dict)
            and set(prerequisites) == _PREREQUISITE_KEYS
            and _text_list(prerequisites["lessons"])
            and _text_list(prerequisites["outside"])
        ):
            problems.append(
                "'lesson.prerequisites' must hold the lists 'lessons' (lesson"
                " ids) and 'outside' (texts), and nothing else"
            )
        else:
            problems += [
                f"prerequisite {entry!r} is not a lesson id"
                for entry in prerequisites["lessons"]
                if not _ID.fullmatch(entry)
            ]
            if lesson.get("id") in prerequisites["lessons"]:
                problems.append("the lesson lists itself as a prerequisite")
    if "lean-modules" in lesson and not (
        _text_list(lesson["lean-modules"])
        and all(_LEAN_MODULE.fullmatch(module) for module in lesson["lean-modules"])
    ):
        problems.append(
            "'lesson.lean-modules' must be a list of module names such as"
            " PhysicsByConstruction.Mechanics.Kinematics"
        )
    return problems


def check_metadata(repository: Path) -> list[Violation]:
    """Every lesson has front matter that follows the schema, and its strand
    and order agree with the directory it is in."""
    violations = []
    for page in lesson_pages(repository):
        lesson = read_lesson(page)
        if lesson.front_matter_error:
            problems = [lesson.front_matter_error]
        else:
            problems = _metadata_problems(
                lesson.front_matter, page.parent.parent.name, page.parent.name
            )
        violations += [
            Violation("metadata", _name(repository, page), problem)
            for problem in problems
        ]
    return violations


# --- Sections -----------------------------------------------------------------


def _divs(blocks: list[Node], name: str) -> list[tuple[Node, ...]]:
    return [path for path in _walk(blocks) if _has_class(path[-1], name)]


def check_sections(repository: Path) -> list[Violation]:
    """Every lesson has the required sections with content, exercises come
    with solutions, and "Reproduce this" is produced by its helper."""
    violations = []
    for page in lesson_pages(repository):
        lesson = read_lesson(page)
        sections = _sections(lesson)
        problems = [
            f"no level-2 section with the identifier '{name}'"
            for name in REQUIRED_SECTIONS
            if name not in sections
        ]
        if not any(name in sections for name in PRACTICE_SECTIONS):
            problems.append(
                "no level-2 section with the identifier"
                f" '{"' or '".join(PRACTICE_SECTIONS)}'"
            )
        problems += [
            f"section '{name}' is empty"
            for name in (*REQUIRED_SECTIONS, *PRACTICE_SECTIONS)
            if name in sections and not sections[name]
        ]

        if sections.get("exercises"):
            exercises = _divs(sections["exercises"], "exercise")
            if not exercises:
                problems.append("section 'exercises' holds no '.exercise' div")
            problems += [
                f"exercise {number} has no '.solution' div"
                for number, path in enumerate(exercises, start=1)
                if not _divs(path[-1]["c"][1], "solution")
            ]
        problems += [
            "a '.solution' div is outside an '.exercise' div"
            for path in _divs(lesson.blocks, "solution")
            if not any(_has_class(node, "exercise") for node in path[:-1])
        ]

        if sections.get("reproduce-this") and not any(
            (cell := lesson.cell(path[-1])) is not None
            and cell.executed
            and "reproduce_this(" in cell.code
            for path in _walk(sections["reproduce-this"])
        ):
            problems.append(
                "section 'reproduce-this' has no executed cell that calls"
                " reproduce_this()"
            )
        violations += [
            Violation("sections", _name(repository, page), problem)
            for problem in problems
        ]
    return violations


# --- Displayed code -----------------------------------------------------------

# A cell runs where Quarto finds its fence: at the top level of the page, in
# a div, or in a list item.
_CELL_CONTAINERS = {"Div", "BulletList", "OrderedList"}
# Options that would make the build show code without running it.
_EXECUTION_SWITCHES = {"eval": True, "enabled": True, "freeze": False, "cache": False}


def _first_line(code: str) -> str:
    lines = [line for line in code.splitlines() if line.strip()]
    return (lines[0].strip() if lines else "")[:60]


def _code_problems(lesson: Lesson) -> Iterator[tuple[str, str]]:
    for path in _walk(lesson.blocks):
        node = path[-1]
        marked = _marked_not_verified(path)
        cell = lesson.cell(node)
        if cell is not None:
            where = f"cell '{_first_line(cell.code)}'"
            if cell.engine != "python":
                yield (
                    "cell-form",
                    f"{where} is a {{{cell.engine}}} cell; the build executes"
                    " only {python} cells",
                )
            elif cell.inline_options:
                yield (
                    "cell-form",
                    f"{where} has options in its fence; write them as '#|' lines",
                )
            elif any(parent["t"] not in _CELL_CONTAINERS for parent in path[:-1]):
                yield (
                    "cell-form",
                    f"{where} is inside a {path[-2]['t']}; a cell belongs at the"
                    " top level of the page, in a div, or in a list item",
                )
            elif not cell.executed and not marked:
                yield (
                    "unverified-code",
                    f"{where} is not executed (eval) and has no"
                    f" '.{NOT_VERIFIED}' marker",
                )
        elif node["t"] == "CodeBlock" and not marked:
            yield (
                "unverified-code",
                f"code block '{_first_line(node['c'][1])}' is not executed and"
                f" has no '.{NOT_VERIFIED}' marker",
            )
        elif (
            node["t"] in ("RawBlock", "RawInline")
            and re.search(r"<pre\b", node["c"][1], re.IGNORECASE)
            and not marked
        ):
            yield (
                "unverified-code",
                f"raw HTML listing has no '.{NOT_VERIFIED}' marker",
            )
    for shortcode in lesson.includes:
        yield (
            "unverified-code",
            f"'{shortcode} ...' brings in content from another file; a lesson"
            " is one page",
        )


def _execution_problems(site: Path) -> list[str]:
    config = yaml.safe_load((site / "_quarto.yml").read_text(encoding="utf-8")) or {}
    execute = config.get("execute") or {}
    return [
        f"execute.{option} is {execute[option]!r}: pages would be shown without"
        " being executed"
        for option, required in _EXECUTION_SWITCHES.items()
        if option in execute and execute[option] is not required
    ]


def check_displayed_code(repository: Path) -> list[Violation]:
    """Code a lesson displays is an executed {python} cell or carries the
    "not verified" marker, and the site configuration executes every page.

    By-reference excerpts are the output of executed cells, so they need no
    rule here; the built-site checks compare them with their source.
    """
    violations = [
        Violation("execution-disabled", f"{SITE}/_quarto.yml", problem)
        for problem in _execution_problems(repository / SITE)
    ]
    for page in lesson_pages(repository):
        violations += [
            Violation(rule, _name(repository, page), problem)
            for rule, problem in _code_problems(read_lesson(page))
        ]
    return violations


# --- Figures ------------------------------------------------------------------


def check_figures(repository: Path) -> list[Violation]:
    """Figures are drawn by executed cells and have alternative text.

    A cell declares a figure with a ``fig-`` label or a caption. An image
    that a cell produces without declaring it has no alternative text in the
    built page, which the built-site checks report.
    """
    violations = []
    for page in lesson_pages(repository):
        name = _name(repository, page)
        lesson = read_lesson(page)
        for path in _walk(lesson.blocks):
            node = path[-1]
            cell = lesson.cell(node)
            if cell is not None:
                options = cell.options
                label = str(options.get("label", ""))
                declared = label.startswith("fig-") or "fig-cap" in options
                alt = options.get("fig-alt")
                texts = alt if isinstance(alt, list) else [alt]
                if declared and not all(_is_text(text) for text in texts):
                    violations.append(
                        Violation(
                            "figure-alt",
                            name,
                            f"figure cell '{label or _first_line(cell.code)}' has"
                            " no 'fig-alt' text",
                        )
                    )
            elif node["t"] == "Image" or (
                node["t"] in ("RawBlock", "RawInline")
                and re.search(r"<img\b", node["c"][1], re.IGNORECASE)
            ):
                violations.append(
                    Violation(
                        "figure-source",
                        name,
                        "image file in the page; a figure is drawn by an executed cell",
                    )
                )
    return violations


# --- Committed files ----------------------------------------------------------

# Directories that only a build or an execution writes.
_GENERATED_DIRECTORIES = {
    "_site",
    "_freeze",
    ".quarto",
    ".jupyter_cache",
    ".ipynb_checkpoints",
}
_GENERATED_DIRECTORY_SUFFIXES = ("_files", "_cache")
# File types of rendered pages, executed notebooks, figures, and stored
# results. Under the site sources and the package, nothing of these types is
# written by hand.
_GENERATED_SUFFIXES = {
    "rendered page": {".html", ".htm"},
    "notebook with stored outputs": {".ipynb", ".quarto_ipynb"},
    "figure": {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".webp",
        ".avif",
        ".bmp",
        ".tif",
        ".tiff",
        ".pdf",
        ".eps",
        ".ps",
        ".mp4",
        ".webm",
    },
    "stored output": {
        ".json",
        ".jsonl",
        ".csv",
        ".tsv",
        ".npy",
        ".npz",
        ".pkl",
        ".pickle",
        ".h5",
        ".hdf5",
        ".parquet",
        ".feather",
        ".mat",
        ".dat",
        ".out",
        ".log",
    },
}
# Where pages take their content from.
_SOURCE_TREES = (SITE, "src")


def _generated(path: Path) -> str | None:
    """Return what kind of generated artifact ``path`` is, or None."""
    for directory in path.parts[:-1]:
        if directory in _GENERATED_DIRECTORIES or directory.endswith(
            _GENERATED_DIRECTORY_SUFFIXES
        ):
            return "build or execution output"
    for kind, suffixes in _GENERATED_SUFFIXES.items():
        if path.suffix.lower() in suffixes:
            return kind
    return None


def _lesson_file(path: Path) -> bool:
    """Whether ``path`` is a file a lesson directory may hold."""
    parts = path.parts
    return (
        len(parts) == 5
        and parts[2] in STRANDS
        and _LESSON_DIRECTORY.fullmatch(parts[3]) is not None
        and parts[4] in (PAGE, REPLAY_FIXTURE)
    )


def committed_files(repository: Path) -> list[Path]:
    """Return the files Git tracks or would add: everything it does not
    ignore, relative to the repository root."""
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=repository,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"cannot list the files of {repository}: {result.stderr}")
    return sorted(
        Path(name)
        for name in result.stdout.split("\0")
        if name and (repository / name).is_file()
    )


def check_committed_files(repository: Path) -> list[Violation]:
    """No generated artifact is committed, and a lesson directory holds only
    its page and, for an agent lesson, its replay fixture.

    The replay fixture is exempt by its location alone (ADR 002): it is the
    file ``replay.json`` next to the page of a lesson.
    """
    violations = []
    for path in committed_files(repository):
        if path.parts[0] not in _SOURCE_TREES:
            continue
        in_lessons = path.parts[:2] == Path(LESSONS).parts
        if in_lessons and _lesson_file(path):
            continue
        kind = _generated(path)
        if kind is not None:
            violations.append(
                Violation(
                    "committed-artifact",
                    path.as_posix(),
                    f"{kind}; it is regenerated by every build and never committed",
                )
            )
        elif in_lessons:
            violations.append(
                Violation(
                    "lesson-layout",
                    path.as_posix(),
                    f"not part of a lesson; {LESSONS} holds only"
                    f" <strand>/<nn>-<slug>/{PAGE} and, for an agent lesson,"
                    f" {REPLAY_FIXTURE} next to it",
                )
            )
    return violations
