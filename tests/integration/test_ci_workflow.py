"""Boundaries of the CI workflow (architecture invariants I2, I8, I9, I15).

These are permission and scope boundaries: a change that loosens one must
fail here and be made on purpose. The checks run in parallel jobs behind one
required check (ADR 012); the tests below also hold that structure together:
every group of checks runs in exactly one job, and only the success of every
job passes the required check.
"""

import re
import subprocess
from pathlib import Path

import pytest
import yaml
from support.paths import REPO_ROOT

WORKFLOWS = sorted((REPO_ROOT / ".github" / "workflows").glob("*.y*ml"))
CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
# The preparation of a runner, shared by the jobs.
PREPARE = REPO_ROOT / ".github" / "actions" / "prepare" / "action.yml"
ACTIONS = sorted((REPO_ROOT / ".github" / "actions").glob("*/action.y*ml"))

CHECKOUT = "actions/checkout@"
VERIFY = "./scripts/verify.sh"
FETCH = './scripts/fetch-built-site.sh "$RUNNER_TEMP/built-site"'
RECORD = './scripts/fetch-built-site.sh --record "$RUNNER_TEMP/built-site-record"'
# The jobs that run checks; 'verify' decides from them and 'deploy' publishes.
AGGREGATE, DEPLOY = "verify", "deploy"


def check_jobs() -> dict[str, dict]:
    jobs = load(CI)["jobs"]
    return {name: job for name, job in jobs.items() if name not in (AGGREGATE, DEPLOY)}


def commands(job: dict) -> list[str]:
    return [step["run"] for step in job["steps"] if "run" in step]


def groups_of(job: dict) -> list[str]:
    """The groups a job runs, with the parts of a matrix written out."""
    [command] = [c for c in commands(job) if VERIFY in c]
    match = re.fullmatch(
        rf'{re.escape(VERIFY)} --all --only "?([a-z0-9,$A-Z-]+)"?', command
    )
    assert match, command
    groups = match.group(1).split(",")
    parts = job.get("strategy", {}).get("matrix", {}).get("part")
    if parts is None:
        assert "$" not in match.group(1), command
        return groups
    assert groups == ["e2e-$PART"], command
    [step] = [s for s in job["steps"] if s.get("run") == command]
    assert step["env"] == {"PART": "${{ matrix.part }}"}
    return [f"e2e-{part}" for part in parts]


def load(path: Path) -> dict:
    workflow = yaml.safe_load(path.read_text())
    # YAML 1.1 reads the key 'on' as the boolean true.
    workflow["on"] = workflow.pop(True)
    return workflow


@pytest.fixture(params=WORKFLOWS, ids=lambda path: path.name)
def workflow(request: pytest.FixtureRequest) -> dict:
    return load(request.param)


def test_ci_is_the_only_workflow():
    # The tests below describe ci.yml. Another workflow would need its own
    # review of triggers and permissions.
    assert WORKFLOWS == [CI]


def test_triggers_are_pull_request_and_push_to_main(workflow: dict):
    assert workflow["on"] == {"pull_request": None, "push": {"branches": ["main"]}}


def test_default_permissions_are_read_only(workflow: dict):
    assert workflow["permissions"] == {"contents": "read"}


def test_only_the_deploy_job_has_more_permissions(workflow: dict):
    for name, job in workflow["jobs"].items():
        if name == "deploy":
            assert job["permissions"] == {"pages": "write", "id-token": "write"}
        else:
            assert "permissions" not in job, name


def test_the_runner_preparation_is_the_only_local_action():
    assert ACTIONS == [PREPARE]


def test_every_action_is_pinned_by_commit_sha(workflow: dict):
    steps = [step for job in workflow["jobs"].values() for step in job["steps"]]
    steps += yaml.safe_load(PREPARE.read_text())["runs"]["steps"]
    uses = [step["uses"] for step in steps if "uses" in step]
    assert uses
    for action in uses:
        if action == "./.github/actions/prepare":
            continue
        assert re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", action), action


@pytest.mark.parametrize(
    "path", [*WORKFLOWS, *ACTIONS], ids=lambda path: path.parent.name
)
def test_no_secret_is_referenced(path: Path):
    assert "secrets." not in path.read_text()


def test_the_jobs_run_checks_only_through_verify_sh():
    for name, job in check_jobs().items():
        runs = commands(job)
        # One run of verify.sh, always with --all, so that CI never skips the
        # workflow self-tests (ADR 005), and always with --only: a run
        # without it would run every check a second time.
        assert sum(VERIFY in command for command in runs) == 1, name
        assert groups_of(job), name
        # The only other commands hand the built site from one job to the
        # next. No job runs a check tool itself, so no check exists only in CI.
        others = [command for command in runs if VERIFY not in command]
        assert set(others) <= {FETCH, RECORD}, name


def test_the_runner_preparation_runs_no_check():
    steps = yaml.safe_load(PREPARE.read_text())["runs"]["steps"]
    runs = [step["run"] for step in steps if "run" in step]
    # Fetching the build products that Mathlib publishes is preparation, like
    # installing the browser (ADR 012). It is the one use of lake here.
    assert runs.count("lake exe cache get") == 1
    setup = "\n".join(run for run in runs if run != "lake exe cache get")
    for tool in ("ruff", "pytest", "quarto", "lake", "scripts/", "tests/"):
        assert tool not in setup, tool


