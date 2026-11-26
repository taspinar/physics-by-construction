"""The original track of the Scientific Research Workspace (F155 part 2): the
coil-loss follow-up of ``ad3-rlc-pilot``, its frozen registration, the
registered rules with their positive controls and boundary cases, the owner's
session inputs and their refusals, and the track end to end without a bench
session or a model account."""

import hashlib
import itertools
import json
import shutil
import subprocess
import sys
import tomllib

import numpy as np
import pytest

from pbc.data import REPO_ROOT
from pbc.products.research_workspace import (
    coil,
    controls,
    followup,
    graph,
    original,
    project,
)
from pbc.products.research_workspace import log as worklog
from pbc.products.research_workspace import registration as reg
from pbc.products.research_workspace.__main__ import main

EXAMPLE = REPO_ROOT / "products/research-workspace/examples/coil-loss"
PLAN = REPO_ROOT / ".agents/plans/619-research-workspace.md"
# The digest of the frozen registration (Issue #619, "The registration is
# frozen"): merge commit d4d9a16 of pull request 625.
FROZEN = "3e4cfd1ae9a4fde8e116df21c3b5035ef05b63322605f94e25a466ee13f0a429"
FREEZE = original.freeze_of(EXAMPLE / "freeze.toml")


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    directory = tmp_path_factory.mktemp("project") / "coil"
    project.run(EXAMPLE, directory)
    return directory


@pytest.fixture(scope="module")
def noise():
    return controls.noise_levels()


def _session(tmp_path, name, noise, **kwargs):
    circuit, channels = controls.circuits()[name]
    return controls.write_session(
        tmp_path / name, circuit, channels, 0, noise, **kwargs
    )


def _make_live(directory):
    """Give a simulated session the run records of the live bench."""
    for path in directory.glob("*/run.json"):
        record = json.loads(path.read_text())
        run = record["run"]
        run["mode"] = "live"
        run["device"] = {
            "calibration": "channel 1 (source) on the 5 V range, channel 2"
            " (response) on the 50 V range"
        }
        conditions = {"pcb_temperature_c": 45.0, "usb_voltage_v": 5.06}
        run["configuration"]["conditions_at_start"] = conditions
        run["configuration"]["conditions_at_end"] = conditions
        path.write_text(json.dumps(record))


def _readings(directory, edit):
    """Rewrite the readings of a session: ``edit`` takes and returns the
    list of the readings, each a dict of the template's fields."""
    path = directory / followup.READINGS
    readings = tomllib.loads(path.read_text())["reading"]
    lines = []
    for reading in edit(readings):
        lines.append("[[reading]]")
        lines += [f"{k} = {json.dumps(v)}" for k, v in reading.items()]
    path.write_text("\n".join(lines) + "\n")


def _first(**changes):
    """An edit that changes the first reading's fields."""
    return lambda readings: [{**readings[0], **changes}, *readings[1:]]


# -- the registration ----------------------------------------------------------


def test_the_registration_is_the_frozen_text_byte_for_byte():
    copied = (EXAMPLE / "registration.md").read_bytes()
    assert hashlib.sha256(copied).hexdigest() == FROZEN
    assert FREEZE.digest == FROZEN and FREEZE.frozen
    # The plan's text between the markers is unchanged since the freeze.
    lines = PLAN.read_text(encoding="utf-8").splitlines(keepends=True)
    begin = lines.index("<!-- registration:begin -->\n")
    end = lines.index("<!-- registration:end -->\n")
    assert "".join(lines[begin + 1 : end]).encode() == copied


def test_the_registration_as_data_discriminates_over_five_explanations():
    plan = reg.load(EXAMPLE / "registration.toml")
    assert reg.problems(plan) == []
    assert len(plan.explanations) == 5
    predicted = {e.name: e.predicts for e in plan.explanations}
    for name, (rule, outcome) in coil.EXPLANATIONS.items():
        assert predicted[name] == (f"{rule}: {outcome}",)
    # "exceeds" and "inconclusive" are outcomes that no explanation predicts.
    owned = {o for e in plan.explanations for o in e.predicts}
    assert {"G1: exceeds", "G1: inconclusive", "G2: inconclusive"} <= (
        set(plan.outcomes) - owned
    )


