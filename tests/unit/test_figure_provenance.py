"""The portable provenance of a declared figure (F172, Issue #524): one
declaration and the dataset card give the PNG's metadata, the visible
credit a card requires, the caption's credit, and the legend's roles; a
figure that declares nothing keeps its bytes."""

import copy
import struct
import zlib
from io import BytesIO

import matplotlib
import matplotlib.pyplot as plt
import pytest

from pbc.data import figure_provenance as fp
from pbc.data.figure_provenance import RESIDUAL, FigureProvenance, role
from pbc.experiment import FIGURE_SETTINGS, PIXEL_RATIO, Experiment, encode

TESS = "tess-exoplanet-light-curves"
NIST = "nist-numisheet-dp980"
BAYREUTH = "bayreuth-rlc-impedance"
MIXED = FigureProvenance(
    status="processed",
    dataset=TESS,
    combines=("simulated",),
    processing="Normalised and folded; the fit: this lesson's code.",
)
ALONE = FigureProvenance(
    status="processed", dataset=NIST, processing="The record, unmodified."
)


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close("all")


def _measured_and_model(*, model_style="--", measured_style="none", roles=True):
    fig, (top, bottom) = plt.subplots(2, 1, sharex=True)
    (points,) = top.plot([0, 1, 2], [1, 0, 1], ls=measured_style, marker="o", label="m")
    (model,) = top.plot([0, 1, 2], [1, 0.1, 1], ls=model_style, label="fit")
    (rest,) = bottom.plot([0, 1, 2], [0, -0.1, 0], ls=":", label="m - fit")
    if roles:
        role(points, "processed")
        role(model, "simulated")
        role(rest, RESIDUAL)
    top.legend()
    bottom.legend()
    return fig


def _old_encode(draw):
    """The encoder of ``main`` before Issue #524, verbatim in what it does."""
    with matplotlib.rc_context():
        matplotlib.rcdefaults()
        matplotlib.rcParams.update(FIGURE_SETTINGS)
        figure = draw()
        try:
            output = BytesIO()
            figure.savefig(
                output,
                format="png",
                dpi=FIGURE_SETTINGS["figure.dpi"] * PIXEL_RATIO,
                bbox_inches="tight",
                facecolor=figure.get_facecolor(),
                edgecolor=figure.get_edgecolor(),
                metadata={"Software": None},
            )
        finally:
            plt.close(figure)
    return output.getvalue()


def _chunk_types(png: bytes) -> list[bytes]:
    found, at = [], 8
    while at < len(png):
        (length,) = struct.unpack(">I", png[at : at + 4])
        found.append(png[at + 4 : at + 8])
        at += 12 + length
    return found


# The figure that opts in, and every other figure.


def test_a_figure_that_declares_nothing_keeps_the_bytes_of_the_old_encoder():
    experiment = Experiment()
    experiment.figure("fig-plain", _measured_and_model)
    experiment.figure("fig-declared", _measured_and_model, provenance=MIXED)

    plain = experiment.png("fig-plain")
    assert plain == _old_encode(_measured_and_model) == encode(_measured_and_model)
    assert fp.read_metadata(plain) == {}
    assert experiment.provenance == {"fig-declared": MIXED}
    assert experiment.png("fig-declared") != plain


def test_the_declared_png_carries_the_record_of_the_declaration_and_the_card():
    experiment = Experiment()
    experiment.figure("fig-declared", _measured_and_model, provenance=MIXED)
    png = experiment.png("fig-declared")
    card = fp.card_of(TESS)
    identity = experiment.identity("fig-declared")

    found = fp.read_metadata(png)
    assert identity == f"{__name__}:fig-declared"
    assert found == fp.metadata(MIXED, card, identity)
    assert list(found) == list(fp.metadata(MIXED, card, identity))
    assert found["pbc:status"] == "processed"
    assert found["pbc:combines"] == "simulated"
    assert found["pbc:dataset"] == TESS
    assert found["pbc:figure"] == identity
    assert found["pbc:credit"] == card["rights"]["figure_credit"]["short"]
    assert found["pbc:attribution"] == " ".join(card["rights"]["attribution"].split())
    assert found["Source"] == f"https://doi.org/{card['source']['doi']}"
    assert "processed measurement with simulated models" in found["Description"]
    assert fp.check_png(png, MIXED, card, identity) == []
    # Deterministic: no date, no software, no author or copyright field.
    assert png == encode(
        _measured_and_model, metadata=fp.metadata(MIXED, card, identity)
    )
    assert not set(found) & set(fp.FORBIDDEN_KEYS)
    assert b"tIME" not in _chunk_types(png)


