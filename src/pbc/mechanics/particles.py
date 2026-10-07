"""Several particles that act on one another in pairs, on the stepping
interface of one particle.

The state of n particles in d dimensions is one vector of length n d: the
position of the first particle, then the second, and so on, and the
velocities likewise. ``stack`` and ``unstack`` convert between that vector
and an array with one row per particle. ``interacting`` turns the masses
and one pairwise force into the acceleration function that ``simulate``
and every stepper of the course take, so the simulation loop and the
integrators are the ones of the earlier lessons, unchanged.

A pairwise force is given once, as the force on the first particle of a
pair as a function of its position relative to the second; the second
particle feels the opposite force. Newton's third law is built into the
interface, and with it the conservation of the total momentum, which every
integrator of the course then keeps to round-off.

Quantities are in SI units as in ``pbc.mechanics.dynamics``.
"""

from collections.abc import Callable

import numpy as np
from numpy.typing import ArrayLike, NDArray

from pbc.mechanics.dynamics import Acceleration, Vector

# A pairwise force: F(r) is the force in N on a particle at the position r
# (m) relative to its partner; the partner feels -F(r). The force acts along
# the line between the two when it depends on r only through |r|.
type PairwiseForce = Callable[[Vector], Vector]


def stack(rows: ArrayLike) -> Vector:
    """The positions or velocities of n particles, one row each, as the one
    vector of length n d that the state of the system holds."""
    return np.array(rows, dtype=np.float64, ndmin=2).reshape(-1)


def unstack(flat: ArrayLike, n: int) -> NDArray[np.float64]:
    """The vector of length n d back to one row per particle, shape (n, d);
    an array of such vectors, such as the positions of a trajectory with
    shape (steps, n d), becomes an array of shape (steps, n, d)."""
    if n <= 0:
        raise ValueError(f"the number of particles must be positive, got {n}")
    array = np.array(flat, dtype=np.float64)
    if array.shape[-1] % n:
        raise ValueError(
            f"a vector of length {array.shape[-1]} does not hold {n} particles"
        )
    return array.reshape(*array.shape[:-1], n, -1)


def _masses(masses: ArrayLike) -> NDArray[np.float64]:
    array = np.array(masses, dtype=np.float64, ndmin=1)
    if array.ndim != 1 or np.any(array <= 0):
        raise ValueError(f"the masses must be a list of positive numbers, got {masses}")
    return array


def interacting(masses: ArrayLike, pairwise: PairwiseForce) -> Acceleration:
    """The acceleration of n particles with the given ``masses`` (kg) that act
    on one another through the ``pairwise`` force.

    For every pair the force on the first particle is ``pairwise`` of its
    position relative to the second, and the second feels the opposite, so
    the forces sum to zero over the system. The acceleration of each
    particle is the sum of the forces on it divided by its mass. The state
    is the stacked vector of ``stack``.
    """
    m = _masses(masses)
    n = len(m)

    def acceleration(t: float, x: Vector, v: Vector) -> Vector:
        positions = unstack(x, n)
        forces = np.zeros_like(positions)
        for i in range(n):
            for j in range(i + 1, n):
                force = pairwise(positions[i] - positions[j])
                forces[i] += force
                forces[j] -= force
        return (forces / m[:, np.newaxis]).reshape(-1)

    return acceleration


def centre_of_mass(masses: ArrayLike, positions: ArrayLike) -> NDArray[np.float64]:
    """The centre of mass (sum of m_i x_i) / (sum of m_i) of particles with
    the given ``masses``, for ``positions`` with one row per particle; an
    array of such rows, shape (steps, n, d), gives one centre per step."""
    m = _masses(masses)
    weighted = np.tensordot(
        np.asarray(positions, dtype=np.float64), m, axes=([-2], [0])
    )
    return weighted / m.sum()


def total_momentum(masses: ArrayLike, velocities: ArrayLike) -> NDArray[np.float64]:
    """The total momentum, the sum of m_i v_i in kg m/s, for ``velocities``
    with one row per particle, or one such array per step."""
    m = _masses(masses)
    return np.tensordot(np.asarray(velocities, dtype=np.float64), m, axes=([-2], [0]))


def kinetic_energy(masses: ArrayLike, velocities: ArrayLike) -> NDArray[np.float64]:
    """The kinetic energy, the sum of m_i |v_i|² / 2 in J, for ``velocities``
    with one row per particle, or one value per step for an array of
    them."""
    m = _masses(masses)
    speeds_squared = np.sum(np.asarray(velocities, dtype=np.float64) ** 2, axis=-1)
    return 0.5 * speeds_squared @ m


def reduced_mass(m1: float, m2: float) -> float:
    """The reduced mass m1 m2 / (m1 + m2) in kg of a pair: the mass whose
    motion under the pair force is the relative motion of the two."""
    m = _masses([m1, m2])
    return float(m[0] * m[1] / m.sum())


def spring_pair(k: float, rest_length: float) -> PairwiseForce:
    """A spring with the constant ``k`` (N/m) and the ``rest_length`` (m)
    between two particles: the force -k (|r| - L_0) r / |r| on the first,
    along the line between them, pulling when the spring is stretched and
    pushing when it is compressed."""
    if k <= 0:
        raise ValueError(f"the spring constant must be positive, got {k}")
    if rest_length < 0:
        raise ValueError(f"the rest length must not be negative, got {rest_length}")

    def force(r: Vector) -> Vector:
        distance = np.sqrt(r @ r)
        return -k * (distance - rest_length) * r / distance

    return force


