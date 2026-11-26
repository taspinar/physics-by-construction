"""The positive controls of the coil-loss registration (F155 part 2):
simulated sessions under each explanation, and constructed values at every
threshold of the rules.

**Simulated sessions.** Each control writes a whole session directory as the
owner would (``session.toml``, ``readings.toml``, and the export of every sweep
of M0 to M3 and M5 with ``raw.csv`` and ``run.json``) and evaluates it through
``followup.evaluate``, the path the owner's data will take. The traces are
the steady state of the series circuit W1 -> R_s -> coil (L with a loss
R_L(f)) -> node A -> C -> ground, computed in closed form at the 13 coarse
frequencies with 8 periods of 64 samples each (the registered input), channel
2 given a relative gain and a delay (the channels' mismatch), and white noise
on each channel at the level the pilot's own phasor fits leave (estimated
from ``ad3-rlc-pilot``, never from the numbers the registration quotes from
F145's campaigns). Every random draw has its seed. The physics lab's
simulated bench is not used: it integrates a circuit with a constant
resistance and probes node A only, and ``ImperfectChannels`` has no delay;
the closed form gives the R-L node and the same-node sweeps and a loss that
depends on the frequency (recorded in the plan's Discoveries).

The explanations and what each control expects:

- ``DC``: a constant loss equal to the coil's DC resistance; G1 ``accounted``.
- ``AC`` (and ``CIRCUIT``): the coil's DC resistance plus a loss that grows
  as the square root of the frequency (the form of the skin effect), ideal
  channels; G1 ``short`` and G2 ``remains``.
- ``AC-steep``: the coil's DC resistance multiplied by sqrt(f / f_c) above a
  corner of 4.5 kHz: the loss differs so much over the three frequencies of
  R_L0 that u exceeds 5 ohm, and G1 is ``inconclusive`` (its undecidable
  case on simulated data); G2 ``remains``.
- ``MISMATCH``: a constant loss, channel 2 with a gain error and a delay;
  G2 ``artefact``.
- ``BOTH``: the growing loss and the mismatch; G2 ``mixed``.
- ``pilot-parts``: the pilot's own measured L, C, and R_L(f), ideal channels;
  the precondition met, G1 for the pilot equal to G1.
- ``other-parts``: an inductor 5 % larger than the pilot's; the precondition
  not met, the conclusions scoped, G1 for the pilot ``not evaluated``, G2
  carried over.

**Boundary cases.** Values just below, at, and just above every threshold,
with the outcome the registration's text gives at that value written out by
hand in ``BOUNDARY_CASES`` (not computed by the rule they test), and the
meter model on constructed readings.
"""

import csv
import json
import math
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from pbc.products.research_workspace import coil, followup, registration

SEEDS = tuple(range(5))
# After the freeze: the simulated sessions' times.
SESSION_DAY = "2026-12-01"
# The channels' mismatch of the controls: a gain error of 0.5 % and a delay
# of 50 ns (1.8 degrees at 100 kHz).
MISMATCH_GAIN = 1.005
MISMATCH_DELAY_S = 50e-9
# The coil of the AC explanation: its DC resistance, and the loss added at
# 43.0 kHz by a part that grows as sqrt(f); the steep variant's corner above
# which the whole loss grows as sqrt(f).
AC_DC_OHM = 20.0
AC_ADDED_OHM = 43.0
AC_REFERENCE_HZ = 43003.6
AC_CORNER_HZ = 4500.0
DC_LOSS_OHM = 63.0
OTHER_PARTS_FACTOR = 1.05


@dataclass(frozen=True)
class Circuit:
    resistance_ohm: float
    inductance_h: float
    capacitance_f: float
    loss: Callable[[float], float]  # R_L(f), ohm
    dc_ohm: float  # the coil's DC resistance


@dataclass(frozen=True)
class Channels:
    gain: float = 1.0
    delay_s: float = 0.0


def noise_levels() -> tuple[float, float]:
    """The noise of channel 1 and channel 2 that the pilot's phasor fits
    leave, ``return`` (V, one standard deviation each): the median over the
    points of the R-L node sweep of the residual scatter of each fit."""
    from pbc.data import SAMPLES_DIR
    from pbc.data.reference.ad3_rlc_pilot import read_traces

    traces = read_traces(SAMPLES_DIR / "ad3-rlc-pilot" / "rl-node" / "raw.csv")
    levels = {"source": [], "response": []}
    for trace in traces:
        omega = 2.0 * math.pi * trace.frequency_hz
        design = np.column_stack(
            [np.cos(omega * trace.t), np.sin(omega * trace.t), np.ones(trace.t.size)]
        )
        for name in levels:
            signal = getattr(trace, name)
            coefficients, *_ = np.linalg.lstsq(design, signal, rcond=None)
            levels[name].append(float(np.std(signal - design @ coefficients)))
    return float(np.median(levels["source"])), float(np.median(levels["response"]))


