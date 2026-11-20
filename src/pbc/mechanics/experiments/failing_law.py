"""The part of the experiment of lesson D11 (MD6) where a known law fails
and is extended (F147; D3's outcome as an exercise of MD6).

A falling-ball viscometer, a stated synthetic world apart from the agent's
hidden one: spheres of one diameter and several densities fall through an
oil at their terminal speed, read with a relative noise. Stokes' law says
the terminal speed is the effective weight (weight minus buoyancy) divided
by ``3 pi mu d``. The world's drag has, besides Stokes' term, the inertial
correction of Oseen, ``(9 pi / 16) rho d^2 v^2``, which the experimenter is
not told.

The known law fails on the record. Two diagnoses are fitted: a missing
constant force, and an inadequate law of the drag. Two extensions of the
drag law, a quadratic correction and a power law, both fit the record; the
experiment where they disagree most in units of the noise is chosen and
read; and what remains ambiguous is stated. The experiment of the lesson
(``pbc.mechanics.experiments.hidden_variables``) calls ``extend``.
"""

import math
from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.data.fit import FitResult, fit_curve
from pbc.experiment import Experiment
from pbc.figure_language import figsize, figure_style, finish

# region: viscometer
VISCOSITY = 0.5  # Pa s, of the oil
OIL_DENSITY = 1260.0  # kg/m³
DIAMETER = 0.005  # m, of every sphere
NOISE = 0.01  # relative standard uncertainty of a terminal speed
RECORD = tuple(np.linspace(1e-4, 1e-3, 16))  # N, effective weights of the record
REACH = (5e-5, 1.1e-2)  # N, the lightest and heaviest spheres the lab owns
NEW_READINGS = 3  # readings of the discriminating experiment
SEED = 4
# A model is consistent with readings when its chi-square is within this many
# standard deviations of its expectation (as the judge of lesson A4).
FIT_SIGMAS = 3.0
# endregion: viscometer

STOKES = 3 * math.pi * VISCOSITY * DIAMETER  # N s/m
OSEEN = 9 * math.pi / 16 * OIL_DENSITY * DIAMETER**2  # N s²/m²


# region: extensions
def stokes(w, b):
    """The known law: the terminal speed (m/s) at the effective weight
    ``w`` (N) is ``w / b``."""
    return w / b


def missing_force(w, b, f):
    """Stokes' law with a constant force ``f`` (N) the law left out."""
    return (w - f) / b


def quadratic_drag(w, b, c):
    """A drag ``b v + c v^2``: the root of ``b v + c v^2 = w``."""
    return 2 * w / (b + np.sqrt(b**2 + 4 * c * w))


def power_drag(w, b, n):
    """A drag ``b v^n``: the terminal speed is ``(w / b)^(1 / n)``."""
    return (w / b) ** (1 / n)


def quadratic_with_force(w, b, c, f):
    """The quadratic drag with a constant force ``f`` (N) as well."""
    return quadratic_drag(w - f, b, c)


# endregion: extensions

MODELS = {
    "Stokes' law": (stokes, (STOKES,)),
    "a missing constant force": (missing_force, (STOKES, 0.0)),
    "quadratic drag": (quadratic_drag, (STOKES, 0.01)),
    "power-law drag": (power_drag, (STOKES, 1.0)),
    "quadratic drag and a constant force": (quadratic_with_force, (STOKES, 0.01, 0.0)),
}


def terminal_speed(w):
    """The world's terminal speed (m/s) at the effective weight ``w`` (N):
    Stokes' drag and Oseen's correction."""
    return quadratic_drag(np.asarray(w, dtype=float), STOKES, OSEEN)


def readings(weights, seed: int) -> np.ndarray:
    """Terminal speeds (m/s) read at ``weights`` (N), with the relative noise
    drawn from a generator seeded by ``seed``."""
    noise = np.random.default_rng(seed).normal(0.0, NOISE, len(weights))
    return terminal_speed(weights) * (1 + noise)


def fit(name: str, weights, speeds) -> FitResult:
    """The model ``name`` fitted to the speeds, each with the relative
    uncertainty of a reading."""
    model, start = MODELS[name]
    return fit_curve(
        model,
        np.asarray(weights, dtype=float),
        speeds,
        start,
        sigma=NOISE * np.asarray(speeds),
    )


def consistent(result: FitResult) -> bool:
    """The chi-square is within ``FIT_SIGMAS`` of its expectation."""
    return result.chi2 <= result.dof + FIT_SIGMAS * math.sqrt(2 * result.dof)


# region: discriminate
def discriminating_weight(quadratic: FitResult, power: FitResult) -> float:
    """The effective weight within the lab's reach where the two fitted
    extensions predict terminal speeds furthest apart, in units of the
    noise of a reading there."""
    weights = np.geomspace(*REACH, 400)
    one = quadratic_drag(weights, *quadratic.params)
    other = power_drag(weights, *power.params)
    apart = np.abs(one - other) / (NOISE * 0.5 * (one + other))
    return float(weights[np.argmax(apart)])


# endregion: discriminate


def _row(name: str, result: FitResult) -> tuple:
    return (
        name,
        len(result.params),
        result.chi2,
        result.dof,
        "yes" if consistent(result) else "no",
        "yes" if all(result.identifiable) else "no",
    )


COLUMNS = [
    ("model", "", "s"),
    ("parameters", "", "d"),
    ("chi-square", "", ".1f"),
    ("degrees of freedom", "", "d"),
    ("consistent", "", "s"),
    ("parameters determined", "", "s"),
]


