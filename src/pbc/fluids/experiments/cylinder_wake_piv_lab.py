"""The experiment of the lesson "Cylinder wake PIV lab".

The vortex-shedding model of FL3 (``pbc.fluids.vortices``: a street of
alternating vortices, St = f D / U, the frequency from the crossings of a
probe signal, blockage raising it) against two measured records: the PIV
velocity fields of the wake of a 9.5 mm cylinder at Re = 413 (the committed
sample of the card ``piv-cylinder-wake``) and ten hot-wire runs behind
cylinders of 25.1 to 50 mm at Re of 8e3 to 5e4 (the card
``ost-hotwire-cylinder-wakes``). The vorticity is derived from the PIV
vectors with the stencils of ``pbc.fluids.piv``, checked first on an
analytic vortex. Run it as a program to write the figures and the numbers of
the page:

    uv run --locked --no-dev python -m \\
        pbc.fluids.experiments.cylinder_wake_piv_lab out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import Normalize
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from pbc.data import SAMPLES_DIR
from pbc.data.adapters import hot_wire_series, piv_probe_series
from pbc.data.plotting import COLOURS, add_credit, label_status
from pbc.data.reference import cylinder_wake, ost_hotwire
from pbc.experiment import Experiment, main
from pbc.fluids import piv
from pbc.fluids.vortices import ROSHKO_FIT, roshko_strouhal, shedding_frequency

PIV_DATASET = "piv-cylinder-wake"
HOT_WIRE_DATASET = "ost-hotwire-cylinder-wakes"
# region: choices
BAND = (0.5, 1.3)  # Hz, the band-pass before the crossings of FL3's method
MAX_LAG = 30  # periods summed in the correlation of the period lengths
FREE_STREAM_ROWS = 6  # the top rows of the crop, 1.9 to 2.4 D from the axis
BEHIND = 1.0  # diameters behind the shadow's centre where the street is compared
HALF_PERIOD = 11  # frames, the nearest whole number to 20 Hz / (2 f)
KEYFRAMES = (0, 6, 11)  # frames about a quarter period apart: half a period
HOT_WIRE_ERROR = 0.01  # relative, per run: the dossier's spread between segments
DECIMATE = 13  # every 13th frame: 1.54 frames per second, for the exercise
# endregion: choices
STENCIL_STEPS = (0.4, 0.2, 0.1, 0.05)  # h / c on the Lamb-Oseen vortex
NOISE_SEED = 20261113
PIV_CREDIT = (
    "Data: J. Shang, J. Tu, PIV of flow past a cylinder, Zenodo, doi "
    "10.5281/zenodo.20765567, CC BY 4.0; extract by this project. Vorticity, "
    "filter, spectra: this lesson's."
)
HOT_WIRE_CREDIT = (
    "Data: A. P. Ost, A. V. de Paula, S. V. Möller, Mendeley Data, doi "
    "10.17632/xy8ggx9hn6.1, CC BY 4.0, 16.4 s per run; PIV: J. Shang, J. Tu, "
    "Zenodo, doi 10.5281/zenodo.20765567, CC BY 4.0. St: this lesson's."
)
MARKERS = {25.1: ("o", COLOURS[0]), 32.0: ("s", COLOURS[2]), 50.0: ("^", COLOURS[1])}


def load_wake() -> cylinder_wake.Wake:
    """The committed PIV sample: 60 frames of the near wake and two probes."""
    return cylinder_wake.load(SAMPLES_DIR / PIV_DATASET)


def load_hot_wire() -> ost_hotwire.HotWire:
    """The committed hot-wire sample: 16.384 s of each of ten runs."""
    return ost_hotwire.load(SAMPLES_DIR / HOT_WIRE_DATASET)


def spacing(wake: cylinder_wake.Wake) -> float:
    """The grid spacing h [m] of the record, the same in x and y."""
    return float(wake.x[1] - wake.x[0])


def axis_row(wake: cylinder_wake.Wake) -> int:
    """The row of the crop on the wake axis, where the probes are."""
    return int(np.argmin(np.abs(wake.y - wake.meta["probes"]["2D"]["y"])))


# The record without a model.


def record_landmarks(wake: cylinder_wake.Wake, data: ost_hotwire.HotWire) -> dict:
    """What the samples show without a model: frames, grid, cadence, masks,
    the probes' series, and the hot-wire runs."""
    probe = piv_probe_series(wake, 0, 1)
    masked = wake.mask.reshape(wake.mask.shape[0], -1).sum(axis=1)
    return {
        "probe": probe,
        "hot-wire": [hot_wire_series(data, k) for k in range(len(data.runs))],
        "frames": int(wake.u.shape[0]),
        "nx": int(wake.x.size),
        "ny": int(wake.y.size),
        "h-mm": spacing(wake) * 1e3,
        "record-s": float(probe.x[-1] + probe.x[1]),
        "masked-low": int(masked.min()),
        "masked-high": int(masked.max()),
        "masked-always": int(wake.mask.all(axis=0).sum()),
        "points": int(wake.x.size * wake.y.size),
        "runs": len(data.runs),
    }


