"""The experiment of the lesson "Quantum tunnelling".

An electron at a rectangular barrier: the transmission and reflection
coefficients against the energy, computed by integrating the stationary
equation across the barrier (``pbc.quantum.barrier.scattering``) and
compared with the closed form; the order of that integration; the
exponential fall with the width; and a wave packet sent at the barrier with
the solver of the first lesson. Run it as a program to write the figures and
numbers of the page:

    uv run --locked --no-dev python -m pbc.quantum.experiments.quantum_tunnelling out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.quantum.barrier import (
    HBAR,
    KINETIC,
    on_grid,
    packet_transmission,
    rectangle,
    scattering,
    transmission,
    wavenumber,
)
from pbc.quantum.schrodinger import crank_nicolson, gaussian_packet, line, norm
from pbc.verification.estimates import convergence_table, fitted_order

# region: setup
# An electron; energies in eV, lengths in nm, times in fs.
HEIGHT = 1.0  # V0, the height of the barrier
WIDTH = 0.5  # a, its width; it stands on [0, a]
# endregion: setup

# region: spectrum
energies = [0.1, 0.3, 0.5, 0.7, 0.9, 1.0, 1.2, 1.5, 2.0, 3.0]
rk_steps = 40  # Runge-Kutta steps across the barrier
# endregion: spectrum

# region: convergence
check_energy = 0.5
step_counts = [10, 20, 40, 80]
# endregion: convergence

# region: widths
widths = [0.25, 0.5, 1.0, 1.5, 2.0]
# endregion: widths

# region: packet
packet_energy = 0.6  # the energy of the mean wavenumber
packet_width = 3.0  # sigma, nm
packet_centre = -30.0  # nm
LEFT, RIGHT = -80.0, 80.0
spacings = [0.04, 0.02, 0.01]  # nm, with dt = 5 h fs per nm
end_time = 110.0  # fs
# endregion: packet

BALANCE_BOUND = 1e-6


def below(value: float, bound: float) -> str:
    """A gap below the stated tolerance is not shown as a number: only that
    it is smaller than ``bound``."""
    if abs(value) >= bound:
        raise ValueError(f"{value!r} is not below {bound!r}")
    return f"below {bound:.0e}"


def spectrum_run(experiment: Experiment):
    """T and R by Runge-Kutta at ten energies against the closed form;
    record the table."""
    e = np.array(energies)
    t, r = scattering(e, rectangle(HEIGHT), WIDTH, rk_steps)
    exact = transmission(e, HEIGHT, WIDTH)
    gap = float(np.max(np.abs(t - exact)))
    balance = float(np.max(np.abs(r + t - 1)))
    assert gap < 1e-6 and balance < BALANCE_BOUND

    experiment.table(
        "spectrum",
        list(zip(e, exact, t, r, strict=True)),
        [
            ("energy", "eV", ".2f"),
            ("T, closed form", "", ".6f"),
            ("T, Runge-Kutta", "", ".6f"),
            ("R, Runge-Kutta", "", ".6f"),
        ],
        "The transmission and reflection coefficients of the barrier of the "
        "example for an electron: the closed form, and the stationary equation "
        "integrated across the barrier by Runge-Kutta.",
    )
    return t, r, gap, balance


def draw_transmission(t, r) -> Figure:
    """T and R against E / V0: closed form, Runge-Kutta, and the classical
    step."""
    e = np.linspace(0.01, 3.0, 600)
    exact = transmission(e, HEIGHT, WIDTH)
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.plot(e / HEIGHT, exact, color=FIGURE_COLOURS[0], label="T, closed form")
    ax.plot(
        e / HEIGHT,
        1 - exact,
        color=FIGURE_COLOURS[1],
        linestyle="--",
        label="R, closed form",
    )
    ax.plot(
        np.array(energies) / HEIGHT,
        t,
        "o",
        color=FIGURE_COLOURS[0],
        markerfacecolor="none",
        label="T, Runge-Kutta",
    )
    ax.plot(
        np.array(energies) / HEIGHT,
        r,
        "s",
        color=FIGURE_COLOURS[1],
        markerfacecolor="none",
        label="R, Runge-Kutta",
    )
    ax.step(
        [0, 1, 3],
        [0, 1, 1],
        where="post",
        color=FIGURE_COLOURS[2],
        linestyle=":",
        label="T of a classical particle",
    )
    ax.set_xlabel("energy over barrier height, E / V0 (dimensionless)")
    ax.set_ylabel("probability (dimensionless)")
    ax.set_ylim(-0.02, 1.05)
    ax.legend(loc="center right", fontsize="small")
    return fig


def convergence(experiment: Experiment):
    """The error of T at one energy as the Runge-Kutta step is halved; record
    the table."""
    steps = WIDTH / np.array(step_counts)
    exact = float(transmission(check_energy, HEIGHT, WIDTH))
    errors, balances = [], []
    for n in step_counts:
        t, r = scattering(check_energy, rectangle(HEIGHT), WIDTH, n)
        errors.append(abs(float(t[0]) - exact))
        balances.append(abs(float(r[0] + t[0]) - 1))
    order = fitted_order(steps, errors)
    assert order > 3.85 and abs(convergence_table(steps, errors)[-1][2] - 4) < 0.05

    experiment.table(
        "convergence",
        [
            (n, h, e, p, b)
            for n, (h, e, p), b in zip(
                step_counts, convergence_table(steps, errors), balances, strict=True
            )
        ],
        [
            ("steps", "", "d"),
            ("step", "nm", ".4f"),
            ("error of T", "", ".2e"),
            ("observed order", "", ".2f"),
            ("R + T - 1", "", ".1e"),
        ],
        "The error of the transmission at the energy of the example against the "
        "closed form, and the balance R + T - 1, as the Runge-Kutta step across "
        "the barrier is halved.",
    )
    return order


def widths_run(experiment: Experiment):
    """T at one energy for five widths: closed form, Runge-Kutta, and the
    thick-barrier law; record the table."""
    a = np.array(widths)
    kappa = float(np.sqrt((HEIGHT - check_energy) / KINETIC))
    exact = np.array([transmission(check_energy, HEIGHT, w) for w in a]).ravel()
    computed = np.array(
        [scattering(check_energy, rectangle(HEIGHT), w, round(160 * w))[0] for w in a]
    ).ravel()
    law = (
        16 * check_energy * (HEIGHT - check_energy) / HEIGHT**2 * np.exp(-2 * kappa * a)
    )
    assert np.all(np.abs(computed / exact - 1) < 1e-6)

    experiment.table(
        "widths",
        list(zip(a, exact, computed, law, strict=True)),
        [
            ("width", "nm", ".2f"),
            ("T, closed form", "", ".3e"),
            ("T, Runge-Kutta", "", ".3e"),
            ("thick-barrier law", "", ".3e"),
        ],
        "The transmission at the energy of the example through barriers of its "
        "height and five widths, and the law of a thick barrier.",
    )
    return a, exact, computed, law, kappa


def draw_widths(a, exact, computed, law) -> Figure:
    """T against the width on a logarithmic axis, with the thick-barrier
    law."""
    w = np.linspace(0.05, 2.1, 200)
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.semilogy(
        w,
        transmission(check_energy, HEIGHT, w),
        color=FIGURE_COLOURS[0],
        label="closed form",
    )
    ax.semilogy(
        a,
        computed,
        "o",
        color=FIGURE_COLOURS[0],
        markerfacecolor="none",
        label="Runge-Kutta",
    )
    kappa = np.sqrt((HEIGHT - check_energy) / KINETIC)
    ax.semilogy(
        w,
        16
        * check_energy
        * (HEIGHT - check_energy)
        / HEIGHT**2
        * np.exp(-2 * kappa * w),
        color=FIGURE_COLOURS[1],
        linestyle="--",
        label="thick-barrier law",
    )
    ax.set_xlabel("barrier width a (nm)")
    ax.set_ylabel("transmission T (dimensionless)")
    ax.legend()
    return fig


def packet_evolution(h: float, records: int = 1):
    """The packet sent at the barrier, evolved by Crank-Nicolson with the
    electron's constants."""
    grid = line(LEFT, RIGHT, round((RIGHT - LEFT) / h))
    k0 = float(wavenumber(packet_energy))
    dt = 5 * h
    n_steps = round(end_time / dt)
    run = crank_nicolson(
        gaussian_packet(
            grid.x, centre=packet_centre, width=packet_width, wavenumber=k0
        ),
        on_grid(grid.x, grid.h, HEIGHT, WIDTH),
        h=grid.h,
        dt=dt,
        n_steps=n_steps,
        every=n_steps // records,
        kinetic=KINETIC,
        hbar=HBAR,
    )
    return grid, run


