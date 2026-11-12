"""Derive the delivery sizes of the atlas illustrations from their masters:
the card 152 and 228 px wide (the 76 px slot at 2x and 3x) and the panel 400
and 800 px wide (the 200 px slot at 2x and 4x), all 4:3, WebP, on the page's
paper. One master per sequence; the mechanics card takes the owner's detail
crop of the same figure, since the whole is too fine at 76 px.

The hero of the home page (F158; since Issue #482 one image) takes the
fluids master, the vortex street: its middle 2:1 band, mirrored so that the
flow runs from right to left with the cylinder toward the right, and faded
by an alpha matte that is zero on every edge, faint under the left third
(where the headline and the subtext stand on a wide screen) and one over
the right half, at 1200, 1800, and 2400 px wide (the master's own width, so
nothing is upscaled), one file per width, named by the image identifier of
site/hero.yaml and the width.

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
# The hero image (Issue #482): its identifier in site/hero.yaml, the sequence
# whose master it is, the widths written, and the crop of the master (left,
# top, right, bottom of the 2400 by 1800 master): the middle 2:1 band, which
# holds the computed domain (rows 468 to 1332 of the master, 14 % to 86 % of
# the band) with a paper margin above and below it.
HERO_IMAGE = "vortex-street"
HERO_SEQUENCE = "fluids"
HERO_WIDTHS = (1200, 1800, 2400)
HERO_CROP = (0, 300, 2400, 1500)
# The matte, in fractions of the mirrored image's width (x, from the left)
# and height (y, from the top). Horizontally: zero up to the domain's edge,
# a quarter at the right edge of the copy's column of a wide screen (31 % of
# the image lies under that column, D5 of the plan), one from the middle of
# the wake on; one until past the cylinder, then zero at the domain's right
# edge, over the incoming streamlines. Vertically: zero at the domain's
# edges, one 13 % of the height inside them. Each ramp is a smoothstep, so
# nowhere is there an edge.
HERO_LEFT_FADE = ((0.03, 0.31, 0.25), (0.31, 0.58, 0.75))  # (from, to, share)
HERO_RIGHT_FADE = (0.90, 0.975)
HERO_TOP_FADE = (0.14, 0.27)
HERO_BOTTOM_FADE = (0.73, 0.86)


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


def hero_matte(width: int, height: int) -> np.ndarray:
    """The alpha of the hero image, 0 to 1, as the product of a horizontal
    and a vertical profile (the fades above)."""
    x = (np.arange(width) + 0.5) / width
    y = (np.arange(height) + 0.5) / height
    across = sum(
        share * _smoothstep(x, start, end) for start, end, share in HERO_LEFT_FADE
    )
    across = across * (1.0 - _smoothstep(x, *HERO_RIGHT_FADE))
    down = _smoothstep(y, *HERO_TOP_FADE) * (1.0 - _smoothstep(y, *HERO_BOTTOM_FADE))
    return down[:, None] * across[None, :]


def hero_image(master: Path) -> Image.Image:
    """The hero image at the master's width: the 2:1 band of the master,
    mirrored, with the matte as its alpha channel."""
    image = load(master).crop(HERO_CROP).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    assert image.size == (HERO_CROP[2] - HERO_CROP[0], HERO_CROP[3] - HERO_CROP[1])
    alpha = Image.fromarray(np.round(hero_matte(*image.size) * 255).astype("uint8"))
    image.putalpha(alpha)
    return image


def hero(masters: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    image = hero_image(masters / MASTERS[HERO_SEQUENCE])
    for width in HERO_WIDTHS:
        if width > image.width:
            raise ValueError(f"the master is {image.width} px wide; not upscaled")
        sized = image.resize((width, width // 2), Image.Resampling.LANCZOS)
        # Lossy colour at the quality of the atlas files, lossless alpha
        # (the matte decides the readability of the copy over the image).
        sized.save(
            out / f"{HERO_IMAGE}-{width}.webp", format="WEBP", quality=88, method=6
        )


if __name__ == "__main__":
    arguments = sys.argv[1:]
    write, kind = (hero, "hero") if arguments[:1] == ["--hero"] else (main, "atlas")
    arguments = arguments[1:] if kind == "hero" else arguments
    output = REPOSITORY / "site/assets" / kind
    write(Path(arguments[0]), Path(arguments[1]) if len(arguments) > 1 else output)
