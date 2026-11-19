"""The experiment of the lesson "Full, partial, and no prior knowledge under one
protocol".

The same model probes the same hidden spring under the three conditions of
prior knowledge (``pbc.discovery.force_lab``, runs ``prior-full``,
``prior-partial``, ``prior-none``): the check that only the task differs, the
replay of the three runs, their scores on the same held-out settings, the
motion fitted to each run's own readings, and the baselines without a model;
and, without a model, a towing tank whose drag law is unknown
(``pbc.discovery.towing_tank``): its boundary, the two conditions of prior
knowledge on two designs, the learner's own probes, and an unknown world.
Run it as a program to write the figure and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.prior_knowledge_in_discovery out

The live runs, which ask a model and need its key, are a separate command
behind the optional dependency ``openai``: ``LIVE``, run with
``uv run --locked --no-dev --extra openai python -m pbc.discovery.force_lab
prior-full prior-partial prior-none``.
"""

from dataclasses import replace
from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.agents.display import AllowlistDisplay, RunDisplay
from pbc.agents.loop import MAX_CALLS_PER_MESSAGE
from pbc.authoring import FIGURE_COLOURS, diagrams
from pbc.authoring.repository import REPOSITORY_ROOT
from pbc.discovery import comparison, environment_allowlist, run_baselines, towing_tank
from pbc.discovery.force_lab import (
    BUDGET,
    MAX_STEPS,
    PROTOCOLS,
    RUNS,
    SEED,
    TOLERANCE,
    baselines,
    environment,
    fit_probes,
    probes,
    replay_run,
    task_of,
)
from pbc.discovery.towing_tank import (
    CONDITIONS as TANK_CONDITIONS,
)
from pbc.discovery.towing_tank import (
    UNKNOWN,
    WATER,
    Outcome,
    grid_design,
    one_sphere_design,
    random_design,
    route,
)
from pbc.experiment import Experiment, main
from pbc.figure_language import figsize, figure_style, finish

# The live runs of the lesson: a model, its key, and the extra openai.
LIVE = "pbc.discovery.force_lab prior-full prior-partial prior-none"

# The recorded runs, next to the page that shows them.
LESSON = REPOSITORY_ROOT / "site/lessons/agents-llm/06-prior-knowledge-in-discovery"
PROTOCOL = "prior-knowledge"
CONDITIONS = ("full", "partial", "none")
NAMES = {c: f"prior-{c}" for c in CONDITIONS}


def tasks(experiment: Experiment) -> None:
    """The task text of each condition; record the table."""
    experiment.table(
        "d2-tasks",
        [(c, task_of(RUNS[NAMES[c]].protocol, c)[1]) for c in CONDITIONS],
        [("condition", "", ""), ("the task the model was given", "", "")],
        "The task text of the three conditions; it is the only input that differs.",
    )


def fairness(experiment: Experiment) -> None:
    """What the three runs share, from the protocol and the record of each
    run; record the table."""
    entries = [RUNS[NAMES[c]] for c in CONDITIONS]
    protocols = [PROTOCOLS[e.protocol] for e in entries]
    same = {
        "protocol object": len({id(p) for p in protocols}) == 1,
        "model": len({e.info.model for e in entries}) == 1,
        "system prompt": len({task_of(e.protocol, e.condition)[0] for e in entries})
        == 1,
        "tools and bounds": len(
            {
                str(environment_allowlist(environment(e.protocol)).specs())
                for e in entries
            }
        )
        == 1,
        "budget and step limit": len({(p.budget, p.max_steps) for p in protocols}) == 1,
        "seed": len({e.info.seed for e in entries}) == 1,
        "tolerance": len({p.tolerance for p in protocols}) == 1,
        "held-out settings": len(
            {str(environment(e.protocol)._held_out) for e in entries}
        )
        == 1,
        "task text": len({task_of(e.protocol, e.condition)[1] for e in entries}) == 1,
    }
    experiment.table(
        "d2-fairness",
        [(what, "same" if equal else "differs") for what, equal in same.items()],
        [("what the runs share", "", ""), ("across the three conditions", "", "")],
        "What the three runs share, checked by the build from the protocol and"
        " the record of each run.",
    )


