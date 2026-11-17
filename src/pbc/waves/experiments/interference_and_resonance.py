"""The experiment of the lesson "Interference and resonance".

Superposition on a string (``pbc.waves.wave``), its modes and their
frequencies, resonance under a drive, the dispersion of the grid, a wave
packet, and the interference of two sources (``pbc.waves.modes``). Run it as
a program to write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.waves.experiments.interference_and_resonance out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.figure_language import LINE, figsize, figure_style, finish
from pbc.waves.modes import (
    centroid,
    measured_frequency,
    spectrum_peaks,
    string_frequency,
    triangle,
    triangle_mode_amplitude,
    two_source_amplitude,
    two_source_pattern,
    wave_packet,
)
from pbc.waves.wave import (
    driven_mode_amplitude,
    error_norm,
    grid,
    numerical_angular_frequency,
    numerical_group_velocity,
    solve,
)

# region: setup
LENGTH = 1.0  # string length, m
SPEED = 100.0  # wave speed, m/s
# endregion: setup
# region: linearity
LINEARITY_BOUND = 1e-12
# endregion: linearity
# region: mode-tolerance
MODE_TOLERANCE = 2e-3  # a chosen tolerance on the relative difference
# endregion: mode-tolerance
# region: sources
wavelength = 1.0
separation = 5.0 * wavelength
distance = 20000.0 * wavelength
PATTERN_TOLERANCE = 5e-3  # in units of the intensity of one source
# endregion: sources


def superposition():
    """Two pulses of opposite sign on 400 cells, run together and apart; the
    largest difference between the run of the sum and the sum of the runs."""
    cells = 400
    dx = LENGTH / cells
    dt = 0.5 * dx / SPEED
    x = grid(LENGTH, cells)

    def pulse(centre, sign):
        return sign * np.exp(-(((x - centre) / 0.04) ** 2))

    up = pulse(0.2, +1.0)
    down = pulse(0.8, -1.0)
    steps = round(0.0045 / dt)
    kwargs = dict(c=SPEED, dx=dx, dt=dt, n_steps=steps, every=1)
    both = solve(up + down, np.zeros_like(x), **kwargs)
    only_up = solve(up, np.zeros_like(x), **kwargs)
    only_down = solve(down, np.zeros_like(x), **kwargs)
    linearity_gap = error_norm(both.u, only_up.u + only_down.u)
    assert linearity_gap < LINEARITY_BOUND, (
        "the sum of two solutions is not the solution of the sum"
    )
    return x, both


def draw_superposition(x, both) -> Figure:
    """The two pulses at four times, shifted for each time."""
    times = [0.0, 0.0025, 0.004, 0.0045]
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for row, t in enumerate(times):
        j = int(np.argmin(np.abs(both.t - t)))
        ax.plot(x, both.u[j] - 2.4 * row, color="#00429d")
        ax.text(1.02, -2.4 * row, f"{both.t[j] * 1000:.1f} ms", va="center")
    ax.set_xlabel("position (m)")
    ax.set_ylabel("displacement, shifted for each time")
    ax.set_yticks([])
    ax.set_xlim(0, 1.15)
    return fig


def modes_run(experiment: Experiment):
    """A string plucked at a third, and the four strongest peaks of the
    spectrum at one point against the mode frequencies; record the table."""
    n_cells = 200
    dx = LENGTH / n_cells
    dt = 0.5 * dx / SPEED
    xs = grid(LENGTH, n_cells)
    steps = round(0.4 / dt)
    pluck = solve(
        triangle(xs, length=LENGTH, at=LENGTH / 3),
        np.zeros_like(xs),
        c=SPEED,
        dx=dx,
        dt=dt,
        n_steps=steps,
    )
    probe = round(0.45 * n_cells)
    record = pluck.u[:, probe]
    found = spectrum_peaks(record, dt, count=4)
    present = [1, 2, 4, 5]  # the third mode has a node at the pluck
    analytic = np.array([string_frequency(n, length=LENGTH, c=SPEED) for n in present])
    scheme = np.array(
        [
            numerical_angular_frequency(n * np.pi / LENGTH, c=SPEED, dx=dx, dt=dt)
            / (2 * np.pi)
            for n in present
        ]
    )
    deviation = np.abs(found - analytic) / analytic
    assert np.all(deviation < MODE_TOLERANCE), "a mode is not where the formula puts it"
    assert np.all(np.abs(found - scheme) / scheme < 1e-4), (
        "a peak is off the grid's own frequency"
    )
    assert abs(triangle_mode_amplitude(3, length=LENGTH, at=LENGTH / 3)) < 1e-12

    experiment.table(
        "modes-run",
        [
            (n, a, f, d * 100)
            for n, a, f, d in zip(present, analytic, found, deviation, strict=True)
        ],
        [
            ("mode", "", "d"),
            ("analytic n c / 2L", "Hz", ".2f"),
            ("simulated", "Hz", ".2f"),
            ("difference", "%", ".3f"),
        ],
        "The frequencies of the four strongest peaks of the spectrum of a plucked "
        "string, against the analytic mode frequencies, to two decimals.",
    )
    return record, dt, analytic, scheme, deviation


def draw_modes_spectrum(record, dt) -> Figure:
    """The spectrum of the plucked string with the mode frequencies."""
    size = 8 * record.size
    spectrum = np.abs(
        np.fft.rfft((record - record.mean()) * np.hanning(record.size), size)
    )
    frequency = np.arange(spectrum.size) / (size * dt)
    band = frequency < 320.0
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line"))
        ax.plot(frequency[band], spectrum[band], color=FIGURE_COLOURS[0])
        for n in range(1, 7):
            ax.axvline(
                string_frequency(n, length=LENGTH, c=SPEED),
                color=FIGURE_COLOURS[1],
                linestyle="--",
                linewidth=LINE["axis"],
            )
        ax.set_xlabel("frequency (Hz)")
        ax.set_ylabel("spectrum magnitude\n(arbitrary units)")
    return finish(fig)


def resonance_run(experiment: Experiment):
    """The first mode driven at its frequency and at seven tenths of it,
    against the exact amplitude; record the table."""
    n_cells = 100
    dx = LENGTH / n_cells
    dt = 0.5 * dx / SPEED
    xs = grid(LENGTH, n_cells)
    shape = np.sin(np.pi * xs / LENGTH)
    omega1 = np.pi * SPEED / LENGTH
    steps = round(0.2 / dt)

    def driven(drive):
        result = solve(
            np.zeros_like(xs),
            np.zeros_like(xs),
            c=SPEED,
            dx=dx,
            dt=dt,
            n_steps=steps,
            forcing=lambda t: shape * np.cos(drive * t),
        )
        amplitude = result.u @ shape / (shape @ shape)
        exact = driven_mode_amplitude(
            result.t, length=LENGTH, n=1, c=SPEED, drive=drive
        )
        return result.t, amplitude, exact

    t_on, amp_on, exact_on = driven(omega1)
    t_off, amp_off, exact_off = driven(0.7 * omega1)
    gap_on = np.max(np.abs(amp_on - exact_on)) / np.max(np.abs(exact_on))
    gap_off = np.max(np.abs(amp_off - exact_off)) / np.max(np.abs(exact_off))
    assert gap_on < 0.02 and gap_off < 0.02
    growth = np.max(np.abs(amp_on[-steps // 5 :])) / np.max(
        np.abs(amp_on[: steps // 5])
    )

    experiment.table(
        "resonance-run",
        [
            ("at the mode frequency", np.max(np.abs(amp_on)), gap_on * 100),
            ("at seven tenths of it", np.max(np.abs(amp_off)), gap_off * 100),
        ],
        [
            ("drive", "", ""),
            ("largest amplitude of the mode in the run", "", ".2e"),
            ("largest gap from the exact amplitude", "% of its largest value", ".2f"),
        ],
        "The largest amplitude of the first mode in a run of ten periods, and how "
        "far the simulation is from the exact formula, for the two drives.",
    )
    return (t_on, amp_on, exact_on), (t_off, amp_off, exact_off), growth


def draw_resonance(on, off) -> Figure:
    """The amplitude of the first mode under the two drives, simulated and
    exact."""
    t_on, amp_on, exact_on = on
    t_off, amp_off, exact_off = off
    on_colour, off_colour = FIGURE_COLOURS[:2]
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line"))
        ax.plot(t_on * 1000, amp_on, color=on_colour, label="at the mode frequency")
        ax.plot(
            t_on * 1000,
            exact_on,
            color=on_colour,
            linestyle="--",
            linewidth=LINE["model"],
        )
        ax.plot(t_off * 1000, amp_off, color=off_colour, label="at seven tenths of it")
        ax.plot(
            t_off * 1000,
            exact_off,
            color=off_colour,
            linestyle="--",
            linewidth=LINE["model"],
        )
        ax.set_xlabel("time (ms)")
        ax.set_ylabel("amplitude of the first mode\n(arbitrary units)")
        # The legend would cover the curves: under the plot, in one column.
        fig.legend(loc="outside lower center", ncols=1)
    return finish(fig)


# region: dispersion
dispersion_cells = 100
mode_numbers = [1, 5, 10, 20, 40, 60, 80]
# endregion: dispersion


def dispersion_run(experiment: Experiment):
    """The frequency of seven standing modes of the grid: analytic, from the
    dispersion relation of the scheme, and measured; record the table."""
    dx = LENGTH / dispersion_cells
    dt = 0.5 * dx / SPEED
    xs = grid(LENGTH, dispersion_cells)
    steps = round(0.3 / dt)
    rows = []
    for n in mode_numbers:
        result = solve(
            np.sin(n * np.pi * xs / LENGTH),
            np.zeros_like(xs),
            c=SPEED,
            dx=dx,
            dt=dt,
            n_steps=steps,
        )
        antinode = max(1, round(dispersion_cells / (2 * n)))
        measured = measured_frequency(result.u[:, antinode], result.t)
        k = n * np.pi / LENGTH
        formula = numerical_angular_frequency(k, c=SPEED, dx=dx, dt=dt) / (2 * np.pi)
        exact_f = SPEED * k / (2 * np.pi)
        rows.append((n, k * dx / np.pi, exact_f, formula, measured, measured / exact_f))
    agreement = max(abs(row[4] / row[3] - 1.0) for row in rows)
    assert agreement < 1e-3, "the measured frequency is not the one of the scheme"

    experiment.table(
        "dispersion-run",
        rows,
        [
            ("mode", "", "d"),
            ("wavenumber over the largest the grid holds", "", ".2f"),
            ("analytic", "Hz", ".1f"),
            ("formula of the grid", "Hz", ".1f"),
            ("measured", "Hz", ".1f"),
            ("measured over analytic", "", ".3f"),
        ],
        "The frequency of seven standing modes of the grid: analytic, from the "
        "dispersion relation of the scheme, and read from the zero crossings of a "
        "run, with the ratio of the measured to the analytic value.",
    )
    return rows, agreement


def packet_run():
    """A packet of short waves on the grid: the speed of its centre, the
    time it ran, and the group velocity of the grid."""
    n_cells = 400
    dx = LENGTH / n_cells
    dt = 0.5 * dx / SPEED
    xs = grid(LENGTH, n_cells)
    carrier = 1.2 / dx
    packet = wave_packet(xs, centre=0.25, width=0.05, k=carrier)
    steps = round(0.0025 / dt)
    packet_run = solve(
        packet, np.zeros_like(xs), c=SPEED, dx=dx, dt=dt, n_steps=steps, every=steps
    )
    right_half = packet_run.u[-1] * (xs > 0.3)
    packet_speed = (centroid(xs, right_half) - 0.25) / packet_run.t[-1]
    group = float(numerical_group_velocity(carrier, c=SPEED, dx=dx, dt=dt))
    assert abs(packet_speed / group - 1.0) < 0.02
    return packet_speed, packet_run.t[-1], group


def interference_run():
    """The intensity of two sources far away, added as waves and from the
    formula."""
    angle = np.linspace(-0.2, 0.2, 801)
    summed = two_source_amplitude(
        angle, separation=separation, wavelength=wavelength, distance=distance
    )
    intensity = (summed * distance) ** 2  # one source gives 1 at this distance
    formula = two_source_pattern(angle, separation=separation, wavelength=wavelength)
    pattern_gap = np.max(np.abs(intensity - formula))
    assert pattern_gap < PATTERN_TOLERANCE
    bright = np.arcsin(np.arange(-1, 2) * wavelength / separation)
    bright_values = two_source_pattern(
        bright, separation=separation, wavelength=wavelength
    )
    return angle, intensity, formula, pattern_gap, bright_values


def draw_interference(angle, intensity, formula) -> Figure:
    """The intensity of two sources against the angle."""
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line"))
        ax.plot(angle, intensity, color=FIGURE_COLOURS[0], label="waves added")
        ax.plot(
            angle,
            formula,
            color=FIGURE_COLOURS[1],
            linestyle="--",
            linewidth=LINE["model"],
            label="formula",
        )
        ax.axhline(
            2.0,
            color="gray",
            linestyle=":",
            linewidth=LINE["guide"],
            label="sum of two intensities",
        )
        ax.set_xlabel("angle (rad)")
        ax.set_ylabel("intensity\n(units of one source)")
        # The legend would cover the curves: under the plot, in one column.
        fig.legend(loc="outside lower center", ncols=1)
    return finish(fig)


def free_end():
    """Exercise 1: a string with one free end; the three strongest peaks of
    its spectrum and the formula."""
    n_cells = 200
    dx = LENGTH / n_cells
    dt = 0.5 * dx / SPEED
    xs = grid(LENGTH, n_cells)
    free = solve(
        triangle(xs, length=LENGTH, at=0.2 * LENGTH),
        np.zeros_like(xs),
        c=SPEED,
        dx=dx,
        dt=dt,
        n_steps=round(0.8 / dt),
        right="free",
    )
    peaks = spectrum_peaks(free.u[:, round(0.6 * n_cells)], dt, count=3, floor=0.05)
    expected = np.array([(2 * n - 1) * SPEED / (4 * LENGTH) for n in (1, 2, 3)])
    return peaks, expected


def beats():
    """Exercise 2: two tones 4 Hz apart and their envelope."""
    f1, f2 = 100.0, 104.0
    t = np.linspace(0.0, 1.0, 20001)
    total = np.sin(2 * np.pi * f1 * t) + np.sin(2 * np.pi * f2 * t)
    envelope = 2 * np.abs(np.cos(np.pi * (f1 - f2) * t))
    beat_rate = abs(f1 - f2)
    return total, envelope, beat_rate


def first_dark_fringe():
    """Exercise 3: the angle of the first dark fringe and the intensity
    there."""
    first_dark = np.arcsin(0.5 * wavelength / separation)
    value = two_source_pattern(first_dark, separation=separation, wavelength=wavelength)
    return first_dark, value


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    x, both = superposition()
    experiment.figure("fig-superposition", partial(draw_superposition, x, both))
    experiment.number("linearity-bound", LINEARITY_BOUND, ".0e")

    record, dt, analytic, scheme, deviation = modes_run(experiment)
    experiment.number("largest-deviation", deviation.max() * 100, ".3f")
    experiment.number("mode-tolerance", MODE_TOLERANCE * 100, ".1f")
    experiment.number(
        "scheme-shift", np.max(np.abs(scheme - analytic) / analytic) * 100, ".3f"
    )
    experiment.figure("fig-modes-spectrum", partial(draw_modes_spectrum, record, dt))

    on, off, growth = resonance_run(experiment)
    experiment.figure("fig-resonance", partial(draw_resonance, on, off))
    experiment.number("growth", growth, ".1f")
    experiment.number("off-largest", np.max(np.abs(off[1])), ".1e")

    rows, agreement = dispersion_run(experiment)
    experiment.number("agreement", agreement, ".1e")
    experiment.number("finest-shortfall", (1 - rows[-1][5]) * 100, ".0f")
    experiment.number(
        "cells-per-wavelength", 2 * dispersion_cells / mode_numbers[-1], ".1f"
    )

    packet_speed, packet_time, group = packet_run()
    experiment.number("packet-speed", packet_speed, ".1f")
    experiment.number("packet-time-ms", packet_time * 1000, ".1f")
    experiment.number("group", group, ".1f")
    experiment.number("speed", SPEED, ".0f")

    angle, intensity, formula, pattern_gap, bright_values = interference_run()
    experiment.figure(
        "fig-interference", partial(draw_interference, angle, intensity, formula)
    )
    experiment.number("pattern-gap", pattern_gap, ".1e")
    experiment.number("bright", bright_values.max(), ".0f")

    peaks, expected = free_end()
    experiment.number("free-peaks", ", ".join(f"{p:.1f}" for p in peaks))
    experiment.number("free-expected", ", ".join(f"{p:.1f}" for p in expected))
    total, envelope, beat_rate = beats()
    experiment.number("beat-rate", beat_rate, ".0f")
    experiment.number("beat-largest", np.max(np.abs(total)), ".2f")
    experiment.number("envelope-largest", envelope.max(), ".0f")
    first_dark, value = first_dark_fringe()
    experiment.number("first-dark", first_dark, ".4f")
    experiment.number("dark-value", float(value), ".3f")
    return experiment


if __name__ == "__main__":
    main(run)
