"""Context-dependent presentation of a page (ADR 014 decision 9).

A lesson page shows things that do not follow from the lesson's own inputs: the
header (previous and next lesson, prerequisites, related lessons, course, slot)
and the previous and next lesson at the end of the page read the front matter
of every lesson, and the last section (the experiment) and
the code and Lean excerpts name the commit the page was built from. A page
taken from the store of an earlier run would show the navigation and the commit
of that run.

So the helpers that produce them do not put that presentation into the result
of their cell. They put a *marker*: an empty block that holds the kind of the
region, the page it belongs to, and the facts the region is built from
(``payload``), each independent of the commit and of the other lessons. The
store holds markers and scientific results only. After the render, the
post-render step ``site/context.py`` replaces every marker in every built page
by the region it stands for, built from the current front matter, the current
curriculum, and the commit of the run, and fails when a marker is not valid or
a page lacks a region it must have. Only a marker is ever modified, and on a
lesson page the previous and next lesson are inserted before the end of
``main`` (F174): the rest of a page is left as the render wrote it.
"""

import base64
import hashlib
import html
import json
import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from pbc.authoring.repository import BuildCommit, build_commit, repository_url
from pbc.authoring.website import PAGE_FILE, page_address, project_root

MARKER_CLASS = "pbc-context"
KINDS = ("header", "reproduce", "excerpt", "lean-excerpt", "lean-evidence")
# A lesson page that has markers has a header and a last section.
REQUIRED = ("header", "reproduce")
LESSONS_DIRECTORY = "lessons"
SPLIT = "<!--pbc-context-split-->"
ID_PREFIX = "ctx-"
HIGHLIGHT_STYLE_DIRECTORY = "site"
# The end of a page's content: the previous and next lesson go before it.
MAIN_END = "</main>"


class InvalidContext(Exception):
    """A marker or a page whose context cannot be regenerated."""


def current_page() -> str:
    """The page of the cell that is running, relative to the site project."""
    directory = Path.cwd().resolve()
    relative = directory.relative_to(project_root(directory)).as_posix()
    return PAGE_FILE if relative == "." else f"{relative}/{PAGE_FILE}"


def _checksum(kind: str, page: str, body: str) -> str:
    return hashlib.sha256(f"{kind}\n{page}\n{body}".encode()).hexdigest()[:16]


def marker(kind: str, page: str, payload: dict) -> str:
    """The Markdown of a marker: what a helper returns as its cell output.

    It is deterministic in its arguments and holds no value that depends on the
    commit, the time, or another lesson.
    """
    if kind not in KINDS:
        raise ValueError(f"unknown kind of context {kind!r}")
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    body = base64.urlsafe_b64encode(text.encode()).decode("ascii")
    return (
        f'::: {{.{MARKER_CLASS} pbc-kind="{kind}" pbc-page="{page}"'
        f' pbc-payload="{body}" pbc-check="{_checksum(kind, page, body)}"}}\n:::\n'
    )


_MARKER = re.compile(rf'<div\s+class="{MARKER_CLASS}"([^<>]*)>\s*</div>')
_ATTRIBUTE = re.compile(r'([A-Za-z][A-Za-z0-9-]*)="([^"]*)"')
_STRAY = re.compile(rf'class="{MARKER_CLASS}"')


def _decode(attributes: str, page: str) -> tuple[str, dict]:
    found = {
        name: html.unescape(value) for name, value in _ATTRIBUTE.findall(attributes)
    }
    try:
        kind, where, body, check = (
            found["data-pbc-kind"],
            found["data-pbc-page"],
            found["data-pbc-payload"],
            found["data-pbc-check"],
        )
    except KeyError as error:
        raise InvalidContext(f"{page}: a marker lacks {error.args[0]}") from None
    if kind not in KINDS:
        raise InvalidContext(f"{page}: a marker of unknown kind {kind!r}")
    # A cell knows the directory it runs in, not the name of its file: only the
    # page of a lesson, which is always its directory's index.qmd, is checked.
    if page.startswith(f"{LESSONS_DIRECTORY}/") and where != page:
        raise InvalidContext(f"{page}: a marker made for {where!r}")
    if check != _checksum(kind, where, body):
        raise InvalidContext(f"{page}: a {kind} marker does not match its checksum")
    try:
        payload = json.loads(base64.urlsafe_b64decode(body.encode("ascii")))
    except ValueError as error:
        raise InvalidContext(
            f"{page}: a {kind} marker is not readable: {error}"
        ) from None
    if not isinstance(payload, dict):
        raise InvalidContext(f"{page}: a {kind} marker holds no object")
    return kind, payload


