"""The compact thermal model of a hypothetical package (pbc.thermodynamics.package):
its geometry and mass, the heat balances of the finite elements and the
finite differences, the shared stiffness of the two methods, the exact cosine
mode, steady and transient, and the hottest junction."""

from dataclasses import replace

import numpy as np
import pytest
from scipy.sparse.linalg import spsolve

from pbc.fem.transient import theta_march
from pbc.thermodynamics.conduction import Material
from pbc.thermodynamics.package import (
    CosineMode,
    Die,
    Package,
    Region,
    cross_section,
    fd_grid,
    fd_laplacian,
    fem_system,
    finite_differences,
    heat_to_coolant,
    junction_maximum,
    mesh_for,
    steady,
    stored_heat,
)
from pbc.verification.estimates import fitted_order

COPPER = Material(k=390.0, rho=8960.0, c=385.0)
ALUMINIUM = Material(k=167.0, rho=2700.0, c=896.0)


def plate(**changes) -> Package:
    """A 40 x 20 mm plate with two dies, one of them off the 2 mm grid."""
    base = Package(
        width=0.040,
        height=0.020,
        thickness=0.002,
        material=COPPER,
        dies=(
            Die("a", Region(0.008, 0.016, 0.006, 0.014), 60.0),
            Die("b", Region(0.0251, 0.0313, 0.0047, 0.0119), 20.0),
        ),
        die_contact=1e-5,
        plate_contact=2e-5,
        h=10000.0,
        coolant=30.0,
    )
    return replace(base, **changes)


def test_a_region_measures_its_area_and_its_overlap():
    r = Region(0.0, 2.0, 1.0, 4.0)
    assert r.area == pytest.approx(6.0)
    assert r.overlap(1.0, 3.0, 0.0, 2.0) == pytest.approx(1.0)
    assert r.overlap(5.0, 6.0, 0.0, 9.0) == 0.0
    x = np.array([0.0, 1.0, 2.0, 3.0])
    y = np.full(4, 2.0)
    np.testing.assert_array_equal(r.inside(x, y), [False, True, False, False])
    np.testing.assert_array_equal(r.covers(x, y), [True, True, True, False])


def test_the_package_adds_its_powers_and_its_resistances():
    p = plate()
    assert p.power == pytest.approx(80.0)
    half = 0.001 / 390.0  # half the thickness over k
    assert p.base_resistance == pytest.approx(half + 2e-5 + 1e-4)
    assert p.die_resistance(p.dies[0]) == pytest.approx(1e-5 + half)
    assert p.dies[0].flux == pytest.approx(60.0 / 64e-6)
    assert p.spreading_length() == pytest.approx(
        np.sqrt(390.0 * 0.002 * p.base_resistance)
    )


def test_an_insert_changes_the_resistances_of_the_dies_and_the_triangles_on_it():
    insert = Region(0.006, 0.018, 0.004, 0.016)  # under die a only
    p = plate(material=ALUMINIUM, insert=COPPER, inserts=(insert,))
    assert p.die_resistance(p.dies[0]) == pytest.approx(1e-5 + 0.001 / 390.0)
    assert p.die_resistance(p.dies[1]) == pytest.approx(1e-5 + 0.001 / 167.0)
    k = p.conductivity(np.array([0.010, 0.030]), np.array([0.010, 0.010]))
    np.testing.assert_array_equal(k, [390.0, 167.0])
    system = fem_system(p, mesh_for(p, 0.002))
    # The exchange matrix integrates 1 / R_base of each material.
    expected = 1.44e-4 / p.resistance_below(390.0) + (8e-4 - 1.44e-4) / (
        p.resistance_below(167.0)
    )
    assert system.exchange.sum() == pytest.approx(expected, rel=1e-12)


def test_the_mass_counts_the_inserts_at_their_own_density():
    p = plate(material=ALUMINIUM)
    assert p.mass == pytest.approx(2700.0 * 0.040 * 0.020 * 0.002)
    insert = Region(0.0, 0.010, 0.0, 0.010)
    q = replace(p, insert=COPPER, inserts=(insert,))
    extra = (8960.0 - 2700.0) * 1e-4 * 0.002
    assert q.mass == pytest.approx(p.mass + extra)


def test_the_mesh_spacing_must_fit_the_plate():
    assert len(mesh_for(plate(), 0.002).nodes) == 21 * 11
    with pytest.raises(ValueError, match="divide"):
        mesh_for(plate(), 0.003)


def test_the_finite_differences_take_one_material():
    with pytest.raises(ValueError, match="one material"):
        finite_differences(
            plate(insert=ALUMINIUM, inserts=(Region(0, 0.01, 0, 0.01),)), 0.002
        )


