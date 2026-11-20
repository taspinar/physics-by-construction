"""A thermal discovery and the levels of transfer of what it found (F147,
lesson MD9).

A small aluminium sphere cools in still air. A box (``CoolingBox``) hides
its law: convection with a coefficient the discoverer is not told, and a
little radiation. Through the box's allowlist a discoverer may set the
sphere's start temperature and read its temperature after a time, with
noise, at the air temperature of the room; nothing else. ``discover`` is a
scripted discoverer without a model: a grid of starts and times, and a fit
of Newton's law of cooling, ``dT/dt = -k (T - T_air)``.

The law found is then carried to held-out worlds (``WORLDS``) that the
allowlist cannot reach, one per level of transfer:

- **interpolation**: a start within the probed range that was not probed;
- **new excitation**: the air temperature oscillates instead of standing;
- **new parameters**: colder air;
- **new regime**: a start of several hundred degrees, where radiation, which
  grows with the fourth power of the absolute temperature, is not small;
- **another structure**: the same sphere inside a thin sheath, a second
  heat capacity between the thermometer and the air.

``never_probed`` reads the discoverer's trace and says, for each world,
whether any probe had its conditions.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp

from pbc.agents.messages import ToolCall, ToolResult
from pbc.agents.tools import Allowlist, Parameter, Tool
from pbc.data.fit import FitResult, fit_curve

STEFAN_BOLTZMANN = 5.670374419e-8  # W/(m² K⁴)
KELVIN = 273.15  # K at 0 °C

# region: box
DIAMETER = 0.02  # m, of the aluminium sphere
DENSITY = 2700.0  # kg/m³
SPECIFIC_HEAT = 900.0  # J/(kg K)
CONVECTION = 25.0  # W/(m² K), hidden from the discoverer
EMISSIVITY = 0.1  # of the oxidised surface, hidden from the discoverer
AIR = 20.0  # °C, the room the box stands in
NOISE = 0.05  # K, standard deviation of a reading
STARTS = (30.0, 60.0)  # °C, the start temperatures the allowlist accepts
TIMES = (0.0, 600.0)  # s, the times the allowlist accepts
BUDGET = 40  # readings
# endregion: box
# region: discoverer
GRID_STARTS = (30.0, 40.0, 50.0, 60.0)  # °C
GRID_TIMES = tuple(60.0 * n for n in range(1, 11))  # s
# endregion: discoverer
TOLERANCE = 0.02  # relative root-mean-square error of the temperature excess
SEED = 1

AREA = math.pi * DIAMETER**2  # m²
CAPACITY = DENSITY * math.pi * DIAMETER**3 / 6 * SPECIFIC_HEAT  # J/K
SHEATH = 0.5  # the sheath's heat capacity, as a fraction of the sphere's
CONTACT = CONVECTION * AREA  # W/K, between the sphere and its sheath


def radiation(t_body: float, t_air: float) -> float:
    """The net radiated power per area (W/m²) at the two temperatures (°C)."""
    return (
        EMISSIVITY * STEFAN_BOLTZMANN * ((t_body + KELVIN) ** 4 - (t_air + KELVIN) ** 4)
    )


def bare(start: float, air: Callable[[float], float], t: np.ndarray) -> np.ndarray:
    """The temperature (°C) of the bare sphere at the times ``t`` (s), from
    ``start`` (°C), in air of temperature ``air(t)`` (°C): convection and
    radiation."""

    def rate(time: float, y: np.ndarray) -> list[float]:
        outside = air(time)
        loss = CONVECTION * (y[0] - outside) + radiation(y[0], outside)
        return [-AREA * loss / CAPACITY]

    return _solve(rate, [start], t)[0]


def sheathed(start: float, air: Callable[[float], float], t: np.ndarray) -> np.ndarray:
    """The temperature (°C) of the sphere inside its sheath: the sheath, of
    heat capacity ``SHEATH`` times the sphere's, exchanges with the sphere
    through ``CONTACT`` and with the air as the bare sphere does."""

    def rate(time: float, y: np.ndarray) -> list[float]:
        outside = air(time)
        inner = CONTACT * (y[0] - y[1])
        loss = AREA * (CONVECTION * (y[1] - outside) + radiation(y[1], outside))
        return [-inner / CAPACITY, (inner - loss) / (SHEATH * CAPACITY)]

    return _solve(rate, [start, start], t)[0]


def _solve(rate, y0, t: np.ndarray) -> np.ndarray:
    solution = solve_ivp(
        rate, (t[0], t[-1]), y0, t_eval=t, rtol=1e-10, atol=1e-10, method="DOP853"
    )
    if not solution.success:
        raise RuntimeError(f"the integration failed: {solution.message}")
    return solution.y


def still(temperature: float) -> Callable[[float], float]:
    """Air at a constant ``temperature`` (°C)."""
    return lambda _: temperature


class CoolingBox:
    """The bare sphere in the room, behind an allowlist: the discoverer sets
    the start temperature and the time and reads the temperature with noise;
    the law, the air temperature's role, and the held-out worlds are out of
    its reach. Every accepted call is in ``trace``."""

    def __init__(self, seed: int = SEED):
        self._seed = seed
        self.trace: list[tuple[ToolCall, ToolResult]] = []
        self._allowlist = Allowlist(
            (
                Tool(
                    name="measure",
                    description=(
                        "Heat the sphere to a start temperature, let it cool in"
                        " the room, and read its temperature after a time. The"
                        f" reading has a noise of {NOISE:g} K."
                    ),
                    parameters=(
                        Parameter("start", "start temperature, in °C", *STARTS),
                        Parameter("time", "time after the start, in s", *TIMES),
                    ),
                    function=self._measure,
                ),
            ),
            budget=BUDGET,
        )

    def _measure(self, start: float, time: float) -> dict[str, float]:
        key = [self._seed, round(start * 1000), round(time * 1000)]
        noise = float(np.random.default_rng(key).normal(0.0, NOISE))
        clean = bare(start, still(AIR), np.array([0.0, time]))[-1] if time else start
        return {"temperature": float(clean) + noise, "air": AIR}

    def call(self, call: ToolCall) -> ToolResult:
        """Dispatch ``call`` through the allowlist and keep it in the trace."""
        result = self._allowlist.dispatch(call)
        self.trace.append((call, result))
        return result


@dataclass(frozen=True)
class CoolingLaw:
    """Newton's law of cooling with the rate ``k`` (1/s), as fitted."""

    k: float
    fit: FitResult

    def predict(
        self, start: float, air: Callable[[float], float], t: np.ndarray
    ) -> np.ndarray:
        """The temperature (°C) the law predicts at the times ``t`` (s)."""

        def rate(time: float, y: np.ndarray) -> list[float]:
            return [-self.k * (y[0] - air(time))]

        return _solve(rate, [start], t)[0]


