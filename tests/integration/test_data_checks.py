"""The dataset check fails on each input that violates it, the repository passes
it, and nothing a build or a check runs reaches a data portal (ADR 007; I6, I20).
"""

import ast
import copy
import hashlib
import os
import re
import shutil
import socket
import stat
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

from pbc.data import check
from pbc.data.card import ARTIFACT_TYPES, load_cards, validate_card
from pbc.data.check import check_repository

ROOT = Path(__file__).parents[2]
SAMPLE = (
    ROOT / "data/samples/npl-onwafer-sparameters/coaxial_3dB_attenuator_0601_CORR.s2p"
)
CARDS = load_cards(ROOT / "data/registry")
SPIKED = ("gw150914-strain", "aalborg-submerged-bar", "npl-onwafer-sparameters")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Repo:
    """A minimal repository with one valid dataset 'demo' and its parsing test."""

    def __init__(self, root: Path):
        self.root = root
        card = copy.deepcopy(CARDS["npl-onwafer-sparameters"])
        card["id"] = "demo"
        card["dossier"] = "docs/datasets/demo.md"
        card["samples"] = []
        self.card = card
        (root / "docs/datasets").mkdir(parents=True)
        (root / "docs/datasets/demo.md").write_text("# demo\n")
        (root / "tests/unit").mkdir(parents=True)
        (root / "tests/unit/test_demo.py").write_text(
            "def test_demo_parses():\n    pass\n"
        )
        (root / "data/registry").mkdir(parents=True)
        (root / "data/samples/demo").mkdir(parents=True)
        self.add_sample("a.s2p", SAMPLE.read_bytes())
        self.write()

    def add_sample(self, name: str, content: bytes):
        path = self.root / "data/samples/demo" / name
        path.write_bytes(content)
        self.card["samples"].append(
            {
                "path": name,
                "sha256": hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
                "derivation": "unchanged copy",
                "test": "tests/unit/test_demo.py::test_demo_parses",
            }
        )

    def write(self):
        text = yaml.safe_dump(self.card, sort_keys=False)
        (self.root / "data/registry/demo.yaml").write_text(text)

    def problems(self) -> list[str]:
        return check_repository(self.root)


@pytest.fixture
def repo(tmp_path) -> Repo:
    return Repo(tmp_path)


def test_the_valid_minimal_repository_passes(repo):
    assert repo.problems() == []


def test_a_sample_without_a_card_fails(repo):
    (repo.root / "data/registry/demo.yaml").unlink()
    assert any("no card" in p for p in repo.problems())


def test_a_sample_above_the_cap_per_file_fails(repo):
    repo.add_sample("big.bin", b"x" * (check.MAX_FILE + 1))
    repo.write()
    assert any("exceeds the" in p and "per file" in p for p in repo.problems())


def test_samples_above_the_cap_per_dataset_fail(repo):
    for k in range(5):
        repo.add_sample(f"part{k}.bin", bytes([k]) * (check.MAX_FILE - 1024))
    repo.write()
    assert any("per dataset" in p for p in repo.problems())


def test_samples_above_the_cap_for_all_datasets_fail(repo, monkeypatch):
    monkeypatch.setattr(check, "MAX_ALL", 1000)
    assert any("for all samples" in p for p in repo.problems())


def test_the_caps_are_those_of_the_architecture():
    mib = 1024 * 1024
    assert (
        2 * mib,
        8 * mib,
        32 * mib,
    ) == (check.MAX_FILE, check.MAX_DATASET, check.MAX_ALL)


def test_a_checksum_mismatch_fails(repo):
    path = repo.root / "data/samples/demo/a.s2p"
    path.write_bytes(path.read_bytes() + b"! tampered\n")
    problems = repo.problems()
    assert any("checksum differs" in p for p in problems)


@pytest.mark.parametrize(
    "change",
    [
        lambda c: c["rights"].update(licence="CC-BY-NC-4.0"),
        lambda c: c["rights"].update(licence="not-assessed"),
        lambda c: c["rights"]["redistribution_of_subsets"].update(answer="unclear"),
        lambda c: c["rights"]["redistribution_of_subsets"].update(answer="restricted"),
        lambda c: c["decision"].update(value="defer"),
    ],
)
def test_a_sample_whose_rights_do_not_permit_redistribution_fails(repo, change):
    change(repo.card)
    repo.write()
    assert repo.problems(), "the sample must not be accepted"


def test_a_sample_without_a_parsing_test_fails(repo):
    (repo.root / "tests/unit/test_demo.py").write_text("def test_other():\n    pass\n")
    assert any("parsing test" in p for p in repo.problems())


def test_a_sample_the_card_does_not_declare_fails(repo):
    (repo.root / "data/samples/demo/extra.txt").write_text("x")
    assert any("not declared" in p for p in repo.problems())


