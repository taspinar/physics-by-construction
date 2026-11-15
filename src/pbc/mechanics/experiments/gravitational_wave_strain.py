"""The experiment of the lesson "Gravitational-wave strain".

The inspiral of two bodies (``pbc.mechanics.chirp``) checked against its
closed form, and the committed strain of GW150914 (``pbc.data.gwosc``):
whitened, correlated between the detectors, seen in a spectrogram, and fitted
with the Newtonian chirp (``pbc.data.gwstrain``). Run it as a program to
write the figures, the data of the waveform comparator, and the numbers of
the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.gravitational_wave_strain out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from scipy import signal as sp_signal
from scipy.optimize import brentq

from pbc.authoring import FIGURE_COLOURS
from pbc.data import SAMPLES_DIR
from pbc.data.comparison import waveform_comparison
from pbc.data.figure_provenance import REFERENCE, FigureProvenance, role
from pbc.data.fit import SLOPPY_RATIO
from pbc.data.gwosc import (
    FILES,
    PUBLISHED_CHIRP_MASS_SOURCE,
    PUBLISHED_REDSHIFT,
    read_strain,
)
from pbc.data.gwstrain import (
    amplitude_spectrum,
    correlation_with_control,
    cut_segment,
    fit_chirp,
    make_whitener,
    models_at_masses,
    noise_sigma,
)
from pbc.data.plotting import (
    check_figure,
    measured_vs_model,
    sequential_image,
)
from pbc.data.series import Series
from pbc.experiment import Experiment, main
from pbc.mechanics import chirp
from pbc.mechanics.dynamics import State
from pbc.mechanics.orbit import orbital_elements

DATASET = "gw150914-strain"
# The provenance each figure of the strain declares (Issue #531): its status
# and credit at the caption and in its PNG, from the card.
CALIBRATED_STRAIN = FigureProvenance(
    status="calibrated",
    dataset=DATASET,
    combines=("processed",),
    processing="Four seconds of the record's calibrated strain of both detectors,"
    " unmodified; the noise spectrum is this lesson's Welch estimate over the whole"
    " file, not part of the record.",
)
SPECTROGRAM = FigureProvenance(
    status="processed",
    dataset=DATASET,
    processing="The record's strain of both detectors whitened, band-passed and"
    " combined, in windows of 62.5 ms: this lesson's code, not part of the record.",
)
MEASURED_VS_MODEL = FigureProvenance(
    status="processed",
    dataset=DATASET,
    combines=("simulated",),
    processing="The Hanford strain whitened and band-passed; the Newtonian chirp"
    " fitted to both detectors, whitened the same way, and its residuals: this"
    " lesson's code, not part of the record.",
)
PROFILE = FigureProvenance(
    status="processed",
    dataset=DATASET,
    processing="The chi-square of the Newtonian chirp fitted to the processed strain,"
    " profiled over the chirp mass: this lesson's code, not part of the record; the"
    " published chirp mass for comparison.",
)

# region: example
m1, m2, f_start = 36.0, 29.0, 35.0  # solar masses, Hz: given values of the example
# endregion: example
# region: band
BAND = (35.0, 350.0)  # Hz, the band of the primary analysis
# endregion: band
# region: window
PRIMARY_WINDOW = (-0.2, 0.0)
# endregion: window


def inspiral_check(experiment: Experiment):
    """The inspiral integrated numerically against the closed form, and the
    orbit at the start through the orbit module of the Kepler lesson;
    record the table and return the largest relative difference, the
    frequency of the orbit, in Hz, and the rows."""
    mc_example = chirp.chirp_mass(m1, m2)
    tau0 = chirp.time_to_coalescence(f_start, mc_example)
    times = np.linspace(0.0, 0.95 * tau0, 400)
    _, f_numeric = chirp.inspiral_frequency(times, m1, m2, f_start)
    f_closed = chirp.chirp_frequency(times, mc_example, tau0)
    worst = float(np.max(np.abs(f_numeric / f_closed - 1.0)))

    # The orbit at the start, through the orbit module of the Kepler lesson.
    a0 = float(chirp.separation_from_frequency(f_start, m1 + m2))
    gm_total = (m1 + m2) * chirp.GM_SUN
    start = State(0.0, np.array([a0, 0.0]), np.array([0.0, np.sqrt(gm_total / a0)]))
    orbit = orbital_elements(start, gm_total)
    f_from_orbit = 2.0 / orbit.period

    rows = []
    for fraction in (0.0, 0.5, 0.9, 0.95):
        k = min(round(fraction * (len(times) - 1) / 0.95), len(times) - 1)
        a_k = float(chirp.separation_from_frequency(f_numeric[k], m1 + m2))
        rows.append((times[k], f_numeric[k], f_closed[k], a_k / 1e3))
    experiment.table(
        "inspiral-check",
        rows,
        columns=[
            ("time", "s", ".3f"),
            ("frequency, integrated orbit", "Hz", ".1f"),
            ("frequency, closed form", "Hz", ".1f"),
            ("separation", "km", ".0f"),
        ],
        caption="The inspiral of two bodies integrated numerically and from the "
        "closed form.",
    )
    return worst, f_from_orbit, rows


def load_strain():
    """The strain of both detectors from the committed sample, with the raw
    RMS of each."""
    strains = {
        name: read_strain(SAMPLES_DIR / "gw150914-strain" / file)
        for name, file in FILES.items()
    }
    assert all(
        s.event.startswith("GW150914") and s.sample_rate == 4096.0
        for s in strains.values()
    )
    raw_rms = {name: float(np.std(s.strain)) for name, s in strains.items()}
    return strains, raw_rms


def draw_calibrated_strain(strains) -> Figure:
    """Four seconds of the calibrated strain and the noise spectrum."""
    segments = {name: cut_segment(s) for name, s in strains.items()}
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(7.2, 6.2), constrained_layout=True)
    for k, (name, seg) in enumerate(segments.items()):
        (line,) = top.plot(
            seg.time, seg.strain * 1e19, lw=0.6, color=FIGURE_COLOURS[k], label=name
        )
        role(line, "calibrated")
        freqs, asd = amplitude_spectrum(strains[name])
        (line,) = bottom.loglog(
            freqs[1:], asd[1:], lw=0.9, color=FIGURE_COLOURS[k], label=name
        )
        role(line, "processed")
    top.set_xlabel("time since the event [s]")
    top.set_ylabel("strain, calibrated [1e-19]")
    top.set_title("Calibrated strain of the two detectors, four seconds")
    top.legend(loc="upper right")
    bottom.set_xlim(10, 2000)
    bottom.set_xlabel("frequency [Hz]")
    bottom.set_ylabel("amplitude spectral density [1/sqrt(Hz)]")
    bottom.set_title("Noise spectrum: Welch estimate over the whole file (processed)")
    bottom.legend(loc="upper right")
    return fig


def whitened(strains):
    """Two seconds around the event, whitened and band-passed, the noise in
    these units, and the processing steps as the figures disclose them."""
    duration = strains["H1"].duration
    big = {name: cut_segment(s, 2.0) for name, s in strains.items()}
    whiteners_big = {
        name: make_whitener(strains[name], big[name], BAND) for name in strains
    }
    white_big = {name: whiteners_big[name](big[name].strain) for name in strains}
    time_big = big["H1"].time
    sigma_big = noise_sigma(white_big["H1"], time_big, (0.5, 1.6))
    steps = ("whitened", f"band-passed {BAND[0]:g} to {BAND[1]:g} Hz")
    steps_long = (
        f"whitened by the Welch spectrum of the {duration:g} s file, "
        f"band-passed {BAND[0]:g} to {BAND[1]:g} Hz, "
        "cut to the seconds around the event"
    )
    return big, white_big, time_big, sigma_big, steps, steps_long


def detector_correlation(white_big, time_big, rate):
    """The correlation of the two detectors and of quiet control windows."""
    corr = correlation_with_control(white_big["H1"], white_big["L1"], time_big, rate)
    control_max = float(corr["controls"].max())
    lag_ms = 1e3 * corr["lag"]
    return corr, control_max, lag_ms


def spectrogram_data(big, white_big, corr, rate):
    """The spectrogram of the two detectors combined, as excess power over
    the median before the event, in dB."""
    shift = round(corr["lag"] * rate)
    sign = -1.0 if corr["correlation"] < 0 else 1.0
    combined = white_big["H1"] + sign * np.roll(white_big["L1"], -shift)
    n_window = 256
    f_grid, t_grid, power = sp_signal.spectrogram(
        combined, rate, nperseg=n_window, noverlap=n_window - 16, nfft=2048
    )
    t_grid = t_grid + big["H1"].time[0]
    shown_t = (t_grid > -0.4) & (t_grid < 0.15)
    shown_f = (f_grid > 20) & (f_grid < 350)
    excess = 10 * np.log10(
        power[np.ix_(shown_f, shown_t)]
        / np.median(power[shown_f][:, t_grid < -0.5], axis=1)[:, None]
    )
    window_length = n_window / rate
    frequency_width = 1.0 / window_length
    return (
        f_grid,
        t_grid,
        power,
        shown_t,
        shown_f,
        excess,
        window_length,
        frequency_width,
    )


def draw_spectrogram(f_grid, t_grid, shown_t, shown_f, excess) -> Figure:
    """The spectrogram of the two detectors combined."""
    fig, ax = plt.subplots(figsize=(7.4, 4.6), constrained_layout=True)
    extent = (
        t_grid[shown_t][0],
        t_grid[shown_t][-1],
        f_grid[shown_f][0],
        f_grid[shown_f][-1],
    )
    image = sequential_image(
        ax,
        excess,
        label="excess power",
        unit="dB",
        extent=extent,
        aspect="auto",
        vmin=0,
        vmax=np.percentile(excess, 99.5),
    )
    ax.set_xlabel("time since the event [s]")
    ax.set_ylabel("frequency [Hz]")
    ax.set_title("Spectrogram of the two detectors combined (processed)")
    role(image, "processed")
    return fig


def analyse(strains, seg, corr, band, window, step=1.0, span=(22.0, 50.0)):
    """Fit the Newtonian chirp to both detectors in a band and a window."""
    time_fit = seg["H1"].time
    whiteners = {
        name: make_whitener(strains[name], seg[name], band) for name in strains
    }
    data = {name: whiteners[name](seg[name].strain) for name in strains}
    sigma = noise_sigma(data["H1"], time_fit, (0.3, 0.65))
    result = fit_chirp(
        time_fit,
        data,
        whiteners,
        {"H1": 0.0, "L1": corr["lag"]},
        window=window,
        sigma=sigma,
        mc_grid=np.arange(span[0], span[1], step),
    )
    return result, data, sigma


def primary_fit(strains, corr):
    """The fit of the primary band and window, and the frequency and its rate
    of the fitted chirp at the ends of the window."""
    seg = {name: cut_segment(s, 0.75) for name, s in strains.items()}
    primary, data_fit, sigma_fit = analyse(strains, seg, corr, BAND, PRIMARY_WINDOW)
    mc_fit = primary.mc
    f_at_end = float(chirp.chirp_frequency(PRIMARY_WINDOW[1], mc_fit, primary.t_c))
    f_at_start = float(chirp.chirp_frequency(PRIMARY_WINDOW[0], mc_fit, primary.t_c))
    fdot_at_end = float(chirp.chirp_rate(f_at_end, mc_fit))
    check_mc = float(chirp.chirp_mass_from_rate(f_at_end, fdot_at_end))
    return (
        seg,
        primary,
        data_fit,
        sigma_fit,
        f_at_start,
        f_at_end,
        fdot_at_end,
        check_mc,
    )


def measured_and_model(seg, primary, data_fit, sigma_fit, steps):
    """The whitened Hanford strain around the event and the fitted model, as
    series that disclose what they are."""
    time_fit = seg["H1"].time
    show = (time_fit > -0.25) & (time_fit < 0.05)
    measured = Series(
        x=time_fit[show],
        y=data_fit["H1"][show],
        sigma=np.full(show.sum(), sigma_fit),
        artifact="calibrated-observation",
        steps=steps,
        x_name="time since the event",
        x_unit="s",
        y_name="whitened strain",
        y_unit="1",
    )
    model = Series(
        x=time_fit[show],
        y=primary.models["H1"][show],
        artifact="synthetic-test",
        x_name="time since the event",
        x_unit="s",
        y_name="whitened strain",
        y_unit="1",
    )
    return measured, model


def draw_measured_vs_model(measured, model) -> Figure:
    """The measured strain against the fitted chirp, with the residuals."""
    fig, _ = measured_vs_model(
        measured,
        {"Newtonian chirp (fitted)": model},
        window=PRIMARY_WINDOW,
        figsize=(8.6, 6.0),
        declared=True,
    )
    check_figure(fig, residuals=True, declared=MEASURED_VS_MODEL.status)
    return fig


def chirp_masses(strains, seg, corr, primary, data_fit, sigma_fit):
    """The data of the waveform comparator: the best chirp at a range of
    fixed masses."""
    time_fit = seg["H1"].time
    mc_fit = primary.mc
    compared_masses = np.unique(np.append(np.arange(24.0, 46.0, 2.0), round(mc_fit, 3)))
    white_fit = {
        name: make_whitener(strains[name], seg[name], BAND) for name in strains
    }
    compared = models_at_masses(
        time_fit,
        data_fit,
        white_fit,
        {"H1": 0.0, "L1": corr["lag"]},
        compared_masses,
        window=PRIMARY_WINDOW,
        sigma=sigma_fit,
        mc_start=mc_fit,
        t_c_start=primary.t_c,
    )
    return waveform_comparison(
        time_fit,
        data_fit["H1"],
        compared,
        "H1",
        sigma=sigma_fit,
        window=PRIMARY_WINDOW,
        show=(-0.25, 0.05),
        quantity="whitened strain",
        unit="1",
        best=round(mc_fit, 3),
    )


def ridge_table(experiment: Experiment, f_grid, t_grid, power, primary) -> None:
    """The strongest spectrogram cell against the fitted chirp at six times;
    record the table."""
    ridge_times = [-0.06, -0.05, -0.04, -0.03, -0.02, -0.01]
    low = f_grid < 200
    rows = []
    for moment in ridge_times:
        column = int(np.argmin(np.abs(t_grid - moment)))
        strongest = float(f_grid[low][np.argmax(power[low, column])])
        rows.append(
            (
                moment,
                strongest,
                float(chirp.chirp_frequency(moment, primary.mc, primary.t_c)),
            )
        )
    experiment.table(
        "ridge-table",
        rows,
        columns=[
            ("time since the event", "s", ".2f"),
            ("strongest cell of the spectrogram", "Hz", ".0f"),
            ("fitted chirp", "Hz", ".0f"),
        ],
        caption="The frequency of the strongest spectrogram cell and of the fitted "
        "Newtonian chirp at six times before the event.",
    )


def fit_diagnostics(primary):
    """The warnings of the fit and the conditioning of its Jacobian."""
    fit_warnings = primary.fit.warnings
    singular_ratio = primary.fit.singular_ratio
    print("fit warnings:", "; ".join(fit_warnings) if fit_warnings else "none")
    print(
        "smallest over largest singular value of the scaled Jacobian:"
        f" {singular_ratio:.1e}"
    )


def sensitivity(experiment: Experiment, strains, seg, corr, primary):
    """The best chirp mass for each choice of band and window; record the
    table and return the spread of the usable results."""
    bands = [(35.0, 350.0), (35.0, 250.0), (30.0, 300.0)]
    windows = [(-0.2, 0.0), (-0.15, 0.0), (-0.2, -0.01)]
    rows, usable = [], []
    choices = [(band, windows[0]) for band in bands] + [
        (bands[0], window) for window in windows[1:]
    ]
    for band, window in choices:
        # The first choice is the fit above; it is not computed a second time.
        if (band, window) == (BAND, PRIMARY_WINDOW):
            result = primary
        else:
            result, _, _ = analyse(
                strains, seg, corr, band, window, step=2.0, span=(26.0, 48.0)
            )
        rows.append(
            (
                f"{band[0]:g} to {band[1]:g}",
                f"{window[0]:g} to {window[1]:g}",
                result.mc,
                result.t_c * 1e3,
                "end of the search: not a result" if result.at_edge else "",
            )
        )
        if not result.at_edge:
            usable.append(result.mc)
    spread = (min(usable), max(usable))
    experiment.table(
        "sensitivity",
        rows,
        columns=[
            ("band", "Hz", "s"),
            ("window", "s", "s"),
            ("chirp mass", "solar masses", ".1f"),
            ("coalescence time", "ms", ".0f"),
            ("note", "", "s"),
        ],
        caption="Best chirp mass for each choice of band and window of the fit. "
        "The first row is the fit above; the other rows search a grid of masses "
        "with a step of two solar masses.",
    )
    return spread


def draw_profile(primary, published_detector) -> Figure:
    """The profile of the chi-square over the chirp mass."""
    fig, ax = plt.subplots(figsize=(6.8, 3.8), constrained_layout=True)
    delta = primary.profile_chi2 - primary.profile_chi2.min()
    (line,) = ax.semilogy(
        primary.profile_mc,
        np.maximum(delta, 1e-2),
        color=FIGURE_COLOURS[0],
        label="profile of the fit",
    )
    role(line, "processed")
    role(
        ax.axhline(1.0, color="0.4", linestyle=":", label="minimum plus one"),
        REFERENCE,  # a threshold and a published value, drawn for comparison
    )
    role(
        ax.axvline(
            published_detector,
            color=FIGURE_COLOURS[1],
            linestyle="--",
            label="published value, detector frame",
        ),
        REFERENCE,
    )
    ax.set_xlabel("chirp mass, detector frame [solar masses]")
    ax.set_ylabel("chi-square above its minimum [1]")
    ax.set_title("Fit of the Newtonian chirp: profile over the chirp mass")
    ax.legend()
    return fig


def mass_from_a_rate():
    """Exercise 1: the chirp mass of a signal at 60 Hz rising by 120 Hz/s."""
    exercise_mc = float(chirp.chirp_mass_from_rate(60.0, 120.0))
    print(f"chirp mass: {exercise_mc:.1f} solar masses")


def frequency_at_three_radii():
    """Exercise 2: the frequency at which two bodies of 65 solar masses are
    three Schwarzschild radii apart."""
    total = 65.0
    target = 3 * chirp.schwarzschild_radius(total)
    f_limit = brentq(
        lambda f: float(chirp.separation_from_frequency(f, total)) - target,
        20.0,
        5000.0,
    )
    print(f"frequency: {f_limit:.0f} Hz")


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    worst, f_from_orbit, rows = inspiral_check(experiment)
    experiment.number("worst", worst, ".0e")
    experiment.number("checked-share", 100 * 0.95, ".0f")
    experiment.number("f-from-orbit", f_from_orbit, ".1f")
    experiment.number("last-separation", rows[-1][3], ".0f")
    experiment.number("horizon", chirp.schwarzschild_radius(m1 + m2) / 1e3, ".0f")
    experiment.number("sample-rate", 4096)

    strains, raw_rms = load_strain()
    published_detector = PUBLISHED_CHIRP_MASS_SOURCE * (1 + PUBLISHED_REDSHIFT)
    rate = strains["H1"].sample_rate
    experiment.figure(
        "fig-calibrated-strain",
        partial(draw_calibrated_strain, strains),
        provenance=CALIBRATED_STRAIN,
    )
    experiment.number("raw-rms", raw_rms["H1"] * 1e19, ".1f")

    big, white_big, time_big, sigma_big, steps, steps_long = whitened(strains)
    experiment.number("steps-long", steps_long)
    experiment.number("sigma-big", sigma_big, ".2f")
    corr, control_max, lag_ms = detector_correlation(white_big, time_big, rate)
    experiment.number("correlation", abs(corr["correlation"]), ".2f")
    experiment.number("lag-ms", abs(lag_ms), ".1f")
    experiment.number("controls", len(corr["controls"]))
    experiment.number("control-max", control_max, ".2f")

    (
        f_grid,
        t_grid,
        power,
        shown_t,
        shown_f,
        excess,
        window_length,
        frequency_width,
    ) = spectrogram_data(big, white_big, corr, rate)
    experiment.figure(
        "fig-spectrogram",
        partial(draw_spectrogram, f_grid, t_grid, shown_t, shown_f, excess),
        provenance=SPECTROGRAM,
    )
    experiment.number("window-length-ms", 1e3 * window_length, ".1f")
    experiment.number("frequency-width", frequency_width, ".0f")

    (
        seg,
        primary,
        data_fit,
        sigma_fit,
        f_at_start,
        f_at_end,
        fdot_at_end,
        check_mc,
    ) = primary_fit(strains, corr)
    measured, model = measured_and_model(seg, primary, data_fit, sigma_fit, steps)
    experiment.figure(
        "fig-measured-vs-model",
        partial(draw_measured_vs_model, measured, model),
        provenance=MEASURED_VS_MODEL,
    )
    experiment.number("disclosure", measured.disclosure())
    experiment.number("reduced-chi2", primary.reduced_chi2, ".2f")
    experiment.number("n-samples", primary.n_samples)
    experiment.widget(
        "chirp-masses",
        chirp_masses(strains, seg, corr, primary, data_fit, sigma_fit),
    )

    mc_fit, (mc_low, mc_high) = primary.mc, primary.interval
    experiment.number("mc-fit", mc_fit, ".1f")
    experiment.number("t-c-ms", 1e3 * primary.t_c, ".0f")
    experiment.number("f-at-start", f_at_start, ".0f")
    experiment.number("f-at-end", f_at_end, ".0f")
    experiment.number("fdot-at-end", fdot_at_end, ".0f")
    experiment.number("check-mc", check_mc, ".1f")
    experiment.number("mc-low", mc_low, ".1f")
    experiment.number("mc-high", mc_high, ".1f")
    experiment.number("sloppy-ratio", SLOPPY_RATIO, ".0e")
    ridge_table(experiment, f_grid, t_grid, power, primary)
    with experiment.capture("fit-diagnostics"):
        fit_diagnostics(primary)

    spread = sensitivity(experiment, strains, seg, corr, primary)
    experiment.number("spread-low", spread[0], ".0f")
    experiment.number("spread-high", spread[1], ".0f")
    experiment.figure(
        "fig-profile",
        partial(draw_profile, primary, published_detector),
        provenance=PROFILE,
    )
    experiment.number("published-source", PUBLISHED_CHIRP_MASS_SOURCE)
    experiment.number("published-redshift", PUBLISHED_REDSHIFT)
    experiment.number("published-detector", published_detector, ".1f")
    # region: published-comparison
    ratio = mc_fit / published_detector
    # endregion: published-comparison
    experiment.number("mc-fit-whole", mc_fit, ".0f")
    experiment.number("above-published", 100 * (ratio - 1), ".0f")

    with experiment.capture("mass-from-a-rate"):
        mass_from_a_rate()
    with experiment.capture("frequency-at-three-radii"):
        frequency_at_three_radii()
    return experiment


if __name__ == "__main__":
    main(run)
