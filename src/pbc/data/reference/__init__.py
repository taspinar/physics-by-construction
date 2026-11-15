"""Reference figures of the feasibility spikes (F50).

Each module reads a dataset from its committed sample or a downloaded copy and
builds one figure (``make_figure``) whose status its dossier states.
Figures are regenerated, never committed (invariant I6)::

    uv run python -m pbc.data.reference gw150914-strain --out figure.png

Since F173 (Issue #531) a reference figure paints no status and no credit:
the module declares its provenance as ``REFERENCE``, a
``pbc.data.figure_provenance.FigureProvenance`` of its card, and
``reference_png`` writes the figure through the one encoder with the record
and the line of credit of the card, as a lesson figure that declares its
provenance.
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

REFERENCE_LABEL = "reference-figure"


def identity(module: ModuleType) -> str:
    """The reference figure of ``module`` as ``<module>:reference-figure``."""
    return f"{module.__name__}:{REFERENCE_LABEL}"


def reference_png(module: ModuleType, data_dir: Path) -> bytes:
    """The PNG of the reference figure of ``module`` drawn from ``data_dir``,
    with the provenance record its ``REFERENCE`` and its card give."""
    from pbc.data import figure_provenance as portable
    from pbc.experiment import encode

    provenance = module.REFERENCE
    card = portable.card_of(provenance.dataset)
    return encode(
        lambda: module.make_figure(data_dir),
        metadata=portable.metadata(provenance, card, identity(module)),
        credit=portable.visible_credit(card, also=portable.also_cards(provenance)),
    )
