"""``python -m pbc.data.reference <dataset> [--data-dir DIR] [--out FILE]``."""

import argparse
import importlib
from pathlib import Path

from pbc.data import SAMPLES_DIR

MODULES = {
    "gw150914-strain": "gw150914",
    "npl-onwafer-sparameters": "npl_sparameters",
    "aalborg-submerged-bar": "aalborg_flume",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", choices=sorted(MODULES))
    parser.add_argument("--data-dir", type=Path, help="default: the committed sample")
    parser.add_argument("--out", type=Path, default=Path("figure.png"))
    args = parser.parse_args()
    module = importlib.import_module(f"pbc.data.reference.{MODULES[args.dataset]}")
    data_dir = args.data_dir or SAMPLES_DIR / args.dataset
    figure = module.make_figure(data_dir)
    figure.savefig(args.out, dpi=150)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
