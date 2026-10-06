"""Display the source of a function or class of ``pbc`` by reference."""

import inspect
import re
from dataclasses import dataclass
from pathlib import Path

from pbc.authoring.repository import (
    REPOSITORY_ROOT,
    BuildCommit,
    build_commit,
    repository_url,
)


@dataclass(frozen=True)
class Excerpt:
    """The source text of one object, with where it was read from.

    As the result of a code cell it renders as a highlighted listing followed
    by the file and lines it came from.
    """

    name: str  # "<module>:<object>", for example "pbc.sample:damped_oscillation"
    source: str  # the source text, exactly as in the file
    path: str  # file, relative to the repository root
    first_line: int
    last_line: int
    commit: BuildCommit
    repository: str

    def _repr_markdown_(self) -> str:
        longest_run = max(
            (len(run) for run in re.findall(r"`+", self.source)), default=0
        )
        fence = "`" * max(3, longest_run + 1)
        location = f"`{self.path}`, lines {self.first_line} to {self.last_line}"
        if self.commit.sha is not None:
            location = (
                f"[{location}]({self.repository}/blob/{self.commit.sha}/{self.path}"
                f"#L{self.first_line}-L{self.last_line})"
            )
        return (
            "::: {.excerpt}\n"
            f'{fence}{{.python source="{self.name}"}}\n'
            f"{self.source.rstrip()}\n"
            f"{fence}\n\n"
            "::: {.excerpt-source}\n"
            f"{location}, read from the repository when this page was built.\n"
            ":::\n"
            ":::\n"
        )


def excerpt(obj: object) -> Excerpt:
    """Return the source of ``obj`` for display in a lesson.

    ``obj`` is a function or class defined at the top level of a module of
    the ``pbc`` package. The text is read from the source file when the cell
    runs, so the page shows the code the tests exercise.
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
    lines, first_line = inspect.getsourcelines(obj)
    file = Path(inspect.getsourcefile(obj) or "").resolve()
    try:
        path = file.relative_to(REPOSITORY_ROOT).as_posix()
    except ValueError:
        raise ValueError(
            f"{file} is outside the repository; install pbc from its checkout"
            " (uv sync) to build lesson pages"
        ) from None
    return Excerpt(
        name=f"{module.__name__}:{name}",
        source="".join(lines),
        path=path,
        first_line=first_line,
        last_line=first_line + len(lines) - 1,
        commit=build_commit(),
        repository=repository_url(),
    )
