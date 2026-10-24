"""The single-page render of the targeted run (ADR 017 decision 7, F119).

``scripts/check-lesson-pages.sh`` renders each lesson the targeted run
selected, alone, in a clone of the working tree, and never builds the site.
It runs here on a copy of this repository's committed files, so a broken page
and a changed proof can be made without touching the checkout, and the
checkout's own site is never built. Each render executes a real lesson, in
the clone's own locked environment: the page reads the clone's files, so a
lesson that displays Lean reads the record of the Lean build in the clone and
not one this checkout may hold from its own build (CI starts without one).
"""

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
from support import lesson_checks
from support.checks import output
from support.paths import REPO_ROOT, SCRIPTS

from pbc.authoring import selection as selecting

KINEMATICS = "site/lessons/mechanics/01-kinematics-as-a-program"
LEAN_LESSON = "site/lessons/lean/01-proving-what-the-simulation-showed"
# A fake Lean build: it compiles nothing, records where it ran, and writes the
# build record as scripts/check-lean.sh does (the versions and a checksum of
# every module), in the project it ran in, so a page that displays Lean reads
# the record of the build in that project. With FAKE_LEAN_RECORD=no it leaves
# no record, as a build that did not run.
FAKE_LEAN = r"""#!/usr/bin/env bash
set -euo pipefail
pwd >>"$FAKE_LEAN_LOG"
[[ "${FAKE_LEAN_RECORD:-yes}" == "yes" ]] || exit 0
cd lean
mkdir -p .lake
{
  printf '{"toolchain":"fake","lean":{"version":"4.0.0","commit":"0"},'
  printf '"mathlib":{"tag":"v4.0.0","rev":"0123456789abcdef"},'
  printf '"exercises":{},"modules":{'
  separator=""
  while IFS= read -r file; do
    module="$(sed -e 's/\.lean$//' -e 's#/#.#g' <<<"$file")"
    checksum="$(shasum -a 256 "$file" | cut -d" " -f1)"
    printf '%s"%s":"%s"' "$separator" "$module" "$checksum"
    separator=","
  done < <(find PhysicsByConstruction -name '*.lean' | LC_ALL=C sort)
  printf '}}\n'
} >.lake/pbc-build-record.json
"""


# The options of the fixture's git commands. Its repository holds enough loose
# objects for the commit to start an automatic gc, which by default runs in
# the background and packs and removes them while a test copies the
# repository; with these, nothing rewrites it after the fixture returns.
IDENTITY = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
FIXTURE_GIT = [*IDENTITY, "-c", "gc.auto=0", "-c", "gc.autoDetach=false"]

# The budget of the lessons these tests render, in the copy's own
# scripts/lesson-budgets.conf, which the check reads. The tests are about what
# the check renders and runs, not about the budget: the render in the clone
# includes the cold start of uv and Quarto, which took 31 to 40 s for a light
# lesson when another verification ran on the machine (#267). The budget is
# checked by test_a_lesson_over_its_budget_fails_the_check, which sets its own.
GENEROUS_BUDGET_SECONDS = 600


def set_budget(root: Path, lesson: str, seconds: int, reason: str) -> None:
    """Give a lesson its own budget in the copy, replacing any it has."""
    table = root / "scripts" / "lesson-budgets.conf"
    key = lesson.removeprefix("site/")
    lines = [
        line
        for line in table.read_text().splitlines()
        if line.split("|", 1)[0].strip() != key
    ]
    table.write_text("\n".join([*lines, f"{key} | {seconds} | {reason}"]) + "\n")


