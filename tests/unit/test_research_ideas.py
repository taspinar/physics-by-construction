"""The checks of a candidate research question, the rule that selects one,
and the archive (``pbc.research.ideas``, RR1, Issue #585)."""

import copy
import dataclasses

import pytest

from pbc.agents.specification import execute, parse
from pbc.mechanics.experiments.experiment_specification import (
    SPECIFICATION,
    laboratory,
)
from pbc.research.ideas import (
    BY_FORMULA,
    EXTENSION,
    REPLICATION,
    SELECTED,
    Answered,
    Archive,
    Idea,
    Judgement,
    assess,
    falsifiable,
    runs_needed,
    select,
    verify_archive,
)

ANSWERED = (
    Answered("range_with_drag", {"speed": 25.0}, "SA1"),
    Answered("range_in_vacuum", {}, "the formula", by_formula=True),
)
RATINGS = {"feasibility": 3, "interest": 3, "novelty": 3}


def idea(key: str, draft, ratings=RATINGS) -> Idea:
    return Idea(key, f"question {key}", "someone", draft, ratings)


def at(speed: float, **changes) -> dict:
    draft = copy.deepcopy(SPECIFICATION)
    draft["variables"]["speed"]["value"] = speed
    for path, value in changes.items():
        part, key = path.split("__")
        draft[part][key] = value
    return draft


@pytest.mark.parametrize(
    ("resolution", "max_runs"), [(1.0, 40), (0.5, 40), (0.25, 60), (2.5, 30)]
)
def test_the_count_of_runs_is_the_count_the_route_makes(resolution, max_runs):
    draft = copy.deepcopy(SPECIFICATION)
    draft["success"]["resolution"]["value"] = resolution
    draft["stopping"]["max_runs"] = max_runs
    lab = laboratory()
    specification = parse(draft, lab)
    assert runs_needed(specification) == len(execute(specification, lab).runs)


def test_a_bound_at_the_end_of_the_range_cannot_be_contradicted():
    lab = laboratory()
    draft = copy.deepcopy(SPECIFICATION)
    assert falsifiable(parse(draft, lab))
    draft["hypothesis"]["prediction"]["value"] = 60.0  # the upper end
    assert not falsifiable(parse(draft, lab))
    draft["hypothesis"]["prediction"]["value"] = 59.5  # within a resolution
    assert not falsifiable(parse(draft, lab))
    draft["hypothesis"]["prediction"]["value"] = 59.0  # exactly a resolution in
    assert falsifiable(parse(draft, lab))


def test_an_idea_the_laboratory_cannot_run_is_not_assessed_further():
    lab = laboratory()
    without = assess(idea("none", None), lab, ANSWERED)
    assert not without.feasible and without.falsifiable is None
    assert without.runs is None and without.contribution is None
    draft = at(25.0)
    draft["actions"] = ["range_with_spin"]
    refused = assess(idea("spin", draft), lab, ANSWERED)
    assert not refused.feasible
    assert any("range_with_spin" in problem for problem in refused.problems)
    assert not refused.passed


def test_the_contribution_is_read_from_the_archive_of_answered_questions():
    lab = laboratory()
    assert assess(idea("a", at(25.0)), lab, ANSWERED).contribution == REPLICATION
    assert assess(idea("b", at(10.0)), lab, ANSWERED).contribution == EXTENSION
    vacuum = at(10.0)
    vacuum["actions"] = ["range_in_vacuum"]
    assert assess(idea("c", vacuum), lab, ANSWERED).contribution == BY_FORMULA


def test_a_budget_smaller_than_the_route_needs_fails_the_check():
    lab = laboratory()
    draft = at(10.0)
    draft["stopping"]["max_runs"] = 12
    found = assess(idea("short", draft), lab, ANSWERED)
    assert found.feasible and found.falsifiable
    assert found.runs == 20 and not found.within_budget and not found.passed


def test_the_rule_prefers_an_extension_then_fewer_runs_then_interest():
    lab = laboratory()
    finer = at(15.0)
    finer["success"]["resolution"]["value"] = 0.5
    found = {
        "replication": assess(idea("replication", at(25.0)), lab, ANSWERED),
        "slow": assess(idea("slow", at(10.0)), lab, ANSWERED),
        "medium": assess(idea("medium", at(15.0)), lab, ANSWERED),
        "finer": assess(idea("finer", finer), lab, ANSWERED),
    }
    assert select(found, {}) in ("medium", "slow")  # fewer runs than "finer"
    judged = {"medium": Judgement("high", "a", "r"), "slow": Judgement("low", "a", "r")}
    assert select(found, judged) == "medium"
    assert select({"replication": found["replication"]}, {}) == "replication"
    assert select({}, {}) is None


def test_no_self_rating_changes_the_selection():
    lab = laboratory()
    ideas = [idea(k, at(v)) for k, v in (("a", 25.0), ("b", 10.0), ("c", 15.0))]
    judged = {"b": Judgement("high", "a", "r")}
    chosen = select({i.key: assess(i, lab, ANSWERED) for i in ideas}, judged)
    for ratings in ({"feasibility": 1}, {"feasibility": 5, "novelty": 5}):
        rated = [dataclasses.replace(i, self_ratings=ratings) for i in ideas]
        found = {i.key: assess(i, lab, ANSWERED) for i in rated}
        assert select(found, judged) == chosen == "b"


def test_the_archive_finds_an_edited_a_removed_and_a_reordered_entry():
    kept = Archive()
    for key, speed in (("a", 25.0), ("b", 10.0), ("c", 15.0)):
        kept.add(idea(key, at(speed)), SELECTED, "the reason", "")
    assert verify_archive(kept.entries) == []
    edited = list(kept.entries)
    edited[0] = dataclasses.replace(
        edited[0], idea=dataclasses.replace(edited[0].idea, question="changed")
    )
    assert verify_archive(edited) == ["entry 1: the idea changed after it was archived"]
    removed = [kept.entries[0], kept.entries[2]]
    assert "entry 3: the chain to the entry before is broken" in verify_archive(removed)
    reordered = [kept.entries[1], kept.entries[0], kept.entries[2]]
    assert verify_archive(reordered)
    changed = list(kept.entries)
    changed[1] = dataclasses.replace(changed[1], decision="rejected")
    assert "entry 2: its digest does not match its content" in verify_archive(changed)


def test_a_decision_needs_its_reason_and_a_known_name():
    kept = Archive()
    with pytest.raises(ValueError, match="reason"):
        kept.add(idea("a", at(25.0)), SELECTED, " ", "")
    with pytest.raises(ValueError, match="unknown decision"):
        kept.add(idea("a", at(25.0)), "maybe", "a reason", "")
