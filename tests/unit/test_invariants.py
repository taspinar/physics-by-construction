"""pbc.discovery.invariants: the baseline finds the known invariants of a test
system and rejects its drift artefact, coincidences and identities are told
apart, and the hidden force stays hidden."""

import json
import math

import numpy as np
import pytest

from pbc.agents import ToolCall
from pbc.discovery.invariants import (
    ARTEFACT,
    COINCIDENCE,
    HALF,
    IDENTITY,
    INVARIANT,
    NOT_CONSERVED,
    OWN,
    PLANAR_LIBRARY,
    REFERENCE,
    TRIVIAL,
    AxesBox,
    CentralBox,
    box_allowlist,
    coefficients,
    conservation_ratio,
    find_invariants,
    independent,
    judge,
    rotation_defect,
)

TOLERANCE = 0.01
# Hidden values chosen to be recognisable if they ever appear in an output.
HIDDEN = {"k": 2.34567, "b": 1.45678}
STARTS = (
    (1.0, 0.2, -0.3, 0.9),
    (-0.7, 1.1, 0.8, 0.1),
    (0.4, -1.2, 1.3, -0.6),
    (1.3, 0.9, -0.5, -1.0),
    (-1.1, -0.4, -0.9, 1.2),
    (0.2, 0.6, 1.4, 0.4),
)


def energy(k, b):
    return coefficients(
        {"x2": k / 2, "y2": k / 2, "vx2": 0.5, "vy2": 0.5}
        | {"x4": b / 4, "y4": b / 4, "x2y2": b / 2},
        PLANAR_LIBRARY,
    )


ANGULAR = coefficients({"xvy": 1.0, "yvx": -1.0}, PLANAR_LIBRARY)


def probe(box, starts=STARTS):
    return [box.trajectory(*s) for s in starts]


def test_the_ratio_is_the_relative_change_and_none_for_terms_that_vanish():
    box = CentralBox(**HIDDEN)
    data = probe(box, STARTS[:2])
    x2 = coefficients({"x2": 3.0}, PLANAR_LIBRARY)
    theta = np.concatenate([s[:, 0] ** 2 for s in data])
    change = np.concatenate([s[:, 0] ** 2 - np.mean(s[:, 0] ** 2) for s in data])
    expected = np.sqrt(np.mean(change**2)) / np.sqrt(np.mean(theta**2))
    assert conservation_ratio(x2, PLANAR_LIBRARY, data) == pytest.approx(expected)
    # The ratio does not depend on the size of the coefficients.
    assert conservation_ratio(2 * ANGULAR + 0 * x2, PLANAR_LIBRARY, data) < 1e-12
    on_axis = [AxesBox(kx=1.0, ky=2.0).trajectory(1.0, 0.0, 0.0, 0.0)]
    y2 = coefficients({"y2": 1.0}, PLANAR_LIBRARY)
    assert conservation_ratio(y2, PLANAR_LIBRARY, on_axis) is None


def test_the_baseline_finds_the_test_systems_invariants_and_rejects_its_artefact():
    kx, ky = 1.0, 2.25
    box = AxesBox(kx=kx, ky=ky)
    dt = box.settings[OWN].dt
    found = find_invariants(PLANAR_LIBRARY, probe(box), TOLERANCE)
    # At the box's own setting the baseline finds two combinations: the
    # modified energies of symplectic Euler, E - (dt / 2) k x v per axis
    # (pbc.mechanics.hamiltonian), conserved by the method to round-off.
    assert len(found.candidates) == 2
    first, second = found.candidate(0), found.candidate(1)
    assert first == pytest.approx({"x2": 1.0, "vx2": 1 / kx, "xvx": -dt})
    assert second == pytest.approx({"y2": 1.0, "vy2": 1 / ky, "yvy": -dt})
    for row in found.candidates:
        verdict = box.judge(row, TOLERANCE, box.probed)
        assert verdict.verdict == ARTEFACT
        assert verdict.settings[OWN] < 1e-12
        assert verdict.settings[REFERENCE] > 3 * TOLERANCE
        # Halving the step halves the artefact's ratio: it is the method's.
        assert verdict.settings[HALF] == pytest.approx(
            verdict.settings[REFERENCE] / 2, rel=0.1
        )
    # At the reference the baseline finds the two known invariants, the
    # energy of each axis, and the build accepts them.
    reference = find_invariants(PLANAR_LIBRARY, box.held_out(REFERENCE), TOLERANCE)
    assert [reference.candidate(i) for i in range(2)] == [
        pytest.approx({"x2": 1.0, "vx2": 1 / kx}),
        pytest.approx({"y2": 1.0, "vy2": 1 / ky}),
    ]
    for row in reference.candidates:
        assert box.judge(row, TOLERANCE).verdict == INVARIANT
    assert box.known_invariants(TOLERANCE) == 2


def test_trajectories_on_one_axis_give_coincidences_that_held_out_ones_reject():
    box = AxesBox(kx=1.0, ky=2.25)
    axis = [box.trajectory(a, 0.0, v, 0.0) for a, v in ((1.0, 0.0), (0.5, 1.0))]
    found = find_invariants(PLANAR_LIBRARY, axis, TOLERANCE)
    assert set(found.constant_terms) >= {"y2", "vy2", "xy", "xvy", "yvx"}
    for term in found.constant_terms:
        c = coefficients({term: 1.0}, PLANAR_LIBRARY)
        assert box.judge(c, TOLERANCE, axis).verdict == COINCIDENCE


