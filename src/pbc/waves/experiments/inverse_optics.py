"""The experiment of the lesson "Inverse optics".

Synthetic photon counts of a double slit on a flat detector, computed as a
sum of wavelets at a finite distance (``pbc.waves.diffraction``) with Poisson
noise; the slit width and separation estimated with the Fraunhofer model
(``pbc.waves.inverse``); the pulls of many data sets; and the limits of
what the intensity identifies: the wavelength against the separation, and
an aperture against its mirror image. Run it as a program to write the
figures and numbers of the page:

    uv run --locked --no-dev python -m pbc.waves.experiments.inverse_optics out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.waves.diffraction import aperture, far_field, field_at, slits
from pbc.waves.inverse import (
    detector,
    double_slit_model,
    fit,
    residuals,
    scaled_jacobian,
)

# region: setup
WAVELENGTH = 633e-9  # m, known: a helium-neon laser
WIDTH, SEPARATION = 40e-6, 200e-6  # m, the slits the data are made from
DISTANCE = 2.0  # m, from the slits to the detector, known
PIXELS, PITCH = 2000, 50e-6  # a row of pixels 0.1 m long
PEAK, BACKGROUND = 2000.0, 20.0  # expected counts at the centre and per pixel
SEED = 283
REPEATS = 1000  # independent data sets for the pulls
RELATIVE_TOLERANCE = 0.01  # a chosen tolerance on the recovered width and separation
# endregion: setup


def expected_counts(width=WIDTH, separation=SEPARATION, peak=PEAK) -> np.ndarray:
    """The expected counts of each pixel: the intensity of the sum of
    wavelets from the two slits at the detector, scaled to ``peak`` at its
    largest, plus the background."""
    y, _ = detector(PIXELS, PITCH, DISTANCE)
    points, widths = slits(2, width, separation, 400)
    intensity = np.abs(field_at(y, DISTANCE, points, widths, WAVELENGTH)) ** 2
    return peak * intensity / intensity.max() + BACKGROUND


def data(rng: np.random.Generator, expected=None) -> np.ndarray:
    """One synthetic measurement: a Poisson number of photons per pixel."""
    expected = expected_counts() if expected is None else expected
    return rng.poisson(expected).astype(float)


def fit_run(experiment: Experiment):
    """One synthetic data set and the fit of the Fraunhofer model with the
    known wavelength; record the table and return the data and the fit."""
    _, s = detector(PIXELS, PITCH, DISTANCE)
    counts = data(np.random.default_rng(SEED))
    result = fit(s, counts, WAVELENGTH)
    truth = {"width": WIDTH, "separation": SEPARATION}
    rows = []
    for name in ("width", "separation"):
        value, error = result.value(name), result.error(name)
        pull = (value - truth[name]) / error
        assert abs(pull) < 4.0, f"the {name} is more than four standard errors off"
        assert abs(value / truth[name] - 1) < RELATIVE_TOLERANCE
        rows.append((name, truth[name] * 1e6, value * 1e6, error * 1e6, pull))
    experiment.table(
        "fit-run",
        rows,
        [
            ("slit parameter", "", ""),
            ("used to make the data", "µm", ".3f"),
            ("estimate", "µm", ".3f"),
            ("standard error", "µm", ".3f"),
            ("(estimate - used) / error", "", ".2f"),
        ],
        "The width and the separation of the slits estimated from one synthetic "
        "data set with the Fraunhofer model and the known wavelength, against the "
        "values the data were made from, to a thousandth of a micrometre.",
    )
    return s, counts, result


def draw_fit(s, counts, result) -> Figure:
    """The counts, the fitted model, and the Pearson residuals."""
    model = double_slit_model(s, *result.values, WAVELENGTH)
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(6.4, 4.6), sharex=True, gridspec_kw={"height_ratios": [3, 1]}
    )
    top.plot(
        s * 1e3,
        counts,
        ".",
        markersize=2,
        color=FIGURE_COLOURS[2],
        label="synthetic counts",
    )
    top.plot(
        s * 1e3,
        model,
        color=FIGURE_COLOURS[1],
        linestyle="--",
        linewidth=0.9,
        label="fitted model",
    )
    top.set_ylabel("photons per pixel")
    top.legend(fontsize=7, loc="upper right")
    bottom.plot(
        s * 1e3,
        residuals(result.values, s, counts, WAVELENGTH),
        ".",
        markersize=2,
        color=FIGURE_COLOURS[0],
    )
    bottom.axhline(0.0, color=FIGURE_COLOURS[2], linewidth=0.8)
    bottom.set_ylabel("residual (sigma)")
    bottom.set_xlabel("sin(theta), times 1000")
    fig.tight_layout()
    return fig


def pulls_run(experiment: Experiment):
    """Many independent data sets, each fitted: the mean and the spread of
    the pulls (estimate - used) / error; record the table and return the
    pulls."""
    _, s = detector(PIXELS, PITCH, DISTANCE)
    rng = np.random.default_rng(SEED + 1)
    expected = expected_counts()
    pulls, chi2 = [], []
    for _ in range(REPEATS):
        result = fit(s, data(rng, expected), WAVELENGTH)
        pulls.append(
            [
                (result.value("width") - WIDTH) / result.error("width"),
                (result.value("separation") - SEPARATION) / result.error("separation"),
            ]
        )
        chi2.append(result.chi2 / result.dof)
    pulls = np.array(pulls)
    rows = []
    for i, name in enumerate(("width", "separation")):
        mean, spread = float(np.mean(pulls[:, i])), float(np.std(pulls[:, i], ddof=1))
        # the standard error of a mean of unit normals, and of their spread
        assert abs(mean) < 4.0 / np.sqrt(REPEATS)
        assert abs(spread - 1.0) < 4.0 / np.sqrt(2 * (REPEATS - 1))
        rows.append(
            (name, mean, 1 / np.sqrt(REPEATS), spread, 1 / np.sqrt(2 * (REPEATS - 1)))
        )
    experiment.table(
        "pulls-run",
        rows,
        [
            ("slit parameter", "", ""),
            ("mean pull", "", ".3f"),
            ("its standard error", "", ".3f"),
            ("spread of the pulls", "", ".3f"),
            ("its standard error", "", ".3f"),
        ],
        "The pulls (estimate - used) / standard error of the width and the "
        "separation over independent synthetic data sets: for honest errors "
        "and no bias their mean is zero and their spread one.",
    )
    return pulls, float(np.mean(chi2))


def model_bias():
    """The fit to the expected counts themselves, without noise: what is
    left is the bias of the Fraunhofer model against the sum of wavelets at
    the finite distance, in units of the standard error of one data set."""
    _, s = detector(PIXELS, PITCH, DISTANCE)
    r = fit(s, expected_counts(), WAVELENGTH)
    return (
        (r.value("width") - WIDTH) / r.error("width"),
        (r.value("separation") - SEPARATION) / r.error("separation"),
    )


def draw_pulls(pulls) -> Figure:
    """Histograms of the pulls with the unit normal."""
    x = np.linspace(-4, 4, 401)
    normal = np.exp(-(x**2) / 2) / np.sqrt(2 * np.pi)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True)
    for ax, i, name, colour, hatch in zip(
        axes,
        (0, 1),
        ("width", "separation"),
        FIGURE_COLOURS[:2],
        ("", "//"),
        strict=True,
    ):
        ax.hist(
            pulls[:, i],
            bins=np.linspace(-4, 4, 17),
            density=True,
            color=colour,
            alpha=0.35,
            hatch=hatch,
            edgecolor=colour,
            label=f"pulls of the {name}",
        )
        ax.plot(x, normal, color=FIGURE_COLOURS[2], linestyle="--", label="unit normal")
        ax.set_xlabel("(estimate - used) / standard error")
        ax.legend(fontsize=7, loc="upper left")
    axes[0].set_ylabel("density")
    fig.tight_layout()
    return fig


def degeneracy_run(experiment: Experiment, s, counts, result):
    """The singular values of the scaled Jacobian with the wavelength known
    and free, and fits that assume three wavelengths; record the table and
    return the values for the page."""
    jacobian = scaled_jacobian(s, *result.values, WAVELENGTH)
    known = np.linalg.svd(jacobian[:, :4], compute_uv=False)
    free = np.linalg.svd(jacobian, compute_uv=False)
    rows = []
    for assumed in (600e-9, WAVELENGTH, 680e-9):
        r = fit(s, counts, assumed)
        rows.append(
            (
                assumed * 1e9,
                r.value("width") * 1e6,
                r.value("separation") * 1e6,
                r.value("separation") / assumed,
                r.chi2,
            )
        )
    ratios = [row[3] for row in rows]
    chi2 = [row[4] for row in rows]
    assert np.ptp(ratios) / np.mean(ratios) < 1e-6 and np.ptp(chi2) < 1e-6 * np.mean(
        chi2
    )
    experiment.table(
        "degeneracy-run",
        rows,
        [
            ("assumed wavelength", "nm", ".0f"),
            ("width", "µm", ".3f"),
            ("separation", "µm", ".3f"),
            ("separation / wavelength", "", ".3f"),
            ("chi^2", "", ".2f"),
        ],
        "The same synthetic data fitted with three assumed wavelengths: the width "
        "and the separation scale with the wavelength, and the fit is equally good.",
    )
    return known[-1] / known[0], free[-1] / free[0]


def draw_degeneracy(s, counts, result) -> Figure:
    """chi^2 over the assumed wavelength and the separation, the width and
    the amplitude and background held at the fit, with a / lambda kept."""
    amplitude, background, width, separation = result.values
    lams = np.linspace(560e-9, 700e-9, 61)
    seps = np.linspace(180e-6, 220e-6, 61)
    grid = np.empty((seps.size, lams.size))
    for j, lam in enumerate(lams):
        for i, d in enumerate(seps):
            w = width * lam / WAVELENGTH
            grid[i, j] = np.sum(
                residuals((amplitude, background, w, d), s, counts, lam) ** 2
            )
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    image = ax.pcolormesh(
        lams * 1e9,
        seps * 1e6,
        np.log10(grid - grid.min() + 1.0),
        cmap="cividis",
        shading="auto",
    )
    fig.colorbar(image, ax=ax, label="log10(chi^2 - smallest + 1), false colour")
    ax.plot(
        lams * 1e9,
        separation * lams / WAVELENGTH * 1e6,
        color=FIGURE_COLOURS[1],
        linestyle="--",
        label="d / lambda as fitted",
    )
    ax.set_ylim(seps[0], seps[-1])
    ax.set_xlabel("assumed wavelength (nm)")
    ax.set_ylabel("separation d (µm)")
    ax.legend(fontsize=7, loc="upper left")
    return fig


def mirror_run(experiment: Experiment):
    """Two slits of unequal width and their mirror image: the far-field
    intensities and the intensities on the detector at the finite distance;
    record the table and return the differences."""
    narrow, wide = 30e-6, 50e-6
    left = (-SEPARATION / 2 - narrow / 2, -SEPARATION / 2 + narrow / 2)
    right = (SEPARATION / 2 - wide / 2, SEPARATION / 2 + wide / 2)
    original = aperture([left, right], 400)
    mirrored = (-original[0][::-1], original[1][::-1])
    y, s = detector(PIXELS, PITCH, DISTANCE)
    far = [np.abs(far_field(s, *a, WAVELENGTH)) ** 2 for a in (original, mirrored)]
    near = [
        np.abs(field_at(y, DISTANCE, *a, WAVELENGTH)) ** 2 for a in (original, mirrored)
    ]
    far_gap = float(np.max(np.abs(far[0] - far[1])) / np.max(far[0]))
    near_gap = float(np.max(np.abs(near[0] - near[1])) / np.max(near[0]))
    assert far_gap < 1e-12, "the mirror image has another far-field intensity"
    experiment.table(
        "mirror-run",
        [
            ("far field", "below 1e-12" if far_gap < 1e-12 else f"{far_gap:.1e}"),
            ("on the detector at the stated distance", f"{near_gap:.1e}"),
        ],
        [("intensity", "", ""), ("largest difference, original and mirror", "", "")],
        "Two slits of unequal widths and the same slits mirrored: the largest "
        "difference between their intensities, relative to the largest intensity.",
    )
    return far_gap, near_gap


def narrow_window():
    """Exercise 1: the standard error of the width when only the central
    pixels are used."""
    _, s = detector(PIXELS, PITCH, DISTANCE)
    counts = data(np.random.default_rng(SEED))
    out = []
    for half in (1000, 400, 100):
        keep = slice(PIXELS // 2 - half, PIXELS // 2 + half)
        r = fit(
            s[keep], counts[keep], WAVELENGTH, guess=fit(s, counts, WAVELENGTH).values
        )
        out.append((2 * half, r.error("width") * 1e6, r.error("separation") * 1e6))
    return out


def fewer_photons():
    """Exercise 2: the standard errors with a tenth of the light."""
    _, s = detector(PIXELS, PITCH, DISTANCE)
    rng = np.random.default_rng(SEED)
    bright = fit(s, data(rng), WAVELENGTH)
    dim = fit(s, data(rng, expected_counts(peak=PEAK / 10)), WAVELENGTH)
    return dim.error("separation") / bright.error("separation")


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    s, counts, result = fit_run(experiment)
    experiment.figure("fig-fit", partial(draw_fit, s, counts, result))
    experiment.number("relative-tolerance", RELATIVE_TOLERANCE * 100, ".0f")
    experiment.number("chi2-dof", result.chi2 / result.dof, ".3f")
    experiment.number("dof", result.dof, "d")
    experiment.number(
        "separation-relative", result.error("separation") / SEPARATION * 100, ".3f"
    )
    experiment.number("width-relative", result.error("width") / WIDTH * 100, ".2f")

    pulls, mean_chi2 = pulls_run(experiment)
    experiment.figure("fig-pulls", partial(draw_pulls, pulls))
    experiment.number("repeats", REPEATS, "d")
    experiment.number("mean-chi2", mean_chi2, ".3f")
    bias_width, bias_separation = model_bias()
    experiment.number("bias-width", bias_width, ".2f")
    experiment.number("bias-separation", bias_separation, ".3f")

    known, free = degeneracy_run(experiment, s, counts, result)
    experiment.figure("fig-degeneracy", partial(draw_degeneracy, s, counts, result))
    experiment.number("singular-known", known, ".1e")
    experiment.number(
        "singular-free", "below 1e-8" if free < 1e-8 else f"{free:.1e}", ""
    )

    _, near_gap = mirror_run(experiment)
    experiment.number("mirror-near", near_gap, ".0e")

    rows = narrow_window()
    for pixels, width_error, separation_error in rows:
        experiment.number(f"window-{pixels}-width", width_error, ".3f")
        experiment.number(f"window-{pixels}-separation", separation_error, ".3f")
    experiment.number("dim-ratio", fewer_photons(), ".2f")
    experiment.number("sqrt-ten", np.sqrt(10), ".2f")
    experiment.number("laser-limit", 1e-9 / WAVELENGTH * SEPARATION * 1e6, ".2f")
    experiment.number("statistical", result.error("separation") * 1e6, ".3f")
    return experiment


if __name__ == "__main__":
    main(run)
