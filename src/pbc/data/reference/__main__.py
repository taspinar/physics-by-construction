"""``python -m pbc.data.reference <dataset> [--data-dir DIR] [--out FILE]``."""

import argparse
import importlib
from pathlib import Path

from pbc.data import SAMPLES_DIR

MODULES = {
    "gw150914-strain": "gw150914",
    "npl-onwafer-sparameters": "npl_sparameters",
    "aalborg-submerged-bar": "aalborg_flume",
    "bayreuth-rlc-impedance": "bayreuth_rlc",
    "nist-numisheet-dp980": "nist_numisheet",
    "tess-exoplanet-light-curves": "tess_wasp18",
    "munich-bell-event-ready": "munich_bell",
    "lycopodium-spore-diffraction": "lycopodium",
    "trackpy-bulk-water": "trackpy_bulk_water",
    "xu-damped-pendulum": "xu_pendulum",
    "sdss-balmer-spectrum": "sdss_balmer",
    "dwd-potsdam-soil-temperature": "dwd_soil",
    "piv-cylinder-wake": "cylinder_wake",
    "ost-hotwire-cylinder-wakes": "ost_hotwire",
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