def test_a_changed_registration_text_is_refused(tmp_path):
    example = tmp_path / "example"
    shutil.copytree(EXAMPLE, example)
    text = (example / "registration.md").read_text()
    (example / "registration.md").write_text(text.replace("5 ohm", "6 ohm", 1))
    with pytest.raises(project.ProjectRefused, match="not the frozen registration"):
        project.run(example, tmp_path / "p")


# -- the analysis of the existing sweeps -----------------------------------------


def test_the_pilot_analysis_reads_the_dossiers_numbers():
    pilot = coil.pilot_analysis()
    assert pilot["L_H"] == pytest.approx(0.861e-3, rel=2e-3)
    assert pilot["C_F"] == pytest.approx(14.55e-9, rel=2e-3)
    assert pilot["R_L0"] == pytest.approx(62.7, abs=0.1)
    assert len(pilot["R_L"]) == coil.COARSE_POINTS
    # The pilot cannot separate a mismatch from a growing loss: a mismatch at
    # the registration's own thresholds moves Rise by more than 3 u_hi.
    unchanged = next(
        r for r in pilot["sensitivity"] if r["dphi_deg"] == 0 and r["dg"] == 0
    )
    assert unchanged["Rise"] == pytest.approx(pilot["Rise"])
    moved = [
        abs(r["Rise"] - pilot["Rise"])
        for r in pilot["sensitivity"]
        if abs(r["dphi_deg"]) == 0.3 and r["dg"] == 0
    ]
    assert min(moved) > 3 * pilot["u_hi"]


# -- the rules, at and around every threshold ------------------------------------


@pytest.mark.parametrize(("rule", "inputs", "expected"), controls.BOUNDARY_CASES)
def test_every_boundary_case_gives_the_registered_outcome(rule, inputs, expected):
    got, predicates = controls.outcome_of(rule, inputs)
    assert got == expected
    assert sum(predicates.values()) <= 1


def test_the_inconclusive_branches_and_exceeds_are_results():
    # G1: undecidable first, whatever D is.
    for d in (-50.0, 0.0, 50.0):
        assert coil.rule_g1(d, 5.5) == coil.INCONCLUSIVE
    # Between 2 u and 3 u, and above 3 u but not above 5 ohm.
    assert coil.rule_g1(5.0, 2.0) == coil.INCONCLUSIVE
    assert coil.rule_g1(4.0, 1.0) == coil.INCONCLUSIVE
    # Below -2 u but not below -3 u, and below -3 u: exceeds.
    assert coil.rule_g1(-5.0, 2.0) == coil.INCONCLUSIVE
    assert coil.rule_g1(-7.0, 2.0) == coil.EXCEEDS
    # G2: Rise between 2 u_hi and 3 u_hi; Rise <= 2 u_hi without a measurable
    # mismatch; a measurable mismatch whose correction does not halve P.
    assert coil.rule_g2(True, 2.5, 1.0, 2.0, 0.1) == coil.INCONCLUSIVE
    assert coil.rule_g2(False, 2.5, 1.0, 2.0, 0.1) == coil.INCONCLUSIVE
    assert coil.rule_g2(False, 1.0, 1.0, 2.0, 0.1) == coil.INCONCLUSIVE
    assert coil.rule_g2(True, 1.0, 1.0, 2.0, 1.5) == coil.INCONCLUSIVE


def test_no_two_outcomes_of_a_rule_hold_together():
    grid = (-20.0, -6.0, -4.0, 0.0, 4.0, 5.0, 6.0, 20.0)
    for d, u in itertools.product(grid, (0.5, 1.0, 2.0, 5.0)):
        assert sum(coil.g1_predicates(d, u).values()) <= 1
    for measurable, rise, p1 in itertools.product(
        (True, False), (-1.0, 0.0, 2.0, 2.5, 3.0, 3.5, 10.0), (0.0, 1.0, 1.5)
    ):
        assert sum(coil.g2_predicates(measurable, rise, 1.0, 2.0, p1).values()) <= 1


def test_the_mismatch_thresholds_are_strict():
    assert not coil.mismatch_measurable(np.array([0.3, -0.3]), np.array([0.003]))
    assert coil.mismatch_measurable(np.array([-0.30001]), np.array([0.0]))
    assert coil.mismatch_measurable(np.array([0.0]), np.array([-0.00301]))


