"""A qubit coupled to its environment: the density matrix, the Lindblad
master equation, and the integrators that advance it.

The density matrix rho is Hermitian, has trace one, and has no negative
eigenvalue; a pure state is |psi><psi|. The Lindblad equation, with hbar = 1,

    d rho / dt = -i [H, rho] + sum_k (L_k rho L_k^+ - {L_k^+ L_k, rho} / 2),

is linear in rho, so on the vector of its four entries (row by row) it is a
4 x 4 matrix G, the generator. Every integrator of this module is then a
matrix M that advances rho by one step dt: explicit Euler 1 + dt G, the
classical fourth-order Runge-Kutta method the Taylor polynomial of
exp(dt G) to fourth order, and the exponential integrator exp(dt G) itself,
the exact step of an equation with a constant generator. Each keeps the
trace, because the trace of G rho is zero for every rho. Whether a step keeps
rho positive for every input, even as part of an entangled pair, is decided
by its Choi matrix: the step is completely positive exactly when that matrix
has no negative eigenvalue.

The qubit has the basis (e, g), excited and ground, with
H = (Delta / 2) sigma_z, Delta the detuning in the frame of the drive, the
decay L = sqrt(gamma) sigma_-, and the dephasing L = sqrt(gamma_phi / 2)
sigma_z. Its closed-form solution is

    rho_ee(t) = rho_ee(0) exp(-gamma t),
    rho_eg(t) = rho_eg(0) exp(-i Delta t - t / T2),  1 / T2 = gamma / 2 + gamma_phi.
"""

from collections.abc import Sequence
from math import factorial

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.linalg import expm

from pbc.quantum.spin import SIGMA_Z

Matrix = NDArray[np.complex128]
Array = NDArray[np.float64]

LOWERING = np.array([[0, 0], [1, 0]], dtype=complex)  # sigma_-, |g><e|


def lindblad(rho: ArrayLike, hamiltonian: ArrayLike, jumps: Sequence[ArrayLike]):
    """d rho / dt of the Lindblad equation, written out with matrix
    products: the reference for ``generator``."""
    rho = np.asarray(rho, dtype=complex)
    h = np.asarray(hamiltonian, dtype=complex)
    change = -1j * (h @ rho - rho @ h)
    for jump in jumps:
        c = np.asarray(jump, dtype=complex)
        cc = c.conj().T @ c
        change += c @ rho @ c.conj().T - 0.5 * (cc @ rho + rho @ cc)
    return change


def generator(hamiltonian: ArrayLike, jumps: Sequence[ArrayLike]) -> Matrix:
    """The Lindblad equation as a matrix on rho stacked row by row, with
    vec(A rho B) = (A x B^T) vec(rho)."""
    h = np.asarray(hamiltonian, dtype=complex)
    one = np.eye(h.shape[0])
    g = -1j * (np.kron(h, one) - np.kron(one, h.T))
    for jump in jumps:
        c = np.asarray(jump, dtype=complex)
        cc = c.conj().T @ c
        g += np.kron(c, c.conj()) - 0.5 * (np.kron(cc, one) + np.kron(one, cc.T))
    return g


def euler_step(g: ArrayLike, dt: float) -> Matrix:
    """The step of explicit Euler, 1 + dt G."""
    g = np.asarray(g, dtype=complex)
    return np.eye(g.shape[0]) + dt * g


def rk4_step(g: ArrayLike, dt: float) -> Matrix:
    """The step of the classical fourth-order Runge-Kutta method on a linear
    equation, sum over k from 0 to 4 of (dt G)^k / k!."""
    g = np.asarray(g, dtype=complex)
    step, term = np.eye(g.shape[0], dtype=complex), np.eye(g.shape[0], dtype=complex)
    for k in range(1, 5):
        term = term @ (dt * g)
        step = step + term / factorial(k)
    return step


def exponential_step(g: ArrayLike, dt: float) -> Matrix:
    """The step of the exponential integrator, exp(dt G)."""
    return expm(dt * np.asarray(g, dtype=complex))


def evolve(rho: ArrayLike, step: ArrayLike, count: int) -> Matrix:
    """rho after 0, 1, ..., ``count`` steps of the matrix ``step``, as an
    array of shape (count + 1, n, n)."""
    rho = np.asarray(rho, dtype=complex)
    n = rho.shape[0]
    states = np.empty((count + 1, n, n), dtype=complex)
    vector = rho.reshape(-1)
    states[0] = rho
    for i in range(1, count + 1):
        vector = step @ vector
        states[i] = vector.reshape(n, n)
    return states


def choi(step: ArrayLike) -> Matrix:
    """The Choi matrix sum_kl |k><l| x M(|k><l|) of the step M, Hermitian
    for a step that keeps rho Hermitian."""
    m = np.asarray(step, dtype=complex)
    n = round(np.sqrt(m.shape[0]))
    # M[(i, j), (k, l)] is entry (i, j) of M(|k><l|); the Choi matrix holds it
    # at the row (k, i) and the column (l, j).
    return m.reshape(n, n, n, n).transpose(2, 0, 3, 1).reshape(n * n, n * n)


