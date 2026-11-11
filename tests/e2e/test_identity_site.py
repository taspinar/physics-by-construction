"""The built site carries the identity text where F57 says it does."""

from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page
from support import site_checks
from support.site_checks import DESKTOP
from support.site_server import SiteServer

from pbc.authoring import identity


@pytest.fixture
def page(browser: Browser) -> Page:
    context = browser.new_context(viewport=DESKTOP)
    yield context.new_page()
    context.close()


ABOUT_LINK = "about.html#creator-and-jidai"


def _content(page: Page) -> str:
    return page.locator("#quarto-document-content").inner_text()


def test_about_carries_the_sentence_and_the_footer_of_both_the_line(
    page: Page, server: SiteServer
):
    """About carries the canonical sentence; Home's introduction does not
    repeat it (the owner's copy of Issue #481) and links to About; the
    footer of both carries the line."""
    for name in ("index.html", "about.html"):
        page.goto(server.url + name)
        carries = identity.description() in _content(page)
        assert carries is (name == "about.html"), name
        assert identity.footer_line() in page.locator("footer").inner_text(), name
    page.goto(server.url + "index.html")
    assert "by JIDAI, created by Ahmet Taspinar" not in _content(page)


def test_home_has_one_attribution_link_and_it_leads_to_the_about_page(
    page: Page, server: SiteServer
):
    page.goto(server.url + "index.html")
    links = page.locator(
        '#quarto-document-content a[href*="#creator-and-jidai"], '
        '#quarto-document-content a[href*="jidai.nl"]'
    )
    assert links.count() == 1
    assert (links.first.get_attribute("href") or "").endswith(ABOUT_LINK)
    assert page.locator("#creator-and-jidai").count() == 0


def test_about_has_the_creator_section_and_the_footer_links_to_jidai_once(
    page: Page, server: SiteServer
):
    page.goto(server.url + "about.html")
    assert page.locator("#creator-and-jidai").count() == 1
    footer = page.locator("footer a[href*='jidai.nl']")
    assert footer.count() == 1


def test_no_page_repeats_the_footer_line_in_its_content(
    page: Page, server: SiteServer, site_dir: Path
):
    for html in site_checks.html_pages(site_dir):
        page.goto(server.url + html.relative_to(site_dir).as_posix())
        assert identity.footer_line() not in _content(page), html.name
        assert "PBC-ATTRIBUTION" not in html.read_text(encoding="utf-8"), html.name
