"""The starter's own tests. Physics by Construction runs them against its
current tree and at the starter's pin (ADR 022 decision 5); run them in
your copy with ``uv run pytest``."""

import json
from pathlib import Path

import pytest
from my_lab import agent, sweep

from pbc.agents.replay import ReplayMismatch
from pbc.electromagnetism.circuits import SeriesRLC
from pbc.instruments import OutOfEnvelope
from pbc.instruments.simulated import BENCH_CIRCUIT
from pbc.products.physics_lab.protocol import Config, evaluate

TRACE = "starter-agent.json"


def fixture(name: str) -> Path:
    """A trace in the fixtures directory: next to the starter in your copy,
    or the product's one fixture location in the repository."""
    here = Path(__file__).resolve()
    for directory in here.parents[:3]:
        path = directory / "fixtures" / name
        if path.is_file():
            return path
    raise FileNotFoundError(f"no fixtures/{name} next to the starter")


def test_the_planned_sweep_brackets_the_resonance_of_the_bench():
    config = Config(seed=1)
    measurements = sweep.run_sweep(sweep.make_instrument(config.seed), config)
    estimate = sweep.estimate(measurements)
    assert estimate.bracket is not None
    low, high = estimate.bracket
    f0 = BENCH_CIRCUIT.natural_frequency / (2 * 3.141592653589793)
    assert low < f0 < high


def test_the_check_is_the_evaluators_not_the_sweeps():
    config = Config(seed=1)
    points = [m.point for m in sweep.run_sweep(sweep.make_instrument(1), config)]
    # Against a different circuit the same points are not correct.
    other = SeriesRLC(50.0, BENCH_CIRCUIT.inductance, BENCH_CIRCUIT.capacitance)
    assert evaluate(points, other).correct is False


def test_the_envelope_refuses_what_the_bench_must_not_do():
    instrument = sweep.make_instrument(1)
    with pytest.raises(OutOfEnvelope):
        instrument.excite(50.0, 5_000.0)


def test_the_agent_route_replays_its_trace():
    measurements = agent.replay_trace(fixture(TRACE))
    assert 0 < len(measurements) <= agent.CONFIG.agent_budget


def test_a_changed_recorded_result_fails_the_replay(tmp_path):
    data = json.loads(fixture(TRACE).read_text())
    data["steps"][0]["results"][0]["content"]["gain"] *= 1.01
    changed = tmp_path / TRACE
    changed.write_text(json.dumps(data))
    with pytest.raises(ReplayMismatch):
        agent.replay_trace(changed)
