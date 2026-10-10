"""The setup page keeps to what the build checks (F39, architecture I8).

Every command on the page is one of three kinds: a required setup command,
which equals CI's; a command that is also a check of ./scripts/verify.sh; or
a command in a "not verified" block that names what it needs. A command of
any other kind fails here, so the page cannot drift from what CI runs.
"""

import re
from dataclasses import dataclass

import pytest
import yaml
from support.paths import REPO_ROOT
from support.verify_conf import checks

PAGE = REPO_ROOT / "site" / "reproduce.qmd"
CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"

_FENCE = re.compile(r"^```\{?\.?(bash)\b([^}]*)\}?\s*$")
_BARE_FENCE = re.compile(r"^```bash\s*$")


@dataclass
class Block:
    classes: set[str]
    commands: list[str]  # without comments and blank lines
    lines: list[str]
    verified: bool  # not inside a ".not-verified" div
    section: str


def blocks() -> list[Block]:
    result: list[Block] = []
    lines = PAGE.read_text().splitlines()
    divs: list[bool] = []  # per open div: is it a not-verified div
    section = ""
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if line.startswith("## "):
            section = line[3:].strip()
        elif line.startswith(":::"):
            if line.strip() == ":::":
                divs.pop()
            else:
                divs.append(".not-verified" in line)
        elif line.startswith("```"):
            match = _FENCE.match(line) or _BARE_FENCE.match(line)
            body: list[str] = []
            while not lines[index].startswith("```"):
                body.append(lines[index])
                index += 1
            index += 1
            if match is None:
                continue
            attributes = match.group(2) if match.groups() else ""
            result.append(
                Block(
                    classes=set(re.findall(r"\.([\w-]+)", attributes)),
                    commands=[
                        text
                        for text in (entry.strip() for entry in body)
                        if text and not text.startswith("#")
                    ],
                    lines=body,
                    verified=not any(divs),
                    section=section,
                )
            )
    return result


def ci_commands() -> list[str]:
    """The commands CI runs to prepare the runner and to verify."""
    workflow = yaml.safe_load(CI.read_text())
    steps = {step.get("name"): step for step in workflow["jobs"]["verify"]["steps"]}
    install = steps["Install the Python environment and the browser build"]["run"]
    verify = steps["Verify"]["run"]
    return [
        *(line.strip() for line in install.splitlines() if line.strip()),
        verify.strip(),
    ]


def setup_block(system: str) -> Block:
    found = [b for b in blocks() if {"required-setup", system} <= b.classes]
    assert len(found) == 1, f"expected one required-setup block for {system}"
    return found[0]


def test_required_setup_on_linux_is_what_ci_runs():
    commands = setup_block("linux").commands
    clone, cd, *rest = commands
    assert clone.startswith("git clone https://github.com/")
    assert cd.startswith("cd ")
    ci = ci_commands()
    # CI verifies with --all, which adds the workflow self-tests; a learner
    # does not need them.
    assert ci[-1] == "./scripts/verify.sh --all"
    assert rest == [*ci[:-1], "./scripts/verify.sh"]


def test_required_setup_on_macos_differs_only_by_the_system_libraries():
    linux = setup_block("linux").commands
    macos = setup_block("macos").commands
    assert macos == [c.replace(" --with-deps", "") for c in linux]
    assert macos != linux


def test_every_command_is_required_verified_or_marked_not_verified():
    unmarked = []
    verify_commands = set(checks().values()) | set(ci_commands())
    for block in blocks():
        if "required-setup" in block.classes:
            continue
        if "verified-by-ci" in block.classes:
            assert block.verified
            for command in block.commands:
                assert command in verify_commands, command
        elif block.verified:
            unmarked.append(block.commands)
    assert not unmarked, f"commands outside the verified kinds: {unmarked}"


def test_optional_commands_name_what_they_need():
    optional = [b for b in blocks() if b.section.startswith("Optional: ")]
    assert len(optional) == 3
    for block in optional:
        assert not block.verified
    # The two workflows with an account name it, and the key goes to the
    # environment, never into a file.
    live, agent, lean = optional
    assert any(line.startswith("# needs: ") for line in live.lines)
    assert any(line.startswith("# needs: ") for line in agent.lines)
    assert 'export OPENAI_API_KEY="..."' in live.commands[1]
    assert not any(line.startswith("# needs: ") for line in lean.lines)


def test_the_page_does_not_hold_a_key():
    text = PAGE.read_text()
    assert not re.search(r"sk-[A-Za-z0-9]{8,}", text)


@pytest.mark.parametrize("command", ["quarto preview", "playwright install-deps"])
def test_commands_the_build_cannot_run_are_not_in_a_verified_block(command: str):
    for block in blocks():
        if block.verified and "required-setup" not in block.classes:
            assert not any(command in c for c in block.commands)
