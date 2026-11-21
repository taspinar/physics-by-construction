"""Coding agents run only on the learner's machine (ADR 010 decision 6,
invariant I24; ``docs/coding-agent-workflow.md``): nothing CI or the build
is made of starts a coding agent, names a coding agent's credential, or
depends on the Agentic Coding Template (ADR 022 decision 7); and a
transcript of an agent session is an example on a page, marked "not
verified" with the agent and the date, never a file the build reads.

This extends ``test_skills_boundary.py``, the boundary of the agent skills
(I32). What "CI and the build" are made of is computed, in two parts:

- the build side: the CI workflows, the checks of ``scripts/verify.conf``,
  every script those run or source, the site, the package, the products'
  code, and the test suites CI runs. None of it starts a coding agent or
  reaches the launcher of the development workflow;
- the self-tests of the development workflow, the checks of
  ``scripts/verify-workflow.conf``, which CI runs with ``verify.sh --all``
  (ADR 005). The development workflow (``scripts/*-feature.sh``,
  ``scripts/lib/agent.sh``) does start a coding agent, on the maintainer's
  machine (ADR 006), and its self-tests load that launcher in CI. So CI
  does reach the launcher, through these self-tests only, and what they
  start under an agent's name is a fake program of the test: every
  self-test that can start one writes a fake for each program the launcher
  starts and puts it first on every ``PATH`` it sets, no other script of
  that reach starts an agent program itself (#569), no file of that reach
  names a credential, and nothing CI runs installs an agent.

The second part is read from the text of the self-tests, as the first is:
it shows how they are written, not what a run of them did.
"""

import ast
import functools
import re
import subprocess
import sys
from pathlib import Path

import pytest
from support import verify_conf

ROOT = Path(__file__).parents[2]
SELF = "tests/unit/test_coding_agent_boundary.py"
LAUNCHER = "scripts/lib/agent.sh"

# The programs a coding agent is started by.
PROGRAMS = (
    "claude", "codex", "aider", "gemini", "cursor-agent", "opencode", "goose",
)  # fmt: skip
_NAMES = "|".join(re.escape(name) for name in PROGRAMS)
# In a shell script, a workflow, or a command of verify.conf: the program's
# name as a word of its own. A model or a package that only starts with the
# name ("claude-...", "codex_home") is not the program.
COMMAND_WORD = re.compile(rf"(?<![\w./-])(?:{_NAMES})(?![\w./-])")
# On a page, in an executed cell: the program's name as a string of its own.
ARGUMENT = re.compile(rf"""["'](?:{_NAMES})["']""")
# On a page: a command line that starts with the program.
PAGE_COMMAND = re.compile(
    rf"(?m)^\s*(?:\$\s+)?(?:(?:npx|uvx|pipx run)\s+(?:-y\s+)?)?(?:{_NAMES})(?:\s|$)"
)
# The credentials and credential files of those programs.
CREDENTIALS = re.compile(
    r"ANTHROPIC_(?:API_KEY|AUTH_TOKEN)|CLAUDE_CODE_OAUTH_TOKEN|CODEX_API_KEY"
    r"|GEMINI_API_KEY|GOOGLE_API_KEY|CURSOR_API_KEY|AIDER_[A-Z_]*KEY"
    r"|GITHUB_COPILOT_TOKEN|\.claude/\.credentials|\.codex/auth\.json"
)
# The provider key of the harness agents (ADR 004): the learner's, never CI's.
HARNESS_KEY = "OPENAI_API_KEY"
# The only token a CI job may name: the workflow's own.
CI_TOKENS = {"GH_TOKEN", "GITHUB_TOKEN"}
TEMPLATE = re.compile(r"agentic[-_ ]coding[-_ ]template", re.IGNORECASE)
# The packages and installers those programs come from: what a job would
# name to install one.
PACKAGES = re.compile(
    r"@anthropic-ai/claude-code|claude\.ai/install|@openai/codex|aider-chat"
    r"|aider-install|@google/gemini-cli|cursor\.com/install|opencode-ai"
    r"|opencode\.ai/install|block/goose"
)
WORKFLOW_CONF = "scripts/verify-workflow.conf"
# The one function of the launcher that starts a program.
STARTS = re.compile(r"\bagent_run\b")
# How a script or a command runs another script: by its path after "./", after
# a variable that holds a directory, or after "bash"; and how it sources one.
# A path that is only named (in a message, a comment, a list of protected
# files, or a loop that reads or syntax-checks files) runs nothing.
RUNS = re.compile(
    r"""(?:\./|\$\{?\w+\}?"?/|\bbash\s+(?:-[a-z]+\s+)*"?)"""
    r"""((?:(?:scripts|tests)/)?(?:lib/)?[\w.-]+\.(?:sh|py))"""
)
# "source" where a command starts (at the start of a line, after ";", "&&",
# "|", "(", an opening quote of "bash -c", "then", "do", "else"), or "." at
# the start of a line; and its argument, up to the script's name.
SOURCES = re.compile(
    r"""(?:(?:^|[;&|(']|\b(?:then|do|else)\b)\s*source|^\s*\.)\s+"""
    r"""(?:([^;]*?\.sh)(?=["';\s)]|$))?"""
)
SOURCED_NAME = re.compile(
    r"""(?:^|[/"'])((?:(?:scripts|tests)/)?(?:lib/)?[\w.-]+\.sh)$"""
)
LOOP = re.compile(r"^\s*for\s+(\w+)\s+in\s+(.+?);\s*do\b")
MESSAGE = re.compile(r"^\s*(?:echo|printf)\b")
# The text a script hands to a function that reports a failure, wherever
# the call stands on its line ("... || fail \"run ./scripts/x.sh\""): a
# message, unless a command substitution in it runs something.
FAILURE_TEXT = re.compile(r"""\b(?:fail|\w+_fail)\s+"(?:[^"$`\\]|\\.|\$(?!\())*\"""")
NOT_VERIFIED = re.compile(r"(?ms)^(:{3,}) *\{[^}\n]*\.not-verified[^}\n]*\}.*?^\1 *$")
PYTHON_SUITES = (
    "tests/unit/", "tests/integration/", "tests/lessons/", "tests/e2e/",
    "tests/support/",
)  # fmt: skip


