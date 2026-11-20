"""Measurement quality of a sampled sinusoid (F142, the lesson "Measurement
quality and multimodal observations").

A capture of the RLC bench is a sinusoid at a known frequency, recorded
through a chain that may scale and offset it, clip it at the converter's
rails, quantise it, and lose samples (``pbc.instruments.channels``). This
module reads such a record:

- ``fit_sine``: the amplitude, phase, and offset of a sinusoid of known
  frequency by linear least squares over the samples that are marked valid,
  with standard errors from the scatter of the residuals;
- ``valid_samples``: the samples that carry information, leaving out the
  lost ones (not a number) and those at or beyond the rails;
- ``quality``: the flags a record is checked against before a number from it
  is used;
- ``calibrate``: the gain and offset of a channel from a reference of known
  voltage, and ``correct`` to undo them;
- ``alias``: the frequency at which a sampled sinusoid appears.
"""

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class SineFit:
    """A sinusoid A cos(2 pi f t + phi) + c fitted to samples: the amplitude
    (V), the phase (rad), the offset (V), their standard errors, the RMS of
    the residuals (V), and the number of samples used."""

    amplitude: float
    phase: float
    offset: float
    amplitude_error: float
    phase_error: float
    offset_error: float
    residual_rms: float
    used: int


def fit_sine(
    t: NDArray[np.float64],
    v: NDArray[np.float64],
    frequency_hz: float,
    valid: NDArray[np.bool_] | None = None,
) -> SineFit:
    """Fit A cos(2 pi f t + phi) + c to the samples ``v`` (V) at the times
    ``t`` (s), using only those that ``valid`` marks (all finite ones by
    default). The model is linear in a = A cos phi, b = -A sin phi, and c,
    so the fit is one least-squares solve; the standard errors come from the
    residual variance and the covariance of the solve."""
    t, v = np.asarray(t, dtype=float), np.asarray(v, dtype=float)
    keep = np.isfinite(v) if valid is None else np.asarray(valid) & np.isfinite(v)
    omega = 2.0 * math.pi * frequency_hz
    design = np.column_stack(
        [np.cos(omega * t[keep]), np.sin(omega * t[keep]), np.ones(keep.sum())]
    )
    used = int(keep.sum())
    if used <= 3:
        raise ValueError("a sine fit needs more than three valid samples")
    coefficients, *_ = np.linalg.lstsq(design, v[keep], rcond=None)
    a, b, c = coefficients
    residuals = v[keep] - design @ coefficients
    variance = float(residuals @ residuals) / (used - 3)
    covariance = variance * np.linalg.inv(design.T @ design)
    amplitude = math.hypot(a, b)
    # The errors of A and phi from those of a and b, to first order.
    gradient_amplitude = np.array([a, b]) / amplitude
    gradient_phase = np.array([b, -a]) / amplitude**2
    block = covariance[:2, :2]
    return SineFit(
        amplitude=amplitude,
        phase=math.atan2(-b, a),
        offset=float(c),
        amplitude_error=math.sqrt(gradient_amplitude @ block @ gradient_amplitude),
        phase_error=math.sqrt(gradient_phase @ block @ gradient_phase),
        offset_error=math.sqrt(covariance[2, 2]),
        residual_rms=math.sqrt(float(residuals @ residuals) / used),
        used=used,
    )


def valid_samples(
    v: NDArray[np.float64], full_scale_v: float, step_v: float = 0.0
) -> NDArray[np.bool_]:
    """The samples that carry information: not lost (finite), and inside the
    rails at plus and minus ``full_scale_v`` (V) by more than half a step
    ``step_v`` (V) of the converter. A sample at a rail says only that the
    voltage was there or beyond."""
    v = np.asarray(v, dtype=float)
    inside = np.abs(np.nan_to_num(v, nan=np.inf)) < full_scale_v - 0.5 * step_v
    return np.isfinite(v) & inside


