"""Extract the committed sample of DWD Potsdam soil temperature from the zip.

    python tools/datasets/dwd_soil_extract.py INPUT.zip OUTPUT_DIR

The one-time extraction of the dataset ``dwd-potsdam-soil-temperature``
(ADR 007: a sample is a subset of the inspected file, written by a documented,
checksum-pinned script). The build, the verification, and CI never run it;
the committed sample is its output.

DWD publishes no checksum and replaces the archive every year (a new end
date in its name, corrections incorporated), so the input is pinned by the
SHA-256 that the dossier computed, ``INPUT_SHA256``; any other archive is
refused. The script uses the standard library only.

It writes, from the product file ``PRODUCT`` of the archive, two files of
whole lines, each line the bytes of the archive (CRLF line ends, padding, and
the missing-value marker -999 kept), the header line first and the rows in
their order:

- ``ANNUAL_FILE``: the rows at 00, 06, 12, and 18 h of the years
  ``ANNUAL_YEARS`` (four equally spaced readings a day, for the annual wave);
- ``DIURNAL_FILE``: every hourly row of June, July, and August of the years
  ``DIURNAL_YEARS`` (for the daily wave).

It also copies ``METADATA`` unchanged: the station's position, its
instruments, the parameters with their sources and units, and its operators.
"""

import hashlib
import sys
import zipfile
from pathlib import Path

INPUT_NAME = "stundenwerte_EB_03987_19510101_20251231_hist.zip"
INPUT_SHA256 = "6a968e6da83c783c4fa3a35196521021550bf56d1a64cde83cc9aeceb882329f"
PRODUCT = "produkt_eb_stunde_19510101_20251231_03987.txt"
HEADER = (
    b"STATIONS_ID;MESS_DATUM;QN_2;V_TE002;V_TE005;V_TE010;V_TE020;V_TE050;V_TE100;eor"
)
ANNUAL_FILE = "eb_stunde_03987_2015_2024_6h.txt"
ANNUAL_YEARS = range(2015, 2025)
ANNUAL_HOURS = ("00", "06", "12", "18")
DIURNAL_FILE = "eb_stunde_03987_jja_2020_2024_1h.txt"
DIURNAL_YEARS = range(2020, 2025)
DIURNAL_MONTHS = ("06", "07", "08")
METADATA = (
    "Metadaten_Geographie_03987.txt",
    "Metadaten_Geraete_Erdbodentemperatur_03987.txt",
    "Metadaten_Parameter_eb_stunde_03987.txt",
    "Metadaten_Stationsname_Betreibername_03987.txt",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stamp(line: bytes) -> str:
    """MESS_DATUM of a product line, YYYYMMDDHH."""
    return line.split(b";")[1].strip().decode("ascii")


def select(lines: list[bytes]) -> tuple[list[bytes], list[bytes]]:
    """The rows of the annual and of the diurnal file, each with the header."""
    if not lines or lines[0].rstrip(b"\r\n") != HEADER:
        raise ValueError("the product file does not start with the expected header")
    annual, diurnal = [lines[0]], [lines[0]]
    for line in lines[1:]:
        when = stamp(line)
        year, month, hour = int(when[:4]), when[4:6], when[8:10]
        if year in ANNUAL_YEARS and hour in ANNUAL_HOURS:
            annual.append(line)
        if year in DIURNAL_YEARS and month in DIURNAL_MONTHS:
            diurnal.append(line)
    return annual, diurnal


def extract(zip_path: Path, out_dir: Path, *, check_input: bool = True) -> None:
    zip_path, out_dir = Path(zip_path), Path(out_dir)
    if check_input and sha256(zip_path) != INPUT_SHA256:
        raise ValueError(
            f"{zip_path}: sha256 {sha256(zip_path)} is not the pinned {INPUT_SHA256}"
        )
    with zipfile.ZipFile(zip_path) as archive:
        if archive.testzip() is not None:
            raise ValueError(f"{zip_path}: a member fails its CRC check")
        lines = archive.read(PRODUCT).splitlines(keepends=True)
        metadata = {name: archive.read(name) for name in METADATA}
    annual, diurnal = select(lines)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / ANNUAL_FILE).write_bytes(b"".join(annual))
    (out_dir / DIURNAL_FILE).write_bytes(b"".join(diurnal))
    for name, content in metadata.items():
        (out_dir / name).write_bytes(content)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    extract(Path(argv[0]), Path(argv[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
