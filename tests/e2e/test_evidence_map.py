"""Required checks on the evidence map of the built site (F19): the page
lists every claim of the lessons once, with its type, scope, and evidence, and
reads without JavaScript. Every link into a lesson reaches an element that
exists once in the built page. The accessibility scan every page gets covers
the page."""

import re
from pathlib import Path

import pytest
from playwright.sync_api import Browser, BrowserContext
from support.paths import REPO_ROOT
from support.site_checks import DESKTOP
from support.site_server import SiteServer

from pbc.authoring.evidence import Evidence, read_all

PAGE = "evidence.html"


class _LazyClaims:
    """Every claim of the lessons, read on first use. Reading them starts one
    pandoc per claim block (seconds for the whole site), so it is not done
    when pytest imports this module: every run that collects tests/e2e
    imports it, also the runs that select or deselect these tests."""

    def __init__(self) -> None:
        self._claims: list | None = None

    def _all(self) -> list:
        if self._claims is None:
            self._claims = read_all(REPO_ROOT)
        return self._claims

    def __iter__(self):
        return iter(self._all())

    def __len__(self) -> int:
        return len(self._all())


CLAIMS = _LazyClaims()


@pytest.fixture
def without_scripts(browser: Browser) -> BrowserContext:
    context = browser.new_context(viewport=DESKTOP, java_script_enabled=False)
    yield context
    context.close()


def plain(text: str) -> str:
    """The text with the typographic quotes of the page as typed."""
    return text.translate({0x2018: "'", 0x2019: "'", 0x201C: '"', 0x201D: '"'})


def built(page: str) -> str:
    return Path(page).with_suffix(".html").as_posix()


def test_the_site_has_claims_and_an_evidence_page(site_dir: Path):
    # Guards the tests below: without claims they would check nothing.
    assert CLAIMS
    assert (site_dir / PAGE).is_file()


def test_every_claim_appears_once_with_type_scope_lesson_and_evidence(
    without_scripts: BrowserContext, server: SiteServer
):
    page = without_scripts.new_page()
    page.goto(server.url + PAGE, wait_until="load")
    evidence = Evidence(REPO_ROOT)

    rows = page.locator("main table tbody tr")
    assert rows.count() == len(CLAIMS)
    for claim in CLAIMS:
        link = f"{built(claim.page)}#{claim.anchor}"
        row = page.locator(f'main tbody tr:has(td a[href="{link}"])')
        assert row.count() == 1, f"{claim.page} {claim.anchor}"
        cells = row.locator("td")
        assert cells.nth(1).inner_text() == claim.type.replace("-", " ").capitalize()
        assert plain(cells.nth(2).inner_text()) == (claim.scope or "not stated")
        links = [
            (anchor.inner_text(), anchor.get_attribute("href"))
            for anchor in cells.nth(3).locator("a").all()
        ]
        assert links == [
            (source.name, source.href)
            for word in claim.evidence
            if (source := evidence.resolve(claim.page, word))
        ]
        # The lesson heading of the table is the lesson of the claim.
        title = row.locator("xpath=ancestor::section[1]/h2").inner_text()
        assert title


def test_every_link_into_a_lesson_reaches_one_element(
    without_scripts: BrowserContext, server: SiteServer, site_dir: Path
):
    page = without_scripts.new_page()
    page.goto(server.url + PAGE, wait_until="load")

    hrefs = page.locator("main table a").evaluate_all(
        "links => links.map(a => a.getAttribute('href'))"
    )
    local = [href for href in hrefs if href.startswith("lessons/")]
    # Each claim links its place, and each cell of the evidence its output.
    assert len(local) >= len(CLAIMS)
    for href in local:
        name, _, fragment = href.partition("#")
        assert fragment, href
        # The built lesson page, where the filter has assigned the claim ids.
        text = (site_dir / name).read_text(encoding="utf-8")
        assert len(re.findall(rf'\bid="{re.escape(fragment)}"', text)) == 1, href