def test_the_central_box_has_the_energy_and_the_angular_momentum():
    box = CentralBox(**HIDDEN)
    data = probe(box)
    found = find_invariants(PLANAR_LIBRARY, data, TOLERANCE)
    assert len(found.candidates) == 2 and not found.constant_terms
    assert box.known_invariants(TOLERANCE) == 2
    e, ell = energy(**HIDDEN), ANGULAR
    assert box.judge(e, TOLERANCE, data).verdict == INVARIANT
    assert box.judge(ell, TOLERANCE, data).verdict == INVARIANT
    assert independent([e, ell, e + 3 * ell], PLANAR_LIBRARY, data) == 2
    # The energy of one axis is not conserved: the quartic couples the axes.
    one_axis = coefficients(
        {"x2": HIDDEN["k"] / 2, "vx2": 0.5, "x4": HIDDEN["b"] / 4}, PLANAR_LIBRARY
    )
    assert box.judge(one_axis, TOLERANCE, data).verdict == NOT_CONSERVED
    # A wrong stiffness is caught at this tolerance.
    wrong = energy(HIDDEN["k"] * 1.05, HIDDEN["b"])
    assert box.judge(wrong, TOLERANCE, data).verdict == NOT_CONSERVED


def test_an_identity_takes_one_value_on_every_trajectory_and_a_constant_is_trivial():
    # Two terms that differ by a constant: their difference is the same on
    # every state, an identity of the description and no law of the motion.
    library = {"a": lambda s: s[:, 0] ** 2 + 1.0, "b": lambda s: s[:, 0] ** 2}
    data = probe(CentralBox(**HIDDEN), STARTS[:3])
    found = find_invariants(library, data, TOLERANCE)
    assert found.candidate(0) == pytest.approx({"a": 1.0, "b": -1.0})
    held_out = {OWN: data, REFERENCE: data}
    verdict = judge(
        found.candidates[0], library, data, held_out, OWN, REFERENCE, TOLERANCE
    )
    assert verdict.verdict == IDENTITY
    # A term that does not change on the held-out trajectories has no ratio.
    axis = [AxesBox(kx=1.0, ky=2.0).trajectory(1.0, 0.0, 0.5, 0.0)]
    y2 = coefficients({"y2": 1.0}, PLANAR_LIBRARY)
    held_out = {OWN: axis, REFERENCE: axis}
    verdict = judge(y2, PLANAR_LIBRARY, axis, held_out, OWN, REFERENCE, TOLERANCE)
    assert verdict.verdict == TRIVIAL


def test_rotation_symmetry_is_seen_from_trajectories():
    start = (1.0, 0.2, 0.1, 0.8)
    assert rotation_defect(CentralBox(**HIDDEN), start, 0.7) < 1e-12
    assert rotation_defect(AxesBox(kx=1.0, ky=2.25), start, 0.7) > 0.1


def test_the_budget_and_the_bounds_are_kept():
    box = CentralBox(**HIDDEN, budget=1)
    with pytest.raises(ValueError):
        box.trajectory(1.6, 0.0, 0.0, 0.0)
    box.trajectory(1.0, 0.0, 0.0, 0.0)
    with pytest.raises(RuntimeError):
        box.trajectory(0.5, 0.0, 0.0, 0.0)


def _numbers(value):
    if isinstance(value, bool):
        return
    if isinstance(value, int | float):
        yield float(value)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _numbers(item)
    elif isinstance(value, list | tuple):
        for item in value:
            yield from _numbers(item)


def test_no_public_attribute_or_tool_reaches_the_hidden_force():
    box = CentralBox(**HIDDEN)
    seen = []
    for attribute in dir(box):
        if attribute.startswith("_") or attribute in {"trajectory", "held_out"}:
            continue
        value = getattr(box, attribute)
        if callable(value):
            try:
                value = value()
            except TypeError, ValueError:
                continue
        seen += list(_numbers(value))
    assert "2.34567" not in repr(box)
    allowlist, submitted = box_allowlist(box, 3)
    assert [t.name for t in allowlist.tools] == ["trajectory", "variation", "submit"]
    for sneaky in ("held_out", "judge", "known_invariants", "_acceleration"):
        result = allowlist.dispatch(ToolCall("x", sneaky, {}))
        assert not result.ok and "not an allowed tool" in result.content["error"]
    start = {"x": 1.0, "y": 0.0, "vx": 0.0, "vy": 1.0}
    assert not allowlist.dispatch(ToolCall("x", "trajectory", start | {"k": 1})).ok
    zeros = dict.fromkeys(PLANAR_LIBRARY, 0.0)
    assert not allowlist.dispatch(ToolCall("x", "variation", zeros | {"x2": 1.0})).ok
    out = [allowlist.dispatch(ToolCall("t", "trajectory", start)).content]
    out.append(
        allowlist.dispatch(ToolCall("v", "variation", zeros | {"x2": 1.0})).content
    )
    out.append(allowlist.dispatch(ToolCall("s", "submit", zeros | {"x2": 1.0})).content)
    assert not allowlist.dispatch(ToolCall("s", "submit", zeros)).ok
    text = json.dumps([s.__dict__ for s in allowlist.specs()], default=str)
    for hidden in HIDDEN.values():
        assert f"{hidden:g}" not in text
        assert not any(math.isclose(hidden, n, rel_tol=1e-6) for n in seen)
        assert not any(
            math.isclose(hidden, n, rel_tol=1e-6) for o in out for n in _numbers(o)
        )
    assert len(submitted) == 1
