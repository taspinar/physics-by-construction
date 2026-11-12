"""The experiment of the lesson "Stress-strain measurements lab".

The linear elastic model of the lesson "Elasticity and deformation"
(sigma = E epsilon, with its illustrative steel of 200 GPa) against a
measured test of a dual-phase sheet steel (the committed sample of the card
``nist-numisheet-dp980``): tension to 5.8 % strain, compression back to
zero strain, tension to fracture. The experiment fits E to the elastic
regime with its standard error and its sensitivity to the fit window, finds
where the curve leaves the line by offset constructions, tests the model's
prediction for the unloading, and integrates the hysteresis loop. Run it as
a program to write the figures and the numbers of the page:

    uv run --locked --no-dev python -m \\
        pbc.materials.experiments.stress_strain_measurements out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.data import SAMPLES_DIR
from pbc.data.adapters import stress_strain_series
from pbc.data.fit import FitResult, fit_curve
from pbc.data.plotting import COLOURS, add_credit, label_status
from pbc.data.reference.nist_numisheet import (
    THICKNESS_MM,
    WIDTH_MM,
    Segments,
    Test,
    load,
    preload,
    reload_maximum,
    segments,
    stress_from_load_cells,
)
from pbc.experiment import Experiment, main
from pbc.materials.experiments.elasticity_and_deformation import E as MAT3_E
from pbc.materials.stress_strain import (
    closed_loop_work,
    elastic_unloading,
    hooke_stress,
    offset_crossing,
    true_stress_strain,
)

DATASET = "nist-numisheet-dp980"
# region: choices
MODEL_MODULUS = MAT3_E / 1e9  # GPa, the illustrative steel of the MAT3 lesson
WINDOW = (100.0, 400.0)  # MPa, the stress window of the elastic fit
WINDOWS = ((50.0, 300.0), (100.0, 300.0), (100.0, 400.0), (150.0, 450.0))
OFFSETS = (0.0002, 0.0005, 0.001, 0.002)  # strain offsets of the yield lines
REVERSE_OFFSET = 0.002  # offset of the reverse yield from the unloading line
# endregion: choices
CREDIT = (
    "Data: NIST; Luecke, Rust, Iadicola, 'Data for Numisheet 2020 uniaxial tensile "
    "and tension/compression tests', doi 10.18434/M32202, v1.2.0; file "
    "C00FeDP980Numisheet2020R01T1.424W17.93-S-Stress-Strain.csv, unmodified (NIST "
    "data, 17 U.S.C. 105). Fitted, offset and model lines and the loop: this "
    "lesson's code, not part of the record."
)


def load_test() -> Test:
    """The committed test R01, with its rows in time order."""
    return load(SAMPLES_DIR / DATASET)


def landmarks(test: Test) -> dict:
    """What the measurement shows without a model: the stress maximum of the
    first tension, the end of the hold after it, the most compressive
    stress, the highest stress of the last tension (where necking starts),
    the fracture, and the scatter of the rows before the force ramp."""
    seg = segments(test)
    neck = reload_maximum(test)
    quiet = preload(test)
    e, s, t = test.strain, test.stress, test.time
    return {
        "rows": int(t.size),
        "duration": float(t[-1]),
        "peak-stress": float(s[seg.reversal]),
        "peak-strain": float(e[seg.reversal]),
        "hold-strain": float(e[seg.hold_end]),
        "hold-stress": float(s[seg.hold_end]),
        "min-stress": float(s[seg.compression]),
        "min-strain": float(e[seg.compression]),
        "neck-stress": float(s[neck]),
        "neck-strain": float(e[neck]),
        "fracture-strain": float(e[-1]),
        "quiet-rows": int(quiet.size),
        "strain-noise": float(np.std(e[quiet], ddof=1)),
        "stress-noise": float(np.std(s[quiet], ddof=1)),
    }


def landmark_table(experiment: Experiment, test: Test) -> None:
    """The landmarks of the path as a table: row, time, strain, stress."""
    seg = segments(test)
    neck = reload_maximum(test)
    rows = [
        ("stress maximum of the first tension", seg.reversal),
        ("end of the hold, start of the unloading", seg.hold_end),
        ("most compressive stress", seg.compression),
        ("highest stress of the last tension", neck),
        ("last row, fracture", test.time.size - 1),
    ]
    experiment.table(
        "landmarks",
        [(name, test.time[k], test.strain[k], test.stress[k]) for name, k in rows],
        columns=[
            ("point of the path", "", "s"),
            ("time", "s", ".1f"),
            ("engineering strain", "", ".4f"),
            ("engineering stress", "MPa", ".1f"),
        ],
        caption="The measured landmarks of test R01, read from the rows of the file "
        "without a model.",
    )


def first_loading(test: Test) -> tuple[np.ndarray, np.ndarray]:
    """Strain and stress of the first tension, up to its stress maximum."""
    stop = segments(test).reversal
    return test.strain[:stop], test.stress[:stop]


def fit_modulus(
    test: Test, window: tuple[float, float] = WINDOW, intercept: bool = True
) -> FitResult:
    """Fit Hooke's law S = E e + S0 (or S = E e with ``intercept=False``) to
    the first loading inside a stress window; E in GPa, S0 in MPa. The record
    gives no uncertainty per point, so the standard errors come from the
    scatter of the residuals."""
    e, s = first_loading(test)
    keep = (s > window[0]) & (s < window[1])
    if intercept:
        return fit_curve(
            hooke_stress, e[keep], s[keep], [200.0, 0.0], names=("E", "S0")
        )
    return fit_curve(
        lambda x, modulus: hooke_stress(x, modulus),
        e[keep],
        s[keep],
        [200.0],
        names=("E",),
    )


def window_rms(test: Test, modulus: float, intercept: float) -> float:
    """Root mean square [MPa] of the measured stress minus a line, over the
    fit window."""
    e, s = first_loading(test)
    keep = (s > WINDOW[0]) & (s < WINDOW[1])
    return float(
        np.sqrt(np.mean((s[keep] - hooke_stress(e[keep], modulus, intercept)) ** 2))
    )


def sensitivity(experiment: Experiment, test: Test) -> dict:
    """E over four stress windows with an intercept, and over the main
    window through the origin as the MAT3 model has it; record the table and
    return the range."""
    rows, moduli = [], []
    for window in WINDOWS:
        result = fit_modulus(test, window)
        moduli.append(result.value("E"))
        rows.append(
            (
                f"{window[0]:.0f} to {window[1]:.0f} MPa, with intercept",
                result.residuals.size,
                result.value("E"),
                float(result.stderr[0]),
                f"{result.value('S0'):.1f}",
            )
        )
    origin = fit_modulus(test, WINDOW, intercept=False)
    moduli.append(origin.value("E"))
    rows.append(
        (
            f"{WINDOW[0]:.0f} to {WINDOW[1]:.0f} MPa, through the origin",
            origin.residuals.size,
            origin.value("E"),
            float(origin.stderr[0]),
            "0 (fixed)",
        )
    )
    experiment.table(
        "modulus-sensitivity",
        rows,
        columns=[
            ("fit", "", "s"),
            ("points", "", "d"),
            ("E", "GPa", ".1f"),
            ("standard error", "GPa", ".1f"),
            ("intercept S0", "MPa", "s"),
        ],
        caption="Young's modulus from the same first loading, fitted over different "
        "stress windows and with or without an intercept: a sensitivity of the fit to "
        "the choices of the analysis, not an uncertainty of the steel's modulus.",
    )
    return {
        "low": min(moduli[:-1]),
        "high": max(moduli[:-1]),
        "origin": origin.value("E"),
        "origin-err": float(origin.stderr[0]),
    }


def offset_yields(test: Test, result: FitResult) -> list[float]:
    """The stress where the first loading crosses the fitted line shifted by
    each strain offset of ``OFFSETS``."""
    e, s = first_loading(test)
    return [
        offset_crossing(e, s, result.value("E"), offset, result.value("S0"))
        for offset in OFFSETS
    ]


def offset_table(experiment: Experiment, yields: list[float], noise: float) -> None:
    """The offset yields as a table, each offset also in units of the
    strain's scatter ``noise`` before the force ramp."""
    rows = [
        (100 * offset, offset / noise, stress)
        for offset, stress in zip(OFFSETS, yields, strict=True)
    ]
    experiment.table(
        "offsets",
        rows,
        columns=[
            ("offset of the line", "%", ".2f"),
            ("offset in strain-noise units", "", ".0f"),
            ("stress where the curve crosses it", "MPa", ".0f"),
        ],
        caption="Where the first loading crosses the fitted elastic line shifted by "
        "four strain offsets. The offset is also given in units of the scatter of the "
        "strain before the force ramp; the 0.2 % offset gives the "
        "conventional yield stress.",
    )


