"""Required checks on the built site (architecture, "Built-site checks").

The site is served under the path of its public address, so everything here
also holds when the site sits in a sub-path of its host.
"""

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


def test_pages_do_not_scroll_sideways_at_phone_width(
    browser: Browser, server: SiteServer, site_dir: Path
):
    violations = site_checks.check_no_horizontal_scroll(browser, server, site_dir)
    assert not violations, describe(violations)


def test_wcag_scan_finds_no_violation(
    browser: Browser, server: SiteServer, site_dir: Path
):
    violations = site_checks.check_accessibility(browser, server, site_dir)
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
    for html in site_checks.html_pages(site_dir):
        page.goto(server.url + html.relative_to(site_dir).as_posix())
        footer = page.locator("footer").inner_text()
        assert "MIT" in footer and "CC BY 4.0" in footer, html.name


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
