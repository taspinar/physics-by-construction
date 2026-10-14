"""Lesson shards: the division of a full run over same-machine jobs (ADR 014
decision 11, F113).

A lesson shard is a share of the lessons that one job of a full run executes on
its own machine. The properties below hold for every lesson count, in
particular around the multiples of the shard size, and the workflow's matrix is
made of what the script derives (the workflow's side is in
``test_ci_workflow.py``). The division of the tests of the built site in
``tests/e2e/shards.json`` is another one and is not tested here.
"""

import json
import math
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from support import verify_conf
from support.paths import REPO_ROOT
from test_lesson_digest import FILES, _write

from pbc.authoring import shards as sharding
from pbc.authoring.digest import PAGE, Digester

SIZE = verify_conf.shard_size()
# The counts of the Issue: both sides of every multiple of 32 up to the growth
# of the curriculum, and the transition from four to five shards at 128 to 129.
COUNTS = [1, 2, 22, 31, 32, 33, 63, 64, 65, 96, 97, 110, 125, 127, 128, 129, 161]


def names(count: int) -> list[str]:
    return [f"site/lessons/s{n // 10}/{n:03d}-lesson" for n in range(count)]


def tree(root: Path, count: int, size: int = SIZE) -> Path:
    """A repository with ``count`` lessons and the shard size declared."""
    _write(root, "scripts/verify.conf", f"shard-size: {size}\nfake: true\n")
    for name in names(count):
        _write(root, f"{name}/{PAGE}", "---\ntitle: T\n---\n")
    return root


@pytest.mark.parametrize("count", COUNTS)
def test_every_lesson_is_in_exactly_one_shard(count: int):
    division = sharding.shares(names(count), SIZE)
    together = [lesson for share in division for lesson in share]
    assert sorted(together) == sorted(names(count))
    assert len(together) == len(set(together))


@pytest.mark.parametrize("count", COUNTS)
def test_no_shard_exceeds_the_size(count: int):
    assert all(len(share) <= SIZE for share in sharding.shares(names(count), SIZE))


@pytest.mark.parametrize("count", COUNTS)
def test_the_number_of_shards_is_the_ceiling_of_the_count_over_the_size(count: int):
    division = sharding.shares(names(count), SIZE)
    assert len(division) == math.ceil(count / SIZE) == sharding.count(count, SIZE)


@pytest.mark.parametrize("count", COUNTS)
def test_no_shard_is_idle_and_the_shares_are_balanced(count: int):
    # An idle shard still prepares a runner: the requirement is a bounded full
    # run, not a padded one.
    sizes = [len(share) for share in sharding.shares(names(count), SIZE)]
    assert min(sizes) >= 1
    assert max(sizes) - min(sizes) <= 1


@pytest.mark.parametrize("count", COUNTS)
def test_the_assignment_is_stable_for_a_lesson_list(count: int):
    shuffled = list(reversed(names(count)))
    assert sharding.shares(shuffled, SIZE) == sharding.shares(names(count), SIZE)


def test_the_transition_from_four_to_five_shards_is_at_129_lessons():
    assert sharding.count(128, SIZE) == 4
    assert sharding.count(129, SIZE) == 5
    assert sharding.count(110, SIZE) == 4
    assert sharding.count(125, SIZE) == 4


def test_the_shard_size_is_the_one_verify_conf_declares(tmp_path: Path):
    assert SIZE == sharding.size(REPO_ROOT) == 32
    assert verify_conf.shard_size() == 32
    root = tree(tmp_path, 10, size=4)
    assert sharding.size(root) == 4
    # The count of shards follows the declaration of the tree, not a constant.
    assert sharding.matrix(root) == [1, 2, 3]


@pytest.mark.parametrize("count", COUNTS)
def test_the_matrix_is_derived_from_the_lessons_of_the_tree(count: int, tmp_path: Path):
    root = tree(tmp_path, count)
    assert sharding.matrix(root) == list(range(1, math.ceil(count / SIZE) + 1))
    # Adding a lesson changes the matrix exactly when the count crosses a
    # multiple of the size, and needs no other change.
    _write(root, f"site/lessons/z/999-added/{PAGE}", "---\ntitle: T\n---\n")
    assert len(sharding.matrix(root)) == math.ceil((count + 1) / SIZE)


