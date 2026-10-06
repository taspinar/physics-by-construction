"""Sample curve for the rendering-check page of the site.

The page calls this function from an executed cell, which proves that pages
run against the locked environment with this package installed. It is a
pipeline sample, not lesson code.
"""

import numpy as np
from numpy.typing import ArrayLike, NDArray


def damped_oscillation(
    t: ArrayLike,
    *,
    amplitude: float = 1.0,
    decay_rate: float = 0.5,
    angular_frequency: float = 2.0 * np.pi,
) -> NDArray[np.float64]:
    """Return ``amplitude * exp(-decay_rate * t) * cos(angular_frequency * t)``.

    ``t`` may be a scalar or an array; the result has the shape of ``t``.
    A negative ``decay_rate`` would describe a growing oscillation and is
    rejected.
    """
    if decay_rate < 0:
        raise ValueError(f"decay_rate must be non-negative, got {decay_rate}")
    time = np.asarray(t, dtype=np.float64)
    return amplitude * np.exp(-decay_rate * time) * np.cos(angular_frequency * time)