# The stencils on an analytic vortex.


def stencil_check(experiment: Experiment) -> dict:
    """Both stencils on a Lamb-Oseen vortex of core c at four steps h, and
    on independent seeded noise, against their stated error and noise."""
    rows, errors = [], {s: [] for s in piv.STENCILS}
    for h in STENCIL_STEPS:
        n = round(3.0 / h)
        axis = np.arange(-n, n + 1) * h
        x, y = np.meshgrid(axis, axis)
        u, v, exact = piv.lamb_oseen(x, y)
        row = [h]
        for stencil in piv.STENCILS:
            omega = piv.vorticity(u, v, h, stencil)
            inside = np.isfinite(omega)
            error = float(np.max(np.abs(omega[inside] - exact[inside])) / exact.max())
            errors[stencil].append(error)
            row.append(error)
        rows.append(tuple(row))
    rng = np.random.default_rng(NOISE_SEED)
    noise = rng.normal(0.0, 1.0, (2, 300, 300))
    gains = {
        s: float(np.nanstd(piv.vorticity(noise[0], noise[1], 1.0, s)))
        for s in piv.STENCILS
    }
    experiment.table(
        "stencil-check",
        rows,
        columns=[
            ("h / c", "", ".2f"),
            ("largest error, central", "of the peak vorticity", ".2e"),
            ("largest error, least squares", "of the peak vorticity", ".2e"),
        ],
        caption="The vorticity of a Lamb-Oseen vortex of core c from its exact "
        "velocity on grids of step h, by the two stencils, against the exact "
        "vorticity.",
    )
    central = np.array(errors["central"])
    squares = np.array(errors["least squares"])
    return {
        "errors": errors,
        "gains": gains,
        "order-low": float(np.min(central[:-1] / central[1:])),
        "order-high": float(np.max(squares[:-1] / squares[1:])),
        "ratio": float(squares[-1] / central[-1]),
    }


# The measured field.


def field_vorticity(wake: cylinder_wake.Wake) -> dict:
    """The vorticity of the 60 frames by both stencils, NaN where a stencil
    touches the mask; and the noise in the free stream."""
    h = spacing(wake)
    omega = {s: piv.vorticity(wake.u, wake.v, h, s, wake.mask) for s in piv.STENCILS}
    top = slice(wake.y.size - FREE_STREAM_ROWS, None)
    noise = {s: float(np.nanstd(omega[s][:, top, :])) for s in piv.STENCILS}
    fluctuation = wake.u[:, top, :] - wake.u[:, top, :].mean(axis=0)
    neighbours = float(
        np.corrcoef(fluctuation[:, :, 1:].ravel(), fluctuation[:, :, :-1].ravel())[0, 1]
    )
    return {
        "omega": omega,
        "noise": noise,
        "noise-ratio": noise["least squares"] / noise["central"],
        "neighbours": neighbours,
        "p99": {s: float(np.nanpercentile(np.abs(omega[s]), 99)) for s in omega},
        "max": {s: float(np.nanmax(np.abs(omega[s]))) for s in omega},
        "free-top": float(wake.y[-1] - wake.y[axis_row(wake)]),
        "free-bottom": float(wake.y[top.start] - wake.y[axis_row(wake)]),
    }


