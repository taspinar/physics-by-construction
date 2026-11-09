"""The committed dataset samples parse into what their cards say (ADR 007).

Each ``test_*_sample_parses`` is the parsing test that the cards of its
dataset name. The figure tests check the physical consistency that the
feasibility dossiers rely on, on the same samples.
"""

import json

import matplotlib.pyplot as plt
import numpy as np
import pytest

from pbc.data import SAMPLES_DIR
from pbc.data.flume import read_elevation
from pbc.data.gwosc import read_strain
from pbc.data.reference import (
    aalborg_flume,
    bayreuth_rlc,
    gw150914,
    munich_bell,
    npl_sparameters,
    xu_pendulum,
)

GW = SAMPLES_DIR / "gw150914-strain"
NPL = SAMPLES_DIR / "npl-onwafer-sparameters"
AAL = SAMPLES_DIR / "aalborg-submerged-bar"
RLC = SAMPLES_DIR / "bayreuth-rlc-impedance"
BELL = SAMPLES_DIR / "munich-bell-event-ready"
XU = SAMPLES_DIR / "xu-damped-pendulum"


def test_gw150914_sample_parses():
    for detector, file in gw150914.FILES.items():
        strain = read_strain(GW / file)
        assert strain.event == "GW150914_R1"
        assert strain.detector == detector
        # Cadence and span: 32 s at 4096 Hz starting at GPS 1126259447.
        assert strain.sample_rate == 4096.0
        assert strain.gps_start == 1126259447.0
        assert strain.strain.shape == (131072,)
        assert np.median(np.diff(strain.time)) == pytest.approx(1 / 4096)
        # Mask: the text product has none, so no value may be missing.
        assert np.isfinite(strain.strain).all()
        # Units: dimensionless strain of detector noise, about 1e-19.
        assert 1e-20 < strain.strain.std() < 1e-18
        # The event lies inside the segment.
        assert strain.time[0] < gw150914.EVENT_GPS < strain.time[-1]


def test_npl_sample_parses():
    networks = npl_sparameters.load(NPL)
    assert list(networks) == list(npl_sparameters.FILES)
    for name, network in networks.items():
        # Field names: S11 S21 S12 S22 as one 2 x 2 matrix per frequency.
        assert network.s.shape == (len(network.frequency), 2, 2)
        assert network.s.dtype == np.complex128
        assert network.reference_impedance == 50.0
        # Units: Hz, 250 MHz step, starting at 2.5 GHz.
        assert network.frequency[0] == 2.5e9
        np.testing.assert_allclose(np.diff(network.frequency), 250e6)
        assert np.isfinite(network.s).all(), name
    assert networks["coaxial, 3 dB pad"].frequency[-1] == 50e9
    assert len(networks["coaxial, 3 dB pad"].frequency) == 191
    assert networks["single sweep, 3 dB pad"].frequency[-1] == 220e9
    assert len(networks["single sweep, 3 dB pad"].frequency) == 871


def test_aalborg_sample_parses():
    experiment, models = aalborg_flume.load(AAL)
    # Field names: five repetitions, the mean, the expanded uncertainty.
    assert experiment.labels == (
        "rep 1",
        "rep 2",
        "rep 3",
        "rep 4",
        "rep 5",
        "mean",
        "expanded unc",
    )
    assert set(experiment.gauges) == {aalborg_flume.GAUGE}
    assert experiment.values.shape == (4501, 7)
    # Cadence: 150 Hz from 0 to 30 s.
    assert experiment.time[0] == 0.0
    assert experiment.time[-1] == pytest.approx(30.0, abs=1e-3)
    # The time stamps are printed with five significant digits (a resolution of
    # 1 ms after 10 s), so the cadence holds to within half of that.
    index = np.arange(experiment.time.size)
    np.testing.assert_allclose(experiment.time, index / 150, atol=5e-4)
    assert np.isfinite(experiment.values).all()
    # Units: metres, a wave of about 12 mm amplitude; the mean is the mean.
    mean = experiment.column(aalborg_flume.GAUGE, "mean")
    reps = np.stack(
        [experiment.column(aalborg_flume.GAUGE, f"rep {k}") for k in range(1, 6)], 1
    )
    np.testing.assert_allclose(mean, reps.mean(axis=1), atol=2e-6)
    assert 0.010 < np.abs(mean).max() < 0.015
    assert (experiment.column(aalborg_flume.GAUGE, "expanded unc") > 0).all()
    # The three modelled series: one column, own cadence and end, NaN masks.
    cadence = {"i-VoF (OpenFOAM)": 0.01, "M-sigma (MIKE 3)": 0.01}
    ends = {
        "i-VoF (OpenFOAM)": 20.0,
        "M-sigma (MIKE 3)": 30.0,
        "D-SPH (DualSPHysics)": 14.1,
    }
    nans = {"i-VoF (OpenFOAM)": 1, "M-sigma (MIKE 3)": 0, "D-SPH (DualSPHysics)": 1}
    for name, model in models.items():
        assert model.labels == ("surface elevation",)
        assert model.values.shape[1] == 1
        assert model.time[-1] == pytest.approx(ends[name])
        assert int(np.isnan(model.values).sum()) == nans[name]
        if name in cadence:
            np.testing.assert_allclose(np.diff(model.time), cadence[name], atol=1e-9)


