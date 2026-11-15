"""The experiment of "Gravitational-wave strain" (mechanics 11)."""

import importlib
import json
from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point
from support.figures import assert_cell_declared, dataset_figures

MODULE = "pbc.mechanics.experiments.gravitational_wave_strain"
PAGE = "mechanics/11-gravitational-wave-strain"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("gravitational_wave_strain")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_integrated_inspiral_follows_the_closed_form(results):
    _, found = results

    assert float(found["numbers"]["worst"]) < 1e-3
    for row in found["tables"]["inspiral-check"]["rows"]:
        assert row[1] == row[2]


def test_the_newtonian_fit_lies_within_its_spread_above_the_published_mass(
    results,
):
    _, found = results
    numbers = found["numbers"]

    assert float(numbers["spread-low"]) <= float(numbers["mc-fit"])
    assert float(numbers["mc-fit"]) <= float(numbers["spread-high"])
    # The Newtonian chirp overestimates the mass, as the lesson says, by
    # less than half of it.
    assert 0 < float(numbers["above-published"]) < 50


def test_the_comparator_holds_the_best_mass(results):
    directory, found = results

    assert found["widgets"] == ["chirp-masses.json"]
    data = json.loads((directory / "chirp-masses.json").read_text())
    assert data


@pytest.fixture(scope="module")
def experiment():
    return importlib.import_module(MODULE).run()


def test_every_figure_of_the_strain_declares_its_provenance(experiment):
    # Issue #531: every figure of the dataset states its status and credit
    # at its caption and in its PNG, from the card.
    assert set(experiment.provenance) == set(dataset_figures(PAGE))


@pytest.mark.parametrize("label", sorted(dataset_figures(PAGE)))
def test_each_figure_states_one_status_and_carries_its_provenance(experiment, label):
    assert_cell_declared(
        experiment, PAGE, label, residuals=label == "fig-measured-vs-model"
    )
