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
    nist_numisheet,
    npl_sparameters,
)

GW = SAMPLES_DIR / "gw150914-strain"
NPL = SAMPLES_DIR / "npl-onwafer-sparameters"
AAL = SAMPLES_DIR / "aalborg-submerged-bar"
RLC = SAMPLES_DIR / "bayreuth-rlc-impedance"
DP980 = SAMPLES_DIR / "nist-numisheet-dp980"


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


def test_nist_numisheet_sample_parses():
    # Field names: the header row of the stress-strain file, and the units of
    # its companion attributes file.
    header = (DP980 / nist_numisheet.FILE).read_text().splitlines()[0]
    assert header == ",".join(f'"{f}"' for f in nist_numisheet.FIELDS)
    units = nist_numisheet.read_attributes(DP980 / nist_numisheet.ATTRIBUTES)
    assert units == nist_numisheet.UNITS
    test = nist_numisheet.load(DP980)
    # Shapes: 1,607 rows of five columns.
    for column in (
        test.time,
        test.strain,
        test.stress,
        test.true_strain,
        test.true_stress,
    ):
        assert column.shape == (1607,)
    # Cadence: the images, 0.25 s apart until 62.85 s, then 1 s (with a few
    # gaps of 1.25-1.33 s), from 0 to 1418.0 s, strictly increasing.
    step = np.diff(test.time)
    assert test.time[0] == 0 and test.time[-1] == pytest.approx(1418.0168)
    assert (step > 0).all()
    early = test.time[1:] <= 62.85
    assert np.allclose(step[early][1:], 0.25, atol=0.002)
    assert np.allclose(step[~early][1:], 1.0, atol=0.34)
    assert np.median(step[~early]) == pytest.approx(1.0, abs=0.001)
    # Units: strain in mm/mm (|e| < 0.2, the true strain is ln(1 + e)),
    # stress in MPa (about 1 GPa for this steel), true stress S (1 + e).
    np.testing.assert_allclose(test.true_strain, np.log1p(test.strain), atol=1e-14)
    np.testing.assert_allclose(
        test.true_stress, test.stress * (1 + test.strain), atol=1e-9
    )
    assert np.abs(test.strain).max() < 0.2
    assert 900 < test.stress.max() < 1100 and -1100 < test.stress.min() < -900
    # Masks: none.
    assert all(
        np.isfinite(c).all()
        for c in (test.time, test.strain, test.stress, test.true_strain)
    )


def test_the_dp980_test_reverses_the_load_and_closes_a_hysteresis_loop():
    """Tension to 5.8 %, compression back to about zero strain, tension to
    fracture: a load reversal with a loop of 75.9 MJ/m^3. The values are the
    dossier's."""
    test = nist_numisheet.load(DP980)
    seg = nist_numisheet.segments(test)
    assert test.stress[seg.reversal] == pytest.approx(991.3, abs=0.1)
    assert test.strain[seg.hold_end] == pytest.approx(0.05791, abs=1e-5)
    # The hold: the strain stays within 0.01 % while the stress relaxes 21 MPa.
    held = test.strain[seg.reversal + 2 : seg.hold_end + 1]
    assert np.ptp(held) < 1e-4
    relaxed = test.stress[seg.reversal] - test.stress[seg.hold_end]
    assert relaxed == pytest.approx(21.1, abs=0.1)
    assert test.stress[seg.compression] == pytest.approx(-1006.6, abs=0.1)
    assert abs(test.strain[seg.compression]) < 0.001
    rows, area = nist_numisheet.loop(test)
    assert area == pytest.approx(75.86, abs=0.01)
    assert test.strain[rows][-1] >= test.strain[seg.reversal]
    neck = nist_numisheet.reload_maximum(test)
    assert test.stress[neck] == pytest.approx(981.2, abs=0.1)
    assert test.strain[neck] == pytest.approx(0.0910, abs=1e-4)
    assert test.strain[-1] == pytest.approx(0.1771, abs=1e-4)
    # The unloading chord is far below E: the curve is not elastic on the way
    # down (the Bauschinger effect of a dual-phase steel).
    chord = nist_numisheet.unloading_modulus(test)
    assert chord == pytest.approx(143.6, abs=0.1)
    assert nist_numisheet.unloading_modulus(test, 500, 0) == pytest.approx(
        130.3, abs=0.1
    )
    assert nist_numisheet.unloading_modulus(test, 950, 600) == pytest.approx(
        159.5, abs=0.1
    )


def test_the_dp980_elastic_fit_and_its_uncertainty():
    """E from the 100-400 MPa window, its standard error from the scatter,
    and the spread over the windows of the sensitivity analysis; the scatter
    of the residuals matches the extensometer noise before the ramp."""
    test = nist_numisheet.load(DP980)
    result = nist_numisheet.elastic_fit(test)
    assert result.ok, result.warnings
    assert result.value("E") == pytest.approx(196.3, abs=0.05)
    assert result.stderr[0] == pytest.approx(1.09, abs=0.01)
    assert result.value("S0") == pytest.approx(7.4, abs=0.05)
    moduli = {
        w: r.value("E") for w, r in nist_numisheet.window_sensitivity(test).items()
    }
    assert min(moduli.values()) == pytest.approx(192.5, abs=0.05)
    assert max(moduli.values()) == pytest.approx(198.4, abs=0.05)
    assert nist_numisheet.offset_yield(test, result) == pytest.approx(775.2, abs=0.1)
    rows = nist_numisheet.preload(test)
    assert rows.size == 10
    noise = test.strain[rows].std(ddof=1)
    assert noise == pytest.approx(2.5e-5, abs=0.1e-5)
    assert noise < nist_numisheet.DIC_NOISE_FLOOR / 10
    rms = np.sqrt(np.mean(result.residuals**2))
    assert rms == pytest.approx(4.4, abs=0.1)
    assert rms == pytest.approx(result.value("E") * 1e3 * noise, rel=0.15)
    assert nist_numisheet.stress_from_load_cells(test) == pytest.approx(5.87, abs=0.01)


def test_a_file_with_other_columns_is_refused(tmp_path):
    path = tmp_path / "other.csv"
    path.write_text('"Time","Load"\n0,1\n')
    with pytest.raises(ValueError, match="columns"):
        nist_numisheet.read_stress_strain(path)
    attributes = tmp_path / "attributes.csv"
    attributes.write_text('"Name","Kind"\n"Time","s"\n')
    with pytest.raises(ValueError, match="attributes"):
        nist_numisheet.read_attributes(attributes)


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
        (nist_numisheet, DP980),
    ):
        figure = module.make_figure(path)
        panels = [a for a in figure.axes if a.axison and a.get_label() != "<colorbar>"]
        assert len(panels) >= 2
        for axis in panels:
            assert axis.get_title(), module.__name__
            assert axis.get_ylabel(), module.__name__
        assert all(a.get_xlabel() for a in panels[-1:]), module.__name__
        plt.close(figure)
