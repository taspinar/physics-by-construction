"""Checks on a built site.

Each check takes the directory of a built site and returns the violations it
found, so the same code runs on the real site (tests/e2e) and on small sites
built to violate one rule (tests/integration).

The browser checks never reach the network: a request to anything but the
local test server is recorded as a violation and aborted.
"""

import ast
import itertools
import re
from collections import Counter
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from axe_playwright_python.sync_playwright import Axe
from playwright.sync_api import Browser, BrowserContext, Page, Route

from support.site_server import SiteServer

DESKTOP = {"width": 1280, "height": 800}
TABLET = {"width": 768, "height": 1024}
# 320 CSS pixels is the width WCAG 2.1 uses for its reflow criterion.
PHONE = {"width": 320, "height": 568}

WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]

# Declares an optional interactive enhancement (architecture invariant I4).
# What a script adds inside such an element is not required content, when the
# element is in the page without scripts, has an id, and holds static content
# there: the fallback the script enhances.
ENHANCEMENT = "[data-enhancement]"


@dataclass(frozen=True)
class Violation:
    rule: str
    page: str
    detail: str

    def __str__(self) -> str:
        return f"[{self.rule}] {self.page}: {self.detail}"


def describe(violations: list[Violation]) -> str:
    """Format violations for an assertion message."""
    return "\n".join(str(violation) for violation in violations)


# --- Reading the built files -------------------------------------------------


class _Document(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.elements: list[tuple[str, dict[str, str]]] = []
        self.inline_css: list[str] = []
        self._in_style = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name: value or "" for name, value in attrs}
        self.elements.append((tag, attributes))
        if "style" in attributes:
            self.inline_css.append(attributes["style"])
        if tag == "style":
            self._in_style = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "style":
            self._in_style = False

    def handle_data(self, data: str) -> None:
        if self._in_style:
            self.inline_css.append(data)


def _parse(path: Path) -> _Document:
    document = _Document()
    document.feed(path.read_text(encoding="utf-8"))
    document.close()
    return document


def html_pages(site_dir: Path) -> list[Path]:
    """Return every HTML page of the site; a site without pages is an error."""
    pages = sorted(site_dir.rglob("*.html"))
    if not pages:
        raise FileNotFoundError(f"no HTML pages in {site_dir}; build the site first")
    return pages


def _name(site_dir: Path, page: Path) -> str:
    return page.relative_to(site_dir).as_posix()


# --- Checks on the files -----------------------------------------------------


def check_images(site_dir: Path) -> list[Violation]:
    """Every image has alternative text and explicit dimensions."""
    violations = []
    for page in html_pages(site_dir):
        name = _name(site_dir, page)
        for tag, attributes in _parse(page).elements:
            if tag != "img":
                continue
            source = attributes.get("src", "(no src)")
            if not attributes.get("alt", "").strip():
                violations.append(
                    Violation("image-alt", name, f"image without alt text: {source}")
                )
            if not all(
                attributes.get(side, "").isdigit() for side in ("width", "height")
            ):
                violations.append(
                    Violation(
                        "image-dimensions",
                        name,
                        f"image without width and height: {source}",
                    )
                )
    return violations


# Attributes whose URL the browser loads as part of the page.
_RESOURCE_ATTRIBUTES = {
    ("script", "src"),
    ("img", "src"),
    ("img", "srcset"),
    ("source", "src"),
    ("source", "srcset"),
    ("video", "src"),
    ("video", "poster"),
    ("audio", "src"),
    ("track", "src"),
    ("iframe", "src"),
    ("embed", "src"),
    ("object", "data"),
    ("input", "src"),
    ("use", "href"),
    ("use", "xlink:href"),
    ("image", "href"),
    ("image", "xlink:href"),
}
# <link> relations that only point somewhere and load nothing.
_NAVIGATIONAL_RELS = {
    "alternate",
    "author",
    "canonical",
    "help",
    "license",
    "me",
    "next",
    "prev",
}
_CSS_URL = re.compile(
    r"""url\(\s*(?:"([^"]*)"|'([^']*)'|([^'")\s][^)]*?))\s*\)"""
    r"""|@import\s+(?:"([^"]*)"|'([^']*)')""",
    re.IGNORECASE,
)