def unloading(test: Test, modulus: float) -> dict:
    """The unloading from the end of the hold against the elastic line of
    slope ``modulus`` through that point: the strain recovered at zero
    stress, measured and predicted, and the reverse offset yield, where the
    measured branch has fallen ``REVERSE_OFFSET`` in strain behind the line."""
    seg = segments(test)
    rows = np.arange(seg.hold_end, seg.compression + 1)
    e, s = test.strain[rows], test.stress[rows]
    e0, s0 = float(e[0]), float(s[0])
    k = int(np.argmax(s < 0))
    zero_strain = float(e[k - 1] + (e[k] - e[k - 1]) * s[k - 1] / (s[k - 1] - s[k]))
    # Mirrored, the unloading is a loading from the hold's end: the reverse
    # yield is the forward offset construction on (e0 - e, s0 - s).
    reverse = s0 - offset_crossing(e0 - e, s0 - s, modulus, REVERSE_OFFSET)
    chord = (s0 - 0.0) / (e0 - zero_strain) / 1e3
    return {
        "start-strain": e0,
        "start-stress": s0,
        "zero-strain": zero_strain,
        "recovered": e0 - zero_strain,
        "predicted": s0 / (modulus * 1e3),
        "chord": chord,
        "reverse-yield": reverse,
    }


