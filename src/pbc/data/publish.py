"""Package a measured dataset for an archive and for the repository (F145
part 3, Issue #614).

From the export folders of a measurement session and a small declaration
file (TOML), ``package`` writes, deterministically:

- the public tree ``<id>-<version>/``: every file of every export, with the
  declared fields replaced (a device's serial number by a stable device
  identifier, for example), a ``MANIFEST.tsv`` (path, bytes, SHA-256, and
  the original's SHA-256 where the file was changed), a ``README.md`` with
  the provenance, the software commits, the version, and the recommended
  citation, and a ``CITATION.cff``;
- one ZIP archive of that tree, with fixed timestamps and permissions, and
  its SHA-256 in ``<archive>.sha256``;
- ``zenodo.json``, the deposit's metadata in the form of a ``.zenodo.json``
  file (title, description, creators, licence, version, keywords, related
  identifiers);
- the repository's part ``repository/``: the declared files of every export
  and the declared raw subsets, with their own ``MANIFEST.tsv``, the same
  README and ``CITATION.cff``.

A field is replaced where the declaration names it (a file and a key path
in its JSON), never by searching for a literal value: the value to remove
is read from the input itself. The output is then searched, archive
included, for every value that was replaced, for the input folder's
absolute path, and for the home directory; a hit is an error. Nothing is
uploaded and no network or token is needed: publishing the archive is the
owner's step (``docs/datasets/README.md``, "Publishing a measured dataset").

    uv run --locked python -m pbc.data.publish --declaration <file.toml> \\
        --exports <folder of the export folders> --out <empty folder>
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import shutil
import sys
import tomllib
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

# A ZIP entry's time: the earliest the format holds, the same for every file.
ZIP_TIME = (1980, 1, 1, 0, 0, 0)
MANIFEST = "MANIFEST.tsv"
README = "README.md"
CITATION = "CITATION.cff"
EXPORTS = "exports"
WRITTEN = "written by the packager"


class PublishError(ValueError):
    """The declaration or an input does not allow a faithful package."""


@dataclass(frozen=True)
class Replacement:
    """Replace the value at ``field`` (a key path) of the JSON file ``file``
    of every export by ``value``. ``file`` is a path relative to the export,
    or a pattern of one (``M*/run.json``; ``matches``), for an export whose
    files lie in folders of their own."""

    file: str
    field: tuple[str, ...]
    value: str
    note: str = ""


@dataclass(frozen=True)
class RawSubset:
    """The rows of ``file`` (a CSV) of ``export`` whose ``column`` is one of
    ``keep``; every row when ``keep`` is empty."""

    export: str
    file: str = "raw.csv"
    column: str = "protocol"
    keep: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExportFiles:
    """The files of one export kept in the repository besides the files
    every export keeps: paths relative to the export, or patterns of them
    (``matches``); each pattern must name at least one file."""

    export: str
    files: tuple[str, ...]


def matches(relative: str, pattern: str) -> bool:
    """Whether the path ``relative`` (POSIX, relative to its export) is
    ``pattern``: a literal path, or one with ``*`` (within one folder),
    ``**`` (across folders), ``?`` and ``[...]``."""
    return PurePosixPath(relative).full_match(pattern)


@dataclass(frozen=True)
class Declaration:
    dataset_id: str
    version: str
    title: str
    description: str
    licence: str
    publication_date: str
    doi: str
    creators: tuple[dict[str, str], ...]
    keywords: tuple[str, ...]
    repository_url: str
    software: tuple[dict[str, str], ...]
    exports: tuple[str, ...]
    replacements: tuple[Replacement, ...]
    repository_files: tuple[str, ...]
    raw_subsets: tuple[RawSubset, ...]
    notes: tuple[str, ...] = ()
    related: tuple[dict[str, str], ...] = field(default=())
    export_files: tuple[ExportFiles, ...] = ()

    @property
    def root(self) -> str:
        return f"{self.dataset_id}-{self.version}"


def load_declaration(path: Path) -> Declaration:
    """The declaration in ``path``; an unknown or missing key is an error."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    known = {"dataset", "software", "exports", "replace", "repository"}
    unknown = sorted(set(data) - known)
    if unknown:
        raise PublishError(f"{path}: unknown tables {', '.join(unknown)}")
    try:
        d = data["dataset"]
        repository = data["repository"]
        declaration = Declaration(
            dataset_id=d["id"],
            version=d["version"],
            title=d["title"],
            description=d["description"].strip(),
            licence=d["licence"],
            publication_date=d["publication_date"],
            doi=d["doi"],
            creators=tuple(dict(c) for c in d["creators"]),
            keywords=tuple(d.get("keywords", ())),
            repository_url=d["repository"],
            software=tuple(dict(s) for s in data["software"]),
            exports=tuple(data["exports"]["names"]),
            replacements=tuple(
                Replacement(r["file"], tuple(r["field"]), r["value"], r.get("note", ""))
                for r in data.get("replace", ())
            ),
            repository_files=tuple(repository["files"]),
            raw_subsets=tuple(
                RawSubset(
                    r["export"],
                    r.get("file", "raw.csv"),
                    r.get("column", "protocol"),
                    tuple(r.get("keep", ())),
                )
                for r in repository.get("raw", ())
            ),
            notes=tuple(d.get("notes", ())),
            related=tuple(dict(r) for r in d.get("related", ())),
            export_files=tuple(
                ExportFiles(e["export"], tuple(e["files"]))
                for e in repository.get("export", ())
            ),
        )
    except KeyError as missing:
        raise PublishError(f"{path}: missing key {missing}") from None
    if len(set(declaration.exports)) != len(declaration.exports):
        raise PublishError(f"{path}: an export is named twice")
    for subset in declaration.raw_subsets:
        if subset.export not in declaration.exports:
            raise PublishError(
                f"{path}: raw subset of an undeclared export {subset.export}"
            )
    for kept in declaration.export_files:
        if kept.export not in declaration.exports:
            raise PublishError(f"{path}: files of an undeclared export {kept.export}")
    return declaration


