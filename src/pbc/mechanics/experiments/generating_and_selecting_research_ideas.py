"""The experiment of the lesson "Generating and selecting research ideas".

Seven candidate questions about the tennis ball of the projectile lesson,
each written where possible as a specification in the seven parts of the
lesson "From research question to experiment specification" and with its
proposer's own ratings. ``pbc.research.ideas`` assesses each against that
lesson's laboratory and an archive of answered questions, without running
any of them; a declared rule selects one; every idea and decision goes into
an append-only archive chained by digest. Run it as a program to write the
figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.generating_and_selecting_research_ideas out
"""

import copy
import dataclasses
from functools import partial

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from pbc.agents.specification import execute, parse
from pbc.authoring import FIGURE_COLOURS, diagrams
from pbc.experiment import Experiment, main
from pbc.figure_language import MUTED, figsize, figure_style, finish
from pbc.mechanics.experiments.experiment_specification import (
    AT_FORTY,
    SPECIFICATION,
    laboratory,
)
from pbc.research.ideas import (
    DEFERRED,
    EXTENSION,
    RATINGS,
    REJECTED,
    SELECTED,
    Answered,
    Archive,
    Assessment,
    Idea,
    Judgement,
    assess,
    runs_needed,
    select,
    verify_archive,
)

AUTHOR = "the author of this page"
COLLEAGUE = "a colleague"


def _draft(speed: float, relation: str, bound: float) -> dict:
    """SA1's specification of the throw at another speed and prediction."""
    draft = copy.deepcopy(SPECIFICATION)
    draft["question"] = (
        f"At what launch angle does the tennis ball thrown at {speed:g} m/s,"
        " with air drag, land furthest away?"
    )
    draft["variables"]["speed"]["value"] = speed
    draft["hypothesis"]["prediction"].update(relation=relation, value=bound)
    return draft


# region: slow-throw
SLOW_THROW = _draft(10.0, "above", 43.0)
SLOW_THROW["hypothesis"]["statement"] = (
    "At 10 m/s the drag at launch is under a fifth of the weight, so the ball"
    " hardly notices the air and its best angle lies within two degrees"
    " of the 45 degrees of a throw without drag."
)
# endregion: slow-throw

MEDIUM_THROW = _draft(15.0, "above", 43.0)
MEDIUM_THROW["hypothesis"]["statement"] = (
    "At 15 m/s the drag at launch is under half the weight, so the best"
    " angle stays within two degrees of 45 degrees."
)

BELOW_SIXTY = copy.deepcopy(SPECIFICATION)
BELOW_SIXTY["hypothesis"]["statement"] = (
    "Drag lowers the best angle, so it lies below sixty degrees."
)
BELOW_SIXTY["hypothesis"]["prediction"]["value"] = 60.0

HUNDREDTH = copy.deepcopy(SPECIFICATION)
HUNDREDTH["question"] = (
    "At what launch angle, to a hundredth of a degree, does the tennis ball"
    " thrown at 25 m/s land furthest away?"
)
HUNDREDTH["success"]["resolution"]["value"] = 0.01
HUNDREDTH["stopping"]["max_runs"] = 20

SPIN = copy.deepcopy(SPECIFICATION)
SPIN["question"] = (
    "Does backspin raise the best launch angle of the tennis ball at 25 m/s?"
)
SPIN["actions"] = ["range_with_spin"]

# The candidates, in the order they were proposed; the ratings are each
# proposer's own, from 1 to 5, for feasibility, interest, and novelty.
IDEAS = (
    Idea(
        "replication",
        "Is the best angle at 25 m/s below 44 degrees, as SA1 found?",
        AUTHOR,
        SPECIFICATION,
        {"feasibility": 5, "interest": 2, "novelty": 1},
    ),
    Idea(
        "spin",
        SPIN["question"],
        COLLEAGUE,
        SPIN,
        {"feasibility": 5, "interest": 5, "novelty": 5},
    ),
    Idea(
        "slow-throw",
        "Is the best angle at 10 m/s within two degrees of 45?",
        AUTHOR,
        SLOW_THROW,
        {"feasibility": 4, "interest": 4, "novelty": 3},
    ),
    Idea(
        "below-sixty",
        "Is the best angle at 25 m/s below sixty degrees?",
        COLLEAGUE,
        BELOW_SIXTY,
        {"feasibility": 5, "interest": 3, "novelty": 3},
    ),
    Idea(
        "middle-throw",
        "Is the best angle at 15 m/s within two degrees of 45?",
        COLLEAGUE,
        MEDIUM_THROW,
        {"feasibility": 5, "interest": 3, "novelty": 4},
    ),
    Idea(
        "fast-throw",
        "Is the best angle at 40 m/s lower than at 25 m/s?",
        COLLEAGUE,
        AT_FORTY,
        {"feasibility": 4, "interest": 4, "novelty": 4},
    ),
    Idea(
        "hundredth",
        HUNDREDTH["question"],
        AUTHOR,
        HUNDREDTH,
        {"feasibility": 4, "interest": 3, "novelty": 2},
    ),
)

