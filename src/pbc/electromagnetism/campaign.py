"""Adaptive and resumable measurement campaigns on the frequency-response
protocol of F138 (lesson SA6, F143).

One point is measured as F138's protocol measures it
(``f138-frequency-response-1``): drive the series RLC circuit at a frequency
f, acquire a whole number of periods after the transient has settled, and
read the gain and the phase of the capacitor voltage against the source.
The resonance f0 is where the phase crosses -90 degrees (linear in the phase
against log f between the two points that bracket it), and Q comes from the
gains of those two points through the second-order response, averaged. The
estimator is the protocol's own (``pbc.products.physics_lab.protocol``,
which no lesson may import; a unit test compares the two).

A campaign decides where to measure next. Its classical adaptive policy
(``suggest``) is a log-spaced sweep, then bisection of the bracket of -90
degrees until it is narrower than the plan's target, then repeats at both
ends of the final bracket, whose spread gives the uncertainty of f0. Every
suggestion names the measurements it follows from, and one that names a
measurement the campaign did not make is refused (``check_suggestion``).

After every measurement the campaign writes a checkpoint. A stop of the
instrument ends the segment: the output is switched off, the measurement in
flight is not kept, and the evaluator's ledger of ``pbc.evidence`` records the
segment as inconclusive with its checkpoint and that checkpoint's digest. A
later segment resumes only from a valid checkpoint (``resume``): the latest
one the ledger recorded, unchanged since, written for the same protocol and
plan, on the same bench, by a campaign that did not finish. Anything else is
refused before the instrument is touched.
"""

import itertools
import json
import math
import os
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from pbc.electromagnetism.circuits import SeriesRLC, steady_phasor
from pbc.evidence import (
    COMPLETED,
    INCONCLUSIVE,
    Artifact,
    Attempt,
    ContractError,
    Evaluation,
    Ledger,
    RunRecord,
    digest_file,
    digest_value,
)
from pbc.instruments import Instrument, Stopped

PROTOCOL_VERSION = "f143-campaign-1"
POINT_PROTOCOL = "f138-frequency-response-1"
CANDIDATE = "campaign"
EVALUATOR = "pbc.electromagnetism.campaign.evaluate, version 1"
# The evaluator's tolerance on f0 against the closed form: F138's.
F0_TOLERANCE = 0.01  # relative

SWEEP, REFINE, REPEAT = "sweep", "refine", "repeat"
INTERRUPTED, COMPLETE, BUDGET_SPENT, NO_BRACKET = (
    "interrupted",
    "complete",
    "budget spent",
    "no bracket",
)

# The first diagnostic of a segment's attempt: how the campaign ended. The
# ledger's status says only completed or inconclusive; this says which.
STATUS_NOTE = "{status} after {made} measurements; output off"

# The checks of a resume, in the order they are made.
RESUME_CHECKS = ("recorded", "unchanged", "protocol", "bench", "unfinished")


@dataclass(frozen=True)
class Plan:
    """The fixed decisions of a campaign, made before its first measurement.

    ``target_width`` is the relative width (high / low - 1) of the final
    bracket of -90 degrees; ``budget`` counts measurements over every
    segment of the campaign."""

    low_hz: float = 1_000.0
    high_hz: float = 25_000.0
    sweep_points: int = 9
    target_width: float = 0.002
    repeats: int = 3
    budget: int = 30
    amplitude_v: float = 1.0
    periods: int = 8
    samples_per_period: int = 64

    def __post_init__(self):
        if not 0 < self.low_hz < self.high_hz:
            raise ValueError("need 0 < low_hz < high_hz")
        if self.sweep_points < 3 or self.repeats < 1 or self.budget < 1:
            raise ValueError("need at least 3 sweep points, 1 repeat, budget 1")


@dataclass(frozen=True)
class Measurement:
    """One measured point, with its id in the order the campaign made it,
    the stage that asked for it, and the measurements that suggestion
    followed from."""

    id: str
    frequency_hz: float
    gain: float
    phase_deg: float
    stage: str
    basis: tuple[str, ...]


