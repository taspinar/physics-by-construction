"""Advection, the Burgers equation, the shared finite-volume interface, and the
shallow-water equations (lessons FL1, FL4, FL9, FL5): each component against a
closed form, a limiting case, or a budget, with a stated tolerance."""

import numpy as np
import pytest
from scipy.integrate import quad

from pbc.fluids import advection, burgers, shallow_water
from pbc.fluids.finite_volume import (
    conservative_update,
    evolve,
    interface_fluxes,
    periodic,
    rusanov,
    transmissive,
    with_ghosts,
)

RNG = np.random.default_rng(188)


# The shared finite-volume interface


def test_the_ghost_cells_close_the_domain_or_copy_the_end():
    q = np.array([1.0, 2.0, 3.0])

    assert with_ghosts(q, periodic).tolist() == [3.0, 1.0, 2.0, 3.0, 1.0]
    assert with_ghosts(q, transmissive).tolist() == [1.0, 1.0, 2.0, 3.0, 3.0]
    system = np.array([[1.0, 0.5], [2.0, -1.0]])
    padded = with_ghosts(system, shallow_water.reflective)
    assert padded[0].tolist() == [1.0, -0.5] and padded[-1].tolist() == [2.0, 1.0]


def test_the_update_changes_the_total_only_by_the_end_fluxes():
    q = RNG.normal(size=50)
    fluxes = RNG.normal(size=51)
    dt, dx = 0.01, 0.1

    after = conservative_update(q, fluxes, dt, dx)

    assert after.sum() * dx == pytest.approx(
        q.sum() * dx + dt * (fluxes[0] - fluxes[-1]), abs=1e-13
    )


def test_evolve_ends_at_the_time_and_closes_the_budget_of_any_data():
    u = RNG.uniform(-1.0, 2.0, size=80)

    run = evolve(
        u,
        0.0125,
        0.37,
        lambda v: interface_fluxes(v, burgers.godunov_flux, transmissive),
        burgers.max_speed,
        0.9,
    )

    assert run.t[-1] == 0.37 and np.all(np.diff(run.t) > 0)
    assert np.max(np.abs(run.budget_residual)) < 1e-13


def test_evolve_takes_the_step_of_the_cfl_condition():
    u = np.full(10, 2.0)

    run = evolve(
        u,
        0.1,
        1.0,
        lambda v: interface_fluxes(v, burgers.godunov_flux, periodic),
        burgers.max_speed,
        0.5,
    )

    # dt = 0.5 * 0.1 / 2 = 0.025: forty steps, all equal.
    assert len(run.t) == 41
    assert np.allclose(np.diff(run.t), 0.025)
    assert np.allclose(run.q, 2.0)


def test_evolve_leaves_a_state_without_wave_speed_unchanged_up_to_the_end_time():
    dry = np.zeros((10, 2))
    cases = [
        (np.zeros(10), burgers.godunov_flux, burgers.max_speed),
        (dry, shallow_water.hll_flux, shallow_water.max_speed),
    ]

    for q0, solver, speed in cases:
        run = evolve(
            q0,
            0.1,
            0.5,
            lambda v, solver=solver: interface_fluxes(v, solver, transmissive),
            speed,
            0.5,
        )

        assert np.array_equal(run.q, q0)
        assert run.t[-1] == 0.5
        assert np.max(np.abs(run.budget_residual)) == 0.0


def test_the_rusanov_flux_is_consistent_and_upwinds_with_diffusion():
    riemann = rusanov(burgers.flux, np.abs)
    states = np.array([-2.0, -0.5, 0.0, 1.0, 3.0])

    assert np.allclose(riemann(states, states), burgers.flux(states))
    left, right = np.array([2.0]), np.array([0.0])
    # The mean of the fluxes, 1, minus half the largest speed times the jump.
    assert riemann(left, right)[0] == pytest.approx(1.0 + 0.5 * 2.0 * 2.0)


# Advection and diffusion (FL1)


@pytest.mark.parametrize("courant", [0.25, 0.5, 0.9, 1.1])
@pytest.mark.parametrize("r", [0.0, 0.2])
def test_the_measured_factors_of_upwind_are_its_closed_form(courant, r):
    n = 32
    theta = 2.0 * np.pi * np.arange(n) / n

    found = advection.amplification("upwind", courant, n, r)

    expected = 1 - courant * (1 - np.exp(-1j * theta)) - 2 * r * (1 - np.cos(theta))
    assert np.allclose(found, expected, atol=1e-13)


@pytest.mark.parametrize("courant", [0.3, 0.8, 1.2])
@pytest.mark.parametrize("r", [0.0, 0.1, 0.3, 0.6])
def test_the_measured_factors_of_lax_wendroff_and_central_are_their_closed_forms(
    courant, r
):
    n = 32
    x = 1 - np.cos(2.0 * np.pi * np.arange(n) / n)

    lw = np.abs(advection.amplification("Lax-Wendroff", courant, n, r)) ** 2
    central = np.abs(advection.amplification("central", courant, n, r)) ** 2

    c2 = courant**2
    assert np.allclose(lw, 1 - 4 * r * x + x**2 * ((c2 + 2 * r) ** 2 - c2), atol=1e-13)
    assert np.allclose(
        central, 1 - 2 * x * (2 * r - c2) + x**2 * (4 * r**2 - c2), atol=1e-13
    )
    if r == 0.0:
        assert np.allclose(lw, 1 - c2 * (1 - c2) * x**2, atol=1e-13)
        assert np.allclose(central, 1 + c2 * x * (2 - x), atol=1e-13)


