"""Conserved quantities from trajectories, and the build's verdict on them
(F82, lesson D13; ``docs/discovery-protocol.md``, "Invariants").

A **conserved quantity** is a function of the state that keeps its value
along every trajectory. It is looked for here as a combination ``c · θ`` of a
public **library** of terms ``θ`` of the state, from sampled trajectories
alone: no equation of motion is fitted or assumed.

The **conservation ratio** of a candidate on a set of trajectories is the
root-mean-square change of ``c · θ`` about its mean on each trajectory,
divided by ``sqrt(Σ c_k² m_k²)``, where ``m_k`` is the root-mean-square size
of term ``k`` on the data: the relative change of the candidate, on the scale
of its terms. An invariant has zero, up to the error of the integration; a
term that changes as much as its size has about one. A candidate whose terms
vanish on the data has no ratio.

The **baseline** without a model is the null space of the matrix of the
terms' changes, each column divided by its ``m_k``: its right singular
vectors with a singular value (over the square root of the number of rows)
at most a threshold are combinations whose ratio is at most that threshold.

A candidate that is conserved on some trajectories need not be a law of the
system. ``judge`` gives the build's **verdict** on trajectories nobody probed,
under several integration settings, and separates the invariants from the
**integration artefacts** (conserved by the method, not by the motion), the
**coincidences** of the trajectories a candidate came from, and the
**identities** of the state's description (constant on every state).

The **boxes** wrap models of ``pbc.mechanics`` as systems an agent, or the
baseline, can only start and watch: the hidden force, its parameters, and the
held-out starts belong to the box. No public attribute or method returns
them; the judge's calls return verdicts and counts.
"""

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import ClassVar

import numpy as np
from numpy.typing import NDArray

from pbc.agents.tools import Allowlist, Parameter, Tool
from pbc.mechanics.dynamics import State, Stepper, simulate
from pbc.mechanics.integrators import rk4_step, symplectic_euler_step, verlet_step

type Array = NDArray[np.float64]
# A term of a library: its values on the states of a trajectory, one row per
# sampled instant.
type Term = Callable[[Array], Array]
type Library = Mapping[str, Term]

# Below this many units of round-off a change counts as no change.
ROUND_OFF = 1e-12

# The verdicts of ``judge``, in the order the rules are tried.
INVARIANT = "invariant"
IDENTITY = "identity"
ARTEFACT = "integration artefact"
COINCIDENCE = "coincidence"
NOT_CONSERVED = "not conserved"
TRIVIAL = "trivial"


def values(library: Library, states: Array) -> Array:
    """The terms of ``library`` on ``states``: one column per term."""
    return np.stack([term(states) for term in library.values()], axis=1)


def changes(library: Library, trajectories: Sequence[Array]) -> Array:
    """The terms' changes about their mean on each trajectory, the
    trajectories stacked: one row per sampled state, one column per term."""
    rows = []
    for states in trajectories:
        theta = values(library, states)
        rows.append(theta - theta.mean(axis=0))
    return np.vstack(rows)


def sizes(library: Library, trajectories: Sequence[Array]) -> Array:
    """The root-mean-square size ``m_k`` of each term on ``trajectories``."""
    theta = np.vstack([values(library, states) for states in trajectories])
    return np.sqrt(np.mean(theta**2, axis=0))


def _scale(c: Array, m: Array) -> float | None:
    scale = math.sqrt(float(np.sum(c**2 * m**2)))
    return None if scale <= ROUND_OFF * float(np.max(np.abs(c))) else scale


def conservation_ratio(
    coefficients: Array, library: Library, trajectories: Sequence[Array]
) -> float | None:
    """The root-mean-square change of ``coefficients · θ`` about its mean on
    each of ``trajectories``, divided by ``sqrt(Σ c_k² m_k²)``; ``None`` when
    the terms of the candidate vanish on them."""
    c = np.asarray(coefficients, dtype=float)
    scale = _scale(c, sizes(library, trajectories))
    if scale is None:
        return None
    matrix = changes(library, trajectories)
    return math.sqrt(float(np.mean((matrix @ c) ** 2))) / scale


