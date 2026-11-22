"""The frequency-response protocol of the Autonomous Physics Lab slice.

One point: drive the prepared series RLC circuit at a frequency f and an
amplitude V, acquire a whole number of periods after the transient has
settled, and read the phasors of the source and of the capacitor voltage
(``circuits.steady_phasor``). The transfer function H = V_C / V_S gives the
gain |H| and the phase arg H at f. For a series RLC circuit the phase is
-90 degrees exactly at the natural frequency f0 = 1 / (2 pi sqrt(L C)), and
the gain there is the quality factor Q = sqrt(L / C) / R.

The analysis of a sweep estimates f0 where the measured phase crosses -90
degrees (linear in the phase against log f between the two points that
bracket it) and Q from the gains of those two points through the
second-order response |H| = 1 / sqrt((1 - x^2)^2 + (x / Q)^2), x = f / f0,
averaged; this is the hypothesis of the protocol, which the evaluator's
check tests against the closed form of the circuit. The
evaluator's check (``evaluate``) recomputes the points from the raw samples
and compares them with the closed form of the model, which the route never
sees.
"""

import itertools
import math
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from pbc.electromagnetism.circuits import SeriesRLC, steady_phasor
from pbc.instruments import Capture, Envelope, Instrument, Interlock, Limit

PROTOCOL_VERSION = "f138-frequency-response-1"

# The tolerances of the evaluator's check against the closed form.
F0_TOLERANCE = 0.01  # relative
Q_TOLERANCE = 0.03  # relative


def bench_envelope(interlocks: tuple[Interlock, ...] = ()) -> Envelope:
    """The safety envelope of the bench: a low-voltage excitation, the
    frequencies and sampling the protocol needs, and a timeout per call."""
    return Envelope(
        amplitude=Limit("excitation amplitude", "V", 0.01, 2.0),
        frequency=Limit("excitation frequency", "Hz", 100.0, 50_000.0),
        sample_rate=Limit("sample rate", "samples/s", 1_000.0, 5_000_000.0),
        samples=Limit("samples per acquisition", "samples", 16, 16_384, integer=True),
        timeout_s=10.0,
        interlocks=interlocks,
    )


# The live bench of F140's pilot (the Analog Discovery 3, docs/products.md):
# the AD3 drives 30 mA without distortion, so the excitation's amplitude over
# the circuit's series resistance stays within it; the owner's circuit (1 mH,
# 10 nF) resonates near 50 kHz, so the frequencies reach 200 kHz, sampled at
# 64 samples per period at most.
LIVE_CURRENT_LIMIT_A = 0.030
LIVE_HIGH_HZ = 200_000.0
LIVE_SAMPLE_RATE_HZ = 20_000_000.0


def live_envelope(
    series_resistance_ohm: float, interlocks: tuple[Interlock, ...] = ()
) -> Envelope:
    """The safety envelope of the live bench: the bench's amplitude, its
    samples per acquisition and timeout, the frequencies of the owner's
    circuit, and the current bound through ``series_resistance_ohm``, the
    circuit's declared series resistance at its lower tolerance."""
    return Envelope(
        amplitude=Limit("excitation amplitude", "V", 0.01, 2.0),
        frequency=Limit("excitation frequency", "Hz", 1_000.0, LIVE_HIGH_HZ),
        sample_rate=Limit("sample rate", "samples/s", 1_000.0, LIVE_SAMPLE_RATE_HZ),
        samples=Limit("samples per acquisition", "samples", 16, 16_384, integer=True),
        timeout_s=10.0,
        interlocks=interlocks,
        current=Limit(
            "source current bound (amplitude / series resistance)",
            "A",
            0.0,
            LIVE_CURRENT_LIMIT_A,
        ),
        series_resistance_ohm=series_resistance_ohm,
    )


