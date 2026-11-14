"""Display the source of a function or class of ``pbc`` by reference.

The display forms of ADR 002 and ADR 023 decisions 3 and 4: the whole
object; an exact selection of its lines (one range, a named region, or
several ranges joined by visible omission markers, optionally without the
docstring), each part with its source line numbers; a signature generated
from the function at build time; and the Source link alone. Every form ends
with a compact Source link to the object at the built commit.
"""

import ast
import html
import inspect
import io
import itertools
import re
import tokenize
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from numbers import Real
from pathlib import Path

from pbc.authoring.context import current_page, marker
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

# The classes of a listing whose lines are numbered after the conversion; a
# selection's parts and a generated signature get no copy button.
LISTING_CLASS = "excerpt-listing"
NO_COPY_CLASSES = ("excerpt-part", "excerpt-signature")


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
class Part:
    """One range of an excerpt: lines of the object, exactly as in the file."""

    lines: tuple[int, int]  # first and last line, counted from 1 in the object
    first_line: int  # file line number of its first line
    source: str

    @property
    def last_line(self) -> int:
        return self.first_line + self.lines[1] - self.lines[0]


@dataclass(frozen=True)
class Omission:
    """Lines of the object between two parts that the display leaves out."""

    lines: tuple[int, int]  # counted from 1 in the object
    first_line: int  # file line numbers
    last_line: int
    docstring: bool  # the omitted lines are exactly the object's docstring

    def markdown(self) -> str:
        where = _line_range(self.first_line, self.last_line)
        verb = "is" if self.first_line == self.last_line else "are"
        text = (
            f"The docstring, {where}, is not shown."
            if self.docstring
            else f"{where.capitalize()} {verb} not shown."
        )
        return (
            f'::: {{.excerpt-omission omitted="{self.lines[0]}-{self.lines[1]}"'
            f' what="{"docstring" if self.docstring else "lines"}"}}\n'
            f"{text}\n:::\n\n"
        )