def project_files() -> list[str]:
    listed = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    return sorted(p for p in listed.split("\0") if p and (ROOT / p).is_file())


FILES = project_files()


def read(path: str) -> str:
    return (ROOT / path).read_text(errors="replace")


def ci_files() -> list[str]:
    return [path for path in FILES if path.startswith(".github/")]


def code_lines(text: str) -> list[str]:
    """The lines of a shell script or a command that can run something: not
    a comment and not a message."""
    return [
        line
        for line in text.splitlines()
        if not line.lstrip().startswith("#") and not MESSAGE.match(line)
    ]


def _script(name: str) -> str | None:
    """The script of the repository a path in a command means."""
    for candidate in (name, f"scripts/{name}"):
        if candidate in FILES:
            return candidate
    return None


def runs(text: str) -> tuple[set[str], list[str]]:
    """The scripts ``text`` runs or sources, and the lines that source a
    file this function cannot name. A sourced path with a loop variable in
    it stands for every word of the loop."""
    found: set[str] = set()
    unresolved: list[str] = []
    loops: dict[str, list[str]] = {}
    for line in code_lines(text):
        if loop := LOOP.match(line):
            loops[loop.group(1)] = loop.group(2).split()
        line = FAILURE_TEXT.sub("", line)
        found |= {s for m in RUNS.finditer(line) if (s := _script(m.group(1)))}
        for sourced in SOURCES.finditer(line):
            path = sourced.group(1) or ""
            variable = re.search(r"/lib/\$\{?(\w+)\}?\.sh$", path)
            named = SOURCED_NAME.search(path)
            names = (
                [f"lib/{word}.sh" for word in loops.get(variable.group(1), [])]
                if variable
                else [named.group(1)]
                if named
                else []
            )
            scripts = [script for name in names if (script := _script(name))]
            if not scripts:
                unresolved.append(line.strip())
            found |= set(scripts)
    return found, unresolved


@functools.cache
def reach(start: str) -> tuple[str, ...]:
    """The scripts the commands of ``start`` run by path, and those a
    reached script runs or sources, to any depth."""
    reached: set[str] = set()
    queue = sorted(runs(start)[0])
    while queue:
        path = queue.pop()
        if path in reached:
            continue
        reached.add(path)
        if path.endswith(".sh"):
            queue += sorted(runs(read(path))[0])
    return tuple(sorted(reached))


def workflow_checks() -> dict[str, str]:
    """The self-tests of the development workflow, as name -> command: the
    checks of verify-workflow.conf, which ``verify.sh --all`` runs in CI."""
    found = {}
    for line in read(WORKFLOW_CONF).splitlines():
        entry = re.match(r"^([a-z0-9][a-z0-9-]*)(?:\s*\[[a-z0-9-]+\])?:\s*(.*\S)", line)
        if entry and entry.group(1) != "paths":
            found[entry.group(1)] = entry.group(2)
    return found


def build_scripts() -> list[str]:
    """The build side: the scripts the CI workflows and the checks of
    verify.conf run or source."""
    start = [*map(read, ci_files()), *verify_conf.checks().values()]
    return list(reach("\n".join(start)))


def self_test_scripts() -> list[str]:
    """The scripts the self-tests of the development workflow run or
    source, the self-tests included."""
    return list(reach("\n".join(workflow_checks().values())))


def reached_scripts() -> list[str]:
    """Every script CI runs: the build side and the workflow's self-tests."""
    return sorted({*build_scripts(), *self_test_scripts()})


def build_like() -> dict[str, str]:
    """What runs as commands on the build side, by a name for the report."""
    texts = {path: read(path) for path in (*ci_files(), *build_scripts())}
    texts.update(
        {f"verify.conf:{name}": cmd for name, cmd in verify_conf.checks().items()}
    )
    return texts


def shell_like() -> dict[str, str]:
    """What runs as commands in CI and the build, by a name for the report:
    the build side, and the self-tests with what they reach."""
    texts = build_like()
    texts.update({path: read(path) for path in self_test_scripts()})
    texts.update(
        {f"verify-workflow.conf:{name}": cmd for name, cmd in workflow_checks().items()}
    )
    return texts


