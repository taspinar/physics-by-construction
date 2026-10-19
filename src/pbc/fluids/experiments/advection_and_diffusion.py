"""The experiment of the lesson "Advection and diffusion: schemes, stability,
and the diffusion a grid adds".

A quantity carried by a flow of constant speed, computed with the upwind,
central, and Lax-Wendroff schemes of ``pbc.fluids.advection``: the
diffusion of the upwind scheme measured from its runs against the modified
equation, a physical diffusion added to it, the stability of each scheme
against its Courant number, and a front that enters through the inflow
boundary. Run it as a program to write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.fluids.experiments.advection_and_diffusion out
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from scipy.special import erfc

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.fluids.advection import (
    amplification,
    fixed,
    inflow_outflow,
    mode_amplitude,
    modified_diffusion,
    step,
)
from pbc.verification.estimates import fitted_order

# region: diffusion
SPEED = 1.0  # m/s
LENGTH = 1.0  # m, a periodic domain
COURANT = 0.5
cells = [25, 50, 100, 200, 400]
WAVE = 1  # whole waves of the sine over the domain
DURATION = 1.0  # s: the wave crosses the domain once
# endregion: diffusion

# region: physical
PHYSICAL_CELLS = 100
viscosities = [2e-3, 1e-3, 3e-4, 1e-4, 0.0]  # m^2/s
# endregion: physical

# region: stability
STABILITY_CELLS = 64
STABILITY_STEPS = 200
runs = [
    ("upwind", 0.5, 0.0),
    ("upwind", 1.0, 0.0),
    ("upwind", 1.1, 0.0),
    ("Lax-Wendroff", 0.9, 0.0),
    ("Lax-Wendroff", 1.1, 0.0),
    ("central", 0.5, 0.0),
    ("upwind", 0.5, 0.25),
    ("upwind", 0.5, 0.3),
    ("central", 0.5, 0.25),
    ("central", 0.8, 0.1),
    ("central", 0.5, 0.6),
    ("Lax-Wendroff", 0.5, 0.3),
    ("Lax-Wendroff", 0.9, 0.2),
]  # scheme, Courant number C, diffusion number r
# endregion: stability

# region: front
front_cells = [40, 80, 160, 320, 640]
FRONT_START = 0.25  # m: the front at the start; behind it u = 1, ahead u = 0
FRONT_TIME = 0.5  # s
# endregion: front

DIFFUSION_ORDER_TOLERANCE = 0.05
ROUND_OFF = 1e-12


def centres(n: int) -> np.ndarray:
    """The centres of ``n`` equal cells on the domain."""
    return (np.arange(n) + 0.5) * LENGTH / n


def advect(u, courant, scheme, n_steps, boundary=None, diffusion=0.0):
    """``n_steps`` steps of ``scheme`` from the profile ``u``."""
    for _ in range(n_steps):
        if boundary is None:
            u = step(u, courant, scheme, diffusion=diffusion)
        else:
            u = step(u, courant, scheme, boundary, diffusion=diffusion)
    return u


def measured_diffusion(
    n: int, viscosity: float = 0.0, courant: float = COURANT
) -> float:
    """Advect a sine of one wave across the periodic domain once with the
    upwind scheme on ``n`` cells at the Courant number ``courant``, and
    return the diffusion coefficient that its loss of amplitude implies,
    A(T) = A(0) exp(-D k^2 T)."""
    dx = LENGTH / n
    dt = courant * dx / SPEED
    k = 2.0 * np.pi * WAVE / LENGTH
    start = np.sin(k * centres(n))
    end = advect(
        start,
        courant,
        "upwind",
        round(DURATION / dt),
        diffusion=viscosity * dt / dx**2,
    )
    ratio = mode_amplitude(end, WAVE) / mode_amplitude(start, WAVE)
    return -np.log(ratio) / (k * k * DURATION)


def diffusion_run(experiment: Experiment) -> float:
    """The diffusion measured on each grid against the modified equation;
    record the table, return the order of their relative difference."""
    measured = np.array([measured_diffusion(n) for n in cells])
    predicted = np.array(
        [modified_diffusion(SPEED, LENGTH / n, COURANT) for n in cells]
    )
    gaps = np.abs(measured - predicted) / predicted
    order = fitted_order(LENGTH / np.array(cells), gaps)
    assert abs(order - 2.0) < DIFFUSION_ORDER_TOLERANCE, (
        "the gap to the modified equation is not of order two"
    )
    experiment.table(
        "diffusion-run",
        [
            (n, LENGTH / n, m, p, g)
            for n, m, p, g in zip(cells, measured, predicted, gaps, strict=True)
        ],
        [
            ("cells", "", "d"),
            ("cell width", "m", ".4f"),
            ("measured diffusion", "m²/s", ".4e"),
            ("modified equation", "m²/s", ".4e"),
            ("relative difference", "", ".2e"),
        ],
        "The diffusion coefficient implied by the loss of amplitude of a sine "
        "advected once across the domain by the upwind scheme at a Courant "
        "number of one half, against the coefficient of its modified equation, "
        "for each grid.",
    )
    return order


def physical_run(experiment: Experiment) -> list[float]:
    """The diffusion measured with a physical viscosity added, against the
    viscosity plus the numerical diffusion; record the table, return the
    ratio of the numerical diffusion to the viscosity for each viscosity
    but zero."""
    dx = LENGTH / PHYSICAL_CELLS
    numerical = modified_diffusion(SPEED, dx, COURANT)
    rows = []
    for nu in viscosities:
        found = measured_diffusion(PHYSICAL_CELLS, nu)
        assert abs(found - (nu + numerical)) < 1e-3 * (nu + numerical), (
            "the measured diffusion is not the physical plus the numerical"
        )
        rows.append((nu, nu + numerical, found, numerical / nu if nu else None))
    experiment.table(
        "physical-run",
        rows,
        [
            ("viscosity", "m²/s", ".1e"),
            ("viscosity plus numerical", "m²/s", ".4e"),
            ("measured diffusion", "m²/s", ".4e"),
            ("numerical over physical", "", ".2f"),
        ],
        "The diffusion measured from the upwind scheme with an explicit "
        "physical diffusion on one hundred cells, against the viscosity plus "
        "the numerical diffusion of the modified equation, and the ratio of "
        "the numerical to the physical part.",
    )
    return [numerical / nu for nu in viscosities if nu]


def stability_run(
    experiment: Experiment,
) -> list[tuple[str, float, float, float, float]]:
    """The largest factor of a step over the Fourier modes of the grid,
    measured by applying the step to each mode, and the largest value after
    many steps of a square pulse; record the table and return its rows."""
    x = np.arange(STABILITY_CELLS) / STABILITY_CELLS
    pulse = np.where(np.abs(x - 0.5) < 0.125, 1.0, 0.0)
    rows = []
    for scheme, courant, r in runs:
        largest = float(
            np.max(np.abs(amplification(scheme, courant, STABILITY_CELLS, r)))
        )
        with np.errstate(over="ignore", invalid="ignore"):
            end = advect(pulse, courant, scheme, STABILITY_STEPS, diffusion=r)
        rows.append((scheme, courant, r, largest, float(np.max(np.abs(end)))))
    stable = [row for row in rows if row[3] <= 1.0 + ROUND_OFF]
    assert all(row[4] <= 1.0 + 0.2 for row in stable), "a stable scheme grew"
    assert all(row[4] > 1e6 for row in rows if row not in stable), (
        "an unstable scheme did not grow"
    )

    def shown(value: float) -> str:
        return f"{value:.1e}" if value >= 1e3 else f"{value:.3f}"

    experiment.table(
        "stability-run",
        [(s, c, r, g, shown(m)) for s, c, r, g, m in rows],
        [
            ("scheme", "", ""),
            ("Courant number", "", ".1f"),
            ("diffusion number", "", ".2f"),
            ("largest factor per step", "", ".4f"),
            ("largest value after the steps", "", ""),
        ],
        "For each scheme, Courant number and diffusion number: the largest "
        "modulus of the factor by which one step multiplies a Fourier mode of "
        "a grid of sixty-four cells, measured by applying the step to each "
        "mode, and the largest value of a square pulse of height one after "
        "two hundred steps.",
    )
    return rows


def front_profile(n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The upwind run of a front that the inflow keeps fed, on ``n`` cells:
    the centres, the computed profile, and the error-function front of the
    modified equation."""
    dx = LENGTH / n
    x = centres(n)
    start = np.where(x < FRONT_START, 1.0, 0.0)
    end = advect(
        start,
        COURANT,
        "upwind",
        round(FRONT_TIME / (COURANT * dx / SPEED)),
        boundary=inflow_outflow(1.0),
    )
    d = modified_diffusion(SPEED, dx, COURANT)
    smeared = 0.5 * erfc(
        (x - FRONT_START - SPEED * FRONT_TIME) / (2.0 * np.sqrt(d * FRONT_TIME))
    )
    return x, end, smeared


