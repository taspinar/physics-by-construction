"""The route of a change on "How we verify the science" (Issue #469): every
count and configured fact of the section is read from its file, the four
groups of checks cover every check of verify.conf exactly once, the diagram
and its text version show the same steps, and a fact that cannot be read
fails the build of the page."""

import re
import shutil
import xml.etree.ElementTree as ET
from itertools import product
from pathlib import Path

import pytest
import yaml
from support import verify_conf
from support.paths import REPO_ROOT, SITE_SOURCE

from pbc.authoring import route
from pbc.authoring.route import (
    BACKS,
    GROUPS,
    STEPS,
    RouteError,
    RoutePage,
    coverage_problems,
    read_facts,
    route_page,
)

SVG = "{http://www.w3.org/2000/svg}"


@pytest.fixture(scope="module")
def page() -> RoutePage:
    return route_page()


def test_every_check_of_verify_conf_is_in_exactly_one_group(page: RoutePage):
    assert coverage_problems(page.facts.checks) == []
    # The module reads verify.conf as the tests of the checks do.
    assert [c.name for c in page.facts.checks] == list(verify_conf.checks())
    assert {c.name: c.group for c in page.facts.checks} == verify_conf.groups()


def test_the_counts_come_from_their_files(page: RoutePage):
    """Each number the page shows equals what an independent reading of the
    file gives."""
    jobs = yaml.safe_load((REPO_ROOT / route.CI_WORKFLOW).read_text())["jobs"]
    expected_jobs = 0
    for job in jobs.values():
        runs = " ".join(str(s.get("run", "")) for s in job.get("steps", []))
        if "verify.sh --all --only" not in runs:
            continue
        matrix = job.get("strategy", {}).get("matrix")
        expected_jobs += 1 if matrix is None else len(list(product(*matrix.values())))
    self_tests = [
        line
        for line in (REPO_ROOT / route.WORKFLOW_CONF).read_text().splitlines()
        if re.match(r"^[a-z0-9-]+(?: \[[a-z0-9-]+\])?: ", line)
        and not line.startswith("paths:")
    ]
    cards = list((REPO_ROOT / route.REGISTRY).glob("*.yaml"))
    rounds = re.search(
        r"^MAX_ROUNDS=(\d+)$", (REPO_ROOT / route.RUN_FEATURE).read_text(), re.M
    )
    assert page.facts.numbers == {
        "checks": len(verify_conf.checks()),
        "jobs": expected_jobs,
        "self_tests": len(self_tests),
        "cards": len(cards),
        "rounds": int(rounds.group(1)),
    }
    assert page.facts.workflow.summary == "verify"
    assert page.facts.workflow.deploy == "deploy"
    assert page.facts.roles.implementer != page.facts.roles.reviewer


def test_every_number_on_the_page_is_a_generated_one(page: RoutePage):
    """The section types no count: every number in its text is a count read
    from a file, a step number, or the size of a group."""
    text = re.sub(r"<svg.*?</svg>", "", str(page), flags=re.S)
    text = re.sub(r"\]\([^)]*\)", "]", text)  # link targets
    allowed = (
        set(page.facts.numbers.values())
        | {step.number for step in STEPS}
        | {len(group.checks) for group in GROUPS}
    )
    found = {int(n) for n in re.findall(r"\d+", text)}
    assert found <= allowed, sorted(found - allowed)
    for name, value in page.facts.numbers.items():
        assert str(value) in text, name


def _svg(page: RoutePage) -> ET.Element:
    match = re.search(r"<svg.*?</svg>", page.diagram(), flags=re.S)
    return ET.fromstring(match.group(0))


def _shift(element: ET.Element) -> tuple[int, int]:
    match = re.fullmatch(
        r"--wide-shift: translate\((-?\d+)px, (-?\d+)px\)", element.get("style")
    )
    return int(match.group(1)), int(match.group(2))


