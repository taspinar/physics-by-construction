"""The vibrations of a chain and the bands of its electrons (lessons MAT1,
MAT2): each result is compared with a closed-form solution, a limiting
case, or an independent computation, with a stated tolerance."""

import numpy as np
import pytest
from scipy.linalg import expm

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
