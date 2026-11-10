"""The execution settings of the site (ADR 002; D11 of #446, Issue #464):
every build executes every page and stores no result, so site/_quarto.yml
states ``execute.freeze: false`` and ``execute.cache: false``. This is a pin,
not a protection: the file stays sensitive, and a change to either setting
fails this test instead of passing unnoticed."""

import pytest
import yaml
from support.paths import SITE_SOURCE

CONFIG = yaml.safe_load((SITE_SOURCE / "_quarto.yml").read_text())
PINNED = {"freeze": False, "cache": False}


def execution_problems(config: dict) -> list[str]:
    """What differs from the pinned execution settings: each setting must be
    stated, and be exactly ``false`` (a missing one leaves it to Quarto's
    default, which is no pin)."""
    execute = config.get("execute")
    if not isinstance(execute, dict):
        return ["site/_quarto.yml has no execute section"]
    return [
        f"execute.{name} is {execute.get(name, 'missing')!r}, not false"
        for name, value in PINNED.items()
        if name not in execute or execute[name] is not value
    ]


def test_the_site_executes_every_page_and_stores_no_result():
    assert execution_problems(CONFIG) == []


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("freeze", True),
        ("freeze", "auto"),
        ("freeze", None),
        ("cache", True),
        ("cache", "refresh"),
        ("cache", None),
    ],
)
def test_a_changed_setting_fails_the_pin(name, value):
    config = {"execute": dict(PINNED)}
    if value is None:
        del config["execute"][name]
    else:
        config["execute"][name] = value
    assert execution_problems(config) == [
        f"execute.{name} is {config['execute'].get(name, 'missing')!r}, not false"
    ]


def test_a_missing_execute_section_fails_the_pin():
    config = {"project": {"type": "website"}}
    assert execution_problems(config) == ["site/_quarto.yml has no execute section"]
