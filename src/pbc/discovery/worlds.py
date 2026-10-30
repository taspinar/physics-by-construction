"""An unknown physical world of three bodies (lesson D5, F99).

Three bodies of public masses move in a plane. Each pair attracts or repels
along the line between them with a central force

    f_ij(r) = k_ij r^-p,

positive for attraction, with a coupling k_ij of its own and one exponent p
for every pair. The couplings and the exponent are hidden. The forces of a
pair are equal and opposite, as in ``pbc.mechanics.nbody``, which is the
case k_ij = G m_i m_j, p = 2: Newton's gravity is one member of the family,
and a world whose couplings are not proportional to the masses, or have
different signs, is another.

The experimenter places the bodies at rest within a box and reads the six
components of their accelerations with noise, one configuration of a
budget each. A claim, the three couplings and the exponent, is scored by
what it predicts: the bodies are started from held-out positions and
velocities (some outside the box) and integrated under the claim and under
the hidden law (DOP853, as ``pbc.astrophysics.three_body.adaptive``), and
the positions are compared at fixed times. Neither the tools nor any
public attribute reaches the couplings, the exponent, or the held-out
starts; the judge returns one number about a prediction.

Baselines without a model work on the same budget of configurations: least
squares of the family, sparse identification over whole powers of each
pair's distance, and the familiar law, Newton's gravity with G fitted.
"""

import hashlib
import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.integrate import solve_ivp

from pbc.agents.tools import Allowlist, Parameter, Tool
from pbc.data.fit import fit_curve
from pbc.discovery.baselines import BaselineResult, consistent

Array = NDArray[np.float64]
# A pair force: the index of the pair in PAIRS and the distance, to the
# magnitude of the force, positive for attraction.
PairForce = Callable[[int, float], float]

MASSES = (1.0, 2.0, 3.0)  # kg, public
PAIRS = ((0, 1), (0, 2), (1, 2))
COUPLINGS = ("k12", "k13", "k23")
BOUND = 3.0  # m, each coordinate of a probed configuration
CLOSEST = 0.5  # m, the smallest distance of a pair in a probed configuration
SIGMA = 0.002  # m/s², the noise of each acceleration component
DIGITS = 6  # decimals of the accelerations a probe returns
INTEGRATION_TOLERANCE = 1e-10
ACCELERATIONS = "accelerations"
SUBMIT = "submit"
NAMES = ("x1", "y1", "x2", "y2", "x3", "y3")
# The bounds of a claim.
COUPLING_BOUND = 10.0
EXPONENT_BOUNDS = (0.0, 4.0)
STARTS = (1.0, 2.0, 3.0)  # exponents the fits start from

# The predictive test: held-out starts (positions and velocities, one row
# per body) and the times the positions are compared at. The judge's
# configuration; never on a page.
_HELD_OUT = (
    (((1.0, 3.2), (2.2, -2.2), (-1.6, 3.0)), ((-0.6, 0.4), (0.4, 0.0), (-0.2, -0.3))),
    (((-1.0, -4.0), (2.6, -2.8), (-1.9, 3.0)), ((0.0, 0.4), (0.2, 0.3), (-0.5, 0.0))),
    (((-1.2, 0.2), (2.1, 3.3), (-2.8, 3.5)), ((-0.6, 0.3), (0.4, -0.4), (-0.1, 0.4))),
)
TIMES = (1.0, 2.0, 3.0, 4.0)  # s


def family_force(claim: Mapping[str, float]) -> PairForce:
    """The pair force of a claim of the family: its coupling of the pair
    times the distance to the power minus its exponent."""
    couplings = [claim[name] for name in COUPLINGS]
    p = claim["exponent"]
    return lambda pair, r: couplings[pair] * r**-p


def accelerations_of(pair_force: PairForce, positions: Array) -> Array:
    """The accelerations of the three bodies at ``positions`` (one row per
    body) under ``pair_force``: each pair pulls its bodies toward each other
    with the force, or pushes them apart when it is negative."""
    a = np.zeros((3, 2))
    for number, (i, j) in enumerate(PAIRS):
        d = positions[j] - positions[i]
        r = float(np.hypot(*d))
        f = pair_force(number, r) * d / r
        a[i] += f / MASSES[i]
        a[j] -= f / MASSES[j]
    return a


