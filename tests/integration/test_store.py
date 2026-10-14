"""The execution store of a build (ADR 014 decisions 3 and 6, F61 step 4).

The store tests run on small Quarto projects in a temporary directory: a lesson
cell records every execution in a file, so the tests show which lessons a build
executed, and that a restored lesson is not.
"""

import json
import os
import shutil
from pathlib import Path

import pytest
from support import second_build
from support.checks import output, run_check

from pbc.authoring import selection as selecting
from pbc.authoring import store

LESSON_A = "site/lessons/s/01-a"
LESSON_B = "site/lessons/s/02-b"
CONFIG = """\
project:
  type: website
format:
  html:
    html-math-method: mathml
"""
PROFILE = (Path(__file__).parents[2] / "site" / "_quarto-store.yml").read_text()


def lesson(text: str) -> str:
    return (
        f"---\ntitle: Lesson {text}\n---\n\n"
        "```{python}\n"
        "#| label: run\n"
        "import os\n"
        "with open(os.environ['PBC_TEST_LOG'], 'a') as log:\n"
        f"    log.write('{text}\\n')\n"
        "print('result of', '" + text + "')\n"
        "```\n"
    )


def write(site: Path, name: str, text: str) -> None:
    (site / name).parent.mkdir(parents=True, exist_ok=True)
    (site / name).write_text(text, encoding="utf-8")


@pytest.fixture
def site(tmp_path: Path) -> Path:
    source = tmp_path / "site"
    write(source, "_quarto.yml", CONFIG)
    write(source, "_quarto-store.yml", PROFILE)
    write(source, "lessons/s/01-a/index.qmd", lesson("a"))
    write(source, "lessons/s/02-b/index.qmd", lesson("b"))
    write(source, "index.qmd", "---\ntitle: Home\n---\n\nHome.\n")
    return source


def build(site: Path, out: Path, log: Path, selection: Path | None = None):
    env = {"PBC_TEST_LOG": str(log)}
    if selection is not None:
        env["PBC_STORE_SELECTION"] = str(selection)
    return run_check("site-build", site, out, env=env)


def executed(log: Path) -> list[str]:
    return sorted(log.read_text().split()) if log.exists() else []


def make_base(site: Path, base: Path) -> Path:
    """The base of the build that left ``site/_freeze``."""
    shutil.copytree(site / "_freeze", base / "freeze")
    return base


def selection(path: Path, base: Path, execute: list[str], reuse: list[str]) -> Path:
    path.write_text(
        json.dumps(
            {
                "format": selecting.SELECTION_FORMAT,
                "mode": "selective",
                "reason": "",
                "base": {"id": "x", "identity": "y"},
                "base_directory": str(base),
                "lessons": sorted(execute + reuse),
                "execute": execute,
                "reuse": reuse,
            }
        )
    )
    return path


def test_a_build_without_a_base_executes_every_page_and_writes_the_store(
    site: Path, tmp_path: Path
):
    log = tmp_path / "log"
    result = build(site, tmp_path / "out", log)

    assert result.returncode == 0, output(result)
    assert executed(log) == ["a", "b"]
    assert (site / "_freeze" / "lessons" / "s" / "01-a").is_dir()
    assert (site / "_timings.json").is_file()


def test_a_build_never_replays_a_store_it_did_not_restore(site: Path, tmp_path: Path):
    log = tmp_path / "log"
    assert build(site, tmp_path / "one", log).returncode == 0
    # The store of the first build is still there.
    assert (site / "_freeze").is_dir()

    assert build(site, tmp_path / "two", log).returncode == 0

    assert executed(log) == ["a", "a", "b", "b"]


def test_a_build_with_a_base_executes_only_the_changed_lessons(
    site: Path, tmp_path: Path
):
    log = tmp_path / "log"
    first = build(site, tmp_path / "one", log)
    assert first.returncode == 0, output(first)
    base = make_base(site, tmp_path / "base")
    write(site, "lessons/s/02-b/index.qmd", lesson("b2"))
    chosen = selection(tmp_path / "selection.json", base, [LESSON_B], [LESSON_A])
    log.unlink()

    second = build(site, tmp_path / "two", log, chosen)

    assert second.returncode == 0, output(second)
    assert executed(log) == ["b2"]
    # The restored lesson is the page of the base, byte for byte.
    page = Path("lessons/s/01-a/index.html")
    assert (tmp_path / "two" / page).read_bytes() == (
        tmp_path / "one" / page
    ).read_bytes()
    assert "result of b2" in (tmp_path / "two/lessons/s/02-b/index.html").read_text()
    assert "restored from the base" in output(second)


def test_a_page_that_is_not_a_lesson_is_never_restored(site: Path, tmp_path: Path):
    log = tmp_path / "log"
    write(
        site,
        "about.qmd",
        "---\ntitle: About\n---\n\n"
        "```{python}\n#| label: about\nimport os\nopen(os.environ['PBC_TEST_LOG'], 'a')"
        ".write('about\\n')\n```\n",
    )
    assert build(site, tmp_path / "one", log).returncode == 0
    base = make_base(site, tmp_path / "base")
    log.unlink()
    chosen = selection(tmp_path / "selection.json", base, [], [LESSON_A, LESSON_B])

    result = build(site, tmp_path / "two", log, chosen)

    assert result.returncode == 0, output(result)
    assert executed(log) == ["about"]