@dataclass(frozen=True)
class Excerpt:
    """The source text of one object, or of a selection of its lines, with
    where it was read from.

    As the result of a code cell it leaves a marker; the page the reader gets
    shows a highlighted listing followed by a compact Source link to the
    object at the commit of the run (``pbc.authoring.context``). A selection
    is labelled as one, and its parts carry their source line numbers and are
    joined by omission markers. With notes, the listing's lines are numbered,
    the noted lines are marked, and a numbered list of notes follows; with an
    interface, a table of inputs and outputs comes first; with a signature,
    a generated signature stands for the header of the function.
    """

    name: str  # "<module>:<object>", for example "pbc.sample:damped_oscillation"
    path: str  # file, relative to the repository root
    parts: tuple[Part, ...]  # what is shown, in order; empty for a link alone
    span: tuple[int, int]  # the file lines the Source link opens
    commit: BuildCommit
    repository: str
    kind: str = "function"  # "function", "class", or "module"
    region: str | None = None  # name of the region of the object that is shown
    selection: bool = False  # the parts are not the whole object
    notes: tuple[Note, ...] = ()
    interface: tuple[Parameter, ...] = ()
    # The lines of the object's docstring: a gap that is exactly these lines
    # is marked as the docstring.
    docstring: tuple[int, int] | None = None
    signature: str | None = None  # the generated signature
    signature_lines: tuple[int, int] | None = None  # the header it stands for
    figure: bool = False  # a Figure source link alone

    @property
    def source(self) -> str:
        """The text shown, the parts one after the other."""
        return "".join(part.source for part in self.parts)

    @property
    def first_line(self) -> int:
        return self.parts[0].first_line if self.parts else self.span[0]

    @property
    def last_line(self) -> int:
        return self.parts[-1].last_line if self.parts else self.span[1]

    @property
    def lines(self) -> tuple[int, int] | tuple[tuple[int, int], ...] | None:
        """The ranges of the object shown, or None for the whole object."""
        if not self.selection or self.region is not None:
            return None
        ranges = tuple(part.lines for part in self.parts)
        return ranges[0] if len(ranges) == 1 else ranges

    @property
    def object_name(self) -> str:
        module, _, name = self.name.partition(":")
        return name or module

    def _omission(self, first: int, last: int) -> Omission:
        """The lines ``first`` to ``last`` of the object, left out."""
        return Omission(
            lines=(first, last),
            first_line=self.span[0] + first - 1,
            last_line=self.span[0] + last - 1,
            docstring=(first, last) == self.docstring,
        )

    def leading_omission(self) -> Omission | None:
        """The lines between a generated signature and the first part."""
        if self.signature_lines is None or not self.parts:
            return None
        first, last = self.signature_lines[1] + 1, self.parts[0].lines[0] - 1
        return self._omission(first, last) if first <= last else None

    def omissions(self) -> tuple[Omission, ...]:
        """The lines between consecutive parts."""
        return tuple(
            self._omission(before.lines[1] + 1, after.lines[0] - 1)
            for before, after in itertools.pairwise(self.parts)
        )

    def _interface_table(self) -> str:
        if not self.interface:
            return ""
        rows = "".join(
            f"| `{p.name}` | {p.kind} | {_cell(p.type)} | {_cell(p.unit)} |\n"
            for p in self.interface
        )
        return (
            "| Name | Kind | Type | Unit |\n|:--|:--|:--|:--|\n"
            f"{rows}\n: Inputs and outputs of `{self.object_name}`.\n\n"
        )

    def _signature(self) -> str:
        if self.signature is None or self.signature_lines is None:
            return ""
        first = self.span[0] + self.signature_lines[0] - 1
        last = self.span[0] + self.signature_lines[1] - 1
        return (
            f"::: {{.excerpt-label}}\nGenerated signature of `{self.object_name}`,"
            " not the source text: the names and defaults are read from the"
            " function when this page is built, the units from its docstring."
            f" It stands for {_line_range(first, last)}, the signature as"
            " written.\n:::\n\n"
            f"{_fence(self.signature)}{{.python .excerpt-signature"
            f' signature="{self.name}"'
            f' replaces="{self.signature_lines[0]}-{self.signature_lines[1]}"}}\n'
            f"{self.signature.rstrip()}\n"
            f"{_fence(self.signature)}\n\n"
        )

    def _block(self, part: Part, classes: str, attributes: str) -> str:
        marked = " ".join(
            f"{note.line}:{index}"
            for index, note in enumerate(self.notes, 1)
            if part.first_line <= note.line <= part.last_line
        )
        if marked:
            attributes += f' marked="{marked}"'
        fence = _fence(part.source)
        return (
            f"{fence}{{.python {classes}{attributes}"
            f' first-line="{part.first_line}"}}\n'
            f"{part.source.rstrip(chr(10))}\n{fence}\n\n"
        )

    def _listing(self) -> str:
        shown = f'source="{self.name}"'
        if self.region is not None:
            shown += f' region="{self.region}"'
        if not self.selection:
            if not self.notes:
                # The whole object without notes: the listing as it always was.
                fence = _fence(self.source)
                return (
                    f"{fence}{{.python {shown}}}\n{self.source.rstrip()}\n{fence}\n\n"
                )
            return self._block(self.parts[0], f".{LISTING_CLASS}", f" {shown}")
        ranges = ",".join(f"{p.lines[0]}-{p.lines[1]}" for p in self.parts)
        leading = self.leading_omission()
        blocks = [leading.markdown()] if leading is not None else []
        blocks.append(self._block(self.parts[0], f".{LISTING_CLASS} .excerpt-part", ""))
        for omission, part in zip(self.omissions(), self.parts[1:], strict=True):
            blocks += [
                omission.markdown(),
                self._block(part, f".{LISTING_CLASS} .excerpt-part", ""),
            ]
        return (
            f'::: {{.excerpt-selection {shown} lines="{ranges}"}}\n'
            f"{''.join(blocks)}:::\n\n"
        )

    def _label(self) -> str:
        if not self.selection:
            return ""
        return (
            f"::: {{.excerpt-label}}\nSelected lines of `{self.object_name}`,"
            f" not the whole {self.kind}: the numbers are its line numbers in"
            " the file, and the Source link opens all of it.\n:::\n\n"
        )

    def _notes(self) -> str:
        if not self.notes:
            return ""
        items = "\n".join(
            f'<li data-anchor="{html.escape(note.code)}">'
            f"Line {note.line}, <code>{html.escape(note.code)}</code>: "
            f"{html.escape(note.text)}</li>"
            for note in self.notes
        )
        return f'```{{=html}}\n<ol class="excerpt-notes">\n{items}\n</ol>\n```\n\n'

    def payload(self) -> dict:
        """What the region is built from, apart from the commit."""
        return {
            "name": self.name,
            "path": self.path,
            "parts": [[*p.lines, p.first_line, p.source] for p in self.parts],
            "span": list(self.span),
            "kind": self.kind,
            "region": self.region,
            "selection": self.selection,
            "notes": [[n.line, n.code, n.text] for n in self.notes],
            "interface": [[p.name, p.kind, p.type, p.unit] for p in self.interface],
            "docstring": None if self.docstring is None else list(self.docstring),
            "signature": self.signature,
            "signature_lines": (
                None if self.signature_lines is None else list(self.signature_lines)
            ),
            "figure": self.figure,
        }

    @classmethod
    def from_payload(
        cls, payload: dict, commit: BuildCommit, repository: str
    ) -> Excerpt:
        """The region a marker stands for, for ``commit``."""
        docstring = payload["docstring"]
        signature_lines = payload["signature_lines"]
        return cls(
            name=payload["name"],
            path=payload["path"],
            parts=tuple(
                Part((first, last), first_line, source)
                for first, last, first_line, source in payload["parts"]
            ),
            span=(payload["span"][0], payload["span"][1]),
            commit=commit,
            repository=repository,
            kind=payload["kind"],
            region=payload["region"],
            selection=payload["selection"],
            notes=tuple(Note(*note) for note in payload["notes"]),
            interface=tuple(Parameter(*item) for item in payload["interface"]),
            docstring=None if docstring is None else (docstring[0], docstring[1]),
            signature=payload["signature"],
            signature_lines=(
                None
                if signature_lines is None
                else (signature_lines[0], signature_lines[1])
            ),
            figure=payload["figure"],
        )

    def _repr_markdown_(self) -> str:
        return marker("excerpt", current_page(), self.payload())

    def markdown(self) -> str:
        """The content of the region, for the commit this was built with."""
        link = source_link_markdown(
            self.name,
            self.path,
            self.span,
            self.commit,
            self.repository,
            "Figure source" if self.figure else "Source",
        )
        if not self.parts:
            classes = (
                ".excerpt-source .figure-source" if self.figure else ".excerpt-source"
            )
            return f"::: {{{classes}}}\n{link}\n:::\n"
        return (
            "::: {.excerpt}\n"
            f"{self._interface_table()}"
            f"{self._signature()}"
            f"{self._label()}"
            f"{self._listing()}"
            f"{self._notes()}"
            f"::: {{.excerpt-source}}\n{link}\n:::\n"
            ":::\n"
        )