def _is_other_origin(url: str, site_url: str) -> bool:
    url = url.strip()
    if url.startswith(site_url):
        return False
    return url.startswith("//") or urlsplit(url).scheme in ("http", "https")


def _resource_urls(tag: str, attributes: dict[str, str]) -> Iterator[str]:
    for name, value in attributes.items():
        if tag == "link" and name == "href":
            rels = set(attributes.get("rel", "").lower().split())
            if rels and rels <= _NAVIGATIONAL_RELS:
                continue
            yield value
        elif (tag, name) in _RESOURCE_ATTRIBUTES:
            if name == "srcset":
                yield from (
                    candidate.split()[0]
                    for candidate in value.split(",")
                    if candidate.strip()
                )
            else:
                yield value


def _css_urls(css: str) -> Iterator[str]:
    for match in _CSS_URL.finditer(css):
        yield next(group for group in match.groups() if group is not None)


def check_static_origins(site_dir: Path, site_url: str) -> list[Violation]:
    """No page or stylesheet refers to a resource on another origin.

    Links a reader follows (``<a href>``) are allowed; anything the browser
    would load is not.
    """
    violations = []
    for page in html_pages(site_dir):
        name = _name(site_dir, page)
        document = _parse(page)
        urls = [
            url
            for tag, attributes in document.elements
            for url in _resource_urls(tag, attributes)
        ]
        urls += [url for css in document.inline_css for url in _css_urls(css)]
        violations += [
            Violation("other-origin", name, f"loads {url}")
            for url in urls
            if _is_other_origin(url, site_url)
        ]
    for stylesheet in sorted(site_dir.rglob("*.css")):
        css = stylesheet.read_text(encoding="utf-8")
        violations += [
            Violation("other-origin", _name(site_dir, stylesheet), f"loads {url}")
            for url in _css_urls(css)
            if _is_other_origin(url, site_url)
        ]
    return violations


_LINK_ATTRIBUTES = {("a", "href"), ("link", "href"), ("area", "href")} | {
    pair for pair in _RESOURCE_ATTRIBUTES if pair[1] != "srcset"
}


def check_internal_links(
    site_dir: Path, base_path: str, site_url: str
) -> list[Violation]:
    """Every link into the site resolves to a file, and to an anchor in it.

    Pages are resolved as if served under ``base_path``, so a link that
    assumes the site sits at the root of its host is reported.
    """
    host = "http://site.invalid"
    ids: dict[Path, set[str]] = {}

    def anchors(page: Path) -> set[str]:
        if page not in ids:
            ids[page] = {
                attributes[key]
                for tag, attributes in _parse(page).elements
                for key in ("id", "name")
                if key in attributes and (key == "id" or tag == "a")
            }
        return ids[page]

    violations = []
    for page in html_pages(site_dir):
        name = _name(site_dir, page)
        page_url = host + base_path + name
        for tag, attributes in _parse(page).elements:
            for attribute, value in attributes.items():
                if (tag, attribute) not in _LINK_ATTRIBUTES or not value.strip():
                    continue
                value = value.strip()
                if value.startswith(site_url):
                    value = base_path + value[len(site_url) :]
                target = urlsplit(urljoin(page_url, value))
                if f"{target.scheme}://{target.netloc}" != host:
                    continue  # another site, or not a web address (mailto:, data:)
                if not target.path.startswith(base_path):
                    violations.append(
                        Violation(
                            "internal-link",
                            name,
                            f"{value} leaves the site root {base_path}",
                        )
                    )
                    continue
                file = site_dir / unquote(target.path[len(base_path) :])
                if file.is_dir():
                    file = file / "index.html"
                if not file.is_file():
                    violations.append(
                        Violation("internal-link", name, f"{value} does not exist")
                    )
                elif (
                    target.fragment
                    and file.suffix == ".html"
                    and unquote(target.fragment) not in anchors(file)
                ):
                    violations.append(
                        Violation("internal-link", name, f"{value} has no such anchor")
                    )
    return violations


# --- Checks in a browser -----------------------------------------------------


