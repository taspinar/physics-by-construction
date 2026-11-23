"""An experiment specification, and a scripted route that executes it.

A specification is written before the first run. It is plain data in seven
parts, ``PARTS``: the research question, a hypothesis with a prediction that
a result can contradict, the variables with their roles and units, the
observable, the permitted actions, the success criteria, and the stopping
conditions. ``parse`` checks it against a ``Laboratory`` (the actions that
exist, with the bounds and the unit of every argument and result) and
refuses it with every problem it has, before anything runs: a missing part,
a quantity without a unit, a unit that is not the action's, a setting
outside an action's bounds, no stopping condition.

``execute`` is the scripted route: a fixed procedure with no model in it. It
scans the one varied variable, halves the bracket around the best setting
until the bracket is no wider than the resolution the specification asks
for, repeats the last three settings with the numerical variable halved,
and stops. Every call goes through the allowlist of ``pbc.agents.tools``
with the budget of the specification, so the route can do nothing the
specification does not permit. Its ``Record`` holds every run, the reason it
stopped, the criteria, and the verdict on the hypothesis, which is given
only when every success criterion is met, and the identity of the
specification it ran: the digest of the data ``parse`` read, set by the
execution and not by whoever passes the record on (Issue #606).

The route assumes that the observable has one optimum inside the range of
the varied variable and that the first scan is fine enough to see it; it
reports an optimum at the edge of the range instead of an answer.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pbc.agents.messages import ToolCall
from pbc.agents.tools import Allowlist, Parameter, Tool
from pbc.evidence.records import digest_value

# The parts of a specification, in the order they are written.
PARTS = (
    "question",
    "hypothesis",
    "variables",
    "observable",
    "actions",
    "success",
    "stopping",
)
ROLES = ("varied", "fixed", "numerical")
RELATIONS = ("below", "above")
GOALS = ("largest", "smallest")
# The settings of the first scan of the varied variable, ends included.
SCAN_POINTS = 9

CRITERIA_MET = "criteria met"
BUDGET_SPENT = "budget spent"
ACTION_REFUSED = "action refused"
AT_THE_EDGE = "optimum at the edge of the range"

SUPPORTED = "supported"
REFUTED = "refuted"
UNDECIDED = "undecided"
NO_VERDICT = "no verdict"


@dataclass(frozen=True)
class Problem:
    """One reason a specification is refused: the part and what is wrong."""

    part: str
    message: str


class SpecificationRejected(ValueError):
    """A specification that was not executed, with every problem found."""

    def __init__(self, problems: list[Problem]):
        self.problems = tuple(problems)
        super().__init__("; ".join(f"{p.part}: {p.message}" for p in self.problems))


@dataclass(frozen=True)
class Action:
    """A permitted action: an allowlisted tool, with the unit of every
    argument (``units``) and of every result (``returns``)."""

    tool: Tool
    units: Mapping[str, str]
    returns: Mapping[str, str]

    def __post_init__(self) -> None:
        declared = {parameter.name for parameter in self.tool.parameters}
        if set(self.units) != declared:
            raise ValueError(
                f"{self.tool.name}: a unit is needed for exactly the arguments"
                f" {sorted(declared)}, got {sorted(self.units)}"
            )
        if not self.returns:
            raise ValueError(f"{self.tool.name}: the action returns nothing")


@dataclass(frozen=True)
class Laboratory:
    """The actions an experiment may be specified with."""

    actions: tuple[Action, ...]

    def action(self, name: str) -> Action | None:
        return next((a for a in self.actions if a.tool.name == name), None)

    def allowlist(self, budget: int) -> Allowlist:
        """A fresh allowlist of the actions, with ``budget`` executed calls."""
        return Allowlist(tuple(a.tool for a in self.actions), budget=budget)


@dataclass(frozen=True)
class Prediction:
    """What the hypothesis says the answer will be: the best setting of
    ``quantity`` lies ``below`` or ``above`` ``value``, in ``unit``."""

    quantity: str
    relation: str
    value: float
    unit: str


@dataclass(frozen=True)
class Variable:
    """A variable of the experiment. A ``varied`` one has the range ``low``
    to ``high``; a ``fixed`` one and a ``numerical`` one (a parameter of the
    method, not of the physics) have a ``value``."""

    name: str
    role: str
    unit: str
    low: float | None = None
    high: float | None = None
    value: float | None = None


@dataclass(frozen=True)
class Specification:
    """A specification that passed ``parse``."""

    question: str
    statement: str
    prediction: Prediction
    variables: tuple[Variable, ...]
    observable: str
    observable_unit: str
    goal: str
    actions: tuple[str, ...]
    measure: str  # the permitted action that returns the observable
    resolution: float  # in the unit of the varied variable
    stable: bool
    max_runs: int
    digest: str = ""  # the digest of the data parsed: its identity

    @property
    def varied(self) -> Variable:
        return next(v for v in self.variables if v.role == "varied")

    @property
    def numerical(self) -> Variable | None:
        return next((v for v in self.variables if v.role == "numerical"), None)


def _number(value: Any) -> bool:
    return (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _unit(found: list[Problem], part: str, what: str, entry: Mapping) -> str:
    unit = entry.get("unit")
    if not isinstance(unit, str) or not unit.strip():
        found.append(Problem(part, f"{what} has no unit"))
        return ""
    return unit


def _mapping(found: list[Problem], data: Mapping, part: str) -> Mapping | None:
    if part not in data:
        found.append(Problem(part, "the part is missing"))
        return None
    if not isinstance(data[part], Mapping):
        found.append(Problem(part, "the part must be a mapping"))
        return None
    return data[part]


def _variables(found: list[Problem], data: Mapping) -> list[Variable]:
    entries = _mapping(found, data, "variables")
    if entries is None:
        return []
    variables = []
    for name, entry in entries.items():
        if not isinstance(entry, Mapping):
            found.append(Problem("variables", f"{name} must be a mapping"))
            continue
        role = entry.get("role")
        if role not in ROLES:
            found.append(
                Problem("variables", f"{name} needs a role, one of {', '.join(ROLES)}")
            )
            continue
        unit = _unit(found, "variables", str(name), entry)
        wanted = ("low", "high") if role == "varied" else ("value",)
        if not all(_number(entry.get(key)) for key in wanted):
            found.append(
                Problem(
                    "variables",
                    f"{name} is {role} and needs a number for {' and '.join(wanted)}",
                )
            )
            continue
        if role == "varied" and not entry["low"] < entry["high"]:
            found.append(Problem("variables", f"{name}: low must be below high"))
            continue
        variables.append(
            Variable(
                str(name), role, unit, *(entry.get(k) for k in ("low", "high", "value"))
            )
        )
    for role, allowed in (("varied", "exactly one"), ("numerical", "at most one")):
        count = sum(v.role == role for v in variables)
        if count > 1 or (role == "varied" and count != 1):
            found.append(
                Problem(
                    "variables", f"{allowed} {role} variable is needed, got {count}"
                )
            )
    return variables


def _against_the_action(
    found: list[Problem], variables: list[Variable], action: Action
) -> None:
    """Every argument of the action is a variable, with the action's unit and
    within the action's bounds, and no variable is left over."""
    declared = {p.name: p for p in action.tool.parameters}
    name = action.tool.name
    for missing in sorted(set(declared) - {v.name for v in variables}):
        found.append(
            Problem("variables", f"{name} takes {missing}, which is not specified")
        )
    for variable in variables:
        parameter = declared.get(variable.name)
        if not isinstance(parameter, Parameter):
            found.append(
                Problem("variables", f"{name} takes no number called {variable.name}")
            )
            continue
        unit = action.units[variable.name]
        if variable.unit and variable.unit != unit:
            found.append(
                Problem(
                    "variables",
                    f"{variable.name} is in {variable.unit}, but {name} takes it"
                    f" in {unit}; convert it yourself",
                )
            )
            continue  # a number in another unit is not compared with the bounds
        for value in (variable.low, variable.high, variable.value):
            if value is not None and not parameter.low <= value <= parameter.high:
                found.append(
                    Problem(
                        "variables",
                        f"{variable.name} = {value:g} is outside what {name}"
                        f" permits, {parameter.low:g} to {parameter.high:g}",
                    )
                )


