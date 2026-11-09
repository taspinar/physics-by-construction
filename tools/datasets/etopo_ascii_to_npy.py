"""Convert the ETOPO 2022 OPeNDAP ASCII crop to the int16 NumPy sample.

    python tools/datasets/etopo_ascii_to_npy.py INPUT.txt OUTPUT.npy

The one-time conversion of the bathymetry of the dataset
``kamchatka-2025-tsunami-inputs`` (ADR 007: a committed sample derived from a
download by a documented, checksum-pinned script outside the build). The
build, the verification, and CI never run it; the committed sample is its
output.

The input is the response of NCEI's THREDDS server to the OPeNDAP ASCII
request of the card (``.ascii?z[7500:4:8999][19200:4:21599]`` on
``ETOPO_2022_v1_60s_N90W180_bed.nc``): every fourth cell of the 60 arc-second
grid from 35N to 60N and from 140E to 180E, 375 rows by 600 columns, cell
centres at

    lat_i = 35 + (4 i + 0.5) / 60,   lon_j = 140 + (4 j + 0.5) / 60  (degrees).

Every fourth cell is taken, not a block average: the stride decimates. The
script checks

- the SHA-256 of the input against ``INPUT_SHA256`` (the response inspected
  for the dossier; a generated response is not guaranteed to stay byte for
  byte the same, so the parsed array is pinned too, ``ARRAY_SHA256``, the
  SHA-256 of the float32 values in C order, little-endian), and
- the two coordinate maps of the response against the formula above.

The output is ``z`` in metres, positive up (EGM2008 heights; negative below
sea level), rounded to the nearest metre and stored as int16 (the largest
change is 0.5 m), in a ``.npy`` file of 375 x 600 values, row 0 the
southernmost. The input is accepted only if every value is finite and no
fill value (-99999) occurs. ``--allow-other-input`` accepts an input whose
own SHA-256 differs if its parsed array equals the pinned one.
"""

import hashlib
import io
import sys
from pathlib import Path

import numpy as np

INPUT_NAME = "etopo2022_60s_bed_35N60N_140E180E_stride4.txt"
INPUT_SHA256 = "454b00a5aaaaf4406523e1f39fc38dbd40ea3c6799d5cde209d25b75701bf198"
ARRAY_SHA256 = "8bd4f1e5c02b1a39c7706cf6b1c76771c4bbde2716310e55af0f743978bb719d"
SHAPE = (375, 600)
STRIDE = 4
LAT0, LON0 = 35.0, 140.0  # degrees, the edges of the crop
FILL = -99999.0


def grid() -> tuple[np.ndarray, np.ndarray]:
    """Cell-centre latitudes and longitudes of the crop, in degrees."""
    i = np.arange(SHAPE[0])
    j = np.arange(SHAPE[1])
    return LAT0 + (STRIDE * i + 0.5) / 60.0, LON0 + (STRIDE * j + 0.5) / 60.0


def _numbers(lines: list[str]) -> np.ndarray:
    return np.array([float(v) for v in ",".join(lines).split(",") if v.strip()])


def parse(text: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The z array (float32), and the lat and lon maps, of an ASCII response."""
    lines = text.splitlines()
    try:
        start = lines.index(f"z.z[{SHAPE[0]}][{SHAPE[1]}]")
        lat_at = lines.index(f"z.lat[{SHAPE[0]}]")
        lon_at = lines.index(f"z.lon[{SHAPE[1]}]")
    except ValueError as error:
        raise ValueError("not the ASCII response of the expected crop") from error
    rows = []
    for k, line in enumerate(lines[start + 1 : start + 1 + SHAPE[0]]):
        index, _, values = line.partition(",")
        if index.strip() != f"[{k}]":
            raise ValueError(f"row {k}: unexpected index {index!r}")
        rows.append(np.array([float(v) for v in values.split(",")], dtype=np.float32))
    z = np.array(rows, dtype=np.float32)
    if z.shape != SHAPE:
        raise ValueError(f"shape {z.shape}, expected {SHAPE}")
    lat = _numbers(lines[lat_at + 1 : lat_at + 2])
    lon = _numbers(lines[lon_at + 1 : lon_at + 2])
    return z, lat, lon


def array_sha256(z: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(z, dtype="<f4").tobytes()).hexdigest()


def convert(text: str) -> np.ndarray:
    """The int16 sample of a parsed, checked response."""
    z, lat, lon = parse(text)
    expected_lat, expected_lon = grid()
    if lat.shape != expected_lat.shape or np.abs(lat - expected_lat).max() > 1e-9:
        raise ValueError("the latitude map differs from the crop's grid")
    if lon.shape != expected_lon.shape or np.abs(lon - expected_lon).max() > 1e-9:
        raise ValueError("the longitude map differs from the crop's grid")
    if not np.all(np.isfinite(z)) or np.any(z == FILL):
        raise ValueError("a value is missing (NaN or the fill value)")
    return np.rint(z).astype(np.int16)


def to_npy(z16: np.ndarray) -> bytes:
    buffer = io.BytesIO()
    np.save(buffer, z16, allow_pickle=False)
    return buffer.getvalue()


def main(argv: list[str]) -> int:
    allow = "--allow-other-input" in argv
    paths = [a for a in argv if a != "--allow-other-input"]
    if len(paths) != 2:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    source, target = Path(paths[0]), Path(paths[1])
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    z, _, _ = parse(raw.decode("ascii"))
    if digest != INPUT_SHA256 and (not allow or array_sha256(z) != ARRAY_SHA256):
        print(
            f"{source}: sha256 {digest} is not the inspected response {INPUT_SHA256}",
            file=sys.stderr,
        )
        return 1
    if array_sha256(z) != ARRAY_SHA256:
        print(
            f"{source}: the parsed array differs from the inspected one",
            file=sys.stderr,
        )
        return 1
    target.write_bytes(to_npy(convert(raw.decode("ascii"))))
    print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
