"""The facts of the verification audit hold in the repository (F118).

``docs/verification-audit.md`` states what a full run executes and compares,
that the third build duplicates the determinism check, which inputs the check
identity has and which domain each affects, and how ``integration`` divides
into parts that run every test once. F119 (Issue #185) applied what the
audit justified; where the repository differs from the state the audit
recorded, these tests assert the state after F119 and the audit says so.
They read the code and the document and fail when the two disagree, so the
audit cannot go stale unnoticed. They run no lesson and no browser.
"""

import ast
import json
import re
import subprocess
import sys
from pathlib import Path

from support import lesson_checks, verify_conf
from support.paths import REPO_ROOT, SCRIPTS

from pbc.authoring import digest
from pbc.authoring import selection as selecting
from pbc.authoring import store as storing

AUDIT = REPO_ROOT / "docs" / "verification-audit.md"
READINESS = REPO_ROOT / "docs" / "release-readiness.md"
# The test of the third build, consolidated into the determinism check (F119).
PREVIEW_TEST = "test_a_second_build_gives_byte_identical_previews"
# What the second build of the determinism check leaves out of its copy.
COPY_LEAVES_OUT = {"_site", ".quarto", "_freeze", "_digests.json", "_timings.json"}


def _section(heading: str) -> str:
    """The text of a section of the audit, from its heading to the next of
    the same or a higher level."""
    text = AUDIT.read_text(encoding="utf-8")
    start = re.search(rf"^(#+) {re.escape(heading)}\s*$", text, re.MULTILINE)
    assert start, f"the audit has no section {heading!r}"
    level = len(start.group(1))
    rest = text[start.end() :]
    end = re.search(rf"^#{{1,{level}}} ", rest, re.MULTILINE)
    return rest[: end.start()] if end else rest


def _rows(section: str) -> list[list[str]]:
    """The cells of the table rows of a section, without header and rule."""
    rows = []
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            continue
        rows.append(cells)
    return rows[1:]  # the header


def _names(cell: str) -> list[str]:
    return re.findall(r"`([^`]+)`", cell)


# The call graph: what each build does and how often a lesson executes.


def test_the_comparisons_that_need_the_machine_of_the_build_are_in_its_group():
    groups = verify_conf.groups()
    assert {name for name, group in groups.items() if group == "build"} == {
        "lean-build",
        "site-build",
        "determinism",
        "site-checks-reproduction",
    }
    # The three checks of the built site that read the artifact run in groups
    # of their own and execute no lesson: none of them builds.
    for name in ("site-checks-pages-1", "site-checks-pages-2", "site-checks-other"):
        assert groups[name].startswith("e2e-")
        assert "build-site" not in verify_conf.command(name)


def test_the_audit_names_every_check_of_the_group_build_and_the_e2e_groups():
    graph = _section("Call graph")
    for name, group in verify_conf.groups().items():
        if group == "build" or group.startswith("e2e-"):
            assert f"`{name}`" in graph, f"the call graph does not name {name}"


def _lessons_left_by(selection: dict | None) -> list[str]:
    """The lessons whose same-machine tests a run with ``selection`` collects.

    tests/e2e/conftest.py drops the reproduction and the experiment of every
    lesson a selective run does not execute; without a selection, or with one
    that is not selective, every lesson stays."""
    lessons = [
        page.parent.relative_to(REPO_ROOT / "site").as_posix()
        for page in lesson_checks.lesson_pages(REPO_ROOT)
    ]
    if selection is None or selection.get("mode") != "selective":
        return lessons
    executed = {
        Path(lesson).relative_to("site").as_posix() for lesson in selection["execute"]
    }
    return [lesson for lesson in lessons if lesson in executed]


def test_the_lessons_left_by_a_selection(tmp_path):
    every = _lessons_left_by(None)
    assert len(every) == len(lesson_checks.lesson_pages(REPO_ROOT))
    assert len(every) >= 2
    chosen = every[0]
    path = tmp_path / selecting.SELECTION_FILE
    path.parent.mkdir(parents=True)

    def left(selection: dict) -> list[str]:
        path.write_text(json.dumps(selection), encoding="utf-8")
        return _lessons_left_by(selecting.read(tmp_path))

    base = {"format": selecting.SELECTION_FORMAT}
    assert _lessons_left_by(selecting.read(tmp_path)) == every  # no file
    assert left({**base, "mode": "full", "reason": "x", "execute": []}) == every
    assert left({**base, "mode": "selective", "execute": [f"site/{chosen}"]}) == [
        chosen
    ]
    assert left({**base, "mode": "selective", "execute": []}) == []


