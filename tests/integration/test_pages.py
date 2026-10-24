"""Which pages a run with a base checks (ADR 014 decision 3, F61 step 6).

The checks of one page and the reproduction of a lesson read the selection the
run made. The tests use small built sites in a temporary directory and a
selection written by hand; ``test_selection.py`` shows how the selection is
made.
"""

import importlib.util
import json
import types
from pathlib import Path

import pytest
from support import site_checks
from support.paths import REPO_ROOT

from pbc.authoring import pages
from pbc.authoring import selection as selecting

BASE_COMMIT = "a" * 40
RUN_COMMIT = "b" * 40
LESSON_ONE = "lessons/s/01-one/index.html"
LESSON_TWO = "lessons/s/02-two/index.html"


def built(site: Path, commit: str, changed: dict[str, str] | None = None) -> Path:
    """A built site whose lesson pages name ``commit``."""
    files = {
        "index.html": "<p>Home</p>",
        LESSON_ONE: f"<p>One, built from {commit}.</p>",
        LESSON_TWO: f"<p>Two, built from {commit}.</p>",
        "lessons/s/01-one/index_files/fig.png": "figure",
        **(changed or {}),
    }
    for name, text in files.items():
        (site / name).parent.mkdir(parents=True, exist_ok=True)
        (site / name).write_text(text, encoding="utf-8")
    return site


@pytest.fixture
def base(tmp_path: Path) -> Path:
    """The record of the base: its site built from another commit."""
    site = built(tmp_path / "base-site", BASE_COMMIT)
    directory = tmp_path / "base"
    directory.mkdir()
    (directory / pages.PAGES).write_text(
        json.dumps(pages.record(site, BASE_COMMIT)), encoding="utf-8"
    )
    return directory


def selective(base: Path, execute: list[str]) -> dict:
    return {
        "format": selecting.SELECTION_FORMAT,
        "mode": "selective",
        "base_directory": str(base),
        "execute": execute,
        "reuse": [],
    }


@pytest.fixture
def chosen(monkeypatch: pytest.MonkeyPatch):
    """Make a selection the selection of the run, and the commit its own."""

    def make(selection: dict | None) -> None:
        monkeypatch.setattr(selecting, "read", lambda root=REPO_ROOT: selection)
        monkeypatch.setattr(
            pages, "build_commit", lambda: types.SimpleNamespace(sha=RUN_COMMIT)
        )

    return make


def test_the_commit_is_the_only_difference_between_pages_of_two_commits(
    tmp_path: Path, base: Path
):
    site = built(tmp_path / "site", RUN_COMMIT)
    record = pages.read(base / pages.PAGES)

    assert pages.differing(site, record, RUN_COMMIT) == []


@pytest.mark.parametrize(
    "change",
    [
        {LESSON_TWO: f"<p>Two changed, built from {RUN_COMMIT}.</p>"},
        {"index.html": "<p>Home, changed</p>"},
        {"new/index.html": "<p>New</p>"},
    ],
    ids=["a lesson page", "a page that is not a lesson", "a page the base lacks"],
)
def test_a_page_that_differs_from_the_base_is_checked_and_nothing_else_is(
    tmp_path: Path, base: Path, chosen, change
):
    site = built(tmp_path / "site", RUN_COMMIT, change)
    chosen(selective(base, execute=[]))

    selected = pages.selected(site)

    assert selected == sorted(name for name in change if name.endswith(".html"))


def test_a_lesson_the_run_executed_is_checked_even_when_its_page_is_the_same(
    tmp_path: Path, base: Path, chosen
):
    site = built(tmp_path / "site", RUN_COMMIT)
    chosen(selective(base, execute=["site/lessons/s/01-one"]))

    assert pages.selected(site) == [LESSON_ONE]


def test_a_changed_figure_of_a_lesson_does_not_hide_behind_an_equal_page(
    tmp_path: Path, base: Path, chosen
):
    # The page of an executed lesson is checked whatever its bytes are.
    site = built(
        tmp_path / "site", RUN_COMMIT, {"lessons/s/01-one/index_files/fig.png": "new"}
    )
    chosen(selective(base, execute=["site/lessons/s/01-one"]))

    assert LESSON_ONE in pages.selected(site)


