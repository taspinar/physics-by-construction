"""The experiment of "Microwave S-parameter lab" (electromagnetism 9): what the
page claims is what the committed files give, the stated uncertainties'
assumptions are checked on the data, and the figures follow the conventions of
a measured-data lab."""

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
from pbc.data.adapters import reflection_series, transmission_series
from pbc.data.plotting import check_figure, figure_status
from pbc.electromagnetism.experiments import microwave_sparameter_lab as lab
from pbc.electromagnetism.two_port import (
    TeeAttenuator,
    absorbed_fraction,
    largest_singular_value,
)
from pbc.experiment import Experiment, encode

MODULE = "pbc.electromagnetism.experiments.microwave_sparameter_lab"
PAGE = "electromagnetism/09-microwave-sparameter-lab"
LABELS = sorted(lab.run().figures)
RESIDUAL_FIGURES = ("fig-transmission", "fig-wideband")


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("microwave_sparameter_lab")
    return directory, run_entry_point(MODULE, directory)


@pytest.fixture(scope="module")
def experiment():
    return lab.run()


@pytest.fixture(scope="module")
def networks():
    return lab.load_networks()


def _number(found: dict, name: str) -> float:
    return float(found["numbers"][name].replace(",", ""))


def _rows(found: dict, table: str) -> list[list[str]]:
    return found["tables"][table]["rows"]


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_no_section_id_equals_a_cell_label():
    # Both become id="..." on the page (pitfall 9 of the labs).
    page = page_of(PAGE)
    sections = set(re.findall(r"\{#([a-z0-9-]+)\}", page))
    labels = set(re.findall(r"^#\|\s*label:\s*([a-z0-9-]+)\s*$", page, re.MULTILINE))
    assert labels and sections
    assert not sections & labels


def test_the_series_carry_the_status_of_the_card(networks):
    network = networks[lab.coaxial("3")]
    for series in (transmission_series(network), reflection_series(network)):
        assert series.artifact == "calibrated-observation"
        assert series.status == "calibrated"
        assert series.sigma is None  # the files state no uncertainty
        assert (series.x_unit, series.y_unit) == ("GHz", "dB")
        assert series.x.size == 191
    assert reflection_series(network).y == pytest.approx(
        20 * np.log10(np.abs(network.s[:, 0, 0]))
    )


def test_the_record_is_what_the_observational_claims_say(results):
    _, found = results
    numbers = found["numbers"]
    assert (numbers["coax-points"], numbers["single-points"]) == ("191", "871")
    assert (numbers["f-min"], numbers["coax-max"], numbers["single-max"]) == (
        "2.5",
        "50",
        "220",
    )
    assert (numbers["step"], numbers["reference"]) == ("250", "50")
    # The dossier's consistency numbers.
    assert numbers["reciprocity-coax"] == "1.3e-03"
    assert numbers["reciprocity-single"] == "0.025"
    assert _number(found, "symmetry-coax") < _number(found, "symmetry-single")


def test_the_matched_pads_are_checked_as_networks(results):
    _, found = results
    assert found["numbers"]["matched-error"] == "below 1e-12"
    rows = _rows(found, "matched-pads")
    assert [r[0] for r in rows] == ["3", "6", "10"]
    assert [r[4] for r in rows] == ["3.000", "6.000", "10.000"]
    assert {r[3] for r in rows} == {"below 1e-12"}
    assert (rows[0][1], rows[0][2]) == ("8.55", "141.9")


def test_amplitude_power_and_the_energy_balance(results):
    _, found = results
    numbers = found["numbers"]
    # The dossier's losses, in the order of the labels and each above it.
    assert [numbers[f"loss-{p}"] for p in lab.PADS] == ["3.89", "6.83", "10.53"]
    for pad in lab.PADS:
        assert _number(found, f"loss-{pad}") > float(pad)
    for row in _rows(found, "power-balance"):
        transmitted, reflected, absorbed = map(float, row[2:5])
        assert transmitted + reflected + absorbed == pytest.approx(1, abs=2e-3)
        assert reflected < 0.01  # "averages below one per cent"
        assert absorbed > transmitted + reflected  # "most ... is absorbed"
        assert float(row[1]) < float(row[6])  # passes less than the label
    assert _number(found, "wrong-loss-3") == pytest.approx(
        _number(found, "loss-3") / 2, abs=0.01
    )
    assert numbers["absorbed-3"] == "0.584"


def test_the_pads_are_passive_on_every_frequency(results, networks):
    _, found = results
    assert found["numbers"]["absorbed-min"] == "0.50"
    assert found["numbers"]["singular-max"] == "0.78"
    for network in networks.values():
        assert absorbed_fraction(network.s).min() >= 0.50
        assert largest_singular_value(network.s).max() <= 0.78


def test_the_two_instruments_agree_as_the_dossier_says(results):
    _, found = results
    assert found["numbers"]["instrument-db"] == "0.042"
    assert _number(found, "instrument-s21") < 0.01
    assert _number(found, "instrument-s11") < 0.01


