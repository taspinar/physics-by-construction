"""The measurement-quality gate of the Autonomous Physics Lab (F145): every
capture of every protocol passes it before a number is read from it.

The flags are those of ``pbc.electromagnetism.measurement.quality`` (F142):
samples at the converter's rails (clipped), samples lost, a sample rate at
or below twice the highest frequency the protocol reads (Nyquist), and a
channel whose calibration is not declared. The gate adds one of its own:
the source channel must carry the excitation that was set (a probe that is
off the generator reads noise, and a gain from it is meaningless).

A capture that fails the gate is invalid: it is recorded with its flags and
its raw samples, exported, counted, and never fitted. The gate is stricter
than F142's ``usable`` (more than half of the samples valid): a clipped
sample biases an amplitude or a ring-down fit, so any clipping is invalid,
and lost samples are tolerated only up to ``MAX_MISSING``.
"""

import math
from dataclasses import dataclass

import numpy as np

from pbc.electromagnetism.measurement import quality
from pbc.instruments import LIVE, SINE, Capture

CHANNELS = ("source", "response")
# The fraction of lost samples a capture may have and still be read; the
# lost ones are left out of the fit.
MAX_MISSING = 0.01
# The source channel carries the excitation when its swing is at least this
# fraction of the one that was set.
MIN_SOURCE_FRACTION = 0.5


@dataclass(frozen=True)
class Rails:
    """The full scale of each channel's converter, ``source_v`` (V) and
    ``response_v`` (V): a sample at plus or minus it is clipped."""

    source_v: float = math.inf
    response_v: float = math.inf

    def of(self, channel: str) -> float:
        return self.source_v if channel == "source" else self.response_v


# The simulated bench has ideal channels. The Analog Discovery 3 reads the
# source on its 5 V range and the response on its 50 V range, peak to peak
# (pbc.instruments.analog_discovery, which the product does not import at
# module level; a unit test compares the numbers).
IDEAL_RAILS = Rails()
LIVE_RAILS = Rails(source_v=2.5, response_v=25.0)


def rails_for(mode: str) -> Rails:
    """The rails of the execution mode: the device's for a live run and for
    the replay of its export, ideal otherwise."""
    return LIVE_RAILS if mode == LIVE else IDEAL_RAILS


@dataclass(frozen=True)
class Verdict:
    """What the gate found in one capture: ``valid``, the flags of each
    channel, the reasons it is invalid, and each channel's mask of the
    samples a fit may use."""

    valid: bool
    flags: dict[str, tuple[str, ...]]
    reasons: tuple[str, ...]
    masks: dict[str, np.ndarray]

    def to_dict(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "flags": {k: list(v) for k, v in self.flags.items()},
            "reasons": list(self.reasons),
        }


def gate(
    capture: Capture,
    amplitude_v: float,
    highest_hz: float,
    rails: Rails = IDEAL_RAILS,
    waveform: str = SINE,
    calibrated: bool = True,
) -> Verdict:
    """The gate's verdict on ``capture``, made with the excitation of
    ``amplitude_v`` (V) and ``waveform``; ``highest_hz`` (Hz) is the highest
    frequency the protocol reads from it (the excitation for a point of the
    frequency response, three times it for the third harmonic, the ringing
    for a ring-down)."""
    flags: dict[str, tuple[str, ...]] = {}
    masks: dict[str, np.ndarray] = {}
    reasons: list[str] = []
    # region: gate
    for name in CHANNELS:
        v = np.asarray(capture.channels[name], dtype=float)
        q = quality(v, capture.sample_rate_hz, highest_hz, rails.of(name), calibrated)
        flags[name] = q.flags
        masks[name] = q.valid
        if q.clipped_fraction > 0:
            reasons.append(f"{name} clipped ({q.clipped_fraction:.1%} at the rails)")
        if q.missing_fraction > MAX_MISSING:
            reasons.append(f"{name} lost {q.missing_fraction:.1%} of its samples")
        if q.samples_per_period <= 2.0:
            reasons.append(
                f"{name} sampled at {q.samples_per_period:.2f} samples per period"
                f" of {highest_hz:g} Hz, at or below the Nyquist rate"
            )
        if not q.calibrated:
            reasons.append(f"{name} not calibrated")
    source = np.asarray(capture.channels["source"], dtype=float)[masks["source"]]
    swing = _swing(source, waveform)
    if not swing >= MIN_SOURCE_FRACTION * amplitude_v:
        reasons.append(
            f"the source channel swings {swing:.3g} V, not the {amplitude_v:g} V"
            " set: the probe is not on the generator, or the output is off"
        )
    # endregion: gate
    return Verdict(not reasons, flags, tuple(reasons), masks)


def _swing(source: np.ndarray, waveform: str) -> float:
    """The amplitude the source channel shows (V): half the spread between
    its 2nd and 98th percentiles for a sine, the whole spread for the square
    wave, which steps from 0 V to the amplitude."""
    if len(source) < 4:
        return 0.0
    low, high = np.percentile(source, [2.0, 98.0])
    spread = float(high - low)
    return spread / 2.0 if waveform == SINE else spread
