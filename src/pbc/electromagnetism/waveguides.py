"""Modes of a hollow rectangular waveguide with perfectly conducting walls.

Inside a guide of width a and height b along z, a field e^(j(omega t - beta
z)) solves Maxwell's equations only if its transverse shape solves the
Helmholtz equation of the cross-section,

    (d^2/dx^2 + d^2/dy^2) psi + k_c^2 psi = 0,

with psi = E_z and psi = 0 on the walls for a TM mode, psi = H_z and a zero
normal derivative on the walls for a TE mode. The eigenvalues k_c^2 of the
cross-section fix the cut-off frequencies f_c = c k_c / (2 pi); a mode with
f > f_c travels with beta = sqrt(k^2 - k_c^2), one with f < f_c decays as
e^(-alpha z) with alpha = sqrt(k_c^2 - k^2), where k = 2 pi f / c.

For a rectangle, k_c = pi sqrt((m/a)^2 + (n/b)^2) in closed form. This
module also solves the eigenproblem of the cross-section numerically, by
the five-point finite-difference Laplacian, to be compared with it.

Quantities are in SI units: lengths in m, frequencies in Hz, wavenumbers in
rad/m, attenuation in Np/m (neper per metre).
"""

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import sparse
from scipy.sparse.linalg import eigsh

from pbc.electromagnetism.fdtd import SPEED_OF_LIGHT

Array = NDArray[np.float64]

__all__ = [
    "attenuation",
    "cross_section_cutoffs",
    "cutoff_frequency",
    "group_velocity",
    "guide_wavenumber",
    "modes",
    "phase_velocity",
]

KINDS = ("TE", "TM")


def cutoff_frequency(m: int, n: int, a: float, b: float) -> float:
    """The cut-off frequency, Hz, of the TE_mn or TM_mn mode of an a by b
    guide: (c / 2) sqrt((m / a)^2 + (n / b)^2)."""
    return 0.5 * SPEED_OF_LIGHT * float(np.hypot(m / a, n / b))


def modes(a: float, b: float, count: int, kind: str) -> list[tuple[int, int, float]]:
    """The ``count`` modes of ``kind`` (TE or TM) of lowest cut-off, as
    (m, n, f_c). TE_mn needs m + n > 0, TM_mn needs m > 0 and n > 0; a mode
    of each pair of indices is listed once, ties by (m, n)."""
    if kind not in KINDS:
        raise ValueError(f"kind is one of {KINDS}")
    first = 0 if kind == "TE" else 1
    span = range(first, count + 2)
    found = [
        (m, n, cutoff_frequency(m, n, a, b)) for m in span for n in span if m + n > 0
    ]
    return sorted(found, key=lambda mode: (mode[2], mode[0], mode[1]))[:count]


def guide_wavenumber(f: ArrayLike, f_c: float) -> Array:
    """beta = (2 pi / c) sqrt(f^2 - f_c^2), rad/m, above the cut-off; nan
    below it."""
    f = np.asarray(f, dtype=float)
    with np.errstate(invalid="ignore"):
        return 2.0 * np.pi / SPEED_OF_LIGHT * np.sqrt(f**2 - f_c**2)


def attenuation(f: ArrayLike, f_c: float) -> Array:
    """alpha = (2 pi / c) sqrt(f_c^2 - f^2), Np/m, of the evanescent field
    below the cut-off; nan above it."""
    f = np.asarray(f, dtype=float)
    with np.errstate(invalid="ignore"):
        return 2.0 * np.pi / SPEED_OF_LIGHT * np.sqrt(f_c**2 - f**2)


def phase_velocity(f: ArrayLike, f_c: float) -> Array:
    """omega / beta = c / sqrt(1 - (f_c / f)^2), m/s: faster than light."""
    return SPEED_OF_LIGHT / np.sqrt(1.0 - (f_c / np.asarray(f, dtype=float)) ** 2)


def group_velocity(f: ArrayLike, f_c: float) -> Array:
    """d omega / d beta = c sqrt(1 - (f_c / f)^2), m/s: the speed of energy,
    slower than light; phase times group velocity is c^2."""
    return SPEED_OF_LIGHT * np.sqrt(1.0 - (f_c / np.asarray(f, dtype=float)) ** 2)


def _second_difference(cells: int, spacing: float, kind: str) -> sparse.csr_matrix:
    """The 1D second difference over ``cells`` cells of ``spacing`` m: on the
    interior nodes with zero ends (TM, Dirichlet), or on the cell centres
    with mirrored ends (TE, a zero derivative at the walls)."""
    size = cells - 1 if kind == "TM" else cells
    main = np.full(size, -2.0)
    if kind == "TE":
        main[[0, -1]] = -1.0  # the ghost value beyond a wall equals its neighbour
    off = np.ones(size - 1)
    return sparse.diags([off, main, off], [-1, 0, 1], format="csr") / spacing**2


def cross_section_cutoffs(
    a: float, b: float, cells_a: int, cells_b: int, kind: str, count: int
) -> Array:
    """The ``count`` lowest cut-off frequencies, Hz, of the TE or TM modes of
    the a by b cross-section, from the eigenvalues k_c^2 of the five-point
    Laplacian on ``cells_a`` by ``cells_b`` cells, solved as a sparse
    eigenproblem. The constant field of the TE problem, k_c = 0, is not a
    mode and is left out."""
    if kind not in KINDS:
        raise ValueError(f"kind is one of {KINDS}")
    dx_a, dx_b = (
        _second_difference(cells_a, a / cells_a, kind),
        _second_difference(cells_b, b / cells_b, kind),
    )
    eye_a, eye_b = sparse.identity(dx_a.shape[0]), sparse.identity(dx_b.shape[0])
    laplacian = sparse.kron(dx_a, eye_b) + sparse.kron(eye_a, dx_b)
    extra = 1 if kind == "TE" else 0
    # Shift-invert about a small negative value finds the smallest
    # eigenvalues of -laplacian, also the zero of the TE problem.
    values = eigsh(
        -laplacian.tocsc(),
        k=count + extra,
        sigma=-1.0,
        which="LM",
        return_eigenvectors=False,
    )
    values = np.sort(values)[extra:]
    return SPEED_OF_LIGHT * np.sqrt(values) / (2.0 * np.pi)