def test_a_record_that_differs_from_the_card_or_claims_ownership_is_reported():
    card = fp.card_of(TESS)
    identity = "m:fig-x"
    changed = copy.deepcopy(card)
    changed["rights"]["attribution"] = "Someone else."
    png = encode(_measured_and_model, metadata=fp.metadata(MIXED, changed, identity))
    assert any("pbc:attribution" in p for p in fp.check_png(png, MIXED, card, identity))

    owned = {**fp.metadata(MIXED, card, identity), "Copyright": "© the project"}
    png = encode(_measured_and_model, metadata=owned)
    problems = fp.check_png(png, MIXED, card, identity)
    assert "metadata holds 'Copyright'" in problems
    assert any("ownership wording" in p for p in problems)
    # Another identity or status is another figure.
    assert fp.check_png(png, ALONE, fp.card_of(NIST), identity)


def test_the_reader_reads_compressed_and_international_text():
    def chunk(kind: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(kind + data)
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"tEXt", b"a\0plain")
        + chunk(b"zTXt", b"b\0\0" + zlib.compress(b"packed"))
        + chunk(b"iTXt", b"c\0\0\0en\0\0" + "Rüther".encode())
        + chunk(b"iTXt", b"d\0\1\0\0\0" + zlib.compress("ü".encode()))
        + chunk(b"IEND", b"")
    )
    assert fp.read_metadata(png) == {
        "a": "plain",
        "b": "packed",
        "c": "Rüther",
        "d": "ü",
    }
    with pytest.raises(ValueError):
        fp.read_metadata(b"GIF89a")


# The visible credit.


def test_a_card_that_requires_a_visible_credit_gets_one_line_under_the_axes():
    drawn = []

    def draw():
        drawn.append(_measured_and_model())
        return drawn[-1]

    card = fp.card_of(NIST)
    line = fp.visible_credit(card)
    assert line == card["rights"]["figure_credit"]["short"]
    with_line = encode(draw, credit=line)
    texts = [t for t in drawn[-1].texts if t.get_gid() == fp.CREDIT_GID]
    assert [t.get_text() for t in texts] == [line]
    # Below the figure's lower edge, outside every panel.
    assert texts[0].get_position() == (0.0, 0.0) and texts[0].get_va() == "top"
    assert all(ax.get_position().y0 > 0 for ax in drawn[-1].axes)
    without = encode(draw)
    assert with_line != without
    assert fp.visible_credit(fp.card_of(TESS)) is None
    assert fp.visible_credit(fp.card_of(BAYREUTH)) is not None


def test_the_visualization_credit_names_the_project_only_as_the_visualization():
    card = fp.card_of(TESS)
    line = fp.visible_credit(card, visualization=True)
    assert line == (
        "Visualization: Physics by Construction · "
        + card["rights"]["figure_credit"]["short"]
    )
    assert fp.ownership_problems(line) == []
    assert (
        fp.metadata(MIXED, card, "m:f", visualization=True)["pbc:visible-credit"]
        == line
    )
    assert fp.VISUALIZATION_CREDIT is False, "the owner's choice (Issue #524)"


@pytest.mark.parametrize(
    "text",
    [
        "© Physics by Construction",
        "Data: our measurements",
        "Data: owned by the lesson",
        "Copyright 2026 Physics by Construction",
        "Data: Physics by Construction, TESS",
    ],
)
def test_ownership_wording_is_reported(text):
    assert fp.ownership_problems(text)


def test_an_attribution_that_mentions_copyright_law_is_not_ownership():
    for name in (TESS, NIST, BAYREUTH):
        attribution = fp.card_of(name)["rights"]["attribution"]
        assert fp.ownership_problems(attribution) == [], name


# The per-card rights check.


def test_the_three_pilot_cards_pass_the_rights_check():
    for name in (TESS, NIST, BAYREUTH):
        assert fp.credit_problems(fp.card_of(name)) == [], name


def _with_credit(name, **changes):
    card = copy.deepcopy(fp.card_of(name))
    card["rights"]["figure_credit"].update(changes)
    return card


def test_the_rights_check_reports_a_bad_credit():
    assert fp.credit_problems({"rights": {}}) == ["rights.figure_credit: missing"]
    cases = {
        "starts with 'Data: '": _with_credit(TESS, short="TESS, MAST"),
        "at most 100": _with_credit(TESS, short="Data: " + "x" * 100),
        "one line": _with_credit(TESS, short="Data: TESS,\n MAST"),
        "ownership": _with_credit(TESS, short="Data: our TESS light curve"),
        "visible: one of": _with_credit(TESS, visible="maybe"),
        "why the credit": _with_credit(TESS, source=" "),
        "a CC BY licence requires": _with_credit(BAYREUTH, visible="not-required"),
        "names the licence": _with_credit(BAYREUTH, short="Data: Danzer et al."),
    }
    for expected, card in cases.items():
        problems = fp.credit_problems(card)
        assert any(expected in p for p in problems), (expected, problems)
    card = copy.deepcopy(fp.card_of(TESS))
    card["rights"]["publication_of_figures"]["answer"] = "restricted"
    assert any("publication_of_figures" in p for p in fp.credit_problems(card))


