"""The bounded agent route of a campaign (F145; ADR 004 harness, ADR 022
decision 8).

The agent's whole reach is one allowlisted tool per protocol of the plan:

- ``measure_point(frequency_hz)``: a point of the frequency response;
- ``measure_ringdown()``: one ring-down after a step;
- ``measure_amplitude(amplitude_v)``: the response of the LED pair at one
  amplitude.

Each is bounded by the plan and the envelope, validated by the harness and
again by ``pbc.instruments.Instrument``, and runs through
``Campaign.execute``, so the quality gate, the record, the checkpoint, and
the budget are the same as for the classical policy. A result says whether
the measurement was valid and gives its numbers with their standard
errors; never the circuit's values or a closed form.

**Recording and replay.** A campaign's trace is its replay fixture at the
product's fixture location (``products/physics-lab/fixtures/``). The build
re-executes every recorded call against the recorded bench: a fresh
simulated bench with the plan's seed, or, for a campaign recorded live, its
measurements declared as a dataset and replayed in order (ADR 007). The
recordings are made by the owner or the supervisor session with a key
(``record-campaign``), never by the build or a check; ``MeteredClient``
counts the tokens of every call, prices them at the rates the recorder
states, and ends the campaign at the spend ceiling with what was recorded.
``ScriptedCampaignClient`` is a deterministic policy that writes the
placeholder fixtures until real ones are recorded; it is not a model.
"""

import itertools
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from pbc.agents.messages import ModelMessage, ToolCall, ToolResult, ToolSpec, Turn
from pbc.agents.secrets import Secret
from pbc.agents.tools import Allowlist, Parameter, Tool
from pbc.instruments import Refused
from pbc.products.physics_lab.campaign import (
    AMPLITUDE_RESPONSE,
    FREQUENCY_RESPONSE,
    TRANSIENT,
    Campaign,
    CampaignPlan,
    Record,
    Step,
)

AGENT = "agent"
TOLERANCE = 1e-9
# The numbers a tool returns, per protocol: what a learner would read off
# the bench, with their standard errors.
RESULT_KEYS = {
    FREQUENCY_RESPONSE: ("gain", "gain_se", "phase_deg", "phase_se_deg"),
    TRANSIENT: ("f0_hz", "f0_se", "q", "q_se", "decay_rate", "damped_frequency_hz"),
    AMPLITUDE_RESPONSE: ("gain", "gain_se", "h3", "h3_se"),
}

SYSTEM = (
    "You run a measurement campaign on a prepared electronic circuit through"
    " the tools you are given; each drives the circuit and returns what one"
    " measurement shows, with standard errors, and whether the measurement"
    " passed the quality gate. An invalid measurement is never used: decide"
    " whether to repeat it. You cannot change the circuit. Spend few"
    " measurements, stop when you can answer, and report only what the valid"
    " measurements show, with their uncertainty."
)


def task(plan: CampaignPlan) -> str:
    parts = []
    if FREQUENCY_RESPONSE in plan.protocols:
        parts.append(
            "the resonance frequency f0, where the phase of the response is -90"
            f" degrees, between {plan.low_hz:g} Hz and {plan.high_hz:g} Hz, with"
            f" an interval narrower than {plan.f0_target:.2%} of f0"
        )
    if TRANSIENT in plan.protocols:
        parts.append(
            "f0 and the quality factor Q from the ring-down after a step, Q with"
            f" an interval narrower than {plan.q_target:.1%} of Q"
        )
    if AMPLITUDE_RESPONSE in plan.protocols:
        parts.append(
            "how the gain and the third harmonic of the response change with the"
            f" amplitude between {min(plan.amplitudes_v):g} V and"
            f" {max(plan.amplitudes_v):g} V, and the amplitude where the gain"
            " starts to fall"
        )
    return (
        "Find " + "; and ".join(parts) + f". You have at most {plan.budget}"
        " measurements. Report each result with its uncertainty."
    )


def _result(record: Record) -> dict[str, Any]:
    content: dict[str, Any] = {"id": record.id, "valid": record.valid}
    if record.valid:
        for key in RESULT_KEYS[record.step.protocol]:
            content[key] = float(record.numbers[key])
    else:
        content["reason"] = record.note
    return content


