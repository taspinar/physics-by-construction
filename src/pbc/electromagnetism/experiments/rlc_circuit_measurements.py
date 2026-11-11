"""The experiment of the lesson "RLC circuit measurements".

A coil in parallel with a capacitor (``pbc.electromagnetism.circuits``): its
closed forms checked by a search on the circuit of the values printed on the
parts, and then the measured impedance spectrum of such a circuit (the
committed sample of the card ``bayreuth-rlc-impedance``): the highest
measured sample, the prediction of the printed values, a fit of R, L, and C
with its standard errors and residuals, the three characteristic
frequencies of the fit, and the fits of the two halves of the band as a
sensitivity of the model fit. Run it as a program to write the figures and
the numbers of the page:

    uv run --locked --no-dev python -m \\
        pbc.electromagnetism.experiments.rlc_circuit_measurements out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from scipy.optimize import brentq

from pbc.data import SAMPLES_DIR
from pbc.data.adapters import impedance_series
from pbc.data.fit import FitResult, fit_curve
from pbc.data.plotting import COLOURS, add_credit, label_status
from pbc.data.reference.bayreuth_rlc import Spectrum, load
from pbc.electromagnetism.circuits import CoilParallelCapacitor, impedance_peak
from pbc.experiment import Experiment, main

DATASET = "bayreuth-rlc-impedance"
# region: nominal
# The values printed on the parts, as the record gives them (its "9.7 mOhm"
# is a unit typo for 9.7 ohm, the dossier shows why), and their tolerance.
NOMINAL = CoilParallelCapacitor(resistance=9.7, inductance=5e-3, capacitance=2.2e-6)
TOLERANCE = 0.10  # the factory tolerance of each value
AMPLITUDE = 30e-3  # A, the amplitude of the current the instrument imposes
# endregion: nominal
NAMES = ("R", "L", "C")
UNITS = {"R": "ohm", "L": "mH", "C": "uF"}
SCALE = {"R": 1.0, "L": 1e-3, "C": 1e-6}  # from the fitted unit to SI
CREDIT = (
    "Data: Danzer, Plank, Ruether (Univ. Bayreuth), 'Impedance data for various "
    "electrochemical and electrical systems', Zenodo 10.5281/zenodo.10794584, "
    "v1.0.0, CC BY 4.0; file rlc_circuit.json, unmodified. Models and residuals: "
    "this lesson's code, not part of the record."
)


def hz(omega: float) -> float:
    """An angular frequency in rad/s as a frequency in Hz."""
    return float(omega) / (2 * np.pi)


def characteristic_frequencies(experiment: Experiment) -> float:
    """The closed forms of the phase zero and of the dynamic resistance
    against a root search on the circuit of the printed values, and the peak
    of |Z| by a bounded search; record the table and return the largest
    relative gap of the two closed forms."""
    tank = NOMINAL
    omega0 = tank.natural_frequency
    root = brentq(
        lambda w: tank.impedance(w).imag, 0.3 * omega0, omega0, xtol=1e-12 * omega0
    )
    at_root = abs(complex(tank.impedance(root)))
    peak = impedance_peak(tank)
    gap = max(
        abs(root / tank.phase_zero_frequency - 1),
        abs(at_root / tank.dynamic_resistance - 1),
    )
    experiment.table(
        "characteristic-frequencies",
        [
            ("1/(2 pi sqrt(LC)), undamped", f"{hz(omega0):.2f}", "", "Hz"),
            (
                "phase of Z zero",
                f"{hz(tank.phase_zero_frequency):.2f}",
                f"{hz(root):.2f}",
                "Hz",
            ),
            (
                "|Z| at the phase zero",
                f"{tank.dynamic_resistance:.2f}",
                f"{at_root:.2f}",
                "ohm",
            ),
            ("largest |Z|", "no closed form", f"{hz(peak):.2f}", "Hz"),
            (
                "largest |Z|, value",
                "",
                f"{abs(complex(tank.impedance(peak))):.2f}",
                "ohm",
            ),
        ],
        columns=[
            ("quantity", "", "s"),
            ("closed form", "", "s"),
            ("search", "", "s"),
            ("unit", "", "s"),
        ],
        caption="The circuit of the printed values (9.7 ohm, 5 mH, 2.2 uF): the "
        "closed forms against a root search for the phase zero and a bounded "
        "search for the largest |Z|.",
    )
    return gap


def load_spectrum() -> Spectrum:
    """The committed spectrum, in increasing frequency."""
    spectrum = load(SAMPLES_DIR / DATASET)
    order = np.argsort(spectrum.frequency)
    return Spectrum(spectrum.frequency[order], spectrum.impedance[order], spectrum.meta)


def measured_extremes(spectrum: Spectrum) -> dict:
    """What the samples say without a model: the highest |Z| and the two
    samples between which the measured phase changes sign."""
    f, z = spectrum.frequency, spectrum.impedance
    k = int(np.argmax(np.abs(z)))
    phase = np.angle(z)
    turn = int(np.flatnonzero((phase[:-1] > 0) & (phase[1:] <= 0))[0])
    return {
        "peak-frequency": float(f[k]),
        "peak-modulus": float(abs(z[k])),
        "turn-low": float(f[turn]),
        "turn-high": float(f[turn + 1]),
        "turn-low-deg": float(np.degrees(phase[turn])),
        "turn-high-deg": float(np.degrees(phase[turn + 1])),
        "step": float(np.median(f[1:] / f[:-1])),
    }


def circuit_of(result: FitResult) -> CoilParallelCapacitor:
    """The circuit of fitted values (R in ohm, L in mH, C in uF)."""
    return CoilParallelCapacitor(*(result.value(name) * SCALE[name] for name in NAMES))


def relative_residual(spectrum: Spectrum, tank: CoilParallelCapacitor) -> np.ndarray:
    """Z_model / Z_measured - 1 at every sample, complex."""
    omega = 2 * np.pi * spectrum.frequency
    return tank.impedance(omega) / spectrum.impedance - 1


def fit_impedance(spectrum: Spectrum, keep: np.ndarray | None = None) -> FitResult:
    """Fit R [ohm], L [mH], C [uF] to the real and imaginary parts of
    Z_model / Z_measured - 1, starting from the printed values: every sample
    weighs the same relative to its own |Z|."""
    keep = np.ones(spectrum.frequency.shape, bool) if keep is None else keep
    part = Spectrum(spectrum.frequency[keep], spectrum.impedance[keep], spectrum.meta)

    def model(_, r, inductance_mh, capacitance_uf):
        tank = CoilParallelCapacitor(r, inductance_mh * 1e-3, capacitance_uf * 1e-6)
        ratio = relative_residual(part, tank)
        return np.concatenate([ratio.real, ratio.imag])

    start = [
        NOMINAL.resistance,
        NOMINAL.inductance / SCALE["L"],
        NOMINAL.capacitance / SCALE["C"],
    ]
    target = np.zeros(2 * part.frequency.size)
    return fit_curve(model, np.arange(target.size), target, start, names=NAMES)


def fit_table(experiment: Experiment, result: FitResult) -> list[float]:
    """The fitted values with their standard errors beside the printed ones;
    record the table and return each value's distance from its printed
    value, as a fraction of it."""
    printed = {
        "R": NOMINAL.resistance,
        "L": NOMINAL.inductance / SCALE["L"],
        "C": NOMINAL.capacitance / SCALE["C"],
    }
    rows, distances = [], []
    for k, name in enumerate(NAMES):
        value, error = result.value(name), float(result.stderr[k])
        distance = value / printed[name] - 1
        distances.append(distance)
        rows.append(
            (
                name,
                UNITS[name],
                f"{value:.4g}",
                f"{error:.2g}",
                f"{printed[name]:g}",
                100 * distance,
            )
        )
    experiment.table(
        "fit",
        rows,
        columns=[
            ("value", "", "s"),
            ("unit", "", "s"),
            ("fitted", "", "s"),
            ("standard error", "", "s"),
            ("printed on the part", "", "s"),
            ("fitted against printed", "%", "+.1f"),
        ],
        caption="R, L, and C fitted to the 81 measured samples, with the standard "
        "errors from the scatter of the residuals, beside the values printed on "
        "the parts (factory tolerance 10 %).",
    )
    return distances


def fitted_frequencies(result: FitResult) -> dict:
    """The three characteristic frequencies of the fitted circuit in Hz, its
    quality factor, and its impedance at the phase zero in ohm."""
    tank = circuit_of(result)
    return {
        "f0": hz(tank.natural_frequency),
        "peak": hz(impedance_peak(tank)),
        "zero": hz(tank.phase_zero_frequency),
        "q": float(tank.quality_factor),
        "dynamic": float(tank.dynamic_resistance),
    }


def residual_summary(spectrum: Spectrum, result: FitResult) -> dict:
    """The size and the place of the residuals of the fit, and of the
    prediction of the printed values, in per cent."""
    fitted = relative_residual(spectrum, circuit_of(result))
    printed = relative_residual(spectrum, NOMINAL)

    def rms(r: np.ndarray) -> float:
        return float(100 * np.sqrt(np.mean(np.concatenate([r.real, r.imag]) ** 2)))

    worst = int(np.argmax(np.abs(fitted)))
    size = 100 * np.abs(fitted)
    return {
        "first": float(size[0]),
        "last": float(size[-1]),
        "least-at": float(spectrum.frequency[np.argmin(size)]),
        "rms": rms(fitted),
        "worst": float(100 * np.abs(fitted).max()),
        "worst-at": float(spectrum.frequency[worst]),
        "printed-rms": rms(printed),
        "printed-worst": float(100 * np.abs(printed).max()),
    }


def band_sensitivity(
    experiment: Experiment, spectrum: Spectrum, full: FitResult
) -> dict:
    """The fit repeated on the samples below and above the full fit's
    undamped resonance; record the table and return the range of the
    resonance and of R over the three fits."""
    f0 = hz(circuit_of(full).natural_frequency)
    below = spectrum.frequency < f0
    fits = [
        ("full band, 100 Hz to 10 kHz", int(below.size), full),
        (f"below {f0:.0f} Hz", int(below.sum()), fit_impedance(spectrum, below)),
        (f"above {f0:.0f} Hz", int((~below).sum()), fit_impedance(spectrum, ~below)),
    ]
    rows, resonances, resistances = [], [], []
    for name, points, result in fits:
        tank = circuit_of(result)
        resonances.append(hz(tank.natural_frequency))
        resistances.append(result.value("R"))
        rows.append(
            (
                name,
                points,
                resonances[-1],
                result.value("R"),
                result.value("L"),
                result.value("C"),
                tank.quality_factor,
            )
        )
    experiment.table(
        "band-sensitivity",
        rows,
        columns=[
            ("samples fitted", "", "s"),
            ("samples", "", "d"),
            ("1/(2 pi sqrt(LC))", "Hz", ".1f"),
            ("R", "ohm", ".3f"),
            ("L", "mH", ".3f"),
            ("C", "uF", ".4f"),
            ("Q", "", ".2f"),
        ],
        caption="The same fit on the whole band and on the samples below and above "
        "the resonance of the whole-band fit: a sensitivity of the model fit to "
        "the band, not an uncertainty of the measurement.",
    )
    return {
        "f0-low": min(resonances),
        "f0-high": max(resonances),
        "r-low": min(resistances),
        "r-high": max(resistances),
        "r-below": resistances[1],
        "r-above": resistances[2],
    }


def _mark(ax, x: float, style: str, label: str) -> None:
    ax.axvline(x, color="0.35", lw=0.9, ls=style, label=label)


def draw_impedance_fit(spectrum: Spectrum, result: FitResult) -> Figure:
    """The measured |Z| and phase against the circuit of the printed values
    and the fitted circuit, with the residuals of both."""
    modulus = impedance_series(spectrum, "modulus")
    phase = impedance_series(spectrum, "phase")
    dense = np.geomspace(spectrum.frequency[0], spectrum.frequency[-1], 400)
    models = {
        "model, printed values": (NOMINAL, ":", COLOURS[2]),
        "model, fitted values": (circuit_of(result), "--", COLOURS[1]),
    }
    fig, (top, middle, bottom) = plt.subplots(
        3,
        1,
        figsize=(6.4, 7.0),
        sharex=True,
        constrained_layout=True,
        gridspec_kw={"height_ratios": [1.3, 1.0, 1.0]},
    )
    measured = {"color": COLOURS[0], "marker": "o", "ms": 3.2, "ls": "none"}
    top.loglog(
        modulus.x,
        modulus.y,
        label=f"measured [{modulus.status}], no uncertainty per point given",
        **measured,
    )
    middle.semilogx(phase.x, phase.y, label=f"measured [{phase.status}]", **measured)
    for name, (tank, style, colour) in models.items():
        z = tank.impedance(2 * np.pi * dense)
        top.plot(
            dense,
            np.abs(z),
            ls=style,
            color=colour,
            lw=1.4,
            label=f"{name} [simulated]",
        )
        middle.plot(
            dense,
            np.degrees(np.angle(z)),
            ls=style,
            color=colour,
            lw=1.4,
            label=f"{name} [simulated]",
        )
        r = 100 * relative_residual(spectrum, tank)
        bottom.semilogx(
            spectrum.frequency,
            np.abs(r),
            ls=style,
            color=colour,
            lw=1.2,
            marker="." if style == "--" else None,
            ms=4,
            label=name,
        )
    middle.axhline(0, color="0.5", lw=0.8)
    top.set_ylabel("|Z| [ohm]")
    top.set_title("Impedance of a coil parallel to a capacitor: magnitude")
    top.legend(fontsize=7.5, loc="lower center")
    middle.set_ylabel("phase of Z [deg]")
    middle.set_title("Phase: inductive below the resonance, capacitive above")
    middle.legend(fontsize=7.5, loc="lower left")
    bottom.set_yscale("log")
    bottom.set_ylabel("residual [%]")
    bottom.set_xlabel("frequency [Hz]")
    bottom.set_title("Residual |Z_model / Z_measured - 1| of the two models")
    bottom.legend(fontsize=7.5, loc="upper left")
    add_credit(fig, CREDIT)
    label_status(fig, modulus.status)
    return fig


def draw_resonance_detail(
    spectrum: Spectrum, result: FitResult, measured: dict
) -> Figure:
    """The samples around the resonance on linear axes, the fitted model,
    and the measured maximum and the model's three frequencies marked."""
    tank = circuit_of(result)
    window = (spectrum.frequency > 1000) & (spectrum.frequency < 2400)
    modulus = impedance_series(spectrum, "modulus").select(1000, 2400)
    phase = impedance_series(spectrum, "phase").select(1000, 2400)
    assert modulus.x.size == int(window.sum())
    dense = np.linspace(1000, 2400, 500)
    z = tank.impedance(2 * np.pi * dense)
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(6.4, 5.4), sharex=True, constrained_layout=True
    )
    style = {"color": COLOURS[0], "marker": "o", "ms": 4.5, "ls": "none"}
    top.plot(
        modulus.x, modulus.y, label=f"measured samples [{modulus.status}]", **style
    )
    top.plot(
        dense,
        np.abs(z),
        "--",
        color=COLOURS[1],
        lw=1.4,
        label="model, fitted values [simulated]",
    )
    bottom.plot(phase.x, phase.y, label=f"measured samples [{phase.status}]", **style)
    bottom.plot(
        dense,
        np.degrees(np.angle(z)),
        "--",
        color=COLOURS[1],
        lw=1.4,
        label="model, fitted values [simulated]",
    )
    marks = [
        (measured["peak-frequency"], "-", "highest measured sample"),
        (
            hz(impedance_peak(tank)),
            "--",
            "largest |Z| of the model, at 1/(2 pi sqrt(LC))",
        ),
        (hz(tank.phase_zero_frequency), "-.", "phase zero of the model"),
    ]
    for x, line, label in marks:
        _mark(top, x, line, label)
        _mark(bottom, x, line, "_" + label)
    bottom.axhline(0, color="0.5", lw=0.8)
    top.set_ylabel("|Z| [ohm]")
    top.set_title("Around the resonance: the sweep against the fitted model")
    top.legend(fontsize=7.5, loc="upper right")
    bottom.set_ylabel("phase of Z [deg]")
    bottom.set_xlabel("frequency [Hz]")
    bottom.set_title("Phase around the resonance")
    bottom.legend(fontsize=7.5, loc="upper right")
    add_credit(fig, CREDIT + f" Steps: {modulus.disclosure()}.")
    label_status(fig, modulus.status)
    return fig


