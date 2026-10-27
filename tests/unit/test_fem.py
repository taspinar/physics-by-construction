"""The triangular finite-element solver (pbc.fem): meshes and their quality,
the assembly against hand-computed elements, solutions that P1 elements
reproduce exactly, the orders of convergence, the boundary fluxes, a
conductivity per triangle, the mass matrix, the theta method in time, and
the boundary of its imports."""

import ast
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import numpy as np
import pytest

from pbc.fem import assembly, mesh, transient
from pbc.verification.estimates import fitted_order

ROOT = Path(__file__).resolve().parents[2]
FEM = ROOT / "src" / "pbc" / "fem"
# The import name of a distribution where it differs from the distribution's.
IMPORT_NAMES = {"pyyaml": "yaml"}
OPTIONAL_TOOLS = {
    "gmsh",
    "dolfinx",
    "ufl",
    "basix",
    "ffcx",
    "fenics",
    "meshio",
    "pygmsh",
}


def one_triangle() -> mesh.Mesh:
    return mesh.Mesh(
        np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]]), np.array([[0, 1, 2]])
    )


# --- meshes ----------------------------------------------------------------------


def test_the_rectangle_is_covered_by_counter_clockwise_triangles():
    m = mesh.rectangle(2.0, 1.0, 4, 3)
    assert m.nodes.shape == (20, 2)
    assert m.triangles.shape == (24, 3)
    a = mesh.areas(m)
    assert np.all(a > 0)
    assert a.sum() == pytest.approx(2.0)
    assert sorted(m.boundary) == ["bottom", "left", "right", "top"]
    # The named boundary groups are exactly the edges of one triangle.
    named = np.concatenate(list(m.boundary.values()))
    assert sorted(map(tuple, named)) == sorted(
        map(tuple, mesh.boundary_edges(m.triangles))
    )


def test_the_rectangle_triangles_are_right_isosceles():
    m = mesh.rectangle(1.0, 1.0, 5, 5)
    np.testing.assert_allclose(
        np.sort(mesh.angles(m), axis=1), [[45.0, 45.0, 90.0]] * 50
    )
    assert mesh.size(m) == pytest.approx(np.sqrt(2) / 5)
    np.testing.assert_allclose(mesh.radius_ratio(m), 2 * (np.sqrt(2) - 1))


def test_the_radius_ratio_is_one_for_an_equilateral_triangle():
    m = mesh.Mesh(
        np.array([[0.0, 0.0], [1.0, 0.0], [0.5, np.sqrt(3) / 2]]), np.array([[0, 1, 2]])
    )
    np.testing.assert_allclose(mesh.radius_ratio(m), 1.0)
    np.testing.assert_allclose(mesh.angles(m), 60.0)


@pytest.mark.parametrize("graded", [False, True])
@pytest.mark.parametrize("layers", [3, 8, 20])
def test_the_annulus_covers_the_polygon_ring_with_good_triangles(layers, graded):
    m = mesh.annulus(0.02, 0.05, layers, graded)
    assert np.all(mesh.areas(m) > 0)
    # The triangles fill exactly the area between the two boundary polygons.
    polygon = 0.0
    for name in ("outer", "inner"):
        a, b = m.nodes[m.boundary[name][:, 0]], m.nodes[m.boundary[name][:, 1]]
        polygon += 0.5 * np.sum(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0])
    assert mesh.areas(m).sum() == pytest.approx(polygon, rel=1e-12)
    # Every boundary node lies on one of the two circles.
    radius = np.hypot(*m.nodes.T)
    np.testing.assert_allclose(radius[m.boundary_nodes("inner")], 0.02)
    np.testing.assert_allclose(radius[m.boundary_nodes("outer")], 0.05)
    assert mesh.angles(m).min() > 30.0


def test_the_graded_annulus_is_fine_at_a_thin_inner_ring():
    even = mesh.annulus(0.001, 0.08, 24)
    graded = mesh.annulus(0.001, 0.08, 24, graded=True)
    inner = graded.boundary["inner"]
    side = np.linalg.norm(graded.nodes[inner[:, 1]] - graded.nodes[inner[:, 0]], axis=1)
    assert side.max() < 0.001
    assert mesh.angles(graded).min() > 30.0
    assert len(graded.boundary["inner"]) > len(even.boundary["inner"])


# --- assembly --------------------------------------------------------------------


def test_the_stiffness_of_one_right_triangle_is_the_textbook_element():
    k = assembly.stiffness(one_triangle(), conductivity=3.0).toarray()
    expected = 0.5 * np.array([[2.0, -1.0, -1.0], [-1.0, 1.0, 0.0], [-1.0, 0.0, 1.0]])
    np.testing.assert_allclose(k, 3.0 * expected)


