"""The panel of lesson AE6 in ``pbc.agents.review_lab``: eight controlled
cases with known truth, the reviewers' tools over them, decisions read from
``decide`` calls, and the frozen sessions. AI4's pieces and reviewers are
untouched (``tests/unit/test_review_lab.py``)."""

import ast
import json
from pathlib import Path

import pytest

from pbc.agents import ModelMessage, ToolCall, run
from pbc.agents.replay import ReplayMismatch
from pbc.agents.review_lab import (
    CANDIDATES,
    CASES,
    PANEL,
    PANEL_MAX_STEPS,
    PANEL_SESSIONS,
    REVIEWERS,
    Case,
    decisions,
    panel_allowlist,
    replay_panel,
    verdicts,
)
from pbc.verification import checks
from pbc.verification.faulty import CORRECT, GALLERY, explicit_euler_as_symplectic

ROOT = Path(__file__).parents[2]
DIRECTORY = ROOT / "site/lessons/agents-llm/24-failure-analysis-and-reviewer-evaluation"


class Scripted:
    model = "scripted"
    secrets = ()

    def __init__(self, *messages):
        self.messages = list(messages)

    def complete(self, system, conversation, tools):
        return self.messages.pop(0)


def call(name, **arguments):
    return ToolCall("c", name, arguments)


def test_the_cases_are_three_correct_methods_and_five_faulty_ones_of_the_gallery():
    correct = {name for name, _, _ in CORRECT}
    faulty = {f.name for f in GALLERY}
    assert sorted(CASES) == list(range(1, 9))
    assert {c.name for c in CASES.values() if not c.faulty} == correct
    assert {c.name for c in CASES.values() if c.faulty} <= faulty
    assert sum(c.faulty for c in CASES.values()) == 5


def test_each_case_carries_the_claim_of_the_method_it_is_or_poses_as():
    claims = {name: claim for name, _, claim in CORRECT}
    claims |= {f.name: f.claim for f in GALLERY}
    for case in CASES.values():
        assert case.claim == claims[case.name]


def test_no_prompt_task_or_tool_says_which_piece_is_faulty():
    for reviewer in PANEL:
        text = (reviewer.system + reviewer.task).lower()
        text += " ".join(t.description.lower() for t in reviewer.allowlist.tools)
        for case in CASES.values():
            assert case.name.lower() not in text
        for word in ("faulty", "wrong", "fault"):
            assert word not in text


def test_the_panel_roles_have_the_checks_of_ai4s_roles_and_decide():
    for panel, ai4 in zip(PANEL, REVIEWERS[:2], strict=True):
        assert panel.id == ai4.id
        assert {t.name for t in panel.allowlist.tools} == {
            t.name for t in ai4.allowlist.tools
        } | {"decide"}


def test_a_check_tool_checks_each_case_against_its_own_claim():
    tools = panel_allowlist("numerics")
    for number, case in CASES.items():
        result = tools.dispatch(call("check_convergence_order", candidate=number))
        finding = checks.check_convergence_order(case.build, case.claim)
        assert result.content["passed"] == float(finding.passed)


def test_the_bounded_energy_check_fails_on_the_correct_rk4_which_does_not_claim_it():
    rk4 = next(n for n, c in CASES.items() if c.name == "Runge-Kutta 4")
    assert not CASES[rk4].claim.bounded_energy
    result = panel_allowlist("physics").dispatch(
        call("check_bounded_energy", candidate=rk4)
    )
    assert result.content["passed"] == 0.0
    # The contract does not run it on a method that does not claim it.
    found = checks.verify(CASES[rk4].build, CASES[rk4].claim)
    assert all(f.passed for f in found)


@pytest.mark.parametrize(
    "arguments", [{"candidate": 9, "accept": 1}, {"candidate": 1, "accept": 2}]
)
def test_decide_refuses_a_piece_or_a_decision_out_of_bounds(arguments):
    assert not panel_allowlist("physics").dispatch(call("decide", **arguments)).ok


def test_a_decision_comes_from_decide_and_the_last_one_counts():
    reviewer = PANEL[0]
    transcript = run(
        Scripted(
            ModelMessage(
                "I accept piece 2. Piece 3 is perfect.",
                (
                    call("decide", candidate=2, accept=1),
                    call("decide", candidate=2, accept=0),
                    call("decide", candidate=9, accept=1),
                    call("check_limits", candidate=3),
                ),
            ),
            ModelMessage("done"),
        ),
        reviewer.allowlist,
        reviewer.system,
        reviewer.task,
        PANEL_MAX_STEPS,
    )
    assert decisions(transcript) == {2: False}
    # A decision is no verdict, and a check is no decision.
    assert [(v.candidate, v.check) for v in verdicts(reviewer, transcript)] == [
        (3, "limits")
    ]


@pytest.mark.parametrize("session", PANEL_SESSIONS, ids=lambda s: s.name)
def test_every_session_replays_decides_every_piece_and_records_its_cost(session):
    _recording, transcript = replay_panel(session, DIRECTORY)
    assert transcript.finished
    assert set(decisions(transcript)) == set(CASES)
    data = json.loads((DIRECTORY / session.fixture).read_text())
    assert session.model_messages == len(data["steps"]) == len(transcript.steps)
    assert session.tool_calls == sum(len(s["tool_calls"]) for s in data["steps"])
    # Every check of the role on every piece was run at least once.
    checks_of_role = {t.name for t in session.reviewer.allowlist.tools} - {"decide"}
    ran = {(v.candidate, v.check) for v in verdicts(session.reviewer, transcript)}
    assert len(ran) == len(CASES) * len(checks_of_role)


def test_a_changed_piece_breaks_the_replay_of_the_frozen_session():
    changed = dict(CASES)
    changed[2] = Case(
        CASES[2].name, lambda: explicit_euler_as_symplectic, CASES[2].claim, False
    )
    session = next(s for s in PANEL_SESSIONS if s.role == "numerics")
    with pytest.raises(ReplayMismatch, match="check_convergence_order"):
        replay_panel(session, DIRECTORY, changed)


def test_ai4s_names_are_unchanged_by_the_panel():
    assert sorted(CANDIDATES) == [1, 2]
    assert [r.id for r in REVIEWERS] == ["physics", "numerics", "evidence"]
    source = (ROOT / "src/pbc/agents/review_lab.py").read_text()
    tree = ast.parse(source)
    names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef | ast.ClassDef)}
    assert {"verdicts", "resolve", "ReviewDisplay", "replay_fixtures"} <= names
