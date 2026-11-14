"""The checks of the built site and the integration tests are divided, and
the divisions lose nothing.

``scripts/verify.conf`` declares the checks of the built site as several
checks, so that CI can run them side by side (docs/development.md, "The
checks of the built site"), and the integration tests as three checks since
F119 (docs/verification-audit.md, "Division into independent parts"). These
tests collect what each of them would run, without a browser and without a
built site, and compare it with everything in the directory it divides.
"""

import shlex
import subprocess
import sys

import pytest
from support import verify_conf
from support.checks import output, run_check
from support.paths import REPO_ROOT

PREFIX = "site-checks-"
# The divided checks: the prefix of their names and the directory they divide.
DIVISIONS = {PREFIX: "tests/e2e", "check-tests-": "tests/integration"}

# The checks of verify.conf before the checks of the built site and the
# integration tests were divided. Each still exists; 'site-checks' is now the
# checks named 'site-checks-*', and 'check-tests' the checks 'check-tests-*'.
ORIGINAL = [
    "preflight",
    "preflight-test",
    "lint",
    "format",
    "unit-tests",
    "dataset-checks",
    "lean-build",
    "check-tests",
    "lesson-checks",
    "site-build",
    "site-checks",
    "determinism",
    "template-structure",
    "shell-syntax",
    "docs-scripts",
    "docs-references",
    "documentation",
]
# The checks added since, outside the divisions: the per-lesson check of the
# targeted run (F119), the skills configuration check (F122), the starter
# checks of the Part B products (F138), and the check that the approved
# planning does not drift (Issue #512).
ADDED = ["lesson-pages", "skills-config", "starters", "planning-drift"]


def _collected(result: subprocess.CompletedProcess[str]) -> list[str]:
    assert result.returncode == 0, output(result)
    return [line for line in result.stdout.splitlines() if "::" in line]


@pytest.fixture(scope="module")
def all_parts() -> dict[str, dict[str, list[str]]]:
    """What the checks of each division collect, by prefix and check."""
    return {
        prefix: {
            name: _collected(run_check(name, "--collect-only", "-q"))
            for name in verify_conf.checks()
            if name.startswith(prefix)
        }
        for prefix in DIVISIONS
    }


@pytest.fixture(scope="module")
def parts(all_parts) -> dict[str, list[str]]:
    return all_parts[PREFIX]


