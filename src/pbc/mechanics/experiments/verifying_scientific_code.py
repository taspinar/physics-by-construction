"""The experiment of the lesson "Verifying scientific code".

The checks of ``pbc.verification`` on the correct steppers and on the
gallery of faulty ones: their verdicts, the findings for velocity Verlet,
the convergence of the oscillator error, and the report of a claim. Run it
as a program to write the figure and the printed results of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.verifying_scientific_code out
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.figure_language import (
    LINE,
    MARKER,
    MUTED,
    direct_label,
    figsize,
    figure_style,
    finish,
    reference_slope,
)
from pbc.mechanics.dynamics import State
from pbc.mechanics.integrators import rk4_step, verlet_step
from pbc.mechanics.resonance import (
    damping_rate,
    driven_motion,
    measured_resonance_curve,
    simulate_driven,
    steady_state_amplitude,
)
from pbc.verification import (
    CHECKS,
    Claim,
    convergence_table,
    driven,
    fitted_order,
    oscillator_error,
    verify,
)
from pbc.verification.driven import MODEL_CHECKS, ModelClaim, verify_simulation
from pbc.verification.faulty import (
    CORRECT,
    GALLERY,
    rk4_with_equal_weights,
    verlet_that_remembers_the_acceleration,
    verlet_with_a_stopped_clock,
    verlet_without_the_half,
)
from pbc.verification.faulty_driven import GALLERY as FAULTY_SIMULATIONS
from pbc.verification.faulty_driven import (
    drive_frozen_within_the_step,
    drive_not_divided_by_mass,
    frequency_in_hertz,
)

# region: counts
counts = np.array([50, 100, 200, 400, 800])
steps = np.pi / counts
# endregion: counts


def list_checks():
    print(", ".join(CHECKS))


def verdicts(build, claim):
    findings = {f.check: f for f in verify(build, claim)}
    return findings, {
        check: "-"
        if check not in findings
        else "pass"
        if findings[check].passed
        else "FAIL"
        for check in CHECKS
    }


def print_matrix(rows):
    print(f"{'':38}" + "".join(f"{check:>19}" for check in CHECKS))
    for name, marks in rows:
        print(f"{name:38}" + "".join(f"{marks[check]:>19}" for check in CHECKS))


def correct_steppers():
    """The verdicts of every check on the correct steppers."""
    correct = {name: verdicts(build, claim) for name, build, claim in CORRECT}
    print_matrix([(name, marks) for name, (_, marks) in correct.items()])
    return correct


def verlet_findings(correct):
    """What each check measured for velocity Verlet."""
    for finding in correct["velocity Verlet"][0].values():
        print(
            f"{finding.check:18} measured {finding.measured:9.3g}"
            f"  tolerance {finding.tolerance:7.2g}  {finding.detail}"
        )
        print(f"{'':18} claim: {finding.claim}")
        print(f"{'':18} reproduce: {finding.reproduction}")


def verlet_convergence():
    """The error of velocity Verlet on the oscillator for each step, with
    the observed order."""
    errors = [oscillator_error(lambda: verlet_step, n) for n in counts]
    print(" steps per period   step (s)     error (m)   observed order")
    for n, (h, e, p) in zip(counts, convergence_table(steps, errors), strict=True):
        print(f"{n:17d}{h:11.5f}{e:14.3e}{'' if p is None else f'{p:15.2f}'}")


def draw_verification_convergence() -> Figure:
    """The error against the step for two correct and two faulty steppers."""
    series = {
        "velocity Verlet": (verlet_step, FIGURE_COLOURS[0], "-"),
        "Runge-Kutta 4": (rk4_step, "#00734f", "-"),
        "verlet without the half": (verlet_without_the_half, FIGURE_COLOURS[1], "--"),
        "rk4 with equal weights": (rk4_with_equal_weights, "#b34700", "-."),
    }
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line", legend=4))
        for name, (step, color, style) in series.items():
            errors = [oscillator_error(lambda: step, n) for n in counts]  # noqa: B023
            ax.loglog(
                steps,
                errors,
                color=color,
                linestyle=style,
                marker="o",
                markersize=3,
                label=name,
            )
        # The steps as the ticks: the minor labels of the log axis ran into
        # each other at this width.
        ax.set_xticks(steps, labels=[f"{value:.2g}" for value in steps])
        ax.minorticks_off()
        ax.set_xlabel("time step (s)")
        ax.set_ylabel("largest error over\ntwo periods (m)")
        # Four entries: under the plot, in one column.
        fig.legend(loc="outside lower center", ncols=1)
    return finish(fig)


def gallery():
    """The verdicts of every check on the gallery of faulty steppers."""
    caught = {g.name: verdicts(g.build, g.claim) for g in GALLERY}
    print_matrix([(name, marks) for name, (_, marks) in caught.items()])
    print()
    for g in GALLERY:
        named = ", ".join(g.caught_by)
        print(f"{g.name}: {g.fault}\n    poses as {g.poses_as}; caught by {named}")


def claimed_orders():
    """The convergence check of velocity Verlet against three claimed
    orders."""
    for order in (1, 2, 4):
        findings = verify(lambda: verlet_step, Claim(order=order, bounded_energy=True))
        result = next(f for f in findings if f.check == "convergence-order")
        print(
            f"claimed order {order}: {'pass' if result.passed else 'FAIL'}"
            f"  ({result.detail})"
        )


def report(name, build, claim):
    findings = verify(build, claim)
    failed = [f.check for f in findings if not f.passed]
    bound = "claimed" if claim.bounded_energy else "not claimed"
    print(f"subject: {name}; claim: order {claim.order}, energy bound {bound}")
    for f in findings:
        print(f"  {'pass' if f.passed else 'FAIL'}  {f.check:18} {f.detail}")
        print(f"{'':26}claim: {f.claim}")
        print(f"{'':26}reproduce: {f.reproduction}")
    print(
        "verdict: "
        + (
            "claim not supported by " + ", ".join(failed)
            if failed
            else "claim supported"
        )
    )
    print("covered: the oscillator at 50 to 800 steps per period")
    print("not covered: nonlinear forces, velocity-dependent forces, the Kepler orbit")


def report_on_equal_weights():
    """Exercise 1: the report on Runge-Kutta 4 with equal weights."""
    rk4_equal_weights = next(g for g in GALLERY if g.name == "rk4 with equal weights")
    report(rk4_equal_weights.name, rk4_equal_weights.build, rk4_equal_weights.claim)


def margins():
    """Exercise 2: the fitted order of two steppers against two margins."""
    for name, step in (
        ("velocity Verlet", verlet_step),
        ("verlet without the half", verlet_without_the_half),
    ):
        errors = [oscillator_error(lambda: step, n) for n in counts]  # noqa: B023
        order = fitted_order(np.pi / counts, errors)
        marks = {m: "pass" if abs(order - 2) <= m else "FAIL" for m in (0.4, 1.5)}
        print(
            f"{name:26} fitted order {order:.2f}; margin 0.4: {marks[0.4]},"
            f" margin 1.5: {marks[1.5]}"
        )


def verlet_with_one_acceleration(state, acceleration, dt):
    a = acceleration(state.t, state.x, state.v)
    return State(
        t=state.t + dt,
        x=state.x + state.v * dt + 0.5 * a * dt**2,
        v=state.v + a * dt,
    )


def one_acceleration():
    """Exercise 3: the checks on a Verlet step that evaluates the
    acceleration once."""
    findings = verify(
        lambda: verlet_with_one_acceleration, Claim(order=2, bounded_energy=True)
    )
    for f in findings:
        print(f"{'pass' if f.passed else 'FAIL'}  {f.check:18} {f.detail}")


# --- From a model to tested code: the damped driven oscillator (SA2). ---

# region: model-claim
REFERENCE_CLAIM = ModelClaim(order=4)  # the classical Runge-Kutta method
VERLET_ON_THE_MODEL = ModelClaim(order=2)
# endregion: model-claim

VERDICT_COLUMNS = [("subject", "", ""), *((check, "", "") for check in MODEL_CHECKS)]


def marks(simulate, claim):
    """The verdict of every check of the model on ``simulate``, in the order
    of the contract."""
    return tuple(
        "pass" if finding.passed else "FAIL"
        for finding in verify_simulation(simulate, claim)
    )


def reference_findings(experiment: Experiment) -> None:
    """The evidence of each check of the model on the reference solution;
    record the table."""
    findings = verify_simulation(simulate_driven, REFERENCE_CLAIM)
    experiment.table(
        "driven-findings",
        [
            ("pass" if f.passed else "FAIL", f.check, f.claim, f.detail)
            for f in findings
        ],
        [
            ("verdict", "", ""),
            ("check", "", ""),
            ("claim", "", ""),
            ("evidence", "", ""),
        ],
        "The four checks of the model on the reference solution, claimed to be"
        " of order four: the verdict, the claim each check tests, and what was"
        " measured against which tolerance.",
    )


def steppers_on_the_model(experiment: Experiment) -> None:
    """Velocity Verlet and two faulty steppers of the gallery inside the
    simulation of the driven oscillator, under the claim of order two;
    record the table."""

    def inside(build):
        return lambda *arguments: simulate_driven(*arguments, step=build())

    subjects = (
        ("velocity Verlet", lambda: verlet_step),
        ("verlet with a stopped clock", lambda: verlet_with_a_stopped_clock),
        ("verlet that remembers", verlet_that_remembers_the_acceleration),
    )
    experiment.table(
        "steppers-on-the-model",
        [
            (name, *marks(inside(build), VERLET_ON_THE_MODEL))
            for name, build in subjects
        ],
        VERDICT_COLUMNS,
        "The checks of the driven oscillator on a simulation that steps with"
        " velocity Verlet and with two faulty steppers of the gallery, each"
        " claimed to be of order two.",
    )


def faulty_simulations(experiment: Experiment) -> None:
    """The checks of the model on the reference solution and on the four
    faulty simulations; record the table."""
    rows = [("reference solution", *marks(simulate_driven, REFERENCE_CLAIM), "")]
    rows += [
        (entry.name, *marks(entry.simulate, REFERENCE_CLAIM), entry.fault)
        for entry in FAULTY_SIMULATIONS
    ]
    experiment.table(
        "faulty-simulations",
        rows,
        [*VERDICT_COLUMNS, ("the fault", "", "")],
        "The checks of the model on the reference solution and on four"
        " simulations with one fault each, all claimed to be of order four.",
    )


def at_unit_mass(experiment: Experiment) -> None:
    """The simulation that does not divide the drive by the mass: the
    convergence check at a mass of 1 kg and at the mass of the checks, and
    the change of each unit; record the table."""
    rows = []
    for mass in (1.0, driven.MASS):
        finding = driven.check_convergence_order(
            drive_not_divided_by_mass, REFERENCE_CLAIM, mass=mass
        )
        rows.append(
            (
                f"convergence-order at a mass of {mass:g} kg",
                "pass" if finding.passed else "FAIL",
                f"fitted order {round(finding.measured, 2) + 0.0:.2f}",
            )
        )
    for name, factors in driven.UNITS.items():
        change = driven.rescaled(drive_not_divided_by_mass, *factors)
        rows.append(
            (
                f"units: the unit of {name} changed",
                "pass" if change <= driven.RESCALED else "FAIL",
                "the motion is the same"
                if change <= driven.RESCALED
                else "the motion changes",
            )
        )
    experiment.table(
        "unit-mass",
        rows,
        [("check", "", ""), ("verdict", "", ""), ("what was found", "", "")],
        "The simulation whose drive is not divided by the mass, under the"
        " convergence check at two masses and under the change of each unit.",
    )


def model_report(name, simulate, claim):
    """The report of a verification of a simulation of the driven
    oscillator, in the form of the contract."""
    findings = verify_simulation(simulate, claim)
    failed = [f.check for f in findings if not f.passed]
    print(f"subject: {name}; claim: order {claim.order}")
    for f in findings:
        print(f"  {'pass' if f.passed else 'FAIL'}  {f.check:18} {f.detail}")
        print(f"{'':26}claim: {f.claim}")
        print(f"{'':26}reproduce: {f.reproduction}")
    print(
        "verdict: "
        + (
            "claim not supported by " + ", ".join(failed)
            if failed
            else "claim supported"
        )
    )
    print(
        "covered: one underdamped oscillator, driven below its natural"
        f" frequency, at {driven.COUNTS[0]} to {driven.COUNTS[-1]} steps per period"
    )
    print(
        "not covered: overdamped motion, driving at or above resonance,"
        " the refusal of invalid inputs, stiff parameters"
    )


def report_on_a_submission():
    """The report on a submission that reads the driving frequency as
    cycles per second."""
    model_report("a submitted simulate_driven", frequency_in_hertz, REFERENCE_CLAIM)


def draw_driven_convergence() -> Figure:
    """The error against the exact driven motion for the reference
    solution, for the same simulation stepped with velocity Verlet, and for
    the simulation that freezes the drive within a step."""
    series = (
        ("reference solution", simulate_driven, FIGURE_COLOURS[0], "-", "o"),
        (
            "velocity Verlet",
            lambda *arguments: simulate_driven(*arguments, step=verlet_step),
            FIGURE_COLOURS[4],
            "-.",
            "^",
        ),
        ("drive frozen", drive_frozen_within_the_step, FIGURE_COLOURS[1], "--", "s"),
    )
    step_counts = np.array(driven.COUNTS)
    h = driven.PERIOD / step_counts
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line"))
        for name, simulate, colour, style, marker in series:
            errors = [driven.driven_error(simulate, n) for n in step_counts]
            ax.loglog(
                h,
                errors,
                color=colour,
                linestyle=style,
                marker=marker,
                markersize=MARKER,
                linewidth=LINE["data"],
            )
            direct_label(
                ax, h[-1], errors[-1], name, colour, offset=(4.0, -9.0), va="top"
            )
            if name == "reference solution":
                reference_slope(ax, h, errors[0], 4, below=0.2)
            if name == "drive frozen":
                reference_slope(ax, h, errors[0], 1, below=3.0)
        ax.set_xticks(h, labels=[f"{value:.2g}" for value in h])
        ax.minorticks_off()
        ax.set_xlabel("time step (s)")
        ax.set_ylabel("largest error over\ntwo periods (m)")
    return finish(fig)


def draw_driven_limits() -> Figure:
    """Two limits of the reference solution: the free decay inside the
    envelope of the closed form, and the steady amplitude against the
    driving frequency on the amplitude formula, with the static deflection."""
    mass, k, b, force = driven.MASS, driven.K, driven.B, driven.FORCE
    n = 4 * 100
    dt = driven.PERIOD / 100
    free = simulate_driven(driven.START, mass, k, b, 0.0, driven.DRIVE, dt, n)
    exact = driven_motion(driven.START, mass, k, b, 0.0, driven.DRIVE, free.t)
    # The envelope of the free decay: its largest excursion at the start,
    # falling as exp(-gamma t).
    gamma = damping_rate(mass, b)
    excursion = np.max(np.abs(exact.x[:, 0]) * np.exp(gamma * exact.t))
    envelope = excursion * np.exp(-gamma * free.t)
    omegas = np.array([0.25, 0.75, 1.25, 1.75, 2.25, 3.0, 4.0])
    measured, _ = measured_resonance_curve(mass, k, b, force, omegas)
    curve = np.linspace(0.0, 4.2, 200)
    with figure_style():
        fig, (top, bottom) = plt.subplots(2, 1, figsize=figsize("pair"))
        top.plot(free.t, free.x[:, 0], color=FIGURE_COLOURS[0], linewidth=LINE["data"])
        for sign in (1.0, -1.0):
            top.plot(
                free.t,
                sign * envelope,
                color=MUTED,
                linestyle=":",
                linewidth=LINE["guide"],
            )
        direct_label(
            top, free.t[40], envelope[40], "envelope", MUTED, offset=(6.0, 6.0)
        )
        top.set_title("no driving force")
        top.set_xlabel("time (s)")
        top.set_ylabel("position (m)")
        bottom.plot(
            curve,
            steady_state_amplitude(mass, k, b, force, curve),
            color=FIGURE_COLOURS[2],
            linestyle="--",
            linewidth=LINE["model"],
        )
        bottom.plot(
            omegas,
            measured,
            color=FIGURE_COLOURS[0],
            linestyle="none",
            marker="o",
            markersize=MARKER,
        )
        bottom.axhline(force / k, color=MUTED, linestyle=":", linewidth=LINE["guide"])
        direct_label(
            bottom,
            4.2,
            force / k,
            "static\ndeflection",
            MUTED,
            offset=(0.0, 4.0),
            ha="right",
            va="bottom",
        )
        direct_label(
            bottom,
            omegas[5],
            measured[5],
            "simulated",
            FIGURE_COLOURS[0],
            offset=(6.0, 8.0),
        )
        direct_label(
            bottom,
            1.25,
            float(steady_state_amplitude(mass, k, b, force, 1.25)),
            "closed form",
            FIGURE_COLOURS[2],
            offset=(-6.0, 14.0),
            ha="right",
        )
        bottom.set_title("steady driving")
        bottom.set_xlabel("driving frequency (rad/s)")
        bottom.set_ylabel("amplitude (m)")
    return finish(fig)


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    with experiment.capture("checks"):
        list_checks()
    with experiment.capture("correct"):
        correct = correct_steppers()
    with experiment.capture("verlet-findings"):
        verlet_findings(correct)
    with experiment.capture("verlet-convergence"):
        verlet_convergence()
    experiment.figure("fig-verification-convergence", draw_verification_convergence)
    with experiment.capture("gallery"):
        gallery()
    with experiment.capture("claimed-orders"):
        claimed_orders()
    with experiment.capture("report"):
        report_on_equal_weights()
    with experiment.capture("margins"):
        margins()
    with experiment.capture("one-acceleration"):
        one_acceleration()
    steppers_on_the_model(experiment)
    reference_findings(experiment)
    experiment.figure("fig-driven-limits", draw_driven_limits)
    experiment.figure("fig-driven-convergence", draw_driven_convergence)
    faulty_simulations(experiment)
    at_unit_mass(experiment)
    with experiment.capture("submission-report"):
        report_on_a_submission()
    return experiment


if __name__ == "__main__":
    main(run)
