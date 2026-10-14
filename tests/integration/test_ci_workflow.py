"""Boundaries of the CI workflow (architecture invariants I2, I8, I9, I15).

These are permission and scope boundaries: a change that loosens one must
fail here and be made on purpose. The checks run in parallel jobs behind one
required check (ADR 012); the tests below also hold that structure together:
every group of checks runs in exactly one job, and only the success of every
job passes the required check.
"""

import json
import math
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from support import verify_conf
from support.paths import REPO_ROOT

from pbc.authoring import shards as sharding

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
# The job that derives the lesson shards and takes the base of a pull request
# once; the job that renders the one site from the parts of the shards (ADR 014
# decision 11).
PLAN, BUILD, ASSEMBLE = "plan", "build", "assemble"
SHARD_RUN = f'{VERIFY} --all --shard "$SHARD/$SHARDS"'
ASSEMBLE_RUN = f'{VERIFY} --all --assemble "$RUNNER_TEMP/parts"'
MATRIX = "${{ fromJSON(needs.plan.outputs.matrix) }}"
BASE_RUN_OF_PLAN = "${{ needs.plan.outputs.base-run }}"
# The job that publishes the base of a run on main (ADR 014 decision 2).
BASE_JOB = "base"
FETCH_BASE = './scripts/fetch-base.sh "$RUNNER_TEMP/base"'
FETCH_BASE_OF_BUILD = './scripts/fetch-base.sh --run "$BASE_RUN" "$RUNNER_TEMP/base"'
COLLECT_BASE = './scripts/collect-base.sh "$RUNNER_TEMP/verification-base"'
BASE_OPTION = ' --base "$RUNNER_TEMP/base"'
ON_PULL_REQUEST = "${{ github.event_name == 'pull_request' }}"
ON_MAIN = "${{ github.event_name == 'push' && github.ref == 'refs/heads/main' }}"


def check_jobs() -> dict[str, dict]:
    """The jobs that run checks of verify.conf; the plan job runs none."""
    jobs = load(CI)["jobs"]
    others = (AGGREGATE, DEPLOY, BASE_JOB, PLAN)
    return {name: job for name, job in jobs.items() if name not in others}


def verify_commands(job: dict) -> list[str]:
    return [c for c in commands(job) if VERIFY in c]


def plain_verify(job: dict) -> str:
    """The run of verify.sh without a base; the other one adds --base to it."""
    plain = [c for c in verify_commands(job) if BASE_OPTION not in c]
    assert len(plain) == 1
    return plain[0]


def commands(job: dict) -> list[str]:
    return [step["run"] for step in job["steps"] if "run" in step]


def groups_of(job: dict) -> list[str]:
    """The groups a job runs, with the parts of a matrix written out. The job
    that assembles the parts runs the group build as the assembly of its
    shards (ADR 014 decision 11): it is counted with them, not again."""
    command = plain_verify(job)
    if command == ASSEMBLE_RUN:
        return []
    if command == SHARD_RUN:
        assert job["strategy"]["matrix"] == {"shard": MATRIX}
        [step] = [s for s in job["steps"] if s.get("run") == command]
        assert step["env"]["SHARD"] == "${{ matrix.shard }}"
        assert step["env"]["SHARDS"] == "${{ strategy.job-total }}"
        return ["build"]
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


def test_only_the_deploy_job_has_write_permissions(workflow: dict):
    for name, job in workflow["jobs"].items():
        if name == "deploy":
            assert job["permissions"] == {"pages": "write", "id-token": "write"}
        elif "permissions" in job:
            assert all(v == "read" for v in job["permissions"].values()), name
    # No job writes anything but the deployment.
    writes = [
        name
        for name, job in workflow["jobs"].items()
        if "write" in job.get("permissions", {}).values()
    ]
    assert writes == ["deploy"]


