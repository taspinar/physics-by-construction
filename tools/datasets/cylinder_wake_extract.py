"""Extract the committed sample of the Shang and Tu cylinder-wake PIV once.

    uv run python tools/datasets/cylinder_wake_extract.py INPUT_MAT OUTPUT_DIR

The one-time extraction of the dataset ``piv-cylinder-wake``: the record's
only file, ``cylinder_vel.mat`` (1,082,404,799 bytes, Zenodo 20765567), is far
more than a sample can hold, so a small part of it is written once, outside
the build. The build, the verification, and CI never run this script; the
committed files are its output and the dataset check compares them with the
card's sha256. ``INPUT_MAT`` is the file as ``./scripts/fetch-data.sh
piv-cylinder-wake`` downloads it; its MD5 (published by Zenodo) and its
SHA-256 must equal those pinned below, any other file is refused. It is read
with ``scipy.io.loadmat`` (MAT 5.0; about 2.4 GB of memory) and nothing in it
is executed.

The output (``pbc.data.reference.cylinder_wake.extract``): u and v of frames
0-59 on a crop of the near wake as float32, the mask (u and v both exactly
zero), the mean u and v over the unmasked frames of all 8000, u and v at two
probes on the wake axis for all 8000 frames, and a JSON file with the grid,
the indices, the cadence, the units, and the source. Two runs give the same
bytes.
"""

import hashlib
import sys
from pathlib import Path

from pbc.data.reference import cylinder_wake as cw

FILENAME = "cylinder_vel.mat"
SIZE = 1082404799
MD5 = "4cc876439c48f7970afa477ea17d217a"  # Zenodo's checksum of the file
SHA256 = "328cd8d17cd2eb42faef6e4766bc8e515e0eac06868152972adab9bdf91926e7"
SOURCE = {
    "record": "Zenodo 20765567, doi 10.5281/zenodo.20765567",
    "file": FILENAME,
    "bytes": SIZE,
    "md5": MD5,
    "sha256": SHA256,
    "extracted_by": "tools/datasets/cylinder_wake_extract.py",
}


def digests(path: Path) -> tuple[str, str]:
    md5, sha = hashlib.md5(), hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 22), b""):
            md5.update(block)
            sha.update(block)
    return md5.hexdigest(), sha.hexdigest()


def convert(input_mat: Path, output_dir: Path) -> None:
    md5, sha = digests(input_mat)
    if (md5, sha) != (MD5, SHA256):
        raise ValueError(
            f"{input_mat}: md5 {md5}, sha256 {sha}; expected md5 {MD5}, sha256 {SHA256}"
        )
    record = cw.read_mat(input_mat)
    if record["u"].shape != cw.RECORD_SHAPE:
        raise ValueError(f"{input_mat}: shape {record['u'].shape}")
    cw.write_sample(cw.extract(record, SOURCE), output_dir)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.splitlines()[2].strip(), file=sys.stderr)
        return 2
    try:
        convert(Path(argv[0]), Path(argv[1]))
    except (OSError, ValueError) as error:
        print(f"cylinder_wake_extract: {error}", file=sys.stderr)
        return 1
    print(f"wrote {', '.join(cw.SAMPLE_FILES)} in {argv[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
