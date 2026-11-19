"""Lesson AE1: what a discovery run did well, measured apart (F149).

One score hides what a run did. This module measures, for any contestant
of a discovery protocol (a replayed run of an agent, or a deterministic
baseline), each of these on its own, from the frozen trace or the
baseline's probes alone:

- **correctness**: the claim's held-out error is within the tolerance;
- **reasoning**: the claim reproduces the contestant's own readings within
  the noise (the chi-square test of ``pbc.discovery.baselines.consistent``);
  undefined without readings;
- **evidence**: least squares of the public family on the contestant's own
  readings recovers the law; undefined without readings;
- **completion**: a claim was submitted and the run ended within its limits;
- **cost**: the model messages and the tool calls (the tokens and the price
  are those the run recorded, never measured here);
- **measurement efficiency**: the probes spent, and the fewest of the first
  readings whose fit already recovers the law ("probes to evidence");
- **software interface**: the calls the harness refused;
- **physical-tool use**: the information the chosen settings carry about
  the law's parameters, relative to a grid of the same number of probes.

None is added to another: a profile is the list. Nothing here reads the
agent's text. The information is computed at the contestant's own fit,
never at the hidden value, so no number about the hidden world but the
judge's held-out error comes out of this module.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from pbc.agents.loop import Transcript
from pbc.agents.vision import Scored, chance
from pbc.discovery.baselines import (
    BaselineResult,
    Dataset,
    consistent,
    grid_probe,
    least_squares,
)
from pbc.discovery.environment import Environment
from pbc.discovery.protocol import Protocol, Score
from pbc.discovery.tools import MEASURE


@dataclass(frozen=True)
class Profile:
    """Every measure of one contestant on one protocol. ``None`` where a
    measure is undefined for it (no readings, no model)."""

    who: str
    environment: str
    held_out_error: float
    correct: bool
    reasoning: bool | None
    evidence: bool | None
    completed: bool
    model_calls: int | None
    tool_calls: int
    probes: int
    allowed: int
    to_evidence: int | None
    refused: int
    information: float | None


def readings_of(protocol: Protocol, transcript: Transcript, seed: int) -> Dataset:
    """The accepted ``measure`` calls of a replayed run, with the readings
    the replay recomputed."""
    world = protocol.make(seed)
    settings, values = [], []
    for step in transcript.steps:
        for call, result in zip(step.message.tool_calls, step.results, strict=True):
            if call.name == MEASURE and result.ok:
                settings.append({k: float(v) for k, v in call.arguments.items()})
                values.append(result.content[world.observation.name])
    return Dataset(tuple(settings), np.array(values), world.observation.sigma)


def first(data: Dataset, n: int) -> Dataset:
    """The first ``n`` readings of ``data``."""
    return Dataset(data.settings[:n], data.values[:n], data.sigma)


def reasoning(
    world: Environment, claim: Mapping[str, float] | None, data: Dataset
) -> bool | None:
    """Does ``claim`` reproduce the readings it was drawn from? The
    chi-square of its predictions against ``data``, with as many degrees of
    freedom as readings (the claim was not fitted here), is within what the
    noise gives. ``None`` without readings or without a claim."""
    if claim is None or not data.settings:
        return None
    predicted = np.array([world.predict(claim, s) for s in data.settings])
    chi2 = float(np.sum(((data.values - predicted) / data.sigma) ** 2))
    return consistent(chi2, len(data.settings))


def supports(protocol: Protocol, data: Dataset, seed: int) -> bool:
    """Do the readings support a recovery: does least squares of the family
    on them fit within the noise and predict the held-out settings within
    the tolerance?"""
    fit = least_squares(protocol.make(seed), data, "fit to the readings")
    return fit.success and fit.held_out_error <= protocol.tolerance


def probes_to_evidence(protocol: Protocol, data: Dataset, seed: int) -> int | None:
    """The fewest of the first readings that already support a recovery;
    ``None`` when all of them together do not."""
    parameters = len(protocol.make(seed).claim)
    for n in range(parameters + 1, len(data.settings) + 1):
        if supports(protocol, first(data, n), seed):
            return n
    return None


def _jacobian(
    world: Environment, at: Mapping[str, float], settings: Sequence[Mapping]
) -> np.ndarray:
    """The derivatives of the family's prediction with respect to each
    claim parameter, at ``at``, one row per setting (central differences)."""
    rows = []
    for s in settings:
        row = []
        for c in world.claim:
            h = 1e-6 * max(abs(at[c.name]), 1.0)
            up, down = dict(at), dict(at)
            up[c.name] += h
            down[c.name] -= h
            row.append((world.predict(up, s) - world.predict(down, s)) / (2 * h))
        rows.append(row)
    return np.array(rows)


def information(world: Environment, at: Mapping[str, float], data: Dataset) -> float:
    """The information of the settings of ``data`` about the parameters,
    det(J^T J)^(1/p) at ``at``, divided by the same for a grid of as many
    probes: above 1, the settings were chosen better than a grid."""
    p = len(world.claim)
    n = len(data.settings)
    grid_world = type(world)(budget=n)
    grid = grid_probe(grid_world).settings

    def det(settings) -> float:
        j = _jacobian(world, at, settings)
        return float(np.linalg.det(j.T @ j)) ** (1.0 / p)

    reference = det(grid)
    return math.nan if reference <= 0 else det(data.settings) / reference


def run_profile(
    who: str,
    environment: str,
    protocol: Protocol,
    transcript: Transcript,
    score: Score,
    seed: int,
    model_calls: int,
    allowed: int,
) -> Profile:
    """The profile of a replayed run of an agent (or of a plain model,
    ``allowed`` 0) under ``protocol``."""
    world = protocol.make(seed)
    data = readings_of(protocol, transcript, seed)
    has = bool(data.settings)
    calls = sum(len(step.message.tool_calls) for step in transcript.steps)
    fit = least_squares(world, data) if len(data.settings) > len(world.claim) else None
    at = fit.claim if fit is not None and fit.claim is not None else None
    return Profile(
        who=who,
        environment=environment,
        held_out_error=score.held_out_error,
        correct=score.recovered,
        reasoning=reasoning(world, score.claim, data),
        evidence=supports(protocol, data, seed) if has else None,
        completed=transcript.finished and score.claim is not None,
        model_calls=model_calls,
        tool_calls=calls,
        probes=score.probes,
        allowed=allowed,
        to_evidence=probes_to_evidence(protocol, data, seed) if has else None,
        refused=score.refused,
        information=information(world, at, data) if at is not None else None,
    )


def baseline_profile(
    environment: str,
    protocol: Protocol,
    result: BaselineResult,
    data: Dataset,
    seed: int,
) -> Profile:
    """The profile of a deterministic baseline that probed ``data`` and
    fitted ``result``: no model, no refused call."""
    world = protocol.make(seed)
    correct = result.success and result.held_out_error <= protocol.tolerance
    return Profile(
        who=result.name,
        environment=environment,
        held_out_error=result.held_out_error,
        correct=correct,
        reasoning=reasoning(world, result.claim, data),
        evidence=supports(protocol, data, seed),
        completed=result.claim is not None,
        model_calls=None,
        tool_calls=len(data.settings),
        probes=len(data.settings),
        allowed=protocol.budget,
        to_evidence=probes_to_evidence(protocol, data, seed),
        refused=0,
        information=(
            information(world, result.claim, data) if result.claim is not None else None
        ),
    )


def by_category(
    scored: Sequence[Scored], category: Mapping[int, str], categories: Sequence[str]
) -> dict[str, tuple[int, int, float]]:
    """For each category: the questions answered correctly, the questions,
    and the number a uniform guess gets right on average."""
    found = {}
    for name in categories:
        mine = [s for s in scored if category[s.question.number] == name]
        found[name] = (
            sum(s.correct for s in mine),
            len(mine),
            sum(chance(s.question, s.truth) for s in mine),
        )
    return found


def chance_distribution(probabilities: Sequence[float]) -> np.ndarray:
    """The probability of each number of correct answers, 0 to n, when each
    question is guessed independently with its own chance of being right."""
    pmf = np.array([1.0])
    for p in probabilities:
        pmf = np.convolve(pmf, [1.0 - p, p])
    return pmf