def test_aalborg_lab_sample_parses():
    experiment, models = aalborg_flume.load_lab(AAL)
    # Every gauge, each with its own file and the experiment's seven columns.
    assert list(experiment) == list(aalborg_flume.GAUGES) == list(range(1, 21))
    for gauge, record in experiment.items():
        assert set(record.gauges) == {gauge}
        assert record.labels[-2:] == ("mean", "expanded unc")
        # Cadence: 150 Hz from 0 to LAB_END (to 30 s for the gauge of F50).
        end = 30.0 if gauge == aalborg_flume.GAUGE else aalborg_flume.LAB_END
        assert record.values.shape == (round(150 * end) + 1, 7)
        index = np.arange(record.time.size)
        np.testing.assert_allclose(record.time, index / 150, atol=5e-4)
        assert np.isfinite(record.values).all()
        # Units: metres, a wave of about 10 to 20 mm crest; the mean is the mean.
        mean = record.column(gauge, "mean")
        reps = np.stack([record.column(gauge, f"rep {k}") for k in range(1, 6)], 1)
        np.testing.assert_allclose(mean, reps.mean(axis=1), atol=2e-6)
        assert 0.009 < np.abs(mean).max() < 0.025
        assert (record.column(gauge, "expanded unc") > 0).all()
    # The solvers: twenty gauge columns each, own cadence and end, NaN masks.
    ends = {
        "i-VoF (OpenFOAM)": (0.01, 20.0, 1),
        "M-sigma (MIKE 3)": (0.0, aalborg_flume.LAB_END, 0),
        "D-SPH (DualSPHysics)": (0.0, 14.1, 1),
    }
    for name, model in models.items():
        start, end, nans = ends[name]
        assert model.gauges == aalborg_flume.GAUGES
        assert set(model.labels) == {"surface elevation"}
        assert model.time[0] == pytest.approx(start)
        assert model.time[-1] == pytest.approx(end)
        assert (np.isnan(model.values).sum(axis=0) == nans).all()
        assert np.nanmax(np.abs(model.values)) < 0.03
    # The gauge-5 column of each solver equals the sample of F50 where both run.
    _, single = aalborg_flume.load(AAL)
    for name, model in models.items():
        n = min(model.time.size, single[name].time.size)
        np.testing.assert_array_equal(
            model.values[:n, aalborg_flume.GAUGE - 1], single[name].values[:n, 0]
        )