def test_the_fit_and_its_residuals(results):
    _, found = results
    numbers = found["numbers"]
    assert numbers["fit-warnings"] == "none"
    assert (numbers["fit-r-series"], numbers["fit-r-shunt"]) == ("14.08", "145.5")
    assert (numbers["fit-l"], numbers["fit-tau"]) == ("15.9", "0.866")
    assert (numbers["rms-low"], numbers["rms-high"]) == ("0.0022", "0.0032")
    assert numbers["misfit-max"] == "0.019"
    # "about nine times larger" without the inductance
    assert numbers["rms-ratio-l"] == "9"
    # The fitted pad is not matched: a resistance above 50 ohm at 2.5 GHz.
    assert _number(found, "model-input") > 55
    assert _number(found, "matched-series") < _number(found, "fit-r-series")


def test_a_fitted_value_is_rounded_to_its_standard_error():
    # One significant figure of the error, the value to the same place.
    assert lab.with_error(21.765208, 0.117187) == "21.8 ± 0.1"
    assert lab.with_error(14.075762, 0.009353) == "14.076 ± 0.009"
    assert lab.with_error(1.23456, 0.0096) == "1.23 ± 0.01"  # 0.0096 -> 0.01
    assert lab.with_error(123.4, 3.2) == "123 ± 3"


def test_the_fit_cells_survive_the_white_space_of_the_page(results):
    # The page's table is read with its white space collapsed into single
    # spaces (a no-break space included): a cell must already be so.
    _, found = results
    for row in _rows(found, "fit"):
        for cell in row:
            assert cell == " ".join(cell.split()), cell


def test_another_start_of_the_fits_gives_the_same_page(results, monkeypatch):
    # The fits stop within the optimiser's tolerance of the minimum; from
    # other start points every table and number must still read the same.
    _, found = results
    fit_curve = lab.fit_curve
    for factor in ([0.7, 1.3, 1.4, 0.8], [1.25, 0.75, 0.6, 1.5]):
        monkeypatch.setattr(
            lab,
            "fit_curve",
            lambda model, x, y, p0, f=factor, **kw: fit_curve(
                model, x, y, np.asarray(p0) * f[: len(p0)], **kw
            ),
        )
        moved = lab.run().results()
        assert moved["tables"] == found["tables"]
        assert moved["numbers"] == found["numbers"]


def _formatted_values(monkeypatch) -> list[tuple[str, float, str]]:
    """Every float the experiment formats with a spec: (name, value, spec)."""
    recorded = []
    number = Experiment.number

    def record(self, name, value, spec=""):
        recorded.append((name, value, spec))
        return number(self, name, value, spec)

    monkeypatch.setattr(Experiment, "number", record)
    experiment = lab.run()
    for name, table in experiment.tables.items():
        for row in table.rows:
            for value, (column, _, spec) in zip(row, table.columns, strict=True):
                recorded.append((f"{name}: {column}", value, spec))
    return [
        (name, float(value), spec)
        for name, value, spec in recorded
        if spec and isinstance(value, float | np.floating)
    ]


def test_no_shown_number_sits_at_a_rounding_edge(monkeypatch, networks):
    # A relative change of 1e-6, far more than the fits move from another
    # start point (below 3e-7), changes no number the page shows.
    margin = 1e-6
    for name, value, spec in _formatted_values(monkeypatch):
        shown = format(value, spec)
        for moved in (value * (1 - margin), value * (1 + margin)):
            assert format(moved, spec) == shown, (name, value, spec)
    for pad in lab.PADS:
        result = lab.fit_pad(networks[lab.coaxial(pad)])
        for k, name in enumerate(lab.NAMES):
            value, stderr = result.value(name), float(result.stderr[k])
            shown = lab.with_error(value, stderr)
            for a in (1 - margin, 1 + margin):
                for b in (1 - margin, 1 + margin):
                    assert lab.with_error(value * a, stderr * b) == shown, (pad, name)


def test_the_reduced_chi_square_against_the_point_to_point_noise(results, networks):
    # The fit's own reduced chi-square is 1 by construction (no uncertainty
    # in the files); against the noise from neighbouring differences it is
    # far above 1, and the weighted fit moves no fitted value.
    _, found = results
    numbers = found["numbers"]
    assert (numbers["noise-low"], numbers["noise-high"]) == ("0.0005", "0.0006")
    assert (numbers["chi2-low"], numbers["chi2-high"]) == ("18", "33")
    for row in _rows(found, "fit-residuals"):
        assert float(row[5]) > 10
        # chi-square near (rms / noise)^2: the table is self-consistent
        assert float(row[5]) == pytest.approx(
            (float(row[1]) / float(row[4])) ** 2, rel=0.5
        )
    for pad in lab.PADS:
        network = networks[lab.coaxial(pad)]
        result = lab.fit_pad(network)
        assert result.reduced_chi2 == 1.0 and not result.absolute_sigma
        weighted = lab.chi_square_test(network, result)
        assert weighted.absolute_sigma
        assert np.allclose(weighted.params, result.params, rtol=1e-6, atol=0)
        assert any("reduced chi-square" in w for w in weighted.warnings)


