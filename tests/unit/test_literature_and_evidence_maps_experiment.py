"""The experiment of "Literature, novelty assessment, and evidence maps"
(mechanics 24, RR3 of Issue #585): the labels against the annotations, the
retrieval's ranks and recall, the review log, and the statement about the
slow throw (acceptance criterion 2)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

from pbc.mechanics.experiments import literature_and_evidence_maps as lab
from pbc.research.corpus import CONTRADICTS, INSUFFICIENT, PASSAGES, SUPPORTS

MODULE = "pbc.mechanics.experiments.literature_and_evidence_maps"
PAGE = "mechanics/24-literature-and-evidence-maps"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("literature")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_every_computed_label_is_the_annotated_label():
    agreed, pairs = lab.agreement()
    assert agreed == pairs == len(PASSAGES) * 3


def test_the_replication_is_supported_by_the_specification_lesson_only():
    rows = lab.labels_of(lab.statement("replication"))
    supporting = {key for key, computed, _, _ in rows if computed == SUPPORTS}
    assert supporting == {"sa1-bracket", "sa1-exercise"}
    assert {computed for _, computed, _, _ in rows} == {SUPPORTS, INSUFFICIENT}
    without_air = next(row for row in rows if row[0] == "sa5-without-air")
    assert without_air[1:3] == (INSUFFICIENT, "the passage assumes drag: none")


def test_the_scaling_guess_is_contradicted_and_the_no_drag_passages_do_not_decide_it():
    rows = lab.labels_of(lab.statement("no-change"))
    contradicting = {key for key, computed, _, _ in rows if computed == CONTRADICTS}
    assert len(contradicting) == 6
    assert {p.lesson for p in PASSAGES if p.key in contradicting} == {
        "experiment-specification",
        "projectile-with-drag",
        "agent-experiment",
        "automated-analysis-pipelines",
    }
    for key in ("sa5-without-air", "m3-formula"):
        assert next(r for r in rows if r[0] == key)[1] == INSUFFICIENT


def test_the_retrieval_finds_the_replications_passages_and_misses_the_guesss():
    replication, slow, no_change = (
        lab.statement(k) for k in ("replication", "slow-throw", "no-change")
    )
    assert lab.recall(replication, lab.retrieve(replication.text, PASSAGES), 3) == 1.0
    ranked = lab.retrieve(no_change.text, PASSAGES)
    assert ranked[0][0] == "m1-rose-less"
    assert lab.recall(no_change, ranked, 3) == pytest.approx(1 / 6)
    assert lab.recall(slow, lab.retrieve(slow.text, PASSAGES), 3) is None
    rewritten = lab.retrieve(lab.REWRITTEN, PASSAGES)
    assert lab.recall(no_change, rewritten, 3) == pytest.approx(2 / 6)


def test_the_slow_throw_is_not_found_and_never_called_new():
    rows = [row for row in lab.evidence_map() if row[0] == "slow-throw"]
    assert rows == [
        (
            "slow-throw",
            "none",
            "",
            "",
            f"not found in this corpus of {len(PASSAGES)} passages",
            "",
        )
    ]
    ratio = next(p for p in PASSAGES if p.key == "m3-ratio")
    computed, reason = lab.label(lab.statement("slow-throw"), ratio.reading)
    assert (computed, reason) == (INSUFFICIENT, "its bound does not decide the claim's")


def test_every_deciding_passage_links_its_drag_assumption_to_the_register():
    rows = [row for row in lab.evidence_map() if row[1] != "none"]
    assert rows and all(row[5] == "drag-coefficient-regimes" for row in rows)


def test_the_exercise_labels():
    assert {key for key, computed, _ in lab.exercise_labels()} == {
        "sa1-vacuum",
        "m3-formula",
        "sa5-without-air",
    }
    assert {computed for _, computed, _ in lab.exercise_labels()} == {SUPPORTS}
