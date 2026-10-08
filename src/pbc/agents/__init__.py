"""The agent harness: an LLM runs an experiment over an explicit allowlist of
simulation functions (ADR 004).

The model's output is data. The harness validates every tool call the model
requests against the allowlist and its argument bounds, runs only allowlisted
functions of ``pbc``, and records a transcript. It never evaluates model
output as code, never runs a shell command, and opens no network connection;
the one exception is the request of the live client of the default provider
(``pbc.agents.clients``), which runs only on a learner's machine.

A run with a live client is not reproducible. A run with the replay client
(``pbc.agents.replay``) needs no credential and no network and executes every
tool call again against the current code.
"""

from pbc.agents.loop import Step, Transcript, run
from pbc.agents.messages import (
    ModelClient,
    ModelMessage,
    ToolCall,
    ToolResult,
    ToolSpec,
    Turn,
)
from pbc.agents.replay import (
    Recording,
    ReplayClient,
    ReplayMismatch,
    load_recording,
    replay,
    save_recording,
)
from pbc.agents.secrets import Secret, redact
from pbc.agents.tools import Allowlist, Parameter, Tool

__all__ = [
    "Allowlist",
    "ModelClient",
    "ModelMessage",
    "Parameter",
    "Recording",
    "ReplayClient",
    "ReplayMismatch",
    "Secret",
    "Step",
    "Tool",
    "ToolCall",
    "ToolResult",
    "ToolSpec",
    "Transcript",
    "Turn",
    "load_recording",
    "redact",
    "replay",
    "run",
    "save_recording",
]
