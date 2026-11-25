"""A registered plan: the question, the explanations and the outcomes each
predicts, the outcome rule, the withheld part, the success criteria, the
stopping conditions, and its freeze.

The rules of ``pbc.research.plan`` and ``pbc.research.followup`` applied to
plans that are not throw specifications: a plan without a withheld part or
without stopping conditions is refused; the explanations (two or more) must
discriminate, so no outcome may be predicted by two of them; and evidence
measured before the freeze is refused. The freeze is the digest of the plan
and the commit on ``main`` that holds it (part 0 of Issue #619 defines it for
the original track); a plan on a feature branch is not frozen.
"""

import tomllib
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from pbc.evidence.records import digest_value


class RegistrationRefused(ValueError):
    """A plan the workspace does not accept as registered, with the reasons."""


@dataclass(frozen=True)
class Explanation:
    """One explanation and the outcomes of the rule it predicts."""

    name: str
    statement: str
    predicts: tuple[str, ...]


@dataclass(frozen=True)
class Criterion:
    """One row of what counts as a result: the quantity, the source of its
    published value, the rule, and what follows otherwise. ``post_hoc``
    says why a rule was set after a result had been seen (empty for a rule
    declared before any fit): its row is then never a confirmatory
    result."""

    quantity: str
    source: str
    rule: str
    otherwise: str
    post_hoc: str = ""


@dataclass(frozen=True)
class Registration:
    key: str
    kind: str  # "replication" or "original"
    question: str
    hypotheses: tuple[str, ...]
    explanations: tuple[Explanation, ...]
    outcomes: tuple[str, ...]
    rule: str
    withheld: str
    criteria: tuple[Criterion, ...]
    stopping: tuple[str, ...]


@dataclass(frozen=True)
class Freeze:
    """Where a registration is frozen: its digest, the commit on ``main``
    (``None`` while it is a draft), and the time it was frozen."""

    digest: str
    commit: str | None
    time: str  # ISO 8601

    @property
    def frozen(self) -> bool:
        return self.commit is not None


def discriminates(registration: Registration) -> list[str]:
    """The reasons the explanations cannot decide: fewer than two, one that
    predicts nothing, an outcome predicted by two, or a prediction that is
    not an outcome of the rule. Empty when every outcome counts for at most
    one explanation."""
    found = []
    explanations = registration.explanations
    if len(explanations) < 2:
        found.append("fewer than two explanations")
    owners: dict[str, list[str]] = {}
    for explanation in explanations:
        if not explanation.predicts:
            found.append(f"{explanation.name} predicts no outcome")
        for outcome in explanation.predicts:
            if outcome not in registration.outcomes:
                found.append(
                    f"{explanation.name} predicts {outcome!r}, which the rule"
                    " cannot return"
                )
            owners.setdefault(outcome, []).append(explanation.name)
    for outcome, names in sorted(owners.items()):
        if len(names) > 1:
            found.append(f"the outcome {outcome!r} is predicted by {', '.join(names)}")
    return found


def problems(registration: Registration) -> list[str]:
    """Every rule the plan breaks (``discriminates`` and the refusal rules of
    ``pbc.research.plan``: a withheld part and stopping conditions)."""
    found = discriminates(registration)
    if registration.kind not in ("replication", "original"):
        found.append(f"unknown kind {registration.kind!r}")
    if not registration.withheld.strip():
        found.append("no withheld (confirmatory) part")
    if not registration.stopping:
        found.append("no stopping conditions")
    if not registration.criteria:
        found.append("no success criteria")
    if len(set(registration.outcomes)) < 2:
        found.append("the rule has fewer than two outcomes")
    return found


def check(registration: Registration) -> None:
    found = problems(registration)
    if found:
        raise RegistrationRefused("; ".join(found))


def digest(registration: Registration) -> str:
    return digest_value(asdict(registration))


def admit(measured: str, freeze: Freeze) -> None:
    """Refuse evidence measured before the freeze, or under a draft."""
    if not freeze.frozen:
        raise RegistrationRefused(
            "the registration is a draft: no evidence is admitted before its freeze"
        )
    if datetime.fromisoformat(measured) < datetime.fromisoformat(freeze.time):
        raise RegistrationRefused(
            f"the evidence was measured at {measured}, before the freeze at"
            f" {freeze.time}"
        )


def load(path: Path) -> Registration:
    """A registration from a project's ``registration.toml``."""
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    return from_mapping(data)


def from_mapping(data: Mapping) -> Registration:
    return Registration(
        key=data["key"],
        kind=data["kind"],
        question=data["question"],
        hypotheses=tuple(data.get("hypotheses", ())),
        explanations=tuple(
            Explanation(e["name"], e["statement"], tuple(e["predicts"]))
            for e in data.get("explanation", ())
        ),
        outcomes=tuple(data["outcomes"]),
        rule=data["rule"],
        withheld=data.get("withheld", ""),
        criteria=tuple(
            Criterion(
                c["quantity"],
                c["source"],
                c["rule"],
                c["otherwise"],
                c.get("post_hoc", ""),
            )
            for c in data.get("criterion", ())
        ),
        stopping=tuple(data.get("stopping", ())),
    )