# region: answered
ANSWERED = (
    Answered("range_with_drag", {"speed": 25.0}, "SA1, its specification"),
    Answered("range_with_drag", {"speed": 40.0}, "SA1, its first exercise"),
    Answered("range_in_vacuum", {}, "M3, the formula without drag", by_formula=True),
)
# endregion: answered

# region: judgements
JUDGEMENTS = {
    "slow-throw": Judgement(
        "high",
        AUTHOR,
        "puts a number on the projectile lesson's argument that a slow ball"
        " hardly notices the air",
    ),
    "middle-throw": Judgement(
        "medium",
        AUTHOR,
        "the same argument at a speed where it is less clear what to expect",
    ),
    "replication": Judgement(
        "medium", AUTHOR, "every extension of SA1 rests on its result"
    ),
    "fast-throw": Judgement("low", AUTHOR, "SA1's exercise has answered it"),
}
# endregion: judgements

# What would warrant revisiting an idea that is not selected: the author's
# conditions, written with the decision.
REVISIT = {
    "replication": "before an extension builds on SA1's result",
    "spin": "when the laboratory has a simulation with spin and lift",
    "below-sixty": "rewritten with a bound inside the range of angles",
    "middle-throw": "after the selected idea, if the trend with speed is next",
    "fast-throw": "when a result at 40 m/s is needed at another resolution",
}

CHECKS = ("feasible", "falsifiable", "within budget", "adds to the archive")


def assessments() -> dict[str, Assessment]:
    """The assessment of every idea, by key; nothing is run."""
    lab = laboratory()
    return {idea.key: assess(idea, lab, ANSWERED) for idea in IDEAS}


def decision(
    key: str, assessment: Assessment, selected: str | None
) -> tuple[str, str, str]:
    """The decision about an idea, its reason, and what would warrant
    revisiting it, from its assessment and the selection."""
    if key == selected:
        return SELECTED, "passes every check; ranked first by the declared rule", ""
    if not assessment.feasible:
        return DEFERRED, assessment.problems[0], REVISIT[key]
    if not assessment.falsifiable:
        return (
            REJECTED,
            "the predicted bound is at the end of the range: no result can"
            " contradict it",
            REVISIT[key],
        )
    if not assessment.within_budget:
        return (
            REJECTED,
            f"the route needs {assessment.runs} runs and the budget is"
            f" {assessment.budget}",
            f"with a budget of at least {assessment.runs} runs",
        )
    return (
        DEFERRED,
        "passes every check; ranked below the selected idea"
        f" ({assessment.contribution})",
        REVISIT[key],
    )


def archive(found: dict[str, Assessment], selected: str | None) -> Archive:
    """The archive of every idea with its decision, in the order proposed."""
    kept = Archive()
    for idea in IDEAS:
        kept.add(idea, *decision(idea.key, found[idea.key], selected))
    return kept


def _mark(value: bool | None) -> str:
    return {True: "yes", False: "no", None: "not reached"}[value]


def assessment_table(
    experiment: Experiment, found: dict[str, Assessment], selected: str | None
) -> None:
    """Record the table of every idea's checks and decision."""
    rows = []
    for idea in IDEAS:
        a = found[idea.key]
        rows.append(
            (
                idea.key,
                idea.proposer,
                _mark(a.feasible),
                _mark(a.falsifiable),
                a.runs,
                a.budget,
                a.contribution or "not reached",
                decision(idea.key, a, selected)[0],
            )
        )
    experiment.table(
        "assessment",
        rows,
        [
            ("idea", "", ""),
            ("proposer", "", ""),
            ("feasible", "", ""),
            ("falsifiable", "", ""),
            ("runs needed", "", "d"),
            ("budget", "", "d"),
            ("contribution", "", ""),
            ("decision", "", ""),
        ],
        "The checks of every idea, computed before any run, and the decision"
        " of the declared rule; an idea the laboratory cannot run reaches no"
        " later check.",
    )


