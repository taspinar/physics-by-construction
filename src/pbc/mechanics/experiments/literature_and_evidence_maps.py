"""The experiment of the lesson "Literature, novelty assessment, and evidence
maps".

Three claims about the tennis ball (the replication and the original
question of the research plans, and the scaling guess of the projectile
lesson) compared with a
small local corpus of passages quoted from the site's own lessons, each
checked against its page
(``pbc.research.corpus``): the label of every pair from the annotator's
reading of each passage, checked against the labels the annotator gave
directly; a lexical retrieval baseline, its ranks and its recall; the log of
what was proposed and not read; and what the search can say about the
selected question. Nothing is read from the web or from another page. Run it
as a program to write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.literature_and_evidence_maps out
"""

from functools import partial

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS, diagrams
from pbc.experiment import Experiment, main
from pbc.figure_language import MARKER, MUTED, figsize, figure_style, finish
from pbc.research.corpus import (
    ANNOTATED_BY,
    ANNOTATIONS,
    CONTRADICTS,
    INSUFFICIENT,
    PASSAGES,
    REGISTER,
    STATEMENTS,
    SUPPORTS,
    Statement,
)
from pbc.research.literature import (
    label,
    novelty,
    recall,
    retrieve,
    review_log,
)

# The number of passages the search returns for a claim.
K = 3

STYLE = {
    SUPPORTS: ("o", FIGURE_COLOURS[0], FIGURE_COLOURS[0]),
    CONTRADICTS: ("X", FIGURE_COLOURS[1], FIGURE_COLOURS[1]),
    INSUFFICIENT: ("o", MUTED, "none"),
}


def statement(key: str) -> Statement:
    return next(s for s in STATEMENTS if s.key == key)


def labels_of(claim: Statement) -> list[tuple[str, str, str, str]]:
    """Every passage's computed label for ``claim``, its reason, and the
    label the annotator gave the pair directly."""
    return [
        (p.key, *label(claim, p.reading), ANNOTATIONS[claim.key][p.key])
        for p in PASSAGES
    ]


def agreement() -> tuple[int, int]:
    """The pairs whose computed label is the annotated one, of all pairs."""
    pairs = [row for claim in STATEMENTS for row in labels_of(claim)]
    return sum(row[1] == row[3] for row in pairs), len(pairs)


def evidence_map() -> list[tuple[str, str, str, str, str, str]]:
    """Each claim with each passage that decides it: the label, the lesson,
    the conditions the passage holds under, and the register source behind
    its drag assumption, where the register holds one."""
    sources = {source.assumption: source.key for source in REGISTER}
    rows = []
    for claim in STATEMENTS:
        decided = [p for p in PASSAGES if label(claim, p.reading)[0] != INSUFFICIENT]
        for p in decided:
            r = p.reading
            if r.speed is None:
                speed = "not stated"
            elif isinstance(r.speed, str):
                speed = r.speed
            else:
                speed = f"{r.speed:g} m/s"
            rows.append(
                (
                    claim.key,
                    p.key,
                    label(claim, r)[0],
                    p.lesson,
                    f"drag {r.drag}; ball {r.ball}; speed {speed}",
                    sources.get(f"{r.drag} drag", ""),
                )
            )
        if not decided:
            rows.append((claim.key, "none", "", "", novelty(claim, PASSAGES), ""))
    return rows


# region: without-drag
WITHOUT_DRAG = Statement(
    key="without-drag",
    text=(
        "Without drag the best launch angle of the tennis ball thrown at"
        " 25 m/s lies above 44 degrees."
    ),
    quantity="best angle",
    drag="none",
    ball="tennis",
    speed=25.0,
    relation="above",
    value=44.0,
)
# endregion: without-drag

# region: rewritten
# The scaling guess rewritten in the words the passages use.
REWRITTEN = (
    "With quadratic drag the longest throw is not flatter than $45^\\circ$;"
    " drag does not move the best angle of the ball lower."
)
# endregion: rewritten


def exercise_labels() -> list[tuple[str, str, str]]:
    """The passages that decide the claim of the first exercise, with
    their labels and reasons."""
    return [
        (p.key, *label(WITHOUT_DRAG, p.reading))
        for p in PASSAGES
        if label(WITHOUT_DRAG, p.reading)[0] != INSUFFICIENT
    ]


