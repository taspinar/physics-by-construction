"""The experiment of "Shallow-water equations: still water and the dam
break" (fluids 04)."""

import itertools
from pathlib import Path

import numpy as np
import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

from pbc.experiment import encode
from pbc.fluids.experiments import shallow_water_equations

MODULE = "pbc.fluids.experiments.shallow_water_equations"
PAGE = "fluids/04-shallow-water-equations"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("shallow_water_equations")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_figure_file_is_the_bytes_of_the_one_encoder(results):
    directory, found = results
    experiment = shallow_water_equations.run()

    for name in found["figures"]:
        label = name.removesuffix(".png")
        assert (directory / name).read_bytes() == encode(experiment.figures[label])


def test_the_lake_stays_still_only_with_the_reconstruction(results):
    _, found = results
    rows = found["tables"]["lake-run"]["rows"]

    assert all(row[1] == "below 1e-12" for row in rows)
    speeds = [float(row[2]) for row in rows]
    assert min(speeds) > 1e-3
    for coarse, fine in itertools.pairwise(speeds):
        assert coarse / fine == pytest.approx(2.0, rel=0.1)


def test_the_dam_break_converges_to_the_exact_solution(results):
    _, found = results
    numbers = found["numbers"]

    # The exact middle state: equal velocity behind the fan and the shock.
    g, h_up, h_down = 9.81, 2.0, 0.5
    h_mid, u_mid = float(numbers["middle-depth"]), float(numbers["middle-velocity"])
    assert u_mid == pytest.approx(
        2 * (np.sqrt(g * h_up) - np.sqrt(g * h_mid)), abs=1e-3
    )
    assert u_mid == pytest.approx(
        (h_mid - h_down) * np.sqrt(g * (h_mid + h_down) / (2 * h_mid * h_down)),
        abs=1e-3,
    )
    assert float(numbers["front-speed"]) == pytest.approx(
        h_mid * u_mid / (h_mid - h_down), abs=1e-3
    )
    assert 0.7 < float(numbers["dam-order"]) < 1.1
    for row in found["tables"]["dam-run"]["rows"]:
        assert float(row[4]) < 1.0


def test_the_depth_stays_positive_on_a_dry_bed(results):
    _, found = results
    rows = found["tables"]["dry-run"]["rows"]

    assert all(row[1] == "0.0" for row in rows)
    errors = [float(row[2]) for row in rows]
    assert errors == sorted(errors, reverse=True)
    fronts = [float(row[3]) for row in rows]
    assert fronts == sorted(fronts)
    assert fronts[-1] < float(found["numbers"]["dry-front"])


def test_the_exercises(results):
    _, found = results
    numbers = found["numbers"]

    assert float(numbers["wave-expected"]) == pytest.approx(np.sqrt(9.81), abs=1e-3)
    assert float(numbers["wave-measured"]) == pytest.approx(
        float(numbers["wave-expected"]), abs=0.01
    )
    volume, momentum = found["tables"]["tank-run"]["rows"]
    assert volume[2] == "0.0000" and volume[3] == momentum[3] == "below 1e-13"
    assert float(momentum[2]) != 0.0
