import numpy as np
import pytest

from pbc.mechanics.dynamics import State, euler_step, newton, simulate
from pbc.mechanics.energy import energy_drift, mechanical_energy
from pbc.mechanics.integrators import (
    INTEGRATORS,
    rk4_step,
    symplectic_euler_step,
    verlet_step,
)
from pbc.mechanics.orbit import (
    Orbit,
    angular_momentum,
    central_gravity,
    eccentricity_vector,
    gravitational_attraction,
    gravitational_potential,
    kepler_motion,
    orbital_elements,
)
from pbc.mechanics.particles import interacting, reduced_mass, stack, unstack

# Astronomical units, years, and solar masses, as in lesson M8: an orbit
# with a = 1 AU has the period 1 yr.
GM = 4 * np.pi**2
MASS = 1.0
GRAVITY = newton(MASS, central_gravity(GM, MASS))
POTENTIAL = gravitational_potential(GM, MASS)


def at_periapsis(a: float, e: float) -> State:
    """The state at the closest point of an orbit with the given elements,
    moving anticlockwise."""
    r = a * (1 - e)
    return State(t=0.0, x=[r, 0.0], v=[0.0, np.sqrt(GM * (1 + e) / r)])


def test_the_attraction_between_two_bodies_is_the_inverse_square_law():
    force = gravitational_attraction(GM, 2.0, 3.0)

    r = np.array([3.0, 4.0])
    np.testing.assert_allclose(force(r), -GM * 6.0 / 25.0 * r / 5.0)
    # The relative motion of the pair is one body of the reduced mass
    # under the central force with G (m1 + m2).
    pair = interacting([2.0, 3.0], force)
    accelerations = unstack(pair(0.0, stack([r, [0.0, 0.0]]), np.zeros(4)), 2)
    mu = reduced_mass(2.0, 3.0)
    one_body = newton(mu, central_gravity(GM * 5.0, mu))(0.0, r, np.zeros(2))
    np.testing.assert_allclose(accelerations[0] - accelerations[1], one_body)


def test_the_central_force_is_minus_the_gradient_of_the_potential():
    x = np.array([0.8, -0.6])
    h = 1e-6
    gradient = np.array(
        [
            (POTENTIAL(x + h * np.eye(2)[i]) - POTENTIAL(x - h * np.eye(2)[i]))
            / (2 * h)
            for i in range(2)
        ]
    )
    np.testing.assert_allclose(
        central_gravity(GM, MASS)(0.0, x, np.zeros(2)), -gradient, rtol=1e-7
    )


def test_angular_momentum_is_the_cross_product_in_the_plane():
    trajectory = kepler_motion(State(0.0, x=[2.0, 0.0], v=[0.0, 3.0]), GM, [0.0])
    np.testing.assert_allclose(angular_momentum(trajectory, 0.5), [0.5 * 6.0])
    with pytest.raises(ValueError, match="plane"):
        angular_momentum(
            simulate(State(0.0, 1.0, 1.0), lambda t, x, v: -x, 0.1, 1), 1.0
        )


def test_orbital_elements_come_from_energy_and_angular_momentum():
    circle = orbital_elements(State(0.0, x=[2.0, 0.0], v=[0.0, np.sqrt(GM / 2.0)]), GM)
    assert circle.eccentricity == pytest.approx(0.0, abs=1e-12)
    assert circle.semi_major_axis == pytest.approx(2.0)
    assert circle.period == pytest.approx(
        2 * np.pi * np.sqrt(8.0 / GM)
    )  # Kepler's third law

    ellipse = orbital_elements(at_periapsis(1.5, 0.4), GM)
    assert ellipse == Orbit(
        pytest.approx(1.5), pytest.approx(0.4), pytest.approx(1.5**1.5)
    )
    assert ellipse.periapsis == pytest.approx(0.9)
    assert ellipse.apoapsis == pytest.approx(2.1)


