"""The base is not fetched again when it is already here (ADR 020 decision 7).

``fetch-base.sh`` makes every provenance check of ADR 014 decision 2 on
every run, and the run those checks choose decides; only the download is
skipped when the base already retrieved came from exactly that run, with
exactly the recorded artifact, and only while its contents are the ones
unpacked from it. Recency never decides: a base from another
run is replaced, and a base whose run is no longer accepted is removed. The
fake GitHub of ``test_fetch_base`` answers; a download that is attempted
after the archive is gone from it fails, which shows whether one happened.
"""

import json
from pathlib import Path

import pytest
from support.checks import output
from test_fetch_base import ARTIFACT, REPO, RUN, Api, assert_no_base


@pytest.fixture
def api(tmp_path: Path) -> Api:
    return Api(tmp_path)


def archive_path(run: int) -> str:
    return f"repos/{REPO}/actions/artifacts/{ARTIFACT + run}/zip"


def forget_archive(api: Api, run: int = RUN) -> None:
    """GitHub no longer serves the archive: a download would fail."""
    (api.api / "".join(c if c.isalnum() else "_" for c in archive_path(run))).unlink()


def test_the_accepted_run_whose_base_is_here_is_not_fetched_again(api: Api):
    first = api.fetch()
    assert first.returncode == 0, output(first)
    record = api.target.parent / "base.fetched"
    assert record.read_text().splitlines()[0] == f"run-id={RUN}"
    forget_archive(api)
    second = api.fetch()
    assert second.returncode == 0, output(second)
    assert "not fetched again" in second.stdout, output(second)
    assert api.outputs() == {"accepted": "true", "run-id": str(RUN)}
    assert (api.target / "digests.json").is_file()


def test_every_provenance_check_is_still_made_before_the_reuse(api: Api):
    assert api.fetch().returncode == 0
    forget_archive(api)
    # The run of the base here is no longer acceptable: its verify failed.
    api.add_run(RUN, verify="failure", listed=False)
    assert_no_base(api, api.fetch(), "the job verify did not conclude with success")
    assert not (api.target.parent / "base.fetched").exists()


def test_a_newer_accepted_run_replaces_the_base_here(api: Api):
    assert api.fetch().returncode == 0
    api.add_run(2000, listed=False)
    api.put(
        f"repos/{REPO}/actions/workflows/ci.yml/runs",
        {"workflow_runs": [{"id": 2000}, {"id": RUN}]},
    )
    result = api.fetch()
    assert result.returncode == 0, output(result)
    assert "not fetched again" not in result.stdout
    assert api.outputs()["run-id"] == "2000"
    recorded = json.loads((api.target / "provenance.json").read_text())
    assert recorded["run_id"] == 2000


def test_a_base_here_that_is_newer_than_the_accepted_run_does_not_count(api: Api):
    # The base here came from run 2000, which is listed first and newest, but
    # its verify failed now; the checks choose RUN, so its base is fetched.
    api.add_run(2000, listed=False)
    api.put(
        f"repos/{REPO}/actions/workflows/ci.yml/runs",
        {"workflow_runs": [{"id": 2000}, {"id": RUN}]},
    )
    assert api.fetch().returncode == 0
    assert api.outputs()["run-id"] == "2000"
    api.add_run(2000, verify="failure", listed=False)
    result = api.fetch()
    assert result.returncode == 0, output(result)
    assert "not fetched again" not in result.stdout
    assert api.outputs()["run-id"] == str(RUN)
    recorded = json.loads((api.target / "provenance.json").read_text())
    assert recorded["run_id"] == RUN


def test_a_base_here_whose_record_does_not_fit_is_fetched_again(api: Api):
    assert api.fetch().returncode == 0
    provenance = api.target / "provenance.json"
    provenance.write_text(
        json.dumps({"ref": "refs/heads/main", "sha": "f" * 40, "run_id": RUN})
    )
    result = api.fetch()
    assert result.returncode == 0, output(result)
    assert "not fetched again" not in result.stdout
    assert json.loads(provenance.read_text())["sha"] != "f" * 40


def test_a_base_here_without_its_record_is_fetched_again(api: Api):
    assert api.fetch().returncode == 0
    (api.target.parent / "base.fetched").unlink()
    forget_archive(api)
    assert_no_base(api, api.fetch(), "cannot be downloaded")


def test_a_base_here_whose_contents_were_changed_is_fetched_again(api: Api):
    # The record and provenance.json still fit; only a stored file differs.
    assert api.fetch().returncode == 0
    digests = api.target / "digests.json"
    original = digests.read_text()
    digests.write_text(json.dumps({"tampered": True}))
    result = api.fetch()
    assert result.returncode == 0, output(result)
    assert "not fetched again" not in result.stdout, output(result)
    assert digests.read_text() == original
    # Without the archive, a changed base is never accepted.
    digests.write_text(json.dumps({"tampered": True}))
    forget_archive(api)
    assert_no_base(api, api.fetch(), "cannot be downloaded")


def test_a_base_here_with_an_added_file_is_fetched_again(api: Api):
    assert api.fetch().returncode == 0
    added = api.target / "freeze" / "added.json"
    added.write_text("{}")
    result = api.fetch()
    assert result.returncode == 0, output(result)
    assert "not fetched again" not in result.stdout, output(result)
    assert not added.exists()


def test_a_record_without_the_contents_digest_is_fetched_again(api: Api):
    assert api.fetch().returncode == 0
    record = api.target.parent / "base.fetched"
    lines = record.read_text().splitlines()
    assert any(line.startswith("contents-digest=") for line in lines)
    record.write_text(
        "\n".join(line for line in lines if not line.startswith("contents-digest="))
        + "\n"
    )
    forget_archive(api)
    assert_no_base(api, api.fetch(), "cannot be downloaded")
