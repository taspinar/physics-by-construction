"""The post-render step completes the caption of a declared figure from its
PNG's record and its card, refuses a caption or a card that disagrees, and
leaves every other figure alone (Issue #524)."""

import copy
from pathlib import Path

import matplotlib.pyplot as plt
import pytest
import yaml

from pbc.authoring.figure_credits import InvalidFigure, annotate
from pbc.data import REGISTRY_DIR
from pbc.data import figure_provenance as fp
from pbc.experiment import encode

DATASET = "tess-exoplanet-light-curves"
DECLARED = fp.FigureProvenance(
    status="processed",
    dataset=DATASET,
    combines=("simulated",),
    processing="Folded and fitted by this lesson's code.",
)
IDENTITY = "pbc.example:fig-declared"


def _draw():
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    return fig


def _figure(src: str, status: str = "processed", dataset: str = DATASET) -> str:
    return (
        '<figure class="quarto-float"><div><img src="'
        + src
        + '" alt="a figure" width="10" height="10"></div>'
        '<figcaption id="c">Figure&nbsp;1: <span class="figure-status"'
        f' data-status="{status}" data-dataset="{dataset}">{status}</span>'
        " The caption.</figcaption></figure>"
    )


@pytest.fixture
def page_dir(tmp_path: Path) -> Path:
    images = tmp_path / "index_files" / "figure-html"
    images.mkdir(parents=True)
    card = fp.card_of(DATASET)
    (images / "declared.png").write_bytes(
        encode(_draw, metadata=fp.metadata(DECLARED, card, IDENTITY))
    )
    (images / "plain.png").write_bytes(encode(_draw))
    return tmp_path


def test_a_declared_figure_gets_its_combined_statuses_credit_and_details(page_dir):
    html = "<main>" + _figure("index_files/figure-html/declared.png") + "</main>"

    done, count = annotate(html, page_dir)

    assert count == 1
    card = fp.card_of(DATASET)
    after, end = fp.caption_html(fp.metadata(DECLARED, card, IDENTITY), card)
    assert f">processed</span>{after} The caption." in done
    assert done.endswith(f"The caption.{end}</figcaption></figure></main>")
    # Once only.
    assert annotate(done, page_dir) == (done, 0)


def test_a_figure_without_a_record_and_a_page_without_figures_are_unchanged(
    page_dir,
):
    html = _figure("index_files/figure-html/plain.png") + _figure("missing.png")
    assert annotate(html, page_dir) == (html, 0)
    assert annotate("<p>No figure.</p>", page_dir) == ("<p>No figure.</p>", 0)


@pytest.mark.parametrize(
    ("status", "dataset", "text"),
    [
        ("calibrated", DATASET, "data-status"),
        ("processed", "nist-numisheet-dp980", "data-dataset"),
    ],
)
def test_a_caption_that_disagrees_with_the_png_fails_the_build(
    page_dir, status, dataset, text
):
    html = _figure("index_files/figure-html/declared.png", status, dataset)
    with pytest.raises(InvalidFigure, match=text):
        annotate(html, page_dir)


def test_a_png_whose_painted_line_is_not_the_cards_fails_the_build(tmp_path):
    images = tmp_path / "index_files" / "figure-html"
    images.mkdir(parents=True)
    card = fp.card_of(DATASET)
    # Drawn without the visualization credit the owner chose (Issue #524).
    (images / "declared.png").write_bytes(
        encode(
            _draw, metadata=fp.metadata(DECLARED, card, IDENTITY, visualization=False)
        )
    )
    html = _figure("index_files/figure-html/declared.png")
    with pytest.raises(InvalidFigure, match="pbc:visible-credit"):
        annotate(html, tmp_path)


def test_a_card_that_no_longer_gives_the_record_fails_the_build(page_dir, tmp_path):
    registry = tmp_path / "registry"
    registry.mkdir()
    card = copy.deepcopy(fp.card_of(DATASET))
    card["rights"]["figure_credit"]["short"] = "Data: someone else"
    (registry / f"{DATASET}.yaml").write_text(yaml.safe_dump(card))
    html = _figure("index_files/figure-html/declared.png")
    with pytest.raises(InvalidFigure, match="pbc:credit"):
        annotate(html, page_dir, registry)
    with pytest.raises(InvalidFigure, match="no card"):
        annotate(html, page_dir, tmp_path / "empty")
    assert (REGISTRY_DIR / f"{DATASET}.yaml").is_file()
