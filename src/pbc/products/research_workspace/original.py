"""The original track as a project: the coil-loss follow-up of
``ad3-rlc-pilot`` (F155 part 2), run end to end without a bench session and
without a model account.

Layout of a project directory of this track::

    inputs/            questions.toml, registration.toml, registration.md,
                       freeze.toml, outcome-code.toml (copied), session/ (the
                       bench session, if any)
    states/            pilot.json, controls.json, boundaries.json, followup.json
    ledger.json        the evidence ledger (pbc.evidence.records)
    archive.json       the question archive; assessments.json
    log.json           the follow-up log: the freeze and the outcome code's
                       identity first, then the findings G1 and G2
    run.json           the run record: the track, the registration and its
                       freeze, the inputs and the pilot's sample by digest,
                       the execution modes, the outcome code's identity
    report.md          the report export
    view.html          the static workspace view

The registration is the frozen text (``registration.md``, whose sha256 must be
the digest of ``freeze.toml``); ``registration.toml`` restates it for the
workspace's checks. The pilot's analysis is exploratory (its data chose the
thresholds). The positive controls are simulated. The follow-up's evidence is
``not evaluated`` until the owner's session is in ``inputs/session``; then it
is admitted only when measured after the freeze, and computed by the rules.
The outcome code's identity is pinned for the follow-up
(``outcome-code.toml``): a session evaluated by other code, or a pin later
than M1, is a deviation, and its outcomes are exploratory.
"""

import json
import platform
import shutil
import tomllib
from dataclasses import asdict
from pathlib import Path

import numpy as np

from pbc.data import REGISTRY_DIR, REPO_ROOT
from pbc.evidence import records
from pbc.evidence.records import (
    COMPLETED,
    DERIVED,
    FAILED,
    INCONCLUSIVE,
    MISSING,
    Artifact,
    Attempt,
    Claim,
    Evaluation,
    Ledger,
    RunRecord,
    digest_file,
)
from pbc.evidence.report import COMPUTED, Statement, validate
from pbc.products.research_workspace import coil, controls, followup, graph, questions
from pbc.products.research_workspace import log as worklog
from pbc.products.research_workspace import registration as reg
from pbc.products.research_workspace import report as rep
from pbc.research.ideas import Entry, Idea, verify_archive

TRACK = "original"
INPUTS = (
    "questions.toml",
    "registration.toml",
    "registration.md",
    "freeze.toml",
    followup.CODE,
)
SESSION_DIR = "session"
PILOT_FILES = tuple(
    f"data/samples/ad3-rlc-pilot/{sweep}/{name}"
    for sweep in ("capacitor", "rl-node")
    for name in ("raw.csv", "run.json")
)
EVALUATOR = "pbc.products.research_workspace evaluator, recomputation from the inputs"
PILOT = "pilot/analysis"
CONTROLS = "control/explanations"
BOUNDARIES = "control/boundaries"
FOLLOWUP = {
    "G1": "followup/G1",
    "G2": "followup/G2",
    "precondition": "followup/precondition",
}
MODES = {
    "pilot": "recorded (the committed sample of ad3-rlc-pilot); exploratory",
    "controls": "simulated (seeded sessions, the closed form of the circuit)",
    "boundaries": "constructed values at every threshold",
    "followup": "not run until the owner's bench session (M0 to M5)",
    "agent": "not run (no model account; the rules decide)",
}
SCOPE = (
    "the pilot's circuit of F140 on the owner's breadboard, as measured with"
    " the AD3 (the parts, the breadboard, the leads, and the instrument together)"
)
ASSUMPTIONS = (
    "The pilot's sweeps are read through the dataset's reader unchanged, at the"
    " 13 coarse frequencies; the nominal 100 ohm stands for R_s_bb until M4.",
    "The thresholds were chosen after seeing the pilot's data: the pilot's"
    " numbers are exploratory, only M1 to M5 are confirmatory.",
    "The simulated controls use the closed form of the series circuit with the"
    " pilot's own noise level, the registered input, and fixed seeds.",
    "The follow-up's outcomes are computed only from a session measured after"
    " the freeze, by the code whose identity the log records.",
)


