"""The experiment of the lesson "Lycopodium diffraction lab".

The far field of a round aperture from the lesson "Diffraction and imaging"
(``pbc.waves.diffraction.circular_field``), carried by Babinet's principle
to the halo of a layer of spores (``pbc.waves.halo``), against measured data
(the committed sample of the card ``lycopodium-spore-diffraction``): two
line profiles of the diffraction halo, at 632.8 nm and 405 nm, and the
diameters of the spores measured under a microscope at two magnifications.
The record does not state the unit of the profiles' coordinate or the
distance to the screen, so the experiment tests what needs neither: the
ratio of the dark-ring radii at the two wavelengths, and the spacing of the
rings within one profile. Run it as a program to write the figures and the
numbers of the page:

    uv run --locked --no-dev python -m \\
        pbc.waves.experiments.lycopodium_diffraction_lab out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from scipy.special import jn_zeros

from pbc.data import SAMPLES_DIR
from pbc.data.adapters import luma_profile_series
from pbc.data.plotting import COLOURS, add_credit, label_status
from pbc.data.reference.lycopodium import (
    MORPHOMETRY,
    SATURATED,
    WHOLE_SPORE,
    WIDTH,
    WIDTHS,
    Profile,
    bright_ring,
    centre,
    core_radius,
    dark_ring,
    diameter_column,
    ensemble,
    folded,
    load_profiles,
    read_morphometry,
    side_rings,
    summary,
    whole_spores,
)
from pbc.data.series import Series
from pbc.experiment import Experiment, main
from pbc.waves import halo

DATASET = "lycopodium-spore-diffraction"
RED = 0.6328  # um, the helium-neon laser
VIOLET = 0.405  # um, the semiconductor laser
CREDIT = (
    "Data: O. Voronkin, S. Lushchin, 'Morphometry and Optical Data of "
    "Lycopodium Spores for the Study of Diffraction and Interference', Zenodo, "
    "doi 10.5281/zenodo.15846643, CC BY 4.0; converted to UTF-8 CSV, values "
    "unchanged. Analysis: this lesson's code."
)
STYLES = {RED: (COLOURS[1], "-", "o"), VIOLET: (COLOURS[0], "--", "s")}


def nm(wavelength: float) -> str:
    """A wavelength in um as the page names it, in nm."""
    return f"{1000 * wavelength:.1f} nm"


def load_record() -> tuple[dict[float, Profile], dict[str, dict[str, np.ndarray]]]:
    """The committed sample: the two line profiles by wavelength [um], and
    the two morphometry tables by magnification."""
    directory = SAMPLES_DIR / DATASET
    tables = {
        name: read_morphometry(directory / file) for name, file in MORPHOMETRY.items()
    }
    return load_profiles(directory), tables


# The halo of the measured diameters.


def diameter_table(experiment: Experiment, tables: dict) -> dict[str, tuple]:
    """Particles, whole spores, and the mean diameter with its standard error
    at each magnification."""
    found, rows = {}, []
    for name, table in tables.items():
        spores = whole_spores(table)
        count, mean, sd, sem = summary(spores)
        found[name] = (count, mean, sd, sem)
        rows.append(
            (
                name,
                int(diameter_column(table).size),
                count,
                mean,
                sem,
                sd,
                float(spores.min()),
                float(spores.max()),
            )
        )
    experiment.table(
        "diameters",
        rows,
        columns=[
            ("magnification", "", "s"),
            ("particles", "", "d"),
            ("whole spores", "", "d"),
            ("mean d", "um", ".2f"),
            ("standard error", "um", ".2f"),
            ("sd", "um", ".2f"),
            ("smallest", "um", ".1f"),
            ("largest", "um", ".1f"),
        ],
        caption="The diameters of the circles of equal area of the particles the "
        "record measured under the microscope; whole spores are those above "
        "15 um, the rest are fragments of their walls.",
    )
    return found


def model_check(experiment: Experiment, diameters: np.ndarray) -> dict:
    """The halo built from the wavelet integral of one disk against the
    closed form 2 J1(x) / x, and the q d of its rings."""
    mean = float(diameters.mean())
    q = np.linspace(0.0, 6.0 / mean, 2001)
    built = halo.halo(q, diameters)
    closed = ensemble(q, diameters)
    one_minima, _ = halo.extrema([mean])
    minima, maxima = halo.extrema(diameters)
    zeros = jn_zeros(1, 3) / np.pi
    experiment.table(
        "rings",
        [
            (k + 1, z, mean * one_minima[k], mean * minima[k], mean * maxima[k])
            for k, z in enumerate(zeros)
        ],
        columns=[
            ("ring", "", "d"),
            ("zero of J1 / pi", "", ".4f"),
            ("one disk, dark", "", ".4f"),
            ("measured diameters, dark", "", ".4f"),
            ("measured diameters, bright", "", ".4f"),
        ],
        caption="The rings of the halo in q times the mean diameter: the zeros of "
        "the closed form for one disk, the minima of one disk built from the "
        "wavelet integral, and the minima and maxima of the halo of the whole "
        "spores at the higher magnification.",
    )
    return {
        "largest-difference": float(np.max(np.abs(built - closed))),
        "minima": minima,
        "maxima": maxima,
        "mean": mean,
        "fill": float(halo.halo(minima[0], diameters)[0]),
    }


# The two line profiles.


def profile_landmarks(profiles: dict[float, Profile]) -> dict:
    """What the profiles show without a model: their rows, steps, centres,
    and the saturated core."""
    out = {}
    for w, p in profiles.items():
        c = centre(p)
        r, luma = folded(p, c)
        out[w] = {
            "rows": int(p.x.size),
            "step": float(np.mean(np.diff(p.x))),
            "saturated": int(np.sum(p.luma >= SATURATED)),
            "centre": c,
            "core": core_radius(r, luma),
        }
    return out


def ring_table(experiment: Experiment, profiles: dict[float, Profile]) -> dict:
    """The dark ring of each profile at every smoothing width of the
    sensitivity range, and the ratio of the two radii at each width."""
    radii = {}
    for w, p in profiles.items():
        c = centre(p)
        radii[w] = np.array([dark_ring(p, width, c) for width in WIDTHS])
    ratios = radii[VIOLET] / radii[RED]
    experiment.table(
        "ring-radii",
        [
            (
                f"{width:g}" + (" (nominal)" if width == WIDTH else ""),
                radii[RED][k],
                radii[VIOLET][k],
                ratios[k],
            )
            for k, width in enumerate(WIDTHS)
        ],
        columns=[
            ("smoothing width", "unit of x", "s"),
            ("dark ring, 632.8 nm", "unit of x", ".2f"),
            ("dark ring, 405 nm", "unit of x", ".2f"),
            ("ratio 405 / 632.8", "", ".3f"),
        ],
        caption="The radius of the dark ring of the folded profile, smoothed by a "
        "moving average of each width, and the ratio of the two radii at the "
        "same width.",
    )
    return {"radii": radii, "ratios": ratios}


def side_table(experiment: Experiment, profiles: dict[float, Profile]) -> dict:
    """The dark ring on the left and on the right of the centre, apart."""
    rows, found = [], {}
    for w, p in profiles.items():
        left, right = side_rings(p)
        fold = dark_ring(p)
        found[w] = (left, right, fold)
        rows.append((nm(w), left, right, fold))
    experiment.table(
        "sides",
        rows,
        columns=[
            ("wavelength", "", "s"),
            ("lowest point, left", "unit of x", ".2f"),
            ("lowest point, right", "unit of x", ".2f"),
            ("fold of both", "unit of x", ".2f"),
        ],
        caption="The lowest point of each side of the smoothed profile near the "
        "dark ring of the fold (within 3 units of x), at the nominal width.",
    )
    return found


def order_table(
    experiment: Experiment, profiles: dict[float, Profile], minima, maxima
) -> dict:
    """The radius of the bright ring beyond the dark one over the dark ring's,
    measured at every width, against the halo's for a dark ring of order one
    and of order two."""
    rows, found = [], {}
    for w, p in profiles.items():
        c = centre(p)
        spacing = [bright_ring(p, width) / dark_ring(p, width, c) for width in WIDTHS]
        nominal = bright_ring(p) / dark_ring(p, WIDTH, c)
        found[w] = (nominal, min(spacing), max(spacing))
        rows.append((f"measured, {nm(w)}", nominal, min(spacing), max(spacing)))
    for k in (0, 1):
        value = float(maxima[k] / minima[k])
        found[f"order {k + 1}"] = value
        rows.append((f"halo, dark ring of order {k + 1}", value, value, value))
    experiment.table(
        "ring-order",
        rows,
        columns=[
            ("", "", "s"),
            ("bright / dark", "", ".2f"),
            ("lowest over widths", "", ".2f"),
            ("highest over widths", "", ".2f"),
        ],
        caption="The radius of the next bright ring over that of the dark ring: "
        "measured at the nominal width and over the sensitivity range, and for the "
        "halo of the measured diameters if the dark ring is its first or its "
        "second minimum.",
    )
    return found


def distance_table(
    experiment: Experiment, radii: dict[float, float], minima, mean: float
) -> dict:
    """The distance to the screen that the microscope's diameters imply for
    each wavelength and each order of the dark ring, in the unit of x."""
    rows, found = [], {}
    for k in (0, 1):
        distances = [
            halo.screen_distance(radii[w], minima[k], w) for w in (RED, VIOLET)
        ]
        found[k + 1] = distances
        rows.append((k + 1, mean * minima[k], *distances))
    experiment.table(
        "screen-distance",
        rows,
        columns=[
            ("order of the dark ring", "", "d"),
            ("q times mean d", "", ".3f"),
            ("distance from 632.8 nm", "unit of x", ".0f"),
            ("distance from 405 nm", "unit of x", ".0f"),
        ],
        caption="The distance to a flat screen at which the halo of the measured "
        "diameters puts its dark ring at the measured radius, for each order. Both "
        "columns use the same two radii as the ratio test.",
    )
    return found


# The figures.


def draw_profiles(
    profiles: dict[float, Profile],
    radii: dict[float, float],
    ranges: dict[float, tuple[float, float]],
) -> Figure:
    """The two measured line profiles about their centres, the saturation
    level, and the dark ring of the fold on both sides: its radius at the
    nominal smoothing width, and the range of its radius over the widths of
    the sensitivity range (an analysis sensitivity, not a statistical error)."""
    fig, ax = plt.subplots(figsize=(5.6, 3.2), constrained_layout=True)
    for w, p in profiles.items():
        colour, ls, _ = STYLES[w]
        series = luma_profile_series(p)
        ax.plot(
            series.x - centre(p),
            series.y,
            color=colour,
            ls=ls,
            lw=0.7,
            # The trace is speckle from sample to sample: without antialiasing
            # its PNG is a third smaller and looks the same at screen size.
            antialiased=False,
            label=f"{nm(w)}, measured [{series.status}]",
        )
        low, high = ranges[w]
        for sign in (-1, 1):
            ax.axvline(sign * radii[w], color=colour, ls=":", lw=1.0)
            ax.axvspan(
                sign * low,
                sign * high,
                color=colour,
                alpha=0.2,
                lw=0,
            )
    ax.axhline(
        SATURATED, color="0.35", lw=0.8, label=f"saturated: luma {SATURATED:.0f} and up"
    )
    ax.set_xlim(-45, 45)
    ax.set_ylim(0, 300)
    ax.set_xlabel("x minus the centre [unit of the record, not stated]")
    ax.set_ylabel("luma [0-255, camera brightness]")
    ax.set_title(
        "The two line profiles; dotted: the dark ring of the fold;\n"
        "band: its range over the smoothing widths, a sensitivity, not an error",
        fontsize=9,
    )
    ax.legend(fontsize=7, loc="upper right")
    add_credit(fig, CREDIT)
    label_status(fig, "processed")
    return fig


def draw_diameters(tables: dict) -> Figure:
    """Histograms of the diameters of whole spores at both magnifications."""
    fig, ax = plt.subplots(figsize=(5.4, 2.8), constrained_layout=True)
    bins = np.arange(15.0, 52.0, 1.5)
    for (name, table), colour, ls in zip(
        tables.items(), (COLOURS[2], COLOURS[3]), ("-", "--"), strict=True
    ):
        spores = whole_spores(table)
        ax.hist(
            spores,
            bins=bins,
            density=True,
            histtype="step",
            color=colour,
            ls=ls,
            lw=1.3,
            label=f"{name}, {spores.size} whole spores, measured [processed]",
        )
    ax.set_xlabel("diameter of the circle of equal area d [um]")
    ax.set_ylabel("fraction per um [1/um]")
    ax.set_title("Microscope diameters of whole spores (d > 15 um)", fontsize=10)
    ax.set_ylim(0, 0.3)
    ax.legend(fontsize=7, loc="upper right")
    add_credit(fig, CREDIT)
    label_status(fig, "processed")
    return fig


def draw_halo_model(diameters: np.ndarray, minima) -> Figure:
    """The halo of one disk of the mean diameter and of the measured
    diameters against q times the mean diameter, on a log scale."""
    mean = float(diameters.mean())
    u = np.linspace(0.0, 4.0, 801)
    one = halo.halo(u / mean, [mean])
    many = halo.halo(u / mean, diameters)
    fig, ax = plt.subplots(figsize=(5.4, 3.0), constrained_layout=True)
    ax.plot(
        u,
        one,
        color=COLOURS[4],
        ls=":",
        lw=1.3,
        label="one disk of the mean diameter (Airy) [simulated]",
    )
    ax.plot(
        u,
        many,
        color=COLOURS[0],
        ls="--",
        lw=1.3,
        label=f"halo of the {diameters.size} measured diameters [simulated]",
    )
    ax.plot(
        mean * minima,
        halo.halo(minima, diameters),
        ls="none",
        marker="v",
        ms=6,
        color=COLOURS[0],
        label="its dark rings",
    )
    ax.set_yscale("log")
    # Room above the curves for the legend.
    ax.set_ylim(1e-5, 10)
    ax.set_xlim(0, 4)
    ax.set_xlabel("q times the mean diameter, d sin(theta) / lambda [1]")
    ax.set_ylabel("intensity / centre [1]")
    ax.set_title("The halo of the measured diameters (log scale)", fontsize=10)
    ax.legend(fontsize=7, loc="upper right")
    add_credit(fig, CREDIT)
    label_status(fig, "simulated")
    return fig


def draw_scaling(
    profiles: dict[float, Profile], radii: dict[float, np.ndarray], predicted: float
) -> Figure:
    """The folded profiles on radius over wavelength with their dark rings;
    the ratio of the radii at each width against the prediction set by the
    two wavelengths alone, and its residual."""
    fig = plt.figure(figsize=(6.0, 3.6), constrained_layout=True)
    grid = fig.add_gridspec(2, 2, width_ratios=[1.35, 1.0], height_ratios=[1.3, 1.0])
    ax_fold = fig.add_subplot(grid[:, 0])
    ax_ratio = fig.add_subplot(grid[0, 1])
    ax_res = fig.add_subplot(grid[1, 1], sharex=ax_ratio)
    nominal = WIDTHS.index(WIDTH)
    for w, p in profiles.items():
        colour, ls, _ = STYLES[w]
        r, luma = folded(p, centre(p))
        fold = Series(
            x=r,
            y=luma,
            artifact="processed-measured",
            x_name="radius",
            x_unit="unit of x",
            y_name="luma",
            y_unit="0-255",
            steps=("folded about the centre of symmetry",),
        )
        # The moving average of the analysis: WIDTH in x, an odd count of samples.
        smoothed = fold.smooth(max(3, round(WIDTH / (r[1] - r[0])) | 1))
        keep = r / w <= 60
        ax_fold.plot(
            r[keep] / w,
            smoothed.y[keep],
            color=colour,
            ls=ls,
            lw=1.1,
            label=f"{nm(w)}, folded, moving average {WIDTH:g} [{smoothed.status}]",
        )
        ax_fold.axvline(radii[w][nominal] / w, color=colour, ls=":", lw=1.0)
    ax_fold.set_xlim(0, 60)
    ax_fold.set_ylim(0, 300)
    ax_fold.set_xlabel("radius / wavelength [unit of x per um]")
    ax_fold.set_ylabel("luma [0-255, camera brightness]")
    ax_fold.set_title("Folded profiles; dotted: dark rings", fontsize=10)
    ax_fold.legend(fontsize=6.5, loc="upper right")

    widths = np.array(WIDTHS)
    ratios = radii[VIOLET] / radii[RED]
    ends = np.array([0.3, 2.2])
    ax_ratio.plot(
        ends,
        [predicted, predicted],
        color="0.2",
        ls="--",
        lw=1.1,
        label="prediction: 405 / 632.8, no fit",
    )
    ax_ratio.plot(
        widths,
        ratios,
        ls="none",
        marker="o",
        ms=5,
        color=COLOURS[2],
        label="measured ratio [processed]",
    )
    ax_ratio.set_xlim(*ends)
    ax_ratio.set_ylim(0.58, 0.72)
    ax_ratio.set_ylabel("ratio [1]")
    ax_ratio.set_title("Ratio r(405) / r(632.8)", fontsize=10)
    ax_ratio.legend(fontsize=6.5, loc="lower right")
    ax_ratio.tick_params(labelbottom=False)
    ax_res.axhline(0, color="0.4", lw=0.8)
    ax_res.plot(
        widths,
        ratios - predicted,
        ls="-",
        lw=0.6,
        marker="o",
        ms=4,
        color=COLOURS[2],
        label="measured minus predicted",
    )
    ax_res.set_ylim(-0.04, 0.06)
    ax_res.set_xlabel("smoothing width [unit of x]")
    ax_res.set_ylabel("residual [1]")
    ax_res.set_title("Residual of the ratio", fontsize=10)
    ax_res.legend(fontsize=6.5, loc="lower right")
    add_credit(fig, CREDIT)
    label_status(fig, "processed")
    return fig


# The exercises.


def tabletop_exercise(radius: float, minima, mean: float) -> None:
    """Exercise 1: the diameter the red ring would give if x were in mm and
    the screen 0.5 m away."""
    distance = 500.0  # mm, assumed
    sin_theta = np.sin(np.arctan(radius / distance))
    q = sin_theta / RED
    print(f"sin(theta) of the ring: {sin_theta:.4f}")
    for k in (0, 1):
        print(f"if it is dark ring {k + 1}: d = {mean * minima[k] / q:.1f} um")


def green_exercise(radius: float, q: float) -> None:
    """Exercise 2: the dark ring of a green laser in the same setup."""
    green = 0.532  # um
    ratio = halo.radius_ratio(q, green, RED)
    print(f"ratio of the radii: {ratio:.4f}")
    print(f"dark ring at 532 nm: {radius * ratio:.2f} units of x")


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    profiles, tables = load_record()

    found = diameter_table(experiment, tables)
    for name, (_, mean, _, sem) in found.items():
        experiment.number(f"{name}-mean", mean, ".2f")
        experiment.number(f"{name}-sem", sem, ".2f")
    experiment.number("x160-count", found["x160"][0])
    gap = found["x80"][1] - found["x160"][1]
    experiment.number(
        "mean-gap-sigma", gap / np.hypot(found["x80"][3], found["x160"][3]), ".1f"
    )
    experiment.number("whole-spore", WHOLE_SPORE, ".0f")
    experiment.number("spread", 100 * found["x160"][2] / found["x160"][1], ".0f")

    diameters = whole_spores(tables["x160"])
    check = model_check(experiment, diameters)
    minima, maxima, mean = check["minima"], check["maxima"], check["mean"]
    experiment.number("model-millionths", 1e6 * check["largest-difference"], ".1f")
    experiment.number("model-first", mean * minima[0], ".3f")
    experiment.number("model-second", mean * minima[1], ".3f")
    experiment.number("airy-first", jn_zeros(1, 1)[0] / np.pi, ".3f")
    experiment.number("fill", 100 * check["fill"], ".1f")

    experiment.number("red-nm", 1000 * RED, ".1f")
    experiment.number("violet-nm", 1000 * VIOLET, ".0f")

    landmarks = profile_landmarks(profiles)
    for w, key in ((RED, "red"), (VIOLET, "violet")):
        experiment.number(f"{key}-rows", landmarks[w]["rows"], ",d")
        experiment.number(f"{key}-step", landmarks[w]["step"], ".4f")
        experiment.number(f"{key}-saturated", landmarks[w]["saturated"])
        experiment.number(f"{key}-centre", landmarks[w]["centre"], ".3f")
        experiment.number(f"{key}-core", landmarks[w]["core"], ".1f")
    experiment.number("saturated", SATURATED, ".0f")
    experiment.number("width-low", min(WIDTHS), "g")
    experiment.number("width-high", max(WIDTHS), "g")

    rings = ring_table(experiment, profiles)
    nominal = WIDTHS.index(WIDTH)
    radius = {w: float(rings["radii"][w][nominal]) for w in (RED, VIOLET)}
    half = {
        w: float(np.ptp(rings["radii"][w]) / 2) for w in (RED, VIOLET)
    }  # half the range over the widths
    for w, key in ((RED, "red"), (VIOLET, "violet")):
        experiment.number(f"{key}-ring", radius[w], ".2f")
        experiment.number(f"{key}-ring-range", half[w], ".2f")
    ratio = radius[VIOLET] / radius[RED]
    propagated = ratio * np.hypot(
        half[VIOLET] / radius[VIOLET], half[RED] / radius[RED]
    )
    ratios = rings["ratios"]
    predicted = halo.radius_ratio(minima[0], VIOLET, RED)
    experiment.number("ratio", ratio, ".3f")
    experiment.number("ratio-range", propagated, ".3f")
    experiment.number("ratio-low", ratios.min(), ".3f")
    experiment.number("ratio-high", ratios.max(), ".3f")
    experiment.number("ratio-half-range", np.ptp(ratios) / 2, ".3f")
    experiment.number("predicted", predicted, ".4f")
    experiment.number(
        "flat-screen-shift",
        abs(predicted - halo.radius_ratio(minima[1], VIOLET, RED)),
        ".4f",
    )
    experiment.number("excess-low", 100 * (ratios.min() / predicted - 1), ".1f")
    experiment.number("excess-high", 100 * (ratios.max() / predicted - 1), ".0f")

    sides = side_table(experiment, profiles)
    experiment.number("red-left", sides[RED][0], ".2f")
    experiment.number("red-right", sides[RED][1], ".2f")
    experiment.number("violet-left", sides[VIOLET][0], ".2f")
    experiment.number("violet-right", sides[VIOLET][1], ".2f")

    order = order_table(experiment, profiles, minima, maxima)
    experiment.number("spacing-red", order[RED][0], ".2f")
    experiment.number("spacing-violet", order[VIOLET][0], ".2f")
    experiment.number("spacing-order-1", order["order 1"], ".2f")
    experiment.number("spacing-order-2", order["order 2"], ".2f")
    low = min(order[w][1] for w in (RED, VIOLET))
    high = max(order[w][2] for w in (RED, VIOLET))
    experiment.number("spacing-low", low, ".2f")
    experiment.number("spacing-high", high, ".2f")

    distances = distance_table(experiment, radius, minima, mean)
    experiment.number("distance-1", distances[1][0], ".0f")
    experiment.number("distance-2", distances[2][0], ".0f")
    experiment.number("sin-1", minima[0] * RED, ".3f")
    experiment.number("sin-2", minima[1] * RED, ".3f")

    spans = {
        w: (float(rings["radii"][w].min()), float(rings["radii"][w].max()))
        for w in (RED, VIOLET)
    }
    experiment.figure("fig-profiles", partial(draw_profiles, profiles, radius, spans))
    experiment.figure("fig-diameters", partial(draw_diameters, tables))
    experiment.figure("fig-halo-model", partial(draw_halo_model, diameters, minima))
    experiment.figure(
        "fig-scaling", partial(draw_scaling, profiles, rings["radii"], predicted)
    )

    with experiment.capture("tabletop-exercise"):
        tabletop_exercise(radius[RED], minima, mean)
    with experiment.capture("green-exercise"):
        green_exercise(radius[RED], minima[0])
    return experiment


if __name__ == "__main__":
    main(run)
