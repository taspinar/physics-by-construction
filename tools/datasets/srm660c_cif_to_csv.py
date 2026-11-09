"""Convert the 20 CIFs of the NIST SRM 660c release to the CSV sample.

    python tools/datasets/srm660c_cif_to_csv.py INPUT.zip OUTPUT_DIR

The one-time conversion of the dataset ``nist-srm660c-lab6`` (ADR 007,
addendum of Issue #417: a CIF file is converted once, outside the build, by a
documented, checksum-pinned script). The build, the verification, and CI
never run it; the committed samples are its output.

The input is the zip of the record, ``srm_660c_cifs_20201029_081700.zip``:
20 CIFs, one per specimen (two specimens from each of ten bottles), and a
``__MACOSX`` folder of Finder metadata that is ignored. Each CIF is read with
the standard library alone (no CIF library is a dependency of the project).
Before converting, the script checks

- the SHA-256 of the zip against ``INPUT_SHA256`` (the file inspected for the
  dossier, as NIST publishes it; any other file is refused),
- that the zip holds exactly the 20 CIFs of ``SPECIMENS``,
- that each CIF has a measured block ``..._meas`` and a calculated block
  ``..._calc``, each a loop of the three items ``_pd_proc_2theta_corrected``,
  ``_pd_proc_intensity_total``, ``_pd_proc_ls_weight`` with as many rows as
  its ``_pd_proc_number_of_points``, every token a number, and
- that the two blocks share the same 2θ tokens, row by row.

Per specimen the CSV ``660c_<specimen>.csv`` has one row per row of the
blocks, in their order, nothing dropped: ``two_theta``, ``intensity`` and
``weight`` of the measured block and ``calc_intensity`` of the calculated
one, each the token of the CIF unchanged. The weight of the calculated block
(NIST's least-squares weight for its model) is not carried. Three comment
lines name the source, its checksums, the conversion, and the units the CIF
implies. ``specimens.csv`` has one row per specimen with the CIF's specimen
temperature, vertical specimen displacement, NIST's refined lattice
parameter, and the number of points, each token unchanged.
"""

import hashlib
import re
import sys
import zipfile
from pathlib import Path

ZIP_NAME = "srm_660c_cifs_20201029_081700.zip"
INPUT_SHA256 = "92034d06498161db365420831fe35d91ec18bad4ed17385329a1761658da2c42"
SPECIMENS = tuple(f"{b}{s}" for b in range(100, 1001, 100) for s in "ab")
MEMBER = "660_cert_cif_mosaic_consensus_{}.cif"
LOOP = (
    "_pd_proc_2theta_corrected",
    "_pd_proc_intensity_total",
    "_pd_proc_ls_weight",
)
HEADER = ("two_theta", "intensity", "weight", "calc_intensity")
SPECIMEN_ITEMS = (
    ("temperature_c", "pd_spec_{}", "_pd_spec_temperature"),
    ("vertical_displacement_mm", "pd_spec_{}", "_pd_spec_vertical_displacement_mm"),
    ("cell_length_a_angstrom", "cell_LaB6_660c", "_cell_length_a"),
    ("points", "pd_proc_{}_meas", "_pd_proc_number_of_points"),
)
_NUMBER = re.compile(r"^-?\d+(\.\d*)?([eE][-+]?\d+)?$")


def parse_cif(text: str) -> dict[str, dict]:
    """The data blocks of a CIF: per block its single items (name -> token)
    and, for the one loop of ``LOOP``, its rows of tokens.

    Only what these files use is read: ``data_`` headers, single-line items
    ``_name value``, and the pattern loop; other loops (citations, atom
    sites) are skipped, and a multi-line text field between ``;`` lines is
    skipped as a whole.
    """
    blocks: dict[str, dict] = {}
    block = None
    in_text = False
    tags: list[str] | None = None  # the tags of the current loop
    rows_started = False
    for line in text.splitlines():
        if line.startswith(";"):
            in_text = not in_text
            continue
        if in_text:
            continue
        stripped = line.strip()
        if line.startswith("data_"):
            block = {"items": {}, "rows": []}
            blocks[line[5:].strip()] = block
            tags = None
            continue
        if block is None or not stripped or stripped.startswith("#"):
            continue
        if stripped == "loop_":
            tags, rows_started = [], False
            continue
        if stripped.startswith("_"):
            parts = stripped.split(None, 1)
            if tags is not None and not rows_started and len(parts) == 1:
                tags.append(parts[0])
                continue
            tags = None
            if len(parts) == 2:
                block["items"][parts[0]] = parts[1].strip()
            continue
        if tags is None:
            continue
        rows_started = True
        if tuple(tags) == LOOP:
            tokens = stripped.split()
            if len(tokens) != len(LOOP) or not all(map(_NUMBER.match, tokens)):
                raise ValueError(f"a pattern row is not three numbers: {line!r}")
            block["rows"].append(tokens)
    return blocks


