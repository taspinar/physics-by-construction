"""The site build and the determinism check fail on pages that violate them.

Each case is a minimal Quarto project in a temporary directory.
"""

from pathlib import Path

import pytest
from support.checks import output, run_check

_CONFIG = """\
project:
  type: website
format:
  html:
    html-math-method: mathml
"""


@pytest.fixture
def site(tmp_path: Path) -> Path:
    source = tmp_path / "site"
    source.mkdir()
    (source / "_quarto.yml").write_text(_CONFIG)
    return source


def test_build_fails_on_an_equation_that_is_not_mathml(site: Path, tmp_path: Path):
    (site / "index.qmd").write_text(
        "---\ntitle: Equation\n---\n\nThe value $\\notacommand{x}$ is unknown.\n"
    )

    result = run_check("site-build", site, tmp_path / "out")

    assert result.returncode != 0
    assert "could not be converted to MathML" in output(result)


def test_build_fails_on_a_cell_that_raises(site: Path, tmp_path: Path):
    (site / "index.qmd").write_text(
        "---\ntitle: Cell\n---\n\n"
        '```{python}\nraise RuntimeError("the lesson code is broken")\n```\n'
    )

    result = run_check("site-build", site, tmp_path / "out")

    assert result.returncode != 0
    assert "the lesson code is broken" in output(result)


def test_determinism_fails_on_a_page_that_changes_between_builds(
    site: Path, tmp_path: Path
):
    (site / "index.qmd").write_text(
        "---\ntitle: Random\n---\n\n"
        "```{python}\nimport uuid\n\nprint(uuid.uuid4())\n```\n"
    )
    first = tmp_path / "first"
    build = run_check("site-build", site, first)
    assert build.returncode == 0, output(build)

    result = run_check("determinism", site, first)

    assert result.returncode != 0
    assert "index.html" in output(result) and "differ" in output(result)