# region: discover
def discover(box: CoolingBox) -> CoolingLaw:
    """The scripted discoverer: read the grid through the allowlist, then fit
    ``T = T_air + (T_0 - T_air) exp(-k t)``, the solution of Newton's law
    for a start ``T_0`` in still air, to the readings."""
    starts, times, temperatures, air = [], [], [], []
    for number, (start, time) in enumerate(
        (s, t) for s in GRID_STARTS for t in GRID_TIMES
    ):
        call = ToolCall(
            f"probe-{number + 1}", "measure", {"start": start, "time": time}
        )
        result = box.call(call)
        if result.ok:
            starts.append(start)
            times.append(time)
            temperatures.append(result.content["temperature"])
            air.append(result.content["air"])
    starts, times, air = np.array(starts), np.array(times), np.array(air)

    def solution(index: np.ndarray, k: float) -> np.ndarray:
        return air + (starts - air) * np.exp(-k * times)

    fit = fit_curve(
        solution,
        np.arange(len(temperatures), dtype=float),
        np.array(temperatures),
        [1e-3],
        sigma=NOISE,
        names=("k",),
    )
    return CoolingLaw(fit.value("k"), fit)


# endregion: discover


@dataclass(frozen=True)
class World:
    """A held-out thermal world: its level of transfer, what changes in it,
    the start (°C), the air (°C over time) and its temperature when it
    stands still (``None`` when it does not), the duration (s), and whether
    the sphere is bare or in its sheath."""

    level: str
    change: str
    start: float
    air: Callable[[float], float]
    still_air: float | None
    duration: float
    structure: str = "bare"


WORLDS = {
    "interpolation": World(
        "interpolation",
        "an unprobed start within the probed range",
        45.0,
        still(AIR),
        AIR,
        600.0,
    ),
    "oscillating air": World(
        "new excitation",
        "the air temperature oscillates by ten kelvin with a period of 400 s",
        AIR,
        lambda t: AIR + 10.0 * math.sin(2 * math.pi * t / 400.0),
        None,
        1200.0,
    ),
    "cold room": World(
        "new parameters",
        "the air is at 5 °C instead of 20 °C",
        45.0,
        still(5.0),
        5.0,
        600.0,
    ),
    "hot start": World(
        "new regime",
        "a start at 600 °C, where radiation is not small",
        600.0,
        still(AIR),
        AIR,
        600.0,
    ),
    "sheathed sphere": World(
        "another structure",
        "the sphere inside a sheath, a second heat capacity",
        60.0,
        still(AIR),
        AIR,
        600.0,
        "sheathed",
    ),
}


def truth(world: World) -> tuple[np.ndarray, np.ndarray]:
    """The times (s) and the true temperatures (°C) of ``world``."""
    t = np.linspace(0.0, world.duration, 121)
    system = bare if world.structure == "bare" else sheathed
    return t, system(world.start, world.air, t)


# region: judge
def transfer_error(law: CoolingLaw, world: World) -> float:
    """The root-mean-square error of the law's temperature in ``world``,
    relative to the root-mean-square of the true excess over the air."""
    t, true = truth(world)
    predicted = law.predict(world.start, world.air, t)
    excess = true - np.array([world.air(time) for time in t])
    return float(
        np.sqrt(np.mean((predicted - true) ** 2)) / np.sqrt(np.mean(excess**2))
    )


# endregion: judge


def never_probed(trace, world: World) -> tuple[bool, float]:
    """Whether any accepted probe of ``trace`` had the conditions of
    ``world`` (its start, still air at the room's temperature, the bare
    sphere), and the distance of the nearest accepted start from the world's
    (°C)."""
    accepted = [call.arguments for call, result in trace if result.ok]
    nearest = min(abs(a["start"] - world.start) for a in accepted)
    conditions = world.still_air == AIR and world.structure == "bare"
    probed = conditions and any(a["start"] == world.start for a in accepted)
    return not probed, nearest