def specimen_tables(text: str, specimen: str) -> tuple[list[list[str]], dict]:
    """The rows (two_theta, intensity, weight, calc_intensity) and the items
    of ``specimens.csv`` of one CIF, after the checks of the module."""
    stem = MEMBER.format(specimen)[:-4]
    blocks = parse_cif(text)
    patterns = []
    for kind in ("meas", "calc"):
        name = f"pd_proc_{stem}_{kind}"
        if name not in blocks:
            raise ValueError(f"{stem}: no block {name}")
        rows = blocks[name]["rows"]
        declared = int(blocks[name]["items"]["_pd_proc_number_of_points"])
        if len(rows) != declared:
            raise ValueError(f"{name}: {len(rows)} rows, declared {declared}")
        patterns.append(rows)
    meas, calc = patterns
    for k, (m, c) in enumerate(zip(meas, calc, strict=True)):
        if m[0] != c[0]:
            raise ValueError(f"{stem}: row {k}: 2theta {m[0]} and {c[0]} differ")
    rows = [[m[0], m[1], m[2], c[1]] for m, c in zip(meas, calc, strict=True)]
    items = {"specimen": specimen}
    for column, block, item in SPECIMEN_ITEMS:
        items[column] = blocks[block.format(stem)]["items"][item]
    return rows, items


def convert(zip_path: Path, out_dir: Path, *, check_input: bool = True) -> None:
    zip_path, out_dir = Path(zip_path), Path(out_dir)
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    if check_input and digest != INPUT_SHA256:
        raise ValueError(f"{zip_path}: sha256 {digest} is not the pinned input")
    with zipfile.ZipFile(zip_path) as archive:
        members = sorted(n for n in archive.namelist() if not n.startswith("__MACOSX/"))
        expected = sorted(MEMBER.format(s) for s in SPECIMENS)
        if members != expected:
            raise ValueError(f"{zip_path}: members {members}, expected {expected}")
        texts = {s: archive.read(MEMBER.format(s)) for s in SPECIMENS}
    out_dir.mkdir(parents=True, exist_ok=True)
    table = []
    for specimen in SPECIMENS:
        data = texts[specimen]
        member = MEMBER.format(specimen)
        rows, items = specimen_tables(data.decode("ascii"), specimen)
        table.append(items)
        lines = [
            f"# source: {ZIP_NAME} (sha256 {digest}), member {member}"
            f" (sha256 {hashlib.sha256(data).hexdigest()})",
            "# converted by tools/datasets/srm660c_cif_to_csv.py; every row of the"
            " blocks _meas (two_theta, intensity, weight) and _calc (calc_intensity),"
            " tokens unchanged",
            "# units: two_theta in degrees (_pd_proc_2theta_corrected); intensity"
            " counts over counting time; weight 1/sigma^2 of intensity; calc_intensity"
            " NIST's fundamental-parameters model in the units of intensity",
            ",".join(HEADER),
        ]
        lines += [",".join(row) for row in rows]
        (out_dir / f"660c_{specimen}.csv").write_text(
            "\n".join(lines) + "\n", encoding="ascii"
        )
    columns = ["specimen"] + [c for c, _, _ in SPECIMEN_ITEMS]
    lines = [
        f"# source: {ZIP_NAME} (sha256 {digest}), one row per CIF",
        "# converted by tools/datasets/srm660c_cif_to_csv.py; items"
        " _pd_spec_temperature (deg C), _pd_spec_vertical_displacement_mm (mm),"
        " _cell_length_a (angstrom,"
        " NIST's refinement), _pd_proc_number_of_points; tokens unchanged",
        ",".join(columns),
    ]
    lines += [",".join(items[c] for c in columns) for items in table]
    (out_dir / "specimens.csv").write_text("\n".join(lines) + "\n", encoding="ascii")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.splitlines()[2].strip(), file=sys.stderr)
        return 2
    convert(Path(argv[0]), Path(argv[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
