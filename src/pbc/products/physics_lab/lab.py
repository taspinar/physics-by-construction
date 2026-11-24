"""A campaign of the Autonomous Physics Lab, end to end (F145): the
instrument of the execution mode, the route, the checkpoints, the export,
and the evaluator's checks recomputed from the exported raw samples.

The routes reach the instrument only through ``Campaign.execute``:

- ``adaptive``: the classical adaptive policy (``campaign.next_step``);
- ``scripted``: the plan's sweep, ring-downs, and amplitudes, with no
  refinement and no retry: the scripted sweep the others are compared with;
- ``agent``: the bounded agent, replayed from its trace at the product's
  fixture location (``agent_campaign``).

The export of a campaign, in its output directory:

- ``raw.csv``: every sample of every acquisition, valid or not, with its
  record, protocol, stage, and excitation (raw data);
- ``measurements.csv``: what each measurement gave, valid or not, and why;
- ``report.md`` with ``frequency-response.svg``, ``ringdown.svg``, and
  ``amplitude-response.svg``: the report and its figures;
- ``run.json``: the run record of every segment with its execution mode,
  the plan, the evaluator's checks, the consistency verdict, and, for the
  agent route, the agent's own answer labelled unverified and its
  comparison with the classical adaptive policy and the scripted sweep
  (``baseline_comparison``);
- ``evidence.json``: the ledger of ``pbc.evidence``;
- ``checkpoints/``: the checkpoint and the journal of the segments.

The evaluator reads ``raw.csv`` again and recomputes every measurement with
the protocols' own analysis, never from the route's numbers or the agent's
words. Its checks: on the simulator, each protocol against the closed form
of the simulated circuit; on every route, the agreement of the two
protocols of the series RLC circuit within their intervals and the
held-out prediction of the LED pair.
"""

import csv
import json
import math
import platform
import tempfile
import tomllib
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from pbc import evidence
from pbc.agents.loop import Transcript
from pbc.agents.loop import run as run_agent
from pbc.agents.messages import ModelClient
from pbc.agents.replay import ReplayMismatch, load_recording, replay, save_recording
from pbc.instruments import (
    LIVE,
    RECORDED,
    SIMULATED,
    SINE,
    SQUARE,
    Capture,
    Driver,
    InterlockOpen,
    Refused,
    utc_now,
)
from pbc.instruments.recorded import (
    MEASURED,
    Declaration,
    RecordedCapture,
    RecordedSample,
)
from pbc.instruments.simulated import LED_BENCH_PAIR
from pbc.products.physics_lab import agent_campaign, nonlinear, resonance, transient
from pbc.products.physics_lab.bench import make_instrument
from pbc.products.physics_lab.campaign import (
    AMPLITUDE_RESPONSE,
    FREQUENCY_RESPONSE,
    PROTOCOL_VERSIONS,
    REPEAT,
    SWEEP,
    TRANSIENT,
    Campaign,
    CampaignPlan,
    Record,
    Segment,
    Step,
    next_step,
    resonance_fit,
    resume,
    run_segment,
)
from pbc.products.physics_lab.estimates import Agreement, Estimate, agreement
from pbc.products.physics_lab.quality import rails_for

ADAPTIVE, SCRIPTED, AGENT = "adaptive", "scripted", "agent"
ROUTES = (ADAPTIVE, SCRIPTED, AGENT)
PRODUCT_DIR = Path(__file__).resolve().parents[4] / "products" / "physics-lab"
FIXTURES = PRODUCT_DIR / "fixtures"
EXAMPLES = PRODUCT_DIR / "examples"


# -- the routes -------------------------------------------------------------------


def scripted_policy(plan: CampaignPlan, records: Sequence[Record]) -> Step | None:
    """The scripted sweep: the plan's sweep, its ring-downs, and its
    amplitudes, in order, with no refinement and no retry."""
    done = len(records)
    script: list[Step] = []
    if FREQUENCY_RESPONSE in plan.protocols:
        grid = np.geomspace(plan.low_hz, plan.high_hz, plan.sweep_points)
        script += [Step(FREQUENCY_RESPONSE, round(float(f), 3), SWEEP) for f in grid]
    if TRANSIENT in plan.protocols:
        script += [Step(TRANSIENT, None, REPEAT)] * plan.min_ringdowns
    if AMPLITUDE_RESPONSE in plan.protocols:
        script += [Step(AMPLITUDE_RESPONSE, float(a), SWEEP) for a in plan.amplitudes_v]
    return script[done] if done < len(script) else None


