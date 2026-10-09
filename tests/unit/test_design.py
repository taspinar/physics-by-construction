"""The colours of the site are defined once, agree with the stylesheet, and
have the contrast the accessibility criteria ask for."""

import re

import pytest
from support.paths import SITE_SOURCE

from pbc.authoring import CLAIM_TYPES, FIGURE_COLOURS, FIGURE_STATUSES
from pbc.authoring.design import (
    CLAIM_LABELS,
    STATUS_LABELS,
    colour_pairs,
    contrast_ratio,
    custom_properties,
)

STYLESHEET = (SITE_SOURCE / "assets" / "site.css").read_text()
ROOT_BLOCK = re.search(r":root \{(.*?)\n\}", STYLESHEET, re.DOTALL)
assert ROOT_BLOCK, "site.css has no :root block of tokens"


def declared() -> dict[str, str]:
    return dict(re.findall(r"(--pbc-[\w-]+):\s*([^;]+);", ROOT_BLOCK.group(1)))


def test_contrast_ratio_matches_the_wcag_extremes_and_a_known_pair():
    assert contrast_ratio("#000000", "#ffffff") == pytest.approx(21.0)
    assert contrast_ratio("#ffffff", "#ffffff") == pytest.approx(1.0)
    # The grey #767676 is the lightest grey with 4.5:1 on white.
    assert contrast_ratio("#767676", "#ffffff") == pytest.approx(4.54, abs=0.01)


@pytest.mark.parametrize(
    ("name", "colour", "background", "minimum"),
    colour_pairs(),
    ids=[pair[0] for pair in colour_pairs()],
)
def test_every_pair_has_enough_contrast(name, colour, background, minimum):
    ratio = contrast_ratio(colour, background)
    assert ratio >= minimum, f"{name}: {colour} on {background} is {ratio:.2f}:1"


def test_a_label_exists_for_every_claim_type_and_figure_status():
    assert set(CLAIM_LABELS) == set(CLAIM_TYPES)
    assert set(STATUS_LABELS) == set(FIGURE_STATUSES)
    assert len(CLAIM_TYPES) == 4 and len(FIGURE_STATUSES) == 5


def test_the_figure_colours_are_distinct():
    assert len(set(FIGURE_COLOURS)) == len(FIGURE_COLOURS) >= 6


def test_the_stylesheet_declares_exactly_the_colours_of_the_module():
    colours = {
        name: value for name, value in declared().items() if value.startswith("#")
    }
    assert colours == custom_properties()


def hex_colours_in_declarations(css: str) -> list[str]:
    return re.findall(r":[^;{}]*?(#[0-9a-fA-F]{3,8})\b[^;{}]*;", css)


def test_the_stylesheet_uses_a_colour_only_through_a_token():
    assert hex_colours_in_declarations("a { color: #123456; }") == ["#123456"]
    outside = STYLESHEET.replace(ROOT_BLOCK.group(0), "")
    assert hex_colours_in_declarations(outside) == []


def test_every_token_the_stylesheet_uses_is_declared():
    used = set(re.findall(r"var\((--pbc-[\w-]+)\)", STYLESHEET))
    assert used <= set(declared()), sorted(used - set(declared()))
