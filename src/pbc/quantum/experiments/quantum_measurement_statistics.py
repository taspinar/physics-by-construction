"""The experiment of the lesson "Quantum measurement statistics lab".

The event counts of the Munich event-ready Bell test (the committed sample
of the card ``munich-bell-event-ready``, read by
``pbc.data.reference.munich_bell``): the run, the eight correlators and the
CHSH value of each heralded state with their binomial standard errors,
against the bounds of the entanglement lesson; the model of that lesson
(``pbc.quantum.bell_test``) fitted to the correlators; the balance of the
settings, the no-signalling marginals, and the selections of the run with
their effect on S. Run it as a program to write the figures and the numbers
of the page:

    uv run --locked --no-dev \\
        python -m pbc.quantum.experiments.quantum_measurement_statistics out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.data import SAMPLES_DIR
from pbc.data.plotting import COLOURS, add_credit, label_status
from pbc.data.reference.munich_bell import (
    ANGLES,
    EVENTS_PER_STATE,
    LHV_BOUND,
    PAIRING_WINDOW_MS,
    SETTINGS,
    STATES,
    TSIRELSON,
    Run,
    chsh,
    chsh_pooled,
    combine,
    correlators,
    excluded_pairs,
    load,
    pairing_problems,
    published_selection,
    running_chsh,
    significance,
)
from pbc.experiment import Experiment, main
from pbc.quantum.bell_test import (
    IDEAL,
    events_for_sigmas,
    fit_visibility,
    model_s_of_fit,
    no_signalling,
    predicted_correlator,
    setting_balance,
    setting_pair_counts,
    visibility_threshold,
)

DATASET = "munich-bell-event-ready"
# region: published
# Phys. Rev. Lett. 119, 010402 (2017), the run of 15 April 2016: the
# stopping rule of 5000 events per state, fixed before the run, and the
# values the paper prints for it (Fig. 3 and the text).
PUBLISHED_S = {"Psi-": (2.240, 0.047), "Psi+": (2.204, 0.047), "pooled": (2.221, 0.033)}
# endregion: published
CREDIT = (
    "Data: Rosenfeld, Burchardt, Garthoff, Redeker, Ortegel, Rau, Weinfurter "
    "(LMU Munich), Zenodo 10.5281/zenodo.22936124, CC BY 4.0; "
    "Bell_2016-04-15.zip, unmodified. Selection, errors and S: this lesson's code."
)
MARKER = {"Psi-": "o", "Psi+": "s"}
LINE = {"Psi-": "-", "Psi+": "--"}
SIGMAS_WANTED = 5.0  # exercise 2: the significance asked for


def load_run() -> Run:
    """The three files of the committed sample, checked against each other:
    every pair agrees with the two lab rows it names."""
    run = load(SAMPLES_DIR / DATASET)
    assert pairing_problems(run) == []
    return run


def the_run(experiment: Experiment, run: Run):
    """The coverage, the events, the pauses and the exclusions of the run;
    record the table and return the selection of the stopping rule."""
    pairs = run.pairs
    days = (pairs.time_ms - pairs.time_ms[0]) / 86400e3
    gaps = np.diff(pairs.time_ms) / 1e3
    pauses = gaps[gaps > 3600]
    published = published_selection(pairs)
    stop_day = float(days[published].max())
    rows = []
    for state in STATES:
        k = pairs.state == state
        rows.append(
            (
                state,
                int(k.sum()),
                int((k & published).sum()),
                int(k.sum()) - EVENTS_PER_STATE,
            )
        )
    experiment.table(
        "the-run",
        rows,
        columns=[
            ("heralded state", "", "s"),
            ("valid events in the archive", "", "d"),
            ("events of the stopping rule", "", "d"),
            ("events after the stopping rule", "", "d"),
        ],
        caption="The valid atom-atom events of the run, per heralded state, and "
        "the first 5000 of each that the stopping rule fixed before the run "
        "selects.",
    )
    return published, days, float(days[-1]), gaps, pauses, stop_day


def draw_run(run: Run, days, published, stop_day) -> Figure:
    """The events of each state accumulated over the run."""
    pairs = run.pairs
    fig, ax = plt.subplots(figsize=(7.2, 4.0), constrained_layout=True)
    for k, state in enumerate(STATES):
        sel = pairs.state == state
        ax.step(
            days[sel],
            np.arange(1, sel.sum() + 1),
            where="post",
            color=COLOURS[k],
            ls=LINE[state],
            lw=1.3,
            label=f"{state}: valid events, accumulated",
        )
    start = pairs.time_ms[0]
    excluded_days = (run.lab_1.time_ms[run.lab_1.excluded] - start) / 86400e3
    ax.plot(
        excluded_days,
        np.full(excluded_days.size, -120.0),
        marker="|",
        ms=9,
        ls="none",
        color=COLOURS[2],
        label="attempt of lab 1 excluded (maintenance)",
    )
    ax.axhline(
        EVENTS_PER_STATE,
        color="0.4",
        lw=0.8,
        ls="-.",
        label="stopping rule: 5000 per state",
    )
    ax.axvline(
        stop_day, color="0.4", lw=0.8, ls=":", label="the moment the rule is met"
    )
    ax.set_xlabel("time since the first event [day]")
    ax.set_ylabel("events of the state [count]")
    ax.set_title("Processed: the valid events of the run, by heralded state")
    ax.legend(fontsize=8, loc="upper left")
    label_status(fig, "processed")
    add_credit(fig, CREDIT)
    return fig


def counts_and_correlators(experiment: Experiment, run: Run, published):
    """The eight correlators of the stopping rule with their binomial
    standard errors; record the table."""
    pairs = run.pairs
    rows, terms = [], {}
    for state in STATES:
        terms[state] = correlators(pairs, state, published)
        for (a, b), c in terms[state].items():
            equal = round(c.n * (1 + c.value) / 2)
            rows.append(
                (
                    state,
                    f"({ANGLES[2 * a + b][0]}, {ANGLES[2 * a + b][1]:+d})",
                    c.n,
                    equal,
                    c.n - equal,
                    c.value,
                    c.stderr,
                )
            )
    experiment.table(
        "counts",
        rows,
        columns=[
            ("heralded state", "", "s"),
            ("settings (alpha, beta)", "degree", "s"),
            ("events", "", "d"),
            ("equal outcomes", "", "d"),
            ("unequal outcomes", "", "d"),
            ("correlator E", "", "+.3f"),
            ("standard error", "", ".3f"),
        ],
        caption="The events of the stopping rule at each pair of settings, how "
        "many gave equal and unequal outcomes, and the correlator with its "
        "binomial standard error.",
    )
    return terms


def chsh_values(experiment: Experiment, run: Run, published):
    """S of each state and pooled, with the stopping rule, with the whole
    archive, and with the excluded attempts added back; record the table."""
    pairs = run.pairs
    rows, found = [], {}
    for state in STATES:
        s, err = chsh(pairs, state, published)
        found[state] = (s, err)
        rows.append(
            (f"{state}, stopping rule", EVENTS_PER_STATE, s, err, significance(s, err))
        )
    s, err = chsh_pooled(pairs, published)
    found["pooled"] = (s, err)
    rows.append(
        (
            "both states, stopping rule",
            int(published.sum()),
            s,
            err,
            significance(s, err),
        )
    )
    s_all, err_all = chsh_pooled(pairs)
    found["archive"] = (s_all, err_all)
    rows.append(
        (
            "both states, whole archive",
            len(pairs),
            s_all,
            err_all,
            significance(s_all, err_all),
        )
    )
    excluded = excluded_pairs(run)
    with_excluded = combine(pairs, excluded)
    s_ex, err_ex = chsh_pooled(with_excluded)
    found["with-excluded"] = (s_ex, err_ex)
    rows.append(
        (
            "both states, archive with the excluded attempts",
            len(with_excluded),
            s_ex,
            err_ex,
            significance(s_ex, err_ex),
        )
    )
    experiment.table(
        "chsh",
        rows,
        columns=[
            ("selection", "", "s"),
            ("events", "", "d"),
            ("S", "", ".4f"),
            ("standard error", "", ".4f"),
            ("(S - 2) / error", "", ".1f"),
        ],
        caption="The CHSH value S with its standard error (the quadrature sum of "
        "the four correlators' errors) for each selection of events, and its "
        "distance above the local bound 2 in standard errors, which assumes "
        "independent events.",
    )
    return found, len(excluded)


def draw_correlators(terms, fits) -> Figure:
    """The eight correlators with their errors, the ideal values, and the
    fitted two-parameter model apart."""
    fig, ax = plt.subplots(figsize=(7.2, 4.2), constrained_layout=True)
    positions = np.arange(4)
    for k, state in enumerate(STATES):
        shift = (k - 0.5) * 0.22
        ax.errorbar(
            positions + shift,
            [terms[state][s].value for s in SETTINGS],
            yerr=[terms[state][s].stderr for s in SETTINGS],
            color=COLOURS[k],
            marker=MARKER[state],
            ls="none",
            capsize=3,
            label=f"{state}: measured correlator, one standard error",
        )
        fit = fits[state]
        v, eps = fit.value("visibility"), fit.value("offset")
        ax.plot(
            positions + shift,
            [predicted_correlator(state, *s, v, eps) for s in SETTINGS],
            color=COLOURS[k],
            marker=MARKER[state],
            markerfacecolor="none",
            markersize=11,
            ls="none",
            label=f"{state}: fitted model (visibility and offset)",
        )
    for v in (IDEAL, -IDEAL):
        ax.axhline(
            v,
            color="0.5",
            lw=0.9,
            ls=":",
            label="ideal state: +-1/sqrt(2)" if v > 0 else None,
        )
    ax.axhline(0, color="0.7", lw=0.6)
    ax.set_xticks(positions, [f"({a}, {b:+d})" for a, b in ANGLES.values()])
    ax.set_ylim(-1, 1)
    ax.set_xlabel("settings (alpha, beta) of lab 1 and lab 2 [degree]")
    ax.set_ylabel("correlator E [dimensionless]")
    ax.set_title(
        "Processed: correlators of the stopping rule, with the fitted model apart"
    )
    ax.legend(fontsize=7.5, loc="center", ncol=2)
    label_status(fig, "processed")
    add_credit(fig, CREDIT)
    return fig


def draw_running_s(run: Run, found) -> Figure:
    """S of each state after each event, with its band and the bounds."""
    pairs = run.pairs
    fig, ax = plt.subplots(figsize=(7.2, 4.4), constrained_layout=True)
    for k, state in enumerate(STATES):
        s, err = running_chsh(pairs, state)
        n = np.arange(40, 40 + s.size)
        ax.plot(
            n,
            s,
            color=COLOURS[k],
            ls=LINE[state],
            lw=1.2,
            label=f"{state}: S after n events",
        )
        ax.fill_between(
            n,
            s - err,
            s + err,
            color=COLOURS[k],
            alpha=0.2,
            lw=0,
            label=f"{state}: one standard error",
        )
    ax.axhline(LHV_BOUND, color="0.2", lw=1.0, label="local bound S = 2")
    ax.axhline(
        TSIRELSON, color="0.5", lw=0.9, ls=":", label="Tsirelson's bound 2 sqrt(2)"
    )
    ax.axvline(
        EVENTS_PER_STATE,
        color="0.4",
        lw=0.8,
        ls="-.",
        label="stopping rule: 5000 events per state",
    )
    ax.set_ylim(1.0, 3.3)
    ax.set_xlabel("events of the state, in time order [count]")
    ax.set_ylabel("S after n events [dimensionless]")
    pooled, pooled_err = found["pooled"]
    ax.set_title(
        f"Processed: running S; both states at the stop S = {pooled:.3f}"
        f" +- {pooled_err:.3f}"
    )
    ax.legend(fontsize=8, loc="lower right", ncol=2)
    label_status(fig, "processed")
    add_credit(fig, CREDIT)
    return fig


def warns(fit) -> str:
    """What the fit helper warns about, in a word: the reduced chi-square,
    the identifiability of the parameters, or nothing."""
    if not fit.warnings:
        return "nothing"
    return "; ".join(
        "the chi-square" if "chi-square" in w else "the parameters"
        for w in fit.warnings
    )


def fit_the_model(experiment: Experiment, terms):
    """The model of the entanglement lesson fitted to the four correlators
    of each state: the visibility alone, then with the offset of lab 2's
    basis; record both tables and return the fits."""
    one_rows, two_rows, fits = [], {}, {}
    for state in STATES:
        one = fit_visibility(terms[state], state, with_offset=False)
        s_one, _ = model_s_of_fit(one)
        assert one.dof == 3
        one_rows.append(
            (
                state,
                one.value("visibility"),
                one.stderr[0],
                s_one,
                one.reduced_chi2,
                warns(one),
            )
        )
        two = fit_visibility(terms[state], state, with_offset=True)
        fits[state] = two
        assert two.dof == 2
        s_two, s_two_err = model_s_of_fit(two)
        two_rows[state] = (
            state,
            two.value("visibility"),
            two.stderr[0],
            np.degrees(two.value("offset")),
            np.degrees(two.stderr[1]),
            s_two,
            s_two_err,
            two.reduced_chi2,
            warns(two),
        )
    experiment.table(
        "fit-one",
        one_rows,
        columns=[
            ("heralded state", "", "s"),
            ("visibility V", "", ".3f"),
            ("its error", "", ".3f"),
            ("S of the model", "", ".3f"),
            ("reduced chi-square", "", ".2f"),
            ("the helper warns", "", "s"),
        ],
        caption="The one-parameter model of the entanglement lesson, the state "
        "mixed with white noise at the visibility V, fitted to the four "
        "correlators of each heralded state by weighted least squares: three "
        "degrees of freedom.",
    )
    experiment.table(
        "fit-two",
        list(two_rows.values()),
        columns=[
            ("heralded state", "", "s"),
            ("visibility V", "", ".3f"),
            ("its error", "", ".3f"),
            ("offset, lab 2", "degree", "+.1f"),
            ("its error", "degree", ".1f"),
            ("S of the model", "", ".3f"),
            ("its error", "", ".3f"),
            ("reduced chi-square", "", ".2f"),
            ("the helper warns", "", "s"),
        ],
        caption="The model with a second parameter, an offset of the analysis "
        "basis of lab 2, fitted to the same four correlators of each state: "
        "two degrees of freedom. S of the model is 2 sqrt(2) V cos(offset).",
    )
    return fits


def settings_checks(experiment: Experiment, run: Run, published):
    """The balance of the random settings; record the table."""
    pairs = run.pairs
    rows, worst = [], 0.0
    for state in STATES:
        k = (pairs.state == state) & published
        for lab, bits in ((1, pairs.a), (2, pairs.b)):
            balance = setting_balance(bits[k])
            worst = max(worst, abs(balance.sigmas))
            rows.append(
                (
                    state,
                    lab,
                    balance.n,
                    balance.fraction,
                    balance.stderr,
                    balance.sigmas,
                )
            )
    experiment.table(
        "settings",
        rows,
        columns=[
            ("heralded state", "", "s"),
            ("lab", "", "d"),
            ("events", "", "d"),
            ("fraction of setting 1", "", ".4f"),
            ("error of a fair coin", "", ".4f"),
            ("distance from one half, in errors", "", "+.1f"),
        ],
        caption="How often each lab's random setting was 1 among the events of "
        "the stopping rule, against a fair coin.",
    )
    chi2 = {
        state: setting_pair_counts(pairs, (pairs.state == state) & published)[1]
        for state in STATES
    }
    return worst, chi2


def no_signalling_checks(experiment: Experiment, run: Run, published):
    """The marginal of each lab at each of its settings, once for each
    setting of the other lab; record the table and return the largest
    difference in standard errors."""
    rows, worst = [], 0.0
    for state in STATES:
        k = (run.pairs.state == state) & published
        for m in no_signalling(run.pairs, k):
            worst = max(worst, abs(m.sigmas))
            rows.append(
                (
                    state,
                    m.lab,
                    m.own_setting,
                    m.fraction[0],
                    m.fraction[1],
                    m.difference,
                    m.stderr,
                    m.sigmas,
                )
            )
    experiment.table(
        "no-signalling",
        rows,
        columns=[
            ("heralded state", "", "s"),
            ("lab", "", "d"),
            ("its setting", "", "d"),
            ("fraction of outcome 1, other lab at 0", "", ".4f"),
            ("other lab at 1", "", ".4f"),
            ("difference", "", "+.4f"),
            ("standard error", "", ".4f"),
            ("difference in errors", "", "+.1f"),
        ],
        caption="No-signalling: the fraction of a lab's outcomes that are 1 at "
        "one of its own settings, with the other lab at each of its settings, "
        "among the events of the stopping rule.",
    )
    return worst


def psi_plus_returns(run: Run):
    """Exercise 3: the events at which the running S of Psi+ is below 2,
    and the last one at which its band still touches 2."""
    s, err = running_chsh(run.pairs, "Psi+")
    n = np.arange(40, 40 + s.size)
    below = n[s < LHV_BOUND]
    band_touches = int(n[s - err < LHV_BOUND].max())
    return [int(v) for v in below], band_touches


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    run_ = load_run()
    pairs = run_.pairs
    published, days, span_days, gaps, pauses, stop_day = the_run(experiment, run_)
    experiment.number("events", len(pairs), "d")
    experiment.number("attempts-1", run_.lab_1.time_ms.size, "d")
    experiment.number("attempts-2", run_.lab_2.time_ms.size, "d")
    experiment.number("excluded-1", int(run_.lab_1.excluded.sum()), "d")
    experiment.number("excluded-2", int(run_.lab_2.excluded.sum()), "d")
    experiment.number("span-days", span_days, ".2f")
    experiment.number("median-gap", float(np.median(gaps)), ".1f")
    experiment.number("pauses", pauses.size, "d")
    experiment.number("pause-hours-low", pauses.min() / 3600, ".1f")
    experiment.number("pause-hours-high", pauses.max() / 3600, ".1f")
    experiment.number("stop-day", stop_day, ".2f")
    experiment.number("pairing-window", PAIRING_WINDOW_MS, "d")
    experiment.number("per-state", EVENTS_PER_STATE, "d")
    experiment.figure("fig-run", partial(draw_run, run_, days, published, stop_day))

    terms = counts_and_correlators(experiment, run_, published)
    experiment.number("ideal", IDEAL, ".3f")
    experiment.number("tsirelson", TSIRELSON, ".3f")
    found, n_excluded_pairs = chsh_values(experiment, run_, published)
    for key, name in (("Psi-", "minus"), ("Psi+", "plus"), ("pooled", "pooled")):
        s, err = found[key]
        experiment.number(f"s-{name}", s, ".3f")
        experiment.number(f"e-{name}", err, ".3f")
        experiment.number(f"sigmas-{name}", significance(s, err), ".1f")
        published_s, published_e = PUBLISHED_S[key]
        assert abs(s - published_s) < 5e-4 and abs(err - published_e) < 5e-4
        experiment.number(f"published-{name}", published_s, ".3f")
        experiment.number(f"published-e-{name}", published_e, ".3f")
    s_all, err_all = found["archive"]
    s_ex, _ = found["with-excluded"]
    experiment.number("s-archive", s_all, ".4f")
    experiment.number("e-archive", err_all, ".4f")
    experiment.number("s-with-excluded", s_ex, ".4f")
    experiment.number("excluded-pairs", n_excluded_pairs, "d")
    experiment.number("shift-in-errors", abs(s_ex - s_all) / err_all, ".2f")
    experiment.number("after-stop", len(pairs) - 2 * EVENTS_PER_STATE, "d")
    experiment.figure("fig-running-s", partial(draw_running_s, run_, found))

    fits = fit_the_model(experiment, terms)
    experiment.number("threshold", visibility_threshold(), ".3f")
    offsets = {state: np.degrees(fits[state].value("offset")) for state in STATES}
    offset_errors = {state: np.degrees(fits[state].stderr[1]) for state in STATES}
    for state, name in (("Psi-", "minus"), ("Psi+", "plus")):
        experiment.number(f"v-{name}", fits[state].value("visibility"), ".3f")
        experiment.number(f"v-e-{name}", fits[state].stderr[0], ".3f")
        experiment.number(f"offset-{name}", offsets[state], "+.1f")
        experiment.number(f"offset-e-{name}", offset_errors[state], ".1f")
        s_model, s_model_err = model_s_of_fit(fits[state])
        experiment.number(f"s-model-{name}", s_model, ".3f")
        experiment.number(f"s-model-e-{name}", s_model_err, ".3f")
        experiment.number(f"chi2-two-{name}", fits[state].reduced_chi2, ".2f")
    one_chi2 = [row[4] for row in experiment.tables["fit-one"].rows]
    experiment.number("chi2-one-low", min(one_chi2), ".1f")
    experiment.number("chi2-one-high", max(one_chi2), ".1f")
    experiment.number(
        "offset-difference", abs(offsets["Psi-"] - offsets["Psi+"]), ".1f"
    )
    experiment.number(
        "offset-difference-e",
        np.sqrt(offset_errors["Psi-"] ** 2 + offset_errors["Psi+"] ** 2),
        ".1f",
    )
    experiment.figure("fig-correlators", partial(draw_correlators, terms, fits))

    worst_balance, chi2_settings = settings_checks(experiment, run_, published)
    experiment.number("worst-balance", worst_balance, ".1f")
    experiment.number("chi2-settings-low", min(chi2_settings.values()), ".1f")
    experiment.number("chi2-settings-high", max(chi2_settings.values()), ".1f")
    worst_signal = no_signalling_checks(experiment, run_, published)
    experiment.number("worst-signal", worst_signal, ".1f")

    # Exercises.
    v_min = {
        state: visibility_threshold(fits[state].value("offset")) for state in STATES
    }
    experiment.number("v-min-minus", v_min["Psi-"], ".3f")
    experiment.number("v-min-plus", v_min["Psi+"], ".3f")
    experiment.number(
        "v-margin-minus",
        (fits["Psi-"].value("visibility") - v_min["Psi-"]) / fits["Psi-"].stderr[0],
        ".1f",
    )
    s_pooled, e_pooled = found["pooled"]
    experiment.number("sigmas-wanted", SIGMAS_WANTED, ".0f")
    experiment.number(
        "events-for-five",
        events_for_sigmas(s_pooled, e_pooled, int(published.sum()), SIGMAS_WANTED),
        "d",
    )
    experiment.number(
        "events-for-five-per-state",
        events_for_sigmas(
            found["Psi+"][0], found["Psi+"][1], EVENTS_PER_STATE, SIGMAS_WANTED
        ),
        "d",
    )
    below, band_touches = psi_plus_returns(run_)
    experiment.number("plus-below", ", ".join(str(v) for v in below))
    experiment.number("plus-band-clears", band_touches + 1, "d")
    return experiment


if __name__ == "__main__":
    main(run)