def test_a_lesson_executes_four_times_in_a_full_run():
    # build 1 is site-build, build 2 is determinism, the third execution is
    # the reproduction of the page, and the fourth the experiment of the
    # lesson, without a render (F117, ADR 016 decision 4). The third build of
    # the preview test (four executions before F119, as the audit recorded)
    # is consolidated into the determinism check (F119, ADR 017 decision 8).
    commands = verify_conf.checks()
    assert commands["site-build"] == "./scripts/build-site.sh"
    assert commands["determinism"] == "./scripts/check-determinism.sh"
    assert "-m same_machine" in commands["site-checks-reproduction"]
    determinism = (SCRIPTS / "check-determinism.sh").read_text(encoding="utf-8")
    assert '"$root/scripts/build-site.sh" "$tmp/site"' in determinism

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/e2e",
            "-m",
            "same_machine",
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    collected = [line for line in result.stdout.splitlines() if "::" in line]
    reproductions = [line for line in collected if "reproduce_commands" in line]
    experiments = [line for line in collected if "the_experiment_regenerates" in line]
    assert [line for line in collected if PREVIEW_TEST in line] == []
    # One reproduction and one experiment per lesson, and nothing else
    # compares bytes on the machine of the build.
    assert sorted(reproductions + experiments) == sorted(collected)
    # A selective local run (--base) keeps those of the executed lessons only.
    left = _lessons_left_by(selecting.read(REPO_ROOT))
    assert len(reproductions) == len(left)
    assert len(experiments) == len(left)

    # The reproduction renders in a clone, which holds no store and no
    # selection, so it executes the lesson itself.
    source = (REPO_ROOT / "tests" / "e2e" / "test_lessons.py").read_text("utf-8")
    body = source[source.index("def test_reproduce_commands_regenerate") :]
    body = body[: body.index("\ndef test_format_2_lessons")]
    assert "PBC_STORE_SELECTION" not in body and "_freeze" not in body


# The verdict on the third build.


def _determinism_leaves_out() -> set[str]:
    script = (SCRIPTS / "check-determinism.sh").read_text(encoding="utf-8")
    removed = set()
    for line in script.splitlines():
        if line.startswith("rm -"):
            removed |= {
                token.removeprefix('"$tmp/site/').removesuffix('"')
                for token in line.split()
                if token.startswith('"$tmp/site/')
            }
    return removed


def test_the_second_build_starts_from_a_copy_without_the_state_of_a_build():
    assert _determinism_leaves_out() == COPY_LEAVES_OUT


def test_a_selection_that_is_not_selective_restores_nothing(tmp_path):
    # The determinism check hands the selection file to its build whatever the
    # mode; a build restores nothing for any mode but selective.
    site = tmp_path / "site"
    site.mkdir()
    assert storing.prepare(site, None) == []
    assert storing.prepare(site, {"mode": "full"}) == []
    script = (SCRIPTS / "check-determinism.sh").read_text(encoding="utf-8")
    assert "selection.json" in script and "PBC_STORE_SELECTION" in script


def test_the_preview_test_is_consolidated_into_the_determinism_check():
    # F119, on the verdict of the audit: the determinism check compares every
    # file of the first build with every file of the second, names and bytes,
    # previews included; the test that compared the previews of a third build
    # and its helper are gone; the regression test of the comparison runs the
    # script on fixture trees; and a lesson without a preview still fails a
    # check of the built site.
    script = (SCRIPTS / "check-determinism.sh").read_text(encoding="utf-8")
    assert 'diff -r "$first" "$tmp/second"' in script
    lessons = (REPO_ROOT / "tests" / "e2e" / "test_lessons.py").read_text("utf-8")
    assert PREVIEW_TEST not in lessons and "second_build" not in lessons
    assert not (REPO_ROOT / "tests" / "support" / "second_build.py").exists()
    regression = REPO_ROOT / "tests" / "integration" / "test_determinism_check.py"
    assert "previews" in regression.read_text("utf-8")
    built = (REPO_ROOT / "tests" / "e2e" / "test_built_site.py").read_text("utf-8")
    assert "def test_every_lesson_has_one_verified_preview_within_the_budget" in built


# The validity domains of the check identity.


def _identity_rows() -> dict[str, dict]:
    rows = {}
    for cells in _rows(_section("Classification of the inputs")):
        names = _names(cells[0])
        assert len(names) == 1, cells
        rows[names[0]] = {
            "domains": [d for d, mark in zip("SRVB", cells[1:5], strict=True) if mark],
            "verdict": cells[5],
        }
    return rows


def test_every_input_of_the_check_identity_is_classified_in_the_audit():
    inputs = set(digest.CHECK_FILES) | set(digest.CHECK_DIRECTORIES)
    rows = _identity_rows()
    classified = set(rows)
    assert inputs - classified == set(), (
        "an input of the check identity that the audit does not classify "
        "belongs to every domain (ADR 014 decision 10): classify it"
    )
    # The one input that left the identity (F119): classified, V only, and
    # the domain of no reused result; the row says so.
    assert classified - inputs == {"tests/integration"}
    assert "left the identity" in rows["tests/integration"]["verdict"]


def test_the_verdict_of_an_input_agrees_with_its_domains():
    for name, row in _identity_rows().items():
        if row["verdict"].startswith("every domain"):
            assert len(row["domains"]) >= 2, name
        else:
            assert row["verdict"].startswith("V only"), name
            assert row["domains"] == ["V"], name


