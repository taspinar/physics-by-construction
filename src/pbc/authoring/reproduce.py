"""The content of a lesson's "Reproduce this" section."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pbc.authoring.repository import (
    REPOSITORY_ROOT,
    BuildCommit,
    build_commit,
    repository_url,
)
from pbc.authoring.website import PAGE_FILE, SITE_DIRECTORY, project_root


def _lesson_page(directory: Path) -> str:
    """Return the repository path of the lesson page in ``directory``."""
    if not (directory / PAGE_FILE).is_file():
        raise FileNotFoundError(f"no {PAGE_FILE} in {directory}")
    relative = directory.relative_to(project_root(directory)).as_posix()
    return f"{SITE_DIRECTORY}/{relative}/{PAGE_FILE}"


def _repository_files(kind: str, paths: Sequence[str]) -> tuple[str, ...]:
    for path in paths:
        if Path(path).is_absolute() or not (REPOSITORY_ROOT / path).is_file():
            raise FileNotFoundError(
                f"{kind} file {path!r} does not exist; name files relative to"
                " the repository root"
            )
    return tuple(paths)


@dataclass(frozen=True)
class Reproduction:
    """What a learner needs to regenerate a lesson page from a clone.

    As the result of a code cell it renders as the commit, the files, and the
    commands.
    """

    page: str  # the lesson page, relative to the repository root
    code: tuple[str, ...]  # the code the page imports
    tests: tuple[str, ...]  # the tests of that code
    commit: BuildCommit
    repository: str

    @property
    def output(self) -> str:
        """The page the render command writes, relative to the repository root."""
        relative = Path(self.page).relative_to(SITE_DIRECTORY).with_suffix(".html")
        return f"{SITE_DIRECTORY}/_site/{relative.as_posix()}"

    @property
    def commands(self) -> tuple[str, ...]:
        """The commands, from cloning to rendering this page."""
        directory = self.repository.rsplit("/", 1)[-1]
        commands = [f"git clone {self.repository}.git", f"cd {directory}"]
        if self.commit.sha is not None:
            commands.append(f"git checkout {self.commit.sha}")
        commands.append("uv sync --locked")
        if self.tests:
            commands.append("uv run --locked pytest " + " ".join(self.tests))
        commands.append(f"uv run --locked quarto render {self.page}")
        return tuple(commands)

    def _link(self, path: str) -> str:
        if self.commit.sha is None:
            return f"`{path}`"
        return f"[`{path}`]({self.repository}/blob/{self.commit.sha}/{path})"

    def _repr_markdown_(self) -> str:
        sha = self.commit.sha
        if sha is None:
            built_from = (
                "This page was not built from a Git checkout, so the commit of"
                " its sources is unknown."
            )
        else:
            built_from = (
                f"This page was built from commit [`{sha}`]"
                f"({self.repository}/tree/{sha}) of the"
                f" [repository]({self.repository})."
            )
            if self.commit.dirty:
                built_from += (
                    " **The checkout had uncommitted changes, so that commit"
                    " does not hold exactly the files this page was built"
                    " from.**"
                )
        files = [f"- {self._link(self.page)}: this page, with every code cell."]
        files += [f"- {self._link(path)}: code the cells import." for path in self.code]
        files += [f"- {self._link(path)}: tests of that code." for path in self.tests]
        setup = self._link("docs/development.md")
        return "\n".join(
            [
                "::: {.reproduce}",
                built_from,
                "",
                "The files behind it:",
                "",
                *files,
                "",
                f"With Git and uv installed (see {setup}), run:",
                "",
                "```{.bash .reproduce-commands}",
                *self.commands,
                "```",
                "",
                "The last command runs every code cell of this page again and"
                f" writes the result to `{self.output}`. Its numbers and figures"
                " match this page to the digits shown. Digits beyond those can"
                " differ between machines, because floating-point libraries"
                " differ; the site is built on Linux.",
                ":::",
                "",
            ]
        )


def reproduce_this(*, code: Sequence[str], tests: Sequence[str] = ()) -> Reproduction:
    """Return the "Reproduce this" content for the lesson page being built.

    ``code`` and ``tests`` name the files behind the page, relative to the
    repository root: the modules its cells import and the tests of those
    modules. Call it from a cell of the lesson's ``index.qmd``; the page is
    the one in the directory the cell runs in.
    """
    return Reproduction(
        page=_lesson_page(Path.cwd().resolve()),
        code=_repository_files("code", code),
        tests=_repository_files("test", tests),
        commit=build_commit(),
        repository=repository_url(),
    )
