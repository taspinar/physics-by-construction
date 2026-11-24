"""The transient-response protocol of the Autonomous Physics Lab (F145).

One ring-down: drive the prepared series RLC circuit with the square wave
of the contract (0 V to A) at a frequency low enough that each half period
holds many decay times, acquire one and a half periods, so that the record
always holds a rising edge followed by a whole half period, pass the
capture through the quality gate, find the rising edge on the source
channel, and fit the capacitor voltage from just after the edge to the
next edge (``ringdown.fit_ringdown``). The result is f0 and Q, each with
its standard error. Repetitions are combined by their weighted mean
(``estimates.combine``).

The simulator's check compares f0 and Q with the closed form of the
simulated circuit, which the protocol never sees; on a live or recorded
circuit the check is the agreement with the frequency-response protocol
(``estimates.agreement``), because the nominal closed form does not
describe the real parts (F140).
"""

import math
from dataclasses import dataclass

import numpy as np

from pbc.electromagnetism.circuits import SeriesRLC
from pbc.instruments import SQUARE, Capture, Instrument
from pbc.products.physics_lab.estimates import Combined, Estimate, combine
from pbc.products.physics_lab.quality import IDEAL_RAILS, Rails, Verdict, gate
from pbc.products.physics_lab.ringdown import RingdownFit, fit_ringdown

PROTOCOL_VERSION = "f145-transient-1"
# The fit starts this fraction of a half period after the edge, at least
# two samples: the edge itself is not a free ring-down.
SKIP_FRACTION = 0.01
# The simulator's check: f0 and Q within this many standard errors of the
# closed form, and within F138's relative tolerances.
CHECK_SIGMAS = 3.0
F0_TOLERANCE = 0.01  # relative
Q_TOLERANCE = 0.03  # relative
# A half period of the square wave must hold at least this many decay
# times 1 / alpha of the declared circuit, so that the ring of one edge has
# died before the next (the current bound of a step assumes it).
MIN_HALF_PERIOD_DECAYS = 10.0


@dataclass(frozen=True)
class TransientSettings:
    """One ring-down: the square wave's ``amplitude_v`` (V) and
    ``square_hz`` (Hz), the acquisition's ``sample_rate_hz`` (samples/s),
    and ``highest_hz`` (Hz), the highest ringing frequency the gate checks
    the sample rate against."""

    amplitude_v: float = 1.0
    square_hz: float = 100.0
    sample_rate_hz: float = 500_000.0
    highest_hz: float = 25_000.0

    @property
    def samples(self) -> int:
        """One and a half periods of the square wave, and one sample."""
        return math.ceil(1.5 * self.sample_rate_hz / self.square_hz) + 1


def check_settings(settings: TransientSettings, circuit: SeriesRLC) -> None:
    """Refuse a square wave too fast for the declared ``circuit``: each
    half period must hold ``MIN_HALF_PERIOD_DECAYS`` decay times."""
    half = 0.5 / settings.square_hz
    if half * circuit.damping_rate < MIN_HALF_PERIOD_DECAYS:
        raise ValueError(
            f"a half period of {half * 1e3:g} ms holds"
            f" {half * circuit.damping_rate:.1f} decay times of the declared"
            f" circuit, fewer than {MIN_HALF_PERIOD_DECAYS:g}: lower square_hz"
        )


@dataclass(frozen=True)
class Ringdown:
    """One ring-down measurement: the capture, the gate's verdict, the
    window of samples fitted, and the fit, or why there is none."""

    settings: TransientSettings
    capture: Capture
    verdict: Verdict
    window: tuple[int, int] | None
    fit: RingdownFit | None
    note: str

    @property
    def valid(self) -> bool:
        return self.fit is not None


def ringdown_window(
    source: np.ndarray, amplitude_v: float, sample_rate_hz: float, square_hz: float
) -> tuple[int, int] | None:
    """The samples [start, end) of the first free ring-down: from just after
    the first rising edge of the source to the next falling edge, or None
    when the record holds no rising edge followed by one."""
    high = np.nan_to_num(source, nan=0.0) >= amplitude_v / 2.0
    rising = np.flatnonzero(~high[:-1] & high[1:]) + 1
    falling = np.flatnonzero(high[:-1] & ~high[1:]) + 1
    skip = max(2, math.ceil(SKIP_FRACTION * sample_rate_hz / (2.0 * square_hz)))
    for edge in rising:
        after = falling[falling > edge]
        if len(after):
            return (int(edge + skip), int(after[0]))
    return None