@pytest.mark.parametrize("courant", np.linspace(0.0, 1.2, 13))
@pytest.mark.parametrize("r", np.linspace(0.0, 0.7, 15))
def test_the_stability_limits_with_diffusion_are_the_derived_ones(courant, r):
    # Upwind C + 2 r <= 1, Lax-Wendroff C^2 + 2 r <= 1, central C^2 <= 2 r <= 1.
    limits = {
        "upwind": courant + 2 * r <= 1 + 1e-12,
        "Lax-Wendroff": courant**2 + 2 * r <= 1 + 1e-12,
        "central": courant**2 <= 2 * r + 1e-12 and r <= 0.5 + 1e-12,
    }
    for scheme, stable in limits.items():
        factors = advection.amplification(scheme, courant, 64, r)
        assert (np.max(np.abs(factors)) <= 1 + 1e-12) == stable, scheme


def test_upwind_at_courant_one_moves_the_profile_one_cell():
    u = RNG.normal(size=20)

    # u - (u - u_left) is u_left up to the rounding of the two subtractions.
    assert np.allclose(
        advection.step(u, 1.0, "upwind"), np.roll(u, 1), rtol=0, atol=1e-15
    )


def test_the_boundaries_feed_the_inflow_and_ignore_the_outflow():
    u = np.array([0.0, 0.5, 1.0])

    open_end = advection.step(u, 0.5, "upwind", advection.inflow_outflow(2.0))
    closed = advection.step(u, 0.5, "upwind", advection.fixed(2.0, -7.0))

    assert open_end[0] == pytest.approx(0.0 - 0.5 * (0.0 - 2.0))
    assert np.array_equal(open_end, closed)


def test_the_amplitude_of_a_mode_is_read_back():
    x = np.arange(64) / 64

    assert advection.mode_amplitude(0.7 * np.sin(2 * np.pi * 3 * x), 3) == (
        pytest.approx(0.7, abs=1e-13)
    )
    assert advection.mode_amplitude(np.cos(2 * np.pi * x), 2) == pytest.approx(
        0.0, abs=1e-13
    )


def test_the_numerical_diffusion_matches_the_factor_for_long_waves():
    # ln|G| / dt -> -nu_num k^2 as k dx -> 0, from the closed form of G.
    speed, dx, courant = 1.0, 0.01, 0.4
    dt = courant * dx / speed
    k = 2 * np.pi
    theta = k * dx
    g = 1 - courant * (1 - np.exp(-1j * theta))

    assert -np.log(abs(g)) / (dt * k * k) == pytest.approx(
        advection.modified_diffusion(speed, dx, courant), rel=1e-3
    )


# The Burgers equation (FL4)


def test_the_godunov_flux_is_consistent():
    u = np.linspace(-3.0, 3.0, 13)

    assert np.allclose(burgers.godunov_flux(u, u), burgers.flux(u))


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        (2.0, 0.0, 2.0),  # shock moving right: the flux of the left state
        (0.0, -2.0, 2.0),  # shock moving left: the flux of the right state
        (1.0, -1.0, 0.5),  # standing shock: both are 1/2
        (-1.0, 1.0, 0.0),  # fan across the face: the sonic value u = 0
        (0.5, 2.0, 0.125),  # fan moving right
        (-2.0, -0.5, 0.125),  # fan moving left
    ],
)
def test_the_godunov_flux_takes_the_state_at_the_face(left, right, expected):
    found = burgers.godunov_flux(np.array([left]), np.array([right]))

    assert found[0] == pytest.approx(expected)


def test_the_shock_speed_is_the_mean_and_the_dissipation_closes_the_energy_budget():
    left, right = 3.0, 0.5
    speed = burgers.shock_speed(left, right)

    assert speed == pytest.approx(1.75)
    # The energy that enters minus the rate of growth of the energy inside.
    lost = (left**3 - right**3) / 3 - speed * (left**2 - right**2) / 2
    assert burgers.shock_dissipation(left, right) == pytest.approx(lost)


def test_the_characteristic_solution_solves_its_implicit_equation():
    def u0(x):
        return 1.0 + 0.5 * np.sin(2 * np.pi * x)

    x = np.linspace(0.0, 1.0, 41)
    t = 0.25

    u = burgers.characteristic_solution(u0, x, t, 1.0)

    assert np.allclose(u, u0(x - u * t), atol=1e-12)
    assert burgers.breaking_time(np.pi * np.cos(2 * np.pi * x)) == pytest.approx(
        1 / np.pi
    )
    assert burgers.breaking_time(np.ones(5)) == np.inf


