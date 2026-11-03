"""The content of a lesson's last section: how to run its experiment.

The section keeps the identifier ``reproduce-this``; its heading and content
name the activity of the lesson (ADR 016 decision 3): "Run this experiment"
for a simulation or a lesson of measured data, "Replay this experiment" for an
agent lesson, "Check this proof" for a lesson whose methods are Lean only. It
lists the commands from a clone to the lesson's experiment and no command
that renders or previews the website.
"""

import importlib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml

from pbc.authoring.context import marker
from pbc.authoring.improvement import suggestion
from pbc.authoring.lean import LEAN_DIRECTORY
from pbc.authoring.repository import (
    REPOSITORY_ROOT,
    BuildCommit,
    build_commit,
    repository_url,
)
from pbc.authoring.website import PAGE_FILE, SITE_DIRECTORY, project_root

# The heading of the section for each kind of lesson.
HEADINGS = {
    "run": "Run this experiment",
    "replay": "Replay this experiment",
    "proof": "Check this proof",
}
# The directory the experiment writes into, relative to the clone.
RESULTS = "results"
# The proof check of a lesson whose methods are Lean only (ADR 016 decision 2).
LEAN_EXPERIMENT = "./scripts/check-lean.sh"
# The setup page, relative to the website project.
SETUP_PAGE = "reproduce.html"
# How the live run of an agent lesson is installed and what it needs.
LIVE_EXTRA = "openai"
LIVE_CREDENTIAL = "OPENAI_API_KEY"

_FRONT_MATTER = re.compile(r"\A---\n(.*?\n)---\s*\n", re.DOTALL)


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


def kind_of(methods: Sequence[str]) -> str:
    """The kind of a lesson with these methods: "proof", "replay", or "run"."""
    if list(methods) == ["lean"]:
        return "proof"
    if "llm-agents" in methods:
        return "replay"
    return "run"


def declaration(page: Path) -> tuple[str, str, tuple[str, ...]]:
    """The experiment, the kind, and the displayed Lean modules of a page."""
    match = _FRONT_MATTER.match(page.read_text(encoding="utf-8"))
    meta = (yaml.safe_load(match.group(1)) or {}).get("lesson") if match else None
    if not isinstance(meta, dict) or not meta.get("experiment"):
        raise ValueError(
            f"{page} declares no 'lesson.experiment'; every lesson declares its"
            " experiment (docs/authoring.md, 'The experiment of a lesson')"
        )
    return (
        str(meta["experiment"]),
        kind_of([str(method) for method in meta.get("methods") or []]),
        tuple(str(module) for module in meta.get("lean-modules") or []),
    )


