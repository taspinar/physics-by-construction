"""Three bodies under their mutual gravity: an exact solution, its
stability, and a chaotic encounter.

The acceleration, the energy, and the angular momentum are those of
``pbc.mechanics.nbody``, in the plane. Three bodies have no general closed
form, but they have special solutions. In Lagrange's (1772) the bodies
stand at the corners of an equilateral triangle of side a, which turns
rigidly about the centre of mass with the angular speed

    omega = sqrt(G M / a³),    M = m1 + m2 + m3,

for any three masses. Whether a small disturbance of it grows depends on
the masses only through Routh's parameter

    beta = (m1 m2 + m2 m3 + m3 m1) / M².

The disturbances of the shape evolve as exp(lambda t) with
lambda⁴ + omega² lambda² + (27/4) beta omega⁴ = 0 (Routh, 1875): for
27 beta < 1 every root is imaginary and the triangle only oscillates; for
27 beta > 1 two roots have the positive real part

    sigma = (omega / 2) sqrt(sqrt(27 beta) - 1),

the growth rate of the disturbance.

Close encounters, as in the Pythagorean problem, need a step that shrinks
near a collision and grows away from it; ``adaptive`` integrates the same
acceleration with the adaptive Dormand-Prince method of order eight
(``scipy.integrate.solve_ivp``, DOP853), whose tolerance sets the error.
"""

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.integrate import solve_ivp

from pbc.mechanics.dynamics import State, Trajectory
from pbc.mechanics.nbody import barycentric, gravity
from pbc.mechanics.particles import stack, unstack


def _three(masses: ArrayLike) -> NDArray[np.float64]:
    m = np.array(masses, dtype=np.float64)
    if m.shape != (3,) or np.any(m <= 0):
        raise ValueError(f"give three positive masses, got {masses}")
    return m


def lagrange_triangle(G: float, masses: ArrayLike, side: float) -> tuple[State, float]:
    """The state at time zero of Lagrange's solution, the bodies at the
    corners of an equilateral triangle of ``side`` turning anticlockwise
    about their centre of mass, and its angular speed omega.

    Every body moves on a circle about the centre of mass with the same
    omega, so its velocity is omega times its position turned by a quarter
    turn."""
    m = _three(masses)
    if side <= 0 or G <= 0:
        raise ValueError("G and the side must be positive")
    angles = np.pi / 2 + 2 * np.pi / 3 * np.arange(3)
    corners = side / np.sqrt(3) * np.column_stack([np.cos(angles), np.sin(angles)])
    omega = np.sqrt(G * m.sum() / side**3)
    start = barycentric(m, corners, np.zeros((3, 2)))
    positions = unstack(start.x, 3)
    velocities = omega * np.column_stack([-positions[:, 1], positions[:, 0]])
    return State(t=0.0, x=start.x, v=stack(velocities)), omega


