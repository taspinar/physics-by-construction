"""The campaign of SA6 (``pbc.electromagnetism.campaign``, Issue #580): F138's
procedure and estimator, the adaptive rule and its suggestions, the
interruption and its cleanup, and the resume, which accepts only a valid
checkpoint and refuses every other before the bench is touched (acceptance
criterion 3)."""

import math
import shutil
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from pbc.electromagnetism.campaign import (
    COMPLETE,
    INTERRUPTED,
    NO_BRACKET,
    REFINE,
    REPEAT,
    RESUME_CHECKS,
    SWEEP,
    Measurement,
    Plan,
    ResumeRefused,
    Suggestion,
    SuggestionRefused,
    analyse,
    check_suggestion,
    evaluate_segment,
    load_checkpoint,
    measure_point,
    new_ledger,
    reference,
    resume,
    run_segment,
    save_checkpoint,
    suggest,
)
from pbc.electromagnetism.circuits import SeriesRLC
from pbc.electromagnetism.experiments.measurement_campaigns import (
    ENVELOPE,
    OperatorStop,
)
from pbc.evidence import COMPLETED, INCONCLUSIVE
from pbc.instruments import Instrument
from pbc.instruments.conformance import CallLog
from pbc.instruments.simulated import BENCH_CIRCUIT, SimulatedRLCBench
from pbc.products.physics_lab import protocol as f138

PLAN = Plan()


def bench(seed=1, circuit=BENCH_CIRCUIT, noise_v=0.002) -> Instrument:
    return Instrument(SimulatedRLCBench(circuit, seed=seed, noise_v=noise_v), ENVELOPE)


def campaign(root: Path, plan=PLAN, seed=1):
    ledger = new_ledger(plan, (seed,), "code")
    segment = run_segment(bench(seed), plan, ledger, root, root / "c.json", "full")
    return segment, ledger


def interrupted(root: Path, stop_at=12):
    ledger = new_ledger(PLAN, (1, 2), "code")
    driver = OperatorStop(stop_at, seed=1)
    instrument = Instrument(driver, ENVELOPE)
    driver.press = instrument.request_stop
    first = run_segment(instrument, PLAN, ledger, root, root / "c.json", "segment-1")
    return first, ledger, instrument


# -- F138's procedure and estimator --------------------------------------------


def test_one_point_is_measured_as_f138_measures_it():
    config = f138.Config(circuit_confirmed=True)
    ours = measure_point(bench(), PLAN, 4_000.0)
    theirs = f138.measure(bench(), config, 4_000.0, 1.0).point
    assert ours == pytest.approx((theirs.gain, theirs.phase_deg), rel=1e-12)


def test_the_estimator_is_f138s(tmp_path):
    segment, _ = campaign(tmp_path)
    distinct = [m for m in segment.measurements if m.stage != REPEAT]
    points = [f138.Point(m.frequency_hz, 1.0, m.gain, m.phase_deg) for m in distinct]
    theirs = f138.analyse(points)
    ours = analyse(distinct)
    assert ours.f0_hz == pytest.approx(theirs.f0_hz, rel=1e-12)
    assert ours.q == pytest.approx(theirs.q, rel=1e-12)
    assert ours.bracket_hz == pytest.approx(theirs.bracket)


def test_without_noise_the_estimates_are_those_of_the_closed_form(tmp_path):
    ledger = new_ledger(PLAN, (1,), "code")
    segment = run_segment(
        bench(noise_v=0.0), PLAN, ledger, tmp_path, tmp_path / "c.json", "x"
    )
    found = analyse(segment.measurements)
    truth = reference(BENCH_CIRCUIT)
    assert found.f0_hz == pytest.approx(truth["f0_hz"], rel=1e-6)
    assert found.q == pytest.approx(truth["q"], rel=1e-4)


# -- the adaptive rule -----------------------------------------------------------


def test_the_rule_sweeps_then_halves_the_bracket_then_repeats(tmp_path):
    segment, _ = campaign(tmp_path)
    made = segment.measurements
    stages = [m.stage for m in made]
    sweep = stages.count(SWEEP)
    refine = stages.count(REFINE)
    assert stages == [SWEEP] * sweep + [REFINE] * refine + [REPEAT] * (
        len(made) - sweep - refine
    )
    assert sweep == PLAN.sweep_points
    for m in made[sweep : sweep + refine]:
        low, high = (next(x for x in made if x.id == i) for i in m.basis)
        assert m.frequency_hz == pytest.approx(
            math.sqrt(low.frequency_hz * high.frequency_hz)
        )
        assert (low.phase_deg + 90) * (high.phase_deg + 90) <= 0
    a, b = analyse(made).bracket_hz
    assert b / a - 1 <= PLAN.target_width
    assert suggest(PLAN, made) is None
    assert segment.status == COMPLETE