def between_ratio(
    coefficients: Array, library: Library, trajectories: Sequence[Array]
) -> float | None:
    """The spread of the candidate's mean value from one trajectory to the
    next, on the scale of ``conservation_ratio``: about zero for an identity,
    which has one value on every state, and not for a conservation law,
    whose value is set by the start."""
    c = np.asarray(coefficients, dtype=float)
    scale = _scale(c, sizes(library, trajectories))
    if scale is None:
        return None
    means = np.array(
        [values(library, states).mean(axis=0) @ c for states in trajectories]
    )
    return float(np.std(means)) / scale


@dataclass(frozen=True)
class Found:
    """What the baseline found on a set of trajectories."""

    terms: tuple[str, ...]
    # The candidates, each a row of coefficients over ``terms``, in reduced
    # row echelon form of the coefficients scaled by the sizes of the terms,
    # scaled back so that the first nonzero coefficient of each is one;
    # a scaled coefficient below a millionth of its row's largest is zero.
    candidates: Array
    # The singular values of the scaled matrix over the square root of its
    # rows, smallest last; the candidates are those at most the threshold.
    singular_values: Array
    # Terms that vanish on the data: each is trivially constant there.
    constant_terms: tuple[str, ...]

    def candidate(self, index: int) -> dict[str, float]:
        """Candidate ``index`` as a mapping from term to coefficient, its
        zero coefficients left out."""
        row = self.candidates[index]
        return {t: float(c) for t, c in zip(self.terms, row, strict=True) if c != 0.0}


def find_invariants(
    library: Library, trajectories: Sequence[Array], threshold: float
) -> Found:
    """The combinations of ``library`` whose conservation ratio on
    ``trajectories`` is at most ``threshold``, as a basis of the null space
    of the scaled matrix of changes; the terms that vanish on the data are
    reported apart, each a candidate of its own."""
    terms = tuple(library)
    matrix = changes(library, trajectories)
    m = sizes(library, trajectories)
    present = m > ROUND_OFF * float(np.max(m))
    scaled = matrix[:, present] / m[present]
    _, sigma, vt = np.linalg.svd(scaled, full_matrices=True)
    sigma = np.concatenate([sigma, np.zeros(vt.shape[0] - len(sigma))])
    sigma = sigma / math.sqrt(len(scaled))
    # The echelon form is taken on the scaled coefficients, where each term
    # weighs by its size, then scaled back.
    scaled_basis = np.zeros((int(np.sum(sigma <= threshold)), len(terms)))
    scaled_basis[:, present] = vt[sigma <= threshold]
    rows = _echelon(scaled_basis)
    basis = np.zeros_like(rows)
    basis[:, present] = rows[:, present] / m[present]
    for row in basis:
        row /= row[np.flatnonzero(row)[0]]
    constant = tuple(t for t, v in zip(terms, present, strict=True) if not v)
    return Found(terms, basis, sigma, constant)


def _echelon(rows: Array, tiny: float = 1e-6) -> Array:
    """The reduced row echelon form of ``rows`` by Gauss-Jordan elimination
    with partial pivoting, each pivot scaled to one and entries below
    ``tiny`` of their row's largest set to zero: the same span, written so
    that each row is readable."""
    a = np.array(rows, dtype=float)
    pivot_row = 0
    for column in range(a.shape[1]):
        if pivot_row == a.shape[0]:
            break
        best = pivot_row + int(np.argmax(np.abs(a[pivot_row:, column])))
        if abs(a[best, column]) <= tiny * max(1.0, float(np.max(np.abs(a)))):
            continue
        a[[pivot_row, best]] = a[[best, pivot_row]]
        a[pivot_row] /= a[pivot_row, column]
        for other in range(a.shape[0]):
            if other != pivot_row:
                a[other] -= a[other, column] * a[pivot_row]
        pivot_row += 1
    for row in a:
        row[np.abs(row) <= tiny * max(1.0, float(np.max(np.abs(row))))] = 0.0
    return a[:pivot_row]


