"""The campaigns of the Autonomous Physics Lab (F145): a plan over the three
protocols, executed step by step through the guarded instrument, with a
checkpoint after every measurement and a resume that accepts only a valid
checkpoint.

**The plan** (``CampaignPlan``) is fixed before the first measurement: the
declared circuit (its topology, ``SERIES_RLC`` or ``LED_PAIR``), the
protocols in order, their settings, the target interval widths, the
repetitions, and the budget of measurements over every segment. The
circuit is the learner's: the product never rewires it, and another
topology is another plan, with its own confirmation of the circuit.

**A step** names a protocol, a setting, the stage that asked for it
(``SWEEP``, ``REFINE``, ``REPEAT``, ``RETRY``), and the measurements it
follows from. ``Campaign.execute`` measures it through the protocol's own
function, passes the capture through the quality gate, and records the
result with its raw samples; an invalid capture is recorded and never
fitted. Every route, the classical adaptive policy (``next_step``), the
scripted sweep, and the agent's tools, reaches the instrument only here.

**The classical adaptive policy**: the frequency response sweeps, then
measures at the geometric middle of the two valid points that bracket
-90 degrees until the interval of f0 is at its target; the transient
protocol repeats the ring-down until the interval of Q is at its target;
the amplitude response measures its amplitudes, then the middle of the
two neighbours whose gains differ most, ``amplitude_refinements`` times.
An invalid measurement is retried once at the same setting.

**Checkpoints and resume.** After each measurement the campaign writes its
checkpoint atomically and records the checkpoint's digest in its journal.
A stop of the instrument ends the segment: the output is off, the
measurement in flight is not kept, and the journal records the segment as
interrupted. ``resume`` accepts only the journal's latest checkpoint,
unchanged since, written for the same plan on the same bench, by a
campaign that was interrupted; anything else is refused before the
instrument is touched.
"""

import hashlib
import itertools
import json
import math
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from pbc.electromagnetism.circuits import SeriesRLC
from pbc.instruments import Capture, Instrument, Refused, Stopped
from pbc.products.physics_lab import nonlinear, resonance, transient
from pbc.products.physics_lab.estimates import Estimate
from pbc.products.physics_lab.quality import IDEAL_RAILS, Rails

FORMAT = 1
FREQUENCY_RESPONSE = "frequency-response"
TRANSIENT = "transient"
AMPLITUDE_RESPONSE = "amplitude-response"
PROTOCOLS = (FREQUENCY_RESPONSE, TRANSIENT, AMPLITUDE_RESPONSE)
PROTOCOL_VERSIONS = {
    FREQUENCY_RESPONSE: resonance.PROTOCOL_VERSION,
    TRANSIENT: transient.PROTOCOL_VERSION,
    AMPLITUDE_RESPONSE: nonlinear.PROTOCOL_VERSION,
}
SERIES_RLC = "series-rlc"
LED_PAIR = "led-pair"
CIRCUITS = {
    SERIES_RLC: (FREQUENCY_RESPONSE, TRANSIENT),
    LED_PAIR: (AMPLITUDE_RESPONSE,),
}
SWEEP, REFINE, REPEAT, RETRY = "sweep", "refine", "repeat", "retry"
# How a segment ended.
COMPLETE, INTERRUPTED, BUDGET_SPENT, FAILED = (
    "complete",
    "interrupted",
    "budget spent",
    "failed",
)


class ResumeRefused(Refused):
    """A checkpoint the campaign may not resume from, with the check it
    failed."""

    def __init__(self, check: str, reason: str):
        super().__init__(f"resume refused ({check}): {reason}")
        self.check = check


