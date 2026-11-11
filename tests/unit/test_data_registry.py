"""The lists a new dataset used to extend by hand are derived from the cards
(Issue #456): the reference modules, and the generated regions of the two
READMEs, which the dataset check compares with the cards.
"""

import copy
import shutil
import sys
import types
from pathlib import Path

import pytest
import yaml

from pbc.data import REGISTRY_DIR, REPO_ROOT
from pbc.data.card import load_card, load_cards, validate_card
from pbc.data.registry import (
    DOCS_README,
    SURVEYED,
    TOOLS_README,
    _row,
    check_readmes,
    check_reference_modules,
    conversion_table,
    go_cards,
    later_table,
    reference_modules,
    region_text,
    survey_table,
    write_readmes,
)

GO = go_cards()


def test_every_go_card_names_a_module_that_imports_and_makes_a_figure():
    assert set(reference_modules()) == set(GO)
    assert check_reference_modules(GO) == []
    assert len(GO) >= 19


def go_card(**changes) -> dict:
    card = copy.deepcopy(GO["npl-onwafer-sparameters"])
    card.update(changes)
    return card


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ({"reference_module": None}, "reference_module"),
        ({"reference_module": "Not-A-Module"}, "reference_module"),
        ({"reference_figure": None}, "reference_figure"),
        ({"reference_figure": {"status": "raw", "residuals": False}}, "status"),
        ({"reference_figure": {"status": "processed", "residuals": "no"}}, "residuals"),
        ({"listing": None}, "listing"),
        ({"listing": {"name": "x"}}, "listing.kind"),
        ({"conversions": [{"script": "tools/datasets/x.py"}]}, "conversions[0].input"),
    ],
)
def test_a_go_card_without_the_fields_of_the_lists_is_invalid(change, expected):
    problems = validate_card(go_card(**change), "npl-onwafer-sparameters")
    assert any(expected in p for p in problems), problems


def test_a_survey_card_needs_none_of_them():
    card = load_card(REGISTRY_DIR / "gaia-dr3-astrometry.yaml")
    assert "reference_module" not in card and "listing" not in card
    assert validate_card(card, card["id"]) == []


def test_a_module_that_does_not_import_or_has_no_make_figure_is_reported(monkeypatch):
    broken = {"x": go_card(id="x", reference_module="no_such_module_456")}
    problems = check_reference_modules(broken)
    assert len(problems) == 1 and "does not import" in problems[0]
    stub = types.ModuleType("pbc.data.reference.stub_without_figure")
    monkeypatch.setitem(sys.modules, stub.__name__, stub)
    bare = {"x": go_card(id="x", reference_module="stub_without_figure")}
    problems = check_reference_modules(bare)
    assert len(problems) == 1 and "make_figure" in problems[0]
    stub.make_figure = lambda data_dir: None
    assert check_reference_modules(bare) == []


def test_the_tables_are_in_alphabetical_order_of_the_id_and_name_every_card():
    cards = GO
    all_cards = _all_cards()
    # The order is checked against the card ids, never against the dossier link:
    # a card without a dossier has no link to read an id from.
    later_ids = sorted(set(all_cards) - SURVEYED)
    later = later_table(all_cards).splitlines()[2:]
    assert later == [_row(all_cards[name]) for name in later_ids]
    surveyed = [
        n
        for n in sorted(SURVEYED)
        if all_cards[n]["decision"]["value"] != "survey-only"
    ]
    survey = survey_table(all_cards).splitlines()[2:]
    assert survey[:-1] == [_row(all_cards[name]) for name in surveyed]
    others = len(
        [n for n in SURVEYED if all_cards[n]["decision"]["value"] == "survey-only"]
    )
    assert survey[-1].startswith(f"| {others} others |")
    assert len(surveyed) + others == len(SURVEYED) == 25
    rows = conversion_table(cards).splitlines()[2:]
    datasets = [row.split("|")[2].strip().strip("`") for row in rows]
    assert datasets == sorted(datasets)
    assert len(rows) == sum(len(c.get("conversions") or []) for c in cards.values())