def loop(test: Test) -> dict:
    """The hysteresis loop from the stress maximum of the first tension,
    round the compression, to the first row of the reload at that strain,
    closed by a straight segment; its work per volume, and the shoelace
    area of the same polygon."""
    seg = segments(test)
    start = seg.reversal
    end = seg.compression + int(
        np.argmax(test.strain[seg.compression :] >= test.strain[start])
    )
    e = test.strain[start : end + 1]
    s = test.stress[start : end + 1]
    work, closing = closed_loop_work(e, s)
    shoelace = 0.5 * abs(float(np.dot(e, np.roll(s, -1)) - np.dot(s, np.roll(e, -1))))
    return {
        "start": start,
        "end": end,
        "work": work,
        "closing": closing,
        "shoelace": shoelace,
        "gap-strain": float(e[-1] - e[0]),
        "gap-stress": float(s[-1] - s[0]),
        "end-time": float(test.time[end]),
    }


def ellipse_check(experiment: Experiment) -> float:
    """``closed_loop_work`` on an ellipse traversed clockwise, against its
    exact area pi a b, for polygons of more and more points; record the
    table and return the error ratio of the last halving of the step."""
    a, b = 0.03, 800.0  # semi-axes: strain and stress [MPa]
    rows, errors = [], []
    for n in (25, 50, 100, 200, 400):
        phi = -np.linspace(0, 2 * np.pi, n, endpoint=False)
        work, _ = closed_loop_work(a * np.cos(phi), b * np.sin(phi))
        exact = np.pi * a * b
        errors.append(abs(work / exact - 1))
        rows.append((n, work, exact, errors[-1]))
    experiment.table(
        "ellipse",
        rows,
        columns=[
            ("points", "", "d"),
            ("closed integral", "MJ/m^3", ".4f"),
            ("pi a b", "MJ/m^3", ".4f"),
            ("relative error", "", ".1e"),
        ],
        caption="The closed integral of S de by trapezoids round an ellipse of "
        "semi-axes 0.03 in strain and 800 MPa in stress, traversed clockwise, "
        "against its exact area.",
    )
    return errors[-2] / errors[-1]


def neck_true_stress(test: Test) -> tuple[float, float]:
    """True strain and stress at the start of necking, from the model of
    uniform deformation, and NIST's computed columns there."""
    neck = reload_maximum(test)
    true_e, true_s = true_stress_strain(test.strain[neck], test.stress[neck])
    return float(true_e), float(true_s)


def _segment_parts(seg: Segments):
    return (
        (slice(0, seg.reversal + 1), "first tension", "o", "-"),
        (
            slice(seg.reversal, seg.compression + 1),
            "unloading and compression",
            "s",
            "--",
        ),
        (slice(seg.compression, None), "tension to fracture", "^", ":"),
    )