@dataclass(frozen=True)
class Config:
    """One run of the protocol, as an example input states it."""

    low_hz: float = 1_000.0
    high_hz: float = 25_000.0
    coarse_points: int = 13
    refine_points: int = 6
    amplitude_v: float = 1.0
    periods: int = 8
    samples_per_period: int = 64
    seed: int = 138
    agent_budget: int = 16
    circuit_confirmed: bool = False

    def __post_init__(self):
        if not 0 < self.low_hz < self.high_hz:
            raise ValueError("need 0 < low_hz < high_hz")
        if self.coarse_points < 3 or self.refine_points < 0:
            raise ValueError("need at least 3 coarse points")
        if self.periods < 1 or self.samples_per_period < 8:
            raise ValueError("need at least one period and 8 samples per period")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_config(path: Path) -> Config:
    """The configuration in the TOML file ``path`` (table ``[protocol]``)."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    table = data.get("protocol")
    if not isinstance(table, dict):
        raise ValueError(f"{path} has no table [protocol]")
    known = set(Config.__dataclass_fields__)
    unknown = sorted(set(table) - known)
    if unknown:
        raise ValueError(f"{path}: unknown keys {', '.join(unknown)}")
    return Config(**table)


@dataclass(frozen=True)
class Point:
    """One measured point of the frequency response."""

    frequency_hz: float
    amplitude_v: float
    gain: float
    phase_deg: float


@dataclass(frozen=True)
class Measurement:
    """A point with the capture it was read from."""

    point: Point
    capture: Capture


def whole_periods(t: np.ndarray, frequency_hz: float) -> bool:
    """Whether the sample times ``t`` span a whole number of periods, as
    ``steady_phasor`` requires."""
    periods = (t[-1] - t[0]) * frequency_hz
    return round(periods) >= 1 and abs(periods - round(periods)) <= 1e-9 * max(
        periods, 1.0
    )


def fitted_phasor(signal: np.ndarray, t: np.ndarray, omega: float) -> complex:
    """The complex amplitude A e^(j phi) of A cos(omega t + phi) plus a
    constant, by least squares over the samples: for a record that does not
    span a whole number of periods, as a device's divided sample clock gives
    (F140). A cos(omega t + phi) = a cos(omega t) + b sin(omega t) with
    a = A cos(phi) and b = -A sin(phi), so the phasor is a - j b."""
    design = np.column_stack([np.cos(omega * t), np.sin(omega * t), np.ones(len(t))])
    (a, b, _), *_ = np.linalg.lstsq(design, signal, rcond=None)
    return complex(a, -b)


def transfer(capture: Capture, frequency_hz: float) -> tuple[float, float]:
    """The gain and the phase (degrees, in (-270, 90]) of response / source:
    from the phasors of whole periods (``steady_phasor``) when the record
    spans them, otherwise by the least-squares fit (``fitted_phasor``)."""
    omega = 2.0 * math.pi * frequency_hz
    t = np.asarray(capture.t, dtype=float)
    phasor = steady_phasor if whole_periods(t, frequency_hz) else fitted_phasor
    source = phasor(np.asarray(capture.channels["source"], dtype=float), t, omega)
    response = phasor(np.asarray(capture.channels["response"], dtype=float), t, omega)
    ratio = response / source
    phase = math.degrees(math.atan2(ratio.imag, ratio.real))
    if phase > 90.0:
        phase -= 360.0
    return float(abs(ratio)), float(phase)


def measure(
    instrument: Instrument, config: Config, frequency_hz: float, amplitude_v: float
) -> Measurement:
    """Measure one point through the guarded instrument."""
    instrument.excite(amplitude_v, frequency_hz)
    rate = config.samples_per_period * frequency_hz
    samples = config.periods * config.samples_per_period + 1
    capture = instrument.acquire(rate, samples)
    gain, phase = transfer(capture, frequency_hz)
    return Measurement(Point(frequency_hz, amplitude_v, gain, phase), capture)


@dataclass(frozen=True)
class Analysis:
    """The estimates of a sweep, or why there are none."""

    f0_hz: float | None
    q: float | None
    bracket: tuple[float, float] | None
    note: str


def analyse(points: list[Point]) -> Analysis:
    """Estimate f0 and Q from the points of a sweep."""
    ordered = sorted(points, key=lambda p: p.frequency_hz)
    for a, b in itertools.pairwise(ordered):
        if a.phase_deg >= -90.0 >= b.phase_deg and a.phase_deg != b.phase_deg:
            x = (a.phase_deg + 90.0) / (a.phase_deg - b.phase_deg)
            la, lb = math.log(a.frequency_hz), math.log(b.frequency_hz)
            f0 = math.exp(la + x * (lb - la))
            estimates = [_quality(p, f0) for p in (a, b)]
            if any(q is None for q in estimates):
                return Analysis(
                    f0, None, (a.frequency_hz, b.frequency_hz), _NOT_SECOND_ORDER
                )
            q = sum(estimates) / 2.0
            return Analysis(f0, q, (a.frequency_hz, b.frequency_hz), "bracketed")
    return Analysis(
        None, None, None, "the phase does not cross -90 degrees within the sweep"
    )


_NOT_SECOND_ORDER = "a gain near f0 is not that of a second-order response"


def _quality(point: Point, f0: float) -> float | None:
    """Q from one point of the second-order response
    |H| = 1 / sqrt((1 - x^2)^2 + (x / Q)^2), x = f / f0, or None where the
    gain is too high for that form."""
    x = point.frequency_hz / f0
    rest = 1.0 / point.gain**2 - (1.0 - x * x) ** 2
    return x / math.sqrt(rest) if rest > 0 else None


def reference(circuit: SeriesRLC) -> dict[str, float]:
    """The closed form of the model: f0 and Q."""
    return {
        "f0_hz": float(circuit.natural_frequency / (2.0 * math.pi)),
        "q": float(circuit.quality_factor),
    }


def model_gain(circuit: SeriesRLC, frequency_hz: np.ndarray) -> np.ndarray:
    """|V_C / V_S| of the closed form at ``frequency_hz``."""
    return np.abs(circuit.capacitor_phasor(1.0, 2.0 * np.pi * frequency_hz))


def model_phase(circuit: SeriesRLC, frequency_hz: np.ndarray) -> np.ndarray:
    """arg(V_C / V_S) of the closed form, degrees in (-180, 0)."""
    phasor = circuit.capacitor_phasor(1.0, 2.0 * np.pi * frequency_hz)
    return np.degrees(np.unwrap(np.angle(phasor)))


@dataclass(frozen=True)
class Check:
    """The evaluator's verdict against the closed form."""

    correct: bool | None  # None: the sweep did not bracket the resonance
    metrics: dict[str, float]
    note: str


