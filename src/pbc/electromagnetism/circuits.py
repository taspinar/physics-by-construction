"""The series RLC circuit: its transient in time and its response in
frequency.

A resistor R, an inductor L, and a capacitor C in series with a source V(t)
carry one current i = dq/dt, where q is the charge on the capacitor.
Kirchhoff's voltage law around the loop is

    L di/dt + R i + q / C = V(t).

The module integrates these state equations in time (``simulate``) and, apart
from that, gives the closed forms they are compared with: the response to a
step of the source in each damping regime, and the steady response to a
sinusoidal source through the complex impedance Z = R + j (omega L -
1 / (omega C)). ``steady_phasor`` reads the amplitude and phase of a
simulated signal by projecting it on a cosine and a sine over whole periods.

Quantities are in SI units: R in ohm, L in H, C in F, charges in C, currents
in A, voltages in V, times in s, angular frequencies in rad/s.
"""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.integrate import solve_ivp

Array = NDArray[np.float64]

__all__ = [
    "SeriesRLC",
    "simulate",
    "steady_phasor",
    "step_response",
]

# Relative tolerance of the integrator: the simulation is then accurate far
# beyond the differences the lesson discusses.
RTOL = 1e-11


@dataclass(frozen=True)
class SeriesRLC:
    """A series RLC circuit."""

    resistance: float  # ohm
    inductance: float  # H
    capacitance: float  # F

    def __post_init__(self) -> None:
        if self.resistance < 0 or self.inductance <= 0 or self.capacitance <= 0:
            raise ValueError("need R >= 0 and positive L and C")

    @property
    def natural_frequency(self) -> float:
        """omega_0 = 1 / sqrt(L C), rad/s: the resonance of the current."""
        return 1.0 / np.sqrt(self.inductance * self.capacitance)

    @property
    def damping_rate(self) -> float:
        """alpha = R / (2 L), 1/s: the decay rate of a free oscillation."""
        return self.resistance / (2.0 * self.inductance)

    @property
    def quality_factor(self) -> float:
        """Q = omega_0 L / R = sqrt(L / C) / R."""
        return np.sqrt(self.inductance / self.capacitance) / self.resistance

    @property
    def critical_resistance(self) -> float:
        """The resistance 2 sqrt(L / C), ohm, at which alpha = omega_0."""
        return 2.0 * np.sqrt(self.inductance / self.capacitance)

    @property
    def regime(self) -> str:
        """``underdamped``, ``critical``, or ``overdamped``, by alpha against
        omega_0 to a relative 1e-12."""
        ratio = self.damping_rate / self.natural_frequency
        if abs(ratio - 1.0) <= 1e-12:
            return "critical"
        return "underdamped" if ratio < 1.0 else "overdamped"

    def impedance(self, omega: ArrayLike) -> NDArray[np.complex128]:
        """Z = R + j (omega L - 1 / (omega C)), ohm."""
        omega = np.asarray(omega, dtype=float)
        return self.resistance + 1j * (
            omega * self.inductance - 1.0 / (omega * self.capacitance)
        )

    def current_phasor(
        self, voltage: float, omega: ArrayLike
    ) -> NDArray[np.complex128]:
        """The complex amplitude of the steady current, A, for the source
        voltage * cos(omega t): I = V / Z."""
        return voltage / self.impedance(omega)

    def capacitor_phasor(
        self, voltage: float, omega: ArrayLike
    ) -> NDArray[np.complex128]:
        """The complex amplitude of the steady capacitor voltage, V:
        I / (j omega C)."""
        omega = np.asarray(omega, dtype=float)
        return self.current_phasor(voltage, omega) / (1j * omega * self.capacitance)


def simulate(
    circuit: SeriesRLC,
    source: Callable[[float], float],
    t: ArrayLike,
    charge: float = 0.0,
    current: float = 0.0,
) -> tuple[Array, Array]:
    """The charge (C) and the current (A) at the times ``t`` (s, increasing,
    from the start), from the state equations dq/dt = i,
    L di/dt = V(t) - R i - q / C, integrated by an eighth-order Runge-Kutta
    method with error control (SciPy's DOP853)."""
    t = np.asarray(t, dtype=float)
    L, R, C = circuit.inductance, circuit.resistance, circuit.capacitance

    def rates(time: float, state: Array) -> list[float]:
        q, i = state
        return [i, (source(time) - R * i - q / C) / L]

    period = 2.0 * np.pi / circuit.natural_frequency
    solution = solve_ivp(
        rates,
        (t[0], t[-1]),
        [charge, current],
        method="DOP853",
        t_eval=t,
        rtol=RTOL,
        atol=RTOL * max(abs(charge), C * abs(source(t[0])), 1e-30),
        max_step=period / 20.0,
    )
    if not solution.success:
        raise RuntimeError(solution.message)
    return solution.y[0], solution.y[1]


def step_response(circuit: SeriesRLC, voltage: float, t: ArrayLike) -> Array:
    """The capacitor voltage, V, of the circuit at rest when the source steps
    to ``voltage`` at t = 0, in closed form for its damping regime:

    - underdamped, with omega_d = sqrt(omega_0^2 - alpha^2):
      V (1 - e^(-alpha t) (cos omega_d t + (alpha / omega_d) sin omega_d t));
    - critical: V (1 - e^(-alpha t) (1 + alpha t));
    - overdamped, with the rates s_1, s_2 = -alpha +- sqrt(alpha^2 - omega_0^2):
      V (1 + (s_2 e^(s_1 t) - s_1 e^(s_2 t)) / (s_1 - s_2)).
    """
    t = np.asarray(t, dtype=float)
    alpha, omega0 = circuit.damping_rate, circuit.natural_frequency
    regime = circuit.regime
    if regime == "underdamped":
        wd = np.sqrt(omega0**2 - alpha**2)
        decay = np.exp(-alpha * t) * (np.cos(wd * t) + alpha / wd * np.sin(wd * t))
        return voltage * (1.0 - decay)
    if regime == "critical":
        return voltage * (1.0 - np.exp(-alpha * t) * (1.0 + alpha * t))
    root = np.sqrt(alpha**2 - omega0**2)
    s1, s2 = -alpha + root, -alpha - root
    return voltage * (1.0 + (s2 * np.exp(s1 * t) - s1 * np.exp(s2 * t)) / (s1 - s2))


def steady_phasor(signal: ArrayLike, t: ArrayLike, omega: float) -> complex:
    """The complex amplitude A e^(j phi) of a signal A cos(omega t + phi),
    sampled at the equally spaced times ``t`` that span a whole number of
    periods: 2 / T times the integral of the signal times e^(-j omega t),
    by the trapezoidal rule (exact for a sinusoid on a periodic grid)."""
    signal, t = np.asarray(signal, dtype=float), np.asarray(t, dtype=float)
    span = t[-1] - t[0]
    periods = span * omega / (2.0 * np.pi)
    if abs(periods - round(periods)) > 1e-9 * max(periods, 1.0) or round(periods) < 1:
        raise ValueError("the samples must span a whole number of periods")
    # The trapezoidal rule over a whole period: the last sample repeats the
    # first, so it is left out and the rest are weighted equally.
    values = signal[:-1] * np.exp(-1j * omega * t[:-1])
    return complex(2.0 * values.mean())
