"""The experiment of "Wave flume lab" (waves 08): what the page claims is
what the committed sample gives, and its figures follow the conventions of
a measured-data lab."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

from pbc.authoring.tables import is_numeric_console_block
from pbc.data.comparison import SCHEMA
from pbc.data.plotting import check_figure, figure_status
from pbc.waves.experiments import wave_flume_lab as lab

MODULE = "pbc.waves.experiments.wave_flume_lab"
PAGE = "waves/08-wave-flume-lab"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("wave_flume_lab")
    return directory, run_entry_point(MODULE, directory)


@pytest.fixture(scope="module")
def experiment():
    return lab.run()


def _number(found: dict, name: str) -> float:
    return float(found["numbers"][name])


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_front_travels_at_the_group_speed_and_not_at_the_others(results):
    _, found = results
    group = _number(found, "arrival-rms-group")
    assert group < 0.25  # s; the claim: about a period's sixth
    assert 3 * group < _number(found, "arrival-rms-phase")
    assert 3 * group < _number(found, "arrival-rms-long")


def test_the_phase_follows_linear_dispersion_and_not_the_wave_equation(results):
    _, found = results
    assert _number(found, "worst-linear") < 0.15  # rad, at every gauge
    assert _number(found, "worst-long") > 2.5  # rad; near half a cycle


def test_the_local_wavenumbers_agree_with_linear_theory_within_two_sigma(results):
    # The claim of the page: within two standard uncertainties of the linear
    # dispersion relation before and behind the bar, the wave equation many
    # away.
    _, found = results
    rows = {row[0]: row for row in found["tables"]["cluster-table"]["rows"]}
    for cluster in ("before the bar", "behind the bar"):
        pull_linear = float(rows[cluster][8])
        pull_long = float(rows[cluster][9])
        assert abs(pull_linear) < 2.0
        assert abs(pull_long) > 5.0
    # The scatter, not the repetitions, sets the uncertainty: stated so.
    assert float(rows["before the bar"][5]) > 10 * float(rows["before the bar"][4])
    assert _number(found, "chi2-before") > 100


def test_the_solvers_are_close_in_phase_and_cover_what_their_runs_cover(results):
    _, found = results
    rows = found["tables"]["solver-table"]["rows"]
    assert [row[0].split(",")[1].strip() for row in rows] == ["modelled-reference"] * 3
    covered = {row[0].split(" ")[0]: int(row[1]) for row in rows}
    assert covered == {"i-VoF": 19, "M-sigma": 20, "D-SPH": 12}
    assert _number(found, "solvers-worst") < 0.3


def test_the_dispersive_prediction_beats_the_wave_equation_at_gauge_five(results):
    _, found = results
    assert 2 * _number(found, "rms-dispersive") < _number(found, "rms-long")


def test_the_comparator_data_is_the_measurement_and_labels_every_model(experiment):
    data = experiment.widget("gauge-five")
    assert data["schema"] == SCHEMA
    names = [m["parameter"] for m in data["models"]]
    assert names[:2] == [
        "linear dispersion, from gauge 1",
        "wave equation, no dispersion, from gauge 1",
    ]
    assert all("modelled-reference" in n for n in names[2:]) and len(names) == 5
    assert data["best_parameter"] is None
    experiment_data, models = lab.load()
    measured, _, _ = lab.propagation_run(experiment_data, models)
    np.testing.assert_allclose(data["measured"], 1000 * measured.y, atol=5e-6)
    for model in data["models"]:
        residual = np.array(model["values"]) - np.array(data["measured"])
        np.testing.assert_allclose(model["residual"], residual, atol=2e-5)


@pytest.mark.parametrize("label", sorted(lab.run().figures))
def test_every_figure_is_processed_measurement_and_follows_the_conventions(
    experiment, label
):
    figure = experiment.figures[label]()
    try:
        assert figure_status(figure) == "processed"
        assert check_figure(figure, residuals=label == "fig-waveform") == []
        # Each solver is labelled by its artifact type wherever it appears.
        for solver in ("i-VoF", "M-sigma", "D-SPH"):
            for ax in figure.axes:
                legend = ax.get_legend()
                if legend is None:
                    continue
                for t in legend.get_texts():
                    if t.get_text().startswith(solver) and "bed" not in t.get_text():
                        assert "modelled-reference" in t.get_text()
    finally:
        plt.close(figure)


def test_no_measured_series_is_drawn_as_simulated(experiment):
    for label, draw in experiment.figures.items():
        figure = draw()
        try:
            for ax in figure.axes:
                legend = ax.get_legend()
                for t in [] if legend is None else legend.get_texts():
                    text = t.get_text()
                    if text.startswith("measure"):
                        assert "[simulated]" not in text, (label, text)
        finally:
            plt.close(figure)


def test_no_printed_output_is_a_block_of_numbers(experiment):
    # A format 2 page prints no block of numbers (tests/e2e/test_lessons.py).
    for name, text in experiment.outputs.items():
        assert not is_numeric_console_block(text), name


def test_the_figures_leave_room_in_the_payload_budget_of_the_page(results):
    # The page transfers about 2.1 MB without its figures (the shared assets
    # and the text); the budget is 3 MB (docs/architecture.md), so the figures
    # keep under 0.75 MB.
    directory, _ = results
    total = sum(p.stat().st_size for p in directory.glob("fig-*.png"))
    assert total < 750_000, total
