"""The DWD Potsdam soil-temperature sample parses into what its card says, the
extraction that wrote it keeps every line it selects, the damped wave solves
the heat equation of T6, and the reference analysis gives the numbers of the
dossier (ADR 007; docs/datasets/dwd-potsdam-soil-temperature.md).
"""

import hashlib
import importlib.util
import io
import zipfile
from pathlib import Path

import numpy as np
import pytest

from pbc.data import SAMPLES_DIR
from pbc.data.reference import dwd_soil
from pbc.thermodynamics.conduction import Fixed, ftcs_step

DWD = SAMPLES_DIR / "dwd-potsdam-soil-temperature"
ROOT = Path(__file__).parents[2]
EXTRACTOR = ROOT / "tools/datasets/dwd_soil_extract.py"


def extractor():
    spec = importlib.util.spec_from_file_location("dwd_soil_extract", EXTRACTOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def readings():
    return dwd_soil.load(DWD)


@pytest.fixture(scope="module")
def results(readings):
    annual, hourly = readings
    return (
        dwd_soil.estimate(dwd_soil.annual_wave(annual)),
        dwd_soil.estimate(dwd_soil.diurnal_wave(hourly)),
    )


# The sample.


def test_dwd_soil_sample_parses(readings):
    annual, hourly = readings
    # Field names, in the order of DWD's product file; 2 cm is never measured.
    for r in (annual, hourly):
        assert tuple(r.header.split(";")) == dwd_soil.FIELDS
        assert r.temperature.shape[1] == 5
        assert set(r.quality) == {3}  # automatic control and correction
    # Shapes and cadence: four readings a day over 2015-2024, two missing rows
    # (2023-09-05 12 h and 18 h are absent from DWD's file); every hour of
    # June to August 2020-2024.
    assert annual.time.shape == (14610,)
    assert hourly.time.shape == (11040,)
    assert annual.time[[0, -1]].tolist() == [
        np.datetime64("2015-01-01T00", "h").item(),
        np.datetime64("2024-12-31T18", "h").item(),
    ]
    hours = set((annual.time - annual.time.astype("datetime64[D]")).astype(int))
    assert hours == {0, 6, 12, 18}
    steps = np.diff(annual.time).astype(int)
    assert set(steps) == {6, 18}
    assert np.datetime64("2023-09-05T12", "h") not in annual.time
    assert np.datetime64("2023-09-05T18", "h") not in annual.time
    months = annual.time.astype("datetime64[M]").astype(int) % 12 + 1
    assert set(months) == set(range(1, 13))
    hourly_months = hourly.time.astype("datetime64[M]").astype(int) % 12 + 1
    assert set(hourly_months) == {6, 7, 8}
    for year in dwd_soil.SUMMERS:
        steps = np.diff(
            hourly.time[hourly.time.astype("datetime64[Y]").astype(int) == year - 1970]
        ).astype(int)
        assert set(steps) == {1}
    # Masks: -999 becomes nan; one 6-hourly row (2023-09-04 12 h) misses 5, 10
    # and 20 cm, three hourly rows (2023-08-24 14-16 h) miss 5 and 10 cm.
    np.testing.assert_array_equal(np.isnan(annual.temperature).sum(0), [1, 1, 1, 0, 0])
    gap = np.isnan(annual.temperature[:, 0])
    assert annual.time[gap].tolist() == [np.datetime64("2023-09-04T12", "h").item()]
    np.testing.assert_array_equal(np.isnan(hourly.temperature).sum(0), [3, 3, 0, 0, 0])
    # Units: degrees Celsius, given to 0.1 K, in the range of a Potsdam soil.
    for r in (annual, hourly):
        values = r.temperature[np.isfinite(r.temperature)]
        assert np.allclose(values * 10, np.round(values * 10))
    assert np.nanmin(annual.temperature[:, 0]) == -10.0
    assert np.nanmax(hourly.temperature[:, 0]) == 40.4
    # The metadata: the depths, the sensors, and the unit of each column.
    geraete = (DWD / "Metadaten_Geraete_Erdbodentemperatur_03987.txt").read_text(
        encoding="utf-8"
    )
    for depth in ("-.05", "-.1", "-.2", "-.5", "-1"):
        assert f";{depth};19780301;20260419;PT 100 (Erdboden);" in geraete
    parameter = (DWD / "Metadaten_Parameter_eb_stunde_03987.txt").read_text(
        encoding="utf-8"
    )
    for column, depth in zip(
        dwd_soil.COLUMNS, ("5 cm", "10 cm", "20 cm", "50 cm", "1 m"), strict=True
    ):
        assert f";Potsdam;{column};Temperatur im Erdboden in {depth} Tiefe;°C;" in (
            parameter
        )
    geographie = (DWD / "Metadaten_Geographie_03987.txt").read_text(encoding="utf-8")
    assert "3987;   80.86; 52.3812; 13.0622;20230706;        ;Potsdam" in geographie
    operator = (DWD / "Metadaten_Stationsname_Betreibername_03987.txt").read_text(
        encoding="utf-8"
    )
    assert "3987;DWD;19910101;" in operator


def test_the_reader_refuses_other_columns_and_values_at_2_cm(tmp_path):
    good = dwd_soil.FIELDS
    row = "       3987;2024070100;    3;  -999;  20.1;  21.0;  22.0;  19.0;  17.0;eor"
    path = tmp_path / "f.txt"
    path.write_bytes(("STATIONS_ID;MESS_DATUM;eor\r\n" + row + "\r\n").encode())
    with pytest.raises(ValueError, match="columns"):
        dwd_soil.read_readings(path)
    path.write_bytes(
        (";".join(good) + "\r\n" + row.replace("-999", "12.0") + "\r\n").encode()
    )
    with pytest.raises(ValueError, match="2 cm"):
        dwd_soil.read_readings(path)
    path.write_bytes(
        (";".join(good) + "\r\n" + row.replace("3987;", "3988;", 1) + "\r\n").encode()
    )
    with pytest.raises(ValueError, match="station"):
        dwd_soil.read_readings(path)
    path.write_bytes((";".join(good) + "\r\n" + row + "\r\n").encode())
    assert dwd_soil.read_readings(path).temperature[0].tolist() == [
        20.1,
        21.0,
        22.0,
        19.0,
        17.0,
    ]


# The extraction, on a small archive written here.


def small_zip(tool, lines: list[str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(tool.PRODUCT, "".join(line + "\r\n" for line in lines))
        for name in tool.METADATA:
            archive.writestr(name, f"{name};\xe4\r\n".encode("latin-1"))
    return buffer.getvalue()


def test_the_extraction_keeps_the_selected_lines_unchanged(tmp_path):
    tool = extractor()
    header = tool.HEADER.decode()
    rows = [
        "       3987;2014123118;    3;  -999;   1.0;   1.1;   1.2;   1.3;   1.4;eor",
        "       3987;2015010100;    3;  -999;   0.0;   0.0;   0.4;   1.9;   4.6;eor",
        "       3987;2015010101;    3;  -999;  -0.1;   0.0;   0.4;   1.9;   4.6;eor",
        "       3987;2020060113;    3;  -999;  25.0;-999;  22.0;  19.0;  17.0;eor",
        "       3987;2020060118;    3;  -999;  21.0;  21.5;  22.0;  19.0;  17.0;eor",
        "       3987;2020090100;    3;  -999;  15.0;  15.5;  16.0;  17.0;  17.5;eor",
        "       3987;2025010100;    3;  -999;   0.1;   0.6;   1.3;   3.0;   5.4;eor",
    ]
    source = tmp_path / tool.INPUT_NAME
    source.write_bytes(small_zip(tool, [header, *rows]))
    with pytest.raises(ValueError, match="pinned"):
        tool.extract(source, tmp_path / "out")
    tool.extract(source, tmp_path / "out", check_input=False)
    annual = (tmp_path / "out" / tool.ANNUAL_FILE).read_bytes()
    diurnal = (tmp_path / "out" / tool.DIURNAL_FILE).read_bytes()
    assert (
        annual
        == "".join(f"{x}\r\n" for x in (header, rows[1], rows[4], rows[5])).encode()
    )
    assert diurnal == "".join(f"{x}\r\n" for x in (header, rows[3], rows[4])).encode()
    for name in tool.METADATA:
        assert (tmp_path / "out" / name).read_bytes() == f"{name};\xe4\r\n".encode()
    other = tmp_path / "other.zip"
    other.write_bytes(small_zip(tool, ["STATIONS_ID;MESS_DATUM;eor", rows[1]]))
    with pytest.raises(ValueError, match="header"):
        tool.extract(other, tmp_path / "out2", check_input=False)


def test_the_sample_is_the_output_the_card_pins():
    tool = extractor()
    assert tool.ANNUAL_FILE == dwd_soil.ANNUAL_FILE
    assert tool.DIURNAL_FILE == dwd_soil.DIURNAL_FILE
    expected = {
        tool.ANNUAL_FILE: (
            "d9fe4916f266c91a0f0ab1e42782682e12ae07a379fd1c98fe309afcfeb824d2"
        ),
        tool.DIURNAL_FILE: (
            "ab6be9339237a2d66b4b552bc2ca42a6f3dbe7560c86a0803c0dcb6d067115cd"
        ),
    }
    for name, digest in expected.items():
        assert hashlib.sha256((DWD / name).read_bytes()).hexdigest() == digest
    # Every committed text file is UTF-8 (the metadata re-encoded, ADR 007).
    for name in tool.METADATA:
        (DWD / name).read_bytes().decode("utf-8")
    parameter = (DWD / "Metadaten_Parameter_eb_stunde_03987.txt").read_bytes()
    assert hashlib.sha256(parameter).hexdigest() == (
        "55a4fa22af5a548be7fda86e0ef953a8de60d9e8de998c93fa132d4ee1490f6e"
    )
    assert sorted(p.name for p in DWD.iterdir()) == sorted(
        [tool.ANNUAL_FILE, tool.DIURNAL_FILE, *tool.METADATA]
    )


# The model.


def test_the_damped_wave_solves_the_t6_heat_equation():
    """The FTCS scheme of T6 with the surface held at a daily cosine settles
    into the damped wave: amplitude exp(-z/d) and lag z/d at every depth."""
    kappa, omega, dz, r = 1.1e-6, dwd_soil.OMEGA_DAY, 0.01, 0.25
    dt = r * dz**2 / kappa
    z = np.arange(0.0, 1.2 + dz / 2, dz)
    temperature = np.full(z.size, 15.0)
    steps_per_day = round(dwd_soil.DAY / dt)
    dt = dwd_soil.DAY / steps_per_day
    r = kappa * dt / dz**2
    last_day = []
    for n in range(8 * steps_per_day):
        surface = 15.0 + 6.0 * np.cos(omega * (n + 1) * dt)
        temperature = ftcs_step(temperature, r, dz, 1.0, Fixed(surface), Fixed(15.0))
        if n >= 7 * steps_per_day:
            last_day.append(temperature)
    last_day = np.array(last_day)
    t = (np.arange(7 * steps_per_day, 8 * steps_per_day) + 1) * dt
    d = np.sqrt(2 * kappa / omega)
    for depth in (0.05, 0.10, 0.20, 0.50):
        k = round(depth / dz)
        c = dwd_soil.harmonic(t, last_day[:, k], omega)
        assert abs(c) == pytest.approx(6.0 * np.exp(-depth / d), rel=2e-3)
        assert -np.angle(c) == pytest.approx(depth / d, abs=2e-3)
        expected = dwd_soil.damped_wave(depth, t, 15.0, 6.0, 0.0, omega, kappa)
        np.testing.assert_allclose(last_day[:, k], expected, atol=0.02)


def test_the_estimate_returns_the_diffusivity_of_a_damped_wave():
    kappa = 1.07e-6
    start = np.datetime64("2015-01-01T00", "h")
    time = start + np.arange(0, 10 * 365 * 24 + 2 * 24, 6).astype("timedelta64[h]")
    t = dwd_soil.seconds(time, start)
    temperature = np.column_stack(
        [
            dwd_soil.damped_wave(z, t, 10.0, 12.8, 0.4, dwd_soil.OMEGA_YEAR, kappa)
            for z in dwd_soil.DEPTHS
        ]
    )
    synthetic = dwd_soil.Readings(time, np.full(time.size, 3), temperature, "")
    result = dwd_soil.estimate(dwd_soil.annual_wave(synthetic))
    assert result.kappa == pytest.approx((kappa, kappa), rel=2e-3)
    for _, _, from_amplitude, from_phase in dwd_soil.pairwise(result.wave):
        assert (from_amplitude, from_phase) == pytest.approx((kappa, kappa), rel=5e-3)


# The numbers of the dossier.


def test_the_annual_wave_gives_the_diffusivity_of_the_dossier(results):
    annual, _ = results
    assert annual.wave.counts.tolist() == [
        1460,
        1464,
        1460,
        1460,
        1460,
        1464,
        1460,
        1460,
        1458,
        1464,
    ]
    np.testing.assert_allclose(
        annual.wave.amplitude.mean(0),
        [12.522, 12.397, 12.076, 11.027, 9.322],
        atol=6e-4,
    )
    np.testing.assert_allclose(
        annual.wave.lag.mean(0), [0.0, 0.0138, 0.0399, 0.1239, 0.2801], atol=6e-5
    )
    assert np.array(annual.kappa) * 1e6 == pytest.approx([1.015, 1.147], abs=6e-4)
    assert np.array(annual.standard_error) * 1e6 == pytest.approx(
        [0.025, 0.009], abs=6e-4
    )
    assert annual.damping_depth == pytest.approx((3.193, 3.394), abs=6e-4)
    assert np.exp(annual.fit.intercept_amplitude) == pytest.approx(12.80, abs=0.006)
    # The single years range over 0.93-1.13 (amplitude) and 1.09-1.18 (phase).
    per = annual.per_period * 1e6
    assert per[:, 0].min() == pytest.approx(0.928, abs=6e-4)
    assert per[:, 0].max() == pytest.approx(1.134, abs=6e-4)
    assert per[:, 1].min() == pytest.approx(1.094, abs=6e-4)
    assert per[:, 1].max() == pytest.approx(1.178, abs=6e-4)


def test_the_daily_wave_gives_the_diffusivity_of_the_dossier(results):
    _, diurnal = results
    assert diurnal.wave.counts.tolist() == [92, 92, 92, 91, 92]
    np.testing.assert_allclose(
        diurnal.wave.amplitude.mean(0), [6.364, 4.633, 2.630, 0.464], atol=6e-4
    )
    np.testing.assert_allclose(
        diurnal.wave.lag.mean(0), [0.0, 0.3195, 0.8076, 2.5766], atol=6e-5
    )
    assert np.array(diurnal.kappa) * 1e6 == pytest.approx([1.084, 1.119], abs=6e-4)
    assert np.array(diurnal.standard_error) * 1e6 == pytest.approx(
        [0.013, 0.009], abs=6e-4
    )
    assert diurnal.damping_depth == pytest.approx((0.1727, 0.1754), abs=6e-5)


def test_the_pairs_of_depths_show_a_soil_that_is_not_uniform(results):
    annual, diurnal = results
    rows = [
        (a, b, ka * 1e6, kp * 1e6) for a, b, ka, kp in dwd_soil.pairwise(annual.wave)
    ]
    expected = [
        (0.05, 0.10, 2.493, 1.315),
        (0.10, 0.20, 1.440, 1.451),
        (0.20, 0.50, 1.085, 1.271),
        (0.50, 1.00, 0.883, 1.020),
    ]
    for row, values in zip(rows, expected, strict=True):
        assert row == pytest.approx(values, abs=6e-4)
    rows = [
        (a, b, ka * 1e6, kp * 1e6) for a, b, ka, kp in dwd_soil.pairwise(diurnal.wave)
    ]
    expected = [
        (0.05, 0.10, 0.902, 0.891),
        (0.10, 0.20, 1.135, 1.526),
        (0.20, 0.50, 1.088, 1.046),
    ]
    for row, values in zip(rows, expected, strict=True):
        assert row == pytest.approx(values, abs=6e-4)


def test_the_straight_lines_leave_small_residuals(results):
    annual, diurnal = results
    ln_a, lag = dwd_soil.depth_residuals(annual)
    assert np.abs(ln_a).max() == pytest.approx(0.0073, abs=1e-4)
    assert np.abs(lag).max() == pytest.approx(0.0059, abs=1e-4)
    ln_a, lag = dwd_soil.depth_residuals(diurnal)
    assert np.abs(ln_a).max() == pytest.approx(0.0144, abs=1e-4)
    assert np.abs(lag).max() == pytest.approx(0.0471, abs=1e-4)
