"""The coil-loss follow-up's dataset (``ad3-rlc-coil-followup``, F155 part
2b, Issue #619): the committed part parses and is the packager's output,
the device serial is replaced everywhere, and the frozen registration's
rules, applied in CI to the repository's part with the pinned outcome code,
give the evaluation of 2026-11-28 (its outcomes, its quantities to the
product's cross-platform tolerance, its report, ledger, and log), with the
two differences the dossier explains. No test reads Zenodo or the archive."""

import csv
import hashlib
import json
import re
import shutil
import tomllib
from html import escape

import pytest
import yaml

from pbc.data import REGISTRY_DIR, REPO_ROOT, SAMPLES_DIR
from pbc.data import publish as packager
from pbc.data.reference import ad3_rlc_coil_followup as followup_data
from pbc.products.physics_lab import agent_campaign
from pbc.products.research_workspace import __main__ as workspace_cli
from pbc.products.research_workspace import followup, original, project
from pbc.products.research_workspace import log as worklog

SAMPLE = SAMPLES_DIR / followup_data.DATASET
DECLARATION = REPO_ROOT / "data" / "publish" / f"{followup_data.DATASET}.toml"
CARD = REGISTRY_DIR / f"{followup_data.DATASET}.yaml"
EXAMPLE = REPO_ROOT / "products" / "research-workspace" / "examples" / "coil-loss"
RECORD = EXAMPLE / "followup-2026-11-28.toml"
SESSION = followup_data.session_dir(SAMPLE)
EVALUATION = SESSION / followup_data.EVALUATION
# The DOI of the archive: the packager's placeholder until the owner
# reserves the DOI in the Zenodo draft; then this constant, the declaration,
# and the packager's files change together.
DOI = "10.5281/zenodo.24622131"
# The files of a session the workspace reads (its templates): the two
# records and the sweeps' folders; the notes and the evaluation are not.
SWEEPS = ("M0", "M0-repeat", "M1", "M2", "M3", "M5")
# The follow-up's registered quantities as the evaluation of 2026-11-28
# computed them (its states/followup.json, whose SHA-256 its ledger.json
# records; the recomputation on the recording machine gives that file byte
# for byte). Compared to agent_campaign.TOLERANCE relative.
VALUES = {
    "C_F": 4.3576561113546154e-07,
    "D": 2.7684155937481836,
    "L_H": 2.591587553990263e-05,
    "M5_C_relative": 0.06361415870376885,
    "M5_L_relative": -0.006903337466049986,
    "M5_R_L0_difference": -0.20867317834845212,
    "P0_deg": 6.386546299097427,
    "P1_deg": 5.823552949582509,
    "R_L0": 2.418415593748184,
    "R_dc": 0.2500000000000018,
    "R_dc_bb": -0.34999999999999964,
    "R_s_bb": 3.083333333333335,
    "Rise": -0.5320846064637295,
    "crossing_M0_hz": 50673.157012935306,
    "crossing_M1_hz": 50605.285744870256,
    "crossing_M1_minus_M0_hz": -67.87126806504966,
    "dz": 2.5000000000000013,
    "g1_sensitivity_differs": 0.0,
    "identity_C_relative": -0.07657219605368226,
    "identity_L_relative": -0.0235849215009718,
    "identity_R_L0_difference": 0.485812148724992,
    "max_abs_dg": 0.01720422616009032,
    "max_abs_dphi_deg": 0.48780748361880627,
    "mismatch_measurable": 1.0,
    "pilot_C_F": 4.719000329784246e-07,
    "pilot_L_H": 2.6541863302378758e-05,
    "pilot_R_L0": 1.932603445023192,
    "resistor_band_high": 102.108,
    "resistor_band_low": 97.908,
    "u_G1": 1.004117607056506,
    "u_G1_p_1_2": 1.0042193711858363,
    "u_L": 0.6446616689936588,
    "u_R_dc": 0.7228425370254119,
    "u_R_dc_bb": 0.7697419134575781,
    "u_R_dc_bb_ng": 0.7697402159170329,
    "u_R_s_bb": 0.8023801629688553,
    "u_R_s_bb_ng": 0.8022537697705833,
    "u_hi": 0.2214355756526966,
    "z": 5.1499999999999995,
}
HEX = re.compile(r"\b[0-9a-f]{12,64}\b")
NUMBER = re.compile(r"-?\d+(?:\.\d+)?(?:e-?\d+)?")


