"""The experiment of "Independently checkable reports and research memory"
(mechanics 26, RR7 of Issue #594): every number and citation of the report
resolves to a record or a verified passage or is marked (acceptance
criterion 3), the report's evidence status of the review follows the log and
not a revision of the prose (criterion 2), the bundle reproduces, and the
memory checks each reuse."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

from pbc.evidence.report import MARKED
from pbc.mechanics.experiments import checkable_reports_and_research_memory as lab
from pbc.mechanics.experiments import discrepancies_and_follow_up_experiments as rr6
from pbc.research.report import (
    CODE_CHANGED,
    PASSAGE,
    RECORD,
    REFUSED,
    REPRODUCED,
    bundle,
    problems,
    reproduce,
)

MODULE = "pbc.mechanics.experiments.checkable_reports_and_research_memory"
PAGE = "mechanics/26-checkable-reports-and-research-memory"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("report")
    return directory, run_entry_point(MODULE, directory)


@pytest.fixture(scope="module")
def made():
    recipes = lab.recipes()
    entries = bundle(recipes)
    return recipes, entries, lab.records(entries)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_every_number_and_citation_of_the_report_resolves_or_is_marked(made):
    # Criterion 3.
    _, _, fields = made
    resolutions = lab.check(lab.REPORT, fields)
    assert problems(resolutions) == []
    assert {r.kind for r in resolutions} == {RECORD, PASSAGE, MARKED}
    marked = [s.key for s in lab.REPORT if s.marked]
    assert [r.sentence for r in resolutions if r.kind == MARKED] == marked
    # Every sentence that is not marked has at least one number or citation.
    checked = {r.sentence for r in resolutions if r.kind in (RECORD, PASSAGE)}
    assert checked == {s.key for s in lab.REPORT if not s.marked}


def test_the_planted_errors_are_each_refused_and_nothing_else(made):
    _, _, fields = made
    refused = problems(lab.check(lab.planted(), fields))
    assert [(r.sentence, r.token) for r in refused] == [
        ("plan", "43.57"),
        ("literature", "m3-ratio"),
        ("method", "20"),
    ]


def test_the_reports_evidence_status_follows_the_log_not_the_prose(made):
    # Criterion 2, on the report: its sentence on the review is refused
    # against a log in which the claim was revised in prose alone.
    _, _, fields = made
    review = [s for s in lab.REPORT if s.key == "review"]
    assert problems(lab.check(review, fields)) == []
    alone = {**fields, "review": lab.review_record(rr6.prose_only())}
    refused = problems(lab.check(review, alone))
    assert [r.to for r in refused] == ["the record gives 0", "the record gives 3"]
    assert alone["review"]["resolved"] == 0


def test_the_bundle_reproduces_and_an_edit_is_found(made):
    recipes, entries, _ = made
    assert set(reproduce(entries, recipes).values()) == {REPRODUCED}
    edited = {lab.EDITED: lab.EDITED.read_bytes() + b"\n# edited\n"}
    after = reproduce(entries, recipes, edited)
    for name, recipe in recipes.items():
        expected = CODE_CHANGED if lab.EDITED in recipe.code else REPRODUCED
        assert after[name] == expected


def test_the_reuses_of_the_memory(results):
    rows = results[1]["tables"]["reuses"]["rows"]
    assert [row[2] for row in rows] == [
        "handed over",
        "refused",
        "refused",
        "handed over",
        "handed over",
    ]
    assert "simulated-only" in rows[0][3] and "measured-throw" in rows[0][3]
    assert "configuration differs" in rows[1][3]
    assert "code differs" in rows[2][3]


def test_the_exercises(made):
    _, _, fields = made
    assert [r.kind for r in lab.check((lab.ROUNDED,), fields)] == [RECORD, RECORD]
    memory = lab.memory(lab.recipes())
    assert lab.bare_result(memory).endswith("a result is kept with its limitations")
    assert REFUSED not in {r.kind for r in lab.check((lab.ROUNDED,), fields)}


@pytest.mark.parametrize(
    "lesson", [PAGE, "mechanics/25-discrepancies-and-follow-up-experiments"]
)
def test_the_lesson_has_an_input_digest(lesson):
    # The code files a record names are path constants the digest can follow;
    # without a digest every run with a base would be a full run.
    from support.paths import REPO_ROOT

    from pbc.authoring.digest import Digester

    found = Digester().digest(REPO_ROOT / "site" / "lessons" / lesson)
    assert found.value is not None, found.reason