def load_plan(path: Path) -> tuple[CampaignPlan, int]:
    """The plan in the TOML file ``path`` (table ``[campaign]``) and its
    ``seed`` (table ``[run]``, default 0)."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    table = data.get("campaign")
    if not isinstance(table, dict):
        raise ValueError(f"{path} has no table [campaign]")
    run = data.get("run", {})
    unknown = sorted(set(run) - {"seed"})
    if unknown:
        raise ValueError(f"{path}: unknown keys of [run]: {', '.join(unknown)}")
    return CampaignPlan.from_dict(table), int(run.get("seed", 0))


def trace_path(plan: CampaignPlan) -> Path:
    """The default replay fixture of the agent route of ``plan``'s circuit."""
    return FIXTURES / f"agent-campaign-{plan.circuit}.json"


def rerecord_command(plan_path: str, fixture: str) -> str:
    return (
        "uv run --locked --extra physics-lab python -m pbc.products.physics_lab"
        f" record-campaign --provider <name> --plan {plan_path} --out {fixture}"
        " --price-in <EUR per Mtok> --price-out <EUR per Mtok>"
        " --spend-ledger <file outside the repository>"
    )


@dataclass
class LabResult:
    """What a campaign produced."""

    out_dir: Path
    route: str
    mode: str
    plan: CampaignPlan
    records: list[Record]
    segment: Segment
    evaluation: dict[str, Any]
    answer: str | None
    files: dict[str, Path] = field(default_factory=dict)


def run_campaign(
    plan: CampaignPlan,
    out_dir: Path,
    *,
    route: str = ADAPTIVE,
    mode: str = SIMULATED,
    seed: int = 0,
    confirmed: bool = False,
    sample: RecordedSample | None = None,
    recorded_live: bool = False,
    driver: Driver | None = None,
    trace: Path | None = None,
    resume_from_checkpoint: bool = False,
    on_record: Callable[[Record], None] | None = None,
    on_campaign: Callable[[Campaign], None] | None = None,
    clock: Callable[[], str] = utc_now,
) -> LabResult:
    """Run the campaign of ``plan`` by ``route`` in ``mode`` and export it to
    ``out_dir``. A refusal of the instrument (a stop, a timeout, an open
    interlock, a value outside the envelope) ends the segment, and what was
    measured before it is exported; ``resume_from_checkpoint`` continues an
    interrupted campaign from its checkpoint in ``out_dir`` (``resume``)."""
    if route not in ROUTES:
        raise ValueError(f"unknown route {route!r}; one of {ROUTES}")
    instrument, rails = make_instrument(
        plan,
        mode,
        seed=seed,
        confirmed=confirmed,
        driver=driver,
        sample=sample,
        recorded_live=recorded_live,
    )
    checkpoints = out_dir / "checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)
    checkpoint, journal = checkpoints / "checkpoint.json", checkpoints / "journal.json"
    if resume_from_checkpoint:
        campaign = resume(journal, checkpoint, plan, instrument, rails, on_record)
    else:
        for stale in (checkpoint, journal):
            stale.unlink(missing_ok=True)
        campaign = Campaign(plan, instrument, rails, checkpoint, (), on_record)
    if on_campaign is not None:
        on_campaign(campaign)
    started = clock()
    answer, comparison = None, None
    if route == AGENT:
        segment, answer = _agent_segment(campaign, journal, trace or trace_path(plan))
        comparison = baseline_comparison(plan, mode, seed, confirmed, campaign.records)
    else:
        policy = next_step if route == ADAPTIVE else scripted_policy
        segment = run_segment(campaign, journal, policy)
    finished = clock()
    record = instrument.run_record(
        configuration={
            "plan": plan.to_dict(),
            "route": route,
            "seed": seed,
            "protocols": {p: PROTOCOL_VERSIONS[p] for p in plan.protocols},
            "segment": segment.number,
        },
        units=UNITS,
        processing=PROCESSING,
        started=started,
        finished=finished,
    )
    return export(
        out_dir,
        plan,
        route,
        record.to_dict(),
        campaign.records,
        segment,
        answer,
        seed,
        comparison,
    )


