"""The checks of a figure that declares its provenance (Issue #524), for the
unit tests of the lessons whose figures opt in."""

from pbc.data import figure_provenance as portable
from pbc.data.plotting import check_figure
from pbc.experiment import encode


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
        credit=portable.visible_credit(card),
    )
    # The owner's choice (2026-11-14): the visualization credit, with the
    # data credit where the card shows it, in one line.
    credit = card["rights"]["figure_credit"]
    painted = portable.read_metadata(png)["pbc:visible-credit"]
    shown = credit["visible"] in ("required", "chosen")
    data = f" · {credit['short']}" if shown else ""
    assert painted == portable.VISUALIZATION_PREFIX + data
