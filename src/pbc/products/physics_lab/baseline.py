"""The scripted baseline: the frequency-response protocol without a model.

A coarse sweep, log-spaced between the configured bounds, finds the two
points whose phases bracket -90 degrees; a refinement measures
``refine_points`` more, log-spaced strictly between them. The order of the
operations is fixed, so the same seed gives the same run.
"""

from collections.abc import Callable

import numpy as np

from pbc.instruments import Instrument
from pbc.products.physics_lab.protocol import Config, Measurement, analyse, measure


def run_baseline(
    instrument: Instrument,
    config: Config,
    on_point: Callable[[Measurement], None] | None = None,
) -> list[Measurement]:
    """The measurements of the scripted route."""
    done: list[Measurement] = []

    def take(frequency: float) -> None:
        measurement = measure(instrument, config, float(frequency), config.amplitude_v)
        done.append(measurement)
        if on_point is not None:
            on_point(measurement)

    for frequency in np.geomspace(config.low_hz, config.high_hz, config.coarse_points):
        take(frequency)
    analysis = analyse([m.point for m in done])
    if analysis.bracket is not None and config.refine_points:
        low, high = analysis.bracket
        for frequency in np.geomspace(low, high, config.refine_points + 2)[1:-1]:
            take(frequency)
    return done