@dataclass(frozen=True)
class CampaignPlan:
    """The fixed decisions of a campaign (units in the field names).

    ``f0_target`` and ``q_target`` are the relative widths of the
    intervals (two standard errors either side) at which the adaptive
    policy stops refining; ``budget`` counts every measurement, valid or
    not, over every segment."""

    circuit: str = SERIES_RLC
    protocols: tuple[str, ...] = (FREQUENCY_RESPONSE, TRANSIENT)
    amplitude_v: float = 1.0
    # the frequency response
    low_hz: float = 1_000.0
    high_hz: float = 25_000.0
    sweep_points: int = 9
    periods: int = 8
    samples_per_period: int = 64
    f0_target: float = 0.0005
    # the transient response
    square_hz: float = 100.0
    transient_rate_hz: float = 500_000.0
    ringing_max_hz: float = 25_000.0
    min_ringdowns: int = 3
    q_target: float = 0.01
    # the amplitude response
    amplitudes_v: tuple[float, ...] = (0.2, 0.5, 1.0, 1.4, 1.6, 1.8, 2.0)
    amplitude_frequency_hz: float = 1_000.0
    amplitude_refinements: int = 2
    series_resistance_ohm: float = 100.0
    # the declared parts of the series RLC circuit (nominal values): the
    # simulator's circuit, and the bound on the square wave's frequency
    inductance_h: float = 10e-3
    capacitance_f: float = 100e-9
    # every protocol
    budget: int = 40

    def __post_init__(self):
        if self.circuit not in CIRCUITS:
            raise ValueError(
                f"unknown circuit {self.circuit!r}; one of {list(CIRCUITS)}"
            )
        allowed = CIRCUITS[self.circuit]
        wrong = [p for p in self.protocols if p not in allowed]
        if not self.protocols or wrong:
            raise ValueError(
                f"the {self.circuit} circuit runs {', '.join(allowed)}; not {wrong}"
            )
        if not 0 < self.low_hz < self.high_hz or self.sweep_points < 3:
            raise ValueError("need 0 < low_hz < high_hz and 3 sweep points")
        if self.min_ringdowns < 1 or self.budget < 1:
            raise ValueError("need a ring-down and a budget")
        if len(self.amplitudes_v) < 2:
            raise ValueError("need two amplitudes")
        if TRANSIENT in self.protocols:
            transient.check_settings(self.transient_settings, self.declared_circuit)

    @property
    def declared_circuit(self) -> SeriesRLC:
        """The series RLC circuit as declared: nominal parts."""
        return SeriesRLC(
            self.series_resistance_ohm, self.inductance_h, self.capacitance_f
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["protocols"] = list(self.protocols)
        data["amplitudes_v"] = list(self.amplitudes_v)
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CampaignPlan:
        known = set(cls.__dataclass_fields__)
        unknown = sorted(set(data) - known)
        if unknown:
            raise ValueError(f"unknown keys of a campaign plan: {', '.join(unknown)}")
        values = dict(data)
        for key in ("protocols", "amplitudes_v"):
            if key in values:
                values[key] = tuple(values[key])
        return cls(**values)

    def digest(self) -> str:
        text = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(text.encode()).hexdigest()

    @property
    def transient_settings(self) -> transient.TransientSettings:
        return transient.TransientSettings(
            self.amplitude_v,
            self.square_hz,
            self.transient_rate_hz,
            self.ringing_max_hz,
        )

    @property
    def nonlinear_settings(self) -> nonlinear.NonlinearSettings:
        return nonlinear.NonlinearSettings(
            self.amplitude_frequency_hz,
            self.periods,
            self.samples_per_period,
            self.series_resistance_ohm,
        )


@dataclass(frozen=True)
class Step:
    """What to measure next: the ``protocol``, its ``setting`` (the
    frequency in Hz for a point of the frequency response, the amplitude in
    V for the amplitude response, none for a ring-down), the ``stage`` that
    asked for it, and the ids of the measurements it follows from."""

    protocol: str
    setting: float | None
    stage: str
    basis: tuple[str, ...] = ()


@dataclass(frozen=True)
class Record:
    """One measurement of the campaign: its id in the order made, the step,
    whether the gate found it valid, the gate's note, the numbers it gave,
    and its raw capture."""

    id: str
    step: Step
    valid: bool
    note: str
    numbers: Mapping[str, float]
    capture: Capture
    gate: Mapping[str, Any] = field(default_factory=dict)


def _numbers(measurement: Any) -> dict[str, float]:
    if isinstance(measurement, resonance.PointMeasurement):
        return {} if measurement.point is None else measurement.point.to_dict()
    if isinstance(measurement, transient.Ringdown):
        return {} if measurement.fit is None else measurement.fit.to_dict()
    if isinstance(measurement, nonlinear.AmplitudeMeasurement):
        return {} if measurement.point is None else measurement.point.to_dict()
    raise TypeError(type(measurement))


class Campaign:
    """A campaign under ``plan`` on ``instrument``: the records so far, the
    budget, and the checkpoint at ``checkpoint`` (none when None)."""

    def __init__(
        self,
        plan: CampaignPlan,
        instrument: Instrument,
        rails: Rails = IDEAL_RAILS,
        checkpoint: Path | None = None,
        records: Sequence[Record] = (),
        on_record: Callable[[Record], None] | None = None,
    ):
        self.plan = plan
        self.instrument = instrument
        self.rails = rails
        self.checkpoint = checkpoint
        self.records: list[Record] = list(records)
        self.on_record = on_record

    @property
    def remaining(self) -> int:
        return self.plan.budget - len(self.records)

    def execute(self, step: Step) -> Record:
        """Measure ``step`` through the protocol's function and record it.
        Refuses a step outside the plan, beyond the budget, or one whose
        basis names a measurement the campaign did not make."""
        if step.protocol not in self.plan.protocols:
            raise Refused(f"the plan does not run the protocol {step.protocol!r}")
        if self.remaining <= 0:
            raise Refused(f"the budget of {self.plan.budget} measurements is spent")
        made = {r.id for r in self.records}
        unknown = [b for b in step.basis if b not in made]
        if unknown:
            raise Refused(f"the step names measurements not made: {unknown}")
        plan = self.plan
        # region: execute
        if step.protocol == FREQUENCY_RESPONSE:
            measured: Any = resonance.measure_point(
                self.instrument,
                float(step.setting or 0.0),
                plan.amplitude_v,
                plan.periods,
                plan.samples_per_period,
                self.rails,
            )
        elif step.protocol == TRANSIENT:
            measured = transient.measure_ringdown(
                self.instrument, plan.transient_settings, self.rails
            )
        else:
            measured = nonlinear.measure_amplitude(
                self.instrument,
                float(step.setting or 0.0),
                plan.nonlinear_settings,
                self.rails,
            )
        # endregion: execute
        record = Record(
            id=f"m{len(self.records) + 1:03d}",
            step=step,
            valid=measured.valid,
            note=measured.note,
            numbers=_numbers(measured),
            capture=measured.capture,
            gate=measured.verdict.to_dict(),
        )
        self.records.append(record)
        if self.checkpoint is not None:
            save_checkpoint(self.checkpoint, self)
        if self.on_record is not None:
            self.on_record(record)
        return record

    def of(self, protocol: str) -> list[Record]:
        return [r for r in self.records if r.step.protocol == protocol]


# -- the analysis of the records -----------------------------------------------------


def response_points(records: Sequence[Record]) -> list[resonance.ResponsePoint]:
    return [
        resonance.ResponsePoint(**{k: float(v) for k, v in r.numbers.items()})
        for r in records
        if r.valid and r.step.protocol == FREQUENCY_RESPONSE
    ]


def resonance_fit(records: Sequence[Record]) -> resonance.ResonanceFit | None:
    return resonance.fit_resonance(response_points(records))


def ringdown_estimates(records: Sequence[Record]) -> tuple[Estimate, Estimate] | None:
    """The combined f0 and Q of the valid ring-downs."""
    fits = [r.numbers for r in records if r.valid and r.step.protocol == TRANSIENT]
    if not fits:
        return None
    from pbc.products.physics_lab.estimates import combine

    f0 = combine([Estimate(f["f0_hz"], f["f0_se"]) for f in fits]).estimate
    q = combine([Estimate(f["q"], f["q_se"]) for f in fits]).estimate
    return f0, q


def bracket(records: Sequence[Record]) -> tuple[Record, Record] | None:
    """The two valid points of the frequency response nearest each other
    whose phases bracket -90 degrees."""
    points = sorted(
        (r for r in records if r.valid and r.step.protocol == FREQUENCY_RESPONSE),
        key=lambda r: r.numbers["frequency_hz"],
    )
    found = None
    for a, b in itertools.pairwise(points):
        if a.numbers["phase_deg"] >= -90.0 >= b.numbers["phase_deg"]:
            width = b.numbers["frequency_hz"] / a.numbers["frequency_hz"]
            if found is None or width < found[0]:
                found = (width, a, b)
    return None if found is None else (found[1], found[2])


# -- the classical adaptive policy ---------------------------------------------------


def _retry(records: Sequence[Record], protocol: str) -> Step | None:
    """A retry of the last measurement of ``protocol`` when it was invalid
    and not itself a retry."""
    mine = [r for r in records if r.step.protocol == protocol]
    if mine and not mine[-1].valid and mine[-1].step.stage != RETRY:
        last = mine[-1]
        return Step(protocol, last.step.setting, RETRY, (last.id,))
    return None


def _next_frequency_response(plan: CampaignPlan, records: list[Record]) -> Step | None:
    retry = _retry(records, FREQUENCY_RESPONSE)
    if retry is not None:
        return retry
    sweep = np.geomspace(plan.low_hz, plan.high_hz, plan.sweep_points)
    asked = [r for r in records if r.step.protocol == FREQUENCY_RESPONSE]
    swept = {r.step.setting for r in asked if r.step.stage in (SWEEP, RETRY)}
    for frequency in sweep:
        if round(float(frequency), 3) not in swept:
            return Step(FREQUENCY_RESPONSE, round(float(frequency), 3), SWEEP)
    found = bracket(records)
    if found is None:
        return None
    fit = resonance_fit(records)
    if fit is not None and fit.f0_hz.relative_width <= plan.f0_target:
        return None
    a, b = found
    middle = math.sqrt(a.numbers["frequency_hz"] * b.numbers["frequency_hz"])
    if middle / a.numbers["frequency_hz"] - 1.0 < 1e-6:
        return None  # the bracket cannot be split further
    return Step(FREQUENCY_RESPONSE, round(middle, 3), REFINE, (a.id, b.id))


def _next_transient(plan: CampaignPlan, records: list[Record]) -> Step | None:
    retry = _retry(records, TRANSIENT)
    if retry is not None:
        return retry
    done = [r for r in records if r.step.protocol == TRANSIENT]
    valid = [r for r in done if r.valid]
    if len(valid) < plan.min_ringdowns:
        return Step(TRANSIENT, None, REPEAT, tuple(r.id for r in valid))
    estimates = ringdown_estimates(records)
    if estimates is not None and estimates[1].relative_width > plan.q_target:
        return Step(TRANSIENT, None, REPEAT, tuple(r.id for r in valid))
    return None


def _next_amplitude(plan: CampaignPlan, records: list[Record]) -> Step | None:
    retry = _retry(records, AMPLITUDE_RESPONSE)
    if retry is not None:
        return retry
    done = [r for r in records if r.step.protocol == AMPLITUDE_RESPONSE]
    asked = {r.step.setting for r in done}
    for amplitude in plan.amplitudes_v:
        if float(amplitude) not in asked:
            return Step(AMPLITUDE_RESPONSE, float(amplitude), SWEEP)
    refined = [r for r in done if r.step.stage == REFINE]
    if len(refined) >= plan.amplitude_refinements:
        return None
    valid = sorted((r for r in done if r.valid), key=lambda r: r.step.setting or 0.0)
    best = None
    for a, b in itertools.pairwise(valid):
        change = abs(a.numbers["gain"] - b.numbers["gain"])
        if best is None or change > best[0]:
            best = (change, a, b)
    if best is None:
        return None
    _, a, b = best
    middle = round(0.5 * ((a.step.setting or 0.0) + (b.step.setting or 0.0)), 4)
    if middle in asked:
        return None
    return Step(AMPLITUDE_RESPONSE, middle, REFINE, (a.id, b.id))


NEXT = {
    FREQUENCY_RESPONSE: _next_frequency_response,
    TRANSIENT: _next_transient,
    AMPLITUDE_RESPONSE: _next_amplitude,
}


def next_step(plan: CampaignPlan, records: Sequence[Record]) -> Step | None:
    """The classical adaptive policy: the next step of the first protocol
    of the plan that is not done, or None when every one is."""
    for protocol in plan.protocols:
        step = NEXT[protocol](plan, list(records))
        if step is not None:
            return step
    return None


# -- checkpoints and the journal ------------------------------------------------------


def _capture_dict(capture: Capture) -> dict[str, Any]:
    return {
        "sample_rate_hz": capture.sample_rate_hz,
        "channels": {
            k: [None if not math.isfinite(x) else float(x) for x in np.asarray(v)]
            for k, v in capture.channels.items()
        },
        "units": dict(capture.units),
    }


def _capture_from(data: Mapping[str, Any]) -> Capture:
    channels = {
        k: np.array([np.nan if x is None else float(x) for x in v])
        for k, v in data["channels"].items()
    }
    n = len(next(iter(channels.values())))
    rate = float(data["sample_rate_hz"])
    return Capture(rate, np.arange(n) / rate, channels, dict(data["units"]))


def record_dict(record: Record) -> dict[str, Any]:
    return {
        "id": record.id,
        "step": {**asdict(record.step), "basis": list(record.step.basis)},
        "valid": record.valid,
        "note": record.note,
        "numbers": dict(record.numbers),
        "gate": dict(record.gate),
        "capture": _capture_dict(record.capture),
    }


def record_from(data: Mapping[str, Any]) -> Record:
    step = data["step"]
    return Record(
        id=data["id"],
        step=Step(
            step["protocol"], step["setting"], step["stage"], tuple(step["basis"])
        ),
        valid=bool(data["valid"]),
        note=data["note"],
        numbers={k: float(v) for k, v in data["numbers"].items()},
        capture=_capture_from(data["capture"]),
        gate=dict(data.get("gate", {})),
    )


def bench(instrument: Instrument) -> dict[str, str]:
    """The bench as the instrument names it, without the seed of a
    simulated bench's noise (a resumed segment draws new noise)."""
    found = {k: str(v) for k, v in instrument.snapshot()["device"].items()}
    found.pop("seed", None)
    return found


def save_checkpoint(path: Path, campaign: Campaign) -> None:
    """Write the campaign's state to ``path`` atomically: a reader finds the
    old checkpoint or the new one, never half of one."""
    data = {
        "format": FORMAT,
        "plan": campaign.plan.to_dict(),
        "plan_digest": campaign.plan.digest(),
        "bench": bench(campaign.instrument),
        "records": [record_dict(r) for r in campaign.records],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    partial.write_text(json.dumps(data) + "\n", encoding="utf-8")
    os.replace(partial, path)


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class Segment:
    """One run of the campaign: its number, how it ended, the records it
    made, the step in flight when it stopped (not kept), the digest of the
    checkpoint it left, and the instrument's output after the cleanup
    (None: off)."""

    number: int
    status: str
    made: tuple[str, ...]
    lost: Step | None
    checkpoint_digest: str | None
    output: Mapping[str, Any] | None
    diagnostics: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "status": self.status,
            "made": list(self.made),
            "lost": None if self.lost is None else asdict(self.lost),
            "checkpoint_digest": self.checkpoint_digest,
            "output": None if self.output is None else dict(self.output),
            "diagnostics": list(self.diagnostics),
        }


def load_journal(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))["segments"]


