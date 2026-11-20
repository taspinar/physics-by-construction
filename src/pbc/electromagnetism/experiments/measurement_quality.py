"""The experiment of the lesson "Measurement quality and multimodal
observations".

Captures of the simulated RLC bench pass through an imperfect acquisition
chain (``pbc.instruments.channels``): a probe and amplifier that scale and
offset, a converter that clips and quantises, a link that loses samples.
The experiment reads them with ``pbc.electromagnetism.measurement``:
calibration against a known reference, the frequency read from a record
sampled too slowly, the spread of the amplitude against the length of the
record, a clipped record, and a record with lost samples. Then it reads two
kinds of picture: a diagram of the set-up, whose interpretations are typed
and checked against the simulated bench with the probe moved
(``pbc.electromagnetism.observations``), and two generated clips of a
compass needle in a field, filmed at two frame rates, tracked frame by frame
and compared with the simulation (``pbc.electromagnetism.needle``). Every
capture and every frame is generated from a model; nothing is measured. Run
it as a program to write the figures, numbers, and the clips of the page:

    uv run --locked --no-dev \\
        python -m pbc.electromagnetism.experiments.measurement_quality out
"""

import math
from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS, diagrams
from pbc.electromagnetism import needle as compass
from pbc.electromagnetism.circuits import SeriesRLC
from pbc.electromagnetism.measurement import (
    alias,
    calibrate,
    correct,
    dominant_frequency,
    fit_sine,
    quality,
)
from pbc.electromagnetism.observations import (
    INFERRED,
    READ,
    UNCERTAIN,
    Check,
    Interpretation,
    check,
)
from pbc.experiment import Experiment, main
from pbc.figure_language import (
    LINE,
    MARKER,
    MUTED,
    direct_label,
    figsize,
    figure_style,
    finish,
    reference_slope,
)
from pbc.instruments import Capture
from pbc.instruments.channels import ChannelChain, Dropouts, ImperfectChannels
from pbc.instruments.simulated import (
    BENCH_CIRCUIT,
    ResistorProbeBench,
    SimulatedRLCBench,
)

SEED = 3
AMPLITUDE_V = 1.0
SAMPLES_PER_PERIOD = 64
PERIODS = 8
F0_HZ = BENCH_CIRCUIT.natural_frequency / (2.0 * math.pi)
FREQUENCY_HZ = 5_000.0  # the drive of the worked examples, near resonance

# region: chain
CHAIN = ChannelChain(gain=0.92, offset_v=0.05, full_scale_v=2.5, bits=10)
DROPOUTS = Dropouts(bursts=3, length=24, seed=SEED)
# endregion: chain
CLIPPING = ChannelChain(full_scale_v=2.0, bits=12)
UNCLIPPED = ChannelChain(gain=CHAIN.gain, offset_v=CHAIN.offset_v, full_scale_v=10.0)
LOST = Dropouts(bursts=6, length=29, seed=SEED)
NOISY_V = 0.05  # V: the noise of the noise example, 25 times the bench's
LENGTHS = (65, 129, 257, 513, 1025, 2049)  # samples per record
REPEATS = 24
SLOW_RATES_HZ = (320_000.0, 12_000.0, 6_000.0, 4_000.0)
SAMPLING_DURATION = 0.02  # s: a hundred periods of the drive

# The clips: one needle, two frame rates.
CLIPS = (
    ("fast", "30 frames per second", 30.0, 2.0),
    ("slow", "5 frames per second", 5.0, 4.0),
)
TABLE_RATES = (30.0, 12.0, 6.0, 5.0)
TABLE_DURATION = 4.0


def capture(bench, frequency_hz: float = FREQUENCY_HZ, samples: int | None = None):
    """One capture of ``bench`` driven at ``frequency_hz``, at 64 samples per
    period, eight periods by default."""
    bench.set_output(AMPLITUDE_V, frequency_hz)
    count = PERIODS * SAMPLES_PER_PERIOD + 1 if samples is None else samples
    return bench.capture(SAMPLES_PER_PERIOD * frequency_hz, count)


