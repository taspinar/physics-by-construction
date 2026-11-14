"""Which cells of a lesson are made from a dataset (ADR 007).

A figure of a dataset has to name it, so that its status can be checked
against the card. Whether a figure cell is made from a dataset is decided by
following names through the Python cells of the lesson, without running them:

- A *source* is what ``pbc.data`` offers to read data (every module of the
  package but the tools in ``TOOLS``, and the sample and download
  directories), a ``pbc`` module outside the package that imports a reader
  of it, and a string that names the sample or download directory.
- A name is *derived from data* when it is bound to an expression that uses a
  source or a derived name: by an assignment, a loop, a ``with``, a function or
  class whose body uses one, or a method call that receives one (``ax.plot``
  of data makes ``ax``, and the figure it was created with, derived).
- A cell uses data when it mentions a source or a derived name.

Names are followed across all cells whatever their order, so a name that holds
data anywhere in the lesson counts as data everywhere. That errs towards
asking for a declaration.

What this cannot see is listed in ``docs/architecture.md`` ("Measured-data
lab"): data that reaches a figure without a name the lesson binds.
"""

import ast
import functools
import importlib.util
import re
from collections.abc import Iterable, Iterator
from pathlib import Path

PACKAGE = "pbc.data"

# Modules of the package that compute, draw, or describe, and read no data.
# Every other module of the package is a source, also one added later.
TOOLS = frozenset(
    f"{PACKAGE}.{name}"
    for name in (
        "calibration",
        "card",
        "check",
        "figure_provenance",
        "fit",
        "inverse",
        "pipeline",
        "plotting",
        "series",
        "status",
        "uncertainty",
    )
)
# What the package itself exports.
DIRECTORIES = frozenset({f"{PACKAGE}.SAMPLES_DIR", f"{PACKAGE}.DOWNLOADS_DIR"})
NOT_DATA = frozenset({f"{PACKAGE}.REPO_ROOT", f"{PACKAGE}.REGISTRY_DIR"})

_DATA_PATH = re.compile(r"\bdata/(?:samples|downloads)\b")
# For a cell that is not plain Python (a cell magic): the names it mentions.
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_.]*")


def _under(dotted: str, prefixes: Iterable[str]) -> bool:
    return any(dotted == p or dotted.startswith(p + ".") for p in prefixes)


def _imports(tree: ast.AST) -> Iterator[tuple[str, str]]:
    """Yield (bound name, dotted path) for every import of ``tree``."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    yield alias.asname, alias.name
                else:
                    top = alias.name.split(".")[0]
                    yield top, top
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            for alias in node.names:
                yield alias.asname or alias.name, f"{node.module}.{alias.name}"


def _is_reader(dotted: str) -> bool:
    """Whether the path lies in a module of the package that reads data."""
    return (
        _under(dotted, [PACKAGE])
        and dotted != PACKAGE
        and not _under(dotted, TOOLS | DIRECTORIES | NOT_DATA)
    )


@functools.cache
def _module_imports(module: str) -> tuple[str, ...]:
    """The dotted paths that the source of a ``pbc`` module imports."""
    try:
        spec = importlib.util.find_spec(module)
    except ImportError, ValueError:
        return ()
    if spec is None or not spec.origin or not spec.origin.endswith(".py"):
        return ()
    try:
        tree = ast.parse(Path(spec.origin).read_text(encoding="utf-8"))
    except OSError, SyntaxError:
        return ()
    return tuple(dotted for _, dotted in _imports(tree))


@functools.cache
def _module_reads_data(module: str) -> bool:
    """Whether a ``pbc`` module outside the package imports a reader of it,
    itself or through the ``pbc`` modules it imports.

    A module that only names the sample directory, as the one that renders a
    data card does, hands no measurements to a lesson and is not counted.
    """
    seen: set[str] = set()
    waiting = [module]
    while waiting:
        current = waiting.pop()
        if current in seen:
            continue
        seen.add(current)
        for dotted in _module_imports(current):
            if _is_reader(dotted):
                return True
            if dotted.startswith("pbc.") and not _under(dotted, [PACKAGE]):
                owner = _owning_module(dotted)
                if owner is not None:
                    waiting.append(owner)
    return False


@functools.cache
def _owning_module(dotted: str) -> str | None:
    """The longest prefix of ``dotted`` that is an importable module."""
    parts = dotted.split(".")
    for end in range(len(parts), 1, -1):
        name = ".".join(parts[:end])
        try:
            if importlib.util.find_spec(name) is not None:
                return name
        except ImportError, ValueError:
            continue
    return None


def is_source(dotted: str) -> bool:
    """Whether the dotted path names something that reads or holds data."""
    if dotted == PACKAGE or _under(dotted, NOT_DATA) or _under(dotted, TOOLS):
        return False
    if _under(dotted, [PACKAGE]):
        return True
    if dotted == "pbc" or not dotted.startswith("pbc."):
        return False
    module = _owning_module(dotted)
    return module is not None and _module_reads_data(module)


def _dotted(node: ast.AST) -> list[str] | None:
    """The parts of a ``a.b.c`` chain, or None for another expression."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    return [node.id, *reversed(parts)]