def score_table(experiment: Experiment, scores) -> None:
    """The three claims scored on the same held-out settings; record the
    table."""
    experiment.table(
        "d2-scores",
        [
            (c, s.probes, s.refused, s.claim["omega"], s.held_out_error, s.outcome)
            for c, s in scores.items()
        ],
        [
            ("condition", "", ""),
            ("probes", "", "d"),
            ("refused", "", "d"),
            ("claimed omega", "rad/s", ".3g"),
            ("held-out error", "relative", ".3g"),
            ("outcome", "", ""),
        ],
        "The three claims, scored again by the build on the same held-out settings.",
    )


def probe_fits(experiment: Experiment, runs, scores):
    """The motion fitted to each run's own readings; record the table and
    return the fits and their held-out errors."""
    fits = {c: fit_probes(PROTOCOL, probes(PROTOCOL, runs[c][1])) for c in CONDITIONS}
    own = {
        c: environment(PROTOCOL).held_out_error({"omega": float(f.params[0])})
        for c, f in fits.items()
    }
    experiment.table(
        "d2-probe-fits",
        [
            (
                c,
                float(f.params[0]),
                float(f.stderr[0]),
                f.chi2,
                f.dof,
                own[c],
                (scores[c].claim["omega"] - float(f.params[0])) / float(f.stderr[0]),
            )
            for c, f in fits.items()
        ],
        [
            ("condition", "", ""),
            ("fitted omega", "rad/s", ".4g"),
            ("standard error", "rad/s", ".2g"),
            ("chi-square", "", ".3g"),
            ("degrees of freedom", "", "d"),
            ("held-out error of the fit", "relative", ".3g"),
            ("claim minus fit", "standard errors", ".2g"),
        ],
        "The motion fitted to each run's own readings, and how far the agent's"
        " claim lies from that fit.",
    )
    return fits, own


def beside_the_baselines(experiment: Experiment, scores) -> None:
    """The three runs beside the baselines without a model; record the
    table."""
    rows = comparison(
        tuple(scores[c] for c in CONDITIONS), baselines(PROTOCOL), TOLERANCE
    )
    for row, condition in zip(rows, CONDITIONS, strict=False):
        row["who"] = f"agent, {condition}"
    experiment.table(
        "d2-baselines",
        [
            (
                r["who"],
                r["probes"],
                r["held_out_error"],
                "yes" if r["recovered"] else "no",
                r["note"],
            )
            for r in rows
        ],
        [
            ("method", "", ""),
            ("probes", "", "d"),
            ("held-out error", "", ".3g"),
            ("recovered", "", ""),
            ("note", "", ""),
        ],
        "The three runs and the baselines without a model, on the same spring"
        " with the same budget.",
    )


def draw_condition_errors(scores, own) -> Figure:
    """The held-out error of each condition's claim beside that of the fit
    to the same run's readings, with the tolerance."""
    x = np.arange(len(CONDITIONS))
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.bar(
        x - 0.18,
        [scores[c].held_out_error for c in CONDITIONS],
        0.36,
        color="#00429d",
        label="agent's claim",
    )
    ax.bar(
        x + 0.18,
        [own[c] for c in CONDITIONS],
        0.36,
        color="#93c4d2",
        label="fit to the run's readings",
    )
    ax.axhline(TOLERANCE, color="#93003a", linestyle="--", label="tolerance")
    ax.set_xticks(x, CONDITIONS)
    ax.set_xlabel("prior knowledge")
    ax.set_ylabel("held-out error (relative)")
    ax.legend(fontsize=8)
    return fig


def the_agents_budget(experiment: Experiment, probes_used: int) -> None:
    """Exercise 1: the baselines on the same spring with the agents' number
    of probes; record the table."""
    small = replace(PROTOCOLS[PROTOCOL], budget=probes_used)
    results = run_baselines(small.make(SEED), SEED)
    experiment.table(
        "small-budget",
        [
            (
                r.name,
                r.probes,
                r.held_out_error,
                "yes" if r.success and r.held_out_error <= TOLERANCE else "no",
                r.reason or "fit consistent with the noise",
            )
            for r in results
        ],
        [
            ("method", "", ""),
            ("probes", "", "d"),
            ("held-out error", "", ".3g"),
            ("recovered", "", ""),
            ("note", "", ""),
        ],
        "The baselines on the same spring with the agents' number of probes.",
    )


def phase_shift(experiment: Experiment, scores, fits) -> None:
    """Exercise 2: the phase shift the partial claim's frequency error causes
    at the latest probed time and at three times it; record the table."""
    delta = scores["partial"].claim["omega"] - float(fits["partial"].params[0])
    experiment.table(
        "phase-shift",
        [(t, t * delta) for t in (3.0, 9.0)],
        [("time", "s", ".0f"), ("phase shift", "rad", ".2g")],
        "The phase shift that the partial claim's frequency error causes, by the time.",
    )


