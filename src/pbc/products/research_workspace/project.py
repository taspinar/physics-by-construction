"""The project: a directory that lives across sessions, with append-only
chains (the question archive, the follow-up log, the evidence ledger), the
run graph's states, and the exports.

Layout of a project directory::

    inputs/          questions.toml, registration.toml, sources.toml (copied)
    states/          the run graph's state files (pbc.evidence.resumable)
    ledger.json      the evidence ledger (pbc.evidence.records)
    branches.json    the branches of the run graph
    archive.json     the question archive (pbc.research.ideas)
    log.json         the follow-up log (log.py)
    states/control/  the positive control
    rows.json        the rows of the reproduction, typed
    run.json         the run record: inputs by digest, execution modes, the
                     digests of the stage code and of the outcome code
    report.md        the report export
    view.html        the static workspace view

``verify`` checks every chain and every digest and names every problem;
nothing is repaired.
"""

import json
import shutil
from dataclasses import asdict
from pathlib import Path

from pbc.data import REGISTRY_DIR, REPO_ROOT
from pbc.data.card import load_card
from pbc.data.reference.cobe_firas import DATASET, read_spectrum
from pbc.evidence import records
from pbc.evidence.records import (
    COMPLETED,
    DERIVED,
    FAILED,
    Artifact,
    Attempt,
    Evaluation,
    digest_file,
)
from pbc.products.research_workspace import discrepancy as d
from pbc.products.research_workspace import (
    firas,
    graph,
    questions,
    registration,
    reproduction,
    review,
    sources,
)
from pbc.products.research_workspace import log as worklog
from pbc.products.research_workspace import report as rep
from pbc.research.ideas import Entry, Idea, verify_archive

INPUTS = ("questions.toml", "registration.toml", "sources.toml")
EVALUATOR = "pbc.products.research_workspace evaluator, recomputation from the state"
REVIEWER = "pbc.products.research_workspace scripted reviewer, normal equations"
CONTROL = "control/run"
CONTROL_FILE = "control/run.json"
MODES = {
    "load": "recorded (the committed sample of a declared dataset)",
    "fit": "recorded (computed from the committed sample)",
    "control": "simulated (seeds 0 to 99)",
    "agent": "not run (the scripted reviewer stands for it; the replay fixtures"
    " are placeholders)",
}


class ProjectRefused(ValueError):
    """An input the workspace does not accept, with the reasons."""


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _archive_data(entries) -> list[dict]:
    return [asdict(e) for e in entries]


def _archive_entries(data) -> list[Entry]:
    return [Entry(**{**e, "idea": Idea(**e["idea"])}) for e in data]


def _evaluate(research, attempt_id: str) -> Evaluation:
    """The evaluator: run the fit again from the states the attempt rests on
    and compare with the recorded output."""
    attempt = research.ledger.attempt(attempt_id)
    state = research.state(attempt_id)
    loaded = research.state(attempt.prior[0])
    again = graph._fit(loaded.output, state.configuration)
    same = again == state.output
    fits = [firas.Fit.from_dict(f) for f in state.output["fits"]]
    return Evaluation(
        attempt_id,
        EVALUATOR,
        same,
        {"chi2": fits[0].chi2},
        {"fits": len(fits)},
        attempt.artifacts,
        research.code,
        research.record.configuration,
    )