@pytest.mark.parametrize(
    "selection",
    [
        None,
        {"format": selecting.SELECTION_FORMAT, "mode": "full", "execute": []},
    ],
    ids=["no base", "a full run"],
)
def test_a_run_without_a_usable_base_checks_every_page(
    tmp_path: Path, chosen, selection
):
    chosen(selection)

    assert pages.selected(built(tmp_path / "site", RUN_COMMIT)) is None


@pytest.mark.parametrize(
    "damage",
    [
        lambda record: record.unlink(),
        lambda record: record.write_text("[1"),
        lambda record: record.write_text('{"format": 0, "files": {}}'),
        lambda record: record.write_text('{"format": 1, "files": {"a": 1}}'),
        lambda record: record.write_text("[1, 2]"),
        lambda record: record.write_text("7"),
        lambda record: record.write_text("null"),
    ],
    ids=[
        "missing",
        "truncated",
        "another format",
        "a checksum that is no text",
        "a list",
        "a number",
        "null",
    ],
)
def test_a_record_of_the_base_that_cannot_be_used_selects_every_page(
    tmp_path: Path, base: Path, chosen, damage
):
    damage(base / pages.PAGES)
    chosen(selective(base, execute=[]))

    assert pages.selected(built(tmp_path / "site", RUN_COMMIT)) is None


ASSETS = {
    "assets/site.css": "body { color: black; }",
    "site_libs/quarto.js": "original();",
    "assets/fonts/Math.woff2": "font",
}
EVERY_PAGE = sorted(["index.html", LESSON_ONE, LESSON_TWO])


ASSET_CHANGES = {
    "a style sheet": {"assets/site.css": "body { color: red; }"},
    "a script": {"site_libs/quarto.js": "changed();"},
    "a font": {"assets/fonts/Math.woff2": "changed"},
    "an image": {"lessons/s/01-one/index_files/fig.png": "new"},
}


@pytest.fixture
def base_with_assets(tmp_path: Path) -> Path:
    """The record of a base whose site has a style sheet, a script, and a font."""
    site = built(tmp_path / "base-site", BASE_COMMIT, ASSETS)
    directory = tmp_path / "base"
    directory.mkdir()
    (directory / pages.PAGES).write_text(
        json.dumps(pages.record(site, BASE_COMMIT)), encoding="utf-8"
    )
    return directory


@pytest.mark.parametrize("change", ASSET_CHANGES.values(), ids=ASSET_CHANGES.keys())
def test_a_file_that_is_not_a_page_checks_every_page_and_executes_no_lesson(
    tmp_path: Path, base_with_assets: Path, chosen, conftest, change
):
    site = built(tmp_path / "site", RUN_COMMIT, {**ASSETS, **change})
    selection = selective(base_with_assets, execute=[])
    chosen(selection)
    record = pages.read(base_with_assets / pages.PAGES)

    checked = pages.checked(site)

    # No page differs; only the file that is not a page does.
    assert pages.differing(site, record, RUN_COMMIT) == []
    assert checked["assets"] == list(change)
    assert pages.selected(site) == EVERY_PAGE
    assert checked["pages"] == dict.fromkeys(EVERY_PAGE, pages.ASSET)
    # It executes no lesson: the reproduction of every lesson is left out.
    items = [reproduction(LESSON_ONE), reproduction(LESSON_TWO)]
    assert conftest._reproductions_of_unchanged_lessons(items) == items
    assert selection["execute"] == []


@pytest.mark.parametrize(
    "difference",
    [
        lambda site: (site / "assets" / "new.js").write_text("new();"),
        lambda site: (site / "assets" / "fonts" / "Math.woff2").unlink(),
    ],
    ids=["a file the base does not have", "a file the site no longer has"],
)
def test_a_file_that_is_added_or_removed_checks_every_page(
    tmp_path: Path, base_with_assets: Path, chosen, difference
):
    site = built(tmp_path / "site", RUN_COMMIT, ASSETS)
    difference(site)
    chosen(selective(base_with_assets, execute=[]))

    assert pages.selected(site) == EVERY_PAGE


