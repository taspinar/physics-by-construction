"""The compass needle and its generated clips (F142): the simulation against
the closed form of small damped swings, the field inverted from the
frequency, the frames drawn as stated, and the tracking against the angle
that drew each frame."""

import math

import numpy as np
import pytest

from pbc.electromagnetism import needle as compass


def test_small_swings_follow_the_damped_closed_form():
    needle = compass.Needle()
    t = np.linspace(0.0, 3.0, 601)
    start = 0.05  # degrees: small enough for sin(theta) = theta
    theta = compass.simulate(needle, t, start_deg=start)
    wd, g = 2 * math.pi * needle.frequency, needle.damping
    exact = (
        math.radians(start)
        * np.exp(-g * t)
        * (np.cos(wd * t) + g / wd * np.sin(wd * t))
    )
    np.testing.assert_allclose(theta, exact, atol=1e-5 * math.radians(start))


def test_the_field_from_the_frequency_inverts_the_frequency_of_the_field():
    for field in (1e-4, 5e-4, 2e-3):
        needle = compass.Needle(field=field)
        found = compass.field_from_frequency(needle.frequency, needle.damping)
        assert found == pytest.approx(field, rel=1e-12)


def test_a_larger_swing_is_slower():
    """The pendulum's correction: the frequency falls with the amplitude, so
    the small-swing formula reads a large swing's field too low."""
    needle = compass.Needle(damping=0.0)
    t = np.arange(0, 2.0, 1 / 2000)

    def frequency(start):
        theta = compass.simulate(needle, t, start_deg=start)
        crossings = np.where(np.diff(np.sign(theta)) != 0)[0]
        return (len(crossings) - 1) / (2 * (t[crossings[-1]] - t[crossings[0]]))

    assert frequency(30.0) < frequency(15.0) < frequency(1.0)
    assert frequency(1.0) == pytest.approx(needle.frequency, rel=2e-3)


@pytest.mark.parametrize("degrees", [-60.0, -17.3, 0.0, 4.2, 15.0, 33.0, 60.0])
def test_the_tracking_finds_the_angle_that_drew_the_frame(degrees):
    frame = compass.render_frame(math.radians(degrees))
    assert frame.shape == (compass.HEIGHT, compass.WIDTH) and frame.dtype == np.uint8
    assert math.degrees(compass.track_angle(frame)) == pytest.approx(degrees, abs=0.05)


def test_a_frame_is_drawn_the_same_way_every_time():
    a, b = compass.render_frame(0.3), compass.render_frame(0.3)
    np.testing.assert_array_equal(a, b)
    assert compass.png(a) == compass.png(b)
    assert compass.data_url(a).startswith("data:image/png;base64,")


def test_a_clip_has_one_frame_per_frame_time():
    clip = compass.film(compass.Needle(), 5.0, 4.0)
    assert len(clip.frames) == len(clip.t) == 20
    np.testing.assert_allclose(np.diff(clip.t), 0.2)


def test_the_fit_of_a_track_gives_its_frequency_and_decay():
    t = np.arange(120) / 30.0
    angle = 0.2 * np.exp(-0.4 * t) * np.cos(2 * math.pi * 3.1 * t + 0.7)
    fit = compass.fit_track(t, angle)
    assert (fit.frequency, fit.damping, fit.amplitude) == pytest.approx((3.1, 0.4, 0.2))
    assert fit.residual_rms < 1e-9