def run(example: Path, directory: Path) -> Path:
    """Run the reproduction track end to end from the inputs in ``example``
    into the new project ``directory``; returns the report's path."""
    example, directory = Path(example), Path(directory)
    from pbc.products.research_workspace import original

    if original.is_example(example):
        try:
            return original.run(example, directory)
        except original.OriginalRefused as reason:
            raise ProjectRefused(str(reason)) from reason
    if directory.exists() and any(directory.iterdir()):
        raise ProjectRefused(
            f"{directory} is not empty: a project is never overwritten"
        )
    (directory / "inputs").mkdir(parents=True, exist_ok=True)
    for name in INPUTS:
        shutil.copyfile(example / name, directory / "inputs" / name)
    inputs = directory / "inputs"

    budget, asked = questions.load(inputs / "questions.toml")
    names = {n for q in asked for n in q.datasets}
    cards = questions.cards_of(names, REGISTRY_DIR)
    assessments = {q.key: questions.assess(q, cards, budget) for q in asked}
    found = questions.selection_problems(asked, assessments)
    plan = registration.load(inputs / "registration.toml")
    found += registration.problems(plan)
    evidence = sources.load(inputs / "sources.toml")
    found += sources.problems(evidence, sources.register_entries())
    if found:
        raise ProjectRefused("; ".join(found))
    archive = questions.archive(asked)
    _write_json(directory / "archive.json", _archive_data(archive.entries))
    _write_json(
        directory / "assessments.json", {k: asdict(a) for k, a in assessments.items()}
    )

    plan_digest = registration.digest(plan)
    research = graph.new_research(directory / "states", plan_digest)
    graph.run_all(research)
    fits = graph.fits_of(research)
    spectrum = read_spectrum(REPO_ROOT / graph.SAMPLE)

    trial = firas.control(spectrum)
    control_path = directory / "states" / CONTROL_FILE
    control_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(control_path, trial.as_dict())
    research.ledger.add_attempt(
        Attempt(
            CONTROL,
            "control",
            research.ledger.cycle,
            COMPLETED if trial.passed else FAILED,
            () if trial.passed else ("the positive control failed",),
            (Artifact.of("control", control_path, directory / "states", DERIVED),),
        )
    )
    for attempt in list(research.ledger.attempts):
        if attempt.id.endswith("/fit") and attempt.status == COMPLETED:
            research.ledger.add_evaluation(_evaluate(research, attempt.id))
    research.ledger.add_evaluation(_evaluate_control(research, spectrum, trial))

    by_id = sources.by_id(evidence)
    rows = reproduction.mark_post_hoc(
        reproduction.rows(spectrum, fits, trial, by_id), plan
    )
    _write_json(directory / "rows.json", [d.as_dict(r) for r in rows])

    log = worklog.Log()
    for decision in firas.decide(fits):
        log.decide(
            decision.branch,
            decision.decision,
            decision.reason,
            decision.revisit,
            "the registered criterion",
        )
    failed = research.ledger.attempt(f"{graph.FAILED_BRANCH}/fit")
    log.decide(
        graph.FAILED_BRANCH,
        "stop",
        f"failed: {'; '.join(failed.diagnostics)}",
        "a fit that separates y and mu, which the paper says these data cannot",
        "the registered criterion",
    )
    context = review.Context(
        load_card(REGISTRY_DIR / f"{DATASET}.yaml"), spectrum, fits, trial, rows
    )
    results = review.review(context, log)
    for result in results:
        if result.name == "independent-refit" and result.passed:
            research.ledger.add_evaluation(
                Evaluation(
                    "b1/fit",
                    REVIEWER,
                    True,
                    {"distance": result.value},
                    {},
                    research.ledger.attempt("b1/fit").artifacts,
                    research.code,
                    research.record.configuration,
                )
            )
    worklog.save(log, directory / "log.json")

    for claim in rep.claims_of(rows):
        research.ledger.add_claim(claim)
    records.save(research.ledger, directory / "ledger.json")
    graph.save_branches(research, directory / "branches.json")

    _write_json(
        directory / "run.json",
        {
            "track": "reproduction",
            "registration": {
                "key": plan.key,
                "digest": plan_digest,
                "file": digest_file(inputs / "registration.toml"),
                "frozen": False,
                "note": "registered in the example file committed with part 1; a"
                " plan on a feature branch is not frozen",
            },
            "inputs": {name: digest_file(inputs / name) for name in INPUTS},
            "sample": {graph.SAMPLE: digest_file(REPO_ROOT / graph.SAMPLE)},
            "modes": MODES,
            "code": research.code,
            "outcome_code": graph.outcome_code_digest(),
            "outcome_files": graph.outcome_file_digests(),
            "results": [asdict(r) for r in results],
        },
    )
    write_exports(directory)
    return directory / "report.md"


