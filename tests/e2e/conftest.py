"""The built site, served as GitHub Pages serves it."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from support.paths import BUILT_SITE, SITE_SOURCE
from support.site_server import SiteServer, configured_base_path


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