def _agent_segment(
    campaign: Campaign, journal: Path, trace: Path
) -> tuple[Segment, str]:
    """Replay the agent's trace against ``campaign``: every recorded call is
    executed again and its result compared with the recorded one."""
    recording = load_recording(trace)
    refusals: list[Refused] = []
    tools = agent_campaign.campaign_tools(campaign, refusals)
    plan = campaign.plan

    def policy(_plan: CampaignPlan, _records: Sequence[Record]) -> Step | None:
        return None  # the agent's calls ran inside the replay

    start = len(campaign.records)  # the segment made what the replay makes
    try:
        transcript = replay(
            recording,
            tools,
            system=agent_campaign.SYSTEM,
            task=agent_campaign.task(plan),
            tolerance=agent_campaign.TOLERANCE,
            max_steps=plan.budget + 2,
            rerecord=rerecord_command("<plan>", str(trace)),
        )
    except ReplayMismatch:
        if refusals:
            # A refusal of the instrument turned a recorded success into a
            # tool error: the segment failed, it did not drift.
            # run_segment records it so, in the journal as in the export.
            segment = run_segment(campaign, journal, policy, start, refused=refusals[0])
            return segment, ""
        raise
    segment = run_segment(campaign, journal, policy, start)
    answer = transcript.steps[-1].message.text if transcript.steps else ""
    return segment, answer


def record_campaign(
    plan: CampaignPlan,
    path: Path,
    client: ModelClient,
    recorded: str,
    *,
    seed: int = 0,
    placeholder: bool,
    confirmed: bool = True,
) -> Transcript:
    """Run the agent route live with ``client`` on a fresh simulated bench
    with ``seed`` and save its trace to ``path``, with every secret of the
    client removed (ADR 004). Nothing is recorded with the interlock open,
    or when no measurement succeeded."""
    instrument, rails = make_instrument(plan, SIMULATED, seed=seed, confirmed=confirmed)
    for interlock in instrument.envelope.interlocks:
        if not interlock.closed():
            raise InterlockOpen(f"interlock {interlock.name} is open; nothing recorded")
    campaign = Campaign(plan, instrument, rails)
    tools = agent_campaign.campaign_tools(campaign)
    try:
        transcript = run_agent(
            client,
            tools,
            agent_campaign.SYSTEM,
            agent_campaign.task(plan),
            plan.budget + 2,
        )
    finally:
        instrument.output_off()
    if not campaign.records:
        raise Refused(f"no measurement succeeded; nothing was saved to {path}")
    save_recording(path, transcript, recorded, *client.secrets, placeholder=placeholder)
    return transcript


# -- the export ---------------------------------------------------------------------

UNITS = {
    "frequency": "Hz",
    "amplitude": "V",
    "time": "s",
    "source": "V",
    "response": "V",
    "gain": "dimensionless (V/V)",
    "phase": "degrees",
    "decay rate": "1/s",
    "h3": "dimensionless (V/V)",
}
PROCESSING = (
    "every capture passes the quality gate (pbc.products.physics_lab.quality)"
    " before a number is read; an invalid one is recorded and never fitted",
    "frequency response: amplitude and phase of each channel by a least-squares"
    " sine fit over the valid samples (pbc.electromagnetism.measurement.fit_sine);"
    " f0, Q, and k with standard errors from a weighted fit of the second-order"
    " response to the log-gain and the phase (pbc.products.physics_lab.resonance)",
    "transient: the ring-down after the first rising edge of the square wave,"
    " fitted by v_inf + e^(-alpha t)(a cos omega_d t + b sin omega_d t);"
    " f0 and Q with standard errors (pbc.products.physics_lab.ringdown);"
    " repetitions combined by their weighted mean, widened by the Birge ratio",
    "amplitude response: the fundamental and the odd harmonics of the response"
    " fitted together; the characteristic v = n V_T asinh(i / 2 I_s) fitted to"
    " the samples above 0.5 mA (pbc.products.physics_lab.nonlinear)",
)

