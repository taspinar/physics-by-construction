"""The experiment of the lesson "Heat engines and thermodynamic cycles".

Ideal-gas cycles as sampled p-V paths (``pbc.thermodynamics.cycles``): the
first law leg by leg, the Carnot efficiency against 1 - T_cold / T_hot, the
Otto, Stirling, and Brayton cycles between the same two temperatures against
their closed forms and the Carnot bound, and the entropy the reservoirs gain.
Run it as a program to write the figures and numbers of the page:

    uv run --locked --no-dev python -m \\
        pbc.thermodynamics.experiments.heat_engines_and_thermodynamic_cycles out
"""

from math import log

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.thermodynamics.cycles import (
    Gas,
    R,
    balance,
    brayton,
    brayton_efficiency,
    carnot,
    carnot_efficiency,
    energy_change,
    heat,
    otto,
    otto_efficiency,
    reservoir_entropy,
    stirling,
    work,
)
from pbc.verification.estimates import fitted_order

# region: engines
gas = Gas(moles=1.0, cv=2.5 * R)  # one mole of a diatomic gas
HOT, COLD = 600.0, 300.0  # K, the two reservoirs
V_SMALL = 0.010  # m^3, the smallest volume of the Carnot cycle
EXPANSION = 2.0  # isothermal expansion of the Carnot cycle
COMPRESSION = 4.0  # the compression ratio of the Otto and Stirling cycles
PRESSURE_RATIO = 8.0  # of the Brayton cycle
POINTS = 2001  # samples per leg
# endregion: engines
# region: refinement
refinements = [11, 21, 41, 81, 161]  # samples per leg, coarsest first
# endregion: refinement

V_LARGE = V_SMALL * EXPANSION * (HOT / COLD) ** (1.0 / (gas.gamma - 1.0))


def below(value: float, bound: float, spec: str) -> str:
    """A value, or, when it is smaller than ``bound``, the bound: a heat or an
    entropy that is zero up to round-off or the error of the quadrature is not
    shown as a number."""
    return f"below {bound:.0e}" if abs(value) < bound else format(value, spec)


def cycles(points: int = POINTS) -> dict:
    """The five engines between the two reservoirs, by name."""
    p_min = gas.moles * R * COLD / V_LARGE
    return {
        "Carnot": carnot(gas, HOT, COLD, V_SMALL, EXPANSION, points),
        "Otto": otto(gas, HOT, COLD, V_LARGE, COMPRESSION, points),
        "Stirling": stirling(gas, HOT, COLD, V_LARGE, COMPRESSION, points, False),
        "Stirling, regenerated": stirling(
            gas, HOT, COLD, V_LARGE, COMPRESSION, points, True
        ),
        "Brayton": brayton(gas, HOT, COLD, p_min, PRESSURE_RATIO, points),
    }


def closed_forms() -> dict:
    """The efficiency of each engine from its closed form."""
    ln_r = log(COMPRESSION)
    stirling_plain = R * ln_r * (HOT - COLD) / (gas.cv * (HOT - COLD) + R * HOT * ln_r)
    return {
        "Carnot": carnot_efficiency(HOT, COLD),
        "Otto": otto_efficiency(gas, COMPRESSION),
        "Stirling": stirling_plain,
        "Stirling, regenerated": carnot_efficiency(HOT, COLD),
        "Brayton": brayton_efficiency(gas, PRESSURE_RATIO),
    }


def first_law(experiment: Experiment) -> float:
    """Heat, work, and energy change of each leg of the Otto cycle, and the
    residual of the first law; record the table and return the largest
    residual relative to the heat taken in."""
    legs = otto(gas, HOT, COLD, V_LARGE, COMPRESSION, POINTS)
    rows, residuals = [], []
    for leg in legs:
        q, w, du = heat(gas, leg), work(gas, leg), energy_change(gas, leg)
        residuals.append(abs(q - w - du))
        rows.append((leg.name, below(q, 1e-6, ".2f"), w, du, q - w - du))
    experiment.table(
        "first-law",
        rows,
        [
            ("leg", "", ""),
            ("heat taken in Q", "J", ""),
            ("work done W", "J", ".2f"),
            ("change of internal energy", "J", ".2f"),
            ("Q - W - change", "J", ".1e"),
        ],
        "The heat (the integral of T dS), the work (the integral of p dV), and "
        "the change of the internal energy along each leg of the Otto cycle, "
        "with the residual of the first law, at the samples per leg of the "
        "example.",
    )
    heat_in = balance(gas, legs, HOT, COLD).heat_in
    return max(residuals) / heat_in


