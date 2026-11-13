"""The experiment of "Galaxy rotation curves lab" (astrophysics 10): what the
page claims is what the committed sample gives, the fits are the dossier's,
the stated uncertainties' assumptions are checked on the data, and the
figures follow the conventions of a measured-data lab."""

import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from support.experiments import (
    assert_the_page_and_the_results_agree,
    page_of,
    run_entry_point,
)

from pbc.astrophysics.experiments import galaxy_rotation_curves as lab
from pbc.authoring.tables import is_numeric_console_block
from pbc.data.adapters import rotation_curve_series
from pbc.data.plotting import check_figure, figure_status
from pbc.data.reference import sparc_rotmod
from pbc.experiment import encode

MODULE = "pbc.astrophysics.experiments.galaxy_rotation_curves"
PAGE = "astrophysics/10-galaxy-rotation-curves"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("galaxy_rotation_curves")
    return directory, run_entry_point(MODULE, directory)


@pytest.fixture(scope="module")
def experiment():
    return lab.run()


@pytest.fixture(scope="module")
def sample():
    return lab.load_sample()


def _number(found: dict, name: str) -> float:
    return float(found["numbers"][name].replace(",", ""))


def _rows(found: dict, table: str) -> list[list[str]]:
    return found["tables"][table]["rows"]


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_no_section_id_equals_a_cell_label():
    # Both become id="..." on the page (pitfall 8 of the labs).
    page = page_of(PAGE)
    sections = set(re.findall(r"\{#([a-z0-9-]+)\}", page))
    labels = set(re.findall(r"^#\|\s*label:\s*([a-z0-9-]+)\s*$", page, re.MULTILINE))
    assert labels and sections
    assert not sections & labels


def test_the_series_carries_the_status_of_the_card(sample):
    galaxy = sample["NGC3198"]
    series = rotation_curve_series(galaxy)
    assert series.artifact == "processed-measured"
    assert series.status == "processed"
    assert (series.x_unit, series.y_unit) == ("kpc", "km/s")
    assert np.array_equal(series.sigma, galaxy.v_err)
    assert np.array_equal(series.y, galaxy.v_obs)


def test_the_record_is_what_the_observational_claim_says(results):
    _, found = results
    assert _number(found, "points") == 212
    assert (_number(found, "radius-low"), _number(found, "radius-high")) == (
        0.16,
        63.64,
    )
    assert (_number(found, "errv-low"), _number(found, "errv-high")) == (0.20, 35.90)
    rows = _rows(found, "record")
    assert [r[0] for r in rows] == [
        "NGC 3198",
        "NGC 2403",
        "NGC 2841",
        "DDO 154",
        "NGC 2903",
    ]
    assert [r[2] for r in rows] == ["43", "73", "50", "12", "34"]
    assert [r[-1] for r in rows].count("yes") == 1  # "only one galaxy has a bulge"


def test_the_model_check_is_the_shell_sum(results):
    _, found = results
    assert found["numbers"]["check-bound"] == "1e-9"
    rows = _rows(found, "model-check")
    assert len(rows) == 8
    assert all(cell == "below 1e-9" for row in rows for cell in row[3:])


