"""The home page takes its example lessons from the Home copy file, resolved
and checked against the published lessons at build time (F158, replacing
the examples chosen by code of F25 and F134).

Each case is a minimal Quarto project in a temporary directory with the real
home page, its data files, and a few lessons: changing the slot the copy
file names changes the example the page shows, adding a lesson changes
nothing, and naming a slot without a published lesson fails the build.
"""

import shutil
from pathlib import Path

import pytest
import yaml
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
  slot: {slot}
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
    slot: str,
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
            slot=slot,
            methods=methods,
            prerequisite="" if id == "kinematics" else prerequisite,
        )
    )


@pytest.fixture
def site(tmp_path: Path) -> Path:
    source = tmp_path / "site"
    source.mkdir()
    (source / "_quarto.yml").write_text(_CONFIG)
    for name in (
        "index.qmd",
        "hero.yaml",
        "home.yaml",
        "journey.yaml",
        "glossary.yaml",
        "curriculum.yaml",
        "atlas.yaml",
    ):
        shutil.copy(SITE_SOURCE / name, source / name)
    (source / "assets").mkdir()
    shutil.copy(SITE_SOURCE / "assets" / "provenance.yaml", source / "assets")
    shutil.copytree(SITE_SOURCE / "assets" / "hero", source / "assets" / "hero")
    write_lesson(source, "kinematics", "First lesson", "mechanics", "M1")
    write_lesson(
        source, "second", "Second lesson", "mechanics", "M2", order=2, difficulty=2
    )
    write_lesson(
        source,
        "agent",
        "Agent lesson",
        "mechanics",
        "SA5",
        "simulation, llm-agents",
        strand="agents-llm",
        difficulty=2,
    )
    return source


def built_text(site: Path, tmp_path: Path, name: str) -> str:
    result = run_check("site-build", site, tmp_path / name)
    assert result.returncode == 0, output(result)
    return (tmp_path / name / "index.html").read_text()


def set_example(site: Path, part: str, label: str | None) -> None:
    file = site / "home.yaml"
    data = yaml.safe_load(file.read_text())
    if label is None:
        data["curriculum"]["examples"].pop(part)
    else:
        data["curriculum"]["examples"][part] = label
    file.write_text(yaml.safe_dump(data, sort_keys=False))


def test_the_examples_follow_the_copy_file(site: Path, tmp_path: Path):
    before = built_text(site, tmp_path, "before")
    assert 'data-lesson-id="kinematics"' in before
    assert 'data-lesson-id="agent"' in before
    assert ">Agent lesson</a>" in before
    assert "Agent lesson, in one line." in before
    assert "A second sentence." not in before
    assert 'data-lesson-id="second"' not in before
    assert before.count("<h1") == 1

    # The owner names another published lesson for Part A, and none for
    # Part B: the page follows the file, and no lesson is chosen in its place.
    set_example(site, "part-a", "M2")
    set_example(site, "part-b", None)
    after = built_text(site, tmp_path, "after")
    assert 'data-lesson-id="second"' in after
    assert 'data-lesson-id="kinematics"' not in after
    assert 'data-lesson-id="agent"' not in after
    assert "home-example" in after and after.count('class="home-example"') == 1


def test_an_example_without_a_published_lesson_fails_the_build(
    site: Path, tmp_path: Path
):
    shutil.rmtree(site / "lessons" / "agents-llm")
    result = run_check("site-build", site, tmp_path / "failed")
    assert result.returncode != 0
    assert "SA5, which has no published lesson" in output(result)