_RAW_FIELDS = (
    "record",
    "protocol",
    "stage",
    "valid",
    "waveform",
    "amplitude_v",
    "frequency_hz",
    "asked_rate_hz",
    "t_s",
    "source_v",
    "response_v",
)


def excitation(plan: CampaignPlan, step: Step) -> tuple[str, float, float, float]:
    """The waveform, amplitude (V), frequency (Hz), and asked sample rate
    (samples/s) of ``step``."""
    if step.protocol == FREQUENCY_RESPONSE:
        f = float(step.setting or 0.0)
        return SINE, plan.amplitude_v, f, plan.samples_per_period * f
    if step.protocol == TRANSIENT:
        return SQUARE, plan.amplitude_v, plan.square_hz, plan.transient_rate_hz
    f = plan.amplitude_frequency_hz
    return SINE, float(step.setting or 0.0), f, plan.samples_per_period * f


def _number(x: float) -> str:
    return "nan" if not math.isfinite(x) else f"{float(x):.12g}"


def write_raw(path: Path, plan: CampaignPlan, records: Sequence[Record]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(_RAW_FIELDS)
        for r in records:
            waveform, amplitude, frequency, asked = excitation(plan, r.step)
            c = r.capture
            head = [
                r.id,
                r.step.protocol,
                r.step.stage,
                int(r.valid),
                waveform,
                _number(amplitude),
                _number(frequency),
                _number(asked),
            ]
            for t, s, v in zip(
                c.t, c.channels["source"], c.channels["response"], strict=True
            ):
                writer.writerow([*head, _number(t), _number(s), _number(v)])


def read_raw(path: Path) -> list[dict[str, Any]]:
    """The acquisitions of ``raw.csv``, in order: each with its record id,
    protocol, stage, excitation, and capture (the rate read from its sample
    times)."""
    blocks: dict[str, list[dict[str, str]]] = {}
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            blocks.setdefault(row["record"], []).append(row)
    found = []
    for record, rows in blocks.items():
        t = np.array([float(r["t_s"]) for r in rows])
        rate = (len(t) - 1) / (t[-1] - t[0])
        first = rows[0]
        found.append(
            {
                "record": record,
                "protocol": first["protocol"],
                "stage": first["stage"],
                "waveform": first["waveform"],
                "amplitude_v": float(first["amplitude_v"]),
                "frequency_hz": float(first["frequency_hz"]),
                "asked_rate_hz": float(first["asked_rate_hz"]),
                "capture": Capture(
                    rate,
                    t,
                    {
                        "source": np.array([float(r["source_v"]) for r in rows]),
                        "response": np.array([float(r["response_v"]) for r in rows]),
                    },
                    {"t": "s", "source": "V", "response": "V"},
                ),
            }
        )
    return found


def read_campaign_export(directory: Path) -> tuple[RecordedSample, CampaignPlan, str]:
    """A campaign's export as a recorded sample replayed in order, its plan,
    and the execution mode it was made in: a live campaign's export is
    declared as a dataset and replayed so in the build (ADR 007)."""
    data = json.loads((directory / "run.json").read_text(encoding="utf-8"))
    plan = CampaignPlan.from_dict(data["plan"])
    run_record = data["run"]
    captures = tuple(
        RecordedCapture(
            amplitude_v=a["amplitude_v"],
            frequency_hz=a["frequency_hz"],
            sample_rate_hz=a["asked_rate_hz"],
            channels={
                k: tuple(map(float, v)) for k, v in a["capture"].channels.items()
            },
            realised_rate_hz=a["capture"].sample_rate_hz,
            waveform=a["waveform"],
        )
        for a in read_raw(directory / "raw.csv")
    )
    device = run_record["device"]
    declaration = Declaration(
        dataset=f"{directory.parent.name}/{directory.name}",
        origin=MEASURED if run_record["mode"] == LIVE else "simulated",
        description=f"a {run_record['mode']} campaign on {device.get('device')},"
        f" started {run_record['started']}",
        units={"source": "V", "response": "V"},
        provenance=f"the export of the campaign in {directory.name}",
    )
    return RecordedSample(declaration, captures), plan, run_record["mode"]


def write_measurements(path: Path, plan: CampaignPlan, records: Sequence[Record]):
    keys = sorted({k for r in records for k in r.numbers})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            ["record", "protocol", "stage", "setting", "basis", "valid", "note", *keys]
        )
        for r in records:
            writer.writerow(
                [
                    r.id,
                    r.step.protocol,
                    r.step.stage,
                    "" if r.step.setting is None else _number(r.step.setting),
                    " ".join(r.step.basis),
                    int(r.valid),
                    r.note,
                    *[_number(r.numbers[k]) if k in r.numbers else "" for k in keys],
                ]
            )