def _probe(circuit: Circuit, f: float, node: str) -> complex:
    """The complex amplitude at ``node`` for 1 V at W1."""
    w = 2.0 * math.pi * f
    z_l = circuit.loss(f) + 1j * w * circuit.inductance_h
    z_c = 1.0 / (1j * w * circuit.capacitance_f)
    current = 1.0 / (circuit.resistance_ohm + z_l + z_c)
    return {"W1": 1.0 + 0j, "A": current * z_c, "RL": current * (z_l + z_c)}[node]


def write_sweep(
    directory: Path,
    circuit: Circuit,
    node: str,
    channels: Channels,
    noise: tuple[float, float],
    seed: int,
    started: str,
) -> None:
    """A simulated export of one sweep: ``raw.csv`` in the physics lab's
    columns and a ``run.json`` with the registered input."""
    directory.mkdir(parents=True)
    rng = np.random.default_rng(seed)
    with (directory / "raw.csv").open("w", encoding="utf-8", newline="") as handle:
        out = csv.writer(handle)
        out.writerow(coil.ad3_rlc_pilot.COLUMNS)
        for point, f in enumerate(coil.coarse_frequencies(), start=1):
            w = 2.0 * math.pi * f
            samples = coil.PERIODS * coil.SAMPLES_PER_PERIOD + 1
            t = np.arange(samples) / (f * coil.SAMPLES_PER_PERIOD)
            v = _probe(circuit, f, node)
            source = coil.AMPLITUDE_V * np.cos(w * t) + rng.normal(0, noise[0], samples)
            response = channels.gain * coil.AMPLITUDE_V * abs(v) * np.cos(
                w * (t - channels.delay_s) + np.angle(v)
            ) + rng.normal(0, noise[1], samples)
            for k in range(samples):
                out.writerow(
                    [
                        point,
                        repr(float(f)),
                        coil.AMPLITUDE_V,
                        repr(float(t[k])),
                        repr(float(source[k])),
                        repr(float(response[k])),
                    ]
                )
    record = {
        "run": {
            "mode": "simulated",
            "started": started,
            "configuration": dict(followup.INPUT),
            "label": "simulated control of the coil-loss registration",
        }
    }
    (directory / "run.json").write_text(json.dumps(record, indent=1), encoding="utf-8")


def readings_rows(circuit: Circuit, seed: int) -> list[list[str]]:
    """Constructed meter readings: leads of 0.2 ohm, a breadboard contact of
    0.1 ohm per part, a spread of one digit, the values on the 200 ohm
    range, and the readings' times in the registered order."""
    rng = np.random.default_rng([seed, 4])
    leads = 0.2
    truths = {
        coil.ZERO_BEFORE: leads,
        coil.DC_BB: circuit.dc_ohm + leads + 0.1,
        coil.DC_OUT: circuit.dc_ohm + leads,
        coil.RS_BB: circuit.resistance_ohm + leads + 0.1,
        coil.ZERO_AFTER: leads,
    }
    rows, minute = [], 0
    for quantity, truth in truths.items():
        for number in range(1, coil.READINGS_PER_QUANTITY + 1):
            minute += 1
            value = round(truth + rng.integers(-1, 2) * 0.1, 1)
            rows.append(
                [
                    quantity,
                    str(number),
                    coil.METER,
                    "200",
                    "0.1",
                    "0.8",
                    "3",
                    f"{value:.1f}",
                    f"{SESSION_DAY}T15:{minute:02d}:00+01:00",
                ]
            )
    return rows


def readings_toml(rows: list[list[str]]) -> str:
    """Readings in the template's TOML form, one ``[[reading]]`` per row."""
    text = []
    for row in rows:
        cell = dict(zip(followup.COLUMNS, row, strict=True))
        text.append("[[reading]]")
        for key, value in cell.items():
            if key in ("quantity", "meter", "time"):
                text.append(f'{key} = "{value}"')
            else:
                text.append(f"{key} = {value}")
    return "\n".join(text) + "\n"


