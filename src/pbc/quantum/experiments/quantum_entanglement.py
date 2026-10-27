"""The experiment of the lesson "Quantum entanglement, Bell and CHSH".

Pairs of spins in the singlet state, measured at two settings
(``pbc.quantum.bell``): the correlations computed from sampled counts
against -cos(alpha - beta), the CHSH value S from four sampled correlations
against the local bound 2 and Tsirelson's bound 2 sqrt(2), and the same for a
local hidden-variable model. Every random draw takes a fixed seed. Run it as
a program to write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.quantum.experiments.quantum_entanglement out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from scipy.optimize import brentq

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.quantum.bell import (
    CHSH_ANGLES,
    LOCAL_BOUND,
    SINGLET,
    TSIRELSON_BOUND,
    chsh,
    chsh_error,
    correlation,
    correlation_error,
    density,
    deterministic_strategies,
    family,
    joint_probabilities,
    local_correlation,
    local_counts,
    marginal,
    quantum_correlation,
    sample_counts,
    setting_pairs,
    werner,
)

# region: setup
# Each pair is measured once, at one pair of settings; the pairs of different
# settings are different pairs, as in an experiment.
SEED = 20261028
SINGLET_STATE = density(SINGLET)
# endregion: setup

# region: correlations
relative_degrees = np.arange(0, 181, 15)  # beta - alpha
pairs_per_angle = 2_000
# endregion: correlations

# region: chsh
pairs_per_setting = 10_000
# endregion: chsh

# region: family
family_degrees = np.arange(
    0, 91, 7.5
)  # theta: a = 0, b = theta, a' = 2 theta, b' = 3 theta
pairs_per_family_setting = 2_000
# endregion: family


def rounded(value):
    """``value`` with round-off below 1e-12 removed, so that a zero is not
    printed with a sign."""
    return float(np.round(value, 12)) + 0.0


def quantum_counts(alpha, beta, count, rng, rho=SINGLET_STATE):
    """The counts of ``count`` pairs in the state ``rho``, sampled from its
    joint probabilities at the settings ``alpha`` and ``beta``."""
    return sample_counts(joint_probabilities(rho, alpha, beta), count, rng)


def correlations_run(experiment: Experiment):
    """The correlation of the singlet and of the local model at each
    relative angle, from sampled counts; record the table."""
    rng = np.random.default_rng(SEED)
    delta = np.radians(relative_degrees)
    rows, found = [], {"quantum": [], "local": []}
    for d in delta:
        q = quantum_counts(0.0, d, pairs_per_angle, rng)
        c = local_counts(0.0, d, pairs_per_angle, rng)
        found["quantum"].append((correlation(q), correlation_error(q)))
        found["local"].append((correlation(c), correlation_error(c)))
        exact = correlation(joint_probabilities(SINGLET_STATE, 0.0, d))
        assert abs(exact - quantum_correlation(0.0, d)) < 1e-14
    quantum, local = (np.array(found[k]) for k in ("quantum", "local"))
    for values, model in (
        (quantum, quantum_correlation(0.0, delta)),
        (local, local_correlation(0.0, delta)),
    ):
        spread = np.sqrt((1 - model**2) / pairs_per_angle)
        shown = spread > 0
        assert np.all(values[~shown, 0] == model[~shown])
        assert np.all(np.abs(values[shown, 0] - model[shown]) < 4 * spread[shown])
    for k, degrees in enumerate(relative_degrees):
        rows.append(
            (
                degrees,
                quantum[k, 0],
                rounded(quantum_correlation(0.0, delta[k])),
                local[k, 0],
                rounded(local_correlation(0.0, delta[k])),
            )
        )

    experiment.table(
        "correlations",
        rows,
        [
            ("angle between the settings", "degree", "d"),
            ("singlet, sampled", "", "+.3f"),
            ("-cos", "", "+.3f"),
            ("local model, sampled", "", "+.3f"),
            ("-1 + 2 angle / pi", "", "+.3f"),
        ],
        "The correlation E, the mean of the product of the two outcomes, from "
        "two thousand sampled pairs at each angle between the settings: the "
        "singlet against -cos of the angle and the local model against its "
        "straight line.",
    )
    return delta, quantum, local


def draw_correlations(delta, quantum, local) -> Figure:
    """The sampled correlations of the singlet and the local model with
    their predictions."""
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    fine = np.linspace(0, np.pi, 181)
    ax.plot(
        np.degrees(fine),
        quantum_correlation(0.0, fine),
        color=FIGURE_COLOURS[0],
        linestyle="--",
        label="singlet, -cos",
    )
    ax.plot(
        np.degrees(fine),
        local_correlation(0.0, fine),
        color=FIGURE_COLOURS[1],
        linestyle=":",
        label="local model, straight line",
    )
    ax.errorbar(
        np.degrees(delta),
        quantum[:, 0],
        yerr=quantum[:, 1],
        fmt="o",
        color=FIGURE_COLOURS[0],
        markerfacecolor="none",
        capsize=3,
        label="singlet, sampled",
    )
    ax.errorbar(
        np.degrees(delta),
        local[:, 0],
        yerr=local[:, 1],
        fmt="s",
        color=FIGURE_COLOURS[1],
        markerfacecolor="none",
        capsize=3,
        label="local model, sampled",
    )
    ax.set_xticks(np.arange(0, 181, 30))
    ax.set_xlabel("angle between the two settings (degree)")
    ax.set_ylabel("correlation E (dimensionless)")
    ax.legend(fontsize="small", loc="upper left")
    return fig


def chsh_counts(sampler, angles, count, rng):
    """The four tables of counts of the CHSH settings, sampled by
    ``sampler(alpha, beta, count, rng)``."""
    return [sampler(alpha, beta, count, rng) for alpha, beta in setting_pairs(angles)]


def chsh_value(tables):
    """S and its standard error from the four tables of counts."""
    return (
        chsh([correlation(t) for t in tables]),
        chsh_error([correlation_error(t) for t in tables]),
    )


def chsh_run(experiment: Experiment):
    """S of the singlet and of the local model at the standard settings,
    from sampled counts, against both bounds; record the tables."""
    rng = np.random.default_rng(SEED + 1)
    tables = {
        "singlet": chsh_counts(quantum_counts, CHSH_ANGLES, pairs_per_setting, rng),
        "local model": chsh_counts(local_counts, CHSH_ANGLES, pairs_per_setting, rng),
    }
    names = ["a, b", "a, b'", "a', b", "a', b'"]
    pairs = setting_pairs(CHSH_ANGLES)
    settings_rows = [
        (
            name,
            np.degrees(alpha),
            np.degrees(beta),
            correlation(tables["singlet"][k]),
            correlation_error(tables["singlet"][k]),
            correlation(tables["local model"][k]),
            correlation_error(tables["local model"][k]),
        )
        for k, (name, (alpha, beta)) in enumerate(zip(names, pairs, strict=True))
    ]
    summary, values = [], {}
    for model, predicted in (
        ("singlet", chsh(quantum_correlation(*np.transpose(pairs)))),
        ("local model", chsh(local_correlation(*np.transpose(pairs)))),
    ):
        s, error = chsh_value(tables[model])
        values[model] = (s, error)
        summary.append(
            (
                model,
                abs(s),
                error,
                abs(predicted),
                (abs(s) - LOCAL_BOUND) / error,
                (TSIRELSON_BOUND - abs(s)) / error,
            )
        )
    s_quantum, e_quantum = values["singlet"]
    assert abs(abs(s_quantum) - TSIRELSON_BOUND) < 4 * e_quantum
    assert abs(s_quantum) - LOCAL_BOUND > 20 * e_quantum
    s_local, e_local = values["local model"]
    assert abs(abs(s_local) - LOCAL_BOUND) < 4 * e_local

    experiment.table(
        "chsh-settings",
        settings_rows,
        [
            ("pair of settings", "", ""),
            ("A's angle", "degree", ".0f"),
            ("B's angle", "degree", ".0f"),
            ("singlet E", "", "+.4f"),
            ("its standard error", "", ".4f"),
            ("local model E", "", "+.4f"),
            ("its standard error", "", ".4f"),
        ],
        "The four correlations of the CHSH sum, each from ten thousand sampled "
        "pairs of its own, for the singlet and for the local model.",
    )
    experiment.table(
        "chsh",
        summary,
        [
            ("model", "", ""),
            ("|S| from the counts", "", ".4f"),
            ("standard error", "", ".4f"),
            ("|S| predicted", "", ".4f"),
            ("|S| - 2 in standard errors", "", "+.1f"),
            ("2 sqrt(2) - |S| in standard errors", "", "+.1f"),
        ],
        "The CHSH value S of each model from its four sampled correlations, "
        "its standard error, the value its correlations predict, and its "
        "distance from the local bound 2 and from Tsirelson's bound 2 sqrt(2) "
        "in standard errors.",
    )
    return tables, values


def family_run():
    """|S| along the family of settings (0, 2 theta, theta, 3 theta), from
    sampled counts, for the singlet and the local model."""
    rng = np.random.default_rng(SEED + 2)
    found = {"quantum": [], "local": []}
    for theta in np.radians(family_degrees):
        angles = family(theta)
        q = chsh_counts(quantum_counts, angles, pairs_per_family_setting, rng)
        c = chsh_counts(local_counts, angles, pairs_per_family_setting, rng)
        found["quantum"].append(chsh_value(q))
        found["local"].append(chsh_value(c))
    return np.array(found["quantum"]), np.array(found["local"])


def family_prediction(theta, correlate):
    """|S| of the family at each theta, from the predicted correlations."""
    return np.array(
        [
            abs(chsh(correlate(*np.transpose(setting_pairs(family(t))))))
            for t in np.atleast_1d(theta)
        ]
    )


def draw_family(quantum, local) -> Figure:
    """|S| against theta for both models, sampled and predicted, with the
    two bounds."""
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    fine = np.linspace(0, np.pi / 2, 181)
    ax.axhline(LOCAL_BOUND, color=FIGURE_COLOURS[2], linewidth=1)
    ax.axhline(TSIRELSON_BOUND, color=FIGURE_COLOURS[2], linewidth=1, linestyle="-.")
    for bound, name in (
        (LOCAL_BOUND, "local bound 2"),
        (TSIRELSON_BOUND, "Tsirelson's bound 2 sqrt(2)"),
    ):
        ax.text(89, bound + 0.04, name, fontsize="small", ha="right")
    ax.plot(
        np.degrees(fine),
        family_prediction(fine, quantum_correlation),
        color=FIGURE_COLOURS[0],
        linestyle="--",
        label="singlet, predicted",
    )
    ax.plot(
        np.degrees(fine),
        family_prediction(fine, local_correlation),
        color=FIGURE_COLOURS[1],
        linestyle=":",
        label="local model, predicted",
    )
    for values, marker, colour, label in (
        (quantum, "o", FIGURE_COLOURS[0], "singlet, sampled"),
        (local, "s", FIGURE_COLOURS[1], "local model, sampled"),
    ):
        ax.errorbar(
            family_degrees,
            np.abs(values[:, 0]),
            yerr=values[:, 1],
            fmt=marker,
            color=colour,
            markerfacecolor="none",
            capsize=3,
            label=label,
        )
    ax.set_ylim(0, 3.3)
    ax.set_xticks(np.arange(0, 91, 15))
    ax.set_xlabel("angle theta between neighbouring settings (degree)")
    ax.set_ylabel("|S| (dimensionless)")
    ax.legend(fontsize="small", loc="lower left")
    return fig


def visibility_threshold():
    """Exercise 1: S of the singlet mixed with white noise, at four
    visibilities, from the exact probabilities, against 2 sqrt(2) V."""
    visibilities = [0.6, 0.7, 0.8, 0.9]
    values = []
    for v in visibilities:
        tables = [joint_probabilities(werner(v), a, b) for a, b in setting_pairs()]
        values.append(abs(chsh([correlation(t) for t in tables])))
    return visibilities, values


def product_state():
    """Exercise 2: S at the standard settings of the unentangled pair with A
    up and B down along z, from the exact probabilities."""
    up_down = np.zeros(4, dtype=complex)
    up_down[1] = 1.0
    tables = [joint_probabilities(density(up_down), a, b) for a, b in setting_pairs()]
    return abs(chsh([correlation(t) for t in tables]))


def no_signalling(tables):
    """Exercise 3: A's fraction of +1 at setting a, with B at b and at b',
    from the counts of the CHSH run, and the standard error of each."""
    first, second = tables["singlet"][0], tables["singlet"][1]
    error = np.sqrt(0.25 / pairs_per_setting)
    return marginal(first), marginal(second), float(error)


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    delta, quantum, local = correlations_run(experiment)
    experiment.figure(
        "fig-correlations", partial(draw_correlations, delta, quantum, local)
    )

    tables, values = chsh_run(experiment)
    s_quantum, e_quantum = values["singlet"]
    s_local, e_local = values["local model"]
    experiment.number("s-quantum", abs(s_quantum), ".3f")
    experiment.number("e-quantum", e_quantum, ".3f")
    experiment.number("s-local", abs(s_local), ".3f")
    experiment.number("e-local", e_local, ".3f")
    experiment.number("sigmas", (abs(s_quantum) - LOCAL_BOUND) / e_quantum, ".0f")
    experiment.number("tsirelson", TSIRELSON_BOUND, ".4f")
    strategies = deterministic_strategies()
    largest = max(abs(s) for _, s in strategies)
    assert largest == LOCAL_BOUND
    experiment.number("strategies", len(strategies), "d")
    experiment.number("largest-strategy", largest, ".0f")

    quantum_family, local_family = family_run()
    experiment.figure("fig-chsh", partial(draw_family, quantum_family, local_family))
    theta = np.radians(family_degrees)
    for values, correlate in (
        (quantum_family, quantum_correlation),
        (local_family, local_correlation),
    ):
        gap = np.abs(np.abs(values[:, 0]) - family_prediction(theta, correlate))
        assert np.all(gap < 4 * values[:, 1] + 1e-12)

    crossing = brentq(
        lambda t: family_prediction(t, quantum_correlation)[0] - LOCAL_BOUND,
        np.pi / 4,
        np.pi / 2,
    )
    experiment.number("crossing", np.degrees(crossing), ".1f")

    visibilities, werner_values = visibility_threshold()
    for v, s in zip(visibilities, werner_values, strict=True):
        assert abs(s - TSIRELSON_BOUND * v) < 1e-12
        experiment.number(f"werner-{round(v * 10)}", s, ".3f")
    experiment.number("threshold", 1 / np.sqrt(2), ".3f")
    experiment.number("product", product_state(), ".3f")
    first, second, error = no_signalling(tables)
    experiment.number("marginal-b", first, ".4f")
    experiment.number("marginal-b2", second, ".4f")
    experiment.number("marginal-error", error, ".4f")
    experiment.number("marginal-b-sigmas", abs(first - 0.5) / error, ".1f")
    experiment.number("marginal-b2-sigmas", abs(second - 0.5) / error, ".1f")
    return experiment


if __name__ == "__main__":
    main(run)