def draw_evidence_chain() -> Figure:
    """A claim, the passages a search proposes with their labels, the
    assumption a passage holds under, and the register source behind the
    assumption, as a sketch."""
    fig, ax = diagrams.canvas(6.4, 4.4, (0.0, 12.8), (0.0, 8.8))
    diagrams.state_box(ax, (1.6, 4.4), "claim", width=2.2, height=1.0)
    diagrams.state_box(ax, (6.0, 7.2), "passage", width=2.4, height=0.9)
    diagrams.state_box(ax, (6.0, 4.4), "passage", width=2.4, height=0.9)
    diagrams.state_box(
        ax, (6.0, 1.6), "proposal,\nnot read", width=2.4, height=1.0, colour=MUTED
    )
    diagrams.arrow(ax, (2.7, 4.7), (4.8, 7.0))
    diagrams.text(ax, (3.2, 6.2), "supports", ha="right")
    diagrams.arrow(ax, (2.7, 4.4), (4.8, 4.4), colour=MUTED, linestyle="--")
    diagrams.text(ax, (3.75, 4.0), "insufficient", colour=MUTED)
    diagrams.arrow(ax, (2.7, 4.1), (4.8, 1.8), colour=MUTED, linestyle=":")
    diagrams.text(ax, (3.2, 2.6), "no label\nyet", ha="right", colour=MUTED)
    diagrams.state_box(
        ax, (10.9, 7.2), "assumption:\nquadratic drag", width=3.0, height=1.1, colour=2
    )
    diagrams.arrow(ax, (7.2, 7.2), (9.4, 7.2))
    diagrams.text(ax, (8.3, 7.6), "holds under")
    diagrams.text(ax, (7.35, 4.4), "holds under\nno drag", ha="left", colour=MUTED)
    diagrams.state_box(
        ax,
        (10.9, 2.6),
        "register source,\nreviewed for it",
        width=3.0,
        height=1.1,
        colour=2,
    )
    diagrams.arrow(ax, (10.9, 3.15), (10.9, 6.65), colour=2, linestyle="--")
    return fig