def write_session(
    directory: Path,
    circuit: Circuit,
    channels: Channels,
    seed: int,
    noise: tuple[float, float] | None = None,
    *,
    times: dict[str, str] | None = None,
) -> Path:
    """A whole simulated session as the owner fills it in."""
    noise = noise or noise_levels()
    starts = {
        "M0": f"{SESSION_DAY}T14:00:00+01:00",
        "M1": f"{SESSION_DAY}T14:05:00+01:00",
        "M2": f"{SESSION_DAY}T14:10:00+01:00",
        "M3": f"{SESSION_DAY}T14:15:00+01:00",
        "M5": f"{SESSION_DAY}T16:00:00+01:00",
        **(times or {}),
    }
    nodes = {"M0": "A", "M1": "A", "M2": "RL", "M3": "W1", "M5": "RL"}
    directory.mkdir(parents=True)
    lines = [
        "[session]",
        f'plugged_in = "{SESSION_DAY}T13:00:00+01:00"',
        "[room]",
        "temperature_c = 20.0",
        f'time = "{SESSION_DAY}T12:58:00+01:00"',
        'instrument = "simulated"',
    ]
    for offset, (measurement, node) in enumerate(nodes.items()):
        write_sweep(
            directory / measurement,
            circuit,
            node,
            channels,
            noise,
            seed * 100 + offset,
            starts[measurement],
        )
        lines += [
            "[[sweep]]",
            f'measurement = "{measurement}"',
            "attempt = 1",
            f'directory = "{measurement}"',
            'outcome = "valid"',
        ]
    (directory / followup.SESSION).write_text("\n".join(lines) + "\n", encoding="utf-8")
    (directory / followup.READINGS).write_text(
        readings_toml(readings_rows(circuit, seed)), encoding="utf-8"
    )
    return directory


def pilot_circuit() -> Circuit:
    """The pilot's own parts as measured apart (L, C, and R_L(f) read with
    the nominal 100 ohm, interpolated in log frequency), the coil's DC
    resistance taken as the AC explanation's."""
    analysis = coil.pilot_analysis()
    f = np.log(np.asarray(analysis["frequency_hz"]))
    loss = np.asarray(analysis["R_L"])
    return Circuit(
        coil.RESISTOR_NOMINAL_OHM,
        analysis["L_H"],
        analysis["C_F"],
        lambda x: float(np.interp(math.log(x), f, loss)),
        AC_DC_OHM,
    )


def circuits() -> dict[str, tuple[Circuit, Channels]]:
    pilot = pilot_circuit()
    growing = lambda f: AC_DC_OHM + AC_ADDED_OHM * math.sqrt(f / AC_REFERENCE_HZ)  # noqa: E731
    steep = lambda f: AC_DC_OHM * math.sqrt(max(f, AC_CORNER_HZ) / AC_CORNER_HZ)  # noqa: E731
    constant = lambda f: DC_LOSS_OHM  # noqa: E731
    mismatch = Channels(MISMATCH_GAIN, MISMATCH_DELAY_S)
    ind, cap = pilot.inductance_h, pilot.capacitance_f
    r = coil.RESISTOR_NOMINAL_OHM
    return {
        "DC": (Circuit(r, ind, cap, constant, DC_LOSS_OHM), Channels()),
        "AC": (Circuit(r, ind, cap, growing, AC_DC_OHM), Channels()),
        "AC-steep": (Circuit(r, ind, cap, steep, AC_DC_OHM), Channels()),
        "MISMATCH": (Circuit(r, ind, cap, constant, DC_LOSS_OHM), mismatch),
        "BOTH": (Circuit(r, ind, cap, growing, AC_DC_OHM), mismatch),
        "pilot-parts": (pilot, Channels()),
        "other-parts": (
            Circuit(r, ind * OTHER_PARTS_FACTOR, cap, pilot.loss, AC_DC_OHM),
            Channels(),
        ),
    }


# What each control expects, from the explanation it simulates.
EXPECTED = {
    "DC": {"g1": coil.ACCOUNTED},
    "AC": {"g1": coil.SHORT, "g2": coil.REMAINS},
    "AC-steep": {"g1": coil.INCONCLUSIVE, "g2": coil.REMAINS},
    "MISMATCH": {"g2": coil.ARTEFACT},
    "BOTH": {"g2": coil.MIXED},
    "pilot-parts": {"precondition": True, "g1_pilot": "=g1"},
    "other-parts": {
        "precondition": False,
        "g1_pilot": coil.NOT_EVALUATED,
        "g2": "evaluated",
    },
}

FROZEN_FOR_CONTROLS = registration.Freeze(
    "the controls' own freeze", "control", "2026-11-26T15:43:26+00:00"
)


