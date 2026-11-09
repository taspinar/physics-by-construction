"""Shorten the ten Ost et al. hot-wire runs once, to the committed sample.

    uv run python tools/datasets/ost_hotwire_extract.py INPUT_DIR OUTPUT_DIR

The one-time extraction of the dataset ``ost-hotwire-cylinder-wakes``: the
ten files of Mendeley Data doi 10.17632/xy8ggx9hn6.1 (4,456,448 bytes each,
44.6 MB together) exceed the sample caps, so the first 2^14 samples
(16.384 s) of each run are written once, outside the build, as one CSV, the
velocity rounded to 0.001 m/s; the time column of the record (k ms, printed
with 8 significant digits) is replaced by the row number. The build, the
verification, and CI never run this script; the dataset check compares the
committed files with the card's sha256.

``INPUT_DIR`` holds the ten files (directly or one per subdirectory), as
``./scripts/fetch-data.sh ost-hotwire-cylinder-wakes`` downloads them. The
SHA-256 of each must equal the one pinned below (the hashes Mendeley Data
publishes for the files); any other file is refused. The files are read as
plain text and nothing in them is executed.

``runs.csv`` holds each run's diameter, reference velocity, Reynolds number,
aspect ratio, and probe position, which the record gives only in the
description of each file (Mendeley Data API, read 2026-11-09), copied here
with the decimal comma of two of them ("5,08 m/s") read as a point. The
Reynolds number of ``Velocity_1C50_5ms.txt`` is copied as the record states
it (5.17e4, the value of the 16 m/s run of that cylinder); the dossier
discusses it.
"""

import hashlib
import sys
from pathlib import Path

import numpy as np

from pbc.data.reference import ost_hotwire as oh

# file: (sha256, "D [mm],U [m/s],Re,L/D,x/D,w/D"), from the record.
RUNS = {
    "Velocity_1C25_5ms-1.txt": (
        "783de993f1d1c03301381524a67e2329585f7664b002ec24adb8a401fcc1c580",
        "25.1,5.08,8250,5.82,1.19,2.9",
    ),
    "Velocity_1C25_10.5ms.txt": (
        "ab7a9b10c149e04c7e975c471c7720a3b068fd7f346d04e4f7bb95e557fe8545",
        "25.1,10.5,17100,5.82,1.19,2.9",
    ),
    "Velocity_1C25_16ms.txt": (
        "605535f205eb6b6b28275e5331df1382261e95906910abb1cdd7044719598520",
        "25.1,16,26100,5.82,1.19,2.9",
    ),
    "Velocity_1C32_5ms.txt": (
        "66c67e5ba8bb3057749c0318803da2b190823405be45885fa98508c593b26fbf",
        "32,5.08,10500,4.56,1.64,2.65",
    ),
    "Velocity_1C32_8.3ms.txt": (
        "cf5320ecdb3301625706010668f910f96644e50e5031f079a39be9935cdabaf8",
        "32,8.3,17100,4.56,1.64,2.65",
    ),
    "Velocity_1C32_10.5ms.txt": (
        "66326563d6214972d7dc34d2ac7ca6a945cc00e5efc9ab8f859a4d12e335379c",
        "32,10.5,21800,4.56,1.64,2.65",
    ),
    "Velocity_1C32_16ms.txt": (
        "079a3342d2259866839d3a5185c96b08b8e6078b0449edf2a8c2e561fb242669",
        "32,16.0,32800,4.56,1.64,2.65",
    ),
    "Velocity_1C50_5ms.txt": (
        "76922c545c48de7166c5523ad15db1c85f449df384cf15820605a5ea189b9cd1",
        "50,5.05,51700,2.92,0.9,1.24",
    ),
    "Velocity_1C50_10.5ms.txt": (
        "42866f6f3eb4051739f325cc3f8f6eb19b1f89df3bf6cdc490263dadef1c16dd",
        "50,10.5,34200,2.92,0.9,1.24",
    ),
    "Velocity_1C50_16ms.txt": (
        "7cc65052666546af4024e64813d1d1f8d25f0f1574bd32c81d219d2dccd8a930",
        "50,16,51700,2.92,0.9,1.24",
    ),
}
RECORD = "Mendeley Data, doi 10.17632/xy8ggx9hn6.1 (version 1, 2019-11-01)"


def run_name(filename: str) -> str:
    return filename.removeprefix("Velocity_").removesuffix(".txt")


def find(input_dir: Path, filename: str) -> Path:
    paths = [p for p in Path(input_dir).rglob(filename) if p.is_file()]
    if len(paths) != 1:
        raise ValueError(f"{input_dir}: {len(paths)} files named {filename}")
    return paths[0]


def read_record_file(path: Path) -> np.ndarray:
    """The velocity column of one record file; the time must be k ms."""
    table = np.loadtxt(path, ndmin=2)
    if table.shape != (oh.RECORD_SAMPLES, 2):
        raise ValueError(f"{path}: shape {table.shape}")
    k = np.arange(oh.RECORD_SAMPLES)
    if np.abs(table[:, 0] - k / oh.FS).max() > 2e-5:
        raise ValueError(f"{path}: the time column is not 1 ms apart")
    return table[:, 1]


def header() -> list[str]:
    return [
        f"# {RECORD}, Ost, de Paula, Moller,"
        " 'Turbulent flow past cylinders'; CC BY 4.0",
        "# the first 16384 of 131072 samples of each file (SHA-256 pinned in"
        " tools/datasets/ost_hotwire_extract.py), velocity rounded to 0.001 m/s",
        "# row k is the time k ms (1000 Hz, low-pass 300 Hz); columns: the runs of"
        " runs.csv; values: hot-wire velocity in m/s",
    ]


def convert(input_dir: Path, output_dir: Path) -> None:
    columns, rows = [], []
    for filename, (expected, meta) in RUNS.items():
        path = find(input_dir, filename)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"{path}: sha256 {actual}, expected {expected}")
        columns.append(read_record_file(path)[: oh.SAMPLES])
        rows.append(",".join([run_name(filename), filename, expected, meta]))
    names = [run_name(f) for f in RUNS]
    table = np.column_stack(columns)
    body = [",".join(f"{value:.3f}" for value in row) for row in table]
    output_dir = Path(output_dir)
    (output_dir / oh.SERIES).write_text(
        "\n".join([*header(), ",".join(names), *body]) + "\n", encoding="ascii"
    )
    (output_dir / oh.RUNS).write_text(
        "\n".join([",".join(oh.RUN_FIELDS), *rows]) + "\n", encoding="ascii"
    )


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.splitlines()[2].strip(), file=sys.stderr)
        return 2
    try:
        convert(Path(argv[0]), Path(argv[1]))
    except (OSError, ValueError) as error:
        print(f"ost_hotwire_extract: {error}", file=sys.stderr)
        return 1
    print(f"wrote {oh.SERIES} and {oh.RUNS} in {argv[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