def test_bayreuth_rlc_sample_parses():
    raw = json.loads((RLC / bayreuth_rlc.FILE).read_text())
    # Field names: the Impedance export of the creators' MATLAB package.
    assert tuple(raw) == bayreuth_rlc.FIELDS
    assert raw["class_"] == "Impedance"
    spectrum = bayreuth_rlc.load(RLC)
    # Shapes: 81 points, Z complex.
    assert spectrum.frequency.shape == spectrum.impedance.shape == (81,)
    assert spectrum.impedance.dtype == np.complex128
    for key in ("omega", "z", "z_modulus", "z_phase"):
        assert len(raw[key]) == 81, key
    # Cadence: one sweep, descending, 40 points per decade, 99.97 Hz to 10 kHz.
    f = spectrum.frequency
    assert f[0] == pytest.approx(10002.226) and f[-1] == pytest.approx(99.968163)
    np.testing.assert_allclose(np.diff(np.log10(f)), -0.025, atol=6e-4)
    # Units: omega is 2 pi f (rad/s from Hz), the phase is in radians, and the
    # modulus and the strings are the same Z; ohm, by the size of the coil.
    np.testing.assert_allclose(raw["omega"], 2 * np.pi * f, rtol=1e-12)
    np.testing.assert_allclose(raw["z_modulus"], np.abs(spectrum.impedance))
    np.testing.assert_allclose(raw["z_phase"], np.angle(spectrum.impedance), atol=1e-12)
    strings = np.array([complex(z.replace("i", "j")) for z in raw["z"]])
    np.testing.assert_allclose(strings, spectrum.impedance, atol=1e-4)
    assert 9 < np.abs(spectrum.impedance[-1]) < 11  # the coil at 100 Hz
    # Masks: none.
    assert np.isfinite(spectrum.impedance).all() and np.isfinite(f).all()


def test_the_rlc_fit_recovers_the_nominal_circuit_within_its_tolerance():
    """The EM5 parallel circuit, C parallel to (R + jwL), describes the
    spectrum; each value is within the 10 % factory tolerance of the record's
    nominal one (9.7 Ohm, not the record's 9.7 mOhm), and the fit identifies
    all three."""
    spectrum = bayreuth_rlc.load(RLC)
    result = bayreuth_rlc.fit(spectrum)
    assert result.ok, result.warnings
    for name, nominal in bayreuth_rlc.NOMINAL.items():
        assert result.value(name) == pytest.approx(nominal, rel=0.10), name
    expected = {"R": (9.537, 0.021), "L": (4.849, 0.007), "C": (2.1832, 0.0031)}
    for name, (value, stderr) in expected.items():
        i = result.names.index(name)
        assert result.params[i] == pytest.approx(value, abs=stderr / 4), name
        assert result.stderr[i] == pytest.approx(stderr, rel=0.1), name
    f0, q = bayreuth_rlc.resonance(result)
    assert f0 == pytest.approx(1546.9, abs=0.5)
    assert q == pytest.approx(4.94, abs=0.01)
    # Three frequencies the caption keeps apart: the highest measured |Z| is
    # the first sample above the fit's maximum (one step of the 40-per-decade
    # sweep away), the fit's |Z| peaks just below 1/(2 pi sqrt(LC)), and the
    # fitted phase crosses zero lower still.
    highest = bayreuth_rlc.measured_peak(spectrum)
    assert highest == pytest.approx(1584.49, abs=0.01)
    peak = bayreuth_rlc.model_peak(result)
    assert peak == pytest.approx(1546.3, abs=0.2)
    assert bayreuth_rlc.model_phase_zero(result) == pytest.approx(1514.9, abs=0.2)
    below = spectrum.frequency[spectrum.frequency < peak].max()
    assert below == pytest.approx(1496.43, abs=0.01)
    assert np.log10(highest / below) == pytest.approx(0.025, abs=5e-4)
    phase = np.angle(spectrum.impedance)
    assert (
        phase[spectrum.frequency == below][0]
        > 0
        > phase[spectrum.frequency == highest][0]
    )
    residual = bayreuth_rlc.relative_residual(spectrum, result)
    rms = np.sqrt(np.mean(np.concatenate([residual.real, residual.imag]) ** 2))
    assert rms == pytest.approx(0.0113, abs=0.0005)
    assert np.abs(residual).max() < 0.05


def test_the_rlc_band_split_is_the_sensitivity_table_of_the_dossier():
    """Fits below and above the resonance disagree by far more than their
    standard errors: the residuals are systematic. The dossier reports the
    band fits as a sensitivity analysis beside the full fit, not as a bound;
    the lower band's resonance lies 7 Hz below the full fit's."""
    spectrum = bayreuth_rlc.load(RLC)
    halves = bayreuth_rlc.band_split(spectrum)
    below, above = halves["below"], halves["above"]
    spread = {n: abs(above.value(n) - below.value(n)) for n in bayreuth_rlc.NAMES}
    assert spread["R"] == pytest.approx(0.93, abs=0.01)
    assert spread["L"] == pytest.approx(0.120, abs=0.002)
    assert spread["C"] == pytest.approx(0.072, abs=0.002)
    full = bayreuth_rlc.fit(spectrum)
    for n in bayreuth_rlc.NAMES:
        assert spread[n] > 10 * full.stderr[full.names.index(n)], n
    resonances = [bayreuth_rlc.resonance(h)[0] for h in (below, above)]
    assert resonances == pytest.approx([1539.8, 1546.1], abs=0.2)
    assert bayreuth_rlc.resonance(full)[0] - min(resonances) > 3