def _meets(outcome: coil.Outcome, expected: dict) -> list[str]:
    misses = []
    for key, want in expected.items():
        got = getattr(outcome, key)
        if want == "=g1":
            want = outcome.g1
        if want == "evaluated":
            if got == coil.NOT_EVALUATED:
                misses.append(f"{key} is not evaluated")
            continue
        if got != want:
            misses.append(f"{key} is {got!r}, expected {want!r}")
    return misses


def run_controls(seeds=SEEDS, root: Path | None = None) -> dict:
    """Every simulated control over ``seeds``: per control and seed the
    outcomes, the values, and what missed; ``passed`` when every seed of
    every control gives the expected outcomes."""
    noise = noise_levels()
    owned = root is None
    root = Path(tempfile.mkdtemp(prefix="coil-controls-")) if owned else Path(root)
    pilot = coil.pilot_response()
    results: dict[str, list[dict]] = {}
    try:
        for name, (circuit, channels) in circuits().items():
            results[name] = []
            for seed in seeds:
                directory = write_session(
                    root / f"{name}-{seed}", circuit, channels, seed, noise
                )
                result = followup.evaluate(
                    directory, FROZEN_FOR_CONTROLS, live=False, pilot=pilot
                )
                outcome = result.outcome
                results[name].append(
                    {
                        "seed": seed,
                        "g1": outcome.g1,
                        "g2": outcome.g2,
                        "g1_pilot": outcome.g1_pilot,
                        "precondition": outcome.precondition,
                        "values": {
                            k: outcome.values[k]
                            for k in (
                                "D",
                                "u_G1",
                                "Rise",
                                "u_hi",
                                "P0_deg",
                                "P1_deg",
                                "max_abs_dphi_deg",
                                "max_abs_dg",
                            )
                        },
                        "misses": _meets(outcome, EXPECTED[name]),
                    }
                )
    finally:
        if owned:
            shutil.rmtree(root, ignore_errors=True)
    resolution = {
        "max_abs_dphi_deg": max(
            r["values"]["max_abs_dphi_deg"]
            for name in ("DC", "AC", "pilot-parts")
            for r in results[name]
        ),
        "max_abs_dg": max(
            r["values"]["max_abs_dg"]
            for name in ("DC", "AC", "pilot-parts")
            for r in results[name]
        ),
    }
    return {
        "seeds": list(seeds),
        "noise_v": list(noise),
        "results": results,
        "resolution": resolution,
        "passed": all(not r["misses"] for rows in results.values() for r in rows),
    }


# --- the boundary cases ------------------------------------------------------

# (rule, inputs, the outcome the registration's text gives), written by hand.
# G1 inputs: (D, u). G2 inputs: (max |dphi|, max |dg|, Rise, u_hi, P0, P1).
BOUNDARY_CASES = (
    ("G1", (4.0, 2.0), coil.ACCOUNTED),  # |D| = 2 u: "<=" holds
    ("G1", (-4.0, 2.0), coil.ACCOUNTED),
    ("G1", (4.001, 2.0), coil.INCONCLUSIVE),  # between 2 u and 3 u
    ("G1", (6.0, 2.0), coil.INCONCLUSIVE),  # D = 3 u: ">" fails
    ("G1", (6.001, 2.0), coil.SHORT),
    ("G1", (5.0, 1.0), coil.INCONCLUSIVE),  # D > 3 u but D = 5 ohm
    ("G1", (5.001, 1.0), coil.SHORT),
    ("G1", (-6.0, 2.0), coil.INCONCLUSIVE),  # D = -3 u: "<" fails
    ("G1", (-6.001, 2.0), coil.EXCEEDS),
    ("G1", (0.0, 5.0), coil.ACCOUNTED),  # u = 5 ohm: not "> 5"
    ("G1", (0.0, 5.001), coil.INCONCLUSIVE),  # undecidable first
    ("G1", (100.0, 5.001), coil.INCONCLUSIVE),
    ("G1", (-100.0, 5.001), coil.INCONCLUSIVE),
    ("G2", (0.3, 0.0, 0.0, 1.0, 2.0, 0.0), coil.INCONCLUSIVE),  # not measurable
    ("G2", (0.301, 0.0, 2.0, 1.0, 2.0, 1.0), coil.ARTEFACT),  # Rise = 2 u_hi, P1 = P0/2
    ("G2", (0.301, 0.0, 2.0, 1.0, 2.0, 1.001), coil.INCONCLUSIVE),  # P1 > P0/2
    ("G2", (0.301, 0.0, 2.001, 1.0, 2.0, 0.0), coil.INCONCLUSIVE),  # 2 to 3 u_hi
    ("G2", (0.301, 0.0, 3.0, 1.0, 2.0, 0.0), coil.INCONCLUSIVE),  # Rise = 3 u_hi
    ("G2", (0.301, 0.0, 3.001, 1.0, 2.0, 0.0), coil.MIXED),
    ("G2", (0.0, 0.003, 3.001, 1.0, 2.0, 0.0), coil.REMAINS),  # dg = 0.003
    ("G2", (0.0, 0.003, 3.0, 1.0, 2.0, 0.0), coil.INCONCLUSIVE),
    ("G2", (0.0, 0.003001, 3.001, 1.0, 2.0, 0.0), coil.MIXED),
    ("G2", (0.0, 0.003001, 1.0, 1.0, 2.0, 0.5), coil.ARTEFACT),
    ("G2", (0.3, 0.003, 1.0, 1.0, 2.0, 0.5), coil.INCONCLUSIVE),  # Rise <= 2 u_hi
)


