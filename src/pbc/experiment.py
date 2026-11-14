"""The experiment of a lesson: its numbers, tables, and figures, outside the page.

Every lesson has an experiment module, ``pbc.<course>.experiments.<name>``
(ADR 016 decision 2, ``docs/authoring.md``, "The experiment of a lesson").
Its ``run()`` computes what the page shows and returns an ``Experiment``
that records it by name. The page's cells call ``run()`` and show the
result; a learner runs the module as a program, without the website:

    uv run --locked --no-dev python -m pbc.mechanics.experiments.kinematics out

which writes every figure as ``out/<label>.png``, the data of an interactive
figure as ``out/<name>.json``, and every number and table cell as the text
the page shows into ``out/results.json``.

One encoder, ``encode``, produces the figure file of both: the page shows
the bytes it returns and the program writes them, so the figure of the
published page and the learner's file are the same file. It draws under
fixed Matplotlib settings, never the caller's, and writes no metadata,
except for a figure that declares its provenance (``Experiment.figure``
with ``provenance``): its deterministic record, from the declaration and
the dataset card.
"""

from __future__ import annotations

import argparse
import json
import struct
from collections.abc import Callable, Iterable, Iterator, Sequence
from contextlib import contextmanager, redirect_stdout
from dataclasses import dataclass, field
from io import BytesIO, StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Any

import matplotlib

if TYPE_CHECKING:
    from matplotlib.figure import Figure

    from pbc.authoring.tables import Column, ResultTable
    from pbc.data.figure_provenance import FigureProvenance

# The settings a figure is drawn with: Matplotlib's defaults, and the size
# and resolution Quarto's kernel gives a figure of an HTML page, so that a
# figure keeps the size it had when the page's inline backend captured it.
FIGURE_SETTINGS = {"figure.figsize": (7.0, 5.0), "figure.dpi": 96.0}
# The page shows a figure at half its pixel size, as Quarto's "retina"
# format does: the file holds twice the resolution of the screen.
PIXEL_RATIO = 2
RESULTS_FILE = "results.json"


def encode(
    draw: Callable[[], Figure],
    *,
    metadata: dict[str, str] | None = None,
    credit: str | None = None,
) -> bytes:
    """The PNG of the figure ``draw`` returns, drawn under ``FIGURE_SETTINGS``.

    The figure is cropped to what it draws, written at ``PIXEL_RATIO``
    times the resolution of the settings with its own face and edge colours
    and without metadata, and closed. The same figure gives the same bytes on every
    call, whatever settings the caller has.

    A figure that declares its provenance (``Experiment.figure`` with
    ``provenance``, Issue #524) passes the text chunks of ``metadata``,
    written in their order and nothing else, and the one line ``credit``
    its card requires visible, painted under the figure
    (``pbc.data.figure_provenance``). Without them the bytes are those of
    every other figure.
    """
    import matplotlib.pyplot as plt

    with matplotlib.rc_context():
        matplotlib.rcdefaults()
        matplotlib.rcParams.update(FIGURE_SETTINGS)
        figure = draw()
        try:
            if credit is not None:
                from pbc.data.figure_provenance import paint_credit

                paint_credit(figure, credit)
            output = BytesIO()
            figure.savefig(
                output,
                format="png",
                # Fixed, never the figure's own: a screen backend such as
                # macOS's doubles a figure's dpi on a high-resolution display.
                dpi=FIGURE_SETTINGS["figure.dpi"] * PIXEL_RATIO,
                bbox_inches="tight",
                facecolor=figure.get_facecolor(),
                edgecolor=figure.get_edgecolor(),
                metadata={"Software": None, **(metadata or {})},
            )
        finally:
            plt.close(figure)
    return output.getvalue()


def png_size(png: bytes) -> tuple[int, int]:
    """The width and height in pixels of the PNG ``png``."""
    if png[:8] != b"\x89PNG\r\n\x1a\n" or png[12:16] != b"IHDR":
        raise ValueError("not a PNG file")
    width, height = struct.unpack(">II", png[16:24])
    return width, height