def test_a_file_that_is_not_an_impedance_export_is_refused(tmp_path):
    path = tmp_path / "other.json"
    path.write_text('{"class_": "Other", "f": [], "z_real": [], "z_imag": []}')
    with pytest.raises(ValueError, match="Impedance"):
        bayreuth_rlc.read_impedance(path)


def test_munich_bell_sample_parses():
    run = munich_bell.load(BELL)
    pairs, one, two = run.pairs, run.lab_1, run.lab_2
    # Field names: the headers of the three files, each with its delimiter
    # (tab in the pairs file, semicolon in the lab files).
    header = (BELL / munich_bell.PAIRS).read_text().splitlines()[0]
    assert tuple(header.split("\t")) == munich_bell.PAIRS_FIELDS
    for name, fields in (
        (munich_bell.LAB_1, munich_bell.LAB_1_FIELDS),
        (munich_bell.LAB_2, munich_bell.LAB_2_FIELDS),
    ):
        assert tuple((BELL / name).read_text().splitlines()[0].split(";")) == fields
    assert "time (Unix time in ms)" in (BELL / munich_bell.README).read_text()
    # Shapes: 10,201 valid pairs; 10,218 attempts in lab 1, 10,248 in lab 2.
    assert len(pairs) == 10201
    assert one.time_ms.shape == (10218,) and two.time_ms.shape == (10248,)
    assert {s: int((pairs.state == s).sum()) for s in munich_bell.STATES} == {
        "Psi-": 5054,
        "Psi+": 5147,
    }
    # Units and coverage: Unix time in ms, 2016-04-15 14:19:57.751 UTC to
    # 2016-04-19 07:03:43.045 UTC, 3.70 days, in time order.
    assert pairs.time_ms[0] == 1460729997751 and pairs.time_ms[-1] == 1461049423045
    assert (np.diff(pairs.time_ms) > 0).all()
    assert (pairs.time_ms[-1] - pairs.time_ms[0]) / 86400e3 == pytest.approx(
        3.697, abs=1e-3
    )
    # Cadence: no clock, one event per heralding; median 20.5 s between
    # events, three pauses of 1.6 to 1.8 h (the daily maintenance).
    gaps = np.diff(pairs.time_ms) / 1e3
    assert np.median(gaps) == pytest.approx(20.5, abs=0.1)
    assert ((gaps > 3600) & (gaps < 2 * 3600)).sum() == 3 and gaps.max() < 2 * 3600
    # Settings and results are bits.
    for bits in (pairs.a, pairs.x, pairs.b, pairs.y):
        assert set(np.unique(bits)) == {0, 1}
    # Masks: exclusions are in the lab files only, all for maintenance; every
    # pair points to valid rows of both labs that agree with it, within the
    # pairing window of 100 ms. Two valid attempts of lab 2 have no partner.
    assert int(one.excluded.sum()) == 17 and int(two.excluded.sum()) == 45
    assert (
        set(one.comment[one.excluded])
        == set(two.comment[two.excluded])
        == {"Maintenance"}
    )
    assert munich_bell.pairing_problems(run) == []
    assert len(set(pairs.line_1)) == len(set(pairs.line_2)) == len(pairs)
    assert int((~one.excluded).sum()) == 10201 and int((~two.excluded).sum()) == 10203


