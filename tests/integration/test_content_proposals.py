"""The content proposal workflow (F12, ADR 006): the form, the criteria, and
the markers that make a proposal assessable and agent-drafted content visible.
"""

import re

import yaml
from support.paths import REPO_ROOT

FORM = REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "lesson-proposal.yml"
GUIDE = REPO_ROOT / "docs" / "content-proposals.md"
PR_TEMPLATE = REPO_ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md"
CONTRIBUTING = REPO_ROOT / "CONTRIBUTING.md"
ADR = (
    REPO_ROOT
    / "docs"
    / "decisions"
    / "006-content-drafting-runs-on-the-maintainers-machine.md"
)


def fields() -> list[dict]:
    return [
        item
        for item in yaml.safe_load(FORM.read_text())["body"]
        if item["type"] != "markdown"
    ]


def test_form_asks_for_what_each_criterion_needs():
    labels = " | ".join(item["attributes"]["label"] for item in fields())
    for needed in (
        "Course",
        "Strand",
        "Fit and prerequisites",
        "How it is verified",
        "Scope and size",
    ):
        assert needed in labels, needed


def test_form_offers_every_course_of_the_site():
    from pbc.authoring import COURSES

    course = next(i for i in fields() if i["attributes"]["label"] == "Course")
    assert [c.id for c in COURSES] <= course["attributes"]["options"]
    assert "course" in GUIDE.read_text().split("## Assessment criteria")[1].lower()


def test_form_requires_its_answers_and_the_licence_confirmation():
    for item in fields():
        if item["attributes"]["label"] == "Sources and third-party material":
            continue
        if item["type"] == "checkboxes":
            assert all(box["required"] for box in item["attributes"]["options"])
        else:
            assert item["validations"]["required"], item["attributes"]["label"]
    licence = next(i for i in fields() if i["type"] == "checkboxes")
    assert "CONTRIBUTING.md" in licence["attributes"]["options"][0]["label"]


def test_form_is_a_valid_issue_form_that_labels_the_issue_as_a_proposal():
    form = yaml.safe_load(FORM.read_text())
    # GitHub Issue Forms require `name`, `description`, and `body` at the top
    # level; `about` belongs to Markdown templates and makes the form invalid.
    for key in ("name", "description", "body"):
        assert form.get(key), key
    assert "about" not in form
    assert form["labels"] == ["lesson-proposal"]


def test_guide_publishes_the_four_criteria_the_form_links_to():
    guide = GUIDE.read_text()
    assert "## Assessment criteria" in guide
    for criterion in (
        "Fit to the learning path",
        "Prerequisites",
        "Verifiability",
        "Scope",
    ):
        assert re.search(rf"^\| {criterion} \|", guide, re.M), criterion
    assert "docs/content-proposals.md#assessment-criteria" in FORM.read_text()


def test_guide_records_assessment_on_the_issue_and_marks_agent_drafts():
    guide = GUIDE.read_text()
    for label in (
        "lesson-proposal",
        "proposal-accepted",
        "proposal-needs-changes",
        "proposal-declined",
    ):
        assert label in guide
    assert "Agent-drafted:" in guide
    # publish-feature.sh rebuilds the description from the latest commit, so
    # the guide must say the marker is repeated in every fix-round commit.
    assert "fix-round commit" in guide
    assert "Agent-drafted content" in PR_TEMPLATE.read_text()


def test_decision_on_llm_credentials_is_recorded_and_references_exist():
    adr = ADR.read_text()
    assert "No LLM key is stored in CI" in adr
    assert "ADR 006" in (REPO_ROOT / "docs" / "architecture.md").read_text()
    assert ADR.name in (REPO_ROOT / "docs" / "decisions" / "README.md").read_text()
    assert "content-proposals.md" in CONTRIBUTING.read_text()


def test_no_workflow_reacts_to_issues_or_names_an_llm_provider():
    for path in (REPO_ROOT / ".github" / "workflows").glob("*.y*ml"):
        text = path.read_text()
        triggers = yaml.safe_load(text).get(True, {})
        assert "issues" not in triggers and "issue_comment" not in triggers, path.name
        for word in ("ANTHROPIC", "OPENAI"):
            assert word not in text.upper(), (path.name, word)
