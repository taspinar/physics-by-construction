"""The built-site checks report a site that violates them.

Each test writes a small site with one violation and runs the check that
tests/e2e runs on the real site. A clean site passes every check, so a
reported violation comes from the violation and not from the test setup.
"""

import html
import inspect
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from playwright.sync_api import Browser
from support import site_checks
from support.paths import REPO_ROOT
from support.site_checks import Violation
from support.site_server import SiteServer

from pbc.sample import damped_oscillation

BASE_PATH = "/sub-path/"
SITE_URL = "https://example.org" + BASE_PATH

_PAGE = """\
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Test page</title>
{head}
</head>
<body>
<main>
<h1>Test page</h1>
<p>Plain text. <a href="other.html#section">Another page</a>.</p>
{body}
</main>
</body>
</html>
"""

_PIXEL = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
    b"\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0\xf0\x1f\x00"
    b"\x05\x00\x01\xff\x89\x99=\x1d\x00\x00\x00\x00IEND\xaeB`\x82"
)

Site = Callable[..., Path]


@pytest.fixture
def make_site(tmp_path: Path) -> Site:
    """Write a two-page site; ``head`` and ``body`` go into index.html."""

    def make(body: str = "", head: str = "", files: dict[str, str] | None = None):
        site = tmp_path / "site"
        site.mkdir()
        (site / "index.html").write_text(_PAGE.format(head=head, body=body))
        (site / "other.html").write_text(
            _PAGE.format(head="", body='<h2 id="section">Section</h2>')
        )
        (site / "pixel.png").write_bytes(_PIXEL)
        for name, content in (files or {}).items():
            (site / name).parent.mkdir(parents=True, exist_ok=True)
            (site / name).write_text(content)
        return site

    return make


@contextmanager
def served(site: Path) -> Iterator[SiteServer]:
    with SiteServer(site, BASE_PATH) as server:
        yield server


def rules(violations: list[Violation], page: str = "index.html") -> set[str]:
    return {violation.rule for violation in violations if violation.page == page}


def test_a_clean_site_passes_every_check(make_site: Site, browser: Browser):
    site = make_site(
        body='<img src="pixel.png" alt="A single pixel" width="1" height="1">'
    )

    assert site_checks.check_images(site) == []
    assert site_checks.check_static_origins(site, SITE_URL) == []
    assert site_checks.check_internal_links(site, BASE_PATH, SITE_URL) == []
    with served(site) as server:
        assert site_checks.check_requests_and_cookies(browser, server, site) == []
        assert (
            site_checks.check_readable_without_javascript(browser, server, site) == []
        )
        assert site_checks.check_no_horizontal_scroll(browser, server, site) == []
        assert site_checks.check_accessibility(browser, server, site) == []


def test_image_without_alt_text_is_reported(make_site: Site):
    site = make_site(body='<img src="pixel.png" width="1" height="1">')

    assert rules(site_checks.check_images(site)) == {"image-alt"}


def test_image_without_dimensions_is_reported(make_site: Site):
    site = make_site(body='<img src="pixel.png" alt="A single pixel">')

    assert rules(site_checks.check_images(site)) == {"image-dimensions"}


@pytest.mark.parametrize(
    "head, body",
    [
        ("", '<img src="https://cdn.example.com/a.png" alt="A" width="1" height="1">'),
        ('<script src="//cdn.example.com/library.js"></script>', ""),
        ('<link rel="stylesheet" href="https://fonts.example.com/css?family=A">', ""),
        ('<style>@import "https://fonts.example.com/font.css";</style>', ""),
        ("", '<p style="background: url(https://cdn.example.com/b.png)">Text</p>'),
    ],
    ids=["image", "script", "stylesheet", "css-import", "css-url"],
)
def test_resource_on_another_origin_is_reported_in_the_files(
    make_site: Site, head: str, body: str
):
    site = make_site(head=head, body=body)

    assert rules(site_checks.check_static_origins(site, SITE_URL)) == {"other-origin"}


