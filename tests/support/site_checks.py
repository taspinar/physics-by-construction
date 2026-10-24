"""Checks on a built site.

Each check takes the directory of a built site and returns the violations it
found, so the same code runs on the real site (tests/e2e) and on small sites
built to violate one rule (tests/integration).

The browser checks never reach the network: a request to anything but the
local test server is recorded as a violation and aborted.
"""

import ast
import itertools
import json
import re
from collections import Counter
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from axe_playwright_python.sync_playwright import Axe
from playwright.sync_api import Browser, BrowserContext, Page, Response, Route

from pbc.authoring import pages as page_selection
from pbc.authoring import previews
from pbc.authoring import selection as selecting
from pbc.authoring.design import CONTROL_CONTRAST, contrast_ratio
from pbc.authoring.path import LearningPath
from pbc.authoring.progress import EXPORT_FILE, STORAGE_KEY
from pbc.data import REGISTRY_DIR
from pbc.data.card import load_card
from pbc.data.status import allowed_statuses, artifact_types, needs_artifact
from support.paths import BUILT_SITE, REPO_ROOT
from support.site_server import SiteServer

DESKTOP = {"width": 1280, "height": 800}
TABLET = {"width": 768, "height": 1024}
# 320 CSS pixels is the width WCAG 2.1 uses for its reflow criterion.
PHONE = {"width": 320, "height": 568}

# The record of the checked pages of the run (pbc.authoring.pages).
CHECKED_RECORD = REPO_ROOT / page_selection.CHECKED_FILE

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


def _artifact_problems(
    card: dict, dataset: str, status: str, artifact: str | None
) -> list[str]:
    if artifact is None and needs_artifact(card):
        return [
            f"a figure of {dataset} does not say which artifact it shows; the"
            " card holds measurements and a modelled artifact"
        ]
    if artifact is not None and artifact not in artifact_types(card):
        return [f"the card of {dataset} has no artifact of type {artifact}"]
    allowed = allowed_statuses(card, artifact)
    if status in allowed:
        return []
    shown = dataset if artifact is None else f"the {artifact} of {dataset}"
    return [
        f"a figure of {shown} is labelled {status!r}; its card"
        f" allows {', '.join(sorted(allowed))}"
    ]


def check_figure_datasets(
    site_dir: Path, registry_dir: Path = REGISTRY_DIR
) -> list[Violation]:
    """A figure made from a dataset carries a status its card allows.

    The lesson filter puts the dataset of a ``fig-dataset`` cell on the status
    label of the caption. A figure of a measured sample is ``measured``,
    ``calibrated``, or ``processed``, never ``simulated``, and a dataset that
    has no card is an error (ADR 007). A figure of a model fitted to a dataset
    (``fig-model-of``) is ``simulated``.

    This compares what a page declares. That a figure made from a dataset
    declares it is the task of the source check (``support.data_use``); a built
    page no longer tells where the pixels of a figure came from.
    """
    violations = []
    for page in html_pages(site_dir):
        for _, attributes in _parse(page).elements:
            if "figure-status" not in attributes.get("class", "").split():
                continue
            status = attributes.get("data-status", "")
            model_of = attributes.get("data-model-of")
            if model_of is not None:
                if not (registry_dir / f"{model_of}.yaml").is_file():
                    violations.append(
                        Violation(
                            "figure-dataset",
                            _name(site_dir, page),
                            f"no card for {model_of}",
                        )
                    )
                elif status != "simulated" or "data-dataset" in attributes:
                    violations.append(
                        Violation(
                            "figure-dataset",
                            _name(site_dir, page),
                            f"a figure of a model of {model_of} is labelled"
                            f" {status!r} or also names a dataset; it is"
                            " 'simulated' and shows no data",
                        )
                    )
            dataset = attributes.get("data-dataset")
            if dataset is None:
                continue
            card = registry_dir / f"{dataset}.yaml"
            if not card.is_file():
                violations.append(
                    Violation(
                        "figure-dataset",
                        _name(site_dir, page),
                        f"no card for {dataset}",
                    )
                )
            else:
                violations.extend(
                    Violation("figure-dataset", _name(site_dir, page), detail)
                    for detail in _artifact_problems(
                        load_card(card),
                        dataset,
                        status,
                        attributes.get("data-artifact"),
                    )
                )
    return violations


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


def _urls(
    site_dir: Path, server: SiteServer, pages: list[Path] | None = None
) -> list[tuple[str, str]]:
    return [
        (_name(site_dir, page), server.url + _name(site_dir, page))
        for page in (html_pages(site_dir) if pages is None else pages)
    ]


class SelectionError(Exception):
    """The selection of the run cannot say whether it executed a lesson."""


def inherited(
    site_dir: Path, lesson: str, root: Path = REPO_ROOT, built: Path = BUILT_SITE
) -> str | None:
    """Why the results of ``lesson`` (a path such as ``site/lessons/s/01-one``)
    in the site at ``site_dir`` were not executed by this run, or None when
    they were (issue 268).

    The record is the selection that verify.sh writes (ADR 014 decision 5),
    the one the reproduction reads in tests/e2e/conftest.py. A run without a
    base removes it and executes every lesson, and a site built from a
    fixture is not the site it describes: both give None, so the check that
    asks runs. A selection that cannot be read, is of another format, or does
    not name the lesson exactly once as executed or restored raises
    SelectionError: a check never skips on a record it cannot trust."""
    if site_dir.resolve() != built.resolve():
        return None
    path = root / selecting.SELECTION_FILE
    if not path.exists():
        return None
    try:
        selection = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SelectionError(f"{path.name} cannot be read: {error}") from None
    if (
        not isinstance(selection, dict)
        or selection.get("format") != selecting.SELECTION_FORMAT
        or selection.get("mode") not in ("full", "selective")
    ):
        raise SelectionError(f"{path.name} is of another format")
    lists = [selection.get(key) for key in ("lessons", "execute", "reuse")]
    if not all(
        isinstance(names, list) and all(isinstance(n, str) for n in names)
        for names in lists
    ):
        raise SelectionError(f"{path.name} does not list its lessons")
    lessons, execute, reuse = lists
    named = (lessons.count(lesson), execute.count(lesson), reuse.count(lesson))
    if named not in ((1, 1, 0), (1, 0, 1)):
        raise SelectionError(
            f"{path.name} does not name {lesson} once as executed or restored"
        )
    if lesson in execute:
        return None
    base = selection.get("base")
    if selection["mode"] != "selective" or not isinstance(base, dict):
        raise SelectionError(f"{path.name} restores {lesson} without a base")
    # The base as pbc.authoring.selection names it: the SHA-256 of its digests
    # and the identity of its checks. A base it cannot name is no base.
    identifier, identity = base.get("id"), base.get("identity")
    if (
        not isinstance(identifier, str)
        or not re.fullmatch(r"[0-9a-f]{64}", identifier)
        or not isinstance(identity, str)
        or not identity
    ):
        raise SelectionError(f"{path.name} does not name the base it restores from")
    return (
        f"{lesson} was restored from the base {identifier[:12]}, not "
        "executed in this run: the run that made the base executed and checked "
        "it (ADR 014 decisions 2 to 4)"
    )


