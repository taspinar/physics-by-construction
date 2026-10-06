import numpy as np
import pytest

from pbc.sample import damped_oscillation


def test_starts_at_the_amplitude():
    assert damped_oscillation(0.0, amplitude=2.5) == pytest.approx(2.5)


def test_stays_inside_the_decaying_envelope():
    t = np.linspace(0.0, 10.0, 2001)
    x = damped_oscillation(t, amplitude=1.5, decay_rate=0.3)
    assert np.all(np.abs(x) <= 1.5 * np.exp(-0.3 * t) + 1e-12)


def test_without_decay_it_repeats_after_one_period():
    omega = 3.0
    period = 2.0 * np.pi / omega
    t = np.linspace(0.0, 4.0, 101)
    np.testing.assert_allclose(
        damped_oscillation(t + period, decay_rate=0.0, angular_frequency=omega),
        damped_oscillation(t, decay_rate=0.0, angular_frequency=omega),
        atol=1e-12,
    )


def test_matches_a_value_computed_by_hand():
    # exp(-0.5 * 1) * cos(pi) = -exp(-0.5)
    x = damped_oscillation(1.0, decay_rate=0.5, angular_frequency=np.pi)
    assert x == pytest.approx(-np.exp(-0.5))


def test_result_has_the_shape_of_the_times():
    t = np.zeros((3, 4))
    assert damped_oscillation(t).shape == (3, 4)


def test_rejects_a_growing_oscillation():
    with pytest.raises(ValueError, match="decay_rate"):
        damped_oscillation(1.0, decay_rate=-0.1)