def test_resource_on_another_origin_in_a_stylesheet_is_reported(make_site: Site):
    site = make_site(
        head='<link rel="stylesheet" href="style.css">',
        files={"style.css": '@font-face { src: url("https://fonts.example.com/a") }'},
    )

    assert rules(site_checks.check_static_origins(site, SITE_URL), "style.css") == {
        "other-origin"
    }


def test_link_to_another_site_is_not_a_resource(make_site: Site):
    site = make_site(body='<p><a href="https://example.com/">Elsewhere</a></p>')

    assert site_checks.check_static_origins(site, SITE_URL) == []


def test_request_to_another_origin_is_reported_and_blocked(
    make_site: Site, browser: Browser
):
    # The request is made by a script, so only loading the page can find it.
    site = make_site(
        body="<script>fetch('https://tracker.example.com/collect')"
        ".catch(() => {})</script>"
    )

    with served(site) as server:
        violations = site_checks.check_requests_and_cookies(browser, server, site)

    assert rules(violations) == {"other-origin"}
    assert "tracker.example.com" in violations[0].detail


def test_cookie_is_reported(make_site: Site, browser: Browser):
    site = make_site(body="<script>document.cookie = 'visitor=1'</script>")

    with served(site) as server:
        violations = site_checks.check_requests_and_cookies(browser, server, site)

    assert rules(violations) == {"cookie"}


def test_missing_resource_of_the_site_is_reported(make_site: Site, browser: Browser):
    site = make_site(head='<link rel="stylesheet" href="missing.css">')

    with served(site) as server:
        violations = site_checks.check_requests_and_cookies(browser, server, site)

    assert rules(violations) == {"failed-request"}


@pytest.mark.parametrize(
    "href",
    ["missing.html", "other.html#no-such-anchor", "/other.html"],
    ids=["missing-page", "missing-anchor", "host-root"],
)
def test_broken_internal_link_is_reported(make_site: Site, href: str):
    site = make_site(body=f'<p><a href="{href}">Link</a></p>')

    violations = site_checks.check_internal_links(site, BASE_PATH, SITE_URL)

    assert rules(violations) == {"internal-link"}


def test_content_that_needs_javascript_is_reported(make_site: Site, browser: Browser):
    site = make_site(
        body='<p id="late" style="display: none">Shown by a script.</p>'
        "<script>document.getElementById('late').style.display = 'block'</script>"
    )

    with served(site) as server:
        violations = site_checks.check_readable_without_javascript(
            browser, server, site
        )

    assert rules(violations) == {"no-javascript"}


_EMPTY = '<div id="late"></div>'
_LATE = "document.getElementById('late')"


@pytest.mark.parametrize(
    "body, created",
    [
        (
            f"{_EMPTY}<script>{_LATE}.textContent = 'Written by a script.'</script>",
            "text: Written by a script.",
        ),
        (
            f"{_EMPTY}<script>{_LATE}.innerHTML ="
            """ '<img src="pixel.png" alt="A pixel" width="1" height="1">'</script>""",
            "image: ",
        ),
        (
            f"{_EMPTY}<script>{_LATE}.innerHTML ="
            " '<math><mi>E</mi><mo>=</mo><mi>m</mi></math>'</script>",
            "equation: E=m",
        ),
        (
            f"{_EMPTY}<script>{_LATE}.append(document.createElement('canvas'))"
            "</script>",
            "drawing: canvas",
        ),
        (
            f"{_EMPTY}<script>fetch('pixel.png').then(() => {{"
            f" {_LATE}.textContent = 'Written after a request.' }})</script>",
            "text: Written after a request.",
        ),
        # Declared as an enhancement, but with nothing to read without scripts.
        (
            '<div id="late" data-enhancement></div>'
            f"<script>{_LATE}.textContent = 'No static content.'</script>",
            "text: No static content.",
        ),
        # The declaration itself needs a script.
        (
            f"{_EMPTY}<script>{_LATE}.dataset.enhancement = '';"
            f" {_LATE}.textContent = 'Declared by a script.'</script>",
            "text: Declared by a script.",
        ),
    ],
    ids=[
        "text",
        "image",
        "equation",
        "drawing",
        "after-a-request",
        "enhancement-without-static-content",
        "enhancement-declared-by-a-script",
    ],
)
def test_content_created_by_a_script_is_reported(
    make_site: Site, browser: Browser, body: str, created: str
):
    # The content is not in the page without scripts, so loading it only
    # without scripts cannot find it missing.
    site = make_site(body=body)

    with served(site) as server:
        violations = site_checks.check_readable_without_javascript(
            browser, server, site
        )

    assert rules(violations) == {"no-javascript"}
    assert all("only with scripts: " + created in v.detail for v in violations)
    # Once at desktop and once at phone width.
    assert len(violations) == 2


