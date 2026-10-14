"""The built site, served as GitHub Pages serves it."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from support import shards
from support.lesson_shard import executed_lessons, idle_shard
from support.paths import BUILT_SITE, REPO_ROOT, SITE_SOURCE
from support.site_server import SiteServer, configured_base_path


@pytest.fixture(scope="session")
def site_dir(request: pytest.FixtureRequest) -> Path:
    directory = Path(request.config.getoption("--site-dir") or BUILT_SITE)
    # A lesson shard with nothing to execute renders no page: there is no site
    # to check, and its part holds the entries it restored.
    if not idle_shard() and not (directory / "index.html").is_file():
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
    chosen = executed_lessons()
    if chosen is None:
        return []
    executed = {
        f"{Path(lesson).relative_to('site').as_posix()}/index.html" for lesson in chosen
    }
    return [
        item
        for item in items
        if item.get_closest_marker("same_machine") is not None
        and getattr(item, "callspec", None) is not None
        and "lesson" in item.callspec.params
        and item.callspec.params["lesson"] not in executed
    ]


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Keep what this run is to check: the reproduction of the lessons it
    executed, and the part of each test file that --shard asks for."""
    skipped = _reproductions_of_unchanged_lessons(items)
    if skipped:
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