def campaign_tools(
    campaign: Campaign, refusals: list[Refused] | None = None
) -> Allowlist:
    """The allowlist of the agent's route: one tool per protocol of the plan,
    with the plan's budget. A refusal of the instrument reaches the agent
    as a tool error and is appended to ``refusals``."""
    plan = campaign.plan
    envelope = campaign.instrument.envelope

    def run(protocol: str, setting: float | None) -> dict[str, Any]:
        try:
            record = campaign.execute(Step(protocol, setting, AGENT))
        except Refused as reason:
            if refusals is not None:
                refusals.append(reason)
            raise RuntimeError(str(reason)) from None
        return _result(record)

    tools = []
    if FREQUENCY_RESPONSE in plan.protocols:
        tools.append(
            Tool(
                "measure_point",
                "Drive the circuit with a sine at one frequency and return the"
                " gain and the phase (degrees) of its response, with standard"
                " errors.",
                (
                    Parameter(
                        "frequency_hz",
                        "frequency of the source, Hz",
                        max(plan.low_hz, envelope.frequency.low),
                        min(plan.high_hz, envelope.frequency.high),
                    ),
                ),
                lambda frequency_hz: run(FREQUENCY_RESPONSE, round(frequency_hz, 3)),
            )
        )
    if TRANSIENT in plan.protocols:
        tools.append(
            Tool(
                "measure_ringdown",
                "Apply a step to the circuit and fit its ring-down: the"
                " resonance frequency f0 (Hz), the quality factor Q, the decay"
                " rate (1/s), and the damped frequency (Hz), with standard"
                " errors.",
                (),
                lambda: run(TRANSIENT, None),
            )
        )
    if AMPLITUDE_RESPONSE in plan.protocols:
        tools.append(
            Tool(
                "measure_amplitude",
                "Drive the circuit with a sine of one amplitude and return the"
                " gain at the fundamental and the ratio of the third harmonic"
                " to the fundamental, with standard errors.",
                (
                    Parameter(
                        "amplitude_v",
                        "amplitude of the source, V",
                        envelope.amplitude.low,
                        envelope.amplitude.high,
                    ),
                ),
                lambda amplitude_v: run(AMPLITUDE_RESPONSE, round(amplitude_v, 4)),
            )
        )
    return Allowlist(tuple(tools), budget=plan.budget)


# -- the placeholder policy --------------------------------------------------------


@dataclass
class ScriptedCampaignClient:
    """A deterministic policy in the shape of a model client, for the
    placeholder fixtures: the frequency response as a sweep in two messages
    and bisections of the -90 degree bracket, three ring-downs, the
    amplitudes of the plan, then a final answer. It is not a model."""

    plan: CampaignPlan
    sweep: int = 8
    bisections: int = 3
    ringdowns: int = 3
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
                if (
                    call.name == "measure_point"
                    and result
                    and result.ok
                    and result.content.get("valid")
                ):
                    points.append(
                        (
                            call.arguments["frequency_hz"],
                            result.content["phase_deg"],
                        )
                    )
        plan, step = self.plan, len(asked)
        script: list[tuple[str, list[dict[str, float]]]] = []
        if FREQUENCY_RESPONSE in plan.protocols:
            grid = np.geomspace(plan.low_hz, plan.high_hz, self.sweep)
            half = self.sweep // 2
            script += [
                (
                    "measure_point",
                    [{"frequency_hz": round(float(f), 3)} for f in grid[:half]],
                ),
                (
                    "measure_point",
                    [{"frequency_hz": round(float(f), 3)} for f in grid[half:]],
                ),
            ]
            script += [("bisect", [])] * self.bisections
        if TRANSIENT in plan.protocols:
            script.append(("measure_ringdown", [{}] * self.ringdowns))
        if AMPLITUDE_RESPONSE in plan.protocols:
            amplitudes = [{"amplitude_v": a} for a in plan.amplitudes_v]
            # The harness takes at most four calls per message.
            script += [
                ("measure_amplitude", amplitudes[i : i + 4])
                for i in range(0, len(amplitudes), 4)
            ]
        if step >= len(script):
            return ModelMessage(_answer(conversation), ())
        name, arguments = script[step]
        if name == "bisect":
            middle = _middle(points)
            if middle is None:
                return ModelMessage(_answer(conversation), ())
            name, arguments = "measure_point", [{"frequency_hz": middle}]
        return ModelMessage(
            "",
            tuple(
                ToolCall(id=f"call-{step}-{n}", name=name, arguments=a)
                for n, a in enumerate(arguments)
            ),
        )


