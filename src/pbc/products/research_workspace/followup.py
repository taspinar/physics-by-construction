"""The follow-up's inputs: the owner's bench session of the coil-loss
registration, read, checked, admitted, and evaluated (F155 part 2).

A session is a directory the owner fills by hand after the bench session,
from the templates in ``products/research-workspace/examples/coil-loss/``:

    session.toml   the time the AD3 was plugged in, the room temperature with
                   its time and the instrument read, and one ``[[sweep]]`` per
                   attempt of M0, M1, M2, M3, M5 (its export directory, valid or
                   failed with the reason)
    readings.toml  the readings of M4, one [[reading]] per reading
    <directory>/   each sweep's export of the physics lab (raw.csv, run.json)

``load`` refuses a malformed or incomplete session and names every problem.
``admit`` refuses evidence whose measurement time (the run record's start of
every sweep of M0 to M3 and M5, the time of every reading of M4) precedes the
freeze. ``evaluate`` applies the registration (``coil.evaluate``) and reports
the deviations from its procedure (the wait of 45 minutes, the order of the
measurements), which change no rule. Without a session every outcome is
``not evaluated``; after a second failed run of one measurement the session
stops and the follow-up is ``inconclusive`` with its reasons.
"""

import itertools
import json
import math
import tomllib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from pbc.products.research_workspace import coil, registration

SESSION = "session.toml"
READINGS = "readings.toml"
SWEEPS = ("M0", "M1", "M2", "M3", "M5")
REQUIRED_SWEEPS = ("M0", "M1", "M2", "M3")
VALID, FAILED = "valid", "failed"
WAIT = timedelta(minutes=45)
COLUMNS = (
    "quantity",
    "reading",
    "meter",
    "range_ohm",
    "resolution_ohm",
    "p_percent",
    "n_digits",
    "value_ohm",
    "time",
)
# The live input the registration names, as the run record states it.
INPUT = {
    "low_hz": coil.LOW_HZ,
    "high_hz": coil.HIGH_HZ,
    "coarse_points": coil.COARSE_POINTS,
    "amplitude_v": coil.AMPLITUDE_V,
    "periods": coil.PERIODS,
    "samples_per_period": coil.SAMPLES_PER_PERIOD,
}
CONDITIONS = ("conditions_at_start", "conditions_at_end")
RANGES_IN_RECORD = ("5 V range", "50 V range")

NOT_EVALUATED = coil.NOT_EVALUATED
INCONCLUSIVE = coil.INCONCLUSIVE
COMPUTED = "computed"


class SessionRefused(ValueError):
    """A session the workspace does not accept, with every reason."""


@dataclass(frozen=True)
class Sweep:
    measurement: str
    attempt: int
    directory: str
    outcome: str
    reason: str
    started: str
    record: dict


@dataclass(frozen=True)
class Session:
    directory: Path
    plugged_in: str
    room_temperature_c: float
    room_time: str
    room_instrument: str
    sweeps: tuple[Sweep, ...]
    readings: tuple[coil.Reading, ...]

    def used(self, measurement: str) -> Sweep | None:
        """The valid attempt of ``measurement`` (the last one), if any."""
        valid = [
            s
            for s in self.sweeps
            if s.measurement == measurement and s.outcome == VALID
        ]
        return valid[-1] if valid else None


@dataclass
class Result:
    """What the follow-up's evidence gives: ``status`` is ``not evaluated``
    (no session), ``inconclusive`` (stopped), or ``computed``."""

    status: str
    outcome: coil.Outcome = field(default_factory=coil.Outcome)
    reasons: list[str] = field(default_factory=list)
    deviations: list[str] = field(default_factory=list)
    records: dict = field(default_factory=dict)


def _time(text, where: str, problems: list[str]) -> datetime | None:
    if not isinstance(text, str) or not text.strip():
        problems.append(f"{where}: no time")
        return None
    try:
        value = datetime.fromisoformat(text)
    except ValueError:
        problems.append(f"{where}: {text!r} is not an ISO 8601 time")
        return None
    if value.tzinfo is None:
        problems.append(f"{where}: {text!r} has no offset from UTC")
        return None
    return value


def _number(text, where: str, problems: list[str]) -> float | None:
    try:
        value = float(text)
    except TypeError, ValueError:
        problems.append(f"{where}: {text!r} is not a number")
        return None
    if not math.isfinite(value):
        problems.append(f"{where}: {text!r} is not a finite number")
        return None
    return value


