"""Waveguide modes and wire antennas (lesson EM6,
pbc.electromagnetism.waveguides and pbc.electromagnetism.antennas): each
against a closed form, an identity, or a limit."""

import numpy as np
import pytest

from pbc.electromagnetism.antennas import (
    IMPEDANCE_OF_FREE_SPACE,
    array_factor,
    directivity,
    far_field,
    half_wave_dipole_pattern,
    half_wave_radiation_resistance,
    radiation_resistance,
    short_dipole_pattern,
    wire_current,
    wire_elements,
)
from pbc.electromagnetism.fdtd import SPEED_OF_LIGHT
from pbc.electromagnetism.waveguides import (
    attenuation,
    cross_section_cutoffs,
    cutoff_frequency,
    group_velocity,
    guide_wavenumber,
    modes,
    phase_velocity,
)

A, B = 22.86e-3, 10.16e-3


def test_the_te10_cutoff_of_wr90_is_c_over_2a():
    assert cutoff_frequency(1, 0, A, B) == pytest.approx(SPEED_OF_LIGHT / (2 * A))
    assert cutoff_frequency(1, 0, A, B) == pytest.approx(6.557e9, rel=1e-4)


def test_the_mode_lists_follow_the_rules_of_te_and_tm():
    te = modes(A, B, 4, "TE")
    tm = modes(A, B, 2, "TM")
    assert [(m, n) for m, n, _ in te] == [(1, 0), (2, 0), (0, 1), (1, 1)]
    assert [(m, n) for m, n, _ in tm] == [(1, 1), (2, 1)]
    with pytest.raises(ValueError):
        modes(A, B, 2, "TEM")


@pytest.mark.parametrize("kind", ["TE", "TM"])
def test_the_eigenproblem_matches_the_eigenvalues_of_the_grid(kind):
    """On a grid the five-point eigenvalues are known in closed form:
    k^2 = (2/h)^2 (sin^2(m pi / 2 N_a) + sin^2(n pi / 2 N_b))."""
    na, nb = 18, 8
    found = cross_section_cutoffs(A, B, na, nb, kind, 3)
    first = 0 if kind == "TE" else 1
    grid = sorted(
        (2 * na / A) ** 2 * np.sin(m * np.pi / (2 * na)) ** 2
        + (2 * nb / B) ** 2 * np.sin(n * np.pi / (2 * nb)) ** 2
        for m in range(first, na)
        for n in range(first, nb)
        if m + n > 0
    )[:3]
    expected = SPEED_OF_LIGHT * np.sqrt(grid) / (2 * np.pi)
    np.testing.assert_allclose(found, expected, rtol=1e-10)


def test_the_eigenproblem_converges_to_the_closed_form():
    exact = [mode[2] for mode in modes(A, B, 3, "TE")]
    errors = [
        np.max(np.abs(cross_section_cutoffs(A, B, 9 * r, 4 * r, "TE", 3) / exact - 1))
        for r in (2, 4)
    ]
    assert errors[1] == pytest.approx(errors[0] / 4, rel=0.05)


def test_phase_times_group_velocity_is_c_squared():
    f_c, f = 6.5e9, np.array([7e9, 10e9, 20e9])
    np.testing.assert_allclose(
        phase_velocity(f, f_c) * group_velocity(f, f_c), SPEED_OF_LIGHT**2
    )
    np.testing.assert_allclose(
        guide_wavenumber(f, f_c), 2 * np.pi * f / phase_velocity(f, f_c)
    )


def test_a_wave_either_travels_or_decays():
    f_c = 6.5e9
    assert np.isnan(guide_wavenumber(5e9, f_c))
    assert np.isnan(attenuation(8e9, f_c))
    # Far below the cut-off the decay is pi / a per metre, set by the width alone.
    assert attenuation(1.0, SPEED_OF_LIGHT / (2 * A)) == pytest.approx(np.pi / A)


def test_the_wire_current_is_one_at_the_feed_and_zero_at_the_ends():
    z = np.array([-0.25, 0.0, 0.25])
    np.testing.assert_allclose(wire_current(z, 0.5, 1.0), [0.0, 1.0, 0.0], atol=1e-15)
    with pytest.raises(ValueError):
        wire_current(z, 1.0, 1.0)


def test_one_short_element_radiates_the_hertzian_dipole_field():
    """r E_theta = j eta k I dl sin(theta) / (4 pi), and its radiation
    resistance is (2 pi / 3) eta (dl / lambda)^2, the 80 pi^2 (dl / lambda)^2
    of the textbooks with eta = 120 pi."""
    theta = np.linspace(0.0, np.pi, 2001)
    dl = 0.01
    field = far_field(theta, 0.0, [[0.0, 0.0, 0.0]], [dl], 1.0)
    np.testing.assert_allclose(
        field,
        1j * IMPEDANCE_OF_FREE_SPACE * 2 * np.pi * dl * np.sin(theta) / (4 * np.pi),
    )
    assert radiation_resistance(field, theta, 1.0) == pytest.approx(
        2 * np.pi / 3 * IMPEDANCE_OF_FREE_SPACE * dl**2, rel=1e-6
    )
    assert directivity(np.abs(field) ** 2, theta) == pytest.approx(1.5, rel=1e-5)


def test_the_half_wave_wire_by_superposition_is_the_closed_form_dipole():
    theta = np.linspace(0.0, np.pi, 1441)
    z, dz = wire_elements(0.5, 400)
    positions = np.column_stack([0 * z, 0 * z, z])
    field = far_field(theta, 0.0, positions, wire_current(z, 0.5, 1.0) * dz, 1.0)
    pattern = np.abs(field) / np.abs(field).max()
    np.testing.assert_allclose(pattern, half_wave_dipole_pattern(theta), atol=1e-5)
    assert radiation_resistance(field, theta, 1.0) == pytest.approx(
        half_wave_radiation_resistance(), rel=1e-4
    )
    assert half_wave_radiation_resistance() == pytest.approx(73.08, abs=0.01)


def test_the_closed_form_patterns_have_their_textbook_directivities():
    theta = np.linspace(0.0, np.pi, 4001)
    assert directivity(short_dipole_pattern(theta) ** 2, theta) == pytest.approx(
        1.5, rel=1e-6
    )
    assert directivity(half_wave_dipole_pattern(theta) ** 2, theta) == pytest.approx(
        1.6409, abs=1e-4
    )


def test_the_array_factor_of_two_elements_half_a_wavelength_apart():
    phi = np.array([0.0, 0.5 * np.pi])
    theta = np.full(2, 0.5 * np.pi)
    centres = [[-0.25, 0.0, 0.0], [0.25, 0.0, 0.0]]
    in_phase = np.abs(array_factor(theta, phi, centres, [1, 1], 1.0))
    antiphase = np.abs(array_factor(theta, phi, centres, [1, -1], 1.0))
    # Along the line joining them the two waves arrive half a period apart.
    np.testing.assert_allclose(in_phase, [0.0, 2.0], atol=1e-12)
    np.testing.assert_allclose(antiphase, [2.0, 0.0], atol=1e-12)