@dataclass(frozen=True)
class Reproduction:
    """What a reader needs to run a lesson's experiment from a clone.

    As the result of a code cell it leaves a marker; the page the reader gets
    shows the commit, the files, and the commands, which the post-render step
    builds from the commit of the run (``pbc.authoring.context``).
    """

    page: str  # the lesson page, relative to the repository root
    code: tuple[str, ...]  # the code the page imports
    tests: tuple[str, ...]  # the tests of that code
    commit: BuildCommit
    repository: str
    experiment: str  # the module of the experiment, or the proof check
    kind: str  # "run", "replay", or "proof"
    lean_modules: tuple[str, ...] = ()  # the Lean modules the page displays
    live: str = ""  # the module of the live run of an agent lesson
    # The public address of the built page, which the "Suggest an
    # improvement" links pre-fill; set by the post-render step, "" before.
    address: str = ""

    @property
    def heading(self) -> str:
        """The heading of the section."""
        return HEADINGS[self.kind]

    @property
    def module(self) -> str:
        """The experiment module, or "" for a proof check alone."""
        return "" if self.experiment == LEAN_EXPERIMENT else self.experiment

    @property
    def experiment_command(self) -> str:
        """The command that runs the experiment of the page."""
        return f"uv run --locked --no-dev python -m {self.module} {RESULTS}"

    @property
    def proof_commands(self) -> tuple[str, ...]:
        """The commands that check the Lean modules the page displays, or the
        whole library for a proof lesson that names none."""
        if not self.lean_modules and self.kind != "proof":
            return ()
        return (
            f"cd {LEAN_DIRECTORY}",
            "lake exe cache get",
            " ".join(("lake build", *self.lean_modules)),
        )

    @property
    def commands(self) -> tuple[str, ...]:
        """The commands, from cloning to the experiment of this page."""
        directory = self.repository.rsplit("/", 1)[-1]
        commands = [f"git clone {self.repository}.git", f"cd {directory}"]
        if self.commit.sha is not None:
            commands.append(f"git checkout {self.commit.sha}")
        if self.module:
            commands += ["uv sync --locked --no-dev", self.experiment_command]
        return (*commands, *self.proof_commands)

    @property
    def live_commands(self) -> tuple[str, ...]:
        """The live run of an agent lesson, with a model and its key."""
        if not self.live:
            return ()
        return (
            f"uv sync --locked --no-dev --extra {LIVE_EXTRA}",
            f'export {LIVE_CREDENTIAL}="..."   # this shell only',
            f"uv run --locked --no-dev --extra {LIVE_EXTRA} python -m {self.live}",
        )

    def _link(self, path: str) -> str:
        if self.commit.sha is None:
            return f"`{path}`"
        return f"[`{path}`]({self.repository}/blob/{self.commit.sha}/{path})"

    def _setup_link(self) -> str:
        depth = Path(self.page).relative_to(SITE_DIRECTORY).parent.as_posix().count("/")
        return f"[the setup page]({'../' * (depth + 1)}{SETUP_PAGE})"

    def payload(self) -> dict:
        """What the region is built from, apart from the commit."""
        return {
            "page": self.page,
            "code": list(self.code),
            "tests": list(self.tests),
            "experiment": self.experiment,
            "kind": self.kind,
            "lean_modules": list(self.lean_modules),
            "live": self.live,
        }

    @classmethod
    def from_payload(
        cls,
        page: str,
        payload: dict,
        commit: BuildCommit,
        repository: str,
        address: str = "",
    ) -> Reproduction:
        """The region of the lesson ``page`` (relative to the site) for
        ``commit``; ``address`` is the public address of the built page."""
        if payload["page"] != f"{SITE_DIRECTORY}/{page}":
            raise ValueError(f"the marker names the page {payload['page']!r}")
        if payload["kind"] not in HEADINGS:
            raise ValueError(f"the marker names the kind {payload['kind']!r}")
        return cls(
            page=payload["page"],
            code=_repository_files("code", payload["code"]),
            tests=_repository_files("test", payload["tests"]),
            commit=commit,
            repository=repository,
            experiment=str(payload["experiment"]),
            kind=str(payload["kind"]),
            lean_modules=tuple(payload["lean_modules"]),
            live=str(payload["live"]),
            address=address,
        )

    def _repr_markdown_(self) -> str:
        return marker(
            "reproduce",
            Path(self.page).relative_to(SITE_DIRECTORY).as_posix(),
            self.payload(),
        )

    def _built_from(self) -> str:
        sha = self.commit.sha
        if sha is None:
            return (
                "This page was not built from a Git checkout, so the commit of"
                " its sources is unknown."
            )
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
        return built_from

    def _summary(self) -> list[str]:
        if self.module and self.kind != "proof":
            return [
                "In a clone at that commit, with the project's Python packages"
                " installed, this command runs the experiment of this page:",
                "",
                "```{.bash .reproduce-summary-command}",
                self.experiment_command,
                "```",
            ]
        return [
            "In a clone at that commit, with the pinned Lean toolchain, this"
            f" command in `{LEAN_DIRECTORY}/` checks the proofs of this page:",
            "",
            "```{.bash .reproduce-summary-command}",
            self.proof_commands[-1],
            "```",
        ]

    def _regenerates(self) -> list[str]:
        lines = []
        if self.module:
            lines.append(
                f"The experiment writes every figure of this page into"
                f" `{RESULTS}/`, as `<label>.png`, and every number and table of"
                f" the page, as the page shows it, into `{RESULTS}/results.json`."
                " Its numbers match this page to the digits shown, and its"
                " figure files are the ones the page shows; digits beyond those"
                " can differ between machines, because floating-point libraries"
                " differ. Change the code of the experiment and run it again"
                " to see what changes."
            )
        if self.kind == "replay":
            lines.append(
                "The experiment replays the recorded run of the agent: it runs"
                " every tool call of the recording again and needs no model"
                " and no key."
            )
        if self.proof_commands:
            lines.append(
                "`lake build` compiles the proofs of this page with the Lean"
                " toolchain that elan installs; the first run fetches the"
                " Mathlib build cache, which is large. The setup page says how"
                " to install elan."
            )
        return [line for text in lines for line in (text, "")]

    def _live(self) -> list[str]:
        if not self.live:
            return []
        return [
            "::: {.not-verified role=note}",
            "::: {.not-verified-label}",
            "**Not verified.** The build of this site did not run or check the"
            " material in this box.",
            ":::",
            "",
            "**Optional: the live run.** It asks a language model to run the"
            " experiment again, with your own account. It needs an OpenAI"
            f" account and its API key in the variable `{LIVE_CREDENTIAL}`,"
            f" and the optional dependency `{LIVE_EXTRA}`; a run costs a few"
            " cents. The key stays in your shell, never in a file.",
            "",
            "```{.bash .reproduce-live}",
            f"# needs: an OpenAI account, its API key, and the extra {LIVE_EXTRA}",
            *self.live_commands,
            "```",
            ":::",
            "",
        ]

    def markdown(self) -> str:
        """The content of the section, for the commit this was built with."""
        files = [f"- {self._link(self.page)}: this page, with every code cell."]
        for path in self.code:
            purpose = (
                "a Lean file the page shows"
                if path.startswith(f"{LEAN_DIRECTORY}/")
                else "code the experiment runs"
            )
            files.append(f"- {self._link(path)}: {purpose}.")
        files += [f"- {self._link(path)}: tests of that code." for path in self.tests]
        tools = "Git and uv" if self.module else "Git"
        if self.proof_commands:
            tools += ", and elan for the proofs,"
        # The summary is what the first view shows; the listing is complete
        # but closed. Both are text in the page, so neither needs JavaScript.
        return "\n".join(
            [
                "::: {.reproduce}",
                self._built_from(),
                "",
                *self._summary(),
                "",
                '<details class="reproduce-details">',
                "<summary>Files, tests, and every command</summary>",
                "",
                "The files behind it:",
                "",
                *files,
                "",
                f"With {tools} installed (see {self._setup_link()}), run:",
                "",
                "```{.bash .reproduce-commands}",
                *self.commands,
                "```",
                "",
                *self._regenerates(),
                "</details>",
                "",
                *self._live(),
                # The last line of the lesson (F135).
                "::: {.suggest-improvement}",
                suggestion(self.repository, self.address or self.page),
                ":::",
                ":::",
                "",
            ]
        )


def reproduce_this(*, code: Sequence[str], tests: Sequence[str] = ()) -> Reproduction:
    """Return the last section of the lesson page being built.

    ``code`` and ``tests`` name the files behind the page, relative to the
    repository root: the modules its cells import and the tests of those
    modules. The experiment, the kind of the lesson, and the Lean modules
    come from the front matter (``lesson.experiment``, ``lesson.methods``,
    ``lesson.lean-modules``); the live run of an agent lesson is the module
    its experiment names as ``LIVE``. Call it from a cell of the lesson's
    ``index.qmd``; the page is the one in the directory the cell runs in.
    """
    directory = Path.cwd().resolve()
    page = _lesson_page(directory)
    experiment, kind, lean_modules = declaration(directory / PAGE_FILE)
    live = ""
    if kind == "replay":
        live = str(importlib.import_module(experiment).LIVE)
    return Reproduction(
        page=page,
        code=_repository_files("code", code),
        tests=_repository_files("test", tests),
        commit=build_commit(),
        repository=repository_url(),
        experiment=experiment,
        kind=kind,
        lean_modules=lean_modules,
        live=live,
    )
