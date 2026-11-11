"""The experiment of "Quantum measurement statistics lab" (quantum 07)."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

from pbc.data.plotting import check_figure
from pbc.quantum.experiments import quantum_measurement_statistics as experiment

MODULE = "pbc.quantum.experiments.quantum_measurement_statistics"
PAGE = "quantum/07-quantum-measurement-statistics"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("quantum_measurement_statistics")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_published_values_are_reproduced_with_the_stopping_rule(results):
    """The correlators and S of the first 5000 events of each state are the
    paper's, and the standard-error count assumes independence: 6.7 pooled."""
    _, found = results
    numbers = found["numbers"]
    for key, name in (("Psi-", "minus"), ("Psi+", "plus"), ("pooled", "pooled")):
        s, err = experiment.PUBLISHED_S[key]
        assert numbers[f"s-{name}"] == f"{s:.3f}"
        assert numbers[f"e-{name}"] == f"{err:.3f}"
        assert numbers[f"published-{name}"] == numbers[f"s-{name}"]
    assert numbers["sigmas-pooled"] == "6.7"
    rows = found["tables"]["counts"]["rows"]
    assert len(rows) == 8 and sum(int(r[2]) for r in rows) == 10000
    figure_3 = [-0.511, -0.615, 0.608, -0.507, -0.535, -0.603, -0.603, 0.463]
    assert [float(r[5]) for r in rows] == pytest.approx(figure_3, abs=5e-4)
    # The counts of equal and unequal outcomes give the correlator back.
    for r in rows:
        n, equal, unequal = int(r[2]), int(r[3]), int(r[4])
        assert equal + unequal == n
        assert (equal - unequal) / n == pytest.approx(float(r[5]), abs=5e-4)


def test_the_selections_of_the_run_do_not_make_the_violation(results):
    _, found = results
    numbers = found["numbers"]
    rows = {r[0]: r for r in found["tables"]["chsh"]["rows"]}
    archive = rows["both states, whole archive"]
    added = rows["both states, archive with the excluded attempts"]
    assert int(archive[1]) == 10201 and int(added[1]) == 10201 + 13
    error = float(archive[3])
    assert abs(float(added[2]) - float(archive[2])) < 0.05 * error
    assert float(numbers["shift-in-errors"]) < 0.05
    assert all(float(r[4]) > 4 for r in rows.values())
    assert numbers["after-stop"] == "201" and numbers["excluded-pairs"] == "13"


def test_the_one_parameter_model_is_rejected_and_the_two_parameter_one_describes(
    results,
):
    """The Q5 model (visibility alone) has a reduced chi-square far above one
    on three degrees of freedom; with the basis offset both states are
    described, the offsets agree, and the model's S is the measured one."""
    _, found = results
    numbers = found["numbers"]
    for row in found["tables"]["fit-one"]["rows"]:
        assert float(row[4]) > 3 and row[5] == "the chi-square"
        assert 0.7 < float(row[1]) < 0.9  # above the threshold 1/sqrt(2)
    two = {row[0]: row for row in found["tables"]["fit-two"]["rows"]}
    for state, name in (("Psi-", "minus"), ("Psi+", "plus")):
        row = two[state]
        v, v_err = float(row[1]), float(row[2])
        offset, offset_err = float(row[3]), float(row[4])
        s_model, s_model_err = float(row[5]), float(row[6])
        assert float(row[7]) < 3 and row[8] in ("nothing", "the chi-square")
        assert v > float(numbers["threshold"]) + 3 * v_err
        assert -8 < offset < -3 and offset_err < 2
        s, err = experiment.PUBLISHED_S[state]
        assert abs(s_model - s) < max(s_model_err, err)
        assert numbers[f"v-{name}"] == row[1] and numbers[f"offset-{name}"] == row[3]
    assert float(numbers["offset-difference"]) < float(numbers["offset-difference-e"])
    assert float(numbers["v-min-minus"]) > float(numbers["threshold"])
    assert float(numbers["v-margin-minus"]) > 3


def test_the_settings_are_balanced_and_the_marginals_carry_no_signal(results):
    _, found = results
    numbers = found["numbers"]
    assert float(numbers["worst-balance"]) < 3
    assert float(numbers["chi2-settings-high"]) < 11.3  # p = 0.01 at 3 dof
    assert float(numbers["worst-signal"]) < 3
    rows = found["tables"]["no-signalling"]["rows"]
    assert len(rows) == 8
    for row in rows:
        difference = float(row[4]) - float(row[3])
        assert difference == pytest.approx(float(row[5]), abs=1e-4)
        assert abs(float(row[7])) < 3


def test_the_exercises_follow_from_the_numbers(results):
    _, found = results
    numbers = found["numbers"]
    # Events for five standard errors scale as the square of the ratio.
    pooled = 10000 * (5 / float(numbers["sigmas-pooled"])) ** 2
    assert int(numbers["events-for-five"]) == pytest.approx(pooled, rel=0.03)
    assert int(numbers["events-for-five-per-state"]) > 5000
    assert numbers["plus-below"] == "160" and numbers["plus-band-clears"] == "295"


def test_every_figure_follows_the_conventions():
    run = experiment.run()
    try:
        assert set(run.figures) == {"fig-run", "fig-correlators", "fig-running-s"}
        for label, draw in run.figures.items():
            fig = draw()
            assert check_figure(fig) == [], label
            assert any("zenodo" in t.get_text().lower() for t in fig.texts), (
                f"{label} carries no attribution"
            )
            plt.close(fig)
    finally:
        plt.close("all")


def test_the_run_takes_the_time_the_page_budget_allows():
    """The whole experiment stays far inside the 30 s warning of a page."""
    import time

    start = time.perf_counter()
    experiment.run()
    assert time.perf_counter() - start < 15
    assert np.isfinite(float(experiment.PUBLISHED_S["pooled"][0]))
