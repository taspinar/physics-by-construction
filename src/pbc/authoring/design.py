"""The colours of the site, defined once.

``site/assets/site.css`` declares these values as custom properties of the
page, and lesson code takes the figure colours from ``FIGURE_COLOURS``, so a
figure and the page around it use one palette. A test compares the stylesheet
with this module and checks the contrast of every pair that sets text or a
control against its background (WCAG 2.1: 4.5:1 for text, 3:1 for large text
and controls). ``docs/authoring.md`` ("Visual design") describes the system.
"""

from dataclasses import dataclass

TEXT_CONTRAST = 4.5
CONTROL_CONTRAST = 3.0

# The sequence of line and marker colours of a Matplotlib figure, in the order
# a figure uses them. Each is at least 3:1 against white, and the first three
# are the colours the lessons already use. Colour never tells two series apart
# alone: a figure also varies the line style or the marker (docs/authoring.md).
FIGURE_COLOURS = (
    "#00429d",  # blue
    "#93003a",  # crimson
    "#555555",  # grey
    "#8a5a00",  # ochre
    "#006b5c",  # teal
    "#6a3d9a",  # violet
)

CLAIM_TYPES = (
    "observational",
    "experimentally-supported",
    "numerically-verified",
    "formal-theorem",
)

FIGURE_STATUSES = ("measured", "calibrated", "processed", "simulated", "conceptual")


@dataclass(frozen=True)
class Label:
    """The text and background colour of one label."""

    foreground: str
    background: str


CLAIM_LABELS = {
    "observational": Label("#0b4f6c", "#e3f1f7"),
    "experimentally-supported": Label("#5b2a86", "#efe6f6"),
    "numerically-verified": Label("#00429d", "#e6edf8"),
    "formal-theorem": Label("#1d5c2e", "#e5f2e8"),
}

STATUS_LABELS = {
    "measured": Label("#7a2e00", "#fdebdc"),
    "calibrated": Label("#6a4a00", "#fbf1d3"),
    "processed": Label("#3b4252", "#eaecf0"),
    "simulated": Label("#00429d", "#e6edf8"),
    "conceptual": Label("#5a2a5a", "#f3e8f3"),
}

# The base palette of the page.
PAGE = {
    "text": "#1f2328",
    "background": "#ffffff",
    "muted": "#57606a",
    "link": "#0a58ca",
    "rule": "#767676",
    "surface": "#f6f8fa",
    "focus": "#00429d",
    "warning": "#7a4100",
    "warning-surface": "#fff8e6",
    # The navigation bar keeps the colour the theme gives it; the text and the
    # focus ring are the colours drawn on it.
    "navbar": "#517699",
    "navbar-text": "#ffffff",
}


def custom_properties() -> dict[str, str]:
    """Every colour as the custom property that site.css declares for it."""
    properties = {f"--pbc-{name}": value for name, value in PAGE.items()}
    for kind, labels in (("claim", CLAIM_LABELS), ("status", STATUS_LABELS)):
        for name, label in labels.items():
            properties[f"--pbc-{kind}-{name}-fg"] = label.foreground
            properties[f"--pbc-{kind}-{name}-bg"] = label.background
    for number, colour in enumerate(FIGURE_COLOURS, start=1):
        properties[f"--pbc-figure-{number}"] = colour
    return properties


def _channel(value: int) -> float:
    scaled = value / 255
    if scaled <= 0.03928:
        return scaled / 12.92
    return ((scaled + 0.055) / 1.055) ** 2.4


def luminance(colour: str) -> float:
    """Relative luminance of ``#rrggbb`` (WCAG 2.1)."""
    red, green, blue = (int(colour[i : i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)


def contrast_ratio(first: str, second: str) -> float:
    lighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def colour_pairs() -> list[tuple[str, str, str, float]]:
    """Every pair that sets something on a background: its name, the colour,
    the background, and the least contrast ratio it needs."""
    page = PAGE["background"]
    pairs = [
        ("text", PAGE["text"], page, TEXT_CONTRAST),
        ("muted text", PAGE["muted"], page, TEXT_CONTRAST),
        ("link", PAGE["link"], page, TEXT_CONTRAST),
        ("link on surface", PAGE["link"], PAGE["surface"], TEXT_CONTRAST),
        ("text on surface", PAGE["text"], PAGE["surface"], TEXT_CONTRAST),
        ("warning text", PAGE["warning"], PAGE["warning-surface"], TEXT_CONTRAST),
        ("text on warning", PAGE["text"], PAGE["warning-surface"], TEXT_CONTRAST),
        ("rule", PAGE["rule"], page, CONTROL_CONTRAST),
        ("focus ring", PAGE["focus"], page, CONTROL_CONTRAST),
        ("focus ring on surface", PAGE["focus"], PAGE["surface"], CONTROL_CONTRAST),
        ("navigation text", PAGE["navbar-text"], PAGE["navbar"], TEXT_CONTRAST),
        (
            "navigation focus ring",
            PAGE["navbar-text"],
            PAGE["navbar"],
            CONTROL_CONTRAST,
        ),
    ]
    for kind, labels in (("claim", CLAIM_LABELS), ("status", STATUS_LABELS)):
        for name, label in labels.items():
            pairs.append(
                (f"{kind} {name}", label.foreground, label.background, TEXT_CONTRAST)
            )
    for number, colour in enumerate(FIGURE_COLOURS, start=1):
        pairs.append((f"figure colour {number}", colour, page, CONTROL_CONTRAST))
    return pairs
