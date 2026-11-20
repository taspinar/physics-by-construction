"""The experiment of the lesson "A prediction and its explanation".

A model predicts four quantities of a particle falling with linear drag,
with an interval, a unit, and an explanation chosen from candidate relations
(``pbc.agents.explanation_lab``). The recorded run is replayed; the build
tests each prediction against the exact solution and each explanation by its
unit, its dimensions, its physics, its support of the prediction, and its
interval. Two baselines without a model: a curve fit to the plotted points
and dimensional analysis. Then the experiment report: the run and the
baselines as a ledger of ``pbc.evidence``, and the report's statements,
each observed, computed, or proposed, traced to the ledger
(``pbc.evidence.report``). Run it as a program to write the figures and
numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.interpretable_physics_explanations out

The live run, which asks a model and needs its key, is a separate command
behind the optional dependency ``openai``: the module ``LIVE``, run with
``uv run --locked --no-dev --extra openai python -m pbc.agents.explanation_lab``.
"""

import json
import platform
import shutil
import tempfile
from collections import Counter
from dataclasses import asdict
from functools import partial
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.agents.display import AllowlistDisplay, RunDisplay
from pbc.agents.explanation_lab import (
    AGREEMENT,
    MAX_STEPS,
    PICTURE,
    PREDICTION_TOLERANCE,
    PROMPT_VERSION,
    QUESTIONS,
    TASK,
    curve_fit_baseline,
    dimensional_baseline,
    examine,
    explain_sheet,
    replay_fixture,
    tested,
    verified,
)
from pbc.authoring import FIGURE_COLOURS
from pbc.authoring.repository import REPOSITORY_ROOT
from pbc.evidence import (
    COMPLETED,
    Artifact,
    Attempt,
    Claim,
    Evaluation,
    Ledger,
    RunRecord,
    digest_value,
)
from pbc.evidence.records import digest_file
from pbc.evidence.report import COMPUTED, OBSERVED, PROPOSED, Statement, trace
from pbc.experiment import Experiment, main

# The live run of the lesson: a model, its key, and the extra openai.
LIVE = "pbc.agents.explanation_lab"

# The recorded run, next to the page that shows it.
LESSON = (
    REPOSITORY_ROOT / "site/lessons/agents-llm/17-interpretable-physics-explanations"
)


def _yes(passed: bool | None) -> str:
    return "none" if passed is None else ("yes" if passed else "no")


def explanation_rows(found):
    """One row per question: what the model said, apart from what the build
    verified, and each test."""
    return [
        (
            t.asked.number,
            f"{t.value:g} [{t.low:g}, {t.high:g}] {t.unit}",
            t.relation,
            f"{t.truth:.4g} {t.asked.unit}",
            _yes(t.prediction),
            _yes(t.unit_right),
            _yes(t.dimensions),
            _yes(t.physics),
            _yes(t.support),
            _yes(t.covers),
        )
        for t in found
    ]


def baseline_rows(found, fit, forms):
    """One row per question: the verified result, the model, the curve fit,
    and the relations dimensional analysis leaves."""
    rows = []
    for t in found:
        n = t.asked.number
        close = abs(fit[n] - t.truth) <= PREDICTION_TOLERANCE * abs(t.truth)
        left = forms[n]
        rows.append(
            (
                n,
                f"{t.truth:.4g}",
                f"{t.value:g}",
                f"{fit[n]:.4g} ({'within' if close else 'outside'})",
                left[0] if len(left) == 1 else f"not identified: {len(left)} left",
            )
        )
    return rows


