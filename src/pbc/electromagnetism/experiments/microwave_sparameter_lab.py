"""The experiment of the lesson "Microwave S-parameter lab".

Three on-wafer attenuators measured by the National Physical Laboratory with
a calibrated vector network analyser (the committed sample of the card
``npl-onwafer-sparameters``): the record and its consistency, transmission
as an amplitude and as a power, the energy balance and passivity, a lumped
T network between matched lines (``pbc.electromagnetism.two_port``) fitted
to each pad, what the fit's standard errors assume and how far two
instruments and two halves of the band move it, the Smith chart, and the
3 dB fit carried beyond its band against the single sweep to 220 GHz. Run
it as a program to write the figures and the numbers of the page:

    uv run --locked --no-dev python -m \\
        pbc.electromagnetism.experiments.microwave_sparameter_lab out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.data import SAMPLES_DIR
from pbc.data.adapters import reflection_series, transmission_series
from pbc.data.fit import FitResult, fit_curve
from pbc.data.plotting import COLOURS, add_credit, label_status
from pbc.data.reference.npl_sparameters import FILES
from pbc.data.touchstone import Network, read_touchstone
from pbc.electromagnetism.two_port import (
    TeeAttenuator,
    absorbed_fraction,
    amplitude_db,
    largest_singular_value,
    matched_tee,
    normalised_impedance,
    power_fraction,
    reflection,
)
from pbc.experiment import Experiment, main

DATASET = "npl-onwafer-sparameters"
PADS = ("3", "6", "10")  # the losses the pads are labelled with, dB
SINGLE = "single sweep, 3 dB pad"
# region: fit-settings
NAMES = ("R_series", "R_shunt", "L", "tau")
UNITS = {"R_series": "ohm", "R_shunt": "ohm", "L": "pH", "tau": "ps"}
SCALE = {"R_series": 1.0, "R_shunt": 1.0, "L": 1e-12, "tau": 1e-12}
BAND_TOP = 50e9  # Hz, the top of the coaxial sweeps and of every fit
# endregion: fit-settings
CHECK_FREQUENCIES = (50e9, 100e9, 150e9, 220e9)
CREDIT = (
    "Data: Ausden, Ridler, Rumiantsev, Martens, Shang (NPL), Zenodo "
    "10.5281/zenodo.22658069, CC BY 4.0; _CORR files, unmodified."
)
MEASURED_STYLE = {"lw": 1.6, "ls": "-"}
MODEL_STYLE = {"lw": 1.2, "ls": "--", "color": "0.15"}
MARKERS = ("o", "s", "^")


def coaxial(pad: str) -> str:
    """The name of the coaxial file of a pad in the card's reference module."""
    return "coaxial, " + pad + " dB pad"


def load_networks() -> dict[str, Network]:
    """The four committed files, by the names of the card's reference module."""
    directory = SAMPLES_DIR / DATASET
    return {name: read_touchstone(directory / file) for name, file in FILES.items()}


def record_summary(networks: dict[str, Network]) -> dict:
    """What the files hold, and the consistency of each: reciprocity
    |S21 - S12| and symmetry |S11 - S22| at their largest."""
    single, coax = networks[SINGLE], networks[coaxial("3")]
    out = {
        "coax-points": coax.frequency.size,
        "single-points": single.frequency.size,
        "f-min": coax.frequency[0],
        "coax-max": coax.frequency[-1],
        "single-max": single.frequency[-1],
        "step": float(np.median(np.diff(coax.frequency))),
        "reference": coax.reference_impedance,
    }
    reciprocity, symmetry = {}, {}
    for name, net in networks.items():
        s = net.s
        reciprocity[name] = float(np.abs(s[:, 1, 0] - s[:, 0, 1]).max())
        symmetry[name] = float(np.abs(s[:, 0, 0] - s[:, 1, 1]).max())
    out["reciprocity-coax"] = max(reciprocity[coaxial(p)] for p in PADS)
    out["reciprocity-single"] = reciprocity[SINGLE]
    out["symmetry-coax"] = max(symmetry[coaxial(p)] for p in PADS)
    out["symmetry-single"] = symmetry[SINGLE]
    return out


