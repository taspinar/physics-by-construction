"""The geometry of the submerged-bar flume and the harmonic fit of a gauge
record (lesson W8)."""

import numpy as np
import pytest

from pbc.data.flume import BED, GAUGE_X, STILL_WATER_DEPTH, depth_at, harmonics


def test_the_gauges_are_twenty_and_in_order_along_the_flume():
    assert list(GAUGE_X) == list(range(1, 21))
    assert np.all(np.diff(list(GAUGE_X.values())) > 0)


@pytest.mark.parametrize("bed", list(BED))
def test_the_bed_is_flat_away_from_the_bar_and_shallowest_on_its_crest(bed):
    assert depth_at(np.array([0.0, 2.0, 7.0, 14.0]), bed) == pytest.approx(
        STILL_WATER_DEPTH
    )
    crest = BED[bed][1]
    assert depth_at(crest[0] + 0.5, bed) == pytest.approx(crest[1])
    # Halfway up the front slope, halfway in depth.
    middle = 0.5 * (BED[bed][0][0] + BED[bed][1][0])
    assert depth_at(middle, bed) == pytest.approx(0.5 * (STILL_WATER_DEPTH + crest[1]))


def test_the_harmonic_fit_recovers_amplitudes_and_phases_of_a_known_record():
    f = 1 / 1.5
    t = np.arange(0, 20, 1 / 150)
    w = 2 * np.pi * f
    record = (
        0.001
        + 0.012 * np.cos(w * t - 0.7)
        + 0.003 * np.cos(2 * w * t + 1.1)
        + 0.0005 * np.sin(3 * w * t)
    )
    record[100] = np.nan  # a masked sample is skipped
    a = harmonics(t, record, f, 3, (4.0, 8.5))
    np.testing.assert_allclose(np.abs(a), [0.012, 0.003, 0.0005], atol=1e-12)
    np.testing.assert_allclose(np.angle(a[:2]), [-0.7, 1.1], atol=1e-9)
    # A wave travelling towards larger x has arg(a_1) = -k x + constant.
    k = 2.68
    shifted = harmonics(t, 0.012 * np.cos(w * t - k * 1.5), f, 1, (4.0, 8.5))
    assert np.angle(shifted[0]) == pytest.approx(np.angle(np.exp(-1j * k * 1.5)))
