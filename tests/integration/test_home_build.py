"""The home page builds from its data files (F158; Issue #481): the owner's
copy from the Home copy file, the course subjects of Part A from the
curriculum, a course without a published lesson marked as planned, and no
example lesson.

Each case is a minimal Quarto project in a temporary directory with the real
home page, its data files, and a few lessons of one course: the subjects
follow what is published, and a copy file that breaks its rules fails the
build.
"""

import re
import shutil
from pathlib import Path

import pytest
import yaml
from support.checks import output, run_check
from support.paths import SITE_SOURCE

from pbc.authoring.path import COURSES

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


def test_the_subjects_follow_the_published_lessons_and_no_example_is_shown(
    site: Path, tmp_path: Path
):
    page = built_text(site, tmp_path, "built")
    assert page.count("<h1") == 1
    (listing,) = re.findall(r'<ul class="home-subjects"[^>]*>(.*?)</ul>', page, re.S)
    subjects = re.findall(r"<li>(.*?)</li>", listing)
    # Only classical mechanics has a lesson here: the seven others are
    # named as planned, in the order of the curriculum file.
    assert subjects[0] == "Classical mechanics"
    assert subjects[1:] == [f"{course.title} (planned)" for course in COURSES[1:]]
    # No example lesson and no preview: the lessons are not on Home.
    assert "home-example" not in page and "previews/" not in page
    for title in ("First lesson", "Second lesson", "Agent lesson"):
        assert f">{title}</a>" not in page
    # The owner's headings, from the copy file.
    copy = yaml.safe_load((site / "home.yaml").read_text())
    assert copy["integrity"]["heading"] in page
    assert "Then challenge the AI." in page


def test_a_copy_file_that_breaks_its_rules_fails_the_build(site: Path, tmp_path: Path):
    file = site / "home.yaml"
    data = yaml.safe_load(file.read_text())
    data["curriculum"]["examples"] = {"part-a": "M1"}
    file.write_text(yaml.safe_dump(data, sort_keys=False))
    result = run_check("site-build", site, tmp_path / "failed")
    assert result.returncode != 0
    assert "curriculum has unknown fields: examples" in output(result)