def draw_retrieval_ranks() -> Figure:
    """For each claim, the retrieval score of every passage in rank order,
    each marked by its label, and the cut-off of the search."""
    with figure_style():
        fig, axes = plt.subplots(
            len(STATEMENTS), 1, figsize=figsize("measured", legend=1), sharex=True
        )
        for ax, claim in zip(axes, STATEMENTS, strict=True):
            ranked = retrieve(claim.text, PASSAGES)
            for rank, (key, score) in enumerate(ranked, start=1):
                given = ANNOTATIONS[claim.key][key]
                marker, colour, face = STYLE[given]
                ax.plot(
                    [rank],
                    [score],
                    marker=marker,
                    markersize=MARKER + 2,
                    color=colour,
                    markerfacecolor=face,
                    linestyle="none",
                )
            ax.axvline(K + 0.5, color=MUTED, linestyle="--", linewidth=1.0)
            ax.set_ylabel("score")
            ax.set_ylim(0.0, 0.7)
            ax.set_title(claim.key, loc="left")
        axes[-1].set_xlabel("rank of the passage")
        axes[-1].set_xticks(range(1, len(PASSAGES) + 1, 2))
        handles = [
            plt.Line2D(
                [],
                [],
                marker=marker,
                color=colour,
                markerfacecolor=face,
                markersize=MARKER + 2,
                linestyle="none",
                label=name,
            )
            for name, (marker, colour, face) in STYLE.items()
        ]
        axes[-1].legend(
            handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.45), ncol=3
        )
    return finish(fig)


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.figure("fig-evidence-chain", draw_evidence_chain)
    experiment.number("passages", len(PASSAGES), "d")
    experiment.number("lessons", len({p.lesson for p in PASSAGES}), "d")
    experiment.number("annotated-by", ANNOTATED_BY)
    experiment.table(
        "corpus",
        [
            (p.key, p.lesson, f"claim {p.claim}" if p.claim else "prose", p.licence)
            for p in PASSAGES
        ],
        [
            ("passage", "", ""),
            ("lesson", "", ""),
            ("where", "", ""),
            ("licence", "", ""),
        ],
        "The corpus: every passage, the lesson it is quoted from, whether it"
        " is a typed claim of that page or a sentence of its prose, and its"
        " licence.",
    )
    replication = statement("replication")
    experiment.table(
        "labels-replication",
        [
            (key, computed, reason, given)
            for key, computed, reason, given in labels_of(replication)
        ],
        [
            ("passage", "", ""),
            ("label", "", ""),
            ("reason", "", ""),
            ("annotated", "", ""),
        ],
        "Every passage against the replication's claim: the label computed"
        " from the annotator's reading, its reason, and the label the"
        " annotator gave the pair directly.",
    )
    agreed, pairs = agreement()
    experiment.number("agreed", agreed, "d")
    experiment.number("pairs", pairs, "d")
    without_air = next(p for p in PASSAGES if p.key == "sa5-without-air")
    experiment.number("without-air-label", label(replication, without_air.reading)[0])
    experiment.number("without-air-reason", label(replication, without_air.reading)[1])

    no_change = statement("no-change")
    experiment.table(
        "labels-no-change",
        [
            (key, computed, reason)
            for key, computed, reason, _ in labels_of(no_change)
            if computed != INSUFFICIENT or key in ("sa5-without-air", "m3-formula")
        ],
        [("passage", "", ""), ("label", "", ""), ("reason", "", "")],
        "The passages that decide the guess that drag leaves the best"
        " angle at forty-five degrees, and the two that state forty-five"
        " degrees without air.",
    )

    rows = []
    for claim in STATEMENTS:
        ranked = retrieve(claim.text, PASSAGES)
        found = recall(claim, ranked, K)
        if found is None:
            experiment.number(f"recall-{claim.key}", "nothing to find")
        else:
            experiment.number(f"recall-{claim.key}", found, ".2f")
        experiment.number(f"top-{claim.key}", ranked[0][0])
        for rank, (key, score) in enumerate(ranked[:K], start=1):
            rows.append((claim.key, rank, key, score, ANNOTATIONS[claim.key][key]))
    experiment.number("k", K, "d")
    experiment.table(
        "retrieved",
        rows,
        [
            ("claim", "", ""),
            ("rank", "", "d"),
            ("passage", "", ""),
            ("score", "", ".3f"),
            ("annotated label", "", ""),
        ],
        f"The first {K} passages the retrieval returns for each claim, with"
        " their TF-IDF cosine score to three decimals and the annotated label.",
    )
    experiment.figure("fig-retrieval-ranks", partial(draw_retrieval_ranks))

    experiment.table(
        "review-log",
        [
            (e.claim, e.source, e.proposed_by, e.quotation, e.label_status, e.label)
            for e in review_log(STATEMENTS, PASSAGES, K)
        ],
        [
            ("claim", "", ""),
            ("source", "", ""),
            ("proposed by", "", ""),
            ("quotation", "", ""),
            ("label status", "", ""),
            ("label", "", ""),
        ],
        "The review log: every source proposed for a claim, by whom, whether"
        " its quotation is checked against its page, where its label comes"
        " from, and the label of the annotations where the annotator has read"
        " it.",
    )
    experiment.table(
        "evidence-map",
        evidence_map(),
        [
            ("claim", "", ""),
            ("passage", "", ""),
            ("label", "", ""),
            ("lesson", "", ""),
            ("holds under", "", ""),
            ("source of the drag assumption", "", ""),
        ],
        "The evidence map of the three claims: each passage that decides a"
        " claim, with its label, its lesson, the conditions it holds under,"
        " and the register source behind its drag assumption; a claim no"
        " passage decides says what the search found.",
    )
    experiment.table(
        "without-drag",
        exercise_labels(),
        [("passage", "", ""), ("label", "", ""), ("reason", "", "")],
        "The passages that decide the claim of the exercise about the throw"
        " without drag, with the label computed from each reading.",
    )
    no_change = statement("no-change")
    rewritten = retrieve(REWRITTEN, PASSAGES)
    experiment.number("rewritten-recall", recall(no_change, rewritten, K), ".2f")
    experiment.number(
        "rewritten-found",
        sum(
            ANNOTATIONS[no_change.key][key] != INSUFFICIENT for key, _ in rewritten[:K]
        ),
        "d",
    )
    experiment.number(
        "no-change-lessons",
        len(
            {
                p.lesson
                for p in PASSAGES
                if ANNOTATIONS[no_change.key][p.key] != INSUFFICIENT
            }
        ),
        "d",
    )
    experiment.number(
        "found-no-change",
        sum(
            ANNOTATIONS[no_change.key][key] != INSUFFICIENT
            for key, _ in retrieve(no_change.text, PASSAGES)[:K]
        ),
        "d",
    )
    experiment.number(
        "supports-replication",
        sum(given == SUPPORTS for given in ANNOTATIONS["replication"].values()),
        "d",
    )
    experiment.number(
        "decisive-no-change",
        sum(given != INSUFFICIENT for given in ANNOTATIONS[no_change.key].values()),
        "d",
    )
    source = REGISTER[0]
    experiment.number("register-key", source.key)
    experiment.number("register-assumption", source.assumption)
    experiment.number("slow-novelty", novelty(statement("slow-throw"), PASSAGES))
    return experiment


if __name__ == "__main__":
    main(run)
