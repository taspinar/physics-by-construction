"""The portable provenance of a declared figure (F172, Issue #524): one
declaration and the dataset card give the PNG's metadata, the visible
credit a card requires, the caption's credit, and the legend's roles; a
figure that declares nothing keeps its bytes."""

import copy
import re
import struct
import subprocess
import sys
import zlib
from io import BytesIO

import matplotlib
import matplotlib.pyplot as plt
import pytest

from pbc.data import figure_provenance as fp
from pbc.data.figure_provenance import RESIDUAL, FigureProvenance, role
from pbc.experiment import (
    FIGURE_SETTINGS,
    PIXEL_RATIO,
    Experiment,
    encode,
    png_size,
)

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
    assert (
        found["pbc:visible-credit"]
        == "Visualization: Physics by Construction · Data: NASA TESS / MAST"
    )
    assert png == encode(
        _measured_and_model,
        metadata=fp.metadata(MIXED, card, identity),
        credit=found["pbc:visible-credit"],
    )
    assert not set(found) & set(fp.FORBIDDEN_KEYS)
    assert b"tIME" not in _chunk_types(png)


def test_the_program_writes_the_pages_declared_png_byte_for_byte(tmp_path):
    # Run as a program (python -m), Python names the experiment's module
    # '__main__'; the record names it as it is imported, so the learner's
    # file and the page's are the same bytes (the e2e reproduction check).
    module = "pbc.electromagnetism.experiments.rlc_circuit_measurements"
    subprocess.run(
        [sys.executable, "-m", module, str(tmp_path)],
        check=True,
        capture_output=True,
    )
    from pbc.electromagnetism.experiments import rlc_circuit_measurements

    page = rlc_circuit_measurements.run().png("fig-impedance-fit")
    written = (tmp_path / "fig-impedance-fit.png").read_bytes()
    assert fp.read_metadata(written)["pbc:figure"] == f"{module}:fig-impedance-fit"
    assert written == page


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
    assert line == (
        "Visualization: Physics by Construction · "
        + card["rights"]["figure_credit"]["short"]
    )
    with_line = encode(draw, credit=line)
    texts = [t for t in drawn[-1].texts if t.get_gid() == fp.CREDIT_GID]
    assert [t.get_text() for t in texts] == [line]
    # Below the figure's lower edge, outside every panel, from the left edge
    # of what the figure draws (Issue #546).
    x, y = texts[0].get_position()
    assert 0.0 < x < 0.1 and y == 0.0 and texts[0].get_va() == "top"
    assert all(ax.get_position().y0 > 0 for ax in drawn[-1].axes)
    without = encode(draw)
    assert with_line != without
    # The type size and grey of the figure credits; no box.
    assert texts[0].get_fontsize() == 7 and texts[0].get_bbox_patch() is None
    assert texts[0].get_color() == "0.25"
    assert fp.visible_credit(fp.card_of(BAYREUTH)).endswith(
        fp.card_of(BAYREUTH)["rights"]["figure_credit"]["short"]
    )
    # Without the visualization credit, only the credit the card requires.
    assert (
        fp.visible_credit(card, visualization=False)
        == (card["rights"]["figure_credit"]["short"])
    )
    assert fp.visible_credit(fp.card_of(TESS), visualization=False) == (
        "Data: NASA TESS / MAST"
    )
    hidden = _with_credit(TESS, visible="not-required")
    assert fp.visible_credit(hidden, visualization=False) is None
    assert fp.visible_credit(hidden) == fp.VISUALIZATION_PREFIX


def _narrow_language_figure():
    """A figure of the figure language's width (F171), one panel."""
    from pbc.figure_language import figsize, figure_style

    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line"))
        (line,) = ax.plot([0, 1, 2], [1, 0, 1], marker="o", ls="none", label="m")
        role(line, "processed")
        ax.set_xlabel("time [s]")
        ax.set_ylabel("flux [1]")
    return fig