def _evaluate_control(research, spectrum, trial: firas.Control) -> Evaluation:
    again = firas.control(spectrum)
    return Evaluation(
        CONTROL,
        EVALUATOR,
        again.as_dict() == trial.as_dict() and trial.passed,
        {"least": float(min(trial.recovered_t, trial.recovered_y, trial.zero_covered))},
        {"seeds": trial.seeds},
        research.ledger.attempt(CONTROL).artifacts,
        research.code,
        research.record.configuration,
    )


def open_research(directory: Path):
    """The run graph of a project as it was saved, to resume or check."""
    directory = Path(directory)
    ledger = records.load(directory / "ledger.json")
    research = graph.new_research(directory / "states", ledger.record.configuration)
    research.ledger = ledger
    research.branches = graph.load_branches(directory / "branches.json")
    return research


def track(directory: Path) -> str:
    """The track of a saved project: ``reproduction`` or ``original``."""
    return _read_json(Path(directory) / "run.json").get("track", "reproduction")


def context(directory: Path) -> review.Context:
    """What the reviewer's checks read, from a saved project."""
    if track(directory) == "original":
        raise ProjectRefused(
            "the original track has no agent reviewer yet: its outcomes are"
            " decided by the registered rules"
        )
    data = summary(directory)
    return review.Context(
        load_card(REGISTRY_DIR / f"{DATASET}.yaml"),
        read_spectrum(REPO_ROOT / graph.SAMPLE),
        data["fits"],
        data["control"],
        data["rows"],
    )


def save_log(directory: Path, log: worklog.Log) -> None:
    """Write the log back and the exports again (the log only grows)."""
    old = worklog.load(Path(directory) / "log.json").entries
    if log.entries[: len(old)] != old:
        raise ProjectRefused("the log only grows: an earlier entry changed")
    worklog.save(log, Path(directory) / "log.json")
    write_exports(directory)


def summary(directory: Path) -> dict:
    """Everything the report and the view show, read from the project."""
    directory = Path(directory)
    if track(directory) == "original":
        from pbc.products.research_workspace import original

        return original.summary(directory)
    research = open_research(directory)
    fits = graph.fits_of(research)
    trial = _read_json(directory / "states" / CONTROL_FILE)
    control = firas.Control(
        trial["seeds"],
        trial["injected"],
        trial["recovered_t"],
        trial["recovered_y"],
        trial["zero_covered"],
        trial["required"],
    )
    log = worklog.load(directory / "log.json")
    status = rep.statuses(research.ledger, directory / "states")
    rows = [d.from_dict(r) for r in _read_json(directory / "rows.json")]
    evidence = sources.load(directory / "inputs" / "sources.toml")
    plan = registration.load(directory / "inputs" / "registration.toml")
    return {
        "directory": directory,
        "research": research,
        "fits": fits,
        "control": control,
        "log": log,
        "status": status,
        "rows": rows,
        "sources": evidence,
        "registration": plan,
        "run": _read_json(directory / "run.json"),
        "archive": _archive_entries(_read_json(directory / "archive.json")),
        "assessments": _read_json(directory / "assessments.json"),
        "records": rep.records_of(fits, control),
        "problems": verify(directory),
    }


def write_view(directory: Path, out: Path) -> None:
    """Write the static view of a saved project of either track to ``out``."""
    if track(directory) == "original":
        from pbc.products.research_workspace import original_view

        original_view.write(summary(directory), Path(out))
        return
    from pbc.products.research_workspace import view

    view.write(summary(directory), Path(out))


