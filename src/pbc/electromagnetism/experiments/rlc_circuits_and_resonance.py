"""The experiment of the lesson "RLC circuits and resonance".

A series RLC circuit of ``pbc.electromagnetism.circuits``, simulated in time
and compared with its closed forms: the response to a step of the source in
the underdamped, critical, and overdamped regimes; the resonance curve of the
current, amplitude and phase, measured on steady states of the simulation
against the response V / |Z| of the impedance, with the peak at
1 / sqrt(LC) and the half-power width R / L; the peak of the capacitor
voltage below the resonance; and the energy lost per cycle against the
quality factor. Run it as a program to write the figures and numbers of the
page:

    uv run --locked --no-dev python -m \\
        pbc.electromagnetism.experiments.rlc_circuits_and_resonance out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from scipy.optimize import brentq, minimize_scalar

from pbc.authoring import FIGURE_COLOURS
from pbc.electromagnetism.circuits import (
    SeriesRLC,
    simulate,
    steady_phasor,
    step_response,
)
from pbc.experiment import Experiment, main

# region: circuit
INDUCTANCE = 10e-3  # H
CAPACITANCE = 100e-9  # F
SOURCE = 5.0  # V, the step, and the amplitude of the sinusoidal source
# endregion: circuit
# region: step
STEP_RESISTANCES = [100.0, None, 2000.0]  # ohm; None: the critical resistance
STEP_TIME = 1.5e-3  # s
# endregion: step
# region: sweep
RESISTANCE = 30.0  # ohm, for the resonance curve
SWEEP = np.linspace(0.5, 1.5, 21)  # omega / omega_0
DECAY_TIMES = 25.0  # the transient falls by e^-25 before the steady state is read
STEADY_PERIODS = 4  # periods over which the steady state is read
SAMPLES_PER_PERIOD = 64
# endregion: sweep


def below(value: float, bound: float) -> str:
    """A gap set by the integrator's tolerance is not shown as a number: only
    that it is smaller than ``bound``."""
    if abs(value) >= bound:
        raise ValueError(f"{value!r} is not below {bound!r}")
    return f"below {bound:.0e}"


def degrees(phasor: complex) -> float:
    """The phase of ``phasor`` in degrees; one that rounds to zero at three
    decimals is zero, so that its sign, set by round-off, is not shown."""
    phase = float(np.degrees(np.angle(phasor)))
    return 0.0 if abs(phase) < 5e-4 else phase


def circuit(resistance: float | None = None) -> SeriesRLC:
    """The circuit of the lesson with ``resistance`` (ohm); None gives the
    critical resistance."""
    base = SeriesRLC(1.0, INDUCTANCE, CAPACITANCE)
    if resistance is None:
        resistance = base.critical_resistance
    return SeriesRLC(resistance, INDUCTANCE, CAPACITANCE)


def step_responses(experiment: Experiment) -> dict:
    """The capacitor voltage after a step of the source, simulated and in
    closed form, in the three regimes; record the table and return the
    curves by regime."""
    t = np.linspace(0.0, STEP_TIME, 601)
    curves, rows, gaps = {}, [], []
    for resistance in STEP_RESISTANCES:
        rlc = circuit(resistance)
        charge, _ = simulate(rlc, lambda _t: SOURCE, t)
        simulated = charge / rlc.capacitance
        exact = step_response(rlc, SOURCE, t)
        curves[rlc.regime] = (t, simulated, exact)
        gaps.append(np.max(np.abs(simulated - exact)) / SOURCE)
        rows.append(
            (
                rlc.regime,
                rlc.resistance,
                rlc.damping_rate / rlc.natural_frequency,
                simulated.max() / SOURCE,
                below(gaps[-1], 1e-9),
            )
        )
    experiment.table(
        "step-response",
        rows,
        [
            ("regime", "", ""),
            ("R", "ohm", ".1f"),
            ("alpha / omega_0", "", ".3f"),
            ("largest capacitor voltage / step", "", ".4f"),
            ("largest gap, simulated to closed form, / step", "", ""),
        ],
        "The capacitor voltage after a step of the source from zero to five "
        "volts, simulated over 1.5 ms against the closed form of each regime.",
    )
    experiment.number("step-gap", below(max(gaps), 1e-9))
    experiment.number("overshoot", 100 * (rows[0][3] - 1.0), ".0f")
    return curves


def steady_state(rlc: SeriesRLC, omega: float) -> tuple[complex, complex]:
    """The complex amplitudes of the current (A) and of the capacitor voltage
    (V), read from a simulation driven by SOURCE cos(omega t) from rest, after
    DECAY_TIMES decay times rounded up to whole periods."""
    period = 2.0 * np.pi / omega
    settle = np.ceil(DECAY_TIMES / rlc.damping_rate / period) * period
    t = settle + np.linspace(
        0.0, STEADY_PERIODS * period, STEADY_PERIODS * SAMPLES_PER_PERIOD + 1
    )
    t = np.concatenate([[0.0], t])
    charge, current = simulate(rlc, lambda time: SOURCE * np.cos(omega * time), t)
    return (
        steady_phasor(current[1:], t[1:], omega),
        steady_phasor(charge[1:] / rlc.capacitance, t[1:], omega),
    )


def resonance_curve(experiment: Experiment):
    """The amplitude and phase of the current over the sweep, simulated and
    from the impedance; record the table and return the curve."""
    rlc = circuit(RESISTANCE)
    omegas = SWEEP * rlc.natural_frequency
    simulated = np.array([steady_state(rlc, omega)[0] for omega in omegas])
    exact = rlc.current_phasor(SOURCE, omegas)
    amplitude_gap = np.max(np.abs(np.abs(simulated) / np.abs(exact) - 1.0))
    phase_gap = np.max(np.abs(np.angle(simulated) - np.angle(exact)))
    rows = [
        (w, abs(s), abs(e), degrees(s), degrees(e))
        for w, s, e in zip(SWEEP[::5], simulated[::5], exact[::5], strict=True)
    ]
    experiment.table(
        "resonance-curve",
        rows,
        [
            ("omega / omega_0", "", ".2f"),
            ("current, simulated", "A", ".5f"),
            ("V / |Z|", "A", ".5f"),
            ("phase, simulated", "degrees", ".3f"),
            ("phase of V / Z", "degrees", ".3f"),
        ],
        "The amplitude and phase of the steady current at every fifth driving "
        "frequency of the sweep, read from the simulation, against the "
        "response of the impedance.",
    )
    experiment.number("amplitude-gap", below(amplitude_gap, 1e-9))
    experiment.number("phase-gap", below(np.degrees(phase_gap), 1e-6))
    experiment.number("quality-factor", rlc.quality_factor, ".2f")
    experiment.number("natural-frequency", rlc.natural_frequency / (2 * np.pi), ".1f")
    return rlc, omegas, simulated


def peak(amplitude, guess: float, width: float) -> float:
    """The angular frequency at which ``amplitude`` is largest, searched
    within ``width`` around ``guess``."""
    found = minimize_scalar(
        lambda omega: -amplitude(omega),
        bounds=(guess - width, guess + width),
        method="bounded",
        options={"xatol": 1e-7 * guess},
    )
    return float(found.x)


def resonance_measures(experiment: Experiment) -> tuple[float, float]:
    """The peak of the current, its half-power frequencies, and the peak of
    the capacitor voltage, each found on the simulated steady states; record
    the table and return the half-power frequencies."""
    rlc = circuit(RESISTANCE)
    w0, width = rlc.natural_frequency, rlc.resistance / rlc.inductance

    def current(omega: float) -> float:
        return abs(steady_state(rlc, omega)[0])

    def capacitor(omega: float) -> float:
        return abs(steady_state(rlc, omega)[1])

    top = peak(current, w0, 0.2 * width)
    half = current(top) / np.sqrt(2.0)
    low = brentq(lambda w: current(w) - half, top - width, top, xtol=1e-8 * w0)
    high = brentq(lambda w: current(w) - half, top, top + width, xtol=1e-8 * w0)
    q = rlc.quality_factor
    v_peak = w0 * np.sqrt(1.0 - 1.0 / (2.0 * q**2))
    capacitor_top = peak(capacitor, v_peak, 0.2 * width)
    rows = [
        ("peak of the current", top / w0, 1.0),
        ("half-power width", (high - low) / w0, width / w0),
        ("product of the half-power frequencies", low * high / w0**2, 1.0),
        ("peak of the capacitor voltage", capacitor_top / w0, v_peak / w0),
    ]
    experiment.table(
        "resonance-measures",
        rows,
        [
            ("quantity, / omega_0 (squared for the product)", "", ""),
            ("simulated", "", ".6f"),
            ("closed form", "", ".6f"),
        ],
        "The resonance of the circuit read from the simulated steady states by "
        "a search for the peak and for the half-power points, against the "
        "closed forms: omega_0, R / L, omega_0 squared, and "
        "omega_0 sqrt(1 - 1 / (2 Q^2)).",
    )
    experiment.number(
        "measures-gap", below(max(abs(row[1] - row[2]) for row in rows), 1e-6)
    )
    return low, high


def energy_per_cycle(experiment: Experiment) -> None:
    """At resonance: the energy stored, the energy the resistor takes per
    cycle from the simulated current, and 2 pi times their ratio against Q;
    record the table."""
    rlc = circuit(RESISTANCE)
    w0 = rlc.natural_frequency
    period = 2.0 * np.pi / w0
    settle = np.ceil(DECAY_TIMES / rlc.damping_rate / period) * period
    t = np.concatenate([[0.0], settle + np.linspace(0.0, period, 2049)])
    charge, current = simulate(rlc, lambda time: SOURCE * np.cos(w0 * time), t)
    q, i = charge[1:], current[1:]
    stored = 0.5 * rlc.inductance * i**2 + 0.5 * q**2 / rlc.capacitance
    power = rlc.resistance * i**2
    lost = period * power[:-1].mean()  # trapezoidal rule over one period
    experiment.table(
        "energy-per-cycle",
        [
            (
                1e6 * stored.mean(),
                below(np.ptp(stored) / stored.mean(), 1e-8),
                1e6 * lost,
                2 * np.pi * stored.mean() / lost,
                rlc.quality_factor,
            )
        ],
        [
            ("energy stored", "uJ", ".4f"),
            ("its relative change over the cycle", "", ""),
            ("energy lost per cycle", "uJ", ".4f"),
            ("2 pi stored / lost", "", ".4f"),
            ("Q", "", ".4f"),
        ],
        "At resonance, over one period of the simulated steady state: the "
        "energy in the inductor and the capacitor, and the energy the "
        "resistor turns into heat.",
    )


def tuning(experiment: Experiment) -> None:
    """Exercise 1: the capacitance that tunes a 250 uH coil with 12 ohm of
    resistance to 1 MHz, the bandwidth and Q that follow, and the current of
    a station 9 kHz away relative to the tuned one; record the table."""
    inductance, resistance, f0, spacing = 250e-6, 12.0, 1e6, 9e3
    capacitance = 1.0 / ((2 * np.pi * f0) ** 2 * inductance)
    rlc = SeriesRLC(resistance, inductance, capacitance)
    neighbour = abs(rlc.impedance(2 * np.pi * f0)) / abs(
        rlc.impedance(2 * np.pi * (f0 + spacing))
    )
    experiment.table(
        "tuning",
        [
            (
                1e12 * capacitance,
                rlc.quality_factor,
                1e-3 * resistance / inductance / (2 * np.pi),
                neighbour,
            )
        ],
        [
            ("C", "pF", ".1f"),
            ("Q", "", ".1f"),
            ("half-power bandwidth", "kHz", ".2f"),
            ("current 9 kHz away / tuned current", "", ".2f"),
        ],
        "A coil of 250 uH and 12 ohm tuned to 1 MHz: the capacitance, the "
        "quality factor, the bandwidth R / (2 pi L), and the current of a "
        "station 9 kHz away for the same signal voltage, relative to the "
        "tuned station's.",
    )


def draw_step_response(curves: dict) -> Figure:
    """The capacitor voltage after the step, simulated (markers) on the
    closed form (lines), in the three regimes."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    for (regime, (t, simulated, exact)), line, marker, colour in zip(
        curves.items(),
        ("-", "--", "-."),
        ("o", "s", "^"),
        (FIGURE_COLOURS[0], FIGURE_COLOURS[1], FIGURE_COLOURS[4]),
        strict=True,
    ):
        ax.plot(1e3 * t, exact / SOURCE, color=colour, linestyle=line, label=regime)
        ax.plot(
            1e3 * t[::30],
            simulated[::30] / SOURCE,
            color=colour,
            marker=marker,
            linestyle="none",
            markersize=4,
        )
    ax.axhline(1.0, color=FIGURE_COLOURS[2], linewidth=0.8, linestyle=":")
    ax.set_xlabel("time (ms)")
    ax.set_ylabel("capacitor voltage / step (dimensionless)")
    ax.legend(frameon=False, loc="lower right", title="closed form; markers simulated")
    fig.tight_layout()
    return fig


