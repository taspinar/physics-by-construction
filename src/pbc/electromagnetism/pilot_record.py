"""The record of the physical pilot of the Autonomous Physics Lab, as the
capstone SA9 shows it: the declared dataset ``ad3-rlc-pilot`` replayed by
the recorded adapter, and its capacitor sweep drawn against the closed form
of the parts' labels.

It is a module apart from the capstone's experiment
(``pbc.electromagnetism.experiments.autonomous_physics_lab``) so that the
figures of that experiment which use no data are not made from a dataset
(``docs/authoring.md``, "Agent lessons", the advice for a measured picture).
Nothing here measures anything: the sample is the committed record, and the
replay asks the device nothing.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.data import SAMPLES_DIR
from pbc.data.figure_provenance import RESIDUAL, role
from pbc.data.plotting import COLOURS
from pbc.data.reference import ad3_bench_2026_11, ad3_rlc_pilot
from pbc.figure_language import LINE, MUTED, figsize, figure_style, finish
from pbc.instruments import RECORDED
from pbc.products.physics_lab import protocol, workflow
from pbc.products.physics_lab.lab import EXAMPLES

PILOT = SAMPLES_DIR / "ad3-rlc-pilot"
# The input of the pilot's live run, which its replay takes again.
PILOT_INPUT = EXAMPLES / "live-pilot.toml"


def draw_discrepancy() -> Figure:
    """The pilot's measured sweep (gain and phase of V_C / V_S, one standard
    deviation of the phasor fits) against the closed form of the parts'
    labels with no coil loss, drawn apart, and the residual of the gain.

    The capstone's experiment declares its provenance (``PILOT_FIGURE``):
    its status, the model it combines with the measurement, and the card's
    credit are at the caption and in the PNG's metadata; every drawn line
    carries the role of what it shows."""
    measured = ad3_rlc_pilot.response(PILOT, "capacitor")
    nominal = ad3_rlc_pilot.NOMINAL
    f = measured.frequency_hz
    dense = np.geomspace(f.min(), f.max(), 400)
    model = ad3_rlc_pilot.capacitor_ratio(
        dense, nominal["R"], nominal["L"], nominal["C"]
    )
    at = ad3_rlc_pilot.capacitor_ratio(f, nominal["R"], nominal["L"], nominal["C"])
    with figure_style():
        fig, (top, middle, bottom) = plt.subplots(
            3, 1, figsize=figsize("measured"), sharex=True,
            gridspec_kw={"height_ratios": [1.6, 1.0, 1.0]},
        )  # fmt: skip
        points = {"color": COLOURS[0], "marker": "o", "ms": 3.2, "ls": "none"}
        bars = top.errorbar(
            f, measured.gain, yerr=measured.gain_sigma,
            label="measured, one s.d.\nof the phasor fits", **points,
        )  # fmt: skip
        role(bars, "processed")
        bars = middle.errorbar(
            f, measured.phase_deg, yerr=measured.phase_sigma_deg, **points
        )
        role(bars, "processed")
        (line,) = top.plot(
            dense, np.abs(model), ls="--", color=COLOURS[1], lw=LINE["model"],
            label="closed form of the labels,\nno coil loss",
        )  # fmt: skip
        role(line, "simulated")
        (line,) = middle.plot(
            dense, np.degrees(np.unwrap(np.angle(model))), ls="--",
            color=COLOURS[1], lw=LINE["model"],
        )  # fmt: skip
        role(line, "simulated")
        (line,) = bottom.plot(
            f, np.abs(at) - measured.gain, ls="--", marker="s", ms=3.2,
            color=COLOURS[1], lw=LINE["model"],
        )  # fmt: skip
        role(line, RESIDUAL)
        middle.axhline(-90.0, color=MUTED, lw=LINE["axis"])
        bottom.axhline(0.0, color=MUTED, lw=LINE["axis"])
        top.set_xscale("log")
        top.set_yscale("log")
        top.set_ylabel("gain [V/V]")
        top.set_title("Gain: the measured peak\nis lower and broader")
        top.legend(
            loc="lower center", bbox_to_anchor=(0.5, 1.28), ncols=1, labelspacing=0.3
        )
        middle.set_ylabel("phase [deg]")
        middle.set_title("Phase: -90 deg is crossed lower")
        bottom.set_ylabel("residual [V/V]")
        bottom.set_xlabel("frequency [Hz]")
        bottom.set_title("Residual of the gain, model - measured")
    return finish(fig, grid=True)


def replay(out_dir: Path) -> workflow.Result:
    """The pilot's capacitor sweep replayed by the recorded adapter through
    F138's frequency-response protocol: nothing is measured again."""
    config = protocol.load_config(PILOT_INPUT)
    return workflow.run(config, out_dir, mode=RECORDED, sample=PILOT / "capacitor")


def bench_sessions() -> dict[str, int]:
    """The counts the page states of the owner's bench sessions
    (``ad3-bench-2026-11``), from the exports' recorded results as they are:
    the series RLC campaigns, those whose two protocols agree on f0 and
    those whose two protocols differ in Q (k = 2), those the evaluator
    failed, and the LED-pair runs and those whose held-out check failed.
    Nothing is replayed or measured."""
    found = ad3_bench_2026_11.campaigns(SAMPLES_DIR / ad3_bench_2026_11.DATASET)
    rlc = [c for c in found if c.circuit == "series-rlc"]
    led = [c for c in found if c.circuit == "led-pair"]
    return {
        "rlc": len(rlc),
        "f0-agree": sum(bool(c.f0_agree) for c in rlc),
        "q-differ": sum(c.q_agree is False for c in rlc),
        "rlc-failed": sum(c.verdict is False for c in rlc),
        "led": len(led),
        "led-held-out-failed": sum(c.held_out_agree is False for c in led),
    }