def test_the_bell_selection_reproduces_the_published_correlators_and_s():
    """The stopping rule fixed before the run, the first 5000 events of each
    state, gives the paper's Fig. 3 correlators and its S values to the digits
    printed: 2.240 +- 0.047 (Psi-), 2.204 +- 0.047 (Psi+), 2.221 +- 0.033
    pooled, 5.1, 4.3, and 6.7 standard errors above 2."""
    pairs = munich_bell.load(BELL).pairs
    selection = munich_bell.published_selection(pairs)
    assert int(selection.sum()) == 10000
    figure_3 = {
        "Psi-": (-0.511, -0.615, 0.608, -0.507),
        "Psi+": (-0.535, -0.603, -0.603, 0.463),
    }
    for state, published in figure_3.items():
        terms = munich_bell.correlators(pairs, state, selection)
        values = [terms[k].value for k in munich_bell.SETTINGS]
        assert values == pytest.approx(published, abs=5e-4), state
        assert sum(terms[k].n for k in munich_bell.SETTINGS) == 5000
    expected = {"Psi-": (2.240, 5.1), "Psi+": (2.204, 4.3)}
    for state, (value, sigmas) in expected.items():
        s, err = munich_bell.chsh(pairs, state, selection)
        assert s == pytest.approx(value, abs=5e-4) and err == pytest.approx(
            0.047, abs=5e-4
        )
        assert munich_bell.significance(s, err) == pytest.approx(sigmas, abs=0.05)
    s, err = munich_bell.chsh_pooled(pairs, selection)
    assert s == pytest.approx(2.221, abs=5e-4) and err == pytest.approx(0.033, abs=5e-4)
    assert munich_bell.significance(s, err) == pytest.approx(6.7, abs=0.05)
    # The pooled S is the mean of the two states' S to rounding: each state
    # has its own sign pattern, and the pooled correlators use them.
    halves = [munich_bell.chsh(pairs, st, selection)[0] for st in munich_bell.STATES]
    assert s == pytest.approx(np.mean(halves), abs=2e-3)


def test_the_whole_bell_archive_and_the_excluded_attempts_change_s_little():
    """The archive holds 201 events beyond the stopping rule; with them S is
    2.2210 +- 0.0329. The 13 maintenance exclusions of lab 1 that have a
    partner in lab 2 within 100 ms, added back, give 2.2201: the exclusion
    does not make the violation."""
    run = munich_bell.load(BELL)
    s, err = munich_bell.chsh_pooled(run.pairs)
    assert s == pytest.approx(2.2210, abs=5e-5) and err == pytest.approx(
        0.0329, abs=5e-5
    )
    per_state = {st: munich_bell.chsh(run.pairs, st)[0] for st in munich_bell.STATES}
    assert per_state == pytest.approx({"Psi-": 2.2462, "Psi+": 2.1977}, abs=5e-5)
    excluded = munich_bell.excluded_pairs(run)
    assert len(excluded) == 13
    assert run.lab_1.excluded[excluded.line_1].all()
    assert run.lab_2.excluded[excluded.line_2].all()
    s_all, _ = munich_bell.chsh_pooled(munich_bell.combine(run.pairs, excluded))
    assert s_all == pytest.approx(2.2201, abs=5e-5)
    assert abs(s_all - s) < 0.1 * err


def test_the_running_bell_s_ends_at_the_whole_state_value():
    pairs = munich_bell.load(BELL).pairs
    for state in munich_bell.STATES:
        s, err = munich_bell.running_chsh(pairs, state)
        assert s.size == int((pairs.state == state).sum()) - 39
        assert s[-1] == pytest.approx(munich_bell.chsh(pairs, state)[0])
        assert err[-1] == pytest.approx(munich_bell.chsh(pairs, state)[1])
        assert np.isfinite(s).all() and (np.diff(err[100:]) < 0.01).all()
    # The caption: from the 40th event on, S of Psi- never falls below 2, S of
    # Psi+ once (its 160th event), and the band of Psi+ clears 2 from its
    # 295th event on.
    s, err = munich_bell.running_chsh(pairs, "Psi-")
    assert (s > 2).all()
    s, err = munich_bell.running_chsh(pairs, "Psi+")
    n = np.arange(40, 40 + s.size)
    assert list(n[s < 2]) == [160]
    assert n[s - err < 2].max() == 294


def test_a_bell_file_with_another_header_or_state_is_refused(tmp_path):
    good = (BELL / munich_bell.PAIRS).read_text().splitlines()
    path = tmp_path / "pairs.csv"
    path.write_text("\n".join([good[0].replace("\t", ";"), *good[1:3]]) + "\n")
    with pytest.raises(ValueError, match="header"):
        munich_bell.read_pairs(path)
    path.write_text("\n".join([good[0], good[1].replace("Psi-", "Phi+")]) + "\n")
    with pytest.raises(ValueError, match="Bell state"):
        munich_bell.read_pairs(path)


