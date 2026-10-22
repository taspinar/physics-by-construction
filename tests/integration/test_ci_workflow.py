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
# The job that publishes the base of a run on main (ADR 014 decision 2).
BASE_JOB = "base"
FETCH_BASE = './scripts/fetch-base.sh "$RUNNER_TEMP/base"'
FETCH_BASE_OF_BUILD = './scripts/fetch-base.sh --run "$BASE_RUN" "$RUNNER_TEMP/base"'
COLLECT_BASE = './scripts/collect-base.sh "$RUNNER_TEMP/verification-base"'
BASE_OPTION = ' --base "$RUNNER_TEMP/base"'
ON_PULL_REQUEST = "${{ github.event_name == 'pull_request' }}"
ON_MAIN = "${{ github.event_name == 'push' && github.ref == 'refs/heads/main' }}"


def check_jobs() -> dict[str, dict]:
    jobs = load(CI)["jobs"]
    others = (AGGREGATE, DEPLOY, BASE_JOB)
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
    """The groups a job runs, with the parts of a matrix written out."""
    command = plain_verify(job)
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
        if name in ("build", "e2e"):
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
        assert groups_of(job), name
        # One run of verify.sh, or the same run with the base of a pull
        # request, chosen by a condition; never both and never another.
        with_base = [c for c in verify_commands(job) if BASE_OPTION in c]
        assert len(verify_commands(job)) == 1 + len(with_base), name
        assert len(with_base) == (1 if name in ("build", "e2e") else 0), name
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
    assert sorted(job["needs"]) == sorted(check_jobs())
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
            "needs.build.outputs.base-run != '' }}"
        ]
    if BASE_OPTION in run:
        return ["${{ steps.base.outputs.accepted == 'true' }}"]
    if VERIFY in run:
        return ["${{ steps.base.outputs.accepted != 'true' }}"]
    return []


def test_the_jobs_have_the_agreed_timeouts():
    # 45 minutes per job since 2026-10-11, by the owner, and kept by ADR 012,
    # decision 9, in place of the 30 of ADR 003; 60 minutes for the one job
    # `build` of a full run since 2026-10-15 (the interim full-run gate of
    # ADR 014, approved for up to 64 lessons since 2026-10-21; 45 before).
    jobs = load(CI)["jobs"]
    for name, job in check_jobs().items():
        assert job["timeout-minutes"] == (60 if name == "build" else 45), name
    assert jobs[AGGREGATE]["timeout-minutes"] == 5
    assert jobs[DEPLOY]["timeout-minutes"] == 10
    assert jobs[BASE_JOB]["timeout-minutes"] == 10


def test_the_site_is_built_in_one_job_and_uploaded_with_its_record():
    jobs = check_jobs()
    builders = [name for name, job in jobs.items() if "build" in groups_of(job)]
    assert builders == ["build"]
    steps = jobs["build"]["steps"]
    names = [step.get("run") or step["uses"].split("@")[0] for step in steps]
    verify = names.index(f"{VERIFY} --all --only build")
    # The record is written after the build passed and before the uploads;
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


def test_a_job_that_checks_the_built_site_checks_the_one_that_was_built():
    for name, job in check_jobs().items():
        groups = groups_of(job)
        # The build job checks its own site; the others get it handed over.
        reads_the_site = any(group.startswith("e2e-") for group in groups)
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


def test_the_integration_parts_prepare_only_what_each_part_needs():
    # The division of F119 (docs/verification-audit.md, "Division into
    # independent parts"): the Quarto part needs neither the browser nor the
    # Lean packages, the browser part the browser, the rest the Lean packages.
    jobs = check_jobs()
    parts = {n: j for n, j in jobs.items() if n.startswith("integration")}
    assert sorted(parts) == [
        "integration-browser",
        "integration-other",
        "integration-quarto",
    ]
    for name, job in parts.items():
        assert groups_of(job) == [name]
        assert "needs" not in job and "permissions" not in job, name
        [prepare] = [
            s for s in job["steps"] if s.get("uses") == "./.github/actions/prepare"
        ]
        given = prepare.get("with", {})
        browser = "true" if name == "integration-browser" else "false"
        assert given.get("browser", "false") == browser, name
        packages = "restore" if name == "integration-other" else "none"
        assert given.get("lean-packages", "none") == packages, name


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
    for name in ("build", "e2e"):
        [fetch] = [
            s
            for s in jobs[name]["steps"]
            if s.get("id") == "base" and "fetch-base.sh" in s.get("run", "")
        ]
        assert "github.event_name == 'pull_request'" in fetch["if"]
        assert "push" not in fetch["if"]
    # The step that passes the base needs the step that accepted one.
    for name in ("build", "e2e"):
        [with_base] = steps_with(jobs[name], BASE_OPTION)
        assert with_base["if"] == "${{ steps.base.outputs.accepted == 'true' }}"


def test_the_base_is_fetched_with_the_read_token_and_nothing_else():
    jobs = load(CI)["jobs"]
    for name in ("build", "e2e"):
        for step in steps_with(jobs[name], "fetch-base.sh"):
            assert step["env"]["GH_TOKEN"] == "${{ github.token }}"
            assert set(step["env"]) <= {"GH_TOKEN", "BASE_RUN"}
    # What the build job accepted reaches the checking jobs as a run number,
    # which the script checks again; the number is never put into a command.
    assert load(CI)["jobs"]["build"]["outputs"] == {
        "base-run": "${{ steps.base.outputs.run-id }}"
    }
    for step in steps_with(jobs["e2e"], "--run"):
        assert step["env"]["BASE_RUN"] == "${{ needs.build.outputs.base-run }}"
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
    build = load(CI)["jobs"]["build"]
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
            assert step["with"]["name"] != "verification-base"
            assert "run-id" not in step["with"]
            assert "github-token" not in step["with"]