def test_a_body_at_or_above_the_escape_speed_has_no_orbit():
    escape = np.sqrt(2 * GM / 1.0)
    with pytest.raises(ValueError, match="not bound"):
        orbital_elements(State(0.0, x=[1.0, 0.0], v=[0.0, escape]), GM)
    assert (
        orbital_elements(
            State(0.0, x=[1.0, 0.0], v=[0.0, 0.999 * escape]), GM
        ).eccentricity
        < 1
    )


def test_a_body_falling_straight_at_the_centre_has_no_orbit():
    """Regression: a bound state with zero angular momentum once passed
    ``orbital_elements`` and made ``kepler_motion`` return NaN throughout,
    from the initial instant on."""
    at_rest = State(0.0, x=[1.0, 0.0], v=[0.0, 0.0])
    along_the_line = State(0.0, x=[0.6, 0.8], v=[-0.3, -0.4])
    for radial in (at_rest, along_the_line):
        with pytest.raises(ValueError, match="radial"):
            orbital_elements(radial, GM)
        with pytest.raises(ValueError, match="radial"):
            kepler_motion(radial, GM, [0.0, 0.1])


def test_the_eccentricity_vector_points_to_the_periapsis_and_is_constant():
    initial = at_periapsis(1.0, 0.5)
    np.testing.assert_allclose(eccentricity_vector(initial, GM), [0.5, 0.0], atol=1e-14)

    exact = kepler_motion(initial, GM, np.linspace(0.0, 1.0, 7))
    for t, x, v in zip(exact.t, exact.x, exact.v, strict=True):
        np.testing.assert_allclose(
            eccentricity_vector(State(t, x, v), GM), [0.5, 0.0], atol=1e-12
        )


def test_the_exact_motion_passes_through_the_initial_state_and_repeats_after_a_period():
    # A generic state, not at the periapsis, moving clockwise.
    initial = State(t=0.3, x=[1.0, 0.5], v=[3.0, -4.0])
    orbit = orbital_elements(initial, GM)

    exact = kepler_motion(
        initial, GM, [0.3, 0.3 + orbit.period, 0.3 + 2.5 * orbit.period]
    )

    np.testing.assert_allclose(exact.x[0], initial.x, atol=1e-12)
    np.testing.assert_allclose(exact.v[0], initial.v, atol=1e-12)
    np.testing.assert_allclose(exact.x[1], initial.x, atol=1e-12)
    np.testing.assert_allclose(exact.v[1], initial.v, atol=1e-12)
    distances = np.hypot(exact.x[:, 0], exact.x[:, 1])
    assert (
        orbit.periapsis - 1e-12 <= distances.min()
        and distances.max() <= orbit.apoapsis + 1e-12
    )


def test_the_exact_motion_reaches_the_apoapsis_half_a_period_after_the_periapsis():
    initial = at_periapsis(1.0, 0.6)
    orbit = orbital_elements(initial, GM)
    exact = kepler_motion(initial, GM, [orbit.period / 2])

    np.testing.assert_allclose(exact.x[0], [-orbit.apoapsis, 0.0], atol=1e-12)
    assert exact.v[0, 1] < 0 and exact.v[0, 0] == pytest.approx(0.0, abs=1e-12)


def test_the_exact_motion_conserves_energy_and_momentum_and_solves_the_equation():
    initial = State(t=0.0, x=[1.2, -0.3], v=[1.0, 5.0])
    times = np.linspace(0.0, 3.0, 61)
    exact = kepler_motion(initial, GM, times)

    energies = mechanical_energy(exact, MASS, POTENTIAL)
    np.testing.assert_allclose(energies, energies[0], rtol=1e-12)
    momenta = angular_momentum(exact, MASS)
    np.testing.assert_allclose(momenta, momenta[0], rtol=1e-12)
    # dx/dt = v and dv/dt = -GM x / |x|³, by central differences.
    h = 1e-6
    for t in (0.4, 1.7, 2.9):
        before, at, after = (kepler_motion(initial, GM, s) for s in (t - h, t, t + h))
        np.testing.assert_allclose(
            (after.x[0] - before.x[0]) / (2 * h), at.v[0], rtol=0, atol=1e-6
        )
        r = np.hypot(*at.x[0])
        np.testing.assert_allclose(
            (after.v[0] - before.v[0]) / (2 * h),
            -GM * at.x[0] / r**3,
            rtol=0,
            atol=1e-5,
        )


