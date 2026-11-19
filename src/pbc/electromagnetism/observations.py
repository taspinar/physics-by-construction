"""Interpretations of a picture, typed by how certain they are (F142, the
lesson "Measurement quality and multimodal observations").

A reading of an image, a diagram, or a clip is not a measurement until it has
been checked against one. Each statement made from a picture is an
``Interpretation`` with a status:

- ``read``: what the picture shows, which another reader of the same picture
  would state the same way (a probe is connected across the capacitor);
- ``inferred``: what follows from what is read and from stated physics, with
  the physics named (the voltage across a resistor is in phase with the
  current);
- ``uncertain``: what the picture does not decide. An uncertain statement
  names what would settle it (a component value, a higher frame rate).

A ``Check`` compares one interpretation with a simulated measurement and
records the outcome: ``confirmed``, ``contradicted``, or ``not checked``,
with the numbers it rests on. A confirmed uncertain interpretation keeps its
status: it was right for the circuit that was checked, and the picture still
does not decide it.
"""

from dataclasses import dataclass

READ = "read"
INFERRED = "inferred"
UNCERTAIN = "uncertain"
STATUSES = (READ, INFERRED, UNCERTAIN)

CONFIRMED = "confirmed"
CONTRADICTED = "contradicted"
NOT_CHECKED = "not checked"
OUTCOMES = (CONFIRMED, CONTRADICTED, NOT_CHECKED)


@dataclass(frozen=True)
class Interpretation:
    """One statement made from a picture, with its status, what it rests on,
    and, when it is uncertain, what would settle it."""

    statement: str
    status: str
    basis: str
    settled_by: str = ""

    def __post_init__(self):
        if self.status not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES}, got {self.status!r}")
        if not self.basis:
            raise ValueError("an interpretation names what it rests on")
        if self.status == UNCERTAIN and not self.settled_by:
            raise ValueError("an uncertain interpretation names what would settle it")
        if self.status != UNCERTAIN and self.settled_by:
            raise ValueError("only an uncertain interpretation is settled by more")


@dataclass(frozen=True)
class Check:
    """An interpretation against a simulated measurement."""

    interpretation: Interpretation
    outcome: str
    evidence: str

    def __post_init__(self):
        if self.outcome not in OUTCOMES:
            raise ValueError(f"outcome must be one of {OUTCOMES}, got {self.outcome!r}")
        if self.outcome != NOT_CHECKED and not self.evidence:
            raise ValueError("a confirmed or contradicted check states its evidence")


def check(interpretation: Interpretation, holds: bool | None, evidence: str) -> Check:
    """The check of ``interpretation``: confirmed when ``holds`` is True,
    contradicted when False, not checked when None."""
    if holds is None:
        return Check(interpretation, NOT_CHECKED, evidence)
    return Check(interpretation, CONFIRMED if holds else CONTRADICTED, evidence)
