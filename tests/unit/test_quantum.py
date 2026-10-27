"""The Schrödinger solver, barrier scattering, and the bound states (lessons
Q1, Q2, Q3): each result is compared with a closed-form solution, a limiting
case, or an independent computation, with a stated tolerance."""

import numpy as np
import pytest

from pbc.quantum.barrier import (
    HBAR,
    KINETIC,
    on_grid,
    packet_transmission,
    rectangle,
    scattering,
    transmission,
    wavenumber,
)
from pbc.quantum.eigenstates import (
    box_energy,
    eigenstates,
    hermite_functions,
    oscillator_energy,
    oscillator_potential,
    oscillator_shift,
    quartic_moment,
)
from pbc.quantum.schrodinger import (
    apply,
    box_mode,
    box_wavenumber,
    crank_nicolson,
    crank_nicolson_frequency,
    euler_norm,
    explicit_euler,
    free_energy,
    free_packet,
    free_spread,
    gaussian_packet,
    grid_energy,
    hamiltonian,
    line,
    mean_momentum,
    mean_position,
    measured_frequency,
    norm,
    spread,
)
from pbc.verification.estimates import fitted_order

PACKET = {"centre": -10.0, "width": 1.0, "wavenumber": 2.0}

# --- Q1: the time-dependent equation -----------------------------------------


def test_the_line_has_interior_nodes_between_the_walls():
    grid = line(0.0, 1.0, 4)

    assert grid.h == 0.25
    assert grid.x.tolist() == [0.25, 0.5, 0.75]


def test_the_hamiltonian_is_the_second_difference_plus_the_potential():
    grid = line(0.0, 1.0, 8)
    v = grid.x**2
    diagonal, off = hamiltonian(v, grid.h)
    psi = np.sin(np.pi * grid.x)
    padded = np.concatenate([[0.0], psi, [0.0]])
    second = (padded[2:] - 2 * padded[1:-1] + padded[:-2]) / grid.h**2

    assert apply(diagonal, off, psi) == pytest.approx(-0.5 * second + v * psi)


def test_the_free_packet_is_the_fft_propagation_of_the_gaussian():
    # The exact free propagator, exp(-i k^2 t / 2) in Fourier space, applied
    # by the FFT on a periodic line long enough that the packet never wraps.
    x = np.linspace(-100.0, 100.0, 4096, endpoint=False)
    k = 2 * np.pi * np.fft.fftfreq(x.size, x[1] - x[0])
    start = gaussian_packet(x, **PACKET)
    for t in (0.0, 1.0, 6.0):
        evolved = np.fft.ifft(np.fft.fft(start) * np.exp(-0.5j * k**2 * t))
        assert np.max(np.abs(evolved - free_packet(x, t, **PACKET))) < 1e-12


def test_the_free_packet_moves_at_the_group_velocity_and_spreads():
    x = np.linspace(-40.0, 60.0, 20001)
    h = x[1] - x[0]
    for t in (0.0, 3.0, 6.0):
        psi = free_packet(x, t, **PACKET)
        assert norm(psi, h) == pytest.approx(1.0, abs=1e-12)
        assert mean_position(x, psi, h) == pytest.approx(-10.0 + 2.0 * t, abs=1e-9)
        assert spread(x, psi, h) == pytest.approx(free_spread(t, width=1.0), abs=1e-9)
        # The centred difference reads sin(k h) / h for k: (k h)^2 / 6 low.
        assert mean_momentum(psi, h) == pytest.approx(2.0, abs=1e-4)


def test_crank_nicolson_keeps_the_norm_and_converges_at_order_two():
    errors, spacings = [], []
    for cells in (350, 700, 1400):
        grid = line(-30.0, 40.0, cells)
        dt = 0.2 * grid.h
        steps = round(6.0 / dt)
        run = crank_nicolson(
            gaussian_packet(grid.x, **PACKET),
            np.zeros_like(grid.x),
            h=grid.h,
            dt=dt,
            n_steps=steps,
            every=steps // 4,
        )
        assert np.max(np.abs(norm(run.psi, grid.h) - norm(run.psi[0], grid.h))) < 1e-12
        exact = free_packet(grid.x, run.t[-1], **PACKET)
        errors.append(np.max(np.abs(run.psi[-1] - exact)))
        spacings.append(grid.h)

    assert fitted_order(spacings, errors) == pytest.approx(2.0, abs=0.05)


