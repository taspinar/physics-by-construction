"""The experiment of the lesson "Independently checkable reports and research
memory".

The investigation of the slow throw, from the idea archive of RR1 to the
revised claim of RR6, written up as a report whose numbers are typed by its
author. ``pbc.research.report`` resolves every number to a field of a record
and every citation to a quoted passage of RR3's corpus in the role the
label rule gives it; a sentence no record supports is marked. The records
form a bundle that is computed again and compared by digest. What the
investigation leaves for the next one is kept in a research memory
(``pbc.research.memory``) and handed over only to a reuse whose identities
match. Run it as a program to write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.checkable_reports_and_research_memory out
"""

import dataclasses
from functools import partial
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS, diagrams
from pbc.evidence.records import digest_value
from pbc.evidence.report import MARKED
from pbc.experiment import Experiment, main
from pbc.figure_language import MARKER, MUTED, figsize, figure_style, finish
from pbc.mechanics.experiments import discrepancies_and_follow_up_experiments as rr6
from pbc.mechanics.experiments import generating_and_selecting_research_ideas as rr1
from pbc.mechanics.experiments.from_question_to_research_plan import (
    ORIGINAL,
    REPLICATION,
    run_plan,
)
from pbc.research import followup
from pbc.research.corpus import PASSAGES, STATEMENTS
from pbc.research.followup import record_digest
from pbc.research.ideas import select
from pbc.research.memory import (
    CODE,
    DATA,
    IDEA,
    LIMITATION,
    QUESTION,
    RESULT,
    Item,
    Memory,
    ReuseRefused,
    recall,
)
from pbc.research.report import (
    PASSAGE,
    RECORD,
    REFUSED,
    Quantity,
    Recipe,
    Sentence,
    bundle,
    check_report,
    code_identity,
    problems,
    reproduce,
)

PBC = Path(__file__).resolve().parents[2]  # src/pbc, where the code files are
SPECIFICATION_CODE = PBC / "agents" / "specification.py"
EDITED = PBC / "mechanics" / "projectile.py"
INTEGRATORS_CODE = PBC / "mechanics" / "integrators.py"
DRAG_CODE = PBC / "mechanics" / "drag.py"
REVIEW_CODE = (
    PBC / "mechanics" / "experiments" / "discrepancies_and_follow_up_experiments.py"
)
PLAN_CODE = PBC / "research" / "plan.py"
PLANS_CODE = PBC / "mechanics" / "experiments" / "from_question_to_research_plan.py"
IDEAS_CODE = PBC / "research" / "ideas.py"
ARCHIVE_CODE = (
    PBC / "mechanics" / "experiments" / "generating_and_selecting_research_ideas.py"
)
CORPUS_CODE = PBC / "research" / "corpus.py"
FOLLOWUP_CODE = PBC / "research" / "followup.py"


def route_code() -> tuple[Path, ...]:
    """The source files of a run of the review lesson's route."""
    return (SPECIFICATION_CODE, EDITED, INTEGRATORS_CODE, DRAG_CODE, REVIEW_CODE)


def archive_record() -> dict:
    found = rr1.assessments()
    selected = select(found, rr1.JUDGEMENTS)
    return {"ideas": len(rr1.IDEAS), "selected": selected}


def plan_record(plan: dict) -> dict:
    record = run_plan(plan)
    low, _, high = record.record.bracket
    return {
        "speed": plan["specification"]["variables"]["speed"]["value"],
        "bound": plan["specification"]["hypothesis"]["prediction"]["value"],
        "control": plan["baselines"]["control"]["answer"],
        "tolerance": (
            plan["baselines"]["control"]["answer"]
            - plan["specification"]["hypothesis"]["prediction"]["value"]
        ),
        "low": low,
        "high": high,
        "withheld": record.withheld[0].best,
        "runs": record.runs,
        "verdict": record.verdict,
    }


def corpus_record() -> dict:
    return {
        "passages": len(PASSAGES),
        "lessons": len({p.lesson for p in PASSAGES}),
    }


def test_record(test: followup.FollowUp) -> dict:
    record = rr6.run_route(test.specification)
    low, _, high = record.bracket
    variables = test.specification["variables"]
    return {
        "cd": variables["cd"]["value"] if "cd" in variables else rr6.COEFFICIENT,
        "resolution": test.specification["success"]["resolution"]["value"],
        "low": low,
        "high": high,
        "verdict": record.verdict,
    }


def review_record(log: followup.Log) -> dict:
    statuses = [followup.status(log, key) for key in log.findings]
    return {
        "findings": len(statuses),
        "resolved": statuses.count(followup.RESOLVED),
        "reworded": statuses.count(followup.REWORDED),
        "inconclusive": statuses.count(followup.INCONCLUSIVE),
        "open": statuses.count(followup.OPEN),
    }


