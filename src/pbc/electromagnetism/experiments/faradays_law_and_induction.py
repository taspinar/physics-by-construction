"""The experiment of the lesson "Faraday's law and induction".

The EMF of loops as a line integral of the force per charge, and minus the
rate of change of their flux as a surface integral and a central difference
(``pbc.electromagnetism.induction``): a loop moving through a non-uniform
field, a coil turning in a uniform one, and loops at rest beside a growing
tube of field. Run it as a program to write the figures and numbers of the
page:

    uv run --locked --no-dev \\
        python -m pbc.electromagnetism.experiments.faradays_law_and_induction out
"""

from dataclasses import dataclass
from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.electromagnetism.induction import (
    Rectangle,
    emf,
    flux,
    flux_rate,
    flux_tube_fields,
    rotating_coil,
)
from pbc.experiment import Experiment, main
from pbc.figure_language import LINE, figsize, figure_style, finish


def uniform(vector):
    vector = np.asarray(vector, dtype=float)
    return lambda points: np.broadcast_to(vector, points.shape)


# region: moving-loop
PEAK = 0.5  # T
BUMP = 0.05  # m
SPEED = 2.0  # m/s
WIDTH, HEIGHT = 0.04, 0.06  # m
STEP = 1e-5  # s, the step of the central difference
times = np.linspace(-0.06, 0.06, 241)  # s
FARADAY_TOLERANCE = 1e-6  # a chosen tolerance, relative to the largest EMF
# endregion: moving-loop


def bump(points):
    x = points[..., 0]
    return np.stack([0 * x, 0 * x, PEAK * np.exp(-((x / BUMP) ** 2))], axis=-1)


def loop_at(t):
    return Rectangle(
        [SPEED * t - WIDTH / 2, -HEIGHT / 2, 0.0], [WIDTH, 0.0, 0.0], [0.0, HEIGHT, 0.0]
    )


@dataclass(frozen=True)
class Passage:
    """The flux through the moving loop, its EMF along the wire, and minus
    the rate of the flux, at each time."""

    fluxes: np.ndarray
    motional: np.ndarray
    from_flux: np.ndarray
    gap: float


def moving_loop_run(experiment: Experiment) -> Passage:
    """The EMF of the moving loop from u x B along the wire against minus
    the rate of its flux; record the table of a few times."""
    carried = uniform([SPEED, 0.0, 0.0])
    fluxes = np.array([flux(bump, loop_at(t)) for t in times])
    motional = np.array(
        [emf(loop_at(t), magnetic=bump, velocity=carried) for t in times]
    )
    from_flux = np.array(
        [-flux_rate(lambda s: flux(bump, loop_at(s)), t, STEP) for t in times]
    )
    gap = float(np.max(np.abs(motional - from_flux)) / np.max(np.abs(motional)))
    assert gap < FARADAY_TOLERANCE, "the motional EMF is not -dPhi/dt"

    shown = [
        0,
        60,
        100,
        140,
        180,
        240,
    ]  # the time zero, where both are zero, is left out
    experiment.table(
        "moving-loop-run",
        [
            (times[i] * 1e3, fluxes[i] * 1e3, motional[i] * 1e3, from_flux[i] * 1e3)
            for i in shown
        ],
        [
            ("time", "ms", ".1f"),
            ("flux", "mWb", ".5f"),
            ("EMF along the wire", "mV", ".5f"),
            ("minus the rate of the flux", "mV", ".5f"),
        ],
        "The flux through the moving loop, its EMF from the force on the charges "
        "of the wire, and minus the rate of change of the flux, at a few of the "
        "computed times, to five decimals.",
    )
    return Passage(fluxes, motional, from_flux, gap)