def write_exports(directory: Path) -> None:
    from pbc.products.research_workspace import view

    if track(directory) == "original":
        from pbc.products.research_workspace import original

        original.write_exports(directory)
        return

    data = summary(directory)
    text, _ = render_markdown(data)
    (Path(directory) / "report.md").write_text(text, encoding="utf-8")
    view.write(data, Path(directory) / "view.html")


def _cell(value) -> str:
    """A Markdown table cell: a pipe in the text is escaped."""
    return str(value).replace("|", "\\|")


def _row(*cells) -> str:
    return "| " + " | ".join(_cell(c) for c in cells) + " |"


def render_markdown(data: dict):
    """The report as Markdown, and the numbers it wrote (for the check)."""
    numbers = rep.Numbers(data["records"])
    status = data["status"]
    claims = {c.id: c for c in data["research"].ledger.claims}
    statements = rep.statements_of(list(claims.values()))
    rep.validate_report(statements, data["research"].ledger)
    lines = [
        "# Reproduction report: the COBE FIRAS spectrum fit (Fixsen et al. 1996)",
        "",
    ]
    lines += [f"> {line}" for line in rep.banner_lines(status)]
    lines += ["", f"Scope: {rep.SCOPE}.", ""]
    if data["problems"]:
        lines += ["**The project does not verify:**", ""]
        lines += [f"- {p}" for p in data["problems"]] + [""]
    plan = data["registration"]
    lines += ["## Question and registration", "", plan.question, ""]
    lines += [
        f"Registration `{plan.key}`, digest"
        f" `{data['run']['registration']['digest'][:16]}`;"
        " not frozen (a plan on a feature branch is not frozen).",
        "",
    ]
    lines += ["| Question | Decision | Reason | Revisit when |", "|---|---|---|---|"]
    for entry in data["archive"]:
        lines.append(_row(entry.idea.key, entry.decision, entry.reason, entry.revisit))
    lines += ["", "## Source evidence", ""]
    lines += ["| Source | Quantity | Place | Quoted |", "|---|---|---|---|"]
    for s in data["sources"]:
        lines.append(_row(s.id, s.quantity, s.place, f'"{s.quote}"'))
    lines += ["", "## The run graph", ""]
    lines += [
        "| Branch | Fit | chi-square / dof | T_fit [K] | Decision | Reason |",
        "|---|---|---|---|---|---|",
    ]
    decisions = {
        e.content["subject"]: e.content for e in data["log"].of(worklog.DECISION)
    }
    for name in graph.BRANCH_ORDER:
        decision = decisions.get(name, {})
        if name in data["fits"]:
            record = f"{name}/fit"
            fit = data["fits"][name][0]
            chi = f"{numbers(record, 'chi2', 2)} / {numbers(record, 'dof', 0)}"
            t = numbers(record, "t_fit_K", 6)
            what = ", ".join(p for p in firas.PARAMETERS if p in fit.parameters)
        else:
            chi, t, what = "failed", "", "dT, G, y, mu"
        lines.append(
            _row(
                name,
                what,
                chi,
                t,
                decision.get("decision", ""),
                decision.get("reason", ""),
            )
        )
    c = data["control"]
    lines += [
        "",
        "## The positive control (simulated)",
        "",
        f"Recovered dT in {numbers(CONTROL, 'recovered_t', 0)} and y in"
        f" {numbers(CONTROL, 'recovered_y', 0)} of {numbers(CONTROL, 'seeds', 0)} seeds"
        f" within two standard errors; the 95 % interval of y covered zero in"
        f" {numbers(CONTROL, 'zero_covered', 0)}; {numbers(CONTROL, 'required', 0)}"
        f" required. {'Passed' if c.passed else 'Failed: every row is not evaluated'}.",
        "",
        "## The rows of the reproduction",
        "",
        "| Quantity | Published | Regenerated | Verdict | Type | Check"
        " | Claim status |",
        "|---|---|---|---|---|---|---|",
    ]
    for number, row in enumerate(data["rows"], start=1):
        check = "" if row.check is None else f"{row.check.name} ({row.check.run})"
        lines.append(
            _row(
                row.quantity,
                row.published,
                row.regenerated,
                d.verdict_text(row),
                row.type or "",
                check,
                status.get(f"row-{number}", ""),
            )
        )
    notes = [
        (n, r)
        for n, r in enumerate(data["rows"], start=1)
        if r.note or r.missing or r.post_hoc
    ]
    if notes:
        lines += [""]
        for number, row in notes:
            parts = [row.note] if row.note else []
            if row.missing:
                parts.append(f"Missing: {row.missing}")
            if row.post_hoc:
                parts.append(f"Post-hoc rule: {row.post_hoc}")
            text = ". ".join(p.rstrip(".") for p in parts)
            lines.append(f"- Row {number}: {text}.")
    lines += ["", "## Findings of the review", ""]
    lines += ["| Finding | Kind | By | State | Text |", "|---|---|---|---|---|"]
    for key, entry in data["log"].findings().items():
        lines.append(
            _row(
                key,
                entry.content["kind"],
                entry.content["reviewer"],
                worklog.state(data["log"], key),
                entry.content["text"],
            )
        )
    lines += ["", "## Claims", ""]
    lines += ["| Claim | Status | Runs | Sources |", "|---|---|---|---|"]
    for cid, claim in claims.items():
        lines.append(
            _row(
                cid,
                status[cid],
                ", ".join(claim.runs),
                ", ".join(claim.sources) or "none",
            )
        )
    lines += [
        "",
        "Data: NASA COBE FIRAS / LAMBDA (firas_monopole_spec_v1.txt); Fixsen et al."
        " 1996, ApJ 473, 576. We acknowledge the use of the Legacy Archive for"
        " Microwave Background Data Analysis (LAMBDA), part of the High Energy"
        " Astrophysics Science Archive Center (HEASARC). HEASARC/LAMBDA is a"
        " service of the Astrophysics Science Division at the NASA Goddard Space"
        " Flight Center.",
        "",
    ]
    return "\n".join(lines), numbers.written


