"""The experiment of "Inverse physics: discovering parameters" (mechanics 12)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.mechanics.experiments.inverse_physics"
PAGE = "mechanics/12-inverse-physics-parameter-discovery"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("inverse_physics")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_known_parameters_are_recovered_with_honest_errors(results):
    _, found = results

    for row in found["tables"]["recovery"]["rows"]:
        name, truth, mean, scatter, stated, coverage = row
        assert abs(float(mean) - float(truth)) < 3 * float(scatter), name
        assert float(stated) == pytest.approx(float(scatter), rel=0.3), name
        assert float(coverage) >= 60, name


def test_a_parameter_the_data_do_not_reach_has_a_flat_profile(results):
    _, found = results

    assert float(found["numbers"]["k-rise"]) < 1.0
    assert "reasons against the fit:\n -" in found["outputs"]["tied-parameters"]


def test_only_the_wrong_model_is_rejected(results):
    _, found = results

    assert (
        found["outputs"]["wrong-model"]
        .strip()
        .endswith("right model, reasons against: none")
    )
    assert float(found["numbers"]["wrong-chi2"]) > float(found["numbers"]["right-chi2"])


def test_the_figures_state_their_status_once_at_the_caption():
    # Issue #531: a simulated figure's status is the caption's (fig-status);
    # nothing is painted on the chart area.
    import importlib

    import matplotlib.pyplot as plt
    from support.figures import figure_cells

    from pbc.data.plotting import STATUS_GID

    experiment = importlib.import_module(MODULE).run()
    cells = figure_cells(PAGE)
    assert set(experiment.figures) == set(cells)
    for label, draw in experiment.figures.items():
        assert cells[label]["fig-status"] == "simulated"
        figure = draw()
        try:
            assert not [t for t in figure.texts if t.get_gid() == STATUS_GID]
        finally:
            plt.close(figure)
    assert experiment.provenance == {}
