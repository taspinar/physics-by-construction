"""The acquisition chain between a probe tip and a number (F142, the lesson
"Measurement quality and multimodal observations").

An ideal channel hands out the voltage at the probe. A real one passes it
through a probe and an amplifier (a gain and an offset, which a calibration
measures), a converter with a full scale (a voltage beyond its rails is
recorded as the rail: clipping) and a finite number of bits (quantisation),
and a link that can lose samples. ``ChannelChain`` models those steps in that
order; ``ImperfectChannels`` is a driver that wraps another driver and passes
its captures through one chain per channel, so that it is reached through an
``Instrument`` and passes the same contract tests as any adapter. A lost
sample is recorded as not a number, so that an analysis can tell it from a
measured zero.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from pbc.instruments.contract import SINE, Capture, Driver, driver_waveforms


@dataclass(frozen=True)
class ChannelChain:
    """One channel from the probe to the number: ``gain`` and ``offset_v``
    (V) of the probe and amplifier, the converter's ``full_scale_v`` (V; its
    rails are at plus and minus this voltage), and its ``bits`` (None for a
    converter without quantisation)."""

    gain: float = 1.0
    offset_v: float = 0.0
    full_scale_v: float = math.inf
    bits: int | None = None

    def __post_init__(self):
        if not self.gain > 0 or not self.full_scale_v > 0:
            raise ValueError("need a positive gain and a positive full scale")
        if self.bits is not None and (self.bits < 2 or math.isinf(self.full_scale_v)):
            raise ValueError(
                "a quantised converter has 2 or more bits and a full scale"
            )

    @property
    def step_v(self) -> float:
        """The voltage of one step of the converter (V), zero without
        quantisation."""
        if self.bits is None:
            return 0.0
        return 2.0 * self.full_scale_v / 2**self.bits

    def record(self, volts: NDArray[np.float64]) -> NDArray[np.float64]:
        """The numbers the converter writes for the voltages ``volts`` (V)
        at the probe: amplified, offset, held at the rails, quantised."""
        recorded = self.gain * np.asarray(volts, dtype=float) + self.offset_v
        recorded = np.clip(recorded, -self.full_scale_v, self.full_scale_v)
        if self.bits is not None:
            recorded = np.round(recorded / self.step_v) * self.step_v
            recorded = np.clip(recorded, -self.full_scale_v, self.full_scale_v)
        return recorded

    def describe(self) -> str:
        bits = "no quantisation" if self.bits is None else f"{self.bits} bits"
        return (
            f"gain {self.gain:g}, offset {self.offset_v:g} V,"
            f" full scale {self.full_scale_v:g} V, {bits}"
        )


@dataclass(frozen=True)
class Dropouts:
    """Samples the link loses: ``bursts`` runs of ``length`` samples per
    capture, at places drawn from a generator seeded with ``seed`` and the
    number of the capture."""

    bursts: int
    length: int
    seed: int = 0

    def lost(self, samples: int, capture: int) -> NDArray[np.bool_]:
        """Which of ``samples`` samples of capture number ``capture`` are lost."""
        lost = np.zeros(samples, dtype=bool)
        if self.bursts == 0 or self.length == 0:
            return lost
        rng = np.random.default_rng([self.seed, capture])
        for start in rng.integers(0, max(samples - self.length, 1), self.bursts):
            lost[start : start + self.length] = True
        return lost


class ImperfectChannels:
    """A driver that passes the captures of ``driver`` through one
    ``ChannelChain`` per channel and loses the samples of ``dropouts``.
    The calibration in its identity is the chains', since that is what a
    reader of its numbers needs to know."""

    def __init__(
        self,
        driver: Driver,
        chains: Mapping[str, ChannelChain],
        dropouts: Dropouts | None = None,
    ):
        self.driver = driver
        self.mode = driver.mode
        self.waveforms = driver_waveforms(driver)
        self.chains = dict(chains)
        self.dropouts = dropouts
        self._captures = 0

    def identity(self) -> Mapping[str, str]:
        identity = dict(self.driver.identity())
        chains = "; ".join(f"{k}: {c.describe()}" for k, c in self.chains.items())
        identity["calibration"] = f"channel chains, {chains}"
        if self.dropouts is not None:
            d = self.dropouts
            identity["dropouts"] = f"{d.bursts} bursts of {d.length} samples"
        return identity

    def set_output(
        self, amplitude_v: float, frequency_hz: float, waveform: str = SINE
    ) -> None:
        if waveform == SINE:
            self.driver.set_output(amplitude_v, frequency_hz)
        else:
            self.driver.set_output(amplitude_v, frequency_hz, waveform=waveform)  # type: ignore[call-arg]

    def output_off(self) -> None:
        self.driver.output_off()

    def capture(self, sample_rate_hz: float, samples: int) -> Capture:
        capture = self.driver.capture(sample_rate_hz, samples)
        lost = (
            np.zeros(samples, dtype=bool)
            if self.dropouts is None
            else self.dropouts.lost(samples, self._captures)
        )
        self._captures += 1
        channels = {}
        for name, values in capture.channels.items():
            chain = self.chains.get(name, ChannelChain())
            recorded = chain.record(np.asarray(values, dtype=float))
            recorded[lost] = np.nan
            channels[name] = recorded
        return Capture(capture.sample_rate_hz, capture.t, channels, capture.units)