def test_explicit_euler_gains_the_norm_its_spectrum_predicts():
    grid = line(-30.0, 40.0, 700)
    start = gaussian_packet(grid.x, **PACKET)
    v = np.zeros_like(grid.x)
    run = explicit_euler(start, v, h=grid.h, dt=0.002, n_steps=300, every=100)
    predicted = euler_norm(start, v, h=grid.h, dt=0.002, steps=[0, 100, 200, 300])

    assert np.all(np.diff(norm(run.psi, grid.h)) > 0)
    assert norm(run.psi, grid.h) == pytest.approx(predicted, rel=1e-10)


def test_a_box_mode_turns_at_the_frequency_of_the_scheme():
    grid = line(0.0, 10.0, 200)
    for j in (1, 20, 100):
        mode = box_mode(grid, j)
        k = box_wavenumber(grid, j)
        diagonal, off = hamiltonian(np.zeros_like(grid.x), grid.h)
        assert apply(diagonal, off, mode) == pytest.approx(
            grid_energy(k, grid.h) * mode, abs=1e-9
        )
        run = crank_nicolson(mode, np.zeros_like(grid.x), h=grid.h, dt=0.01, n_steps=1)
        assert measured_frequency(run, mode) == pytest.approx(
            crank_nicolson_frequency(grid_energy(k, grid.h), 0.01), rel=1e-10
        )


def test_the_grid_dispersion_tends_to_the_free_one():
    k = np.array([0.5, 1.0, 2.0])
    for h in (1e-2, 1e-3):
        assert grid_energy(k, h) == pytest.approx(
            free_energy(k) * (1 - (k * h) ** 2 / 12), rel=1e-6
        )
    assert crank_nicolson_frequency(2.0, 1e-4) == pytest.approx(2.0, rel=1e-8)


# --- Q2: the barrier ---------------------------------------------------------


def test_the_electron_constants_are_codata():
    assert pytest.approx(0.0380998, rel=1e-6) == KINETIC
    assert pytest.approx(0.658212, rel=1e-6) == HBAR


def test_the_closed_form_has_its_limits():
    # Continuous through the top of the barrier.
    top = transmission(1.0, 1.0, 0.5)
    assert transmission([1.0 - 1e-9, 1.0 + 1e-9], 1.0, 0.5) == pytest.approx(
        [top, top], rel=1e-6
    )
    # Thick barrier: T -> 16 E (V0 - E) / V0^2 exp(-2 kappa a).
    e, v0, a = 0.3, 1.0, 3.0
    kappa = np.sqrt((v0 - e) / KINETIC)
    assert transmission(e, v0, a) == pytest.approx(
        16 * e * (v0 - e) / v0**2 * np.exp(-2 * kappa * a), rel=1e-12
    )
    # Resonance above the barrier: T = 1 where q a = n pi.
    resonance = 1.0 + KINETIC * (np.pi / 0.5) ** 2
    assert transmission(resonance, 1.0, 0.5) == pytest.approx(1.0, abs=1e-12)


def test_runge_kutta_converges_to_the_closed_form_at_order_four():
    energies = np.array([0.2, 0.5, 0.9, 1.1, 2.0])
    exact = transmission(energies, 1.0, 0.5)
    errors = []
    for steps in (10, 20, 40, 80):
        t, r = scattering(energies, rectangle(1.0), 0.5, steps)
        errors.append(np.max(np.abs(t - exact)))
        assert np.max(np.abs(r + t - 1)) < 1e-3

    assert fitted_order(0.5 / np.array([10, 20, 40, 80]), errors) > 3.9
    assert errors[-1] < 1e-7


