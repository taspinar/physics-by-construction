"""NPL on-wafer attenuators: transmission, reflection, passivity, and cross-check.

Status of the figure: *calibrated* (VNA S-parameters after multiline TRL).
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from pbc.data.figure_provenance import REFERENCE as REFERENCE_ROLE
from pbc.data.figure_provenance import FigureProvenance, role
from pbc.data.touchstone import Network, read_touchstone

FILES = {
    "coaxial, 3 dB pad": "coaxial_3dB_attenuator_0601_CORR.s2p",
    "coaxial, 6 dB pad": "coaxial_6dB_attenuator_0602_CORR.s2p",
    "coaxial, 10 dB pad": "coaxial_10dB_attenuator_0603_CORR.s2p",
    "single sweep, 3 dB pad": "broadband_3dB_attenuator_0601_CORR.s2p",
}
COLORS = ["#0072B2", "#009E73", "#CC79A7", "#D55E00"]
# The provenance of the reference figure (Issue #531): its status and credit
# at no place on the chart, in its PNG's record, from the card.
REFERENCE = FigureProvenance(
    status="calibrated",
    dataset="npl-onwafer-sparameters",
    combines=("processed",),
    processing="The record's calibrated (_CORR, multiline TRL) S2P files of the"
    " four sweeps, unmodified; the largest singular value of S and the difference"
    " of the two instruments on the 3 dB pad: the reference figure's code, not"
    " part of the record.",
)


def load(data_dir: Path) -> dict[str, Network]:
    return {name: read_touchstone(Path(data_dir) / f) for name, f in FILES.items()}


def db(x: np.ndarray) -> np.ndarray:
    return 20 * np.log10(np.abs(x))


def largest_singular_value(network: Network) -> np.ndarray:
    """Largest singular value of S at each frequency; a passive device has <= 1."""
    return np.linalg.svd(network.s, compute_uv=False)[:, 0]


def reciprocity_error(network: Network) -> np.ndarray:
    """|S21 - S12| at each frequency; a reciprocal device has 0."""
    return np.abs(network.s[:, 1, 0] - network.s[:, 0, 1])


def cross_check_db(single: Network, coaxial: Network) -> tuple[np.ndarray, np.ndarray]:
    """Frequencies of the coaxial sweep and |S21| differences in dB there."""
    s21 = np.interp(
        coaxial.frequency,
        single.frequency,
        np.abs(single.s[:, 1, 0]),
    )
    return coaxial.frequency, 20 * np.log10(s21 / np.abs(coaxial.s[:, 1, 0]))


def make_figure(data_dir: Path) -> plt.Figure:
    networks = load(data_dir)
    fig, axes = plt.subplots(2, 2, figsize=(10, 8), constrained_layout=True)
    (ax_s21, ax_gamma), (ax_sv, ax_diff) = axes
    for (name, net), color in zip(networks.items(), COLORS, strict=True):
        ghz = net.frequency / 1e9
        (line,) = ax_s21.plot(ghz, db(net.s[:, 1, 0]), label=name, color=color)
        role(line, "calibrated")
        gamma = net.s[:, 0, 0]
        (line,) = ax_gamma.plot(gamma.real, gamma.imag, label=name, color=color, lw=1)
        role(line, "calibrated")
        (line,) = ax_sv.plot(ghz, largest_singular_value(net), label=name, color=color)
        role(line, "processed")
    angle = np.linspace(0, 2 * np.pi, 200)
    ax_gamma.plot(np.cos(angle), np.sin(angle), color="0.5", lw=0.8)
    ax_gamma.set_aspect("equal")
    ax_gamma.set_xlim(-0.6, 1.05)
    ax_gamma.set_ylim(-0.6, 0.6)
    ax_gamma.set_xlabel("Re S11 [1]")
    ax_gamma.set_ylabel("Im S11 [1]")
    ax_gamma.legend(fontsize=8, loc="lower left")
    ax_gamma.set_title(
        "Calibrated: input reflection in the reflection-coefficient plane"
    )
    ax_s21.set_xlabel("frequency [GHz]")
    ax_s21.set_ylabel("|S21| [dB]")
    ax_s21.set_title("Calibrated: transmission of three attenuators")
    ax_s21.legend(fontsize=8)
    # A limit drawn for comparison: a reference, in any style (Issue #531).
    role(
        ax_sv.axhline(1, color="k", linestyle="--", label="passivity limit"),
        REFERENCE_ROLE,
    )
    ax_sv.set_xlabel("frequency [GHz]")
    ax_sv.set_ylabel("largest singular value of S [1]")
    ax_sv.set_title("Consistency check: passive means <= 1 (50 ohm reference)")
    ax_sv.set_ylim(0, 1.1)
    ax_sv.legend(fontsize=8, loc="lower left")
    single = networks["single sweep, 3 dB pad"]
    coaxial = networks["coaxial, 3 dB pad"]
    freq, diff = cross_check_db(single, coaxial)
    (line,) = ax_diff.plot(freq / 1e9, diff, color=COLORS[3])
    role(line, "processed")
    ax_diff.axhline(0, color="0.5", lw=0.8)
    ax_diff.set_xlabel("frequency [GHz]")
    ax_diff.set_ylabel("single sweep minus coaxial, |S21| [dB]")
    ax_diff.set_title("Two instruments, same 3 dB pad (2.5-50 GHz)")
    return fig