class OriginalRefused(ValueError):
    """An input of the original track the workspace does not accept."""


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def is_example(example: Path) -> bool:
    return (Path(example) / "freeze.toml").is_file()


def freeze_of(path: Path) -> reg.Freeze:
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    return reg.Freeze(data["digest"], data["commit"], data["time"])


def registration_problems(inputs: Path) -> list[str]:
    """The frozen text must be the registration the freeze names."""
    freeze = freeze_of(inputs / "freeze.toml")
    found = []
    if digest_file(inputs / "registration.md") != freeze.digest:
        found.append(
            "registration.md is not the frozen registration: its sha256 differs"
            f" from the digest {freeze.digest[:16]} of freeze.toml"
        )
    if not freeze.frozen:
        found.append("the freeze names no commit on main")
    return found


def _record(plan_digest: str) -> RunRecord:
    return RunRecord(
        task="The coil-loss follow-up of ad3-rlc-pilot: why the ideal series RLC"
        " model fails on the pilot's circuit (G1, G2 of the frozen registration)",
        hypothesis="Each registered rule returns the outcome its explanation"
        " predicts, or inconclusive; the follow-up decides which",
        assumptions=ASSUMPTIONS,
        protocol_version="F155 part 2",
        split={
            "probed": "the pilot's two sweeps (exploratory) and the simulated controls",
            "held out": "M0 to M5 of the registration, made after part 2 is merged",
        },
        seeds=tuple(controls.SEEDS),
        budgets={"stages": 3, "seeds": len(controls.SEEDS)},
        code=graph.outcome_code_digest(),
        configuration=plan_digest,
        environment={"python": platform.python_version(), "numpy": np.__version__},
    )


def _rounded(value):
    """JSON-stable numbers: the states are compared by recomputation."""
    return json.loads(json.dumps(value))


def _attempt(ledger, root, attempt_id, candidate, status, diagnostics, path):
    artifacts = () if path is None else (Artifact.of(candidate, path, root, DERIVED),)
    ledger.add_attempt(
        Attempt(
            attempt_id, candidate, ledger.cycle, status, tuple(diagnostics), artifacts
        )
    )


def _evaluation(ledger, attempt_id, correct, metrics) -> None:
    attempt = ledger.attempt(attempt_id)
    ledger.add_evaluation(
        Evaluation(
            attempt_id,
            EVALUATOR,
            correct,
            metrics,
            {},
            attempt.artifacts,
            ledger.record.code,
            ledger.record.configuration,
        )
    )


