"""The experiment of the capstone "Autonomous Physics Lab" (agents-llm 25,
slot SA9, F145 part 2, Issue #614): every claim of the page is asserted here
as the page states it, the figure of the pilot's record follows the
conventions of measured data, and nothing reaches a device or a model."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point
from support.figures import assert_cell_declared, dataset_figures

from pbc.authoring.tables import is_numeric_console_block
from pbc.electromagnetism.experiments import autonomous_physics_lab as lab

MODULE = "pbc.electromagnetism.experiments.autonomous_physics_lab"
PAGE = "agents-llm/25-autonomous-physics-lab"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("autonomous-physics-lab")
    return directory, run_entry_point(MODULE, directory)


@pytest.fixture(scope="module")
def experiment():
    return lab.run()


def rows(results, name):
    return results[1]["tables"][name]["rows"]


def numbers(results):
    return results[1]["numbers"]


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_every_refused_request_is_refused_before_the_bench(results):
    """Claim 'refusals': four requests, four refusals, no device call."""
    table = rows(results, "refusals")
    assert [r[1] for r in table] == ["refused"] * 4
    assert "interlock circuit-confirmed is open" in table[0][2]
    assert "outside the permitted range" in table[1][2]
    assert "outside the permitted range" in table[2][2]
    assert "halted" in table[3][2]
    assert numbers(results)["calls-reaching-bench"] == "0"


def test_the_lossy_measurement_is_refused_retried_and_never_fitted(results):
    table = {r[0]: r for r in rows(results, "campaign-measurements")}
    found = numbers(results)
    refused, retry = table[found["invalid-id"]], table[found["retry-id"]]
    assert found["invalid"] == "1"
    assert refused[5].startswith("refused:") and "lost" in refused[5]
    assert retry[2] == "retry" and retry[4] == found["invalid-id"]
    assert retry[3] == refused[3]  # the same frequency, measured again
    # The page: "Measurement {invalid-id}, a refinement, was refused".
    assert refused[1] == "frequency-response" and refused[2] == "refine"
    # The next refinement follows from the retry, never from the refused one.
    ordered = rows(results, "campaign-measurements")
    later = [r for r in ordered if r[2] == "refine"]
    assert all(found["invalid-id"] not in r[4] for r in later if r[0] != refused[0])
    after_retry = ordered[[r[0] for r in ordered].index(found["retry-id"]) + 1 :]
    following = next(r for r in after_retry if r[2] == "refine")
    assert found["retry-id"] in following[4].split(", ")
    # Twelve valid frequency-response points of thirteen were fitted.
    frequency = [r for r in table.values() if r[1] == "frequency-response"]
    assert int(found["valid-points"]) == len(frequency) - 1
    assert found["segment-status"] == "complete"
    assert int(found["refinements"]) >= 2
    assert "loses" in found["link"]


def test_both_protocols_pass_the_simulator_check_and_agree(results):
    """Claim 'simulator-checks consistency'."""
    assert [r[7] for r in rows(results, "simulator-checks")] == ["passed"] * 2
    assert [r[4] for r in rows(results, "consistency")] == ["agree"] * 2
    assert float(numbers(results)["reduced-chi2"]) < 2.0
    # The page: "The ring-down gives the wider interval" (of f0, relative).
    width = {
        r[0]: float(r[2]) / float(r[1].replace(",", ""))
        for r in rows(results, "simulator-checks")
    }
    assert width["ring-down"] > width["frequency response"]


def test_the_led_pair_recovers_its_diodes_and_its_held_out_prediction(results):
    """Claim 'led-characteristic fig-amplitude-response'."""
    found = numbers(results)
    assert found["led-check"] == "passed"
    assert found["held-out-verdict"] == "agree"
    assert float(found["held-out-worst"]) <= 2.0
    n, v_ref = rows(results, "led-characteristic")
    assert abs(float(n[1]) / float(n[3]) - 1) <= 0.05
    assert abs(float(v_ref[1]) - float(v_ref[3])) <= 0.01


def test_the_routes_need_the_same_count_at_the_common_width(results):
    """Claim 'routes fig-routes', and the second exercise."""
    table = {r[0]: r for r in rows(results, "routes")}
    assert set(table) == {"agent", "adaptive", "scripted"}
    assert len({r[4] for r in table.values()}) == 1
    assert "placeholder" in numbers(results)["agent-answer"].lower()
    needed = dict(rows(results, "needed-for-target"))
    assert needed["scripted"].startswith("never")
    assert int(needed["agent"]) < int(needed["adaptive"])  # the self-check


def test_a_mismatched_circuit_fails_the_closed_form_and_the_protocols_agree(
    results,
):
    """Claim 'mismatch-checks mismatch-consistency'."""
    assert [r[7] for r in rows(results, "mismatch-checks")] == ["failed"] * 2
    assert [r[4] for r in rows(results, "mismatch-consistency")] == ["agree"] * 2
    actual = float(numbers(results)["actual-f0"].replace(",", ""))
    for row in rows(results, "mismatch-checks"):
        assert abs(float(row[1].replace(",", "")) / actual - 1) < 0.01


def test_the_pilot_record_is_replayed_and_fails_the_nominal_closed_form(results):
    """Claim 'pilot fig-pilot-discrepancy ad3-rlc-pilot': the dataset's own
    numbers (docs/datasets/ad3-rlc-pilot.md: f0 about 47.0 kHz, Q about 1.55
    against 50.3 kHz and 3.16 of the labels)."""
    found = numbers(results)
    assert found["pilot-mode"] == "recorded"
    assert found["pilot-check"] == "failed"
    assert found["pilot-points"] == "19"
    f0, q = rows(results, "pilot")
    assert 46_900 < float(f0[1].replace(",", "")) < 47_100
    assert 1.5 < float(q[1]) < 1.6
    assert float(found["pilot-f0-error"]) > 5 and float(found["pilot-q-error"]) > 40


@pytest.mark.parametrize("label", sorted(dataset_figures(PAGE)))
def test_the_pilot_figure_is_processed_measurement_by_the_conventions(
    experiment, label
):
    assert dataset_figures(PAGE)[label]["fig-status"] == "processed"
    assert_cell_declared(experiment, PAGE, label, residuals=True)


def test_only_the_pilot_figure_names_a_dataset(experiment):
    assert set(dataset_figures(PAGE)) == {"fig-pilot-discrepancy"}
    assert experiment.provenance == {"fig-pilot-discrepancy": lab.PILOT_FIGURE}


def test_no_printed_output_is_a_block_of_numbers(experiment):
    for name, text in experiment.outputs.items():
        assert not is_numeric_console_block(text), name


def test_the_figures_leave_room_in_the_payload_budget_of_the_page(results):
    directory, _ = results
    total = sum(p.stat().st_size for p in directory.glob("fig-*.png"))
    assert total < 750_000, total