def test_a_circular_orbit_is_traced_at_constant_speed():
    exact = kepler_motion(
        State(0.0, x=[0.0, 1.0], v=[-2 * np.pi, 0.0]), GM, np.linspace(0.0, 1.0, 9)
    )

    np.testing.assert_allclose(np.hypot(exact.x[:, 0], exact.x[:, 1]), 1.0, rtol=1e-12)
    np.testing.assert_allclose(
        np.hypot(exact.v[:, 0], exact.v[:, 1]), 2 * np.pi, rtol=1e-12
    )
    np.testing.assert_allclose(
        exact.x[2], [-1.0, 0.0], atol=1e-12
    )  # a quarter turn anticlockwise


@pytest.mark.parametrize("radius", [0.5, 1.0, 2.0, 5.0, 30.0])
@pytest.mark.parametrize("angle_degrees", [0.0, 37.0, 90.0, 200.0])
@pytest.mark.parametrize("sense", [1.0, -1.0], ids=["anticlockwise", "clockwise"])
def test_exact_circular_orbits_start_where_they_are_and_stay_on_the_circle(
    radius, angle_degrees, sense
):
    """Regression: the eccentricity of a circular state is round-off, and
    the eccentricity vector is round-off too. Dividing the one by the other
    once collapsed the reference orbit to the origin."""
    angle = np.radians(angle_degrees)
    x = radius * np.array([np.cos(angle), np.sin(angle)])
    v = sense * np.sqrt(GM / radius) * np.array([-np.sin(angle), np.cos(angle)])
    initial = State(t=0.0, x=x, v=v)
    orbit = orbital_elements(initial, GM)

    assert orbit.eccentricity == pytest.approx(0.0, abs=1e-14)
    assert orbit.semi_major_axis == pytest.approx(radius, rel=1e-12)

    exact = kepler_motion(initial, GM, np.linspace(0.0, orbit.period, 13))
    np.testing.assert_allclose(exact.x[0], x, rtol=0, atol=1e-12 * radius)
    np.testing.assert_allclose(exact.v[0], v, rtol=0, atol=1e-12 * np.hypot(*v))
    np.testing.assert_allclose(exact.x[-1], x, rtol=0, atol=1e-10 * radius)
    np.testing.assert_allclose(
        np.hypot(exact.x[:, 0], exact.x[:, 1]), radius, rtol=1e-12
    )
    np.testing.assert_allclose(
        np.hypot(exact.v[:, 0], exact.v[:, 1]), np.sqrt(GM / radius), rtol=1e-12
    )
    # A quarter of a period on: a quarter turn in the sense of the motion.
    np.testing.assert_allclose(
        exact.x[3],
        sense * radius * np.array([-np.sin(angle), np.cos(angle)]),
        rtol=0,
        atol=1e-10 * radius,
    )


@pytest.mark.parametrize("e", [1e-10, 1e-7, 1e-4])
def test_exact_nearly_circular_orbits_keep_their_small_eccentricity(e):
    initial = at_periapsis(3.0, e)
    orbit = orbital_elements(initial, GM)

    assert orbit.eccentricity == pytest.approx(e, abs=1e-14)
    np.testing.assert_allclose(eccentricity_vector(initial, GM), [e, 0.0], atol=1e-14)

    exact = kepler_motion(initial, GM, np.linspace(0.0, 2 * orbit.period, 25))
    np.testing.assert_allclose(exact.x[0], initial.x, rtol=0, atol=1e-12)
    np.testing.assert_allclose(exact.x[-1], initial.x, rtol=0, atol=1e-10)
    np.testing.assert_allclose(exact.x[6], [-orbit.apoapsis, 0.0], rtol=0, atol=1e-10)
    distances = np.hypot(exact.x[:, 0], exact.x[:, 1])
    assert orbit.periapsis - 1e-12 <= distances.min()
    assert distances.max() <= orbit.apoapsis + 1e-12
    energies = mechanical_energy(exact, MASS, POTENTIAL)
    np.testing.assert_allclose(energies, energies[0], rtol=1e-12)