def test_the_lessons_are_the_ones_the_digests_are_made_for():
    assert sharding.lessons(REPO_ROOT) == [
        path.relative_to(REPO_ROOT).as_posix() for path in Digester(REPO_ROOT).lessons()
    ]


def test_the_number_of_shards_is_read_from_no_file(tmp_path: Path):
    # Only the lesson count and the declared size decide it: a file that
    # claims another number of shards changes nothing.
    root = tree(tmp_path, 40)
    for decoy in ("scripts/shards.conf", "scripts/shards.json", "shards.json"):
        _write(root, decoy, "9\n")
    assert sharding.matrix(root) == [1, 2]


@pytest.mark.parametrize("spec", ["0/1", "2/1", "x", "1/", "1/2", "1/0"])
def test_a_shard_that_the_lessons_do_not_derive_is_refused(spec: str, tmp_path: Path):
    root = tree(tmp_path, 3, size=4)  # one shard
    with pytest.raises(sharding.ShardError):
        sharding.share(root, spec)


def test_the_shard_number_k_names_the_k_th_share(tmp_path: Path):
    root = tree(tmp_path, 9, size=4)
    division = sharding.shares(sharding.lessons(root), 4)
    for number in (1, 2, 3):
        assert sharding.share(root, f"{number}/3") == (number, 3, division[number - 1])


def test_a_shard_executes_its_share_and_of_it_what_the_selection_names():
    shard = {"lessons": ["a", "b", "c"]}
    assert sharding.executed(None, None) is None
    assert sharding.executed(shard, None) == ["a", "b", "c"]
    full = {"mode": "full", "execute": ["a", "b", "c", "d"]}
    assert sharding.executed(shard, full) == ["a", "b", "c"]
    selective = {"mode": "selective", "execute": ["b", "d"]}
    assert sharding.executed(shard, selective) == ["b"]
    assert sharding.executed(None, selective) == ["b", "d"]
    # A shard with nothing to execute executes nothing, and says so.
    assert sharding.executed(shard, {"mode": "selective", "execute": ["d"]}) == []


def test_the_pages_a_shard_renders_are_the_lesson_pages_of_what_it_executes(
    tmp_path: Path,
):
    file = tmp_path / "shard.json"
    file.write_text(
        json.dumps(
            {
                "format": sharding.SHARD_FORMAT,
                "lessons": ["site/lessons/s/01-one", "site/lessons/s/02-two"],
            }
        )
    )
    selection = tmp_path / "selection.json"
    selection.write_text(
        json.dumps(
            {"format": 1, "mode": "selective", "execute": ["site/lessons/s/02-two"]}
        )
    )
    assert sharding.render_list(Path("site"), None, file) == [
        "lessons/s/01-one/index.qmd",
        "lessons/s/02-two/index.qmd",
    ]
    assert sharding.render_list(Path("site"), selection, file) == [
        "lessons/s/02-two/index.qmd"
    ]


# --- scripts/verify.sh ---------------------------------------------------------


