"""A new dataset adds new files only, and two dataset branches merge without
touching the same line (Issue #456).

The first test adds a scratch dataset to a temporary tree whose lists are
generated and shows that the check passes with no edit to a file that existed
before, except the generated regions of the two READMEs, which only gain
lines. The second plays two branches in a temporary Git repository.
"""

import copy
import hashlib
import os
import subprocess
import sys
import types
from pathlib import Path

import pytest
import yaml

from pbc.data.card import load_cards
from pbc.data.check import check_repository
from pbc.data.registry import (
    DOCS_README,
    TOOLS_README,
    region_text,
    regions,
    with_region,
    write_readmes,
)

ROOT = Path(__file__).parents[2]
CARDS = load_cards(ROOT / "data/registry")
SAMPLE = (
    ROOT / "data/samples/npl-onwafer-sparameters/coaxial_3dB_attenuator_0601_CORR.s2p"
)


def add_dataset(root: Path, name: str, monkeypatch) -> list[Path]:
    """Add the dataset ``name`` with new files only; returns the files written."""
    module = "scratch_" + name.replace("-", "_")
    card = copy.deepcopy(CARDS["npl-onwafer-sparameters"])
    content = SAMPLE.read_bytes()
    card.update(
        {
            "id": name,
            "dossier": f"docs/datasets/{name}.md",
            "reference_module": module,
            "listing": {"name": f"Scratch {name}", "kind": "scratch"},
            "conversions": [
                {
                    "script": f"tools/datasets/{module}.py",
                    "input": "`in.bin` (`0`)",
                    "output": "`a.s2p` (`1`)",
                    "command": f"uv run python tools/datasets/{module}.py\n",
                }
            ],
            "samples": [
                {
                    "path": "a.s2p",
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "bytes": len(content),
                    "derivation": "unchanged copy",
                    "test": f"tests/unit/test_{module}.py::test_{module}_parses",
                }
            ],
        }
    )
    files = {
        f"data/registry/{name}.yaml": yaml.safe_dump(card, sort_keys=False),
        f"docs/datasets/{name}.md": f"# {name}\n\n**Status label: calibrated.**\n",
        f"tests/unit/test_{module}.py": f"def test_{module}_parses():\n    pass\n",
        f"tools/datasets/{module}.py": "print('a one-time conversion')\n",
        f"src/pbc/data/reference/{module}.py": "def make_figure(data_dir):\n    pass\n",
    }
    written = []
    for relative, text in files.items():
        path = root / relative
        assert not path.exists(), f"{relative} exists: not a new file"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        written.append(path)
    sample = root / "data/samples" / name / "a.s2p"
    sample.parent.mkdir(parents=True)
    sample.write_bytes(content)
    written.append(sample)
    # The reference module of a scratch dataset: the check imports it by name
    # from pbc.data.reference, where this test cannot write a file.
    stub = types.ModuleType(f"pbc.data.reference.{module}")
    stub.make_figure = lambda data_dir: None
    monkeypatch.setitem(sys.modules, stub.__name__, stub)
    return written


def snapshot(root: Path) -> dict[Path, bytes]:
    return {
        p.relative_to(root): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file() and ".git" not in p.parts
    }


def test_a_new_dataset_adds_new_files_only_and_passes_the_check(tmp_path, monkeypatch):
    add_dataset(tmp_path, "first-scratch", monkeypatch)
    write_readmes(tmp_path)
    assert check_repository(tmp_path) == []
    before = snapshot(tmp_path)

    new = add_dataset(tmp_path, "second-scratch", monkeypatch)
    assert check_repository(tmp_path) != [], "the READMEs are stale until generated"
    write_readmes(tmp_path)
    assert check_repository(tmp_path) == []

    after = snapshot(tmp_path)
    changed = {p for p in before if before[p] != after[p]}
    assert changed == {DOCS_README, TOOLS_README}
    for relative in changed:
        old, new_text = before[relative].decode(), after[relative].decode()
        old_lines, new_lines = old.splitlines(), new_text.splitlines()
        added = [line for line in new_lines if line not in old_lines]
        assert added and all("second" in line for line in added), added
        assert all(line in new_lines for line in old_lines), "a line was removed"
    assert set(after) - set(before) == {p.relative_to(tmp_path) for p in new}
    assert "[second-scratch]" in region_text(after[DOCS_README].decode(), "later-table")


# Two branches.

GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "test",
    "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "test",
    "GIT_COMMITTER_EMAIL": "test@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
}


def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=root,
        env=GIT_ENV,
        capture_output=True,
        text=True,
        check=check,
    )


def commit_dataset(root: Path, branch: str, name: str, monkeypatch) -> None:
    git(root, "checkout", "-q", "-b", branch, "main")
    add_dataset(root, name, monkeypatch)
    write_readmes(root)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", f"add {name}")


@pytest.fixture
def repo(tmp_path, monkeypatch) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    add_dataset(tmp_path, "base-scratch", monkeypatch)
    write_readmes(tmp_path)
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "a dataset and the generated lists")
    return tmp_path


def test_two_dataset_branches_merge_without_conflict(repo, monkeypatch):
    # Ids that are not neighbours in the alphabetical order: a row each in
    # another place of the table, so neither branch touches the other's line.
    commit_dataset(repo, "one", "aaa-scratch", monkeypatch)
    commit_dataset(repo, "two", "zzz-scratch", monkeypatch)
    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "-q", "--no-edit", "one")
    merged = git(repo, "merge", "-q", "--no-edit", "two", check=False)
    assert merged.returncode == 0, merged.stdout + merged.stderr
    assert check_repository(repo) == []
    text = (repo / DOCS_README).read_text()
    assert "[aaa-scratch]" in text and "[zzz-scratch]" in text


def test_neighbouring_ids_conflict_only_in_a_generated_region_that_write_resolves(
    repo, monkeypatch
):
    commit_dataset(repo, "one", "zz-one-scratch", monkeypatch)
    commit_dataset(repo, "two", "zz-two-scratch", monkeypatch)
    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "-q", "--no-edit", "one")
    merged = git(repo, "merge", "--no-edit", "two", check=False)
    assert merged.returncode != 0, (
        "neighbouring rows conflict; this shows the resolution"
    )
    conflicted = git(repo, "diff", "--name-only", "--diff-filter=U").stdout.split()
    assert set(conflicted) <= {str(DOCS_README), str(TOOLS_README)}
    for relative in conflicted:
        text = (repo / relative).read_text()
        assert "<<<<<<<" in text
        outside = text
        for name in regions({})[Path(relative)]:
            outside = with_region(outside, name, "")
        assert "<<<<<<<" not in outside, f"{relative}: a conflict outside a region"
    write_readmes(repo)
    for relative in conflicted:
        assert "<<<<<<<" not in (repo / relative).read_text()
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--no-edit")
    assert check_repository(repo) == []
    text = (repo / DOCS_README).read_text()
    assert "[zz-one-scratch]" in text and "[zz-two-scratch]" in text
