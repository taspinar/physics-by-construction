"""The experiment of "Gravitational-wave chirp simulation" (astrophysics 04)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.astrophysics.experiments.gravitational_wave_chirp"
PAGE = "astrophysics/04-gravitational-wave-chirp"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("gravitational_wave_chirp")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_gap_to_the_closed_form_is_its_first_correction(results):
    _, found = results

    rows = found["tables"]["chirp-check"]["rows"]
    slowness = [float(row[2]) for row in rows]
    assert slowness == sorted(slowness)
    # The amplitude gap over eps² is 57/32 throughout, while eps grows.
    for row in rows:
        assert float(row[4]) == pytest.approx(57 / 32, rel=2e-3)
    # Twice the orbital phase is the closed-form phase; the wave leads it
    # by +(5/4) eps, a lead that grows with eps.
    for row in rows:
        assert abs(float(row[5])) < 1e-8
        assert float(row[7]) == pytest.approx(5 / 4, rel=5e-3)
    leads = [float(row[6]) for row in rows]
    assert leads == sorted(leads) and leads[0] > 0
    assert found["numbers"]["orbit-gap"] == "below 1e-08"
    assert found["numbers"]["left"] == found["numbers"]["left-closed"]


def test_the_polarisations_follow_the_inclination(results):
    _, found = results

    for row in found["tables"]["inclinations"]["rows"]:
        assert float(row[1]) == pytest.approx(float(row[2]), abs=1e-5)
        assert float(row[3]) == pytest.approx(float(row[4]), abs=1e-6)


def test_one_chirp_mass_one_waveform_different_ends(results):
    _, found = results

    rows = found["tables"]["same-chirp-mass"]["rows"]
    assert len({row[2] for row in rows}) == 1
    ends = [float(row[4]) for row in rows]
    assert ends == sorted(ends, reverse=True)
    assert found["numbers"]["same-difference"] == "below 1e-06"


def test_the_band_agrees_with_the_closed_forms(results):
    _, found = results

    for row in found["tables"]["band"]["rows"]:
        assert row[3] == row[4]
        assert row[5] == row[6]
    assert found["numbers"]["band-gap"] == "below 1e-08"
    cycles = [float(row[5]) for row in found["tables"]["band"]["rows"]]
    assert cycles == sorted(cycles, reverse=True)
