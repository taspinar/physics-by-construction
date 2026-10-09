"""Display the source of a function or class of ``pbc`` by reference."""

import html
import inspect
import re
from collections.abc import Mapping
from dataclasses import dataclass
from numbers import Real
from pathlib import Path

from pbc.authoring.repository import (
    REPOSITORY_ROOT,
    BuildCommit,
    build_commit,
    repository_url,
)

# A number written into a note, outside a ``{placeholder}`` and outside a
# word such as ``x2``.
_LITERAL_NUMBER = re.compile(r"(?<![\w.])\d")
_PLACEHOLDER = re.compile(r"\{[^{}]*\}")
_UNIT = re.compile(r"``(\w+)``\s*\(([^()]*)\)")


@dataclass(frozen=True)
class Note:
    """A note on one line of an excerpt."""

    line: int  # file line number
    code: str  # the line, without indentation: what the note is anchored to
    text: str  # the note, plain text, with its computed numbers filled in


@dataclass(frozen=True)
class Parameter:
    """One row of the interface table."""

    name: str
    kind: str  # "input" or "output"
    type: str
    unit: str


@dataclass(frozen=True)
class Excerpt:
    """The source text of one object, or of a part of it, with where it was
    read from.

    As the result of a code cell it renders as a highlighted listing followed
    by the file and lines it came from. With notes it renders as a listing
    with marked lines and a numbered list of notes in the page text; with an
    interface, a table of inputs and outputs comes first.
    """

    name: str  # "<module>:<object>", for example "pbc.sample:damped_oscillation"
    source: str  # the text shown, exactly as in the file
    path: str  # file, relative to the repository root
    first_line: int  # of the text shown
    last_line: int
    commit: BuildCommit
    repository: str
    region: str | None = None  # name of the region of the object that is shown
    lines: tuple[int, int] | None = None  # first and last line of the object shown
    notes: tuple[Note, ...] = ()
    interface: tuple[Parameter, ...] = ()

    def _attributes(self) -> str:
        shown = f'source="{self.name}"'
        if self.region is not None:
            shown += f' region="{self.region}"'
        if self.lines is not None:
            shown += f' lines="{self.lines[0]}-{self.lines[1]}"'
        return shown

    def _location(self) -> str:
        if self.first_line == self.last_line:
            where = f"`{self.path}`, line {self.first_line}"
        else:
            where = f"`{self.path}`, lines {self.first_line} to {self.last_line}"
        if self.commit.sha is not None:
            where = (
                f"[{where}]({self.repository}/blob/{self.commit.sha}/{self.path}"
                f"#L{self.first_line}-L{self.last_line})"
            )
        return where

    def _interface_table(self) -> str:
        if not self.interface:
            return ""
        rows = "".join(
            f"| `{p.name}` | {p.kind} | {_cell(p.type)} | {_cell(p.unit)} |\n"
            for p in self.interface
        )
        object_name = self.name.partition(":")[2]
        return (
            "| Name | Kind | Type | Unit |\n|:--|:--|:--|:--|\n"
            f"{rows}\n: Inputs and outputs of `{object_name}`.\n\n"
        )

    def _listing(self) -> str:
        if not self.notes:
            longest_run = max(
                (len(run) for run in re.findall(r"`+", self.source)), default=0
            )
            fence = "`" * max(3, longest_run + 1)
            return (
                f"{fence}{{.python {self._attributes()}}}\n"
                f"{self.source.rstrip()}\n"
                f"{fence}\n\n"
            )
        marked = {note.line: index for index, note in enumerate(self.notes, 1)}
        spans = "\n".join(
            f'<span class="line{" marked" if number in marked else ""}"'
            f' data-line="{number}"'
            + (f' data-note="{marked[number]}"' if number in marked else "")
            + f">{html.escape(text)}</span>"
            for number, text in enumerate(
                self.source.rstrip("\n").split("\n"), self.first_line
            )
        )
        attributes = f'data-source="{html.escape(self.name)}"'
        if self.region is not None:
            attributes += f' data-region="{html.escape(self.region)}"'
        if self.lines is not None:
            attributes += f' data-lines="{self.lines[0]}-{self.lines[1]}"'
        items = "\n".join(
            f'<li data-anchor="{html.escape(note.code)}">'
            f"Line {note.line}, <code>{html.escape(note.code)}</code>: "
            f"{html.escape(note.text)}</li>"
            for note in self.notes
        )
        return (
            "```{=html}\n"
            f'<pre class="excerpt-listing" tabindex="0" {attributes}>'
            f'<code class="language-python">{spans}\n</code></pre>\n'
            f'<ol class="excerpt-notes">\n{items}\n</ol>\n'
            "```\n\n"
        )

    def _repr_markdown_(self) -> str:
        return (
            "::: {.excerpt}\n"
            f"{self._interface_table()}"
            f"{self._listing()}"
            "::: {.excerpt-source}\n"
            f"{self._location()}, read from the repository when this page was"
            " built.\n"
            ":::\n"
            ":::\n"
        )


def _cell(text: str) -> str:
    return text.replace("|", "\\|") if text else "not stated"


