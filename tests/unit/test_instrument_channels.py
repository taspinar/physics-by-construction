"""The acquisition chain of pbc.instruments.channels (F142): each step does
what its docstring says, in that order, and the channel adapter passes the
captures of the adapter below it through one chain per channel."""

import math

import numpy as np
import pytest

from pbc.instruments.channels import ChannelChain, Dropouts, ImperfectChannels
from pbc.instruments.simulated import SimulatedRLCBench


def test_an_ideal_chain_writes_the_voltage_unchanged():
    volts = np.linspace(-3.0, 3.0, 13)
    np.testing.assert_array_equal(ChannelChain().record(volts), volts)


def test_gain_and_offset_come_before_the_rails():
    chain = ChannelChain(gain=2.0, offset_v=0.5, full_scale_v=2.0)
    recorded = chain.record(np.array([-2.0, -0.5, 0.0, 0.5, 2.0]))
    # 2 v + 0.5, then held at plus and minus 2
    np.testing.assert_allclose(recorded, [-2.0, -0.5, 0.5, 1.5, 2.0])


def test_the_converter_rounds_to_its_step_and_a_clipped_sample_sits_on_a_rail():
    chain = ChannelChain(full_scale_v=1.0, bits=3)
    assert chain.step_v == pytest.approx(0.25)
    recorded = chain.record(np.array([0.11, 0.13, -0.6, 5.0, -5.0]))
    np.testing.assert_allclose(recorded, [0.0, 0.25, -0.5, 1.0, -1.0])


@pytest.mark.parametrize(
    "arguments",
    [
        {"gain": 0.0},
        {"full_scale_v": -1.0},
        {"bits": 1, "full_scale_v": 1.0},
        {"bits": 8},  # quantised without a full scale
    ],
)
def test_an_impossible_chain_is_refused(arguments):
    with pytest.raises(ValueError):
        ChannelChain(**arguments)


def test_dropouts_are_bursts_at_seeded_places():
    dropouts = Dropouts(bursts=3, length=10, seed=4)
    lost = dropouts.lost(500, 0)
    np.testing.assert_array_equal(lost, dropouts.lost(500, 0))
    assert not np.array_equal(lost, dropouts.lost(500, 1))
    assert 10 <= lost.sum() <= 30
    assert not Dropouts(0, 10).lost(100, 0).any()


def test_the_channel_adapter_applies_one_chain_per_channel_and_marks_losses():
    chain = ChannelChain(gain=0.5, offset_v=0.1)
    plain = SimulatedRLCBench(seed=9)
    wrapped = ImperfectChannels(
        SimulatedRLCBench(seed=9), {"response": chain}, Dropouts(1, 7, seed=2)
    )
    for bench in (plain, wrapped):
        bench.set_output(1.0, 4_000.0)
    ideal, recorded = plain.capture(256_000.0, 257), wrapped.capture(256_000.0, 257)
    lost = np.isnan(recorded.channels["response"])
    assert lost.sum() == 7
    np.testing.assert_array_equal(np.isnan(recorded.channels["source"]), lost)
    np.testing.assert_allclose(
        recorded.channels["response"][~lost],
        0.5 * ideal.channels["response"][~lost] + 0.1,
    )
    np.testing.assert_array_equal(
        recorded.channels["source"][~lost], ideal.channels["source"][~lost]
    )
    identity = wrapped.identity()
    assert "response: gain 0.5, offset 0.1 V" in identity["calibration"]
    assert identity["dropouts"] == "1 bursts of 7 samples"
    assert wrapped.mode == plain.mode
    assert math.isinf(chain.full_scale_v)
