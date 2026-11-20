"""The experiment of the lesson "Independent scoring, sealed evaluation, and
provenance".

The evidence contract of ``pbc.evidence`` at work, in two parts. On the
projectile task of the pilot (``pbc.evidence.pilot``), the evaluator scores
the committed runs itself, a candidate's report of a score it did not
achieve fails, an edited fixture is invalid, and the final evaluation is
bound to the frozen candidate: the cases of the pilot's tests, run here on
copies of the fixtures in a temporary directory. On the spring of D2
(``pbc.evidence.sealed``), three recorded runs are evaluated in development,
the best is selected and frozen, and it is evaluated once on a sealed split
of later times. Run it as a program to write the figure and numbers of the
page:

    uv run --locked --no-dev python -m \\
        pbc.mechanics.experiments.independent_scoring_and_sealed_evaluation out

Nothing is recorded or measured live: every run is a fixture of the pages of
EV2, EV3, and D2, replayed here.
"""

import json
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.authoring.repository import REPOSITORY_ROOT
from pbc.discovery import benchmark
from pbc.evidence import (
    ContractError,
    Ledger,
    check,
    claim_status,
    pilot,
    sealed,
    summary,
)
from pbc.evidence.records import Claim
from pbc.experiment import Experiment, main
from pbc.figure_language import figsize, figure_style, finish

# The live run of a recording this lesson evaluates: the plain model of EV3,
# with a model and its key and the extra openai. The other live commands are
# on the pages that hold their fixtures.
LIVE = "pbc.discovery.benchmark plain-projectile"

# The pages whose fixtures the evaluations replay, each used by name: the
# input digest of this page follows them (``pbc.authoring.digest``).
EV2 = REPOSITORY_ROOT / "site/lessons/agents-llm/12-interactive-discovery-benchmarks"
EV3 = REPOSITORY_ROOT / "site/lessons/agents-llm/13-agent-versus-non-agent-baselines"
D2 = REPOSITORY_ROOT / "site/lessons/agents-llm/06-prior-knowledge-in-discovery"

AGENT, PLAIN = "projectile-full", "plain-projectile"


def _read_where_named() -> None:
    """The fixtures the pilot and the sealed split read are those of the
    pages named above."""
    pages = {pilot.fixture(c).parent for c in pilot.CANDIDATES}
    pages |= {sealed.fixture(c).parent for c in sealed.CANDIDATES}
    if pages != {EV2, EV3, D2}:
        raise RuntimeError(f"the fixtures moved: {sorted(map(str, pages))}")


# What the plain model is made to report about itself: a score it did not
# achieve (the case of the pilot's tests).
FABRICATED = {"held_out_error": 0.001, "recovered": True}