def draw_stress_strain(test: Test, cycle: dict) -> Figure:
    """The whole measured path in its three parts, the loop shaded, and the
    landmarks marked."""
    series = stress_strain_series(test)
    seg = segments(test)
    neck = reload_maximum(test)
    e, s = series.x, series.y
    fig, ax = plt.subplots(figsize=(7.0, 4.8), constrained_layout=True)
    for k, (part, name, marker, style) in enumerate(_segment_parts(seg)):
        ax.plot(
            e[part],
            s[part],
            color=COLOURS[k],
            marker=marker,
            ms=2.2,
            lw=0.7,
            ls=style,
            markevery=4,
            label=f"measured [{series.status}]: {name}",
        )
    rows = slice(cycle["start"], cycle["end"] + 1)
    ax.fill(e[rows], s[rows], color="0.85", zorder=0, label="the hysteresis loop")
    marks = [
        (seg.reversal, "kD", "stress maximum, first tension"),
        (seg.compression, "kv", "most compressive stress"),
        (neck, "k^", "highest stress of the last tension"),
    ]
    for k, style, label in marks:
        ax.plot(e[k], s[k], style, ms=6, ls="none", label=label)
    ax.axhline(0, color="0.5", lw=0.8)
    ax.set_xlabel("engineering strain e [mm/mm]")
    ax.set_ylabel("engineering stress S [MPa]")
    ax.set_title("DP980 steel: tension, compression, tension to fracture")
    ax.legend(fontsize=7.5, loc="lower right")
    add_credit(fig, CREDIT)
    label_status(fig, series.status)
    return fig


def draw_elastic_regime(test: Test, result: FitResult, yield_stress: float) -> Figure:
    """The first loading at small strain with the fitted line, the MAT3
    line, and the 0.2 % offset line; below, the residuals of both lines."""
    series = stress_strain_series(test)
    e, s = first_loading(test)
    small = e < 0.012
    grid = np.linspace(0, 0.012, 200)
    modulus, s0 = result.value("E"), result.value("S0")
    fig, (top, bottom) = plt.subplots(
        2,
        1,
        figsize=(6.4, 7.0),
        constrained_layout=True,
        gridspec_kw={"height_ratios": [1.4, 1.0]},
    )
    top.axhspan(*WINDOW, color="0.92", label="fit window")
    top.plot(
        e[small],
        s[small],
        color=COLOURS[0],
        marker="o",
        ms=2.5,
        ls="none",
        label=f"measured first tension [{series.status}], "
        "no uncertainty per point given",
    )
    fitted = hooke_stress(grid, modulus, s0)
    shown = fitted < 1000
    top.plot(
        grid[shown],
        fitted[shown],
        "--",
        color=COLOURS[1],
        lw=1.3,
        label="Hooke's law, fitted E and intercept [simulated]",
    )
    model = hooke_stress(grid, MODEL_MODULUS)
    shown = model < 1000
    top.plot(
        grid[shown],
        model[shown],
        ":",
        color=COLOURS[2],
        lw=1.6,
        label="Hooke's law, E of the MAT3 lesson [simulated]",
    )
    shifted = hooke_stress(grid - OFFSETS[-1], modulus, s0)
    keep = (shifted > 0) & (shifted < 1000)
    top.plot(
        grid[keep],
        shifted[keep],
        "-.",
        color=COLOURS[3],
        lw=1.2,
        label="fitted line shifted by 0.2 % [simulated]",
    )
    top.axhline(yield_stress, color="0.4", lw=0.8, label="0.2 % offset yield")
    top.set_xlim(0, 0.012)
    top.set_ylim(0, 1050)
    top.set_xlabel("engineering strain e [mm/mm]")
    top.set_ylabel("engineering stress S [MPa]")
    top.set_title("The elastic regime and where the curve leaves the line")
    top.legend(fontsize=7, loc="lower right")

    upto = s < 700
    bottom.axvspan(*WINDOW, color="0.92", label="fit window")
    bottom.plot(
        s[upto],
        (s - hooke_stress(e, modulus, s0))[upto],
        color=COLOURS[1],
        marker="o",
        ms=2.5,
        ls="none",
        label="measured minus fitted line",
    )
    bottom.plot(
        s[upto],
        (s - hooke_stress(e, MODEL_MODULUS))[upto],
        color=COLOURS[2],
        marker="x",
        ms=3,
        ls="none",
        label="measured minus MAT3 line",
    )
    bottom.axhline(0, color="0.5", lw=0.8)
    bottom.set_xlabel("engineering stress S [MPa]")
    bottom.set_ylabel("residual [MPa]")
    bottom.set_title("Residuals against stress: scatter in the window, then a bend")
    bottom.legend(fontsize=7, loc="lower left")
    add_credit(fig, CREDIT)
    label_status(fig, series.status)
    return fig