def tank_boundary(experiment: Experiment) -> None:
    """The four decisions before the first probe, for the towing tank."""
    box = towing_tank.tank()
    controls = ", ".join(f"{c.name} ({c.unit})" for c in box.controls)
    experiment.table(
        "tank-boundary",
        [
            (
                "boundary",
                "the sphere and the fluid around it; the carriage and the"
                " gauge are outside",
            ),
            ("set by the experimenter", controls),
            (
                "read",
                f"{box.observation.name} ({box.observation.unit}), with a"
                f" relative noise of {100 * box.observation.sigma:g} percent",
            ),
            (
                "inside but not accessible",
                "the density and the viscosity of the fluid: fixed, never read",
            ),
            ("candidate structures", "power laws of the speed and the diameter"),
            (
                "prior",
                "knowledge-informed: the two drag laws; restricted prior:"
                " every power law of the grammar",
            ),
        ],
        columns=[("decision", "", "s"), ("in the towing tank", "", "s")],
        caption="What is decided before the first probe of the towing tank.",
    )


def _outcome_row(design: str, outcome: Outcome) -> tuple:
    return (
        design,
        outcome.condition,
        outcome.forms,
        outcome.consistent,
        outcome.chosen,
        "no claim" if outcome.chosen == "none" else f"{outcome.held_out_error:.2g}",
        "yes" if outcome.recovered else "no",
    )


_OUTCOME_COLUMNS = [
    ("design", "", "s"),
    ("condition", "", "s"),
    ("forms", "", "d"),
    ("consistent", "", "d"),
    ("chosen", "", "s"),
    ("held-out error", "", "s"),
    ("recovered", "", "s"),
]


def tank_conditions(experiment: Experiment) -> dict[tuple[str, str], Outcome]:
    """Both conditions on the same readings of the water tank, for the grid
    and for one sphere; record the table and return the outcomes."""
    designs = {"grid": grid_design(), "one sphere": one_sphere_design()}
    found = {
        (name, condition): route(WATER, design, condition)
        for name, design in designs.items()
        for condition in TANK_CONDITIONS
    }
    experiment.table(
        "tank-conditions",
        [_outcome_row(design, o) for (design, _), o in found.items()],
        _OUTCOME_COLUMNS,
        caption="The two conditions on the same twelve readings of the towing"
        " tank, for each design: the forms searched, how many are consistent,"
        " the form chosen (v the speed, d the diameter), and the judge's"
        " held-out error, relative, to two significant digits.",
    )
    return found


def draw_tank_boundary() -> Figure:
    """The towing tank as a system: the boundary, what is set, what is read,
    and what is inside but out of reach."""
    fig, ax = diagrams.canvas(6.4, 3.4, (0.0, 10.0), (0.0, 5.3))
    diagrams.line(
        ax,
        [(3.4, 0.9), (6.6, 0.9), (6.6, 4.7), (3.4, 4.7), (3.4, 0.9)],
        colour=2,
        linestyle=":",
    )
    diagrams.text(ax, (5.0, 5.0), "system boundary", colour=2)
    diagrams.circle(ax, (5.0, 3.0), 0.7, colour=0)
    diagrams.text(ax, (5.0, 3.0), "sphere")
    diagrams.text(
        ax,
        (5.0, 1.55),
        "fluid: density,\nviscosity; fixed,\nnever read",
        colour="#57606a",
    )
    diagrams.state_box(ax, (1.3, 3.0), "carriage", width=1.9, height=0.8, colour=0)
    diagrams.arrow(ax, (2.25, 3.25), (4.33, 3.25), colour=0)
    diagrams.text(ax, (2.0, 3.75), "sets $v$, $d$", ha="left")
    diagrams.state_box(ax, (8.7, 3.0), "gauge", width=1.9, height=0.8, colour=1)
    diagrams.arrow(ax, (5.67, 2.75), (7.75, 2.75), colour=1, linestyle="--")
    diagrams.text(ax, (6.75, 2.25), "reads $F$", ha="left")
    diagrams.text(
        ax,
        (5.0, 0.35),
        "solid: set by the experimenter;  dashed: read",
        colour="#57606a",
    )
    return fig


