"""The vibrations of a chain, the bands of its electrons, elasticity, and
point defects (lessons MAT1 to MAT4): each result is compared with a
closed-form solution, a limiting case, or an independent computation, with
a stated tolerance."""

import numpy as np
import pytest
from scipy.linalg import expm
from scipy.special import gammaln

from pbc.fem.mesh import rectangle
from pbc.materials.bands import (
    allowed_wavenumbers as band_wavenumbers,
)
from pbc.materials.bands import (
    bloch_centre,
    chain_hamiltonian,
    closed_form_energies,
    counting,
    effective_mass,
    filled,
    gaussian_packet,
    one_band,
    propagate,
    ring_energies,
    ring_hamiltonian,
    translation,
    two_site_bands,
)
from pbc.materials.defects import (
    exact_vacancies,
    free_energy,
    free_energy_step,
    hop_rate,
    lattice_walks,
    vacancy_exchanges,
    vacancy_fraction,
)
from pbc.materials.elasticity import (
    bar_displacement,
    bar_load,
    bar_stiffness,
    bar_stress,
    clamped_supports,
    element_dofs,
    plane_stress,
    plate_stiffness,
    roller_supports,
    solve_bar,
    solve_plate,
    strain_matrices,
    traction_load,
    uniform_tension,
)
from pbc.materials.phonons import (
    allowed_wavenumbers,
    closed_form_frequencies,
    diatomic_dispersion,
    energy_density,
    force_constants,
    group_velocity,
    monatomic_dispersion,
    packet_start,
    phase_velocity,
    ring_frequencies,
    ring_masses,
    ring_modes,
    sound_speed,
    verlet_packet,
    zone_boundary,
)

# --- MAT1: phonons -------------------------------------------------------------


def test_the_force_constants_store_the_energy_of_every_spring():
    rng = np.random.default_rng(1)
    u = rng.normal(size=7)
    c = force_constants(7, 2.5)
    springs = 0.5 * 2.5 * np.sum((np.roll(u, -1) - u) ** 2)
    assert 0.5 * u @ c @ u == pytest.approx(springs, rel=1e-13)
    assert np.allclose(c, c.T)
    # A rigid translation stretches no spring.
    assert np.allclose(c @ np.ones(7), 0.0)


@pytest.mark.parametrize("masses", [[1.7], [3.0, 0.7], [0.4, 0.4]])
def test_the_ring_has_the_closed_form_frequencies(masses):
    ring = ring_frequencies(10, masses, 2.5)
    closed = closed_form_frequencies(10, masses, 2.5)
    assert ring.size == 10 * len(masses)
    assert np.allclose(ring**2, closed**2, atol=1e-12)
    assert ring[0] == pytest.approx(0.0, abs=1e-6)  # the rigid translation


def test_a_mode_of_the_ring_solves_the_equations_of_motion():
    # A standing wave of an allowed wavenumber, integrated in time by an
    # independent method (the matrix exponential of the first-order system),
    # returns to its start after one closed-form period.
    cells, spring, mass = 12, 1.3, 0.8
    k = allowed_wavenumbers(cells)[3]
    omega = float(monatomic_dispersion(k, mass, spring))
    u0 = np.cos(k * np.arange(cells))
    a = np.block(
        [
            [np.zeros((cells, cells)), np.eye(cells)],
            [-force_constants(cells, spring) / mass, np.zeros((cells, cells))],
        ]
    )
    state = expm(a * 2 * np.pi / omega) @ np.concatenate([u0, np.zeros(cells)])
    assert np.allclose(state[:cells], u0, atol=1e-10)


def test_the_diatomic_branches_fold_the_monatomic_one_for_equal_masses():
    k = np.linspace(0, np.pi, 50)
    acoustic, optical = diatomic_dispersion(k, 1.0, 1.0, 1.0)
    # Spacing a / 2: the monatomic wavenumbers k and k + 2 pi / a.
    assert np.allclose(acoustic, 2 * np.abs(np.sin(k / 4)))
    assert np.allclose(optical, 2 * np.abs(np.cos(k / 4)))


