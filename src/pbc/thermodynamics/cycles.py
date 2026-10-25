"""Ideal-gas heat engines as closed paths in the p-V plane.

A leg of a cycle is a quasi-static path of an ideal gas, sampled at points of
volume V (m^3) and temperature T (K); the pressure is p = n R T / V (Pa). Along
a leg the work done by the gas is the integral of p dV and the heat taken in is
the integral of T dS, with S the entropy of the ideal gas, both by the
trapezoidal rule over the samples. The internal energy n c_v T is a function
of the state. The first law, Q = dU + W, is then a check between two
integrals and a state function, not an identity of the code.

A cycle is a list of legs, each starting where the one before it ends. An
ideal regenerator stores the heat of the legs it is attached to and gives it
back within the cycle; those legs exchange no heat with the reservoirs.
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

Array = NDArray[np.float64]

R = 8.314462618  # J/(mol K), the molar gas constant


@dataclass(frozen=True)
class Gas:
    """An ideal gas of ``moles`` mol with the molar heat capacity at constant
    volume ``cv`` (J/(mol K)); 5/2 R for a diatomic gas such as air near room
    temperature."""

    moles: float = 1.0
    cv: float = 2.5 * R

    @property
    def gamma(self) -> float:
        """The ratio of the heat capacities, c_p / c_v = (c_v + R) / c_v."""
        return (self.cv + R) / self.cv

    def pressure(self, volume: Array, temperature: Array) -> Array:
        """n R T / V (Pa)."""
        return self.moles * R * np.asarray(temperature) / np.asarray(volume)

    def internal_energy(self, temperature: Array) -> Array:
        """n c_v T (J), counted from T = 0."""
        return self.moles * self.cv * np.asarray(temperature)

    def entropy(self, volume: Array, temperature: Array) -> Array:
        """n c_v ln T + n R ln V (J/K), up to a constant that cancels in every
        difference."""
        return self.moles * (
            self.cv * np.log(np.asarray(temperature)) + R * np.log(np.asarray(volume))
        )


@dataclass(frozen=True)
class Leg:
    """A sampled quasi-static path: its name, volumes (m^3), temperatures (K),
    and whether a regenerator takes its heat."""

    name: str
    volume: Array
    temperature: Array
    regenerated: bool = False


def isotherm(name: str, temperature: float, v1: float, v2: float, points: int) -> Leg:
    """From V1 to V2 at constant temperature."""
    v = np.linspace(v1, v2, points)
    return Leg(name, v, np.full(points, float(temperature)))


def adiabat(gas: Gas, name: str, v1: float, t1: float, v2: float, points: int) -> Leg:
    """From (V1, T1) to V2 without heat: T V^(gamma - 1) stays constant."""
    v = np.linspace(v1, v2, points)
    return Leg(name, v, t1 * (v1 / v) ** (gas.gamma - 1.0))


def isochore(
    name: str, volume: float, t1: float, t2: float, points: int, regenerated=False
) -> Leg:
    """From T1 to T2 at constant volume."""
    return Leg(
        name, np.full(points, float(volume)), np.linspace(t1, t2, points), regenerated
    )


def isobar(
    gas: Gas, name: str, pressure: float, t1: float, t2: float, points: int
) -> Leg:
    """From T1 to T2 at constant pressure: V = n R T / p."""
    t = np.linspace(t1, t2, points)
    return Leg(name, gas.moles * R * t / pressure, t)


def trapezoid(y: Array, x: Array) -> Array:
    """The increments of the trapezoidal rule, (y_k + y_k+1) / 2 (x_k+1 - x_k)."""
    return 0.5 * (y[1:] + y[:-1]) * np.diff(x)


def work(gas: Gas, leg: Leg) -> float:
    """The work done by the gas, the integral of p dV along the leg (J)."""
    p = gas.pressure(leg.volume, leg.temperature)
    return float(trapezoid(p, leg.volume).sum())


def heat_increments(gas: Gas, leg: Leg) -> Array:
    """The heat taken in over each interval of the leg, T dS by the
    trapezoidal rule (J)."""
    s = gas.entropy(leg.volume, leg.temperature)
    return trapezoid(leg.temperature, s)


def heat(gas: Gas, leg: Leg) -> float:
    """The heat taken in along the leg, the integral of T dS (J)."""
    return float(heat_increments(gas, leg).sum())


def energy_change(gas: Gas, leg: Leg) -> float:
    """The change of the internal energy from the start to the end of the leg
    (J)."""
    return float(
        gas.internal_energy(leg.temperature[-1])
        - gas.internal_energy(leg.temperature[0])
    )


@dataclass(frozen=True)
class Balance:
    """The energy and entropy balance of a cycle (J and J/K): the net work,
    the heat taken from and given to the reservoirs, the residual of the first
    law, and the entropy that the reservoirs at ``hot`` and ``cold`` gain."""

    work: float
    heat_in: float
    heat_out: float
    first_law_residual: float
    reservoir_entropy: float

    @property
    def efficiency(self) -> float:
        """The net work over the heat taken in."""
        return self.work / self.heat_in


def balance(gas: Gas, legs: list[Leg], hot: float, cold: float) -> Balance:
    """The balance of a closed cycle that takes its heat from a reservoir at
    ``hot`` and gives it to one at ``cold`` (K). Heat in and out are summed
    interval by interval, so a leg that takes heat in part and gives it in
    part is counted right; regenerated legs are left out of both."""
    for first, second in zip(legs, legs[1:] + legs[:1], strict=True):
        if not (
            np.isclose(first.volume[-1], second.volume[0], rtol=1e-12)
            and np.isclose(first.temperature[-1], second.temperature[0], rtol=1e-12)
        ):
            raise ValueError(
                f"the leg {second.name!r} does not start where {first.name!r} ends"
            )
    w = sum(work(gas, leg) for leg in legs)
    q = np.concatenate(
        [heat_increments(gas, leg) for leg in legs if not leg.regenerated]
    )
    heat_in = float(q[q > 0.0].sum())
    heat_out = float(-q[q < 0.0].sum())
    regenerated = sum(heat(gas, leg) for leg in legs if leg.regenerated)
    residual = heat_in - heat_out + regenerated - w
    entropy = reservoir_entropy(heat_in, heat_out, hot, cold)
    return Balance(w, heat_in, heat_out, residual, entropy)


def carnot_efficiency(hot: float, cold: float) -> float:
    """1 - T_cold / T_hot, the bound on the efficiency of every engine between
    two reservoirs."""
    return 1.0 - cold / hot


def otto_efficiency(gas: Gas, ratio: float) -> float:
    """1 - r^(1 - gamma), the efficiency of the ideal Otto cycle of
    compression ratio r."""
    return 1.0 - ratio ** (1.0 - gas.gamma)


def brayton_efficiency(gas: Gas, pressure_ratio: float) -> float:
    """1 - r_p^((1 - gamma) / gamma), the efficiency of the ideal Brayton
    cycle of pressure ratio r_p."""
    return 1.0 - pressure_ratio ** ((1.0 - gas.gamma) / gas.gamma)


def carnot(gas: Gas, hot: float, cold: float, v1: float, expansion: float, points: int):
    """The Carnot cycle: isothermal expansion at ``hot`` from V1 by the factor
    ``expansion``, adiabatic expansion to ``cold``, isothermal compression, and
    adiabatic compression back."""
    factor = (hot / cold) ** (1.0 / (gas.gamma - 1.0))
    v2 = v1 * expansion
    v3, v4 = v2 * factor, v1 * factor
    return [
        isotherm("isothermal expansion", hot, v1, v2, points),
        adiabat(gas, "adiabatic expansion", v2, hot, v3, points),
        isotherm("isothermal compression", cold, v3, v4, points),
        adiabat(gas, "adiabatic compression", v4, cold, v1, points),
    ]


def otto(gas: Gas, hot: float, cold: float, v_max: float, ratio: float, points: int):
    """The ideal Otto cycle between the extreme temperatures: adiabatic
    compression from (V_max, cold) by the ratio r, heating at constant volume
    to ``hot``, adiabatic expansion back to V_max, cooling at constant volume
    to ``cold``. Needs cold r^(gamma - 1) <= hot."""
    v_min = v_max / ratio
    t2 = cold * ratio ** (gas.gamma - 1.0)
    if t2 > hot:
        raise ValueError(
            "the compression alone would heat the gas above the hot reservoir"
        )
    t4 = hot / ratio ** (gas.gamma - 1.0)
    return [
        adiabat(gas, "adiabatic compression", v_max, cold, v_min, points),
        isochore("heating at constant volume", v_min, t2, hot, points),
        adiabat(gas, "adiabatic expansion", v_min, hot, v_max, points),
        isochore("cooling at constant volume", v_max, t4, cold, points),
    ]


def stirling(
    gas: Gas,
    hot: float,
    cold: float,
    v_max: float,
    ratio: float,
    points: int,
    regenerator: bool,
):
    """The ideal Stirling cycle: isothermal compression at ``cold`` from V_max
    by the ratio r, heating at constant volume to ``hot``, isothermal
    expansion, cooling at constant volume. With an ideal ``regenerator`` the
    heat of cooling is stored and gives the heating, so only the isotherms
    exchange heat with the reservoirs."""
    v_min = v_max / ratio
    return [
        isotherm("isothermal compression", cold, v_max, v_min, points),
        isochore("heating at constant volume", v_min, cold, hot, points, regenerator),
        isotherm("isothermal expansion", hot, v_min, v_max, points),
        isochore("cooling at constant volume", v_max, hot, cold, points, regenerator),
    ]


def brayton(
    gas: Gas, hot: float, cold: float, p_min: float, pressure_ratio: float, points: int
):
    """The ideal Brayton (Joule) cycle: adiabatic compression from (p_min,
    cold) by the pressure ratio r_p, heating at constant pressure to ``hot``,
    adiabatic expansion back to p_min, cooling at constant pressure."""
    exponent = (gas.gamma - 1.0) / gas.gamma
    t2 = cold * pressure_ratio**exponent
    if t2 > hot:
        raise ValueError(
            "the compression alone would heat the gas above the hot reservoir"
        )
    t4 = hot / pressure_ratio**exponent
    p_max = p_min * pressure_ratio
    v1 = gas.moles * R * cold / p_min
    v2 = gas.moles * R * t2 / p_max
    v3 = gas.moles * R * hot / p_max
    v4 = gas.moles * R * t4 / p_min
    return [
        adiabat(gas, "adiabatic compression", v1, cold, v2, points),
        isobar(gas, "heating at constant pressure", p_max, t2, hot, points),
        adiabat(gas, "adiabatic expansion", v3, hot, v4, points),
        isobar(gas, "cooling at constant pressure", p_min, t4, cold, points),
    ]


def reservoir_entropy(
    heat_in: float, heat_out: float, hot: float, cold: float
) -> float:
    """The entropy (J/K) that two reservoirs gain when the engine takes
    ``heat_in`` from the one at ``hot`` and gives ``heat_out`` to the one at
    ``cold``: -Q_in / T_hot + Q_out / T_cold. The second law requires it to be
    at least zero."""
    return -heat_in / hot + heat_out / cold