def read_readings(path: Path, problems: list[str]) -> list[coil.Reading]:
    """The readings of M4 from the template, each checked against the
    registered meter, its ranges and their resolution, and the registered
    p and n; exactly three readings of each quantity."""
    path = Path(path)
    if not path.is_file():
        problems.append(f"{path.name}: missing")
        return []
    try:
        entries = tomllib.loads(path.read_text(encoding="utf-8")).get("reading")
    except tomllib.TOMLDecodeError as error:
        problems.append(f"{path.name}: {error}")
        return []
    if not isinstance(entries, list) or not entries:
        problems.append(f"{path.name}: no [[reading]]")
        return []
    out = []
    for line, entry in enumerate(entries, start=1):
        where = f"{path.name} reading {line}"
        if not isinstance(entry, dict) or set(entry) != set(COLUMNS):
            keys = set(entry) if isinstance(entry, dict) else set()
            problems.append(
                f"{where}: the fields are not {', '.join(COLUMNS)}"
                f" (missing {sorted(set(COLUMNS) - keys) or 'none'},"
                f" unknown {sorted(keys - set(COLUMNS)) or 'none'})"
            )
            continue
        cell = {k: str(v).strip() for k, v in entry.items()}
        before = len(problems)
        if cell["quantity"] not in coil.QUANTITIES:
            problems.append(f"{where}: unknown quantity {cell['quantity']!r}")
        if cell["meter"] != coil.METER:
            problems.append(
                f"{where}: the meter is {cell['meter']!r}, the registration's is"
                f" {coil.METER}"
            )
        number = _number(cell["reading"], f"{where} reading", problems)
        range_ohm = _number(cell["range_ohm"], f"{where} range_ohm", problems)
        q = _number(cell["resolution_ohm"], f"{where} resolution_ohm", problems)
        p = _number(cell["p_percent"], f"{where} p_percent", problems)
        n = _number(cell["n_digits"], f"{where} n_digits", problems)
        value = _number(cell["value_ohm"], f"{where} value_ohm", problems)
        _time(cell["time"], f"{where} time", problems)
        if range_ohm is not None:
            if range_ohm not in coil.RANGES_OHM:
                problems.append(f"{where}: no registered range {range_ohm:g} ohm")
            elif q is not None and q != coil.RANGES_OHM[range_ohm]:
                problems.append(
                    f"{where}: the resolution on the {range_ohm:g} ohm range is"
                    f" {coil.RANGES_OHM[range_ohm]:g} ohm, not {q:g}"
                )
        if p is not None and p != coil.P_REGISTERED * 100:
            problems.append(
                f"{where}: p is {p:g} %, registered {coil.P_REGISTERED * 100:g} %"
            )
        if n is not None and n != coil.N_REGISTERED:
            problems.append(f"{where}: n is {n:g}, registered {coil.N_REGISTERED}")
        if len(problems) == before:
            out.append(
                coil.Reading(
                    cell["quantity"],
                    int(number),
                    cell["meter"],
                    range_ohm,
                    q,
                    p / 100.0,
                    int(n),
                    value,
                    cell["time"],
                )
            )
    if len(problems) == 0 or out:
        for quantity in coil.QUANTITIES:
            numbers = sorted(r.number for r in out if r.quantity == quantity)
            if numbers != list(range(1, coil.READINGS_PER_QUANTITY + 1)):
                problems.append(
                    f"{path.name}: {quantity} needs the readings 1, 2, 3, has"
                    f" {numbers or 'none'}"
                )
    return out


