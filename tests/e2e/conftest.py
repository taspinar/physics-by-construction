"""The built site, served as GitHub Pages serves it."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from support import shards
from support.paths import BUILT_SITE, REPO_ROOT, SITE_SOURCE
from support.site_server import SiteServer, configured_base_path

from pbc.authoring import pages as page_selection
from pbc.authoring import selection as selecting


@pytest.fixture(scope="session")
def site_dir(request: pytest.FixtureRequest) -> Path:
    directory = Path(request.config.getoption("--site-dir") or BUILT_SITE)
    if not (directory / "index.html").is_file():
        # A missing site is a failure, never a skip: these checks are required.
        pytest.fail(
            f"no built site in {directory}; run ./scripts/build-site.sh first",
            pytrace=False,
        )
    return directory


@pytest.fixture(scope="session")
def server(site_dir: Path) -> Iterator[SiteServer]:
    with SiteServer(site_dir, configured_base_path(SITE_SOURCE)) as server:
        yield server


def _reproductions_of_unchanged_lessons(items: list[pytest.Item]) -> list[pytest.Item]:
    """The reproductions of the lessons this run did not execute.

    A run with a base reproduces the lessons it executed: the page it
    regenerates is compared with a result this run computed on this machine, and
    for a lesson restored from the base there is none. A run without a base, a
    full run, and a base that cannot be used select every lesson (ADR 014
    decision 3)."""
    selection = selecting.read(REPO_ROOT)
    if selection is None or selection.get("mode") != "selective":
        return []
    executed = {
        f"{Path(lesson).relative_to('site').as_posix()}/index.html"
        for lesson in selection["execute"]
    }
    return [
        item
        for item in items
        if item.get_closest_marker("same_machine") is not None
        and getattr(item, "callspec", None) is not None
        and "lesson" in item.callspec.params
        and item.callspec.params["lesson"] not in executed
    ]


# Set when this run deselected reproductions and its selection executes no
# lesson: a run with nothing to reproduce, such as a change to the
# documentation only.
_NOTHING_TO_REPRODUCE = pytest.StashKey[bool]()


def _executes_no_lesson() -> bool:
    selection = selecting.read(REPO_ROOT)
    return (
        selection is not None
        and selection.get("mode") == "selective"
        and selection.get("execute") == []
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Keep what this run is to check: the reproduction of the lessons it
    executed, and the part of each test file that --shard asks for."""
    skipped = _reproductions_of_unchanged_lessons(items)
    if skipped:
        config.stash[_NOTHING_TO_REPRODUCE] = _executes_no_lesson()
        gone = set(skipped)
        config.hook.pytest_deselected(items=skipped)
        items[:] = [item for item in items if item not in gone]
    option = config.getoption("--shard")
    if option is None:
        return
    here = Path(__file__).parent
    by_file: dict[str, list[pytest.Item]] = {}
    for item in items:
        if here in item.path.parents:
            by_file.setdefault(item.path.relative_to(REPO_ROOT).as_posix(), []).append(
                item
            )
    try:
        part, parts = shards.parse(option)
        table = shards.table()
        left_out: list[pytest.Item] = []
        for file, tests in by_file.items():
            names = [getattr(test, "originalname", None) or test.name for test in tests]
            known = [name for name in vars(tests[0].module) if name.startswith("test")]
            numbers = shards.part_of(file, names, table, parts, known)
            left_out += [t for t, n in zip(tests, numbers, strict=True) if n != part]
    except shards.ShardError as error:
        raise pytest.UsageError(str(error)) from None
    if left_out:
        gone = set(left_out)
        config.hook.pytest_deselected(items=left_out)
        items[:] = [item for item in items if item not in gone]


def pytest_terminal_summary(terminalreporter) -> None:
    """The log of the run names the pages the checks of one page ran for, and
    why, and those they skipped (#230, m3); a session that ran none of these
    checks prints nothing."""
    from support import site_checks

    if site_checks.checked_record is None:
        return
    terminalreporter.section("pages of the checks of one page")
    for line in page_selection.summary(site_checks.checked_record):
        terminalreporter.write_line(line)


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """A selective run that executes no lesson has no reproduction to run
    (issue 200): 'pytest -m same_machine' then selects no test, and pytest's
    status 5 (no tests collected) is that valid state, so it passes. Every
    other empty run still fails with 5: a run without a selection, a full
    run, a selection that executes a lesson, and a run that deselected no
    reproduction for the selection."""
    if exitstatus == pytest.ExitCode.NO_TESTS_COLLECTED and session.config.stash.get(
        _NOTHING_TO_REPRODUCE, False
    ):
        print(
            "\nno reproduction to run: this selective run executes no lesson",
            flush=True,
        )
        session.exitstatus = pytest.ExitCode.OK