def checked_pages(site_dir: Path) -> list[Path]:
    """The pages the checks of one page run for (ADR 014 decision 3).

    Without a base, every page. With one, the pages whose bytes differ from the
    base's with the build commit normalised, and the pages of the lessons the
    run executed; a page that is byte-identical to a page of ``main`` that was
    checked is not checked again; a difference in a file that is not a page
    checks every page. What it chose, and why, is written to
    ``CHECKED_RECORD``. Only the checks of one page use this."""
    pages = html_pages(site_dir)
    # The selection belongs to the site this repository built, not to a site
    # built from a fixture.
    if site_dir.resolve() != BUILT_SITE.resolve():
        return pages
    data = page_selection.checked(site_dir)
    page_selection.write_checked(CHECKED_RECORD, data)
    if data["mode"] == "every":
        return pages
    return [page for page in pages if _name(site_dir, page) in data["pages"]]


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
    // dropped on a narrow screen; the <title> and <desc> of a drawing, which
    // are its accessible name and description and are never rendered; and
    // the body of a closed <details>, which opens without a script.
    if (element.closest(
      "script, style, template, annotation, annotation-xml, nav[role='doc-toc'],"
        + " svg > title, svg > desc"
    )) continue;
    // Inside a closed <details> only its own summary is rendered; a summary
    // inside the body of another closed <details> is hidden with that body.
    let closed = false;
    for (
      let details = element.closest("details:not([open])");
      details;
      details = details.parentElement?.closest("details:not([open])")
    ) {
      const summary = element.closest("summary");
      if (!summary || summary.parentElement !== details) closed = true;
    }
    if (closed) continue;
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
            for name, url in _urls(site_dir, server, checked_pages(site_dir)):
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
# and the images, figures, and captions that extend past an edge of the
# screen. They can do that without widening the page, when a container clips
# them.
_WIDTHS = """
() => {
  const screen = document.documentElement.clientWidth;
  const past = (element) => {
    const box = element.getBoundingClientRect();
    return box.right > screen + 1 || box.left < -1 || box.width > screen + 1;
  };
  const images = [...document.images]
    .filter(past)
    .map((image) => image.getAttribute("src"));
  const figures = [...document.querySelectorAll("figure, figcaption")]
    .filter(past)
    .map((element) => {
      const text = element.textContent.trim().slice(0, 40);
      return `${element.tagName.toLowerCase()} "${text}"`;
    });
  return [document.documentElement.scrollWidth, screen, images, figures];
}
"""