def test_every_suggestion_follows_from_measurements_made_before_it(tmp_path):
    segment, _ = campaign(tmp_path)
    earlier = set()
    for m in segment.measurements:
        assert set(m.basis) <= earlier
        earlier.add(m.id)


def test_a_suggestion_from_a_measurement_not_made_is_refused():
    made = [Measurement("m01", 1000.0, 1.0, -4.0, SWEEP, ())]
    check_suggestion(Suggestion(2000.0, REFINE, ("m01",), "fine"), made)
    with pytest.raises(SuggestionRefused, match="m02"):
        check_suggestion(Suggestion(2000.0, REFINE, ("m01", "m02"), "lost"), made)


def test_a_range_without_the_resonance_ends_without_a_bracket(tmp_path):
    plan = replace(PLAN, low_hz=10_000.0, high_hz=20_000.0)
    segment, ledger = campaign(tmp_path, plan)
    assert segment.status == NO_BRACKET
    assert ledger.attempts[0].status == INCONCLUSIVE


def test_the_budget_stops_the_campaign(tmp_path):
    plan = replace(PLAN, budget=12)
    segment, ledger = campaign(tmp_path, plan)
    assert segment.status == "budget spent"
    assert len(segment.measurements) == 12
    assert ledger.attempts[0].status == INCONCLUSIVE


def test_the_standard_error_from_the_repeats_has_the_right_size(tmp_path):
    """Over many seeds, f0 minus the closed form, in standard errors, has a
    spread near one: the repeats measure the noise, neither more nor less."""
    plan = replace(PLAN, repeats=10, budget=40)
    truth = reference(BENCH_CIRCUIT)["f0_hz"]
    z = []
    for seed in range(12):
        (tmp_path / str(seed)).mkdir()
        segment, _ = campaign(tmp_path / str(seed), plan, seed)
        found = analyse(segment.measurements)
        z.append((found.f0_hz - truth) / found.f0_error_hz)
    assert 0.5 < float(np.std(z)) < 1.6
    assert abs(float(np.mean(z))) < 0.8


# -- interruption, checkpoint, ledger ------------------------------------------


def test_an_interruption_keeps_complete_measurements_only_and_switches_off(tmp_path):
    first, ledger, instrument = interrupted(tmp_path)
    assert first.status == INTERRUPTED
    assert len(first.measurements) == 11
    assert first.lost is not None
    assert first.output is None
    assert instrument.snapshot()["output"] is None
    assert load_checkpoint(tmp_path / "c.json").measurements == first.measurements
    (attempt,) = ledger.attempts
    assert attempt.status == INCONCLUSIVE
    assert "not kept" in attempt.diagnostics[1]
    assert not (tmp_path / "c.json.partial").exists()


def test_a_complete_campaign_is_evaluated_from_its_recorded_checkpoint(tmp_path):
    _, ledger = campaign(tmp_path)
    evaluation = evaluate_segment(ledger, tmp_path, "full", BENCH_CIRCUIT)
    assert evaluation.correct is True
    assert ledger.attempts[0].status == COMPLETED


def test_a_valid_checkpoint_resumes_and_finishes_the_campaign(tmp_path):
    first, ledger, _ = interrupted(tmp_path)
    log = CallLog(SimulatedRLCBench(seed=2))
    instrument = Instrument(log, ENVELOPE)
    checkpoint, previous = resume(
        ledger, tmp_path, tmp_path / "c.json", PLAN, instrument
    )
    assert previous == "segment-1"
    assert log.device_calls() == []
    second = run_segment(
        instrument, PLAN, ledger, tmp_path, tmp_path / "c.json", "segment-2",
        resumed=checkpoint, prior=(previous,),
    )  # fmt: skip
    assert second.status == COMPLETE
    assert second.measurements[:11] == first.measurements
    assert second.measurements[11].frequency_hz == first.lost.frequency_hz
    assert ledger.attempts[-1].prior == ("segment-1",)
    assert evaluate_segment(ledger, tmp_path, "segment-2", BENCH_CIRCUIT).correct


def _refused(ledger, root, path, plan=PLAN, circuit=BENCH_CIRCUIT) -> str:
    log = CallLog(SimulatedRLCBench(circuit, seed=2))
    with pytest.raises(ResumeRefused) as refusal:
        resume(ledger, root, path, plan, Instrument(log, ENVELOPE))
    assert log.calls == []  # nothing reached the bench, not even output_off
    return refusal.value.check


