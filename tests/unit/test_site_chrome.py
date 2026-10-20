"""The shared header of every page (docs/atelier.md, "Components"): the mark,
the primary navigation, and the start link, configured once in
site/_quarto.yml."""

import yaml
from support.paths import SITE_SOURCE

from pbc.authoring.path import LearningPath

CONFIG = yaml.safe_load((SITE_SOURCE / "_quarto.yml").read_text())
NAVBAR = CONFIG["website"]["navbar"]
START_CLASS = "{.pbc-start}"


def entries() -> list[dict]:
    return [*NAVBAR.get("left", []), *NAVBAR.get("right", [])]


def test_the_start_link_goes_to_the_first_lesson_of_the_learning_path():
    first = LearningPath.read(SITE_SOURCE).lessons[0]
    starts = [entry for entry in entries() if START_CLASS in entry.get("text", "")]

    assert len(starts) == 1, "the header has exactly one start link"
    assert starts[0]["text"] == f"[Start the course]{START_CLASS}"
    assert starts[0]["href"] == first.page


def test_the_start_link_is_the_last_entry_of_the_header():
    assert START_CLASS in NAVBAR["right"][-1]["text"]


def test_the_header_carries_the_mark_with_the_site_title_as_its_name():
    assert NAVBAR["logo"] == "assets/mark.svg"
    assert NAVBAR["logo-alt"] == CONFIG["website"]["title"]
    assert (SITE_SOURCE / NAVBAR["logo"]).is_file()


def test_the_primary_navigation_names_every_section_once():
    texts = [entry["text"] for entry in entries()]
    assert texts[:-1] == [
        "Home",
        "Learning path",
        "Glossary",
        "Evidence",
        "About",
        "Set up",
        "Contribute",
        "Source",
    ]
    assert NAVBAR["collapse"] is False
