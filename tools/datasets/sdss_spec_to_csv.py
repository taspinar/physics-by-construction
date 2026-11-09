"""Convert one SDSS DR17 optical spectrum (``spec-*.fits``, lite) to a CSV.

    python tools/datasets/sdss_spec_to_csv.py INPUT.fits OUTPUT.csv

The one-time conversion of the dataset ``sdss-balmer-spectrum`` (ADR 007,
addendum of Issue #417: a FITS file is converted once, outside the build, by a
documented, checksum-pinned script). The build, the verification, and CI never
run it.

It reads the FITS file with NumPy alone, with the header and table reader of
``tess_lc_to_csv.py`` beside it (no FITS library is a dependency of the
project): the primary header, the binary table ``COADD`` of the first
extension (one row per pixel of the co-added spectrum), and the one-row table
``SPECOBJ`` of the second (the pipeline's redshift and classification). Before
converting it checks

- the SHA-256 of the input against ``INPUT_SHA256`` and its SHA-1 against
  ``INPUT_SHA1``, the checksum the SDSS Science Archive Server publishes for
  the file (another spectrum or a reprocessed version is refused), and
- the FITS ``DATASUM`` and ``CHECKSUM`` keywords of any HDU that has them (this
  file has none).

The CSV has one row per pixel of ``COADD``, in its order, nothing dropped or
changed: the columns ``loglam``, ``flux``, ``ivar``, ``and_mask``, and
``wdisp``, each float written as the shortest decimal that reads back to the
same float32, the mask as the pipeline's integer. Comment lines name the
source file and its checksum, the columns and their units (from the primary
header's ``BUNIT``, ``VACUUM``, and ``WFITTYPE`` and the SDSS data model, since
the table has no ``TUNITn``), and the pipeline's values of ``SPECOBJ`` that the
dossier compares with.
"""

import hashlib
import importlib.util
import sys
from pathlib import Path

import numpy as np

INPUT_NAME = "spec-1949-53433-0480.fits"
INPUT_SHA256 = "0f9aa3f5f187dde1fb42e6b58ab9b428e48a2d45f73e7254d954f48121a6a813"
INPUT_SHA1 = "e288a7d8c1fa38d11d83757fce03038ab183a012"
COLUMNS = ("loglam", "flux", "ivar", "and_mask", "wdisp")
UNITS = {
    "loglam": "log10(wavelength / Angstrom), vacuum, heliocentric",
    "flux": "1E-17 erg/cm^2/s/Ang",
    "ivar": "(1E-17 erg/cm^2/s/Ang)^-2",
    "and_mask": "none, SPPIXMASK bits",
    "wdisp": "pixels of 1e-4 in loglam",
}
SPECOBJ = ("CLASS", "SUBCLASS", "Z", "Z_ERR", "ZWARNING")


def _reader():
    """The FITS reader of ``tess_lc_to_csv.py``, loaded from beside this file."""
    path = Path(__file__).with_name("tess_lc_to_csv.py")
    spec = importlib.util.spec_from_file_location("tess_lc_to_csv", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fits = _reader()


def _text(value) -> str:
    """A FITS character field (an array of single bytes) as a stripped str."""
    return b"".join(np.atleast_1d(value).tolist()).decode("ascii").strip()


def _float(value) -> str:
    return np.format_float_positional(np.float32(value), unique=True, trim="-")


def convert(fits_path: Path, csv_path: Path, *, check_input: bool = True) -> None:
    raw = Path(fits_path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if check_input and (
        digest != INPUT_SHA256 or hashlib.sha1(raw).hexdigest() != INPUT_SHA1
    ):
        raise ValueError(f"{fits_path}: sha256 {digest} is not the pinned input")
    problems = fits.verify_checksums(raw)
    if problems:
        raise ValueError(f"{fits_path}: " + "; ".join(problems))
    primary = fits.hdus(raw)[0][0]
    if primary.get("VACUUM") is not True:
        raise ValueError(f"{fits_path}: wavelengths are not vacuum (VACUUM)")
    if primary.get("BUNIT") != UNITS["flux"]:
        raise ValueError(f"{fits_path}: BUNIT {primary.get('BUNIT')!r}")
    header, table = fits.read_table(raw, 1)
    if header.get("EXTNAME") != "COADD":
        raise ValueError(f"{fits_path}: HDU 1 is not COADD")
    _, specobj = fits.read_table(raw, 2)
    pipeline = []
    for name in SPECOBJ:
        value = specobj[name][0]
        if name in ("CLASS", "SUBCLASS"):
            pipeline.append(f"{name} {_text(value)}")
        elif name == "ZWARNING":
            pipeline.append(f"{name} {int(value)}")
        else:
            pipeline.append(f"{name} {_float(value)}")
    lines = [
        f"# source: {Path(fits_path).name} (sha256 {digest})",
        "# converted by tools/datasets/sdss_spec_to_csv.py; every row of the"
        " COADD table, values unchanged",
        "# units: " + ", ".join(f"{name} [{UNITS[name]}]" for name in COLUMNS),
        f"# pipeline (SPECOBJ): {', '.join(pipeline)}; HELIO_RV"
        f" {primary['HELIO_RV']} km/s applied",
        ",".join(COLUMNS),
    ]
    for loglam, flux, ivar, mask, wdisp in zip(
        *(table[name] for name in COLUMNS), strict=True
    ):
        lines.append(
            ",".join(
                (
                    _float(loglam),
                    _float(flux),
                    _float(ivar),
                    str(int(mask)),
                    _float(wdisp),
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