def launcher_programs() -> set[str]:
    """The programs the launcher of the development workflow names."""
    return set(COMMAND_WORD.findall("\n".join(code_lines(read(LAUNCHER)))))


def calls_the_launcher(path: str) -> bool:
    return bool(STARTS.search("\n".join(code_lines(read(path)))))


def starting_self_tests() -> dict[str, str]:
    """The self-tests that can start a program under an agent's name: those
    that call the starting function of the launcher, or reach a script that
    does. By name -> the script of the self-test."""
    found = {}
    for name, command in workflow_checks().items():
        scripts = reach(command)
        if LAUNCHER in scripts and any(
            calls_the_launcher(path) for path in scripts if path != LAUNCHER
        ):
            (found[name],) = runs(command)[0]
    return found


WRITES = re.compile(r"""(?:>\s*|\bcp\s+\S+\s+)"(\$\w+(?:/[\w-]+)*)/(\$?\w+)\"""")
FAKES_CALL = re.compile(r"""^\s*make_fake_agents\s+"([^"]+)"\s*$""")
SYSTEM_DIRECTORIES = {"/usr/bin", "/bin"}
PATH_VALUE = re.compile(r"""\bPATH="([^"]*)\"""")


def written_programs(text: str) -> dict[str, set[str]]:
    """The files a shell script writes or copies into a directory, as
    directory -> names: how a self-test makes its fake programs. A name
    that is a loop variable stands for every word of the loop."""
    found: dict[str, set[str]] = {}
    loops: dict[str, list[str]] = {}
    for line in text.splitlines():
        if loop := LOOP.match(line):
            loops[loop.group(1)] = loop.group(2).split()
        for directory, name in WRITES.findall(line):
            names = loops.get(name[1:], []) if name.startswith("$") else [name]
            found.setdefault(directory, set()).update(names)
    return found


def fake_directories(text: str, needed: set[str]) -> set[str]:
    """The directories in which a self-test makes a fake of every needed
    program: by ``make_fake_agents`` of tests/lib-fakes.sh, or by itself."""
    shared = written_programs(read("tests/lib-fakes.sh")).get("$bin", set())
    found = {d for d, names in written_programs(text).items() if needed <= names}
    if needed <= shared and "tests/lib-fakes.sh" in runs(text)[0]:
        found |= {
            call.group(1)
            for line in text.splitlines()
            if (call := FAKES_CALL.match(line))
        }
    return found


def unshadowed_paths(text: str, needed: set[str]) -> list[str]:
    """The values a self-test gives ``PATH`` that do not start with a
    directory of its fakes; all of them when it makes no fakes or sets no
    ``PATH``. A value that only extends the ``PATH`` it inherits, with a
    directory of the test's own in front, counts when the test has exported
    a ``PATH`` that starts with the fakes. A value of the system directories
    alone counts too: it is how a self-test shows that a missing program is
    refused, and it finds an agent only where one is installed in the
    system, which nothing CI runs does (the test of the installers)."""
    fakes = fake_directories(text, needed)
    values = PATH_VALUE.findall("\n".join(code_lines(text)))
    if not fakes or not values:
        return ["(no fakes)" if not fakes else "(no PATH)", *values]
    exported = any(
        value.split(":")[0] in fakes
        for value in re.findall(r"""export PATH="([^"]*)\"""", text)
    )
    return [
        value
        for value in values
        if (entries := value.split(":"))[0] not in fakes
        and not set(entries) <= SYSTEM_DIRECTORIES
        and not (exported and entries[0].startswith("$tmp/") and entries[-1] == "$PATH")
    ]


def python_sources() -> list[str]:
    return [
        path
        for path in FILES
        if path.endswith(".py")
        and path != SELF
        and path.startswith(("src/", "site/", "products/", *PYTHON_SUITES))
    ]


def agent_arguments(source: str) -> list[str]:
    """The names of coding-agent programs that ``source`` holds as an
    argument of a call or as an element of a list, a tuple, or a set: how
    Python starts a program or looks one up. A key of a mapping that names
    a provider for display is neither."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            values = [*node.args, *(keyword.value for keyword in node.keywords)]
        elif isinstance(node, ast.List | ast.Tuple | ast.Set):
            values = node.elts
        else:
            continue
        found += [
            value.value
            for value in values
            if isinstance(value, ast.Constant) and value.value in PROGRAMS
        ]
    return found


def key_holders() -> set[str]:
    """The names a module of the package binds to the harness key's name."""
    found = set()
    for path in python_sources():
        if not path.startswith(("src/", "site/", "products/")):
            continue
        for node in ast.walk(ast.parse(read(path))):
            if (
                isinstance(node, ast.Assign)
                and isinstance(node.value, ast.Constant)
                and node.value.value == HARNESS_KEY
            ):
                found |= {t.id for t in node.targets if isinstance(t, ast.Name)}
    return found