def _fence(text: str) -> str:
    longest_run = max((len(run) for run in re.findall(r"`+", text)), default=0)
    return "`" * max(3, longest_run + 1)


def _line_range(first: int, last: int) -> str:
    return f"line {first}" if first == last else f"lines {first} to {last}"


def _cell(text: str) -> str:
    return text.replace("|", "\\|") if text else "not stated"


def source_link_markdown(
    name: str,
    path: str,
    span: tuple[int, int],
    commit: BuildCommit,
    repository: str,
    text: str = "Source",
) -> str:
    """The compact Source link of an excerpt (U1b): the word, with the object
    and its lines for a screen reader; the path, the lines, and the commit in
    the address and in the link's data attributes. Without a known commit
    there is nothing to link to, and the path and lines are written out."""
    first, last = span
    where = _line_range(first, last)
    object_name = name.partition(":")[2] or name.partition(":")[0]
    if commit.sha is None:
        return f"{text}: `{path}`, {where}."
    address = f"{repository}/blob/{commit.sha}/{path}#L{first}-L{last}"
    return (
        f"[{text} [of `{object_name}`, {where}]{{.visually-hidden}}]({address})"
        f'{{.source-link title="{path}, {where}, at commit {commit.sha[:12]}"'
        f' source-name="{name}" path="{path}" lines="{first}-{last}"'
        f' commit="{commit.sha}"}}'
    )


