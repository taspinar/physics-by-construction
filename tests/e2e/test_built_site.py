"""Required checks on the built site (architecture, "Built-site checks").

The site is served under the path of its public address, so everything here
also holds when the site sits in a sub-path of its host.
"""

import html
import json
import re
from pathlib import Path

import pytest
import yaml
from playwright.sync_api import Browser, Page
from support import site_checks
from support.paths import SITE_SOURCE
from support.site_checks import DESKTOP, describe
from support.site_server import (
    SiteServer,
    configured_base_path,
    configured_site_url,
)

from pbc.authoring import design


def test_navigation_entries_stay_on_a_phone_screen(
    browser: Browser, server: SiteServer, site_dir: Path
):
    violations = site_checks.check_navigation_fits(browser, server, site_dir)
    assert not violations, describe(violations)


def test_images_have_alt_text_and_dimensions(site_dir: Path):
    violations = site_checks.check_images(site_dir)
    assert not violations, describe(violations)


def test_no_file_refers_to_a_resource_on_another_origin(site_dir: Path):
    violations = site_checks.check_static_origins(
        site_dir, configured_site_url(SITE_SOURCE)
    )
    assert not violations, describe(violations)


def test_internal_links_resolve_under_the_sub_path(site_dir: Path):
    violations = site_checks.check_internal_links(
        site_dir, configured_base_path(SITE_SOURCE), configured_site_url(SITE_SOURCE)
    )
    assert not violations, describe(violations)


def test_pages_request_nothing_from_another_origin_and_set_no_cookie(
    browser: Browser, server: SiteServer, site_dir: Path
):
    violations = site_checks.check_requests_and_cookies(browser, server, site_dir)
    assert not violations, describe(violations)


def test_pages_are_readable_without_javascript(
    browser: Browser, server: SiteServer, site_dir: Path
):
    violations = site_checks.check_readable_without_javascript(
        browser, server, site_dir
    )
    assert not violations, describe(violations)


def test_pages_and_figures_fit_phone_tablet_and_desktop_width(
    browser: Browser, server: SiteServer, site_dir: Path
):
    violations = site_checks.check_no_horizontal_scroll(browser, server, site_dir)
    assert not violations, describe(violations)


def test_wcag_scan_finds_no_violation(
    browser: Browser, server: SiteServer, site_dir: Path
):
    violations = site_checks.check_accessibility(browser, server, site_dir)
    assert not violations, describe(violations)


def test_skip_link_and_navigation_focus_pass_the_keyboard_pass(
    browser: Browser, server: SiteServer, site_dir: Path
):
    violations = site_checks.check_keyboard_navigation(browser, server, site_dir)
    assert not violations, describe(violations)


def test_every_page_loads_within_the_payload_budget(
    browser: Browser, server: SiteServer, site_dir: Path, capsys: pytest.CaptureFixture
):
    sizes = site_checks.measure_payloads(browser, server, site_dir)
    with capsys.disabled():
        print("\nInitial payload by page (bytes):")
        for name, size in sorted(sizes.items()):
            print(f"  {size:>10,}  {name}")
    violations = site_checks.check_payload(sizes)
    assert not violations, describe(violations)


def test_the_site_is_served_from_a_sub_path(server: SiteServer):
    # Guards the tests above: at the root of a host they could not detect a
    # link that breaks on GitHub Pages.
    assert server.base_path not in ("", "/")


@pytest.fixture
def page(browser: Browser) -> Page:
    context = browser.new_context(viewport=DESKTOP)
    yield context.new_page()
    context.close()


_MATH_FONT_LOADED = """
async () => {
  await document.fonts.ready;
  return [...document.fonts].some(
    (font) => font.family.replaceAll('"', "") === "STIX Two Math"
      && font.status === "loaded"
  );
}
"""


def test_home_page_renders_an_equation_as_mathml_in_the_site_font(
    page: Page, server: SiteServer
):
    page.goto(server.url + "index.html", wait_until="load")

    equation = page.locator('math[display="block"]').first
    box = equation.bounding_box()
    assert box is not None and box["width"] > 0 and box["height"] > 0
    assert page.evaluate(_MATH_FONT_LOADED), "the self-hosted math font did not load"
    # MathML is the rendering, not a fallback next to a script renderer.
    assert page.locator(".MathJax, .katex, mjx-container").count() == 0


def test_home_page_links_to_the_repository(page: Page, server: SiteServer):
    repository = yaml.safe_load((SITE_SOURCE / "_quarto.yml").read_text())["website"][
        "repo-url"
    ]
    page.goto(server.url + "index.html", wait_until="load")

    assert page.locator(f'main a[href="{repository}"]').count() >= 1


def test_every_page_states_both_licences_in_the_footer(
    page: Page, server: SiteServer, site_dir: Path
):
    for built in site_checks.html_pages(site_dir):
        page.goto(server.url + built.relative_to(site_dir).as_posix())
        footer = page.locator("footer").inner_text()
        assert "MIT" in footer and "CC BY 4.0" in footer, built.name


