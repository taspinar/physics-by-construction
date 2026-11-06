"""The bounded agent route of the frequency-response protocol (ADR 004
harness).

The agent's whole reach is one allowlisted tool, ``measure``: a frequency
and an amplitude, each bounded by the instrument's envelope, validated by the
harness and again by ``pbc.instruments.Instrument`` before anything reaches
the device. It returns the gain and the phase of the point and nothing else:
not the circuit's values, not the closed form the evaluator checks against.
The allowlist has a budget of measurements.

In CI and on a learner's machine without a model account the route is
replayed from its trace in ``products/physics-lab/fixtures/`` (ADR 022
decision 8): every recorded call is executed again on a fresh bench with the
same seed and its result compared with the recorded one; a mismatch fails.
The traces of the slice were written by ``ScriptedClient``, a deterministic
policy and not a model, and are marked as placeholders; a learner may record
a live run with their own key (``python -m pbc.products.physics_lab record
--provider openai``).
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np

from pbc.agents.messages import ModelMessage, ToolCall, ToolResult, ToolSpec, Turn
from pbc.agents.secrets import Secret
from pbc.agents.tools import Allowlist, Parameter, Tool
from pbc.instruments import Instrument, Refused
from pbc.products.physics_lab.protocol import (
    Config,
    Measurement,
    Point,
    analyse,
    measure,
)

SYSTEM = (
    "You run a frequency-response measurement on a prepared electronic"
    " circuit through one tool, measure, which drives the circuit with a"
    " sinusoidal source and returns the gain and the phase (degrees) of the"
    " circuit's response relative to the source. You cannot change the"
    " circuit. Use few measurements, stop when you can answer, and report"
    " only what the measurements show."
)

# Replayed results are compared with the recorded ones to this relative and
# absolute tolerance; the bench is deterministic, so only round-off differs.
TOLERANCE = 1e-9


def task(config: Config) -> str:
    return (
        "Find the resonance frequency of the circuit, where the phase of the"
        " response is -90 degrees, and the gain there, between"
        f" {config.low_hz:g} Hz and {config.high_hz:g} Hz, with at most"
        f" {config.agent_budget} measurements at {config.amplitude_v:g} V."
        " Report the frequency in Hz and the gain."
    )


def measurement_tools(
    instrument: Instrument,
    config: Config,
    log: list[Measurement],
    on_point: Callable[[Measurement], None] | None = None,
    refusals: list[Refused] | None = None,
) -> Allowlist:
    """The allowlist of the route: ``measure`` and nothing else, with a
    budget of ``config.agent_budget`` measurements. A refusal of the
    instrument reaches the agent as a tool error (``Allowlist.dispatch``);
    it is also appended to ``refusals``, when given, so that the caller
    can tell a stopped or refused run from a replay that no longer
    matches its trace."""
    envelope = instrument.envelope

    def run_measure(frequency_hz: float, amplitude_v: float) -> dict[str, float]:
        try:
            measurement = measure(instrument, config, frequency_hz, amplitude_v)
        except Refused as reason:
            if refusals is not None:
                refusals.append(reason)
            raise
        log.append(measurement)
        if on_point is not None:
            on_point(measurement)
        return {
            "gain": measurement.point.gain,
            "phase_deg": measurement.point.phase_deg,
        }

    tool = Tool(
        name="measure",
        description=(
            "Drive the circuit at one frequency and amplitude and return the"
            " gain and the phase of its response."
        ),
        parameters=(
            Parameter(
                "frequency_hz",
                "frequency of the source, Hz",
                envelope.frequency.low,
                envelope.frequency.high,
            ),
            Parameter(
                "amplitude_v",
                "amplitude of the source, V",
                envelope.amplitude.low,
                envelope.amplitude.high,
            ),
        ),
        function=run_measure,
    )
    return Allowlist((tool,), budget=config.agent_budget)


@dataclass
class ScriptedClient:
    """A deterministic policy in the shape of a model client: a coarse sweep
    in two messages, a refinement between the two points that bracket -90
    degrees, and a final answer. It writes the placeholder traces of the
    slice; it is not a model and needs no key."""

    config: Config
    coarse: int = 8
    refine: int = 4
    model: str = "placeholder: scripted policy, not a model"
    secrets: tuple[Secret, ...] = ()

    def complete(
        self, system: str, conversation: Sequence[Turn], tools: Sequence[ToolSpec]
    ) -> ModelMessage:
        asked = [t for t in conversation if isinstance(t, ModelMessage)]
        results = {t.call_id: t for t in conversation if isinstance(t, ToolResult)}
        points = []
        for message in asked:
            for call in message.tool_calls:
                result = results.get(call.id)
                if result is not None and result.ok:
                    points.append((call.arguments["frequency_hz"], result.content))
        c = self.config
        coarse = np.geomspace(c.low_hz, c.high_hz, self.coarse)
        step = len(asked)
        if step == 0:
            return self._calls(step, coarse[: self.coarse // 2])
        if step == 1:
            return self._calls(step, coarse[self.coarse // 2 :])
        analysis = analyse(_points(points, c.amplitude_v))
        if step == 2 and analysis.bracket is not None:
            low, high = analysis.bracket
            return self._calls(step, np.geomspace(low, high, self.refine + 2)[1:-1])
        if analysis.f0_hz is None:
            return ModelMessage(
                "The phase did not cross -90 degrees in the range I measured;"
                " I cannot locate the resonance.",
                (),
            )
        return ModelMessage(
            f"The phase crosses -90 degrees near {analysis.f0_hz:.0f} Hz, where"
            f" the gain is about {analysis.q:.2f}, from {len(points)}"
            " measurements.",
            (),
        )

    def _calls(self, step: int, frequencies) -> ModelMessage:
        calls = tuple(
            ToolCall(
                id=f"call-{step}-{n}",
                name="measure",
                arguments={
                    "frequency_hz": round(float(f), 3),
                    "amplitude_v": self.config.amplitude_v,
                },
            )
            for n, f in enumerate(frequencies)
        )
        return ModelMessage("", calls)


def _points(points, amplitude: float) -> list[Point]:
    return [
        Point(f, amplitude, content["gain"], content["phase_deg"])
        for f, content in points
    ]