def test_the_drawing_and_the_list_show_the_same_steps(page: RoutePage):
    svg = _svg(page)
    texts = [t.text for t in svg.iter(f"{SVG}text")]
    listed = page.steps()
    for step in STEPS:
        assert f"{step.number} {step.title}" in texts, step.title
        assert f"\n{step.number}. **" in "\n" + listed
    for back in BACKS:
        for line in back.label:
            assert line.format(**page.values) in texts, line
        assert back.text.format(**page.values) in listed
    # The steps where the owner decides are marked, and no other: a box
    # with the class gate, whose title stands at its top left.
    corners = {
        (int(r.get("x")) + 10, int(r.get("y")) + 24)
        for r in svg.iter(f"{SVG}rect")
        if "gate" in r.get("class").split()
    }
    gates = {
        t.text
        for t in svg.iter(f"{SVG}text")
        if (int(t.get("x")), int(t.get("y"))) in corners
    }
    assert gates == {f"{s.number} {s.title}" for s in STEPS if s.gate}


def _overlaps(boxes: list[tuple[int, int]]) -> list[tuple]:
    found = []
    for i, (x1, y1) in enumerate(boxes):
        for x2, y2 in boxes[i + 1 :]:
            if abs(x1 - x2) < route._BOX_WIDTH and abs(y1 - y2) < route._BOX_HEIGHT:
                found.append(((x1, y1), (x2, y2)))
    return found


def test_the_boxes_stand_in_both_layouts_without_overlap(page: RoutePage):
    """Every box is drawn at its place in the column and carries the shift
    to its place in the wide layout; in each layout the boxes lie inside the
    drawing and apart from each other."""
    svg = _svg(page)
    narrow, wide = route.narrow_layout(), route.wide_layout()
    groups = [g for g in svg.iter(f"{SVG}g") if "movable" in (g.get("class") or "")]
    assert len(groups) == len(STEPS)
    placed = {}
    for group in groups:
        rect = group.find(f"{SVG}rect")
        at = (int(rect.get("x")), int(rect.get("y")))
        dx, dy = _shift(group)
        placed[at] = (at[0] + dx, at[1] + dy)
    assert set(placed) == set(narrow.boxes.values())
    assert set(placed.values()) == set(wide.boxes.values())
    for layout, boxes in ((narrow, list(placed)), (wide, list(placed.values()))):
        assert _overlaps(boxes) == []
        for x, y in boxes:
            assert x >= 0 and x + route._BOX_WIDTH <= layout.width
            assert y >= 0 and y + route._BOX_HEIGHT <= layout.height
    scale = re.search(r"scale\(([\d.]+)\)", svg.find(f"{SVG}g").get("style"))
    assert float(scale.group(1)) == pytest.approx(narrow.width / wide.width, abs=1e-4)
    assert svg.get("style") == f"--wide-aspect: {wide.width} / {wide.height}"


def test_the_drawing_is_an_image_with_its_title_and_description(page: RoutePage):
    svg = _svg(page)
    assert svg.get("role") == "img"
    title = svg.find(f"{SVG}title")
    description = svg.find(f"{SVG}desc")
    assert svg.get("aria-labelledby") == f"{title.get('id')} {description.get('id')}"
    assert title.text == route.DIAGRAM_TITLE
    assert description.text == page.description()
    for step in STEPS:
        assert f"{step.number} {step.title}" in description.text
    ids = [e.get("id") for e in svg.iter() if e.get("id")]
    assert len(ids) == len(set(ids))
    # No external resource: the only address is the SVG namespace.
    assert "http" not in ET.tostring(svg, encoding="unicode").replace(
        "http://www.w3.org/2000/svg", ""
    )
    for element in svg.iter(f"{SVG}path"):
        marker = element.get("marker-end", "")
        assert marker == "" or marker[5:-1] in ids, marker


def test_the_page_types_no_count():
    """The Markdown of the section outside its generated parts has no number
    but the three risk levels."""
    source = (SITE_SOURCE / "verify.qmd").read_text()
    section = source[source.index("## How a change reaches the site") :]
    section = re.sub(r"```\{python\}.*?```", "", section, flags=re.S)
    section = re.sub(r"\{#[^}]*\}", "", section)
    section = re.sub(r"\]\([^)]*\)", "]", section)
    numbers = re.findall(r"(?:Level )?\d+", section)
    assert numbers and set(numbers) <= {"Level 1", "Level 2", "Level 3"}, numbers


