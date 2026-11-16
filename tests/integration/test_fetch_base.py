"""Which base a pull request run accepts (ADR 014 decision 2).

``fetch-base.sh`` runs here against a fake ``gh`` that answers the runs API
from files, so every case of provenance is one record: the run that produced
an artifact decides, never the artifact's name, its recency, or its contents.
"""

import hashlib
import json
import os
import stat
import subprocess
import zipfile
from pathlib import Path

import pytest
from support.checks import output
from support.paths import SCRIPTS

REPO = "owner/repo"
RUN = 1000
ARTIFACT = 77
MAIN = "a" * 40  # the commit refs/heads/main points to
COMMIT = "b" * 40  # the commit of a run, an ancestor of MAIN
ELSEWHERE = "c" * 40  # a commit that never reached main

FAKE_GH = """#!/usr/bin/env bash
# api [-H header] <path>: answers from $FAKE_API, one file per path (the query
# string is dropped, so the script's own checks do the filtering).
# auth status: the login of a developer's machine, as FAKE_AUTH_EXIT says.
# repo view: the repository of the clone, FAKE_REPO, or none.
case "$1" in
  auth) exit "${FAKE_AUTH_EXIT:-0}" ;;
  repo) [[ -n "${FAKE_REPO:-}" ]] || exit 1; printf '%s\\n' "$FAKE_REPO"; exit 0 ;;
  api) ;;
  *) exit 64 ;;
esac
shift
path=""
while [[ $# -gt 0 ]]; do
  case "$1" in
  -H) shift 2 ;;
  *) path="$1"; shift ;;
  esac
done
path="${path%%\\?*}"
file="$FAKE_API/$(printf '%s' "$path" | tr -c 'A-Za-z0-9\\n' '_')"
[[ -f "$file" ]] || { echo "gh: HTTP 404: $path" >&2; exit 1; }
cat "$file"
"""


def key(path: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in path)