# -- the evaluator ------------------------------------------------------------------


def evaluate(
    raw: Path, plan: CampaignPlan, mode: str, recorded_live: bool = False
) -> dict[str, Any]:
    """The evaluator's results, recomputed from ``raw.csv`` alone with the
    protocols' own analysis: each protocol's estimates with intervals, the
    simulator's checks against the closed forms (simulated mode), the
    consistency of the two protocols of the RLC circuit, and the held-out
    check of the LED pair."""
    rails = rails_for(LIVE if mode == LIVE or recorded_live else mode)
    acquisitions = read_raw(raw)
    points, ringdowns, amplitudes = [], [], []
    for a in acquisitions:
        capture = a["capture"]
        if a["protocol"] == FREQUENCY_RESPONSE:
            m = resonance.analyse_point(
                capture, a["frequency_hz"], a["amplitude_v"], rails
            )
            if m.valid:
                points.append(m.point)
        elif a["protocol"] == TRANSIENT:
            ringdowns.append(
                transient.analyse_ringdown(capture, plan.transient_settings, rails)
            )
        else:
            amplitudes.append(
                nonlinear.analyse_amplitude(
                    capture, a["amplitude_v"], plan.nonlinear_settings, rails
                )
            )
    result: dict[str, Any] = {
        "acquisitions": len(acquisitions),
        "simulator_checks": {},
        "agreements": [],
    }
    simulated = mode == SIMULATED or (mode == RECORDED and not recorded_live)
    fit = resonance.fit_resonance(points) if points else None
    if FREQUENCY_RESPONSE in plan.protocols:
        result[FREQUENCY_RESPONSE] = {
            "valid_points": len(points),
            "fit": None if fit is None else fit.to_dict(),
        }
        if simulated and fit is not None:
            ref = transient.reference(plan.declared_circuit)
            result["simulator_checks"][FREQUENCY_RESPONSE] = _against(
                {"f0_hz": fit.f0_hz, "q": fit.q}, ref
            )
    combined = transient.combine_ringdowns(ringdowns) if ringdowns else None
    if TRANSIENT in plan.protocols:
        result[TRANSIENT] = {
            "valid": 0 if combined is None else combined.valid,
            "invalid": 0 if combined is None else combined.invalid,
            "f0_hz": None
            if combined is None or combined.f0_hz is None
            else {**combined.f0_hz.estimate.to_dict(), "birge": combined.f0_hz.birge},
            "q": None
            if combined is None or combined.q is None
            else {**combined.q.estimate.to_dict(), "birge": combined.q.birge},
        }
        if simulated and combined is not None:
            check = transient.check_against_closed_form(combined, plan.declared_circuit)
            if check is not None:
                result["simulator_checks"][TRANSIENT] = {
                    "correct": check.correct,
                    "note": check.note,
                    **check.metrics,
                }
    if fit is not None and combined is not None and combined.f0_hz is not None:
        result["agreements"] = [
            a.to_dict()
            for a in consistency(fit, combined.f0_hz.estimate, combined.q.estimate)
        ]
    if AMPLITUDE_RESPONSE in plan.protocols:
        valid = [m for m in amplitudes if m.valid]
        characteristic = nonlinear.fit_characteristic(valid, plan.series_resistance_ohm)
        held = nonlinear.held_out_check(valid, plan.series_resistance_ohm)
        result[AMPLITUDE_RESPONSE] = {
            "valid": len(valid),
            "invalid": len(amplitudes) - len(valid),
            "points": [m.point.to_dict() for m in valid if m.point is not None],
            "characteristic": None
            if characteristic is None
            else characteristic.to_dict(),
            "held_out": None
            if held is None
            else {
                "fitted_on_v": held.fitted_on,
                "agree": held.agree,
                "agreements": [
                    {"amplitude_v": a, **g.to_dict()} for a, g in held.agreements
                ],
            },
        }
        if simulated and characteristic is not None:
            check = nonlinear.check_against_model(characteristic, LED_BENCH_PAIR)
            result["simulator_checks"][AMPLITUDE_RESPONSE] = {
                "correct": check.correct,
                "note": check.note,
                **check.metrics,
            }
    return result


