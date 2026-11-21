"""The roles of an investigation, the human step, and checks instead of
votes (F153, lesson RR5)."""

from dataclasses import replace

import pytest

from pbc.agents import investigation as inv
from pbc.agents.review_lab import CASES, PANEL_DIRECTORY, replay_fixtures
from pbc.authoring.repository import REPOSITORY_ROOT

LESSON = REPOSITORY_ROOT / "site/lessons/agents-llm/03-three-reviewers"


@pytest.fixture(scope="module")
def transcripts():
    return {name: t for name, (_, t) in replay_fixtures(LESSON).items()}


@pytest.fixture
def board(transcripts):
    board = inv.Board()
    inv.extract(board, inv.EXTRACTION)
    inv.implement(board)
    inv.review(board, transcripts)
    return board


def test_every_role_writes_only_its_own_field_in_order(board):
    assert board.log == [
        ("extraction", "claim"),
        ("implementation", "pieces"),
        ("review", "verdicts"),
    ]
    for item in inv.INTERFACES:
        assert len(item.writes) == 1


def test_a_role_may_not_read_outside_its_interface(board):
    with pytest.raises(inv.OutOfBounds, match="implementation role may not read"):
        board.read("implementation", "verdicts")
    with pytest.raises(inv.OutOfBounds, match="extraction role may not read"):
        board.read("extraction", "pieces")


def test_a_role_may_not_write_outside_its_interface_or_twice(board):
    with pytest.raises(inv.OutOfBounds, match="review role may not write claim"):
        board.write("review", "claim", None)
    with pytest.raises(inv.OutOfBounds, match="human role may not write verdicts"):
        board.write("human", "verdicts", ())
    with pytest.raises(inv.OutOfBounds, match="already written"):
        board.write("implementation", "pieces", (1,))


def test_an_extraction_that_quotes_words_the_handover_lacks_is_refused():
    invented = replace(
        inv.EXTRACTION,
        quotes={**inv.EXTRACTION.quotes, "bounded_energy": "conserves energy"},
    )
    board = inv.Board()

    with pytest.raises(inv.OutOfBounds, match="which the handover does not say"):
        inv.extract(board, invented)
    assert "claim" not in board.fields


def test_an_extraction_of_another_claim_than_the_reviewed_one_is_refused():
    second = replace(inv.EXTRACTION, quotes={"order": "a first-order method"})
    second = replace(second, bounded_energy=False)

    with pytest.raises(inv.OutOfBounds, match="recorded reviewers were given"):
        inv.extract(inv.Board(), second)


def test_the_human_cannot_accept_a_piece_whose_applicable_check_failed(board):
    with pytest.raises(inv.OutOfBounds, match=r"failed \['bounded-energy'\]"):
        inv.steer(board, inv.Steering(inv.ACCEPT, 2, "it looks fine"))
    assert inv.decision(board, 2) == "open"


def test_no_steering_action_sets_the_result_of_a_check(board):
    with pytest.raises(inv.OutOfBounds, match="no action sets the result"):
        inv.steer(board, inv.Steering("pass check", 2, "overrule"))


def test_the_human_accepts_one_piece_and_sends_the_other_back(board):
    inv.steer(board, inv.Steering(inv.ACCEPT, 1, "every check passed"))
    inv.steer(board, inv.Steering(inv.SEND_BACK, 2, "bounded-energy failed"))

    assert inv.decision(board, 1).startswith("accepted for the claim")
    assert inv.decision(board, 2).startswith("sent back")
    assert board.log[-2:] == [("human", "steering"), ("human", "steering")]


def test_a_narrowed_claim_is_recorded_and_the_original_stays_failed(board):
    inv.steer(
        board,
        inv.Steering(inv.NARROW, 2, "a run of two periods", drop="bounded_energy"),
    )
    inv.steer(board, inv.Steering(inv.ACCEPT, 2, "first order only"))

    assert not inv.claim_of(board, 2).bounded_energy
    assert inv.claim_of(board, 1).bounded_energy
    assert any(
        v.candidate == 2 and v.check == "bounded-energy" and not v.passed
        for v in board.fields["verdicts"]
    )


def test_a_required_check_must_be_run_before_an_acceptance(board):
    lean = inv.Board()
    inv.extract(lean, inv.EXTRACTION)
    inv.implement(lean)
    lean.write(
        "review",
        "verdicts",
        tuple(v for v in board.fields["verdicts"] if v.check != "purity"),
    )
    inv.steer(lean, inv.Steering(inv.REQUIRE, 1, "state matters", check="purity"))

    with pytest.raises(inv.OutOfBounds, match=r"required and not run \['purity'\]"):
        inv.steer(lean, inv.Steering(inv.ACCEPT, 1, "every check passed"))


def test_the_steering_is_read_through_the_human_interface_only(board):
    inv.steer(board, inv.Steering(inv.SEND_BACK, 2, "bounded-energy failed"))

    assert inv.steering(board) == board.read("human", "steering")
    for role in ("extraction", "implementation", "review"):
        with pytest.raises(inv.OutOfBounds, match=f"{role} role may not read"):
            board.read(role, "steering")


def test_the_acceptance_gate_follows_the_contract_rule_applies(board, monkeypatch):
    assert inv.failed_checks(board, 2) == ["bounded-energy"]
    monkeypatch.setattr(inv, "applies", lambda check, case: False)

    assert inv.failed_checks(board, 2) == []


@pytest.fixture(scope="module")
def recorded_panel():
    return inv.panel(REPOSITORY_ROOT / PANEL_DIRECTORY)


TIES = (1, 4, 6)


def test_the_vote_of_the_four_recorded_sessions_ties_on_three_faulty_cases(
    recorded_panel,
):
    decided, _ = recorded_panel
    everyone = inv.panels()[0]

    tied = [n for n in CASES if inv.votes(decided, n, everyone)[2] == "tie"]
    assert tied == list(TIES)
    assert all(CASES[n].faulty for n in tied)


def test_a_panel_of_three_gives_a_majority_that_accepts_a_faulty_case(
    recorded_panel,
):
    decided, _ = recorded_panel

    for case in TIES:
        outcomes = [inv.votes(decided, case, p)[2] for p in inv.panels()[1:]]
        assert "accept" in outcomes


def test_the_recomputed_checks_reject_every_faulty_case_in_every_panel(
    recorded_panel,
):
    _, found = recorded_panel

    for panel in inv.panels():
        for case in TIES:
            assert inv.checked(found, case, panel) == "reject"
    assert inv.failing(found, 6) == ["bounded-energy"]


def test_case_six_of_the_panel_is_piece_two_of_this_lesson():
    from pbc.verification.faulty import explicit_euler_as_symplectic

    assert CASES[6].build() is explicit_euler_as_symplectic
