"""The experiment of "Crystal lattices and phonons" (materials 01)."""

from pathlib import Path

import numpy as np
import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.materials.experiments.crystal_lattices_and_phonons"
PAGE = "materials/01-crystal-lattices-and-phonons"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("crystal_lattices_and_phonons")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_ring_has_one_mode_per_atom_on_the_closed_form(results):
    _, found = results

    monatomic, diatomic = found["tables"]["dispersion"]["rows"]
    assert monatomic[2] == "24" and diatomic[2] == "48"
    assert monatomic[3].startswith("below") and diatomic[3].startswith("below")


def test_the_branch_edges_are_their_closed_forms(results):
    _, found = results

    rows = found["tables"]["branches"]["rows"]
    # m1 = 1, m2 = 2, K = 1: sqrt(2K / m2), sqrt(2K / m1), sqrt(2K (1 + 1/2)).
    expected = [1.0, np.sqrt(2), np.sqrt(3), np.sqrt(2) - 1]
    for row, value in zip(rows, expected, strict=True):
        assert float(row[1]) == pytest.approx(value, abs=1e-6)
        assert row[3].startswith("below")
    assert float(found["numbers"]["gap-ratio"]) == pytest.approx(np.sqrt(2), abs=1e-4)


def test_the_sound_speed_is_reached_at_second_order(results):
    _, found = results

    for _, k, mono, mono_gap, di, di_gap in found["tables"]["sound"]["rows"]:
        # The monatomic gap is exactly sin(ka/2) / (ka/2) - 1.
        x = float(k) / 2
        assert float(mono_gap) == pytest.approx(np.sin(x) / x - 1, rel=1e-2)
        assert float(mono) == pytest.approx(1 + float(mono_gap), abs=1e-5)
        # The diatomic sound speed is a sqrt(K / (2 (m1 + m2))) = sqrt(1/6).
        assert float(di) == pytest.approx(
            np.sqrt(1 / 6) * (1 + float(di_gap)), abs=1e-5
        )
        assert float(di_gap) < 0
    assert float(found["numbers"]["sound-order-mono"]) == pytest.approx(2.0, abs=0.05)
    assert float(found["numbers"]["sound-order-di"]) == pytest.approx(2.0, abs=0.05)


def test_the_packet_follows_the_group_velocity_not_the_phase_velocity(results):
    _, found = results

    rows = found["tables"]["packet"]["rows"]
    gaps = [abs(float(row[4])) for row in rows]
    assert gaps == sorted(gaps, reverse=True) and max(gaps) < 5e-3
    for _, speed, group, phase, _ in rows:
        assert float(group) == pytest.approx(np.cos(np.pi / 4), abs=1e-5)
        assert abs(float(speed) - float(phase)) > 0.15
    assert float(found["numbers"]["packet-order"]) == pytest.approx(2.0, abs=0.3)
    assert float(found["numbers"]["verlet-excess"]) < 0.2 * min(gaps)


def test_the_gap_closes_for_equal_masses_and_the_optical_branch_flattens(results):
    _, found = results

    assert found["numbers"]["equal-gap"].startswith("below")
    assert found["numbers"]["equal-difference"].startswith("below")
    widths = [float(row[1]) for row in found["tables"]["flat-optical"]["rows"]]
    assert widths == sorted(widths, reverse=True)
    for _, ring, closed in found["tables"]["flat-optical"]["rows"]:
        assert float(ring) == pytest.approx(float(closed), abs=1e-5)