def test_rendering_check_page_shows_code_output_figure_and_equations(
    page: Page, server: SiteServer
):
    page.goto(server.url + "rendering-check.html", wait_until="load")

    # Code is highlighted at build time: tokens carry classes with a colour.
    assert page.locator("pre.sourceCode code span[class]").count() > 0
    # The output is what the executed cell printed.
    assert "x = +1.0000 m" in page.locator(".cell-output-stdout").first.inner_text()
    # The figure was produced by the build and loads.
    assert page.locator("img.figure-img").evaluate(
        "image => image.complete && image.naturalWidth > 0"
    )
    # Every equation has a rendered box.
    boxes = page.locator("math").evaluate_all(
        "equations => equations.map(e => e.getBoundingClientRect().width)"
    )
    assert len(boxes) >= 4 and all(width > 0 for width in boxes)


def test_the_built_site_makes_no_request_to_an_llm_provider(site_dir: Path):
    """The site never calls an LLM (architecture, invariant I2)."""
    hosts = ("api.openai.com", "api.anthropic.com", "generativelanguage.googleapis")
    offenders = [
        path.relative_to(site_dir).as_posix()
        for path in site_dir.rglob("*")
        if path.suffix in {".html", ".js", ".css", ".json"}
        and any(host in path.read_text(errors="ignore") for host in hosts)
    ]
    assert not offenders, f"these files refer to an LLM provider: {offenders}"


def test_sample_page_renders_every_design_component_with_its_colours(
    browser: Browser, server: SiteServer
):
    """Runs in the engine chosen with --engine, so that the sample page can be
    checked in Chromium, Firefox, and WebKit."""
    context = browser.new_context(viewport=DESKTOP)
    page = context.new_page()
    page.goto(server.url + "rendering-check.html", wait_until="load")

    for selector in (
        ".learn-box",
        ".assumptions",
        "div.claim",
        ".table-scroll table.result-table",
        ".annotated-excerpt ol",
        ".go-deeper",
        ".exercise.self-check",
        "details.hint",
        ".path-cards .path-card",
        ".prerequisite-graph",
        ".footer-attribution",
        "figcaption .figure-status",
    ):
        assert page.locator(selector).first.is_visible(), selector

    def colours(selector: str) -> tuple[str, str]:
        return tuple(
            page.locator(selector).first.evaluate(
                f"e => getComputedStyle(e).{property}"
            )
            for property in ("color", "backgroundColor")
        )

    def rgb(colour: str) -> str:
        red, green, blue = (int(colour[i : i + 2], 16) for i in (1, 3, 5))
        return f"rgb({red}, {green}, {blue})"

    for kind, selector, labels in (
        ("claim", "span.claim[data-type='{}']", design.CLAIM_LABELS),
        ("status", ".figure-status[data-status='{}']", design.STATUS_LABELS),
    ):
        for name, label in labels.items():
            assert colours(selector.format(name)) == (
                rgb(label.foreground),
                rgb(label.background),
            ), f"{kind} {name}"
    context.close()


def test_search_finds_a_lesson_by_a_term_in_its_body(
    browser: Browser, server: SiteServer, site_dir: Path
):
    violations = site_checks.check_search_finds_a_lesson(
        browser,
        server,
        site_dir,
        "index.html",
        "eccentricity",
        "lessons/mechanics/08-kepler-orbit/index.html",
    )
    assert not violations, describe(violations)


def test_search_control_is_replaced_by_the_learning_path_without_javascript(
    browser: Browser, server: SiteServer, site_dir: Path
):
    violations = site_checks.check_search_falls_back_without_javascript(
        browser, server, site_dir, "path/index.html"
    )
    assert not violations, describe(violations)


def test_the_search_index_is_part_of_the_site_and_within_the_payload_budget(
    site_dir: Path,
):
    index = site_dir / "search.json"
    assert index.is_file(), "the build wrote no search index"
    # A page fetches the index when it is searched, on top of what it loads.
    assert index.stat().st_size < site_checks.SEARCH_INDEX_BUDGET


def test_the_search_index_holds_the_prose_of_a_page_and_not_its_code(
    site_dir: Path,
):
    """site/search-index.py removes code and printed output from the index:
    a reader searches for a concept, and the code would use up the budget."""
    entries = json.loads((site_dir / "search.json").read_text(encoding="utf-8"))
    assert entries, "the search index is empty"
    assert all(entry["text"].strip() for entry in entries)
    pre = re.compile(r"<pre\b[^>]*>(.*?)</pre>", re.DOTALL)
    indexed_code = []
    for entry in entries:
        page = entry["href"].split("#")[0]
        text = "".join(entry["text"].split())
        for block in pre.findall((site_dir / page).read_text(encoding="utf-8")):
            code = "".join(html.unescape(re.sub(r"<[^>]+>", "", block)).split())
            # A short block, such as one command, can also stand in the prose.
            if len(code) >= 80 and code in text:
                indexed_code.append(f"{entry['href']}: {code[:60]}")
    assert not indexed_code, "\n".join(indexed_code[:10])
