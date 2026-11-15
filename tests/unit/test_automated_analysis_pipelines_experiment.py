"""The experiment of "Automated analysis pipelines" (mechanics 10)."""

import importlib
from pathlib import Path

import matplotlib.pyplot as plt
import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point
from support.figures import dataset_figures

from pbc.data import figure_provenance as portable
from pbc.data.plotting import figure_status
from pbc.experiment import encode

MODULE = "pbc.mechanics.experiments.automated_analysis_pipelines"
PAGE = "mechanics/10-automated-analysis-pipelines"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("automated_analysis_pipelines")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_both_reports_match_their_committed_expectations(results):
    _, found = results

    assert found["numbers"]["report-differences"] == "0"
    assert found["outputs"]["flume-expectation"].strip().endswith(": 0")


def test_the_propagated_uncertainty_matches_the_monte_carlo_spread(results):
    _, found = results
    (row,) = found["tables"]["monte-carlo-check"]["rows"]

    # Within the uncertainty of a standard deviation from the samples.
    assert abs(float(row[2])) <= float(found["numbers"]["spread-uncertainty"])


def test_halving_the_speed_uncertainty_halves_the_range_uncertainty(results):
    _, found = results

    assert found["outputs"]["halved-speed-uncertainty"].strip().endswith("ratio 0.50")


@pytest.fixture(scope="module")
def experiment():
    return importlib.import_module(MODULE).run()


def test_every_dataset_figure_declares_its_provenance(experiment):
    # Issue #531: the window sweep of the flume record states its status and
    # credit at its caption and in its PNG, from the card; the simulated
    # range sweep declares nothing.
    assert set(experiment.provenance) == set(dataset_figures(PAGE))
    assert "fig-range-sweep" not in experiment.provenance


@pytest.mark.parametrize("label", sorted(dataset_figures(PAGE)))
def test_each_dataset_figure_states_one_status_and_carries_its_provenance(
    experiment, label
):
    # The window sweep is a lesson figure (units in parentheses, no title),
    # not one of pbc.data.plotting's, so of check_figure (and so of
    # assert_cell_declared) only the rules of a declared figure apply: no
    # painted status, no painted credit. Everything else is assert_declared.
    options = dataset_figures(PAGE)[label]
    provenance = experiment.provenance[label]
    assert not provenance.model_of
    assert provenance.dataset == options["fig-dataset"]
    assert provenance.artifact == options.get("fig-artifact")
    assert provenance.status == options["fig-status"]
    figure = experiment.figures[label]()
    try:
        assert figure_status(figure) is None
        assert not any(t.get_gid() == portable.CREDIT_GID for t in figure.texts)
        assert portable.check_roles(figure, provenance) == []
    finally:
        plt.close(figure)
    card = portable.card_of(provenance.dataset)
    identity = experiment.identity(label)
    png = experiment.png(label)
    assert portable.check_png(png, provenance, card, identity) == []
    assert png == encode(
        experiment.figures[label],
        metadata=portable.metadata(provenance, card, identity),
        credit=portable.visible_credit(card),
    )
    credit = card["rights"]["figure_credit"]
    painted = portable.read_metadata(png)["pbc:visible-credit"]
    shown = credit["visible"] in ("required", "chosen")
    data = f" · {credit['short']}" if shown else ""
    assert painted == portable.VISUALIZATION_PREFIX + data
