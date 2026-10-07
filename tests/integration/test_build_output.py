"""Quarto's intermediate build output does not mark the checkout as changed.

While it renders, Quarto writes each page next to its source before moving it
to ``site/_site/``. A lesson reads the state of the checkout during that
build, so output that Git does not ignore makes a clean checkout report
uncommitted changes, in the first build only (ADR 002, determinism).
"""

import subprocess

from support.paths import REPO_ROOT, SITE_SOURCE


def _page_sources() -> list[str]:
    """The pages Quarto renders: every .qmd outside an underscore directory."""
    pages = []
    for source in sorted(SITE_SOURCE.rglob("*.qmd")):
        parts = source.relative_to(SITE_SOURCE).parts
        if not any(part.startswith(("_", ".")) for part in parts):
            pages.append(source.relative_to(REPO_ROOT).as_posix())
    return pages


def test_git_ignores_the_page_rendered_next_to_every_source():
    pages = _page_sources()
    assert pages, "no page sources found"
    outputs = [page.removesuffix(".qmd") + ".html" for page in pages]
    outputs.append("site/site_libs/quarto-nav/quarto-nav.js")

    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "check-ignore", *outputs],
        capture_output=True,
        text=True,
        check=False,
    )

    missing = sorted(set(outputs) - set(result.stdout.split()))
    assert not missing, f"not ignored by Git: {missing}"


def test_git_still_tracks_html_sources():
    sources = ["site/widgets/example/widget.html", "site/_includes/partial.html"]

    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "check-ignore", *sources],
        capture_output=True,
        text=True,
        check=False,
    )

    assert not result.stdout.split(), f"ignored by Git: {result.stdout.split()}"
