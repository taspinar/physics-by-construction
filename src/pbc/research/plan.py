"""A research plan, declared before execution and run by the scripted route.

A plan is plain data in seven parts, ``PLAN_PARTS``: the kind (a
replication of a published result or an original investigation) and its
source, the specification in the seven parts of
``pbc.agents.specification``, the baselines, the withheld tests, the success
criteria, and the stopping conditions. ``check`` reads it against a
``Laboratory`` and refuses it with every problem it has before anything
runs: among them a plan without withheld tests, a withheld test that uses a
setting the search uses, and a plan without stopping conditions or whose
budget does not cover its stages.

The baselines are a positive control, the same specification on an action
whose answer is known (the throw without drag, whose best angle is
forty-five degrees), and a method baseline, an even grid over the varied
range with as many runs as the route needs. A withheld test is a finer scan
around the route's best setting, at a numerical setting the route never
uses; it is opened once, after the route has finished.

``freeze`` gives the digest of a plan, written before the first run.
``execute`` runs the stages in their order (the control, the route, the
baseline, the withheld tests) through the allowlist of the laboratory and
returns a ``PlanRecord``. Its verdict is the route's verdict only when every
success criterion is met; and it is the plan's verdict only when the plan
executed is the plan that was frozen.
"""

import copy
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pbc.agents.messages import ToolCall
from pbc.agents.specification import (
    NO_VERDICT,
    Laboratory,
    Record,
    Specification,
    SpecificationRejected,
    parse,
)
from pbc.agents.specification import (
    execute as route,
)
from pbc.evidence.records import digest_value
from pbc.research.ideas import runs_needed

PLAN_PARTS = (
    "kind",
    "source",
    "specification",
    "baselines",
    "withheld",
    "success",
    "stopping",
)
KINDS = ("replication", "original")
# The success criteria a plan can declare; a replication also declares the
# last one.
ROUTE_MET = "route criteria met"
CONTROL_PASSED = "control finds its known answer"
WITHHELD_PASSED = "withheld tests passed"
PUBLISHED_VERDICT = "published verdict reproduced"
CRITERIA = (ROUTE_MET, CONTROL_PASSED, WITHHELD_PASSED, PUBLISHED_VERDICT)

COMPLETED = "completed"
CONTROL_FAILED = "stopped: the positive control failed"
NOT_REGISTERED = "deviation: the plan executed is not the plan frozen"


@dataclass(frozen=True)
class Problem:
    """One reason a plan is refused: the part and what is wrong."""

    part: str
    message: str


class PlanRejected(ValueError):
    """A plan that was not executed, with every problem found."""

    def __init__(self, problems: list[Problem]):
        self.problems = tuple(problems)
        super().__init__("; ".join(f"{p.part}: {p.message}" for p in self.problems))


@dataclass(frozen=True)
class Withheld:
    """A withheld test: a scan of the varied variable from ``span``
    resolutions below the route's best setting to ``span`` above, in steps
    of one ``fraction`` of the resolution, at the numerical setting
    ``numerical``; it passes when its best setting lies inside the route's
    bracket. ``runs`` is its budget. A scan near an end of the varied range
    is clipped to that range, the range the specification was checked
    against, so a setting outside it is not run (#593)."""

    name: str
    numerical: float
    span: float
    fraction: int
    runs: int

    def settings(
        self,
        centre: float,
        resolution: float,
        bounds: tuple[float, float] = (-math.inf, math.inf),
    ) -> list[float]:
        step = resolution / self.fraction
        count = round(2.0 * self.span * self.fraction)
        start = centre - self.span * resolution
        low, high = bounds
        slack = 1e-9 * step
        return [
            min(max(setting, low), high)
            for i in range(count + 1)
            if low - slack <= (setting := start + i * step) <= high + slack
        ]


@dataclass(frozen=True)
class Plan:
    """A plan that passed ``check``."""

    kind: str
    source: Mapping[str, str]
    specification: Specification
    control_action: str
    control_answer: float
    grid_runs: int
    withheld: tuple[Withheld, ...]
    success: tuple[str, ...]
    max_runs: int
    stop_if_control_fails: bool
    published_verdict: str | None
    data: Mapping[str, Any]


def freeze(data: Mapping[str, Any]) -> str:
    """The digest of the plan ``data``, written before the first run."""
    return digest_value(data)


