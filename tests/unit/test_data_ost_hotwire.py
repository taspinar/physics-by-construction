"""The Ost et al. hot-wire sample parses into what its card says, the tool
that wrote it pins the record's files, and the reference analysis gives the
Strouhal numbers of the dossier (ADR 007;
docs/datasets/ost-hotwire-cylinder-wakes.md).
"""

import hashlib
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from pbc.data import SAMPLES_DIR
from pbc.data.card import load_card
from pbc.data.reference import ost_hotwire as oh

OST = SAMPLES_DIR / "ost-hotwire-cylinder-wakes"
ROOT = Path(__file__).parents[2]
TOOL = ROOT / "tools/datasets/ost_hotwire_extract.py"


def tool():
    spec = importlib.util.spec_from_file_location("ost_hotwire_extract", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def data():
    return oh.load(OST)


@pytest.fixture(scope="module")
def analysis(data):
    return oh.analyse(data)


def test_ost_hotwire_sample_parses(data):
    # Provenance and processing in the header.
    assert "doi 10.17632/xy8ggx9hn6.1" in data.header[0]
    assert "first 16384 of 131072 samples" in data.header[1]
    assert "rounded to 0.001 m/s" in data.header[1]
    # Cadence and units: row k is k ms at 1000 Hz; velocity in m/s.
    assert "row k is the time k ms (1000 Hz, low-pass 300 Hz)" in data.header[2]
    assert "velocity in m/s" in data.header[2]
    # Field names: ten runs, the same in both files.
    names = tuple(r.name for r in data.runs)
    assert len(names) == 10 and len(set(names)) == 10
    lines = (OST / oh.SERIES).read_text().splitlines()
    assert tuple(lines[3].split(",")) == names
    assert tuple((OST / oh.RUNS).read_text().splitlines()[0].split(",")) == (
        oh.RUN_FIELDS
    )
    # Shapes: 16,384 samples of each run, three decimals.
    assert data.u.shape == (16384, 10)
    assert all(len(v.split(".")[1]) == 3 for v in lines[4].split(","))
    # No mask and no missing value: every velocity finite and positive (a
    # single hot wire measures a speed), between 0.3 and 30 m/s.
    assert np.all(np.isfinite(data.u))
    assert data.u.min() > 0.3 and data.u.max() < 30
    # The runs: three diameters, reference velocities 5.05 to 16 m/s.
    assert sorted({r.diameter for r in data.runs}) == [0.0251, 0.032, 0.05]
    assert min(r.velocity for r in data.runs) == 5.05
    assert max(r.velocity for r in data.runs) == 16.0
    # The probe is beside the wake: its mean speed exceeds the reference.
    assert np.all(data.u.mean(axis=0) > [r.velocity for r in data.runs])


def test_the_card_and_the_tool_pin_the_same_files():
    card = load_card(ROOT / "data/registry/ost-hotwire-cylinder-wakes.yaml")
    pinned = {name: value[0] for name, value in tool().RUNS.items()}
    assert {d["filename"]: d["digest"] for d in card["downloads"]} == pinned
    runs = {r.file: r.sha256 for r in oh.read_runs(OST / oh.RUNS)}
    assert runs == pinned
    for sample in card["samples"]:
        content = (OST / sample["path"]).read_bytes()
        assert hashlib.sha256(content).hexdigest() == sample["sha256"]
        assert len(content) == sample["bytes"]


def test_the_tool_refuses_other_files_and_a_wrong_time_column(tmp_path):
    module = tool()
    for name in module.RUNS:
        (tmp_path / name).write_text("0.0 1.0\n")
    with pytest.raises(ValueError, match="sha256"):
        module.convert(tmp_path, tmp_path)
    path = tmp_path / "times.txt"
    k = np.arange(oh.RECORD_SAMPLES)
    np.savetxt(path, np.column_stack([k / 500, np.ones(k.size)]))
    with pytest.raises(ValueError, match="1 ms"):
        module.read_record_file(path)


def test_the_record_states_one_reynolds_number_that_its_own_values_contradict(
    analysis, data
):
    # U D / Re gives the same viscosity for nine runs (air, 1.54e-5 m^2/s);
    # the 50 mm run at 5.05 m/s states the Re of the 16 m/s run.
    assert analysis.nu == pytest.approx(1.543e-5, rel=1e-3)
    odd = [
        r.name
        for r, q in zip(data.runs, analysis.nu_ratio, strict=True)
        if abs(q - 1) > 0.02
    ]
    assert odd == ["1C50_5ms"]
    assert np.all(np.abs(np.delete(analysis.nu_ratio, 7) - 1) < 0.012)


def test_the_strouhal_numbers_of_the_ten_runs(analysis, data):
    expected = {
        "1C25_5ms-1": (44.82, 0.2215),
        "1C25_10.5ms": (93.27, 0.2230),
        "1C25_16ms": (135.46, 0.2125),
        "1C32_5ms": (36.69, 0.2311),
        "1C32_8.3ms": (56.03, 0.2160),
        "1C32_10.5ms": (75.64, 0.2305),
        "1C32_16ms": (109.84, 0.2197),
        "1C50_5ms": (24.36, 0.2412),
        "1C50_10.5ms": (50.06, 0.2384),
        "1C50_16ms": (74.22, 0.2319),
    }
    for k, run in enumerate(data.runs):
        f, st = expected[run.name]
        assert analysis.frequency[k] == pytest.approx(f, abs=0.01), run.name
        assert analysis.strouhal[k] == pytest.approx(st, abs=1e-4), run.name
        assert analysis.frequency_err[k] < 0.25
    # The largest cylinder (blockage 0.26) sheds at the highest St: every
    # 50 mm run lies above every 25.1 mm run.
    by = {
        d: analysis.strouhal[analysis.blockage == d]
        for d in np.unique(analysis.blockage)
    }
    small, large = by[min(by)], by[max(by)]
    assert large.min() > small.max()
    assert analysis.blockage == pytest.approx(
        [0.1301] * 3 + [0.1658] * 4 + [0.2591] * 3, abs=1e-4
    )
