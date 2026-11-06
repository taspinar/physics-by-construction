"""The scripted route of my lab: plan a sweep, measure it through the
guarded instrument, and refine it.

Everything imported from ``pbc`` is already verified by Physics by
Construction at the starter's pin: the instrument contract with its safety
envelope (``pbc.instruments``), the simulated bench over the series RLC
circuit, and one point of the protocol with its analysis and the
evaluator's check (``pbc.products.physics_lab.protocol``). Your work is in
the places marked YOUR WORK.
"""

import numpy as np

from pbc.instruments import Instrument
from pbc.instruments.simulated import SimulatedRLCBench
from pbc.products.physics_lab.protocol import (
    Config,
    Measurement,
    Point,
    analyse,
    bench_envelope,
    measure,
)


def make_instrument(seed: int) -> Instrument:
    """The simulated bench behind the product's safety envelope."""
    return Instrument(SimulatedRLCBench(seed=seed), bench_envelope())


def plan_sweep(config: Config) -> list[float]:
    """The frequencies of the first sweep, log-spaced between the bounds."""
    return [float(f) for f in np.geomspace(config.low_hz, config.high_hz, 9)]


def refine(config: Config, points: list[Point]) -> list[float]:
    """The frequencies to measure next, from the points so far.

    YOUR WORK: choose points that locate the resonance better, for example
    between the two points whose phases bracket -90 degrees. The starter
    measures nothing more.
    """
    return []


def run_sweep(instrument: Instrument, config: Config) -> list[Measurement]:
    """Measure the planned sweep, then each refinement, until ``refine``
    asks for nothing more or the budget of measurements is spent."""
    done = [
        measure(instrument, config, f, config.amplitude_v) for f in plan_sweep(config)
    ]
    while len(done) < config.agent_budget:
        more = refine(config, [m.point for m in done])
        if not more:
            break
        for f in more[: config.agent_budget - len(done)]:
            done.append(measure(instrument, config, f, config.amplitude_v))
    instrument.output_off()
    return done


def estimate(measurements: list[Measurement]):
    """The resonance and the quality factor the points show."""
    return analyse([m.point for m in measurements])