def run(example: Path, directory: Path) -> Path:
    """Run the original track from ``example`` into the new project
    ``directory``; returns the report's path."""
    example, directory = Path(example), Path(directory)
    if directory.exists() and any(directory.iterdir()):
        raise OriginalRefused(
            f"{directory} is not empty: a project is never overwritten"
        )
    inputs = directory / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    for name in INPUTS:
        shutil.copyfile(example / name, inputs / name)
    if (example / SESSION_DIR).is_dir():
        shutil.copytree(example / SESSION_DIR, inputs / SESSION_DIR)

    budget, asked = questions.load(inputs / "questions.toml")
    names = {n for q in asked for n in q.datasets}
    cards = questions.cards_of(names, REGISTRY_DIR)
    assessments = {q.key: questions.assess(q, cards, budget) for q in asked}
    found = questions.selection_problems(asked, assessments)
    plan = reg.load(inputs / "registration.toml")
    found += reg.problems(plan)
    found += registration_problems(inputs)
    if found:
        raise OriginalRefused("; ".join(found))
    freeze = freeze_of(inputs / "freeze.toml")
    _write_json(
        directory / "archive.json",
        [asdict(e) for e in questions.archive(asked).entries],
    )
    _write_json(
        directory / "assessments.json", {k: asdict(a) for k, a in assessments.items()}
    )

    session = inputs / SESSION_DIR if (inputs / SESSION_DIR).is_dir() else None
    try:
        pin = followup.load_pin(inputs / followup.CODE)
    except followup.SessionRefused as reason:
        raise OriginalRefused(f"the outcome code's pin is refused: {reason}") from None
    try:
        result = followup.evaluate(session, freeze, code=pin)
    except followup.SessionRefused as reason:
        raise OriginalRefused(f"the bench session is refused: {reason}") from reason

    states = directory / "states"
    states.mkdir()
    ledger = Ledger(_record(reg.digest(plan)))

    pilot = _rounded(coil.pilot_analysis())
    _write_json(states / "pilot.json", pilot)
    _attempt(ledger, states, PILOT, "pilot", COMPLETED, (), states / "pilot.json")
    _evaluation(ledger, PILOT, True, {"R_L0": pilot["R_L0"]})

    trial = _rounded(controls.run_controls())
    _write_json(states / "controls.json", trial)
    status = COMPLETED if trial["passed"] else FAILED
    misses = [
        f"{name} seed {r['seed']}: {'; '.join(r['misses'])}"
        for name, rows in trial["results"].items()
        for r in rows
        if r["misses"]
    ]
    _attempt(
        ledger, states, CONTROLS, "controls", status, misses, states / "controls.json"
    )
    _evaluation(
        ledger, CONTROLS, trial["passed"], {"seeds": float(len(trial["seeds"]))}
    )

    bounds = _rounded(controls.run_boundaries())
    _write_json(states / "boundaries.json", bounds)
    _attempt(
        ledger,
        states,
        BOUNDARIES,
        "boundaries",
        COMPLETED if bounds["passed"] else FAILED,
        [
            f"{c['rule']} {c['inputs']}: {c['got']}"
            for c in bounds["cases"]
            if not c["passed"]
        ],
        states / "boundaries.json",
    )
    _evaluation(
        ledger, BOUNDARIES, bounds["passed"], {"cases": float(len(bounds["cases"]))}
    )

    followup_state = {
        "status": result.status,
        "outcome": result.outcome.as_dict(),
        "reasons": result.reasons,
        "deviations": result.deviations,
        "exploratory": result.exploratory,
        "records": result.records,
    }
    _write_json(states / "followup.json", _rounded(followup_state))
    for key, attempt_id in FOLLOWUP.items():
        if result.status == followup.NOT_EVALUATED:
            _attempt(ledger, states, attempt_id, key, MISSING, result.reasons, None)
            continue
        attempt_status = (
            COMPLETED if result.status == followup.COMPUTED else INCONCLUSIVE
        )
        _attempt(
            ledger,
            states,
            attempt_id,
            key,
            attempt_status,
            result.reasons,
            states / "followup.json",
        )
        _evaluation(ledger, attempt_id, True, {})

    for claim in claims_of(pilot, trial, bounds, followup_state):
        ledger.add_claim(claim)
    records.save(ledger, directory / "ledger.json")

    log = worklog.Log()
    log.decide(
        "registration",
        "frozen",
        f"the registration {freeze.digest} is frozen at the merge commit"
        f" {freeze.commit} of {freeze.time} (pull request 625, after the owner's"
        " approving review of its exact head)",
        "a change of the text between the markers is a new registration",
        "the owner (the merge)",
    )
    current = graph.outcome_code_digest()
    log.decide(
        "outcome-code",
        "the pinned code" if current == pin.digest else "not the pinned code",
        f"the identity of the outcome code: {current}; pinned for the follow-up"
        f" at {pin.time}: {pin.digest}",
        "a change of this code after M1 is a deviation, and its result exploratory",
        "the workspace (this run)",
    )
    for key, text in (
        ("G1", "Is the loss near the resonance the DC resistance or an AC loss?"),
        (
            "G2",
            "Are the rise and the phase residual of the circuit or of the channels?",
        ),
    ):
        log.find(key, key, worklog.REGISTERED, text, worklog.EVIDENCE, f"rule {key}")
        if result.status != followup.NOT_EVALUATED:
            outcome = getattr(result.outcome, key.lower())
            decided = (
                None
                if outcome in (coil.INCONCLUSIVE, coil.NOT_EVALUATED)
                or result.exploratory
                else True
            )
            log.evidence(
                key,
                f"rule {key}: {outcome}"
                + (", exploratory (not the pinned code)" if result.exploratory else ""),
                decided,
                digest_file(states / "followup.json"),
            )
    for number, text in enumerate(result.outcome.new_findings, start=1):
        log.find(
            f"new-{number}", "G1", worklog.REGISTERED, text, worklog.EVIDENCE, "rule G1"
        )
    worklog.save(log, directory / "log.json")

    _write_json(
        directory / "run.json",
        {
            "track": TRACK,
            "registration": {
                "key": plan.key,
                "digest": freeze.digest,
                "commit": freeze.commit,
                "time": freeze.time,
                "frozen": True,
                "data_digest": reg.digest(plan),
            },
            "inputs": {name: digest_file(inputs / name) for name in INPUTS},
            "session": None if session is None else _session_digests(session),
            "sample": {path: digest_file(REPO_ROOT / path) for path in PILOT_FILES},
            "modes": MODES,
            "outcome_code": graph.outcome_code_digest(),
            "outcome_code_pinned": pin.digest,
            "outcome_files": graph.outcome_file_digests(),
            "followup": result.status,
        },
    )
    write_exports(directory)
    return directory / "report.md"


