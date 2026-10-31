"""The shared header and footer of every page (docs/atelier.md, "Components"):
the mark, the primary navigation of four items with the start link, and the
footer with the secondary pages, configured once in site/_quarto.yml."""

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
        ("Scientific evidence", "evidence.qmd"),
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
