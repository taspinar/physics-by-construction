"""The experiment of "Shock waves and the Burgers equation" (fluids 02)."""

import itertools
from pathlib import Path

import numpy as np
import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

from pbc.experiment import encode
from pbc.fluids.experiments import shock_waves_and_burgers_equation

MODULE = "pbc.fluids.experiments.shock_waves_and_burgers_equation"
PAGE = "fluids/02-shock-waves-and-burgers-equation"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("shock_waves_and_burgers_equation")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_figure_file_is_the_bytes_of_the_one_encoder(results):
    directory, found = results
    experiment = shock_waves_and_burgers_equation.run()

    for name in found["figures"]:
        label = name.removesuffix(".png")
        assert (directory / name).read_bytes() == encode(experiment.figures[label])


def test_the_wave_breaks_at_one_over_pi_and_converges_with_order_one(results):
    _, found = results
    numbers = found["numbers"]

    assert float(numbers["breaking-time"]) == pytest.approx(1 / np.pi, abs=1e-4)
    assert float(numbers["smooth-order"]) == pytest.approx(1.0, abs=0.05)
    errors = [float(row[2]) for row in found["tables"]["steepening-run"]["rows"]]
    assert errors == sorted(errors, reverse=True)


def test_every_shock_moves_at_the_mean_of_its_states(results):
    _, found = results

    for left, right, measured, expected in found["tables"]["shock-run"]["rows"]:
        assert float(expected) == pytest.approx((float(left) + float(right)) / 2)
        assert float(measured) == pytest.approx(float(expected), abs=0.01 * 3)


def test_a_shock_dissipates_its_closed_form_and_smooth_flow_nothing_in_the_limit(
    results,
):
    _, found = results
    rows = found["tables"]["dissipation-run"]["rows"]

    assert found["numbers"]["dissipation-exact"] == "0.6667"
    for _, _, shock in rows:
        assert float(shock) == pytest.approx(2 / 3, rel=0.01)
    smooth = [float(row[1]) for row in rows]
    for coarse, fine in itertools.pairwise(smooth):
        assert coarse / fine == pytest.approx(2.0, rel=0.05)


def test_the_exercises(results):
    _, found = results
    numbers = found["numbers"]

    assert 0.6 < float(numbers["fan-order"]) < 1.0
    assert float(numbers["standing-speed"]) < 1e-3
    assert float(numbers["standing-position"]) == pytest.approx(0.5, abs=2.5e-3)