def test_the_branch_edges_and_the_sound_speeds_are_the_limits_of_the_closed_form():
    m1, m2, spring = 1.0, 3.0, 2.0
    acoustic, optical = diatomic_dispersion(np.array([0.0, np.pi]), m1, m2, spring)
    top, bottom, highest = zone_boundary(m1, m2, spring)
    assert acoustic[1] == pytest.approx(top) and optical[1] == pytest.approx(bottom)
    assert optical[0] == pytest.approx(highest) and acoustic[0] == 0.0
    # The slope at a small k, whose relative departure is of order k^2.
    h = 1e-3
    slope, _ = diatomic_dispersion(h, m1, m2, spring)
    assert slope / h == pytest.approx(sound_speed([m1, m2], spring), rel=1e-6)
    assert monatomic_dispersion(h, m1, spring) / h == pytest.approx(
        sound_speed([m1], spring), rel=1e-6
    )


def test_the_group_velocity_is_the_slope_of_the_dispersion():
    k = np.linspace(0.1, 3.0, 9)
    h = 1e-6
    slope = (
        monatomic_dispersion(k + h, 2.0, 3.0) - monatomic_dispersion(k - h, 2.0, 3.0)
    ) / (2 * h)
    assert np.allclose(group_velocity(k, 2.0, 3.0), slope, rtol=1e-7)
    assert np.all(phase_velocity(k, 2.0, 3.0) > group_velocity(k, 2.0, 3.0))


def test_the_modes_are_read_at_their_wavenumber():
    frequencies, k = ring_modes(16, [1.0, 2.0], 1.0)
    acoustic, optical = diatomic_dispersion(k, 1.0, 2.0, 1.0)
    on_branch = np.isclose(frequencies, acoustic) | np.isclose(frequencies, optical)
    assert np.all(on_branch)


def test_the_packet_moves_forward_at_the_group_velocity():
    mass, spring = 1.0, 1.0
    u, v = packet_start(512, 150.0, 15.0, np.pi / 2, mass, spring)
    # The energy per atom adds up to the energy of the ring.
    total = 0.5 * u @ force_constants(512, spring) @ u + 0.5 * mass * v @ v
    assert energy_density(u, v, mass, spring).sum() == pytest.approx(total, rel=1e-12)
    run = verlet_packet(u, v, mass, spring, 0.02, 5000, 500)
    speed = np.polyfit(run.t, run.centre, 1)[0]
    expected = float(group_velocity(np.pi / 2, mass, spring))
    assert speed == pytest.approx(expected, rel=2e-3)


def test_a_ring_needs_two_cells():
    with pytest.raises(ValueError):
        ring_masses(1, [1.0])


# --- MAT2: bands ---------------------------------------------------------------


@pytest.mark.parametrize("onsite", [[1.2], [0.3, -0.3]])
def test_the_ring_has_the_closed_form_bands(onsite):
    h = ring_hamiltonian(11, onsite, 0.7)
    assert np.allclose(h, h.T)
    assert np.allclose(
        ring_energies(11, onsite, 0.7),
        closed_form_energies(11, onsite, 0.7),
        atol=1e-12,
    )


def test_the_two_site_bands_without_a_gap_fold_the_one_band():
    k = np.linspace(-np.pi, np.pi, 41)
    lower, upper = two_site_bands(k, 0.0, 1.0)
    # Spacing a / 2: the one-band wavenumbers k / 2 and k / 2 + pi / a.
    assert np.allclose(
        np.sort([lower, upper], axis=0),
        np.sort([one_band(k / 2, 0.0, 1.0), one_band(k / 2 + np.pi, 0.0, 1.0)], axis=0),
    )


def test_the_allowed_wavenumbers_fill_the_zone():
    k = band_wavenumbers(8)
    assert k.min() > -np.pi and k.max() == pytest.approx(np.pi)
    assert len(set(np.round(k, 12))) == 8


def test_the_count_of_levels_is_the_closed_form_within_one():
    energies = ring_energies(37, [0.4], 1.5)
    e = np.linspace(-3.5, 4.5, 3001)
    below = np.searchsorted(energies, e)
    assert np.max(np.abs(below - 37 * counting(e, 0.4, 1.5))) <= 1 + 1e-9


