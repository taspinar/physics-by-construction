"""The committed dataset samples parse into what their cards say (ADR 007).

Each ``test_*_sample_parses`` is the parsing test that the cards of its
dataset name. The figure tests check the physical consistency that the
feasibility dossiers rely on, on the same samples.
"""

import matplotlib.pyplot as plt
import numpy as np
import pytest

from pbc.data import SAMPLES_DIR
from pbc.data.flume import read_elevation
from pbc.data.gwosc import read_strain
from pbc.data.reference import aalborg_flume, gw150914, npl_sparameters

GW = SAMPLES_DIR / "gw150914-strain"
NPL = SAMPLES_DIR / "npl-onwafer-sparameters"
AAL = SAMPLES_DIR / "aalborg-submerged-bar"


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
    ):
        figure = module.make_figure(path)
        panels = [a for a in figure.axes if a.axison and a.get_label() != "<colorbar>"]
        assert len(panels) >= 2
        for axis in panels:
            assert axis.get_title(), module.__name__
            assert axis.get_ylabel(), module.__name__
        assert all(a.get_xlabel() for a in panels[-1:]), module.__name__
        plt.close(figure)
