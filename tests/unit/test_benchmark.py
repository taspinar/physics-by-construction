"""The lessons EV2 and EV3 (F81): the grid is one protocol per environment,
every frozen run replays without a model or a network and is scored again,
the plain model has no probe, and the comparability check names what differs
between two entries."""

import math
import socket
from dataclasses import replace
from pathlib import Path

import pytest

from pbc.agents import ToolCall
from pbc.discovery import benchmark, force_lab, prompt_sha
from pbc.discovery.benchmark import (
    ENVIRONMENTS,
    GRID,
    PLAIN,
    PLAIN_RUNS,
    PROTOCOLS,
    RUNS,
    Entry,
    comparable,
    entry,
    plain_allowlist,
    replay_cell,
    task_of,
    verdict,
)
from pbc.discovery.protocol import CONDITIONS
from pbc.discovery.tools import MEASURE, SUBMIT

LESSONS = Path(__file__).parents[2] / "site" / "lessons" / "agents-llm"
HOMES = {
    "D1": LESSONS / "05-discovering-a-force-law",
    "D2": LESSONS / "06-prior-knowledge-in-discovery",
    "EV2": LESSONS / "11-interactive-discovery-benchmarks",
    "EV3": LESSONS / "12-agent-versus-non-agent-baselines",
}
CELLS = {
    **{f"{e}/{c}": cell for (e, c), cell in GRID.items()},
    **{f"{e}/plain": cell for e, cell in PLAIN_RUNS.items()},
}


@pytest.fixture
def offline(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("the replay opened a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)


def test_the_grid_has_every_condition_of_every_environment_under_one_protocol():
    assert set(GRID) == {(e, c) for e in ENVIRONMENTS for c in CONDITIONS}
    for (environment, condition), cell in GRID.items():
        run = entry(cell.run)
        assert run.protocol == ENVIRONMENTS[environment]
        assert run.condition == condition
    for environment, cell in PLAIN_RUNS.items():
        assert entry(cell.run).protocol == ENVIRONMENTS[environment]
        assert entry(cell.run).condition == PLAIN


def test_the_protocols_share_budget_step_limit_seed_and_tolerance():
    shared = {(p.budget, p.max_steps, p.seeds, p.tolerance) for p in PROTOCOLS.values()}
    assert len(shared) == 1
    # The runs of D1 and D2 are scored under the very protocol objects of F66.
    assert PROTOCOLS["black-box"] is force_lab.PROTOCOLS["black-box"]
    assert PROTOCOLS["prior-knowledge"] is force_lab.PROTOCOLS["prior-knowledge"]


@pytest.mark.parametrize("name", sorted(RUNS))
def test_the_record_of_each_run_matches_its_prompt(name):
    run = RUNS[name]
    assert run.info.prompt_sha256 == prompt_sha(*task_of(name))
    assert run.info.protocol == PROTOCOLS[run.protocol].version
    assert run.info.cost.model_calls > 0
    assert run.info.cost.input_tokens is None  # a session reports none


@pytest.mark.parametrize("name", sorted(CELLS))
def test_each_run_replays_offline_and_is_scored_again(name, offline):
    recording, transcript, score = replay_cell(CELLS[name], HOMES[CELLS[name].home])
    assert not recording.placeholder
    assert transcript.finished
    assert score.claim is not None
    again = replay_cell(CELLS[name], HOMES[CELLS[name].home])[2]
    assert again == score


@pytest.mark.parametrize("environment", sorted(PLAIN_RUNS))
def test_the_plain_model_spends_no_probe(environment, offline):
    _, transcript, score = replay_cell(PLAIN_RUNS[environment], HOMES["EV3"])
    assert score.probes == 0
    calls = [c.name for s in transcript.steps for c in s.message.tool_calls]
    assert set(calls) <= {SUBMIT}


def test_the_plain_allowlist_refuses_a_probe():
    world = benchmark.environment("projectile")
    tools = plain_allowlist(world)
    assert [t.name for t in tools.tools] == [SUBMIT]
    result = tools.dispatch(ToolCall("1", MEASURE, {"speed": 10.0, "angle": 45.0}))
    assert not result.ok
    assert world.used == 0


def _entry(protocol, allowed=20):
    return Entry("x", protocol, allowed, allowed, 0.01, True)


def test_entries_of_one_protocol_and_budget_compare():
    p = PROTOCOLS["projectile"]
    assert comparable(_entry(p), _entry(p)) == ()
    assert verdict(_entry(p), _entry(p)) == "comparable"


def test_the_check_names_what_differs_and_never_its_hidden_value():
    p = PROTOCOLS["black-box"]
    modified = force_lab.PROTOCOLS["modified"]
    reasons = comparable(_entry(p), _entry(modified))
    assert reasons == ("the hidden worlds differ",)
    for value in modified.world.values():
        assert f"{value:g}" not in verdict(_entry(p), _entry(modified))

    other = comparable(_entry(p), _entry(PROTOCOLS["projectile"]))
    assert other == ("environments differ (central-force, projectile)",)

    assert comparable(_entry(p), _entry(p, allowed=0)) == (
        "budgets differ (20, 0 probes)",
    )
    looser = replace(p, tolerance=0.1)
    assert comparable(_entry(p), _entry(looser)) == ("tolerances differ (0.05, 0.1)",)
    seeds = replace(p, seeds=(1,))
    assert comparable(_entry(p), _entry(seeds)) == ("the seeds differ",)


def test_the_check_refuses_entries_scored_on_other_held_out_settings():
    p = PROTOCOLS["projectile"]
    settings = p.held_out_settings()
    moved = replace(p, held_out=({**settings[0], "speed": 2 * settings[0]["speed"]},))
    assert comparable(_entry(p), _entry(moved)) == ("the held-out settings differ",)
    assert f"{2 * settings[0]['speed']:g}" not in verdict(_entry(p), _entry(moved))
    # The protocol's settings are the ones the judge scores on.
    seen = []
    moved.make(benchmark.SEED).score_predictor(lambda s: seen.append(dict(s)) or 1.0)
    assert tuple(seen) == moved.held_out_settings() != settings
    # Naming the environment's own settings changes nothing.
    same = replace(p, held_out=settings)
    assert comparable(_entry(p), _entry(same)) == ()


def test_a_baseline_without_a_claim_does_not_recover():
    from pbc.discovery import BaselineResult

    p = PROTOCOLS["projectile"]
    failed = BaselineResult("b", 20, False, None, math.inf, "no fit")
    assert not benchmark.baseline_entry(p, failed).recovered
    lucky = BaselineResult("b", 20, False, {"g": 1.0}, 0.0, "inconsistent fit")
    assert not benchmark.baseline_entry(p, lucky).recovered


def test_a_run_is_scored_with_its_own_tools():
    from pbc.agents import ModelMessage
    from pbc.agents.loop import Step, Transcript
    from pbc.discovery import score_transcript

    probe = ToolCall("1", MEASURE, {"speed": 10.0, "angle": 45.0})
    claim = ToolCall("2", SUBMIT, {"g": 6.0})
    steps = (Step(ModelMessage("", (probe, claim)), ()), Step(ModelMessage(""), ()))
    transcript = Transcript("m", "s", "t", steps, True)
    p = PROTOCOLS["projectile"]

    agent = score_transcript(p, transcript, 0)
    plain = score_transcript(p, transcript, 0, plain_allowlist)
    assert (agent.probes, agent.refused) == (1, 0)
    assert (plain.probes, plain.refused) == (0, 1)
    assert plain.claim == agent.claim