def recipes() -> dict[str, Recipe]:
    """How each record of the report is made."""

    def recipe(compute, configuration, code) -> Recipe:
        return Recipe(compute, configuration, code)

    plans = (SPECIFICATION_CODE, EDITED, PLAN_CODE, PLANS_CODE)

    def test(t: followup.FollowUp) -> Recipe:
        return recipe(partial(test_record, t), t.specification, route_code())

    return {
        "archive": recipe(
            archive_record,
            [i.key for i in rr1.IDEAS],
            (IDEAS_CODE, ARCHIVE_CODE),
        ),
        "original-plan": recipe(partial(plan_record, ORIGINAL), ORIGINAL, plans),
        "replication-plan": recipe(
            partial(plan_record, REPLICATION), REPLICATION, plans
        ),
        "corpus": recipe(corpus_record, [p.key for p in PASSAGES], (CORPUS_CODE,)),
        "fourth-order": test(rr6.FOURTH_ORDER),
        "below-the-top": test(rr6.BELOW_THE_TOP),
        "top-at-half-degree": test(rr6.TOP_AT_HALF_DEGREE),
        "review": recipe(
            lambda: review_record(rr6.follow_up()[0]),
            [f.key for f in rr6.FINDINGS],
            (*route_code(), FOLLOWUP_CODE),
        ),
    }


def q(record: str, field: str) -> Quantity:
    return Quantity(record, field)


# region: sentence
REPLICATION_SENTENCE = Sentence(
    "replication",
    "The same procedure at 25 m/s reproduced the verdict of the lesson it"
    " replicates, whose passage supports it [@sa1-bracket].",
    (q("replication-plan", "speed"),),
    {"sa1-bracket": "supports"},
    claim="replication",
)
# endregion: sentence

REPORT = (
    Sentence(
        "question",
        "Of 7 ideas about the simulated tennis ball, a rule declared before the"
        " assessment selected this question: is the best launch angle at 10 m/s"
        " within 2 degrees of the 45 of a throw without drag?",
        (
            q("archive", "ideas"),
            q("original-plan", "speed"),
            q("original-plan", "tolerance"),
            q("original-plan", "control"),
        ),
    ),
    Sentence(
        "plan",
        "A plan frozen before its first run put the best angle between 43.75 and"
        " 44.375 degrees, above the predicted bound of 43, in 93 runs of all"
        " stages; its withheld test peaked at 43.94 degrees, inside that bracket.",
        (
            q("original-plan", "low"),
            q("original-plan", "high"),
            q("original-plan", "bound"),
            q("original-plan", "runs"),
            q("original-plan", "withheld"),
        ),
    ),
    REPLICATION_SENTENCE,
    Sentence(
        "literature",
        "The projectile lesson anticipates the direction for a slow throw"
        " [@m3-ratio] but gives no bound, and none of 12 passages of the corpus"
        " decides the claim.",
        (q("corpus", "passages"),),
        {"m3-ratio": "insufficient"},
        claim="slow-throw",
    ),
    Sentence(
        "guess",
        "The guess that drag leaves the best angle at 45 degrees for any ball is"
        " contradicted by the passages [@m3-flatter] and [@sa5-moves-lower].",
        (q("original-plan", "control"),),
        {"m3-flatter": "contradicts", "sa5-moves-lower": "contradicts"},
        claim="no-change",
    ),
    Sentence(
        "method",
        "Stepped by the fourth-order method, the route gave the same bracket,"
        " 43.75 to 44.375 degrees.",
        (q("fourth-order", "low"), q("fourth-order", "high")),
    ),
    Sentence(
        "coefficient",
        "With the drag coefficient at 0.8 the bracket was 43.125 to 43.75"
        " degrees, above the bound; at 1.0, to 0.5 degrees, it was 42.969 to"
        " 43.281 degrees, and the route could not decide.",
        (
            q("below-the-top", "cd"),
            q("below-the-top", "low"),
            q("below-the-top", "high"),
            q("top-at-half-degree", "cd"),
            q("top-at-half-degree", "resolution"),
            q("top-at-half-degree", "low"),
            q("top-at-half-degree", "high"),
        ),
    ),
    Sentence(
        "review",
        "Of 4 review findings, 2 were resolved by new evidence, 1 by a revision"
        " of the wording, and 1 is open: no measured throw was compared.",
        (
            q("review", "findings"),
            q("review", "resolved"),
            q("review", "reworded"),
            q("review", "open"),
        ),
    ),
    Sentence(
        "outlook",
        "A real ball would probably land furthest a little lower still, since"
        " its coefficient is uncertain and its spin adds lift.",
        marked=True,
    ),
)