@dataclass(frozen=True)
class FigureImage:
    """As the result of a code cell it shows the PNG at its size on the page."""

    png: bytes

    def _repr_mimebundle_(
        self, include: Any = None, exclude: Any = None
    ) -> tuple[dict, dict]:
        width, height = png_size(self.png)
        size = {"width": width // PIXEL_RATIO, "height": height // PIXEL_RATIO}
        return {"image/png": self.png}, {"image/png": size}


@dataclass(frozen=True)
class Markdown:
    """As the result of a code cell it shows the Markdown text."""

    text: str

    def _repr_markdown_(self) -> str:
        return self.text


@dataclass(frozen=True)
class _Table:
    rows: tuple[tuple[object, ...], ...]
    columns: tuple[Column, ...]
    caption: str

    def text(self) -> dict:
        """The table as the page shows it: header labels and cell texts."""
        return {
            "caption": self.caption,
            "columns": [
                f"{name} ({unit})" if unit else name for name, unit, _ in self.columns
            ],
            "rows": [
                [
                    "" if value is None else format(value, spec)
                    for value, (_, _, spec) in zip(row, self.columns, strict=True)
                ]
                for row in self.rows
            ],
        }


@dataclass
class Experiment:
    """What a lesson's experiment computed, by name.

    ``number`` records a number with the format the page shows it in,
    ``table`` a result table, ``figure`` a figure by the label of its cell,
    ``widget`` the data of an interactive figure, ``capture`` what a block
    prints, ``display`` the Markdown of a display object such as a replayed
    run. The page reads them back (``experiment[name]``, ``table``, ``show``,
    ``widget``, ``output``, ``display``); ``write`` puts them into a
    directory.
    """

    numbers: dict[str, str] = field(default_factory=dict)
    tables: dict[str, _Table] = field(default_factory=dict)
    figures: dict[str, Callable[[], Figure]] = field(default_factory=dict)
    widgets: dict[str, object] = field(default_factory=dict)
    outputs: dict[str, str] = field(default_factory=dict)
    displays: dict[str, str] = field(default_factory=dict)
    provenance: dict[str, FigureProvenance] = field(default_factory=dict)
    _encoded: dict[str, bytes] = field(default_factory=dict, repr=False)

    def _new(self, kind: str, name: str, names: Iterable[str]) -> None:
        if name in names:
            raise ValueError(f"the experiment already has a {kind} {name!r}")

    def number(self, name: str, value: object, spec: str = "") -> str:
        """Record ``value`` formatted with ``spec``, as the page shows it, and
        return that text."""
        self._new("number", name, self.numbers)
        self.numbers[name] = format(value, spec)
        return self.numbers[name]

    def table(
        self,
        name: str,
        rows: Iterable[Sequence[object]] | None = None,
        columns: Sequence[Column] | None = None,
        caption: str | None = None,
    ) -> ResultTable:
        """With ``rows``, ``columns`` and ``caption``, record the table
        ``name``; return the table ``name`` as the page shows it."""
        from pbc.authoring.tables import table

        if rows is not None:
            if columns is None or caption is None:
                raise ValueError("a new table needs its columns and its caption")
            self._new("table", name, self.tables)
            self.tables[name] = _Table(
                tuple(tuple(row) for row in rows), tuple(columns), caption
            )
        recorded = self.tables[name]
        return table(recorded.rows, recorded.columns, recorded.caption)

    def figure(
        self,
        label: str,
        draw: Callable[[], Figure],
        provenance: FigureProvenance | None = None,
    ) -> None:
        """Record the figure that ``draw`` returns under the label of the
        page's cell, such as ``fig-ball-thrown-up``.

        With ``provenance`` the figure opts in to portable provenance
        (Issue #524): its PNG carries the declaration and its card's credit
        as metadata, and the line of credit the card requires visible.
        """
        if not label.startswith("fig-"):
            raise ValueError(f"a figure label starts with 'fig-': {label!r}")
        self._new("figure", label, self.figures)
        if provenance is not None:
            from pbc.data.figure_provenance import card_of, declaration_problems

            problems = declaration_problems(provenance, card_of(provenance.dataset))
            if problems:
                raise ValueError(f"{label}: " + "; ".join(problems))
            self.provenance[label] = provenance
        self.figures[label] = draw

    def identity(self, label: str) -> str:
        """The figure ``label`` as ``<module of its draw function>:<label>``."""
        draw = self.figures[label]
        return f"{getattr(draw, 'func', draw).__module__}:{label}"

    def widget(self, name: str, data: object = None) -> object:
        """With ``data``, record the JSON data of the widget ``name``; return
        the data of the widget ``name``."""
        if data is not None:
            self._new("widget", name, self.widgets)
            self.widgets[name] = data
        return self.widgets[name]

    @contextmanager
    def capture(self, name: str) -> Iterator[None]:
        """Record what the block prints as the output ``name``, the text a
        cell of the page prints."""
        self._new("output", name, self.outputs)
        printed = StringIO()
        with redirect_stdout(printed):
            yield
        self.outputs[name] = printed.getvalue()

    def output(self, name: str) -> str:
        """The text the block recorded as ``name`` printed."""
        return self.outputs[name]

    def display(self, name: str, shown: object = None) -> Markdown:
        """With ``shown``, an object with ``_repr_markdown_``, record its
        Markdown as ``name``; return the Markdown ``name`` as the result of
        the page's cell."""
        if shown is not None:
            self._new("display", name, self.displays)
            self.displays[name] = shown._repr_markdown_()  # type: ignore[attr-defined]
        return Markdown(self.displays[name])

    def __getitem__(self, name: str) -> str:
        return self.numbers[name]

    def png(self, label: str) -> bytes:
        """The PNG of the figure ``label``, encoded once."""
        if label not in self._encoded:
            provenance = self.provenance.get(label)
            if provenance is None:
                self._encoded[label] = encode(self.figures[label])
            else:
                from pbc.data import figure_provenance as portable

                card = portable.card_of(provenance.dataset)
                visualization = portable.VISUALIZATION_CREDIT
                self._encoded[label] = encode(
                    self.figures[label],
                    metadata=portable.metadata(
                        provenance,
                        card,
                        self.identity(label),
                        visualization=visualization,
                    ),
                    credit=portable.visible_credit(card, visualization=visualization),
                )
        return self._encoded[label]

    def show(self, label: str) -> FigureImage:
        """The figure ``label`` as the result of the page's cell."""
        return FigureImage(self.png(label))

    def results(self) -> dict:
        """Every number and table as the text the page shows."""
        return {
            "numbers": dict(self.numbers),
            "tables": {name: table.text() for name, table in self.tables.items()},
            "figures": [f"{label}.png" for label in self.figures],
            "widgets": [f"{name}.json" for name in self.widgets],
            "outputs": dict(self.outputs),
            "displays": dict(self.displays),
        }

    def write(self, directory: Path) -> list[Path]:
        """Write every figure, the data of every widget, and the results file
        into ``directory``; return the files written."""
        directory.mkdir(parents=True, exist_ok=True)
        written = []
        for label in self.figures:
            path = directory / f"{label}.png"
            path.write_bytes(self.png(label))
            written.append(path)
        for name, data in self.widgets.items():
            path = directory / f"{name}.json"
            path.write_text(json.dumps(data) + "\n", encoding="utf-8")
            written.append(path)
        path = directory / RESULTS_FILE
        path.write_text(
            json.dumps(self.results(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        written.append(path)
        return written


def main(run: Callable[[], Experiment], argv: Sequence[str] | None = None) -> None:
    """Run a lesson's experiment as a program: ``python -m <module> <directory>``."""
    parser = argparse.ArgumentParser(
        description="Run the experiment of a lesson and write its figures and"
        f" numbers ({RESULTS_FILE}) into a directory."
    )
    parser.add_argument("directory", type=Path, help="where to write the results")
    arguments = parser.parse_args(argv)
    # Without a screen: the figures are written, never shown.
    matplotlib.use("agg", force=True)
    for path in run().write(arguments.directory):
        print(path)
