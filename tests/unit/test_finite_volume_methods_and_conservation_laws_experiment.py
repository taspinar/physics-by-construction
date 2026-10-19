"""The experiment of "Finite-volume methods and conservation laws"
(fluids 03)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

from pbc.experiment import encode
from pbc.fluids.experiments import finite_volume_methods_and_conservation_laws

MODULE = "pbc.fluids.experiments.finite_volume_methods_and_conservation_laws"
PAGE = "fluids/03-finite-volume-methods-and-conservation-laws"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("finite_volume_methods_and_conservation_laws")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_figure_file_is_the_bytes_of_the_one_encoder(results):
    directory, found = results
    experiment = finite_volume_methods_and_conservation_laws.run()

    for name in found["figures"]:
        label = name.removesuffix(".png")
        assert (directory / name).read_bytes() == encode(experiment.figures[label])


def test_every_budget_closes_and_only_the_open_and_walled_totals_change(results):
    _, found = results
    rows = found["tables"]["budget-run"]["rows"]

    assert all(row[4] == "below 1e-13" for row in rows)
    changes = {(row[0], row[1], row[2]): float(row[3]) for row in rows}
    # The open Burgers run gains (u_L^2 - u_R^2) / 2 per second: 1.875 * 0.3.
    assert changes[("Burgers", "open", "u")] == pytest.approx(0.5625, abs=1e-4)
    assert changes[("Burgers", "periodic", "u")] == 0.0
    assert changes[("shallow water", "periodic", "h")] == 0.0
    assert changes[("shallow water", "periodic", "hu")] == 0.0
    assert changes[("shallow water", "walls", "h")] == 0.0
    assert changes[("shallow water", "walls", "hu")] != 0.0


def test_within_the_cfl_limit_nothing_grows_and_beyond_it_the_solution_blows_up(
    results,
):
    _, found = results

    for courant, variation, largest in found["tables"]["courant-run"]["rows"]:
        if float(courant) <= 1.0:
            assert float(variation) < 1.0 and float(largest) < 1.0
    assert float(found["tables"]["courant-run"]["rows"][-1][1]) > 10.0


def test_the_non_conservative_scheme_converges_to_a_wrong_shock(results):
    _, found = results
    numbers = found["numbers"]

    assert float(numbers["right-order"]) == pytest.approx(1.0, abs=0.1)
    assert abs(float(numbers["wrong-order"])) < 0.1
    for row in found["tables"]["comparison-run"]["rows"]:
        assert float(row[3]) == pytest.approx(1.25, abs=1e-3)
        assert float(row[4]) < 1.0
    # The mass it loses is the speed it lacks times the jump.
    assert float(numbers["created"]) == pytest.approx(
        float(numbers["deficit"]), abs=0.01
    )


def test_any_conservative_flux_gives_the_rankine_hugoniot_speed(results):
    _, found = results

    for _, speed, _, _ in found["tables"]["rusanov-run"]["rows"]:
        assert float(speed) == pytest.approx(1.25, abs=1e-3)
    assert float(found["numbers"]["upwind-flux-speed"]) == pytest.approx(1.25, abs=1e-3)