def independent(
    candidates: Sequence[Array], library: Library, trajectories: Sequence[Array]
) -> int:
    """How many of ``candidates`` are linearly independent, each scaled by
    the sizes of the terms on ``trajectories`` so that units do not matter:
    the rank of the scaled rows, at one part in a thousand."""
    if not candidates:
        return 0
    m = sizes(library, trajectories)
    rows = np.array([np.asarray(c, dtype=float) * m for c in candidates])
    rows = rows / np.linalg.norm(rows, axis=1, keepdims=True)
    sigma = np.linalg.svd(rows, compute_uv=False)
    return int(np.sum(sigma > 1e-3 * sigma[0]))


@dataclass(frozen=True)
class Verdict:
    """The build's verdict on one candidate, with the ratios it rests on."""

    training: float | None  # on the trajectories the candidate came from
    settings: Mapping[str, float | None]  # on the held-out ones, by setting
    between: float | None  # spread between held-out trajectories
    verdict: str


def judge(
    coefficients: Array,
    library: Library,
    training: Sequence[Array],
    held_out: Mapping[str, Sequence[Array]],
    own: str,
    reference: str,
    tolerance: float,
) -> Verdict:
    """The verdict on a candidate: its conservation ratio on the
    ``training`` trajectories it came from, and on the ``held_out``
    trajectories (by integration setting: the box's ``own``, the
    ``reference``, and any other) that nobody probed.

    An invariant is conserved at the reference and differs between
    trajectories; an identity is conserved and takes one value on all; an
    integration artefact is conserved at the box's own setting only; a
    coincidence is conserved on its training trajectories only.
    """
    c = np.asarray(coefficients, dtype=float)
    ratios = {name: conservation_ratio(c, library, ts) for name, ts in held_out.items()}
    trained = conservation_ratio(c, library, training) if training else None
    between = between_ratio(c, library, held_out[reference])

    def kept(ratio: float | None) -> bool:
        return ratio is not None and ratio <= tolerance

    if ratios[reference] is None:
        verdict = TRIVIAL
    elif kept(ratios[reference]):
        verdict = (
            IDENTITY if between is not None and between <= tolerance else INVARIANT
        )
    elif kept(ratios[own]):
        verdict = ARTEFACT
    elif training and (trained is None or trained <= tolerance):
        verdict = COINCIDENCE
    else:
        verdict = NOT_CONSERVED
    return Verdict(trained, ratios, between, verdict)


# The library of a particle in a plane, state columns (x, y, vx, vy): the
# terms of degree two and the quartic terms of the position. The keys are
# the names a tool can carry; ``PLANAR_TERMS`` gives each in symbols.
PLANAR_TERMS = {
    "x2": "x^2",
    "y2": "y^2",
    "vx2": "vx^2",
    "vy2": "vy^2",
    "xy": "x y",
    "vxvy": "vx vy",
    "xvx": "x vx",
    "yvy": "y vy",
    "xvy": "x vy",
    "yvx": "y vx",
    "x4": "x^4",
    "y4": "y^4",
    "x2y2": "x^2 y^2",
}
PLANAR_LIBRARY: Library = {
    "x2": lambda s: s[:, 0] ** 2,
    "y2": lambda s: s[:, 1] ** 2,
    "vx2": lambda s: s[:, 2] ** 2,
    "vy2": lambda s: s[:, 3] ** 2,
    "xy": lambda s: s[:, 0] * s[:, 1],
    "vxvy": lambda s: s[:, 2] * s[:, 3],
    "xvx": lambda s: s[:, 0] * s[:, 2],
    "yvy": lambda s: s[:, 1] * s[:, 3],
    "xvy": lambda s: s[:, 0] * s[:, 3],
    "yvx": lambda s: s[:, 1] * s[:, 2],
    "x4": lambda s: s[:, 0] ** 4,
    "y4": lambda s: s[:, 1] ** 4,
    "x2y2": lambda s: s[:, 0] ** 2 * s[:, 1] ** 2,
}
STATE = ("x", "y", "vx", "vy")