def test_a_credit_longer_than_the_figure_wraps_within_its_width():
    # Issue #546: a credit line wider than the figure breaks onto further
    # lines inside the figure's width, so the page does not scale the chart
    # and its labels down for it.
    drawn = []

    def draw():
        drawn.append(_narrow_language_figure())
        return drawn[-1]

    card = fp.card_of(BAYREUTH)
    line = fp.visible_credit(card, also=(fp.card_of(TESS),))
    long_word = "https://example.org/" + "a" * 120
    credit = f"{line} · {long_word}"
    bare = encode(draw)
    painted = encode(draw, credit=credit)
    width, height = png_size(bare)
    # The same width as the figure without a credit, and taller: the credit
    # takes further lines, not width.
    assert png_size(painted)[0] == width
    assert png_size(painted)[1] > height
    # In one line it would be wider than the figure.
    fig = drawn[-1]
    texts = [t for t in fig.texts if t.get_gid() == fp.CREDIT_GID]
    assert len(texts) == 1
    shown = texts[0].get_text()
    # Only line breaks added: the words, and the word longer than a line,
    # are all there, in order.
    assert shown != credit
    assert shown.split()[: len(line.split())] == line.split()
    assert re.sub(r"\s", "", shown) == re.sub(r"\s", "", credit)
    assert long_word not in shown and long_word in shown.replace("\n", "")
    # The further card's credit keeps its own line.
    further = line.split("\n")[1]
    assert any(row.startswith(further) for row in shown.split("\n"))
    assert len(shown.splitlines()) > len(credit.splitlines())
    # The page shows it at the same width and the same scale on every width.
    from pbc.figure_audit import PHONE_WIDTH, SMALL_PHONE_WIDTH

    for column in (760, PHONE_WIDTH, SMALL_PHONE_WIDTH):
        bare_scale = min(1.0, column / (width // PIXEL_RATIO))
        painted_scale = min(1.0, column / (png_size(painted)[0] // PIXEL_RATIO))
        assert painted_scale == bare_scale


def test_the_credit_of_em8s_pilot_figure_takes_no_width():
    # The case of Issue #546: EM8's figure of the figure language grew from
    # 404 to 621 CSS px with its credit line, and the page scaled it down.
    from pbc.electromagnetism.experiments import rlc_circuit_measurements

    experiment = rlc_circuit_measurements.run()
    for label in experiment.provenance:
        bare = encode(experiment.figures[label])
        assert png_size(experiment.png(label))[0] == png_size(bare)[0], label


def test_a_credit_that_fits_stays_one_line():
    drawn = []

    def draw():
        drawn.append(_narrow_language_figure())
        return drawn[-1]

    encode(draw, credit="Visualization: Physics by Construction")
    texts = [t for t in drawn[-1].texts if t.get_gid() == fp.CREDIT_GID]
    assert [t.get_text() for t in texts] == ["Visualization: Physics by Construction"]


def test_the_visualization_credit_names_the_project_only_as_the_visualization():
    # The owner's choice on Issue #524 (2026-11-14): with subtle branding.
    assert fp.VISUALIZATION_CREDIT is True
    # A card whose terms ask for no visible credit, which the project shows
    # by choice (TESS, public domain; the owner's review of 2026-11-14):
    # the branding and the data source in one line.
    card = fp.card_of(TESS)
    assert card["rights"]["figure_credit"]["visible"] == "chosen"
    line = fp.visible_credit(card)
    assert line == "Visualization: Physics by Construction · Data: NASA TESS / MAST"
    assert fp.ownership_problems(line) == []
    assert fp.metadata(MIXED, card, "m:f")["pbc:visible-credit"] == line
    # Cards whose terms ask for one: one line, the branding and the data.
    for dataset in (NIST, BAYREUTH):
        other = fp.card_of(dataset)
        assert other["rights"]["figure_credit"]["visible"] == "required"
        combined = fp.visible_credit(other)
        assert combined == (
            f"{fp.VISUALIZATION_PREFIX} · {other['rights']['figure_credit']['short']}"
        )
        assert "\n" not in combined and fp.ownership_problems(combined) == []


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


def test_a_residual_needs_a_measurement_in_the_figure():
    """A figure of a measurement may draw the misfit of a fit without the
    model (EM9's wideband figure, PR #540); a model alone may not."""
    fig, ax = plt.subplots()
    role(ax.plot([0, 1], [0, 1], label="m")[0], "processed")
    role(ax.plot([0, 1], [1, 0], label="misfit")[0], RESIDUAL)
    ax.legend()
    assert fp.check_roles(fig, ALONE) == []
    model = FigureProvenance(
        status="simulated", dataset=ALONE.dataset, model_of=True, processing="fit"
    )
    fig, ax = plt.subplots()
    role(ax.plot([0, 1], [0, 1], label="fit", ls="--")[0], "simulated")
    role(ax.plot([0, 1], [1, 0], label="misfit")[0], RESIDUAL)
    ax.legend()
    assert any("declares" in p for p in fp.check_roles(fig, model))


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
    assert (
        "<dt>On the image</dt><dd>Visualization: Physics by Construction"
        " · Data: NASA TESS / MAST</dd>"
    ) in end
    after, _ = fp.caption_html(fp.metadata(ALONE, fp.card_of(NIST), "m:f"), card)
    assert after == ""


def test_the_examples_are_the_page_figure_and_the_one_without_the_visualization_credit(
    tmp_path,
):
    experiment = Experiment()
    experiment.figure("fig-declared", _measured_and_model, provenance=MIXED)
    experiment.figure("fig-plain", _measured_and_model)

    written = fp.examples(tmp_path, [experiment])

    assert [p.name for p in written] == [
        "fig-declared.png",
        "fig-declared-without-visualization-credit.png",
    ]
    assert written[0].read_bytes() == experiment.png("fig-declared")
    branded = fp.read_metadata(written[0].read_bytes())
    assert branded["pbc:visible-credit"] == fp.visible_credit(fp.card_of(TESS))
    plain = fp.read_metadata(written[1].read_bytes())
    assert plain["pbc:visible-credit"] == "Data: NASA TESS / MAST"


# --- The rollout (F173, Issue #531) -----------------------------------------

LYCOPODIUM = "lycopodium-spore-diffraction"
KAMCHATKA = "kamchatka-2025-tsunami-inputs"
HALO = FigureProvenance(
    status="simulated",
    dataset=LYCOPODIUM,
    model_of=True,
    processing="The halo of the lesson's model at the measured diameters.",
)


def test_every_card_with_a_go_passes_the_rights_check_of_its_figure_credit():
    from pbc.data import REGISTRY_DIR
    from pbc.data.card import load_card, validate_card

    go = [
        card
        for path in sorted(REGISTRY_DIR.glob("*.yaml"))
        if ((card := load_card(path)).get("decision") or {}).get("value") == "go"
    ]
    assert len(go) >= 19
    for card in go:
        assert fp.credit_problems(card) == [], card["id"]
        # A CC BY card and a card whose terms ask for the credit paint it.
        visible = card["rights"]["figure_credit"]["visible"]
        assert visible in fp.PAINTED, card["id"]
    card = copy.deepcopy(go[0])
    del card["rights"]["figure_credit"]
    assert "rights.figure_credit: missing" in validate_card(card)


@pytest.mark.parametrize(
    "arguments",
    [
        {"status": "processed", "model_of": True},
        {"status": "simulated", "model_of": True, "artifact": "modelled-reference"},
        {"status": "simulated"},
    ],
)
def test_a_simulated_declaration_shows_a_modelled_artifact_or_models_the_dataset(
    arguments,
):
    with pytest.raises(ValueError):
        FigureProvenance(dataset=LYCOPODIUM, processing="p", **arguments)


def test_a_model_of_the_dataset_names_it_as_such_in_its_record():
    card = fp.card_of(LYCOPODIUM)
    assert fp.declaration_problems(HALO, card) == []
    meta = fp.metadata(HALO, card, "m:fig-halo")
    assert meta["pbc:dataset"] == "" and meta["pbc:model-of"] == LYCOPODIUM
    assert list(meta).index("pbc:model-of") == list(meta).index("pbc:dataset") + 1
    assert fp.dataset_of(meta) == LYCOPODIUM
    assert meta["Description"].startswith("Status: simulation modelled on the dataset.")
    # A figure of the dataset itself has no such key: the pilot's records.
    assert "pbc:model-of" not in fp.metadata(MIXED, fp.card_of(TESS), "m:f")
    assert fp.dataset_of(fp.metadata(MIXED, fp.card_of(TESS), "m:f")) == TESS


def test_a_simulated_figure_of_a_modelled_artifact_is_allowed_where_the_card_says():
    card = fp.card_of(KAMCHATKA)
    modelled = FigureProvenance(
        status="simulated",
        dataset=KAMCHATKA,
        artifact="modelled-reference",
        processing="The model's field.",
    )
    assert fp.declaration_problems(modelled, card) == []
    measured_artifact = FigureProvenance(
        status="simulated",
        dataset=KAMCHATKA,
        artifact="processed-measured",
        processing="The model's field.",
    )
    assert any(
        "status 'simulated'" in p
        for p in fp.declaration_problems(measured_artifact, card)
    )


def test_a_panel_without_a_legend_shows_its_roles_by_its_drawn_artists():
    fig, ax = plt.subplots()
    image = ax.imshow([[0, 1], [1, 0]])
    assert any("no legend entry" in p for p in fp.check_roles(fig, ALONE))
    role(image, "processed")
    assert fp.check_roles(fig, ALONE) == []
    role(image, "simulated")
    assert any("'simulated'" in p for p in fp.check_roles(fig, ALONE))
    # In a panel with a legend the entries count, not an unnamed artist.
    fig, ax = plt.subplots()
    role(ax.plot([0, 1], [0, 1])[0], "simulated")
    role(ax.plot([0, 1], [1, 0], label="m")[0], "processed")
    ax.legend()
    assert any("no legend entry" in p for p in fp.check_roles(fig, MIXED))


def test_a_simulation_alone_may_be_solid_and_a_model_beside_a_measurement_not():
    fig, ax = plt.subplots()
    role(ax.plot([0, 1], [0, 1], ls="-", label="halo")[0], "simulated")
    ax.legend()
    assert fp.check_roles(fig, HALO) == []
    assert any(
        "solid" in p
        for p in fp.check_roles(_measured_and_model(model_style="-"), MIXED)
    )


def test_a_further_stage_of_the_data_is_named_as_data_not_as_a_model():
    spectrum = FigureProvenance(
        status="calibrated",
        dataset="gw150914-strain",
        combines=("processed",),
        processing="The strain and its spectrum.",
    )
    assert spectrum.statement() == "calibrated measurement with processed data"
    card = fp.card_of("gw150914-strain")
    after, _ = fp.caption_html(fp.metadata(spectrum, card, "m:f"), card)
    assert "with processed data</span>" in after


def test_a_reference_value_takes_any_style_and_counts_for_no_declared_role():
    fig, ax = plt.subplots()
    role(ax.plot([0, 1], [1, 0], ls="none", marker="o", label="m")[0], "processed")
    role(ax.plot([0, 1], [0, 1], ls="--", label="fit")[0], "simulated")
    role(ax.axhline(0.5, ls="-", label="bound"), fp.REFERENCE)
    ax.legend()
    assert fp.check_roles(fig, MIXED) == []
    fig, ax = plt.subplots()
    role(ax.axhline(0.5, label="bound"), fp.REFERENCE)
    ax.legend()
    assert any("no legend entry" in p for p in fp.check_roles(fig, ALONE))


def test_the_style_rules_hold_within_a_panel():
    # A dashed measurement in a panel without a model, beside a panel that
    # draws one: the measurement of that panel is not mistaken for a model.
    fig, (top, bottom) = plt.subplots(2, 1)
    role(top.plot([0, 1], [0, 1], ls="--", label="2 cm")[0], "processed")
    role(top.plot([0, 1], [1, 0], ls=":", label="5 cm")[0], "processed")
    top.legend()
    role(bottom.plot([0, 1], [0, 1], ls="-", label="m")[0], "processed")
    role(bottom.plot([0, 1], [1, 1], ls="--", label="fit")[0], "simulated")
    bottom.legend()
    assert fp.check_roles(fig, MIXED) == []
    role(bottom.plot([0, 1], [0, 0], ls=":", label="m2")[0], "processed")
    bottom.legend()
    assert any("drawn as a model" in p for p in fp.check_roles(fig, MIXED))


def test_a_providers_copyright_notice_in_its_attribution_is_not_ownership():
    card = fp.card_of("trackpy-bulk-water")
    assert "Copyright (c)" in card["rights"]["attribution"]
    alone = FigureProvenance(
        status="processed", dataset="trackpy-bulk-water", processing="Tracked."
    )
    png = encode(_draw_one, metadata=fp.metadata(alone, card, "m:f"))
    assert fp.check_png(png, alone, card, "m:f") == []
    # Elsewhere, and as the project's claim, the mark is still refused.
    assert fp.ownership_problems("Data (c) 2024 NASA")
    assert fp.ownership_problems("Copyright (c) Physics by Construction", notice=True)


def _draw_one():
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    return fig


def test_a_figure_of_further_datasets_credits_each_on_the_image_and_caption():
    hot_wire, piv = "ost-hotwire-cylinder-wakes", "piv-cylinder-wake"
    both = FigureProvenance(
        status="processed",
        dataset=hot_wire,
        artifact="processed-measured",
        also=(piv,),
        processing="Strouhal numbers of both records.",
    )
    card, other = fp.card_of(hot_wire), fp.card_of(piv)
    assert fp.declaration_problems(both, card) == []
    meta = fp.metadata(both, card, "m:f")
    short = other["rights"]["figure_credit"]["short"]
    assert meta["pbc:also"] == piv and meta["pbc:also-credit"] == short
    first, second = meta["pbc:visible-credit"].split("\n")
    assert first.endswith(card["rights"]["figure_credit"]["short"])
    assert second == short
    _, end = fp.caption_html(meta, card)
    assert f'<span class="figure-credit-also">{short}</span>' in end
    assert "<dt>Also from</dt>" in end
    # A record of one dataset has none of these keys.
    assert "pbc:also" not in fp.metadata(ALONE, fp.card_of(NIST), "m:f")
    with pytest.raises(ValueError):
        FigureProvenance(status="processed", dataset=piv, also=(piv,), processing="p")


def _image_and_contours(linestyles):
    # A measured field with a model's contour lines over it, as the
    # Kamchatka map draws (review 02 M1, Issue #531).
    fig, ax = plt.subplots()
    role(ax.imshow([[0, 1], [1, 0]]), "processed")
    z = [[0.0, 1.0, 2.0], [1.0, 2.0, 3.0], [2.0, 3.0, 4.0]]
    contours = ax.contour(z, levels=[1.0, 2.0], colors="k", linestyles=linestyles)
    return fig, contours


def test_a_contour_set_carries_a_role_and_follows_the_style_rules():
    fig, contours = _image_and_contours("-.")
    assert any("contour set has no role" in p for p in fp.check_roles(fig, MIXED))
    role(contours, "simulated")
    assert fp.check_roles(fig, MIXED) == []
    role(contours, "conceptual")
    assert any("'conceptual'" in p for p in fp.check_roles(fig, MIXED))
    # Beside a measurement, a model's contour lines are never solid.
    fig, contours = _image_and_contours(["--", "-"])
    role(contours, "simulated")
    assert any("solid lines" in p for p in fp.check_roles(fig, MIXED))
    # Beside a model, a measurement's contour lines are never dashed.
    fig, ax = plt.subplots()
    role(ax.imshow([[0, 1], [1, 0]]), "simulated")
    contours = ax.contour([[0.0, 1.0], [1.0, 2.0]], levels=[1.0], linestyles="--")
    role(contours, "processed")
    assert any("drawn as a model" in p for p in fp.check_roles(fig, MIXED))