def append_journal(path: Path, segment: Segment) -> None:
    segments = [*load_journal(path), segment.to_dict()]
    partial = path.with_name(path.name + ".partial")
    partial.write_text(json.dumps({"segments": segments}, indent=1) + "\n")
    os.replace(partial, path)


Policy = Callable[[CampaignPlan, Sequence[Record]], Step | None]


def run_segment(
    campaign: Campaign,
    journal: Path,
    policy: Policy = next_step,
    start: int | None = None,
    refused: Refused | None = None,
) -> Segment:
    """Run ``campaign`` under ``policy`` until it is done, its budget is
    spent, or the instrument refuses; switch the output off at the end in
    every case; record the segment in ``journal``. The segment made the
    records from index ``start`` on: by default those made here; a caller
    that executed steps before (the agent's replay) passes the count it
    started from, and the refusal that already ended them as ``refused``,
    so that the journal records the segment as failed with its reason."""
    number = len(load_journal(journal)) + 1
    start = len(campaign.records) if start is None else start
    status, lost, diagnostics = COMPLETE, None, ()
    if refused is not None:
        status, diagnostics = FAILED, (str(refused),)
    try:
        # region: segment
        while refused is None:
            step = policy(campaign.plan, campaign.records)
            if step is None:
                break
            if campaign.remaining <= 0:
                status = BUDGET_SPENT
                break
            lost = step
            campaign.execute(step)
            lost = None
        # endregion: segment
    except Stopped as reason:
        status, diagnostics = INTERRUPTED, (str(reason),)
    except Refused as reason:
        status, diagnostics = FAILED, (str(reason),)
    finally:
        campaign.instrument.output_off()
    digest = (
        file_digest(campaign.checkpoint)
        if campaign.checkpoint is not None and campaign.checkpoint.exists()
        else None
    )
    segment = Segment(
        number,
        status,
        tuple(r.id for r in campaign.records[start:]),
        lost,
        digest,
        campaign.instrument.snapshot()["output"],
        diagnostics,
    )
    append_journal(journal, segment)
    return segment


