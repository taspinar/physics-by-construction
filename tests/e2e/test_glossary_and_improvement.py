"""The glossary in context and "Suggest an improvement" on the built site (F135).

Without scripts, a lesson's "Before you begin" opens the definition of each
glossary entry it assumes, and its last section ends with the three links to
the issue forms, each with the lesson's public address filled in. CI cannot
reach github.com: that GitHub shows the address in the form is the one
manual check of F135; here the links are checked against the forms.
"""

from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import pytest
import yaml
from playwright.sync_api import Browser, BrowserContext
from support.paths import REPO_ROOT, SITE_SOURCE
from support.site_checks import DESKTOP
from support.site_server import SiteServer, configured_site_url

from pbc.authoring import LearningPath
from pbc.authoring.glossary import Glossary
from pbc.authoring.improvement import FORMS, LABEL, PAGE_FIELD, TEMPLATE_DIRECTORY

LESSON_PATH = LearningPath.read(SITE_SOURCE)
GLOSSARY = Glossary.read(SITE_SOURCE)
SITE_URL = configured_site_url(SITE_SOURCE)
TEMPLATES = REPO_ROOT / TEMPLATE_DIRECTORY


def _built(page: str) -> str:
    return Path(page).with_suffix(".html").as_posix()


@pytest.fixture
def without_scripts(browser: Browser) -> BrowserContext:
    context = browser.new_context(viewport=DESKTOP, java_script_enabled=False)
    yield context
    context.close()


def _template_ids(name: str) -> set[str]:
    data = yaml.safe_load((TEMPLATES / name).read_text(encoding="utf-8"))
    return {str(field["id"]) for field in data["body"] if "id" in field}


def test_every_lesson_ends_with_the_prefilled_improvement_links(
    without_scripts: BrowserContext, server: SiteServer
):
    assert LESSON_PATH.lessons
    page = without_scripts.new_page()
    for lesson in LESSON_PATH.lessons:
        built = _built(lesson.page)
        page.goto(server.url + built, wait_until="load")
        line = page.locator("#reproduce-this .suggest-improvement")
        assert line.count() == 1, built
        # The last line of the last section of the page.
        assert line.evaluate("e => e.closest('.reproduce').lastElementChild === e"), (
            built
        )
        assert line.inner_text().startswith(LABEL), built
        hrefs = line.locator("a").evaluate_all("links => links.map(a => a.href)")
        assert len(hrefs) == len(FORMS), built
        for href, form in zip(hrefs, FORMS, strict=True):
            query = dict(parse_qsl(urlsplit(href).query))
            assert query.pop("template") == f"{form.name}.yml", built
            assert query == {PAGE_FIELD: SITE_URL + built}, built
            assert set(query) <= _template_ids(f"{form.name}.yml"), built


def test_before_you_begin_opens_each_definition_without_scripts(
    without_scripts: BrowserContext, server: SiteServer
):
    lessons = [lesson for lesson in LESSON_PATH.lessons if lesson.outside]
    assert lessons
    page = without_scripts.new_page()
    for lesson in lessons[:3]:
        page.goto(server.url + _built(lesson.page), wait_until="load")
        # "Before you begin" is in the header's closed disclosure (F174).
        page.locator(".lesson-header-details > summary").click()
        disclosures = page.locator(".lesson-header .glossary-definition")
        entries = []
        for text in lesson.outside:
            entry = GLOSSARY.entry(text)
            if entry is not None and entry not in entries:
                entries.append(entry)
        assert disclosures.count() == len(entries), lesson.id
        for index, entry in enumerate(entries):
            disclosure = disclosures.nth(index)
            body = disclosure.locator("p")
            assert not body.is_visible()
            disclosure.locator("summary").click()
            assert body.is_visible()
            # The build turns apostrophes into typographic ones.
            shown = " ".join(body.inner_text().split()).replace("\u2019", "'")
            assert shown == entry.definition, lesson.id


def test_the_contribute_page_opens_with_the_three_forms_and_says_what_they_need(
    without_scripts: BrowserContext, server: SiteServer
):
    page = without_scripts.new_page()
    page.goto(server.url + "contribute.html", wait_until="load")
    main = page.locator("main")

    text = " ".join(main.inner_text().split())
    assert "You need a GitHub account" in text
    assert "issues are public" in text
    first = main.locator("ul").first
    hrefs = first.locator("a").evaluate_all("links => links.map(a => a.href)")
    assert [dict(parse_qsl(urlsplit(h).query)) for h in hrefs] == [
        {"template": f"{form.name}.yml"} for form in FORMS
    ]
    # The links come before the first section.
    assert first.evaluate(
        "ul => !!(ul.compareDocumentPosition(document.querySelector('main h2'))"
        " & Node.DOCUMENT_POSITION_FOLLOWING)"
    )
