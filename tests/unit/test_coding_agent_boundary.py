"""Coding agents run only on the learner's machine (ADR 010 decision 6,
invariant I24; ``docs/coding-agent-workflow.md``): nothing CI or the build
is made of starts a coding agent, reaches the launcher of the development
workflow, names a coding agent's credential, or depends on the Agentic
Coding Template (ADR 022 decision 7); and a transcript of an agent session
is an example on a page, marked "not verified" with the agent and the date,
never a file the build reads.

This extends ``test_skills_boundary.py``, the boundary of the agent skills
(I32). What "CI and the build" are made of is computed: the CI workflows,
the checks of ``scripts/verify.conf``, every script those reach by name,
the site, the package, the products' code, and the test suites CI runs. The
development workflow (``scripts/*-feature.sh``, ``scripts/lib/agent.sh``)
does start a coding agent, on the maintainer's machine (ADR 006): the test
shows that its patterns find that launcher, and that nothing of CI or the
build reaches it.
"""

import ast
import re
import subprocess
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
# How a script or a command runs another script: by its path after "./", after
# a variable that holds a directory, or after "bash"; and how it sources one.
# A path that is only named (in a message, a comment, a list of protected
# files, or a loop that reads or syntax-checks files) runs nothing.
RUNS = re.compile(
    r"""(?:\./|\$\{?\w+\}?"?/|\bbash\s+(?:-[a-z]+\s+)*"?)"""
    r"""((?:(?:scripts|tests)/)?(?:lib/)?[\w.-]+\.(?:sh|py))"""
)
SOURCES = re.compile(r"""^\s*(?:source|\.)\s+(\S+)""")
LOOP = re.compile(r"^\s*for\s+(\w+)\s+in\s+(.+?);\s*do\b")
MESSAGE = re.compile(r"^\s*(?:echo|printf)\b")
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
        found |= {s for m in RUNS.finditer(line) if (s := _script(m.group(1)))}
        if sourced := SOURCES.match(line):
            path = sourced.group(1).strip('"')
            variable = re.search(r"/lib/\$\{?(\w+)\}?\.sh$", path)
            names = (
                [f"lib/{word}.sh" for word in loops.get(variable.group(1), [])]
                if variable
                else re.findall(r"(lib/[\w.-]+\.sh)$", path)
            )
            scripts = [script for name in names if (script := _script(name))]
            if not scripts:
                unresolved.append(line.strip())
            found |= set(scripts)
    return found, unresolved


def reached_scripts() -> list[str]:
    """The scripts CI and the checks of verify.conf run: those they run by
    path, and those a reached script runs or sources, to any depth."""
    start = "\n".join([*map(read, ci_files()), *verify_conf.checks().values()])
    reached: set[str] = set()
    queue = sorted(runs(start)[0])
    while queue:
        path = queue.pop()
        if path in reached:
            continue
        reached.add(path)
        if path.endswith(".sh"):
            queue += sorted(runs(read(path))[0])
    return sorted(reached)


def shell_like() -> dict[str, str]:
    """What runs as commands in CI and the build, by a name for the report."""
    texts = {path: read(path) for path in (*ci_files(), *reached_scripts())}
    texts.update(
        {f"verify.conf:{name}": cmd for name, cmd in verify_conf.checks().items()}
    )
    return texts


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
    reached = reached_scripts()
    for script in (
        "scripts/verify.sh",
        "scripts/build-site.sh",
        "scripts/check-lesson-pages.sh",
        "scripts/check-lean.sh",
        "scripts/preflight.sh",
    ):
        assert script in reached, script
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
    assert runs('bash -eo pipefail "$here/lib/agent.sh"')[0] == {LAUNCHER}


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


# --- The boundary. ---


def test_no_ci_job_check_or_build_script_starts_a_coding_agent():
    found = {
        name: match.group(0)
        for name, text in shell_like().items()
        if (match := COMMAND_WORD.search(text))
    }
    assert found == {}


def test_every_sourced_file_of_a_reached_script_is_known():
    # The reach is only as good as what it can read: a script that sources
    # a file by a name this test cannot resolve fails here, not silently.
    unresolved = {
        path: lines
        for path in reached_scripts()
        if path.endswith(".sh") and (lines := runs(read(path))[1])
    }
    assert unresolved == {}


def test_nothing_ci_or_the_build_runs_reaches_the_launcher():
    reached = reached_scripts()
    assert LAUNCHER not in reached
    # The scripts that source the launcher are the development workflow's,
    # and none of them is reached either.
    launching = [
        path
        for path in FILES
        if path.startswith("scripts/") and LAUNCHER in runs(read(path))[0]
    ]
    assert "scripts/start-feature.sh" in launching
    assert "scripts/review-feature.sh" in launching
    assert set(launching).isdisjoint(reached)
    call = re.compile(r"\bagent_(?:run|resolve|parse_args)\b")
    found = [
        name
        for name, text in shell_like().items()
        if call.search("\n".join(code_lines(text)))
    ] + [path for path in python_sources() if "lib/agent.sh" in read(path)]
    assert found == []


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
    for name, command in verify_conf.checks().items():
        if match := CREDENTIALS.search(command):
            found[f"verify.conf:{name}"] = match.group(0)
    assert found == {}


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