def manifest() -> dict[str, dict[str, str]]:
    with (SAMPLE / packager.MANIFEST).open(encoding="utf-8") as handle:
        return {r["path"]: r for r in csv.DictReader(handle, delimiter="\t")}


def close(computed: float, recorded: float) -> bool:
    """Relative to agent_campaign.TOLERANCE; the absolute floor (1e-15)
    only serves a recorded zero."""
    return computed == pytest.approx(recorded, rel=agent_campaign.TOLERANCE, abs=1e-15)


def same_structure(computed, recorded, where: str = "") -> None:
    """The same keys, lengths, words, and flags; floats to the tolerance;
    the SHA-256 of a state (the digests that depend on its last bits) by
    form only."""
    if isinstance(recorded, dict):
        assert isinstance(computed, dict) and computed.keys() == recorded.keys(), where
        for key, value in recorded.items():
            if key in ("sha256", "digest", "previous") and isinstance(value, str):
                if value:
                    assert HEX.fullmatch(computed[key]), f"{where}.{key}"
                else:
                    assert computed[key] == "", f"{where}.{key}"
                continue
            same_structure(computed[key], value, f"{where}.{key}")
    elif isinstance(recorded, list):
        assert isinstance(computed, list) and len(computed) == len(recorded), where
        for k, value in enumerate(recorded):
            same_structure(computed[k], value, f"{where}[{k}]")
    elif isinstance(recorded, float):
        assert close(computed, recorded), where
    elif isinstance(recorded, str):
        assert HEX.sub("#", computed) == HEX.sub("#", recorded), where
    else:
        assert computed == recorded, where


def same_printed(computed: str, recorded: str) -> None:
    """Two reports equal in every word, and in every printed number to one
    unit of its last printed digit (a number rounded for print can move by
    one unit when the value moves by far less than the tolerance)."""
    a = HEX.sub("#", computed).splitlines()
    b = HEX.sub("#", recorded).splitlines()
    assert len(a) == len(b)
    for line_a, line_b in zip(a, b, strict=True):
        assert NUMBER.split(line_a) == NUMBER.split(line_b), line_b
        for x, y in zip(NUMBER.findall(line_a), NUMBER.findall(line_b), strict=True):
            places = len(y.split(".")[1]) if "." in y and "e" not in y else 0
            assert abs(float(x) - float(y)) <= 10.0**-places * 1.000001, line_b


@pytest.fixture(scope="module")
def evaluated(tmp_path_factory):
    """The original track run from the example with the repository's part
    of the session in ``session/``: the session's records and its sweeps'
    folders, as the workspace's templates name them."""
    root = tmp_path_factory.mktemp("coil-followup")
    example = root / "example"
    shutil.copytree(EXAMPLE, example)
    session = example / original.SESSION_DIR
    session.mkdir()
    for name in (followup.SESSION, followup.READINGS):
        shutil.copyfile(SESSION / name, session / name)
    for name in SWEEPS:
        shutil.copytree(SESSION / name, session / name)
    directory = root / "project"
    project.run(example, directory)
    return directory


