"""A thermal discovery and its levels of transfer (MD9, F147):
``pbc.discovery.thermal_transfer``."""

import numpy as np
import pytest

from pbc.agents.messages import ToolCall
from pbc.discovery import thermal_transfer as thermal


def test_the_box_refuses_a_start_outside_its_bounds_and_keeps_it_in_the_trace():
    box = thermal.CoolingBox()
    result = box.call(ToolCall("1", "measure", {"start": 600.0, "time": 60.0}))

    assert not result.ok and "start" in result.content["error"]
    assert box.trace == [(box.trace[0][0], result)]


def test_a_reading_is_the_bare_sphere_in_the_room_with_its_noise():
    box = thermal.CoolingBox()
    result = box.call(ToolCall("1", "measure", {"start": 50.0, "time": 300.0}))
    clean = thermal.bare(50.0, thermal.still(thermal.AIR), np.array([0.0, 300.0]))[-1]

    assert result.ok
    assert abs(result.content["temperature"] - clean) < 5 * thermal.NOISE
    assert result.content["air"] == thermal.AIR


def test_without_radiation_newtons_law_is_exact():
    # Cooling by convection alone is Newton's law with k = h A / C.
    k = thermal.CONVECTION * thermal.AREA / thermal.CAPACITY
    t = np.linspace(0.0, 600.0, 7)
    exact = thermal.AIR + 40.0 * np.exp(-k * t)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(thermal, "EMISSIVITY", 0.0)
        found = thermal.bare(60.0, thermal.still(thermal.AIR), t)
    assert found == pytest.approx(exact, abs=1e-6)


def test_the_discoverer_finds_the_convective_rate_within_the_radiation():
    box = thermal.CoolingBox()
    law = thermal.discover(box)
    convective = thermal.CONVECTION * thermal.AREA / thermal.CAPACITY

    # Radiation adds a few percent to the rate at the probed temperatures.
    assert convective < law.k < 1.05 * convective
    assert len(box.trace) == len(thermal.GRID_STARTS) * len(thermal.GRID_TIMES)
    assert law.fit.chi2 < law.fit.dof + 3 * np.sqrt(2 * law.fit.dof)


def test_no_held_out_world_is_reachable_through_the_allowlist():
    box = thermal.CoolingBox()
    thermal.discover(box)
    for world in thermal.WORLDS.values():
        unprobed, _ = thermal.never_probed(box.trace, world)
        assert unprobed
    # The tool takes no air temperature and no structure: only a start and a
    # time within their bounds.
    names = {p.name for p in box._allowlist.tool("measure").parameters}
    assert names == {"start", "time"}


def test_a_world_with_a_probed_start_counts_as_probed():
    box = thermal.CoolingBox()
    thermal.discover(box)
    probed = thermal.World(
        "interpolation",
        "a probed start",
        40.0,
        thermal.still(thermal.AIR),
        thermal.AIR,
        600.0,
    )
    assert thermal.never_probed(box.trace, probed) == (False, 0.0)


def test_the_sheath_delays_the_response():
    t = np.array([0.0, 10.0, 600.0])
    air = thermal.still(thermal.AIR)
    bare, inside = thermal.bare(60.0, air, t), thermal.sheathed(60.0, air, t)

    assert inside[1] > bare[1]  # the sheath shields the sphere at first
    assert inside[-1] > bare[-1]  # and holds it warmer
