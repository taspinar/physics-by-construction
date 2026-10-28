"""A spin one half: its states, the probabilities of a measurement along any
direction, and the Stern-Gerlach apparatus that performs the measurement.

A state is a normalised complex vector (a, b) in the basis of spin up and
spin down along z. The measurement along the unit vector n has the outcomes
+1 and -1, with the projectors P(+-n) = (1 +- n . sigma) / 2 built from the
Pauli matrices, and the Born rule gives p(+n) = <psi| P(+n) |psi>. For the
state along the direction at the angle theta from n, p(+n) = cos^2(theta / 2).
After the outcome s the state is P(s n) psi, normalised: the atom leaves the
magnet with its spin along s n.

The apparatus is modelled as a magnet of length L whose field has a uniform
gradient G along z, and a free drift D to the screen. An atom of mass m and
speed v with the moment component mu_z feels the constant force mu_z G in
the magnet, and reaches the screen displaced by

    z = (mu_z G / m v^2) (L^2 / 2 + L D).
"""

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.constants import physical_constants

Array = NDArray[np.float64]
State = NDArray[np.complex128]

IDENTITY = np.eye(2, dtype=complex)
SIGMA_X = np.array([[0, 1], [1, 0]], dtype=complex)
SIGMA_Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
SIGMA_Z = np.array([[1, 0], [0, -1]], dtype=complex)

# The magnitude of the electron's magnetic moment (J/T, CODATA): the moment
# of a silver atom, whose one outer electron carries its spin.
ELECTRON_MOMENT = abs(physical_constants["electron mag. mom."][0])
ATOMIC_MASS = physical_constants["atomic mass constant"][0]  # kg
SILVER_MASS = 107.8682 * ATOMIC_MASS  # kg, the standard atomic weight of silver


def direction(theta: float, phi: float = 0.0) -> Array:
    """The unit vector at the polar angle ``theta`` from z and the azimuth
    ``phi`` from x."""
    return np.array(
        [np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)]
    )


def spin_state(theta: float, phi: float = 0.0) -> State:
    """The state of spin up along ``direction(theta, phi)``,
    (cos(theta / 2), exp(i phi) sin(theta / 2))."""
    return np.array([np.cos(theta / 2), np.exp(1j * phi) * np.sin(theta / 2)])


def spin_operator(n: ArrayLike) -> NDArray[np.complex128]:
    """n . sigma, whose eigenvalues +1 and -1 are the outcomes along n."""
    nx, ny, nz = np.asarray(n, dtype=float)
    return nx * SIGMA_X + ny * SIGMA_Y + nz * SIGMA_Z


def projector(n: ArrayLike, outcome: int) -> NDArray[np.complex128]:
    """The projector (1 + outcome n . sigma) / 2 on the outcome +1 or -1."""
    if outcome not in (1, -1):
        raise ValueError(f"an outcome is +1 or -1, not {outcome!r}")
    return (IDENTITY + outcome * spin_operator(n)) / 2


def probability(state: ArrayLike, n: ArrayLike, outcome: int = 1) -> float:
    """The Born rule, <psi| P |psi>, for the outcome along n."""
    psi = np.asarray(state, dtype=complex)
    return float(np.real(np.vdot(psi, projector(n, outcome) @ psi)))


def born_angle(theta: ArrayLike) -> Array:
    """p(+n) = cos^2(theta / 2) for a state at the angle theta from n."""
    return np.cos(np.asarray(theta, dtype=float) / 2) ** 2


def bloch_vector(state: ArrayLike) -> Array:
    """(<sigma_x>, <sigma_y>, <sigma_z>) of a state, a unit vector along the
    direction the spin points."""
    psi = np.asarray(state, dtype=complex)
    return np.array(
        [np.real(np.vdot(psi, s @ psi)) for s in (SIGMA_X, SIGMA_Y, SIGMA_Z)]
    )


def measure(
    state: ArrayLike, n: ArrayLike, rng: np.random.Generator
) -> tuple[int, State]:
    """One measurement along n: the outcome, drawn with the Born
    probabilities, and the state after it, the normalised projection."""
    psi = np.asarray(state, dtype=complex)
    outcome = 1 if rng.random() < probability(psi, n) else -1
    after = projector(n, outcome) @ psi
    return outcome, after / np.linalg.norm(after)


def sample_outcomes(
    state: ArrayLike, n: ArrayLike, count: int, rng: np.random.Generator
) -> int:
    """How many of ``count`` atoms in ``state`` give +1 along n: a binomial
    draw with the Born probability."""
    return int(rng.binomial(count, probability(state, n)))


def standard_error(p: ArrayLike, count: int) -> Array:
    """sqrt(p (1 - p) / N), the standard deviation of the fraction of N
    independent outcomes that are +1 when each is +1 with the probability p."""
    p = np.asarray(p, dtype=float)
    return np.sqrt(p * (1 - p) / count)


def filters(
    state: ArrayLike, axes: list[ArrayLike], rng: np.random.Generator
) -> list[int]:
    """One atom through magnets in a row, each along one of ``axes``, with
    the beam of -1 blocked after each: the outcomes until the atom is
    blocked (the last is then -1) or has passed them all."""
    outcomes, psi = [], np.asarray(state, dtype=complex)
    for axis in axes:
        outcome, psi = measure(psi, axis, rng)
        outcomes.append(outcome)
        if outcome == -1:
            break
    return outcomes


def deflection(
    moment: ArrayLike,
    gradient: float,
    length: float,
    drift: float,
    speed: float,
    mass: float = SILVER_MASS,
) -> Array:
    """The displacement on the screen (m) of an atom with the moment
    component ``moment`` (J/T) along z, through a magnet of ``length`` (m)
    with the field gradient ``gradient`` (T/m) and a ``drift`` (m) to the
    screen, at ``speed`` (m/s): (mu_z G / m v^2) (L^2 / 2 + L D)."""
    acceleration = np.asarray(moment, dtype=float) * gradient / mass
    return acceleration * (length**2 / 2 + length * drift) / speed**2