def test_the_effective_mass_is_the_curvature_of_the_band_bottom():
    h = 1e-4
    curvature = (one_band(h, 0.0, 0.8, 1.5) - one_band(0.0, 0.0, 0.8, 1.5)) / h**2
    assert 1 / (2 * curvature) == pytest.approx(effective_mass(0.8, 1.5), rel=1e-6)


def test_the_filling_counts_two_electrons_per_level():
    assert filled([0.0, 1.0, 2.0, 3.0], 4) == (1.0, 2.0)
    with pytest.raises(ValueError):
        filled([0.0, 1.0], 3)
    with pytest.raises(ValueError):
        filled([0.0, 1.0], 4)


def test_the_propagation_is_the_matrix_exponential():
    h = chain_hamiltonian(40, 1.0, 0.3)
    psi0 = gaussian_packet(40, 20.0, 3.0, 0.5)
    run = propagate(h, psi0, [0.0, 2.7])
    assert np.allclose(run.psi[1], expm(-1j * h * 2.7) @ psi0, atol=1e-12)
    assert np.linalg.norm(run.psi[1]) == pytest.approx(1.0, abs=1e-12)


def test_a_moving_packet_follows_the_closed_form_centre():
    # A packet with a carrier, k0 = 1, starts moving: the closed form has
    # the phase of <T> and no fit.
    force, sites = 0.15, 500
    psi0 = gaussian_packet(sites, 250.0, 6.0, 1.0)
    shift = translation(psi0)
    assert np.angle(shift) == pytest.approx(-1.0, abs=1e-9)
    times = np.linspace(0, 2 * np.pi / force, 101)
    run = propagate(chain_hamiltonian(sites, 1.0, force), psi0, times)
    closed = bloch_centre(times, run.centre[0], shift, 1.0, force)
    assert np.max(np.abs(run.centre - closed)) < 1e-9


def test_without_a_force_the_closed_form_is_the_group_velocity():
    # For a small force and a short time the centre moves at
    # (2 t a / hbar) sin(k0 a) times Re of the spread factor.
    psi0 = gaussian_packet(400, 200.0, 20.0, 0.7)
    shift = translation(psi0)
    t = 1e-3
    speed = (bloch_centre(t, 0.0, shift, 1.0, 1e-6) - 0.0) / t
    assert speed == pytest.approx(2 * np.sin(0.7) * abs(shift), rel=1e-5)


# --- MAT3: elasticity ----------------------------------------------------------


def test_the_bar_stiffness_stores_the_energy_of_every_element():
    rng = np.random.default_rng(2)
    x = np.cumsum(rng.uniform(0.5, 1.5, size=6)) - 0.5
    modulus = rng.uniform(1.0, 3.0, size=5)
    u = rng.normal(size=6)
    k = bar_stiffness(x, modulus, 0.2)
    springs = 0.5 * np.sum(modulus * 0.2 / np.diff(x) * np.diff(u) ** 2)
    assert 0.5 * u @ k @ u == pytest.approx(springs, rel=1e-13)
    assert np.allclose(k @ np.ones(6), 0.0)  # a rigid translation
    with pytest.raises(ValueError):
        bar_stiffness(np.array([0.0, 1.0, 1.0]), 1.0, 1.0)


def test_the_bar_load_is_the_total_load():
    x = np.array([0.0, 0.3, 1.0, 1.6])
    f = bar_load(x, 2.0, 5.0)
    assert f.sum() == pytest.approx(2.0 * 1.6 + 5.0, rel=1e-14)
    assert f[0] == pytest.approx(2.0 * 0.3 / 2)


@pytest.mark.parametrize("elements", [1, 3, 7])
def test_the_bar_is_exact_at_the_nodes(elements):
    bar = solve_bar(2.0, elements, 3.0, 0.5, 1.5, 4.0)
    exact = bar_displacement(bar.x, 2.0, 3.0, 0.5, 1.5, 4.0)
    assert np.allclose(bar.u, exact, rtol=1e-12, atol=1e-14)
    mid = (bar.x[:-1] + bar.x[1:]) / 2
    assert np.allclose(bar.stress, bar_stress(mid, 2.0, 0.5, 1.5, 4.0), rtol=1e-12)
    assert bar.reaction == pytest.approx(-(4.0 + 1.5 * 2.0), rel=1e-12)


