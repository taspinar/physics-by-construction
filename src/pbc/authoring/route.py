"""The route of a change, for "How we verify the science" (Issue #469).

What the section states about the process is read, when the page is built,
from the files that carry the rules, so that no count and no configured fact
is typed into the page: the checks of ``scripts/verify.conf`` and their
groups, the self-tests of ``scripts/verify-workflow.conf``, the jobs of the
CI workflow, the providers of the implementer and the reviewer in
``.agents/agents.conf``, the review-round limit of
``scripts/run-feature.sh``, and the dataset cards of ``data/registry``. A
fact that cannot be read raises, which fails the build, as a worked example
whose target is missing does (``pbc.authoring.verify``).

The diagram of the route is drawn here as inline SVG, in two layouts from
one list of steps (a wide one for a desktop, a column for a phone; the style
sheet shows one of them by the width of the figure), and the ordered list
after it is the text version of everything the diagram shows. The four
groups of checks map every check of ``verify.conf`` to one group; a test
keeps the mapping complete.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from html import escape
from itertools import product
from pathlib import Path

import yaml

from pbc.authoring.repository import REPOSITORY_ROOT, repository_url
from pbc.data.card import load_cards

VERIFY_CONF = "scripts/verify.conf"
WORKFLOW_CONF = "scripts/verify-workflow.conf"
CI_WORKFLOW = ".github/workflows/ci.yml"
AGENTS_CONF = ".agents/agents.conf"
RUN_FEATURE = "scripts/run-feature.sh"
REGISTRY = "data/registry"
PROCESS_DOCUMENT = "docs/process.md"

# '<name>: <command>' or '<name> [<group>]: <command>', as verify.sh reads it.
_CHECK_LINE = re.compile(
    r"^([a-z0-9][a-z0-9-]*)(?:\s*\[([a-z0-9][a-z0-9-]*)\])?:\s*(.*\S)\s*$"
)
# The entries of the two configurations that declare no check.
_RESERVED = {"targeted", "after", "paths"}
_DEFAULT_GROUP = "default"
_ROLE_LINE = re.compile(r"^([a-z][a-z-]*):\s*([a-z]+)\s+(\S+)\s*$")
_ROUNDS_LINE = re.compile(r"^MAX_ROUNDS=(\d+)\s*$", re.MULTILINE)
# How the page names a provider of .agents/agents.conf.
_PROVIDERS = {"claude": "Claude", "codex": "Codex"}
_RUN_CHECKS = "./scripts/verify.sh --all --only"
_SUMMARY_SCRIPT = "ci-aggregate.sh"
_DEPLOY_ACTION = "deploy-pages"


class RouteError(ValueError):
    """A fact of the process that the page cannot read from its file."""


# --- The facts, read from their files ----------------------------------------


@dataclass(frozen=True)
class Check:
    name: str
    group: str


@dataclass(frozen=True)
class Workflow:
    """The jobs of the CI workflow: the ones that run the checks, with a
    matrix expanded into one name per part; the summary job that needs each
    of them; the job that publishes the site."""

    check_jobs: tuple[str, ...]
    summary: str
    deploy: str


@dataclass(frozen=True)
class Roles:
    implementer: str  # the provider, as the page names it
    reviewer: str


@dataclass(frozen=True)
class Facts:
    checks: tuple[Check, ...]
    self_tests: tuple[str, ...]
    workflow: Workflow
    roles: Roles
    round_limit: int
    cards: tuple[str, ...]

    @property
    def numbers(self) -> dict[str, int]:
        """Every count the page shows, by the name the texts use."""
        return {
            "checks": len(self.checks),
            "jobs": len(self.workflow.check_jobs),
            "self_tests": len(self.self_tests),
            "cards": len(self.cards),
            "rounds": self.round_limit,
        }


def _check_lines(path: Path) -> list[tuple[str, str, str]]:
    if not path.is_file():
        raise RouteError(f"{path} is missing")
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = _CHECK_LINE.match(line)
        if match is None:
            raise RouteError(f"{path}: malformed line {line!r}")
        name, group, command = match.groups()
        if name in _RESERVED:
            continue
        lines.append((name, group or _DEFAULT_GROUP, command))
    if not lines:
        raise RouteError(f"{path} declares no check")
    return lines


def read_checks(root: Path = REPOSITORY_ROOT) -> tuple[Check, ...]:
    """The checks of ``scripts/verify.conf``, in file order."""
    return tuple(
        Check(name, group) for name, group, _ in _check_lines(root / VERIFY_CONF)
    )


def read_self_tests(root: Path = REPOSITORY_ROOT) -> tuple[str, ...]:
    """The self-tests of the workflow scripts, ``scripts/verify-workflow.conf``."""
    return tuple(name for name, _, _ in _check_lines(root / WORKFLOW_CONF))


def _matrix_parts(job: Mapping) -> list[str]:
    """The names of a job's parts: one for a job without a matrix, else one
    per combination of its matrix lists, as ``<job>-<value>``."""
    matrix = (job.get("strategy") or {}).get("matrix")
    if matrix is None:
        return [""]
    if not isinstance(matrix, dict) or any(
        key in ("include", "exclude") or not isinstance(values, list)
        for key, values in matrix.items()
    ):
        raise RouteError(f"{CI_WORKFLOW}: a matrix this page cannot count")
    return [
        "-".join(str(value) for value in combination)
        for combination in product(*matrix.values())
    ]


def _steps_of(job: Mapping) -> Iterator[Mapping]:
    return (step for step in job.get("steps") or [] if isinstance(step, dict))


def read_workflow(root: Path = REPOSITORY_ROOT) -> Workflow:
    """The jobs of the CI workflow, from ``.github/workflows/ci.yml``.

    The check jobs are the jobs with a step that runs ``./scripts/verify.sh
    --all --only``; the summary job runs the aggregate script and must need
    exactly the check jobs; the deploy job uses the Pages deployment action.
    Anything else raises."""
    path = root / CI_WORKFLOW
    if not path.is_file():
        raise RouteError(f"{path} is missing")
    jobs = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("jobs") or {}
    check_jobs: list[str] = []
    checking: set[str] = set()
    summary = deploy = None
    for name, job in jobs.items():
        runs = " ".join(str(step.get("run", "")) for step in _steps_of(job))
        uses = " ".join(str(step.get("uses", "")) for step in _steps_of(job))
        if _RUN_CHECKS in runs:
            checking.add(name)
            check_jobs += [
                f"{name}-{part}" if part else name for part in _matrix_parts(job)
            ]
        if _SUMMARY_SCRIPT in runs:
            if summary is not None:
                raise RouteError(f"{CI_WORKFLOW}: two summary jobs")
            summary = name
        if _DEPLOY_ACTION in uses:
            deploy = name
    if summary is None:
        raise RouteError(f"{CI_WORKFLOW}: no job runs {_SUMMARY_SCRIPT}")
    needs = jobs[summary].get("needs")
    needed = set(needs if isinstance(needs, list) else [needs])
    if needed != checking:
        raise RouteError(
            f"{CI_WORKFLOW}: the job {summary} needs {sorted(needed)}, not the"
            f" jobs that run the checks, {sorted(checking)}"
        )
    if deploy is None:
        raise RouteError(f"{CI_WORKFLOW}: no job uses {_DEPLOY_ACTION}")
    if jobs[deploy].get("needs") != summary:
        raise RouteError(f"{CI_WORKFLOW}: the job {deploy} does not need {summary}")
    return Workflow(tuple(check_jobs), summary, deploy)


def read_roles(root: Path = REPOSITORY_ROOT) -> Roles:
    """The providers of the implementer and the reviewer, from
    ``.agents/agents.conf``; the page says they differ, so equal providers
    raise."""
    path = root / AGENTS_CONF
    if not path.is_file():
        raise RouteError(f"{path} is missing")
    providers = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = _ROLE_LINE.match(line)
        if match is None:
            raise RouteError(f"{path}: malformed line {line!r}")
        providers[match.group(1)] = match.group(2)
    named = {}
    for role in ("implementer", "reviewer"):
        if role not in providers:
            raise RouteError(f"{path} names no {role}")
        if providers[role] not in _PROVIDERS:
            raise RouteError(
                f"{path}: the page has no name for the provider {providers[role]!r}"
            )
        named[role] = _PROVIDERS[providers[role]]
    if named["implementer"] == named["reviewer"]:
        raise RouteError(
            f"{path}: the implementer and the reviewer are both {named['reviewer']}"
            " models; the page says that the reviewer is of a different provider"
        )
    return Roles(named["implementer"], named["reviewer"])


def read_round_limit(root: Path = REPOSITORY_ROOT) -> int:
    """The number of review rounds a feature may take, ``MAX_ROUNDS`` of
    ``scripts/run-feature.sh``."""
    path = root / RUN_FEATURE
    if not path.is_file():
        raise RouteError(f"{path} is missing")
    found = _ROUNDS_LINE.findall(path.read_text(encoding="utf-8"))
    if len(found) != 1:
        raise RouteError(f"{path} sets MAX_ROUNDS {len(found)} times, not once")
    return int(found[0])


def read_cards(root: Path = REPOSITORY_ROOT) -> tuple[str, ...]:
    """The dataset cards of ``data/registry``."""
    cards = tuple(load_cards(root / REGISTRY))
    if not cards:
        raise RouteError(f"{root / REGISTRY} holds no dataset card")
    return cards


def read_facts(root: Path = REPOSITORY_ROOT) -> Facts:
    return Facts(
        read_checks(root),
        read_self_tests(root),
        read_workflow(root),
        read_roles(root),
        read_round_limit(root),
        read_cards(root),
    )


# --- The route ---------------------------------------------------------------


@dataclass(frozen=True)
class Step:
    """One step of the route: its number, its title, the two short lines
    of its box, and the sentence of the text version. ``gate`` marks a step
    where the owner decides. The texts may name a number of ``Facts.numbers``
    or a role in braces."""

    number: int
    title: str
    lines: tuple[str, str]
    text: str
    gate: bool = False


@dataclass(frozen=True)
class Back:
    """An arrow back along the route, with its label of one or two lines."""

    source: int
    target: int
    label: tuple[str, ...]
    text: str


STEPS = (
    Step(
        1,
        "Issue",
        ("the owner: criteria", "and a risk level"),
        "**The Issue.** The owner, one person, opens an Issue with its acceptance"
        " criteria and its risk level, and a plan is written when the change"
        " needs one.",
        gate=True,
    ),
    Step(
        2,
        "Implementation",
        ("an agent, in its own", "branch and worktree"),
        "**The implementation.** An implementer agent, a {implementer} model,"
        " makes the change in a branch and a worktree of its own, never on"
        " `main`, and records for every criterion of the Issue what shows that"
        " it is met.",
    ),
    Step(
        3,
        "Verification",
        ("one script, the tier", "the change needs"),
        "**The verification.** One script runs the checks on the agent's"
        " machine, at the tier the change needs: the targeted run for an"
        " ordinary change, a run against a verified base when a change alters"
        " what other pages show of a lesson, the full run when the change"
        " touches what every page shares or a check itself. A failing check"
        " sends the change back to step 2. A pass holds for the exact content"
        " it ran on and for nothing changed after it.",
    ),
    Step(
        4,
        "Pull request, CI",
        ("the same checks on", "GitHub, in {jobs} jobs"),
        "**The pull request and CI.** The change is published as a draft pull"
        " request, and GitHub runs the same checks again in {jobs} jobs, with"
        " one more job that passes only when every one of them did: the one"
        " required check of `main`. A job that fails sends the change back to"
        " step 2.",
    ),
    Step(
        5,
        "Independent review",
        ("a second model, then", "the triage per finding"),
        "**The independent review.** A reviewer of a different provider, a"
        " {reviewer} model with read access only, reads the complete change"
        " against the Issue, its content included, and reports its findings."
        " Each finding is triaged: fixed now, deferred with a linked Issue, or"
        " accepted with a rationale. A fix goes back to step 2, and the"
        " reviewer reads the result again. At most {rounds} rounds are used;"
        " then the owner decides.",
    ),
    Step(
        6,
        "Owner's approval",
        ("Level 3: the exact", "commit, by the owner"),
        "**The owner's approval.** The owner reads the pull request. A change"
        " at Level 3 also needs the owner's approving review of the exact"
        " commit, which never carries over to content pushed after it.",
        gate=True,
    ),
    Step(
        7,
        "Merge",
        ("only the owner;", "no agent merges"),
        "**The merge.** Only the owner merges a pull request. No agent merges"
        " one, and no script takes an agent's statement as the owner's"
        " approval.",
        gate=True,
    ),
    Step(
        8,
        "Publication",
        ("main runs everything", "again, then deploys"),
        "**The publication.** The push to `main` runs every check and every"
        " lesson again, and the deploy job publishes exactly the site that"
        " the build job of that run made.",
    ),
)

BACKS = (
    Back(
        3,
        2,
        ("a failing check: back to 2",),
        "from the verification, when a check fails",
    ),
    Back(
        5,
        2,
        ("findings: back to 2,", "at most {rounds} rounds"),
        "from the review, with its findings, for at most {rounds} rounds",
    ),
)

# The geometry, in SVG user units (CSS pixels at the natural size). The
# drawing is one SVG laid out as a column, its viewBox, with the same box
# width as the wide layout: for a wide figure the style sheet scales the
# whole by the wide scale, moves each box and each label line by its wide
# shift, and shows the arrows of that layout (docs/atelier.md, "The route of
# a change"). The texts exist once, so none is hidden at any width.
_BOX_HEIGHT = 76
_BOX_WIDTH = 160
_LINE = 14  # the height of one line of a label
_NARROW = {"width": 320, "left": 12, "gap": 36, "top": 12}
_WIDE = {"width": 760, "gap": 40, "top": 48, "channel": 72}


@dataclass(frozen=True)
class Layout:
    """Where the boxes and the labels stand in one layout, and its arrows."""

    width: int
    height: int
    boxes: dict[int, tuple[int, int]]  # step number -> top left corner
    labels: dict[int, tuple[int, int]]  # index into BACKS -> first line's anchor
    flows: tuple[tuple[tuple[int, int], ...], ...]  # the forward arrows
    backs: tuple[tuple[tuple[int, int], ...], ...]  # the arrows back, as BACKS


def narrow_layout() -> Layout:
    """One column: the boxes under each other, the arrows back in the
    channel at the right, their labels in the gaps between the boxes."""
    left, gap, top = _NARROW["left"], _NARROW["gap"], _NARROW["top"]
    stride = _BOX_HEIGHT + gap
    boxes = {s.number: (left, top + (s.number - 1) * stride) for s in STEPS}
    height = top + len(STEPS) * _BOX_HEIGHT + (len(STEPS) - 1) * gap + top
    centre = left + _BOX_WIDTH // 2
    right = left + _BOX_WIDTH
    flows = tuple(
        ((centre, y + _BOX_HEIGHT), (centre, y + stride))
        for n, (_, y) in boxes.items()
        if n < len(STEPS)
    )
    backs = []
    labels = {}
    for i, back in enumerate(BACKS):
        source_y = boxes[back.source][1]
        target_y = boxes[back.target][1]
        channel = _NARROW["width"] - 24 + 12 * i
        into = target_y + 50 - 24 * i
        backs.append(
            (
                (right, source_y + 38),
                (channel, source_y + 38),
                (channel, into),
                (right, into),
            )
        )
        lines = len(back.label)
        labels[i] = (_NARROW["width"] - 36, source_y - gap + 14 - 2 * (lines - 1))
    return Layout(_NARROW["width"], height, boxes, labels, flows, tuple(backs))


def wide_layout() -> Layout:
    """Two rows of four: the first left to right, the second right to left
    under it, so that step 5 stands under step 4; the arrow back from the
    verification is an arc above the first row, the one from the review
    runs through the channel between the rows."""
    gap, top, channel = _WIDE["gap"], _WIDE["top"], _WIDE["channel"]
    stride = _BOX_WIDTH + gap
    row2 = top + _BOX_HEIGHT + channel
    height = row2 + _BOX_HEIGHT + 8
    half = len(STEPS) // 2
    boxes = {}
    for s in STEPS:
        column = s.number - 1 if s.number <= half else len(STEPS) - s.number
        boxes[s.number] = (column * stride, top if s.number <= half else row2)
    middle = _BOX_HEIGHT // 2
    flows = []
    for n, (x, y) in boxes.items():
        if n == half:
            flows.append(
                ((x + _BOX_WIDTH // 2, y + _BOX_HEIGHT), (x + _BOX_WIDTH // 2, row2))
            )
        elif n < half:
            flows.append(((x + _BOX_WIDTH, y + middle), (x + stride, y + middle)))
        elif n < len(STEPS):
            flows.append(((x, y + middle), (x - gap, y + middle)))
    (x2, y2), (x3, y3), (x5, y5) = boxes[2], boxes[3], boxes[5]
    arc = top - 24
    start = x5 + _BOX_WIDTH // 2 - 40
    line = row2 - channel // 2
    backs = (
        (
            (x3 + _BOX_WIDTH // 2, y3),
            (x3 + _BOX_WIDTH // 2, arc),
            (x2 + _BOX_WIDTH // 2, arc),
            (x2 + _BOX_WIDTH // 2, y3),
        ),
        (
            (start, y5),
            (start, line),
            (x2 + _BOX_WIDTH // 2, line),
            (x2 + _BOX_WIDTH // 2, y2 + _BOX_HEIGHT),
        ),
    )
    labels = {
        0: ((x3 + x2 + _BOX_WIDTH) // 2, arc - 8),
        1: (
            (start + x2 + _BOX_WIDTH // 2) // 2,
            line - 6 - _LINE * (len(BACKS[1].label) - 1),
        ),
    }
    return Layout(_WIDE["width"], height, boxes, labels, tuple(flows), backs)


def _fill(text: str, values: Mapping[str, object]) -> str:
    return text.format(**values)


def _escape(text: str) -> str:
    return escape(text, quote=True)


def _shift(narrow: tuple[int, int], wide: tuple[int, int]) -> str:
    dx, dy = wide[0] - narrow[0], wide[1] - narrow[1]
    return f'style="--wide-shift: translate({dx}px, {dy}px)"'


def _box(
    step: Step, at: tuple[int, int], wide: tuple[int, int], values: Mapping[str, object]
) -> list[str]:
    x, y = at
    kind = "step gate" if step.gate else "step"
    title = _escape(f"{step.number} {step.title}")
    first, second = (_escape(_fill(line, values)) for line in step.lines)
    return [
        f'<g class="movable" {_shift(at, wide)}>',
        f'<rect class="{kind}" x="{x}" y="{y}" width="{_BOX_WIDTH}"'
        f' height="{_BOX_HEIGHT}"/>',
        f'<text class="title" x="{x + 10}" y="{y + 24}">{title}</text>',
        f'<text class="detail" x="{x + 10}" y="{y + 44}">{first}</text>',
        f'<text class="detail" x="{x + 10}" y="{y + 60}">{second}</text>',
        "</g>",
    ]


def _arrow(points: tuple[tuple[int, int], ...], back: bool = False) -> str:
    kind = "back" if back else "flow"
    path = " ".join(
        f"{'M' if i == 0 else 'L'}{x},{y}" for i, (x, y) in enumerate(points)
    )
    return f'<path class="{kind}" d="{path}" marker-end="url(#route-{kind})"/>'


def _label(
    back: Back, at: tuple[int, int], wide: tuple[int, int], values: Mapping[str, object]
) -> list[str]:
    x, y = at
    return [
        f'<text class="back-label movable" {_shift(at, wide)} x="{x}"'
        f' y="{y + _LINE * i}" text-anchor="end">{_escape(_fill(line, values))}</text>'
        for i, line in enumerate(back.label)
    ]


def _svg(values: Mapping[str, object], title: str, description: str) -> str:
    narrow, wide = narrow_layout(), wide_layout()
    scale = narrow.width / wide.width
    arrows = {
        "narrow": [_arrow(a) for a in narrow.flows]
        + [_arrow(a, back=True) for a in narrow.backs],
        "wide": [_arrow(a) for a in wide.flows]
        + [_arrow(a, back=True) for a in wide.backs],
    }
    body = []
    for layout, paths in arrows.items():
        body += [f'<g class="arrows-{layout}">', *paths, "</g>"]
    for step in STEPS:
        body += _box(step, narrow.boxes[step.number], wide.boxes[step.number], values)
    for i, back in enumerate(BACKS):
        body += _label(back, narrow.labels[i], wide.labels[i], values)
    markers = "".join(
        f'<marker id="route-{kind}" class="{kind}-head" viewBox="0 0 10 10"'
        ' refX="9" refY="5" markerWidth="7" markerHeight="7"'
        ' orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z"/></marker>'
        for kind in ("flow", "back")
    )
    return "\n".join(
        [
            '<svg xmlns="http://www.w3.org/2000/svg" class="route-diagram"'
            f' viewBox="0 0 {narrow.width} {narrow.height}"'
            ' preserveAspectRatio="xMinYMin slice" role="img"'
            ' aria-labelledby="route-title route-description"'
            f' style="--wide-aspect: {wide.width} / {wide.height}">',
            f'<title id="route-title">{_escape(title)}</title>',
            f'<desc id="route-description">{_escape(description)}</desc>',
            f"<defs>{markers}</defs>",
            f'<g class="route-all" style="--wide-scale: scale({scale:.5f})">',
            *body,
            "</g>",
            "</svg>",
        ]
    )


# --- What the checks cover ---------------------------------------------------


@dataclass(frozen=True)
class Coverage:
    """One line of a group: what the named checks of ``verify.conf`` do."""

    text: str
    checks: tuple[str, ...]


@dataclass(frozen=True)
class Group:
    title: str
    coverage: tuple[Coverage, ...]
    more: tuple[str, ...] = ()  # sentences about what is not a check of verify.conf

    @property
    def checks(self) -> tuple[str, ...]:
        return tuple(name for line in self.coverage for name in line.checks)


GROUPS = (
    Group(
        "Science and lessons",
        (
            Coverage(
                "Every lesson's front matter, sections, place in the learning path,"
                " displayed code, figures, and claims follow the lesson rules, and"
                " every claim names evidence that exists",
                ("lesson-checks",),
            ),
            Coverage(
                "Each lesson a change selects is rendered on its own in a clone of"
                " the tree and its experiment is run with a reader's commands,"
                " within the page budget; its figures and numbers must agree with"
                " the page",
                ("lesson-pages",),
            ),
            Coverage(
                "Every Lean module builds against Mathlib, without `sorry` and"
                " without an axiom of the project",
                ("lean-build",),
            ),
            Coverage(
                "Every dataset card is valid, and every committed sample has a"
                " card that permits it, stays under the size caps, matches its"
                " checksum, and has a parsing test; the registry holds {cards}"
                " cards",
                ("dataset-checks",),
            ),
            Coverage(
                "Every lesson the run executed is executed again in a fresh"
                " clone, and the figures and the numbers it writes must equal"
                " what the page shows",
                ("site-checks-reproduction",),
            ),
        ),
    ),
    Group(
        "The published site",
        (
            Coverage(
                "The site is built with every page executed; a failing cell, a"
                " claim without evidence, or an equation that cannot become"
                " MathML stops the build",
                ("site-build",),
            ),
            Coverage(
                "The site is built a second time, elsewhere and later, and the"
                " two builds must be byte for byte the same",
                ("determinism",),
            ),
            Coverage(
                "Every built page is opened in a browser: readable without"
                " scripts, no request to another origin and no cookie, the"
                " accessibility scan, the keyboard pass, no sideways scrolling"
                " at phone, tablet, and desktop width, the payload budget, every"
                " link resolving, the search, the atlas, the glossary, and the"
                " learner's progress staying in the browser",
                ("site-checks-pages-1", "site-checks-pages-2", "site-checks-other"),
            ),
        ),
    ),
    Group(
        "Code and documents",
        (
            Coverage(
                "The Python sources pass the linter and the formatter",
                ("lint", "format"),
            ),
            Coverage("The unit tests of the package pass", ("unit-tests",)),
            Coverage(
                "The starter kits of the capstone products pass their tests"
                " against the current tree and at their pinned commit",
                ("starters",),
            ),
            Coverage(
                "Every script is named in the project map, every path the"
                " documentation names exists, every shell script parses, the"
                " files of the workflow are present, and a documentation site"
                " checks itself where a project has one",
                (
                    "docs-scripts",
                    "docs-references",
                    "shell-syntax",
                    "template-structure",
                    "documentation",
                ),
            ),
            Coverage(
                "The agent skills, which are guidance and never evidence, have"
                " their provenance records, and their digests match their files",
                ("skills-config",),
            ),
        ),
    ),
    Group(
        "The pipeline itself",
        (
            Coverage(
                "The machine has every prerequisite before anything runs, and"
                " the preflight reports each missing one with a fix",
                ("preflight", "preflight-test"),
            ),
            Coverage(
                "Every check fails on an input that violates it: the integration"
                " tests build small sites and lessons made to break one rule"
                " each, and must see each check fail",
                ("check-tests-quarto", "check-tests-browser", "check-tests-other"),
            ),
        ),
        more=(
            "The {self_tests} self-tests of the workflow scripts, one per"
            " script (the start of a feature, the review, the triage, the"
            " commit, the pull request, the merge, the risk level, the"
            " guardrails), run on every CI run and, on the agent's machine,"
            " whenever a workflow file changed.",
        ),
    ),
)


def coverage_problems(checks: tuple[Check, ...] = ()) -> list[str]:
    """Why ``GROUPS`` and the checks of ``verify.conf`` disagree: a check in
    no group, in two groups, or named by a group but not declared. Empty
    when the mapping is complete."""
    declared = [check.name for check in checks or read_checks()]
    named = [name for group in GROUPS for name in group.checks]
    problems = []
    for name in sorted(set(named)):
        if named.count(name) > 1:
            problems.append(f"{name} is in {named.count(name)} groups")
        if name not in declared:
            problems.append(f"{name} is not a check of {VERIFY_CONF}")
    problems += [f"{name} is in no group" for name in declared if name not in named]
    return problems


# --- The page ----------------------------------------------------------------

DIAGRAM_TITLE = "The route of a change, from the Issue to the publication"
_DESCRIPTION = (
    "Numbered boxes joined by arrows: {steps}. The boxes where the owner"
    " decides, {gates}, have a stronger outline. Dashed arrows point back to"
    " the implementation: {backs}. The list after the diagram gives every"
    " step."
)


@dataclass(frozen=True)
class RoutePage:
    facts: Facts
    repository: str  # the address of the repository, for the links to the rules

    @property
    def values(self) -> dict[str, object]:
        """What the texts may name in braces: every number and both roles."""
        return {
            **self.facts.numbers,
            "implementer": self.facts.roles.implementer,
            "reviewer": self.facts.roles.reviewer,
        }

    def _link(self, path: str) -> str:
        return f"{self.repository}/blob/main/{path}"

    def who(self) -> str:
        values = self.values
        return (
            "Four parties take part, and the files of the repository say which"
            " does what. The **owner**, one person, opens the Issues, reads"
            " every pull request, and is the only one who merges. An"
            f" **implementer agent**, a {values['implementer']} model, makes the"
            " change. An **independent reviewer**, a"
            f" {values['reviewer']} model from a different provider with read"
            " access only, reads it. The **checks**, one list that one script"
            " runs, decide mechanically what passes; they are the same on the"
            " agent's machine and on GitHub. The rules themselves are public:"
            f" [the process as it stands]({self._link(PROCESS_DOCUMENT)}), the"
            f" list of checks [`{VERIFY_CONF}`]({self._link(VERIFY_CONF)}), and"
            f" the CI workflow [`{CI_WORKFLOW}`]({self._link(CI_WORKFLOW)})."
        )

    def description(self) -> str:
        """What the diagram shows, for a reader who does not see it."""
        steps = ", ".join(f"{step.number} {step.title}" for step in STEPS)
        gates = ", ".join(str(step.number) for step in STEPS if step.gate)
        backs = "; ".join(_fill(back.text, self.values) for back in BACKS)
        return _DESCRIPTION.format(steps=steps, gates=gates, backs=backs)

    def diagram(self) -> str:
        """The diagram, as one raw HTML block."""
        return "\n".join(
            [
                "```{=html}",
                '<div class="route-figure">',
                _svg(self.values, DIAGRAM_TITLE, self.description()),
                "</div>",
                "```",
            ]
        )

    def steps(self) -> str:
        """The text version: every step, then the arrows back."""
        values = self.values
        lines = [f"{step.number}. {_fill(step.text, values)}" for step in STEPS]
        backs = " and ".join(_fill(back.text, values) for back in BACKS)
        return (
            "\n".join(lines)
            + f"\n\nTwo arrows point back to the implementation: {backs}."
        )

    def route(self) -> str:
        return "\n\n".join(
            [
                self.who(),
                "### The route {#route-steps}",
                "The diagram shows the steps; the list after it says what each"
                " step is, and the diagram shows nothing that the list does"
                " not say.",
                self.diagram(),
                self.steps(),
            ]
        )

    def checks(self) -> str:
        """The four groups, with the number of checks of each and what they
        cover, from the configuration."""
        values = self.values
        problems = coverage_problems(self.facts.checks)
        if problems:
            raise RouteError(
                "the groups and verify.conf disagree: " + "; ".join(problems)
            )
        workflow = self.facts.workflow
        parts = [
            f"The verification is one list of {values['checks']} checks,"
            f" [`{VERIFY_CONF}`]({self._link(VERIFY_CONF)}), which one script"
            " runs on the agent's machine and GitHub runs again in"
            f" {values['jobs']} jobs; the job `{workflow.summary}` passes only"
            " when every one of them did and is the one required check of"
            f" `main`, and on `main` the job `{workflow.deploy}` publishes the"
            " site after it. Every check must pass; none is optional, and a"
            " check is removed only by a decision record with evidence that"
            " something else covers it. In four groups:",
        ]
        for group in GROUPS:
            count = len(group.checks)
            parts.append(f"**{group.title}** ({count} checks)")
            parts.append(
                "\n".join(
                    f"- {_fill(line.text, values)}"
                    f" ({', '.join(f'`{name}`' for name in line.checks)})."
                    for line in group.coverage
                )
                + "".join(f"\n- {_fill(text, values)}" for text in group.more)
            )
        return "\n\n".join(parts)

    def __str__(self) -> str:
        return self.route() + "\n\n" + self.checks()


def route_page(root: Path = REPOSITORY_ROOT) -> RoutePage:
    """The route section of the page being built. It raises when a fact
    cannot be read from its file, which fails the build."""
    return RoutePage(read_facts(root), repository_url())