def run_verify(*arguments: str, cwd: Path = REPO_ROOT, env: dict | None = None):
    return subprocess.run(
        ["bash", "scripts/verify.sh", *arguments],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_verify_prints_the_shards_the_module_derives():
    result = run_verify("--shards")
    assert result.returncode == 0, result.stderr
    assert [int(n) for n in result.stdout.split()] == sharding.matrix(REPO_ROOT)


@pytest.mark.parametrize(
    "arguments",
    [
        ["--shards", "--groups"],
        ["--shards", "--only", "build"],
        ["--shards", "--all"],
        ["--shard", "1/1", "--assemble", "."],
        ["--shard", "1/1", "--only", "code"],
        ["--shard", "1/1", "--reuse"],
        ["--assemble", ".", "--reuse"],
        ["--assemble", ".", "--base", "."],
        ["--shard", "one"],
        ["--assemble"],
    ],
)
def test_verify_refuses_combinations_that_would_verify_something_else(
    arguments: list[str],
):
    result = run_verify(*arguments)
    assert result.returncode != 0
    assert "Verification passed" not in result.stdout


def test_verify_refuses_a_number_of_shards_that_is_not_the_derived_one():
    count = len(sharding.matrix(REPO_ROOT))
    result = run_verify("--shard", f"1/{count + 1}")
    assert result.returncode != 0
    assert "derived" in result.stderr


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A repository with the real script, two trivial checks in the group
    build, one outside it, and a stub for ``uv`` that runs this source tree."""
    root = tmp_path / "repo"
    for name, text in FILES.items():
        _write(root, name, text)
    _write(root, "src/pbc/data/__init__.py", 'SAMPLES_DIR = "data/samples"\n')
    (root / "site/lessons/s/02-two" / PAGE).unlink()
    for number in (1, 2, 3):
        _write(root, f"site/lessons/s/0{number}-l/{PAGE}", "---\ntitle: T\n---\n")
    for name in ("verify.sh", "lib/verification.sh", "lib/fingerprint.sh"):
        (root / "scripts" / Path(name).parent).mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO_ROOT / "scripts" / name, root / "scripts" / name)
    _write(
        root,
        "scripts/verify.conf",
        "shard-size: 2\n"
        "one [build]: test -f .agents/verification/shard.json\n"
        "two [build]: true\n"
        "other [code]: false\n",
    )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "uv"
    stub.write_text(
        '#!/usr/bin/env bash\nwhile [[ "$1" != python ]]; do shift; done; shift\n'
        f'PYTHONPATH="{REPO_ROOT / "src"}" exec "{sys.executable}" "$@"\n',
        encoding="utf-8",
    )
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    return root


def verify(project: Path, *arguments: str | Path):
    env = {**os.environ, "PATH": f"{project.parent / 'bin'}:{os.environ['PATH']}"}
    return run_verify(*map(str, arguments), cwd=project, env=env)


def test_a_shard_runs_the_group_build_on_its_share_and_verifies_nothing(project: Path):
    result = verify(project, "--shard", "2/2")
    # It fails on the part, which needs a built site; the checks of the group
    # ran, and the ones of the other groups did not.
    assert "PASS  one" in result.stdout and "PASS  two" in result.stdout
    assert "other" not in result.stdout.split("Verification summary")[1]
    shard = json.loads((project / sharding.SHARD_FILE).read_text())
    assert (shard["shard"], shard["of"]) == (2, 2)
    assert shard["lessons"] == ["site/lessons/s/02-l"]
    assert "Verification passed." not in result.stdout


def test_a_local_run_without_options_is_unchanged_in_meaning(project: Path):
    (project / "scripts" / "verify.conf").write_text(
        "shard-size: 2\none [build]: test ! -f .agents/verification/shard.json\n"
        "two [code]: test ! -d .agents/verification/part\n",
        encoding="utf-8",
    )
    stale = project / sharding.SHARD_FILE
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text("{}")
    result = verify(project)
    assert result.returncode == 0, result.stdout + result.stderr
    # Every check ran in one process, the shard of an earlier run is gone, and
    # the declaration of the shard size is no check.
    summary = result.stdout.split("Verification summary")[1]
    assert "PASS  one" in summary and "PASS  two" in summary
    assert "shard-size" not in summary
    assert "Verification passed." in result.stdout
    assert not stale.exists()


def test_a_shard_and_the_assembly_record_nothing_and_claim_no_verification(
    project: Path,
):
    (project / "scripts" / "verify.conf").write_text(
        "shard-size: 3\none [build]: true\n", encoding="utf-8"
    )
    for arguments in (("--assemble", project / "no-parts"), ("--shard", "1/1")):
        result = verify(project, *arguments)
        # Neither has a built site or parts to work with here, so both fail
        # after their checks; in no case is a pass recorded or claimed.
        assert result.returncode != 0
        assert "Verification passed." not in result.stdout
        assert not (project / ".agents/verification/passed").exists()


def test_a_failing_check_fails_the_shard(project: Path):
    (project / "scripts" / "verify.conf").write_text(
        "shard-size: 3\nbroken [build]: false\n", encoding="utf-8"
    )
    result = verify(project, "--shard", "1/1")
    assert result.returncode != 0
    assert "FAIL  broken" in result.stdout
    assert "part" not in result.stdout.split("Verification summary")[1]
    assert not (project / ".agents/verification/part").exists()


def test_the_shard_size_is_declared_once_and_is_a_number(project: Path):
    (project / "scripts" / "verify.conf").write_text(
        "shard-size: many\none [build]: true\n", encoding="utf-8"
    )
    assert verify(project, "--groups").returncode != 0
