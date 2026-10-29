"""The experiment of the lesson "Cosmic expansion and redshift".

Toy Friedmann models (``pbc.astrophysics.cosmology``): the scale factor of
four models integrated in time against its analytic form and their ages,
the distance-redshift relations by quadrature and by a ray followed back in
time against the analytic cases, the Hubble law and its first correction at
low redshift, and the turnover of the angular diameter distance. Run it as
a program to write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.astrophysics.experiments.cosmic_expansion out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from scipy.constants import Julian_year, kilo, parsec
from scipy.constants import c as C
from scipy.optimize import minimize_scalar

from pbc.astrophysics.cosmology import (
    Model,
    age,
    angular_diameter_distance,
    comoving_distance,
    de_sitter_comoving,
    einstein_de_sitter_comoving,
    expansion,
    flat_lambda_age,
    flat_lambda_scale_factor,
    hubble_rate,
    low_redshift_luminosity,
    luminosity_distance,
    milne_luminosity,
    ray_distance,
)
from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.verification.estimates import fitted_order

# region: setup
# Units: times in Hubble times 1/H0, distances in Hubble distances c/H0.
H0 = 70.0  # km/s/Mpc, a toy value that sets the scale in years and megaparsecs
MODELS = {
    "Einstein-de Sitter (matter only)": Model(matter=1.0),
    "empty (Milne)": Model(matter=0.0),
    "de Sitter (Lambda only)": Model(matter=0.0, lam=1.0),
    "flat, matter 0.3 and Lambda 0.7": Model(matter=0.3, lam=0.7),
}
# endregion: setup

# region: redshifts
redshifts = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
# endregion: redshifts

# region: low
low = [0.3, 0.1, 0.03, 0.01, 0.003]
# endregion: low

EDS, MILNE, DE_SITTER, TOY = MODELS.values()
HUBBLE_DISTANCE = C / kilo / H0  # Mpc
HUBBLE_TIME = parsec * 1e6 / kilo / H0 / Julian_year / 1e9  # Gyr
STYLES = list(
    zip(FIGURE_COLOURS, ("--", ":", "-.", "-"), ("o", "s", "^", "D"), strict=False)
)


def bound(value, limit):
    """A value at the level of round-off is shown as below ``limit``."""
    return f"{value:.1e}" if value > limit else f"below {limit:.0e}"


def expansion_histories(experiment: Experiment):
    """The scale factor of each model integrated back from today and on into
    the future, and its age by quadrature, against the analytic forms;
    record the table and return the histories."""
    analytic_age = [2 / 3, 1.0, None, flat_lambda_age(TOY.matter)]
    exact = [
        lambda tau: (1.5 * (tau + 2 / 3)) ** (2 / 3),
        lambda tau: 1 + tau,
        np.exp,
        lambda tau: flat_lambda_scale_factor(
            TOY.matter, tau + flat_lambda_age(TOY.matter)
        ),
    ]
    rows, histories = [], []
    for (name, model), t0, a_of in zip(
        MODELS.items(), analytic_age, exact, strict=True
    ):
        history = expansion(model, 1.5, 1.5)
        gap = np.max(np.abs(history.a / a_of(history.tau) - 1))
        assert gap < 1e-9
        histories.append(history)
        measured = None if t0 is None else age(model)
        rows.append(
            (
                name,
                model.deceleration,
                measured,
                t0,
                None if t0 is None else measured * HUBBLE_TIME,
                bound(gap, 1e-9),
            )
        )
    experiment.table(
        "expansion",
        rows,
        [
            ("model", "", ""),
            ("deceleration q0", "", ".2f"),
            ("age, quadrature", "1/H0", ".6f"),
            ("age, analytic", "1/H0", ".6f"),
            ("age", "Gyr", ".2f"),
            ("integrated a(t) against analytic, relative", "", ""),
        ],
        "Four toy models: the deceleration parameter today, the age by "
        "quadrature and in closed form in Hubble times and in billions of years "
        "for H0 = 70 km/s/Mpc, and the largest relative gap between the scale "
        "factor integrated in time and its analytic form; de Sitter has no "
        "beginning.",
    )
    return histories


def draw_expansion(histories) -> Figure:
    """The scale factor against the time from today for the four models."""
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for (name, _), history, (colour, style, _) in zip(
        MODELS.items(), histories, STYLES, strict=True
    ):
        ax.plot(history.tau, history.a, color=colour, linestyle=style, label=name)
    ax.axvline(0.0, color="#57606a", linewidth=0.8)
    ax.text(
        0.03,
        0.03,
        "today",
        transform=ax.get_xaxis_transform(),
        va="bottom",
        fontsize="small",
    )
    ax.set_xlabel("time from today (Hubble times 1/H0)")
    ax.set_ylabel("scale factor a (1 today)")
    ax.set_ylim(0.0, 4.5)
    ax.legend(fontsize="small", loc="upper left")
    return fig


def distances(experiment: Experiment):
    """For each model and redshift: the luminosity distance by quadrature
    against its analytic form, and the comoving distance of a ray followed
    back in time against the quadrature; record the two tables and return
    the luminosity distances."""
    analytic = {
        EDS: lambda z: (1 + z) * einstein_de_sitter_comoving(z),
        MILNE: milne_luminosity,
        DE_SITTER: lambda z: (1 + z) * de_sitter_comoving(z),
    }
    rows, curves = [], {}
    for name, model in MODELS.items():
        d_l = np.array([luminosity_distance(model, z) for z in redshifts])
        curves[model] = d_l
        ray = max(
            abs(ray_distance(model, z) / comoving_distance(model, z) - 1)
            for z in redshifts
        )
        assert ray < 1e-10
        if model in analytic:
            gap = np.max(np.abs(d_l / analytic[model](np.array(redshifts)) - 1))
            assert gap < 1e-12
            shown = bound(gap, 1e-12)
        else:
            shown = "no closed form"
        rows.append((name, shown, bound(ray, 1e-10)))
    experiment.table(
        "distance-checks",
        rows,
        [
            ("model", "", ""),
            ("quadrature against analytic D_L, relative", "", ""),
            ("ray in time against quadrature, relative", "", ""),
        ],
        "The largest relative gaps of the distance-redshift relation for "
        "z = 0.1 to 10: the luminosity distance by quadrature against its "
        "closed form, and the comoving distance of a ray followed back in time "
        "against the quadrature.",
    )
    experiment.table(
        "distances",
        [
            (
                z,
                comoving_distance(TOY, z) * HUBBLE_DISTANCE,
                curves[TOY][i] * HUBBLE_DISTANCE,
                angular_diameter_distance(TOY, z) * HUBBLE_DISTANCE,
                5 * np.log10(curves[TOY][i] * HUBBLE_DISTANCE) + 25,
            )
            for i, z in enumerate(redshifts)
        ],
        [
            ("redshift z", "", "g"),
            ("comoving distance", "Mpc", ".0f"),
            ("luminosity distance", "Mpc", ".0f"),
            ("angular diameter distance", "Mpc", ".0f"),
            ("distance modulus", "mag", ".2f"),
        ],
        "The distances of the flat toy model with matter 0.3 and Lambda 0.7, "
        "for H0 = 70 km/s/Mpc, to the nearest megaparsec, and the distance "
        "modulus 5 log10(D_L / 10 pc).",
    )
    return curves


def draw_distances(curves) -> Figure:
    """The luminosity distance against redshift, log-log: the quadrature as
    markers, the analytic forms as lines."""
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    z = np.geomspace(redshifts[0], redshifts[-1], 200)
    lines = {
        EDS: (1 + z) * einstein_de_sitter_comoving(z),
        MILNE: milne_luminosity(z),
        DE_SITTER: (1 + z) * de_sitter_comoving(z),
    }
    for (name, model), (colour, style, marker) in zip(
        MODELS.items(), STYLES, strict=True
    ):
        if model in lines:
            ax.loglog(
                z,
                lines[model],
                color=colour,
                linestyle=style,
                linewidth=1,
                label=f"{name}, analytic",
            )
        ax.loglog(
            redshifts,
            curves[model],
            marker,
            color=colour,
            markerfacecolor="none",
            label=f"{name}, quadrature",
        )
    ax.loglog(
        z, z, color="#57606a", linestyle=(0, (1, 4)), label="Hubble law, D = cz/H0"
    )
    ax.set_xlabel("redshift z")
    ax.set_ylabel("luminosity distance (c/H0)")
    ax.legend(fontsize="x-small", loc="upper left")
    return fig


def hubble_law(experiment: Experiment):
    """For each small redshift of ``low``: the relative gap of the toy
    model's luminosity distance from the Hubble law z and from the
    second-order form z + (1 - q0) z²/2; record the table and return the
    fitted orders."""
    d_l = np.array([luminosity_distance(TOY, z) for z in low])
    first = np.abs(d_l / np.array(low) - 1)
    second = np.abs(d_l / low_redshift_luminosity(TOY, low) - 1)
    orders = fitted_order(low, first), fitted_order(low, second)
    assert abs(orders[0] - 1) < 0.1 and abs(orders[1] - 2) < 0.15
    experiment.table(
        "hubble-law",
        [(z, d_l[i] * HUBBLE_DISTANCE, first[i], second[i]) for i, z in enumerate(low)],
        [
            ("redshift z", "", "g"),
            ("luminosity distance", "Mpc", ".2f"),
            ("relative gap from cz/H0", "", ".2e"),
            ("relative gap with the q0 term", "", ".2e"),
        ],
        "The luminosity distance of the flat toy model at low redshift against "
        "the Hubble law and against its second-order form with the deceleration "
        "parameter, to three significant digits.",
    )
    return orders


def turnover(model):
    """The redshift at which the angular diameter distance of ``model`` is
    largest, found numerically, and the distance there."""
    found = minimize_scalar(
        lambda z: -angular_diameter_distance(model, z),
        bounds=(0.1, 10.0),
        method="bounded",
        options={"xatol": 1e-8},
    )
    return float(found.x), -float(found.fun)


def draw_angular(peaks) -> Figure:
    """The angular diameter distance against redshift for the matter-only
    and the toy model, with their maxima marked."""
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    z = np.linspace(0.01, 10.0, 400)
    for model, (colour, style, marker), name, peak in zip(
        (EDS, TOY),
        (STYLES[0], STYLES[3]),
        ("matter only", "flat toy model"),
        peaks,
        strict=True,
    ):
        ax.plot(
            z,
            [angular_diameter_distance(model, x) for x in z],
            color=colour,
            linestyle=style,
            label=name,
        )
        ax.plot(
            *peak,
            marker,
            color=colour,
            markerfacecolor="none",
            label=f"largest distance, {name}",
        )
    ax.set_xlabel("redshift z")
    ax.set_ylabel("angular diameter distance (c/H0)")
    ax.legend(fontsize="small")
    return fig


def supernova(z=0.5):
    """Exercise 1: how much fainter, in magnitudes, a standard candle at
    redshift 0.5 appears in the toy model than in matter only and than in
    the empty model."""
    toy = luminosity_distance(TOY, z)
    return (
        5 * np.log10(toy / luminosity_distance(EDS, z)),
        5 * np.log10(toy / luminosity_distance(MILNE, z)),
    )


def acceleration():
    """Exercise 2: the redshift at which the toy model's expansion turned
    from slowing to speeding up, where the expansion speed da/dt = a E(a)
    is smallest, found by numerical minimisation, against the closed form
    (2 L / m)^(1/3) - 1."""
    found = minimize_scalar(
        lambda a: a * hubble_rate(TOY, a),
        bounds=(0.05, 1.0),
        method="bounded",
        options={"xatol": 1e-10},
    )
    return 1 / float(found.x) - 1, (2 * TOY.lam / TOY.matter) ** (1 / 3) - 1


def angular_size(size=0.03, z=1.0):
    """Exercise 3: the angle, in arcseconds, of a galaxy 30 kpc across at
    redshift 1 in the toy model, and its distance used."""
    d_a = angular_diameter_distance(TOY, z) * HUBBLE_DISTANCE
    return np.degrees(size / d_a) * 3600, d_a


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()

    histories = expansion_histories(experiment)
    experiment.figure("fig-expansion", partial(draw_expansion, histories))
    experiment.number("hubble-time", HUBBLE_TIME, ".2f")
    experiment.number("hubble-distance", HUBBLE_DISTANCE, ".0f")

    curves = distances(experiment)
    experiment.figure("fig-distances", partial(draw_distances, curves))

    orders = hubble_law(experiment)
    experiment.number("first-order", orders[0], ".2f")
    experiment.number("second-order", orders[1], ".2f")
    experiment.number("toy-q0", TOY.deceleration, ".2f")

    peaks = turnover(EDS), turnover(TOY)
    assert abs(peaks[0][0] - 1.25) < 1e-6
    experiment.figure("fig-angular", partial(draw_angular, peaks))
    experiment.number("eds-peak", peaks[0][0], ".4f")
    experiment.number("toy-peak", peaks[1][0], ".2f")
    experiment.number("toy-peak-distance", peaks[1][1] * HUBBLE_DISTANCE, ".0f")

    fainter_eds, fainter_milne = supernova()
    experiment.number("fainter-eds", fainter_eds, ".2f")
    experiment.number("fainter-milne", fainter_milne, ".2f")
    numerical, closed = acceleration()
    assert abs(numerical - closed) < 1e-6
    experiment.number("turn-z", numerical, ".4f")
    experiment.number("turn-z-closed", closed, ".4f")
    angle, d_a = angular_size()
    experiment.number("galaxy-angle", angle, ".2f")
    experiment.number("galaxy-distance", d_a, ".0f")
    return experiment


if __name__ == "__main__":
    main(run)