@contextmanager
def _context(
    browser: Browser,
    server: SiteServer,
    blocked: Callable[[str], None],
    **options: object,
) -> Iterator[BrowserContext]:
    """Open a browser context that can reach only the local test server."""
    context = browser.new_context(**options)

    def guard(route: Route) -> None:
        url = route.request.url
        if url.startswith(server.origin + "/"):
            route.continue_()
        else:
            blocked(url)
            route.abort()

    context.route("**/*", guard)
    try:
        yield context
    finally:
        context.close()


def _open(context: BrowserContext, url: str) -> Page:
    page = context.new_page()
    page.goto(url, wait_until="load")
    return page


def _urls(site_dir: Path, server: SiteServer) -> list[tuple[str, str]]:
    return [
        (_name(site_dir, page), server.url + _name(site_dir, page))
        for page in html_pages(site_dir)
    ]


def check_requests_and_cookies(
    browser: Browser, server: SiteServer, site_dir: Path
) -> list[Violation]:
    """Loading a page requests nothing from another origin and sets no cookie.

    Also reports a resource of the site itself that fails to load.
    """
    violations = []
    blocked: list[str] = []
    with _context(browser, server, blocked.append, viewport=DESKTOP) as context:
        for name, url in _urls(site_dir, server):
            blocked.clear()
            failed: list[str] = []
            page = context.new_page()
            page.on(
                "response",
                lambda response, failed=failed: (
                    failed.append(f"{response.url} ({response.status})")
                    if response.status >= 400
                    else None
                ),
            )
            page.goto(url, wait_until="networkidle")
            violations += [
                Violation("other-origin", name, f"requests {target}")
                for target in blocked
            ]
            violations += [
                Violation("failed-request", name, target) for target in failed
            ]
            cookies = {cookie["name"] for cookie in context.cookies()}
            cookies |= {
                part.split("=")[0].strip()
                for part in page.evaluate("document.cookie").split(";")
                if part.strip()
            }
            violations += [
                Violation("cookie", name, f"sets cookie {cookie}")
                for cookie in sorted(cookies)
            ]
            context.clear_cookies()
            page.close()
    return violations


# Runs in the page. Reports text that is in the document but not rendered,
# images that did not load, and equations without a rendered box.
_UNREADABLE_CONTENT = """
() => {
  const problems = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const seen = new Set();
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const element = node.parentElement;
    if (!node.textContent.trim() || !element || seen.has(element)) continue;
    seen.add(element);
    // Not content, or hidden by design: the TeX source kept inside MathML;
    // the table of contents, which repeats the headings of the page and is
    // dropped on a narrow screen; and the body of a closed <details>, which
    // opens without a script.
    if (element.closest(
      "script, style, template, annotation, annotation-xml, nav[role='doc-toc']"
    )) continue;
    const details = element.closest("details:not([open])");
    if (details && !element.closest("summary")) continue;
    const visible = element.checkVisibility({
      visibilityProperty: true,
      opacityProperty: true,
      contentVisibilityAuto: true,
    });
    if (!visible) {
      problems.push("hidden text: " + node.textContent.trim().slice(0, 60));
    }
  }
  for (const image of document.images) {
    if (!(image.complete && image.naturalWidth > 0)) {
      problems.push("image not loaded: " + image.getAttribute("src"));
    }
  }
  for (const equation of document.querySelectorAll("math")) {
    const box = equation.getBoundingClientRect();
    if (box.width === 0 || box.height === 0) {
      const source = equation.textContent.trim().slice(0, 60);
      problems.push("equation not rendered: " + source);
    }
  }
  return problems;
}
"""


# Runs in the page, with the selector of a declared enhancement. Returns the
# content of the page: text, images, equations, and drawings, each with the id
# of the enhancement it is in and whether it is rendered.
_CONTENT = """
(enhancement) => {
  const items = [];
  const add = (element, description) => {
    const declared = element.closest(enhancement);
    items.push({
      description,
      enhancement: declared ? declared.id : "",
      rendered: element.checkVisibility({
        visibilityProperty: true,
        opacityProperty: true,
        contentVisibilityAuto: true,
      }),
    });
  };
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const element = node.parentElement;
    const text = node.textContent.trim().replace(/\\s+/g, " ");
    // An equation is one item, below, not the text of its parts.
    if (!text || !element || element.closest("script, style, template, math")) {
      continue;
    }
    add(element, "text: " + text);
  }
  for (const image of document.images) {
    add(image, "image: " + (image.currentSrc || image.src));
  }
  for (const equation of document.querySelectorAll("math")) {
    add(equation, "equation: " + equation.textContent.trim());
  }
  for (const drawing of document.querySelectorAll("svg, canvas")) {
    add(drawing, "drawing: " + drawing.localName);
  }
  return items;
}
"""


