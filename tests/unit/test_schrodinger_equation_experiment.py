"""The experiment of "The Schrödinger equation" (quantum 01)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.quantum.experiments.schrodinger_equation"
PAGE = "quantum/01-the-schrodinger-equation"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("schrodinger_equation")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_crank_nicolson_keeps_the_norm_and_converges_at_order_two(results):
    _, found = results

    assert found["numbers"]["norm-drift"] == "below 1e-12"
    assert float(found["numbers"]["order"]) == pytest.approx(2.0, abs=0.05)


def test_the_packet_follows_the_free_dispersion(results):
    _, found = results

    for row in found["tables"]["packet"]["rows"]:
        _, centre, exact_centre, width, exact_width, _ = map(float, row)
        assert centre == pytest.approx(exact_centre, abs=0.05)
        assert width == pytest.approx(exact_width, abs=0.05)
    for row in found["tables"]["dispersion"]["rows"]:
        assert float(row[5]) == pytest.approx(float(row[4]), rel=1e-3)


def test_explicit_euler_gains_the_predicted_norm(results):
    _, found = results

    rows = found["tables"]["euler"]["rows"]
    assert [row[1] for row in rows] == [row[2] for row in rows]
    assert float(rows[-1][1]) > float(rows[0][1])
