"""The scripted reviewer: a fixed list of checks, each recomputed from the
project's records, never read from a report.

A failing check becomes a finding of the follow-up log, of the kind its
definition names (``EVIDENCE``: it asks for new evidence; ``WORDING``: for
other words); a passing check is recorded as the evidence that answers its
finding. The agent reviewer (``agent.py``) reaches these checks only through
the tool ``run_check``, so a finding it proposes is accepted only through a
recomputed check.
"""

import hashlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from pbc.data import REPO_ROOT
from pbc.data.reference.cobe_firas import Spectrum
from pbc.evidence.records import digest_value
from pbc.products.research_workspace import discrepancy as d
from pbc.products.research_workspace import firas
from pbc.products.research_workspace import log as worklog
from pbc.products.research_workspace.graph import SAMPLE


@dataclass(frozen=True)
class Context:
    """What the checks read: the card, the spectrum, the fits by branch, the
    control, and the rows."""

    card: Mapping
    spectrum: Spectrum
    fits: Mapping[str, Sequence[firas.Fit]]
    control: firas.Control
    rows: Sequence[d.Discrepancy]


@dataclass(frozen=True)
class Result:
    name: str
    passed: bool | None
    value: float
    detail: str


@dataclass(frozen=True)
class Definition:
    """A check and the finding it raises when it fails."""

    name: str
    question: str
    claim: str
    kind: str
    finding: str
    function: Callable[[Context], tuple[bool | None, float, str]]


def _sample(context: Context):
    data = (REPO_ROOT / SAMPLE).read_bytes()
    expected = context.card["samples"][0]["sha256"]
    ok = hashlib.sha256(data).hexdigest() == expected
    return ok, float(len(data)), "the committed sample's sha256 against the card"


def _control(context: Context):
    c = context.control
    least = min(c.recovered_t, c.recovered_y, c.zero_covered)
    return c.passed, float(least), f"{least} of {c.seeds} seeds, {c.required} required"


def _typed(context: Context):
    found = [p for row in context.rows for p in d.problems(row)]
    return not found, float(len(found)), "; ".join(found) or "every row admissible"


def _refit(context: Context):
    # A different implementation of the b1 fit: the normal equations solved
    # directly, not the least-squares solver of ``firas.fit``.
    s = context.spectrum
    templates = firas.shapes(s, s.t_ref)
    a = np.column_stack([templates[firas.TEMPERATURE], templates[firas.GALAXY]])
    w = s.sigma**-2.0
    normal = a.T @ (a * w[:, None])
    values = np.linalg.solve(normal, a.T @ (s.residual * w))
    b1 = context.fits["b1"][0]
    recorded = np.array([b1.parameters[firas.TEMPERATURE], b1.parameters[firas.GALAXY]])
    errors = np.array([b1.errors[firas.TEMPERATURE], b1.errors[firas.GALAXY]])
    distance = float(np.max(np.abs(values - recorded) / errors))
    return distance < 1e-6, distance, "b1 refitted by the normal equations"


def _by_construction(context: Context):
    resting = [
        r
        for r in context.rows
        if r.verdict == d.REPRODUCED
        and r.quantity.startswith(
            ("the spectrum fit", "the weighted rms", "the residual")
        )
    ]
    stated = [r for r in resting if "by construction" in r.note]
    ok = len(stated) == len(resting)
    return (
        ok,
        float(len(resting) - len(stated)),
        ("every reproduced row that rests on the paper's own residuals says so"),
    )


def _t0(context: Context):
    claimed = [
        r
        for r in context.rows
        if r.quantity.startswith("T0") and r.verdict == d.REPRODUCED
    ]
    return not claimed, float(len(claimed)), "no row reports the absolute T0 reproduced"


def _statistical(context: Context):
    bounds = [r for r in context.rows if r.quantity.startswith("|")]
    unlabelled = [r for r in bounds if "statistical" not in r.regenerated]
    return not unlabelled, float(len(unlabelled)), "every bound labelled statistical"


def _covariance(context: Context):
    # The method weights with the diagonal; the paper with its covariance
    # between frequencies (section 3.3). Nothing in the records answers it.
    return False, 0.0, "the fits use the diagonal of the uncertainties only"


CHECKS: tuple[Definition, ...] = (
    Definition(
        "sample-digest",
        "Is the committed sample the file the card names?",
        "inputs",
        worklog.EVIDENCE,
        "The committed sample's digest differs from the card.",
        _sample,
    ),
    Definition(
        "control",
        "Does the method recover what was injected?",
        "control",
        worklog.EVIDENCE,
        "The positive control fails: the method cannot be trusted on this data.",
        _control,
    ),
    Definition(
        "discrepancies-typed",
        "Is every discrepancy typed with a supporting check?",
        "rows",
        worklog.EVIDENCE,
        "A discrepancy carries a type its records do not support.",
        _typed,
    ),
    Definition(
        "independent-refit",
        "Does another implementation give the same b1 fit?",
        "b1",
        worklog.EVIDENCE,
        "The b1 fit differs between two implementations.",
        _refit,
    ),
    Definition(
        "by-construction-stated",
        "Does each reproduced row that rests on the paper's own residuals say so?",
        "rows",
        worklog.WORDING,
        "A reproduced row hides that the residuals are the paper's own fit.",
        _by_construction,
    ),
    Definition(
        "t0-not-claimed",
        "Is the absolute T0 kept out of the reproduced rows?",
        "t0",
        worklog.WORDING,
        "A row reports the absolute temperature as reproduced.",
        _t0,
    ),
    Definition(
        "bounds-statistical",
        "Is every regenerated bound labelled statistical?",
        "bounds",
        worklog.WORDING,
        "A regenerated bound is not labelled statistical only.",
        _statistical,
    ),
    Definition(
        "covariance-weighting",
        "Does the fit weight with the paper's covariance between frequencies?",
        "rows",
        worklog.EVIDENCE,
        "The fits weight with the diagonal only, while the paper weights with the"
        " covariance between frequencies of its section 3.3; the statistical"
        " errors, chi-square, and bounds may differ from the paper's for that"
        " reason. It asks for a fit with that covariance, not for other words.",
        _covariance,
    ),
)
NAMES = tuple(c.name for c in CHECKS)


def run_check(name: str, context: Context) -> Result:
    definition = next(c for c in CHECKS if c.name == name)
    passed, value, detail = definition.function(context)
    return Result(name, passed, value, detail)


def review(context: Context, log: worklog.Log) -> list[Result]:
    """Run every check; add a finding for each failing one that the log does
    not hold yet, and the evidence of each passing one whose finding it
    holds."""
    results = []
    held = log.findings()
    for definition in CHECKS:
        result = run_check(definition.name, context)
        results.append(result)
        key = f"review-{definition.name}"
        digest = digest_value([result.name, result.passed, result.value, result.detail])
        if result.passed is False and key not in held:
            log.find(
                key,
                definition.claim,
                worklog.SCRIPTED,
                definition.finding,
                definition.kind,
                definition.name,
            )
        elif result.passed is True and key in held:
            log.evidence(key, definition.name, True, digest)
    return results
