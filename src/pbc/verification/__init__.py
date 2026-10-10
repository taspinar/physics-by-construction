"""Showing that scientific code is right, with evidence a reader can rerun.

``estimates`` holds the numerical helpers: observed orders of convergence,
a fitted order, a convergence table, and the drift and band of an invariant.
``checks`` applies them as the named checks of the scientific validation
contract (``docs/validation-contract.md``) to a stepper of the mechanics
course. ``faulty`` is a gallery of steppers with a deliberate fault, each
recording the check that must catch it; nothing outside the lesson and its
tests may import it.
"""

from pbc.verification.checks import (
    CHECKS,
    Claim,
    Finding,
    oscillator_error,
    verify,
)
from pbc.verification.estimates import (
    convergence_table,
    fitted_order,
    invariant_band,
    invariant_drift,
    observed_orders,
)

__all__ = [
    "CHECKS",
    "Claim",
    "Finding",
    "convergence_table",
    "fitted_order",
    "invariant_band",
    "invariant_drift",
    "observed_orders",
    "oscillator_error",
    "verify",
]
