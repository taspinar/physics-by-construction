import json

import numpy as np
import pytest

from pbc.mechanics.dynamics import State, newton, simulate
from pbc.mechanics.explorer import STEPS_PER_PERIOD, explorer_data
from pbc.mechanics.integrators import INTEGRATORS
from pbc.mechanics.oscillator import energy, harmonic_motion, spring


@pytest.fixture(scope="module")
def data():
    return explorer_data()


def test_every_integrator_has_a_run_at_every_step_count(data):
    assert [run["name"] for run in data["integrators"]] == [i.name for i in INTEGRATORS]
    for run in data["integrators"]:
        assert [s["steps_per_period"] for s in run["series"]] == list(STEPS_PER_PERIOD)


def test_a_run_has_one_point_per_step_and_the_start(data):
    for run in data["integrators"]:
        for series in run["series"]:
            points = series["steps_per_period"] * data["n_periods"] + 1
            assert len(series["x"]) == len(series["e"]) == points
            assert series["x"][0] == data["amplitude"]
            assert series["e"][0] == 1.0


def test_the_data_is_json(data):
    assert json.loads(json.dumps(data, allow_nan=False)) == data


def test_the_exact_curve_is_the_harmonic_motion(data):
    t = np.linspace(0.0, data["n_periods"] * data["period"], len(data["exact"]["t"]))
    # The times are sent with five significant digits too.
    np.testing.assert_allclose(data["exact"]["t"], t, rtol=1e-4, atol=1e-4)
    exact = harmonic_motion(State(0.0, data["amplitude"], 0.0), 0.5, 2.0, t)
    # The curve is sent with five significant digits.
    np.testing.assert_allclose(data["exact"]["x"], exact.x[:, 0], atol=2e-5)


@pytest.mark.parametrize("integrator", INTEGRATORS, ids=lambda i: i.name)
def test_the_summary_numbers_match_an_independent_run(data, integrator):
    mass, k, omega = data["mass"], data["k"], data["omega"]
    period = data["period"]
    run = next(r for r in data["integrators"] if r["name"] == integrator.name)
    calls = []

    def counting(t, x, v):
        calls.append(1)
        return newton(mass, spring(k))(t, x, v)

    for series in run["series"]:
        n = series["steps_per_period"]
        calls.clear()
        trajectory = simulate(
            State(0.0, 1.0, 0.0),
            counting,
            period / n,
            n * data["n_periods"],
            step=integrator.step,
        )
        e = energy(trajectory, mass, k)
        exact = harmonic_motion(State(0.0, 1.0, 0.0), mass, k, trajectory.t)
        assert series["final_energy"] == pytest.approx(e[-1] / e[0], rel=1e-12)
        assert series["max_error"] == pytest.approx(
            np.max(np.abs(trajectory.x - exact.x)), rel=1e-12
        )
        assert series["calls"] == len(calls)
    assert omega == pytest.approx(2.0)


def test_the_physics_the_widget_shows_is_the_physics_of_the_lesson(data):
    # Explicit Euler multiplies the energy by 1 + (omega dt)^2 every step;
    # velocity Verlet stays within a band; both are what the lesson derives.
    euler = data["integrators"][0]["series"][STEPS_PER_PERIOD.index(32)]
    z = data["omega"] * data["period"] / 32
    assert euler["final_energy"] == pytest.approx((1 + z**2) ** (32 * 5), rel=1e-9)
    verlet = data["integrators"][2]["series"][STEPS_PER_PERIOD.index(32)]
    assert min(verlet["e"]) > 0.99 and max(verlet["e"]) < 1.01