def exact_capacitor_amplitude(
    frequency_hz: float = FREQUENCY_HZ, circuit: SeriesRLC = BENCH_CIRCUIT
) -> float:
    """The amplitude of the capacitor voltage (V) in the steady state, from
    the phasor of the RLC lesson."""
    return abs(circuit.capacitor_phasor(AMPLITUDE_V, 2.0 * math.pi * frequency_hz))


# -- the first observation -------------------------------------------------------


def first_observation() -> tuple[Capture, Capture]:
    """The same capture through an ideal chain and through the lesson's
    imperfect one."""
    ideal = capture(SimulatedRLCBench(seed=SEED))
    # region: imperfect
    bench = ImperfectChannels(
        SimulatedRLCBench(seed=SEED), {"response": CHAIN}, DROPOUTS
    )
    recorded = capture(bench)
    # endregion: imperfect
    return ideal, recorded


def quality_table(experiment: Experiment, recorded: Capture) -> None:
    v = recorded.channels["response"]
    report = quality(
        v,
        recorded.sample_rate_hz,
        FREQUENCY_HZ,
        CHAIN.full_scale_v,
        calibrated=False,
        step_v=CHAIN.step_v,
    )
    experiment.table(
        "quality",
        [
            ("samples at a rail", 100 * report.clipped_fraction, "%"),
            ("samples lost", 100 * report.missing_fraction, "%"),
            ("samples per period", report.samples_per_period, ""),
            ("valid samples", 100 * report.valid.mean(), "%"),
        ],
        [("flag", "", ""), ("value", "", ".1f"), ("unit", "", "")],
        "The quality of the response channel of the first capture, to a tenth.",
    )
    experiment.number("quality-flags", ", ".join(report.flags))
    experiment.number("quality-usable", "usable" if report.usable else "not usable")
    experiment.number("peak-reading", float(np.nanmax(np.abs(v))), ".2f")
    experiment.number("exact-amplitude", exact_capacitor_amplitude(), ".3f")
    experiment.number("full-scale", CHAIN.full_scale_v, "g")
    experiment.number("bits", CHAIN.bits, "d")
    experiment.number("step-mv", 1e3 * CHAIN.step_v, ".1f")


# -- calibration -------------------------------------------------------------------


def calibration() -> dict[str, float]:
    """Connect the response probe to the generator, whose output is known,
    and fit the line recorded = gain * reference + offset; then measure the
    gain of the circuit with and without the correction."""
    # region: calibration
    probe_on_source = ImperfectChannels(
        SimulatedRLCBench(seed=SEED), {"source": UNCLIPPED}
    )
    reference = capture(probe_on_source)
    known = AMPLITUDE_V * np.cos(2.0 * math.pi * FREQUENCY_HZ * reference.t)
    gain, offset = calibrate(known, reference.channels["source"])
    # endregion: calibration
    measured = capture(
        ImperfectChannels(SimulatedRLCBench(seed=SEED + 1), {"response": UNCLIPPED})
    )
    raw = fit_sine(measured.t, measured.channels["response"], FREQUENCY_HZ)
    corrected = fit_sine(
        measured.t, correct(measured.channels["response"], gain, offset), FREQUENCY_HZ
    )
    return {
        "gain": gain,
        "offset": offset,
        "raw": raw.amplitude,
        "corrected": corrected.amplitude,
        "corrected-error": corrected.amplitude_error,
        "exact": exact_capacitor_amplitude(),
    }


# -- sampling --------------------------------------------------------------------


def sampling() -> list[tuple[float, float, float, float]]:
    """The frequency read from the response record alone, at sample rates
    from far above to below twice the drive's: rows (rate, samples per
    period, frequency read, alias predicted)."""
    rows = []
    for rate in SLOW_RATES_HZ:
        bench = SimulatedRLCBench(seed=SEED)
        bench.set_output(AMPLITUDE_V, FREQUENCY_HZ)
        record = bench.capture(rate, round(SAMPLING_DURATION * rate) + 1)
        found = dominant_frequency(record.channels["response"], rate)
        rows.append((rate, rate / FREQUENCY_HZ, found, alias(FREQUENCY_HZ, rate)))
    return rows


# -- noise and the length of the record -------------------------------------------


