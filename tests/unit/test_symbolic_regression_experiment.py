"""The experiment of "Symbolic regression: a law from simulated data"
(agents-llm 08, D7)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.mechanics.experiments.symbolic_regression"
PAGE = "agents-llm/08-symbolic-regression"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("symbolic_regression")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_small_angle_law_is_recovered_from_clean_data(results):
    _, found = results
    numbers = found["numbers"]

    assert float(numbers["simulation-error"]) < 1e-6
    assert numbers["recovered"] == "recovered"
    assert numbers["chosen"].endswith("L^(1/2) g^(-1/2)")
    assert float(numbers["constant-error"]) < float(numbers["tolerance"])
    assert numbers["consistent-forms"] == "1"
    last = found["tables"]["pareto"]["rows"][-1]
    assert last[1].endswith("L^(1/2) g^(-1/2)") and last[3] == "yes"


def test_the_law_holds_out_of_range_only_at_small_amplitude(results):
    _, found = results

    errors = [abs(float(row[-1])) for row in found["tables"]["held-out"]["rows"]]
    assert max(errors[:2]) < 0.1
    assert errors[2] < errors[3] < errors[4]
    assert errors[4] > 5


def test_one_gravity_leaves_its_exponent_undetermined(results):
    _, found = results
    numbers = found["numbers"]

    rows = found["tables"]["earth-rivals"]["rows"]
    assert numbers["earth-rivals"] == str(len(rows)) == "9"
    assert len({row[1] for row in rows}) == 1
    assert numbers["earth-chosen"].endswith(" L^(1/2)")
    assert float(numbers["moon-error"]) > 50
    assert numbers["units-forms"] == "1"
    assert numbers["units-chosen"].endswith("L^(1/2) g^(-1/2)")


def test_a_law_outside_the_grammar_is_reported_as_a_failure(results):
    _, found = results

    assert found["numbers"]["wide-reason"].startswith("no form of the grammar")


def test_noise_removes_the_gravity_near_the_predicted_level(results):
    _, found = results
    numbers = found["numbers"]
    rows = found["tables"]["noise-sweep"]["rows"]
    noise = [float(row[0]) for row in rows]
    right = [int(row[1]) for row in rows]

    assert right[0] == 20 and right[-1] < 5
    assert numbers["rival"] == "L^(1/2)"
    floor = float(numbers["floor"])
    # The switch from the law to the simpler form lies within a factor of two
    # of the prediction.
    switch = next(n for n, r in zip(noise, right, strict=True) if r < 10)
    assert floor / 2 < switch < 2 * floor
    # Where the law is chosen, its constant scatters as the noise over root n
    # (at the smallest noise, the bias of the finite amplitudes dominates).
    for row in rows[1:]:
        if row[2]:
            assert float(row[2]) == pytest.approx(float(row[3]), rel=0.5)
    more = [int(row[1]) for row in found["tables"]["more-samples"]["rows"]]
    assert more[1] > right[noise.index(20.0)]


def test_whole_powers_find_no_law_and_half_and_quarter_powers_find_it(results):
    _, found = results
    numbers = found["numbers"]
    rows = {row[0]: row for row in found["tables"]["grammars"]["rows"]}

    assert list(rows) == ["whole powers", "half powers", "quarter powers"]
    # Whole powers: no consistent form, so no claim, and the reason says so.
    assert rows["whole powers"][2] == "0" and rows["whole powers"][3] == "none"
    assert numbers["whole-reason"].startswith("no form of the grammar")
    # Half and quarter powers choose the small-angle law on the clean periods.
    for name in ("half powers", "quarter powers"):
        assert rows[name][3] == "L^(1/2) g^(-1/2)"
    assert int(numbers["quarter-forms"]) > 12 * int(rows["half powers"][1])


def test_the_richer_grammar_loses_the_law_at_a_lower_noise_as_predicted(results):
    _, found = results
    numbers = found["numbers"]
    rows = found["tables"]["grammar-noise"]["rows"]
    noise = [float(row[0]) for row in rows]
    whole, half, quarter = ([int(row[k]) for row in rows] for k in (1, 2, 3))

    assert set(whole) == {0}
    # The quarter grammar never chooses the law more often than the half one,
    # and less often at some noise: it loses the law sooner.
    assert all(q <= h for q, h in zip(quarter, half, strict=True))
    lost_half = next(n for n, h in zip(noise, half, strict=True) if h < 10)
    lost_quarter = next(n for n, q in zip(noise, quarter, strict=True) if q < 10)
    assert lost_quarter < lost_half
    # It loses it to a form with a fourth root, at about its predicted noise,
    # which is lower than the half grammar's.
    assert "1/4" in numbers["quarter-rival"]
    assert float(numbers["quarter-floor"]) < float(numbers["half-floor"])
    for floor, lost in (
        (numbers["quarter-floor"], lost_quarter),
        (numbers["half-floor"], lost_half),
    ):
        assert float(floor) / 2 < lost < 2 * float(floor)
