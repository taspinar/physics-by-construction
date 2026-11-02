"""The home page chooses its examples from the lesson metadata at build time.

Each case is a minimal Quarto project in a temporary directory with the real
home page, its data files, and a few lessons; changing the lessons and
building again changes the examples the page shows (F25, F134).
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
description: "{title}, in one line. A second sentence."
lesson:
  id: {id}
  strand: {strand}
  order: {order}
  difficulty: {difficulty}
  course: {course}
  methods: [{methods}]
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
    course: str,
    methods: str = "simulation",
    strand: str = "",
    order: int = 1,
    difficulty: int = 1,
    prerequisite: str = "kinematics",
) -> None:
    strand = strand or course
    directory = site / "lessons" / strand / f"{order:02d}-{id}"
    directory.mkdir(parents=True)
    (directory / "index.qmd").write_text(
        _LESSON.format(
            id=id,
            title=title,
            strand=strand,
            order=order,
            difficulty=difficulty,
            course=course,
            methods=methods,
            prerequisite="" if id == "kinematics" else prerequisite,
        )
    )


@pytest.fixture
def site(tmp_path: Path) -> Path:
    source = tmp_path / "site"
    source.mkdir()
    (source / "_quarto.yml").write_text(_CONFIG)
    for name in ("index.qmd", "hero.yaml", "curriculum.yaml", "atlas.yaml"):
        shutil.copy(SITE_SOURCE / name, source / name)
    (source / "assets").mkdir()
    shutil.copy(SITE_SOURCE / "assets" / "provenance.yaml", source / "assets")
    write_lesson(source, "kinematics", "First lesson", "mechanics")
    write_lesson(source, "walk", "Walk lesson", "thermodynamics", order=1)
    write_lesson(
        source, "lab", "Lab lesson", "waves", "measured-data, simulation", difficulty=3
    )
    write_lesson(
        source,
        "agent",
        "Agent lesson",
        "astrophysics",
        "simulation, llm-agents",
        strand="agents-llm",
        difficulty=3,
    )
    return source


def built_text(site: Path, tmp_path: Path, name: str) -> str:
    result = run_check("site-build", site, tmp_path / name)
    assert result.returncode == 0, output(result)
    return (tmp_path / name / "index.html").read_text()


def test_the_examples_follow_the_lessons(site: Path, tmp_path: Path):
    before = built_text(site, tmp_path, "before")
    for title in ("Walk lesson", "Lab lesson", "Agent lesson"):
        assert f">{title}</a>" in before
    assert "Walk lesson, in one line." in before
    assert "A second sentence." not in before
    # The first course is the start link's, never an example.
    assert ">First lesson</a>" not in before
    assert "Introductory, level 1 of 3, in Thermodynamics" in before

    # Without the waves lab, a measured-data lesson of another course becomes
    # the example of its kind.
    shutil.rmtree(site / "lessons" / "waves")
    write_lesson(
        site,
        "fluid-lab",
        "Fluid lab lesson",
        "fluids",
        "measured-data",
        strand="fluids",
        difficulty=2,
    )
    after = built_text(site, tmp_path, "after")
    assert ">Fluid lab lesson</a>" in after
    assert ">Lab lesson</a>" not in after
    assert after.count("<h1") == 1
