"""A small triangular finite-element solver for scalar heat problems.

Meshes of triangles (``pbc.fem.mesh``) and piecewise-linear elements
(``pbc.fem.assembly``) for -div(k grad u) = f with fixed values and
convective (Robin) boundaries, assembled into a sparse system that SciPy
solves, and the theta method in time for c du/dt = div(k grad u) + f
(``pbc.fem.transient``). It depends on NumPy and SciPy only; Gmsh and
FEniCSx are optional reference tools outside the package, never imported by
it. Shared by the thermodynamics lessons (T10, T11) and, later, the
materials course (MAT3).
"""