def front_run(experiment: Experiment) -> float:
    """The largest difference of the computed front from the sharp front of
    the exact solution and from the smeared front of the modified equation,
    for each grid; record the table, return the order of the second."""
    rows = []
    for n in front_cells:
        x, end, smeared = front_profile(n)
        sharp = np.where(x < FRONT_START + SPEED * FRONT_TIME, 1.0, 0.0)
        rows.append(
            (
                n,
                float(np.max(np.abs(end - sharp))),
                float(np.max(np.abs(end - smeared))),
            )
        )
    order = fitted_order(LENGTH / np.array(front_cells), [row[2] for row in rows])
    assert abs(order - 1.0) < 0.1, "the front does not approach the modified equation"
    experiment.table(
        "front-run",
        rows,
        [
            ("cells", "", "d"),
            ("largest difference from the sharp front", "", ".3f"),
            ("largest difference from the modified equation", "", ".2e"),
        ],
        "The largest difference between the upwind profile of a front fed by "
        "the inflow boundary and two references, for each grid: the sharp "
        "front of the exact advection, and the error-function front of the "
        "modified equation.",
    )
    return order


def draw_advected_pulse() -> Figure:
    """A square pulse carried once around the periodic domain by the upwind
    and the Lax-Wendroff schemes, against the exact profile, which is the
    pulse where it started."""
    n = 100
    x = centres(n)
    pulse = np.where(np.abs(x - 0.5) < 0.15, 1.0, 0.0)
    steps = round(DURATION / (COURANT * LENGTH / n / SPEED))
    upwind = advect(pulse, COURANT, "upwind", steps)
    lax_wendroff = advect(pulse, COURANT, "Lax-Wendroff", steps)
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.plot(
        x,
        pulse,
        color=FIGURE_COLOURS[2],
        linewidth=1.2,
        drawstyle="steps-mid",
        label="exact",
    )
    ax.plot(
        x,
        upwind,
        color=FIGURE_COLOURS[0],
        linestyle="--",
        marker="o",
        markersize=3,
        label="upwind",
    )
    ax.plot(
        x,
        lax_wendroff,
        color=FIGURE_COLOURS[1],
        linestyle=":",
        marker="s",
        markersize=3,
        label="Lax-Wendroff",
    )
    ax.set_xlabel("position (m)")
    ax.set_ylabel("u (dimensionless)")
    ax.legend(loc="upper right", frameon=False)
    return fig