def street_symmetry(wake: cylinder_wake.Wake, omega: np.ndarray) -> dict:
    """The correlation of the vorticity behind the cylinder with itself
    after a shift in time, reflected about the wake axis or not, with its
    sign flipped or not; the mean over the frames that the shift allows."""
    centre = cylinder_wake.shadow_centre_x(wake)
    behind = wake.x > centre + BEHIND * cylinder_wake.DIAMETER
    row = axis_row(wake)
    rows = min(row, wake.y.size - 1 - row)

    def mean_correlation(shift: int, reflected: bool, sign: float) -> float:
        values = []
        for k in range(omega.shape[0] - shift):
            band, mirror = piv.reflect(omega[k + shift], row, rows)
            first, _ = piv.reflect(omega[k], row, rows)
            other = (mirror if reflected else band) * sign
            a, b = first[:, behind], other[:, behind]
            ok = np.isfinite(a) & np.isfinite(b)
            values.append(np.corrcoef(a[ok], b[ok])[0, 1])
        return float(np.mean(values))

    return {
        "half-reflected": mean_correlation(HALF_PERIOD, True, -1.0),
        "full": mean_correlation(2 * HALF_PERIOD, False, 1.0),
        "half-plain": mean_correlation(HALF_PERIOD, False, 1.0),
        "none-reflected": mean_correlation(0, True, -1.0),
        "rows": rows,
    }


# The shedding frequency.


def crossing_frequency(series: np.ndarray, t: np.ndarray) -> dict:
    """FL3's frequency from upward crossings of v, raw and after the
    band-pass; the period lengths, their correlation, and the standard error
    of the mean frequency with and without that correlation."""
    raw, _ = shedding_frequency(t, series)
    filtered = piv.band_pass(series, *BAND, cylinder_wake.FPS)
    frequency, crossings = shedding_frequency(t, filtered)
    periods = np.diff(crossings)
    q = periods - periods.mean()
    lags = np.arange(1, MAX_LAG + 1)
    rho = np.array([np.sum(q[:-k] * q[k:]) / np.sum(q * q) for k in lags])
    effective = periods.size / (1 + 2 * rho.sum())
    spread = periods.std(ddof=1)
    blocks = []
    for b in range(cylinder_wake.BLOCKS):
        span = t[-1] / cylinder_wake.BLOCKS
        inside = crossings[(crossings >= b * span) & (crossings < (b + 1) * span)]
        blocks.append((inside.size - 1) / (inside[-1] - inside[0]))
    blocks = np.array(blocks)
    return {
        "raw": raw,
        "filtered": filtered,
        "frequency": frequency,
        "periods": periods,
        "rho": rho,
        "band": 2 / np.sqrt(periods.size),
        "effective": effective,
        "naive-err": spread / np.sqrt(periods.size) / periods.mean() ** 2,
        "correlated-err": spread / np.sqrt(effective) / periods.mean() ** 2,
        "blocks": blocks,
        "block-err": float(blocks.std(ddof=1) / np.sqrt(blocks.size)),
    }


def frequency_table(
    experiment: Experiment, analysis: cylinder_wake.Analysis, crossing: dict
) -> None:
    rows = []
    for k in range(cylinder_wake.BLOCKS):
        rows.append(
            (
                f"{100 * k}-{100 * (k + 1)} s",
                analysis.block_frequency["2D"][k],
                analysis.block_frequency["5D"][k],
                crossing["blocks"][k],
            )
        )
    rows.append(
        (
            "mean of the blocks",
            analysis.frequency["2D"],
            analysis.frequency["5D"],
            float(crossing["blocks"].mean()),
        )
    )
    rows.append(
        (
            "standard error",
            analysis.frequency_err["2D"],
            analysis.frequency_err["5D"],
            crossing["block-err"],
        )
    )
    experiment.table(
        "frequencies",
        rows,
        columns=[
            ("block", "", "s"),
            ("spectral peak of v, 2 D", "Hz", ".4f"),
            ("spectral peak of v, 5 D", "Hz", ".4f"),
            ("crossings of filtered v, 2 D", "Hz", ".4f"),
        ],
        caption="The shedding frequency in four blocks of 100 s: the largest "
        "spectral peak of v at each probe, and FL3's method, upward crossings of "
        "v at 2 D after the band-pass.",
    )


# The hot wire.