def comparison(experiment: Experiment) -> list:
    """The balance of each engine against its closed form and the Carnot
    bound; record the table and return its rows."""
    forms = closed_forms()
    bound = carnot_efficiency(HOT, COLD)
    rows = []
    for name, legs in cycles().items():
        b = balance(gas, legs, HOT, COLD)
        rows.append(
            (
                name,
                b.work,
                b.heat_in,
                b.efficiency,
                forms[name],
                bound,
                below(b.reservoir_entropy, 1e-6, ".3f"),
                b.reservoir_entropy,
            )
        )
    experiment.table(
        "comparison",
        [row[:7] for row in rows],
        [
            ("engine", "", ""),
            ("work per cycle", "J", ".1f"),
            ("heat from the hot reservoir", "J", ".1f"),
            ("efficiency", "", ".6f"),
            ("closed form", "", ".6f"),
            ("Carnot bound", "", ".6f"),
            ("entropy gained by the reservoirs", "J/K", ""),
        ],
        "Five ideal-gas engines between reservoirs at 600 K and 300 K: the work "
        "and the heat from the sampled paths, the efficiency against its closed "
        "form and the Carnot bound, and the entropy the two reservoirs gain per "
        "cycle.",
    )
    return rows


def refinement(experiment: Experiment) -> float:
    """The error of the Carnot efficiency and the residual of the first law
    of the Otto cycle against the number of samples per leg; record the
    table and return the fitted order of the efficiency error."""
    rows, errors = [], []
    exact = carnot_efficiency(HOT, COLD)
    for points in refinements:
        c = balance(gas, carnot(gas, HOT, COLD, V_SMALL, EXPANSION, points), HOT, COLD)
        o = balance(gas, otto(gas, HOT, COLD, V_LARGE, COMPRESSION, points), HOT, COLD)
        errors.append(abs(c.efficiency - exact))
        rows.append((points - 1, abs(c.efficiency - exact), abs(o.first_law_residual)))
    experiment.table(
        "refinement",
        rows,
        [
            ("intervals per leg", "", "d"),
            ("error of the Carnot efficiency", "", ".2e"),
            ("first-law residual of the Otto cycle", "J", ".2e"),
        ],
        "The error of the computed Carnot efficiency against 1 - T_cold / T_hot "
        "and the residual of the first law over the Otto cycle, as the paths are "
        "sampled more finely.",
    )
    steps = [1.0 / (points - 1) for points in refinements]
    return fitted_order(steps, errors)


def draw_cycles_pv() -> Figure:
    """The Carnot, Otto, and Stirling cycles in the p-V plane, log-log, one
    panel each, with the two isotherms of the reservoirs."""
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.2), sharex=True, sharey=True)
    styles = {
        "Carnot": ("-", FIGURE_COLOURS[0]),
        "Otto": ("--", FIGURE_COLOURS[1]),
        "Stirling": ("-.", FIGURE_COLOURS[4]),
    }
    engines = cycles(201)
    v = np.geomspace(V_SMALL, V_LARGE, 300)
    for ax, (name, (line, colour)) in zip(axes, styles.items(), strict=True):
        for temperature in (HOT, COLD):
            ax.plot(
                1e3 * v,
                1e-3 * gas.pressure(v, temperature),
                color=FIGURE_COLOURS[2],
                linestyle=":",
                linewidth=0.8,
            )
        volume = np.concatenate([leg.volume for leg in engines[name]])
        temperature = np.concatenate([leg.temperature for leg in engines[name]])
        ax.plot(
            1e3 * volume,
            1e-3 * gas.pressure(volume, temperature),
            color=colour,
            linestyle=line,
            linewidth=1.8,
        )
        ax.set_title(name, fontsize="medium")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xticks([10, 30, 100], labels=["10", "30", "100"])
        ax.set_yticks([20, 50, 100, 200, 500], labels=["20", "50", "100", "200", "500"])
        ax.minorticks_off()
        ax.set_xlabel("volume (L)")
    for temperature, offset in ((HOT, 8), (COLD, -14)):
        axes[0].annotate(
            f"{temperature:.0f} K",
            (1e3 * V_LARGE, 1e-3 * gas.pressure(V_LARGE, temperature)),
            xytext=(-34, offset),
            textcoords="offset points",
            color=FIGURE_COLOURS[2],
            fontsize="small",
        )
    axes[0].set_ylabel("pressure (kPa)")
    fig.tight_layout()
    return fig


