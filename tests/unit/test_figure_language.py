"""The figure language (F170, revised by F171): its rules hold on the six
sample figures and on the figures the rollout opted in, at desktop and phone
widths down to 320 CSS px, and a figure that does not opt in is left as it
was."""

import importlib

import matplotlib
import matplotlib.pyplot as plt
import pytest

from pbc.authoring.design import (
    CONTROL_CONTRAST,
    FIGURE_COLOURS,
    PAGE,
    TEXT_CONTRAST,
    contrast_ratio,
)
from pbc.data.plotting import COLOURS
from pbc.experiment import FIGURE_SETTINGS, encode
from pbc.figure_audit import (
    PHONE_WIDTH,
    PIXELS_PER_POINT,
    ROLLOUT,
    SMALL_PHONE_WIDTH,
    measure,
    rollout_figures,
    sample_figures,
)
from pbc.figure_language import (
    INK,
    MIN_TEXT,
    MUTED,
    RULE,
    SEQUENTIAL,
    TEXT,
    TICKS,
    WIDTH,
    cased,
    figure_style,
    finish,
    isoline_colours,
    line_colours,
)

# The tight crop of a saved figure (bbox_inches="tight") widens it by up to
# this much beyond WIDTH: 405 px for 394.
CROP = 1.03
# The least size of type on a phone, in CSS px: MIN_TEXT at the widest
# cropped figure, scaled to the phone's width of a figure: 11.07 at 375 CSS
# px (PHONE_WIDTH, 306 CSS px, measured on a built page) and 9.08 at 320 CSS
# px (SMALL_PHONE_WIDTH, 251 CSS px), docs/authoring.md.
PHONE_TEXT = MIN_TEXT * PIXELS_PER_POINT * PHONE_WIDTH / (CROP * WIDTH * 96)
SMALL_PHONE_TEXT = MIN_TEXT * PIXELS_PER_POINT * SMALL_PHONE_WIDTH / (CROP * WIDTH * 96)
# The owner's floor for the revised language (Issue #544): 9 CSS px at 320.
SMALL_PHONE_FLOOR = 9.0


@pytest.fixture(scope="module")
def samples():
    return {label: (kind, draw) for kind, label, draw in sample_figures()}


@pytest.fixture(scope="module")
def audits(samples):
    return {label: measure(draw) for label, (_, draw) in samples.items()}


@pytest.fixture(scope="module")
def rollout():
    return {(module, label): draw for module, label, draw in rollout_figures()}


@pytest.fixture(scope="module")
def rollout_audits(rollout):
    return {key: measure(draw) for key, draw in rollout.items()}


def test_the_six_classes_are_sampled_once_each(samples):
    kinds = sorted(kind for kind, _ in samples.values())
    assert kinds == sorted(
        [
            "trajectory",
            "multi-series numerical comparison",
            "phase space",
            "convergence, log-log",
            "field",
            "measured against model, residuals",
        ]
    )


def _canvas_width(draw):
    fig = draw()
    try:
        return fig.get_figwidth()
    finally:
        plt.close(fig)


def _assert_the_one_width(name, draw, audit):
    # Every figure is drawn on the language's canvas; bbox_inches="tight"
    # crops it, by a few pixels for a line plot and more for equal-aspect
    # panels narrower than the canvas, and widens it by no more than CROP.
    assert _canvas_width(draw) == WIDTH, name
    assert audit.natural_width <= CROP * WIDTH * 96, name


def test_every_sample_has_the_one_width(samples, audits):
    for label, (_, draw) in samples.items():
        _assert_the_one_width(label, draw, audits[label])
    lines = [a for label, a in audits.items() if label != "fig-plate-temperature"]
    for audit in lines:
        assert abs(audit.natural_width - WIDTH * 96) <= 0.05 * WIDTH * 96


def test_the_phone_minimum_is_the_documented_one():
    assert round(PHONE_TEXT, 2) == 11.07
    assert round(SMALL_PHONE_TEXT, 2) == 9.08
    assert SMALL_PHONE_TEXT >= SMALL_PHONE_FLOOR


def _assert_legible(name, audit):
    assert audit.smallest_text >= MIN_TEXT, (name, audit.smallest_text)
    assert audit.smallest_phone_px >= PHONE_TEXT, (name, audit)
    assert audit.smallest_small_phone_px >= SMALL_PHONE_FLOOR, (name, audit)
    assert audit.smallest_desktop_px >= 14.5, (name, audit)


def test_no_text_of_a_sample_is_smaller_than_the_least_size(audits):
    for label, audit in audits.items():
        _assert_legible(label, audit)