def test_the_fits_are_the_dossiers(results):
    _, found = results
    fits = {(r[0], r[1]): r for r in _rows(found, "fits")}
    # The dossier's table: Y and chi2/dof of each model with errV.
    expected = {
        ("NGC 3198", "baryons only"): ("1.33", "235.38"),
        ("NGC 3198", "NFW halo"): ("0.45", "1.39"),
        ("NGC 3198", "isothermal halo"): ("0.52", "1.24"),
        ("NGC 2403", "NFW halo"): ("0.29", "9.14"),
        ("NGC 2403", "isothermal halo"): ("0.76", "10.70"),
        ("NGC 2841", "isothermal halo"): ("1.09", "1.34"),
        ("DDO 154", "baryons only"): ("18.93", "1026.42"),
        ("DDO 154", "NFW halo"): ("0.00", "8.73"),
        ("DDO 154", "isothermal halo"): ("0.06", "2.19"),
        ("NGC 2903", "NFW halo"): ("0.22", "5.95"),
        ("NGC 2903", "isothermal halo"): ("0.30", "6.23"),
    }
    for key, (y, chi2) in expected.items():
        assert (fits[key][2], fits[key][6]) == (y, chi2), key
    assert fits[("DDO 154", "NFW halo")][3] == "at the bound"
    # The claims about them.
    assert (_number(found, "none-low"), _number(found, "none-high")) == (175, 1026)
    assert (_number(found, "short-low"), _number(found, "short-high")) == (31, 44)
    assert (_number(found, "good-low"), _number(found, "good-high")) == (1.2, 1.4)
    assert _number(found, "halo-high") == 10.7
    halo = [float(r[6]) for r in fits.values() if r[1] != "baryons only"]
    assert max(halo) == pytest.approx(_number(found, "halo-high"), abs=0.05)
    assert (_number(found, "y-rho-low"), _number(found, "y-rho-high")) == (
        -0.98,
        -0.84,
    )


def test_ngc_3198_without_a_halo_overshoots_inside_and_falls_short_outside(results):
    _, found = results
    assert _number(found, "n3198-y") == 1.33
    assert (_number(found, "n3198-over-low"), _number(found, "n3198-over-high")) == (
        16,
        22,
    )
    assert _number(found, "n3198-over-sigma") >= 3
    assert _number(found, "n3198-short") == 63
    assert _number(found, "ddo-none-y") == 19


def test_the_residuals_are_correlated(results, sample):
    _, found = results
    rhos = [float(r[7]) for r in _rows(found, "fits")]
    assert len(rhos) == 15
    band = _number(found, "band-high")
    # "in all fifteen fits" the correlation lies outside the widest band.
    assert min(rhos) > band
    assert (_number(found, "rho-low"), _number(found, "rho-high")) == (0.60, 0.97)
    assert band == pytest.approx(2 / np.sqrt(12), abs=0.005)
    assert _number(found, "band-low") == pytest.approx(2 / np.sqrt(73), abs=0.005)


def test_the_baryons_alone_fail_under_every_variant(results):
    _, found = results
    rows = _rows(found, "robustness")
    assert len(rows) == 7
    none = [float(r[1]) for r in rows]
    ratio = [float(r[3]) for r in rows]
    systematic = [float(r[1]) for r in rows if "floor" not in r[0]]
    assert min(systematic) >= _number(found, "robust-none-systematic") == 167
    assert min(none) == _number(found, "robust-none") == 5.2
    assert min(ratio) >= _number(found, "robust-ratio") == 9


def test_cusp_and_core(results):
    _, found = results
    assert (_number(found, "ddo-miss-1"), _number(found, "ddo-miss-2")) == (4.0, 3.7)
    assert (
        _number(found, "ddo-miss-1-sigma"),
        _number(found, "ddo-miss-2-sigma"),
    ) == (2.5, 4.6)
    rows = _rows(found, "robustness")
    ratios = [float(r[4]) / float(r[5]) for r in rows]
    assert min(ratios) >= _number(found, "cusp-core-low") >= 3.8
    # "with a ten per cent floor both fall below one"
    assert _number(found, "floor10-cusp") < 1 and _number(found, "floor10-core") < 1
    assert _number(found, "ddo-gas-share") == 12
    # The bar: without the inner points NGC 2903 prefers the cusp.
    assert _number(found, "bar-left-out") == 3
    assert (_number(found, "bar-low"), _number(found, "bar-high")) == (64, 70)
    assert _number(found, "bar-cusp") < 1 < _number(found, "bar-core")
    assert _number(found, "bar-max-disk") == 0.07