def smallest_eigenvalue(matrix: ArrayLike) -> float:
    """The smallest eigenvalue of the Hermitian part of a matrix, or of each
    of a stack of matrices."""
    m = np.asarray(matrix, dtype=complex)
    hermitian = (m + np.swapaxes(m, -1, -2).conj()) / 2
    return np.linalg.eigvalsh(hermitian).min(axis=-1)


def trace(rho: ArrayLike) -> NDArray:
    """The trace of rho, or of each of a stack."""
    return np.trace(np.asarray(rho), axis1=-2, axis2=-1)


def purity(rho: ArrayLike) -> Array:
    """tr(rho^2): one for a pure state, 1 / n for the fully mixed state."""
    rho = np.asarray(rho, dtype=complex)
    return np.real(np.einsum("...ij,...ji->...", rho, rho))


def expectation(rho: ArrayLike, operator: ArrayLike) -> Array:
    """tr(rho A), the mean of the observable A, for one rho or a stack."""
    return np.real(np.einsum("...ij,ji->...", np.asarray(rho), np.asarray(operator)))


def partial_trace(rho: ArrayLike, keep: int) -> Matrix:
    """The state of one qubit of a pair, A (``keep`` = 0) or B (1): the
    trace of the pair's density matrix over the other."""
    r = np.asarray(rho, dtype=complex).reshape(2, 2, 2, 2)
    if keep == 0:
        return np.einsum("ijkj->ik", r)
    if keep == 1:
        return np.einsum("ijil->jl", r)
    raise ValueError(f"keep is 0 or 1, not {keep!r}")


def qubit(detuning: float, decay: float, dephasing: float) -> Matrix:
    """The generator of the qubit with H = (Delta / 2) sigma_z, the decay
    sqrt(gamma) sigma_-, and the dephasing sqrt(gamma_phi / 2) sigma_z."""
    hamiltonian, jumps = qubit_terms(detuning, decay, dephasing)
    return generator(hamiltonian, jumps)


def qubit_terms(
    detuning: float, decay: float, dephasing: float
) -> tuple[Matrix, list[Matrix]]:
    """The Hamiltonian and the jump operators of ``qubit``."""
    return (
        0.5 * detuning * SIGMA_Z,
        [np.sqrt(decay) * LOWERING, np.sqrt(dephasing / 2) * SIGMA_Z],
    )


def coherence_time(decay: float, dephasing: float) -> float:
    """T2 = 1 / (gamma / 2 + gamma_phi)."""
    return 1 / (decay / 2 + dephasing)


def exact_qubit(
    rho: ArrayLike, times: ArrayLike, detuning: float, decay: float, dephasing: float
) -> Matrix:
    """The closed-form rho(t) of the qubit at each of ``times``."""
    rho = np.asarray(rho, dtype=complex)
    t = np.asarray(times, dtype=float)
    excited = rho[0, 0] * np.exp(-decay * t)
    coherence = rho[0, 1] * np.exp(
        (-1j * detuning - 1 / coherence_time(decay, dephasing)) * t
    )
    states = np.empty((t.size, 2, 2), dtype=complex)
    states[:, 0, 0] = excited
    states[:, 1, 1] = 1 - excited
    states[:, 0, 1] = coherence
    states[:, 1, 0] = coherence.conj()
    return states


def ramsey(times: ArrayLike, detuning: float, t2: float) -> Array:
    """The probability of +1 along x of a qubit started along +x,
    (1 + exp(-t / T2) cos(Delta t)) / 2."""
    t = np.asarray(times, dtype=float)
    return (1 + np.exp(-t / t2) * np.cos(detuning * t)) / 2


def plus_x() -> Matrix:
    """The pure state along +x, (|e> + |g>) / sqrt(2), as a density matrix."""
    return np.full((2, 2), 0.5, dtype=complex)


def random_phase_coherence(
    times: ArrayLike, dephasing: float, count: int, rng: np.random.Generator
) -> tuple[NDArray[np.complex128], Array]:
    """The mean of exp(-i phi(t)) over ``count`` qubits whose relative phase
    phi takes independent random kicks, a random walk with the variance
    2 gamma_phi t, and the standard error of its real part. Each qubit stays
    pure; only the average over the kicks, which nobody records, is mixed."""
    t = np.asarray(times, dtype=float)
    steps = np.diff(t, prepend=0.0)
    kicks = rng.standard_normal((count, t.size)) * np.sqrt(2 * dephasing * steps)
    phases = np.exp(-1j * np.cumsum(kicks, axis=1))
    return phases.mean(axis=0), phases.real.std(axis=0, ddof=1) / np.sqrt(count)