def _hypothesis(
    found: list[Problem], data: Mapping, varied: Variable | None
) -> Prediction | None:
    hypothesis = _mapping(found, data, "hypothesis")
    if hypothesis is None:
        return None
    statement, prediction = hypothesis.get("statement"), hypothesis.get("prediction")
    if not isinstance(statement, str) or not statement.strip():
        found.append(Problem("hypothesis", "the statement is missing"))
    if not isinstance(prediction, Mapping):
        found.append(
            Problem(
                "hypothesis", "a prediction that a result can contradict is missing"
            )
        )
        return None
    unit = _unit(found, "hypothesis", "the prediction", prediction)
    if prediction.get("relation") not in RELATIONS or not _number(
        prediction.get("value")
    ):
        found.append(
            Problem(
                "hypothesis",
                f"the prediction needs a relation ({' or '.join(RELATIONS)})"
                " and a number as its value",
            )
        )
        return None
    if varied is None:
        return None
    if prediction.get("quantity") != varied.name:
        found.append(
            Problem(
                "hypothesis",
                f"the prediction must be about {varied.name}, the variable the"
                " experiment varies",
            )
        )
        return None
    if unit and varied.unit and unit != varied.unit:
        found.append(
            Problem(
                "hypothesis",
                f"the prediction is in {unit}, {varied.name} in {varied.unit}",
            )
        )
    return Prediction(varied.name, prediction["relation"], prediction["value"], unit)