def _sweep_record(
    directory: Path, where: str, outcome: str, live: bool, problems: list[str]
) -> tuple[str, dict]:
    path = directory / "run.json"
    if not path.is_file():
        problems.append(f"{where}: no run record {path.name} in {directory.name}")
        return "", {}
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        run = record["run"]
    except ValueError, KeyError, TypeError:
        problems.append(f"{where}: {path.name} is not a run record of the physics lab")
        return "", {}
    started = run.get("started", "")
    _time(started, f"{where} started", problems)
    if outcome == FAILED:
        return started, run
    configuration = run.get("configuration") or {}
    for key, expected in INPUT.items():
        if configuration.get(key) != expected:
            problems.append(
                f"{where}: {key} is {configuration.get(key)!r}, the registered input"
                f" has {expected!r}"
            )
    if live:
        if run.get("mode") != "live":
            problems.append(f"{where}: mode {run.get('mode')!r}, not live")
        calibration = (run.get("device") or {}).get("calibration", "")
        for words in RANGES_IN_RECORD:
            if words not in calibration:
                problems.append(f"{where}: the run record does not state the {words}")
        for key in CONDITIONS:
            if not configuration.get(key):
                problems.append(f"{where}: the run record has no {key}")
    if not (directory / "raw.csv").is_file():
        problems.append(f"{where}: no raw.csv in {directory.name}")
    return started, run


def load(directory: Path, *, live: bool = True) -> Session:
    """The session in ``directory``; every problem is named in one refusal.
    ``live`` is False only for the simulated sessions of the positive
    controls, whose run records carry no device and no conditions."""
    directory = Path(directory)
    problems: list[str] = []
    path = directory / SESSION
    if not path.is_file():
        raise SessionRefused(f"{SESSION}: missing")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise SessionRefused(f"{SESSION}: {error}") from error
    session = data.get("session") or {}
    room = data.get("room") or {}
    _time(session.get("plugged_in"), f"{SESSION} session.plugged_in", problems)
    temperature = _number(
        room.get("temperature_c"), f"{SESSION} room.temperature_c", problems
    )
    _time(room.get("time"), f"{SESSION} room.time", problems)
    instrument = room.get("instrument", "")
    if not isinstance(instrument, str) or not instrument.strip():
        problems.append(f"{SESSION} room.instrument: not named")
    sweeps = []
    for number, entry in enumerate(data.get("sweep") or [], start=1):
        where = f"{SESSION} sweep {number}"
        measurement = entry.get("measurement")
        if measurement not in SWEEPS:
            problems.append(f"{where}: unknown measurement {measurement!r}")
            continue
        outcome = entry.get("outcome")
        if outcome not in (VALID, FAILED):
            problems.append(f"{where}: outcome {outcome!r}, not valid or failed")
            continue
        reason = str(entry.get("reason", ""))
        if outcome == FAILED and not reason.strip():
            problems.append(f"{where}: a failed run needs its reason")
        name = str(entry.get("directory", ""))
        if not name or not (directory / name).is_dir():
            problems.append(f"{where}: no export directory {name!r}")
            continue
        started, run = _sweep_record(
            directory / name, f"{where} ({measurement})", outcome, live, problems
        )
        sweeps.append(
            Sweep(
                measurement,
                int(entry.get("attempt", 0)),
                name,
                outcome,
                reason,
                started,
                run,
            )
        )
    for measurement in SWEEPS:
        attempts = [s for s in sweeps if s.measurement == measurement]
        if [s.attempt for s in attempts] != list(range(1, len(attempts) + 1)):
            problems.append(f"{measurement}: the attempts are not numbered 1, 2")
        pattern = tuple(s.outcome for s in attempts)
        allowed = ((VALID,), (FAILED, VALID), (FAILED, FAILED))
        if measurement in REQUIRED_SWEEPS and not attempts:
            problems.append(f"{measurement}: no sweep recorded")
        elif attempts and pattern not in allowed:
            problems.append(
                f"{measurement}: attempts {', '.join(pattern)}; a failed run is"
                " repeated once, and no valid sweep is repeated or exchanged"
            )
    readings = read_readings(directory / READINGS, problems)
    if problems:
        raise SessionRefused("; ".join(problems))
    return Session(
        directory,
        session["plugged_in"],
        temperature,
        room["time"],
        instrument,
        tuple(sweeps),
        tuple(readings),
    )


def measurement_times(session: Session) -> list[tuple[str, str]]:
    """Every measurement time of M0 to M5: (what, time)."""
    out = [(f"{s.measurement} attempt {s.attempt}", s.started) for s in session.sweeps]
    out += [(f"M4 {r.quantity} reading {r.number}", r.time) for r in session.readings]
    return out


def admit(session: Session, freeze: registration.Freeze) -> None:
    """Refuse the session when the time of any sweep of M0 to M3 and M5 (its
    run record's start) or of any reading of M4 precedes the freeze."""
    early = []
    for what, time in measurement_times(session):
        try:
            registration.admit(time, freeze)
        except registration.RegistrationRefused as reason:
            early.append(f"{what}: {reason}")
    if early:
        raise SessionRefused("; ".join(early))