def _against(found: dict[str, Estimate], ref: dict[str, float]) -> dict[str, Any]:
    """The frequency response's fit against the closed form: within
    ``transient.CHECK_SIGMAS`` standard errors and F138's tolerances."""
    f0, q = found["f0_hz"], found["q"]
    f0_error = f0.value / ref["f0_hz"] - 1.0
    q_error = q.value / ref["q"] - 1.0
    correct = (
        abs(f0.value - ref["f0_hz"]) <= transient.CHECK_SIGMAS * f0.se
        and abs(q.value - ref["q"]) <= transient.CHECK_SIGMAS * q.se
        and abs(f0_error) <= transient.F0_TOLERANCE
        and abs(q_error) <= transient.Q_TOLERANCE
    )
    return {
        "correct": bool(correct),
        "reference_f0_hz": ref["f0_hz"],
        "reference_q": ref["q"],
        "f0_relative_error": f0_error,
        "q_relative_error": q_error,
        "f0_sigmas": abs(f0.value - ref["f0_hz"]) / f0.se,
        "q_sigmas": abs(q.value - ref["q"]) / q.se,
    }


def consistency(
    fit: resonance.ResonanceFit, f0: Estimate, q: Estimate
) -> tuple[Agreement, Agreement]:
    """The independent check of a live or recorded RLC circuit: the
    frequency response and the ring-down agree on f0 and on Q."""
    # region: consistency
    checks = (
        agreement("f0_hz", FREQUENCY_RESPONSE, fit.f0_hz, TRANSIENT, f0),
        agreement("q", FREQUENCY_RESPONSE, fit.q, TRANSIENT, q),
    )
    # endregion: consistency
    return checks


def _verdict(evaluation: dict[str, Any]) -> bool | None:
    """True when every check that ran passed, None when none ran."""
    verdicts = [c["correct"] for c in evaluation["simulator_checks"].values()]
    verdicts += [a["agree"] for a in evaluation["agreements"]]
    held = evaluation.get(AMPLITUDE_RESPONSE, {}).get("held_out")
    if held is not None:
        verdicts.append(held["agree"])
    return None if not verdicts else all(verdicts)