def noise_and_length() -> list[tuple[int, float, float, float]]:
    """The spread of the fitted amplitude over repeated captures, against
    the number of samples in each: rows (samples, standard deviation of the
    amplitude, mean standard error the fit reports, sigma sqrt(2 / N))."""
    rows = []
    for samples in LENGTHS:
        amplitudes, errors = [], []
        for repeat in range(REPEATS):
            bench = SimulatedRLCBench(seed=1000 * samples + repeat, noise_v=NOISY_V)
            record = capture(bench, samples=samples)
            fit = fit_sine(record.t, record.channels["response"], FREQUENCY_HZ)
            amplitudes.append(fit.amplitude)
            errors.append(fit.amplitude_error)
        rows.append(
            (
                samples,
                float(np.std(amplitudes, ddof=1)),
                float(np.mean(errors)),
                NOISY_V * math.sqrt(2.0 / samples),
            )
        )
    return rows


# -- clipping and missing samples ----------------------------------------------------


def clipping() -> list[tuple[str, float, int]]:
    """Three readings of one clipped record of the capacitor voltage: the
    peak, a fit to every sample, and a fit to the valid samples only."""
    chain = CLIPPING
    record = capture(
        ImperfectChannels(SimulatedRLCBench(seed=SEED), {"response": chain})
    )
    v = record.channels["response"]
    # region: clipped-fit
    report = quality(
        v, record.sample_rate_hz, FREQUENCY_HZ, chain.full_scale_v, True, chain.step_v
    )
    everything = fit_sine(record.t, v, FREQUENCY_HZ)
    inside = fit_sine(record.t, v, FREQUENCY_HZ, valid=report.valid)
    # endregion: clipped-fit
    return [
        ("the largest sample", float(np.max(np.abs(v))), len(v)),
        ("fit to every sample", everything.amplitude, everything.used),
        ("fit to the samples inside the rails", inside.amplitude, inside.used),
    ]


def missing_samples() -> list[tuple[str, float, int]]:
    """One record with a third of its samples lost in bursts, read with the
    lost samples left out and with them filled with zeros."""
    record = capture(ImperfectChannels(SimulatedRLCBench(seed=SEED), {}, LOST))
    v = record.channels["response"]
    masked = fit_sine(record.t, v, FREQUENCY_HZ)
    zeros = fit_sine(record.t, np.nan_to_num(v, nan=0.0), FREQUENCY_HZ)
    return [
        ("lost samples left out", masked.amplitude, masked.used),
        ("lost samples set to zero", zeros.amplitude, zeros.used),
    ]


# -- the picture of the set-up ---------------------------------------------------------


def _sweep_peak(bench_class, circuit: SeriesRLC) -> tuple[float, float]:
    """The frequency (Hz) and the gain of the largest response of a fine
    sweep around resonance, measured on a noiseless bench."""
    frequencies = np.linspace(0.85 * F0_HZ, 1.1 * F0_HZ, 51)
    gains = []
    for f in frequencies:
        record = capture(bench_class(circuit=circuit, seed=SEED, noise_v=0.0), f)
        source = fit_sine(record.t, record.channels["source"], f).amplitude
        gains.append(
            fit_sine(record.t, record.channels["response"], f).amplitude / source
        )
    best = int(np.argmax(gains))
    return float(frequencies[best]), float(gains[best])


def _at(
    bench_class, frequency_hz: float, circuit: SeriesRLC = BENCH_CIRCUIT
) -> tuple[float, float]:
    """Gain and phase (deg) of the response against the source at one
    frequency, on a noiseless bench."""
    record = capture(bench_class(circuit=circuit, seed=SEED, noise_v=0.0), frequency_hz)
    source = fit_sine(record.t, record.channels["source"], frequency_hz)
    response = fit_sine(record.t, record.channels["response"], frequency_hz)
    phase = math.degrees(response.phase - source.phase)
    return response.amplitude / source.amplitude, (phase + 180.0) % 360.0 - 180.0


