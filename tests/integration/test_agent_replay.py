"""The agent lesson A1 is verified by replay: no network, no credential, and
no LLM secret anywhere in CI (ADR 004)."""

import re
import socket
from pathlib import Path

import pytest

from pbc.agents import load_recording
from pbc.agents.projectile_lab import RECORD_COMMAND, REPLAY_FILE, replay_fixture

ROOT = Path(__file__).parents[2]
LESSON = ROOT / "site" / "lessons" / "agents-llm" / "01-an-agent-runs-an-experiment"
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.y*ml"))
CREDENTIAL = re.compile(
    r"sk-[A-Za-z0-9_-]{10,}|Bearer\s+\S+|api[_-]?key", re.IGNORECASE
)
LLM_SECRET = re.compile(r"OPENAI|ANTHROPIC|LLM|API_KEY|GEMINI|MISTRAL", re.IGNORECASE)


def test_the_lesson_replays_with_no_network_and_no_credential(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("the replay opened a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    recording, transcript = replay_fixture(LESSON)
    assert transcript.steps
    assert all(
        result.ok or "error" in result.content
        for step in transcript.steps
        for result in step.results
    )
    assert recording.recorded


def test_the_fixture_contains_no_credential():
    text = (LESSON / REPLAY_FILE).read_text()
    # The system prompt may use the word "key" in prose; a key-shaped value or
    # a header may not appear at all.
    assert not CREDENTIAL.search(text)


def test_the_fixture_names_the_model_and_the_date():
    recording = load_recording(LESSON / REPLAY_FILE)
    assert recording.model.strip()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", recording.recorded)


def test_the_published_fixture_is_a_recorded_run_not_a_placeholder():
    """Acceptance criterion 8 of Issue #24: the committed fixture comes from
    the maintainer's live run. A hand-written stand-in may be used while
    developing, but it must not be published."""
    recording = load_recording(LESSON / REPLAY_FILE)
    how = f" Record a live run with: {RECORD_COMMAND}"
    assert not recording.placeholder, "the fixture is a placeholder." + how
    assert "placeholder" not in recording.model.lower(), (
        "the fixture names no model." + how
    )


def test_the_replay_fixture_is_the_only_file_besides_the_page():
    # A preview or a render leaves ignored output next to the page.
    kept = {p.name for p in LESSON.iterdir() if p.name != "index_files"}
    assert kept - {"index.html"} == {"index.qmd", REPLAY_FILE}


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_no_workflow_references_an_llm_secret(workflow):
    text = workflow.read_text()
    assert "secrets." not in text.replace("secrets.GITHUB_TOKEN", "")
    assert not LLM_SECRET.search(text), f"{workflow.name} mentions an LLM credential"


def test_ci_installs_no_provider_package():
    """The optional extra is for learners; the site build and CI never use it."""
    for workflow in WORKFLOWS:
        assert "--extra openai" not in workflow.read_text()
        assert "--all-extras" not in workflow.read_text()