def power_table(experiment: Experiment, networks: dict[str, Network]) -> dict:
    """Transmission of each coaxial file as an amplitude, as a power, and in
    decibels, and where the incident power goes; record the table and
    return the pads' mean losses and absorbed fractions."""
    rows, out = [], {}
    for pad in PADS:
        s = networks[coaxial(pad)].s
        s21, s11 = s[:, 1, 0], s[:, 0, 0]
        absorbed = absorbed_fraction(s)[:, 0]
        loss = float(-amplitude_db(s21).mean())
        out[pad] = {
            "loss": loss,
            "amplitude": float(np.abs(s21).mean()),
            "transmitted": float(power_fraction(s21).mean()),
            "reflected": float(power_fraction(s11).mean()),
            "absorbed-min": float(absorbed.min()),
            "absorbed-max": float(absorbed.max()),
        }
        rows.append(
            (
                pad,
                out[pad]["amplitude"],
                out[pad]["transmitted"],
                out[pad]["reflected"],
                float(absorbed.mean()),
                loss,
                float(10 ** (-float(pad) / 20)),
            )
        )
    experiment.table(
        "power-balance",
        rows,
        columns=[
            ("pad labelled", "dB", "s"),
            ("|S21|", "", ".3f"),
            ("|S21|^2 transmitted", "", ".3f"),
            ("|S11|^2 reflected", "", ".4f"),
            ("absorbed", "", ".3f"),
            ("loss, -20 log10 |S21|", "dB", ".2f"),
            ("|S21| of the label", "", ".3f"),
        ],
        caption="The three coaxial sweeps, averaged over 2.5-50 GHz: the "
        "transmitted amplitude, the fractions of the incident power transmitted, "
        "reflected, and absorbed (they add to one), and the loss in dB, beside "
        "the amplitude a pad of exactly the labelled loss would pass.",
    )
    return out


def passivity(networks: dict[str, Network]) -> dict:
    """The smallest absorbed fraction at either port and the largest
    singular value of S over every frequency of every file."""
    absorbed = {name: absorbed_fraction(net.s) for name, net in networks.items()}
    singular = {name: largest_singular_value(net.s) for name, net in networks.items()}
    return {
        "absorbed-min": min(float(a.min()) for a in absorbed.values()),
        "absorbed-min-single": float(absorbed[SINGLE].min()),
        "singular-max": max(float(v.max()) for v in singular.values()),
        "singular-max-single": float(singular[SINGLE].max()),
    }


def instruments(networks: dict[str, Network]) -> dict:
    """The two instruments on the 3 dB pad over the coaxial band: the
    largest difference of |S21| in dB and of the complex S11 and S21."""
    single, coax = networks[SINGLE], networks[coaxial("3")]
    keep = single.frequency <= BAND_TOP
    assert np.array_equal(single.frequency[keep], coax.frequency)
    a, b = single.s[keep], coax.s
    db = amplitude_db(a[:, 1, 0]) - amplitude_db(b[:, 1, 0])
    return {
        "db": db,
        "db-max": float(np.abs(db).max()),
        "s21-max": float(np.abs(a[:, 1, 0] - b[:, 1, 0]).max()),
        "s11-max": float(np.abs(a[:, 0, 0] - b[:, 0, 0]).max()),
        "difference": np.maximum(
            np.abs(a[:, 0, 0] - b[:, 0, 0]), np.abs(a[:, 1, 0] - b[:, 1, 0])
        ),
    }