def _session_digests(session: Path) -> dict[str, str]:
    return {
        p.relative_to(session).as_posix(): digest_file(p)
        for p in sorted(session.rglob("*"))
        if p.is_file()
    }


# --- claims and records -------------------------------------------------------

CONTROL_NAMES = tuple(controls.EXPECTED)


def precondition_text(met: bool | None) -> str:
    """The precondition in the words of a claim: met, not met, or, when a
    session stopped before it was computed, not evaluated."""
    if met is None:
        return "not evaluated (the session stopped before it was computed)"
    return "met" if met else "not met"


def claims_of(pilot: dict, trial: dict, bounds: dict, follow: dict) -> list[Claim]:
    """The claims of the report, each with its run; the follow-up's claims
    rest on attempts that are missing until the bench session."""
    outcome = follow["outcome"]
    out = [
        Claim(
            "pilot-loss",
            "Exploratory: the pilot's R-L node sweep, read with the nominal 100 ohm,"
            " gives R_L0 near the resonance and a loss that rises towards 200 kHz;"
            " these data chose the thresholds and confirm nothing",
            "pilot run 3 of ad3-rlc-pilot (2026-11-22), the nominal resistor",
            {PILOT: True},
        ),
        Claim(
            "pilot-sensitivity",
            "Exploratory: an assumed channel mismatch at the registration's"
            " thresholds changes Rise by tens of ohm, so the pilot cannot separate"
            " a mismatch from a loss that depends on the frequency (G2 needs M3)",
            "pilot runs 2 and 3, constant assumed mismatches",
            {PILOT: True},
        ),
        Claim(
            "controls",
            "Each rule returns the outcome its explanation predicts on simulated"
            " sessions (DC, AC, MISMATCH, BOTH; the precondition met and not met;"
            " G1 undecidable under a steep loss), for every seed",
            "simulated sessions at the pilot's noise level, seeds "
            + ", ".join(str(s) for s in trial["seeds"]),
            {CONTROLS: True},
        ),
        Claim(
            "boundaries",
            "At every threshold the rules give the outcome the registration's text"
            " gives at that value, never two at once; the meter model behaves as"
            " registered on constructed readings",
            "constructed values",
            {BOUNDARIES: True},
        ),
    ]
    for key, label in (
        ("G1", "G1 (the loss near the resonance)"),
        ("G2", "G2 (the frequency dependence and the phase residual)"),
        ("precondition", "the precondition (identity of the parts)"),
    ):
        value = (
            precondition_text(outcome["precondition"])
            if key == "precondition"
            else outcome[key.lower()]
        )
        if follow["status"] == followup.NOT_EVALUATED:
            text = f"{label}: not evaluated, the bench session is not made"
        elif follow.get("exploratory"):
            text = (
                f"{label}: {value}, exploratory: the outcome code is not the"
                " code pinned for the follow-up"
            )
        else:
            text = f"{label}: {value}"
        out.append(Claim(key, text, SCOPE, {FOLLOWUP[key]: True}))
    return out