def test_the_mass_to_light_ratio_is_degenerate(results):
    _, found = results
    assert (_number(found, "n2403-y-cusp"), _number(found, "n2403-y-core")) == (
        0.29,
        0.76,
    )
    assert _number(found, "n2403-y-low") == 0.08
    # Both valleys are almost equally deep: "nearly the same residuals".
    assert _number(found, "n2403-low-chi2") / _number(found, "n2403-high-chi2") < 1.2
    assert _number(found, "n2403-y-core") < _number(found, "n2403-max-disk") == 0.86
    assert (
        _number(found, "n2403-y-cusp-floor"),
        _number(found, "n2403-y-core-floor"),
    ) == (0.50, 0.84)
    assert (_number(found, "y-core-low"), _number(found, "y-core-high")) == (0.61, 0.94)
    # "at the galaxy's maximum disk"
    assert abs(_number(found, "n2841-y") - _number(found, "n2841-max-disk")) < 0.05


def test_the_variants_scale_the_galaxy_as_stated(sample):
    galaxy = sample["NGC2841"]
    far = lab.at_distance(galaxy, 1.25)
    assert far.radius == pytest.approx(1.25 * galaxy.radius)
    assert far.v_disk == pytest.approx(np.sqrt(1.25) * galaxy.v_disk)
    assert np.array_equal(far.v_obs, galaxy.v_obs)
    tilted = lab.scaled_speed(galaxy, 0.9)
    assert tilted.v_obs == pytest.approx(0.9 * galaxy.v_obs)
    assert tilted.v_err == pytest.approx(0.9 * galaxy.v_err)
    trimmed = lab.outside(sample["NGC2903"], lab.BAR_RADIUS)
    assert trimmed.radius.min() > lab.BAR_RADIUS
    assert trimmed.radius.size == sample["NGC2903"].radius.size - 3


def test_the_reference_module_gives_the_same_fits(sample):
    ours = lab.fit_all(sample["NGC3198"])
    theirs = sparc_rotmod.analyse({"NGC3198": sample["NGC3198"]})["fits"]
    for halo in sparc_rotmod.HALOS:
        assert ours[halo].reduced_chi2 == theirs[("NGC3198", halo, 0.0)].reduced_chi2


def test_the_exercises(experiment):
    distance = experiment.output("distance-exercise")
    ys = [float(v) for v in re.findall(r"core fit: Y = ([\d.]+)", distance)]
    assert len(ys) == 2
    assert ys[1] / ys[0] == pytest.approx(1 / 1.25, rel=0.03)  # "about 1/k"
    mass = experiment.output("mass-exercise")
    share = int(re.search(r"share of the baryons: (\d+)%", mass).group(1))
    assert share < 50  # "most of the mass gives no light"


@pytest.mark.parametrize("label", sorted(lab.run().figures))
def test_every_figure_is_the_same_bytes_on_every_draw(experiment, label):
    drawings = {encode(experiment.figures[label]) for _ in range(12)}
    assert len(drawings) == 1


@pytest.mark.parametrize("label", sorted(lab.run().figures))
def test_every_figure_follows_the_conventions(experiment, label):
    figure = experiment.figures[label]()
    try:
        assert figure_status(figure) == "processed"
        residuals = label != "fig-curves"
        assert check_figure(figure, residuals=residuals) == []
        for ax in figure.axes:
            legend = ax.get_legend()
            for t in [] if legend is None else legend.get_texts():
                if "measured" in t.get_text():
                    assert "[processed]" in t.get_text(), (label, t.get_text())
    finally:
        plt.close(figure)


def test_no_printed_output_is_a_block_of_numbers(experiment):
    for name, text in experiment.outputs.items():
        assert not is_numeric_console_block(text), name


def test_the_figures_leave_room_in_the_payload_budget_of_the_page(results):
    # The Linux build in CI came out up to 17 % larger than the local one
    # (W7); locally these are about 0.41 MB.
    directory, _ = results
    total = sum(p.stat().st_size for p in directory.glob("fig-*.png"))
    assert total < 525_000, total
