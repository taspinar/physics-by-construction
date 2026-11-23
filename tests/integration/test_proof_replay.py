"""The search of "A proof an agent proposed" is verified by replay: no
network, no credential, and the verdicts the build computes (Issue #609,
ADR 004)."""

import re
import socket
from pathlib import Path

import pytest

from pbc.agents import load_recording
from pbc.agents.proof_lab import HUNTS, replay_hunt

ROOT = Path(__file__).parents[2]
LESSON = ROOT / "site" / "lessons" / "lean" / "06-a-proof-an-agent-proposed"
CREDENTIAL = re.compile(
    r"sk-[A-Za-z0-9_-]{10,}|Bearer\s+\S+|api[_-]?key", re.IGNORECASE
)


@pytest.mark.parametrize("name", sorted(HUNTS))
def test_the_hunts_replay_with_no_network_and_no_credential(name, monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("the replay opened a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    for variable in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(variable, raising=False)
    _, transcript, verdict = replay_hunt(name, LESSON)
    assert transcript.finished
    expected = {"any": "counterexample", "unit": "inconclusive"}[name]
    assert verdict.outcome == expected


def test_the_inconclusive_hunt_spent_its_budget_inside_the_domain():
    _, _, verdict = replay_hunt("unit", LESSON)
    assert verdict.tested == HUNTS["unit"].claim.budget


@pytest.mark.parametrize("name", sorted(HUNTS))
def test_the_fixtures_hold_no_credential_and_are_not_placeholders(name):
    path = LESSON / HUNTS[name].fixture
    assert not CREDENTIAL.search(path.read_text())
    recording = load_recording(path)
    assert recording.model.strip()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", recording.recorded)
    assert not recording.placeholder


def test_the_lesson_holds_only_the_page_and_its_two_fixtures():
    kept = {p.name for p in LESSON.iterdir() if p.name != "index_files"}
    fixtures = {hunt.fixture for hunt in HUNTS.values()}
    assert kept - {"index.html"} == {"index.qmd", *fixtures}
