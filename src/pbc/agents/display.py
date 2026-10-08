"""Show an agent run and its allowlist on a lesson page.

Both are the result of a code cell, so they render as Markdown the build
produced. A run is shown from a *replay*: the model's messages are the
recorded ones, labelled as such with the model and the date, and every tool
result is the one the build recomputed. The results stored in the fixture are
never displayed.

Model text is untrusted. It is only ever placed inside a fenced code block, so
that nothing in it can become markup of the page.
"""

import json
import re

from pbc.agents.loop import Transcript
from pbc.agents.messages import ToolCall, ToolResult
from pbc.agents.replay import Recording
from pbc.agents.tools import Allowlist, Tool


def _fence(text: str) -> str:
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def _block(text: str) -> str:
    fence = _fence(text)
    return f"{fence}{{.text}}\n{text.rstrip()}\n{fence}"


def _inline(text: str) -> str:
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    fence = "`" * (longest + 1)
    return f"{fence} {text} {fence}"


def _number(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return json.dumps(value)
    return f"{value:.6g}"


def _call(call: ToolCall) -> str:
    arguments = call.arguments
    if isinstance(arguments, dict):
        shown = ", ".join(f"{key}={_number(value)}" for key, value in arguments.items())
    else:
        shown = json.dumps(arguments)
    return _inline(f"{call.name}({shown})")


def _result(result: ToolResult) -> str:
    if not result.ok:
        return f"**rejected before it ran:** {_inline(str(result.content['error']))}"
    values = ", ".join(f"{k} = {_number(v)}" for k, v in result.content.items())
    return f"**recomputed by this build:** {_inline(values)}"


class RunDisplay:
    """A replayed run, rendered with its recorded messages labelled."""

    def __init__(self, recording: Recording, transcript: Transcript):
        self.recording = recording
        self.transcript = transcript

    def _repr_markdown_(self) -> str:
        recording = self.recording
        lines = [
            "::: {.agent-run}",
            f"**Recorded run.** The model messages below were recorded from"
            f" {_inline(recording.model)} on {recording.recorded}. This build"
            " did not call a model. It ran every tool call again; the results"
            " shown are the ones it computed.",
            "",
        ]
        if recording.placeholder:
            lines += [
                "**This recording is a placeholder.** Its messages were written"
                " by hand, not produced by a model, and stand in until the"
                " maintainer records a live run.",
                "",
            ]
        for number, step in enumerate(self.transcript.steps, start=1):
            lines += [f"**Step {number}. Model message (recorded):**", ""]
            lines += [_block(step.message.text or "(no text)"), ""]
            for call, result in zip(step.message.tool_calls, step.results, strict=True):
                lines.append(f"- {_call(call)}: {_result(result)}")
            lines.append("")
        ending = (
            "The model ended the run with a message that requests no tool."
            if self.transcript.finished
            else "The step limit stopped the run."
        )
        lines += [ending, ":::", ""]
        return "\n".join(lines)


def _tool_lines(tool: Tool) -> list[str]:
    lines = [f"- {_inline(tool.name)}: {tool.description}"]
    lines += [
        f"    - {_inline(p.name)}: {p.description}; allowed values {p.low:g} to"
        f" {p.high:g}"
        for p in tool.parameters
    ]
    return lines


class AllowlistDisplay:
    """The allowlist of a lesson as a list of tools, arguments, and bounds.

    A list rather than a table: it wraps on a phone screen, where a wide table
    would need a scroll region.
    """

    def __init__(self, allowlist: Allowlist):
        self.allowlist = allowlist

    def _repr_markdown_(self) -> str:
        lines: list[str] = []
        for tool in self.allowlist.tools:
            lines += _tool_lines(tool)
        return "\n".join(lines) + "\n"
