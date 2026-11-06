"""One run of the slice, end to end: the instrument of the chosen execution
mode behind its envelope, the chosen route, the evaluator's check recomputed
from the exported raw samples, the evidence ledger, and the export.

The export of a run, in its output directory:

- ``raw.csv``: every sample of every acquisition (raw data);
- ``points.csv``: the points the route measured;
- ``report.md`` and ``frequency-response.svg``: the report and its figure;
- ``run.json``: the instrument's run record (the execution mode, the device
  or model and its calibration, the configuration, the units, the
  processing, the timestamps), the evaluator's check, and, for the agent
  route, the agent's own answer labelled unverified;
- ``evidence.json``: the ledger of ``pbc.evidence``.

The evaluator's numbers come from ``raw.csv``, never from the route's own
points or the agent's words; a recorded tool result of a trace is never
exported (ADR 002 condition 3).
"""

import csv
import json
import platform
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from pbc import evidence
from pbc.agents.loop import Transcript
from pbc.agents.loop import run as run_agent
from pbc.agents.messages import ModelClient
from pbc.agents.replay import ReplayMismatch, load_recording, replay, save_recording
from pbc.electromagnetism.circuits import SeriesRLC
from pbc.instruments import (
    LIVE,
    RECORDED,
    SIMULATED,
    Capture,
    Instrument,
    InstrumentRun,
    Interlock,
    InterlockOpen,
    Refused,
    utc_now,
)
from pbc.instruments.recorded import (
    Declaration,
    RecordedBench,
    RecordedCapture,
    RecordedSample,
    load_sample,
    save_sample,
)
from pbc.instruments.simulated import BENCH_CIRCUIT, SimulatedRLCBench
from pbc.products.physics_lab import agent
from pbc.products.physics_lab.baseline import run_baseline
from pbc.products.physics_lab.protocol import (
    PROTOCOL_VERSION,
    Analysis,
    Check,
    Config,
    Measurement,
    Point,
    analyse,
    bench_envelope,
    evaluate,
    transfer,
)

BASELINE = "baseline"
AGENT = "agent"
ROUTES = (BASELINE, AGENT)

# The repository's product directory, when the package runs from a checkout.
PRODUCT_DIR = Path(__file__).resolve().parents[4] / "products" / "physics-lab"
FIXTURES = PRODUCT_DIR / "fixtures"
TRACE = FIXTURES / "agent-frequency-response.json"

UNITS = {
    "frequency": "Hz",
    "amplitude": "V",
    "time": "s",
    "source": "V",
    "response": "V",
    "gain": "dimensionless (V/V)",
    "phase": "degrees",
}
PROCESSING = (
    "each acquisition spans a whole number of periods after the transient settled",
    "the phasor of each channel by projection on cos and sin over the record"
    " (pbc.electromagnetism.circuits.steady_phasor)",
    "gain and phase of response / source",
    "f0 where the phase crosses -90 degrees, linear in log frequency between"
    " the bracketing points; Q from their gains through the second-order"
    " response, averaged",
)

RERECORD = (
    "uv run --locked --extra physics-lab python -m pbc.products.physics_lab"
    " record --provider openai"
    " --input products/physics-lab/examples/frequency-response.toml"
    " --out products/physics-lab/fixtures/agent-frequency-response.json"
)


@dataclass
class Result:
    """What a run produced."""

    out_dir: Path
    route: str
    mode: str
    status: str
    measurements: list[Measurement]
    analysis: Analysis
    check: Check | None
    run: InstrumentRun
    candidate_answer: str | None
    diagnostics: tuple[str, ...]
    files: dict[str, Path] = field(default_factory=dict)


def make_instrument(
    config: Config, mode: str = SIMULATED, sample: Path | None = None
) -> Instrument:
    """The guarded instrument of ``mode`` with the bench's envelope and the
    interlock of the prepared circuit."""
    if mode == SIMULATED:
        driver = SimulatedRLCBench(seed=config.seed)
    elif mode == RECORDED:
        if sample is None:
            raise ValueError("the recorded mode needs a sample (--sample)")
        driver = RecordedBench(load_sample(sample))
    elif mode == LIVE:
        raise ValueError(
            "no live adapter exists yet: live hardware is decided by the"
            " one-instrument pilot (F140)"
        )
    else:
        raise ValueError(f"unknown execution mode {mode!r}")
    confirmed = Interlock(
        "circuit-confirmed",
        "confirm that the prepared series RLC circuit of the brief is connected;"
        " the product never rewires a circuit",
        lambda: config.circuit_confirmed,
    )
    # A recorded sample drives nothing, so the interlock of the circuit does
    # not apply to it.
    interlocks = () if mode == RECORDED else (confirmed,)
    return Instrument(driver, bench_envelope(interlocks))


