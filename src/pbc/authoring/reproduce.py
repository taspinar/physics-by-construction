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
from pathlib import Path, PurePosixPath

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
# The words of the section (F174, the owner's decision of 2026-11-14): the
# summary of its closed disclosure, the route to the version a page was built
# from, the note on the default route, and the visible notice of a local build
# with uncommitted changes.
DETAILS_SUMMARY = "Setup and commands"
PAGE_VERSION = "Use the version behind this page"
MAIN_MAY_DIFFER = "The latest version may produce different results."
LOCAL_PREVIEW = "Local preview: results may differ from the linked source."
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
    def page_address(self) -> str:
        """The address the "Suggest an improvement" links pre-fill: the public
        address of the built page once the post-render step has set it, and
        before that the built page's path in the site (``lessons/.../index.html``,
        as ``website.page_address`` gives it without a ``site-url``), never the
        repository path of the source page."""
        if self.address:
            return self.address
        page = PurePosixPath(self.page)
        if page.parts[:1] == (SITE_DIRECTORY,):
            page = page.relative_to(SITE_DIRECTORY)
        return page.with_suffix(".html").as_posix()

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
    def clone_commands(self) -> tuple[str, ...]:
        """The commands that clone the repository: the latest version, on
        ``main``."""
        directory = self.repository.rsplit("/", 1)[-1]
        return (f"git clone {self.repository}.git", f"cd {directory}")

    @property
    def checkout_command(self) -> str:
        """The command that checks out the commit this page was built from,
        or "" when that commit is unknown."""
        sha = self.commit.sha
        return "" if sha is None else f"git checkout {sha}"

    @property
    def run_commands(self) -> tuple[str, ...]:
        """The commands that run the experiment and check the proofs, the
        same in either version."""
        commands = []
        if self.module:
            commands += ["uv sync --locked --no-dev", self.experiment_command]
        return (*commands, *self.proof_commands)

    @property
    def commands(self) -> tuple[str, ...]:
        """Every command, in order, from cloning through the checkout of the
        version behind this page to the experiment; the page shows each
        once."""
        checkout = (self.checkout_command,) if self.checkout_command else ()
        return (*self.clone_commands, *checkout, *self.run_commands)

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

    def _activity(self) -> str:
        """What a reader does with the lesson, in the words of the sentence:
        run an experiment, replay a recorded agent run, or check a proof."""
        if self.kind == "proof":
            return (
                "check this proof and run its experiment"
                if self.module
                else "check this proof"
            )
        if self.kind == "replay":
            activity = "replay this recorded agent run"
        else:
            activity = "run this experiment"
        if self.proof_commands:
            activity += " and check its proofs"
        return activity

    def _sentence(self) -> str:
        """The one visible sentence of the section (F174, the owner's decision
        of 2026-11-14): what a reader can do on their own computer. It shows
        no commit and no command; both are in the disclosure."""
        activity = self._activity()
        return f"{activity[0].upper()}{activity[1:]} on your own computer."

    def _notice(self) -> list[str]:
        """The visible notice of a local build with uncommitted changes."""
        if not self.commit.dirty:
            return []
        return [
            "::: {.reproduce-notice role=note}",
            f"**{LOCAL_PREVIEW}**",
            ":::",
            "",
        ]

    def _versions(self) -> list[str]:
        """Which version to use: ``main`` by default, or the version behind
        this page, whose checkout is the one extra step (no step is listed
        twice)."""
        sha = self.commit.sha
        latest = (
            "This gives the latest version, on the branch `main`, to explore"
            f" and change. {MAIN_MAY_DIFFER}"
        )
        if sha is None:
            return [
                latest,
                "",
                "This page was not built from a Git checkout, so the commit of"
                " its sources is unknown and there is no version behind this"
                " page to check out: `main` is the only route.",
                "",
            ]
        lines = [
            latest,
            "",
            f"**{PAGE_VERSION}:** to reproduce the published results, check"
            f" out [the commit this page was built from]({self.repository}/tree/{sha})"
            " after cloning:",
            "",
            "```{.bash .reproduce-commands}",
            self.checkout_command,
            "```",
            "",
        ]
        if self.commit.dirty:
            lines += [
                "This page was built locally, from a checkout with"
                " uncommitted changes. The linked commit does not contain"
                " those changes, so neither version is sure to reproduce this"
                " page exactly.",
                "",
            ]
        return lines

    def _then(self) -> str:
        """The line before the shared commands."""
        steps = []
        if self.module:
            steps.append(
                "replay the recorded agent run"
                if self.kind == "replay"
                else "run the experiment"
            )
        if self.proof_commands:
            steps.append("check the proofs")
        either = ", in either version," if self.commit.sha is not None else ""
        return f"Then{either} {' and '.join(steps)}:"

    def _regenerates(self) -> list[str]:
        lines = []
        if self.module:
            # The promise of an exact reproduction holds only for a page
            # built from exactly one commit.
            match = (
                " In the version behind this page its numbers match this page"
                " to the digits shown, and its figure files are the ones the"
                " page shows; digits beyond those can differ between machines,"
                " because floating-point libraries differ."
                if self.commit.exact
                else ""
            )
            lines.append(
                f"The experiment writes every figure of this page into"
                f" `{RESULTS}/`, as `<label>.png`, and every number and table of"
                f" the page, as the page shows it, into `{RESULTS}/results.json`."
                f"{match} Change the code of the experiment and run it again"
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
                " Mathlib build cache, which is large."
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
        tools = ["Git", *(["uv"] if self.module else [])]
        if self.proof_commands:
            tools.append("elan")
        installed = (
            " and ".join(tools)
            if len(tools) < 3
            else f"{', '.join(tools[:-1])}, and {tools[-1]}"
        )
        files_at = (
            "The files behind this page, at the commit it was built from:"
            if self.commit.sha is not None
            else "The files behind this page:"
        )
        # The first view is one sentence and, for a local build with
        # uncommitted changes, its notice; the routes, every command once,
        # the files, the tests, and the live run of an agent lesson are in
        # one closed native disclosure, so neither needs JavaScript.
        return "\n".join(
            [
                "::: {.reproduce}",
                self._sentence(),
                "",
                *self._notice(),
                '<details class="reproduce-details">',
                f"<summary>{DETAILS_SUMMARY}</summary>",
                "",
                f"Install {installed} (see {self._setup_link()}), then get the code:",
                "",
                "```{.bash .reproduce-commands}",
                *self.clone_commands,
                "```",
                "",
                *self._versions(),
                self._then(),
                "",
                "```{.bash .reproduce-commands}",
                *self.run_commands,
                "```",
                "",
                *self._regenerates(),
                files_at,
                "",
                *files,
                "",
                *self._live(),
                "</details>",
                "",
                # The last line of the lesson (F135).
                "::: {.suggest-improvement}",
                suggestion(self.repository, self.page_address),
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