def test_the_meter_model_on_constructed_readings():
    for case in controls.meter_cases():
        assert case["passed"], case
    # The third party's 1.2 % only enlarges the gain part.
    readings = [controls._reading("Z1", k, 0.2) for k in (1, 2, 3)]
    readings += [controls._reading("Z2", k, 0.2) for k in (1, 2, 3)]
    readings += [controls._reading("R_dc_bb", k, 63.0) for k in (1, 2, 3)]
    registered = coil.meter_value(readings, "R_dc_bb")
    third = coil.meter_value(readings, "R_dc_bb", p=coil.P_SENSITIVITY)
    assert third.u_ng == registered.u_ng
    assert third.parts["u_gain"] == pytest.approx(1.5 * registered.parts["u_gain"])
    low, high = coil.resistor_band()
    assert low == pytest.approx(97.9, abs=0.01) and high == pytest.approx(
        102.1, abs=0.01
    )


# -- the positive controls (simulated sessions) ------------------------------------


def test_each_rule_returns_what_its_explanation_predicts(built):
    trial = json.loads((built / "states/controls.json").read_text())
    assert trial["passed"]
    assert set(trial["results"]) == set(controls.EXPECTED)
    for name, rows in trial["results"].items():
        assert len(rows) == len(controls.SEEDS)
        for row in rows:
            assert row["misses"] == [], (name, row)
    # The same-node sweep resolves the thresholds of a measurable mismatch.
    assert trial["resolution"]["max_abs_dphi_deg"] < coil.MISMATCH_PHASE_DEG
    assert trial["resolution"]["max_abs_dg"] < coil.MISMATCH_GAIN


def test_the_precondition_not_met_scopes_the_conclusions(tmp_path, noise):
    directory = _session(tmp_path, "other-parts", noise)
    result = followup.evaluate(directory, FREEZE, live=False)
    outcome = result.outcome
    assert outcome.precondition is False
    assert outcome.g1 != coil.NOT_EVALUATED  # scoped to the circuit of M1 to M5
    assert outcome.g1_pilot == coil.NOT_EVALUATED
    assert outcome.g2 == coil.REMAINS  # carried over
    assert any("scoped to the circuit of M1 to M5" in n for n in outcome.notes)
    met = followup.evaluate(
        _session(tmp_path, "pilot-parts", noise), FREEZE, live=False
    )
    assert met.outcome.precondition is True
    assert met.outcome.g1_pilot == met.outcome.g1 == coil.SHORT


# -- the session: its template, its refusals, the freeze date ----------------------


def test_the_templates_are_refused_until_filled_in(tmp_path):
    directory = tmp_path / "session"
    directory.mkdir()
    shutil.copy(EXAMPLE / "session-template.toml", directory / followup.SESSION)
    shutil.copy(EXAMPLE / "readings-template.toml", directory / followup.READINGS)
    with pytest.raises(followup.SessionRefused) as refused:
        followup.load(directory)
    text = str(refused.value)
    assert "session.plugged_in: no time" in text
    assert "room.temperature_c" in text
    assert "no export directory 'M0'" in text
    assert "value_ohm: '' is not a number" in text


@pytest.mark.parametrize(
    ("edit", "words"),
    [
        (lambda readings: readings[:-1], "Z2 needs the readings 1, 2, 3"),
        (lambda readings: [*readings, readings[-1]], "Z2 needs the readings 1, 2, 3"),
        (
            lambda readings: [
                {k: v for k, v in readings[0].items() if k != "time"},
                *readings[1:],
            ],
            "missing \\['time'\\]",
        ),
        (_first(when="now"), "unknown \\['when'\\]"),
        (_first(meter="Mastech MAS830B"), "the registration's is Mastech MAS830BC"),
        (_first(p_percent=1.2), "p is 1.2 %"),
        (_first(resolution_ohm=1), "resolution"),
        (_first(range_ohm=20), "no registered range"),
        (_first(time="2026-12-01T15:01:00"), "no offset from UTC"),
        (_first(quantity="Z0"), "unknown quantity"),
        (_first(value_ohm=""), "value_ohm: '' is not a number"),
    ],
)
def test_a_malformed_readings_file_is_refused(tmp_path, noise, edit, words):
    directory = _session(tmp_path, "DC", noise)
    _readings(directory, edit)
    with pytest.raises(followup.SessionRefused, match=words):
        followup.load(directory, live=False)


