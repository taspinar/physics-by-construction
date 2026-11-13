"""Benchmarks of the two-dimensional shallow-water model of the capstone FL10
(``pbc.fluids.tsunami``) against exact solutions of linear long waves on a
flat bed: a plane hump, which splits into two waves that keep their shape
(d'Alembert), and a round hump, which spreads in rings (the Hankel transform
of the wave equation). They use no data.
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.ticker import NullFormatter
from scipy.special import erf, j0

from pbc.authoring import FIGURE_COLOURS
from pbc.fluids import tsunami
from pbc.fluids.shallow_water import GRAVITY

__all__ = [
    "PLANE",
    "RADIAL",
    "draw_plane_wave_convergence",
    "plane_wave_error",
    "plane_wave_errors",
    "radial_exact",
    "radial_run",
]

# A Gaussian hump on a flat bed: depth (m), amplitude (m), width sigma (m),
# time (s); the plane hump in a channel of the length (m).
PLANE = {
    "depth": 4000.0,
    "amplitude": 0.01,
    "sigma": 40e3,
    "t": 1000.0,
    "length": 800e3,
}
RADIAL = {"depth": 4000.0, "amplitude": 0.01, "sigma": 30e3, "t": 1200.0, "size": 500e3}


def plane_wave_error(n: int, limiter: str | None, courant: float) -> float:
    """The plane hump on ``n`` cells: the rms difference of the computed cell
    averages from d'Alembert's after ``PLANE["t"]``, relative to the
    amplitude; first order (FL5's scheme) if ``limiter`` is None."""
    length, depth, sigma = PLANE["length"], PLANE["depth"], PLANE["sigma"]
    amplitude, t = PLANE["amplitude"], PLANE["t"]
    dx = length / n
    edges = np.arange(n + 1) * dx
    c = np.sqrt(GRAVITY * depth)

    def average(centre: float) -> np.ndarray:
        z = (edges - centre) / (np.sqrt(2.0) * sigma)
        return amplitude * sigma * np.sqrt(np.pi / 2) * np.diff(erf(z)) / dx

    # Two rows and a very long cell across them: a channel along x.
    grid = tsunami.plane_grid(np.full((2, n), -depth), dx, 1e12)
    q = np.zeros((2, n, 3))
    q[..., 0] = depth + average(0.5 * length)
    second = limiter is not None
    run = tsunami.simulate(
        grid, q, t, courant, second_order=second, limiter=limiter or "minmod"
    )
    exact = 0.5 * (average(0.5 * length + c * t) + average(0.5 * length - c * t))
    return float(np.sqrt(np.mean((run.q[0, :, 0] - depth - exact) ** 2)) / amplitude)


def plane_wave_errors(
    cells: tuple[int, ...], schemes: dict[str, str | None], courant: float
) -> dict[str, list[float]]:
    """``plane_wave_error`` of every scheme (name -> limiter or None) on
    every number of cells."""
    return {
        name: [plane_wave_error(n, limiter, courant) for n in cells]
        for name, limiter in schemes.items()
    }


def radial_exact(r: np.ndarray, t: float) -> np.ndarray:
    """The linear wave of the round hump at the distances ``r`` (m) at the
    time ``t`` (s), by the Hankel transform: eta = A s^2 int k exp(-k^2 s^2
    / 2) J0(k r) cos(c k t) dk, by the trapezoid rule on 4001 points up to
    k = 10 / s, where the integrand is below e^-50 of its scale."""
    a, s, depth = RADIAL["amplitude"], RADIAL["sigma"], RADIAL["depth"]
    c = np.sqrt(GRAVITY * depth)
    k = np.linspace(0.0, 10.0 / s, 4001)
    integrand = k * np.exp(-0.5 * (k * s) ** 2) * j0(np.outer(r, k)) * np.cos(c * k * t)
    return a * s * s * np.trapezoid(integrand, k, axis=1)


def radial_run(
    dx: float, courant: float, limiter: str, max_steps: int = 1_000_000
) -> tuple[tsunami.Run, np.ndarray]:
    """The round hump in the corner of a quarter domain with walls (the two
    walls through the hump are its planes of symmetry), on cells of ``dx``
    (m), until ``RADIAL["t"]``; with the distance of every cell's centre
    from the hump. Overflow of an unstable run is not reported."""
    n = round(RADIAL["size"] / dx)
    x = (np.arange(n) + 0.5) * dx
    r = np.hypot(*np.meshgrid(x, x, indexing="ij"))
    grid = tsunami.plane_grid(np.full((n, n), -RADIAL["depth"]), dx, dx)
    q = np.zeros((n, n, 3))
    q[..., 0] = RADIAL["depth"] + RADIAL["amplitude"] * np.exp(
        -0.5 * (r / RADIAL["sigma"]) ** 2
    )
    with np.errstate(all="ignore"):
        run = tsunami.simulate(
            grid,
            q,
            RADIAL["t"],
            courant,
            open_ends=False,
            max_steps=max_steps,
            limiter=limiter,
        )
    return run, r


def draw_plane_wave_convergence(
    errors: dict[str, list[float]], cells: tuple[int, ...]
) -> Figure:
    """The errors of ``plane_wave_errors`` against the cell size, log-log,
    with reference slopes one and two from the first point of the first and
    the last scheme."""
    fig, ax = plt.subplots(figsize=(4.6, 2.8), layout="constrained")
    sizes = PLANE["length"] / 1e3 / np.array(cells)
    for (name, values), marker, style in zip(
        errors.items(), ("o", "s", "^"), ("-", "--", ":"), strict=False
    ):
        ax.loglog(
            sizes, values, marker=marker, ms=4, ls=style, color=FIGURE_COLOURS[0],
            label=name,
        )  # fmt: skip
    ends = sizes[[0, -1]]
    values = list(errors.values())
    first, last = values[0], values[-1]
    for slope, style, start in ((1, ":", first[0]), (2, "-.", last[0])):
        ax.loglog(
            ends, start * (ends / sizes[0]) ** slope, ls=style, color="0.5", lw=1,
            label=f"slope {slope} (reference)",
        )  # fmt: skip
    ax.set_xticks(sizes, labels=[f"{size:g}" for size in sizes])
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xlabel("cell size (km)")
    ax.set_ylabel("rms error / amplitude")
    ax.set_title("Plane wave against d'Alembert's solution")
    ax.legend(fontsize=7)
    return fig