def test_the_symplectic_methods_conserve_the_angular_momentum_to_round_off():
    """Acceptance criterion 2: for any central force the velocity change of
    symplectic Euler and velocity Verlet is along the position, so the
    angular momentum is exact at every step, even at a coarse step. The
    other two methods change it."""
    initial = at_periapsis(1.0, 0.5)
    exact = angular_momentum(kepler_motion(initial, GM, [0.0]), MASS)[0]
    results = {
        step: angular_momentum(simulate(initial, GRAVITY, 1 / 50, 500, step=step), MASS)
        for step in (symplectic_euler_step, verlet_step, euler_step, rk4_step)
    }

    for step in (symplectic_euler_step, verlet_step):
        np.testing.assert_allclose(results[step], exact, rtol=1e-12)
    for step in (euler_step, rk4_step):
        assert np.ptp(results[step]) > 1e-6 * exact


def test_verlet_keeps_the_energy_of_the_orbit_in_a_band_and_runge_kutta_drains_it():
    """Acceptance criterion 2: over 200 orbits with e = 0.5 at 100 steps per
    orbit, the energy drift of velocity Verlet stays below 2 per cent and is
    no larger over the whole run than over its first half; Runge-Kutta 4's
    drift grows with the run."""
    initial = at_periapsis(1.0, 0.5)
    n_steps = 200 * 100

    verlet = mechanical_energy(
        simulate(initial, GRAVITY, 1 / 100, n_steps, step=verlet_step), MASS, POTENTIAL
    )
    rk4 = mechanical_energy(
        simulate(initial, GRAVITY, 1 / 100, n_steps, step=rk4_step), MASS, POTENTIAL
    )

    assert energy_drift(verlet) < 0.02
    assert energy_drift(verlet) <= 1.01 * energy_drift(verlet[: n_steps // 2])
    assert energy_drift(rk4) > 1.5 * energy_drift(rk4[: n_steps // 2])
    # Runge-Kutta 4 loses energy, so the orbit shrinks.
    assert rk4[-1] < rk4[0] < 0


@pytest.mark.parametrize("integrator", INTEGRATORS[2:], ids=lambda i: i.name)
def test_the_position_error_on_the_orbit_converges_at_the_order_of_the_method(
    integrator,
):
    initial = at_periapsis(1.0, 0.3)
    errors = []
    for steps_per_orbit in (400, 800, 1600, 3200):
        simulated = simulate(
            initial,
            GRAVITY,
            1 / steps_per_orbit,
            2 * steps_per_orbit,
            step=integrator.step,
        )
        exact = kepler_motion(initial, GM, simulated.t)
        errors.append(np.max(np.hypot(*(simulated.x - exact.x).T)))
    errors = np.array(errors)

    orders = np.log2(errors[:-1] / errors[1:])
    np.testing.assert_allclose(orders, integrator.order, rtol=0, atol=0.15)


def test_verlet_turns_the_orbit_by_an_angle_proportional_to_the_square_of_the_step():
    """The error the bounded energy does not see: the periapsis precesses,
    by an angle per orbit that quarters when the step halves."""
    initial = at_periapsis(1.0, 0.5)
    turns = []
    for steps_per_orbit in (100, 200):
        simulated = simulate(
            initial,
            GRAVITY,
            1 / steps_per_orbit,
            20 * steps_per_orbit,
            step=verlet_step,
        )
        final = State(simulated.t[-1], simulated.x[-1], simulated.v[-1])
        e = eccentricity_vector(final, GM)
        turns.append(abs(np.arctan2(e[1], e[0])))

    assert turns[0] > np.radians(1.0)
    assert turns[1] == pytest.approx(turns[0] / 4, rel=0.1)
