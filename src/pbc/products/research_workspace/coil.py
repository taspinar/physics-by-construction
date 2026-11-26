"""The original track's analysis: the coil-loss follow-up of ``ad3-rlc-pilot``
(F155 part 2), as the frozen registration states it
(``products/research-workspace/examples/coil-loss/registration.md``).

Every quantity and every rule here is the registration's, in its words:

- the phasors by the least-squares fit of the pilot's dossier (cosine, sine,
  constant over each record), read through ``pbc.data.reference.ad3_rlc_pilot``
  unchanged, at the 13 coarse frequencies of the live input;
- the meter readings of M4: the zero, the change of the contact, and the
  standard uncertainty of a net value with its five parts (``meter_value``);
- ``Z = R_s_bb H / (1 - H)`` with H uncorrected (G1) and ``H / m`` (G2),
  ``R_L0``, ``u_L``, L and C, the parts-apart model, ``P0`` and ``P1``,
  ``Rise`` and ``u_hi``;
- the precondition (identity of the parts), the rules G1 and G2, each with
  its predicates evaluated apart so that a test can see that no two hold
  together, and every other case ``inconclusive``.

The thresholds were chosen after seeing the pilot's data; only the follow-up's
measurements are confirmatory. A change of this module after M1 is a
deviation, and its result exploratory (the registration's "Withheld part"):
``graph.outcome_code_digest`` covers it, and ``followup.code_deviations``
compares it with the identity pinned in ``examples/coil-loss/outcome-code.toml``.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from pbc.data.reference import ad3_rlc_pilot
from pbc.data.reference.ad3_rlc_pilot import Response

# The live input of the registration (products/physics-lab/examples/live-pilot.toml).
LOW_HZ = 5000.0
HIGH_HZ = 200000.0
COARSE_POINTS = 13
AMPLITUDE_V = 1.0
PERIODS = 8
SAMPLES_PER_PERIOD = 64
# R_L0: the mean of R_L at 31.6, 43.0, and 58.5 kHz (coarse points 7 to 9).
LOSS_POINTS = (6, 7, 8)
# Rise = R_L(200 kHz) - R_L(43.0 kHz).
RISE_LOW, RISE_HIGH = 7, 12
# A realised frequency is the coarse one within this relative distance.
FREQUENCY_MATCH = 1e-3

# The meter of M4 (the registration, "Meter readings").
METER = "Mastech MAS830BC"
RANGES_OHM = {200.0: 0.1, 2000.0: 1.0}  # range: resolution q
P_REGISTERED = 0.008  # 0.8 % of reading
N_REGISTERED = 3  # digits
P_SENSITIVITY = 0.012  # the third party's 1.2 %, decides no outcome
ZERO_BEFORE, ZERO_AFTER = "Z1", "Z2"
DC_BB, DC_OUT, RS_BB = "R_dc_bb", "R_dc", "R_s_bb"
QUANTITIES = (ZERO_BEFORE, DC_BB, DC_OUT, RS_BB, ZERO_AFTER)
READINGS_PER_QUANTITY = 3
# The meter check of R_s_bb (reported, decides no outcome).
RESISTOR_NOMINAL_OHM = 100.0
RESISTOR_TOLERANCE = 0.01

# The precondition: L and C within 2 %, R_L0 within 3 u_L of pilot run 3.
IDENTITY_RELATIVE = 0.02
IDENTITY_FACTOR = 3.0

# G1.
UNDECIDABLE_U_OHM = 5.0
ACCOUNTED_FACTOR = 2.0
SHORT_FACTOR = 3.0
SHORT_FLOOR_OHM = 5.0
EXCEEDS_FACTOR = 3.0
# G2.
MISMATCH_PHASE_DEG = 0.3
MISMATCH_GAIN = 0.003
ARTEFACT_FACTOR = 2.0
REMAINS_FACTOR = 3.0
P_RATIO = 0.5

INCONCLUSIVE = "inconclusive"
NOT_EVALUATED = "not evaluated"
ACCOUNTED, SHORT, EXCEEDS = "accounted", "short", "exceeds"
ARTEFACT, REMAINS, MIXED = "artefact", "remains", "mixed"
G1_OUTCOMES = (ACCOUNTED, SHORT, EXCEEDS, INCONCLUSIVE)
G2_OUTCOMES = (ARTEFACT, REMAINS, MIXED, INCONCLUSIVE)
# The explanations and the outcome each predicts; "exceeds" is predicted by
# neither explanation of G1 and opens a new finding.
EXPLANATIONS = {
    "DC": ("G1", ACCOUNTED),
    "AC": ("G1", SHORT),
    "MISMATCH": ("G2", ARTEFACT),
    "CIRCUIT": ("G2", REMAINS),
    "BOTH": ("G2", MIXED),
}


class AnalysisRefused(ValueError):
    """Data the registered analysis cannot be applied to, with the reason."""


def coarse_frequencies() -> np.ndarray:
    """The 13 log-spaced coarse frequencies of the live input, ``return`` (Hz)."""
    k = np.arange(COARSE_POINTS)
    return LOW_HZ * (HIGH_HZ / LOW_HZ) ** (k / (COARSE_POINTS - 1))


def read_sweep(directory: Path) -> Response:
    """The response of a sweep exported by the physics lab (``raw.csv`` in
    ``directory``), by the pilot's reader, sorted by frequency."""
    directory = Path(directory)
    return ad3_rlc_pilot.response(directory.parent, directory.name)


