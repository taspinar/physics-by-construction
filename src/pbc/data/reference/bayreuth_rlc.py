"""Bayreuth RLC circuit: measured impedance and a fit of C parallel to (R + jwL).

Status of the figure: *processed* (the potentiostat's impedance spectrum,
exported by the creators' MATLAB package; the step from the recorded voltage
and current to these values is not documented). The fitted curve is drawn
apart from the measurement, as a model, with its residuals.

The record gives no uncertainty per point and no calibration. The fit takes its
standard errors from the scatter of the residuals; ``band_split`` fits below
and above the resonance separately, a sensitivity analysis of the model fit
(the structured residuals show the model, not the scatter, to limit it). It is
no bound on the unknown calibration or instrument error of the record.

Three frequencies are kept apart: the highest measured |Z| (a sample of the
40-per-decade sweep), the maximum of the fitted |Z| (``model_peak``), and the
zero crossing of the fitted phase (``model_phase_zero``).
"""

import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import brentq, minimize_scalar

from pbc.data.fit import FitResult, fit_curve
from pbc.data.plotting import COLOURS, add_credit, label_status

FILE = "rlc_circuit.json"
FIELDS = (
    "class_",
    "meta_",
    "f",
    "omega",
    "z",
    "z_real",
    "z_imag",
    "z_modulus",
    "z_phase",
)
# Nominal values of the record: 2.2 uF foil capacitor, lossy inductor 5 mH with
# "9.7 mOhm" (a typo for 9.7 Ohm, which the fit shows), factory tolerance 10 %.
NOMINAL = {"R": 9.7, "L": 5.0, "C": 2.2}  # Ohm, mH, uF
NAMES = ("R", "L", "C")


@dataclass(frozen=True)
class Spectrum:
    frequency: np.ndarray  # Hz, as in the file (descending)
    impedance: np.ndarray  # Ohm, complex, Z = Re Z + j Im Z
    meta: dict