def verify(directory: Path) -> list[str]:
    """Every problem of the project's chains and digests; empty when none."""
    directory = Path(directory)
    if track(directory) == "original":
        from pbc.products.research_workspace import original

        return original.verify(directory)
    found = []
    run_record = _read_json(directory / "run.json")
    for name, digest in run_record["inputs"].items():
        if digest_file(directory / "inputs" / name) != digest:
            found.append(f"the input {name} changed after the run")
    for path, digest in run_record["sample"].items():
        if digest_file(REPO_ROOT / path) != digest:
            found.append(f"the sample {path} changed after the run")
    found += verify_archive(_archive_entries(_read_json(directory / "archive.json")))
    found += worklog.verify(worklog.load(directory / "log.json").entries)
    research = open_research(directory)
    if research.code != graph.code_digest():
        found.append("the analysis code changed after the run")
    outcome = run_record.get("outcome_code")
    if outcome is None:
        found.append(
            "the run records no digest of the outcome code (its rules cannot"
            " be checked)"
        )
    elif outcome != graph.outcome_code_digest():
        recorded = run_record.get("outcome_files", {})
        current = graph.outcome_file_digests()
        changed = sorted(
            name
            for name in recorded.keys() | current.keys()
            if recorded.get(name) != current.get(name)
        )
        named = ", ".join(changed) if recorded and changed else "not recorded by file"
        found.append(
            "the outcome code changed after the run (the code that decides"
            f" the rows, claims, or checks; changed: {named});"
            " the recorded rows were decided by the old code"
        )
    for invalid in records.check(research.ledger, directory / "states"):
        found.append(str(invalid))
    for name in research.branches:
        attempt = research.ledger.attempt(f"{name}/fit")
        if attempt is not None and attempt.status == FAILED:
            continue  # a failed attempt is kept, never resumed
        found += research.problems(name)
    return found