def run(
    config: Config,
    out_dir: Path,
    *,
    route: str = BASELINE,
    mode: str = SIMULATED,
    sample: Path | None = None,
    trace: Path = TRACE,
    on_point: Callable[[Measurement], None] | None = None,
    on_instrument: Callable[[Instrument], None] | None = None,
    clock: Callable[[], str] = utc_now,
) -> Result:
    """Run the protocol by ``route`` in ``mode`` and export the result to
    ``out_dir``. A refusal of the instrument (a stop, a timeout, an open
    interlock, a value outside the envelope) ends the run as failed and is
    reported, and the points measured before it are exported; on the agent
    route as well, where the refusal reaches the agent as a tool error and
    the replay then departs from its trace. A replay that does not match
    its trace for any other reason raises ``ReplayMismatch``."""
    if route not in ROUTES:
        raise ValueError(f"unknown route {route!r}; choose one of {ROUTES}")
    instrument = make_instrument(config, mode, sample)
    if on_instrument is not None:
        on_instrument(instrument)
    out_dir.mkdir(parents=True, exist_ok=True)
    started = clock()
    measurements: list[Measurement] = []
    answer = None
    diagnostics: tuple[str, ...] = ()
    try:
        if route == BASELINE:
            # The points are collected as they come, so that a run stopped
            # part way keeps and exports what it measured.
            def collect(measurement: Measurement) -> None:
                measurements.append(measurement)
                if on_point is not None:
                    on_point(measurement)

            run_baseline(instrument, config, collect)
        else:
            recording = load_recording(trace)
            refusals: list[Refused] = []
            tools = agent.measurement_tools(
                instrument, config, measurements, on_point, refusals
            )
            try:
                transcript = replay(
                    recording,
                    tools,
                    system=agent.SYSTEM,
                    task=agent.task(config),
                    tolerance=agent.TOLERANCE,
                    max_steps=config.agent_budget + 1,
                    rerecord=RERECORD,
                )
            except ReplayMismatch:
                # A refusal of the instrument (a stop above all) turned a
                # recorded success into a tool error: the run failed, it
                # did not drift from its trace.
                if refusals:
                    raise refusals[0] from None
                raise
            answer = transcript.steps[-1].message.text if transcript.steps else ""
    except Refused as reason:
        diagnostics = (f"refused by the instrument: {reason}",)
    finally:
        instrument.output_off()
    finished = clock()
    record = instrument.run_record(
        configuration={
            **config.to_dict(),
            "route": route,
            "protocol": PROTOCOL_VERSION,
        },
        units=UNITS,
        processing=PROCESSING,
        started=started,
        finished=finished,
    )
    return _export(
        config, out_dir, route, record, measurements, answer, diagnostics, sample
    )


def record_trace(
    config: Config,
    path: Path,
    client: ModelClient,
    recorded: str,
    *,
    placeholder: bool,
) -> Transcript:
    """Run the agent route live with ``client`` on a fresh simulated bench
    and save its trace to ``path``: the model's messages and the tool
    results, with every secret of the client removed (ADR 004).

    It records nothing when an interlock is open, before the model is asked
    anything, and saves no trace in which no measurement succeeded: such a
    trace would replay only refusals. Both raise ``Refused``."""
    instrument = make_instrument(config, SIMULATED)
    for interlock in instrument.envelope.interlocks:
        if not interlock.closed():
            raise InterlockOpen(
                f"interlock {interlock.name} is open: {interlock.description};"
                " no trace was recorded"
            )
    measured: list[Measurement] = []
    tools = agent.measurement_tools(instrument, config, measured)
    try:
        transcript = run_agent(
            client, tools, agent.SYSTEM, agent.task(config), config.agent_budget + 1
        )
    finally:
        instrument.output_off()
    if not measured:
        raise Refused(
            f"no measurement of the run succeeded; the trace was not saved to {path}"
        )
    save_recording(path, transcript, recorded, *client.secrets, placeholder=placeholder)
    return transcript


