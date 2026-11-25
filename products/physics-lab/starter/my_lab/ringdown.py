"""The ring-down fit of my lab's transient-response protocol: the resonance
frequency and the quality factor of the circuit from the capacitor voltage
after a step, with their standard errors (SPECIFICATION.md).

Your work is in the place marked YOUR WORK.
"""

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class RingdownFit:
    """What one ring-down shows, each value with its standard error."""

    decay_rate: float  # alpha, 1/s
    decay_rate_se: float
    damped_frequency_hz: float  # omega_d / (2 pi), Hz
    damped_frequency_se: float
    f0_hz: float  # sqrt(omega_d^2 + alpha^2) / (2 pi), Hz
    f0_se: float
    q: float  # omega_0 / (2 alpha)
    q_se: float


def fit_ringdown(t_s: Sequence[float], v: Sequence[float]) -> RingdownFit:
    """Fit v(t) = v_inf + e^(-alpha t) (a cos(omega_d t) + b sin(omega_d t))
    to the record and return alpha, omega_d, f0 and Q with their standard
    errors.

    YOUR WORK: see SPECIFICATION.md for the model, what the fit may not
    know, and what it must refuse with ``ValueError``.
    """
    raise NotImplementedError("YOUR WORK: the ring-down fit")
