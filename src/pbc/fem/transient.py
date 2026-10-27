"""Time stepping of the finite-element heat equation by the theta method.

In space the elements turn c du/dt = div(k grad u) + f into the system of
ordinary differential equations

    C du/dt = F - A u,

with C the capacity (a mass matrix, J/K) and A the conduction and any
exchange with a fluid (W/K). The theta method evaluates the right-hand side
between the old and the new state,

    C (u_1 - u_0) / dt = F - A (theta u_1 + (1 - theta) u_0),

which is backward Euler for theta = 1 (first order, damps every mode) and
Crank-Nicolson for theta = 1/2 (second order, unconditionally stable but
lets the fastest modes ring). Both solve one sparse system per step; its
matrix C + theta dt A does not change, so it is factorised once.
"""

import numpy as np
from numpy.typing import NDArray
from scipy import sparse
from scipy.sparse.linalg import splu

Array = NDArray[np.float64]


def theta_march(
    capacity: sparse.csr_matrix,
    matrix: sparse.csr_matrix,
    vector: Array,
    initial: Array,
    dt: float,
    steps: int,
    theta: float = 1.0,
) -> Array:
    """``steps`` steps of the theta method from ``initial``: the states at
    every step, the initial one first (steps + 1 rows)."""
    if not 0.5 <= theta <= 1.0:
        raise ValueError("theta lies between 1/2 and 1")
    left = splu((capacity + theta * dt * matrix).tocsc())
    right = (capacity - (1.0 - theta) * dt * matrix).tocsr()
    states = np.empty((steps + 1, len(vector)))
    states[0] = initial
    for n in range(steps):
        states[n + 1] = left.solve(right @ states[n] + dt * vector)
    return states


def midpoints(states: Array, theta: float) -> Array:
    """The states the theta method evaluates the right-hand side at, one per
    step: theta u_(n+1) + (1 - theta) u_n."""
    return theta * states[1:] + (1.0 - theta) * states[:-1]