def draw_resonance(rlc: SeriesRLC, omegas, simulated, band) -> Figure:
    """Amplitude and phase of the current against omega / omega_0:
    simulated markers on the impedance's curve, the half-power band shaded."""
    w0 = rlc.natural_frequency
    fine = np.linspace(omegas[0], omegas[-1], 600)
    exact = rlc.current_phasor(SOURCE, fine)
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(6.4, 5.0), sharex=True)
    for ax in (top, bottom):
        ax.axvspan(band[0] / w0, band[1] / w0, color=FIGURE_COLOURS[2], alpha=0.15)
    top.plot(fine / w0, 1e3 * np.abs(exact), color=FIGURE_COLOURS[0], label="V / |Z|")
    top.plot(
        omegas / w0,
        1e3 * np.abs(simulated),
        color=FIGURE_COLOURS[1],
        marker="o",
        linestyle="none",
        label="simulated",
    )
    top.set_ylabel("current amplitude (mA)")
    top.legend(frameon=False, loc="upper left")
    top.text(band[1] / w0 + 0.01, 0.9e3 * np.abs(exact).max(), "half-power width")
    bottom.plot(fine / w0, np.degrees(np.angle(exact)), color=FIGURE_COLOURS[0])
    bottom.plot(
        omegas / w0,
        np.degrees(np.angle(simulated)),
        color=FIGURE_COLOURS[1],
        marker="o",
        linestyle="none",
    )
    bottom.axhline(0.0, color=FIGURE_COLOURS[2], linewidth=0.8, linestyle=":")
    bottom.set_ylabel("phase of the current (degrees)")
    bottom.set_xlabel(r"driving frequency $\omega/\omega_0$")
    fig.tight_layout()
    return fig


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    curves = step_responses(experiment)
    experiment.figure("fig-step-response", partial(draw_step_response, curves))
    rlc, omegas, simulated = resonance_curve(experiment)
    band = resonance_measures(experiment)
    experiment.figure(
        "fig-rlc-resonance", partial(draw_resonance, rlc, omegas, simulated, band)
    )
    energy_per_cycle(experiment)
    experiment.number(
        "capacitor-at-resonance",
        abs(rlc.capacitor_phasor(SOURCE, rlc.natural_frequency)),
        ".1f",
    )
    tuning(experiment)
    return experiment


if __name__ == "__main__":
    main(run)