def draw_moving_loop(passage: Passage) -> Figure:
    """The flux through the passing loop, and its EMF computed both ways."""
    with figure_style():
        fig, (top, bottom) = plt.subplots(2, 1, figsize=figsize("stacked"), sharex=True)
        top.plot(times * 1e3, passage.fluxes * 1e3, color=FIGURE_COLOURS[0])
        top.set_ylabel("flux (mWb)")
        bottom.plot(
            times * 1e3,
            passage.motional * 1e3,
            color=FIGURE_COLOURS[0],
            label="EMF along the wire",
        )
        bottom.plot(
            times[::8] * 1e3,
            passage.from_flux[::8] * 1e3,
            "o",
            markerfacecolor="none",
            color=FIGURE_COLOURS[1],
            label="minus the rate of the flux",
        )
        bottom.axhline(0.0, color=FIGURE_COLOURS[2], linewidth=LINE["guide"])
        bottom.set_xlabel("time (ms)")
        bottom.set_ylabel("EMF (mV)")
        # The legend would cover the curves: under the plot, in one column.
        fig.legend(loc="outside lower center", ncols=1)
    return finish(fig)


# region: coil
FIELD = np.array([0.3, 0.0, 0.0])  # T
OMEGA = 2 * np.pi * 50.0  # rad/s
COIL = dict(angular_velocity=OMEGA, width=0.1, height=0.2)
turn_times = np.linspace(0.0, 0.02, 81)  # s, one turn
# endregion: coil


def coil_run(experiment: Experiment) -> tuple[float, float]:
    """The EMF of the turning coil along the wire against minus the rate of
    its flux and against B A omega sin(omega t); record the table, return
    the largest gap and the peak."""
    area = COIL["width"] * COIL["height"]
    spin = np.array([0.0, 0.0, OMEGA])

    def turning(points):
        return np.cross(spin, points)

    coil_emf = np.array(
        [
            emf(rotating_coil(t, **COIL), magnetic=uniform(FIELD), velocity=turning)
            for t in turn_times
        ]
    )
    coil_from_flux = np.array(
        [
            -flux_rate(
                lambda s: flux(uniform(FIELD), rotating_coil(s, **COIL)), t, 1e-7
            )
            for t in turn_times
        ]
    )
    generator = FIELD[0] * area * OMEGA * np.sin(OMEGA * turn_times)
    peak = FIELD[0] * area * OMEGA
    coil_gap = float(np.max(np.abs(coil_emf - coil_from_flux)) / peak)
    formula_gap = float(np.max(np.abs(coil_emf - generator)) / peak)
    gap = max(coil_gap, formula_gap)
    assert gap < FARADAY_TOLERANCE, "the coil is not a generator"

    experiment.table(
        "coil-run",
        [
            ("EMF along the wire", np.max(coil_emf), np.min(coil_emf)),
            (
                "minus the rate of the flux",
                np.max(coil_from_flux),
                np.min(coil_from_flux),
            ),
            ("B A ω sin ωt", peak, -peak),
        ],
        [("computed as", "", ""), ("largest", "V", ".5f"), ("smallest", "V", ".5f")],
        "The largest and smallest EMF of the turning coil over one turn, from the "
        "force along the wire, from the rate of the flux, and from the generator "
        "formula, to five decimals.",
    )
    return gap, peak


# region: tube
TUBE = 0.02  # m
RATE = 10.0  # T/s
loops = {
    "around": Rectangle([-0.05, -0.04, 0.0], [0.09, 0.0, 0.0], [0.0, 0.07, 0.0]),
    "beside": Rectangle([0.04, -0.02, 0.0], [0.03, 0.0, 0.0], [0.0, 0.03, 0.0]),
    "across the edge": Rectangle(
        [-0.01, -0.005, 0.0], [0.03, 0.0, 0.0], [0.0, 0.03, 0.0]
    ),
}
# endregion: tube


def tube_magnetic_at(t):
    return lambda p: flux_tube_fields(
        p, strength=1.0 + RATE * t, rate=RATE, width=TUBE
    )[1]


def tube_electric(p):
    return flux_tube_fields(p, strength=1.0, rate=RATE, width=TUBE)[0]