def grid_for(viscosity: float) -> tuple[int, int, float, float, float, float]:
    """Exercise 1: a grid and a step on which the numerical diffusion of the
    upwind scheme is at most a tenth of ``viscosity`` and the scheme is
    stable. Return the cells, the steps over the duration, the Courant and
    diffusion numbers, the numerical diffusion, and the diffusion measured."""
    # a dx (1 - C) / 2 < a dx / 2 <= nu / 10 holds for every C when dx <= nu / (5 a)
    n = int(np.ceil(LENGTH * 5.0 * SPEED / viscosity))
    dx = LENGTH / n
    # the stability limit C + 2 r <= 1 is dt <= 1 / (a / dx + 2 nu / dx^2)
    steps = int(np.ceil(DURATION * (SPEED / dx + 2.0 * viscosity / dx**2)))
    courant = SPEED * DURATION / steps / dx
    r = viscosity * DURATION / steps / dx**2
    assert courant + 2.0 * r <= 1.0, "the step breaks the stability limit"
    numerical = modified_diffusion(SPEED, dx, courant)
    assert numerical <= viscosity / 10.0, "the numerical diffusion is too large"
    return n, steps, courant, r, numerical, measured_diffusion(n, viscosity, courant)


def courant_one() -> float:
    """Exercise 2: the diffusion measured with the upwind scheme at a Courant
    number of one, where each step moves the profile by exactly one cell."""
    n = PHYSICAL_CELLS
    k = 2.0 * np.pi * WAVE / LENGTH
    start = np.sin(k * centres(n))
    end = advect(start, 1.0, "upwind", round(DURATION * SPEED * n / LENGTH))
    return abs(mode_amplitude(end, WAVE) / mode_amplitude(start, WAVE) - 1.0)