def planted() -> tuple[Sentence, ...]:
    """The report with three errors: a number mistyped, a passage cited in a
    role it does not play, and a number with no record."""
    changed = list(REPORT)
    for position, sentence in enumerate(changed):
        if sentence.key == "plan":
            changed[position] = dataclasses.replace(
                sentence, text=sentence.text.replace("43.75 and", "43.57 and")
            )
        elif sentence.key == "literature":
            changed[position] = dataclasses.replace(
                sentence,
                text=sentence.text.replace(
                    "anticipates the direction for", "supports the claim for"
                ),
                citations={"m3-ratio": "supports"},
            )
        elif sentence.key == "method":
            changed[position] = dataclasses.replace(
                sentence, text=sentence.text.replace("degrees.", "degrees in 20 runs.")
            )
    return tuple(changed)


# region: rounded
ROUNDED = Sentence(
    "rounded",
    "The plan's bracket was 43.8 to 44.4 degrees.",
    (q("original-plan", "low"), q("original-plan", "high")),
)
# endregion: rounded


def bare_result(kept: Memory) -> str:
    """What the memory answers when the revised result is kept again under
    another key, without its limitations."""
    result = kept.items["slow-throw-result"]
    try:
        kept.store(dataclasses.replace(result, key="slow-throw-bare", links=()))
    except ReuseRefused as refused:
        return "; ".join(refused.reasons)
    return ""


def records(entries) -> dict[str, dict]:
    return {name: dict(entry.fields) for name, entry in entries.items()}


def check(sentences, fields) -> list:
    return check_report(sentences, fields, PASSAGES, STATEMENTS)


def memory(kept: dict[str, Recipe]) -> Memory:
    """What the investigation leaves for the next one."""
    log, _ = rr6.follow_up()
    found = rr1.assessments()
    archive = rr1.archive(found, select(found, rr1.JUDGEMENTS))
    middle = next(e for e in archive.entries if e.idea.key == "middle-throw")
    decisions = {
        e.content["finding"]: e.content["revisit"]
        for e in log.entries
        if "revisit" in e.content
    }
    kept_memory = Memory()
    for item in (
        Item(
            "middle-throw",
            IDEA,
            middle.idea.question,
            f"the archive of the ideas lesson, entry {middle.number}",
            {"archive entry": middle.digest},
            revisit=middle.revisit,
        ),
        Item(
            "route",
            CODE,
            "The scripted route of the specification lesson and its laboratory.",
            "src/pbc/agents/specification.py",
            {"code": code_identity(kept["below-the-top"])},
        ),
        Item(
            "slow-throw-runs",
            DATA,
            "Every run of the route of the original plan.",
            "the record of the original plan",
            {"record": record_digest(run_plan(ORIGINAL).record)},
        ),
        Item(
            "simulated-only",
            LIMITATION,
            "Every run is a simulation of one model of the ball.",
            "the review, finding real-ball",
            {"log": log.entries[-1].digest},
        ),
        Item(
            "one-degree",
            LIMITATION,
            "The route resolves the best angle to about a degree.",
            "the specification of the slow throw",
            {"configuration": digest_value(rr1.SLOW_THROW)},
        ),
        Item(
            "between-the-runs",
            LIMITATION,
            "The range of coefficients assumes the best angle falls as the drag grows.",
            "the ablation of the review lesson",
            {"log": log.entries[-1].digest},
        ),
        Item(
            "where-it-fails",
            QUESTION,
            "Where between 0.8 and 1.0 does the best angle reach the bound?",
            "the review, finding coefficient",
            {"log": log.entries[-1].digest},
            revisit=decisions["coefficient"],
        ),
        Item(
            "measured-throw",
            QUESTION,
            "Does a measured throw at 10 m/s land furthest above 43 degrees?",
            "the review, finding real-ball",
            {"log": log.entries[-1].digest},
            revisit=decisions["real-ball"],
        ),
        Item(
            "slow-throw-result",
            RESULT,
            rr6.REVISED,
            "the revised claim of the review lesson",
            {
                "code": code_identity(kept["below-the-top"]),
                "configuration": digest_value(rr1.SLOW_THROW),
            },
            links=(
                "simulated-only",
                "one-degree",
                "between-the-runs",
                "where-it-fails",
                "measured-throw",
            ),
        ),
    ):
        kept_memory.store(item)
    return kept_memory


