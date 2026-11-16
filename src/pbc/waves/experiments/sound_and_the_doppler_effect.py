"""The experiment of the lesson "Sound and the Doppler effect".

The resonances of a pipe open or closed at one end, found from a pulse and
from a sweep of the driving frequency (``pbc.waves.wave``), and the
frequency heard from a moving source and by a moving listener
(``pbc.waves.sound``). Run it as a program to write the figures and numbers
of the page:

    uv run --locked --no-dev \\
        python -m pbc.waves.experiments.sound_and_the_doppler_effect out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.figure_language import figsize, figure_style, finish
from pbc.waves.modes import measured_frequency, spectrum_peaks, triangle
from pbc.waves.sound import (
    SPEED_OF_SOUND,
    observer_shift,
    pipe_frequency,
    received_signal,
    source_shift,
)
from pbc.waves.wave import grid, solve

# region: setup
LENGTH = 0.8  # pipe length, m
SOUND = SPEED_OF_SOUND  # speed of sound, m/s
PIPE_TOLERANCE = 1e-3  # a chosen tolerance on the relative difference
# endregion: setup
# region: doppler
F0 = 440.0  # frequency of the tone, Hz
START = 300.0  # starting distance, m
times = np.linspace(1.5, 2.0, 100_000)
DOPPLER_TOLERANCE = 1e-4  # a chosen tolerance on the relative difference
# endregion: doppler


def pipe_run(experiment: Experiment):
    """A pulse in a pipe open at both ends and in one closed at one end, and
    the first three peaks of the spectrum against the analytic resonances;
    record the table and return its rows and the largest difference."""
    cells = 160
    dx = LENGTH / cells
    dt = 0.5 * dx / SOUND
    xs = grid(LENGTH, cells)
    pulse = triangle(xs, length=LENGTH, at=0.2 * LENGTH)
    steps = round(0.4 / dt)
    stride = 4  # the field is recorded every fourth step

    pipes = {
        "open at both ends": dict(
            left="fixed", right="fixed", closed=False, probe=0.45
        ),
        "closed at the right end": dict(
            left="fixed", right="free", closed=True, probe=0.6
        ),
    }
    pipe_rows = []
    worst_pipe = 0.0
    for name, setup in pipes.items():
        result = solve(
            pulse,
            np.zeros_like(xs),
            c=SOUND,
            dx=dx,
            dt=dt,
            n_steps=steps,
            every=stride,
            left=setup["left"],
            right=setup["right"],
        )
        signal = result.u[:, round(setup["probe"] * cells)]
        found = spectrum_peaks(signal, stride * dt, count=3, floor=0.05)
        for n, f in zip((1, 2, 3), found, strict=True):
            expected = pipe_frequency(
                n, length=LENGTH, c=SOUND, closed_end=setup["closed"]
            )
            worst_pipe = max(worst_pipe, abs(f / expected - 1.0))
            pipe_rows.append((name, n, expected, f, (f / expected - 1.0) * 100))
    assert worst_pipe < PIPE_TOLERANCE, "a resonance is not where the formula puts it"

    experiment.table(
        "pipe-run",
        pipe_rows,
        [
            ("pipe", "", ""),
            ("resonance", "", "d"),
            ("analytic", "Hz", ".1f"),
            ("simulated", "Hz", ".1f"),
            ("difference", "%", ".4f"),
        ],
        "The first three resonances of a pipe of the stated length, open at both "
        "ends and closed at one, against the analytic frequencies, and the "
        "percentage difference.",
    )
    return pipe_rows, worst_pipe


def sweep_run(experiment: Experiment):
    """The closed pipe driven next to its closed end over a sweep of
    frequencies: its largest response, and the four peaks against the
    resonances; record the table."""
    cells = 40
    dx = LENGTH / cells
    dt = 0.5 * dx / SOUND
    xs = grid(LENGTH, cells)
    steps = round(0.1 / dt)
    push = np.zeros_like(xs)
    push[-2] = 1e6  # a push on the node next to the closed end, in m / s^2
    frequencies = np.arange(60.0, 820.0, 8.0)
    response = []
    for f in frequencies:
        omega = 2 * np.pi * f
        driven = solve(
            np.zeros_like(xs),
            np.zeros_like(xs),
            c=SOUND,
            dx=dx,
            dt=dt,
            n_steps=steps,
            every=5,
            left="fixed",
            right="free",
            forcing=lambda t: push * np.cos(omega * t),  # noqa: B023, used at once
        )
        response.append(np.max(np.abs(driven.u)))
    response = np.array(response)
    local = [
        i
        for i in range(1, len(response) - 1)
        if response[i] > response[i - 1]
        and response[i] >= response[i + 1]
        and response[i] > 0.05 * response.max()  # a peak, not a ripple
    ]
    peak_frequencies = frequencies[local][:4]
    closed = np.array(
        [
            pipe_frequency(n, length=LENGTH, c=SOUND, closed_end=True)
            for n in (1, 2, 3, 4)
        ]
    )
    spacing = float(frequencies[1] - frequencies[0])
    assert len(peak_frequencies) == 4
    assert np.all(np.abs(peak_frequencies - closed) <= spacing), (
        "a peak is off a resonance"
    )

    experiment.table(
        "sweep-run",
        [
            (n, a, p, p - a)
            for n, a, p in zip((1, 2, 3, 4), closed, peak_frequencies, strict=True)
        ],
        [
            ("resonance", "", "d"),
            ("analytic", "Hz", ".1f"),
            ("peak of the sweep", "Hz", ".0f"),
            ("difference", "Hz", ".1f"),
        ],
        "The four peaks of the response of the closed pipe to a sweep of the "
        "driving frequency in steps of the stated spacing, against the analytic "
        "resonances.",
    )
    return frequencies, response, closed, spacing


def draw_sweep(frequencies, response, closed) -> Figure:
    """The response of the closed pipe against the driving frequency."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.plot(frequencies, response, color="#00429d")
    for f in closed:
        ax.axvline(f, color="#93003a", linestyle="--", linewidth=0.8)
    ax.set_xlabel("driving frequency (Hz)")
    ax.set_ylabel("largest pressure in the pipe (arbitrary units)")
    return fig