def test_the_one_added_scope_is_reading_actions_in_the_jobs_that_take_the_base():
    # ADR 014 decision 2: contents stays read, and the jobs that look for the
    # base of a pull request read the runs and artifacts of earlier runs. No
    # other job has it.
    jobs = load(CI)["jobs"]
    for name, job in jobs.items():
        if name in (PLAN, BUILD, "e2e"):
            assert job["permissions"] == {"contents": "read", "actions": "read"}, name
        elif name != "deploy":
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
        assert groups_of(job) or name == ASSEMBLE, name
        # One run of verify.sh, or the same run with the base of a pull
        # request, chosen by a condition; never both and never another.
        with_base = [c for c in verify_commands(job) if BASE_OPTION in c]
        assert len(verify_commands(job)) == 1 + len(with_base), name
        assert len(with_base) == (1 if name in (BUILD, "e2e") else 0), name
        for command in with_base:
            assert command.replace(BASE_OPTION, "") == plain_verify(job), name
        # The only other commands hand the built site from one job to the
        # next. No job runs a check tool itself, so no check exists only in CI.
        others = [command for command in runs if VERIFY not in command]
        assert set(others) <= {
            FETCH,
            RECORD,
            FETCH_BASE,
            FETCH_BASE_OF_BUILD,
            COLLECT_BASE,
        }, name


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
    assert sorted(job["needs"]) == sorted([*check_jobs(), PLAN])
    [step] = [step for step in job["steps"] if "run" in step]
    assert step["env"] == {"NEEDS": "${{ toJSON(needs) }}"}
    assert step["run"] == "./scripts/ci-aggregate.sh " + " ".join(job["needs"])
    assert [s["uses"].split("@")[0] + "@" for s in job["steps"] if "uses" in s] == [
        CHECKOUT
    ]


def test_the_required_check_is_the_only_one_shown_as_verify():
    # The ruleset of main requires the status check 'verify'. GitHub shows a
    # job under its 'name' when it has one, and under its key otherwise. No
    # job has a 'name' here, so the aggregate is shown as 'verify' and
    # nothing else is; a matrix job is shown with its part in brackets.
    jobs = load(CI)["jobs"]
    shown = {key: job.get("name", key) for key, job in jobs.items()}
    assert shown[AGGREGATE] == "verify"
    assert [key for key, name in shown.items() if name == "verify"] == [AGGREGATE]
    for key, job in jobs.items():
        assert "name" not in job, key
    assert "strategy" not in jobs[AGGREGATE]


def test_no_job_continues_after_a_failure_or_runs_on_a_condition():
    jobs = load(CI)["jobs"]
    for name, job in jobs.items():
        assert "continue-on-error" not in job, name
        assert ("if" in job) == (name in (AGGREGATE, DEPLOY, BASE_JOB)), name
        for step in job["steps"]:
            assert "continue-on-error" not in step, name
            if "if" in step:
                assert step["if"] in allowed_conditions(step), (name, step)


def allowed_conditions(step: dict) -> list[str]:
    """The conditions a step of a check job may have, by what it does."""
    run, uses = step.get("run", ""), step.get("uses", "")
    if uses.startswith("actions/upload-pages-artifact@"):
        return ["${{ !cancelled() && hashFiles('site/_site/index.html') != '' }}"]
    if run == COLLECT_BASE or "verification-base-candidate" in str(step.get("with")):
        return [ON_MAIN]
    if run.startswith(FETCH_BASE.split(" ")[0]) and "--run" not in run:
        return [ON_PULL_REQUEST]
    if "--run" in run:
        return [
            "${{ github.event_name == 'pull_request' && "
            "needs.plan.outputs.base-run != '' }}"
        ]
    if BASE_OPTION in run:
        return ["${{ steps.base.outputs.accepted == 'true' }}"]
    if VERIFY in run:
        return ["${{ steps.base.outputs.accepted != 'true' }}"]
    return []


def test_the_jobs_have_the_agreed_timeouts():
    # 45 minutes per job since 2026-10-11, by the owner, and kept by ADR 012,
    # decision 9, in place of the 30 of ADR 003.
    jobs = load(CI)["jobs"]
    for name, job in check_jobs().items():
        assert job["timeout-minutes"] == 45, name
    assert jobs[PLAN]["timeout-minutes"] == 10
    assert jobs[AGGREGATE]["timeout-minutes"] == 5
    assert jobs[DEPLOY]["timeout-minutes"] == 10
    assert jobs[BASE_JOB]["timeout-minutes"] == 10


def test_the_site_is_assembled_in_one_job_and_uploaded_with_its_record():
    jobs = check_jobs()
    assert jobs[ASSEMBLE]["needs"] == BUILD
    steps = jobs[ASSEMBLE]["steps"]
    names = [step.get("run") or step["uses"].split("@")[0] for step in steps]
    verify = names.index(ASSEMBLE_RUN)
    # The record is written after the assembly passed and before the uploads;
    # what a run on main stored follows the uploads of the site.
    assert names[verify + 1 :] == [
        RECORD,
        "actions/upload-pages-artifact",
        "actions/upload-artifact",
        COLLECT_BASE,
        "actions/upload-artifact",
    ]
    pages, record = steps[-4], steps[-3]
    assert pages["with"]["path"] == "site/_site"
    # Without a condition GitHub skips the step after a failed one. This one
    # runs whenever a site was built, unless the run was cancelled.
    assert (
        pages["if"] == "${{ !cancelled() && hashFiles('site/_site/index.html') != '' }}"
    )
    assert record["with"]["name"] == "built-site-record"
    assert record["with"]["path"] == "${{ runner.temp }}/built-site-record"
    assert record["with"]["if-no-files-found"] == "error"