def at_coarse(response: Response) -> Response:
    """The points of ``response`` at the 13 coarse frequencies; a sweep
    without one of them is refused (the refinement points are dropped)."""
    keep = []
    for f in coarse_frequencies():
        distance = np.abs(response.frequency_hz / f - 1.0)
        nearest = int(np.argmin(distance))
        if distance[nearest] > FREQUENCY_MATCH:
            raise AnalysisRefused(f"the sweep has no point at {f:.1f} Hz")
        keep.append(nearest)
    return Response(
        response.frequency_hz[keep],
        response.ratio[keep],
        response.gain_sigma[keep],
        response.phase_sigma_deg[keep],
    )


def divided(response: Response, m: np.ndarray) -> Response:
    """``H / m``: the response corrected by the channels' relative response
    ``m`` (M3); the relative uncertainties stay those of the sweep."""
    ratio = response.ratio / m
    return Response(
        response.frequency_hz,
        ratio,
        response.gain_sigma / np.abs(response.ratio) * np.abs(ratio),
        response.phase_sigma_deg,
    )


def wrap_deg(angle: np.ndarray) -> np.ndarray:
    """``angle`` (degrees) wrapped into (-180, 180], ``return`` (degrees)."""
    out = np.mod(np.asarray(angle, dtype=float) + 180.0, 360.0) - 180.0
    return np.where(out == -180.0, 180.0, out)


# --- the meter readings of M4 ---------------------------------------------


@dataclass(frozen=True)
class Reading:
    """One reading of M4, as the template records it."""

    quantity: str
    number: int
    meter: str
    range_ohm: float
    resolution_ohm: float
    p: float  # fraction of reading
    n: int  # digits
    value_ohm: float
    time: str  # ISO 8601 with its offset


@dataclass(frozen=True)
class MeterValue:
    """A net meter value X = mean(x) - z, ``value`` (ohm), with its
    standard uncertainty ``u`` (ohm), ``u_ng`` (ohm) without the gain part,
    and the ``parts`` (ohm) it combines."""

    quantity: str
    value: float
    u: float
    u_ng: float  # without the gain part
    parts: Mapping[str, float]
    range_ohm: float


@dataclass(frozen=True)
class Zero:
    """The zero of the meter: z, the mean of the six readings of Z1 and Z2,
    and dz = mean(Z2) - mean(Z1), the change of the contact during M4."""

    z: float
    dz: float
    range_ohm: float
    resolution_ohm: float


def _of(readings: Sequence[Reading], quantity: str) -> list[Reading]:
    return [r for r in readings if r.quantity == quantity]


def zero(readings: Sequence[Reading]) -> Zero:
    before, after = _of(readings, ZERO_BEFORE), _of(readings, ZERO_AFTER)
    if not before or not after:
        raise AnalysisRefused("the zero needs the readings of Z1 and Z2")
    both = before + after
    ranges = {r.range_ohm for r in both}
    if len(ranges) != 1:
        raise AnalysisRefused("the readings of the zero are on more than one range")
    (range_ohm,) = ranges
    return Zero(
        float(np.mean([r.value_ohm for r in both])),
        float(
            np.mean([r.value_ohm for r in after])
            - np.mean([r.value_ohm for r in before])
        ),
        range_ohm,
        both[0].resolution_ohm,
    )