def _number(value: Any) -> bool:
    return (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _withheld(
    found: list[Problem],
    data: Mapping,
    specification: Specification | None,
    laboratory: Laboratory,
) -> list[Withheld]:
    """Every withheld test, and the rule that it is withheld: the route uses
    the numerical setting of the specification and, when the answer must be
    stable, half of it, so a test at either setting repeats what the search
    saw and checks nothing it did not."""
    tests = data.get("withheld")
    if not isinstance(tests, list) or not tests:
        found.append(
            Problem(
                "withheld",
                "there is no withheld test: the search's own record would be"
                " the only check of its answer",
            )
        )
        return []
    numerical = specification.numerical if specification is not None else None
    used = set()
    if numerical is not None:
        used = {numerical.value}
        if specification.stable:
            used.add(numerical.value / 2.0)
    accepted = []
    for test in tests:
        if not isinstance(test, Mapping) or not isinstance(test.get("name"), str):
            found.append(Problem("withheld", "a withheld test needs a name"))
            continue
        name = test["name"]
        if not all(_number(test.get(key)) for key in ("numerical", "span")) or not all(
            _count(test.get(key)) for key in ("fraction", "runs")
        ):
            found.append(
                Problem(
                    "withheld",
                    f"{name} needs numbers for numerical and span and whole"
                    " numbers for fraction and runs",
                )
            )
            continue
        withheld = Withheld(
            name, test["numerical"], test["span"], test["fraction"], test["runs"]
        )
        if numerical is None:
            found.append(
                Problem("withheld", f"{name} needs a numerical variable to set")
            )
            continue
        if withheld.numerical in used:
            found.append(
                Problem(
                    "withheld",
                    f"{name} is not withheld: the route uses"
                    f" {numerical.name} = {withheld.numerical:g}",
                )
            )
            continue
        bounds = next(
            p
            for p in laboratory.action(specification.measure).tool.parameters
            if p.name == numerical.name
        )
        if not bounds.low <= withheld.numerical <= bounds.high:
            found.append(
                Problem(
                    "withheld",
                    f"{name}: {numerical.name} = {withheld.numerical:g} is outside"
                    f" what {specification.measure} permits",
                )
            )
            continue
        needed = len(withheld.settings(0.0, 1.0))
        if needed > withheld.runs:
            found.append(
                Problem(
                    "withheld",
                    f"{name} needs {needed} runs and has a budget of {withheld.runs}",
                )
            )
            continue
        accepted.append(withheld)
    return accepted


def _stopping(found: list[Problem], data: Mapping) -> tuple[int, bool] | None:
    """A plan says when the whole investigation ends: a budget of executed
    runs for all its stages together, and whether a failed positive control
    ends it. Without them the results decide how long it goes on."""
    stopping = data.get("stopping")
    if not isinstance(stopping, Mapping):
        found.append(
            Problem("stopping", "the part is missing: there is no stopping condition")
        )
        return None
    budget, on_control = stopping.get("max_runs"), stopping.get("stop_if_control_fails")
    if not _count(budget):
        found.append(
            Problem(
                "stopping",
                "max_runs, the budget of the whole plan in executed runs, is missing",
            )
        )
        return None
    if not isinstance(on_control, bool):
        found.append(
            Problem(
                "stopping",
                "say whether a failed positive control stops the plan"
                " (stop_if_control_fails: true or false)",
            )
        )
        return None
    return budget, on_control


def _baselines(
    found: list[Problem],
    data: Mapping,
    laboratory: Laboratory,
    specification: Specification | None,
) -> tuple[str, float, int] | None:
    baselines = data.get("baselines")
    if not isinstance(baselines, Mapping):
        found.append(Problem("baselines", "the part is missing"))
        return None
    control, grid = baselines.get("control"), baselines.get("grid")
    if (
        not isinstance(control, Mapping)
        or not isinstance(control.get("action"), str)
        or not _number(control.get("answer"))
    ):
        found.append(
            Problem(
                "baselines",
                "a positive control needs an action and its known answer",
            )
        )
        return None
    action = laboratory.action(control["action"])
    if action is None:
        found.append(
            Problem(
                "baselines",
                f"{control['action']!r} is not an action of the laboratory",
            )
        )
        return None
    if specification is not None and (
        action.returns.get(specification.observable) != specification.observable_unit
        or dict(action.units) != dict(laboratory.action(specification.measure).units)
    ):
        found.append(
            Problem(
                "baselines",
                f"the control {action.tool.name} must take the same arguments and"
                f" return {specification.observable} in"
                f" {specification.observable_unit}",
            )
        )
        return None
    if not isinstance(grid, Mapping) or not _count(grid.get("runs")):
        found.append(Problem("baselines", "the grid baseline needs a number of runs"))
        return None
    if grid["runs"] < 2:
        found.append(
            Problem(
                "baselines",
                "the grid baseline needs at least 2 runs: an even grid spans the"
                " varied range from its low end to its high end",
            )
        )
        return None
    return control["action"], float(control["answer"]), grid["runs"]


def check(data: Any, laboratory: Laboratory) -> Plan:
    """The plan ``data`` describes, checked against ``laboratory``;
    ``PlanRejected`` with every problem when it cannot be executed as
    written. Nothing is executed."""
    if not isinstance(data, Mapping):
        raise PlanRejected([Problem("plan", "must be a mapping")])
    found = [
        Problem("plan", f"{key!r} is not a part of a plan")
        for key in data
        if key not in PLAN_PARTS
    ]
    kind = data.get("kind")
    if kind not in KINDS:
        found.append(Problem("kind", f"the kind must be one of {', '.join(KINDS)}"))
    source = data.get("source")
    if not isinstance(source, Mapping) or not all(
        isinstance(source.get(key), str) and source[key].strip()
        for key in ("reference", "statement")
    ):
        found.append(
            Problem(
                "source", "name the reference and the statement the plan starts from"
            )
        )
    published = None
    if kind == "replication":
        published = source.get("verdict") if isinstance(source, Mapping) else None
        if not isinstance(published, str):
            found.append(
                Problem(
                    "source", "a replication names the verdict it was published with"
                )
            )
    specification = None
    try:
        specification = parse(copy.deepcopy(data.get("specification")), laboratory)
    except SpecificationRejected as rejected:
        found += [
            Problem("specification", f"{p.part}: {p.message}")
            for p in rejected.problems
        ]
    baselines = _baselines(found, data, laboratory, specification)
    withheld = _withheld(found, data, specification, laboratory)
    success = data.get("success")
    required = [ROUTE_MET, CONTROL_PASSED, WITHHELD_PASSED]
    if kind == "replication":
        required.append(PUBLISHED_VERDICT)
    elif isinstance(success, list) and PUBLISHED_VERDICT in success:
        found.append(
            Problem("success", "an original investigation has no published verdict")
        )
    if not isinstance(success, list) or any(c not in CRITERIA for c in success):
        found.append(
            Problem("success", f"the criteria are a list from: {'; '.join(CRITERIA)}")
        )
    else:
        for missing in (c for c in required if c not in success):
            found.append(Problem("success", f"the criterion {missing!r} is missing"))
    stopping = _stopping(found, data)
    if (
        stopping
        and baselines
        and specification
        and len(withheld) == len(data.get("withheld") or [])
    ):
        stages = (
            runs_needed(specification)
            + specification.max_runs
            + baselines[2]
            + sum(test.runs for test in withheld)
        )
        if stages > stopping[0]:
            found.append(
                Problem(
                    "stopping",
                    f"the stages need up to {stages} runs and the plan's budget"
                    f" is {stopping[0]}",
                )
            )
    if found:
        raise PlanRejected(found)
    return Plan(
        kind=kind,
        source=dict(source),
        specification=specification,
        control_action=baselines[0],
        control_answer=baselines[1],
        grid_runs=baselines[2],
        withheld=tuple(withheld),
        success=tuple(success),
        max_runs=stopping[0],
        stop_if_control_fails=stopping[1],
        published_verdict=published,
        data=copy.deepcopy(dict(data)),
    )


@dataclass(frozen=True)
class Control:
    """The positive control: the route on the control action, and whether
    its bracket holds the known answer."""

    record: Record
    passed: bool


@dataclass(frozen=True)
class Grid:
    """The method baseline: the settings, the values, and the best setting."""

    settings: tuple[float, ...]
    values: tuple[float, ...]
    best: float


@dataclass(frozen=True)
class Outcome:
    """A withheld test, opened once: its settings and values, its best
    setting, and whether that lies inside the route's bracket."""

    test: Withheld
    settings: tuple[float, ...]
    values: tuple[float, ...]
    best: float
    passed: bool


@dataclass(frozen=True)
class PlanRecord:
    """What the plan did, stage by stage, the criteria, the verdict, the
    runs of all stages, the plan executed, and whether it is the plan that
    was frozen."""

    digest: str
    frozen: str
    stop: str
    control: Control
    record: Record | None
    grid: Grid | None
    withheld: tuple[Outcome, ...]
    criteria: Mapping[str, bool]
    verdict: str
    runs: int
    data: Mapping[str, Any]

    @property
    def as_registered(self) -> bool:
        return self.digest == self.frozen

    @property
    def status(self) -> str:
        return self.stop if self.as_registered else NOT_REGISTERED


def _scan(
    laboratory: Laboratory,
    specification: Specification,
    settings: list[float],
    numerical: float | None,
) -> tuple[float, ...]:
    """The observable at each setting of the varied variable, through an
    allowlist with exactly as many runs as settings."""
    allowlist = laboratory.allowlist(len(settings))
    fixed = {v.name: v.value for v in specification.variables if v.role != "varied"}
    if numerical is not None:
        fixed[specification.numerical.name] = numerical
    values = []
    for number, setting in enumerate(settings, start=1):
        arguments = {**fixed, specification.varied.name: setting}
        result = allowlist.dispatch(
            ToolCall(f"scan-{number}", specification.measure, arguments)
        )
        if not result.ok:
            raise RuntimeError(f"a checked plan made a refused call: {result.content}")
        values.append(float(result.content[specification.observable]))
    return tuple(values)


def _best(settings: list[float], values: tuple[float, ...], goal: str) -> float:
    sign = 1.0 if goal == "largest" else -1.0
    return settings[max(range(len(values)), key=lambda i: sign * values[i])]


def execute(plan: Plan, laboratory: Laboratory, frozen: str) -> PlanRecord:
    """Run ``plan`` stage by stage: the positive control, the route on the
    specification, the grid baseline, and then each withheld test once.
    ``frozen`` is the digest written before the first run."""
    spec = plan.specification
    control_spec = Specification(**{**spec.__dict__, "measure": plan.control_action})
    control_record = route(control_spec, laboratory)
    low, high = (
        (control_record.bracket[0], control_record.bracket[2])
        if control_record.bracket
        else (math.nan, math.nan)
    )
    control = Control(control_record, low <= plan.control_answer <= high)
    runs = len(control_record.runs)
    criteria = {criterion: False for criterion in plan.success}
    criteria[CONTROL_PASSED] = control.passed
    if not control.passed and plan.stop_if_control_fails:
        return PlanRecord(
            digest=freeze(plan.data),
            frozen=frozen,
            stop=CONTROL_FAILED,
            control=control,
            record=None,
            grid=None,
            withheld=(),
            criteria=criteria,
            verdict=NO_VERDICT,
            runs=runs,
            data=plan.data,
        )
    record = route(spec, laboratory)
    runs += len(record.runs)
    criteria[ROUTE_MET] = all(record.criteria.values()) and record.bracket is not None
    varied = spec.varied
    step = (varied.high - varied.low) / (plan.grid_runs - 1)
    settings = [varied.low + i * step for i in range(plan.grid_runs)]
    values = _scan(laboratory, spec, settings, None)
    grid = Grid(tuple(settings), values, _best(settings, values, spec.goal))
    runs += len(settings)
    outcomes = []
    if record.bracket is not None:
        low, centre, high = record.bracket
        for test in plan.withheld:
            points = test.settings(centre, spec.resolution, (varied.low, varied.high))
            found = _scan(laboratory, spec, points, test.numerical)
            best = _best(points, found, spec.goal)
            outcomes.append(
                Outcome(test, tuple(points), found, best, low <= best <= high)
            )
            runs += len(points)
    criteria[WITHHELD_PASSED] = bool(outcomes) and all(o.passed for o in outcomes)
    if PUBLISHED_VERDICT in criteria:
        criteria[PUBLISHED_VERDICT] = record.verdict == plan.published_verdict
    met = all(criteria.values())
    return PlanRecord(
        digest=freeze(plan.data),
        frozen=frozen,
        stop=COMPLETED,
        control=control,
        record=record,
        grid=grid,
        withheld=tuple(outcomes),
        criteria=criteria,
        verdict=record.verdict if met else NO_VERDICT,
        runs=runs,
        data=plan.data,
    )