def hot_wire_table(
    experiment: Experiment, data: ost_hotwire.HotWire, result: ost_hotwire.Analysis
) -> None:
    rows = []
    for k, run in enumerate(data.runs):
        rows.append(
            (
                run.name,
                run.diameter * 1e3,
                run.velocity,
                result.reynolds[k],
                result.blockage[k],
                result.frequency[k],
                result.strouhal[k],
                result.strouhal[k] * (1 - result.blockage[k]),
            )
        )
    experiment.table(
        "hot-wire",
        rows,
        columns=[
            ("run", "", "s"),
            ("D", "mm", ".1f"),
            ("U", "m/s", ".2f"),
            ("Re = U D / nu", "", ",.0f"),
            ("D / W", "", ".3f"),
            ("f", "Hz", ".2f"),
            ("St = f D / U", "", ".4f"),
            ("St (1 - D/W)", "", ".4f"),
        ],
        caption="The ten hot-wire runs: the record's diameter and reference "
        "velocity, the Reynolds number with the viscosity the record implies, "
        "the blockage, the spectral peak, and the Strouhal number with and "
        "without the continuity correction of the speed past the cylinder.",
    )


def blockage_line(result: ost_hotwire.Analysis) -> dict:
    """A straight line St = a + b D/W through the ten runs; the errors of a
    and b from the scatter about it, the runs taken as independent."""
    params, covariance = np.polyfit(result.blockage, result.strouhal, 1, cov=True)
    slope, intercept = params
    errors = np.sqrt(np.diag(covariance))
    return {
        "slope": float(slope),
        "slope-err": float(errors[0]),
        "intercept": float(intercept),
        "intercept-err": float(errors[1]),
    }


# The figures.


def _extent(wake: cylinder_wake.Wake) -> tuple[float, float, float, float]:
    half = spacing(wake) * 1e3 / 2
    return (
        wake.x[0] * 1e3 - half,
        wake.x[-1] * 1e3 + half,
        wake.y[0] * 1e3 - half,
        wake.y[-1] * 1e3 + half,
    )


def _vorticity_panels(
    fig: Figure,
    axes,
    fields,
    titles,
    wake: cylinder_wake.Wake,
    limit: float,
    bar_axes=None,
) -> None:
    cmap = plt.get_cmap("PuOr").with_extremes(bad="0.85")
    norm = Normalize(-limit, limit)
    image = None
    for ax, field, title in zip(axes, fields, titles, strict=True):
        image = ax.imshow(
            np.ma.masked_invalid(field),
            cmap=cmap,
            norm=norm,
            origin="lower",
            extent=_extent(wake),
            interpolation="nearest",
        )
        ax.set_title(title, fontsize=8)
        ax.set_xlabel("x [mm]", fontsize=7)
        ax.set_ylabel("y [mm]", fontsize=7)
        ax.tick_params(labelsize=6)
    bar = fig.colorbar(image, ax=axes if bar_axes is None else bar_axes, shrink=0.8)
    bar.set_label("ω [1/s] (false colour)", fontsize=7)
    bar.ax.tick_params(labelsize=6)


def draw_wake_keyframes(
    wake: cylinder_wake.Wake, field: dict, analysis: cylinder_wake.Analysis
) -> Figure:
    fig, axes = plt.subplots(2, 2, figsize=(6.2, 4.6), constrained_layout=True)
    panels = axes.ravel()
    omega = field["omega"]["central"]
    titles = [f"ω, frame {k}, t = {k / cylinder_wake.FPS:.2f} s" for k in KEYFRAMES]
    _vorticity_panels(
        fig,
        panels[:3],
        [omega[k] for k in KEYFRAMES],
        titles,
        wake,
        20.0,
        bar_axes=panels[:2],
    )
    probe = wake.meta["probes"]["2D"]
    for ax in panels[:3]:
        ax.plot(
            [probe["x"] * 1e3],
            [probe["y"] * 1e3],
            "o",
            mfc="none",
            mec="k",
            ms=5,
        )
    panels[2].legend(
        handles=[
            Line2D(
                [], [], ls="none", marker="o", mfc="none", mec="k", label="probe 2 D"
            ),
            Line2D([], [], ls="none", marker="s", color="0.85", label="no data"),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.3),
        ncols=2,
        fontsize=6,
    )

    # The mean over all 8000 frames: u and the streamlines of the mean field.
    ax = panels[3]
    cmap = plt.get_cmap("PuOr").with_extremes(bad="0.85")
    limit = float(np.nanmax(np.abs(wake.mean[0]))) * 1e3
    image = ax.imshow(
        np.ma.masked_invalid(wake.mean[0] * 1e3),
        cmap=cmap,
        norm=Normalize(-limit, limit),
        origin="lower",
        extent=_extent(wake),
        interpolation="nearest",
    )
    bar = fig.colorbar(image, ax=ax)
    bar.set_label("mean u [mm/s] (false colour)", fontsize=7)
    bar.ax.tick_params(labelsize=6)
    mu, mv = (np.ma.masked_invalid(c) for c in wake.mean)
    ax.streamplot(
        wake.x * 1e3,
        wake.y * 1e3,
        mu,
        mv,
        color="k",
        linewidth=0.5,
        density=0.6,
        arrowsize=0.6,
    )
    end = analysis.recirculation * 1e3
    ax.plot(
        [end, end],
        [wake.y[0] * 1e3, wake.y[-1] * 1e3],
        "--",
        color=COLOURS[1],
        lw=1.0,
    )
    ax.set_xlim(_extent(wake)[:2])
    ax.set_ylim(_extent(wake)[2:])
    ax.set_xlabel("x [mm]", fontsize=7)
    ax.set_ylabel("y [mm]", fontsize=7)
    ax.tick_params(labelsize=6)
    ax.set_title("mean u, 8000 frames", fontsize=8)
    ax.legend(
        handles=[
            Line2D([], [], color="k", lw=0.5, label="mean streamlines"),
            Line2D([], [], color=COLOURS[1], ls="--", label="end of recirculation"),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.3),
        ncols=2,
        fontsize=6,
    )
    label_status(fig, "processed")
    add_credit(fig, PIV_CREDIT)
    return fig