def _copy(root: Path) -> Path:
    """The pilot's fixtures copied to their paths under ``root``."""
    for candidate in pilot.CANDIDATES:
        target = pilot.fixture(candidate, root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(pilot.fixture(candidate), target)
    return root


def _edit(path: Path, change: Callable[[dict], None]) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _better_readings(data: dict) -> None:
    for result in data["steps"][0]["results"]:
        if "range" in result["content"]:
            result["content"]["range"] *= 1.2


def scoring() -> Ledger:
    """The evaluator scores three candidates; the plain model reports a
    score it did not achieve, and claims it recovered the law."""
    ledger = Ledger(pilot.run_record())
    pilot.evaluate_attempt(ledger, "agent-1", AGENT, claims_correct=True)
    # region: fabricated
    pilot.evaluate_attempt(
        ledger, "plain-1", PLAIN, reported=FABRICATED, claims_correct=True
    )
    ledger.add_claim(
        Claim(
            "plain-recovers", "The plain model recovers g.", "pilot", {"plain-1": True}
        )
    )
    # endregion: fabricated
    pilot.evaluate_baseline(ledger, "baseline-1")
    return ledger


def scoring_table(experiment: Experiment, ledger: Ledger) -> None:
    s = summary(ledger, pilot.repository())
    reports = {r.attempt: r for r in ledger.reports}
    rows = []
    for row, evaluation in zip(s.rows, ledger.evaluations, strict=True):
        report = reports.get(row.attempt)
        reported = "-"
        if report is not None and "held_out_error" in report.details:
            reported = f"{report.details['held_out_error']:.3g}"
        rows.append(
            (
                row.candidate,
                f"{evaluation.metrics['held_out_error']:.3g}",
                "yes" if row.correct else "no",
                reported,
                row.report,
                evaluation.resources["probes"],
            )
        )
    experiment.table(
        "ae4-scoring",
        rows,
        [
            ("candidate", "", ""),
            ("held-out error, recomputed", "", ""),
            ("correct", "", ""),
            ("held-out error, as reported", "", ""),
            ("report", "", ""),
            ("probes, counted", "", "d"),
        ],
        "Each candidate scored by the evaluator from its replayed fixture; a"
        " report is the candidate's own and is never used. A dash: nothing"
        " reported.",
    )
    status = claim_status(ledger, ledger.claims[0])
    experiment.number("plain-claim-status", status)
    plain = next(e for e in ledger.evaluations if e.attempt == "plain-1")
    experiment.number("plain-error", plain.metrics["held_out_error"], ".2f")
    experiment.number("fabricated-error", FABRICATED["held_out_error"], "g")
    agent = next(e for e in ledger.evaluations if e.attempt == "agent-1")
    info = benchmark.RUNS[AGENT].info.cost
    experiment.number("agent-calls-counted", agent.resources["tool_calls"])
    experiment.number("agent-calls-recorded", info.tool_calls)
    experiment.number("agent-messages-counted", agent.resources["model_messages"])
    experiment.number("agent-refused", agent.resources["refused"])


def tampering(experiment: Experiment) -> dict[str, str]:
    """Five changes to the evidence, each on a fresh copy of the fixtures,
    and what the contract does with each. Returns the outcome by case."""
    found: dict[str, str] = {}
    with tempfile.TemporaryDirectory() as directory:
        root = _copy(Path(directory) / "edited-readings")
        _edit(pilot.fixture(AGENT, root), _better_readings)
        ledger = Ledger(pilot.run_record())
        attempt = pilot.evaluate_attempt(ledger, "agent-1", AGENT, root)
        ledger.add_claim(
            Claim("c", "The agent recovers g.", "pilot", {"agent-1": True})
        )
        found["readings edited before the evaluation"] = (
            f"attempt {attempt.status}; claim {claim_status(ledger, ledger.claims[0])}"
        )

        root = _copy(Path(directory) / "edited-after")
        ledger = pilot.run_pilot(root)
        _edit(
            pilot.fixture(AGENT, root), lambda d: d["steps"][-1].update(text="edited")
        )
        stale = check(ledger, root)
        statuses = {c.id: claim_status(ledger, c, stale) for c in ledger.claims}
        found["fixture edited after the evaluation"] = (
            f"{len(stale)} evaluations invalidated; claim {statuses['agent-recovers']}"
        )

        root = _copy(Path(directory) / "changed-after-freeze")
        ledger = Ledger(pilot.run_record())
        pilot.evaluate_attempt(ledger, "agent-1", AGENT, root)
        pilot.freeze(ledger, AGENT, "1", root)
        _edit(pilot.fixture(AGENT, root), lambda d: d["steps"][-1].update(text="tuned"))
        found["candidate changed between freeze and final evaluation"] = _refused(
            lambda: pilot.final_evaluation(ledger, AGENT, root)
        )

        root = _copy(Path(directory) / "second-final")
        ledger = pilot.run_pilot(root)
        found["a second final evaluation in the same cycle"] = _refused(
            lambda: pilot.final_evaluation(ledger, AGENT, root)
        )

        # region: new-cycle
        _edit(pilot.fixture(AGENT, root), lambda d: d["steps"][-1].update(text="tuned"))
        ledger.new_cycle("the fixture changed after the final evaluation of version 1")
        pilot.evaluate_attempt(ledger, "agent-2", AGENT, root, prior=("agent-1",))
        pilot.freeze(ledger, AGENT, "2", root)
        pilot.final_evaluation(ledger, AGENT, root)
        finals = summary(ledger, root).finals
        # endregion: new-cycle
        found["a change after the final evaluation, as a new cycle"] = "; ".join(
            f"version {f.version}, cycle {f.cycle}"
            + (", invalidated" if stale_ else ", valid")
            for f, stale_ in finals
        )
    experiment.table(
        "ae4-tampering",
        list(found.items()),
        [("what changed", "", ""), ("what the contract recorded", "", "")],
        "Each change made to a copy of the committed fixtures; the ledger's"
        " own records and refusals.",
    )
    return found


def _refused(action: Callable[[], object]) -> str:
    try:
        action()
    except ContractError as error:
        return f"refused: {str(error).split(';')[0]}"
    return "accepted"


def sealed_table(experiment: Experiment, ledger: Ledger) -> None:
    """The spring's candidates: development, selection, the sealed final."""
    (final,) = ledger.finals
    rows = []
    for evaluation in ledger.evaluations:
        candidate = ledger.attempt(evaluation.attempt).candidate
        chosen = candidate == final.candidate
        rows.append(
            (
                candidate,
                f"{evaluation.metrics['held_out_error']:.3f}",
                "yes" if evaluation.correct else "no",
                "yes" if chosen else "no",
                f"{final.evaluation.metrics['held_out_error']:.3f}"
                if chosen
                else "not evaluated",
            )
        )
    experiment.table(
        "ae4-sealed",
        rows,
        [
            ("candidate", "", ""),
            ("development error", "", ""),
            ("correct in development", "", ""),
            ("selected and frozen", "", ""),
            ("error on the sealed split", "", ""),
        ],
        "D2's three recorded runs on the spring: the development evaluation"
        " decided the selection; the sealed split was scored once, for the"
        " frozen candidate only.",
    )
    development = next(
        e
        for e in ledger.evaluations
        if ledger.attempt(e.attempt).candidate == final.candidate
    )
    experiment.number("selected", final.candidate)
    experiment.number(
        "selected-development", development.metrics["held_out_error"], ".3f"
    )
    experiment.number(
        "selected-sealed", final.evaluation.metrics["held_out_error"], ".3f"
    )
    experiment.number("sealed-tolerance", sealed.PROTOCOL.tolerance, "g")
    experiment.number("frozen-digest", final.digest[:12])
    experiment.number("frozen-version", final.version)


def draw_evaluator_scores(scored: Ledger, chosen: Ledger) -> Figure:
    """Two panels: the projectile candidates' recomputed and reported
    errors; the spring candidates' development errors and the frozen
    candidate's sealed error. Log scale, tolerance dashed."""
    with figure_style():
        fig, (top, bottom) = plt.subplots(2, 1, figsize=figsize("pair", legend=3))
        reports = {r.attempt: r for r in scored.reports}
        names = []
        for i, e in enumerate(scored.evaluations):
            names.append(scored.attempt(e.attempt).candidate)
            top.scatter(
                i,
                e.metrics["held_out_error"],
                marker="o",
                s=40,
                color=FIGURE_COLOURS[0],
                label="recomputed by the evaluator" if i == 0 else None,
                zorder=3,
            )
            report = reports.get(e.attempt)
            if report is not None and "held_out_error" in report.details:
                top.scatter(
                    i,
                    report.details["held_out_error"],
                    marker="s",
                    s=44,
                    facecolors="none",
                    edgecolors=FIGURE_COLOURS[1],
                    label="reported by the candidate, unverified",
                    zorder=3,
                )
        short = {
            AGENT: "agent",
            PLAIN: "plain\nmodel",
            pilot.BASELINE: "grid +\nleast squares",
        }
        top.set_xticks(range(len(names)), [short[n] for n in names])
        top.set_title("projectile: who computes the score")
        (final,) = chosen.finals
        labels = []
        for i, e in enumerate(chosen.evaluations):
            candidate = chosen.attempt(e.attempt).candidate
            labels.append(candidate)
            bottom.scatter(
                i,
                e.metrics["held_out_error"],
                marker="o",
                s=40,
                color=FIGURE_COLOURS[0],
                zorder=3,
            )
            if candidate == final.candidate:
                bottom.scatter(
                    i + 0.15,
                    final.evaluation.metrics["held_out_error"],
                    marker="D",
                    s=40,
                    color=FIGURE_COLOURS[4],
                    label="sealed split, frozen candidate only",
                    zorder=3,
                )
        bottom.set_xticks(
            range(len(labels)), [n.replace("told ", "told\n") for n in labels]
        )
        bottom.set_title("spring: development, then one sealed evaluation")
        for ax, tolerance in (
            (top, pilot.protocol().tolerance),
            (bottom, sealed.PROTOCOL.tolerance),
        ):
            ax.set_yscale("log")
            ax.axhline(
                tolerance,
                color=FIGURE_COLOURS[2],
                linestyle="--",
                linewidth=1.0,
                label="tolerance" if ax is top else None,
            )
            ax.set_ylabel("held-out error (relative)")
            ax.set_xlim(-0.5, len(ax.get_xticks()) - 0.5)
        fig.legend(loc="outside lower center", ncols=1)
    return finish(fig)


def run() -> Experiment:
    """Everything the lesson's page shows."""
    _read_where_named()
    experiment = Experiment()
    experiment.number("tolerance", pilot.protocol().tolerance, "g")
    scored = scoring()
    scoring_table(experiment, scored)
    tampering(experiment)
    chosen = sealed.run_sealed()
    sealed_table(experiment, chosen)
    experiment.figure(
        "fig-evaluator-scores", lambda: draw_evaluator_scores(scored, chosen)
    )
    return experiment


if __name__ == "__main__":
    main(run)
