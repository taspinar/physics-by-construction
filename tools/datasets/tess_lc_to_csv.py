"""Convert one TESS SPOC light-curve FITS file to the four-column CSV sample.

    python tools/datasets/tess_lc_to_csv.py INPUT.fits OUTPUT.csv

The one-time conversion of the dataset ``tess-exoplanet-light-curves``
(ADR 007, addendum of Issue #417: a FITS file is converted once, outside the
build, by a documented, checksum-pinned script). The build, the verification,
and CI never run it; the committed sample is its output.

It reads the FITS file with NumPy alone (no FITS library is a dependency of the
project): the header cards of each HDU, the binary table ``LIGHTCURVE`` of the
first extension, and its columns ``TIME``, ``PDCSAP_FLUX``, ``PDCSAP_FLUX_ERR``,
and ``QUALITY``. Before converting it checks

- the SHA-256 of the input against ``INPUT_SHA256`` (the file inspected for the
  dossier; another sector or a reprocessed version is refused), and
- the ``DATASUM`` and ``CHECKSUM`` keywords of every HDU (the FITS checksum
  convention: the 32-bit ones'-complement sum of the data, and of the whole
  HDU, which the CHECKSUM card makes equal to -0).

The CSV has one row per cadence of the table, in its order, nothing dropped or
changed: each value is written as the shortest decimal that reads back to the
same binary number (float64 for the time, float32 for the fluxes), and a
missing value (NaN in the file) as ``nan``. The quality flags are the
pipeline's integers. A header comment names the source file, its checksum, the
columns, and their units as the FITS header gives them.
"""

import hashlib
import sys
from pathlib import Path

import numpy as np

INPUT_NAME = "tess2020238165205-s0029-0000000100100827-0193-s_lc.fits"
INPUT_SHA256 = "c89434e50db863e589c9321cf29c93e449ef1526f1a9db19552446b721fd0949"
COLUMNS = ("TIME", "PDCSAP_FLUX", "PDCSAP_FLUX_ERR", "QUALITY")
BLOCK = 2880
CARD = 80
# TFORM letter -> big-endian NumPy type (FITS standard 4.0, table 18).
_TYPES = {
    "L": "i1",
    "B": "u1",
    "I": ">i2",
    "J": ">i4",
    "K": ">i8",
    "E": ">f4",
    "D": ">f8",
    "A": "S1",
}


def _value(text: str):
    text = text.split("/", 1)[0].strip() if not text.lstrip().startswith("'") else text
    text = text.strip()
    if text.startswith("'"):
        end = text.find("'", 1)
        while end != -1 and text[end + 1 : end + 2] == "'":
            end = text.find("'", end + 2)
        return text[1:end].replace("''", "'").rstrip()
    if text in ("T", "F"):
        return text == "T"
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text.replace("D", "E"))
    except ValueError:
        return text


def read_header(raw: bytes, start: int) -> tuple[dict, int]:
    """The keywords of the header at ``start`` and the offset of its data."""
    header: dict = {}
    pos = start
    while True:
        if pos + BLOCK > len(raw):
            raise ValueError("a header runs past the end of the file")
        block = raw[pos : pos + BLOCK].decode("ascii")
        pos += BLOCK
        for k in range(0, BLOCK, CARD):
            card = block[k : k + CARD]
            key = card[:8].strip()
            if key == "END":
                return header, pos
            if card[8:10] == "= " and key not in header:
                header[key] = _value(card[10:])


def data_size(header: dict) -> int:
    """Bytes of the data of an HDU, before padding to a whole block."""
    naxis = header.get("NAXIS", 0)
    if naxis == 0:
        return 0
    size = abs(header["BITPIX"]) // 8
    for k in range(1, naxis + 1):
        size *= header[f"NAXIS{k}"]
    return header.get("GCOUNT", 1) * (size + header.get("PCOUNT", 0))