def behind_elastic(
    test: Test, modulus: float, found: dict
) -> tuple[np.ndarray, np.ndarray]:
    """Stress [MPa] and the strain by which the measured unloading lies
    behind the elastic unloading line at that stress, over the unloading
    and the compression: the inelastic strain of the reversal."""
    seg = segments(test)
    rows = slice(seg.hold_end, seg.compression + 1)
    e, s = test.strain[rows], test.stress[rows]
    on_line = found["start-strain"] - (found["start-stress"] - s) / (modulus * 1e3)
    return s, on_line - e


def draw_unloading(test: Test, modulus: float, found: dict) -> Figure:
    """The first part of the unloading against the elastic unloading of
    slope E from the end of the hold; below, how far in strain the measured
    branch lies behind that line, against the stress."""
    series = stress_strain_series(test)
    seg = segments(test)
    rows = slice(seg.hold_end, seg.compression + 1)
    e, s = series.x[rows], series.y[rows]
    e0, s0 = found["start-strain"], found["start-stress"]
    near = e > e0 - 0.012
    fig, (top, bottom) = plt.subplots(
        2,
        1,
        figsize=(6.4, 6.8),
        constrained_layout=True,
        gridspec_kw={"height_ratios": [1.3, 1.0]},
    )
    top.plot(
        e[near],
        s[near],
        color=COLOURS[1],
        marker="s",
        ms=2.5,
        lw=0.6,
        label=f"measured unloading [{series.status}], no uncertainty per point given",
    )
    grid = np.linspace(e0 - (s0 + 1000) / (modulus * 1e3), e0, 100)
    top.plot(
        grid,
        elastic_unloading(grid, e0, s0, modulus),
        "--",
        color=COLOURS[0],
        lw=1.3,
        label="elastic unloading, slope of the fitted E [simulated]",
    )
    top.axhline(0, color="0.5", lw=0.8)
    top.axhline(
        found["reverse-yield"],
        color="0.4",
        lw=0.8,
        ls="-.",
        label="reverse yield: 0.2 % behind the elastic unloading",
    )
    top.set_xlim(e0 - 0.012, e0 + 0.0005)
    top.set_ylim(-1050, 1050)
    top.set_xlabel("engineering strain e [mm/mm]")
    top.set_ylabel("engineering stress S [MPa]")
    top.set_title("The reversal: the measured unloading against an elastic one")
    top.legend(fontsize=7, loc="lower right")

    stress, lag = behind_elastic(test, modulus, found)
    bottom.plot(
        stress,
        lag,
        color=COLOURS[1],
        marker="s",
        ms=2.0,
        ls="none",
        label="measured, behind the elastic unloading",
    )
    bottom.axhline(REVERSE_OFFSET, color="0.4", lw=0.8, ls="-.", label="0.2 % offset")
    bottom.axhline(0, color="0.5", lw=0.8)
    bottom.set_xlim(1050, -1050)
    # The lag grows to several per cent in the compression (the first
    # figure shows that part); the panel keeps the start, where the offset
    # is reached.
    bottom.set_ylim(-0.0005, 0.006)
    bottom.set_xlabel("engineering stress S [MPa], falling to the right")
    bottom.set_ylabel("strain behind the line [mm/mm]")
    bottom.set_title("Inelastic strain of the reversal: its first 0.6 %")
    bottom.legend(fontsize=7, loc="upper left")
    add_credit(fig, CREDIT)
    label_status(fig, series.status)
    return fig


def recovery_exercise() -> None:
    """Exercise 1: elastic recovery of a steel bar unloaded from 600 MPa."""
    modulus, stress = 200.0, 600.0
    elastic = stress / (modulus * 1e3)
    print(f"elastic recovery: {elastic:.4f} ({1e6 * elastic:.0f} um/m)")
    measured = 1.4 * elastic
    print(
        f"chord modulus for 1.4 times that recovery: {stress / measured / 1e3:.0f} GPa"
    )


