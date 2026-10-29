"""Special relativity in units with c = 1.

An event is a four-vector (t, x, y, z); a time is measured in the units in
which light covers one unit of length, so a velocity is the fraction beta of
the speed of light. The Minkowski metric diag(-1, 1, 1, 1) gives the
interval between two events,

    s² = -(delta t)² + (delta x)² + (delta y)² + (delta z)²,

the same for every inertial observer. A boost with the velocity beta along
the unit vector n is the Lorentz transformation

    t' = gamma (t - beta n . x),
    x' = x + ((gamma - 1) n . x - gamma beta t) n,
    gamma = 1 / sqrt(1 - beta²),

which keeps the metric: Lambda^T eta Lambda = eta. Two boosts along one line
are one boost whose rapidity, artanh(beta), is the sum of theirs. For a
massive particle the four-momentum is m gamma (1, v); its square gives the
invariant mass, E² - |p|² = m², and the total four-momentum of a collision is
conserved in every frame if it is in one, because the transformation is
linear. As beta goes to zero the transformation becomes Galileo's, x' = x -
v t and t' = t, and the kinetic energy (gamma - 1) m becomes m v² / 2.
"""

import numpy as np
from numpy.typing import ArrayLike, NDArray

METRIC = np.diag([-1.0, 1.0, 1.0, 1.0])


def _speed(beta: ArrayLike) -> NDArray[np.float64]:
    b = np.abs(np.asarray(beta, dtype=np.float64))
    if np.any(b >= 1):
        raise ValueError("a massive body moves slower than light: |beta| < 1")
    return b


def lorentz_factor(beta: ArrayLike) -> NDArray[np.float64]:
    """The Lorentz factor gamma = 1 / sqrt(1 - beta²) of the speed ``beta``
    (a fraction of the speed of light)."""
    return 1 / np.sqrt(1 - _speed(beta) ** 2)


def rapidity(beta: ArrayLike) -> NDArray[np.float64]:
    """The rapidity artanh(beta) of a velocity along a line: rapidities of
    collinear boosts add."""
    _speed(beta)
    return np.arctanh(np.asarray(beta, dtype=np.float64))


def boost(velocity: ArrayLike) -> NDArray[np.float64]:
    """The 4 x 4 Lorentz boost into the frame that moves with the
    three-velocity ``velocity`` (in units of c): it maps the coordinates
    (t, x, y, z) of an event to its coordinates in that frame."""
    v = np.asarray(velocity, dtype=np.float64)
    beta = float(np.linalg.norm(v))
    gamma = float(lorentz_factor(beta))
    matrix = np.eye(4)
    if beta == 0:
        return matrix
    n = v / beta
    matrix[0, 0] = gamma
    matrix[0, 1:] = matrix[1:, 0] = -gamma * beta * n
    matrix[1:, 1:] += (gamma - 1) * np.outer(n, n)
    return matrix


def galilean(velocity: ArrayLike) -> NDArray[np.float64]:
    """The 4 x 4 Galilean transformation into the frame that moves with
    ``velocity``: t' = t and x' = x - v t."""
    matrix = np.eye(4)
    matrix[1:, 0] = -np.asarray(velocity, dtype=np.float64)
    return matrix


def interval(a: ArrayLike, b: ArrayLike | None = None) -> NDArray[np.float64]:
    """The squared interval -(delta t)² + |delta x|² between the events ``a``
    and ``b`` (from the origin when ``b`` is None), for one event or an
    array of events of shape (..., 4): negative for timelike, positive for
    spacelike separations."""
    d = np.asarray(a, dtype=np.float64)
    if b is not None:
        d = d - np.asarray(b, dtype=np.float64)
    return -(d[..., 0] ** 2) + np.sum(d[..., 1:] ** 2, axis=-1)


def add_velocities(u: ArrayLike, v: ArrayLike) -> NDArray[np.float64]:
    """The velocity, in a frame S, of a body that moves with ``u`` along a
    line in a frame that itself moves with ``v`` along the same line in S:
    (u + v) / (1 + u v)."""
    u, v = np.asarray(u, dtype=np.float64), np.asarray(v, dtype=np.float64)
    return (u + v) / (1 + u * v)