class Api:
    """The state of the fake GitHub, and a run of the script against it."""

    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.api = tmp / "api"
        self.api.mkdir()
        self.bin = tmp / "bin"
        self.bin.mkdir()
        gh = self.bin / "gh"
        gh.write_text(FAKE_GH)
        gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
        self.target = tmp / "work" / "base"
        self.github_output = tmp / "github-output"
        self.put(
            f"repos/{REPO}/git/ref/heads/main",
            {"ref": "refs/heads/main", "object": {"type": "commit", "sha": MAIN}},
        )
        self.put(f"repos/{REPO}/git/matching-refs/tags/main", [])
        self.add_commit(COMMIT, "behind")
        self.add_commit(MAIN, "identical")
        self.add_commit(ELSEWHERE, "ahead", merge_base=MAIN)
        self.add_run(RUN)

    def put(self, path: str, data: object) -> None:
        (self.api / key(path)).write_text(json.dumps(data))

    def put_bytes(self, path: str, data: bytes) -> None:
        (self.api / key(path)).write_bytes(data)

    def add_commit(self, sha: str, status: str, merge_base: str | None = None):
        """How the compare API relates ``sha`` to the head of main."""
        self.put(
            f"repos/{REPO}/compare/{MAIN}...{sha}",
            {"status": status, "merge_base_commit": {"sha": merge_base or sha}},
        )

    def add_run(
        self, run: int, *, listed: bool = True, verify: str = "success", **record
    ) -> None:
        data = {
            "id": run,
            "event": "push",
            "head_branch": "main",
            "head_sha": COMMIT,
            "status": "completed",
            "conclusion": "success",
            "path": ".github/workflows/ci.yml",
            "head_repository": {"full_name": REPO},
            "repository": {"full_name": REPO},
        } | record
        self.put(f"repos/{REPO}/actions/runs/{run}", data)
        self.put(
            f"repos/{REPO}/actions/runs/{run}/jobs",
            {
                "jobs": [
                    {"name": "build", "status": "completed", "conclusion": "success"},
                    {"name": "verify", "status": "completed", "conclusion": verify},
                ]
            },
        )
        if listed:
            path = f"repos/{REPO}/actions/workflows/ci.yml/runs"
            listing = self.read(path) or {"workflow_runs": []}
            listing["workflow_runs"].append({"id": run})
            self.put(path, listing)
        self.add_artifact(run, ARTIFACT + run)

    def change_run(self, run: int, **record) -> None:
        path = f"repos/{REPO}/actions/runs/{run}"
        self.put(path, self.read(path) | record)

    def read(self, path: str):
        file = self.api / key(path)
        return json.loads(file.read_text()) if file.exists() else None

    def add_artifact(
        self,
        run: int,
        artifact: int,
        entries: dict[str, bytes | None] | None = None,
        **record,
    ) -> None:
        archive = self.tmp / f"base-{artifact}.zip"
        sha = (self.read(f"repos/{REPO}/actions/runs/{run}") or {}).get("head_sha")
        files = entries if entries is not None else good_entries(run, sha or COMMIT)
        with zipfile.ZipFile(archive, "w") as zipped:
            for name, content in files.items():
                zipped.writestr(name, content if content is not None else b"")
        data = archive.read_bytes()
        digest = "sha256:" + hashlib.sha256(data).hexdigest()
        self.put_bytes(f"repos/{REPO}/actions/artifacts/{artifact}/zip", data)
        found = {
            "id": artifact,
            "name": "verification-base",
            "expired": False,
            "size_in_bytes": len(data),
            "digest": digest,
            "workflow_run": {"id": run, "head_branch": "main"},
        } | record
        path = f"repos/{REPO}/actions/runs/{run}/artifacts"
        listing = self.read(path) or {"artifacts": []}
        listing["artifacts"].append(found)
        self.put(path, listing)

    def fetch(
        self, *arguments: str, without: tuple[str, ...] = (), **extra: str
    ) -> subprocess.CompletedProcess[str]:
        """Run the script as CI does, or without the variables ``without``
        and with the variables ``extra``, as a developer's machine has it."""
        env = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "FAKE_API": str(self.api),
            "GH_TOKEN": "token",
            "GITHUB_REPOSITORY": REPO,
            "GITHUB_OUTPUT": str(self.github_output),
            **extra,
        }
        for name in without:
            env.pop(name, None)
        return subprocess.run(
            [SCRIPTS / "fetch-base.sh", *arguments, str(self.target)],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def outputs(self) -> dict[str, str]:
        lines = self.github_output.read_text().splitlines()
        return dict(line.split("=", 1) for line in lines)


def provenance(run: int = RUN, sha: str = COMMIT, ref: str = "refs/heads/main"):
    """What collect-base.sh records of the run that collected a base."""
    return json.dumps({"ref": ref, "sha": sha, "run_id": run}).encode()


def good_entries(run: int = RUN, sha: str = COMMIT) -> dict[str, bytes | None]:
    return {
        "provenance.json": provenance(run, sha),
        "digests.json": json.dumps({"format": 1, "lessons": {}}).encode(),
        "pages.json": json.dumps({"format": 1, "files": {}}).encode(),
        "freeze/lessons/a/index/execute-results/html.json": b"{}",
    }


@pytest.fixture
def api(tmp_path: Path) -> Api:
    return Api(tmp_path)


def assert_no_base(api: Api, result: subprocess.CompletedProcess[str], why: str):
    # Not an error: the run goes on and executes every lesson.
    assert result.returncode == 0, output(result)
    assert "No base:" in result.stdout, output(result)
    assert why in result.stderr + result.stdout, output(result)
    assert not api.target.exists()
    assert api.outputs() == {"accepted": "false", "run-id": ""}


def test_the_base_of_a_verified_push_run_on_main_is_accepted(api: Api):
    result = api.fetch()
    assert result.returncode == 0, output(result)
    assert api.outputs() == {"accepted": "true", "run-id": str(RUN)}
    assert (api.target / "digests.json").is_file()
    assert (api.target / "pages.json").is_file()
    assert (
        api.target / "freeze" / "lessons" / "a" / "index" / "execute-results"
    ).is_dir()


# A developer's machine (ADR 017 decision 7): the repository of the clone and
# the login of gh stand in for the variables CI sets.


def test_without_a_token_the_login_of_gh_is_used(api: Api):
    result = api.fetch(without=("GH_TOKEN",), FAKE_AUTH_EXIT="0")
    assert result.returncode == 0, output(result)
    assert api.outputs() == {"accepted": "true", "run-id": str(RUN)}


def test_without_a_token_or_a_login_there_is_no_base(api: Api):
    result = api.fetch(without=("GH_TOKEN",), FAKE_AUTH_EXIT="1")
    assert_no_base(api, result, "gh is not logged in")


def test_without_the_repository_variable_the_repository_of_the_clone_is_used(
    api: Api,
):
    result = api.fetch(without=("GITHUB_REPOSITORY",), FAKE_REPO=REPO)
    assert result.returncode == 0, output(result)
    assert api.outputs() == {"accepted": "true", "run-id": str(RUN)}
    # Another repository's clone finds no base of this one: the records of
    # the runs are read for the repository gh names.
    result = api.fetch(without=("GITHUB_REPOSITORY",), FAKE_REPO="other/repo")
    assert_no_base(api, result, "cannot be listed")


def test_without_a_repository_there_is_no_base(api: Api):
    result = api.fetch(without=("GITHUB_REPOSITORY",))
    assert_no_base(api, result, "the repository cannot be determined")


def test_the_latest_acceptable_run_wins_and_a_rejected_one_is_skipped(api: Api):
    # Listed first, so the newest; its verify failed, so the next one is taken.
    api.add_run(2000, listed=False, verify="failure")
    api.put(
        f"repos/{REPO}/actions/workflows/ci.yml/runs",
        {"workflow_runs": [{"id": 2000}, {"id": RUN}]},
    )
    result = api.fetch()
    assert result.returncode == 0, output(result)
    assert api.outputs()["run-id"] == str(RUN)
    assert "run 2000: the job verify did not conclude with success" in result.stderr


@pytest.mark.parametrize(
    ("record", "why"),
    [
        ({"event": "pull_request"}, "pull_request run, not a push run"),
        ({"event": "workflow_dispatch"}, "not a push run"),
        ({"head_branch": "feature/x"}, "not main"),
        ({"head_branch": "main-copy"}, "not main"),
        ({"head_repository": {"full_name": "fork/repo"}}, "another repository"),
        ({"repository": {"full_name": "fork/repo"}}, "another repository"),
        ({"path": ".github/workflows/other.yml"}, "not ci.yml"),
        ({"status": "in_progress"}, "has not completed"),
        ({"conclusion": "failure"}, "concluded with failure"),
        ({"conclusion": "cancelled"}, "concluded with cancelled"),
    ],
    ids=lambda value: value if isinstance(value, str) else next(iter(value)),
)
def test_a_run_that_is_not_a_verified_push_run_on_main_is_rejected(
    api: Api, record: dict, why: str
):
    # The run record decides, even when the listing offers the run and its
    # artifact carries the right name and the branch main.
    api.add_run(RUN + 1, listed=False)
    api.put(f"repos/{REPO}/actions/runs/{RUN}", {"id": RUN} | record)
    api.put(
        f"repos/{REPO}/actions/runs/{RUN}", api.read(f"repos/{REPO}/actions/runs/{RUN}")
    )
    run = api.read(f"repos/{REPO}/actions/runs/{RUN + 1}") | record | {"id": RUN}
    api.put(f"repos/{REPO}/actions/runs/{RUN}", run)
    assert_no_base(api, api.fetch(), why)


# A tag push records the tag's name as head_branch, so a tag named main reads
# like the branch: the repository decides (ADR 014 decision 2, Issue #211).


def test_a_tag_push_of_a_tag_named_main_is_rejected(api: Api):
    # The record of the push of a tag main on a commit that never reached the
    # branch: the same as a branch push but for the commit it checked out.
    api.change_run(RUN, head_sha=ELSEWHERE)
    assert_no_base(api, api.fetch(), "not on the history of refs/heads/main")
    api.github_output.unlink()
    assert_no_base(
        api, api.fetch("--run", str(RUN)), "not on the history of refs/heads/main"
    )


def test_while_a_tag_named_main_exists_there_is_no_base(api: Api):
    # Even for a run whose commit is on main: the tag could have pointed there.
    api.put(
        f"repos/{REPO}/git/matching-refs/tags/main",
        [
            {"ref": "refs/tags/main-v1", "object": {"type": "commit", "sha": MAIN}},
            {"ref": "refs/tags/main", "object": {"type": "commit", "sha": COMMIT}},
        ],
    )
    assert_no_base(api, api.fetch(), "a tag named main exists")


def test_a_tag_whose_name_only_begins_with_main_does_not_matter(api: Api):
    api.put(
        f"repos/{REPO}/git/matching-refs/tags/main",
        [{"ref": "refs/tags/main-v1", "object": {"type": "commit", "sha": MAIN}}],
    )
    result = api.fetch()
    assert result.returncode == 0, output(result)
    assert api.outputs() == {"accepted": "true", "run-id": str(RUN)}


def test_a_tag_push_of_a_commit_on_main_whose_tag_is_gone_is_rejected(api: Api):
    # Review 01, M1: a tag main pushed on a commit already on main, and
    # deleted before the fetch. The run record, the ancestry and the tags
    # are those of a branch push; only the run's own ref tells them apart.
    only_artifact(
        api, good_entries() | {"provenance.json": provenance(ref="refs/tags/main")}
    )
    why = "does not name refs/heads/main"
    assert_no_base(api, api.fetch(), why)
    api.github_output.unlink()
    assert_no_base(api, api.fetch("--run", str(RUN)), why)


@pytest.mark.parametrize(
    ("record", "why"),
    [
        (None, "holds no provenance.json"),
        (b"not json", "does not name refs/heads/main"),
        (b'["refs/heads/main"]', "does not name refs/heads/main"),
        (provenance(ref="main"), "does not name refs/heads/main"),
        (provenance(ref="refs/heads/main-copy"), "does not name refs/heads/main"),
        (provenance(sha=MAIN), "does not name refs/heads/main"),
        (provenance(run=RUN + 1), "does not name refs/heads/main"),
    ],
    ids=["missing", "not-json", "not-object", "short", "other-branch", "sha", "run"],
)
def test_a_base_whose_run_did_not_record_the_branch_main_is_rejected(
    api: Api, record: bytes | None, why: str
):
    # Fail closed: a base that does not establish the full ref of its run,
    # for this run and its commit, gives a full run.
    entries = {k: v for k, v in good_entries().items() if k != "provenance.json"}
    if record is not None:
        entries["provenance.json"] = record
    only_artifact(api, entries)
    assert_no_base(api, api.fetch(), why)


@pytest.mark.parametrize(
    ("compare", "head_sha"),
    [
        ({"status": "ahead"}, COMMIT),
        ({"status": "diverged", "merge_base_commit": {"sha": MAIN}}, COMMIT),
        ({"status": "behind", "merge_base_commit": {"sha": MAIN}}, COMMIT),
        (None, COMMIT),
        ({"status": "behind"}, None),
        ({"status": "behind"}, "main"),
    ],
    ids=["ahead", "diverged", "other-merge-base", "no-compare", "no-sha", "not-sha"],
)
def test_a_run_whose_commit_is_not_on_main_is_rejected(
    api: Api, compare: dict | None, head_sha: str | None
):
    path = f"repos/{REPO}/compare/{MAIN}...{COMMIT}"
    if compare is None:
        api.api.joinpath(key(path)).unlink()
    else:
        api.put(path, {"merge_base_commit": {"sha": COMMIT}} | compare)
    api.change_run(RUN, head_sha=head_sha)
    assert_no_base(api, api.fetch(), "not on the history of refs/heads/main")


def test_the_head_of_main_itself_is_on_main(api: Api):
    api.change_run(RUN, head_sha=MAIN)
    only_artifact(api, good_entries(RUN, MAIN))
    result = api.fetch()
    assert result.returncode == 0, output(result)
    assert api.outputs() == {"accepted": "true", "run-id": str(RUN)}


@pytest.mark.parametrize(
    ("path", "data", "why"),
    [
        ("git/ref/heads/main", None, "the branch main cannot be read"),
        (
            "git/ref/heads/main",
            {"ref": "refs/tags/main", "object": {"type": "commit", "sha": MAIN}},
            "is not a commit",
        ),
        (
            "git/ref/heads/main",
            {"ref": "refs/heads/main", "object": {"type": "tag", "sha": MAIN}},
            "is not a commit",
        ),
        ("git/matching-refs/tags/main", None, "cannot be listed"),
        ("git/matching-refs/tags/main", {"ref": "x"}, "cannot be listed"),
    ],
    ids=["no-branch", "tag-ref", "not-commit", "no-tags", "tags-not-list"],
)
def test_when_the_ref_of_main_cannot_be_established_there_is_no_base(
    api: Api, path: str, data: object, why: str
):
    if data is None:
        api.api.joinpath(key(f"repos/{REPO}/{path}")).unlink()
    else:
        api.put(f"repos/{REPO}/{path}", data)
    assert_no_base(api, api.fetch(), why)


@pytest.mark.parametrize("verify", ["failure", "cancelled", "skipped"])
def test_a_main_run_whose_verify_did_not_succeed_is_rejected(api: Api, verify: str):
    api.add_run(RUN, verify=verify, listed=False)
    assert_no_base(api, api.fetch(), "the job verify did not conclude with success")


def test_a_run_without_the_job_verify_is_rejected(api: Api):
    api.put(f"repos/{REPO}/actions/runs/{RUN}/jobs", {"jobs": []})
    assert_no_base(api, api.fetch(), "the job verify did not conclude")


@pytest.mark.parametrize(
    ("record", "why"),
    [
        ({"expired": True}, "no single unexpired"),
        ({"name": "something-else"}, "no single unexpired"),
        ({"digest": None}, "no single unexpired"),
        ({"digest": "md5:abc"}, "no single unexpired"),
        ({"size_in_bytes": 0}, "no single unexpired"),
        ({"size_in_bytes": 3 * 1024**3}, "no single unexpired"),
        ({"workflow_run": {"id": 5, "head_branch": "main"}}, "no single unexpired"),
        (
            {"workflow_run": {"id": RUN, "head_branch": "feature/x"}},
            "no single unexpired",
        ),
    ],
    ids=lambda value: next(iter(value)) if isinstance(value, dict) else value,
)
def test_an_artifact_whose_record_does_not_fit_is_rejected(
    api: Api, record: dict, why: str
):
    path = f"repos/{REPO}/actions/runs/{RUN}/artifacts"
    listing = api.read(path)
    listing["artifacts"][0] |= record
    api.put(path, listing)
    assert_no_base(api, api.fetch(), why)


def test_two_artifacts_of_the_name_are_rejected(api: Api):
    api.add_artifact(RUN, 999)
    assert_no_base(api, api.fetch(), "no single unexpired")


def test_a_download_that_is_not_the_recorded_archive_is_rejected(api: Api):
    api.put_bytes(
        f"repos/{REPO}/actions/artifacts/{ARTIFACT + RUN}/zip", b"not the archive"
    )
    assert_no_base(api, api.fetch(), "digest differs")


def test_a_run_without_a_listing_gives_no_base(api: Api):
    api.api.joinpath(key(f"repos/{REPO}/actions/workflows/ci.yml/runs")).unlink()
    assert_no_base(api, api.fetch(), "cannot be listed")


def test_an_empty_listing_gives_no_base(api: Api):
    api.put(f"repos/{REPO}/actions/workflows/ci.yml/runs", {"workflow_runs": []})
    assert_no_base(api, api.fetch(), "no earlier push to main")


def only_artifact(api: Api, entries: dict[str, bytes | None], **record) -> None:
    """Replace the artifact of the run with one holding ``entries``."""
    api.put(f"repos/{REPO}/actions/runs/{RUN}/artifacts", {"artifacts": []})
    api.add_artifact(RUN, 500, entries, **record)


@pytest.mark.parametrize(
    ("entries", "why"),
    [
        ({}, "the archive is empty or not readable"),
        ({"../escape": b"x"} | good_entries(), "holds the path ../escape"),
        ({"/absolute": b"x"} | good_entries(), "holds the path /absolute"),
        ({"a/../../b": b"x"} | good_entries(), "holds the path a/../../b"),
        (
            {k: v for k, v in good_entries().items() if k != "digests.json"},
            "no digests.json",
        ),
        (
            {k: v for k, v in good_entries().items() if k != "pages.json"},
            "no pages.json",
        ),
        (
            {k: v for k, v in good_entries().items() if not k.startswith("freeze")},
            "no stored results",
        ),
        (good_entries() | {"digests.json": b"[1]"}, "not a JSON object"),
        (good_entries() | {"pages.json": b"not json"}, "not a JSON object"),
    ],
    ids=[
        "empty",
        "parent",
        "absolute",
        "nested-parent",
        "no-digests",
        "no-pages",
        "no-freeze",
        "digests-not-object",
        "pages-not-json",
    ],
)
def test_an_incomplete_or_unsafe_archive_is_rejected(
    api: Api, entries: dict[str, bytes | None], why: str
):
    only_artifact(api, entries)
    assert_no_base(api, api.fetch(), why)


def put_archive_with_link(
    api: Api, tmp_path: Path, *, link_first: bool = False, padding: int = 0
) -> None:
    """Make the one artifact of the run an archive that holds a link."""
    archive = tmp_path / "link.zip"
    link = zipfile.ZipInfo("freeze/link")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(archive, "w") as zipped:
        if link_first:
            zipped.writestr(link, "/etc/passwd")
        for name, content in good_entries().items():
            zipped.writestr(name, content or b"")
        for number in range(padding):
            zipped.writestr(f"freeze/padding/{number:06d}-{'x' * 60}.txt", b"x")
        if not link_first:
            zipped.writestr(link, "/etc/passwd")
    data = archive.read_bytes()
    api.put(f"repos/{REPO}/actions/runs/{RUN}/artifacts", {"artifacts": []})
    api.add_artifact(RUN, 600)
    api.put_bytes(f"repos/{REPO}/actions/artifacts/600/zip", data)
    listing = api.read(f"repos/{REPO}/actions/runs/{RUN}/artifacts")
    listing["artifacts"][0]["digest"] = "sha256:" + hashlib.sha256(data).hexdigest()
    api.put(f"repos/{REPO}/actions/runs/{RUN}/artifacts", listing)


def test_an_archive_holding_a_link_is_rejected(api: Api, tmp_path: Path):
    put_archive_with_link(api, tmp_path)
    assert_no_base(api, api.fetch(), "holds ")


def test_a_link_before_a_listing_longer_than_a_pipe_is_found_by_the_listing(
    api: Api, tmp_path: Path
):
    """The rejection comes from the listing of the archive, not only from the
    check of what was unpacked: `unzip -Z | grep -q` must not fail with the
    SIGPIPE of unzip (pipefail) when grep stops at the first link."""
    put_archive_with_link(api, tmp_path, link_first=True, padding=4000)
    assert_no_base(api, api.fetch(), "the archive holds a link")


def test_nothing_of_the_base_is_executed(api: Api):
    marker = api.tmp / "executed"
    script = f"#!/usr/bin/env bash\ntouch {marker}\n".encode()
    only_artifact(
        api,
        good_entries() | {"run.sh": script, "freeze/hook.sh": script},
    )
    result = api.fetch()
    assert result.returncode == 0, output(result)
    assert not marker.exists()
    unpacked = api.target / "run.sh"
    assert not os.access(unpacked, os.X_OK) or unpacked.stat().st_mode & 0o111 == 0


def test_a_named_run_gets_the_same_checks(api: Api):
    result = api.fetch("--run", str(RUN))
    assert result.returncode == 0, output(result)
    assert api.outputs() == {"accepted": "true", "run-id": str(RUN)}

    api.add_run(RUN + 5, listed=False, event="pull_request")
    api.github_output.unlink()
    assert_no_base(api, api.fetch("--run", str(RUN + 5)), "not a push run")


@pytest.mark.parametrize("run", ["", "abc", "1;rm", "-1"])
def test_a_run_id_that_is_not_a_number_is_a_usage_error(api: Api, run: str):
    assert api.fetch("--run", run).returncode == 2


def test_a_failing_api_gives_no_base_and_does_not_fail_the_run(api: Api):
    for file in api.api.iterdir():
        file.unlink()
    assert_no_base(api, api.fetch(), "cannot be listed")


WARNING = "::warning title=No verification base::No base: "


def test_a_fallback_in_ci_is_a_workflow_warning_with_the_reason(api: Api):
    """In GitHub Actions a run without a base says so as a warning on the run,
    with the reason, and still exits 0 and runs everything (#230, m4)."""
    for file in api.api.iterdir():
        file.unlink()

    result = api.fetch(GITHUB_ACTIONS="true")

    assert_no_base(api, result, "cannot be listed")
    warnings = [line for line in result.stdout.splitlines() if line.startswith("::")]
    assert warnings == [
        f"{WARNING}the runs of earlier pushes to main cannot be listed."
        " Every lesson is executed and checked."
    ], output(result)


def test_a_rejected_base_in_ci_is_a_workflow_warning_too(api: Api):
    api.put(f"repos/{REPO}/actions/runs/{RUN}", {"id": RUN, "event": "pull_request"})

    result = api.fetch(GITHUB_ACTIONS="true")

    assert_no_base(api, result, "not a push run")
    assert f"{WARNING}no run offers a base that passes the provenance checks" in (
        result.stdout
    ), output(result)


def test_an_accepted_base_and_a_run_outside_ci_give_no_warning(api: Api):
    accepted = api.fetch(GITHUB_ACTIONS="true")
    assert accepted.returncode == 0, output(accepted)
    assert "::warning" not in accepted.stdout + accepted.stderr

    for file in api.api.iterdir():
        file.unlink()
    api.github_output.unlink()
    local = api.fetch(without=("GITHUB_ACTIONS",))
    assert_no_base(api, local, "cannot be listed")
    assert "::warning" not in local.stdout + local.stderr


def test_the_reason_of_a_warning_cannot_start_another_workflow_command(
    api: Api, tmp_path: Path
):
    """A name in an archive is part of a reason; a line break or a percent sign
    in it is escaped, so it stays inside the one warning."""
    script = (SCRIPTS / "fetch-base.sh").read_text()
    start = script.index("without_base() {")
    function = script[start : script.index("\n}\n", start) + 3]
    probe = tmp_path / "probe.sh"
    probe.write_text(
        "set -euo pipefail\noutput() { :; }\ntarget=x\nfetched_record=y\n"
        f"{function}\nwithout_base $'a%b\\n::error::injected\\rc'\n"
    )

    result = subprocess.run(
        ["bash", str(probe)],
        env={**os.environ, "GITHUB_ACTIONS": "true"},
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )

    warning = [
        line for line in result.stdout.split("\n") if line.startswith("::warning")
    ]
    assert warning == [
        f"{WARNING}a%25b%0A::error::injected%0Dc. Every lesson is executed and checked."
    ], output(result)


def test_what_an_earlier_base_left_is_replaced_even_when_none_is_accepted(api: Api):
    api.target.mkdir(parents=True)
    (api.target / "stale").write_text("old")
    api.put(f"repos/{REPO}/actions/runs/{RUN}", {"id": RUN, "event": "pull_request"})
    assert_no_base(api, api.fetch(), "not a push run")


def test_collect_base_gathers_what_a_build_left(tmp_path: Path):
    site = tmp_path / "site"
    (site / "_freeze" / "lessons" / "a").mkdir(parents=True)
    (site / "_freeze" / "lessons" / "a" / "result.json").write_text("{}")
    (site / "_digests.json").write_text("{}")
    (site / "_pages.json").write_text("{}")
    out = tmp_path / "out"
    env = {
        **os.environ,
        "PBC_SOURCE_DIR": str(site),
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_SHA": COMMIT,
        "GITHUB_RUN_ID": str(RUN),
    }
    run = subprocess.run(
        [SCRIPTS / "collect-base.sh", out],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 0, output(run)
    assert sorted(
        p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()
    ) == [
        "digests.json",
        "freeze/lessons/a/result.json",
        "pages.json",
        "provenance.json",
    ]
    assert json.loads((out / "provenance.json").read_text()) == {
        "ref": "refs/heads/main",
        "sha": COMMIT,
        "run_id": RUN,
    }
    # Only a workflow run, which knows its ref, collects a base.
    for name in ("GITHUB_REF", "GITHUB_SHA", "GITHUB_RUN_ID"):
        run = subprocess.run(
            [SCRIPTS / "collect-base.sh", out],
            env={k: v for k, v in env.items() if k != name},
            capture_output=True,
            text=True,
            check=False,
        )
        assert run.returncode == 1, name
        assert f"{name} is not set" in run.stderr
    (site / "_pages.json").unlink()
    run = subprocess.run(
        [SCRIPTS / "collect-base.sh", out],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 1
    assert "_pages.json is missing" in run.stderr