# --- A fact that cannot be read fails the build ------------------------------

_FILES = (
    route.VERIFY_CONF,
    route.WORKFLOW_CONF,
    route.CI_WORKFLOW,
    route.AGENTS_CONF,
    route.RUN_FEATURE,
    route.GUARDRAILS_CONF,
)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A copy of the files the page reads."""
    for file in _FILES:
        target = tmp_path / file
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO_ROOT / file, target)
    registry = tmp_path / route.REGISTRY
    registry.mkdir(parents=True)
    card = next(iter(sorted((REPO_ROOT / route.REGISTRY).glob("*.yaml"))))
    shutil.copy(card, registry / card.name)
    return tmp_path


def _edit(root: Path, file: str, old: str, new: str) -> None:
    path = root / file
    text = path.read_text()
    assert old in text, old
    path.write_text(text.replace(old, new))


def test_the_copy_reads_as_the_repository_does(root: Path):
    facts = read_facts(root)
    assert facts.numbers == {**read_facts().numbers, "cards": 1}
    assert facts.owner_identity == read_facts().owner_identity


def test_the_approval_paragraph_says_whether_the_owners_identity_is_set_up(
    root: Path,
):
    """Before the owner's setup the guardrails name no identity and the page
    says that the code-owner rule is not set up yet and that the owner
    merges by hand; once the line names the login, the page says that the
    identity's review of the exact commit is what the merge script needs
    (ADR 020 decision 3). A line that names no single login fails the build,
    as scripts/merge-feature.sh refuses it."""
    page = RoutePage(read_facts(root), "https://example.org/repo")
    assert page.facts.owner_identity is None
    before = page.approval()
    assert "not set up yet" in before and "by hand" in before
    assert "names no such identity" in before
    assert "Level 3" in before and before in str(page)
    guardrails = root / route.GUARDRAILS_CONF
    line = "\nowner-identity: @Owner-Review # the second identity\n"
    guardrails.write_text(guardrails.read_text() + line)
    page = RoutePage(read_facts(root), "https://example.org/repo")
    assert page.facts.owner_identity == "Owner-Review"
    after = page.approval()
    assert "names that identity" in after and "exactly its last commit" in after
    assert "not set up yet" not in after and "by hand" not in after
    for bad in ("owner-identity: one two\n", "owner-identity:\n"):
        guardrails.write_text(guardrails.read_text() + bad)
        with pytest.raises(RouteError, match=r"owner's identity|exactly one"):
            route.read_owner_identity(root)


def test_a_reviewer_of_the_implementers_provider_fails(root: Path):
    _edit(root, route.AGENTS_CONF, "reviewer: codex", "reviewer: claude")
    with pytest.raises(RouteError, match="different provider"):
        read_facts(root)


def test_a_missing_role_or_round_limit_fails(root: Path):
    _edit(root, route.RUN_FEATURE, "MAX_ROUNDS=", "ROUNDS=")
    with pytest.raises(RouteError, match="MAX_ROUNDS"):
        route.read_round_limit(root)
    _edit(root, route.AGENTS_CONF, "implementer:", "builder:")
    with pytest.raises(RouteError, match="names no implementer"):
        route.read_roles(root)


def test_a_summary_job_that_misses_a_check_job_fails(root: Path):
    _edit(
        root,
        route.CI_WORKFLOW,
        "needs: [code, workflow, integration-quarto",
        "needs: [workflow, integration-quarto",
    )
    with pytest.raises(RouteError, match="needs"):
        route.read_workflow(root)


def test_a_check_in_no_group_fails_the_section(root: Path):
    _edit(
        root,
        route.VERIFY_CONF,
        "lint [code]:",
        "typing [code]: uv run mypy\nlint [code]:",
    )
    page = RoutePage(read_facts(root), "https://example.org/repo")
    assert coverage_problems(page.facts.checks) == ["typing is in no group"]
    with pytest.raises(RouteError, match="typing is in no group"):
        page.checks()