def test_the_inserts_set_the_conductivity_of_their_triangles():
    insert = Region(0.0, 0.010, 0.0, 0.010)
    p = plate(material=ALUMINIUM, insert=COPPER, inserts=(insert,))
    system = fem_system(p, mesh_for(p, 0.002))
    # The capacity of the plate is rho c t times the area of each material.
    expected = 0.002 * (8960.0 * 385.0 * 1e-4 + 2700.0 * 896.0 * (0.040 * 0.020 - 1e-4))
    assert system.capacity.sum() == pytest.approx(expected, rel=1e-12)


@pytest.mark.parametrize("spacing", [0.002, 0.001])
def test_the_steady_heat_balances_close_for_both_methods(spacing):
    """The dies' power enters the load exactly where their edges lie on mesh
    lines, and the control-volume source of the finite differences enters it
    exactly everywhere; in both models it all leaves into the coolant."""
    p = replace(plate(), dies=plate().dies[:1])
    system = fem_system(p, mesh_for(p, spacing))
    temperature = steady(system)
    assert system.load.sum() == pytest.approx(p.power, rel=1e-12)
    assert heat_to_coolant(system, temperature) == pytest.approx(p.power, rel=1e-10)
    off_grid = plate()
    model = finite_differences(off_grid, spacing)
    assert model.source @ model.grid.areas == pytest.approx(off_grid.power, rel=1e-12)
    assert model.heat_to_coolant(model.steady()) == pytest.approx(
        off_grid.power, rel=1e-10
    )


def test_the_insulated_laplacian_conserves_heat_and_annihilates_constants():
    p = plate()
    grid = fd_grid(p, 0.002)
    laplacian = fd_laplacian(p, 0.002)
    assert grid.areas.sum() == pytest.approx(0.040 * 0.020)
    np.testing.assert_allclose(laplacian @ np.ones(len(grid.x)), 0.0, atol=1e-6)
    # The control-volume areas weigh the rows so that no heat is created.
    np.testing.assert_allclose(grid.areas @ laplacian, 0.0, atol=1e-12)


def test_the_element_stiffness_is_the_five_point_grid_weighted_by_the_areas():
    """On the structured mesh the P1 stiffness equals -k t A L, with A the
    control-volume areas and L the insulated five-point Laplacian: the two
    methods differ only in how they spread the source, the capacity, and the
    exchange with the coolant over the nodes."""
    p = plate()
    system = fem_system(p, mesh_for(p, 0.002))
    grid = fd_grid(p, 0.002)
    laplacian = fd_laplacian(p, 0.002).toarray()
    kt = p.material.k * p.thickness
    np.testing.assert_allclose(
        system.conduction.toarray(), -kt * grid.areas[:, None] * laplacian, atol=1e-9
    )


def test_the_cosine_mode_is_exact_for_its_load():
    p = plate()
    mode = CosineMode(p, uniform=1e5, amplitude=2e5)
    g0, g1 = mode.conductances()
    assert g0 == pytest.approx(1.0 / p.base_resistance)
    # At a corner the mode's shape is one: T = T_c + q0 / g0 + q1 / g1.
    assert mode.temperature(0.0, 0.0) == pytest.approx(30.0 + 1e5 / g0 + 2e5 / g1)
    assert mode.temperature(0.0, 0.0, 0.0) == pytest.approx(30.0)
    # It solves the steady equation: k t laplacian(T) + q = (T - T_c) / R.
    x, y, d = 0.013, 0.007, 1e-5
    t = mode.temperature
    laplacian = (
        t(x + d, y) + t(x - d, y) + t(x, y + d) + t(x, y - d) - 4 * t(x, y)
    ) / d**2
    lhs = p.material.k * p.thickness * laplacian + mode.flux(x, y)
    assert lhs == pytest.approx((t(x, y) - 30.0) / p.base_resistance, rel=1e-5)


def test_both_methods_converge_to_the_cosine_mode_at_order_two():
    p = plate()
    mode = CosineMode(p, uniform=1e5, amplitude=2e5)
    spacings, fem, fd = [0.004, 0.002, 0.001], [], []
    for spacing in spacings:
        system = fem_system(p, mesh_for(p, spacing), flux=mode.flux)
        x, y = system.mesh.nodes.T
        exact = mode.temperature(x, y)
        model = finite_differences(p, spacing, source=mode.flux(x, y))
        w = model.grid.areas / model.grid.areas.sum()
        fem.append(np.sqrt(w @ (steady(system) - exact) ** 2))
        fd.append(np.sqrt(w @ (model.steady() - exact) ** 2))
    assert fitted_order(spacings, fem) == pytest.approx(2.0, abs=0.1)
    assert fitted_order(spacings, fd) == pytest.approx(2.0, abs=0.1)