def test_the_record_says_which_pages_are_checked_only_for_a_file_that_is_not_a_page(
    tmp_path: Path, base_with_assets: Path, chosen
):
    site = built(
        tmp_path / "site",
        RUN_COMMIT,
        {
            **ASSETS,
            **ASSET_CHANGES["a style sheet"],
            LESSON_TWO: f"<p>Two changed, built from {RUN_COMMIT}.</p>",
        },
    )
    chosen(selective(base_with_assets, execute=["site/lessons/s/01-one"]))

    assert pages.checked(site)["pages"] == {
        "index.html": pages.ASSET,
        LESSON_ONE: pages.EXECUTED,
        LESSON_TWO: pages.DIFFERS,
    }


def test_the_checks_of_one_page_write_the_record_of_the_checked_pages(
    tmp_path: Path, base_with_assets: Path, chosen, monkeypatch: pytest.MonkeyPatch
):
    site = built(
        tmp_path / "site", RUN_COMMIT, {**ASSETS, **ASSET_CHANGES["a style sheet"]}
    )
    chosen(selective(base_with_assets, execute=[]))
    monkeypatch.setattr(site_checks, "BUILT_SITE", site)
    target = tmp_path / "verification" / "checked-pages.json"
    monkeypatch.setattr(site_checks, "CHECKED_RECORD", target)

    names = [
        page.relative_to(site).as_posix() for page in site_checks.checked_pages(site)
    ]

    written = json.loads(target.read_text(encoding="utf-8"))
    assert names == EVERY_PAGE
    assert written["mode"] == "selective"
    assert written["assets"] == ["assets/site.css"]
    assert written["pages"] == dict.fromkeys(EVERY_PAGE, pages.ASSET)


def test_a_run_that_checks_every_page_records_why(
    tmp_path: Path, base: Path, chosen, monkeypatch: pytest.MonkeyPatch
):
    site = built(tmp_path / "site", RUN_COMMIT)
    (base / pages.PAGES).write_text("[1")
    chosen(selective(base, execute=[]))
    monkeypatch.setattr(site_checks, "BUILT_SITE", site)
    target = tmp_path / "checked-pages.json"
    monkeypatch.setattr(site_checks, "CHECKED_RECORD", target)

    assert len(site_checks.checked_pages(site)) == 3
    written = json.loads(target.read_text(encoding="utf-8"))
    assert written["mode"] == "every"
    assert "pages.json" in written["reason"]
    assert set(written["pages"]) == set(EVERY_PAGE)


def test_the_checks_of_one_page_run_for_the_selected_pages_only(
    tmp_path: Path, base: Path, chosen, monkeypatch: pytest.MonkeyPatch
):
    site = built(
        tmp_path / "site",
        RUN_COMMIT,
        {LESSON_TWO: f"<p>Two changed, built from {RUN_COMMIT}.</p>"},
    )
    chosen(selective(base, execute=[]))
    monkeypatch.setattr(site_checks, "BUILT_SITE", site)
    monkeypatch.setattr(site_checks, "CHECKED_RECORD", tmp_path / "checked.json")

    names = [
        page.relative_to(site).as_posix() for page in site_checks.checked_pages(site)
    ]

    assert names == [LESSON_TWO]


def test_a_site_that_is_not_the_site_of_this_repository_is_checked_in_full(
    tmp_path: Path, base: Path, chosen
):
    site = built(tmp_path / "site", RUN_COMMIT)
    chosen(selective(base, execute=[]))

    assert len(site_checks.checked_pages(site)) == 3


# --- The reproduction of a lesson -------------------------------------------------


