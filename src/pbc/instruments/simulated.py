"""The simulated adapter: a bench with a series RLC circuit (execution mode
*simulated*).

A function generator drives the circuit of ``pbc.electromagnetism.circuits``
with V cos(2 pi f t), switched on from rest; a two-channel oscilloscope
samples the source (channel ``source``) and the capacitor voltage (channel
``response``). Each acquisition integrates the state equations from the
moment the output was set, through a settling time of a number of decay
times 1 / alpha, and samples the record after it, with Gaussian noise of a
stated level drawn from a seeded generator. The same seed and the same
sequence of operations give the same samples.

The model is the physics layer; this module is only the adapter, and it is
reached only through ``pbc.instruments.Instrument``.
"""

from collections.abc import Mapping

import numpy as np

from pbc.electromagnetism.circuits import SeriesRLC, simulate
from pbc.instruments.contract import SIMULATED, Capture

# The circuit of EM5 ("RLC circuits and resonance"): L = 10 mH, C = 100 nF,
# with R = 100 ohm, so that f0 is about 5.03 kHz and Q about 3.16.
BENCH_CIRCUIT = SeriesRLC(resistance=100.0, inductance=10e-3, capacitance=100e-9)
NOISE_V = 0.002  # V, one standard deviation, on each channel
SETTLE_DECAYS = 12.0  # the transient falls by e^-12 before the record starts

UNITS = {"t": "s", "source": "V", "response": "V"}


class SimulatedRLCBench:
    """A driver over a deterministic model of the series RLC circuit."""

    mode = SIMULATED

    def __init__(
        self,
        circuit: SeriesRLC = BENCH_CIRCUIT,
        seed: int = 0,
        noise_v: float = NOISE_V,
        settle_decays: float = SETTLE_DECAYS,
    ):
        if noise_v < 0 or settle_decays <= 0:
            raise ValueError("need noise_v >= 0 and settle_decays > 0")
        self.circuit = circuit
        self.seed = seed
        self.noise_v = noise_v
        self.settle_decays = settle_decays
        self._amplitude = 0.0
        self._frequency = 0.0
        self._captures = 0

    def identity(self) -> Mapping[str, str]:
        c = self.circuit
        return {
            "device": "simulated bench: function generator, series RLC,"
            " two-channel oscilloscope",
            "model": "pbc.electromagnetism.circuits.SeriesRLC with simulate",
            "resistance_ohm": f"{c.resistance:g}",
            "inductance_h": f"{c.inductance:g}",
            "capacitance_f": f"{c.capacitance:g}",
            "noise_v": f"{self.noise_v:g}",
            "seed": str(self.seed),
            "calibration": "ideal channels: gain 1, no offset, no delay",
        }

    def set_output(self, amplitude_v: float, frequency_hz: float) -> None:
        self._amplitude = float(amplitude_v)
        self._frequency = float(frequency_hz)

    def output_off(self) -> None:
        self._amplitude = 0.0

    def capture(self, sample_rate_hz: float, samples: int) -> Capture:
        record = np.arange(samples) / sample_rate_hz
        rng = np.random.default_rng([self.seed, self._captures])
        self._captures += 1
        if self._amplitude == 0.0:
            source = np.zeros(samples)
            response = np.zeros(samples)
        else:
            amplitude, omega = self._amplitude, 2.0 * np.pi * self._frequency
            settle = self.settle_decays / self.circuit.damping_rate
            times = np.concatenate([[0.0], settle + record])
            charge, _ = simulate(
                self.circuit, lambda t: amplitude * np.cos(omega * t), times
            )
            source = amplitude * np.cos(omega * times[1:])
            response = charge[1:] / self.circuit.capacitance
        return Capture(
            sample_rate_hz=sample_rate_hz,
            t=record,
            channels={
                "source": source + rng.normal(0.0, self.noise_v, samples),
                "response": response + rng.normal(0.0, self.noise_v, samples),
            },
            units=UNITS,
        )
