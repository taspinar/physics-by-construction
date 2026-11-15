"""The experiment of "Kinematics as a program" (mechanics 01)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

from pbc.experiment import encode
from pbc.mechanics.experiments import kinematics

MODULE = "pbc.mechanics.experiments.kinematics"
PAGE = "mechanics/01-kinematics-as-a-program"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("kinematics")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_figure_files_are_the_bytes_of_the_one_encoder(results):
    directory, found = results
    experiment = kinematics.run()

    for name in found["figures"]:
        label = name.removesuffix(".png")
        assert (directory / name).read_bytes() == encode(experiment.figures[label])


def test_the_lag_of_the_ball_is_the_predicted_one(results):
    _, found = results
    numbers = found["numbers"]

    # x_n - x(t_n) = -a t dt / 2 with a = -g, in the digits shown.
    assert numbers["ball-gap"] == numbers["predicted-lag"] == "1.177"
    # The computed velocity is exact for a constant acceleration.
    for row in found["tables"]["thrown-ball"]["rows"]:
        assert row[3] == row[4]


def test_the_first_step_is_high_by_half_g_dt_squared(results):
    _, found = results
    numbers = found["numbers"]

    # One step of explicit Euler from the launch: the velocity is exact, the
    # height is too high by g dt^2 / 2, in the digits shown.
    assert numbers["one-step-v"] == numbers["one-step-exact-v"]
    assert numbers["one-step-gap"] == numbers["one-step-predicted"] == "0.049"
    assert float(numbers["one-step-x"]) > float(numbers["one-step-exact-x"])
    # Every step adds the same gap: the gap of the whole flight is n times it.
    steps = int(numbers["n-steps"])
    assert float(numbers["ball-gap"]) == pytest.approx(
        steps * kinematics.g * kinematics.dt**2 / 2, abs=5e-4
    )


def test_the_error_halves_with_the_time_step(results):
    _, found = results

    assert found["numbers"]["last-ratio"] == "2.0000"
    assert float(found["numbers"]["last-order"]) == pytest.approx(1.0, abs=0.01)
    ratios = [row[3] for row in found["tables"]["halving"]["rows"][1:]]
    assert all(float(ratio) == pytest.approx(2.0, abs=1e-3) for ratio in ratios)


def test_the_second_order_step_is_exact_for_free_fall(results):
    _, found = results

    assert float(found["numbers"]["improved-error"]) == 0.0
    assert int(found["numbers"]["steps-needed"]) == 28244