def test_the_point_noise_of_white_residuals_is_their_standard_deviation():
    rng = np.random.default_rng(1)
    residuals = rng.normal(0, 0.01, 4 * 2000)

    class Fake:
        pass

    fake = Fake()
    fake.residuals = residuals
    assert lab.point_noise(fake) == pytest.approx(0.01, rel=0.05)
    # A smooth misfit on top barely changes it.
    fake.residuals = residuals + np.tile(np.linspace(0, 0.05, 2000), 4)
    assert lab.point_noise(fake) == pytest.approx(0.01, rel=0.05)


def test_the_largest_misfit_is_at_the_lowest_frequency(networks, experiment):
    for pad in lab.PADS:
        network = networks[lab.coaxial(pad)]
        tee = lab.model_of(lab.fit_pad(network))
        error = lab.misfit(network, tee)
        assert int(np.argmax(error)) == 0
        # Smooth: it falls over the first part of the band.
        assert error[:8].mean() > 2 * error[60:].mean()


def test_the_standard_errors_rest_on_an_assumption_the_data_refute(results):
    _, found = results
    assert _number(found, "correlation-low") > 0.8
    for row in _rows(found, "fit-residuals"):
        assert float(row[3]) > 0.8
    assert [r[0] for r in _rows(found, "fit")] == ["3", "6", "10"]
    # The other instrument moves R_series by several of its standard errors.
    assert _number(found, "instrument-r-errors") >= 3
    assert _number(found, "sensitivity-errors") > 10


def test_the_sensitivity_table(results):
    _, found = results
    rows = _rows(found, "sensitivity")
    assert [r[0] for r in rows] == [
        "coaxial, 2.5-50 GHz",
        "single sweep, 2.5-50 GHz",
        "coaxial, lower half",
        "coaxial, upper half",
    ]
    r_series = [float(r[1]) for r in rows]
    assert max(abs(r - r_series[0]) for r in r_series[1:]) == pytest.approx(
        _number(found, "sensitivity-r"), abs=0.006
    )


def test_the_model_fails_beyond_its_band(results):
    _, found = results
    inside = _number(found, "beyond-inside")
    at = [_number(found, f"beyond-{f}") for f in (100, 150, 220)]
    assert inside < 0.02
    assert at == sorted(at)  # "grows steadily"
    assert at[-1] > 5 * inside
    assert _number(found, "beyond-ratio") > 10
    assert found["numbers"]["delay-phase"] == "1.2"


def test_the_model_is_reciprocal_symmetric_and_passive(results):
    tee = TeeAttenuator(14.08, 145.5, 15.9e-12, 0.866e-12)
    s = tee.s(np.linspace(2.5e9, 220e9, 50))
    assert largest_singular_value(s).max() < 1


def test_the_exercises(experiment):
    decibel = experiment.output("decibel-exercise")
    assert "power transmitted: 0.25" in decibel
    assert "loss: 6.02 dB" in decibel
    assert "a wrong loss: 3.01 dB" in decibel
    assert "amplitude of a pad of exactly three decibels: 0.708" in decibel
    design = experiment.output("design-exercise")
    assert "R_series: 40.91 ohm, R_shunt: 10.10 ohm" in design
    assert "normalised input impedance: 1.000" in design
    assert "power absorbed: 0.990" in design


@pytest.mark.parametrize("label", LABELS)
def test_every_figure_is_the_same_bytes_on_every_draw(experiment, label):
    # The page's figure must be regenerated byte for byte.
    drawings = {encode(experiment.figures[label]) for _ in range(12)}
    assert len(drawings) == 1


@pytest.mark.parametrize("label", LABELS)
def test_every_figure_follows_the_conventions(experiment, label):
    figure = experiment.figures[label]()
    try:
        assert figure_status(figure) == "calibrated"
        # Panels with a residual (misfit) axis are checked as such.
        assert check_figure(figure, residuals=label in RESIDUAL_FIGURES) == []
        for ax in figure.axes:
            legend = ax.get_legend()
            for t in [] if legend is None else legend.get_texts():
                text = t.get_text()
                if "pad" in text and "fit" not in text:
                    assert "[calibrated]" in text, (label, text)
                if "T network" in text:
                    assert "[simulated]" in text, (label, text)
    finally:
        plt.close(figure)


def test_no_printed_output_is_a_block_of_numbers(experiment):
    for name, text in experiment.outputs.items():
        assert not is_numeric_console_block(text), name


def test_the_figures_leave_room_in_the_payload_budget_of_the_page(results):
    # The labs keep their figures under 0.75 MB; the Linux build in CI came
    # out up to 16.6 % larger than the local one (W7), so the local total is
    # kept at most 70 % of that bound. Locally these are about 0.42 MB.
    directory, _ = results
    total = sum(p.stat().st_size for p in directory.glob("fig-*.png"))
    assert total < 525_000, total
