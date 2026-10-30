"""The experiment of "Defects and material properties" (materials 04)."""

from pathlib import Path

import numpy as np
import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.materials.experiments.defects_and_material_properties"
PAGE = "materials/04-defects-and-material-properties"
F_SQUARE = 1 / (np.pi - 1)


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("defects_and_material_properties")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_exact_minimum_is_within_one_vacancy_of_the_closed_form(results):
    _, found = results

    rows = found["tables"]["vacancies"]["rows"]
    for temperature, fraction, closed, exact, difference in rows:
        x = np.exp(-1.0 / (8.617333262e-5 * float(temperature)))
        assert float(fraction) == pytest.approx(x / (1 + x), rel=1e-3)
        assert -1 < float(difference) <= 0
        assert int(exact) == pytest.approx(float(closed), abs=1)
    fractions = [float(row[1]) for row in rows]
    assert fractions == sorted(fractions)


def test_the_vacancy_diffuses_as_t1_predicts(results):
    _, found = results

    lattice, t1, prediction = found["tables"]["walk"]["rows"]
    # a^2 / (2 d tau) = Gamma a^2 at 1000 K, in cm^2/s.
    gamma = 1e13 * np.exp(-0.7 / (8.617333262e-5 * 1000))
    assert float(prediction[1]) == pytest.approx(gamma * (0.25e-9) ** 2 * 1e4, rel=1e-3)
    for row in (lattice, t1):
        assert abs(float(row[3])) < 3
        assert float(row[1]) == pytest.approx(float(prediction[1]), rel=0.05)


def test_the_arrhenius_fit_recovers_the_migration_energy(results):
    _, found = results

    for _, _, measured, predicted, gap in found["tables"]["arrhenius"]["rows"]:
        assert abs(float(gap)) < 3
        assert float(measured) == pytest.approx(float(predicted), rel=0.05)
    energy = float(found["numbers"]["migration-fit"])
    error = float(found["numbers"]["migration-error"])
    assert abs(energy - 0.7) < 3 * error and error < 0.01


def test_the_atoms_jumps_are_correlated_with_the_square_lattice_factor(results):
    _, found = results

    growth, early, late, vacancy = found["tables"]["correlation"]["rows"]
    assert abs(float(growth[1]) - F_SQUARE) < 3 * float(growth[2])
    assert float(early[1]) > float(late[1]) > F_SQUARE
    assert abs(float(vacancy[1]) - 1) < 3 * float(vacancy[2])
    sizes = found["tables"]["finite-size"]["rows"]
    assert float(sizes[0][1]) > F_SQUARE + 0.05
    assert abs(float(sizes[-1][3])) < 3
    # D* = f c_v D_v: the slowdown is 1 / (f c_v) at 1000 K.
    x = np.exp(-1.0 / (8.617333262e-5 * 1000))
    assert float(found["numbers"]["slowdown-1000"]) == pytest.approx(
        (1 + x) / (x * F_SQUARE), rel=0.05
    )


def test_the_hot_crystal_exercise_inverts_the_closed_form(results):
    _, found = results

    for name, c in (("t-1e-6", 1e-6), ("t-1e-4", 1e-4)):
        t = float(found["numbers"][name])
        x = np.exp(-1.0 / (8.617333262e-5 * t))
        assert x / (1 + x) == pytest.approx(c, rel=0.01)