# -- one file ---------------------------------------------------------------------


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_layout(text: str) -> tuple[int | None, bool]:
    """The indent and final newline with which ``json.dumps`` gives ``text``
    back byte for byte; anything else is refused, so that a replacement
    changes the declared field and nothing else."""
    value = json.loads(text)
    for indent in (None, 1, 2, 4):
        dumped = json.dumps(value, indent=indent)
        for newline in (False, True):
            if dumped + ("\n" if newline else "") == text:
                return indent, newline
    raise PublishError(
        "a JSON file not written by json.dumps cannot be edited by field"
    )


def replace_fields(
    data: bytes, replacements: list[Replacement], where: str
) -> tuple[bytes, list[str]]:
    """``data`` with every replacement applied, and the values removed."""
    text = data.decode("utf-8")
    indent, newline = _json_layout(text)
    value = json.loads(text)
    removed = []
    for r in replacements:
        node = value
        for key in r.field[:-1]:
            if not isinstance(node, dict) or key not in node:
                raise PublishError(f"{where}: no field {'.'.join(r.field)}")
            node = node[key]
        last = r.field[-1]
        if not isinstance(node, dict) or not isinstance(node.get(last), str):
            raise PublishError(f"{where}: no text field {'.'.join(r.field)}")
        if node[last] != r.value:
            removed.append(node[last])
        node[last] = r.value
    out = json.dumps(value, indent=indent) + ("\n" if newline else "")
    return out.encode("utf-8"), removed


def subset_rows(data: bytes, subset: RawSubset) -> bytes:
    """The header and the rows of ``data`` kept by ``subset``, byte for byte
    (the lines are copied, not re-written)."""
    lines = data.decode("utf-8").splitlines(keepends=True)
    header = next(csv.reader([lines[0]]))
    if subset.column not in header:
        raise PublishError(f"{subset.export}/{subset.file}: no column {subset.column}")
    column = header.index(subset.column)
    kept = [lines[0]]
    for line in lines[1:]:
        if not subset.keep or next(csv.reader([line]))[column] in subset.keep:
            kept.append(line)
    return "".join(kept).encode("utf-8")