def ratings_table(experiment: Experiment) -> None:
    """Record the proposers' own ratings, which nothing reads."""
    experiment.table(
        "self-ratings",
        [
            (idea.key, idea.proposer, *(idea.self_ratings[r] for r in RATINGS))
            for idea in IDEAS
        ],
        [
            ("idea", "", ""),
            ("proposer", "", ""),
            *((rating, "", "d") for rating in RATINGS),
        ],
        "The ratings each proposer gave their own idea, from 1 to 5: kept,"
        " shown, and read by no check and by no rule.",
    )


def by_self_rating() -> str:
    """The idea a rule would choose that took the mean self-rating."""
    return max(
        IDEAS,
        key=lambda idea: sum(idea.self_ratings.values()) / len(RATINGS),
    ).key


def tampered(kept: Archive) -> list[str]:
    """The archive with one idea's self-ratings edited after it was
    archived and one entry removed, and what ``verify_archive`` finds."""
    entries = list(kept.entries)
    spin = entries[1]
    entries[1] = dataclasses.replace(
        spin,
        idea=dataclasses.replace(
            spin.idea, self_ratings={**spin.idea.self_ratings, "feasibility": 1}
        ),
    )
    del entries[4]
    return verify_archive(entries)


def readded(kept: Archive) -> Archive:
    """The archive of the exercise: a second decision about the 15 m/s idea,
    added as a new entry after a new judgement."""
    again = Archive()
    for entry in kept.entries:
        again.add(entry.idea, entry.decision, entry.reason, entry.revisit)
    medium = next(idea for idea in IDEAS if idea.key == "middle-throw")
    again.add(
        medium,
        SELECTED,
        "selected after the slow throw: the trend with speed is the next question",
        "",
    )
    return again


def half_degree() -> int:
    """The runs the route needs for SA1's specification at a resolution of
    half a degree, counted from its procedure: the third exercise."""
    draft = copy.deepcopy(SPECIFICATION)
    draft["success"]["resolution"]["value"] = 0.5
    return runs_needed(parse(draft, laboratory()))


def draw_idea_checks() -> Figure:
    """An idea through the checks the build computes and the one judgement a
    person records, with the self-rating beside it, as a sketch."""
    fig, ax = diagrams.canvas(6.4, 4.2, (0.0, 12.8), (0.0, 8.4))
    diagrams.state_box(ax, (1.6, 6.9), "idea\nand draft", width=2.4, height=1.1)
    diagrams.state_box(
        ax, (1.6, 4.4), "self-rating", width=2.4, height=0.9, colour=MUTED
    )
    diagrams.line(ax, [(1.6, 6.35), (1.6, 4.85)], colour=MUTED, linestyle=":")
    centres = (4.55, 6.9, 9.25, 11.6)
    for x, name in zip(
        centres, ("feasible?", "falsifiable?", "in budget?", "new?"), strict=True
    ):
        diagrams.state_box(ax, (x, 6.9), name, width=2.0, height=1.1)
    # From the right edge of each box to the left edge of the next.
    starts = (2.8, *(x + 1.0 for x in centres[:-1]))
    for start, centre in zip(starts, centres, strict=True):
        diagrams.arrow(ax, (start, 6.9), (centre - 1.0, 6.9))
    diagrams.text(ax, (8.07, 8.05), "computed before any run", colour=MUTED)
    diagrams.state_box(
        ax, (8.3, 4.4), "interest:\na named judgement", width=3.5, height=1.1, colour=2
    )
    diagrams.state_box(ax, (11.6, 4.4), "rule", width=1.9, height=0.9)
    diagrams.arrow(ax, (11.6, 6.35), (11.6, 4.85))
    diagrams.arrow(ax, (10.05, 4.4), (10.65, 4.4), colour=2, linestyle="--")
    diagrams.state_box(ax, (6.6, 1.4), "archive", width=10.8, height=1.0)
    diagrams.arrow(ax, (11.6, 3.95), (11.6, 1.9))
    diagrams.text(ax, (11.45, 2.9), "decision", ha="right")
    diagrams.arrow(ax, (1.6, 3.95), (1.6, 1.9), colour=MUTED, linestyle=":")
    diagrams.text(ax, (1.75, 2.9), "kept,\nnot read", ha="left", colour=MUTED)
    return fig