def meter_value(
    readings: Sequence[Reading], quantity: str, p: float | None = None
) -> MeterValue:
    """The net value of ``quantity`` and its standard uncertainty by the
    registration's model: u_repeat, u_res, u_contact, u_off (zero when the
    zero was read on the same range), and u_gain = p |X| / sqrt(3), which is
    a property of the meter and not reduced by more readings. ``p`` replaces
    the registered percentage for the sensitivity (1.2 %)."""
    own = _of(readings, quantity)
    if len(own) < 2:
        raise AnalysisRefused(f"{quantity} needs at least two readings")
    ranges = {r.range_ohm for r in own}
    if len(ranges) != 1:
        raise AnalysisRefused(f"the readings of {quantity} are on more than one range")
    zero_ = zero(readings)
    x = np.array([r.value_ohm for r in own])
    value = float(x.mean() - zero_.z)
    q = own[0].resolution_ohm
    n = own[0].n
    p = own[0].p if p is None else p
    u_repeat = float(x.std(ddof=1) / math.sqrt(x.size))
    u_res = q / math.sqrt(6.0)
    u_contact = abs(zero_.dz) / (2.0 * math.sqrt(3.0))
    if own[0].range_ohm == zero_.range_ohm:
        u_off = 0.0
    else:
        u_off = math.hypot(n * q, n * zero_.resolution_ohm) / math.sqrt(3.0)
    u_gain = p * abs(value) / math.sqrt(3.0)
    u_ng = math.sqrt(u_repeat**2 + u_res**2 + u_contact**2 + u_off**2)
    return MeterValue(
        quantity,
        value,
        math.hypot(u_ng, u_gain),
        u_ng,
        {
            "u_repeat": u_repeat,
            "u_res": u_res,
            "u_contact": u_contact,
            "u_off": u_off,
            "u_gain": u_gain,
        },
        own[0].range_ohm,
    )


def resistor_band(
    p: float = P_REGISTERED, n: int = N_REGISTERED
) -> tuple[float, float]:
    """The band in which R_s_bb should read: 100 ohm +- 1 % widened by the
    meter's limit a = p |reading| + n q on the 200 ohm range."""
    q = RANGES_OHM[200.0]
    low = RESISTOR_NOMINAL_OHM * (1.0 - RESISTOR_TOLERANCE)
    high = RESISTOR_NOMINAL_OHM * (1.0 + RESISTOR_TOLERANCE)
    return low - (p * low + n * q), high + (p * high + n * q)


# --- the impedance of the R-L node sweep ------------------------------------


def impedance(response: Response, resistance: float) -> np.ndarray:
    """The impedance Z = R H / (1 - H) of the R-L node, ``return``
    (ohm, complex), with the series resistance ``resistance`` (ohm)."""
    h = response.ratio
    return resistance * h / (1.0 - h)


@dataclass(frozen=True)
class Parts:
    """L and C from the reactance, ``inductance_h`` (H) and
    ``capacitance_f`` (F); R_L at the coarse frequencies, ``loss_ohm`` (ohm);
    ``r_l0`` (ohm) and ``u_l`` (ohm)."""

    inductance_h: float
    capacitance_f: float
    loss_ohm: tuple[float, ...]  # R_L at the 13 coarse frequencies
    r_l0: float
    u_l: float


def reactance_fit(frequency_hz: np.ndarray, z: np.ndarray) -> tuple[float, float]:
    """L and C from the least-squares fit of Im Z = 2 pi f L - 1 / (2 pi f C)."""
    omega = 2.0 * math.pi * np.asarray(frequency_hz, dtype=float)
    design = np.column_stack([omega, -1.0 / omega])
    (inductance, elastance), *_ = np.linalg.lstsq(design, z.imag, rcond=None)
    return float(inductance), float(1.0 / elastance)


def parts(response: Response, resistance: float, u_rs_ng: float) -> Parts:
    """The parts measured apart from a coarse R-L node response with the
    series resistance ``resistance`` and its non-gain uncertainty."""
    z = impedance(response, resistance)
    inductance, capacitance = reactance_fit(response.frequency_hz, z)
    near = z.real[list(LOSS_POINTS)]
    r_l0 = float(near.mean())
    u_l = math.hypot(
        float(near.std(ddof=1) / math.sqrt(near.size)), r_l0 * u_rs_ng / resistance
    )
    return Parts(inductance, capacitance, tuple(float(v) for v in z.real), r_l0, u_l)


