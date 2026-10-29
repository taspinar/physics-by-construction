"""The preview of a lesson comes from the figure cell it names or from the
conceptual fallback, and the same input gives the same bytes (F63)."""

import io
from pathlib import Path

import pytest
from PIL import Image

from pbc.authoring import LearningPath, previews
from pbc.authoring.path import Lesson
from pbc.authoring.progress import path_export

PAGE = """---
title: A lesson
---

```{python}
#| label: fig-sketch
#| fig-cap: "A sketch."
#| fig-status: conceptual
#| fig-alt: "A box with an arrow."
plt.show()
```

Text.

```{python}
#| label: fig-result
#| fig-cap: "A result."
#| fig-status: simulated
#| fig-alt: >-
#|   A curve that falls
#|   to zero.
plt.show()
```

```{python}
#| label: fig-bare
#| fig-cap: "No status."
plt.show()
```
"""

SITE = Path(__file__).resolve().parents[2] / "site"


def lesson(preview: str = "", course: str = "mechanics") -> Lesson:
    return Lesson(
        page="lessons/mechanics/01-a/index.qmd",
        id="a",
        title="A",
        description="",
        strand="mechanics",
        order=1,
        difficulty=1,
        prerequisites=(),
        outside=(),
        course=course,
        methods=("simulation", "proofs"),
        outcomes=("x", "y"),
        related=(),
        preview=preview,
    )


def png(width: int, height: int) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (width, height), (200, 30, 30)).save(out, format="PNG")
    return out.getvalue()


def test_figure_cells_are_read_in_page_order_with_status_and_alt():
    cells = previews.figure_cells(PAGE)
    assert [cell.label for cell in cells] == ["fig-sketch", "fig-result", "fig-bare"]
    assert cells[1].status == "simulated"
    assert cells[1].alt == "A curve that falls to zero."
    assert cells[2].status == ""


def test_a_preview_names_a_figure_cell_with_a_status_and_alt_text():
    assert previews.problems("", PAGE) == []
    assert previews.problems("fig-result", PAGE) == []
    assert "not the label of a figure cell" in previews.problems("fig-missing", PAGE)[0]
    assert "no 'fig-status'" in previews.problems("fig-bare", PAGE)[0]


def test_scaling_gives_the_fixed_size_and_the_same_bytes_every_time():
    wide, tall = previews.scale(png(1200, 300)), previews.scale(png(300, 900))
    for scaled in (wide, tall):
        with Image.open(io.BytesIO(scaled)) as picture:
            assert picture.size == (previews.WIDTH, previews.HEIGHT)
    assert previews.scale(png(1200, 300)) == wide


def test_a_preview_is_lossless_webp_and_lighter_than_a_png():
    # A figure of exactly the preview size is not resampled, so the preview
    # must decode to the very pixels of the figure: the encoding that makes
    # the path page lighter (Issue #319) simplifies no figure.
    noise = Image.frombytes(
        "RGB",
        (previews.WIDTH, previews.HEIGHT),
        bytes(
            (i * 7919 + i // 3) % 251
            for i in range(previews.WIDTH * previews.HEIGHT * 3)
        ),
    )
    out = io.BytesIO()
    noise.save(out, format="PNG", compress_level=9)
    scaled = previews.scale(out.getvalue())
    with Image.open(io.BytesIO(scaled)) as picture:
        assert picture.format == "WEBP"
        assert picture.convert("RGB").tobytes() == noise.tobytes()
    plot = Image.new("RGB", (previews.WIDTH, previews.HEIGHT), "white")
    plot.paste((30, 90, 200), (20, 100, 300, 104))
    as_png = io.BytesIO()
    plot.save(as_png, format="PNG", compress_level=9)
    assert len(previews.scale(as_png.getvalue())) < len(as_png.getvalue())


def test_the_fallback_is_drawn_from_course_and_methods_only():
    drawing = previews.fallback(lesson())
    assert drawing == previews.fallback(lesson())
    assert "Classical mechanics" in drawing and "conceptual" in drawing
    assert drawing != previews.fallback(lesson(course="waves"))


def test_a_lesson_without_preview_gets_the_conceptual_fallback(tmp_path: Path):
    page = tmp_path / "lessons/mechanics/01-a/index.qmd"
    page.parent.mkdir(parents=True)
    page.write_text(PAGE, encoding="utf-8")
    fallback = previews.preview_of(lesson(), tmp_path)
    assert fallback.fallback and fallback.file == "previews/a.svg"
    assert fallback.alt.startswith("Preview, conceptual: ")
    chosen = previews.preview_of(lesson("fig-result"), tmp_path)
    assert chosen.source == "fig-result" and chosen.file == "previews/a.webp"
    assert chosen.alt == "Preview, simulated: A curve that falls to zero."
    with pytest.raises(ValueError, match="not the label of a figure cell"):
        previews.preview_of(lesson("fig-missing"), tmp_path)


def test_a_named_cell_that_drew_no_figure_fails_the_build(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="fig-result"):
        previews.figure_file(tmp_path, lesson("fig-result"), "fig-result")


def test_the_published_lessons_each_name_a_preview_cell_of_their_page():
    path = LearningPath.read(SITE)
    assert path.lessons
    for item in path.lessons:
        assert item.preview, item.id
        found = previews.problems(item.preview, (SITE / item.page).read_text("utf-8"))
        assert found == [], (item.id, found)
        assert previews.preview_of(item, SITE).source == item.preview


def test_the_export_names_the_preview_of_every_lesson():
    path = LearningPath.read(SITE)
    exported = path_export(path, SITE)["lessons"]
    for entry, item in zip(exported, path.lessons, strict=True):
        expected = previews.preview_of(item, SITE)
        assert entry["preview"] == {"alt": expected.alt, "src": expected.file}
    assert all("preview" not in entry for entry in path_export(path)["lessons"])  # type: ignore[union-attr]
