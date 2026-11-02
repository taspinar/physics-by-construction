"""The built page "How we verify the science" (F134, ADR 021 decision 5): the
four claim types under their labels, three worked examples whose links reach
one element each, in the lesson and in the Evidence map, and the way from the
footer to the page and from the page to the Evidence map. Read without
JavaScript."""

import pytest
from playwright.sync_api import Browser, BrowserContext
from support.paths import SITE_SOURCE
from support.site_checks import DESKTOP
from support.site_server import SiteServer

from pbc.authoring.design import CLAIM_TYPES
from pbc.authoring.verify import verify_page

PAGE = "verify.html"
WORKED = verify_page(site=SITE_SOURCE)


@pytest.fixture
def context(browser: Browser):
    context = browser.new_context(viewport=DESKTOP, java_script_enabled=False)
    yield context
    context.close()


def test_the_page_names_the_four_types_with_their_labels(
    context: BrowserContext, server: SiteServer
):
    page = context.new_page()
    page.goto(server.url + PAGE)
    labels = page.locator("main section#claim-types .claim").evaluate_all(
        "ls => ls.map(l => l.dataset.type)"
    )
    assert labels == list(CLAIM_TYPES)


def test_each_example_links_reach_one_element(
    context: BrowserContext, server: SiteServer
):
    page = context.new_page()
    page.goto(server.url + PAGE)
    examples = page.locator("main .verify-example")
    assert examples.count() == len(WORKED.examples) == 3
    target = context.new_page()
    for box, worked in zip(examples.all(), WORKED.examples, strict=True):
        links = box.locator("a").evaluate_all("as => as.map(a => a.href)")
        lesson = server.url + worked.lesson.page.removesuffix(".qmd") + ".html"
        claim = f"{lesson}#{worked.claim.anchor}"
        row = f"{server.url}evidence.html#{worked.claim.row}"
        assert claim in links and row in links
        for link in links:
            if not link.startswith(server.url):
                continue
            address, _, fragment = link.partition("#")
            target.goto(address)
            assert target.locator(f"[id='{fragment}']").count() == 1, link
        # The row is the row of this claim.
        target.goto(row)
        anchor = target.locator(f"[id='{worked.claim.row}']")
        cell_link = anchor.locator("xpath=ancestor::tr[1]//a").first
        assert cell_link.get_attribute("href").endswith(worked.claim.anchor)


def test_the_footer_leads_here_and_the_page_to_the_evidence_map(
    context: BrowserContext, server: SiteServer
):
    page = context.new_page()
    page.goto(server.url + "index.html")
    footer = page.locator("footer a", has_text="Scientific evidence")
    assert footer.evaluate("a => a.href") == server.url + PAGE
    page.goto(server.url + PAGE)
    links = page.locator("main a").evaluate_all("as => as.map(a => a.href)")
    assert server.url + "evidence.html" in links
    page.goto(server.url + "evidence.html")
    back = page.locator("main a", has_text="How we verify the science")
    assert back.evaluate("a => a.href") == server.url + PAGE
