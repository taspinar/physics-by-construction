"""The parts of the lesson shards and their assembly (ADR 014 decision 11, F113).

A shard hands over a part; the assembly verifies the parts as data, renders the
one site from their store, and compares every lesson page with the page its
shard rendered. The tests run on a small repository in a temporary directory
whose shards and parts are written by the code under test from a fake build
(a store entry and a page per lesson), and damage one thing at a time.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from support.paths import REPO_ROOT
from test_lesson_digest import FILES, _lesson, _write

from pbc.authoring import assemble
from pbc.authoring import selection as selecting
from pbc.authoring import shards as sharding
from pbc.authoring.digest import render

LESSONS = [f"site/lessons/s/0{n}-lesson" for n in range(1, 6)]
SHARDS = 3  # five lessons at two per shard


def page(lesson: str) -> str:
    return f"<html>{lesson}</html>\n"


def figure(lesson: str) -> bytes:
    return f"png of {lesson}".encode()


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    for name, text in FILES.items():
        if "02-two" not in name:
            _write(root, name, text)
    _write(root, "src/pbc/data/__init__.py", 'SAMPLES_DIR = "data/samples"\n')
    _write(root, "scripts/verify.conf", "shard-size: 2\nfake: true\n")
    for lesson in LESSONS:
        _write(root, f"{lesson}/index.qmd", _lesson("x = 1\n"))
    return root


def build_shard(
    root: Path,
    number: int,
    *,
    executed: list[str] | None = None,
    total: int = SHARDS,
) -> None:
    """The state a shard leaves: its digests, the store entries of its share,
    and the pages it rendered, as the build writes them."""
    data = sharding.write(root, f"{number}/{total}")
    (root / "site/_digests.json").write_text(render(root), encoding="utf-8")
    shutil.rmtree(root / "site/_freeze", ignore_errors=True)
    shutil.rmtree(root / "site/_site", ignore_errors=True)
    for lesson in data["lessons"]:
        relative = Path(lesson).relative_to("site")
        results = root / "site/_freeze" / relative / "index/execute-results"
        results.mkdir(parents=True)
        (results / "html.json").write_text(json.dumps({"lesson": lesson}))
        (root / "site/_freeze" / relative / "index/figure-html").mkdir()
        (root / "site/_freeze" / relative / "index/figure-html/f.png").write_bytes(
            figure(lesson)
        )
    for lesson in data["lessons"] if executed is None else executed:
        write_site(root / "site/_site", lesson)


def write_site(site: Path, lesson: str) -> None:
    directory = site / Path(lesson).relative_to("site")
    (directory / "index_files").mkdir(parents=True, exist_ok=True)
    (directory / "index.html").write_text(page(lesson), encoding="utf-8")
    (directory / "index_files/fig.png").write_bytes(figure(lesson))


def make_parts(root: Path, destination: Path) -> Path:
    destination.mkdir()
    for number in range(1, SHARDS + 1):
        build_shard(root, number)
        assemble.write_part(root, destination / assemble.part_name(number))
    return destination


def assembled_site(root: Path) -> None:
    """The site the assembly renders: every page, as the shards rendered it."""
    shutil.rmtree(root / "site/_site", ignore_errors=True)
    for lesson in LESSONS:
        write_site(root / "site/_site", lesson)


@pytest.fixture
def parts(repository: Path, tmp_path: Path) -> Path:
    return make_parts(repository, tmp_path / "parts")


def part_of(parts: Path, number: int) -> Path:
    return parts / assemble.part_name(number)


def record(directory: Path) -> None:
    """Record the files of a part again, as a careless forger would."""
    files = assemble._files(directory)
    files.pop(assemble.LIST_FILE, None)
    lines = [f"{assemble._sha(p)}  {n}" for n, p in sorted(files.items())]
    (directory / assemble.LIST_FILE).write_text("\n".join(lines) + "\n")


def refused(root: Path, parts: Path, *words: str) -> None:
    with pytest.raises(assemble.InvalidParts) as error:
        assemble.verify_parts(root, parts)
    for word in words:
        assert word in str(error.value)


def test_the_parts_of_every_shard_are_assembled_and_cover_every_lesson_once(
    repository: Path, parts: Path
):
    result = assemble.verify_parts(repository, parts)
    assert [d["shard"] for d in result] == [1, 2, 3]
    covered = [lesson for data in result for lesson in data["lessons"]]
    assert sorted(covered) == LESSONS
    assert len(set(covered)) == len(covered)


def test_the_union_is_a_base_that_executes_no_lesson(
    repository: Path, parts: Path, tmp_path: Path
):
    chosen = assemble.build_union(repository, parts, tmp_path / "union")
    assert chosen["mode"] == "selective" and chosen["execute"] == []
    assert chosen["reuse"] == LESSONS
    assert selecting.read(repository)["execute"] == []
    stored = sorted(
        p.relative_to(tmp_path / "union/freeze").as_posix()
        for p in (tmp_path / "union/freeze").glob("lessons/*/*")
    )
    assert stored == [Path(lesson).relative_to("site").as_posix() for lesson in LESSONS]
    assert (tmp_path / "union/digests.json").read_text() == render(repository)


def test_the_assembled_site_equal_to_the_shards_pages_is_accepted(
    repository: Path, parts: Path
):
    assembled_site(repository)
    assert assemble.compare(repository, parts) == len(LESSONS)


def test_a_missing_part_fails_the_assembly(repository: Path, parts: Path):
    shutil.rmtree(part_of(parts, 2))
    refused(repository, parts, "missing the part", "lesson-shard-2")


def test_an_extra_part_fails_the_assembly(repository: Path, parts: Path):
    shutil.copytree(part_of(parts, 1), parts / "lesson-shard-4")
    refused(repository, parts, "unexpected lesson-shard-4")


def test_a_part_that_is_a_file_or_a_stray_file_fails_the_assembly(
    repository: Path, parts: Path
):
    (parts / "notes.txt").write_text("x")
    refused(repository, parts, "unexpected notes.txt")


def test_an_altered_file_fails_the_assembly(repository: Path, parts: Path):
    target = next(part_of(parts, 1).glob("site/lessons/*/*/index.html"))
    target.write_text("<html>changed</html>\n")
    refused(repository, parts, "lesson-shard-1", "not the file that was recorded")


def test_an_altered_store_entry_fails_the_assembly(repository: Path, parts: Path):
    target = next(part_of(parts, 3).glob("freeze/lessons/*/*/index/figure-html/f.png"))
    target.write_bytes(b"forged")
    refused(repository, parts, "lesson-shard-3", "recorded")


def test_a_missing_file_fails_the_assembly(repository: Path, parts: Path):
    next(part_of(parts, 2).glob("site/lessons/*/*/index_files/fig.png")).unlink()
    refused(repository, parts, "missing")


def test_an_extra_file_fails_the_assembly(repository: Path, parts: Path):
    (part_of(parts, 2) / "extra.txt").write_text("x")
    refused(repository, parts, "unexpected extra.txt")


def test_a_link_fails_the_assembly(repository: Path, parts: Path, tmp_path: Path):
    outside = tmp_path / "outside"
    outside.write_text("x")
    (part_of(parts, 1) / "link").symlink_to(outside)
    refused(repository, parts, "symbolic link")


def test_a_list_that_names_a_path_outside_the_part_fails_the_assembly(
    repository: Path, parts: Path
):
    listing = part_of(parts, 1) / assemble.LIST_FILE
    listing.write_text(listing.read_text() + f"{'0' * 64}  ../escape\n")
    refused(repository, parts, "not a valid entry")


def test_a_part_of_another_share_fails_the_assembly(repository: Path, parts: Path):
    # Shard 2 hands over what shard 1 holds: a lesson twice, another in no part.
    shutil.rmtree(part_of(parts, 2))
    shutil.copytree(part_of(parts, 1), part_of(parts, 2))
    refused(repository, parts, "lesson-shard-2", "shard 1/3")


def test_a_part_that_claims_another_share_fails_the_assembly(
    repository: Path, parts: Path
):
    directory = part_of(parts, 2)
    data = json.loads((directory / assemble.PART_FILE).read_text())
    data["lessons"] = data["lessons"] + [LESSONS[0]]
    (directory / assemble.PART_FILE).write_text(json.dumps(data))
    record(directory)
    refused(repository, parts, "another share")


def test_a_lesson_in_a_part_without_a_store_entry_fails_the_assembly(
    repository: Path, parts: Path
):
    directory = part_of(parts, 1)
    entry = next(directory.glob("freeze/lessons/*/*"))
    shutil.rmtree(entry)
    record(directory)
    refused(repository, parts, "store entries")


def test_a_store_entry_without_an_executed_result_fails_the_assembly(
    repository: Path, parts: Path
):
    directory = part_of(parts, 1)
    next(directory.glob("freeze/lessons/*/*/index/execute-results/html.json")).unlink()
    record(directory)
    refused(repository, parts, "no executed result")


def test_a_part_made_from_other_sources_fails_the_assembly(
    repository: Path, parts: Path
):
    (repository / LESSONS[0] / "index.qmd").write_text(_lesson("x = 2\n"))
    refused(repository, parts, "digests")


def test_a_part_made_by_another_commit_fails_the_assembly(
    repository: Path, tmp_path: Path
):
    git = ["git", "-C", str(repository), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-q", "-m", "one"], check=True)
    parts = make_parts(repository, tmp_path / "parts")
    assemble.verify_parts(repository, parts)
    directory = part_of(parts, 3)
    data = json.loads((directory / assemble.PART_FILE).read_text())
    assert data["commit"]
    data["commit"] = "0" * 40
    (directory / assemble.PART_FILE).write_text(json.dumps(data))
    record(directory)
    refused(repository, parts, "was made at the commit")


def test_parts_that_took_different_bases_fail_the_assembly(
    repository: Path, parts: Path
):
    directory = part_of(parts, 2)
    data = json.loads((directory / assemble.PART_FILE).read_text())
    data["base"] = "a" * 64
    (directory / assemble.PART_FILE).write_text(json.dumps(data))
    record(directory)
    refused(repository, parts, "same base")


def test_a_full_run_in_which_a_shard_executed_less_than_its_share_fails(
    repository: Path, parts: Path
):
    directory = part_of(parts, 2)
    data = json.loads((directory / assemble.PART_FILE).read_text())
    data["executed"] = data["executed"][:1]
    (directory / assemble.PART_FILE).write_text(json.dumps(data))
    record(directory)
    refused(repository, parts)


def test_a_part_without_the_page_of_an_executed_lesson_fails_the_assembly(
    repository: Path, parts: Path
):
    directory = part_of(parts, 1)
    next(directory.glob("site/lessons/*/*/index.html")).unlink()
    record(directory)
    refused(repository, parts, "no page")


def test_a_lesson_page_that_differs_from_its_shards_fails_the_assembly(
    repository: Path, parts: Path
):
    assembled_site(repository)
    target = repository / "site/_site" / Path(LESSONS[3]).relative_to("site")
    (target / "index.html").write_text("<html>another page</html>\n")
    with pytest.raises(assemble.InvalidParts, match="differs from the file shard"):
        assemble.compare(repository, parts)


def test_a_figure_that_differs_from_its_shards_fails_the_assembly(
    repository: Path, parts: Path
):
    assembled_site(repository)
    target = repository / "site/_site" / Path(LESSONS[0]).relative_to("site")
    (target / "index_files/fig.png").write_bytes(b"other")
    with pytest.raises(assemble.InvalidParts, match=r"fig\.png: differs"):
        assemble.compare(repository, parts)


def test_a_lesson_page_the_assembly_did_not_render_fails_the_assembly(
    repository: Path, parts: Path
):
    assembled_site(repository)
    (
        repository / "site/_site" / Path(LESSONS[2]).relative_to("site") / "index.html"
    ).unlink()
    with pytest.raises(assemble.InvalidParts, match="the assembly did not render it"):
        assemble.compare(repository, parts)


def test_a_file_only_the_assembly_rendered_fails_the_assembly(
    repository: Path, parts: Path
):
    assembled_site(repository)
    extra = (
        repository / "site/_site" / Path(LESSONS[1]).relative_to("site") / "extra.png"
    )
    extra.write_bytes(b"x")
    with pytest.raises(assemble.InvalidParts, match="the shard did not render it"):
        assemble.compare(repository, parts)


def test_the_comparison_is_made_against_verified_parts(repository: Path, parts: Path):
    assembled_site(repository)
    shutil.rmtree(part_of(parts, 1))
    with pytest.raises(assemble.InvalidParts, match="missing the part"):
        assemble.compare(repository, parts)


# A pull request: a shard with nothing to execute still hands over the entries
# it restored, and the assembly compares only what the shards rendered.


def test_a_shard_with_nothing_to_execute_hands_over_its_store_and_no_page(
    repository: Path, tmp_path: Path
):
    parts = tmp_path / "parts"
    parts.mkdir()
    base = {"id": "b" * 64, "identity": "i"}
    for number in range(1, SHARDS + 1):
        build_shard(repository, number, executed=[] if number == 2 else None)
        share = sharding.read(root=repository)["lessons"]
        selection = {
            "format": selecting.SELECTION_FORMAT,
            "mode": "selective",
            "base": base,
            "lessons": LESSONS,
            "execute": [x for x in LESSONS if x not in share] if number == 2 else share,
            "reuse": [],
        }
        selecting.write(repository, selection)
        assemble.write_part(repository, parts / assemble.part_name(number))
    result = assemble.verify_parts(repository, parts)
    assert result[1]["executed"] == []
    assert not list(part_of(parts, 2).glob("site/**/*.html"))
    assert sorted(len(d["lessons"]) for d in result) == [1, 2, 2]
    shutil.rmtree(repository / "site/_site")
    for data in result:
        for lesson in data["executed"]:
            write_site(repository / "site/_site", lesson)
    assert assemble.compare(repository, parts) == len(LESSONS) - len(
        result[1]["lessons"]
    )


# --- the command ---------------------------------------------------------------


def command(root: Path, *arguments: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pbc.authoring.assemble",
            str(arguments[0]),
            "--root",
            str(root),
            *map(str, arguments[1:]),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )


def test_the_command_verifies_and_compares(
    repository: Path, parts: Path, tmp_path: Path
):
    union = tmp_path / "union"
    done = command(repository, "verify", "--parts", parts, "--union", union)
    assert done.returncode == 0, done.stderr
    assert "exactly once" in done.stdout
    assembled_site(repository)
    done = command(repository, "compare", "--parts", parts)
    assert done.returncode == 0, done.stderr


def test_the_command_fails_on_a_part_that_is_not_the_recorded_one(
    repository: Path, parts: Path, tmp_path: Path
):
    (part_of(parts, 1) / "extra.txt").write_text("x")
    done = command(repository, "verify", "--parts", parts, "--union", tmp_path / "u")
    assert done.returncode == 1
    assert "Error: " in done.stderr
    assert not (tmp_path / "u").exists()


def test_the_part_command_refuses_a_run_that_is_no_shard(repository: Path):
    done = command(repository, "part", "--out", repository / "out")
    assert done.returncode == 1
    assert "not a lesson shard" in done.stderr


def test_a_part_is_not_written_over_a_directory_it_does_not_own(
    repository: Path, tmp_path: Path
):
    build_shard(repository, 1)
    target = tmp_path / "precious"
    target.mkdir()
    (target / "file").write_text("keep")
    with pytest.raises(assemble.InvalidParts, match="earlier run"):
        assemble.write_part(repository, target)
    assert (target / "file").read_text() == "keep"


# --- the growth of the curriculum -------------------------------------------------

# Synthetic lessons check the orchestration at the sizes around the multiples
# of the shard size; what a lesson costs is measured on the real lessons in CI.
COUNTS = [31, 32, 33, 63, 64, 65, 96, 97, 127, 128, 129]


@pytest.fixture(params=COUNTS, ids=lambda count: f"{count}-lessons")
def curriculum(
    request: pytest.FixtureRequest, tmp_path: Path
) -> tuple[Path, Path, int]:
    root = tmp_path / "repo"
    for name, text in FILES.items():
        if "02-two" not in name:
            _write(root, name, text)
    _write(root, "src/pbc/data/__init__.py", 'SAMPLES_DIR = "data/samples"\n')
    _write(root, "scripts/verify.conf", "shard-size: 32\nfake: true\n")
    for n in range(request.param):
        _write(root, f"site/lessons/s{n // 40}/{n:03d}-l/index.qmd", _lesson("x = 1\n"))
    total = sharding.count(request.param, 32)
    parts = tmp_path / "parts"
    parts.mkdir()
    for number in range(1, total + 1):
        build_shard(root, number, total=total)
        assemble.write_part(root, parts / assemble.part_name(number))
    return root, parts, total


def test_the_assembly_of_every_size_covers_every_lesson_and_renders_every_page(
    curriculum: tuple[Path, Path, int], tmp_path: Path
):
    root, parts, total = curriculum
    everything = sharding.lessons(root)
    result = assemble.verify_parts(root, parts)
    assert len(result) == total == -(-len(everything) // 32)
    assert all(
        len(d["lessons"]) <= 32 and d["executed"] == d["lessons"] for d in result
    )
    chosen = assemble.build_union(root, parts, tmp_path / "union")
    assert chosen["execute"] == [] and chosen["reuse"] == everything
    shutil.rmtree(root / "site/_site")
    for lesson in everything:
        write_site(root / "site/_site", lesson)
    assert assemble.compare(root, parts) == len(everything)


def test_the_assembly_of_every_size_rejects_a_missing_extra_or_changed_part(
    curriculum: tuple[Path, Path, int],
):
    root, parts, total = curriculum
    last = part_of(parts, total)
    # An extra part: one more shard than the lessons derive.
    shutil.copytree(last, part_of(parts, total + 1))
    refused(root, parts, "unexpected")
    shutil.rmtree(part_of(parts, total + 1))
    # A duplicate: the last shard hands over the first one's share.
    saved = parts.parent / "saved"
    shutil.move(last, saved)
    if total > 1:
        shutil.copytree(part_of(parts, 1), last)
        refused(root, parts)
        shutil.rmtree(last)
    # A missing part.
    refused(root, parts, "missing the part")
    # A corrupted one.
    shutil.move(saved, last)
    assemble.verify_parts(root, parts)
    next(last.glob("site/lessons/*/*/index.html")).write_text("changed")
    refused(root, parts, "recorded")


def test_the_command_lines_of_verify_sh_are_accepted_by_the_parser():
    """The CI run failed on `part --root`: the option sat after the sub-command."""
    import re
    import shlex

    script = (REPO_ROOT / "scripts/verify.sh").read_text()
    lines = re.findall(
        r"python -m pbc\.authoring\.assemble "
        r"((?:part|verify|compare)(?:[^\n]*\\\n)*[^\n]*?)\)",
        script,
    )
    assert {line.split()[0] for line in lines} == {"part", "verify", "compare"}
    for line in lines:
        words = shlex.split(line.replace("\\\n", " "))
        words = [re.sub(r"\$\{?\w+\}?", "x", word) for word in words]
        # the parser accepts every option the script passes; --help style exit
        # codes (2) would raise SystemExit on an unrecognized argument
        parser_arguments = assemble.build_parser().parse_args(words)
        assert parser_arguments.command == words[0]
        assert parser_arguments.root == Path("x")


# -- the layouts that downloading the job artifacts produces -----------------------
# actions/download-artifact with a pattern extracts a single matching artifact
# straight into the target and several into one directory each (found by the first
# assemble job on a hosted runner, which had one shard).


@pytest.fixture
def single(tmp_path: Path) -> tuple[Path, Path]:
    """One shard (two lessons at shard-size 32): the repository and a part."""
    root = tmp_path / "single"
    for name, text in FILES.items():
        if "02-two" not in name:
            _write(root, name, text)
    _write(root, "src/pbc/data/__init__.py", 'SAMPLES_DIR = "data/samples"\n')
    _write(root, "scripts/verify.conf", "shard-size: 32\nfake: true\n")
    for lesson in LESSONS[:2]:
        _write(root, f"{lesson}/index.qmd", _lesson("x = 1\n"))
    build_shard(root, 1, total=1)
    part = tmp_path / "made"
    assemble.write_part(root, part)
    return root, part


def extracted_directly(part: Path, tmp_path: Path) -> Path:
    target = tmp_path / "direct"
    shutil.copytree(part, target)
    return target


def in_a_directory(part: Path, tmp_path: Path) -> Path:
    target = tmp_path / "per-directory"
    shutil.copytree(part, target / assemble.part_name(1))
    return target


def test_a_single_part_extracted_directly_and_one_directory_per_part_give_the_same_result(
    single: tuple[Path, Path], tmp_path: Path
):
    root, part = single
    direct = assemble.verify_parts(root, extracted_directly(part, tmp_path))
    nested = assemble.verify_parts(root, in_a_directory(part, tmp_path))
    assert direct == nested and [d["shard"] for d in direct] == [1]
    for layout in (
        extracted_directly(part, tmp_path / "a"),
        in_a_directory(part, tmp_path / "b"),
    ):
        chosen = assemble.build_union(root, layout, tmp_path / "union")
        assert chosen["execute"] == []
        assert assemble.compare(root, layout) == 2


def test_the_command_assembles_a_single_part_extracted_directly(
    single: tuple[Path, Path], tmp_path: Path
):
    root, part = single
    direct = extracted_directly(part, tmp_path)
    done = command(root, "verify", "--parts", direct, "--union", tmp_path / "u")
    assert done.returncode == 0, done.stderr + done.stdout


def test_the_direct_layout_is_refused_when_the_lessons_have_several_shards(
    repository: Path, parts: Path, tmp_path: Path
):
    refused_parts = extracted_directly(part_of(parts, 1), tmp_path)
    refused(repository, refused_parts, "directly", "3 shards")


def test_the_direct_layout_is_refused_beside_another_part_or_a_stray_file(
    single: tuple[Path, Path], tmp_path: Path
):
    root, part = single
    direct = extracted_directly(part, tmp_path)
    (direct / "notes.txt").write_text("x")
    refused(root, direct, "unexpected notes.txt")
    (direct / "notes.txt").unlink()
    shutil.copytree(part, direct / "lesson-shard-1")
    refused(root, direct, "unexpected lesson-shard-1")


def test_the_direct_layout_keeps_every_integrity_rule(
    single: tuple[Path, Path], tmp_path: Path
):
    root, part = single
    direct = extracted_directly(part, tmp_path)
    next(direct.glob("site/lessons/*/*/index.html")).write_text("changed")
    refused(root, direct, "recorded")
    (direct / assemble.LIST_FILE).unlink()
    refused(root, direct, "is missing")