def test_no_lesson_shard_uploads_a_pages_artifact():
    jobs = load(CI)["jobs"]
    shard = jobs[BUILD]["steps"]
    assert not [s for s in shard if "upload-pages-artifact" in s.get("uses", "")]
    assert not [s for s in shard if "deploy-pages" in s.get("uses", "")]
    uploads = [
        s for s in shard if s.get("uses", "").startswith("actions/upload-artifact@")
    ]
    assert [u["with"]["name"] for u in uploads] == ["lesson-shard-${{ matrix.shard }}"]
    # The one Pages artifact of the workflow is the one the assembly uploads.
    pages = [
        name
        for name, job in jobs.items()
        for s in job["steps"]
        if s.get("uses", "").startswith("actions/upload-pages-artifact@")
    ]
    assert pages == [ASSEMBLE]


def test_the_assembly_takes_the_parts_of_every_shard_and_nothing_else():
    steps = load(CI)["jobs"][ASSEMBLE]["steps"]
    [download] = [
        s
        for s in steps
        if s.get("uses", "").startswith("actions/download-artifact@")
        and "lesson-shard" in str(s["with"])
    ]
    assert download["with"] == {
        "pattern": "lesson-shard-*",
        "path": "${{ runner.temp }}/parts",
    }
    # Downloaded before the run that verifies them.
    names = [s.get("run") or s["uses"] for s in steps]
    assert steps.index(download) < names.index(ASSEMBLE_RUN)


def test_a_shard_hands_over_its_part_only_after_its_checks_passed():
    steps = load(CI)["jobs"][BUILD]["steps"]
    [upload] = [
        s for s in steps if s.get("uses", "").startswith("actions/upload-artifact@")
    ]
    assert "if" not in upload  # runs only while every step before it succeeded
    assert upload["with"]["if-no-files-found"] == "error"
    assert upload["with"]["path"] == "${{ runner.temp }}/part"
    verifying = [i for i, s in enumerate(steps) if VERIFY in s.get("run", "")]
    assert verifying and max(verifying) < steps.index(upload)
    for index in verifying:
        assert steps[index]["env"]["PBC_PART_DIR"] == "${{ runner.temp }}/part"


def test_a_job_that_checks_the_built_site_checks_the_one_that_was_built():
    for name, job in check_jobs().items():
        groups = groups_of(job)
        # The build job checks its own site; the others get it handed over.
        reads_the_site = any(group.startswith("e2e-") for group in groups)
        assert (job.get("needs") == [PLAN, ASSEMBLE]) == reads_the_site, name
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
        # The base comes after the site and before any check.
        assert [d["with"]["name"] for d in downloads] == [
            "github-pages",
            "built-site-record",
        ]
        for download in downloads:
            assert download["with"]["path"] == "${{ runner.temp }}/built-site"
        order = [steps.index(downloads[-1])]
        order += [i for i, s in enumerate(steps) if s.get("run") == FETCH]
        order += [i for i, s in enumerate(steps) if VERIFY in s.get("run", "")]
        assert order == sorted(order) and len(order) == 4, name


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


def steps_with(job: dict, text: str) -> list[dict]:
    return [s for s in job["steps"] if text in s.get("run", "")]


def test_a_run_on_main_never_receives_a_base():
    # ADR 014 decision 2: main executes and checks every lesson. The only
    # steps that fetch a base run on a pull request, and no step of the
    # workflow fetches it on any other event.
    jobs = load(CI)["jobs"]
    fetching = [
        (name, step)
        for name, job in jobs.items()
        for step in job["steps"]
        if "fetch-base.sh" in step.get("run", "") or "--base" in step.get("run", "")
    ]
    assert fetching
    for name, step in fetching:
        assert "github.event_name == 'pull_request'" in step.get("if", "") or (
            "steps.base.outputs.accepted == 'true'" in step.get("if", "")
        ), (name, step)
    for name in (PLAN, BUILD, "e2e"):
        [fetch] = [
            s
            for s in jobs[name]["steps"]
            if s.get("id") == "base" and "fetch-base.sh" in s.get("run", "")
        ]
        assert "github.event_name == 'pull_request'" in fetch["if"]
        assert "push" not in fetch["if"]
    # The step that passes the base needs the step that accepted one.
    for name in (BUILD, "e2e"):
        [with_base] = steps_with(jobs[name], BASE_OPTION)
        assert with_base["if"] == "${{ steps.base.outputs.accepted == 'true' }}"


