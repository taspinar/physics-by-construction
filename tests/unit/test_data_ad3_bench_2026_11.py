"""The bench sessions' dataset (``ad3-bench-2026-11``, F145 part 3, Issue
#614): the committed part parses and is the packager's output, the device
serial is replaced everywhere, the recorded adapter replays the sampled
frequency response and both LED runs to the exports' recorded results, and
the reference module reads what the dossier states."""

import csv
import dataclasses
import hashlib
import json
import tomllib
from pathlib import Path

import pytest
import yaml

from pbc.data import REGISTRY_DIR, SAMPLES_DIR
from pbc.data import publish as packager
from pbc.data.reference import ad3_bench_2026_11 as bench
from pbc.products.physics_lab import lab

SAMPLE = SAMPLES_DIR / bench.DATASET
ROOT = SAMPLES_DIR.parents[1]
DECLARATION = ROOT / "data" / "publish" / f"{bench.DATASET}.toml"
# The DOI of the archive, reserved by the owner in the Zenodo draft.
DOI = "10.5281/zenodo.24578221"


def manifest() -> dict[str, dict[str, str]]:
    with (SAMPLE / packager.MANIFEST).open(encoding="utf-8") as handle:
        return {r["path"]: r for r in csv.DictReader(handle, delimiter="\t")}


def raw_records(folder: Path) -> dict[str, set[str]]:
    """Record id -> the protocols of its rows in ``raw.csv``."""
    found: dict[str, set[str]] = {}
    with (folder / bench.RAW).open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            found.setdefault(row["record"], set()).add(row["protocol"])
    return found


def test_ad3_bench_2026_11_sample_parses():
    """29 exports in the declaration's order of time (27 series RLC, 2 LED
    pair), each with its run record, measurement table, and evidence log;
    the three raw files of the declared rule; every run record names the
    device identifier."""
    declared = tomllib.loads(DECLARATION.read_text(encoding="utf-8"))
    folders = bench.export_dirs(SAMPLE)
    assert [f.name for f in folders] == declared["exports"]["names"]
    circuits = [bench.read_run(f)["plan"]["circuit"] for f in folders]
    assert circuits.count("series-rlc") == 27 and circuits.count("led-pair") == 2
    for folder in folders:
        record = bench.read_run(folder)
        assert record["run"]["mode"] == "live"
        assert record["run"]["device"]["serial"] == bench.DEVICE_ID
        assert record["execution_modes"] == ["live"]
        rows = bench.read_measurements(folder)
        assert len(rows) == record["evaluation"]["acquisitions"]
        assert {r["valid"] for r in rows} == {"1"}
        evidence = json.loads((folder / bench.EVIDENCE).read_text(encoding="utf-8"))
        assert evidence["record"]["environment"]["execution_mode"] == "live"
        files = sorted(p.name for p in folder.iterdir())
        expected = [bench.EVIDENCE, bench.MEASUREMENTS, bench.RUN]
        if folder.name in (bench.RLC_SAMPLE, *bench.LED_RUNS):
            expected = sorted([*expected, bench.RAW])
        assert files == expected
    # The RLC sample holds the frequency-response records only: all 31 of
    # the campaign's, none of its ring-downs.
    rlc = raw_records(SAMPLE / bench.EXPORTS / bench.RLC_SAMPLE)
    assert len(rlc) == 31 and set().union(*rlc.values()) == {"frequency-response"}
    table = bench.read_measurements(SAMPLE / bench.EXPORTS / bench.RLC_SAMPLE)
    assert set(rlc) == {
        r["record"] for r in table if r["protocol"] == "frequency-response"
    }
    for name in bench.LED_RUNS:
        assert len(raw_records(SAMPLE / bench.EXPORTS / name)) == 13