def draw_otto_against_carnot() -> Figure:
    """The efficiency and the work of the Otto cycle against its compression
    ratio, with the closed form and the Carnot bound."""
    largest = (HOT / COLD) ** (1.0 / (gas.gamma - 1.0))
    ratios = np.array([1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5])
    computed = [
        balance(gas, otto(gas, HOT, COLD, V_LARGE, r, 401), HOT, COLD) for r in ratios
    ]
    fine = np.linspace(1.2, largest, 300)
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(6.4, 4.6), sharex=True)
    top.plot(
        fine, otto_efficiency(gas, fine), color=FIGURE_COLOURS[0], label="closed form"
    )
    top.plot(
        ratios,
        [b.efficiency for b in computed],
        color=FIGURE_COLOURS[1],
        marker="o",
        linestyle="none",
        label="from the sampled path",
    )
    top.axhline(
        carnot_efficiency(HOT, COLD),
        color=FIGURE_COLOURS[2],
        linestyle="--",
        label="Carnot bound",
    )
    top.set_ylabel("efficiency")
    top.legend(frameon=False, loc="lower right")
    bottom.plot(ratios, [b.work for b in computed], color=FIGURE_COLOURS[1], marker="o")
    bottom.axvline(largest, color=FIGURE_COLOURS[2], linestyle=":")
    bottom.annotate(
        "compression reaches 600 K",
        (largest, 0.85),
        xycoords=("data", "axes fraction"),
        xytext=(-6, 0),
        textcoords="offset points",
        ha="right",
        color=FIGURE_COLOURS[2],
    )
    bottom.set_xlabel("compression ratio r")
    bottom.set_ylabel("work per cycle (J)")
    fig.tight_layout()
    return fig


def impossible_engine(experiment: Experiment) -> None:
    """Exercise 1: the entropy the reservoirs would gain from a claimed engine;
    record the table."""
    heat_in, work_out = 1000.0, 600.0
    experiment.table(
        "impossible-engine",
        [
            (
                work_out / heat_in,
                carnot_efficiency(HOT, COLD),
                reservoir_entropy(heat_in, heat_in - work_out, HOT, COLD),
            )
        ],
        [
            ("claimed efficiency", "", ".3f"),
            ("Carnot bound", "", ".3f"),
            ("entropy gained by the reservoirs", "J/K", ".3f"),
        ],
        "The claimed engine against the Carnot bound, and the entropy the two "
        "reservoirs would gain per cycle if the claim were true.",
    )


def monatomic_otto(experiment: Experiment) -> None:
    """Exercise 2: the largest compression ratio of an Otto cycle of a
    monatomic gas between the reservoirs, and its efficiency there; record the
    table."""
    mono = Gas(moles=1.0, cv=1.5 * R)
    largest = (HOT / COLD) ** (1.0 / (mono.gamma - 1.0))
    experiment.table(
        "monatomic-otto",
        [
            (
                mono.gamma,
                largest,
                otto_efficiency(mono, largest),
                carnot_efficiency(HOT, COLD),
            )
        ],
        [
            ("gamma", "", ".4f"),
            ("largest compression ratio", "", ".4f"),
            ("Otto efficiency there", "", ".4f"),
            ("Carnot bound", "", ".4f"),
        ],
        "The Otto cycle of a monatomic ideal gas at the largest compression ratio "
        "the two reservoirs allow.",
    )


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.number("first-law-largest", first_law(experiment), ".1e")
    experiment.figure("fig-cycles-pv", draw_cycles_pv)
    rows = comparison(experiment)
    carnot_row = rows[0]
    experiment.number("carnot-efficiency", carnot_row[3], ".6f")
    experiment.number(
        "smallest-entropy",
        min(
            row[7] for row in rows if row[0] not in ("Carnot", "Stirling, regenerated")
        ),
        ".3f",
    )
    experiment.number("refinement-order", refinement(experiment), ".2f")
    experiment.figure("fig-otto-against-carnot", draw_otto_against_carnot)
    impossible_engine(experiment)
    monatomic_otto(experiment)
    return experiment


if __name__ == "__main__":
    main(run)