def test_no_check_that_a_base_reduces_reads_the_integration_tests():
    # What the audit says makes tests/integration splittable from the
    # identity with a complete-input test: the builds, the reproductions, and
    # the per-page checks neither read nor import it. The only mentions are
    # comments and docstrings, the check that runs it, and the identity.
    allowed = {
        "tests/support/site_checks.py",
        "tests/support/lesson_checks.py",
        "scripts/verify.conf",
        "src/pbc/authoring/digest.py",
        # A comment that names the test of the division of the checks.
        ".github/workflows/ci.yml",
    }
    mentions = set()
    for directory in ("tests/e2e", "tests/support", "scripts", "src", ".github"):
        for path in (REPO_ROOT / directory).rglob("*"):
            if not path.is_file() or path.suffix not in {".py", ".sh", ".yml", ".conf"}:
                continue
            if "tests/integration" in path.read_text(encoding="utf-8"):
                mentions.add(path.relative_to(REPO_ROOT).as_posix())
    assert mentions <= allowed, sorted(mentions - allowed)
    # Its only consumers are the check-tests-* checks, in groups that a base
    # never reduces (the groups build and e2e-* are the reduced ones).
    consumers = {
        name
        for name, command in verify_conf.checks().items()
        if "tests/integration" in command
    }
    parts = ("check-tests-quarto", "check-tests-browser", "check-tests-other")
    assert consumers == set(parts)
    for name in consumers:
        group = verify_conf.groups()[name]
        assert group != "build" and not group.startswith("e2e-"), name
    for path in [
        *(REPO_ROOT / "tests" / "e2e").glob("*.py"),
        *(REPO_ROOT / "tests" / "support").glob("*.py"),
    ]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = {
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        } | {
            a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
        }
        assert not [m for m in imported if m.split(".")[0] == "integration"], path


# The division of integration.


def _parts() -> tuple[list[str], list[str]]:
    rows = _rows(
        _section("Division into independent parts").split("What it would shorten")[0]
    )
    named = {int(cells[0]): _names(cells[1]) for cells in rows}
    return named[1], named[2]


def test_the_parts_of_integration_are_the_checks_of_verify_conf():
    # F119 applied the division: parts 1 and 2 of the record are the files the
    # checks check-tests-quarto and check-tests-browser name, and
    # check-tests-other runs every file they do not name. That the three run
    # every test exactly once is proved by collection in
    # tests/integration/test_site_check_division.py.
    first, second = _parts()
    here = REPO_ROOT / "tests" / "integration"
    present = sorted(p.name for p in here.glob("test_*.py"))
    named = [*first, *second]
    assert len(named) == len(set(named)), "a file is named in two parts"
    assert set(named) <= set(present), sorted(set(named) - set(present))
    rest = [name for name in present if name not in named]
    assert rest and "test_verification_audit.py" in rest

    directory = "tests/integration"
    commands = verify_conf.checks()
    assert verify_conf.groups()["check-tests-quarto"] == "integration-quarto"
    assert verify_conf.groups()["check-tests-browser"] == "integration-browser"
    assert verify_conf.groups()["check-tests-other"] == "integration-other"
    assert "check-tests" not in commands
    quarto = commands["check-tests-quarto"].split()[4:]
    browser = commands["check-tests-browser"].split()[4:]
    assert quarto == [f"{directory}/{name}" for name in first]
    assert browser == [f"{directory}/{name}" for name in second]
    other = commands["check-tests-other"].split()[4:]
    assert other == [directory, *(f"--ignore={directory}/{name}" for name in named)]


# The targeted run (ADR 017 decision 7).


def test_the_targeted_run_builds_no_site_and_reads_none():
    # The groups of the targeted run hold no check that builds the site, builds
    # it again, reproduces a lesson, or reads the built site; the render of
    # the selected lessons never calls the site build.
    groups = verify_conf.groups()
    commands = verify_conf.checks()
    targeted = verify_conf.targeted()
    assert "build" not in targeted and not any(g.startswith("e2e-") for g in targeted)
    for name, group in groups.items():
        if group in targeted:
            assert name not in {"site-build", "determinism", "lean-build"}, name
            assert not name.startswith("site-checks-"), name
            assert "build-site" not in commands[name], name
            assert "tests/e2e" not in commands[name], name
    assert groups["lesson-pages"] in targeted
    assert commands["lesson-pages"] == "./scripts/check-lesson-pages.sh"
    render = (SCRIPTS / "check-lesson-pages.sh").read_text(encoding="utf-8")
    assert "build-site.sh" not in render and "quarto render" in render
    assert "never builds the site" in render


# The record of the measurements.


def test_the_runs_the_audit_cites_are_recorded_with_the_measurements():
    cited = set(re.findall(r"\b3[0-9]{10}\b", AUDIT.read_text(encoding="utf-8")))
    readiness = READINESS.read_text(encoding="utf-8")
    assert cited
    assert {run for run in cited if run not in readiness} == set()
    section = readiness[readiness.index("(F118), measured 2026-10-15") :]
    assert "ADR 015" in section and "15-minute target" in section
    assert "projection" in section.lower()
