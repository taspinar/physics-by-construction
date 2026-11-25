"""Typed discrepancies between a published and a regenerated value.

A discrepancy is reported, typed, and never explained away. Its type is one
of ``TYPES``; every type but ``unexplained`` needs a recorded check that
supports it (``Check.supports``), and ``unexplained`` is the honest default.
A ``not-reproduced`` verdict is a result with its evidence, not a failure of
the track.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

INPUT = "input"
METHOD = "method"
UNCERTAINTY = "uncertainty"
NUMERICAL = "numerical"
UNEXPLAINED = "unexplained"
TYPES = (INPUT, METHOD, UNCERTAINTY, NUMERICAL, UNEXPLAINED)

REPRODUCED = "reproduced"
NOT_REPRODUCED = "not-reproduced"
INCONCLUSIVE = "inconclusive"
NOT_EVALUATED = "not evaluated"
VERDICTS = (REPRODUCED, NOT_REPRODUCED, INCONCLUSIVE, NOT_EVALUATED)

# What each type's check must show (the plan of Issue #619, "Typed
# discrepancies").
REQUIRES = {
    INPUT: "a sensitivity branch in which the regenerated value moves to the"
    " published one when the paper's input is used instead",
    METHOD: "the missing piece named with where the paper describes it, and a"
    " sensitivity branch showing the size of its effect",
    UNCERTAINTY: "the regenerated statistical uncertainty beside the published"
    " one, and the published budget's other terms named from the paper",
    NUMERICAL: "a run at a higher precision or a different implementation that"
    " removes it",
}


class DiscrepancyRefused(ValueError):
    """A discrepancy whose type its record does not support."""


@dataclass(frozen=True)
class Check:
    """A recorded check behind a type: its name, what it computed (numbers
    by name), the run or branch it rests on, and whether it supports the
    type."""

    name: str
    run: str
    values: Mapping[str, float]
    supports: bool
    note: str = ""


@dataclass(frozen=True)
class Discrepancy:
    """One row of the reproduction: the quantity, the published value with
    its source key, the regenerated value, the verdict, and for a verdict
    other than ``reproduced`` the type and its check. ``missing`` names what
    the paper's method needs that the inputs lack (``method``), with the
    place in the paper; ``terms`` the published budget's other terms
    (``uncertainty``)."""

    quantity: str
    published: str
    source: str
    regenerated: str
    verdict: str
    type: str | None = None
    check: Check | None = None
    missing: str = ""
    terms: tuple[str, ...] = field(default_factory=tuple)
    note: str = ""


def problems(discrepancy: Discrepancy) -> list[str]:
    """Every rule the discrepancy breaks; empty when it is admissible."""
    d = discrepancy
    found = []
    if d.verdict not in VERDICTS:
        found.append(f"{d.quantity}: unknown verdict {d.verdict!r}")
        return found
    if not d.source:
        found.append(f"{d.quantity}: the published value names no source")
    if d.verdict == REPRODUCED:
        if d.type is not None:
            found.append(f"{d.quantity}: a reproduced value carries no type")
        return found
    if d.verdict == NOT_EVALUATED:
        return found
    if d.type not in TYPES:
        found.append(f"{d.quantity}: the type {d.type!r} is not one of {TYPES}")
        return found
    if d.type == UNEXPLAINED:
        return found
    if d.check is None:
        found.append(
            f"{d.quantity}: the type {d.type} needs a recorded check:"
            f" {REQUIRES[d.type]}; otherwise it is {UNEXPLAINED}"
        )
    elif not d.check.supports:
        found.append(
            f"{d.quantity}: the check {d.check.name} does not support the type"
            f" {d.type}; the discrepancy stays {UNEXPLAINED} or takes another"
            " supported type"
        )
    if d.type == METHOD and not d.missing.strip():
        found.append(f"{d.quantity}: a method discrepancy names the missing piece")
    if d.type == UNCERTAINTY and not d.terms:
        found.append(
            f"{d.quantity}: an uncertainty discrepancy names the published"
            " budget's other terms"
        )
    return found


def validate(discrepancies: Iterable[Discrepancy]) -> None:
    """Raise ``DiscrepancyRefused`` with every problem of the rows."""
    found = [p for d in discrepancies for p in problems(d)]
    if found:
        raise DiscrepancyRefused("; ".join(found))


def as_dict(discrepancy: Discrepancy) -> dict:
    d = discrepancy
    return {
        "quantity": d.quantity,
        "published": d.published,
        "source": d.source,
        "regenerated": d.regenerated,
        "verdict": d.verdict,
        "type": d.type,
        "check": None
        if d.check is None
        else {
            "name": d.check.name,
            "run": d.check.run,
            "values": dict(d.check.values),
            "supports": d.check.supports,
            "note": d.check.note,
        },
        "missing": d.missing,
        "terms": list(d.terms),
        "note": d.note,
    }


def from_dict(data: Mapping) -> Discrepancy:
    check = data.get("check")
    return Discrepancy(
        data["quantity"],
        data["published"],
        data["source"],
        data["regenerated"],
        data["verdict"],
        data.get("type"),
        None if check is None else Check(**{**check, "values": dict(check["values"])}),
        data.get("missing", ""),
        tuple(data.get("terms", ())),
        data.get("note", ""),
    )