def test_a_simulated_run_record_is_not_live_evidence(tmp_path, noise):
    directory = _session(tmp_path, "DC", noise)
    with pytest.raises(followup.SessionRefused, match="not live") as refused:
        followup.load(directory)
    assert "no conditions_at_start" in str(refused.value)
    _make_live(directory)
    assert followup.load(directory).used("M1") is not None


@pytest.mark.parametrize("measurement", ["M0", "M1", "M2", "M3", "M5"])
def test_a_sweep_measured_before_the_freeze_is_refused(tmp_path, noise, measurement):
    directory = _session(
        tmp_path, "DC", noise, times={measurement: "2026-11-26T16:43:25+01:00"}
    )
    with pytest.raises(followup.SessionRefused, match=f"{measurement} attempt 1"):
        followup.evaluate(directory, FREEZE, live=False)


def test_a_reading_measured_before_the_freeze_is_refused(tmp_path, noise):
    directory = _session(tmp_path, "DC", noise)
    _readings(directory, _first(time="2026-11-26T15:43:25Z"))
    with pytest.raises(followup.SessionRefused, match="M4 Z1 reading 1"):
        followup.evaluate(directory, FREEZE, live=False)
    # At the freeze itself, the evidence is admitted.
    _readings(directory, _first(time="2026-11-26T15:43:26Z"))
    followup.admit(followup.load(directory, live=False), FREEZE)


def _add_attempts(directory, measurement, outcomes):
    """Rewrite the sweep entries of ``measurement`` with ``outcomes``, the
    first attempt in its own directory, the others copies of it."""
    text = (directory / followup.SESSION).read_text()
    entry = (
        f'[[sweep]]\nmeasurement = "{measurement}"\nattempt = 1\n'
        f'directory = "{measurement}"\noutcome = "valid"'
    )
    assert entry in text
    new = []
    for number, outcome in enumerate(outcomes, start=1):
        name = measurement if number == len(outcomes) else f"{measurement}-{number}"
        if name != measurement:
            shutil.copytree(directory / measurement, directory / name)
        reason = '\nreason = "the capture was invalid"' if outcome == "failed" else ""
        new.append(
            f'[[sweep]]\nmeasurement = "{measurement}"\nattempt = {number}\n'
            f'directory = "{name}"\noutcome = "{outcome}"{reason}'
        )
    (directory / followup.SESSION).write_text(text.replace(entry, "\n".join(new)))


def test_a_failed_run_is_repeated_once_and_a_second_failure_stops(tmp_path, noise):
    once = _session(tmp_path / "a", "AC", noise)
    _add_attempts(once, "M2", ["failed", "valid"])
    result = followup.evaluate(once, FREEZE, live=False)
    assert result.status == followup.COMPUTED and result.outcome.g1 == coil.SHORT
    assert (
        len(
            [s for s in followup.load(once, live=False).sweeps if s.measurement == "M2"]
        )
        == 2
    )

    twice = _session(tmp_path / "b", "AC", noise)
    _add_attempts(twice, "M2", ["failed", "failed"])
    stopped = followup.evaluate(twice, FREEZE, live=False)
    assert stopped.status == followup.INCONCLUSIVE
    assert stopped.outcome.g1 == stopped.outcome.g2 == coil.INCONCLUSIVE
    assert "M2 failed twice" in stopped.reasons[0]

    repeated = _session(tmp_path / "c", "AC", noise)
    _add_attempts(repeated, "M1", ["valid", "valid"])
    with pytest.raises(followup.SessionRefused, match="no valid sweep is repeated"):
        followup.load(repeated, live=False)


def test_the_deviations_from_the_procedure_are_reported(tmp_path, noise):
    directory = _session(
        tmp_path,
        "DC",
        noise,
        times={"M0": "2026-12-01T13:30:00+01:00", "M5": "2026-12-01T14:12:00+01:00"},
    )
    result = followup.evaluate(directory, FREEZE, live=False)
    text = " ".join(result.deviations)
    assert "30 minutes after the plug-in" in text
    assert "M5 was measured before M4 Z2" in text
    assert result.outcome.g1 == coil.ACCOUNTED  # a deviation changes no rule


# -- the track end to end ------------------------------------------------------------