def reads_the_harness_key(source: str, holders: set[str] = frozenset()) -> bool:
    """Whether ``source`` hands the name of the harness key to a call or
    looks it up in a mapping, by its text or by a name bound to it: how
    Python reads a variable of the environment. A message or a docstring
    that tells the learner to set the variable does neither."""

    def is_key(node: ast.AST) -> bool:
        return (
            (isinstance(node, ast.Constant) and node.value == HARNESS_KEY)
            or (isinstance(node, ast.Name) and node.id in holders)
            or (isinstance(node, ast.Attribute) and node.attr in holders)
        )

    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            values = [*node.args, *(keyword.value for keyword in node.keywords)]
        elif isinstance(node, ast.Subscript):
            values = [node.slice]
        else:
            continue
        if any(is_key(value) for value in values):
            return True
    return False


EXECUTED_CELL = re.compile(r"(?ms)^```\{python[^}\n]*\}\n(.*?)^```")
HARNESS_CLIENT = "src/pbc/agents/clients/openai.py"


def pages() -> list[str]:
    return [p for p in FILES if p.startswith("site/") and p.endswith(".qmd")]


def outside_not_verified(text: str) -> str:
    return NOT_VERIFIED.sub("", text)


def build_inputs() -> list[str]:
    """Every file CI and the build read as code or configuration."""
    other = [
        path
        for path in FILES
        if path.startswith(("site/", "lean/", "products/"))
        and path.endswith((".yml", ".yaml", ".toml", ".lua", ".js", ".json", ".lean"))
    ]
    return sorted(
        {*ci_files(), *reached_scripts(), *python_sources(), *other, "pyproject.toml"}
    )


# --- The scan sees what it should. ---


def test_the_scan_sees_ci_the_build_the_package_and_the_pages():
    assert ".github/workflows/ci.yml" in ci_files()
    built = build_scripts()
    for script in (
        "scripts/verify.sh",
        "scripts/build-site.sh",
        "scripts/check-lesson-pages.sh",
        "scripts/check-lean.sh",
        "scripts/preflight.sh",
    ):
        assert script in built, script
    # The self-tests of the workflow, which CI runs with --all (ADR 005).
    assert any("./scripts/verify.sh --all" in read(path) for path in ci_files()), (
        "CI no longer runs verify.sh --all: revise what this test calls CI"
    )
    assert len(workflow_checks()) > 20
    tested = self_test_scripts()
    for script in (
        "tests/agent-test.sh",
        "tests/start-feature-test.sh",
        "tests/lib-fakes.sh",
        "scripts/start-feature.sh",
        "scripts/review-feature.sh",
        "scripts/lib/review-run.sh",
    ):
        assert script in tested, script
    assert set(tested) <= set(reached_scripts())
    sources = python_sources()
    assert "src/pbc/mechanics/resonance.py" in sources
    assert "src/pbc/verification/driven.py" in sources
    assert "site/lesson-previews.py" in sources
    assert "tests/unit/test_skills_boundary.py" in sources
    assert len(sources) > 400
    assert "site/lessons/mechanics/09-verifying-scientific-code/index.qmd" in pages()
    assert len(pages()) > 100


# --- A check can fail: the patterns on planted examples. ---


@pytest.mark.parametrize(
    "line",
    [
        'claude -p "fix the failing test"',
        "    run: codex exec --full-auto 'write the lesson'",
        "exec aider --yes --message-file task.md",
        'result="$(gemini --prompt "$task")"',
        "timeout 600 opencode run",
    ],
)
def test_a_command_that_starts_an_agent_is_found(line):
    assert COMMAND_WORD.search(line)


@pytest.mark.parametrize(
    "line",
    [
        "a coding agent, such as Claude Code or Codex, writes the file",
        "model: claude-fable-5-2",
        "export CODEX_HOME=/tmp/codex_home",
        "uv run --locked pytest tests/unit",
        "the constellation Gemini",
    ],
)
def test_a_mention_is_not_a_command(line):
    assert not COMMAND_WORD.search(line)


def test_an_argument_list_or_a_lookup_that_names_an_agent_is_found():
    assert agent_arguments('subprocess.run(["claude", "-p", task], check=True)')
    assert agent_arguments("path = shutil.which('codex')")
    assert agent_arguments('COMMAND = ("aider", "--yes")')
    assert not agent_arguments('RECORDED_WITH = "Claude Code, 2026-10-30"')
    assert not agent_arguments('model = "claude-fable-5-2"')
    # a mapping from the provider names of the workflow's configuration to
    # the words a page shows starts nothing
    assert not agent_arguments('SHOWN = {"claude": "Claude", "codex": "Codex"}')
    assert ARGUMENT.search('subprocess.run(["claude", "-p", task])')
    assert not ARGUMENT.search('model = "claude-fable-5-2"')