# region: readings
READINGS = (
    Interpretation(
        "Channel 1 records the source voltage.",
        READ,
        "its probe is across the generator's terminals",
    ),
    Interpretation(
        "Channel 2 records the voltage across the capacitor.",
        READ,
        "its probe is across the capacitor",
    ),
    Interpretation(
        "The set-up does not record the current; channel 2 gives it as"
        " i = C dv/dt only if C is known.",
        INFERRED,
        "no probe is across the resistor; the capacitor's law",
    ),
    Interpretation(
        "Channel 2 peaks at the natural frequency 1 / (2 pi sqrt(LC)).",
        INFERRED,
        "a series circuit resonates where the reactances cancel",
    ),
    Interpretation(
        "With the probe moved to the resistor, channel 2 peaks at the natural"
        " frequency with a gain of one, in phase with the source, whatever R is.",
        INFERRED,
        "at the natural frequency the impedance is R alone, so v_R = v_source",
    ),
    Interpretation(
        "With R doubled, the peak of channel 2 is about half as high.",
        UNCERTAIN,
        "the peak of the capacitor voltage is about Q, and Q falls as 1 / R",
        settled_by="the component values, which the diagram does not give:"
        " the rule needs Q well above one",
    ),
)
# endregion: readings


def check_readings() -> list[Check]:
    """Each reading of the diagram against the simulated bench: the bench of
    the diagram, the same bench with the probe on the resistor, and the
    bench with R doubled."""
    bench = capture(SimulatedRLCBench(seed=SEED, noise_v=0.0), F0_HZ)
    source = fit_sine(bench.t, bench.channels["source"], F0_HZ).amplitude
    # At f0 the inductor's voltage also has a gain of Q; the capacitor's alone
    # lags the source by a quarter period.
    capacitor_gain, capacitor_phase = _at(SimulatedRLCBench, F0_HZ)
    # The current from channel 2, against the current from a resistor probe.
    response = fit_sine(bench.t, bench.channels["response"], F0_HZ).amplitude
    current_from_c = BENCH_CIRCUIT.capacitance * 2 * math.pi * F0_HZ * response
    probe = capture(ResistorProbeBench(seed=SEED, noise_v=0.0), F0_HZ)
    resistor = fit_sine(probe.t, probe.channels["response"], F0_HZ).amplitude
    current_from_r = resistor / BENCH_CIRCUIT.resistance
    peak_f, peak = _sweep_peak(SimulatedRLCBench, BENCH_CIRCUIT)
    doubled = SeriesRLC(
        2.0 * BENCH_CIRCUIT.resistance,
        BENCH_CIRCUIT.inductance,
        BENCH_CIRCUIT.capacitance,
    )
    _, doubled_peak = _sweep_peak(SimulatedRLCBench, doubled)
    half = doubled_peak / peak
    # The probe on the resistor, for R and for R doubled: where the sweep
    # peaks, how high, and the phase at the natural frequency.
    step = 0.25 * F0_HZ / 50  # the step of the sweep (Hz)
    on_resistor = [
        (*_sweep_peak(ResistorProbeBench, c), _at(ResistorProbeBench, F0_HZ, c)[1])
        for c in (BENCH_CIRCUIT, doubled)
    ]
    return [
        check(
            READINGS[0], abs(source - AMPLITUDE_V) < 1e-3, f"{source:.3f} V at 1 V set"
        ),
        check(
            READINGS[1],
            abs(capacitor_gain / BENCH_CIRCUIT.quality_factor - 1) < 1e-3
            and abs(capacitor_phase + 90.0) < 0.1,
            f"gain {capacitor_gain:.3f} at f0, Q = {BENCH_CIRCUIT.quality_factor:.3f};"
            f" phase {capacitor_phase:.2f} deg, lagging as a capacitor's",
        ),
        check(
            READINGS[2],
            abs(current_from_c / current_from_r - 1) < 1e-3,
            f"{1e3 * current_from_c:.2f} mA from C dv/dt,"
            f" {1e3 * current_from_r:.2f} mA from a resistor probe",
        ),
        check(
            READINGS[3],
            abs(peak_f / F0_HZ - 1) < 0.005,
            f"peak at {peak_f:.0f} Hz, f0 = {F0_HZ:.0f} Hz",
        ),
        check(
            READINGS[4],
            all(
                abs(f - F0_HZ) <= step / 2 and abs(g - 1) < 1e-3 and abs(p) < 0.1
                for f, g, p in on_resistor
            ),
            "; ".join(
                f"R = {c.resistance:.0f} ohm: peak at {f:.0f} Hz, gain {g:.3f},"
                f" phase difference {abs(p):.2f} deg"
                for c, (f, g, p) in zip(
                    (BENCH_CIRCUIT, doubled), on_resistor, strict=True
                )
            ),
        ),
        check(
            READINGS[5],
            abs(half - 0.5) < 0.05,
            f"peaks {peak:.3f} and {doubled_peak:.3f}, ratio {half:.2f}",
        ),
    ]


