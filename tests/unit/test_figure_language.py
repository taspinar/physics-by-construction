"""The figure language of the pilot (F170): its rules hold on the six sample
figures, at desktop and phone widths, and a figure that does not opt in is
left as it was."""

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
from pbc.figure_audit import PHONE_WIDTH, PIXELS_PER_POINT, measure, sample_figures
from pbc.figure_language import (
    INK,
    MIN_TEXT,
    MUTED,
    RULE,
    SEQUENTIAL,
    TEXT,
    WIDTH,
    figure_style,
    finish,
    line_colours,
)

# The least size of type on a phone, in CSS px: MIN_TEXT at WIDTH, scaled to
# the phone's width of a figure.
PHONE_TEXT = 7.0


@pytest.fixture(scope="module")
def samples():
    return {label: (kind, draw) for kind, label, draw in sample_figures()}


@pytest.fixture(scope="module")
def audits(samples):
    return {label: measure(draw) for label, (_, draw) in samples.items()}


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


def test_every_sample_has_the_one_width(audits):
    # bbox_inches="tight" crops a few pixels; the width is the language's.
    for label, audit in audits.items():
        assert abs(audit.natural_width - WIDTH * 96) <= 0.05 * WIDTH * 96, label


def test_no_text_of_a_sample_is_smaller_than_the_least_size(audits):
    for label, audit in audits.items():
        assert audit.smallest_text >= MIN_TEXT, (label, audit.smallest_text)
        assert audit.smallest_phone_px >= PHONE_TEXT, (label, audit)
        assert audit.smallest_desktop_px >= 12.0, (label, audit)


def test_every_line_of_a_sample_has_three_to_one_against_the_plate(audits):
    for label, audit in audits.items():
        if audit.least_line_contrast is not None:
            assert audit.least_line_contrast >= CONTROL_CONTRAST, label


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