def _base(node: ast.AST) -> str | None:
    """The name an assignment target or a call receiver starts from."""
    while isinstance(node, ast.Attribute | ast.Subscript | ast.Starred):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def _targets(node: ast.AST) -> Iterator[str]:
    if isinstance(node, ast.Tuple | ast.List):
        for element in node.elts:
            yield from _targets(element)
    elif (name := _base(node)) is not None:
        yield name


class DataUse:
    """The names of a lesson that are derived from data."""

    def __init__(self, codes: Iterable[str], inert: Iterable[str] = ()):
        """``inert`` names never become data, as a module does not: the
        record of a lesson's experiment receives every result, and what it
        hands back is decided where it was recorded."""
        self._trees: list[ast.AST] = []
        self._unparsed: list[str] = []
        for code in codes:
            try:
                self._trees.append(ast.parse(code))
            except SyntaxError:
                self._unparsed.append(code)
        self._aliases: dict[str, str] = {}
        self._imported: set[str] = set()
        self._everything = False
        for tree in self._trees:
            for name, dotted in _imports(tree):
                self._imported.add(name)
                if name == "*":
                    module = dotted.removesuffix(".*")
                    if module == PACKAGE:
                        # The package hands out the sample and download
                        # directories; its other names are not data.
                        for export in DIRECTORIES:
                            self._aliases[export.rsplit(".", 1)[1]] = export
                    else:
                        # Every name of a reader arrives unnamed.
                        self._everything |= is_source(module)
                elif dotted == "pbc" or dotted.startswith("pbc."):
                    self._aliases[name] = dotted
        self._imported |= set(inert)
        self._derived: set[str] = set()
        # Names bound together (``fig, ax = ...``) share what happens to one.
        self._siblings: dict[str, set[str]] = {}
        changed = True
        while changed:
            before = len(self._derived)
            for tree in self._trees:
                for node in ast.walk(tree):
                    self._bind(node)
            for code in self._unparsed:
                self._bind_unparsed(code)
            changed = len(self._derived) != before

    def _name_is_data(self, parts: list[str]) -> bool:
        if parts[0] in self._derived:
            return True
        dotted = self._aliases.get(parts[0])
        return dotted is not None and is_source(".".join([dotted, *parts[1:]]))

    def _uses(self, *nodes: ast.AST | None) -> bool:
        for root in nodes:
            if root is None:
                continue
            for node in ast.walk(root):
                if isinstance(node, ast.Name | ast.Attribute):
                    parts = _dotted(node)
                    if parts is not None and self._name_is_data(parts):
                        return True
                elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if _DATA_PATH.search(node.value):
                        return True
        return False

    def _derive(self, names: Iterable[str]) -> None:
        for name in names:
            # A module stays a module: ``plt.plot(data)`` does not make every
            # later figure a figure of the data.
            if name not in self._imported:
                self._derived.add(name)
                self._derived |= self._siblings.get(name, set())

    def _bind(self, node: ast.AST) -> None:
        match node:
            case ast.Assign(targets=targets, value=value):
                names = [name for target in targets for name in _targets(target)]
                for name in names:
                    self._siblings.setdefault(name, set()).update(names)
                if self._uses(value):
                    self._derive(names)
            case (
                ast.AnnAssign(target=target, value=value)
                | ast.AugAssign(target=target, value=value)
                | ast.NamedExpr(target=target, value=value)
            ):
                if self._uses(value):
                    self._derive(_targets(target))
            case (
                ast.For(target=target, iter=source)
                | ast.AsyncFor(target=target, iter=source)
                | ast.comprehension(target=target, iter=source)
            ):
                if self._uses(source):
                    self._derive(_targets(target))
            case ast.With(items=items) | ast.AsyncWith(items=items):
                for item in items:
                    if item.optional_vars is not None and self._uses(item.context_expr):
                        self._derive(_targets(item.optional_vars))
            case (
                ast.FunctionDef(name=name)
                | ast.AsyncFunctionDef(name=name)
                | ast.ClassDef(name=name)
            ):
                if self._uses(*node.body):
                    self._derive([name])
            case ast.Expr(value=ast.Call(func=ast.Attribute() as func) as call):
                arguments = [*call.args, *(k.value for k in call.keywords)]
                receiver = _base(func)
                if receiver is not None and self._uses(*arguments):
                    self._derive([receiver])

    def _bind_unparsed(self, code: str) -> None:
        # Without a syntax tree nothing can be followed: if the cell mentions
        # data, every name it binds with '=' counts as derived.
        if self.uses(code):
            self._derive(re.findall(r"^\s*([A-Za-z_]\w*)\s*=(?!=)", code, re.M))

    def uses(self, code: str) -> bool:
        """Whether the cell mentions a source or a name derived from data."""
        if self._everything:
            return True
        try:
            return self._uses(ast.parse(code))
        except SyntaxError:
            return bool(_DATA_PATH.search(code)) or any(
                self._name_is_data(word.split(".")) for word in _WORD.findall(code)
            )