def draw_intervals(found, fit) -> Figure:
    """Each prediction and its interval over the verified result, with the
    curve fit's prediction and the tolerance of a prediction."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    x = np.arange(len(found))
    ax.axhspan(
        1 - PREDICTION_TOLERANCE,
        1 + PREDICTION_TOLERANCE,
        color=FIGURE_COLOURS[2],
        alpha=0.15,
        label="tolerance of a prediction",
    )
    ax.axhline(1.0, color=FIGURE_COLOURS[2], linestyle=":", linewidth=0.8)
    ratio = [t.value / t.truth for t in found]
    below = [(t.value - t.low) / t.truth for t in found]
    above = [(t.high - t.value) / t.truth for t in found]
    ax.errorbar(
        x - 0.1,
        ratio,
        yerr=[below, above],
        fmt="o",
        color=FIGURE_COLOURS[0],
        capsize=4,
        label="model: prediction and its interval",
    )
    ax.scatter(
        x + 0.1,
        [fit[t.asked.number] / t.truth for t in found],
        marker="s",
        color=FIGURE_COLOURS[1],
        label="curve fit to the plotted points",
        zorder=3,
    )
    ax.set_xticks(x, [f"Q{t.asked.number}" for t in found])
    ax.set_xlabel("question")
    ax.set_ylabel("prediction over the verified result")
    ax.set_ylim(0.4, 1.2)
    ax.legend(fontsize=8, loc="lower left")
    return fig


def constructed_examples():
    """Exercise 1: two answers written for the exercise, not by a model,
    tested like the recorded ones."""
    q4 = QUESTIONS[3]
    truth = verified()[4]
    answers = (
        {
            "value": round(truth, 1),
            "low": round(truth, 1) - 1.0,
            "high": round(truth, 1) + 1.0,
            "unit": "m/s",
            "relation": "v = g t",
        },
        {
            "value": 30.0,
            "low": 28.0,
            "high": 32.0,
            "unit": "m/s",
            "relation": "v = (m g / b) (1 - exp(-b t / m))",
        },
        {
            "value": round(truth, 1),
            "low": round(truth, 1) - 1.0,
            "high": round(truth, 1) + 1.0,
            "unit": "m/s",
            "relation": "v = (m g / b) (1 - exp(-t))",
        },
    )
    return [
        (
            k,
            f"{a['value']:g} [{a['low']:g}, {a['high']:g}] {a['unit']}",
            a["relation"],
            *(
                _yes(getattr(t, name))
                for name in ("prediction", "dimensions", "physics", "support")
            ),
        )
        for k, a in enumerate(answers, start=1)
        for t in [examine(q4, truth, a)]
    ]


# --- The experiment report (SA8). ---

# The recorded run; the ledger's artifacts are named relative to the lesson.
RECORDING = (
    REPOSITORY_ROOT
    / "site/lessons/agents-llm/17-interpretable-physics-explanations/replay.json"
)
# This module, by the path the build's digest of the lesson can follow.
EXPERIMENT_SOURCE = (
    REPOSITORY_ROOT
    / "src/pbc/mechanics/experiments/interpretable_physics_explanations.py"
)
EVALUATOR = "pbc.mechanics.experiments.interpretable_physics_explanations, version 1"
COUNTERFACTUAL = 3  # the question about a heavier particle
# The assumptions of the page, in its order: a statement names them by number.
ASSUMPTIONS = (
    "The scene is given.",
    "The verified result is the exact solution.",
    "An explanation is one relation from a list.",
    f"A prediction is right within {100 * PREDICTION_TOLERANCE:.0f} per cent.",
    "The model's words are data.",
)


def run_record() -> RunRecord:
    """The task as the evaluator states it. The digests and the environment
    identify the run in the ledger and never reach the page."""
    sources = (
        ("explanation_lab", REPOSITORY_ROOT / "src/pbc/agents/explanation_lab.py"),
        ("drag", REPOSITORY_ROOT / "src/pbc/mechanics/drag.py"),
        ("experiment", EXPERIMENT_SOURCE),
    )
    return RunRecord(
        task=TASK,
        hypothesis=(
            "A model's predictions and the explanations it gives for them can"
            " be tested apart; a right prediction does not make its"
            " explanation right."
        ),
        assumptions=ASSUMPTIONS,
        protocol_version=f"explanation lab, prompt version {PROMPT_VERSION}",
        split={
            "given": "the picture and the given values of the scene",
            "verified": "the exact solution, computed by the build, never shown",
        },
        seeds=(),
        budgets={"model messages": MAX_STEPS},
        code=digest_value([(name, digest_file(path)) for name, path in sources]),
        configuration=digest_value([asdict(q) for q in QUESTIONS]),
        environment={"python": platform.python_version(), "numpy": np.__version__},
    )


def _passes(t) -> bool:
    """The prediction and every test of its explanation pass."""
    return bool(
        t.prediction
        and t.unit_right
        and t.dimensions
        and t.physics
        and t.support
        and t.covers
    )


def ledger(found, fit, forms) -> Ledger:
    """The recorded run and the two baselines as attempts, each evaluated by
    the build, and the claims of the report, each with the outcome it
    asserts for its runs: constants of the claim, never read from the
    evaluations, so that an evaluation can contradict them."""
    record = run_record()
    book = Ledger(record)
    recording = Artifact.of("recorded run", RECORDING, LESSON)

    def evaluate(attempt, correct, metrics, depends_on=()):
        book.add_evaluation(
            Evaluation(
                attempt,
                EVALUATOR,
                correct,
                metrics,
                {},
                depends_on,
                record.code,
                record.configuration,
            )
        )

    # The recording replayed (``replay_fixture`` raises when it does not).
    book.add_attempt(
        Attempt("recording", "the recorded model", 1, COMPLETED, (), (recording,))
    )
    evaluate("recording", True, {"answers": len(found)}, (recording,))
    for t in found:
        n = t.asked.number
        book.add_attempt(
            Attempt(f"model Q{n}", "the recorded model", 1, COMPLETED, (), (recording,))
        )
        ratio = {"prediction over verified": t.value / t.truth}
        evaluate(f"model Q{n}", _passes(t), ratio, (recording,))
        book.add_attempt(Attempt(f"fit Q{n}", "curve fit", 1, COMPLETED))
        close = abs(fit[n] - t.truth) <= PREDICTION_TOLERANCE * abs(t.truth)
        evaluate(f"fit Q{n}", close, {"prediction over verified": fit[n] / t.truth})
        book.add_attempt(
            Attempt(f"dimensions Q{n}", "dimensional analysis", 1, COMPLETED)
        )
        evaluate(f"dimensions Q{n}", len(forms[n]) == 1, {"left": len(forms[n])})

    numbers = [q.number for q in QUESTIONS]
    scope = "one recorded run, the linear-drag fall of Newton's laws"
    for claim in (
        Claim("recording", "The recording replays.", scope, {"recording": True}),
        Claim(
            "model-answers",
            "Every prediction and every explanation passes.",
            scope,
            {f"model Q{n}": True for n in numbers},
        ),
        Claim(
            "fit-counterfactual",
            "The curve fit misses the counterfactual question only.",
            "the linear-drag fall of Newton's laws",
            {f"fit Q{n}": n != COUNTERFACTUAL for n in numbers},
        ),
        Claim(
            "dimensional-forms",
            "Dimensional analysis identifies the terminal speeds and the time"
            " constant, not the velocity at a time.",
            "the candidate relations of this lesson",
            {f"dimensions Q{n}": n != 4 for n in numbers},
        ),
    ):
        book.add_claim(claim)
    return book


def report(found) -> tuple[Statement, ...]:
    """The statements of the report, as an author writes them."""
    widest = max(found, key=lambda t: (t.high - t.low) / t.value)
    tolerance = f"{100 * PREDICTION_TOLERANCE:.0f} per cent"
    n = len(found)
    statements = (
        Statement(
            "answers",
            f"All {n} predictions are within {tolerance} of the verified"
            f" result, and all {n} explanations pass the unit, scaling,"
            " physics, and support tests.",
            COMPUTED,
            record="model-answers",
            plots=("ai7-explanations", "fig-explanation-intervals"),
            assumptions=(2, 3, 4),
            uncertainty=f"a prediction counts within {tolerance}; one run",
        ),
        Statement(
            "fit",
            f"The curve fit is outside {tolerance} on question"
            f" {COUNTERFACTUAL}, the heavier particle, and within it on the"
            " other three.",
            COMPUTED,
            record="fit-counterfactual",
            plots=("ai7-baselines", "fig-explanation-intervals"),
            assumptions=(1, 2, 4),
            uncertainty=f"a prediction counts within {tolerance}; one fit",
        ),
        Statement(
            "dimensions",
            "Dimensional analysis leaves one candidate relation for the"
            " terminal speeds and the time constant, and several for the"
            " velocity after four seconds.",
            COMPUTED,
            record="dimensional-forms",
            plots=("ai7-baselines",),
            assumptions=(3,),
            uncertainty=f"a scaling test at two changes of units, to {AGREEMENT:.0e}",
        ),
        Statement(
            "interval",
            "The model's widest interval for its prediction is on question"
            f" {widest.asked.number}: {widest.low:g} to {widest.high:g}"
            f" {widest.unit} around {widest.value:g} {widest.unit}.",
            OBSERVED,
            record="recording",
            plots=("ai7-explanations", "fig-explanation-intervals"),
            assumptions=(5,),
            uncertainty="exact as recorded; another run gives other intervals",
        ),
        Statement(
            "harder-scene",
            "A scene in which the picture and the given values disagree"
            " could separate the model's predictions from its explanations.",
            PROPOSED,
        ),
    )
    return statements


def _runs(book: Ledger, runs) -> str:
    by = Counter(book.attempt(r).candidate for r in runs)
    return "; ".join(
        f"{candidate}: {count} attempt{'s' if count > 1 else ''}"
        for candidate, count in by.items()
    )


def report_rows(traced):
    """One row per statement: its kind and the evidence status the ledger
    gives it."""
    return [
        (t.statement.id, t.statement.text, t.statement.kind, t.status) for t in traced
    ]


def trace_rows(traced, book: Ledger):
    """One row per statement: the runs, the data, the figures and tables,
    the assumptions, and the uncertainty it is traced to."""
    rows = []
    for t in traced:
        s = t.statement
        rows.append(
            (
                s.id,
                _runs(book, t.runs) or "none",
                ", ".join(Path(a).name for a in t.artifacts)
                or ("none: computed by the build" if t.runs else "none"),
                ", ".join(s.plots) or "none",
                ", ".join(str(a) for a in s.assumptions) or "none",
                s.uncertainty or "none",
            )
        )
    return rows


def _edit_an_interval(path: Path) -> None:
    """Widen the first recorded interval by one tenth of its upper end."""
    data = json.loads(path.read_text(encoding="utf-8"))
    for step in data["steps"]:
        for call in step["tool_calls"]:
            if "high" in call["arguments"]:
                call["arguments"]["high"] *= 1.1
                path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
                return


def changed_recording(statements, book: Ledger):
    """Exercise: the report traced again after one interval of a copy of the
    recording was edited."""
    before = trace(statements, book, LESSON)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        copy = root / RECORDING.name
        shutil.copyfile(RECORDING, copy)
        _edit_an_interval(copy)
        after = trace(statements, book, root)
    return [
        (b.statement.id, b.statement.kind, b.status, a.status)
        for b, a in zip(before, after, strict=True)
    ]


def report_on_the_page(experiment: Experiment, found, fit, forms) -> None:
    """The tables of the section on the experiment report."""
    book = ledger(found, fit, forms)
    statements = report(found)
    traced = trace(statements, book, LESSON)
    experiment.number("report-statements-count", len(statements), "d")
    experiment.table(
        "report-statements",
        report_rows(traced),
        [
            ("id", "", ""),
            ("statement", "", ""),
            ("kind", "", ""),
            ("evidence status", "", ""),
        ],
        "The statements of the report, each with the kind its author gave it"
        " and the evidence status the ledger gives its record.",
    )
    experiment.table(
        "report-traces",
        trace_rows(traced, book),
        [
            ("id", "", ""),
            ("runs", "", ""),
            ("data", "", ""),
            ("shown in", "", ""),
            ("assumptions", "", ""),
            ("uncertainty", "", ""),
        ],
        "What each statement is traced to: the runs of its record, the data"
        " those runs produced, the figures and tables of this page, the"
        " assumptions by their number, and the uncertainty.",
    )
    experiment.table(
        "report-changed",
        changed_recording(statements, book),
        [
            ("id", "", ""),
            ("kind", "", ""),
            ("status", "", ""),
            ("after the edit", "", ""),
        ],
        "The evidence status of each statement, traced against the recording"
        " and against a copy of it with one interval edited.",
    )


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.figure("fig-explanation-picture", PICTURE.draw)

    # region: replay
    recording, transcript = replay_fixture(LESSON)
    found = tested(transcript)
    # endregion: replay
    experiment.display("allowlist", AllowlistDisplay(explain_sheet()))
    experiment.display("run", RunDisplay(recording, transcript))
    experiment.number("recorded", recording.recorded)
    experiment.number("prediction-tolerance", 100 * PREDICTION_TOLERANCE, ".0f")
    experiment.number("agreement", AGREEMENT, ".0e")
    experiment.number("questions", len(QUESTIONS), "d")
    experiment.number("predictions-right", sum(t.prediction for t in found), "d")
    experiment.number(
        "explanations-right",
        sum(
            bool(t.unit_right and t.dimensions and t.physics and t.support)
            for t in found
        ),
        "d",
    )

    experiment.table(
        "ai7-explanations",
        explanation_rows(found),
        [
            ("question", "", "d"),
            ("the model's prediction [interval]", "", ""),
            ("the model's explanation", "", ""),
            ("verified result", "", ""),
            ("prediction", "", ""),
            ("unit", "", ""),
            ("dimensions", "", ""),
            ("physics", "", ""),
            ("support", "", ""),
            ("interval", "", ""),
        ],
        "What the recorded model said (its prediction, interval, unit, and the"
        " relation it chose) beside the verified result the build computed from"
        " the exact solution, and each test the build ran on the prediction and"
        " on the explanation.",
    )
    fit, forms = curve_fit_baseline(), dimensional_baseline()
    experiment.table(
        "ai7-baselines",
        baseline_rows(found, fit, forms),
        [
            ("question", "", "d"),
            ("verified result", "", ""),
            ("model", "", ""),
            ("curve fit", "", ""),
            ("dimensional analysis", "", ""),
        ],
        "The verified result, the model's prediction, the prediction of a curve"
        " fitted to the plotted points (within or outside the tolerance), and"
        " the candidate relations that pass the scaling test.",
    )
    experiment.figure("fig-explanation-intervals", partial(draw_intervals, found, fit))
    experiment.table(
        "ai7-examples",
        constructed_examples(),
        [
            ("answer", "", "d"),
            ("prediction [interval]", "", ""),
            ("explanation", "", ""),
            ("prediction", "", ""),
            ("dimensions", "", ""),
            ("physics", "", ""),
            ("support", "", ""),
        ],
        "Three answers to the question of the velocity after four seconds,"
        " written for the exercise, tested as the recorded ones are.",
    )
    report_on_the_page(experiment, found, fit, forms)
    return experiment


if __name__ == "__main__":
    main(run)