def model_ratio(frequency_hz: np.ndarray, resistance: float, p: Parts) -> np.ndarray:
    """The parts-apart model V_C / V_S = 1 / (1 - w^2 L C + j w (R_s_bb +
    R_L0) C)."""
    return ad3_rlc_pilot.capacitor_ratio(
        frequency_hz, resistance + p.r_l0, p.inductance_h, p.capacitance_f
    )


def phase_rms(capacitor: Response, resistance: float, p: Parts) -> float:
    """P: the rms over the coarse frequencies of the model's phase minus the
    phase of the capacitor sweep, ``return`` (degrees), with the series
    resistance ``resistance`` (ohm)."""
    model = model_ratio(capacitor.frequency_hz, resistance, p)
    difference = wrap_deg(np.degrees(np.angle(model) - np.angle(capacitor.ratio)))
    return float(np.sqrt(np.mean(difference**2)))


def _loss_at(h2: complex, m: complex, resistance: float) -> float:
    h = h2 / m
    return float((resistance * h / (1.0 - h)).real)


def rise(
    rl_node: Response, m: Response, resistance: float, u_rs: float
) -> tuple[float, float]:
    """Rise = R_L(200 kHz) - R_L(43.0 kHz) after the correction H / m, and
    u_hi, its standard uncertainty from the phasor fits of M2 and M3 at the
    two frequencies (linearised, each phasor's gain and phase apart) and the
    full uncertainty of R_s_bb, to which Z is proportional."""
    values, variance = [], 0.0
    for index in (RISE_HIGH, RISE_LOW):
        h2, mm = complex(rl_node.ratio[index]), complex(m.ratio[index])
        values.append(_loss_at(h2, mm, resistance))
    value = values[0] - values[1]
    for sign, index in ((1.0, RISE_HIGH), (-1.0, RISE_LOW)):
        h2, mm = complex(rl_node.ratio[index]), complex(m.ratio[index])
        base = _loss_at(h2, mm, resistance)
        for which, response in (("h2", rl_node), ("m", m)):
            relative = float(response.gain_sigma[index] / abs(response.ratio[index]))
            phase = math.radians(float(response.phase_sigma_deg[index]))
            for factor in (1.0 + relative, complex(math.cos(phase), math.sin(phase))):
                if which == "h2":
                    moved = _loss_at(h2 * factor, mm, resistance)
                else:
                    moved = _loss_at(h2, mm * factor, resistance)
                variance += (sign * (moved - base)) ** 2
    variance += (value * u_rs / resistance) ** 2
    return value, math.sqrt(variance)


def crossing_hz(response: Response) -> float | None:
    """Where the phase crosses -90 degrees, linear in log frequency between
    the bracketing coarse points; None without a crossing."""
    phase = response.phase_deg
    f = response.frequency_hz
    for i in range(f.size - 1):
        if phase[i] > -90.0 >= phase[i + 1]:
            x0, x1 = math.log(f[i]), math.log(f[i + 1])
            t = (phase[i] + 90.0) / (phase[i] - phase[i + 1])
            return float(math.exp(x0 + t * (x1 - x0)))
    return None


# --- the precondition and the rules ------------------------------------------


@dataclass(frozen=True)
class Identity:
    """The precondition: M2 against pilot run 3, with the same R_s_bb."""

    inductance_relative: float
    capacitance_relative: float
    loss_difference_ohm: float
    u_l: float
    met: bool


def identity(m2: Parts, pilot: Parts) -> Identity:
    dl = m2.inductance_h / pilot.inductance_h - 1.0
    dc = m2.capacitance_f / pilot.capacitance_f - 1.0
    dr = m2.r_l0 - pilot.r_l0
    met = (
        abs(dl) <= IDENTITY_RELATIVE
        and abs(dc) <= IDENTITY_RELATIVE
        and abs(dr) <= IDENTITY_FACTOR * m2.u_l
    )
    return Identity(dl, dc, dr, m2.u_l, met)


def g1_uncertainty(u_l: float, dc_bb: MeterValue, d: float, p: float) -> float:
    """u = sqrt(u_L^2 + u_dc,ng^2 + (p |D| / sqrt(3))^2): the meter's gain
    is common to R_s_bb and R_dc_bb and acts on D once."""
    return math.sqrt(u_l**2 + dc_bb.u_ng**2 + (p * abs(d) / math.sqrt(3.0)) ** 2)


