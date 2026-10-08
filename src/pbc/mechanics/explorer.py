"""The data of the integrator explorer, the interactive figure of the
numerical-integrators lesson.

The widget in ``site/widgets/integrator-explorer.js`` does no physics. This
module runs every integrator of ``pbc.mechanics.integrators`` on the harmonic
oscillator at every step count the widget offers, when the page is built, and
the page embeds the results. What the widget displays is therefore a result of
the tested package, and a test compares the displayed numbers with a fresh
run (tests/e2e/test_widgets.py).

Units are SI as in ``pbc.mechanics.dynamics``.
"""

import numpy as np

from pbc.mechanics.dynamics import State, newton, simulate
from pbc.mechanics.integrators import INTEGRATORS
from pbc.mechanics.oscillator import angular_frequency, energy, harmonic_motion, spring

# The step counts per period the widget offers, from a step so coarse that
# the methods differ in kind to one fine enough that they agree.
STEPS_PER_PERIOD = (4, 6, 8, 12, 16, 24, 32, 50, 100)

# Significant digits of the series sent to the page. The numbers the widget
# displays (final energy, error, calls) are rounded by the widget, not here.
SERIES_DIGITS = 5

# Points of the exact curve drawn in the position panel, per period.
EXACT_POINTS_PER_PERIOD = 40


def _rounded(values: np.ndarray, digits: int = SERIES_DIGITS) -> list[float]:
    return [float(f"{value:.{digits}g}") for value in values]


def explorer_data(
    mass: float = 0.5,
    k: float = 2.0,
    amplitude: float = 1.0,
    n_periods: int = 5,
    steps_per_period: tuple[int, ...] = STEPS_PER_PERIOD,
) -> dict:
    """Return the runs of every integrator at every step count, as plain
    data for JSON.

    The oscillator is released from rest at ``amplitude`` (m). For each
    integrator and step count the entry holds the position ``x`` (m) and the
    energy relative to the initial energy ``e`` at the steps, the energy at
    the end, the largest difference between the position and the exact one at
    the steps (m), and the number of evaluations of the acceleration.
    """
    omega = angular_frequency(mass, k)
    period = 2 * np.pi / omega
    released = State(t=0.0, x=amplitude, v=0.0)
    acceleration = newton(mass, spring(k))

    t_exact = np.linspace(
        0.0, n_periods * period, n_periods * EXACT_POINTS_PER_PERIOD + 1
    )
    exact = harmonic_motion(released, mass, k, t_exact)

    runs = []
    for integrator in INTEGRATORS:
        series = []
        for n in steps_per_period:
            trajectory = simulate(
                released, acceleration, period / n, n * n_periods, step=integrator.step
            )
            relative = energy(trajectory, mass, k)
            relative = relative / relative[0]
            reference = harmonic_motion(released, mass, k, trajectory.t)
            series.append(
                {
                    "steps_per_period": n,
                    "x": _rounded(trajectory.x[:, 0]),
                    "e": _rounded(relative),
                    "final_energy": float(relative[-1]),
                    "max_error": float(np.max(np.abs(trajectory.x - reference.x))),
                    "calls": n * n_periods * integrator.evaluations,
                }
            )
        runs.append(
            {"name": integrator.name, "order": integrator.order, "series": series}
        )

    return {
        "mass": mass,
        "k": k,
        "omega": omega,
        "period": period,
        "n_periods": n_periods,
        "amplitude": amplitude,
        "exact": {"t": _rounded(t_exact), "x": _rounded(exact.x[:, 0])},
        "integrators": runs,
    }