def select(
    object_lines: list[str],
    lines: tuple[int, int] | None,
    region: str | None,
) -> tuple[int, list[str]]:
    """Return the index of the first line shown and the lines shown, out of
    the lines of one object. The whole object when neither is given."""
    if lines is not None and region is not None:
        raise ValueError("give lines or region, not both")
    if lines is not None:
        first, last = lines
        if not 1 <= first <= last <= len(object_lines):
            raise ValueError(
                f"lines {first} to {last} are not within the {len(object_lines)}"
                " lines of the object"
            )
        return first - 1, object_lines[first - 1 : last]
    if region is not None:
        starts = [
            i for i, t in enumerate(object_lines) if t.strip() == f"# region: {region}"
        ]
        ends = [
            i
            for i, t in enumerate(object_lines)
            if t.strip() == f"# endregion: {region}"
        ]
        if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
            raise ValueError(
                f"the object has no region {region!r}: it needs one"
                f" '# region: {region}' line followed by one"
                f" '# endregion: {region}' line"
            )
        return starts[0] + 1, object_lines[starts[0] + 1 : ends[0]]
    return 0, object_lines


def _note_text(template: str, values: Mapping[str, Real]) -> str:
    if _LITERAL_NUMBER.search(_PLACEHOLDER.sub("", template)):
        raise ValueError(
            f"the note {template!r} contains a number; write it as a"
            " {placeholder} and pass the value the build computed in values="
        )
    for key, value in values.items():
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError(f"values[{key!r}] is not a number: {value!r}")
    try:
        return template.format(**values)
    except (KeyError, IndexError, ValueError) as error:
        raise ValueError(
            f"the note {template!r} does not match values: {error!r}"
        ) from None


def _interface(obj: object, name: str) -> tuple[Parameter, ...]:
    documentation = inspect.getdoc(obj) or ""
    units = dict(_UNIT.findall(documentation))
    signature = inspect.signature(obj)  # type: ignore[arg-type]
    rows = [
        Parameter(
            name=parameter.name,
            kind="input",
            type=_annotation(parameter.annotation),
            unit=units.get(parameter.name, ""),
        )
        for parameter in signature.parameters.values()
    ]
    returned = (
        f"an instance of {name}"
        if inspect.isclass(obj)
        else _annotation(signature.return_annotation)
    )
    rows.append(
        Parameter(
            name="return", kind="output", type=returned, unit=units.get("return", "")
        )
    )
    return tuple(rows)


def _annotation(annotation: object) -> str:
    if annotation is inspect.Parameter.empty:
        return ""
    if isinstance(annotation, str):
        return annotation
    return getattr(annotation, "__qualname__", None) or str(annotation).replace(
        "typing.", ""
    )


def excerpt(
    obj: object,
    *,
    lines: tuple[int, int] | None = None,
    region: str | None = None,
    notes: Mapping[str, str] | None = None,
    values: Mapping[str, Real] | None = None,
    interface: bool = False,
) -> Excerpt:
    """Return the source of ``obj`` for display in a lesson.

    ``obj`` is a function or class defined at the top level of a module of
    the ``pbc`` package. The text is read from the source file when the cell
    runs, so the page shows the code the tests exercise.

    ``lines=(first, last)`` shows only those lines of the object, counted
    from 1 at its first line; ``region="name"`` shows the lines between
    ``# region: name`` and ``# endregion: name`` in its source. Either must
    exist, or the build fails.

    ``notes`` maps a line of what is shown, written without its indentation,
    to a short note. The line is marked and the note is listed under the
    listing; a line that is not shown exactly once fails the build, so notes
    cannot outlive the code they explain. A note holds no digits: write a
    computed number as ``{name}`` and pass it in ``values``.

    ``interface=True`` adds a table of the inputs and the output of ``obj``
    from its signature, with the units its docstring gives as ``name`` (unit).
    """
    module = inspect.getmodule(obj)
    name = getattr(obj, "__qualname__", None)
    if module is None or name is None:
        raise TypeError(f"expected a function or class, got {obj!r}")
    if module.__name__.split(".")[0] != "pbc":
        raise ValueError(
            f"{module.__name__}.{name} is not part of pbc; an excerpt shows"
            " code from src/pbc only"
        )
    if getattr(module, name, None) is not obj:
        raise ValueError(
            f"{module.__name__}.{name} is not defined at the top level of its"
            " module; show the function or class that contains it"
        )
    object_lines, first_line = inspect.getsourcelines(obj)
    file = Path(inspect.getsourcefile(obj) or "").resolve()
    try:
        path = file.relative_to(REPOSITORY_ROOT).as_posix()
    except ValueError:
        raise ValueError(
            f"{file} is outside the repository; install pbc from its checkout"
            " (uv sync) to build lesson pages"
        ) from None
    offset, shown = select(object_lines, lines, region)
    shown_first = first_line + offset
    marked = []
    for code, template in (notes or {}).items():
        matches = [
            shown_first + i for i, text in enumerate(shown) if text.strip() == code
        ]
        if len(matches) != 1:
            raise ValueError(
                f"a note is anchored to {code!r}, which is on {len(matches)} of the"
                f" lines shown from {module.__name__}.{name}; it must be on exactly one"
            )
        marked.append(Note(matches[0], code, _note_text(template, values or {})))
    return Excerpt(
        name=f"{module.__name__}:{name}",
        source="".join(shown),
        path=path,
        first_line=shown_first,
        last_line=shown_first + len(shown) - 1,
        commit=build_commit(),
        repository=repository_url(),
        region=region,
        lines=lines,
        notes=tuple(sorted(marked, key=lambda note: note.line)),
        interface=_interface(obj, name) if interface else (),
    )
