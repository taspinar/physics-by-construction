"""Many bodies under their mutual gravity, in the plane.

Every pair of n bodies attracts with Newton's force -G m_i m_j r / |r|³,
r = x_i - x_j, so body i has the acceleration

    a_i = -G sum over j != i of m_j (x_i - x_j) / |x_i - x_j|³.

The forces of a pair are equal and opposite and act along the line between
the two, so the total momentum and the total angular momentum are
conserved, and the force has a potential, so the total energy

    E = sum of m_i |v_i|² / 2  -  sum over pairs of G m_i m_j / |x_i - x_j|

is conserved too. There is no closed form for three or more bodies; these
three conserved quantities, and the two-body case, which is Kepler's
problem, are what a simulation is checked against.

The state of the system is the stacked vector of ``pbc.mechanics.particles``
(one row per body, flattened), so the course's integrators step it
unchanged. The functions take G as an argument, so any consistent system
of units serves; the lesson uses astronomical units, years, and solar
masses, with G = 4 pi² AU³ / (M_sun yr²). Positions and velocities are
vectors in the plane of the motion.
"""

import numpy as np
from numpy.typing import ArrayLike, NDArray

from pbc.mechanics.dynamics import Acceleration, State, Trajectory, Vector
from pbc.mechanics.particles import stack, unstack


def _masses(masses: ArrayLike) -> NDArray[np.float64]:
    array = np.array(masses, dtype=np.float64, ndmin=1)
    if array.ndim != 1 or len(array) < 2 or np.any(array <= 0):
        raise ValueError(
            f"the masses must be a list of at least two positive numbers, got {masses}"
        )
    return array


def _check_g(G: float) -> None:
    if G <= 0:
        raise ValueError(f"G must be positive, got {G}")


def gravity(G: float, masses: ArrayLike) -> Acceleration:
    """The acceleration a(t, x, v) of n bodies of ``masses`` under their
    mutual gravity with the constant ``G``, on the stacked state.

    All pairs at once: the separations x_i - x_j form an array of shape
    (n, n, d), the factor m_j / |x_i - x_j|³ an array of shape (n, n) with
    zero on the diagonal, where a body would act on itself.
    """
    _check_g(G)
    m = _masses(masses)
    n = len(m)
    others = ~np.eye(n, dtype=bool)

    def acceleration(t: float, x: Vector, v: Vector) -> Vector:
        positions = unstack(x, n)
        separation = positions[:, np.newaxis, :] - positions[np.newaxis, :, :]
        distance = np.sqrt(np.sum(separation**2, axis=-1))
        weight = np.zeros((n, n))
        weight[others] = m[np.nonzero(others)[1]] / distance[others] ** 3
        return (-G * np.einsum("ij,ijk->ik", weight, separation)).reshape(-1)

    return acceleration


def potential_energy(G: float, masses: ArrayLike, positions: ArrayLike) -> NDArray:
    """The potential energy, minus the sum over pairs of G m_i m_j / |x_i - x_j|,
    for ``positions`` with one row per body, or one value per step for an
    array of shape (steps, n, d)."""
    _check_g(G)
    m = _masses(masses)
    p = np.asarray(positions, dtype=np.float64)
    total = np.zeros(p.shape[:-2])
    for i in range(len(m)):
        for j in range(i + 1, len(m)):
            r = p[..., i, :] - p[..., j, :]
            total = total - G * m[i] * m[j] / np.sqrt(np.sum(r**2, axis=-1))
    return total


def total_energy(G: float, masses: ArrayLike, trajectory: Trajectory) -> NDArray:
    """The kinetic plus the potential energy at every instant of a
    ``trajectory`` of the stacked state."""
    m = _masses(masses)
    n = len(m)
    v = unstack(trajectory.v, n)
    kinetic = 0.5 * np.sum(v**2, axis=-1) @ m
    return kinetic + potential_energy(G, m, unstack(trajectory.x, n))


def angular_momentum(masses: ArrayLike, trajectory: Trajectory) -> NDArray:
    """The total angular momentum about the origin, the sum of
    m_i (x_i v_y,i - y_i v_x,i), at every instant of a ``trajectory`` in the
    plane: the component perpendicular to it, positive for anticlockwise
    motion."""
    m = _masses(masses)
    n = len(m)
    x, v = unstack(trajectory.x, n), unstack(trajectory.v, n)
    if x.shape[-1] != 2:
        raise ValueError(
            "the angular momentum is computed in the plane (two coordinates)"
        )
    return (x[..., 0] * v[..., 1] - x[..., 1] * v[..., 0]) @ m


def barycentric(
    masses: ArrayLike, positions: ArrayLike, velocities: ArrayLike
) -> State:
    """The state at time zero of bodies with the given ``positions`` and
    ``velocities`` (one row per body), moved to the frame in which the centre
    of mass is at rest at the origin. In that frame the system does not
    drift away, and the angular momentum is the one about the centre."""
    m = _masses(masses)
    x = np.array(positions, dtype=np.float64)
    v = np.array(velocities, dtype=np.float64)
    if x.shape != v.shape or x.shape[0] != len(m):
        raise ValueError("give one position and one velocity row per body")
    x = x - m @ x / m.sum()
    v = v - m @ v / m.sum()
    return State(t=0.0, x=stack(x), v=stack(v))