def export(
    out_dir: Path,
    plan: CampaignPlan,
    route: str,
    run_record: dict[str, Any],
    records: list[Record],
    segment: Segment,
    answer: str | None,
    seed: int,
    comparison: dict[str, Any] | None = None,
) -> LabResult:
    from pbc.products.physics_lab.campaign_report import write_report

    files = {
        "raw": out_dir / "raw.csv",
        "measurements": out_dir / "measurements.csv",
        "report": out_dir / "report.md",
        "run": out_dir / "run.json",
        "evidence": out_dir / "evidence.json",
    }
    write_raw(files["raw"], plan, records)
    write_measurements(files["measurements"], plan, records)
    mode = run_record["mode"]
    recorded_live = mode == RECORDED and "measured" in str(
        run_record["device"].get("origin", "")
    )
    evaluation = (
        evaluate(files["raw"], plan, mode, recorded_live)
        if records
        else {
            "acquisitions": 0,
            "simulator_checks": {},
            "agreements": [],
        }
    )
    verdict = _verdict(evaluation)
    if segment.status in ("interrupted", "failed"):
        status = (
            evidence.FAILED if segment.status == "failed" else evidence.INCONCLUSIVE
        )
    elif verdict is None:
        status = evidence.INCONCLUSIVE
    else:
        status = evidence.COMPLETED
    ledger = _ledger(
        plan,
        route,
        run_record,
        files["raw"],
        out_dir,
        evaluation,
        verdict,
        status,
        segment,
        answer,
        seed,
    )
    evidence.save(ledger, files["evidence"])
    data = {
        "product": "physics-lab",
        "kind": "campaign",
        "route": route,
        "status": status,
        "segment": segment.to_dict(),
        "plan": plan.to_dict(),
        "run": run_record,
        "execution_modes": [run_record["mode"]],
        "evaluation": evaluation,
        "verdict": verdict,
        "invalid": [
            {"record": r.id, "protocol": r.step.protocol, "reason": r.note}
            for r in records
            if not r.valid
        ],
        "candidate_answer": None
        if answer is None
        else {"text": answer, "label": evidence.UNVERIFIED},
        "comparison": comparison,
        "evidence": {
            "file": files["evidence"].name,
            "summary": evidence.summary(ledger, out_dir).text(),
        },
    }
    files["run"].write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    result = LabResult(
        out_dir, route, mode, plan, records, segment, evaluation, answer, files
    )
    files.update(write_report(result, data))
    return result


def _code_identity() -> str:
    root = Path(__file__).resolve().parents[2]  # src/pbc
    paths = [
        *sorted((root / "instruments").glob("*.py")),
        *sorted((root / "products" / "physics_lab").glob("*.py")),
        root / "electromagnetism" / "led_pair.py",
        root / "electromagnetism" / "measurement.py",
    ]
    return evidence.records.digest_files(paths, root)


def _ledger(
    plan,
    route,
    run_record,
    raw,
    out_dir,
    evaluation,
    verdict,
    status,
    segment,
    answer,
    seed,
) -> evidence.Ledger:
    configuration = evidence.digest_value(plan.to_dict())
    task = evidence.RunRecord(
        task="f0 and Q of the declared series RLC circuit by two protocols, and"
        " the amplitude-dependent response of the declared LED pair, as the"
        " plan names them",
        hypothesis="a driven, damped linear oscillator (one f0 and one Q for the"
        " frequency response and the ring-down); a memoryless, symmetric diode"
        " characteristic for the LED pair",
        assumptions=(
            "the declared circuit is the one connected; nothing rewires it",
            "the channels are calibrated as the run record declares",
            "an invalid capture carries no number",
        ),
        protocol_version=",".join(PROTOCOL_VERSIONS[p] for p in plan.protocols),
        split={
            "probed": "the settings the route chose, within the plan and the envelope",
            "reference": "the closed form of the simulated circuit (simulated"
            " mode only), held by the evaluator; otherwise the other protocol"
            " and the held-out amplitudes",
        },
        seeds=(seed,),
        budgets={"measurements": plan.budget},
        code=_code_identity(),
        configuration=configuration,
        environment={
            "python": platform.python_version(),
            "numpy": np.__version__,
            "execution_mode": run_record["mode"],
            "label": run_record["label"],
        },
    )
    ledger = evidence.Ledger(task)
    attempt = f"{route}-segment-{segment.number}"
    artifact = evidence.Artifact.of("raw samples", raw, out_dir)
    ledger.add_attempt(
        evidence.Attempt(
            id=attempt,
            candidate=route,
            cycle=1,
            status=status,
            diagnostics=(
                f"{segment.status} after {len(segment.made)} measurements",
                *segment.diagnostics,
            ),
            artifacts=(artifact,),
        )
    )
    metrics: dict[str, float] = {"acquisitions": float(evaluation["acquisitions"])}
    for a in evaluation["agreements"]:
        metrics[f"{a['quantity']}_sigmas"] = float(a["sigmas"])
    ledger.add_evaluation(
        evidence.Evaluation(
            attempt=attempt,
            evaluator="pbc.products.physics_lab.lab.evaluate, version 1",
            correct=verdict,
            metrics=metrics,
            resources={"measurements": int(evaluation["acquisitions"])},
            depends_on=(artifact,),
            code=task.code,
            configuration=configuration,
        )
    )
    if answer is not None:
        ledger.add_report(
            evidence.CandidateReport(
                attempt, True if answer else None, {"answer": answer}
            )
        )
    ledger.add_claim(
        evidence.Claim(
            id="campaign",
            text="the evaluator's checks of this campaign pass: the closed form"
            " on the simulator, the agreement of the two protocols, and the"
            " held-out prediction, where each applies",
            scope=f"this circuit, {run_record['mode']} mode, seed {seed}",
            runs={attempt: True},
        )
    )
    return ledger