def tube_run(experiment: Experiment) -> list[tuple[str, float, float, float]]:
    """For each loop at rest, the line integral of the induced field against
    minus the rate of its flux, and the strongest induced field on its wire;
    record the table, return its rows."""
    rows = []
    for name, loop in loops.items():
        induced = emf(loop, electric=tube_electric, nodes=48)
        change = flux_rate(
            lambda t, loop=loop: flux(tube_magnetic_at(t), loop, nodes=48), 0.0, 1e-3
        )
        points, _ = loop.edge(48)
        strongest = float(np.max(np.linalg.norm(tube_electric(points), axis=-1)))
        assert abs(induced + change) <= FARADAY_TOLERANCE * abs(RATE * np.pi * TUBE**2)
        rows.append((name, induced * 1e3, -change * 1e3, strongest * 1e3))

    experiment.table(
        "tube-run",
        rows,
        [
            ("loop", "", ""),
            ("EMF along the wire", "mV", ".5f"),
            ("minus the rate of the flux", "mV", ".5f"),
            ("strongest induced field on the wire", "mV/m", ".2f"),
        ],
        "For three loops at rest near a growing tube of field: the EMF from the "
        "induced electric field along the wire, minus the rate of change of the "
        "flux through the loop, and the strongest induced field on the wire, to "
        "the stated decimals.",
    )
    return rows


def draw_tube() -> Figure:
    """The induced field around the tube, the tube shaded, and the three
    loops."""
    lim = 0.08
    gx, gy = np.meshgrid(np.linspace(-lim, lim, 17), np.linspace(-lim, lim, 17))
    plane = np.stack([gx, gy, np.zeros_like(gx)], axis=-1)
    arrows = tube_electric(plane)
    fx, fy = np.meshgrid(np.linspace(-lim, lim, 201), np.linspace(-lim, lim, 201))
    shade = flux_tube_fields(
        np.stack([fx, fy, np.zeros_like(fx)], axis=-1),
        strength=1.0,
        rate=RATE,
        width=TUBE,
    )[1][..., 2]
    fig, ax = plt.subplots(figsize=(5.6, 5.6))
    ax.contourf(
        fx * 100,
        fy * 100,
        shade,
        levels=np.linspace(0.05, 1.0, 8),
        cmap="Greys",
        alpha=0.6,
    )
    ax.quiver(
        gx * 100, gy * 100, arrows[..., 0], arrows[..., 1], color=FIGURE_COLOURS[0]
    )
    for (name, loop), style in zip(loops.items(), ["--", "-", ":"], strict=True):
        corners = np.array(
            [
                loop.corner,
                loop.corner + loop.side_a,
                loop.corner + loop.side_a + loop.side_b,
                loop.corner + loop.side_b,
                loop.corner,
            ]
        )
        ax.plot(
            corners[:, 0] * 100,
            corners[:, 1] * 100,
            linestyle=style,
            color=FIGURE_COLOURS[1],
            linewidth=1.4,
            label=name,
        )
    ax.set_aspect("equal")
    ax.set_xlabel("x (cm)")
    ax.set_ylabel("y (cm)")
    ax.legend(fontsize=8, loc="upper left")
    return fig


def sliding_bar() -> tuple[float, float, float]:
    """Exercise 1: the EMF of a bar sliding on rails, from the force on its
    charges, from minus the rate of the flux, and B L v."""
    b_rails = np.array([0.0, 0.0, 0.2])
    gap, bar_speed, start = 0.1, 3.0, 0.5

    def rails(t):
        return Rectangle(
            [0.0, 0.0, 0.0], [start + bar_speed * t, 0.0, 0.0], [0.0, gap, 0.0]
        )

    def bar_only(points):
        # the bar is the side at the far end; the rest of the loop is at rest
        moving = np.isclose(points[..., 0], start)
        return np.where(moving[..., None], [bar_speed, 0.0, 0.0], 0.0)

    bar_emf = emf(rails(0.0), magnetic=uniform(b_rails), velocity=bar_only)
    rails_rate = -flux_rate(lambda t: flux(uniform(b_rails), rails(t)), 0.0, 1e-4)
    blv = b_rails[2] * gap * bar_speed
    return bar_emf, rails_rate, blv