# -- the clips ---------------------------------------------------------------------


def clips() -> dict[str, compass.Clip]:
    """The two generated clips of the needle."""
    needle = compass.Needle()
    return {
        name: compass.film(needle, rate, duration) for name, _, rate, duration in CLIPS
    }


def tracks(filmed: dict[str, compass.Clip]) -> dict[str, np.ndarray]:
    """The angle of the needle found in every frame of each clip (rad)."""
    # region: track
    angles = {
        name: np.array([compass.track_angle(frame) for frame in clip.frames])
        for name, clip in filmed.items()
    }
    # endregion: track
    return angles


def frame_rates() -> list[tuple[float, float, float, float, float]]:
    """The frequency and the field read from clips of the needle at several
    frame rates: rows (frame rate, frames per swing, frequency read,
    alias predicted, field read in mT)."""
    needle = compass.Needle()
    rows = []
    for rate in TABLE_RATES:
        clip = compass.film(needle, rate, TABLE_DURATION)
        angles = np.array([compass.track_angle(frame) for frame in clip.frames])
        fit = compass.fit_track(clip.t, angles)
        rows.append(
            (
                rate,
                rate / needle.frequency,
                fit.frequency,
                alias(needle.frequency, rate),
                1e3 * compass.field_from_frequency(fit.frequency, fit.damping),
            )
        )
    return rows


def clip_file(filmed: dict[str, compass.Clip]) -> dict:
    """The on-demand file of the clip viewer: every frame as a PNG data URL
    with its time, and the words the viewer shows."""
    return {
        "schema": "clip-frames-1",
        "label": "Generated by the build from a simulation; not filmed.",
        "clips": [
            {
                "id": name,
                "title": title,
                "frame_rate": rate,
                "width": compass.WIDTH,
                "height": compass.HEIGHT,
                "alt": (
                    "A compass needle on a pivot in front of a scale of ticks"
                    " every ten degrees, the field pointing up the frame."
                ),
                "frames": [
                    {"t": round(float(t), 6), "src": compass.data_url(frame)}
                    for t, frame in zip(clip.t, clip.frames, strict=True)
                ],
            }
            for (name, title, rate, _), clip in zip(CLIPS, filmed.values(), strict=True)
        ],
    }


# -- the figures -----------------------------------------------------------------------


def draw_imperfect_capture(ideal: Capture, recorded: Capture) -> Figure:
    """The response of the first capture as the converter wrote it, and the
    rails, over the record of an ideal chain; nothing is fitted."""
    v = recorded.channels["response"]
    t_ms = 1e3 * recorded.t
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line", legend=1))
        ax.plot(
            t_ms, ideal.channels["response"], color=MUTED, linewidth=LINE["guide"],
            linestyle=":", label="at the probe (ideal chain)",
        )  # fmt: skip
        ax.plot(
            t_ms, v, linestyle="none", marker="o", markersize=MARKER - 2.0,
            color=FIGURE_COLOURS[0], label="recorded",
        )  # fmt: skip
        for rail in (-CHAIN.full_scale_v, CHAIN.full_scale_v):
            ax.axhline(rail, color=MUTED, linewidth=LINE["axis"])
        direct_label(
            ax, t_ms[-1], CHAIN.full_scale_v, "rail", MUTED, ha="right", va="bottom"
        )
        ax.set_xlabel("time (ms)")
        ax.set_ylabel("response channel (V)")
        ax.legend(
            loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=1, frameon=False
        )
    return finish(fig)