def test_the_rollout_is_the_approved_list_and_opts_in():
    # List A of the plan (28 figures), and phase 2c: list B (4) and the
    # figures of the three tested types that passed the gate (84); none of
    # them a sample, each drawn by a draw_ function that opts in
    # (figure_style, finish). The four that failed the gate stay out.
    import inspect

    from pbc.figure_audit import ROLLOUT_LIST_B_AND_TYPES, SAMPLES

    assert len(ROLLOUT) == len(set(ROLLOUT)) == 28 + 88
    assert len(ROLLOUT_LIST_B_AND_TYPES) == 88
    labels = {label for _, label in ROLLOUT_LIST_B_AND_TYPES}
    assert {"fig-drift", "fig-solar-system", "fig-limit-cycle"} <= labels
    assert "fig-airy-rayleigh" in labels
    left_out = {
        ("pbc.mechanics.experiments.energy_conservation", "fig-pendulum-energy"),
        (
            "pbc.mechanics.experiments.proving_what_the_simulation_showed",
            "fig-proved-energy-growth",
        ),
        ("pbc.materials.experiments.elasticity_and_deformation", "fig-plate"),
        ("pbc.astrophysics.experiments.three_body_problem", "fig-pythagorean"),
    }
    assert not left_out & set(ROLLOUT)
    assert not {label for _, label in ROLLOUT} & {label for *_, label in SAMPLES}
    # The one figure whose draw function lives outside its lesson's module.
    drawn_in = {"fig-tsunami-benchmarks": "pbc.fluids.tsunami_benchmarks"}
    for module, label in ROLLOUT:
        source = inspect.getsource(importlib.import_module(drawn_in.get(label, module)))
        assert "figure_style()" in source and "finish(" in source, (module, label)


def test_every_figure_of_the_rollout_meets_the_language(rollout, rollout_audits):
    for (module, label), audit in rollout_audits.items():
        name = f"{module}:{label}"
        _assert_the_one_width(name, rollout[(module, label)], audit)
        assert abs(audit.natural_width - WIDTH * 96) <= 0.05 * WIDTH * 96, name
        _assert_legible(name, audit)
        if audit.least_line_contrast is not None:
            assert audit.least_line_contrast >= CONTROL_CONTRAST, name
        # At most three entries in a legend inside the axes; more go under
        # the plot, a figure legend.
        assert audit.axes_legend_entries <= 3, name


@pytest.mark.parametrize(
    "key",
    ROLLOUT,
    ids=[f"{module.rsplit('.', 1)[1]}:{label}" for module, label in ROLLOUT],
)
def test_every_figure_of_the_rollout_is_the_same_bytes_on_every_draw(rollout, key):
    assert len({encode(rollout[key]) for _ in range(2)}) == 1


def test_every_line_of_a_sample_has_three_to_one_against_the_plate(audits):
    for label, audit in audits.items():
        if audit.least_line_contrast is not None:
            assert audit.least_line_contrast >= CONTROL_CONTRAST, label


def test_the_isolines_of_the_field_are_audited_against_the_field(audits):
    # The field draws its isotherms with contour(), a collection and not a
    # Line2D: the audit measures them against the rendered field beneath.
    audit = audits["fig-plate-temperature"]
    assert audit.least_line_contrast is not None
    assert audit.least_line_contrast >= CONTROL_CONTRAST


def test_every_sample_of_the_isotherms_counts_their_ends_included(samples):
    # The isotherms run to the bottom corners, where the hot edge (100
    # degrees C) meets the cold ones (20): no stroke colour has 3:1 against
    # both. Each carries a casing of the other colour, and every sample, the
    # ends too, has 3:1 with the line or its casing.
    from pbc.figure_audit import _stroke_contrasts

    _, draw = samples["fig-plate-temperature"]
    fig = draw()
    try:
        fig.canvas.draw()
        counted = 0
        for ax in fig.axes:
            for collection in ax.collections:
                for contrast in _stroke_contrasts(ax, collection, PAGE["plate"]):
                    assert contrast >= CONTROL_CONTRAST
                    counted += 1
        assert counted > 0
    finally:
        plt.close(fig)