def at_rest(t):
    return np.zeros_like(t)


def source_moving(speed):
    return lambda t: -START + speed * t


def observer_moving(speed):
    return lambda t: START - speed * t


def heard(source, observer):
    return measured_frequency(
        received_signal(times, F0, source, observer, SOUND), times
    )


def doppler_run(experiment: Experiment):
    """The frequency heard from a moving source and by a moving listener at
    six speeds, computed and from the formula; record the table."""
    speeds = np.array([-120.0, -60.0, -30.0, 30.0, 60.0, 120.0])
    from_source = np.array([heard(source_moving(v), at_rest) for v in speeds])
    from_observer = np.array([heard(at_rest, observer_moving(v)) for v in speeds])
    formula_source = np.array([source_shift(F0, SOUND, v) for v in speeds])
    formula_observer = np.array([observer_shift(F0, SOUND, v) for v in speeds])
    gap_source = np.max(np.abs(from_source / formula_source - 1.0))
    gap_observer = np.max(np.abs(from_observer / formula_observer - 1.0))
    assert max(gap_source, gap_observer) < DOPPLER_TOLERANCE

    experiment.table(
        "doppler-run",
        list(
            zip(
                speeds,
                from_source,
                formula_source,
                from_observer,
                formula_observer,
                strict=True,
            )
        ),
        [
            ("speed towards", "m/s", ".0f"),
            ("moving source, computed", "Hz", ".2f"),
            ("moving source, formula", "Hz", ".2f"),
            ("moving listener, computed", "Hz", ".2f"),
            ("moving listener, formula", "Hz", ".2f"),
        ],
        "The frequency heard from a tone of the stated frequency, for a source and "
        "for a listener that move at the stated speed, towards (positive) or away "
        "(negative), computed from the moment of emission and from the formula.",
    )
    return speeds, from_source, from_observer, max(gap_source, gap_observer)


def draw_doppler(speeds, from_source, from_observer) -> Figure:
    """The heard frequency over the emitted against the speed, formulas and
    computed points."""
    v = np.linspace(-0.4, 0.4, 161) * SOUND
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line", legend=5))
        ax.plot(
            v / SOUND,
            [source_shift(F0, SOUND, s) / F0 for s in v],
            color=FIGURE_COLOURS[0],
            label="source: formula",
        )
        ax.plot(
            v / SOUND,
            [observer_shift(F0, SOUND, s) / F0 for s in v],
            color=FIGURE_COLOURS[1],
            label="listener: formula",
        )
        ax.plot(
            v / SOUND, 1 + v / SOUND, color="gray", linestyle=":", label="first order"
        )
        ax.plot(
            speeds / SOUND,
            from_source / F0,
            "o",
            color=FIGURE_COLOURS[0],
            label="source: computed",
        )
        ax.plot(
            speeds / SOUND,
            from_observer / F0,
            "s",
            color=FIGURE_COLOURS[1],
            label="listener: computed",
        )
        ax.set_xlabel("speed towards, in units of\nthe speed of sound")
        ax.set_ylabel("heard frequency\nover emitted")
        # Five entries: under the plot, in one column.
        fig.legend(loc="outside lower center", ncols=1)
    return finish(fig)


