"""Two bodies under their mutual gravity, and the orbit of one about the
other.

The relative position r = x_1 - x_2 of two bodies that attract each other
with the force -G m_1 m_2 r / |r|³ obeys the equation of one particle of the
reduced mass mu = m_1 m_2 / (m_1 + m_2) under the central force
-G (m_1 + m_2) mu r / |r|³: the two-body problem is a one-body problem about
a fixed centre with the gravitational parameter GM = G (m_1 + m_2). The
motion stays in a plane, its energy and its angular momentum are constant,
and a bound orbit is an ellipse with the centre at a focus, traced in the
period 2 pi sqrt(a³ / GM). The functions here give the forces for both
descriptions, the conserved quantities, the elements of the orbit, and the
exact motion, from Kepler's equation, for a simulation to be checked
against.

The functions take G or GM as an argument, so any consistent system of
units serves; the SI value of G is ``scipy.constants.G``. The orbit lesson
uses astronomical units, years, and solar masses, in which
G = 4 pi² AU³ / (M_sun yr²) to the precision of the lesson. Positions and
velocities are vectors in the plane of the orbit.
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from pbc.mechanics.dynamics import Force, State, Trajectory, Vector
from pbc.mechanics.energy import Potential
from pbc.mechanics.particles import PairwiseForce


def _check_positive(name: str, value: float) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")


def gravitational_attraction(G: float, m1: float, m2: float) -> PairwiseForce:
    """Newton's law of gravitation between two bodies of masses ``m1`` and
    ``m2``: the force -G m1 m2 r / |r|³ on the first, at the position r
    relative to the second, as a pairwise force for
    ``pbc.mechanics.particles.interacting``."""
    for name, value in (("G", G), ("m1", m1), ("m2", m2)):
        _check_positive(name, value)

    def force(r: Vector) -> Vector:
        return -G * m1 * m2 * r / np.sqrt(r @ r) ** 3

    return force


def central_gravity(gm: float, mass: float) -> Force:
    """The inverse-square force -GM m x / |x|³ on a body of ``mass`` at the
    position x from a fixed centre with the gravitational parameter ``gm``
    = G M. With ``mass`` the reduced mass and ``gm`` = G (m1 + m2) it is the
    force of the relative motion of two bodies."""
    _check_positive("gm", gm)
    _check_positive("mass", mass)

    def force(t: float, x: Vector, v: Vector) -> Vector:
        return -gm * mass * x / np.sqrt(x @ x) ** 3

    return force


def gravitational_potential(gm: float, mass: float) -> Potential:
    """The potential energy -GM m / |x| of ``central_gravity``, zero at
    infinite distance, so that a bound orbit has negative energy."""
    _check_positive("gm", gm)
    _check_positive("mass", mass)

    def potential(x: Vector) -> float:
        return float(-gm * mass / np.sqrt(x @ x))

    return potential


def _cross(x: NDArray[np.float64], v: NDArray[np.float64]) -> NDArray[np.float64]:
    """The cross product of vectors in the plane: the component out of it."""
    if x.shape[-1] != 2:
        raise ValueError(
            "the orbit functions work in the plane of the orbit (two coordinates)"
        )
    return x[..., 0] * v[..., 1] - x[..., 1] * v[..., 0]


def angular_momentum(trajectory: Trajectory, mass: float) -> NDArray[np.float64]:
    """The angular momentum m (x v_y - y v_x) about the origin, in kg m²/s,
    at every instant of a ``trajectory`` in the plane: the component
    perpendicular to the plane, positive for anticlockwise motion. A central
    force keeps it constant."""
    _check_positive("mass", mass)
    return mass * _cross(trajectory.x, trajectory.v)


@dataclass(frozen=True)
class Orbit:
    """The shape and the period of a bound orbit about a centre of
    attraction."""

    semi_major_axis: float  # a: half the longest diameter of the ellipse
    eccentricity: float  # e: 0 for a circle, approaching 1 for a long, thin ellipse
    period: float  # T = 2 pi sqrt(a³ / GM), Kepler's third law

    @property
    def periapsis(self) -> float:
        """The closest distance to the centre, a (1 - e)."""
        return self.semi_major_axis * (1.0 - self.eccentricity)

    @property
    def apoapsis(self) -> float:
        """The farthest distance from the centre, a (1 + e)."""
        return self.semi_major_axis * (1.0 + self.eccentricity)


def orbital_elements(state: State, gm: float) -> Orbit:
    """The orbit through ``state`` about a centre at the origin with the
    gravitational parameter ``gm``, from the two conserved quantities.

    With the energy per unit mass epsilon = |v|² / 2 - GM / |x| and the
    angular momentum per unit mass h = x v_y - y v_x,

        a = -GM / (2 epsilon),    e = sqrt(1 + 2 epsilon h² / GM²),
        T = 2 pi sqrt(a³ / GM).

    The eccentricity is evaluated as the length of ``eccentricity_vector``,
    which equals the square root above exactly but not in floating point:
    near a circle the expression under the root is the difference of two
    numbers close to 1, and its round-off of about 1e-16 becomes an
    eccentricity of about 1e-8 after the root, while the vector carries the
    round-off itself.

    The orbit must be bound, epsilon < 0; a state at or above the escape
    speed sqrt(2 GM / |x|) raises ``ValueError``. The orbit must also turn,
    h != 0: a body moving straight towards or away from the centre falls
    into it along a line, a degenerate ellipse of eccentricity 1 with no
    plane and no periapsis to orient it, and raises ``ValueError`` too.
    """
    _check_positive("gm", gm)
    r = np.sqrt(state.x @ state.x)
    epsilon = 0.5 * (state.v @ state.v) - gm / r
    if epsilon >= 0:
        raise ValueError(
            f"the orbit is not bound: the energy per unit mass is {epsilon:.4g},"
            " not negative"
        )
    if _cross(state.x, state.v) == 0.0:
        raise ValueError(
            "the orbit is radial: the angular momentum is zero, so the body"
            " falls into the centre along a line instead of tracing an ellipse"
        )
    a = -gm / (2.0 * epsilon)
    ecc = eccentricity_vector(state, gm)
    e = float(np.sqrt(ecc @ ecc))
    return Orbit(float(a), e, float(2.0 * np.pi * np.sqrt(a**3 / gm)))


def eccentricity_vector(state: State, gm: float) -> Vector:
    """The vector e = (|v|² x - (x . v) v) / GM - x / |x|, which points from
    the centre to the periapsis and has the eccentricity as its length. It
    is constant on the exact orbit; a simulation that turns it is
    precessing."""
    _check_positive("gm", gm)
    x, v = state.x, state.v
    return ((v @ v) * x - (x @ v) * v) / gm - x / np.sqrt(x @ x)


def _solve_kepler(mean_anomaly: NDArray[np.float64], e: float) -> NDArray[np.float64]:
    """E - e sin E = M for E, by Newton's method from Danby's starting value."""
    E = mean_anomaly + 0.85 * e * np.sign(np.sin(mean_anomaly))
    for _ in range(50):
        step = (E - e * np.sin(E) - mean_anomaly) / (1.0 - e * np.cos(E))
        E = E - step
        if np.all(np.abs(step) < 1e-15):
            break
    return E


def kepler_motion(initial: State, gm: float, t: ArrayLike) -> Trajectory:
    """The exact motion from ``initial`` about a centre at the origin with the
    gravitational parameter ``gm``, evaluated at the times ``t``.

    The orbit is the ellipse of ``orbital_elements``, oriented by the
    eccentricity vector. Each time is turned into the mean anomaly
    M = M_0 + n (t - t_0) with the mean motion n = 2 pi / T, Kepler's
    equation E - e sin E = M is solved for the eccentric anomaly E, and the
    position and velocity follow from E in the frame of the ellipse:

        x = a (cos E - e) P + a sqrt(1 - e²) sin E Q,
        v = sqrt(GM a) / |x| (-sin E P + sqrt(1 - e²) cos E Q),

    with P the unit vector towards the periapsis and Q the unit vector a
    quarter turn ahead in the direction of the motion. The orbit must be
    bound and must have a nonzero angular momentum, as for
    ``orbital_elements``; a radial infall raises ``ValueError``. ``t`` is a
    scalar or an array; the arrays of the result have one row per time.
    """
    orbit = orbital_elements(initial, gm)
    a, e = orbit.semi_major_axis, orbit.eccentricity
    n = 2.0 * np.pi / orbit.period
    h = float(_cross(initial.x, initial.v))
    ecc = eccentricity_vector(initial, gm)
    # e is the length of ecc, so P is a unit vector whenever e > 0, however
    # small. A circle has no periapsis; any direction then serves as the
    # reference, and the eccentric anomaly below is measured from it.
    P = ecc / e if e > 0.0 else initial.x / np.sqrt(initial.x @ initial.x)
    Q = np.sign(h) * np.array([-P[1], P[0]])
    b = a * np.sqrt(1.0 - e**2)
    # The eccentric anomaly at the initial time, from the position.
    E_0 = np.arctan2((initial.x @ Q) / b, (initial.x @ P) / a + e)
    M_0 = E_0 - e * np.sin(E_0)

    times = np.array(t, dtype=np.float64, ndmin=1)
    E = _solve_kepler(M_0 + n * (times - initial.t), e)
    cos, sin = np.cos(E)[:, np.newaxis], np.sin(E)[:, np.newaxis]
    x = a * (cos - e) * P + b * sin * Q
    r = a * (1.0 - e * np.cos(E))[:, np.newaxis]
    v = np.sqrt(gm * a) / r * (-sin * P + np.sqrt(1.0 - e**2) * cos * Q)
    return Trajectory(t=times, x=x, v=v)
