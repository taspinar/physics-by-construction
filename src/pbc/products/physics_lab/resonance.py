"""The frequency-response protocol with intervals (F145).

One point is F138's (``protocol.measure``: drive at f and A, acquire after
the transient, read the response against the source), with two changes:
the capture passes the quality gate first, and each channel is read by
``pbc.electromagnetism.measurement.fit_sine`` over its valid samples, which
gives the amplitude and the phase with their standard errors. So each
point carries the gain |H| and the phase arg H of H = V_C / V_S with their
errors.

The interval of f0 and Q comes from a weighted least-squares fit of the
second-order response

    H(f) = k / (1 - x^2 + j x / Q),  x = f / f0,

to the logarithm of the gain and to the phase of every valid point, with
the parameters' covariance scaled by the reduced chi-square when that is
above one (a model that does not describe the circuit widens the interval
instead of hiding the misfit). F138's bracket estimator stays the route's
own estimate; the fit is the interval.
"""

import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass

import numpy as np
from scipy.optimize import least_squares

from pbc.electromagnetism.measurement import fit_sine
from pbc.instruments import Capture, Instrument
from pbc.products.physics_lab.estimates import Estimate
from pbc.products.physics_lab.quality import IDEAL_RAILS, Rails, Verdict, gate

PROTOCOL_VERSION = "f145-frequency-response-1"
MIN_POINTS = 4


@dataclass(frozen=True)
class ResponsePoint:
    """One valid point: ``frequency_hz`` (Hz), ``amplitude_v`` (V), the
    ``gain`` (V/V) and its standard error ``gain_se`` (V/V), the
    ``phase_deg`` (degrees, in (-270, 90]) and ``phase_se_deg`` (degrees)."""

    frequency_hz: float
    amplitude_v: float
    gain: float
    gain_se: float
    phase_deg: float
    phase_se_deg: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class PointMeasurement:
    """A measured point: the capture, the gate's verdict, and the point, or
    None when the capture is invalid."""

    frequency_hz: float
    amplitude_v: float
    capture: Capture
    verdict: Verdict
    point: ResponsePoint | None
    note: str

    @property
    def valid(self) -> bool:
        return self.point is not None


def analyse_point(
    capture: Capture,
    frequency_hz: float,
    amplitude_v: float,
    rails: Rails = IDEAL_RAILS,
) -> PointMeasurement:
    """Gate ``capture`` and read the gain and the phase with their errors."""
    verdict = gate(capture, amplitude_v, frequency_hz, rails)
    if not verdict.valid:
        note = "; ".join(verdict.reasons)
        return PointMeasurement(frequency_hz, amplitude_v, capture, verdict, None, note)
    # region: point
    t = np.asarray(capture.t, dtype=float)
    fits = {
        name: fit_sine(
            t,
            np.asarray(capture.channels[name], dtype=float),
            frequency_hz,
            verdict.masks[name],
        )
        for name in ("source", "response")
    }
    source, response = fits["source"], fits["response"]
    gain = response.amplitude / source.amplitude
    gain_se = gain * math.hypot(
        response.amplitude_error / response.amplitude,
        source.amplitude_error / source.amplitude,
    )
    phase = math.degrees(response.phase - source.phase)
    phase = (phase + 270.0) % 360.0 - 270.0  # into (-270, 90]
    phase_se = math.degrees(math.hypot(response.phase_error, source.phase_error))
    # endregion: point
    point = ResponsePoint(frequency_hz, amplitude_v, gain, gain_se, phase, phase_se)
    return PointMeasurement(frequency_hz, amplitude_v, capture, verdict, point, "read")


def measure_point(
    instrument: Instrument,
    frequency_hz: float,
    amplitude_v: float,
    periods: int = 8,
    samples_per_period: int = 64,
    rails: Rails = IDEAL_RAILS,
) -> PointMeasurement:
    """Measure one point through the guarded instrument, as F138 does."""
    instrument.excite(amplitude_v, frequency_hz)
    capture = instrument.acquire(
        samples_per_period * frequency_hz, periods * samples_per_period + 1
    )
    return analyse_point(capture, frequency_hz, amplitude_v, rails)


def model(frequency_hz: np.ndarray, f0: float, q: float, k: float) -> np.ndarray:
    """The second-order response H (complex) at ``frequency_hz`` (Hz)."""
    x = np.asarray(frequency_hz, dtype=float) / f0
    return k / (1.0 - x * x + 1j * x / q)


@dataclass(frozen=True)
class ResonanceFit:
    """f0 (Hz), Q, and the gain k at low frequency, each with its standard
    error, the reduced chi-square of the fit, and the points it used."""

    f0_hz: Estimate
    q: Estimate
    k: Estimate
    reduced_chi2: float
    points: int

    def to_dict(self) -> dict[str, object]:
        return {
            "f0_hz": self.f0_hz.to_dict(),
            "q": self.q.to_dict(),
            "k": self.k.to_dict(),
            "reduced_chi2": self.reduced_chi2,
            "points": self.points,
        }


def _wrap(degrees: np.ndarray) -> np.ndarray:
    return (degrees + 180.0) % 360.0 - 180.0


def fit_resonance(
    points: Sequence[ResponsePoint], start: tuple[float, float] | None = None
) -> ResonanceFit | None:
    """The weighted fit of the second-order response to ``points``, or None
    with fewer than ``MIN_POINTS`` or a fit that does not converge.
    ``start`` is (f0, Q) to start from; by default the point whose phase is
    nearest -90 degrees and the largest gain."""
    if len(points) < MIN_POINTS:
        return None
    f = np.array([p.frequency_hz for p in points])
    log_gain = np.log([p.gain for p in points])
    log_gain_se = np.array([p.gain_se / p.gain for p in points])
    phase = np.array([p.phase_deg for p in points])
    phase_se = np.array([p.phase_se_deg for p in points])
    if np.any(log_gain_se <= 0) or np.any(phase_se <= 0):
        return None
    if start is None:
        nearest = int(np.argmin(np.abs(phase + 90.0)))
        start = (float(f[nearest]), float(max(np.exp(log_gain).max(), 0.6)))

    # region: fit
    def residuals(parameters: np.ndarray) -> np.ndarray:
        f0, q, k = np.exp(parameters)
        h = model(f, f0, q, k)
        return np.concatenate(
            [
                (np.log(np.abs(h)) - log_gain) / log_gain_se,
                _wrap(np.degrees(np.angle(h)) - phase) / phase_se,
            ]
        )

    solution = least_squares(residuals, np.log([start[0], start[1], 1.0]))
    # endregion: fit
    if not solution.success:
        return None
    dof = 2 * len(points) - 3
    chi2 = float(solution.fun @ solution.fun)
    reduced = chi2 / dof
    jacobian = solution.jac
    try:
        covariance = np.linalg.inv(jacobian.T @ jacobian) * max(1.0, reduced)
    except np.linalg.LinAlgError:
        return None
    if not np.all(np.isfinite(covariance)):
        return None
    f0, q, k = np.exp(solution.x)
    se = np.sqrt(np.diag(covariance))  # of the logarithms: relative errors
    return ResonanceFit(
        Estimate(float(f0), float(f0 * se[0])),
        Estimate(float(q), float(q * se[1])),
        Estimate(float(k), float(k * se[2])),
        reduced,
        len(points),
    )