def test_the_riemann_solution_is_a_shock_or_a_fan():
    xi = np.array([-1.0, 0.2, 0.6, 2.0])

    assert burgers.riemann_solution(1.0, 0.0, xi).tolist() == [1.0, 1.0, 0.0, 0.0]
    assert burgers.riemann_solution(0.0, 1.0, xi).tolist() == [0.0, 0.2, 0.6, 1.0]


def test_the_nonconservative_step_agrees_with_the_conservative_one_where_smooth():
    n = 400
    dx = 1.0 / n
    u = 1.0 + 0.5 * np.sin(2 * np.pi * (np.arange(n) + 0.5) * dx)
    dt = 0.5 * dx / 1.5

    smooth = burgers.nonconservative_step(u, dt, dx, periodic)
    conservative = conservative_update(
        u, interface_fluxes(u, burgers.godunov_flux, periodic), dt, dx
    )

    # They differ by dt dx / 2 times u_x^2, of order dt dx.
    assert np.max(np.abs(smooth - conservative)) < 10 * dt * dx


# The shallow-water equations (FL5)

G = shallow_water.GRAVITY


def test_the_hll_flux_is_consistent_and_upwind_in_supercritical_flow():
    states = np.array([[1.0, 0.0], [2.0, 1.0], [0.5, -0.3]])

    assert np.allclose(
        shallow_water.hll_flux(states, states), shallow_water.flux(states)
    )
    # Both waves move right when u > sqrt(g h): the face sees the left flux.
    left, right = np.array([[1.0, 5.0]]), np.array([[1.1, 5.5]])
    assert np.allclose(shallow_water.hll_flux(left, right), shallow_water.flux(left))


def test_a_wall_lets_no_water_through():
    q = np.array([[1.3, 0.7], [0.9, -0.2]])
    padded = with_ghosts(q, shallow_water.reflective)

    fluxes = shallow_water.hll_flux(padded[:-1], padded[1:])

    assert fluxes[0, 0] == 0.0 and fluxes[-1, 0] == 0.0


def test_a_dry_cell_has_no_velocity_and_no_flux():
    dry = np.array([[0.0, 0.0], [1e-12, 1e-9]])

    assert shallow_water.velocity(dry).tolist() == [0.0, 0.0]
    assert np.allclose(shallow_water.flux(dry[:1]), 0.0)


def test_the_lake_at_rest_is_kept_by_the_reconstruction_and_not_by_the_point_source():
    n = 60
    dx = 0.2
    x = (np.arange(n) + 0.5) * dx
    bed = 0.3 * np.sin(x) + 0.2
    water = np.stack([1.0 - bed, np.zeros(n)], axis=-1)

    fluxes, source = shallow_water.well_balanced(bed, dx, shallow_water.reflective)
    kept = conservative_update(water, fluxes(water), 0.01, dx) + 0.01 * source(water)
    fluxes, source = shallow_water.pointwise_source(bed, dx, shallow_water.reflective)
    moved = conservative_update(water, fluxes(water), 0.01, dx) + 0.01 * source(water)

    assert np.max(np.abs(kept - water)) < 1e-14
    assert np.max(np.abs(moved[:, 1])) > 1e-5


def test_the_exact_dam_break_satisfies_both_jump_conditions_and_keeps_the_mass():
    h_up, h_down = 3.0, 1.0
    exact = shallow_water.dam_break(h_up, h_down)
    h, u, s = exact.middle, exact.middle_velocity, exact.front_speed

    # Mass and momentum across the shock moving at s into still water.
    assert s * (h - h_down) == pytest.approx(h * u)
    assert s * h * u == pytest.approx(h * u * u + G / 2 * (h * h - h_down * h_down))
    # u + 2c is the same on both sides of the rarefaction.
    assert u + 2 * np.sqrt(G * h) == pytest.approx(2 * np.sqrt(G * h_up))
    # The depth is continuous at both ends of the fan, and the volume is kept.
    t = 0.5
    c_up = np.sqrt(G * h_up)
    tail = (u - np.sqrt(G * h)) * t
    assert exact.depth([-c_up * t + 1e-9], t)[0] == pytest.approx(h_up, abs=1e-6)
    assert exact.depth([tail - 1e-9], t)[0] == pytest.approx(h, abs=1e-6)
    volume = quad(lambda y: exact.depth(y, t), -10, 10, points=[-c_up * t, tail, s * t],
                  limit=200)[0]  # fmt: skip
    assert volume == pytest.approx(10 * h_up + 10 * h_down, rel=1e-9)


def test_the_dry_dam_break_runs_out_at_twice_the_wave_speed():
    exact = shallow_water.dam_break(1.0, 0.0)
    c = np.sqrt(G)

    assert exact.front_speed == pytest.approx(2 * c)
    assert exact.depth([2 * c * 0.99], 1.0)[0] == pytest.approx(
        (2 * c - 2 * c * 0.99) ** 2 / (9 * G)
    )
    assert exact.depth([2 * c * 1.01], 1.0)[0] == 0.0
    with pytest.raises(ValueError):
        shallow_water.dam_break(1.0, 2.0)
