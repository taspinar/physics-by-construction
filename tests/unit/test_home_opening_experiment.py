"""The opening figures of the home page (F124): the paths of both bobs and
the change of the energy, drawn from the validated double pendulum of
``pbc.mechanics.chaos``, step-independent over their window, and
byte-stable."""

import json
from pathlib import Path

import numpy as np
import pytest
from support.experiments import run_entry_point

from pbc.experiment import RESULTS_FILE, encode
from pbc.mechanics.experiments import double_pendulum_chaos, home_opening

MODULE = "pbc.mechanics.experiments.home_opening"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("home_opening")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_the_figure_and_the_numbers_the_page_states(results):
    directory, found = results
    assert found["figures"] == [
        f"{home_opening.LABEL}.png",
        f"{home_opening.ENERGY_LABEL}.png",
    ]
    for label in (home_opening.LABEL, home_opening.ENERGY_LABEL):
        png = (directory / f"{label}.png").read_bytes()
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert set(found["numbers"]) == {
        "angle",
        "duration",
        "step",
        "energy-change",
        "half-step-gap",
    }
    assert (
        json.loads((directory / RESULTS_FILE).read_text())["numbers"]
        == (found["numbers"])
    )


def test_the_figure_is_byte_stable_and_is_the_file_the_command_writes(results):
    directory, _ = results
    first, second = home_opening.run(), home_opening.run()
    for label in (home_opening.LABEL, home_opening.ENERGY_LABEL):
        assert first.png(label) == second.png(label)
        assert first.png(label) == (directory / f"{label}.png").read_bytes()


def test_the_start_is_the_chaotic_start_of_the_lesson():
    lesson = double_pendulum_chaos.chaotic_start
    start = home_opening.START
    np.testing.assert_array_equal(start.x, lesson.x)
    np.testing.assert_array_equal(start.v, lesson.v)
    assert (
        double_pendulum_chaos.mass,
        double_pendulum_chaos.length,
    ) == (home_opening.MASS, home_opening.LENGTH)


def test_the_drawn_path_does_not_depend_on_the_step():
    trajectory = home_opening.run_at(home_opening.STEP)
    # Far below what the plate can show: the axes span about 4 m in about
    # 300 CSS px, about 13 mm a pixel.
    assert home_opening.half_step_gap(trajectory) < 1e-4
    assert np.max(np.abs(home_opening.energy_change(trajectory))) < 1e-6
    assert trajectory.t[-1] == pytest.approx(home_opening.DURATION)


def test_the_bobs_stay_on_their_rods():
    first, second = home_opening.bobs(home_opening.run_at(home_opening.STEP))
    np.testing.assert_allclose(np.linalg.norm(first, axis=1), home_opening.LENGTH)
    np.testing.assert_allclose(
        np.linalg.norm(second - first, axis=1), home_opening.LENGTH
    )


def test_the_figure_draws_the_computed_paths_of_both_bobs():
    trajectory = home_opening.run_at(home_opening.STEP)
    figure = home_opening.draw_opening(trajectory)
    (motion,) = figure.axes
    first, second = home_opening.bobs(trajectory)
    first_path, second_path = motion.lines[:2]
    np.testing.assert_array_equal(first_path.get_xdata(), first[:, 0])
    np.testing.assert_array_equal(first_path.get_ydata(), first[:, 1])
    np.testing.assert_array_equal(second_path.get_xdata(), second[:, 0])
    np.testing.assert_array_equal(second_path.get_ydata(), second[:, 1])
    # Told apart by width as well as colour, and named at their start.
    assert first_path.get_linewidth() > 2 * second_path.get_linewidth()
    assert first_path.get_color() != second_path.get_color()
    labels = {text.get_text(): text.xy for text in motion.texts}
    assert set(labels) == {"first bob", "second bob"}
    np.testing.assert_array_equal(labels["first bob"], first[0])
    np.testing.assert_array_equal(labels["second bob"], second[0])
    assert motion.get_xlabel() == "horizontal position (m)"
    assert motion.get_ylabel() == "height above the pivot (m)"
    assert encode(lambda: figure)[:8] == b"\x89PNG\r\n\x1a\n"


def test_the_energy_figure_draws_the_computed_change():
    trajectory = home_opening.run_at(home_opening.STEP)
    change = home_opening.energy_change(trajectory)
    (energy,) = home_opening.draw_energy(trajectory, change).axes
    np.testing.assert_array_equal(energy.lines[0].get_xdata(), trajectory.t)
    np.testing.assert_array_equal(energy.lines[0].get_ydata(), change)
    assert energy.get_xlabel() == "time (s)"
    assert energy.get_ylabel() == "relative energy change\n(dimensionless)"
