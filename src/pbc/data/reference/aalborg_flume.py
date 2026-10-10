"""Submerged-bar wave flume: measured surface elevation against three CFD models.

Status of the figure: the experiment is *processed-measured* (aligned
repetitions, sample mean, expanded uncertainty); the three numerical series are
*modelled-reference*. They are drawn apart and never merged.
"""

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from pbc.data.flume import Elevation, read_elevation

WAVE_CONDITION = 1
GAUGE = 5
WINDOW = (5.0, 14.0)  # s; all three numerical runs and the steady wave train overlap
SAMPLE_END = 30.0  # s; the numerical runs of the A files end at 14, 20, 30 s

EXPERIMENT = f"Exp_WC{WAVE_CONDITION}_surfaceElevation.csv"
MODELS = {  # label: (folder in the archive, file)
    "i-VoF (OpenFOAM)": ("iVoF", f"iVoF_WC{WAVE_CONDITION}_surfaceElevation_A.csv"),
    "M-sigma (MIKE 3)": ("Msigma", f"Msigma_WC{WAVE_CONDITION}_surfaceElevation_A.csv"),
    "D-SPH (DualSPHysics)": ("DSPH", f"DSPH_WC{WAVE_CONDITION}_surfaceElevation_A.csv"),
}
COLORS = ["#D55E00", "#009E73", "#CC79A7"]


def sample_name(source: str) -> str:
    return source.replace("surfaceElevation", f"gauge{GAUGE:02d}_surfaceElevation")


def extract_sample(archive_dir: Path, out_dir: Path) -> list[Path]:
    """Write the committed sample from the extracted archive ``Andersen_etal_2025``.

    Keeps the two header rows and, for wave gauge ``GAUGE``, the rows with
    time <= ``SAMPLE_END``. Cell text is copied unchanged, so every sample
    value is a value of the source file.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    jobs = [(Path("Exp/dataset") / EXPERIMENT, EXPERIMENT)]
    jobs += [(Path(folder) / "dataset" / f, f) for folder, f in MODELS.values()]
    for relative, name in jobs:
        with open(Path(archive_dir) / relative, newline="", encoding="utf-8") as fh:
            rows = list(csv.reader(fh))
        if name == EXPERIMENT:
            columns = [0, *range(1 + (GAUGE - 1) * 7, 8 + (GAUGE - 1) * 7)]
        else:
            columns = [0, GAUGE]
        target = out_dir / sample_name(name)
        with open(target, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh, lineterminator="\n")
            for k, row in enumerate(rows):
                if k >= 2 and float(row[0]) > SAMPLE_END:
                    break
                writer.writerow([row[c] for c in columns])
        written.append(target)
    return written


def load(data_dir: Path) -> tuple[Elevation, dict[str, Elevation]]:
    data_dir = Path(data_dir)
    experiment = read_elevation(data_dir / sample_name(EXPERIMENT))
    models = {
        k: read_elevation(data_dir / sample_name(f)) for k, (_, f) in MODELS.items()
    }
    return experiment, models


def residual(experiment: Elevation, model: Elevation) -> np.ndarray:
    """Model minus experimental mean on the experiment's times (model interpolated).

    NaN where the model run has ended or has no value.
    """
    mean = experiment.column(GAUGE, "mean")
    series = model.values[:, 0]
    ok = ~np.isnan(series)
    out = np.interp(
        experiment.time, model.time[ok], series[ok], left=np.nan, right=np.nan
    )
    return out - mean


def window_rms(experiment: Elevation, model: Elevation) -> float:
    """RMS of the residual over the comparison window, in metres."""
    r = residual(experiment, model)
    inside = (experiment.time >= WINDOW[0]) & (experiment.time <= WINDOW[1])
    return float(np.sqrt(np.nanmean(r[inside] ** 2)))


def dominant_period(time: np.ndarray, values: np.ndarray, start: float, stop: float):
    """Period (s) of the strongest spectral line of ``values`` in [start, stop]."""
    inside = (time >= start) & (time <= stop) & ~np.isnan(values)
    x = values[inside] - values[inside].mean()
    dt = np.median(np.diff(time[inside]))
    spectrum = np.abs(np.fft.rfft(x * np.hanning(x.size)))
    freq = np.fft.rfftfreq(x.size, dt)
    return 1 / freq[1:][np.argmax(spectrum[1:])]


def make_figure(data_dir: Path) -> plt.Figure:
    experiment, models = load(data_dir)
    t = experiment.time
    mean = experiment.column(GAUGE, "mean")
    unc = experiment.column(GAUGE, "expanded unc")
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(9, 7), sharex=True, constrained_layout=True
    )
    top.fill_between(
        t,
        mean - unc,
        mean + unc,
        color="#0072B2",
        alpha=0.3,
        label="95 % expanded unc.",
    )
    top.plot(t, mean, color="#0072B2", lw=1.5, label="measured, mean of 5 repetitions")
    for (name, model), color in zip(models.items(), COLORS, strict=True):
        top.plot(model.time, model.values[:, 0], color=color, lw=1, ls="--", label=name)
        rms = window_rms(experiment, model) * 1e3
        bottom.plot(
            t,
            residual(experiment, model) * 1e3,
            color=color,
            lw=1,
            label=f"{name}: RMS {rms:.2f} mm in the window",
        )
    for axis in (top, bottom):
        axis.axvspan(*WINDOW, color="0.5", alpha=0.12, lw=0)
    top.set_ylabel("surface elevation [m]")
    top.set_title(
        f"Wave condition {WAVE_CONDITION}, wave gauge {GAUGE}: processed measurement "
        "(solid) and modelled references (dashed)"
    )
    top.legend(fontsize=8, ncols=2)
    bottom.set_ylabel("model minus measured mean [mm]")
    bottom.set_xlabel("time [s]")
    bottom.set_title(
        "Simulated minus measured (model interpolated to 150 Hz); shaded: comparison "
        "window, outside it start-up transients and run ends dominate"
    )
    bottom.legend(fontsize=8)
    top.set_xlim(0, SAMPLE_END)
    fig.text(
        0.01,
        -0.02,
        "Data: Andersen, Eldrup, Ferri, Verao Fernandez, Aalborg University, Zenodo "
        "10.5281/zenodo.15049542, CC BY 4.0. Subset of the published files; "
        "interpolation for the residual is ours.",
        fontsize=7,
    )
    return fig
