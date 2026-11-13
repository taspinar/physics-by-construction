"""The experiment of "Cylinder wake PIV lab" (fluids 8): what the page claims
is what the committed samples give, the frequency and the Strouhal number are
the dossiers', the stated uncertainties' assumptions are checked on the data,
and the figures follow the conventions of a measured-data lab."""

import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from support.experiments import (
    assert_the_page_and_the_results_agree,
    page_of,
    run_entry_point,
)

from pbc.authoring.tables import is_numeric_console_block
from pbc.data.adapters import hot_wire_series, piv_probe_series
from pbc.data.plotting import check_figure, figure_status
from pbc.data.reference import cylinder_wake
from pbc.experiment import encode
from pbc.fluids import piv
from pbc.fluids.experiments import cylinder_wake_piv_lab as lab

MODULE = "pbc.fluids.experiments.cylinder_wake_piv_lab"
PAGE = "fluids/08-cylinder-wake-piv-lab"
LABELS = sorted(lab.run().figures)


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("cylinder_wake_piv_lab")
    return directory, run_entry_point(MODULE, directory)


@pytest.fixture(scope="module")
def experiment():
    return lab.run()


@pytest.fixture(scope="module")
def wake():
    return lab.load_wake()


def _number(found: dict, name: str) -> float:
    return float(found["numbers"][name].replace(",", ""))


def _column(found: dict, table: str, column: int) -> list[str]:
    return [row[column] for row in found["tables"][table]["rows"]]


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_no_section_id_equals_a_cell_label():
    # Both become id="..." on the page (pitfall 8 of the labs).
    page = page_of(PAGE)
    sections = set(re.findall(r"\{#([a-z0-9-]+)\}", page))
    labels = set(re.findall(r"^#\|\s*label:\s*([a-z0-9-]+)\s*$", page, re.MULTILINE))
    assert labels and sections
    assert not sections & labels


def test_the_series_carry_the_status_of_the_cards(wake):
    probe = piv_probe_series(wake, 0, 1)
    assert probe.artifact == "processed-measured"
    assert probe.status == "processed"
    assert probe.sigma is None  # the record states no PIV uncertainty
    assert (probe.x_unit, probe.y_unit) == ("s", "m/s")
    assert probe.x.size == 8000 and probe.x[1] == pytest.approx(0.05)
    assert probe.y == pytest.approx(wake.probes[:, 0, 1])
    runs = lab.load_hot_wire()
    series = hot_wire_series(runs, 0)
    assert series.artifact == "processed-measured" and series.sigma is None
    assert series.x[1] == pytest.approx(1e-3) and series.x.size == 2**14


def test_the_record_is_what_the_observational_claim_says(results):
    _, found = results
    numbers = found["numbers"]
    assert (numbers["frames"], numbers["nx"], numbers["ny"]) == ("60", "61", "46")
    assert numbers["points"] == "2,806"
    assert numbers["h-mm"] == "1.05"
    assert numbers["record-s"] == "400"
    assert (numbers["masked-low"], numbers["masked-high"]) == ("260", "263")
    assert numbers["masked-always"] == "260"
    assert numbers["runs"] == "10"


def test_the_stencils_are_checked_on_the_analytic_vortex(results):
    _, found = results
    assert 3.8 < _number(found, "order-low") <= _number(found, "order-high") < 4.05
    assert _number(found, "stencil-ratio") == pytest.approx(
        _number(found, "stated-ratio"), abs=0.05
    )
    assert _number(found, "stated-ratio") == 3.40
    assert _number(found, "gain-central") == pytest.approx(1.0, abs=0.01)
    assert _number(found, "gain-squares") == pytest.approx(
        piv.NOISE_GAIN["least squares"], abs=0.005
    )
    rows = found["tables"]["stencil-check"]["rows"]
    assert [r[0] for r in rows] == ["0.40", "0.20", "0.10", "0.05"]
    # "more than halves the noise and more than triples the truncation error"
    assert _number(found, "gain-squares") < 0.5
    assert _number(found, "stencil-ratio") > 3