def draw_vorticity_stencils(wake: cylinder_wake.Wake, field: dict) -> Figure:
    fig, axes = plt.subplots(1, 2, figsize=(5.8, 2.6), constrained_layout=True)
    _vorticity_panels(
        fig,
        axes,
        [field["omega"][s][0] for s in piv.STENCILS],
        ["frame 0, central stencil", "frame 0, least-squares stencil"],
        wake,
        20.0,
    )
    label_status(fig, "processed")
    add_credit(fig, PIV_CREDIT)
    return fig


def draw_shedding(wake: cylinder_wake.Wake, crossing: dict) -> Figure:
    fig, (series, power) = plt.subplots(
        1, 2, figsize=(6.0, 2.4), constrained_layout=True, width_ratios=(1.1, 1.0)
    )
    t = np.arange(wake.probes.shape[0]) / cylinder_wake.FPS
    first = t < 6
    series.plot(
        t[first],
        wake.probes[first, 0, 1] * 1e3,
        "-",
        color="0.6",
        lw=0.7,
        antialiased=False,
        label="v at 2 D [processed]",
    )
    series.plot(
        t[first],
        crossing["filtered"][first] * 1e3,
        "-",
        color=COLOURS[0],
        lw=1.1,
        label=f"v band-passed {BAND[0]}-{BAND[1]} Hz",
    )
    series.set_xlabel("time [s]", fontsize=8)
    series.set_ylabel("v [mm/s]", fontsize=8)
    series.set_ylim(-60, 75)
    series.set_title("Cross-stream velocity on the axis", fontsize=9)
    series.legend(fontsize=6, loc="upper center", ncols=2)
    for k, (name, colour, style) in enumerate(
        (("u", COLOURS[2], "--"), ("v", COLOURS[0], "-"))
    ):
        f, p = cylinder_wake.spectrum(wake.probes[:, 0, k])
        keep = (f > 0) & (f <= 3)
        power.semilogy(
            f[keep],
            p[keep],
            style,
            color=colour,
            lw=0.8,
            antialiased=False,
            label=f"{name} at 2 D [processed]",
        )
    for multiple, style in ((1, ":"), (2, "-.")):
        frequency = multiple * cylinder_wake.F_PUBLISHED
        power.plot(
            [frequency, frequency],
            [1e-9, 1e-2],
            style,
            color=COLOURS[1],
            lw=0.9,
            label="published f" if multiple == 1 else "twice that",
        )
    power.set_ylim(1e-8, 5e-3)
    power.set_xlabel("frequency [Hz]", fontsize=8)
    power.set_ylabel("power density [(m/s)²/Hz]", fontsize=8)
    power.set_title("Welch spectra, 400 s", fontsize=9)
    power.legend(fontsize=6, loc="upper right")
    for ax in (series, power):
        ax.tick_params(labelsize=7)
    label_status(fig, "processed")
    add_credit(fig, PIV_CREDIT)
    return fig


