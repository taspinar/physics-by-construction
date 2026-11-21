"""The experiment of "Three reviewers" (agents-llm 03)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.mechanics.experiments.scientific_review"
PAGE = "agents-llm/03-three-reviewers"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("scientific_review")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_faulty_piece_gains_energy(results):
    _, found = results

    assert float(found["numbers"]["growth"]) > 1.0


def test_a_boasting_reviewer_is_judged_by_what_it_ran(results):
    _, found = results

    assert "FAILED" in found["outputs"]["boasting-reviewer"]


def test_only_the_faulty_piece_fails_a_check(results):
    _, found = results
    lines = found["outputs"]["every-check"].splitlines()

    assert all("FAIL" not in line for line in lines if line.startswith("piece 1"))
    assert any("FAIL" in line for line in lines if line.startswith("piece 2"))


def test_the_implementer_cannot_read_the_verdicts(results):
    _, found = results

    assert found["outputs"]["implementer-reads-the-verdicts"].startswith("refused:")


def test_the_human_step_refuses_piece_two_and_sends_it_back(results):
    _, found = results
    lines = found["outputs"]["human-step"].splitlines()

    assert lines[0].startswith("refused: piece 2 cannot be accepted")
    assert lines[1].startswith("piece 1: accepted")
    assert lines[2].startswith("piece 2: sent back")


def test_the_vote_differs_from_the_recomputed_checks_on_the_replayed_panel(results):
    _, found = results
    rows = found["tables"]["vote-against-checks"]["rows"]

    assert all(cell.endswith("tie") for cell in rows[0][1:4])
    assert all(row[4] == "reject" for row in rows)
    assert int(found["numbers"]["wrong-majorities"]) > 0


def test_the_narrowed_claim_keeps_the_failed_check_in_the_record(results):
    _, found = results
    text = found["outputs"]["narrowed-claim"]

    assert "accepted for the claim 'first order only'" in text
    assert "['bounded-energy']" in text


def test_the_diagram_draws_every_role_of_the_interfaces():
    import matplotlib.pyplot as plt

    from pbc.agents.investigation import INTERFACES
    from pbc.mechanics.experiments.scientific_review import draw_investigation_roles

    figure = draw_investigation_roles()
    try:
        drawn = " ".join(t.get_text() for t in figure.axes[0].texts)
    finally:
        plt.close(figure)
    for item in INTERFACES:
        assert item.role in drawn
