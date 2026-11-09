"""Re-encode one Lycopodium morphometry CSV from Latin-1 to UTF-8.

    python tools/datasets/lycopodium_morphometry_to_utf8.py INPUT.csv OUTPUT.csv

The one-time conversion of the two morphometry files of the dataset
``lycopodium-spore-diffraction`` (ADR 007, addendum of Issue #417: a file is
converted once, outside the build, by a documented, checksum-pinned script).
The build, the verification, and CI never run it; the committed samples are
its output.

The record's files are ImageJ results saved as Latin-1: the only bytes above
127 are 0xB5, the micro sign of the headers ``r^2 (µm^2)``, ``r (µm)`` and
``d (µm)``. A committed file of the repository is UTF-8, so the script
decodes the bytes as Latin-1 and encodes them as UTF-8, and changes nothing
else: the same numbers, the ``;`` separators, the CRLF line endings. Before
converting it checks

- the SHA-256 of the input against ``INPUTS`` (the two files inspected for the
  dossier; any other file is refused), and
- that every byte above 127 is 0xB5, so that the decoding cannot be in doubt
  (Latin-1 and cp1252 agree on it).
"""

import hashlib
import sys
from pathlib import Path

INPUTS = {
    "Lycopodium_Morphometry_x160.csv": (
        "03648277f9fda3d561a8fbab048133e72333877feec65e103159a1baeb08d7dc"
    ),
    "Lycopodium_Morphometry_x80.csv": (
        "eb6a0c5c922add8b3f962b00374b6f52bfca2297bf4f45d5617c0aff5ca1644d"
    ),
}
MICRO = 0xB5


def reencode(data: bytes) -> bytes:
    """The bytes decoded as Latin-1 and encoded as UTF-8, after checking that
    the micro sign is their only byte above 127."""
    other = sorted({b for b in data if b > 127} - {MICRO})
    if other:
        raise ValueError(f"bytes above 127 other than 0xB5: {[hex(b) for b in other]}")
    return data.decode("latin-1").encode("utf-8")


def convert(input_path: Path, output_path: Path, *, check_input: bool = True) -> None:
    input_path = Path(input_path)
    data = input_path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if check_input and INPUTS.get(input_path.name) != digest:
        raise ValueError(f"{input_path}: sha256 {digest} is not a pinned input")
    Path(output_path).write_bytes(reencode(data))


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.splitlines()[2].strip(), file=sys.stderr)
        return 2
    convert(Path(argv[0]), Path(argv[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