def g1_predicates(d: float, u: float) -> dict[str, bool]:
    """Each outcome of G1 evaluated apart, after the undecidable case."""
    return {
        ACCOUNTED: abs(d) <= ACCOUNTED_FACTOR * u,
        SHORT: d > SHORT_FACTOR * u and d > SHORT_FLOOR_OHM,
        EXCEEDS: d < -EXCEEDS_FACTOR * u,
    }


def rule_g1(d: float, u: float) -> str:
    """G1 as registered: inconclusive when u > 5 ohm, whatever D is;
    otherwise the one predicate that holds, or inconclusive."""
    if u > UNDECIDABLE_U_OHM:
        return INCONCLUSIVE
    holding = [name for name, holds in g1_predicates(d, u).items() if holds]
    if len(holding) > 1:
        raise AssertionError(f"two outcomes of G1 hold together: {holding}")
    return holding[0] if holding else INCONCLUSIVE


def mismatch_measurable(dphi_deg: np.ndarray, dg: np.ndarray) -> bool:
    return bool(
        np.max(np.abs(dphi_deg)) > MISMATCH_PHASE_DEG
        or np.max(np.abs(dg)) > MISMATCH_GAIN
    )


def g2_predicates(
    measurable: bool, rise_ohm: float, u_hi: float, p0: float, p1: float
) -> dict[str, bool]:
    return {
        ARTEFACT: measurable
        and rise_ohm <= ARTEFACT_FACTOR * u_hi
        and p1 <= P_RATIO * p0,
        REMAINS: (not measurable) and rise_ohm > REMAINS_FACTOR * u_hi,
        MIXED: measurable and rise_ohm > REMAINS_FACTOR * u_hi,
    }


def rule_g2(
    measurable: bool, rise_ohm: float, u_hi: float, p0: float, p1: float
) -> str:
    holding = [
        name
        for name, holds in g2_predicates(measurable, rise_ohm, u_hi, p0, p1).items()
        if holds
    ]
    if len(holding) > 1:
        raise AssertionError(f"two outcomes of G2 hold together: {holding}")
    return holding[0] if holding else INCONCLUSIVE


# --- the follow-up's analysis -----------------------------------------------


@dataclass(frozen=True)
class Sweeps:
    """The coarse responses of the follow-up's sweeps (M5 optional)."""

    m0: Response
    m1: Response
    m2: Response
    m3: Response
    m5: Response | None = None


@dataclass
class Outcome:
    """Everything the registration computes from M0 to M5, and the outcomes."""

    values: dict[str, float] = field(default_factory=dict)
    series: dict[str, list[float]] = field(default_factory=dict)
    g1: str = NOT_EVALUATED
    g2: str = NOT_EVALUATED
    g1_pilot: str = NOT_EVALUATED
    precondition: bool | None = None
    notes: list[str] = field(default_factory=list)
    new_findings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "values": dict(self.values),
            "series": {k: list(v) for k, v in self.series.items()},
            "g1": self.g1,
            "g2": self.g2,
            "g1_pilot": self.g1_pilot,
            "precondition": self.precondition,
            "notes": list(self.notes),
            "new_findings": list(self.new_findings),
        }


def pilot_response(data_dir: Path | None = None) -> Response:
    """Pilot run 3, the R-L node sweep of ``ad3-rlc-pilot``, at the coarse
    frequencies."""
    from pbc.data import SAMPLES_DIR

    directory = data_dir or SAMPLES_DIR / "ad3-rlc-pilot"
    return at_coarse(ad3_rlc_pilot.response(directory, "rl-node"))