def test_the_stiffness_is_symmetric_and_annihilates_constants():
    m = mesh.annulus(1.0, 2.0, 4)
    k = assembly.stiffness(m, 2.5)
    assert abs(k - k.T).max() < 1e-12
    np.testing.assert_allclose(k @ np.ones(len(m.nodes)), 0.0, atol=1e-12)


def test_the_load_of_a_constant_source_gives_a_third_of_each_area_to_each_node():
    m = mesh.rectangle(1.0, 1.0, 3, 3)
    f = assembly.load(m, lambda x, y: np.full_like(x, 6.0))
    assert f.sum() == pytest.approx(6.0)
    expected = np.zeros(len(m.nodes))
    np.add.at(expected, m.triangles, (2.0 * mesh.areas(m))[:, None] * np.ones(3))
    np.testing.assert_allclose(f, expected)


def test_the_convective_edge_matrix_and_vector():
    nodes = np.array([[0.0, 0.0], [3.0, 4.0]])
    m = mesh.Mesh(nodes, np.zeros((0, 3), dtype=np.int64))
    matrix, vector = assembly.convection(
        m, np.array([[0, 1]]), 2.0, lambda x, y: 10.0 + x
    )
    np.testing.assert_allclose(
        matrix.toarray(), 2.0 * 5.0 / 6.0 * np.array([[2, 1], [1, 2]])
    )
    # h times the integral of g phi_i, exact for a linear g: L h (2 g_i + g_j) / 6.
    np.testing.assert_allclose(
        vector, 2.0 * 5.0 * np.array([2 * 10 + 13, 10 + 2 * 13]) / 6
    )


@pytest.mark.parametrize("graded", [False, True])
def test_a_linear_temperature_between_fixed_walls_is_reproduced_exactly(graded):
    """P1 elements contain every linear function, so a linear solution of the
    Laplace equation is found at round-off on any mesh."""
    m = mesh.annulus(1.0, 3.0, 5, graded)
    exact = 2.0 + 0.3 * m.nodes[:, 0] - 0.7 * m.nodes[:, 1]
    fixed = m.boundary_nodes("inner", "outer")
    u = assembly.solve(
        assembly.stiffness(m, 4.0), np.zeros(len(exact)), fixed, exact[fixed]
    )
    np.testing.assert_allclose(u, exact, atol=1e-12)


def test_a_linear_temperature_with_a_convective_side_is_reproduced_exactly():
    """On the top side, -k du/dy = h (u - g) holds for the linear u when the
    fluid is at g = u + (k / h) du/dy; the elements then find u at round-off."""
    m = mesh.rectangle(2.0, 1.0, 6, 5)
    k, h = 4.0, 5.0

    def exact(x, y):
        return 2.0 + 0.3 * x - 0.7 * y

    air_matrix, air_vector = assembly.convection(
        m, m.boundary["top"], h, lambda x, y: exact(x, y) + k * (-0.7) / h
    )
    fixed = m.boundary_nodes("bottom", "left", "right")
    u = assembly.solve(
        assembly.stiffness(m, k) + air_matrix,
        air_vector,
        fixed,
        exact(*m.nodes[fixed].T),
    )
    np.testing.assert_allclose(u, exact(*m.nodes.T), atol=1e-12)


def test_the_gradients_of_a_linear_field_are_exact():
    m = mesh.annulus(1.0, 2.0, 3)
    u = 4.0 * m.nodes[:, 0] + 2.0 * m.nodes[:, 1]
    grad = np.einsum("ti,tia->ta", u[m.triangles], assembly.gradients(m))
    np.testing.assert_allclose(grad, np.tile([4.0, 2.0], (len(m.triangles), 1)))
    l2, h1 = assembly.errors(
        m,
        u,
        lambda x, y: 4 * x + 2 * y,
        lambda x, y: np.stack([4 + 0 * x, 2 + 0 * y], -1),
    )
    assert l2 < 1e-12 and h1 < 1e-12


def test_the_orders_of_convergence_for_a_smooth_solution():
    def exact(x, y):
        return np.sin(np.pi * x) * np.sin(np.pi * y)

    def gradient(x, y):
        return np.pi * np.stack(
            [
                np.cos(np.pi * x) * np.sin(np.pi * y),
                np.sin(np.pi * x) * np.cos(np.pi * y),
            ],
            -1,
        )

    sizes, l2, h1 = [], [], []
    for cells in (4, 8, 16, 32):
        m = mesh.rectangle(1.0, 1.0, cells, cells)
        fixed = m.boundary_nodes("bottom", "right", "top", "left")
        u = assembly.solve(
            assembly.stiffness(m),
            assembly.load(m, lambda x, y: 2 * np.pi**2 * exact(x, y)),
            fixed,
            np.zeros(len(fixed)),
        )
        e = assembly.errors(m, u, exact, gradient)
        sizes.append(mesh.size(m))
        l2.append(e[0])
        h1.append(e[1])
    assert fitted_order(sizes, l2) == pytest.approx(2.0, abs=0.1)
    assert fitted_order(sizes, h1) == pytest.approx(1.0, abs=0.1)


