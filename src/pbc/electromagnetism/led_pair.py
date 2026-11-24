"""Two LEDs of one colour in anti-parallel behind a series resistor: the
bounded nonlinear circuit of the Autonomous Physics Lab (F145).

Each LED is a diode with the Shockley characteristic
i = I_s (e^(v / (n V_T)) - 1); in anti-parallel the two pass

    i(v) = 2 I_s sinh(v / (n V_T)),

an odd function, so a sinusoidal source gives odd harmonics only. With the
series resistor R the source voltage is shared, v_s = R i + v, and the
pair's voltage v follows from v_s alone at every instant (no capacitance at
the frequencies of the protocol): the circuit is memoryless. Below about
1.5 V a red LED passes almost nothing and the pair's voltage follows the
source; above it the pair holds its voltage near the forward voltage and
the rest falls across R. The current is never above |v_s| / R.

``pair_voltage`` solves v + R i(v) = v_s by bisection, sample by sample;
``characteristic_voltage`` is the inverse characteristic
v = n V_T asinh(i / (2 I_s)).
"""

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

# The thermal voltage k T / q at 300 K (V).
THERMAL_VOLTAGE_V = 0.025852
BISECTIONS = 100


@dataclass(frozen=True)
class LEDPair:
    """The circuit: ``resistance`` (ohm) in series with two LEDs in
    anti-parallel, each of saturation current ``saturation_current``
    (A) and ideality factor ``ideality`` (dimensionless), at the thermal
    voltage ``thermal_voltage`` (V)."""

    resistance: float = 100.0
    saturation_current: float = 1e-18
    ideality: float = 2.0
    thermal_voltage: float = THERMAL_VOLTAGE_V

    def __post_init__(self):
        if not (
            self.resistance > 0
            and self.saturation_current > 0
            and self.ideality > 0
            and self.thermal_voltage > 0
        ):
            raise ValueError("every parameter of the LED pair must be positive")

    @property
    def slope_voltage(self) -> float:
        """n V_T (V): the voltage over which the current grows by e."""
        return self.ideality * self.thermal_voltage

    def current(self, v: ArrayLike) -> NDArray[np.float64]:
        """The current (A) through the pair at the voltage ``v`` (V)."""
        return (
            2.0
            * self.saturation_current
            * np.sinh(np.asarray(v, dtype=float) / self.slope_voltage)
        )

    def characteristic_voltage(self, i: ArrayLike) -> NDArray[np.float64]:
        """The pair's voltage (V) at the current ``i`` (A)."""
        return self.slope_voltage * np.arcsinh(
            np.asarray(i, dtype=float) / (2.0 * self.saturation_current)
        )

    def pair_voltage(self, source_v: ArrayLike) -> NDArray[np.float64]:
        """The pair's voltage (V) for the source voltages ``source_v`` (V):
        the root of v + R i(v) - v_s, which lies between 0 and v_s, found
        by bisection to the precision of the floating-point numbers."""
        vs = np.asarray(source_v, dtype=float)
        low = np.minimum(vs, 0.0)
        high = np.maximum(vs, 0.0)
        for _ in range(BISECTIONS):
            middle = 0.5 * (low + high)
            above = middle + self.resistance * self.current(middle) > vs
            high = np.where(above, middle, high)
            low = np.where(above, low, middle)
        return 0.5 * (low + high)

    def forward_voltage(self, current_a: float) -> float:
        """The voltage (V) at which the pair passes ``current_a`` (A)."""
        return float(self.characteristic_voltage(current_a))


def harmonics(
    pair: LEDPair,
    amplitude_v: float,
    orders: tuple[int, ...] = (1, 3),
    points: int = 4096,
) -> dict[int, float]:
    """The amplitudes (V) of the harmonics ``orders`` of the pair's voltage
    under the source amplitude_v cos(theta), over one period sampled at
    ``points`` phases: the steady response of the memoryless circuit."""
    theta = 2.0 * math.pi * np.arange(points) / points
    v = pair.pair_voltage(amplitude_v * np.cos(theta))
    spectrum = np.fft.rfft(v) * 2.0 / points
    return {n: float(abs(spectrum[n])) for n in orders}
