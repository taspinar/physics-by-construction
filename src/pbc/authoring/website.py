"""The website project a page belongs to."""

import posixpath
from pathlib import Path, PurePosixPath

import yaml

# Where the website project sits in the repository, and the file that marks
# the root of that project.
SITE_DIRECTORY = "site"
PROJECT_FILE = "_quarto.yml"
PAGE_FILE = "index.qmd"


def project_root(directory: Path) -> Path:
    """Return the website project that ``directory`` is inside of.

    A cell runs in the directory of its page, so this is how a helper finds
    the project it is building.
    """
    for candidate in (directory, *directory.parents):
        if (candidate / PROJECT_FILE).is_file():
            return candidate
    raise FileNotFoundError(f"{directory} is not inside a website project")


def page_href(from_page: str, to_page: str, fragment: str = "") -> str:
    """A relative link from the built ``from_page`` to the built ``to_page``,
    both given as source pages relative to the website project."""
    target = PurePosixPath(to_page).with_suffix(".html").as_posix()
    href = posixpath.relpath(target, PurePosixPath(from_page).parent.as_posix())
    return f"{href}#{fragment}" if fragment else href


def page_address(site: Path, page: str) -> str:
    """The public address of the built ``page`` (a source page relative to
    the website project ``site``): ``website.site-url`` of its
    ``_quarto.yml`` followed by the built page. A project without a
    ``site-url`` gets the built page's path in the site."""
    config = yaml.safe_load((site / PROJECT_FILE).read_text(encoding="utf-8")) or {}
    base = str((config.get("website") or {}).get("site-url") or "")
    built = PurePosixPath(page).with_suffix(".html").as_posix()
    return f"{base.rstrip('/')}/{built}" if base else built