def test_the_measured_vorticity_and_its_noise(results):
    _, found = results
    assert _number(found, "h-over-d") == 0.11
    assert (_number(found, "p99-central"), _number(found, "p99-squares")) == (
        21.7,
        15.3,
    )
    assert (_number(found, "max-central"), _number(found, "max-squares")) == (120, 67)
    assert (_number(found, "noise-central"), _number(found, "noise-squares")) == (
        0.68,
        0.40,
    )
    # Not the 0.447 of independent errors: the vectors' errors correlate.
    assert _number(found, "noise-ratio") == 0.59
    assert _number(found, "noise-ratio") > _number(found, "stated-gain") + 0.1
    assert _number(found, "neighbours") > 0.8
    # "a few per cent of the peaks"
    assert _number(found, "noise-central") / _number(found, "p99-central") < 0.05
    assert (_number(found, "free-bottom"), _number(found, "free-top")) == (1.9, 2.4)


def test_the_street_has_its_half_period_symmetry(results):
    _, found = results
    half, full = _number(found, "sym-half"), _number(found, "sym-full")
    assert half == 0.68 and full == 0.67
    assert abs(half - full) < 0.05  # "as closely as a whole period later"
    assert abs(_number(found, "sym-plain")) < 0.1
    assert abs(_number(found, "sym-none")) < 0.1
    assert _number(found, "recirculation") == 2.14


def test_the_shedding_frequency_is_the_dossiers(results):
    _, found = results
    # The dossier: 0.8887 +- 0.0028 Hz at 2 D, 0.8881 at 5 D, Welch 0.8914,
    # the harmonic of u 1.792 Hz.
    assert (found["numbers"]["f-2d"], found["numbers"]["f-2d-err"]) == (
        "0.8887",
        "0.0028",
    )
    assert found["numbers"]["f-5d"] == "0.8881"
    assert found["numbers"]["f-welch"] == "0.8914"
    assert found["numbers"]["harmonic"] == "1.792"
    assert _number(found, "harmonic-ratio") == 2.02
    assert _number(found, "f-raw-crossings") > 0.95  # noise adds crossings
    assert found["numbers"]["f-crossings"] == "0.8827"
    assert found["numbers"]["f-crossings-err"] == "0.0043"
    assert _number(found, "periods") == 352
    rows = found["tables"]["frequencies"]["rows"]
    assert [r[0] for r in rows][-2:] == ["mean of the blocks", "standard error"]


def test_the_block_errors_rest_on_assumptions_that_were_checked(results, wake):
    _, found = results
    assert _number(found, "rho-1") == 0.26
    assert _number(found, "rho-1") > _number(found, "rho-band")
    assert _number(found, "rho-outside") == 6 and _number(found, "max-lag") == 30
    assert _number(found, "effective") == 69
    assert _number(found, "naive-err") == 0.0026
    assert _number(found, "correlated-err") == 0.0059
    # The correlated error is about twice the naive one, and larger than
    # both four-block errors.
    assert _number(found, "correlated-err") > 2 * _number(found, "naive-err")
    assert _number(found, "correlated-err") > _number(found, "f-crossings-err")
    assert _number(found, "periods-per-block") == 88
    # The memory: positive correlations up to about twenty periods, a block
    # holds more than three times that.
    crossing = lab.crossing_frequency(
        wake.probes[:, 0, 1], np.arange(8000) / cylinder_wake.FPS
    )
    beyond = np.abs(crossing["rho"][24:])
    assert np.all(beyond < crossing["band"])
    assert _number(found, "spectral-gap") == 0.0003
    assert _number(found, "crossing-gap") == 1.1


def test_the_strouhal_number_and_its_comparisons(results):
    _, found = results
    assert (_number(found, "st"), _number(found, "st-err")) == (0.194, 0.001)
    assert _number(found, "st-crossings") == 0.193
    assert (_number(found, "u-top"), _number(found, "u-paper")) == (4.52, 4.35)
    assert _number(found, "st-top") == 0.187
    # "the choice of speed alone moves it by more than the frequency error"
    assert _number(found, "st") - _number(found, "st-top") > 3 * _number(
        found, "st-err"
    )
    assert _number(found, "roshko-413") == 0.2055
    assert _number(found, "roshko-gap") == 5.5
    # Above the top of the stable-range fit, below the irregular-range fit.
    assert _number(found, "fl3-high") == 0.182
    assert (
        _number(found, "fl3-high") < _number(found, "st") < _number(found, "roshko-413")
    )