def integrate(
    pair_force: PairForce, positions: Array, velocities: Array, times: Array
) -> Array | None:
    """The positions of the bodies at ``times``, shape (times, 3, 2), from
    ``positions`` and ``velocities`` at time zero under ``pair_force``;
    ``None`` when the integration fails (a collision under the law)."""

    def rate(t, y):
        a = accelerations_of(pair_force, y[:6].reshape(3, 2))
        return np.concatenate([y[6:], a.reshape(-1)])

    try:
        with np.errstate(over="raise", divide="raise", invalid="raise"):
            solution = solve_ivp(
                rate,
                (0.0, float(times[-1])),
                np.concatenate([positions.reshape(-1), velocities.reshape(-1)]),
                method="DOP853",
                t_eval=times,
                rtol=INTEGRATION_TOLERANCE,
                atol=INTEGRATION_TOLERANCE / 100,
            )
    except ArithmeticError, ValueError, FloatingPointError:
        return None
    if not solution.success or solution.y.shape[1] != len(times):
        return None
    return solution.y[:6].T.reshape(len(times), 3, 2)


def _relative_error(predicted: Array, truth: Array) -> Array:
    """Per time: the root-mean-square position error over the starts and the
    bodies, relative to the root-mean-square distance of the bodies from
    their centre of mass in the truth. Arrays of shape (starts, times, 3, 2)."""
    m = np.array(MASSES)
    centre = np.einsum("b,stbk->stk", m, truth) / m.sum()
    size = np.mean(np.sum((truth - centre[:, :, None, :]) ** 2, axis=-1), axis=(0, 2))
    error = np.mean(np.sum((predicted - truth) ** 2, axis=-1), axis=(0, 2))
    return np.sqrt(error / size)


class PairForceWorld:
    """Three bodies under hidden pair forces: probed at rest, judged in
    motion."""

    name = "pair-force world"
    bound = BOUND
    masses = MASSES

    def __init__(
        self,
        *,
        k12: float = 1.0,
        k13: float = 1.0,
        k23: float = 1.0,
        exponent: float = 2.0,
        budget: int = 12,
        seed: int = 0,
    ):
        if budget < 1:
            raise ValueError(f"the budget must be at least 1, got {budget}")
        self.budget = budget
        self.seed = seed
        self._used = 0
        self._truth = family_force(
            {"k12": k12, "k13": k13, "k23": k23, "exponent": exponent}
        )
        self._paths: dict[tuple[float, ...], Array] = {}

    def __repr__(self) -> str:
        return f"PairForceWorld(budget={self.budget}, seed={self.seed})"

    @property
    def remaining(self) -> int:
        return self.budget - self._used

    def reset(self) -> None:
        """The budget whole again; the law and the noise stay as they are."""
        self._used = 0

    def accelerations(self, positions: Array) -> Array:
        """One probe: the bodies at rest at ``positions`` (one row per body,
        each coordinate within the box), and their accelerations with noise.

        Raises ``ValueError`` for a coordinate outside the box or a pair
        closer than ``CLOSEST``, and ``RuntimeError`` when the budget is
        spent; neither costs anything."""
        positions = np.asarray(positions, dtype=float).reshape(3, 2)
        if not np.all(np.isfinite(positions)) or np.any(np.abs(positions) > BOUND):
            raise ValueError(
                f"every coordinate must be between {-BOUND:g} and {BOUND:g}"
            )
        for i, j in PAIRS:
            if np.hypot(*(positions[j] - positions[i])) < CLOSEST:
                raise ValueError(
                    f"bodies {i + 1} and {j + 1} are closer than {CLOSEST:g} m"
                )
        if self._used >= self.budget:
            raise RuntimeError(f"the budget of {self.budget} configurations is spent")
        self._used += 1
        return accelerations_of(self._truth, positions) + SIGMA * self._noise(positions)

    def _noise(self, positions: Array) -> Array:
        key = f"{self.seed}|{self.name}|" + "|".join(
            f"{v:.12g}" for v in positions.reshape(-1)
        )
        digest = hashlib.sha256(key.encode()).digest()
        rng = np.random.default_rng(int.from_bytes(digest[:8], "big"))
        return rng.standard_normal((3, 2))

    def _truth_paths(self, times: tuple[float, ...]) -> Array:
        if times not in self._paths:
            paths = [
                integrate(self._truth, np.array(x), np.array(v), np.array(times))
                for x, v in _HELD_OUT
            ]
            self._paths[times] = np.array(paths)
        return self._paths[times]

    # region: judge
    def error_in_time(
        self, pair_force: PairForce, times: tuple[float, ...] = TIMES
    ) -> Array:
        """The relative position error of ``pair_force`` on the held-out
        starts at each of ``times``; ``inf`` where a prediction fails.

        A judge's call: numbers about a prediction, in no allowlist."""
        truth = self._truth_paths(times)
        predicted = []
        for x, v in _HELD_OUT:
            path = integrate(pair_force, np.array(x), np.array(v), np.array(times))
            if path is None or not np.all(np.isfinite(path)):
                return np.full(len(times), math.inf)
            predicted.append(path)
        return _relative_error(np.array(predicted), truth)

    # endregion: judge

    def score_forces(self, pair_force: PairForce) -> float:
        """The root-mean-square relative position error of ``pair_force``
        over the held-out starts and ``TIMES``; ``inf`` when a prediction
        fails. The judge's call."""
        errors = self.error_in_time(pair_force)
        if not np.all(np.isfinite(errors)):
            return math.inf
        return float(np.sqrt(np.mean(errors**2)))

    def held_out_error(self, claim: Mapping[str, float]) -> float:
        """The score of a claim of the family (``score_forces``)."""
        return self.score_forces(family_force(claim))


