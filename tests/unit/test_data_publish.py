"""The packager of a measured dataset (``pbc.data.publish``, F145 part 3,
Issue #614), on a tiny synthetic export: the same input gives the same
archive byte for byte, a declared field is replaced and nothing else, the
output is searched for every removed value, and the repository's part is
the declared subset."""

import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from pbc.data import publish

# A made-up identifier of a made-up device, standing in for a serial.
SECRET = "UNIT-TEST-DEVICE-0042"

DECLARATION = """
[dataset]
id = "tiny-bench"
version = "0.1.0"
title = "A tiny bench"
description = "Two synthetic exports."
licence = "CC-BY-4.0"
publication_date = "2026-01-02"
doi = "NOT-YET-RESERVED"
repository = "https://example.org/repo"
keywords = ["test"]
notes = ["Synthetic."]

[[dataset.creators]]
name = "Doe, Jane"

[[software]]
commit = "0000000000000000000000000000000000000000"
description = "the code"

[exports]
names = ["a", "b"]

[[replace]]
file = "run.json"
field = ["run", "device", "serial"]
value = "DEV-001"

[[replace]]
file = "checkpoints/checkpoint.json"
field = ["bench", "serial"]
value = "DEV-001"

[repository]
files = ["run.json", "measurements.csv"]

[[repository.raw]]
export = "a"
keep = ["frequency-response"]
"""


def make_export(folder: Path, name: str) -> None:
    root = folder / name
    (root / "checkpoints").mkdir(parents=True)
    run = {"run": {"device": {"device": "a scope", "serial": SECRET}, "started": name}}
    (root / "run.json").write_text(json.dumps(run, indent=2) + "\n")
    (root / "checkpoints" / "checkpoint.json").write_text(
        json.dumps({"bench": {"serial": SECRET}, "records": [1, 2]}) + "\n"
    )
    (root / "measurements.csv").write_text("record,valid\nm001,1\n")
    (root / "raw.csv").write_text(
        "record,protocol,t_s\n"
        "m001,frequency-response,0\n"
        "m002,transient,0\n"
        "m003,frequency-response,1e-06\n"
    )
    (root / "report.md").write_text(f"# {name}\n")


@pytest.fixture
def inputs(tmp_path):
    exports = tmp_path / "exports"
    for name in ("a", "b"):
        make_export(exports, name)
    declaration = tmp_path / "tiny.toml"
    declaration.write_text(DECLARATION)
    return declaration, exports


def test_the_same_input_gives_the_same_archive_byte_for_byte(inputs, tmp_path):
    declaration, exports = inputs
    first = publish.package(declaration, exports, tmp_path / "one")
    # The files' times change; the archive does not.
    for path in exports.rglob("*"):
        path.touch()
    second = publish.package(declaration, exports, tmp_path / "two")
    one = (tmp_path / "one" / first.archive_name).read_bytes()
    two = (tmp_path / "two" / second.archive_name).read_bytes()
    assert one == two
    assert first.archive_sha256 == hashlib.sha256(one).hexdigest()
    with zipfile.ZipFile(io.BytesIO(one)) as archive:
        infos = archive.infolist()
    assert [i.filename for i in infos] == sorted(i.filename for i in infos)
    assert {i.date_time for i in infos} == {publish.ZIP_TIME}
    assert all(i.filename.startswith("tiny-bench-0.1.0/") for i in infos)
    sidecar = (tmp_path / "one" / f"{first.archive_name}.sha256").read_text()
    assert sidecar.split()[0] == first.archive_sha256


def test_a_declared_field_is_replaced_and_nothing_else(inputs, tmp_path):
    declaration, exports = inputs
    publish.package(declaration, exports, tmp_path / "out")
    tree = tmp_path / "out" / "tiny-bench-0.1.0"
    original = exports / "a" / "run.json"
    published = tree / "exports" / "a" / "run.json"
    expected = json.loads(original.read_text())
    expected["run"]["device"]["serial"] = "DEV-001"
    assert published.read_text() == json.dumps(expected, indent=2) + "\n"
    checkpoint = json.loads(
        (tree / "exports/a/checkpoints/checkpoint.json").read_text()
    )
    assert checkpoint == {"bench": {"serial": "DEV-001"}, "records": [1, 2]}
    assert (tree / "exports/a/raw.csv").read_bytes() == (
        exports / "a/raw.csv"
    ).read_bytes()
    with (tree / publish.MANIFEST).open() as handle:
        rows = {r["path"]: r for r in csv.DictReader(handle, delimiter="\t")}
    row = rows["exports/a/run.json"]
    assert row["original_sha256"] == hashlib.sha256(original.read_bytes()).hexdigest()
    assert row["sha256"] == hashlib.sha256(published.read_bytes()).hexdigest()
    assert rows["exports/a/report.md"]["original_sha256"] == ""
    # Every published file, the archive and the metadata included, is free
    # of the removed value.
    for path in (tmp_path / "out").rglob("*"):
        if path.is_file():
            assert SECRET.encode() not in path.read_bytes()
    with zipfile.ZipFile(tmp_path / "out" / "tiny-bench-0.1.0.zip") as archive:
        assert all(SECRET.encode() not in archive.read(n) for n in archive.namelist())


