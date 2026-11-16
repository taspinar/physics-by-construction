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
from pbc.figure_language import figsize, figure_style, finish
from pbc.mechanics.dynamics import State
from pbc.mechanics.integrators import rk4_step, verlet_step
from pbc.verification import (
    CHECKS,
    Claim,
    convergence_table,
    fitted_order,
    oscillator_error,
    verify,
)
from pbc.verification.faulty import (
    CORRECT,
    GALLERY,
    rk4_with_equal_weights,
    verlet_without_the_half,
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
    return experiment


if __name__ == "__main__":
    main(run)