def world_allowlist(world: PairForceWorld) -> tuple[Allowlist, list[dict[str, float]]]:
    """The two tools over ``world`` and the list the claims are appended to.

    ``accelerations`` places the bodies at rest (one of the budget) and
    returns their noisy accelerations; ``submit`` states a claim, the three
    couplings and the exponent; the last one counts. Neither reaches the
    hidden law or the held-out starts."""
    claims: list[dict[str, float]] = []

    def probe(**s: float) -> Mapping[str, float]:
        positions = np.array([s[name] for name in NAMES]).reshape(3, 2)
        a = world.accelerations(positions)
        return {
            f"a{axis}{body + 1}": round(float(a[body, k]), DIGITS)
            for body in range(3)
            for k, axis in enumerate("xy")
        }

    def submit(**claim: float) -> Mapping[str, float]:
        claims.append({k: float(v) for k, v in claim.items()})
        return {"submitted": 1.0}

    m = ", ".join(f"body {i + 1} {mass:g} kg" for i, mass in enumerate(MASSES))
    tools = (
        Tool(
            name=ACCELERATIONS,
            description=(
                "Place the three bodies at rest at the positions given (m) and"
                " read the x and y components of their accelerations (m/s^2),"
                f" with noise. Masses: {m}. No two bodies closer than"
                f" {CLOSEST:g} m. Each call uses one of {world.budget}"
                " configurations."
            ),
            parameters=tuple(
                Parameter(name, f"{name[0]} of body {name[1]} (m)", -BOUND, BOUND)
                for name in NAMES
            ),
            function=probe,
        ),
        Tool(
            name=SUBMIT,
            description=(
                "State your claim: the coupling of each pair and the exponent"
                " of the distance. The last claim counts. It uses no"
                " configuration."
            ),
            parameters=(
                *(
                    Parameter(
                        name,
                        f"coupling of bodies {name[1]} and {name[2]} (N m^p),"
                        " positive for attraction",
                        -COUPLING_BOUND,
                        COUPLING_BOUND,
                    )
                    for name in COUPLINGS
                ),
                Parameter("exponent", "power p of the distance", *EXPONENT_BOUNDS),
            ),
            function=submit,
        ),
    )
    return Allowlist(tools), claims


@dataclass(frozen=True)
class Probes:
    """Configurations and their noisy accelerations, shapes (n, 3, 2)."""

    positions: Array
    accelerations: Array
    sigma: float

    def __len__(self) -> int:
        return len(self.positions)


def random_configurations(world: PairForceWorld, seed: int = 0) -> Probes:
    """Spend the whole budget at configurations drawn uniformly in the box,
    drawing again any that puts a pair closer than ``CLOSEST``."""
    rng = np.random.default_rng(seed)
    world.reset()
    positions, found = [], []
    while world.remaining > 0:
        x = rng.uniform(-BOUND, BOUND, (3, 2))
        try:
            found.append(world.accelerations(x))
        except ValueError:
            continue
        positions.append(x)
    world.reset()
    return Probes(np.array(positions), np.array(found), SIGMA)


def _failed(name: str, data: Probes, reason: str) -> BaselineResult:
    return BaselineResult(name, len(data), False, None, math.inf, reason)