def evaluate(points: list[Point], circuit: SeriesRLC) -> Check:
    """Compare the estimates of ``points`` with the closed form of
    ``circuit`` within ``F0_TOLERANCE`` and ``Q_TOLERANCE``."""
    analysis = analyse(points)
    ref = reference(circuit)
    frequencies = np.array([p.frequency_hz for p in points])
    gains = np.array([p.gain for p in points])
    worst = float(np.max(np.abs(gains / model_gain(circuit, frequencies) - 1.0)))
    metrics = {
        "points": float(len(points)),
        "reference_f0_hz": ref["f0_hz"],
        "reference_q": ref["q"],
        "largest_gain_deviation": worst,
    }
    if analysis.f0_hz is None or analysis.q is None:
        return Check(None, metrics, analysis.note)
    f0_error = analysis.f0_hz / ref["f0_hz"] - 1.0
    q_error = analysis.q / ref["q"] - 1.0
    metrics |= {
        "f0_hz": analysis.f0_hz,
        "q": analysis.q,
        "f0_relative_error": f0_error,
        "q_relative_error": q_error,
    }
    correct = bool(abs(f0_error) <= F0_TOLERANCE and abs(q_error) <= Q_TOLERANCE)
    note = (
        f"{'within' if correct else 'outside'} the tolerance of the closed form"
        f" (f0 within {F0_TOLERANCE:.0%}, Q within {Q_TOLERANCE:.0%})"
    )
    return Check(correct, metrics, note)
