"""Pictures given with the task: the loop sends them once, the live client
turns them into image parts, and a recording holds none."""

import base64
import json

import matplotlib.pyplot as plt
import pytest

from pbc.agents import Allowlist, ModelMessage, Picture, run, save_recording
from pbc.agents.clients import openai as provider
from pbc.agents.messages import UserTurn
from pbc.experiment import encode


def _png() -> bytes:
    def draw():
        fig, ax = plt.subplots(figsize=(1, 1))
        ax.plot([0, 1], [0, 1])
        return fig

    return encode(draw)


def test_a_picture_must_be_a_png():
    with pytest.raises(ValueError, match="not a PNG"):
        Picture("A", b"GIF89a")


def test_the_live_request_carries_each_picture_as_an_image_part():
    png = _png()
    request = provider.build_request(
        "m", "system", [UserTurn("look", (Picture("A", png),))], ()
    )
    content = request["messages"][1]["content"]
    assert content[0] == {"type": "text", "text": "look"}
    url = content[1]["image_url"]["url"]
    assert url.startswith("data:image/png;base64,")
    assert base64.b64decode(url.split(",", 1)[1]) == png


def test_a_turn_without_pictures_stays_plain_text():
    request = provider.build_request("m", "system", [UserTurn("look")], ())
    assert request["messages"][1]["content"] == "look"


class _Seeing:
    model = "seeing"
    secrets = ()

    def __init__(self):
        self.conversations = []

    def complete(self, system, conversation, tools):
        self.conversations.append(list(conversation))
        return ModelMessage("done")


def test_the_loop_gives_the_pictures_with_the_task_and_records_only_text(tmp_path):
    picture = Picture("A", _png())
    client = _Seeing()
    transcript = run(client, Allowlist(()), "s", "task", 2, pictures=(picture,))
    first = client.conversations[0][0]
    assert first == UserTurn("task", (picture,))
    path = tmp_path / "replay.json"
    save_recording(path, transcript, "2026-10-29")
    data = json.loads(path.read_text())
    assert data["task"] == "task"
    assert "png" not in path.read_text().lower()