def draw_idea_assessment(found: dict[str, Assessment], selected: str | None) -> Figure:
    """Every idea's checks as markers, and its proposer's mean self-rating
    in a column of its own."""
    outcome = {
        True: ("o", FIGURE_COLOURS[0], "passed"),
        False: ("X", FIGURE_COLOURS[1], "failed"),
        None: (".", MUTED, "not reached"),
    }
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("square", legend=1))
        seen = set()
        for row, idea in enumerate(IDEAS):
            a = found[idea.key]
            cells = (
                a.feasible,
                a.falsifiable,
                a.within_budget,
                None if a.contribution is None else a.contribution == EXTENSION,
            )
            for column, value in enumerate(cells):
                marker, colour, name = outcome[value]
                ax.scatter(
                    [column],
                    [row],
                    marker=marker,
                    s=70 if marker != "." else 40,
                    color=colour,
                    label=None if name in seen else name,
                    zorder=3,
                )
                seen.add(name)
            mean = sum(idea.self_ratings.values()) / len(RATINGS)
            ax.text(len(CHECKS) + 0.4, row, f"{mean:.1f}", color=MUTED, va="center")
        ax.set_xticks([*range(len(CHECKS)), len(CHECKS) + 0.6])
        ax.set_xticklabels(
            ["feasible", "falsifiable", "in budget", "new", "self-rating\n(not used)"],
            rotation=45,
            ha="right",
        )
        ax.set_yticks(range(len(IDEAS)))
        ax.set_yticklabels(
            [f"{i.key} *" if i.key == selected else i.key for i in IDEAS]
        )
        ax.set_xlim(-0.5, len(CHECKS) + 1.2)
        ax.set_ylim(len(IDEAS) - 0.5, -0.5)
        ax.tick_params(length=0)
        for side in ("top", "right", "bottom", "left"):
            ax.spines[side].set_visible(False)
        ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.42), ncol=3)
    return finish(fig)


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.figure("fig-idea-checks", draw_idea_checks)
    found = assessments()
    # region: select
    selected = select(found, JUDGEMENTS)
    kept = archive(found, selected)
    # endregion: select
    assessment_table(experiment, found, selected)
    ratings_table(experiment)
    experiment.figure(
        "fig-idea-assessment", partial(draw_idea_assessment, found, selected)
    )
    experiment.number("selected", selected)
    experiment.number("ideas", len(IDEAS), "d")
    experiment.number("removed", sum(not a.passed for a in found.values()), "d")
    experiment.number("by-self-rating", by_self_rating())
    # The prose reads the action the refusal names, not the refusal: its
    # quotation marks would be set as typographic quotes there; the archive
    # table shows the refusal as written.
    experiment.number("spin-action", SPIN["actions"][0])
    experiment.number("hundredth-runs", found["hundredth"].runs, "d")
    experiment.number("hundredth-budget", found["hundredth"].budget, "d")

    # The count of runs is the route's own: execute the selected draft once.
    lab = laboratory()
    record = execute(parse(copy.deepcopy(SLOW_THROW), lab), lab)
    experiment.number("slow-runs-needed", found["slow-throw"].runs, "d")
    experiment.number("slow-runs-made", len(record.runs), "d")

    experiment.table(
        "archive",
        [
            (e.number, e.idea.key, e.decision, e.reason, e.revisit, e.digest[:12])
            for e in kept.entries
        ],
        [
            ("entry", "", "d"),
            ("idea", "", ""),
            ("decision", "", ""),
            ("reason", "", ""),
            ("revisit when", "", ""),
            ("digest", "", ""),
        ],
        "The archive: every idea with its decision, the reason, and what would"
        " warrant revisiting it; the first twelve characters of each entry's"
        " digest.",
    )
    experiment.number("archive-problems", len(verify_archive(kept.entries)), "d")
    experiment.table(
        "tampered",
        [(problem,) for problem in tampered(kept)],
        [("what the check of the archive finds", "", "")],
        "The archive after the colleague's feasibility rating of the spin idea"
        " was lowered and one entry was removed.",
    )
    experiment.number("half-degree-runs", half_degree(), "d")
    again = readded(kept)
    experiment.number("again-entries", len(again.entries), "d")
    experiment.number("again-problems", len(verify_archive(again.entries)), "d")
    return experiment


if __name__ == "__main__":
    main(run)
