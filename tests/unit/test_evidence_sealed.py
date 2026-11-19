"""The withheld final evaluation of lesson AE4 (``pbc.evidence.sealed``): the
selection reads development evaluations only, the frozen candidate is
scored once on a split no development evaluation used, and the binding
rules of the ledger hold for it. Fixtures are copied before a test changes
them."""

import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from pbc.discovery import force_lab
from pbc.evidence import COMPLETED, ContractError, Ledger, check, sealed, summary
from pbc.evidence.sealed import (
    CANDIDATES,
    EVALUATOR,
    FINAL_EVALUATOR,
    SEALED,
    develop,
    final_on_sealed,
    fixture,
    freeze,
    run_record,
    run_sealed,
    select,
)


@pytest.fixture
def root(tmp_path) -> Path:
    for candidate in CANDIDATES:
        target = fixture(candidate, tmp_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fixture(candidate), target)
    return tmp_path


def test_the_sealed_split_is_new_later_and_inside_the_probed_amplitudes():
    development = force_lab.PROTOCOLS["prior-knowledge"].held_out_settings()
    world = sealed.PROTOCOL.make(0)
    amplitude, time = world.controls
    assert not {tuple(sorted(s.items())) for s in SEALED} & {
        tuple(sorted(s.items())) for s in development
    }
    assert min(s["time"] for s in SEALED) > max(s["time"] for s in development)
    assert all(amplitude.low <= s["amplitude"] <= amplitude.high for s in SEALED)
    assert all(s["time"] > time.high for s in SEALED)


def test_the_configuration_digest_covers_the_sealed_split(monkeypatch):
    before = run_record().configuration
    monkeypatch.setattr(sealed, "SEALED", ({"amplitude": 1.0, "time": 14.0},))
    assert run_record().configuration != before


def test_the_selected_candidate_is_the_best_in_development_and_is_scored_once():
    ledger = run_sealed()
    s = summary(ledger, sealed.ROOT)
    assert [(r.candidate, r.correct) for r in s.rows] == [
        ("told the form", True),
        ("told the names", False),
        ("told nothing", False),
    ]
    (final,) = ledger.finals
    assert final.candidate == "told the form"
    assert final.evaluation.evaluator == FINAL_EVALUATOR
    assert (final.status, final.evaluation.correct) == (COMPLETED, True)
    # The page's claim: worse on the sealed split than in development,
    # still within the tolerance.
    development = next(
        e for e in ledger.evaluations if e.attempt == "development-1"
    ).metrics["held_out_error"]
    error = final.evaluation.metrics["held_out_error"]
    assert development < error <= sealed.PROTOCOL.tolerance
    assert f"{development:.3f}" == "0.017" and f"{error:.3f}" == "0.023"
    # Only the frozen candidate's claim was ever scored on the sealed split.
    assert [e.evaluator for e in ledger.evaluations] == [EVALUATOR] * 3


def test_selection_ignores_any_evaluation_but_the_development_one(root):
    ledger = Ledger(run_record())
    develop(ledger, root)
    assert select(ledger) == "told the form"
    # A better score from another evaluator, on the run told nothing, does
    # not take part in the selection.
    other = replace(
        ledger.evaluations[2],
        evaluator="a peek at another split",
        correct=True,
        metrics={"held_out_error": 0.0, "tolerance": 0.05},
    )
    ledger.add_evaluation(other)
    assert select(ledger) == "told the form"


def test_no_correct_candidate_is_no_selection():
    ledger = Ledger(run_record())
    with pytest.raises(ContractError, match="no candidate"):
        select(ledger)


def test_a_second_sealed_evaluation_and_one_of_a_changed_candidate_are_refused(root):
    ledger = run_sealed(root)
    with pytest.raises(ContractError, match="already had its final evaluation"):
        final_on_sealed(ledger, "told the form", root)
    other = Ledger(run_record())
    develop(other, root)
    freeze(other, "told the form", "1", root)
    path = fixture("told the form", root)
    data = json.loads(path.read_text())
    data["steps"][-1]["text"] = "tuned"
    path.write_text(json.dumps(data))
    with pytest.raises(ContractError, match="changed after it was frozen"):
        final_on_sealed(other, "told the form", root)
    # The first ledger shows the change as invalidations, the final included.
    assert any(i.final for i in check(ledger, root))


def test_a_missing_fixture_is_a_missing_attempt(root):
    fixture("told nothing", root).unlink()
    ledger = Ledger(run_record())
    develop(ledger, root)
    statuses = {a.candidate: a.status for a in ledger.attempts}
    assert statuses["told nothing"] == "missing"
    assert len(ledger.evaluations) == 2


def test_the_page_never_names_a_held_out_or_sealed_time():
    lesson = "22-independent-scoring-and-sealed-evaluation"
    page = (sealed.ROOT / "site/lessons/agents-llm" / lesson / "index.qmd").read_text()
    for setting in (*SEALED, *sealed.PROTOCOL.held_out_settings()):
        assert f"{setting['time']:g} s" not in page
