"""The simulated adapter: a bench with a series RLC circuit (execution mode
*simulated*).

A function generator drives the circuit of ``pbc.electromagnetism.circuits``
with V cos(2 pi f t), or with a square wave that steps between 0 V and V
(high for the first half of each period, F145), switched on from rest; a
two-channel oscilloscope
samples the source (channel ``source``) and the capacitor voltage (channel
``response``). Each acquisition integrates the state equations from the
moment the output was set, through a settling time of a number of decay
times 1 / alpha, and samples the record after it, with Gaussian noise of a
stated level drawn from a seeded generator. The same seed and the same
sequence of operations give the same samples. A square drive is integrated
piece by piece between its edges, the state carried across each edge, so
that no edge falls inside an integration step.

``SimulatedLEDBench`` is the bench of the nonlinear protocol (F145): the
generator drives two LEDs in anti-parallel behind a series resistor
(``pbc.electromagnetism.led_pair``), and channel ``response`` reads the
pair's voltage.

The model is the physics layer; this module is only the adapter, and it is
reached only through ``pbc.instruments.Instrument``.
"""

from collections.abc import Mapping

import numpy as np

from pbc.electromagnetism.circuits import SeriesRLC, simulate
from pbc.electromagnetism.led_pair import LEDPair
from pbc.instruments.contract import SIMULATED, SINE, SQUARE, Capture

# The circuit of EM5 ("RLC circuits and resonance"): L = 10 mH, C = 100 nF,
# with R = 100 ohm, so that f0 is about 5.03 kHz and Q about 3.16.
BENCH_CIRCUIT = SeriesRLC(resistance=100.0, inductance=10e-3, capacitance=100e-9)
NOISE_V = 0.002  # V, one standard deviation, on each channel
SETTLE_DECAYS = 12.0  # the transient falls by e^-12 before the record starts

UNITS = {"t": "s", "source": "V", "response": "V"}


