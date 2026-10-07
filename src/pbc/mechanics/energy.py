"""The energy of a simulated particle, and its drift as the diagnostic of a
simulation.

A force that depends on the position alone and does no net work around any
closed path is conservative: it is minus the gradient of a potential energy
U(x), and the mechanical energy, kinetic plus potential, is constant along
the true motion. A simulation has no such law; what it does to the energy
depends on the method and the step, and the drift of the energy over a run
is the one number that says how far the computed motion has left the
physics. The functions here evaluate the energies of a trajectory and that
drift; each lesson supplies the potential of its force.

Quantities are in SI units as in ``pbc.mechanics.dynamics``; energies are
in joules.
"""

from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray

from pbc.mechanics.dynamics import Trajectory, Vector

# A potential energy: U(x) is the potential energy in J of the particle at
# the position x (m). The force it gives is minus its gradient.
type Potential = Callable[[Vector], float]


def kinetic_energy(trajectory: Trajectory, mass: float) -> NDArray[np.float64]:
    """The kinetic energy m |v|² / 2 in J at every instant of ``trajectory``,
    for a particle of ``mass`` (kg)."""
    if mass <= 0:
        raise ValueError(f"mass must be positive, got {mass}")
    return 0.5 * mass * np.sum(trajectory.v**2, axis=1)


def potential_energy(
    trajectory: Trajectory, potential: Potential
) -> NDArray[np.float64]:
    """The potential energy U(x) in J at every instant of ``trajectory``."""
    return np.array([potential(x) for x in trajectory.x], dtype=np.float64)


def mechanical_energy(
    trajectory: Trajectory, mass: float, potential: Potential
) -> NDArray[np.float64]:
    """The mechanical energy, kinetic plus potential, in J at every instant
    of ``trajectory``: the quantity the true motion keeps constant."""
    return kinetic_energy(trajectory, mass) + potential_energy(trajectory, potential)


def energy_drift(energies: NDArray[np.float64]) -> float:
    """The largest relative deviation of ``energies`` from the first one,
    max |E - E_0| / |E_0|: how far a simulation has let the energy go.

    The initial energy must not be zero; a bound orbit has a negative one,
    and the deviation is measured against its size.
    """
    initial = energies[0]
    if initial == 0:
        raise ValueError("the initial energy is zero; there is nothing to compare with")
    return float(np.max(np.abs(energies - initial)) / abs(initial))
