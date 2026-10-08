"""Recording and replaying: the replay recomputes and compares."""

import json
from dataclasses import replace

import pytest

from pbc.agents import (
    Allowlist,
    ModelMessage,
    Parameter,
    ReplayMismatch,
    Tool,
    ToolCall,
    load_recording,
    replay,
    run,
    save_recording,
)

SYSTEM, TASK = "system", "task"
RERECORD = "the-re-record-command"


def make_allowlist(factor=2.0):
    return Allowlist(
        (
            Tool(
                "scale",
                "multiplies",
                (Parameter("x", "a number", 0, 10),),
                lambda x: {"y": factor * x},
            ),
        )
    )


class Scripted:
    model = "scripted-model"
    secrets = ()

    def __init__(self):
        self.messages = [
            ModelMessage("try", (ToolCall("c1", "scale", {"x": 3}),)),
            ModelMessage("too big", (ToolCall("c2", "scale", {"x": 99}),)),
            ModelMessage("done"),
        ]

    def complete(self, *args):
        return self.messages.pop(0)


@pytest.fixture
def recording(tmp_path):
    transcript = run(Scripted(), make_allowlist(), SYSTEM, TASK, 5)
    path = tmp_path / "replay.json"
    save_recording(path, transcript, "2026-10-08")
    return load_recording(path)


def check(recording, allowlist, **changes):
    options = {
        "system": SYSTEM,
        "task": TASK,
        "tolerance": 1e-6,
        "max_steps": 5,
        "rerecord": RERECORD,
    }
    return replay(recording, allowlist, **(options | changes))


def test_recording_round_trips(recording):
    assert recording.model == "scripted-model"
    assert recording.recorded == "2026-10-08"
    assert [s.message.text for s in recording.steps] == ["try", "too big", "done"]
    assert recording.steps[0].results[0].content == {"y": 6.0}
    assert not recording.steps[1].results[0].ok


def test_replay_of_unchanged_code_passes_and_returns_recomputed_results(recording):
    transcript = check(recording, make_allowlist())
    assert transcript.finished
    assert transcript.model == "scripted-model"
    assert transcript.steps[0].results[0].content == {"y": 6.0}


def test_replay_recomputes_instead_of_trusting_the_fixture(recording):
    """A fixture whose recorded value is wrong does not reach the page."""
    forged = replace(
        recording,
        steps=(
            replace(
                recording.steps[0],
                results=(replace(recording.steps[0].results[0], content={"y": 7.0}),),
            ),
            *recording.steps[1:],
        ),
    )
    with pytest.raises(ReplayMismatch, match="step 1"):
        check(forged, make_allowlist())


def test_a_changed_result_beyond_tolerance_fails_and_says_how_to_rerecord(recording):
    with pytest.raises(ReplayMismatch) as info:
        check(recording, make_allowlist(factor=2.001))
    message = str(info.value)
    assert "step 1" in message
    assert "scale" in message
    assert "y was 6.0" in message
    assert RERECORD in message
    assert "record the run again" in message


def test_a_change_within_tolerance_passes(recording):
    check(recording, make_allowlist(factor=2.0 + 1e-9))


def test_a_call_that_is_accepted_now_fails(recording):
    wider = Allowlist(
        (Tool("scale", "m", (Parameter("x", "x", 0, 100),), lambda x: {"y": 2 * x}),)
    )
    with pytest.raises(ReplayMismatch, match="rejected when recorded"):
        check(recording, wider)


def test_a_call_that_is_rejected_now_fails(recording):
    narrower = Allowlist(
        (Tool("scale", "m", (Parameter("x", "x", 0, 2),), lambda x: {"y": 2 * x}),)
    )
    with pytest.raises(ReplayMismatch, match="accepted when recorded"):
        check(recording, narrower)


def test_a_changed_task_fails(recording):
    with pytest.raises(ReplayMismatch, match=RERECORD):
        check(recording, make_allowlist(), task="another task")


def test_a_run_longer_than_the_step_limit_fails(recording):
    with pytest.raises(ReplayMismatch, match="steps"):
        check(recording, make_allowlist(), max_steps=2)


def test_a_fixture_with_an_unknown_key_is_refused(tmp_path, recording):
    path = tmp_path / "replay.json"
    save_recording(path, run(Scripted(), make_allowlist(), SYSTEM, TASK, 5), "d")
    data = json.loads(path.read_text())
    data["api_key"] = "x"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="unknown keys"):
        load_recording(path)