@pytest.fixture(scope="module")
def conftest():
    spec = importlib.util.spec_from_file_location(
        "e2e_conftest", REPO_ROOT / "tests" / "e2e" / "conftest.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reproduction(lesson: str, marked: bool = True):
    return types.SimpleNamespace(
        get_closest_marker=lambda name: object() if marked else None,
        callspec=types.SimpleNamespace(params={"lesson": lesson}),
    )


def test_the_reproduction_runs_for_the_lessons_the_run_executed(
    conftest, monkeypatch: pytest.MonkeyPatch
):
    items = [reproduction(LESSON_ONE), reproduction(LESSON_TWO)]
    selection = selective(Path("/base"), execute=["site/lessons/s/01-one"])
    monkeypatch.setattr(selecting, "read", lambda root: selection)

    skipped = conftest._reproductions_of_unchanged_lessons(items)

    assert skipped == [items[1]]


@pytest.mark.parametrize(
    "selection",
    [None, {"format": selecting.SELECTION_FORMAT, "mode": "full", "execute": []}],
    ids=["no base", "a full run"],
)
def test_the_reproduction_runs_for_every_lesson_without_a_usable_base(
    conftest, monkeypatch: pytest.MonkeyPatch, selection
):
    items = [reproduction(LESSON_ONE), reproduction(LESSON_TWO)]
    monkeypatch.setattr(selecting, "read", lambda root: selection)

    assert conftest._reproductions_of_unchanged_lessons(items) == []


def test_only_the_reproduction_of_a_lesson_is_left_out(
    conftest, monkeypatch: pytest.MonkeyPatch
):
    other = types.SimpleNamespace(
        get_closest_marker=lambda name: None,
        callspec=types.SimpleNamespace(params={"lesson": LESSON_TWO}),
    )
    unmarked = reproduction(LESSON_TWO, marked=False)
    selection = selective(Path("/base"), execute=[])
    monkeypatch.setattr(selecting, "read", lambda root: selection)

    assert conftest._reproductions_of_unchanged_lessons([other, unmarked]) == []


def test_the_build_script_records_the_pages_the_next_run_compares_with():
    script = (REPO_ROOT / "scripts" / "build-site.sh").read_text()

    assert "pbc.authoring.pages" in script and "_pages.json" in script


# --- A comparison with a fresh run on this machine (issue 268) ---------------------

GW_LESSON = "site/lessons/mechanics/11-gravitational-wave-strain"


def recorded(root: Path, selection: object) -> Path:
    """Write ``selection`` where verify.sh writes the selection of the run."""
    path = root / selecting.SELECTION_FILE
    path.parent.mkdir(parents=True)
    text = selection if isinstance(selection, str) else json.dumps(selection)
    path.write_text(text, encoding="utf-8")
    return root


def restoring(lesson: str) -> dict:
    """A selective run that restores ``lesson`` from the base."""
    return {
        **selective(Path("/base"), execute=["site/lessons/s/01-one"]),
        "base": {"id": "c" * 64, "identity": "i"},
        "lessons": sorted(["site/lessons/s/01-one", lesson]),
        "reuse": [lesson],
    }


def test_a_lesson_is_executed_in_a_run_without_a_selection(tmp_path: Path):
    # verify.sh removes the selection for a run without a base: every lesson
    # is executed, and the comparison runs.
    site = tmp_path / "site"

    assert site_checks.inherited(site, GW_LESSON, tmp_path, site) is None


@pytest.mark.parametrize(
    "selection",
    [
        {
            "format": selecting.SELECTION_FORMAT,
            "mode": "full",
            "base": None,
            "lessons": [GW_LESSON],
            "execute": [GW_LESSON],
            "reuse": [],
        },
        {
            **restoring("site/lessons/s/01-one"),
            "lessons": sorted(["site/lessons/s/01-one", GW_LESSON]),
            "execute": [GW_LESSON],
        },
    ],
    ids=["a full run", "a selection that executes it"],
)
def test_a_lesson_the_selection_executes_is_executed(tmp_path: Path, selection):
    root, site = recorded(tmp_path, selection), tmp_path / "site"

    assert site_checks.inherited(site, GW_LESSON, root, site) is None


def test_a_restored_lesson_is_inherited_from_the_base_it_names(tmp_path: Path):
    root, site = recorded(tmp_path, restoring(GW_LESSON)), tmp_path / "site"

    reason = site_checks.inherited(site, GW_LESSON, root, site)

    assert reason is not None
    assert GW_LESSON in reason and "c" * 12 in reason and "not executed" in reason


def test_a_site_built_elsewhere_is_not_described_by_the_selection(tmp_path: Path):
    root = recorded(tmp_path, restoring(GW_LESSON))

    assert (
        site_checks.inherited(tmp_path / "other", GW_LESSON, root, tmp_path / "site")
        is None
    )


@pytest.mark.parametrize(
    ("selection", "why"),
    [
        ("{not json", "cannot be read"),
        ({**restoring(GW_LESSON), "format": 0}, "another format"),
        ({**restoring(GW_LESSON), "mode": "partial"}, "another format"),
        ({**restoring(GW_LESSON), "reuse": None}, "does not list"),
        ({**restoring(GW_LESSON), "lessons": ["site/lessons/s/01-one"]}, "once"),
        ({**restoring(GW_LESSON), "reuse": []}, "once"),
        (
            {**restoring(GW_LESSON), "execute": ["site/lessons/s/01-one", GW_LESSON]},
            "once",
        ),
        ({**restoring(GW_LESSON), "mode": "full"}, "without a base"),
        ({**restoring(GW_LESSON), "base": None}, "without a base"),
        ({**restoring(GW_LESSON), "base": {"identity": "i"}}, "name the base"),
        (
            {**restoring(GW_LESSON), "base": {"id": "c" * 12, "identity": "i"}},
            "name the base",
        ),
        ({**restoring(GW_LESSON), "base": {"id": "c" * 64}}, "name the base"),
        (
            {**restoring(GW_LESSON), "base": {"id": "c" * 64, "identity": 1}},
            "name the base",
        ),
    ],
    ids=[
        "unreadable",
        "another format",
        "another mode",
        "no list",
        "not among the lessons",
        "neither executed nor restored",
        "executed and restored",
        "restored in a full run",
        "restored without a base",
        "a base without an id",
        "a base with a malformed id",
        "a base without an identity",
        "a base with a malformed identity",
    ],
)
def test_a_selection_that_cannot_be_trusted_is_an_error_never_a_skip(
    tmp_path: Path, selection, why: str
):
    root, site = recorded(tmp_path, selection), tmp_path / "site"

    with pytest.raises(site_checks.SelectionError, match=why):
        site_checks.inherited(site, GW_LESSON, root, site)


@pytest.fixture
def comparator():
    spec = importlib.util.spec_from_file_location(
        "e2e_test_comparator", REPO_ROOT / "tests" / "e2e" / "test_comparator.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Compared(Exception):
    """The comparison asked for the fresh run."""


def run_comparison(comparator, monkeypatch: pytest.MonkeyPatch, decision) -> None:
    """Run the comparison of the e2e test with ``decision`` as the answer of
    the selection; asking for the fresh run raises _Compared."""

    def answer(site_dir, lesson):
        assert lesson == GW_LESSON
        return decision()

    def fresh(name):
        assert name == "fresh"
        raise _Compared

    monkeypatch.setattr(comparator.site_checks, "inherited", answer)
    comparator.test_the_embedded_series_and_metrics_agree_with_a_fresh_run_of_pbc(
        Path("site"), {}, types.SimpleNamespace(getfixturevalue=fresh)
    )


def test_the_comparator_compares_a_lesson_this_run_executed(
    comparator, monkeypatch: pytest.MonkeyPatch
):
    with pytest.raises(_Compared):
        run_comparison(comparator, monkeypatch, lambda: None)


def test_the_comparator_skips_a_restored_lesson_with_the_reason(
    comparator, monkeypatch: pytest.MonkeyPatch
):
    with pytest.raises(pytest.skip.Exception, match="restored from the base"):
        run_comparison(
            comparator, monkeypatch, lambda: "the lesson was restored from the base"
        )


def test_the_comparator_fails_when_the_selection_cannot_be_trusted(
    comparator, monkeypatch: pytest.MonkeyPatch
):
    def broken():
        raise site_checks.SelectionError("selection.json cannot be read")

    with pytest.raises(pytest.fail.Exception, match="cannot be read"):
        run_comparison(comparator, monkeypatch, broken)


def test_the_comparator_fails_on_a_base_the_selection_cannot_name(
    comparator, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    # The selection restores the lesson but names no base: never a skip.
    selection = {**restoring(GW_LESSON), "base": {"id": "c" * 64}}
    root, site = recorded(tmp_path, selection), tmp_path / "site"
    inherited = site_checks.inherited

    with pytest.raises(pytest.fail.Exception, match="name the base"):
        run_comparison(
            comparator, monkeypatch, lambda: inherited(site, GW_LESSON, root, site)
        )