class SimulatedRLCBench:
    """A driver over a deterministic model of the series RLC circuit."""

    mode = SIMULATED
    waveforms = (SINE, SQUARE)

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
        self._waveform = SINE
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

    def set_output(
        self, amplitude_v: float, frequency_hz: float, waveform: str = SINE
    ) -> None:
        if waveform not in self.waveforms:
            raise ValueError(f"the simulated bench has no waveform {waveform!r}")
        self._amplitude = float(amplitude_v)
        self._frequency = float(frequency_hz)
        self._waveform = waveform

    def output_off(self) -> None:
        self._amplitude = 0.0

    def capture(self, sample_rate_hz: float, samples: int) -> Capture:
        record = np.arange(samples) / sample_rate_hz
        rng = np.random.default_rng([self.seed, self._captures])
        self._captures += 1
        if self._amplitude == 0.0:
            source = np.zeros(samples)
            response = np.zeros(samples)
        elif self._waveform == SQUARE:
            settle = self.settle_decays / self.circuit.damping_rate
            times = settle + record
            source = square_wave(self._amplitude, self._frequency, times)
            charge, current = self._square_response(times)
            response = self._probe(charge, current)
        else:
            amplitude, omega = self._amplitude, 2.0 * np.pi * self._frequency
            settle = self.settle_decays / self.circuit.damping_rate
            times = np.concatenate([[0.0], settle + record])
            charge, current = simulate(
                self.circuit, lambda t: amplitude * np.cos(omega * t), times
            )
            source = amplitude * np.cos(omega * times[1:])
            response = self._probe(charge[1:], current[1:])
        return Capture(
            sample_rate_hz=sample_rate_hz,
            t=record,
            channels={
                "source": source + rng.normal(0.0, self.noise_v, samples),
                "response": response + rng.normal(0.0, self.noise_v, samples),
            },
            units=UNITS,
        )

    def _square_response(self, times: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """The charge (C) and the current (A) at ``times`` (s, from the
        moment the output was set) under the square drive: integrated from
        rest over each half period at its constant level in turn."""
        half = 0.5 / self._frequency
        charge = np.empty(len(times))
        current = np.empty(len(times))
        state = (0.0, 0.0)
        edge = 0
        while edge * half <= times[-1]:  # a sample on the last edge too
            start, end = edge * half, (edge + 1) * half
            level = self._amplitude if edge % 2 == 0 else 0.0
            inside = (times >= start) & (times < end)
            grid = np.unique(np.concatenate([[start], times[inside], [end]]))
            q, i = simulate(
                self.circuit, lambda t, v=level: v, grid, state[0], state[1]
            )
            at = np.searchsorted(grid, times[inside])
            charge[inside], current[inside] = q[at], i[at]
            state = (float(q[-1]), float(i[-1]))
            edge += 1
        return charge, current

    def _probe(self, charge: np.ndarray, current: np.ndarray) -> np.ndarray:
        """The voltage the response probe reads (V): across the capacitor."""
        return charge / self.circuit.capacitance


def square_wave(
    amplitude_v: float, frequency_hz: float, times: np.ndarray
) -> np.ndarray:
    """The square wave of the contract at ``times`` (s, from the moment the
    output was set): ``amplitude_v`` (V) for the first half of each period
    at ``frequency_hz`` (Hz), 0 V for the second."""
    phase = np.mod(np.asarray(times, dtype=float) * frequency_hz, 1.0)
    return np.where(phase < 0.5, amplitude_v, 0.0)


class ResistorProbeBench(SimulatedRLCBench):
    """The same bench with the response probe moved from the capacitor to
    the resistor: channel ``response`` reads R i (F142, the still-image
    exercise of "Measurement quality and multimodal observations")."""

    def identity(self) -> Mapping[str, str]:
        return {**super().identity(), "probe": "response across the resistor"}

    def _probe(self, charge: np.ndarray, current: np.ndarray) -> np.ndarray:
        """The voltage the response probe reads (V): across the resistor."""
        return self.circuit.resistance * current


# The LED pair of F145's nonlinear protocol: two red LEDs in anti-parallel
# behind 100 ohm; the pair passes 1 mA at about 1.67 V and 10 mA at about
# 1.79 V, typical of a red 5 mm LED.
LED_BENCH_PAIR = LEDPair(resistance=100.0, saturation_current=1e-17, ideality=2.0)


class SimulatedLEDBench:
    """A driver over a deterministic model of the LED pair behind its series
    resistor (``pbc.electromagnetism.led_pair``): channel ``source`` reads
    the generator, channel ``response`` the pair's voltage, each with
    Gaussian noise from a seeded generator. The circuit is memoryless, so
    there is no settling; it takes a sine only."""

    mode = SIMULATED
    waveforms = (SINE,)

    def __init__(
        self, pair: LEDPair = LED_BENCH_PAIR, seed: int = 0, noise_v: float = NOISE_V
    ):
        if noise_v < 0:
            raise ValueError("need noise_v >= 0")
        self.pair = pair
        self.seed = seed
        self.noise_v = noise_v
        self._amplitude = 0.0
        self._frequency = 0.0
        self._captures = 0

    def identity(self) -> Mapping[str, str]:
        p = self.pair
        return {
            "device": "simulated bench: function generator, series resistor and"
            " two LEDs in anti-parallel, two-channel oscilloscope",
            "model": "pbc.electromagnetism.led_pair.LEDPair",
            "resistance_ohm": f"{p.resistance:g}",
            "saturation_current_a": f"{p.saturation_current:g}",
            "ideality": f"{p.ideality:g}",
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
        t = np.arange(samples) / sample_rate_hz
        rng = np.random.default_rng([self.seed, self._captures])
        self._captures += 1
        source = self._amplitude * np.cos(2.0 * np.pi * self._frequency * t)
        response = self.pair.pair_voltage(source)
        return Capture(
            sample_rate_hz=sample_rate_hz,
            t=t,
            channels={
                "source": source + rng.normal(0.0, self.noise_v, samples),
                "response": response + rng.normal(0.0, self.noise_v, samples),
            },
            units=UNITS,
        )
