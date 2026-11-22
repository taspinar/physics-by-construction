"""The F140 pilot: a series RLC circuit measured with an Analog Discovery 3.

Status of the figure: *processed*. The record is the raw traces of the
pilot's two live sweeps (``raw.csv``: every sample of channel 1 at the
generator W1 and of channel 2, per point), with the run record of each
(``run.json``). This module reads the phasor of each channel from the samples
(a least-squares fit of a cosine, a sine, and a constant, because the AD3's
divided sample clock does not give whole periods), and from them the gain and
the phase of channel 2 over channel 1. That step is this module's, not the
record's.

The two sweeps, both at 1 V from 5 kHz to 200 kHz, on the owner's breadboard
(R 100 ohm at 1 %, L 1 mH, C 10 nF, nominal; #508, 2026-11-22):

- ``capacitor``: channel 2 at the L-C node, so the response is the
  capacitor's voltage, the frequency response the protocol measures;
- ``rl-node``: channel 2 moved to the R-L node, so the response is the
  voltage over the coil and the capacitor together. With the resistor's
  nominal value it gives the impedance of the rest of the circuit,
  ``Z = R H / (1 - H)``, whose reactance ``w L - 1/(w C)`` gives L and C
  apart from the capacitor sweep, and whose real part is the loss of the
  coil and the wiring, ``R_L``.

The model drawn beside the measurement is the closed form of the series
circuit, ``V_C / V_S = 1 / (1 - w^2 L C + j w (R + R_L) C)``: once with the
nominal parts and no loss, once with the parts measured apart (L and C from
the reactance, ``R_L`` the mean of the real part within a factor 1.5 of the
resonance, where ``1 - H`` is not small). The loss of the coil grows with the
frequency (core and skin losses), so no constant ``R_L`` fits the whole band;
the residual panels show where the model with constant parts departs.

The uncertainty per point is the noise of the two phasor fits (one standard
deviation, from the residual scatter of each fit); the AD3's channel gain and
phase accuracy is the factory calibration, not documented in the record, and
not included. The uncertainties of L, C, and ``R_L`` combine the scatter of
the reactance fit with the resistor's 1 % tolerance, to which ``Z`` is
proportional.
"""

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from pbc.data.figure_provenance import RESIDUAL, FigureProvenance, role
from pbc.data.plotting import COLOURS

SWEEPS = ("capacitor", "rl-node")
RAW = "raw.csv"
RUN = "run.json"
COLUMNS = ("point", "frequency_hz", "amplitude_v", "t_s", "source_v", "response_v")
# The owner's parts, nominal (#508, 2026-11-22); the resistor's tolerance.
NOMINAL = {"R": 100.0, "L": 1e-3, "C": 10e-9}  # ohm, H, F
R_TOLERANCE = 0.01
# R_L is read where 1 - H is not small: within this factor of the resonance.
LOSS_BAND = 1.5
REFERENCE = FigureProvenance(
    status="processed",
    dataset="ad3-rlc-pilot",
    combines=("simulated",),
    processing="The pilot's raw traces (raw.csv of the sweeps capacitor and"
    " rl-node), unmodified; the phasor fits, the gain and phase, the parts"
    " measured apart, the closed-form model, and the residuals: this module's"
    " code (pbc.data.reference.ad3_rlc_pilot), not part of the record.",
)


@dataclass(frozen=True)
class Trace:
    """One point of a sweep: its samples as recorded."""

    frequency_hz: float
    amplitude_v: float
    t: np.ndarray  # s
    source: np.ndarray  # V, channel 1 at W1
    response: np.ndarray  # V, channel 2


@dataclass(frozen=True)
class Response:
    """The frequency response of a sweep, one entry per point, in the
    order of the frequency."""

    frequency_hz: np.ndarray
    ratio: np.ndarray  # complex V_response / V_source
    gain_sigma: np.ndarray  # one standard deviation of |ratio|
    phase_sigma_deg: np.ndarray

    @property
    def gain(self) -> np.ndarray:
        return np.abs(self.ratio)

    @property
    def phase_deg(self) -> np.ndarray:
        """In (-270, 90], as the protocol reports it."""
        phase = np.degrees(np.angle(self.ratio))
        return np.where(phase > 90.0, phase - 360.0, phase)


@dataclass(frozen=True)
class Parts:
    """L, C, and the coil's loss R_L measured apart, with one standard
    deviation each, from the R-L node sweep."""

    inductance_h: float
    inductance_sigma: float
    capacitance_f: float
    capacitance_sigma: float
    loss_ohm: float
    loss_sigma: float

    @property
    def f0_hz(self) -> float:
        return 1.0 / (2.0 * math.pi * math.sqrt(self.inductance_h * self.capacitance_f))

    @property
    def q(self) -> float:
        total = NOMINAL["R"] + self.loss_ohm
        return math.sqrt(self.inductance_h / self.capacitance_f) / total