@pytest.fixture
def stopped(tmp_path):
    root = tmp_path / "campaign"
    root.mkdir()
    _, ledger, _ = interrupted(root)
    return root, ledger


def test_a_resume_from_an_older_copy_is_refused(stopped):
    root, ledger = stopped
    older = root / "older.json"
    state = load_checkpoint(root / "c.json")
    save_checkpoint(older, replace(state, measurements=state.measurements[:9]))
    assert _refused(ledger, root, older) == "recorded"


def test_a_resume_from_an_edited_checkpoint_is_refused(stopped):
    root, ledger = stopped
    state = load_checkpoint(root / "c.json")
    last = replace(state.measurements[-1], gain=state.measurements[-1].gain * 1.01)
    save_checkpoint(
        root / "c.json", replace(state, measurements=(*state.measurements[:-1], last))
    )
    assert _refused(ledger, root, root / "c.json") == "unchanged"


def test_a_resume_from_a_truncated_or_missing_checkpoint_is_refused(stopped):
    root, ledger = stopped
    text = (root / "c.json").read_text()
    (root / "c.json").write_text(text[: len(text) // 2])
    assert _refused(ledger, root, root / "c.json") == "unchanged"
    (root / "c.json").unlink()
    assert _refused(ledger, root, root / "c.json") == "unchanged"


def test_a_resume_under_another_plan_is_refused(stopped):
    root, ledger = stopped
    other = replace(PLAN, repeats=PLAN.repeats + 1)
    assert _refused(ledger, root, root / "c.json", plan=other) == "protocol"


def test_a_resume_on_another_bench_is_refused(stopped):
    root, ledger = stopped
    other = SeriesRLC(120.0, BENCH_CIRCUIT.inductance, BENCH_CIRCUIT.capacitance)
    assert _refused(ledger, root, root / "c.json", circuit=other) == "bench"


def test_a_resume_of_a_finished_campaign_is_refused(tmp_path):
    _, ledger = campaign(tmp_path)
    assert _refused(ledger, tmp_path, tmp_path / "c.json") == "unfinished"


@pytest.mark.parametrize(
    "change", [{"budget": 12}, {"low_hz": 10_000.0, "high_hz": 20_000.0}]
)
def test_a_resume_of_a_campaign_that_spent_its_budget_or_has_no_bracket_is_refused(
    tmp_path, change
):
    """Both end inconclusive, and both have finished: only an interrupted
    segment is unfinished."""
    plan = replace(PLAN, **change)
    segment, ledger = campaign(tmp_path, plan)
    assert segment.status != INTERRUPTED
    assert ledger.attempts[-1].status == INCONCLUSIVE
    assert _refused(ledger, tmp_path, tmp_path / "c.json", plan) == "unfinished"


def test_a_resume_after_a_stop_before_the_first_measurement_is_refused(tmp_path):
    """No measurement was made, so no checkpoint was written and none was
    recorded: there is nothing to resume from."""
    first, ledger, _ = interrupted(tmp_path, stop_at=1)
    assert first.status == INTERRUPTED and first.measurements == ()
    assert not (tmp_path / "c.json").exists()
    assert _refused(ledger, tmp_path, tmp_path / "c.json") == "recorded"


def test_a_resume_from_a_checkpoint_outside_the_root_is_refused(stopped, tmp_path):
    root, ledger = stopped
    outside = tmp_path / "c.json"
    shutil.copy(root / "c.json", outside)
    assert _refused(ledger, root, outside) == "recorded"


def test_a_resume_without_a_recorded_segment_is_refused(tmp_path):
    _, ledger, _ = interrupted(tmp_path)
    shutil.copy(tmp_path / "c.json", tmp_path / "copy.json")
    empty = new_ledger(PLAN, (1,), "code")
    assert _refused(empty, tmp_path, tmp_path / "c.json") == "recorded"
    assert _refused(ledger, tmp_path, tmp_path / "copy.json") == "recorded"


def test_the_checks_are_made_in_the_stated_order(stopped):
    """An older, edited copy under another plan on another bench fails the
    first check; with each check passed in turn the next one decides."""
    root, ledger = stopped
    other = SeriesRLC(120.0, BENCH_CIRCUIT.inductance, BENCH_CIRCUIT.capacitance)
    narrower = replace(PLAN, target_width=PLAN.target_width / 2)
    state = load_checkpoint(root / "c.json")
    save_checkpoint(
        root / "older.json", replace(state, measurements=state.measurements[:9])
    )
    assert _refused(ledger, root, root / "older.json", narrower, other) == "recorded"
    assert _refused(ledger, root, root / "c.json", narrower, other) == "protocol"
    assert RESUME_CHECKS == ("recorded", "unchanged", "protocol", "bench", "unfinished")