def packet_run(experiment: Experiment):
    """The probability that passes the barrier, on three grids, against T
    averaged over the packet's wavenumbers; record the table."""
    k0 = float(wavenumber(packet_energy))
    expected = packet_transmission(k0, packet_width, HEIGHT, WIDTH)
    rows = []
    for h in spacings:
        grid, run = packet_evolution(h)
        last = run.psi[-1]
        passed = grid.h * np.sum(np.abs(last[grid.x > WIDTH]) ** 2)
        back = grid.h * np.sum(np.abs(last[grid.x < 0]) ** 2)
        drift = abs(norm(last, grid.h) - norm(run.psi[0], grid.h))
        rows.append((h, 5 * h, passed, back, passed / expected - 1, drift))
    assert abs(rows[1][4]) < 1e-4
    assert all(row[5] < 1e-10 for row in rows)

    experiment.table(
        "packet",
        [row[:5] for row in rows],
        [
            ("spacing", "nm", ".2f"),
            ("time step", "fs", ".2f"),
            ("probability passed", "", ".6f"),
            ("probability reflected", "", ".6f"),
            ("relative gap to averaged T", "", ".1e"),
        ],
        "The probability on each side of the barrier at the end of the run, on "
        "three grids, and the relative gap of the part that passed to T averaged "
        "over the packet's wavenumbers.",
    )
    return expected, rows