def many_turns() -> tuple[float, float]:
    """Exercise 2: the peak EMF of one turn of the coil of 5 cm by 8 cm at
    25 Hz in 0.1 T, and of 200 turns in series."""
    one_turn = dict(angular_velocity=2 * np.pi * 25.0, width=0.05, height=0.08)
    quarter = 0.25 / 25.0  # a quarter of a turn, when the EMF is largest
    single = emf(
        rotating_coil(quarter, **one_turn),
        magnetic=uniform([0.1, 0.0, 0.0]),
        velocity=lambda p: np.cross([0.0, 0.0, one_turn["angular_velocity"]], p),
    )
    return single, 200 * single


def further_out(experiment: Experiment) -> tuple[list[float], list[float]]:
    """Exercise 3: the EMF, the rate of the flux, and the strongest induced
    field of the square beside the tube, moved out in steps of 1 cm; record
    the table, return the EMFs and the fields."""
    offsets = np.arange(0.04, 0.09, 0.01)
    beside_emf = []
    beside_rate = []
    beside_field = []
    for x0 in offsets:
        square = Rectangle([x0, -0.02, 0.0], [0.03, 0.0, 0.0], [0.0, 0.03, 0.0])
        beside_emf.append(abs(emf(square, electric=tube_electric, nodes=48)))
        beside_rate.append(
            abs(
                flux_rate(
                    lambda t, square=square: flux(
                        tube_magnetic_at(t), square, nodes=48
                    ),
                    0.0,
                    1e-3,
                )
            )
        )
        points, _ = square.edge(48)
        beside_field.append(
            float(np.max(np.linalg.norm(tube_electric(points), axis=-1)))
        )
    experiment.table(
        "further-out",
        [
            (x0 * 100, e * 1e3, r * 1e3, f * 1e3)
            for x0, e, r, f in zip(
                offsets, beside_emf, beside_rate, beside_field, strict=True
            )
        ],
        [
            ("near side at", "cm", ".0f"),
            ("size of the EMF", "mV", ".2e"),
            ("size of the rate of the flux", "mV", ".2e"),
            ("strongest field on the wire", "mV/m", ".2f"),
        ],
        "The size of the EMF of the small square beside the growing tube, the "
        "size of the rate of change of its flux, and the strongest induced field "
        "on its wire, for each distance of its near side from the axis, to three "
        "significant digits.",
    )
    return beside_emf, beside_field


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()

    passage = moving_loop_run(experiment)
    experiment.figure("fig-moving-loop", partial(draw_moving_loop, passage))
    experiment.number("times", len(times))
    experiment.number("moving-gap", passage.gap, ".1e")
    experiment.number("faraday-tolerance", FARADAY_TOLERANCE, ".0e")

    coil_gap, peak = coil_run(experiment)
    experiment.number("coil-gap", coil_gap, ".1e")
    experiment.number("peak", peak, ".4f")

    rows = tube_run(experiment)
    experiment.figure("fig-tube", draw_tube)
    total = RATE * np.pi * TUBE**2  # the rate of the whole flux of the tube, Wb/s
    experiment.number("total-mv", total * 1e3, ".4f")
    experiment.number("beside-percent", abs(rows[1][1]) / abs(rows[0][1]) * 100, ".2f")

    bar_emf, rails_rate, blv = sliding_bar()
    experiment.number("bar-emf-mv", bar_emf * 1e3, ".4f")
    experiment.number("rails-rate-mv", rails_rate * 1e3, ".4f")
    experiment.number("blv-mv", blv * 1e3, ".4f")

    single, peak_voltage = many_turns()
    experiment.number("single", single, ".4f")
    experiment.number("peak-voltage", peak_voltage, ".3f")

    beside_emf, beside_field = further_out(experiment)
    experiment.number("first-beside-emf", beside_emf[0] * 1e3, ".1e")
    experiment.number("last-beside-emf", beside_emf[-1] * 1e3, ".1e")
    experiment.number("first-beside-field", beside_field[0] * 1e3, ".1f")
    experiment.number("last-beside-field", beside_field[-1] * 1e3, ".1f")
    return experiment


if __name__ == "__main__":
    main(run)