def evaluate(
    sweeps: Sweeps,
    readings: Sequence[Reading],
    pilot: Response | None = None,
) -> Outcome:
    """Apply the registration to the follow-up's sweeps and readings.

    ``pilot`` is pilot run 3 at the coarse frequencies (the R-L node sweep
    of ``ad3-rlc-pilot``); it is read with R_s_bb, like M2, so that the
    precondition compares the two sweeps and not two resistances."""
    out = Outcome()
    v = out.values
    rs = meter_value(readings, RS_BB)
    dc_bb = meter_value(readings, DC_BB)
    dc_out = meter_value(readings, DC_OUT)
    zero_ = zero(readings)
    v.update(
        {
            "z": zero_.z,
            "dz": zero_.dz,
            "R_s_bb": rs.value,
            "u_R_s_bb": rs.u,
            "u_R_s_bb_ng": rs.u_ng,
            "R_dc_bb": dc_bb.value,
            "u_R_dc_bb": dc_bb.u,
            "u_R_dc_bb_ng": dc_bb.u_ng,
            "R_dc": dc_out.value,
            "u_R_dc": dc_out.u,
        }
    )
    low, high = resistor_band()
    v["resistor_band_low"], v["resistor_band_high"] = low, high
    if not low <= rs.value <= high:
        out.notes.append(
            f"R_s_bb reads {rs.value:.2f} ohm, outside {low:.1f} to {high:.1f} ohm:"
            " a gross error of the meter or of the contacts (reported beside G1;"
            " it decides no outcome)"
        )

    m = sweeps.m3
    dg = np.abs(m.ratio) - 1.0
    dphi = np.degrees(np.angle(m.ratio))
    out.series["dg"] = dg.tolist()
    out.series["dphi_deg"] = dphi.tolist()
    measurable = mismatch_measurable(dphi, dg)
    v["max_abs_dphi_deg"] = float(np.max(np.abs(dphi)))
    v["max_abs_dg"] = float(np.max(np.abs(dg)))
    v["mismatch_measurable"] = float(measurable)

    # G1: H uncorrected.
    raw = parts(sweeps.m2, rs.value, rs.u_ng)
    out.series["R_L_uncorrected"] = list(raw.loss_ohm)
    v.update(
        {
            "L_H": raw.inductance_h,
            "C_F": raw.capacitance_f,
            "R_L0": raw.r_l0,
            "u_L": raw.u_l,
        }
    )
    d = raw.r_l0 - dc_bb.value
    u = g1_uncertainty(raw.u_l, dc_bb, d, P_REGISTERED)
    u_sensitivity = g1_uncertainty(raw.u_l, dc_bb, d, P_SENSITIVITY)
    v.update({"D": d, "u_G1": u, "u_G1_p_1_2": u_sensitivity})
    out.g1 = rule_g1(d, u)
    v["g1_sensitivity_differs"] = float(rule_g1(d, u_sensitivity) != out.g1)
    if out.g1 == EXCEEDS:
        out.new_findings.append(
            "D < -3 u: predicted by neither explanation; the sweep's model or the"
            " meter reading is wrong"
        )

    # G2: H / m for both sweeps, the model refitted.
    corrected_m2 = divided(sweeps.m2, m.ratio)
    corrected_m1 = divided(sweeps.m1, m.ratio)
    fixed = parts(corrected_m2, rs.value, rs.u_ng)
    out.series["R_L_corrected"] = list(fixed.loss_ohm)
    p0 = phase_rms(sweeps.m1, rs.value, raw)
    p1 = phase_rms(corrected_m1, rs.value, fixed)
    rise_ohm, u_hi = rise(sweeps.m2, m, rs.value, rs.u)
    v.update({"P0_deg": p0, "P1_deg": p1, "Rise": rise_ohm, "u_hi": u_hi})
    out.g2 = rule_g2(measurable, rise_ohm, u_hi, p0, p1)

    # The precondition (identity of the parts).
    if pilot is not None:
        pilot_parts = parts(pilot, rs.value, rs.u_ng)
        same = identity(raw, pilot_parts)
        v.update(
            {
                "identity_L_relative": same.inductance_relative,
                "identity_C_relative": same.capacitance_relative,
                "identity_R_L0_difference": same.loss_difference_ohm,
                "pilot_L_H": pilot_parts.inductance_h,
                "pilot_C_F": pilot_parts.capacitance_f,
                "pilot_R_L0": pilot_parts.r_l0,
            }
        )
        out.precondition = same.met
        if same.met:
            out.g1_pilot = out.g1
        else:
            out.g1_pilot = NOT_EVALUATED
            out.notes.append(
                "the precondition is not met: the conclusions are scoped to the"
                " circuit of M1 to M5; the pilot's discrepancy stays not evaluated"
                " for G1, and G2 (a property of the instrument) carries over"
            )

    # M1 against M0, and M5 against M2: reported, read by no rule.
    c0, c1 = crossing_hz(sweeps.m0), crossing_hz(sweeps.m1)
    if c0 is not None and c1 is not None:
        v["crossing_M0_hz"], v["crossing_M1_hz"] = c0, c1
        v["crossing_M1_minus_M0_hz"] = c1 - c0
    else:
        out.notes.append("M0 or M1 has no -90 degree crossing")
    out.series["phase_M1_minus_M0_deg"] = wrap_deg(
        sweeps.m1.phase_deg - sweeps.m0.phase_deg
    ).tolist()
    if sweeps.m5 is not None:
        again = parts(sweeps.m5, rs.value, rs.u_ng)
        v.update(
            {
                "M5_L_relative": again.inductance_h / raw.inductance_h - 1.0,
                "M5_C_relative": again.capacitance_f / raw.capacitance_f - 1.0,
                "M5_R_L0_difference": again.r_l0 - raw.r_l0,
            }
        )
    return out


