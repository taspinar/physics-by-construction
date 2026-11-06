"""The starter checks of ADR 022 decision 5 (F138): the current-tree check
runs a starter's tests against the working tree; the at-pin check installs
the pinned commit from the repository's own history, without a fetch, and
fails on a broken pin; a `pending` pin is skipped and the skip named. Shown
on temporary repositories whose package ``pbc`` says which commit it is."""

import subprocess
from pathlib import Path

import pytest

from pbc.products import starters

ROOT = Path(__file__).parents[2]

STARTER_TEST = """
import pbc

def test_the_installed_pbc_is_the_good_one():
    assert pbc.GOOD, pbc.__file__
"""


def git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        [
            "git",
            "-c",
            "user.name=test",
            "-c",
            "user.email=test@example.org",
            *arguments,
        ],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def write_pin(repository: Path, pin: str) -> None:
    starter = repository / "products" / "lab" / "starter"
    (starter / "pyproject.toml").write_text(
        '[project]\nname = "lab"\nversion = "0"\ndependencies = ["pbc"]\n'
        "[tool.uv.sources]\n"
        f'pbc = {{ git = "https://example.org/pbc", rev = "{pin}" }}\n'
    )


@pytest.fixture
def repository(tmp_path):
    """A repository with a starter, whose first commit has a good ``pbc``
    and whose second commit breaks it; the working tree has a good one
    again."""
    repo = tmp_path / "repo"
    (repo / "src" / "pbc").mkdir(parents=True)
    starter = repo / "products" / "lab" / "starter"
    (starter / "tests").mkdir(parents=True)
    (starter / "tests" / "test_lab.py").write_text(STARTER_TEST)
    write_pin(repo, "pending")
    package = repo / "src" / "pbc" / "__init__.py"
    git(tmp_path, "init", "-q", str(repo))
    package.write_text("GOOD = True\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "good")
    good = git(repo, "rev-parse", "HEAD")
    package.write_text("GOOD = False\n")
    git(repo, "commit", "-qam", "broken")
    broken = git(repo, "rev-parse", "HEAD")
    package.write_text("GOOD = True\n")  # the working tree is good again
    return repo, good, broken


def outcome(repo: Path, check: str) -> starters.Outcome:
    [found] = [o for o in starters.check_all(repo) if o.check == check]
    return found


def test_a_pending_pin_is_skipped_and_the_skip_named(repository, capsys):
    repo, _, _ = repository
    skipped = outcome(repo, "at pin")
    assert skipped.status == "skipped"
    assert "`pending`" in skipped.detail
    assert starters.main(["--root", str(repo)]) == 0
    printed = capsys.readouterr().out
    assert "products/lab/starter, at pin: skipped. the pin is `pending`" in printed


def test_the_current_tree_check_runs_the_working_tree(repository):
    repo, _, _ = repository
    assert outcome(repo, "current tree").status == "passed"
    (repo / "src" / "pbc" / "__init__.py").write_text("GOOD = False\n")
    failed = outcome(repo, "current tree")
    assert failed.status == "failed"
    assert starters.main(["--root", str(repo)]) == 1


def test_the_at_pin_check_installs_the_pinned_commit_from_the_history(repository):
    repo, good, broken = repository
    write_pin(repo, good)
    passed = outcome(repo, "at pin")
    assert passed.status == "passed", passed.detail
    assert good in passed.detail
    # The working tree is good, the pinned commit is not: the check runs the
    # pinned commit, so it fails.
    write_pin(repo, broken)
    assert outcome(repo, "at pin").status == "failed"
    assert outcome(repo, "current tree").status == "passed"


@pytest.mark.parametrize(
    ("pin", "reason"),
    [
        ("main", "not the full hash"),
        ("abc123", "not the full hash"),
        ("0" * 40, "not a commit in the repository's history"),
    ],
)
def test_a_broken_pin_fails(repository, pin, reason):
    repo, _, _ = repository
    write_pin(repo, pin)
    failed = outcome(repo, "at pin")
    assert failed.status == "failed"
    assert reason in failed.detail


def test_a_pin_outside_the_history_of_head_fails(repository):
    repo, good, _ = repository
    git(repo, "checkout", "-q", "--orphan", "elsewhere")
    git(repo, "commit", "-qm", "unrelated", "--allow-empty")
    write_pin(repo, good)
    assert "not in the history of HEAD" in outcome(repo, "at pin").detail


def test_a_starter_without_a_pin_fails(repository):
    repo, _, _ = repository
    (repo / "products" / "lab" / "starter" / "pyproject.toml").write_text(
        '[project]\nname = "lab"\n'
    )
    assert "declares no pin" in outcome(repo, "at pin").detail


def test_the_physics_lab_starter_is_found_with_its_pending_pin():
    [starter] = [
        s for s in starters.find_starters(ROOT) if s.parent.name == "physics-lab"
    ]
    assert starters.pin_of(starter) == starters.PENDING
