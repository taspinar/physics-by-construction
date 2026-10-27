"""The experiment of the capstone "Thermal engineering of an AI accelerator"
(thermodynamics 09)."""

import re
from itertools import pairwise
from pathlib import Path

import pytest
from support.experiments import (
    assert_the_page_and_the_results_agree,
    page_of,
    run_entry_point,
)

MODULE = "pbc.thermodynamics.experiments.thermal_engineering_of_an_ai_accelerator"
PAGE = "thermodynamics/09-thermal-engineering-of-an-ai-accelerator"
LIMIT = 85.0  # degrees C, the junction limit the page states


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("thermal_engineering_of_an_ai_accelerator")
    return directory, run_entry_point(MODULE, directory)


def numbers(results) -> dict:
    return results[1]["numbers"]


def rows(results, name: str) -> list[list[str]]:
    return results[1]["tables"][name]["rows"]


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_credibility_boundary_is_a_typed_claim_on_the_page():
    page = page_of(PAGE)
    claim = re.search(r"::: \{\.claim ([^}]*)\}\n(.*?)\n:::", page, re.S)
    assert claim, "the page opens no claim div"
    attributes, text = claim.groups()
    assert 'type="numerically-verified"' in attributes
    assert "hypothetical" in attributes
    text = " ".join(text.split())
    for phrase in (
        "digital-twin-style teaching prototype",
        "not a calibrated twin",
        "no vendor data",
        "no proprietary or real accelerator",
        "no three-dimensional computational fluid dynamics",
        "not validation",
    ):
        assert phrase in text, phrase
    # It comes before the first section, so that it frames the whole page.
    assert page.index(claim.group(0)) < page.index("## Assumptions")


def test_both_methods_converge_to_the_exact_cosine_mode(results):
    found = numbers(results)
    assert float(found["cosine-fem-order"]) == pytest.approx(2.0, abs=0.05)
    assert float(found["cosine-fd-order"]) == pytest.approx(2.0, abs=0.05)
    # The largest error of the elements, at a corner, converges more slowly.
    assert 1.5 < float(found["cosine-corner-order"]) < 1.95
    for coarse, fine in pairwise(rows(results, "cosine-mode")):
        for column in (2, 3):
            assert float(coarse[column]) / float(fine[column]) == pytest.approx(
                4.0, rel=0.1
            )


def test_the_methods_agree_under_refinement_and_the_balances_close(results):
    found = numbers(results)
    assert found["balance-gap"] == "below 1e-10"
    assert found["insert-balance-gap"] == "below 1e-10"
    assert float(found["method-order"]) == pytest.approx(2.0, abs=0.1)
    table = rows(results, "mesh-study")
    for row in table:
        assert row[5] == "below 1e-10"
    differences = [float(row[4]) for row in table]
    assert differences == sorted(differences, reverse=True)
    assert differences[-1] < 0.01


def test_the_inserts_converge_more_slowly_than_strips_without_corners(results):
    found = numbers(results)
    assert 1.0 < float(found["inserts-order"]) < 1.7
    assert float(found["strips-order"]) == pytest.approx(2.0, abs=0.1)
    assert float(found["insert-change"]) < 1e-3


def test_the_plate_model_is_close_to_the_cross_section_and_on_the_safe_side(results):
    found = numbers(results)
    assert 0.0 < float(found["section-least"]) <= float(found["section-gap"]) < 0.5
    assert float(found["section-change"]) < 0.01
    for row in rows(results, "cross-section"):
        assert float(row[5]) > 0.0  # the plate model is the warmer


def test_the_theta_methods_have_their_orders_against_the_exact_solution(results):
    found = numbers(results)
    assert float(found["euler-order"]) == pytest.approx(1.0, abs=0.05)
    assert float(found["crank-order"]) == pytest.approx(2.0, abs=0.15)


def test_the_explicit_step_is_measured_stable_below_its_limit_only(results):
    found = numbers(results)
    (row,) = rows(results, "explicit-limit")
    exact, measured, used = float(row[1]), float(row[2]), float(row[3])
    assert measured == pytest.approx(exact, rel=1e-3)
    assert used < exact
    assert float(row[5]) > 2.0  # it diverges at the implicit step
    assert int(found["step-ratio"]) > 5
    assert int(found["explicit-steps"]) > 5 * int(found["implicit-steps"])