def analyse_ringdown(
    capture: Capture, settings: TransientSettings, rails: Rails = IDEAL_RAILS
) -> Ringdown:
    """Gate the capture, find its ring-down, and fit it."""
    verdict = gate(
        capture, settings.amplitude_v, settings.highest_hz, rails, waveform=SQUARE
    )
    if not verdict.valid:
        return Ringdown(
            settings, capture, verdict, None, None, "; ".join(verdict.reasons)
        )
    source = np.asarray(capture.channels["source"], dtype=float)
    window = ringdown_window(
        source, settings.amplitude_v, capture.sample_rate_hz, settings.square_hz
    )
    if window is None:
        return Ringdown(settings, capture, verdict, None, None, "no rising edge")
    start, end = window
    t = np.asarray(capture.t, dtype=float)[start:end]
    v = np.asarray(capture.channels["response"], dtype=float)[start:end]
    keep = verdict.masks["response"][start:end]
    try:
        fit = fit_ringdown(t[keep], v[keep])
    except ValueError as reason:
        return Ringdown(settings, capture, verdict, window, None, str(reason))
    return Ringdown(settings, capture, verdict, window, fit, "fitted")


def measure_ringdown(
    instrument: Instrument, settings: TransientSettings, rails: Rails = IDEAL_RAILS
) -> Ringdown:
    """Measure and read one ring-down through the guarded instrument."""
    # region: measure
    instrument.excite(settings.amplitude_v, settings.square_hz, SQUARE)
    capture = instrument.acquire(settings.sample_rate_hz, settings.samples)
    # endregion: measure
    return analyse_ringdown(capture, settings, rails)


@dataclass(frozen=True)
class TransientResult:
    """The ring-downs of a run combined: f0 and Q, each over the valid
    repetitions."""

    f0_hz: Combined | None
    q: Combined | None
    valid: int
    invalid: int


def combine_ringdowns(ringdowns: list[Ringdown]) -> TransientResult:
    fits = [r.fit for r in ringdowns if r.fit is not None]
    invalid = len(ringdowns) - len(fits)
    if not fits:
        return TransientResult(None, None, 0, invalid)
    f0 = combine([Estimate(f.f0_hz, f.f0_se) for f in fits])
    q = combine([Estimate(f.q, f.q_se) for f in fits])
    return TransientResult(f0, q, len(fits), invalid)


def reference(circuit: SeriesRLC) -> dict[str, float]:
    """The closed form of the model: f0 (Hz) and Q."""
    return {
        "f0_hz": float(circuit.natural_frequency / (2.0 * math.pi)),
        "q": float(circuit.quality_factor),
    }


@dataclass(frozen=True)
class TransientCheck:
    """The simulator's check against the closed form."""

    correct: bool
    metrics: dict[str, float]
    note: str


def check_against_closed_form(
    result: TransientResult, circuit: SeriesRLC
) -> TransientCheck | None:
    """f0 and Q of ``result`` against the closed form of the simulated
    ``circuit``: within ``CHECK_SIGMAS`` standard errors and within F138's
    relative tolerances. None when no ring-down was fitted."""
    if result.f0_hz is None or result.q is None:
        return None
    ref = reference(circuit)
    f0, q = result.f0_hz.estimate, result.q.estimate
    metrics = {
        "f0_hz": f0.value,
        "f0_se": f0.se,
        "q": q.value,
        "q_se": q.se,
        "reference_f0_hz": ref["f0_hz"],
        "reference_q": ref["q"],
        "f0_relative_error": f0.value / ref["f0_hz"] - 1.0,
        "q_relative_error": q.value / ref["q"] - 1.0,
        "f0_sigmas": abs(f0.value - ref["f0_hz"]) / f0.se,
        "q_sigmas": abs(q.value - ref["q"]) / q.se,
    }
    correct = bool(
        metrics["f0_sigmas"] <= CHECK_SIGMAS
        and metrics["q_sigmas"] <= CHECK_SIGMAS
        and abs(metrics["f0_relative_error"]) <= F0_TOLERANCE
        and abs(metrics["q_relative_error"]) <= Q_TOLERANCE
    )
    note = (
        f"{'within' if correct else 'outside'} {CHECK_SIGMAS:g} standard errors"
        f" and the tolerance of the closed form (f0 {F0_TOLERANCE:.0%},"
        f" Q {Q_TOLERANCE:.0%})"
    )
    return TransientCheck(correct, metrics, note)