def check_no_horizontal_scroll(
    browser: Browser, server: SiteServer, site_dir: Path
) -> list[Violation]:
    """At phone, tablet, and desktop width the page is not wider than the
    screen and every image, figure, and caption fits on it, with and without scripts."""
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
            for name, url in _urls(site_dir, server, checked_pages(site_dir)):
                page = _open(context, url)
                content, screen, images, figures = page.evaluate(_WIDTHS)
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
                violations += [
                    Violation(
                        "figure-overflow",
                        name,
                        f"{figure} extends past a {screen}px screen"
                        f" ({scripts} scripts)",
                    )
                    for figure in figures
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
            for name, url in _urls(site_dir, server, checked_pages(site_dir)):
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


# Runs in the page after the first Tab. Describes the focused element: what it
# is, where it is on the screen, and how its focus ring is drawn.
_FOCUSED = """
() => {
  const element = document.activeElement;
  if (!element || element === document.body) return null;
  const style = getComputedStyle(element);
  const box = element.getBoundingClientRect();
  const colourOf = (candidate) => {
    for (let node = candidate; node; node = node.parentElement) {
      const colour = getComputedStyle(node).backgroundColor;
      if (colour !== "rgba(0, 0, 0, 0)" && colour !== "transparent") return colour;
    }
    return "rgb(255, 255, 255)";
  };
  return {
    text: element.textContent.trim(),
    skipLink: element.classList.contains("skip-link"),
    inNavigation: element.closest(".navbar") !== null,
    inMain: element.closest("main") !== null,
    box: [box.left, box.top, box.right, box.bottom],
    width: [window.innerWidth, window.innerHeight],
    outlineStyle: style.outlineStyle,
    outlineWidth: parseFloat(style.outlineWidth),
    outlineColour: style.outlineColor,
    background: colourOf(element),
  };
}
"""

_RGB = re.compile(r"rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)")


def _hex(colour: str) -> str:
    red, green, blue = (round(float(part)) for part in _RGB.match(colour).groups())
    return f"#{red:02x}{green:02x}{blue:02x}"


def _focus_ring_problem(focused: dict) -> str | None:
    """Why the focus ring of an element is not visible enough, if it is not:
    a ring at least two pixels wide with 3:1 against what is behind it
    (WCAG 2.2, 2.4.13)."""
    if focused["outlineStyle"] in ("none", "hidden") or focused["outlineWidth"] < 2:
        return "has no focus ring of two pixels or more"
    ratio = contrast_ratio(_hex(focused["outlineColour"]), _hex(focused["background"]))
    if ratio < CONTROL_CONTRAST:
        return f"has a focus ring with a contrast of {ratio:.2f}:1"
    return None


def check_keyboard_navigation(
    browser: Browser, server: SiteServer, site_dir: Path
) -> list[Violation]:
    """The keyboard pass of the accessibility audit, on every page: the first
    Tab reaches a skip link that is on the screen and has a visible focus ring,
    Enter on it moves to the content, and every entry of the navigation bar
    shows a focus ring that passes WCAG 2.2's focus appearance contrast."""
    violations = []
    for viewport in (DESKTOP, PHONE):
        with _context(browser, server, lambda url: None, viewport=viewport) as context:
            for name, url in _urls(site_dir, server):
                where = f"{viewport['width']}px wide"
                page = _open(context, url)
                page.keyboard.press("Tab")
                focused = page.evaluate(_FOCUSED)
                if not focused or not focused["skipLink"]:
                    violations.append(
                        Violation(
                            "skip-link", name, f"is not the first tab stop ({where})"
                        )
                    )
                    page.close()
                    continue
                left, top, right, bottom = focused["box"]
                width, height = focused["width"]
                if left < 0 or top < 0 or right > width or bottom > height:
                    violations.append(
                        Violation("skip-link", name, f"is off the screen ({where})")
                    )
                if problem := _focus_ring_problem(focused):
                    violations.append(
                        Violation("skip-link", name, f"{problem} ({where})")
                    )
                page.keyboard.press("Enter")
                if not page.evaluate("location.hash").endswith(
                    "#quarto-document-content"
                ):
                    violations.append(
                        Violation(
                            "skip-link", name, f"does not lead to the content ({where})"
                        )
                    )
                if not page.evaluate(
                    "document.getElementById('quarto-document-content') !== null"
                ):
                    violations.append(
                        Violation("skip-link", name, f"has no target ({where})")
                    )
                if not page.evaluate(
                    "document.activeElement.id === 'quarto-document-content'"
                ):
                    violations.append(
                        Violation(
                            "skip-link",
                            name,
                            f"does not move keyboard focus to the content ({where})",
                        )
                    )
                page.keyboard.press("Tab")
                after = page.evaluate(_FOCUSED)
                if after and (after["inNavigation"] or after["skipLink"]):
                    violations.append(
                        Violation(
                            "skip-link",
                            name,
                            f"is followed by the navigation on the next Tab ({where})",
                        )
                    )
                page.close()

                page = _open(context, url)
                entries = 0
                for _ in range(40):
                    page.keyboard.press("Tab")
                    focused = page.evaluate(_FOCUSED)
                    if not focused or focused["inMain"]:
                        break
                    if not focused["inNavigation"]:
                        continue
                    entries += 1
                    if problem := _focus_ring_problem(focused):
                        violations.append(
                            Violation(
                                "navigation-focus",
                                name,
                                f"the entry {focused['text']!r} {problem} ({where})",
                            )
                        )
                if entries < 5:
                    violations.append(
                        Violation(
                            "navigation-focus",
                            name,
                            f"only {entries} navigation entries took focus ({where})",
                        )
                    )
                page.close()
    return violations


# --- Page payload ------------------------------------------------------------

# The initial payload of a page: HTML, style sheets, fonts, static figures,
# scripts, and the data of an embedded widget (docs/architecture.md, "Budgets").
PAYLOAD_BUDGET = 3_000_000
# The learning path page together with the preview of every lesson it shows:
# 4 MB (owner's decision of 2026-10-23, Issue #264; 3 MB until then). The page
# grows by about 23 KB per lesson; 4 MB covers the 64 lessons of the capacity
# decision of 2026-10-21 with a margin of about 15 percent. Revisit at the next
# capacity decision (docs/architecture.md, "Budgets").
PATH_PAGE_BUDGET = 4_000_000
# The search index is fetched when a reader searches, on top of the page. One
# budget for the planned curriculum of 119 lessons (docs/architecture.md,
# "Budgets").
SEARCH_INDEX_BUDGET = 3_500_000
# Pages that site/search-index.py leaves out of the index.
UNINDEXED_PAGES = ("path/index.html",)


def check_search_index(site_dir: Path) -> list[Violation]:
    """The index exists, is within its budget, and holds no entry of a page
    that is navigation (the Learning path page)."""
    index = site_dir / "search.json"
    if not index.is_file():
        return [Violation("search-index", "search.json", "the build wrote no index")]
    violations = []
    size = index.stat().st_size
    if size >= SEARCH_INDEX_BUDGET:
        violations.append(
            Violation(
                "search-index",
                "search.json",
                f"{size} bytes, budget {SEARCH_INDEX_BUDGET}",
            )
        )
    for entry in json.loads(index.read_text(encoding="utf-8")):
        if entry["href"].split("#")[0] in UNINDEXED_PAGES:
            violations.append(
                Violation("search-index", entry["href"], "a page that is not indexed")
            )
    return violations


def measure_payloads(
    browser: Browser,
    server: SiteServer,
    site_dir: Path,
    pages: list[Path] | None = None,
) -> dict[str, int]:
    """The bytes every page transfers when it loads, by page: the sizes of
    the files of the site that the page requests. The test server sends files
    as they are, so this is the uncompressed size, which is the upper bound
    of what a compressing host transfers.

    Every page is loaded in a browser context of its own, as a reader who
    arrives on it first: a file that pages share, such as a font, counts for
    each of them. The sizes are read from the files and not from the
    responses, whose bodies the browser may not have kept when they are
    asked for, so the same site gives the same result on every run.
    ``pages`` limits the measure to those pages; by default every checked
    page is measured."""
    base = urlsplit(server.url).path
    sizes = {}
    chosen = checked_pages(site_dir) if pages is None else pages
    for name, url in _urls(site_dir, server, chosen):
        requested: set[str] = set()

        def note(response: Response, requested: set[str] = requested) -> None:
            if response.status < 400:
                requested.add(unquote(urlsplit(response.url).path))

        with _context(browser, server, lambda url: None, viewport=DESKTOP) as context:
            page = context.new_page()
            page.on("response", note)
            page.goto(url, wait_until="networkidle")
            page.close()
        total = 0
        for path in requested:
            if not path.startswith(base):
                continue
            file = site_dir / path[len(base) :]
            if file.is_dir():
                file = file / "index.html"
            if file.is_file():
                total += file.stat().st_size
        sizes[name] = total
    return sizes


def check_payload(
    sizes: dict[str, int], budget: int = PAYLOAD_BUDGET
) -> list[Violation]:
    return [
        Violation("payload", name, f"transfers {size:,} bytes, over {budget:,}")
        for name, size in sizes.items()
        if size > budget
    ]


# --- Lesson previews ---------------------------------------------------------

_IMG_SOURCE = re.compile(r"<img\b[^>]*?\bsrc\s*=\s*[\"']([^\"']*)", re.IGNORECASE)


def check_previews(
    site_dir: Path, path: LearningPath, site_source: Path, site_url: str
) -> list[Violation]:
    """Every lesson has exactly one preview in the built site (F63): the file
    is the figure of the cell the lesson names, scaled by the one function that
    scales, or the conceptual fallback drawn for the lesson; ``path.json``
    names the file with alt text that starts with the status; the previews
    hold nothing else; no image of the path page comes from another origin;
    and the previews together fit in the payload budget of the path page
    (``PATH_PAGE_BUDGET``)."""
    violations = []
    exported = json.loads((site_dir / EXPORT_FILE).read_text(encoding="utf-8"))
    entries = {entry["id"]: entry for entry in exported["lessons"]}
    expected = set()
    total = 0
    for lesson in path.lessons:
        preview = previews.preview_of(lesson, site_source)
        expected.add(preview.file)
        entry = entries.get(lesson.id, {}).get("preview")
        if entry != {"alt": preview.alt, "src": preview.file}:
            violations.append(
                Violation("preview", lesson.id, f"{EXPORT_FILE} names {entry!r}")
            )
        if not preview.alt.startswith(f"Preview, {preview.status}: "):
            violations.append(
                Violation(
                    "preview", lesson.id, "the alt text does not carry the status"
                )
            )
        file = site_dir / preview.file
        if not file.is_file():
            violations.append(
                Violation("preview", lesson.id, f"{preview.file} is not in the site")
            )
            continue
        total += file.stat().st_size
        if preview.fallback:
            wanted = previews.fallback(lesson).encode("utf-8")
        else:
            wanted = previews.scale(
                previews.figure_file(site_dir, lesson, preview.source).read_bytes()
            )
        if file.read_bytes() != wanted:
            violations.append(
                Violation(
                    "preview",
                    lesson.id,
                    f"{preview.file} is not the figure of"
                    f" {preview.source or 'the fallback'}",
                )
            )
    found = {
        file.relative_to(site_dir).as_posix()
        for file in (site_dir / previews.PREVIEW_DIRECTORY).glob("*")
    }
    for extra in sorted(found - expected):
        violations.append(Violation("preview", extra, "belongs to no lesson"))
    page = site_dir / "path" / "index.html"
    for source in _IMG_SOURCE.findall(page.read_text(encoding="utf-8")):
        if _is_other_origin(source, site_url):
            violations.append(
                Violation(
                    "preview", "path/index.html", f"image from another origin: {source}"
                )
            )
    if total > PATH_PAGE_BUDGET:
        violations.append(
            Violation(
                "preview", "previews", f"{total:,} bytes, over {PATH_PAGE_BUDGET:,}"
            )
        )
    return violations


def check_path_payload_with_previews(
    sizes: dict[str, int], site_dir: Path, budget: int = PATH_PAGE_BUDGET
) -> list[Violation]:
    """The learning path page with every preview it will show stays within
    its own budget, ``PATH_PAGE_BUDGET``; every other page keeps
    ``PAYLOAD_BUDGET``."""
    previews_size = sum(
        file.stat().st_size
        for file in (site_dir / previews.PREVIEW_DIRECTORY).glob("*")
    )
    name = "path/index.html"
    total = sizes.get(name, 0) + previews_size
    if total > budget:
        return [
            Violation(
                "payload", name, f"with the previews {total:,} bytes, over {budget:,}"
            )
        ]
    return []


# --- Search ------------------------------------------------------------------

SEARCH_CONTROL = "#quarto-search"
_SEARCH_INPUT = f"{SEARCH_CONTROL} input"
_SEARCH_RESULTS = "#quarto-search-results .aa-Item a, .aa-Panel .aa-Item a"
_STORAGE_ENTRIES = (
    "() => [...Object.keys(localStorage), ...Object.keys(sessionStorage)]"
)


def search_results(page: Page, query: str) -> list[str]:
    """Type ``query`` into the search control of ``page`` and return the
    addresses of the results it lists, in their order; none when it lists
    nothing within five seconds."""
    page.fill(_SEARCH_INPUT, "")
    page.fill(_SEARCH_INPUT, query)
    try:
        page.wait_for_selector(_SEARCH_RESULTS, timeout=5000)
    except Exception:
        return []
    return [
        urlsplit(link.get_attribute("href") or "").path
        for link in page.locator(_SEARCH_RESULTS).all()
    ]


def check_search_finds_a_lesson(
    browser: Browser,
    server: SiteServer,
    site_dir: Path,
    page_name: str,
    query: str,
    expected: str,
) -> list[Violation]:
    """On ``page_name``, typing ``query`` into the search control lists a
    result whose address ends with ``expected``. While it searches, the page
    requests nothing from another origin and writes no cookie and nothing to
    Web Storage, IndexedDB, the Cache API, or a service worker; what the page
    wrote while it loaded is not counted."""
    violations = []
    blocked: list[str] = []
    with _context(browser, server, blocked.append, viewport=DESKTOP) as context:
        context.add_init_script(f"({_RECORD_STORAGE_WRITES})()")
        page = context.new_page()
        page.goto(server.url + page_name, wait_until="networkidle")
        before = len(page.evaluate("window.__storageWrites"))
        entries = set(page.evaluate(_STORAGE_ENTRIES))
        if not page.locator(_SEARCH_INPUT).count():
            return [Violation("search", page_name, "has no search input")]
        page.fill(_SEARCH_INPUT, query)
        try:
            page.wait_for_selector(_SEARCH_RESULTS, timeout=5000)
        except Exception:
            return [Violation("search", page_name, f"'{query}' lists no result")]
        found = [
            link.get_attribute("href") or ""
            for link in page.locator(_SEARCH_RESULTS).all()
        ]
        if not any(urlsplit(href).path.endswith(expected) for href in found):
            violations.append(
                Violation("search", page_name, f"'{query}' does not find {expected}")
            )
        page.wait_for_load_state("networkidle")
        violations += [
            Violation("search-storage", page_name, f"writes {write}")
            for write in page.evaluate("window.__storageWrites")[before:]
        ]
        violations += [
            Violation("search-storage", page_name, f"leaves entry {key}")
            for key in set(page.evaluate(_STORAGE_ENTRIES)) - entries
        ]
        violations += [
            Violation("search-storage", page_name, f"sets cookie {cookie['name']}")
            for cookie in context.cookies()
        ]
        violations += [
            Violation("other-origin", page_name, f"requests {target}")
            for target in blocked
        ]
        page.close()
    return violations


def check_search_falls_back_without_javascript(
    browser: Browser, server: SiteServer, site_dir: Path, path_page: str
) -> list[Violation]:
    """With scripts disabled, no page shows a search control that cannot work:
    the place of the control holds a visible link to ``path_page`` instead."""
    violations = []
    with _context(
        browser, server, lambda url: None, viewport=DESKTOP, java_script_enabled=False
    ) as context:
        for name, url in _urls(site_dir, server):
            page = _open(context, url)
            control = page.locator(SEARCH_CONTROL)
            if control.count():
                if control.locator("input, button, [role=search]").count():
                    violations.append(
                        Violation("search-fallback", name, "shows a search control")
                    )
                link = control.locator("a")
                target = link.get_attribute("href") if link.count() == 1 else None
                if (
                    target is None
                    or not link.is_visible()
                    or urljoin(url, target) != server.url + path_page
                ):
                    violations.append(
                        Violation(
                            "search-fallback",
                            name,
                            f"does not show one visible link to {path_page}",
                        )
                    )
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
  region: element.getAttribute("data-region"),
  lines: element.getAttribute("data-lines"),
  text: (element.querySelector("code") ?? element).textContent,
  // The lines the listing marks, and the line each note is anchored to.
  marked: [...element.querySelectorAll(".marked")].map((l) => l.textContent.trim()),
  anchors: [
    ...(element.closest(".excerpt") ?? element).querySelectorAll("[data-anchor]"),
  ].map((note) => note.getAttribute("data-anchor")),
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


def _shown_part(text: str, region: str | None, lines: str | None) -> str | None:
    """Return the part of the source of one object that an excerpt declares
    to show (``region``, or ``lines`` as "first-last"), or None when the
    object has no such part."""
    if not region and not lines:
        return text
    object_lines = text.splitlines()
    if lines:
        match = re.fullmatch(r"(\d+)-(\d+)", lines)
        if not match:
            return None
        first, last = int(match[1]), int(match[2])
        if not 1 <= first <= last <= len(object_lines):
            return None
        return "\n".join(object_lines[first - 1 : last])
    starts = [
        i for i, t in enumerate(object_lines) if t.strip() == f"# region: {region}"
    ]
    ends = [
        i for i, t in enumerate(object_lines) if t.strip() == f"# endregion: {region}"
    ]
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        return None
    return "\n".join(object_lines[starts[0] + 1 : ends[0]])


def _source_of(
    repository: Path, name: str, region: str | None = None, lines: str | None = None
) -> str | None:
    """Return the source text of ``<module>:<object>``, read from the file, or
    None when there is no such thing. With ``region`` or ``lines``, only that
    part of a Python object, or None when it does not exist.

    A module of ``pbc`` names a top-level function or class of ``src/``, or
    nothing after the colon for a region or lines of the module itself; a
    module of ``PhysicsByConstruction`` or an exercise stub (``Exercises``)
    names a region of a Lean file in ``lean/``.
    """
    module, _, target = name.partition(":")
    if module.split(".")[0] in ("PhysicsByConstruction", "Exercises"):
        return None if region or lines else _lean_region(repository, name)
    file = repository / "src" / Path(*module.split(".")).with_suffix(".py")
    if module.split(".")[0] != "pbc" or not file.is_file():
        return None
    text = file.read_text(encoding="utf-8")
    if not target:
        # A part of the module itself, never the whole of it.
        return _shown_part(text, region, lines) if region or lines else None
    for node in ast.parse(text).body:
        if (
            isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
            and node.name == target
        ):
            first = min([node.lineno, *(d.lineno for d in node.decorator_list)])
            return _shown_part(
                "\n".join(text.splitlines()[first - 1 : node.end_lineno]), region, lines
            )
    return None


def _note_violations(page: str, excerpt: dict, source: str) -> list[Violation]:
    """The notes of an excerpt are anchored to lines of its source, and the
    listing marks exactly those lines."""
    shown = [line.strip() for line in source.splitlines()]
    anchors, marked = excerpt["anchors"], excerpt["marked"]
    violations = [
        Violation(
            "excerpt",
            page,
            f"a note on {excerpt['source']} is anchored to {anchor!r}, which is not"
            " on exactly one line of its source",
        )
        for anchor in anchors
        if shown.count(anchor) != 1
    ]
    if marked != anchors:
        violations.append(
            Violation(
                "excerpt",
                page,
                f"the lines marked in {excerpt['source']} are not the lines its"
                " notes name",
            )
        )
    return violations


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
                source = _source_of(
                    repository, excerpt["source"], excerpt["region"], excerpt["lines"]
                )
                if source is None:
                    violations.append(
                        Violation(
                            "excerpt",
                            name,
                            f"{excerpt['source']} (region {excerpt['region']},"
                            f" lines {excerpt['lines']}) is not a function or class"
                            " in src/pbc, nor an anchored region of a file in lean/,"
                            " or has no such region or lines",
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
                else:
                    violations += _note_violations(name, excerpt, source)
            page.close()
    return violations


def excerpt_sources(browser: Browser, server: SiteServer, page: str) -> list[str]:
    """Return the declared source of every excerpt on the built page ``page``."""
    with _context(browser, server, lambda url: None, viewport=DESKTOP) as context:
        opened = _open(context, server.url + page)
        return [excerpt["source"] for excerpt in opened.evaluate(_EXCERPTS)]


# --- Widgets -----------------------------------------------------------------

WIDGETS = "widgets"

# What a widget script must not contain: a reach for the network, for another
# origin, or for anything the browser keeps for the next visit. The XML
# namespace of SVG is a name, not a request, and is removed first.
_NAMESPACES = ("http://www.w3.org/2000/svg", "http://www.w3.org/1999/xhtml")
_REQUEST = re.compile(
    r"\bfetch\s*\(|XMLHttpRequest|WebSocket|EventSource|sendBeacon"
    r"|new\s+(?:Shared)?Worker\b|\bimportScripts\b|\bimport\s*\("
)
# A widget may load its on-demand data with ``fetch`` (see "On-demand data"
# below); every other way to reach the network stays out. That the fetch
# happens only after a user action, from the site's own origin, is shown by
# ``check_ondemand_loads_after_action``, not by this scan.
_REQUEST_OTHER_THAN_FETCH = re.compile(
    _REQUEST.pattern.replace(r"\bfetch\s*\(|", "", 1)
)
_FORBIDDEN_IN_WIDGETS = {
    "request": _REQUEST_OTHER_THAN_FETCH,
    "other origin": re.compile(r"(?:https?:)?//[\w.-]+\.\w+|https?://", re.IGNORECASE),
    "browser storage": re.compile(
        r"localStorage|sessionStorage|indexedDB|document\s*\.\s*cookie"
        r"|\bcaches\b|serviceWorker|cookieStore|openDatabase"
    ),
}


def check_widget_sources(site_dir: Path) -> list[Violation]:
    """The scripts in the widgets directory of the built site contain no
    request other than a ``fetch`` of its on-demand data, no other origin, and
    no use of browser storage.

    A static scan of the source is a floor, not proof: the browser check
    ``check_widgets_store_nothing`` watches what the widgets do.
    """
    violations = []
    for script in sorted((site_dir / WIDGETS).glob("*.js")):
        source = script.read_text(encoding="utf-8")
        for namespace in _NAMESPACES:
            source = source.replace(namespace, "")
        for kind, pattern in _FORBIDDEN_IN_WIDGETS.items():
            match = pattern.search(source)
            if match:
                violations.append(
                    Violation(
                        "widget-source",
                        _name(site_dir, script),
                        f"{kind}: {match.group(0)!r}",
                    )
                )
    return violations


# Runs before any script of the page. Records each write to cookies, Web
# Storage, IndexedDB, the Cache API, and service workers.
_RECORD_STORAGE_WRITES = """
() => {
  const writes = [];
  window.__storageWrites = writes;
  const record = (what) => writes.push(what);
  for (const method of ["setItem", "removeItem", "clear"]) {
    const original = Storage.prototype[method];
    Storage.prototype[method] = function (...args) {
      record("Storage." + method + "(" + args.join(", ") + ")");
      return original.apply(this, args);
    };
  }
  const cookie = Object.getOwnPropertyDescriptor(Document.prototype, "cookie");
  Object.defineProperty(Document.prototype, "cookie", {
    configurable: true,
    get() { return cookie.get.call(this); },
    set(value) { record("document.cookie = " + value); cookie.set.call(this, value); },
  });
  if (window.indexedDB) {
    const open = IDBFactory.prototype.open;
    IDBFactory.prototype.open = function (...args) {
      record("indexedDB.open(" + args[0] + ")");
      return open.apply(this, args);
    };
  }
  if (window.caches) {
    const open = CacheStorage.prototype.open;
    CacheStorage.prototype.open = function (...args) {
      record("caches.open(" + args[0] + ")");
      return open.apply(this, args);
    };
  }
  if (navigator.serviceWorker) {
    const register = ServiceWorkerContainer.prototype.register;
    ServiceWorkerContainer.prototype.register = function (...args) {
      record("serviceWorker.register(" + args[0] + ")");
      return register.apply(this, args);
    };
  }
}
"""

# Keys that move every kind of native control: radio buttons and sliders,
# selects, and (with Enter and Space) buttons.
_CONTROL_KEYS = ("ArrowRight", "ArrowDown", "End", "ArrowLeft", "ArrowUp", "Home")
_CONTROLS = f"{ENHANCEMENT} :is(input, select, textarea, button, summary, [tabindex])"


def drive_controls(page: Page, selector: str = _CONTROLS) -> int:
    """Operate every control of the declared enhancements with the keyboard,
    as a reader would; returns how many controls there were."""
    controls = page.locator(selector)
    count = controls.count()
    for index in range(count):
        control = controls.nth(index)
        if not control.is_visible():
            continue
        control.focus()
        for key in _CONTROL_KEYS:
            page.keyboard.press(key)
        tag = control.evaluate("element => element.localName")
        if tag in ("button", "summary"):
            page.keyboard.press("Enter")
            page.keyboard.press("Space")
    return count


def _storage_activity(
    browser: Browser, server: SiteServer, url: str, with_widgets: bool
) -> tuple[Counter, Counter]:
    """Load the page, operate the controls of its enhancements, and return
    the writes recorded and the entries left in Web Storage and cookies."""
    with _context(browser, server, lambda url: None, viewport=DESKTOP) as context:
        context.add_init_script(f"({_RECORD_STORAGE_WRITES})()")
        if not with_widgets:
            context.route(f"**/{WIDGETS}/*.js", lambda route: route.abort())
        page = context.new_page()
        page.goto(url, wait_until="networkidle")
        drive_controls(page)
        page.wait_for_timeout(100)
        writes = Counter(page.evaluate("window.__storageWrites"))
        left = Counter(
            "entry " + key
            for key in page.evaluate(
                "() => [...Object.keys(localStorage), ...Object.keys(sessionStorage)]"
            )
        )
        left += Counter("cookie " + cookie["name"] for cookie in context.cookies())
        page.close()
    return writes, left


def check_widgets_store_nothing(
    browser: Browser, server: SiteServer, site_dir: Path
) -> list[Violation]:
    """Loading a page with an enhancement and operating its controls writes
    no cookie and nothing to Web Storage, IndexedDB, the Cache API, or a
    service worker, beyond what the page does without its widget scripts.

    The writes are recorded as they happen, so a widget that writes and then
    clears its entry is caught too. The baseline is the same page with the
    scripts in ``widgets/`` blocked, because the site generator's own scripts
    keep a little state of their own; the widget must add nothing to it.
    """
    violations = []
    for name, url in _urls(site_dir, server):
        if "data-enhancement" not in (site_dir / name).read_text(encoding="utf-8"):
            continue
        writes, left = _storage_activity(browser, server, url, with_widgets=True)
        base_writes, base_left = _storage_activity(
            browser, server, url, with_widgets=False
        )
        violations += [
            Violation("widget-storage", name, f"writes {write}")
            for write in (writes - base_writes).elements()
        ]
        violations += [
            Violation("widget-storage", name, f"leaves {entry}")
            for entry in (left - base_left).elements()
        ]
    return violations


# --- On-demand data ----------------------------------------------------------

# Optional data a page loads after a user action (docs/architecture.md,
# "Budgets"): animation frames, field data, the series of a comparator. A
# widget names the files in ``data-ondemand`` (space-separated URLs relative
# to the page); the page is complete without them.
ONDEMAND_ATTRIBUTE = "data-ondemand"
# The button of that element that asks for the data.
LOAD_ATTRIBUTE = "data-loads-ondemand"
ONDEMAND_BUDGET = 3_000_000  # bytes per page
EVERYTHING_BUDGET = 5_000_000  # bytes: the initial payload and the on-demand data


def _ondemand_attributes(page: Path) -> list[str]:
    document = _parse(page)
    return [
        value
        for _tag, attributes in document.elements
        for name, value in attributes.items()
        if name == ONDEMAND_ATTRIBUTE
    ]


def ondemand_files(site_dir: Path) -> dict[str, list[tuple[str, Path | None]]]:
    """The on-demand files each page of the built site names, as
    ``(url, file in the built site or None when it is not there)``. A page
    that names none is left out."""
    found: dict[str, list[tuple[str, Path | None]]] = {}
    for page in html_pages(site_dir):
        entries = []
        for value in _ondemand_attributes(page):
            for url in value.split():
                target = (page.parent / unquote(urlsplit(url).path)).resolve()
                inside = target.is_relative_to(site_dir.resolve())
                entries.append((url, target if inside and target.is_file() else None))
        if entries:
            found[_name(site_dir, page)] = entries
    return found


def check_ondemand_budget(
    site_dir: Path,
    initial: dict[str, int] | None = None,
    budget: int = ONDEMAND_BUDGET,
    everything: int = EVERYTHING_BUDGET,
) -> list[Violation]:
    """Every on-demand file a page names exists in the built site, is a
    relative address of the site's own origin, and the files of a page are
    within ``budget`` bytes; with the initial payloads (``initial``, by page,
    from ``measure_payloads``), everything a page can load is within
    ``everything`` bytes."""
    violations = []
    for name, entries in ondemand_files(site_dir).items():
        total = 0
        for url, file in entries:
            parts = urlsplit(url)
            if parts.scheme or parts.netloc or url.startswith("/"):
                violations.append(
                    Violation(
                        "ondemand-origin", name, f"{url!r} is not a relative address"
                    )
                )
            elif file is None:
                violations.append(
                    Violation(
                        "ondemand-missing", name, f"{url!r} is not in the built site"
                    )
                )
            else:
                total += file.stat().st_size
        if total > budget:
            violations.append(
                Violation(
                    "ondemand-budget", name, f"loads {total:,} bytes, over {budget:,}"
                )
            )
        if (
            initial is not None
            and name in initial
            and initial[name] + total > everything
        ):
            violations.append(
                Violation(
                    "ondemand-total",
                    name,
                    f"can load {initial[name] + total:,} bytes, over {everything:,}",
                )
            )
    return violations


def check_ondemand_loads_after_action(
    browser: Browser, server: SiteServer, site_dir: Path
) -> list[Violation]:
    """A page requests its on-demand files only after a user action: loading
    the page and waiting for it to settle requests none of them, and pressing
    the button of the element that names them (``data-loads-ondemand``)
    requests them, and only from the site's own origin."""
    violations = []
    base = urlsplit(server.url)
    for name, entries in ondemand_files(site_dir).items():
        url = urljoin(server.url, name)
        wanted = {urljoin(url, entry).split("#")[0] for entry, file in entries if file}
        with _context(browser, server, lambda url: None, viewport=DESKTOP) as context:
            requested: list[str] = []
            context.on(
                "request", lambda request, log=requested: log.append(request.url)
            )
            page = context.new_page()
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(200)
            early = [r for r in requested if r.split("#")[0] in wanted]
            violations += [
                Violation(
                    "ondemand-early", name, f"{r!r} was requested before an action"
                )
                for r in early
            ]
            buttons = page.locator(f"[{ONDEMAND_ATTRIBUTE}] button[{LOAD_ATTRIBUTE}]")
            if buttons.count() == 0:
                violations.append(
                    Violation(
                        "ondemand-no-action",
                        name,
                        f"no button with {LOAD_ATTRIBUTE} asks for the data",
                    )
                )
            else:
                before = len(requested)
                buttons.first.click()
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(200)
                after = requested[before:]
                if not any(r.split("#")[0] in wanted for r in after):
                    violations.append(
                        Violation(
                            "ondemand-not-loaded", name, "the button loaded nothing"
                        )
                    )
                violations += [
                    Violation("ondemand-origin", name, f"{r!r} is another origin")
                    for r in after
                    if urlsplit(r).scheme in ("http", "https")
                    and urlsplit(r).netloc != base.netloc
                ]
            page.close()
    return violations


# --- Learner state -----------------------------------------------------------

LEARNER = "learner"

# What the learner-state script must not contain: it keeps its data in local
# storage and nowhere else. A request, another origin, a cookie, and every
# other place the browser can keep data are out; ``localStorage`` itself is
# what the script is for.
_FORBIDDEN_IN_LEARNER_SCRIPT = {
    "request": _REQUEST,
    "other origin": _FORBIDDEN_IN_WIDGETS["other origin"],
    "other storage": re.compile(
        r"sessionStorage|indexedDB|document\s*\.\s*cookie"
        r"|\bcaches\b|serviceWorker|cookieStore|openDatabase"
    ),
}


def check_learner_script_sources(site_dir: Path) -> list[Violation]:
    """The scripts in the learner directory of the built site contain no
    request, no other origin, and no storage but local storage.

    A static scan is a floor; ``check_learner_state_stays_local`` watches what
    the page does.
    """
    violations = []
    for script in sorted((site_dir / LEARNER).glob("*.js")):
        source = script.read_text(encoding="utf-8")
        for namespace in _NAMESPACES:
            source = source.replace(namespace, "")
        for kind, pattern in _FORBIDDEN_IN_LEARNER_SCRIPT.items():
            match = pattern.search(source)
            if match:
                violations.append(
                    Violation(
                        "learner-source",
                        _name(site_dir, script),
                        f"{kind}: {match.group(0)!r}",
                    )
                )
    return violations


_ELSEWHERE = ("document.cookie", "indexedDB", "caches", "serviceWorker")


def check_learner_state_stays_local(
    browser: Browser,
    server: SiteServer,
    page_name: str,
    act: Callable[[Page], None],
) -> list[Violation]:
    """Opening ``page_name`` and doing what ``act`` does with the page, which
    must store learner state, leaves the state in local storage only.

    Every request is a plain read of a file of the site (a GET with no body),
    and nothing the script stored, nor the key it stored it under, appears in
    the address, the headers, or the body of any request. No cookie is set
    and no write goes to a cookie, IndexedDB, the Cache API, or a service
    worker. A state that was not stored is reported too: the check would
    otherwise pass on a page that stores nothing.
    """
    violations = []
    requests: list[tuple[str, str, str | None, dict[str, str]]] = []
    blocked: list[str] = []
    with _context(browser, server, blocked.append, viewport=DESKTOP) as context:
        context.add_init_script(f"({_RECORD_STORAGE_WRITES})()")
        page = context.new_page()
        page.on(
            "request",
            lambda request: requests.append(
                (
                    request.method,
                    request.url,
                    request.post_data,
                    request.headers,
                )
            ),
        )
        page.goto(server.url + page_name, wait_until="networkidle")
        act(page)
        page.wait_for_load_state("networkidle")
        value = page.evaluate("(key) => localStorage.getItem(key)", STORAGE_KEY)
        stored = [STORAGE_KEY, value] if value else []
        writes = page.evaluate("window.__storageWrites")
        cookies = context.cookies()
        document_cookie = page.evaluate("document.cookie")
        page.close()
    if not stored:
        violations.append(
            Violation("state-stored", page_name, f"stored nothing under {STORAGE_KEY}")
        )
    for target in blocked:
        violations.append(Violation("other-origin", page_name, f"requests {target}"))
    for method, url, body, headers in requests:
        if not url.startswith(server.origin + "/"):
            continue
        if method != "GET" or body:
            violations.append(
                Violation("state-request", page_name, f"{method} {url} carries a body")
            )
        sent = "\n".join([unquote(url), body or "", *headers.values()])
        for text in stored:
            if text in sent:
                violations.append(
                    Violation(
                        "state-request",
                        page_name,
                        f"{method} {url} carries stored state {text[:40]!r}",
                    )
                )
    violations += [
        Violation("state-cookie", page_name, f"sets cookie {cookie['name']}")
        for cookie in cookies
    ]
    if document_cookie:
        violations.append(Violation("state-cookie", page_name, "sets document.cookie"))
    violations += [
        Violation("state-elsewhere", page_name, f"writes {write}")
        for write in writes
        if write.startswith(_ELSEWHERE)
    ]
    return violations


# --- The atlas modules (F126) ------------------------------------------------

# The scripts of the learner directory that enhance the course atlas and the
# index of the path page. They keep nothing at all: no request, no other
# origin, and no browser storage, local storage included;
# site/learner/progress.js stays the only script that stores anything.
ATLAS_MODULES = ("atlas.js", "path.js")
_FORBIDDEN_IN_ATLAS_MODULES = {
    "request": _REQUEST,
    "other origin": _FORBIDDEN_IN_WIDGETS["other origin"],
    "browser storage": _FORBIDDEN_IN_WIDGETS["browser storage"],
}


def check_atlas_module_sources(site_dir: Path) -> list[Violation]:
    """Each atlas module is in the built site and contains no request, no
    other origin, and no use of browser storage.

    A static scan is a floor; ``check_controls_keep_nothing`` watches what
    the page does while its controls are operated."""
    violations = []
    for name in ATLAS_MODULES:
        script = site_dir / LEARNER / name
        if not script.is_file():
            violations.append(Violation("atlas-source", f"{LEARNER}/{name}", "missing"))
            continue
        source = script.read_text(encoding="utf-8")
        for namespace in _NAMESPACES:
            source = source.replace(namespace, "")
        for kind, pattern in _FORBIDDEN_IN_ATLAS_MODULES.items():
            match = pattern.search(source)
            if match:
                violations.append(
                    Violation(
                        "atlas-source",
                        _name(site_dir, script),
                        f"{kind}: {match.group(0)!r}",
                    )
                )
    return violations


# A lazy image loads when scrolling or a relayout brings it near the
# viewport: a request of the page, not of a control. Loading every image
# before the recording keeps the check strict for every request (#259).
_LOAD_LAZY_IMAGES = """
() => {
  for (const image of document.images) image.loading = "eager";
}
"""
_IMAGES_LOADED = "() => [...document.images].every((image) => image.complete)"


def _load_lazy_images(page: Page) -> None:
    page.evaluate(_LOAD_LAZY_IMAGES)
    page.wait_for_function(_IMAGES_LOADED)
    page.wait_for_load_state("networkidle")


def check_controls_keep_nothing(
    browser: Browser,
    server: SiteServer,
    page_name: str,
    operate: Callable[[Page], int],
    viewport: dict[str, int] = DESKTOP,
) -> list[Violation]:
    """Opening ``page_name`` and doing what ``operate`` does with its controls
    makes no request once the page and its images have loaded (lazy ones
    included), sets no cookie, and writes
    nothing to Web Storage, IndexedDB, the Cache API, or a service worker;
    the entries of Web Storage are what they were after the page loaded.

    The writes are recorded as they happen, so a script that writes and then
    clears an entry is caught too. ``operate`` returns how many controls it
    operated; none is reported, since the check would otherwise pass on a
    page whose controls are missing."""
    violations = []
    blocked: list[str] = []
    requests: list[str] = []
    with _context(browser, server, blocked.append, viewport=viewport) as context:
        context.add_init_script(f"({_RECORD_STORAGE_WRITES})()")
        page = context.new_page()
        page.goto(server.url + page_name, wait_until="networkidle")
        _load_lazy_images(page)
        before = len(page.evaluate("window.__storageWrites"))
        entries = Counter(page.evaluate(_STORAGE_ENTRIES))
        page.on("request", lambda request: requests.append(request.url))
        operated = operate(page)
        page.wait_for_timeout(100)
        writes = page.evaluate("window.__storageWrites")[before:]
        left = Counter(page.evaluate(_STORAGE_ENTRIES))
        cookies = context.cookies()
        document_cookie = page.evaluate("document.cookie")
        page.close()
    if not operated:
        violations.append(Violation("controls", page_name, "operated no control"))
    violations += [
        Violation("controls-request", page_name, f"requests {url}") for url in requests
    ]
    violations += [
        Violation("other-origin", page_name, f"requests {url}") for url in blocked
    ]
    violations += [
        Violation("controls-storage", page_name, f"writes {write}") for write in writes
    ]
    violations += [
        Violation("controls-storage", page_name, f"leaves entry {key}")
        for key in (left - entries).elements()
    ]
    violations += [
        Violation("controls-cookie", page_name, f"sets cookie {cookie['name']}")
        for cookie in cookies
    ]
    if document_cookie:
        violations.append(
            Violation("controls-cookie", page_name, "sets document.cookie")
        )
    return violations