# -- the package ------------------------------------------------------------------


@dataclass
class Entry:
    path: str
    data: bytes
    original_sha256: str | None = None  # where the file differs from its source
    derivation: str = "unchanged"


@dataclass
class Package:
    declaration: Declaration
    archive: list[Entry]
    repository: list[Entry]
    removed: set[str]
    archive_name: str = ""
    archive_bytes: int = 0
    archive_sha256: str = ""


def _export_files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*") if p.is_file())


def collect(declaration: Declaration, exports: Path) -> Package:
    """Read every export and apply the declaration, in memory."""
    archive: list[Entry] = []
    repository: list[Entry] = []
    removed: set[str] = set()
    subsets = {(s.export, s.file): s for s in declaration.raw_subsets}
    for name in declaration.exports:
        folder = exports / name
        if not folder.is_dir():
            raise PublishError(f"no export folder {name}")
        kept = [
            p for e in declaration.export_files if e.export == name for p in e.files
        ]
        used: set[str] = set()
        for path in _export_files(folder):
            relative = path.relative_to(folder).as_posix()
            raw = path.read_bytes()
            entry = Entry(f"{EXPORTS}/{name}/{relative}", raw)
            fields = [r for r in declaration.replacements if matches(relative, r.file)]
            if fields:
                data, values = replace_fields(raw, fields, f"{name}/{relative}")
                removed.update(values)
                if data != raw:
                    entry = Entry(
                        entry.path,
                        data,
                        sha256(raw),
                        "field replaced: "
                        + ", ".join(f"{'.'.join(r.field)} = {r.value}" for r in fields),
                    )
            archive.append(entry)
            subset = subsets.get((name, relative))
            if subset is not None:
                data = subset_rows(entry.data, subset)
                derivation = (
                    f"rows with {subset.column} in {', '.join(subset.keep)}"
                    if subset.keep
                    else entry.derivation
                )
                repository.append(
                    Entry(
                        entry.path,
                        data,
                        sha256(raw) if data != raw else None,
                        derivation,
                    )
                )
            elif relative in declaration.repository_files:
                repository.append(entry)
            elif any(matches(relative, pattern) for pattern in kept):
                used.update(p for p in kept if matches(relative, p))
                repository.append(entry)
        for wanted in declaration.repository_files:
            if not (folder / wanted).is_file():
                raise PublishError(f"{name}: no {wanted}")
        for pattern in kept:
            if pattern not in used:
                raise PublishError(f"{name}: no file is {pattern}")
    return Package(declaration, archive, repository, removed)


def manifest(entries: list[Entry]) -> bytes:
    out = io.StringIO()
    writer = csv.writer(out, delimiter="\t", lineterminator="\n")
    writer.writerow(["path", "bytes", "sha256", "original_sha256", "derivation"])
    for e in sorted(entries, key=lambda e: e.path):
        writer.writerow(
            [e.path, len(e.data), sha256(e.data), e.original_sha256 or "", e.derivation]
        )
    return out.getvalue().encode("utf-8")


def citation_text(d: Declaration) -> str:
    names = "; ".join(c["name"] for c in d.creators)
    year = d.publication_date[:4]
    return f"{names} ({year}). {d.title} (Version {d.version}) [Data set]. {d.licence}. https://doi.org/{d.doi}"


def citation_cff(d: Declaration) -> bytes:
    lines = [
        "cff-version: 1.2.0",
        "message: If you use this dataset, please cite it as below.",
        "type: dataset",
        f"title: {json.dumps(d.title)}",
        f"version: {json.dumps(d.version)}",
        f"date-released: {json.dumps(d.publication_date)}",
        f"license: {json.dumps(d.licence)}",
        f"doi: {json.dumps(d.doi)}",
        f"repository-code: {json.dumps(d.repository_url)}",
        "authors:",
    ]
    for c in d.creators:
        family, _, given = c["name"].partition(", ")
        lines.append(f"  - family-names: {json.dumps(family)}")
        if given:
            lines.append(f"    given-names: {json.dumps(given)}")
        if c.get("affiliation"):
            lines.append(f"    affiliation: {json.dumps(c['affiliation'])}")
    if d.keywords:
        lines.append("keywords:")
        lines += [f"  - {json.dumps(k)}" for k in d.keywords]
    return ("\n".join(lines) + "\n").encode("utf-8")