def draw_strouhal(
    data: ost_hotwire.HotWire,
    result: ost_hotwire.Analysis,
    analysis: cylinder_wake.Analysis,
    piv_err: float,
    line: dict,
) -> Figure:
    fig, (st_re, st_block) = plt.subplots(
        1, 2, figsize=(6.2, 3.7), constrained_layout=True
    )
    diameters = np.array([round(r.diameter * 1e3, 1) for r in data.runs])
    for diameter, (marker, colour) in MARKERS.items():
        pick = diameters == diameter
        error = HOT_WIRE_ERROR * result.strouhal[pick]
        st_re.errorbar(
            result.reynolds[pick],
            result.strouhal[pick],
            yerr=error,
            fmt=marker,
            color=colour,
            ms=4,
            capsize=0,
            label=f"hot wire, D = {diameter:g} mm [processed]",
        )
        st_block.errorbar(
            result.blockage[pick],
            result.strouhal[pick],
            yerr=error,
            fmt=marker,
            color=colour,
            ms=4,
            capsize=0,
            label=f"D = {diameter:g} mm, St [processed]",
        )
        st_block.plot(
            result.blockage[pick],
            result.strouhal[pick] * (1 - result.blockage[pick]),
            marker,
            mfc="none",
            color=colour,
            ms=4,
        )
    st_block.plot([], [], "o", mfc="none", color="0.3", label="St (1 - D/W)")
    st_re.errorbar(
        [cylinder_wake.REYNOLDS],
        [analysis.strouhal],
        yerr=[piv_err],
        fmt="D",
        color=COLOURS[3],
        ms=4,
        capsize=0,
        label="PIV, Re = 413 [processed]",
    )
    stable = np.geomspace(ROSHKO_FIT[0] + 1, ROSHKO_FIT[1] - 1, 30)
    st_re.plot(
        stable,
        [roshko_strouhal(r) for r in stable],
        "-",
        color="0.2",
        lw=1.0,
        label="Roshko, stable range (FL3)",
    )
    irregular = np.geomspace(300, 2000, 30)
    st_re.plot(
        irregular,
        cylinder_wake.roshko(irregular),
        "--",
        color="0.2",
        lw=1.0,
        label="Roshko, irregular range",
    )
    st_re.set_xscale("log")
    st_re.set_ylim(0.14, 0.26)
    st_re.set_xlabel("Re = U D / ν [dimensionless]", fontsize=8)  # noqa: RUF001
    st_re.set_ylabel("St = f D / U [dimensionless]", fontsize=7)
    st_re.set_title("Strouhal against Reynolds number", fontsize=9)
    st_re.legend(fontsize=5.5, loc="upper center", bbox_to_anchor=(0.5, -0.25))
    ends = np.array([0.0, 0.3])
    st_block.plot(
        ends,
        line["intercept"] + line["slope"] * ends,
        ":",
        color="0.3",
        lw=1.0,
        label="straight line through St",
    )
    st_block.set_xlim(0, 0.3)
    st_block.set_ylim(0.16, 0.25)
    st_block.set_xlabel("blockage D / W [dimensionless]", fontsize=8)
    st_block.set_ylabel("St [dimensionless]", fontsize=7)
    st_block.set_title("Strouhal against blockage", fontsize=9)
    st_block.legend(fontsize=5.5, loc="upper center", bbox_to_anchor=(0.5, -0.25))
    for ax in (st_re, st_block):
        ax.tick_params(labelsize=7)
    label_status(fig, "processed")
    add_credit(fig, HOT_WIRE_CREDIT)
    return fig


# The exercises.


def aliasing_exercise(wake: cylinder_wake.Wake, frequency: float) -> None:
    """Exercise 2: v at 2 D kept at every 13th frame, a camera at 1.54
    frames per second: where does its spectral peak lie?"""
    rate = cylinder_wake.FPS / DECIMATE
    kept = wake.probes[::DECIMATE, 0, 1]
    f, p = cylinder_wake.spectrum(kept, nperseg=256)
    f = f * rate / cylinder_wake.FPS  # spectrum() assumes 20 Hz
    peak = f[1:][np.argmax(p[1:])]
    print(f"frames per second: {rate:.2f}, Nyquist frequency {rate / 2:.2f} Hz")
    print(f"spectral peak of the kept frames: {peak:.2f} Hz")
    print(f"rate minus the shedding frequency: {rate - frequency:.2f} Hz")


