"""The experiment of "Heat engines and thermodynamic cycles" (thermodynamics 06)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.thermodynamics.experiments.heat_engines_and_thermodynamic_cycles"
PAGE = "thermodynamics/06-heat-engines-and-thermodynamic-cycles"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("heat_engines_and_thermodynamic_cycles")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_first_law_holds_leg_by_leg_at_second_order(results):
    _, found = results

    assert float(found["numbers"]["first-law-largest"]) < 1e-5
    assert float(found["numbers"]["refinement-order"]) == pytest.approx(2.0, abs=0.05)


def test_every_engine_meets_its_closed_form_and_stays_within_the_carnot_bound(results):
    _, found = results

    for row in found["tables"]["comparison"]["rows"]:
        name, efficiency, form, bound, entropy = row[0], *map(float, row[3:6]), row[6]
        assert efficiency == pytest.approx(form, abs=2e-6)
        assert efficiency <= bound + 1e-6
        if name in ("Carnot", "Stirling, regenerated"):
            assert efficiency == pytest.approx(bound, abs=2e-6)
            assert entropy.startswith("below")
        else:
            assert efficiency < bound
            assert float(entropy) > 0.0


def test_a_claim_beyond_carnot_lowers_the_entropy_of_the_reservoirs(results):
    _, found = results

    claimed, bound, entropy = map(
        float, found["tables"]["impossible-engine"]["rows"][0]
    )
    assert claimed > bound
    assert entropy < 0.0