def records_of(pilot: dict, trial: dict, bounds: dict, follow: dict) -> dict:
    """The flat records the report's numbers resolve to."""
    out = {
        PILOT: {
            k: float(v)
            for k, v in pilot.items()
            if isinstance(v, (int, float)) and v is not None
        },
        CONTROLS: {
            "seeds": float(len(trial["seeds"])),
            "noise_ch1_mV": trial["noise_v"][0] * 1e3,
            "noise_ch2_mV": trial["noise_v"][1] * 1e3,
            "resolution_dphi_deg": trial["resolution"]["max_abs_dphi_deg"],
            "resolution_dg": trial["resolution"]["max_abs_dg"],
            "threshold_dphi_deg": coil.MISMATCH_PHASE_DEG,
            "threshold_dg": coil.MISMATCH_GAIN,
        },
        BOUNDARIES: {
            "cases": float(len(bounds["cases"])),
            "passed": float(sum(c["passed"] for c in bounds["cases"])),
            "meter_cases": float(len(bounds["meter"])),
        },
    }
    out[PILOT]["L_mH"] = pilot["L_H"] * 1e3
    out[PILOT]["C_nF"] = pilot["C_F"] * 1e9
    if pilot["crossing_hz"] is not None:
        out[PILOT]["crossing_kHz"] = pilot["crossing_hz"] / 1e3
    for index, (f, r, s) in enumerate(
        zip(pilot["frequency_hz"], pilot["R_L"], pilot["R_L_sigma"], strict=True)
    ):
        out[f"{PILOT}#{index}"] = {"f_kHz": f / 1e3, "R_L": r, "sigma": s}
    for index, row in enumerate(pilot["sensitivity"]):
        out[f"{PILOT}#s{index}"] = {k: float(v) for k, v in row.items()}
    for name, rows in trial["results"].items():
        for r in rows:
            out[f"{CONTROLS}#{name}-{r['seed']}"] = dict(r["values"])
    values = follow["outcome"]["values"]
    if values:
        out["followup"] = {k: float(v) for k, v in values.items()}
    series = follow["outcome"]["series"]
    for index, f in enumerate(coil.coarse_frequencies()):
        if series.get("phase_M1_minus_M0_deg"):
            out[f"followup#{index}"] = {
                "f_kHz": float(f) / 1e3,
                **{name: float(series[name][index]) for name in SERIES},
            }
    return out


# The follow-up's quantities per coarse frequency, shown in the report.
SERIES = (
    "phase_M1_minus_M0_deg",
    "dphi_deg",
    "dg",
    "R_L_uncorrected",
    "R_L_corrected",
)


def statements_of(claims) -> list[Statement]:
    return [
        Statement(
            f"s-{c.id}",
            c.text,
            COMPUTED,
            c.id,
            (f"table-{c.id}",),
            (1, 2)
            if c.id.startswith("pilot")
            else (3,)
            if c.id in ("controls", "boundaries")
            else (4,),
            "the phasor noise of the sweeps and the resistor's 1 %"
            if c.id.startswith("pilot")
            else "seeded; the counts are exact"
            if c.id in ("controls", "boundaries")
            else "the registered uncertainty model, once measured",
        )
        for c in claims
    ]


# --- reading a project -------------------------------------------------------


def _archive_entries(data) -> list[Entry]:
    return [Entry(**{**e, "idea": Idea(**e["idea"])}) for e in data]


def summary(directory: Path) -> dict:
    directory = Path(directory)
    ledger = records.load(directory / "ledger.json")
    states = directory / "states"
    pilot = _read_json(states / "pilot.json")
    trial = _read_json(states / "controls.json")
    bounds = _read_json(states / "boundaries.json")
    follow = _read_json(states / "followup.json")
    inputs = directory / "inputs"
    return {
        "track": TRACK,
        "directory": directory,
        "ledger": ledger,
        "status": rep.statuses(ledger, states),
        "pilot": pilot,
        "controls": trial,
        "boundaries": bounds,
        "followup": follow,
        "log": worklog.load(directory / "log.json"),
        "registration": reg.load(inputs / "registration.toml"),
        "freeze": freeze_of(inputs / "freeze.toml"),
        "run": _read_json(directory / "run.json"),
        "archive": _archive_entries(_read_json(directory / "archive.json")),
        "assessments": _read_json(directory / "assessments.json"),
        "records": records_of(pilot, trial, bounds, follow),
        "problems": verify(directory),
    }


