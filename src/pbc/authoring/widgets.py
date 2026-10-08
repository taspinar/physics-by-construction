"""Embedding an interactive widget in a lesson page.

A widget is a self-hosted ES module in ``site/widgets/`` that enhances a
static figure already in the page (``docs/authoring.md``, "Widgets"). Its
data is computed by an executed cell when the page is built and embedded in
the page as JSON, so that the widget needs no request and does no physics of
its own. The two helpers here write the data and the script tag.
"""

import json
from dataclasses import dataclass
from html import escape

from pbc.authoring.path import _page_being_built

# Compact JSON: a float is written in its shortest form, which reads back to
# the same float and is the same in every build.
_SEPARATORS = (",", ":")


def _raw_html(markup: str) -> str:
    """Markdown that passes ``markup`` to the page unchanged."""
    return f"```{{=html}}\n{markup}\n```"


def data_markup(widget_id: str, data: object) -> str:
    """The HTML element that carries ``data`` for the widget ``widget_id``.

    The JSON sits in a ``script`` element of type ``application/json``,
    which the browser neither runs nor shows. ``<`` is escaped, so the data
    cannot end the element early.
    """
    payload = json.dumps(data, separators=_SEPARATORS, allow_nan=False)
    payload = payload.replace("<", "\\u003c")
    return (
        f'<script type="application/json" id="{escape(widget_id)}-data">'
        f"{payload}</script>"
    )


def module_markup(module: str, depth: int) -> str:
    """The script element that loads the widget module ``module`` (a file
    name in ``site/widgets/``) from a page ``depth`` directories below the
    site root. The URL is relative, so it holds under any base path."""
    if "/" in module or not module.endswith(".js"):
        raise ValueError(f"a widget is a .js file in site/widgets/, got {module!r}")
    return (
        f'<script type="module" src="{"../" * depth}widgets/{escape(module)}"></script>'
    )


@dataclass(frozen=True)
class WidgetScript:
    """As the result of a code cell it renders the data and the script tag
    of a widget."""

    markup: str

    def _repr_markdown_(self) -> str:
        return _raw_html(self.markup)


def widget_data(widget_id: str, data: object) -> WidgetScript:
    """Embed ``data`` in the page for the widget with the id ``widget_id``.

    Call it from a cell with ``#| echo: false``; ``data`` must be JSON data
    (numbers, text, lists, dictionaries).
    """
    return WidgetScript(data_markup(widget_id, data))


def widget_module(module: str) -> WidgetScript:
    """Load the widget module ``module`` from ``site/widgets/`` on the page
    being built."""
    _site, page = _page_being_built()
    depth = page.count("/")
    return WidgetScript(module_markup(module, depth))
