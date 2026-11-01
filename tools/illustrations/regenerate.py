"""The regeneration check of the atlas illustrations, run on demand (ADR 021
decision 2): never by the build, by ./scripts/verify.sh, or by CI.

For each sequence whose illustration has a script, it runs the script in a
scratch directory, finds the master the script writes, and compares its
SHA-256 with the provenance register (site/assets/provenance.yaml). The
renders are not promised to be byte-stable across versions of NumPy, SciPy,
Matplotlib, and Pillow, so a master whose bytes differ is compared by its
pixels instead: its derived 800 px panel (or 228 px card) against the file
committed under site/assets/atlas, which passes when the mean absolute
difference is at most TOLERANCE of 255 per channel. An illustration without a
script (the astrophysics transit) is reported and skipped.

Run with an environment that has the scripts' dependencies (numpy, scipy,
matplotlib, pillow; numba for the fluid dynamics):

    python tools/illustrations/regenerate.py [SEQUENCE ...]
"""

import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml
from PIL import Image, ImageChops, ImageStat

HERE = Path(__file__).resolve().parent
REPOSITORY = HERE.parents[1]
sys.path.insert(0, str(HERE))
from derive_assets import CARD_MASTER, MASTERS, load  # noqa: E402

REGISTER = REPOSITORY / "site/assets/provenance.yaml"
ATLAS = REPOSITORY / "site/assets/atlas"
TOLERANCE = 2.0

# The scripts each sequence needs, and the one to run with its arguments; the
# scratch directory is passed where a script takes an output directory, and
# every script is run from inside it.
RUNS = {
    "mechanics": (["double_pendulum_atlas.py"], []),
    "thermodynamics": (["render_hot_cold.py"], []),
    "waves": (["render_waves.py"], []),
    "electromagnetism": (["render_solenoid.py"], ["--output-dir", "."]),
    "fluids": (["generate_fluid_dynamics.py"], []),
    "quantum": (["generate_wigner_cat.py"], []),
    "materials": (["render_phonons.py"], []),
    **{
        sequence: (["part_b_textfree.py", "render_part_b.py"], ["."])
        for sequence in (
            "reasoning",
            "law-discovery",
            "benchmarking",
            "autonomous-research",
        )
    },
}


def sha256(file: Path) -> str:
    return hashlib.sha256(file.read_bytes()).hexdigest()


def registered_hashes() -> dict[str, str]:
    """The SHA-256 of each master, as the register records it."""
    entries = yaml.safe_load(REGISTER.read_text(encoding="utf-8"))["assets"]
    return {
        entry["master"]: entry["sha256"]
        for entry in entries.values()
        if isinstance(entry, dict) and "master" in entry
    }


def pixel_difference(master: Path, committed: Path) -> float:
    """The mean absolute difference, per channel of 0 to 255, between the
    committed file and the same size derived from ``master``."""
    with Image.open(committed) as image:
        size = image.size
        reference = image.convert("RGB")
    derived = load(master).resize(size, Image.Resampling.LANCZOS)
    return sum(ImageStat.Stat(ImageChops.difference(derived, reference)).mean) / 3


def check(sequence: str, hashes: dict[str, str]) -> list[str]:
    """Run the sequence's script and return the problems found."""
    if sequence not in RUNS:
        return [f"{sequence}: no script; registered by its author, not regenerated"]
    scripts, arguments = RUNS[sequence]
    masters = {"panel": MASTERS[sequence]}
    if sequence in CARD_MASTER:
        masters["card"] = CARD_MASTER[sequence]
    problems = []
    with tempfile.TemporaryDirectory() as scratch:
        directory = Path(scratch)
        for script in scripts:
            shutil.copy(HERE / script, directory / script)
        subprocess.run(
            [sys.executable, scripts[0], *arguments], cwd=directory, check=True
        )
        for kind, name in masters.items():
            master = directory / name
            if not master.is_file():
                problems.append(f"{sequence}: the script wrote no {name}")
                continue
            if sha256(master) == hashes.get(name):
                print(f"{sequence}: {name} is identical to the registered master")
                continue
            width = 800 if kind == "panel" else 228
            committed = ATLAS / f"{sequence}-{kind}-{width}.webp"
            difference = pixel_difference(master, committed)
            verdict = "within" if difference <= TOLERANCE else "OVER"
            print(
                f"{sequence}: {name} differs in its bytes; the {kind} differs by"
                f" {difference:.2f} of 255 per pixel, {verdict} {TOLERANCE}"
            )
            if difference > TOLERANCE:
                problems.append(f"{sequence}: {name} no longer matches its files")
    return problems


def main(sequences: list[str]) -> int:
    hashes = registered_hashes()
    problems = []
    for sequence in sequences or list(MASTERS):
        problems += check(sequence, hashes)
    for problem in problems:
        print(problem)
    return 1 if any("no longer" in p or "wrote no" in p for p in problems) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