def draw_tank_conditions(found: dict[tuple[str, str], Outcome]) -> Figure:
    """The judge's error of each condition on each design, with the
    tolerance."""
    designs = list(dict.fromkeys(design for design, _ in found))
    x = np.arange(len(designs))
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line", legend=3))
        for k, (condition, hatch) in enumerate(
            zip(TANK_CONDITIONS, ("", "//"), strict=True)
        ):
            ax.bar(
                x + (k - 0.5) * 0.36,
                [found[(d, condition)].held_out_error for d in designs],
                0.36,
                color=FIGURE_COLOURS[k],
                hatch=hatch,
                edgecolor="white",
                label=condition,
            )
        ax.axhline(
            towing_tank.TOLERANCE,
            color=FIGURE_COLOURS[2],
            linestyle="--",
            label="tolerance",
        )
        ax.set_yscale("log")
        ax.set_xticks(x, designs)
        ax.set_xlabel("design of the twelve probes")
        ax.set_ylabel("held-out error\n(relative)")
        fig.legend(loc="outside lower center", ncols=1)
    return finish(fig)


def own_probes(experiment: Experiment) -> Outcome:
    """Exercise: twelve probes at random settings, the grammar of the
    restricted prior, and the judge's score."""
    outcome = route(WATER, random_design(), "restricted prior")
    experiment.table(
        "tank-own-probes",
        [_outcome_row("random", outcome)],
        _OUTCOME_COLUMNS,
        caption="Twelve probes at random settings of the towing tank, searched"
        " with every power law of the grammar and scored by the judge;"
        " held-out error relative, to two significant digits.",
    )
    return outcome


def unknown_world(experiment: Experiment) -> dict[str, Outcome]:
    """Exercise: both conditions on the grid of a tank whose fluid is of no
    known kind; record the table."""
    found = {c: route(UNKNOWN, grid_design(), c, seed=1) for c in TANK_CONDITIONS}
    experiment.table(
        "tank-unknown",
        [_outcome_row("grid", o) for o in found.values()],
        _OUTCOME_COLUMNS,
        caption="The two conditions on the grid of the tank with an unknown"
        " fluid; held-out error relative, to two significant digits.",
    )
    return found


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.number("tolerance", TOLERANCE, "g")
    experiment.number("budget", BUDGET)
    experiment.number("max-steps", MAX_STEPS)
    experiment.number("max-calls", MAX_CALLS_PER_MESSAGE)
    tasks(experiment)
    fairness(experiment)
    experiment.display(
        "allowlist", AllowlistDisplay(environment_allowlist(environment(PROTOCOL)))
    )

    # region: replay
    runs = {c: replay_run(NAMES[c], LESSON) for c in CONDITIONS}
    # endregion: replay
    for c in CONDITIONS:
        experiment.display(f"run-{c}", RunDisplay(*runs[c][:2]))
    scores = {c: runs[c][2] for c in CONDITIONS}
    score_table(experiment, scores)
    experiment.number("probes", scores["full"].probes)
    fits, own = probe_fits(experiment, runs, scores)
    beside_the_baselines(experiment, scores)
    experiment.figure(
        "fig-condition-errors", partial(draw_condition_errors, scores, own)
    )
    the_agents_budget(experiment, scores["full"].probes)
    phase_shift(experiment, scores, fits)

    tank_boundary(experiment)
    experiment.figure("fig-tank-boundary", draw_tank_boundary)
    found = tank_conditions(experiment)
    experiment.figure("fig-tank-conditions", partial(draw_tank_conditions, found))
    one_sphere = found[("one sphere", "restricted prior")]
    experiment.number("tank-budget", towing_tank.BUDGET)
    experiment.number("tank-tolerance", towing_tank.TOLERANCE, "g")
    experiment.number("tank-noise", 100 * towing_tank.NOISE, "g")
    experiment.number("one-sphere-rivals", one_sphere.consistent)
    experiment.number("one-sphere-chosen", one_sphere.chosen)
    experiment.number("one-sphere-error", one_sphere.held_out_error, ".2f")
    own = own_probes(experiment)
    experiment.number("own-chosen", own.chosen)
    experiment.number("own-outcome", "recovered" if own.recovered else "not recovered")
    unknown = unknown_world(experiment)
    experiment.number(
        "unknown-reason",
        unknown["knowledge-informed"].reason.replace(
            "no form of the grammar", "neither candidate"
        ),
    )
    experiment.number("unknown-chosen", unknown["restricted prior"].chosen)
    return experiment


if __name__ == "__main__":
    main(run)
