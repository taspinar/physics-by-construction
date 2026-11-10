"""The shared header and footer of every page (docs/atelier.md, "Components"):
the mark, the primary navigation of four items with the start link, and the
footer with the secondary pages, configured once in site/_quarto.yml; and
the post-render script that gives the header its compact form on a narrow
screen (site/navigation.py, F158 round 2): the title's two forms and the
native menu around the four items, open in the HTML."""

import importlib.util
import re

import pytest
import yaml
from support.paths import SITE_SOURCE

from pbc.authoring.path import LearningPath

CONFIG = yaml.safe_load((SITE_SOURCE / "_quarto.yml").read_text())
NAVBAR = CONFIG["website"]["navbar"]
FOOTER = CONFIG["website"]["page-footer"]
START_CLASS = "{.pbc-start}"
REPOSITORY = CONFIG["website"]["repo-url"]
MARKDOWN_LINK = re.compile(r"\]\(([^)]+)\)")


def entries() -> list[dict]:
    return [*NAVBAR.get("left", []), *NAVBAR.get("right", [])]


def test_the_start_link_goes_to_the_first_lesson_of_the_learning_path():
    first = LearningPath.read(SITE_SOURCE).lessons[0]
    starts = [entry for entry in entries() if START_CLASS in entry.get("text", "")]

    assert len(starts) == 1, "the header has exactly one start link"
    assert starts[0]["text"] == f"[Start learning]{START_CLASS}"
    assert starts[0]["href"] == first.page


def test_the_start_link_is_the_last_entry_of_the_header():
    assert START_CLASS in NAVBAR["right"][-1]["text"]


def test_the_header_carries_the_mark_with_the_site_title_as_its_name():
    assert NAVBAR["logo"] == "assets/mark.svg"
    assert NAVBAR["logo-alt"] == CONFIG["website"]["title"]
    assert (SITE_SOURCE / NAVBAR["logo"]).is_file()


def test_the_primary_navigation_has_exactly_four_items():
    assert [(entry["text"], entry["href"]) for entry in NAVBAR["left"]] == [
        ("Home", "index.qmd"),
        ("Course Atlas", "path/index.qmd"),
        ("About", "about.qmd"),
    ]
    assert len(NAVBAR["right"]) == 1  # the start link alone
    assert NAVBAR["collapse"] is False


def test_the_footer_carries_the_secondary_pages_and_the_source():
    assert [(entry["text"], entry["href"]) for entry in FOOTER["right"]] == [
        ("Run the code", "reproduce.qmd"),
        ("Glossary", "glossary.qmd"),
        ("Scientific evidence", "verify.qmd"),
        ("For educators", "educators.qmd"),
        ("Contribute", "contribute.qmd"),
        ("Source", REPOSITORY),
    ]


def test_no_link_of_the_header_and_the_footer_appears_twice():
    hrefs = [entry["href"] for entry in [*entries(), *FOOTER["right"]]]
    hrefs += MARKDOWN_LINK.findall(FOOTER["center"])
    assert len(hrefs) == len(set(hrefs)), hrefs


def test_every_page_of_the_header_and_the_footer_exists():
    for entry in [*entries(), *FOOTER["right"]]:
        if not entry["href"].startswith("https://"):
            assert (SITE_SOURCE / entry["href"]).is_file(), entry["href"]


def _mark_module():
    spec = importlib.util.spec_from_file_location("mark", SITE_SOURCE / "mark.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LOGOS = "".join(
    f'<img src="a/mark.svg" alt="Physics by Construction" class="navbar-logo {mode}">'
    for mode in ("light-content", "dark-content")
)
FIGURE = '<img src="figure.png" alt="A figure" width="640" height="480">'


def test_the_post_render_script_sizes_the_mark_and_only_the_mark(
    tmp_path, monkeypatch: pytest.MonkeyPatch
):
    mark = _mark_module()
    page = tmp_path / "lessons" / "x" / "index.html"
    page.parent.mkdir(parents=True)
    page.write_text(f'<nav>{LOGOS}</nav>{FIGURE}<img src="b.png" alt="b">')
    monkeypatch.setenv("QUARTO_PROJECT_OUTPUT_DIR", str(tmp_path))

    mark.main()

    text = page.read_text()
    size = f'width="{mark.SIZE}" height="{mark.SIZE}"'
    assert text.count(size) == 2  # the light and the dark mark
    assert text.count("<img ") == 4
    assert FIGURE in text  # an image with a size keeps it
    assert '<img src="b.png" alt="b">' in text  # another image is not touched


