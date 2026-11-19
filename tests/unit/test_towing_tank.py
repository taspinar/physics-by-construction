"""pbc.discovery.towing_tank: the drag law and the withheld settings stay out
of the reach of the tools (I27), the box reads with its stated relative
noise, and the two conditions of prior knowledge find what the lesson MD1
says they find."""

import json
import math

import numpy as np
import pytest

from pbc.agents import ToolCall
from pbc.discovery import towing_tank as tt
from pbc.discovery.tools import environment_allowlist

# Recognisable if they ever appear in an output.
HIDDEN = {"constant": 77.7123, "speed_exponent": 1.23456, "diameter_exponent": 2.65432}


def _text_an_agent_can_see(box) -> str:
    allowlist = environment_allowlist(box)
    text = json.dumps([s.__dict__ for s in allowlist.specs()], default=str)
    text += repr(box)
    text += " ".join(repr(getattr(box, a)) for a in dir(box) if not a.startswith("_"))
    return text


def test_no_tool_or_public_attribute_reaches_the_law_or_the_withheld_settings():
    world = HIDDEN
    box = tt.tank(world)
    allowlist = environment_allowlist(box)

    assert [t.name for t in allowlist.tools] == ["measure", "submit"]
    for sneaky in ("_law", "held_out_error", "score_predictor", "_held_out", "predict"):
        result = allowlist.dispatch(ToolCall("x", sneaky, {}))
        assert not result.ok and "not an allowed tool" in result.content["error"]
    text = _text_an_agent_can_see(box)
    for value in world.values():
        for written in (f"{value:g}", f"{value:.4g}", repr(value)):
            assert written not in text
    for setting in tt.TowingTankEnvironment._held_out:
        assert f"{setting['speed']:g}, {setting['diameter']:g}" not in text
    # The tools say the same whatever the hidden law.
    assert allowlist.specs() == environment_allowlist(tt.tank(tt.WATER)).specs()


@pytest.mark.parametrize("world", [tt.WATER, tt.UNKNOWN])
def test_the_constant_of_the_lessons_worlds_is_in_no_public_attribute(world):
    box = tt.tank(world)
    seen = [
        getattr(box, a)
        for a in dir(box)
        if not a.startswith("_") and not callable(getattr(box, a))
    ]
    text = _text_an_agent_can_see(box)
    assert f"{world['constant']:.4g}" not in text
    assert not any(
        isinstance(v, float) and math.isclose(v, world["constant"]) for v in seen
    )


def test_the_withheld_settings_cannot_be_probed():
    box = tt.tank(HIDDEN)
    allowlist = environment_allowlist(box)
    for setting in tt.TowingTankEnvironment._held_out:
        result = allowlist.dispatch(ToolCall("x", "measure", dict(setting)))
        assert not result.ok and "must be between" in result.content["error"]
    assert box.used == 0


def test_a_measure_returns_only_the_reading_and_a_submit_only_an_acknowledgement():
    box = tt.tank(HIDDEN)
    allowlist = environment_allowlist(box)
    reading = allowlist.dispatch(
        ToolCall("a", "measure", {"speed": 1.0, "diameter": 0.05})
    )
    claim = {"constant": 1.0, "speed_exponent": 1.0, "diameter_exponent": 1.0}
    submitted = allowlist.dispatch(ToolCall("b", "submit", claim))

    assert set(reading.content) == {"force"}
    assert submitted.content == {"submitted": 1.0}


def test_readings_have_the_stated_relative_noise_and_repeat():
    box = tt.tank(HIDDEN, seed=4)
    design = [
        {"speed": v, "diameter": d}
        for v in np.linspace(0.2, 2.0, 30)
        for d in (0.03, 0.08)
    ]
    box.budget = len(design) + 1
    ratios = [
        box.measure(**s)["force"] / box._law(s)
        for s in design  # the truth, in a test
    ]
    spread = np.std(np.log(ratios))
    assert spread == pytest.approx(tt.NOISE, rel=0.25)
    assert box.measure(**design[0])["force"] == pytest.approx(
        ratios[0] * box._law(design[0])
    )


def test_the_budget_is_kept():
    box = tt.tank(HIDDEN)
    allowlist = environment_allowlist(box)
    for k in range(tt.BUDGET):
        assert allowlist.dispatch(
            ToolCall(str(k), "measure", {"speed": 1.0, "diameter": 0.05})
        ).ok
    refused = allowlist.dispatch(
        ToolCall("x", "measure", {"speed": 1.0, "diameter": 0.05})
    )
    assert not refused.ok and box.used == tt.BUDGET


def test_the_judge_scores_the_truth_zero():
    box = tt.tank(HIDDEN)
    assert box.held_out_error(HIDDEN) == pytest.approx(0.0, abs=1e-12)


def test_on_the_grid_both_conditions_recover_the_quadratic_drag():
    for condition in tt.CONDITIONS:
        outcome = tt.route(tt.WATER, tt.grid_design(), condition)
        assert outcome.chosen == "v^(2) d^(2)" and outcome.recovered, condition
        assert outcome.consistent == 1


def test_on_one_sphere_only_the_prior_fixes_the_diameter():
    informed = tt.route(tt.WATER, tt.one_sphere_design(), "knowledge-informed")
    restricted = tt.route(tt.WATER, tt.one_sphere_design(), "restricted prior")

    assert informed.chosen == "v^(2) d^(2)" and informed.recovered
    # One exponent of the diameter per form of the grammar fits alike.
    assert restricted.consistent == len(tt.HALF_STEPS)
    assert restricted.chosen == "v^(2)" and not restricted.recovered


def test_in_the_unknown_world_the_prior_makes_no_claim_and_the_grammar_recovers():
    informed = tt.route(tt.UNKNOWN, tt.grid_design(), "knowledge-informed", seed=1)
    restricted = tt.route(tt.UNKNOWN, tt.grid_design(), "restricted prior", seed=1)

    assert informed.consistent == 0 and informed.chosen == "none"
    assert math.isinf(informed.held_out_error) and informed.reason
    assert restricted.chosen == "v^(3/2) d^(3/2)" and restricted.recovered


def test_the_route_probes_only_within_the_bounds_through_the_allowlist():
    for design in (tt.grid_design(), tt.one_sphere_design(), tt.random_design()):
        assert len(design) == tt.BUDGET
        for setting in design:
            assert 0.2 <= setting["speed"] <= 2.0 and 0.02 <= setting["diameter"] <= 0.1
    box = tt.tank(HIDDEN)
    data = tt.probe(environment_allowlist(box), tt.grid_design())
    assert box.used == tt.BUDGET and len(data.values) == tt.BUDGET
