import json
import re

import pytest

from pbc.authoring import widgets


def test_data_is_embedded_as_json_that_reads_back():
    data = {"a": [1.5, 2, 1e-9], "b": "text"}

    markup = widgets.data_markup("explorer", data)

    match = re.fullmatch(
        r'<script type="application/json" id="explorer-data">(.*)</script>', markup
    )
    assert match and json.loads(match.group(1)) == data


def test_data_cannot_end_its_element():
    markup = widgets.data_markup("w", {"text": "</script><b>"})

    assert markup.count("</script>") == 1
    payload = markup.removeprefix('<script type="application/json" id="w-data">')
    assert json.loads(payload.removesuffix("</script>")) == {"text": "</script><b>"}


def test_data_that_is_not_a_number_is_refused():
    with pytest.raises(ValueError):
        widgets.data_markup("w", {"x": float("nan")})


@pytest.mark.parametrize(
    "depth, source", [(0, "widgets/a.js"), (3, "../../../widgets/a.js")]
)
def test_the_module_url_is_relative_to_the_page(depth, source):
    assert widgets.module_markup("a.js", depth) == (
        f'<script type="module" src="{source}"></script>'
    )


@pytest.mark.parametrize("name", ["../a.js", "dir/a.js", "a.css", "a"])
def test_only_a_file_of_the_widget_directory_can_be_loaded(name):
    with pytest.raises(ValueError):
        widgets.module_markup(name, 2)


def test_a_cell_result_passes_the_markup_through_as_raw_html():
    result = widgets.WidgetScript("<p>x</p>")

    assert result._repr_markdown_() == "```{=html}\n<p>x</p>\n```"