def coefficients(candidate: Mapping[str, float], library: Library) -> Array:
    """A candidate given by term name, as the vector over ``library``."""
    unknown = sorted(set(candidate) - set(library))
    if unknown:
        raise ValueError(f"unknown terms: {', '.join(unknown)}")
    return np.array([float(candidate.get(name, 0.0)) for name in library])


@dataclass(frozen=True)
class Setting:
    """How a trajectory is integrated: a stepper of ``pbc.mechanics`` and its
    step in s."""

    method: str
    step: Stepper
    dt: float


OWN = "own setting"
HALF = "half step"
REFERENCE = "reference"


class PlanarBox:
    """A particle of unit mass in a plane under a hidden force, started at
    a chosen position and velocity and watched at fixed times. The box
    integrates with its own method and step; the judge also integrates the
    held-out starts at half the step and with a reference method.

    Subclasses implement ``_acceleration`` (the truth) and set ``_held_out``
    and ``settings``.
    """

    name: str
    bound = 1.5  # m and m/s: each coordinate of a start lies within ±bound
    times = tuple(0.5 * i for i in range(8))  # s, the instants returned
    settings: ClassVar[Mapping[str, Setting]]
    # Starts that nobody probes, some beyond the bounds.
    _held_out: tuple[tuple[float, float, float, float], ...] = (
        (1.0, 0.0, 0.0, 1.2),
        (-0.6, 1.1, 0.9, 0.3),
        (1.8, -0.4, -0.2, 0.7),
        (0.2, -1.6, 1.4, -0.5),
        (-1.2, -1.2, -0.8, 1.0),
        (0.5, 0.9, -1.7, -1.1),
        (-1.9, 0.6, 0.4, -0.3),
        (1.3, 1.4, 1.1, -1.4),
    )

    def __init__(self, *, budget: int = 6):
        if budget < 1:
            raise ValueError(f"the budget must be at least 1, got {budget}")
        self.budget = budget
        self._probed: list[Array] = []

    def __repr__(self) -> str:
        return f"{type(self).__name__}(budget={self.budget})"

    @property
    def remaining(self) -> int:
        return self.budget - len(self._probed)

    @property
    def probed(self) -> tuple[Array, ...]:
        """The trajectories started so far at the box's own setting."""
        return tuple(self._probed)

    def trajectory(self, x: float, y: float, vx: float, vy: float) -> Array:
        """The states (x, y, vx, vy) at ``times`` from the start, at the box's
        own setting; one of the budget.

        Raises ``ValueError`` for a start beyond the bounds and
        ``RuntimeError`` when the budget is spent; neither costs anything."""
        start = (x, y, vx, vy)
        if not all(math.isfinite(v) and abs(v) <= self.bound for v in start):
            raise ValueError(
                f"each coordinate of the start must be within ±{self.bound:g}"
            )
        if self.remaining <= 0:
            raise RuntimeError(f"the budget of {self.budget} trajectories is spent")
        states = self._integrate(start, self.settings[OWN])
        self._probed.append(states)
        return states

    def held_out(self, setting: str) -> list[Array]:
        """The held-out trajectories at ``setting``: the judge's data. The
        starts are not returned, and no tool calls this."""
        # Shared by the boxes of one hidden world, which give the same.
        key = (type(self), self._world(), setting)
        if key not in _HELD_OUT:
            _HELD_OUT[key] = [
                self._integrate(start, self.settings[setting])
                for start in self._held_out
            ]
        return _HELD_OUT[key]

    def judge(
        self,
        coefficients: Array,
        tolerance: float,
        training: Sequence[Array] = (),
    ) -> Verdict:
        """The verdict of ``judge`` on a candidate over ``PLANAR_LIBRARY``, on
        the held-out trajectories at every setting."""
        return judge(
            coefficients,
            PLANAR_LIBRARY,
            training,
            {name: self.held_out(name) for name in self.settings},
            OWN,
            REFERENCE,
            tolerance,
        )

    def known_invariants(self, tolerance: float) -> int:
        """How many independent combinations of the library are conserved on
        the held-out trajectories at the reference: the count a run is scored
        against. A number, never the combinations."""
        found = find_invariants(PLANAR_LIBRARY, self.held_out(REFERENCE), tolerance)
        return len(found.candidates) + len(found.constant_terms)

    def _integrate(self, start: Sequence[float], setting: Setting) -> Array:
        steps = [round(t / setting.dt) for t in self.times]
        motion = simulate(
            State(0.0, start[:2], start[2:]),
            lambda t, x, v: self._acceleration(x),
            setting.dt,
            steps[-1],
            step=setting.step,
        )
        return np.hstack([motion.x[steps], motion.v[steps]])

    def _acceleration(self, x: Array) -> Array:
        raise NotImplementedError

    def _world(self) -> tuple[float, ...]:
        raise NotImplementedError