def tank_exercise() -> None:
    """Exercise 1: a coil of 10 mH with 20 ohm parallel to 1 uF."""
    tank = CoilParallelCapacitor(20.0, 10e-3, 1e-6)
    print(f"undamped resonance: {hz(tank.natural_frequency):.1f} Hz")
    print(f"quality factor: {tank.quality_factor:.2f}")
    print(f"phase zero: {hz(tank.phase_zero_frequency):.1f} Hz")
    print(f"impedance there: {tank.dynamic_resistance:.0f} ohm")


def sweep_exercise() -> None:
    """Exercise 2: how far the highest sample of a sweep of 40 points per
    decade can lie from the true peak."""
    ratio = 10 ** (1 / 40)
    print(f"ratio of neighbouring frequencies: {ratio:.4f}")
    print(f"step near 1.5 kHz: {1500 * (ratio - 1):.0f} Hz")
    print(f"largest distance of the nearest sample: {100 * (np.sqrt(ratio) - 1):.1f} %")


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    gap = characteristic_frequencies(experiment)
    experiment.number("closed-form-gap", "below 1e-9" if gap < 1e-9 else f"{gap:.1e}")
    experiment.number("nominal-f0", hz(NOMINAL.natural_frequency), ".0f")
    experiment.number("nominal-q", NOMINAL.quality_factor, ".2f")

    spectrum = load_spectrum()
    measured = measured_extremes(spectrum)
    experiment.number("samples", spectrum.frequency.size)
    experiment.number("f-min", spectrum.frequency[0], ".0f")
    experiment.number("f-max", spectrum.frequency[-1], ".0f")
    experiment.number("step", 100 * (measured["step"] - 1), ".1f")
    experiment.number("peak-frequency", measured["peak-frequency"], ".1f")
    experiment.number("peak-modulus", measured["peak-modulus"], ".0f")
    experiment.number("turn-low", measured["turn-low"], ".1f")
    experiment.number("turn-high", measured["turn-high"], ".1f")
    experiment.number("turn-low-deg", measured["turn-low-deg"], "+.0f")
    experiment.number("turn-high-deg", measured["turn-high-deg"], "+.0f")
    experiment.number(
        "peak-over-low", measured["peak-modulus"] / abs(spectrum.impedance[0]), ".0f"
    )
    experiment.number("voltage", AMPLITUDE * measured["peak-modulus"], ".1f")

    result = fit_impedance(spectrum)
    distances = fit_table(experiment, result)
    experiment.number("largest-distance", 100 * max(map(abs, distances)), ".0f")
    for k, name in enumerate(NAMES):
        experiment.number(f"{name.lower()}-fit", result.value(name), ".4g")
        experiment.number(f"{name.lower()}-err", result.stderr[k], ".2g")
    experiment.number(
        "fit-warnings", "; ".join(result.warnings) if result.warnings else "none"
    )
    experiment.number("lc-correlation", result.correlation[1, 2], ".2f")
    found = fitted_frequencies(result)
    experiment.number("fit-f0", found["f0"], ".1f")
    experiment.number("fit-peak", found["peak"], ".1f")
    experiment.number("fit-zero", found["zero"], ".1f")
    experiment.number("fit-q", found["q"], ".2f")
    experiment.number("fit-dynamic", found["dynamic"], ".0f")
    experiment.number(
        "peak-above-model",
        100 * (measured["peak-frequency"] / found["peak"] - 1),
        ".1f",
    )

    residuals = residual_summary(spectrum, result)
    experiment.number("rms", residuals["rms"], ".1f")
    experiment.number("worst", residuals["worst"], ".1f")
    experiment.number("worst-at", residuals["worst-at"], ".0f")
    experiment.number("residual-first", residuals["first"], ".1f")
    experiment.number("residual-last", residuals["last"], ".1f")
    experiment.number("residual-min-at", residuals["least-at"], ".0f")
    experiment.number("printed-rms", residuals["printed-rms"], ".1f")
    experiment.number("printed-worst", residuals["printed-worst"], ".0f")

    spread = band_sensitivity(experiment, spectrum, result)
    experiment.number("band-f0-low", spread["f0-low"], ".1f")
    experiment.number("band-f0-high", spread["f0-high"], ".1f")
    experiment.number(
        "band-f0-spread", 100 * (spread["f0-high"] / spread["f0-low"] - 1), ".1f"
    )
    experiment.number("band-r-below", spread["r-below"], ".2f")
    experiment.number("band-r-above", spread["r-above"], ".2f")

    experiment.figure(
        "fig-impedance-fit", partial(draw_impedance_fit, spectrum, result)
    )
    experiment.figure(
        "fig-resonance-detail",
        partial(draw_resonance_detail, spectrum, result, measured),
    )

    with experiment.capture("tank-exercise"):
        tank_exercise()
    with experiment.capture("sweep-exercise"):
        sweep_exercise()
    return experiment


if __name__ == "__main__":
    main(run)