def test_the_closed_form_of_the_bar_solves_its_equation():
    # -E A u'' = q, u(0) = 0, E A u'(L) = F, by finite differences of the form.
    length, modulus, area, q, force = 3.0, 2.0, 0.7, 1.1, 0.4
    h = 1e-3
    x = 1.3
    second = (
        bar_displacement(x + h, length, modulus, area, q, force)
        - 2 * bar_displacement(x, length, modulus, area, q, force)
        + bar_displacement(x - h, length, modulus, area, q, force)
    ) / h**2
    assert -modulus * area * second == pytest.approx(q, rel=1e-6)
    assert bar_displacement(0.0, length, modulus, area, q, force) == 0.0
    slope = (
        bar_displacement(length + h, length, modulus, area, q, force)
        - bar_displacement(length - h, length, modulus, area, q, force)
    ) / (2 * h)
    assert modulus * area * slope == pytest.approx(force, rel=1e-6)


def test_hookes_law_in_plane_stress_contracts_by_poissons_ratio():
    d = plane_stress(2.0, 0.25)
    strain = np.linalg.solve(d, [1.0, 0.0, 0.0])  # a pull along x alone
    assert strain[0] == pytest.approx(1 / 2.0)
    assert -strain[1] / strain[0] == pytest.approx(0.25)
    # Shear: tau = G gamma with G = E / (2 (1 + nu)).
    assert d[2, 2] == pytest.approx(2.0 / (2 * 1.25))


def test_the_strain_matrices_differentiate_a_linear_field():
    mesh = rectangle(2.0, 1.0, 5, 3)
    g = np.array([[0.3, -0.2], [0.7, 0.1]])  # u = g x
    u = (mesh.nodes @ g.T).ravel()
    strain = np.einsum("tkj,tj->tk", strain_matrices(mesh), u[element_dofs(mesh)])
    expected = [g[0, 0], g[1, 1], g[0, 1] + g[1, 0]]
    assert np.allclose(strain, expected, atol=1e-13)


def test_the_plate_stiffness_has_the_rigid_motions_as_its_null_space():
    mesh = rectangle(2.0, 1.0, 4, 2)
    k = plate_stiffness(mesh, 3.0, 0.3, 0.1).toarray()
    assert np.allclose(k, k.T)
    x, y = mesh.nodes[:, 0], mesh.nodes[:, 1]
    for motion in (
        np.column_stack([np.ones_like(x), 0 * x]),
        np.column_stack([0 * x, np.ones_like(x)]),
        np.column_stack([-y, x]),  # a small rotation
    ):
        assert np.allclose(k @ motion.ravel(), 0.0, atol=1e-12)
    assert np.sum(np.linalg.eigvalsh(k) > 1e-9) == k.shape[0] - 3


def test_the_traction_load_is_the_force_on_the_edge():
    mesh = rectangle(2.0, 0.5, 4, 3)
    f = traction_load(mesh, "right", (3.0, -1.0), 0.2)
    assert f[0::2].sum() == pytest.approx(3.0 * 0.5 * 0.2)
    assert f[1::2].sum() == pytest.approx(-1.0 * 0.5 * 0.2)
    off = np.setdiff1d(np.arange(len(mesh.nodes)), mesh.boundary_nodes("right"))
    assert np.all(f[2 * off] == 0)


def test_the_roller_plate_reproduces_uniform_tension():
    mesh = rectangle(1.0, 0.4, 7, 3)
    load = traction_load(mesh, "right", (5.0, 0.0), 0.1)
    plate = solve_plate(mesh, 20.0, 0.35, 0.1, load, roller_supports(mesh))
    assert np.allclose(
        plate.u, uniform_tension(mesh.nodes, 20.0, 0.35, 5.0), atol=1e-13
    )
    assert np.allclose(plate.stress, [5.0, 0.0, 0.0], atol=1e-11)
    assert len(roller_supports(mesh)) == 4 + 1  # u_x on the left edge, u_y once


