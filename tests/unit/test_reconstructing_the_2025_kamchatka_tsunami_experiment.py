"""The experiment of "Applied capstone: reconstructing the 2025 Kamchatka
tsunami" (fluids 10): the benchmarks hold, every run keeps its volume budget
and a positive depth, the metric of the records is the reference module's,
what the page says of the comparison is what the runs give, and the figures
follow the conventions of a measured-data figure and of a simulated one."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

from pbc.authoring.tables import is_numeric_console_block
from pbc.data import SAMPLES_DIR
from pbc.data.adapters import dart_residual_series
from pbc.data.plotting import check_figure, figure_status
from pbc.data.reference import kamchatka_tsunami
from pbc.experiment import encode
from pbc.fluids.experiments import reconstructing_the_2025_kamchatka_tsunami as capstone

MODULE = "pbc.fluids.experiments.reconstructing_the_2025_kamchatka_tsunami"
PAGE = "fluids/10-reconstructing-the-2025-kamchatka-tsunami"
FIGURES = ("fig-tsunami-benchmarks", "fig-tsunami-map", "fig-tsunami-comparison")


@pytest.fixture(scope="module")
def experiment():
    return capstone.run()


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory, experiment) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("reconstructing_the_2025_kamchatka_tsunami")
    return directory, run_entry_point(MODULE, directory)


def number(experiment, name: str) -> float:
    return float(experiment[name].replace(",", "").replace("+", ""))


def rows(experiment, name: str) -> list[list[str]]:
    return experiment.results()["tables"][name]["rows"]


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_figures_of_the_page_are_the_experiments(experiment):
    assert set(experiment.figures) == set(FIGURES)


def test_the_records_carry_the_status_of_the_card_and_the_correction():
    inputs = kamchatka_tsunami.load(SAMPLES_DIR / capstone.DATASET)
    for station in capstone.STATIONS:
        record = inputs.ncei[station]
        series = dart_residual_series(record)
        assert series.status == "processed" and series.is_raw
        assert series.sigma is None  # no uncertainty per sample is published
        assert np.all(np.diff(series.x) >= 0)
        assert np.allclose(np.sort(series.y), np.sort(record.residual / 0.670))
        assert capstone.measured(station).status == "processed"
    run = capstone.kamchatka_run(capstone.COARSE)
    assert capstone.model_series(run, "21416").status == "simulated"


def test_the_metric_of_a_record_is_the_reference_modules():
    # The page's arrival drops the reference's lower bound (a model may
    # arrive before the window opens); on the records both agree.
    inputs = kamchatka_tsunami.load(SAMPLES_DIR / capstone.DATASET)
    for station in capstone.STATIONS:
        arrival, height, at = capstone.record_metric(station)
        record = inputs.ncei[station]
        window = capstone.WINDOWS[station]
        assert arrival == pytest.approx(
            kamchatka_tsunami.half_peak_time(record, window)
        )
        assert (height, at) == pytest.approx(kamchatka_tsunami.peak(record, window))
    # The dossier's numbers.
    assert capstone.record_metric("21416")[1] == pytest.approx(0.818, abs=0.0005)
    assert capstone.record_metric("21416")[2] == pytest.approx(32.1, abs=0.05)
    assert capstone.record_metric("21415")[1] == pytest.approx(0.352, abs=0.0005)
    assert capstone.record_metric("21415")[2] == pytest.approx(69.1, abs=0.05)


def test_the_half_crest_time_interpolates_the_last_crossing():
    minutes = np.arange(10.0)
    y = np.array([0, 0.6, 0, 0, 0.2, 0.6, 1.0, 0.5, 0, 0])
    # Half the crest is 0.5: crossed upwards at 0.5 (before a dip) and last
    # between 4 and 5, at 4.75.
    assert capstone.half_crest_time(minutes, y, (0.0, 9.0)) == pytest.approx(4.75)


def test_the_benchmarks(experiment):
    assert 0.85 < number(experiment, "order-first") < 1.1
    assert number(experiment, "order-mc") > 1.6
    assert number(experiment, "order-mc") > number(experiment, "order-minmod")
    assert number(experiment, "error-ratio") > 2
    assert number(experiment, "radial-error") < 1e-2
    # The exact solution's crest also runs ahead of sqrt(gh) t.
    radial = rows(experiment, "radial")
    for _, computed, exact, travel, _ in radial:
        assert float(exact) > float(travel)
        assert computed == exact  # the same cell: "lies in the cell"
    assert number(experiment, "cfl-stable") > capstone.COURANT
    assert number(experiment, "cfl-unstable") > number(experiment, "cfl-stable")
    assert [r[3] for r in rows(experiment, "cfl")] == ["yes"] * 4 + ["no"]


def test_every_run_keeps_its_budget_and_a_positive_depth(experiment):
    for factor, options in capstone.RUNS:
        run = capstone.kamchatka_run(factor, **dict(options))
        assert np.max(np.abs(run.budget_residual)) / run.volume[0] < 1e-12
        assert run.min_depth >= 0.0
    assert number(experiment, "run-count") == len(capstone.RUNS)


def test_the_volume_that_leaves_is_what_the_source_displaced(experiment):
    # The two-hour base runs: more than the net uplift of the sea (the trough
    # behind the wave is still inside), within half of it, and changing by
    # less with each refinement.
    left = {r[0]: float(r[3]) for r in rows(experiment, "budget")}
    base = [left[f"{name}, base"] for name in ("32'", "16'", "8'")]
    net = number(experiment, "net-uplift")
    assert all(net < v < 1.5 * net for v in base)
    assert abs(base[2] - base[1]) < abs(base[1] - base[0])
    assert number(experiment, "left-low") == round(min(base))
    assert number(experiment, "left-high") == round(max(base))


def test_a_copied_boundary_drains_through_the_kuril_islands(experiment):
    # The failure mode the page states: tens of times the radiating run's
    # outflow, the surface a hundred metres down at the west edge in the
    # Kuril Islands; in proportion to the source; absent with walls.
    d = capstone.domain(capstone.BASE)
    found = capstone.copied(capstone.Experiment(), d)
    radiating = capstone.kamchatka_run(capstone.BASE).outflow[-1] / 1e9
    assert found["outflow"] > 10 * radiating
    assert found["outflow"] == pytest.approx(number(experiment, "copy-outflow"), abs=1)
    assert found["lowest"] < -100.0 and found["column"] == 0
    assert 46.0 < found["lat"] < 50.0  # the Kuril arc at 153 degrees E
    options = {"threshold": capstone.THRESHOLD, "limiter": capstone.LIMITER}
    small = capstone.tsunami.simulate(
        d.grid,
        capstone.at_rest(d.grid),
        capstone.DURATION,
        capstone.COURANT,
        uplift=0.01 * d.uplift,
        onset=d.onset,
        **options,
    )
    assert small.outflow[-1] / 1e9 == pytest.approx(0.01 * found["outflow"], rel=0.2)
    walls = capstone.tsunami.simulate(
        d.grid,
        capstone.at_rest(d.grid),
        capstone.DURATION,
        capstone.COURANT,
        uplift=d.uplift,
        onset=d.onset,
        open_ends=False,
        **options,
    )
    lifted = capstone.replace(d.grid, bed=d.grid.bed + d.uplift)
    assert np.nanmin(capstone.tsunami.surface(lifted, walls.q)) > -10.0


def test_the_grid_study(experiment):
    study = rows(experiment, "grid-study")
    arrivals = [float(r[2]) for r in study if r[0] == "DART 21416"]
    changes = np.diff(arrivals)
    assert np.all(changes > 0) and np.all(np.diff(changes) < 0)  # later, by less
    crests = {
        s: [float(r[4]) for r in study if r[0] == f"DART {s}"]
        for s in capstone.STATIONS
    }
    for station, values in crests.items():
        growth = np.array(values[1:]) / np.array(values[:-1]) - 1
        assert np.all(growth > 0.3), station  # "does not settle"
    assert number(experiment, "fine-crest") > 1.3


def test_the_sensitivities(experiment):
    assert number(experiment, "boundary-gap-21416") < 30
    assert number(experiment, "boundary-gap-21415") < 30
    assert number(experiment, "near-gap") < 30
    assert number(experiment, "rotation-shift") < 10  # seconds: "small"
    assert number(experiment, "kinematic-shift-21416") > 1.0
    assert number(experiment, "kinematic-shift-21415") > 1.0
    # The edge of the source: cut off instead of tapered, a small effect,
    # and part of the uncertainty table at both stations.
    assert number(experiment, "taper-arrival") < 30  # seconds
    assert number(experiment, "taper-crest") < 10  # per cent
    budget = rows(experiment, "uncertainty")
    for station in capstone.STATIONS:
        assert [f"DART {station}", "source edge (no taper)"] in [r[:2] for r in budget]
    no_taper = capstone.domain(capstone.COARSE, tapered=False).uplift
    tapered = capstone.domain(capstone.COARSE).uplift
    assert np.max(np.abs(no_taper - tapered)) > 0.1  # m: the variant differs


def test_what_the_page_says_of_the_comparison(experiment):
    early = {s: number(experiment, f"early-{s}") for s in capstone.STATIONS}
    spread = {s: number(experiment, f"spread-a-{s}") for s in capstone.STATIONS}
    # Early at both; within the spread at 21416 (8' and 4'), beyond it at 21415.
    assert all(v > 0 for v in early.values())
    assert early["21416"] < spread["21416"]
    assert 0 < number(experiment, "best-early-21416") < spread["21416"]
    assert early["21415"] > spread["21415"]
    # ... while the arrival at 21415 still moved by about two minutes.
    study = rows(experiment, "grid-study")
    last_21415 = [float(r[3]) for r in study if r[0] == "DART 21415" and r[3]][-1]
    assert 1.5 < last_21415 < 2.5
    # The crest: within a fifth on 8' at 21416 (the self-check), well above
    # on 4'; the 21415 match on 8' with a crest that grew in the last
    # refinement.
    assert 80 <= number(experiment, "ratio-21416") <= 120
    assert number(experiment, "best-ratio-21416") > 150
    assert 85 <= number(experiment, "ratio-21415") <= 115
    assert number(experiment, "grid-crest-21415") > 30
    # The residuals are many times the noise floors, also after the shift.
    for station in capstone.STATIONS:
        floor = number(experiment, f"floor-{station}")
        assert number(experiment, f"rms-{station}") > 5 * floor
        assert number(experiment, f"rms-shift-{station}") > 5 * floor


def test_both_waves_are_a_crest_followed_by_a_trough():
    run = capstone.kamchatka_run(capstone.BASE)
    for station in capstone.STATIONS:
        window = capstone.WINDOWS[station]
        for x, y in (
            (run.t / 60.0, run.records[station]),
            (capstone.measured(station).x, capstone.measured(station).y),
        ):
            inside = (x > window[0]) & (x < window[1])
            k_crest = np.argmax(np.where(inside, y, -np.inf))
            k_trough = np.argmin(np.where(inside, y, np.inf))
            assert x[k_crest] < x[k_trough], station


@pytest.mark.parametrize("minutes", (*capstone.PERIODS, 60.0, 0.5))
@pytest.mark.parametrize("depth", (4720.0, 5788.0, 50.0))
def test_the_wavenumber_solves_the_dispersion_relation(minutes, depth):
    # Independently: Newton's method on k tanh(kh) = omega^2 / g from the
    # deep-water root, in exact steps; and the limits of shallow and deep water.
    g, omega = capstone.GRAVITY, 2 * np.pi / (60.0 * minutes)
    k = max(omega**2 / g, omega / np.sqrt(g * depth))
    for _ in range(100):
        t = np.tanh(k * depth)
        k -= (k * t - omega**2 / g) / (t + k * depth * (1 - t * t))
    assert capstone.wavenumber(omega, depth) == pytest.approx(k, rel=1e-12)
    if k * depth < 0.05:
        assert k == pytest.approx(omega / np.sqrt(g * depth), rel=1e-3)
    if k * depth > 5:
        assert k == pytest.approx(omega**2 / g, rel=1e-3)


def test_dispersion_and_rotation(experiment):
    assert number(experiment, "dispersion-long") < 1.0
    assert number(experiment, "dispersion-short") >= 5
    assert number(experiment, "inertial-period") > 10


@pytest.mark.parametrize("label", FIGURES)
def test_every_figure_is_the_same_bytes_on_every_draw(experiment, label):
    drawings = {encode(experiment.figures[label]) for _ in range(8)}
    assert len(drawings) == 1


def test_the_figures_follow_the_conventions(experiment):
    comparison = experiment.figures["fig-tsunami-comparison"]()
    figure_map = experiment.figures["fig-tsunami-map"]()
    try:
        assert figure_status(comparison) == "processed"
        assert check_figure(comparison, residuals=True) == []
        texts = [
            t.get_text()
            for ax in comparison.axes
            if ax.get_legend() is not None
            for t in ax.get_legend().get_texts()
        ]
        assert any(t.startswith("record [processed]") for t in texts)
        assert all(
            "[simulated]" in t for t in texts if t.startswith("model") and "[" in t
        )
        assert figure_status(figure_map) == "simulated"
        assert check_figure(figure_map) == []
    finally:
        plt.close(comparison)
        plt.close(figure_map)


def test_no_printed_output_is_a_block_of_numbers(experiment):
    for name, text in experiment.outputs.items():
        assert not is_numeric_console_block(text), name


def test_the_figures_leave_room_in_the_payload_budget_of_the_page(results):
    # The figures of a page with measured data stay below 525,000 bytes
    # (0.7 of the 0.75 MB the labs keep of the page's 3 MB): the Linux
    # build in CI comes out up to 17 % larger than the local one, so the
    # local total is kept at most 82 % of the bound (W7, FL8, MAT5).
    directory, _ = results
    total = sum(p.stat().st_size for p in directory.glob("fig-*.png"))
    assert total < 525_000, total