def fit_family(
    world: PairForceWorld, data: Probes, name: str = "least squares"
) -> BaselineResult:
    """The family fitted to the probes by weighted least squares
    (``pbc.data.fit.fit_curve``) from each exponent of ``STARTS``, the best
    fit kept, judged by the chi-square rule of every baseline."""
    names = (*COUPLINGS, "exponent")
    flat = data.accelerations.reshape(-1)
    if len(flat) <= len(names):
        return _failed(name, data, "fewer readings than parameters")

    def curve(index: Array, *params: float) -> Array:
        force = family_force(dict(zip(names, params, strict=True)))
        model = np.array([accelerations_of(force, x) for x in data.positions])
        return model.reshape(-1)[index.astype(int)]

    bounds = (
        [-COUPLING_BOUND] * 3 + [EXPONENT_BOUNDS[0]],
        [COUPLING_BOUND] * 3 + [EXPONENT_BOUNDS[1]],
    )
    best = None
    for p in STARTS:
        try:
            fit = fit_curve(
                curve,
                np.arange(len(flat), dtype=float),
                flat,
                (1.0, 1.0, 1.0, p),
                sigma=data.sigma,
                names=names,
                bounds=bounds,
            )
        except ValueError:
            continue
        if best is None or fit.chi2 < best.chi2:
            best = fit
    if best is None:
        return _failed(name, data, "no fit could be made")
    claim = dict(zip(names, map(float, best.params), strict=True))
    error = world.held_out_error(claim)
    if not consistent(best.chi2, best.dof):
        reason = (
            f"chi-square {best.chi2:.3g} for {best.dof} degrees of freedom: the"
            " family does not describe the readings"
        )
    elif not all(best.identifiable):
        reason = "the readings do not determine the parameters separately"
    else:
        reason = ""
    return BaselineResult(name, len(data), not reason, claim, error, reason)


def terms_force(claim: Mapping[str, float]) -> PairForce:
    """The pair force of a sum of terms, by name ``"k12 r^-2"``: the
    coefficients of each pair's whole powers of the distance."""
    parsed = []
    for term, value in claim.items():
        pair, power = term.split(" r^-")
        parsed.append((COUPLINGS.index(pair), int(power), value))
    return lambda index, r: sum(c * r**-n for i, n, c in parsed if i == index)


def _design(data: Probes, powers: tuple[int, ...]) -> tuple[Array, list[str]]:
    """The acceleration components of a unit coupling of each pair at each
    power, one column per term, scaled by the noise."""
    columns, terms = [], []
    for number, pair in enumerate(COUPLINGS):
        for n in powers:

            def unit(index: int, r: float, number=number, n=n) -> float:
                return r**-n if index == number else 0.0

            columns.append(
                np.array(
                    [accelerations_of(unit, x).reshape(-1) for x in data.positions]
                ).reshape(-1)
            )
            terms.append(f"{pair} r^-{n}")
    return np.array(columns).T / data.sigma, terms


def sparse_pairs(
    world: PairForceWorld,
    data: Probes,
    powers: tuple[int, ...] = (1, 2, 3),
    threshold: float = 0.2,
    name: str = "sparse identification",
) -> BaselineResult:
    """Sequentially thresholded least squares over whole powers of each
    pair's distance: the force of each pair is looked for as a short sum
    of c r^-n. It finds the law only if the law is such a sum."""
    design, terms = _design(data, powers)
    target = data.accelerations.reshape(-1) / data.sigma
    active = np.ones(len(terms), dtype=bool)
    c = np.zeros(len(terms))
    for _ in range(10):
        c[:] = 0.0
        c[active], *_ = np.linalg.lstsq(design[:, active], target, rcond=None)
        small = active & (np.abs(c) < threshold * np.abs(c).max())
        if not small.any():
            break
        active &= ~small
    c[~active] = 0.0
    chi2 = float(np.sum((target - design @ c) ** 2))
    dof = len(target) - int(active.sum())
    claim = {t: float(x) for t, x in zip(terms, c, strict=True) if x != 0.0}
    error = world.score_forces(terms_force(claim))
    reason = ""
    if not consistent(chi2, dof):
        reason = (
            f"chi-square {chi2:.3g} for {dof} degrees of freedom: no sparse sum"
            " of whole powers describes the readings"
        )
    return BaselineResult(name, len(data), not reason, claim or None, error, reason)


def newton(
    world: PairForceWorld, data: Probes, name: str = "Newton's gravity"
) -> BaselineResult:
    """The familiar law: k_ij = G m_i m_j and p = 2, with G fitted to the
    probes (linear in G). It succeeds only when that fit is consistent with
    the noise."""
    unit = {
        name: MASSES[i] * MASSES[j]
        for name, (i, j) in zip(COUPLINGS, PAIRS, strict=True)
    }
    x = np.array(
        [
            accelerations_of(family_force(unit | {"exponent": 2.0}), p)
            for p in data.positions
        ]
    ).reshape(-1)
    y = data.accelerations.reshape(-1)
    g = float(np.sum(x * y) / np.sum(x * x))
    chi2 = float(np.sum(((y - g * x) / data.sigma) ** 2))
    dof = len(y) - 1
    claim = {k: g * v for k, v in unit.items()} | {"exponent": 2.0}
    error = world.held_out_error(claim)
    reason = ""
    if not consistent(chi2, dof):
        reason = (
            f"chi-square {chi2:.3g} for {dof} degrees of freedom: gravity does"
            " not describe the readings"
        )
    return BaselineResult(name, len(data), not reason, claim, error, reason)