def test_the_clamped_reactions_balance_the_load():
    mesh = rectangle(1.0, 0.4, 8, 4)
    load = traction_load(mesh, "right", (5.0, 0.0), 0.1)
    plate = solve_plate(mesh, 20.0, 0.35, 0.1, load, clamped_supports(mesh))
    assert plate.reactions[0::2].sum() == pytest.approx(-5.0 * 0.4 * 0.1, rel=1e-12)
    assert plate.reactions[1::2].sum() == pytest.approx(0.0, abs=1e-12)
    free = np.setdiff1d(np.arange(2 * len(mesh.nodes)), clamped_supports(mesh))
    assert np.allclose(plate.reactions[free], 0.0, atol=1e-12)
    # The wall stops the contraction: the left edge keeps its height.
    left = mesh.boundary_nodes("left")
    assert np.allclose(plate.u[left], 0.0)


# --- MAT4: defects -------------------------------------------------------------


def test_the_free_energy_counts_the_arrangements_exactly():
    counts = np.arange(0, 30)
    g = free_energy(1000, counts, 0.3, 0.05)
    choose = gammaln(1001) - gammaln(counts + 1) - gammaln(1001 - counts)
    assert np.allclose(g, counts * 0.3 - 0.05 * choose, atol=1e-10)
    steps = [free_energy_step(1000, n, 0.3, 0.05) for n in counts[:-1]]
    assert np.allclose(steps, np.diff(g), atol=1e-10)


@pytest.mark.parametrize("kt", [0.04, 0.06, 0.1])
def test_the_exact_minimum_is_the_argmin_and_near_the_closed_form(kt):
    sites = 10**6
    n = exact_vacancies(sites, 0.5, kt)
    counts = np.arange(0, 3 * n + 10)
    assert n == int(np.argmin(free_energy(sites, counts, 0.5, kt)))
    assert abs(n - sites * float(vacancy_fraction(0.5, kt))) < 1


def test_the_vacancy_fraction_is_the_boltzmann_factor_when_small():
    assert float(vacancy_fraction(1.0, 0.05)) == pytest.approx(np.exp(-20), rel=1e-8)
    assert float(vacancy_fraction(1.0, 1e6)) == pytest.approx(0.5, rel=1e-5)
    assert float(hop_rate(2.0, 0.3, 0.1)) == pytest.approx(2.0 * np.exp(-3))


def test_the_lattice_walk_takes_lattice_steps_at_the_rate():
    rng = np.random.default_rng(4)
    times = np.array([1.0, 2.0, 5.0])
    paths = lattice_walks(20000, times, 3.0, 0.5, rng)
    assert paths.shape == (4, 20000, 2)
    assert np.allclose(paths / 0.5, np.round(paths / 0.5))
    assert np.all(paths[0] == 0)
    # <r^2> = 4 Gamma a^2 t: z Gamma t hops of a^2, with z = 4.
    msd = np.mean(np.sum(paths[-1] ** 2, axis=1))
    assert msd == pytest.approx(4 * 3.0 * 0.25 * 5.0, rel=0.03)
    with pytest.raises(ValueError):
        lattice_walks(2, np.array([1.0, 1.0]), 1.0, 1.0, rng)


def test_a_vacancy_moves_one_atom_per_jump():
    rng = np.random.default_rng(5)
    atoms, vacancy = vacancy_exchanges(5, [1, 2], 400, rng)
    # One jump: one atom moved by one spacing, the vacancy by one.
    assert np.all(atoms[0] == 1) and np.all(vacancy[0] == 1)
    # Two jumps: straight back (the same atom returns), a turn, or straight on.
    back = vacancy[1] == 0
    assert np.all(atoms[1][back] == 0) and np.all(atoms[1][~back] == 2)
    assert set(np.unique(vacancy[1])) == {0.0, 2.0, 4.0}
    assert np.mean(back) == pytest.approx(0.25, abs=0.07)