def matched_pad_check(experiment: Experiment) -> float:
    """The T pad designed for each labelled loss, computed as a network:
    record the table and return the largest |S11| and the largest error of
    the loss in dB."""
    rows, worst = [], 0.0
    frequency = np.array([2.5e9, 50e9])
    for pad in PADS:
        series, shunt = matched_tee(float(pad))
        s = TeeAttenuator(series, shunt).s(frequency)
        reflected = float(np.abs(s[:, 0, 0]).max())
        loss = float(-amplitude_db(s[:, 1, 0]).mean())
        worst = max(worst, reflected, abs(loss - float(pad)))
        shown = "below 1e-12" if reflected < 1e-12 else f"{reflected:.0e}"
        rows.append((pad, series, shunt, shown, loss))
    experiment.table(
        "matched-pads",
        rows,
        columns=[
            ("loss designed", "dB", "s"),
            ("R_series", "ohm", ".2f"),
            ("R_shunt", "ohm", ".1f"),
            ("|S11| of the network", "", "s"),
            ("loss of the network", "dB", ".3f"),
        ],
        caption="The resistive T pads matched to 50 ohm for the three labelled "
        "losses, from the closed form, and their S-parameters computed from the "
        "element impedances.",
    )
    return worst


def model_of(result: FitResult) -> TeeAttenuator:
    """The T network of fitted values (ohm, ohm, pH, ps)."""
    r, shunt, inductance, delay = (result.value(n) * SCALE[n] for n in NAMES)
    return TeeAttenuator(r, shunt, inductance, delay)


def fit_pad(
    network: Network,
    keep: np.ndarray | None = None,
    *,
    sigma: float | None = None,
    start: np.ndarray | None = None,
) -> FitResult:
    """Fit R_series, R_shunt, L [pH], and tau [ps] to the real and imaginary
    parts of the complex S11 and S21 at the kept frequencies (all frequencies
    up to 50 GHz when none are given), every sample with the same weight.
    With ``sigma``, the standard uncertainty of every sample, the fit's
    ``reduced_chi2`` tests the model against that noise."""
    if keep is None:
        keep = network.frequency <= BAND_TOP
    frequency = network.frequency[keep]
    measured = np.concatenate([network.s[keep, 0, 0], network.s[keep, 1, 0]])

    def model(_, r, shunt, inductance_ph, delay_ps):
        s = TeeAttenuator(r, shunt, inductance_ph * 1e-12, delay_ps * 1e-12).s(
            frequency
        )
        difference = np.concatenate([s[:, 0, 0], s[:, 1, 0]]) - measured
        return np.concatenate([difference.real, difference.imag])

    if start is None:
        loss = float(-amplitude_db(network.s[keep, 1, 0]).mean())
        start = [*matched_tee(loss), 10.0, 1.0]
    target = np.zeros(4 * frequency.size)
    return fit_curve(
        model, np.arange(target.size), target, start, sigma=sigma, names=NAMES
    )


def misfit(network: Network, tee: TeeAttenuator) -> np.ndarray:
    """max(|S11 model - measured|, |S21 model - measured|) at every frequency."""
    s = tee.s(network.frequency)
    return np.maximum(
        np.abs(s[:, 0, 0] - network.s[:, 0, 0]),
        np.abs(s[:, 1, 0] - network.s[:, 1, 0]),
    )


def neighbour_correlation(result: FitResult) -> float:
    """The correlation of the fit residuals at neighbouring frequencies,
    averaged over the four residual sequences (Re and Im of S11 and S21):
    zero if the residuals were independent, as the standard errors assume."""
    parts = np.asarray(result.residuals).reshape(4, -1)
    return float(np.mean([np.corrcoef(p[:-1], p[1:])[0, 1] for p in parts]))


def point_noise(result: FitResult) -> float:
    """The noise of one sample, from the differences of the residuals at
    neighbouring frequencies: sqrt(mean(difference^2) / 2) over the four
    residual sequences. It assumes noise independent from sample to sample
    and a misfit that changes little over one frequency step, which the
    differences then remove."""
    parts = np.asarray(result.residuals).reshape(4, -1)
    return float(np.sqrt(np.mean(np.diff(parts, axis=1) ** 2) / 2))


def chi_square_test(network: Network, result: FitResult) -> FitResult:
    """The same fit with every sample weighted by its point-to-point noise,
    started at the fitted values: its ``reduced_chi2`` compares the
    residuals with that noise (near 1 if the model left only noise)."""
    return fit_pad(network, sigma=point_noise(result), start=result.params)


