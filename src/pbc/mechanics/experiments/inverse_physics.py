"""The experiment of the lesson "Inverse physics: discovering parameters".

The recovery of known parameters from synthetic data (``pbc.data.inverse``),
a parameter the data do not determine, a wrong model, and the chirp mass of
GW150914 with injections into its noise (``pbc.data.gwinjection``); and the
series RLC circuit of ``pbc.electromagnetism.circuits`` identified from its
step response and from its impedance. Run it
as a program to write the figures and numbers of the page:

    uv run --locked --no-dev python -m pbc.mechanics.experiments.inverse_physics out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.ticker import NullFormatter

from pbc.authoring import FIGURE_COLOURS
from pbc.data import SAMPLES_DIR
from pbc.data.fit import fit_curve
from pbc.data.gwinjection import inject_and_fit
from pbc.data.gwosc import (
    FILES,
    PUBLISHED_CHIRP_MASS_SOURCE,
    PUBLISHED_REDSHIFT,
    read_strain,
)
from pbc.data.gwstrain import (
    correlation_with_control,
    cut_segment,
    fit_chirp,
    make_whitener,
    noise_sigma,
)
from pbc.data.inverse import (
    Recovery,
    profile,
    recover,
    residual_autocorrelation,
    verdict,
)
from pbc.electromagnetism.circuits import SeriesRLC, step_response
from pbc.experiment import Experiment, main
from pbc.figure_language import LINE, figsize, figure_style, finish
from pbc.mechanics import chirp


def damped(t, amplitude, decay, omega, phase):
    return amplitude * np.exp(-decay * t) * np.cos(omega * t + phase)


# region: setup
NAMES = ["amplitude", "decay", "omega", "phase"]
TRUTH = [1.0, 0.35, 5.0, 0.4]
SIGMA = 0.05
t = np.linspace(0.0, 6.0, 120)
# endregion: setup
# region: tied
K_TRUE, M_TRUE = 4.0, 1.0
k_grid = np.linspace(1.0, 10.0, 37)
bound = ([1e-3, 1e-3], [np.inf, np.inf])
# endregion: tied
# region: strain
BAND = (35.0, 350.0)
WINDOW = (-0.2, 0.0)
# endregion: strain
# region: injection
TRUTH_MC, TRUTH_TC = 35.0, 0.03
CENTRES = [-12.0, -8.0, 8.0, 12.0]  # seconds from the event: no event there
# endregion: injection
# region: rlc
RLC_NAMES = ("R", "L", "C")
RLC_TRUTH = (10.0, 10.0, 1.0)  # ohm, mH, µF
RLC_TOLERANCE = 0.02  # relative: bias and scatter of each recovered parameter
STEP_SIGMA = 0.01  # V, noise of the capacitor voltage after a step of 1 V
step_times = np.linspace(0.0, 5e-3, 200)  # s
IMPEDANCE_SIGMA = 0.5  # ohm, noise of the real and the imaginary part
sweep = np.geomspace(3e3, 3e4, 40)  # rad/s, around the resonance at 1e4
low_sweep = np.geomspace(5e2, 3e3, 40)  # rad/s, below it
# endregion: rlc


def recovery(experiment: Experiment):
    """The recovery of the four parameters of a damped oscillation from 200
    noisy copies; record the table."""
    report = recover(damped, t, TRUTH, sigma=SIGMA, trials=200, seed=11, names=NAMES)
    experiment.table(
        "recovery",
        [
            (name, truth, mean, rms, stated, 100 * cover)
            for name, truth, mean, rms, stated, cover in zip(
                report.names,
                report.truth,
                report.mean,
                report.rms_error,
                report.mean_stderr,
                report.coverage,
                strict=True,
            )
        ],
        columns=[
            ("parameter", "", "s"),
            ("truth", "", ".3f"),
            ("mean estimate", "", ".3f"),
            ("scatter of the estimates", "", ".4f"),
            ("stated standard error", "", ".4f"),
            ("interval holds the truth", "%", ".0f"),
        ],
        caption="Recovery of the four parameters of a damped oscillation from 200 "
        "noisy copies. The scatter is the root-mean-square error of one estimate.",
    )
    return report


def spring_mass(t, k, m):
    """Free oscillation of a mass on a spring: only k/m reaches the motion."""
    return np.cos(np.sqrt(k / m) * t)


def tied_parameters():
    """A fit of k and m to the free oscillation, which tells only their
    ratio, and the profile of k."""
    rng = np.random.default_rng(2)
    y_free = spring_mass(t, K_TRUE, M_TRUE) + rng.normal(0.0, SIGMA, t.size)
    tied = fit_curve(
        spring_mass, t, y_free, [4.5, 1.1], sigma=SIGMA, names=["k", "m"], bounds=bound
    )
    profile_k = profile(
        spring_mass,
        t,
        y_free,
        [K_TRUE, M_TRUE],
        "k",
        k_grid,
        sigma=SIGMA,
        names=["k", "m"],
        bounds=bound,
    )
    print("reasons against the fit:")
    for reason in verdict(tied):
        print(" -", reason)
    print(
        "profile of k: rise of the chi-square over the whole range ="
        f" {np.ptp(profile_k.chi2):.2f}"
    )
    return tied, profile_k


def frequency_profile():
    """A damped oscillation with noise, and the profile of its angular
    frequency."""
    rng = np.random.default_rng(1)
    y_damped = damped(t, *TRUTH) + rng.normal(0.0, SIGMA, t.size)
    w_grid = np.linspace(4.95, 5.05, 41)
    profile_w = profile(
        damped, t, y_damped, TRUTH, "omega", w_grid, sigma=SIGMA, names=NAMES
    )
    return y_damped, profile_w


def draw_profiles(profile_w, profile_k) -> Figure:
    """The profile of a determined and of an undetermined parameter."""
    with figure_style():
        fig, (top, bottom) = plt.subplots(2, 1, figsize=figsize("pair"), sharey=True)
        top.semilogy(
            profile_w.grid,
            np.maximum(profile_w.chi2 - profile_w.chi2.min(), 1e-3),
            color=FIGURE_COLOURS[0],
        )
        top.set_xlabel("angular frequency (rad/s)")
        top.set_title("Determined")
        bottom.semilogy(
            profile_k.grid,
            np.maximum(profile_k.chi2 - profile_k.chi2.min(), 1e-3),
            color=FIGURE_COLOURS[1],
        )
        bottom.set_xlabel("spring constant (N/m)")
        bottom.set_title("Not determined")
        for ax in (top, bottom):
            ax.axhline(1.0, color="0.4", linestyle=":", linewidth=LINE["guide"])
            ax.set_ylabel("chi-square above\nits minimum")
    return finish(fig)


def wrong_model(y_damped):
    """The damped model fitted to a linear loss and to its own data."""
    envelope = np.clip(1.0 - t / 5.0, 0.0, None)  # linear loss: dry friction
    rng = np.random.default_rng(5)
    y_dry = envelope * np.cos(5.0 * t + 0.4) + rng.normal(0.0, SIGMA, t.size)
    wrong = fit_curve(damped, t, y_dry, TRUTH, sigma=SIGMA, names=NAMES)
    right_fit = fit_curve(damped, t, y_damped, TRUTH, sigma=SIGMA, names=NAMES)
    print("wrong model, reasons against:")
    for reason in verdict(wrong):
        print(" -", reason)
    print("right model, reasons against:", verdict(right_fit) or "none")
    return wrong, right_fit


def draw_residuals(wrong, right_fit) -> Figure:
    """The residuals of the right and of the wrong model."""
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line"))
        ax.plot(t, right_fit.residuals / SIGMA, color="0.55", label="right model")
        ax.plot(
            t, wrong.residuals / SIGMA, color=FIGURE_COLOURS[0], label="wrong model"
        )
        ax.axhline(0.0, color="0.3", linewidth=LINE["guide"])
        ax.set_xlabel("time (s)")
        ax.set_ylabel("residual (noise units)")
        # The legend would cover the curves: under the plot, in one column.
        fig.legend(loc="outside lower center", ncols=1)
    return finish(fig)


def strain_fit():
    """The chirp fitted to the committed strain of GW150914, as in the strain
    lesson."""
    gw_strains = {
        det: read_strain(SAMPLES_DIR / "gw150914-strain" / file)
        for det, file in FILES.items()
    }
    gw_rate = gw_strains["H1"].sample_rate
    gw_wide = {det: cut_segment(s, 2.0) for det, s in gw_strains.items()}
    gw_white = {
        det: make_whitener(gw_strains[det], gw_wide[det], BAND)(gw_wide[det].strain)
        for det in gw_strains
    }
    gw_corr = correlation_with_control(
        gw_white["H1"], gw_white["L1"], gw_wide["H1"].time, gw_rate
    )
    gw_delays = {"H1": 0.0, "L1": gw_corr["lag"]}

    gw_seg = {det: cut_segment(s, 0.75) for det, s in gw_strains.items()}
    gw_time = gw_seg["H1"].time
    gw_whiteners = {
        det: make_whitener(gw_strains[det], gw_seg[det], BAND) for det in gw_strains
    }
    gw_data = {det: gw_whiteners[det](gw_seg[det].strain) for det in gw_strains}
    gw_sigma = noise_sigma(gw_data["H1"], gw_time, (0.3, 0.65))
    gw_fit = fit_chirp(
        gw_time,
        gw_data,
        gw_whiteners,
        gw_delays,
        window=WINDOW,
        sigma=gw_sigma,
        mc_grid=np.arange(22.0, 50.0, 1.0),
    )
    gw_inside = (gw_time >= WINDOW[0]) & (gw_time <= WINDOW[1])
    gw_peak = {
        det: float(np.max(np.abs(gw_fit.models[det][gw_inside]))) for det in gw_strains
    }
    return gw_strains, gw_delays, gw_seg, gw_time, gw_data, gw_fit, gw_peak


def noise_correlation(gw_time, gw_data):
    """The correlation of neighbouring samples of the whitened noise."""
    quiet = (np.abs(gw_time) > 0.3) & (np.abs(gw_time) < 0.65)
    return residual_autocorrelation(gw_data["H1"][quiet])[0]


def injection(experiment: Experiment, gw_strains, gw_delays, gw_peak):
    """A known chirp added to four stretches of strain without an event and
    fitted; record the table."""
    injections = inject_and_fit(
        gw_strains,
        CENTRES,
        truth_mc=TRUTH_MC,
        truth_tc=TRUTH_TC,
        delays=gw_delays,
        peak=gw_peak,
        band=BAND,
        window=WINDOW,
        mc_grid=np.arange(24.0, 48.0, 1.0),
    )
    inj_mc = np.array([inj.mc for inj in injections])
    inj_half = float(np.mean([(inj.high - inj.low) / 2 for inj in injections]))
    inj_rms = float(np.sqrt(np.mean((inj_mc - TRUTH_MC) ** 2)))
    inj_worst = float(np.max(np.abs(inj_mc - TRUTH_MC)))
    inj_covered = sum(inj.covers(TRUTH_MC) for inj in injections)
    experiment.table(
        "injection",
        [
            (
                inj.centre,
                inj.mc,
                inj.low,
                inj.high,
                "yes" if inj.covers(TRUTH_MC) else "no",
            )
            for inj in injections
        ],
        columns=[
            ("noise taken around", "s from the event", ".0f"),
            ("recovered chirp mass", "solar masses", ".1f"),
            ("stated interval, low", "solar masses", ".1f"),
            ("stated interval, high", "solar masses", ".1f"),
            ("holds the truth", "", "s"),
        ],
        caption=f"A chirp of {TRUTH_MC:g} solar masses, of the size of the fitted "
        "signal, added to four stretches of strain without an event.",
    )
    return len(injections), inj_half, inj_rms, inj_worst, inj_covered


def band_spread(gw_strains, gw_delays, gw_seg, gw_time, gw_fit):
    """The chirp mass for three bands of the fit."""
    gw_bands = [(35.0, 350.0), (35.0, 250.0), (30.0, 300.0)]
    gw_band_mc = []
    for band in gw_bands:
        if band == BAND:
            gw_band_mc.append(gw_fit.mc)
            continue
        whiten = {
            det: make_whitener(gw_strains[det], gw_seg[det], band) for det in gw_strains
        }
        gw_series = {det: whiten[det](gw_seg[det].strain) for det in gw_strains}
        other = fit_chirp(
            gw_time,
            gw_series,
            whiten,
            gw_delays,
            window=WINDOW,
            sigma=noise_sigma(gw_series["H1"], gw_time, (0.3, 0.65)),
            mc_grid=np.arange(26.0, 48.0, 2.0),
        )
        gw_band_mc.append(other.mc)
    return min(gw_band_mc), max(gw_band_mc)


def degenerate_masses(experiment: Experiment, gw_fit) -> None:
    """Pairs of masses with the chirp mass of the fit; record the table."""
    mass_rows = []
    for q in (1.0, 0.8, 0.5, 0.25):
        # m1 + m2 from the chirp mass at a given ratio q = m2 / m1.
        total_mass = gw_fit.mc * (1 + q) ** (6 / 5) / q ** (3 / 5)
        heavier = total_mass / (1 + q)
        mass_rows.append(
            (q, heavier, q * heavier, float(chirp.chirp_mass(heavier, q * heavier)))
        )
    experiment.table(
        "degenerate-masses",
        mass_rows,
        columns=[
            ("mass ratio", "", ".2f"),
            ("heavier mass", "solar masses", ".0f"),
            ("lighter mass", "solar masses", ".0f"),
            ("chirp mass", "solar masses", ".1f"),
        ],
        caption="Pairs of masses with the chirp mass of the fit: the leading-order "
        "chirp is the same for all of them.",
    )


def short_record(experiment: Experiment) -> None:
    """Exercise 1: fits of a record shorter than one decay time; record the
    table."""
    t_short = np.linspace(0.0, 0.8, 30)
    short = recover(damped, t_short, TRUTH, sigma=0.2, trials=100, seed=4, names=NAMES)
    rows = [
        (label, rms / value, stated, rms, 100 * cover)
        for label, value, cover, rms, stated in zip(
            short.names,
            short.truth,
            short.coverage,
            short.rms_error,
            short.mean_stderr,
            strict=True,
        )
    ]
    experiment.table(
        "short-record",
        rows,
        columns=[
            ("parameter", "", "s"),
            ("scatter over value", "", ".2f"),
            ("stated error", "", ".3f"),
            ("scatter", "", ".3f"),
            ("coverage", "%", ".0f"),
        ],
        caption="Fits of a record shorter than one decay time: the stated error "
        "against the scatter of 100 trials.",
    )


def two_runs(index, k, m):
    first = np.cos(np.sqrt(k / m) * t)
    second = np.cos(np.sqrt(k / (m + 0.5)) * t)
    return np.where(
        index < t.size,
        first[np.minimum(index, t.size - 1).astype(int)],
        second[np.maximum(index - t.size, 0).astype(int)],
    )


def joint_fit():
    """Exercise 2: k and m from two runs, the second with a known extra
    mass."""
    index = np.arange(2 * t.size, dtype=float)
    rng = np.random.default_rng(8)
    y_two = two_runs(index, K_TRUE, M_TRUE) + rng.normal(0.0, SIGMA, index.size)
    joint = fit_curve(
        two_runs, index, y_two, [4.5, 1.1], sigma=SIGMA, names=["k", "m"], bounds=bound
    )
    print("identifiable:", joint.identifiable)
    print(
        f"k = {joint.value('k'):.2f} +/- {joint.stderr[0]:.2f},"
        f" m = {joint.value('m'):.2f} +/- {joint.stderr[1]:.2f}"
    )


def circuit(R, L, C) -> SeriesRLC:
    """The series circuit with R in ohm, L in mH, and C in µF."""
    return SeriesRLC(R, L * 1e-3, C * 1e-6)


# region: rlc-models
def step_by_rates(t, alpha, omega0):
    """The capacitor voltage (V) after a step of 1 V, underdamped, as a
    function of the decay rate ``alpha`` (1/s) and the natural frequency
    ``omega0`` (rad/s): the two numbers the response depends on."""
    wd = np.sqrt(np.maximum(omega0**2 - alpha**2, 1e-12))
    return 1.0 - np.exp(-alpha * t) * (np.cos(wd * t) + alpha / wd * np.sin(wd * t))


def step_by_elements(t, R, L, C):
    """The same response with the three element values as parameters:
    alpha = R / (2 L) and omega0 = 1 / sqrt(L C)."""
    return step_response(circuit(R, L, C), 1.0, t)


def impedance_parts(x, R, L, C):
    """The real parts and then the imaginary parts (ohm) of the impedance
    Z = R + j (omega L - 1 / (omega C)) at the angular frequencies of the
    first half of ``x`` (rad/s; the second half repeats them)."""
    z = circuit(R, L, C).impedance(x[: len(x) // 2])
    return np.concatenate([z.real, z.imag])


# endregion: rlc-models


def _recovery_rows(domain: str, report: Recovery) -> list[tuple]:
    return [
        (
            domain,
            name,
            truth,
            mean,
            rms / truth * 100,
            stated / truth * 100,
            100 * cover,
        )
        for name, truth, mean, rms, stated, cover in zip(
            report.names,
            report.truth,
            report.mean,
            report.rms_error,
            report.mean_stderr,
            report.coverage,
            strict=True,
        )
    ]


def rlc_in_two_domains(experiment: Experiment) -> tuple[Recovery, Recovery]:
    """The recovery of the step response by its rates and of the impedance
    by its elements, each from 200 noisy copies; record one table."""
    truth = circuit(*RLC_TRUTH)
    in_time = recover(
        step_by_rates,
        step_times,
        (truth.damping_rate, truth.natural_frequency),
        sigma=STEP_SIGMA,
        trials=200,
        seed=12,
        names=("alpha", "omega0"),
    )
    in_frequency = recover(
        impedance_parts,
        np.concatenate([sweep, sweep]),
        RLC_TRUTH,
        sigma=IMPEDANCE_SIGMA,
        trials=200,
        seed=13,
        names=RLC_NAMES,
        bounds=(1e-6, np.inf),
    )
    experiment.table(
        "rlc-recovery",
        _recovery_rows("step response", in_time)
        + _recovery_rows("impedance", in_frequency),
        columns=[
            ("measurement", "", "s"),
            ("parameter", "", "s"),
            ("truth", "", "g"),
            ("mean estimate", "", ".5g"),
            ("scatter of the estimates", "%", ".3f"),
            ("stated standard error", "%", ".3f"),
            ("interval holds the truth", "%", ".0f"),
        ],
        caption="Recovery of the series circuit from 200 noisy copies of each"
        " measurement: the step response by its decay rate (1/s) and natural"
        " frequency (rad/s), the impedance by R (ohm), L (mH), and C (µF). The"
        " scatter and the stated error are relative to the truth.",
    )
    return in_time, in_frequency


def step_with_elements():
    """One noisy step response fitted with R, L, and C as parameters."""
    rng = np.random.default_rng(14)
    y = step_by_elements(step_times, *RLC_TRUTH)
    y = y + STEP_SIGMA * rng.normal(size=step_times.size)
    return fit_curve(
        step_by_elements,
        step_times,
        y,
        [12.0, 8.0, 1.2],
        sigma=STEP_SIGMA,
        names=RLC_NAMES,
        bounds=(1e-6, np.inf),
    )


def impedance_fit(frequencies: np.ndarray, seed: int = 15):
    """One noisy impedance sweep at ``frequencies`` (rad/s), fitted with R,
    L, and C; return the fit and the noisy parts."""
    x = np.concatenate([frequencies, frequencies])
    rng = np.random.default_rng(seed)
    y = impedance_parts(x, *RLC_TRUTH) + IMPEDANCE_SIGMA * rng.normal(size=x.size)
    fit = fit_curve(
        impedance_parts,
        x,
        y,
        [12.0, 8.0, 1.2],
        sigma=IMPEDANCE_SIGMA,
        names=RLC_NAMES,
        bounds=(1e-6, np.inf),
    )
    return fit, y


def rlc_sensitivity(experiment: Experiment, fit) -> None:
    """The correlations of the fitted R, L, and C: how a change of one is
    absorbed by the others."""
    experiment.table(
        "rlc-correlation",
        [(n, *fit.correlation[k]) for k, n in enumerate(fit.names)],
        columns=[("", "", "s"), *((n, "", "+.2f") for n in fit.names)],
        caption="Correlations of the estimates of R, L, and C from one impedance"
        " sweep around the resonance, to two decimals.",
    )


def below_resonance(experiment: Experiment) -> None:
    """Exercise: the sweep only below the resonance; record the relative
    standard errors of both sweeps."""
    around, _ = impedance_fit(sweep)
    below, _ = impedance_fit(low_sweep)
    experiment.table(
        "below-resonance",
        [
            (n, 100 * a / v, 100 * b / w)
            for n, a, v, b, w in zip(
                RLC_NAMES,
                around.stderr,
                around.params,
                below.stderr,
                below.params,
                strict=True,
            )
        ],
        columns=[
            ("parameter", "", "s"),
            ("relative error, around the resonance", "%", ".3f"),
            ("relative error, below it", "%", ".3f"),
        ],
        caption="Stated standard errors of one fit of each sweep, relative to the"
        " estimate, to three decimals.",
    )


def draw_impedance(fit, y) -> Figure:
    """The noisy real and imaginary parts of the impedance with the fitted
    model, and the residuals of both in units of the noise."""
    n = sweep.size
    dense = np.geomspace(sweep[0], sweep[-1], 300)
    model = impedance_parts(np.concatenate([dense, dense]), *fit.params)
    residuals = fit.residuals / IMPEDANCE_SIGMA
    with figure_style():
        fig, (top, bottom) = plt.subplots(
            2, 1, sharex=True, figsize=figsize("pair", legend=4)
        )
        for k, (part, marker) in enumerate(
            (("real part", "o"), ("imaginary part", "s"))
        ):
            top.plot(
                sweep,
                y[k * n : (k + 1) * n],
                linestyle="none",
                marker=marker,
                markerfacecolor="none",
                color=FIGURE_COLOURS[k],
                label=f"{part}, noisy",
            )
            top.plot(
                dense,
                model[k * 300 : (k + 1) * 300],
                color=FIGURE_COLOURS[k],
                linestyle="-" if k == 0 else "--",
                label=f"{part}, fitted model",
            )
            bottom.plot(
                sweep,
                residuals[k * n : (k + 1) * n],
                linestyle="none",
                marker=marker,
                markerfacecolor="none",
                color=FIGURE_COLOURS[k],
            )
        top.set_xscale("log")
        bottom.xaxis.set_minor_formatter(NullFormatter())
        top.set_ylabel("impedance (ohm)")
        bottom.axhspan(-2.0, 2.0, color=FIGURE_COLOURS[4], alpha=0.15)
        bottom.set_ylabel("residual\n(units of the noise)")
        bottom.set_xlabel("angular frequency (rad/s)")
        fig.legend(loc="outside lower center", ncols=1)
    return finish(fig)


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    report = recovery(experiment)
    experiment.number("trials", report.trials)
    experiment.number(
        "largest-bias", np.max(np.abs(report.bias) / np.abs(report.truth)), ".1%"
    )
    experiment.number("least-coverage", 100 * report.coverage.min(), ".0f")

    with experiment.capture("tied-parameters"):
        tied, profile_k = tied_parameters()
    experiment.number("tied-singular-ratio", tied.singular_ratio, ".0e")
    experiment.number("k-low", k_grid[0], "g")
    experiment.number("k-high", k_grid[-1], "g")
    experiment.number("k-rise", np.ptp(profile_k.chi2), ".2f")
    experiment.number("k-rise-1", np.ptp(profile_k.chi2), ".1f")

    y_damped, profile_w = frequency_profile()
    experiment.figure("fig-profiles", partial(draw_profiles, profile_w, profile_k))
    experiment.number("omega-low", profile_w.low, ".3f")
    experiment.number("omega-high", profile_w.high, ".3f")

    with experiment.capture("wrong-model"):
        wrong, right_fit = wrong_model(y_damped)
    experiment.number("wrong-chi2", wrong.reduced_chi2, ".1f")
    experiment.number("right-chi2", right_fit.reduced_chi2, ".1f")
    experiment.figure("fig-residuals", partial(draw_residuals, wrong, right_fit))

    gw_strains, gw_delays, gw_seg, gw_time, gw_data, gw_fit, gw_peak = strain_fit()
    gw_published = PUBLISHED_CHIRP_MASS_SOURCE * (1 + PUBLISHED_REDSHIFT)
    gw_reasons = verdict(gw_fit.fit)
    experiment.number("gw-reasons", "; ".join(gw_reasons) if gw_reasons else "none")
    experiment.number("gw-mc", gw_fit.mc, ".1f")
    experiment.number("gw-mc-low", gw_fit.mc_low, ".1f")
    experiment.number("gw-mc-high", gw_fit.mc_high, ".1f")
    experiment.number("gw-chi2", gw_fit.reduced_chi2, ".2f")
    experiment.number("gw-noise-rho", noise_correlation(gw_time, gw_data), ".2f")

    n_injections, inj_half, inj_rms, inj_worst, inj_covered = injection(
        experiment, gw_strains, gw_delays, gw_peak
    )
    experiment.number("inj-worst", inj_worst, ".1f")
    experiment.number("inj-half", inj_half, ".1f")
    experiment.number("inj-covered", inj_covered)
    experiment.number("injections", n_injections)
    experiment.number("inj-rms", inj_rms, ".1f")

    # region: band-spread
    gw_spread = band_spread(gw_strains, gw_delays, gw_seg, gw_time, gw_fit)
    gw_half = (gw_fit.mc_high - gw_fit.mc_low) / 2
    gw_excess = gw_fit.mc - gw_published
    # endregion: band-spread
    experiment.number("spread-low", gw_spread[0], ".0f")
    experiment.number("spread-high", gw_spread[1], ".0f")
    experiment.number("gw-mc-whole", gw_fit.mc, ".0f")
    experiment.number("gw-half", gw_half, ".1f")
    experiment.number("truth-mc", TRUTH_MC, "g")
    experiment.number("gw-excess", gw_excess, ".0f")
    experiment.number("gw-published", gw_published, ".0f")
    degenerate_masses(experiment, gw_fit)
    experiment.number("gw-singular-ratio", gw_fit.fit.singular_ratio, ".1e")

    in_time, in_frequency = rlc_in_two_domains(experiment)
    experiment.number("rlc-tolerance", 100 * RLC_TOLERANCE, "g")
    experiment.number(
        "rlc-time-recovered",
        "recovered" if in_time.recovered(RLC_TOLERANCE) else "not recovered",
    )
    experiment.number(
        "rlc-frequency-recovered",
        "recovered" if in_frequency.recovered(RLC_TOLERANCE) else "not recovered",
    )
    elements = step_with_elements()
    experiment.number(
        "step-identified",
        ", ".join(
            n for n, ok in zip(RLC_NAMES, elements.identifiable, strict=True) if ok
        )
        or "none",
    )
    experiment.number("step-warning", "; ".join(elements.warnings))
    experiment.number("step-singular-ratio", elements.singular_ratio, ".0e")
    sweep_fit, sweep_parts = impedance_fit(sweep)
    experiment.number("sweep-chi2", sweep_fit.reduced_chi2, ".2f")
    experiment.number(
        "sweep-autocorrelation",
        residual_autocorrelation(sweep_fit.residuals[: sweep.size])[0],
        ".2f",
    )
    rlc_sensitivity(experiment, sweep_fit)
    experiment.figure(
        "fig-rlc-impedance", partial(draw_impedance, sweep_fit, sweep_parts)
    )
    below_resonance(experiment)

    short_record(experiment)
    with experiment.capture("joint-fit"):
        joint_fit()
    return experiment


if __name__ == "__main__":
    main(run)