def test_the_base_is_fetched_with_the_read_token_and_nothing_else():
    jobs = load(CI)["jobs"]
    for name in (PLAN, BUILD, "e2e"):
        for step in steps_with(jobs[name], "fetch-base.sh"):
            assert step["env"]["GH_TOKEN"] == "${{ github.token }}"
            assert set(step["env"]) <= {"GH_TOKEN", "BASE_RUN"}
    # What the plan job accepted reaches the shards and the checking jobs as a
    # run number, which the script checks again; the number is never put into
    # a command.
    assert jobs[PLAN]["outputs"]["base-run"] == "${{ steps.base.outputs.run-id }}"
    for name in (BUILD, "e2e"):
        for step in steps_with(jobs[name], "--run"):
            assert step["env"]["BASE_RUN"] == BASE_RUN_OF_PLAN
            assert "${{" not in step["run"]


def test_the_base_is_published_by_main_only_after_verify_passed():
    jobs = load(CI)["jobs"]
    job = jobs[BASE_JOB]
    # After the required check, which passes only when every job did, and
    # only on main. A pull request run cannot reach it, so no pull request
    # (and no fork) uploads an artifact of that name.
    assert job["needs"] == AGGREGATE
    assert job["if"] == "github.event_name == 'push' && github.ref == 'refs/heads/main'"
    assert "permissions" not in job
    # No command: it copies the artifact the build job of this run made.
    assert not [s for s in job["steps"] if "run" in s]
    assert [s["uses"].split("@")[0] for s in job["steps"]] == [
        "actions/download-artifact",
        "actions/upload-artifact",
    ]
    download, upload = job["steps"]
    assert download["with"]["name"] == "verification-base-candidate"
    assert upload["with"]["name"] == "verification-base"
    assert upload["with"]["if-no-files-found"] == "error"
    # Nothing else uploads under the name that a pull request run reads.
    uploads = [
        step["with"]["name"]
        for j in jobs.values()
        for step in j["steps"]
        if step.get("uses", "").startswith("actions/upload-artifact@")
    ]
    assert uploads.count("verification-base") == 1
    # The required check does not wait for it: a failed publication means the
    # next pull requests run without a base, never that main fails.
    assert BASE_JOB not in jobs[AGGREGATE]["needs"]


def test_the_candidate_of_the_base_is_made_on_main_only():
    build = load(CI)["jobs"][ASSEMBLE]
    candidate = [
        s
        for s in build["steps"]
        if s.get("with", {}).get("name") == "verification-base-candidate"
    ]
    assert len(candidate) == 1
    assert candidate[0]["if"] == ON_MAIN
    [collect] = steps_with(build, "collect-base.sh")
    assert collect["if"] == ON_MAIN


def test_the_scripts_that_take_the_base_use_the_run_record():
    # The decision is made by the script, which the tests of
    # test_fetch_base.py hold to the record of the producing run. The
    # workflow does not decide from a name, a time, or a file of the base.
    text = CI.read_text()
    assert "download-artifact" in text
    for step in (s for j in load(CI)["jobs"].values() for s in j["steps"]):
        if step.get("uses", "").startswith("actions/download-artifact@"):
            assert step["with"].get("name") != "verification-base"
            assert "run-id" not in step["with"]
            assert "github-token" not in step["with"]


# --- the lesson shards (ADR 014 decision 11, F113) -------------------------------


def test_the_matrix_of_the_lesson_shards_is_derived_and_listed_in_no_file():
    jobs = load(CI)["jobs"]
    # A matrix that is a list in this file would be bumped by hand, and an
    # over-covering one would run idle shards.
    assert jobs[BUILD]["strategy"]["matrix"] == {"shard": MATRIX}
    assert jobs[BUILD]["needs"] == PLAN
    assert jobs[BUILD]["strategy"]["fail-fast"] is False
    assert jobs[PLAN]["outputs"]["matrix"] == "${{ steps.shards.outputs.matrix }}"
    derive = plan_step()
    assert f"{VERIFY} --shards" in derive["run"]
    assert "GITHUB_OUTPUT" in derive["run"]
    assert "env" not in derive and "with" not in derive
    # The shard count of the run is the size of the matrix, which the script
    # checks against its own derivation: N is never given freely.
    shard = [s for s in jobs[BUILD]["steps"] if s.get("run") == SHARD_RUN]
    assert len(shard) == 1
    assert shard[0]["env"]["SHARDS"] == "${{ strategy.job-total }}"


