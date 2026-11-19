"""The experiment of "Verifying scientific code" (mechanics 09)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.mechanics.experiments.verifying_scientific_code"
PAGE = "mechanics/09-verifying-scientific-code"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("verifying_scientific_code")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_correct_steppers_pass_every_check_they_claim(results):
    _, found = results

    assert "FAIL" not in found["outputs"]["correct"]


def test_every_faulty_stepper_fails_a_check(results):
    _, found = results
    matrix = found["outputs"]["gallery"].split("\n\n")[0].splitlines()[1:]

    assert matrix
    assert all("FAIL" in line for line in matrix)


def test_only_the_true_order_of_verlet_passes(results):
    _, found = results
    lines = found["outputs"]["claimed-orders"].splitlines()

    assert [line.split(":")[1].split()[0] for line in lines] == ["FAIL", "pass", "FAIL"]


# --- The model-to-code route on the damped driven oscillator (F141). ---


def rows(found: dict, table: str) -> dict[str, list[str]]:
    return {row[0]: row[1:] for row in found["tables"][table]["rows"]}


def test_the_reference_solution_passes_every_check_of_the_model(results):
    _, found = results
    findings = found["tables"]["driven-findings"]["rows"]

    assert [row[1] for row in findings] == [
        "limits",
        "convergence-order",
        "units",
        "energy-balance",
    ]
    assert all(row[0] == "pass" for row in findings)
    assert rows(found, "faulty-simulations")["reference solution"][:4] == ["pass"] * 4


def test_every_faulty_simulation_fails_a_check_and_the_page_names_it(results):
    from pbc.verification.driven import MODEL_CHECKS
    from pbc.verification.faulty_driven import GALLERY

    _, found = results
    table = rows(found, "faulty-simulations")

    for entry in GALLERY:
        failed = tuple(
            check
            for check, mark in zip(MODEL_CHECKS, table[entry.name][:4], strict=True)
            if mark == "FAIL"
        )
        assert failed == entry.caught_by, entry.name
        assert table[entry.name][4] == entry.fault


def test_the_stopped_clock_shows_on_the_model_and_the_hidden_state_does_not(results):
    _, found = results
    table = rows(found, "steppers-on-the-model")

    assert table["velocity Verlet"] == ["pass"] * 4
    assert table["verlet with a stopped clock"] == ["pass", "FAIL", "pass", "FAIL"]
    assert table["verlet that remembers"] == ["pass"] * 4


def test_the_missing_division_hides_at_one_kilogram_and_the_units_find_it(results):
    _, found = results
    table = rows(found, "unit-mass")

    assert table["convergence-order at a mass of 1 kg"][0] == "pass"
    assert table["convergence-order at a mass of 0.5 kg"][0] == "FAIL"
    assert table["units: the unit of mass changed"][0] == "FAIL"
    assert table["units: the unit of length changed"][0] == "pass"
    assert table["units: the unit of time changed"][0] == "pass"


def test_the_report_on_the_submission_names_the_failed_checks(results):
    _, found = results
    report = found["outputs"]["submission-report"]

    assert "verdict: claim not supported by convergence-order, energy-balance" in report
    assert "not covered:" in report and "reproduce:" in report


def test_no_evidence_text_of_the_model_shows_a_value_at_round_off(results):
    # Digits at the level of round-off differ between machines, and the
    # reproduction compares the page with a reader's run.
    import re

    _, found = results
    texts = [row[3] for row in found["tables"]["driven-findings"]["rows"]]
    texts.append(found["outputs"]["submission-report"])
    for text in texts:
        for exponent in re.findall(r"\d\.\de-(\d\d)", text):
            assert int(exponent) < 12, text


def test_the_transcript_is_marked_not_verified_with_the_agent_and_the_date():
    from support.experiments import page_of

    page = page_of(PAGE)
    start = page.index("**Example transcript")
    block = page[page.rindex(":::", 0, start) : page.index("\n:::\n", start)]

    assert block.startswith("::: {.not-verified}")
    assert "Agent: " in block and "Date: 2026-11-18" in block
    assert "```text" in block