# The held-out trajectories by box class, hidden world, and setting.
_HELD_OUT: dict[tuple[type, tuple[float, ...], str], list[Array]] = {}


class CentralBox(PlanarBox):
    """A hidden central force, ``a = -(k + b r²) r``: the potential
    ``k r² / 2 + b r⁴ / 4``, integrated by velocity Verlet."""

    name = "central"
    settings: ClassVar[Mapping[str, Setting]] = {
        OWN: Setting("velocity Verlet", verlet_step, 0.01),
        HALF: Setting("velocity Verlet", verlet_step, 0.005),
        REFERENCE: Setting("classical Runge-Kutta", rk4_step, 0.002),
    }

    def __init__(self, *, k: float, b: float, budget: int = 6):
        super().__init__(budget=budget)
        self._k = k
        self._b = b

    def _acceleration(self, x):
        return -(self._k + self._b * float(x @ x)) * x

    def _world(self):
        return (self._k, self._b)


class AxesBox(PlanarBox):
    """A hidden harmonic force of a different stiffness along each axis,
    ``a = -(kx x, ky y)``, integrated by symplectic Euler at a coarse step:
    the test system of the drift artefact."""

    name = "axes"
    settings: ClassVar[Mapping[str, Setting]] = {
        OWN: Setting("symplectic Euler", symplectic_euler_step, 0.1),
        HALF: Setting("symplectic Euler", symplectic_euler_step, 0.05),
        REFERENCE: Setting("classical Runge-Kutta", rk4_step, 0.002),
    }

    def __init__(self, *, kx: float, ky: float, budget: int = 6):
        super().__init__(budget=budget)
        self._stiffness = np.array([kx, ky], dtype=float)

    def _acceleration(self, x):
        return -self._stiffness * x

    def _world(self):
        return tuple(self._stiffness)


def rotation_defect(box: PlanarBox, start: Sequence[float], angle: float) -> float:
    """Whether the box is symmetric under rotation, from two of its
    trajectories: the largest difference between the trajectory of the
    rotated start and the rotated trajectory of the start, relative to the
    largest coordinate. Zero up to round-off for a box whose force turns with
    the plane; uses two of the budget."""
    c, s = math.cos(angle), math.sin(angle)
    turn = np.array([[c, -s], [s, c]])

    def rotate(states: Array) -> Array:
        return np.hstack([states[:, :2] @ turn.T, states[:, 2:] @ turn.T])

    first = box.trajectory(*start)
    second = box.trajectory(*rotate(np.array([start], dtype=float))[0])
    return float(np.max(np.abs(second - rotate(first))) / np.max(np.abs(first)))


