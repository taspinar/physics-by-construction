"""The part of the experiment of lesson D12 (MD9) that carries a thermal
law to held-out worlds of every level of transfer (F147;
``pbc.discovery.thermal_transfer``).

A scripted discoverer finds Newton's law of cooling for a small sphere
through the allowlist of a box; the law is then judged in five held-out
worlds, one per level, which the trace shows were never probed. The
experiment of the lesson
(``pbc.mechanics.experiments.generalisation_to_unseen_systems``) calls
``extend``.
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.discovery.thermal_transfer import (
    AIR,
    BUDGET,
    CONVECTION,
    STARTS,
    TOLERANCE,
    WORLDS,
    CoolingBox,
    discover,
    never_probed,
    radiation,
    transfer_error,
)
from pbc.experiment import Experiment
from pbc.figure_language import figsize, figure_style, finish


def draw_thermal_transfer(errors: dict[str, float], tolerance: float) -> Figure:
    """The error of the found law in each held-out world, and the
    tolerance."""
    names = list(errors)
    hatches = ["" if errors[n] <= tolerance else "//" for n in names]
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line"))
        positions = np.arange(len(names))[::-1]
        bars = ax.barh(
            positions,
            [errors[n] for n in names],
            color=FIGURE_COLOURS[0],
            edgecolor="black",
        )
        for bar, hatch in zip(bars, hatches, strict=True):
            bar.set_hatch(hatch)
        ax.axvline(tolerance, color="black", linestyle="--", linewidth=1)
        ax.annotate(
            "tolerance",
            (tolerance, len(names) - 0.5),
            textcoords="offset points",
            xytext=(4, -2),
            va="top",
        )
        ax.set_xscale("log")
        ax.set_yticks(positions, names)
        ax.set_xlabel("relative error of the temperature (dimensionless)")
        ax.set_ylabel("held-out world\n(hatched: beyond the tolerance)")
    return finish(fig)


def extend(experiment: Experiment):
    """The thermal discovery and its transfer, for the lesson's page;
    returns the drawing of its figure, which the lesson's experiment
    records."""
    box = CoolingBox()
    law = discover(box)
    accepted = [call.arguments for call, result in box.trace if result.ok]
    experiment.number("thermal-probes", len(accepted))
    experiment.number("thermal-budget", BUDGET)
    experiment.number("thermal-low", STARTS[0], "g")
    experiment.number("thermal-high", STARTS[1], "g")
    experiment.number("thermal-air", AIR, "g")
    experiment.number("thermal-k", 1e3 * law.k, ".3f")
    experiment.number("thermal-k-error", 1e3 * law.fit.stderr[0], ".1g")
    experiment.number("thermal-time-constant", 1 / law.k, ".0f")
    experiment.number("thermal-chi2", law.fit.chi2, ".0f")
    experiment.number("thermal-dof", law.fit.dof)
    experiment.number("thermal-tolerance", TOLERANCE, "g")

    rows, errors = [], {}
    for name, world in WORLDS.items():
        unprobed, nearest = never_probed(box.trace, world)
        error = transfer_error(law, world)
        errors[name] = error
        rows.append(
            (
                name,
                world.level,
                "never" if unprobed else "probed",
                nearest,
                error,
                "yes" if error <= TOLERANCE else "no",
            )
        )
    experiment.table(
        "thermal-transfer",
        rows,
        columns=[
            ("held-out world", "", "s"),
            ("level of transfer", "", "s"),
            ("probed", "", "s"),
            ("nearest probed start", "°C", ".0f"),
            ("relative error", "", ".2g"),
            ("within the tolerance", "", "s"),
        ],
        caption="Newton's law of cooling, found by the scripted discoverer, in"
        " each held-out world: its level of transfer, whether any probe of the"
        " trace had the world's conditions, the distance of the nearest probed"
        " start temperature from the world's, the root-mean-square error of the"
        " predicted temperature relative to the true excess over the air, to"
        " two significant digits, and whether it is within the tolerance.",
    )
    failed = [n for n, e in errors.items() if e > TOLERANCE]
    passed = [n for n, e in errors.items() if e <= TOLERANCE]
    experiment.number("thermal-failed", " and ".join(failed) if failed else "none")
    experiment.number("thermal-passed", ", ".join(passed) if passed else "none")
    experiment.number(
        "thermal-probed-worlds",
        "none"
        if all(row[2] == "never" for row in rows)
        else ", ".join(row[0] for row in rows if row[2] != "never"),
    )
    experiment.number(
        "thermal-in-bounds",
        "all"
        if all(STARTS[0] <= a["start"] <= STARTS[1] for a in accepted)
        else "not all",
    )
    for name, key in (("hot start", "hot"), ("sheathed sphere", "sheathed")):
        experiment.number(f"thermal-error-{key}", errors[name], ".2g")
    # The share of radiation in the loss at the hottest probed start and at
    # the start of the hot world.
    for start, key in ((STARTS[1], "probed"), (WORLDS["hot start"].start, "hot")):
        radiated = radiation(start, AIR)
        share = radiated / (radiated + CONVECTION * (start - AIR))
        experiment.number(f"radiation-share-{key}", 100 * share, ".1f")
    experiment.number(
        "thermal-largest-passed",
        max((errors[n] for n in passed), default=np.nan),
        ".1g",
    )
    return partial(draw_thermal_transfer, errors, TOLERANCE)