def test_every_group_of_checks_runs_in_exactly_one_job():
    # What verify.conf declares against what CI runs: a check in a group that
    # no job runs would pass locally and never in CI.
    result = subprocess.run(
        [VERIFY, "--groups"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    )
    declared = result.stdout.split()
    run = [group for job in check_jobs().values() for group in groups_of(job)]
    assert sorted(run) == sorted(declared)
    assert len(run) == len(set(run))


def test_the_required_check_passes_only_when_every_job_succeeded():
    jobs = load(CI)["jobs"]
    job = jobs[AGGREGATE]
    # It runs whatever happened to the jobs before it; without this GitHub
    # would skip it after a failure, and a skipped required check passes.
    assert job["if"] == "${{ always() }}"
    assert sorted(job["needs"]) == sorted(check_jobs())
    [step] = [step for step in job["steps"] if "run" in step]
    assert step["env"] == {"NEEDS": "${{ toJSON(needs) }}"}
    assert step["run"] == "./scripts/ci-aggregate.sh " + " ".join(job["needs"])
    assert [s["uses"].split("@")[0] + "@" for s in job["steps"] if "uses" in s] == [
        CHECKOUT
    ]


def test_no_job_continues_after_a_failure_or_runs_on_a_condition():
    jobs = load(CI)["jobs"]
    for name, job in jobs.items():
        assert "continue-on-error" not in job, name
        assert ("if" in job) == (name in (AGGREGATE, DEPLOY)), name
        for step in job["steps"]:
            assert "continue-on-error" not in step, name
            if "if" in step:
                assert step["uses"].startswith("actions/upload-pages-artifact@"), name


def test_the_jobs_have_the_agreed_timeouts():
    # 45 minutes per job since 2026-10-11, by the owner; ADR 012 decides from
    # the measured cold-cache run whether it returns to the 30 of ADR 003.
    jobs = load(CI)["jobs"]
    for name, job in check_jobs().items():
        assert job["timeout-minutes"] == 45, name
    assert jobs[AGGREGATE]["timeout-minutes"] == 5
    assert jobs[DEPLOY]["timeout-minutes"] == 10


def test_the_site_is_built_in_one_job_and_uploaded_with_its_record():
    jobs = check_jobs()
    builders = [name for name, job in jobs.items() if "build" in groups_of(job)]
    assert builders == ["build"]
    steps = jobs["build"]["steps"]
    names = [step.get("run") or step["uses"].split("@")[0] for step in steps]
    verify = names.index(f"{VERIFY} --all --only build")
    # The record is written after the build passed and before the uploads.
    assert names[verify + 1 :] == [
        RECORD,
        "actions/upload-pages-artifact",
        "actions/upload-artifact",
    ]
    pages, record = steps[-2], steps[-1]
    assert pages["with"]["path"] == "site/_site"
    # Without a condition GitHub skips the step after a failed one. This one
    # runs whenever a site was built, unless the run was cancelled.
    assert (
        pages["if"] == "${{ !cancelled() && hashFiles('site/_site/index.html') != '' }}"
    )
    assert record["with"]["name"] == "built-site-record"
    assert record["with"]["path"] == "${{ runner.temp }}/built-site-record"
    assert record["with"]["if-no-files-found"] == "error"


def test_a_job_that_checks_the_built_site_checks_the_one_that_was_built():
    for name, job in check_jobs().items():
        groups = groups_of(job)
        reads_the_site = any(g == "determinism" or g.startswith("e2e-") for g in groups)
        assert (job.get("needs") == "build") == reads_the_site, name
        runs = commands(job)
        assert (FETCH in runs) == reads_the_site, name
        if not reads_the_site:
            continue
        # Both artifacts, then the comparison with the record, then the checks.
        steps = job["steps"]
        downloads = [
            s
            for s in steps
            if s.get("uses", "").startswith("actions/download-artifact@")
        ]
        assert [d["with"]["name"] for d in downloads] == [
            "github-pages",
            "built-site-record",
        ]
        for download in downloads:
            assert download["with"]["path"] == "${{ runner.temp }}/built-site"
        order = [steps.index(downloads[-1])]
        order += [i for i, s in enumerate(steps) if s.get("run") == FETCH]
        order += [i for i, s in enumerate(steps) if VERIFY in s.get("run", "")]
        assert order == sorted(order) and len(order) == 3, name


def test_the_lean_packages_are_saved_by_the_build_job_only():
    for name, job in check_jobs().items():
        [prepare] = [
            s for s in job["steps"] if s.get("uses") == "./.github/actions/prepare"
        ]
        mode = prepare.get("with", {}).get("lean-packages", "none")
        assert (mode == "save") == (name == "build"), name


def test_deploy_job_publishes_the_verified_artifact_and_builds_nothing():
    job = load(CI)["jobs"][DEPLOY]

    # Only after the required check, which passes only when every job did.
    assert job["needs"] == AGGREGATE
    assert job["if"] == "github.event_name == 'push' && github.ref == 'refs/heads/main'"
    # One step, the Pages deployment of the artifact uploaded by the build
    # job: no checkout, no command.
    assert len(job["steps"]) == 1
    assert job["steps"][0]["uses"].startswith("actions/deploy-pages@")
    assert "run" not in job["steps"][0]