def test_running_and_sourcing_a_script_are_told_from_naming_it():
    text = """
# see ./scripts/start-feature.sh for the session
echo "then run ./scripts/finish-planning.sh" >&2
fail "revise with ./scripts/revise-planning.sh and review \\"again\\""
[[ -n "$reviews" ]] || fail "no review ($latest): ./scripts/review-planning.sh"
protected=(
  scripts/lib/agent.sh
)
for file in scripts/*.sh; do bash -n "$file"; done
"$root/scripts/build-site.sh" --quiet
source "$script_dir/lib/guardrails.sh"
for library in fingerprint verification; do
  source "$root/scripts/lib/$library.sh"
done
"""
    found, unresolved = runs(text)
    assert found == {
        "scripts/build-site.sh",
        "scripts/lib/guardrails.sh",
        "scripts/lib/fingerprint.sh",
        "scripts/lib/verification.sh",
    }
    assert unresolved == []
    assert runs('source "$root/scripts/lib/$other.sh"')[1]
    assert runs("./scripts/start-feature.sh 12")[0] == {"scripts/start-feature.sh"}
    # a failure text that runs a command is not only a message
    assert runs('fail "got $(./scripts/doctor.sh 2>&1)"')[0] == {"scripts/doctor.sh"}
    assert runs('bash -eo pipefail "$here/lib/agent.sh"')[0] == {LAUNCHER}
    # sourcing, however the path is written and wherever the command starts
    for line in (
        'source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/lib/agent.sh"',
        'x="$(source "$repo/scripts/lib/risk.sh" && source "$repo/scripts/lib/agent.sh',
        "  tree=\"$(bash -c 'source scripts/lib/risk.sh; source scripts/lib/agent.sh",
        'if true; then source "$source_root/scripts/lib/agent.sh"; fi',
    ):
        assert LAUNCHER in runs(line)[0], line
        assert runs(line)[1] == [], line
    assert runs('source "$source_root/tests/lib-fakes.sh"')[0] == {"tests/lib-fakes.sh"}
    # a word "source" that starts no command sources nothing
    assert runs('jq --arg source ".agents/reviews/r.sh" . file') == (set(), [])
    assert runs('expect "a source change" RISK_PATH_MIN 2') == (set(), [])
    # a file this function cannot name is reported
    assert runs('source "$RUN_CONTROL/$role.sh"')[1]
    assert runs('. "$venv/bin/activate"')[1]


def test_a_command_line_on_a_page_is_found_outside_a_marked_block_only():
    page = (
        "Run it:\n\n```bash\nclaude -p task.md\n```\n\n"
        "::: {.not-verified}\n```bash\n$ codex exec task.md\n```\n:::\n"
    )
    assert PAGE_COMMAND.search(page)
    assert [m.group(0).strip() for m in PAGE_COMMAND.finditer(page)] == [
        "claude",
        "$ codex",
    ]
    found = PAGE_COMMAND.findall(outside_not_verified(page))
    assert [command.strip() for command in found] == ["claude"]
    assert not PAGE_COMMAND.search("You can ask a coding agent, such as Claude Code.")


def test_a_credential_of_a_coding_agent_is_found():
    for text in (
        "env:\n  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}",
        'os.environ["CLAUDE_CODE_OAUTH_TOKEN"]',
        "cat ~/.codex/auth.json",
    ):
        assert CREDENTIALS.search(text), text
    assert not CREDENTIALS.search("GH_TOKEN: ${{ github.token }}")


def test_the_patterns_find_the_launcher_of_the_development_workflow():
    # The one place of the repository that starts a coding agent, on the
    # maintainer's machine: a real positive for the command pattern.
    assert LAUNCHER in FILES
    assert COMMAND_WORD.search(read(LAUNCHER))


def test_fakes_of_a_self_test_and_a_path_that_does_not_shadow_are_found():
    needed = {"claude", "codex"}
    own = """
for provider in codex claude; do
  cat >"$tmp/bin/$provider" <<'FAKE'
FAKE
done
export PATH="$tmp/bin:$PATH"
(PATH="$tmp/silent-bin:$PATH" agent_run unattended codex model "$dir" "prompt")
"""
    assert written_programs(own) == {"$tmp/bin": needed}
    assert fake_directories(own, needed) == {"$tmp/bin"}
    assert unshadowed_paths(own, needed) == []
    shared = """
source "$source_root/tests/lib-fakes.sh"
make_fake_agents "$tmp/bin"
    PATH="$tmp/bin:/usr/bin:/bin" MOCK_AGENT_LOG="$repo.log" ./scripts/start-feature.sh
"""
    assert fake_directories(shared, needed) == {"$tmp/bin"}
    assert unshadowed_paths(shared, needed) == []
    # the real program would be found first, or alone
    late = shared.replace('"$tmp/bin:/usr/bin:/bin"', '"/usr/bin:/bin:$tmp/bin"')
    assert unshadowed_paths(late, needed) == ["/usr/bin:/bin:$tmp/bin"]
    inherited = shared.replace('"$tmp/bin:/usr/bin:/bin"', '"$HOME/.local/bin:$PATH"')
    assert unshadowed_paths(inherited, needed) == ["$HOME/.local/bin:$PATH"]
    # the system directories alone: the case of a missing program
    system = shared + '  PATH="/usr/bin:/bin" ./scripts/start-planning.sh\n'
    assert unshadowed_paths(system, needed) == []
    assert unshadowed_paths(own.replace("export ", ""), needed) == [
        "$tmp/silent-bin:$PATH"
    ]
    # a fake of one program only, no fakes, no PATH
    one = own.replace("codex claude; do", "codex; do")
    assert unshadowed_paths(one, needed)[0] == "(no fakes)"
    assert unshadowed_paths("./scripts/start-feature.sh 12", needed) == ["(no fakes)"]
    assert unshadowed_paths(shared.split("    PATH=")[0], needed) == ["(no PATH)"]