def outcome_of(rule: str, inputs: tuple) -> tuple[str, dict[str, bool]]:
    """The rule's outcome and its predicates for one case."""
    if rule == "G1":
        d, u = inputs
        return coil.rule_g1(d, u), coil.g1_predicates(d, u)
    dphi, dg, rise_ohm, u_hi, p0, p1 = inputs
    measurable = coil.mismatch_measurable(np.array([dphi]), np.array([dg]))
    return (
        coil.rule_g2(measurable, rise_ohm, u_hi, p0, p1),
        coil.g2_predicates(measurable, rise_ohm, u_hi, p0, p1),
    )


def _reading(quantity: str, number: int, value: float, range_ohm: float = 200.0):
    return coil.Reading(
        quantity,
        number,
        coil.METER,
        range_ohm,
        coil.RANGES_OHM[range_ohm],
        coil.P_REGISTERED,
        coil.N_REGISTERED,
        value,
        f"{SESSION_DAY}T15:00:00+01:00",
    )


def meter_cases() -> list[dict]:
    """The meter model on constructed readings: the offset cancels on one
    range and not across two; more readings do not reduce the gain part;
    dz enters as the contact term."""
    zero = [_reading("Z1", k, 0.2) for k in (1, 2, 3)] + [
        _reading("Z2", k, 0.4) for k in (1, 2, 3)
    ]
    same = coil.meter_value(
        zero + [_reading("R_dc_bb", k, 20.3) for k in (1, 2, 3)], "R_dc_bb"
    )
    across = coil.meter_value(
        zero + [_reading("R_dc_bb", k, 20.0, 2000.0) for k in (1, 2, 3)], "R_dc_bb"
    )
    six = coil.meter_value(
        zero + [_reading("R_dc_bb", k, 20.3) for k in range(1, 7)], "R_dc_bb"
    )
    expected_off = math.hypot(3 * 1.0, 3 * 0.1) / math.sqrt(3.0)
    expected_contact = 0.2 / (2.0 * math.sqrt(3.0))
    cases = [
        {
            "case": "the offset cancels on one range",
            "value": same.parts["u_off"],
            "expected": 0.0,
        },
        {
            "case": "the offset does not cancel across two ranges",
            "value": across.parts["u_off"],
            "expected": expected_off,
        },
        {
            "case": "six readings do not reduce the gain part",
            "value": six.parts["u_gain"],
            "expected": same.parts["u_gain"],
        },
        {
            "case": "dz enters as the contact term",
            "value": same.parts["u_contact"],
            "expected": expected_contact,
        },
        {
            "case": "the net value subtracts the zero",
            "value": same.value,
            "expected": 20.3 - 0.3,
        },
    ]
    for case in cases:
        case["passed"] = math.isclose(
            case["value"], case["expected"], rel_tol=1e-9, abs_tol=1e-12
        )
    return cases


def run_boundaries() -> dict:
    rows = []
    for rule, inputs, expected in BOUNDARY_CASES:
        got, predicates = outcome_of(rule, inputs)
        rows.append(
            {
                "rule": rule,
                "inputs": list(inputs),
                "expected": expected,
                "got": got,
                "holding": [k for k, v in predicates.items() if v],
                "passed": got == expected and sum(predicates.values()) <= 1,
            }
        )
    meter = meter_cases()
    return {
        "cases": rows,
        "meter": meter,
        "passed": all(r["passed"] for r in rows) and all(m["passed"] for m in meter),
    }
