"""The Kamchatka tsunami inputs parse into what their card says, the numbers
of the dossier follow from them, and the one-time ETOPO conversion is
faithful (ADR 007).
"""

import hashlib
import importlib.util

import numpy as np
import pytest

from pbc.data import REPO_ROOT, SAMPLES_DIR
from pbc.data.card import load_card
from pbc.data.reference import kamchatka_tsunami as kt

DIR = SAMPLES_DIR / "kamchatka-2025-tsunami-inputs"
CARD = load_card(REPO_ROOT / "data/registry/kamchatka-2025-tsunami-inputs.yaml")
SCRIPT = REPO_ROOT / "tools/datasets/etopo_ascii_to_npy.py"


def converter():
    spec = importlib.util.spec_from_file_location(SCRIPT.stem, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def analysed():
    return kt.analyse(DIR)


def test_kamchatka_tsunami_sample_parses(analysed):
    inputs, _ = analysed
    # NCEI event files: eleven columns; 15-minute records, then 1-minute and
    # 15-second records in event mode; 2025-07-27 00:00 to 07-31 12:00 (not
    # to 08-03 as the names say); height - tide = residual to the file's
    # rounding; the eleventh column is 0 throughout.
    for name, rows, dups in (("21416", 1697, 13), ("21415", 1761, 18)):
        r = inputs.ncei[name]
        assert r.time.shape == r.height.shape == r.residual.shape == (rows,)
        assert r.time[0] == np.datetime64("2025-07-27T00:00")
        assert r.time[-1] == np.datetime64("2025-07-31T12:00")
        steps = set(np.diff(np.unique(r.time)).astype(int) // 1000)
        assert {15, 60, 900} <= steps
        assert kt.duplicate_times(r) == dups
        np.testing.assert_allclose(r.height - r.tide, r.residual, atol=2.1e-5)
        assert (r.flag == 0).all()
        assert np.isfinite(r.height).all()
    # NDBC annual files: the whole of 2025, record types 1 (15 min),
    # 2 (1 min), 3 (15 s); 9999.000 is a missing height (NaN here).
    for name, rows, missing, kinds in (
        ("21416", 41133, 7064, (35040, 5833, 260)),
        ("21415", 38784, 1803, (35040, 3600, 144)),
    ):
        n = inputs.ndbc[name]
        assert n.time.shape == n.height.shape == (rows,)
        assert int(np.isnan(n.height).sum()) == missing
        assert tuple(int((n.kind == k).sum()) for k in (1, 2, 3)) == kinds
        assert n.time[0] == np.datetime64("2025-01-01T00:00")
    # Units: NDBC's height is the water column in metres, so its mean in the
    # event window is the station depth of NCEI's deployment list.
    for name in ("21416", "21415"):
        n, site = inputs.ndbc[name], inputs.stations[name]
        window = (n.time >= np.datetime64("2025-07-27")) & (
            n.time < np.datetime64("2025-07-31T12:00")
        )
        assert abs(np.nanmean(n.height[window]) - site.depth) < 1.0
    assert len(inputs.stations) == 26
    assert inputs.stations["21416"] == kt.Station(
        48.1258, 163.3755, 5788.0, "20250711to20250731"
    )
    assert inputs.stations["21415"].depth == 4720.0
    # USGS finite fault: three segments of 186, 186, 93 subfaults, ten columns.
    fault = inputs.fault
    assert fault.subfaults.shape == (465, 10)
    assert [int((fault.segment == s).sum()) for s in (1, 2, 3)] == [186, 186, 93]
    assert fault.header["time"] == np.datetime64("2025-07-29T23:24:50")
    # Surface deformation: 40 x 40, metres, longitude fastest.
    d = inputs.deformation
    assert d.up.shape == (40, 40)
    assert (d.lon[0, 0], d.lat[0, 0]) == (154.3825, 48.9143)
    assert np.all(np.diff(d.lon, axis=1) > 0) and np.all(np.diff(d.lat, axis=0) > 0)
    # ETOPO: 375 x 600 int16 metres, cell centres on the 4' grid.
    b = inputs.bathymetry
    assert b.z.shape == (375, 600) and b.z.dtype == np.int16
    assert (b.z.min(), b.z.max()) == (-9573, 3808)
    assert abs((b.z < 0).mean() - 0.9188) < 1e-4
    np.testing.assert_allclose(b.lat[[0, -1]], [35 + 0.5 / 60, 59.94166666666667])
    np.testing.assert_allclose(b.lon[[0, -1]], [140 + 0.5 / 60, 179.94166666666667])


def test_the_samples_are_the_downloads_and_the_conversion_output():
    downloads = {d["filename"]: d for d in CARD["downloads"]}
    for sample in CARD["samples"]:
        data = (DIR / sample["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == sample["sha256"]
        assert len(data) == sample["bytes"]
        if sample["path"] in downloads:
            entry = downloads[sample["path"]]
            assert (
                entry["algorithm"] == "sha256" and entry["digest"] == sample["sha256"]
            )
    module = converter()
    assert downloads[module.INPUT_NAME]["digest"] == module.INPUT_SHA256


def test_the_ncei_heights_are_ndbc_heights_converted_a_second_time(analysed):
    _, results = analysed
    for name in ("21416", "21415"):
        r = results[name]
        # Every NCEI timestamp is in NDBC's file, and NCEI / NDBC is 0.670
        # within 3.6e-6 (2 cm of a 5788 m column) at all of them.
        assert r.matched == {"21416": 1697, "21415": 1761}[name]
        assert abs(r.ratio_median - 0.670) < 3e-6
        assert r.ratio_max_deviation < 3.6e-6
        # The mean NCEI height is 0.670 times the station depth.
        assert abs(r.mean_over_depth - 0.670) < 1e-4


def test_the_peaks_and_the_arrival_windows_of_the_dossier(analysed):
    _, results = analysed
    a, b = results["21416"], results["21415"]
    assert a.peak == pytest.approx((0.8178, 32.125), abs=1e-3)
    assert a.trough == pytest.approx((-0.5076, 40.125), abs=1e-3)
    assert b.peak == pytest.approx((0.3519, 69.125), abs=1e-3)
    assert a.half_peak == pytest.approx(29.80, abs=0.01)
    assert b.half_peak == pytest.approx(66.51, abs=0.01)
    # Noise floor in the day before, and the seafloor shaking at 21416.
    assert a.noise == pytest.approx(0.0197, abs=1e-4)
    assert b.noise == pytest.approx(0.0074, abs=1e-4)
    assert a.seismic == pytest.approx(0.615, abs=1e-3)
    # sqrt(gh) along great circles over the ETOPO crop.
    assert a.epicentre_distance == pytest.approx(534.3, abs=0.1)
    assert b.epicentre_distance == pytest.approx(849.4, abs=0.1)
    assert a.epicentre_arrival == pytest.approx(40.0, abs=0.1)
    assert b.epicentre_arrival == pytest.approx(69.1, abs=0.1)
    assert a.uplift_arrival[1.0] == pytest.approx(26.55, abs=0.01)
    assert b.uplift_arrival[1.0] == pytest.approx(60.83, abs=0.01)
    # The window holds the arrival: the leading crest passes half its peak
    # after the front from the nearest uplift would arrive, and the peak
    # comes before the front from the epicentre would (at 21415, together).
    for r in (a, b):
        assert (
            r.uplift_arrival[1.0] < r.half_peak < r.peak[1] <= r.epicentre_arrival + 0.1
        )
        levels = [r.uplift_arrival[level] for level in kt.UPLIFT_LEVELS]
        assert levels == sorted(levels) and levels[-1] - levels[0] < 1.5


def test_the_fault_and_its_deformation(analysed):
    inputs, _ = analysed
    fault, d = inputs.fault, inputs.deformation
    # The summed subfault moment gives the header's magnitude.
    assert fault.moment == pytest.approx(fault.header["mo"], rel=1e-4)
    assert fault.mw == pytest.approx(8.835, abs=1e-3)
    assert fault.subfaults[:, 5].max() == pytest.approx(39.34, abs=0.01)
    assert (d.up.max(), d.up.min()) == (8.1113, -4.4003)
    # The model's grid does not reach zero at its edges.
    edges = np.concatenate([d.up[0], d.up[-1], d.up[:, 0], d.up[:, -1]])
    assert np.abs(edges).max() == pytest.approx(1.13, abs=0.01)
    # The fault's origin time is 2.483 s before ComCat's.
    assert (kt.ORIGIN - fault.header["time"]) / np.timedelta64(1, "ms") == 2483


def test_the_travel_time_is_exact_over_a_flat_sea():
    flat = kt.Bathymetry(
        lat=np.zeros(375), lon=np.zeros(600), z=np.full((375, 600), -4000, np.int16)
    )
    minutes, km = kt.travel_time(flat, (50.0, 160.0), (50.0, 165.0))
    expected_km = (
        kt.EARTH_RADIUS
        / 1e3
        * np.arccos(
            np.sin(np.radians(50)) ** 2
            + np.cos(np.radians(50)) ** 2 * np.cos(np.radians(5))
        )
    )
    assert km == pytest.approx(expected_km, rel=1e-9)
    assert minutes == pytest.approx(km * 1e3 / np.sqrt(kt.G * 4000) / 60, rel=1e-9)
    # A path across land is blocked.
    land = kt.Bathymetry(flat.lat, flat.lon, flat.z.copy())
    land.z[:, 300] = 10
    assert kt.travel_time(land, (50.0, 140.5), (50.0, 179.5))[0] == np.inf


def test_the_converter_checks_the_grid_and_writes_int16(tmp_path):
    module = converter()
    lat, lon = module.grid()
    z = np.arange(375 * 600, dtype=np.float32).reshape(375, 600) % 9000 - 6000.25
    lines = ["Dataset {", "} x;", "-" * 45, "z.z[375][600]"]
    lines += [
        f"[{i}], " + ", ".join(repr(float(v)) for v in row) for i, row in enumerate(z)
    ]
    lines += ["", "z.lat[375]", ", ".join(repr(float(v)) for v in lat), ""]
    lines += ["z.lon[600]", ", ".join(repr(float(v)) for v in lon), ""]
    text = "\n".join(lines)
    out = module.convert(text)
    assert out.dtype == np.int16 and out.shape == (375, 600)
    np.testing.assert_array_equal(out, np.rint(z).astype(np.int16))
    shifted = text.replace(repr(float(lat[0])), repr(float(lat[0]) + 0.01), 1)
    with pytest.raises(ValueError, match="latitude"):
        module.convert(shifted)
    with pytest.raises(ValueError, match="missing"):
        module.convert(text.replace("[0], " + repr(float(z[0, 0])), "[0], -99999.0", 1))
    source = tmp_path / "other.txt"
    source.write_text(text)
    assert module.main([str(source), str(tmp_path / "out.npy")]) == 1
    assert not (tmp_path / "out.npy").exists()