HEREDOC = re.compile(r"""<<-?\s*(['"]?)(\w+)\1""")
# A string without a command substitution in it runs nothing.
QUOTED = re.compile(r""""(?:[^"$`\\]|\\.|\$(?!\())*"|'[^']*'""")
# A presence check names a program to look it up, not to run it.
PRESENCE = re.compile(r"""\b(?:have|command\s+-v|type\s+-[pP]|which|hash)\s+\S+""")
CASE_LABEL = re.compile(r"^\s*[\w:*.-]+(?:\s*\|\s*[\w:*.-]+)*\)")
LOOP_WORDS = re.compile(r"\bfor\s+\w+\s+in\s+[^;]*;")


def direct_starts(text: str) -> list[str]:
    """The code lines of a shell script that run an agent program by its name
    as a command word: not inside a heredoc (the body of a fake or a usage
    text), not in a string without a command substitution, not a presence
    check (``have claude``, ``command -v codex``), the label of a case, or
    the words of a loop; and not a line that writes a fake, whose target is
    a path (``>"$bin/claude"``) and so not a word of its own."""
    found = []
    ending = None
    for line in text.splitlines():
        if ending is not None:
            if line.strip() == ending:
                ending = None
            continue
        if heredoc := HEREDOC.search(line):
            ending = heredoc.group(2)
        if line.lstrip().startswith("#") or MESSAGE.match(line):
            continue
        code = LOOP_WORDS.sub("", PRESENCE.sub("", QUOTED.sub('""', line)))
        if CASE_LABEL.match(code):
            code = CASE_LABEL.sub("", code, count=1)
        if COMMAND_WORD.search(code):
            found.append(line.strip())
    return found


def reached_by_self_tests_outside_the_launcher() -> list[str]:
    """The scripts a self-test reaches that may not start an agent program
    themselves: all but the self-tests (tests/*-test.sh, held to their fakes
    above) and the launcher."""
    return [
        path
        for path in self_test_scripts()
        if path.endswith(".sh")
        and path != LAUNCHER
        and not re.fullmatch(r"tests/[\w-]+-test\.sh", path)
    ]


def test_a_direct_start_is_told_from_a_check_a_fake_and_a_message():
    planted = """
claude -p "fix the failing test"
result="$(codex exec "$task")"
  exec aider --yes
  claude -p task)
"""
    assert direct_starts(planted) == [
        'claude -p "fix the failing test"',
        'result="$(codex exec "$task")"',
        "exec aider --yes",
        "claude -p task)",
    ]
    not_starts = """
if have "$agent"; then ok "found"; fi
command -v claude >/dev/null || missing "claude CLI is not installed"
for agent in codex claude; do
  case "$agent" in
    codex) codex_roles+=" $role" ;;
    claude) claude_roles+=" $role" ;;
  esac
done
cat >"$bin/claude" <<'FAKE'
claude -p "the body of a fake"
FAKE
cat <<EOF
  $0 --agent claude --model fable
EOF
if [[ "$agent" == "codex" ]]; then :; fi
echo "run claude -p to start a session"
# claude -p in a comment
"""
    assert direct_starts(not_starts) == []


def test_no_script_a_self_test_reaches_starts_an_agent_outside_the_launcher():
    # A script a self-test reaches starts a program under an agent's name
    # only through the launcher, whose start the self-test shadows with its
    # fake (the test above). A direct start, with the PATH the script
    # inherits, could find an installed agent.
    reached = reached_by_self_tests_outside_the_launcher()
    for path in (
        "scripts/doctor.sh",
        "tests/lib-fakes.sh",
        "scripts/start-planning.sh",
    ):
        assert path in reached, path
    found = {path: lines for path in reached if (lines := direct_starts(read(path)))}
    assert found == {}


def test_a_planted_direct_start_in_a_reached_script_fails_the_boundary(monkeypatch):
    # A script reached by a self-test, here doctor.sh, with a line that runs
    # the program itself, without the launcher and with an inherited PATH.
    line = 'claude -p "check the setup"'
    planted = read("scripts/doctor.sh") + f"\n{line}\n"
    assert direct_starts(planted) == [line]
    real = read
    monkeypatch.setattr(
        sys.modules[__name__],
        "read",
        lambda path: planted if path == "scripts/doctor.sh" else real(path),
    )
    with pytest.raises(AssertionError, match="check the setup"):
        test_no_script_a_self_test_reaches_starts_an_agent_outside_the_launcher()


def test_an_installed_agent_is_found():
    for line in (
        "npm install -g @anthropic-ai/claude-code",
        "run: npm i -g @openai/codex",
        "uv tool install aider-chat",
        "curl -fsSL https://claude.ai/install.sh | bash",
    ):
        assert PACKAGES.search(line), line
    assert not PACKAGES.search("uv sync --locked --all-extras")