def test_a_declared_sample_that_is_not_committed_fails(repo):
    (repo.root / "data/samples/demo/a.s2p").unlink()
    assert any("declared in the card, not committed" in p for p in repo.problems())


def test_a_dossier_that_does_not_exist_fails(repo):
    (repo.root / "docs/datasets/demo.md").unlink()
    assert any("dossier" in p for p in repo.problems())


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        (lambda c: c.pop("title"), "title"),
        (lambda c: c["source"].pop("url"), "source.url"),
        (lambda c: c["source"].update(accessed="yesterday"), "source.accessed"),
        (lambda c: c["rights"].pop("local_download"), "rights.local_download"),
        (lambda c: c["rights"]["local_download"].update(answer="yes"), "answer"),
        (lambda c: c["rights"]["local_download"].update(source=""), "source"),
        (lambda c: c["artifacts"][0].update(type="measured"), "artifacts[0].type"),
        (lambda c: c.update(artifacts=[]), "artifacts"),
        (lambda c: c["decision"].update(value="maybe"), "decision.value"),
        (lambda c: c["decision"].update(reasons=[]), "decision.reasons"),
        (lambda c: c.pop("estimates"), "estimates"),
        (lambda c: c["downloads"][0].update(digest="12"), "digest"),
        (lambda c: c["samples"][0].update(test="somewhere"), "test"),
        (lambda c: c.update(id="Not An Id"), "id"),
    ],
)
def test_the_schema_names_what_is_wrong(change, expected):
    card = copy.deepcopy(CARDS["npl-onwafer-sparameters"])
    assert validate_card(card, "npl-onwafer-sparameters") == []
    change(card)
    problems = validate_card(card, "npl-onwafer-sparameters")
    assert any(expected in p for p in problems), problems


def test_a_survey_card_must_name_its_gate():
    card = copy.deepcopy(CARDS["gaia-dr3-astrometry"])
    assert validate_card(card, card["id"]) == []
    card["decision"].pop("gate")
    assert any("gate" in p for p in validate_card(card, card["id"]))


def test_a_card_must_carry_the_name_of_its_file():
    card = copy.deepcopy(CARDS["gaia-dr3-astrometry"])
    assert any("differs from the file name" in p for p in validate_card(card, "other"))


# The cards of this repository.


def test_the_repository_passes_the_dataset_check():
    assert check_repository(ROOT) == []


def test_there_is_one_card_for_each_of_the_25_surveyed_datasets():
    assert len(CARDS) == 25
    decisions = {n: c["decision"]["value"] for n, c in CARDS.items()}
    assert sorted(n for n in decisions if n in SPIKED) == sorted(SPIKED)
    survey = [n for n, v in decisions.items() if v == "survey-only"]
    assert len(survey) == 22 and not set(survey) & set(SPIKED)


def test_a_survey_card_does_not_claim_an_inspected_file_or_a_survey_score():
    for name, card in CARDS.items():
        if card["decision"]["value"] != "survey-only":
            continue
        assert not card.get("samples"), name
        assert not card.get("downloads"), name
        text = yaml.safe_dump(card).lower()
        assert not re.search(r"\bscores?\b", text), name
        for artifact in card["artifacts"]:
            assert "no file was inspected" in artifact["description"], name


def test_the_diffraction_record_keeps_both_its_licence_and_its_copyright_line():
    card = CARDS["fraunhofer-microstructure-diffraction"]
    text = yaml.safe_dump(card)
    assert "CC-BY-4.0" in text and "Copyright (c) 2026 Oleksii Voronkin" in text
    assert card["rights"]["redistribution_of_subsets"]["answer"] == "unclear"
    assert card["decision"]["value"] == "survey-only"


def test_every_artifact_type_is_one_of_the_five():
    for card in CARDS.values():
        for artifact in card["artifacts"]:
            assert artifact["type"] in ARTIFACT_TYPES


def test_the_spiked_cards_separate_measurement_from_model():
    types = {a["type"] for a in CARDS["aalborg-submerged-bar"]["artifacts"]}
    assert {"processed-measured", "modelled-reference"} <= types
    for name in SPIKED:
        assert CARDS[name]["decision"]["date"] == date(2026, 10, 9)


# Invariant I20: nothing a build or a check does reaches a portal.

PORTALS = re.compile(
    r"zenodo\.org|gwosc\.org|opendata\.cern\.ch|esa\.int|almascience|mast\.stsci|ukaea",
    re.IGNORECASE,
)
NETWORK_MODULES = {
    "socket",
    "urllib",
    "http",
    "requests",
    "httpx",
    "aiohttp",
    "ftplib",
    "ssl",
}


def block_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("a connection was attempted")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)


