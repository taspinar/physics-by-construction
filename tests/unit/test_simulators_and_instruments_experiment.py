"""The experiment of "Connecting simulators and instruments" (electromagnetism
10, slot SA3, Issue #570): every claim of the page is asserted here, beside
the check that the command writes what the page shows."""

import math
from pathlib import Path

import pytest
from support.experiments import (
    assert_the_page_and_the_results_agree,
    page_of,
    run_entry_point,
)

from pbc.electromagnetism.experiments import simulators_and_instruments as lab
from pbc.instruments import MODES, RECORDED, SIMULATED, Instrument
from pbc.instruments.conformance import CHECKS, PASSED, Setting, check_driver
from pbc.instruments.recorded import NotRecorded, RecordedBench
from pbc.instruments.simulated import SimulatedRLCBench

MODULE = "pbc.electromagnetism.experiments.simulators_and_instruments"
PAGE = "electromagnetism/10-simulators-and-instruments"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("simulators-and-instruments")
    return directory, run_entry_point(MODULE, directory)


@pytest.fixture(scope="module")
def simulated():
    return lab.sweep(Instrument(SimulatedRLCBench(seed=lab.SEED), lab.ENVELOPE))


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_sweep_lies_on_the_closed_form_within_the_stated_tolerance(simulated):
    """Claim 1: at every frequency the measured gain and phase agree with the
    closed form, within the deviations the page prints."""
    assert [row[0] for row in simulated] == list(lab.FREQUENCIES_HZ)
    for frequency, gain, phase in simulated:
        exact_gain, exact_phase = lab.closed_form(frequency)
        assert abs(gain / exact_gain - 1.0) < lab.GAIN_TOLERANCE
        assert abs(phase - exact_phase) < lab.PHASE_TOLERANCE_DEG
    gain, phase = lab.deviations(simulated)
    assert gain < lab.GAIN_TOLERANCE and phase < lab.PHASE_TOLERANCE_DEG


def test_the_closed_form_is_the_capacitor_response_of_the_rlc_lesson():
    """An independent reference: the gain of the capacitor voltage is
    1 / |1 - (w/w0)^2 + j w / (w0 Q)|, peaking near Q."""
    circuit = lab.BENCH_CIRCUIT
    w0, q = circuit.natural_frequency, circuit.quality_factor
    for frequency in lab.FREQUENCIES_HZ:
        x = 2 * math.pi * frequency / w0
        expected = 1.0 / abs(complex(1.0 - x * x, x / q))
        assert lab.closed_form(frequency)[0] == pytest.approx(expected, rel=1e-12)


def test_the_recording_gives_the_same_sweep_and_is_no_new_experiment(
    results, simulated
):
    """Claim: the sweep from the recording is identical to the simulated one,
    and its run record says it is not a new experiment."""
    replay = Instrument(RecordedBench(lab.recorded_sample()), lab.ENVELOPE)
    assert lab.sweep(replay) == simulated
    _, found = results
    assert found["numbers"]["recorded-identical"] == "identical"
    records = found["tables"]["run-records"]["rows"]
    assert [r[:2] for r in records] == [[SIMULATED, "yes"], [RECORDED, "no"]]


def test_the_recording_refuses_a_frequency_between_two_recorded_ones():
    replay = Instrument(RecordedBench(lab.recorded_sample()), lab.ENVELOPE)
    assert lab.FREQUENCIES_HZ[4] < lab.BETWEEN_HZ < lab.FREQUENCIES_HZ[5]
    with pytest.raises(NotRecorded, match="cannot make a new measurement"):
        lab.measure_response(replay, lab.BETWEEN_HZ)


def test_no_refused_request_reaches_the_adapter(results):
    """Claim: none of the five requests reached the adapter; each is refused
    with the reason of the envelope."""
    _, found = results
    rows = found["tables"]["refusals"]["rows"]
    assert len(rows) == 5
    assert all(row[2] == "0" for row in rows)
    assert all("outside the permitted range" in row[1] for row in rows)
    assert found["numbers"]["refusals-reaching"] == "0"


def test_after_the_stop_nothing_reaches_the_adapter_and_the_output_is_off(results):
    _, found = results
    assert found["numbers"]["stop-reaching"] == "0"
    assert found["numbers"]["stop-last-call"] == "output_off"
    assert "the reader pressed stop" in found["numbers"]["stop-reason"]
    snapshot = dict(found["tables"]["snapshot"]["rows"])
    assert snapshot["output"] == "off"
    assert snapshot["halted"] == "the reader pressed stop"


def test_both_adapters_pass_every_contract_test(results):
    """Claim: the simulated and the recorded adapter pass all the contract
    tests."""
    _, found = results
    rows = found["tables"]["conformance"]["rows"]
    assert [row[0] for row in rows] == [name for name, _ in CHECKS]
    assert all(row[1:] == [PASSED, PASSED] for row in rows)
    assert found["numbers"]["checks"] == str(len(CHECKS))


def test_the_forgetful_adapter_fails_only_the_check_of_the_signal():
    setting = Setting(lab.AMPLITUDE_V, 4_000.0, 256_000.0, 513)
    findings = {
        f.check: f.status
        for f in check_driver(lambda: lab.ForgetfulBench(seed=lab.SEED), setting)
    }
    failed = {name for name, status in findings.items() if status != PASSED}
    assert failed == {"output-off-stops-excitation"}
    assert findings["stop"] == PASSED


def test_the_layers_diagram_names_the_three_modes():
    page = page_of(PAGE)
    assert all(mode in page for mode in MODES)
    assert "optional" in page and "not demonstrated" in page


def test_the_page_states_that_live_hardware_is_optional_and_not_demonstrated():
    """Acceptance criterion 2 of Issue #570, on the page itself."""
    page = " ".join(page_of(PAGE).split())
    assert "a live adapter is optional and, until the project's physical pilot" in page
    assert "live hardware is not demonstrated" in page
