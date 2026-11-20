"""The experiment of the lesson "Failure analysis, reviewer evaluation, and
regressions".

The panel of ``pbc.agents.review_lab``: the physics and numerics reviewers of
AI4, each recorded twice with the same prompt, over eight steppers whose
truth is known. Every session is replayed (each check executed again), its
decisions are read from its ``decide`` calls and classified
(``pbc.evidence.reviewers``), and every wrong decision gets what the
recomputed checks show. Then the evaluator's own rules on the same
recomputed checks: AI4's rule and the contract's, ablations of a reviewer
or a check, a rule fitted to AI4's two pieces, and two regressions, one in
the code under review and one in the evaluator. Run it as a program to write
the figure and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.failure_analysis_and_reviewer_evaluation out

AI4's page and its replay are not touched: its fixtures are only read.
"""

from functools import partial

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from pbc.agents import review_lab
from pbc.agents.display import RunDisplay
from pbc.agents.replay import ReplayMismatch
from pbc.agents.review_lab import (
    CANDIDATES,
    CASES,
    CLAIM,
    PANEL_SESSIONS,
    Case,
    PanelSession,
    Verdict,
    decisions,
    replay_fixtures,
    replay_panel,
    verdicts,
)
from pbc.authoring import FIGURE_COLOURS
from pbc.authoring.repository import REPOSITORY_ROOT
from pbc.evidence.reviewers import (
    CORRECT_ACCEPTANCE,
    CORRECT_REJECTION,
    FALSE_ALARM,
    MISSED_ERROR,
    NO_DECISION,
    ablate,
    agreement,
    any_failure_rule,
    cause,
    classify,
    contract_rule,
    energy_only_rule,
    outcomes,
    regressions,
    tally,
)
from pbc.experiment import Experiment, main
from pbc.figure_language import figsize, figure_style, finish

# The live run of the panel, with a model and its key and the extra openai.
LIVE = "pbc.agents.review_lab --panel"

AE6 = (
    REPOSITORY_ROOT
    / "site/lessons/agents-llm/24-failure-analysis-and-reviewer-evaluation"
)
AI4 = REPOSITORY_ROOT / "site/lessons/agents-llm/03-three-reviewers"

# AI4's two pieces as cases: what they are is known from its page.
AI4_CASES = {
    1: Case("symplectic Euler", CANDIDATES[1], CLAIM, False),
    2: Case("explicit Euler as symplectic", CANDIDATES[2], CLAIM, True),
}


def sessions() -> dict[str, tuple[PanelSession, list[Verdict], dict[int, bool]]]:
    """Every panel session replayed: its verdicts and its decisions."""
    found = {}
    for session in PANEL_SESSIONS:
        _, transcript = replay_panel(session, AE6)
        found[session.name] = (
            session,
            verdicts(session.reviewer, transcript),
            decisions(transcript),
        )
    return found


def session_table(experiment: Experiment, found) -> dict[str, dict[int, str]]:
    by_session = {}
    rows = []
    for name, (session, mine, decided) in found.items():
        result = outcomes(decided)
        by_session[name] = result
        t = tally(result)
        covered = {(v.candidate, v.check) for v in mine}
        rows.append(
            (
                session.reviewer.role,
                session.repeat,
                len(covered),
                f"{t.missed} of {t.faulty}",
                f"{t.false_alarms} of {t.correct}",
                t.undecided,
                session.model_messages,
                session.tool_calls,
            )
        )
    experiment.table(
        "ae6-sessions",
        rows,
        [
            ("reviewer", "", ""),
            ("repeat", "", "d"),
            ("checks run", "", "d"),
            ("missed errors", "", ""),
            ("false alarms", "", ""),
            ("no decision", "", "d"),
            ("model messages, recorded", "", "d"),
            ("tool calls, recorded", "", "d"),
        ],
        "Each recorded session of the panel, its decisions classified against"
        " the known truth of the eight pieces. The cost is the one each"
        " session reported; tokens and price were not reported.",
    )
    for role in ("physics", "numerics"):
        same = agreement(by_session[f"{role}-1"], by_session[f"{role}-2"])
        experiment.number(f"{role}-agreement", same)
    experiment.number("cases", len(CASES))
    experiment.number("faulty", sum(c.faulty for c in CASES.values()))
    experiment.number("correct", sum(not c.faulty for c in CASES.values()))
    return by_session


