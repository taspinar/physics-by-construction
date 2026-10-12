"""The two scripts that hold the parallel CI jobs together (ADR 012).

``ci-aggregate.sh`` decides the one required check from the results of the
jobs; ``fetch-built-site.sh`` hands the site of the build job to the jobs
that check it. Both run here without GitHub.
"""

import json
import os
import subprocess
import tarfile
from pathlib import Path

import pytest
from support.checks import output
from support.paths import SCRIPTS

JOBS = ["code", "build", "e2e-other"]


def aggregate(needs: object, *jobs: str) -> subprocess.CompletedProcess[str]:
    text = needs if isinstance(needs, str) else json.dumps(needs)
    return subprocess.run(
        [SCRIPTS / "ci-aggregate.sh", *jobs],
        env={**os.environ, "NEEDS": text},
        capture_output=True,
        text=True,
        check=False,
    )


def results(**overrides: str) -> dict[str, dict[str, str]]:
    return {job: {"result": overrides.get(job, "success")} for job in JOBS}


def test_the_aggregate_passes_when_every_job_succeeded():
    result = aggregate(results(), *JOBS)
    assert result.returncode == 0, output(result)
    assert "All 3 jobs succeeded." in result.stdout


@pytest.mark.parametrize("outcome", ["failure", "cancelled", "skipped"])
def test_the_aggregate_fails_on_a_job_that_did_not_succeed(outcome):
    result = aggregate(results(build=outcome), *JOBS)
    assert result.returncode == 1
    assert f"{outcome}" in result.stderr and "build" in result.stderr


def test_the_aggregate_fails_on_a_job_that_is_expected_and_was_not_needed():
    needs = results()
    del needs["e2e-other"]
    result = aggregate(needs, *JOBS)
    assert result.returncode == 1
    assert "missing  e2e-other" in result.stderr


def test_the_aggregate_fails_on_a_needed_job_that_is_not_expected():
    result = aggregate(results(), "code", "build")
    assert result.returncode == 1
    assert "unlisted e2e-other" in result.stderr


@pytest.mark.parametrize("needs", ["", "not json", "[]", '"success"'])
def test_the_aggregate_fails_on_results_it_cannot_read(needs):
    result = aggregate(needs, *JOBS)
    assert result.returncode == 1
    assert "All" not in result.stdout


def test_the_aggregate_fails_without_a_job_to_expect():
    assert aggregate(results()).returncode == 1


class Site:
    """A built site, its Lean build record, and the place a job unpacks to."""

    def __init__(self, tmp: Path) -> None:
        self.built = tmp / "built"
        (self.built / "lessons").mkdir(parents=True)
        (self.built / "index.html").write_text("<h1>home</h1>\n")
        (self.built / "lessons" / "a page.html").write_text("<p>a</p>\n")
        self.built_record = tmp / "record.json"
        self.built_record.write_text('{"lean": "4"}\n')
        self.handed = tmp / "handed"
        self.unpacked = tmp / "job" / "site" / "_site"
        self.record = tmp / "job" / "lean" / ".lake" / "pbc-build-record.json"

    def run(self, *arguments: str | Path, site: Path, record: Path):
        return subprocess.run(
            [SCRIPTS / "fetch-built-site.sh", *arguments],
            env={
                **os.environ,
                "PBC_SITE_DIR": str(site),
                "PBC_BUILD_RECORD": str(record),
            },
            capture_output=True,
            text=True,
            check=False,
        )

    def hand_over(self) -> None:
        """What the build job does: record, and archive like the Pages action."""
        result = self.run(
            "--record", self.handed, site=self.built, record=self.built_record
        )
        assert result.returncode == 0, output(result)
        with tarfile.open(self.handed / "artifact.tar", "w") as archive:
            archive.add(self.built, arcname=".")

    def fetch(self) -> subprocess.CompletedProcess[str]:
        return self.run(self.handed, site=self.unpacked, record=self.record)


@pytest.fixture
def site(tmp_path: Path) -> Site:
    return Site(tmp_path)


def files(directory: Path) -> dict[str, bytes]:
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in directory.rglob("*")
        if path.is_file()
    }


def test_a_job_gets_the_site_that_was_built_and_its_build_record(site: Site):
    site.hand_over()
    result = site.fetch()
    assert result.returncode == 0, output(result)
    assert files(site.unpacked) == files(site.built)
    assert site.record.read_bytes() == site.built_record.read_bytes()


def test_what_a_job_had_before_is_replaced(site: Site):
    site.hand_over()
    site.unpacked.mkdir(parents=True)
    (site.unpacked / "stale.html").write_text("old\n")
    assert site.fetch().returncode == 0
    assert files(site.unpacked) == files(site.built)


def rebuild_archive(site: Site, change) -> None:
    change(site.built)
    with tarfile.open(site.handed / "artifact.tar", "w") as archive:
        archive.add(site.built, arcname=".")


@pytest.mark.parametrize(
    ("change", "named"),
    [
        (
            lambda built: (built / "index.html").write_text("<h1>other</h1>\n"),
            "index.html",
        ),
        (lambda built: (built / "lessons" / "a page.html").unlink(), "a page.html"),
        (lambda built: (built / "extra.html").write_text("x\n"), "extra.html"),
    ],
    ids=["changed", "missing", "extra"],
)
def test_a_site_that_is_not_the_built_one_stops_the_job(site: Site, change, named):
    site.hand_over()
    rebuild_archive(site, change)
    result = site.fetch()
    assert result.returncode == 1
    assert named in result.stderr
    assert "is not the site that was built" in result.stderr
    # The Lean build record is only put in place for a site that is accepted.
    assert not site.record.exists()


@pytest.mark.parametrize(
    "missing", ["artifact.tar", "site-files.sha256", "pbc-build-record.json"]
)
def test_an_incomplete_hand_over_stops_the_job(site: Site, missing):
    site.hand_over()
    (site.handed / missing).unlink()
    result = site.fetch()
    assert result.returncode == 1
    assert missing in result.stderr


def test_an_empty_list_of_checksums_stops_the_job(site: Site):
    site.hand_over()
    (site.handed / "site-files.sha256").write_text("")
    assert site.fetch().returncode == 1


def test_recording_needs_a_built_site_and_a_build_record(site: Site, tmp_path: Path):
    nowhere = tmp_path / "nowhere"
    no_site = site.run("--record", site.handed, site=nowhere, record=site.built_record)
    assert no_site.returncode == 1 and "no built site" in no_site.stderr
    no_record = site.run("--record", site.handed, site=site.built, record=nowhere)
    assert no_record.returncode == 1 and "no Lean build record" in no_record.stderr