def markdown(
    kind: str,
    page: str,
    payload: dict,
    site: Path,
    commit: BuildCommit,
    repository: str,
) -> str:
    """The Markdown of the region a marker stands for, from the current state."""
    # Imported here: the helpers import this module to make their markers.
    from pbc.authoring.excerpt import Excerpt
    from pbc.authoring.lean import LeanEvidence, LeanExcerpt
    from pbc.authoring.path import LessonHeader
    from pbc.authoring.reproduce import Reproduction

    try:
        if kind == "header":
            return LessonHeader.from_payload(site, page, payload).markdown()
        if kind == "reproduce":
            return Reproduction.from_payload(
                page, payload, commit, repository, page_address(site, page)
            ).markdown()
        if kind == "excerpt":
            return Excerpt.from_payload(payload, commit, repository).markdown()
        if kind == "lean-excerpt":
            return LeanExcerpt.from_payload(payload, commit, repository).markdown()
        return LeanEvidence.from_payload(payload, commit, repository).markdown()
    except (KeyError, TypeError, ValueError, LookupError, OSError) as error:
        raise InvalidContext(
            f"{page}: the {kind} region cannot be built: {error}"
        ) from error


def pager_markdown(site: Path, page: str) -> str:
    """The previous and the next lesson of the lesson ``page``, which end the
    page after all its content (F174), from the current front matter."""
    from pbc.authoring.path import LearningPath, lesson_pager

    try:
        path = LearningPath.read(site)
        return lesson_pager(path, path.at_page(page))
    except (KeyError, TypeError, ValueError, LookupError, OSError) as error:
        raise InvalidContext(
            f"{page}: the previous and next lesson cannot be built: {error}"
        ) from error