# The tools of an agent over a box (ADR 004).
TRAJECTORY = "trajectory"
VARIATION = "variation"
SUBMIT = "submit"
DIGITS = 6  # decimals of the states a trajectory returns


def box_allowlist(box: PlanarBox, max_candidates: int) -> tuple[Allowlist, list[Array]]:
    """The three tools over ``box`` and the list the submitted candidates
    are appended to.

    ``trajectory`` starts the box (one of its budget) and returns the state
    at its fixed times; ``variation`` gives the conservation ratio of a
    candidate on the agent's own trajectories and uses no budget; ``submit``
    states a candidate, at most ``max_candidates`` of them. None of them
    reaches the hidden force, its parameters, or the held-out starts."""
    submitted: list[Array] = []
    coefficient = tuple(
        Parameter(name, f"coefficient of {symbol}", -100.0, 100.0)
        for name, symbol in PLANAR_TERMS.items()
    )

    def start(**s: float) -> Mapping[str, float]:
        states = box.trajectory(s["x"], s["y"], s["vx"], s["vy"])
        return {
            f"{name}({t:g})": round(float(value), DIGITS)
            for t, row in zip(box.times, states, strict=True)
            for name, value in zip(STATE, row, strict=True)
        }

    def candidate(arguments: Mapping[str, float]) -> Array:
        c = coefficients(arguments, PLANAR_LIBRARY)
        if not np.any(c):
            raise ValueError("a candidate needs a coefficient that is not zero")
        return c

    def variation(**arguments: float) -> Mapping[str, float]:
        if not box.probed:
            raise ValueError("start a trajectory first")
        c = candidate(arguments)
        result = {}
        for number, states in enumerate(box.probed, start=1):
            ratio = conservation_ratio(c, PLANAR_LIBRARY, [states])
            if ratio is not None:
                result[f"trajectory {number}"] = ratio
        pooled = conservation_ratio(c, PLANAR_LIBRARY, box.probed)
        if pooled is None:
            raise ValueError("the terms of this candidate vanish on your trajectories")
        return result | {"all trajectories": pooled}

    def submit(**arguments: float) -> Mapping[str, float]:
        if len(submitted) >= max_candidates:
            raise ValueError(f"at most {max_candidates} candidates may be submitted")
        submitted.append(candidate(arguments))
        return {"submitted": float(len(submitted))}

    tools = (
        Tool(
            name=TRAJECTORY,
            description=(
                "Start the system at a position (x, y in m) and velocity (vx, vy"
                " in m/s) and return the state at the times"
                f" {', '.join(f'{t:g}' for t in box.times)} s. Each call uses one"
                f" of {box.budget} trajectories."
            ),
            parameters=tuple(
                Parameter(name, f"{name} at the start", -box.bound, box.bound)
                for name in STATE
            ),
            function=start,
        ),
        Tool(
            name=VARIATION,
            description=(
                "The conservation ratio of the candidate, the sum of the"
                " coefficients times their terms, on each of your trajectories"
                " and on all of them: the root-mean-square change of the"
                " candidate along a trajectory, divided by the square root of"
                " the sum of each coefficient squared times the mean square of"
                " its term. Zero for a conserved quantity. Uses no trajectory."
            ),
            parameters=coefficient,
            function=variation,
        ),
        Tool(
            name=SUBMIT,
            description=(
                "Submit a candidate conserved quantity, the sum of the"
                " coefficients times their terms. At most"
                f" {max_candidates} candidates; each is tested on trajectories"
                " you cannot start. It uses no trajectory."
            ),
            parameters=coefficient,
            function=submit,
        ),
    )
    return Allowlist(tools), submitted