def test_the_isotherms_are_the_contours_of_the_whole_displayed_field(samples):
    # The contour source is the image's whole array, its boundary rows and
    # columns included: each drawn isotherm ends where the contour of the
    # displayed field at its level ends (the label's gap lies at its top).
    import numpy as np

    _, draw = samples["fig-plate-temperature"]
    fig = draw()
    scratch = plt.figure()
    try:
        for ax in fig.axes:
            if not ax.images:
                continue
            image = ax.images[0]
            field = np.asarray(image.get_array())
            extent = image.get_extent()
            cell = (extent[1] - extent[0]) / field.shape[1]
            sets = [c for c in ax.collections if hasattr(c, "levels")]
            assert [float(c.levels[0]) for c in sets] == [30.0, 40.0, 60.0, 80.0]
            for drawn in sets:
                expected = scratch.add_subplot().contour(
                    field, levels=drawn.levels, origin="lower", extent=extent
                )
                ends = [
                    np.vstack([p.vertices for p in c.get_paths()])
                    for c in (drawn, expected)
                ]
                # left, right, and bottom: the ends of the arch; its top holds
                # the label's gap
                lows = [e.min(axis=0) for e in ends]
                highs = [e.max(axis=0) for e in ends]
                assert lows[0] == pytest.approx(lows[1], abs=1e-9)
                assert highs[0][0] == pytest.approx(highs[1][0], abs=1e-9)
                # the ends lie between the boundary nodes and the next ones
                assert ends[0][:, 0].min() < extent[0] + 1.5 * cell
                assert ends[0][:, 0].max() > extent[1] - 1.5 * cell
                assert ends[0][:, 1].min() < extent[2] + 1.5 * cell
    finally:
        plt.close(fig)
        plt.close(scratch)


def _field_with_isolines(colour):
    import numpy as np

    def draw():
        fig, ax = plt.subplots(figsize=(WIDTH, 3.0))
        _, x = np.mgrid[0:1:41j, 0:1:41j]
        field = 20.0 + 80.0 * x
        extent = (0.0, 1.0, 0.0, 1.0)
        ax.imshow(field, origin="lower", extent=extent, cmap=SEQUENTIAL)
        ax.contour(field, levels=[85.0], origin="lower", extent=extent, colors=colour)
        return fig

    return draw


def test_the_audit_measures_an_isoline_against_the_field_beneath():
    # At 85 degrees on a map from 20 to 100 the field is bright yellow-green:
    # white on it is below 3:1, ink is far above.
    white = measure(_field_with_isolines("white"))
    ink = measure(_field_with_isolines(INK))
    assert white.least_line_contrast < CONTROL_CONTRAST
    assert ink.least_line_contrast >= CONTROL_CONTRAST


def test_a_cased_isoline_is_measured_by_its_line_or_its_casing():
    # White on bright yellow-green is below 3:1; with an ink casing the
    # stroke has its edge, and the audit counts the casing.
    def draw():
        fig = _field_with_isolines("white")()
        ax = fig.axes[0]
        for collection in ax.collections:
            collection.set_path_effects(cased(PAGE["plate"]))
        return fig

    assert measure(draw).least_line_contrast >= CONTROL_CONTRAST
    assert cased(INK)[0]._gc["foreground"] == PAGE["plate"]


def test_an_isoline_takes_the_colour_with_more_contrast_on_its_level():
    colours = isoline_colours([30, 40, 60, 80], 20.0, 100.0)
    assert colours == [PAGE["plate"], PAGE["plate"], INK, INK]
    cmap = matplotlib.colormaps[SEQUENTIAL]
    for level, colour in zip([30, 40, 60, 80], colours, strict=True):
        under = matplotlib.colors.to_hex(cmap((level - 20.0) / 80.0))
        # the labels take the same colour: text contrast, not only 3:1
        assert contrast_ratio(colour, under) >= TEXT_CONTRAST


def test_the_text_colours_have_the_contrast_of_text_on_the_plate():
    plate = PAGE["plate"]
    assert contrast_ratio(INK, plate) >= TEXT_CONTRAST
    assert contrast_ratio(MUTED, plate) >= TEXT_CONTRAST
    assert contrast_ratio(RULE, plate) >= CONTROL_CONTRAST


def test_a_line_never_takes_a_palette_colour_below_three_to_one():
    assert line_colours(FIGURE_COLOURS) == FIGURE_COLOURS
    # Okabe-Ito's orange and sky blue are paler than 3:1 on white.
    assert line_colours(COLOURS) == COLOURS[:4]


def test_the_field_is_drawn_with_the_sequential_map(audits):
    # The plate's temperatures are a magnitude: sequential, never diverging.
    assert audits["fig-plate-temperature"].colour_maps == (SEQUENTIAL,)


def test_a_legend_holds_no_more_than_three_entries(audits):
    for label, audit in audits.items():
        assert audit.legend_entries <= 3, label