def test_a_module_that_reads_the_harness_key_is_found():
    assert reads_the_harness_key('key = os.environ["OPENAI_API_KEY"]')
    assert reads_the_harness_key('key = os.getenv("OPENAI_API_KEY")')
    assert reads_the_harness_key('os.environ.get(key="OPENAI_API_KEY")')
    bound = 'KEY_VARIABLE = "OPENAI_API_KEY"\nsecret = Secret.read(KEY_VARIABLE)'
    assert reads_the_harness_key(bound, {"KEY_VARIABLE"})
    assert reads_the_harness_key("os.environ[openai.KEY_VARIABLE]", {"KEY_VARIABLE"})
    # telling the learner to set the variable reads nothing
    assert not reads_the_harness_key('HINT = " (with OPENAI_API_KEY set)"')
    assert not reads_the_harness_key(
        'LIVE = "OPENAI_API_KEY"\nlines = [f"export {LIVE}=..."]', {"LIVE"}
    )


# --- The boundary. ---


def test_no_ci_job_check_or_build_script_starts_a_coding_agent():
    # The build side. The self-tests of the workflow do name the programs:
    # the tests below say what they start.
    found = {
        name: match.group(0)
        for name, text in build_like().items()
        if (match := COMMAND_WORD.search(text))
    }
    assert found == {}


# The files a self-test sources that it wrote itself, in its temporary
# directory: the replies run-feature-test.sh gives its fake agent.
WRITTEN_BY_THE_TEST = {"tests/run-feature-test.sh": '"$RUN_CONTROL/'}


def test_every_sourced_file_of_a_reached_script_is_known():
    # The reach is only as good as what it can read: a script that sources
    # a file by a name this test cannot resolve fails here, not silently.
    unresolved = {}
    for path in reached_scripts():
        if not path.endswith(".sh"):
            continue
        own = WRITTEN_BY_THE_TEST.get(path)
        if lines := [x for x in runs(read(path))[1] if not (own and own in x)]:
            unresolved[path] = lines
    assert unresolved == {}


def test_the_build_side_of_ci_does_not_reach_the_launcher():
    built = build_scripts()
    assert LAUNCHER not in built
    # The scripts that source the launcher are the development workflow's,
    # and none of them is on the build side either.
    launching = [
        path
        for path in FILES
        if path.startswith("scripts/") and LAUNCHER in runs(read(path))[0]
    ]
    assert "scripts/start-feature.sh" in launching
    assert "scripts/review-feature.sh" in launching
    assert "scripts/start-planning.sh" in launching
    assert set(launching).isdisjoint(built)
    call = re.compile(r"\bagent_(?:run|resolve|parse_args)\b")
    found = [
        name
        for name, text in build_like().items()
        if call.search("\n".join(code_lines(text)))
    ] + [path for path in python_sources() if "lib/agent.sh" in read(path)]
    assert found == []


def test_ci_reaches_the_launcher_through_the_workflow_self_tests():
    # Stated as it is: the self-tests CI runs with --all load the launcher,
    # and some of them call the function that starts a program.
    assert LAUNCHER in self_test_scripts()
    starting = starting_self_tests()
    for name in ("agent", "start-feature", "review-feature", "start-planning"):
        assert name in starting, name
    assert all(
        re.fullmatch(r"tests/[\w-]+-test\.sh", script) for script in starting.values()
    ), starting


def test_the_launcher_starts_a_program_in_one_function_only():
    # What "can start an agent" means above: a call of agent_run. Before
    # that function, the launcher names the programs only as the labels of
    # a case and in the text of a message; nothing after it is another
    # function.
    text = read(LAUNCHER)
    before, _, after = text.partition("\nagent_run() {\n")
    assert after, "the launcher has no function agent_run"
    label = re.compile(r"^\s*[\w:|* -]+\)\s*(?:;;)?\s*$")
    found = [
        line.strip()
        for line in code_lines(before)
        if COMMAND_WORD.search(re.sub(r'"[^"]*"', '""', line)) and not label.match(line)
    ]
    assert found == []
    assert not re.search(r"(?m)^\w+\(\) \{$", after)
    assert launcher_programs() == {"claude", "codex"}


def test_a_self_test_that_can_start_an_agent_starts_its_own_fake():
    # Each one makes a fake of every program the launcher starts, and every
    # PATH it sets begins with the directory of those fakes: the program a
    # command of the test finds under an agent's name is the fake.
    needed = launcher_programs()
    shared = written_programs(read("tests/lib-fakes.sh"))
    assert needed <= shared["$bin"]
    found = {
        script: paths
        for script in starting_self_tests().values()
        if (paths := unshadowed_paths(read(script), needed))
    }
    assert found == {}


def test_nothing_ci_runs_installs_a_coding_agent():
    # The fakes are the only programs of those names in CI: no workflow,
    # action, check, or reached script installs one.
    found = {
        name: match.group(0)
        for name, text in shell_like().items()
        if (match := PACKAGES.search(text))
    }
    for path in ("pyproject.toml", *(p for p in FILES if p.endswith("package.json"))):
        if match := PACKAGES.search(read(path)):
            found[path] = match.group(0)
    assert found == {}


def test_no_module_page_product_or_test_starts_a_coding_agent():
    found = {
        path: names[0]
        for path in python_sources()
        if (names := agent_arguments(read(path)))
    }
    for path in pages():
        text = outside_not_verified(read(path))
        if match := (PAGE_COMMAND.search(text) or ARGUMENT.search(text)):
            found[path] = match.group(0)
    assert found == {}


