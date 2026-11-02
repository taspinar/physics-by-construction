"""The hero script of the home page (F134, ADR 021 decision 4): small, with no
dependency, and it makes no request and uses no storage, cookie, timer, or
listener, so nothing changes after it has run. The browser tests show what it
does (tests/e2e/test_home.py); this test reads what it could do."""

import re

from support.paths import SITE_SOURCE

from pbc.authoring.home import HERO_SCRIPT

SOURCE = (SITE_SOURCE / HERO_SCRIPT).read_text(encoding="utf-8")
CODE = "\n".join(
    line for line in SOURCE.splitlines() if not line.lstrip().startswith("//")
)


def test_the_script_makes_no_request_and_uses_no_storage():
    for word in (
        "fetch",
        "XMLHttpRequest",
        "sendBeacon",
        "WebSocket",
        "EventSource",
        "import",
        "localStorage",
        "sessionStorage",
        "indexedDB",
        "cookie",
        "caches",
        "http",
        "src",
        "Image(",
    ):
        assert word not in CODE, word


def test_the_script_changes_nothing_after_it_has_run():
    for word in (
        "setTimeout",
        "setInterval",
        "requestAnimationFrame",
        "addEventListener",
        "onload",
        "history",
    ):
        assert word not in CODE, word


def test_the_script_is_small_and_reads_only_the_embedded_pairs_and_the_parameter():
    lines = [line for line in CODE.splitlines() if line.strip()]
    assert len(lines) <= 25
    assert 'getElementById("hero-pairs")' in CODE
    assert '.get("hero")' in CODE
    assert re.search(r"Math\.random\(\)", CODE)