@pytest.mark.parametrize(
    "label",
    [
        "fig-orbit-four-methods",
        "fig-orbit-thousand",
        "fig-phase-blob",
        "fig-heat-convergence",
        "fig-plate-temperature",
        "fig-impedance-fit",
    ],
)
def test_every_sample_is_the_same_bytes_on_every_draw(samples, label):
    _, draw = samples[label]
    assert len({encode(draw) for _ in range(3)}) == 1


def _three_series():
    fig, ax = plt.subplots(figsize=(WIDTH, 3.0))
    for k in range(3):
        ax.plot([0, 1, 2], [k, k + 1, k], label=f"series {k}")
    ax.legend()
    return fig


def _styled_three_series():
    with figure_style():
        fig = _three_series()
    return finish(fig)


def test_tick_labels_made_when_the_figure_is_saved_keep_the_style():
    # Matplotlib makes most tick labels only when it draws the figure, which
    # encode does after the styled function has returned and its settings
    # are gone: the labels must still take the style.
    with matplotlib.rc_context():
        matplotlib.rcdefaults()
        matplotlib.rcParams.update(FIGURE_SETTINGS)
        fig = _styled_three_series()
        fig.canvas.draw()
        ax = fig.axes[0]
        labels = ax.get_xticklabels() + ax.get_yticklabels()
        assert labels
        for text in labels:
            assert text.get_fontsize() == TEXT["tick"]
            assert matplotlib.colors.to_hex(text.get_color()) == MUTED
        plt.close(fig)


def test_a_figure_that_does_not_opt_in_is_drawn_as_before():
    plain = encode(_three_series)
    encode(_styled_three_series)
    assert encode(_three_series) == plain
    assert matplotlib.rcParams["font.size"] == matplotlib.rcParamsDefault["font.size"]


def test_the_audit_converts_points_to_css_pixels_at_both_widths():
    def one_label():
        fig, ax = plt.subplots(figsize=(WIDTH, 3.0))
        ax.set_axis_off()
        ax.text(0.5, 0.5, "ten points", fontsize=10.0)
        return fig

    audit = measure(one_label)
    assert audit.smallest_text == 10.0
    assert audit.smallest_desktop_px == pytest.approx(10.0 * PIXELS_PER_POINT)
    assert audit.smallest_phone_px == pytest.approx(
        10.0 * PIXELS_PER_POINT * PHONE_WIDTH / audit.natural_width
    )


def test_an_excerpt_of_a_sample_points_to_its_own_module(samples):
    # The page shows the draw_ functions with excerpt(), which reads the file
    # and the lines of the function: they must be the lesson's own.
    import inspect

    from pbc.figure_audit import SAMPLES

    for _, module, label in SAMPLES:
        draw = samples[label][1]
        function = getattr(draw, "func", draw)
        assert inspect.getsourcefile(function).endswith(
            module.replace(".", "/") + ".py"
        ), label


def test_an_axis_the_language_places_shows_at_most_five_ticks(samples, rollout):
    # finish() gives a linear axis whose ticks Matplotlib places itself at
    # most TICKS ticks (MaxNLocator); an axis with its own ticks keeps them.
    from matplotlib.ticker import MaxNLocator

    draws = [draw for _, draw in samples.values()] + list(rollout.values())
    placed = 0
    for draw in draws:
        with matplotlib.rc_context():
            matplotlib.rcdefaults()
            matplotlib.rcParams.update(FIGURE_SETTINGS)
            fig = draw()
            try:
                fig.canvas.draw()
                for ax in fig.axes:
                    for axis, limits in (
                        (ax.xaxis, ax.get_xlim()),
                        (ax.yaxis, ax.get_ylim()),
                    ):
                        if not isinstance(axis.get_major_locator(), MaxNLocator):
                            continue
                        low, high = sorted(limits)
                        shown = [
                            t
                            for t in axis.get_majorticklocs()
                            if low - 1e-12 <= t <= high + 1e-12
                        ]
                        assert len(shown) <= TICKS, (ax.get_xlabel(), shown)
                        placed += 1
            finally:
                plt.close(fig)
    assert placed > 0


def test_finish_keeps_a_tick_set_of_the_figure_and_a_log_axis():
    from matplotlib.ticker import FixedLocator, LogLocator

    with figure_style():
        fig, (lin, log) = plt.subplots(2, 1, figsize=(WIDTH, 3.0))
        lin.plot([0, 1, 2, 3], [0, 1, 4, 9])
        lin.set_xticks([0, 1, 2, 3])
        log.loglog([1, 10, 100], [1, 10, 100])
    finish(fig)
    try:
        assert isinstance(lin.xaxis.get_major_locator(), FixedLocator)
        assert isinstance(log.xaxis.get_major_locator(), LogLocator)
    finally:
        plt.close(fig)