def _pandoc(chunks: list[str], site: Path) -> list[str]:
    """Convert Markdown regions to HTML the way the render does.

    One run for the page; the options are those of ``site/_quarto.yml``
    (MathML, the vendored Lean syntax definition) and the filter that makes
    code and display equations scrollable.
    """
    quarto = shutil.which("quarto")
    if quarto is None:
        raise InvalidContext("quarto is not on the path; it converts the regions")
    needed = (site / "assets" / "lean.xml", site / "_filters" / "scroll-regions.lua")
    for file in needed:
        if not file.is_file():
            raise InvalidContext(
                f"{file} is missing; it is read to convert the regions"
            )
    text = f"\n\n```{{=html}}\n{SPLIT}\n```\n\n".join(chunks)
    command = [
        quarto,
        "pandoc",
        "--from=markdown",
        "--to=html",
        "--wrap=none",
        "--mathml",
        f"--id-prefix={ID_PREFIX}",
        f"--syntax-definition={site / 'assets' / 'lean.xml'}",
        f"--lua-filter={site / '_filters' / 'scroll-regions.lua'}",
    ]
    result = subprocess.run(
        command, input=text, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise InvalidContext(f"pandoc failed: {result.stderr.strip()}")
    parts = [part.strip("\n") for part in result.stdout.split(SPLIT)]
    if len(parts) != len(chunks):
        raise InvalidContext("pandoc returned a different number of regions")
    return parts


_CODE = re.compile(
    r'(<div class="sourceCode"[^>]*>)<pre class="sourceCode ([^"]*)"(.*?)</pre></div>',
    re.S,
)


def _quarto_code(region: str) -> str:
    """Give a code block the copy button the render gives every code block,
    after numbering the lines of an excerpt's listing.

    A part of a selection and a generated signature get no copy button: they
    are not a whole that runs (ADR 023 decision 3).
    """
    from pbc.authoring.excerpt import NO_COPY_CLASSES, number_lines

    def wrap(found: re.Match[str]) -> str:
        # The render writes the quotation marks of code as they are.
        code = found.group(3).replace("&quot;", '"').replace("&#39;", "'")
        if set(found.group(2).split()) & set(NO_COPY_CLASSES):
            return (
                f'{found.group(1)}<pre class="sourceCode {found.group(2)}"'
                f"{code}</pre></div>"
            )
        return (
            '<div class="code-copy-outer-scaffold">'
            f'{found.group(1)}<pre class="sourceCode {found.group(2)} code-with-copy"'
            f"{code}</pre></div>"
            '<button title="Copy to Clipboard" class="code-copy-button">'
            '<i class="bi"></i></button></div>'
        )

    return _CODE.sub(wrap, number_lines(region))


def regenerate_page(
    text: str,
    page: str,
    site: Path,
    commit: BuildCommit,
    repository: str,
    convert: Callable[[list[str]], list[str]] | None = None,
) -> str:
    """The built page ``text`` (``page`` is its source, ``lessons/.../index.qmd``)
    with every marker replaced by its region. Raises InvalidContext."""
    found = list(_MARKER.finditer(text))
    decoded = [_decode(match.group(1), page) for match in found]
    kinds = [kind for kind, _ in decoded]
    # A lesson page whose cells leave markers has the regions every lesson has. A
    # page without any marker has nothing that could be stale; the source
    # checks and the checks of the built site require its header.
    if found and page.startswith(f"{LESSONS_DIRECTORY}/"):
        for required in REQUIRED:
            if required not in kinds:
                raise InvalidContext(f"{page}: the page has no {required} region")
    chunks = [
        markdown(kind, page, payload, site, commit, repository)
        for kind, payload in decoded
    ]
    if not found:
        return text
    # A lesson page ends with the previous and the next lesson, after all its
    # content, whatever follows the last section's cell (F174).
    pager = page.startswith(f"{LESSONS_DIRECTORY}/") and "reproduce" in kinds
    if pager:
        chunks.append(pager_markdown(site, page))
    regions = (convert or (lambda c: _pandoc(c, site)))(chunks)
    end = regions.pop() if pager else ""
    pieces = []
    last = 0
    for match, region in zip(found, regions, strict=True):
        pieces += [text[last : match.start()], _quarto_code(region)]
        last = match.end()
    pieces.append(text[last:])
    result = "".join(pieces)
    if _STRAY.search(result):
        # A marker the pattern did not match: the page would keep stale or empty
        # context.
        raise InvalidContext(f"{page}: a marker remains after regeneration")
    if pager:
        close = result.rfind(MAIN_END)
        if close < 0:
            raise InvalidContext(
                f"{page}: the page has no {MAIN_END} before which the previous"
                " and next lesson go"
            )
        result = f"{result[:close]}{end}\n{result[close:]}"
    return result


def regenerate(
    output: Path,
    site: Path,
    commit: BuildCommit | None = None,
    repository: str | None = None,
) -> list[str]:
    """Regenerate the context of every built page under ``output``.

    The commit and the repository are those of this checkout unless given.
    Returns the pages that held markers. Raises InvalidContext for the first
    page that cannot be regenerated; that page is not written.
    """
    commit = build_commit() if commit is None else commit
    repository = repository_url() if repository is None else repository
    changed = []
    for built in sorted(output.rglob("*.html")):
        relative = built.relative_to(output)
        text = built.read_text(encoding="utf-8")
        page = relative.with_suffix(".qmd").as_posix()
        # Pages the render wrote that are not pages of the site (search
        # fallback, previews) hold no marker and no required region.
        if not (site / page).is_file():
            if _STRAY.search(text):
                raise InvalidContext(f"{relative}: a marker in a page without a source")
            continue
        updated = regenerate_page(text, page, site, commit, repository)
        if updated != text:
            built.write_text(updated, encoding="utf-8")
            changed.append(page)
    return changed
