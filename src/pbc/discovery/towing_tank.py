"""A towing tank: an unknown drag law, its boundary, and competing models
(lesson MD1, F146; ``docs/discovery-protocol.md``, "Unknown systems and
competing models").

A sphere is towed through a fluid at a set speed; the experimenter chooses
the speed and the diameter of the sphere and reads the drag force, with a
relative noise of known size. The fluid is inside the boundary of the
system, but it is neither set nor read: it is held fixed and out of reach.
The law of the drag, a power law of the speed and the diameter with a
constant that holds the fluid, is hidden, and so are the settings at which
a claim is scored, which lie beyond what the carriage can tow and the tank
can hold.

Two worlds share the box. In ``WATER`` the drag is Newton's quadratic drag
on a sphere, ``F = C_d rho (pi / 8) d^2 v^2``, with a drag coefficient
held constant over the whole range (a real sphere's coefficient falls at
the drag crisis, near a Reynolds number of 3e5, which the simulated world
leaves out). In ``UNKNOWN`` the tank holds a fluid of no known kind, and
neither drag law of the textbook holds. Both are the judge's configuration:
no tool, prompt, or page shows them.

The routes probe only through the allowlist of the box (``measure`` and
``submit``) and search for the law in one of two conditions of prior
knowledge: **knowledge-informed**, the two drag laws of the textbook as
the only candidates (Stokes' drag, linear in speed and diameter, and the
quadratic drag), and **restricted prior**, every power law of the speed and
the diameter of the grammar of ``pbc.discovery.symbolic``.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from pbc.agents import ToolCall
from pbc.agents.tools import Allowlist
from pbc.discovery.baselines import Dataset
from pbc.discovery.environment import Control, Environment, Observation
from pbc.discovery.symbolic import HALF_STEPS, Search, power_law_search
from pbc.discovery.tools import MEASURE, SUBMIT, environment_allowlist

BUDGET = 12  # probes
TOLERANCE = 0.05  # held-out error that counts as recovering the law
NOISE = 0.02  # relative noise of a reading, known to the experimenter
SEED = 0
# The candidates of the knowledge-informed condition: exponents of the speed
# and of the diameter.
CANDIDATES = {"Stokes drag": (1.0, 1.0), "quadratic drag": (2.0, 2.0)}
CONDITIONS = ("knowledge-informed", "restricted prior")
# The judge's configuration: the hidden laws. Never on a page.
WATER = {
    "constant": 0.47 * 1000.0 * math.pi / 8,
    "speed_exponent": 2.0,
    "diameter_exponent": 2.0,
}
UNKNOWN = {"constant": 23.1, "speed_exponent": 1.5, "diameter_exponent": 1.5}


class TowingTankEnvironment(Environment):
    """The drag on a towed sphere, read with a relative noise. The noise of
    a setting is a function of the seed and the controls, as in every
    environment: a repeated probe repeats it."""

    name = "towing-tank"
    controls = (
        Control("speed", "m/s", 0.2, 2.0, "towing speed of the carriage"),
        Control("diameter", "m", 0.02, 0.1, "diameter of the sphere"),
    )
    observation = Observation(
        "force", "N", NOISE, "drag on the sphere; the noise is relative"
    )
    claim = (
        Control("constant", "N s^a/m^(a+b)", 1e-3, 1e5, "coefficient of the law"),
        Control("speed_exponent", "1", 0.0, 4.0, "power a of the speed"),
        Control("diameter_exponent", "1", 0.0, 4.0, "power b of the diameter"),
    )
    family = "force = constant speed^speed_exponent diameter^diameter_exponent"
    starts = ((100.0, 2.0, 2.0),)
    _held_out = (
        {"speed": 3.0, "diameter": 0.05},
        {"speed": 1.0, "diameter": 0.15},
        {"speed": 2.5, "diameter": 0.12},
    )

    def __init__(
        self,
        *,
        constant: float,
        speed_exponent: float,
        diameter_exponent: float,
        budget: int = BUDGET,
        seed: int = SEED,
    ):
        super().__init__(budget=budget, seed=seed)
        self._constant = constant
        self._exponents = (speed_exponent, diameter_exponent)

    def __repr__(self) -> str:
        return f"TowingTankEnvironment(budget={self.budget}, seed={self.seed})"

    def measure(self, **controls: float) -> dict[str, float]:
        """One probe: the drag with a relative noise, the reading multiplied
        by exp(noise times a standard normal draw)."""
        settings = self._validated(controls)
        if self._used >= self.budget:
            raise RuntimeError(f"the budget of {self.budget} probes is spent")
        self._used += 1
        noise = self.observation.sigma * self._noise(settings)
        return {self.observation.name: float(self._law(settings) * math.exp(noise))}

    def _law(self, settings):
        a, b = self._exponents
        return self._constant * settings["speed"] ** a * settings["diameter"] ** b

    def predict(self, claim, settings):
        return float(
            claim["constant"]
            * settings["speed"] ** claim["speed_exponent"]
            * settings["diameter"] ** claim["diameter_exponent"]
        )


def tank(world: Mapping[str, float] = WATER, seed: int = SEED) -> TowingTankEnvironment:
    """A fresh tank holding ``world``, with the protocol's budget."""
    return TowingTankEnvironment(**world, seed=seed)


