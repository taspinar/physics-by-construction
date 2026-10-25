"""Rigid bodies that turn: the inertia tensor, torque, angular momentum,
and the heavy symmetric top.

A rigid body turning with the angular velocity omega has the angular
momentum L = I omega, where I is the inertia tensor: for point masses m_k at
the positions r_k from the reference point,

    I = sum of m_k (|r_k|² 1 - r_k r_kᵀ),

a symmetric 3 by 3 matrix. Its eigenvectors are the principal axes and its
eigenvalues the principal moments; L is parallel to omega only along a
principal axis. The torque changes the angular momentum, dL/dt = tau, and
the kinetic energy of the rotation is omega · L / 2.

The heavy symmetric top is a body with two equal principal moments I₁ (about
the pivot) and a third, I₃, about its symmetry axis, held at a fixed pivot
on its axis, with the centre of mass at the distance l along the axis.
Gravity exerts the torque tau = l e₃ cross (-m g z), horizontal, so the vertical
component of L is conserved; the symmetry makes the component along the
axis, I₃ omega₃, conserved too, and the energy
omega · L / 2 + m g l cos theta is conserved because gravity is
conservative. A fast top precesses: its axis turns about the vertical at
the rate m g l / (I₃ omega₃) in the limit of a large spin omega₃.

The program integrates the top in the space frame: the orientation as a
unit quaternion q, which turns body vectors into space vectors, and the
angular momentum L in space. The angular velocity is omega = I⁻¹ L, with
the inertia tensor turned into space, I = R diag(I₁, I₁, I₃) Rᵀ; the
quaternion follows dq/dt = (0, omega) q / 2 and the momentum dL/dt = tau.
There are no Euler angles in the equations, so the vertical axis is no
singularity.

Quantities are in SI units: kg, m, s, rad, kg m² for moments, kg m²/s for
angular momenta, N m for torques, J for energies; any consistent system of
units works the same.
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

type Vector3 = NDArray[np.float64]

VERTICAL = np.array([0.0, 0.0, 1.0])


def inertia_tensor(masses: ArrayLike, positions: ArrayLike) -> NDArray[np.float64]:
    """The inertia tensor, sum of m_k (|r_k|² 1 - r_k r_kᵀ) in kg m², of point
    ``masses`` (kg) at ``positions`` (m, one row of three per mass) about the
    origin."""
    m = np.asarray(masses, dtype=np.float64)
    r = np.asarray(positions, dtype=np.float64)
    if r.ndim != 2 or r.shape != (len(m), 3):
        raise ValueError("give one position of three coordinates per mass")
    squared = np.sum(r**2, axis=1)
    return np.einsum(
        "k,kij->ij",
        m,
        squared[:, None, None] * np.eye(3) - r[:, :, None] * r[:, None, :],
    )


def parallel_axis(
    inertia_centre: ArrayLike, mass: float, offset: ArrayLike
) -> NDArray[np.float64]:
    """The inertia tensor about a point at ``offset`` (m) from the centre of
    mass, from the tensor ``inertia_centre`` (kg m²) about the centre and the
    total ``mass`` (kg): I + m (|d|² 1 - d dᵀ), the parallel-axis theorem."""
    d = np.asarray(offset, dtype=np.float64)
    return np.asarray(inertia_centre, dtype=np.float64) + mass * (
        (d @ d) * np.eye(3) - np.outer(d, d)
    )


def rotation_matrix(q: ArrayLike) -> NDArray[np.float64]:
    """The rotation matrix of the unit quaternion q = (w, x, y, z)."""
    w, x, y, z = np.asarray(q, dtype=np.float64)
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
            [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
            [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
        ]
    )


def _product(a: NDArray[np.float64], b: NDArray[np.float64]) -> NDArray[np.float64]:
    """The quaternion product a b."""
    aw, av = a[0], a[1:]
    bw, bv = b[0], b[1:]
    return np.concatenate([[aw * bw - av @ bv], aw * bv + bw * av + np.cross(av, bv)])


@dataclass(frozen=True)
class Top:
    """A heavy symmetric top on a fixed pivot."""

    mass: float  # m, kg
    length: float  # l, m: from the pivot to the centre of mass, along the axis
    i1: float  # I₁, kg m²: about an axis through the pivot, across the symmetry axis
    i3: float  # I₃, kg m²: about the symmetry axis
    g: float = 9.81  # m/s²

    def __post_init__(self) -> None:
        for name in ("mass", "length", "i1", "i3", "g"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")

    def body_inertia(self) -> NDArray[np.float64]:
        """The principal moments as the diagonal tensor of the body frame."""
        return np.diag([self.i1, self.i1, self.i3])

    # region: top-equations
    def _torque(self, rotation: NDArray[np.float64]) -> Vector3:
        return np.cross(self.length * rotation[:, 2], -self.mass * self.g * VERTICAL)

    def _angular_velocity(
        self, rotation: NDArray[np.float64], momentum: ArrayLike
    ) -> Vector3:
        # R diag(1/I) Rᵀ L, from right to left: L into the body, divided by
        # the principal moments, back into space.
        body = rotation.T @ np.asarray(momentum, dtype=np.float64)
        return rotation @ (body / np.array([self.i1, self.i1, self.i3]))

    # endregion: top-equations

    def torque(self, q: ArrayLike) -> Vector3:
        """The torque of gravity about the pivot, l e₃ cross (-m g z), in N m."""
        return self._torque(rotation_matrix(q))

    def angular_velocity(self, q: ArrayLike, momentum: ArrayLike) -> Vector3:
        """omega = I⁻¹ L in rad/s, with the inertia tensor turned into space."""
        return self._angular_velocity(rotation_matrix(q), momentum)


@dataclass(frozen=True)
class TopMotion:
    """The orientations and angular momenta of a simulated top."""

    t: NDArray[np.float64]  # times, s, shape (n,)
    q: NDArray[np.float64]  # unit quaternions, shape (n, 4)
    momentum: NDArray[np.float64]  # angular momentum in space, kg m²/s, shape (n, 3)

    def axes(self) -> NDArray[np.float64]:
        """The symmetry axis e₃ in space at every instant, shape (n, 3)."""
        return np.array([rotation_matrix(q)[:, 2] for q in self.q])


def tilted_start(
    top: Top, tilt: float, spin: float, precession: float = 0.0
) -> tuple[NDArray[np.float64], Vector3]:
    """The quaternion and the angular momentum of the top with its axis at
    the angle ``tilt`` (rad) from the vertical, in the x-z plane, turning
    with the component ``spin`` omega₃ (rad/s) of the angular velocity along
    the axis and the rate ``precession`` (rad/s) of the axis about the
    vertical, with no nodding (theta' = 0).

    The angular velocity is precession z + (omega₃ - precession cos tilt) e₃.
    """
    q = np.array([np.cos(tilt / 2), 0.0, np.sin(tilt / 2), 0.0])
    rotation = rotation_matrix(q)
    axis = rotation[:, 2]
    omega = precession * VERTICAL + (spin - precession * np.cos(tilt)) * axis
    return q, rotation @ top.body_inertia() @ rotation.T @ omega


def _rates(top: Top, q: NDArray[np.float64], momentum: NDArray[np.float64]):
    """dq/dt and dL/dt at the orientation ``q`` and the momentum ``momentum``."""
    rotation = rotation_matrix(q)
    omega = top._angular_velocity(rotation, momentum)
    return 0.5 * _product(np.concatenate([[0.0], omega]), q), top._torque(rotation)


def simulate_top(
    top: Top, q: ArrayLike, momentum: ArrayLike, dt: float, n_steps: int
) -> TopMotion:
    """Take ``n_steps`` steps of the classical Runge-Kutta method of length
    ``dt`` (s) from the orientation ``q`` and the angular momentum
    ``momentum`` (kg m²/s).

    The four stages evaluate dq/dt = (0, omega) q / 2 and dL/dt = tau. The
    quaternion is scaled back to unit length after each step: the method
    keeps the length only to its own accuracy, and a quaternion that is not
    a unit is no rotation.
    """
    if dt <= 0 or n_steps < 0:
        raise ValueError("dt must be positive and n_steps not negative")
    qs = [np.asarray(q, dtype=np.float64) / np.linalg.norm(q)]
    ls = [np.asarray(momentum, dtype=np.float64)]
    half = 0.5 * dt
    for _ in range(n_steps):
        q0, l0 = qs[-1], ls[-1]
        k1q, k1l = _rates(top, q0, l0)
        k2q, k2l = _rates(top, q0 + half * k1q, l0 + half * k1l)
        k3q, k3l = _rates(top, q0 + half * k2q, l0 + half * k2l)
        k4q, k4l = _rates(top, q0 + dt * k3q, l0 + dt * k3l)
        q1 = q0 + dt / 6.0 * (k1q + 2 * k2q + 2 * k3q + k4q)
        qs.append(q1 / np.linalg.norm(q1))
        ls.append(l0 + dt / 6.0 * (k1l + 2 * k2l + 2 * k3l + k4l))
    return TopMotion(
        t=dt * np.arange(n_steps + 1), q=np.array(qs), momentum=np.array(ls)
    )


def top_energy(top: Top, motion: TopMotion) -> NDArray[np.float64]:
    """The kinetic energy omega · L / 2 plus the potential energy m g l cos
    theta, in J, at every instant."""
    kinetic = np.array(
        [
            0.5 * top.angular_velocity(q, momentum) @ momentum
            for q, momentum in zip(motion.q, motion.momentum, strict=True)
        ]
    )
    return kinetic + top.mass * top.g * top.length * motion.axes()[:, 2]


def axial_momentum(motion: TopMotion) -> NDArray[np.float64]:
    """The component L · e₃ = I₃ omega₃ of the angular momentum along the
    symmetry axis, in kg m²/s, at every instant."""
    return np.einsum("ij,ij->i", motion.momentum, motion.axes())


def precession_angle(motion: TopMotion) -> NDArray[np.float64]:
    """The azimuth phi of the axis about the vertical, in rad, unwrapped so
    that it grows without jumps as the axis goes round."""
    axes = motion.axes()
    return np.unwrap(np.arctan2(axes[:, 1], axes[:, 0]))


def mean_precession_rate(motion: TopMotion) -> float:
    """The mean rate of the azimuth, in rad/s: the slope of a straight line
    fitted to it, which averages over the nodding of the axis."""
    slope, _ = np.polyfit(motion.t, precession_angle(motion), 1)
    return float(slope)


def fast_top_rate(top: Top, spin: float) -> float:
    """The precession rate m g l / (I₃ omega₃) in rad/s of a fast top: the
    torque divided by the axial angular momentum, the limit of a large
    ``spin`` omega₃ (rad/s)."""
    return top.mass * top.g * top.length / (top.i3 * spin)


def steady_precession_rates(top: Top, tilt: float, spin: float) -> tuple[float, float]:
    """The two rates (slow, fast) in rad/s at which the top precesses at the
    constant ``tilt`` (rad) without nodding, for the axial component
    ``spin`` omega₃ (rad/s): the roots of

        I₁ cos theta phi'² - I₃ omega₃ phi' + m g l = 0,

    the equation of the tilt with theta'' = theta' = 0. For a fast top the
    slow root tends to m g l / (I₃ omega₃). Raises ``ValueError`` when the
    spin is too small for steady precession (no real root), and for a
    horizontal axis, where the equation is linear.
    """
    a = top.i1 * np.cos(tilt)
    b = top.i3 * spin
    c = top.mass * top.g * top.length
    if a == 0.0:
        raise ValueError("the axis is horizontal: one rate, c / b")
    discriminant = b * b - 4.0 * a * c
    if discriminant < 0:
        raise ValueError("the spin is too small for steady precession at this tilt")
    root = np.sqrt(discriminant)
    # The slow root as 2c / (b + root), which keeps its digits when 4 a c is
    # much smaller than b²; the fast root is c / (a slow).
    slow = 2.0 * c / (b + np.copysign(root, b))
    return float(slow), float(c / (a * slow))
