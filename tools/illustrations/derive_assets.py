"""Derive the delivery sizes of the atlas illustrations from their masters:
the card 152 and 228 px wide (the 76 px slot at 2x and 3x) and the panel 400
and 800 px wide (the 200 px slot at 2x and 4x), all 4:3, WebP, on the page's
paper. One master per sequence; the mechanics card takes the owner's detail
crop of the same figure, since the whole is too fine at 76 px.

The hero of the home page (F158; since Issue #482 one image; since Issue
#487 the owner's double-pendulum illustration) takes the owner's master
`pbc_hero_assets/pbc-double-pendulum-hero-original.png` (1774 by 887 px,
2:1): a double pendulum at the left, a dotted trace with a dashed curve
through the middle, a ball in a glowing well at the right, on a warm white
ground. The file derived for the page blends the master over the page's
paper: the ground is keyed to the paper, and under the copy of a wide
screen (the left 47 % of the image) each pixel is lifted toward the paper
by what the text's contrast needs, so that the pendulum stays a pale
drawing instead of vanishing; the right part is whole. Its alpha channel
is the edge fade alone (zero on every edge), which is smooth and cheap,
where an alpha that followed the content cost more bytes than the colour.
Written at 1200, 1480, and 1774 px wide
(the master's own width, so nothing is upscaled), one file per width,
named by the image identifier of site/hero.yaml and the width.

Run: python derive_assets.py MASTERS_DIRECTORY [OUTPUT_DIRECTORY]
The output defaults to site/assets/atlas of the repository.
Run: python derive_assets.py --hero MASTERS_DIRECTORY [OUTPUT_DIRECTORY]
The output defaults to site/assets/hero of the repository.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

REPOSITORY = Path(__file__).resolve().parents[2]
PAPER = (250, 248, 243)

MASTERS = {
    "mechanics": "pbc_classical_mechanics_double_pendulum.webp",
    "thermodynamics": "pbc_thermodynamics_hot_cold.webp",
    "waves": "pbc_waves_optics_interference.webp",
    "electromagnetism": "pbc_electromagnetism_solenoid.webp",
    "fluids": "pbc_fluid_dynamics_vortex_street.webp",
    "quantum": "pbc_quantum_physics_wigner_cat.webp",
    "astrophysics": "pbc_astrophysics_exoplanet_transit.webp",
    "materials": "pbc_condensed_matter_acoustic.webp",
    "reasoning": "pbc_part_b_reasoning_textfree.png",
    "law-discovery": "pbc_part_b_law_discovery_textfree.png",
    "benchmarking": "pbc_part_b_benchmarking_textfree.png",
    "autonomous-research": "pbc_part_b_autonomous_research_textfree.png",
}
CARD_MASTER = {"mechanics": "pbc_classical_mechanics_atlas_card_detail.png"}
SIZES = {"card": (152, 228), "panel": (400, 800)}
# The hero image (Issue #487): its identifier in site/hero.yaml, the course
# it is named with, its master under the masters directory, and the widths
# written. The master is 2:1; its full frame is used.
HERO_IMAGE = "double-pendulum"
HERO_SEQUENCE = "mechanics"
HERO_MASTER = "pbc_hero_assets/pbc-double-pendulum-hero-original.png"
HERO_WIDTHS = (1200, 1480, 1774)
# The illustration's own ground, a warm white (the median of its light,
# low-chroma pixels), and the RGB distance over which a pixel near it is
# blended to the page's paper, so that no pink rectangle shows.
HERO_GROUND = (251, 241, 238)
HERO_KEY = 24.0
# The lift under the copy of a wide screen (D3 of the plan). The copy and
# the actions lie over the left 45 % of the image at most; up to HERO_LIFT[0]
# every pixel is lifted toward the paper so that, composited on it, its luma
# (the sRGB-weighted sum the browser blends linearly) is at least
# HERO_FLOOR, the grey whose WCAG luminance is 0.78 (the lossy encoding and
# the resampling dip a few levels below it): the muted subtext and
# the link colour keep a contrast above 4.5 against it, the headline above
# 3. The ink of a pixel (the paper's luma minus its own) is compressed by a
# power law with the exponent HERO_LIFT_GAMMA, so black keeps a ninth of its
# ink, a mid-grey a quarter to a third, and the pale haze most of it. From
# HERO_LIFT[0] to HERO_LIFT[1] the lift eases out to nothing.
HERO_LIFT = (0.47, 0.60)
HERO_FLOOR = 228.0
HERO_LIFT_GAMMA = 0.3
# The edge matte, in fractions of the width (x) and the height (y): zero
# on every edge, one inside the fades; each ramp a smoothstep.
HERO_LEFT_FADE = (0.0, 0.08)
HERO_RIGHT_FADE = (0.86, 0.985)
HERO_TOP_FADE = (0.0, 0.12)
HERO_BOTTOM_FADE = (0.88, 1.0)


def load(file: Path) -> Image.Image:
    image = Image.open(file).convert("RGBA")
    paper = Image.new("RGBA", image.size, (*PAPER, 255))
    paper.alpha_composite(image)
    image = paper.convert("RGB")
    assert abs(image.width / image.height - 4 / 3) < 0.01, (file, image.size)
    return image


def resize(image: Image.Image, width: int) -> Image.Image:
    if width > image.width:
        raise ValueError(f"a master {image.width} px wide is not upscaled to {width}")
    return image.resize((width, round(width * 3 / 4)), Image.Resampling.LANCZOS)


def derive(sequence: str, kind: str, master: Path, out: Path) -> list[Path]:
    image = load(master)
    written = []
    for width in SIZES[kind]:
        file = out / f"{sequence}-{kind}-{width}.webp"
        resize(image, width).save(file, format="WEBP", quality=88, method=6)
        written.append(file)
    return written


def main(masters: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for sequence, name in MASTERS.items():
        for kind in SIZES:
            master = CARD_MASTER.get(sequence, name) if kind == "card" else name
            derive(sequence, kind, masters / master, out)


def _smoothstep(values: np.ndarray, start: float, end: float) -> np.ndarray:
    """0 up to ``start``, 1 from ``end``, a cubic ease between them."""
    t = np.clip((values - start) / (end - start), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _luma(pixels: np.ndarray) -> np.ndarray:
    """The sRGB-weighted luma of RGB pixels, 0 to 255: linear in the
    channels, as the browser's blend over the paper is; a composite of this
    luma has at least the WCAG luminance of the grey of the same value."""
    return 0.2126 * pixels[..., 0] + 0.7152 * pixels[..., 1] + 0.0722 * pixels[..., 2]


def hero_edge_matte(width: int, height: int) -> np.ndarray:
    """The geometric part of the alpha, 0 to 1: zero on every edge, one
    inside the fades, the product of a horizontal and a vertical profile."""
    x = (np.arange(width) + 0.5) / width
    y = (np.arange(height) + 0.5) / height
    across = _smoothstep(x, *HERO_LEFT_FADE) * (1.0 - _smoothstep(x, *HERO_RIGHT_FADE))
    down = _smoothstep(y, *HERO_TOP_FADE) * (1.0 - _smoothstep(y, *HERO_BOTTOM_FADE))
    return down[:, None] * across[None, :]


def hero_lift(pixels: np.ndarray) -> np.ndarray:
    """The alpha, 0 to 1, that lifts each pixel toward the paper under the
    copy: the ink of a pixel (the paper's luma minus its own) is compressed
    to ``floor_ink * (ink / black_ink) ** gamma``, which brings black to the
    floor and leaves a pale pixel nearly whole; from HERO_LIFT[0] to
    HERO_LIFT[1] of the width the compression eases out to none."""
    width = pixels.shape[1]
    paper = _luma(np.array(PAPER, dtype=float))
    ink = np.clip(paper - _luma(pixels), 0.0, None)
    compressed = (paper - HERO_FLOOR) * (ink / paper) ** HERO_LIFT_GAMMA
    x = (np.arange(width) + 0.5) / width
    strength = 1.0 - _smoothstep(x, *HERO_LIFT)
    kept = (1.0 - strength)[None, :] * ink + strength[None, :] * compressed
    with np.errstate(divide="ignore", invalid="ignore"):
        alpha = np.where(ink > 0, kept / ink, 1.0)
    return np.clip(alpha, 0.0, 1.0)


def hero_key(pixels: np.ndarray) -> np.ndarray:
    """The alpha, 0 to 1, that keys the illustration's ground to the paper:
    zero at the ground's colour, one from HERO_KEY levels of RGB distance."""
    distance = np.sqrt(((pixels - np.array(HERO_GROUND, dtype=float)) ** 2).sum(-1))
    return _smoothstep(distance, 0.0, HERO_KEY)


def hero_image(master: Path) -> Image.Image:
    """The hero image at the master's size: its pixels blended over the
    paper by the key and the lift, with the edge matte as the alpha
    channel."""
    image = Image.open(master).convert("RGB")
    assert image.width == 2 * image.height, (master, image.size)
    pixels = np.asarray(image).astype(float)
    paper = np.array(PAPER, dtype=float)
    blend = (hero_key(pixels) * hero_lift(pixels))[..., None]
    blended = np.round(paper + blend * (pixels - paper)).astype("uint8")
    result = Image.fromarray(blended)
    alpha = hero_edge_matte(*image.size)
    result.putalpha(Image.fromarray(np.round(alpha * 255).astype("uint8")))
    return result


def hero(masters: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    image = hero_image(masters / HERO_MASTER)
    for width in HERO_WIDTHS:
        if width > image.width:
            raise ValueError(f"the master is {image.width} px wide; not upscaled")
        # Resized premultiplied, so that no colour of a transparent pixel
        # bleeds into its neighbours.
        sized = (
            image.convert("RGBa")
            .resize((width, width // 2), Image.Resampling.LANCZOS)
            .convert("RGBA")
        )
        # Lossy colour at the quality of the atlas files, lossless alpha.
        sized.save(
            out / f"{HERO_IMAGE}-{width}.webp", format="WEBP", quality=88, method=6
        )


if __name__ == "__main__":
    arguments = sys.argv[1:]
    write, kind = (hero, "hero") if arguments[:1] == ["--hero"] else (main, "atlas")
    arguments = arguments[1:] if kind == "hero" else arguments
    output = REPOSITORY / "site/assets" / kind
    write(Path(arguments[0]), Path(arguments[1]) if len(arguments) > 1 else output)