def _column(block: list[dict[str, str]], name: str) -> np.ndarray:
    return np.array([float(row[name]) for row in block])


def read_traces(path: Path) -> list[Trace]:
    """The points of a ``raw.csv`` export of the physics lab, in the order
    recorded; a file with other columns is refused."""
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise ValueError(f"{path}: the columns are not {', '.join(COLUMNS)}")
        rows: dict[int, list[dict[str, str]]] = {}
        for row in reader:
            rows.setdefault(int(row["point"]), []).append(row)
    traces = []
    for number in sorted(rows):
        block = rows[number]
        traces.append(
            Trace(
                frequency_hz=float(block[0]["frequency_hz"]),
                amplitude_v=float(block[0]["amplitude_v"]),
                t=_column(block, "t_s"),
                source=_column(block, "source_v"),
                response=_column(block, "response_v"),
            )
        )
    return traces


def read_run(path: Path) -> dict:
    """The run record of a sweep (``run.json``)."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def phasor(signal: np.ndarray, t: np.ndarray, omega: float) -> tuple[complex, float]:
    """The phasor of ``signal`` at ``omega`` by least squares over a cosine,
    a sine, and a constant, and the standard deviation of its real and of
    its imaginary part from the residual scatter."""
    design = np.column_stack([np.cos(omega * t), np.sin(omega * t), np.ones(t.size)])
    coefficients, *_ = np.linalg.lstsq(design, signal, rcond=None)
    residual = signal - design @ coefficients
    variance = float(residual @ residual) / (t.size - 3)
    covariance = variance * np.linalg.inv(design.T @ design)
    sigma = math.sqrt(0.5 * (covariance[0, 0] + covariance[1, 1]))
    return complex(coefficients[0], -coefficients[1]), sigma


def response(data_dir: Path, sweep: str) -> Response:
    """The frequency response of ``sweep``, sorted by frequency."""
    traces = sorted(
        read_traces(Path(data_dir) / sweep / RAW), key=lambda x: x.frequency_hz
    )
    ratio, gain_sigma, phase_sigma = [], [], []
    for trace in traces:
        omega = 2.0 * math.pi * trace.frequency_hz
        source, s_sigma = phasor(trace.source, trace.t, omega)
        answer, r_sigma = phasor(trace.response, trace.t, omega)
        h = answer / source
        # first order: the relative error of a ratio of two phasors
        relative = math.hypot(s_sigma / abs(source), r_sigma / abs(answer))
        ratio.append(h)
        gain_sigma.append(abs(h) * relative)
        phase_sigma.append(math.degrees(relative))
    return Response(
        np.array([t.frequency_hz for t in traces]),
        np.array(ratio),
        np.array(gain_sigma),
        np.array(phase_sigma),
    )


def rest_impedance(rl_node: Response, resistance: float = NOMINAL["R"]) -> np.ndarray:
    """The impedance of the coil and the capacitor in series from the R-L
    node sweep: ``Z = R H / (1 - H)`` (ohm, complex)."""
    h = rl_node.ratio
    return resistance * h / (1.0 - h)


def parts_apart(data_dir: Path) -> Parts:
    """L and C from the reactance of the R-L node sweep, ``w L - 1/(w C)``,
    by least squares; R_L the mean real part within ``LOSS_BAND`` of the
    resonance. Each with the scatter of its estimate and the resistor's
    tolerance in quadrature."""
    rl = response(data_dir, "rl-node")
    z = rest_impedance(rl)
    omega = 2.0 * math.pi * rl.frequency_hz
    design = np.column_stack([omega, -1.0 / omega])
    (inductance, elastance), *_ = np.linalg.lstsq(design, z.imag, rcond=None)
    residual = z.imag - design @ (inductance, elastance)
    variance = float(residual @ residual) / (omega.size - 2)
    covariance = variance * np.linalg.inv(design.T @ design)
    capacitance = 1.0 / elastance
    f0 = 1.0 / (2.0 * math.pi * math.sqrt(inductance * capacitance))
    near = (rl.frequency_hz > f0 / LOSS_BAND) & (rl.frequency_hz < f0 * LOSS_BAND)
    loss = z.real[near]
    # Z is proportional to R: L and R_L scale with it, C inversely.
    return Parts(
        inductance_h=float(inductance),
        inductance_sigma=float(
            inductance
            * math.hypot(math.sqrt(covariance[0, 0]) / inductance, R_TOLERANCE)
        ),
        capacitance_f=float(capacitance),
        capacitance_sigma=float(
            capacitance
            * math.hypot(math.sqrt(covariance[1, 1]) / elastance, R_TOLERANCE)
        ),
        loss_ohm=float(loss.mean()),
        loss_sigma=float(math.hypot(loss.std(ddof=1), R_TOLERANCE * loss.mean())),
    )


def capacitor_ratio(
    frequency_hz: np.ndarray, resistance: float, inductance: float, capacitance: float
) -> np.ndarray:
    """V_C / V_S of a series circuit with total series resistance
    ``resistance``: the closed form the model curves draw."""
    w = 2.0 * math.pi * np.asarray(frequency_hz, dtype=float)
    return 1.0 / (
        1.0 - w**2 * inductance * capacitance + 1j * w * resistance * capacitance
    )


def models(parts: Parts) -> dict[str, tuple[float, float, float]]:
    """The two models: (total series resistance, L, C)."""
    return {
        "closed form, nominal parts, no coil loss": (
            NOMINAL["R"],
            NOMINAL["L"],
            NOMINAL["C"],
        ),
        "closed form, parts measured apart": (
            NOMINAL["R"] + parts.loss_ohm,
            parts.inductance_h,
            parts.capacitance_f,
        ),
    }


def _phase(ratio: np.ndarray) -> np.ndarray:
    phase = np.degrees(np.angle(ratio))
    return np.where(phase > 90.0, phase - 360.0, phase)


def make_figure(data_dir: Path) -> plt.Figure:
    measured = response(data_dir, "capacitor")
    parts = parts_apart(data_dir)
    f = measured.frequency_hz
    dense = np.geomspace(f.min(), f.max(), 400)
    fig, axes = plt.subplots(2, 2, figsize=(10, 8), constrained_layout=True)
    (ax_gain, ax_phase), (ax_gres, ax_pres) = axes
    points = {"color": COLOURS[0], "marker": "o", "ms": 4, "ls": "none", "capsize": 2}
    styles = ({"ls": "--", "lw": 1.3}, {"ls": ":", "lw": 1.8})

    bars = ax_gain.errorbar(
        f, measured.gain, yerr=measured.gain_sigma,
        label="measured, 1 s.d. of the phasor fits", **points,
    )  # fmt: skip
    role(bars, "processed")
    bars = ax_phase.errorbar(
        f, measured.phase_deg, yerr=measured.phase_sigma_deg,
        label="measured", **points,
    )  # fmt: skip
    role(bars, "processed")
    markers = ("s", "^")
    for k, (name, (r, inductance, c)) in enumerate(models(parts).items()):
        colour = COLOURS[k + 1]
        curve = capacitor_ratio(dense, r, inductance, c)
        (line,) = ax_gain.loglog(
            dense, np.abs(curve), color=colour, label=name, **styles[k]
        )
        role(line, "simulated")
        (line,) = ax_phase.semilogx(
            dense, _phase(curve), color=colour, label=name, **styles[k]
        )
        role(line, "simulated")
        at = capacitor_ratio(f, r, inductance, c)
        (line,) = ax_gres.semilogx(
            f, np.abs(at) - measured.gain, color=colour, marker=markers[k], ms=4,
            label=name, **styles[k],
        )  # fmt: skip
        role(line, RESIDUAL)
        (line,) = ax_pres.semilogx(
            f, _phase(at) - measured.phase_deg, color=colour, marker=markers[k],
            ms=4, label=name, **styles[k],
        )  # fmt: skip
        role(line, RESIDUAL)
    ax_gain.set_xscale("log")
    ax_gain.set_yscale("log")
    ax_phase.set_xscale("log")
    ax_gain.set_xlabel("frequency [Hz]")
    ax_gain.set_ylabel("gain |V_C / V_S| [V/V]")
    ax_gain.set_title(
        "Processed: the measured peak is lower and broader",
        fontsize=10,
    )
    ax_gain.legend(fontsize=8, loc="lower left")
    ax_phase.axhline(-90.0, color="0.5", lw=0.8)
    ax_phase.set_xlabel("frequency [Hz]")
    ax_phase.set_ylabel("phase of V_C / V_S [deg]")
    ax_phase.set_title(
        f"Processed: parts apart give f0 {parts.f0_hz / 1e3:.1f} kHz, Q {parts.q:.2f}",
        fontsize=10,
    )
    ax_phase.legend(fontsize=8, loc="lower left")
    for ax, quantity, unit in (
        (ax_gres, "gain", "V/V"),
        (ax_pres, "phase", "deg"),
    ):
        ax.axhline(0.0, color="0.5", lw=0.8)
        ax.set_xlabel("frequency [Hz]")
        ax.set_ylabel(f"residual of the {quantity}, model - measured [{unit}]")
        ax.legend(fontsize=8)
    ax_gres.set_title("Residuals of the gain: largest at the resonance", fontsize=10)
    ax_pres.set_title(
        "Residuals of the phase: neither model fits the band", fontsize=10
    )
    return fig
