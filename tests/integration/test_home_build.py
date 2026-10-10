"""The home page states the published lessons from the lesson metadata.

Each case is a minimal Quarto project in a temporary directory with the real
home page and a few lessons; changing the lessons and building again changes
the page (F25, acceptance criterion 2).
"""

import shutil
from pathlib import Path

import pytest
from support.checks import output, run_check
from support.paths import SITE_SOURCE

_CONFIG = """\
project:
  type: website
format:
  html:
    html-math-method: mathml
"""

_LESSON = """\
---
title: "{title}"
lesson:
  id: {id}
  strand: {strand}
  order: {order}
  difficulty: 1
  course: mechanics
  methods: [simulation]
  outcomes:
    - Do the first thing
    - Do the second thing
  related: []
  prerequisites:
    lessons: [{prerequisite}]
    outside: []
---

Body.
"""


def write_lesson(
    site: Path,
    id: str,
    title: str,
    strand: str = "mechanics",
    order: int = 1,
    prerequisite: str = "",
) -> None:
    directory = site / "lessons" / strand / f"{order:02d}-{id}"
    directory.mkdir(parents=True)
    (directory / "index.qmd").write_text(
        _LESSON.format(
            id=id,
            title=title,
            strand=strand,
            order=order,
            prerequisite=prerequisite,
        )
    )


@pytest.fixture
def site(tmp_path: Path) -> Path:
    source = tmp_path / "site"
    source.mkdir()
    (source / "_quarto.yml").write_text(_CONFIG)
    shutil.copy(SITE_SOURCE / "index.qmd", source / "index.qmd")
    # The three lessons the home page names as examples.
    write_lesson(source, "numerical-integrators", "First lesson")
    write_lesson(
        source,
        "agent-experiment",
        "Agent lesson",
        strand="agents-llm",
        prerequisite="numerical-integrators",
    )
    write_lesson(
        source,
        "proving-what-the-simulation-showed",
        "Proof lesson",
        strand="lean",
        prerequisite="numerical-integrators",
    )
    return source


def built_text(site: Path, tmp_path: Path, name: str) -> str:
    result = run_check("site-build", site, tmp_path / name)
    assert result.returncode == 0, output(result)
    return (tmp_path / name / "index.html").read_text()


def test_the_counts_and_names_follow_the_lessons(site: Path, tmp_path: Path):
    before = built_text(site, tmp_path, "before")
    assert "publishes 3 lessons in 3 strands" in before
    assert "Second lesson" not in before

    write_lesson(
        site,
        "second",
        "Second lesson",
        order=2,
        prerequisite="numerical-integrators",
    )
    after = built_text(site, tmp_path, "after")

    assert "publishes 4 lessons in 3 strands" in after
    assert "Second lesson" in after
    assert "mechanics course is published with 2 core lessons" in after.lower()
    assert "mechanics course is published with 1 core lesson and" in before.lower()