@dataclass(frozen=True)
class Suggestion:
    """Where to measure next, why, and the measurements it follows from."""

    frequency_hz: float
    stage: str
    basis: tuple[str, ...]
    reason: str


class SuggestionRefused(ContractError):
    """A suggestion that names a measurement the campaign did not make."""


class ResumeRefused(ContractError):
    """A resume from a checkpoint that is not valid; ``check`` names the
    check of ``RESUME_CHECKS`` that failed."""

    def __init__(self, check: str, reason: str):
        super().__init__(f"{check}: {reason}")
        self.check = check
        self.reason = reason


def measure_point(
    instrument: Instrument, plan: Plan, frequency_hz: float
) -> tuple[float, float]:
    """The gain and the phase (degrees, in (-270, 90]) of the response
    against the source at ``frequency_hz``, by F138's procedure: a whole
    number of periods, sampled after the transient has settled."""
    instrument.excite(plan.amplitude_v, frequency_hz)
    rate = plan.samples_per_period * frequency_hz
    capture = instrument.acquire(rate, plan.periods * plan.samples_per_period + 1)
    omega = 2.0 * math.pi * frequency_hz
    source = steady_phasor(capture.channels["source"], capture.t, omega)
    response = steady_phasor(capture.channels["response"], capture.t, omega)
    ratio = response / source
    phase = math.degrees(math.atan2(ratio.imag, ratio.real))
    if phase > 90.0:
        phase -= 360.0
    return float(abs(ratio)), float(phase)


@dataclass(frozen=True)
class Point:
    """The measurements at one frequency, averaged: the mean gain and
    phase, their count, the standard error of the phase (``None`` for a
    single measurement), and their ids."""

    frequency_hz: float
    gain: float
    phase_deg: float
    count: int
    phase_error_deg: float | None
    ids: tuple[str, ...]


def points(measurements: Sequence[Measurement]) -> list[Point]:
    """The measurements grouped by frequency, in increasing frequency."""
    groups: dict[float, list[Measurement]] = {}
    for m in measurements:
        groups.setdefault(m.frequency_hz, []).append(m)
    found = []
    for frequency in sorted(groups):
        group = groups[frequency]
        phases = np.array([m.phase_deg for m in group])
        error = (
            float(phases.std(ddof=1) / math.sqrt(len(group)))
            if len(group) > 1
            else None
        )
        found.append(
            Point(
                frequency,
                float(np.mean([m.gain for m in group])),
                float(phases.mean()),
                len(group),
                error,
                tuple(m.id for m in group),
            )
        )
    return found


def bracket(measurements: Sequence[Measurement]) -> tuple[Point, Point] | None:
    """The two neighbouring points whose phases bracket -90 degrees, as
    F138's analysis finds them, or ``None``."""
    for a, b in itertools.pairwise(points(measurements)):
        if a.phase_deg >= -90.0 >= b.phase_deg and a.phase_deg != b.phase_deg:
            return a, b
    return None


@dataclass(frozen=True)
class Analysis:
    """The estimates of the measurements: f0 and Q by F138's estimator,
    the standard error of f0 from the repeats (``None`` without them), and
    the bracket."""

    f0_hz: float | None
    q: float | None
    f0_error_hz: float | None
    bracket_hz: tuple[float, float] | None


def _quality(point: Point, f0: float) -> float | None:
    """Q from one point of |H| = 1 / sqrt((1 - x^2)^2 + (x / Q)^2), x = f / f0,
    or None where the gain is too high for that form."""
    x = point.frequency_hz / f0
    rest = 1.0 / point.gain**2 - (1.0 - x * x) ** 2
    return x / math.sqrt(rest) if rest > 0 else None


