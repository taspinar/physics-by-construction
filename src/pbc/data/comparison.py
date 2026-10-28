"""The data of the waveform comparator, a browser component of the labs.

The component draws a measured series against a family of model profiles and
reads out the error metrics of each. It computes nothing: this module computes
both, from the lab's own code, and the page embeds the result as JSON. The
measured series is stored as it is given (rounded to ``DECIMALS`` places, far
below the noise), never smoothed or resampled. The file also holds every word
the component shows about the data (``labels``, the metrics with the decimals
they are shown with, the details of a model), so that one component serves
every lab: ``waveform_comparison`` writes the family of trial chirp masses of
the gravitational-wave lab, ``named_comparison`` a family of named models.
"""

from collections.abc import Mapping, Sequence

import numpy as np
from numpy.typing import NDArray

from pbc.data.gwstrain import ModelAtMass

Array = NDArray[np.float64]

DECIMALS = 5  # places kept of a whitened sample, whose noise is of order one
SCHEMA = "waveform-comparison-2"
# The metrics of the chirp-mass family: key, label, decimals shown.
CHIRP_METRICS = (
    ("chi2", "Chi-square of the fit window, H1 and L1 combined", 1),
    ("reduced_chi2", "Chi-square per sample, H1 and L1 combined", 3),
    (
        "rms_residual",
        "Root-mean-square residual, H1 and L1 combined (whitened units)",
        4,
    ),
    ("correlation", "Correlation of data and model, H1 and L1 combined", 4),
)


def _as_browser_writes(value: float) -> str:
    """A number as the component wrote it before the text was in the file:
    24.0 is "24"."""
    return str(int(value)) if value == int(value) else repr(value)


def _round(values: Array) -> list[float]:
    return [float(v) for v in np.round(values, DECIMALS)]


def waveform_comparison(
    time: Array,
    measured: Array,
    models: Sequence[ModelAtMass],
    detector: str,
    *,
    sigma: float,
    window: tuple[float, float],
    show: tuple[float, float],
    quantity: str,
    unit: str,
    best: float,
) -> Mapping[str, object]:
    """The comparison of ``measured`` with each of ``models`` for the
    detector ``detector``, over the times ``show``.

    ``window`` is the part the models were fitted to, and ``best`` the trial
    value of the parameter (a mass) of the overall best fit. The metrics are
    those of ``ModelAtMass``, over both detectors, as the fit sees them.
    """
    keep = (time >= show[0]) & (time <= show[1])
    parameter = "chirp mass, detector frame"
    sigma = round(sigma, DECIMALS)
    return {
        "schema": SCHEMA,
        "detector": detector,
        "quantity": quantity,
        "unit": unit,
        "time_unit": "s",
        "sigma": sigma,
        "window": list(window),
        "best_parameter": best,
        "parameter": {"name": parameter, "unit": "solar masses"},
        "labels": {
            "title": f"{quantity} of detector {detector}, measured and model",
            "description": (
                f"The {quantity} of detector {detector} against time, with the"
                f" model for the chosen {parameter}, and the residuals below."
            ),
            "slider": "Trial",
            "measured": "measured, whitened",
            "model": f"model, {parameter} ",
            "window": "fit window",
            "notes": [f"noise standard deviation: {_as_browser_writes(sigma)}"],
        },
        "metrics": [list(m) for m in CHIRP_METRICS],
        "details": [
            [
                "coalescence_time",
                "Coalescence time of this model (s)",
                "coalescence time (s)",
            ]
        ],
        "time": _round(time[keep]),
        "measured": _round(measured[keep]),
        "models": [
            {
                "parameter": round(m.mc, 3),
                "coalescence_time": round(m.t_c, 5),
                "metrics": {
                    "chi2": round(m.chi2, 2),
                    "reduced_chi2": round(m.reduced_chi2, 3),
                    "rms_residual": round(m.rms_residual, 4),
                    "correlation": round(m.correlation, 4),
                },
                "values": _round(m.model[detector][keep]),
                "residual": _round((measured - m.model[detector])[keep]),
            }
            for m in models
        ],
    }


def named_comparison(
    time: Array,
    measured: Array,
    models: Mapping[str, Array],
    *,
    window: tuple[float, float],
    quantity: str,
    unit: str,
    measured_label: str,
    title: str,
    notes: Sequence[str] = (),
    scale: float = 1.0,
) -> Mapping[str, object]:
    """The comparison of ``measured`` with each named model of ``models`` on
    the same samples ``time``, with the metrics of the window ``window``.

    The values are stored times ``scale`` (1000 to show metres in mm) and
    rounded to ``DECIMALS`` places; the residual is the model minus the
    measurement, as ``pbc.data.plotting.measured_vs_model`` draws it in the
    static figure that the component replaces. The metrics, over the window: the
    root-mean-square and the largest residual, in ``unit``, and the
    correlation of the measurement and the model. The models are named, not
    fitted, so no model is marked the best one.
    """
    measured = np.asarray(measured, dtype=float) * scale
    inside = (time >= window[0]) & (time <= window[1])
    entries = []
    for name, values in models.items():
        values = np.asarray(values, dtype=float) * scale
        residual = values - measured
        r = residual[inside]
        entries.append(
            {
                "parameter": name,
                "metrics": {
                    "rms_residual": round(float(np.sqrt(np.mean(r**2))), 4),
                    "largest_residual": round(float(np.max(np.abs(r))), 4),
                    "correlation": round(
                        float(np.corrcoef(measured[inside], values[inside])[0, 1]), 4
                    ),
                },
                "values": _round(values),
                "residual": _round(residual),
            }
        )
    return {
        "schema": SCHEMA,
        "quantity": quantity,
        "unit": unit,
        "time_unit": "s",
        "window": list(window),
        "best_parameter": None,
        "parameter": {"name": "model", "unit": ""},
        "labels": {
            "title": title,
            "description": (
                f"The {quantity} against time, measured and as the chosen model"
                " gives it, and the residuals below."
            ),
            "slider": "Choose the",
            "measured": measured_label,
            "model": "",
            "window": "window of the metrics",
            "notes": ["residual: model minus measured", *notes],
        },
        "metrics": [
            ["rms_residual", f"Root-mean-square residual in the window ({unit})", 3],
            ["largest_residual", f"Largest residual in the window ({unit})", 3],
            ["correlation", "Correlation of measurement and model in the window", 4],
        ],
        "details": [],
        "time": _round(time),
        "measured": _round(measured),
        "models": entries,
    }
