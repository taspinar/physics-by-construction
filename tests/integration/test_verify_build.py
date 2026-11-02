"""A worked example of "How we verify the science" whose target is missing
fails the build, as a claim without evidence does (F134, criterion 5).

The case is a minimal Quarto project in a temporary directory with the real
page and the lesson of the first example, whose claim no longer exists.
"""

import shutil
from pathlib import Path

from support.checks import output, run_check
from support.paths import SITE_SOURCE

from pbc.authoring.verify import EXAMPLES

_CONFIG = """\
project:
  type: website
format:
  html:
    html-math-method: mathml
"""

_LESSON = """\
---
title: "The lesson of the example"
lesson:
  id: {id}
  strand: mechanics
  order: 1
  difficulty: 1
  course: mechanics
  methods: [simulation]
  outcomes:
    - Do the first thing
    - Do the second thing
  related: []
  prerequisites:
    lessons: []
    outside: []
---

The claim the example names is gone.
"""


def test_a_missing_target_of_an_example_fails_the_build(tmp_path: Path):
    site = tmp_path / "site"
    lesson = site / "lessons" / "mechanics" / "01-example"
    lesson.mkdir(parents=True)
    (site / "_quarto.yml").write_text(_CONFIG)
    shutil.copy(SITE_SOURCE / "verify.qmd", site / "verify.qmd")
    (lesson / "index.qmd").write_text(_LESSON.format(id=EXAMPLES[0].lesson))

    result = run_check("site-build", site, tmp_path / "built")

    assert result.returncode != 0
    assert f"the example {EXAMPLES[0].lesson}/{EXAMPLES[0].evidence}" in output(result)
    assert not (tmp_path / "built" / "verify.html").exists()