def test_the_original_track_runs_end_to_end_without_a_session(built):
    assert project.verify(built) == []
    status = project.summary(built)["status"]
    for key in ("G1", "G2", "precondition"):
        assert status[key] == "not evaluated"
    for key in ("pilot-loss", "pilot-sensitivity", "controls", "boundaries"):
        assert status[key] == "completed"
    report = (built / "report.md").read_text()
    assert report.splitlines()[2].startswith(
        "> This report is a summary of the project's records, not a proof"
    )
    assert "Exploratory" in report or "exploratory" in report
    run = json.loads((built / "run.json").read_text())
    assert run["track"] == "original" and run["followup"] == "not evaluated"
    assert run["registration"]["digest"] == FROZEN
    assert run["registration"]["commit"].startswith("d4d9a16")


def test_the_log_begins_with_the_freeze_and_the_outcome_code(built):
    log = worklog.load(built / "log.json")
    first, second = log.entries[:2]
    assert first.content["subject"] == "registration"
    assert FROZEN in first.content["reason"] and "d4d9a16" in first.content["reason"]
    assert "2026-11-26T15:43:26" in first.content["reason"]
    assert second.content["subject"] == "outcome-code"
    assert graph.outcome_code_digest() in second.content["reason"]
    assert {k: worklog.state(log, k) for k in log.findings()} == {
        "G1": "open",
        "G2": "open",
    }


def test_every_number_of_the_investigation_report_resolves(built):
    data = project.summary(built)
    text, written = original.render_markdown(data)
    assert len(written) > 50
    from pbc.products.research_workspace import report as rep

    assert rep.number_problems(written, data["records"]) == []
    assert text == (built / "report.md").read_text()


def test_a_session_measured_after_the_freeze_is_evaluated_in_the_project(
    tmp_path, noise
):
    example = tmp_path / "example"
    shutil.copytree(EXAMPLE, example)
    controls.write_session(
        example / original.SESSION_DIR, *controls.circuits()["AC"], 0, noise
    )
    _make_live(example / original.SESSION_DIR)
    directory = tmp_path / "project"
    project.run(example, directory)
    assert project.verify(directory) == []
    status = project.summary(directory)["status"]
    assert status["G1"] == status["G2"] == "completed"
    state = json.loads((directory / "states/followup.json").read_text())
    assert state["outcome"]["g1"] == coil.SHORT
    assert state["outcome"]["g2"] == coil.REMAINS
    report = (directory / "report.md").read_text()
    assert "AC" in report
    # M1 against M0: the crossing and the phase at each coarse frequency.
    assert "crossing_M1_minus_M0_hz" in report
    assert report.count("| M1 - M0 [deg] |") == 1
    rows = [r for r in report.splitlines() if r.startswith("| 200.0 |")]
    assert len(rows) == 2  # the pilot's R_L table and the follow-up's table
    log = worklog.load(directory / "log.json")
    assert worklog.state(log, "G1") == worklog.RESOLVED
    # A changed reading after the run is named by verify.
    readings = directory / "inputs" / original.SESSION_DIR / followup.READINGS
    readings.write_text(readings.read_text().replace("20.", "21.", 1))
    assert "the bench session's files changed after the run" in project.verify(
        directory
    )


def test_the_outcome_code_covers_the_original_tracks_rules(built, tmp_path):
    for name in ("coil.py", "followup.py", "controls.py", "original.py"):
        assert name in graph.OUTCOME_MODULES
    assert "ad3_rlc_pilot.py" in graph.outcome_file_digests()
    assert "original_view.py" in graph.NOT_OUTCOME
    copy = tmp_path / "copy"
    shutil.copytree(built, copy)
    run = json.loads((copy / "run.json").read_text())
    run["outcome_files"]["coil.py"] = "0" * 64
    run["outcome_code"] = "changed"
    (copy / "run.json").write_text(json.dumps(run))
    problems = project.verify(copy)
    assert any("changed: coil.py" in p for p in problems)


def test_the_view_is_static_and_the_agent_commands_are_refused(built, tmp_path):
    out = tmp_path / "view.html"
    assert main(["view", "--project", str(built), "--out", str(out)]) == 0
    page = out.read_text()
    assert "<script" not in page and "not evaluated" in page
    assert 'alt="' in page and "registration" in page
    assert main(["review", "--project", str(built)]) == 1


def test_the_command_line_runs_the_original_track(tmp_path):
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pbc.products.research_workspace",
            "run",
            "--example",
            str(EXAMPLE),
            "--project",
            str(tmp_path / "p"),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert completed.returncode == 0, completed.stderr
    assert (tmp_path / "p" / "view.html").is_file()