def test_a_removed_value_left_in_another_file_refuses_the_package(inputs, tmp_path):
    declaration, exports = inputs
    (exports / "b" / "report.md").write_text(f"measured on {SECRET}\n")
    with pytest.raises(publish.PublishError, match="removed value") as refused:
        publish.package(declaration, exports, tmp_path / "out")
    assert SECRET not in str(refused.value)
    assert not (tmp_path / "out").exists()


def test_a_json_file_not_written_by_json_dumps_is_refused(inputs, tmp_path):
    declaration, exports = inputs
    (exports / "a" / "run.json").write_text('{"run": {"device": {"serial": "x"}}}  \n')
    with pytest.raises(publish.PublishError, match=r"json\.dumps"):
        publish.package(declaration, exports, tmp_path / "out")


def test_a_missing_field_or_export_is_refused(inputs, tmp_path):
    declaration, exports = inputs
    (exports / "b" / "run.json").write_text(json.dumps({"run": {}}) + "\n")
    with pytest.raises(publish.PublishError, match=r"no field run\.device\.serial"):
        publish.package(declaration, exports, tmp_path / "out")
    make_export(tmp_path / "other", "a")
    with pytest.raises(publish.PublishError, match="no export folder b"):
        publish.package(declaration, tmp_path / "other", tmp_path / "out2")


def test_the_repository_part_is_the_declared_subset(inputs, tmp_path):
    declaration, exports = inputs
    package = publish.package(declaration, exports, tmp_path / "out")
    repository = tmp_path / "out" / "repository"
    files = sorted(
        p.relative_to(repository).as_posix()
        for p in repository.rglob("*")
        if p.is_file()
    )
    assert files == [
        publish.CITATION,
        publish.MANIFEST,
        publish.README,
        "exports/a/measurements.csv",
        "exports/a/raw.csv",
        "exports/a/run.json",
        "exports/b/measurements.csv",
        "exports/b/run.json",
    ]
    raw = (repository / "exports/a/raw.csv").read_text()
    assert (
        raw == "record,protocol,t_s\n"
        "m001,frequency-response,0\n"
        "m003,frequency-response,1e-06\n"
    )
    readme = (repository / publish.README).read_text()
    assert package.archive_sha256 in readme and str(package.archive_bytes) in readme
    with (repository / publish.MANIFEST).open() as handle:
        rows = {r["path"]: r for r in csv.DictReader(handle, delimiter="\t")}
    assert (
        rows["exports/a/raw.csv"]["derivation"]
        == "rows with protocol in frequency-response"
    )
    assert (
        rows["exports/a/raw.csv"]["original_sha256"]
        == hashlib.sha256((exports / "a/raw.csv").read_bytes()).hexdigest()
    )


def test_the_metadata_names_the_licence_version_creators_and_commits(inputs, tmp_path):
    declaration, exports = inputs
    publish.package(declaration, exports, tmp_path / "out")
    zenodo = json.loads((tmp_path / "out" / "zenodo.json").read_text())
    assert zenodo["license"] == "cc-by-4.0"
    assert zenodo["version"] == "0.1.0"
    assert zenodo["creators"] == [{"name": "Doe, Jane"}]
    assert {r["identifier"] for r in zenodo["related_identifiers"]} == {
        "https://example.org/repo/commit/0000000000000000000000000000000000000000",
        "https://example.org/repo",
    }
    cff = (tmp_path / "out" / "tiny-bench-0.1.0" / publish.CITATION).read_text()
    assert 'family-names: "Doe"' in cff and 'doi: "NOT-YET-RESERVED"' in cff


