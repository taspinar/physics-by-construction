"""The counterexample hunter: a claim, a budget, and a verdict the build
computes (Issue #87, on the harness of ADR 004).

A ``FalsifiableClaim`` is a statement about a simulation together with the
predicate that decides it and a budget of experiments. The agent tries to
refute it through the allowlist. The verdict is not what the agent says: the
harness takes every experiment the agent ran inside the claim's domain, runs
it again, and evaluates the predicate on the new value.

- A recomputed value that breaks the predicate is a **counterexample**. It is
  a statement about a computation the build ran, so it carries the claim type
  ``numerically-verified`` (``docs/authoring.md``), with the experiment as its
  scope.
- Otherwise the outcome is **inconclusive**. Finitely many experiments cannot
  show that a claim holds everywhere, so this outcome is not a result, has no
  claim type, and is never reported as "the claim is true".

The agent's prose is shown, labelled as recorded or as authored, and never read by the
judge. A counterexample the agent only describes, or names with a wrong
number, does not count; one the agent does not mention still does.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pbc.agents.loop import Transcript
from pbc.agents.tools import Allowlist, ToolRejected

COUNTEREXAMPLE = "counterexample"
INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True)
class FalsifiableClaim:
    """A statement, the predicate that decides it, and a budget.

    The claim is: for every experiment of ``tool`` whose arguments are in the
    domain, the value ``result`` is at most ``limit``. The domain fixes some
    arguments (``fixed``, for the choices) and bounds others (``ranges``,
    inclusive); an experiment outside it says nothing about the claim.
    ``budget`` is the number of experiments the agent may run.
    """

    statement: str
    tool: str
    fixed: Mapping[str, str]
    ranges: Mapping[str, tuple[float, float]]
    result: str
    limit: float
    budget: int

    def covers(self, arguments: Mapping[str, Any]) -> bool:
        """Whether an experiment with ``arguments`` is in the domain."""
        if any(arguments.get(name) != value for name, value in self.fixed.items()):
            return False
        return all(
            low <= arguments[name] <= high for name, (low, high) in self.ranges.items()
        )

    def holds_on(self, value: float) -> bool:
        """The predicate: the value does not exceed the limit."""
        return value <= self.limit


@dataclass(frozen=True)
class Experiment:
    """One experiment of the domain, with the value the judge computed."""

    arguments: Mapping[str, Any]
    value: float


@dataclass(frozen=True)
class Verdict:
    """What the build found out about a claim.

    ``witness`` is the first experiment, in the order the agent ran them,
    whose recomputed value breaks the predicate; it is None when the outcome
    is inconclusive. ``tested`` counts the recomputed experiments in the
    domain, and ``closest`` is the one that came nearest to breaking the
    predicate.
    """

    claim: FalsifiableClaim
    witness: Experiment | None
    tested: int
    closest: Experiment | None

    @property
    def outcome(self) -> str:
        return COUNTEREXAMPLE if self.witness is not None else INCONCLUSIVE

    @property
    def claim_type(self) -> str | None:
        """``numerically-verified`` for a recomputed counterexample, and
        nothing for any other outcome."""
        return "numerically-verified" if self.witness is not None else None


def judge(
    claim: FalsifiableClaim, transcript: Transcript, allowlist: Allowlist
) -> Verdict:
    """The verdict on ``claim`` from the experiments of ``transcript``.

    Each accepted call of the claim's tool inside the domain is run again
    with the function of ``allowlist``, not read from the transcript, and the
    predicate is evaluated on that value. A value that is not finite is not
    evidence either way (the validation contract: not measured is not
    passed) and is not counted. At most ``claim.budget`` experiments count,
    whatever the transcript holds.
    """
    tool = allowlist.tool(claim.tool)
    witness: Experiment | None = None
    closest: Experiment | None = None
    tested = 0
    for step in transcript.steps:
        for call, result in zip(step.message.tool_calls, step.results, strict=True):
            if not result.ok or call.name != claim.tool or tested >= claim.budget:
                continue
            try:
                arguments = tool.validate(call.arguments)
            except ToolRejected:
                continue  # the allowlist could not have accepted it
            if not claim.covers(arguments):
                continue
            value = float(tool.function(**arguments)[claim.result])
            if not math.isfinite(value):
                continue
            tested += 1
            experiment = Experiment(arguments, value)
            if witness is None and not claim.holds_on(value):
                witness = experiment
            if closest is None or value > closest.value:
                closest = experiment
    return Verdict(claim, witness, tested, closest)