def test_the_barrier_on_the_grid_has_its_area():
    for h in (0.03, 0.02, 0.07):
        x = np.arange(-1.0, 2.0, h)
        assert h * np.sum(on_grid(x, h, 1.0, 0.5)) == pytest.approx(0.5, abs=1e-12)


def test_a_packet_on_a_barrier_passes_with_the_averaged_transmission():
    k0 = float(wavenumber(0.6))
    grid = line(-80.0, 80.0, 4000)
    dt, steps = 0.2, 550
    run = crank_nicolson(
        gaussian_packet(grid.x, centre=-30.0, width=3.0, wavenumber=k0),
        on_grid(grid.x, grid.h, 1.0, 0.5),
        h=grid.h,
        dt=dt,
        n_steps=steps,
        every=steps,
        kinetic=KINETIC,
        hbar=HBAR,
    )
    passed = grid.h * np.sum(np.abs(run.psi[-1][grid.x > 0.5]) ** 2)

    assert passed == pytest.approx(packet_transmission(k0, 3.0, 1.0, 0.5), rel=1e-2)


# --- Q3: bound states --------------------------------------------------------


def test_the_hermite_functions_are_orthonormal_eigenfunctions():
    x = np.linspace(-12.0, 12.0, 24001)
    h = x[1] - x[0]
    rows = hermite_functions(6, x)

    assert h * rows @ rows.T == pytest.approx(np.eye(6), abs=1e-10)
    # -psi''/2 + x^2 psi / 2 = (n + 1/2) psi, psi'' by central differences,
    # whose own error is of order h^2 = 1e-6.
    second = (rows[:, 2:] - 2 * rows[:, 1:-1] + rows[:, :-2]) / h**2
    energies = oscillator_energy(np.arange(6))[:, None]
    residual = -0.5 * second + (0.5 * x[1:-1] ** 2 - energies) * rows[:, 1:-1]
    assert np.max(np.abs(residual)) < 1e-5


def test_the_levels_converge_with_the_predicted_coefficient():
    n = np.arange(6)
    for cells in (160, 320, 640):
        grid = line(-8.0, 8.0, cells)
        energies, vectors = eigenstates(oscillator_potential(grid.x), grid.h, 6)
        error = energies - oscillator_energy(n)
        assert error / oscillator_shift(n, grid.h) == pytest.approx(
            np.ones(6), abs=0.4 * grid.h
        )
        assert np.max(np.abs(vectors.T - hermite_functions(6, grid.x))) < 0.07 * grid.h


def test_a_box_that_cuts_the_state_raises_its_level():
    low = []
    for half in (2.0, 3.0, 6.0):
        grid = line(-half, half, round(2 * half / 0.02))
        low.append(eigenstates(oscillator_potential(grid.x), grid.h, 3)[0])
    assert np.all(low[0] > low[1]) and np.all(low[1] > low[2])
    assert low[2] - oscillator_energy(np.arange(3)) == pytest.approx(
        oscillator_shift(np.arange(3), 0.02), rel=1e-3
    )


def test_an_empty_box_has_the_grid_energies_of_its_modes():
    grid = line(0.0, 2.0, 200)
    energies, _ = eigenstates(np.zeros_like(grid.x), grid.h, 4)
    n = np.arange(1, 5)
    assert energies == pytest.approx(grid_energy(n * np.pi / 2.0, grid.h), rel=1e-10)
    assert energies == pytest.approx(box_energy(n, 2.0), rel=1e-3)


def test_a_weak_quartic_term_shifts_the_levels_by_the_moment():
    grid = line(-8.0, 8.0, 1600)
    base, _ = eigenstates(oscillator_potential(grid.x), grid.h, 3)
    strength = 1e-4
    perturbed, _ = eigenstates(
        oscillator_potential(grid.x) + strength * grid.x**4, grid.h, 3
    )
    assert (perturbed - base) / strength == pytest.approx(
        quartic_moment(np.arange(3)), rel=0.02
    )