def load_cell_exercise(test: Test) -> None:
    """Exercise 2: what a force difference between the load cells means as
    a stress."""
    scale = stress_from_load_cells(test)
    print(f"cross-section: {THICKNESS_MM * WIDTH_MM:.2f} mm^2")
    print(f"half the force difference over it: {scale:.1f} MPa")
    print(f"as a fraction of the stress in the middle of the window: {scale / 300:.1%}")


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    test = load_test()
    found = landmarks(test)
    landmark_table(experiment, test)
    experiment.number("rows", found["rows"])
    experiment.number("duration", found["duration"], ".0f")
    experiment.number("peak-stress", found["peak-stress"], ".0f")
    experiment.number("peak-strain", 100 * found["peak-strain"], ".2f")
    experiment.number("hold-stress", found["hold-stress"], ".0f")
    experiment.number("min-stress", found["min-stress"], ".0f")
    experiment.number("neck-stress", found["neck-stress"], ".0f")
    experiment.number("neck-strain", 100 * found["neck-strain"], ".1f")
    experiment.number("fracture-strain", 100 * found["fracture-strain"], ".1f")
    experiment.number("quiet-rows", found["quiet-rows"])
    experiment.number("strain-noise", 1e6 * found["strain-noise"], ".0f")
    experiment.number("stress-noise", found["stress-noise"], ".2f")

    result = fit_modulus(test)
    modulus, s0 = result.value("E"), result.value("S0")
    rms = window_rms(test, modulus, s0)
    experiment.number("e-fit", modulus, ".1f")
    experiment.number("e-err", result.stderr[0], ".1f")
    experiment.number("s0", s0, ".1f")
    experiment.number("s0-err", result.stderr[1], ".1f")
    experiment.number("fit-points", result.residuals.size)
    experiment.number(
        "fit-warnings", "; ".join(result.warnings) if result.warnings else "none"
    )
    experiment.number("rms", rms, ".1f")
    experiment.number("noise-times-e", found["strain-noise"] * modulus * 1e3, ".1f")
    experiment.number("s0-strain", 1e6 * s0 / (modulus * 1e3), ".0f")
    experiment.number("model-e", MODEL_MODULUS, ".0f")
    experiment.number("model-above", 100 * (MODEL_MODULUS / modulus - 1), ".1f")
    experiment.number(
        "model-sigmas", (MODEL_MODULUS - modulus) / result.stderr[0], ".1f"
    )
    experiment.number("model-rms", window_rms(test, MODEL_MODULUS, 0.0), ".1f")

    spread = sensitivity(experiment, test)
    experiment.number("window-low", spread["low"], ".1f")
    experiment.number("window-high", spread["high"], ".1f")
    experiment.number("origin-e", spread["origin"], ".1f")
    experiment.number("origin-err", spread["origin-err"], ".1f")

    yields = offset_yields(test, result)
    offset_table(experiment, yields, found["strain-noise"])
    experiment.number("yield-small", yields[0], ".0f")
    experiment.number("yield", yields[-1], ".0f")
    experiment.number("yield-over-peak", 100 * yields[-1] / found["peak-stress"], ".0f")

    reversal = unloading(test, modulus)
    experiment.number("recovered", 1e3 * reversal["recovered"], ".2f")
    experiment.number("predicted", 1e3 * reversal["predicted"], ".2f")
    experiment.number(
        "recovered-ratio", reversal["recovered"] / reversal["predicted"], ".2f"
    )
    experiment.number("chord", reversal["chord"], ".0f")
    experiment.number("reverse-yield", reversal["reverse-yield"], ".0f")
    experiment.number(
        "reverse-drop", reversal["start-stress"] - reversal["reverse-yield"], ".0f"
    )

    cycle = loop(test)
    experiment.number("loop-work", cycle["work"], ".1f")
    experiment.number("loop-closing", cycle["closing"], ".1f")
    experiment.number("loop-gap-stress", cycle["gap-stress"], ".0f")
    experiment.number("loop-gap-strain", 1e6 * cycle["gap-strain"], ".0f")
    experiment.number("loop-rows", cycle["end"] - cycle["start"] + 1)
    experiment.number("ellipse-ratio", ellipse_check(experiment), ".1f")

    true_e, true_s = neck_true_stress(test)
    experiment.number("neck-true-stress", true_s, ".0f")
    experiment.number("neck-true-strain", true_e, ".3f")

    experiment.figure("fig-stress-strain", partial(draw_stress_strain, test, cycle))
    experiment.figure(
        "fig-elastic-regime", partial(draw_elastic_regime, test, result, yields[-1])
    )
    experiment.figure("fig-unloading", partial(draw_unloading, test, modulus, reversal))

    with experiment.capture("recovery-exercise"):
        recovery_exercise()
    with experiment.capture("load-cell-exercise"):
        load_cell_exercise(test)
    return experiment


if __name__ == "__main__":
    main(run)
