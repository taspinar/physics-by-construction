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
measurements), which change no rule. The outcome code's identity is pinned
for the follow-up (``outcome-code.toml``, ``CodePin``): when the code that
evaluates a session is not the pinned code, or the pin is later than M1, the
change is a deviation and the outcomes are exploratory (the registration's
"Withheld part"). Without a session every outcome is
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

from pbc.products.research_workspace import coil, graph, registration

SESSION = "session.toml"
READINGS = "readings.toml"
CODE = "outcome-code.toml"
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
    # Why the outcomes are exploratory (the outcome code is not the pinned
    # code); empty when they are confirmatory.
    exploratory: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CodePin:
    """The outcome code's identity fixed for the follow-up before M1: the
    digest of ``graph.outcome_code_digest``, the digest of each of its files,
    and the time it was pinned (ISO 8601 with its offset)."""

    digest: str
    time: str
    files: dict


def load_pin(path: Path) -> CodePin:
    """The pin in ``path``; a malformed pin is refused."""
    path = Path(path)
    problems: list[str] = []
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise SessionRefused(f"{path.name}: {error}") from error
    digest = data.get("digest")
    if not isinstance(digest, str) or len(digest) != 64:
        problems.append(f"{path.name} digest: {digest!r} is not a sha256")
    _time(data.get("time"), f"{path.name} time", problems)
    files = _table(data.get("files"), f"{path.name} files", problems)
    if not files:
        problems.append(f"{path.name}: no [files]")
    if problems:
        raise SessionRefused("; ".join(problems))
    return CodePin(digest, data["time"], dict(files))


def code_deviations(
    session: Session, pin: CodePin, digest: str, files: dict
) -> list[str]:
    """The outcome code against its pin: a code other than the pinned one
    (named by file), and a pin later than the start of M1, are each a
    deviation that makes the outcomes exploratory."""
    found = []
    if digest != pin.digest:
        changed = sorted(
            name
            for name in pin.files.keys() | files.keys()
            if pin.files.get(name) != files.get(name)
        )
        found.append(
            f"the outcome code {digest[:16]} is not the code pinned for the"
            f" follow-up ({pin.digest[:16]}, {pin.time}; changed:"
            f" {', '.join(changed) or 'not named by file'}): its outcomes are"
            " exploratory"
        )
    starts = [
        datetime.fromisoformat(s.started)
        for s in session.sweeps
        if s.measurement == "M1" and s.started
    ]
    if starts and datetime.fromisoformat(pin.time) > min(starts):
        found.append(
            f"the outcome code was pinned at {pin.time}, after M1 started at"
            f" {min(starts).isoformat()}: the code may have changed after M1,"
            " and its outcomes are exploratory"
        )
    return found


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
        if number is not None and number != int(number):
            problems.append(f"{where} reading: {number:g} is not a whole number")
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


def _table(value, where: str, problems: list[str]) -> dict:
    """``value`` when it is a table; otherwise the problem is named and an
    empty table stands in, so that every other problem is named too."""
    if value is None:
        return {}
    if not isinstance(value, dict):
        problems.append(f"{where}: {value!r} is not a table")
        return {}
    return value


