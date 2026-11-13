"""The experiment of "Lycopodium diffraction lab" (waves 9): what the page
claims is what the committed sample gives, the ring radii and the halo are
the dossier's, the stated uncertainty's assumptions are checked on the
data, no fitted line stands for a prediction, and the figures follow the
conventions of a measured-data lab."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

from pbc.authoring.tables import is_numeric_console_block
from pbc.data.adapters import luma_profile_series
from pbc.data.plotting import check_figure, figure_status
from pbc.data.reference import lycopodium
from pbc.experiment import encode
from pbc.waves import halo
from pbc.waves.experiments import lycopodium_diffraction_lab as lab

MODULE = "pbc.waves.experiments.lycopodium_diffraction_lab"
PAGE = "waves/09-lycopodium-diffraction-lab"
RED, VIOLET = lab.RED, lab.VIOLET


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("lycopodium_diffraction_lab")
    return directory, run_entry_point(MODULE, directory)


@pytest.fixture(scope="module")
def experiment():
    return lab.run()


@pytest.fixture(scope="module")
def record():
    return lab.load_record()


def _number(found: dict, name: str) -> float:
    return float(found["numbers"][name])


def _column(found: dict, table: str, column: int) -> list[str]:
    return [row[column] for row in found["tables"][table]["rows"]]


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_series_carries_the_status_of_the_card(record):
    profiles, _ = record
    for w, rows in ((RED, 2211), (VIOLET, 932)):
        series = luma_profile_series(profiles[w])
        assert series.artifact == "processed-measured"
        assert series.status == "processed"
        assert series.sigma is None  # the record gives no uncertainty
        assert series.x.size == rows
        assert "not stated" in series.x_unit


def test_the_diameters_are_the_dossiers(results):
    _, found = results
    assert _column(found, "diameters", 1) == ["150", "642"]
    assert _column(found, "diameters", 2) == ["72", "605"]
    assert _column(found, "diameters", 3) == ["29.91", "30.36"]
    assert _column(found, "diameters", 4) == ["0.34", "0.13"]
    assert _number(found, "mean-gap-sigma") == 1.2
    assert _number(found, "spread") == 10


def test_the_halo_is_the_closed_form_and_the_dossiers_model(results, record):
    _, found = results
    # Built from the wavelet integral of the diffraction lesson, the halo is
    # the closed form of the reference module to a few millionths.
    assert _number(found, "model-millionths") < 5
    for _, zero, one_disk, *_ in found["tables"]["rings"]["rows"]:
        assert one_disk == zero  # to the four decimals shown
    _, tables = record
    d = lycopodium.whole_spores(tables["x160"])
    # The reference module takes the grid's extreme sample; the lab refines
    # it, so the two agree to the grid's step.
    ours, theirs = halo.extrema(d), lycopodium.model_extrema(d)
    step = 6.0 / d.mean() / 30000
    for a, b in zip(ours, theirs, strict=True):
        np.testing.assert_allclose(a, b, atol=step)
    assert _number(found, "model-first") == 1.232
    assert _number(found, "model-second") == 2.231
    # The spread of sizes fills the first dark ring a little.
    assert 0.1 < _number(found, "fill") < 1


def test_the_profiles_are_what_the_observational_claim_says(results):
    _, found = results
    assert found["numbers"]["red-rows"] == "2,211"
    assert found["numbers"]["violet-rows"] == "932"
    assert _number(found, "red-saturated") == 37
    assert _number(found, "violet-saturated") == 57
    assert _number(found, "red-centre") == 1.245
    assert _number(found, "violet-centre") == 0.075
    # The core is smaller than the dark ring by far.
    assert _number(found, "red-core") < _number(found, "red-ring") / 5
    assert _number(found, "violet-core") < _number(found, "violet-ring") / 4


def test_the_rings_and_their_ranges_are_the_dossiers(results, record):
    _, found = results
    profiles, _ = record
    # The dossier: 16.68 +- 0.34 and 11.02 +- 0.33 in units of x; 0.661 +- 0.024.
    assert found["numbers"]["red-ring"] == "16.68"
    assert found["numbers"]["red-ring-range"] == "0.34"
    assert found["numbers"]["violet-ring"] == "11.02"
    assert found["numbers"]["violet-ring-range"] == "0.33"
    assert found["numbers"]["ratio"] == "0.661"
    assert found["numbers"]["ratio-range"] == "0.024"
    value, error = lycopodium.ratio(profiles)
    assert _number(found, "ratio") == pytest.approx(value, abs=5e-4)
    assert _number(found, "ratio-range") == pytest.approx(error, abs=5e-4)
    for w, column in ((RED, 1), (VIOLET, 2)):
        radii = [f"{r:.2f}" for r in lycopodium.ring(profiles[w]).radii]
        assert _column(found, "ring-radii", column) == radii


def test_the_ratio_claim_against_a_prediction_that_is_not_fitted(results):
    _, found = results
    predicted = _number(found, "predicted")
    # The prediction comes from the two wavelengths alone, not from the radii.
    assert predicted == pytest.approx(0.405 / 0.6328, abs=2e-4)
    assert predicted == pytest.approx(
        halo.radius_ratio(1.232 / 29.9075, VIOLET, RED), abs=1e-4
    )
    ratios = [float(r) for r in _column(found, "ring-radii", 3)]
    assert min(ratios) == _number(found, "ratio-low") == 0.642
    assert max(ratios) == _number(found, "ratio-high") == 0.685
    # "Every width gives a ratio at or above the prediction, by 0.3 to 7 %."
    assert all(r >= predicted for r in ratios)
    assert _number(found, "excess-low") == 0.3
    assert _number(found, "excess-high") == 7
    assert _number(found, "flat-screen-shift") < 0.001


def test_the_stated_uncertainty_rests_on_assumptions_checked_on_the_data(
    results, record
):
    _, found = results
    profiles, _ = record
    # The violet radius rises with the smoothing width: a bias, not scatter.
    violet = lycopodium.ring(profiles[VIOLET]).radii
    assert np.all(np.diff(violet) > 0)
    # The red one does not.
    red = lycopodium.ring(profiles[RED]).radii
    assert not np.all(np.diff(red) > 0) and not np.all(np.diff(red) < 0)
    # The red sides agree; the violet right side shows no dip near the ring.
    assert abs(_number(found, "red-left") - _number(found, "red-right")) < 0.15
    assert _number(found, "violet-left") == 10.92
    assert _number(found, "violet-right") > 13.9
    # The ratio at a common width spreads about as much as the propagation
    # of independent ranges says.
    half = _number(found, "ratio-half-range")
    assert half == pytest.approx(_number(found, "ratio-range"), abs=0.005)


def test_the_ring_order_is_as_the_claim_says(results):
    _, found = results
    assert _number(found, "spacing-red") == 1.19
    assert _number(found, "spacing-violet") == 1.11
    assert _number(found, "spacing-order-1") == 1.31
    assert _number(found, "spacing-order-2") == 1.17
    low, high = _number(found, "spacing-low"), _number(found, "spacing-high")
    # Below the first order's spacing at every width, around the second's.
    assert high < _number(found, "spacing-order-1")
    assert low < _number(found, "spacing-order-2") < high


def test_the_screen_distances_are_the_dossiers(results):
    _, found = results
    rows = found["tables"]["screen-distance"]["rows"]
    assert [r[2:] for r in rows] == [["640", "661"], ["353", "365"]]
    assert _number(found, "sin-1") == 0.026 and _number(found, "sin-2") == 0.047


def test_the_exercises(experiment):
    tabletop = experiment.output("tabletop-exercise")
    assert "d = 23.4 um" in tabletop and "d = 42.3 um" in tabletop
    green = experiment.output("green-exercise")
    assert "14.02 units of x" in green


@pytest.mark.parametrize("label", sorted(lab.run().figures))
def test_every_figure_is_the_same_bytes_on_every_draw(experiment, label):
    # The page's figure must be regenerated byte for byte (straight lines are
    # drawn from their two ends, as in MAT6 and T7).
    drawings = {encode(experiment.figures[label]) for _ in range(12)}
    assert len(drawings) == 1


@pytest.mark.parametrize("label", sorted(lab.run().figures))
def test_every_figure_follows_the_conventions(experiment, label):
    figure = experiment.figures[label]()
    try:
        expected = "simulated" if label == "fig-halo-model" else "processed"
        assert figure_status(figure) == expected
        assert check_figure(figure, residuals=label == "fig-scaling") == []
        for ax in figure.axes:
            legend = ax.get_legend()
            for t in [] if legend is None else legend.get_texts():
                text = t.get_text()
                if (
                    "measured" in text
                    and "[simulated]" not in text
                    and "minus" not in text
                ):
                    assert "[processed]" in text, (label, text)
                if "halo of" in text or "one disk" in text:
                    assert "[simulated]" in text, (label, text)
                # Issue #453: nothing fitted to the rings is drawn as a model.
                assert "fit" not in text.replace("no fit", ""), (label, text)
    finally:
        plt.close(figure)


def test_no_printed_output_is_a_block_of_numbers(experiment):
    for name, text in experiment.outputs.items():
        assert not is_numeric_console_block(text), name


def test_the_figures_leave_room_in_the_payload_budget_of_the_page(results):
    # The page budget is 3 MB; the labs keep their figures well under it.
    # Locally these are about 0.45 MB. The Linux build in CI came out 8 %
    # (AST8) to 15 % (T7) larger than the local one, so the bound keeps a
    # margin of more than 15 % over the local total.
    directory, _ = results
    total = sum(p.stat().st_size for p in directory.glob("fig-*.png"))
    assert total < 550_000, total
    assert total < 0.85 * 550_000, total