# --- the analysis of the existing sweeps (exploratory) -----------------------

# The channel mismatches whose effect on the pilot's numbers is shown: a
# relative phase of channel 2 (degrees) and a relative gain error. The
# smallest pair is the registration's threshold of a measurable mismatch.
SENSITIVITY_PHASES_DEG = (-1.0, -0.3, 0.0, 0.3, 1.0)
SENSITIVITY_GAINS = (-0.01, -0.003, 0.0, 0.003, 0.01)


def pilot_analysis(data_dir: Path | None = None) -> dict:
    """The pilot's sweeps read with the registration's quantities, the
    nominal 100 ohm in place of R_s_bb (no reading exists): R_L(f), R_L0,
    u_L (the spread over the three frequencies and the resistor's 1 %),
    L, C, P0, and the sensitivity of R_L0, Rise and P to an assumed channel
    mismatch. Exploratory: these data chose the thresholds."""
    from pbc.data import SAMPLES_DIR

    directory = data_dir or SAMPLES_DIR / "ad3-rlc-pilot"
    rl = at_coarse(ad3_rlc_pilot.response(directory, "rl-node"))
    capacitor = at_coarse(ad3_rlc_pilot.response(directory, "capacitor"))
    r = RESISTOR_NOMINAL_OHM
    u_r = RESISTOR_TOLERANCE * r  # the tolerance, read as a standard uncertainty
    base = parts(rl, r, u_r)
    z = impedance(rl, r)
    loss_sigma = []
    for index in range(rl.frequency_hz.size):
        h = complex(rl.ratio[index])
        relative = float(rl.gain_sigma[index] / abs(h))
        phase = math.radians(float(rl.phase_sigma_deg[index]))
        moved_gain = (r * h * (1 + relative) / (1 - h * (1 + relative))).real
        turn = complex(math.cos(phase), math.sin(phase))
        moved_phase = (r * h * turn / (1 - h * turn)).real
        loss_sigma.append(
            math.hypot(moved_gain - z.real[index], moved_phase - z.real[index])
        )
    rows = []
    for dphi in SENSITIVITY_PHASES_DEG:
        for dg in SENSITIVITY_GAINS:
            m = np.full(
                rl.frequency_hz.size, (1.0 + dg) * np.exp(1j * math.radians(dphi))
            )
            mm = Response(rl.frequency_hz, m, np.zeros(m.size), np.zeros(m.size))
            fixed = parts(divided(rl, m), r, u_r)
            rise_ohm, _ = rise(rl, mm, r, u_r)
            rows.append(
                {
                    "dphi_deg": dphi,
                    "dg": dg,
                    "R_L0": fixed.r_l0,
                    "Rise": rise_ohm,
                    "P_deg": phase_rms(divided(capacitor, m), r, fixed),
                    "L_H": fixed.inductance_h,
                    "C_F": fixed.capacitance_f,
                }
            )
    unity = Response(
        rl.frequency_hz,
        np.ones(rl.frequency_hz.size, dtype=complex),
        np.zeros(rl.frequency_hz.size),
        np.zeros(rl.frequency_hz.size),
    )
    rise_ohm, u_hi = rise(rl, unity, r, u_r)
    return {
        "frequency_hz": rl.frequency_hz.tolist(),
        "R_L": list(base.loss_ohm),
        "R_L_sigma": loss_sigma,
        "R_L0": base.r_l0,
        "u_L": base.u_l,
        "L_H": base.inductance_h,
        "C_F": base.capacitance_f,
        "P0_deg": phase_rms(capacitor, r, base),
        "Rise": rise_ohm,
        "u_hi": u_hi,
        "crossing_hz": crossing_hz(capacitor),
        "phase_sigma_deg_max": float(
            max(np.max(rl.phase_sigma_deg), np.max(capacitor.phase_sigma_deg))
        ),
        "sensitivity": rows,
    }