def test_ad3_rlc_coil_followup_sample_parses():
    """Both folders in the declaration's order; every sweep's run record is
    live, at the registered input, names the device identifier, and has its
    points; the raw samples are those of the valid attempts, read whole; the
    workspace's reader accepts the session; the readings and the notes are
    there as recorded."""
    declared = tomllib.loads(DECLARATION.read_text(encoding="utf-8"))
    assert declared["exports"]["names"] == [
        followup_data.SESSION,
        followup_data.DIAGNOSTIC,
    ]
    folders = followup_data.sweep_dirs(SAMPLE)
    assert sorted(folders) == sorted([*SWEEPS, followup_data.DIAGNOSTIC])
    used = followup_data.used(SAMPLE)
    raw_kept = {
        name for name, f in folders.items() if (f / followup_data.RAW).is_file()
    }
    assert raw_kept == {a.directory for a in used.values()}
    assert raw_kept == {"M0-repeat", "M1", "M2", "M3", "M5"}
    for name, folder in folders.items():
        record = followup_data.read_run(folder)
        run = record["run"]
        assert (
            run["mode"] == "live" and run["device"]["serial"] == followup_data.DEVICE_ID
        )
        for key, value in followup.INPUT.items():
            assert run["configuration"][key] == value, (name, key)
        assert all(run["configuration"][k] for k in followup.CONDITIONS)
        points = followup_data.points(folder)
        assert len(points.frequency_hz) == (13 if name in ("M2", "M3", "M5") else 19)
        assert points.frequency_hz[0] == 5000.0 and points.frequency_hz[-1] == 200000.0
        if (folder / followup_data.RAW).is_file():
            with (folder / followup_data.RAW).open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            assert {int(r["point"]) for r in rows} == set(
                range(1, len(points.gain) + 1)
            )
        evidence = json.loads((folder / "evidence.json").read_text(encoding="utf-8"))
        assert evidence["record"]["environment"]["execution_mode"] == "live"
    attempts = followup_data.attempts(SAMPLE)
    assert [(a.measurement, a.attempt, a.outcome) for a in attempts] == [
        ("M0", 1, "failed"),
        ("M0", 2, "valid"),
        ("M1", 1, "valid"),
        ("M2", 1, "valid"),
        ("M3", 1, "valid"),
        ("M5", 1, "valid"),
    ]
    session = followup.load(SESSION)
    assert session.outcome_code_pin == followup.load_pin(followup.PINNED).digest
    readings = followup_data.readings(SAMPLE)
    assert len(readings) == 15
    assert {r.range_ohm for r in readings} == {200.0}
    for name in followup_data.NOTES:
        assert (SESSION / name).is_file()
    for name in ("run.json", "ledger.json", "log.json", "report.md"):
        assert (EVALUATION / name).is_file()
    assert not (EVALUATION / "view.html").exists()


def test_the_manifest_and_the_card_list_every_committed_file():
    """MANIFEST.tsv (the packager's) and the card's samples name the same
    files with the same sizes and SHA-256 values as the files committed;
    only the seven run records differ from their originals."""
    listed = manifest()
    card = yaml.safe_load(CARD.read_text(encoding="utf-8"))
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
        f"exports/{followup_data.SESSION}/{name}/run.json" for name in SWEEPS
    } | {f"exports/{followup_data.DIAGNOSTIC}/run.json"}
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
    for path in [*SAMPLE.rglob("*"), DECLARATION, CARD, RECORD]:
        if path.is_file():
            assert serial not in path.read_bytes(), path.name


def test_the_archive_doi_is_the_declared_one():
    """The DOI is one constant: in the declaration, in the files the
    packager makes from it, and on the card."""
    declared = tomllib.loads(DECLARATION.read_text(encoding="utf-8"))
    assert declared["dataset"]["doi"] == DOI
    assert DOI in CARD.read_text(encoding="utf-8")
    for name in (packager.README, packager.CITATION):
        assert DOI in (SAMPLE / name).read_text(encoding="utf-8")


def test_the_registered_rules_give_the_evaluations_outcomes(evaluated):
    """The outcomes and the follow-up's quantities, recomputed in CI from
    the repository's part with the pinned outcome code: G1 and G2
    inconclusive, the precondition not met, the deviation, the R_s_bb
    report, and every registered quantity to agent_campaign.TOLERANCE
    relative. The record of the verdicts states the same outcomes."""
    state = json.loads((evaluated / "states" / "followup.json").read_text())
    outcome = state["outcome"]
    assert state["status"] == followup.COMPUTED
    assert state["exploratory"] == [] and state["reasons"] == []
    assert outcome["g1"] == outcome["g2"] == "inconclusive"
    assert outcome["g1_pilot"] == "not evaluated"
    assert outcome["precondition"] is False and outcome["new_findings"] == []
    assert state["deviations"] == [
        "M0 started 4 minutes after the plug-in, earlier than the registered 45 minutes"
    ]
    assert outcome["notes"][0].startswith(
        "R_s_bb reads 3.08 ohm, outside 97.9 to 102.1 ohm"
    )
    assert outcome["values"].keys() == VALUES.keys()
    for key, value in VALUES.items():
        assert close(outcome["values"][key], value), key
    # The channels' relative response is M3's recorded points: dg = gain - 1
    # and dphi = the phase, at the 13 coarse frequencies.
    m3 = followup_data.points(SESSION / "M3")
    series = outcome["series"]
    for computed, recorded in zip(series["dphi_deg"], m3.phase_deg, strict=True):
        assert close(computed, recorded)
    for computed, gain in zip(series["dg"], m3.gain, strict=True):
        assert close(computed, gain - 1.0)
    assert close(max(abs(x) for x in series["dphi_deg"]), VALUES["max_abs_dphi_deg"])
    record = tomllib.loads(RECORD.read_text(encoding="utf-8"))
    expected = record["outcomes"]
    assert state["status"] == expected["status"]
    for key in ("g1", "g2", "g1_pilot", "precondition", "notes"):
        assert outcome[key] == expected[key], key
    assert state["deviations"] == expected["deviations"]
    assert record["dataset"] == followup_data.DATASET
    assert (SAMPLE / record["session"]) == SESSION