def write_synthetic_sample(config: Config, path: Path) -> RecordedSample:
    """Write the synthetic sample of the recorded mode: the acquisitions of
    the scripted baseline on the simulated bench with ``config.seed``,
    declared as simulated. It is regenerated from its seed, never committed."""
    instrument = make_instrument(config, SIMULATED)
    taken: list[Measurement] = []
    try:
        run_baseline(instrument, config, taken.append)
    finally:
        instrument.output_off()
    c = BENCH_CIRCUIT
    sample = RecordedSample(
        Declaration(
            dataset="physics-lab-synthetic-rlc",
            origin="simulated",
            description="synthetic frequency-response acquisitions of the"
            " scripted baseline, a stand-in until a measured RLC sample passes"
            " the dataset gate",
            units={"source": "V", "response": "V"},
            provenance=f"pbc.instruments.simulated.SimulatedRLCBench, seed"
            f" {config.seed}, R {c.resistance:g} ohm, L {c.inductance:g} H,"
            f" C {c.capacitance:g} F",
        ),
        tuple(
            RecordedCapture(
                m.point.amplitude_v,
                m.point.frequency_hz,
                m.capture.sample_rate_hz,
                {k: tuple(float(x) for x in v) for k, v in m.capture.channels.items()},
            )
            for m in taken
        ),
    )
    save_sample(path, sample)
    return sample


# -- export and evaluation -----------------------------------------------------

_RAW_FIELDS = ("point", "frequency_hz", "amplitude_v", "t_s", "source_v", "response_v")


def _number(x: float) -> str:
    return f"{float(x):.12g}"