def test_the_transients_agree_and_conserve_energy(results):
    found = numbers(results)
    assert found["energy-gap"] == "below 1e-10"
    assert float(found["transient-gap"]) < 1.0
    assert float(found["late-gap"]) < 0.2
    assert 0.5 < float(found["settle-copper"]) < float(found["settle-insert"]) < 3.0
    table = rows(results, "transient")
    for column in (1, 2, 3):
        values = [float(row[column]) for row in table]
        assert values == sorted(values)  # the junction only warms


def test_the_layout_optimum_is_the_centre_of_each_half(results):
    found = numbers(results)
    assert found["best-separation"] == "32"
    for row in rows(results, "layout"):
        assert row[3] == "32"
        assert float(row[4]) < float(row[5])
        assert row[6] == "yes"


def test_the_thickness_and_the_coefficient_only_cool(results):
    table = rows(results, "bounds")
    for row in table:
        values = [float(v) for v in row[2:]]
        assert values == sorted(values, reverse=True)
    for column in (2, 3, 4):
        values = [float(row[column]) for row in table]
        assert values == sorted(values, reverse=True)


def test_the_baseline_reproduces_the_sensitivities(results):
    found = numbers(results)
    assert float(found["sensitivity-agreement"]) < 0.05
    table = rows(results, "sensitivity")
    assert found["leading-input"] == table[0][0] == "compute-die power"
    for row in table[:-1]:  # the inserts' conductivity has no baseline
        for elements, differences in ((row[3], row[5]), (row[4], row[6])):
            assert float(elements) == pytest.approx(float(differences), abs=0.05)


def test_the_recommendation_follows_the_stated_rule(results):
    found = numbers(results)
    table = rows(results, "trade-off")
    assert int(found["scenario-count"]) == len(table)
    feasible = [row for row in table if row[7] == "meets all"]
    assert int(found["feasible-count"]) == len(feasible)
    for row in table:
        assert ("junction" in row[7]) == (float(row[5]) > LIMIT)
    # Nothing meets the limit with air or on the nominal flow, nor the plain
    # aluminium spreader.
    for row in table:
        if row[1] != "cold plate, full flow" or row[0] == "aluminium":
            assert float(row[5]) > LIMIT
    assert found["recommended"].startswith("aluminium, copper inserts, 3.00 mm")
    assert found["runner-up"].startswith("copper, 2.18 mm")
    # The two coolest differ by less than the model's gap: the lighter wins.
    assert float(found["runner-up-difference"]) < float(found["section-gap"])
    assert float(found["recommended-mass"]) < float(found["runner-up-mass"])
    margin = float(found["recommended-margin"])
    assert margin == pytest.approx(
        LIMIT - float(found["recommended-junction"]), abs=0.1
    )
    # The margin covers every single input but the compute power.
    assert float(found["second-swing"]) < margin
    assert abs(float(found["largest-swing"]) - margin) < 1.0


def test_the_simple_estimates_bracket_the_field(results):
    found = numbers(results)
    assert float(found["even-error"]) > 10.0
    assert float(found["straight-error"]) > 20.0
    for row in rows(results, "estimates"):
        assert float(row[1]) < float(row[2]) < float(row[3])


def test_a_burst_crosses_the_limit_within_the_first_second(results):
    table = rows(results, "burst")
    assert float(table[0][1]) < LIMIT < float(table[1][1])
    values = [float(row[1]) for row in table]
    assert values == sorted(values)


def test_the_coolant_warms_in_inverse_proportion_to_the_flow(results):
    found = numbers(results)
    table = rows(results, "coolant-rise")
    for slow, fast in pairwise(table):
        assert float(slow[1]) / float(fast[1]) == pytest.approx(2.0, rel=0.05)
    assert float(table[0][1]) > float(found["recommended-margin"])
    assert float(table[2][1]) < 5.0