def test_no_credential_of_a_coding_agent_is_named_in_ci_or_the_build():
    suites = tuple(PYTHON_SUITES)
    found = {
        path: match.group(0)
        for path in (*build_inputs(), *pages(), ".env.example")
        if not path.startswith(suites) and (match := CREDENTIALS.search(read(path)))
    }
    for name, command in shell_like().items():
        if name.startswith("verify") and (match := CREDENTIALS.search(command)):
            found[name] = match.group(0)
    assert found == {}
    # build_inputs() holds the self-tests of the workflow and what they
    # reach: the launcher and its tests name no credential either.
    assert {LAUNCHER, "tests/agent-test.sh", "tests/lib-fakes.sh"} <= set(
        build_inputs()
    )


def test_a_test_names_such_a_credential_only_to_remove_it():
    # Some tests delete provider keys from the environment to show that a
    # replay needs none. No test reads one.
    reading = re.compile(rf"(?:environ|getenv|setenv)[^\n]*(?:{CREDENTIALS.pattern})")
    found = [
        path
        for path in python_sources()
        if path.startswith(tuple(PYTHON_SUITES)) and reading.search(read(path))
    ]
    assert found == []


def test_ci_holds_no_secret_but_the_workflows_own_token():
    for path in ci_files():
        text = read(path)
        assert set(re.findall(r"secrets\.(\w+)", text)) <= CI_TOKENS, path
        named = set(re.findall(r"\b[A-Z][A-Z0-9_]*_(?:API_KEY|TOKEN|SECRET)\b", text))
        assert named <= CI_TOKENS, (path, named)


def test_the_harness_key_is_named_by_no_ci_job_check_or_build_script():
    found = [name for name, text in shell_like().items() if HARNESS_KEY in text]
    assert found == []
    # .env.example lists names only, each on a comment line.
    for line in read(".env.example").splitlines():
        assert not line.strip() or line.startswith("#"), line


def test_only_the_provider_client_reads_the_harness_key():
    # Other modules and pages name the variable to tell the learner to set
    # it. One module hands its name to a call: the client of the provider.
    holders = key_holders()
    assert "KEY_VARIABLE" in holders
    reading = [
        path
        for path in python_sources()
        if path.startswith(("src/", "site/", "products/"))
        and reads_the_harness_key(read(path), holders)
    ]
    assert reading == [HARNESS_CLIENT]
    # No executed cell of a page names it, outside a "not verified" block.
    cells = {
        path: cell
        for path in pages()
        for cell in EXECUTED_CELL.findall(outside_not_verified(read(path)))
        if HARNESS_KEY in cell or any(name in cell for name in holders)
    }
    assert cells == {}


def test_no_file_of_the_build_or_the_checks_depends_on_the_coding_template():
    found = [path for path in build_inputs() if TEMPLATE.search(read(path))]
    found += [
        f"verify.conf:{name}"
        for name, command in verify_conf.checks().items()
        if TEMPLATE.search(command)
    ]
    assert found == []


# --- Transcripts. ---


def test_no_transcript_of_an_agent_session_is_a_file_of_the_build():
    found = [
        path
        for path in FILES
        if path.startswith(("site/", "src/", "data/", "products/", "lean/"))
        and "transcript" in Path(path).name.lower()
    ]
    assert found == []


def test_an_example_transcript_on_a_page_is_marked_with_the_agent_and_the_date():
    marked = 0
    for path in pages():
        text = read(path)
        blocks = [match.group(0) for match in NOT_VERIFIED.finditer(text)]
        for position in (m.start() for m in re.finditer(r"Example transcript", text)):
            block = next(
                (b for b in blocks if text.find(b) <= position < text.find(b) + len(b)),
                None,
            )
            assert block is not None, f"{path}: a transcript outside 'not verified'"
            assert re.search(r"Agent: \S", block), path
            assert re.search(r"Date: \d{4}-\d{2}-\d{2}", block), path
            marked += 1
    assert marked >= 1  # the lesson on verifying scientific code shows one


def test_the_workflow_document_states_the_profile_the_page_states():
    workflow = read("docs/coding-agent-workflow.md")
    page = read("site/lessons/mechanics/09-verifying-scientific-code/index.qmd")
    for rule in (
        "A scratch checkout.",
        "An allowlist of commands.",
        "No network beyond the agent's own provider.",
        "A budget, set before the start",
    ):
        assert rule in workflow, rule
        assert rule in page, rule
    assert "Read every diff before you run it." in page
    assert "Every diff is read before it is run." in workflow
    assert "credential stays in" in workflow and "credential stays in" in page
    # Rule 4 names the credential files, in the same words in both places.
    files = (
        "A credential stored in a file the agent's commands can read (an SSH"
        " key, the configuration of a cloud tool, a stored Git credential, the"
        " agent's own login) is just as readable to them, wherever the checkout"
        " is: only a container or a separate machine keeps such a file out of"
        " reach."
    )
    for text in (workflow, page):
        assert files in " ".join(text.split())