def _only_with_scripts(scripted: list[dict], static: list[dict]) -> list[str]:
    """Return the content a reader sees with scripts that the page without
    scripts does not contain, outside the declared enhancements."""
    fallbacks = {item["enhancement"] for item in static if item["enhancement"]}
    # Everything in the static page counts, rendered or not: content that is
    # there but not rendered is already reported as such.
    present = Counter(item["description"] for item in static)
    seen = Counter(
        item["description"]
        for item in scripted
        if item["rendered"] and item["enhancement"] not in fallbacks
    )
    return [
        f"only with scripts: {description[:70]}"
        for description in (seen - present).elements()
    ]


def check_readable_without_javascript(
    browser: Browser, server: SiteServer, site_dir: Path
) -> list[Violation]:
    """With scripts disabled, all text is rendered, images load, and equations
    have a rendered box, at desktop and at phone width. Text, images,
    equations, and drawings that a reader sees with scripts are also in the
    page without them; only a declared enhancement (``ENHANCEMENT``) may add
    more."""
    violations = []
    for viewport in (DESKTOP, PHONE):
        with (
            _context(
                browser,
                server,
                lambda url: None,
                viewport=viewport,
                java_script_enabled=False,
            ) as without_scripts,
            _context(
                browser, server, lambda url: None, viewport=viewport
            ) as with_scripts,
        ):
            for name, url in _urls(site_dir, server):
                page = _open(without_scripts, url)
                problems = page.evaluate(_UNREADABLE_CONTENT)
                static = page.evaluate(_CONTENT, ENHANCEMENT)
                page.close()
                # Wait for the network as well, for content a script fetches.
                page = with_scripts.new_page()
                page.goto(url, wait_until="networkidle")
                problems += _only_with_scripts(
                    page.evaluate(_CONTENT, ENHANCEMENT), static
                )
                page.close()
                violations += [
                    Violation(
                        "no-javascript", name, f"{problem} ({viewport['width']}px wide)"
                    )
                    for problem in problems
                ]
    return violations


# Runs in the page. Returns the width of the page, the width of the screen,
# and the images that extend past the right edge of the screen. An image can
# do that without widening the page, when a container clips it.
_WIDTHS = """
() => {
  const screen = document.documentElement.clientWidth;
  const images = [...document.images]
    .filter((image) => image.getBoundingClientRect().right > screen + 1)
    .map((image) => image.getAttribute("src"));
  return [document.documentElement.scrollWidth, screen, images];
}
"""


def check_no_horizontal_scroll(
    browser: Browser, server: SiteServer, site_dir: Path
) -> list[Violation]:
    """At phone, tablet, and desktop width the page is not wider than the
    screen and every image fits on it, with and without scripts."""
    violations = []
    for javascript, viewport in itertools.product(
        (True, False), (PHONE, TABLET, DESKTOP)
    ):
        scripts = "with" if javascript else "without"
        with _context(
            browser,
            server,
            lambda url: None,
            viewport=viewport,
            java_script_enabled=javascript,
        ) as context:
            for name, url in _urls(site_dir, server):
                page = _open(context, url)
                content, screen, images = page.evaluate(_WIDTHS)
                if content > screen:
                    violations.append(
                        Violation(
                            "horizontal-scroll",
                            name,
                            f"page is {content}px wide on a {screen}px screen"
                            f" ({scripts} scripts)",
                        )
                    )
                violations += [
                    Violation(
                        "image-overflow",
                        name,
                        f"{image} extends past a {screen}px screen ({scripts} scripts)",
                    )
                    for image in images
                ]
                page.close()
    return violations