def test_the_reader_of_a_flume_file_refuses_a_file_without_a_time_column(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text(",1\nx [s],surface elevation [m]\n0,0.1\n")
    with pytest.raises(ValueError, match="time"):
        read_elevation(path)


def test_the_sample_is_passive_and_reciprocal():
    """A passive two-port has no singular value of S above 1 (energy cannot be
    created), and these passive pads are reciprocal: S21 equals S12."""
    for name, network in npl_sparameters.load(NPL).items():
        assert npl_sparameters.largest_singular_value(network).max() <= 1.0, name
        tolerance = 5e-2 if "single" in name else 5e-3
        assert npl_sparameters.reciprocity_error(network).max() < tolerance, name


def test_the_attenuators_attenuate_in_the_order_they_are_labelled():
    networks = npl_sparameters.load(NPL)
    loss = {
        pad: -npl_sparameters.db(networks[f"coaxial, {pad} dB pad"].s[:, 1, 0]).mean()
        for pad in (3, 6, 10)
    }
    assert loss[3] < loss[6] < loss[10]
    for pad, measured in loss.items():
        assert measured == pytest.approx(pad, abs=1.0)


def test_two_instruments_agree_on_the_same_pad():
    networks = npl_sparameters.load(NPL)
    _, difference = npl_sparameters.cross_check_db(
        networks["single sweep, 3 dB pad"], networks["coaxial, 3 dB pad"]
    )
    assert np.abs(difference).max() < 0.1  # dB; the spike measured 0.042 dB


def test_the_strain_gives_the_published_signal():
    """The two detectors see a chirp of the published mass at the published
    delay. A leading-order template overestimates the chirp mass, so the fitted
    value is expected above the published one and within 25 % of it."""
    strains = gw150914.load(GW)
    fit = gw150914.fit_chirp_mass(strains, np.arange(20.0, 56.0, 2.0))
    published = gw150914.PUBLISHED_CHIRP_MASS_SOURCE * (1 + gw150914.PUBLISHED_REDSHIFT)
    assert fit["best_snr"] > 15  # the published network SNR is about 24
    assert published < fit["best_mass"] < 1.25 * published
    # Hanford before Livingston by at most the 10 ms light travel time.
    assert 0 < fit["delay"] < 0.010


def test_the_template_finds_nothing_in_the_data_away_from_the_event():
    """Control: away from the event the same template stays at noise level."""
    strain = gw150914.load(GW)["H1"]
    time, snr = gw150914.template_snr(strain, 30.0)
    away = np.abs(time - gw150914.EVENT_GPS) > 3.0
    assert snr[away].max() < 10


def test_the_models_and_the_measurement_share_the_wave_period():
    experiment, models = aalborg_flume.load(AAL)
    measured = aalborg_flume.dominant_period(
        experiment.time, experiment.column(aalborg_flume.GAUGE, "mean"), 2, 14
    )
    for name, model in models.items():
        modelled = aalborg_flume.dominant_period(model.time, model.values[:, 0], 2, 14)
        assert modelled == pytest.approx(measured, rel=0.02), name


def test_the_models_follow_the_measurement_inside_the_window():
    experiment, models = aalborg_flume.load(AAL)
    amplitude = np.abs(experiment.column(aalborg_flume.GAUGE, "mean")).max()
    for name, model in models.items():
        assert aalborg_flume.window_rms(experiment, model) < 0.15 * amplitude, name


def test_every_panel_of_every_figure_is_titled_and_labelled():
    for module, path in (
        (gw150914, GW),
        (npl_sparameters, NPL),
        (aalborg_flume, AAL),
        (bayreuth_rlc, RLC),
        (munich_bell, BELL),
        (xu_pendulum, XU),
    ):
        figure = module.make_figure(path)
        panels = [a for a in figure.axes if a.axison and a.get_label() != "<colorbar>"]
        assert len(panels) >= 2
        for axis in panels:
            assert axis.get_title(), module.__name__
            assert axis.get_ylabel(), module.__name__
        assert all(a.get_xlabel() for a in panels[-1:]), module.__name__
        plt.close(figure)
