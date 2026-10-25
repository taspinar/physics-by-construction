"""A small triangular finite-element solver for steady scalar problems.

Meshes of triangles (``pbc.fem.mesh``) and piecewise-linear elements
(``pbc.fem.assembly``) for -div(k grad u) = f with fixed values and
convective (Robin) boundaries, assembled into a sparse system that SciPy
solves. It depends on NumPy and SciPy only; Gmsh and FEniCSx are optional
reference tools outside the package, never imported by it. Shared by the
thermodynamics lessons (T10, T11) and, later, the materials course (MAT3).
"""