def draw_packet(grid, run) -> Figure:
    """The probability density before, during, and after the collision, one
    panel each, with the barrier shaded."""
    fig, axes = plt.subplots(len(run.t), 1, figsize=(6.4, 4.8), sharex=True)
    for ax, t, psi in zip(axes, run.t, run.psi, strict=True):
        ax.plot(grid.x, np.abs(psi) ** 2, color=FIGURE_COLOURS[0])
        ax.axvspan(0, WIDTH, color=FIGURE_COLOURS[1], alpha=0.5)
        ax.set_ylim(0, 0.16)
        ax.text(0.02, 0.8, f"t = {t:.0f} fs", transform=ax.transAxes)
    axes[0].annotate(
        "barrier",
        (WIDTH, 0.08),
        xytext=(8, 0.11),
        arrowprops={"arrowstyle": "->", "color": FIGURE_COLOURS[2]},
        color=FIGURE_COLOURS[2],
    )
    axes[-1].set_xlim(-45, 45)
    axes[-1].set_xlabel("position x (nm)")
    fig.supylabel("probability density (1/nm)")
    return fig


def tip(experiment: Experiment):
    """Exercise 1: a barrier 4 eV above the electron, 0.5 nm and 0.6 nm wide:
    the ratio of the transmissions against exp(-2 kappa 0.1 nm)."""
    energy, height = 1.0, 5.0
    near, far = (
        float(scattering(energy, rectangle(height), w, 200)[0][0]) for w in (0.5, 0.6)
    )
    kappa = np.sqrt((height - energy) / KINETIC)
    return near, far, far / near, float(np.exp(-2 * kappa * 0.1))


def resonances():
    """Exercise 2: the energy of the largest T between 2 and 3 eV and between
    6 and 8 eV, on a fine scan by Runge-Kutta, against
    V0 + kinetic (n pi / a)^2."""
    found = []
    for low, high in ((2.0, 3.0), (6.0, 8.0)):
        e = np.linspace(low, high, 4001)
        t, _ = scattering(e, rectangle(HEIGHT), WIDTH, 80)
        found.append((float(e[np.argmax(t)]), float(t.max())))
    predicted = [HEIGHT + KINETIC * (n * np.pi / WIDTH) ** 2 for n in (1, 2)]
    return found, predicted


def smooth(x):
    return HEIGHT * np.sin(np.pi * np.asarray(x) / WIDTH) ** 2


def smooth_barrier():
    """Exercise 3: T at 0.5 eV through V0 sin^2(pi x / a) on three step
    counts, and through the rectangle."""
    values = [
        float(scattering(check_energy, smooth, WIDTH, n)[0][0]) for n in (20, 40, 80)
    ]
    return values, float(transmission(check_energy, HEIGHT, WIDTH))


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    t, r, gap, balance = spectrum_run(experiment)
    experiment.figure("fig-transmission", partial(draw_transmission, t, r))
    experiment.number("spectrum-gap", below(gap, 1e-6))
    experiment.number("balance", below(balance, BALANCE_BOUND))
    experiment.number("t-low", float(transmission(0.5, HEIGHT, WIDTH)), ".3f")
    experiment.number("r-high", 1 - float(transmission(2.0, HEIGHT, WIDTH)), ".3f")

    order = convergence(experiment)
    experiment.number("order", order, ".2f")

    a, exact, computed, law, kappa = widths_run(experiment)
    experiment.figure("fig-widths", partial(draw_widths, a, exact, computed, law))
    experiment.number("kappa", kappa, ".2f")
    experiment.number("decade", np.log(10) / (2 * kappa), ".3f")
    experiment.number("law-gap", abs(law[2] / exact[2] - 1) * 100, ".2f")

    expected, rows = packet_run(experiment)
    grid, evolution = packet_evolution(spacings[1], 2)
    experiment.figure("fig-packet", partial(draw_packet, grid, evolution))
    experiment.number("packet-expected", expected, ".4f")
    experiment.number("packet-passed", rows[1][2], ".4f")
    experiment.number(
        "packet-t0", float(transmission(packet_energy, HEIGHT, WIDTH)), ".4f"
    )

    near, far, ratio, law_ratio = tip(experiment)
    experiment.number("tip-near", near, ".3e")
    experiment.number("tip-far", far, ".3e")
    experiment.number("tip-ratio", ratio, ".3f")
    experiment.number("tip-law", law_ratio, ".3f")
    found, predicted = resonances()
    for n, ((energy, peak), expect) in enumerate(zip(found, predicted, strict=True), 1):
        experiment.number(f"resonance-{n}", energy, ".3f")
        experiment.number(f"resonance-{n}-predicted", expect, ".3f")
        experiment.number(f"resonance-{n}-peak", below(1 - peak, 1e-6))
    values, rectangular = smooth_barrier()
    experiment.number("smooth-20", values[0], ".6f")
    experiment.number("smooth-40", values[1], ".6f")
    experiment.number("smooth-80", values[2], ".6f")
    experiment.number("smooth-rectangle", rectangular, ".6f")
    return experiment


if __name__ == "__main__":
    main(run)