def write_raw(path: Path, measurements: list[Measurement]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(_RAW_FIELDS)
        for number, m in enumerate(measurements, start=1):
            c = m.capture
            for t, s, r in zip(
                c.t, c.channels["source"], c.channels["response"], strict=True
            ):
                writer.writerow(
                    [
                        number,
                        _number(m.point.frequency_hz),
                        _number(m.point.amplitude_v),
                        _number(t),
                        _number(s),
                        _number(r),
                    ]
                )


def read_raw(path: Path) -> list[Point]:
    """The points recomputed from the raw samples of ``path``: the
    evaluator's own reading, independent of what the route reported."""
    rows: dict[int, list[dict[str, str]]] = {}
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.setdefault(int(row["point"]), []).append(row)
    points = []
    for number in sorted(rows):
        block = rows[number]
        frequency = float(block[0]["frequency_hz"])
        t = np.array([float(r["t_s"]) for r in block])
        capture = Capture(
            sample_rate_hz=1.0 / (t[1] - t[0]),
            t=t,
            channels={
                "source": np.array([float(r["source_v"]) for r in block]),
                "response": np.array([float(r["response_v"]) for r in block]),
            },
            units={},
        )
        gain, phase = transfer(capture, frequency)
        points.append(Point(frequency, float(block[0]["amplitude_v"]), gain, phase))
    return points


def write_points(path: Path, points: list[Point]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("frequency_hz", "amplitude_v", "gain", "phase_deg"))
        for p in points:
            writer.writerow(
                [
                    _number(x)
                    for x in (p.frequency_hz, p.amplitude_v, p.gain, p.phase_deg)
                ]
            )


def _code_identity() -> str:
    root = Path(__file__).resolve().parents[2]  # src/pbc
    files = [
        *sorted((root / "instruments").glob("*.py")),
        *sorted((root / "products" / "physics_lab").glob("*.py")),
    ]
    return evidence.records.digest_files(files, root)


def _ledger(
    config: Config,
    route: str,
    record: InstrumentRun,
    raw: Path,
    out_dir: Path,
    check: Check | None,
    status: str,
    diagnostics: tuple[str, ...],
    answer: str | None,
) -> evidence.Ledger:
    task = evidence.RunRecord(
        task="the resonance frequency f0 and the quality factor Q of the prepared"
        " series RLC circuit, from its frequency response",
        hypothesis="the circuit responds as a driven, damped linear oscillator:"
        " the phase of V_C / V_S is -90 degrees at f0 and the gain there is Q",
        assumptions=(
            "the transient has settled before each record",
            "the channels are ideal (gain 1, no offset, no delay)",
            "the circuit stays the prepared one; nothing rewires it",
        ),
        protocol_version=PROTOCOL_VERSION,
        split={
            "probed": "the frequencies the route chose, within the envelope",
            "reference": "the closed form of the model, held by the evaluator"
            " and never given to the route",
        },
        seeds=(config.seed,),
        budgets={
            "measurements": config.agent_budget
            if route == AGENT
            else config.coarse_points + config.refine_points
        },
        code=_code_identity(),
        configuration=evidence.digest_value(dict(record.configuration)),
        environment={
            "python": platform.python_version(),
            "numpy": np.__version__,
            "execution_mode": record.mode,
            "label": record.label,
        },
    )
    ledger = evidence.Ledger(task)
    attempt_id = f"{route}-1"
    raw_artifact = evidence.Artifact.of("raw samples", raw, out_dir)
    ledger.add_attempt(
        evidence.Attempt(
            id=attempt_id,
            candidate=route,
            cycle=1,
            status=status,
            diagnostics=diagnostics,
            artifacts=(raw_artifact,),
        )
    )
    if check is not None:
        ledger.add_evaluation(
            evidence.Evaluation(
                attempt=attempt_id,
                evaluator=f"physics-lab evaluator {PROTOCOL_VERSION}",
                correct=check.correct,
                metrics={k: float(v) for k, v in check.metrics.items()},
                resources={"measurements": int(check.metrics["points"])},
                depends_on=(raw_artifact,),
                code=task.code,
                configuration=task.configuration,
            )
        )
    if answer is not None:
        ledger.add_report(
            evidence.CandidateReport(
                attempt=attempt_id,
                claims_correct=True if answer else None,
                details={"answer": answer},
            )
        )
    ledger.add_claim(
        evidence.Claim(
            id="resonance",
            text="f0 and Q measured by this run agree with the closed form of the"
            " circuit within the evaluator's tolerances",
            scope=f"this circuit, {record.mode} mode, seed {config.seed}",
            runs={attempt_id: True},
        )
    )
    return ledger


def _export(
    config: Config,
    out_dir: Path,
    route: str,
    record: InstrumentRun,
    measurements: list[Measurement],
    answer: str | None,
    diagnostics: tuple[str, ...],
    sample: Path | None,
) -> Result:
    from pbc.products.physics_lab.report import write_report

    files = {
        "raw": out_dir / "raw.csv",
        "points": out_dir / "points.csv",
        "report": out_dir / "report.md",
        "figure": out_dir / "frequency-response.svg",
        "run": out_dir / "run.json",
        "evidence": out_dir / "evidence.json",
    }
    write_raw(files["raw"], measurements)
    write_points(files["points"], [m.point for m in measurements])
    recomputed = read_raw(files["raw"]) if measurements else []
    circuit: SeriesRLC = BENCH_CIRCUIT
    check = evaluate(recomputed, circuit) if recomputed else None
    analysis = analyse(recomputed)
    if diagnostics:
        status = evidence.FAILED
    elif check is None or check.correct is None:
        status = evidence.INCONCLUSIVE
        diagnostics = (analysis.note,)
    else:
        status = evidence.COMPLETED
    ledger = _ledger(
        config,
        route,
        record,
        files["raw"],
        out_dir,
        check,
        status,
        diagnostics,
        answer,
    )
    evidence.save(ledger, files["evidence"])
    summary = evidence.summary(ledger, out_dir)
    data: dict[str, Any] = {
        "product": "physics-lab",
        "protocol": PROTOCOL_VERSION,
        "route": route,
        "status": status,
        "diagnostics": list(diagnostics),
        "run": record.to_dict(),
        "sample": None if sample is None else str(sample),
        "check": None
        if check is None
        else {"correct": check.correct, "note": check.note, "metrics": check.metrics},
        "candidate_answer": None
        if answer is None
        else {"text": answer, "label": evidence.UNVERIFIED},
        "evidence": {"file": files["evidence"].name, "summary": summary.text()},
    }
    files["run"].write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    result = Result(
        out_dir=out_dir,
        route=route,
        mode=record.mode,
        status=status,
        measurements=measurements,
        analysis=analysis,
        check=check,
        run=record,
        candidate_answer=answer,
        diagnostics=diagnostics,
        files=files,
    )
    write_report(result, recomputed, circuit)
    return result