def test_the_residual_flux_balances_a_source_exactly():
    """With a source and fixed edges, the heat flowing out through the fixed
    nodes (minus the residual) equals the heat generated, at round-off."""
    m = mesh.rectangle(1.0, 1.0, 12, 12)
    matrix = assembly.stiffness(m, 2.0)
    vector = assembly.load(m, lambda x, y: 5.0 + 3.0 * x * y)
    fixed = m.boundary_nodes("bottom", "right", "top", "left")
    u = assembly.solve(matrix, vector, fixed, np.zeros(len(fixed)))
    r = assembly.residual(matrix, vector, u)
    free = np.setdiff1d(np.arange(len(u)), fixed)
    np.testing.assert_allclose(r[free], 0.0, atol=1e-12)
    generated = 5.0 + 3.0 / 4.0  # the integral of the source over the square
    assert -r[fixed].sum() == pytest.approx(generated, rel=1e-12)


def test_the_gradient_outflow_of_a_linear_field():
    m = mesh.rectangle(2.0, 1.0, 4, 2)
    u = 3.0 * m.nodes[:, 0]  # q = -k grad u = (-3 k, 0)
    out = assembly.edge_outflow(m, m.boundary["right"], u, conductivity=2.0)
    np.testing.assert_allclose(out.sum(), -6.0 * 1.0)  # flows in through x = 2
    out = assembly.edge_outflow(m, m.boundary["left"], u, conductivity=2.0)
    np.testing.assert_allclose(out.sum(), 6.0)


# --- the import boundary ---------------------------------------------------------


def test_two_layers_in_series_are_reproduced_exactly():
    """With the conductivity jumping on a mesh line, the temperature is linear
    in each layer and the heat flux is continuous: q = dT / (L1/k1 + L2/k2).
    P1 elements with a conductivity per triangle find it at round-off."""
    m = mesh.rectangle(2.0, 1.0, 8, 3)
    x_centre = m.nodes[m.triangles].mean(axis=1)[:, 0]
    k = np.where(x_centre < 1.0, 1.0, 4.0)
    fixed = m.boundary_nodes("left", "right")
    u = assembly.solve(
        assembly.stiffness(m, k),
        np.zeros(len(m.nodes)),
        fixed,
        np.where(m.nodes[fixed, 0] < 1.0, 0.0, 1.0),
    )
    q = 1.0 / (1.0 / 1.0 + 1.0 / 4.0)
    x = m.nodes[:, 0]
    exact = np.where(x < 1.0, q * x / 1.0, q / 1.0 + q * (x - 1.0) / 4.0)
    np.testing.assert_allclose(u, exact, atol=1e-12)


def test_a_coefficient_is_a_constant_or_one_per_triangle():
    m = mesh.rectangle(1.0, 1.0, 2, 2)
    constant = assembly.stiffness(m, 3.0).toarray()
    repeated = assembly.stiffness(m, np.full(len(m.triangles), 3.0)).toarray()
    np.testing.assert_allclose(constant, repeated)
    with pytest.raises(ValueError, match="one value per triangle"):
        assembly.mass(m, np.ones(len(m.triangles) + 1))


def test_the_mass_matrix_integrates_products_of_linear_fields_exactly():
    """u^T M v is the integral of c u v for linear hats, so for u = x and
    v = y on the unit square with c = 3 it is 3/4; its entries sum to the
    integral of c, and it is symmetric and positive definite."""
    m = mesh.rectangle(1.0, 1.0, 5, 4)
    matrix = assembly.mass(m, 3.0)
    x, y = m.nodes.T
    assert x @ matrix @ y == pytest.approx(3.0 / 4.0, rel=1e-12)
    assert matrix.sum() == pytest.approx(3.0, rel=1e-12)
    dense = matrix.toarray()
    np.testing.assert_allclose(dense, dense.T)
    assert np.linalg.eigvalsh(dense).min() > 0.0


def test_the_mass_of_one_triangle_is_the_textbook_element():
    np.testing.assert_allclose(
        assembly.mass(one_triangle(), 12.0).toarray(),
        0.5 * np.array([[2, 1, 1], [1, 2, 1], [1, 1, 2]]),
    )