def test_the_transient_converges_to_the_exact_cosine_mode_and_keeps_its_energy():
    """Crank-Nicolson on the elements, the spacing and the step halved
    together: the rms error at a fixed time falls at order two, and every
    step stores and removes exactly the heat the load generates."""
    p = plate()
    mode = CosineMode(p, uniform=1e5, amplitude=2e5)
    span, errors = 0.2, []
    for spacing, steps in ((0.002, 25), (0.001, 50), (0.0005, 100)):
        system = fem_system(p, mesh_for(p, spacing), flux=mode.flux)
        x, y = system.mesh.nodes.T
        dt = span / steps
        initial = np.full(len(x), p.coolant)
        states = theta_march(
            system.capacity, system.matrix, system.vector, initial, dt, steps, 0.5
        )
        weights = fd_grid(p, spacing).areas / (p.width * p.height)
        error = states[-1] - mode.temperature(x, y, span)
        errors.append(np.sqrt(weights @ error**2))
        stored = np.diff(stored_heat(system, states))
        removed = heat_to_coolant(system, 0.5 * (states[1:] + states[:-1])) * dt
        generated = system.load.sum() * dt
        np.testing.assert_allclose(stored + removed, generated, rtol=1e-10)
    assert fitted_order([4.0, 2.0, 1.0], errors) == pytest.approx(2.0, abs=0.1)


def test_the_explicit_step_keeps_the_energy_of_the_grid():
    p = plate()
    model = finite_differences(p, 0.002)
    dt = 1e-3
    states = [np.full(len(model.source), p.coolant)]
    for _ in range(20):
        states.append(model.step(dt)(states[-1]))
    states = np.array(states)
    stored = np.diff(model.stored_heat(states))
    removed = model.heat_to_coolant(states[:-1]) * dt
    np.testing.assert_allclose(stored + removed, p.power * dt, rtol=1e-10)


def test_the_steady_finite_differences_solve_their_equations():
    p = plate()
    model = finite_differences(p, 0.002)
    np.testing.assert_allclose(model.rate(model.steady()), 0.0, atol=1e-6)
    # And the same matrix, assembled by hand, gives the same solution.
    n = len(model.source)
    matrix = (
        np.eye(n) / p.base_resistance
        - p.material.k * p.thickness * fd_laplacian(p, 0.002).toarray()
    )
    expected = np.linalg.solve(matrix, model.source + p.coolant / p.base_resistance)
    np.testing.assert_allclose(model.steady(), expected, rtol=1e-12)


def test_the_hottest_junction_adds_the_die_contact_to_the_plate():
    p = plate()
    x = np.array([0.010, 0.020, 0.030])
    y = np.array([0.010, 0.010, 0.010])
    temperature = np.array([50.0, 80.0, 60.0])
    # The middle node lies under no die; die a covers the first, die b the third.
    r = 1e-5 + 0.001 / 390.0
    expected = max(50.0 + p.dies[0].flux * r, 60.0 + p.dies[1].flux * r)
    assert junction_maximum(p, x, y, temperature) == pytest.approx(expected)
    many = junction_maximum(p, x, y, np.array([temperature, temperature + 1.0]))
    np.testing.assert_allclose(many, [expected, expected + 1.0])


def test_the_steady_plate_is_hottest_under_the_strongest_die():
    p = replace(plate(), dies=plate().dies[:1])
    system = fem_system(p, mesh_for(p, 0.001))
    temperature = steady(system)
    hottest = system.mesh.nodes[np.argmax(temperature)]
    assert p.dies[0].region.covers(*hottest)
    # Hotter than the even spread of the power, cooler than no spreading.
    even = p.coolant + p.power / (p.width * p.height) * p.base_resistance
    straight = p.coolant + p.dies[0].flux * p.base_resistance
    assert even < temperature.max() < straight
    direct = spsolve(system.matrix.tocsc(), system.vector)
    np.testing.assert_allclose(temperature, direct)


def test_a_uniform_flux_crosses_the_cross_section_in_one_dimension():
    """With the same flux over the whole top, nothing varies along x: the
    temperature falls linearly through the plate, by q t / k, above the
    coolant's q (R_lid-plate + 1 / h); linear elements find it at round-off,
    and the plate model's mid-plane temperature lies halfway."""
    p = plate()
    q = 3e5
    mesh, temperature = cross_section(p, lambda x, y: np.full_like(x, q), 20, 4)
    z = mesh.nodes[:, 1]
    bottom = p.coolant + q * (p.plate_contact + 1.0 / p.h)
    exact = bottom + q * z / p.material.k
    np.testing.assert_allclose(temperature, exact, rtol=1e-12)
    uniform = replace(
        p, dies=(Die("all", Region(0.0, p.width, 0.0, p.height), q * 8e-4),)
    )
    system = fem_system(uniform, mesh_for(uniform, 0.004))
    np.testing.assert_allclose(steady(system), bottom + q * 0.001 / 390.0, rtol=1e-12)