def test_the_manifest_and_the_card_list_every_committed_file():
    """MANIFEST.tsv (the packager's) and the card's samples name the same
    files with the same sizes and SHA-256 values as the files committed."""
    listed = manifest()
    card = yaml.safe_load((REGISTRY_DIR / f"{bench.DATASET}.yaml").read_text())
    files = {
        p.relative_to(SAMPLE).as_posix(): p.read_bytes()
        for p in SAMPLE.rglob("*")
        if p.is_file()
    }
    assert set(listed) == set(files) - {packager.MANIFEST}
    assert {s["path"] for s in card["samples"]} == set(files)
    for path, row in listed.items():
        assert int(row["bytes"]) == len(files[path])
        assert row["sha256"] == hashlib.sha256(files[path]).hexdigest()
    changed = {p for p, r in listed.items() if r["original_sha256"]}
    assert changed == {
        f"exports/{f.name}/run.json" for f in bench.export_dirs(SAMPLE)
    } | {f"exports/{bench.RLC_SAMPLE}/raw.csv"}
    # The subset's original is the file the export's evidence log names.
    evidence = json.loads(
        (SAMPLE / bench.EXPORTS / bench.RLC_SAMPLE / bench.EVIDENCE).read_text()
    )
    raw = next(
        a for a in evidence["attempts"][0]["artifacts"] if a["path"] == "raw.csv"
    )
    assert (
        listed[f"exports/{bench.RLC_SAMPLE}/raw.csv"]["original_sha256"]
        == raw["sha256"]
    )
    readme = (SAMPLE / packager.README).read_text(encoding="utf-8")
    assert card["archive"]["sha256"] in readme
    assert str(card["archive"]["bytes"]) in readme


def test_no_committed_file_holds_a_device_serial():
    """The pilot's committed run record holds the device's serial (left as
    it is by the owner's decision); this dataset's files never do. The
    serial is read from that record, not written here."""
    pilot = json.loads(
        (SAMPLES_DIR / "ad3-rlc-pilot" / "capacitor" / "run.json").read_text()
    )
    serial = pilot["run"]["device"]["serial"].encode()
    assert serial
    for path in [
        *SAMPLE.rglob("*"),
        DECLARATION,
        REGISTRY_DIR / f"{bench.DATASET}.yaml",
    ]:
        if path.is_file():
            assert serial not in path.read_bytes(), path.name


def test_the_archive_doi_is_the_reserved_one():
    """The DOI the owner reserved is in the declaration, in the files the
    packager makes from it, and on the card; no placeholder is left."""
    declared = tomllib.loads(DECLARATION.read_text(encoding="utf-8"))
    assert declared["dataset"]["doi"] == DOI
    card_path = ROOT / "data" / "registry" / f"{bench.DATASET}.yaml"
    card = card_path.read_text(encoding="utf-8")
    assert DOI in card
    for name in (packager.README, packager.CITATION):
        text = (SAMPLE / name).read_text(encoding="utf-8")
        assert DOI in text and "NOT-YET" not in text


def same_table(replayed: list[dict[str, str]], recorded: list[dict[str, str]]) -> None:
    """The same rows and columns; the words exactly, the numbers to 1e-9
    (the live run read them from the device's samples, the replay from
    raw.csv, which keeps 12 significant digits; the evaluator's results
    are recomputed from raw.csv in both and agree exactly)."""
    assert [list(r) for r in replayed] == [list(r) for r in recorded]
    for a, b in zip(replayed, recorded, strict=True):
        for key, value in b.items():
            try:
                number = float(value)
            except ValueError:
                assert a[key] == value
                continue
            assert float(a[key]) == pytest.approx(number, rel=1e-9, abs=1e-12), key


def replay(folder: Path, out: Path, protocols: tuple[str, ...] | None = None):
    sample, plan, mode = lab.read_campaign_export(folder)
    assert mode == "live"
    if protocols is not None:
        plan = dataclasses.replace(plan, protocols=protocols)
    return lab.run_campaign(
        plan,
        out,
        mode="recorded",
        sample=sample,
        recorded_live=True,
        confirmed=True,
    )


def test_the_replay_reproduces_the_sampled_frequency_response(tmp_path):
    """The first RLC campaign of 2026-11-26, its frequency-response records
    replayed by the recorded adapter with the plan narrowed to that
    protocol (the adaptive route measures it first): the same 31 settings in
    the same order, and the recorded fit exactly."""
    folder = SAMPLE / bench.EXPORTS / bench.RLC_SAMPLE
    result = replay(folder, tmp_path / "rlc", ("frequency-response",))
    assert result.segment.status == "complete"
    recorded = bench.read_run(folder)["evaluation"]["frequency-response"]
    assert result.evaluation["frequency-response"] == recorded
    table = [
        r
        for r in bench.read_measurements(folder)
        if r["protocol"] == "frequency-response"
    ]
    replayed = bench.read_measurements(tmp_path / "rlc")
    # The export's table has the ring-downs' columns too, empty in these rows.
    columns = list(replayed[0])
    assert all(v == "" for r in table for k, v in r.items() if k not in columns)
    same_table(replayed, [{k: r[k] for k in columns} for r in table])