_LINE_SPAN = re.compile(r'<span id="[^"]*-(\d+)"><a href="#[^"]*"[^>]*></a>')
_LISTING = re.compile(
    r'<div class="sourceCode"([^>]*)><pre class="sourceCode ([^"]*)"(.*?)</pre></div>',
    re.S,
)
_DATA = re.compile(r'data-(first-line|marked)="([^"]*)"')


def number_lines(region: str) -> str:
    """Give each line of a listing of an excerpt its source line number and
    its note, after the conversion that highlighted it.

    The converter writes one ``<span id="...-k"><a ...></a>`` per line of a
    code block; in a block with the class ``excerpt-listing`` it becomes
    ``<span class="line" data-line="n">``, with ``marked`` and
    ``data-note`` on a noted line. The numbers and the note's mark are
    generated content of the style sheet, so the text of the listing, and
    what a reader copies, stays the source.
    """

    def rewrite(found: re.Match[str]) -> str:
        if LISTING_CLASS not in found.group(2).split():
            return found.group(0)
        data = dict(_DATA.findall(found.group(1)))
        first = int(data["first-line"])
        marked = dict(
            item.split(":") for item in data.get("marked", "").split() if item
        )

        def line(span: re.Match[str]) -> str:
            number = first + int(span.group(1)) - 1
            note = marked.get(str(number))
            if note is None:
                return f'<span class="line" data-line="{number}">'
            return f'<span class="line marked" data-line="{number}" data-note="{note}">'

        body = _LINE_SPAN.sub(line, found.group(3))
        return (
            f'<div class="sourceCode"{found.group(1)}>'
            f'<pre class="sourceCode {found.group(2)}"{body}</pre></div>'
        )

    return _LISTING.sub(rewrite, region)


def _normalized(
    lines: tuple[int, int] | Sequence[tuple[int, int]] | None,
) -> list[tuple[int, int]] | None:
    if lines is None:
        return None
    if len(lines) == 2 and all(isinstance(n, int) for n in lines):
        return [(lines[0], lines[1])]  # type: ignore[index]
    ranges = [tuple(item) for item in lines]  # type: ignore[union-attr]
    if not ranges or any(len(r) != 2 for r in ranges):
        raise ValueError("lines is (first, last) or a sequence of (first, last) ranges")
    return [(int(r[0]), int(r[1])) for r in ranges]


def select(
    object_lines: list[str],
    lines: tuple[int, int] | Sequence[tuple[int, int]] | None,
    region: str | None,
) -> list[tuple[int, int]]:
    """Return the ranges of the lines shown, counted from 1 in the object,
    out of the lines of one object. The whole object when neither is given.

    Several ranges are in order and do not touch, so that an omission
    marker stands between any two of them."""
    if lines is not None and region is not None:
        raise ValueError("give lines or region, not both")
    ranges = _normalized(lines)
    if ranges is not None:
        for first, last in ranges:
            if not 1 <= first <= last <= len(object_lines):
                raise ValueError(
                    f"lines {first} to {last} are not within the"
                    f" {len(object_lines)} lines of the object"
                )
        for (_, last), (first, _) in itertools.pairwise(ranges):
            if first <= last + 1:
                raise ValueError(
                    "the ranges of lines must be in order with at least one"
                    f" line between them; {last} is followed by {first}"
                )
        return ranges
    if region is not None:
        starts = [
            i for i, t in enumerate(object_lines) if t.strip() == f"# region: {region}"
        ]
        ends = [
            i
            for i, t in enumerate(object_lines)
            if t.strip() == f"# endregion: {region}"
        ]
        if len(starts) != 1 or len(ends) != 1 or starts[0] + 1 >= ends[0]:
            raise ValueError(
                f"the object has no region {region!r}: it needs one"
                f" '# region: {region}' line followed by one"
                f" '# endregion: {region}' line"
            )
        return [(starts[0] + 2, ends[0])]
    return [(1, len(object_lines))]


