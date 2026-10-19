"""The experiment of "Discovering differential equations from trajectories"
(agents-llm 09, D8)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.mechanics.experiments.discovering_differential_equations"
PAGE = "agents-llm/09-discovering-differential-equations"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("discovering_differential_equations")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_equation_is_recovered_from_clean_positions(results):
    _, found = results
    numbers = found["numbers"]

    assert numbers["recovered"] == "recovered"
    assert float(numbers["largest-error"]) < float(numbers["tolerance"])
    kept = {
        row[0]: float(row[2])
        for row in found["tables"]["coefficients"]["rows"]
        if row[2]
    }
    assert kept == pytest.approx({"x": -4.0, "v": -0.3}, rel=1e-3)


def test_the_found_equation_holds_from_a_held_out_start(results):
    _, found = results
    numbers = found["numbers"]

    assert float(numbers["held-out-error"]) < 1e-3 * float(
        numbers["held-out-amplitude"]
    )


def test_one_orbit_cannot_tell_the_equation_from_a_rival(results):
    _, found = results
    numbers = found["numbers"]

    (true, on_true, off_true), (_, on_rival, off_rival) = found["tables"][
        "rival-equations"
    ]["rows"]
    assert true == "a = -4 x"
    # Both fit the orbit within the error of the differences; only another
    # orbit separates them.
    assert max(float(on_true), float(on_rival)) < 1e-3
    assert float(off_true) < 1e-3 < 1.0 < float(off_rival)
    assert numbers["near-zero"] == "3"
    assert float(numbers["smallest-several"]) > 0.01


def test_a_pendulum_gives_the_law_of_its_training_range(results):
    _, found = results

    (_, linear, drift_small), (_, cubic, drift_large) = found["tables"]["pendulum"][
        "rows"
    ]
    assert "x^3" not in linear and "x^3" in cubic and "+" in cubic
    assert float(drift_large) < float(drift_small)