def check_accessibility(
    browser: Browser, server: SiteServer, site_dir: Path
) -> list[Violation]:
    """The automated WCAG 2.1 A and AA scan (axe-core) finds nothing, at
    desktop and at phone width."""
    violations = []
    options = {
        "runOnly": {"type": "tag", "values": WCAG_TAGS},
        "resultTypes": ["violations"],
    }
    for viewport in (DESKTOP, PHONE):
        with _context(browser, server, lambda url: None, viewport=viewport) as context:
            for name, url in _urls(site_dir, server):
                page = _open(context, url)
                results = Axe().run(page, options=options)
                for finding in results.response["violations"]:
                    for node in finding["nodes"]:
                        violations.append(
                            Violation(
                                f"wcag:{finding['id']}",
                                name,
                                f"{finding['help']} at {node['target']}"
                                f" ({viewport['width']}px wide)",
                            )
                        )
                page.close()
    return violations


def check_navigation_fits(
    browser: Browser, server: SiteServer, site_dir: Path
) -> list[Violation]:
    """Every entry of the navigation bar stays on the screen at phone width,
    also with text a quarter wider than here.

    The bar does not collapse into a menu. Its entries must wrap, and how many
    fit on a line depends on the fonts of the machine: an entry that fits here
    can lie past the right edge on another machine, where it cannot be reached
    without a script. The wider text stands in for those fonts.
    """
    violations = []
    for scale in (1.0, 1.25):
        with _context(browser, server, lambda url: None, viewport=PHONE) as context:
            for name, url in _urls(site_dir, server):
                page = _open(context, url)
                page.add_style_tag(content=f".navbar {{ font-size: {scale}em; }}")
                outside = page.evaluate(
                    """(width) => [...document.querySelectorAll('.navbar a')]
                        .filter((link) => {
                            const box = link.getBoundingClientRect();
                            return box.width > 0 && (box.left < 0 || box.right > width);
                        })
                        .map((link) => link.textContent.trim())""",
                    PHONE["width"],
                )
                violations += [
                    Violation(
                        "navigation",
                        name,
                        f"the entry {entry!r} is not on the screen at"
                        f" {PHONE['width']}px with text {scale} times as wide",
                    )
                    for entry in outside
                ]
                page.close()
    return violations


# --- Lesson constructs -------------------------------------------------------
#
# What docs/authoring.md promises about a built lesson page. The checks run
# on every page of the site, because the constructs work on every page.


def check_sections(
    site_dir: Path, page: str, sections: Sequence[str]
) -> list[Violation]:
    """The built page ``page`` exists and has a level-2 section for each
    identifier in ``sections``."""
    file = site_dir / page
    if not file.is_file():
        return [Violation("lesson-page", page, "the lesson has no built page")]
    present = {
        attributes.get("id")
        for tag, attributes in _parse(file).elements
        if tag == "section" and "level2" in attributes.get("class", "").split()
    }
    return [
        Violation("lesson-page", page, f"no section with the identifier '{section}'")
        for section in sections
        if section not in present
    ]


# Runs in the page. Returns the start of every "not verified" element whose
# label is missing, does not say so, or is not rendered. An element inside a
# closed <details> element, such as a solution, is judged as the reader sees
# it after opening that element: the label has to appear with the material.
_UNLABELLED = """
() => {
  const marked = [...document.querySelectorAll(".not-verified")];
  for (const element of marked) {
    let details = element.closest("details");
    while (details) {
      details.open = true;
      details = details.parentElement?.closest("details");
    }
  }
  return marked
    .filter((element) => {
      const label = element.querySelector(".not-verified-label");
      return !(
        label
        && /not verified/i.test(label.textContent)
        && label.checkVisibility({ visibilityProperty: true, opacityProperty: true })
      );
    })
    .map((element) => element.textContent.trim().replace(/\\s+/g, " ").slice(0, 60));
}
"""


def check_not_verified_labels(
    browser: Browser, server: SiteServer, site_dir: Path
) -> list[Violation]:
    """Material marked "not verified" shows a label that says so, without
    scripts."""
    violations = []
    with _context(
        browser, server, lambda url: None, viewport=DESKTOP, java_script_enabled=False
    ) as context:
        for name, url in _urls(site_dir, server):
            page = _open(context, url)
            violations += [
                Violation("not-verified-label", name, f"no visible label on: {text}")
                for text in page.evaluate(_UNLABELLED)
            ]
            page.close()
    return violations