def draw_noise_and_length(rows: list[tuple[int, float, float, float]]) -> Figure:
    """The spread of the fitted amplitude against the record length, log-log,
    with the expected sigma sqrt(2 / N) and a reference slope of minus one
    half."""
    n = np.array([r[0] for r in rows], dtype=float)
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line", legend=1))
        ax.loglog(
            n, [1e3 * r[1] for r in rows], linestyle="none", marker="o",
            markersize=MARKER, color=FIGURE_COLOURS[0],
            label=f"spread over {REPEATS} captures",
        )  # fmt: skip
        ax.loglog(
            n, [1e3 * r[2] for r in rows], linestyle="--", marker="s",
            markersize=MARKER - 1.0, color=FIGURE_COLOURS[1], linewidth=LINE["guide"],
            label="standard error the fit reports",
        )  # fmt: skip
        reference_slope(ax, n, 1e3 * rows[0][3], -0.5, below=0.6)
        ax.set_xlabel("samples in the record")
        ax.set_ylabel("amplitude spread (mV)")
        ax.legend(
            loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=1, frameon=False
        )
    return finish(fig)


def draw_bench_setup() -> Figure:
    """The measurement set-up: a generator driving a series R, L, C, with
    channel 1 across the generator and channel 2 across the capacitor."""
    fig, ax = diagrams.canvas(6.4, 3.6, (0.0, 12.8), (0.0, 7.2))
    # The loop: generator on the left, R and L on top, C on the right.
    diagrams.line(ax, [(2.0, 1.2), (2.0, 6.0), (10.8, 6.0), (10.8, 1.2), (2.0, 1.2)])
    diagrams.circle(ax, (2.0, 3.6), 0.75, colour=0)
    diagrams.text(ax, (2.0, 3.6), "~")
    diagrams.text(ax, (0.55, 3.6), "generator", ha="center")
    diagrams.state_box(ax, (4.8, 6.0), "R", width=1.4, height=0.7, colour=0)
    diagrams.state_box(ax, (7.8, 6.0), "L", width=1.4, height=0.7, colour=0)
    diagrams.state_box(ax, (10.8, 3.6), "C", width=0.9, height=1.2, colour=0)
    # The probes: channel 1 across the generator, channel 2 across C.
    diagrams.line(
        ax, [(2.0, 5.0), (3.3, 5.0), (3.3, 2.2), (2.0, 2.2)], colour=1, linestyle="--"
    )
    diagrams.text(ax, (3.5, 3.6), "channel 1", ha="left", colour=1)
    diagrams.line(
        ax, [(10.8, 5.0), (9.5, 5.0), (9.5, 2.2), (10.8, 2.2)], colour=2, linestyle=":"
    )
    diagrams.text(ax, (9.3, 3.6), "channel 2", ha="right", colour=2)
    return fig


def draw_needle_frames(filmed: dict[str, compass.Clip]) -> Figure:
    """The first four frames of each clip, one clip a row, with the time of
    each frame."""
    with figure_style():
        fig, axes = plt.subplots(2, 4, figsize=(4.1, 2.35))
        for row, (name, _, _, _) in zip(axes, CLIPS, strict=True):
            clip = filmed[name]
            for ax, index in zip(row, range(4), strict=True):
                ax.imshow(
                    clip.frames[index], cmap="gray", vmin=0, vmax=255,
                    interpolation="nearest",
                )  # fmt: skip
                ax.set_xticks([])
                ax.set_yticks([])
                ax.set_title(f"{clip.t[index]:.2f} s", fontsize=11.0)
                if index == 0:
                    ax.set_ylabel(f"{clip.frame_rate:g} frames/s", fontsize=11.0)
                for spine in ax.spines.values():
                    spine.set_visible(False)
    return fig


def draw_needle_tracks(
    filmed: dict[str, compass.Clip], found: dict[str, np.ndarray]
) -> Figure:
    """The angle found in each frame of the two clips, on the simulated
    motion; the slow clip's frames joined in order."""
    needle = compass.Needle()
    fine = np.linspace(0.0, 4.0, 4001)
    truth = compass.simulate(needle, fine)
    fast, slow = filmed["fast"], filmed["slow"]
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line", legend=2))
        ax.plot(
            fine, np.degrees(truth), color=MUTED, linewidth=LINE["guide"],
            label="simulated motion",
        )  # fmt: skip
        ax.plot(
            fast.t, np.degrees(found["fast"]), linestyle="none", marker="o",
            markersize=MARKER - 1.0, color=FIGURE_COLOURS[0],
            label="tracked, 30 frames/s",
        )  # fmt: skip
        ax.plot(
            slow.t, np.degrees(found["slow"]), linestyle="--", marker="s",
            markersize=MARKER, color=FIGURE_COLOURS[1], linewidth=LINE["model"],
            label="tracked, 5 frames/s, in order",
        )  # fmt: skip
        ax.set_xlabel("time (s)")
        ax.set_ylabel("needle angle (deg)")
        ax.legend(
            loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=1, frameon=False
        )
    return finish(fig)