def soft_sphere(k: float, diameter: float) -> PairwiseForce:
    """Two spheres that repel only while they overlap, with the force
    k (D - |r|) r / |r| on the first for |r| < D and no force otherwise:
    a spring of stiffness ``k`` (N/m) that acts only in compression, with
    ``diameter`` D the sum of the two radii (m).

    A head-on collision under this force lasts pi sqrt(mu / k) with mu the
    reduced mass of the pair and ends as the hard-sphere collision of
    ``hard_sphere_collision``, provided the spheres turn before their
    centres meet: the relative speed u must satisfy |u| sqrt(mu / k) < D,
    the relative kinetic energy below k D² / 2. Faster pairs carry enough
    kinetic energy to cross the finite potential barrier k D² / 2 and pass
    through each other: once the centres cross, r reverses, the repulsion
    reverses with it and now drives the pair apart, vanishing only when they
    cease to overlap. A simulation must resolve the contact time; as k grows
    the contact shortens and the outcome tends to the hard-sphere one.
    """
    if k <= 0:
        raise ValueError(f"the stiffness must be positive, got {k}")
    if diameter <= 0:
        raise ValueError(f"the diameter must be positive, got {diameter}")

    def force(r: Vector) -> Vector:
        distance = np.sqrt(r @ r)
        if distance >= diameter:
            return np.zeros_like(r)
        return k * (diameter - distance) * r / distance

    return force


def first_contact(r: Vector, u: Vector, diameter: float) -> tuple[float, Vector]:
    """When two spheres on straight paths first touch, and how.

    ``r`` is the position of the first sphere relative to the second (m) and
    ``u`` its velocity relative to the second (m/s), both now; ``diameter``
    is the sum of the radii. Returns the time until |r + u t| = diameter and
    the unit vector along the line of centres at that moment, from the
    second sphere to the first. Raises ``ValueError`` when the spheres
    already overlap or never meet.
    """
    r = np.array(r, dtype=np.float64, ndmin=1)
    u = np.array(u, dtype=np.float64, ndmin=1)
    if r @ r <= diameter**2:
        raise ValueError("the spheres already overlap")
    # |r + u t|² = D²: a quadratic in t; the smaller root is the first touch.
    a, b, c = u @ u, 2.0 * (r @ u), r @ r - diameter**2
    discriminant = b**2 - 4.0 * a * c
    if a == 0 or discriminant < 0 or b >= 0:
        raise ValueError("the spheres never meet")
    t = (-b - np.sqrt(discriminant)) / (2.0 * a)
    contact = r + u * t
    return float(t), contact / diameter


def hard_sphere_collision(
    m1: float, v1: Vector, m2: float, v2: Vector, normal: Vector
) -> tuple[Vector, Vector]:
    """The velocities after an elastic collision of two hard spheres.

    ``normal`` is the unit vector along the line of centres at contact, from
    the second sphere to the first. Momentum and kinetic energy are
    conserved, and the impulse acts along the normal, so the component of
    the relative velocity along the normal reverses and the components
    across it are unchanged:

        v1' = v1 - 2 m2 / (m1 + m2) ((v1 - v2) . n) n,
        v2' = v2 + 2 m1 / (m1 + m2) ((v1 - v2) . n) n.

    Head on, with equal masses, the spheres exchange velocities.
    """
    m = _masses([m1, m2])
    v1 = np.array(v1, dtype=np.float64, ndmin=1)
    v2 = np.array(v2, dtype=np.float64, ndmin=1)
    n = np.array(normal, dtype=np.float64, ndmin=1)
    approach = (v1 - v2) @ n
    return (
        v1 - 2.0 * m[1] / m.sum() * approach * n,
        v2 + 2.0 * m[0] / m.sum() * approach * n,
    )


# A pairwise potential energy: U(r) is the potential energy in J of a pair
# at the relative position r (m); the pairwise force is minus its gradient.
type PairwisePotential = Callable[[Vector], float]


def soft_sphere_potential(k: float, diameter: float) -> PairwisePotential:
    """The energy k (D - |r|)² / 2 stored in the compression of two soft
    spheres that overlap, and 0 when they do not: the potential of
    ``soft_sphere``. During a collision the kinetic energy the pair loses
    is held here and given back."""
    if k <= 0:
        raise ValueError(f"the stiffness must be positive, got {k}")
    if diameter <= 0:
        raise ValueError(f"the diameter must be positive, got {diameter}")

    def potential(r: Vector) -> float:
        distance = np.sqrt(r @ r)
        return (
            float(0.5 * k * (diameter - distance) ** 2) if distance < diameter else 0.0
        )

    return potential


def pair_potential_energy(
    positions: ArrayLike, potential: PairwisePotential
) -> NDArray[np.float64]:
    """The potential energy of a system, the sum of U(x_i - x_j) over its
    pairs, for ``positions`` with one row per particle, or one value per
    step for an array of them with shape (steps, n, d)."""
    array = np.array(positions, dtype=np.float64)
    if array.ndim == 2:
        n = array.shape[0]
        return np.array(
            sum(
                potential(array[i] - array[j])
                for i in range(n)
                for j in range(i + 1, n)
            ),
            dtype=np.float64,
        )
    return np.array([pair_potential_energy(rows, potential) for rows in array])