def test_an_output_folder_that_is_not_empty_is_refused(inputs, tmp_path):
    declaration, exports = inputs
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "keep.txt").write_text("mine")
    with pytest.raises(publish.PublishError, match="not empty"):
        publish.package(declaration, exports, tmp_path / "out")
    assert (
        publish.main(
            [
                "--declaration",
                str(declaration),
                "--exports",
                str(exports),
                "--out",
                str(tmp_path / "out"),
            ]
        )
        == 1
    )


# A session whose sweeps lie in folders of their own (F155 part 2b, Issue
# #619): the replaced field's file is a pattern, and the repository keeps
# the files one export's list names.
NESTED = """
[dataset]
id = "tiny-session"
version = "0.1.0"
title = "A tiny session"
description = "One session folder with two sweeps."
licence = "CC-BY-4.0"
publication_date = "2026-01-02"
doi = "NOT-YET-RESERVED"
repository = "https://example.org/repo"

[[dataset.creators]]
name = "Doe, Jane"

[[software]]
commit = "0000000000000000000000000000000000000000"
description = "the code"

[exports]
names = ["session"]

[[replace]]
file = "M*/run.json"
field = ["run", "device", "serial"]
value = "DEV-001"

[repository]
files = []

[[repository.export]]
export = "session"
files = ["session.toml", "M*/run.json", "M2/raw.csv"]
"""


def make_session(folder: Path) -> None:
    root = folder / "session"
    for sweep in ("M1", "M2"):
        (root / sweep).mkdir(parents=True)
        run = {"run": {"device": {"serial": SECRET}, "started": sweep}}
        (root / sweep / "run.json").write_text(json.dumps(run, indent=1) + "\n")
        (root / sweep / "raw.csv").write_text(f"point,t_s\n1,{sweep}\n")
    (root / "session.toml").write_text('[session]\nplugged_in = "x"\n')
    (root / "note.md").write_text("a note\n")


def test_a_pattern_replaces_the_field_in_every_sweep_and_lists_keep_one_exports_files(
    tmp_path,
):
    make_session(tmp_path / "exports")
    declaration = tmp_path / "nested.toml"
    declaration.write_text(NESTED)
    package = publish.package(declaration, tmp_path / "exports", tmp_path / "out")
    assert package.removed == {SECRET}
    tree = tmp_path / "out" / "tiny-session-0.1.0" / "exports" / "session"
    for sweep in ("M1", "M2"):
        run = json.loads((tree / sweep / "run.json").read_text())
        assert run["run"]["device"]["serial"] == "DEV-001"
    repository = tmp_path / "out" / "repository"
    assert sorted(
        p.relative_to(repository).as_posix()
        for p in repository.rglob("*")
        if p.is_file()
    ) == [
        publish.CITATION,
        publish.MANIFEST,
        publish.README,
        "exports/session/M1/run.json",
        "exports/session/M2/raw.csv",
        "exports/session/M2/run.json",
        "exports/session/session.toml",
    ]
    readme = (repository / publish.README).read_text()
    assert "`session.toml`, `M*/run.json`, `M2/raw.csv` of `session`." in readme
    assert "raw subsets" not in readme and "A raw subset" not in readme


def test_a_pattern_of_one_exports_list_that_names_no_file_is_refused(tmp_path):
    make_session(tmp_path / "exports")
    declaration = tmp_path / "nested.toml"
    declaration.write_text(NESTED.replace('"M2/raw.csv"', '"M3/raw.csv"'))
    with pytest.raises(publish.PublishError, match=r"no file is M3/raw\.csv"):
        publish.package(declaration, tmp_path / "exports", tmp_path / "out")
    declaration.write_text(NESTED.replace('export = "session"', 'export = "other"'))
    with pytest.raises(publish.PublishError, match="undeclared export other"):
        publish.package(declaration, tmp_path / "exports", tmp_path / "out2")


def test_the_pattern_matches_within_one_folder_and_a_literal_path_exactly():
    assert publish.matches("M1/run.json", "M*/run.json")
    assert not publish.matches("run.json", "M*/run.json")
    assert not publish.matches("evaluation/run.json", "M*/run.json")
    assert publish.matches("run.json", "run.json")
    assert not publish.matches("M1/run.json", "run.json")
    assert publish.matches("checkpoints/checkpoint.json", "checkpoints/checkpoint.json")
