"""The ring-down fit of the transient-response protocol (F145): the
resonance frequency and the quality factor of a series RLC circuit from the
capacitor voltage after a step, each with its standard error.

After a step the capacitor voltage of an underdamped series RLC circuit is

    v(t) = v_inf + e^(-alpha t) (a cos(omega_d t) + b sin(omega_d t)),

with the decay rate alpha = R / 2L and the damped angular frequency
omega_d = sqrt(omega_0^2 - alpha^2). So omega_0 = sqrt(omega_d^2 + alpha^2)
and Q = omega_0 / (2 alpha). The fit is the reference solution of F139's
manual route (Issue #614, 2026-11-24): nonlinear least squares started
from the spectrum's peak and a coarse search of alpha, in which the model
is linear in v_inf, a, and b; the standard errors of f0 and Q are
propagated from the covariance of alpha and omega_d.
"""

import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass

import numpy as np
from scipy.optimize import curve_fit

MIN_SAMPLES = 16


@dataclass(frozen=True)
class RingdownFit:
    """What one ring-down shows, each value with its standard error:
    ``decay_rate`` (1/s), ``damped_frequency_hz`` (Hz), ``f0_hz`` (Hz),
    ``q`` (dimensionless), and the fitted final level ``v_inf`` (V)."""

    decay_rate: float
    decay_rate_se: float
    damped_frequency_hz: float
    damped_frequency_se: float
    f0_hz: float
    f0_se: float
    q: float
    q_se: float
    v_inf: float
    a: float
    b: float
    samples: int

    def to_dict(self) -> dict[str, float]:
        return asdict(self)

    def curve(self, t: np.ndarray) -> np.ndarray:
        """The fitted voltage (V) at ``t`` (s, from the first fitted sample)."""
        return model(
            np.asarray(t, dtype=float),
            self.v_inf,
            self.a,
            self.b,
            self.decay_rate,
            2.0 * math.pi * self.damped_frequency_hz,
        )


def model(t, v_inf, a, b, alpha, omega_d):
    return v_inf + np.exp(-alpha * t) * (
        a * np.cos(omega_d * t) + b * np.sin(omega_d * t)
    )


def _linear_part(t, v, alpha, omega_d):
    """For fixed rates the model is linear in v_inf, a and b: their least
    squares values and the sum of squared residuals."""
    decay = np.exp(-alpha * t)
    design = np.column_stack(
        [np.ones_like(t), decay * np.cos(omega_d * t), decay * np.sin(omega_d * t)]
    )
    coefficients, *_ = np.linalg.lstsq(design, v, rcond=None)
    return coefficients, float(np.sum((design @ coefficients - v) ** 2))


def _start(t, v):
    """Starting values: omega_d from the spectrum's peak of the record less
    its final level, alpha from a coarse search, the rest from the linear
    part."""
    step = (t[-1] - t[0]) / (len(t) - 1)
    tail = v[-max(len(v) // 8, 2) :]
    spectrum = np.abs(np.fft.rfft(v - np.mean(tail), 8 * len(v)))
    frequencies = np.fft.rfftfreq(8 * len(v), step)
    peak = int(np.argmax(spectrum[1:])) + 1
    omega_d = 2 * math.pi * frequencies[peak]
    best = None
    for alpha in omega_d * np.geomspace(0.003, 1.5, 25):
        coefficients, misfit = _linear_part(t, v, alpha, omega_d)
        if best is None or misfit < best[0]:
            best = (misfit, alpha, coefficients)
    _, alpha, (v_inf, a, b) = best
    return [v_inf, a, b, alpha, omega_d]


def fit_ringdown(t_s: Sequence[float], v: Sequence[float]) -> RingdownFit:
    """Fit the ring-down model to the record ``v`` (V) at the times ``t_s``
    (s) and return alpha, omega_d, f0 and Q with their standard errors.
    Raises ``ValueError`` for a record it cannot read as a ring-down."""
    t = np.asarray(t_s, dtype=float)
    v = np.asarray(v, dtype=float)
    if t.ndim != 1 or v.ndim != 1 or len(t) != len(v):
        raise ValueError("t_s and v must be one-dimensional and of equal length")
    if len(t) < MIN_SAMPLES:
        raise ValueError(f"a ring-down needs at least {MIN_SAMPLES} samples")
    if not (np.all(np.isfinite(t)) and np.all(np.isfinite(v))):
        raise ValueError("every time and voltage must be finite")
    if not np.all(np.diff(t) > 0):
        raise ValueError("the times must increase")

    # Time from the first sample: a and b absorb the shift, the rates do not
    # change, and the exponential stays well scaled.
    t = t - t[0]
    # region: fit
    try:
        values, covariance = curve_fit(model, t, v, p0=_start(t, v), maxfev=20_000)
    except RuntimeError as error:
        raise ValueError(f"the record could not be fitted: {error}") from None
    if not np.all(np.isfinite(covariance)):
        raise ValueError("the record does not determine a ring-down")
    v_inf, a, b, alpha, omega_d = values
    omega_d = abs(omega_d)
    if alpha <= 0:
        raise ValueError("the record does not decay")
    omega_0 = math.hypot(omega_d, alpha)
    q = omega_0 / (2 * alpha)
    # endregion: fit

    var_alpha, var_omega = covariance[3, 3], covariance[4, 4]
    cov = covariance[3, 4] * math.copysign(1.0, values[4])

    def propagated(d_alpha: float, d_omega: float) -> float:
        variance = (
            d_alpha**2 * var_alpha
            + d_omega**2 * var_omega
            + 2 * d_alpha * d_omega * cov
        )
        return math.sqrt(max(variance, 0.0))

    f0_se = propagated(alpha / omega_0, omega_d / omega_0) / (2 * math.pi)
    q_se = propagated(
        1 / (2 * omega_0) - omega_0 / (2 * alpha**2), omega_d / (2 * alpha * omega_0)
    )

    # No oscillation: an amplitude that the noise explains, less than one
    # period in the record, or a Q that does not stand clear of 1/2, the
    # value at critical damping.
    amplitude = math.hypot(a, b)
    d_a, d_b = (a / amplitude, b / amplitude) if amplitude else (1.0, 0.0)
    amplitude_se = math.sqrt(
        max(
            d_a**2 * covariance[1, 1]
            + d_b**2 * covariance[2, 2]
            + 2 * d_a * d_b * covariance[1, 2],
            0.0,
        )
    )
    if (
        amplitude <= 5 * amplitude_se
        or omega_d * t[-1] < 2 * math.pi
        or q - 3 * q_se <= 0.5
    ):
        raise ValueError("the record shows no oscillation")

    return RingdownFit(
        decay_rate=float(alpha),
        decay_rate_se=math.sqrt(var_alpha),
        damped_frequency_hz=float(omega_d / (2 * math.pi)),
        damped_frequency_se=math.sqrt(var_omega) / (2 * math.pi),
        f0_hz=float(omega_0 / (2 * math.pi)),
        f0_se=f0_se,
        q=float(q),
        q_se=q_se,
        v_inf=float(v_inf),
        a=float(a),
        b=float(b),
        samples=len(t),
    )
