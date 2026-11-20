"""The experiment of the lesson "Robustness and statistical uncertainty".

Ten recorded trials of one task, the spring of D2 in the partial condition,
under three variants (``pbc.evidence.robustness``): the readings as
published at other noise seeds, readings with five times the noise, and an
instrument whose every third accepted measurement fails. Every trial is
replayed and scored by the evaluator and held in a ledger of
``pbc.evidence``; the rates carry exact intervals; two baselines without a
model run over twenty noise seeds of each variant. The costs are those each
recording session reported, quoted from the trials' records. Run it as a
program to write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.robustness_and_statistical_uncertainty out

The live command of one trial is on the page; nothing is recorded or
measured live by the build.
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.agents.display import RunDisplay
from pbc.authoring import FIGURE_COLOURS
from pbc.authoring.repository import REPOSITORY_ROOT
from pbc.discovery import force_lab
from pbc.evidence import Ledger, robustness, summary
from pbc.evidence.robustness import (
    BASE,
    BASELINE_SEEDS,
    TRIALS,
    VARIANTS,
    baseline,
    baseline_recovers,
    calls_for,
    success_interval,
)
from pbc.experiment import Experiment, main
from pbc.figure_language import figsize, figure_style, finish

# The live run of one trial, with a model and its key and the extra openai.
LIVE = "pbc.evidence.robustness repeated 1"

AE5 = (
    REPOSITORY_ROOT
    / "site/lessons/agents-llm/23-robustness-and-statistical-uncertainty"
)
D2 = REPOSITORY_ROOT / "site/lessons/agents-llm/06-prior-knowledge-in-discovery"
METHODS = {"grid": "grid + least squares", "random": "random + least squares"}


def trials() -> Ledger:
    return robustness.ledger(AE5)


def _evaluation(ledger: Ledger, name: str):
    return next(e for e in ledger.evaluations if e.attempt == name)


def _claim(name: str) -> float:
    _, _, score = robustness.replay_trial(name, AE5)
    return score.claim["omega"]


def trial_table(experiment: Experiment, ledger: Ledger) -> None:
    rows = []
    for name, trial in TRIALS.items():
        e = _evaluation(ledger, name)
        cost = trial.info.cost
        rows.append(
            (
                trial.variant,
                trial.seed,
                f"{_claim(name):g}",
                f"{e.metrics['held_out_error']:.3f}",
                "yes" if e.correct else "no",
                e.resources["probes"],
                e.resources["failed"],
                e.resources["refused"],
                cost.model_calls,
                cost.tool_calls,
            )
        )
    experiment.table(
        "ae5-trials",
        rows,
        [
            ("variant", "", ""),
            ("seed", "", "d"),
            ("claimed omega", "rad/s", ""),
            ("held-out error", "", ""),
            ("recovered", "", ""),
            ("probes", "", "d"),
            ("failed by the instrument", "", "d"),
            ("refused by the harness", "", "d"),
            ("model messages, recorded", "", "d"),
            ("tool calls, recorded", "", "d"),
        ],
        "Every recorded trial, replayed and scored by the evaluator. The last"
        " two columns are the cost each recording session reported; tokens"
        " and price were not reported.",
    )
    calls = [t.info.cost.tool_calls for t in TRIALS.values()]
    messages = [t.info.cost.model_calls for t in TRIALS.values()]
    experiment.number("calls-low", min(calls))
    experiment.number("calls-high", max(calls))
    experiment.number("messages-low", min(messages))
    experiment.number("messages-high", max(messages))


def rates(ledger: Ledger) -> dict[str, dict[str, tuple[int, int]]]:
    """Recoveries and trials of every contestant in every variant."""
    found: dict[str, dict[str, tuple[int, int]]] = {}
    for variant in VARIANTS:
        # region: one-rate
        mine = [e for e in ledger.evaluations if TRIALS[e.attempt].variant == variant]
        attempts = [a for a in ledger.attempts if a.candidate == variant]
        found.setdefault(variant, {})["agent"] = (
            sum(e.correct is True for e in mine),
            len(attempts),
        )
        # endregion: one-rate
        for method in METHODS:
            results = [baseline(variant, method, s) for s in BASELINE_SEEDS]
            found[variant][method] = (
                sum(baseline_recovers(r) for r in results),
                len(results),
            )
    return found


def rate_table(experiment: Experiment, found) -> None:
    rows = []
    for variant, by in found.items():
        for who, (k, n) in by.items():
            low, high = success_interval(k, n)
            name = "agent, recorded trials" if who == "agent" else METHODS[who]
            rows.append((variant, name, f"{k} of {n}", f"{low:.2f} to {high:.2f}"))
    experiment.table(
        "ae5-rates",
        rows,
        [
            ("variant", "", ""),
            ("contestant", "", ""),
            ("recovered", "", ""),
            ("95 % interval of the rate", "", ""),
        ],
        "The share of runs that recovered the law, with its exact"
        " (Clopper-Pearson) interval. The agent's trials are recorded; each"
        " baseline runs over twenty noise seeds. On the failing instrument the"
        " baselines are not run through it: a baseline that retries every"
        " failed call reads what it reads on the published spring, so its"
        " rows equal the published ones by construction.",
    )
    k, n = found["repeated"]["agent"]
    low, _ = success_interval(k, n)
    experiment.number("repeated-trials", n)
    experiment.number("repeated-low", low, ".2f")
    _low1, high1 = success_interval(0, 1)
    experiment.number("one-failure-high", high1, ".3f")
    experiment.number("level", 0.95, "g")
    experiment.number("low-4", success_interval(4, 4)[0], ".2f")
    experiment.number("low-20", success_interval(20, 20)[0], ".2f")
    bound = np.log(0.025) / np.log(0.9)
    experiment.number("n-bound", bound, ".1f")
    experiment.number("n-needed", int(np.floor(bound)) + 1)
    for variant in ("noisier", "failing"):
        k, n = found[variant]["agent"]
        experiment.number(f"{variant}-recovered", k)
        experiment.number(f"{variant}-trials", n)
    experiment.number("noisier-grid", found["noisier"]["grid"][0])
    experiment.number("noisier-random", found["noisier"]["random"][0])
    experiment.number("baseline-seeds", len(BASELINE_SEEDS))
    experiment.number("calls-for-budget", calls_for(BASE.budget))


def claim_table(experiment: Experiment, ledger: Ledger) -> None:
    """The distinct claims of the trials and the error each has: what the
    outcome of a trial turns on."""
    world = BASE.make(force_lab.SEED)
    claims: dict[float, list[str]] = {}
    for name in TRIALS:
        claims.setdefault(_claim(name), []).append(name)
    rows = [
        (
            f"{value:g}",
            len(names),
            f"{world.held_out_error({'omega': value}):.3f}",
            "yes" if world.held_out_error({"omega": value}) <= BASE.tolerance else "no",
        )
        for value, names in sorted(claims.items())
    ]
    experiment.table(
        "ae5-claims",
        rows,
        [
            ("claimed omega", "rad/s", ""),
            ("trials", "", "d"),
            ("held-out error", "", ""),
            ("within the tolerance", "", ""),
        ],
        "Every distinct claim of the ten trials and its held-out error on the"
        " published world; a claim's error does not depend on the variant.",
    )
    values = sorted(claims)
    experiment.number("claim-low", values[0], "g")
    experiment.number("claim-high", values[-1], "g")
    experiment.number("claims-distinct", len(values))
    failing = [v for v in values if world.held_out_error({"omega": v}) > BASE.tolerance]
    experiment.number("claims-failing", ", ".join(f"{v:g}" for v in failing))
    _, _, d2 = force_lab.replay_run("prior-partial", D2)
    experiment.number("d2-claim", d2.claim["omega"], "g")
    experiment.number("d2-error", d2.held_out_error, ".2f")
    experiment.number("tolerance", BASE.tolerance, "g")


def draw_trial_spread(ledger: Ledger) -> Figure:
    """The held-out error of every trial by variant, beside the errors of
    the two baselines over twenty noise seeds of that variant."""
    variants = list(VARIANTS)
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line", legend=4))
        for i, variant in enumerate(variants):
            for j, (method, marker) in enumerate((("grid", "_"), ("random", "x"))):
                errors = [
                    baseline(variant, method, s).held_out_error for s in BASELINE_SEEDS
                ]
                ax.scatter(
                    np.full(len(errors), i + (j - 0.5) * 0.3),
                    errors,
                    marker=marker,
                    s=30,
                    color=FIGURE_COLOURS[2],
                    linewidths=1.0,
                    label=f"{METHODS[method]}, {len(errors)} seeds" if i == 0 else None,
                    zorder=2,
                )
            mine = [
                e.metrics["held_out_error"]
                for e in ledger.evaluations
                if TRIALS[e.attempt].variant == variant
            ]
            spread = np.linspace(-0.05, 0.05, len(mine))
            ax.scatter(
                i + spread,
                mine,
                marker="o",
                s=46,
                facecolors="none",
                edgecolors=FIGURE_COLOURS[0],
                linewidths=1.4,
                label="agent, recorded trials" if i == 0 else None,
                zorder=3,
            )
        ax.axhline(
            BASE.tolerance,
            color=FIGURE_COLOURS[1],
            linestyle="--",
            linewidth=1.0,
            label="tolerance",
        )
        ax.set_yscale("log")
        ax.set_xticks(
            range(len(variants)),
            ["published\nreadings", "five times\nthe noise", "failing\ninstrument"],
        )
        ax.set_xlim(-0.6, len(variants) - 0.4)
        ax.set_ylabel("held-out error (relative)")
        fig.legend(loc="outside lower center", ncols=1)
    return finish(fig)


def draw_success_intervals(found) -> Figure:
    """The share of recovering runs per variant and contestant, with its
    exact 95 % interval."""
    variants = list(found)
    styles = (("agent", "o", 0), ("grid", "s", 2), ("random", "^", 4))
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line", legend=3))
        for j, (who, marker, colour) in enumerate(styles):
            for i, variant in enumerate(variants):
                k, n = found[variant][who]
                low, high = success_interval(k, n)
                x = i + (j - 1) * 0.22
                ax.errorbar(
                    x,
                    k / n,
                    yerr=[[k / n - low], [high - k / n]],
                    fmt=marker,
                    color=FIGURE_COLOURS[colour],
                    markerfacecolor="none"
                    if who == "agent"
                    else FIGURE_COLOURS[colour],
                    capsize=3,
                    label=(
                        ("agent, recorded trials" if who == "agent" else METHODS[who])
                        if i == 0
                        else None
                    ),
                )
        ax.set_xticks(
            range(len(variants)),
            ["published\nreadings", "five times\nthe noise", "failing\ninstrument"],
        )
        ax.set_ylim(-0.05, 1.05)
        ax.set_xlim(-0.6, len(variants) - 0.4)
        ax.set_ylabel("share recovered (95 % interval)")
        fig.legend(loc="outside lower center", ncols=1)
    return finish(fig)


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    ledger = trials()
    s = summary(ledger, AE5)
    experiment.number("trials", s.total)
    experiment.number("recovered", s.correct)
    experiment.number("budget", BASE.budget)
    trial_table(experiment, ledger)
    # region: replay
    recording, transcript, _ = robustness.replay_trial("failing-1", AE5)
    experiment.display("failing-run", RunDisplay(recording, transcript))
    # endregion: replay
    found = rates(ledger)
    rate_table(experiment, found)
    claim_table(experiment, ledger)
    experiment.figure("fig-trial-spread", partial(draw_trial_spread, ledger))
    experiment.figure("fig-success-intervals", partial(draw_success_intervals, found))
    return experiment


if __name__ == "__main__":
    main(run)
