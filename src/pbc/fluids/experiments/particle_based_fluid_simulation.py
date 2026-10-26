"""The experiment of the lesson "Particle-based fluid simulation".

Smoothed particle hydrodynamics of ``pbc.fluids.sph``: the kernel and the
particle estimate of a gradient on a lattice and on disordered particles,
against the central difference of a grid; the elliptical drop, a free-surface
flow with an exact solution; the conservation of mass, momentum, angular
momentum, and energy by a spinning drop; and the density error of weak
compressibility. Run it as a program to write the figures and numbers of the
page:

    uv run --locked --no-dev \\
        python -m pbc.fluids.experiments.particle_based_fluid_simulation out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import Ellipse

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.fluids.sph import (
    Particles,
    angular_momentum,
    drop_pressure,
    ellipse_moments,
    elliptical_drop,
    energy,
    gradient_difference,
    gradient_sum,
    kernel,
    lattice_disc,
    momentum,
    step,
)
from pbc.verification.estimates import fitted_order

ROUND_OFF = 1e-12

# region: gradient
WAVENUMBER = 2 * np.pi  # 1/m: f = sin(k x) cos(k y) on the unit square
GRADIENT_RATIO = 2.0  # h / spacing
JITTER = 0.2  # largest displacement from the lattice, in spacings
gradient_cells = [20, 40, 80]
SEED = 11
# endregion: gradient

# region: drop
RADIUS = 1.0  # m
STRETCH = 1.0  # 1/s, A(0): the velocity (A x, -A y)
RHO0 = 1.0  # kg/m^2
SOUND = 10.0  # m/s, ten times the largest speed of the drop
H_RATIO = 1.3  # h / spacing
COURANT = 0.25  # dt = COURANT h / SOUND
DROP_TIME = 0.5  # s
drop_spacings = [0.1, 0.05]  # m
drop_snapshots = [0.0, 0.25, 0.5]  # s, drawn on the finer drop
# endregion: drop

# region: conservation
SPIN = 0.5  # 1/s, a rigid rotation added to the drop
VISCOSITY = 0.1  # Monaghan's alpha
CONSERVATION_SPACING = 0.1  # m
courants = [0.4, 0.2, 0.1]
# endregion: conservation

sounds = [5.0, 10.0, 20.0, 40.0]  # m/s, exercise 1
LONG_TIME = 0.75  # s, exercise 2


def kernel_integral(h: float) -> float:
    """The integral of the kernel over the plane, by the trapezoidal rule in
    the radius on a fine grid: one for a normalised kernel."""
    r = np.linspace(0.0, 2.0 * h, 20001)
    integrand = 2 * np.pi * r * kernel(r, h)
    return float(np.sum(0.5 * (integrand[1:] + integrand[:-1]) * np.diff(r)))


def square_particles(n: int, disordered: bool) -> np.ndarray:
    """The centres of an n by n lattice on the unit square, each moved by up
    to JITTER spacings in each direction if ``disordered``."""
    spacing = 1.0 / n
    axis = (np.arange(n) + 0.5) * spacing
    x, y = np.meshgrid(axis, axis)
    points = np.column_stack([x.ravel(), y.ravel()])
    if disordered:
        rng = np.random.default_rng(SEED)
        points = points + rng.uniform(-JITTER, JITTER, points.shape) * spacing
    return points


def gradient_errors(n: int) -> tuple[float, float, float, float]:
    """The largest error of the gradient of f = sin(k x) cos(k y) in the
    middle of the square, away from its edges: the central difference of a
    grid of the same spacing, the plain particle estimate on the lattice,
    and the plain and the difference estimates on disordered particles."""
    spacing = 1.0 / n
    h = GRADIENT_RATIO * spacing
    k = WAVENUMBER
    errors = []
    for disordered, estimate in (
        (False, gradient_sum),
        (True, gradient_sum),
        (True, gradient_difference),
    ):
        x = square_particles(n, disordered)
        f = np.sin(k * x[:, 0]) * np.cos(k * x[:, 1])
        exact = np.column_stack(
            [
                k * np.cos(k * x[:, 0]) * np.cos(k * x[:, 1]),
                -k * np.sin(k * x[:, 0]) * np.sin(k * x[:, 1]),
            ]
        )
        volume = np.full(len(x), spacing**2)
        middle = np.all((x > 0.3) & (x < 0.7), axis=1)
        errors.append(float(np.max(np.abs(estimate(x, f, volume, h) - exact)[middle])))
    # The central difference of sin(k x) has the relative error 1 - sin(k dx) / (k dx).
    central = k**2 * (1.0 - np.sin(k * spacing) / (k * spacing))
    return (float(central), *errors)


def gradient_run(experiment: Experiment) -> dict:
    """Every estimate on every spacing; record the table and return the
    errors."""
    rows = [gradient_errors(n) for n in gradient_cells]
    spacings = 1.0 / np.array(gradient_cells)
    found = {
        "spacing": spacings,
        "central": [r[0] for r in rows],
        "lattice": [r[1] for r in rows],
        "plain": [r[2] for r in rows],
        "difference": [r[3] for r in rows],
    }
    assert fitted_order(spacings, found["lattice"]) > 1.8
    assert found["plain"][-1] > found["plain"][0], "the plain error does not grow"
    experiment.table(
        "gradient-run",
        [(s, *r) for s, r in zip(spacings, rows, strict=False)],
        [
            ("spacing", "m", ".4f"),
            ("grid, central difference", "1/m", ".3f"),
            ("particles on a lattice", "1/m", ".3f"),
            ("disordered, plain sum", "1/m", ".3f"),
            ("disordered, difference", "1/m", ".3f"),
        ],
        "The largest error of the gradient of sin(k x) cos(k y), whose largest "
        "value is k, about 6.28 per metre, in the middle of the unit square, "
        "for each spacing, with the kernel width twice the spacing, to three "
        "decimals.",
    )
    experiment.number("lattice-order", fitted_order(spacings, found["lattice"]), ".1f")
    return found


def draw_particle_gradient(found: dict) -> Figure:
    """The errors against the spacing, log-log, with a reference slope two."""
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    h = found["spacing"]
    series = (
        ("central", "grid, central difference", "o", "-"),
        ("lattice", "particles on a lattice", "s", "--"),
        ("plain", "disordered, plain sum", "^", ":"),
        ("difference", "disordered, difference", "D", "-."),
    )
    for (key, label, marker, style), colour in zip(
        series, FIGURE_COLOURS, strict=False
    ):
        ax.loglog(
            h, found[key], marker=marker, linestyle=style, color=colour, label=label
        )
    ax.loglog(
        h,
        0.5 * found["central"][0] * (h / h[0]) ** 2,
        color=FIGURE_COLOURS[2],
        linewidth=0.8,
        label="slope 2 (reference)",
    )
    ax.set_xlabel("particle or grid spacing (m)")
    ax.set_ylabel("largest gradient error (1/m)")
    ax.legend(frameon=False, fontsize="small")
    fig.tight_layout()
    return fig


def percent(fraction: float) -> float:
    """A fraction in per cent, rounded to the tables' two decimals with the
    sign of zero removed."""
    return float(np.round(100 * fraction, 2)) + 0.0


def drop(spacing: float, sound: float = SOUND, spin: float = 0.0) -> Particles:
    """The circular drop with the stretching velocity (A x, -A y), a rigid
    rotation ``spin``, and the pressure of the exact solution at the start,
    P = rho0 A^2 (R^2 - r^2) / 2, carried by the density rho0 + P / sound^2."""
    x = lattice_disc(RADIUS, spacing)
    v = np.column_stack(
        [STRETCH * x[:, 0] - spin * x[:, 1], -STRETCH * x[:, 1] + spin * x[:, 0]]
    )
    p = 0.5 * RHO0 * STRETCH**2 * (RADIUS**2 - np.sum(x**2, axis=1))
    return Particles(x, v, RHO0 + p / sound**2, RHO0 * spacing**2)


def evolve(
    state: Particles,
    spacing: float,
    duration: float,
    sound: float = SOUND,
    courant: float = COURANT,
    viscosity: float = 0.0,
    keep: tuple[float, ...] = (),
) -> tuple[Particles, list[np.ndarray], int]:
    """Equal steps of courant h / sound up to ``duration``; the positions at
    the times ``keep`` that the steps reach, and the number of steps."""
    h = H_RATIO * spacing
    steps = int(np.ceil(duration / (courant * h / sound)))
    dt = duration / steps
    kept = [state.x] if 0.0 in keep else []
    marks = {round(t / dt) for t in keep if t > 0}
    for n in range(1, steps + 1):
        state = step(state, dt, h, RHO0, sound, viscosity)
        if n in marks:
            kept.append(state.x)
    return state, kept, steps


def drop_run(experiment: Experiment) -> dict:
    """The drop on each spacing against the exact semi-axes; record the
    table and return the snapshots of the finer drop."""
    exact_a, exact_b, _ = elliptical_drop([DROP_TIME], STRETCH, RADIUS)
    rows, snapshots = [], []
    for spacing in drop_spacings:
        start = drop(spacing)
        a0, b0 = ellipse_moments(start.x)
        end, kept, _ = evolve(start, spacing, DROP_TIME, keep=tuple(drop_snapshots))
        a, b = ellipse_moments(end.x)
        a, b = a / a0 * RADIUS, b / b0 * RADIUS
        rows.append(
            (
                spacing,
                len(start.x),
                a,
                percent(a / exact_a[0] - 1),
                b,
                percent(b / exact_b[0] - 1),
                100 * float(np.max(np.abs(end.rho / RHO0 - 1))),
            )
        )
        snapshots = kept
    assert all(abs(r[3]) < 1.0 and abs(r[5]) < 2.0 for r in rows)
    experiment.table(
        "drop-run",
        rows,
        [
            ("spacing", "m", ".2f"),
            ("particles", "", "d"),
            ("a", "m", ".4f"),
            ("error of a", "%", ".2f"),
            ("b", "m", ".4f"),
            ("error of b", "%", ".2f"),
            ("largest density change", "%", ".2f"),
        ],
        "The elliptical drop after half a second, for each particle spacing: "
        "the semi-axes a and b from the second moments of the particles, "
        "scaled by their values at the start, their errors against the exact "
        "semi-axes, and the largest change of a particle's density.",
    )
    experiment.number("exact-a", exact_a[0], ".4f")
    experiment.number("exact-b", exact_b[0], ".4f")
    return {"snapshots": snapshots}


def draw_elliptical_drop(found: dict) -> Figure:
    """The particles of the finer drop at the snapshots, with the exact
    ellipses."""
    fig, axes = plt.subplots(1, 3, figsize=(7.6, 2.6), sharey=True)
    a, b, _ = elliptical_drop(drop_snapshots[1:], STRETCH, RADIUS)
    semi = [(RADIUS, RADIUS), *list(zip(a, b, strict=False))]
    for ax, x, (sa, sb), t in zip(
        axes, found["snapshots"], semi, drop_snapshots, strict=False
    ):
        ax.plot(
            x[:, 0],
            x[:, 1],
            linestyle="none",
            marker=".",
            markersize=1.6,
            color=FIGURE_COLOURS[0],
            label="particles",
        )
        ax.add_patch(
            Ellipse(
                (0, 0),
                2 * sa,
                2 * sb,
                fill=False,
                linestyle="--",
                color=FIGURE_COLOURS[1],
                label="exact surface",
            )
        )
        ax.set_title(f"t = {t:.2f} s", fontsize="medium")
        ax.set_xlim(-1.8, 1.8)
        ax.set_ylim(-1.2, 1.2)
        ax.set_aspect("equal")
        ax.set_xlabel("x (m)")
    axes[0].set_ylabel("y (m)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        ncol=2,
        frameon=False,
        fontsize="small",
        markerscale=4,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.9), w_pad=0.4)
    return fig


def conservation_run(experiment: Experiment) -> None:
    """The spinning drop with artificial viscosity for each time step: the
    change of the mass, the momentum, the angular momentum, and the energy
    with the heat; record the table and the orders."""
    rows, angular, energies = [], [], []
    for courant in courants:
        start = drop(CONSERVATION_SPACING, spin=SPIN)
        end, _, steps = evolve(
            start, CONSERVATION_SPACING, DROP_TIME, courant=courant, viscosity=VISCOSITY
        )
        dp = float(np.max(np.abs(momentum(end) - momentum(start))))
        assert dp < ROUND_OFF and len(end.x) == len(start.x)
        angular.append(abs(angular_momentum(end) / angular_momentum(start) - 1))
        e0 = energy(start, RHO0, SOUND)
        energies.append(abs(energy(end, RHO0, SOUND) / e0 - 1))
        heat = float(end.mass * np.sum(end.heat)) / e0
        rows.append(
            (
                DROP_TIME / steps,
                f"below {ROUND_OFF:.0e}",
                angular[-1],
                energies[-1],
                heat,
            )
        )
    steps = [row[0] for row in rows]
    experiment.table(
        "conservation-run",
        rows,
        [
            ("time step", "s", ".5f"),
            ("change of momentum", "kg/s", ""),
            ("change of angular momentum", "relative", ".2e"),
            ("change of energy", "relative", ".2e"),
            ("heat made by the viscosity", "relative", ".4f"),
        ],
        "The spinning drop with artificial viscosity after half a second, for "
        "each time step: the largest change of a component of the total "
        "momentum, the relative changes of the angular momentum and of the "
        "energy with the heat included, and the heat as a fraction of the "
        "energy at the start.",
    )
    experiment.number("angular-order", fitted_order(steps, angular), ".1f")
    experiment.number("energy-order", fitted_order(steps, energies), ".1f")
    experiment.number("round-off", ROUND_OFF, ".0e")
    experiment.number("heat-fraction", rows[-1][4], ".3f")


def compressibility_run(experiment: Experiment) -> None:
    """Exercise 1: for each speed of sound, the mean density change of the
    drop against the mean of the exact pressure over sound^2, and the rms of
    what is left of the density change; the fitted power of the Mach number
    of each."""
    (a,), (b,), (rate,) = elliptical_drop([DROP_TIME], STRETCH, RADIUS)
    centre = drop_pressure(a, b, rate, RHO0)
    rows, means, noise = [], [], []
    for sound in sounds:
        end, _, _ = evolve(drop(0.1, sound), 0.1, DROP_TIME, sound=sound)
        q = end.x[:, 0] ** 2 / a**2 + end.x[:, 1] ** 2 / b**2
        exact = RHO0 + np.clip(centre * (1 - q), 0.0, None) / sound**2
        means.append(float(np.mean(end.rho / RHO0 - 1)))
        noise.append(float(np.sqrt(np.mean((end.rho - exact) ** 2))) / RHO0)
        rows.append(
            (
                sound,
                STRETCH * RADIUS / sound,
                100 * means[-1],
                100 * float(np.mean(exact / RHO0 - 1)),
                100 * noise[-1],
            )
        )
    mach = np.log([STRETCH * RADIUS / s for s in sounds])
    experiment.table(
        "compressibility-run",
        rows,
        [
            ("speed of sound", "m/s", ".0f"),
            ("Mach number", "", ".3f"),
            ("mean density change", "%", ".4f"),
            ("from the exact pressure", "%", ".4f"),
            ("rms of the rest", "%", ".4f"),
        ],
        "The drop on the coarser spacing after half a second, for four speeds "
        "of sound: the Mach number of the largest initial speed, the mean "
        "change of the particles' density, the mean change that the exact "
        "pressure over the square of the speed of sound gives at their "
        "positions, and the root mean square of the difference between the "
        "two at each particle.",
    )
    experiment.number("mean-power", np.polyfit(mach, np.log(means), 1)[0], ".1f")
    experiment.number("noise-power", np.polyfit(mach, np.log(noise), 1)[0], ".1f")


def long_run(experiment: Experiment) -> None:
    """Exercise 2: the coarse drop at DROP_TIME and at LONG_TIME, the errors
    of its semi-axes and the neighbours of a particle along x at the end."""
    rows = []
    for duration in (DROP_TIME, LONG_TIME):
        start = drop(0.1)
        a0, b0 = ellipse_moments(start.x)
        end, _, _ = evolve(start, 0.1, duration)
        a, b = ellipse_moments(end.x)
        ea, eb, _ = elliptical_drop([duration], STRETCH, RADIUS)
        rows.append(
            (
                duration,
                percent(a / a0 / ea[0] - 1),
                percent(b / b0 / eb[0] - 1),
                2 * H_RATIO / ea[0],
            )
        )
    experiment.table(
        "long-run",
        rows,
        [
            ("time", "s", ".2f"),
            ("error of a", "%", ".2f"),
            ("error of b", "%", ".2f"),
            ("kernel reach along x", "spacings", ".2f"),
        ],
        "The drop on the coarser spacing at two times: the errors of its "
        "semi-axes against the exact ones, and the reach 2h of the kernel "
        "measured in the stretched spacing of the particles along x.",
    )
    experiment.number("long-error-start", rows[0][2], ".2f")
    experiment.number("long-error-end", rows[1][2], ".2f")


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()

    experiment.number("kernel-integral", kernel_integral(1.0), ".6f")
    gradients = gradient_run(experiment)
    experiment.figure(
        "fig-particle-gradient", partial(draw_particle_gradient, gradients)
    )

    found = drop_run(experiment)
    experiment.figure("fig-elliptical-drop", partial(draw_elliptical_drop, found))

    conservation_run(experiment)
    compressibility_run(experiment)
    long_run(experiment)
    return experiment


if __name__ == "__main__":
    main(run)