def test_the_recomputation_is_the_evaluation_of_2026_11_28(evaluated):
    """The report, ledger, and log are the evaluation's (words exactly,
    numbers to the tolerance or to the last printed digit); its run.json is
    the evaluation's but for the session's digests, which differ only where
    the dossier says: the six run records whose serial was replaced (each
    recorded digest is the original's in MANIFEST.tsv), the raw samples
    of the early M0, which are in the archive only (their digest is the one
    M0's evidence log names), and the figure and the report of each sweep,
    which are in the archive only (the repository commits no generated
    image, and each report links to its figure)."""
    same_printed(
        (evaluated / "report.md").read_text(encoding="utf-8"),
        (EVALUATION / "report.md").read_text(encoding="utf-8"),
    )
    for name in ("ledger.json", "log.json"):
        same_structure(
            json.loads((evaluated / name).read_text(encoding="utf-8")),
            json.loads((EVALUATION / name).read_text(encoding="utf-8")),
            name,
        )
    computed = json.loads((evaluated / "run.json").read_text(encoding="utf-8"))
    recorded = json.loads((EVALUATION / "run.json").read_text(encoding="utf-8"))
    assert computed.keys() == recorded.keys()
    for key in recorded.keys() - {"session"}:
        assert computed[key] == recorded[key], key
    listed = manifest()
    early_raw = next(
        a["sha256"]
        for a in json.loads((SESSION / "M0" / "evidence.json").read_text())["attempts"][
            0
        ]["artifacts"]
        if a["path"] == "raw.csv"
    )
    differs = set()
    for path, digest in recorded["session"].items():
        if computed["session"].get(path) == digest:
            continue
        differs.add(path)
        if path == "M0/raw.csv":
            assert path not in computed["session"] and digest == early_raw
            continue
        if path.endswith(("/frequency-response.svg", "/report.md")):
            assert path not in computed["session"]
            assert not (SESSION / path).exists()
            continue
        row = listed[f"exports/{followup_data.SESSION}/{path}"]
        assert row["original_sha256"] == digest
        assert row["sha256"] == computed["session"][path]
    assert computed["session"].keys() <= recorded["session"].keys()
    assert differs == (
        {f"{name}/run.json" for name in SWEEPS}
        | {f"{name}/frequency-response.svg" for name in SWEEPS}
        | {f"{name}/report.md" for name in SWEEPS}
        | {"M0/raw.csv"}
    )


def test_the_verdicts_and_the_revised_claim_enter_the_log(evaluated, tmp_path):
    """Each decision of the record enters the project's log with the
    workspace's own command; the chain verifies, the decisions show in the
    view, and no decision changes what the evidence decided (G1 and G2
    stay inconclusive: a decision is never evidence)."""
    copy = tmp_path / "project"
    shutil.copytree(evaluated, copy)
    record = tomllib.loads(RECORD.read_text(encoding="utf-8"))
    subjects = [d["subject"] for d in record["decision"]]
    assert subjects == ["G1", "G2", "precondition", "coil-loss claim"]
    for d in record["decision"]:
        assert (
            workspace_cli.main(
                [
                    "decide",
                    "--project",
                    str(copy),
                    "--subject",
                    d["subject"],
                    "--decision",
                    d["decision"],
                    "--reason",
                    d["reason"],
                    "--revisit",
                    d["revisit"],
                    "--by",
                    d["by"],
                ]
            )
            == 0
        )
    assert project.verify(copy) == []
    log = worklog.load(copy / "log.json")
    decisions = [e.content for e in log.of(worklog.DECISION)]
    assert [c["subject"] for c in decisions[-4:]] == subjects
    assert decisions[-1]["decision"] == "revised"
    assert worklog.state(log, "G1") == worklog.INCONCLUSIVE
    assert worklog.state(log, "G2") == worklog.INCONCLUSIVE
    project.write_view(copy, copy / "view.html")
    view = (copy / "view.html").read_text(encoding="utf-8")
    for d in record["decision"]:
        assert escape(d["reason"], quote=False) in view or escape(d["reason"]) in view