def outflow_run(experiment: Experiment) -> list[float]:
    """Exercise 3: a pulse carried out through the right end, once with the
    open outflow and once with a fixed value zero beyond it, for the upwind
    and the Lax-Wendroff schemes; record the largest difference of the two
    runs while the pulse leaves."""
    n = 200
    x = centres(n)
    pulse = np.exp(-(((x - 0.5) / 0.02) ** 2))
    steps = round(0.5 / (0.8 * LENGTH / n / SPEED))  # the pulse at the outflow
    differences = []
    for scheme in ("upwind", "Lax-Wendroff"):
        open_end = advect(pulse, 0.8, scheme, steps, boundary=inflow_outflow(0.0))
        closed = advect(pulse, 0.8, scheme, steps, boundary=fixed(0.0, 0.0))
        differences.append(float(np.max(np.abs(open_end - closed))))
    assert differences[0] == 0.0, "the upwind scheme read the outflow ghost"
    assert differences[1] > 1e-6, "Lax-Wendroff did not read the outflow ghost"
    experiment.table(
        "outflow-run",
        [("upwind", "exactly zero"), ("Lax-Wendroff", f"{differences[1]:.2e}")],
        [("scheme", "", ""), ("largest difference of the two runs", "", "")],
        "The largest difference between a run with an open outflow and a run "
        "with a fixed value zero beyond the outflow end, when a pulse reaches "
        "it, for each scheme.",
    )
    return differences


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()

    experiment.number("diffusion-order", diffusion_run(experiment), ".3f")
    k = 2.0 * np.pi * WAVE / LENGTH
    kept = np.exp(-measured_diffusion(cells[0]) * k * k * DURATION)
    experiment.number("coarse-loss", (1.0 - kept) * 100, ".0f")

    ratios = physical_run(experiment)
    experiment.number("ratio-smallest", ratios[-1], ".0f")

    stability_run(experiment)

    experiment.number("front-order", front_run(experiment), ".2f")
    experiment.figure("fig-advected-pulse", draw_advected_pulse)

    n, steps, courant, r, numerical, found = grid_for(1e-2)
    experiment.number("fine-cells", n, "d")
    experiment.number("fine-steps", steps, "d")
    experiment.number("fine-courant", courant, ".4f")
    experiment.number("fine-r", r, ".4f")
    experiment.number("fine-numerical", numerical, ".3e")
    experiment.number("fine-diffusion", found, ".4e")

    change = courant_one()
    assert change < ROUND_OFF, "upwind at C = 1 is not an exact shift"
    experiment.number("round-off", ROUND_OFF, ".0e")

    outflow_run(experiment)
    return experiment


if __name__ == "__main__":
    main(run)
