"""Agent skills stay development guidance (ADR 019 decision 1, invariant
I32): no workflow, script, check, build step, or CI job invokes, installs,
fetches, or reads a skill, except the skills configuration check, which
validates .agents/skills/ as data; and the structural checks pass on a copy
of the repository without the directory. F45 extends this boundary to coding
agents (I24)."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest
from support import verify_conf

ROOT = Path(__file__).parents[2]
SKILLS = ".agents/skills"
# The one reader of the directory and its tests.
READERS = {"src/pbc/skills.py"}
TESTS = {"tests/unit/test_skills_config.py", "tests/unit/test_skills_boundary.py"}
# What the build, the checks, CI, and the site are made of. The documentation,
# the plans, and the role prompts describe the skills and are not listed.
MACHINERY = ("scripts/", ".github/", "site/", "src/", "lean/", "tests/", "data/")
MANIFESTS = {"pyproject.toml", "uv.lock", ".gitignore"}
# A command that would install, fetch, or start a skill or its tooling.
INSTALLERS = re.compile(
    r"skills?[ -](?:install|add)\b|skill-installer|plugin\s+(?:install|marketplace)"
    r"|npx\s+skills|\bimpeccable\b|\.impeccable|diagram-design|frontend-design"
    r"|pbc-scientific-visualization|pbc-physics-teaching",
    re.IGNORECASE,
)
# The checks of the group default that need only the files: the structural
# checks of the workflow and the documentation. The others of the group are
# the supply-chain contract of the machine (preflight) and the dataset check,
# which reads data/ only.
STRUCTURAL = ("template-structure", "shell-syntax", "docs-scripts", "docs-references")


def project_files() -> list[str]:
    listed = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    return sorted(
        path for path in listed.split("\0") if path and (ROOT / path).is_file()
    )


def machinery() -> list[str]:
    return [
        path
        for path in project_files()
        if (path.startswith(MACHINERY) or path in MANIFESTS)
        and not path.startswith(SKILLS + "/")
        and path not in READERS | TESTS
    ]


def test_the_machinery_is_scanned():
    files = machinery()
    for expected in (
        "scripts/verify.sh",
        ".github/workflows/ci.yml",
        "site/_quarto.yml",
    ):
        assert expected in files
    assert len(files) > 300


def test_nothing_but_the_check_names_the_skills_directory():
    named = [
        path
        for path in machinery()
        if path != "scripts/verify.conf"
        and "agents/skills" in (ROOT / path).read_text(errors="replace")
    ]
    assert named == [], "only pbc.skills reads .agents/skills/ (ADR 019 decision 1)"


def test_nothing_installs_fetches_or_starts_a_skill():
    found = {}
    for path in machinery():
        if path == "scripts/verify.conf":
            continue
        match = INSTALLERS.search((ROOT / path).read_text(errors="replace"))
        if match:
            found[path] = match.group(0)
    assert found == {}


def test_one_ungrouped_check_reads_the_skills_and_no_other_does():
    commands = verify_conf.checks()
    readers = [
        name
        for name, command in commands.items()
        if "pbc.skills" in command or "agents/skills" in command
        or INSTALLERS.search(command)
    ]  # fmt: skip
    assert readers == ["skills-config"]
    assert commands["skills-config"] == "uv run --locked python -m pbc.skills"
    assert verify_conf.groups()["skills-config"] == verify_conf.DEFAULT_GROUP
    assert verify_conf.DEFAULT_GROUP in verify_conf.targeted()


def test_the_check_reads_the_files_as_data():
    source = (ROOT / "src/pbc/skills.py").read_text()
    for forbidden in (
        "subprocess",
        "import os",
        "exec(",
        "eval(",
        "importlib",
        "urllib",
    ):
        assert forbidden not in source


@pytest.fixture(scope="module")
def copy_without_skills(tmp_path_factory):
    copy = tmp_path_factory.mktemp("without-skills") / "repository"
    for path in project_files():
        if path.startswith(SKILLS + "/"):
            continue
        target = copy / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / path, target)
    git = ["git", "-c", "user.name=test", "-c", "user.email=test@example.org"]
    subprocess.run(["git", "init", "-q"], cwd=copy, check=True)
    subprocess.run(["git", "add", "-A"], cwd=copy, check=True)
    subprocess.run([*git, "commit", "-qm", "copy"], cwd=copy, check=True)
    assert not (copy / SKILLS).exists()
    return copy


@pytest.mark.parametrize("name", STRUCTURAL)
def test_the_structural_checks_pass_without_the_skills(copy_without_skills, name):
    result = subprocess.run(
        ["bash", "-eo", "pipefail", "-c", verify_conf.command(name)],
        cwd=copy_without_skills,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
