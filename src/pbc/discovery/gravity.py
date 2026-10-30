"""Gravity in a laboratory, scored on orbits nobody probed (lesson D4, F99).

The environment is a torsion-balance laboratory in a world whose law of
attraction is hidden: the experimenter sets a source mass, a test mass, and
their distance, and reads the attraction with noise. A claim is a member of
the public family

    force = G source_mass^source_power test_mass^test_power distance^-exponent,

of which Newton's law is G m M / r², and the hidden world is one member.

A claim is never scored on forces. It is scored on a **transfer**: bound
orbits of a light body about a heavy one, with masses and distances far
outside what the laboratory can set, in a system the agent never probed.
Each orbit starts at a periapsis, with the velocity perpendicular to the
radius, and is integrated under the claimed law and under the hidden one by
``pbc.astrophysics.central_force.orbit``; the observable is the radial
period, the time from one periapsis to the next. The score is the
root-mean-square relative error of the predicted periods. A law under which
the body escapes, or does not come round twice within the window, predicts
no period and scores infinity.

The heavy body is held fixed: its acceleration toward the light one is
neglected, as the test mass is a five-hundredth of it or less. Any force
predictor transfers, so a sum of terms (the sparse baseline) is scored in
the same way as a claim of the family.
"""

import math
from collections.abc import Callable, Mapping

import numpy as np

from pbc.astrophysics.central_force import orbit
from pbc.discovery.environment import Control, Environment, Observation

# The window within which a predicted orbit must come round twice, a shorter
# one tried first, and the relative tolerance of the integration.
WINDOW = 2000.0  # s
FIRST_WINDOW = 400.0  # s
INTEGRATION_TOLERANCE = 1e-10


def radial_period(
    acceleration: Callable[[float], float], periapsis: float, speed: float
) -> float:
    """The time from one periapsis to the next of the orbit that starts at
    ``periapsis`` (m) from a fixed centre with ``speed`` (m/s) perpendicular
    to the radius, under the radial ``acceleration`` per unit mass (negative
    for attraction); ``nan`` when the body does not come round twice within
    ``WINDOW``. A shorter window is tried first, since most orbits come
    round twice in it.

    The start is an apsis, but it is a periapsis only if the speed exceeds
    the circular one; the difference of the first two periapsis passages
    after it is the radial period either way."""
    for window in (FIRST_WINDOW, WINDOW):
        try:
            path = orbit(
                acceleration,
                [periapsis, 0.0],
                [0.0, speed],
                window,
                samples=2,
                tolerance=INTEGRATION_TOLERANCE,
            )
        except RuntimeError, ValueError, ArithmeticError:
            return math.nan
        if len(path.periapsis_t) >= 2:
            return float(path.periapsis_t[1] - path.periapsis_t[0])
    return math.nan


class GravityEnvironment(Environment):
    """The attraction between two masses in a laboratory, in a world whose
    law is hidden; scored by the periods of orbits it predicts."""

    name = "gravity"
    controls = (
        Control("source_mass", "kg", 1.0, 10.0, "mass of the source body"),
        Control("test_mass", "kg", 1.0, 10.0, "mass of the test body"),
        Control("distance", "m", 0.5, 2.0, "distance between their centres"),
    )
    observation = Observation("force", "N", 0.001, "attraction between the bodies")
    claim = (
        Control("G", "N m^p/kg^(a+b)", 1e-4, 10.0, "coefficient of the law"),
        Control("source_power", "1", 0.0, 3.0, "power a of the source mass"),
        Control("test_power", "1", 0.0, 3.0, "power b of the test mass"),
        Control("exponent", "1", 0.0, 6.0, "power p of the distance"),
    )
    family = (
        "force = G source_mass^source_power test_mass^test_power distance^-exponent"
    )
    starts = (
        (0.1, 1.0, 1.0, 2.0),
        (1.0, 0.5, 0.5, 1.0),
        (0.01, 1.5, 1.5, 3.0),
    )
    # The transfer: orbits of a test body about a fixed source, started at
    # periapsis (m) with a speed (m/s) perpendicular to the radius. Masses and
    # distances lie far outside the laboratory's bounds.
    _held_out = (
        {"source_mass": 500.0, "test_mass": 0.5, "periapsis": 8.0, "speed": 1.8},
        {"source_mass": 2000.0, "test_mass": 2.0, "periapsis": 15.0, "speed": 2.6},
        {"source_mass": 10000.0, "test_mass": 20.0, "periapsis": 40.0, "speed": 3.6},
    )

    def __init__(
        self,
        *,
        G: float = 0.05,
        source_power: float = 1.0,
        test_power: float = 1.0,
        exponent: float = 2.0,
        budget: int = 30,
        seed: int = 0,
    ):
        super().__init__(budget=budget, seed=seed)
        self._truth = {
            "G": G,
            "source_power": source_power,
            "test_power": test_power,
            "exponent": exponent,
        }
        self._periods: tuple[float, ...] | None = None

    def __repr__(self) -> str:
        return f"GravityEnvironment(budget={self.budget}, seed={self.seed})"

    def _law(self, settings):
        return self.predict(self._truth, settings)

    def predict(self, claim, settings):
        return float(
            claim["G"]
            * settings["source_mass"] ** claim["source_power"]
            * settings["test_mass"] ** claim["test_power"]
            * settings["distance"] ** -claim["exponent"]
        )

    # region: judge
    def score_predictor(
        self, predictor: Callable[[Mapping[str, float]], float]
    ) -> float:
        """The root-mean-square relative error of the radial periods that the
        force ``predictor`` gives for the orbits of the transfer, against the
        hidden law's; ``inf`` when a predicted orbit has no period.

        This is the judge's call. It gives one number about a prediction and
        is in no allowlist."""
        if self._periods is None:
            self._periods = tuple(
                self._period(lambda s: self._law(s), o) for o in self._held_out
            )
        predicted = np.array([self._period(predictor, o) for o in self._held_out])
        if not np.all(np.isfinite(predicted)):
            return math.inf
        truth = np.array(self._periods)
        return float(np.sqrt(np.mean(((predicted - truth) / truth) ** 2)))

    # endregion: judge

    @staticmethod
    def _period(
        predictor: Callable[[Mapping[str, float]], float],
        setting: Mapping[str, float],
    ) -> float:
        source, test = setting["source_mass"], setting["test_mass"]

        def acceleration(r: float) -> float:
            force = predictor(
                {"source_mass": source, "test_mass": test, "distance": float(r)}
            )
            return -float(force) / test

        try:
            return radial_period(acceleration, setting["periapsis"], setting["speed"])
        except ArithmeticError, ValueError, TypeError, KeyError:
            return math.nan


def gravity_library() -> dict[str, Callable[[Mapping[str, float]], float]]:
    """The candidate terms of the sparse baseline: products and single masses
    over whole powers of the distance. Terms are public; they say nothing of
    the law."""
    terms: dict[str, Callable[[Mapping[str, float]], float]] = {}
    for n in range(1, 5):
        terms[f"source*test*distance^-{n}"] = lambda s, n=n: (
            s["source_mass"] * s["test_mass"] * s["distance"] ** -n
        )
    terms["source*distance^-2"] = lambda s: s["source_mass"] * s["distance"] ** -2
    terms["test*distance^-2"] = lambda s: s["test_mass"] * s["distance"] ** -2
    return terms
