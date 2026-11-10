"""The hero script of the home page (F158; ADR 021 decision 4 as amended):
small, with no dependency; it requests nothing but the one hero image it
creates from the data the build embedded, touches no text of the page (the
headline and the subtext are fixed since round 2 of Issue #462), and uses no
storage, cookie, timer, or listener, so nothing changes after it has run (the
scan of I16 extended to the hero script, I35). The browser tests show what it
does (tests/e2e/test_home.py); this test reads what it could do."""

import re

from support.paths import SITE_SOURCE

from pbc.authoring.home import HERO_IMAGE_PARAMETER, HERO_SCRIPT

SOURCE = (SITE_SOURCE / HERO_SCRIPT).read_text(encoding="utf-8")
CODE = "\n".join(
    line for line in SOURCE.splitlines() if not line.lstrip().startswith("//")
)


def test_the_script_makes_no_request_but_the_one_image_and_uses_no_storage():
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
        "Image(",
        "srcset",
        "innerHTML",
        "write(",
        "preload",
    ):
        assert word not in CODE, word
    # The only address it sets is the embedded image's, on the one image it
    # creates.
    assert re.findall(r".*\bsrc\b.*", CODE) == ["    image.src = chosen.src;"]
    assert CODE.count('createElement("img")') == 1


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


def test_the_script_reads_only_the_embedded_images_and_its_one_parameter():
    lines = [line for line in CODE.splitlines() if line.strip()]
    assert len(lines) <= 25
    assert 'getElementById("hero-images")' in CODE
    assert re.findall(r'\.get\("([\w-]+)"\)', CODE) == [HERO_IMAGE_PARAMETER]
    assert CODE.count("pick(") == 2  # the function and its one use
    assert len(re.findall(r"Math\.random\(\)", CODE)) == 1


def test_the_script_touches_no_text_of_the_page():
    # The headline and the subtext are the HTML's: the script neither finds
    # nor writes them.
    for word in ("hero-copy", "hero-pairs", "h1", "querySelector", "textContent ="):
        assert word not in CODE, word
    assert "hero" not in re.sub(
        r"hero-image|hero-figure|hero-images|hero\.js", "", CODE
    )