def test_script_may_add_to_a_declared_enhancement_of_static_content(
    make_site: Site, browser: Browser
):
    site = make_site(
        body='<figure id="figure" data-enhancement>'
        '<img src="pixel.png" alt="A single pixel" width="1" height="1">'
        "</figure>"
        "<script>document.getElementById('figure').append("
        "Object.assign(document.createElement('button'), {textContent: 'Play'}),"
        " document.createElement('canvas'))</script>"
    )

    with served(site) as server:
        violations = site_checks.check_readable_without_javascript(
            browser, server, site
        )

    assert violations == []


def test_page_wider_than_a_phone_or_a_tablet_is_reported(
    make_site: Site, browser: Browser
):
    site = make_site(body='<div style="width: 900px">A wide block.</div>')

    with served(site) as server:
        violations = site_checks.check_no_horizontal_scroll(browser, server, site)

    assert rules(violations) == {"horizontal-scroll"}
    # Wider than a phone and a tablet, with and without scripts; a desktop
    # screen holds it.
    assert sorted(v.detail.split(" on a ")[1][:6] for v in violations) == [
        "320px ",
        "320px ",
        "768px ",
        "768px ",
    ]


def test_image_cut_off_at_phone_width_is_reported(make_site: Site, browser: Browser):
    # The container clips the image, so the page itself does not scroll.
    site = make_site(
        body='<div style="overflow: hidden">'
        '<img src="pixel.png" alt="A wide image" width="900" height="10"></div>'
    )

    with served(site) as server:
        violations = site_checks.check_no_horizontal_scroll(browser, server, site)

    assert rules(violations) == {"image-overflow"}


def test_wcag_violation_is_reported(make_site: Site, browser: Browser):
    site = make_site(
        body='<p style="color: #bbbbbb; background: #ffffff">Low contrast text.</p>'
    )

    with served(site) as server:
        violations = site_checks.check_accessibility(browser, server, site)

    assert rules(violations) == {"wcag:color-contrast"}


# --- Lesson constructs -------------------------------------------------------

_LABELLED = (
    '<div class="not-verified"><div class="not-verified-label">'
    "<p><strong>Not verified.</strong> Nothing checked this.</p></div>"
    "<p>A quoted value.</p></div>"
)


def _listing(source: str, text: str) -> str:
    return (
        f'<div class="sourceCode" data-source="{source}">'
        f"<pre><code>{html.escape(text)}</code></pre></div>"
    )


def test_lesson_constructs_as_the_build_writes_them_pass(
    make_site: Site, browser: Browser
):
    # The text comes from Python's own reading of the function, the check
    # reads the file: two routes to the same source.
    site = make_site(
        body=_LABELLED
        + _listing(
            "pbc.sample:damped_oscillation", inspect.getsource(damped_oscillation)
        )
        + '<section id="assumptions" class="level2"><h2>Assumptions</h2></section>'
    )

    assert site_checks.check_sections(site, "index.html", ["assumptions"]) == []
    with served(site) as server:
        assert site_checks.check_not_verified_labels(browser, server, site) == []
        assert site_checks.check_displayed_code(browser, server, site, REPO_ROOT) == []