def _middle(points: list[tuple[float, float]]) -> float | None:
    """The geometric middle of the narrowest pair of measured frequencies
    whose phases bracket -90 degrees."""
    ordered = sorted(points)
    best = None
    for (fa, pa), (fb, pb) in itertools.pairwise(ordered):
        if pa >= -90.0 >= pb and (best is None or fb / fa < best[1] / best[0]):
            best = (fa, fb)
    return None if best is None else round(math.sqrt(best[0] * best[1]), 3)


def _answer(conversation: Sequence[Turn]) -> str:
    valid = sum(
        1
        for t in conversation
        if isinstance(t, ToolResult) and t.ok and t.content.get("valid")
    )
    return (
        f"Scripted placeholder: {valid} valid measurements made; the evaluator"
        " computes the results from the raw samples."
    )


# -- the spend of a recording ---------------------------------------------------------


@dataclass
class Prices:
    """The recorder's prices in EUR per million input and output tokens."""

    input_eur_per_mtok: float
    output_eur_per_mtok: float

    def cost(self, input_tokens: int, output_tokens: int) -> float:
        return (
            input_tokens * self.input_eur_per_mtok
            + output_tokens * self.output_eur_per_mtok
        ) / 1e6


@dataclass
class MeteredClient:
    """A client that counts the tokens of every call of ``client`` (its
    ``last_usage``, ``{"input_tokens", "output_tokens"}``, after each call),
    adds their cost at ``prices`` to ``spent_before`` (EUR, from the
    recorder's spend ledger), and, once the total reaches ``ceiling_eur``,
    answers with a final message instead of calling the provider: the
    campaign then ends with what was recorded."""

    client: Any
    prices: Prices
    ceiling_eur: float
    spent_before: float = 0.0
    calls: list[dict[str, Any]] = field(default_factory=list)

    @property
    def model(self) -> str:
        return self.client.model

    @property
    def secrets(self) -> tuple[Secret, ...]:
        return self.client.secrets

    @property
    def spent(self) -> float:
        return self.spent_before + sum(c["cost_eur"] for c in self.calls)

    @property
    def stopped(self) -> bool:
        return self.spent >= self.ceiling_eur

    def complete(
        self, system: str, conversation: Sequence[Turn], tools: Sequence[ToolSpec]
    ) -> ModelMessage:
        if self.stopped:
            return ModelMessage(
                f"Stopped at the spend ceiling of EUR {self.ceiling_eur:g}.", ()
            )
        message = self.client.complete(system, conversation, tools)
        usage = getattr(self.client, "last_usage", None) or {}
        tokens_in = int(usage.get("input_tokens", 0))
        tokens_out = int(usage.get("output_tokens", 0))
        self.calls.append(
            {
                "input_tokens": tokens_in,
                "output_tokens": tokens_out,
                "cost_eur": self.prices.cost(tokens_in, tokens_out),
                "usage_reported": bool(usage),
            }
        )
        return message

    def summary(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "calls": len(self.calls),
            "input_tokens": sum(c["input_tokens"] for c in self.calls),
            "output_tokens": sum(c["output_tokens"] for c in self.calls),
            "usage_reported_on_every_call": all(
                c["usage_reported"] for c in self.calls
            ),
            "cost_eur": round(sum(c["cost_eur"] for c in self.calls), 6),
            "spent_before_eur": self.spent_before,
            "spent_total_eur": round(self.spent, 6),
            "ceiling_eur": self.ceiling_eur,
            "stopped_at_ceiling": self.stopped,
            "prices_eur_per_mtok": {
                "input": self.prices.input_eur_per_mtok,
                "output": self.prices.output_eur_per_mtok,
            },
        }


def spent_so_far(ledger: Path | None) -> float:
    """The total EUR the recorder's spend ledger holds (0 without one)."""
    if ledger is None or not ledger.exists():
        return 0.0
    entries = json.loads(ledger.read_text(encoding="utf-8")).get("recordings", [])
    return float(sum(e["cost_eur"] for e in entries))


def add_to_ledger(ledger: Path, entry: dict[str, Any]) -> None:
    """Append one recording's spend to the recorder's ledger."""
    data = (
        json.loads(ledger.read_text(encoding="utf-8"))
        if ledger.exists()
        else {"recordings": []}
    )
    data["recordings"].append(entry)
    ledger.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
