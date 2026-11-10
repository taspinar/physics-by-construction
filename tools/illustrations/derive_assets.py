"""Derive the delivery sizes of the atlas illustrations from their masters:
the card 152 and 228 px wide (the 76 px slot at 2x and 3x) and the panel 400
and 800 px wide (the 200 px slot at 2x and 4x), all 4:3, WebP, on the page's
paper. One master per sequence; the mechanics card takes the owner's detail
crop of the same figure, since the whole is too fine at 76 px.

The hero of the home page (F158) takes four of the same masters at one hero
size, 1200 px wide (4:3), one file per illustration, named by the image
identifier of site/hero.yaml. Every master is wider than 1200 px, so
nothing is upscaled.

Run: python derive_assets.py MASTERS_DIRECTORY [OUTPUT_DIRECTORY]
The output defaults to site/assets/atlas of the repository.
Run: python derive_assets.py --hero MASTERS_DIRECTORY [OUTPUT_DIRECTORY]
The output defaults to site/assets/hero of the repository.
"""

import sys
from pathlib import Path

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
# The hero images: the image identifier and the sequence whose master it is.
HERO = {
    "double-pendulum": "mechanics",
    "vortex-street": "fluids",
    "hot-cold-gas": "thermodynamics",
    "exoplanet-transit": "astrophysics",
}
HERO_WIDTH = 1200


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


def hero(masters: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for image_id, sequence in HERO.items():
        resize(load(masters / MASTERS[sequence]), HERO_WIDTH).save(
            out / f"{image_id}.webp", format="WEBP", quality=88, method=6
        )


if __name__ == "__main__":
    arguments = sys.argv[1:]
    write, kind = (hero, "hero") if arguments[:1] == ["--hero"] else (main, "atlas")
    arguments = arguments[1:] if kind == "hero" else arguments
    output = REPOSITORY / "site/assets" / kind
    write(Path(arguments[0]), Path(arguments[1]) if len(arguments) > 1 else output)