def analyse(measurements: Sequence[Measurement]) -> Analysis:
    """f0 where the phase crosses -90 degrees, linear in log f between the
    bracketing points; Q from their gains, averaged; and the standard error
    of f0 propagated from the standard errors of the two phases."""
    found = bracket(measurements)
    if found is None:
        return Analysis(None, None, None, None)
    a, b = found
    x = (a.phase_deg + 90.0) / (a.phase_deg - b.phase_deg)
    la, lb = math.log(a.frequency_hz), math.log(b.frequency_hz)
    f0 = math.exp(la + x * (lb - la))
    estimates = [_quality(p, f0) for p in (a, b)]
    q = None if None in estimates else sum(estimates) / 2.0
    error = None
    if a.phase_error_deg is not None and b.phase_error_deg is not None:
        span = (a.phase_deg - b.phase_deg) ** 2
        da = (-b.phase_deg - 90.0) / span * a.phase_error_deg
        db = (a.phase_deg + 90.0) / span * b.phase_error_deg
        error = f0 * (lb - la) * math.hypot(da, db)
    return Analysis(f0, q, error, (a.frequency_hz, b.frequency_hz))


def reference(circuit: SeriesRLC) -> dict[str, float]:
    """The closed form of the circuit, which the campaign never sees."""
    return {
        "f0_hz": float(circuit.natural_frequency / (2.0 * math.pi)),
        "q": float(circuit.quality_factor),
    }


def evaluate(
    measurements: Sequence[Measurement], circuit: SeriesRLC
) -> dict[str, float]:
    """The evaluator's numbers: the estimates against the closed form."""
    analysis = analyse(measurements)
    ref = reference(circuit)
    if analysis.f0_hz is None or analysis.q is None:
        return {"measurements": float(len(measurements))}
    return {
        "measurements": float(len(measurements)),
        "f0_hz": analysis.f0_hz,
        "q": analysis.q,
        "f0_relative_error": analysis.f0_hz / ref["f0_hz"] - 1.0,
        "q_relative_error": analysis.q / ref["q"] - 1.0,
    }


def suggest(plan: Plan, measurements: Sequence[Measurement]) -> Suggestion | None:
    """The next measurement of the classical adaptive policy, or ``None``
    when the campaign is done (or cannot go on: no bracket after the
    sweep)."""
    sweep = np.geomspace(plan.low_hz, plan.high_hz, plan.sweep_points)
    made = sum(m.stage == SWEEP for m in measurements)
    if made < plan.sweep_points:
        return Suggestion(
            float(sweep[made]),
            SWEEP,
            (),
            f"sweep point {made + 1} of {plan.sweep_points}",
        )
    found = bracket(measurements)
    if found is None:
        return None
    a, b = found
    if b.frequency_hz / a.frequency_hz - 1.0 > plan.target_width:
        return Suggestion(
            math.sqrt(a.frequency_hz * b.frequency_hz),
            REFINE,
            a.ids + b.ids,
            f"the middle (in log f) of the bracket {a.frequency_hz:.1f} to"
            f" {b.frequency_hz:.1f} Hz, where the phase crosses -90 degrees",
        )
    for end in (a, b):
        if end.count < plan.repeats:
            return Suggestion(
                end.frequency_hz,
                REPEAT,
                end.ids,
                f"repeat {end.count + 1} of {plan.repeats} at the bracket's"
                f" end {end.frequency_hz:.1f} Hz",
            )
    return None


def check_suggestion(
    suggestion: Suggestion, measurements: Sequence[Measurement]
) -> None:
    """Refuse a suggestion that follows from a measurement the campaign did
    not make."""
    made = {m.id for m in measurements}
    missing = [i for i in suggestion.basis if i not in made]
    if missing:
        raise SuggestionRefused(
            f"the suggestion of {suggestion.frequency_hz:.1f} Hz follows from"
            f" {', '.join(missing)}, which the campaign did not make"
        )


# -- checkpoints -------------------------------------------------------------

CHECKPOINT_FORMAT = 1


@dataclass(frozen=True)
class Checkpoint:
    """The state of a campaign after its last completed measurement."""

    protocol: str
    plan: Mapping[str, Any]
    device: Mapping[str, str]
    measurements: tuple[Measurement, ...]


def device(instrument: Instrument) -> dict[str, str]:
    """The bench as the instrument names it, without the seed of a
    simulated bench's noise: the seed belongs to the run, not to the
    device, and a resumed segment draws new noise."""
    found = dict(instrument.snapshot()["device"])
    found.pop("seed", None)
    return found