def _subtract(
    ranges: list[tuple[int, int]], first: int, last: int
) -> list[tuple[int, int]]:
    kept = []
    for a, b in ranges:
        if b < first or a > last:
            kept.append((a, b))
            continue
        if a < first:
            kept.append((a, first - 1))
        if b > last:
            kept.append((last + 1, b))
    return kept


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


def _units(obj: object) -> dict[str, str]:
    return dict(_UNIT.findall(inspect.getdoc(obj) or ""))


def _interface(obj: object, name: str) -> tuple[Parameter, ...]:
    units = _units(obj)
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


def _definition(text: str) -> ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef:
    node = ast.parse(text).body[0]
    if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        raise TypeError("expected the source of a function or class")
    return node


def docstring_lines(text: str) -> tuple[int, int] | None:
    """The first and last line of the docstring of the function or class
    whose source is ``text``, counted from 1, or None when it has none."""
    node = _definition(text)
    first = node.body[0]
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        return first.lineno, first.end_lineno or first.lineno
    return None


def header_lines(text: str) -> tuple[int, int]:
    """The first and last line of the header of the function whose source is
    ``text``, from its decorators to the colon that ends the ``def``, counted
    from 1."""
    node = _definition(text)
    depth = 0
    seen_def = False
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.start[0] < node.lineno:
            continue
        if token.type == tokenize.NAME and token.string == "def":
            seen_def = True
        elif seen_def and token.type == tokenize.OP:
            if token.string in "([{":
                depth += 1
            elif token.string in ")]}":
                depth -= 1
            elif token.string == ":" and depth == 0:
                return 1, token.start[0]
    raise ValueError("the function has no header that ends in a colon")


def generated_signature(text: str, units: Mapping[str, str] | None = None) -> str:
    """The signature of the function whose source is ``text``, generated from
    it: the parameters and their kinds, the defaults as the source writes
    them, without annotations, one parameter per line with its unit as a
    comment, ending in ``: ...``."""
    node = _definition(text)
    if isinstance(node, ast.ClassDef):
        raise TypeError("a generated signature is of a function, not a class")
    units = units or {}
    arguments = node.args
    positional = [*arguments.posonlyargs, *arguments.args]
    defaults: list[ast.expr | None] = [None] * (
        len(positional) - len(arguments.defaults)
    ) + list(arguments.defaults)
    entries: list[tuple[str, str]] = []  # (text, name for its unit)

    def default(node_: ast.expr | None) -> str:
        if node_ is None:
            return ""
        return "=" + (ast.get_source_segment(text, node_) or ast.unparse(node_))

    for index, (argument, value) in enumerate(zip(positional, defaults, strict=True)):
        entries.append((argument.arg + default(value), argument.arg))
        if arguments.posonlyargs and index == len(arguments.posonlyargs) - 1:
            entries.append(("/", ""))
    if arguments.vararg is not None:
        entries.append((f"*{arguments.vararg.arg}", arguments.vararg.arg))
    elif arguments.kwonlyargs:
        entries.append(("*", ""))
    for argument, value in zip(
        arguments.kwonlyargs, arguments.kw_defaults, strict=True
    ):
        entries.append((argument.arg + default(value), argument.arg))
    if arguments.kwarg is not None:
        entries.append((f"**{arguments.kwarg.arg}", arguments.kwarg.arg))
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    lines = [f"{prefix} {node.name}("]
    for entry, name in entries:
        unit = units.get(name, "") if name else ""
        lines.append(f"    {entry},{f'  # {unit}' if unit else ''}")
    returned = units.get("return", "")
    lines.append(f"): ...{f'  # returns {returned}' if returned else ''}")
    return "\n".join(lines) + "\n"