def reuse(kept: Memory, key: str, presented: dict) -> tuple[str, str]:
    """The outcome of a reuse of ``key`` presenting ``presented``, and what
    comes with it or why it was refused."""
    try:
        found = recall(kept, key, presented)
    except ReuseRefused as refused:
        return "refused", "; ".join(refused.reasons)
    attached = ", ".join(i.key for i in found.attached)
    revisit = f"revisit when: {found.item.revisit}" if found.item.revisit else ""
    return "handed over", attached or revisit


def draw_report_trace() -> Figure:
    """A sentence of the report, its number to a record and the bundle, its
    citation to a passage and its page, and a marked sentence, as a sketch."""
    fig, ax = diagrams.canvas(6.4, 4.4, (0.0, 12.8), (0.0, 8.8))
    diagrams.state_box(ax, (1.9, 4.4), "sentence\nof the report", width=3.0, height=1.2)
    rows = (
        (7.4, "number", "field of\na record", "bundle: computed\nagain, compared"),
        (4.4, "citation", "quoted\npassage", "label for\nthe claim"),
    )
    for y, what, first, second in rows:
        diagrams.arrow(ax, (3.4, 4.4 + (y - 4.4) * 0.15), (5.0, y))
        diagrams.text(
            ax,
            (4.0, 6.6) if y > 5 else (4.2, 4.85),
            what,
            ha="right" if y > 5 else "center",
        )
        diagrams.state_box(ax, (6.3, y), first, width=2.6, height=1.1)
        diagrams.arrow(ax, (7.6, y), (8.7, y))
        diagrams.state_box(ax, (10.6, y), second, width=3.4, height=1.1)
    diagrams.arrow(ax, (1.9, 3.8), (1.9, 2.2), colour=MUTED, linestyle=":")
    diagrams.state_box(
        ax,
        (1.9, 1.5),
        "marked: proposed,\nnot evaluated",
        width=3.2,
        height=1.1,
        colour=MUTED,
    )
    diagrams.text(
        ax,
        (6.3, 1.5),
        "a number or citation\nthat resolves to\nnothing: refused",
        colour=1,
    )
    return fig


STYLES = {
    RECORD: ("o", 0, "record"),
    PASSAGE: ("s", 1, "passage"),
    MARKED: ("D", None, "marked"),
    REFUSED: ("X", 2, "refused"),
}