def _solution(content: str) -> str:
    return f"<details><summary>Solution to exercise 1</summary>{content}</details>"


def test_labelled_material_inside_a_closed_solution_passes(
    make_site: Site, browser: Browser
):
    # The label is not rendered while the solution is closed; it appears
    # together with the material when the reader opens the solution.
    site = make_site(body=_solution(_solution(_LABELLED)))

    with served(site) as server:
        assert site_checks.check_not_verified_labels(browser, server, site) == []


@pytest.mark.parametrize(
    "body",
    [
        '<div class="not-verified"><p>A quoted value.</p></div>',
        '<p>About <span class="not-verified">9.8</span> metres.</p>',
        _LABELLED.replace('"not-verified-label"', '"not-verified-label" hidden'),
        _LABELLED.replace("Not verified.", "Note."),
        _solution('<div class="not-verified"><p>A quoted value.</p></div>'),
        _solution(
            _LABELLED.replace('"not-verified-label"', '"not-verified-label" hidden')
        ),
        # The material is in the open and its label in a closed element.
        _LABELLED.replace(
            '<div class="not-verified-label">',
            '<details><div class="not-verified-label">',
        ).replace("</p></div><p>", "</p></div></details><p>"),
    ],
    ids=[
        "block",
        "phrase",
        "hidden-label",
        "label-with-other-text",
        "block-in-a-solution",
        "hidden-label-in-a-solution",
        "label-in-a-closed-element",
    ],
)
def test_not_verified_material_without_a_visible_label_is_reported(
    make_site: Site, browser: Browser, body: str
):
    site = make_site(body=body)

    with served(site) as server:
        violations = site_checks.check_not_verified_labels(browser, server, site)

    assert rules(violations) == {"not-verified-label"}


@pytest.mark.parametrize(
    "source, change",
    [
        ("pbc.sample:damped_oscillation", lambda text: text.replace("0.5", "0.25")),
        ("pbc.sample:damped_oscillation", lambda text: text.split('"""')[0]),
        ("pbc.sample:no_such_function", lambda text: text),
        ("json:dumps", lambda text: text),
    ],
    ids=["changed-value", "shortened", "unknown-object", "outside-the-package"],
)
def test_excerpt_that_differs_from_its_source_is_reported(
    make_site: Site, browser: Browser, source: str, change: Callable[[str], str]
):
    site = make_site(
        body=_listing(source, change(inspect.getsource(damped_oscillation)))
    )

    with served(site) as server:
        violations = site_checks.check_displayed_code(browser, server, site, REPO_ROOT)

    assert rules(violations) == {"excerpt"}


@pytest.mark.parametrize(
    "body",
    [
        "<blockquote><p><code>{python} print(position)</code></p></blockquote>",
        "<p>The position is <code>{python} position</code> m.</p>",
    ],
    ids=["cell", "inline-expression"],
)
def test_cell_that_the_build_did_not_execute_is_reported(
    make_site: Site, browser: Browser, body: str
):
    site = make_site(body=body)

    with served(site) as server:
        violations = site_checks.check_displayed_code(browser, server, site, REPO_ROOT)

    assert rules(violations) == {"unexecuted-cell"}


def test_lesson_page_without_a_required_section_is_reported(make_site: Site):
    site = make_site(
        body='<section id="assumptions" class="level2"><h2>Assumptions</h2></section>'
        '<section id="code" class="level3"><h3>Code</h3></section>'
    )

    violations = site_checks.check_sections(site, "index.html", ["assumptions", "code"])

    assert [violation.detail for violation in violations] == [
        "no section with the identifier 'code'"
    ]


def test_lesson_without_a_built_page_is_reported(make_site: Site):
    site = make_site()

    violations = site_checks.check_sections(site, "lessons/x/index.html", ["code"])

    assert rules(violations, "lessons/x/index.html") == {"lesson-page"}


# --- Widgets -------------------------------------------------------------------


