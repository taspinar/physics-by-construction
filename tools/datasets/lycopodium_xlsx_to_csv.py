"""Convert one Lycopodium intensity-profile XLSX file to the CSV sample.

    python tools/datasets/lycopodium_xlsx_to_csv.py INPUT.xlsx OUTPUT.csv

The one-time conversion of the dataset ``lycopodium-spore-diffraction``
(ADR 007, addendum of Issue #417: an XLSX file is converted once, outside the
build, by a documented, checksum-pinned script). The build, the verification,
and CI never run it; the committed samples are its output.

An XLSX file is a zip archive of XML parts. The script reads it with the
standard library alone (no spreadsheet library is a dependency of the
project): the shared strings ``xl/sharedStrings.xml`` and the one worksheet
``xl/worksheets/sheet1.xml``. Before converting it checks

- the SHA-256 of the input against ``INPUTS`` (the two files inspected for the
  dossier; any other file is refused),
- that the workbook has exactly one worksheet, that its first row is the
  title ``profile_A`` and its second the header ``n, x, y, luma`` (the export
  of a line profile by the Tracker software), and
- that every later row has a number in each of the four columns, ``n``
  counting 0, 1, 2, ... without a gap.

The CSV has one row per row of the sheet, in its order, nothing dropped or
changed: ``n`` as an integer, ``x``, ``y`` and ``luma`` as the shortest
decimal that reads back to the same float64 as the number stored in the
sheet. Two comment lines name the source file, its checksum, and the
conversion; a third says that the record states no unit.
"""

import hashlib
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

INPUTS = {
    "Intensity_profile_diffraction_lambda0.6328um.xlsx": (
        "2efdb178052814c982f3870746cf3173c671d1a997765b02af06335e0c496b87"
    ),
    "Intensity_profile_diffraction_lambda0.405um.xlsx": (
        "f7b6caf8daf2c90c2cb923515a3e55a2700d91e11373ca50714f193e83083e56"
    ),
}
HEADER = ("n", "x", "y", "luma")
TITLE = "profile_A"
_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_COLUMN = re.compile(r"^([A-Z]+)(\d+)$")


def _text(element) -> str:
    return "".join(t.text or "" for t in element.iter(f"{{{_NS['m']}}}t"))


def read_rows(path: Path) -> list[dict[str, str]]:
    """The cells of the one worksheet, a dict of column letter -> text per row
    (shared strings resolved)."""
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        sheets = sorted(n for n in names if n.startswith("xl/worksheets/sheet"))
        if sheets != ["xl/worksheets/sheet1.xml"]:
            raise ValueError(f"{path}: expected one worksheet, found {sheets}")
        strings = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            strings = [_text(si) for si in root.findall("m:si", _NS)]
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    rows = []
    for row in sheet.find("m:sheetData", _NS):
        cells = {}
        for cell in row:
            column = _COLUMN.match(cell.get("r")).group(1)
            value = cell.find("m:v", _NS)
            if value is None:
                continue
            kind = cell.get("t")
            if kind == "s":
                cells[column] = strings[int(value.text)]
            elif kind in (None, "n"):
                cells[column] = value.text
            else:
                raise ValueError(f"{path}: cell {cell.get('r')} has type {kind!r}")
        rows.append(cells)
    return rows


def table(rows: list[dict[str, str]]) -> list[tuple[int, float, float, float]]:
    """The profile rows as (n, x, y, luma), after checking title and header."""
    if rows[0] != {"A": TITLE}:
        raise ValueError(f"the first row is {rows[0]}, not the title {TITLE!r}")
    if tuple(rows[1].get(c) for c in "ABCD") != HEADER or len(rows[1]) != 4:
        raise ValueError(f"the header is {rows[1]}, not {HEADER}")
    out = []
    for k, row in enumerate(rows[2:]):
        if sorted(row) != ["A", "B", "C", "D"]:
            raise ValueError(f"row {k + 3} has the columns {sorted(row)}")
        n = float(row["A"])
        if n != k:
            raise ValueError(f"row {k + 3}: n is {row['A']}, expected {k}")
        out.append((k, float(row["B"]), float(row["C"]), float(row["D"])))
    return out


def convert(xlsx_path: Path, csv_path: Path, *, check_input: bool = True) -> None:
    xlsx_path = Path(xlsx_path)
    digest = hashlib.sha256(xlsx_path.read_bytes()).hexdigest()
    if check_input and INPUTS.get(xlsx_path.name) != digest:
        raise ValueError(f"{xlsx_path}: sha256 {digest} is not a pinned input")
    rows = table(read_rows(xlsx_path))
    lines = [
        f"# source: {xlsx_path.name} (sha256 {digest}), sheet 1 '{TITLE}'",
        "# converted by tools/datasets/lycopodium_xlsx_to_csv.py; every row,"
        " values unchanged (shortest decimal of the stored float64)",
        "# units: not stated in the record; n is the sample index, x and y the"
        " Tracker coordinates of the scanline, luma the brightness 0 to 255",
        ",".join(HEADER),
    ]
    lines += [f"{n},{x!r},{y!r},{luma!r}" for n, x, y, luma in rows]
    Path(csv_path).write_text("\n".join(lines) + "\n", encoding="ascii")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.splitlines()[2].strip(), file=sys.stderr)
        return 2
    convert(Path(argv[0]), Path(argv[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