def test_the_dataset_check_and_the_readers_work_with_the_network_blocked(monkeypatch):
    block_network(monkeypatch)
    from pbc.data.reference import aalborg_flume, gw150914, npl_sparameters

    assert check_repository(ROOT) == []
    for module, name in (
        (gw150914, "gw150914-strain"),
        (npl_sparameters, "npl-onwafer-sparameters"),
        (aalborg_flume, "aalborg-submerged-bar"),
    ):
        figure = module.make_figure(ROOT / "data/samples" / name)
        assert figure.axes


def test_the_data_package_imports_no_network_module():
    for path in (ROOT / "src/pbc/data").rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                assert name.split(".")[0] not in NETWORK_MODULES, f"{path}: {name}"


def test_no_lesson_and_no_verification_step_names_a_portal_or_the_download_script():
    sources = [
        *ROOT.glob("site/**/*.qmd"),
        *ROOT.glob("site/**/*.py"),
        *ROOT.glob("src/pbc/**/*.py"),
        ROOT / "scripts/verify.conf",
        ROOT / "scripts/build-site.sh",
        ROOT / "scripts/check-determinism.sh",
        ROOT / "scripts/check-lean.sh",
        *ROOT.glob(".github/workflows/*.y*ml"),
    ]
    assert len(sources) > 10
    for path in sources:
        if "_site" in path.parts or ".quarto" in path.parts:
            continue
        if path.is_relative_to(ROOT / "src/pbc/data"):
            continue  # its captions name the sources; see the import test above
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert "fetch-data" not in text, path
        assert not PORTALS.search(text), (path, PORTALS.search(text).group(0))


# scripts/fetch-data.sh, with a stand-in for curl.

CONTENT = b"a stand-in for a dataset\n"


@pytest.fixture
def fetch(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "curl.log"
    stub = bin_dir / "curl"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        'echo "$@" >> "$CURL_LOG"\n'
        'while [ "$#" -gt 0 ]; do\n'
        '  case "$1" in --output) out="$2"; shift ;; esac; shift\n'
        "done\n"
        'printf %s "$STUB_CONTENT" > "$out"\n'
    )
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    registry = tmp_path / "registry"
    registry.mkdir()
    card = copy.deepcopy(CARDS["npl-onwafer-sparameters"])
    card["id"] = "demo"
    card["samples"] = []
    card["downloads"] = [
        {
            "url": "https://example.invalid/demo.bin",
            "filename": "demo.bin",
            "algorithm": "sha256",
            "digest": hashlib.sha256(CONTENT).hexdigest(),
            "digest_source": "test",
        }
    ]
    (registry / "demo.yaml").write_text(yaml.safe_dump(card, sort_keys=False))
    env = {
        **{k: v for k, v in os.environ.items() if k != "CI"},
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "PBC_PYTHON": sys.executable,
        "PBC_REGISTRY": str(registry),
        "PBC_DOWNLOADS": str(tmp_path / "downloads"),
        "PBC_FETCH_DELAY": "0",
        "CURL_LOG": str(log),
        "STUB_CONTENT": CONTENT.decode(),
    }

    def run(*args, **overrides):
        return subprocess.run(
            [str(ROOT / "scripts/fetch-data.sh"), *args],
            env={**env, **overrides},
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

    run.log = log
    run.downloads = tmp_path / "downloads"
    run.registry = registry
    return run


def test_fetch_downloads_by_the_card_and_checks_the_digest(fetch):
    result = fetch("demo")
    assert result.returncode == 0, result.stderr
    assert (fetch.downloads / "demo/demo.bin").read_bytes() == CONTENT
    assert "https://example.invalid/demo.bin" in fetch.log.read_text()


def test_fetch_does_not_download_a_file_it_already_has(fetch):
    assert fetch("demo").returncode == 0
    fetch.log.unlink()
    assert fetch("demo").returncode == 0
    assert not fetch.log.exists()


def test_fetch_removes_a_file_whose_digest_differs_and_fails(fetch):
    result = fetch("demo", STUB_CONTENT="something else")
    assert result.returncode == 1
    assert "card says" in result.stderr
    assert not list(fetch.downloads.glob("demo/*"))


def test_fetch_refuses_an_unknown_dataset_and_a_card_without_downloads(fetch):
    assert fetch("nothing").returncode == 1
    shutil.copy(ROOT / "data/registry/gaia-dr3-astrometry.yaml", fetch.registry)
    result = fetch("gaia-dr3-astrometry")
    assert result.returncode == 1 and "no download" in result.stderr


def test_fetch_needs_exactly_one_dataset(fetch):
    assert fetch().returncode == 2
    assert fetch("a", "b").returncode == 2


def test_fetch_refuses_to_run_in_ci_and_makes_no_request(fetch):
    result = fetch("demo", CI="true")
    assert result.returncode == 2
    assert not fetch.log.exists()


def test_fetch_is_executable():
    assert os.access(ROOT / "scripts/fetch-data.sh", os.X_OK)