@pytest.fixture(scope="module")
def everything() -> dict[str, list[str]]:
    """Every test of each divided directory, by prefix."""
    found = {}
    for prefix, directory in DIVISIONS.items():
        result = subprocess.run(
            [sys.executable, "-m", "pytest", directory, "--collect-only", "-q"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        found[prefix] = _collected(result)
    return found


@pytest.mark.parametrize("prefix", DIVISIONS)
def test_the_parts_together_are_every_test_of_the_directory(
    all_parts, everything, prefix
):
    together = [test for tests in all_parts[prefix].values() for test in tests]
    assert sorted(together) == sorted(everything[prefix])


@pytest.mark.parametrize("prefix", DIVISIONS)
def test_no_test_runs_in_two_parts(all_parts, prefix):
    seen: dict[str, str] = {}
    for name, tests in all_parts[prefix].items():
        for test in tests:
            assert test not in seen, f"{test} runs in {seen[test]} and in {name}"
            seen[test] = name


@pytest.mark.parametrize("prefix", DIVISIONS)
def test_no_part_is_empty(all_parts, prefix):
    parts = all_parts[prefix]
    assert len(parts) >= 2
    for name, tests in parts.items():
        assert tests, f"{name} runs no test"


def test_every_part_is_pytest_on_the_directory_it_divides():
    # A part that ran something else would not be part of its division.
    for name, command in verify_conf.checks().items():
        for prefix, directory in DIVISIONS.items():
            if name.startswith(prefix):
                words = shlex.split(command)
                assert words[:4] == ["uv", "run", "--locked", "pytest"], name
                assert words[4].startswith(directory), name


def test_the_named_files_of_the_integration_parts_exist_and_the_rest_runs_the_others():
    # Two parts name their files; the third runs the directory without
    # exactly those files, so a renamed file fails the part that names it
    # and a new file runs in the third without a change.
    named = {}
    for name in ("check-tests-quarto", "check-tests-browser"):
        words = shlex.split(verify_conf.command(name))[4:]
        assert words and all(w.startswith("tests/integration/test_") for w in words)
        assert all((REPO_ROOT / w).is_file() for w in words), name
        named[name] = words
    files = [*named["check-tests-quarto"], *named["check-tests-browser"]]
    assert len(files) == len(set(files)), "a file is named in two parts"
    words = shlex.split(verify_conf.command("check-tests-other"))[4:]
    assert words[0] == "tests/integration"
    ignored = [w.removeprefix("--ignore=") for w in words[1:]]
    assert all(w.startswith("--ignore=") for w in words[1:])
    assert sorted(ignored) == sorted(files)


def test_every_check_from_before_the_division_is_still_a_check():
    names = list(verify_conf.checks())
    undivided = list(names)
    for prefix in DIVISIONS:
        divided = [name for name in names if name.startswith(prefix)]
        assert divided, prefix
        assert prefix.rstrip("-") not in names
        undivided = [name for name in undivided if not name.startswith(prefix)]
    before = [*undivided, *(p.rstrip("-") for p in DIVISIONS)]
    assert sorted(before) == sorted([*ORIGINAL, *ADDED])
    assert len(names) == len(set(names))


def test_a_part_is_in_the_group_of_the_build_or_in_a_group_of_its_own():
    # The part that compares bytes with the built site runs with the build,
    # on one machine. Every other part can run beside the others.
    groups = verify_conf.groups()
    assert groups["site-build"] == "build"
    assert groups["determinism"] == "build"
    assert groups[f"{PREFIX}reproduction"] == "build"
    own = [
        groups[name]
        for name in groups
        if name.startswith(PREFIX) and groups[name] != "build"
    ]
    assert len(own) == len(set(own)) and len(own) >= 2
    others = {groups[name] for name in groups if not name.startswith(PREFIX)}
    assert not others & set(own)
    assert verify_conf.DEFAULT_GROUP not in own


def test_the_part_on_the_machine_of_the_build_is_what_compares_bytes(parts):
    # Exactly the tests that are marked for it, and every one of them.
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/e2e",
            "-m",
            "same_machine",
            "--co",
            "-q",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    marked = _collected(result)
    assert marked
    assert sorted(parts[f"{PREFIX}reproduction"]) == sorted(marked)
    for name, tests in parts.items():
        if name != f"{PREFIX}reproduction":
            assert not set(tests) & set(marked), name


def test_every_check_has_one_group_and_verify_sh_lists_those_groups():
    # verify.sh runs a group with --only; a group it does not list could not
    # be run, and a check in no listed group would run in no job of a CI
    # that runs each group.
    result = subprocess.run(
        ["./scripts/verify.sh", "--groups"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, output(result)
    listed = result.stdout.split()
    assert len(listed) == len(set(listed))
    groups = verify_conf.groups()
    assert set(groups) == set(verify_conf.checks())
    # The workflow self-tests have no group of their own: they are 'default'.
    assert set(listed) == set(groups.values()) | {verify_conf.DEFAULT_GROUP}


def test_one_test_can_be_selected_from_a_part(parts):
    # Rerunning one failing test with the command of its check works: what the
    # selection leaves out is not reported as missing from the division.
    name = "site-checks-pages-2"
    test = parts[name][0]
    file = test.split("::")[0]
    command = verify_conf.command(name).replace(f" {file} ", f" '{test}' ")
    assert command != verify_conf.command(name)
    result = subprocess.run(
        ["bash", "-c", f"{command} --collect-only -q"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert _collected(result) == [test]


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (["tests/e2e/test_built_site.py", "--shard", "3/2"], "expected <part>/<parts>"),
        (["tests/e2e/test_built_site.py", "--shard", "1/3"], "divided in 2 parts"),
        (["tests/e2e/test_home.py", "--shard", "1/2"], "has no division"),
    ],
)
def test_a_division_that_does_not_exist_is_an_error_and_runs_nothing(
    arguments, message
):
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *arguments, "--collect-only", "-q"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 4, output(result)
    assert message in output(result)