def hdus(raw: bytes) -> list[tuple[dict, int, int, int]]:
    """``(header, header start, data start, data end padded)`` of every HDU."""
    out = []
    pos = 0
    while pos < len(raw):
        header, data = read_header(raw, pos)
        end = data + -(-data_size(header) // BLOCK) * BLOCK
        out.append((header, pos, data, end))
        pos = end
    return out


def ones_complement_sum(chunk: bytes) -> int:
    """The 32-bit ones'-complement sum of big-endian words (FITS checksum)."""
    words = np.frombuffer(chunk, dtype=">u4").astype(np.uint64)
    total = int(words.sum())
    while total >> 32:
        total = (total & 0xFFFFFFFF) + (total >> 32)
    return total


def verify_checksums(raw: bytes) -> list[str]:
    """Problems with DATASUM or CHECKSUM of any HDU; empty when all verify."""
    problems = []
    for k, (header, start, data, end) in enumerate(hdus(raw)):
        if "DATASUM" in header:
            datasum = ones_complement_sum(raw[data:end])
            if str(datasum) != str(header["DATASUM"]).strip():
                problems.append(f"HDU {k}: DATASUM {header['DATASUM']} != {datasum}")
        if "CHECKSUM" in header and ones_complement_sum(raw[start:end]) != 0xFFFFFFFF:
            problems.append(f"HDU {k}: CHECKSUM does not verify")
    return problems


def read_table(raw: bytes, index: int = 1) -> tuple[dict, dict[str, np.ndarray]]:
    """The header and the columns of the binary table in HDU ``index``."""
    header, _, data, _ = hdus(raw)[index]
    if header.get("XTENSION") != "BINTABLE":
        raise ValueError(f"HDU {index} is not a binary table")
    fields = []
    for k in range(1, header["TFIELDS"] + 1):
        form = str(header[f"TFORM{k}"]).strip()
        count = int(form[:-1] or 1)
        kind = _TYPES[form[-1]]
        fields.append((header[f"TTYPE{k}"], kind, (count,) if count > 1 else ()))
    dtype = np.dtype(fields)
    if dtype.itemsize != header["NAXIS1"]:
        raise ValueError("the row length differs from NAXIS1")
    rows = np.frombuffer(raw, dtype=dtype, count=header["NAXIS2"], offset=data)
    return header, {name: rows[name] for name in dtype.names}


def units(header: dict) -> dict[str, str]:
    return {
        header[f"TTYPE{k}"]: str(header.get(f"TUNIT{k}", "")).strip()
        for k in range(1, header["TFIELDS"] + 1)
    }


def _float(value, kind) -> str:
    value = kind(value)
    if np.isnan(value):
        return "nan"
    return np.format_float_positional(value, unique=True, trim="-")


def convert(fits_path: Path, csv_path: Path, *, check_input: bool = True) -> None:
    raw = Path(fits_path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if check_input and digest != INPUT_SHA256:
        raise ValueError(f"{fits_path}: sha256 {digest} is not the pinned input")
    problems = verify_checksums(raw)
    if problems:
        raise ValueError(f"{fits_path}: " + "; ".join(problems))
    header, table = read_table(raw)
    unit = units(header)
    lines = [
        f"# source: {Path(fits_path).name} (sha256 {digest})",
        "# converted by tools/datasets/tess_lc_to_csv.py; every row of the"
        " LIGHTCURVE table, values unchanged, NaN written as nan",
        "# units: " + ", ".join(f"{name} [{unit[name] or 'none'}]" for name in COLUMNS),
        ",".join(name.lower() for name in COLUMNS),
    ]
    for t, f, e, q in zip(*(table[name] for name in COLUMNS), strict=True):
        lines.append(
            ",".join(
                (
                    _float(t, np.float64),
                    _float(f, np.float32),
                    _float(e, np.float32),
                    str(int(q)),
                )
            )
        )
    Path(csv_path).write_text("\n".join(lines) + "\n", encoding="ascii")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.splitlines()[2].strip(), file=sys.stderr)
        return 2
    convert(Path(argv[0]), Path(argv[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