def error_decimals(stderr: float) -> int:
    """The decimal places of a standard error rounded to one significant
    figure (0.0096 rounds to 0.01, two places), never fewer than none."""
    places = -int(np.floor(np.log10(stderr)))
    if round(stderr, places) >= 10.0 ** (1 - places):
        places -= 1
    return max(places, 0)


def with_error(value: float, stderr: float) -> str:
    """``value ± stderr``, the standard error at one significant figure and
    the value rounded to the same decimal place, with plain spaces: the page
    collapses any other white space into one."""
    places = error_decimals(stderr)
    return f"{value:.{places}f} ± {stderr:.{places}f}"


def fit_table(
    experiment: Experiment, networks: dict[str, Network]
) -> dict[str, FitResult]:
    """The fit of each coaxial file; record the table of the fitted values
    and the table of the residuals, and return the fits."""
    fits, values, residuals = {}, [], []
    for pad in PADS:
        network = networks[coaxial(pad)]
        result = fit_pad(network)
        fits[pad] = result
        values.append(
            (
                pad,
                *(
                    with_error(result.value(n), float(result.stderr[k]))
                    for k, n in enumerate(NAMES)
                ),
            )
        )
        residuals.append(
            (
                pad,
                float(np.sqrt(np.mean(np.asarray(result.residuals) ** 2))),
                float(misfit(network, model_of(result)).max()),
                neighbour_correlation(result),
                point_noise(result),
                chi_square_test(network, result).reduced_chi2,
            )
        )
    experiment.table(
        "fit",
        values,
        columns=[
            ("pad labelled", "dB", "s"),
            ("R_series", "ohm", "s"),
            ("R_shunt", "ohm", "s"),
            ("L", "pH", "s"),
            ("tau", "ps", "s"),
        ],
        caption="The T network fitted to the complex S11 and S21 of each coaxial "
        "sweep (191 frequencies, 2.5-50 GHz), with the standard errors that "
        "assume independent residuals.",
    )
    experiment.table(
        "fit-residuals",
        residuals,
        columns=[
            ("pad labelled", "dB", "s"),
            ("rms residual", "", ".4f"),
            ("largest misfit", "", ".4f"),
            ("neighbour correlation", "", ".2f"),
            ("point-to-point noise", "", ".4f"),
            ("reduced chi-square", "", ".0f"),
        ],
        caption="The residuals of the fits: the rms of the real and imaginary "
        "parts, the largest misfit |S_model - S_measured|, the correlation "
        "of the residuals at neighbouring frequencies (zero if they were "
        "independent), the noise of one sample estimated from the differences "
        "of neighbouring residuals, and the reduced chi-square of the fit "
        "against that noise (near 1 if the model left only noise).",
    )
    return fits


def sensitivity_table(
    experiment: Experiment, networks: dict[str, Network], full: FitResult
) -> dict:
    """The 3 dB fit repeated on the other instrument and on the two halves
    of the band; record the table and return the largest change of each
    parameter against the full coaxial fit, in units of its standard error
    and as a value."""
    single, coax = networks[SINGLE], networks[coaxial("3")]
    middle = 0.5 * (coax.frequency[0] + BAND_TOP)
    cases = [
        ("coaxial, 2.5-50 GHz", full),
        ("single sweep, 2.5-50 GHz", fit_pad(single)),
        ("coaxial, lower half", fit_pad(coax, coax.frequency < middle)),
        ("coaxial, upper half", fit_pad(coax, coax.frequency >= middle)),
    ]
    rows = [(name, *(r.value(n) for n in NAMES)) for name, r in cases]
    changes = {}
    for k, n in enumerate(NAMES):
        shifts = [abs(r.value(n) - full.value(n)) for _, r in cases[1:]]
        changes[n] = {
            "instrument": abs(cases[1][1].value(n) - full.value(n)),
            "largest": max(shifts),
            "in-errors": max(shifts) / float(full.stderr[k]),
        }
    experiment.table(
        "sensitivity",
        rows,
        columns=[
            ("3 dB pad, fitted to", "", "s"),
            ("R_series", "ohm", ".3f"),
            ("R_shunt", "ohm", ".2f"),
            ("L", "pH", ".2f"),
            ("tau", "ps", ".3f"),
        ],
        caption="The fit of the 3 dB pad on the coaxial sweep, on the single "
        "sweep of the other instrument over the same band, and on the two halves "
        "of the coaxial band (2.5-26.25 and 26.25-50 GHz): a sensitivity of the "
        "fit, not a calibration uncertainty.",
    )
    return changes


