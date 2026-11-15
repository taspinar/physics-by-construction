"""``python -m pbc.data.reference <dataset> [--data-dir DIR] [--out FILE]``."""

import argparse
import importlib
from pathlib import Path

import matplotlib

from pbc.data import SAMPLES_DIR
from pbc.data.reference import reference_png
from pbc.data.registry import reference_modules

# Dataset id to module, from the cards with a go (Issue #456); a new dataset
# adds its card with a reference_module and no line here.
MODULES = reference_modules()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", choices=sorted(MODULES))
    parser.add_argument("--data-dir", type=Path, help="default: the committed sample")
    parser.add_argument("--out", type=Path, default=Path("figure.png"))
    args = parser.parse_args()
    matplotlib.use("agg", force=True)
    module = importlib.import_module(f"pbc.data.reference.{MODULES[args.dataset]}")
    data_dir = args.data_dir or SAMPLES_DIR / args.dataset
    # The one encoder, with the figure's provenance record (Issue #531).
    args.out.write_bytes(reference_png(module, data_dir))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
