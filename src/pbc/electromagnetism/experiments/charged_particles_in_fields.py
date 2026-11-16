"""The experiment of the lesson "Charged particles in electric and magnetic fields".

A proton and an electron under the Lorentz force, integrated with the Boris
pusher (``pbc.electromagnetism.motion``): the cyclotron frequency and the
Larmor radius, the energy against explicit Euler, and the drift in crossed
fields, each against its formula. Run it as a program to write the figures
and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.electromagnetism.experiments.charged_particles_in_fields out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

from pbc.authoring import FIGURE_COLOURS
from pbc.electromagnetism.motion import (
    ELECTRON_CHARGE_TO_MASS,
    PROTON_CHARGE_TO_MASS,
    Trajectory,
    boris,
    boris_frequency,
    boris_radius,
    cyclotron_frequency,
    drift_velocity,
    euler_energy_factor,
    explicit_euler,
    fitted_radius,
    guiding_centre_velocity,
    larmor_radius,
    measured_angular_frequency,
)
from pbc.experiment import Experiment, main
from pbc.figure_language import LINE, direct_label, figsize, figure_style, finish
from pbc.verification.estimates import fitted_order

NO_FIELD = np.zeros(3)

# region: proton
FIELD = np.array([0.0, 0.0, 1.0])  # T
SPEED = 1e5  # m/s
OMEGA = cyclotron_frequency(PROTON_CHARGE_TO_MASS, FIELD[2])  # rad/s
RADIUS = larmor_radius(PROTON_CHARGE_TO_MASS, FIELD[2], SPEED)  # m
PERIOD = 2 * np.pi / OMEGA  # s
METHOD_TOLERANCE = 1e-10  # a chosen tolerance against the pusher's own closed form
per_period = np.array([20, 40, 80, 160, 320])
# endregion: proton

# region: energy
steps_per_turn = 80
turns = 5
ENERGY_FLOOR = 1e-12  # a bound shown in place of a value at round-off
# endregion: energy

# region: crossed
ELECTRIC = np.array([0.0, 1e4, 0.0])  # V/m
DRIFT_TOLERANCE = 1e-8  # a chosen tolerance, relative to the drift speed
particles = [
    ("proton", PROTON_CHARGE_TO_MASS, 1.0),
    ("electron", ELECTRON_CHARGE_TO_MASS, 1e-3),
]
# endregion: crossed


def cyclotron_run(experiment: Experiment) -> tuple[list[float], float]:
    """The frequency and radius of ten simulated turns for each step, against
    the pusher's closed forms and against qB/m and mv/(qB); record the table,
    return the gaps of the frequency and their fitted order."""
    rows = []
    gaps = []
    for n in per_period:
        dt = PERIOD / n
        orbit = boris(
            NO_FIELD,
            [SPEED, 0.0, 0.0],
            q_over_m=PROTON_CHARGE_TO_MASS,
            electric=NO_FIELD,
            magnetic=FIELD,
            dt=dt,
            n_steps=10 * n,
        )
        omega = measured_angular_frequency(orbit.t, orbit.v)
        radius = fitted_radius(orbit.x)
        assert abs(omega / boris_frequency(OMEGA, dt) - 1) < METHOD_TOLERANCE
        assert abs(radius / boris_radius(OMEGA, dt, SPEED) - 1) < METHOD_TOLERANCE
        gaps.append(abs(omega / OMEGA - 1))
        rows.append(
            (n, omega / OMEGA, boris_frequency(OMEGA, dt) / OMEGA, radius / RADIUS)
        )
    order = fitted_order(PERIOD / per_period, gaps)
    assert abs(order - 2.0) < 0.02, "the pusher is not of second order"

    experiment.table(
        "cyclotron-run",
        rows,
        [
            ("steps per period", "", "d"),
            ("measured frequency over qB/m", "", ".8f"),
            ("Boris frequency over qB/m", "", ".8f"),
            ("measured radius over mv/(qB)", "", ".8f"),
        ],
        "The angular frequency and the radius of the simulated orbit of a "
        "proton, measured from ten turns, as fractions of the cyclotron "
        "frequency and the Larmor radius, with the frequency the Boris pusher "
        "predicts for its step, to eight decimals.",
    )
    return gaps, order


def energy_run(experiment: Experiment) -> tuple[Trajectory, Trajectory, float]:
    """Five turns of eighty steps with Boris and with explicit Euler, and the
    energy of each against the start; record the table, return both orbits
    and the final energy of Euler over the initial."""
    dt = PERIOD / steps_per_turn
    pushed = boris(
        NO_FIELD,
        [SPEED, 0.0, 0.0],
        q_over_m=PROTON_CHARGE_TO_MASS,
        electric=NO_FIELD,
        magnetic=FIELD,
        dt=dt,
        n_steps=turns * steps_per_turn,
    )
    euler = explicit_euler(
        NO_FIELD,
        [SPEED, 0.0, 0.0],
        q_over_m=PROTON_CHARGE_TO_MASS,
        electric=NO_FIELD,
        magnetic=FIELD,
        dt=dt,
        n_steps=turns * steps_per_turn,
    )
    boris_energy = np.sum(pushed.v**2, axis=1) / SPEED**2
    euler_energy = np.sum(euler.v**2, axis=1) / SPEED**2
    predicted = euler_energy_factor(OMEGA, dt) ** np.arange(len(euler_energy))
    boris_drift = float(np.max(np.abs(boris_energy - 1.0)))
    assert boris_drift < ENERGY_FLOOR, "the Boris pusher changed the energy"
    assert np.allclose(euler_energy, predicted, rtol=1e-10), (
        "Euler did not grow as predicted"
    )

    experiment.table(
        "energy-run",
        [
            ("Boris", f"below {ENERGY_FLOOR:.0e}", None),
            ("explicit Euler", f"{euler_energy[-1]:.4f}", predicted[-1]),
        ],
        [
            ("method", "", ""),
            ("final energy over initial", "", ""),
            ("predicted by the factor per step", "", ".4f"),
        ],
        "The kinetic energy after five turns of eighty steps, relative to the "
        "start, for each method (for Boris the change from one), and the "
        "growth that the factor of explicit Euler per step predicts.",
    )
    return pushed, euler, float(euler_energy[-1])


def draw_gyration(pushed: Trajectory, euler: Trajectory) -> Figure:
    """The Boris and the Euler orbits against the Larmor circle, in units of
    the Larmor radius."""
    centre = np.array([0.0, -RADIUS])  # a proton moving along x turns towards -y
    angle = np.linspace(0, 2 * np.pi, 361)
    fig, ax = plt.subplots(figsize=(5.6, 5.0))
    ax.plot(
        np.cos(angle),
        np.sin(angle),
        color=FIGURE_COLOURS[2],
        linestyle=":",
        label="Larmor circle",
    )
    ax.plot(
        (pushed.x[:, 0] - centre[0]) / RADIUS,
        (pushed.x[:, 1] - centre[1]) / RADIUS,
        color=FIGURE_COLOURS[0],
        label="Boris",
    )
    ax.plot(
        (euler.x[:, 0] - centre[0]) / RADIUS,
        (euler.x[:, 1] - centre[1]) / RADIUS,
        color=FIGURE_COLOURS[1],
        linestyle="--",
        label="explicit Euler",
    )
    ax.set_aspect("equal")
    ax.set_xlabel("x over the Larmor radius")
    ax.set_ylabel("y over the Larmor radius")
    ax.legend(fontsize=8, loc="upper right")
    return fig


def drift_run(experiment: Experiment) -> dict[str, tuple[Trajectory, float]]:
    """A proton and an electron from rest in crossed fields for fifty turns,
    the fitted velocity of the centre against E x B / B^2; record the table,
    return each orbit and its period."""
    rows = []
    orbits = {}
    for name, q_over_m, b in particles:
        magnetic = np.array([0.0, 0.0, b])
        electric = ELECTRIC * b  # keeps E/B, and so the drift, the same
        expected = drift_velocity(electric, magnetic)
        period = 2 * np.pi / cyclotron_frequency(q_over_m, b)
        dt = period / 50
        orbit = boris(
            NO_FIELD,
            NO_FIELD,
            q_over_m=q_over_m,
            electric=electric,
            magnetic=magnetic,
            dt=dt,
            n_steps=50 * 50,
        )
        omega = measured_angular_frequency(orbit.t, orbit.v, drift=expected)
        found = guiding_centre_velocity(orbit.t, orbit.x, omega)
        gap = float(np.linalg.norm(found - expected) / np.linalg.norm(expected))
        assert gap < DRIFT_TOLERANCE, f"the {name} does not drift with E x B / B^2"
        orbits[name] = (orbit, period)
        rows.append(
            (
                name,
                b,
                electric[1],
                found[0],
                expected[0],
                f"below {DRIFT_TOLERANCE:.0e}",
            )
        )

    experiment.table(
        "drift-run",
        rows,
        [
            ("particle", "", ""),
            ("magnetic field", "T", ".3f"),
            ("electric field", "V/m", ".0f"),
            ("drift along x", "m/s", ".3f"),
            ("E over B", "m/s", ".3f"),
            ("relative difference of the drift vectors", "", ""),
        ],
        "The velocity of the centre of the orbit of a proton and of an electron "
        "in crossed fields, fitted from fifty turns, against the drift E x B "
        "over B squared, to three decimals, and the relative difference of the "
        "two vectors, given as a bound.",
    )
    return orbits


def draw_drift(orbits: dict[str, tuple[Trajectory, float]]) -> Figure:
    """The paths of the proton and the electron over four turns of the
    proton."""
    shown_time = 4 * orbits["proton"][1]  # four turns of the proton
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line"))
        for (name, (orbit, _)), colour, style, below in zip(
            orbits.items(), FIGURE_COLOURS[:2], ["-", "--"], [False, True], strict=True
        ):
            shown = orbit.t <= shown_time
            x = orbit.x[shown, 0] * 1e6
            y = orbit.x[shown, 1] * 1e6
            ax.plot(x, y, color=colour, linestyle=style, label=name)
            # The name beside the end of its path (S5), on its side of the
            # starting line.
            direct_label(
                ax,
                x[-1],
                0.0,
                name,
                colour,
                offset=(4.0, -3.0 if below else 3.0),
                va="top" if below else "bottom",
            )
        ax.axhline(0.0, color=FIGURE_COLOURS[2], linewidth=LINE["guide"])
        ax.set_aspect("equal")
        # A flat plot: three ticks on y, so that their labels stay apart.
        ax.yaxis.set_major_locator(MaxNLocator(3))
        ax.set_xlabel("x (μm)")
        ax.set_ylabel("y (μm)")
    return finish(fig)


def mass_spectrometer() -> tuple[float, float]:
    """Exercise 1: the diameters of the half circles of singly charged
    carbon-12 and carbon-13 ions at 50 km/s in 0.5 T."""
    unit = 1.66054e-27  # kg
    charge = 1.602176634e-19  # C
    light, heavy = (
        2 * larmor_radius(charge / (mass * unit), 0.5, 5e4) for mass in (12.000, 13.003)
    )
    return light, heavy


def electron_in_the_earths_field() -> tuple[float, float]:
    """Exercise 2: the cyclotron frequency in hertz of an electron in 50 μT,
    and its radius at 1000 km/s."""
    electron_omega = cyclotron_frequency(ELECTRON_CHARGE_TO_MASS, 50e-6)
    electron_radius = larmor_radius(ELECTRON_CHARGE_TO_MASS, 50e-6, 1e6)
    return electron_omega / (2 * np.pi), electron_radius


def helix() -> tuple[float, float]:
    """Exercise 3: the advance per turn along the field of the proton with
    30 km/s along it, simulated, and the speed along it times the period."""
    orbit = boris(
        NO_FIELD,
        [SPEED, 0.0, 3e4],
        q_over_m=PROTON_CHARGE_TO_MASS,
        electric=NO_FIELD,
        magnetic=FIELD,
        dt=PERIOD / 80,
        n_steps=800,
    )
    omega = measured_angular_frequency(orbit.t, orbit.v)
    turns_made = omega * orbit.t[-1] / (2 * np.pi)  # the turns of the pusher
    pitch = (orbit.x[-1, 2] - orbit.x[0, 2]) / turns_made
    expected_pitch = 3e4 * 2 * np.pi / omega
    return pitch, expected_pitch


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()

    gaps, order = cyclotron_run(experiment)
    experiment.number("omega", OMEGA, ".4e")
    experiment.number("period-ns", PERIOD * 1e9, ".2f")
    experiment.number("radius-mm", RADIUS * 1e3, ".3f")
    experiment.number("first-gap-percent", gaps[0] * 100, ".2f")
    experiment.number("last-gap", gaps[-1], ".1e")
    experiment.number("frequency-order", order, ".3f")
    experiment.number("method-tolerance", METHOD_TOLERANCE, ".0e")

    pushed, euler, euler_final = energy_run(experiment)
    experiment.figure("fig-gyration", partial(draw_gyration, pushed, euler))
    experiment.number("euler-final", euler_final, ".2f")
    experiment.number("energy-floor", ENERGY_FLOOR, ".0e")

    orbits = drift_run(experiment)
    experiment.figure("fig-drift", partial(draw_drift, orbits))
    experiment.number("drift-tolerance", DRIFT_TOLERANCE, ".0e")

    light, heavy = mass_spectrometer()
    experiment.number("light-cm", light * 100, ".3f")
    experiment.number("heavy-cm", heavy * 100, ".3f")
    experiment.number("apart-mm", (heavy - light) * 1e3, ".2f")

    hertz, radius = electron_in_the_earths_field()
    experiment.number("electron-megahertz", hertz / 1e6, ".3f")
    experiment.number("electron-radius-cm", radius * 100, ".1f")

    pitch, expected_pitch = helix()
    experiment.number("pitch-mm", pitch * 1e3, ".4f")
    experiment.number("expected-pitch-mm", expected_pitch * 1e3, ".4f")
    return experiment


if __name__ == "__main__":
    main(run)