def _integer(value, where: str, problems: list[str]) -> int | None:
    """A whole number written as one (``2``, not ``"two"`` or ``2.5``)."""
    if isinstance(value, bool) or not isinstance(value, int):
        problems.append(f"{where}: {value!r} is not a whole number")
        return None
    return value


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
        run = None
    if not isinstance(run, dict):
        problems.append(f"{where}: {path.name} is not a run record of the physics lab")
        return "", {}
    started = run.get("started", "")
    _time(started, f"{where} started", problems)
    if outcome == FAILED:
        return started, run
    configuration = _table(run.get("configuration"), f"{where} configuration", problems)
    for key, expected in INPUT.items():
        if configuration.get(key) != expected:
            problems.append(
                f"{where}: {key} is {configuration.get(key)!r}, the registered input"
                f" has {expected!r}"
            )
    if live:
        if run.get("mode") != "live":
            problems.append(f"{where}: mode {run.get('mode')!r}, not live")
        device = _table(run.get("device"), f"{where} device", problems)
        calibration = str(device.get("calibration", ""))
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
    controls, whose run records carry no device and no conditions.

    A failed attempt may have no export (a run that stopped before the
    physics lab wrote one): its ``directory`` is empty and its reason says
    why; it has no time and decides nothing. A valid attempt always has its
    export, and a failed one that names a directory must have it."""
    directory = Path(directory)
    problems: list[str] = []
    path = directory / SESSION
    if not path.is_file():
        raise SessionRefused(f"{SESSION}: missing")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise SessionRefused(f"{SESSION}: {error}") from error
    session = _table(data.get("session"), f"{SESSION} session", problems)
    room = _table(data.get("room"), f"{SESSION} room", problems)
    _time(session.get("plugged_in"), f"{SESSION} session.plugged_in", problems)
    temperature = _number(
        room.get("temperature_c"), f"{SESSION} room.temperature_c", problems
    )
    _time(room.get("time"), f"{SESSION} room.time", problems)
    instrument = room.get("instrument", "")
    if not isinstance(instrument, str) or not instrument.strip():
        problems.append(f"{SESSION} room.instrument: not named")
    entries = data.get("sweep") or []
    if not isinstance(entries, list):
        problems.append(f"{SESSION} sweep: {entries!r} is not a list of [[sweep]]")
        entries = []
    sweeps = []
    for number, entry in enumerate(entries, start=1):
        where = f"{SESSION} sweep {number}"
        if not isinstance(entry, dict):
            problems.append(f"{where}: {entry!r} is not a [[sweep]] table")
            continue
        measurement = entry.get("measurement")
        if not isinstance(measurement, str) or measurement not in SWEEPS:
            problems.append(f"{where}: unknown measurement {measurement!r}")
            continue
        attempt = _integer(entry.get("attempt"), f"{where} attempt", problems)
        outcome = entry.get("outcome")
        if not isinstance(outcome, str) or outcome not in (VALID, FAILED):
            problems.append(f"{where}: outcome {outcome!r}, not valid or failed")
            continue
        reason = entry.get("reason", "")
        if not isinstance(reason, str):
            problems.append(f"{where} reason: {reason!r} is not text")
            reason = ""
        if outcome == FAILED and not reason.strip():
            problems.append(f"{where}: a failed run needs its reason")
        name = entry.get("directory", "")
        if not isinstance(name, str):
            problems.append(f"{where} directory: {name!r} is not a folder name")
            continue
        if outcome == FAILED and not name:
            started, run = "", {}
        elif not name or not (directory / name).is_dir():
            problems.append(f"{where}: no export directory {name!r}")
            continue
        else:
            started, run = _sweep_record(
                directory / name, f"{where} ({measurement})", outcome, live, problems
            )
        if attempt is None:
            continue
        sweeps.append(Sweep(measurement, attempt, name, outcome, reason, started, run))
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
    """Every measurement time of M0 to M5: (what, time). A failed attempt
    without an export has no time."""
    out = [
        (f"{s.measurement} attempt {s.attempt}", s.started)
        for s in session.sweeps
        if s.started
    ]
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
        (s for s in session.sweeps if s.measurement == "M0" and s.started), None
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
            if s.measurement == measurement and s.started
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
        if s.measurement == "M5" and s.started
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
    code: CodePin | None = None,
) -> Result:
    """The follow-up's outcomes from the session in ``directory`` (None: no
    session, every outcome ``not evaluated``). A malformed session or one
    measured before the freeze is refused (``SessionRefused``). With
    ``code``, the outcome code is compared with its pin (``code_deviations``);
    the simulated controls pass none."""
    if directory is None or not Path(directory).exists():
        return Result(
            NOT_EVALUATED,
            reasons=["no bench session is recorded: M0 to M5 are not made"],
        )
    session = load(directory, live=live)
    admit(session, freeze)
    result = Result(COMPUTED, records=records_of(session))
    result.deviations = deviations(session)
    if code is not None:
        result.exploratory = code_deviations(
            session, code, graph.outcome_code_digest(), graph.outcome_file_digests()
        )
        result.deviations += result.exploratory
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