def test_the_hot_wire_runs_and_the_blockage(results):
    _, found = results
    rows = found["tables"]["hot-wire"]["rows"]
    assert len(rows) == 10
    st = [float(r[6]) for r in rows]
    diameter = [r[1] for r in rows]
    by = {d: [s for s, e in zip(st, diameter, strict=True) if e == d] for d in diameter}
    assert min(by["50.0"]) > max(by["25.1"])
    assert (_number(found, "st-50-low"), _number(found, "st-25-high")) == (
        0.232,
        0.223,
    )
    # Within one cylinder St neither rises nor falls steadily with Re.
    small = by["25.1"]
    assert not (small == sorted(small) or small == sorted(small, reverse=True))
    assert (_number(found, "st-hw-low"), _number(found, "st-hw-high")) == (
        0.212,
        0.241,
    )
    assert found["numbers"]["re-hw-low"] == "8,261"
    assert found["numbers"]["re-hw-high"] == "51,833"
    assert (_number(found, "slope"), _number(found, "slope-err")) == (0.14, 0.04)
    assert _number(found, "slope-sigma") == 3.9
    assert (_number(found, "intercept"), _number(found, "intercept-err")) == (
        0.201,
        0.007,
    )
    # The continuity correction reverses the order.
    assert _number(found, "gap-50") < _number(found, "gap-25")
    gap = [float(r[7]) for r in rows]
    gap_by = {d: [g for g, e in zip(gap, diameter, strict=True) if e == d] for d in by}
    assert max(gap_by["50.0"]) < min(gap_by["25.1"])
    # The per-run error of the dossier exceeds the block scatter of the sample.
    assert _number(found, "hw-error") == 1
    assert _number(found, "hw-block-high") < 0.01 * 24


def test_the_exercises(experiment):
    scaling = experiment.output("scaling-exercise")
    assert "Re of the 25 mm cylinder: 1087" in scaling
    assert "f = St U / D: 0.338 Hz" in scaling
    aliasing = experiment.output("aliasing-exercise")
    peak = float(re.search(r"kept frames: ([\d.]+) Hz", aliasing).group(1))
    folded = float(re.search(r"shedding frequency: ([\d.]+) Hz", aliasing).group(1))
    assert peak == pytest.approx(folded, abs=0.02)
    assert "Nyquist frequency 0.77 Hz" in aliasing


@pytest.mark.parametrize("label", LABELS)
def test_every_figure_is_the_same_bytes_on_every_draw(experiment, label):
    # The page's figure must be regenerated byte for byte.
    drawings = {encode(experiment.figures[label]) for _ in range(12)}
    assert len(drawings) == 1


@pytest.mark.parametrize("label", LABELS)
def test_every_figure_follows_the_conventions(experiment, label):
    figure = experiment.figures[label]()
    try:
        assert figure_status(figure) == "processed"
        assert check_figure(figure) == []
        for ax in figure.axes:
            legend = ax.get_legend()
            for t in [] if legend is None else legend.get_texts():
                text = t.get_text()
                if "hot wire" in text or " at 2 D" in text or "PIV" in text:
                    assert "[processed]" in text, (label, text)
    finally:
        plt.close(figure)


def test_no_printed_output_is_a_block_of_numbers(experiment):
    for name, text in experiment.outputs.items():
        assert not is_numeric_console_block(text), name


def test_the_figures_leave_room_in_the_payload_budget_of_the_page(results):
    # The labs keep their figures under 0.75 MB; the Linux build in CI came
    # out up to 16.6 % larger than the local one (W7), so the local total is
    # kept at most 70 % of that bound. Locally these are about 0.40 MB.
    directory, _ = results
    total = sum(p.stat().st_size for p in directory.glob("fig-*.png"))
    assert total < 525_000, total
