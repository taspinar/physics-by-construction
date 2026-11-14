"""The experiment of "RLC circuit measurements lab" (electromagnetism 08):
what the page claims is what the committed sample gives, the fit is the
dossier's, and the figures follow the conventions of a measured-data lab."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point
from support.figures import assert_declared

from pbc.authoring.tables import is_numeric_console_block
from pbc.data import SAMPLES_DIR
from pbc.data.plotting import check_figure, figure_status
from pbc.data.reference import bayreuth_rlc
from pbc.electromagnetism.experiments import rlc_circuit_measurements as lab

MODULE = "pbc.electromagnetism.experiments.rlc_circuit_measurements"
PAGE = "electromagnetism/08-rlc-circuit-measurements"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("rlc_circuit_measurements")
    return directory, run_entry_point(MODULE, directory)


@pytest.fixture(scope="module")
def experiment():
    return lab.run()


def _number(found: dict, name: str) -> float:
    return float(found["numbers"][name])


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_closed_forms_agree_with_the_search(results):
    _, found = results
    assert found["numbers"]["closed-form-gap"] == "below 1e-9"
    rows = {
        row[0]: row for row in found["tables"]["characteristic-frequencies"]["rows"]
    }
    zero = float(rows["phase of Z zero"][1])
    peak = float(rows["largest |Z|"][2])
    f0 = float(rows["1/(2 pi sqrt(LC)), undamped"][1])
    # The claim: the largest |Z| lies between the phase zero and f0.
    assert zero < peak < f0


def test_the_fit_is_the_dossiers_fit():
    # Two implementations of the same fit, the lab's through the circuits
    # module and the reference figure's of the dossier, give the same values.
    spectrum = lab.load_spectrum()
    ours = lab.fit_impedance(spectrum)
    theirs = bayreuth_rlc.fit(bayreuth_rlc.load(SAMPLES_DIR / lab.DATASET))
    np.testing.assert_allclose(ours.params, theirs.params, rtol=1e-6)
    np.testing.assert_allclose(ours.stderr, theirs.stderr, rtol=1e-4)
    assert ours.ok


def test_the_fitted_values_and_their_standard_errors_are_those_of_the_claim(results):
    _, found = results
    # The dossier's values: R = 9.537 +- 0.021 ohm, L = 4.849 +- 0.007 mH,
    # C = 2.1832 +- 0.0031 uF.
    assert _number(found, "r-fit") == pytest.approx(9.537, abs=1e-3)
    assert _number(found, "l-fit") == pytest.approx(4.849, abs=1e-3)
    assert _number(found, "c-fit") == pytest.approx(2.183, abs=1e-3)
    assert _number(found, "r-err") == pytest.approx(0.021, abs=1e-3)
    # Each within the factory tolerance of its printed value, as claimed.
    assert _number(found, "largest-distance") < 100 * lab.TOLERANCE
    assert found["numbers"]["fit-warnings"] == "none"


def test_the_three_frequencies_of_the_model_are_apart_from_the_measured_sample(
    results,
):
    _, found = results
    assert _number(found, "fit-f0") == pytest.approx(1546.9, abs=0.1)
    assert _number(found, "fit-peak") == pytest.approx(1546.3, abs=0.1)
    assert _number(found, "fit-zero") == pytest.approx(1514.9, abs=0.1)
    assert _number(found, "peak-frequency") == pytest.approx(1584.5, abs=0.1)
    # The highest sample is less than one step of the sweep from the model's
    # peak (the page says so), and the phase turns between its two
    # neighbours around the peak.
    step = _number(found, "step")
    assert 0 < _number(found, "peak-above-model") < step
    assert _number(found, "turn-low") < _number(found, "fit-zero")
    assert _number(found, "fit-peak") < _number(found, "turn-high")
    assert _number(found, "turn-high") == _number(found, "peak-frequency")


def test_the_residuals_are_structured_and_the_printed_values_miss_more(results):
    _, found = results
    assert _number(found, "rms") == pytest.approx(1.1, abs=0.05)
    assert _number(found, "worst") == pytest.approx(4.3, abs=0.05)
    # Largest next to the resonance, smallest well below it.
    assert 1400 < _number(found, "worst-at") < 1700
    assert _number(found, "residual-min-at") < 1000
    assert _number(found, "printed-rms") > 3 * _number(found, "rms")


def test_the_band_fits_differ_by_many_standard_errors(results):
    _, found = results
    rows = found["tables"]["band-sensitivity"]["rows"]
    assert [int(row[1]) for row in rows] == [81, 48, 33]
    r_below, r_above = _number(found, "band-r-below"), _number(found, "band-r-above")
    # The claim: many standard errors apart, R most, f0 least.
    assert r_above - r_below > 10 * _number(found, "r-err")
    assert r_above > r_below
    assert _number(found, "band-f0-spread") < 1.0

    def spread(column: int) -> float:
        values = [float(row[column]) for row in rows]
        return (max(values) - min(values)) / min(values)

    # R moves most of R, L, C and the resonance, the resonance least.
    assert spread(3) > max(spread(4), spread(5), spread(2))
    assert spread(2) < min(spread(3), spread(4), spread(5))


def test_only_the_pilot_figure_declares_its_provenance(experiment):
    # Issue #524: the impedance fit opts in, processed measurement with
    # simulated models, under a CC BY card that requires a visible credit.
    assert experiment.provenance == {"fig-impedance-fit": lab.IMPEDANCE_FIT}
    assert lab.IMPEDANCE_FIT.combines == ("simulated",)


@pytest.mark.parametrize("label", sorted(lab.run().figures))
def test_every_figure_is_processed_measurement_and_follows_the_conventions(
    experiment, label
):
    figure = experiment.figures[label]()
    try:
        residuals = label == "fig-impedance-fit"
        if label in experiment.provenance:
            # Issue #524: the declared figure states its status at the caption
            # and in its PNG; its legend entries carry roles, not status words.
            assert_declared(experiment, label, figure, "processed", residuals)
            return
        assert figure_status(figure) == "processed"
        assert check_figure(figure, residuals=residuals) == []
        for ax in figure.axes:
            legend = ax.get_legend()
            for t in [] if legend is None else legend.get_texts():
                text = t.get_text()
                if text.startswith("measured"):
                    assert "[processed]" in text, (label, text)
                if text.startswith("model") and "[" in text:
                    assert "[simulated]" in text, (label, text)
    finally:
        plt.close(figure)


def test_no_printed_output_is_a_block_of_numbers(experiment):
    for name, text in experiment.outputs.items():
        assert not is_numeric_console_block(text), name


def test_the_figures_leave_room_in_the_payload_budget_of_the_page(results):
    # The page budget is 3 MB; the gravitational-wave and the flume labs
    # keep their figures under 0.75 MB, and so does this one.
    directory, _ = results
    total = sum(p.stat().st_size for p in directory.glob("fig-*.png"))
    assert total < 750_000, total