def deviations(session: Session) -> list[str]:
    """The departures from the registered procedure, reported beside the
    outcomes (they change no rule): M0 earlier than 45 minutes after the
    plug-in, and the measurements out of their registered order."""
    found = []
    plugged = datetime.fromisoformat(session.plugged_in)
    first = session.used("M0") or next(
        (s for s in session.sweeps if s.measurement == "M0"), None
    )
    if first is not None:
        start = datetime.fromisoformat(first.started)
        if start < plugged + WAIT:
            minutes = (start - plugged).total_seconds() / 60.0
            found.append(
                f"M0 started {minutes:.0f} minutes after the plug-in, earlier than"
                " the registered 45 minutes"
            )
    order = []
    for measurement in ("M0", "M1", "M2", "M3"):
        order += [
            (measurement, datetime.fromisoformat(s.started))
            for s in session.sweeps
            if s.measurement == measurement
        ]
    readings = {
        q: [datetime.fromisoformat(r.time) for r in session.readings if r.quantity == q]
        for q in coil.QUANTITIES
    }
    for q in (coil.ZERO_BEFORE, coil.DC_BB, coil.DC_OUT, coil.RS_BB, coil.ZERO_AFTER):
        order += [(f"M4 {q}", t) for t in sorted(readings[q])]
    order += [
        ("M5", datetime.fromisoformat(s.started))
        for s in session.sweeps
        if s.measurement == "M5"
    ]
    for (a, ta), (b, tb) in itertools.pairwise(order):
        if tb < ta:
            found.append(f"{b} was measured before {a}, against the registered order")
    if session.used("M5") is None:
        found.append("M5 (the repeat of M2) is missing: no repeatability is reported")
    return found


def records_of(session: Session) -> dict:
    """What the session records and no rule reads: the plug-in, the room
    temperature, and the device's conditions of every sweep."""
    return {
        "plugged_in": session.plugged_in,
        "room": {
            "temperature_c": session.room_temperature_c,
            "time": session.room_time,
            "instrument": session.room_instrument,
        },
        "sweeps": [
            {
                "measurement": s.measurement,
                "attempt": s.attempt,
                "outcome": s.outcome,
                "reason": s.reason,
                "started": s.started,
                **{
                    key: (s.record.get("configuration") or {}).get(key)
                    for key in CONDITIONS
                },
            }
            for s in session.sweeps
        ],
    }


def evaluate(
    directory: Path | None,
    freeze: registration.Freeze,
    *,
    live: bool = True,
    pilot=None,
) -> Result:
    """The follow-up's outcomes from the session in ``directory`` (None: no
    session, every outcome ``not evaluated``). A malformed session or one
    measured before the freeze is refused (``SessionRefused``)."""
    if directory is None or not Path(directory).exists():
        return Result(
            NOT_EVALUATED,
            reasons=["no bench session is recorded: M0 to M5 are not made"],
        )
    session = load(directory, live=live)
    admit(session, freeze)
    result = Result(COMPUTED, records=records_of(session))
    result.deviations = deviations(session)
    stopped = [
        m
        for m in SWEEPS
        if [s.outcome for s in session.sweeps if s.measurement == m] == [FAILED, FAILED]
    ]
    if stopped:
        result.status = INCONCLUSIVE
        result.outcome.g1 = result.outcome.g2 = INCONCLUSIVE
        result.outcome.g1_pilot = NOT_EVALUATED
        for m in stopped:
            reasons = "; ".join(s.reason for s in session.sweeps if s.measurement == m)
            result.reasons.append(
                f"{m} failed twice ({reasons}): the session stops, and the"
                " follow-up is inconclusive"
            )
        return result
    responses = {
        m: coil.at_coarse(coil.read_sweep(directory / session.used(m).directory))
        for m in SWEEPS
        if session.used(m) is not None
    }
    sweeps = coil.Sweeps(
        responses["M0"],
        responses["M1"],
        responses["M2"],
        responses["M3"],
        responses.get("M5"),
    )
    if pilot is None:
        pilot = coil.pilot_response()
    result.outcome = coil.evaluate(sweeps, session.readings, pilot)
    return result