def plan_step() -> dict:
    [derive] = [s for s in load(CI)["jobs"][PLAN]["steps"] if s.get("id") == "shards"]
    return derive


COUNTS = [1, 22, 31, 32, 33, 63, 64, 65, 96, 97, 110, 125, 127, 128, 129]


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A repository with the real script and a stub for ``uv`` that runs this
    source tree, in which the step of the plan job can run."""
    root = tmp_path / "repo"
    (root / "scripts" / "lib").mkdir(parents=True)
    for name in (
        "verify.sh",
        "lib/verification.sh",
        "lib/fingerprint.sh",
        "verify.conf",
    ):
        shutil.copy2(REPO_ROOT / "scripts" / name, root / "scripts" / name)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "uv"
    stub.write_text(
        '#!/usr/bin/env bash\nwhile [[ "$1" != python ]]; do shift; done; shift\n'
        f'PYTHONPATH="{REPO_ROOT / "src"}" exec "{sys.executable}" "$@"\n'
    )
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    return root


def lessons(root: Path, count: int) -> None:
    shutil.rmtree(root / "site", ignore_errors=True)
    for number in range(count):
        page = root / f"site/lessons/s{number // 40}/{number:03d}-l/index.qmd"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text("---\ntitle: T\n---\n")


def environment(project: Path) -> dict[str, str]:
    return {**os.environ, "PATH": f"{project.parent / 'bin'}:{os.environ['PATH']}"}


def workflow_matrix(project: Path) -> list[int]:
    """The matrix the plan job makes of the lessons of ``project``: its step,
    run as the runner runs it."""
    output = project.parent / "github-output"
    output.unlink(missing_ok=True)
    subprocess.run(
        ["bash", "-e", "-c", plan_step()["run"]],
        cwd=project,
        env={**environment(project), "GITHUB_OUTPUT": str(output)},
        check=True,
    )
    [line] = output.read_text().splitlines()
    return json.loads(line.removeprefix("matrix="))


@pytest.mark.parametrize("count", COUNTS)
def test_the_matrix_the_workflow_makes_has_as_many_shards_as_the_script_derives(
    count: int, project: Path
):
    lessons(project, count)
    matrix = workflow_matrix(project)
    # N, the ceiling of the count over S: never more and never fewer.
    assert matrix == list(range(1, math.ceil(count / verify_conf.shard_size()) + 1))
    assert matrix == sharding.matrix(project)
    # Every job of the matrix is a shard the script accepts for that count; one
    # more would be an idle shard, and the script refuses it.
    for number in matrix:
        assert sharding.share(project, f"{number}/{len(matrix)}")[:2] == (
            number,
            len(matrix),
        )
    with pytest.raises(sharding.ShardError, match="derived"):
        sharding.share(project, f"1/{len(matrix) + 1}")


def test_the_transition_from_four_to_five_shards_needs_no_change_of_the_workflow(
    project: Path,
):
    before = CI.read_text()
    sizes = {}
    for count in (128, 129):
        lessons(project, count)
        sizes[count] = len(workflow_matrix(project))
    assert sizes == {128: 4, 129: 5}
    assert CI.read_text() == before


def test_the_tests_that_compare_bytes_run_in_the_jobs_that_computed_them():
    # ADR 012 decision 4, extended by ADR 014 decision 11: the reproduction of a
    # lesson runs in the shard that rendered it, and the determinism of the
    # one site runs in the assembly that rendered it. No job that compares
    # bytes with a site takes that site from another job.
    jobs = load(CI)["jobs"]
    groups = verify_conf.groups()
    assert groups["site-checks-reproduction"] == groups["site-build"] == "build"
    assert groups["determinism"] == "build"
    runners = [
        name
        for name, job in jobs.items()
        if any(
            f"{VERIFY} --all --shard" in c or f"{VERIFY} --all --assemble" in c
            for c in commands(job)
        )
    ]
    assert runners == [BUILD, ASSEMBLE]
    for name in runners:
        downloads = [
            s["with"]
            for s in jobs[name]["steps"]
            if s.get("uses", "").startswith("actions/download-artifact@")
        ]
        # A shard downloads nothing; the assembly downloads the parts, never a site.
        assert all("github-pages" not in str(d) for d in downloads), name
    assert not [
        s
        for s in jobs[BUILD]["steps"]
        if s.get("uses", "").startswith("actions/download-artifact@")
    ]
    # The jobs that check a site they were handed run the tests that do not
    # compare bytes with it.
    command = verify_conf.command("site-checks-other")
    assert '-m "not same_machine"' in command