def draw_extensions(
    weights, speeds, new_weights, new_speeds, fits: dict[str, FitResult]
) -> Figure:
    """The terminal speeds relative to Stokes' law fitted to the record,
    against the effective weight, with the fitted extensions."""
    b = fits["Stokes' law"].params[0]
    grid = np.geomspace(*REACH, 300)
    styles = {
        "a missing constant force": ":",
        "quadratic drag": "-",
        "power-law drag": "--",
    }
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line", legend=3))
        for i, (name, style) in enumerate(styles.items()):
            model = MODELS[name][0]
            ax.plot(
                grid,
                model(grid, *fits[name].params) / stokes(grid, b),
                color=FIGURE_COLOURS[i],
                linestyle=style,
                label=f"{name}, fitted to the record",
            )
        ax.errorbar(
            weights,
            speeds / stokes(np.asarray(weights), b),
            yerr=NOISE * speeds / stokes(np.asarray(weights), b),
            fmt="o",
            color="black",
            markersize=3,
            label="record (one standard deviation)",
        )
        ax.errorbar(
            new_weights,
            new_speeds / stokes(np.asarray(new_weights), b),
            yerr=NOISE * new_speeds / stokes(np.asarray(new_weights), b),
            fmt="s",
            color="black",
            markerfacecolor="none",
            markersize=5,
            label="discriminating readings",
        )
        ax.axhline(1.0, color="grey", linewidth=0.8)
        ax.set_xscale("log")
        ax.set_xlabel("effective weight of the sphere (N)")
        ax.set_ylabel("terminal speed relative\nto Stokes' law (dimensionless)")
        fig.legend(loc="outside lower center", ncols=1)
    return finish(fig)


def extend(experiment: Experiment):
    """The known law that fails and its extensions, for the lesson's page;
    returns the drawing of its figure, which the lesson's experiment
    records."""
    weights = np.array(RECORD)
    speeds = readings(weights, SEED)
    before = {
        name: fit(name, weights, speeds)
        for name in (
            "Stokes' law",
            "a missing constant force",
            "quadratic drag",
            "power-law drag",
        )
    }
    experiment.table(
        "known-law",
        [
            _row(name, before[name])
            for name in ("Stokes' law", "a missing constant force")
        ],
        columns=COLUMNS,
        caption="Stokes' law and the diagnosis of a missing constant force,"
        " fitted to the record of sixteen spheres: the chi-square of each, its"
        " degrees of freedom, whether it is consistent with the noise (within"
        " three standard deviations of its expectation), and whether the"
        " readings determine its parameters.",
    )
    residuals = before["Stokes' law"].residuals / (NOISE * speeds)
    experiment.number("record-spheres", len(RECORD))
    experiment.number("noise-percent", 100 * NOISE, "g")
    experiment.number("lightest", weights[0] * 1e3, ".2f")
    experiment.number("heaviest", weights[-1] * 1e3, ".2f")
    experiment.number("residual-light", residuals[0], ".1f")
    experiment.number("residual-middle", residuals[len(residuals) // 2], ".1f")
    experiment.number("residual-heavy", residuals[-1], ".1f")
    reynolds = OIL_DENSITY * speeds * DIAMETER / VISCOSITY
    experiment.number("reynolds-least", reynolds.min(), ".2f")
    experiment.number("reynolds-most", reynolds.max(), ".2f")

    experiment.table(
        "extensions-record",
        [_row(name, before[name]) for name in ("quadratic drag", "power-law drag")],
        columns=COLUMNS,
        caption="Two extensions of the drag law fitted to the same record, with"
        " the columns of the table before.",
    )
    chosen = discriminating_weight(before["quadratic drag"], before["power-law drag"])
    one = quadratic_drag(chosen, *before["quadratic drag"].params)
    other = power_drag(chosen, *before["power-law drag"].params)
    experiment.number("chosen-weight", chosen * 1e3, ".1f")
    experiment.number(
        "chosen-apart", abs(one - other) / (NOISE * 0.5 * (one + other)), ".0f"
    )
    experiment.number(
        "faster-extension", "quadratic drag" if one > other else "power-law drag"
    )

    new_weights = np.full(NEW_READINGS, chosen)
    new_speeds = readings(new_weights, SEED + 1)
    all_weights = np.concatenate([weights, new_weights])
    all_speeds = np.concatenate([speeds, new_speeds])
    after = {
        name: fit(name, all_weights, all_speeds)
        for name in (
            "quadratic drag",
            "power-law drag",
            "quadratic drag and a constant force",
        )
    }
    experiment.table(
        "extensions-after",
        [_row(name, result) for name, result in after.items()],
        columns=COLUMNS,
        caption="The extensions fitted to the record and the readings of the"
        " discriminating experiment, with a third that adds a constant force to"
        " the quadratic drag.",
    )
    survivors = [name for name, result in after.items() if consistent(result)]
    experiment.number("survivors", " and ".join(survivors) if survivors else "none")
    force = after["quadratic drag and a constant force"]
    low, high = force.interval("p2")
    experiment.number("force-low", low * 1e6, ".1f")
    experiment.number("force-high", high * 1e6, ".1f")
    experiment.number("force-share", 100 * max(abs(low), abs(high)) / weights[0], ".1f")
    experiment.number(
        "force-excludes-zero", "excludes" if low > 0 or high < 0 else "includes"
    )
    quadratic = after["quadratic drag"]
    experiment.number("quadratic-ratio", quadratic.params[1] / OSEEN, ".2f")
    return partial(
        draw_extensions,
        weights,
        speeds,
        new_weights,
        new_speeds,
        {**before},
    )