RESUME_CHECKS = ("recorded", "unchanged", "plan", "bench", "interrupted")


def resume(
    journal: Path,
    checkpoint: Path,
    plan: CampaignPlan,
    instrument: Instrument,
    rails: Rails = IDEAL_RAILS,
    on_record: Callable[[Record], None] | None = None,
) -> Campaign:
    """The campaign at ``checkpoint``, if it may be resumed; otherwise
    ``ResumeRefused``, raised before the instrument is asked to do
    anything. The checks, in ``RESUME_CHECKS`` order: the journal's latest
    segment recorded this checkpoint, it is unchanged since, it was written
    for ``plan``, on this bench, and that segment was interrupted."""
    segments = load_journal(journal)
    latest = segments[-1] if segments else None
    if latest is None or latest["checkpoint_digest"] is None or not checkpoint.exists():
        raise ResumeRefused("recorded", "the journal records no checkpoint")
    if file_digest(checkpoint) != latest["checkpoint_digest"]:
        raise ResumeRefused("unchanged", "it changed after the journal recorded it")
    data = json.loads(checkpoint.read_text(encoding="utf-8"))
    if data.get("format") != FORMAT or data.get("plan_digest") != plan.digest():
        raise ResumeRefused("plan", "it was written for another plan")
    if data.get("bench") != bench(instrument):
        raise ResumeRefused("bench", "it was written on another bench")
    if latest["status"] != INTERRUPTED:
        raise ResumeRefused("interrupted", f"its campaign ended {latest['status']}")
    records = [record_from(r) for r in data["records"]]
    return Campaign(plan, instrument, rails, checkpoint, records, on_record)