def _check_signature(obj: object, text: str, name: str) -> None:
    """The generated signature names the parameters of the function the build
    imported, and every default the source writes as a literal is the
    function's default."""
    node = _definition(text)
    signature = inspect.signature(obj)  # type: ignore[arg-type]
    arguments = node.args
    written = [
        *arguments.posonlyargs,
        *arguments.args,
        *([arguments.vararg] if arguments.vararg else []),
        *arguments.kwonlyargs,
        *([arguments.kwarg] if arguments.kwarg else []),
    ]
    if [a.arg for a in written] != list(signature.parameters):
        raise ValueError(
            f"the source of {name} names other parameters than the function"
        )
    positional = [*arguments.posonlyargs, *arguments.args]
    pairs = list(
        zip(
            positional[len(positional) - len(arguments.defaults) :],
            arguments.defaults,
            strict=True,
        )
    ) + [
        (a, d)
        for a, d in zip(arguments.kwonlyargs, arguments.kw_defaults, strict=True)
        if d is not None
    ]
    for argument, value in pairs:
        try:
            literal = ast.literal_eval(value)
        except ValueError:
            continue  # a name or a call: shown as the source writes it
        actual = signature.parameters[argument.arg].default
        if type(literal) is not type(actual) or literal != actual:
            raise ValueError(
                f"the default of {argument.arg} in the source of {name} is not"
                " the function's default"
            )


def _resolve(obj: object) -> tuple[object, str, str]:
    """The module of ``obj``, its name in the module, and the kind."""
    module = inspect.getmodule(obj)
    if inspect.ismodule(obj):
        name, kind = "", "module"
    else:
        name = getattr(obj, "__qualname__", None)
        kind = "class" if inspect.isclass(obj) else "function"
    if module is None or name is None:
        raise TypeError(f"expected a function, class, or module, got {obj!r}")
    if module.__name__.split(".")[0] != "pbc":
        raise ValueError(
            f"{module.__name__}.{name} is not part of pbc; an excerpt shows"
            " code from src/pbc only"
        )
    if name and getattr(module, name, None) is not obj:
        raise ValueError(
            f"{module.__name__}.{name} is not defined at the top level of its"
            " module; show the function or class that contains it"
        )
    return module, name, kind


def _location(obj: object) -> tuple[list[str], int, str]:
    """The lines of ``obj``, the file line of the first, and the file."""
    object_lines, first_line = inspect.getsourcelines(obj)  # type: ignore[arg-type]
    # A module's lines start at 1; inspect reports 0 for it.
    first_line = max(first_line, 1)
    file = Path(inspect.getsourcefile(obj) or "").resolve()  # type: ignore[arg-type]
    try:
        path = file.relative_to(REPOSITORY_ROOT).as_posix()
    except ValueError:
        raise ValueError(
            f"{file} is outside the repository; install pbc from its checkout"
            " (uv sync) to build lesson pages"
        ) from None
    return object_lines, first_line, path


