"""The experiment of "Advection and diffusion: schemes, stability, and the
diffusion a grid adds" (fluids 01)."""

import itertools
from pathlib import Path

import numpy as np
import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

from pbc.experiment import encode
from pbc.fluids.experiments import advection_and_diffusion

MODULE = "pbc.fluids.experiments.advection_and_diffusion"
PAGE = "fluids/01-advection-and-diffusion"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("advection_and_diffusion")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_figure_file_is_the_bytes_of_the_one_encoder(results):
    directory, found = results
    experiment = advection_and_diffusion.run()

    for name in found["figures"]:
        label = name.removesuffix(".png")
        assert (directory / name).read_bytes() == encode(experiment.figures[label])


def test_the_upwind_diffusion_is_the_modified_equation(results):
    _, found = results
    rows = found["tables"]["diffusion-run"]["rows"]

    # The measured coefficient agrees with a dx (1 - C) / 2, and the gap falls
    # as dx squared: each halving of the cell divides it by four.
    assert float(found["numbers"]["diffusion-order"]) == pytest.approx(2.0, abs=0.05)
    gaps = [float(row[4]) for row in rows]
    for coarse, fine in itertools.pairwise(gaps):
        assert coarse / fine == pytest.approx(4.0, rel=0.05)
    for _, _, measured, predicted, _ in rows:
        assert float(measured) == pytest.approx(float(predicted), rel=3e-3)


def test_the_physical_and_the_numerical_diffusion_add(results):
    _, found = results

    for _, expected, measured, _ in found["tables"]["physical-run"]["rows"]:
        assert float(measured) == pytest.approx(float(expected), rel=3e-4)


def test_the_stability_limits_are_the_closed_forms(results):
    _, found = results
    rows = {
        (scheme, float(c), float(r)): (float(factor), float(largest))
        for scheme, c, r, factor, largest in found["tables"]["stability-run"]["rows"]
    }

    assert rows[("upwind", 1.1, 0.0)][0] == pytest.approx(1.2, abs=1e-4)
    assert rows[("central", 0.5, 0.0)][0] == pytest.approx(1.25**0.5, abs=1e-4)
    assert rows[("Lax-Wendroff", 1.1, 0.0)][0] == pytest.approx(
        (1 + 4 * 1.21 * 0.21) ** 0.5, abs=1e-4
    )
    assert rows[("upwind", 0.5, 0.3)][0] == pytest.approx(1.2, abs=1e-4)
    # With diffusion: the sawtooth of Lax-Wendroff and of the central scheme
    # beyond r = 1/2, and the long waves of the central scheme for C^2 > 2 r.
    assert rows[("Lax-Wendroff", 0.9, 0.2)][0] == pytest.approx(1.42, abs=1e-4)
    assert rows[("central", 0.5, 0.6)][0] == pytest.approx(1.4, abs=1e-4)
    theta = 2.0 * np.pi * np.arange(64) / 64
    central = 1 - 0.2 * (1 - np.cos(theta)) - 0.8j * np.sin(theta)
    assert rows[("central", 0.8, 0.1)][0] == pytest.approx(
        np.max(np.abs(central)), abs=1e-4
    )
    for (scheme, c, r), (factor, largest) in rows.items():
        stable = factor <= 1.0 + 1e-4
        assert stable == (
            (scheme == "upwind" and c + 2 * r <= 1.0)
            or (scheme == "Lax-Wendroff" and c**2 + 2 * r <= 1.0)
            or (scheme == "central" and c**2 <= 2 * r <= 1.0)
        )
        assert (largest < 2.0) == stable


def test_the_front_approaches_the_modified_equation_not_the_sharp_front(results):
    _, found = results
    rows = found["tables"]["front-run"]["rows"]

    assert float(found["numbers"]["front-order"]) == pytest.approx(1.0, abs=0.1)
    assert all(float(row[1]) > 0.4 for row in rows)
    assert all(float(row[2]) < 1e-3 for row in rows)


def test_the_exercises(results):
    _, found = results
    numbers = found["numbers"]

    assert float(numbers["fine-courant"]) + 2 * float(numbers["fine-r"]) <= 1.0001
    assert float(numbers["fine-numerical"]) <= 1e-3
    assert float(numbers["fine-diffusion"]) == pytest.approx(
        1e-2 + float(numbers["fine-numerical"]), rel=1e-3
    )
    upwind, lax_wendroff = found["tables"]["outflow-run"]["rows"]
    assert upwind[1] == "exactly zero"
    assert float(lax_wendroff[1]) > 1e-3
