"""The experiment of the lesson "Physics reasoning benchmarks".

A benchmark of twelve items per seed, built from the lessons of the site
(``pbc.agents.reasoning_benchmark``): problems in words, visual and tool
affordances of two verified figures, and counterfactual predictions. One
recorded run per seed is replayed and scored against the key the build
computes; the score is reported per seed and over the seeds, with every
failure, and with a failure of the software interface kept apart from a
failure of reasoning. Run it as a program to write the figures and numbers of
the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.physics_reasoning_benchmarks out

The live run, which asks a model and needs its key, is a separate command
behind the optional dependency ``openai``: the module ``LIVE``, run with
``uv run --locked --no-dev --extra openai python -m pbc.agents.reasoning_benchmark``.
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.agents.display import AllowlistDisplay, RunDisplay
from pbc.agents.reasoning_benchmark import (
    COMPUTED_TOLERANCE,
    KINDS,
    MAX_STEPS,
    READING_MARGIN,
    SEEDS,
    chance,
    checks,
    draw_oscillation,
    draw_ranges,
    items,
    key,
    outcome,
    refusals,
    replay_fixtures,
    sheet,
    spread,
)
from pbc.agents.vision import READING_TOLERANCE
from pbc.authoring import FIGURE_COLOURS
from pbc.authoring.repository import REPOSITORY_ROOT
from pbc.experiment import Experiment, main

# The live run of the lesson: a model, its key, and the extra openai.
LIVE = "pbc.agents.reasoning_benchmark"

# The recorded runs, next to the page that shows them.
LESSON = REPOSITORY_ROOT / "site/lessons/agents-llm/21-physics-reasoning-benchmarks"

# The run shown in full on the page.
SHOWN = SEEDS[0]


def _shown(item, value) -> str:
    if value is None:
        return "none"
    if item.options:
        return item.options[int(value) - 1]
    return f"{value:.4g} {item.unit}".strip()


def scored_runs(replays):
    """The outcome of every item of each seed's run, by seed."""
    return {seed: outcome(items(seed), key(seed), replays[seed][1]) for seed in SEEDS}


def fraction(found, kind=None) -> float:
    """The fraction of the items of one run (of ``kind``, or all) answered
    correctly."""
    chosen = [o for o in found if kind is None or o.item.kind == kind]
    return sum(o.verdict == "correct" for o in chosen) / len(chosen)


def expected_by_chance(seed: int, kind=None) -> float:
    """The fraction a uniform guesser is expected to get right on ``seed``."""
    truths = key(seed)
    chosen = [i for i in items(seed) if kind is None or i.kind == kind]
    return sum(chance(i, truths[i.number]) for i in chosen) / len(chosen)


def item_rows(seed: int):
    """The items of ``seed``: kind, lesson, picture, the build's answer, and
    the second route's when there is one."""
    truths, second = key(seed), checks(seed)
    rows = []
    for item in items(seed):
        rows.append(
            (
                item.number,
                item.kind,
                item.source,
                item.picture or "none",
                _shown(item, truths[item.number]),
                _shown(item, second[item.number][1])
                if item.number in second
                else "none",
            )
        )
    return rows


def check_rows():
    """For each seed, the largest relative difference between an answer of
    the lesson code and its second route, and how many items have one."""
    rows = []
    for seed in SEEDS:
        found = checks(seed)
        largest = max(abs(b - a) / abs(a) for a, b in found.values())
        rows.append((seed, len(found), largest))
    return rows


def _of_kind(found, kind) -> str:
    chosen = [o for o in found if o.item.kind == kind]
    return f"{sum(o.verdict == 'correct' for o in chosen)} of {len(chosen)}"


def seed_rows(scored, replays):
    """One row per seed: the correct answers by kind, the wrong ones, the
    items left without an accepted answer, and the refused calls."""
    rows = []
    for seed in SEEDS:
        found = scored[seed]
        rows.append(
            (
                seed,
                *(_of_kind(found, kind) for kind in KINDS),
                sum(o.verdict == "correct" for o in found),
                sum(o.verdict == "wrong" for o in found),
                sum(o.verdict == "unanswered" for o in found),
                len(refusals(replays[seed][1])),
            )
        )
    return rows


def spreads(scored):
    """The score over the seeds, overall and by kind: the model's and the
    expected score of uniform guessing."""
    rows = {}
    for kind in (*KINDS, None):
        model = spread([fraction(scored[seed], kind) for seed in SEEDS])
        guess = float(np.mean([expected_by_chance(seed, kind) for seed in SEEDS]))
        rows[kind or "all"] = (model, guess)
    return rows


def spread_rows(found):
    return [
        (
            name,
            100 * model.mean,
            100 * model.deviation,
            100 * model.low,
            min(100.0, 100 * model.high),
            100 * guess,
        )
        for name, (model, guess) in found.items()
    ]


def failure_rows(scored):
    """Every item a run did not answer correctly: a wrong accepted answer (a
    reasoning failure) or none accepted (an interface failure)."""
    rows = []
    for seed in SEEDS:
        for o in scored[seed]:
            if o.verdict != "correct":
                rows.append(
                    (
                        seed,
                        o.item.number,
                        o.item.kind,
                        _shown(o.item, o.answer),
                        _shown(o.item, o.truth),
                        "reasoning" if o.verdict == "wrong" else "interface",
                    )
                )
    return rows