def verify(directory: Path) -> list[str]:
    """Every problem of the project's chains and digests; empty when none."""
    directory = Path(directory)
    found = []
    run_record = _read_json(directory / "run.json")
    inputs = directory / "inputs"
    for name, digest in run_record["inputs"].items():
        if digest_file(inputs / name) != digest:
            found.append(f"the input {name} changed after the run")
    found += registration_problems(inputs)
    recorded_session = run_record.get("session")
    current_session = (
        _session_digests(inputs / SESSION_DIR)
        if (inputs / SESSION_DIR).is_dir()
        else None
    )
    if recorded_session != current_session:
        found.append("the bench session's files changed after the run")
    for path, digest in run_record["sample"].items():
        if digest_file(REPO_ROOT / path) != digest:
            found.append(f"the sample {path} changed after the run")
    found += verify_archive(_archive_entries(_read_json(directory / "archive.json")))
    found += worklog.verify(worklog.load(directory / "log.json").entries)
    if run_record.get("outcome_code") != graph.outcome_code_digest():
        recorded = run_record.get("outcome_files", {})
        current = graph.outcome_file_digests()
        changed = sorted(
            n
            for n in recorded.keys() | current.keys()
            if recorded.get(n) != current.get(n)
        )
        found.append(
            "the outcome code changed after the run (changed: "
            f"{', '.join(changed) or 'not recorded by file'}); the recorded"
            " outcomes were decided by the old code"
        )
    ledger = records.load(directory / "ledger.json")
    for invalid in records.check(ledger, directory / "states"):
        found.append(str(invalid))
    return found


# --- the report ------------------------------------------------------------------


def _row(*cells) -> str:
    return "| " + " | ".join(str(c).replace("|", "\\|") for c in cells) + " |"