def beyond_the_band(networks: dict[str, Network], full: FitResult) -> dict:
    """The 3 dB fit, made on the coaxial sweep to 50 GHz, against the single
    sweep at every frequency to 220 GHz."""
    single = networks[SINGLE]
    error = misfit(single, model_of(full))
    at = {
        f: float(error[int(np.argmin(np.abs(single.frequency - f)))])
        for f in CHECK_FREQUENCIES
    }
    inside = single.frequency <= BAND_TOP
    return {"error": error, "at": at, "inside-max": float(error[inside].max())}


def smith_grid(ax) -> None:
    """The Smith chart's grid: circles of constant normalised resistance and
    arcs of constant normalised reactance, drawn by mapping z to Gamma."""
    grid = {"color": "0.82", "lw": 0.6, "zorder": 0}
    for r in (0.0, 0.2, 0.5, 1.0, 2.0, 5.0):
        g = reflection(r + 1j * np.tan(np.linspace(-1.55, 1.55, 241)))
        ax.plot(g.real, g.imag, **grid)
    for x in (0.2, 0.5, 1.0, 2.0, 5.0):
        for sign in (1, -1):
            g = reflection(np.geomspace(1e-3, 60, 241) + 1j * sign * x)
            ax.plot(g.real, g.imag, **grid)
    ax.plot([-1, 1], [0, 0], **grid)


def draw_transmission(networks: dict[str, Network], fits: dict) -> Figure:
    """|S21| and |S11| in dB of the coaxial sweeps against the fitted T
    networks, and the misfit of each fit; one legend for the three panels."""
    fig, (top, middle, bottom) = plt.subplots(
        3,
        1,
        figsize=(6.0, 5.4),
        sharex=True,
        constrained_layout=True,
        gridspec_kw={"height_ratios": [1.0, 1.0, 0.9]},
    )
    for pad, colour, marker in zip(PADS, COLOURS, MARKERS, strict=False):
        network = networks[coaxial(pad)]
        transmission = transmission_series(network)
        reflected = reflection_series(network)
        tee = model_of(fits[pad])
        s = tee.s(network.frequency)
        style = {"color": colour, "marker": marker, "markevery": 19, "ms": 4}
        top.plot(
            transmission.x,
            transmission.y,
            label=f"{pad} dB pad [{transmission.status}]",
            **style,
            **MEASURED_STYLE,
        )
        middle.plot(reflected.x, reflected.y, **style, **MEASURED_STYLE)
        top.plot(transmission.x, amplitude_db(s[:, 1, 0]), **MODEL_STYLE)
        middle.plot(reflected.x, amplitude_db(s[:, 0, 0]), **MODEL_STYLE)
        bottom.plot(transmission.x, misfit(network, tee), lw=1.0, **style)
    top.plot([], [], label="fitted T network [simulated]", **MODEL_STYLE)
    top.set_ylabel("|S21| [dB]")
    top.set_title("Transmission, coaxial system")
    top.legend(fontsize=7, loc="lower center", ncol=2)
    top.set_ylim(-17.5, -2.0)
    middle.set_ylabel("|S11| [dB]")
    middle.set_title("Reflection at port 1 (same symbols)")
    bottom.set_ylabel("residual misfit [1]")
    bottom.set_xlabel("frequency [GHz]")
    bottom.set_title("Residual: larger of |S11| and |S21| model - measured")
    add_credit(fig, CREDIT)
    label_status(fig, "calibrated")
    return fig


