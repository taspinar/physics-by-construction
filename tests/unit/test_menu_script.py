"""The menu script of the shared header (F158, round 2 of Issue #462): small,
with no dependency; it reads the menu and the viewport and nothing else,
makes no request, and uses no storage or cookie (the scan of I16 extended to
the scripts of the chrome). The browser tests show what it does
(tests/e2e/test_header.py); this test reads what it could do, and that the
script and the style sheet agree on the break point of the compact header."""

import re

from support.paths import SITE_SOURCE

SCRIPT = SITE_SOURCE / "learner" / "menu.js"
STYLE = SITE_SOURCE / "assets" / "site.css"
SOURCE = SCRIPT.read_text(encoding="utf-8")
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
        "innerHTML",
        "write(",
        "setTimeout",
        "setInterval",
        "history",
    ):
        assert word not in CODE, word


def test_the_script_reads_only_the_menu_and_the_viewport():
    lines = [line for line in CODE.splitlines() if line.strip()]
    assert len(lines) <= 20
    assert re.findall(r"getElementById\(\"([\w-]+)\"\)", CODE) == ["pbc-menu"]
    assert 'querySelector("summary")' in CODE
    # Four things happen, and no other: the toggle's state follows the
    # menu; the fit to the viewport, now and on a change; the Escape key.
    assert re.findall(r"addEventListener\(\"(\w+)\"", CODE) == [
        "toggle",
        "change",
        "keydown",
    ]
    assert '"Escape"' in CODE
    assert CODE.count("menu.open =") == 2
    assert re.findall(r'setAttribute\("([\w-]+)"', CODE) == ["aria-expanded"]


def test_the_script_and_the_style_sheet_agree_on_the_break_point():
    (query,) = re.findall(r'matchMedia\("([^"]+)"\)', CODE)
    style = STYLE.read_text(encoding="utf-8")
    assert style.count(f"@media {query}") == 1
    # The compact header's rules are under that query; the step above it
    # starts where it ends.
    assert query == "(max-width: 39.99em)"
    compact = style.split(f"@media {query}")[1]
    assert ".pbc-menu-toggle {\n    position: absolute;" in compact