def excerpt(
    obj: object,
    *,
    lines: tuple[int, int] | Sequence[tuple[int, int]] | None = None,
    region: str | None = None,
    notes: Mapping[str, str] | None = None,
    values: Mapping[str, Real] | None = None,
    interface: bool = False,
    docstring: bool = True,
    signature: bool = False,
) -> Excerpt:
    """Return the source of ``obj`` for display in a lesson.

    ``obj`` is a function or class defined at the top level of a module of
    the ``pbc`` package, or such a module itself with ``region`` or
    ``lines``, for the values a lesson's experiment starts from. The text is
    read from the source file when the cell runs, so the page shows the code
    the tests exercise.

    ``lines=(first, last)`` shows only those lines of the object, counted
    from 1 at its first line; ``lines=[(a, b), (c, d)]`` shows several
    ranges, in order and not touching, joined by a marker that names the
    lines left out; ``region="name"`` shows the lines between
    ``# region: name`` and ``# endregion: name`` in its source. They must
    exist, or the build fails. A selection is labelled as one and shows its
    source line numbers.

    ``docstring=False`` leaves the docstring of a function or class out of
    the display, with a marker; the source keeps it, and the Source link
    opens it. ``signature=True`` shows, instead of the header of a function
    as written, a signature generated from it: the parameter names and the
    defaults the source writes, and the units of the docstring, labelled as
    generated.

    ``notes`` maps a line of what is shown, written without its indentation,
    to a short note. The line is marked and the note is listed under the
    listing; a line that is not shown exactly once fails the build, so notes
    cannot outlive the code they explain. A note holds no digits: write a
    computed number as ``{name}`` and pass it in ``values``.

    ``interface=True`` adds a table of the inputs and the output of ``obj``
    from its signature, with the units its docstring gives as ``name`` (unit).
    """
    module, name, kind = _resolve(obj)
    if kind == "module":
        if region is None and lines is None:
            raise TypeError(
                f"an excerpt of the module {module.__name__} shows a region or"  # type: ignore[attr-defined]
                " lines of it; show a function or class for more"
            )
        if interface:
            raise ValueError("a module has no interface to show")
        if not docstring or signature:
            raise ValueError("a module has no docstring or signature to leave out")
    if signature and kind != "function":
        raise ValueError("a generated signature is of a function, not a class")
    full_name = f"{module.__name__}:{name}"  # type: ignore[attr-defined]
    object_lines, first_line, path = _location(obj)
    text = "".join(object_lines)
    ranges = select(object_lines, lines, region)
    whole = ranges == [(1, len(object_lines))]
    omitted_docstring = None if kind == "module" else docstring_lines(text)
    if not docstring:
        if omitted_docstring is None:
            raise ValueError(f"{full_name} has no docstring to leave out")
        before = ranges
        ranges = _subtract(ranges, *omitted_docstring)
        if ranges == before:
            raise ValueError(f"the lines shown of {full_name} hold no docstring")
    generated = header = None
    if signature:
        header = header_lines(text)
        _check_signature(obj, text, full_name)
        generated = generated_signature(text, _units(obj))
        ranges = _subtract(ranges, *header)
    if not ranges:
        raise ValueError(f"nothing of {full_name} is left to show")
    parts = tuple(
        Part((a, b), first_line + a - 1, "".join(object_lines[a - 1 : b]))
        for a, b in ranges
    )
    marked = []
    for code, template in (notes or {}).items():
        matches = [
            part.first_line + i
            for part in parts
            for i, line in enumerate(part.source.splitlines())
            if line.strip() == code
        ]
        if len(matches) != 1:
            raise ValueError(
                f"a note is anchored to {code!r}, which is on {len(matches)} of the"
                f" lines shown from {module.__name__}.{name}; it must be on exactly one"  # type: ignore[attr-defined]
            )
        marked.append(Note(matches[0], code, _note_text(template, values or {})))
    if kind == "module":
        span = (parts[0].first_line, parts[-1].last_line)
    else:
        span = (first_line, first_line + len(object_lines) - 1)
    return Excerpt(
        name=full_name,
        path=path,
        parts=parts,
        span=span,
        commit=build_commit(),
        repository=repository_url(),
        kind=kind,
        region=region,
        selection=not whole or not docstring or signature,
        notes=tuple(sorted(marked, key=lambda note: note.line)),
        interface=_interface(obj, name) if interface else (),
        docstring=omitted_docstring,
        signature=generated,
        signature_lines=header,
    )


def source_link(obj: object, *, figure: bool = False) -> Excerpt:
    """Return the Source link alone to a function or class of ``pbc``, the
    display form for code the lesson does not teach (ADR 023; U1h).

    ``figure=True`` names it "Figure source", for the function that draws a
    figure shown on the page. The link opens the whole object at the built
    commit.
    """
    module, name, kind = _resolve(obj)
    if kind == "module":
        raise TypeError("a Source link opens a function or class, not a module")
    object_lines, first_line, path = _location(obj)
    return Excerpt(
        name=f"{module.__name__}:{name}",  # type: ignore[attr-defined]
        path=path,
        parts=(),
        span=(first_line, first_line + len(object_lines) - 1),
        commit=build_commit(),
        repository=repository_url(),
        kind=kind,
        figure=figure,
    )