def siren():
    """Exercise 1: a siren of 700 Hz passing at 25 m/s."""
    tone = 700.0
    approaching = source_shift(tone, SOUND, 25.0)
    receding = source_shift(tone, SOUND, -25.0)
    drop = approaching - receding
    return approaching, receding, drop


def pipes_for_a():
    """Exercise 2: the lengths of a closed and of an open pipe whose lowest
    resonance is 440 Hz."""
    closed_length = SOUND / (4 * 440.0)
    open_length = SOUND / (2 * 440.0)
    check = pipe_frequency(1, length=closed_length, c=SOUND, closed_end=True)
    return closed_length, open_length, check


def plucked_in_the_middle():
    """Exercise 3: a pulse in the middle of the open pipe; its two strongest
    peaks and the distance of the nearest from the second resonance."""
    cells = 160
    dx = LENGTH / cells
    dt = 0.5 * dx / SOUND
    xs = grid(LENGTH, cells)
    centred = solve(
        triangle(xs, length=LENGTH, at=LENGTH / 2),
        np.zeros_like(xs),
        c=SOUND,
        dx=dx,
        dt=dt,
        n_steps=round(0.4 / dt),
        every=4,
    )
    found = spectrum_peaks(
        centred.u[:, round(0.17 * cells)], 4 * dt, count=2, floor=0.05
    )
    second = pipe_frequency(2, length=LENGTH, c=SOUND, closed_end=False)
    nearest = float(np.min(np.abs(found - second)))
    return found, second, nearest


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    pipe_rows, worst_pipe = pipe_run(experiment)
    experiment.number("worst-pipe", worst_pipe * 100, ".4f")
    experiment.number("pipe-tolerance", PIPE_TOLERANCE * 100, ".1f")
    experiment.number("closed-lowest", pipe_rows[3][3], ".1f")
    experiment.number("open-lowest", pipe_rows[0][3], ".1f")
    experiment.number("closed-ratio", pipe_rows[4][3] / pipe_rows[3][3], ".2f")

    frequencies, response, closed, spacing = sweep_run(experiment)
    experiment.figure("fig-sweep", partial(draw_sweep, frequencies, response, closed))
    experiment.number("spacing", spacing, ".0f")
    experiment.number("drive-resolution", 1 / 0.1, ".0f")

    speeds, from_source, from_observer, gap = doppler_run(experiment)
    experiment.figure(
        "fig-doppler", partial(draw_doppler, speeds, from_source, from_observer)
    )
    experiment.number("doppler-gap", gap, ".1e")
    experiment.number("doppler-tolerance", DOPPLER_TOLERANCE, ".0e")
    experiment.number("source-fastest", from_source[-1], ".1f")
    experiment.number("observer-fastest", from_observer[-1], ".1f")

    approaching, receding, drop = siren()
    experiment.number("approaching", approaching, ".1f")
    experiment.number("receding", receding, ".1f")
    experiment.number("drop", drop, ".1f")
    experiment.number("pitch-ratio", approaching / receding, ".3f")
    experiment.number("semitones", 12 * np.log2(approaching / receding), ".1f")

    closed_length, open_length, check = pipes_for_a()
    experiment.number("closed-length-cm", closed_length * 100, ".1f")
    experiment.number("open-length-cm", open_length * 100, ".1f")
    experiment.number("check", check, ".1f")

    found, second, nearest = plucked_in_the_middle()
    experiment.number("middle-peaks", ", ".join(f"{p:.1f}" for p in found))
    experiment.number(
        "open-first",
        pipe_frequency(1, length=LENGTH, c=SOUND, closed_end=False),
        ".1f",
    )
    experiment.number("second", second, ".1f")
    experiment.number("nearest", nearest, ".0f")
    return experiment


if __name__ == "__main__":
    main(run)