# Runs in the page. Returns the text of every code element that still starts
# with a cell or inline-expression marker such as {python}.
_UNEXECUTED = """
() => [...document.querySelectorAll("code")]
  .map((code) => code.textContent.trim())
  .filter((text) => /^\\{[A-Za-z]+\\}/.test(text))
  .map((text) => text.replace(/\\s+/g, " ").slice(0, 60))
"""

# Runs in the page. Returns the declared source and the text of every
# by-reference excerpt.
_EXCERPTS = """
() => [...document.querySelectorAll("[data-source]")].map((element) => ({
  source: element.getAttribute("data-source"),
  text: (element.querySelector("code") ?? element).textContent,
}))
"""


def _lean_region(repository: Path, name: str) -> str | None:
    """Return the text between ``-- ANCHOR: <anchor>`` and
    ``-- ANCHOR_END: <anchor>`` in the Lean module of ``<module>:<anchor>``,
    or None when the file or the markers are missing.

    Written out here and not imported from ``pbc``, so that the check does not
    rely on the code that wrote the page.
    """
    module, _, anchor = name.partition(":")
    file = repository / "lean" / Path(*module.split(".")).with_suffix(".lean")
    if not file.is_file():
        return None
    lines = file.read_text(encoding="utf-8").splitlines()
    start = [
        i for i, line in enumerate(lines) if line.strip() == f"-- ANCHOR: {anchor}"
    ]
    end = [
        i for i, line in enumerate(lines) if line.strip() == f"-- ANCHOR_END: {anchor}"
    ]
    if len(start) != 1 or len(end) != 1 or start[0] >= end[0]:
        return None
    return "\n".join(lines[start[0] + 1 : end[0]])


def _source_of(repository: Path, name: str) -> str | None:
    """Return the source text of ``<module>:<object>``, read from the file, or
    None when there is no such thing.

    A module of ``pbc`` names a top-level function or class of ``src/``; a
    module of ``PhysicsByConstruction`` names a region of a Lean file in
    ``lean/``.
    """
    module, _, target = name.partition(":")
    if module.split(".")[0] == "PhysicsByConstruction":
        return _lean_region(repository, name)
    file = repository / "src" / Path(*module.split(".")).with_suffix(".py")
    if module.split(".")[0] != "pbc" or not file.is_file():
        return None
    text = file.read_text(encoding="utf-8")
    for node in ast.parse(text).body:
        if (
            isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
            and node.name == target
        ):
            first = min([node.lineno, *(d.lineno for d in node.decorator_list)])
            return "\n".join(text.splitlines()[first - 1 : node.end_lineno])
    return None


def check_displayed_code(
    browser: Browser, server: SiteServer, site_dir: Path, repository: Path
) -> list[Violation]:
    """Every by-reference excerpt is textually identical to its source in
    ``src/pbc`` or ``lean/`` of ``repository``, and no page shows a cell or an inline
    expression that the build did not execute."""
    violations = []
    with _context(browser, server, lambda url: None, viewport=DESKTOP) as context:
        for name, url in _urls(site_dir, server):
            page = _open(context, url)
            violations += [
                Violation("unexecuted-cell", name, f"shown but not executed: {text}")
                for text in page.evaluate(_UNEXECUTED)
            ]
            for excerpt in page.evaluate(_EXCERPTS):
                source = _source_of(repository, excerpt["source"])
                if source is None:
                    violations.append(
                        Violation(
                            "excerpt",
                            name,
                            f"{excerpt['source']} is not a function or class in"
                            " src/pbc, nor an anchored region of a file in lean/",
                        )
                    )
                elif excerpt["text"].rstrip("\n") != source.rstrip("\n"):
                    violations.append(
                        Violation(
                            "excerpt",
                            name,
                            f"the listing of {excerpt['source']} differs from"
                            " its source",
                        )
                    )
            page.close()
    return violations


def excerpt_sources(browser: Browser, server: SiteServer, page: str) -> list[str]:
    """Return the declared source of every excerpt on the built page ``page``."""
    with _context(browser, server, lambda url: None, viewport=DESKTOP) as context:
        opened = _open(context, server.url + page)
        return [excerpt["source"] for excerpt in opened.evaluate(_EXCERPTS)]