def draw_report_checks(panels) -> Figure:
    """For each sentence (rows), each number and citation in order
    (columns), marked by what it resolved to; one panel per report."""
    with figure_style():
        fig, axes = plt.subplots(
            len(panels), 1, figsize=figsize("pair", legend=2), sharex=True
        )
        shown = set()
        for ax, (title, resolutions) in zip(axes, panels, strict=True):
            keys = list(dict.fromkeys(r.sentence for r in resolutions))
            for row, key in enumerate(keys):
                y = len(keys) - 1 - row
                for column, r in enumerate(x for x in resolutions if x.sentence == key):
                    marker, colour, label = STYLES[r.kind]
                    colour = MUTED if colour is None else FIGURE_COLOURS[colour]
                    ax.plot(
                        column + 1,
                        y,
                        linestyle="none",
                        marker=marker,
                        markersize=MARKER * 1.5,
                        color=colour,
                        markerfacecolor="none" if r.kind == MARKED else colour,
                        label=None if label in shown else label,
                    )
                    shown.add(label)
            ax.set_yticks(range(len(keys))[::-1], keys)
            ax.set_ylim(-0.7, len(keys) - 0.3)
            ax.set_title(title, loc="left")
        axes[-1].set_xlabel("number or citation, in the order of the sentence")
        widest = max(int(ax.get_xlim()[1]) for ax in axes)
        axes[-1].set_xticks(range(1, widest + 1))
        axes[-1].set_xlim(0.5, widest + 0.5)
        handles = [h for ax in axes for h in ax.get_legend_handles_labels()[0]]
        axes[-1].legend(
            handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.3), ncol=2
        )
    return finish(fig)


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.figure("fig-report-trace", draw_report_trace)
    kept = recipes()
    entries = bundle(kept)
    fields = records(entries)
    written = check(REPORT, fields)
    experiment.table(
        "report",
        [(s.key, s.text, MARKED if s.marked else "") for s in REPORT],
        [("sentence", "", ""), ("as written", "", ""), ("mark", "", "")],
        "The report of the investigation as its author wrote it, sentence by"
        " sentence, with its mark where no record supports a sentence.",
    )
    experiment.table(
        "resolutions",
        [(r.sentence, r.token, r.kind, r.to) for r in written],
        [
            ("sentence", "", ""),
            ("number or citation", "", ""),
            ("resolves to", "", ""),
            ("where", "", ""),
        ],
        "Every number and citation of the report in order, and the field of a"
        " record or the quoted passage it resolves to.",
    )
    experiment.number("tokens", len(written), "d")
    experiment.number("refused", len(problems(written)), "d")
    experiment.number("numbers", sum(r.kind == RECORD for r in written), "d")
    experiment.number("citations", sum(r.kind == PASSAGE for r in written), "d")

    wrong = check(planted(), fields)
    experiment.table(
        "planted",
        [(r.sentence, r.token, r.to) for r in problems(wrong)],
        [
            ("sentence", "", ""),
            ("number or citation", "", ""),
            ("why it is refused", "", ""),
        ],
        "The report with three planted errors: what the check refuses, and why.",
    )
    experiment.figure(
        "fig-report-checks",
        partial(
            draw_report_checks,
            (("as written", written), ("with three planted errors", wrong)),
        ),
    )

    alone = {**fields, "review": review_record(rr6.prose_only())}
    review = next(s for s in REPORT if s.key == "review")
    experiment.table(
        "review-sentence",
        [
            (which, r.token, r.kind, r.to)
            for which, against in (
                ("the log of the review lesson", fields),
                ("a log revised in prose alone", alone),
            )
            for r in check((review,), against)
        ],
        [
            ("the review record from", "", ""),
            ("number", "", ""),
            ("resolves to", "", ""),
            ("where, or why not", "", ""),
        ],
        "The report's sentence on the review findings, checked against the"
        " statuses of the review lesson's log and of a log in which the claim"
        " was revised in prose alone.",
    )

    edited = {EDITED: EDITED.read_bytes() + b"\n# edited\n"}
    again = reproduce(entries, kept)
    changed = reproduce(entries, kept, edited)
    experiment.table(
        "bundle",
        [
            (name, len(entry.fields), len(kept[name].code), again[name], changed[name])
            for name, entry in entries.items()
        ],
        [
            ("record", "", ""),
            ("fields", "", "d"),
            ("code files", "", "d"),
            ("computed again", "", ""),
            ("after the projectile module is edited", "", ""),
        ],
        "Every record of the bundle: how many fields and code files it has,"
        " and its status when computed again, as committed and with one code"
        " file edited.",
    )
    experiment.number("reproduced", sum(s == "reproduced" for s in again.values()), "d")
    experiment.number("records", len(entries), "d")

    kept_memory = memory(kept)
    result_code = code_identity(kept["below-the-top"])
    result_edited = code_identity(kept["below-the-top"], edited)
    found = rr1.assessments()
    archive = rr1.archive(found, select(found, rr1.JUDGEMENTS))
    middle = next(e for e in archive.entries if e.idea.key == "middle-throw")
    cases = (
        (
            "the slow-throw result, for the slow throw",
            "slow-throw-result",
            {"code": result_code, "configuration": digest_value(rr1.SLOW_THROW)},
        ),
        (
            "the slow-throw result, for the throw at 15 m/s",
            "slow-throw-result",
            {"code": result_code, "configuration": digest_value(rr1.MEDIUM_THROW)},
        ),
        (
            "the slow-throw result, after the projectile module is edited",
            "slow-throw-result",
            {"code": result_edited, "configuration": digest_value(rr1.SLOW_THROW)},
        ),
        (
            "the deferred idea, against the archive as it is now",
            "middle-throw",
            {"archive entry": middle.digest},
        ),
        (
            "the runs of the original plan, run again",
            "slow-throw-runs",
            {"record": record_digest(run_plan(ORIGINAL).record)},
        ),
    )
    experiment.table(
        "memory",
        [(i.key, i.kind, i.text) for i in kept_memory.items.values()],
        [("item", "", ""), ("kind", "", ""), ("what is kept", "", "")],
        "The research memory of the investigation: every item with its kind.",
    )
    experiment.table(
        "reuses",
        [
            (what, key, *reuse(kept_memory, key, presented))
            for what, key, presented in cases
        ],
        [
            ("reuse", "", ""),
            ("item", "", ""),
            ("outcome", "", ""),
            ("what comes with it, or why not", "", ""),
        ],
        "Five reuses of the memory: the item asked for, the outcome of the"
        " check of its identities, and what is handed over with it or why it"
        " is refused.",
    )
    experiment.number("items", len(kept_memory.items), "d")
    experiment.number("bare-result", bare_result(kept_memory))
    experiment.number(
        "rounded", ", ".join(f"{r.token}: {r.kind}" for r in check((ROUNDED,), fields))
    )
    return experiment


if __name__ == "__main__":
    main(run)
