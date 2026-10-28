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

from pbc.data.adapters import measured_elevation, modelled_elevation
from pbc.data.flume import Elevation, read_elevation
from pbc.data.plotting import add_credit, measured_vs_model

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


# The sample of the wave flume lab (W8): every gauge, for the comparison of
# the propagation along the flume. The experiment's seven columns of each
# gauge other than GAUGE (whose file above runs to SAMPLE_END already), and
# the A file of each model with all its gauges, rows with time <= LAB_END.
GAUGES = tuple(range(1, 21))
LAB_END = 22.0  # s; the last gauge's analysis window ends before it


def lab_sample_name(source: str, gauge: int | None = None) -> str:
    if gauge is None:
        return source
    return source.replace("surfaceElevation", f"gauge{gauge:02d}_surfaceElevation")


def _rows(source: Path) -> list[list[str]]:
    with open(source, newline="", encoding="utf-8") as fh:
        return list(csv.reader(fh))


def _copy_rows(rows: list[list[str]], target: Path, columns: list[int], end: float):
    with open(target, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        for k, row in enumerate(rows):
            if k >= 2 and float(row[0]) > end:
                break
            writer.writerow([row[c] for c in columns])


def extract_lab_sample(archive_dir: Path, out_dir: Path) -> list[Path]:
    """Write the lab's part of the committed sample from the extracted archive.

    As ``extract_sample``: the two header rows and the rows with time <=
    ``LAB_END``, cell text unchanged.
    """
    archive_dir, out_dir = Path(archive_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    rows = _rows(archive_dir / "Exp/dataset" / EXPERIMENT)
    for gauge in GAUGES:
        if gauge == GAUGE:
            continue
        target = out_dir / lab_sample_name(EXPERIMENT, gauge)
        columns = [0, *range(1 + (gauge - 1) * 7, 8 + (gauge - 1) * 7)]
        _copy_rows(rows, target, columns, LAB_END)
        written.append(target)
    for folder, name in MODELS.values():
        target = out_dir / lab_sample_name(name)
        source = _rows(archive_dir / folder / "dataset" / name)
        _copy_rows(source, target, [0, *GAUGES], LAB_END)
        written.append(target)
    return written


def load_lab(data_dir: Path) -> tuple[dict[int, Elevation], dict[str, Elevation]]:
    """The experiment at every gauge, and each model with all its gauges."""
    data_dir = Path(data_dir)
    experiment = {}
    for gauge in GAUGES:
        name = sample_name(EXPERIMENT) if gauge == GAUGE else None
        experiment[gauge] = read_elevation(
            data_dir / (name or lab_sample_name(EXPERIMENT, gauge))
        )
    models = {k: read_elevation(data_dir / f) for k, (_, f) in MODELS.items()}
    return experiment, models


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
    fig, (top, bottom) = measured_vs_model(
        measured_elevation(experiment, GAUGE),
        {name: modelled_elevation(model) for name, model in models.items()},
        window=WINDOW,
        figsize=(9, 7),
    )
    top.set_title(
        f"Gauge {GAUGE}, wave condition {WAVE_CONDITION}: measurement (solid), "
        "modelled references (dashed)"
    )
    bottom.set_title(
        "Model minus measurement (model interpolated to 150 Hz); shaded: comparison "
        "window"
    )
    top.set_xlim(0, SAMPLE_END)
    add_credit(
        fig,
        "Data: Andersen, Eldrup, Ferri, Verao Fernandez, Aalborg University, Zenodo "
        "10.5281/zenodo.15049542, CC BY 4.0. Subset of the published files; "
        "interpolation for the residual is ours. Band: one standard uncertainty "
        "of the mean (the file gives the 95 % expanded one).",
    )
    return fig