# -- run ---------------------------------------------------------------------------


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()

    ideal, recorded = first_observation()
    experiment.figure(
        "fig-imperfect-capture", partial(draw_imperfect_capture, ideal, recorded)
    )
    quality_table(experiment, recorded)

    calibrated = calibration()
    experiment.table(
        "calibration",
        [
            ("gain", CHAIN.gain, calibrated["gain"], ""),
            ("offset", CHAIN.offset_v, calibrated["offset"], "V"),
        ],
        [
            ("quantity", "", ""),
            ("in the chain", "", ".4f"),
            ("calibrated", "", ".4f"),
            ("unit", "", ""),
        ],
        "The gain and offset of the response channel, as the chain has them and"
        " as the calibration against the generator finds them, to four decimals.",
    )
    experiment.table(
        "amplitudes",
        [
            ("fit, uncorrected", calibrated["raw"]),
            ("fit, corrected with the calibration", calibrated["corrected"]),
            ("closed form", calibrated["exact"]),
        ],
        [("reading", "", ""), ("amplitude of the capacitor voltage", "V", ".3f")],
        "The amplitude of the capacitor voltage near resonance, read through the"
        " chain with and without the calibration, and the closed form; to the"
        " millivolt.",
    )
    experiment.number(
        "amplitude-corrected-error", 1e3 * calibrated["corrected-error"], ".1f"
    )
    experiment.number(
        "raw-error-percent", 100 * (1 - calibrated["raw"] / calibrated["exact"]), ".1f"
    )

    rows = sampling()
    experiment.table(
        "sampling",
        [(r[0] / 1e3, r[1], r[2], r[3]) for r in rows],
        [
            ("sample rate", "kHz", ".0f"),
            ("samples per period", "", ".2f"),
            ("frequency read from the record", "Hz", ".0f"),
            ("alias predicted", "Hz", ".0f"),
        ],
        "The frequency of the strongest component of the response record,"
        " read from the record alone, at four sample rates, with the frequency"
        f" the sampling theorem predicts; the drive is at {FREQUENCY_HZ / 1e3:g} kHz.",
    )
    experiment.number("drive", FREQUENCY_HZ, ".0f")
    experiment.number("nyquist", 2 * FREQUENCY_HZ / 1e3, ".0f")

    noise = noise_and_length()
    experiment.figure("fig-noise-and-length", partial(draw_noise_and_length, noise))
    experiment.table(
        "noise",
        [(n, 1e3 * s, 1e3 * e, 1e3 * p) for n, s, e, p in noise],
        [
            ("samples", "", "d"),
            ("spread of the amplitude", "mV", ".2f"),
            ("standard error of the fit", "mV", ".2f"),
            ("sigma sqrt(2/N)", "mV", ".2f"),
        ],
        f"The spread of the fitted amplitude over {REPEATS} captures at each"
        " record length, the mean standard error the fit reports, and the"
        " expected value; in millivolts to a hundredth.",
    )
    experiment.number("noise-mv", 1e3 * NOISY_V, ".0f")
    experiment.number("repeats", REPEATS, "d")
    experiment.number("length-ratio", LENGTHS[-1] / LENGTHS[0], ".0f")
    experiment.number("spread-ratio", noise[0][1] / noise[-1][1], ".1f")

    experiment.table(
        "clipping",
        clipping(),
        [("reading", "", ""), ("amplitude", "V", ".3f"), ("samples used", "", "d")],
        "Three readings of one record of the capacitor voltage, clipped at"
        f" plus and minus {CLIPPING.full_scale_v:g} V by a converter of"
        f" {CLIPPING.bits} bits; to the millivolt.",
    )
    experiment.table(
        "missing",
        missing_samples(),
        [("reading", "", ""), ("amplitude", "V", ".3f"), ("samples used", "", "d")],
        "Two readings of one record with a third of its samples lost in"
        f" {LOST.bursts} bursts; to the millivolt.",
    )

    experiment.figure("fig-bench-setup", draw_bench_setup)
    checks = check_readings()
    experiment.table(
        "readings",
        [
            (c.interpretation.statement, c.interpretation.status, c.outcome, c.evidence)
            for c in checks
        ],
        [
            ("reading", "", ""),
            ("status", "", ""),
            ("check", "", ""),
            ("evidence", "", ""),
        ],
        "The readings of the diagram, typed, and each checked against the"
        " simulated bench (the probe moved or R doubled where the reading says so).",
    )
    experiment.number("f0", F0_HZ, ".0f")

    filmed = clips()
    found = tracks(filmed)
    experiment.widget("needle-clips", clip_file(filmed))
    experiment.figure("fig-needle-frames", partial(draw_needle_frames, filmed))
    experiment.figure("fig-needle-tracks", partial(draw_needle_tracks, filmed, found))
    worst = max(
        float(np.max(np.abs(found[name] - clip.theta))) for name, clip in filmed.items()
    )
    experiment.number("track-error", math.degrees(worst), ".2f")
    needle = compass.Needle()
    experiment.number("needle-frequency", needle.frequency, ".2f")
    experiment.number("field-set", 1e3 * needle.field, ".2f")
    experiment.number("start-deg", compass.START_DEG, ".0f")
    fits = {name: compass.fit_track(filmed[name].t, found[name]) for name in filmed}
    for name, fit in fits.items():
        experiment.number(f"{name}-frequency", fit.frequency, ".2f")
        experiment.number(
            f"{name}-field",
            1e3 * compass.field_from_frequency(fit.frequency, fit.damping),
            ".3f",
        )
    experiment.number("slow-alias", alias(needle.frequency, 5.0), ".2f")
    experiment.number("frames", sum(len(c.frames) for c in filmed.values()), "d")
    experiment.number("slow-frames", len(filmed["slow"].frames), "d")
    experiment.table(
        "frame-rates",
        frame_rates(),
        [
            ("frame rate", "frames/s", ".0f"),
            ("frames per swing", "", ".2f"),
            ("frequency read", "Hz", ".2f"),
            ("alias predicted", "Hz", ".2f"),
            ("field read", "mT", ".3f"),
        ],
        "The frequency and the field read from four-second clips of the same"
        " needle at four frame rates, with the frequency the sampling theorem"
        f" predicts; the field set in the simulation is {1e3 * compass.FIELD:g} mT.",
    )
    fast_field = compass.field_from_frequency(
        fits["fast"].frequency, fits["fast"].damping
    )
    clip_checks = [
        check(
            Interpretation(
                "The needle swings about once a second (the slow clip).",
                UNCERTAIN,
                "the angle found in twenty frames at five frames per second",
                settled_by="a frame rate above twice the swing's frequency,"
                " or another bound on that frequency",
            ),
            abs(fits["slow"].frequency - needle.frequency) < 0.05,
            f"the simulated needle swings at {needle.frequency:.2f} Hz",
        ),
        check(
            Interpretation(
                "The field is about half a millitesla (the fast clip).",
                INFERRED,
                "the frequency and decay of the track, the needle's m and I,"
                " and B = I (omega^2 + gamma^2) / m for small swings",
            ),
            # The read field agrees with the simulation's, and both are about
            # half a millitesla, as the statement says.
            abs(fast_field / needle.field - 1) < 0.02
            and abs(fast_field / 0.5e-3 - 1) < 0.1,
            f"read {1e3 * fast_field:.3f} mT; the simulation's field is"
            f" {1e3 * needle.field:.2f} mT",
        ),
    ]
    experiment.table(
        "clip-readings",
        [
            (c.interpretation.statement, c.interpretation.status, c.outcome, c.evidence)
            for c in clip_checks
        ],
        [
            ("reading", "", ""),
            ("status", "", ""),
            ("check", "", ""),
            ("evidence", "", ""),
        ],
        "Two readings of the clips, typed, against the simulation.",
    )
    return experiment


if __name__ == "__main__":
    main(run)