def draw_smith_chart(networks: dict[str, Network], fits: dict) -> Figure:
    """S11 of the three coaxial sweeps and of the single sweep on the centre
    of the Smith chart, with the fitted T networks."""
    fig, ax = plt.subplots(figsize=(5.0, 4.6), constrained_layout=True)
    smith_grid(ax)
    for r, x in ((1.0, 0.0), (2.0, 0.0)):
        g = reflection(r + 1j * x)
        ax.annotate(
            f"r = {r:g}",
            (g.real, g.imag),
            xytext=(3, 3),
            textcoords="offset points",
            fontsize=7,
            color="0.45",
        )
    for x in (0.2, -0.2):
        g = reflection(1.0 + 1j * x)
        ax.annotate(
            f"x = {x:+g}",
            (g.real, g.imag),
            xytext=(3, 3),
            textcoords="offset points",
            fontsize=7,
            color="0.45",
        )
    for pad, colour, marker in zip(PADS, COLOURS, MARKERS, strict=False):
        network = networks[coaxial(pad)]
        gamma = network.s[:, 0, 0]
        ax.plot(
            gamma.real,
            gamma.imag,
            color=colour,
            marker=marker,
            markevery=38,
            ms=3.5,
            label=f"{pad} dB pad, coaxial [calibrated]",
            **MEASURED_STYLE,
        )
        model = model_of(fits[pad]).s(network.frequency)[:, 0, 0]
        ax.plot(model.real, model.imag, **MODEL_STYLE)
    gamma = networks[SINGLE].s[:, 0, 0]
    ax.plot(
        gamma.real,
        gamma.imag,
        color=COLOURS[3],
        lw=0.9,
        label="3 dB pad, single sweep to 220 GHz [calibrated]",
    )
    starts = np.array([networks[coaxial(p)].s[0, 0, 0] for p in PADS])
    ax.plot(starts.real, starts.imag, "kx", ms=6, label="2.5 GHz, start of each sweep")
    ax.plot([], [], label="fitted T networks [simulated]", **MODEL_STYLE)
    ax.set_aspect("equal")
    ax.set_xlim(-0.06, 0.38)
    ax.set_ylim(-0.17, 0.13)
    ax.set_xlabel("Re S11 [1]")
    ax.set_ylabel("Im S11 [1]")
    ax.set_title("Centre of the Smith chart (grey: constant r and x)")
    ax.legend(fontsize=6.8, loc="lower right")
    add_credit(fig, CREDIT)
    label_status(fig, "calibrated")
    return fig


def draw_wideband(
    networks: dict[str, Network], full: FitResult, compared: dict
) -> Figure:
    """The absorbed fraction of every file to 220 GHz, and the misfit of the
    3 dB fit against the single sweep beside the two instruments' difference."""
    single = networks[SINGLE]
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(6.0, 4.6), sharex=True, constrained_layout=True
    )
    names = [coaxial(p) for p in PADS] + [SINGLE]
    for name, colour, line in zip(names, COLOURS, ("-", "--", "-.", ":"), strict=False):
        network = networks[name]
        top.plot(
            network.frequency / 1e9,
            absorbed_fraction(network.s)[:, 0],
            color=colour,
            ls=line,
            lw=1.4,
            label=f"{name} [calibrated]",
        )
    top.axhline(0, color="k", lw=0.8, label="lossless")
    top.set_ylim(-0.05, 1.0)
    top.set_ylabel("1 - |S11|^2 - |S21|^2 [1]")
    top.set_title("Fraction of the power entering port 1 that is absorbed")
    top.legend(fontsize=6.5, loc="lower left", ncol=2)
    ghz = single.frequency / 1e9
    bottom.plot(
        ghz,
        misfit(single, model_of(full)),
        color=COLOURS[3],
        lw=1.2,
        label="3 dB fit (2.5-50 GHz) against the single sweep",
    )
    coax = networks[coaxial("3")]
    bottom.plot(
        coax.frequency / 1e9,
        compared["difference"],
        color="0.35",
        lw=0.9,
        label="single sweep minus coaxial, same pad [calibrated]",
    )
    bottom.axvspan(ghz[0], BAND_TOP / 1e9, color="0.9", zorder=0, label="fitted band")
    bottom.set_yscale("log")
    bottom.set_ylabel("residual misfit [1]")
    bottom.set_xlabel("frequency [GHz]")
    bottom.set_title("Misfit of the 3 dB fit, and two instruments on one pad")
    bottom.legend(fontsize=6.5, loc="lower right")
    add_credit(fig, CREDIT)
    label_status(fig, "calibrated")
    return fig


