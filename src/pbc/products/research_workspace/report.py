"""The report export: every claim with its run or source link and its
evidence status, every number resolved to a record's field, and a first
line that says what a report is.

Each row of the reproduction becomes a ``pbc.evidence.Claim`` with the
attempt of its branch as its run and the register key of its published
value as its source; each sentence is a ``pbc.evidence.report.Statement``
that ``validate`` refuses without a claim, a table, an assumption, or an
uncertainty. Every number of a sentence is written through ``Numbers``,
which resolves it with ``pbc.research.report.resolve_number`` against the
records, so a number with no record cannot be written. The report's first
lines count the claims in each status, generated from the ledger, and say
that a report is a summary of records, not a proof that the investigation
succeeded.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from pbc.evidence.records import (
    EVIDENCE_STATUSES,
    Claim,
    Ledger,
    check,
    claim_status,
)
from pbc.evidence.report import COMPUTED, Statement, validate
from pbc.products.research_workspace import discrepancy as d
from pbc.products.research_workspace import firas
from pbc.research.report import RECORD, Quantity, resolve_number

BANNER = (
    "This report is a summary of the project's records, not a proof that the"
    " investigation succeeded."
)
# The run of each row's claim: the branch whose fit it rests on.
ROW_RUNS = {
    "the spectrum fit": ("b1/fit",),
    "T0, the absolute temperature": ("b1/fit", "b4/fit"),
    "the uncertainty of T0": ("b1/fit",),
    "the weighted rms": ("b1/fit",),
    "the residual figure": ("b1/fit",),
    "|y|": ("b2/fit",),
    "|mu|": ("b3/fit",),
}
SCOPE = (
    "the LAMBDA monopole file, diagonal weights, statistical uncertainties only;"
    " not the absolute temperature calibration"
)


def records_of(fits: Mapping[str, Sequence[firas.Fit]], control: firas.Control) -> dict:
    """The flat records the report's numbers resolve to, by attempt."""
    out: dict[str, dict[str, float]] = {}
    for branch, branch_fits in fits.items():
        for number, f in enumerate(branch_fits):
            key = f"{branch}/fit" if number == 0 else f"{branch}/fit#{number}"
            fields = {
                "chi2": f.chi2,
                "dof": float(f.dof),
                "rms_ppm": f.rms_ppm(),
                "t_fit_K": f.temperature,
                "points": float(f.points),
            }
            for name, value in f.parameters.items():
                scale, unit = {
                    firas.TEMPERATURE: (1e-6, "microK"),
                    firas.GALAXY: (1.0, "1"),
                    firas.COMPTON: (1e-6, "1e-6"),
                    firas.CHEMICAL: (1e-5, "1e-5"),
                }[name]
                fields[f"{name}_{unit}"] = value / scale
                fields[f"sigma_{name}_{unit}"] = f.errors[name] / scale
                if name in (firas.COMPTON, firas.CHEMICAL):
                    fields[f"bound_{name}_{unit}"] = f.bound(name) / scale
            out[key] = fields
    out["control/run"] = {
        "seeds": float(control.seeds),
        "recovered_t": float(control.recovered_t),
        "recovered_y": float(control.recovered_y),
        "zero_covered": float(control.zero_covered),
        "required": float(control.required),
    }
    return out


@dataclass
class Numbers:
    """Writes numbers only from the records, and remembers each one."""

    records: Mapping[str, Mapping[str, float]]
    written: list[tuple[str, Quantity]] = field(default_factory=list)

    def __call__(self, record: str, name: str, decimals: int) -> str:
        text = format(self.records[record][name], f".{decimals}f")
        quantity = Quantity(record, name)
        outcome, why = resolve_number(text, quantity, self.records)
        if outcome != RECORD:
            raise ValueError(f"{record}.{name}: {why}")
        self.written.append((text, quantity))
        return text


def number_problems(
    written: Sequence[tuple[str, Quantity]], records: Mapping[str, Mapping[str, float]]
) -> list[str]:
    """Every written number that no longer resolves to its record."""
    out = []
    for text, quantity in written:
        outcome, why = resolve_number(text, quantity, records)
        if outcome != RECORD:
            out.append(f"{text} ({quantity.record}.{quantity.field}): {why}")
    return out


def _runs_of(row: d.Discrepancy) -> tuple[str, ...]:
    for head, runs in ROW_RUNS.items():
        if row.quantity.startswith(head):
            return runs
    raise ValueError(f"no run for the row {row.quantity!r}")


def claims_of(rows: Sequence[d.Discrepancy]) -> list[Claim]:
    """One claim per row, with its runs and its source; plus the control."""
    out = []
    for number, row in enumerate(rows, start=1):
        text = f"{row.quantity}: {d.verdict_text(row)}"
        if row.type:
            text += f" ({row.type})"
        text += f"; regenerated {row.regenerated}; published {row.published}"
        out.append(
            Claim(
                f"row-{number}",
                text,
                SCOPE,
                {run: True for run in _runs_of(row)},
                (row.source,),
            )
        )
    out.append(
        Claim(
            "control",
            "the positive control recovers the injected dT and y and covers zero",
            "simulated spectra at the file's frequencies and uncertainties",
            {"control/run": True},
        )
    )
    return out


def statements_of(claims: Sequence[Claim]) -> list[Statement]:
    return [
        Statement(
            f"s-{claim.id}",
            claim.text,
            COMPUTED,
            claim.id,
            ("table-rows",) if claim.id != "control" else ("table-control",),
            (1, 2, 3, 4) if claim.id != "control" else (2, 3),
            "statistical only, from the diagonal 1-sigma column; the systematic"
            " terms of the paper are not in the file"
            if claim.id != "control"
            else "binomial: 90 of 100 is the declared floor",
        )
        for claim in claims
    ]


def statuses(ledger: Ledger, root) -> dict[str, str]:
    stale = check(ledger, root)
    return {c.id: claim_status(ledger, c, stale) for c in ledger.claims}


def counts(status_by_claim: Mapping[str, str]) -> dict[str, int]:
    return {s: sum(v == s for v in status_by_claim.values()) for s in EVIDENCE_STATUSES}


def banner_lines(status_by_claim: Mapping[str, str]) -> list[str]:
    tally = counts(status_by_claim)
    shown = ", ".join(f"{n} {s}" for s, n in tally.items() if n)
    lines = [BANNER, f"Claims: {len(status_by_claim)} ({shown})."]
    if status_by_claim and all(v == "not evaluated" for v in status_by_claim.values()):
        lines.append("Every claim of this report is not evaluated.")
    return lines


def validate_report(statements: Sequence[Statement], ledger: Ledger) -> None:
    validate(statements, ledger)