def test_the_second_build_of_the_determinism_check_starts_from_the_same_state(
    site: Path, tmp_path: Path
):
    log = tmp_path / "log"
    assert build(site, tmp_path / "one", log).returncode == 0
    base = make_base(site, tmp_path / "base")
    write(site, "lessons/s/02-b/index.qmd", lesson("b2"))
    chosen = selection(tmp_path / "selection.json", base, [LESSON_B], [LESSON_A])
    log.unlink()
    first = tmp_path / "first"
    assert build(site, first, log, chosen).returncode == 0
    assert executed(log) == ["b2"]
    log.unlink()

    result = run_check(
        "determinism",
        site,
        first,
        env={"PBC_TEST_LOG": str(log), "PBC_STORE_SELECTION": str(chosen)},
    )

    assert result.returncode == 0, output(result)
    # The changed lesson executed again, the restored one did not.
    assert executed(log) == ["b2"]


def test_a_second_build_of_a_copy_starts_from_the_state_of_the_run(
    site: Path, tmp_path: Path
):
    """The second build of the preview test restores the unchanged lesson from the
    base like the first build, so no result of the base is compared with one this
    machine computed; without the selection it would execute both lessons."""
    log = tmp_path / "log"
    assert build(site, tmp_path / "one", log).returncode == 0
    base = make_base(site, tmp_path / "base")
    write(site, "lessons/s/02-b/index.qmd", lesson("b2"))
    chosen = selection(tmp_path / "selection.json", base, [LESSON_B], [LESSON_A])
    log.unlink()
    assert build(site, tmp_path / "first", log, chosen).returncode == 0
    assert executed(log) == ["b2"]
    log.unlink()

    environment = {"PBC_TEST_LOG": str(log), "PBC_STORE_SELECTION": str(chosen)}
    result = second_build.build_copy(
        site, tmp_path / "second", tmp_path / "work", environment=environment
    )
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
    assert executed(log) == ["b2"]
    log.unlink()

    # A copy built without the selection executes every lesson.
    (tmp_path / "plain").mkdir()
    result = second_build.build_copy(
        site,
        tmp_path / "second-plain",
        tmp_path / "plain",
        environment={"PBC_TEST_LOG": str(log)},
    )
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
    assert executed(log) == ["a", "b2"]


def test_the_selection_of_the_run_reaches_a_build_of_a_copy(tmp_path: Path):
    chosen = tmp_path / selecting.SELECTION_FILE
    chosen.parent.mkdir(parents=True)
    assert second_build.selection_environment(tmp_path) == {}
    selection(chosen, tmp_path / "base", [LESSON_B], [LESSON_A])
    assert second_build.selection_environment(tmp_path) == {
        "PBC_STORE_SELECTION": str(chosen)
    }
    data = json.loads(chosen.read_text())
    data["mode"] = "full"
    chosen.write_text(json.dumps(data))
    assert second_build.selection_environment(tmp_path) == {}


@pytest.mark.parametrize(
    "damage",
    [
        lambda entry: (entry / "leak").symlink_to("/etc/hosts"),
        lambda entry: (entry / "execute-results" / "html.json").write_text("[1"),
    ],
    ids=["symbolic link", "unreadable result"],
)
def test_an_entry_that_is_not_plain_data_is_not_restored(
    site: Path, tmp_path: Path, damage
):
    log = tmp_path / "log"
    assert build(site, tmp_path / "one", log).returncode == 0
    base = make_base(site, tmp_path / "base")
    damage(base / "freeze" / "lessons" / "s" / "01-a" / "index")
    chosen = selection(tmp_path / "selection.json", base, [LESSON_B], [LESSON_A])

    result = build(site, tmp_path / "two", log, chosen)

    assert result.returncode != 0
    assert "cannot be restored" in output(result)


def test_a_lesson_path_outside_the_lessons_is_not_restored(tmp_path: Path):
    base = tmp_path / "base"
    (base / "freeze").mkdir(parents=True)
    with pytest.raises(store.InvalidStore):
        store.restore(tmp_path / "site", base, ["site/../../etc"])
    with pytest.raises(store.InvalidStore):
        store.restore(tmp_path / "site", base, ["site/about"])


def test_the_store_starts_empty_for_a_full_run(tmp_path: Path):
    site = tmp_path / "site"
    (site / "_freeze" / "lessons").mkdir(parents=True)
    full = {"format": selecting.SELECTION_FORMAT, "mode": "full", "reuse": []}

    assert store.prepare(site, full) == []
    assert not (site / "_freeze").exists()
    (site / "_freeze").mkdir()
    assert store.prepare(site, None) == []
    assert not (site / "_freeze").exists()


def test_the_time_of_each_page_comes_from_the_progress_of_the_render():
    log = [
        (0.0, "Starting\n"),
        (1.0, "\x1b[1m\x1b[34m\r[ 1/3] about.qmd\x1b[39m\x1b[22m\n"),
        (4.5, "\x1b[1m\x1b[34m\r[ 2/3] lessons/s/01-a/index.qmd\x1b[39m\x1b[22m\n"),
        (40.0, "[ 3/3] lessons/s/02-b/index.qmd\n"),
        (50.0, "Done\n"),
    ]

    pages = store.timings(log)

    assert pages == [
        {"page": "about.qmd", "seconds": 3.5},
        {"page": "lessons/s/01-a/index.qmd", "seconds": 35.5},
        {"page": "lessons/s/02-b/index.qmd", "seconds": 10.0},
    ]
    assert store.over_budget(pages) == ["lessons/s/01-a/index.qmd: 35.5 s"]


def test_the_digests_of_the_lessons_are_written_beside_the_built_site(
    tmp_path: Path,
):
    out = tmp_path / "digests.json"
    store.write_digests(Path(__file__).parents[2], out)
    data = json.loads(out.read_text())
    assert data["identity"] and data["lessons"]
    assert all(entry["digest"] for entry in data["lessons"].values())
    assert os.path.isfile(out)