def decibel_exercise() -> None:
    """Exercise 1: amplitude, power, and decibels of a transmission of 0.5."""
    s21 = 0.5
    print(f"power transmitted: {power_fraction(s21):.2f} of the incident power")
    print(f"loss: {-amplitude_db(s21):.2f} dB")
    print(
        f"ten times log10 of the amplitude, a wrong loss: {-10 * np.log10(s21):.2f} dB"
    )
    print(f"amplitude of a pad of exactly three decibels: {10 ** (-3 / 20):.3f}")


def design_exercise() -> None:
    """Exercise 2: a matched 20 dB T pad and the impedance seen at its input."""
    series, shunt = matched_tee(20.0)
    s = TeeAttenuator(series, shunt).s([1e9])
    print(f"R_series: {series:.2f} ohm, R_shunt: {shunt:.2f} ohm")
    print(f"|S11|: {abs(s[0, 0, 0]):.0e}")
    print(f"normalised input impedance: {normalised_impedance(s[0, 0, 0]).real:.3f}")
    print(f"power absorbed: {absorbed_fraction(s)[0, 0]:.3f} of the incident power")


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    worst = matched_pad_check(experiment)
    experiment.number(
        "matched-error", "below 1e-12" if worst < 1e-12 else f"{worst:.0e}"
    )

    networks = load_networks()
    record = record_summary(networks)
    experiment.number("coax-points", record["coax-points"])
    experiment.number("single-points", record["single-points"])
    experiment.number("f-min", record["f-min"] / 1e9, ".1f")
    experiment.number("coax-max", record["coax-max"] / 1e9, ".0f")
    experiment.number("single-max", record["single-max"] / 1e9, ".0f")
    experiment.number("step", record["step"] / 1e6, ".0f")
    experiment.number("reference", record["reference"], ".0f")
    experiment.number("reciprocity-coax", record["reciprocity-coax"], ".1e")
    experiment.number("reciprocity-single", record["reciprocity-single"], ".3f")
    experiment.number("symmetry-coax", record["symmetry-coax"], ".3f")
    experiment.number("symmetry-single", record["symmetry-single"], ".3f")

    pads = power_table(experiment, networks)
    for pad in PADS:
        experiment.number(f"loss-{pad}", pads[pad]["loss"], ".2f")
    experiment.number("amplitude-3", pads["3"]["amplitude"], ".3f")
    experiment.number("transmitted-3", pads["3"]["transmitted"], ".3f")
    experiment.number("reflected-3", pads["3"]["reflected"], ".4f")
    experiment.number(
        "absorbed-3", 1 - pads["3"]["transmitted"] - pads["3"]["reflected"], ".3f"
    )
    experiment.number("wrong-loss-3", pads["3"]["loss"] / 2, ".2f")

    passive = passivity(networks)
    experiment.number("absorbed-min", passive["absorbed-min"], ".2f")
    experiment.number("singular-max", passive["singular-max"], ".2f")

    compared = instruments(networks)
    experiment.number("instrument-db", compared["db-max"], ".3f")
    experiment.number("instrument-s21", compared["s21-max"], ".4f")
    experiment.number("instrument-s11", compared["s11-max"], ".4f")

    fits = fit_table(experiment, networks)
    full = fits["3"]
    for name, spec in zip(NAMES, (".2f", ".1f", ".1f", ".3f"), strict=True):
        experiment.number(
            "fit-" + name.lower().replace("_", "-"), full.value(name), spec
        )
    matched = matched_tee(pads["3"]["loss"])
    experiment.number("matched-series", matched[0], ".1f")
    experiment.number("matched-shunt", matched[1], ".1f")
    low = model_of(full).s([record["f-min"]])[0, 0, 0]
    experiment.number("model-input", 50 * normalised_impedance(low).real, ".1f")
    rms = [float(np.sqrt(np.mean(np.asarray(f.residuals) ** 2))) for f in fits.values()]
    experiment.number("rms-low", min(rms), ".4f")
    experiment.number("rms-high", max(rms), ".4f")
    worst_fit = max(
        float(misfit(networks[coaxial(p)], model_of(fits[p])).max()) for p in PADS
    )
    experiment.number("misfit-max", worst_fit, ".3f")
    correlations = [neighbour_correlation(f) for f in fits.values()]
    experiment.number("correlation-low", min(correlations), ".2f")
    experiment.number("correlation-high", max(correlations), ".2f")
    noises = [point_noise(f) for f in fits.values()]
    experiment.number("noise-low", min(noises), ".4f")
    experiment.number("noise-high", max(noises), ".4f")
    chi2 = [chi_square_test(networks[coaxial(p)], fits[p]).reduced_chi2 for p in PADS]
    experiment.number("chi2-low", min(chi2), ".0f")
    experiment.number("chi2-high", max(chi2), ".0f")
    experiment.number(
        "fit-warnings",
        "; ".join(w for f in fits.values() for w in f.warnings) or "none",
    )
    without = fit_without_inductance(networks[coaxial("3")])
    experiment.number("rms-without-l", without, ".4f")
    experiment.number("rms-ratio-l", without / rms[0], ".0f")

    changes = sensitivity_table(experiment, networks, full)
    experiment.number("instrument-r", changes["R_series"]["instrument"], ".3f")
    experiment.number(
        "instrument-r-errors", changes["R_series"]["instrument"] / full.stderr[0], ".0f"
    )
    experiment.number("sensitivity-r", changes["R_series"]["largest"], ".2f")
    experiment.number("sensitivity-shunt", changes["R_shunt"]["largest"], ".1f")
    experiment.number("sensitivity-l", changes["L"]["largest"], ".1f")
    experiment.number("sensitivity-tau", changes["tau"]["largest"], ".3f")
    experiment.number(
        "sensitivity-errors", max(c["in-errors"] for c in changes.values()), ".0f"
    )

    beyond = beyond_the_band(networks, full)
    experiment.number("beyond-inside", beyond["inside-max"], ".4f")
    for f in CHECK_FREQUENCIES[1:]:
        experiment.number(f"beyond-{f / 1e9:.0f}", beyond["at"][f], ".3f")
    experiment.number("beyond-ratio", beyond["at"][220e9] / compared["s21-max"], ".0f")
    phase = 2 * np.pi * 220e9 * full.value("tau") * 1e-12
    experiment.number("delay-phase", phase, ".1f")

    experiment.figure("fig-transmission", partial(draw_transmission, networks, fits))
    experiment.figure("fig-smith-chart", partial(draw_smith_chart, networks, fits))
    experiment.figure("fig-wideband", partial(draw_wideband, networks, full, compared))

    with experiment.capture("decibel-exercise"):
        decibel_exercise()
    with experiment.capture("design-exercise"):
        design_exercise()
    return experiment


def fit_without_inductance(network: Network) -> float:
    """The rms residual of the T network fitted with L = 0: the series
    inductance is what the other fits need beyond the resistors."""
    keep = network.frequency <= BAND_TOP
    frequency = network.frequency[keep]
    measured = np.concatenate([network.s[keep, 0, 0], network.s[keep, 1, 0]])

    def model(_, r, shunt, delay_ps):
        s = TeeAttenuator(r, shunt, 0.0, delay_ps * 1e-12).s(frequency)
        difference = np.concatenate([s[:, 0, 0], s[:, 1, 0]]) - measured
        return np.concatenate([difference.real, difference.imag])

    loss = float(-amplitude_db(network.s[keep, 1, 0]).mean())
    target = np.zeros(4 * frequency.size)
    result = fit_curve(model, np.arange(target.size), target, [*matched_tee(loss), 1.0])
    return float(np.sqrt(np.mean(np.asarray(result.residuals) ** 2)))


if __name__ == "__main__":
    main(run)