def _measuring_action(
    found: list[Problem],
    data: Mapping,
    laboratory: Laboratory,
    variables: list[Variable],
) -> Action | None:
    """The permitted action that returns the observable, with the observable
    and the variables checked against it."""
    observable = _mapping(found, data, "observable")
    unit = ""
    if observable is not None:
        unit = _unit(found, "observable", "the observable", observable)
        if not isinstance(observable.get("name"), str):
            found.append(Problem("observable", "the name is missing"))
            observable = None
        elif observable.get("goal") not in GOALS:
            found.append(
                Problem("observable", f"the goal must be one of {', '.join(GOALS)}")
            )
    names = data.get("actions")
    if "actions" not in data:
        found.append(Problem("actions", "the part is missing"))
        return None
    if (
        not isinstance(names, list | tuple)
        or not names
        or not all(isinstance(name, str) for name in names)
    ):
        found.append(Problem("actions", "name at least one permitted action"))
        return None
    permitted = []
    for name in names:
        action = laboratory.action(name)
        if action is None:
            found.append(
                Problem("actions", f"{name!r} is not an action of the laboratory")
            )
        else:
            permitted.append(action)
    if observable is None:
        return None
    measuring = [a for a in permitted if observable["name"] in a.returns]
    if len(measuring) != 1:
        found.append(
            Problem(
                "observable",
                f"exactly one permitted action must return {observable['name']},"
                f" {len(measuring)} do",
            )
        )
        return None
    action = measuring[0]
    returned = action.returns[observable["name"]]
    if unit and unit != returned:
        found.append(
            Problem(
                "observable",
                f"{observable['name']} is specified in {unit}, but"
                f" {action.tool.name} returns it in {returned}",
            )
        )
    _against_the_action(found, variables, action)
    return action


def _success(
    found: list[Problem],
    data: Mapping,
    varied: Variable | None,
    numerical: Variable | None,
    action: Action | None,
) -> None:
    success = _mapping(found, data, "success")
    if success is None:
        return
    resolution = success.get("resolution")
    if not isinstance(resolution, Mapping):
        found.append(Problem("success", "the resolution of the answer is missing"))
    else:
        unit = _unit(found, "success", "the resolution", resolution)
        if not _number(resolution.get("value")) or resolution["value"] <= 0:
            found.append(Problem("success", "the resolution must be a positive number"))
        elif varied is not None and unit and varied.unit and unit != varied.unit:
            found.append(
                Problem(
                    "success",
                    f"the resolution is in {unit}, {varied.name} in {varied.unit}",
                )
            )
    if not isinstance(success.get("stable"), bool):
        found.append(
            Problem(
                "success",
                "say whether the answer must hold when the numerical variable"
                " is halved (stable: true or false)",
            )
        )
    elif success["stable"] and numerical is None:
        found.append(Problem("success", "stable needs a numerical variable to halve"))
    elif (
        success["stable"]
        and action is not None
        and action.units.get(numerical.name) == numerical.unit
    ):
        half = numerical.value / 2.0
        bound = next(
            (p for p in action.tool.parameters if p.name == numerical.name), None
        )
        if isinstance(bound, Parameter) and not bound.low <= half <= bound.high:
            found.append(
                Problem(
                    "success",
                    f"stable halves {numerical.name} to {half:g}, which"
                    f" {action.tool.name} does not permit",
                )
            )


def _stopping(found: list[Problem], data: Mapping) -> None:
    """A route without a budget can run for ever, and one that stops "when
    the result looks right" has chosen its answer: the specification must
    say after how many executed actions the experiment ends."""
    if "stopping" not in data:
        found.append(
            Problem("stopping", "the part is missing: there is no stopping condition")
        )
        return
    stopping = data["stopping"]
    budget = stopping.get("max_runs") if isinstance(stopping, Mapping) else None
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < 1:
        found.append(
            Problem(
                "stopping",
                "a stopping condition is missing: max_runs, a positive whole"
                " number of executed actions",
            )
        )