def uniform_relaxation(theta: float, dt: float, steps: int):
    """A plate exchanging heat with a fluid at zero over its whole face,
    heated uniformly: C du/dt = F - S u with C and S mass matrices. A uniform
    state stays uniform (the stiffness annihilates it), so every node follows
    the scalar equation c du/dt = q - u / R."""
    m = mesh.rectangle(1.0, 1.0, 3, 3)
    c, resistance, q = 2.0, 0.5, 4.0
    capacity = assembly.mass(m, c)
    matrix = assembly.stiffness(m, 7.0) + assembly.mass(m, 1.0 / resistance)
    vector = assembly.load(m, lambda x, y: q + 0.0 * x)
    initial = np.full(len(m.nodes), 1.0)
    states = transient.theta_march(capacity, matrix, vector, initial, dt, steps, theta)
    tau, final = c * resistance, q * resistance
    return states, tau, final


def test_backward_euler_and_crank_nicolson_have_their_amplification_factors():
    dt, steps = 0.3, 5
    for theta, factor in (
        (1.0, lambda z: 1.0 / (1.0 + z)),
        (0.5, lambda z: (1.0 - 0.5 * z) / (1.0 + 0.5 * z)),
    ):
        states, tau, final = uniform_relaxation(theta, dt, steps)
        expected = final + (1.0 - final) * factor(dt / tau) ** np.arange(steps + 1)
        np.testing.assert_allclose(states, expected[:, None] + 0 * states, rtol=1e-12)


def test_the_theta_methods_converge_at_orders_one_and_two():
    span = 1.0
    for theta, order in ((1.0, 1.0), (0.5, 2.0)):
        steps, errors = [], []
        for count in (8, 16, 32, 64):
            states, tau, final = uniform_relaxation(theta, span / count, count)
            exact = final + (1.0 - final) * np.exp(-span / tau)
            steps.append(span / count)
            errors.append(np.max(np.abs(states[-1] - exact)))
        assert fitted_order(steps, errors) == pytest.approx(order, abs=0.05)


def test_the_theta_method_is_only_defined_between_one_half_and_one():
    m = mesh.rectangle(1.0, 1.0, 1, 1)
    capacity = assembly.mass(m)
    with pytest.raises(ValueError, match="theta"):
        transient.theta_march(capacity, capacity, np.zeros(4), np.zeros(4), 0.1, 1, 0.3)


def test_the_midpoints_weigh_the_old_and_the_new_state():
    states = np.array([[0.0, 2.0], [4.0, 6.0], [8.0, 10.0]])
    np.testing.assert_allclose(
        transient.midpoints(states, 0.5), [[2.0, 4.0], [6.0, 8.0]]
    )
    np.testing.assert_allclose(transient.midpoints(states, 1.0), states[1:])


def runtime_import_names() -> set[str]:
    """The import names of the project's runtime dependencies, each of which
    uv.lock pins."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    locked = set(
        re.findall(r'^name = "([^"]+)"$', (ROOT / "uv.lock").read_text(), re.M)
    )
    names = set()
    for requirement in project["dependencies"]:
        distribution = re.match(r"[A-Za-z0-9_.-]+", requirement).group(0).lower()
        assert distribution in locked, f"{distribution} is not in uv.lock"
        names.add(IMPORT_NAMES.get(distribution, distribution))
    return names


@pytest.mark.parametrize("source", sorted(FEM.glob("*.py")), ids=lambda p: p.name)
def test_fem_imports_only_the_locked_environment(source):
    allowed = set(sys.stdlib_module_names) | runtime_import_names() | {"pbc"}
    for node in ast.walk(ast.parse(source.read_text())):
        if isinstance(node, ast.Import):
            roots = {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, f"{source.name} uses a relative import"
            roots = {node.module.split(".")[0]}
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "__import__", f"{source.name} imports dynamically"
            continue
        else:
            continue
        assert roots <= allowed, f"{source.name} imports {roots - allowed}"
        assert not roots & OPTIONAL_TOOLS


def test_fem_works_with_the_optional_tools_unavailable():
    """In a fresh interpreter in which any import of Gmsh or FEniCSx fails,
    pbc.fem imports and solves a small problem."""
    script = f"""
import sys
class Block:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in {sorted(OPTIONAL_TOOLS)!r}:
            raise ImportError(name)
sys.meta_path.insert(0, Block())
import numpy as np
from pbc.fem import assembly, mesh, transient
m = mesh.rectangle(1.0, 1.0, 4, 4)
fixed = m.boundary_nodes("left", "right")
k = assembly.stiffness(m)
u = assembly.solve(k, np.zeros(len(m.nodes)), fixed, m.nodes[fixed, 0])
assert np.allclose(u, m.nodes[:, 0])
print("ok")
"""
    run = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=False
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout.strip() == "ok"
