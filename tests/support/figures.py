"""The checks of a figure that declares its provenance (Issue #524), for the
unit tests of the lessons whose figures opt in; since F173 (Issue #531)
every figure of a dataset."""

import re

import matplotlib.pyplot as plt

from pbc.data import figure_provenance as portable
from pbc.data.plotting import check_figure
from pbc.experiment import encode
from support.experiments import page_of


def assert_declared(experiment, label: str, figure, status: str, residuals: bool):
    """The declared figure ``label`` of ``experiment`` (``figure`` is one
    drawing of it) states ``status`` once, keeps every figure convention,
    gives each legend entry a declared role, and its PNG carries exactly the
    record of the declaration and the card, with the visualization credit
    and the data credit the card requires, deterministically."""
    provenance = experiment.provenance[label]
    assert provenance.status == status
    assert check_figure(figure, residuals=residuals, declared=status) == []
    assert portable.check_roles(figure, provenance) == []
    card = portable.card_of(provenance.dataset)
    identity = experiment.identity(label)
    png = experiment.png(label)
    assert portable.check_png(png, provenance, card, identity) == []
    # The page's bytes are the encoder's for the declaration and the card:
    # the credit the card requires is painted, and nothing else differs.
    assert png == encode(
        experiment.figures[label],
        metadata=portable.metadata(provenance, card, identity),
        credit=portable.visible_credit(card, also=portable.also_cards(provenance)),
    )
    # The owner's choice (2026-11-14): the visualization credit, with the
    # data credit where the card shows it, in one line.
    credit = card["rights"]["figure_credit"]
    painted = portable.read_metadata(png)["pbc:visible-credit"]
    shown = credit["visible"] in ("required", "chosen")
    data = f" · {credit['short']}" if shown else ""
    further = [
        c["rights"]["figure_credit"]["short"]
        for c in portable.also_cards(provenance)
        if c["rights"]["figure_credit"]["visible"] in ("required", "chosen")
    ]
    rest = "\n" + " · ".join(further) if further else ""
    assert painted == portable.VISUALIZATION_PREFIX + data + rest


_OPTION = re.compile(r"^#\|\s*([a-z-]+):\s*(.*?)\s*$")


def figure_cells(lesson: str) -> dict[str, dict[str, str]]:
    """The options (``#|`` lines) of every figure cell of the lesson page
    ``lesson``, by label."""
    cells: dict[str, dict[str, str]] = {}
    for block in re.findall(r"```\{python\}\n(.*?)```", page_of(lesson), re.DOTALL):
        options = dict(
            match.groups()
            for line in block.splitlines()
            if (match := _OPTION.match(line))
        )
        if options.get("label", "").startswith("fig-"):
            cells[options["label"]] = options
    return cells


def dataset_figures(lesson: str) -> dict[str, dict[str, str]]:
    """The figure cells of ``lesson`` that name a dataset (``fig-dataset``
    or ``fig-model-of``), by label: since F173 (Issue #531) each declares
    its provenance."""
    return {
        label: options
        for label, options in figure_cells(lesson).items()
        if "fig-dataset" in options or "fig-model-of" in options
    }


def assert_cell_declared(
    experiment, lesson: str, label: str, *, residuals: bool = False
) -> None:
    """The figure ``label`` of ``lesson`` names a dataset, and its
    experiment declares the cell's status, dataset (or the dataset it
    models), and artifact, and draws it by the contract
    (``assert_declared``)."""
    options = dataset_figures(lesson)[label]
    provenance = experiment.provenance[label]
    if "fig-model-of" in options:
        assert provenance.model_of
        assert provenance.dataset == options["fig-model-of"]
    else:
        assert not provenance.model_of
        assert provenance.dataset == options["fig-dataset"]
    assert provenance.artifact == options.get("fig-artifact")
    figure = experiment.figures[label]()
    try:
        assert_declared(experiment, label, figure, options["fig-status"], residuals)
    finally:
        plt.close(figure)
