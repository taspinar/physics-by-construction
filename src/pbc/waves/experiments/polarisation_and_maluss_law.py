"""The experiment of the lesson "Polarisation and Malus's law".

The intensity behind an analyser measured as the time average of the real
field, against Malus's law for an ideal and for a leaky polariser;
unpolarised light as an ensemble of random states; a chain of polarisers;
the Stokes parameters from six analysers; and a quarter-wave plate used away
from its design wavelength (``pbc.waves.polarisation``). Run it as a program
to write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.waves.experiments.polarisation_and_maluss_law out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.waves.polarisation import (
    chain_transmission,
    circular,
    degree_of_polarisation,
    intensity,
    linear,
    malus,
    polariser,
    retarder,
    stokes_closed,
    stokes_measured,
    unpolarised,
)

# region: setup
angles = np.radians(np.arange(0.0, 181.0, 15.0))  # analyser against the light
LEAK = 1e-3  # power let through across the axis: an extinction ratio of 1000
ENSEMBLE = 40_000  # random states that model unpolarised light
SEED = 283
# endregion: setup
# region: wave-plate
DESIGN = 633e-9  # m, the wavelength the quarter-wave plate is made for
ORDER = 5  # the multi-order plate delays by ORDER whole waves more
wavelengths = np.linspace(450e-9, 750e-9, 13)  # m
# endregion: wave-plate


def below(value: float, bound: float = 1e-12) -> str:
    """A value, or the bound when it is smaller: a difference at the level
    of round-off is not shown as a number."""
    return f"below {bound:.0e}" if abs(value) < bound else f"{value:.1e}"


def shown(value: float, spec: str) -> str:
    """A value at the precision ``spec``, or "below 1e-12" when it is at
    round-off; never a negative zero."""
    if abs(value) < 1e-12:
        return "below 1e-12"
    return format(float(np.round(value, 12)) + 0.0, spec)


def transmitted(angle: float, leak: float = 0.0) -> float:
    """The intensity behind an analyser at ``angle`` to light polarised
    along x, from the sampled real field."""
    return float(intensity(polariser(angle, leak) @ linear(0.0)))


def malus_run(experiment: Experiment):
    """The transmitted intensity at thirteen angles, ideal and leaky,
    against the closed forms; record the table and return the largest
    difference."""
    rows, worst = [], 0.0
    for a in angles:
        ideal, leaky = transmitted(a), transmitted(a, LEAK)
        worst = max(worst, abs(ideal - malus(a)), abs(leaky - malus(a, LEAK)))
        rows.append(
            (np.degrees(a), ideal, float(malus(a)), leaky, float(malus(a, LEAK)))
        )
    assert worst < 1e-12, "the measured intensity departs from Malus's law"
    experiment.table(
        "malus-run",
        rows,
        [
            ("analyser angle", "deg", ".0f"),
            ("ideal, from the field", "", ".6f"),
            ("cos^2", "", ".6f"),
            ("leaky, from the field", "", ".6f"),
            ("cos^2 + leak sin^2", "", ".6f"),
        ],
        "The intensity behind an analyser, in units of the incident intensity, "
        "measured as the time average of the sampled field, for an ideal "
        "analyser and for one that lets through the stated fraction across its "
        "axis, against the closed forms, to six decimals.",
    )
    return worst


def draw_malus() -> Figure:
    """The transmitted intensity against the analyser angle, on a linear and
    on a logarithmic scale."""
    fine = np.radians(np.linspace(0.0, 180.0, 721))
    fig, (left, right) = plt.subplots(1, 2, figsize=(7.2, 3.4))
    for ax in (left, right):
        ax.plot(
            np.degrees(fine), malus(fine), color=FIGURE_COLOURS[0], label="cos^2, ideal"
        )
        ax.plot(
            np.degrees(fine),
            malus(fine, LEAK),
            color=FIGURE_COLOURS[1],
            linestyle="--",
            label="cos^2 + leak sin^2",
        )
        ax.plot(
            np.degrees(angles),
            [transmitted(a) for a in angles],
            "o",
            color=FIGURE_COLOURS[0],
            label="ideal, from the field",
        )
        ax.plot(
            np.degrees(angles),
            [transmitted(a, LEAK) for a in angles],
            "s",
            markerfacecolor="none",
            color=FIGURE_COLOURS[1],
            label="leaky, from the field",
        )
        ax.set_xlabel("analyser angle (degrees)")
        ax.set_xticks([0, 45, 90, 135, 180])
    left.set_ylabel("transmitted intensity (of the incident)")
    right.set_yscale("log")
    right.set_ylim(1e-5, 2.0)
    right.set_title("logarithmic scale", fontsize="medium")
    left.legend(fontsize=7, loc="upper center")
    fig.tight_layout()
    return fig


def unpolarised_run(experiment: Experiment):
    """An ensemble of random states through one polariser, through three
    at 0, 45, and 90 degrees, and through two crossed ones, and its Stokes
    parameters; record the table and return the values for the page."""
    rng = np.random.default_rng(SEED)
    states = unpolarised(ENSEMBLE, rng)
    setups = {
        "one polariser": ([0.0], 0.5),
        "polarisers at 0, 45, 90 degrees": ([0.0, np.pi / 4, np.pi / 2], 0.125),
        "crossed polarisers at 0, 90 degrees": ([0.0, np.pi / 2], 0.0),
    }
    rows, worst = [], 0.0
    for name, (directions, expected) in setups.items():
        beam = states
        for d in directions:
            beam = beam @ polariser(d).T
        values = intensity(beam)
        mean = float(np.mean(values))
        error = float(np.std(values, ddof=1) / np.sqrt(values.size))
        if error > 1e-12:
            worst = max(worst, abs(mean - expected) / error)
        else:  # every state is blocked: no spread to compare with
            assert abs(mean - expected) < 1e-12
        rows.append((name, shown(mean, ".4f"), shown(error, ".4f"), expected))
    assert worst < 4.0, "the ensemble mean is more than four standard errors off"
    stokes = stokes_measured(states)
    degree = degree_of_polarisation(stokes)
    assert degree < 5.0 / np.sqrt(ENSEMBLE)
    experiment.table(
        "unpolarised-run",
        rows,
        [
            ("setup", "", ""),
            ("mean transmitted intensity", "", ""),
            ("standard error", "", ""),
            ("closed form", "", ".3f"),
        ],
        "Unpolarised light, modelled as an ensemble of random polarisation "
        "states, through three arrangements of ideal polarisers: the mean "
        "intensity of the ensemble in units of the incident one, its standard "
        "error, and the closed form.",
    )
    return worst, degree


def chain_run(experiment: Experiment):
    """N polarisers that turn the polarisation by a right angle in equal
    steps, from N = 1 to 60, against cos^(2N)(pi / 2N); record the table
    and return the counts and the transmissions."""
    counts = np.arange(1, 61)
    computed = []
    for n in counts:
        beam = linear(0.0)
        for k in range(1, n + 1):
            beam = polariser(k * np.pi / (2 * n)) @ beam
        computed.append(float(intensity(beam)))
    computed = np.array(computed)
    closed = np.array([chain_transmission(n) for n in counts])
    worst = float(np.max(np.abs(computed - closed)))
    assert worst < 1e-12
    listed = [1, 2, 3, 5, 10, 20, 60]
    experiment.table(
        "chain-run",
        [(n, shown(computed[n - 1], ".6f"), closed[n - 1]) for n in listed],
        [
            ("polarisers", "", "d"),
            ("transmitted, from the field", "", ""),
            ("cos^(2N)(pi / 2N)", "", ".6f"),
        ],
        "The intensity that passes N ideal polarisers, each turned by a right "
        "angle over N from the one before, behind light polarised along the "
        "first, in units of the incident intensity, to six decimals.",
    )
    return counts, computed, worst


def draw_polariser_chain(counts, computed) -> Figure:
    """The transmission of a chain of polarisers against their number."""
    fine = np.arange(1, 61)
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ax.plot(
        fine,
        [chain_transmission(n) for n in fine],
        color=FIGURE_COLOURS[0],
        label="cos^(2N)(pi / 2N)",
    )
    ax.plot(
        counts,
        computed,
        "o",
        markersize=3,
        color=FIGURE_COLOURS[1],
        label="from the field",
    )
    ax.plot(
        fine[1:],
        1 - np.pi**2 / (4 * fine[1:]),
        color=FIGURE_COLOURS[2],
        linestyle=":",
        label="1 - pi^2 / (4N), large N",
    )
    ax.set_xscale("log")
    ax.set_xticks([1, 2, 5, 10, 20, 50], labels=["1", "2", "5", "10", "20", "50"])
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlabel("number of polarisers N")
    ax.set_ylabel("transmitted intensity (of the incident)")
    ax.legend(fontsize=7, loc="lower right")
    return fig


def stokes_run(experiment: Experiment):
    """The Stokes parameters of five states from six analyser intensities
    against their closed forms; record the table and return the largest
    difference."""
    states = {
        "linear along x": linear(0.0),
        "linear at 30 degrees": linear(np.radians(30.0)),
        "circular, x towards y": circular(1),
        "circular, y towards x": circular(-1),
        "elliptical": retarder(0.0, np.pi / 4) @ linear(np.radians(30.0)),
    }
    rows, worst = [], 0.0
    for name, state in states.items():
        measured = stokes_measured(state)
        worst = max(worst, float(np.max(np.abs(measured - stokes_closed(state)))))
        rows.append(
            (
                name,
                *(float(np.round(v, 12)) + 0.0 for v in measured),
                degree_of_polarisation(measured),
            )
        )
    assert worst < 1e-12
    experiment.table(
        "stokes-run",
        rows,
        [
            ("state", "", ""),
            ("S0", "", ".3f"),
            ("S1", "", ".3f"),
            ("S2", "", ".3f"),
            ("S3", "", ".3f"),
            ("degree of polarisation", "", ".3f"),
        ],
        "The Stokes parameters of five states of unit intensity, measured "
        "from the intensities behind six analysers, to three decimals.",
    )
    return worst


def circular_degree(retardance: float) -> float:
    """S3 / S0 behind a wave plate at 0 degrees for light polarised at 45
    degrees, from the six analysers."""
    s = stokes_measured(retarder(0.0, retardance) @ linear(np.pi / 4))
    return float(s[3] / s[0])


def wave_plate_run(experiment: Experiment):
    """A zero-order and a multi-order quarter-wave plate used at other
    wavelengths: the measured degree of circular polarisation against
    sin(Gamma); record the table and return the values for the figure."""
    zero = (np.pi / 2) * DESIGN / wavelengths
    multi = (2 * np.pi * ORDER + np.pi / 2) * DESIGN / wavelengths
    measured_zero = np.array([circular_degree(g) for g in zero])
    measured_multi = np.array([circular_degree(g) for g in multi])
    worst = float(
        max(
            np.max(np.abs(measured_zero - np.sin(zero))),
            np.max(np.abs(measured_multi - np.sin(multi))),
        )
    )
    assert worst < 1e-12
    experiment.table(
        "wave-plate-run",
        list(
            zip(
                wavelengths * 1e9,
                measured_zero,
                np.sin(zero),
                measured_multi,
                np.sin(multi),
                strict=True,
            )
        ),
        [
            ("wavelength", "nm", ".0f"),
            ("zero-order plate, measured", "", ".4f"),
            ("sin of its retardance", "", ".4f"),
            ("multi-order plate, measured", "", ".4f"),
            ("sin of its retardance", "", ".4f"),
        ],
        "The degree of circular polarisation S3 / S0 behind a quarter-wave plate "
        "made for the design wavelength, for light polarised at 45 degrees to its "
        "axis, measured from six analysers and against the sine of the "
        "retardance at each wavelength, to four decimals.",
    )
    return measured_zero, measured_multi, worst


def draw_wave_plate() -> Figure:
    """The degree of circular polarisation against the wavelength, for a
    zero-order and a multi-order quarter-wave plate."""
    fine = np.linspace(450e-9, 750e-9, 301)
    zero = (np.pi / 2) * DESIGN / fine
    multi = (2 * np.pi * ORDER + np.pi / 2) * DESIGN / fine
    fig, ax = plt.subplots(figsize=(7.6, 3.4))
    ax.plot(fine * 1e9, np.sin(zero), color=FIGURE_COLOURS[0], label="zero-order plate")
    ax.plot(
        fine * 1e9,
        np.sin(multi),
        color=FIGURE_COLOURS[1],
        linestyle="--",
        label="multi-order plate",
    )
    ax.plot(
        wavelengths * 1e9,
        [circular_degree(g) for g in (np.pi / 2) * DESIGN / wavelengths],
        "o",
        color=FIGURE_COLOURS[0],
        label="zero-order, measured",
    )
    ax.plot(
        wavelengths * 1e9,
        [
            circular_degree(g)
            for g in (2 * np.pi * ORDER + np.pi / 2) * DESIGN / wavelengths
        ],
        "s",
        markerfacecolor="none",
        color=FIGURE_COLOURS[1],
        label="multi-order, measured",
    )
    ax.axvline(
        DESIGN * 1e9, color=FIGURE_COLOURS[2], linestyle=":", label="design wavelength"
    )
    ax.set_xlabel("wavelength (nm)")
    ax.set_ylabel("degree of circular polarisation")
    ax.legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.02, 1.0))
    fig.tight_layout()
    return fig


def crossing_width():
    """Exercise 1: the angle from the crossed position at which a leaky
    analyser lets through twice its floor."""
    return np.degrees(np.arcsin(np.sqrt(LEAK / (1 - LEAK))))


def steepest():
    """Exercise 2: the analyser angle at which the transmitted intensity
    changes fastest, and the change per degree there."""
    fine = np.radians(np.linspace(0.0, 90.0, 9001))
    slope = np.abs(np.gradient(malus(fine), fine))
    i = int(np.argmax(slope))
    return np.degrees(fine[i]), slope[i] * np.pi / 180


def half_wave():
    """Exercise 3: a half-wave plate at 22.5 degrees turns light polarised
    along x; the direction of the light behind it."""
    out = retarder(np.radians(22.5), np.pi) @ linear(0.0)
    s = stokes_closed(out)
    return np.degrees(0.5 * np.arctan2(s[2], s[1])), degree_of_polarisation(s)


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.number("malus-gap", below(malus_run(experiment)), "")
    experiment.figure("fig-malus", draw_malus)
    experiment.number("leak", LEAK, ".0e")
    experiment.number("extinction", 1 / LEAK, ".0f")

    worst, degree = unpolarised_run(experiment)
    experiment.number("ensemble", ENSEMBLE, "d")
    experiment.number("ensemble-sigmas", worst, ".1f")
    experiment.number("ensemble-degree", degree, ".3f")
    experiment.number("ensemble-scale", 1 / np.sqrt(ENSEMBLE), ".3f")

    counts, computed, chain_gap = chain_run(experiment)
    experiment.figure(
        "fig-polariser-chain", partial(draw_polariser_chain, counts, computed)
    )
    experiment.number("chain-gap", below(chain_gap), "")
    experiment.number("chain-two", chain_transmission(2), ".2f")
    experiment.number("chain-sixty", chain_transmission(60), ".3f")

    experiment.number("stokes-gap", below(stokes_run(experiment)), "")
    zero, multi, plate_gap = wave_plate_run(experiment)
    experiment.figure("fig-wave-plate", draw_wave_plate)
    experiment.number("plate-gap", below(plate_gap), "")
    experiment.number("zero-worst", float(np.min(zero)), ".3f")
    experiment.number("multi-worst", float(np.min(multi)), ".2f")
    experiment.number("design-nm", DESIGN * 1e9, ".0f")

    experiment.number("crossing-width", crossing_width(), ".1f")
    angle, per_degree = steepest()
    experiment.number("steepest", angle, ".0f")
    experiment.number("per-degree", per_degree * 100, ".2f")
    direction, purity = half_wave()
    experiment.number("half-wave-direction", direction, ".1f")
    experiment.number("half-wave-degree", purity, ".3f")
    return experiment


if __name__ == "__main__":
    main(run)