def test_the_post_render_script_is_idempotent(
    tmp_path, monkeypatch: pytest.MonkeyPatch
):
    mark = _mark_module()
    page = tmp_path / "index.html"
    page.write_text(f"<nav>{LOGOS}</nav>")
    monkeypatch.setenv("QUARTO_PROJECT_OUTPUT_DIR", str(tmp_path))

    mark.main()
    once = page.read_text()
    mark.main()

    assert page.read_text() == once
    assert once.count("width=") == 2


# --- The compact header (navigation.py) ----------------------------------------


def _navigation_module():
    spec = importlib.util.spec_from_file_location(
        "navigation", SITE_SOURCE / "navigation.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HEADER = (
    '<nav class="navbar navbar-expand"><div class="navbar-container container-fluid">'
    '<div class="navbar-brand-container mx-auto">'
    '<a class="navbar-brand" href="./index.html">'
    '<span class="navbar-title">Physics by Construction</span></a></div>\n'
    '          <ul class="navbar-nav navbar-nav-scroll me-auto">\n'
    '  <li class="nav-item"><a class="nav-link" href="./index.html">Home</a></li>\n'
    '  <li class="nav-item"><a class="nav-link" href="./about.html">About</a></li>\n'
    "</ul>\n"
    '          <ul class="navbar-nav navbar-nav-scroll ms-auto">\n'
    '  <li class="nav-item"><a class="nav-link" href="./l/index.html">'
    '<span class="pbc-start">Start learning</span></a></li>\n'
    "</ul>\n"
    '          <div class="quarto-navbar-tools">\n</div>\n'
    '            <div id="quarto-search" data-enhancement class="" title="Search">'
    '<noscript><a class="search-fallback" href="path/index.html">Find a lesson</a>'
    "</noscript></div>\n      </div></nav>"
)
LISTS = re.compile(r'<ul class="navbar-nav[^"]*">.*?</ul>', re.S)


def test_the_compact_header_has_the_two_title_forms_and_the_menu_after_the_search():
    navigation = _navigation_module()
    page = navigation.compact(HEADER, depth=2)
    assert navigation.short_form("Physics by Construction") == "PBC"
    assert (
        '<span class="navbar-title"><span class="pbc-title-full">Physics by'
        ' Construction</span><span class="pbc-title-short" aria-hidden="true">'
        "PBC</span></span>"
    ) in page
    # The two lists, unchanged, inside the open menu after the search; the
    # toggle is named and holds only the icon; the script follows the menu.
    menu = re.search(
        r'<details class="pbc-menu" id="pbc-menu" open>(.*?)</details>', page, re.S
    )
    assert menu is not None
    assert page.index('id="quarto-search"') < menu.start()
    assert menu.group(1).startswith(
        '<summary class="pbc-menu-toggle" role="button" aria-label="Menu"'
        ' aria-expanded="true"><span class="pbc-menu-icon"></span></summary>'
        '<div class="pbc-menu-panel">'
    )
    assert LISTS.findall(page) == LISTS.findall(HEADER)
    assert page.count("navbar-nav navbar-nav-scroll") == 2
    assert page.endswith(
        '</details><script src="../../learner/menu.js"></script>\n      </div></nav>'
    )
    # Every link is kept, once (the entries now follow the search's).
    assert sorted(re.findall(r"<a [^>]*>", page)) == sorted(
        re.findall(r"<a [^>]*>", HEADER)
    )


def test_the_compact_header_is_idempotent_and_leaves_a_page_without_a_header():
    navigation = _navigation_module()
    once = navigation.compact(HEADER, depth=0)
    assert navigation.compact(once, depth=0) == once
    assert once.count('class="pbc-menu"') == 1 and once.count('id="pbc-menu"') == 1
    assert once.count("<script") == 1
    assert navigation.compact("<p>no header</p>", depth=0) == "<p>no header</p>"


def test_the_post_render_script_rewrites_every_built_page(
    tmp_path, monkeypatch: pytest.MonkeyPatch
):
    navigation = _navigation_module()
    top = tmp_path / "index.html"
    deep = tmp_path / "lessons" / "x" / "index.html"
    deep.parent.mkdir(parents=True)
    top.write_text(HEADER)
    deep.write_text(HEADER)
    monkeypatch.setenv("QUARTO_PROJECT_OUTPUT_DIR", str(tmp_path))

    navigation.main()

    assert '<script src="learner/menu.js"></script>' in top.read_text()
    assert '<script src="../../learner/menu.js"></script>' in deep.read_text()
    assert (SITE_SOURCE / navigation.SCRIPT).is_file()
    before = deep.read_text()
    navigation.main()
    assert deep.read_text() == before
