"""Options and fixtures shared by the test directories."""

from collections.abc import Iterator

import pytest
from playwright.sync_api import Browser, sync_playwright


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--engine",
        default="chromium",
        choices=["chromium", "firefox", "webkit"],
        help="Browser engine for the built-site checks. Verification uses"
        " chromium; the others need 'playwright install firefox webkit'.",
    )
    parser.addoption(
        "--site-dir",
        default=None,
        help="Built site to check in tests/e2e (default: site/_site).",
    )
    parser.addoption(
        "--repository",
        default=None,
        help="Repository whose lessons tests/lessons checks (default: this one).",
    )


@pytest.fixture(scope="session")
def browser(request: pytest.FixtureRequest) -> Iterator[Browser]:
    with sync_playwright() as playwright:
        engine = getattr(playwright, request.config.getoption("--engine"))
        browser = engine.launch()
        yield browser
        browser.close()