def scaling_exercise() -> None:
    """Exercise 1: the shedding frequency of a 25 mm cylinder in the same
    channel at the same speed, if St stays at the measured value."""
    st, speed, diameter = 0.194, cylinder_wake.FREE_STREAM, 0.025
    nu = cylinder_wake.FREE_STREAM * cylinder_wake.DIAMETER / cylinder_wake.REYNOLDS
    print(f"viscosity from the paper's D, U and Re: {nu:.3e} m^2/s")
    print(f"Re of the 25 mm cylinder: {speed * diameter / nu:.0f}")
    print(f"f = St U / D: {st * speed / diameter:.3f} Hz")
    print(f"period: {diameter / (st * speed):.2f} s")


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    wake = load_wake()
    data = load_hot_wire()

    found = record_landmarks(wake, data)
    experiment.number("frames", found["frames"])
    experiment.number("nx", found["nx"])
    experiment.number("ny", found["ny"])
    experiment.number("points", found["points"], ",d")
    experiment.number("h-mm", found["h-mm"], ".2f")
    experiment.number("record-s", found["record-s"], ".0f")
    experiment.number("masked-low", found["masked-low"])
    experiment.number("masked-high", found["masked-high"])
    experiment.number("masked-always", found["masked-always"])
    experiment.number("runs", found["runs"])

    check = stencil_check(experiment)
    experiment.number("order-low", check["order-low"], ".2f")
    experiment.number("order-high", check["order-high"], ".2f")
    experiment.number("stencil-ratio", check["ratio"], ".2f")
    experiment.number(
        "stated-ratio",
        piv.TRUNCATION["least squares"] / piv.TRUNCATION["central"],
        ".2f",
    )
    experiment.number("gain-central", check["gains"]["central"], ".3f")
    experiment.number("gain-squares", check["gains"]["least squares"], ".3f")
    experiment.number("stated-gain", piv.NOISE_GAIN["least squares"], ".3f")

    analysis = cylinder_wake.analyse(wake)
    field = field_vorticity(wake)
    experiment.number("h-over-d", spacing(wake) / cylinder_wake.DIAMETER, ".2f")
    experiment.number("noise-central", field["noise"]["central"], ".2f")
    experiment.number("noise-squares", field["noise"]["least squares"], ".2f")
    experiment.number("noise-ratio", field["noise-ratio"], ".2f")
    experiment.number("neighbours", field["neighbours"], ".2f")
    experiment.number("p99-central", field["p99"]["central"], ".1f")
    experiment.number("p99-squares", field["p99"]["least squares"], ".1f")
    experiment.number("max-central", field["max"]["central"], ".0f")
    experiment.number("max-squares", field["max"]["least squares"], ".0f")
    experiment.number(
        "free-bottom", field["free-bottom"] / cylinder_wake.DIAMETER, ".1f"
    )
    experiment.number("free-top", field["free-top"] / cylinder_wake.DIAMETER, ".1f")
    experiment.number("masked-share", 100 * analysis.masked_fraction, ".1f")

    symmetry = street_symmetry(wake, field["omega"]["central"])
    experiment.number("sym-half", symmetry["half-reflected"], ".2f")
    experiment.number("sym-full", symmetry["full"], ".2f")
    experiment.number("sym-plain", symmetry["half-plain"], "+.2f")
    experiment.number("sym-none", symmetry["none-reflected"], "+.2f")

    experiment.number(
        "recirculation",
        (analysis.recirculation - analysis.cylinder_x) / cylinder_wake.DIAMETER,
        ".2f",
    )

    t = found["probe"].x
    crossing = crossing_frequency(found["probe"].y, t)
    frequency_table(experiment, analysis, crossing)
    experiment.number("f-2d", analysis.frequency["2D"], ".4f")
    experiment.number("f-2d-err", analysis.frequency_err["2D"], ".4f")
    experiment.number("f-5d", analysis.frequency["5D"], ".4f")
    experiment.number("f-welch", analysis.welch_frequency["2D"], ".4f")
    experiment.number("f-published", cylinder_wake.F_PUBLISHED, ".3f")
    experiment.number("harmonic", analysis.harmonic_u, ".3f")
    experiment.number(
        "harmonic-ratio", analysis.harmonic_u / analysis.frequency["2D"], ".2f"
    )
    experiment.number("f-raw-crossings", crossing["raw"], ".3f")
    experiment.number("f-crossings", crossing["frequency"], ".4f")
    experiment.number("f-crossings-err", crossing["block-err"], ".4f")
    experiment.number("periods", crossing["periods"].size)
    experiment.number(
        "period-spread",
        100 * crossing["periods"].std(ddof=1) / crossing["periods"].mean(),
        ".1f",
    )
    experiment.number("rho-1", crossing["rho"][0], ".2f")
    outside = int(np.sum(np.abs(crossing["rho"]) > crossing["band"]))
    experiment.number("rho-outside", outside)
    experiment.number("max-lag", MAX_LAG)
    experiment.number("rho-band", crossing["band"], ".2f")
    experiment.number("effective", crossing["effective"], ".0f")
    experiment.number("naive-err", crossing["naive-err"], ".4f")
    experiment.number("correlated-err", crossing["correlated-err"], ".4f")
    per_block = crossing["periods"].size / cylinder_wake.BLOCKS
    experiment.number("periods-per-block", per_block, ".0f")
    error = crossing["correlated-err"]
    experiment.number(
        "spectral-gap", (cylinder_wake.F_PUBLISHED - analysis.frequency["2D"]), ".4f"
    )
    experiment.number(
        "crossing-gap",
        (cylinder_wake.F_PUBLISHED - crossing["frequency"]) / error,
        ".1f",
    )

    st_err = cylinder_wake.strouhal(error)
    experiment.number("st", analysis.strouhal, ".3f")
    experiment.number("st-err", st_err, ".3f")
    experiment.number(
        "st-crossings", cylinder_wake.strouhal(crossing["frequency"]), ".3f"
    )
    experiment.number("u-top", analysis.free_stream_sample * 100, ".2f")
    experiment.number("u-paper", cylinder_wake.FREE_STREAM * 100, ".2f")
    experiment.number(
        "st-top",
        analysis.frequency["2D"] * cylinder_wake.DIAMETER / analysis.free_stream_sample,
        ".3f",
    )
    experiment.number("roshko-413", analysis.roshko, ".4f")
    experiment.number(
        "roshko-gap", 100 * (1 - analysis.strouhal / analysis.roshko), ".1f"
    )
    experiment.number("fl3-high", roshko_strouhal(ROSHKO_FIT[1] - 1e-9), ".3f")

    result = ost_hotwire.analyse(data)
    hot_wire_table(experiment, data, result)
    diameters = np.array([round(r.diameter * 1e3, 1) for r in data.runs])
    experiment.number("st-hw-low", result.strouhal.min(), ".3f")
    experiment.number("st-hw-high", result.strouhal.max(), ".3f")
    experiment.number("re-hw-low", result.reynolds.min(), ",.0f")
    experiment.number("re-hw-high", result.reynolds.max(), ",.0f")
    experiment.number("st-25-high", result.strouhal[diameters == 25.1].max(), ".3f")
    experiment.number("st-50-low", result.strouhal[diameters == 50.0].min(), ".3f")
    gap = result.strouhal * (1 - result.blockage)
    experiment.number("gap-25", gap[diameters == 25.1].mean(), ".3f")
    experiment.number("gap-50", gap[diameters == 50.0].mean(), ".3f")
    experiment.number("hw-error", 100 * HOT_WIRE_ERROR, ".0f")
    experiment.number("hw-block-high", result.frequency_err.max(), ".2f")
    line = blockage_line(result)
    experiment.number("slope", line["slope"], ".2f")
    experiment.number("slope-err", line["slope-err"], ".2f")
    experiment.number("slope-sigma", line["slope"] / line["slope-err"], ".1f")
    experiment.number("intercept", line["intercept"], ".3f")
    experiment.number("intercept-err", line["intercept-err"], ".3f")

    experiment.figure(
        "fig-wake-keyframes", partial(draw_wake_keyframes, wake, field, analysis)
    )
    experiment.figure(
        "fig-vorticity-stencils", partial(draw_vorticity_stencils, wake, field)
    )
    experiment.figure("fig-shedding", partial(draw_shedding, wake, crossing))
    experiment.figure(
        "fig-strouhal",
        partial(draw_strouhal, data, result, analysis, st_err, line),
    )

    with experiment.capture("scaling-exercise"):
        scaling_exercise()
    with experiment.capture("aliasing-exercise"):
        aliasing_exercise(wake, analysis.frequency["2D"])
    return experiment


if __name__ == "__main__":
    main(run)
