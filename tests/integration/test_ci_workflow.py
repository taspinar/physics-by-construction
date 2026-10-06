"""Boundaries of the CI workflow (architecture invariants I2, I8, I9, I15).

These are permission and scope boundaries: a change that loosens one must
fail here and be made on purpose.
"""

import re
from pathlib import Path

import pytest
import yaml
from support.paths import REPO_ROOT

WORKFLOWS = sorted((REPO_ROOT / ".github" / "workflows").glob("*.y*ml"))
CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"


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


def test_every_action_is_pinned_by_commit_sha(workflow: dict):
    uses = [
        step["uses"]
        for job in workflow["jobs"].values()
        for step in job["steps"]
        if "uses" in step
    ]
    assert uses
    for action in uses:
        assert re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", action), action


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda path: path.name)
def test_no_secret_is_referenced(path: Path):
    assert "secrets." not in path.read_text()


def test_verify_job_runs_checks_only_through_verify_sh():
    job = load(CI)["jobs"]["verify"]
    commands = [step["run"] for step in job["steps"] if "run" in step]

    assert sum("./scripts/verify.sh" in command for command in commands) == 1
    # The other steps prepare the machine. None of them runs a check tool, so
    # no check exists only in CI.
    setup = "\n".join(c for c in commands if "./scripts/verify.sh" not in c)
    for tool in ("ruff", "pytest", "quarto", "lake", "scripts/", "tests/"):
        assert tool not in setup, tool


def test_verify_job_has_the_agreed_timeout():
    assert load(CI)["jobs"]["verify"]["timeout-minutes"] == 30


def test_built_site_is_uploaded_when_a_check_failed():
    job = load(CI)["jobs"]["verify"]
    upload = [
        step
        for step in job["steps"]
        if step.get("uses", "").startswith("actions/upload-pages-artifact@")
    ]

    assert len(upload) == 1
    assert upload[0]["with"]["path"] == "site/_site"
    # Without a condition GitHub skips the step after a failed one. This one
    # runs whenever a site was built, unless the run was cancelled.
    assert (
        upload[0]["if"]
        == "${{ !cancelled() && hashFiles('site/_site/index.html') != '' }}"
    )
    # A failed check still fails the job, so the deploy job, which needs it,
    # does not publish that site. No other step runs after a failure.
    assert "continue-on-error" not in job
    for step in job["steps"]:
        assert "continue-on-error" not in step, step
        assert step is upload[0] or "if" not in step, step


def test_deploy_job_publishes_the_verified_artifact_and_builds_nothing():
    job = load(CI)["jobs"]["deploy"]

    assert job["needs"] == "verify"
    assert job["if"] == "github.event_name == 'push' && github.ref == 'refs/heads/main'"
    # One step, the Pages deployment of the artifact uploaded by verify: no
    # checkout, no command.
    assert len(job["steps"]) == 1
    assert job["steps"][0]["uses"].startswith("actions/deploy-pages@")
    assert "run" not in job["steps"][0]