@pytest.fixture(scope="module")
def pristine(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A repository of the committed files of this checkout, on main."""
    root = tmp_path_factory.mktemp("pristine") / "repo"
    for file in lesson_checks.committed_files(REPO_ROOT):
        (root / file).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / file, root / file)
    git = ["git", *FIXTURE_GIT, "-C", root]
    subprocess.run([*git, "init", "-q", "-b", "main"], check=True)
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-qm", "The committed files"], check=True)
    return root


@pytest.fixture
def tree(pristine: Path, tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(pristine, root, symlinks=True)
    fake = root / "scripts" / "check-lean.sh"
    fake.write_text(FAKE_LEAN)
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    for lesson in (KINEMATICS, LEAN_LESSON):
        set_budget(
            root,
            lesson,
            GENEROUS_BUDGET_SECONDS,
            "the tests of the check, whose clone render starts uv and Quarto cold",
        )
    return root


def select(root: Path, lessons: list[str], tier: str | None) -> None:
    data = {
        "format": selecting.SELECTION_FORMAT,
        "mode": "selective",
        "execute": lessons,
        "reuse": [],
    }
    if tier:
        data["tier"] = tier
    selecting.write(root, data)


def check(
    root: Path, tmp_path: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    # UV_PROJECT runs the script's own helper in the environment of this
    # checkout; the clone's commands must not inherit it.
    return subprocess.run(
        ["bash", str(SCRIPTS / "check-lesson-pages.sh"), str(root)],
        cwd=root,
        env={
            **os.environ,
            "UV_PROJECT": str(REPO_ROOT),
            "FAKE_LEAN_LOG": str(tmp_path / "lean.log"),
            **(env or {}),
        },
        capture_output=True,
        text=True,
        check=False,
    )


def lean_runs(tmp_path: Path) -> list[str]:
    log = tmp_path / "lean.log"
    return log.read_text().splitlines() if log.exists() else []


def loose_objects(root: Path) -> list[Path]:
    objects = root / ".git" / "objects"
    return sorted(p for p in objects.glob("[0-9a-f][0-9a-f]/*") if p.is_file())


@pytest.mark.parametrize("options", [[], FIXTURE_GIT], ids=["plain", "fixture"])
def test_the_fixture_commit_leaves_its_loose_objects_in_place(tmp_path, options):
    # A repository over the automatic-gc threshold: gc.auto=1 asks for a gc
    # when the sampled object directory holds more than one loose object.
    root = tmp_path / "repo"
    root.mkdir()
    for n in range(2000):
        (root / f"{n}.txt").write_text(f"{n}\n")
    git = ["git", *IDENTITY, "-C", root]
    subprocess.run([*git, "init", "-q", "-b", "main"], check=True)
    subprocess.run([*git, "config", "gc.auto", "1"], check=True)
    subprocess.run([*git, "config", "gc.autoDetach", "false"], check=True)
    subprocess.run([*git, "add", "-A"], check=True)
    before = loose_objects(root)
    # The repository's own gc.autoDetach=false makes the plain commit's gc
    # finish before it returns, so the control needs no wait.
    subprocess.run([*git, *options, "commit", "-qm", "c"], check=True)
    after = loose_objects(root)
    packs = list((root / ".git" / "objects" / "pack").glob("*.pack"))
    if options:
        # The blobs of git add, and the trees and the commit of git commit.
        assert set(before) <= set(after) and len(after) > len(before)
        assert packs == []
        assert not (root / ".git" / "gc.log").exists()
    else:
        assert packs, "the control commit started no gc: the test shows nothing"
        assert not set(before) & set(after)


def test_without_a_selection_there_is_nothing_to_render(tree, tmp_path):
    result = check(tree, tmp_path)
    assert result.returncode == 0, output(result)
    assert "Nothing to render" in result.stdout
    assert lean_runs(tmp_path) == []


def test_a_run_that_builds_the_site_leaves_nothing_to_render(tree, tmp_path):
    # The selection of a run with --base: the build executes the lessons.
    select(tree, [KINEMATICS], None)
    result = check(tree, tmp_path)
    assert result.returncode == 0, output(result)
    assert "Nothing to render" in result.stdout
    assert "cover every lesson" in result.stdout


def test_the_selected_lesson_renders_alone_in_a_clone_and_no_site_is_built(
    tree, tmp_path
):
    select(tree, [KINEMATICS], "targeted")
    result = check(tree, tmp_path)
    assert result.returncode == 0, output(result)
    assert "The locked environment of the clone" in result.stdout
    assert f"Rendered {KINEMATICS}/index.qmd in " in result.stdout
    # Then its experiment, with a reader's commands, writes what the page shows.
    assert "The learner environment of the clone" in result.stdout
    assert f"Ran the experiment of {KINEMATICS} in " in result.stdout
    assert "no site was built" in result.stdout
    # Rendered in a clone, which is gone: the tree holds no page and no build.
    assert not (tree / "site" / "_site").exists()
    assert not (tree / "site" / "_freeze").exists()
    assert not list((tree / "site").rglob("*.html"))
    # No proof changed and the lesson displays none: no Lean build.
    assert lean_runs(tmp_path) == []


def test_a_page_that_does_not_render_fails_the_check(tree, tmp_path):
    page = tree / KINEMATICS / "index.qmd"
    page.write_text(
        page.read_text() + "\n```{python}\nraise SystemExit('broken cell')\n```\n"
    )
    select(tree, [KINEMATICS], "targeted")
    result = check(tree, tmp_path)
    assert result.returncode != 0
    assert f"the page {KINEMATICS}/index.qmd does not render" in result.stderr
    assert "broken cell" in result.stderr


def test_a_lesson_over_its_budget_fails_the_check(tree, tmp_path):
    # A budget of 0 s, which no render can stay under: the check compares the
    # seconds with the budget of the lesson's own entry and fails.
    set_budget(tree, KINEMATICS, 0, "a budget no render can meet")
    select(tree, [KINEMATICS], "targeted")
    result = check(tree, tmp_path)
    assert result.returncode != 0
    assert f"the page {KINEMATICS}/index.qmd took " in result.stderr
    assert "the budget of a lesson page is 0 s" in result.stderr


def test_an_experiment_that_does_not_write_what_its_page_shows_fails(tree, tmp_path):
    # The experiment computes another number in the learner environment than
    # in the render: the comparison with the rendered page must catch it.
    experiment = tree / "src" / "pbc" / "mechanics" / "experiments" / "kinematics.py"
    text = experiment.read_text()
    old = 'experiment.number("g", g)'
    assert old in text
    experiment.write_text(
        "import os\n"
        + text.replace(
            old, 'experiment.number("g", 9.8 if "UV_NO_SYNC" in os.environ else g)'
        )
    )
    select(tree, [KINEMATICS], "targeted")
    result = check(tree, tmp_path)
    assert result.returncode != 0
    assert f"the experiment of {KINEMATICS} does not write what its page" in (
        result.stderr
    )
    assert "the number g = '9.8' is not on the page" in result.stderr


def test_a_lesson_without_an_experiment_fails(tree, tmp_path):
    page = tree / KINEMATICS / "index.qmd"
    page.write_text(
        page.read_text().replace(
            "  experiment: pbc.mechanics.experiments.kinematics\n", ""
        )
    )
    select(tree, [KINEMATICS], "targeted")
    result = check(tree, tmp_path)
    assert result.returncode != 0
    assert "declares no 'lesson.experiment'" in result.stderr


def test_a_changed_proof_runs_the_lean_build_of_the_checkout(tree, tmp_path):
    proof = next((tree / "lean" / "PhysicsByConstruction").rglob("*.lean"))
    proof.write_text(proof.read_text() + "\n-- a change\n")
    select(tree, [KINEMATICS], "targeted")
    result = check(tree, tmp_path)
    assert result.returncode == 0, output(result)
    assert "a file under lean/ differs from the base branch" in result.stdout
    assert lean_runs(tmp_path) == [str(tree.resolve())]


def test_a_lesson_that_displays_lean_gets_the_lean_build_in_the_clone(tree, tmp_path):
    # As the page's commands say: the environment, the Lean build, then the
    # render of the page, each in the clone. The page renders from the record
    # that build left in the clone (the fake writes it there and nowhere
    # else; the copy of the repository holds none).
    select(tree, [LEAN_LESSON], "targeted")
    result = check(tree, tmp_path)
    assert result.returncode == 0, output(result)
    assert "a selected lesson displays Lean modules" in result.stdout
    [where] = lean_runs(tmp_path)
    assert where != str(tree.resolve()) and "lesson-pages." in where
    assert not (tree / "lean" / ".lake" / "pbc-build-record.json").exists()
    assert (
        result.stdout.index("locked environment of the clone")
        < result.stdout.index("Lean build in the clone")
        < result.stdout.index(f"Rendering {LEAN_LESSON}/index.qmd alone")
    )
    assert f"Rendered {LEAN_LESSON}/index.qmd in " in result.stdout


def test_the_page_reads_the_lean_build_of_the_clone_and_not_of_the_checkout(
    tree, tmp_path
):
    # The build in the clone left no record. The page must fail on the
    # clone's record, whatever record this checkout holds from its own Lean
    # build: a page rendered with the checkout's environment would read that
    # one and pass here while a fresh machine fails.
    select(tree, [LEAN_LESSON], "targeted")
    result = check(tree, tmp_path, env={"FAKE_LEAN_RECORD": "no"})
    assert result.returncode != 0
    assert f"the page {LEAN_LESSON}/index.qmd does not render" in result.stderr
    [where] = lean_runs(tmp_path)
    record = Path(where).resolve() / "lean" / ".lake" / "pbc-build-record.json"
    assert f"{record} does not exist" in result.stderr, result.stderr


def test_the_check_needs_a_working_tree(tmp_path):
    (tmp_path / "plain").mkdir()
    result = check(tmp_path / "plain", tmp_path)
    assert result.returncode != 0
    assert "not a Git working tree" in result.stderr