# region: designs
def grid_design() -> list[dict[str, float]]:
    """Four speeds by three spheres, spread over the controls."""
    return [
        {"speed": v, "diameter": d}
        for v in (0.2, 0.5, 1.0, 2.0)
        for d in (0.02, 0.05, 0.1)
    ]


def one_sphere_design() -> list[dict[str, float]]:
    """Twelve speeds, all on the sphere of 5 cm: the diameter, an accessible
    variable, left unvaried."""
    return [
        {"speed": float(v), "diameter": 0.05} for v in np.geomspace(0.2, 2.0, BUDGET)
    ]


def random_design(seed: int = 3) -> list[dict[str, float]]:
    """Twelve settings drawn uniformly within the bounds of the controls."""
    rng = np.random.default_rng(seed)
    return [
        {"speed": float(v), "diameter": float(d)}
        for v, d in zip(
            rng.uniform(0.2, 2.0, BUDGET), rng.uniform(0.02, 0.1, BUDGET), strict=True
        )
    ]


# endregion: designs


def probe(allowlist: Allowlist, design: Sequence[Mapping[str, float]]) -> Dataset:
    """Read the force at each setting of ``design`` through the allowlist's
    ``measure``, the only way to the tank; a refused call stops the route."""
    settings, values = [], []
    for k, setting in enumerate(design):
        result = allowlist.dispatch(ToolCall(f"probe-{k}", MEASURE, dict(setting)))
        if not result.ok:
            raise RuntimeError(f"the tank refused a probe: {result.content['error']}")
        settings.append(dict(setting))
        values.append(result.content["force"])
    return Dataset(tuple(settings), np.array(values), NOISE)


# region: conditions
def search(data: Dataset, condition: str) -> Search:
    """The search of ``condition`` on the readings: the two drag laws as the
    only forms, or every power law of the grammar."""
    variables = {
        "v": [s["speed"] for s in data.settings],
        "d": [s["diameter"] for s in data.settings],
    }
    if condition == "knowledge-informed":
        return power_law_search(
            variables, data.values, data.sigma, forms=list(CANDIDATES.values())
        )
    if condition == "restricted prior":
        return power_law_search(variables, data.values, data.sigma, HALF_STEPS)
    raise ValueError(f"unknown condition {condition!r}")


# endregion: conditions


def claim_of(found: Search) -> dict[str, float] | None:
    """The chosen form as a claim of the family, or ``None``: a search with
    no consistent form makes no claim."""
    if found.chosen is None:
        return None
    a, b = found.chosen.exponents
    return {
        "constant": found.chosen.constant,
        "speed_exponent": a,
        "diameter_exponent": b,
    }


@dataclass(frozen=True)
class Outcome:
    """One condition on one set of readings, scored by the judge."""

    condition: str
    forms: int
    consistent: int
    chosen: str  # the shape of the chosen form, or "none"
    held_out_error: float  # inf when no claim was made
    reason: str  # why no claim was made, or ""

    @property
    def recovered(self) -> bool:
        return self.held_out_error <= TOLERANCE


def route(
    world: Mapping[str, float],
    design: Sequence[Mapping[str, float]],
    condition: str,
    seed: int = SEED,
) -> Outcome:
    """Probe a fresh tank of ``world`` at ``design`` through its allowlist,
    search in ``condition``, submit the claim through the allowlist, and
    have the judge score it on the withheld settings."""
    box = tank(world, seed)
    allowlist = environment_allowlist(box)
    found = search(probe(allowlist, design), condition)
    claim = claim_of(found)
    if claim is not None:
        submitted = allowlist.dispatch(ToolCall("claim", SUBMIT, claim))
        if not submitted.ok:
            raise RuntimeError(f"the claim was refused: {submitted.content['error']}")
    return Outcome(
        condition,
        len(found.forms),
        len(found.consistent()),
        found.chosen.shape if found.chosen else "none",
        math.inf if claim is None else box.held_out_error(claim),
        found.reason,
    )