# -- the comparison of routes ----------------------------------------------------------


def width_history(records: Sequence[Record]) -> list[tuple[int, float | None]]:
    """After each measurement of the frequency response (valid or not), the
    count so far and the relative width of the interval of f0 then (None
    while no fit exists)."""
    history = []
    seen: list[Record] = []
    for r in records:
        if r.step.protocol != FREQUENCY_RESPONSE:
            continue
        seen.append(r)
        fit = resonance_fit(seen)
        history.append((len(seen), None if fit is None else fit.f0_hz.relative_width))
    return history


def needed(history: Sequence[tuple[int, float | None]], target: float) -> int | None:
    """The first count at which the width is at most ``target``."""
    for count, width in history:
        if width is not None and width <= target:
            return count
    return None


def compare_routes(
    histories: dict[str, Sequence[tuple[int, float | None]]],
) -> dict[str, Any]:
    """The routes compared by the measurements each needed for the same
    interval: the common target is the widest final width among them (one
    every route reached), and each route's count at which it first reached
    it."""
    finals = {
        route: next((w for _, w in reversed(h) if w is not None), None)
        for route, h in histories.items()
    }
    reached = [w for w in finals.values() if w is not None]
    if not reached:
        return {"target": None, "routes": {}}
    target = max(reached)
    return {
        "target": target,
        "routes": {
            route: {
                "final_width": finals[route],
                "measurements": len(h),
                "needed": needed(h, target),
            }
            for route, h in histories.items()
        },
    }


def baseline_comparison(
    plan: CampaignPlan,
    mode: str,
    seed: int,
    confirmed: bool,
    agent_records: Sequence[Record],
) -> dict[str, Any]:
    """The agent's campaign beside the classical adaptive policy and the
    scripted sweep: each baseline runs on a fresh simulated bench with the
    same plan and seed (its checkpoints in a temporary directory, never in
    the export), and the three routes are compared by the measurements each
    needed for the same interval width of f0 (``compare_routes``). Only a
    simulated agent campaign has baselines: on a recorded sample or a live
    bench a baseline would need the circuit again, so the comparison says
    so and holds no route."""
    base: dict[str, Any] = {
        "mode": SIMULATED,
        "seed": seed,
        "quantity": "relative width of the interval of f0",
        "baselines": [ADAPTIVE, SCRIPTED],
    }
    if mode != SIMULATED:
        return {
            **base,
            "target": None,
            "routes": {},
            "measurements": {AGENT: len(agent_records)},
            "note": f"no baseline in the {mode} mode: the classical routes run"
            " beside the agent only on the simulated bench",
        }
    records: dict[str, Sequence[Record]] = {AGENT: agent_records}
    with tempfile.TemporaryDirectory() as scratch:
        for route, policy in ((ADAPTIVE, next_step), (SCRIPTED, scripted_policy)):
            instrument, rails = make_instrument(
                plan, SIMULATED, seed=seed, confirmed=confirmed
            )
            baseline = Campaign(plan, instrument, rails)
            run_segment(baseline, Path(scratch) / f"{route}-journal.json", policy)
            records[route] = baseline.records
    compared = compare_routes({r: width_history(rs) for r, rs in records.items()})
    note = (
        None
        if compared["target"] is not None
        else "the plan has no fitted frequency response: the routes are"
        " compared by their measurement counts only"
    )
    return {
        **base,
        **compared,
        "measurements": {r: len(rs) for r, rs in records.items()},
        "note": note,
    }