def draw_benchmark_scores(scored, found) -> Figure:
    """The fraction correct of each seed by kind, the mean over seeds with
    its 95 per cent interval, and the expected score of uniform guessing."""
    names = [*KINDS, "all"]
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    positions = np.arange(len(names))
    for k, name in enumerate(names):
        kind = None if name == "all" else name
        values = [fraction(scored[seed], kind) for seed in SEEDS]
        offsets = np.linspace(-0.18, 0.18, len(SEEDS))
        ax.scatter(
            positions[k] + offsets,
            values,
            marker="o",
            s=22,
            facecolors="none",
            edgecolors=FIGURE_COLOURS[0],
            label="one seed" if k == 0 else None,
            zorder=3,
        )
        model, guess = found[name]
        ax.errorbar(
            positions[k] + 0.32,
            model.mean,
            yerr=[
                [model.mean - max(0.0, model.low)],
                [min(1.0, model.high) - model.mean],
            ],
            fmt="s",
            color=FIGURE_COLOURS[1],
            capsize=4,
            label="mean, 95 % interval over seeds" if k == 0 else None,
            zorder=4,
        )
        ax.scatter(
            positions[k] + 0.32,
            guess,
            marker="x",
            s=40,
            color=FIGURE_COLOURS[2],
            label="uniform guessing (expected)" if k == 0 else None,
            zorder=4,
        )
    ax.set_xticks(
        positions,
        [
            "problem",
            "visual\naffordance",
            "tool\naffordance",
            "counter-\nfactual",
            "all",
        ],
    )
    ax.set_ylim(-0.05, 1.08)
    ax.set_ylabel("fraction of items correct")
    ax.set_xlabel("kind of item")
    ax.legend(
        fontsize=8, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, frameon=False
    )
    return fig


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.figure("fig-picture-a", draw_oscillation)
    experiment.figure("fig-picture-b", draw_ranges)

    # region: replay
    replays = replay_fixtures(LESSON)
    scored = scored_runs(replays)
    found = spreads(scored)
    # endregion: replay
    experiment.display("allowlist", AllowlistDisplay(sheet(SHOWN)))
    experiment.display("run-shown", RunDisplay(*replays[SHOWN]))
    experiment.number("recorded", replays[SHOWN][0].recorded)
    experiment.number("shown", SHOWN, "d")
    experiment.number("seeds", len(SEEDS), "d")
    experiment.number("items", len(items(SHOWN)), "d")
    experiment.number("max-steps", MAX_STEPS, "d")
    experiment.number("computed-tolerance", 100 * COMPUTED_TOLERANCE, ".0f")
    experiment.number("reading-tolerance", 100 * READING_TOLERANCE, ".0f")
    experiment.number("reading-margin", 100 * READING_MARGIN, ".0f")
    experiment.number("largest-check", max(r[2] for r in check_rows()), ".0e")
    model, guess = found["all"]
    experiment.number("mean", 100 * model.mean, ".0f")
    experiment.number("deviation", 100 * model.deviation, ".0f")
    experiment.number("low", 100 * model.low, ".0f")
    experiment.number("high", min(100.0, 100 * model.high), ".0f")
    experiment.number("chance", 100 * guess, ".0f")
    experiment.number(
        "wrong", sum(o.verdict == "wrong" for s in SEEDS for o in scored[s]), "d"
    )
    experiment.number(
        "unanswered",
        sum(o.verdict == "unanswered" for s in SEEDS for o in scored[s]),
        "d",
    )
    experiment.number("refused", sum(len(refusals(replays[s][1])) for s in SEEDS), "d")

    experiment.table(
        "ev1-items",
        item_rows(SHOWN),
        [
            ("item", "", "d"),
            ("kind", "", ""),
            ("from the lesson", "", ""),
            ("picture", "", ""),
            ("answer of the lesson's code", "", ""),
            ("second route", "", ""),
        ],
        "The items of the run shown, with the answer the build computes by the"
        " code of the lesson each comes from and, where one exists, the answer of"
        " a second, independent route.",
    )
    experiment.table(
        "ev1-checks",
        check_rows(),
        [
            ("seed", "", "d"),
            ("items with a second route", "", "d"),
            ("largest relative difference", "", ".1e"),
        ],
        "For each seed, how far the second route lies from the lesson's code at"
        " most, relative to the answer.",
    )
    experiment.table(
        "ev1-seeds",
        seed_rows(scored, replays),
        [
            ("seed", "", "d"),
            *((kind, "correct", "") for kind in KINDS),
            ("all", "correct", "d"),
            ("wrong", "reasoning", "d"),
            ("no accepted answer", "interface", "d"),
            ("refused calls", "interface", "d"),
        ],
        "Each seed's run scored by the build: the correct answers by kind, the"
        " accepted answers that are wrong, the items left without an accepted"
        " answer, and the calls the interface refused.",
    )
    experiment.table(
        "ev1-spread",
        spread_rows(found),
        [
            ("kind", "", ""),
            ("mean", "%", ".0f"),
            ("standard deviation", "%", ".0f"),
            ("95 % interval, low", "%", ".0f"),
            ("95 % interval, high", "%", ".0f"),
            ("uniform guessing", "%", ".0f"),
        ],
        "The fraction of items correct over the seeds: its mean, its standard"
        " deviation from seed to seed, the Student-t interval of the mean (cut"
        " at 100 per cent), and the expected score of a uniform guess in the"
        " stated options and ranges.",
    )
    experiment.table(
        "ev1-failures",
        failure_rows(scored),
        [
            ("seed", "", "d"),
            ("item", "", "d"),
            ("kind", "", ""),
            ("answer", "", ""),
            ("recomputed truth", "", ""),
            ("failure of", "", ""),
        ],
        "Every item of every run that is not correct, with the accepted answer,"
        " the truth the build computed, and whether the failure is one of"
        " reasoning (a wrong accepted answer) or of the interface (none"
        " accepted).",
    )
    experiment.figure(
        "fig-benchmark-scores", partial(draw_benchmark_scores, scored, found)
    )
    return experiment


if __name__ == "__main__":
    main(run)