@pytest.mark.parametrize("name", bench.LED_RUNS)
def test_the_replay_reproduces_both_led_runs(tmp_path, name):
    """Each LED-pair run replayed whole: the recorded evaluation (points,
    characteristic, held-out check) and the measurement table exactly."""
    folder = SAMPLE / bench.EXPORTS / name
    result = replay(folder, tmp_path / name)
    assert result.segment.status == "complete"
    assert result.evaluation == bench.read_run(folder)["evaluation"]
    same_table(
        bench.read_measurements(tmp_path / name), bench.read_measurements(folder)
    )


def test_the_recorded_results_are_the_dossiers():
    """The dossier's statements, read from the exports as recorded and from
    the module's re-analysis (the -90 degree crossing)."""
    found = bench.campaigns(SAMPLE)
    rlc = [c for c in found if c.circuit == "series-rlc"]
    led = [c for c in found if c.circuit == "led-pair"]
    assert all(c.status == "completed" and c.verdict is False for c in found)
    assert all(c.invalid == 0 for c in found)
    # Q: the two protocols disagree (k = 2) in every campaign, the ring-down
    # higher; f0: they agree in 25 of 27.
    assert all(c.q_agree is False for c in rlc)
    assert all(c.q_ringdown.value > c.q_response.value for c in rlc)
    assert min(c.q_sigmas for c in rlc) > 10
    disagree = [c.name for c in rlc if not c.f0_agree]
    assert disagree == ["2026-11-25-series-rlc", "2026-11-26-series-rlc-run16"]
    assert min(c.q_response.value for c in rlc) > 1.47
    assert max(c.q_response.value for c in rlc) < 1.50
    assert min(c.q_ringdown.value for c in rlc) > 1.63
    assert max(c.q_ringdown.value for c in rlc) < 1.69
    chi2 = [c.reduced_chi2 for c in rlc]
    assert min(chi2) > 3_400 and max(chi2) < 5_500
    # The -90 degree crossing on 2026-11-26 against minutes after plug-in.
    folders = {f.name: f for f in bench.export_dirs(SAMPLE)}
    crossing = {c.name: bench.phase_crossing_hz(folders[c.name]) / 1e3 for c in rlc}
    minutes = {c.name: bench.minutes_after_plug_in(c) for c in rlc}
    first = "2026-11-26-series-rlc"
    assert minutes[first] == pytest.approx(4.9, abs=0.1)
    assert crossing[first] == pytest.approx(49.99, abs=0.005)
    ten = [f"2026-11-26-series-rlc-run{k}" for k in range(2, 12)]
    assert all(7.5 < minutes[n] < 9 for n in ten)
    assert 49.51 < min(crossing[n] for n in ten) < max(crossing[n] for n in ten) < 49.59
    day = [c.name for c in rlc if minutes[c.name] is not None]
    lowest = min(day, key=crossing.get)
    assert lowest == "2026-11-26-series-rlc-run15"
    assert crossing[lowest] == pytest.approx(48.46, abs=0.005)
    assert minutes[lowest] == pytest.approx(42.8, abs=0.1)
    assert crossing["2026-11-26-series-rlc-run24"] == pytest.approx(48.92, abs=0.005)
    assert [round(crossing[c.name], 2) for c in rlc[:3]] == [50.18, 49.83, 49.67]
    assert all(minutes[c.name] is None for c in rlc[:3])
    # The LED pair: the held-out check fails in both runs; the fitted
    # ideality differs between them on nearly the same points.
    assert all(c.held_out_agree is False for c in led)
    assert led[0].ideality.value == pytest.approx(50.9, abs=0.05)
    assert led[0].ideality.se == pytest.approx(5.50, abs=0.005)
    assert led[1].ideality.value == pytest.approx(2.32, abs=0.005)
    assert led[1].ideality.se == pytest.approx(0.034, abs=0.0005)
    for name in bench.LED_RUNS:
        top = bench.amplitude_points(folders[name])[-1]
        assert top["amplitude_v"] == 2.0
        assert top["gain"] == pytest.approx(0.973, abs=0.0005)
        assert top["h3"] == pytest.approx(0.020, abs=0.0006)