def render_markdown(data: dict) -> tuple[str, list]:
    numbers = rep.Numbers(data["records"])
    status = data["status"]
    ledger = data["ledger"]
    claims = {c.id: c for c in ledger.claims}
    validate(statements_of(list(claims.values())), ledger)
    pilot, trial, follow = data["pilot"], data["controls"], data["followup"]
    freeze = data["freeze"]
    lines = ["# Investigation report: the coil loss of the pilot's RLC circuit", ""]
    lines += [f"> {line}" for line in rep.banner_lines(status)]
    lines += ["", f"Scope: {SCOPE}.", ""]
    if data["problems"]:
        lines += ["**The project does not verify:**", ""]
        lines += [f"- {p}" for p in data["problems"]] + [""]
    plan = data["registration"]
    lines += ["## Question and registration", "", plan.question, ""]
    lines += [
        f"The registration is frozen: digest `{freeze.digest[:16]}`, merge commit"
        f" `{freeze.commit[:12]}` on `main`, {freeze.time}. Evidence measured"
        " before that time is refused. The thresholds were chosen after seeing"
        " the pilot's data; only M1 to M5 are confirmatory.",
        "",
        "| Question | Decision | Reason | Revisit when |",
        "|---|---|---|---|",
    ]
    for entry in data["archive"]:
        lines.append(_row(entry.idea.key, entry.decision, entry.reason, entry.revisit))
    lines += ["", "## The explanations and their outcomes", ""]
    lines += [
        "| Explanation | Rule | Predicts | Verdict | Status |",
        "|---|---|---|---|---|",
    ]
    outcome = follow["outcome"]
    for name, (rule, predicted) in coil.EXPLANATIONS.items():
        got = outcome[rule.lower()]
        if got == coil.NOT_EVALUATED:
            verdict = "not evaluated"
        elif got == predicted:
            verdict = "supported"
        elif got == coil.INCONCLUSIVE:
            verdict = "undecided"
        else:
            verdict = "not supported"
        if got != coil.NOT_EVALUATED and follow.get("exploratory"):
            verdict += " (exploratory)"
        lines.append(_row(name, rule, predicted, verdict, status[rule]))
    lines += [
        "",
        "`exceeds` (D < -3 u) is predicted by neither explanation of G1 and opens"
        " a new finding. Every case that meets no predicted outcome is"
        " `inconclusive`, a result.",
        "",
        "## The analysis of the existing sweeps (exploratory)",
        "",
        "Pilot run 3 read with the nominal 100 ohm:"
        f" L = {numbers(PILOT, 'L_mH', 3)} mH,"
        f" C = {numbers(PILOT, 'C_nF', 2)} nF, R_L0 = {numbers(PILOT, 'R_L0', 1)} ohm"
        f" (u_L {numbers(PILOT, 'u_L', 1)} ohm), Rise = {numbers(PILOT, 'Rise', 0)} ohm"
        f" (u_hi {numbers(PILOT, 'u_hi', 1)} ohm, no correction), P0 ="
        f" {numbers(PILOT, 'P0_deg', 2)} degrees. These data chose the thresholds:"
        " they confirm nothing.",
        "",
        "| f [kHz] | R_L [ohm] | one sigma [ohm] |",
        "|---|---|---|",
    ]
    for index in range(len(pilot["frequency_hz"])):
        key = f"{PILOT}#{index}"
        lines.append(
            _row(
                numbers(key, "f_kHz", 1),
                numbers(key, "R_L", 1),
                numbers(key, "sigma", 2),
            )
        )
    lines += [
        "",
        "The sensitivity to a channel mismatch (constant, assumed): a phase of"
        " channel 2 relative to channel 1, and a gain error, divided out of both"
        " sweeps.",
        "",
        "| dphi [deg] | dg | R_L0 [ohm] | Rise [ohm] | P [deg] |",
        "|---|---|---|---|---|",
    ]
    for index, row in enumerate(pilot["sensitivity"]):
        if row["dphi_deg"] in (-0.3, 0.0, 0.3) and row["dg"] in (-0.003, 0.0, 0.003):
            key = f"{PILOT}#s{index}"
            lines.append(
                _row(
                    numbers(key, "dphi_deg", 1),
                    numbers(key, "dg", 3),
                    numbers(key, "R_L0", 1),
                    numbers(key, "Rise", 0),
                    numbers(key, "P_deg", 2),
                )
            )
    lines += [
        "",
        "## The positive controls (simulated)",
        "",
        f"Seeded sessions at the pilot's noise level (channel 1"
        f" {numbers(CONTROLS, 'noise_ch1_mV', 2)} mV, channel 2"
        f" {numbers(CONTROLS, 'noise_ch2_mV', 2)} mV), {numbers(CONTROLS, 'seeds', 0)}"
        " seeds each, evaluated through the follow-up's own reader. With ideal"
        " channels the largest |dphi| was"
        f" {numbers(CONTROLS, 'resolution_dphi_deg', 3)}"
        f" degrees and the largest |dg| {numbers(CONTROLS, 'resolution_dg', 4)}, below"
        f" the thresholds {numbers(CONTROLS, 'threshold_dphi_deg', 1)} degrees and"
        f" {numbers(CONTROLS, 'threshold_dg', 3)}: the same-node sweep resolves a"
        " measurable mismatch on the simulated bench.",
        "",
        "| Control | Seed | G1 | G2 | Precondition | G1 for the pilot | D [ohm]"
        " | u [ohm] | Rise [ohm] | u_hi [ohm] | Missed |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name, rows in trial["results"].items():
        for r in rows:
            key = f"{CONTROLS}#{name}-{r['seed']}"
            lines.append(
                _row(
                    name,
                    r["seed"],
                    r["g1"],
                    r["g2"],
                    r["precondition"],
                    r["g1_pilot"],
                    numbers(key, "D", 2),
                    numbers(key, "u_G1", 2),
                    numbers(key, "Rise", 1),
                    numbers(key, "u_hi", 2),
                    "; ".join(r["misses"]) or "nothing",
                )
            )
    bounds = data["boundaries"]
    lines += [
        "",
        "## The boundary cases",
        "",
        f"{numbers(BOUNDARIES, 'passed', 0)} of {numbers(BOUNDARIES, 'cases', 0)} cases"
        " give the outcome the registration's text gives at the value; the"
        f" meter model passes {sum(m['passed'] for m in bounds['meter'])} of"
        f" {numbers(BOUNDARIES, 'meter_cases', 0)} constructed checks.",
        "",
        "| Rule | Inputs | Expected | Got | Holding |",
        "|---|---|---|---|---|",
    ]
    for c in bounds["cases"]:
        lines.append(
            _row(
                c["rule"],
                ", ".join(f"{v:g}" for v in c["inputs"]),
                c["expected"],
                c["got"],
                ", ".join(c["holding"]) or "none",
            )
        )
    lines += ["", "## The follow-up", ""]
    if follow["status"] == followup.NOT_EVALUATED:
        lines += [
            "Not evaluated: " + "; ".join(follow["reasons"]) + ". The bench session"
            " is the owner's, after part 2 is merged into `main`; its inputs are"
            " the templates `session-template.toml` and `readings-template.toml`.",
            "",
        ]
    else:
        lines += [f"Status: {follow['status']}.", ""]
        if follow.get("exploratory"):
            lines += [
                "**Exploratory:** the outcome code that evaluated this session"
                " is not the code pinned for the follow-up, or was pinned after"
                " M1; the outcomes below confirm nothing (the registration's"
                " withheld part).",
                "",
            ]
        lines += [f"- {r}" for r in follow["reasons"]]
        lines += [f"- Deviation: {d}" for d in follow["deviations"]]
        lines += [f"- {n}" for n in outcome["notes"]]
        lines += [
            "",
            "| Quantity | Value |",
            "|---|---|",
        ]
        for name in sorted(outcome["values"]):
            lines.append(_row(name, numbers("followup", name, 4)))
        lines += [
            "",
            "Per coarse frequency: the phase of M1 minus the phase of M0 (read by"
            " no rule), the channels' relative response m from M3, and R_L"
            " without and with the correction H / m.",
            "",
            "| f [kHz] | M1 - M0 [deg] | dphi [deg] | dg | R_L [ohm] |"
            " R_L corrected [ohm] |",
            "|---|---|---|---|---|---|",
        ]
        for index in range(coil.COARSE_POINTS):
            key = f"followup#{index}"
            if key in data["records"]:
                lines.append(
                    _row(
                        numbers(key, "f_kHz", 1),
                        numbers(key, "phase_M1_minus_M0_deg", 3),
                        numbers(key, "dphi_deg", 3),
                        numbers(key, "dg", 4),
                        numbers(key, "R_L_uncorrected", 2),
                        numbers(key, "R_L_corrected", 2),
                    )
                )
        lines.append("")
    lines += ["## Findings and decisions", ""]
    lines += ["| Finding | Kind | State | Text |", "|---|---|---|---|"]
    log = data["log"]
    for key, entry in log.findings().items():
        lines.append(
            _row(
                key,
                entry.content["kind"],
                worklog.state(log, key),
                entry.content["text"],
            )
        )
    lines += ["", "| Subject | Decision | Reason | By |", "|---|---|---|---|"]
    for entry in log.of(worklog.DECISION):
        c = entry.content
        lines.append(_row(c["subject"], c["decision"], c["reason"], c["by"]))
    lines += ["", "## Claims", "", "| Claim | Status | Runs |", "|---|---|---|"]
    for cid, claim in claims.items():
        lines.append(_row(cid, status[cid], ", ".join(claim.runs)))
    lines += [
        "",
        "Data: A. Taspinar, F140 pilot (Analog Discovery 3), 2026-11-22, CC BY 4.0"
        " (ad3-rlc-pilot).",
        "",
    ]
    return "\n".join(lines), numbers.written


def write_exports(directory: Path) -> None:
    from pbc.products.research_workspace import original_view

    data = summary(directory)
    text, _ = render_markdown(data)
    (Path(directory) / "report.md").write_text(text, encoding="utf-8")
    original_view.write(data, Path(directory) / "view.html")