SYMBOL = {
    CORRECT_ACCEPTANCE: "accepted",
    CORRECT_REJECTION: "rejected",
    MISSED_ERROR: "MISSED",
    FALSE_ALARM: "FALSE ALARM",
    NO_DECISION: "-",
}


def case_table(experiment: Experiment, by_session) -> None:
    rows = []
    for number, case in CASES.items():
        rows.append(
            (
                number,
                case.name,
                "faulty" if case.faulty else "correct",
                *(SYMBOL[by_session[s.name][number]] for s in PANEL_SESSIONS),
            )
        )
    experiment.table(
        "ae6-cases",
        rows,
        [
            ("piece", "", "d"),
            ("what it is", "", ""),
            ("truth", "", ""),
            *((f"{s.reviewer.id} {s.repeat}", "", "") for s in PANEL_SESSIONS),
        ],
        "Every decision of every session. A wrong decision is in capitals:"
        " a faulty piece accepted (missed) or a correct one rejected (false"
        " alarm).",
    )


def cause_table(experiment: Experiment, found, by_session) -> None:
    rows = []
    for name, (session, mine, _) in found.items():
        for number, outcome in by_session[name].items():
            why = cause(number, outcome, mine)
            if why:
                rows.append(
                    (
                        f"{session.reviewer.id} {session.repeat}",
                        number,
                        outcome,
                        why,
                    )
                )
    experiment.table(
        "ae6-causes",
        rows,
        [
            ("session", "", ""),
            ("piece", "", "d"),
            ("outcome", "", ""),
            ("what the recomputed checks show", "", ""),
        ],
        "Every wrong decision, and every right one without a check that"
        " applies, with what the checks the session ran on the piece show;"
        " never its words.",
    )


def rules(experiment: Experiment, found) -> dict[str, dict[int, str]]:
    """The evaluator's rules, and ablations, on the recomputed checks of all
    four sessions (deterministic, so the sessions' checks agree)."""
    every = [v for _, mine, _ in found.values() for v in mine]
    # region: rules
    variants = {
        "AI4's rule, both reviewers": ablate(every, any_failure_rule),
        "the contract's rule, both reviewers": ablate(every, contract_rule),
        "the contract's rule, physics only": ablate(every, contract_rule, ["physics"]),
        "the contract's rule, numerics only": ablate(
            every, contract_rule, ["numerics"]
        ),
        "the contract's rule, without the order check": ablate(
            every, contract_rule, without_check="convergence-order"
        ),
        "the contract's rule, without the energy check": ablate(
            every, contract_rule, without_check="bounded-energy"
        ),
        "reject when the energy check fails": ablate(every, energy_only_rule),
    }
    # endregion: rules
    rows = []
    for name, result in variants.items():
        t = tally(result)
        rows.append(
            (name, f"{t.missed} of {t.faulty}", f"{t.false_alarms} of {t.correct}")
        )
    experiment.table(
        "ae6-rules",
        rows,
        [
            ("rule and panel", "", ""),
            ("missed errors", "", ""),
            ("false alarms", "", ""),
        ],
        "Rules that decide from the recomputed checks of the four sessions,"
        " and the same rules with a reviewer or a check removed.",
    )
    return variants


def overfitting(experiment: Experiment, variants) -> None:
    """The energy-only rule on AI4's two pieces, where it was chosen, and on
    the eight cases."""
    replays = replay_fixtures(AI4)
    ai4 = [
        v
        for reviewer in review_lab.REVIEWERS
        for v in verdicts(reviewer, replays[reviewer.id][1])
    ]
    decided = energy_only_rule(ai4, AI4_CASES)
    on_ai4 = tally(
        {n: classify(AI4_CASES[n].faulty, decided[n]) for n in AI4_CASES}, AI4_CASES
    )
    on_cases = tally(variants["reject when the energy check fails"])
    experiment.number("overfit-ai4-wrong", on_ai4.missed + on_ai4.false_alarms)
    experiment.number("overfit-ai4-cases", len(AI4_CASES))
    experiment.number("overfit-missed", on_cases.missed)
    experiment.number("overfit-false", on_cases.false_alarms)


