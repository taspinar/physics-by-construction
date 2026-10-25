"""Molecular dynamics of Lennard-Jones particles in a periodic square box.

Reduced units: lengths in sigma, energies in epsilon, masses in the mass of the
lightest particle, temperatures in epsilon / k_B, and times in
sigma sqrt(m / epsilon). The pair potential is Lennard-Jones,
u(r) = 4 (r^-12 - r^-6), cut off at ``CUTOFF`` and shifted so that both the
potential and the force go to zero there (the shifted-force potential): the
energy is then a smooth function of the positions, and the error of its
conservation is the integrator's.

Particles interact with the nearest image of every other particle (the minimum
image convention), which needs a box side of at least twice the cut-off. The
state is the positions, shape ``(N, 2)``, the velocities, shape ``(N, 2)``, and
the masses, shape ``(N,)``.
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

Array = NDArray[np.float64]

CUTOFF = 2.5
DIMENSION = 2


def lennard_jones(r: Array) -> Array:
    """The unshifted Lennard-Jones potential 4 (r^-12 - r^-6)."""
    inv6 = np.asarray(r, dtype=np.float64) ** -6.0
    return 4.0 * (inv6 * inv6 - inv6)


def lennard_jones_derivative(r: Array) -> Array:
    """du/dr of the unshifted potential, -24 (2 r^-13 - r^-7)."""
    r = np.asarray(r, dtype=np.float64)
    inv6 = r**-6.0
    return -24.0 * (2.0 * inv6 * inv6 - inv6) / r


def shifted_force(r: Array, cutoff: float = CUTOFF) -> Array:
    """The shifted-force potential u(r) - u(rc) - (r - rc) u'(rc) for r < rc,
    and zero beyond: it and its derivative vanish at the cut-off."""
    r = np.asarray(r, dtype=np.float64)
    inside = r < cutoff
    value = (
        lennard_jones(r)
        - lennard_jones(cutoff)
        - (r - cutoff) * lennard_jones_derivative(cutoff)
    )
    return np.where(inside, value, 0.0)


def minimum_image(positions: Array, box: float) -> Array:
    """The displacement r_i - r_j of every pair to the nearest image, shape
    ``(N, N, 2)``."""
    d = positions[:, None, :] - positions[None, :, :]
    return d - box * np.round(d / box)


def forces(
    positions: Array, box: float, cutoff: float = CUTOFF
) -> tuple[Array, float, float]:
    """The force on every particle, the potential energy, and the virial
    sum over pairs of r_ij . f_ij, for the shifted-force potential."""
    if box < 2.0 * cutoff:
        raise ValueError("the box side must be at least twice the cut-off")
    d = minimum_image(positions, box)
    r2 = np.einsum("ijk,ijk->ij", d, d)
    np.fill_diagonal(r2, np.inf)
    inside = r2 < cutoff * cutoff
    r = np.sqrt(np.where(inside, r2, 1.0))
    # -du/dr of the shifted-force potential, divided by r: f_ij = this * d_ij
    f_over_r = np.where(
        inside,
        -(lennard_jones_derivative(r) - lennard_jones_derivative(cutoff)) / r,
        0.0,
    )
    f = np.einsum("ij,ijk->ik", f_over_r, d)
    potential = 0.5 * float(np.sum(np.where(inside, shifted_force(r, cutoff), 0.0)))
    virial = 0.5 * float(np.sum(f_over_r * np.where(inside, r2, 0.0)))
    return f, potential, virial


def square_lattice(per_side: int, box: float) -> Array:
    """``per_side``^2 positions on a square lattice filling the box."""
    g = (np.arange(per_side) + 0.5) * box / per_side
    x, y = np.meshgrid(g, g)
    return np.column_stack([x.ravel(), y.ravel()])


def initial_velocities(
    masses: Array, temperatures: Array, rng: np.random.Generator
) -> Array:
    """Gaussian velocities of variance T_i / m_i per component, with the
    temperature ``temperatures[i]`` of each particle, and the total momentum
    then removed."""
    m = np.asarray(masses, dtype=np.float64)
    t = np.asarray(temperatures, dtype=np.float64)
    v = rng.normal(size=(m.size, DIMENSION)) * np.sqrt(t / m)[:, None]
    return v - (m[:, None] * v).sum(axis=0) / m.sum()


def kinetic_energy(velocities: Array, masses: Array) -> float:
    """The kinetic energy sum m v^2 / 2."""
    return 0.5 * float(np.sum(masses[:, None] * velocities**2))


def temperature(velocities: Array, masses: Array, selected: Array) -> Array:
    """The kinetic temperature of the ``selected`` particles, per component.

    With the total momentum fixed at zero, a particle of mass m_i in a system
    of total mass M has <m_i v_ix^2> = (1 - m_i / M) k_B T (the centre of mass
    takes the rest), so the temperature is sum m_i v_ix^2 over
    sum (1 - m_i / M). Without the factor, light and heavy particles would
    seem to differ in temperature by an amount of order 1 / N.
    """
    m = np.asarray(masses, dtype=np.float64)
    share = (1.0 - m / m.sum())[selected].sum()
    return (m[selected, None] * velocities[selected] ** 2).sum(axis=0) / share


@dataclass(frozen=True)
class Trajectory:
    """What a run records every ``every`` steps: the times, the potential and
    kinetic energies, the virial, and the temperature per component of each
    group of particles (shape ``(records, groups, 2)``); and the final state."""

    times: Array
    potential: Array
    kinetic: Array
    virial: Array
    temperatures: Array
    positions: Array
    velocities: Array

    @property
    def energy(self) -> Array:
        """The total energy at each record."""
        return self.potential + self.kinetic


def velocity_verlet(
    positions: Array,
    velocities: Array,
    masses: Array,
    box: float,
    dt: float,
    steps: int,
    every: int = 1,
    groups: tuple[Array, ...] = (),
) -> Trajectory:
    """``steps`` steps of velocity Verlet: half a kick, a drift, the new
    forces, half a kick. Records the start and every ``every`` steps; the
    temperatures are those of the ``groups`` (index arrays) of particles."""
    if steps < 1 or every < 1 or dt <= 0.0:
        raise ValueError("steps and every must be at least 1, and dt positive")
    x = np.array(positions, dtype=np.float64) % box
    v = np.array(velocities, dtype=np.float64)
    m = np.asarray(masses, dtype=np.float64)[:, None]
    f, u, w = forces(x, box)
    records: list[tuple[float, float, float, float, Array]] = []

    def record(t: float) -> None:
        temps = np.array([temperature(v, m[:, 0], g) for g in groups])
        records.append((t, u, kinetic_energy(v, m[:, 0]), w, temps))

    record(0.0)
    for k in range(1, steps + 1):
        v += 0.5 * dt * f / m
        x += dt * v
        x %= box
        f, u, w = forces(x, box)
        v += 0.5 * dt * f / m
        if k % every == 0:
            record(k * dt)
    times, potential, kinetic, virial, temps = zip(*records, strict=True)
    return Trajectory(
        np.array(times),
        np.array(potential),
        np.array(kinetic),
        np.array(virial),
        np.array(temps),
        x,
        v,
    )


def virial_pressure(
    n_particles: int, kinetic_temperature: float, virial: float, box: float
) -> float:
    """The pressure (N k_B T + W / 2) / A of the two-dimensional system, from
    the virial W = sum over pairs of r_ij . f_ij and the area A."""
    return (n_particles * kinetic_temperature + virial / DIMENSION) / box**2