def readme(p: Package, part: str) -> bytes:
    """The README of the archive (``part`` "archive") or of the repository's
    part ("repository"), which also states the archive's size and SHA-256."""
    d = p.declaration
    lines = [f"# {d.title}", "", d.description, ""]
    lines += [
        f"- Dataset: `{d.dataset_id}`, version {d.version},"
        f" published {d.publication_date}",
        f"- Licence: {d.licence}",
        f"- DOI: {d.doi}",
        f"- Exports: {len(d.exports)}",
        "",
        "## Contents",
        "",
    ]
    if part == "archive":
        lines.append(
            f"Every file of every export, under `{EXPORTS}/<export>/`; `{MANIFEST}`"
            " lists each with its size and SHA-256, and the SHA-256 of the"
            " original for every file that was changed."
        )
    else:
        parts = [f"{', '.join(d.repository_files)} of every export"] * bool(
            d.repository_files
        )
        parts += [
            f"{', '.join(f'`{f}`' for f in e.files)} of `{e.export}`"
            for e in d.export_files
        ]
        if d.raw_subsets:
            parts.append(f"the raw subsets listed in `{MANIFEST}`")
        kept = (
            ", and ".join(parts)
            if len(parts) <= 2
            else "; ".join(parts[:-1]) + "; and " + parts[-1]
        )
        lines.append(
            "The part of the archive kept in the repository, under"
            f" `{EXPORTS}/<export>/`:"
            f" {kept}. The complete files are in the archive"
            f" `{p.archive_name}` ({p.archive_bytes} bytes,"
            f" SHA-256 {p.archive_sha256})."
        )
    lines += ["", "## Changes to the exported files", ""]
    if d.replacements:
        for r in d.replacements:
            lines.append(
                f"- `{r.file}`, field `{'.'.join(r.field)}`: replaced by `{r.value}`."
                + (f" {r.note}" if r.note else "")
            )
        lines.append(
            "- Digests recorded inside the files (a checkpoint digest, the SHA-256"
            " of an artifact) refer to the original files and were not rewritten;"
            f" `{MANIFEST}` gives the original's SHA-256 beside the published one."
        )
    else:
        lines.append("- None.")
    if part == "repository" and d.raw_subsets:
        lines.append(
            "- A raw subset holds the header and the rows named in its derivation,"
            " copied line by line from the published file."
        )
    lines += ["", "## Provenance", ""]
    lines += [f"- {note}" for note in d.notes]
    lines += ["", "## Software", ""]
    for s in d.software:
        lines.append(
            f"- {d.repository_url}/commit/{s['commit']}: {s['description']}"
            + (f" (code digest {s['code_digest']})" if s.get("code_digest") else "")
        )
    lines += ["", "## Citation", "", citation_text(d), ""]
    return "\n".join(lines).encode("utf-8")


def zenodo_metadata(d: Declaration) -> dict[str, Any]:
    related = [
        {
            "identifier": f"{d.repository_url}/commit/{s['commit']}",
            "relation": "isDerivedFrom",
            "resource_type": "software",
            "scheme": "url",
        }
        for s in d.software
    ]
    related.append(
        {"identifier": d.repository_url, "relation": "isSupplementTo", "scheme": "url"}
    )
    related += [dict(r) for r in d.related]
    return {
        "title": d.title,
        "upload_type": "dataset",
        "description": d.description,
        "creators": [dict(c) for c in d.creators],
        "license": d.licence.lower(),
        "version": d.version,
        "publication_date": d.publication_date,
        "keywords": list(d.keywords),
        "related_identifiers": related,
        "access_right": "open",
    }