def test_a_declaration_the_card_does_not_allow_is_refused():
    card = fp.card_of(NIST)
    measured = FigureProvenance(status="measured", dataset=NIST, processing="x")
    assert any("allows processed" in p for p in fp.declaration_problems(measured, card))
    assert any("declaration names" in p for p in fp.declaration_problems(MIXED, card))
    with pytest.raises(ValueError, match="allows processed"):
        Experiment().figure("fig-x", _measured_and_model, provenance=measured)
    with pytest.raises(ValueError):
        fp.metadata(measured, card, "m:fig-x")


@pytest.mark.parametrize(
    "arguments",
    [
        {"status": "simulated"},
        {"status": "conceptual"},
        {"combines": ("processed",)},
        {"combines": ("conceptual",)},
        {"combines": ("simulated", "simulated")},
        {"processing": "  "},
    ],
)
def test_a_declaration_names_a_measurement_and_what_it_combines(arguments):
    values = {"status": "processed", "dataset": TESS, "processing": "x", **arguments}
    with pytest.raises(ValueError):
        FigureProvenance(**values)


# The legend's roles.


def test_a_figure_whose_artists_carry_the_declared_roles_passes():
    assert fp.check_roles(_measured_and_model(), MIXED) == []


def test_the_roles_report_what_the_status_words_of_a_legend_used_to_show():
    assert any(
        "has no role" in p
        for p in fp.check_roles(_measured_and_model(roles=False), MIXED)
    )
    assert any(
        "is a solid line" in p
        for p in fp.check_roles(_measured_and_model(model_style="-"), MIXED)
    )
    assert any(
        "drawn as a model" in p
        for p in fp.check_roles(_measured_and_model(measured_style="--"), MIXED)
    )
    # A model in a figure that declares none, and a declared model not drawn.
    assert any("declares" in p for p in fp.check_roles(_measured_and_model(), ALONE))
    fig, ax = plt.subplots()
    role(ax.plot([0, 1], [0, 1], label="m")[0], "processed")
    ax.legend()
    assert fp.check_roles(fig, ALONE) == []
    assert any("no legend entry" in p for p in fp.check_roles(fig, MIXED))


def test_a_legend_that_drops_an_entry_is_reported():
    fig, ax = plt.subplots()
    for k in range(2):
        role(ax.plot([0, 1], [k, k], label=f"part {k}")[0], "processed")
    ax.legend(handles=ax.get_lines()[:1])
    assert any("the legend shows" in p for p in fp.check_roles(fig, ALONE))


def test_an_unknown_role_is_refused():
    with pytest.raises(ValueError):
        role(object(), "natural")


# The caption.


def test_the_caption_gets_the_combined_statuses_the_short_credit_and_the_details():
    card = fp.card_of(TESS)
    meta = fp.metadata(MIXED, card, "m:fig-x")
    after, end = fp.caption_html(meta, card)
    assert after == (
        ' <span class="figure-combines" data-combines="simulated">'
        "with simulated models</span>"
    )
    short = card["rights"]["figure_credit"]["short"]
    assert f'<span class="figure-credit">{short}</span>' in end
    assert '<details class="figure-provenance"><summary>' in end
    assert end.endswith("</details>")
    assert "Includes data collected with the TESS mission" in end
    assert f'href="https://doi.org/{card["source"]["doi"]}"' in end
    assert "<code>m:fig-x</code>" in end
    after, _ = fp.caption_html(fp.metadata(ALONE, fp.card_of(NIST), "m:f"), card)
    assert after == ""


def test_the_examples_are_the_page_figure_and_the_one_with_the_visualization_credit(
    tmp_path,
):
    experiment = Experiment()
    experiment.figure("fig-declared", _measured_and_model, provenance=MIXED)
    experiment.figure("fig-plain", _measured_and_model)

    written = fp.examples(tmp_path, [experiment])

    assert [p.name for p in written] == [
        "fig-declared.png",
        "fig-declared-visualization-credit.png",
    ]
    assert written[0].read_bytes() == experiment.png("fig-declared")
    branded = fp.read_metadata(written[1].read_bytes())
    assert branded["pbc:visible-credit"].startswith(fp.VISUALIZATION_PREFIX)
