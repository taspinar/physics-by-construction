"""The slots of the reference curriculum that no published lesson fills, read
straight from the files (`site/curriculum.yaml` and the front matter of every
lesson page), independently of the authoring code that the tests check. Tests
that need a planned slot as an example take it from here, so that publishing a
slot does not change what they assert."""

from pathlib import Path

import yaml

from support.paths import SITE_SOURCE


def _front_matter(page: Path) -> dict:
    text = page.read_text(encoding="utf-8")
    _, header, _ = text.split("---\n", 2)
    return yaml.safe_load(header)


def filled_slots(site: Path = SITE_SOURCE) -> set[str]:
    """The labels that a published lesson's `lesson.slot` names."""
    return {
        slot
        for page in (site / "lessons").glob("*/*/index.qmd")
        if (slot := (_front_matter(page).get("lesson") or {}).get("slot"))
    }


def unfilled_slots(site: Path = SITE_SOURCE) -> list[dict]:
    """The curriculum's slots that no published lesson fills, in file order."""
    curriculum = yaml.safe_load((site / "curriculum.yaml").read_text(encoding="utf-8"))
    filled = filled_slots(site)
    return [slot for slot in curriculum["slots"] if slot["label"] not in filled]
