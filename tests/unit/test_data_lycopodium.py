"""The Lycopodium sample parses into what its card says, the numbers of its
dossier follow from it, and the one-time XLSX conversion is faithful (ADR 007
and its addendum of #417).
"""

import hashlib
import importlib.util
import zipfile
from pathlib import Path

import numpy as np
import pytest

from pbc.data import REPO_ROOT, SAMPLES_DIR
from pbc.data.card import load_card
from pbc.data.reference import lycopodium as lyc
from pbc.waves.diffraction import AIRY_FIRST_ZERO

DIR = SAMPLES_DIR / "lycopodium-spore-diffraction"
CARD = load_card(REPO_ROOT / "data/registry/lycopodium-spore-diffraction.yaml")
SCRIPT = REPO_ROOT / "tools/datasets/lycopodium_xlsx_to_csv.py"
RECODE = REPO_ROOT / "tools/datasets/lycopodium_morphometry_to_utf8.py"


def converter(script=SCRIPT):
    spec = importlib.util.spec_from_file_location(script.stem, script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def profiles():
    return lyc.load_profiles(DIR)


@pytest.fixture(scope="module")
def tables():
    return {k: lyc.read_morphometry(DIR / f) for k, f in lyc.MORPHOMETRY.items()}


def test_lycopodium_sample_parses(profiles, tables):
    # Field names, shapes, cadence: one scanline per wavelength, n counting
    # from 0, x in equal steps (a different scale in each photograph), y
    # constant.
    shape = {0.6328: 2211, 0.405: 932}
    step = {0.6328: 0.0530345, 0.405: 0.0830055}
    for w, p in profiles.items():
        assert p.x.shape == p.y.shape == p.luma.shape == (shape[w],)
        np.testing.assert_array_equal(p.n, np.arange(shape[w]))
        np.testing.assert_allclose(np.diff(p.x), step[w], atol=1e-7)
        assert np.unique(p.y).size == 1
        # Units: luma is the 8-bit brightness; the centre is saturated.
        assert p.luma.min() > 25 and p.luma.max() <= 255
        assert (p.luma >= lyc.SATURATED).sum() == {0.6328: 37, 0.405: 57}[w]
        # Masks: none in the record; every value is a number.
        assert np.isfinite(p.x).all() and np.isfinite(p.luma).all()
    assert profiles[0.6328].x[[0, -1]].tolist() == [-61.4950942, 55.71112758]
    assert profiles[0.405].x[[0, -1]].tolist() == [-39.1460014, 38.13209741]
    # The morphometry: ImageJ's columns plus the creators' r^2, r, d.
    x160, x80 = tables["x160"], tables["x80"]
    assert len(x160["number"]) == 150 and len(x80["number"]) == 642
    assert "Perim." in x160 and "Perim." not in x80
    for table in (x160, x80):
        assert list(table)[-3:][2] == "d (µm)"
        np.testing.assert_array_equal(
            table["number"], np.arange(1, table["number"].size + 1)
        )
        # Units: Area is in um^2, not pixels^2 as the record says; d is the
        # diameter of the circle of that area, computed with pi = 3.14.
        d = lyc.diameter_column(table)
        np.testing.assert_allclose(d, 2 * np.sqrt(table["Area"] / 3.14), atol=1e-8)
        assert np.abs(d - 2 * np.sqrt(table["Area"] / np.pi)).max() < 0.013


def test_the_samples_are_the_record_files_and_the_conversion_outputs():
    for sample in CARD["samples"]:
        data = (DIR / sample["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == sample["sha256"]
        assert len(data) == sample["bytes"]
    # The morphometry samples are the record's files re-encoded from Latin-1
    # to UTF-8 and nothing else: encoded back, their md5 is Zenodo's, and
    # their sha256 is the one the re-encoding script pins.
    recode = converter(RECODE).INPUTS
    md5 = {d["filename"]: d["digest"] for d in CARD["downloads"]}
    for name in lyc.MORPHOMETRY.values():
        record = (DIR / name).read_bytes().decode("utf-8").encode("latin-1")
        assert hashlib.md5(record).hexdigest() == md5[name]
        assert hashlib.sha256(record).hexdigest() == recode[name]
    assert md5["Lycopodium_Morphometry_x160.csv"] == "bf607a6ee0b547b614067f4be793d9cc"
    assert md5["Lycopodium_Morphometry_x80.csv"] == "ac827547093505ab1867d17b19be8521"
    pinned = converter().INPUTS
    for download in CARD["downloads"]:
        if download["filename"].endswith(".xlsx"):
            assert pinned[download["filename"]] == download["digest"]


def test_the_microscope_diameters_of_whole_spores(tables):
    n, mean, sd, sem = lyc.summary(lyc.whole_spores(tables["x160"]))
    assert n == 72
    assert mean == pytest.approx(29.908, abs=1e-3)
    assert sd == pytest.approx(2.865, abs=1e-3)
    assert sem == pytest.approx(0.338, abs=1e-3)
    n, mean, sd, sem = lyc.summary(lyc.whole_spores(tables["x80"]))
    assert n == 605
    assert mean == pytest.approx(30.360, abs=1e-3)
    assert sem == pytest.approx(0.131, abs=1e-3)
    # The two magnifications, each with its own scale bar, agree within
    # 1.3 combined standard errors.
    assert (30.360 - 29.908) / np.hypot(0.338, 0.131) < 1.3
    # The cut at 15 um lies in a gap at x160 (no particle from 10 to 20 um);
    # at x80 it moves only seven particles between 10 and 20 um.
    d = lyc.diameter_column(tables["x160"])
    assert ((d > 10) & (d < 20)).sum() == 0
    d = lyc.diameter_column(tables["x80"])
    assert ((d > 10) & (d <= 15)).sum() == 3 and ((d > 15) & (d < 20)).sum() == 4


def test_the_ensemble_model_reduces_to_the_airy_pattern_of_one_disk():
    minima, maxima = lyc.model_extrema(np.array([30.0]))
    assert minima[0] * 30.0 == pytest.approx(AIRY_FIRST_ZERO, abs=1e-4)
    assert minima[1] * 30.0 == pytest.approx(2.2331, abs=1e-3)
    assert maxima[0] * 30.0 == pytest.approx(1.6347, abs=1e-3)
    q = np.linspace(0, 0.2, 7)
    np.testing.assert_allclose(
        lyc.ensemble(q, np.array([30.0, 30.0])), lyc.ensemble(q, np.array([30.0]))
    )


def test_the_dark_rings_their_ratio_and_the_model(profiles, tables):
    assert lyc.centre(profiles[0.6328]) == pytest.approx(1.245, abs=1e-9)
    assert lyc.centre(profiles[0.405]) == pytest.approx(0.075, abs=1e-9)
    red, blue = lyc.ring(profiles[0.6328]), lyc.ring(profiles[0.405])
    assert red.radius == pytest.approx(16.682, abs=1e-3)
    assert red.uncertainty == pytest.approx(0.341, abs=1e-3)
    assert blue.radius == pytest.approx(11.020, abs=1e-3)
    assert blue.uncertainty == pytest.approx(0.326, abs=1e-3)
    value, error = lyc.ratio(profiles)
    assert value == pytest.approx(0.6606, abs=1e-4)
    assert error == pytest.approx(0.0237, abs=1e-4)
    # The scale-free test: within one standard error of the wavelength ratio.
    assert abs(value - 0.405 / 0.6328) < error
    # The sides: at 632.8 nm they agree; at 405 nm the right side has no dip.
    left, right = lyc.side_rings(profiles[0.6328])
    assert abs(left - right) < 0.15
    left, right = lyc.side_rings(profiles[0.405])
    assert left == pytest.approx(10.92, abs=0.01) and right > 13.9
    # The polydisperse model of the 72 whole spores at x160.
    d = lyc.whole_spores(tables["x160"])
    minima, _ = lyc.model_extrema(d)
    assert minima[0] * d.mean() == pytest.approx(1.2316, abs=1e-3)
    assert minima[1] * d.mean() == pytest.approx(2.2312, abs=1e-3)
    order = lyc.ring_order(profiles, d)
    assert order["model order 1"] == pytest.approx(1.313, abs=1e-3)
    assert order["model order 2"] == pytest.approx(1.172, abs=1e-3)
    assert order["measured 0.6328 um"] == pytest.approx(1.191, abs=1e-3)
    assert order["measured 0.405 um"] == pytest.approx(1.111, abs=1e-3)
    # The implied screen distance, in the profile's unit, for either order.
    distance = {
        (k + 1, w): lyc.screen_distance(lyc.ring(p).radius, minima[k], w)
        for k in (0, 1)
        for w, p in profiles.items()
    }
    assert distance[1, 0.6328] == pytest.approx(639.9, abs=0.1)
    assert distance[1, 0.405] == pytest.approx(660.7, abs=0.1)
    assert distance[2, 0.6328] == pytest.approx(353.0, abs=0.1)
    assert distance[2, 0.405] == pytest.approx(364.6, abs=0.1)


def _xlsx(path: Path, rows: list[list], title="profile_A"):
    strings = [title, "n", "x", "y", "luma"]
    shared = "".join(f"<si><t>{s}</t></si>" for s in strings)
    cells = ['<row r="1"><c r="A1" t="s"><v>0</v></c></row>']
    cells.append(
        '<row r="2">'
        + "".join(f'<c r="{c}2" t="s"><v>{k + 1}</v></c>' for k, c in enumerate("ABCD"))
        + "</row>"
    )
    for k, row in enumerate(rows, start=3):
        cells.append(
            f'<row r="{k}">'
            + "".join(
                f'<c r="{c}{k}"><v>{v}</v></c>'
                for c, v in zip("ABCD", row, strict=True)
            )
            + "</row>"
        )
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/sharedStrings.xml", f"<sst {ns}>{shared}</sst>")
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            f"<worksheet {ns}><sheetData>{''.join(cells)}</sheetData></worksheet>",
        )


def test_the_conversion_keeps_every_row_and_value(tmp_path):
    tool = converter()
    source = tmp_path / "profile.xlsx"
    _xlsx(
        source, [[0, "-1.5", "0.25", "36.876857139999998"], [1, "2E-3", "0.25", "255"]]
    )
    out = tmp_path / "profile.csv"
    tool.convert(source, out, check_input=False)
    lines = out.read_text().splitlines()
    assert lines[3:] == ["n,x,y,luma", "0,-1.5,0.25,36.87685714", "1,0.002,0.25,255.0"]
    profile = lyc.read_profile(out, 0.6328)
    assert profile.luma.tolist() == [36.876857139999998, 255.0]
    # The pinned check refuses a file that is not one of the inspected ones.
    with pytest.raises(ValueError, match="not a pinned input"):
        tool.convert(source, out)


def test_the_conversion_refuses_another_layout(tmp_path):
    tool = converter()
    bad_title = tmp_path / "a.xlsx"
    _xlsx(bad_title, [[0, 1, 2, 3]], title="profile_B")
    with pytest.raises(ValueError, match="title"):
        tool.convert(bad_title, tmp_path / "a.csv", check_input=False)
    gap = tmp_path / "b.xlsx"
    _xlsx(gap, [[0, 1, 2, 3], [2, 1, 2, 3]])
    with pytest.raises(ValueError, match="expected 1"):
        tool.convert(gap, tmp_path / "b.csv", check_input=False)


def test_the_reencoding_changes_the_micro_sign_and_nothing_else(tmp_path):
    tool = converter(RECODE)
    source = tmp_path / "morphometry.csv"
    record = (
        b" ;Area;;r^2  (\xb5m^2);r (\xb5m);d (\xb5m)\r\n"
        b"1;511.04;;162.75;12.757;25.515\r\n"
    )
    source.write_bytes(record)
    out = tmp_path / "out.csv"
    tool.convert(source, out, check_input=False)
    data = out.read_bytes()
    assert data == record.replace(b"\xb5", "µ".encode())
    assert data.decode("utf-8").encode("latin-1") == record
    table = lyc.read_morphometry(out)
    assert table["d (µm)"].tolist() == [25.515] and table["Area"].tolist() == [511.04]
    # The pinned check refuses a file that is not one of the inspected ones,
    # and another byte above 127 leaves the decoding in doubt.
    with pytest.raises(ValueError, match="not a pinned input"):
        tool.convert(source, out)
    source.write_bytes(record + b"\x96\r\n")
    with pytest.raises(ValueError, match="other than 0xB5"):
        tool.convert(source, out, check_input=False)