def test_a_widget_script_without_requests_or_storage_is_clean(make_site: Site):
    site = make_site(
        files={
            "widgets/w.js": "const ns = 'http://www.w3.org/2000/svg';\n"
            "// A comment with a space after the slashes.\n"
            "document.createElementNS(ns, 'svg');\n"
        }
    )

    assert site_checks.check_widget_sources(site) == []


@pytest.mark.parametrize(
    "source, kind",
    [
        ("fetch('data.json');", "request"),
        ("new XMLHttpRequest();", "request"),
        ("import('./other.js');", "request"),
        ("const url = 'https://example.org/lib.js';", "other origin"),
        ("const url = '//cdn.example.org/lib.js';", "other origin"),
        ("localStorage.setItem('a', 'b');", "browser storage"),
        ("document.cookie = 'a=b';", "browser storage"),
        ("indexedDB.open('db');", "browser storage"),
    ],
)
def test_a_widget_script_that_reaches_out_or_stores_is_reported(
    make_site: Site, source: str, kind: str
):
    site = make_site(files={"widgets/w.js": source})

    violations = site_checks.check_widget_sources(site)

    assert [v.rule for v in violations] == ["widget-source"]
    assert violations[0].detail.startswith(kind)


_WIDGET = (
    '<div id="w" data-enhancement><p>Static text.</p>'
    '<input id="control" type="range" min="0" max="3" value="1"></div>'
    '<script src="widgets/w.js"></script>'
)


@pytest.mark.parametrize(
    "script, written",
    [
        ("localStorage.setItem('k', 'v');", "Storage.setItem(k, v)"),
        ("sessionStorage.setItem('k', 'v');", "Storage.setItem(k, v)"),
        ("localStorage.setItem('k', 'v'); localStorage.clear();", "Storage.setItem"),
        ("document.cookie = 'a=b';", "document.cookie = a=b"),
        ("indexedDB.open('db');", "indexedDB.open(db)"),
        # Only after the reader operates a control.
        (
            "document.getElementById('control').addEventListener("
            "'input', () => localStorage.setItem('k', 'v'));",
            "Storage.setItem(k, v)",
        ),
    ],
    ids=[
        "local-storage",
        "session-storage",
        "written-and-cleared",
        "cookie",
        "indexed-db",
        "on-input",
    ],
)
def test_a_widget_that_stores_something_is_reported(
    make_site: Site, browser: Browser, script: str, written: str
):
    site = make_site(body=_WIDGET, files={"widgets/w.js": script})

    with served(site) as server:
        violations = site_checks.check_widgets_store_nothing(browser, server, site)

    assert "widget-storage" in rules(violations)
    assert any(written in v.detail for v in violations)


def test_storage_the_page_itself_uses_is_not_blamed_on_the_widget(
    make_site: Site, browser: Browser
):
    # The site generator's own scripts keep state; the widget adds none.
    site = make_site(
        body=_WIDGET + "<script>localStorage.setItem('theme', 'dark')</script>",
        files={"widgets/w.js": "document.getElementById('w').dataset.on = '';"},
    )

    with served(site) as server:
        violations = site_checks.check_widgets_store_nothing(browser, server, site)

    assert violations == []


def test_a_widget_that_only_draws_is_not_reported(make_site: Site, browser: Browser):
    site = make_site(
        body=_WIDGET,
        files={
            "widgets/w.js": "document.getElementById('control')"
            ".addEventListener('input', () => { document.getElementById('w')"
            ".dataset.value = 'changed'; });"
        },
    )

    with served(site) as server:
        violations = site_checks.check_widgets_store_nothing(browser, server, site)

    assert violations == []


def test_a_page_without_an_enhancement_is_not_driven(make_site: Site, browser: Browser):
    # A page that writes storage but declares no widget is not this check's
    # business; the generic page checks apply to it.
    site = make_site(body="<script>localStorage.setItem('k', 'v')</script>")

    with served(site) as server:
        violations = site_checks.check_widgets_store_nothing(browser, server, site)

    assert violations == []