def _all_cards() -> dict:
    return load_cards(REGISTRY_DIR)


def test_the_committed_readmes_equal_the_cards():
    assert check_readmes(REPO_ROOT) == []


@pytest.fixture
def tree(tmp_path) -> Path:
    """A copy of the registry and the two READMEs, nothing else."""
    shutil.copytree(REGISTRY_DIR, tmp_path / "data/registry")
    for relative in (DOCS_README, TOOLS_README):
        (tmp_path / relative).parent.mkdir(parents=True)
        shutil.copy(REPO_ROOT / relative, tmp_path / relative)
    return tmp_path


def test_a_region_that_differs_from_the_cards_is_reported_and_write_repairs_it(tree):
    assert check_readmes(tree) == []
    readme = tree / DOCS_README
    text = readme.read_text()
    row = next(line for line in text.splitlines() if "[gw150914-strain]" in line)
    readme.write_text(text.replace(row, row.replace("time series", "edited by hand")))
    problems = check_readmes(tree)
    assert len(problems) == 1 and "'survey-table'" in problems[0]
    assert write_readmes(tree) == [readme]
    assert check_readmes(tree) == []
    assert region_text(readme.read_text(), "survey-table") == survey_table(_all_cards())


def test_a_missing_region_and_a_missing_readme_are_reported(tree):
    tools = tree / TOOLS_README
    tools.write_text("# no regions\n")
    problems = check_readmes(tree)
    assert {p.split(": ")[1].split(" ")[0] for p in problems} == {"no"}
    assert len(problems) == 2
    tools.unlink()
    problems = check_readmes(tree)
    assert len(problems) == 1 and "missing" in problems[0]
    write_readmes(tree)
    assert check_readmes(tree) == []


def test_text_outside_the_regions_is_kept_by_write(tree):
    readme = tree / DOCS_README
    readme.write_text("# Prose before\n\n" + readme.read_text() + "\nProse after.\n")
    (tree / "data/registry/zz-scratch.yaml").write_text(
        (tree / "data/registry/gw150914-strain.yaml")
        .read_text()
        .replace("id: gw150914-strain", "id: zz-scratch", 1)
        .replace(
            "dossier: docs/datasets/gw150914-strain.md",
            "dossier: docs/datasets/zz-scratch.md",
        )
    )
    write_readmes(tree)
    text = readme.read_text()
    assert text.startswith("# Prose before\n") and text.endswith("\nProse after.\n")
    assert "[zz-scratch]" in region_text(text, "later-table")


def test_a_card_without_a_dossier_is_listed_by_its_id_and_does_not_break_the_tables():
    all_cards = _all_cards()
    bare = {
        "id": "zz-survey-only",
        "title": "A survey-only card",
        "decision": {"value": "survey-only"},
    }
    cards = {**all_cards, "zz-survey-only": bare}
    rows = later_table(cards).splitlines()[2:]
    assert rows[-1] == _row(bare) and "data/registry/zz-survey-only.yaml" in rows[-1]
    assert rows[:-1] == later_table(all_cards).splitlines()[2:]
    assert survey_table(cards) == survey_table(all_cards)


def test_the_check_returns_the_validation_messages_of_an_incomplete_conversion_card(
    tmp_path,
):
    from pbc.data.check import check_repository

    card = copy.deepcopy(_all_cards()["dwd-potsdam-soil-temperature"])
    del card["conversions"][0]["input"]
    registry = tmp_path / "data" / "registry"
    registry.mkdir(parents=True)
    (registry / "dwd-potsdam-soil-temperature.yaml").write_text(
        yaml.safe_dump(card, sort_keys=False), encoding="utf-8"
    )
    problems = check_repository(tmp_path)  # must not raise
    assert any("input" in p for p in problems), problems