def proper_time(events: ArrayLike) -> float:
    """The time a clock shows along the worldline through ``events``, an
    array of shape (n, 4) in time order: the sum of sqrt(-s²) of the
    straight pieces between successive events, which must be timelike. It
    is exact for a worldline made of straight pieces."""
    e = np.asarray(events, dtype=np.float64)
    pieces = -interval(e[1:], e[:-1])
    if np.any(pieces <= 0) or np.any(np.diff(e[:, 0]) <= 0):
        raise ValueError("every piece of a worldline is timelike and future-directed")
    return float(np.sum(np.sqrt(pieces)))


def moving_rod_length(rest_length: float, beta: float) -> float:
    """The length of a rod at rest along x in a frame S' that moves with
    ``beta`` along x, measured in S as the distance between its two ends at
    the same time t = 0 of S. The ends' worldlines x' = 0 and x' = L are
    carried into S by the inverse boost; each end's place at t = 0 is read
    off its straight worldline, so no contraction formula is used."""
    to_s = boost([-beta, 0.0, 0.0])
    ends = []
    for x_rest in (0.0, rest_length):
        # Two events on the end's worldline, at t' = 0 and t' = 1.
        first, second = (to_s @ np.array([t, x_rest, 0.0, 0.0]) for t in (0.0, 1.0))
        fraction = -first[0] / (second[0] - first[0])
        ends.append(first[1] + fraction * (second[1] - first[1]))
    return float(ends[1] - ends[0])


def four_momentum(mass: float, velocity: ArrayLike) -> NDArray[np.float64]:
    """The four-momentum (E, p) = m gamma (1, v) of a particle of rest mass
    ``mass`` moving with the three-velocity ``velocity`` (units of c)."""
    v = np.asarray(velocity, dtype=np.float64)
    gamma = float(lorentz_factor(np.linalg.norm(v)))
    return mass * gamma * np.concatenate([[1.0], v])


def invariant_mass(momentum: ArrayLike) -> NDArray[np.float64]:
    """The invariant mass sqrt(E² - |p|²) of a four-momentum, or of an array
    of them of shape (..., 4)."""
    return np.sqrt(-interval(momentum))


def velocity(momentum: ArrayLike) -> NDArray[np.float64]:
    """The three-velocity p / E of a four-momentum."""
    p = np.asarray(momentum, dtype=np.float64)
    return p[..., 1:] / p[..., :1]


def elastic_collision(
    momenta: ArrayLike, deflection: float = np.pi
) -> NDArray[np.float64]:
    """The four-momenta after an elastic collision of two particles whose
    four-momenta before are the rows of ``momenta``, shape (2, 4): in the
    frame of zero total momentum the two momenta keep their size and turn
    by ``deflection`` about the z axis (pi, a head-on rebound, by default);
    the result is carried back by the inverse boost."""
    p = np.asarray(momenta, dtype=np.float64)
    total = p.sum(axis=0)
    to_centre = boost(total[1:] / total[0])
    c, s = np.cos(deflection), np.sin(deflection)
    turn = np.array([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1.0]])
    return (np.linalg.inv(to_centre) @ turn @ to_centre @ p.T).T


def kinetic_energy(mass: float, beta: ArrayLike) -> NDArray[np.float64]:
    """The relativistic kinetic energy (gamma - 1) m, in units of c² = 1."""
    b = np.asarray(beta, dtype=np.float64)
    # gamma - 1 written as beta² gamma² / (gamma + 1), which loses no digits
    # at small beta.
    gamma = lorentz_factor(b)
    return mass * b**2 * gamma**2 / (gamma + 1)


def newtonian_kinetic_energy(mass: float, beta: ArrayLike) -> NDArray[np.float64]:
    """Newton's kinetic energy m v² / 2, in units of c² = 1."""
    return 0.5 * mass * np.asarray(beta, dtype=np.float64) ** 2