def zip_bytes(root: str, entries: list[Entry]) -> bytes:
    """A ZIP of ``entries`` under ``root/``, the same bytes for the same
    entries: sorted, fixed time, fixed permissions, no host metadata."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for e in sorted(entries, key=lambda e: e.path):
            info = zipfile.ZipInfo(f"{root}/{e.path}", date_time=ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            archive.writestr(info, e.data, compresslevel=9)
    return buffer.getvalue()


def build(declaration: Declaration, exports: Path) -> tuple[Package, dict[str, bytes]]:
    """The package and every output file by its path under the output folder."""
    p = collect(declaration, exports)
    d = declaration
    tree = list(p.archive)
    tree.append(Entry(CITATION, citation_cff(d), derivation=WRITTEN))
    tree.append(Entry(README, readme(p, "archive"), derivation=WRITTEN))
    tree.append(Entry(MANIFEST, manifest(tree), derivation=WRITTEN))
    archive = zip_bytes(d.root, tree)
    p.archive_name = f"{d.root}.zip"
    p.archive_bytes = len(archive)
    p.archive_sha256 = sha256(archive)
    repository = list(p.repository)
    repository.append(Entry(CITATION, citation_cff(d), derivation=WRITTEN))
    repository.append(Entry(README, readme(p, "repository"), derivation=WRITTEN))
    repository.append(Entry(MANIFEST, manifest(repository), derivation=WRITTEN))
    files: dict[str, bytes] = {f"{d.root}/{e.path}": e.data for e in tree}
    files[p.archive_name] = archive
    files[f"{p.archive_name}.sha256"] = (
        f"{p.archive_sha256}  {p.archive_name}\n".encode()
    )
    files["zenodo.json"] = (
        json.dumps(zenodo_metadata(d), indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    files.update({f"repository/{e.path}": e.data for e in repository})
    leaks = leaked(files, p.removed, [str(exports.resolve()), str(Path.home())])
    if leaks:
        raise PublishError(
            "the output still holds a removed value: " + ", ".join(leaks)
        )
    return p, files


def leaked(files: dict[str, bytes], removed: set[str], paths: list[str]) -> list[str]:
    """The output files (inside the archive too) that contain a removed
    value or a host path, by name only (never the value)."""
    needles = [v.encode("utf-8") for v in removed if v]
    needles += [p.encode("utf-8") for p in paths if len(p) > 1]
    found = []
    for name, data in sorted(files.items()):
        bodies = [data]
        if name.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                bodies += [z.read(n) for n in z.namelist()]
                bodies.append("\n".join(z.namelist()).encode("utf-8"))
        if any(n in body for body in bodies for n in needles):
            found.append(name)
    return found


def package(declaration: Path, exports: Path, out: Path) -> Package:
    """Write the package to ``out``, which must be empty or absent."""
    if out.exists() and any(out.iterdir()):
        raise PublishError(f"{out} is not empty")
    p, files = build(load_declaration(declaration), exports)
    for name, data in files.items():
        path = out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return p


def install(source: Path, target: Path) -> None:
    """Replace ``target`` (the repository's sample folder) by ``source``
    (a package's ``repository/``)."""
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m pbc.data.publish")
    parser.add_argument("--declaration", type=Path, required=True)
    parser.add_argument("--exports", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--install",
        type=Path,
        default=None,
        help="copy the repository's part to this folder (data/samples/<id>)",
    )
    arguments = parser.parse_args(argv)
    try:
        p = package(arguments.declaration, arguments.exports, arguments.out)
    except PublishError as error:
        print(f"refused: {error}", file=sys.stderr)
        return 1
    if arguments.install is not None:
        install(arguments.out / "repository", arguments.install)
    print(
        f"archive: {p.archive_name}, {p.archive_bytes} bytes, sha256 {p.archive_sha256}"
    )
    print(
        f"files: {len(p.archive)} in the archive, {len(p.repository)} in the repository"
    )
    print(f"replaced values: {len(p.removed)}; none left in the output")
    return 0


if __name__ == "__main__":
    sys.exit(main())
