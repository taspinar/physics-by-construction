"""A lesson shard and the assembly on a small Quarto project (ADR 014 decision
11, F113).

A cell of each lesson records every execution in a file, so the tests show what
a shard executed, that the assembly executes no lesson, and that the page the
assembly renders from the store of the shards is, byte for byte, the page the
shard rendered. The project is the one of ``test_store.py``.
"""

import json
import shutil
from pathlib import Path

import pytest
from support.checks import output, run_check
from test_store import (
    CONFIG,
    LESSON_A,
    LESSON_B,
    PROFILE,
    executed,
    lesson,
    make_base,
    selection,
    write,
)

from pbc.authoring import shards as sharding


@pytest.fixture
def site(tmp_path: Path) -> Path:
    source = tmp_path / "site"
    write(source, "_quarto.yml", CONFIG)
    write(source, "_quarto-store.yml", PROFILE)
    write(source, "lessons/s/01-a/index.qmd", lesson("a"))
    write(source, "lessons/s/02-b/index.qmd", lesson("b"))
    write(source, "index.qmd", "---\ntitle: Home\n---\n\nHome.\n")
    return source


def shard_file(path: Path, number: int, lessons: list[str]) -> Path:
    path.write_text(
        json.dumps(
            {
                "format": sharding.SHARD_FORMAT,
                "shard": number,
                "of": 2,
                "lessons": lessons,
            }
        )
    )
    return path


def build_shard(
    site: Path, out: Path, log: Path, shard: Path, chosen: Path | None = None
):
    env = {"PBC_TEST_LOG": str(log), "PBC_SHARD_FILE": str(shard)}
    if chosen is not None:
        env["PBC_STORE_SELECTION"] = str(chosen)
    return run_check("site-build", site, out, env=env)


def two_machines(
    site: Path, tmp_path: Path, log: Path
) -> tuple[Path, Path, Path, Path]:
    """Each lesson built by its own shard on its own copy of the sources."""
    result = []
    for number, name in enumerate((LESSON_A, LESSON_B), start=1):
        machine = tmp_path / f"machine-{number}"
        shutil.copytree(site, machine)
        out = tmp_path / f"out-{number}"
        built = build_shard(
            machine,
            out,
            log,
            shard_file(tmp_path / f"shard-{number}.json", number, [name]),
        )
        assert built.returncode == 0, output(built)
        result += [machine, out]
    return result[0], result[1], result[2], result[3]


def test_a_shard_executes_renders_and_stores_only_its_share(site: Path, tmp_path: Path):
    log = tmp_path / "log"
    shard = shard_file(tmp_path / "shard.json", 1, [LESSON_A])

    result = build_shard(site, tmp_path / "out", log, shard)

    assert result.returncode == 0, output(result)
    assert executed(log) == ["a"]
    assert (tmp_path / "out/lessons/s/01-a/index.html").is_file()
    assert not (tmp_path / "out/lessons/s/02-b").exists()
    assert (site / "_freeze/lessons/s/01-a").is_dir()
    assert not (site / "_freeze/lessons/s/02-b").exists()


def test_a_shard_with_nothing_to_execute_renders_nothing(site: Path, tmp_path: Path):
    log = tmp_path / "log"
    shard = shard_file(tmp_path / "shard.json", 1, [LESSON_A])
    first = build_shard(site, tmp_path / "one", log, shard)
    assert first.returncode == 0, output(first)
    base = make_base(site, tmp_path / "base")
    log.unlink()
    # Both lessons are unchanged: the shard restores its entry and runs nothing.
    chosen = selection(tmp_path / "selection.json", base, [], [LESSON_A, LESSON_B])

    result = build_shard(site, tmp_path / "two", log, shard, chosen)

    assert result.returncode == 0, output(result)
    assert executed(log) == []
    assert "0 page(s) to render" in output(result)
    assert (site / "_freeze/lessons/s/01-a").is_dir()
    assert not (site / "_freeze/lessons/s/02-b").exists()
    assert not list((tmp_path / "two").glob("lessons/**/*.html"))


def test_a_shard_executes_the_changed_lessons_of_its_share_against_a_base(
    site: Path, tmp_path: Path
):
    log = tmp_path / "log"
    both = shard_file(tmp_path / "shard.json", 1, [LESSON_A, LESSON_B])
    assert build_shard(site, tmp_path / "one", log, both).returncode == 0
    base = make_base(site, tmp_path / "base")
    write(site, "lessons/s/02-b/index.qmd", lesson("b2"))
    log.unlink()
    chosen = selection(tmp_path / "selection.json", base, [LESSON_B], [LESSON_A])

    result = build_shard(site, tmp_path / "two", log, both, chosen)

    assert result.returncode == 0, output(result)
    assert executed(log) == ["b2"]
    assert (site / "_freeze/lessons/s/01-a").is_dir()  # restored, handed over


def test_the_determinism_check_of_a_shard_builds_its_share_again(
    site: Path, tmp_path: Path
):
    log = tmp_path / "log"
    shard = shard_file(tmp_path / "shard.json", 1, [LESSON_A])
    first = tmp_path / "first"
    assert build_shard(site, first, log, shard).returncode == 0
    log.unlink()

    result = run_check(
        "determinism",
        site,
        first,
        env={"PBC_TEST_LOG": str(log), "PBC_SHARD_FILE": str(shard)},
    )

    assert result.returncode == 0, output(result)
    assert executed(log) == ["a"]


def test_the_assembly_executes_no_lesson_and_renders_the_pages_the_shards_rendered(
    site: Path, tmp_path: Path
):
    log = tmp_path / "log"
    machine_a, out_a, machine_b, out_b = two_machines(site, tmp_path, log)
    assert executed(log) == ["a", "b"]

    # The union of the stores of the two shards, as the assembly builds it.
    union = tmp_path / "union"
    for machine, directory in ((machine_a, "01-a"), (machine_b, "02-b")):
        shutil.copytree(
            machine / "_freeze/lessons/s" / directory,
            union / "freeze/lessons/s" / directory,
        )
    chosen = selection(tmp_path / "selection.json", union, [], [LESSON_A, LESSON_B])
    log.unlink()

    assembled = tmp_path / "assembled"
    result = run_check(
        "site-build",
        site,
        assembled,
        env={
            "PBC_TEST_LOG": str(log),
            "PBC_STORE_SELECTION": str(chosen),
        },
    )

    assert result.returncode == 0, output(result)
    assert executed(log) == [], "the assembly executed a lesson"
    for rendered, directory in ((out_a, "01-a"), (out_b, "02-b")):
        shard_page = rendered / "lessons/s" / directory / "index.html"
        page = assembled / "lessons/s" / directory / "index.html"
        assert page.read_bytes() == shard_page.read_bytes(), directory
    # And the second render of the assembly is byte-identical to the first.
    again = run_check(
        "determinism",
        site,
        assembled,
        env={"PBC_TEST_LOG": str(log), "PBC_STORE_SELECTION": str(chosen)},
    )
    assert again.returncode == 0, output(again)
    assert executed(log) == []


def test_a_shard_leaves_no_page_of_an_earlier_build_in_its_output(
    site: Path, tmp_path: Path
):
    """A render of one page keeps what the directory holds; the shard starts clean."""
    out = tmp_path / "out"
    out.mkdir()
    (out / "stale.html").write_text("an earlier build")
    shard = shard_file(tmp_path / "shard.json", 1, [LESSON_A])

    result = build_shard(site, out, tmp_path / "log", shard)

    assert result.returncode == 0, output(result)
    assert (out / "lessons/s/01-a/index.html").is_file()
    assert not (out / "stale.html").exists()