def read_impedance(path: Path) -> Spectrum:
    """Read the ``Impedance`` JSON export of the creators' MATLAB package."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("class_") != "Impedance":
        raise ValueError(f"{path}: not an Impedance export")
    frequency = np.asarray(data["f"], dtype=float)
    impedance = np.asarray(data["z_real"], float) + 1j * np.asarray(
        data["z_imag"], float
    )
    if frequency.shape != impedance.shape:
        raise ValueError(f"{path}: f and z differ in length")
    return Spectrum(frequency, impedance, data["meta_"])


def load(data_dir: Path) -> Spectrum:
    return read_impedance(Path(data_dir) / FILE)


def impedance(
    frequency: np.ndarray, r: float, inductance: float, c: float
) -> np.ndarray:
    """Z of a capacitor ``c`` [F] parallel to an inductor ``inductance`` [H] with
    series resistance ``r`` [Ohm]: the EM5 parallel resonant circuit."""
    w = 2 * np.pi * np.asarray(frequency, dtype=float)
    branch = r + 1j * w * inductance
    return branch / (1 + 1j * w * c * branch)


def fit(spectrum: Spectrum, band: np.ndarray | None = None) -> FitResult:
    """Fit R [Ohm], L [mH], C [uF] to the relative complex residual.

    Every point weighs the same relative to its own |Z|, so the points near the
    resonance, where |Z| is 70 times larger than at 100 Hz, do not dominate.
    The real and the imaginary part are two residuals per point.
    """
    keep = np.ones(spectrum.frequency.shape, bool) if band is None else band
    f, z = spectrum.frequency[keep], spectrum.impedance[keep]

    def model(_, r, inductance_mh, c_uf):
        ratio = impedance(f, r, inductance_mh * 1e-3, c_uf * 1e-6) / z
        return np.concatenate([ratio.real, ratio.imag])

    target = np.concatenate([np.ones(f.size), np.zeros(f.size)])
    return fit_curve(
        model,
        np.arange(target.size),
        target,
        [NOMINAL[n] for n in NAMES],
        names=NAMES,
    )


def parameters(result: FitResult) -> tuple[float, float, float]:
    """R [Ohm], L [H], C [F] of a fit."""
    return result.value("R"), result.value("L") * 1e-3, result.value("C") * 1e-6


def resonance(result: FitResult) -> tuple[float, float]:
    """Undamped resonance 1/(2 pi sqrt(LC)) [Hz] and quality factor sqrt(L/C)/R."""
    r, inductance, c = parameters(result)
    return 1 / (2 * np.pi * np.sqrt(inductance * c)), np.sqrt(inductance / c) / r


def model_peak(result: FitResult) -> float:
    """Frequency [Hz] of the maximum of the fitted |Z|."""
    f0, _ = resonance(result)
    found = minimize_scalar(
        lambda f: -abs(impedance(f, *parameters(result))),
        bounds=(0.8 * f0, 1.2 * f0),
        method="bounded",
        options={"xatol": 1e-3},
    )
    return float(found.x)


def model_phase_zero(result: FitResult) -> float:
    """Frequency [Hz] where the fitted phase turns from inductive to capacitive."""
    f0, _ = resonance(result)
    phase = lambda f: np.angle(impedance(f, *parameters(result)))  # noqa: E731
    return float(brentq(phase, 0.5 * f0, f0, xtol=1e-6))


def measured_peak(spectrum: Spectrum) -> float:
    """Frequency [Hz] of the sample with the highest measured |Z|."""
    return float(spectrum.frequency[np.argmax(np.abs(spectrum.impedance))])


def relative_residual(spectrum: Spectrum, result: FitResult) -> np.ndarray:
    """Complex (model - measurement) / measurement at every point."""
    return impedance(spectrum.frequency, *parameters(result)) / spectrum.impedance - 1


def band_split(spectrum: Spectrum) -> dict[str, FitResult]:
    """Separate fits below and above the resonance of the full fit: a
    sensitivity analysis of the model fit, not an uncertainty of the record."""
    f0, _ = resonance(fit(spectrum))
    below = spectrum.frequency < f0
    return {
        "below": fit(spectrum, below),
        "above": fit(spectrum, ~below),
    }


def make_figure(data_dir: Path) -> plt.Figure:
    spectrum = load(data_dir)
    result = fit(spectrum)
    f0, q = resonance(result)
    peak, zero, highest = (
        model_peak(result),
        model_phase_zero(result),
        measured_peak(spectrum),
    )
    f = spectrum.frequency
    z = spectrum.impedance
    dense = np.geomspace(f.min(), f.max(), 600)
    model = impedance(dense, *parameters(result))
    fig, axes = plt.subplots(2, 2, figsize=(10, 8), constrained_layout=True)
    (ax_mag, ax_phase), (ax_nyq, ax_res) = axes
    measured = {"color": COLOURS[0], "marker": "o", "ms": 3.5, "ls": "none"}
    fitted = {"color": COLOURS[1], "ls": "--", "lw": 1.4}
    fit_label = (
        f"fit: R = {result.value('R'):.2f} Ohm, L = {result.value('L'):.3f} mH, "
        f"C = {result.value('C'):.3f} uF"
    )

    ax_mag.loglog(
        f, np.abs(z), label="measured (no uncertainty per point given)", **measured
    )
    ax_mag.loglog(dense, np.abs(model), label=fit_label, **fitted)
    ax_mag.axvline(
        peak, color="0.5", lw=0.8, ls=":", label=f"maximum of the fit: {peak:.0f} Hz"
    )
    ax_mag.set_xlabel("frequency [Hz]")
    ax_mag.set_ylabel("|Z| [Ohm]")
    ax_mag.set_title(
        f"Processed: highest measured |Z| at {highest:.0f} Hz; "
        f"fit peaks at {peak:.0f} Hz (Q = {q:.1f})",
        fontsize=10,
    )
    ax_mag.legend(fontsize=8, loc="lower center")

    ax_phase.semilogx(f, np.degrees(np.angle(z)), label="measured", **measured)
    ax_phase.semilogx(dense, np.degrees(np.angle(model)), label="fit", **fitted)
    ax_phase.axhline(0, color="0.5", lw=0.8)
    ax_phase.axvline(
        zero, color="0.5", lw=0.8, ls=":", label=f"zero of the fit: {zero:.0f} Hz"
    )
    ax_phase.set_xlabel("frequency [Hz]")
    ax_phase.set_ylabel("phase of Z [deg]")
    ax_phase.set_title(
        f"Processed: fitted phase turns capacitive at {zero:.0f} Hz", fontsize=10
    )
    ax_phase.legend(fontsize=8)

    ax_nyq.plot(z.real, -z.imag, label="measured", **measured)
    ax_nyq.plot(model.real, -model.imag, label="fit", **fitted)
    ax_nyq.set_aspect("equal")
    ax_nyq.set_xlabel("Re Z [Ohm]")
    ax_nyq.set_ylabel("-Im Z [Ohm]")
    ax_nyq.set_title("Processed: impedance plane (Nyquist)")
    ax_nyq.legend(fontsize=8)

    residual = relative_residual(spectrum, result) * 100
    ax_res.semilogx(f, residual.real, color=COLOURS[2], marker=".", label="real part")
    ax_res.semilogx(
        f,
        residual.imag,
        color=COLOURS[3],
        marker="x",
        ms=4,
        ls="--",
        label="imaginary part",
    )
    ax_res.axhline(0, color="0.5", lw=0.8)
    ax_res.axvline(
        f0, color="0.5", lw=0.8, ls=":", label=f"1/(2 pi sqrt(LC)) = {f0:.0f} Hz"
    )
    ax_res.set_xlabel("frequency [Hz]")
    ax_res.set_ylabel("residual Z_fit / Z_measured - 1 [%]")
    ax_res.set_title("Residuals: structured, largest at the resonance")
    ax_res.legend(fontsize=8)
    add_credit(
        fig,
        "Data: Danzer, Plank, Ruether (Univ. Bayreuth), 'Impedance data for various "
        "electrochemical and electrical systems', Zenodo 10.5281/zenodo.10794584, "
        "v1.0.0, CC BY 4.0; file rlc_circuit.json, unmodified. Fit and residuals: "
        "this figure's code (pbc.data.reference.bayreuth_rlc), not part of the record.",
    )
    label_status(fig, "processed")
    return fig