def parse(data: Any, laboratory: Laboratory) -> Specification:
    """The specification ``data`` describes, checked against ``laboratory``;
    ``SpecificationRejected`` with every problem when it cannot be run as
    written. Nothing is executed."""
    if not isinstance(data, Mapping):
        raise SpecificationRejected([Problem("specification", "must be a mapping")])
    found = [
        Problem("specification", f"{key!r} is not a part of a specification")
        for key in data
        if key not in PARTS
    ]
    question = data.get("question")
    if not isinstance(question, str) or not question.strip():
        found.append(Problem("question", "the part is missing"))
    variables = _variables(found, data)
    varied = next((v for v in variables if v.role == "varied"), None)
    numerical = next((v for v in variables if v.role == "numerical"), None)
    prediction = _hypothesis(found, data, varied)
    action = _measuring_action(found, data, laboratory, variables)
    _success(found, data, varied, numerical, action)
    _stopping(found, data)
    if found:
        raise SpecificationRejected(found)
    return Specification(
        question=question,
        statement=data["hypothesis"]["statement"],
        prediction=prediction,
        variables=tuple(variables),
        observable=data["observable"]["name"],
        observable_unit=data["observable"]["unit"],
        goal=data["observable"]["goal"],
        actions=tuple(data["actions"]),
        measure=action.tool.name,
        resolution=float(data["success"]["resolution"]["value"]),
        stable=data["success"]["stable"],
        max_runs=data["stopping"]["max_runs"],
        digest=digest_value(data),
    )


@dataclass(frozen=True)
class Run:
    """One executed action: its number, the stage of the route that asked
    for it, the arguments, and the value of the observable."""

    number: int
    stage: str
    arguments: Mapping[str, float]
    value: float


@dataclass(frozen=True)
class Record:
    """What the route did: the runs, why it stopped, the bracket around the
    best setting (low, best, high) when it found one, whether each success
    criterion is met, the verdict on the hypothesis, and the identity of the
    specification the route ran (its ``digest``)."""

    runs: tuple[Run, ...]
    stop: str
    bracket: tuple[float, float, float] | None
    criteria: Mapping[str, bool]
    verdict: str
    refusal: str = ""
    specification: str = ""


class _Stopped(Exception):
    def __init__(self, reason: str, refusal: str = ""):
        self.reason, self.refusal = reason, refusal


def verdict(prediction: Prediction, bracket: tuple[float, float, float]) -> str:
    """The prediction against the bracket around the best setting: supported
    when the whole bracket lies on the predicted side of the value, refuted
    when the whole bracket lies on the other side, undecided when the value
    is inside the bracket."""
    low, _, high = bracket
    if prediction.relation == "above":
        low, high, value = -high, -low, -prediction.value
    else:
        value = prediction.value
    if high < value:
        return SUPPORTED
    if low >= value:
        return REFUTED
    return UNDECIDED


def execute(specification: Specification, laboratory: Laboratory) -> Record:
    """Run the experiment ``specification`` describes, by the scripted
    route, and return its record."""
    spec = specification
    varied, numerical = spec.varied, spec.numerical
    allowlist = laboratory.allowlist(spec.max_runs)
    sign = 1.0 if spec.goal == "largest" else -1.0
    settings = {v.name: v.value for v in spec.variables if v.role != "varied"}
    runs: list[Run] = []

    def measure(stage: str, setting: float, **changed: float) -> float:
        if len(runs) >= spec.max_runs:
            raise _Stopped(BUDGET_SPENT)
        arguments = {**settings, varied.name: setting, **changed}
        number = len(runs) + 1
        result = allowlist.dispatch(ToolCall(f"run-{number}", spec.measure, arguments))
        if not result.ok:
            raise _Stopped(ACTION_REFUSED, str(result.content["error"]))
        value = float(result.content[spec.observable])
        runs.append(Run(number, stage, arguments, value))
        return value

    bracket = None
    criteria = {"resolved": False}
    if spec.stable:
        criteria["stable"] = False
    try:
        step = (varied.high - varied.low) / (SCAN_POINTS - 1)
        grid = [varied.low + i * step for i in range(SCAN_POINTS)]
        seen = {setting: measure("scan", setting) for setting in grid}
        centre = max(grid, key=lambda setting: sign * seen[setting])
        if centre in (grid[0], grid[-1]):
            raise _Stopped(AT_THE_EDGE)
        bracket = (centre - step, centre, centre + step)
        while 2.0 * step > spec.resolution:
            step /= 2.0
            for setting in (centre - step, centre + step):
                seen[setting] = measure("refine", setting)
            centre = max(
                (centre, centre - step, centre + step),
                key=lambda setting: sign * seen[setting],
            )
            bracket = (centre - step, centre, centre + step)
        criteria["resolved"] = True
        if spec.stable:
            assert numerical is not None
            halved = {numerical.name: numerical.value / 2.0}
            low, best, high = (
                sign * measure("check", setting, **halved) for setting in bracket
            )
            criteria["stable"] = best >= low and best >= high
        stop, refusal = CRITERIA_MET, ""
    except _Stopped as stopped:
        stop, refusal = stopped.reason, stopped.refusal
    met = stop == CRITERIA_MET and all(criteria.values())
    return Record(
        runs=tuple(runs),
        stop=stop,
        bracket=bracket,
        criteria=criteria,
        verdict=verdict(spec.prediction, bracket) if met else NO_VERDICT,
        refusal=refusal,
        specification=spec.digest,
    )
