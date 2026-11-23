"""The F140 pilot's dataset (``ad3-rlc-pilot``): the committed traces parse,
the reference module reads what the dossier states, and the CI fixture
replays the measured sweep through the recorded adapter without the device
(criterion 3 of #508)."""

import csv
import json
import math
from pathlib import Path

import numpy as np
import pytest

from pbc.data import SAMPLES_DIR
from pbc.data.reference import ad3_rlc_pilot as pilot
from pbc.instruments import RECORDED, OutOfEnvelope
from pbc.products.physics_lab import workflow
from pbc.products.physics_lab.protocol import Config

SAMPLE = SAMPLES_DIR / "ad3-rlc-pilot"


def config_of(directory: Path) -> Config:
    record = json.loads((directory / "run.json").read_text())
    stated = record["run"]["configuration"]
    return Config(
        **{k: v for k, v in stated.items() if k in Config.__dataclass_fields__}
    )


def test_ad3_rlc_pilot_sample_parses():
    """Two sweeps of 1 V from 5 kHz to 200 kHz, 513 samples per point at
    about 64 per period, both channels within the input ranges, and run
    records of a live run on the pilot's device with the declared circuit."""
    for sweep, points in (("capacitor", 19), ("rl-node", 13)):
        traces = pilot.read_traces(SAMPLE / sweep / pilot.RAW)
        assert len(traces) == points
        frequencies = sorted(t.frequency_hz for t in traces)
        assert frequencies[0] == 5_000.0 and frequencies[-1] == 200_000.0
        for trace in traces:
            assert trace.amplitude_v == 1.0
            assert trace.t.size == trace.source.size == trace.response.size == 513
            assert np.all(np.diff(trace.t) > 0)
            rate = (trace.t.size - 1) / (trace.t[-1] - trace.t[0])
            # 100 MHz over the nearest whole divider N: up to 0.5 / N from
            # the rate asked (3.2 % at 108 kHz, divider 14.45 -> 14), the
            # decision record's operating limit
            divider = math.floor(1e8 / (64 * trace.frequency_hz) + 0.5)
            assert rate == pytest.approx(1e8 / divider, rel=1e-9)
            assert abs(rate / (64 * trace.frequency_hz) - 1) <= 0.5 / (divider - 0.5)
            assert np.abs(trace.source).max() < 2.5  # the 5 V range
            assert np.abs(trace.response).max() < 25.0  # the 50 V range
        record = pilot.read_run(SAMPLE / sweep / pilot.RUN)
        run = record["run"]
        assert run["mode"] == "live" and run["new_experiment"] is True
        assert run["device"]["serial"] == "SN:210415BFB222"
        assert run["configuration"]["circuit"]["inductance_h"] == 1e-3
        assert run["units"]["frequency"] == "Hz"


def test_a_file_with_other_columns_is_refused(tmp_path):
    path = tmp_path / "raw.csv"
    path.write_text("point,frequency_hz,t_s\n1,5000,0\n")
    with pytest.raises(ValueError, match="columns"):
        pilot.read_traces(path)


def test_the_reference_reading_agrees_with_the_products_evaluator():
    """The module's own phasor fit gives the points the product's evaluator
    recomputed from the same raw file during the live run (points.csv is
    not committed; the run record's f0 and Q are)."""
    measured = pilot.response(SAMPLE, "capacitor")
    recomputed = sorted(
        workflow.read_raw(SAMPLE / "capacitor" / pilot.RAW),
        key=lambda p: p.frequency_hz,
    )
    assert [p.frequency_hz for p in recomputed] == list(measured.frequency_hz)
    assert [p.gain for p in recomputed] == pytest.approx(measured.gain, rel=1e-9)
    assert [p.phase_deg for p in recomputed] == pytest.approx(
        measured.phase_deg, abs=1e-7
    )
    # the noise of the phasor fits is small beside the model's misfit
    assert measured.gain_sigma.max() < 1e-3
    assert measured.phase_sigma_deg.max() < 0.5