def rigid_rotation(start: State, omega: float, t: ArrayLike) -> NDArray:
    """The positions at the times ``t`` of the exact solution that starts at
    ``start`` and turns rigidly with ``omega``, one row of the stacked
    positions per time."""
    times = np.atleast_1d(np.asarray(t, dtype=np.float64))
    positions = unstack(start.x, len(start.x) // 2)
    c, s = np.cos(omega * times), np.sin(omega * times)
    x = c[:, None] * positions[None, :, 0] - s[:, None] * positions[None, :, 1]
    y = s[:, None] * positions[None, :, 0] + c[:, None] * positions[None, :, 1]
    return np.stack([x, y], axis=-1).reshape(len(times), -1)


def routh_beta(masses: ArrayLike) -> float:
    """Routh's parameter (m1 m2 + m2 m3 + m3 m1) / M² of three masses; the
    triangle is linearly stable when 27 times it is below one."""
    m = _three(masses)
    return float((m[0] * m[1] + m[1] * m[2] + m[2] * m[0]) / m.sum() ** 2)


def lagrange_growth_rate(masses: ArrayLike, omega: float) -> float:
    """The predicted growth rate sigma of a small disturbance of Lagrange's
    triangle turning with ``omega``: (omega / 2) sqrt(sqrt(27 beta) - 1),
    and zero where 27 beta <= 1, where the roots are imaginary."""
    k = 27 * routh_beta(masses)
    return 0.5 * omega * np.sqrt(np.sqrt(k) - 1) if k > 1 else 0.0


def lagrange_libration(masses: ArrayLike, omega: float) -> NDArray[np.float64]:
    """The two angular frequencies of the oscillation of a stable triangle,
    omega sqrt((1 -+ sqrt(1 - 27 beta)) / 2), the slow one first."""
    k = 27 * routh_beta(masses)
    if k >= 1:
        raise ValueError("the triangle is unstable: 27 beta >= 1")
    root = np.sqrt(1 - k)
    return omega * np.sqrt(np.array([1 - root, 1 + root]) / 2)


def shape_departure(positions: ArrayLike) -> NDArray:
    """How far three bodies are from an equilateral triangle: the largest
    relative difference of a side from the mean of the three sides, for each
    row of stacked positions. A rotation, a change of scale, and the motion
    of Lagrange's solution leave it at zero."""
    p = np.asarray(positions, dtype=np.float64).reshape(-1, 3, 2)
    sides = np.stack(
        [np.linalg.norm(p[:, i] - p[:, (i + 1) % 3], axis=-1) for i in range(3)],
        axis=-1,
    )
    return np.max(np.abs(sides / sides.mean(axis=-1, keepdims=True) - 1), axis=-1)


def adaptive(
    G: float,
    masses: ArrayLike,
    start: State,
    times: ArrayLike,
    tolerance: float,
) -> Trajectory:
    """The bodies of ``masses`` from ``start`` under their mutual gravity,
    integrated by DOP853 with the relative tolerance ``tolerance`` (and an
    absolute tolerance a hundred times smaller), and read at ``times``."""
    acceleration = gravity(G, masses)
    n = len(start.x)

    def rate(t, y):
        return np.concatenate([y[n:], acceleration(t, y[:n], y[n:])])

    times = np.asarray(times, dtype=np.float64)
    solution = solve_ivp(
        rate,
        (start.t, times[-1]),
        np.concatenate([start.x, start.v]),
        method="DOP853",
        t_eval=times,
        rtol=tolerance,
        atol=tolerance / 100,
    )
    if not solution.success:
        raise RuntimeError(solution.message)
    return Trajectory(t=solution.t, x=solution.y[:n].T, v=solution.y[n:].T)


def pythagorean_start() -> tuple[list[float], State]:
    """Burrau's Pythagorean problem (1913): masses 3, 4, and 5 at rest at the
    corners of a right triangle with sides 3, 4, and 5, each mass opposite
    the side of its own length, with the centre of mass at the origin
    (G = 1)."""
    masses = [3.0, 4.0, 5.0]
    return masses, barycentric(
        masses, [[1.0, 3.0], [-2.0, -1.0], [1.0, -1.0]], np.zeros((3, 2))
    )


def escaper(
    G: float, masses: ArrayLike, positions: ArrayLike, velocities: ArrayLike
) -> tuple[int, float, float]:
    """The body that leaves: the index k of the body outside the most tightly
    bound pair (the pair of lowest two-body energy), the two-body energy of k
    relative to the centre of mass of that pair, and the energy of the pair,
    for the final positions and velocities (one row per body). The body
    escapes for good when its energy is positive and the pair is bound
    (negative)."""
    m = _three(masses)
    x = np.asarray(positions, dtype=np.float64)
    v = np.asarray(velocities, dtype=np.float64)
    best = None
    for k in range(3):
        i, j = (b for b in range(3) if b != k)
        pair = m[i] + m[j]
        centre = (m[i] * x[i] + m[j] * x[j]) / pair
        drift = (m[i] * v[i] + m[j] * v[j]) / pair
        reduced_outer = m[k] * pair / (m[k] + pair)
        reduced_inner = m[i] * m[j] / pair
        outer = 0.5 * reduced_outer * np.sum((v[k] - drift) ** 2)
        outer -= G * m[k] * pair / np.linalg.norm(x[k] - centre)
        inner = 0.5 * reduced_inner * np.sum((v[i] - v[j]) ** 2)
        inner -= G * m[i] * m[j] / np.linalg.norm(x[i] - x[j])
        if best is None or inner < best[2]:
            best = (k, float(outer), float(inner))
    return best