@dataclass(frozen=True)
class Quality:
    """The flags of one channel of one capture. ``usable`` is the verdict:
    the record may be read for a number, with ``valid`` as its mask."""

    clipped_fraction: float
    missing_fraction: float
    samples_per_period: float
    calibrated: bool
    valid: NDArray[np.bool_]

    @property
    def flags(self) -> tuple[str, ...]:
        flags = []
        if self.clipped_fraction > 0:
            flags.append("clipped")
        if self.missing_fraction > 0:
            flags.append("samples missing")
        if self.samples_per_period <= 2.0:
            flags.append("below the Nyquist rate")
        if not self.calibrated:
            flags.append("not calibrated")
        return tuple(flags)

    @property
    def usable(self) -> bool:
        """Sampled above the Nyquist rate, calibrated, and with more than
        half of the samples valid."""
        return (
            self.samples_per_period > 2.0
            and self.calibrated
            and self.valid.mean() > 0.5
        )


def quality(
    v: NDArray[np.float64],
    sample_rate_hz: float,
    frequency_hz: float,
    full_scale_v: float,
    calibrated: bool,
    step_v: float = 0.0,
) -> Quality:
    """The quality flags of the samples ``v`` (V) of a sinusoid at
    ``frequency_hz`` sampled at ``sample_rate_hz``, recorded by a converter
    with rails at ``full_scale_v`` (V) and steps of ``step_v`` (V)."""
    v = np.asarray(v, dtype=float)
    finite = np.isfinite(v)
    at_rail = finite & (np.abs(np.nan_to_num(v)) >= full_scale_v - 0.5 * step_v)
    return Quality(
        clipped_fraction=float(at_rail.mean()),
        missing_fraction=float((~finite).mean()),
        samples_per_period=sample_rate_hz / frequency_hz,
        calibrated=calibrated,
        valid=valid_samples(v, full_scale_v, step_v),
    )


def calibrate(
    reference_v: NDArray[np.float64], recorded_v: NDArray[np.float64]
) -> tuple[float, float]:
    """The gain and the offset (V) of a channel that recorded ``recorded_v``
    when its probe saw the known voltages ``reference_v``: the straight line
    recorded = gain * reference + offset, by least squares over the finite
    samples."""
    reference_v = np.asarray(reference_v, dtype=float)
    recorded_v = np.asarray(recorded_v, dtype=float)
    keep = np.isfinite(recorded_v)
    gain, offset = np.polyfit(reference_v[keep], recorded_v[keep], 1)
    return float(gain), float(offset)


def correct(v: NDArray[np.float64], gain: float, offset: float) -> NDArray[np.float64]:
    """The voltages at the probe (V) from the recorded ones (V), undoing a
    calibrated gain and offset (V)."""
    return (np.asarray(v, dtype=float) - offset) / gain


def alias(frequency_hz: float, sample_rate_hz: float) -> float:
    """The frequency (Hz) at which a sinusoid at ``frequency_hz`` appears
    when it is sampled at ``sample_rate_hz``: its distance to the nearest
    whole multiple of the sample rate, between zero and half the rate."""
    return abs(frequency_hz - sample_rate_hz * round(frequency_hz / sample_rate_hz))


def dominant_frequency(v: NDArray[np.float64], sample_rate_hz: float) -> float:
    """The frequency (Hz) of the strongest component of the samples ``v``,
    read from the record alone, as one would without knowing the source:
    the peak of the spectrum of the record, zero-padded to 64 times its
    length, between zero and half the sample rate. Lost samples are set to
    the mean first."""
    v = np.asarray(v, dtype=float)
    v = np.where(np.isfinite(v), v, np.nanmean(v)) - np.nanmean(v)
    padded = 64 * len(v)
    spectrum = np.abs(np.fft.rfft(v, padded))
    frequencies = np.fft.rfftfreq(padded, 1.0 / sample_rate_hz)
    return float(frequencies[1 + int(np.argmax(spectrum[1:]))])