def save_checkpoint(path: Path, checkpoint: Checkpoint) -> None:
    """Write ``checkpoint`` to ``path`` atomically: a reader finds the old
    checkpoint or the new one, never half of one."""
    data = {
        "format": CHECKPOINT_FORMAT,
        "protocol": checkpoint.protocol,
        "plan": dict(checkpoint.plan),
        "device": dict(checkpoint.device),
        "measurements": [asdict(m) for m in checkpoint.measurements],
    }
    partial = path.with_name(path.name + ".partial")
    partial.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    os.replace(partial, path)


def load_checkpoint(path: Path) -> Checkpoint:
    """Read a checkpoint, refusing anything that is not exactly one."""
    data = json.loads(path.read_text(encoding="utf-8"))
    keys = {"format", "protocol", "plan", "device", "measurements"}
    if not isinstance(data, dict) or set(data) != keys:
        raise ValueError(f"{path} is not a checkpoint")
    if data["format"] != CHECKPOINT_FORMAT:
        raise ValueError(f"{path}: format is not {CHECKPOINT_FORMAT}")
    measurements = tuple(
        Measurement(
            m["id"],
            float(m["frequency_hz"]),
            float(m["gain"]),
            float(m["phase_deg"]),
            m["stage"],
            tuple(m["basis"]),
        )
        for m in data["measurements"]
    )
    return Checkpoint(data["protocol"], data["plan"], data["device"], measurements)


# -- a campaign, in segments ---------------------------------------------------


@dataclass(frozen=True)
class Segment:
    """What one run of the campaign did: its id, how it ended, its
    measurements (those resumed from first), the suggestion that was in
    flight when a stop came, the checkpoint, and the instrument's output
    after the cleanup (``None``: off)."""

    id: str
    status: str
    measurements: tuple[Measurement, ...]
    lost: Suggestion | None
    checkpoint: Path
    output: Mapping[str, float] | None


def run_segment(
    instrument: Instrument,
    plan: Plan,
    ledger: Ledger,
    root: Path,
    checkpoint: Path,
    segment: str,
    resumed: Checkpoint | None = None,
    prior: tuple[str, ...] = (),
) -> Segment:
    """Run the campaign until it is done, its budget is spent, or the
    instrument stops; checkpoint after every measurement; switch the output
    off whatever happens; and record the segment in ``ledger``."""
    made = list(resumed.measurements) if resumed is not None else []
    state = Checkpoint(PROTOCOL_VERSION, asdict(plan), device(instrument), ())
    lost = None
    status = COMPLETE
    try:
        while (suggestion := suggest(plan, made)) is not None:
            if len(made) >= plan.budget:
                status = BUDGET_SPENT
                break
            check_suggestion(suggestion, made)
            try:
                gain, phase = measure_point(instrument, plan, suggestion.frequency_hz)
            except Stopped:
                lost, status = suggestion, INTERRUPTED
                break
            made.append(
                Measurement(
                    f"m{len(made) + 1:02d}",
                    suggestion.frequency_hz,
                    gain,
                    phase,
                    suggestion.stage,
                    suggestion.basis,
                )
            )
            state = Checkpoint(state.protocol, state.plan, state.device, tuple(made))
            save_checkpoint(checkpoint, state)
        else:
            if bracket(made) is None:
                status = NO_BRACKET
    finally:
        instrument.output_off()
    output = instrument.snapshot()["output"]
    _record(ledger, root, segment, status, made, lost, checkpoint, prior)
    return Segment(segment, status, tuple(made), lost, checkpoint, output)


def _record(
    ledger: Ledger,
    root: Path,
    segment: str,
    status: str,
    made: list[Measurement],
    lost: Suggestion | None,
    checkpoint: Path,
    prior: tuple[str, ...],
) -> None:
    """The segment as an attempt of the campaign, its checkpoint the
    artifact with the digest it has now; a complete one is evaluated."""
    notes = [STATUS_NOTE.format(status=status, made=len(made))]
    if lost is not None:
        notes.append(
            f"the measurement at {lost.frequency_hz:.1f} Hz ({lost.stage}) was in"
            " flight and is not kept"
        )
    artifact = Artifact.of("checkpoint", checkpoint, root)
    ledger.add_attempt(
        Attempt(
            segment,
            CANDIDATE,
            ledger.cycle,
            COMPLETED if status == COMPLETE else INCONCLUSIVE,
            tuple(notes),
            (artifact,),
            prior,
        )
    )