def test_the_parts_measured_apart_are_what_the_dossier_states():
    """From the R-L node sweep: L = 0.861 +- 0.010 mH, C = 14.55 +- 0.15 nF,
    R_L = 63 +- 3 ohm near the resonance; f0 45.0 kHz and Q 1.50 for the
    series circuit with them, against 47.0 kHz and 1.55 measured on the
    capacitor (the run record) and 50.3 kHz and 3.16 nominal."""
    parts = pilot.parts_apart(SAMPLE)
    assert parts.inductance_h == pytest.approx(0.861e-3, abs=0.001e-3)
    assert parts.inductance_sigma == pytest.approx(0.010e-3, abs=0.001e-3)
    assert parts.capacitance_f == pytest.approx(14.55e-9, abs=0.01e-9)
    assert parts.capacitance_sigma == pytest.approx(0.15e-9, abs=0.01e-9)
    assert parts.loss_ohm == pytest.approx(62.7, abs=0.1)
    assert parts.loss_sigma == pytest.approx(3.0, abs=0.1)
    assert parts.f0_hz == pytest.approx(44_970.0, abs=10.0)
    assert parts.q == pytest.approx(1.495, abs=0.001)
    metrics = pilot.read_run(SAMPLE / "capacitor" / pilot.RUN)["check"]["metrics"]
    assert metrics["f0_hz"] == pytest.approx(47_008.7, abs=0.1)
    assert metrics["q"] == pytest.approx(1.549, abs=0.001)
    nominal = 1 / (2 * math.pi * math.sqrt(pilot.NOMINAL["L"] * pilot.NOMINAL["C"]))
    assert nominal == pytest.approx(metrics["reference_f0_hz"])
    # the parts measured apart explain most of the gap to the nominal circuit
    assert abs(parts.f0_hz / metrics["f0_hz"] - 1) < 0.05
    assert abs(parts.q / metrics["q"] - 1) < 0.05
    assert metrics["reference_q"] / metrics["q"] > 2


def test_the_coil_loss_grows_with_the_frequency():
    """No constant R_L fits the band: well inside the conditioned band
    (within 1.5 of the resonance, where 1 - H is not small) the real part of
    the coil-and-capacitor impedance rises with the frequency above the
    resonance; at the low end 1 - H is near zero and the real part is noise
    and channel mismatch, which the dossier says."""
    rl = pilot.response(SAMPLE, "rl-node")
    z = pilot.rest_impedance(rl)
    above = rl.frequency_hz > 45_000.0
    assert np.all(np.diff(z.real[above]) > 0)
    assert (
        z.real[rl.frequency_hz == 200_000.0][0] > 3 * pilot.parts_apart(SAMPLE).loss_ohm
    )
    # at 5 kHz 1 - H is under 5 %: an unknown channel mismatch of a fraction
    # of a percent or a degree moves the real part there by tens of ohm
    assert abs(1 - rl.ratio[0]) < 0.05


def test_the_ci_fixture_replays_the_measured_sweep_without_the_device(tmp_path):
    """The recorded adapter replays the committed capacitor sweep: the same
    19 points in the same order (the refinement around the resonance
    follows from the replayed coarse points), and the evaluator's f0 and Q
    equal the live run's record. Nothing is measured: the run record says
    recorded, not a new experiment."""
    directory = SAMPLE / "capacitor"
    result = workflow.run(
        config_of(directory), tmp_path, mode=RECORDED, sample=directory
    )
    assert result.status == "completed", result.diagnostics
    live = pilot.read_run(directory / pilot.RUN)
    replayed = json.loads((tmp_path / "run.json").read_text())
    assert replayed["run"]["mode"] == "recorded"
    assert replayed["run"]["new_experiment"] is False
    assert replayed["run"]["device"]["dataset"] == "ad3-rlc-pilot/capacitor"
    # The same metrics to rounding: the platform's floating point (macOS
    # where the run was recorded, Linux in CI) differs in the last digits.
    metrics, expected = replayed["check"]["metrics"], live["check"]["metrics"]
    assert metrics.keys() == expected.keys()
    for name, value in expected.items():
        if isinstance(value, float):
            assert metrics[name] == pytest.approx(value, rel=1e-9), name
        else:
            assert metrics[name] == value, name
    with (tmp_path / "points.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    with (directory / pilot.RAW).open() as handle:
        recorded = {}
        for row in csv.DictReader(handle):
            recorded.setdefault(row["point"], row["frequency_hz"])
    assert [r["frequency_hz"] for r in rows] == list(recorded.values())


def test_the_fixture_replays_under_the_live_envelope_it_was_recorded_with():
    """200 kHz is outside the simulated bench's envelope (50 kHz) and inside
    the live one; the replay keeps the live envelope and its current bound,
    so a setting the pilot could not have made is refused, not computed."""
    instrument = workflow.make_instrument(
        config_of(SAMPLE / "capacitor"), RECORDED, SAMPLE / "capacitor"
    )
    assert instrument.envelope.frequency.high == 200_000.0
    assert instrument.envelope.series_resistance_ohm == pytest.approx(99.0)
    with pytest.raises(OutOfEnvelope):
        instrument.excite(2.5, 47_000.0)


def test_only_the_export_of_a_live_run_is_replayed_as_a_measurement(tmp_path):
    directory = tmp_path / "export"
    directory.mkdir()
    record = json.loads((SAMPLE / "capacitor" / pilot.RUN).read_text())
    record["run"]["mode"] = "simulated"
    (directory / "run.json").write_text(json.dumps(record))
    with pytest.raises(ValueError, match="not the export of a live run"):
        workflow.read_export(directory)