def regression_checks(experiment: Experiment, variants) -> None:
    """Two regressions: a piece of code changed after the recording, which
    the replay of the frozen trace detects; and the evaluator's rule
    changed, which a comparison with the frozen outcomes detects."""
    # region: code-regression
    changed = dict(CASES)
    # The second piece replaced by AI4's second piece, a different step.
    changed[2] = Case(CASES[2].name, CANDIDATES[2], CASES[2].claim, False)
    session = next(s for s in PANEL_SESSIONS if s.name == "numerics-1")
    try:
        replay_panel(session, AE6, changed)
        detected = "not detected"
    except ReplayMismatch as error:
        detected = str(error).split(" (tolerance")[0]
    # endregion: code-regression
    experiment.number("code-regression", detected)
    frozen = variants["the contract's rule, both reviewers"]
    current = variants["AI4's rule, both reviewers"]
    found = regressions(frozen, current)
    experiment.table(
        "ae6-regressions",
        [
            (r.case, CASES[r.case].name, r.was, r.now, "yes" if r.worse else "no")
            for r in found
        ],
        [
            ("piece", "", "d"),
            ("what it is", "", ""),
            ("frozen outcome", "", ""),
            ("outcome now", "", ""),
            ("worse", "", ""),
        ],
        "The outcomes of the contract's rule, frozen, against AI4's rule"
        " applied to the same recorded checks: every case whose outcome"
        " changed.",
    )


MARKERS = {
    CORRECT_ACCEPTANCE: ("o", True, "correct acceptance"),
    CORRECT_REJECTION: ("s", True, "correct rejection"),
    MISSED_ERROR: ("X", False, "missed error"),
    FALSE_ALARM: ("^", False, "false alarm"),
    NO_DECISION: ("_", False, "no decision"),
}


def draw_review_outcomes(by_session) -> Figure:
    """Pieces against sessions; each decision's outcome by marker shape and
    fill, wrong decisions larger."""
    names = [s.name for s in PANEL_SESSIONS]
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line", legend=4))
        shown = set()
        for row, name in enumerate(names):
            for number in CASES:
                outcome = by_session[name][number]
                marker, right, label = MARKERS[outcome]
                colour = FIGURE_COLOURS[0] if right else FIGURE_COLOURS[1]
                ax.scatter(
                    number,
                    row,
                    marker=marker,
                    s=60 if right else 110,
                    color=colour,
                    label=label if outcome not in shown else None,
                    zorder=3,
                )
                shown.add(outcome)
        ax.set_xticks(
            list(CASES),
            [f"{n}\n{'F' if c.faulty else 'C'}" for n, c in CASES.items()],
        )
        ax.set_yticks(range(len(names)), [n.replace("-", " ") for n in names])
        ax.set_xlabel("piece (F faulty, C correct)")
        ax.set_ylim(len(names) - 0.5, -0.5)
        ax.grid(axis="x", color=FIGURE_COLOURS[2], linewidth=0.4, alpha=0.4)
        fig.legend(loc="outside lower center", ncols=1)
    return finish(fig)


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    found = sessions()
    by_session = session_table(experiment, found)
    session = next(s for s in PANEL_SESSIONS if s.name == "physics-1")
    experiment.display("physics-run", RunDisplay(*replay_panel(session, AE6)))
    case_table(experiment, by_session)
    cause_table(experiment, found, by_session)
    variants = rules(experiment, found)
    overfitting(experiment, variants)
    regression_checks(experiment, variants)
    experiment.figure("fig-review-outcomes", partial(draw_review_outcomes, by_session))
    return experiment


if __name__ == "__main__":
    main(run)