def evaluate_segment(
    ledger: Ledger, root: Path, segment: str, circuit: SeriesRLC
) -> Evaluation:
    """The evaluator recomputes the estimates of a complete segment from its
    checkpoint as recorded and compares them with the closed form."""
    attempt = ledger.attempt(segment)
    if attempt is None or attempt.status != COMPLETED:
        raise ContractError(f"{segment} is not a complete segment")
    (artifact,) = attempt.artifacts
    if digest_file(root / artifact.path) != artifact.sha256:
        raise ContractError(f"the checkpoint of {segment} changed since recorded")
    measurements = load_checkpoint(root / artifact.path).measurements
    metrics = evaluate(measurements, circuit)
    ref = reference(circuit)
    evaluation = Evaluation(
        segment,
        EVALUATOR,
        None
        if "f0_hz" not in metrics
        else bool(abs(metrics["f0_relative_error"]) <= F0_TOLERANCE),
        metrics | {"reference_f0_hz": ref["f0_hz"], "reference_q": ref["q"]},
        {"measurements": len(measurements)},
        (artifact,),
        ledger.record.code,
        ledger.record.configuration,
    )
    ledger.add_evaluation(evaluation)
    return evaluation


def _interrupted(attempt: Attempt) -> bool:
    """Whether the segment of ``attempt`` was stopped: the only way a
    campaign is unfinished. A segment that spent the budget or found no
    bracket is inconclusive too, but its campaign has finished."""
    return (
        attempt.status == INCONCLUSIVE
        and bool(attempt.diagnostics)
        and attempt.diagnostics[0].startswith(f"{INTERRUPTED} after ")
    )


def resume(
    ledger: Ledger, root: Path, path: Path, plan: Plan, instrument: Instrument
) -> tuple[Checkpoint, str]:
    """The checkpoint at ``path`` and the segment it ends, if a campaign may
    resume from it; otherwise ``ResumeRefused``, raised before the
    instrument is asked to do anything."""
    segments = [a for a in ledger.attempts if a.candidate == CANDIDATE]
    latest = segments[-1] if segments else None
    recorded = latest.artifacts[0] if latest is not None else None
    try:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:  # outside the ledger's root: never one it recorded
        relative = None
    if (
        recorded is None
        or recorded.sha256 is None  # no checkpoint existed when recorded
        or recorded.path != relative
    ):
        raise ResumeRefused(
            "recorded", "it is not the latest checkpoint the ledger recorded"
        )
    if digest_file(path) != recorded.sha256:
        raise ResumeRefused("unchanged", "it changed after the ledger recorded it")
    checkpoint = load_checkpoint(path)
    if checkpoint.protocol != PROTOCOL_VERSION or dict(checkpoint.plan) != asdict(plan):
        raise ResumeRefused("protocol", "it was written for another protocol or plan")
    if dict(checkpoint.device) != device(instrument):
        raise ResumeRefused("bench", "it was written on another bench")
    if not _interrupted(latest):
        raise ResumeRefused("unfinished", "its campaign has finished")
    return checkpoint, latest.id


def new_ledger(plan: Plan, seeds: tuple[int, ...], code: str) -> Ledger:
    """The evaluator's ledger of one campaign under ``plan``; ``code`` is the
    digest of the campaign's source."""
    return Ledger(
        RunRecord(
            task="locate the resonance f0 of the series RLC bench and its Q",
            hypothesis="the phase of V_C / V_S crosses -90 degrees once, at f0",
            assumptions=(
                "a second-order response near f0",
                "the bench is the same device in every segment",
            ),
            protocol_version=PROTOCOL_VERSION,
            split={"truth": "the closed form of the circuit, held by the evaluator"},
            seeds=seeds,
            budgets={"measurements": plan.budget},
            code=code,
            configuration=digest_value(asdict(plan)),
            environment={"point protocol": POINT_PROTOCOL},
        )
    )
