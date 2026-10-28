"""The experiment of the lesson "Modified gravity".

Orbits under central forces other than Newton's inverse square
(``pbc.astrophysics.central_force``): the conserved quantities and the turn
of the periapsis of a power law beside the closed Kepler ellipse, the turn
per orbit against its first-order prediction as the law departs from the
inverse square, and a Yukawa term of several ranges. Run it as a program to
write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.astrophysics.experiments.modified_gravity out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.astrophysics.central_force import (
    angular_momentum,
    energy,
    first_order_precession,
    near_circular_precession,
    orbit,
    periapsis_start,
    power_law,
    power_law_potential,
    power_law_precession,
    precession_per_orbit,
    yukawa,
    yukawa_term,
)
from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.verification.estimates import fitted_order

# region: setup
# Units: GM = 1 and a = 1, so an unperturbed orbit takes 2 pi.
GM, A = 1.0, 1.0
E = 0.5  # the eccentricity of the starting ellipse
ORBITS = 10.5  # the duration, in unperturbed periods
# endregion: setup

# region: diagnostics
shown_delta = 0.1
# endregion: diagnostics

# region: power-law
deltas = [0.001, 0.003, 0.01, 0.03, 0.1, 0.3]
# endregion: power-law

# region: yukawa
alpha = 1e-3
scales = [0.1, 0.3, 1.0, 3.0, 10.0, 30.0]
# endregion: yukawa


def bound(value, limit):
    """A value at the level of round-off is shown as below ``limit``."""
    return f"{value:.1e}" if value > limit else f"below {limit:.0e}"


def run_law(force, e=E):
    """The orbit under ``force`` from the periapsis of the ellipse (A, e)."""
    x, v = periapsis_start(GM, A, e)
    return orbit(force, x, v, ORBITS * 2 * np.pi)


def diagnostics(experiment: Experiment):
    """Newton's law and the power law of ``shown_delta`` from the same start:
    the turn per orbit, the energy and the angular momentum along the
    orbit; record the table and return the two orbits."""
    rows, paths = [], []
    laws = (("inverse square", 0.0), (f"power law, delta {shown_delta}", shown_delta))
    for name, delta in laws:
        path = run_law(power_law(GM, A, delta))
        e = energy(path, power_law_potential(GM, A, delta))
        h = angular_momentum(path)
        rows.append(
            (
                name,
                len(path.periapsis_t),
                bound(abs(precession_per_orbit(path)), 1e-9)
                if delta == 0
                else f"{precession_per_orbit(path):.4f}",
                bound(np.max(np.abs(e / e[0] - 1)), 1e-10),
                bound(np.max(np.abs(h / h[0] - 1)), 1e-10),
            )
        )
        paths.append(path)

    experiment.table(
        "diagnostics",
        rows,
        [
            ("law", "", ""),
            ("periapsis passages", "", "d"),
            ("turn of the periapsis per orbit", "rad", ""),
            ("largest relative energy change", "", ""),
            ("largest relative angular momentum change", "", ""),
        ],
        "Two orbits from the periapsis of the same ellipse (a = 1, e = 0.5, "
        "GM = 1) over ten and a half periods, integrated by DOP853: the turn "
        "of the periapsis and the conserved quantities.",
    )
    return paths


def draw_rosette(paths) -> Figure:
    """The closed ellipse of the inverse square and the rosette of the power
    law, with the periapses of the power law marked."""
    newtonian, modified = paths
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    ax.plot(
        *modified.x.T,
        color=FIGURE_COLOURS[1],
        linestyle="-",
        linewidth=0.8,
        label=f"power law, delta = {shown_delta}",
    )
    ax.plot(
        *newtonian.x.T,
        color=FIGURE_COLOURS[0],
        linestyle="--",
        linewidth=1.5,
        label="inverse square",
    )
    ax.plot(
        *modified.periapsis_x.T,
        "o",
        color=FIGURE_COLOURS[1],
        markerfacecolor="none",
        label="periapses, power law",
    )
    ax.plot(0.0, 0.0, "+", color="#57606a", markersize=10, label="centre")
    ax.set_aspect("equal")
    ax.set_xlabel("x (units of a)")
    ax.set_ylabel("y (units of a)")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncols=2, fontsize="small")
    return fig


def power_law_scan(experiment: Experiment):
    """The turn per orbit of the power law for each delta against its
    first-order prediction; record the table and return the deltas, the
    measured turns, and the fitted order of the gap."""
    measured = np.array(
        [precession_per_orbit(run_law(power_law(GM, A, d))) for d in deltas]
    )
    predicted = power_law_precession(deltas, E)
    gap = measured - predicted
    order = fitted_order(deltas[::-1], np.abs(gap[::-1]))
    assert abs(order - 2) < 0.1
    assert np.all(np.abs(gap / predicted) < np.array(deltas))

    experiment.table(
        "power-law",
        [
            (d, m, p, g / p, g / p / d)
            for d, m, p, g in zip(deltas, measured, predicted, gap, strict=True)
        ],
        [
            ("delta", "", "g"),
            ("measured turn per orbit", "rad", ".6f"),
            ("first-order prediction", "rad", ".6f"),
            ("relative gap", "", ".2e"),
            ("relative gap / delta", "", ".3f"),
        ],
        "The turn of the periapsis per orbit under the power law "
        "-GM a^delta / r^(2 + delta), from the ellipse a = 1, e = 0.5, against "
        "the first-order prediction 2 pi delta (1 - sqrt(1 - e^2)) / e^2.",
    )
    return measured, order


def draw_power_law(measured) -> Figure:
    """The turn per orbit against delta, log-log: measured, the first-order
    line, and the near-circular formula."""
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    d = np.geomspace(deltas[0], deltas[-1], 100)
    ax.loglog(
        d,
        power_law_precession(d, E),
        color=FIGURE_COLOURS[0],
        linestyle="--",
        linewidth=1,
        label="first-order prediction, e = 0.5",
    )
    ax.loglog(
        deltas,
        measured,
        "o",
        color=FIGURE_COLOURS[1],
        markerfacecolor="none",
        label="measured, e = 0.5",
    )
    ax.loglog(
        d,
        near_circular_precession(d),
        color=FIGURE_COLOURS[2],
        linestyle=":",
        label="nearly circular orbit, any delta",
    )
    ax.set_xlabel("delta (departure of the exponent from 2)")
    ax.set_ylabel("turn of the periapsis per orbit (rad)")
    ax.legend(fontsize="small")
    return fig


def yukawa_scan(experiment: Experiment):
    """The turn per orbit with a Yukawa term of strength ``alpha`` and ten
    times it, for each range, against the first-order prediction; record
    the table and return the measured and predicted turns per unit alpha."""
    rows, measured, predicted = [], [], []
    for scale in scales:
        first = first_order_precession(yukawa_term(GM, scale), GM, A, E)
        turns = [
            precession_per_orbit(run_law(yukawa(GM, strength, scale)))
            for strength in (alpha, 10 * alpha)
        ]
        gaps = [
            turn / (strength * first) - 1
            for turn, strength in zip(turns, (alpha, 10 * alpha), strict=True)
        ]
        rows.append((scale, turns[0] / alpha, first, gaps[0], gaps[1]))
        measured.append(turns[0] / alpha)
        predicted.append(first)
    for *_, small, large in rows:
        assert abs(small) < 7 * alpha and abs(large) < 7 * 10 * alpha

    experiment.table(
        "yukawa",
        rows,
        [
            ("range lambda", "units of a", "g"),
            ("measured turn per orbit / alpha", "rad", ".4g"),
            ("first-order prediction / alpha", "rad", ".4g"),
            ("relative gap, alpha = 0.001", "", ".1e"),
            ("relative gap, alpha = 0.01", "", ".1e"),
        ],
        "The turn of the periapsis per orbit with a Yukawa term "
        "alpha (1 + r / lambda) exp(-r / lambda) added to Newton's attraction, "
        "from the ellipse a = 1, e = 0.5, per unit alpha, against the "
        "first-order prediction by quadrature.",
    )
    return np.array(measured), np.array(predicted), rows


def draw_yukawa(measured) -> Figure:
    """The turn per orbit per unit alpha against the range, log-log:
    measured, and the first-order prediction on a fine grid."""
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    fine = np.geomspace(scales[0], scales[-1], 120)
    prediction = [first_order_precession(yukawa_term(GM, s), GM, A, E) for s in fine]
    ax.loglog(
        fine,
        prediction,
        color=FIGURE_COLOURS[0],
        linestyle="--",
        linewidth=1,
        label="first-order prediction",
    )
    ax.loglog(
        scales,
        measured,
        "o",
        color=FIGURE_COLOURS[1],
        markerfacecolor="none",
        label="measured, alpha = 0.001",
    )
    for r, name in ((A * (1 - E), "periapsis"), (A * (1 + E), "apoapsis")):
        ax.axvline(r, color="#57606a", linestyle=":", linewidth=1)
        ax.text(
            r * 1.05,
            0.05,
            name,
            fontsize="small",
            rotation=90,
            va="bottom",
            transform=ax.get_xaxis_transform(),
        )
    ax.set_xlabel("range lambda (units of a)")
    ax.set_ylabel("turn per orbit / alpha (rad)")
    ax.legend(fontsize="small", loc="lower left")
    return fig


def near_circular():
    """Exercise 1: the turn per orbit of a nearly circular orbit (e = 0.01)
    under the power law of delta 0.3, against the near-circular formula and
    the first-order one."""
    measured = precession_per_orbit(run_law(power_law(GM, A, 0.3), e=0.01))
    return measured, near_circular_precession(0.3), power_law_precession(0.3, 0.01)


def hall_exponent():
    """Exercise 2: the delta that would turn Mercury's periapsis by 43
    arcseconds per century, with Mercury's period 87.969 days and
    eccentricity 0.2056 (given values)."""
    orbits = 36525 / 87.969
    turn = np.radians(43 / 3600) / orbits
    return orbits, turn / float(power_law_precession(1.0, 0.2056))


def yukawa_bound(predicted):
    """Exercise 3: the largest alpha allowed at each range when the turn per
    orbit is known to 1e-6 rad and agrees with Newton's."""
    return [(s, 1e-6 / p) for s, p in zip(scales, predicted, strict=True)]


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()

    paths = diagnostics(experiment)
    experiment.figure("fig-rosette", partial(draw_rosette, paths))
    experiment.number("shown-turn", precession_per_orbit(paths[1]), ".4f")
    experiment.number(
        "shown-first-order", float(power_law_precession(shown_delta, E)), ".4f"
    )

    measured, order = power_law_scan(experiment)
    experiment.figure("fig-power-law", partial(draw_power_law, measured))
    experiment.number("gap-order", order, ".2f")

    yukawa_measured, yukawa_predicted, rows = yukawa_scan(experiment)
    experiment.figure("fig-yukawa", partial(draw_yukawa, yukawa_measured))
    fine = np.geomspace(scales[0], scales[-1], 400)
    per_alpha = [first_order_precession(yukawa_term(GM, s), GM, A, E) for s in fine]
    experiment.number("yukawa-peak", fine[int(np.argmax(per_alpha))], ".2f")
    peak = int(np.argmax(yukawa_predicted))
    experiment.number("yukawa-gap", max(abs(row[3]) for row in rows), ".1e")
    experiment.number("yukawa-gap-large", max(abs(row[4]) for row in rows), ".1e")
    experiment.number(
        "yukawa-fall", yukawa_predicted[peak] / yukawa_predicted[-1], ".0f"
    )

    measured_circle, formula, first = near_circular()
    experiment.number("circle-measured", measured_circle, ".4f")
    experiment.number("circle-formula", formula, ".4f")
    experiment.number("circle-first-order", first, ".4f")
    orbits, delta = hall_exponent()
    experiment.number("mercury-orbits", orbits, ".1f")
    experiment.number("hall-delta", delta, ".2e")
    experiment.table(
        "yukawa-bound",
        yukawa_bound(yukawa_predicted),
        [("range lambda", "units of a", "g"), ("largest allowed alpha", "", ".1e")],
        "The largest strength alpha of the Yukawa term consistent with a turn "
        "of the periapsis of 1e-6 rad per orbit at most, for each range, from "
        "the first-order prediction.",
    )
    return experiment


if __name__ == "__main__":
    main(run)
